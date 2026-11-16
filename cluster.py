#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cluster.py · 十部作品在形状空间里的自然聚类

做法：7 维形状特征 → z-score 标准化 → 平均链接层次聚类（不预设类别）
输出：合并日志、k=2/3/4 的分组、各组特征均值

用法：python3 cluster.py
"""
import json
import math

DIMS = ["turn", "slope", "jump_pos", "reside_r", "peak_n", "base", "tail_head"]
PEAK_MIN = 3


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def slope(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(range(n)) / n
    my = sum(xs) / n
    num = sum((i - mx) * (xs[i] - my) for i in range(n))
    den = sum((i - mx) ** 2 for i in range(n))
    return num / den if den else 0.0


def load_all():
    out = []
    for p in ("jwr_annot.json", "works_annot.json", "works_annot2.json"):
        d = json.load(open(p, encoding="utf-8"))
        items = d["works"] if "works" in d else [d]
        for w in items:
            out.append((w["work"], w["scenes"]))
    return out


def features(scenes):
    rows = [s["u"] + s["m"] + s["l"] for s in scenes]
    n = len(rows)
    tc = [r.count("T") for r in rows]
    dists = [hamming(rows[i], rows[i + 1]) for i in range(n - 1)]
    turn = sum(dists) / len(dists)
    jump_i = max(range(len(dists)), key=lambda i: dists[i])
    jump_pos = (jump_i + 1) / n
    best = cur = st = bs = 1
    for i, dd in enumerate(dists):
        if dd <= 1:
            cur += 1
        else:
            if cur > best:
                best, bs = cur, st
            cur, st = 1, i + 1
    if cur > best:
        best, bs = cur, st
    reside_r = best / n
    peak_n = len([i for i in range(n) if tc[i] >= PEAK_MIN
                  and (i == 0 or tc[i] > tc[i - 1]) and (i == n - 1 or tc[i] >= tc[i + 1])])
    base = sum(tc) / n
    third = max(1, n // 3)
    tail_head = sum(tc[-third:]) / third - sum(tc[:third]) / third
    return {"turn": turn, "slope": slope(tc), "jump_pos": jump_pos, "reside_r": reside_r,
            "peak_n": peak_n, "base": base, "tail_head": tail_head, "tc": tc, "n": n}


def zscore(vecs):
    m = len(vecs[0])
    cols = [[v[j] for v in vecs] for j in range(m)]
    out = []
    for j in range(m):
        mu = sum(cols[j]) / len(cols[j])
        sd = math.sqrt(sum((x - mu) ** 2 for x in cols[j]) / len(cols[j])) or 1.0
        out.append([(x - mu) / sd for x in cols[j]])
    return [[out[j][i] for j in range(m)] for i in range(len(vecs))]


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def hcluster(names, vecs):
    clusters = [[i] for i in range(len(names))]
    merges = []
    while len(clusters) > 1:
        best = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                a, b = clusters[i], clusters[j]
                d = sum(dist(vecs[x], vecs[y]) for x in a for y in b) / (len(a) * len(b))
                if best is None or d < best[0]:
                    best = (d, i, j)
        d, i, j = best
        merges.append(([names[k] for k in clusters[i]], [names[k] for k in clusters[j]], d))
        clusters[i] = clusters[i] + clusters[j]
        del clusters[j]
    return merges


def cut(names, merges, k):
    groups = [[n] for n in names]
    for a, b, d in merges[:len(names) - k]:
        groups = [g for g in groups if g != a and g != b] + [a + b]
    return groups


def main():
    data = load_all()
    names = [w for w, _ in data]
    feats = [features(s) for _, s in data]
    print("=" * 100)
    print(f"十部作品 · 形状空间聚类（{len(names)} 部，7 维特征，z-score 标准化，平均链接）")
    print("=" * 100)
    print(f"\n{'作品':<10}{'n':>3}  turn  slope  jump_pos reside_r peak  base  tail-head")
    for n, f in zip(names, feats):
        print(f"{n:<10}{f['n']:>3}  {f['turn']:.2f}  {f['slope']:+.2f}   {f['jump_pos']:.2f}"
              f"    {f['reside_r']:.2f}   {f['peak_n']}   {f['base']:.2f}   {f['tail_head']:+.1f}")

    vecs = zscore([[f[d] for d in DIMS] for f in feats])
    merges = hcluster(names, vecs)

    print("\n合并顺序（距离由近到远）：")
    for i, (a, b, d) in enumerate(merges, 1):
        print(f"  {i:>2}. {a} + {b}  距离 {d:.3f}")

    for k in (2, 3, 4):
        print(f"\n切成 {k} 组：")
        for g in cut(names, merges, k):
            print(f"  ┣ {', '.join(g)}")

    print("\n各组形状特征均值（k=4）：")
    for g in cut(names, merges, 4):
        fs = [feats[names.index(x)] for x in g]
        avg = {d: sum(f[d] for f in fs) / len(fs) for d in DIMS}
        print(f"  {', '.join(g)}\n     turn {avg['turn']:.2f} | slope {avg['slope']:+.2f}"
              f" | jump_pos {avg['jump_pos']:.2f} | reside_r {avg['reside_r']:.2f}"
              f" | peak {avg['peak_n']:.1f} | base {avg['base']:.2f} | tail-head {avg['tail_head']:+.1f}")


if __name__ == "__main__":
    main()
