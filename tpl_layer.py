# -*- coding: utf-8 -*-
"""
模板提取（阶段1：分层拆解）
从规范一致卦中提取每(层卦编号, 位置)的分层拆解行模板，并在一 致卦上验证保真度。
"""
import json, os, re
from collections import defaultdict, Counter

ROOT = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型"
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集.json")
d = json.load(open(KB, encoding="utf-8"))
recs = d["卦"]

def canon(num):
    n = num - 1; o = []
    for _ in range(3):
        o.append(["D", "R", "T"][n % 3]); n //= 3
    return list(reversed(o))

# 每个记录：各层段的爻值
def seg_ok(r, pos):
    idx = {"下": 0, "中": 1, "上": 2}[pos]
    num = r[{"下": "下编号", "中": "中编号", "上": "上编号"}[pos]]
    return r["九爻值"][idx*3:idx*3+3] == canon(num)

# 提取模板： (编号, 位置) -> Counter(分层拆解行)
tmpl = defaultdict(Counter)
for r in recs:
    for pos, pre in [("下", "1."), ("中", "2."), ("上", "3.")]:
        if not seg_ok(r, pos):
            continue
        num = r[{"下": "下编号", "中": "中编号", "上": "上编号"}[pos]]
        line = next((x for x in r["分层拆解"] if x.startswith(pre)), None)
        if line:
            tmpl[(num, pos)][line] += 1

# 代表性模板
rep = {}
for k, c in tmpl.items():
    rep[k] = c.most_common(1)[0][0]
print("提取模板数:", len(rep))

# 验证：在全部记录上，用模板(该层爻值=规范时)比对原文
match = total = 0
mismatch_examples = []
for r in recs:
    for pos, pre in [("下", "1."), ("中", "2."), ("上", "3.")]:
        num = r[{"下": "下编号", "中": "中编号", "上": "上编号"}[pos]]
        orig = next((x for x in r["分层拆解"] if x.startswith(pre)), None)
        if orig is None:
            continue
        total += 1
        t = rep.get((num, pos))
        if t == orig:
            match += 1
        elif len(mismatch_examples) < 15 and t:
            mismatch_examples.append((num, pos, orig[:60], t[:60]))
print(f"分层拆解行模板命中率: {match}/{total} = {match/total:.1%}")
print("--- 不一致示例 ---")
for num, pos, o, t in mismatch_examples:
    print(f"[{pos}{num:02d}] 原文:{o} | 模板:{t}")
