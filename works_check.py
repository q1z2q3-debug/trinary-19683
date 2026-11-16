#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""works_check.py · 学习阶段：用同一套标准标多部作品，看标准立不立得住

读入：jwr_annot.json（局外人，21 场景）+ works_annot.json（三部，各 18 场景）
输出：每部合规性 + 结构画像 + 类型判定 + 指纹 + 两两画像距离

类型判定规则（写死，可复算，不按作品调参）：
  A 断裂型   ：存在单步突变 ≥7 爻，且突变之后 D 爻占比 ≥ 0.55
  B 循环振荡型：转折密度 ≥3.60 且峰数 ≥4
  C 多峰推进型：峰数 3–5 且末段 T 均值 > 首段
  D 长坡下行型：全篇 T 占比 <0.35 且末段 T 均值 ≤ 首段
  E 单峰型   ：其余且峰数 ≤2
判定按 A→B→C→D→E 优先级取首个命中。

用法：python3 works_check.py
"""
import json
import hashlib
import math

TRIT = {"D": 0, "R": 1, "T": 2}
MIN_EV = 5
PEAK_MIN = 3          # T 爻数 ≥3 才算一个峰，滤掉噪声


def dominant(s):
    c = {k: s.count(k) for k in "DRT"}
    top = max(c.values())
    cand = [k for k, v in c.items() if v == top]
    return cand[0] if len(cand) == 1 else s[1]


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    if "works" in d:
        return [(w["work"], w["scenes"], w.get("exempt", {})) for w in d["works"]]
    return [(d["work"], d["scenes"], d.get("exempt", {}))]


def check(work, scenes, exempt):
    errs = 0
    for s in scenes:
        full = s["u"] + s["m"] + s["l"]
        if len(full) != 9 or any(c not in TRIT for c in full):
            print("  ✗ 九爻不合法", s["id"], full); errs += 1
        if len(s.get("ev", [])) != 9:
            print("  ✗ 证据条数不足", s["id"]); errs += 1
        else:
            for e in s["ev"]:
                if len(e.strip()) < MIN_EV:
                    print("  ✗ 证据过短", s["id"], e); errs += 1
        if full[0] * 9 == full and s["id"] not in exempt:
            print("  ! 九爻全同未豁免", s["id"]); errs += 1
    return errs


def profile(scenes):
    rows = [{"id": s["id"], "full": s["u"] + s["m"] + s["l"]} for s in scenes]
    n = len(rows)
    dists = [hamming(rows[i]["full"], rows[i + 1]["full"]) for i in range(n - 1)]
    turn = sum(dists) / len(dists)
    tc = [r["full"].count("T") for r in rows]
    dc = [r["full"].count("D") for r in rows]
    rc = [r["full"].count("R") for r in rows]
    tot = n * 9
    tp = sum(tc) / tot
    dp = sum(dc) / tot
    rp = sum(rc) / tot
    # 最长驻留（相邻差 ≤1 的连续段）
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
    # 峰数（局部极大且 ≥PEAK_MIN）
    peaks = [i for i in range(n) if tc[i] >= PEAK_MIN
             and (i == 0 or tc[i] > tc[i - 1]) and (i == n - 1 or tc[i] >= tc[i + 1])]
    head = sum(tc[:max(1, n // 3)]) / max(1, n // 3)
    tail = sum(tc[-max(1, n // 3):]) / max(1, n // 3)
    jump_i = max(range(len(dists)), key=lambda i: dists[i])
    after_d = sum(r["full"].count("D") for r in rows[jump_i + 1:]) / \
              max(1, (n - jump_i - 1) * 9)
    fp = hashlib.sha256(json.dumps({"s": [(r["id"], r["full"]) for r in rows],
                                    "k": [round(turn, 4), best, dists[jump_i]]},
                                   ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return {"rows": rows, "turn": turn, "tp": tp, "dp": dp, "rp": rp,
            "reside": best, "reside_at": (rows[bs]["id"], rows[bs + best - 1]["id"]),
            "peaks": len(peaks), "head": head, "tail": tail,
            "jump": dists[jump_i], "jump_at": (rows[jump_i]["id"], rows[jump_i + 1]["id"]),
            "after_d": after_d, "tc": tc, "fp": fp}


def classify(st):
    if st["jump"] >= 7 and st["after_d"] >= 0.55:
        return "A 断裂型", f"最大突变 {st['jump']} 爻且其后 D 占比 {st['after_d']:.2f}"
    if st["turn"] >= 3.60 and st["peaks"] >= 4:
        return "B 循环振荡型", f"转折密度 {st['turn']:.2f} 且峰数 {st['peaks']}"
    if 3 <= st["peaks"] <= 5 and st["tail"] > st["head"]:
        return "C 多峰推进型", f"峰数 {st['peaks']} 且末段 {st['tail']:.1f} > 首段 {st['head']:.1f}"
    if st["tp"] < 0.35 and st["tail"] <= st["head"]:
        return "D 长坡下行型", f"T 占比 {st['tp']:.2f} 且末段未回升"
    return "E 单峰型", f"峰数 {st['peaks']}"


def main():
    data = load("jwr_annot.json") + load("works_annot.json")
    stats = {}
    print("=" * 92)
    print("学习阶段：四部作品 · 同一标准 · 结构画像与类型判定")
    print("=" * 92)
    for work, scenes, exempt in data:
        print(f"\n【{work}】{len(scenes)} 场景")
        e = check(work, scenes, exempt)
        print("  合规校验", "✅ 0 错误" if e == 0 else f"❌ {e} 处问题")
        st = profile(scenes)
        typ, why = classify(st)
        stats[work] = {**st, "type": typ}
        print(f"  类型 {typ}（{why}）")
        print(f"  转折 {st['turn']:.2f} · D {st['dp']:.2f} / R {st['rp']:.2f} / T {st['tp']:.2f}"
              f" · 最长驻留 {st['reside']}（{st['reside_at'][0]}→{st['reside_at'][1]}）")
        print(f"  峰数 {st['peaks']} · 首段T {st['head']:.1f} · 末段T {st['tail']:.1f}"
              f" · 最大突变 {st['jump']}（{st['jump_at'][0]}→{st['jump_at'][1]}）")
        print(f"  T 曲线 {st['tc']}")
        print(f"  指纹 {st['fp']}")

    # ---- 两两画像距离 ----
    print("\n" + "-" * 92)
    print("标准立不立得住：① 四部是否各归其类 ② 两两画像是否分得开 ③ 类型是否与文学共识相符")
    names = list(stats)
    keys = ["turn", "tp", "dp", "rp"]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = stats[names[i]], stats[names[j]]
            dist = sum(abs(a[k] - b[k]) for k in keys) / len(keys)
            print(f"  {names[i]:<6} ↔ {names[j]:<6} 画像距离 {dist:.3f}"
                  f" | 类型 {'相同' if a['type'] == b['type'] else '不同'}")
    print("\n类型汇总：")
    for n in names:
        print(f"  {n:<6} → {stats[n]['type']} · 指纹 {stats[n]['fp']}")


if __name__ == "__main__":
    main()
