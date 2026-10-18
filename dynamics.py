# -*- coding: utf-8 -*-
"""
三元九维19683 · 动态推演引擎 (dynamics)
把静态 9 爻构型升级为可复算的过程模型：
- 势能从下卦底层 → 上卦顶层，逐爻流动；每爻按其三态对分量做变换。
- 量化流模型（系数为「示意」假设，非体系内建数值）：
    D 承载：离开 = 进入 × 0.60，封存滞留 = 进入 × 0.40
    R 判定：离开 = 进入 × 0.75，否决/回灌滞留 = 进入 × 0.25
    T 增益：离开 = 进入 × 2.00 + 0.30（放大 + 自激造能基数），无滞留
- 扰动：把某一爻(位置 0..8)改为另一三态 → 重算整条链路，对比演化前后。
输出：逐爻进入/离开/滞留、各层吞吐、最终对外释放量、判定/承载/增益数、自适配等级、演化影响分析。
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集_规范校正版.json")

# 量化流模型（示意系数）
COEF = {"D": 0.60, "R": 0.75, "T": 2.00}   # 离开系数
SELF = {"D": 0.0, "R": 0.0, "T": 0.30}     # 自激造能基数（T 无输入也造能）
POSN = ["下底", "下中", "下顶", "中底", "中中", "中顶", "上底", "上中", "上顶"]
LAYER = {0: "下", 3: "中", 6: "上"}

def _level(seq):
    from level9 import level9
    return level9(tuple(seq))

def flow(seq, init=1.0):
    """沿9爻从下到上流动，返回每爻节点明细 + 最终输出。"""
    if len(seq) != 9:
        raise ValueError("需要9爻序列")
    x = init
    nodes = []
    for i, c in enumerate(seq):
        if c == "T":
            leave = x * COEF["T"] + SELF["T"]
            hold = 0.0
            note = "放大" + ("+自激" if x < 0.001 else "")
        elif c == "R":
            leave = x * COEF["R"]
            hold = x - leave
            note = "放行"
        else:  # D
            leave = x * COEF["D"]
            hold = x - leave
            note = "削减"
        nodes.append({
            "pos": i, "name": POSN[i], "c": c,
            "in": round(x, 4), "out": round(leave, 4),
            "hold": round(hold, 4), "note": note,
        })
        x = leave
    return nodes, round(x, 4)

def metrics(nodes, seq, final_out):
    total_hold = round(sum(n["hold"] for n in nodes), 4)
    nR, nD, nT = seq.count("R"), seq.count("D"), seq.count("T")
    return {
        "判定": nR, "承载": nD, "增益": nT,
        "最终输出": final_out, "累计滞留": total_hold,
        "自适配": _level(seq),
    }

def perturb(seq, idx, newc):
    """把第 idx 爻改为 newc，返回新9爻序列。"""
    s = list(seq)
    s[idx] = newc
    return "".join(s)

def evolve(seq, idx, newc, init=1.0):
    """扰动前后对比。seq=原9爻, idx=扰动位, newc=新三态。"""
    old_nodes, old_out = flow(seq, init)
    new_seq = perturb(seq, idx, newc)
    new_nodes, new_out = flow(new_seq, init)
    return {
        "原序列": seq, "新序列": new_seq,
        "扰动位": idx, "扰动位名称": POSN[idx], "原态": seq[idx], "新态": newc,
        "原指标": metrics(old_nodes, seq, old_out),
        "新指标": metrics(new_nodes, new_seq, new_out),
        "原节点": old_nodes, "新节点": new_nodes,
        "输出变化": round(new_out - old_out, 4),
        "滞留变化": round(metrics(new_nodes, new_seq, new_out)["累计滞留"]
                          - metrics(old_nodes, seq, old_out)["累计滞留"], 4),
    }

def demo():
    """若干典型卦的扰动演示。"""
    cases = [
        ("全衡·全扬·厚藏", "RRR" + "TTT" + "DDD", 4, "D"),   # 中层中位 T→D
        ("全衡·全扬·厚藏", "RRR" + "TTT" + "DDD", 0, "T"),   # 上层底层 R→T
        ("扬衡·启生·待衡", "DTR" + "DDT" + "DDR", 5, "D"),   # 中层顶层 R→D
    ]
    print("=== 动态推演演示 ===")
    for title, seq, idx, newc in cases:
        e = evolve(seq, idx, newc)
        print(f"\n[{title}] {seq}  (扰动 {e['扰动位名称']}: {e['原态']}→{e['新态']})")
        print(f"  原: 输出{e['原指标']['最终输出']} 滞留{e['原指标']['累计滞留']} 判/承/增={e['原指标']['判定']}/{e['原指标']['承载']}/{e['原指标']['增益']} 自适配{e['原指标']['自适配']}")
        print(f"  新: 输出{e['新指标']['最终输出']} 滞留{e['新指标']['累计滞留']} 判/承/增={e['新指标']['判定']}/{e['新指标']['承载']}/{e['新指标']['增益']} 自适配{e['新指标']['自适配']}")
        print(f"  影响: 输出{'+' if e['输出变化']>=0 else ''}{e['输出变化']}  滞留{'+' if e['滞留变化']>=0 else ''}{e['滞留变化']}")

if __name__ == "__main__":
    demo()
