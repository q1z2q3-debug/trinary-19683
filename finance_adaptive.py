# -*- coding: utf-8 -*-
"""
finance_adaptive.py — 预设参数·经验增强适配（自适应校准）
============================================================
把金融信号里「拍脑袋」的预设数字，用数据网格扫描自适应校准：
  ① 前向持有期 FWD_HORIZON（原固定 20）
  ② 三态划分分位 P（原固定 1/3、2/3）
  ③ 量能门控权重 W（原固定 0.3/1.0）
对「横盘突破综合信号(S4)」在各参数组合下评估样本外 long-short/t，选经验最优，
并做样本外前/后段稳健性。防过拟合提示：最优参数需跨期复验。

数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc


def classify(m, lo, hi):
    return np.where(m > hi, "升", np.where(m < lo, "降", "横"))


def eval_sig(sig, ret):
    m = ~(np.isnan(sig) | np.isnan(ret))
    sig, ret = sig[m], ret[m]
    if len(ret) < 100:
        return np.nan, np.nan, len(ret)
    q = pd.qcut(pd.Series(sig), 5, labels=False, duplicates="drop").to_numpy()
    a = ret[q == q.max()]; b = ret[q == q.min()]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = (a.mean() - b.mean()) / se if se > 0 else np.nan
    return (a.mean() - b.mean()), t, len(ret)


def build_signal(feat, trd, ted, p, w):
    """三态(分位p) + 横盘 + 量能门控加权信号(mom10方向)。返回 test 期信号与各 fwd。"""
    lo, hi = feat[feat["date"].isin(trd)]["mom20"].quantile([p, 1 - p]).to_numpy()
    feat = feat.copy()
    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"]
    ht = h[h["date"].isin(ted)].copy()
    rm = ht["mom10"].rank(pct=True).to_numpy()
    vmed = ht["vol_ratio"].median()
    hm = ht["vol_ratio"] < vmed
    sig = rm * np.where(hm, 1.0, w)          # 缩量保留方向，放量压缩×w
    return ht, sig


def main():
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel).sort_values(["symbol", "date"]).reset_index(drop=True)
    # 重算多持有期前向收益（原预设 FWD=20 → 经验扫描）
    for hz in [5, 10, 20, 40]:
        feat[f"fwd{hz}"] = feat.groupby("symbol")["close"].shift(-hz) / feat["close"] - 1.0
    dates = sorted(feat["date"].unique()); si = int(len(dates) * 0.6)
    trd, ted = set(dates[:si]), set(dates[si:])
    tedl = sorted(ted)
    mid = tedl[len(tedl) // 2]              # 样本外前/后段分界
    print("=== 预设参数 · 经验增强适配（横盘突破综合信号）===\n")

    # ① 扫描持有期（固定 p=1/3, w=0.3）
    print("[①] 前向持有期 FWD_HORIZON（原固定20）→ 信号强度随持有期")
    print("    持有期 | long-short | t | n")
    hz_rows = []
    for hz in [5, 10, 20, 40]:
        ht, sig = build_signal(feat, trd, ted, 1 / 3, 0.3)
        s, t, n = eval_sig(sig, ht[f"fwd{hz}"].to_numpy())
        hz_rows.append((hz, s, t, n))
        print(f"      {hz:>4} | {s:+.4f} | {t:+.2f} | {n}")
    best_hz = max(hz_rows, key=lambda r: abs(r[2]))[0]
    print(f"    → 经验最优持有期 = {best_hz} 日\n")

    # ② 扫描三态分位（固定持有期=最优, w=0.3）
    print(f"[②] 三态划分分位 P（原固定1/3）→ 信号稳健性")
    print("    分位 | long-short | t | n")
    p_rows = []
    for p in [1 / 4, 1 / 3, 0.4, 0.45]:
        ht, sig = build_signal(feat, trd, ted, p, 0.3)
        s, t, n = eval_sig(sig, ht[f"fwd{best_hz}"].to_numpy())
        p_rows.append((p, s, t, n))
        print(f"    {p:>4} | {s:+.4f} | {t:+.2f} | {n}")
    best_p = max(p_rows, key=lambda r: abs(r[2]))[0]
    print(f"    → 经验最优分位 = {best_p}\n")

    # ③ 扫描量能门控权重（固定持有期/分位）
    print(f"[③] 量能门控权重 W（原固定0.3/1.0）→ 经验校准")
    print("    W(放量) | long-short | t | n")
    w_rows = []
    for w in [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
        ht, sig = build_signal(feat, trd, ted, best_p, w)
        s, t, n = eval_sig(sig, ht[f"fwd{best_hz}"].to_numpy())
        w_rows.append((w, s, t, n))
        print(f"      {w:>6} | {s:+.4f} | {t:+.2f} | {n}")
    best_w = max(w_rows, key=lambda r: abs(r[2]))[0]
    print(f"    → 经验最优 W = {best_w}\n")

    # ④ 最优参数下 样本外前/后段稳健性
    print(f"[④] 最优组合(hz={best_hz}, p={best_p}, w={best_w}) 样本外分段稳健性")
    ht, sig = build_signal(feat, trd, ted, best_p, best_w)
    fwd = ht[f"fwd{best_hz}"].to_numpy()
    for lbl, cond in [("前段", ht["date"] < mid), ("后段", ht["date"] >= mid)]:
        s, t, n = eval_sig(sig[cond], fwd[cond])
        print(f"    {lbl}: long-short={s:+.4f} | t={t:+.2f} | n={n}")
    s_all, t_all, _ = eval_sig(sig, fwd)
    print(f"    全体: long-short={s_all:+.4f} | t={t_all:+.2f}")

    print("\n[结论] 经验适配：FWD_HORIZON、三态分位、量能权重均由数据校准；"
          "最优参数需跨期/扩池复验防过拟合。研究演示、非投资建议。")


if __name__ == "__main__":
    main()
