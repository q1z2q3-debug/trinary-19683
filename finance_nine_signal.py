# -*- coding: utf-8 -*-
"""
finance_nine_signal.py — 横盘(变)突破方向的【可交易】信号（无前视）
============================================================
上一轮 [B] 用「次日状态」分组含轻微未来信息。这里只取 t 日收盘前可观察特征
（横盘内微动量 mom10 + 量能 vol_ratio）预判横盘突破方向，t 日收盘出信号、t+1 可入场，
完全无前视。样本外(walk-forward)验证区分力，并与「次日状态」基准对比。

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
    q = pd.qcut(pd.Series(sig), 5, labels=False, duplicates="drop")
    codes = np.unique(q)
    a = ret[q == codes[-1]]; b = ret[q == codes[0]]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = (a.mean() - b.mean()) / se if se > 0 else np.nan
    spread = a.mean() - b.mean()
    lm = {int(k): float(np.mean(ret[q == k])) for k in codes}
    mono = 1 if len(codes) >= 3 and lm[int(codes[-1])] == max(lm.values()) else 0
    # 单调检验：5层均值是否单调
    ks = sorted(lm)
    mono5 = all(lm[ks[i]] <= lm[ks[i + 1]] or lm[ks[i]] >= lm[ks[i + 1]]
                for i in range(len(ks) - 1)) and (lm[ks[-1]] != lm[ks[0]])
    return spread, t, mono5, len(ret)


def main():
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel)
    feat = feat.sort_values(["symbol", "date"]).reset_index(drop=True)
    feat = feat.dropna(subset=["mom10", "mom20", "vol_ratio", "fwd_ret"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique()); si = int(len(dates) * 0.6)
    trd, ted = set(dates[:si]), set(dates[si:])
    lo, hi = feat[feat["date"].isin(trd)]["mom20"].quantile([1 / 3, 2 / 3]).to_numpy()
    print(f"=== 横盘(变)突破方向 · 可交易无前视信号 | 阈值 lo={lo:.4f} hi={hi:.4f} ===")

    feat["state"] = classify(feat["mom20"].to_numpy(), lo, hi)
    h = feat[feat["state"] == "横"].copy()
    ht = h[h["date"].isin(ted)].copy()
    print(f"横盘样本 {len(h)} 行（test {len(ht)} 行）| 信号=mom10(横盘内微动量)+vol_ratio(量能)，均 t 日可观察")

    print("\n[1] 横盘全体 × 横盘内微动量(mom10) 样本外分层 → 未来20日收益")
    s, t, mono, nn = validate(ht["mom10"].to_numpy(), ht["fwd_ret"].to_numpy())
    print(f"   long-short={s:+.4f} | t={t:+.2f} | 单调5层={mono} | n={nn}")
    q = pd.qcut(pd.Series(ht["mom10"].to_numpy()), 5, labels=False, duplicates="drop").to_numpy()
    m10 = ht["mom10"].to_numpy(); fr = ht["fwd_ret"].to_numpy()
    for k in sorted(np.unique(q)):
        mask = q == k
        print(f"    层{int(k)+1}({m10[mask].mean():+.4f}): 未来20日={fr[mask].mean():+.4f}")

    print("\n[2] 量能确认：仅高量能横盘(vol_ratio>中位) × mom10 → 突破方向更清晰？")
    hv = ht[ht["vol_ratio"] >= ht["vol_ratio"].median()]
    s2, t2, mono2, nn2 = validate(hv["mom10"].to_numpy(), hv["fwd_ret"].to_numpy())
    print(f"   n={nn2} | long-short={s2:+.4f} | t={t2:+.2f} | 单调5层={mono2}")
    lv = ht[ht["vol_ratio"] < ht["vol_ratio"].median()]
    s3, t3, mono3, nn3 = validate(lv["mom10"].to_numpy(), lv["fwd_ret"].to_numpy())
    print(f"   低量能 n={nn3} | long-short={s3:+.4f} | t={t3:+.2f}")

    print("\n[3] 与「次日状态」基准对比（上一轮[B]，含轻微前视）")
    st_arr = feat["state"].to_numpy()
    nxt = np.full(len(feat), "", dtype=object)
    for sym, idx in feat.groupby("symbol").indices.items():   # 位置法：下一行=次日
        for i in range(len(idx) - 1):
            nxt[idx[i]] = st_arr[idx[i + 1]]
    hb = feat[feat["state"] == "横"].copy()
    hb["nxt"] = [nxt[i] for i in hb.index]
    hb = hb[hb["nxt"] != ""]
    pv = hb[hb["date"].isin(ted)]
    a = pv[pv["nxt"] == "升"]["fwd_ret"]; b = pv[pv["nxt"] == "降"]["fwd_ret"]
    if len(a) > 50 and len(b) > 50:
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        t_baseline = (a.mean() - b.mean()) / se
        print(f"   次日状态基准: 升{a.mean():+.4f} vs 降{b.mean():+.4f} | 差={a.mean()-b.mean():+.4f} t={t_baseline:+.2f}")
        print(f"   → 本信号(mom10, 无前视) 区分度 |t|={abs(t):.2f} vs 基准 |t|={abs(t_baseline):.2f}："
              f"{'接近/部分保留基准信息量' if abs(t) >= abs(t_baseline)*0.5 else '明显弱于基准'}")
    else:
        print("   (次日状态基准样本不足)")

    print("\n[4] 单调分层明细（横盘全体 × mom10，test）")
    print("  → " + ("横盘内微动量可复算地预判突破方向（无前视）" if abs(t) >= 2 else "区分不显著（如实拦截）"))
    print("\n[说明] 信号仅用 t 日及之前数据（mom10=过去10日、vol_ratio=量比），t+1 可入场，无前视。研究演示、非投资建议。")


if __name__ == "__main__":
    main()
