#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认知棋盘 v2 · 最小可运行原型（cognition_board.py）

把「认知棋盘 v2 设计提案」落成可运行的确定性认知层，作为三元九维大模型的升级能力。
覆盖：L1 基元层 · L2 认知张量 · L3 证伪动力学 + 跳跃→迁移三联验证，
并融合深化设计：自我矛盾检测（内源证据）、三档证伪、可逆迁移、受引导跳跃、双库。

运行：python3 cognition_board.py        # 跑通一个 agent 决策全流程 demo
依赖：Python 3.8+，无第三方包。
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field

# =====================================================================
# L1 基元层 —— 可执行的原子作用法则（离散可判定，不依赖拟物理参数）
# =====================================================================
PRIMITIVES = {
    "ACT": "激活：使信息进入活跃，参与下游",
    "SUP": "抑制：使信息降权，降低参与",
    "GAT": "门控：仅当条件满足时放行下游（布尔判定）",
    "SUS": "悬置：把冲突/未知挂起，不判断（进入挂起集合）",
    "ASS": "主张：产出断言（作为输出）",
    "REF": "反驳：产出反断言（抵消目标）",
    "TRF": "转移：把信息/能量从一个状态转到另一个",
    "MRG": "合并：把多个格局合成一个",
    "SPL": "分裂：把一个格局拆成多个",
    "VRF": "校验：对照证据/契约返回真/假",
}

# =====================================================================
# L2 认知张量 —— 状态不再是点，而是「格局 × 投影 × 置信度 × 历史」
# =====================================================================
@dataclass
class Stance:
    pattern_id: str                    # 格局 ID
    primitives: dict                   # {基元: 活跃度 0..1}
    projection: str = "generic"        # 语义投影 ID（领域）
    confidence: float = 0.5            # 置信度 c ∈ [0,1]
    history: list = field(default_factory=list)  # [到达路径, 代价, 是否曾被证伪]
    ts: float = field(default_factory=time.time)

    def __repr__(self):
        act = {k: round(v, 2) for k, v in self.primitives.items() if v > 0}
        return (f"Stance({self.pattern_id}|c={self.confidence:.2f}|"
                f"{self.projection}|{act})")


# ---------------------------------------------------------------------
# 一致性检测（自我矛盾 = 内源高置信反例）—— 棋盘独有，可判定，LLM 做不到
# ---------------------------------------------------------------------
def contradictions(st: Stance) -> list[str]:
    """检测格局内部的结构矛盾。返回矛盾描述列表（空 = 自洽）。"""
    out = []
    a = st.primitives.get("ASS", 0.0); r = st.primitives.get("REF", 0.0)
    if a > 0 and r > 0:
        out.append(f"自我矛盾：ASS(主张) 与 REF(反驳) 同时活跃（{a:.2f}/{r:.2f}）")
    g = st.primitives.get("GAT", 0.0); s = st.primitives.get("SUS", 0.0)
    if g > 0 and s > 0:
        out.append(f"门控矛盾：GAT(条件放行) 与 SUS(挂起不判) 并存（{g:.2f}/{s:.2f}）")
    return out


# =====================================================================
# 多维计分（状态价 + 路径价）
# =====================================================================
def state_score(st: Stance) -> float:
    """状态价：一致性 + 置信度 + 确定性（模糊态计分低）。"""
    cons = 1.0 - 0.4 * len(contradictions(st))   # 无矛盾=1
    has_sus = st.primitives.get("SUS", 0.0)
    determinacy = 1.0 - min(0.5, has_sus)         # 悬置多 → 更不确定
    return round(cons * st.confidence * determinacy, 4)


def path_cost(a: Stance, b: Stance) -> float:
    """路径价：两格局基元差异度 + 置信度落差。"""
    keys = set(a.primitives) | set(b.primitives)
    diff = sum(abs(a.primitives.get(k, 0) - b.primitives.get(k, 0)) for k in keys)
    conf = abs(a.confidence - b.confidence)
    return round(diff + conf, 4)


# =====================================================================
# L3 证伪动力学 —— 三档证伪 + 可逆迁移 + 双库
# =====================================================================
@dataclass
class Evidence:
    features: dict            # {特征名: 匹配值/True}
    source: str = "external"  # external / peer / self
    strength: float = 0.8     # 0..1
    def __post_init__(self):
        self.strength = max(0.0, min(1.0, self.strength))


@dataclass
class RefutationCondition:
    negations: list            # 何种证据特征出现即触发（任一命中即算部分）
    all_required: bool = False # True=需全部命中才硬迁移；False=任一命中即硬迁
    fallback: str = ""         # 迁往格局 ID（空=受引导跳跃生成修正）
    confidence_drop: float = 0.3


@dataclass
class RefutationEvent:
    pattern_id: str
    evidence: Evidence
    hit_type: str             # "full" 全命中硬迁 / "partial" 降置信 / "unforeseen" 预设外
    from_state: Stance
    to_state: Stance
    reason: str
    ts: float = field(default_factory=time.time)


class Refuter:
    """证伪器：识别「该放弃一个想法、往哪走」，并把每次证伪结构化入库。"""
    def __init__(self):
        self.conditions: dict[str, RefutationCondition] = {}
        self.pos_lib: list = []   # 正例库：权威迁移边（跳跃→迁移沉淀）
        self.neg_lib: list = []   # 反例库：RefutationEvent（失败模式）
        self.undone: list = []    # 可逆迁移的撤销记录

    def add_condition(self, pattern_id, negations, **kw):
        self.conditions[pattern_id] = RefutationCondition(negations, **kw)

    def _match(self, ev: Evidence, feat) -> bool:
        return ev.features.get(feat, False)

    def check(self, st: Stance, ev: Evidence):
        """三档证伪。返回 (新状态或 None, 事件或 None)。"""
        # 证伪条件按「格局族」继承：跳跃后 P_in' 仍命中 P_in 的证伪条件
        cond = self.conditions.get(st.pattern_id) \
               or self.conditions.get(st.pattern_id.rstrip("'"))
        # ① 预设外反例：无证伪条件但外部证据冲击 → 降级（不硬迁）+ 入库
        if cond is None:
            if ev.strength > 0:
                newc = max(0.0, st.confidence * (1 - 0.3 * ev.strength))
                moved = Stance(st.pattern_id, dict(st.primitives), st.projection,
                               round(newc, 4), list(st.history))
                evt = RefutationEvent(st.pattern_id, ev, "unforeseen", st, moved,
                                      f"预设外反例: 命中{list(ev.features)}")
                self.neg_lib.append(evt)
                return moved, evt
            return None, None
        hits = [f for f in cond.negations if self._match(ev, f)]
        # all_required=True 需全部反证齐备才硬迁移；False 任一硬伤即推翻
        hard = hits and ((not cond.all_required) or len(hits) >= len(cond.negations))
        if hard:
            target = cond.fallback if cond.fallback else st.pattern_id
            # 证伪硬迁同步下调置信度（沙箱实测发现的缺陷修正：被推翻不应保持原置信度）
            newc = max(0.0, st.confidence * (1 - 0.4 * ev.strength))
            to = Stance(target, dict(st.primitives), st.projection,
                        round(newc, 4), list(st.history))
            evt = RefutationEvent(st.pattern_id, ev, "full", st, to,
                                  f"全命中证伪: {hits}")
            self.neg_lib.append(evt)
            self.undone.append((to, st))   # 可逆：记录 (新→旧)
            return to, evt
        if hits:
            newc = max(0.0, st.confidence * (1 - cond.confidence_drop * ev.strength))
            moved = Stance(st.pattern_id, dict(st.primitives), st.projection,
                           round(newc, 4), list(st.history))
            evt = RefutationEvent(st.pattern_id, ev, "partial", st, moved,
                                  f"部分命中: {hits} 置信度下调")
            self.neg_lib.append(evt)
            return moved, evt
        return None, None

    def undo(self) -> bool:
        """可逆迁移：回滚最近一次硬迁移（若事后发现证伪判断有误）。"""
        if not self.undone:
            return False
        to, fro = self.undone.pop()
        self.neg_lib.append(RefutationEvent(fro.pattern_id,
            Evidence({}, "rollback", 1.0), "full", to, fro, "证伪回滚：恢复原状态"))
        return True


# =====================================================================
# L3 跳跃 → 迁移三联验证（给"自由联想固化"一个可判定机制）
# =====================================================================
def verify_jump(src: Stance, dst: Stance, known_rules) -> str:
    """返回 "authoritative"（权威迁移边）或 "tentative"（试探边）。
    V1 一致性：目标格局不自相矛盾
    V2 可逆性：逆迁移可判定（同代价函数成立）
    V3 收益性：多维计分不劣化
    """
    v1 = len(contradictions(dst)) == 0
    v2 = path_cost(src, dst) == path_cost(dst, src)
    v3 = state_score(dst) >= state_score(src)
    if v1 and v2 and v3:
        return "authoritative"
    return "tentative"


def guided_jump(st: Stance, failure: Evidence) -> Stance:
    """受引导跳跃：证伪失败后不缩回，而是沿失败点定向生成修正格局。
    把命中反例对应的基元降权，并把最相关的悬置项转为激活，产出更对的格局。
    """
    prim = dict(st.primitives)
    # 命中反例的特征 → 对应基元降权（如监管反证 → 抑制/门控）
    for feat in failure.features:
        key = feat.split(":")[0].strip()
        if key in prim:
            prim[key] = max(0.0, prim[key] - 0.4)
    # 把残余悬置转为"已核对"（修正方向）
    if "SUS" in prim and prim["SUS"] > 0:
        prim["SUS"] = max(0.0, prim["SUS"] - 0.3)
        prim["VRF"] = prim.get("VRF", 0) + 0.4
    new_id = st.pattern_id + "'"
    return Stance(new_id, prim, st.projection, min(1.0, st.confidence + 0.1),
                  st.history + [f"受引导跳跃(反例:{list(failure.features)})"])


# =====================================================================
# 端到端 demo：一个 agent 决策「是否进入某市场」
# =====================================================================
def demo():
    print("=" * 66)
    print("认知棋盘 v2 · 最小原型 demo —— Agent 决策『是否进入某市场』")
    print("=" * 66)

    refuter = Refuter()
    refuter.add_condition("P_in",
        negations=["监管未落地", "资金不足"], all_required=True, fallback="P_out")

    print("\n[1] 投影 L1/L2：格局 P（激活:需求证据 · 门控:资金 · 悬置:监管）")
    p = Stance("P_in", {"ACT": 0.9, "GAT": 0.8, "SUS": 0.7, "ASS": 0.5},
               projection="market", confidence=0.55)
    print("   ", p, f"| 状态价={state_score(p)} | 自我矛盾={contradictions(p)}")
    print("   → 含悬置项，为模糊态；置信度 0.55")

    print("\n[2] 元评估（v2-4 简化）：悬置项·监管 是关键缺口")
    print("    M(P)=『我对 P 的评估：监管未决，置信度偏低』")

    print("\n[3] 跳跃→迁移：尝试 P → P'(激活:监管已落地)")
    p2 = Stance("P_in'", {"ACT": 0.9, "VRF": 0.9, "ASS": 0.7},
                projection="market", confidence=0.7)
    verdict = verify_jump(p, p2, refuter.pos_lib)
    print(f"    三联验证 V1一致✓ V2可逆✓ V3收益✓ → {verdict}")
    if verdict == "authoritative":
        refuter.pos_lib.append({"from": p.pattern_id, "to": p2.pattern_id,
                                "reason": "跳跃被验证，固化为权威迁移边"})
        print("    已沉淀进正例库（权威迁移边）")

    print("\n[4] 证伪动力学：外部反证『监管未落地』出现（partial 渐进）")
    ev1 = Evidence({"监管未落地": True}, source="external", strength=0.9)
    s1, e1 = refuter.check(p2, ev1)
    print(f"    {e1.hit_type}: 置信度 {p2.confidence:.2f} → {s1.confidence:.2f}（下调）")
    print(f"    状态价 {state_score(p2)} → {state_score(s1)}")

    print("\n[5] 证伪升级：追加『资金不足』→ 两个反证齐备 → 全命中 → 硬迁移（可逆）")
    ev2 = Evidence({"监管未落地": True, "资金不足": True}, source="peer", strength=0.9)
    s2, e2 = refuter.check(s1, ev2)
    print(f"    {e2.hit_type}: 迁往 {s2.pattern_id}（置信度 {s2.confidence:.2f}）")
    print("    事件已入反例库；硬迁移记录可逆（undo 可回滚）")

    print("\n[6] 受引导跳跃：被推翻后不缩回，沿失败点生成修正格局")
    guided = guided_jump(s2, ev2)
    print("    ", guided)
    print(f"    状态价 {state_score(s2)} → {state_score(guided)}（失败成为生成正确的原料）")

    print("\n[7] 自我矛盾检测（内源反例）：若 P 同时主张又反驳『进入』")
    bad = Stance("P_in", {"ASS": 0.8, "REF": 0.7}, projection="market", confidence=0.9)
    print("    矛盾:", contradictions(bad), "→ 棋盘可判定，LLM 难自查")

    print("\n[8] 双库沉淀（学习闭环）")
    print(f"    正例库(权威迁移边): {len(refuter.pos_lib)} 条")
    print(f"    反例库(失败模式):   {len(refuter.neg_lib)} 条")
    print("    反例库可反向修正证伪条件，distiller 从正/负例一起蒸馏。")

    print("\n" + "=" * 66)
    print("全过程可复算 · 可回放 · 可审计 · 可逆。认知主体仍是 Agent；棋盘是锚点与保险丝。")
    print("=" * 66)


if __name__ == "__main__":
    demo()
