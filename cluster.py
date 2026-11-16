#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cluster.py v2 · 20 部作品在形状空间里的自然聚类

相对 v1 的三处改动：
1. 数据源扩到 5 个标注文件（20 部）
2. base（基座均值）降权到 0.5，修 v1 中"单维主导"问题
3. 新增抖动重采样稳定性检验：给特征加噪 100 次，看每部作品落回原团的频率

用法：
  python3 cluster.py           # 20 部全量
  python3 cluster.py --k 5     # 试 5 团
"""
import json
import math
import random
import sys

DIMS = ["turn", "slope", "jump_pos", "reside_r", "peak_n", "base", "tail_head"]
WEIGHT = {"base": 0.5}          # 降权：基座均值只给半权
if "--noweight" in __import__("sys").argv:
    WEIGHT = {}
PEAK_MIN = 3
FILES = ("jwr_annot.json", "works_annot.json", "works_annot2.json",
         "works_annot3.json", "works_annot4.json")


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
    for p in FILES:
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


def zscore(vecs, dims=None):
    dims = dims or DIMS
    m = len(vecs[0])
    cols = [[v[j] for v in vecs] for j in range(m)]
    out = []
    for j in range(m):
        mu = sum(cols[j]) / len(cols[j])
        sd = math.sqrt(sum((x - mu) ** 2 for x in cols[j]) / len(cols[j])) or 1.0
        w = WEIGHT.get(dims[j], 1.0)
        out.append([(x - mu) / sd * w for x in cols[j]])
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


def jitter_stability(names, vecs, k=4, trials=100, noise=0.08, seed=42):
    """给标准化特征加高斯噪声重采样，统计每部作品落回原团的频率"""
    base_groups = cut(names, hcluster(names, vecs), k)
    assign = {n: i for i, g in enumerate(base_groups) for n in g}
    rng = random.Random(seed)
    hit = {n: 0 for n in names}
    for _ in range(trials):
        jv = [[x + rng.gauss(0, noise) for x in v] for v in vecs]
        jgroups = cut(names, hcluster(names, jv), k)
        for g in jgroups:
            maj = max(range(len(base_groups)), key=lambda bi: sum(1 for n in g if assign[n] == bi))
            for n in g:
                if assign[n] == maj:
                    hit[n] += 1
    return base_groups, {n: hit[n] / trials for n in names}


def main():
    k = 4
    if "--k" in sys.argv:
        k = int(sys.argv[sys.argv.index("--k") + 1])

    data = load_all()
    names = [w for w, _ in data]
    feats = [features(s) for _, s in data]
    print("=" * 104)
    print(f"作品形状空间聚类 · {len(names)} 部 · 7 维（base 权重 0.5）· 平均链接层次聚类")
    print("=" * 104)
    print(f"\n{'作品':<12}{'n':>3}  turn  slope  jump_pos reside_r peak  base  tail-head")
    for n, f in zip(names, feats):
        print(f"{n:<12}{f['n']:>3}  {f['turn']:.2f}  {f['slope']:+.2f}   {f['jump_pos']:.2f}"
              f"    {f['reside_r']:.2f}   {f['peak_n']}   {f['base']:.2f}   {f['tail_head']:+.1f}")

    vecs = zscore([[f[d] for d in DIMS] for f in feats])
    merges = hcluster(names, vecs)

    for kk in (4, 5, 6, 7):
        print(f"\n── 切成 {kk} 组 ──")
        groups = cut(names, merges, kk)
        for g in groups:
            fs = [feats[names.index(x)] for x in g]
            avg = {d: sum(f[d] for f in fs) / len(fs) for d in DIMS}
            print(f"  ┣ {len(g):>2} 部：{', '.join(g)}")
            if len(g) > 1:
                print(f"      turn {avg['turn']:.2f} | slope {avg['slope']:+.2f}"
                      f" | jump {avg['jump_pos']:.2f} | reside {avg['reside_r']:.2f}"
                      f" | peak {avg['peak_n']:.1f} | base {avg['base']:.2f} | tail-head {avg['tail_head']:+.1f}")

    print(f"\n── 抖动重采样稳定性（k=7，100 次，噪声 σ=0.08）──")
    bgroups, stab = jitter_stability(names, vecs, k=7, trials=100)
    for n in names:
        bar = "█" * int(stab[n] * 20)
        print(f"  {n:<12}{stab[n]:.0%}  {bar}")

    print("\n── 合并距离：最近 4 / 最远 4 ──")
    for a, b, dd in merges[:4]:
        print(f"  近 {dd:.3f}  {a} + {b}")
    for a, b, dd in merges[-4:]:
        print(f"  远 {dd:.3f}  {a} + {b}")


if __name__ == "__main__":
    main()
