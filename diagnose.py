#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diagnose.py · 结构诊断器

输入任一九位标注文件（1 部或多部），输出：
  1. 七维形状特征
  2. 在 20 部参照库中最近的 3 部（距离）
  3. 归属的团（k=7）与团内距离
  4. 最异常场景（最大断崖落点）
  5. 一句话诊断

用法：
  python3 diagnose.py works_annot4.json
  python3 diagnose.py 某作品.json --top 5
"""
import json
import math
import sys

from cluster import (DIMS, WEIGHT, FILES, load_all, features, dist, hcluster, cut,
                     hamming)


def fit(vecs):
    m = len(vecs[0])
    mu = [sum(v[j] for v in vecs) / len(vecs) for j in range(m)]
    sd = [math.sqrt(sum((v[j] - mu[j]) ** 2 for v in vecs) / len(vecs)) or 1.0 for j in range(m)]
    return mu, sd


def tf(v, mu, sd):
    return [(v[j] - mu[j]) / sd[j] * WEIGHT.get(DIMS[j], 1.0) for j in range(len(v))]


def build_ref(exclude=None):
    data = [x for x in load_all() if x[0] != exclude]
    names = [w for w, _ in data]
    feats = [features(s) for _, s in data]
    raw = [[f[d] for d in DIMS] for f in feats]
    mu, sd = fit(raw)
    vecs = [tf(v, mu, sd) for v in raw]
    groups = cut(names, hcluster(names, vecs), 7)
    cents, tags = [], []
    for g in groups:
        idx = [names.index(x) for x in g]
        cents.append([sum(vecs[i][j] for i in idx) / len(idx) for j in range(len(DIMS))])
        tags.append(tag({d: sum(feats[i][d] for i in idx) / len(idx) for d in DIMS}))
    return names, feats, vecs, groups, cents, tags, mu, sd


def tag(a):
    if a["tail_head"] <= -3.5:
        return "锥形坠落·顶端陡降"
    if a["jump_pos"] >= 0.75:
        return "末尾断崖·高位崩塌"
    if a["base"] < 2.2 and a["peak_n"] <= 2:
        return "静态循环·变化趋零"
    if a["slope"] >= 0.10:
        return "多峰上行·末段抬升"
    if a["peak_n"] <= 2 and a["base"] < 3.2:
        return "程序推进·低平下行"
    return "多峰衰减·前端断裂"


def diagnose(path, top=3):
    d = json.load(open(path, encoding="utf-8"))
    items = d["works"] if "works" in d else [d]

    for w in items:
        names, feats, vecs, groups, cents, tags, mu, sd = build_ref(exclude=w["work"])
        f = features(w["scenes"])
        v = tf([f[x] for x in DIMS], mu, sd)
        dlist = sorted(((dist(v, vecs[i]), names[i]) for i in range(len(names))), key=lambda t: t[0])
        ci = min(range(len(cents)), key=lambda i: dist(v, cents[i]))
        cdist = dist(v, cents[ci])

        rows = [s["u"] + s["m"] + s["l"] for s in w["scenes"]]
        ds = [hamming(rows[i], rows[i + 1]) for i in range(len(rows) - 1)]
        j = max(range(len(ds)), key=lambda i: ds[i])

        dev = sorted(range(len(DIMS)), key=lambda k: -abs(v[k] - cents[ci][k]) * sd[k])
        lead = DIMS[dev[0]]

        print("━" * 78)
        print(f"《{w['work']}》  场景 {f['n']}  |  归属团：{tags[ci]}（团内距离 {cdist:.2f}）")
        print("━" * 78)
        print(f"  turn {f['turn']:.2f}  slope {f['slope']:+.2f}  jump {f['jump_pos']:.2f}"
              f"  reside {f['reside_r']:.2f}  peak {f['peak_n']}  base {f['base']:.2f}"
              f"  tail-head {f['tail_head']:+.1f}")
        print(f"  最近邻：" + " / ".join(f"《{n}》 {dd:.2f}" for dd, n in dlist[:top]))
        print(f"  最异常场景：{w['scenes'][j]['name']} → {w['scenes'][j+1]['name']}"
              f"（爻距 {ds[j]}，全书 {len(ds)} 个相邻对中最大）")
        print(f"  该场景九爻：{w['scenes'][j]['u']} / {w['scenes'][j]['m']} / {w['scenes'][j]['l']}"
              f"  →  {w['scenes'][j+1]['u']} / {w['scenes'][j+1]['m']} / {w['scenes'][j+1]['l']}")
        print(f"  最偏离维度：{lead}")

        verdict = []
        if f["tail_head"] <= -3.0:
            verdict.append(f"首段均值远高于末段（差 {abs(f['tail_head']):.1f}），整条曲线锥形收束")
        elif f["jump_pos"] >= 0.75:
            verdict.append("断裂压在末段：前面一直在撑，最后一次性塌")
        elif f["jump_pos"] >= 0.50:
            verdict.append(f"断裂落在中后段（{f['jump_pos']:.0%} 处），幅度不大")
        elif f["jump_pos"] <= 0.30 and f["slope"] >= 0.10:
            verdict.append("开场即有一次大跳，此后长期在高位多峰起伏")
        elif f["jump_pos"] <= 0.30:
            verdict.append("断裂压在开头：一开始就破，后面是余波")
        if f["slope"] <= -0.25:
            verdict.append(f"斜率 {f['slope']:+.2f}，整体下行")
        elif f["slope"] >= 0.10:
            verdict.append(f"斜率 {f['slope']:+.2f}，整体上行")
        if f["base"] < 2.0:
            verdict.append(f"基座 {f['base']:.2f} 极低，常压低释放")
        if f["peak_n"] >= 4:
            verdict.append(f"峰数 {f['peak_n']}，高点密集")
        print("  诊断：" + ("；".join(verdict) if verdict else "整体平缓，没有明显转折") + "。")
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    top = 3
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])
    for p in [a for a in sys.argv[1:] if not a.startswith("--") and a != str(top)]:
        diagnose(p, top)


if __name__ == "__main__":
    main()
