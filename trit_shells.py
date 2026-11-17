# -*- coding: utf-8 -*-
"""
trit_shells.py — 平衡三进制金融骨架的四个可分离外壳
=====================================================
骨架（内核冻结）：三值向量 d ∈ {-1,0,+1}^n，n=9
外壳（可独立更替）：

  壳① 索引   group_distance   —— 分组投影，组内查最近邻，组间不合并
  壳② 精度   precision        —— π 位：0 = 未观测（退出分母），1 = 已观测
  壳③ 主从   moderation       —— 从轴只调制主轴强度，不具备决定权
  壳④ 驻留   dwell_filter     —— 翻转须保持 N 期，短命翻转被吃掉
  壳⑤ 路径   path_distance    —— 比最近 k 步的路径形状，不比单点

四条设计原则：
  · 三值只表达「值」；知、时、层、径都在它外面，塞进 trit 就会失真
  · 距离只在 π=1 的维度上算：F = Σ π|s−t| / Σ π；Σπ=0 即「不可比」，返回 None
  · 平权的相关轴才是病，正交化不是解；主从一分，共线变冗余而非冲突
  · 单点状态在非平稳市场不重复，重复的是走法

数据：finance_full_panel_298stocks.csv（后复权+护栏），示例演示·非投资建议
"""
import numpy as np
import pandas as pd

UP, FLAT, DOWN = 1, 0, -1

# 九轴：名称、因子列、角色。role=None 表示该轴本次无数据（π 恒 0）
AXES = [
    ("趋势", "mom20", "主"),
    ("动量", "mom60", "从"),
    ("波动", "vol20", "主"),
    ("量能", "vr",    "从"),
    ("反转", "rev5",  "从"),
    ("估值", "pe",    None),
    ("信用", "credit", None),
    ("情绪", "sent",   None),
    ("政策", "policy", None),
]
N_AXIS = len(AXES)

# 壳① 分组：四组，各自独立成子空间；组间不合并、不跨组比距离
GROUPS = {
    "市场":   [0, 1, 2],
    "流动性": [3],
    "基本面": [5, 6],
    "情绪政策": [7, 8],
}


def tri_series(x, lo, hi):
    """连续量 → 三值。lo/hi 用训练期分位，防前视。"""
    return np.where(x > hi, UP, np.where(x < lo, DOWN, FLAT))


def build_states(panel: pd.DataFrame, train_frac: float = 0.6):
    """把 panel 转成 (date, symbol, d[n], pi[n])。π=0 的轴表示「没测到」。"""
    p = panel.sort_values(["symbol", "date"]).copy()
    g = p.groupby("symbol")["close"]
    p["mom20"] = g.pct_change(20)
    p["mom60"] = g.pct_change(60)
    p["rev5"] = -g.pct_change(5)
    p["vol20"] = g.pct_change().rolling(20).std()
    p["vr"] = p["volume"] / p.groupby("symbol")["volume"].transform(lambda s: s.rolling(20).mean())

    dates = sorted(p["date"].unique())
    si = int(len(dates) * train_frac)
    tr = set(dates[:si])

    d = np.zeros((len(p), N_AXIS), dtype=int)
    pi = np.zeros((len(p), N_AXIS), dtype=int)

    for j, (name, col, role) in enumerate(AXES):
        if role is None or col not in p.columns or p[col].isna().all():
            continue                       # 该轴无数据 → π 全 0，不伪装成中性
        v = p[col].to_numpy()
        obs = ~np.isnan(v)
        lo, hi = np.nanquantile(p.loc[p["date"].isin(tr), col].to_numpy(), [1 / 3, 2 / 3])
        d[obs, j] = tri_series(v[obs], lo, hi)
        pi[obs, j] = 1

    return p[["date", "symbol"]].assign(d=list(d), pi=list(pi))


def precision(states):
    """壳②：报告每轴的观测率。卡点一眼可见——哪一轴根本没数据。"""
    P = np.array(list(states["pi"]))
    return {AXES[j][0]: float(P[:, j].mean()) for j in range(N_AXIS)}


def dist(s, t):
    """F = Σπ|s−t| / Σπ。只在双方都观测的维度上算。Σπ=0 → 不可比（None）。"""
    mask = s["pi"] & t["pi"]
    den = mask.sum()
    if den == 0:
        return None
    num = np.abs(s["d"][mask].astype(int) - t["d"][mask].astype(int)).sum()
    return float(num / den)


def group_distance(s, t):
    """壳①：按组分算，返回字典。组间不合并——避免 5.4 亿的扁平检索。"""
    sd, sp = list(s["d"]), list(s["pi"])
    td, tp = list(t["d"]), list(t["pi"])
    out = {}
    for gn, idx in GROUPS.items():
        num, den = 0, 0
        for j in idx:
            if sp[j] and tp[j]:          # 只在双方都观测到的轴上算
                num += abs(int(sd[j]) - int(td[j]))
                den += 1
        out[gn] = None if den == 0 else num / den
    return out


def moderation(d, pi):
    """
    壳③：主从。主轴定方向（符号），从轴只调制强度。
    返回 (方向, 强度)。强度 = 主轴观测数 + 0.3×从轴一致数，从轴永远不翻转符号。
    """
    main_idx = [j for j, (_, _, r) in enumerate(AXES) if r == "主" and pi[j]]
    sub_idx = [j for j, (_, _, r) in enumerate(AXES) if r == "从" and pi[j]]
    if not main_idx:
        return 0, 0.0
    raw = sum(int(d[j]) for j in main_idx)
    direction = int(np.sign(raw))
    strength = len(main_idx) + 0.3 * sum(1 for j in sub_idx if np.sign(d[j]) == direction)
    return direction, float(strength)


def dwell_filter(seq, n_hold: int = 3):
    """
    壳④：驻留。翻转须保持 n_hold 期才生效，短命翻转被吃掉。
    返回 (过滤后序列, 原始翻转数, 过滤后翻转数)。
    """
    out, held, hold = [seq[0]], seq[0], 0
    raw_flips = 0
    for x in seq[1:]:
        if x != out[-1]:
            raw_flips += 1              # 先记「原始序列里翻了几次」
        if x == held:
            hold = 0
        else:
            hold += 1
            if hold >= n_hold:
                held, hold = x, 0       # 持续够久才承认翻转
        out.append(held)
    filt = sum(1 for i in range(1, len(out)) if out[i] != out[i - 1])
    return out, raw_flips, filt


def path_distance(path_s, path_t, k: int):
    """壳⑤：路径距离。展平最近 k 步，仍只在 π=1 的维度上算。"""
    pd_, ptt = [], []
    for step in range(k):
        pd_.append(path_s[step]["d"])
        ptt.append(path_t[step]["pi"])
    # 用最后一步的 π 作代表掩码（简化：取交集）
    mask = np.ones(N_AXIS, dtype=bool)
    for step in range(k):
        mask &= np.asarray(path_s[step]["pi"], dtype=bool) & np.asarray(path_t[step]["pi"], dtype=bool)
    if mask.sum() == 0:
        return None
    num = 0
    for step in range(k):
        ds = np.asarray(path_s[step]["d"], dtype=int)[mask]
        dt = np.asarray(path_t[step]["d"], dtype=int)[mask]
        num += int(np.abs(ds - dt).sum())
    return float(num / (mask.sum() * k))


def demo(panel_path="finance_full_panel_298stocks.csv"):
    panel = pd.read_csv(panel_path)
    st = build_states(panel)
    print("=" * 74)
    print("壳② 精度：哪一轴真的测到了")
    for k, v in precision(st).items():
        bar = "█" * int(v * 30)
        print(f"  {k:<4} π=1 占比 {v:6.1%}  {bar}")
    n_obs = int(np.mean([p.sum() for p in st['pi']]))
    print(f"  → 平均每场只有 {n_obs} 个轴有值（共 {N_AXIS} 个），其余为「未观测」而非「中性」\n")

    # 取样本最多的一只，做序列演示
    sym = st["symbol"].value_counts().idxmax()
    df = st[st["symbol"] == sym].reset_index(drop=True)
    print(f"=== 序列演示：{sym}（{len(df)} 天）===")
    for i in [0, 1, 100, 150, 200, 250]:
        if i >= len(df):
            continue
        d, pi = df.loc[i, "d"], df.loc[i, "pi"]
        codes = " ".join(f"{('+' if x==UP else '-' if x==DOWN else '0') if pi[j] else '·'}"
                         for j, x in enumerate(d))
        direction, strength = moderation(d, pi)
        sign = "+1" if direction > 0 else ("-1" if direction < 0 else " 0")
        print(f"  {df.loc[i,'date']}  [{codes}]  方向={sign} 强度={strength:.2f}")
    print("  图例：+ 上行 / - 下行 / 0 中性 / · 未观测（π=0）\n")

    # 壳④ 驻留：抖动能不能被吃掉
    trend = [int(x[0]) for x in df["d"]]
    _, raw_f, filt_f = dwell_filter(trend, n_hold=3)
    reduce = (1 - filt_f / raw_f) * 100 if raw_f else 0
    print("=== 壳④ 驻留：趋势轴的翻转次数 ===")
    print(f"  原始翻转 {raw_f} 次 → 驻留 N=3 后 {filt_f} 次，减少 {reduce:.0f}%")
    print("  → 短命翻转被吃掉；不是调阈值，是给状态装寿命\n")

    # 壳② 对照：不加 π vs 加 π
    idx = [i for i in range(len(df)) if df.loc[i, "pi"].sum() >= 3]
    a, b = df.loc[idx[0]], df.loc[idx[len(idx) // 2]]
    d_ignore = float(np.abs(a["d"].astype(int) - b["d"].astype(int)).sum() / N_AXIS)
    d_pi = dist(a, b)
    print("=== 壳② 对照：缺失被当成中性 vs 退出分母 ===")
    print(f"  不加 π（9 维全算）：距离 {d_ignore:.2f}")
    print(f"  加 π（只在观测维算）：距离 {d_pi:.2f}  ← 后者才可比")
    print("  差值不是小数误差，是「把没测到的轴当成中性」造成的系统偏移\n")

    # 壳① 分组距离
    print("=== 壳① 分组：同一对状态，按组分算 ===")
    for gn, val in group_distance(a, b).items():
        print(f"  {gn:<6} {'不可比（该组全未观测）' if val is None else f'{val:.2f}'}")
    print("  → 组间不合并：宏观没数据时，市场组的距离仍然可信\n")

    # 壳⑤ 路径检索
    k = 10
    paths = {}
    for s, g in st.groupby("symbol"):
        if len(g) >= 260:
            paths[s] = g.iloc[-260:].reset_index(drop=True)
    if paths:
        ref_sym = list(paths)[0]
        ref = [paths[ref_sym].iloc[-k + i] for i in range(k)]
        scores = []
        for s, g in paths.items():
            if s == ref_sym:
                continue
            cand = [g.iloc[-k + i] for i in range(k)]
            v = path_distance(ref, cand, k)
            if v is not None:
                scores.append((v, s))
        scores.sort()
        print(f"=== 壳⑤ 路径检索：谁最近 {k} 步的走法最像 {ref_sym} ===")
        for v, s in scores[:3]:
            print(f"  {s}  路径距离 {v:.2f}")
        print("  → 比的是走法，不是单点；单点在非平稳市场几乎不重复")

    print("\n" + "=" * 74)
    print("内核未动：三值向量仍是 {-1,0,+1}^9。四个壳可单独换，互不牵连。")


if __name__ == "__main__":
    demo()
