# -*- coding: utf-8 -*-
"""
三元九维19683 · 语义推导器 (infer)
把模型从「记忆/检索语料」提升为「从三态公理推导」：
不查语料模板，而用确定性公理 + 位置语义，对任意 9 爻构型推导出结构化解释。

三态公理（确定性、可复算）：
  D 承载：削减分量、封存兜底、不读信息、不分辨、不审定、不回灌 —— 净作用=减少传递量+滞留能量
  R 判定：审定/否决/回灌、分辨有序无序、输出评估信息、管控吞吐 —— 净作用=把关挑拣+读信息
  T 增益：萌发原生(自激)、整形生发、对外释放信息 —— 净作用=放大/造能/释放

推导结构：
  ① 底层势能 ② 逐爻公理作用 ③ 层间传递 ④ 上层输出模式 ⑤ 自适配等级(level9) ⑥ 关键制约与演化建议
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

AXIOM = {
    "D": {"削减": "按物理属性削减经过的分量，封存兜底",
          "读": "不读信息", "分辨": "不分辨有序无序", "回灌": "不回灌"},
    "R": {"削减": "不削减、只审定；挑出合规分量放行，否决不合规者",
          "读": "能读信息、能感知抵达量", "分辨": "分辨有序无序",
          "回灌": "否决能量按链路回灌/滞留"},
    "T": {"削减": "不削减，成倍放大经过的分量；无输入时仍自激造能",
          "读": "不读信息", "分辨": "不分辨", "回灌": "反冲分散",
          "生发": "萌发原生动能/对外释放"},
}
POSN = {0: "底层", 1: "中位", 2: "顶层"}
LAYER_NAME = {0: "下卦", 3: "中卦", 6: "上卦"}

def _canon(num):
    n = num - 1; o = []
    for _ in range(3):
        o.append(["D", "R", "T"][n % 3]); n //= 3
    return list(reversed(o))

CANON_NAME = ["厚藏","待衡","启生","衡藏","双衡","启衡","抑扬","扬衡","奋生",
              "基衡","上下衡","基启","双衡藏","全衡","衡启","抑衡","扬双衡","衡奋",
              "基扬抑","基扬衡","对扬","基扬抑衡","基扬双衡","扬衡启","奋抑","奋衡","全扬"]

def layer_name(num):
    return CANON_NAME[num - 1]

def yi_role(c, lay, pos):
    """单爻公理作用描述。lay: 下/中/上, pos: 层内 0/1/2。"""
    lab = f"{lay}{POSN[pos]}"
    if c == "D":
        return f"{lab}D承载——{AXIOM['D']['削减']}，{AXIOM['D']['读']}、{AXIOM['D']['分辨']}、{AXIOM['D']['回灌']}"
    if c == "R":
        return f"{lab}R判定——{AXIOM['R']['削减']}；{AXIOM['R']['读']}，{AXIOM['R']['分辨']}；{AXIOM['R']['回灌']}"
    return f"{lab}T增益——{AXIOM['T']['削减']}；{AXIOM['T']['生发']}；{AXIOM['T']['回灌']}"

def infer_seq(seq9):
    """对任意9爻推导。seq9: 9元素D/R/T。返回结构化dict。"""
    if len(seq9) != 9 or any(c not in "DRT" for c in seq9):
        raise ValueError("需要9爻(D/R/T)")
    up, mid, lo = seq9[0:3], seq9[3:6], seq9[6:9]
    # ① 底层势能
    if "T" in lo:
        src = "底层含增益单元，具备原生造能（自激）供给"
    elif "R" in lo:
        src = "底层含判定单元，以评估/管理驱动（非自激，有动能但依赖存量）"
    else:
        src = "底层纯承载，无自发扰动、无动能供给（零输入）"
    # ② 逐爻公理（按下→中→上顺序，标注全层）
    per_yi = []
    for lay, vals in [("下", lo), ("中", mid), ("上", up)]:
        for pos in range(3):
            per_yi.append(yi_role(vals[pos], lay, pos))
    # ③ 层间传递
    trans = []
    trans.append(f"底层势能 {'充足' if 'T' in lo else ('有限' if 'R' in lo else '为零')}，向上递送")
    trans.append(f"中层{'' if 'T' in mid or 'R' in mid else '纯承载'}处理——{'放大/把关' if ('T' in mid or 'R' in mid) else '纯削减'}后继续上行")
    trans.append(f"上层{'释放/生发' if 'T' in up else ('读而不放' if 'R' in up else '滞留锁界')}")
    # ④ 上层输出模式
    if "T" in up:
        out = "对外释放（含增益通道，具备生发/释放能力）"
    elif "R" in up:
        out = "自知但不外放（能读信息、能审定，但无增益单元，成果滞留内域）"
    else:
        out = "滞留锁界（上层纯承载，不读、不自知、不释放，成果封存）"
    # ⑤ 等级
    from level9 import level9
    lvl = level9(tuple(seq9))
    # ⑥ 关键制约
    cons = []
    if "T" not in up and "R" not in up:
        cons.append("上层无R无T——全链无读取/释放，成果滞留，是最大制约")
    if lo.count("D") == 3:
        cons.append("底层无源——整链无原生动能，只能处理既存量")
    if "T" in up and "T" not in mid and "T" not in lo:
        cons.append("上T孤立——上游无造能与放大，增益单元缺少输入，放大的大多是零")
    if seq9.count("R") == 0:
        cons.append("全卦零判定——分不清有序与无序，无把关")
    if seq9.count("T") == 0:
        cons.append("全卦零增益——无撬动与释放，只有消耗能力")
    return {
        "构型": "".join(seq9),
        "底层势能": src,
        "逐爻作用": per_yi,
        "层间传递": trans,
        "上层输出": out,
        "自适配等级": lvl,
        "关键制约": cons,
    }

def infer_by_num(up, mid, lo):
    seq9 = _canon(up) + _canon(mid) + _canon(lo)
    return infer_seq(seq9)


def _flow_out(seq9, dynamics):
    """自下而上势能流：底层→顶层，返回顶层输出。"""
    bu = seq9[6:] + seq9[3:6] + seq9[0:3]
    _, final = dynamics.flow(bu)
    return final


def suggest(seq9, top=3, level9=None, dynamics=None):
    """演化指导器：对任意9爻，试遍每个位置改三态之一，给出可操作的优化建议。

    目标方向 = 增强：优先提升自适配等级，其次提升顶层输出。
    返回 top 条建议，每条标注 改第几爻 X→C、等级 原→新、输出 原→新。
    完全确定性、可复算。
    """
    if level9 is None:
        from level9 import level9
    from level9 import ORDER
    if dynamics is None:
        import dynamics
    base_lvl = level9(tuple(seq9))
    base_idx = ORDER[base_lvl]
    base_out = _flow_out(seq9, dynamics)
    cands = []
    for i in range(9):
        for c in "DRT":
            if c == seq9[i]:
                continue
            s2 = list(seq9); s2[i] = c
            lvl2 = level9(tuple(s2)); idx2 = ORDER[lvl2]
            out2 = _flow_out(s2, dynamics)
            cands.append((i, seq9[i], c, lvl2, idx2, out2))
    # 排序：等级提升优先，其次输出
    cands.sort(key=lambda x: (x[4], x[5]), reverse=True)
    res = []
    seen = set()
    for i, old, new, lvl2, idx2, out2 in cands:
        if len(res) >= top:
            break
        up_lvl = idx2 > base_idx
        up_out = out2 > base_out
        res.append({
            "改爻": i, "原爻": old, "改爻值": new,
            "爻位": f"{['上','中','下'][i//3]}{['底','中','顶'][i%3]}",
            "等级变化": f"{base_lvl}→{lvl2}", "等级提升": up_lvl,
            "输出变化": round(out2 - base_out, 4),
            "输出提升": up_out,
        })
    return {
        "构型": "".join(seq9),
        "原自适配": base_lvl,
        "原顶层输出": round(base_out, 4),
        "演化建议": res,
        "方向": "增强（优先提升自适配等级，其次提升顶层输出）",
    }


def _trend(seq9, dynamics):
    """顺势演化倾向：不加干预时，势能自然走向。基于确定性位置/输出特征。"""
    up, mid, lo = seq9[0:3], seq9[3:6], seq9[6:9]
    out = _flow_out(seq9, dynamics)
    if "T" in up:
        return ("外放扩张", f"上层含增益通道，势能持续对外释放（顶层输出 {out:.3f}），若不做干预将趋于开放扩张；短板在于中下层若无增益承接，放大的多为既存量。")
    if "R" in up:
        return ("内敛收束", f"上层能读能审定但无增益，势能『读而不放』滞留内域（顶层输出 {out:.3f}），自然走向是内敛收束、价值沉淀于存量纯度，不对外扩散。")
    if lo == "DDD" and mid == "DDD":
        return ("沉寂封存", "下中双纯承载、上层无读无放，势能无从产生也无处释放，自然走向是沉寂封存、全链安静。")
    return ("滞留锁界", f"上层纯承载，无读取无释放（顶层输出 {out:.3f}），势能沿链削减后在末端滞留锁界，自然走向是收敛沉积。")

def trace(seq9, steps=4, dynamics=None, level9=None):
    """时序演化路径推导（深化）：给出『顺势倾向』+『干预演化轨迹』。

    顺势：不加干预时势能的自然走向（确定性位置/输出规则）。
    干预：贪心逐代施加最优单爻增强（复用 suggest），生成 N 步演化轨迹。
    每一步标注 改哪爻、构型、等级、顶层输出 —— 完全确定性、可复算。
    """
    if dynamics is None:
        import dynamics
    if level9 is None:
        from level9 import level9, ORDER
    tendency, desc = _trend(seq9, dynamics)
    # 干预轨迹：贪心逐代
    cur = list(seq9)
    traj = [{
        "步": 0, "改动": "初始", "构型": "".join(cur),
        "自适配": level9(tuple(cur)), "顶层输出": round(_flow_out(cur, dynamics), 4),
    }]
    for st in range(1, steps + 1):
        sug = suggest(cur, top=1, level9=level9, dynamics=dynamics)["演化建议"]
        if not sug:
            break
        b = sug[0]
        i = b["改爻"]; new = b["改爻值"]
        cur[i] = new
        traj.append({
            "步": st, "改动": f"{b['爻位']}爻 {b['原爻']}→{new}",
            "构型": "".join(cur), "自适配": level9(tuple(cur)),
            "顶层输出": round(_flow_out(cur, dynamics), 4),
        })
    return {
        "构型": "".join(seq9),
        "顺势演化": {"倾向": tendency, "描述": desc},
        "干预演化轨迹": traj,
        "方向": "增强（每代取确定性最优单爻改动）",
    }

def demo():
    cases = [("RRR", "TTT", "DDD"), ("DTR", "DDT", "DDR"), ("DDD", "DDD", "DDD"), ("TTT", "TTT", "TTT")]
    for up, mid, lo in cases:
        r = infer_by_num([int(x) for x in up][0] if False else up2num(up), up2num(mid), up2num(lo))
        print(f"\n=== 上{up}({layer_name(up2num(up))}) 中{mid}({layer_name(up2num(mid))}) 下{lo}({layer_name(up2num(lo))}) ===")
        print(" 底层:", r["底层势能"])
        for y in r["逐爻作用"]:
            print("  ", y)
        for t in r["层间传递"]:
            print(" 传递:", t)
        print(" 输出:", r["上层输出"], "| 等级:", r["自适配等级"])
        print(" 制约:", "；".join(r["关键制约"]))

def up2num(s):
    """把3爻串映射回编号（D=0,R=1,T=2，底→顶）。"""
    n = 0
    for c in s:
        n = n * 3 + ["D", "R", "T"].index(c)
    return n + 1

if __name__ == "__main__":
    demo()
