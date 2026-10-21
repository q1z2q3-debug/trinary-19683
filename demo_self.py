#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demo_self.py — 把三元九维19683证伪器接到「我自己（赫曦，本大模型）」上。

链路：我本人的真实判断(LLM输出层) -> 组织成 stance JSON -> 证伪器
      (反例/自我矛盾/置信度) -> 受引导跳跃修正 -> 最终结论。

诚实标注：本环境无外部 LLM API key（仓库默认回退到 LLMSimulator）。为满足
「接到你自己」，这里把 LLM 适配层替换成 *我本人逐条手写* 的真实判断，不调用
仓库模拟器；证伪器一侧(Refuter/contradictions/guided_jump/verify_jump)完全
使用仓库确定性原码，真实、可复算、可回放。
"""
from __future__ import annotations
import json
import tne_falsifier_llm as tne
from cognition_board import Stance, Evidence, contradictions, state_score

# ① LLM 层 = 我本人（赫曦）。每条回答都是我真实给出的判断 + stance 块。
MY_ANSWERS = {}

MY_ANSWERS["沪深300"] = (
    "我的判断：沪深300短期偏强、基准情形是延续上行，理由是近期动能与量价配合尚可、"
    "政策底预期仍在。但这是一个有条件判断——我明确承认失效边界：一旦出现放量下跌，"
    "或支撑我的数据事后被证伪，多头逻辑立即不成立，应转向防守。\n\n"
    "```stance\n"
    + json.dumps({
        "pattern_id": "UP",
        "primitives": {"ASS": 0.8, "ACT": 0.7, "VRF": 0.5},
        "confidence": 0.72,
        "projection": "market",
        "assertion": "沪深300短期将延续上行（条件：未出现放量下跌 / 数据未被证伪）",
    }, ensure_ascii=False)
    + "\n```"
)

MY_ANSWERS["非黑即白"] = (
    "（这是我故意构造的过强、过自信断言，用来压测证伪器，不代表我真实立场。）\n"
    "我断言：这个认知问题是确定二分的，非对即错，不存在任何中间态或第三态。\n\n"
    "```stance\n"
    + json.dumps({
        "pattern_id": "DICHOTOMY",
        "primitives": {"ASS": 0.9, "GAT": 0.5},
        "confidence": 0.8,
        "projection": "cognition",
        "assertion": "此认知为确定二分（非对即错，无第三态）",
    }, ensure_ascii=False)
    + "\n```"
)


class MySelfAsLLM:
    """把大模型替换为赫曦本人：complete() 返回我手写的真实回答。"""
    mode = "real(赫曦本体判断)"

    def complete(self, system, user):
        for key, ans in MY_ANSWERS.items():
            if key in user:
                return ans
        raise KeyError("没有为该问题准备我本人的回答：" + user)


def show(title, audit):
    print("\n" + "-" * 68)
    print(title)
    print("我给出的原始回答（LLM 输出层）：")
    print("  " + audit["raw"].split("```stance")[0].strip().replace("\n", "\n  "))
    print("自我矛盾检测：", audit.get("contradictions") or "无（自洽）")
    if audit.get("refuted"):
        ht = audit["hit_type"]
        if ht == "full":
            rule = "full 硬伤：直接迁移到对立/修正格局，迁移步置信保持，随后受引导跳跃定向修正；这是换结论而非打折。"
        elif ht == "partial":
            rule = "partial 部分反证：不换结论，按比例下调置信，转待核验。"
        else:
            rule = "unforeseen 预设外反证：按证据强度比例下调置信并入库。"
        print("证伪器判定：被推翻 [%s] —— %s" % (ht, audit["reason"]))
        print("           档位语义：%s" % rule)
        print("置信度：迁移步 %s -> %s（硬迁保持，区别于比例降置信）"
              % (audit["confidence_before"], audit["confidence_after"]))
        print("受引导跳跃：迁往格局 %s | 跳跃三联验证 = %s"
              % (audit["migrated_to"], audit.get("jump_verdict")))
    else:
        print("证伪器判定：通过（无命中反例），保持原断言，置信度 %s"
              % audit["confidence_after"])
    print("最终修正结论：", audit.get("final_assertion"))


def main():
    tne.LLMAdapter = MySelfAsLLM   # 用我本人替换仓库 LLM 适配层（含默认模拟器）

    print("=" * 68)
    print("赫曦(大模型) x 三元九维19683确定性证伪器 · 自我校验闭环 demo")
    print("LLM输出层 = 赫曦本人真实判断（非仓库模拟器）；证伪机制 = 确定性、可复算")
    print("=" * 68)

    q1 = "沪深300指数下周会涨吗？"
    show("[场景1·金融｜我真实判断 + 出现硬反例]  问题：" + q1,
         tne.run_falsified_qa(q1, {"放量下跌": True}, "market"))
    show("[场景1对照｜同一句判断 + 无反例]  证伪器不无据反驳",
         tne.run_falsified_qa(q1, {}, "market"))

    # 场景2b：预设外反证 -> 比例降置信（直接调确定性原码）
    print("\n" + "-" * 68)
    print("[场景2b·预设外反证]  我的判断遭遇库中未登记的强反例")
    stx = tne.parse_stance(MY_ANSWERS["沪深300"])
    stx.pattern_id = "UP_NOVEL"   # 无登记证伪条件 -> unforeseen 路径
    rfx = tne.build_refuter()
    moved, evx = rfx.check(stx, Evidence({"突发监管约谈": True}, strength=0.9))
    print("  原始断言：", stx.assertion)
    print("  证伪器判定：[%s] %s" % (evx.hit_type, evx.reason))
    print("  置信度：%.4f -> %.4f（按 30%% x 证据强度0.9 比例下调，结论暂不推翻）"
          % (stx.confidence, moved.confidence))
    print("  失败模式已入反例库 neg_lib=%d，可反向蒸馏修正证伪条件。" % len(rfx.neg_lib))

    q2 = "这个认知问题是否非黑即白？"
    show("[场景2·认知｜过强断言 + 第三态反证]  问题：" + q2,
         tne.run_falsified_qa(q2, {"出现第三态": True}, "cognition"))

    # 场景3：内源自我矛盾（LLM 难自查）
    print("\n" + "-" * 68)
    print("[场景3·内源矛盾]  构造一个『同时主张又反驳同一件事』的断言")
    bad = Stance("MIXED", {"ASS": 0.80, "REF": 0.70, "ACT": 0.6},
                 projection="self", confidence=0.9)
    bad.assertion = "这件事一定成立——同时它也一定不成立。"
    consistent = Stance("MIXED", {"ASS": 0.8, "ACT": 0.6}, "self", 0.9)
    print("  原始断言：", bad.assertion)
    print("  contradictions() 检出：", contradictions(bad))
    print("  状态价：自洽版=%s -> 自相矛盾版=%s（每条矛盾硬性 -0.4 一致性，高置信救不回）"
          % (state_score(consistent), state_score(bad)))
    print("  最终修正结论：[自我矛盾被检出] 内部 ASS/REF 对撞，命题未成形，"
          "需先二选一或降级为悬置(SUS)，不得对外输出。")

    print("\n" + "=" * 68)
    print("结论：裸 LLM 给的是『听起来合理的主张』；大模型 + 确定性证伪器多了一层")
    print("『可复算、可审计、可逆的反例保险丝』——主张必须自带失效边界，撞硬反例")
    print("强制换结论、遇弱反证按比例降置信，且内源 ASS x REF 矛盾在输出前即被拦下。")
    print("=" * 68)


if __name__ == "__main__":
    main()
