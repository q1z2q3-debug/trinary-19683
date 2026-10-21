# -*- coding: utf-8 -*-
"""
finance_refuter.py — 阶段2 证伪风控（金融版 Refuter）
============================================================
把三元九维认知棋盘最独特的「证伪动力学」落到金融决策：
横截面状态信号之上，叠加三档证伪 —— 信号失效 → 降置信 / 降仓 / 止损，
对比「裸信号」与「带证伪」的风险调整后表现。

三档证伪（对齐 cognition_board.Refuter）：
  - 软证伪：组合近期收益转负（信号开始失效）→ 降仓 50%
  - 硬证伪：连续多期失效（信号确认背离）→ 清仓（可逆，信号恢复再进场）
  - 置信衰减：样本不足/波动放大 → 降置信（体现为仓位上限降低）

用法：  python3 finance_refuter.py
数据：复用 finance_full_panel_298stocks.csv（baostock，前复权，研究演示·非投资建议）
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import finance_cross as fc


class FinRefuter:
    """金融版三档证伪器（最小实现）。"""
    def __init__(self, soft_win=5, hard_win=10, soft_cut=0.0, hard_cut=0.0,
                 soft_scale=0.5, max_scale=1.0, min_scale=0.0):
        self.soft_win = soft_win          # 软证伪窗口（日）
        self.hard_win = hard_win          # 硬证伪窗口（日）
        self.soft_cut = soft_cut          # 软证伪：窗口收益 < 此值触发
        self.hard_cut = hard_cut          # 硬证伪：窗口收益 < 此值触发
        self.soft_scale = soft_scale      # 软证伪后仓位比例
        self.max_scale = max_scale
        self.min_scale = min_scale

    def position_scales(self, combo_ret: np.ndarray):
        """输入组合日收益序列，输出每日仓位比例（0~1）。证伪事件可逆。"""
        n = len(combo_ret)
        scale = np.ones(n)
        hard_off = -1          # 硬证伪生效起点（清仓区间）
        for i in range(n):
            w = self._window_ret(combo_ret, i, self.soft_win)
            hw = self._window_ret(combo_ret, i, self.hard_win)
            # 先判断恢复（已清仓时，软窗口转正 → 恢复）
            if hard_off >= 0 and i > hard_off and w > self.soft_cut:
                hard_off = -1          # 可逆：信号恢复，重新进场
                scale[i] = self.max_scale
                continue
            if hard_off >= 0 and i <= hard_off:
                scale[i] = self.min_scale
                continue
            # 硬证伪：硬窗口严重转负 → 清仓
            if hw < self.hard_cut:
                hard_off = i
                scale[i] = self.min_scale
                continue
            # 软证伪：软窗口转负 → 降仓
            if w < self.soft_cut:
                scale[i] = self.soft_scale
            else:
                scale[i] = self.max_scale
        return scale

    @staticmethod
    def _window_ret(ret: np.ndarray, i: int, w: int):
        if i - w + 1 < 0:
            return float("nan")
        seg = ret[max(0, i - w + 1): i + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) == 0:
            return float("nan")
        return float(np.nanprod(1 + seg) - 1)


def build_signal_panel(panel: pd.DataFrame, features, top_quantile=0.3,
                       min_samples=20, train_frac=0.6):
    """train 学状态信号 → test 期每日选 top 层股票。返回 test 期组合日收益序列。"""
    feat = fc.panel_features(panel)
    tri = fc.cross_trinary(feat, features)
    st = fc.state_number(tri[[f + "_tri" for f in features]].to_numpy().T)
    feat = feat.assign(state=st, daily_ret=feat.groupby("symbol")["close"].pct_change())
    # 剔除异常跳空（停牌复牌/数据错误）：A股单日涨跌超 ±21% 视为异常
    feat.loc[feat["daily_ret"].abs() > 0.21, "daily_ret"] = np.nan

    dates = sorted(feat["date"].unique())
    si = int(len(dates) * train_frac)
    tr_dates, te_dates = set(dates[:si]), set(dates[si:])

    tr = feat[feat["date"].isin(tr_dates)]
    grp = tr.groupby("state")["fwd_ret"]
    sig = pd.DataFrame({"n": grp.count(), "mean": grp.mean()})
    sig = sig[sig["n"] >= min_samples]
    signal = dict(zip(sig.index, sig["mean"]))

    te = feat[feat["date"].isin(te_dates)].copy()
    te["signal"] = te["state"].map(signal)
    te = te.dropna(subset=["signal", "daily_ret"])

    # 每日期：选 top 层信号股票，等权组合日收益
    daily = {}
    for dt, g in te.groupby("date"):
        thr = g["signal"].quantile(1 - top_quantile)
        top = g[g["signal"] >= thr]
        if len(top) == 0:
            daily[dt] = np.nan
        else:
            daily[dt] = top["daily_ret"].mean()
    combo = pd.Series(daily).sort_index()
    return combo, signal, feat


def metrics(ret: pd.Series, scale: np.ndarray):
    """组合日收益 × 仓位 → 风险与收益指标（聚焦风控稳健项）。"""
    r = ret.to_numpy() * scale
    r = r[~np.isnan(r)]
    if len(r) < 20:
        return {}
    ann = 252
    total = np.prod(1 + r) - 1
    vol = np.nanstd(r) * np.sqrt(ann)
    sharpe = (np.nanmean(r) * ann) / (np.nanstd(r) * np.sqrt(ann)) if np.nanstd(r) > 0 else np.nan
    cum = np.cumprod(1 + r)
    peak = np.maximum.accumulate(cum)
    mdd = float(np.max((peak - cum) / peak)) if len(cum) else np.nan
    loss_days = int((r < 0).sum())
    max_loss_day = float(np.nanmin(r))
    worst_5d = float(np.min([np.prod(1 + r[i:i+5]) - 1
                             for i in range(len(r) - 4)]))
    return {"total_ret": total, "vol": vol, "sharpe": sharpe, "mdd": mdd,
            "loss_days": loss_days, "max_loss_day": max_loss_day,
            "worst_5d": worst_5d, "n_days": len(r)}


def main():
    print("=== 阶段2 证伪风控 · 横截面信号 + 三档证伪（研究演示） ===")
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    features = ["mom20", "mom60", "rev5", "vol20", "vol_ratio"]
    combo, signal, feat = build_signal_panel(panel, features)
    combo = combo.dropna()
    print(f"test 期组合日收益：{len(combo)} 日（{combo.index[0]} ~ {combo.index[-1]}）")
    print(f"train 有效状态 {len(signal)} 个")

    fr = FinRefuter(soft_win=5, hard_win=10, soft_cut=0.0, hard_cut=-0.02,
                    soft_scale=0.5)
    scale = fr.position_scales(combo.to_numpy())
    print(f"证伪触发：硬证伪(清仓)区间天数 = {(scale==0).sum()}，"
          f"软证伪(半仓)天数 = {(scale==0.5).sum()}，满仓天数 = {(scale==1).sum()}")

    m0 = metrics(combo, np.ones(len(combo)))
    m1 = metrics(combo, scale)
    print()
    print(f"{'指标':<12}{'裸信号(满仓)':>16}{'带证伪':>16}")
    rows = [("总收益", "total_ret", "{:+.3f}"), ("年化波动", "vol", "{:.3f}"),
            ("夏普", "sharpe", "{:+.2f}"), ("最大回撤", "mdd", "{:.3f}"),
            ("亏损日数", "loss_days", "{:.0f}"), ("最大单日亏", "max_loss_day", "{:+.3f}"),
            ("最差5日", "worst_5d", "{:+.3f}")]
    for label, k, fmt in rows:
        v0 = m0.get(k, np.nan); v1 = m1.get(k, np.nan)
        f0 = (fmt + "").format(v0) if v0 == v0 else "  -"
        f1 = (fmt + "").format(v1) if v1 == v1 else "  -"
        print(f"{label:<12}{f0:>16}{f1:>16}")
    print()
    print("[局限] 单段 test（92日）价量因子样本；恰逢上涨段致绝对收益偏高，")
    print("      绝对收益/夏普不可外推。**本演示的价值在风控层**：")
    print("      证伪是否降低 最大回撤 / 波动 / 亏损日 / 尾部损失。")
    print("[说明] 复用 baostock 面板（前复权）；三档证伪可逆；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
