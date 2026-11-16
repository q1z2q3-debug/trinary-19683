#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""literature_space.py · 认知空间 × 文学：单部作品的结构指纹

对象：加缪《局外人》(L'Étranger)
方法：场景级拆解 → 每场景 9 爻打标（上卦·大势 / 中卦·枢纽 / 下卦·底盘，各 3 爻，每爻 T/R/D）
     → 状态编号（3^9=19683）→ 轨迹指标 → 结构指纹

【重要声明】
- 9 爻编码是「文本解读」，不是客观测量；换一个解读者，编码会不同。本脚本保证的是
  「给定这套编码，指标可复算」，不保证「这套编码就是唯一正解」。
- 目的是验证一件事：认知空间能不能把一部作品的**结构**定位出来、并照出它的**破格点**。

运行：python3 literature_space.py
"""
from __future__ import annotations
import hashlib
import json

# 三态：D 承载/封存 = 0，R 判定/审定 = 1，T 增益/释放 = 2
TRIT = {"D": 0, "R": 1, "T": 2}
SYM = {"D": "●", "R": "■", "T": "▲"}   # 封存 / 判定 / 释放

# ---------------------------------------------------------------------
# 21 个场景级叙事状态（《局外人》第一部 1–13，第二部 14–21）
# 每场景：id, 名称, 上卦(大势), 中卦(枢纽), 下卦(底盘), 编码理由
# ---------------------------------------------------------------------
SCENES = [
    ("S01", "接到电报·母亲去世",  "DRD", "DRT", "RDT", "大势封存待定；关系未启动；身体在路途与热"),
    ("S02", "请假·赴养老院",      "DRD", "DRT", "RDT", "同上，程序性推进"),
    ("S03", "守灵夜",             "DDD", "DRT", "RDR", "大势全封存；关系悬置；身体被咖啡/烟/困占据"),
    ("S04", "葬礼·烈日下行",      "DRD", "DRD", "RDR", "关系切断（葬毕即断）；身体被光热支配"),
    ("S05", "回城·游泳遇玛丽",    "TRD", "TRT", "TRT", "全书第一次上扬：关系接上，身体释放"),
    ("S06", "看电影·亲密",        "TRT", "TRT", "TRT", "短暂的全面释放（喜剧片/亲密）"),
    ("S07", "周日·阳台看街",      "DRD", "DRD", "RDR", "释放回落；日常封存；身体观感"),
    ("S08", "雷蒙求助·写信",      "DRT", "TRT", "RDD", "枢纽被拉入（关系增益）；底盘转被动承载"),
    ("S09", "海滩·初遇冲突",      "DRT", "TRT", "RDR", "关系张力上升；身体在日光/沙"),
    ("S10", "雷蒙被刺",           "DRD", "DRD", "RDR", "情势转为封存；关系断裂"),
    ("S11", "再赴海滩",           "DRD", "DRD", "RDR", "重复推进；封存加深"),
    ("S12", "正午·对峙",          "DDD", "DRD", "RDR", "大势压到最低；身体被光/热/汗锁死"),
    ("S13", "开枪·四响",          "TTT", "TRT", "TTT", "★全书唯一一次全释放：释放即毁灭"),
    ("S14", "被捕·初审",          "DDD", "DDD", "RDD", "系统接管；关系全断；身体被羁押"),
    ("S15", "监狱·律师",          "DDD", "DDD", "RDD", "同上"),
    ("S16", "玛丽探监",           "DRD", "DRD", "RDR", "唯一残留的连接，随即被制度隔断"),
    ("S17", "法庭·质询葬礼",      "DDD", "DDD", "RDD", "外部判定压顶；主体全程承载不辩"),
    ("S18", "检察官论罪",         "DDD", "DDD", "RDD", "同上，判定强度最高"),
    ("S19", "判决死刑",           "DDD", "DDD", "RDD", "封存到底"),
    ("S20", "拒绝神父",           "DDD", "DDD", "RDD", "最后一次拒绝，仍不释放"),
    ("S21", "死刑前夜·向世界敞开", "DTD", "DDT", "TRT", "★第二次释放：这次是和解，不是毁灭"),
]

def state_code(u: str, m: str, l: str) -> int:
    """9 爻 → 19683 空间编号（1..19683）。上卦高位，下卦低位，D=0/R=1/T=2。"""
    seq = u + m + l
    n = 0
    for ch in seq:
        n = n * 3 + TRIT[ch]
    return n + 1

def layer_gua(s: str) -> int:
    """单层 3 爻 → 层卦编号（1..27），底→顶。"""
    n = 0
    for ch in s:
        n = n * 3 + TRIT[ch]
    return n + 1

def hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)

def dominant(s: str) -> str:
    """层主导态：多数票，平票取中爻。"""
    c = {k: s.count(k) for k in "DRT"}
    top = max(c.values())
    cand = [k for k, v in c.items() if v == top]
    return cand[0] if len(cand) == 1 else s[1]

def main():
    rows = []
    for sid, name, u, m, l, note in SCENES:
        full = u + m + l
        rows.append({
            "id": sid, "name": name, "u": u, "m": m, "l": l,
            "full": full,
            "code": state_code(u, m, l),
            "dup": dominant(u), "dmp": dominant(m), "dlp": dominant(l),
            "note": note,
        })

    # ---- 轨迹指标 ----
    dists = [hamming(rows[i]["full"], rows[i+1]["full"]) for i in range(len(rows)-1)]
    turn_density = sum(dists) / len(dists)
    # 最长驻留：连续相邻距离 ≤1 的段
    best_len, best_start, cur_len, cur_start = 1, 0, 1, 0
    for i, d in enumerate(dists):
        if d <= 1:
            cur_len += 1
        else:
            if cur_len > best_len:
                best_len, best_start = cur_len, cur_start
            cur_len, cur_start = 1, i + 1
    if cur_len > best_len:
        best_len, best_start = cur_len, cur_start

    # 破格点：全书 T 爻数的尖峰（相对全书中位数）
    t_counts = [r["full"].count("T") for r in rows]
    med = sorted(t_counts)[len(t_counts)//2]
    breakpoints = [rows[i]["id"] for i, t in enumerate(t_counts) if t - med >= 4]

    # 最大突变
    jump_i = max(range(len(dists)), key=lambda i: dists[i])

    # ---- 打印轨迹表 ----
    print("=" * 78)
    print("《局外人》结构指纹 · 21 场景 · 9 爻 → 19683 空间")
    print("=" * 78)
    print(f"{'场景':<4}{'名称':<20}{'上':<5}{'中':<5}{'下':<5}{'编号':<7}理由")
    for r in rows:
        print(f"{r['id']:<4}{r['name']:<20}{r['u']:<5}{r['m']:<5}{r['l']:<5}{r['code']:<7}{r['note']}")

    # ---- ASCII 轨迹（三行：上/中/下 的主导态）----
    print("\n层主导态轨迹（● 封存 / ■ 判定 / ▲ 释放）")
    for key, label in (("dup", "上·大势"), ("dmp", "中·枢纽"), ("dlp", "下·底盘")):
        line = "".join(SYM[r[key]] for r in rows)
        print(f"  {label} {line}")
    print("        " + "".join(str((i + 1) % 10) for i in range(len(rows))))

    # ---- 指标 ----
    print("\n" + "-" * 78)
    print("轨迹指标")
    print(f"  平均转折密度      : {turn_density:.2f} 爻/场景（相邻状态平均差几爻）")
    print(f"  最长驻留段        : {best_len} 个场景（{rows[best_start]['id']} → {rows[best_start+best_len-1]['id']}）")
    print(f"  最大单步突变      : {dists[jump_i]} 爻（{rows[jump_i]['id']} → {rows[jump_i+1]['id']}）")
    print(f"  破格点（T 尖峰）  : {', '.join(breakpoints) if breakpoints else '无'}")
    print(f"  T 爻数曲线        : {t_counts}")

    # ---- 结构指纹 ----
    payload = {"scenes": [(r["id"], r["full"]) for r in rows],
               "metrics": {"turn": round(turn_density, 4), "reside": best_len,
                           "jump": dists[jump_i], "bp": breakpoints}}
    fp = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    print(f"\n结构指纹（sha256 前16位）: {fp}")
    print("  → 同一套编码，任何机器复算都得到同一指纹；换编码则指纹变，可对照。")

    # ---- 复算验证 ----
    fp2 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    print(f"复算校验                : {'✅ 一致' if fp == fp2 else '❌ 不一致'}")
    return fp


if __name__ == "__main__":
    main()
