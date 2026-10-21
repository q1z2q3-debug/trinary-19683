# -*- coding: utf-8 -*-
"""
finance_pull_extend.py — baostock 价量扩池延史（后复权+护栏）【断点续拉+单只超时】
============================================================
拉沪深300成分股 2018-01-01 至今 后复权价量。单只 30s 超时跳过（防挂起），
已成功股票断点跳过（复用 finance_panel_ext_hs300.csv 存量）。
用法：python finance_pull_extend.py [n]   （n 可选限拉取数量，测试用）
数据：baostock，研究演示·非投资建议
"""
import sys
import os
import signal
import time
import numpy as np
import pandas as pd
import baostock as bs

START, END = "2018-01-01", "2026-10-20"
OUT = "finance_panel_ext_hs300.csv"
TIME_LIMIT = 30


class _Timeout(Exception):
    pass


def _handler(s, f):
    raise _Timeout()


def login():
    for i in range(5):
        try:
            lg = bs.login()
        except Exception:
            lg = None
        if lg is not None and lg.error_code == "0":
            return True
        print(f"login 失败，重试…")
        time.sleep(4)
    return False


def pull(code, start, end):
    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(TIME_LIMIT)
    try:
        rs = bs.query_history_k_data_plus(
            code, "date,code,close,volume", start_date=start, end_date=end,
            frequency="d", adjustflag="1")
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        if rs.error_code != "0":
            return None
        return pd.DataFrame(rows, columns=["date", "symbol", "close", "volume"])
    except _Timeout:
        print(f"    [超时跳过] {code}")
        return None
    finally:
        signal.alarm(0)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    done = set()
    if os.path.exists(OUT):
        try:
            done = set(pd.read_csv(OUT)["symbol"])
            print(f"断点：已有 {len(done)} 只，跳过")
        except Exception:
            done = set()
    if not login():
        print("baostock 登录失败"); return
    rs = bs.query_hs300_stocks()
    codes = list(rs.get_data()["code"]) if rs.error_code == "0" else []
    if n:
        codes = codes[:n]
    todo = [c for c in codes if c not in done]
    print(f"需拉 {len(todo)} 只（共{len(codes)}，hs300） {START}~{END} 后复权")

    frames = [pd.read_csv(OUT)] if done and os.path.exists(OUT) else []
    frames = [f for f in frames if not f.empty]
    ok = len(done)
    for i, c in enumerate(todo, 1):
        df = pull(c, START, END)
        if df is not None and not df.empty:
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            df = df[(df["close"] > 0) & (df["volume"] >= 0)]
            frames.append(df); ok += 1
            # 逐只落盘，防中途挂断丢全部
            pd.concat(frames).to_csv(OUT, index=False)
        if i % 20 == 0:
            print(f"  {i}/{len(todo)} 完成（累计成功 {ok}）")
        time.sleep(0.1)
    if not frames:
        print("全部失败"); bs.logout(); return
    out = pd.concat(frames).reset_index(drop=True)
    out.to_csv(OUT, index=False)
    print(f"\n完成：{out['symbol'].nunique()} 只 / {len(out)} 行 / "
          f"{out['date'].min()}~{out['date'].max()}")
    bs.logout()


if __name__ == "__main__":
    main()
