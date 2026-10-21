# -*- coding: utf-8 -*-
"""
finance_fundamental.py — 基本面因子横截面验证（对比价量）
============================================================
针对"价量技术因子在 A 股样本外弱"的结论，接入基本面因子再测 alpha：
ROE / 净利率 / 毛利率 / 负债率 / 净利同比，按公告日(pubDate)前向对齐（避免前视），
构成横截面 → 三态状态机 → 样本外验证，与价量因子对比。

用法：  python3 finance_fundamental.py [--n 60]
数据：baostock 财务 + 复用 finance_full_panel（日K），研究演示·非投资建议
"""
import sys, time, random, socket
import numpy as np
import pandas as pd
import baostock as bs
import finance_cross as fc

socket.setdefaulttimeout(25)   # 防财务查询挂起拖死整池（25s 超时→跳过该查询，宁可少几只）

# 财务季度（最近 8 个完整季度）
QUARTERS = [(2024, q) for q in (1, 2, 3, 4)] + [(2025, q) for q in (1, 2, 3, 4)]
FUND_FEATURES = ["roeAvg", "npMargin", "gpMargin", "liabilityToAsset", "YOYNI"]


def fetch_fund(symbol: str):
    """拉取 symbol 最近若干季度的财务，返回 {pubDate: {指标}} 字典。"""
    out = {}
    for y, q in QUARTERS:
        try:
            rs = bs.query_profit_data(code=symbol, year=y, quarter=q)
            while rs.error_code == "0" and rs.next():
                row = dict(zip(rs.fields, rs.get_row_data()))
                out[row["pubDate"]] = {k: float(row[k]) if row[k] not in ("", None) else np.nan
                                       for k in ["roeAvg", "npMargin", "gpMargin"]}
            rs = bs.query_growth_data(code=symbol, year=y, quarter=q)
            while rs.error_code == "0" and rs.next():
                row = dict(zip(rs.fields, rs.get_row_data()))
                out.setdefault(row["pubDate"], {})["YOYNI"] = \
                    float(row["YOYNI"]) if row["YOYNI"] not in ("", None) else np.nan
            rs = bs.query_balance_data(code=symbol, year=y, quarter=q)
            while rs.error_code == "0" and rs.next():
                row = dict(zip(rs.fields, rs.get_row_data()))
                out.setdefault(row["pubDate"], {})["liabilityToAsset"] = \
                    float(row["liabilityToAsset"]) if row["liabilityToAsset"] not in ("", None) else np.nan
        except Exception:                       # noqa: BLE001
            continue
        time.sleep(0.03)
    return out


def align_fundamental(panel: pd.DataFrame, n_pool: int):
    """对 panel 的每只股票，按 pubDate 前向对齐财务到日频。返回含基本面列的长表。"""
    symbols = sorted(panel["symbol"].unique())
    random.seed(7)
    sample = random.sample(symbols, min(n_pool, len(symbols)))
    frames = []
    print(f"拉取 {len(sample)} 只股票财务…")
    for i, sym in enumerate(sample):
        fund = fetch_fund(sym)
        if not fund:
            continue
        fdf = pd.DataFrame(fund).T.reset_index()
        fdf = fdf.rename(columns={"index": "pubDate"})
        fdf["pubDate"] = pd.to_datetime(fdf["pubDate"])
        fdf = fdf.dropna(subset=["pubDate"]).sort_values("pubDate")
        # 与日K对齐：取 pubDate<=trade_date 的最新财务
        tr = panel[panel["symbol"] == sym][["date", "symbol", "close", "volume"]].copy()
        tr["date"] = pd.to_datetime(tr["date"])
        m = pd.merge_asof(tr.sort_values("date"), fdf.sort_values("pubDate"),
                          left_on="date", right_on="pubDate", direction="backward")
        frames.append(m)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(sample)}")
    if not frames:
        raise RuntimeError("无财务数据")
    return pd.concat(frames, ignore_index=True)


def main():
    args = sys.argv[1:]
    n = int(args[args.index("--n") + 1]) if "--n" in args else 60
    print("=== 基本面因子横截面验证（对比价量）===")
    panel = pd.read_csv("finance_full_panel_298stocks.csv")
    lg = bs.login()
    for _ in range(6):
        if lg.error_code == "0":
            break
        time.sleep(4); lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError("baostock 登录失败")

    t0 = time.time()
    fund = align_fundamental(panel, n)
    # 构造横截面长表：基本面 + 前向收益
    feat = fund.copy()
    feat = feat.sort_values(["symbol", "date"]).reset_index(drop=True)
    feat["fwd_ret"] = feat.groupby("symbol")["close"].shift(-20) / feat["close"] - 1.0
    feat = feat.dropna(subset=FUND_FEATURES + ["fwd_ret"])
    print(f"基本面面板：{len(feat)} 行 / {feat['symbol'].nunique()} 只，耗时 {time.time()-t0:.0f}s")
    feat.to_csv("finance_fund_feat_60.csv", index=False)   # 供 multi_agent 复用（含基本面+close/vol+fwd_ret）

    r_fund = fc.cross_walk_forward(feat, FUND_FEATURES)
    print()
    print("—— 基本面因子（ROE/净利率/毛利率/负债率/净利同比）——")
    print(fc.format_cross(r_fund))

    # 价量对照（同股票池）
    pv = fc.panel_features(panel)
    pv = pv[pv["symbol"].isin(feat["symbol"].unique())]
    r_pv = fc.cross_walk_forward(pv, ["mom20", "mom60", "rev5", "vol20", "vol_ratio"])
    print()
    print("—— 价量因子（同池对照）——")
    print(fc.format_cross(r_pv))

    bs.logout()
    print("\n[说明] 财务按公告日对齐（无前视）；研究演示、非投资建议。")


if __name__ == "__main__":
    main()
