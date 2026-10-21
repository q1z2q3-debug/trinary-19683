# -*- coding: utf-8 -*-
"""
finance_nine_markov.py — 市场三态转移动力学（升/降/横盘 及 横盘三去向）
============================================================
升(阳)·降(阴)·横盘(变)。横盘不是静止：可升、可降、或继续横盘。
研究：
  [A] 3×3 状态转移矩阵（升/降/横 之间）
  [B] 横盘三去向：概率分布 + 各自未来20日收益
  [C] 横盘持续时长：连续横盘段长度 → 突破方向与突破后收益（蓄势时长效应）
  [D] 量能门控：缩量横盘 vs 放量横盘 的突破质量

数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
from itertools import groupby
import finance_cross as fc


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def main():
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel).sort_values(["symbol", "date"]).reset_index(drop=True)
    feat = feat.dropna(subset=["mom20", "fwd_ret"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique()); si = int(len(dates) * 0.6)
    trd, ted = set(dates[:si]), set(dates[si:])
    lo, hi = feat[feat["date"].isin(trd)]["mom20"].quantile([1 / 3, 2 / 3]).to_numpy()
    print(f"=== 市场三态转移动力学 | {feat['symbol'].nunique()} 只 | 阈值 lo={lo:.4f} hi={hi:.4f} ===")

    st = classify(feat["mom20"].to_numpy(), lo, hi)
    feat["state"] = st
    # 位置法 prev/nxt（避免 groupby.shift 对 <U1 的异常）
    sympos = feat.groupby("symbol").indices
    prev = np.full(len(feat), "", dtype=object); nxt = np.full(len(feat), "", dtype=object)
    for sym, idx in sympos.items():
        for i in range(len(idx) - 1):
            prev[idx[i + 1]] = st[idx[i]]
            nxt[idx[i]] = st[idx[i + 1]]
    feat["prev"] = prev; feat["nxt"] = nxt
    dd = feat[(prev != "") & (nxt != "")].copy()

    # [A] 3×3 转移矩阵
    print("\n[A] 状态转移矩阵 P(次日 | 今日)（全体样本，行归一）")
    M = pd.crosstab(dd["state"], dd["nxt"], normalize="index")
    for s in ["升", "横", "降"]:
        print(f"   今日{s} →  升{M.loc[s,'升']:.3f}  横{M.loc[s,'横']:.3f}  降{M.loc[s,'降']:.3f}")

    # [B] 横盘三去向：概率 + 未来收益
    print("\n[B] 横盘三去向（横盘今日 → 次日升/横/降）")
    h = dd[dd["state"] == "横"]
    gh = h.groupby("nxt")["fwd_ret"].agg(["count", "mean"])
    tot = gh["count"].sum()
    for k in ["升", "横", "降"]:
        if k in gh.index:
            print(f"   横盘→{k:<2} 概率={gh.loc[k,'count']/tot:.3f}  n={int(gh.loc[k,'count']):<6}  未来20日={gh.loc[k,'mean']:+.4f}")

    # [C] 横盘段持续时长 → 突破方向与突破后收益
    print("\n[C] 横盘持续时长（连续横盘段长度）→ 突破方向与突破后20日收益")
    runs = []
    for sym, g in feat.groupby("symbol", sort=False):
        sts = g["state"].tolist(); fr = g["fwd_ret"].tolist(); vr = g["vol_ratio"].fillna(0).tolist()
        n = len(sts)
        for k, grp in groupby(range(n), key=lambda i: sts[i]):
            if k != "横":
                continue
            pos = list(grp); end = pos[-1]
            runs.append({"len": len(pos),
                         "nxt": sts[end + 1] if end + 1 < n else "横",
                         "fwd": fr[end], "vol": vr[end]})
    rf = pd.DataFrame(runs)
    for lo_len, hi_len, lbl in [(1, 3, "短横(1-3日)"), (4, 6, "中横(4-6日)"), (7, 99, "长横(≥7日)")]:
        seg = rf[(rf["len"] >= lo_len) & (rf["len"] <= hi_len)]
        if len(seg) == 0:
            continue
        brk = seg[seg["nxt"] != "横"]
        cont = seg[seg["nxt"] == "横"]
        pb = len(brk) / len(seg)
        print(f"   {lbl}  n={len(seg):<6} 突破率={pb:.3f}  突破后20日={brk['fwd'].mean():+.4f}"
              f"  继续横{n}20日={cont['fwd'].mean():+.4f}" if len(cont) else
              f"   {lbl}  n={len(seg):<6} 突破率={pb:.3f}  突破后20日={brk['fwd'].mean():+.4f}")
    # 突破方向分解
    brk = rf[rf["nxt"] != "横"]
    print(f"   全部横盘段: 突破率={len(brk)/len(rf):.3f}  其中突破向上(→升)占比={(brk['nxt']=='升').mean():.3f}")

    # [D] 量能门控：缩量 vs 放量横盘 的突破质量
    print("\n[D] 量能门控：横盘段末量能 → 突破方向与突破后收益")
    vmed = rf["vol"].median()
    for vlo, vhi, lbl in [(0, vmed, "缩量横盘"), (vmed, 99, "放量横盘")]:
        seg = rf[(rf["vol"] >= vlo) & (rf["vol"] < vhi)]
        if len(seg) == 0:
            continue
        brk = seg[seg["nxt"] != "横"]
        up = brk[brk["nxt"] == "升"]["fwd"].mean() if (brk["nxt"] == "升").any() else np.nan
        dn = brk[brk["nxt"] == "降"]["fwd"].mean() if (brk["nxt"] == "降").any() else np.nan
        print(f"   {lbl}  n={len(seg):<6} 突破率={len(brk)/len(seg):.3f}  突破后20日={brk['fwd'].mean():+.4f}  (→升 {up:+.4f} / →降 {dn:+.4f})")

    print("\n[说明] 后复权+护栏；20日动量三态；横盘段=连续横盘日；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
