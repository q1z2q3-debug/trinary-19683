#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认知棋盘 v2 · 多 Agent 共享协议最小原型（multi_agent.py）

实现 L5 生态层：多个 Agent 在共享棋盘上工作，分歧定位到具体迁移边、
用共享证据证伪对撞、收敛到可复算联合链。复用 cognition_board 的确定性核心。

运行：python3 multi_agent.py
依赖：Python 3.8+，无第三方包。
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from cognition_board import (Stance, Evidence, Refuter, contradictions,
                             state_score, path_cost)


@dataclass
class Agent:
    name: str
    stance: Stance

    def __repr__(self):
        return f"Agent[{self.name}]{self.stance}"


# ---------------------------------------------------------------------
# 共享棋盘：共享证伪器 + 权威迁移边 + 事件日志（可回放）
# ---------------------------------------------------------------------
class SharedBoard:
    def __init__(self):
        self.refuter = Refuter()
        self.edges: list = []        # 权威迁移边
        self.log: list = []          # 联合推导链（可复算、可回放）
        self.ts = 0

    def add_condition(self, pattern_id, negations, **kw):
        self.refuter.add_condition(pattern_id, negations, **kw)

    def record(self, action, agent, fro, to, confidence, note=""):
        self.ts += 1
        self.log.append({
            "step": self.ts, "agent": agent, "action": action,
            "from": fro, "to": to, "confidence": round(confidence, 4), "note": note,
        })

    def consensus(self):
        """收敛出的可复算联合链（逐条可回放、可裁判）。"""
        return [dict(r) for r in self.log]


# ---------------------------------------------------------------------
# 冲突检测：把分歧「定位到具体迁移边/基元」，而不是一句"我觉得你不对"
# ---------------------------------------------------------------------
def conflict_detect(a: Stance, b: Stance) -> list:
    out = []
    # 断言冲突：A 主张进入 vs B 反驳进入
    if a.primitives.get("ASS", 0) > 0.5 and b.primitives.get("REF", 0) > 0.5:
        out.append("断言冲突：A 主张(ASS) 与 B 反驳(REF) 针对同一命题")
    # 门控冲突：A 判定条件通过 vs B 悬置不判
    if a.primitives.get("GAT", 0) > 0.5 and b.primitives.get("SUS", 0) > 0.5:
        out.append("判定冲突：A 认为条件已满足(GAT) 而 B 悬置未决(SUS)")
    # 定位分歧焦点：两格局基元差异最大者 = 关键迁移边
    keys = set(a.primitives) | set(b.primitives)
    diffs = [(k, abs(a.primitives.get(k, 0) - b.primitives.get(k, 0)))
             for k in keys]
    top = max(diffs, key=lambda x: x[1])
    out.append(f"分歧焦点：基元「{top[0]}」差异最大（A={a.primitives.get(top[0],0):.2f} vs B={b.primitives.get(top[0],0):.2f}），冲突收敛到该迁移边")
    return out


# ---------------------------------------------------------------------
# 合并：两 Agent 到达同格局族 → 置信度加权合并（证据合并）
# ---------------------------------------------------------------------
def merge(a: Stance, b: Stance) -> Stance:
    wa, wb = a.confidence, b.confidence
    conf = min(1.0, 0.5 * (a.confidence + b.confidence) + 0.5 * max(a.confidence, b.confidence))
    prim = {k: max(a.primitives.get(k, 0), b.primitives.get(k, 0))
            for k in set(a.primitives) | set(b.primitives)}
    return Stance(a.pattern_id, prim, a.projection, round(conf, 4),
                  a.history + ["多Agent证据合并"])


# ---------------------------------------------------------------------
# demo：两个 Agent 评估同一决策「是否进入某市场」，从冲突到共识
# ---------------------------------------------------------------------
def demo():
    print("=" * 68)
    print("认知棋盘 v2 · 多 Agent 共享协议 demo —— 进入/审慎 两派收敛")
    print("=" * 68)

    board = SharedBoard()
    # 共享证伪条件：监管未落地 + 资金不足 齐备 → 进入派被推翻
    board.add_condition("P_enter", ["监管未落地", "资金不足"],
                        all_required=True, fallback="P_hold")

    print("\n[1] 两个 Agent 各自投影（同一决策，不同判定）")
    A = Agent("进取", Stance("P_enter", {"ACT": 0.9, "GAT": 0.7, "ASS": 0.8, "SUS": 0.2},
                             projection="market", confidence=0.70))
    B = Agent("审慎", Stance("P_hold", {"ACT": 0.8, "SUS": 0.8, "ASS": 0.3, "REF": 0.6},
                             projection="market", confidence=0.65))
    print("   ", A)
    print("   ", B)
    board.record("投影", A.name, "-", A.stance.pattern_id, A.stance.confidence)
    board.record("投影", B.name, "-", B.stance.pattern_id, B.stance.confidence)

    print("\n[2] 共享棋盘冲突检测：把分歧定位到具体迁移边")
    for c in conflict_detect(A.stance, B.stance):
        print("   ✦", c)

    print("\n[3] 共享证据对撞 1：『监管未落地』出现（外部契约）")
    ev1 = Evidence({"监管未落地": True}, source="external", strength=0.9)
    sA1, eA1 = board.refuter.check(A.stance, ev1)
    print(f"   命中进入派(A)：{eA1.hit_type} → 置信度 {A.stance.confidence:.2f}→{sA1.confidence:.2f}")
    A.stance = sA1
    board.record("证伪", A.name, "P_enter", sA1.pattern_id, sA1.confidence, "监管未落地")

    print("\n[4] 共享证据对撞 2：追加『资金不足』→ 齐备 → 进入派硬迁移（可逆）")
    ev2 = Evidence({"监管未落地": True, "资金不足": True}, source="external", strength=0.9)
    sA2, eA2 = board.refuter.check(A.stance, ev2)
    print(f"   命中进入派(A)：{eA2.hit_type} → 迁往 {sA2.pattern_id}")
    A.stance = sA2
    board.record("硬迁移", A.name, "P_enter", sA2.pattern_id, sA2.confidence, "双反证齐备")

    print("\n[5] 收敛：A 与 B 到达同格局族 → 置信度加权合并")
    joined = merge(A.stance, B.stance)
    print(f"   联合格局 {joined.pattern_id} | 联合置信度 {joined.confidence:.2f}")
    board.record("合并", A.name + "+" + B.name, A.stance.pattern_id, joined.pattern_id,
                 joined.confidence, "多Agent证据合并收敛")

    print("\n[6] 可复算联合推导链（可回放、可裁判、可证伪）")
    print(f"    {'step':<4}{'agent':<12}{'action':<8}{'to':<10}{'conf':<8}note")
    for r in board.consensus():
        print(f"    {r['step']:<4}{r['agent']:<12}{r['action']:<8}{r['to']:<10}"
              f"{r['confidence']:<8}{r['note']}")

    print("\n" + "=" * 68)
    print("分歧被定位到具体迁移边，用共享证据证伪对撞收敛；每一步可回放、可裁判、可证伪。")
    print("=" * 68)


if __name__ == "__main__":
    demo()
