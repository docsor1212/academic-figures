# Academic Figures

[![GitHub Stars](https://img.shields.io/github/stars/docsor1212/academic-figures?style=social&label=Star)](https://github.com/docsor1212/academic-figures)

> **Publication-ready scientific figures from data — one command, verified output.**
> 从数据一键生成投稿级论文图表：期刊合规、统计正确、中文零配置、纯本地运行。

[![SkillHub](https://img.shields.io/badge/SkillHub-academic--figures-blue)](https://skillhub.cn/skill/academic-figures)
[![Site](https://img.shields.io/badge/Site-docsor.cn-teal)](https://docsor.cn)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Tests](https://img.shields.io/badge/tests-318%20pass-brightgreen)

**25 chart types** (bar/slope/volcano/upset set-intersections/box/violin/scatter/line/heatmap/
clustered-heatmap/forest/KM/ROC/venn 4-set ellipse/Bland-Altman/PCA/funnel/paired/dual-axis/
stacked/composite/diagram/PRISMA 2020 …) · **9 journal presets** (Nature/Lancet/Science/Cell/NEJM/JAMA/IEEE/CMA/
中文核心) · **9 color themes** incl. colorblind-safe Okabe-Ito · **600dpi TIFF/PDF/SVG/EPS** ·
**fully local, zero telemetry**.

---

## Quick Start

```bash
# one-command figure (auto-picks the chart type)
python3 scripts/gen_figure.py --quick -d data.csv

# Nature double-column submission (width/font/DPI per author guidelines)
python3 scripts/gen_figure.py -t bar -d data.json -o fig.pdf --journal nature --column double --verify

# Cox multi-variable regression forest (raw per-subject data; Efron + PH test)
python3 scripts/gen_figure.py -t forest -d patient.csv --stats cox   --cox-time time --cox-event event --cox-cols "age,sex,treat"

# Chinese zero-config (auto CJK font detection)
python3 scripts/gen_figure.py -t km -d survival.json -o km.png --cjk
```

## Why academic-figures

- **Journal compliance built-in**: column widths, font sizes and DPI from official author
  guidelines; `--verify` pixel-level text-overlap gate; `audit_pdf.py` font-size gate —
  the hard desk-reject reasons are guarded mechanically.
- **Statistical correctness**: Cox (Efron ties + PH test), KM (risk table, log-rank,
  median survival 95% CI), ROC (DeLong), metafunnel (Egger) — all validated against
  reference implementations (lifelines) to machine precision.
- **Chinese zero-config**: CJK font auto-detection, CMA/中文核心 presets, Chinese
  diagnostics for every error (graded exit codes 0-6).
- **Safe by construction**: fully local rendering, no network requests, no telemetry.
  See SKILL.md "Safety & Data" statement.

## Docs

- Full docs: `SKILL.md` (EN) · 中文文档见 SkillHub 页面
- Getting started: `references/quickstart.md` · One-page cheatsheet:
  `references/cheatsheet.md` · Limits & flag interactions: `references/limits.md`
- Scenario templates: `templates/` (23, each with a ready-to-run command)
- Regression suite: `tests/run_tests.py` (297 tests)

## Install

```bash
git clone https://github.com/docsor1212/academic-figures.git
cd academic-figures
python3 scripts/setup_env.py    # optional: install deps + self-check
```

Or install as an agent skill from [SkillHub](https://skillhub.cn/skill/academic-figures)
(中文) — search `academic-figures`.

**China mirror (ModelScope 魔搭)**: <https://modelscope.cn/skills/Docsor/academic-figures> — if you find this skill useful, a like there helps others find it.

## Related tools · 相关工具

- pubmed-verifier —— 批量核验 PMID/DOI 引用真实性
- cite-holmes —— 引用与上下文一致性核查（幻觉引用检测）
- paper-polisher-pro —— 论文润色 · AI 率检测
- paper-rewriter —— AI 痕迹风格改写
- doc-holmes —— PDF 精确翻译/全文提取
- cn-med-oa —— 中文 OA 医学文献检索与引用核验
- [MedWiki](https://docsor.cn) —— 医学维基参考站（药品说明书/医学术语）

## License

MIT
