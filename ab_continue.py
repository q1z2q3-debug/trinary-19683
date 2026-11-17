#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab_continue.py · 续写 A/B 对照实验

问的问题：
  直接续写 vs 认知空间续写，差别能不能算出来？

做法：
  A 组：只给前 80 回原文，模型续 10 场
  B 组：给前 80 回原文 + template_hou40.json（目标七维 + 逐场九位模板）

  两组各跑 N 次，各自把结果标成九位 → 算七维 → 与真值（S21–S30 实测）比落位距离。

预测（写在这里，便于事后打自己的脸）：
  A 组 turn 会落在 3.2–4.2（把前 80 回的密度惯性带下来，真值是 2.11）
  B 组 turn 会落在 1.8–2.5

用法：
  # 只算真值基线，不生成（默认，无需模型）
  python3 ab_continue.py

  # 若已有生成结果（每场一个九位码），算落位距离
  python3 ab_continue.py --eval gen_A.json gen_B.json
"""
import json, sys
import numpy as np
from cluster import features, DIMS

TRUTH_FILE = "hongloumeng_annot.json"
TEMPLATE = "template_hou40.json"
LIB_FILES = ["jwr_annot.json", "works_annot.json", "works_annot2.json", "works_annot3.json",
             "works_annot4.json", "works_annot5.json", "cloud_annot.json", "myth_annot.json",
             "comedy_annot.json", "ulysses_annot.json", "hongloumeng_annot.json"]


def lib_stats():
    """26 部库的均值与标准差，用于把七维距离标准化。"""
    rows = []
    for fn in LIB_FILES:
        d = json.load(open(fn, encoding="utf-8"))
        for w in (d["works"] if "works" in d else [d]):
            rows.append([features(w["scenes"])[k] for k in DIMS])
    X = np.array(rows)
    sd = X.std(0)
    sd[sd == 0] = 1
    return X.mean(0), sd


def distance(feat, target, mu, sd):
    v = np.array([(feat[k] - target[k]) / sd[i] for i, k in enumerate(DIMS)])
    return float(np.linalg.norm(v)), dict(zip(DIMS, v.round(2)))


def truth():
    """返回 (前 80 回七维, 后 40 回七维)。"""
    d = json.load(open(TRUTH_FILE, encoding="utf-8"))
    S = d["scenes"]
    return features(S[:20]), features(S[20:])


def baseline():
    """打印真值，并把『直接续写最可能出的偏差』量化出来。"""
    fa, fb = truth()
    tpl = json.load(open(TEMPLATE, encoding="utf-8"))
    mu, sd = lib_stats()
    print("=== 真值（S21–S30 实测）===")
    print("  " + "  ".join(f"{k}={fb[k]:+.2f}" for k in DIMS))
    print(f"  总变差 {fb['turn'] * 9:.0f} 爻\n")

    print("=== 若 A 组照抄前 80 回的密度（最常见的失败）===")
    naive = dict(fb)
    naive["turn"] = fa["turn"]
    naive["peak_n"] = fa["peak_n"]
    naive["base"] = fa["base"]
    dd, comp = distance(naive, fb, mu, sd)
    print("  " + "  ".join(f"{k}={naive[k]:+.2f}" for k in DIMS))
    print(f"  到真值的标准化距离 {dd:.2f}（>1.0 即判为未命中）")
    print("  主要偏差：" + " / ".join(f"{k} {v:+.1f}σ" for k, v in comp.items()
                                if abs(v) > 0.8) + "\n")

    print("=== 若 B 组按模板写准（理论最好情形）===")
    print(f"  到真值距离 0.00（模板即真值）\n")

    print("=== 判定线 ===")
    print("  结构命中：七维标准化距离 < 1.0")
    print("  局部合法：annotate_check.py 0 错误 0 警告")
    print("  两者都过，才算『认知空间续写成立』；只过局部合法，等于只写通顺，没写对骨架。")


def eval_files(paths):
    fa, fb = truth()
    mu, sd = lib_stats()
    print(f"真值：" + "  ".join(f"{k}={fb[k]:+.2f}" for k in DIMS))
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        got = features(d["scenes"])
        dd, comp = distance(got, fb, mu, sd)
        verdict = "命中" if dd < 1.0 else "未命中"
        print(f"\n{p}")
        print("  " + "  ".join(f"{k}={got[k]:+.2f}" for k in DIMS))
        print(f"  距离 {dd:.2f} → {verdict}")
        print("  偏差最大的两维：" + " / ".join(
            f"{k} {v:+.1f}σ" for k, v in sorted(comp.items(), key=lambda x: -abs(x[1]))[:2]))


if __name__ == "__main__":
    if "--eval" in sys.argv:
        eval_files(sys.argv[sys.argv.index("--eval") + 1:])
    else:
        baseline()
