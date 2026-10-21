# -*- coding: utf-8 -*-
"""
finance_nine_revalidate2.py — 横盘突破信号·长历史跨期复验（扩池延史）
============================================================
在 baostock 扩池延史面板（hs300 300只 / 2018-2026 约8.7年）上，
用既有经验适配参数(hz=5,p=0.25,w=0.5)重跑跨期复验：train学参数、test切5个连续子时段，
各做每5日调仓真实回测。检验 alpha 在长历史/更多股票下是否跨期稳健。
诚实局限：单标的池、后复权；研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def real_backtest(ht, HZ=5):
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
    if len(ls) < 10:
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
    panel = pd.read_csv("finance_panel_ext_hs300.csv")
    print(f"面板：{panel['symbol'].nunique()} 只 / {len(panel)} 行 / "
          f"{panel['date'].min()}~{panel['date'].max()}")
    feat = fc.panel_features(panel).sort_values(["symbol", "date"]).reset_index(drop=True)
    feat["fwd5"] = feat.groupby("symbol")["close"].shift(-5) / feat["close"] - 1.0
    feat = feat.dropna(subset=["mom10", "mom20", "vol_ratio", "fwd5"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique())
    print(f"=== 长历史跨期复验 | hz={HZ} p={P} w={W} | {len(dates)} 个交易日 ===")

    tr = int(len(dates) * 0.4); train_d = dates[:tr]
    test_d = dates[tr:]
    K = 5
    cuts = np.array_split(test_d, K)
    lo, hi = feat[feat["date"].isin(train_d)]["mom20"].quantile([P, 1 - P]).to_numpy()
    vmed = feat[feat["date"].isin(train_d)]["vol_ratio"].median()
    print(f"train {train_d[0]}~{train_d[-1]} ({len(train_d)}日) → test {test_d[0]}~{test_d[-1]} ({len(test_d)}日, {K}段)\n")

    feat = feat.copy()
    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"].copy()
    results = []
    for i, seg in enumerate(cuts, 1):
        ht = h[h["date"].isin(set(seg))].copy()
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
        print(f"\n  跨期汇总：{pos}/{len(results)} 段正 alpha | Sharpe = {[f'{s:+.2f}' for s in sharps]}")
        print(f"  Sharpe 均值 {np.mean(sharps):+.2f} / 中位 {np.median(sharps):+.2f}")
        verdict = ("跨期稳健（多数时段正 alpha，且Sharpe均值>0.5）"
                   if pos >= len(results) - 1 and np.mean(sharps) > 0.5
                   else ("部分稳健（正负交替，alpha波动）" if pos >= len(results) // 2
                         else "跨期不稳健（如实拦截）"))
        print(f"  → {verdict}")

    print("\n[说明] 后复权+护栏；train学参数、test评估无前视；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
