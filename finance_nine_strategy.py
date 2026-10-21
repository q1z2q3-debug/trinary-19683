# -*- coding: utf-8 -*-
"""
finance_nine_strategy.py — 横盘突破策略回测（经验适配后参数）
============================================================
用阶段4e 经验适配的最优参数(hz=5, p=0.25, w=0.5)构造可回测策略：
  横盘状态 → 量能门控加权方向信号(mom10) → 逐时点5层分组
  层5(高信号)做多 / 层1(低信号)做空 → long-short 对冲组合
逐时点组合收益 → 累计净值。样本外(test)期回测。
诚实标注：5日收益逐日重叠，sharpe/波动因自相关偏乐观，须注意。

数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def main():
    HZ, P, W = 5, 0.25, 0.5                      # 经验适配最优
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel).sort_values(["symbol", "date"]).reset_index(drop=True)
    feat[f"fwd{HZ}"] = feat.groupby("symbol")["close"].shift(-HZ) / feat["close"] - 1.0
    feat = feat.dropna(subset=["mom10", "mom20", "vol_ratio", f"fwd{HZ}"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique()); si = int(len(dates) * 0.6)
    trd, ted = set(dates[:si]), set(dates[si:])
    lo, hi = feat[feat["date"].isin(trd)]["mom20"].quantile([P, 1 - P]).to_numpy()
    print(f"=== 横盘突破策略回测 | hz={HZ} p={P} w={W} | 阈值 lo={lo:.4f} hi={hi:.4f} ===")

    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"]
    ht = h[h["date"].isin(ted)].copy()
    rm = ht["mom10"].rank(pct=True).to_numpy()
    hm = ht["vol_ratio"] < ht["vol_ratio"].median()
    ht["sig"] = rm * np.where(hm, 1.0, W)
    ht = ht.dropna(subset=["sig", f"fwd{HZ}"])
    fwd = ht[f"fwd{HZ}"].to_numpy()

    # 逐时点 long-short 组合：组内按信号5层，层5(高)做多-层1(低)做空
    rows = []
    for d, g in ht.groupby("date"):
        if len(g) < 10:
            continue
        q = pd.qcut(g["sig"], 5, labels=False, duplicates="drop")
        if q.min() == q.max():
            continue
        top = q == q.max()          # 前20% 高信号（做多）
        bot = q == q.min()          # 后20% 低信号（做空）
        ls = g[f"fwd{HZ}"][top].mean() - g[f"fwd{HZ}"][bot].mean()
        rows.append((d, len(g), ls))
    strat = pd.DataFrame(rows, columns=["date", "n", "ls"])
    strat["cum"] = strat["ls"].cumsum()

    print(f"\n样本外逐日 long-short 组合：{len(strat)} 个时点（test 期）")
    print(f"  累计净收益(5日持有,long-short) = {strat['cum'].iloc[-1]:+.4f}")
    print(f"  日均 long-short = {strat['ls'].mean():+.5f}  胜率(正日占比) = {(strat['ls']>0).mean():.3f}")
    print(f"  最大回撤(累计) = {((strat['cum']-strat['cum'].cummax()).min()):+.4f}")
    # 年化估计（252日）
    ann = strat['ls'].mean() * 252
    print(f"  年化(粗估, 5日持有重叠) = {ann:+.3f}")

    print("\n  累计净值曲线（前20个时点预览）:")
    print("  " + "".join(["█" if x > 0 else "░" for x in strat['cum'].iloc[:20].diff().fillna(0)])[:60])
    print("  → " + ("策略样本外呈正 alpha（long-short 累计为正）" if strat['cum'].iloc[-1] > 0
                    else "策略样本外累计为负（如实拦截）"))

    print("\n[说明] 后复权+护栏；5日收益逐日重叠致统计偏乐观；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
