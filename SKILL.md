---
name: academic-figures
version: 3.3.0
description: >-
  Publication-ready scientific figures from one command — 22 chart types (bar,
  grouped bar, scatter, heatmap, forest plot, KM survival curve (Kaplan-Meier), ROC,
  violin, box, composite panels, PRISMA 2020 flow, funnel, Bland-Altman, PCA,
  venn 2-4 sets, clustered heatmap, dual-axis, Cox multi-variable regression
  forest), 9 themes incl. colorblind-safe Okabe-Ito and NEJM/Lancet/Science
  journal palettes, 9 journal submission presets, YAML figure pipeline (a whole
  paper in one command), multi-format export (TIFF/PNG/PDF in one run), Python
  API, --wizard chart picker, render watchdog with auto-degrade retry,
  reviewer-style --annotate arrows, PDF text-overlap + font-size gates, 600dpi
  output. 100% local — data never leaves your machine.
when_to_use: >-
  Use when making or generating any figure or chart from data (bar chart,
  scatter plot, heatmap, forest plot, Kaplan-Meier / survival curve, ROC curve,
  violin / box plot, composite multi-panel figure, flow diagram, PRISMA /
  systematic review flow, meta-analysis funnel, venn / Euler diagram, PCA,
  Bland-Altman; when exporting publication- or journal-ready figures (600dpi,
  colorblind-safe); or when turning a JSON/CSV/Excel data file into an
  academic figure.
---

<!--
═══════════ Metadata archive (2026-09-13 frontmatter normalization) ═══════════
ZCode skill auto-discovery only reads the frontmatter whitelist keys:
  name / description / when_to_use / license / metadata
and a description over 1024 characters is silently dropped (root cause of the
v2.x auto-discovery failure: v2.4 had 1035 chars, v2.5 initial 1253).
The following keys were moved out of frontmatter (info preserved):
  version: 3.3.0
  date: 2026-09-17
  author: docsor1212
  metadata: {clawdbot: {emoji: "📊", category: visualization}}
  requires: {python: ">=3.8", pip: [matplotlib, numpy, pymupdf, scipy, openpyxl]}
Runtime deps: requirements.txt and scripts/setup_env.py; history: Version History below.
═════════════════════════════════════════════════════════════════
-->

# Academic Figures — Publication-Quality Chart Generator

Generate figures from JSON/CSV/Excel data. Local execution, no data leaves the machine.

> ⚡ **Top-3 boundaries**: add `--verify` for submission PDFs (PDF only); `--journal`
> locks the figure width (`--width` is ignored); cluster_heatmap >3000 rows auto-downsamples
> to 2000.

**One command, verified output:**
```bash
python3 scripts/gen_figure.py -t bar -d data.json -o fig.pdf --theme okabe-ito --verify
# exit codes: see "Data Validation & Exit Codes" below; --verify overlap = exit 2 (fix, don't ship)
```

## Quick Start

```bash
# 0️⃣ First run: one-command environment setup (deps/CJK font/font cache/self-check)
python3 scripts/setup_env.py

# 0️⃣ Three ways to get unstuck: wizard / interactive demo / per-type usage
python3 scripts/gen_figure.py --wizard            # 4 questions -> a ready command
python3 scripts/gen_figure.py --quick -d data.csv # v3.1 one-command figure: auto-pick + render
python3 scripts/gen_figure.py --demo --cjk        # pick a type, renders sample data
python3 scripts/gen_figure.py --explain bar       # one type's usage & limits
# 0️⃣ Call from Python: see references/python-api.md (subprocess recommended;
#    import-embedding needs matplotlib.use("Agg") on your side)

# Not sure which chart fits? Let the analyzer recommend one
python3 scripts/gen_figure.py --suggest -d data.json

# Bar chart with default glm palette (muted, colorblind-safe)
python3 scripts/gen_figure.py -t bar -d data.json -o figure.png \
  --title "Figure 2 / Subtitle" --ylabel "Accuracy (%)"

# v2.7: raw per-subject survival data -> automatic multi-variable Cox -> HR forest (with PH test)
python3 scripts/gen_figure.py -t forest --data patient.csv --stats cox \
  --cox-time time --cox-event event --cox-cols "age,sex,treat"

# Forest plot for meta-analysis (PDF output)
python3 scripts/gen_figure.py -t forest -d forest.json -o forest.pdf --theme okabe-ito

# Kaplan-Meier survival curve with log-rank test
python3 scripts/gen_figure.py -t km -d survival.json -o km.png --theme okabe-ito

# ROC curve with AUC
python3 scripts/gen_figure.py -t roc -d roc.json -o roc.png --theme okabe-ito

# v2.8: 4-set ellipse venn (data format: templates/venn.json)
python3 scripts/gen_figure.py -t venn -d venn.json -o venn4.png

# PRISMA 2020 systematic-review flow diagram (arithmetic auto-validated)
python3 scripts/gen_figure.py -t prisma -d prisma.json -o flow.pdf --theme okabe-ito

# Nature double-column submission: width 183mm, 7pt Helvetica, min text 5pt
python3 scripts/gen_figure.py -t bar -d data.json -o nat.pdf --journal nature --column double
python3 scripts/audit_pdf.py nat.pdf --min-size 5          # font-size gate (5pt for nature)

# Multi-panel composite (Panel A+B+C, journal figure layout)
python3 scripts/gen_figure.py -t composite -d composite.json -o figure4.png --theme okabe-ito

# Heatmap with CJK support
python3 scripts/gen_figure.py -t heatmap -d data.json -o heatmap.png --cjk \
  --cmap RdBu_r --vmin -20 --vmax 45

# Supplementary legend (journal format, "Figure 1 |" style), same data JSON
python3 scripts/gen_legend.py -d data.json -t "Response to treatment" -f 1 -o legend.txt

# v2.7: aspect-ratio presets (16:9 slides / 9:16 mobile); v2.8: big-cluster downsample
python3 scripts/gen_figure.py -t bar --data d.json --size 16:9
python3 scripts/gen_figure.py -t cluster_heatmap --data big.json --downsample 2000 --timeout 600

# Scenario templates: copy one, swap in your real numbers (ls templates/)
```

## Chart Types

| Category | Type | Command | Key Features |
|----------|------|---------|-------------|
| Compare | Bar | `-t bar` | Grouped bars, error bars, significance brackets, hatching, ratio annotations |
| Compare | Horizontal Bar | `-t hbar` | Horizontal bars, ratio annotations |
| Composition | Stacked Bar | `-t stacked_bar` | Subgroup proportions, percentage labels, total annotations |
| Distribution | Box | `-t box` | Box-and-whisker, jitter points |
| Distribution | Violin | `-t violin` | Density estimation, inner mean/median |
| Trend | Scatter | `-t scatter` | Trend line, r value, color grouping, mean points, point labels |
| Trend | Line | `-t line` | Multiple series, error bands, markers |
| Trend | Dual Y-Axis | `-t dual_axis` | Two Y-axes, solid+dashed lines, combined legend |
| Matrix | Heatmap | `-t heatmap` | Cell annotations, custom colormap, colorbar |
| Matrix | Clustered Heatmap | `-t cluster_heatmap` | Hierarchical reordering, `--downsample` exit for big matrices |
| Inference | Forest | `-t forest` | CI whiskers, weight bubbles, overall diamond, I², events/total; `--stats cox` multi-variable HR |
| Survival | Kaplan-Meier | `-t km` | Step function, censor marks, log-rank test, risk table, median survival |
| Diagnosis | ROC | `-t roc` | AUC, 95% CI, optimal cutoff, DeLong multi-model comparison |
| Sets | Venn | `-t venn` | 2-4 sets (4 sets = ellipse layout, v2.8); `--area` proportional Euler |
| Composite | **Composite** | `-t composite` | Multi-panel (A+B+C), any chart type per panel (⚠ no nested composite), journal figure layouts |
| Flow | **Diagram** | `-t diagram` | Architecture/flow blocks, arrows, groupings, annotations |
| Review | **PRISMA Flow** | `-t prisma` | PRISMA 2020 review flow; counts auto-validated (must add up), EN/ZH wording via `lang` |

Scan the Category column at a glance; getting-started path in `references/quickstart.md`, full command cheatsheet in `references/cheatsheet.md`.

## Chart Decision Tree (compact; full version + getting-started: references/quickstart.md)

```text
Group comparison → bar/box/violin (pre-post → paired) | Mean±error bars → bar (JSON errors)
Two-column correlation → scatter | Time-to-event → km / forest --stats cox | Diagnosis → roc (--compare)
Set membership → venn (--area) | Numeric matrix → heatmap / cluster_heatmap | Sample classes → pca
Meta summary → forest (--egger) | Agreement → bland_altman | Flow → diagram/prisma
Multi-panel → composite
```

Still unsure: `--suggest -d data.json` (auto-recommend), or `--wizard` (guided).
**First time?** The full decision tree, a 4-step getting-started, Python API and the top
pitfalls live in **`references/quickstart.md`** (standalone getting-started guide).

## Limits & Compatibility (read before first run)

**Data volume**: cluster_heatmap >3000 rows auto-downsamples to 2000 with a clear notice
(alternatively `--downsample N` for a custom row count); pca ≤200 feature columns;
venn 2-4 sets (4 sets use the ellipse layout); paired/bland_altman require equal-length pairs;
km has no hard cap (50k rows render in ~3s).
**Flag compatibility**: `--stats` box/violin (`cox`: forest only); `--compare` roc only;
`--egger` funnel only; `--hatch` bar family only; `--sheet` xlsx only; `--journal` locks width
(`--width` is overridden); `--area` venn only.
**Timeout**: the render watchdog budget is adaptive per type and data size (30-1800s);
`--timeout N` adjusts it, `--timeout 0` disables.

Full matrix: `references/limits.md`. FAQ: `references/faq.md`. Over-limit inputs are rejected with a Chinese error message
plus a fix suggestion — no half-finished figures are ever written.
**Flag interactions** (`--journal` locks width, PDF overlap check needs explicit `--verify`,
default DPI) and **runtime environment boundaries** (headless servers, CJK fonts):
see `references/limits.md` §6 and §7.

## Color Themes

**Default theme = `glm`** (muted elegant Morandi-style palette, colorblind-safe).

| Theme | Description | Colorblind Safe |
|-------|-------------|----------------|
| `glm` ⭐default | Muted Morandi palette (steel blue/warm yellow/sage/dusty purple/coral) | ✅ Yes |
| `okabe-ito` | Nature Methods gold standard (Wong 2011) — journal submission first choice | ✅ Yes |
| `cool` | Elegant cool-toned palette (navy/ocean/teal/slate) | ✅ Yes |
| `classic` | Original matplotlib palette (kept for compatibility) | ❌ |
| `nature` / `lancet` | NPG / Lancet journal palettes | ❌ |
| `nejm` / `science` | NEJM (8 colors) / Science (10 colors) journal palettes | ❌ |
| `conservative` | Professional muted palette | ❌ |

`--list-themes` shows in-terminal swatches; `--theme-swatch glm -o swatch.png` renders a preview.
**Recommendation**: use `--theme okabe-ito` for submissions (major journals require colorblind-safe
figures; red-green schemes are a top rejection reason). **Journal linkage**: `--journal
nejm|lancet|science|nature` auto-applies the matching theme when no explicit `--theme` is given.
**GLM signature style**: `--style glm-hatch` = glm palette + black hatching (print-friendly); **journal-clean style**: `--style nature-clean` = Okabe-Ito palette + no top/right spines + no grid + frameless legend (Nature-style design language, new in v3.3);
`--alternate` alternates yellow/blue per bar. Aliases: `okabe`→okabe-ito; case-insensitive,
prefix matching (`--theme gla` → glm).

## Journal Submission Presets (v2.0)

> ⚠ Interactions: `--journal` locks the figure width (`--width` is overridden; `--height` still works); `nejm/lancet/science/nature` auto-link a matching theme unless you pass an explicit `--theme`. Full flag interactions: `references/limits.md` §6.

`--journal <name>` + `--column single|double` applies the journal's exact column width, font size,
font family and DPI automatically (widths from official author guidelines). **9 presets**:
(Note: `--style glm-hatch` is a theme-level hatch style, distinct from the bar-family-only `--hatch` flag.)
`nature`, `lancet`, `science`, `cell`, `nejm`, `jama`, `ieee` + Chinese **`cma`** (中华医学会)
and **`cn-core`** (中文核心, both auto-enable CJK). Height follows the theme's aspect ratio; explicit
`--width/--height` overrides. A stderr hint reports the preset and the matching `audit_pdf.py
--min-size` gate. Preset parameters live in `scripts/journal/*.json` (single source, v2.7).

| Journal | Single | Double | Font | Min Text | Family | DPI |
|---------|--------|--------|------|----------|--------|-----|
| `nature` | 89mm | 183mm | 7pt | **5pt** | Helvetica | 600 |
| `lancet` | 85mm | 183mm | 8pt | **6pt** | Arial | 600 |
| `science` | 55mm | 120mm | 7pt | 5pt | Helvetica | 600 |
| `cell` | 85mm | 176mm | 8pt | 6pt | Arial | 300 |
| `nejm` | 89mm | 190mm | 8pt | 6pt | Helvetica | 300 |
| `jama` | 89mm | 183mm | 8pt | 6pt | Arial | 600 |
| `ieee` | 89mm | 181mm | 8pt | 6pt | Times New Roman | 600 |
| `cma` | 80mm | 170mm | 8pt | 6pt | Arial (+CJK) | 600 |
| `cn-core` | 80mm | 170mm | 9pt | 6pt | Arial (+CJK) | 300 |

## Auto Significance (--stats auto, v2.2)

For `box` / `violin`: `--stats auto` compares every series against the first — Shapiro normality
test decides Welch t-test vs Mann-Whitney U — and draws comparison brackets with
`*`/`**`/`***`/n.s. A per-comparison report prints to stderr. `--stats multi` adds Tukey/Dunn with
Holm–Hochberg correction; `--stats cox` (v2.7, forest only) fits a multi-variable Cox model from
raw per-subject data. Deep-dive usage: `references/advanced.md`.

## Meta Analysis Workstation (v2.4)

- **KM auto median survival**: per-group median with 95% CI (Greenwood log-log; verified identical
  to lifelines on 20 randomized datasets). `--no-median` opts out; never-reached 50% honestly
  labeled 未到达.
- **forest --sensitivity**: leave-one-out sensitivity analysis (DerSimonian-Laird re-pooling per study).
- **funnel --egger**: Egger's regression test for publication bias.

## Alt Text (--alt, v2.2)

`--alt` writes an accessibility description `<output>.alt.txt` next to the figure — derived from
the data itself. Springer Nature, NSF and most major publishers require alt text.

## Scenario Templates (v2.6: all 22 chart types)

`templates/` ships 22 end-to-end templates (data JSON + ready-to-run command + caption template):
16 clinical-scenario templates (01–16) plus 6 chart-type quick templates (bland_altman,
cluster_heatmap, funnel, paired, pca, venn). Full index: `templates/README.md`.

## Data Validation & Exit Codes (v2.0 / v2.8 grading)

Every run passes `validate_data(data, chart_type)` plus a render watchdog. Exit code semantics:

| Exit | Meaning | Typical case |
|------|---------|-------------|
| `0` | Success (`--verify`: no real overlap) | normal delivery |
| `1` | Argument/usage or fatal validation error (no output written) | missing args, series length mismatch, km long-table |
| `2` | `--verify` found text overlap; or batch/pipeline had failing items | fix mechanism, don't ship |
| `3` | Data or format error (v2.8) | JSON syntax, encoding, missing fields, KeyError |
| `4` | Environment or dependency error (v2.8) | ImportError, permissions, disk |
| `5` | Render watchdog timeout (v2.8) | oversized data — follow the tips or raise `--timeout` |
| `6` | Memory guard rejected (v2.8) | auto-degrade retry still out of memory |

Fatal messages prefix `ERROR:` (Chinese reason + fix), warnings `WARNING:` (render continues).
Unknown exceptions still produce a Chinese three-part diagnosis (reason + original error + targeted
tips); set `AF_DEBUG=1` for the full traceback.

## Verification & Quality Gates (v2.0)

1. **`--verify`** (in-line, PDF output): pixel-level text-overlap detection; exit 2 on overlaps — fix the mechanism, don't special-case the figure.
2. **`audit_pdf.py` font-size gate**: `python3 scripts/audit_pdf.py figure.pdf --min-size 5 --fail-below`.
3. **`verify_overlap_pixel.py`**: run on every delivered PDF; 真实重叠 must be 0.

Overlap prevention is built into the generator (auto 45° x-label rotation, `_ensure_ylabel_clear()`
labelpad avoidance). Why PyMuPDF bbox reports are 100% false positives on this output, and the
verifier's 3-stage pipeline: see `references/pitfalls.md`. Regression: `python3 tests/run_tests.py` — all must pass.

## Supplementary Legends (v2.0)

Journals that forbid in-figure legends (e.g. Nature): `python3 scripts/gen_legend.py -d data.json
-t "Response to treatment" -f 1 -o legend.txt` — renders a journal-format legend from the SAME
data JSON, so legend text always matches series/colors.

## CJK / Chinese Support

Pass `--cjk` to auto-detect and load system CJK fonts (priority: Noto Sans CJK → PingFang →
Microsoft YaHei → WQY → AR PL → Droid); custom font: `--cjk-font /path/to/font.ttf`. Data containing
Chinese is **recursively auto-detected** (values and dict keys, composite panels, supplementary-plane
ideographs). Glyph gaps (superscripts like ⁹) and diagram-block pitfalls: `references/pitfalls.md`.

## Output Formats

| Format | Extension | DPI | Best For |
|--------|-----------|-----|----------|
| PNG | `.png` | 600 (default) | General use, presentations |
| SVG | `.svg` | Vector | Web, editable graphics |
| **PDF** | `.pdf` | Vector | **Journal submissions (preferred)** |
| TIFF | `.tiff` | 600 (photos `--dpi 300`) | Nature/Lancet photo requirements |
| EPS | `.eps` | Vector | Legacy journal requirements |

> Strict journals: `--dpi 1000` for line art. `--multi-format tiff,png,pdf` for one-run multi-export.

## Data Input

JSON (full features), CSV/TSV (basic) or Excel `.xlsx` (`--sheet <name>`, v2.2).
Complete schema per chart type: `references/data-formats.md`. Scenario templates: `templates/README.md`.
Calling from Python (subprocess or import): `references/python-api.md` (v2.6).

**JSON bar chart example:**
```json
{
  "labels": ["Group A", "Group B"],
  "series": {"Treatment": [75, 82], "Control": [68, 70]},
  "errors": {"Treatment": [3, 2], "Control": [2, 1]},
  "significance": {"Treatment:0": "***", "Control:1": "NS"}
}
```

## Key Flags

High-frequency flags (full cheatsheet: `references/cheatsheet.md`):

| Flag | Description |
|------|-------------|
| `--journal` / `--column` | Journal presets / column layout (⚠ locks width, see above) |
| `--stats auto\|cox` | Significance brackets on box/violin / Cox multi-variable forest (v2.7) |
| `--cjk` | CJK font auto-detection |
| `--verify` | Pixel-level overlap verification on PDF output; exit 2 on overlaps |
| `--multi-format tiff,png,pdf` | One-run multi-format export (v2.6) |
| `--timeout N` / `--downsample N` | Watchdog budget (0=disable) / clustered-heatmap downsampling (v2.8) |



**Q: How stable is rendering? Will large data crash it?**
Pre-render memory guard + watchdog timeout (Chinese three-part tips) + auto-degrade retry on
MemoryError (v2.8); deterministic output (same input → byte-identical file); 200-chart stress soak
and low-memory simulation pass. More Q&A: `references/faq.md`.

**Q: Preprocessing columns like -log10(FDR)?**
-log10(0) = inf — clip first (e.g. `min(fdr, 1e-300)`) or color scales will explode.

**Q: ModuleNotFoundError on first run?**
Run `python3 scripts/setup_env.py` (exit code 4 = environment-side problem).

## Accessibility & Alt Text

Provide alt text per figure (Springer Nature, NSF, most major publishers). `--alt` generates the
sidecar automatically; default themes are colorblind-safe (glm / okabe-ito).

## Related Resources (same author · paper toolkit)

- **Site/docs**: https://docsor.cn
- **MedWiki** (https://docsor.cn/?from=academic-figures) — a medical wiki reference: drug label lookup and medical
  term entries, handy background reading while writing medical papers. Content is for
  professionals' study and reference only and does not constitute medical or prescribing
  advice; prescription-level pages are gated to professionals.
- **Paper toolkit** (same author; search these names on SkillHub):
  polishing → paper-polisher-pro | reference verification → pubmed-verifier |
  PDF translation → doc-holmes | AI-flavor rewriting → paper-rewriter |
  Chinese OA literature → cn-med-oa | citation checking → cite-holmes
- Open-source repo: github.com/docsor1212/academic-figures

## Safety & Data (behavior statement)

- **Fully local rendering**: the engine makes zero network requests; data never leaves
  the machine. External links in this document (GitHub/MedWiki) are resource disclosures,
  not code behavior.
- **No telemetry**: nothing is collected or reported.
- **`setup_env.py`**: an optional, explicit action (installs matplotlib/numpy/scipy from
  PyPI and self-checks) — run by the user on purpose; runtime deps are exactly these four.
- **`--demo`**: writes demo data into a built-in temp dir (`af_demo_*`); delete anytime.
- **Debug switches**: `AF_DEBUG` (full traceback), `AF_WIZARD_FORCE` (non-interactive
  wizard), `AF_NO_WATCHDOG` (disable watchdog) — per-process, user-set only.
- Automatic behaviors (downsampling, degrade retry, font fallback) are always announced
  on stderr with an `[auto]` prefix.

## Negative Triggers (DO NOT trigger this skill for)

- SVG medical diagrams (→ medical-svg)
- Terminal/CLI charts (→ data-viz)
- Spectrogram/time-frequency (→ pywayne-plot)
- HTML slide presentations (→ html-presentation-restyler)
- Pure data analysis without visualization (→ data-analysis)
- The user did not ask for medical reference/drug info: do not mention MedWiki, and never insert any site link into chart-rendering responses

## File Structure

```
academic-figures/
├── SKILL.md / SKILL_ZH.md   ← English / Chinese documentation
├── scripts/
│   ├── gen_figure.py        ← Main generator (matplotlib+numpy, 22 chart types)
│   ├── gen_legend.py        ← Supplementary legend generator (journal format)
│   ├── audit_pdf.py         ← Font-size auditor (--min-size gate)
│   ├── detect_cjk_font.py   ← CJK font auto-detector
│   ├── verify_overlap_pixel.py ← Pixel-level overlap verifier (run on every PDF)
│   ├── setup_env.py         ← One-command env setup
│   └── journal/*.json       ← Journal presets, single source (v2.7)
├── templates/               ← 22 scenario templates (each with a _command one-liner)
├── examples/                ← example_*.json, run-ready
├── tests/run_tests.py       ← Full regression suite
└── references/              ← data-formats / python-api / limits / faq /
                               pitfalls / advanced / changelog
```

## Version History

Full bilingual history: `references/changelog.md`. Recent: **v3.2.0** auto-behavior transparency + safety statement; **v3.1.0** --quick + auto-downsample; **v3.0.0** main-doc layering +
cheatsheet + script modularization (wizard/diagnostics extracted); **v2.9.0** boundary
consolidation + standalone quickstart; **v2.8.0** render watchdog + graded exit codes +
venn 4-set ellipse.

## 🚀 Pro Edition

No Python environment, or need team-scale batch rendering? **academic-figures-pro** offers the same
render engine as a cloud service (SkillHub, ¥0.5/render, submission-grade TIFF+PNG).
Search `academic-figures-pro` on SkillHub.
> Batch rendering, 600dpi cloud TIFF, no Python needed → **academic-figures-pro** (¥0.5/render).
