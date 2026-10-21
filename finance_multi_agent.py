# -*- coding: utf-8 -*-
"""
finance_multi_agent.py — 阶段3 多因子共识（复用多Agent设计）
============================================================
把「基本面(alpha)」与「价量(反向/状态分层)」两个信号当作两个 Agent，
用多Agent共识思想融合：冲突检测（两信号反向）→ 分歧处理 → 可复算共识，
对比 单一基本面 / 单一价量 / 共识融合 三路的样本外表现。

用法：  python3 finance_multi_agent.py [--n 60]
数据：baostock 后复权面板 + 财务（公告日对齐，无前视），研究演示·非投资建议
"""
import sys, time, os, socket
import numpy as np
import pandas as pd
import finance_cross as fc
import finance_fundamental as ff

socket.setdefaulttimeout(60)          # 防挂起但不过度跳过慢查询（20s 太激进导致池变小）

FUND_F = ff.FUND_FEATURES                                   # 基本面特征
PV_F = ["mom20", "mom60", "rev5", "vol20", "vol_ratio"]     # 价量特征
FEAT_CACHE = "finance_fund_feat_60.csv"                     # 双因子面板缓存


def add_price_features(feat):
    """给含 close/volume 的面板叠加价量特征（供缓存复用分支）。"""
    c = feat["close"]; v = feat["volume"]
    for f, p in [("mom10", 10), ("mom20", 20), ("mom40", 40), ("mom60", 60)]:
        feat[f] = c.pct_change(p)
    feat["rev5"] = c.shift(5) / c - 1.0
    for w in [5, 20, 40]:
        feat[f"vol{w}"] = c.pct_change().rolling(w).std()
    feat["vol_ratio"] = v / v.rolling(20).mean()
    for f in PV_F:
        feat[f] = feat[f].where(np.isfinite(feat[f]))
    return feat


def build_dual_panel(panel, n):
    """财务对齐 → 叠加价量特征 → 返回含基本面+价量+前向收益的长表。"""
    fund = ff.align_fundamental(panel, n)                    # 需 baostock 登录
    feat = fund.sort_values(["symbol", "date"]).reset_index(drop=True)
    feat = add_price_features(feat)
    feat["fwd_ret"] = feat.groupby("symbol")["close"].shift(-20) / feat["close"] - 1.0
    # 护栏：非有限值置 nan
    for f in FUND_F + PV_F + ["fwd_ret"]:
        feat[f] = feat[f].where(np.isfinite(feat[f]))
    return feat.dropna(subset=FUND_F + ["fwd_ret"]).reset_index(drop=True)


def learn_signal(df, features, train_dates, min_samples=20):
    """train 段学『状态→平均未来收益』信号，返回 (state_signal_dict, state_col)。"""
    tri = fc.cross_trinary(df, features)
    st = fc.state_number(tri[[f + "_tri" for f in features]].to_numpy().T)
    df = df.assign(**{features[0] + "_st": st})     # 暂存状态（单列）
    tr = df[df["date"].isin(train_dates)]
    grp = tr.groupby(st)["fwd_ret"]
    sig = pd.DataFrame({"n": grp.count(), "mean": grp.mean()})
    sig = sig[sig["n"] >= min_samples]
    return dict(zip(sig.index, sig["mean"])), st


def main():
    args = sys.argv[1:]
    n = int(args[args.index("--n") + 1]) if "--n" in args else 60
    print(f"=== 阶段3 多因子共识 · {n} 只（基本面 vs 价量 vs 融合）===")
    panel = pd.read_csv("finance_full_panel_298stocks.csv")

    if os.path.exists(FEAT_CACHE):                       # 复用缓存面板，跳过拉财务
        feat = pd.read_csv(FEAT_CACHE)
        feat = add_price_features(feat)                  # 缓存含基本面+fwd_ret，补价量特征
        print(f"复用缓存 {FEAT_CACHE}（{len(feat)} 行，补价量特征）")
    else:
        lg = ff.bs.login()
        for _ in range(6):
            if lg.error_code == "0":
                break
            time.sleep(4); lg = ff.bs.login()
        if lg.error_code != "0":
            raise RuntimeError("baostock 登录失败")
        feat = build_dual_panel(panel, n)
        feat.to_csv(FEAT_CACHE, index=False)
        ff.bs.logout()
        print(f"双因子面板：{len(feat)} 行 / {feat['symbol'].nunique()} 只（已缓存 {FEAT_CACHE}）")

    dates = sorted(feat["date"].unique())
    si = int(len(dates) * 0.6)
    tr_dates, te_dates = set(dates[:si]), set(dates[si:])

    # 两个 Agent 的状态信号
    tri_f = fc.cross_trinary(feat, FUND_F)
    st_f = fc.state_number(tri_f[[f + "_tri" for f in FUND_F]].to_numpy().T)
    tri_p = fc.cross_trinary(feat, PV_F)
    st_p = fc.state_number(tri_p[[f + "_tri" for f in PV_F]].to_numpy().T)
    tr_mask = feat["date"].isin(tr_dates)
    sig_f = _learn(feat[tr_mask], st_f[tr_mask], "fwd_ret")
    sig_p = _learn(feat[tr_mask], st_p[tr_mask], "fwd_ret")

    te = feat[feat["date"].isin(te_dates)].copy()
    te_idx = te.index.to_numpy()
    te["sig_f"] = [sig_f.get(st_f[i], np.nan) for i in te_idx]
    te["sig_p"] = [sig_p.get(st_p[i], np.nan) for i in te_idx]
    te = te.dropna(subset=["sig_f", "sig_p", "fwd_ret"])

    # 共识融合：两信号各自 rank 标准化 → 等权平均
    rf = te["sig_f"].rank(pct=True).to_numpy()
    rp = te["sig_p"].rank(pct=True).to_numpy()
    te["sig_avg"] = (rf + rp) / 2.0
    # 冲突检测：两信号方向相反且幅度都大 → 分歧（降权）
    conflict = ((te["sig_f"] - te["sig_f"].mean()) * (te["sig_p"] - te["sig_p"].mean()) < 0).to_numpy()
    te["sig_cons"] = te["sig_avg"].copy()
    te.loc[conflict, "sig_cons"] = te["sig_avg"][conflict] * 0.5    # 分歧降权

    print()
    for name, col in [("基本面(单一)", "sig_f"), ("价量(单一)", "sig_p"),
                      ("共识融合(avg)", "sig_avg"), ("共识融合(分歧降权)", "sig_cons")]:
        r = _validate(te, col)
        print(f"{name:<16} long-short={r['spread']:+.4f} | t={r['t']:+.2f} | 单调={r['mono']} | 覆盖={r['n']}")
    print()
    print("[说明] 财务公告日对齐无前视；后复权+护栏；研究演示、非投资建议。")


def _learn(tr, states, ret_col):
    df = pd.DataFrame({"st": states, "ret": tr[ret_col].to_numpy()}).dropna()
    g = df.groupby("st")["ret"]
    s = pd.DataFrame({"n": g.count(), "mean": g.mean()})
    s = s[s["n"] >= 20]
    return dict(zip(s.index, s["mean"]))


def _validate(te, col):
    s = te[col].to_numpy(); r = te["fwd_ret"].to_numpy()
    m = ~(np.isnan(s) | np.isnan(r))
    s, r = s[m], r[m]
    if len(r) < 100:
        return {"spread": np.nan, "t": np.nan, "mono": 0, "n": len(r)}
    q = pd.qcut(pd.Series(s), 5, labels=False, duplicates="drop")
    codes = np.unique(q)
    layer = {int(k) + 1: float(np.mean(r[q == k])) for k in codes}
    top, bot = codes[-1], codes[0]
    a = r[q == top]; b = r[q == bot]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = (a.mean() - b.mean()) / se if se > 0 else np.nan
    spread = layer[int(top) + 1] - layer[int(bot) + 1]
    mono = 1 if len(codes) >= 3 and layer[int(top) + 1] == max(layer.values()) else 0
    return {"spread": spread, "t": t, "mono": mono, "n": len(r)}


if __name__ == "__main__":
    main()
