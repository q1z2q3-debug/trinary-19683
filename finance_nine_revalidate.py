# -*- coding: utf-8 -*-
"""
finance_nine_revalidate.py — 横盘突破信号·跨期复验（多子段 walk-forward）
============================================================
用已有3年面板，把样本外(test)切成前/中/后 3 个连续时段，各做【每5日调仓真实回测】，
检验 alpha 是否跨期稳健（而非只在单一 test 折成立）。train 学参数、test 评估，无前视。
诚实局限：单标的历史、约1.8年测试窗口、每段样本有限。

数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def real_backtest(ht, HZ=5):
    """每 HZ 日调仓、连乘复利真实回测，返回指标。"""
    rebal = sorted(ht["date"].unique())[::HZ]
    ls = []
    for d in rebal:
        g = ht[ht["date"] == d]
        if len(g) < 20:
            continue
        q = pd.qcut(g["sig"], 5, labels=False, duplicates="drop")
        if q.min() == q.max():
            continue
        ls.append(g["fwd5"][q == q.max()].mean() - g["fwd5"][q == q.min()].mean())
    if len(ls) < 4:
        return None
    ls = np.array(ls); n = len(ls)
    net = np.cumprod(1 + ls); total = net[-1] - 1
    years = n * HZ / 252
    ann = (1 + total) ** (1 / years) - 1 if total > -1 else np.nan
    sharpe = ls.mean() / ls.std(ddof=1) * np.sqrt(252 / HZ) if ls.std(ddof=1) > 0 else np.nan
    dd = (net / np.maximum.accumulate(net) - 1).min()
    return {"期数": n, "累计": total, "年化": ann, "Sharpe": sharpe,
            "回撤": dd, "胜率": (ls > 0).mean()}


def main():
    HZ, P, W = 5, 0.25, 0.5
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel).sort_values(["symbol", "date"]).reset_index(drop=True)
    feat["fwd5"] = feat.groupby("symbol")["close"].shift(-5) / feat["close"] - 1.0
    feat = feat.dropna(subset=["mom10", "mom20", "vol_ratio", "fwd5"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique())
    print(f"=== 跨期复验 | hz={HZ} p={P} w={W} | 全历史 {len(dates)} 个交易日 ===")

    tr = int(len(dates) * 0.4); train_d = dates[:tr]
    test_d = dates[tr:]
    # 把 test 切成前/中/后 3 段
    cuts = np.array_split(test_d, 3)
    lo, hi = feat[feat["date"].isin(train_d)]["mom20"].quantile([P, 1 - P]).to_numpy()
    vmed = feat[feat["date"].isin(train_d)]["vol_ratio"].median()

    results = []
    feat = feat.copy()
    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"].copy()
    for i, seg in enumerate(cuts, 1):
        segset = set(seg)
        ht = h[h["date"].isin(segset)].copy()
        rm = ht["mom10"].rank(pct=True).to_numpy()
        ht["sig"] = rm * np.where(ht["vol_ratio"] < vmed, 1.0, W)
        ht = ht.dropna(subset=["sig", "fwd5"])
        r = real_backtest(ht, HZ)
        if r is None:
            print(f"  时段{i}（{seg[0]}~{seg[-1]}）: 样本不足")
            continue
        results.append((i, seg[0], seg[-1], r))
        print(f"  时段{i}（{seg[0]}~{seg[-1]}）: 期数{r['期数']:>3} | "
              f"累计{r['累计']:+.4f} | 年化{r['年化']:+.3f} | "
              f"Sharpe{r['Sharpe']:+.2f} | 回撤{r['回撤']:+.3f} | 胜率{r['胜率']:.2f}")

    if results:
        sharps = [r[3]["Sharpe"] for r in results]
        pos = sum(1 for s in sharps if s > 0)
        print(f"\n  跨期汇总：{pos}/{len(results)} 个时段为正 alpha，Sharpe = "
              f"{[f'{s:+.2f}' for s in sharps]}")
        verdict = ("跨期稳健（多数时段正 alpha）" if pos >= len(results) - 1
                   else ("部分时段正 alpha（稳健性一般）" if pos >= len(results) // 2
                         else "跨期不稳健（如实拦截）"))
        print(f"  → {verdict}")

    print("\n[说明] 后复权+护栏；train学参数、test评估无前视；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
