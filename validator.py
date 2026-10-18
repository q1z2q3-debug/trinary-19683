# -*- coding: utf-8 -*-
"""
三元九维19683 · 一致性校验器 v2 (validator)
把「校正」从单向变成可闭环、可回归的校验：
  A. 结构不变量（确定性，全量 19683 卦）——硬
     A1 名称=规范  A2 九爻值=canon  A3 序列格式  A4 计数  A5 等级合法  A6 编号唯一  A7 层卦表
  B. 结构化正文断言（可精确比对）——硬
     B1 分层行层名 vs 规范名   B2 爻值标注【…】vs 规范爻值
     B3 显式计数(判定N道/承载N道/增益N道) vs 实际（分层行=该层计数；总释/评估/演化=全卦计数）
  C. 定性散文断言（作用域精确的强断言）——软（提示，不判硬错）
     C1 明确"全卦零判定/全卦零增益/九爻全承载/系统无能量流转" vs 九爻
     C2 分层行整层"纯承载/无R无T" 强断言 vs 该层
输出：通过率 + 矛盾清单 + 回归报告(md)。
"""
import json, os, re
from collections import defaultdict, Counter

ROOT = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型/知识库"
KB = os.path.join(ROOT, "三元九维19683_全集_规范校正版.json")
d = json.load(open(KB, encoding="utf-8"))
recs = d["卦"]
layers = {t["编号"]: t for t in d["层卦规范"]}
CANON_NAME = {t["编号"]: t["规范名称"] for t in d["层卦规范"]}
VALID_LVL = {"极弱","弱","较弱","中等偏弱","中等","中等偏上","较强","强","极强"}

def canon(num):
    n = num - 1; o = []
    for _ in range(3):
        o.append(["D", "R", "T"][n % 3]); n //= 3
    return list(reversed(o))

hard = []   # (id, 类别, 说明)
soft = []   # (id, 类别, 说明)

# ============ A. 结构不变量（硬） ============
def check_structure():
    ids = set()
    for r in recs:
        gid = f"{r['上编号']:02d}{r['中编号']:02d}{r['下编号']:02d}"
        ids.add(gid)
        vu, vm, vl = canon(r["上编号"]), canon(r["中编号"]), canon(r["下编号"])
        if r["上卦"] != CANON_NAME[r["上编号"]] or r["中卦"] != CANON_NAME[r["中编号"]] or r["下卦"] != CANON_NAME[r["下编号"]]:
            hard.append((gid, "A1名称", f"{r['上卦']}/{r['中卦']}/{r['下卦']}"))
        if r["九爻值"] != vu + vm + vl:
            hard.append((gid, "A2爻值", "".join(r["九爻值"])))
        if r["九爻序列"] != " ".join(vu) + "｜" + ",".join(vm) + "｜" + " ".join(vl):
            hard.append((gid, "A3序列", r["九爻序列"]))
        if (r["判定数"], r["承载数"], r["增益数"]) != ((vu+vm+vl).count("R"), (vu+vm+vl).count("D"), (vu+vm+vl).count("T")):
            hard.append((gid, "A4计数", f"{r['判定数']}/{r['承载数']}/{r['增益数']}"))
        if r["自适配等级"] not in VALID_LVL:
            hard.append((gid, "A5等级", r["自适配等级"]))
    if len(ids) != len(recs):
        hard.append(("", "A6编号", f"{len(ids)}/{len(recs)}"))
    for num in range(1, 28):
        if num not in layers:
            hard.append(("", "A7层卦", str(num)))

# ============ B. 结构化正文断言（硬） ============
def layer_num(text):
    m = re.search(r'[上下中]卦(?:[枢纽大势底盘]?\（)?(\d+)[）]?', text)
    return int(m.group(1)) if m else None

def check_structured():
    for r in recs:
        gid = f"{r['上编号']:02d}{r['中编号']:02d}{r['下编号']:02d}"
        for pos, pre, num, v3 in [("下", "1.", r["下编号"], canon(r["下编号"])),
                                   ("中", "2.", r["中编号"], canon(r["中编号"])),
                                   ("上", "3.", r["上编号"], canon(r["上编号"]))]:
            line = next((x for x in r["分层拆解"] if x.startswith(pre)), None)
            if not line: continue
            # B1 层名：行内若出现"X卦（YY名）"，YY 应=该层规范名
            nm = re.search(r'[上下中]卦[^（]*（([\u4e00-\u9fa5]{2,3})）', line)
            if nm and nm.group(1) != CANON_NAME[num]:
                hard.append((gid, f"B1层[{pos}]", f"层名'{nm.group(1)}'≠'{CANON_NAME[num]}'"))
            # B2 爻值标注【..】
            mv = re.search(r'【([DRT,，]+)】', line)
            if mv:
                vals = [c for c in mv.group(1) if c in "DRT"]
                if vals and vals != v3:
                    hard.append((gid, f"B2层[{pos}]", f"爻值标注{''.join(vals)}≠{''.join(v3)}"))
            # B3 该层显式计数
            mj = re.search(r'判定(\d)道', line); md = re.search(r'承载(\d)道', line); mt = re.search(r'增益(\d)道', line)
            if mj and int(mj.group(1)) != v3.count("R"): hard.append((gid, f"B3层[{pos}]", f"判定数{mj.group(1)}≠{v3.count('R')}"))
            if md and int(md.group(1)) != v3.count("D"): hard.append((gid, f"B3层[{pos}]", f"承载数{md.group(1)}≠{v3.count('D')}"))
            if mt and int(mt.group(1)) != v3.count("T"): hard.append((gid, f"B3层[{pos}]", f"增益数{mt.group(1)}≠{v3.count('T')}"))
        # 全卦字段的显式计数（总释/评估/演化）
        v9 = canon(r["上编号"]) + canon(r["中编号"]) + canon(r["下编号"])
        for field in ["复合卦总释", "自适配评估", "跨层制衡"]:
            txt = r.get(field, "") or ""
            mj = re.search(r'判定(\d)道', txt); md = re.search(r'承载(\d)道', txt); mt = re.search(r'增益(\d)道', txt)
            if mj and int(mj.group(1)) != v9.count("R"): hard.append((gid, f"B3[{field}]", f"判定数{mj.group(1)}≠{v9.count('R')}"))
            if md and int(md.group(1)) != v9.count("D"): hard.append((gid, f"B3[{field}]", f"承载数{md.group(1)}≠{v9.count('D')}"))
            if mt and int(mt.group(1)) != v9.count("T"): hard.append((gid, f"B3[{field}]", f"增益数{mt.group(1)}≠{v9.count('T')}"))

# ============ C. 定性散文断言（软） ============
def check_qualitative():
    for r in recs:
        gid = f"{r['上编号']:02d}{r['中编号']:02d}{r['下编号']:02d}"
        v9 = canon(r["上编号"]) + canon(r["中编号"]) + canon(r["下编号"])
        for field in ["复合卦总释", "跨层制衡", "自适配评估"]:
            txt = r.get(field, "") or ""
            if re.search(r'(全卦零判定|全卦无判定|系统无任何判定|全系统无判定)', txt) and "R" in v9:
                soft.append((gid, f"C1[{field}]", "全卦零判定但含R"))
            if re.search(r'(全卦零增益|全卦无增益|系统无任何增益|无任何撬动)', txt) and "T" in v9:
                soft.append((gid, f"C1[{field}]", "全卦零增益但含T"))
            if re.search(r'(九爻全承载|九爻全D)', txt) and not all(c == "D" for c in v9):
                soft.append((gid, f"C1[{field}]", "九爻全承载但非全D"))
        evo = r.get("演化路径", {}) or {}
        for k in ["顺势演化", "干预演化"]:
            txt = evo.get(k, "") or ""
            if re.search(r'(全卦零判定|全系统无判定)', txt) and "R" in v9:
                soft.append((gid, f"C1[演化.{k}]", "全卦零判定但含R"))
        # C2 分层整层强断言：行以"X卦...纯承载"或"无R无T"开头段
        for pos, pre, num in [("下", "1.", r["下编号"]), ("中", "2.", r["中编号"]), ("上", "3.", r["上编号"])]:
            line = next((x for x in r["分层拆解"] if x.startswith(pre)), None)
            if not line: continue
            body = re.sub(r'^\d\.\s*[上下中]卦[^：]*：', '', line)
            v3 = canon(num)
            if re.search(r'^(纯承载|纯D|无R无T|无任何R|全承载)', body.strip()) and (v3.count("R") or v3.count("T")):
                soft.append((gid, f"C2层[{pos}]", f"整层'{body[:24]}'声称纯承载但含R/T:{''.join(v3)}"))

check_structure()
check_structured()
check_qualitative()

hc = Counter(x[1].split("[")[0] for x in hard)
sc = Counter(x[1].split("[")[0] for x in soft)

lines = []
lines.append("# 三元九维19683 · 一致性校验报告（v2）\n")
lines.append(f"- 校验对象：**{len(recs)}** 卦（规范校正版·语境化正文）")
lines.append(f"- **A 结构不变量（硬）**：**{len(hard)}** 条")
lines.append(f"- **B 结构化正文断言（硬，层名/爻值标注/显式计数）**：**{len([x for x in hard if x[1].startswith('B')])}** 条")
lines.append(f"- **C 定性散文断言（软，作用域精确的全卦/整层强断言）**：**{len(soft)}** 条（提示性，需人工复核）\n")
lines.append("## 一、A 结构不变量\n")
lines.append("A1名称 A2爻值 A3序列 A4计数 A5等级 A6编号 A7层卦表 —— 全量确定性断言。")
lines.append("")
lines.append("## 二、B 结构化正文断言矛盾（硬）\n")
if [x for x in hard if x[1].startswith("B")]:
    lines.append("|卦id|类别|说明|")
    lines.append("|---|---|---|")
    for gid, c, note in hard:
        if c.startswith("B"):
            lines.append(f"|{gid}|{c}|{note}|")
else:
    lines.append("无。")
lines.append("")
lines.append("## 三、C 定性散文断言提示（软）\n")
lines.append("|卦id|类别|说明|")
lines.append("|---|---|---|")
for gid, c, note in soft[:60]:
    lines.append(f"|{gid}|{c}|{note}|")
if len(soft) > 60:
    lines.append(f"|…|共 {len(soft)} 条，仅列前60|")
lines.append("")
lines.append("## 四、类别统计\n")
lines.append("|类别|条数|")
lines.append("|---|---|")
for k, v in sorted((hc + sc).items()):
    lines.append(f"|{k}|{v}|")
lines.append("")
lines.append(f"> 结论：结构不变量与结构化正文断言（A+B）硬伤 {len(hard)} 条；C 定性散文 {len(soft)} 条为提示，需人工复核或修模板。本校验器可作回归测试反复运行：`python3 validator.py`。")
rep = "\n".join(lines)
with open(os.path.join(ROOT, "一致性校验报告.md"), "w", encoding="utf-8") as f:
    f.write(rep)

print("=== 一致性校验 v2 ===")
print("A 结构硬伤:", len(hard))
print("B 结构化正文硬伤:", len([x for x in hard if x[1].startswith('B')]))
print("C 定性散文提示(软):", len(soft))
print("类别:", dict(hc + sc))
if [x for x in hard if x[1].startswith('B')]:
    print("--- B 硬伤示例 ---")
    for x in [x for x in hard if x[1].startswith('B')][:10]:
        print("  ", x)
print("报告:", os.path.join(ROOT, "一致性校验报告.md"))
