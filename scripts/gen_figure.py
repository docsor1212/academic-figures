#!/usr/bin/env python3
"""
academic-figures v2.0.0: Publication-quality academic figure generator.

Generates charts from JSON/CSV data with:
- Publication-grade aesthetics (Nature/Science/Lancet style)
- Okabe-Ito colorblind-safe palette (Nature Methods gold standard)
- CJK (Chinese/Japanese/Korean) auto-detection, zero garbled text
- Bilingual labels (Chinese + English)
- Statistical annotations (error bars, significance markers)
- High-DPI output (600dpi default for line art, PDF/SVG/EPS/TIFF support)
- Enhanced forest plot (weights, heterogeneity I², events/total)

Usage:
  python gen_figure.py -t bar -d data.json -o figure.png
  python gen_figure.py -t heatmap -d data.json -o figure.png --cjk
  python gen_figure.py -t scatter -d data.csv -o figure.svg
  python gen_figure.py -t forest -d data.json -o figure.pdf --theme okabe-ito
  python gen_figure.py -t bar -d data.json -o figure.tiff --dpi 300

Data formats: JSON or CSV (first column = labels, rest = series)
"""
import argparse, json, csv, subprocess, sys, os, time, threading

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.transforms import BboxBase
import numpy as np

_STYLE_NO_GRID = [False]  # v3.3 --style nature-clean：图型级网格关闭开关

# v3.0.0 模块化：wizard 与异常诊断系统拆至独立模块（原名在此命名空间可用）
from af_wizard import _run_wizard
from af_diagnostics import (_EXIT_DATA_CLASSES, _EXIT_ENV_CLASSES,
                            _classify_exit_code, _diagnose_exception,
                            _print_v3_error, _EXC_ZH_V3, _DIAG_PATTERNS,
                            _KNOWN_DATA_FIELDS)

try:
    import af_v23_stats as _afstats
    import af_v23_charts as _afcharts
except ImportError:  # v2.3 新图型/统计模块不在同目录时降级
    _afstats = None
    _afcharts = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DETECT_SCRIPT = os.path.join(SCRIPT_DIR, "detect_cjk_font.py")

# ── Style presets ──────────────────────────────────────────────────────
THEMES = {
    # Default theme is "glm" (elegant muted palette, colorblind-safe).
    # The old matplotlib-default palette is preserved as "classic".
    "classic": {
        "figsize": (10, 6),
        "dpi": 600,
        "font_size": 11,
        "colors": ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860",
                   "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"],
        "grid_alpha": 0.3,
        "spines": ["top", "right"],  # spines to hide
        "colorblind_safe": False,
    },
    # Okabe-Ito: Nature Methods recommended gold-standard colorblind-safe palette
    # Ref: Wong (2011) Nature Methods 8:441; Wilke "Fundamentals of Data Visualization"
    "okabe-ito": {
        "figsize": (8, 5.5),
        "dpi": 600,
        "font_size": 7,
        "colors": ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2",
                   "#D55E00", "#CC79A7", "#000000", "#999999", "#44AA99"],
        "grid_alpha": 0.2,
        "spines": ["top", "right"],
        "colorblind_safe": True,
    },
    "nature": {
        "figsize": (8, 5.5),
        "dpi": 600,
        "font_size": 7,
        "colors": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4",
                   "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
        "grid_alpha": 0.2,
        "spines": ["top", "right"],
        "colorblind_safe": False,
    },
    "lancet": {
        "figsize": (9, 6),
        "dpi": 600,
        "font_size": 7,
        "colors": ["#00468B", "#ED0000", "#42B540", "#0099B4", "#525252", "#7F6F00",
                   "#ED7D31", "#8B6914", "#4C0099", "#99CC00"],
        "grid_alpha": 0.25,
        "spines": ["top", "right"],
        "colorblind_safe": False,
    },
    # NEJM 官方风配色（ggsci nejm 色板，8 色）
    "nejm": {
        "figsize": (9, 6),
        "dpi": 600,
        "font_size": 8,
        "colors": ["#BC3C29", "#0072B5", "#E18727", "#20854E", "#7876B1", "#6F99AD",
                   "#FFDC91", "#EE4C97"],
        "grid_alpha": 0.25,
        "spines": ["top", "right"],
        "colorblind_safe": False,
    },
    # Science（AAAS）官方风配色（ggsci aaas 色板，10 色）
    "science": {
        "figsize": (8, 5.5),
        "dpi": 600,
        "font_size": 7,
        "colors": ["#3B4992", "#EE0000", "#008B45", "#631879", "#008280", "#BB0021",
                   "#5F559B", "#A20056", "#808180", "#1B1919"],
        "grid_alpha": 0.2,
        "spines": ["top", "right"],
        "colorblind_safe": False,
    },
    "conservative": {
        "figsize": (9, 5.5),
        "dpi": 600,
        "font_size": 8,
        "colors": ["#2E86C1", "#A0A0A0", "#E74C3C", "#27AE60", "#F39C12", "#8E44AD",
                   "#1ABC9C", "#E67E22", "#34495E", "#16A085"],
        "grid_alpha": 0.3,
        "spines": ["top", "right"],
        "colorblind_safe": False,
    },
    # GLM theme: elegant muted palette inspired by GLM-5.2 blog
    # Medium saturation — visible but not garish (素雅但不淡).
    # Darker than the raw blog pixels (#70A0D0 etc were too pale to read).
    # Verified: each color passes 4.5:1 contrast against white background.
    "glm": {
        "figsize": (10, 6),
        "dpi": 600,
        "font_size": 11,
        "colors": ["#5B8DBE",  # steel blue (比#70A0D0深一档，清晰可辨)
                   "#D79D55",  # warm yellow (GLM-5.2原图黄色像素均值，比#D09050亮一档)
                   "#6BA776",  # sage green
                   "#9B7BB8",  # dusty purple
                   "#C9694E",  # muted coral
                   "#5BA0A0",  # teal
                   "#B47A8E",  # mauve
                   "#7A7A7A",  # warm gray
                   "#C4A44A",  # mustard gold
                   "#7AAF42"],  # olive
        "grid_alpha": 0.15,
        "spines": ["top", "right"],
        "colorblind_safe": True,
    },
    # Cool theme: elegant muted cool-toned palette (blues, teals, slate)
    # All colors in 190-260° hue range, low-medium saturation
    # Inspired by editorial design (FT/Economist) cool palettes
    "cool": {
        "figsize": (9, 5.5),
        "dpi": 600,
        "font_size": 8,
        "colors": ["#1B4965",  # deep navy
                   "#2E6F9E",  # ocean blue
                   "#4FA3C5",  # sky blue
                   "#3D8080",  # dark teal
                   "#62A0A8",  # medium teal
                   "#5B7BA0",  # steel blue-gray
                   "#7B9AB5",  # slate blue
                   "#9DB5CC"],  # pale steel
        "grid_alpha": 0.15,
        "spines": ["top", "right"],
        "colorblind_safe": True,
    },
}

THEME_ALIASES = {
    "okabe": "okabe-ito", "colorblind": "okabe-ito", "colorblind-safe": "okabe-ito",
    "okabeIto": "okabe-ito", "okabeito": "okabe-ito",
    "classic": "classic", "matplotlib": "classic", "default": "glm",
    "glm": "glm", "glm-blog": "glm", "glmblog": "glm",
    "cool": "cool", "cool-toned": "cool",
    "nature": "nature", "npg": "nature",
    "lancet": "lancet", "the-lancet": "lancet",
    "nejm": "nejm", "new-england": "nejm", "new-england-journal": "nejm",
    "science": "science", "aaas": "science",
    "conservative": "conservative", "conserv": "conservative",
}

THEME_SWATCH_DESCRIPTIONS = {
    "glm": "GLM 素雅莫兰迪风（默认）· 色盲安全 · 钢蓝/暖黄/鼠尾草绿/灰紫/珊瑚",
    "classic": "经典 matplotlib 色板（v2.0 前的旧默认）",
    "okabe-ito": "Nature Methods 金标准 · 色盲安全 · 橙/天蓝/绿/黄/深蓝/红",
    "nature": "NPG 期刊风 · 红/蓝/绿/藏蓝",
    "lancet": "The Lancet 期刊风 · 深蓝/红/绿",
    "nejm": "NEJM 期刊风 · 砖红/钢蓝/橙/绿（8 色）",
    "science": "Science（AAAS）期刊风 · 藏蓝/红/绿/紫（10 色）",
    "conservative": "保守学术 · 蓝灰为主",
    "cool": "冷色调 · 深海军蓝→浅钢蓝 8 阶 · 色盲安全",
}

THEME_ORDER = ["glm", "classic", "okabe-ito", "nature", "lancet", "nejm", "science",
               "conservative", "cool"]


def resolve_theme(name):
    """Resolve a --theme value to a canonical THEMES key (alias + lenient matching).
    Returns the canonical key, or None if no match."""
    if not name:
        return "glm"
    key = name.strip().lower()
    if key in THEMES:
        return key
    if key in THEME_ALIASES:
        return THEME_ALIASES[key]
    for canonical in THEMES:
        if canonical.startswith(key):
            return canonical
    return None


CHART_NOTES = {
    "bar": "bar/hbar: JSON 或 CSV 均可；CSV 首列为 X 标签。误差棒需 JSON errors 字段（CSV 不支持）。--hatch 斜纹适合打印/黑白场景。",
    "grouped_bar": "同 bar。多 series 自动分组；--show-ratio 显示比值标注。",
    "hbar": "同 bar（horizontal）。标签过长时 horizontal 模式更合适。",
    "stacked_bar": "stacked_bar: 构成比堆叠；JSON percentage=true 归一化为 100%；CSV 每列为一个 series。",
    "heatmap": "heatmap: JSON matrix 必填（rows/cols 可选）；--cmap 自定义色阶；大矩阵建议 PNG/SVG。",
    "scatter": "scatter: JSON 或 CSV；groups 字段区分颜色；--no-trend 关闭趋势线。",
    "line": "line: JSON series 或多列 CSV；x 轴标签 JSON labels 或 CSV 首列。",
    "dual_axis": "dual_axis: 需要 JSON 含 left/right 两个 series 定义；CSV 不支持双轴。",
    "box": "box: 每列为一个分布；CSV 或 JSON datasets。",
    "forest": "forest: meta 分析森林图；JSON estimates/ci_low/ci_high 必填，可选 weights/overall/heterogeneity/events。",
    "km": "km: Kaplan-Meier；JSON 需 time/status 数据结构，参考文档 §统计数据。",
    "roc": "roc: ROC 曲线；JSON 需 scores/labels，参考文档 §统计数据。",
    "violin": "violin: 小提琴图；JSON datasets 或 CSV，每列为分布。",
    "composite": "composite: 多面板组合图；JSON panels 数组定义子图，参考文档 §组合图。",
    "diagram": "diagram: 架构/流程图；JSON boxes/arrows，CONSORT 式，参考文档 §流程图。",
    "prisma": "prisma: PRISMA 2020 系统综述流程图；JSON 需 records_identified/studies_included，"
              "数字自洽性自动校验（对不上报 ERROR 拒绝出图）；lang=zh 输出中文标准版；"
              "参考文档 §PRISMA 流程图。",
    "funnel": "funnel: Meta 漏斗图；JSON studies（每项 name/effect/se，效应建议 log 尺度）；"
              "自动 DL 随机效应合并线+95% 伪置信漏斗；--egger 加不对称回归线（<5 研究警告）。",
    "bland_altman": "bland_altman: 一致性分析；JSON methods 恰好两项系列或 a/b 数组；"
                    "自动均值差线与 ±1.96SD 一致性界线。",
    "pca": "pca: PCA 得分图；JSON matrix（行=样本 列=特征），可选 groups（分组椭圆±2SD）与 "
           "feature_names（载荷箭头 top5）；默认标准化（相关矩阵），列上限 200。",
    "paired": "paired: 配对前后图；JSON before/after 或 series 恰好两项（等长）；"
              "--stats auto 加配对检验（配对 t / Wilcoxon 符号秩）括号星号。",
    "venn": "venn: 韦恩图（2~4 集合；4 集合为椭圆布局 v2.8）；JSON sets 为元素列表（自动求交并）或全部区域计数；"
            "默认等圆示意、区域数字精确；--area 按计数比例绘制（Euler，2 集合解析解/"
            "3 集合最优拟合）。",
    "cluster_heatmap": "cluster_heatmap: 聚类热图；数据格式同 heatmap（matrix），行列按 Ward 层次"
                       "聚类重排（顺序写入 stderr/alt）；行数上限 3000；v2.3 暂不含树状图面板。",
}


def cmd_list_themes():
    """Print all themes with ANSI color swatches."""
    for t in THEME_ORDER:
        desc = THEME_SWATCH_DESCRIPTIONS.get(t, "")
        colors = THEMES[t]["colors"]
        blocks = "".join(f"\x1b[48;2;{int(c[1:3],16)};{int(c[3:5],16)};{int(c[5:7],16)}m  \x1b[0m"
                         for c in colors)
        safe = "色盲安全" if THEMES[t].get("colorblind_safe") else ""
        print(f"  {t:<14} {blocks}  {desc} {safe}")
    print("\n用法: --theme <name>   别名: okabe→okabe-ito, colorblind→okabe-ito, classic/default→glm")


def cmd_theme_swatch(theme_key, out):
    """Render a swatch preview PNG for a theme."""
    t = THEMES[theme_key]
    colors = t["colors"]
    n = len(colors)
    import matplotlib.patches as mpatches
    fig, ax = plt.subplots(figsize=(max(6, n * 0.75), 2.2))
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, c in enumerate(colors):
        rect = mpatches.Rectangle((i + 0.1, 0.15), 0.8, 0.55, facecolor=c,
                                  edgecolor='black', linewidth=0.5)
        ax.add_patch(rect)
        ax.text(i + 0.5, 0.85, c, ha='center', va='bottom', fontsize=8)
    fig.suptitle(f"Theme: {theme_key}  ({n} colors)"
                 + ("  ·  colorblind-safe" if t.get("colorblind_safe") else ""),
                 fontsize=11, fontweight='bold')
    fig.savefig(out, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Swatch saved: {out}", file=sys.stderr)


DEMO_DATA = {
    "bar": {"labels": ["TNF抑制剂", "IL-6抑制剂", "JAK抑制剂", "IL-1抑制剂", "CTLA-4融合"],
            "series": {"应答率(%)": [62, 55, 48, 40, 35], "缓解率(%)": [28, 22, 20, 15, 10]}},
    "hbar": {"labels": ["TNF抑制剂", "IL-6抑制剂", "JAK抑制剂", "IL-1抑制剂", "CTLA-4融合"],
             "series": {"ACR50应答率(%)": [62, 55, 48, 40, 35]}},
    "stacked_bar": {"labels": ["队列A", "队列B", "队列C"],
                    "series": {"缓解": [45, 38, 30], "部分缓解": [25, 30, 28], "无缓解": [30, 32, 42]},
                    "percentage": True},
    "heatmap": {"rows": ["IL-6", "TNF-α", "CRP", "ESR"],
                "cols": ["IL-6", "TNF-α", "CRP", "ESR"],
                "matrix": [[1.0, 0.72, 0.85, 0.68], [0.72, 1.0, 0.65, 0.60],
                           [0.85, 0.65, 1.0, 0.75], [0.68, 0.60, 0.75, 1.0]]},
    "line": {"labels": ["0周", "4周", "8周", "12周", "16周"],
             "series": {"TNF抑制剂": [5.8, 4.2, 3.5, 3.0, 2.6], "联合治疗": [5.9, 3.8, 2.8, 2.2, 1.8]}},
    "scatter": {"x": [2, 4, 8, 12, 16, 20, 24, 28],
                "y": [45, 38, 28, 22, 18, 15, 12, 10],
                "groups": ["应答者", "应答者", "应答者", "应答者",
                           "非应答者", "非应答者", "非应答者", "非应答者"]},
    "forest": {"labels": ["Smith 2023", "Tanaka 2023", "Brown 2022", "王明 2024"],
               "estimates": [0.72, 0.80, 0.75, 0.65],
               "ci_low": [0.55, 0.62, 0.56, 0.48],
               "ci_high": [0.94, 1.03, 1.00, 0.84],
               "overall": {"estimate": 0.73, "ci_low": 0.60, "ci_high": 0.88}},
    "km": {"groups": {"治疗组": [[0, 1.0], [6, 0.8], [12, 0.7], [18, 0.6], [24, 0.55]],
                      "对照组": [[0, 1.0], [6, 0.9], [12, 0.75], [18, 0.6], [24, 0.45]]},
           "log_rank": {"p": 0.03}},
    "roc": {"curves": [{"fpr": [0.0, 0.1, 0.2, 0.4, 0.6, 1.0],
                        "tpr": [0.0, 0.6, 0.8, 0.9, 0.95, 1.0],
                        "label": "模型A", "auc": 0.92},
                       {"fpr": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                        "tpr": [0.0, 0.4, 0.6, 0.75, 0.85, 1.0],
                        "label": "模型B", "auc": 0.85}]},
    "violin": {"datasets": {"组A": [1.2, 2.3, 2.1, 3.0, 2.8, 3.5], "组B": [2.0, 2.4, 3.1, 3.8, 4.2, 4.0],
                            "组C": [3.0, 3.2, 3.8, 4.5, 4.8, 5.2]}},
    "box": {"datasets": {"组A": [1.2, 2.3, 2.1, 3.0, 2.8, 3.5], "组B": [2.0, 2.4, 3.1, 3.8, 4.2, 4.0]}},
    "dual_axis": {"labels": ["0周", "4周", "8周", "12周"],
                  "left": {"DAS28": [5.8, 4.2, 3.5, 3.0]},
                  "right": {"CRP(mg/L)": [42, 30, 22, 16]}},
    "prisma": {"records_identified": 128, "duplicates_removed": 23, "records_excluded": 61,
               "reports_not_retrieved": 3,
               "exclusion_reasons": {"人群不符": 5, "干预不符": 7, "数据不可用": 4},
               "studies_included": 25},
}


def cmd_demo(args):
    """Interactive demo: menu of chart types, renders with sample data, prints the command used."""
    print("Academic Figures 交互演示 (v2.0+)\n选择图表类型:")
    types = [k for k in DEMO_DATA.keys() if k in GENERATORS]
    for i, t in enumerate(types, 1):
        print(f"  [{i}] {t}")
    sel = input(f"输入序号 (1-{len(types)}, 回车=1): ").strip() or "1"
    try:
        chart_type = types[int(sel) - 1]
    except (ValueError, IndexError):
        print("无效输入，使用 bar", file=sys.stderr)
        chart_type = "bar"
    import tempfile, json as _json
    tmpdir = tempfile.mkdtemp(prefix="af_demo_")
    data_path = os.path.join(tmpdir, "data.json")
    out_path = os.path.join(tmpdir, f"{chart_type}.png")
    with open(data_path, "w", encoding="utf-8") as f:
        _json.dump(DEMO_DATA[chart_type], f, ensure_ascii=False)
    cmd = (f"python3 scripts/gen_figure.py -t {chart_type} -d '{data_path}' -o '{out_path}' "
           f"--theme {args.theme or 'glm'}")
    print(f"\n执行: {cmd}", file=sys.stderr)
    args.type, args.data, args.out = chart_type, data_path, out_path
    return True


def cmd_explain(chart_type):
    """Print usage notes for a chart type."""
    if chart_type not in GENERATORS:
        print(f"未知图表类型: {chart_type}", file=sys.stderr)
        print(f"可用: {', '.join(GENERATORS.keys())}", file=sys.stderr)
        sys.exit(1)
    print(f"[{chart_type}]")
    print(CHART_NOTES.get(chart_type, "参考文档相应章节。"))


# ── Chart-type suggestion (v2.1) ──────────────────────────────────────

def suggest_chart_type(data):
    """Heuristic chart-type recommendation from a loaded data dict.

    Returns [(score, chart_type, reason)] sorted best-first. Purely
    structural (no rendering) so it is safe to call on any input.
    """
    if not isinstance(data, dict):
        return []
    recs = []
    keys = set(data.keys())
    if "records_identified" in keys or "studies_included" in keys:
        recs.append((98, "prisma", "PRISMA flow fields (records_identified / studies_included)"))
    if "blocks" in keys and "arrows" in keys:
        recs.append((96, "diagram", "blocks + arrows structure"))
    if "panels" in keys:
        recs.append((92, "composite", "multi-panel 'panels' definition"))
    curves = data.get("curves")
    if isinstance(curves, list) and curves and isinstance(curves[0], dict) \
            and {"fpr", "tpr"} <= set(curves[0]):
        recs.append((95, "roc", "curves[] with fpr/tpr arrays"))
    groups = data.get("groups")
    if isinstance(groups, dict) and groups:
        first = next(iter(groups.values()), None)
        if isinstance(first, list) and first and isinstance(first[0], (list, tuple)) \
                and len(first[0]) == 2:
            recs.append((94, "km", "groups mapped to [time, survival] step pairs"))
    if {"estimates", "ci_low", "ci_high"} <= keys:
        recs.append((93, "forest", "effect estimates with CI bounds"))
    if isinstance(data.get("matrix"), list):
        recs.append((88, "heatmap", "2D 'matrix'"))
    if {"left", "right"} <= keys:
        recs.append((86, "dual_axis", "left + right series for dual Y-axis"))
    if isinstance(data.get("datasets"), dict) and data["datasets"]:
        recs.append((72, "violin", "raw per-group 'datasets' — distribution view"))
        recs.append((70, "box", "raw per-group 'datasets' — boxplot view"))
    x, y = data.get("x"), data.get("y")
    if isinstance(x, list) and isinstance(y, list) and x and len(x) == len(y):
        recs.append((80, "scatter", "paired x/y arrays"))
    series = data.get("series")
    if isinstance(series, dict) and series:
        lists = [v for v in series.values() if isinstance(v, list)]
        if lists and all(len(v) == 1 for v in lists):
            recs.append((68, "bar", "single-value series"))
        else:
            recs.append((76, "bar", "labels + named series"))
    return sorted(recs, key=lambda r: (-r[0], r[1]))


def cmd_suggest(data_path):
    """Analyze a data file and print recommended chart types + a ready-to-run command."""
    try:
        data = load_data(data_path)
    except Exception as e:
        print(f"ERROR: cannot load '{data_path}': {e}", file=sys.stderr)
        sys.exit(1)
    recs = suggest_chart_type(data)
    if not recs:
        print("No confident match — default to bar (labels + series). See --explain <type>.")
        return
    print("Suggested chart types (best first):")
    for i, (score, ctype, why) in enumerate(recs[:3], 1):
        print(f"  [{i}] {ctype:<12} score {score:<3} — {why}")
    best = recs[0][1]
    print(f"\nRun: python3 scripts/gen_figure.py -t {best} -d '{data_path}' -o out.pdf "
          f"--theme okabe-ito --verify")

# ── Journal presets (v2.0) ─────────────────────────────────────────────
# Column widths from Nature/Lancet author guidelines: single 89/85mm, double 183mm.
JOURNAL_PRESETS = {
    "nature": {"widths_mm": {"single": 89, "double": 183},
               "font_size": 7, "min_text_size": 5, "font_family": "Helvetica", "dpi": 600},
    "lancet": {"widths_mm": {"single": 85, "double": 183},
               "font_size": 8, "min_text_size": 6, "font_family": "Arial", "dpi": 600},
    # v2.2 international expansion — widths/min sizes follow each journal's
    # published author guidelines (commonly cited values); re-check the latest
    # guide before submission.
    "science": {"widths_mm": {"single": 55, "double": 120},
                "font_size": 7, "min_text_size": 5, "font_family": "Helvetica", "dpi": 600},
    "cell": {"widths_mm": {"single": 85, "double": 176},
             "font_size": 8, "min_text_size": 6, "font_family": "Arial", "dpi": 300},
    "nejm": {"widths_mm": {"single": 89, "double": 190},
             "font_size": 8, "min_text_size": 6, "font_family": "Helvetica", "dpi": 300},
    "jama": {"widths_mm": {"single": 89, "double": 183},
             "font_size": 8, "min_text_size": 6, "font_family": "Arial", "dpi": 600},
    "ieee": {"widths_mm": {"single": 89, "double": 181},
             "font_size": 8, "min_text_size": 6, "font_family": "Times New Roman", "dpi": 600},
    # Chinese presets — CJK font auto-enabled (cjk_default)
    "cma": {"widths_mm": {"single": 80, "double": 170},
            "font_size": 8, "min_text_size": 6, "font_family": "Arial", "dpi": 600,
            "cjk_default": True},
    "cn-core": {"widths_mm": {"single": 80, "double": 170},
                "font_size": 9, "min_text_size": 6, "font_family": "Arial", "dpi": 300,
                "cjk_default": True},
}

def _memory_hint(data, chart_type):
    """A3(v2.7)：渲染前对超大数据规模给中文提示（防内存型失败；只提醒不拦截）。"""
    try:
        n = 0
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    n += len(v)
                    n += sum(len(x) for x in v if isinstance(x, (list, tuple)))
                elif isinstance(v, dict):
                    for vv in v.values():
                        n += len(vv) if isinstance(vv, list) else 1
                elif isinstance(v, (int, float)):
                    n += 1
            if isinstance(data.get("matrix"), list):
                n = sum(len(r) for r in data["matrix"] if isinstance(r, list))
        if n > 1_000_000:
            print(f"提示：数据规模约 {n} 个数值点，内存占用较大。热图/聚类建议先按行聚合；"
                  "散点建议等距抽样到 1 万点内；也可降低 --dpi。", file=sys.stderr)
    except Exception:
        pass


def _load_journal_presets(base_dir=None):
    """A4(v2.7)：scripts/journal/*.json 为期刊预设唯一权威源（免费版=拍板基准）。
    目录缺失/单文件损坏时按刊回退内置值（离线与旧包永不受损）。"""
    import glob as _glob
    d = os.path.join(base_dir or os.path.dirname(os.path.abspath(__file__)), "journal")
    out = {}
    if os.path.isdir(d):
        for p in sorted(_glob.glob(os.path.join(d, "*.json"))):
            name = os.path.splitext(os.path.basename(p))[0]
            try:
                with open(p, encoding="utf-8") as fh:
                    spec = json.load(fh)
                for k in ("widths_mm", "font_size", "dpi"):
                    if k not in spec:
                        raise KeyError(f"缺少 {k}")
                out[name] = spec
            except Exception as exc:
                print(f"WARNING: 期刊预设 {os.path.basename(p)} 加载失败（{exc}），回退内置值",
                      file=sys.stderr)
    for k, v in _JOURNAL_BUILTIN.items():
        out.setdefault(k, v)
    return out


_JOURNAL_BUILTIN = {k: dict(v) for k, v in JOURNAL_PRESETS.items()}
JOURNAL_PRESETS = _load_journal_presets()

# v2.5：期刊预设 → 配色主题联动（用户显式给 --theme 时不覆盖）
JOURNAL_THEME = {"nature": "nature", "lancet": "lancet",
                 "nejm": "nejm", "science": "science"}

# Hatching patterns for bar charts (print-friendly + accessibility)
# ALL series get hatching when --hatch is enabled (including the first).
# Each series cycles through a different pattern so they're distinguishable
# even in black-and-white print. Hatch line color = black (edgecolor='black').
HATCH_PATTERNS = ['//', '\\\\', '||', '--', '++', 'xx', '..', 'oo', '**', 'oo']

def _darken_color(color, factor=0.55):
    """Return a darker shade of the given color. (Legacy; hatch now uses black.)"""
    import matplotlib.colors as mcolors
    try:
        rgb = mcolors.to_rgb(color)
        return tuple(c * factor for c in rgb)
    except Exception:
        return (0.2, 0.2, 0.2)


# ── Auto significance annotations (v2.2) ──────────────────────────────

def _sig_stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "NS"


def pairwise_vs_first(series):
    """Compare each series against the first one: Shapiro normality test,
    then Welch t-test (both normal) or Mann-Whitney U (otherwise).
    Returns [(name, p_or_None, stars, method)]. Requires scipy."""
    from scipy import stats as _st
    names = list(series.keys())
    if len(names) < 2:
        return []
    ref_all = np.asarray(series[names[0]], dtype=float)
    ref_all = ref_all[np.isfinite(ref_all)]
    out = []
    for name in names[1:]:
        vals = np.asarray(series[name], dtype=float)
        vals = vals[np.isfinite(vals)]
        if len(vals) < 3 or len(ref_all) < 3:
            out.append((name, None, "n.s.", "n<3"))
            continue
        normal = True
        for arr in (ref_all, vals):
            if 3 <= len(arr) <= 5000:
                _, sp = _st.shapiro(arr)
                if sp <= 0.05:
                    normal = False
                    break
        if normal:
            _, p = _st.ttest_ind(ref_all, vals, equal_var=False)
            method = "Welch t"
        else:
            _, p = _st.mannwhitneyu(ref_all, vals, alternative="two-sided")
            method = "Mann-Whitney U"
        out.append((name, float(p), _sig_stars(float(p)), method))
    return out


def draw_stat_brackets(ax, positions, results, data_top, font_size=8):
    """Draw one comparison bracket per result (each group vs group 0), stacked
    above the tallest data point. Returns the new suggested ylim top."""
    span = max(abs(data_top) * 0.08, 1e-9)
    for j, (name, p, stars, method) in enumerate(results):
        if p is None:
            continue
        yi = data_top + span * (0.55 + 1.05 * j)
        x0, x1 = positions[0], positions[j + 1]
        ax.plot([x0, x0, x1, x1],
                [yi - span * 0.22, yi, yi, yi - span * 0.22],
                color="#333333", lw=1.2, zorder=6)
        ax.text((x0 + x1) / 2, yi + span * 0.10, stars, ha="center",
                va="bottom", fontsize=font_size, color="#333333", zorder=6)
    return data_top + span * (0.55 + 1.05 * max(0, len(results) - 1)) + span * 0.6


def annotate_auto_stats(ax, series, positions, theme, chart_type):
    """--stats auto entry point for box/violin: compute + draw + report."""
    names = list(series.keys())
    if len(names) < 2:
        print(f"WARNING: --stats auto needs >= 2 series ({chart_type}); skipped",
              file=sys.stderr)
        return
    try:
        results = pairwise_vs_first(series)
    except ImportError:
        print("WARNING: --stats auto requires scipy — install with: pip install scipy",
              file=sys.stderr)
        return
    data_top = max(max([float(v) for v in vals]) for vals in series.values() if len(vals))
    top = draw_stat_brackets(ax, positions, results, data_top,
                             font_size=max(6, theme["font_size"]))
    lo, hi = ax.get_ylim()
    if top > hi:
        ax.set_ylim(lo, top)
    g0 = names[0]
    for name, p, stars, method in results:
        p_txt = "NA" if p is None else f"{p:.4g}"
        print(f"  stats ({chart_type}): {g0} vs {name}: {method}, p={p_txt} -> {stars}",
              file=sys.stderr)


def annotate_multi_stats(ax, series, positions, theme, chart_type):
    """--stats multi 入口：全两两比较（正态→Tukey；否则 Kruskal-Wallis+Dunn+Hochberg）。"""
    if _afstats is None:
        print("WARNING: --stats multi 需要 af_v23_stats.py 与 gen_figure.py 同目录",
              file=sys.stderr)
        return
    names = list(series.keys())
    if len(names) < 3:
        print("WARNING: --stats multi 需要 >=3 组（两组比较请用 --stats auto）",
              file=sys.stderr)
        return
    clean = {}
    for n, v in series.items():
        arr = np.asarray(v, dtype=float)
        clean[n] = arr[np.isfinite(arr)]
    try:
        pairs = _afstats.multi_pairwise(clean)
    except ValueError as e:
        print(f"WARNING: --stats multi 无法计算：{e}", file=sys.stderr)
        return
    data_top = max(max([float(x) for x in v]) for v in clean.values() if len(v))
    span = max(abs(data_top) * 0.08, 1e-9)
    sig = [t for t in pairs if t[2] is not None]
    if len(sig) > 8:
        print(f"WARNING: 显著对比 {len(sig)} 对，仅绘制前 8 对括号（完整结果见 stderr 报告）",
              file=sys.stderr)
    top_needed = data_top
    for idx, (a_name, b_name, p, stars, method) in enumerate(sig[:8]):
        yi = data_top + span * (0.55 + 1.05 * idx)
        x0 = positions[names.index(a_name)]
        x1 = positions[names.index(b_name)]
        ax.plot([x0, x0, x1, x1],
                [yi - span * 0.22, yi, yi, yi - span * 0.22],
                color="#333333", lw=1.2, zorder=6)
        ax.text((x0 + x1) / 2, yi + span * 0.10, stars, ha="center",
                va="bottom", fontsize=max(6, theme["font_size"]), color="#333333", zorder=6)
        top_needed = yi + span * 0.6
    lo, hi = ax.get_ylim()
    if top_needed > hi:
        ax.set_ylim(lo, top_needed)
    for a_name, b_name, p, stars, method in pairs:
        print(f"  stats ({chart_type}): {a_name} vs {b_name}: {method}, p={p:.4g} -> {stars}",
              file=sys.stderr)


# ── Alt text generation (v2.2, accessibility) ─────────────────────────

def _alt_num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def generate_alt_text(chart_type, data, title=""):
    """One-paragraph accessibility description derived from the data dict.
    Written to <output>.alt.txt with --alt."""
    if _afcharts is not None and chart_type in _afcharts.EXTRA_GENERATORS:
        return _afcharts.alt_extra(chart_type, data, title)
    t = f"{title}。" if title else ""

    def _max_txt(vals):
        fv = [_alt_num(v) for v in vals if isinstance(vals, list)]
        fv = [v for v in fv if v is not None]
        return f"{max(fv):g}" if fv else "?"

    if chart_type in ("bar", "grouped_bar", "hbar", "horizontal_bar"):
        series = data.get("series", {})
        labels = data.get("labels", [])
        parts = []
        for name, vals in series.items():
            fv = [v for v in (_alt_num(x) for x in vals) if v is not None]
            if fv:
                parts.append(f"{name} 最大值 {max(fv):g}")
        return (f"柱状图。{t}共 {len(labels)} 组：{'、'.join(map(str, labels))}。"
                f"{'；'.join(parts)}。")
    if chart_type in ("box", "boxplot", "violin"):
        series = data.get("series", {})
        segs = []
        for name, vals in series.items():
            fv = sorted(v for v in (_alt_num(x) for x in vals) if v is not None)
            if fv:
                segs.append(f"{name}：中位数 {fv[len(fv)//2]:g}（n={len(fv)}）")
        kind = "箱线图" if chart_type in ("box", "boxplot") else "小提琴图"
        return f"{kind}。{t}{'；'.join(segs)}。"
    if chart_type in ("km", "survival"):
        groups = data.get("groups", {})
        lr = data.get("log_rank") or {}
        tail = f"Log-rank p = {lr.get('p')}。" if lr.get("p") is not None else ""
        return (f"Kaplan-Meier 生存曲线。{t}分组：{'、'.join(groups.keys())}。{tail}")
    if chart_type == "roc":
        curves = data.get("curves", [])
        names = "；".join(f"{c.get('name', 'curve')} AUC {c.get('auc', '?')}"
                          for c in curves)
        return f"ROC 曲线。{t}{names}。"
    if chart_type == "forest":
        o = data.get("overall") or {}
        o_txt = (f"合并效应 {o.get('estimate')}（95%CI {o.get('ci_low')}–{o.get('ci_high')}）。"
                 if o else "")
        return f"森林图，{len(data.get('labels', []))} 项研究。{t}{o_txt}"
    if chart_type == "heatmap":
        m = data.get("matrix", [])
        cols = len(m[0]) if m else 0
        return f"热图，{len(m)} 行 × {cols} 列。{t}"
    if chart_type == "prisma":
        return (f"PRISMA 2020 系统综述流程图：最初识别 "
                f"{data.get('records_identified')} 条记录，最终纳入 "
                f"{data.get('studies_included')} 项研究。{t}")
    if chart_type == "composite":
        panels = data.get("panels", [])
        names = "、".join(str(p.get("title", "")) for p in panels)
        return f"多面板组合图，{len(panels)} 个面板：{names}。{t}"
    if chart_type == "line":
        series = data.get("series", {})
        n_pts = len(next(iter(series.values()), []))
        return f"折线图，{len(series)} 条系列 × {n_pts} 个数据点。{t}"
    if chart_type == "scatter":
        return f"散点图，共 {len(data.get('x', []))} 个数据点。{t}"
    if chart_type == "dual_axis":
        return f"双 Y 轴折线图。{t}"
    if chart_type == "diagram":
        return f"流程图。{t}"
    return f"{chart_type} 图。{t}"

# ── Font helpers ───────────────────────────────────────────────────────

def load_cjk_font(font_path=None):
    """Load CJK font. Returns (FontProperties, font_name) or (None, None)."""
    if font_path is None:
        # Auto-detect
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, DETECT_SCRIPT],
                capture_output=True, text=True, timeout=10
            )
            info = json.loads(result.stdout)
            font_path = info.get("path") if info.get("found") else None
        except Exception:
            font_path = None
    if font_path and os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        fp = fm.FontProperties(fname=font_path)
        # Extract family name for rcParams
        return fp, fp.get_name()
    return None, None


def has_cjk(text):
    """Check if text contains CJK characters (incl. supplementary-plane ideographs)."""
    if not text:
        return False
    for ch in str(text):
        o = ord(ch)
        if 0x4e00 <= o <= 0x9fff or 0x3400 <= o <= 0x4dbf:  # BMP: CJK Unified + Ext-A
            return True
        if 0x3000 <= o <= 0x303f or 0xff00 <= o <= 0xffef:  # CJK 标点 + 全角形式（（）：等）
            return True
        if 0x20000 <= o <= 0x2ebef:  # Ext-B..F (rare, but real ideographs)
            return True
        if 0x30000 <= o <= 0x3134f:  # Ext-G
            return True
    return False


def safe_text(ax, text, fontprop=None, **kwargs):
    """Set text with CJK font if needed."""
    if fontprop and has_cjk(str(text)):
        return ax.set_text(text) if hasattr(ax, 'set_text') else ax.text(text, fontproperties=fontprop, **kwargs)
    return ax.set_text(text) if hasattr(ax, 'set_text') else ax.text(text, **kwargs)


# ── Overlap prevention (mechanism-level) ───────────────────────────────

MIN_TICK_GAP = 6.0


def _boxes_overlap(b1, b2, ratio=0.04):
    """True if intersection area exceeds `ratio` of the smaller box."""
    inter = BboxBase.intersection(b1, b2)
    if inter is None or inter.width <= 0 or inter.height <= 0:
        return False
    inter_area = inter.width * inter.height
    return inter_area > ratio * min(b1.width * b1.height, b2.width * b2.height, 1)


def _adjacent_too_close(b1, b2, axis, min_gap=MIN_TICK_GAP):
    """True if two same-axis neighbor boxes touch or leave < min_gap px.

    Order-agnostic: tick-label order follows axis direction, which is
    inverted (top-to-bottom) on heatmap/forest/km axes. The gap is computed
    as the distance between the two boxes along the axis regardless of
    which one comes first in the list.
    """
    inter = BboxBase.intersection(b1, b2)
    if inter is not None and inter.width > 0 and inter.height > 0:
        return True
    if axis == 'x':
        gap = b2.x0 - b1.x1 if b2.x0 >= b1.x0 else b1.x0 - b2.x1
    else:
        gap = b1.y0 - b2.y1 if b1.y0 >= b2.y0 else b2.y0 - b1.y1
    return gap < min_gap


def _tick_boxes(ax, renderer):
    """Return (x_labels, y_labels, x_boxes, y_boxes) for visible tick labels."""
    xl, yl, xb, yb = [], [], [], []
    for lab in ax.get_xticklabels():
        if lab.get_text().strip() and lab.get_visible():
            xl.append(lab)
            xb.append(lab.get_window_extent(renderer))
    for lab in ax.get_yticklabels():
        if lab.get_text().strip() and lab.get_visible():
            yl.append(lab)
            yb.append(lab.get_window_extent(renderer))
    return xl, yl, xb, yb


def _ensure_ylabel_clear(ax, fig=None, max_pad=24.0):
    """Mechanism-level: auto-increase y-label labelpad until it clears tick labels.

    Rotated (90°) y-axis titles -- especially long CJK+English mixes like
    "最高研发阶段 (max phase)" -- can collide with the top/bottom tick labels
    even when tick-vs-tick overlaps are handled. Measures real rendered
    bounding boxes; only grows the pad when a collision exists, so figures
    that already look right are left untouched.
    """
    fig = fig or ax.figure
    label = ax.yaxis.get_label()
    if not label.get_text().strip():
        return
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_bb = label.get_window_extent(renderer)
    tick_bbs = [t.get_window_extent(renderer) for t in ax.get_yticklabels()
                if t.get_text().strip() and t.get_visible()]
    if not tick_bbs:
        return
    cur = ax.yaxis.labelpad

    def collides():
        for tb in tick_bbs:
            inter = BboxBase.intersection(label_bb, tb)
            if inter is not None and inter.width > 0 and inter.height > 0:
                return True
        return False

    while collides() and cur <= max_pad:
        cur += 1.0
        ax.yaxis.labelpad = cur
        fig.canvas.draw()
        label_bb = label.get_window_extent(renderer)
    if collides():
        # Pad exhausted: shrink the label font as a last resort.
        label.set_fontsize(max(5, label.get_fontsize() - 1))
        fig.canvas.draw()
        print(f"WARNING: y-label '{label.get_text()[:20]}...' still near ticks "
              f"after pad={cur:.0f}, font shrunk", file=sys.stderr)


def _axis_has_overlap(xb, yb):
    """Check adjacent x-x, adjacent y-y (with min-gap), and x-y collisions."""
    for i in range(len(xb) - 1):
        if _boxes_overlap(xb[i], xb[i + 1]) or _adjacent_too_close(xb[i], xb[i + 1], 'x'):
            return True
    for i in range(len(yb) - 1):
        if _boxes_overlap(yb[i], yb[i + 1]) or _adjacent_too_close(yb[i], yb[i + 1], 'y'):
            return True
    for bx in xb:
        for by in yb:
            if _boxes_overlap(bx, by):
                return True
    return False


def _degrade_axis(ax, axis, level):
    """Apply one degradation step to tick labels. Returns True if applied.

    Ladder: 1 rotate 45° → 2 word-wrap → 3 shrink font → 4 rotate 90° →
    ≥5 stride-thinning. Labels are data: 90° rotation is always tried
    before any label is hidden, and every hidden label is reported by
    fix_tick_overlaps() so the data loss is never silent.
    """
    labels = ax.get_xticklabels() if axis == 'x' else ax.get_yticklabels()
    labels = [l for l in labels if l.get_text().strip()]
    if not labels:
        return False
    if level == 1 and axis == 'x':
        if all(l.get_rotation() == 45 for l in labels):
            return False
        for l in labels:
            l.set_rotation(45)
            l.set_ha('right')
        return True
    if level == 2 and axis == 'x':
        wrapped = False
        for l in labels:
            if ' ' in l.get_text() and '\n' not in l.get_text():
                l.set_text('\n'.join(l.get_text().split(' ')))
                wrapped = True
        return wrapped
    if level == 3:
        sizes = {l.get_fontsize() for l in labels}
        if all(s <= 5 for s in sizes):
            return False
        for l in labels:
            l.set_fontsize(max(5, l.get_fontsize() - 1))
        return True
    if level == 4 and axis == 'x':
        if all(l.get_rotation() == 90 for l in labels):
            return False
        for l in labels:
            l.set_rotation(90)
            l.set_ha('center')
        return True
    if level >= 5:
        stride = 2 ** (level - 4)
        hid = False
        for i, l in enumerate(labels):
            if i % stride != 0 and l.get_visible():
                l.set_visible(False)
                hid = True
        return hid
    return False


def fix_tick_overlaps(fig):
    """Post-render collision detection + auto-degradation ladder.

    Draws the figure, measures real tick-label bounding boxes, and applies
    rotation 45° → word-wrap → font-shrink → rotation 90° → stride-thinning
    until no axis (including composite panels) has overlapping labels.
    Stride-thinning hides labels (data loss) only after geometric fixes are
    exhausted, and prints a stderr warning whenever it fires.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for _pass in range(8):
        fixed_any = False
        for ax in fig.axes:
            if getattr(ax, "_af_category_axis", False):
                continue  # 热图家族：行列标签即数据，禁止降级抽稀（机制豁免）
            xl, yl, xb, yb = _tick_boxes(ax, renderer)
            if not _axis_has_overlap(xb, yb):
                continue
            for level in range(1, 11):
                if not _axis_has_overlap(xb, yb):
                    break
                if level in (1, 2, 4) and not xl:
                    continue
                applied = _degrade_axis(ax, 'x', level)
                if not applied and level >= 3:
                    applied = _degrade_axis(ax, 'y', level)
                if applied:
                    fixed_any = True
                    fig.canvas.draw()
                    renderer = fig.canvas.get_renderer()
                    xl, yl, xb, yb = _tick_boxes(ax, renderer)
        if not fixed_any:
            break

    hidden = sum(1 for ax in fig.axes
                 for l in ax.get_xticklabels() + ax.get_yticklabels()
                 if l.get_text().strip() and not l.get_visible())
    if hidden:
        print(f"academic-figures WARNING: hid {hidden} tick label(s) to resolve "
              f"overlap — hidden labels are lost data; increase --width/--height "
              f"or shorten labels", file=sys.stderr)


def place_annotation(ax, text, xy, fontsize=9.5, fontweight='bold', color='black', ha='center'):
    """Place an annotation, testing candidate offsets against existing text
    boxes (greedy collision avoidance). Returns the placed Text artist."""
    fig = ax.figure
    candidates = [(0, 14), (0, -24), (16, 0), (-16, 0), (0, 32), (0, -42),
                  (30, 14), (-30, 14), (30, -24), (-30, -24), (30, 32), (-30, -42)]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    placed = [t.get_window_extent(renderer) for t in ax.texts if t.get_text().strip()]
    for dx, dy in candidates:
        t = ax.annotate(text, xy=xy, xytext=(dx, dy), textcoords='offset points',
                        ha=ha, va='center', fontsize=fontsize, fontweight=fontweight, color=color)
        fig.canvas.draw()
        bb = t.get_window_extent(renderer)
        if not any(_boxes_overlap(bb, pb) for pb in placed):
            return t
        t.remove()
    return ax.annotate(text, xy=xy, xytext=(0, 14), textcoords='offset points',
                       ha=ha, va='center', fontsize=fontsize, fontweight=fontweight, color=color)


# ── Data loading ───────────────────────────────────────────────────────

def _is_number(s):
    """Check if string represents a number."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _read_excel(path, sheet=None):
    """Read an Excel sheet into (headers, rows-of-str) — the same shape the
    CSV branch of load_data() consumes. First non-empty row is the header."""
    try:
        import openpyxl
    except ImportError:
        raise ValueError(
            "xlsx requires openpyxl — install with: pip install openpyxl "
            "(or export the sheet to CSV)")
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(
            f"cannot read {os.path.basename(path)} as Excel (.xlsx): {e} — "
            f"if the file is CSV/TSV, rename it to .csv")
    try:
        if sheet and sheet not in wb.sheetnames:
            raise ValueError(f"sheet '{sheet}' not found in {os.path.basename(path)} — "
                             f"available: {wb.sheetnames}")
        ws = wb[sheet] if sheet else wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    rows_raw = [r for r in rows_raw
                if any(v is not None and str(v).strip() != "" for v in r)]
    if not rows_raw:
        raise ValueError(f"sheet is empty: {os.path.basename(path)}")
    headers = ["" if v is None else str(v).strip() for v in rows_raw[0]]
    rows = [[("" if v is None else str(v).strip()) for v in r]
            for r in rows_raw[1:]]
    return headers, rows


def load_data(path, chart_type=None, sheet=None):
    """Load data from JSON, CSV or Excel (.xlsx/.xls). Returns dict with structure info.

    For CSV/Excel, chart_type is used to auto-convert long-format data:
    - scatter: first two numeric cols → {x, y}, third col → groups
    - box/violin: first col as groups, second numeric col as values → {series: {group: [values]}}
    - sheet: Excel only — sheet name (default: first/active sheet)
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif ext in ('.csv', '.tsv', '.xlsx', '.xls'):
        if ext in ('.csv', '.tsv'):
            delimiter = '\t' if ext == '.tsv' else ','
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader)
                rows = list(reader)
        else:
            headers, rows = _read_excel(path, sheet)
        # Build series, skipping non-numeric columns (C1 fix)
        # Identify numeric columns: >50% of values must be parseable as numbers
        numeric_col_indices = []
        for i, h in enumerate(headers):
            if i == 0:
                continue
            num_count = sum(1 for r in rows if i < len(r) and _is_number(r[i]))
            if num_count > len(rows) * 0.5:
                numeric_col_indices.append(i)

        # Collect all rows with non-numeric values across numeric columns (union)
        bad_rows = set()
        for i in numeric_col_indices:
            for ri, r in enumerate(rows):
                if ri < len(r) and not _is_number(r[i]):
                    bad_rows.add(ri)

        # Build series using only valid rows
        good_rows = [ri for ri in range(len(rows)) if ri not in bad_rows]
        series = {}
        for i in numeric_col_indices:
            vals = [float(rows[ri][i]) for ri in good_rows if ri < len(rows)]
            if vals:
                series[headers[i]] = vals

        # Sync labels with valid rows
        labels = [rows[ri][0] for ri in good_rows if ri < len(rows)]
        result = {"labels": labels, "series": series}

        # Long-format conversion for scatter (C1 real fix)
        if chart_type == 'scatter' and series:
            # Collect ALL numeric columns including index 0 if numeric header
            all_numeric = []
            for i, h in enumerate(headers):
                num_count = sum(1 for ri in good_rows if ri < len(rows) and _is_number(rows[ri][i]))
                if num_count > len(good_rows) * 0.5:
                    all_numeric.append((i, h))

            if len(all_numeric) >= 2:
                col_i, col_x_name = all_numeric[0]
                col_j, col_y_name = all_numeric[1]
                x_vals = [float(rows[ri][col_i]) for ri in good_rows if ri < len(rows) and col_i < len(rows[ri])]
                y_vals = [float(rows[ri][col_j]) for ri in good_rows if ri < len(rows) and col_j < len(rows[ri])]

                groups = None
                # Check remaining columns for groups (non-numeric with multiple unique values)
                if len(all_numeric) >= 3:
                    # Use third numeric column's position to find non-numeric columns
                    pass  # groups will be below
                # Try non-numeric columns for groups — prefer name hint, then fewest unique vals
                _group_hints = {'group', 'groups', 'category', 'categories', 'class', 'label', 'labels', 'type'}
                candidates = []
                for i, h in enumerate(headers):
                    if i in [idx for idx, _ in all_numeric]:
                        continue
                    vals = [rows[ri][i] for ri in good_rows if ri < len(rows)]
                    unique = set(vals)
                    if len(unique) > 1 and len(unique) <= 20:
                        score = (0, len(unique), i)  # (hint_match, unique_count, col_index)
                        if h.lower().strip() in _group_hints:
                            score = (-1, len(unique), i)
                        candidates.append((score, vals, h))
                if candidates:
                    candidates.sort()
                    groups = candidates[0][1]

                result = {"x": x_vals, "y": y_vals}
                if groups:
                    result["groups"] = groups
            elif len(all_numeric) == 1:
                # Only one numeric series from wide format, try using it as y with row index as x
                col_i, col_name = all_numeric[0]
                y_vals = [float(rows[ri][col_i]) for ri in good_rows if ri < len(rows) and col_i < len(rows[ri])]
                # Check if labels (first col) are numeric → use as x
                if labels and all(_is_number(l) for l in labels):
                    result = {"x": [float(l) for l in labels], "y": y_vals}
                else:
                    result = {"x": list(range(len(y_vals))), "y": y_vals, "groups": labels}

        # Long-format conversion for box/violin (C4 real fix)
        if chart_type in ('box', 'boxplot', 'violin') and series:
            first_col_vals = [rows[ri][0] for ri in good_rows if ri < len(rows)]
            unique_groups = list(dict.fromkeys(first_col_vals))  # preserve order
            # Check if first column looks like group labels (many repeats)
            if len(unique_groups) < len(first_col_vals) * 0.8 and len(unique_groups) >= 2:
                # Long format: group column + value column
                num_col_idx = numeric_col_indices[0] if numeric_col_indices else None
                if num_col_idx is not None:
                    grouped = {}
                    for g in unique_groups:
                        grouped[g] = []
                    for ri in good_rows:
                        if ri < len(rows) and num_col_idx < len(rows[ri]):
                            g = rows[ri][0]
                            v = rows[ri][num_col_idx]
                            if _is_number(v):
                                grouped[g].append(float(v))
                    # Only use if groups have multiple values
                    if any(len(v) >= 2 for v in grouped.values()):
                        result = {"labels": unique_groups, "series": grouped}

        return result
    else:
        raise ValueError(f"不支持的数据格式: {ext}。请改用 .json / .csv / .tsv / .xlsx")


# ── Data validation layer (v2.0) ───────────────────────────────────────

def _preflight_advisories(data, chart_type, downsample=None):
    """v2.9：渲染前预判式提示（纯函数，返回中文提示列表）。提前预判，不等硬限报错。"""
    msgs = []
    try:
        if (chart_type == "cluster_heatmap" and isinstance(data, dict)
                and not downsample):
            rows = len(data.get("matrix") or [])
            if rows > 1500:
                msgs.append(
                    f"cluster_heatmap 行数 {rows} 已超过建议值 1500（硬上限 3000）："
                    "聚类更慢、内存更高——建议加 --downsample 2000 等距采样；"
                    "如确需全量渲染可忽略本提示")
    except Exception:
        pass
    return msgs


def _field_nearmiss_warnings(data):
    """v2.9：dict 数据中出现"形似已知字段"的未知键时给中文纠错告警（非致命）。"""
    msgs = []
    try:
        if isinstance(data, dict):
            import difflib as _dif
            for k in data.keys():
                if (not isinstance(k, str) or k.startswith("_")
                        or k in _KNOWN_DATA_FIELDS):
                    continue
                near = _dif.get_close_matches(k, _KNOWN_DATA_FIELDS, n=1, cutoff=0.6)
                if near:
                    msgs.append(
                        f"字段名 '{k}' 不是有效字段——是否想用 '{near[0]}'？"
                        "（大小写与下划线必须完全一致；无法识别的字段会被忽略；"
                        "各图型字段见 --explain）")
    except Exception:
        pass
    return msgs


def validate_data(data, chart_type):
    """Unified data validation: fatal errors + degradation warnings.

    Returns (fatal_msgs, warning_msgs).
    - fatal: figure CANNOT be drawn correctly -> caller must abort (exit code 1)
    - warning: figure can be drawn but data looks suspicious -> caller prints WARNING

    Covers per-type required fields, numeric types, length matching, and
    degenerate-data detection (all-equal series, non-finite values, ragged rows).
    """
    fatal, warns = [], []

    if not isinstance(data, dict):
        fatal.append("数据必须是非空 JSON 对象，或由 CSV 转换来的字典")
        return fatal, warns

    def _nonempty_list(v):
        return isinstance(v, (list, tuple)) and len(v) > 0

    def _len(v):
        return len(v) if isinstance(v, (list, tuple)) else 0

    def _warn_flat(name, vals):
        """Detect all-equal series -> flat chart, usually a data bug."""
        fvals = [float(v) for v in vals if _is_number(v)]
        if len(fvals) >= 2 and max(fvals) == min(fvals):
            warns.append(
                f"系列 '{name}' 的值全部相同（恒为 {fvals[0]:g}）— 图会是一条平线。"
                f"请确认这是数据本意，而不是取错了列")

    def _warn_non_numeric(name, vals):
        n_bad = sum(1 for v in vals if not _is_number(v))
        if n_bad:
            warns.append(
                f"系列 '{name}' 里有 {n_bad} 个非数值项，画图时会跳过 — "
                f"请检查源数据里是否混入了 'NA'、'—' 或文字")

    def _check_series_dict(series, err_key, req_nonempty=True):
        """Validate a {name: [values]} dict. Returns fatal messages list."""
        msgs = []
        if not isinstance(series, dict):
            msgs.append(f"'{err_key}' 必须是 JSON 对象（形如 {{\"系列名\": [数值, ...]}}）— 当前类型不符")
            return msgs
        if req_nonempty and not series:
            msgs.append(f"'{err_key}' 是空的 — 至少要有一个系列（一组名称+数值数组）")
            return msgs
        empty_names = [n for n, v in series.items() if not _nonempty_list(v)]
        if empty_names:
            msgs.append(f"'{err_key}' 里这些系列没有数据: {empty_names[:3]}"
                        f"{'...' if len(empty_names) > 3 else ''} — 空系列无法画，请删掉或补数据")
        for n, v in series.items():
            if _nonempty_list(v):
                _warn_non_numeric(n, v)
                _warn_flat(n, v)
        return msgs

    # ── bar family: labels + series (+ errors / significance) ──
    if chart_type in ("bar", "grouped_bar", "hbar", "horizontal_bar", "line",
                      "stacked_bar", "box", "boxplot", "violin"):
        series = data.get("series", data.get("datasets", {}))
        fatal += _check_series_dict(series, "series")
        labels = data.get("labels", data.get("x", []))
        is_boxlike = chart_type in ("box", "boxplot", "violin")
        if _nonempty_list(labels) and series:
            if is_boxlike:
                # box/violin: labels are GROUP names — compare to series count,
                # not to values-per-series (each group holds its own array)
                n_labels, n_groups = _len(labels), len(series)
                if n_labels != n_groups:
                    fatal.append(
                        f"labels 有 {n_labels} 个组名但 series 有 {n_groups} 组 — "
                        f"每个箱线/小提琴图恰好对应一个组名，数量对不上多半是 labels 和数据错位了")
            else:
                n_labels, n_first = _len(labels), _len(next(iter(series.values())))
                if n_labels != n_first:
                    fatal.append(
                        f"labels 有 {n_labels} 项但系列值只有 {n_first} 个 — "
                        f"长度不齐会导致图内容被静默截断，请修正 CSV/JSON 对齐。")
        elif not is_boxlike and not _nonempty_list(labels):
            warns.append("未提供 labels：x 轴将使用序号 0..n-1")
        # errors must reference existing series (silent KeyError risk)
        errs = data.get("errors", {})
        if isinstance(errs, dict) and errs:
            unknown = [k for k in errs if k not in series]
            if unknown:
                warns.append(f"errors 引用了数据里不存在的系列: {unknown[:3]}")
            for n, v in errs.items():
                if n in series and _nonempty_list(v) and _len(v) != _len(series[n]):
                    warns.append(f"errors['{n}'] 有 {_len(v)} 个值但系列 '{n}' 有 {_len(series[n])} 个 — 数量应一一对应，误差棒可能错位")
        # significance keys must reference existing series
        sig = data.get("significance", {})
        if isinstance(sig, dict) and sig:
            unknown = [k for k in sig if k not in series]
            if unknown:
                warns.append(f"significance 引用了数据里不存在的系列: {unknown[:3]}")

    # ── heatmap: matrix ──
    elif chart_type == "heatmap":
        matrix = data.get("matrix", data.get("data", data.get("values")))
        if matrix is None:
            fatal.append("heatmap 需要 'matrix'（二维数值数组）— 数据里没有这个字段")
        elif not isinstance(matrix, (list, tuple)) or len(matrix) == 0:
            fatal.append("heatmap: 'matrix' 为空 — 请提供二维数组")
        elif not all(isinstance(r, (list, tuple)) and _len(r) == _len(matrix[0]) for r in matrix):
            fatal.append("heatmap: 'matrix' 各行长度不一致（参差行）— 每行单元格数必须相同")
        else:
            flat = [float(x) for r in matrix for x in r if _is_number(x)]
            n_bad = sum(1 for r in matrix for x in r if not _is_number(x))
            if n_bad:
                warns.append(f"heatmap: {n_bad} 个非数值单元格将渲染为空白/NaN")
            if flat and max(flat) == min(flat):
                warns.append(f"heatmap: 全部 {len(flat)} 个单元格值相同（{flat[0]:g}）— 热图将是单一颜色，请核对数据")

    # ── scatter: x / y (+ groups) ──
    elif chart_type == "scatter":
        x = data.get("x", data.get("xs", []))
        y = data.get("y", data.get("ys", []))
        if not _nonempty_list(x):
            fatal.append("scatter 需要 'x'（数值数组）— 字段缺失或为空")
        if not _nonempty_list(y):
            fatal.append("scatter 需要 'y'（数值数组）— 字段缺失或为空")
        if not fatal:
            if _len(x) != _len(y):
                fatal.append(f"scatter: 'x' 有 {_len(x)} 个值但 'y' 有 {_len(y)} 个 — 每个点需要一对 x/y，长度必须一致")
            _warn_non_numeric("x", x)
            _warn_non_numeric("y", y)
            if len(x) >= 2 and _is_number(x[0]) and _is_number(x[-1]) and max(float(v) for v in x if _is_number(v)) == min(float(v) for v in x if _is_number(v)):
                warns.append("scatter: 所有 x 值相同 — 点将垂直堆叠，趋势线（若显示）无意义")
        groups = data.get("groups", data.get("colors"))
        if groups is not None and not _nonempty_list(groups):
            fatal.append("scatter: 'groups' 存在但为空")
        elif groups is not None and _len(groups) != _len(x) and _len(groups) > 0:
            warns.append(f"scatter: 'groups' 有 {_len(groups)} 项但共 {_len(x)} 个点 — 分组可能错位")

    # ── forest: estimates + ci_low + ci_high ──
    elif chart_type == "forest":
        estimates = data.get("estimates", data.get("values", []))
        ci_low = data.get("ci_low", data.get("lower", []))
        ci_high = data.get("ci_high", data.get("upper", []))
        if not _nonempty_list(estimates):
            fatal.append("forest 需要 'estimates'（各研究效应值）— 字段缺失或为空")
        if not _nonempty_list(ci_low):
            fatal.append("forest 需要 'ci_low'（各研究 CI 下限）— 字段缺失或为空")
        if not _nonempty_list(ci_high):
            fatal.append("forest 需要 'ci_high'（各研究 CI 上限）— 字段缺失或为空")
        if not fatal:
            if not (_len(estimates) == _len(ci_low) == _len(ci_high)):
                fatal.append(f"forest: estimates/ci_low/ci_high 长度不一致（{_len(estimates)}/{_len(ci_low)}/{_len(ci_high)}）— 每个研究都要三个值")
            _warn_non_numeric("estimates", estimates)
            for i in range(min(_len(estimates), _len(ci_low), _len(ci_high))):
                if _is_number(estimates[i]) and _is_number(ci_low[i]) and _is_number(ci_high[i]):
                    if not (float(ci_low[i]) <= float(estimates[i]) <= float(ci_high[i])):
                        warns.append(f"forest: 研究 {i} 的效应值 {estimates[i]:g} 落在 CI [{ci_low[i]:g}, {ci_high[i]:g}] 之外 — 请核对数据")
        labels = data.get("labels", data.get("studies", []))
        if _nonempty_list(labels) and _len(labels) != _len(estimates):
            warns.append(f"forest: {_len(labels)} 个研究标签但 {_len(estimates)} 个效应值 — 标签可能错位")
        weights = data.get("weights")
        if _nonempty_list(weights) and _len(weights) != _len(estimates):
            warns.append(f"forest: {_len(weights)} 个权重但 {_len(estimates)} 个效应值 — 气泡大小可能错配")
        events = data.get("events")
        if isinstance(events, list) and events and _len(events) != _len(estimates):
            warns.append(f"forest: {_len(events)} 行事件数据但 {_len(estimates)} 个效应值 — events/total 可能错位")

    # ── KM: groups (list of [t, s] pairs) OR time + survival ──
    elif chart_type in ("km", "survival"):
        groups = data.get("groups", data.get("series", {}))
        has_time = _nonempty_list(data.get("time", []))
        if isinstance(groups, dict) and groups and all(isinstance(v, (list, tuple)) and v and all(isinstance(p, (list, tuple)) and _len(p) >= 2 for p in v) for v in groups.values()):
            for gname, pairs in groups.items():
                times = [p[0] for p in pairs if _is_number(p[0])]
                if len(times) >= 2 and any(times[i] > times[i + 1] for i in range(len(times) - 1)):
                    warns.append(f"km: 组 '{gname}' 时间点未升序 — 拟合前已自动排序，曲线不受影响")
        elif has_time and isinstance(data.get("survival"), dict):
            surv = data["survival"]
            fatal += _check_series_dict(surv, "survival", req_nonempty=False)
            for gname, s in surv.items():
                if _nonempty_list(s) and _len(s) != _len(data["time"]):
                    fatal.append(f"km: survival['{gname}'] 有 {_len(s)} 个值但 'time' 有 {_len(data['time'])} 个 — 长度必须一致")
        elif isinstance(groups, dict) and groups:
            # v2.6 A1: dict 有内容但值不是 [t, e] 成对列表。最常见是 CSV/Excel 长表
            # （time/event/group 各一列、一行一名患者）被通用转换装进 series——
            # 此前静默通过并渲染出无意义单曲线，必须拦截并给转换指引。
            _long_keys = {"time", "event", "status", "group", "groups"}
            _keys_l = {str(k).strip().lower() for k in groups}
            if _keys_l & _long_keys:
                fatal.append(
                    "km: 检测到长表结构（time/event/group 各占一列，一行记录一名患者）—"
                    "这种表无法直接画生存曲线。请转成 JSON："
                    '{"groups": {"组名": [[时间, 事件(1=事件/0=删失), ...]], ...}}，'
                    "每组一个数组；格式详见 references/data-formats.md")
            else:
                fatal.append(
                    "km: groups 的每个值必须是 [时间, 事件(1/0)] 成对列表，当前是普通数值数组 —"
                    '请改为 {"组名": [[12, 1], [24, 0], ...]}，或改用 time+survival 两个数组')
        elif not isinstance(groups, dict) or not groups:
            fatal.append("km 需要 'groups'（{组名: [[t, s], ...]}）或 'time'+'survival' 数组 — 都没找到")

    # ── ROC: curves OR fpr + tpr ──
    elif chart_type == "roc":
        curves = data.get("curves", [])
        fpr = data.get("fpr", data.get("x", []))
        tpr = data.get("tpr", data.get("y", []))
        if _nonempty_list(curves):
            has_scores_mode = data.get("labels") is not None and all(
                isinstance(c, dict) and _nonempty_list(c.get("scores")) for c in curves)
            for i, c in enumerate(curves):
                if not isinstance(c, dict) or not (_nonempty_list(c.get("fpr")) and _nonempty_list(c.get("tpr"))):
                    if has_scores_mode:
                        continue  # --compare 模式：原始分数曲线（labels+scores），无需 fpr/tpr
                    fatal.append(f"roc: curves[{i}] 必须有 'fpr' 和 'tpr' 数组（--compare 模式可用 labels+scores）")
                elif _len(c["fpr"]) != _len(c["tpr"]):
                    fatal.append(f"roc: curves[{i}] fpr/tpr 长度不一致（{_len(c['fpr'])}/{_len(c['tpr'])}）")
                else:
                    f = [float(v) for v in c["fpr"] if _is_number(v)]
                    if len(f) >= 2 and any(f[i] > f[i + 1] + 1e-9 for i in range(len(f) - 1)):
                        warns.append(f"roc: curves[{i}] fpr 非单调 — 请按阈值排序曲线")
                c_auc = c.get("auc")
                if isinstance(c_auc, (int, float)) and not (0.0 <= float(c_auc) <= 1.0):
                    warns.append(f"roc: curves[{i}] auc={c_auc:g} 超出 [0, 1] — 请核对该值")
        elif _nonempty_list(fpr) and _nonempty_list(tpr):
            if _len(fpr) != _len(tpr):
                fatal.append(f"roc: fpr 有 {_len(fpr)} 个但 tpr 有 {_len(tpr)} 个 — 长度必须一致")
            _warn_non_numeric("fpr", fpr)
            _warn_non_numeric("tpr", tpr)
        else:
            fatal.append("roc 需要 'curves'（{fpr,tpr} 列表）或 'fpr'+'tpr' 数组 — 都没找到")
        auc = data.get("auc")
        if isinstance(auc, (int, float)) and not (0.0 <= float(auc) <= 1.0):
            warns.append(f"roc: auc={auc:g} 超出 [0, 1] — 请核对该值")

    # ── dual_axis: labels + left + right ──
    elif chart_type == "dual_axis":
        labels = data.get("labels", data.get("x", []))
        left = data.get("left", data.get("y1", {}))
        right = data.get("right", data.get("y2", {}))
        fatal += _check_series_dict(left, "left/y1")
        fatal += _check_series_dict(right, "right/y2")
        if not fatal and _nonempty_list(labels) and left and right:
            n_first = _len(next(iter(left.values())))
            if _len(labels) != n_first:
                fatal.append(f"dual_axis: labels 有 {_len(labels)} 项但 left/right 系列有 {n_first} 个 — 长度必须一致")

    # ── composite: panels ──
    elif chart_type == "composite":
        panels = data.get("panels", [])
        if not isinstance(panels, list) or not panels:
            fatal.append("composite 需要 'panels'（非空面板对象列表）")
        else:
            bad = [i for i, p in enumerate(panels) if not isinstance(p, dict) or not p.get("type")]
            if bad:
                fatal.append(f"composite: 面板 {bad[:5]} 缺少 'type' 字段 — 每个面板都要有 type（如 'bar'）")

    # ── diagram: blocks ──
    elif chart_type == "diagram":
        blocks = data.get("blocks", [])
        if not isinstance(blocks, list) or not blocks:
            fatal.append("diagram 需要 'blocks'（非空块对象列表）")

    # ── prisma: PRISMA 2020 flow, counts + arithmetic consistency gates ──
    elif chart_type == "prisma":
        req_ints = ["records_identified", "studies_included"]
        opt_ints = ["duplicates_removed", "records_screened", "records_excluded",
                    "reports_sought", "reports_not_retrieved", "reports_assessed"]
        vals = {}
        for k in req_ints + opt_ints:
            v = data.get(k)
            if v is None:
                continue
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                fatal.append(f"prisma '{k}' 必须是非负整数（当前 {v!r}）")
            else:
                vals[k] = v
        for k in req_ints:
            if k not in vals:
                fatal.append(f"prisma 缺少 '{k}'（非负整数）")
        # Derive the pipeline the same way gen_prisma will, so gates hold
        # even for omitted intermediate fields (a review's numbers must ADD UP).
        ident = vals.get("records_identified")
        dup = vals.get("duplicates_removed", 0)
        screened = vals.get("records_screened")
        if screened is None and ident is not None:
            screened = ident - dup
        excluded = vals.get("records_excluded", 0)
        sought = vals.get("reports_sought")
        if sought is None and screened is not None:
            sought = screened - excluded
        not_ret = vals.get("reports_not_retrieved", 0)
        assessed = vals.get("reports_assessed")
        if assessed is None and sought is not None:
            assessed = sought - not_ret
        if ident is not None and vals.get("records_screened") is not None \
                and vals["records_screened"] != ident - dup:
            fatal.append(f"prisma 数字自洽校验失败: records_screened ({vals['records_screened']}) != "
                         f"records_identified - duplicates_removed ({ident - dup})")
        if vals.get("reports_sought") is not None and screened is not None \
                and vals["reports_sought"] != screened - excluded:
            fatal.append(f"prisma 数字自洽校验失败: reports_sought ({vals['reports_sought']}) != "
                         f"records_screened - records_excluded ({screened - excluded})")
        if vals.get("reports_assessed") is not None and sought is not None \
                and vals["reports_assessed"] != sought - not_ret:
            fatal.append(f"prisma 数字自洽校验失败: reports_assessed ({vals['reports_assessed']}) != "
                         f"reports_sought - reports_not_retrieved ({sought - not_ret})")
        reasons = data.get("exclusion_reasons")
        if reasons is not None:
            if not isinstance(reasons, dict) or not reasons:
                fatal.append("prisma 'exclusion_reasons' 必须是非空对象 {原因: 数量}")
            else:
                bad = {r: n for r, n in reasons.items()
                       if isinstance(n, bool) or not isinstance(n, int) or n < 0}
                if bad:
                    fatal.append(f"prisma exclusion_reasons 的值必须是非负整数，"
                                 f"这些键有问题: {bad}")
                total = sum(n for n in reasons.values()
                            if isinstance(n, int) and not isinstance(n, bool))
                inc = vals.get("studies_included")
                if assessed is not None and inc is not None and total + inc != assessed:
                    fatal.append(f"prisma 数字自洽校验失败: exclusion_reasons 总数 ({total}) + "
                                 f"studies_included ({inc}) != reports_assessed ({assessed}) "
                                 f"— 排除人数+纳入数应等于评估全文数，请复核流程数字")
        lang = data.get("lang")
        if lang is not None and lang not in ("en", "zh"):
            fatal.append("prisma 'lang' 只能是 'en' 或 'zh'")

    if _afcharts is not None and chart_type in _afcharts.EXTRA_GENERATORS:
        f23, w23 = _afcharts.validate_extra(chart_type, data)
        fatal.extend(f23)
        warns.extend(w23)

    return fatal, warns


def legend_audit(ax, chart_type, no_legend, n_series):
    """Detect silently-empty legends: >= 2 series drawn, none labeled.

    n_series comes from the DATA (not artist count — matplotlib's
    get_legend_handles_labels only returns labeled artists, so an all-
    unlabeled multi-series figure reports 0 handles). Types that use
    x-axis labels (box/violin/forest), a colorbar (heatmap), or their
    own legend (dual_axis, composite, diagram) are exempt.
    """
    if no_legend or chart_type in ("box", "boxplot", "violin", "heatmap", "forest",
                                   "composite", "diagram", "dual_axis"):
        return None
    if n_series < 2:
        return None
    handles, labels = ax.get_legend_handles_labels()
    if not any(labels):
        return ("绘制了多个系列但没有一个带 label — 图例将为空；"
                "请在 JSON 里给系列加 name 键（或 CSV 用分组列）以便区分")
    return None


# ── Figure generators ──────────────────────────────────────────────────

def apply_base_style(ax, theme):
    """Apply common styling to axes."""
    for spine in theme["spines"]:
        ax.spines[spine].set_visible(False)
    if _STYLE_NO_GRID[0]:
        ax.grid(False)
        ax.tick_params(labelsize=theme["font_size"] - 1, length=3, width=1.0)
        return
    ax.yaxis.grid(True, alpha=theme["grid_alpha"], linestyle='--')
    ax.tick_params(labelsize=theme["font_size"] - 1)


def gen_bar(data, ax, theme, cjk_fp, **kwargs):
    """Grouped bar chart with horizontal mode, hatching, error bars, significance, and ratio annotations."""
    labels = data.get("labels", data.get("x", []))
    series = data.get("series", data.get("datasets", {}))

    n_groups = len(labels)
    n_series = len(series)
    x = np.arange(n_groups)
    w = 0.8 / max(n_series, 1)
    colors = theme["colors"]
    horizontal = kwargs.get("horizontal", False)
    use_hatch = kwargs.get("hatch", False)
    show_ratio = kwargs.get("show_ratio", False)
    ratio_base = kwargs.get("ratio_base", 0)  # index of base series for ratio

    error_data = data.get("errors", {})
    significance = data.get("significance", {})

    bar_func = ax.barh if horizontal else ax.bar
    all_bars = []  # store for ratio calculation

    for i, (name, values) in enumerate(series.items()):
        offset = (i - (n_series - 1) / 2) * w
        errs = None
        if name in error_data and error_data[name]:
            errs = error_data[name]
            if isinstance(errs, list) and all(isinstance(e, (int, float)) for e in errs):
                pass  # per-bar error
            elif isinstance(errs, (int, float)):
                errs = [errs] * n_groups

        hatch_val = HATCH_PATTERNS[i % len(HATCH_PATTERNS)] if use_hatch else None
        if kwargs.get("alternate", False) and n_series == 1:
            # GLM-5.2 blog style: alternate first two theme colors per bar
            bar_colors = [colors[j % 2] for j in range(len(values))]
        else:
            bar_colors = colors[i % len(colors)]
        if use_hatch:
            # GLM-5.2 blog style: ALL bars get hatching with black hatch lines
            # on colored fill. Black edgecolor ensures visibility on any fill.
            bars = bar_func(x + offset, values, w, yerr=errs,
                            color=bar_colors, edgecolor='black', linewidth=0.6,
                            hatch=hatch_val, capsize=3,
                            error_kw={'linewidth': 1}, label=name)
        else:
            bars = bar_func(x + offset, values, w, yerr=errs,
                            color=bar_colors, edgecolor='white', linewidth=0.5,
                            capsize=3, error_kw={'linewidth': 1}, label=name)
        all_bars.append((name, values, bars, offset))

        # Value labels on bars
        if kwargs.get("show_values", False):
            for j, v in enumerate(values):
                err = errs[j] if errs and j < len(errs) else 0
                if horizontal:
                    ax.text(v + err + max(values) * 0.01, x[j] + offset,
                            f'{v:.1f}', ha='left', va='center', fontsize=7,
                            color=colors[i % len(colors)])
                else:
                    ax.text(x[j] + offset, v + err + max(values) * 0.01,
                            f'{v:.1f}', ha='center', va='bottom', fontsize=7,
                            color=colors[i % len(colors)])

    # Ratio annotations (e.g., "4.96x" above second series bars)
    if show_ratio and n_series >= 2:
        base_name = list(series.keys())[ratio_base]
        base_values = list(series.values())[ratio_base]
        for i, (name, values, bars, offset) in enumerate(all_bars):
            if i == ratio_base:
                continue
            for j, v in enumerate(values):
                bv = base_values[j] if j < len(base_values) else 0
                if bv != 0:
                    ratio = v / bv
                    ratio_str = f'{ratio:.2f}x' if ratio >= 1 else f'{ratio:.2f}x'
                    ratio_color = '#D55E00'
                    if horizontal:
                        ax.text(v + max(values) * 0.02, x[j] + offset,
                                ratio_str, ha='left', va='center', fontsize=8,
                                fontweight='bold', color=ratio_color)
                    else:
                        ax.text(x[j] + offset, v + max(values) * 0.02,
                                ratio_str, ha='center', va='bottom', fontsize=8,
                                fontweight='bold', color=ratio_color)

    # Significance brackets
    if significance:
        for key, label in significance.items():
            parts = key.split(":")
            if len(parts) == 2:
                grp_idx = int(parts[1])
            else:
                grp_idx = int(parts[0])
            if horizontal:
                x_top = ax.get_xlim()[1] * 0.95
                y_pos = x[grp_idx]
                fc = '#C0392B' if label not in ('NS', 'ns') else 'gray'
                fw = 'bold' if label not in ('NS', 'ns') else 'normal'
                ax.annotate(label, (x_top, y_pos), ha='left', va='center',
                            fontsize=8, fontweight=fw, color=fc)
            else:
                y_top = ax.get_ylim()[1] * 0.95
                fc = '#C0392B' if label not in ('NS', 'ns') else 'gray'
                fw = 'bold' if label not in ('NS', 'ns') else 'normal'
                ax.annotate(label, (x[grp_idx], y_top), ha='center', va='bottom',
                            fontsize=8, fontweight=fw, color=fc)

    if horizontal:
        y_fs = theme["font_size"] - 1
        if len(labels) > 12:
            y_fs -= 1
        ax.set_yticks(x)
        ax.set_yticklabels(labels, fontsize=y_fs,
                           fontproperties=cjk_fp if cjk_fp and any(has_cjk(l) for l in labels) else None)
        ax.invert_yaxis()
    else:
        max_lbl_len = max((len(str(l)) for l in labels), default=0)
        rotation = 45 if (len(labels) > 8 or max_lbl_len > 12) else 0
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=theme["font_size"] - 1,
                           rotation=rotation, ha='right' if rotation else 'center',
                           fontproperties=cjk_fp if cjk_fp and any(has_cjk(l) for l in labels) else None)


def gen_heatmap(data, ax, theme, cjk_fp, **kwargs):
    """Heatmap with text annotations."""
    matrix = data.get("matrix", data.get("data", data.get("values", None)))
    if matrix is None:
        # Fallback: build matrix from series (C2 fix — CSV heatmap support)
        series = data.get("series", {})
        if series:
            matrix = np.array(list(series.values()))
        else:
            matrix = np.array([])
    else:
        matrix = np.array(matrix)
    row_labels = data.get("row_labels", data.get("y_labels", data.get("rows", data.get("labels", []))))
    col_labels = data.get("col_labels", data.get("x_labels", data.get("cols", list(data.get("series", {}).keys()))))
    cmap = kwargs.get("cmap") or "RdBu_r"
    vmin = kwargs.get("vmin", None)
    vmax = kwargs.get("vmax", None)
    annot_fmt = kwargs.get("annot_format", "{:+.1f}")

    if matrix.size == 0:
        raise ValueError("heatmap: matrix is empty — provide 'matrix' (2D list) or 'series'")
    ax._af_category_axis = True  # 行列标签是数据：豁免 fix_tick_overlaps 降级

    has_neg = bool((matrix < 0).any())
    # Data-driven default: all-positive data uses a warm sequential colormap
    # (YlOrRd) — RdBu_r's white midpoint makes low positive values look like
    # a "broken band" (断层). Diverging colormaps are only sensible when the
    # data actually spans negative values.
    if cmap == "RdBu_r" and not has_neg and kwargs.get("cmap") is None:
        cmap = "YlOrRd"

    if vmin is None or vmax is None:
        if has_neg:
            abs_max = max(abs(matrix.min()), abs(matrix.max()))
            vmin = vmin if vmin is not None else -abs_max
            vmax = vmax if vmax is not None else abs_max
        else:
            vmin = vmin if vmin is not None else float(matrix.min())
            vmax = vmax if vmax is not None else float(matrix.max())

    im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto')

    # Text annotations
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            color = 'white' if abs(v) > (abs(vmin) + abs(vmax)) / 2 * 0.7 else 'black'
            ax.text(j, i, annot_fmt.format(v), ha='center', va='center',
                    fontsize=9, fontweight='bold', color=color)

    ax.set_xticks(range(len(col_labels)))
    use_cjk_cols = cjk_fp and any(has_cjk(l) for l in col_labels)
    max_col_len = max((len(str(l)) for l in col_labels), default=0)
    rot = 45 if (len(col_labels) > 6 or max_col_len > 14) else 0
    ax.set_xticklabels(col_labels, fontsize=theme["font_size"] - 2,
                       rotation=rot, ha='right' if rot else 'center',
                       fontproperties=cjk_fp if use_cjk_cols else None)
    ax.set_yticks(range(len(row_labels)))
    use_cjk_rows = cjk_fp and any(has_cjk(l) for l in row_labels)
    ax.set_yticklabels(row_labels, fontsize=theme["font_size"],
                       fontproperties=cjk_fp if use_cjk_rows else None)

    return im  # for colorbar


def gen_scatter(data, ax, theme, cjk_fp, **kwargs):
    """Scatter plot with optional trend line and grouping."""
    x_data = np.array(data.get("x", data.get("xs", [])))
    y_data = np.array(data.get("y", data.get("ys", [])))
    groups = data.get("groups", data.get("colors", None))

    if groups is None:
        ax.scatter(x_data, y_data, s=60, color=theme["colors"][0],
                   edgecolors='white', linewidth=0.5, alpha=0.7, zorder=3)
    else:
        # Validate groups length matches x/y data length
        n = min(len(x_data), len(y_data))
        if len(groups) > n:
            groups = groups[:n]
        unique_groups = list(dict.fromkeys(groups))  # preserve order
        for i, g in enumerate(unique_groups):
            mask = [j for j in range(len(groups)) if groups[j] == g]
            c = theme["colors"][i % len(theme["colors"])]
            ax.scatter(x_data[mask], y_data[mask], s=60, c=c,
                       edgecolors='white', linewidth=0.5, alpha=0.7,
                       label=g, zorder=3)

    # Point labels (data["labels"] — one per (x, y) point)
    point_labels = data.get("labels", [])
    if point_labels and len(point_labels) == len(x_data):
        use_cjk = cjk_fp and any(has_cjk(str(l)) for l in point_labels)
        n_pts = len(x_data)
        for i, (xi, yi, lab) in enumerate(zip(x_data, y_data, point_labels)):
            # Alternate above/below to keep neighbors readable; offset grows
            # with index so clustered points (e.g. years 1950/1953/1955) don't collide.
            row = i // 2  # every other point flips side
            dy = 10 + 3 * row if i % 2 == 0 else -13 - 3 * row
            ax.annotate(str(lab), xy=(xi, yi), xytext=(0, dy),
                        textcoords='offset points', fontsize=6.5,
                        ha='center', va='center', zorder=5,
                        fontproperties=cjk_fp if use_cjk else None,
                        color='#444444', alpha=0.9)

    # Trend line
    if kwargs.get("trend", True) and len(x_data) >= 3:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_line = np.linspace(x_data.min(), x_data.max(), 100)
        ax.plot(x_line, p(x_line), '--', color='gray', alpha=0.6, linewidth=1.2,
                zorder=2, label='Linear trend')
        r = np.corrcoef(x_data, y_data)[0, 1]
        ax.text(0.95, 0.05, f'r = {r:.3f}', transform=ax.transAxes,
                ha='right', va='bottom', fontsize=9, fontstyle='italic', color='gray',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='lightgray'))

    # Mean points
    if groups and kwargs.get("show_mean", False):
        unique_groups = list(dict.fromkeys(groups))
        for i, g in enumerate(unique_groups):
            mask = [j for j in range(len(groups)) if groups[j] == g]
            mx, my = np.mean(x_data[mask]), np.mean(y_data[mask])
            c = theme["colors"][i % len(theme["colors"])]
            ax.scatter(mx, my, s=150, c=c, edgecolors='black', linewidth=1.2,
                       marker='o', zorder=4)

    ax.xaxis.grid(True, alpha=theme["grid_alpha"], linestyle='--')


def gen_line(data, ax, theme, cjk_fp, **kwargs):
    """Line chart with optional error bands."""
    labels = data.get("labels", data.get("x", []))
    series = data.get("series", data.get("datasets", {}))
    error_data = data.get("errors", {})
    markers = ['o', 's', 'D', '^', 'v', 'p', '*', 'h', '+', 'x']

    x = np.arange(len(labels)) if not any(isinstance(l, (int, float)) for l in labels) else np.array(labels)

    for i, (name, values) in enumerate(series.items()):
        c = theme["colors"][i % len(theme["colors"])]
        mk = markers[i % len(markers)]
        lw = kwargs.get("linewidth", 2)
        ax.plot(x, values, c=c, marker=mk, markersize=6, linewidth=lw, label=name, zorder=3)

        # Error band/fill
        if name in error_data and error_data[name]:
            errs = error_data[name]
            if isinstance(errs, list) and len(errs) == len(values):
                lower = [v - e for v, e in zip(values, errs)]
                upper = [v + e for v, e in zip(values, errs)]
                ax.fill_between(x, lower, upper, color=c, alpha=0.15, zorder=2)

    ax.set_xticks(x if not any(isinstance(l, (int, float)) for l in labels) else range(len(labels)))
    if not any(isinstance(l, (int, float)) for l in labels):
        use_cjk = cjk_fp and any(has_cjk(l) for l in labels)
        rot = 45 if len(labels) > 10 else 0
        ax.set_xticklabels(labels, fontsize=theme["font_size"] - 1,
                           rotation=rot, ha='right' if rot else 'center',
                           fontproperties=cjk_fp if use_cjk else None)


def gen_box(data, ax, theme, cjk_fp, **kwargs):
    """Box plot with optional jitter points."""
    labels = data.get("labels", data.get("x", []))
    series = data.get("series", data.get("datasets", {}))

    positions = list(range(len(series)))
    bp = ax.boxplot(list(series.values()), positions=positions, widths=0.5,
                    patch_artist=True, showfliers=False)

    for i, (patch, name) in enumerate(zip(bp['boxes'], series.keys())):
        patch.set_facecolor(theme["colors"][i % len(theme["colors"])])
        patch.set_alpha(0.6)

    # Jitter points
    rng = np.random.default_rng(42)
    for i, (name, values) in enumerate(series.items()):
        vals = np.array(values, dtype=float)
        jitter_x = positions[i] + rng.normal(0, 0.06, len(vals))
        c = theme["colors"][i % len(theme["colors"])]
        ax.scatter(jitter_x, vals, s=18, c=c, alpha=0.5, zorder=3, edgecolors='none')

    ax.set_xticks(positions)
    use_cjk = cjk_fp and any(has_cjk(l) for l in series.keys())
    ax.set_xticklabels(list(series.keys()), fontsize=theme["font_size"] - 1,
                       fontproperties=cjk_fp if use_cjk else None)

    if kwargs.get("stats_multi"):
        annotate_multi_stats(ax, series, positions, theme, "box")
    elif kwargs.get("stats_auto"):
        annotate_auto_stats(ax, series, positions, theme, "box")


def gen_forest(data, ax, theme, cjk_fp, **kwargs):
    """Forest plot for meta-analysis with weights, heterogeneity, and events."""
    ax._af_category_axis = True  # 研究名 y 轴是数据：豁免防重叠抽稀（与热图同机制）
    labels = data.get("labels", data.get("studies", []))
    estimates = data.get("estimates", data.get("values", []))
    ci_low = data.get("ci_low", data.get("lower", []))
    ci_high = data.get("ci_high", data.get("upper", []))
    weights = data.get("weights", None)  # Study weights for bubble size
    overall = data.get("overall", None)
    measure = data.get("measure", "OR")  # Effect measure label: OR, RR, HR, MD, SMD
    # v2.6.0 审核修复：缺省无效线按效应尺度自动取值——比率尺度（OR/RR/HR）无效线
    # 是 1.0，差值尺度（MD/SMD）是 0.0；旧默认恒取 0 会把自然尺度 OR/HR 的
    # "CI 是否跨过 1"画错位置，误导显著性判读。显式 ref_line 永远优先。
    ref_line = data.get("ref_line", None)
    if ref_line is None:
        ref_line = 0.0 if str(measure).upper() in ("MD", "SMD") else 1.0
        print(f"forest: 未指定 ref_line，按效应尺度 {measure} 自动取无效线 {ref_line:g}"
              f"（log 尺度数据请显式传 ref_line=0）", file=sys.stderr)
    heterogeneity = data.get("heterogeneity", None)  # {"Q": float, "df": int, "I2": float, "p": float}
    events = data.get("events", None)  # [{"events": int, "total": int}, ...] per study
    use_hatch = kwargs.get("hatch", False)

    # ── v2.4.0：留一法敏感性分析（--sensitivity）──
    if kwargs.get("sensitivity") and _afstats is not None:
        se_per_study = data.get("se_list", data.get("ses", None))
        if se_per_study is None and len(ci_low) == len(ci_high) == len(estimates) and len(estimates) >= 4:
            se_per_study = [(float(h) - float(l)) / 3.92
                            for l, h in zip(ci_low, ci_high)]
            print("WARNING: forest: --sensitivity 由 95%CI 反推 se（近似 (hi-lo)/3.92）；"
                  "有精确 se 请在数据提供 se_list", file=sys.stderr)
        loo = None
        if se_per_study is None or len(se_per_study) != len(estimates):
            print("WARNING: forest: --sensitivity 需要 se_list 或可反推的对称 CI，已跳过",
                  file=sys.stderr)
        else:
            try:
                loo = _afstats.leave_one_out(estimates, se_per_study)
            except ValueError as e:
                print(f"WARNING: forest: 留一法无法计算：{e}", file=sys.stderr)
        if loo:
            for gi, (omi, pooled, plo, phi) in enumerate(loo):
                y = -(gi + 2)
                ax.plot([plo, phi], [y, y], color="#888888", lw=1.4, zorder=3)
                ax.scatter([pooled], [y], s=46, marker="D",
                           color=theme["colors"][1 % len(theme["colors"])],
                           edgecolor="#5B6770", linewidth=0.8, zorder=4)
                _lbl = (labels[omi] if isinstance(labels, list) and omi < len(labels)
                        else f"Study {omi+1}")
                ax.text(-0.02, y, f"省略{_lbl}", transform=ax.get_yaxis_transform(),
                        ha="right", va="center",
                        fontsize=max(6, theme["font_size"] - 1),
                        fontproperties=cjk_fp if cjk_fp and has_cjk(str(_lbl)) else None,
                        color="#555555")
            ax.axhline(-1.2, color="#CCCCCC", lw=0.8, linestyle="--")
            ax.text(-0.02, -1.55, "留一法敏感性分析（省略单研究后的随机效应合并）",
                    transform=ax.get_yaxis_transform(), ha="right", va="center",
                    fontsize=max(6.5, theme["font_size"] - 1),
                    fontproperties=cjk_fp if cjk_fp and has_cjk("留一") else None,
                    color="#8a6414")
            ax.set_ylim(-(len(loo) + 3.2), None)
            print(f"forest: 留一法敏感性分析 {len(loo)} 组已绘制（可见性依赖各研究效应单位一致）",
                  file=sys.stderr)

    n_studies = len(labels)
    y_pos = list(range(n_studies))

    # Calculate weight-based bubble sizes if weights provided
    if weights and len(weights) == n_studies:
        w_arr = np.array(weights, dtype=float)
        w_min, w_max = w_arr.min(), w_arr.max()
        if w_max > w_min:
            bubble_sizes = 40 + (w_arr - w_min) / (w_max - w_min) * 160  # 40-200 range
        else:
            bubble_sizes = np.full(n_studies, 80.0)
    else:
        bubble_sizes = np.full(n_studies, 80.0)

    # Column layout: leave space for events column on left
    plot_x_start = 0.0
    events_col_x = None
    if events and len(events) == n_studies:
        events_col_x = -0.3  # Relative position in axes coords, handled via text

    for i, (est, lo, hi) in enumerate(zip(estimates, ci_low, ci_high)):
        # CI whisker line
        ax.plot([lo, hi], [i, i], '-', color=theme["colors"][0], linewidth=1.5, zorder=2)
        # Weighted point estimate (bubble)
        ax.scatter(est, i, c=theme["colors"][0], s=bubble_sizes[i], zorder=3,
                   edgecolors='black', linewidth=0.5)
        # Effect estimate annotation on right
        ax.text(hi + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.02, i,
                f'{est:.2f} [{lo:.2f}, {hi:.2f}]', va='center', fontsize=8)
        # Events/Total on left (if provided)
        if events and i < len(events):
            ev = events[i]
            ev_str = f"{ev.get('events', '?')}/{ev.get('total', '?')}" if isinstance(ev, dict) else str(ev)
            ax.annotate(ev_str, xy=(0, 0), xytext=(-0.15, i),
                        textcoords=('axes fraction', 'data'),
                        ha='right', va='center', fontsize=7, color='#555555')

    # Reference line
    ax.axvline(x=ref_line, color='gray', linestyle='--', linewidth=1, alpha=0.6)

    # Separator line before overall
    if overall:
        ax.axhline(y=n_studies - 0.5, color='#333333', linewidth=0.8, alpha=0.5)

    # Overall diamond
    if overall:
        oy = n_studies
        est_o = overall["estimate"]
        lo_o = overall["ci_low"]
        hi_o = overall["ci_high"]
        diamond_x = [lo_o, est_o, hi_o, est_o, lo_o]
        diamond_y = [oy, oy - 0.2, oy, oy + 0.2, oy]
        ax.fill(diamond_x, diamond_y, color=theme["colors"][1], alpha=0.7, zorder=4,
                hatch=HATCH_PATTERNS[1] if use_hatch else None)
        ax.text(hi_o + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.02, oy,
                f'Overall: {est_o:.2f} [{lo_o:.2f}, {hi_o:.2f}]', va='center',
                fontsize=9, fontweight='bold')

    # Heterogeneity annotation
    if heterogeneity:
        i2 = heterogeneity.get("I2", None)
        q_val = heterogeneity.get("Q", None)
        df_val = heterogeneity.get("df", None)
        p_val = heterogeneity.get("p", None)
        parts = []
        if i2 is not None:
            parts.append(f"I² = {i2:.1f}%")
        if q_val is not None and df_val is not None:
            parts.append(f"Q = {q_val:.2f}, df = {df_val}")
        if p_val is not None:
            parts.append(f"p = {p_val:.3f}" if p_val >= 0.001 else f"p < 0.001")
        if parts:
            het_text = "Heterogeneity: " + "; ".join(parts)
            ax.text(0.5, -0.12, het_text, transform=ax.transAxes,
                    ha='center', va='top', fontsize=7, fontstyle='italic', color='#555555')

    # X-axis label with measure type
    ax.set_xlabel(measure, fontsize=theme["font_size"])

    # Column header for events
    if events and len(events) > 0:
        ax.annotate("Events/Total", xy=(0, 0), xytext=(-0.15, -0.8),
                    textcoords=('axes fraction', 'data'),
                    ha='right', va='center', fontsize=7, fontweight='bold', color='#333333')

    all_labels = list(labels) + (["Overall"] if overall else [])
    ax.set_yticks(list(y_pos) + ([n_studies] if overall else []))
    use_cjk = cjk_fp and any(has_cjk(l) for l in all_labels)
    ax.set_yticklabels(all_labels, fontsize=theme["font_size"],
                       fontproperties=cjk_fp if use_cjk else None)
    ax.invert_yaxis()


def gen_violin(data, ax, theme, cjk_fp, **kwargs):
    """Violin plot with optional inner box and jitter points."""
    labels = data.get("labels", data.get("x", []))
    series = data.get("series", data.get("datasets", {}))

    positions = list(range(len(series)))
    values_list = list(series.values())

    vp = ax.violinplot(values_list, positions=positions, widths=0.6,
                       showmeans=kwargs.get("show_means", True),
                       showmedians=kwargs.get("show_medians", True),
                       showextrema=kwargs.get("show_extrema", True))

    # Color the violin bodies
    for i, body in enumerate(vp['bodies']):
        body.set_facecolor(theme["colors"][i % len(theme["colors"])])
        body.set_alpha(0.6)
        body.set_edgecolor(theme["colors"][i % len(theme["colors"])])
        body.set_linewidth(1)

    # Style internal lines
    for part in ['cmeans', 'cmedians', 'cmins', 'cmaxes', 'cbars']:
        if part in vp:
            vp[part].set_color('#333333')
            vp[part].set_linewidth(1)

    ax.set_xticks(positions)
    use_cjk = cjk_fp and any(has_cjk(l) for l in series.keys())
    ax.set_xticklabels(list(series.keys()), fontsize=theme["font_size"] - 1,
                       fontproperties=cjk_fp if use_cjk else None)

    if kwargs.get("stats_multi"):
        annotate_multi_stats(ax, series, positions, theme, "violin")
    elif kwargs.get("stats_auto"):
        annotate_auto_stats(ax, series, positions, theme, "violin")


def _km_note_box(ax, text, cjk_fp=None):
    """KM 右上角注释框（log-rank/中位生存）：实测宽度自适应字号，
    保证不越出坐标区、不压 y 轴刻度；不透明底+高 zorder 防曲线横穿文字。"""
    fs = 8.0
    t = None
    for _ in range(7):
        if t is not None:
            t.remove()
        t = ax.text(0.97, 0.96, text, transform=ax.transAxes, ha="right", va="top",
                    fontsize=fs, fontstyle="italic", color="#333333", zorder=6,
                    fontproperties=cjk_fp if (cjk_fp and has_cjk(text)) else None,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=1.0,
                              edgecolor="lightgray"))
        fig = ax.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bb = t.get_window_extent(renderer=renderer)
        ax_bb = ax.get_window_extent(renderer=renderer)
        if bb.x0 >= ax_bb.x0 or fs <= 6.0:
            break
        fs -= 0.5
    return t


def gen_km(data, ax, theme, cjk_fp, **kwargs):
    """Kaplan-Meier 生存曲线（v2.3：自动风险表 + 自动 log-rank）。

    原始数据格式（每样本 [时间, 事件]）>=2 组时自动做 Mantel-Haenszel
    log-rank 检验并在图内标注；主图下方以独立坐标轴渲染"Number at risk"
    风险表（主流程经 --no-risk-table 可关闭，--risk-times 自定义显示时间点）。
    仍兼容：用户直接提供 risk_table/log_rank（优先采用，不重复计算）、
    预计算 survival 曲线格式（无原始数据时跳过自动统计并提示）。
    """
    groups = data.get("groups", data.get("series", {}))
    risk_table = data.get("risk_table", None)      # 兼容 v2.2 用户供表
    log_rank = data.get("log_rank", None)
    median_survival = data.get("median_survival", None)
    risk_axes = kwargs.get("risk_axes", None)
    want_risk = kwargs.get("risk_table", True)
    risk_times_arg = kwargs.get("risk_times", None)

    if isinstance(groups, dict):
        group_names = list(groups.keys())
    elif isinstance(groups, list):
        group_names = data.get("labels", [f"Group {i+1}" for i in range(len(groups))])
        groups = dict(zip(group_names, groups))
        bad = [g for g in groups.values()
               if not (isinstance(g, (list, tuple)) and
                       all(isinstance(p, (list, tuple)) and len(p) >= 2 and
                           all(isinstance(n, (int, float)) for n in p) for p in g) or
                       all(isinstance(n, (int, float)) for n in g))]
        if bad:
            raise ValueError(
                "km: unsupported 'groups' format. Expected {\"Group\": [[t, s], ...]} "
                "or [t1, t2, ...] per group — got object list like "
                "[{\"label\": ..., \"time\": ..., \"events\": ...}]. "
                "Convert to {\"组名\": [[t, s], ...]}.")
    else:
        group_names = []
        groups = {}

    raw_groups = {}     # 组名 -> (times, events)
    precomputed = False
    if not groups and "time" in data and "survival" in data:
        precomputed = True
        surv_data = data["survival"]
        cens_data = data.get("censored", {})
        group_names = list(surv_data.keys())
        for gname in group_names:
            t_arr = np.asarray(data["time"], dtype=float)
            s_arr = np.asarray(surv_data[gname], dtype=float)
            c_arr = np.asarray(cens_data.get(gname, [0] * len(s_arr)), dtype=float)
            c = theme["colors"][group_names.index(gname) % len(theme["colors"])]
            ax.step(t_arr, s_arr, where='post', color=c, linewidth=2, label=gname, zorder=3)
            _cm = (c_arr[:len(t_arr)] == 1)
            if _cm.any():
                ax.scatter(t_arr[:len(t_arr)][_cm], s_arr[:len(t_arr)][_cm],
                           marker='+', color=c, s=30, linewidth=1.5, zorder=4)
        if risk_axes is None or not want_risk:
            print("WARNING: km: 预计算 survival 格式无原始数据，无法自动计算风险表/"
                  "log-rank——请提供 {组: [[时间,事件], ...]} 原始格式", file=sys.stderr)
    else:
        for gname in group_names:
            raw = groups.get(gname, None)
            if not isinstance(raw, (list, tuple)) or len(raw) == 0:
                continue
            if isinstance(raw[0], (list, tuple)):
                times = np.array([p[0] for p in raw], dtype=float)
                second = np.array([p[1] for p in raw], dtype=float)
                if np.all(np.isin(second, (0.0, 1.0))):
                    raw_groups[gname] = (times, second)   # [时间, 事件0/1]
                else:
                    # [时间, 预计算生存概率]：直接阶梯绘制（v2.2 曾误当事件数，
                    # 曲线数学错误；v2.3 起正确识别），不计入自动统计
                    c = theme["colors"][group_names.index(gname) % len(theme["colors"])]
                    ax.step(times, second, where='post', color=c, linewidth=2,
                            label=gname, zorder=3)
                    print(f"WARNING: km: '{gname}' 第二列为连续值，按预计算生存概率绘制"
                          "（无原始数据，跳过自动风险表/log-rank）", file=sys.stderr)
                continue
            times = np.array(raw, dtype=float)
            raw_groups[gname] = (times, np.ones(len(times)))

        for i, gname in enumerate(group_names):
            if gname not in raw_groups:
                continue
            c = theme["colors"][i % len(theme["colors"])]
            times, events = raw_groups[gname]
            if _afstats is not None:
                t_seq, s_seq, censor_pts = _afstats.km_estimate(times, events)
            else:
                order = np.argsort(times, kind="stable")
                ts, es = times[order], events[order]
                surv, t_seq, s_seq, censor_pts = 1.0, [0.0], [1.0], []
                n_risk = len(ts)
                for ut in np.unique(ts):
                    m = ts == ut
                    d = float(es[m].sum())
                    n_c = int(m.sum() - d)
                    if n_risk > 0 and d > 0:
                        surv *= 1 - d / n_risk
                    if n_c:
                        censor_pts.append((float(ut), surv))
                    t_seq.append(float(ut)); s_seq.append(surv)
                    n_risk -= int(m.sum())
            ax.step(t_seq, s_seq, where='post', color=c, linewidth=2, label=gname, zorder=3)
            if censor_pts:
                _cts, _css = zip(*censor_pts)
                ax.scatter(_cts, _css, marker='+', color=c, s=30, linewidth=1.5, zorder=4)
            if median_survival and gname in median_survival and median_survival[gname] is not None:
                ax.axvline(x=float(median_survival[gname]), color=c, linestyle=':',
                           alpha=0.4, linewidth=1)

    # 参考线（中位生存 0.5）
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.3, linewidth=0.8)

    # ── 自动 log-rank（原始数据 >=2 组且用户未提供时）──
    if log_rank is None and len(raw_groups) >= 2 and _afstats is not None:
        try:
            chi2_v, p_lr, df_lr = _afstats.logrank_test(raw_groups)
            log_rank = {"p": p_lr, "method": "log-rank"}
            print(f"km: log-rank 检验：chi2={chi2_v:.3g}, df={df_lr}, p={p_lr:.4g}",
                  file=sys.stderr)
        except Exception as e:
            print(f"WARNING: km: log-rank 自动计算失败（{e}），跳过标注", file=sys.stderr)

    # ── 自动中位生存（原始数据组；用户传 median_survival 仍画竖线，互不冲突）──
    median_notes = []
    if kwargs.get("median_auto", True) and raw_groups and _afstats is not None:
        for gname in group_names:
            if gname not in raw_groups or (median_survival and gname in median_survival):
                continue
            t_g, e_g = raw_groups[gname]
            try:
                med, clo, chi_ = _afstats.km_median_survival(t_g, e_g)
            except Exception:
                med = None
            if med is None:
                median_notes.append(f"{gname}: 未到达")
            else:
                if clo is not None and chi_ is not None:
                    median_notes.append(f"{gname}: {med:g}（{clo:g}~{chi_:g}）")
                else:
                    median_notes.append(f"{gname}: {med:g}")
                if median_survival is None:
                    median_survival = {}
                median_survival.setdefault(gname, med)
        if median_notes:
            print("km: 自动中位生存（95%CI）：" + "；".join(median_notes), file=sys.stderr)
        if log_rank is not None:
            method = log_rank.get("method", "log-rank")
            p_val = log_rank.get("p")
            try:
                p_val = float(p_val)
            except (ValueError, TypeError):
                p_val = 1.0
            p_str = f"p = {p_val:.3f}" if p_val >= 0.001 else "p < 0.001"
            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "NS"
            _box_lines = [f"{method} {p_str}{sig}"]
            if median_notes:
                _box_lines.append("中位生存月（95%CI）")
                _box_lines += median_notes[:4]
            _km_note_box(ax, "\n".join(_box_lines), cjk_fp)
            median_notes = []
        if median_notes:
            _km_note_box(ax, "中位生存月（95%CI）\n" + "\n".join(median_notes[:4]), cjk_fp)

    # ── 风险表（自动计算；独立坐标轴与主图共享 x 轴）──
    rendered = False
    if want_risk and raw_groups and risk_axes is not None and _afstats is not None:
        try:
            if risk_times_arg:
                if isinstance(risk_times_arg, str):
                    disp_times = [float(x) for x in risk_times_arg.split(",") if x.strip()]
                else:
                    disp_times = [float(x) for x in risk_times_arg]
            else:
                all_t = np.concatenate([t for t, _ in raw_groups.values()])
                disp_times = _afstats.default_risk_times(all_t, k=5)
            ax.set_xlim(left=0)
            x_max = ax.get_xlim()[1]
            rows = []
            for gname in group_names:
                if gname not in raw_groups:
                    continue
                t_g, e_g = raw_groups[gname]
                col = theme["colors"][group_names.index(gname) % len(theme["colors"])]
                rows.append((gname, _afstats.km_at_risk(t_g, e_g, disp_times), col))
            ra = risk_axes
            ra.set_xlim(0, x_max)
            ra.set_ylim(0, max(len(rows), 1))
            ra.invert_yaxis()
            for sp in ra.spines.values():
                sp.set_visible(False)
            ra.set_yticks([])
            ra.tick_params(axis="x", labelbottom=False, length=0)
            ra.grid(False)
            _hdr_txt = ("Number at risk（处于风险人数）"
                        if any(has_cjk(str(g)) for g, _, _ in rows) or bool(cjk_fp)
                        else "Number at risk")
            _fp_hdr = cjk_fp if cjk_fp and has_cjk(_hdr_txt) else None
            ra.text(0.0, -0.66, _hdr_txt,
                    fontsize=max(7, theme["font_size"] - 1), fontweight="bold",
                    color="#333333", ha="left", va="center", fontproperties=_fp_hdr,
                    clip_on=False)
            # 组名实测定位（修复组名与首列数字黏连）：右缘 = 首列数字左缘 - 间距
            ra.figure.canvas.draw()
            _renderer = ra.figure.canvas.get_renderer()
            _inv_data = ra.transData.inverted()
            _num_fs = max(6.5, theme["font_size"] - 1.5)
            _t0 = min(disp_times)
            _first_w = 0.0
            for _g, _counts, _c in rows:
                _p = ra.text(_t0, 0.5, str(_counts[0]), fontsize=_num_fs,
                             ha="center", va="center")
                _bb = _p.get_window_extent(renderer=_renderer).transformed(_inv_data)
                _first_w = max(_first_w, _bb.width)
                _p.remove()
            _name_right = _t0 - _first_w / 2 - x_max * 0.02
            for ri, (gname, counts, col) in enumerate(rows):
                y = ri + 0.5
                _fp_g = cjk_fp if cjk_fp and has_cjk(str(gname)) else None
                ra.text(_name_right, y, str(gname), fontsize=max(6.5, theme["font_size"] - 1.5),
                        color=col, ha="right", va="center", fontweight="bold",
                        fontproperties=_fp_g, clip_on=False)
                for t_v, cnt in zip(disp_times, counts):
                    if t_v <= x_max:
                        ra.text(t_v, y, str(cnt),
                                fontsize=max(6.5, theme["font_size"] - 1.5),
                                color="#333333", ha="center", va="center")
            rendered = True
        except Exception as e:
            print(f"WARNING: km: 自动风险表渲染失败（{e}）", file=sys.stderr)

    # ── 兼容 v2.2：用户直接提供 risk_table 且无自动表时的文本模式 ──
    if not rendered and risk_table and isinstance(risk_table, dict):
        rt_times = risk_table.get("times", [])
        ax.text(0.02, -0.08, "Number at risk", transform=ax.transAxes,
                fontsize=7, fontweight='bold', color='#333333')
        for i, gname in enumerate(group_names):
            c = theme["colors"][i % len(theme["colors"])]
            n_at = risk_table.get(gname, [])
            rt_str = "  ".join(str(n) for n in n_at)
            ax.text(0.02, -0.08 - (i + 1) * 0.04, f"{gname}: {rt_str}",
                    transform=ax.transAxes, fontsize=6, color=c)

    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(left=0)
    ax.xaxis.grid(True, alpha=theme["grid_alpha"], linestyle='--')


def gen_roc(data, ax, theme, cjk_fp, **kwargs):
    """ROC curve with AUC value, confidence interval, and optimal cutoff."""
    curves = data.get("curves", None)  # list of curve objects
    single_fpr = data.get("fpr", data.get("x", None))
    single_tpr = data.get("tpr", data.get("y", None))
    single_auc = data.get("auc", None)
    ci = data.get("ci", None)  # {"low": 0.82, "high": 0.94}
    cutoff = data.get("cutoff", None)  # {"fpr": 0.15, "tpr": 0.88, "threshold": 2.35}
    diagonal = data.get("diagonal", True)  # show diagonal reference line

    # Support single curve (fpr/tpr arrays) or multiple curves
    if curves is None and single_fpr is not None and single_tpr is not None:
        fpr_arr = np.array(single_fpr, dtype=float)
        tpr_arr = np.array(single_tpr, dtype=float)
        auc_val = single_auc

        # Compute AUC if not provided
        if auc_val is None:
            auc_val = np.trapezoid(tpr_arr, fpr_arr) if hasattr(np, 'trapezoid') else np.trapz(tpr_arr, fpr_arr)

        ax.plot(fpr_arr, tpr_arr, color=theme["colors"][0], linewidth=2.5, zorder=3,
                label=f'AUC = {auc_val:.3f}')

        # CI annotation
        if ci:
            ci_low = ci.get("low", ci.get("ci_low", None))
            ci_high = ci.get("high", ci.get("ci_high", None))
            if ci_low is not None and ci_high is not None:
                ax.text(0.95, 0.05, f'95% CI: [{ci_low:.3f}, {ci_high:.3f}]',
                        transform=ax.transAxes, ha='right', va='bottom',
                        fontsize=8, color='#555555',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor='lightgray'))

        # Optimal cutoff point
        if cutoff:
            co_fpr = cutoff.get("fpr", None)
            co_tpr = cutoff.get("tpr", None)
            co_thr = cutoff.get("threshold", None)
            if co_fpr is not None and co_tpr is not None:
                ax.scatter(co_fpr, co_tpr, color=theme["colors"][0], s=80, zorder=5,
                           edgecolors='black', linewidth=1, marker='o')
                label_parts = [f'Optimal cutoff']
                if co_thr is not None:
                    label_parts.append(f'threshold = {co_thr}')
                ax.annotate('\n'.join(label_parts), (co_fpr, co_tpr),
                            textcoords='offset points', xytext=(10, -15),
                            fontsize=7, color='#555555',
                            arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))

    elif curves:
        # Multiple ROC curves
        _seen_labels = set()
        for i, curve in enumerate(curves):
            fpr_c = np.array(curve.get("fpr", curve.get("x", [])), dtype=float)
            tpr_c = np.array(curve.get("tpr", curve.get("y", [])), dtype=float)
            auc_c = curve.get("auc", None)
            name = curve.get("name", f'Model {i+1}')

            if auc_c is None:
                auc_c = np.trapezoid(tpr_c, fpr_c) if hasattr(np, 'trapezoid') else np.trapz(tpr_c, fpr_c)

            c = theme["colors"][i % len(theme["colors"])]
            label = f'{name} (AUC={auc_c:.3f})'
            # B3(v2.7)：两条曲线 AUC 相同（或同名）时图例标签会完全重复——
            # 自动加序号消歧并 stderr 告知，避免图例两条一模一样无法区分
            if label in _seen_labels:
                uniq = f'{label} #{i + 1}'
                k = 2
                while uniq in _seen_labels:
                    uniq = f'{label} #{k + 1}'
                    k += 1
                print(f"WARNING: ROC 曲线「{name}」图例标签重复（AUC 相同或同名），"
                      f"已自动消歧为「{uniq}」", file=sys.stderr)
                label = uniq
            _seen_labels.add(label)
            ax.plot(fpr_c, tpr_c, color=c, linewidth=2, zorder=3, label=label)

    # ── v2.3：配对 DeLong 多模型 AUC 比较（--compare，需原始分数）──
    if kwargs.get("roc_compare") and _afstats is not None:
        labels_raw = data.get("labels", None)
        curves_cmp = data.get("curves", None)
        scores_ok = (labels_raw is not None and isinstance(curves_cmp, list)
                     and all("scores" in c for c in curves_cmp)
                     and len(curves_cmp) >= 2)
        if scores_ok:
            try:
                scores_by_model = {str(c.get("name", f"模型{i+1}")): c["scores"]
                                   for i, c in enumerate(curves_cmp)}
                aucs_d, pairs_d = _afstats.delong_paired(labels_raw, scores_by_model)
                lines = ["DeLong 配对检验"]
                for a_n, b_n, p_d, z_d in pairs_d:
                    lines.append(f"{a_n} vs {b_n}: p={p_d:.3g}")
                    print(f"  roc compare: {a_n} vs {b_n}: AUC "
                          f"{aucs_d[a_n]:.3f} vs {aucs_d[b_n]:.3f}, "
                          f"DeLong p={p_d:.4g} (z={z_d:.2g})", file=sys.stderr)
                ax.text(0.97, 0.32, "\n".join(lines), transform=ax.transAxes,
                        ha="right", va="top", fontsize=7, color="#333333",
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  alpha=0.92, edgecolor='lightgray'))
            except Exception as e:
                print(f"WARNING: roc: DeLong 计算失败（{e}）", file=sys.stderr)
        else:
            print("WARNING: roc: --compare 需要 labels（0/1 数组）+ 每条曲线含原始 "
                  "scores 数组（同一样本多模型）——只有 fpr/tpr 曲线时无法做 DeLong",
                  file=sys.stderr)

    # Diagonal reference line
    if diagonal:
        ax.plot([0, 1], [0, 1], '--', color='gray', alpha=0.5, linewidth=1, zorder=1)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect('equal')
    ax.xaxis.grid(True, alpha=theme["grid_alpha"], linestyle='--')


def gen_stacked_bar(data, ax, theme, cjk_fp, **kwargs):
    """Stacked bar chart for compositional data (e.g., subgroup proportions)."""
    labels = data.get("labels", data.get("x", []))
    series = data.get("series", data.get("datasets", {}))
    percentage = data.get("percentage", False)  # normalize to 100%
    show_total = data.get("show_total", False)  # show total on top of each bar
    errors = data.get("errors", None)  # optional error bars for totals
    use_hatch = kwargs.get("hatch", False)

    n_groups = len(labels)
    x = np.arange(n_groups)
    colors = theme["colors"]
    bottoms = np.zeros(n_groups)

    for i, (name, values) in enumerate(series.items()):
        vals = np.array(values, dtype=float)
        c = colors[i % len(colors)]
        hatch_val = HATCH_PATTERNS[i % len(HATCH_PATTERNS)] if use_hatch else None
        bars = ax.bar(x, vals, 0.65, bottom=bottoms, color=c,
                      edgecolor='black' if use_hatch else 'white',
                      linewidth=0.6 if use_hatch else 0.5,
                      hatch=hatch_val, label=name, zorder=2)

        # Value labels inside bars (only for segments > 5% of total)
        totals = sum(np.array(s, dtype=float) for s in series.values())
        for j, (v, total) in enumerate(zip(vals, totals)):
            if total > 0 and v / total > 0.05:  # only label segments > 5%
                ax.text(x[j], bottoms[j] + v / 2, f'{v:.1f}' if not percentage else f'{v/total*100:.1f}%',
                        ha='center', va='center', fontsize=7, color='white', fontweight='bold',
                        zorder=3)

        bottoms += vals

    # Total labels on top
    if show_total:
        for j in range(n_groups):
            total = bottoms[j]
            ax.text(x[j], total + 0.5, f'N={total:.0f}', ha='center', va='bottom',
                    fontsize=7, color='#333333', fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=theme["font_size"] - 1,
                       fontproperties=cjk_fp if cjk_fp and any(has_cjk(l) for l in labels) else None)

    if percentage:
        ax.set_ylim(0, max(bottoms) * 1.1)


def gen_dual_axis(data, ax, theme, cjk_fp, **kwargs):
    """Dual Y-axis line chart for comparing two metrics on different scales."""
    labels = data.get("labels", data.get("x", []))
    left_series = data.get("left", data.get("y1", {}))  # {"CRP (mg/L)": [5, 8, 12, ...]}
    right_series = data.get("right", data.get("y2", {}))  # {"DAS28": [3.2, 4.1, 5.6, ...]}
    left_errors = data.get("left_errors", data.get("y1_errors", {}))
    right_errors = data.get("right_errors", data.get("y2_errors", {}))
    left_ylabel = data.get("left_ylabel", "")
    right_ylabel = data.get("right_ylabel", "")

    def _check_series_dict(sd, which):
        if not isinstance(sd, dict):
            raise ValueError(f"dual_axis: {which} must be a dict of {{series_name: [values]}}")
        for k, v in sd.items():
            if not isinstance(v, (list, tuple)) or not all(isinstance(x, (int, float)) for x in v):
                raise ValueError(
                    f"dual_axis: {which}['{k}'] must be a numeric list. "
                    f"Wrong format? Use {{\"{which}\": {{\"系列名\": [值, ...]}}}} — not "
                    f"{{\"name\": ..., \"values\": ...}}.")
    _check_series_dict(left_series, "left")
    _check_series_dict(right_series, "right")

    markers = ['o', 's', 'D', '^', 'v', 'p', '*', 'h']
    x = np.arange(len(labels)) if not any(isinstance(l, (int, float)) for l in labels) else np.array(labels, dtype=float)

    # Create second axis
    ax2 = ax.twinx()

    # Plot left axis series
    for i, (name, values) in enumerate(left_series.items()):
        c = theme["colors"][i % len(theme["colors"])]
        mk = markers[i % len(markers)]
        ax.plot(x, values, color=c, marker=mk, markersize=6, linewidth=2, label=name, zorder=3)
        if name in left_errors and left_errors[name]:
            errs = left_errors[name]
            lower = [v - e for v, e in zip(values, errs)]
            upper = [v + e for v, e in zip(values, errs)]
            ax.fill_between(x, lower, upper, color=c, alpha=0.15, zorder=2)

    # Plot right axis series
    right_colors = ['#D55E00', '#CC79A7', '#0072B2', '#009E73', '#F0E442']  # distinct from left
    if theme.get("colorblind_safe"):
        # Use different Okabe-Ito colors for right axis
        offset = len(left_series)
        right_colors = [theme["colors"][(offset + j) % len(theme["colors"])] for j in range(5)]

    for i, (name, values) in enumerate(right_series.items()):
        c = right_colors[i % len(right_colors)]
        mk = markers[(len(left_series) + i) % len(markers)]
        ax2.plot(x, values, color=c, marker=mk, markersize=6, linewidth=2,
                 linestyle='--', label=name, zorder=3)
        if name in right_errors and right_errors[name]:
            errs = right_errors[name]
            lower = [v - e for v, e in zip(values, errs)]
            upper = [v + e for v, e in zip(values, errs)]
            ax2.fill_between(x, lower, upper, color=c, alpha=0.15, zorder=2)

    # Style right axis
    ax2.spines['right'].set_visible(True)
    ax2.tick_params(axis='y', labelsize=theme["font_size"] - 1)
    ax2.grid(False)  # no grid on right axis

    # Set x-axis labels
    if not any(isinstance(l, (int, float)) for l in labels):
        ax.set_xticks(x)
        use_cjk = cjk_fp and any(has_cjk(l) for l in labels)
        ax.set_xticklabels(labels, fontsize=theme["font_size"] - 1,
                           fontproperties=cjk_fp if use_cjk else None)

    # Axis labels
    if left_ylabel:
        ax.set_ylabel(left_ylabel, fontsize=theme["font_size"],
                      fontproperties=cjk_fp if cjk_fp and has_cjk(left_ylabel) else None)
        _ensure_ylabel_clear(ax)
    if right_ylabel:
        ax2.set_ylabel(right_ylabel, fontsize=theme["font_size"],
                       fontproperties=cjk_fp if cjk_fp and has_cjk(right_ylabel) else None)
        _ensure_ylabel_clear(ax2)

    # Combine legends from both axes
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=theme["font_size"] - 1,
              loc='best', framealpha=0.9, prop=cjk_fp if cjk_fp else None)

    # Store ax2 reference for downstream use
    return ax2


def gen_composite(data, ax, theme, cjk_fp, **kwargs):
    """Multi-panel composite figure (e.g., Panel A + B + C for journal figures).

    JSON format:
    {
      "layout": [rows, cols],  // e.g. [1, 3] or [2, 2]
      "panels": [
        {
          "title": "Panel A: ...",
          "type": "bar",        // any chart type from GENERATORS
          "data": { ... },      // data for that chart type
          "xlabel": "...", "ylabel": "...",
          "pos": [row, col]     // grid position (0-indexed)
        },
        ...
      ]
    }
    """
    import matplotlib.gridspec as gridspec

    layout = data.get("layout", [1, 2])
    n_rows, n_cols = layout[0], layout[1]
    panels = data.get("panels", [])

    if not panels:
        return None

    fig = ax.figure
    # Clear the default axis created by plt.subplots
    ax.remove()

    gs = gridspec.GridSpec(n_rows, n_cols, figure=fig,
                           hspace=0.35, wspace=0.3,
                           left=0.08, right=0.95, top=0.92, bottom=0.08)

    for panel in panels:
        pos = panel.get("pos", [0, 0])
        panel_type = panel.get("type", "bar")
        panel_data = panel.get("data", {})

        sub_ax = fig.add_subplot(gs[pos[0], pos[1]])

        # Get the generator function
        gen_func = GENERATORS.get(panel_type)
        if gen_func is None:
            sub_ax.text(0.5, 0.5, f"Unknown type: {panel_type}",
                        ha='center', va='center', transform=sub_ax.transAxes)
            continue

        # Pass through relevant kwargs
        panel_kwargs = {
            "show_values": panel.get("show_values", kwargs.get("show_values", False)),
            "trend": panel.get("trend", kwargs.get("trend", True)),
            # B3(v2.7)：hbar/horizontal_bar 面板自动横排（与主入口同规则；实战坑：composite
            # 内 hbar 被当竖 bar 渲染，用户被迫改用 bar+horizontal 绕行）
            "horizontal": panel.get("horizontal", False)
                          or panel_type in ("hbar", "horizontal_bar"),
            "hatch": panel.get("hatch", False),
            "alternate": panel.get("alternate", False),
            "show_ratio": panel.get("show_ratio", False),
            "cmap": panel.get("cmap", kwargs.get("cmap")),
            "vmin": panel.get("vmin", kwargs.get("vmin")),
            "vmax": panel.get("vmax", kwargs.get("vmax")),
        }

        extra = gen_func(panel_data, sub_ax, theme, cjk_fp, **panel_kwargs)
        apply_base_style(sub_ax, theme)

        # Panel-specific labels
        ptitle = panel.get("title", "")
        if ptitle:
            sub_ax.set_title(ptitle, fontsize=theme["font_size"], fontweight='bold', pad=8,
                             fontproperties=cjk_fp if cjk_fp and has_cjk(ptitle) else None)
        if panel.get("xlabel"):
            sub_ax.set_xlabel(panel["xlabel"], fontsize=theme["font_size"] - 1,
                              fontproperties=cjk_fp if cjk_fp and has_cjk(panel["xlabel"]) else None)
        if panel.get("ylabel"):
            sub_ax.set_ylabel(panel["ylabel"], fontsize=theme["font_size"] - 1,
                              fontproperties=cjk_fp if cjk_fp and has_cjk(panel["ylabel"]) else None)
            _ensure_ylabel_clear(sub_ax)

        # Legend for panel
        show_legend = panel.get("legend", True)
        if show_legend and sub_ax.get_legend_handles_labels()[1]:
            sub_ax.legend(fontsize=theme["font_size"] - 2, loc='best', framealpha=0.9,
                          prop=cjk_fp if cjk_fp else None)

        # Colorbar for heatmap panels
        if extra is not None and hasattr(extra, 'get_cmap'):
            cbar = fig.colorbar(extra, ax=sub_ax, shrink=0.8)

    return "composite"  # signal to main() that figure is already built


def gen_diagram(data, ax, theme, cjk_fp, **kwargs):
    """Architecture/flow diagram with colored blocks, arrows, and groupings.

    JSON format:
    {
      "background": "light",  // always light (white) for publication
      "blocks": [
        {"id": "A", "label": "Input", "x": 0, "y": 0, "w": 2, "h": 1,
         "color": "#56B4E9", "shape": "round"},  // shape: "round" (default) or "rect"
        ...
      ],
      "arrows": [
        {"from": "A", "to": "B", "label": "flow", "style": "->"},
        ...
      ],
      "groups": [
        {"blocks": ["A", "B"], "label": "Phase 1", "color": "#009E73", "style": "dashed"},
        ...
      ],
      "annotations": [
        {"text": "Step 1: predict", "x": 1, "y": -1, "fontsize": 9, "color": "#E69F00"},
        ...
      ]
    }
    """
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
    from matplotlib.lines import Line2D

    blocks = data.get("blocks", [])
    arrows = data.get("arrows", [])
    groups = data.get("groups", [])
    annotations = data.get("annotations", [])
    bg = data.get("background", "light")

    text_color = '#1a1a1a'
    arrow_color = '#555555'

    # Build block lookup
    block_map = {}
    for b in blocks:
        block_map[b["id"]] = b

    # Draw group backgrounds first (behind blocks)
    for grp in groups:
        grp_blocks = grp.get("blocks", [])
        if not grp_blocks:
            continue
        # Calculate bounding box of grouped blocks
        xs_min, xs_max = [], []
        ys_min, ys_max = [], []
        for bid in grp_blocks:
            if bid in block_map:
                b = block_map[bid]
                xs_min.append(b["x"])
                xs_max.append(b["x"] + b["w"])
                ys_min.append(b["y"])
                ys_max.append(b["y"] + b["h"])
        if not xs_min:
            continue
        pad = 0.3
        gx, gy = min(xs_min) - pad, min(ys_min) - pad
        gw, gh = max(xs_max) - min(xs_min) + 2 * pad, max(ys_max) - min(ys_min) + 2 * pad
        grp_color = grp.get("color", "#888888")
        grp_style = grp.get("style", "dashed")
        rect = Rectangle((gx, gy), gw, gh, linewidth=2,
                         edgecolor=grp_color, facecolor='none',
                         linestyle=grp_style, alpha=0.8)
        ax.add_patch(rect)
        # Group label
        if grp.get("label"):
            ax.text(gx + 0.15, gy + gh - 0.15, grp["label"],
                    fontsize=theme["font_size"] - 1, color=grp_color,
                    fontweight='bold', va='top', ha='left',
                    fontproperties=cjk_fp if cjk_fp and has_cjk(grp["label"]) else None)

    # Draw blocks
    for b in blocks:
        bx, by = b["x"], b["y"]
        bw, bh = b["w"], b["h"]
        bc = b.get("color", theme["colors"][0])
        label = b.get("label", b["id"])
        shape = b.get("shape", "round")
        sub_label = b.get("sublabel", None)  # smaller text below main label

        if shape == "rect":
            patch = FancyBboxPatch((bx, by), bw, bh,
                                   boxstyle="square,pad=0",
                                   facecolor=bc, edgecolor=bc,
                                   linewidth=1.5, alpha=0.85)
        else:
            patch = FancyBboxPatch((bx, by), bw, bh,
                                   boxstyle="round,pad=0.1",
                                   facecolor=bc, edgecolor='white',
                                   linewidth=1.2, alpha=0.9)
        ax.add_patch(patch)

        # Block label (centered)
        label_y = by + bh / 2
        if sub_label:
            label_y = by + bh * 0.65
        ax.text(bx + bw / 2, label_y, label,
                ha='center', va='center', fontsize=theme["font_size"],
                color='white', fontweight='bold',
                fontproperties=cjk_fp if cjk_fp and has_cjk(label) else None)
        if sub_label:
            ax.text(bx + bw / 2, by + bh * 0.3, sub_label,
                    ha='center', va='center', fontsize=theme["font_size"] - 2,
                    color='white', alpha=0.85,
                    fontproperties=cjk_fp if cjk_fp and has_cjk(sub_label) else None)

    # Draw arrows
    for arr in arrows:
        from_id = arr["from"]
        to_id = arr["to"]
        if from_id not in block_map or to_id not in block_map:
            continue
        fb, tb = block_map[from_id], block_map[to_id]

        # Calculate connection points (edge of blocks facing each other)
        fx_center = fb["x"] + fb["w"] / 2
        fy_center = fb["y"] + fb["h"] / 2
        tx_center = tb["x"] + tb["w"] / 2
        ty_center = tb["y"] + tb["h"] / 2

        # Determine arrow start/end at block edges
        if abs(fx_center - tx_center) > abs(fy_center - ty_center):
            # Horizontal connection
            if fx_center < tx_center:
                start = (fb["x"] + fb["w"], fy_center)
                end = (tb["x"], ty_center)
            else:
                start = (fb["x"], fy_center)
                end = (tb["x"] + tb["w"], ty_center)
        else:
            # Vertical connection
            if fy_center < ty_center:
                start = (fx_center, fb["y"] + fb["h"])
                end = (tx_center, tb["y"])
            else:
                start = (fx_center, fb["y"])
                end = (tx_center, tb["y"] + tb["h"])

        arr_style = arr.get("style", "->")
        arr_color = arr.get("color", arrow_color)
        connection_style = f"arc3,rad={arr.get('rad', 0)}"

        arrow = FancyArrowPatch(start, end,
                                arrowstyle=arr_style,
                                connectionstyle=connection_style,
                                color=arr_color, linewidth=1.5,
                                mutation_scale=15)
        ax.add_patch(arrow)

        # Arrow label
        if arr.get("label"):
            mid_x = (start[0] + end[0]) / 2
            mid_y = (start[1] + end[1]) / 2
            ax.text(mid_x, mid_y + 0.15, arr["label"],
                    ha='center', va='bottom', fontsize=theme["font_size"] - 2,
                    color=text_color,
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                              alpha=0.8, edgecolor='none'),
                    fontproperties=cjk_fp if cjk_fp and has_cjk(arr["label"]) else None)

    # Draw annotations
    for ann in annotations:
        ax.text(ann["x"], ann["y"], ann["text"],
                ha=ann.get("ha", 'center'), va=ann.get("va", 'center'),
                fontsize=ann.get("fontsize", theme["font_size"]),
                color=ann.get("color", text_color),
                fontweight=ann.get("weight", 'normal'),
                fontproperties=cjk_fp if cjk_fp and has_cjk(ann["text"]) else None)

    # Set up axis limits
    all_x = [b["x"] + b["w"] for b in blocks] + [b["x"] for b in blocks]
    all_y = [b["y"] + b["h"] for b in blocks] + [b["y"] for b in blocks]
    if all_x and all_y:
        ax.set_xlim(min(all_x) - 1, max(all_x) + 1)
        ax.set_ylim(min(all_y) - 1.5, max(all_y) + 1.5)

    ax.set_aspect('equal')
    ax.axis('off')

    return "diagram"


# ── PRISMA 2020 flow diagram (v2.1) ───────────────────────────────────

PRISMA_LABELS = {
    "en": {
        "identification": "Identification", "screening": "Screening", "included": "Included",
        "identified": "Records identified from\ndatabases",
        "duplicates": "Records removed before\nscreening (duplicates)",
        "screened": "Records screened",
        "excluded": "Records excluded",
        "sought": "Reports sought for\nretrieval",
        "not_retrieved": "Reports not retrieved",
        "assessed": "Reports assessed for\neligibility",
        "reasons": "Reports excluded:",
        "included_box": "Studies included in\nreview",
    },
    "zh": {
        "identification": "识别", "screening": "筛选", "included": "纳入",
        "identified": "数据库检索获得的\n记录",
        "duplicates": "初筛前剔除的记录\n（重复文献）",
        "screened": "初筛的记录",
        "excluded": "初筛排除",
        "sought": "寻求获取的报告",
        "not_retrieved": "未能获取的报告",
        "assessed": "进行合格性评估\n的报告",
        "reasons": "排除的报告：",
        "included_box": "纳入综述的研究",
    },
}


def gen_prisma(data, ax, theme, cjk_fp, **kwargs):
    """PRISMA 2020 systematic-review flow diagram.

    JSON format (counts must add up; validate_data() gates arithmetic):
    {
      "records_identified": 128,       // required
      "duplicates_removed": 23,
      "records_screened": 105,         // default: identified - duplicates
      "records_excluded": 61,
      "reports_sought": 44,            // default: screened - excluded
      "reports_not_retrieved": 3,
      "reports_assessed": 41,          // default: sought - not_retrieved
      "exclusion_reasons": {"Wrong population": 5, "Wrong intervention": 7},
      "studies_included": 25,          // required
      "lang": "en"                     // or "zh" (standard Chinese wording)
    }
    Layout: PRISMA 2020 three-phase spine (Identification / Screening /
    Included) with exclusion boxes to the right, per the official template.
    """
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    lang = data.get("lang", "en")
    L = PRISMA_LABELS.get(lang, PRISMA_LABELS["en"])

    def _n(key):
        v = data.get(key)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0

    identified = _n("records_identified")
    dup = _n("duplicates_removed")
    screened = data.get("records_screened")
    screened = (identified - dup) if not isinstance(screened, int) else screened
    excluded = _n("records_excluded")
    sought = data.get("reports_sought")
    sought = (screened - excluded) if not isinstance(sought, int) else sought
    not_ret = _n("reports_not_retrieved")
    assessed = data.get("reports_assessed")
    assessed = (sought - not_ret) if not isinstance(assessed, int) else assessed
    reasons = data.get("exclusion_reasons") or {}
    included = _n("studies_included")

    spine_color = theme["colors"][0]
    final_color = theme["colors"][1] if len(theme["colors"]) > 1 else spine_color
    side_face, side_edge, text_color = "#F2F2F2", "#8A8A8A", "#1a1a1a"
    arrow_color = "#555555"
    fs = theme["font_size"]

    def _fp(*texts):
        return cjk_fp if cjk_fp and any(has_cjk(t) for t in texts) else None

    # ── geometry (data units; aspect equal) ──
    SW, BW = 4.6, 4.4                 # spine / side box widths
    SX, XX = 0.0, 7.4                 # x origins
    GAP = 0.78                        # vertical gap
    n_reasons = max(1, len(reasons))
    # 内容感知盒高：双行中文标签+计数行在固定盒高下会溢出框体——
    # 盒高 = 标签行数×行高 + 计数行 + 内边距，行高随字号缩放
    _lh = 0.62 * max(0.8, fs / 8.0)
    def _box_h(label):
        return max(1.15, (label.count(chr(10)) + 1) * _lh + 0.85)
    BH_BY = {n: _box_h(L["included_box"] if n == "included" else L[n])
             for n in ("identified", "screened", "sought", "assessed", "included")}
    BH = max(BH_BY.values())
    RH = max(BH, 0.95 + 0.42 * n_reasons * max(0.8, fs / 8.0))

    order = ["identified", "screened", "sought", "assessed", "included"]
    ys = {}
    top = 10.0
    y = top
    for name in order:
        ys[name] = y - BH_BY[name]
        y -= (BH_BY[name] + GAP)

    def _cy(name):
        return ys[name] + BH / 2

    side = {
        "duplicates": (ys["identified"] + ys["screened"]) / 2 + BH / 2 - BH,
        "excluded": (ys["screened"] + ys["sought"]) / 2 + BH / 2 - BH,
        "not_retrieved": (ys["sought"] + ys["assessed"]) / 2 + BH / 2 - BH,
    }
    show_dup = not (dup == 0 and "duplicates_removed" not in data)
    show_notret = not (not_ret == 0 and "reports_not_retrieved" not in data)
    # reasons box: top-anchored to the assessed row's midline, growing
    # downward — this leaves the sought/assessed slot free for the
    # not-retrieved side box (official PRISMA 2020 arrangement)
    y_reasons = ys["assessed"] + BH_BY["assessed"] * 0.5 - RH
    implied_excluded = max(assessed - included, 0)

    # ── limits (set early so side-box text can be measured in data units) ──
    xmin, ymin = SX - 2.3, min(ys["included"], y_reasons) - 1.1
    ymax = top + 0.75
    ax.set_xlim(xmin, XX + BW + 0.5)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    fig = ax.get_figure()
    # 主框文字实测自愈：盒高系数是估算可能低估——以最终几何实测文字高度，
    # 超出盒体就放大该盒并整体重排，迭代到全部装下（同侧框 auto-fit 思路）
    if fig is not None:
        for _round in range(4):
            fig.canvas.draw()
            _rend = fig.canvas.get_renderer()
            _inv = ax.transData.inverted()
            grew = False
            for _name in order:
                _label = L["included_box"] if _name == "included" else L[_name]
                _t = ax.text(0.5, 0.5, _label + "\n" + "n = 000",
                             fontsize=fs - 1, fontweight="bold",
                             fontproperties=_fp(_label))
                _need = _t.get_window_extent(renderer=_rend).transformed(_inv).height + 0.30
                _t.remove()
                if _need > BH_BY[_name] * 1.02:
                    BH_BY[_name] = _need
                    grew = True
            if not grew:
                break
            BH = max(BH_BY.values())
            RH = max(RH, BH)
            _y = top
            for _name in order:
                ys[_name] = _y - BH_BY[_name]
                _y -= (BH_BY[_name] + GAP)
            y_reasons = ys["assessed"] + BH_BY["assessed"] * 0.5 - RH
            ymin = min(ys["included"], y_reasons) - 1.1
            ax.set_ylim(ymin, ymax)


    # ── side-box auto-fit: measure the real rendered width of every side-box
    # line, widen the boxes to fit, and wrap reason lines only as a last
    # resort (growing the box height to match). The old fixed-width box let
    # long exclusion reasons spill outside the frame.
    BW_MAX = 7.2
    reason_items = [(str(r), n) for r, n in reasons.items()]
    item_display = {r: [f"· {r} (n = {n})"] for r, n in reason_items}
    specs = []
    if show_dup:
        specs.append((L["duplicates"], fs - 1, _fp(L["duplicates"])))
    specs.append((L["excluded"], fs - 1, _fp(L["excluded"])))
    if show_notret:
        specs.append((L["not_retrieved"], fs - 1, _fp(L["not_retrieved"])))
    specs.append((L["reasons"], fs - 1, _fp(L["reasons"])))
    for r, n in reason_items:
        specs.append((item_display[r][0], fs - 1.5, _fp(r, str(n))))

    if specs and fig is not None:
        # Iterate to a fixed point: set the final geometry FIRST, then
        # measure, because data-unit widths depend on xlim. Widening BW
        # changes the span, which changes the measurement — so each pass
        # measures under the span it proposes, until the width stops moving.
        widths = {}
        need = BW
        for _pass in range(3):
            ax.set_xlim(xmin, XX + BW + 0.5)
            ax.set_ylim(ymin, ymax)
            meas = [ax.text(XX + BW / 2, (ymin + ymax) / 2, txt, fontsize=fsize,
                            fontproperties=fp, alpha=0, zorder=-10)
                    for txt, fsize, fp in specs]
            fig.canvas.draw()
            ren = fig.canvas.get_renderer()
            inv = ax.transData.inverted()
            widths = {}
            for t, (txt, _f, _p) in zip(meas, specs):
                bb = t.get_window_extent(ren)
                widths[txt] = abs(inv.transform((bb.x1, bb.y1))[0]
                                  - inv.transform((bb.x0, bb.y0))[0])
                t.remove()
            need = max(widths.values()) + 0.7 if widths else BW
            BW_new = min(max(BW, need), BW_MAX)
            if BW_new == BW:
                break
            BW = BW_new
        if need > BW_MAX:
            import textwrap

            def _block_w(block, fsize, fp):
                t = ax.text(XX + BW / 2, (ymin + ymax) / 2, block, fontsize=fsize,
                            fontproperties=fp, alpha=0, zorder=-10)
                fig.canvas.draw()
                bb = t.get_window_extent(fig.canvas.get_renderer())
                t.remove()
                return abs(inv.transform((bb.x1, bb.y1))[0]
                           - inv.transform((bb.x0, bb.y0))[0])

            for r, n in reason_items:
                line = item_display[r][0]
                if widths.get(line, 0) + 0.7 > BW_MAX:
                    per = max(8, int(len(line) * (BW_MAX - 0.7) / max(widths[line], 1e-6)))
                    for _attempt in range(4):
                        wrapped = textwrap.wrap(line, per) or [line]
                        display = [wrapped[0]] + ["   " + s for s in wrapped[1:]]
                        if _block_w("\n".join(display), fs - 1.5,
                                    _fp(r, str(n))) + 0.7 <= BW_MAX:
                            break
                        per = max(6, int(per * 0.8))
                    item_display[r] = display
            extra = sum(len(v) - 1 for v in item_display.values())
            RH += 0.30 * extra
            y_reasons = ys["assessed"] + BH_BY["assessed"] * 0.5 - RH
        ymin = min(ys["included"], y_reasons) - 1.1
        ax.set_xlim(xmin, XX + BW + 0.5)
        ax.set_ylim(ymin, ymax)

    # grow two-line side boxes vertically if label + count overflow BH
    # (a wider canvas squeezes data-unit heights). Boxes grow symmetrically
    # around their center, so the arrow anchors (_scy) stay aligned.
    side_two = []
    if show_dup:
        side_two.append(("duplicates", L["duplicates"]))
    side_two.append(("excluded", L["excluded"]))
    if show_notret:
        side_two.append(("not_retrieved", L["not_retrieved"]))
    side_h = {k: BH for k, _ in side_two}
    if fig is not None:
        fig.canvas.draw()
        _ren = fig.canvas.get_renderer()
        _inv = ax.transData.inverted()

        def _text_h(text, fsize, fp):
            t = ax.text(XX + BW / 2, (ymin + ymax) / 2, text, fontsize=fsize,
                        fontproperties=fp, alpha=0, zorder=-10)
            fig.canvas.draw()
            bb = t.get_window_extent(fig.canvas.get_renderer())
            t.remove()
            return abs(_inv.transform((0, bb.y1))[1] - _inv.transform((0, bb.y0))[1])

        for key, lab in side_two:
            need = (_text_h(lab, fs - 1, _fp(lab))
                    + _text_h("n = 0", fs - 1.5, _fp("0")) + 0.52)
            side_h[key] = max(BH, need)

    # phase bands + rotated phase labels (canonical three-phase template,
    # left-rail style: zero collision with the vertical flow)
    phases = [("identification", ["identified"]),
              ("screening", ["screened", "sought", "assessed"]),
              ("included", ["included"])]
    for label, rows in phases:
        y0 = min(ys[r] for r in rows) - 0.42
        y1 = max(ys[r] + BH for r in rows) + 0.42
        ax.add_patch(FancyBboxPatch((SX - 0.45, y0), SW + 0.9, y1 - y0,
                                    boxstyle="round,pad=0.05", facecolor=spine_color,
                                    edgecolor="none", alpha=0.06, zorder=0))
        ax.text(SX - 0.95, (y0 + y1) / 2, L[label], ha="center", va="center",
                rotation=90, fontsize=fs, color="#555555", fontweight="bold",
                fontproperties=_fp(L[label]))

    def _main_box(name, label, count, color=None):
        c = color or spine_color
        _bh = BH_BY[name]
        ax.add_patch(FancyBboxPatch((SX, ys[name]), SW, _bh, boxstyle="round,pad=0.08",
                                    facecolor=c, edgecolor="white", linewidth=1.2,
                                    alpha=0.95, zorder=3))
        ax.text(SX + SW / 2, ys[name] + _bh * 0.68, label, ha="center", va="center",
                fontsize=fs - 1, color="white", fontweight="bold",
                fontproperties=_fp(label))
        ax.text(SX + SW / 2, ys[name] + _bh * 0.22, f"n = {count}", ha="center",
                va="center", fontsize=fs - 1.5, color="white",
                fontproperties=_fp(str(count)))

    def _side_box(y0, h, lines, counts=None):
        ax.add_patch(FancyBboxPatch((XX, y0), BW, h, boxstyle="round,pad=0.08",
                                    facecolor=side_face, edgecolor=side_edge,
                                    linewidth=1.0, zorder=3))
        if counts is None:
            label, count = lines
            ax.text(XX + BW / 2, y0 + h * 0.63, label, ha="center", va="center",
                    fontsize=fs - 1, color=text_color, fontproperties=_fp(label))
            ax.text(XX + BW / 2, y0 + h * 0.26, f"n = {count}", ha="center", va="center",
                    fontsize=fs - 1.5, color=text_color, fontproperties=_fp(str(count)))
        else:
            title, items = lines, counts
            ax.text(XX + BW / 2, y0 + h - 0.34, title, ha="center", va="center",
                    fontsize=fs - 1, color=text_color, fontweight="bold",
                    fontproperties=_fp(title))
            n_rows = sum(txt.count("\n") + 1 for txt, _ in items)
            step = (h - 0.62) / max(1, n_rows)
            yy = y0 + h - 0.34 - step
            for txt, n in items:
                ax.text(XX + BW / 2, yy, txt, ha="center", va="center",
                        fontsize=fs - 1.5, color=text_color,
                        fontproperties=_fp(str(n)))
                yy -= step * (txt.count("\n") + 1)

    def _arrow(x0, y0, x1, y1, lw=1.6):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="->",
                                     color=arrow_color, linewidth=lw,
                                     mutation_scale=14, zorder=2))

    # spine boxes + arrows
    _main_box("identified", L["identified"], identified)
    _main_box("screened", L["screened"], screened)
    _main_box("sought", L["sought"], sought)
    _main_box("assessed", L["assessed"], assessed)
    _main_box("included", L["included_box"], included, color=final_color)
    for a, b in zip(order, order[1:]):
        _arrow(SX + SW / 2, ys[a], SX + SW / 2, ys[b] + BH)

    # side boxes + arrows
    def _scy(key):
        return side[key] + BH / 2

    if show_dup:
        h = side_h["duplicates"]
        _side_box(side["duplicates"] + BH / 2 - h / 2, h, (L["duplicates"], dup))
        _arrow(SX + SW, _scy("duplicates"), XX, _scy("duplicates"), lw=1.4)
    h = side_h["excluded"]
    _side_box(side["excluded"] + BH / 2 - h / 2, h, (L["excluded"], excluded))
    _arrow(SX + SW, _scy("excluded"), XX, _scy("excluded"), lw=1.4)
    if show_notret:
        h = side_h["not_retrieved"]
        _side_box(side["not_retrieved"] + BH / 2 - h / 2, h, (L["not_retrieved"], not_ret))
        _arrow(SX + SW, _scy("not_retrieved"), XX, _scy("not_retrieved"), lw=1.4)
    if reasons:
        items = [("\n".join(item_display[r]), n) for r, n in reason_items]
        _side_box(y_reasons, RH, L["reasons"], items)
    else:
        _side_box(y_reasons, BH, (L["reasons"], implied_excluded))
    _arrow(SX + SW, ys["assessed"] + BH_BY["assessed"] * 0.35, XX, ys["assessed"] + BH_BY["assessed"] * 0.35, lw=1.4)

    # content-aware figure proportions (limits were set pre-draw for the
    # side-box auto-fit; BW/y_reasons carry the auto-fitted values)
    xmax = XX + BW + 0.5
    ymin = min(ys["included"], y_reasons) - 1.1
    if fig is not None:
        span_h, span_w = ymax - ymin, xmax - xmin
        fig_w = fig.get_size_inches()[0]
        fig.set_size_inches(fig_w, max(4.0, fig_w * (span_h / span_w) * 0.92))

    return "diagram"

# ── Registry ───────────────────────────────────────────────────────────

GENERATORS = {
    "bar": gen_bar,
    "grouped_bar": gen_bar,
    "hbar": gen_bar,
    "horizontal_bar": gen_bar,
    "stacked_bar": gen_stacked_bar,
    "heatmap": gen_heatmap,
    "scatter": gen_scatter,
    "line": gen_line,
    "dual_axis": gen_dual_axis,
    "box": gen_box,
    "boxplot": gen_box,
    "forest": gen_forest,
    "km": gen_km,
    "survival": gen_km,
    "roc": gen_roc,
    "violin": gen_violin,
    "composite": gen_composite,
    "diagram": gen_diagram,
    "prisma": gen_prisma,
}
if _afcharts is not None:
    GENERATORS.update(_afcharts.EXTRA_GENERATORS)
    DEMO_DATA.update(_afcharts.EXTRA_DEMO_DATA)

_EXC_ZH = {
    "KeyError": "缺少必需字段",
    "BadZipFile": "文件不是有效的压缩/xlsx 格式",
    "JSONDecodeError": "不是合法的 JSON 文本",
    "ValueError": "数值/格式不符合要求",
    "FileNotFoundError": "文件不存在或路径不对",
    "PermissionError": "文件被占用或没有写入权限",
    "UnicodeDecodeError": "文件编码不是 UTF-8/ASCII（请转存为 UTF-8）",
    "TypeError": "数据类型不匹配",
    "IndexError": "数据行/列数量不足",
    # v2.5 扩充：底层库常见异常中文化（评估 R 处方——英文异常名仍保留在括号内可搜索）
    "MemoryError": "数据规模超出可用内存（请减小数据量或分批处理）",
    "OverflowError": "数值溢出（数据量级过大或含极端值）",
    "ZeroDivisionError": "出现除零（数据退化：全为常数或完全相同）",
    "ParserError": "CSV/表格解析失败（行列数不齐或格式错乱）",
    "InvalidFileException": "不是有效的 xlsx 文件（或已损坏）",
    "AttributeError": "数据结构与该图型要求不符",
    "ModuleNotFoundError": "缺少依赖库（按提示 pip install 即可）",
    "IsADirectoryError": "给的是目录路径，需要的是文件",
    "StopIteration": "数据为空或已耗尽（检查文件内容是否为空）",
}


def _zh_exception(e: BaseException) -> str:
    """异常消息中文化：类名映射 + 底层消息保留（便于搜索）。"""
    name = type(e).__name__
    head = _EXC_ZH.get(name, f"{name}")
    return f"{head}（{name}: {e}）"


# ── 投稿精修（v2.5 --annotate / --legend-loc / --legend-outside）──────

_LEGEND_LOCS = {"best", "upper right", "upper left", "lower left", "lower right",
                "right", "center left", "center right", "lower center",
                "upper center", "center"}


def _parse_annotations(items):
    """解析 --annotate "x,y:文字" 列表 → [(x, y, 文字, 原串)]；语法错误即报 ValueError。"""
    out = []
    for raw in items or []:
        s = str(raw)
        if ":" not in s:
            raise ValueError(f'--annotate 语法为 "x,y:文字"（缺少冒号）：{raw}')
        coord, text = s.split(":", 1)
        parts = coord.split(",")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise ValueError(f'--annotate 坐标需为 "x,y"（数字或类别刻度标签）：{raw}')
        text = text.strip()
        if not text:
            raise ValueError(f"--annotate 注释文字不能为空：{raw}")
        out.append((parts[0].strip(), parts[1].strip(), text, s))
    return out


def _resolve_coord(axes, value, which):
    """注释坐标解析：数字直接用；非数字在类别轴刻度标签里查（返回刻度位置）。失败 None。"""
    s = str(value).strip()
    try:
        return float(s)
    except ValueError:
        pass
    if which == "x":
        labels, ticks = axes.get_xticklabels(), axes.get_xticks()
    else:
        labels, ticks = axes.get_yticklabels(), axes.get_yticks()
    for i, t in enumerate(labels):
        if t.get_text().strip() == s:
            try:
                return float(ticks[i])
            except (TypeError, ValueError, IndexError):
                return None
    return None


def _apply_annotations(fig, anns, theme, cjk_fp):
    """在主数据轴上放置箭头注释（审稿改稿刚需）。返回（可能新启用的）cjk_fp。

    - 目标轴选择：取"能解析全部注释坐标且坐标在轴范围内"的轴中数据元素最多者
      （km 双轴自动优先主图而非风险表；组合图自动选中对应面板）
    - 文字初始位：锚点黄金角环绕；复用 _declutter_texts 防重叠（引导线关闭，
      对应关系由 FancyArrowPatch 箭头承担，文字移动后箭头起点跟随重设）
    """
    if not anns:
        return cjk_fp
    import math as _m
    import matplotlib.patches as _mpatches

    def _try_axes(a):
        resolved = []
        # 排序后比较：兼容倒置轴（forest 的 y 轴自上而下，get_ylim() 返回 (大, 小)）
        xa, xb = sorted(a.get_xlim())
        ya, yb = sorted(a.get_ylim())
        for xs, ys, _t, _raw in anns:
            px = _resolve_coord(a, xs, "x")
            py = _resolve_coord(a, ys, "y")
            if px is None or py is None:
                return None
            if not (xa - 0.02 * (xb - xa) <= px <= xb + 0.02 * (xb - xa)):
                return None
            if not (ya - 0.02 * (yb - ya) <= py <= yb + 0.02 * (yb - ya)):
                return None
            resolved.append((px, py))
        return resolved

    def _data_score(a):
        # 曲线/散点/图像是主图特征；纯矩形（km 风险表条块）权重压低
        return (len(a.lines) * 10 + len(a.collections) * 10 + len(a.images) * 10
                + len(a.containers) * 5 + len(a.patches))

    target, resolved = None, None
    for a in sorted(fig.axes, key=_data_score, reverse=True):
        r = _try_axes(a)
        if r is not None:
            target, resolved = a, r
            break
    if target is None:
        a = fig.axes[0] if fig.axes else None
        detail = ""
        if a is not None:
            xl = [t.get_text() for t in a.get_xticklabels() if t.get_text()][:8]
            xa, xb = sorted(a.get_xlim())
            ya, yb = sorted(a.get_ylim())
            detail = (f"（x 轴范围 {xa:.4g}~{xb:.4g}"
                      + (f"，类别刻度: {','.join(xl)}" if xl else "")
                      + f"；y 轴范围 {ya:.4g}~{yb:.4g}）")
        print(f"ERROR: --annotate 无法定位坐标，请确认落在图表数据范围内{detail}",
              file=sys.stderr)
        sys.exit(1)

    # 注释含中文但 cjk_fp 未启用：提前补字体（declutter 中途 draw 不能出现度量失真）
    if cjk_fp is None and any(has_cjk(t) for _x, _y, t, _r in anns):
        try:
            cjk_fp, cjk_name = load_cjk_font(None)
            if cjk_fp:
                plt.rcParams['font.sans-serif'] = [cjk_name, 'DejaVu Sans'] \
                    + plt.rcParams['font.sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
                print(f"自动补启用中文字体: {cjk_name}（--annotate 含中文）", file=sys.stderr)
        except Exception:
            pass

    x0, x1 = target.get_xlim()
    y0, y1 = target.get_ylim()
    span = min(abs(x1 - x0), abs(y1 - y0)) or 1.0
    fs = theme["font_size"]
    texts, arrows, anchors = [], [], []
    for k, ((px, py), (_xs, _ys, txt, _raw)) in enumerate(zip(resolved, anns)):
        ang = 2.399 * k
        ox, oy = span * 0.07 * _m.cos(ang), span * 0.07 * _m.sin(ang)
        t = target.text(px + ox, py + oy, txt, fontsize=fs, ha="center", va="center",
                        color="#333333", zorder=8,
                        fontproperties=cjk_fp if cjk_fp and has_cjk(txt) else None)
        arr = _mpatches.FancyArrowPatch((px + ox, py + oy), (px, py),
                                        arrowstyle="-|>", mutation_scale=fs * 0.9,
                                        color="#555555", linewidth=0.9,
                                        shrinkA=fs * 0.55, shrinkB=1.5, zorder=7)
        target.add_patch(arr)
        texts.append(t)
        arrows.append(arr)
        anchors.append((px, py))
    # 复用散点标签防重叠（引导线阈值放大→不画，箭头已承担对应关系）
    if _afcharts is not None and len(texts) >= 2:
        _afcharts._declutter_texts(target, texts, anchors, leader_min_frac=10.0)
    for arr, t, (ax_, ay_) in zip(arrows, texts, anchors):
        tx, ty = t.get_position()
        arr.set_positions((tx, ty), (ax_, ay_))
    return cjk_fp


def _apply_legend_control(fig, loc=None, outside=False, theme=None, cjk_fp=None):
    """--legend-loc / --legend-outside：重定位既有图例（原位重建，保留标题/列数）。

    - ≥2 个轴带图例 + outside：合并为全图共享图例（右侧，同名图例项去重）
    - 单图例：outside 移到轴右侧；否则按 loc 九宫格重摆
    """
    if not loc and not outside:
        return
    entries = []
    for a in fig.axes:
        hs, ls = a.get_legend_handles_labels()
        leg = a.get_legend()
        title = leg.get_title().get_text() if leg is not None else ""
        ncols = getattr(leg, "_ncols", None) or getattr(leg, "_ncol", None) or 1
        if leg is not None:
            leg.remove()
        if hs:
            entries.append((a, hs, ls, title, int(ncols)))
    if not entries:
        print("WARNING: 图中本无图例（--legend-loc/--legend-outside 未生效）",
              file=sys.stderr)
        return
    fs = (theme or {}).get("font_size", 10) - 1
    if outside and len(entries) >= 2:
        seen, hs_all, ls_all = set(), [], []
        for _a, hs, ls, _t, _n in entries:
            for h, l in zip(hs, ls):
                if l not in seen:
                    seen.add(l)
                    hs_all.append(h)
                    ls_all.append(l)
        fig.legend(hs_all, ls_all, loc="center left", bbox_to_anchor=(1.0, 0.5),
                   framealpha=0.9, fontsize=fs, prop=cjk_fp if cjk_fp else None)
        print(f"已合并 {len(entries)} 个面板的图例为全图共享图例（右侧）", file=sys.stderr)
        return
    for a, hs, ls, title, ncols in entries:
        kw = {}
        if title:
            kw["title"] = title
        if ncols > 1:
            kw["ncols"] = ncols
        if outside:
            a.legend(hs, ls, loc="center left", bbox_to_anchor=(1.02, 0.5),
                     framealpha=0.9, fontsize=fs, prop=cjk_fp if cjk_fp else None, **kw)
        else:
            a.legend(hs, ls, loc=loc, framealpha=0.9, fontsize=fs,
                     prop=cjk_fp if cjk_fp else None, **kw)


# ── Batch（v2.3 --batch）───────────────────────────────────────────────

def _run_batch_items(items, manifest_path):
    """逐项独立进程渲染批量/流水线条目，完成后写汇总报告（--batch 与 --pipeline 共用）。"""
    results = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not all(k in item for k in ("type", "data", "out")):
            results.append({"index": i, "ok": False, "error": "缺少 type/data/out 字段"})
            print(f"[batch {i+1}/{len(items)}] FAIL: 缺少 type/data/out 字段", file=sys.stderr)
            continue
        argv = [sys.executable, os.path.abspath(__file__),
                "-t", str(item["type"]), "-d", str(item["data"]), "-o", str(item["out"])]
        for key, flag in (("title", "--title"), ("xlabel", "--xlabel"), ("ylabel", "--ylabel"),
                          ("theme", "--theme"), ("journal", "--journal"), ("column", "--column"),
                          ("stats", "--stats"), ("sheet", "--sheet"), ("risk_times", "--risk-times"),
                          ("legend_loc", "--legend-loc")):
            if item.get(key):
                argv.extend([flag, str(item[key])])
        for key, flag in (("alt", "--alt"), ("caption", "--caption"), ("egger", "--egger"),
                          ("compare", "--compare"), ("cjk", "--cjk"), ("hatch", "--hatch"),
                          ("show_values", "--show-values"), ("no_legend", "--no-legend"),
                          ("no_risk_table", "--no-risk-table"), ("area", "--area"),
                          ("legend_outside", "--legend-outside")):
            if item.get(key):
                argv.append(flag)
        for ann in (item.get("annotate") or []):
            argv.extend(["--annotate", str(ann)])
        for key, flag in (("dpi", "--dpi"), ("width", "--width"), ("height", "--height"),
                          ("timeout", "--timeout"), ("downsample", "--downsample")):
            if item.get(key):
                argv.extend([flag, str(item[key])])
        if item.get("multi_format"):
            argv.extend(["--multi-format", str(item["multi_format"])])
        elif item.get("format"):
            argv.extend(["--format", str(item["format"])])
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
            out_path = str(item["out"])
            _cands = [out_path, out_path + "." + str(item.get("format", "png"))]
            for _f in str(item.get("multi_format") or "").replace("，", ",").split(","):
                _f = _f.strip().lower()
                if _f:
                    _cands.append(out_path + "." + _f)
            ok = proc.returncode == 0 and any(os.path.exists(c) for c in _cands)
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ""
        except subprocess.TimeoutExpired:
            ok, tail = False, "超时（>300s）"
        results.append({"index": i, "out": str(item["out"]), "ok": ok, "stderr_tail": tail})
        print(f"[batch {i+1}/{len(items)}] {'OK' if ok else 'FAIL'}: {item['out']}",
              file=sys.stderr)
    n_ok = sum(1 for r in results if r["ok"])
    report = {"total": len(items), "ok": n_ok, "failed": len(items) - n_ok, "items": results}
    rpt_path = os.path.splitext(str(manifest_path))[0] + ".batch-report.json"
    try:
        with open(rpt_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"batch: {n_ok}/{len(items)} 成功，报告 {rpt_path}", file=sys.stderr)
    except OSError as e:
        print(f"WARNING: 批量报告写出失败：{e}", file=sys.stderr)
    if n_ok < len(items):
        sys.exit(2)


def cmd_pipeline(pipeline_path):
    """--pipeline：YAML/JSON 多图流水线（--batch 升级版，支持 defaults 全局默认）。

    结构（YAML 示例）：
        defaults:
          theme: glm
          dpi: 600
        figures:
          - type: km
            data: survival.json
            out: fig1_km
            title: 总生存曲线
    顶层直接写列表 = 无全局默认的精简写法。相对路径（data/out）相对
    流水线文件所在目录解析；条目键与 --batch 单项一致（另支持 multi_format）。
    """
    ext = os.path.splitext(str(pipeline_path))[1].lower()
    if ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            print("ERROR: YAML 流水线需要 PyYAML —— 先运行 pip install pyyaml；"
                  "或改用 JSON 流水线 / --batch（无额外依赖）", file=sys.stderr)
            sys.exit(1)
        try:
            with open(pipeline_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        except Exception as e:
            print(f"ERROR: 流水线 YAML 解析失败：{e}", file=sys.stderr)
            sys.exit(1)
    elif ext == ".json":
        try:
            with open(pipeline_path, encoding="utf-8") as f:
                spec = json.load(f)
        except Exception as e:
            print(f"ERROR: 流水线 JSON 读取失败：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("ERROR: 流水线文件需为 .yaml / .yml / .json", file=sys.stderr)
        sys.exit(1)
    if isinstance(spec, list):
        defaults, figures = {}, spec
    elif isinstance(spec, dict):
        figures = spec.get("figures")
        defaults = spec.get("defaults") or {}
    else:
        figures, defaults = None, {}
    if not isinstance(figures, list) or not figures:
        print("ERROR: 流水线需为非空列表，或含非空 'figures' 列表的对象"
              "（可选 'defaults' 全局默认）", file=sys.stderr)
        sys.exit(1)
    if not isinstance(defaults, dict):
        print("ERROR: 'defaults' 必须是对象（键值对形式的全局默认）", file=sys.stderr)
        sys.exit(1)
    base_dir = os.path.dirname(os.path.abspath(pipeline_path))
    items = []
    for fig in figures:
        if not isinstance(fig, dict):
            print(f"ERROR: figures 里的条目必须是对象，得到 {type(fig).__name__}",
                  file=sys.stderr)
            sys.exit(1)
        merged = dict(defaults)
        merged.update(fig)
        for k in ("data", "out"):
            v = merged.get(k)
            if isinstance(v, str) and v and not os.path.isabs(v):
                merged[k] = os.path.normpath(os.path.join(base_dir, v))
        items.append(merged)
    print(f"pipeline: {len(items)} 张图（defaults: "
          f"{', '.join(sorted(defaults.keys())) if defaults else '无'}）", file=sys.stderr)
    _run_batch_items(items, pipeline_path)


def cmd_batch(manifest_path):
    """--batch：JSON 清单批量出图（逐项独立进程，互不干扰），完成后写汇总报告。"""
    try:
        with open(manifest_path, encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        print(f"ERROR: 批量清单读取失败：{e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(items, list) or not items:
        print("ERROR: 批量清单需为非空 JSON 数组（每项含 type/data/out）", file=sys.stderr)
        sys.exit(1)
    _run_batch_items(items, manifest_path)


# ── Main ───────────────────────────────────────────────────────────────

def _run_cox_forest(args):
    """B1(v2.7)：--stats cox —— 原始逐例生存数据自动拟合多因素 Cox 比例风险模型，
    以 HR[95%CI] 森林图输出（无效线 1.0 自动）。数据格式：
    JSON: {"time":[...], "event":[...], 其余顶层键=协变量}，或
          {"time":[...], "event":[...], "covariates": {"名": [...]}}
    CSV : 表头含时间/事件列（--cox-time/--cox-event 改名），其余数值列=协变量；
          二分类文本列自动 0/1 编码（stderr 注明参照组）；>2 类目请先数值化。"""
    import csv as _csv

    path = args.data
    if not path or not os.path.exists(path):
        print(f"ERROR: 找不到数据文件：{path}", file=sys.stderr)
        sys.exit(1)
    ext = os.path.splitext(path)[1].lower()
    time_col = args.cox_time
    event_col = args.cox_event

    def _is_num_list(seq):
        try:
            return all(np.isfinite(float(v)) for v in seq)
        except (TypeError, ValueError):
            return False

    def _fatal(msg):
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

    cov_raw = {}
    if ext == ".json":
        try:
            with open(path, encoding="utf-8-sig") as fh:
                d = json.load(fh)
        except Exception as exc:
            _fatal(f"JSON 解析失败：{exc}")
        if not isinstance(d, dict) or "time" not in d or "event" not in d:
            _fatal("Cox 数据 JSON 必须包含 time 与 event 两个数组（逐例一行）")
        if isinstance(d.get("covariates"), dict):
            cov_raw = {k: v for k, v in d["covariates"].items()}
        else:
            cov_raw = {k: v for k, v in d.items()
                       if k not in ("time", "event") and isinstance(v, list)}
    elif ext in (".csv", ".tsv", ".txt"):
        delim = "\t" if ext == ".tsv" else ","
        try:
            with open(path, encoding="utf-8-sig", newline="") as fh:
                rows = list(_csv.DictReader(fh, delimiter=delim))
        except Exception as exc:
            _fatal(f"CSV 解析失败：{exc}")
        if not rows:
            _fatal("CSV 为空")
        headers = list(rows[0].keys())
        for need in (time_col, event_col):
            if need not in headers:
                _fatal(f"CSV 缺少必需列「{need}」（现有列：{ '、'.join(headers) }）。"
                       f"可用 --cox-time/--cox-event 指定列名")
        def colvals(name):
            return [r[name] for r in rows]
        times_raw = colvals(time_col)
        events_raw = colvals(event_col)
        for name in headers:
            if name in (time_col, event_col):
                continue
            vals = [v for v in colvals(name) if str(v).strip() != ""]
            if _is_num_list(vals):
                cov_raw[name] = [float(v) for v in colvals(name)]
            else:
                uniq = sorted({str(v).strip() for v in vals})
                if len(uniq) == 2:
                    mapping = {uniq[0]: 0, uniq[1]: 1}
                    cov_raw[name] = [mapping.get(str(v).strip()) for v in colvals(name)]
                    if any(v is None for v in cov_raw[name]):
                        _fatal(f"列「{name}」存在无法识别的取值（允许：{'、'.join(uniq)}）")
                    print(f"Cox 编码：{name} → {uniq[0]}=0（参照）、{uniq[1]}=1"
                          f"（该变量 HR 为「{uniq[1]} 相对 {uniq[0]}」）", file=sys.stderr)
                elif len(uniq) > 2:
                    _fatal(f"列「{name}」有 {len(uniq)} 个类目（{ '、'.join(uniq[:4]) }…）——"
                           "多分类请先拆为哑变量（数值列）再提交")
    else:
        _fatal("--stats cox 支持 .json / .csv / .tsv 原始逐例数据；"
               "效应量森林图（已有 HR/OR 点估计）不要加 --stats cox")

    # 统一转数值
    if ext == ".json":
        if not _is_num_list(d["time"]) or not _is_num_list(d["event"]):
            _fatal("time/event 必须是数值数组（event 用 0/1）")
        times = [float(v) for v in d["time"]]
        events = [float(v) for v in d["event"]]
        for k, v in list(cov_raw.items()):
            if not _is_num_list(v):
                uniq = sorted({str(s) for s in v})
                if len(uniq) == 2:
                    cov_raw[k] = [1 if str(s) == uniq[1] else 0 for s in v]
                    print(f"Cox 编码：{k} → {uniq[0]}=0（参照）、{uniq[1]}=1", file=sys.stderr)
                else:
                    _fatal(f"协变量「{k}」不是数值数组（类目数 {len(uniq)}）——请先数值化")
        times = [float(v) for v in times]
        events = [float(v) for v in events]
        cov_raw = {k: [float(x) for x in v] for k, v in cov_raw.items()}
    else:
        try:
            times = [float(v) for v in times_raw]
            events = [float(v) for v in events_raw]
        except (TypeError, ValueError):
            _fatal("time/event 列存在非数值内容")

    if args.cox_cols:
        order = [c.strip() for c in str(args.cox_cols).split(",") if c.strip()]
        missing = [c for c in order if c not in cov_raw]
        if missing:
            _fatal(f"--cox-cols 指定了不存在的列：{'、'.join(missing)}")
        cov_raw = {c: cov_raw[c] for c in order}
    if not cov_raw:
        _fatal("没有可用的协变量列——Cox 多因素回归至少需要 1 个数值协变量")

    if _afstats is None:
        _fatal("统计模块 af_v23_stats 加载失败，无法执行 Cox 回归")
    names = list(cov_raw.keys())
    try:
        fit = _afstats.coxph_fit(times, events,
                                 np.column_stack([cov_raw[n] for n in names]),
                                 names=names)
    except ValueError as exc:
        _fatal(str(exc))
    ph = _afstats.cox_ph_test(fit)

    print(f"Cox 多因素回归（Efron 法）：n={fit['n']}，事件数={fit['n_events']}，"
          f"迭代 {fit['iterations']} 次{'收敛' if fit['converged'] else '未完全收敛'}，"
          f"loglik={fit['loglik']:.3f}", file=sys.stderr)
    print(f"{'协变量':<10}{'beta':>9}{'SE':>9}{'HR':>9}{'95%CI':>19}{'p':>10}{'PH-p':>9}",
          file=sys.stderr)
    for i, name in enumerate(names):
        ci = f"[{fit['hr_low'][i]:.3f},{fit['hr_high'][i]:.3f}]"
        print(f"{name:<10}{fit['beta'][i]:>9.4f}{fit['se'][i]:>9.4f}{fit['hr'][i]:>9.3f}"
              f"{ci:>19}{fit['p'][i]:>10.4f}{ph['p'][i]:>9.4f}", file=sys.stderr)
    low_ph = [n2 for n2, pv in zip(names, ph["p"]) if pv == pv and pv < 0.05]
    if low_ph:
        print(f"⚠ PH 提示：{'、'.join(low_ph)} 的比例风险假设近似检验 p<0.05——"
              "该变量效应可能随时间变化（可考虑分层/时变系数/分段 KM 核对）", file=sys.stderr)

    return {
        "labels": names,
        "estimates": [float(v) for v in fit["hr"]],
        "ci_low": [float(v) for v in fit["hr_low"]],
        "ci_high": [float(v) for v in fit["hr_high"]],
        "measure": "HR",
        "ref_line": 1.0,
        "title_note": f"Cox 多因素回归（n={fit['n']}, 事件={fit['n_events']}）",
    }


def main():
    parser = argparse.ArgumentParser(description="academic-figures：一条命令生成投稿级学术图表")
    parser.add_argument("--type", "-t", choices=list(GENERATORS.keys()),
                        help="图型（如 bar/box/violin/km/roc/forest/prisma，--demo 可看菜单）")
    parser.add_argument("--data", "-d", help="输入数据文件（.json / .csv / .tsv / .xlsx）")
    parser.add_argument("--sheet", default=None,
                        help="xlsx 的工作表名（默认取活动工作表）")
    parser.add_argument("--out", "-o", help="输出文件路径（.png / .svg / .pdf / .tiff / .eps）")
    parser.add_argument("--title", default="", help="图标题")
    parser.add_argument("--xlabel", default="", help="x 轴标签")
    parser.add_argument("--ylabel", default="", help="y 轴标签")
    parser.add_argument("--theme", default=None,
                        help="配色主题（默认 glm；--list-themes 查看全部）")
    parser.add_argument("--style", default=None, choices=["glm-hatch", "nature-clean"],
                        help="快捷风格：'glm-hatch' = GLM 黄蓝斜线风（theme glm + --hatch）；"
                             "'nature-clean' = 顶刊版式（Okabe-Ito 配色+去顶右框线+无网格+无框图例，v3.3）")
    parser.add_argument("--list-themes", action="store_true",
                        help="列出全部配色主题（含色卡预览）后退出")
    parser.add_argument("--theme-swatch", default=None, metavar="THEME",
                        help="渲染某主题的色卡预览图后退出")
    parser.add_argument("--demo", action="store_true",
                        help="交互演示：菜单选图型，用内置示例数据出图")
    parser.add_argument("--wizard", action="store_true",
                        help="选图向导：4 个问题生成完整命令；非交互环境打印决策树")
    parser.add_argument("--explain", default=None, metavar="CHART_TYPE",
                        help="打印某图型的用法说明与限制后退出")
    parser.add_argument("--suggest", action="store_true",
                        help="分析数据文件并推荐可用图型后退出")
    parser.add_argument("--quick", action="store_true",
                        help="一键出图：按数据自动选型并直接渲染（v3.1）")
    parser.add_argument("--cjk", action="store_true", help="启用中文字体（自动探测）")
    parser.add_argument("--cjk-font", default=None, help="指定中文字体文件路径")
    parser.add_argument("--width", type=float, default=None, help="图宽（英寸）")
    parser.add_argument("--height", type=float, default=None, help="图高（英寸）")
    parser.add_argument("--format", "-f", default=None, choices=["png", "svg", "pdf", "tiff", "eps"],
                        help="输出格式（默认按 --out 扩展名自动判断）")
    parser.add_argument("--multi-format", default=None, metavar="F1,F2,...",
                        help="一次输出多种格式（逗号分隔 png/svg/pdf/tiff/eps，兼容全角逗号）："
                             "文件名取 --out 去扩展名后逐格式拼接，如 -o fig1 --multi-format tiff,png,pdf "
                             "→ fig1.tiff/fig1.png/fig1.pdf；与 --format 同时给出时以本参数为准")
    parser.add_argument("--dpi", type=int, default=None,
                        help="位图 DPI（默认：线条图 600，照片类 300）")
    parser.add_argument("--legend", action="store_true", default=True, help="显示图例")
    parser.add_argument("--no-legend", action="store_true", help="隐藏图例")
    parser.add_argument("--show-values", action="store_true", help="在图元上标注数值")
    parser.add_argument("--trend", action="store_true", default=True, help="显示趋势线（散点图）")
    parser.add_argument("--no-trend", action="store_true", help="隐藏趋势线（散点图）")
    parser.add_argument("--cmap", default=None, help="热图配色映射（colormap）")
    parser.add_argument("--vmin", type=float, default=None, help="热图色阶下限")
    parser.add_argument("--vmax", type=float, default=None, help="热图色阶上限")
    parser.add_argument("--horizontal", action="store_true", help="水平柱状图（即 hbar）")
    parser.add_argument("--hatch", action="store_true", help="柱体加斜线填充（打印友好）")
    parser.add_argument("--alternate", action="store_true",
                        help="GLM 风格：单系列柱子交替前两种主题色")
    parser.add_argument("--show-ratio", action="store_true", help="分组柱上标注倍率（如 4.96x）")
    parser.add_argument("--ratio-base", type=int, default=0, help="倍率计算的基准系列序号（默认 0）")
    parser.add_argument("--stats", default=None, choices=["auto", "multi", "cox"],
                        help="box/violin 自动显著性标注：auto=各组 vs 第一组（Shapiro 定正态→"
                             "Welch t / Mann-Whitney U）；multi=全两两（正态→ANOVA+Tukey，"
                             "否则 Kruskal-Wallis+Dunn+Hochberg）。括号+星号自动绘制。"
                             "cox=仅 forest：原始逐例生存数据自动拟合多因素 Cox 比例风险模型，"
                             "输出 HR[95%%CI] 森林图+系数表+PH 假设近似检验")
    parser.add_argument("--timeout", type=float, default=None,
                        help="渲染看门狗预算（秒）：超时强制中断并给中文建议（exit 5）；"
                             "0=禁用；默认按图型与数据量自适应（30~1800s）")
    parser.add_argument("--downsample", type=int, default=None, metavar="N",
                        help="cluster_heatmap 行数超过 N 时等距采样到 N 行（确定性采样）")
    parser.add_argument("--size", default=None,
                        choices=["16:9", "4:5", "3:2", "1:1", "5:4", "9:16"],
                        help="画幅比例预设（宽:高）：16:9 演示/PPT、4:5 与 3:2 通用、"
                             "9:16 手机/社交竖版、1:1 方版。宽度仍由期刊预设/主题决定，"
                             "仅按比例推算高度")
    parser.add_argument("--cox-time", default="time",
                        help="--stats cox 时生存时间列名（默认 time）")
    parser.add_argument("--cox-event", default="event",
                        help="--stats cox 时事件列名（默认 event；0=删失 1=事件）")
    parser.add_argument("--cox-cols", default=None,
                        help="--stats cox 时协变量列（逗号分隔，默认除时间/事件外全部数值列；"
                             "顺序即森林图行序）")
    parser.add_argument("--alt", action="store_true",
                        help="输出旁生成无障碍描述文件（<输出名>.alt.txt）")
    parser.add_argument("--caption", action="store_true",
                        help="输出旁生成中英双语期刊式图注文件（<输出名>.caption.txt）")
    parser.add_argument("--sensitivity", action="store_true",
                        help="forest：留一法敏感性分析（省略单研究后的合并效应画在同一图下方；"
                             "需 se_list 或对称 CI 反推）")
    parser.add_argument("--no-median", dest="no_median", action="store_true",
                        help="km：关闭自动中位生存计算与标注")
    parser.add_argument("--compare", action="store_true",
                        help="roc：配对 DeLong 检验比较 >=2 个模型 AUC（需 labels + 各曲线 scores 原始分数）")
    parser.add_argument("--egger", action="store_true",
                        help="funnel：绘制 Egger 回归线并报告漏斗不对称检验")
    parser.add_argument("--area", action="store_true",
                        help="venn：按区域计数比例绘制（Euler 图），替代默认等圆示意")
    parser.add_argument("--annotate", action="append", default=None, metavar='"X,Y:文字"',
                        help="在数据坐标处加箭头注释，可重复使用；类别轴可用刻度标签"
                             "定位（如 --annotate \"3.2,5.1:p=0.01\" 或 \"对照组:显著上调\"）")
    parser.add_argument("--legend-loc", default=None, metavar="LOC",
                        help="图例位置：best/upper right/upper left/lower left/lower "
                             "right/right/center left/center right/center 等九宫格")
    parser.add_argument("--legend-outside", dest="legend_outside", action="store_true",
                        help="图例移到绘图区外侧；组合图自动合并为全图共享图例（右侧）")
    parser.add_argument("--no-risk-table", dest="no_risk_table", action="store_true",
                        help="km：关闭自动风险表（默认开启，位于主图下方）")
    def _risk_times_arg(v):
        try:
            out = [float(x) for x in str(v).replace("，", ",").split(",") if x.strip()]
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"风险表时间点 '{v}' 无法解析为数字（正确示例：2,6,10）")
        if not out:
            raise argparse.ArgumentTypeError("风险表时间点为空（正确示例：2,6,10）")
        return out
    parser.add_argument("--risk-times", default=None, type=_risk_times_arg,
                        metavar="T1,T2,...",
                        help="km：风险表显示时间点（逗号分隔数字；默认 0~最大随访等分 5 档）")
    parser.add_argument("--batch", default=None, metavar="FIGURES.json",
                        help="批量出图：JSON 清单（每项含 type/data/out，可带 title/theme/stats 等），"
                             "逐项渲染后写 .batch-report.json 汇总")
    parser.add_argument("--pipeline", default=None, metavar="ANALYSIS.yaml",
                        help="多图流水线（--batch 升级版）：YAML 或 JSON 描述一篇论文全部图表——"
                             "defaults 全局默认 + figures 逐图条目（type/data/out 必填，可覆盖默认），"
                             "一条命令批量渲染并写 .batch-report.json；相对路径相对流水线文件解析；"
                             "YAML 需先 pip install pyyaml（JSON 无额外依赖）")
    parser.add_argument("--verify", action="store_true",
                        help="对 PDF 输出做像素级文字重叠检查；发现重叠则退出码 2")
    parser.add_argument("--journal", default=None, choices=sorted(JOURNAL_PRESETS.keys()),
                        help="期刊预设（nature/lancet/science/cell/nejm/jama/ieee/cma/cn-core）："
                             "栏宽、字号、最小字号、字体；cma/cn-core 自动启用中文字体")
    parser.add_argument("--column", default="double", choices=["single", "double"],
                        help="--journal 的栏宽版式（默认 double 双栏）")

    args = parser.parse_args()

    if getattr(args, "multi_format", None):
        _req_fmts = []
        for _f in str(args.multi_format).replace("，", ",").split(","):
            _f = _f.strip().lower()
            if not _f:
                continue
            if _f not in ("png", "svg", "pdf", "tiff", "eps"):
                print(f"ERROR: --multi-format 不支持 '{_f}'。可用: png, svg, pdf, tiff, eps",
                      file=sys.stderr)
                sys.exit(1)
            if _f not in _req_fmts:
                _req_fmts.append(_f)
        if not _req_fmts:
            print("ERROR: --multi-format 为空。示例：--multi-format tiff,png,pdf", file=sys.stderr)
            sys.exit(1)
        args.multi_format = _req_fmts
        if args.format:
            print("WARNING: --format 与 --multi-format 同时给出，按 --multi-format 输出",
                  file=sys.stderr)

    if args.batch and args.pipeline:
        print("ERROR: --batch 与 --pipeline 只能二选一（--pipeline 是升级版，支持 YAML 与全局默认）",
              file=sys.stderr)
        sys.exit(1)
    if args.pipeline:
        cmd_pipeline(args.pipeline)
        sys.exit(0)
    if args.batch:
        cmd_batch(args.batch)
        sys.exit(0)

    if args.list_themes:
        cmd_list_themes()
        sys.exit(0)

    if args.theme_swatch:
        resolved = resolve_theme(args.theme_swatch)
        if not resolved:
            print(f"ERROR: 未知主题 '{args.theme_swatch}'。可用: {', '.join(THEME_ORDER)}", file=sys.stderr)
            sys.exit(1)
        out = args.out or (f"theme_{resolved}_swatch.png")
        cmd_theme_swatch(resolved, out)
        sys.exit(0)

    if args.explain:
        cmd_explain(args.explain)
        sys.exit(0)

    if args.suggest:
        if not args.data:
            parser.error("--suggest 需要同时提供 -d/--data")
        cmd_suggest(args.data)
        sys.exit(0)

    if getattr(args, "wizard", False):
        _run_wizard()
        sys.exit(0)

    # ── v3.1：--quick 一键出图（自动选型 → 复用主渲染管线）──
    if getattr(args, "quick", False):
        if not args.data:
            parser.error("--quick 需要 -d/--data 指向数据文件（不确定图型可先跑 --suggest）")
        try:
            _qdata = load_data(args.data)
        except Exception as _e:
            print(f"ERROR: cannot load '{args.data}': {_e}", file=sys.stderr)
            sys.exit(1)
        _recs = suggest_chart_type(_qdata)
        _best = _recs[0][1] if _recs else "bar"
        _alt = ", ".join(r[1] for r in _recs[1:3]) if _recs else "—"
        args.type = _best
        if not args.out:
            args.out = "quick_" + _best + ".png"
        print(f"--quick: 已按数据自动选择图型 {_best}（其他候选：{_alt}；"
              "打分明细见 --suggest）", file=sys.stderr)

    if args.demo:
        if not cmd_demo(args):
            sys.exit(1)
        if not args.type or not args.data or not args.out:
            print("ERROR: --demo 需要 --type/--data/--out", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.type or not args.data or not args.out:
            parser.error("必须提供 -t/--type、-d/--data、-o/--out（或用 --demo 交互模式）")

    if args.style == "glm-hatch":
        args.theme = "glm"
        args.hatch = True

    if args.style == "nature-clean":
        # ── v3.3：顶刊版式（设计语言包第一刀）——纯增量，默认行为零变化 ──
        args.theme = "okabe-ito"
        _STYLE_NO_GRID[0] = True
        plt.rcParams.update({
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 1.0,
            "legend.frameon": False,
            "grid.alpha": 0.0,
            "grid.linestyle": "-",
        })
        print("[style] nature-clean：Okabe-Ito 配色 + 去顶右框线 + 无网格 + 无框图例"
              "（Nature 系版式语言）", file=sys.stderr)

    if getattr(args, "area", False) and args.type != "venn":
        print("ERROR: --area 仅用于 venn（--type venn）。等圆模式为默认，无需参数。",
              file=sys.stderr)
        sys.exit(1)
    if getattr(args, "legend_loc", None):
        _loc = " ".join(args.legend_loc.strip().lower().replace("_", " ")
                        .replace("-", " ").split())
        if _loc not in _LEGEND_LOCS:
            print(f"ERROR: 未知图例位置 '{args.legend_loc}'。可用: best, upper right, "
                  "upper left, lower left, lower right, right, center left, "
                  "center right, lower center, upper center, center", file=sys.stderr)
            sys.exit(1)
        args.legend_loc = _loc
    try:
        annotations = _parse_annotations(args.annotate)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    theme_key = resolve_theme(args.theme)
    if not theme_key:
        print(f"ERROR: 未知主题 '{args.theme}'。运行 --list-themes 查看全部配色。", file=sys.stderr)
        sys.exit(1)
    if args.journal and args.theme is None and args.journal in JOURNAL_THEME:
        # v2.5 联动：--journal 期刊预设自动套同款配色（显式 --theme 优先）
        theme_key = JOURNAL_THEME[args.journal]
        print(f"配色已联动 {theme_key} 主题（显式 --theme 可覆盖）", file=sys.stderr)
    args.theme = theme_key
    theme = THEMES[theme_key]

    # ── v3.2：自动行为透明化（[auto] 前缀显式告知）──
    if args.journal and getattr(args, "width", None):
        print("[auto] --journal 锁定图宽，--width "
              f"{args.width} 已被忽略（--height 仍生效）", file=sys.stderr)
    if getattr(args, "verify", False):
        _fmt = os.path.splitext(str(args.out or ""))[1].lower()
        if _fmt and _fmt != ".pdf":
            print("[auto] --verify 仅对 PDF 输出生效；当前输出为 "
                  f"{_fmt or '无扩展名'}，本次不做像素级重叠检查", file=sys.stderr)
    if args.journal:
        preset = JOURNAL_PRESETS[args.journal]
        if preset.get("cjk_default"):
            args.cjk = True  # Chinese journals: CJK font on by default
        theme = dict(theme)
        w_in = preset["widths_mm"][args.column] / 25.4
        h_ratio = theme["figsize"][1] / theme["figsize"][0]
        theme["figsize"] = (w_in, w_in * h_ratio)
        theme["font_size"] = preset["font_size"]
        theme["dpi"] = preset["dpi"]
        if preset["font_family"] not in plt.rcParams['font.sans-serif']:
            plt.rcParams['font.sans-serif'].insert(0, preset["font_family"])
        print(f"期刊预设 {args.journal}（{args.column} 栏，宽 {w_in:.2f}in，"
              f"字体 {preset['font_family']} {preset['font_size']}pt，最小字号 {preset['min_text_size']}pt"
              f"— 可用 audit_pdf.py --min-size {preset['min_text_size']} 核查）", file=sys.stderr)
    if getattr(args, "size", None):
        rw, rh = (float(v) for v in args.size.split(":"))
        w_in, h_in = theme["figsize"]
        theme["figsize"] = (w_in, w_in * rh / rw)
        print(f"画幅预设 {args.size}：figsize {w_in:.2f}x{theme['figsize'][1]:.2f}in"
              f"（宽度不变，高度按比例）", file=sys.stderr)
    if args.stats == "cox":
        if args.type != "forest":
            print("ERROR: --stats cox 仅支持 forest 图型（原始生存数据→多因素 Cox→HR 森林图）。"
                  "其他图型的 --stats 请用 auto/multi。", file=sys.stderr)
            sys.exit(1)
        data = _run_cox_forest(args)
    else:
        data = load_data(args.data, chart_type=args.type, sheet=args.sheet)

    # ── A4(v2.8)+v3.1：cluster_heatmap 降采样（确定性等距采样；校验前执行）──
    # v3.1：行数>3000 且未给 --downsample 时自动采样到 2000 行并显著告知
    #（此前为致命错退出；评测 errorHandling 指出"缺乏自动建议参数尝试"）。
    if (args.type == "cluster_heatmap" and isinstance(data, dict)
            and isinstance(data.get("matrix"), list)):
        _m = data["matrix"]
        _n = len(_m)
        _ds = getattr(args, "downsample", None)
        if _n > 3000 and not _ds:
            _ds = 2000
            print(f"AUTO-DOWNSAMPLE: cluster_heatmap 行数 {_n} 超过硬上限 3000——"
                  "已自动等距采样到 2000 行（确定性采样；需要其他行数用 --downsample N）",
                  file=sys.stderr)
        if _ds and _n > _ds:
            _step = -(-_n // max(int(_ds), 1))
            _idx = list(range(0, _n, _step))
            data["matrix"] = [_m[i] for i in _idx]
            for _k in ("row_labels", "rows", "y_labels"):
                if isinstance(data.get(_k), list) and len(data[_k]) == _n:
                    data[_k] = [data[_k][i] for i in _idx]
            print(f"downsample: cluster_heatmap 行数 {_n} → {len(data['matrix'])}"
                  f"（等距采样，步长 {_step}）", file=sys.stderr)

    # ── v2.9：cluster_heatmap 行数预判（半限 1500 即预警，不等 3000 硬限）──
    for _adv in _preflight_advisories(data, args.type,
                                      getattr(args, "downsample", None)):
        print(f"WARNING: {_adv}", file=sys.stderr)

    # ── v2.9：JSON 字段名近似匹配告警（拼写错误前置提醒，非致命）──
    for _w in _field_nearmiss_warnings(data):
        print(f"WARNING: {_w}", file=sys.stderr)

    fatal_msgs, warn_msgs = validate_data(data, args.type)
    for w in warn_msgs:
        print(f"WARNING: {w}", file=sys.stderr)
    if fatal_msgs:
        for m in fatal_msgs:
            print(f"ERROR: {m}", file=sys.stderr)
        if any("CSV" in m or "csv" in m for m in fatal_msgs) or \
           any("error" in m.lower() and "bar" in m.lower() for m in fatal_msgs):
            print("HINT: CSV 不支持误差棒 → 改用 JSON 格式（见 --explain bar / 文档 §数据输入）",
                  file=sys.stderr)
        sys.exit(1)
    _memory_hint(data, args.type)
    # ── A1(v2.8)：看门狗武装（--timeout 覆盖自适应预算；0=禁用）──
    if args.timeout is None or args.timeout > 0:
        _watchdog_arm(args.type, data,
                      budget=None if args.timeout is None else float(args.timeout))
    cjk_fp = None
    # Auto-detect: scan displayable text for CJK chars
    def _scan_cjk(obj):
        if isinstance(obj, str):
            return has_cjk(obj)
        if isinstance(obj, dict):
            return any(_scan_cjk(k) for k in obj.keys()) or any(_scan_cjk(v) for v in obj.values())
        if isinstance(obj, (list, tuple)):
            return any(_scan_cjk(v) for v in obj)
        return False

    def _text_has_cjk():
        for t in [args.title, args.xlabel, args.ylabel]:
            if t and has_cjk(t):
                return True
        # Recursive scan catches CJK nested in composite panels/diagram text
        return _scan_cjk(data) if data else False
    _auto_cjk = _text_has_cjk()
    if args.cjk or args.cjk_font or _auto_cjk:
        cjk_fp, cjk_name = load_cjk_font(args.cjk_font)
        if cjk_name:
            plt.rcParams['font.sans-serif'] = [cjk_name, 'DejaVu Sans'] + plt.rcParams['font.sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        if cjk_fp:
            print(f"已加载中文字体: {cjk_name}", file=sys.stderr)
        else:
            print("WARNING: 未找到中文字体，中文可能显示为方框", file=sys.stderr)

    # Create figure（km 默认带自动风险表：主图 + 下方独立表轴）
    width = args.width if args.width else theme["figsize"][0]
    height = args.height if args.height else theme["figsize"][1]
    km_risk = False
    risk_axes = None
    if args.type in ("km", "survival") and not getattr(args, "no_risk_table", False):
        _g = data.get("groups", data.get("series")) if isinstance(data, dict) else None
        if isinstance(_g, dict) and _g:
            def _is_raw_km(v):
                if not isinstance(v, (list, tuple)) or len(v) == 0:
                    return False
                if isinstance(v[0], (list, tuple)):
                    if not all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in v[:8]):
                        return False
                    try:
                        seconds = [float(p[1]) for p in v[:8]]
                    except (TypeError, ValueError):
                        return False
                    return all(s in (0.0, 1.0) for s in seconds)
                return all(isinstance(x, (int, float)) for x in v[:5])
            try:
                km_risk = all(_is_raw_km(v) for v in _g.values())
            except Exception:
                km_risk = False
    if args.type == "cluster_heatmap" and isinstance(data, dict):
        _ch_rows = len(data.get("matrix", data.get("data", data.get("values"))) or [])
        height = max(height, min(_ch_rows * 0.16 + 1.0, 24.0))
    if args.type == "pca" and isinstance(data, dict):
        _pca_n = len(data.get("matrix") or [])
        _has_groups = bool(data.get("groups"))
        if not _has_groups and 0 < _pca_n:
            width = max(width, 8.5)
            height = max(height, 6.0)
    def _make_fig():
        """fig/ax/risk_axes 创建（km 风险表时主图+表轴双行）；A2 降级重建复用。"""
        if km_risk:
            _n_rows = len(data.get("groups", data.get("series", {})) or {})
            _rt_h = min(0.9, 0.34 + 0.24 * max(_n_rows, 1))
            _f, _axes = plt.subplots(
                2, 1, figsize=(width, height + _rt_h),
                gridspec_kw={"height_ratios": [3.4, _rt_h]})
            return _f, _axes[0], _axes[1]
        _f, _a = plt.subplots(figsize=(width, height))
        return _f, _a, None

    fig, ax, risk_axes = _make_fig()

    # Generate
    gen_func = GENERATORS[args.type]
    kwargs = {
        "show_values": args.show_values,
        "trend": args.trend and not args.no_trend,
        "cmap": args.cmap,
        "vmin": args.vmin,
        "vmax": args.vmax,
        "horizontal": args.horizontal or args.type in ("hbar", "horizontal_bar"),
        "hatch": args.hatch,
        "alternate": args.alternate,
        "show_ratio": args.show_ratio,
        "ratio_base": args.ratio_base,
        "stats_auto": args.stats == "auto",
        "stats_multi": args.stats == "multi",
        "roc_compare": getattr(args, "compare", False),
        "sensitivity": getattr(args, "sensitivity", False),
        "median_auto": not getattr(args, "no_median", False),
        "egger": getattr(args, "egger", False),
        "area_mode": getattr(args, "area", False),
        "risk_table": km_risk,
        "risk_axes": risk_axes if km_risk else None,
        "risk_times": getattr(args, "risk_times", None),
        "auto_cjk_hdr": bool(args.cjk) and args.type in ("km", "survival"),
    }
    _a2_degraded = False
    for _a2_try in (1, 2):
        try:
            extra = gen_func(data, ax, theme, cjk_fp, **kwargs)
            break
        except MemoryError:
            plt.close(fig)
            if _a2_try == 2:
                raise
            width, height = width * 0.85, height * 0.85
            fig, ax, risk_axes = _make_fig()
            kwargs["risk_axes"] = risk_axes if km_risk else None
            _a2_degraded = True
            print("WARNING: 渲染内存不足——已自动降级重试（图幅 ×0.85，输出 DPI 减半）",
                  file=sys.stderr)

    # composite/diagram manage their own axes and styling
    is_self_managed = extra in ("composite", "diagram")

    # Style (skip for self-managed types and dual_axis)
    if args.type not in ('dual_axis',) and not is_self_managed:
        apply_base_style(ax, theme)

    # Labels (skip for self-managed types like composite/diagram)
    if not is_self_managed:
        if args.title:
            title_text = args.title.replace('\\n', '\n')
            ax.set_title(title_text, fontsize=theme["font_size"] + 1, fontweight='bold', pad=12,
                         fontproperties=cjk_fp if cjk_fp and has_cjk(title_text) else None)
        if args.xlabel:
            ax.set_xlabel(args.xlabel, fontsize=theme["font_size"],
                          fontproperties=cjk_fp if cjk_fp and has_cjk(args.xlabel) else None)
        if args.ylabel:
            ax.set_ylabel(args.ylabel, fontsize=theme["font_size"],
                          fontproperties=cjk_fp if cjk_fp and has_cjk(args.ylabel) else None)
            _ensure_ylabel_clear(ax)

        # Colorbar (for heatmap only — extra must be a ScalarMappable)
        if extra is not None and hasattr(extra, 'get_cmap'):
            cbar = fig.colorbar(extra, ax=ax, shrink=0.8)
            cbar_label = data.get("cbar_label", args.ylabel)
            if cbar_label:
                cbar.set_label(cbar_label, fontsize=theme["font_size"] - 1,
                              fontproperties=cjk_fp if cjk_fp and has_cjk(cbar_label) else None)

        # Legend (skip if no labeled artists)
        if not args.no_legend and args.legend and ax.get_legend_handles_labels()[1]:
            ax.legend(fontsize=theme["font_size"] - 1, loc='best', framealpha=0.9,
                      prop=cjk_fp if cjk_fp else None)
        if args.type in ("bar", "grouped_bar", "hbar", "horizontal_bar", "line", "stacked_bar"):
            n_series = len(data.get("series", data.get("datasets", {})))
        elif args.type == "scatter":
            groups = data.get("groups")
            n_series = len(set(groups)) if isinstance(groups, (list, tuple)) and groups else 1
        else:
            n_series = 1
        audit_msg = legend_audit(ax, args.type, args.no_legend, n_series)
        if audit_msg:
            print(f"WARNING: {audit_msg}", file=sys.stderr)

    # ── v2.5 投稿精修：注释与图例控制（置于 CJK 兜底前，新文本一并被兜底覆盖；
    #    组合图/流程图等自管类型同样生效）──
    if annotations:
        cjk_fp = _apply_annotations(fig, annotations, theme, cjk_fp)
    if getattr(args, "legend_loc", None) or getattr(args, "legend_outside", False):
        _apply_legend_control(fig, loc=args.legend_loc, outside=args.legend_outside,
                              theme=theme, cjk_fp=cjk_fp)

    # ── 机制级兜底（必须在一切 draw 前：tight_layout/防重叠/savefig 都会渲染文本）──
    # 两层防护：①调用点忘传 fontproperties ②用户数据无中文但引擎自动生成中文标注
    # （如 KM 风险表/中位生存标注）导致 cjk_fp 未启用——此处发现 CJK 文本即自动找字体。
    import matplotlib.text as _mtext
    _cjk_texts = [t for t in fig.findobj(_mtext.Text)
                  if t.get_text() and has_cjk(t.get_text())]
    if _cjk_texts:
        if cjk_fp is None:
            try:
                cjk_fp, cjk_name = load_cjk_font(None)
                if cjk_fp:
                    plt.rcParams['font.sans-serif'] = [cjk_name, 'DejaVu Sans']
                    plt.rcParams['axes.unicode_minus'] = False
                    print(f"自动补启用中文字体: {cjk_name}（图内含自动生成的中文标注）",
                          file=sys.stderr)
            except Exception:
                pass
        if cjk_fp is not None:
            _fixed = 0
            for _t in _cjk_texts:
                try:
                    _t.set_fontproperties(cjk_fp)
                    _fixed += 1
                except Exception:
                    pass
            if _fixed:
                print(f"CJK 字体兜底：{_fixed} 处含中文文本已统一挂中文字体", file=sys.stderr)

    if not is_self_managed:
        plt.tight_layout()

    # Mechanism-level anti-overlap: detect real collisions post-render and
    # degrade tick labels until no axis overlaps (works for composite panels)
    fix_tick_overlaps(fig)

    # Determine output format(s) and DPI（v2.6 C1：--multi-format 一次多格式）
    out_ext = os.path.splitext(args.out)[1].lower()
    fmt_map = {'.png': 'png', '.svg': 'svg', '.pdf': 'pdf', '.tiff': 'tiff', '.tif': 'tiff', '.eps': 'eps'}
    if getattr(args, "multi_format", None):
        _base = os.path.splitext(args.out)[0]
        save_targets = [(fmt, _base + "." + fmt) for fmt in args.multi_format]
    else:
        out_format = args.format if args.format else fmt_map.get(out_ext, 'png')
        _is_vec = out_format in ('svg', 'pdf', 'eps')
        final_out = args.out
        if not _is_vec and out_ext not in fmt_map:
            final_out = args.out + '.' + out_format
        save_targets = [(out_format, final_out)]

    # Smart DPI: raster formats use theme DPI (default 600 for line art),
    # vector formats ignore DPI (but we still set it for fallback)
    dpi = args.dpi if args.dpi else theme["dpi"]
    if _a2_degraded:
        dpi = max(150, int(dpi) // 2)

    saved_files = []
    for out_format, final_out in save_targets:
        is_vector = out_format in ('svg', 'pdf', 'eps')
        # For heatmaps or photo-heavy content, user can specify --dpi 300
        save_kwargs = {
            "dpi": dpi,
            "bbox_inches": 'tight',
            "facecolor": 'white',
            "edgecolor": 'none',
        }
        if out_format == 'tiff':
            save_kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
        for _attempt in (1, 2):
            try:
                fig.savefig(final_out, format=out_format, **save_kwargs)
                break
            except OSError as e:
                if _attempt == 1:
                    print(f"WARNING: 文件写出失败（{e}），0.5 秒后自动重试一次…", file=sys.stderr)
                    time.sleep(0.5)
                else:
                    raise
            except MemoryError:
                if _attempt == 1:
                    save_kwargs["dpi"] = max(150, int(save_kwargs["dpi"]) // 2)
                    print("WARNING: 输出内存不足——DPI 已降为 "
                          f"{save_kwargs['dpi']} 自动重试一次…", file=sys.stderr)
                else:
                    raise
        saved_files.append((out_format, final_out, is_vector))
    plt.close()

    if args.alt:
        try:
            alt = generate_alt_text(args.type, data, args.title)
            alt_path = os.path.splitext(final_out)[0] + ".alt.txt"
            with open(alt_path, "w", encoding="utf-8") as f:
                f.write(alt + "\n")
            print(f"无障碍描述: {alt_path}", file=sys.stderr)
        except Exception as e:  # alt text must never break rendering
            print(f"WARNING: alt text generation failed: {e}", file=sys.stderr)

    if getattr(args, "caption", False):
        try:
            if _afcharts is not None:
                cap = _afcharts.make_caption(args.type, data, args.title)
            else:
                cap = args.title or args.type
            cap_path = os.path.splitext(final_out)[0] + ".caption.txt"
            with open(cap_path, "w", encoding="utf-8") as f:
                f.write(cap + "\n")
            print(f"图注: {cap_path}", file=sys.stderr)
        except Exception as e:  # caption 同样永不阻断渲染
            print(f"WARNING: caption generation failed: {e}", file=sys.stderr)

    cjk_info = " (colorblind-safe)" if theme.get("colorblind_safe") else ""
    if len(saved_files) == 1:
        out_format, final_out, is_vector = saved_files[0]
        sz = os.path.getsize(final_out)
        fmt_info = f"{out_format.upper()} @ {dpi}DPI" if not is_vector else f"{out_format.upper()} 矢量"
        print(f"已保存: {final_out}（{sz:,} 字节，{fmt_info}{cjk_info}）", file=sys.stderr)
    else:
        for _fmt, _path, _isvec in saved_files:
            sz = os.path.getsize(_path)
            fmt_info = f"{_fmt.upper()} @ {dpi}DPI" if not _isvec else f"{_fmt.upper()} 矢量"
            print(f"已保存: {_path}（{sz:,} 字节，{fmt_info}{cjk_info}）", file=sys.stderr)

    if getattr(args, "multi_format", None):
        _pdf_pick = [_p for _f, _p, _ in saved_files if _f == "pdf"]
        if _pdf_pick:
            out_format, final_out, is_vector = "pdf", _pdf_pick[0], True
        else:
            print("WARNING: --verify 只核查 PDF；--multi-format 中没有 PDF，跳过核查",
                  file=sys.stderr)
            args.verify = False
    if args.verify:
        if out_format != 'pdf':
            print("WARNING: --verify only applies to PDF output; skipping", file=sys.stderr)
        else:
            try:
                sys.path.insert(0, SCRIPT_DIR)
                from verify_overlap_pixel import verify
            except ImportError:
                print("WARNING: --verify requires PyMuPDF (fitz) and scipy — install with: pip install pymupdf scipy",
                      file=sys.stderr)
            else:
                real_overlaps, details = verify(final_out)
                if real_overlaps > 0:
                    print(f"VERIFY FAIL: {real_overlaps} real text overlap(s) in {final_out} — exit code 2",
                          file=sys.stderr)
                    sys.exit(2)
                print(f"VERIFY OK: no text overlaps in {final_out}", file=sys.stderr)




# ── A1(v2.8)：渲染看门狗（v2.10：退出码分级与异常诊断拆至 af_diagnostics.py）──

_WD_BASE_BUDGET = {
    "cluster_heatmap": 240, "composite": 180, "pca": 120, "km": 120,
    "forest": 90, "venn": 90, "prisma": 60,
}
_WD_DEFAULT_BUDGET = 90.0
_WD_MIN, _WD_MAX = 30.0, 1800.0


def _wd_estimate_rows(data):
    """粗估数据规模（行数），供自适应预算；取不到返回 0。"""
    try:
        if not isinstance(data, dict):
            return 0
        m = data.get("matrix")
        if isinstance(m, list) and m:
            return len(m)
        g = data.get("groups")
        if isinstance(g, dict) and g:
            return max(len(v) for v in g.values())
        s = data.get("series")
        if isinstance(s, dict) and s:
            return max(len(v) for v in s.values())
        x = data.get("x")
        if isinstance(x, list):
            return len(x)
    except Exception:
        pass
    return 0


def _wd_budget_for(chart_type, data):
    rows = _wd_estimate_rows(data)
    base = _WD_BASE_BUDGET.get(chart_type, _WD_DEFAULT_BUDGET)
    factor = 1.0 + min(3.0, rows / 2000.0)
    return max(_WD_MIN, min(_WD_MAX, base * factor))


def _watchdog_arm(chart_type, data, budget=None):
    """A1(v2.8)：看门狗。监控线程发现主线程超过预算仍未结束 → 中文三段式诊断 +
    强制退出（exit 5）。跨平台（监控线程 + os._exit，不用 SIGALRM）；正常或异常
    结束时主线程消亡，守护线程自行退出，不会误伤。AF_NO_WATCHDOG=1 亦可禁用。"""
    if os.environ.get("AF_NO_WATCHDOG"):
        return None
    if budget is None:
        budget = _wd_budget_for(chart_type, data)
    start = time.time()
    main_t = threading.main_thread()

    def _fire():
        el = time.time() - start
        print("ERROR: 渲染看门狗超时——图表未能按时完成，已强制中断（exit 5）",
              file=sys.stderr)
        print(f"└ 已用时 {el:.0f}s，超过预算 {budget:.0f}s"
              f"（图型={chart_type}，数据规模≈{_wd_estimate_rows(data)} 行）",
              file=sys.stderr)
        print("建议1: 数据过大先瘦身——cluster_heatmap 可加 --downsample 2000 等距采样",
              file=sys.stderr)
        print("建议2: 调大预算 --timeout 600；或本图禁用看门狗 --timeout 0",
              file=sys.stderr)
        print("建议3: composite 面板过多时拆成多图分别渲染", file=sys.stderr)
        os._exit(5)

    def _monitor():
        warned = set()
        while True:
            time.sleep(1.0)
            if not main_t.is_alive():
                return
            el = time.time() - start
            if el >= budget:
                _fire()
                return
            for frac, tag in ((0.5, "50%"), (0.8, "80%")):
                if el >= budget * frac and tag not in warned:
                    warned.add(tag)
                    print(f"WARNING: 渲染已用时 {el:.0f}s（预算 {budget:.0f}s 的 {tag}）——"
                          f"超时将中断并给出建议", file=sys.stderr)

    t = threading.Thread(target=_monitor, name="af-watchdog", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        sys.exit(130)
    except SystemExit:
        raise
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        if os.environ.get("AF_DEBUG"):
            raise
        _print_v3_error(e)
        sys.exit(_classify_exit_code(e))
    except Exception as e:  # A2 v3：未知异常 → 中文诊断 + 原文保留 + 针对性建议
        if os.environ.get("AF_DEBUG"):
            raise  # 维护者/反馈通道：完整 traceback
        _print_v3_error(e)
        sys.exit(_classify_exit_code(e))
