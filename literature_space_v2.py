#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""literature_space_v2.py · 认知空间 × 文学：三部对照

在 v1（单部《局外人》）基础上加两件事：
  1) 三部作品对照 —— 验「分辨力」：三部件在坐标上分不分得开
  2) 双准则一致性 —— 验「规则硬不硬」：同一部作品，两套标注准则各标一遍，算 kappa

【声明】
- 9 爻编码是文本解读，不是客观测量；换人换准则，编码会变。
- 脚本保证「给定编码，指标可复算」，不保证「编码是唯一正解」。
- 三部作品仍不成「规律」，只验「坐标有没有分辨力」。

运行：python3 literature_space_v2.py
"""
from __future__ import annotations
import hashlib
import json

TRIT = {"D": 0, "R": 1, "T": 2}
SYM = {"D": "●", "R": "■", "T": "▲"}

# =====================================================================
# 作品一：《局外人》21 场景（准则 A：上=命运大势 / 中=关系枢纽 / 下=身体感知）
# =====================================================================
JW = [
    ("S01", "接到电报·母死", "DRD", "DRT", "RDT"),
    ("S02", "请假·赴院", "DRD", "DRT", "RDT"),
    ("S03", "守灵夜", "DDD", "DRT", "RDR"),
    ("S04", "葬礼·烈日", "DRD", "DRD", "RDR"),
    ("S05", "回城·游泳遇玛丽", "TRD", "TRT", "TRT"),
    ("S06", "看电影·亲密", "TRT", "TRT", "TRT"),
    ("S07", "周日·阳台", "DRD", "DRD", "RDR"),
    ("S08", "雷蒙求助", "DRT", "TRT", "RDD"),
    ("S09", "海滩·初遇冲突", "DRT", "TRT", "RDR"),
    ("S10", "雷蒙被刺", "DRD", "DRD", "RDR"),
    ("S11", "再赴海滩", "DRD", "DRD", "RDR"),
    ("S12", "正午·对峙", "DDD", "DRD", "RDR"),
    ("S13", "开枪·四响", "TTT", "TRT", "TTT"),
    ("S14", "被捕·初审", "DDD", "DDD", "RDD"),
    ("S15", "监狱·律师", "DDD", "DDD", "RDD"),
    ("S16", "玛丽探监", "DRD", "DRD", "RDR"),
    ("S17", "法庭·质询", "DDD", "DDD", "RDD"),
    ("S18", "检察官论罪", "DDD", "DDD", "RDD"),
    ("S19", "判决死刑", "DDD", "DDD", "RDD"),
    ("S20", "拒绝神父", "DDD", "DDD", "RDD"),
    ("S21", "向世界敞开", "DTD", "DDT", "TRT"),
]

# =====================================================================
# 作品二：《百年孤独》21 场景（上=家族/马孔多兴衰 / 中=世系关系 / 下=时间与记忆）
# =====================================================================
BN = [
    ("B01", "马孔多建立", "TRD", "TTR", "TRT"),
    ("B02", "吉普赛人·磁铁炼金", "DRT", "TRT", "TRT"),
    ("B03", "失眠症·全村遗忘", "DDD", "DRD", "RDR"),
    ("B04", "与政府军冲突", "DRD", "DRT", "RDR"),
    ("B05", "上校发动32场起义", "TRT", "DRD", "RDD"),
    ("B06", "作坊·做小金鱼", "DDD", "DRD", "RDR"),
    ("B07", "阿玛兰妲·拒绝与烧伤", "DRD", "DRD", "RDR"),
    ("B08", "香蕉公司进驻·繁荣", "TRT", "TRT", "TRT"),
    ("B09", "罢工·三百人大屠杀", "DDD", "DDD", "RDD"),
    ("B10", "四年十一月两天雨", "DDD", "DDD", "RDR"),
    ("B11", "奥雷里亚诺第二·饕餮宴", "TRT", "TRT", "TRT"),
    ("B12", "美人儿蕾梅黛丝升天", "TDT", "DRT", "TRT"),
    ("B13", "铁路·电影·电话到来", "DRT", "DRD", "RDT"),
    ("B14", "家族衰败·房屋朽坏", "DDD", "DDD", "RDD"),
    ("B15", "香蕉公司撤离·凋敝", "DDD", "DDD", "RDD"),
    ("B16", "末代奥雷里亚诺破译羊皮卷", "DDT", "DDD", "RDT"),
    ("B17", "乌尔苏拉失明·死去", "DDD", "DDD", "RDD"),
    ("B18", "家族成员逐一死去", "DDD", "DDD", "RDD"),
    ("B19", "阿玛兰妲·乌尔苏拉归来", "DRT", "TRT", "RDT"),
    ("B20", "飓风来临", "DDT", "DDD", "RDR"),
    ("B21", "马孔多被抹去", "DDD", "DDD", "DDD"),
]

# =====================================================================
# 作品三：《战争与和平》21 场景（上=历史大势/战争 / 中=人物关系与选择 / 下=生命与死亡感知）
# =====================================================================
WP = [
    ("W01", "彼得堡沙龙", "DRD", "TRT", "RDT"),
    ("W02", "安德烈决意参军", "TRD", "TRT", "RDT"),
    ("W03", "奥斯特里茨·倒下看天", "TDT", "DRD", "RDT"),
    ("W04", "娜塔莎第一次舞会", "TRT", "TRT", "TRT"),
    ("W05", "安德烈与娜塔莎订婚", "TRT", "TRT", "TRT"),
    ("W06", "阿纳托利诱拐·婚约破裂", "DDD", "DDD", "RDR"),
    ("W07", "1812·拿破仑入侵", "DDD", "DRD", "RDD"),
    ("W08", "安德烈重返军队", "DRT", "DRT", "RDT"),
    ("W09", "波罗金诺会战", "TDT", "DRD", "RDT"),
    ("W10", "莫斯科大火", "DDD", "DDD", "RDD"),
    ("W11", "皮埃尔留城·被捕", "DDD", "DDD", "RDD"),
    ("W12", "受俘·卡拉塔耶夫", "DDD", "DRD", "RDT"),
    ("W13", "娜塔莎照顾伤兵·遇安德烈", "DDD", "TRT", "RDT"),
    ("W14", "安德烈之死", "DDD", "DDD", "DDT"),
    ("W15", "拿破仑大军溃退", "DRD", "DRD", "RDD"),
    ("W16", "皮埃尔获释", "TRD", "TRT", "RDT"),
    ("W17", "娜塔莎与皮埃尔重逢", "TRT", "TRT", "TRT"),
    ("W18", "别祖霍夫家复苏", "TRT", "TRT", "TRT"),
    ("W19", "尼古拉与玛丽亚", "DRT", "TRT", "RDT"),
    ("W20", "尾声·家庭生活", "TRT", "TRT", "TRT"),
    ("W21", "结尾·历史观", "DTT", "DDT", "TDT"),
]

# =====================================================================
# 准则 B（仅《局外人》）：上=外部压力 / 中=主角能动性 / 下=时间与记忆
# 用于双准则一致性检验
# =====================================================================
JW_B = [
    ("S01", "D", "D", "R"), ("S02", "D", "D", "R"), ("S03", "D", "D", "D"),
    ("S04", "R", "D", "R"), ("S05", "D", "T", "T"), ("S06", "D", "T", "T"),
    ("S07", "D", "D", "R"), ("S08", "R", "D", "D"), ("S09", "R", "D", "R"),
    ("S10", "R", "D", "D"), ("S11", "R", "D", "D"), ("S12", "R", "D", "D"),
    ("S13", "T", "T", "T"), ("S14", "T", "D", "D"), ("S15", "T", "D", "D"),
    ("S16", "T", "D", "D"), ("S17", "T", "D", "D"), ("S18", "T", "D", "D"),
    ("S19", "T", "D", "D"), ("S20", "T", "D", "D"), ("S21", "D", "T", "T"),
]


def state_code(u, m, l):
    n = 0
    for ch in u + m + l:
        n = n * 3 + TRIT[ch]
    return n + 1


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def dominant(s):
    c = {k: s.count(k) for k in "DRT"}
    top = max(c.values())
    cand = [k for k, v in c.items() if v == top]
    return cand[0] if len(cand) == 1 else s[1]


def analyze(scenes):
    rows = []
    for sid, name, u, m, l in scenes:
        full = u + m + l
        rows.append({"id": sid, "name": name, "u": u, "m": m, "l": l, "full": full,
                     "code": state_code(u, m, l),
                     "du": dominant(u), "dm": dominant(m), "dl": dominant(l)})
    dists = [hamming(rows[i]["full"], rows[i + 1]["full"]) for i in range(len(rows) - 1)]
    turn = sum(dists) / len(dists)
    best = best_start = cur = start = 1
    for i, d in enumerate(dists):
        if d <= 1:
            cur += 1
        else:
            if cur > best:
                best, best_start = cur, start
            cur, start = 1, i + 1
    if cur > best:
        best, best_start = cur, start
    t_counts = [r["full"].count("T") for r in rows]
    med = sorted(t_counts)[len(t_counts) // 2]
    bp = [rows[i]["id"] for i, t in enumerate(t_counts) if t - med >= 4]
    jump_i = max(range(len(dists)), key=lambda i: dists[i])
    fp = hashlib.sha256(json.dumps(
        {"s": [(r["id"], r["full"]) for r in rows]}, ensure_ascii=False, sort_keys=True
    ).encode()).hexdigest()[:16]
    return {"rows": rows, "dists": dists, "turn": turn, "reside": best,
            "reside_span": (rows[best_start]["id"], rows[best_start + best - 1]["id"]),
            "jump": dists[jump_i], "jump_at": (rows[jump_i]["id"], rows[jump_i + 1]["id"]),
            "bp": bp, "tcounts": t_counts, "fp": fp}


def ref_curve(n):
    """典型悲剧参照曲线：前 1/3 扬(TRT) → 中 1/3 判(DRD) → 后 1/3 封(DDD)。
    「偏离度」= 实际上卦与这条参照的平均汉明距离，用来量化「破格」。"""
    out = []
    for i in range(n):
        if i < n / 3:
            out.append("TRT")
        elif i < 2 * n / 3:
            out.append("DRD")
        else:
            out.append("DDD")
    return out


def deviation(res):
    ref = ref_curve(len(res["rows"]))
    return sum(hamming(r["u"], ref[i]) for i, r in enumerate(res["rows"])) / len(ref)


def kappa(a, b):
    """Cohen's kappa：比较两组层主导态判定。"""
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca = {k: a.count(k) / n for k in "DRT"}
    cb = {k: b.count(k) / n for k in "DRT"}
    pe = sum(ca.get(k, 0) * cb.get(k, 0) for k in "DRT")
    return (po, (po - pe) / (1 - pe) if pe < 1 else 1.0)


def show(name, res):
    print(f"\n【{name}】指纹 {res['fp']}")
    for key, label in (("du", "上"), ("dm", "中"), ("dl", "下")):
        print(f"    {label} " + "".join(SYM[r[key]] for r in res["rows"]))
    print(f"    转折密度 {res['turn']:.2f} · 最长驻留 {res['reside']}"
          f"（{res['reside_span'][0]}→{res['reside_span'][1]}）"
          f" · 最大突变 {res['jump']} 爻（{res['jump_at'][0]}→{res['jump_at'][1]}）")
    print(f"    破格点 {res['bp']} · T 曲线 {res['tcounts']}")


def main():
    print("=" * 82)
    print("认知空间 × 文学 · 三部对照：分辨力 + 双准则一致性")
    print("=" * 82)

    works = [("局外人·加缪", JW), ("百年孤独·马尔克斯", BN), ("战争与和平·托尔斯泰", WP)]
    results = {}
    for name, scenes in works:
        res = analyze(scenes)
        results[name.split("·")[0]] = res
        show(name, res)
        print(f"    参照曲线偏离度（破格度） {deviation(res):.2f} 爻/场景")

    # ---- 分辨力：两两比较 ----
    print("\n" + "-" * 82)
    print("分辨力：三部作品在坐标上分得开吗")
    keys = list(results)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = results[keys[i]], results[keys[j]]
            # 逐场景同位置距离（同数量场景，可直接对齐）
            seq_d = sum(hamming(ra["full"], rb["full"])
                        for ra, rb in zip(a["rows"], b["rows"])) / len(a["rows"])
            print(f"  {keys[i]:<6} ↔ {keys[j]:<6} 同位置平均差 {seq_d:.2f} 爻"
                  f" | 指纹是否相同: {'是' if a['fp'] == b['fp'] else '否'}")
    print("  → 若两两位移都显著（>2 爻），说明坐标对作品有分辨力。")

    # ---- 双准则一致性（局外人）----
    print("\n" + "-" * 82)
    print("双准则一致性（《局外人》）：准则A（命运/关系/身体） vs 准则B（外压/能动/时间）")
    ra = results["局外人"]
    a_dom = [x for r in ra["rows"] for x in (r["du"], r["dm"], r["dl"])]
    b_dom = [x for _, u, m, l in JW_B for x in (u, m, l)]
    po, k = kappa(a_dom, b_dom)
    print(f"  观测一致率 po = {po:.3f} · Cohen's kappa = {k:.3f}")
    if k < 0.4:
        print("  → kappa < 0.4：两套准则一致性差。这说明「编码规则还不够硬」，")
        print("    同一部作品换一个观察轴就标出不同结果——规则需要先硬化，否则坐标只是解读的外衣。")
    elif k < 0.7:
        print("  → 中等一致：规则有骨架，但自由度过大。")
    else:
        print("  → 高度一致：规则已足够硬。")

    # ---- 复算验证 ----
    fp2 = analyze(JW)["fp"]
    print(f"\n复算校验（局外人两遍）: {'✅ 一致' if fp2 == ra['fp'] else '❌ 不一致'}")


if __name__ == "__main__":
    main()
