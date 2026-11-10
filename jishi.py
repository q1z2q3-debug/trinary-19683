#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""稽式（JISHI）· 认知法式校验器

稽式：可长久稽考、恒常遵循的法式。出《道德经》第六十五章
「知此两者，亦稽式。常知稽式，是谓玄德。」

与「智」相对——智是 LLM 的概率机巧：会幻觉、不可复算、随语气漂移；
稽式是给「智」套上的恒常法式约束层：不追求更聪明，而追求恒常可稽。

一个认知单元要成为「稽式」，必须同时通过四铁律：
  1. 可复算  recomputable  —— 同输入必同输出，带稳定审计哈希
  2. 可推翻  falsifiable   —— 自带「什么证据会推翻我」
  3. 可逆    reversible    —— 带 undo 令牌，迁移不锁死
  4. 可稽考  auditable     —— 每步留审计轨迹

缺任何一条，它就不是「式」，只是一句随起随灭的话。

运行：python3 jishi.py        # 无第三方依赖，Python 3.8+
"""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field

# 四铁律（式：法式本身的条款）
RULES = ["recomputable", "falsifiable", "reversible", "auditable"]
RULE_CN = {
    "recomputable": "可复算（同输入同输出）",
    "falsifiable":  "可推翻（自带证伪条件）",
    "reversible":   "可逆（带 undo 令牌）",
    "auditable":    "可稽考（带审计轨迹）",
}


@dataclass
class JishiRecord:
    """一个待入「稽式」的认知单元。"""
    assertion: str                              # 断言（式：它在法式里的位置）
    refutation_condition: str = ""             # 证伪条件（稽：什么证据推翻它）
    undo_token: str = ""                        # 可逆令牌
    trace: list = field(default_factory=list)  # 审计轨迹
    payload: dict = field(default_factory=dict)  # 可复算的输入指纹
    ts: float = field(default_factory=time.time)

    def audit_hash(self) -> str:
        """审计哈希：同 assertion+payload 必得同签名（可复算的凭证）。

        键序无关（sort_keys），只看语义内容——这正是「式」应有的确定性。"""
        blob = json.dumps(
            {"a": self.assertion, "p": self.payload},
            ensure_ascii=False, sort_keys=True,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def check_jishi(rec: JishiRecord) -> tuple[bool, list]:
    """四铁律校验。返回 (是否成式, 违反项列表)。缺一项即不入稽式。"""
    violations = []
    # 1. 可复算：必须有 payload 输入指纹，否则无从复算
    if not rec.payload:
        violations.append("可复算：缺少 payload 输入指纹")
    # 2. 可推翻：必须写清证伪条件（没有反例可推翻 = 信仰陈述，不是认知命题）
    if not rec.refutation_condition or len(rec.refutation_condition.strip()) < 4:
        violations.append("可推翻：缺少证伪条件（没有什么证据会推翻它）")
    # 3. 可逆：必须有 undo 令牌
    if not rec.undo_token:
        violations.append("可逆：缺少 undo 令牌（迁移会锁死，无法回滚）")
    # 4. 可稽考：必须留审计轨迹
    if not rec.trace:
        violations.append("可稽考：缺少审计轨迹（事后无法稽考）")
    return (len(violations) == 0, violations)


def make_jishi(assertion: str, refutation_condition: str, payload: dict,
               trace: list = None, undo_token: str = None) -> JishiRecord:
    """把一句裸 LLM 断言补全为「稽式」：自动配 undo 令牌，轨迹留痕。"""
    return JishiRecord(
        assertion=assertion,
        refutation_condition=refutation_condition,
        payload=payload,
        trace=trace or ["born@jishi"],
        undo_token=undo_token or ("undo-" + hashlib.sha256(
            f"{assertion}|{time.time()}".encode()).hexdigest()[:10]),
    )


def demo():
    print("=" * 64)
    print("稽式校验 demo · 一个认知单元要成「式」，四铁律缺一不可")
    print("=" * 64)

    cases = [
        ("合格：金融断言（四要素齐备）", make_jishi(
            assertion="沪深300 短期偏多",
            refutation_condition="放量下跌跌破前低 → 推翻，转 DOWN'",
            payload={"close": 4317.25, "rsi14": 29.47, "mom20": -0.0517},
            trace=["born", "verified_by_refuter", "hash=ok"])),

        ("不合格①：没写证伪条件", make_jishi(
            assertion="这只股一定会涨",
            refutation_condition="",          # ← 缺：信仰陈述，不是认知命题
            payload={"close": 100.0},
            trace=["born"])),

        ("不合格②：不可逆 + 无轨迹", JishiRecord(
            assertion="最终结论（拍板，不许回头）",
            refutation_condition="出现反例即修正",
            payload={"x": 1})),                 # ← 缺 undo_token、缺 trace
    ]

    for name, rec in cases:
        ok, bad = check_jishi(rec)
        print(f"\n【{name}】")
        print(f"  断言     ：{rec.assertion}")
        print(f"  审计哈希 ：{rec.audit_hash()}")
        verdict = "✅ 成式（入稽式）" if ok else "❌ 不成式：" + "；".join(bad)
        print(f"  结论     ：{verdict}")

    # 可复算证明：同 payload（键序不同）两次哈希必须一致
    r1 = make_jishi("测试", "反例即推翻", {"a": 1, "b": 2})
    r2 = make_jishi("测试", "反例即推翻", {"b": 2, "a": 1})
    same = r1.audit_hash() == r2.audit_hash()
    print("\n" + "-" * 64)
    print(f"可复算证明：同 payload（键序不同）两次哈希 = "
          f"{r1.audit_hash()} / {r2.audit_hash()}")
    print(f"  → {'一致 ✅（式是确定的，与书写顺序无关）' if same else '不一致 ❌'}")


if __name__ == "__main__":
    demo()
