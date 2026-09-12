#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.3 新图型模块：funnel / bland_altman / pca / paired / venn / cluster_heatmap。

由 gen_figure.py 在启动时 import 并合并进 GENERATORS/DEMO_DATA；
校验与 alt 文本经 validate_extra()/alt_extra() 钩子接入。
仅依赖 numpy + matplotlib + af_v23_stats。
"""
from __future__ import annotations

import sys

import numpy as np

try:
    import af_v23_stats as st
except ImportError:  # 同目录运行时直接可用；打包路径异常时显式报错
    raise

MAX_CLUSTER_ROWS = 3000   # linkage O(n²) 内存护栏
MAX_PCA_COLS = 200        # 特征列护栏


def _has_cjk(text):
    if not isinstance(text, str):
        return False
    return any('\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f'
               for ch in text)


def _fp(cjk_fp, text):
    return cjk_fp if (cjk_fp is not None and _has_cjk(str(text))) else None


def _warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr)


# ── funnel 漏斗图 ─────────────────────────────────────────────────────

def gen_funnel(data, ax, theme, cjk_fp, **kwargs):
    """Meta 分析漏斗图：研究效应散点 + 合并效应竖线 + 95% 伪置信漏斗线。

    数据: {"studies": [{"name": "Smith 2020", "effect": 0.69, "se": 0.12}, ...]}
    或 {"effects": [...], "ses": [...], "labels": [...] }（效应建议为 log 尺度）。
    选项: egger=True 画 Egger 回归线（stderr 报告不对称检验 p）。
    """
    studies = data.get("studies", None)
    if studies:
        names = [str(s.get("name", f"研究{i+1}")) for i, s in enumerate(studies)]
        es = [float(s["effect"]) for s in studies]
        ses = [float(s["se"]) for s in studies]
    else:
        es = data.get("effects", data.get("effects_list", None))
        ses = data.get("ses", data.get("se_list", None))
        names = list(data.get("labels", []))
        if es is None or ses is None:
            raise ValueError(
                "funnel: 需要 'studies'（每项含 name/effect/se）或 'effects'+'ses' 数组 — "
                "森林图的 effect/lci/uci 格式请先换算（se≈(uci−lci)/3.92）")
    if len(es) != len(ses) or len(es) == 0:
        raise ValueError(f"funnel: effects({len(es)}) 与 ses({len(ses)}) 数量不一致或为空")
    es = np.asarray(es, float)
    ses = np.asarray(ses, float)
    bad = ~(np.isfinite(es) & np.isfinite(ses) & (ses > 0))
    if bad.any():
        raise ValueError(f"funnel: {int(bad.sum())} 个研究的 se 非法（必须为正且有限）")
    if len(es) < 5:
        _warn(f"funnel: 仅 {len(es)} 个研究，漏斗对称性目测不可靠（建议 >=10）")

    pooled = st.dl_pool(es, ses)
    c_main = theme["colors"][0]

    ax.scatter(es, ses, s=36, color=c_main, edgecolor="#333333",
               linewidth=0.8, zorder=4)
    se_max = float(ses.max()) * 1.08
    se_min = 0.0
    # 95% 伪置信漏斗
    for sign in (-1.0, 1.0):
        ax.plot([pooled["pooled"] - 1.96 * se_max, pooled["pooled"],
                 pooled["pooled"] + 1.96 * se_max],
                [se_max, se_min, se_max],
                color="#888888", linewidth=1.2, linestyle="--", zorder=2)
    ax.axvline(pooled["pooled"], color=c_main, linewidth=1.4, linestyle="-",
               alpha=0.85, zorder=3,
               label=f"合并效应 {pooled['pooled']:.3g}")
    ax.axvline(0, color="#BBBBBB", linewidth=0.8, zorder=1)
    ax.invert_yaxis()
    ax.set_ylabel("标准误 se")
    ax.set_xlabel("效应值")

    if kwargs.get("egger"):
        if len(es) >= 3:
            eg = st.egger_test(es, ses)
            # Egger 线：z = intercept + slope * (1/se) → effect = intercept*se + slope
            se_grid = np.linspace(se_min, se_max, 32)
            ax.plot(eg["slope"] + eg["intercept"] * se_grid, se_grid,
                    color=theme["colors"][1 % len(theme["colors"])],
                    linewidth=1.2, linestyle=":", zorder=3,
                    label=f"Egger 回归线 (P={eg['p']:.3g})")
            _warn(f"funnel: Egger 不对称检验 P={eg['p']:.4g}（截距 {eg['intercept']:.3g}）")
        else:
            _warn("funnel: Egger 检验需要 >=3 个研究，已跳过")
    ax.legend(fontsize=theme["font_size"] - 1, loc="upper right", framealpha=0.9,
              prop=cjk_fp if _has_cjk("".join(names)) or cjk_fp and _has_cjk(str(data.get("title", ""))) else None)
    _warn(f"funnel: DL 随机效应合并 {pooled['pooled']:.4g}（95%CI {pooled['pooled']-1.96*pooled['se']:.3g}~"
          f"{pooled['pooled']+1.96*pooled['se']:.3g}），异质性 I²={pooled['i2']:.0f}%，P_het={pooled['p_het']:.3g}")
    return None


# ── bland_altman 一致性分析 ───────────────────────────────────────────

def gen_bland_altman(data, ax, theme, cjk_fp, **kwargs):
    """Bland-Altman 一致性图：均值差 vs 均值，LoA=mean±1.96SD。

    数据: {"a": [...], "b": [...]} 或 {"methods": {"新方法": [...], "金标准": [...]}}
    （methods 恰好两项，差值=第一项−第二项）。
    """
    a, b, name_a, name_b = _two_series(data, "bland_altman")
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) != len(b) or len(a) < 3:
        raise ValueError(f"bland_altman: 两组数据须等长且 >=3 对（当前 {len(a)} vs {len(b)}）")
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        raise ValueError("bland_altman: 含非数值/NaN")
    mean_ab = (a + b) / 2.0
    diff = a - b
    md = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1))
    loa_hi, loa_lo = md + 1.96 * sd, md - 1.96 * sd

    ax.scatter(mean_ab, diff, s=34, color=theme["colors"][0],
               edgecolor="#333333", linewidth=0.8, zorder=4)
    ax.axhline(md, color=theme["colors"][1 % len(theme["colors"])], lw=1.4, zorder=3,
               label=f"均值差 {md:.3g}")
    for v, tag in ((loa_hi, "+1.96SD"), (loa_lo, "−1.96SD")):
        ax.axhline(v, color="#888888", lw=1.2, linestyle="--", zorder=3,
                   label=f"{tag} {v:.3g}")
    ax.axhline(0, color="#CCCCCC", lw=0.8, zorder=2)
    ax.set_xlabel(f"两法均值 ({name_a}/{name_b})")
    ax.set_ylabel(f"差值 ({name_a}−{name_b})")
    ax.legend(fontsize=theme["font_size"] - 1, loc="best", framealpha=0.9,
              prop=_fp(cjk_fp, name_a + name_b))
    _warn(f"bland_altman: 一致性界值 [{loa_lo:.3g}, {loa_hi:.3g}]，"
          f"差值均值 {md:.3g}（SD {sd:.3g}），n={len(a)}")
    return None


def _two_series(data, chart_name):
    """取恰好两个系列：支持 {'a':..,'b':..} 或 {'methods': {名:.., 名:..}}。"""
    if "a" in data and "b" in data:
        return data["a"], data["b"], str(data.get("label_a", "A")), str(data.get("label_b", "B"))
    methods = data.get("methods", None)
    if isinstance(methods, dict) and len(methods) == 2:
        (na, va), (nb, vb) = methods.items()
        return va, vb, str(na), str(nb)
    raise ValueError(
        f"{chart_name}: 需要 'a'+'b' 数组，或 'methods' 恰好两个系列 "
        f"（如 {{\"新方法\": [...], \"金标准\": [...]}}）")



def _declutter_texts(ax, texts, anchors, max_pass=120, step=9.0,
                     max_disp_frac=0.15, leader_min_frac=0.02):
    """散点数据标签防重叠：重叠排斥 + 锚点弹簧 + 位移上限 + 引导线。

    - 排斥：测量真实 bbox，重叠对互推（显示坐标测量、数据坐标移动）
    - 锚点弹簧：每轮向自己的数据点回拉，标签永不远离锚点
    - 位移上限：标签离锚点超过 max_disp_frac·min(轴跨度) 即强制拉回边界
    - 引导线：最终位移 > leader_min_frac 时画点→标签细线，保证对应关系可读
    返回剩余重叠对数。
    """
    if len(texts) < 2:
        return 0
    import math as _m
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    span = min(x1 - x0, y1 - y0)
    max_disp = max_disp_frac * span
    leader_min = leader_min_frac * span
    for _pass in range(max_pass):
        bbs = [t.get_window_extent(renderer) for t in texts]
        n_over = 0
        moves = [(0.0, 0.0)] * len(texts)
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                bi, bj = bbs[i], bbs[j]
                if bi.x1 < bj.x0 or bj.x1 < bi.x0 or bi.y1 < bj.y0 or bj.y1 < bi.y0:
                    continue
                n_over += 1
                dx = (bi.x0 + bi.x1) / 2 - (bj.x0 + bj.x1) / 2
                dy = (bi.y0 + bi.y1) / 2 - (bj.y0 + bj.y1) / 2
                dist = _m.hypot(dx, dy) or 1.0
                ux, uy = dx / dist, dy / dist
                if abs(dx) < 0.5 and abs(dy) < 0.5:
                    ang = 2.399 * (i + 1)
                    ux, uy = _m.cos(ang), _m.sin(ang)
                moves[i] = (moves[i][0] + ux * step, moves[i][1] + uy * step)
                moves[j] = (moves[j][0] - ux * step, moves[j][1] - uy * step)
        if n_over == 0:
            break
        p0 = inv.transform((0, 0))
        p1 = inv.transform((step, step))
        ddx, ddy = p1[0] - p0[0], p1[1] - p0[1]
        for t, (mx, my), (axn, ayn) in zip(texts, moves, anchors):
            tx, ty = t.get_position()
            nx, ny = tx + mx * ddx, ty + my * ddy
            nx += (axn - nx) * 0.25   # 锚点弹簧
            ny += (ayn - ny) * 0.25
            ddx_a, ddy_a = nx - axn, ny - ayn
            dist_a = _m.hypot(ddx_a, ddy_a)
            if dist_a > max_disp:     # 位移上限：拉回锚点邻域
                nx = axn + ddx_a / dist_a * max_disp
                ny = ayn + ddy_a / dist_a * max_disp
            t.set_position((nx, ny))
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    bbs = [t.get_window_extent(renderer) for t in texts]
    n_over = 0
    for i in range(len(bbs)):
        for j in range(i + 1, len(bbs)):
            if bbs[i].overlaps(bbs[j]):
                n_over += 1
    # 引导线：位移超阈值的标签画点→标签细线（对应关系可读）
    drawn = 0
    for t, (axn, ayn) in zip(texts, anchors):
        tx, ty = t.get_position()
        if _m.hypot(tx - axn, ty - ayn) > leader_min:
            ax.plot([axn, tx], [ayn, ty], color="#AAAAAA", linewidth=0.7,
                    zorder=5, clip_on=False)
            drawn += 1
    return n_over


def _thin_overlapping_texts(ax, texts):
    """最后手段：反复移除卷入重叠最多的标签，直到无重叠。返回移除数（调用方发 stderr 警告）。"""
    fig = ax.figure
    removed = 0
    while texts:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbs = [t.get_window_extent(renderer) for t in texts]
        worst, worst_n = -1, 0
        for i, bi in enumerate(bbs):
            n = sum(1 for j, bj in enumerate(bbs) if j != i and bi.overlaps(bj))
            if n > worst_n:
                worst, worst_n = i, n
        if worst_n == 0:
            break
        texts[worst].remove()
        texts.pop(worst)
        removed += 1
    return removed


# ── pca 得分图 ────────────────────────────────────────────────────────

def gen_pca(data, ax, theme, cjk_fp, **kwargs):
    """PCA 得分图（PC1×PC2）：标准化默认开，分组椭圆=均值±2SD，载荷 top5。

    数据: {"matrix": [[...]], "row_labels": [...], "groups": [...](可选, 按行),
           "feature_names": [...]}
    """
    matrix = data.get("matrix", data.get("values", None))
    if matrix is None or not isinstance(matrix, (list, tuple)) or len(matrix) == 0:
        raise ValueError("pca: 需要 'matrix'（二维数值数组，行=样本 列=特征）")
    X = np.asarray(matrix, dtype=float)
    if X.ndim != 2 or X.shape[0] < 3:
        raise ValueError(f"pca: 矩阵需 >=3 行样本（当前 {X.shape}）")
    if X.shape[1] < 2:
        raise ValueError("pca: 至少 2 个特征列")
    if X.shape[1] > MAX_PCA_COLS:
        raise ValueError(f"pca: 特征列 {X.shape[1]} 超过上限 {MAX_PCA_COLS}（维度过高请先降维/筛选）")
    if np.any(~np.isfinite(X)):
        raise ValueError("pca: 矩阵含 NaN/Inf——请先补全或剔除")
    row_labels = list(data.get("row_labels", data.get("labels", [])))
    groups = data.get("groups", None)
    feature_names = list(data.get("feature_names", [f"特征{i+1}" for i in range(X.shape[1])]))
    if len(feature_names) != X.shape[1]:
        feature_names = [f"特征{i+1}" for i in range(X.shape[1])]

    scale = kwargs.get("scale", True)
    Xc = X - X.mean(axis=0)
    if scale:
        sd = X.std(axis=0, ddof=1)
        if np.any(sd == 0):
            zero_cols = int(np.sum(sd == 0))
            keep = sd > 0
            Xc = Xc[:, keep]
            feature_names = [f for f, k in zip(feature_names, keep) if k]
            _warn(f"pca: {zero_cols} 个零方差特征列已剔除")
            if Xc.shape[1] < 2:
                raise ValueError("pca: 剔除零方差列后不足 2 列")
        Xc = Xc / Xc.std(axis=0, ddof=1)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    scores = U * S
    total_var = float(np.sum(S ** 2))
    var_pct = [S[i] ** 2 / total_var * 100 for i in range(min(2, len(S)))]

    import math as _m
    label_texts = []
    _anchors = []
    if groups and isinstance(groups, (list, tuple)) and len(groups) == X.shape[0]:
        uniq = list(dict.fromkeys(str(g) for g in groups))
        for gi, g in enumerate(uniq):
            mask = np.array([str(x) == g for x in groups])
            pts = scores[mask, :2]
            c = theme["colors"][gi % len(theme["colors"])]
            ax.scatter(pts[:, 0], pts[:, 1], s=36, color=c, edgecolor="#333333",
                       linewidth=0.8, zorder=4, label=str(g))
            if mask.sum() >= 3:
                mu = pts.mean(axis=0)
                sd_pts = pts.std(axis=0, ddof=1)
                theta = np.linspace(0, 2 * np.pi, 72)
                ell = np.c_[mu[0] + 2 * sd_pts[0] * np.cos(theta),
                            mu[1] + 2 * sd_pts[1] * np.sin(theta)]
                ax.plot(ell[:, 0], ell[:, 1], color=c, linewidth=1.1,
                        alpha=0.65, linestyle="--", zorder=3)
    else:
        ax.scatter(scores[:, 0], scores[:, 1], s=36, color=theme["colors"][0],
                   edgecolor="#333333", linewidth=0.8, zorder=4)
        if 0 < len(row_labels) == X.shape[0] and X.shape[0] <= 40:
            _fs = max(6, theme["font_size"] - 2)
            _sx = float(np.ptp(scores[:, 0])) or 1.0
            _sy = float(np.ptp(scores[:, 1])) or 1.0
            _anchors = []
            for i, rl in enumerate(row_labels):
                ang = 2.399 * i  # 黄金角环绕初始位，天然散开减少推移
                ox, oy = _sx * 0.02 * _m.cos(ang), _sy * 0.02 * _m.sin(ang)
                label_texts.append(ax.text(
                    scores[i, 0] + ox, scores[i, 1] + oy,
                    str(rl), fontsize=_fs, color="#555555",
                    fontproperties=_fp(cjk_fp, rl), zorder=6,
                    ha="center", va="center"))
                _anchors.append((scores[i, 0], scores[i, 1]))

    # 载荷箭头 top5（|PC1|+|PC2|）
    loadings = Vt[:2, :].T
    imp = np.abs(loadings).sum(axis=1)
    top_idx = np.argsort(imp)[::-1][:5]
    scale_l = np.abs(scores[:, :2]).max() * 0.42 / max(imp[top_idx].max(), 1e-12)
    import matplotlib.patches as _mpatches
    _sx = float(np.ptp(scores[:, 0])) or 1.0
    _sy = float(np.ptp(scores[:, 1])) or 1.0
    for idx in top_idx:
        lx, ly = loadings[idx, 0] * scale_l, loadings[idx, 1] * scale_l
        ax.add_patch(_mpatches.FancyArrowPatch(
            (0, 0), (lx, ly), arrowstyle="->", mutation_scale=14,
            color="#E8A33D", lw=1.3, zorder=5, shrinkA=0, shrinkB=0))
        label_texts.append(ax.text(
            lx + _sx * 0.012, ly + _sy * 0.012, feature_names[idx],
            fontsize=max(6, theme["font_size"] - 2), color="#8a6414",
            fontproperties=_fp(cjk_fp, feature_names[idx]), zorder=7,
            ha="left", va="bottom"))
        _anchors.append((lx, ly))
    ax.axhline(0, color="#CCCCCC", lw=0.8, zorder=1)
    ax.axvline(0, color="#CCCCCC", lw=0.8, zorder=1)
    ax.set_xlabel(f"PC1（解释 {var_pct[0]:.1f}%）")
    ax.set_ylabel(f"PC2（解释 {var_pct[1]:.1f}%）")
    if groups:
        ax.legend(fontsize=theme["font_size"] - 1, loc="best", framealpha=0.9,
                  prop=_fp(cjk_fp, " ".join(str(g) for g in groups)))
    ax.update_datalim(scores[:, :2])
    ax.autoscale_view()
    if label_texts:
        n_left = _declutter_texts(ax, label_texts, _anchors)
        if n_left > 0:
            removed = _thin_overlapping_texts(ax, label_texts)
            if removed:
                _warn(f"pca: 样本标签过密，已省略 {removed} 个重叠标签"
                      "（完整样本清单见 --alt 无障碍描述）")
    _warn(f"pca: PC1+PC2 累计解释 {var_pct[0]+var_pct[1]:.1f}% 方差"
          f"（标准化={'是' if scale else '否'}）")
    return None


# ── paired 配对前后图 ─────────────────────────────────────────────────

def gen_paired(data, ax, theme, cjk_fp, **kwargs):
    """配对前后折线图：每个受试对象一条线 + 配对检验（配对 t / Wilcoxon 符号秩）。

    数据: {"before": [...], "after": [...]} 或
          {"series": {"术前": [...], "术后": [...]}}（恰好两项）+ 可选 labels。
    """
    from scipy import stats as _st
    if "before" in data and "after" in data:
        a = list(data["before"]); b = list(data["after"])
        name_a, name_b = str(data.get("label_a", "Before")), str(data.get("label_b", "After"))
    else:
        series = data.get("series", None)
        if not (isinstance(series, dict) and len(series) == 2):
            raise ValueError(
                "paired: 需要 'before'+'after' 数组，或 'series' 恰好两项"
                "（如 {\"术前\": [...], \"术后\": [...]}）")
        (name_a, a), (name_b, b) = series.items()
    a = np.asarray(a, float); b = np.asarray(b, float)
    if len(a) != len(b) or len(a) < 2:
        raise ValueError(f"paired: 两组须等长且 >=2 对（当前 {len(a)} vs {len(b)}）")
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        raise ValueError("paired: 含非数值/NaN")

    n = len(a)
    c_a = theme["colors"][0]; c_b = theme["colors"][1 % len(theme["colors"])]
    for i in range(n):
        ax.plot([0, 1], [a[i], b[i]], color="#B9B9B9", lw=1.1, zorder=2,
                marker="o", markersize=4, markerfacecolor="white",
                markeredgecolor="#777777")
    ax.scatter(np.zeros(n), a, s=42, color=c_a, edgecolor="#333333",
               linewidth=0.8, zorder=4, label=name_a)
    ax.scatter(np.ones(n), b, s=42, color=c_b, edgecolor="#333333",
               linewidth=0.8, zorder=4, label=name_b)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([name_a, name_b],
                       fontproperties=_fp(cjk_fp, name_a + name_b))
    ax.set_xlim(-0.35, 1.35)

    if kwargs.get("stats_auto"):
        d = b - a
        use_t = True
        if 3 <= n <= 5000 and float(_st.shapiro(d).pvalue) <= 0.05:
            use_t = False
        if n >= 6 and use_t:
            _, p = _st.ttest_rel(b, a)
            method = "配对 t 检验"
        elif n >= 6:
            _, p = _st.wilcoxon(b, a)
            method = "Wilcoxon 符号秩"
        else:
            _warn(f"paired: n={n} <6，检验效力不足，未做统计标注")
            p, method = None, ""
        if p is not None:
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
            top = float(max(a.max(), b.max()))
            span = max(abs(top) * 0.08, 1e-9)
            yi = top + span
            ax.plot([0, 0, 1, 1], [yi - span * 0.25, yi, yi, yi - span * 0.25],
                    color="#333333", lw=1.2, zorder=6)
            ax.text(0.5, yi + span * 0.08, stars, ha="center", va="bottom",
                    fontsize=max(7, theme["font_size"]), color="#333333", zorder=6)
            ax.set_ylim(top=yi + span * 0.7)
            _warn(f"paired: {name_b} vs {name_a}：{method}，p={p:.4g} → {stars}")
    ax.set_ylabel("测量值")
    ax.legend(fontsize=theme["font_size"] - 1, loc="best", framealpha=0.9,
              prop=_fp(cjk_fp, name_a + name_b))
    return None


# ── venn 韦恩图 ───────────────────────────────────────────────────────

def gen_venn(data, ax, theme, cjk_fp, **kwargs):
    """韦恩图（2~3 集合，等圆示意，不按面积比例——数字精确标注）。

    数据: {"sets": {"A": [元素...], "B": [...], "C": [...]}}（列表自动求交并）
          或区域计数 {"sets": {"A": 30, "B": 25, "AB": 9, "ABC": 3, ...}}。
    """
    import matplotlib.patches as mpatches
    sets = data.get("sets", None)
    if not isinstance(sets, dict) or len(sets) not in (2, 3):
        raise ValueError("venn: 'sets' 需为 2~3 个集合的字典")
    keys = [str(k) for k in sets.keys()]
    sample = sets[keys[0]]
    if isinstance(sample, (list, tuple, set)):
        ss = {k: set(sets[k]) for k in keys}
        regions = {}
        if len(keys) == 2:
            A, B = ss[keys[0]], ss[keys[1]]
            regions = {keys[0]: len(A - B), keys[1]: len(B - A),
                       keys[0] + keys[1]: len(A & B)}
        else:
            A, B, C = ss[keys[0]], ss[keys[1]], ss[keys[2]]
            regions = {keys[0]: len(A - B - C), keys[1]: len(B - A - C),
                       keys[2]: len(C - A - B),
                       keys[0] + keys[1]: len((A & B) - C),
                       keys[0] + keys[2]: len((A & C) - B),
                       keys[1] + keys[2]: len((B & C) - A),
                       keys[0] + keys[1] + keys[2]: len(A & B & C)}
    else:
        regions = {}
        for k in keys:
            v = sets[k]
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"venn: 区域 '{k}' 需为非负数字（元素个数）")
            regions[k] = int(v)
        if len(keys) == 2:
            need = {keys[0], keys[1], keys[0] + keys[1]}
        else:
            need = {keys[0], keys[1], keys[2], keys[0]+keys[1], keys[0]+keys[2],
                    keys[1]+keys[2], keys[0]+keys[1]+keys[2]}
        missing = [r for r in need if r not in regions]
        if missing:
            raise ValueError(f"venn: 缺少区域计数 {missing}——请提供全部交并区域（无交集填 0）")
        for r, v in regions.items():
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"venn: 区域 '{r}' 需为非负数字")
        regions = {r: int(v) for r, v in regions.items()}

    colors = theme["colors"][:len(keys)]
    if len(keys) == 2:
        centers = [(0.62, 0.5), (0.38, 0.5)]
        r = 0.27
        # 区域标签绝对坐标（与圆心几何对应）
        k1, k2 = keys
        label_xy = {k1: (0.76, 0.5), k2: (0.24, 0.5), k1 + k2: (0.5, 0.5)}
    else:
        centers = [(0.60, 0.62), (0.40, 0.62), (0.50, 0.40)]
        r = 0.235
        k1, k2, k3 = keys
        label_xy = {k1: (0.745, 0.64), k2: (0.255, 0.64), k3: (0.50, 0.245),
                    k1 + k2: (0.50, 0.705), k1 + k3: (0.585, 0.462),
                    k2 + k3: (0.415, 0.462), k1 + k2 + k3: (0.50, 0.535)}
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal"); ax.axis("off")
    label_pos = [(-0.24, 0.16), (0.24, 0.16), (0.0, -0.26)] if len(keys) == 3 \
        else [(-0.24, 0.0), (0.24, 0.0)]
    for i, k in enumerate(keys):
        cx, cy = centers[i]
        ax.add_patch(mpatches.Circle((cx, cy), r, facecolor=colors[i],
                                     edgecolor="#333333", linewidth=1.4,
                                     alpha=0.42, zorder=2))
        lx, ly = label_pos[i]
        ax.annotate(k, (cx + lx * 1.15, cy + ly * 1.15), fontsize=theme["font_size"] + 2,
                    fontweight="bold", ha="center", va="center",
                    fontproperties=_fp(cjk_fp, k), color="#333333", zorder=5)
    for region, cnt in regions.items():
        lx, ly = label_xy[region]
        ax.annotate(str(cnt), (lx, ly), fontsize=theme["font_size"] + 2,
                    ha="center", va="center", fontweight="bold", color="#333333",
                    zorder=6)
    total = sum(regions.values())
    ax.set_title(f"n = {total}") if not data.get("title") else None
    return None


# ── cluster_heatmap 聚类热图 ──────────────────────────────────────────

def gen_cluster_heatmap(data, ax, theme, cjk_fp, **kwargs):
    """聚类热图：行列按层次聚类（Ward）重排后绘制（v2.3 不含树状图面板，
    聚类顺序写入 stderr 与 alt 文本；树状图面板计划 v2.4）。

    数据格式同 heatmap：{"matrix": [[...]], "row_labels": [...], "col_labels": [...]}。
    """
    from scipy.cluster.hierarchy import linkage, leaves_list
    matrix = data.get("matrix", data.get("data", data.get("values", None)))
    if matrix is None or not isinstance(matrix, (list, tuple)) or len(matrix) == 0:
        raise ValueError("cluster_heatmap: 需要 'matrix'（二维数值数组）")
    M = np.asarray(matrix, dtype=float)
    if M.ndim != 2 or M.shape[0] < 2 or M.shape[1] < 2:
        raise ValueError(f"cluster_heatmap: 矩阵需 >=2×2（当前 {M.shape}）")
    if M.shape[0] > MAX_CLUSTER_ROWS:
        raise ValueError(f"cluster_heatmap: 行数 {M.shape[0]} 超过聚类上限 {MAX_CLUSTER_ROWS}"
                         f"（层次聚类内存随行数平方增长，请先筛选特征/样本）")
    if np.any(~np.isfinite(M)):
        raise ValueError("cluster_heatmap: 矩阵含 NaN/Inf——请先补全（聚类不支持缺失值）")
    row_labels = list(data.get("row_labels", data.get("rows", data.get("y_labels", []))))
    col_labels = list(data.get("col_labels", data.get("cols", data.get("x_labels", []))))

    method = kwargs.get("cluster_method", "ward")
    metric = kwargs.get("cluster_metric", "euclidean")
    row_order = np.array(leaves_list(linkage(M, method=method, metric=metric)))
    col_order = np.array(leaves_list(linkage(M.T, method=method, metric=metric)))
    M2 = M[np.ix_(row_order, col_order)]
    rl2 = [row_labels[i] if i < len(row_labels) else f"行{i+1}" for i in row_order]
    cl2 = [col_labels[i] if i < len(col_labels) else f"列{i+1}" for i in col_order]

    ax._af_category_axis = True  # 行列标签是数据：豁免 fix_tick_overlaps 降级
    cmap = kwargs.get("cmap") or "RdBu_r"
    vmin = kwargs.get("vmin", None) or float(M2.min())
    vmax = kwargs.get("vmax", None) or float(M2.max())
    if vmin == vmax:
        vmin, vmax = vmin - 1e-9, vmax + 1e-9
    im = ax.imshow(M2, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                   interpolation="nearest")
    ax.set_xticks(range(len(cl2)))
    ax.set_xticklabels(cl2, rotation=45, ha="right",
                       fontsize=max(6, theme["font_size"] - 2),
                       fontproperties=_fp(cjk_fp, " ".join(map(str, cl2))))
    ax.set_yticks(range(len(rl2)))
    ax.set_yticklabels(rl2, fontsize=max(6, theme["font_size"] - 2),
                       fontproperties=_fp(cjk_fp, " ".join(map(str, rl2))))
    for spine in ax.spines.values():
        spine.set_visible(False)
    if kwargs.get("show_values"):
        for i in range(M2.shape[0]):
            for j in range(M2.shape[1]):
                ax.text(j, i, f"{M2[i, j]:.1f}", ha="center", va="center",
                        fontsize=max(5, theme["font_size"] - 3),
                        color="white" if abs(M2[i, j] - (vmin+vmax)/2) > (vmax-vmin)/4 else "#333333")
    _warn(f"cluster_heatmap: 行聚类顺序 {rl2[:8]}{'…' if len(rl2) > 8 else ''}；"
          f"列聚类顺序 {cl2[:8]}{'…' if len(cl2) > 8 else ''}（method={method}/{metric}）")
    return im  # 交给主流程挂色条


# ── 注册表 ────────────────────────────────────────────────────────────

EXTRA_GENERATORS = {
    "funnel": gen_funnel,
    "bland_altman": gen_bland_altman,
    "pca": gen_pca,
    "paired": gen_paired,
    "venn": gen_venn,
    "cluster_heatmap": gen_cluster_heatmap,
}

EXTRA_DEMO_DATA = {
    "funnel": {"studies": [
        {"name": "Smith 2020", "effect": 0.69, "se": 0.12},
        {"name": "Lee 2021", "effect": 0.55, "se": 0.20},
        {"name": "王 2022", "effect": 0.80, "se": 0.09},
        {"name": "Garcia 2023", "effect": 0.42, "se": 0.31},
        {"name": "陈 2024", "effect": 0.61, "se": 0.15},
        {"name": "Kim 2025", "effect": 0.73, "se": 0.11},
    ]},
    "bland_altman": {"methods": {"新仪器": [5.1, 4.9, 5.3, 5.6, 4.8, 5.2, 5.0, 5.5],
                                 "金标准": [5.0, 5.1, 5.2, 5.4, 5.0, 5.1, 5.2, 5.3]}},
    "pca": {"matrix": [[5.1, 3.5, 1.4, 0.2], [4.9, 3.0, 1.4, 0.2], [6.7, 3.1, 4.4, 1.4],
                        [6.0, 2.9, 4.5, 1.5], [6.3, 3.3, 6.0, 2.5], [5.8, 2.7, 5.1, 1.9],
                        [4.7, 3.2, 1.3, 0.2], [6.1, 2.8, 4.7, 1.2]],
            "groups": ["setosa", "setosa", "versicolor", "versicolor",
                       "virginica", "virginica", "setosa", "versicolor"],
            "feature_names": ["萼长", "萼宽", "瓣长", "瓣宽"]},
    "paired": {"series": {"术前": [8.2, 7.5, 9.1, 6.8, 7.9, 8.5],
                           "术后": [6.1, 5.8, 7.2, 5.0, 6.3, 6.9]}},
    "venn": {"sets": {"基因集A": ["TP53", "BRCA1", "EGFR", "MYC", "KRAS", "PTEN"],
                      "基因集B": ["TP53", "EGFR", "ALK", "ROS1"],
                      "基因集C": ["TP53", "MYC", "ALK", "NRAS"]}},
    "cluster_heatmap": {"matrix": [[2.1, 0.3, 1.8, 0.1], [1.9, 0.2, 2.0, 0.3],
                                    [0.2, 2.2, 0.1, 1.9], [0.3, 2.0, 0.4, 2.1],
                                    [1.8, 0.4, 1.9, 0.2], [0.1, 1.8, 0.3, 2.0]],
                         "row_labels": ["样本1", "样本2", "样本3", "样本4", "样本5", "样本6"],
                         "col_labels": ["基因A", "基因B", "基因C", "基因D"]},
}


# ── validate / alt / caption 钩子 ─────────────────────────────────────

def validate_extra(chart_type, data):
    """新图型数据校验。返回 (fatal, warn) 两条列表（信息可含修正指引）。"""
    fatal, warns = [], []
    if chart_type == "funnel":
        studies = data.get("studies", None)
        if not studies and (data.get("effects") is None or data.get("ses") is None):
            fatal.append("funnel: 需要 'studies'（每项含 name/effect/se）或 'effects'+'ses'")
        elif studies:
            bad = [i for i, s in enumerate(studies)
                   if not isinstance(s, dict) or "effect" not in s or "se" not in s]
            if bad:
                fatal.append(f"funnel: studies 第 {bad[:3]} 项缺少 effect 或 se 字段")
    elif chart_type == "bland_altman":
        if ("a" not in data or "b" not in data) and not isinstance(data.get("methods"), dict):
            fatal.append("bland_altman: 需要 'a'+'b' 数组或 'methods' 两个系列")
    elif chart_type == "pca":
        m = data.get("matrix")
        if not m:
            fatal.append("pca: 需要 'matrix'（行=样本 列=特征）")
        elif len(m[0]) > MAX_PCA_COLS:
            fatal.append(f"pca: 特征列 {len(m[0])} 超上限 {MAX_PCA_COLS}")
    elif chart_type == "paired":
        if ("before" not in data or "after" not in data) and not isinstance(data.get("series"), dict):
            fatal.append("paired: 需要 'before'+'after' 或 'series' 恰好两项")
    elif chart_type == "venn":
        s = data.get("sets")
        if not isinstance(s, dict) or len(s) not in (2, 3):
            fatal.append("venn: 'sets' 需为 2~3 个集合的字典")
    elif chart_type == "cluster_heatmap":
        m = data.get("matrix", data.get("data", data.get("values")))
        if m is None:
            fatal.append("cluster_heatmap: 需要 'matrix'")
        elif isinstance(m, (list, tuple)) and len(m) > MAX_CLUSTER_ROWS:
            fatal.append(f"cluster_heatmap: 行数 {len(m)} 超过聚类上限 {MAX_CLUSTER_ROWS}")
    return fatal, warns


def alt_extra(chart_type, data, title=""):
    """新图型的无障碍描述（--alt）。"""
    t = f"{title}。" if title else ""
    if chart_type == "funnel":
        n = len(data.get("studies", data.get("effects", [])) or [])
        return f"{t}漏斗图，含 {n} 个研究的效应值散点、DerSimonian-Laird 合并效应线与 95% 伪置信漏斗线。"
    if chart_type == "bland_altman":
        a = data.get("a") or (data.get("methods") or {}).get(list(data.get("methods", {}))[0], [])
        return f"{t}Bland-Altman 一致性图，{len(a)} 对测量的差值-均值散点，含均值差线与 95% 一致性界线。"
    if chart_type == "pca":
        m = data.get("matrix") or []
        return f"{t}PCA 得分图，{len(m)} 个样本投影到前两个主成分平面，橙色箭头为主要载荷特征。"
    if chart_type == "paired":
        b = data.get("before") or []
        return f"{t}配对前后图，{len(b)} 个受试对象各一条灰色折线连接前后两次测量，附配对检验显著性。"
    if chart_type == "venn":
        s = data.get("sets") or {}
        return f"{t}韦恩图，{len(s)} 个集合的交并关系，各区域标注元素个数（不按面积比例）。"
    if chart_type == "cluster_heatmap":
        m = data.get("matrix") or []
        return f"{t}聚类热图，{len(m)} 行按层次聚类重排，颜色深浅映射数值高低。"
    return t or f"{chart_type} 图。"


# ── 图注模板（--caption，中英双语并列） ────────────────────────────────

def make_caption(chart_type, data, title=""):
    """期刊式图注（中英双语并列），写 <out>.caption.txt。渲染失败不阻断出图。"""
    zh_head = f"{title}。" if title else ""
    en_head = ""
    def _n(key, default="?"):
        v = data.get(key)
        return str(len(v)) if isinstance(v, (list, dict, tuple)) else default
    T = {
        "bar": ("柱状图展示各组测量值（n 组）。",
                "Bar chart of measurements across groups."),
        "box": (f"箱线图展示 {_n('series')} 组分布：箱体=四分位距，横线=中位数，须线=1.5×IQR。",
                f"Box plots of {len(data.get('series', {}) or [])} groups: box = IQR, line = median, whiskers = 1.5×IQR."),
        "violin": (f"小提琴图展示 {_n('series')} 组分布（核密度估计），内部箱线为中位数与四分位。",
                "Violin plots (kernel density) with inner box (median and IQR)."),
        "km": ("Kaplan-Meier 生存曲线（纵轴生存概率，横轴时间），下方风险表为各时间点仍处于风险的人数；log-rank 检验。",
               "Kaplan-Meier survival curves with numbers at risk; log-rank test."),
        "roc": ("ROC 曲线，AUC 量化判别能力（0.5=无判别，1.0=完美）。",
                "ROC curves; AUC quantifies discrimination."),
        "forest": ("森林图：各方块为各研究效应值（面积∝权重），横线为 95%CI，菱形为合并效应。",
                   "Forest plot: squares = study effects (area ∝ weight), lines = 95% CI, diamond = pooled effect."),
        "heatmap": ("热图，颜色深浅映射数值大小（见色条）。",
                    "Heatmap; color intensity maps value (see colorbar)."),
        "scatter": ("散点图及线性趋势线。",
                    "Scatter plot with linear trend."),
        "line": ("折线图展示随 x 变化的趋势。",
                 "Line plot of trends."),
        "funnel": ("漏斗图：各研究效应值 vs 标准误，虚线为 95% 伪置信界，竖线为 DL 随机效应合并值。",
                   "Funnel plot: study effects vs SE, dashed pseudo-95% CI bounds, vertical line = DL pooled estimate."),
        "bland_altman": ("Bland-Altman 图：横轴两法均值、纵轴差值；实线=均值差，虚线=95% 一致性界值。",
                         "Bland-Altman plot: mean vs difference; solid = mean difference, dashed = 95% limits of agreement."),
        "pca": ("PCA 得分图（PC1×PC2，标准化后），椭圆为各组均值±2SD，箭头为载荷前 5 特征。",
                "PCA score plot (PC1×PC2, standardized); ellipses = group mean±2SD; arrows = top-5 loadings."),
        "paired": ("配对前后图：每受试对象一条折线连接前后测量，星号为配对检验显著性。",
                   "Paired before-after plot: one line per subject; stars denote paired-test significance."),
        "venn": ("韦恩图展示集合交并（区域数字=元素个数，非面积比例）。",
                 "Venn diagram of set intersections (region labels = counts, not area-proportional)."),
        "cluster_heatmap": ("聚类热图：行/列按 Ward 层次聚类重排，颜色映射数值（见色条）。",
                            "Clustered heatmap: rows/columns reordered by Ward linkage; color maps values."),
    }
    zh, en = T.get(chart_type, (f"{chart_type} 图。", f"{chart_type} figure."))
    if title:
        zh_full = f"图：{zh_head}{zh}"
        en_full = f"Fig. {title}. {en}"
    else:
        zh_full = zh
        en_full = en
    return f"{zh_full}\n{en_full}"
