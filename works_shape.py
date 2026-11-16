#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""works_shape.py · 形状特征 + 类型判定 v2

v1（works_check.py）用 4 个平均值判类，结果大面积误判：局外人被判「长坡下行」，
活着被判「循环振荡」。原因是平均值抹掉了曲线形状——而结构恰恰全在形状里。

v2 改用 7 个形状特征：
  turn       转折密度
  slope      T 曲线的最小二乘斜率（<0 衰减，>0 上升）
  jump_pos   最大突变位置（归一化 0–1）
  reside_r   最长驻留占全篇比例
  peak_n     峰数（T≥3 的局部极大）
  base       峰间基座均值（低谷处平均 T 爻数）
  tail_head  末段 T 均值 − 首段 T 均值

判定（写死、不依作品名调参，按 1→5 取首个命中）：
  1 断裂-封存型：jump_pos ≤ 0.35 且 reside_r ≥ 0.15
  2 衰减振荡型：slope ≤ -0.10 且 peak_n ≥ 3
  3 锯齿回升型：slope ≥ 0.10 且 base ≤ 1.8
  4 多峰推进型：slope ≥ 0.10 且 peak_n ≥ 3
  5 平缓型：其余
"""
import json
import hashlib

PEAK_MIN = 3


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    if "works" in d:
        return [(w["work"], w["scenes"]) for w in d["works"]]
    return [(d["work"], d["scenes"])]


def slope(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(range(n)) / n
    my = sum(xs) / n
    num = sum((i - mx) * (xs[i] - my) for i in range(n))
    den = sum((i - mx) ** 2 for i in range(n))
    return num / den if den else 0.0


def shape(scenes):
    rows = [s["u"] + s["m"] + s["l"] for s in scenes]
    ids = [s["id"] for s in scenes]
    n = len(rows)
    tc = [r.count("T") for r in rows]
    dists = [hamming(rows[i], rows[i + 1]) for i in range(n - 1)]
    turn = sum(dists) / len(dists)
    sl = slope(tc)
    jump_i = max(range(len(dists)), key=lambda i: dists[i])
    jump_pos = (jump_i + 1) / n
    # 最长驻留
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
    peaks = [i for i in range(n) if tc[i] >= PEAK_MIN
             and (i == 0 or tc[i] > tc[i - 1]) and (i == n - 1 or tc[i] >= tc[i + 1])]
    peak_n = len(peaks)
    base = sum(tc) / n
    third = max(1, n // 3)
    tail_head = sum(tc[-third:]) / third - sum(tc[:third]) / third
    fp = hashlib.sha256(json.dumps({"s": [(ids[i], rows[i]) for i in range(n)],
                                    "f": [round(turn, 3), round(sl, 3), round(jump_pos, 3),
                                          round(reside_r, 3), peak_n, round(tail_head, 3)]},
                                   ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return {"n": n, "turn": turn, "slope": sl, "jump": dists[jump_i],
            "jump_at": (ids[jump_i], ids[jump_i + 1]), "jump_pos": jump_pos,
            "reside": best, "reside_r": reside_r, "peak_n": peak_n,
            "peaks_at": [ids[i] for i in peaks], "base": base, "tail_head": tail_head,
            "tc": tc, "fp": fp}


def classify(sh):
    if sh["jump_pos"] <= 0.35 and sh["reside_r"] >= 0.15:
        return "1 断裂—封存型", f"最大突变在 {sh['jump_pos']:.0%} 处且长驻留 {sh['reside_r']:.0%}"
    if sh["slope"] <= -0.10 and sh["peak_n"] >= 3:
        return "2 衰减振荡型", f"斜率 {sh['slope']:+.2f}（衰减）且 {sh['peak_n']} 峰"
    if sh["slope"] >= 0.10 and sh["base"] <= 1.8:
        return "3 锯齿回升型", f"斜率 {sh['slope']:+.2f}（回升）且基座仅 {sh['base']:.2f}"
    if sh["slope"] >= 0.10 and sh["peak_n"] >= 3:
        return "4 多峰推进型", f"斜率 {sh['slope']:+.2f}（上升）且 {sh['peak_n']} 峰"
    return "5 平缓型", f"无显著特征（斜率 {sh['slope']:+.2f}）"


def main():
    data = load("jwr_annot.json") + load("works_annot.json")
    out = {}
    print("=" * 96)
    print("形状特征 · 类型判定 v2（同一标准，四部一并计算）")
    print("=" * 96)
    for work, scenes in data:
        sh = shape(scenes)
        t, why = classify(sh)
        out[work] = {**sh, "type": t}
        print(f"\n【{work}】{sh['n']} 场景")
        print(f"  turn {sh['turn']:.2f} | slope {sh['slope']:+.3f} | jump {sh['jump']}@{sh['jump_pos']:.0%}"
              f" | reside {sh['reside']}({sh['reside_r']:.0%}) | peak {sh['peak_n']} | base {sh['base']:.2f}"
              f" | tail-head {sh['tail_head']:+.1f}")
        print(f"  峰位置 {sh['peaks_at']}")
        print(f"  T 曲线 {sh['tc']}")
        print(f"  → {t}（{why}）")
        print(f"  指纹 {sh['fp']}")

    print("\n" + "-" * 96)
    print("两两形状距离（7 维标准化欧氏距离）")
    names = list(out)
    dims = ["turn", "slope", "jump_pos", "reside_r", "peak_n", "base", "tail_head"]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = out[names[i]], out[names[j]]
            d = sum((a[k] - b[k]) ** 2 for k in dims) ** 0.5
            print(f"  {names[i]:<6} ↔ {names[j]:<6} 距离 {d:.3f}"
                  f" | {'同类' if a['type'] == b['type'] else '异类'}")
    print("\n各类归属：")
    for n in names:
        print(f"  {n:<6} → {out[n]['type']}")


if __name__ == "__main__":
    main()
