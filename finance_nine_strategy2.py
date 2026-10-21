# -*- coding: utf-8 -*-
"""
finance_nine_strategy2.py — 横盘突破策略【真实回测】（每5日调仓，消除重叠）
============================================================
修正阶段4f 的逐日重叠问题：每 HZ=5 日调仓一次，组合持有该5日收益（非重叠），
净值 = 逐期连乘（真实复利）。输出：年化 / 波动 / Sharpe / 最大回撤 / 胜率。
诚实标注：test 期约 90 日 → 调仓周期少，统计估计波动大。

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
    print(f"=== 横盘突破策略·真实回测 | hz={HZ} p={P} w={W} ===")

    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"].copy()
    ht = h[h["date"].isin(ted)].copy()
    rm = ht["mom10"].rank(pct=True).to_numpy()
    hm = ht["vol_ratio"] < ht["vol_ratio"].median()
    ht["sig"] = rm * np.where(hm, 1.0, W)
    ht = ht.dropna(subset=["sig", f"fwd{HZ}"])

    # 每5日调仓（非重叠）
    rebal = sorted(ht["date"].unique())[::HZ]
    ls_list = []
    for d in rebal:
        g = ht[ht["date"] == d]
        if len(g) < 20:
            continue
        q = pd.qcut(g["sig"], 5, labels=False, duplicates="drop")
        if q.min() == q.max():
            continue
        ls = g[f"fwd{HZ}"][q == q.max()].mean() - g[f"fwd{HZ}"][q == q.min()].mean()
        ls_list.append(ls)
    if len(ls_list) < 4:
        print("调仓期数不足，无法回测")
        return

    ls = np.array(ls_list)
    net = np.cumprod(1 + ls)                       # 真实复利净值
    total = net[-1] - 1
    n = len(ls)
    years = n * HZ / 252
    ann = (1 + total) ** (1 / years) - 1 if total > -1 else np.nan
    vol_ann = ls.std(ddof=1) * np.sqrt(252 / HZ)
    sharpe = ls.mean() / ls.std(ddof=1) * np.sqrt(252 / HZ) if ls.std(ddof=1) > 0 else np.nan
    dd = (net / np.maximum.accumulate(net) - 1).min()

    print(f"\n真实回测（每{HZ}日调仓，非重叠）：{n} 期 / 约 {years:.2f} 年")
    print(f"  累计收益(连乘)      = {total:+.4f}")
    print(f"  年化收益            = {ann:+.3f}")
    print(f"  年化波动            = {vol_ann:.3f}")
    print(f"  Sharpe(年化)        = {sharpe:+.2f}")
    print(f"  最大回撤            = {dd:+.3f}")
    print(f"  胜率(正收益期)      = {(ls > 0).mean():.3f}")
    print(f"  平均每期收益        = {ls.mean():+.5f} / 期")
    print(f"\n  逐期净值序列: " + " ".join(f"{x:+.3f}" for x in net))
    verdict = ("正 alpha 且回撤可控" if total > 0 and sharpe > 0.5
               else ("正 alpha 但样本少/Sharpe偏低" if total > 0 else "累计为负（如实拦截）"))
    print(f"  → {verdict}")

    print("\n[说明] 后复权+护栏；test期约90日→调仓~18期，小样本统计波动大，需跨期复验；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
