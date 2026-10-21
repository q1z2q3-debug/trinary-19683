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

# ---------------------------------------------------------------------
# 九变生成算符（阴阳变 → 三元两两组合 → 9种转化型）
# 由「变」驱动推演：不看孤立爻，而看爻与爻之间的转化关系。
#   TRI映射：阴=D(承载/收敛)、阳=R(判定/生发)、变=T(增益/转化)。
#   NINE[(前爻, 后爻)] = (变名, 传递系数, 自激基数)；系数为「示意」假设。
#   对应可视化谱系：凝/交/萌/化/盛/动/敛/发/元变。
# ---------------------------------------------------------------------
NINE = {
    ("D", "D"): ("凝", 0.35, 0.00),   # 阴阴·静凝：承载滞留
    ("D", "R"): ("交", 1.20, 0.00),   # 阴阳·交：生发
    ("D", "T"): ("萌", 0.90, 0.10),   # 阴变·萌：阴中蕴变而萌动
    ("R", "D"): ("化", 0.70, 0.00),   # 阳阴·化：阳化入阴而潜长
    ("R", "R"): ("盛", 0.85, 0.00),   # 阳阳·盛：阳阳相持
    ("R", "T"): ("动", 1.50, 0.00),   # 阳变·动：阳激而变，发动
    ("T", "D"): ("敛", 0.50, 0.00),   # 变阴·敛：变归而敛藏
    ("T", "R"): ("发", 1.80, 0.00),   # 变阳·发：变出而发张
    ("T", "T"): ("元变", 2.20, 0.20),  # 变变·元变：变之变，自激造能
}
TRI_CN = {"D": "阴", "R": "阳", "T": "变"}


def pair_type(prev, cur):
    """返回 (变名, 传递系数, 自激基数)。"""
    return NINE[(prev, cur)]


def drive_flow(seq, init=1.0):
    """由「变」驱动的流动：首爻用自身态基础系数，之后每爻用『前爻→本爻』的变型系数。"""
    if len(seq) != 9:
        raise ValueError("需要9爻序列")
    x = init
    nodes = []
    for i, c in enumerate(seq):
        if i == 0:
            coef = COEF.get(c, 0.6); selfg = SELF.get(c, 0.0)
            tag = f"{TRI_CN[c]}·首爻"
        else:
            name, coef, selfg = NINE[(seq[i - 1], c)]
            tag = f"{TRI_CN[seq[i-1]]}→{TRI_CN[c]}·{name}"
        leave = x * coef + selfg
        hold = x - leave
        nodes.append({
            "pos": i, "name": POSN[i], "c": c, "变型": tag,
            "in": round(x, 4), "out": round(leave, 4),
            "hold": round(hold, 4), "note": tag,
        })
        x = leave
    return nodes, round(x, 4)


def nine_signature(seq):
    """返回9爻的『变签名』：首爻态 + 8个相邻变型 + 各变型计数。"""
    sig = [("首爻", TRI_CN[seq[0]])]
    for i in range(1, len(seq)):
        name, coef, selfg = NINE[(seq[i - 1], seq[i])]
        sig.append((f"{TRI_CN[seq[i-1]]}→{TRI_CN[seq[i]]}", name, coef))
    from collections import Counter
    cnt = Counter(s[1] for s in sig[1:])
    return sig, dict(cnt)


def drive_evolve(seq, idx, newc, init=1.0):
    """变驱动下的扰动对比（由变驱动 + 静态 flow 双视角）。"""
    old_nodes, old_out = drive_flow(seq, init)
    new_seq = perturb(seq, idx, newc)
    new_nodes, new_out = drive_flow(new_seq, init)
    _, old_sig_cnt = nine_signature(seq)
    _, new_sig_cnt = nine_signature(new_seq)
    s_old, s_out = flow(seq, init)
    s_new, s_new_out = flow(new_seq, init)
    return {
        "原序列": seq, "新序列": new_seq,
        "扰动位": idx, "扰动位名称": POSN[idx], "原态": seq[idx], "新态": newc,
        "变签名(原)": old_sig_cnt, "变签名(新)": new_sig_cnt,
        "变驱动输出(原)": old_out, "变驱动输出(新)": new_out,
        "静态flow输出(原)": s_out, "静态flow输出(新)": s_new_out,
        "变驱动变化": round(new_out - old_out, 4),
    }


def demo_nine():
    """由「变」驱动的推演演示：爻间转化签名 + 变驱动 vs 静态流动。"""
    print("=" * 66)
    print("九变生成算符 · 由变驱动的推演 —— 阴阳变 → 三元两两组合 → 9种转化型")
    print("=" * 66)
    print("九变谱系：凝(阴阴) 交(阴阳) 萌(阴变) 化(阳阴) 盛(阳阳) 动(阳变) 敛(变阴) 发(变阳) 元变(变变)")
    case = "RRRTTTDDD"
    sig, cnt = nine_signature(case)
    print(f"\n[1] 变签名：序列 {case}（R阳 T变 D阴）")
    print("   " + "  ".join(f"{a}·{n}" for a, n, c in sig[1:]))
    print("   变型计数:", cnt)
    print(f"\n[2] 由变驱动 vs 静态流动（同一序列）")
    nodes, out = drive_flow(case)
    sn, so = flow(case)
    print(f"   静态flow输出 = {so}")
    print(f"   变驱动输出   = {out}  ← 由爻间转化系数驱动，非静态逐爻")
    print("\n[3] 变驱动下的扰动对比（中层中位 T→D）")
    e = drive_evolve(case, 4, "D")
    print(f"   {e['原序列']} → {e['新序列']}  扰动 {e['扰动位名称']}: {e['原态']}→{e['新态']}")
    print(f"   变签名(原): {e['变签名(原)']}")
    print(f"   变签名(新): {e['变签名(新)']}")
    print(f"   变驱动输出 {e['变驱动输出(原)']} → {e['变驱动输出(新)']}（{'+' if e['变驱动变化']>=0 else ''}{e['变驱动变化']}）")
    print("\n[4] 九变驱动力 = 体系的生成机制：不是 4 个状态(四季)，而是状态的转化(变型)")
    print("=" * 66)


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
    demo_nine()
