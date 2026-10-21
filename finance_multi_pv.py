# -*- coding: utf-8 -*-
"""
finance_multi_pv.py — 阶段3 多Agent共识（价量版，无需财务）
============================================================
baostock 财务接口当前不稳定（登录反复失败+查询挂起），先用手头已有的
后复权+护栏全市场面板，把阶段3 的核心方法论跑通：
把 5 个价量特征视为 5 个独立 Agent，各自学『状态→未来收益』信号，
再按多Agent共识（等权平均 + 分歧降权）融合，对比『最优单一 vs 共识融合』。

用法：  python3 finance_multi_pv.py
数据：finance_full_panel_298stocks.csv（后复权+护栏），研究演示·非投资建议
"""
import numpy as np
import pandas as pd
import finance_cross as fc

PV_AGENTS = ["mom20", "mom60", "rev5", "vol20", "vol_ratio"]


def learn_agent_signal(df, feature, train_dates, min_n=25):
    """单特征(Agent) 学『三态→平均未来收益』信号。"""
    tri = fc.cross_trinary(df, [feature])[feature + "_tri"]
    df = df.copy()
    df["_st"] = tri
    tr = df[df["date"].isin(train_dates)]
    g = tr.groupby("_st")["fwd_ret"]
    s = pd.DataFrame({"n": g.count(), "mean": g.mean()})
    s = s[s["n"] >= min_n]
    return dict(zip(s.index, s["mean"]))


def main():
    print("=== 阶段3 多Agent共识融合（价量版，全市场298只，后复权+护栏）===")
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    feat = fc.panel_features(panel)
    feat = feat.sort_values(["symbol", "date"]).reset_index(drop=True)
    feat = feat.dropna(subset=PV_AGENTS + ["fwd_ret"]).reset_index(drop=True)
    dates = sorted(feat["date"].unique())
    si = int(len(dates) * 0.6)
    tr_dates, te_dates = set(dates[:si]), set(dates[si:])
    print(f"观测 {len(feat)} 行 | train {len(tr_dates)} 时点 / test {len(te_dates)} 时点 | 前向20日")

    # 各 Agent 学习信号 + 计算 test 信号
    agents = {}
    for f in PV_AGENTS:
        sig = learn_agent_signal(feat, f, tr_dates)
        tri = fc.cross_trinary(feat, [f])[f + "_tri"].to_numpy()
        agents[f] = (sig, tri)
    te_mask = feat["date"].isin(te_dates)
    te = feat[te_mask].copy()
    te_idx = te.index.to_numpy()
    # S[j,i] = 第 j 个 Agent 对 test 第 i 行的信号值
    S = np.array([[agents[f][0].get(agents[f][1][i], np.nan) for f in PV_AGENTS]
                  for i in te_idx])
    r = te["fwd_ret"].to_numpy()

    # 共识融合：各 Agent 信号 rank 标准化 → 等权平均；分歧（多数反向）降权
    R = np.apply_along_axis(lambda x: pd.Series(x).rank(pct=True).to_numpy(), 0, S)
    valid = ~np.isnan(S).any(axis=1)
    Rv = R[valid, :]; rv = r[valid]; Sv = S[valid, :]
    avg = Rv.mean(axis=1)                                   # 每样本对 5 Agent 的 rank 平均
    signs = np.sign(Sv - np.nanmean(Sv, axis=1, keepdims=True))
    n_oppose = (signs != signs[:, [0]]).sum(axis=1)         # 与第 1 个 Agent 反向的个数
    cons = avg.copy()
    cons[n_oppose >= 2] = avg[n_oppose >= 2] * 0.5          # 分歧≥2 → 降权

    print()
    # 单一最优 Agent
    best_t, best_name, best_spread, best_mono = -9, "", 0, 0
    for j, f in enumerate(PV_AGENTS):
        spread, t, mono, nn = _validate(Sv[:, j], rv)
        if t > best_t:
            best_t, best_name, best_spread, best_mono = t, f, spread, mono
        print(f"Agent[{f:<9}] long-short={spread:+.4f} | t={t:+.2f} | 单调={mono} | 覆盖={nn}")
    for name, col in [("共识融合(等权)", avg), ("共识融合(分歧降权)", cons)]:
        spread, t, mono, nn = _validate(col, rv)
        print(f"{name:<16} long-short={spread:+.4f} | t={t:+.2f} | 单调={mono} | 覆盖={nn}")
    print(f"\n最优单一 Agent: {best_name} (t={best_t:+.2f})")
    print("[说明] 后复权+护栏；研究演示、非投资建议。")


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
    layer_mean = {int(k): float(np.mean(ret[q == k])) for k in codes}
    mono = 1 if len(codes) >= 3 and layer_mean[int(codes[-1])] == max(layer_mean.values()) else 0
    return spread, t, mono, len(ret)


if __name__ == "__main__":
    main()
