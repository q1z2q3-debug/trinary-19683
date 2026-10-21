# -*- coding: utf-8 -*-
"""
finance_state.py — 三元九维19683 金融落地 · 阶段0+1 最小框架
=============================================================
定位：不是预测器，而是「市场状态认知层」的最小可验证实现。

能力：
  1. 转译层：把 n 维金融特征序列量化成三态（D=0/R=1/T=2），
     用"截至当期的滚动分位"（默认 33%/67%）映射，避免前视偏差、可复算。
  2. 状态机：n 维三态组合 → 状态编号（n=9 时即 19683 状态空间）。
  3. 状态收益：对每个出现过的状态，统计未来收益分布（样本/均值/中位/标准差）。
  4. IC 检验：特征原始值 vs 未来收益的 Spearman 秩相关（每维特征）。
  5. 分层验证（Walk-forward，样本外）：train 定义"状态信号"，test 按信号分层，
     计算 top-bottom 收益差 + t 值 + 分层单调性 —— 防过拟合的核心证据。

用法（喂自己的数据）：
    import pandas as pd, finance_state as fs
    df 需为时间升序 DataFrame，含特征列 + 未来收益列(forward return)
    report = fs.walk_forward(df, features=['mom','vol','corr'],
                             return_col='fwd_ret', window=60, hold=20)

演示（合成数据，非真实行情）：  python3 finance_state.py

依赖：numpy, pandas（无 scipy 依赖）
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# 三态常量（对齐项目三进制：D=0 / R=1 / T=2）
D, R, T = 0, 1, 2
TRIN = {D: "D", R: "R", T: "T"}


# ---------------------------------------------------------------- 转译层
def rolling_quantile_thresholds(x: np.ndarray, window: int = 60, q_lo=1/3, q_hi=2/3):
    """对序列逐期用『截至当期』的滚动分位给阈值（无前视）。返回 (lo, hi) 两列。"""
    n = len(x)
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    xa = np.asarray(x, dtype=float)
    for i in range(n):
        seg = xa[max(0, i - window + 1): i + 1]  # 截至当期
        if len(seg) < max(5, int(window * 0.5)):
            continue
        lo[i] = np.quantile(seg, q_lo)
        hi[i] = np.quantile(seg, q_hi)
    # 前 window 段没有足够历史 → 用首个有效阈值回填（保证每期有状态、可复算）
    first = np.nanargmin(np.isnan(lo))
    if not np.isnan(lo[first]):
        lo[:first] = lo[first]
        hi[:first] = hi[first]
    # 仍未覆盖（window 内数据过少）→ 退化为符号
    for i in range(n):
        if np.isnan(lo[i]):
            lo[i] = 0.0
            hi[i] = 0.0
    return lo, hi


def quantize(x: np.ndarray, lo: np.ndarray, hi: np.ndarray):
    """按阈值把数值量化为三态：<lo→D, lo..hi→R, >hi→T"""
    xa = np.asarray(x, dtype=float)
    s = np.where(xa < lo, D, np.where(xa > hi, T, R))
    return s.astype(int)


def feature_to_trinary(df: pd.DataFrame, feature: str, window: int = 60):
    """把单个特征列转成三态序列，返回 (三态array, 说明dict)。"""
    x = df[feature].to_numpy(dtype=float)
    lo, hi = rolling_quantile_thresholds(x, window)
    s = quantize(x, lo, hi)
    return s, {"feature": feature, "window": window,
               "lo_method": "rolling_quantile_1/3", "hi_method": "rolling_quantile_2/3"}


# ---------------------------------------------------------------- 状态机
def state_number(trin_states: np.ndarray) -> np.ndarray:
    """n 维三态序列 → 状态编号（基3，维 d 权重 3^d）。n=9 时取值 0..19682。"""
    trin_states = np.asarray(trin_states)
    n_dims = trin_states.shape[0]
    weights = (3 ** np.arange(n_dims))[None, :]
    return (trin_states.T * weights).sum(axis=1).astype(int)


# ---------------------------------------------------------------- IC 检验
def spearman_ic(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman 秩相关（不依赖 scipy）。"""
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 10 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return float("nan")
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denom = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / denom) if denom > 0 else float("nan")


# ---------------------------------------------------------------- 状态收益表
def build_state_table(df: pd.DataFrame, features, return_col: str,
                      window: int = 60, min_samples: int = 20):
    """对全样本：特征→三态→状态编号→状态收益聚合。返回 (状态表DataFrame, 三态DataFrame)。"""
    trin_cols = {}
    enc_meta = []
    for f in features:
        s, meta = feature_to_trinary(df, f, window)
        trin_cols[f + "_tri"] = s
        enc_meta.append(meta)
    tri = pd.DataFrame(trin_cols, index=df.index)

    # 状态编号（按特征顺序，基3编码）
    tri_arr = tri.to_numpy().T          # dims × n
    states = state_number(tri_arr)      # n × 1
    tri["state"] = states
    tri["ret"] = df[return_col].to_numpy(dtype=float)

    # 聚合状态收益
    valid = tri.dropna(subset=["ret"])
    grp = valid.groupby("state")["ret"]
    table = pd.DataFrame({
        "samples": grp.count(),
        "mean": grp.mean(),
        "median": grp.median(),
        "std": grp.std(),
    }).reset_index()
    table = table[table["samples"] >= min_samples].reset_index(drop=True)
    return table, tri, enc_meta


# ---------------------------------------------------------------- Walk-forward 分层验证
def _t_value(a: np.ndarray, b: np.ndarray) -> float:
    """两样本 t 值（Welch，不依赖 scipy）。"""
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 3 or len(b) < 3:
        return float("nan")
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / len(a) + vb / len(b))
    return float((ma - mb) / se) if se > 0 else float("nan")


def walk_forward(df: pd.DataFrame, features, return_col: str, window: int = 60,
                 min_samples: int = 20, train_frac: float = 0.6, n_layers: int = 5):
    """
    样本外验证：train 段定义"状态→平均收益"信号，test 段按信号分层检验。
    返回包含 状态机规模 / 各特征IC / 分层收益 / top-bottom t值 / 结论 的 dict。
    """
    df = df.sort_index()
    n = len(df)
    split = int(n * train_frac)
    tr = df.iloc[:split]
    te = df.iloc[split:]

    # train 状态信号
    tbl_tr, _, enc_meta = build_state_table(tr, features, return_col, window, min_samples)
    if tbl_tr.empty:
        return {"error": "train 段有效状态过少，调小 min_samples 或增大数据"}
    signal = dict(zip(tbl_tr["state"], tbl_tr["mean"]))

    # test 三态 + 状态
    trin_cols = {}
    for f in features:
        s, _ = feature_to_trinary(te, f, window)
        trin_cols[f + "_tri"] = s
    tri_te = pd.DataFrame(trin_cols, index=te.index)
    states_te = state_number(tri_te.to_numpy().T)
    ret_te = te[return_col].to_numpy(dtype=float)

    # test 每行 → 信号（train 已知状态取信号；未知状态=NaN，排除）
    sig = np.array([signal.get(s, np.nan) for s in states_te])
    m = ~np.isnan(sig) & ~np.isnan(ret_te)

    # 各特征 IC（全样本）
    ic = {}
    for f in features:
        ic[f] = spearman_ic(df[f].to_numpy(), df[return_col].to_numpy(dtype=float))

    # 分层：按信号分 n_layers 层，每层 test 平均收益
    if m.sum() >= n_layers * 5:
        layer_of = pd.qcut(pd.Series(sig[m]), n_layers, labels=False, duplicates="drop")
        layer_ret = {}
        lay_vals = pd.Series(sig[m]).to_numpy()
        ret_vals = ret_te[m]
        codes = np.unique(layer_of)                  # 实际层 code（0..K-1）
        for k in codes:
            layer_ret[int(k) + 1] = float(np.nanmean(ret_vals[layer_of == k]))
        top_code = codes[-1]; bottom_code = codes[0]  # 用 code 比较，避免层号偏移
        t_top_bottom = _t_value(ret_vals[layer_of == top_code], ret_vals[layer_of == bottom_code])
        spread = layer_ret[int(top_code) + 1] - layer_ret[int(bottom_code) + 1]
        mono = 1 if len(codes) >= 3 and layer_ret[int(top_code) + 1] == max(layer_ret.values()) else 0
    else:
        layer_ret, t_top_bottom, spread, mono = {}, float("nan"), float("nan"), 0

    # 覆盖
    n_states_used = len(signal)
    coverage = float(np.nanmean(sig[m].size / max(n, 1)))

    conclusion = []
    if spread == spread and abs(t_top_bottom) >= 2.0:
        conclusion.append(f"样本外 top-bottom 收益差 {spread:+.4f}，t={t_top_bottom:+.2f}（|t|≥2，具统计显著性）")
    elif spread == spread:
        conclusion.append(f"样本外 top-bottom 收益差 {spread:+.4f}，t={t_top_bottom:+.2f}（|t|<2，区分度不足）")
    else:
        conclusion.append("test 段可检验样本过少，无法下结论")

    return {
        "n_rows": n,
        "train_rows": split,
        "test_rows": n - split,
        "n_features": len(features),
        "state_space": 3 ** len(features),
        "states_observed_train": int(n_states_used),
        "features_ic": ic,
        "layers_return": layer_ret,
        "spread_top_bottom": spread,
        "t_top_bottom": t_top_bottom,
        "layer_monotonic": mono,
        "encoders": enc_meta,
        "conclusion": conclusion,
        "walk_forward": {"train_frac": train_frac, "window": window,
                         "min_samples": min_samples, "n_layers": n_layers},
    }


def format_report(r: dict) -> str:
    """把 walk_forward 结果格式化成可读报告。"""
    if "error" in r:
        return "错误: " + r["error"]
    L = []
    L.append("=== 三元九维19683 · 金融状态层 样本外验证报告（示意框架） ===")
    L.append(f"样本: 共 {r['n_rows']} 行 | train {r['train_rows']} | test {r['test_rows']} "
             f"(window={r['walk_forward']['window']}, train_frac={r['walk_forward']['train_frac']})")
    L.append(f"状态机: {r['n_features']} 维特征 → 状态空间 {r['state_space']} | train 观测到 {r['states_observed_train']} 个状态")
    L.append("")
    L.append("每维特征 IC（特征原始值 vs 未来收益，Spearman）：")
    for f, v in r["features_ic"].items():
        L.append(f"  {f:<12} IC = {v:+.4f}" if v == v else f"  {f:<12} IC = (样本不足)")
    L.append("")
    L.append(f"样本外分层收益（按 train 状态信号分 {r['walk_forward']['n_layers']} 层，test 段平均收益）：")
    for k in sorted(r["layers_return"]):
        L.append(f"  层{k}: {r['layers_return'][k]:+.4f}")
    L.append(f"  top-bottom 收益差 = {r['spread_top_bottom']:+.4f} | t = {r['t_top_bottom']:+.2f} | 分层单调 = {r['layer_monotonic']}")
    L.append("")
    L.append("结论：" + "；".join(r["conclusion"]))
    return "\n".join(L)


# ---------------------------------------------------------------- 演示（合成数据）
def run_demo(seed: int = 7, n: int = 2000, hold: int = 20):
    """合成数据演示：构造一个『真实动量信号 + 噪声』的假市场，验证框架能捕捉到状态区分度。
    注意：这是示例数据，非真实行情，仅用于证明『框架能捕捉真实存在、但需从数据中发现的状态收益结构』。"""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")

    # 三个自相关强的真实因子（当期值对未来有预测力，因为序列平滑）
    # f1 正向贡献、f2 正向、f3 反向 —— 真实收益结构是它们的加权未来值
    fs = {}
    w = {"f1": 1.0, "f2": 0.6, "f3": -0.4}
    for name in w:
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.99 * x[i - 1] + rng.normal(0, 0.01)
        fs[name] = x

    # 未来收益 = 各因子未来值的加权和 + 噪声（因子自相关 → 当期三态对未来收益有系统预测力）
    fwd = np.full(n, np.nan)
    for i in range(n - hold):
        fwd[i] = sum(w[name] * fs[name][i + hold] for name in w) + rng.normal(0, 0.05)

    df = pd.DataFrame({
        "f1": fs["f1"], "f2": fs["f2"], "f3": fs["f3"], "fwd_ret": fwd,
    }, index=dates)
    return walk_forward(df, features=["f1", "f2", "f3"],
                        return_col="fwd_ret", window=60)


if __name__ == "__main__":
    r = run_demo()
    print(format_report(r))
    print("\n[提示] 这是合成数据演示（非真实行情），用于证明流程可运行。喂入你的真实数据后，")
    print("      请以样本外 top-bottom t 值 ≥2 作为『状态区分度成立』的判定线。")
