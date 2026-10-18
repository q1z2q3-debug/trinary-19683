# -*- coding: utf-8 -*-
"""
三元九维19683 · 规范校正引擎 v2（富文本复用版）
校正目标：全部 19683 卦统一到三进制规范层卦表。
- 结构身份：上/中/下 规范名称、规范爻值、九爻序列(上|中|下)、判定/承载/增益 → 全部规范化。
- 正文：原文值==规范值 → 保留原文；真值错误 → 用语料富文本模板重写，保证爻值—正文一致。
  分层拆解 / 演化路径：按 (层卦,位置) 取语料多数派富文本。
  自适配等级：按规范爻值的计数组合取多数派。
  总释 / 跨层制衡 / 自适配评估：用语料逐爻短语库 + 流程组装。
"""
import json, os, re, random
from collections import defaultdict, Counter

ROOT = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型"
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集.json")
OUT_KB = os.path.join(ROOT, "知识库", "三元九维19683_全集_规范校正版.json")

def canon(num):
    n = num - 1; o = []
    for _ in range(3):
        o.append(["D", "R", "T"][n % 3]); n //= 3
    return list(reversed(o))

d = json.load(open(KB, encoding="utf-8"))
recs = d["卦"]
layer = {t["编号"]: t for t in d["层卦规范"]}
NAME = {t["编号"]: t["规范名称"] for t in d["层卦规范"]}
SEM = d.get("语义字典", {})
POSL = {0: "底层", 1: "中位", 2: "顶层"}
POSX = {0: "基底", 1: "中位", 2: "顶层"}
POSN = {0: "最基底", 1: "中位", 2: "顶层"}
ROLE = {"上": "大势", "中": "枢纽", "下": "底盘"}

def canon_vals(r):
    return canon(r["上编号"]) + canon(r["中编号"]) + canon(r["下编号"])

# ============ 训练集 ============
train = [r for r in recs if r["九爻值"] == canon_vals(r)]
print("训练集(值正确)卦数:", len(train))

# 1) 分层拆解模板: (编号, 位置) -> Counter(富文本行)
fj = defaultdict(Counter)
for r in train:
    for pos, pre in [("下", "1."), ("中", "2."), ("上", "3.")]:
        line = next((x for x in r["分层拆解"] if x.startswith(pre)), None)
        if line:
            fj[(r[{"下": "下编号", "中": "中编号", "上": "上编号"}[pos]], pos)][line] += 1

# 2) 演化路径模板: (编号, 位置) -> {顺势, 干预} Counter
evt = defaultdict(lambda: {"顺势": Counter(), "干预": Counter()})
for r in train:
    for pos in ["下", "中", "上"]:
        num = r[{"下": "下编号", "中": "中编号", "上": "上编号"}[pos]]
        ev = r["演化路径"]
        if ev.get("顺势演化"): evt[(num, pos)]["顺势"][ev["顺势演化"]] += 1
        if ev.get("干预演化"): evt[(num, pos)]["干预"][ev["干预演化"]] += 1

# 3) 自适配等级: (判定,承载,增益) -> 多数派
lvl_ctr = defaultdict(Counter)
for r in train:
    lvl_ctr[(r["判定数"], r["承载数"], r["增益数"])][r["自适配等级"]] += 1
LEVEL = {k: v.most_common(1)[0][0] for k, v in lvl_ctr.items()}

def level_for(vals):
    k = (vals.count("R"), vals.count("D"), vals.count("T"))
    if k in LEVEL: return LEVEL[k]
    s = vals.count("R") + 2 * vals.count("T")
    if vals.count("D") == 9: return "极弱"
    if s == 0: return "极弱"
    if s <= 2: return "弱"
    if s <= 5: return "中等"
    if s <= 7: return "较强"
    if s <= 8: return "强"
    return "极强"

# 4) 总释逐爻短语库：从训练集总释按标记切分
# 标记集合
def split_zongshi(text):
    """把总释按爻位标记切成6个爻位片段(中层3+上层3)或None。"""
    pat = re.compile(r'(中层|上层)(最基底|基底|中位|顶层)[DTR]')
    marks = [(m.start(), m.end()) for m in pat.finditer(text)]
    if len(marks) < 6:
        return None
    starts = [m[0] for m in marks[:6]]
    segs = []
    for i in range(6):
        e = starts[i+1] if i+1 < 6 else len(text)
        segs.append(text[starts[i]:e])
    return segs

piece = defaultdict(Counter)   # (role, 爻值, pos) -> Counter(片段)
for r in train:
    segs = split_zongshi(r["复合卦总释"])
    if not segs: continue
    mid_v = canon(r["中编号"]); up_v = canon(r["上编号"])
    for i in range(3):
        piece[("中", mid_v[i], i)][segs[i].strip()] += 1
        piece[("上", up_v[i], i)][segs[i+3].strip()] += 1

def rep_piece(role, v, pos):
    c = piece[(role, v, pos)]
    return c.most_common(1)[0][0] if c else None

# ============ 生成函数（富文本） ============
def build_fenjie(vu, vm, vl, up, mp, lo):
    out = []
    for pos, pre, vals, num, role in [("下", "1.", vl, lo, "下"), ("中", "2.", vm, mp, "中"), ("上", "3.", vu, up, "上")]:
        line = rep_piece_pos(num, pos)
        if line is None:
            line = f"{pre} {role}卦{ROLE[role]}（{NAME[num]}）：{NAME[num]}【{','.join(vals)}】承载/判定/增益按位运行。"
        out.append(line)
    return out

def rep_piece_pos(num, pos):
    c = fj[(num, pos)]
    return c.most_common(1)[0][0] if c else None

def clean_evo(segs):
    """合并多段演化，去掉空段与多余分隔。"""
    segs = [s.strip().strip("：;；。") for s in segs if s and s.strip()]
    return "；".join(segs) + "。" if segs else ""

def build_evolution(vu, vm, vl, up, mp, lo):
    sh, ga = [], []
    for pos, num in [("下", lo), ("中", mp), ("上", up)]:
        s = evt[(num, pos)]["顺势"].most_common(1)
        g = evt[(num, pos)]["干预"].most_common(1)
        if s: sh.append(s[0][0])
        if g: ga.append(g[0][0])
    return "顺势演化：" + clean_evo(sh), "干预演化：" + clean_evo(ga)

def lay_desc(num, pos):
    """某层卦在某位置的富文本描述（来自分层拆解模板，去除编号前缀）。"""
    line = rep_piece_pos(num, pos)
    if line:
        # 去掉 "N. 下卦底盘（XX）：" 前缀，保留描述主体
        line = re.sub(r'^\d\.\s*[上下中]卦[^：]*：', '', line)
        return line
    return None

def build_zongshi(vu, vm, vl, up, mp, lo):
    parts = []
    # 下卦
    ld = lay_desc(lo, "下")
    parts.append(f"**下卦{ROLE['下']}（{NAME[lo]}）**：{ld if ld else ('纯' + '·'.join(vl) + '构型')}")
    # 中卦 3 爻流程
    mdesc = lay_desc(mp, "中")
    parts.append(f"下卦向上递送势能，进入**中卦{ROLE['中']}（{NAME[mp]}）**——{mdesc if mdesc else '按' + '→'.join(vm) + '运行'}")
    # 上卦
    udesc = lay_desc(up, "上")
    parts.append(f"经中层传递后的分量抵达**上卦{ROLE['上']}（{NAME[up]}）**——{udesc if udesc else '按' + '→'.join(vu) + '运行'}")
    # 结尾
    if vu.count("R") == 0 and vu.count("T") == 0:
        parts.append("上层纯承载，无R无T——不读信息、不自知、不对外释放，成果滞留锁界")
    elif vu.count("T") > 0:
        parts.append("上层含增益单元，具备对外释放/生发通道")
    elif vu.count("R") > 0:
        parts.append("上层含判定单元，能读信息、能审定")
    return "；".join(parts) + "。"

def build_kua(vu, vm, vl):
    v = vu + vm + vl
    nr, nd, nt = v.count("R"), v.count("D"), v.count("T")
    n = []
    if vu.count("R") == 0 and vu.count("T") == 0: n.append("上层纯承载，成果滞留锁界、不对外释放")
    if vm.count("R") == 0 and vm.count("T") == 0: n.append("中层纯承载，对上行分量一律削减")
    if vl.count("R") == 0 and vl.count("T") == 0: n.append("底层纯承载，无自发扰动")
    if nr == 0: n.append("全卦零判定，分不清有序与无序")
    if nt == 0: n.append("全卦零增益，无撬动能力、只有消耗能力")
    if nd == 9: n.append("九爻全承载，纯衰减构型、全体系最安静")
    return "；".join(n) + "。"

def build_pinggu(vals, lvl):
    nr, nd, nt = vals.count("R"), vals.count("D"), vals.count("T")
    return f"本卦判定{nr}道、承载{nd}道、增益{nt}道，自适配能力评估为「{lvl}」。三方制衡下整体协调性以层次链通为要，承载兜底、判定把关、增益撬动。"


# ============ 校正主流程 ============
def correct_record(r):
    up, mp, lo = r["上编号"], r["中编号"], r["下编号"]
    vu, vm, vl = canon(up), canon(mp), canon(lo)
    newvals = vu + vm + vl
    orig = r["九爻值"]
    out = dict(r)
    out["上卦"] = NAME[up]; out["中卦"] = NAME[mp]; out["下卦"] = NAME[lo]
    out["九爻值"] = newvals
    out["九爻序列"] = " ".join(vu) + "｜" + ",".join(vm) + "｜" + " ".join(vl)
    out["判定数"] = newvals.count("R"); out["承载数"] = newvals.count("D"); out["增益数"] = newvals.count("T")
    out["三层值"] = [vu, vm, vl]
    out["规范九爻值"] = newvals; out["九爻一致"] = True; out["偏差说明"] = ""
    out["自适配等级"] = level_for(newvals)
    if orig == newvals:
        # 值正确：保留原文正文，但保证三层结构行用规范名称（原多已规范）
        return out
    # 真值错误：重写正文（富文本复用）
    out["复合卦总释"] = build_zongshi(vu, vm, vl, up, mp, lo)
    out["分层拆解"] = build_fenjie(vu, vm, vl, up, mp, lo)
    out["跨层制衡"] = build_kua(vu, vm, vl)
    out["自适配评估"] = build_pinggu(newvals, out["自适配等级"])
    sh, ga = build_evolution(vu, vm, vl, up, mp, lo)
    out["演化路径"] = {"顺势演化": sh, "干预演化": ga}
    return out

new_recs = [correct_record(r) for r in recs]
kept = sum(1 for r in new_recs if r["九爻一致"] and r["复合卦总释"] == recs[new_recs.index(r)]["复合卦总释"])
# 重新统计保留/重写
kept = 0; regen = 0
for old, new in zip(recs, new_recs):
    if old["九爻值"] == canon_vals(old): kept += 1
    else: regen += 1
print(f"校正: 共{len(new_recs)}卦 | 保留原文(值正确){kept} | 重写正文(值错误){regen}")

out_data = dict(d)
out_data["meta"] = {**d.get("meta", {}), "版本": "规范校正版",
                    "校正说明": "全部卦结构统一到三进制规范层卦表；真值错误卦正文按规范爻值以语料富文本重写。"}
out_data["卦"] = new_recs
with open(OUT_KB, "w", encoding="utf-8") as f:
    json.dump(out_data, f, ensure_ascii=False, indent=1)
print("输出:", OUT_KB)

# 抽样看质量
print("\n=== 抽样(真值错误卦校正后) ===")
for r in new_recs:
    if r["九爻一致"] and (r["上编号"], r["中编号"]) == (1, 8) and r["下编号"] == 1:
        print("卦(1,8,1)", r["九爻序列"], "上%s 中%s 下%s" % (r["上卦"], r["中卦"], r["下卦"]), "等级", r["自适配等级"])
        print(" 总释:", r["复合卦总释"][:400])
        print(" 分层:", " || ".join(x[:60] for x in r["分层拆解"]))
        print(" 演化:", r["演化路径"]["顺势演化"][:80], "||", r["演化路径"]["干预演化"][:80])
        break
