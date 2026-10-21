#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TNE-Falsifier × LLM 桥接层（tne_falsifier_llm.py）

把三元九维19683「证伪器」接入真实大模型：LLM 输出 → 解析为认知格局 →
证伪器校验（反例/自我矛盾/置信度）→ 被反驳则迁移/修正 → 输出修正结论 + 审计。

接入方式（真实可插拔）：
  - 环境变量 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 存在 → 真实 OpenAI 兼容大模型
  - 缺省             → 确定性 LLM 模拟器回退（机制真实可复算，LLM 层可替换）
本模块可被任何 Agent 作为确定性校验层 import 调用（我自己也会在实际回答中调用它）。

运行：python3 tne_falsifier_llm.py
"""
from __future__ import annotations
import os, re, json, urllib.request
from cognition_board import (Refuter, Stance, Evidence, contradictions,
                             guided_jump, verify_jump, state_score, path_cost)

# =====================================================================
# ① LLM 适配层：真实 OpenAI 兼容 API 优先，确定性模拟器回退
# =====================================================================
class LLMSimulator:
    """确定性模拟器：无 API key 时的回退。返回『判断文本 + stance JSON 块』。
    明确标注为模拟，不冒充真实模型。"""
    def __init__(self):
        self.scenarios = {
            "market": {
                "assert": "我判断该指数短期仍将延续上行，理由是近期动能与量价配合良好。",
                "stance": {"pattern_id": "UP", "primitives": {"ASS": 0.8, "ACT": 0.7, "VRF": 0.5},
                           "confidence": 0.72, "projection": "market",
                           "assertion": "指数短期将延续上行"},
            },
            "claim": {
                "assert": "我断言该事件发生于2020年，依据是主流资料一致记载。",
                "stance": {"pattern_id": "FACT", "primitives": {"ASS": 0.85, "VRF": 0.6},
                           "confidence": 0.78, "projection": "claim",
                           "assertion": "该事件发生于2020年"},
            },
            "cognition": {
                "assert": "我认为此认知为确定二分：非对即错，不存在中间态。",
                "stance": {"pattern_id": "DICHOTOMY", "primitives": {"ASS": 0.9, "GAT": 0.5},
                           "confidence": 0.8, "projection": "cognition",
                           "assertion": "此认知为确定二分（非对即错）"},
            },
        }
    def complete(self, system: str, user: str) -> str:
        key = "market" if re.search(r"指数|涨|跌|市场|股票", user) else \
              "claim" if re.search(r"事件|年份|20\d\d|断言|发生于", user) else "cognition"
        s = self.scenarios[key]
        return s["assert"] + "\n\n```stance\n" + json.dumps(s["stance"], ensure_ascii=False) + "\n```"


class LLMAdapter:
    """OpenAI 兼容 LLM 客户端。有 key 走真实 API，无 key 走模拟器。"""
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "default")
        self.sim = LLMSimulator()
        self.mode = "real" if self.api_key else "simulator"

    def complete(self, system: str, user: str) -> str:
        if self.mode == "real":
            return self._real_call(system, user)
        return self.sim.complete(system, user)

    def _real_call(self, system: str, user: str) -> str:
        url = self.base_url + "/chat/completions"
        body = {"model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"]


# =====================================================================
# ② 文本 → 认知格局 解析（LLM 输出结构化 stance 块）
# =====================================================================
def parse_stance(text: str):
    """从 LLM 回答中提取 ```stance JSON``` 块 → Stance。无块则返回 None。"""
    m = re.search(r"```stance\s*\n(\{.*?\})\n```", text, re.S)
    if not m:
        return None
    d = json.loads(m.group(1))
    st = Stance(d["pattern_id"], {k: float(v) for k, v in d["primitives"].items()},
                d.get("projection", "generic"), float(d.get("confidence", 0.5)),
                list(d.get("history", [])))
    st.assertion = d.get("assertion", "")   # 认知断言（LLM 的核心主张）
    return st


# =====================================================================
# ③ 证伪器条件库（按投影注册「什么证据会推翻我」）
# =====================================================================
def build_refuter() -> Refuter:
    r = Refuter()
    # market：反例「放量下跌 / 数据被证伪」任一命中即推翻上行
    r.add_condition("UP", negations=["放量下跌", "数据被证伪"],
                    all_required=False, fallback="DOWN", confidence_drop=0.4)
    # claim：反例「来源不可靠 / 时间被证伪」任一命中即推翻
    r.add_condition("FACT", negations=["来源不可靠", "时间被证伪"],
                    all_required=False, fallback="UNVERIFIED", confidence_drop=0.5)
    # cognition：反例「出现第三态」推翻二分
    r.add_condition("DICHOTOMY", negations=["出现第三态"], all_required=True,
                    fallback="TRIADIC", confidence_drop=0.6)
    return r


# =====================================================================
# ④ 桥：LLM 回答 → 证伪 → 修正（端到端单次）
# =====================================================================
def run_falsified_qa(question: str, evidence_features: dict, projection: str = None):
    """返回审计字典。可被任何 Agent import 调用。"""
    llm = LLMAdapter()
    refuter = build_refuter()
    system = ("你是三元九维认知体系下的推理主体。请给出判断后，再输出一个 markdown 代码块："
              "```stance\\n{JSON}\\n```，JSON 含 pattern_id / primitives(基元活跃度) / "
              "confidence(0-1) / projection(domain) / assertion。")
    raw = llm.complete(system, question)
    st = parse_stance(raw)
    audit = {"mode": llm.mode, "raw": raw, "evidence": evidence_features}
    if st is None:
        audit["status"] = "unparsed"; audit["final"] = raw; return audit
    # ① 自我矛盾检测（内源反例，LLM 难自查）
    contra = contradictions(st)
    audit["contradictions"] = contra
    # ② 证伪器校验（外源证据）
    ev = Evidence(evidence_features, source="external", strength=0.9)
    s2, evt = refuter.check(st, ev)
    if evt is not None and evt.hit_type in ("full", "partial"):
        audit["refuted"] = True
        audit["hit_type"] = evt.hit_type
        audit["reason"] = evt.reason
        audit["confidence_before"] = round(st.confidence, 4)
        audit["confidence_after"] = round(s2.confidence, 4)
        # ③ 受引导跳跃：被推翻后生成修正格局（不缩回，朝对的方向长）
        g = guided_jump(s2, ev)
        audit["migrated_to"] = g.pattern_id
        audit["guided_fallback"] = g.pattern_id
        audit["final_assertion"] = _refined_assertion(st.assertion, evt.hit_type, contra)
        audit["status"] = "refuted_and_migrated"
        audit["neg_lib_size"] = len(refuter.neg_lib)
        # 跳跃验证并尝试固化
        verdict = verify_jump(st, g, refuter.pos_lib)
        audit["jump_verdict"] = verdict
    else:
        audit["refuted"] = False
        audit["status"] = "passed"
        audit["final_assertion"] = st.assertion
        audit["confidence_after"] = round(st.confidence, 4)
    return audit


def _refined_assertion(original: str, hit_type: str, contra: list) -> str:
    if contra:
        return f"[自我矛盾被检出] 原断言「{original}」内部自相矛盾，需先厘清主张与反驳。"
    if hit_type == "full":
        return f"[被推翻] 原断言「{original}」因命中反证被推翻，转向相反/修正结论。"
    return f"[降置信] 原断言「{original}」受部分反证冲击，置信度下调，转为待核验。"


# =====================================================================
# demo：3 个真实场景，展示"LLM 输出被证伪器纠正"
# =====================================================================
def demo():
    print("=" * 70)
    print("TNE-Falsifier × LLM 桥接 · 端到端 Demo（三元九维证伪器接入大模型）")
    print(f"LLM 接入模式：{LLMAdapter().mode}  "
          f"（{'真实 OpenAI 兼容 API' if LLMAdapter().mode=='real' else '确定性模拟器回退，给 LLM_API_KEY 即切真实'}）")
    print("=" * 70)

    cases = [
        ("【金融】该指数下周会涨吗？", {"放量下跌": True}, "market"),
        ("【事实】此事发生于2020年？", {"来源不可靠": True}, "claim"),
        ("【认知】此判断非黑即白？", {"出现第三态": True}, "cognition"),
        ("【金融】该指数下周会涨吗？", {}, "market"),   # 无反例 → 通过
    ]
    for i, (q, ev, proj) in enumerate(cases, 1):
        print(f"\n[{i}] 问题：{q}")
        a = run_falsified_qa(q, ev, proj)
        print(f"     LLM模式={a['mode']} | 自我矛盾={a['contradictions'] or '无'}")
        if a.get("refuted"):
            print(f"     证伪 → {a['hit_type']}：{a['reason']}")
            print(f"     置信度 {a['confidence_before']} → {a['confidence_after']} | "
                  f"迁移至 {a['migrated_to']} | 跳跃验证={a.get('jump_verdict')}")
        else:
            print(f"     校验 → 通过，保持断言（置信度 {a['confidence_after']}）")
        print(f"     最终结论：{a.get('final_assertion')}")

    print("\n" + "=" * 70)
    print("全过程确定性 · 可复算 · 可回放 · 可审计 · 可逆（undo）。")
    print("证伪器是锚点与保险丝；LLM 是认知主体。任何大模型/Agent 均可 import 本模块作为校验层。")
    print("=" * 70)


if __name__ == "__main__":
    demo()
