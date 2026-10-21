# -*- coding: utf-8 -*-
"""
finance_nine_entry.py — 横盘突破·合成可交易入场信号（量能门控加权）
============================================================
阶段4b/4c 的合成：横盘(变)的突破方向，用 t 日可观察特征（横盘内微动量 mom10
= 方向，量能 vol_ratio = 门控/力度）合成可交易信号，t+1 可入场、无前视。
对比四路样本外：
  S1 全体横盘 × mom10（基准）
  S2 缩量横盘 × mom10（4b: 方向可预判）
  S3 放量横盘 × mom10（4c: 突破有力但方向难判）
  S4 综合·量能门控加权（缩量保留方向、放量压缩方向）

数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def validate(sig, ret):
    m = ~(np.isnan(sig) | np.isnan(ret))
    sig, ret = sig[m], ret[m]
    if len(ret) < 100:
        return np.nan, np.nan, 0, len(ret)
    q = pd.qcut(pd.Series(sig), 5, labels=False, duplicates="drop").to_numpy()
    a = ret[q == q.max()]; b = ret[q == q.min()]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = (a.mean() - b.mean()) / se if se > 0 else np.nan
    spread = a.mean() - b.mean()
    lm = {int(k): float(np.mean(ret[q == k])) for k in np.unique(q)}
    ks = sorted(lm)
    mono = int(all(lm[ks[i]] <= lm[ks[i + 1]] or lm[ks[i]] >= lm[ks[i + 1]] for i in range(len(ks) - 1)))
    return spread, t, mono, len(ret)


def main():
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel).sort_values(["symbol", "date"]).reset_index(drop=True)
    feat = feat.dropna(subset=["mom10", "mom20", "vol_ratio", "fwd_ret"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique()); si = int(len(dates) * 0.6)
    trd, ted = set(dates[:si]), set(dates[si:])
    lo, hi = feat[feat["date"].isin(trd)]["mom20"].quantile([1 / 3, 2 / 3]).to_numpy()
    print(f"=== 横盘突破·合成可交易信号 | 阈值 lo={lo:.4f} hi={hi:.4f} ===")

    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"].copy()
    ht = h[h["date"].isin(ted)].copy()
    rm = ht["mom10"].rank(pct=True).to_numpy()           # 方向(0..1)
    fr = ht["fwd_ret"].to_numpy()
    vmed = ht["vol_ratio"].median()
    print(f"横盘 test 样本 {len(ht)} 行 | 信号=mom10(方向)+vol_ratio(量能门控)，t 日可观察、t+1 入场\n")

    # S1 全体 / S2 缩量 / S3 放量 / S4 综合
    rows = []
    s1, t1, m1, n1 = validate(rm, fr); rows.append(("S1 全体横盘×mom10", s1, t1, m1, n1))
    hm = ht["vol_ratio"] < vmed
    s2, t2, m2, n2 = validate(rm[hm], fr[hm]); rows.append(("S2 缩量横盘×mom10(方向可预判)", s2, t2, m2, int(hm.sum())))
    s3, t3, m3, n3 = validate(rm[~hm], fr[~hm]); rows.append(("S3 放量横盘×mom10(突破有力)", s3, t3, m3, int((~hm).sum())))
    # 综合：量能门控加权——缩量保留方向(w=1.0)，放量压缩(w=0.3)
    w = np.where(hm, 1.0, 0.3)
    sig4 = rm * w
    s4, t4, m4, n4 = validate(sig4, fr); rows.append(("S4 综合·量能门控加权", s4, t4, m4, n4))

    print("样本外 long-short（横盘内 未来20日 多空分层）")
    for name, s, t, m, n in rows:
        flag = "✓显著" if abs(t) >= 2 else ("↘弱" if abs(t) >= 1 else "✗不显著")
        print(f"  {name:<28} long-short={s:+.4f} | t={t:+.2f} | 单调={m} | n={n:<5} {flag}")

    # 做多/做空方向触发（S4 综合信号高低层）
    q = pd.qcut(pd.Series(sig4), 2, labels=False, duplicates="drop").to_numpy()
    long_ret = fr[q == q.max()].mean(); short_ret = fr[q == q.min()].mean()
    print(f"\nS4 综合信号：高信号(偏做多)未来20日={long_ret:+.4f} | 低信号(偏做空)={short_ret:+.4f}")
    print("  → " + ("合成信号样本外显著，可作入场方向信号" if abs(t4) >= 2
                    else "合成信号样本外未达显著阈值（如实拦截）"))

    print("\n[说明] 后复权+护栏；信号仅用 t 日数据；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
