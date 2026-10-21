#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认知棋盘 v2 · 元棋盘（L4 自指/反思层）最小原型（meta_board.py）

实现 v2-4 元棋盘：让认知状态「审视自身」。
    普通层：思考 A → 状态 X
    元层  ：状态 X 成为被审视对象 → M(X) = 对 X 的评估（确定性、可复算）
    递归  ：M(M(X)) = 对评估的评估（自省、策略调整）
元层规则同样确定性、可复算、可证伪。

运行：python3 meta_board.py
依赖：Python 3.8+，无第三方包。
"""
from __future__ import annotations
from cognition_board import Stance, Evidence, Refuter, contradictions, state_score


# ---------------------------------------------------------------------
# M(X)：确定性元评估 —— 不看内容，只看结构（一致性/置信度/悬置/支撑）
# ---------------------------------------------------------------------
def meta_evaluate(st: Stance) -> dict:
    """对格局 X 做元评估，返回结构化评估（可复算、可证伪）。"""
    cons = contradictions(st)
    sus = st.primitives.get("SUS", 0.0)
    ass = st.primitives.get("ASS", 0.0)
    act = st.primitives.get("ACT", 0.0)
    vrf = st.primitives.get("VRF", 0.0)
    conf = st.confidence

    health = round(1.0 - 0.3 * len(cons), 3)          # 结构健康度
    inflated = conf > 0.7 and (len(cons) > 0 or sus > 0.5)   # 置信度虚高
    unsupported = ass > 0.6 and (act < 0.3 and vrf < 0.3)    # 无源主张

    risks = []
    if len(cons) > 0: risks.append(f"结构矛盾×{len(cons)}")
    if sus > 0.5:     risks.append("未决悬置·不确定性未显式标记")
    if unsupported:   risks.append("无源主张·缺证据支撑")
    if inflated:      risks.append("置信度虚高")

    advice = []
    if inflated:     advice.append("下调置信度，先补校验(VRF)")
    if unsupported:  advice.append("降权断言，补激活/校验")
    if len(cons) > 0: advice.append("分裂或降权冲突基元")
    if not advice and conf < 0.5: advice.append("证据充分，可上调置信度")
    if not advice:    advice.append("结构健康，维持")

    return {"对象": st.pattern_id, "健康度": health, "置信度": conf,
            "虚高": inflated, "无源主张": unsupported,
            "风险": risks, "建议": advice}


# ---------------------------------------------------------------------
# 策略调整：依据元评估，确定性地产出修正后的格局
# ---------------------------------------------------------------------
def strategize(st: Stance, meta: dict) -> Stance:
    prim = dict(st.primitives)
    conf = st.confidence
    if meta["虚高"]:
        conf = round(conf * 0.7, 3)
        prim["VRF"] = min(1.0, prim.get("VRF", 0.0) + 0.3)
    if meta["无源主张"]:
        prim["ASS"] = max(0.0, prim.get("ASS", 0.0) - 0.3)
    # 消除矛盾：冲突基元降到 0
    if prim.get("ASS", 0.0) >= prim.get("REF", 0.0):
        prim["REF"] = 0.0
    else:
        prim["ASS"] = 0.0
    # 未决悬置 → 转为已核对（消除不确定性）
    if prim.get("SUS", 0.0) > 0:
        prim["VRF"] = min(1.0, prim.get("VRF", 0.0) + prim["SUS"] * 0.5)
        prim["SUS"] = 0.0
    return Stance(st.pattern_id + "'", prim, st.projection, conf,
                  st.history + ["元策略调整"])


# ---------------------------------------------------------------------
# M(M(X))：递归自省 —— 对评估本身再评估，检查评估是否可靠
# ---------------------------------------------------------------------
def recursive(st: Stance, depth: int = 2) -> list:
    chain = [{"层": "L0·对象", "格局": st.pattern_id, "置信度": st.confidence,
              "矛盾": contradictions(st), "状态价": state_score(st),
              "认知层": "L0·本能·知道对象"}]
    cur = meta_evaluate(st)
    for d in range(1, depth + 1):
        # 自省：元评估自身是否过度悲观/乐观
        if cur["置信度"] < 0.4 and cur["健康度"] > 0.8:
            bias = "过度悲观（低估健康结构）"
        elif cur["置信度"] > 0.7 and len(cur["风险"]) > 0 and cur["健康度"] < 0.6:
            bias = "过度乐观（低估风险）"
        else:
            bias = "平稳（评估可靠）"
        # 自省偏差 → 三分认知态（知道/不知道/转化）：过度悲观=不知道、过度乐观=转化、平稳=知道
        tri = {"过度悲观": "不知道", "过度乐观": "转化", "平稳": "知道"}.get(bias.split("（")[0], "知道")
        chain.append({"层": f"L{d}·元评估", "对象": cur.get("对象", "(递归)"),
                      "置信度": cur["置信度"], "健康度": cur["健康度"],
                      "风险": cur["风险"], "自省": bias,
                      "认知层": f"L{d}·{tri}（自指第 {d} 层）"})
        # 下一层：以「评估的健康度」为新对象继续递归（收敛则停）
        cur = {"对象": f"(L{d}评估)", "置信度": cur["健康度"],
               "健康度": round(max(0.0, 1 - 0.5 * len(cur["风险"])), 3),
               "风险": cur["风险"] or ["无"]}
    return chain


# ---------------------------------------------------------------------
# 三分认知层（认知轴 · 自指递归编码）
# 基本单元：每个认知状态 = 知道(0/阳) · 不知道(1/阴) · 转化(2/变) 三元。
# 递归：对认知状态自身再三分 → 第 n 层 = 3^n 种认知状态。
#   L9 = 3^9 = 19683，与「三元九维19683」状态空间同构 —— 认知轴 = 体系第 10 根轴。
# ---------------------------------------------------------------------
TRI_CN = {0: "知道", 1: "不知道", 2: "转化"}
TRI_SYM = {0: "阳", 1: "阴", 2: "变"}
TRI_SHORT = {0: "知", 1: "不", 2: "变"}

# 代表性认知路径的层名（含用户措辞）
_GLOSS = {
    ():        "L0·本能认知",
    (0,):      "L1·知道（确信）",
    (1,):      "L1·不知道（缺口）",
    (2,):      "L1·转化（自省起点）",
    (0, 0):    "L2·知道自己知道（元确信）",
    (0, 1):    "L2·知道自己不知道（元缺口）",
    (1, 0):    "L2·不知道自己知道（隐知·潜能）",
    (1, 1):    "L2·不知道自己不知道（盲点）",
    (2, 0):    "L2·转化中知道（动态确信）",
    (2, 1):    "L2·转化中不知道（开放缺口）",
    (0, 0, 0): "L3·知道自己知道自己知道",
    (0, 1, 1): "L3·知道自己不知道自己不知道",
    (1, 1, 0): "L3·不知道自己不知道自己知道",
}


def cognition_path(path: tuple) -> dict:
    """给一条自指认知路径（每层 0/1/2）→ 认知层坐标 + 层名 + 深度 + 状态空间。
    编码：code = 层区间偏移(base) + 层内码(inner)，跨层唯一、层层递增。"""
    depth = len(path)
    base = sum(3 ** d for d in range(0, depth))       # L0(空态=1)+L1..L(depth-1) 的状态数偏移
    inner = 0
    for t in path:
        inner = inner * 3 + t                          # 保持路径顺序权重递减
    code = base + inner
    name = "→".join(TRI_CN[t] for t in path) if path else "本能"
    sym = "".join(TRI_SYM[t] for t in path) if path else "—"
    return {"path": path, "code": code, "depth": depth,
            "layer": f"L{depth}", "name": name, "sym": sym,
            "gloss": _GLOSS.get(path, f"L{depth}·{name}"), "space": 3 ** depth}


def cognition_spectrum(depth: int = 3) -> list:
    """列出 0..3^depth-1 的全部认知状态（每层三分、自指递归）。"""
    rows = []
    for code in range(3 ** depth):
        path = []
        x = code
        for _ in range(depth):
            path.append(x % 3)
            x //= 3
        rows.append(cognition_path(tuple(reversed(path))))
    return rows


def cognition_total(levels: int = 9) -> int:
    """认知轴总状态数：L1~L9 各层三分累计 = 3 + 9 + 27 + … + 3^9。"""
    return sum(3 ** d for d in range(1, levels + 1))


# ---------------------------------------------------------------------
# demo：一个 Agent 的高置信但结构不稳的结论，被元棋盘自省并修正
# ---------------------------------------------------------------------
def demo():
    print("=" * 66)
    print("认知棋盘 v2 · 元棋盘（L4 自指/反思层）demo —— 审视自己的结论")
    print("=" * 66)

    print("\n[1] 一个 Agent 的结论 X：高置信 0.90，但含矛盾 + 未决悬置")
    X = Stance("X_结论", {"ACT": 0.9, "SUS": 0.7, "ASS": 0.8, "REF": 0.7},
               projection="决策", confidence=0.90)
    print("   ", X, f"| 状态价={state_score(X)} | 矛盾={contradictions(X)}")

    print("\n[2] M(X) 元评估：不看内容，只判结构")
    m = meta_evaluate(X)
    print(f"   健康度={m['健康度']} | 置信度={m['置信度']} | 虚高={m['虚高']} | 无源主张={m['无源主张']}")
    print("   风险:", m["风险"])
    print("   建议:", m["建议"])
    print("   → 元棋盘发现『置信度虚高』：结构不稳(矛盾+悬置)却高置信，LLM 本身难自查")

    print("\n[3] 策略调整：依元评估确定性地产出修正 X'")
    Xp = strategize(X, m)
    print("   ", Xp, f"| 状态价={state_score(Xp)} | 矛盾={contradictions(Xp)}")
    print("   → 结构矛盾消除、悬置转为已核对(VRF)；置信度从虚高 0.90 下调至 0.63（更诚实）")

    print("\n[4] M(M(X)) 递归自省：评估自身是否可靠")
    for r in recursive(X, depth=2):
        print(f"   {r['层']}: 置信度={r.get('置信度')} 健康度={r.get('健康度')} "
              f"风险={r.get('风险')} 自省={r.get('自省','—')}")

    print("\n[5] 元层可证伪：元评估结论本身也受证据约束")
    ref = Refuter()
    ref.add_condition("X_结论'", ["关键前提被推翻"], all_required=False, fallback="X_撤回")
    ev = Evidence({"关键前提被推翻": True}, source="external", strength=0.95)
    s, e = ref.check(Xp, ev)
    print(f"   证据命中 → {e.hit_type}：迁往 {s.pattern_id}（元修正后的结论也接受证伪）")

    print("\n[6] 三分认知层（认知轴）：元自省挂上可复算的认知坐标")
    print("   每个认知状态 = 知道/不知道/转化；对自身再三分 → 第 n 层 3^n 种认知状态")
    for p in [(), (1,), (0, 1), (1, 0), (0, 0, 1), (2, 1)]:
        c = cognition_path(p)
        print(f"   认知路径 {c['sym']:<4} → code={c['code']:<4} {c['layer']} "
              f"{c['gloss']:<28}（空间 3^{c['depth']}={c['space']}）")
    print(f"   累计状态空间 L1~L9 = {cognition_total(9):,}（L9 层 = 3^9 = {3**9:,}，与三元九维同构）")

    print("\n[7] 认知轴挂到元棋盘：自省偏差 → 三分认知态")
    for r in recursive(X, depth=2):
        print(f"   {r['层']:<12} 认知层={r.get('认知层','—')}  自省={r.get('自省','—')}")

    print("\n" + "=" * 66)
    print("元棋盘=受控递归的自省：M(X)→策略调整→M(M(X))→可证伪。反思不是玄学，是确定性操作。")
    print("三分认知层=自指递归的认知坐标：知道/不知道/转化，L9=19683 —— 思维维度上的体系同构。")
    print("=" * 66)


if __name__ == "__main__":
    demo()
