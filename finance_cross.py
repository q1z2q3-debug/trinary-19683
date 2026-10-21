# -*- coding: utf-8 -*-
"""
finance_cross.py — 三元九维19683 金融落地 · 横截面（选股）版
============================================================
单标的时序信号弱 → 改横截面：同一时点取多只股票，状态 = 横截面特征组合，
让 19683 状态空间在大量『股票×时点』样本上真正吃饱，验证多空区分度。

数据：腾讯行情公开接口，股票池日K（前复权），研究演示、非投资建议、不承诺收益。

用法：  python3 finance_cross.py [--pool small|mid] [--features 5|9]
"""
from __future__ import annotations
import json, sys, time, urllib.request
import numpy as np
import pandas as pd

D, R, T = 0, 1, 2
FWD_HOLD = 20          # 前向20日（月频，信号更强）
MIN_SAMPLES = 20
TRAIN_FRAC = 0.6
N_LAYERS = 5

# 股票池（行业龙头，示例池，非全市场）
POOL_SMALL = [  # 24 只
    "sh600519", "sh600036", "sh600030", "sh601318", "sh600900",
    "sh601857", "sh600028", "sh601988", "sh601398", "sh601288",
    "sh601939", "sh600000", "sh600276", "sh600887", "sh600809",
    "sz000858", "sz000333", "sz000651", "sz002415", "sz002594",
    "sz300750", "sh601012", "sz002475", "sz000725",
]
POOL_MID = [  # 50 只
    "sh600519", "sh600036", "sh600030", "sh601318", "sh600900",
    "sh601857", "sh600028", "sh601988", "sh601398", "sh601288",
    "sh601939", "sh600000", "sh600016", "sh601166", "sh601328",
    "sh600276", "sh600887", "sh603288", "sh600809", "sz000858",
    "sz000333", "sz000651", "sz002415", "sz002594", "sz300750",
    "sh601012", "sh600438", "sz002475", "sz000725", "sh600031",
    "sh601899", "sh600309", "sh601088", "sh600104", "sh601668",
    "sh600585", "sz002714", "sh600690", "sz000002", "sh601888",
    "sh600050", "sh601728", "sh600941", "sz000001", "sh601601",
    "sh601628", "sh600048", "sz000063", "sz002230", "sz300059",
]


def fetch_kline(symbol: str, n: int = 260):
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?param={symbol},day,,,{n},qfq")
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except Exception:                       # noqa: BLE001
            time.sleep(1.0)
    else:
        return None
    node = d["data"][symbol]
    rows = node.get("qfqday") or node.get("day")
    if not rows:
        return None
    df = pd.DataFrame([r[:6] for r in rows],
                      columns=["date", "open", "close", "high", "low", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "close", "high", "low", "volume"]:
        df[c] = df[c].astype(float)
    df["symbol"] = symbol
    return df[["date", "symbol", "close", "volume"]]


def build_panel(symbols):
    """拉取股票池 → 逐只日K → 长表 panel[date, symbol, close, volume]。"""
    frames = []
    ok = 0
    for i, s in enumerate(symbols):
        df = fetch_kline(s)
        if df is not None and len(df) > 100:
            frames.append(df); ok += 1
        if i % 10 == 9:
            time.sleep(0.5)
        time.sleep(0.2)
    if not frames:
        raise RuntimeError("股票池全部拉取失败")
    panel = pd.concat(frames, ignore_index=True)
    print(f"  拉取成功 {ok}/{len(symbols)} 只")
    return panel


def panel_features(panel: pd.DataFrame):
    """逐股票计算特征 + 前向收益，返回长表。"""
    panel = panel.sort_values(["symbol", "date"])
    feat_list = []
    # 非正价护栏：剔除 close<=0 或 volume<0（前复权负价/零价会污染全部比率特征）
    panel = panel[panel["close"] > 0]
    panel = panel[panel["volume"].fillna(0) >= 0]
    for sym, g in panel.groupby("symbol"):
        g = g.sort_values("date").reset_index(drop=True)
        c = g["close"]; v = g["volume"]
        g = g.assign(
            mom10=c.pct_change(10),
            mom20=c.pct_change(20),
            mom40=c.pct_change(40),
            mom60=c.pct_change(60),
            rev5=(c.shift(5) / c - 1.0),          # 5日反转
            vol5=c.pct_change().rolling(5).std(),
            vol20=c.pct_change().rolling(20).std(),
            vol40=c.pct_change().rolling(40).std(),
            vol_ratio=v / v.rolling(20).mean(),
            fwd_ret=c.shift(-FWD_HOLD) / c - 1.0,
        )
        # 分母护栏：任何比率/收益特征非有限值(inf/-inf)一律置 nan，避免假涨跌
        for f in ["mom10", "mom20", "mom40", "mom60", "rev5", "vol5", "vol20", "vol40",
                  "vol_ratio", "fwd_ret"]:
            g[f] = g[f].where(np.isfinite(g[f]))
        feat_list.append(g)
    return pd.concat(feat_list, ignore_index=True).dropna(subset=["mom60", "fwd_ret"])


def cross_trinary(df: pd.DataFrame, features):
    """每个时点，对每个特征在『当日横截面』三分位 → D/R/T。无前视（仅用当日截面）。"""
    tri = pd.DataFrame(index=df.index)
    for f in features:
        p = df.groupby("date")[f].rank(pct=True)     # 当日截面百分位，0~1
        tri[f + "_tri"] = np.where(p < 1/3, D, np.where(p >= 2/3, T, R)).astype(int)
    return tri


def state_number(tri_arr):
    n_dims = tri_arr.shape[0]
    weights = (3 ** np.arange(n_dims))[None, :]
    return (tri_arr.T * weights).sum(axis=1).astype(int)


def _spearman(a, b):
    m = ~(np.isnan(a) | np.isnan(b))
    a, b = a[m], b[m]
    if len(a) < 5 or np.unique(a).size < 2 or np.unique(b).size < 2:
        return float("nan")
    ra = pd.Series(a).rank().to_numpy(); rb = pd.Series(b).rank().to_numpy()
    ra -= ra.mean(); rb -= rb.mean()
    den = np.sqrt((ra**2).sum() * (rb**2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def _t(a, b):
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    ma, mb = a.mean(), b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((ma - mb) / se) if se > 0 else float("nan")


def cross_walk_forward(df, features, min_samples=MIN_SAMPLES,
                       train_frac=TRAIN_FRAC, n_layers=N_LAYERS):
    """横截面样本外验证。train 时点学『状态信号』，test 时点按信号分层多空。"""
    tri = cross_trinary(df, features)
    st = state_number(tri[[f + "_tri" for f in features]].to_numpy().T)
    df = df.assign(state=st, signal=np.nan)

    dates = sorted(df["date"].unique())
    split_i = int(len(dates) * train_frac)
    train_dates, test_dates = set(dates[:split_i]), set(dates[split_i:])

    # train：状态 → 平均未来收益
    tr = df[df["date"].isin(train_dates)]
    grp = tr.groupby("state")["fwd_ret"]
    sig_tbl = pd.DataFrame({"n": grp.count(), "mean": grp.mean()})
    sig_tbl = sig_tbl[sig_tbl["n"] >= min_samples]
    signal = dict(zip(sig_tbl.index, sig_tbl["mean"]))

    # test：每行映射信号
    te = df[df["date"].isin(test_dates)].copy()
    te["signal"] = te["state"].map(signal)
    te = te.dropna(subset=["signal", "fwd_ret"])

    # 横截面 IC：每个时点 信号 vs 收益 的 spearman，按时点平均
    xic = []
    for dt, g in te.groupby("date"):
        ic = _spearman(g["signal"].to_numpy(), g["fwd_ret"].to_numpy())
        if ic == ic:
            xic.append(ic)
    ic_mean = float(np.mean(xic)) if xic else float("nan")

    # 多空分层：按信号分 n_layers，各层 test 收益
    if len(te) >= n_layers * 20:
        layer_of = pd.qcut(te["signal"], n_layers, labels=False, duplicates="drop")
        codes = np.unique(layer_of)
        layer_ret = {int(k) + 1: float(te.loc[layer_of == k, "fwd_ret"].mean())
                     for k in codes}
        tc, bc = codes[-1], codes[0]
        long = te.loc[layer_of == tc, "fwd_ret"].to_numpy()
        short = te.loc[layer_of == bc, "fwd_ret"].to_numpy()
        spread = layer_ret[int(tc) + 1] - layer_ret[int(bc) + 1]
        tval = _t(long, short)
        mono = 1 if len(codes) >= 3 and layer_ret[int(tc) + 1] == max(layer_ret.values()) else 0
    else:
        layer_ret, spread, tval, mono = {}, float("nan"), float("nan"), 0

    return {
        "n_obs": int(len(df)), "n_train_dates": split_i,
        "n_test_dates": len(dates) - split_i, "n_stocks": int(df["symbol"].nunique()),
        "n_features": len(features), "state_space": 3 ** len(features),
        "states_seen_train": int(len(sig_tbl)),
        "cross_ic_mean": ic_mean, "n_ic_days": len(xic),
        "layers_return": layer_ret, "spread_long_short": spread,
        "t_long_short": tval, "monotonic": mono,
        "conclusion": [],
    }


def format_cross(r):
    L = []
    L.append("=== 三元九维19683 · 横截面(选股) 样本外验证 ===")
    L.append(f"观测 {r['n_obs']} 行 | {r['n_stocks']} 只股票 | train {r['n_train_dates']} 时点 / "
             f"test {r['n_test_dates']} 时点 | 前向 {FWD_HOLD} 日")
    L.append(f"状态机: {r['n_features']} 维 → 状态空间 {r['state_space']} | "
             f"train 观测 {r['states_seen_train']} 状态 | 样本外横截面IC均值 {r['cross_ic_mean']:+.4f} ({r['n_ic_days']} 日)")
    L.append(f"样本外多空分层（按 train 状态信号，test 各层平均前向收益）：")
    for k in sorted(r["layers_return"]):
        L.append(f"  层{k}: {r['layers_return'][k]:+.4f}")
    L.append(f"  long-short 收益差 = {r['spread_long_short']:+.4f} | t={r['t_long_short']:+.2f} | 单调={r['monotonic']}")
    if r["spread_long_short"] == r["spread_long_short"] and abs(r["t_long_short"]) >= 2:
        L.append("结论：样本外 long-short 区分度显著成立")
    else:
        L.append("结论：样本外区分度不显著（|t|<2）——如实拦截，请换特征/扩大股票池/调参")
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    pool = POOL_MID if "--pool" in args and "mid" in args else POOL_SMALL
    features = ["mom20", "mom60", "rev5", "vol20", "vol_ratio"]
    if "--features" in args:
        n = args[args.index("--features") + 1]
        if n == "9":
            # 用 9 维近似：加入滞后动量/波动分解等 → 19683 状态空间
            features = ["mom20", "mom60", "rev5", "vol20", "vol_ratio",
                        "mom10", "mom40", "vol5", "vol40"]
    print(f"=== 横截面验证 · 股票池 {len(pool)} 只 · 特征 {len(features)} 维"
          f"（{'19683 状态空间' if len(features)==9 else str(3**len(features))}）===")
    panel = build_panel(pool)
    feat = panel_features(panel)
    print(f"  面板就绪：{len(feat)} 行")
    r = cross_walk_forward(feat, features)
    print()
    print(format_cross(r))
    print("\n[说明] 腾讯公开行情、前复权、研究演示、非投资建议。")


if __name__ == "__main__":
    main()
