# -*- coding: utf-8 -*-
"""
fetch_and_run.py — 用腾讯金融真实行情，完整跑通 finance_state 阶段0+1
数据来源：腾讯行情接口（web.ifzq.gtimg.cn，公开免费）
用法：
  python3 fetch_and_run.py                 # 默认 沪深300
  python3 fetch_and_run.py sh600519        # 指定标的（腾讯代码）
  python3 fetch_and_run.py --multi         # 多标的对比
口径：研究用途，不构成投资建议；不承诺收益。
"""
import json, sys, time, urllib.request
import pandas as pd
import numpy as np
import finance_state as fs

N_BARS = 600
FWD_HOLD = 5
FEATURES = ["mom5", "mom20", "vol10", "rsi14", "vol_ratio"]

# 多标的对比预设
MULTI = [
    ("sh000300", "沪深300"),
    ("sh000905", "中证500"),
    ("sz399006", "创业板指"),
    ("sh600519", "贵州茅台"),
]


def fetch_tencent_kline(symbol: str, n_bars: int = N_BARS):
    """拉取腾讯日K，返回 DataFrame[date, open, close, high, low, volume]。带重试。"""
    # hfq=后复权(价格恒正)；前复权(qfq)长期会把早期价格推成负价，导致涨跌幅假象
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?param={symbol},day,,,{n_bars},hfq")
    import time
    last = None
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:          # noqa: BLE001
            last = e
            time.sleep(1.0)
    else:
        raise RuntimeError(f"拉取 {symbol} 失败: {last}")
    node = d["data"][symbol]
    rows = node.get("hfqday") or node.get("day")
    df = pd.DataFrame([r[:6] for r in rows],
                      columns=["date", "open", "close", "high", "low", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for c in ["open", "close", "high", "low", "volume"]:
        df[c] = df[c].astype(float)
    return df


def build_features(df: pd.DataFrame, fwd_hold: int = 5):
    """构造特征 + 前向收益。全部只用当期及之前数据（无前视）。"""
    close = df["close"]; vol = df["volume"]
    out = df[["date", "close"]].copy()
    out["mom5"] = close.pct_change(5)                      # 5日动量
    out["mom20"] = close.pct_change(20)                    # 20日动量
    out["vol10"] = close.pct_change().rolling(10).std()    # 10日波动
    out["rsi14"] = rsi(close, 14)                          # RSI
    out["vol_ratio"] = vol / vol.rolling(20).mean()        # 量比
    # 前向收益（未来 fwd_hold 日）
    out["fwd_ret"] = close.shift(-fwd_hold) / close - 1.0
    return out


def rsi(close: pd.Series, n: int = 14):
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = (-delta.clip(upper=0)).rolling(n).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def run_one(symbol: str, name: str, verbose: bool = True):
    """对单个标的全流程跑通，返回关键指标 dict。"""
    df = fetch_tencent_kline(symbol)
    feat = build_features(df, FWD_HOLD).set_index("date").dropna()
    report = fs.walk_forward(
        feat, features=FEATURES, return_col="fwd_ret",
        window=30, min_samples=5, train_frac=0.6, n_layers=5,
    )
    if "error" in report:
        print(f"  {name}({symbol}): 错误 {report['error']}")
        return None
    if verbose:
        print(f"\n===== {name} ({symbol}) =====")
        print(f"  数据: {len(report['n_rows'])} 行 ({feat.index[0].date()} ~ {feat.index[-1].date()}) | "
              f"状态空间 {report['state_space']} | train 观测 {report['states_observed_train']} 状态")
        for f, v in report["features_ic"].items():
            print(f"  IC {f:<9} = {v:+.4f}" if v == v else f"  IC {f:<9} = 样本不足")
        print(f"  样本外 top-bottom 收益差 {report['spread_top_bottom']:+.4f} | "
              f"t={report['t_top_bottom']:+.2f} | 分层单调={report['layer_monotonic']}")
    return {
        "symbol": symbol, "name": name, "n_rows": report["n_rows"],
        "state_space": report["state_space"], "states_seen": report["states_observed_train"],
        "ic_mom5": report["features_ic"].get("mom5"),
        "ic_mom20": report["features_ic"].get("mom20"),
        "ic_rsi14": report["features_ic"].get("rsi14"),
        "spread": report["spread_top_bottom"], "t": report["t_top_bottom"],
        "mono": report["layer_monotonic"],
    }


def main():
    args = sys.argv[1:]
    if "--multi" in args:
        print("=== 多标的对比（腾讯真实行情，前复权日K，前向5日收益）===")
        results = []
        for i, (sym, name) in enumerate(MULTI):
            if i > 0:
                time.sleep(0.8)
            r = run_one(sym, name, verbose=False)
            if r:
                results.append(r)
        print(f"\n{'标的':<10}{'样本':>6}{'状态空间':>8}{'观测状态':>8}"
              f"{'IC_mom5':>10}{'IC_mom20':>10}{'IC_rsi':>9}{'spread':>9}{'t':>7}{'单调':>5}")
        for r in results:
            ic5 = f"{r['ic_mom5']:+.3f}" if r["ic_mom5"] == r["ic_mom5"] else "  -  "
            ic20 = f"{r['ic_mom20']:+.3f}" if r["ic_mom20"] == r["ic_mom20"] else "  -  "
            icr = f"{r['ic_rsi14']:+.3f}" if r["ic_rsi14"] == r["ic_rsi14"] else "  -  "
            t = f"{r['t']:+.2f}" if r["t"] == r["t"] else "  - "
            print(f"{r['name']:<10}{r['n_rows']:>6}{r['state_space']:>8}{r['states_seen']:>8}"
                  f"{ic5:>10}{ic20:>10}{icr:>9}{r['spread']:+.4f}{t:>7}{r['mono']:>5}")
        print("\n判定线：样本外 |t|≥2 且 单调=1 → 该标的该组特征有状态区分度")
        print("（区分度不足 = 框架如实拦截，这正是价值所在，避免无效信号强行上线）")
        return

    symbol = args[0] if args else "sh000300"
    name = {"sh000300": "沪深300", "sh000905": "中证500",
            "sz399006": "创业板指", "sh600519": "贵州茅台"}.get(symbol, symbol)
    df = fetch_tencent_kline(symbol)
    feat = build_features(df, FWD_HOLD).set_index("date").dropna()
    feat.to_csv(f"finance_tencent_{symbol}.csv")
    r = run_one(symbol, name, verbose=True)
    print(f"\n已存: finance_tencent_{symbol}.csv")
    print("[数据说明] 来源腾讯行情公开接口，前复权日K；研究演示，非投资建议。")


if __name__ == "__main__":
    main()
