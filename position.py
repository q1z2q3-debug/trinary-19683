#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""position.py · 位置报告器（替代"团归属"）

不给团名，只报位置。
  1. 七维形状
  2. 5 维 PCA 坐标（有效维度，见 结构真实性检验）
  3. 最近 5 邻（距离）
  4. 稀疏度：到最近 5 邻的平均距离，以及它在全库的百分位
  5. 方位：偏离幅度最大的两维（说明它站在空间的哪一侧）
  6. 最靠近它的一块空白（方向上离它最近的稀疏区）

用法：
  python3 position.py comedy_annot.json
  python3 position.py ulysses_annot.json --k 3
"""
import json, sys, math
import numpy as np
from cluster import DIMS, features

FILES = ["jwr_annot.json", "works_annot.json", "works_annot2.json", "works_annot3.json",
         "works_annot4.json", "works_annot5.json", "cloud_annot.json", "myth_annot.json",
         "comedy_annot.json", "ulysses_annot.json"]


def load_lib():
    out = []
    for fn in FILES:
        d = json.load(open(fn, encoding="utf-8"))
        for w in (d["works"] if "works" in d else [d]):
            out.append((w["work"], features(w["scenes"])))
    return out


def vecs(lib):
    X = np.array([[f[d] for d in DIMS] for _, f in lib])
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = (X - mu) / sd
    ev, vec = np.linalg.eigh(np.cov(Z.T))
    order = ev.argsort()[::-1]
    return X, mu, sd, Z, Z @ vec[:, order[:5]], ev[order]


def report(path, k=5):
    target = []
    d = json.load(open(path, encoding="utf-8"))
    for w in (d["works"] if "works" in d else [d]):
        target.append((w["work"], features(w["scenes"])))
    lib = load_lib()
    lib = [(n, s) for n, s in lib if n not in {t[0] for t in target}] + target
    X, mu, sd, Z, P, ev = vecs(lib)
    idx_t = [i for i, (n, _) in enumerate(lib) if n in {t[0] for t in target}]
    lib_feats = [f for _, f in lib]

    for t in idx_t:
        z = (X[t] - mu) / sd
        dists = sorted(((np.linalg.norm(P[t] - P[j]), lib[j][0]) for j in range(len(lib)) if j != t))
        sp = np.mean([x[0] for x in dists[:k]])
        all_sp = np.array([np.mean(sorted(np.linalg.norm(P[i] - P[j]) for j in range(len(lib)) if j != i)[:k])
                           for i in range(len(lib))])
        pct = (all_sp < sp).mean() * 100
        f = lib_feats[t]
        dev = sorted(((abs(z[j]), DIMS[j]) for j in range(len(DIMS))), reverse=True)[:2]

        print(f"\n《{lib[t][0]}》")
        print("  " + "  ".join(f"{d}={f[d]:+.2f}" for d in DIMS))
        print(f"  稀疏度 {sp:.2f}（全库第 {100 - int(pct)} 稀疏 / 共 {len(lib)} 部，{pct:.0f}% 的作品比它更密）")
        print("  最近邻：" + " / ".join(f"《{n}》{dd:.2f}" for dd, n in dists[:3]))
        print("  方位：偏离最大的是 " + " 与 ".join(
            f"{d}（{'高于' if z[DIMS.index(d)] > 0 else '低于'}均值 {abs(z[DIMS.index(d)]):.1f}σ）" for _, d in dev))
        # 最近的空白方向：从该点向外 8 个方向试探
        best = None
        for a in range(8):
            v = np.zeros(5); v[a % 3] = 1 if a < 3 else -1
            for step in (1.0, 1.5, 2.0):
                q = P[t] + v * step
                md = np.min(np.linalg.norm(P - q, axis=1))
                if md > 1.6 and (best is None or md > best[0]):
                    best = (md, "+" if a < 3 else "-", a % 3, step)
                    break
        if best:
            print(f"  最近的空白：沿 PC{best[2] + 1}{best[1]} 方向 {best[3]:.1f} 个标准差处仍无样本（距最近样本 {best[0]:.2f}）")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    k = 5
    if "--k" in sys.argv:
        k = int(sys.argv[sys.argv.index("--k") + 1])
    report(sys.argv[1], k)
