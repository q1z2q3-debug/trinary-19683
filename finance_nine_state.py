# -*- coding: utf-8 -*-
"""
finance_nine_state.py — 阴阳变·九变 金融市场状态转化研究
============================================================
三态：升(阳/R) · 降(阴/D) · 横盘(变/T)，横盘可升可降（变的双向性）。
九变转化：相邻两日市场状态的三元组合 → 凝/交/萌/化/盛/动/敛/发/元变。

研究问题：
  [A] 九变转化 × 未来收益 —— 延续(盛/凝) vs 反转(化/交) vs 横盘突破(发/敛)
  [B] 横盘(变)的双向性 —— 横盘当日，次日升/横/降对未来收益的区分
  [C] 样本外 —— 变型信号的 walk-forward 分层是否可复算

数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc

NINE_CN = {"升→升": "盛", "降→降": "凝", "升→降": "化", "降→升": "交",
           "升→横": "动", "降→横": "萌", "横→升": "发", "横→降": "敛", "横→横": "元变"}


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def _validate(sig, ret):
    m = ~(np.isnan(sig) | np.isnan(ret))
    sig, ret = sig[m], ret[m]
    if len(ret) < 100:
        return np.nan, np.nan, 0, len(ret)
    q = pd.qcut(pd.Series(sig), 5, labels=False, duplicates="drop")
    codes = np.unique(q)
    a = ret[q == codes[-1]]; b = ret[q == codes[0]]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = (a.mean() - b.mean()) / se if se > 0 else np.nan
    spread = a.mean() - b.mean()
    lm = {int(k): float(np.mean(ret[q == k])) for k in codes}
    mono = 1 if len(codes) >= 3 and lm[int(codes[-1])] == max(lm.values()) else 0
    return spread, t, mono, len(ret)


def main():
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel)
    feat = feat.sort_values(["symbol", "date"]).reset_index(drop=True)
    feat = feat.dropna(subset=["mom20", "fwd_ret"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique()); si = int(len(dates) * 0.6)
    trd, ted = set(dates[:si]), set(dates[si:])
    m_tr = feat[feat["date"].isin(trd)]["mom20"]
    lo, hi = m_tr.quantile(1 / 3), m_tr.quantile(2 / 3)      # train 期分位，无前视
    print(f"=== 阴阳变·九变 金融状态转化 | {feat['symbol'].nunique()} 只 | mom20 分位 lo={lo:.4f} hi={hi:.4f} ===")

    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    feat["prev"] = feat.groupby("symbol")["state"].shift(1)
    feat["next"] = feat.groupby("symbol")["state"].shift(-1)
    feat["trans"] = feat["prev"] + "→" + feat["state"]
    feat["trans_cn"] = feat["trans"].map(NINE_CN)
    dd = feat.dropna(subset=["prev"]).copy()

    # [A] 九变 × 未来收益（全体样本）
    g = dd.groupby(["trans_cn", "trans"])["fwd_ret"].agg(["count", "mean"])
    print("\n[A] 九变转化 × 未来20日均收益（全体样本，按变型）")
    order = ["盛", "交", "萌", "动", "发", "元变", "化", "敛", "凝"]
    mmin, mmax = g["mean"].min(), g["mean"].max()
    for k in order:
        sub = g[g.index.get_level_values(0) == k]
        for (cn, tt), (cnt, mn) in sub.iterrows():
            bar = "█" * max(0, int(round((mn - mmin) / (mmax - mmin) * 20))) if mmax > mmin else ""
            print(f"  {k}({tt:<5}) n={int(cnt):<6} 未来20日={mn:+.4f} {bar}")

    # [B] 横盘双向性：处于横盘时，次日升/横/降 → 未来收益
    h = dd[dd["state"] == "横"].dropna(subset=["next"])
    gh = h.groupby("next")["fwd_ret"].agg(["count", "mean"])
    print("\n[B] 横盘(变)的双向性：横盘当日，按次日走向分组的未来20日收益")
    for k, row in gh.iterrows():
        print(f"  横盘→{k}  n={int(row['count']):<6} 未来20日={row['mean']:+.4f}")
    if len(gh) >= 2:
        a = h[h["next"] == "升"]["fwd_ret"]; b = h[h["next"] == "降"]["fwd_ret"]
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"  横盘→升 vs 横盘→降：差={a.mean()-b.mean():+.4f}  t={a.mean()-b.mean()/se:+.2f}" if se > 0
              else "  样本不足")

    # [C] 样本外分层（变型信号）
    print("\n[C] 样本外验证：train 学变型平均收益 → test 分层")
    sig_tr = dd[dd["date"].isin(trd)].groupby("trans")["fwd_ret"].mean()
    dd["sig"] = dd["trans"].map(sig_tr)
    te_d = dd[dd["date"].isin(ted)].dropna(subset=["sig"])
    spread, t, mono, nn = _validate(te_d["sig"].to_numpy(), te_d["fwd_ret"].to_numpy())
    print(f"  样本外 long-short={spread:+.4f} | t={t:+.2f} | 单调={mono} | 覆盖={nn}")
    print("  → " + ("变型信号样本外显著" if abs(t) >= 2 else "变型信号样本外不显著（如实拦截）"))

    print("\n[说明] 后复权+护栏；变型=相邻日状态转化；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
