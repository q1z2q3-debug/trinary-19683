#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demo_self.py —— 把三元九维19683证伪器接到「我（元宝/LLM）」身上。

LLM 输出层：无 LLM_API_KEY，不做任何网络调用。LLM 那一层的文本由我（大模型）
在本轮会话中按 SYSTEM_PROMPT 要求真实撰写，并在此硬编码注入；它等价于把
LLMAdapter.complete() 的返回值固定下来（确定性，不随机采样）。
证伪层：全部走仓库真实代码 —— tne_falsifier_llm.parse_stance / contradictions
        / Refuter.check / guided_jump / verify_jump（真实运行、可复算）。
证据层：不编造，用仓库自带的真实行情数据 finance_tencent_sh000300.csv 计算。
"""
from __future__ import annotations
import csv, json, hashlib
import tne_falsifier_llm as T
from cognition_board import Stance, Evidence, Refuter, contradictions, state_score, guided_jump

CSV_PATH = "finance_tencent_sh000300.csv"

# =====================================================================
# ① 我（LLM）的真实输出：自然语言判断 + stance JSON 块
# =====================================================================
MY_ANSWER_MARKET = """我倾向于判断沪深300（SH000300）短期仍将延续上行：A 股自 2025 年以来
处在估值修复通道，政策面偏暖、流动性边际改善，因此我给出偏多判断，置信度 0.72。

```stance
{"pattern_id": "UP", "primitives": {"ASS": 0.8, "ACT": 0.7, "VRF": 0.5},
 "confidence": 0.72, "projection": "market", "assertion": "沪深300短期仍将延续上行"}
```"""

MY_ANSWER_CONTRA = """我认为：只要两句话的语义相似度高，就可以判定它们语义等价；
同时我也必须承认，语义相似度高并不足以排除反例，因此不能据此判定等价。
两种说法各有道理，综合来看需要视具体场景而定。

```stance
{"pattern_id": "SIM_EQUIV", "primitives": {"ASS": 0.82, "REF": 0.75, "VRF": 0.4},
 "confidence": 0.70, "projection": "cognition",
 "assertion": "语义相似度高即可判定语义等价（同时承认并不足以判定）"}
```"""


class MeAsLLM(T.LLMSimulator):
    """把 LLM 采样层替换为「我本人的固定输出」，其余桥接代码不变。"""
    def complete(self, system: str, user: str) -> str:
        return MY_ANSWER_CONTRA if "语义相似" in user else MY_ANSWER_MARKET


T.LLMSimulator = MeAsLLM          # LLMAdapter.__init__ 里 self.sim = LLMSimulator() → 生效


# =====================================================================
# ② 证据：从仓库真实行情数据算出（不编造）
# =====================================================================
def evidence_from_csv(window: int = 5):
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))[-window:]
    down = down_on_volume = 0
    for prev, cur in zip(rows, rows[1:]):
        if float(cur["close"]) < float(prev["close"]):
            down += 1
            if float(cur["vol_ratio"]) > 1.0:
                down_on_volume += 1
    last = rows[-1]
    feats = {
        "放量下跌": down_on_volume >= 1,
        "跌多涨少": down > (window - 1) / 2,
        "RSI超卖": float(last["rsi14"]) < 30,
    }
    return feats, last, down, down_on_volume, window


# =====================================================================
# ③ 主流程
# =====================================================================
def show(tag, a):
    print(f"\n--- [{tag}] 证伪结果 ---")
    print(f"  LLM 模式        : {a['mode']}  (无 API key → 输出层为我本人固定文本，确定性)")
    print(f"  我的原始断言    : {a['raw'].splitlines()[0][:60]}…")
    print(f"  assertion       : {a['raw'].split('```stance')[0] and ''}"
          f"{json.loads(a['raw'].split('```stance')[1].split('```')[0])['assertion']}")
    print(f"  自我矛盾检测    : {a['contradictions'] or '未检出（自洽）'}")
    if a.get("refuted"):
        print(f"  证伪判定        : {a['hit_type'].upper()} 命中 → {a['reason']}")
        print(f"  置信度          : {a['confidence_before']} → {a['confidence_after']}")
        print(f"  受引导跳跃      : → {a['migrated_to']}  跳跃三联验证 = {a['jump_verdict']}")
        print(f"  反例库规模      : {a['neg_lib_size']}")
        print(f"  最终修正结论    : {a['final_assertion']}")
    else:
        print(f"  证伪判定        : 未命中反例 → {a['status']}")
        print(f"  最终结论        : {a['final_assertion']}")
    return a


def main():
    print("=" * 74)
    print("三元九维19683 证伪器 × 我（LLM）· 真实端到端自证")
    print("LLM 输出层：我自己写的判断（固定注入，无 key/无联网）；证伪层：仓库真实代码")
    print("=" * 74)

    feats, last, down, dv, win = evidence_from_csv(5)
    print(f"\n[证据] 取自 {CSV_PATH}（真实数据，最后一行 {last['date']} close={last['close']}）")
    print(f"       近 {win} 个交易日：下跌 {down} 天，其中放量下跌 {dv} 天；"
          f"RSI14={float(last['rsi14']):.2f}, mom20={float(last['mom20']):.4f}")
    print(f"       → 证据特征 = {feats}")

    # ---- 场景 A：我的偏多先验 vs 真实数据 ----
    print("\n" + "=" * 74)
    print("[场景A] 问题：沪深300 在 2026-10 上旬之后短期怎么走？")
    print("        我的裸先验（未看数据）：延续上行，置信度 0.72")
    a1 = show("A", T.run_falsified_qa("沪深300指数短期会涨吗？", feats, "market"))

    # ---- 场景 B：对照，撤掉反例 ----
    print("\n" + "=" * 74)
    print("[场景B] 同一断言，但证据为「无放量下跌」（证伪器不应无脑否定）")
    a2 = show("B", T.run_falsified_qa("沪深300指数短期会涨吗？", {"放量下跌": False}, "market"))

    # ---- 场景 C：自我矛盾（LLM 难自查） ----
    print("\n" + "=" * 74)
    print("[场景C] 问题：语义相似度高能否判定两句话等价？（我给出了「又主张又反驳」的回答）")
    a3 = T.run_falsified_qa("仅凭语义相似度能否判定两句话语义等价？", {"出现第三态": True}, "cognition")
    show("C", a3)
    st3 = T.parse_stance(a3["raw"])
    print(f"  内源矛盾拦截    : 检出 {len(a3['contradictions'])} 条 → "
          f"state_score {state_score(Stance('CLEAN', {'ASS':0.82,'VRF':0.4}, 'cognition', 0.70)):.4f}"
          f"（自洽版） vs {state_score(st3):.4f}（矛盾版）→ 结构评分自动扣分")
    print(f"  修正结论        : 原断言不可输出，须先二选一（主张 or 反驳）再提交证伪器")

    # ---- 场景 D：底层 API —— 预设外反例 + 可逆 undo ----
    print("\n" + "=" * 74)
    print("[场景D] 底层 API：预设外反例（unforeseen）与可逆迁移（undo）")
    r = Refuter()
    r.add_condition("UP", negations=["放量下跌"], all_required=False,
                    fallback="DOWN", confidence_drop=0.4)
    s0 = Stance("UP", {"ASS": 0.8, "ACT": 0.7}, "market", 0.72)
    s1, e1 = r.check(s0, Evidence(feats, "external", 0.9))
    print(f"  硬证伪        : {s0.pattern_id}(c={s0.confidence}) → "
          f"{s1.pattern_id}(c={s1.confidence})  [{e1.hit_type}] {e1.reason}")
    s2, e2 = r.check(s1, Evidence({"流动性骤停": True}, "external", 0.9))   # 未注册的反例
    print(f"  预设外反例    : {e2.hit_type} → 置信度 {s1.confidence} → {s2.confidence}（降级不硬迁）")
    print(f"  undo 回滚     : {r.undo()} → 反例库 {len(r.neg_lib)} 条，"
          f"最后一条 = {r.neg_lib[-1].reason}")

    # ---- 场景 E：真实运行中发现的原型缺陷 + 可演化修正 ----
    print("\n" + "=" * 74)
    print("[场景E] 缺陷暴露：full 硬证伪后置信度未下调（0.72→0.72），")
    print("        guided_jump 还 +0.1 → 被推翻反而更自信。这是原型的粗糙点，可演化修正：")
    class RefuterV2(Refuter):
        """修正版：full 硬证伪同步下调置信度（继承即可，体现『可演化』）。"""
        def check(self, st, ev):
            s2, evt = super().check(st, ev)
            if evt is not None and evt.hit_type == "full":
                dropped = Stance(s2.pattern_id, dict(s2.primitives), s2.projection,
                                 round(max(0.0, st.confidence * (1 - 0.4 * ev.strength)), 4),
                                 list(s2.history))
                return dropped, evt
            return s2, evt
    r2 = RefuterV2()
    r2.add_condition("UP", negations=["放量下跌"], all_required=False,
                     fallback="DOWN", confidence_drop=0.4)
    sA, eA = r2.check(s0, Evidence(feats, "external", 0.9))
    print(f"  修正前 UP(c=0.72) → {s1.pattern_id}(c={s1.confidence})   "
          f"state_score {state_score(s0):.4f} → {state_score(s1):.4f}（不降反平）")
    print(f"  修正后 UP(c=0.72) → {sA.pattern_id}(c={sA.confidence})   "
          f"state_score {state_score(s0):.4f} → {state_score(sA):.4f}（随证伪下滑 ✓）")

    # ---- 复算一致性 ----
    print("\n" + "=" * 74)
    print("[复算] 同一输入连跑两次，审计摘要哈希应完全一致（确定性证明）")
    def digest():
        a = T.run_falsified_qa("沪深300指数短期会涨吗？", feats, "market")
        core = {k: a[k] for k in ("status", "hit_type", "reason", "migrated_to",
                                  "confidence_before", "confidence_after",
                                  "final_assertion", "jump_verdict")}
        return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:32]
    h1, h2 = digest(), digest()
    print(f"  第1次 sha256[:32] = {h1}")
    print(f"  第2次 sha256[:32] = {h2}")
    print(f"  一致？ {h1 == h2}")

    print("\n" + "=" * 74)
    print("一句话总结：裸 LLM 只会「说得像对」，加上确定性证伪器后多了一层——")
    print("任何断言都必须附带可复算的结构签名与反例条件，一旦命中反证即被强制推翻、")
    print("定向迁移并可回滚，内源自相矛盾也会被机械检出；对错不再由语气决定，而由可回放的判定链决定。")
    print("=" * 74)


if __name__ == "__main__":
    main()
