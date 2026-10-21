# -*- coding: utf-8 -*-
"""
finance_full.py — 三元九维19683 金融落地 · 方案A 全市场横截面
============================================================
数据源：baostock（免费、官方、无token）。全市场股票列表 → 均匀抽样 N 只 →
拉日K（前复权）→ 面板 → 复用 finance_cross 的横截面验证。

用法：  python3 finance_full.py [--n 300] [--features 5|9]
"""
import sys, time, random
import numpy as np
import pandas as pd
import baostock as bs
import finance_cross as fc

START, END = "2023-06-01", "2026-10-16"


def is_stock(code: str) -> bool:
    m, num = code.split(".")
    if m == "sh" and (num.startswith("60") or num.startswith("68")):
        return True
    if m == "sz" and (num.startswith("00") or num.startswith("30")):
        return True
    return False


def all_stock_codes():
    rs = bs.query_all_stock(day=END)
    codes = []
    while rs.error_code == "0" and rs.next():
        codes.append(rs.get_row_data()[0])
    return [c for c in codes if is_stock(c)]


def fetch_history(code: str):
    # adjustflag: 1=后复权(价格恒正)；2=前复权(长期会把早期价格推成负价，导致涨跌幅假象)
    rs = bs.query_history_k_data_plus(
        code, "date,close,volume", start_date=START, end_date=END,
        frequency="d", adjustflag="1")
    rows = []
    while rs.error_code == "0" and rs.next():
        d, c, v = rs.get_row_data()
        try:
            cf, vf = float(c), float(v)
        except ValueError:                # 停牌/空值日，跳过
            continue
        if cf <= 0:                       # 非正价护栏：剔除
            continue
        rows.append((d, code, cf, vf))
    return rows


def build_panel(codes: list, max_rows_per_stock: int = 300):
    frames = []
    ok = 0
    for i, code in enumerate(codes):
        rows = fetch_history(code)
        if len(rows) >= 150:
            rows = rows[-max_rows_per_stock:]
            frames.append(pd.DataFrame(rows, columns=["date", "symbol", "close", "volume"]))
            ok += 1
        if (i + 1) % 50 == 0:
            print(f"  进度 {i+1}/{len(codes)}，成功 {ok} 只")
    if not frames:
        raise RuntimeError("无有效股票")
    return pd.concat(frames, ignore_index=True), ok


def main():
    args = sys.argv[1:]
    n = 300
    if "--n" in args:
        n = int(args[args.index("--n") + 1])
    features = ["mom20", "mom60", "rev5", "vol20", "vol_ratio"]
    if "--features" in args and args[args.index("--features") + 1] == "9":
        features = ["mom20", "mom60", "rev5", "vol20", "vol_ratio",
                    "mom10", "mom40", "vol5", "vol40"]

    print(f"baostock 登录…")
    lg = bs.login()
    for _ in range(6):                     # 服务端偶发限流，重试
        if lg.error_code == "0":
            break
        print(f"  登录失败({lg.error_code})，{4}s 后重试…")
        time.sleep(4)
        lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {lg.error_code} {lg.error_msg}")
    print("  登录成功")
    codes = all_stock_codes()
    print(f"全市场股票数: {len(codes)} → 抽样 {n} 只（均匀）")
    random.seed(42)
    sample = random.sample(codes, min(n, len(codes)))

    t0 = time.time()
    panel, ok = build_panel(sample)
    print(f"面板就绪: {len(panel)} 行 / {ok} 只，耗时 {time.time()-t0:.0f}s")

    feat = fc.panel_features(panel)
    print(f"特征构造: {len(feat)} 行（特征 {len(features)} 维，状态空间 {3**len(features)}）")

    r = fc.cross_walk_forward(feat, features)
    print()
    print(fc.format_cross(r))

    panel.to_csv(f"finance_full_panel_{ok}stocks.csv", index=False)
    print(f"\n已存: finance_full_panel_{ok}stocks.csv")
    print("[说明] baostock 免费公开数据、后复权(恒正)+非正价护栏、研究演示、非投资建议。")
    bs.logout()


if __name__ == "__main__":
    main()
