# -*- coding: utf-8 -*-
"""
三元九维19683 · 规范校正引擎
目标：把全部 19683 卦统一到三进制规范层卦表，消除「同一编号不同含义」的不一致。
- 结构身份：上/中/下 规范名称、规范爻值、九爻序列统一为「上|中|下」顺序、判定/承载/增益按规范爻值重算。
- 正文：原文爻值==规范值 的卦保留原文；真值错误卦按规范爻值重写，保证爻值—正文一致。
"""
import json, os, re
from collections import defaultdict, Counter

ROOT = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型"
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集.json")
OUT_KB = os.path.join(ROOT, "知识库", "三元九维19683_全集_规范校正版.json")

CANON_NAME = ["厚藏","待衡","启生","衡藏","双衡","启衡","抑扬","扬衡","奋生",
              "基衡","上下衡","基启","双衡藏","全衡","衡启","抑衡","扬双衡","衡奋",
              "基扬抑","基扬衡","对扬","基扬抑衡","基扬双衡","扬衡启","奋抑","奋衡","全扬"]
def canon(num):
    n = num - 1; o = []
    for _ in range(3):
        o.append(["D", "R", "T"][n % 3]); n //= 3
    return list(reversed(o))

d = json.load(open(KB, encoding="utf-8"))
recs = d["卦"]
layer = {t["编号"]: t for t in d["层卦规范"]}

def layer_vals(num):
    return layer[num]["规范三爻"]

# ============ 1. 提取模板库（来自规范一致卦）============
# 1a. 分层拆解： (编号, 位置) -> 各变体（多数派为准）
fj = defaultdict(Counter)     # (num,pos) -> Counter(line)
# 1b. 演化路径： (编号, 位置) -> 顺势/干预
evt = defaultdict(lambda: defaultdict(Counter))
# 1c. 自适配评估正文： (编号组合签名) -> 变体 —— 暂用 判定/承载/增益+极值 作特征
# 1d. 总释 逐爻叙述： (爻值, 层内位置, 层角色) -> 叙述片段
zong_piece = defaultdict(list)

POSL = {0:"底层",1:"中位",2:"顶层"}
ROLE = {"上":"大势","中":"枢纽","下":"底盘"}
RPOS = {"上":"上","中":"中","下":"下"}

def seg_is_canon(r, pos):
    idx = {"下":0,"中":1,"上":2}[pos]
    num = r[{"下":"下编号","中":"中编号","上":"上编号"}[pos]]
    return r["九爻值"][idx*3:idx*3+3] == canon(num)

for r in recs:
    # 仅用"九爻与规范一致"的记录做训练（值正确的记录）
    if r["九爻值"] != canon(r["上编号"])+canon(r["中编号"])+canon(r["下编号"]):
        continue
    # 分层拆解
    for pos, pre in [("下","1."),("中","2."),("上","3.")]:
        line = next((x for x in r["分层拆解"] if x.startswith(pre)), None)
        if line:
            fj[(r[{"下":"下编号","中":"中编号","上":"上编号"}[pos]], pos)][line]+=1
    # 演化路径
    for pos in ["下","中","上"]:
        num = r[{"下":"下编号","中":"中编号","上":"上编号"}[pos]]
        ev = r["演化路径"]
        evt[(num,pos)]["顺势"][ev.get("顺势演化","")]+=1
        evt[(num,pos)]["干预"][ev.get("干预演化","")]+=1

# ============ 2. 等级规则 ============
lvl_ctr = defaultdict(Counter)
for r in recs:
    if r["九爻值"] != canon(r["上编号"])+canon(r["中编号"])+canon(r["下编号"]):
        continue
    lvl_ctr[(r["判定数"],r["承载数"],r["增益数"])][r["自适配等级"]]+=1
LEVEL_BY_COUNTS = {k: v.most_common(1)[0][0] for k,v in lvl_ctr.items()}

def level_for(vals):
    nr, nd, nt = vals.count("R"), vals.count("D"), vals.count("T")
    k = (nr, nd, nt)
    if k in LEVEL_BY_COUNTS:
        return LEVEL_BY_COUNTS[k]
    # 未见组合：启发式
    s = nr + 2*nt
    if nd == 9: return "极弱"
    if s == 0: return "极弱"
    if s <= 2: return "弱"
    if s <= 5: return "中等"
    if s <= 7: return "较强"
    if s <= 8: return "强"
    return "极强"

# ============ 3. 流程生成器（总释/跨层制衡/自适配评估）============
# 逐爻叙述：从规范一致卦的 总释 中抽取每爻描述句（按 爻值+层角色+层内位置）
# 简化：从规范一致卦的 分层拆解 + 总释 提取每层的语义要点，生成结构化总释。
def build_zongshi(r, up, mp, lo):
    """按规范爻值生成总释（流程叙事）。"""
    def layer_name(num):
        return layer[num]["规范名称"]
    def yi(c, pos, role):
        # 单爻行为
        if c == "D":
            return f"{POSL[pos]}D承载——按物理属性削减，能封存兜底，无分辨，不审定、不回灌"
        if c == "R":
            return f"{POSL[pos]}R判定——审定/否决/回灌，分辨有序与无序，输出评估信息"
        return f"{POSL[pos]}T增益——萌发原生动能，整形生发，对外释放信息"
    s = []
    # 下卦（底盘）
    lo0,lo1,lo2 = lo
    if lo.count("D")==3:
        s.append(f"**下卦底盘（{layer_name(r['下编号'])}）纯承载——无自发扰动，资源沉淀封存**")
    elif lo2=="T":
        s.append(f"**下卦底盘（{layer_name(r['下编号'])}）顶层T萌发原生持续动能向上推送**")
    elif lo1=="T" and lo2=="R":
        s.append(f"**下卦底盘（{layer_name(r['下编号'])}）中位R管控吞吐、顶层T稳定生发，推送可控势能**")
    elif lo0=="R":
        s.append(f"**下卦底盘（{layer_name(r['下编号'])}）底层R审定根基，管控储能与释放策略**")
    elif lo1=="R":
        s.append(f"**下卦底盘（{layer_name(r['下编号'])}）中位R调控存量吞吐**")
    else:
        s.append(f"**下卦底盘（{layer_name(r['下编号'])}）{layer_name(r['下编号'])}【{'·'.join(lo)}】构型**")
    # 中卦三爻
    mid = []
    for i,c in enumerate(mp):
        mid.append(f"经递送/削减后的分量上行至中层{POSL[i]}{c}——{yi(c,i,'中')}")
    # 上卦三爻
    top = []
    for i,c in enumerate(up):
        top.append(f"上行至上层{POSL[i]}{c}——{yi(c,i,'上')}")
    s.append("；".join(mid))
    s.append("；".join(top))
    # 结尾
    if up.count("R")==0 and up.count("T")==0:
        s.append("**上层纯承载，无R无T——不读信息、不自知、不对外释放，成果滞留锁界**")
    elif up.count("T")>0:
        s.append("**上层含增益单元，具备对外释放/生发通道**")
    elif up.count("R")>0:
        s.append("**上层含判定单元，能读信息、能审定，但无对外增益**")
    return "；".join(s) + "。"

def build_kua(up, mp, lo):
    """跨层制衡：结构化总结。"""
    v = up+mp+lo
    nr,nd,nt = v.count("R"),v.count("D"),v.count("T")
    notes=[]
    if up.count("R")==0 and up.count("T")==0:
        notes.append("上层纯承载，成果滞留锁界、不对外释放")
    if mp.count("R")==0 and mp.count("T")==0:
        notes.append("中层纯承载，对上行分量一律削减")
    if lo.count("R")==0 and lo.count("T")==0:
        notes.append("底层纯承载，无自发扰动")
    if nr==0:
        notes.append("全卦零判定，分不清有序与无序")
    if nt==0:
        notes.append("全卦零增益，无撬动能力、只有消耗能力")
    if nd==9:
        notes.append("九爻全承载，纯衰减构型、全体系最安静")
    return "；".join(notes) + "。"

def build_pinggu(up, mp, lo, lvl):
    v = up+mp+lo
    nr,nd,nt = v.count("R"),v.count("D"),v.count("T")
    base = f"本卦判定{nr}道、承载{nd}道、增益{nt}道，自适配能力评估为「{lvl}」。"
    return base

def build_evolution(up, mp, lo):
    """演化路径：按层生成顺势/干预。"""
    shun, gan = [], []
    lo0,lo1,lo2=lo
    if lo.count("R")==0 and lo.count("T")==0:
        shun.append("底层持续静止封存"); gan.append("底层产生T或R，让底盘有可递送的势能")
    elif lo2=="T":
        shun.append("底层持续造能"); gan.append("底层加R约束产能，让造能可控")
    elif lo1=="R":
        shun.append("底层持续管控吞吐"); gan.append("底层改为T生发，增加可递送势能")
    # 中
    if mp.count("R")==0 and mp.count("T")==0:
        shun.append("中层持续空削"); gan.append("中位或末端换R/T，让链路有分辨或增益")
    elif mp[2]=="R":
        shun.append("末端持续审定与回灌"); gan.append("末端换T，让链路有增益")
    elif mp[2]=="T":
        shun.append("末端持续放大生发"); gan.append("末端换R，加强审定与分辨")
    # 上
    if up.count("R")==0 and up.count("T")==0:
        shun.append("上层持续封存不释放"); gan.append("上层加R或T，建立自知或对外释放通道")
    return "顺势演化：" + "，".join(shun) + "。", "干预演化：" + "，".join(gan) + "。"

# ============ 4. 校正主流程 ============
def correct_record(r):
    up, mp, lo = r["上编号"], r["中编号"], r["下编号"]
    vu, vm, vl = canon(up), canon(mp), canon(lo)
    newvals = vu+vm+vl
    orig = r["九爻值"]
    out = dict(r)
    # 结构身份
    out["上卦"] = layer[up]["规范名称"]
    out["中卦"] = layer[mp]["规范名称"]
    out["下卦"] = layer[lo]["规范名称"]
    out["九爻值"] = newvals
    out["九爻序列"] = " ".join(vu)+"｜"+",".join(vm)+"｜"+" ".join(vl)
    out["判定数"] = newvals.count("R")
    out["承载数"] = newvals.count("D")
    out["增益数"] = newvals.count("T")
    out["三层值"] = [vu, vm, vl]
    out["规范九爻值"] = newvals
    out["九爻一致"] = True
    out["偏差说明"] = ""
    # 自适配等级
    out["自适配等级"] = level_for(newvals)
    if orig == newvals:
        # 原文值正确：保留正文（仅确保等级一致——若原文等级不同，以复算为准）
        # 但原文等级可能依赖配置；为一致性，用复算等级 + 保留正文措辞
        out["_keep_prose"] = True
        return out
    # 真值错误：重写正文
    out["复合卦总释"] = build_zongshi(out, vu, vm, vl)
    out["分层拆解"] = [
        "1. 下卦底盘（"+layer[lo]["规范名称"]+"）："+layer[lo]["规范名称"]+"【"+",".join(vl)+"】承载/判定/增益按位运行。",
        "2. 中卦枢纽（"+layer[mp]["规范名称"]+"）："+layer[mp]["规范名称"]+"【"+",".join(vm)+"】",
        "3. 上卦大势（"+layer[up]["规范名称"]+"）："+layer[up]["规范名称"]+"【"+",".join(vu)+"】",
    ]
    out["跨层制衡"] = build_kua(vu, vm, vl)
    out["自适配评估"] = build_pinggu(vu, vm, vl, out["自适配等级"])
    sh, ga = build_evolution(vu, vm, vl)
    out["演化路径"] = {"顺势演化": sh, "干预演化": ga}
    out["_keep_prose"] = False
    return out

new_recs = [correct_record(r) for r in recs]
kept = sum(1 for r in new_recs if r["_keep_prose"])
regenerated = len(new_recs) - kept
for r in new_recs:
    r.pop("_keep_prose", None)

out_data = dict(d)
out_data["meta"] = {**d.get("meta",{}), "版本":"规范校正版",
                    "校正说明":"全部卦结构统一到三进制规范层卦表；真值错误卦正文按规范爻值重写。"}
out_data["卦"] = new_recs
with open(OUT_KB, "w", encoding="utf-8") as f:
    json.dump(out_data, f, ensure_ascii=False, indent=1)
print(f"校正完成: 共{len(new_recs)}卦, 保留原文{kept}, 重写正文{regenerated}")
print("输出:", OUT_KB)

# 抽样
import random
random.seed(7)
print("\n=== 抽样：真值错误卦的校正效果 ===")
for r in new_recs:
    if r["九爻一致"] and (r["上编号"],r["中编号"])==(1,8):
        print("卦(%d,%d,%d)"%(r["上编号"],r["中编号"],r["下编号"]), r["九爻序列"], "| 上%s 中%s 下%s"%(r["上卦"],r["中卦"],r["下卦"]), "| 等级",r["自适配等级"])
        print("  总释:", r["复合卦总释"][:200])
        print("  分层:", " | ".join(x[:40] for x in r["分层拆解"]))
        print("  演化:", r["演化路径"]["顺势演化"][:60], "||", r["演化路径"]["干预演化"][:60])
        if random.random()<0.2: break
