#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.3 统计深水区模块：KM/log-rank、漏斗图合并、Dunn/Tukey 多重比较、配对 DeLong。

仅依赖 numpy + scipy。所有函数对非法输入抛 ValueError（中文信息），
与 gen_figure.validate_data 的报错风格一致。

对拍基准：Dunn/Tukey 与 scikit-posthocs 对拍（tests）；DeLong 与
delong.py 公开实现的结构恒等式对拍（AUC≡Mann-Whitney、已知数据集数值）。
"""
from __future__ import annotations

import numpy as np


# ── Kaplan-Meier ──────────────────────────────────────────────────────

def km_estimate(times, events):
    """Kaplan-Meier 估计（向量化，O(n log n)，5 万行 <1s）。

    times/events：等长一维序列（event=1 事件，0 删失）。自动排序、非负校验。
    返回 (t_seq, s_seq, censor_points)：阶梯序列 t 从 0 起、s 从 1.0 起
    （where='post' 直接画）；censor_points=[(时间, 删失时生存概率), ...]。
    """
    t = np.asarray(times, dtype=float)
    e = np.asarray(events, dtype=float)
    if t.ndim != 1 or e.ndim != 1 or len(t) != len(e):
        raise ValueError("km: times/events 必须是等长一维数值序列")
    if len(t) == 0:
        raise ValueError("km: 数据为空")
    if np.any(~np.isfinite(t)) or np.any(~np.isfinite(e)):
        raise ValueError("km: 含 NaN/Inf 值")
    if np.any(t < 0):
        raise ValueError("km: 存在负时间")
    if np.any((e != 0) & (e != 1)):
        raise ValueError("km: event 必须是 0（删失）或 1（事件）")
    order = np.argsort(t, kind="stable")
    t, e = t[order], e[order]
    ut, first_idx, counts = np.unique(t, return_index=True, return_counts=True)
    d = np.add.reduceat(e, first_idx)                     # 每唯一时间的事件数
    n_at_risk = len(t) - np.concatenate(([0], np.cumsum(counts)[:-1]))
    has_event = d > 0
    surv_steps = np.ones(len(ut))
    surv_steps[has_event] = 1.0 - d[has_event] / n_at_risk[has_event]
    surv = np.cumprod(surv_steps)
    t_seq = np.concatenate(([0.0], ut))
    s_seq = np.concatenate(([1.0], surv))
    censor_mask = counts > d
    censor_points = list(zip(ut[censor_mask].tolist(), surv[censor_mask].tolist()))
    return t_seq, s_seq, censor_points


def km_at_risk(times, events, eval_times):
    """给定显示时间点，返回各点的风险人数（时间 >= t 计入，t 取等号）。"""
    t = np.asarray(times, dtype=float)
    return [int(np.sum(t >= float(et))) for et in eval_times]


def default_risk_times(all_times, k=5):
    """风险表默认显示时间：0 到最大随访的等分刻度（含 0）。"""
    tmax = float(np.max(all_times)) if len(all_times) else 0.0
    if tmax <= 0:
        return [0.0]
    step = tmax / (k - 1)
    return [round(step * i, 6) for i in range(k)]


def logrank_test(groups):
    """Mantel-Haenszel log-rank 检验（k>=2 组，含删失调整；向量化 O((n+E)·k log n)）。

    groups: {组名: (times, events)}。返回 (chi2, p, df)。
    逐事件时间累计 O/E/V_sum，χ² 在全部时间累计完后一次计算
    （协方差矩阵秩 k−1，删去最后一组用伪逆）。
    """
    from scipy import stats as _st
    clean = {}
    for name, (t, e) in groups.items():
        t = np.asarray(t, dtype=float)
        e = np.asarray(e, dtype=float)
        if len(t) == 0:
            continue
        if len(t) != len(e):
            raise ValueError("log-rank: 组内 times/events 等长")
        order = np.argsort(t, kind="stable")
        clean[name] = (t[order], e[order])
    names = list(clean.keys())
    if len(names) < 2:
        raise ValueError("log-rank 需要 >=2 组")
    k = len(names)
    n_total_all = sum(len(a[0]) for a in clean.values())
    if n_total_all < 2:
        raise ValueError("log-rank: 总样本 <2")
    # 事件时间并集（只在这些时间点更新）
    event_only = [a[0][a[1] == 1] for a in clean.values()]
    event_times = np.unique(np.concatenate(event_only)) if event_only else np.array([])
    # 每组事件时间计数表（唯一事件时间 → 事件数），union 上逐点 O(log n) 查
    Ns = np.array([len(a[0]) for a in clean.values()], dtype=float)
    ev_times_arr, ev_counts_arr = [], []
    for g in range(k):
        et, cnt = np.unique(clean[names[g]][0][clean[names[g]][1] == 1],
                            return_counts=True)
        ev_times_arr.append(et)
        ev_counts_arr.append(cnt)
    O = np.zeros(k)
    E = np.zeros(k)
    V_sum = np.zeros((k, k))
    for ut in event_times:
        n_g = np.array([Ns[g] - np.searchsorted(clean[names[g]][0], ut, side="left")
                        for g in range(k)], dtype=float)
        n_total = n_g.sum()
        if n_total < 2:
            continue
        d_g = np.zeros(k)
        for g in range(k):
            pos = np.searchsorted(ev_times_arr[g], ut)
            if pos < len(ev_times_arr[g]) and ev_times_arr[g][pos] == ut:
                d_g[g] = ev_counts_arr[g][pos]
        d_total = d_g.sum()
        if d_total <= 0:
            continue
        O += d_g
        E += n_g * d_total / n_total
        coef = d_total * (n_total - d_total) / (n_total * n_total * (n_total - 1))
        # V_gg = coef·n_g(n_T−n_g)；V_gh = −coef·n_g·n_h（outer 含对角，需加回 n_g²）
        V_sum += coef * (np.diag(n_g * (n_total - n_g) + n_g * n_g) - np.outer(n_g, n_g))
    # χ² 在全部时间累计完后一次计算（超定降 1 维 + 伪逆）
    diff = (O - E)[:-1]
    Vr = V_sum[:-1, :-1]
    chi2 = float(diff @ np.linalg.pinv(Vr) @ diff) if np.trace(Vr) > 0 else 0.0
    df = len(names) - 1
    return chi2, float(_st.chi2.sf(chi2, df)), df


# ── Meta 分析：DerSimonian-Laird 合并 + Egger 检验（漏斗图） ───────────

def dl_pool(effects, ses):
    """DerSimonian-Laird 随机效应合并。

    effects/ses：各研究效应值与标准误（log RR/OR 或均差等，单位一致即可）。
    返回 dict(pooled, se, q, df, p_het, i2, tau2)。
    """
    from scipy import stats as _st
    es = np.asarray(effects, dtype=float)
    se = np.asarray(ses, dtype=float)
    if len(es) < 2:
        raise ValueError("meta 合并需要 >=2 个研究")
    if np.any(se <= 0) or np.any(~np.isfinite(se)) or np.any(~np.isfinite(es)):
        raise ValueError("meta: se 必须为正且效应值/标准误均为有限数值")
    w = 1.0 / se ** 2
    fe = float(np.sum(w * es) / np.sum(w))
    q = float(np.sum(w * (es - fe) ** 2))
    df = len(es) - 1
    c = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    w_re = 1.0 / (se ** 2 + tau2)
    pooled = float(np.sum(w_re * es) / np.sum(w_re))
    se_pooled = float(1.0 / np.sqrt(np.sum(w_re)))
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 else 0.0
    p_het = float(_st.chi2.sf(q, df))
    return {"pooled": pooled, "se": se_pooled, "q": q, "df": df,
            "p_het": p_het, "i2": i2, "tau2": tau2}


def egger_test(effects, ses):
    """Egger 线性回归法漏斗不对称检验。

    z = effect/se 对 precision = 1/se 回归；截距显著偏离 0 提示不对称。
    返回 dict(intercept, p, slope)。研究数 <5 时统计效力极低（上层负责警告）。
    """
    from scipy import stats as _st
    es = np.asarray(effects, dtype=float)
    se = np.asarray(ses, dtype=float)
    if len(es) < 3:
        raise ValueError("egger 检验需要 >=3 个研究")
    if np.any(se <= 0):
        raise ValueError("egger: se 必须为正")
    precision = 1.0 / se
    z = es / se
    res = _st.linregress(precision, z)
    return {"intercept": float(res.intercept), "p": float(res.pvalue),
            "slope": float(res.slope)}


# ── 多组两两比较（--stats multi） ──────────────────────────────────────

def hochberg(pvals):
    """Hochberg 步进校正，返回校正后 p 值数组（与输入同序）。"""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    adj_sorted = np.empty(n)
    running = 1.0
    for rank_from_top, idx in enumerate(order[::-1]):
        multiplier = n - rank_from_top
        running = min(running, multiplier * p[idx])
        adj_sorted[idx] = min(1.0, running)
    return adj_sorted


def _mse_and_df(groups_vals):
    """单因素 ANOVA 的组内均方 MSE 与自由度 N-k。"""
    k = len(groups_vals)
    n_total = sum(len(g) for g in groups_vals)
    grand = np.mean(np.concatenate(groups_vals))
    sse = sum(float(np.sum((np.asarray(g) - np.mean(g)) ** 2)) for g in groups_vals)
    return sse / (n_total - k), n_total - k


def tukey_pairs(series):
    """Tukey HSD 全两两比较。series: {组名: 数值数组}。
    返回 [(a, b, p_adj, stars, "Tukey HSD")]（未校正的原始 Tukey p，
    校正在 multi_pairwise 统一做 Hochberg？——Tukey 本身即多重比较校正，
    这里不再叠加，直接返回 Tukey p）。"""
    from scipy import stats as _st
    names = list(series.keys())
    k = len(names)
    if k < 2:
        raise ValueError("Tukey 需要 >=2 组")
    vals = [np.asarray(series[n], dtype=float) for n in names]
    means = [float(np.mean(v)) for v in vals]
    ns = [len(v) for v in vals]
    mse, df = _mse_and_df(vals)
    out = []
    for i in range(k):
        for j in range(i + 1, k):
            q = abs(means[i] - means[j]) / np.sqrt(mse / 2.0 * (1.0 / ns[i] + 1.0 / ns[j]))
            p = float(_st.studentized_range.sf(q, k, df)) if mse > 0 else 1.0
            out.append((names[i], names[j], p, _stars(p), "Tukey HSD"))
    return out


def dunn_pairs(series):
    """Dunn 检验全两两比较（Kruskal-Wallis 的事后检验）。
    z = (R̄i − R̄j) / sqrt( σ² (1/ni + 1/nj) )，σ² 含结校正；
    p 为双侧正态近似（未校正，Hochberg 在 multi_pairwise 统一叠加）。"""
    from scipy import stats as _st
    names = list(series.keys())
    vals = [np.asarray(series[n], dtype=float) for n in names]
    all_v = np.concatenate(vals)
    n_total = len(all_v)
    if n_total < 3:
        raise ValueError("Dunn 需要总样本 >=3")
    # 中位秩（含结）
    order = np.argsort(all_v, kind="stable")
    ranks_sorted = np.empty(n_total)
    i = 0
    sorted_v = all_v[order]
    while i < n_total:
        j = i
        while j < n_total and sorted_v[j] == sorted_v[i]:
            j += 1
        ranks_sorted[i:j] = 0.5 * (i + j - 1) + 1.0
        i = j
    ranks = np.empty(n_total)
    ranks[order] = ranks_sorted          # 散回原顺序（组切片按原拼接顺序）
    pos = 0
    rank_means, rank_sums = {}, {}
    for name, v in zip(names, vals):
        n_i = len(v)
        seg = ranks[pos:pos + n_i]
        rank_sums[name] = float(seg.sum())
        rank_means[name] = float(seg.mean())
        pos += n_i
    # 结校正项
    _, tie_counts = np.unique(all_v, return_counts=True)
    tie_term = float(np.sum(tie_counts ** 3 - tie_counts))
    sigma2 = (n_total * (n_total + 1) / 12.0) - tie_term / (12.0 * (n_total - 1)) \
        if n_total > 1 else 0.0
    out = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ni, nj = len(vals[i]), len(vals[j])
            if ni == 0 or nj == 0:
                continue
            se = np.sqrt(max(sigma2, 0.0) * (1.0 / ni + 1.0 / nj))
            z = abs(rank_means[names[i]] - rank_means[names[j]]) / se if se > 0 else 0.0
            p = float(2.0 * _st.norm.sf(z))
            out.append((names[i], names[j], p, _stars(p), "Dunn"))
    return out


def multi_pairwise(series):
    """--stats multi 入口：正态（Shapiro 全过，每组 n>=3）→ ANOVA+Tukey；
    否则 Kruskal-Wallis+Dunn。Tukey 自带校正；Dunn 叠加 Hochberg。
    返回 [(a, b, p, stars, method), ...]。"""
    from scipy import stats as _st
    names = list(series.keys())
    if len(names) < 2:
        raise ValueError("多组比较需要 >=2 组")
    vals = {}
    for n in names:
        v = np.asarray(series[n], dtype=float)
        v = v[np.isfinite(v)]
        vals[n] = v
    vals = {n: v for n, v in vals.items() if len(v) >= 1}
    if len(vals) < 2:
        raise ValueError("有效组不足 2 组")
    all_normal = True
    for v in vals.values():
        if 3 <= len(v) <= 5000:
            if float(_st.shapiro(v).pvalue) <= 0.05:
                all_normal = False
                break
        elif len(v) > 5000:
            continue  # 大样本跳过正态检验，视作正态
        else:
            all_normal = False
            break
    if all_normal:
        pairs = tukey_pairs(vals)
    else:
        pairs = dunn_pairs(vals)
        if not pairs:
            return pairs
        ps = np.array([p for _, _, p, _, _ in pairs])
        adj = hochberg(ps)
        pairs = [(a, b, float(ap), _stars(float(ap)), m + "+Hochberg")
                 for (a, b, p, _, m), ap in zip(pairs, adj)]
    return pairs


def _stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."



# ── v2.4.0：KM 中位生存 + 留一法敏感性 ────────────────────────────────

def km_median_survival(times, events, alpha=0.05):
    """中位生存时间及 95%CI（Greenwood 方差 + log-log 逐点法，与 survfit/lifelines 一致）。

    CI 定义：{t: S(t) 的 CI 包含 0.5}——对每个事件时间 t 逐点计算
    CI(t) = S^exp(∓z·σ(t)/|ln S|)，分别找上/下包络首次穿越 0.5 的时间。
    曲线未降到 0.5 以下返回 (None, None, None)；CI 包络在该方向不可穿越时
    对应端点返回 None（保守，不硬造）。
    """
    from scipy import stats as _st
    t = np.asarray(times, dtype=float)
    e = np.asarray(events, dtype=float)
    if len(t) == 0:
        raise ValueError("km: 数据为空")
    order = np.argsort(t, kind="stable")
    t, e = t[order], e[order]
    ut, first_idx, counts = np.unique(t, return_index=True, return_counts=True)
    d = np.add.reduceat(e, first_idx)
    n_risk = len(t) - np.concatenate(([0], np.cumsum(counts)[:-1]))
    has_event = d > 0
    # d==n_risk（全组死亡）时 1−d/n_risk=0，数学上自洽，无需防除零包装
    surv_steps = np.ones(len(ut))
    surv_steps[has_event] = 1.0 - d[has_event] / n_risk[has_event]
    surv = np.cumprod(surv_steps)
    with np.errstate(divide="ignore", invalid="ignore"):
        var_term = np.where(has_event & (n_risk > d),
                            d / (n_risk * (n_risk - d)), 0.0)
    gvar = np.cumsum(var_term)
    z = float(_st.norm.ppf(1 - alpha / 2))

    def _cross(env):
        """找包络曲线 env 首次降到 0.5 的事件时间（env 为逐点 CI 包络数组）。"""
        idx = np.where(env <= 0.5)[0]
        return float(ut[idx[0]]) if len(idx) else None

    def _cross_interp(ut_arr, surv_arr, env):
        """阶梯穿越点 + 相邻事件时间线性插值（对齐 lifelines 的连续端点）。"""
        env_arr = np.full(len(surv_arr), env, dtype=float) if np.isscalar(env) else np.asarray(env, dtype=float)
        idx = np.where(surv_arr[1:] <= env_arr[1:])[0]
        if not len(idx):
            return None
        k = idx[0] + 1  # surv_arr 含 t=0 起点 1.0
        s_prev, s_cur = surv_arr[k - 1], surv_arr[k]
        t_prev, t_cur = ut_arr[k - 1], ut_arr[k]
        if s_cur == s_prev:
            return float(t_cur)
        frac = (s_prev - env_arr[k]) / (s_prev - s_cur)
        return float(t_prev + (t_cur - t_prev) * frac)

    below = np.where(surv <= 0.5)[0]
    if not len(below):
        return None, None, None
    med = float(ut[below[0]])
    # 逐点 CI 包络：σ(t)=sqrt(gvar)/|ln S|
    # 标准 log-log CI：CI(t) = S(t)^exp(∓z·σ(t))，σ(t)=√gvar/|lnS|
    safe_log = np.where((surv > 0) & (surv < 1), np.abs(np.log(np.where(surv > 0, surv, 0.5))), 1.0)
    sigma = np.where((surv < 1.0) & (surv > 0.0), np.sqrt(gvar) / safe_log, 0.0)
    lo_env = np.power(surv, np.exp(+np.minimum(z * sigma, 50)))  # 下包络 ≤ S：更晚穿越 0.5
    hi_env = np.power(surv, np.exp(-np.minimum(z * sigma, 50)))  # 上包络 ≥ S：更早穿越 0.5
    # 悲观下包络（≤S）更早穿 0.5 = CI 下限；乐观上包络（≥S）更晚穿 = CI 上限
    ci_lo = _cross(lo_env)
    ci_hi = _cross(hi_env)
    return med, ci_lo, ci_hi


def _m_sqrt(x):
    return float(np.sqrt(x))


def _m_log(x):
    return float(np.log(x))


def _m_exp(x):
    return float(np.exp(x))


def _m_sqrt(x):
    return float(np.sqrt(x))


def _m_log(x):
    return float(np.log(x))


def _m_exp(x):
    return float(np.exp(x))


def leave_one_out(es, ses):
    """留一法敏感性分析：对每个研究 i，用其余 N-1 项做 DL 随机效应合并。

    es/ses：全研究效应值与标准误。返回 [(省略的研究名或序号, pooled, lo, hi), ...]。
    恒等式：留一 i 的合并效应 == 用 N-1 子集直接 DL——由调用方测试对拍。
    """
    es = list(es)
    ses = list(ses)
    n = len(es)
    if n < 4:
        raise ValueError("留一法需要 >=4 个研究（太少无敏感性意义）")
    out = []
    for i in range(n):
        sub_e = [es[k] for k in range(n) if k != i]
        sub_s = [ses[k] for k in range(n) if k != i]
        r = dl_pool(sub_e, sub_s)
        out.append((i, r["pooled"],
                    r["pooled"] - 1.96 * r["se"], r["pooled"] + 1.96 * r["se"]))
    return out

# ── 配对 DeLong（ROC 多模型 AUC 比较） ────────────────────────────────

def _midrank(x):
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="stable")
    xs = x[order]
    n = len(x)
    t = np.empty(n)
    i = 0
    while i < n:
        j = i
        while j < n and xs[j] == xs[i]:
            j += 1
        t[i:j] = 0.5 * (i + j - 1) + 1.0
        i = j
    out = np.empty(n)
    out[order] = t
    return out


def delong_paired(labels, scores_by_model):
    """配对 DeLong 检验：同一样本上 >=2 个模型的 AUC 两两比较。

    labels: 0/1 数组（1=阳性）；scores_by_model: {模型名: 分数数组}。
    返回 (aucs dict, [(a, b, p, z), ...])。
    """
    from scipy import stats as _st
    y = np.asarray(labels, dtype=float)
    if len(y) == 0 or np.any(~np.isin(y, (0.0, 1.0))):
        raise ValueError("DeLong: labels 必须是 0/1 数组")
    m_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    if m_pos == 0 or n_neg == 0:
        raise ValueError("DeLong: 需要同时包含阳性和阴性样本")
    names = list(scores_by_model.keys())
    tz_at_pos, tx_pos, tz_at_neg, ty_neg, aucs = [], [], [], [], {}
    for name in names:
        s = np.asarray(scores_by_model[name], dtype=float)
        if len(s) != len(y) or np.any(~np.isfinite(s)):
            raise ValueError(f"DeLong: 模型 {name} 的分数与 labels 等长且为有限数值")
        z = _midrank(s)                 # 全体中位秩
        tx = _midrank(s[y == 1])        # 阳性内部中位秩
        ty = _midrank(s[y == 0])        # 阴性内部中位秩
        tz_at_pos.append(z[y == 1])
        tx_pos.append(tx)
        tz_at_neg.append(z[y == 0])
        ty_neg.append(ty)
        # AUC = 每阳性样本 (Tz−Tx)/n_neg 的均值（与 Mann-Whitney U 恒等）
        aucs[name] = float(np.mean((z[y == 1] - tx) / n_neg))
    k = len(names)
    # v01：每阳性样本对 AUC 的结构贡献；v10：每阴性样本的结构贡献
    v01 = np.empty((k, m_pos))
    v10 = np.empty((k, n_neg))
    for r, name in enumerate(names):
        v01[r] = (tz_at_pos[r] - tx_pos[r]) / n_neg
        v10[r] = (tz_at_neg[r] - ty_neg[r]) / m_pos
    sx = np.cov(v01) if m_pos > 1 else np.zeros((k, k))
    sy = np.cov(v10) if n_neg > 1 else np.zeros((k, k))
    sigma = sx / m_pos + sy / n_neg
    pairs = []
    for i in range(k):
        for j in range(i + 1, k):
            var = sigma[i, i] + sigma[j, j] - 2.0 * sigma[i, j]
            if var <= 0:
                p, z = 1.0, 0.0
            else:
                z = abs(aucs[names[i]] - aucs[names[j]]) / np.sqrt(var)
                p = float(2.0 * _st.norm.sf(z))
            pairs.append((names[i], names[j], p, float(z)))
    return aucs, pairs
