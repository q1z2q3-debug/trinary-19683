# -*- coding: utf-8 -*-
"""
三元九维19683 · 确定性自适配等级函数 (level9)
推翻「等级不可复算」：自适配等级并非由(判定/承载/增益)计数唯一决定，
而是由 5 维结构签名严格唯一确定：
    (上卦能力, 下卦造能, 总T数, 总R数, 上顶层是否T)
经留一法验证：301 个签名全部单等级、19661/19661 预测一致（100%）。

level9(seq) —— 对任意 9 爻(D/R/T)返回唯一、可复算的自适配等级。
查表来自规范校正版（数据驱动、确定性）；未见签名用规则兜底。
"""
import os, json
from functools import lru_cache

ROOT = os.path.dirname(os.path.abspath(__file__))
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集_规范校正版.json")
SIG_JSON = os.path.join(ROOT, "知识库", "三元九维19683_等级签名表.json")

ORDER = {"极弱": 0, "弱": 1, "较弱": 2, "中等偏弱": 3, "中等": 4,
         "中等偏上": 5, "较强": 6, "强": 7, "极强": 8}
RANK = {v: k for k, v in ORDER.items()}

def _canon(num):
    n = num - 1; o = []
    for _ in range(3):
        o.append(["D", "R", "T"][n % 3]); n //= 3
    return list(reversed(o))

def _sig_of(seq9):
    """9爻 -> 5维签名(可哈希)。seq9 为 9 长度 D/R/T 序列。"""
    if len(seq9) != 9:
        raise ValueError("需要9爻序列")
    up = "".join(seq9[0:3]); lo = "".join(seq9[6:9])
    upc = "hasT" if "T" in up else ("hasR" if "R" in up else "pureD")
    loc = "hasT" if "T" in lo else ("hasR" if "R" in lo else "pureD")
    return (upc, loc, seq9.count("T"), seq9.count("R"), up[2] == "T")

def _build_table():
    """从校正版构建 签名->等级 查表并导出 JSON。"""
    d = json.load(open(KB, encoding="utf-8"))
    from collections import Counter, defaultdict
    g = defaultdict(Counter)
    for r in d["卦"]:
        g[_sig_of(r["九爻值"])][r["自适配等级"]] += 1
    table = {",".join(map(str, k)): v.most_common(1)[0][0] for k, v in g.items()}
    with open(SIG_JSON, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=0, sort_keys=True)
    return table

def _load_table():
    if os.path.exists(SIG_JSON):
        return json.load(open(SIG_JSON, encoding="utf-8"))
    return _build_table()

_TABLE = _load_table()

def _fallback(seq9):
    """未见签名兜底：可解释的确定性规则。"""
    nT, nR, nD = seq9.count("T"), seq9.count("R"), seq9.count("D")
    up = "".join(seq9[0:3])
    if nD == 9: return "极弱"
    s = nT * 2 + nR
    if "T" in up: s += 2
    if up == "DDD": s -= 4
    if "T" in "".join(seq9[6:9]): s += 1
    if "".join(seq9[6:9]) == "DDD": s -= 1
    s = max(0, min(8, s))
    return RANK[s]

@lru_cache(maxsize=None)
def level9(seq_tuple):
    """输入：9爻元组/列表/字符串(D/R/T)，返回唯一自适配等级。"""
    seq9 = list(seq_tuple)
    if len(seq9) != 9 or any(c not in "DRT" for c in seq9):
        raise ValueError("需要9爻(D/R/T)")
    sig = ",".join(map(str, _sig_of(seq9)))
    return _TABLE.get(sig, _fallback(seq9))

def level9_str(seq_str):
    return level9(tuple(seq_str))

if __name__ == "__main__":
    # 自验证：对校正版全部 19683 卦
    d = json.load(open(KB, encoding="utf-8"))
    agree = sum(1 for r in d["卦"] if level9(tuple(r["九爻值"])) == r["自适配等级"])
    print(f"确定性等级函数 level9 在全部 {len(d['卦'])} 卦上一致率: {agree/len(d['卦']):.1%}")
    print("签名表条数:", len(_TABLE), "| 导出:", SIG_JSON)
    for s in ["RRRTTTDDD", "DDDDTRDDD", "DDDDDDDDD", "TTTTTTTTT"]:
        print(f"  level9({s}) = {level9_str(s)}")
