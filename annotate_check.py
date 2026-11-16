#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""annotate_check.py · 标注合规校验器（可执行的标准）

作用：把《爻位判定手册》的五条纪律做成机器检查，不合格直接报错。
用法：python3 annotate_check.py jwr_annot.json
"""
import json
import sys
import hashlib

TRIT = {"D": 0, "R": 1, "T": 2}
SYM = {"D": "●", "R": "■", "T": "▲"}
POS = ["u3", "u2", "u1", "m3", "m2", "m1", "l3", "l2", "l1"]   # 高位在前
MIN_EV = 5   # 证据最短字数


def dominant(s):
    c = {k: s.count(k) for k in "DRT"}
    top = max(c.values())
    cand = [k for k, v in c.items() if v == top]
    return cand[0] if len(cand) == 1 else s[1]


def state_code(u, m, l):
    n = 0
    for ch in u + m + l:
        n = n * 3 + TRIT[ch]
    return n + 1


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    scenes = data["scenes"]
    exempt = data.get("exempt", {})
    errors, warns = [], []

    for s in scenes:
        full = s["u"] + s["m"] + s["l"]
        # 纪律1：9 爻必须是合法三态
        if len(full) != 9 or any(c not in TRIT for c in full):
            errors.append(f"{s['id']} 九爻不合法: {full}")
        # 纪律2：每位必须有证据短语
        ev = s.get("ev", [])
        if len(ev) != 9:
            errors.append(f"{s['id']} 证据条数 {len(ev)} ≠ 9")
        else:
            for i, e in enumerate(ev):
                if len(e.strip()) < MIN_EV:
                    errors.append(f"{s['id']}.{POS[i]} 证据过短: 「{e}」")
        # 纪律3：非豁免场景九爻不得全同
        if full[0] * 9 == full and s["id"] not in exempt:
            warns.append(f"{s['id']} 九爻全同（{full[0]}）却未登记豁免理由")

    # ---- 指标 ----
    rows = [{"id": s["id"], "full": s["u"] + s["m"] + s["l"],
             "du": dominant(s["u"]), "dm": dominant(s["m"]), "dl": dominant(s["l"]),
             "code": state_code(s["u"], s["m"], s["l"])} for s in scenes]
    dists = [hamming(rows[i]["full"], rows[i + 1]["full"]) for i in range(len(rows) - 1)]
    turn = sum(dists) / len(dists)
    bp, bs, cur, st = 1, 0, 1, 0
    for i, d in enumerate(dists):
        if d <= 1:
            cur += 1
        else:
            if cur > bp:
                bp, bs = cur, st
            cur, st = 1, i + 1
    if cur > bp:
        bp, bs = cur, st
    tc = [r["full"].count("T") for r in rows]
    jump_i = max(range(len(dists)), key=lambda i: dists[i])
    fp = hashlib.sha256(json.dumps(
        {"s": [(r["id"], r["full"]) for r in rows]}, ensure_ascii=False, sort_keys=True
    ).encode()).hexdigest()[:16]

    print("=" * 72)
    print(f"标注合规校验 · {data['work']} · 准则 {data['criterion']}")
    print("=" * 72)
    print(f"场景数 {len(scenes)} · 证据条数 {sum(len(s.get('ev', [])) for s in scenes)}")
    print(f"错误 {len(errors)} 条 · 警告 {len(warns)} 条")
    for e in errors:
        print("  ✗", e)
    for w in warns:
        print("  !", w)
    if not errors and not warns:
        print("  ✅ 五条纪律全部通过")

    print("\n层主导态轨迹（● 封存 / ■ 判定 / ▲ 释放）")
    for key, label in (("du", "上·外部"), ("dm", "中·主体"), ("dl", "下·底盘")):
        print(f"  {label} " + "".join(SYM[r[key]] for r in rows))
    print("        " + "".join(str((i + 1) % 10) for i in range(len(rows))))

    print(f"\n转折密度 {turn:.2f} 爻/场景 · 最长驻留 {bp}"
          f"（{rows[bs]['id']}→{rows[bs + bp - 1]['id']}）"
          f" · 最大突变 {dists[jump_i]} 爻（{rows[jump_i]['id']}→{rows[jump_i + 1]['id']}）")
    print(f"T 爻数曲线 {tc}")
    print(f"结构指纹 {fp}")
    print(f"复算校验 {'✅ 一致' if fp == hashlib.sha256(json.dumps({'s': [(r['id'], r['full']) for r in rows]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16] else '❌'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "jwr_annot.json"))
