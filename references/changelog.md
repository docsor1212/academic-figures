# Changelog / 版本历史

> 本文件为完整双语版本历史；主文档只保留最近三个版本。

## English

## Version History

- **v3.3.0** (2026-09-24) — Discovery-channel release (small & safe; no behavior changes):
  - **Frontmatter colon-bomb fix**: the platform's YAML reader treats ": " inside folded
    description/when_to_use values as a mapping and reports "no valid skill" (observed on
    another skill). Both EN frontmatter values rewritten with em-dash/parenthesis phrasing.
  - **README.md (official)**: bilingual first screen for the GitHub discovery channel —
    badges, quick start, "why" section, docs map, paper toolkit, docsor.cn site link.
  - GitHub sync is now step-10 of the release chain (sync_github.sh, one-way mirror,
    hygiene hard-scan; pitfalls.md excluded via .gh-sync-exclude).

- **v3.2.0** (2026-09-22) — Auto-behavior transparency + safety statement (targets the
  v3.1.0 evaluation's lowest items: accuracy 4.6, antiPatternFaq 4.7):
  - **`[auto]` transparency**: automatic behaviors are explicitly announced —
    `--journal` width-lock prints that `--width` was ignored; `--verify` on non-PDF
    output prints that no overlap check runs. (Follows the v3.1 auto-downsample pattern.)
  - **Boundaries front-loaded**: a top-3 boundary banner at the top of the main docs
    (--verify PDF-only, --journal width-lock, cluster auto-downsample).
  - **FAQ expanded**: a dedicated flag-conflict section (--journal×--width, --verify×format,
    --stats×chart-type, --compare scores, --egger funnel, --hatch vs --style, CSV errors).
  - **Safety & Data statement** (bilingual): fully-local rendering, zero network requests,
    no telemetry, explicit optional setup_env, --demo temp dir, per-process debug switches.
  - **`--style nature-clean`** (design-language pack, first slice): Okabe-Ito palette,
    top/right spines removed, grid off, frameless legend — the Nature-style visual
    language, answering the "default style looks provincial" critique with a
    one-flag switch. Pure addition: default behavior unchanged.

  - **Templates**: every scenario template gains a `_description` line.

- **v3.1.0** (2026-09-21) — One-command figure + auto-downsample + KM risk-table hotfix
  (merged release; supersedes v3.0.1 which was published hours earlier on the same day).
  Targets the v3.0.0 evaluation's lowest items: usability 4.6, errorHandling 4.8.
  Includes the v3.0.1 hotfix: KM auto risk-table silently dropped when a CJK font was
  loaded with non-CJK group names (regression since v2.9.0; fixed with regression lock
  + 22-template CJK sweep), plus the Related Resources section (MedWiki, docsor.cn):
  - **`--quick -d data`**: one-command figure — auto-picks the chart type from the data
    (reuses the --suggest analyzer) and renders immediately through the full pipeline
    (validation, watchdog, exit codes); prints alternative types.
  - **cluster_heatmap auto-downsample**: >3000 rows without `--downsample` now
    auto-samples to 2000 rows with a prominent notice instead of failing (behavior
    change; docs updated). Still deterministic; `--downsample N` overrides.
  - **venn --area high-residual guidance**: when the ellipse fit deviation is large
    (>15%), concrete remedies are printed (fewer sets / drop extreme regions / classic
    equal-circle mode).
  - **Docs**: --hatch wording unified across SKILL.md; limits.md gains a measured
    performance reference table; data-formats.md gains a JSON-vs-CSV capability matrix.
- **v3.0.1** (2026-09-20) — Hotfix: KM auto risk-table silently dropped when a CJK font
  was loaded with non-CJK group names (undefined symbol; regression since v2.9.0).
  Fixed with a regression lock + 22-template CJK sweep. Also adds a 'Related Resources'
  section (MedWiki reference site, same-author disclosure + disclaimer).
- **v3.0.0** (2026-09-19) — Main-doc layering, cheatsheet, script modularization
  (targets the v2.9.0 evaluation's lowest items: trigger 4.5, progressive 4.5, and the
  structure note on large scripts):
  - **Chart table gains a Category column** (Compare/Composition/Distribution/Trend/
    Matrix/Inference/Survival/Diagnosis/Sets/Flow) — scannable without reading every row.
  - **Key Flags table slimmed** to high-frequency entries; the full flag reference moved
    to the new `references/cheatsheet.md` (one-page commands + full flags + exit codes +
    top boundaries).
  - **Journal preset interactions surfaced inline** (--journal locks width, theme
    auto-linking) at the point of use, instead of requiring a trip to limits.md.
  - **Script modularization (first slice)**: wizard (`af_wizard.py`) and the exception
    diagnosis system (`af_diagnostics.py`: graded exit codes, Chinese three-part
    diagnosis, field near-miss hints) extracted from gen_figure.py; names remain
    importable from gen_figure (zero caller changes). gen_figure.py 4760→4522 lines.
  - Version history in the main docs compressed to one line + pointer (dedupe).

- **v2.9.0** (2026-09-19) — Boundary consolidation + standalone getting-started guide
  (targets the v2.8.0 evaluation's two lowest items: boundary 4.5, progressive 4.5):
  - **references/quickstart.md** (new): standalone getting-started guide — full chart
    decision tree, the three helpers (--wizard/--suggest/--explain), a 4-step first-run
    path, Python API entry points, and the top first-timer pitfalls. The main doc keeps
    a compact mapping plus a pointer.
  - **references/limits.md** §6/§7 (new): consolidated flag-interaction matrix
    (--journal × --width, PDF overlap check needs explicit --verify, default DPI,
    watchdog, journal×theme, --stats multi×auto) and runtime environment boundaries
    (headless Agg built in, CJK font detection, import-embedding Agg requirement,
    writable output dir, cluster row pre-advisory).
  - **Pre-emptive cluster advisory**: cluster_heatmap with >1500 rows (half the hard
    cap) now prints a --downsample suggestion at render time instead of only failing
    at the 3000-row limit.
  - **KeyError near-miss hints**: a misspelled JSON field in the error path now suggests
    the closest legal field names (difflib) in the Chinese diagnosis.
  - Python API surfaced from the Quick Start section; version bumps to 2.9.0.

- **v3.3.0**（2026-09-24）—— 发现渠道版（小而稳；无行为变更）：
  - **frontmatter 冒号炸弹修复**：平台 YAML 解析器把 description/when_to_use 折叠值中的
    "冒号+空格"当作映射，导致判"无有效 skill"（其他 skill 已踩坑）。英文两处值改写为
    破折号/括号表述；
  - **README.md 官方化**：GitHub 发现渠道第一屏——双语徽章/快速开始/卖点/文档地图/
    论文全家桶/docsor.cn 官网入口；
  - GitHub 同步固化为发布链第⑩步（sync_github.sh 单向镜像+卫生硬扫描；
    pitfalls.md 经 .gh-sync-exclude 排除不上公开面）。

- **v3.2.0**（2026-09-22）—— 自动行为透明化与安全声明（对标 v3.1.0 评测最低项：
  accuracy 4.6、antiPatternFaq 4.7）：
  - **`[auto]` 透明化**：自动行为显式告知——`--journal` 锁宽度时明示 `--width` 被忽略；
    `--verify` 用于非 PDF 输出时明示本次不做重叠检查；
  - **边界前置**：主文档顶部新增三条最常用边界横幅（--verify 仅 PDF/--journal 锁宽/
    cluster 自动降采样）；
  - **FAQ 扩充**：新增参数冲突专节（--journal×--width、--verify×格式、--stats×图型、
    --compare scores、--egger、--hatch vs --style、CSV 误差棒）；
  - **「安全与数据」声明（双语）**：纯本地渲染零网络请求、无遥测、setup_env 为可选显式
    动作、--demo 临时目录、调试开关均为进程内显式设置；
  - **`--style nature-clean`**（设计语言包第一刀）：Okabe-Ito 配色+去顶右框线+无网格+
    无框图例——Nature 系版式语言一键开关，正面回应"默认风格保守"批评。
    纯增量：默认行为零变化。

  - **模板**：全部场景模板补 `_description` 说明行。

- **v3.1.0**（2026-09-21）—— 一键出图+自动降采样+KM 风险表热修（合并发布，含同日早间的
  v3.0.1 全部内容）。对标 v3.0.0 评测最低项：usability 4.6、errorHandling 4.8。
  含 v3.0.1 热修：KM 自动风险表在『已加载中文字体+组名英文』场景静默丢失（回归锁+22 模板
  CJK 扫描）；另含『相关资源（同一作者）』节（MedWiki，docsor.cn）。
  - **`--quick -d 数据`**：一键出图——按数据自动选择图型（复用 --suggest 分析器）并直接
    走完整渲染管线（校验/看门狗/退出码），stderr 打印备选图型；
  - **cluster_heatmap 自动降采样**：>3000 行未给 `--downsample` 时自动采样到 2000 行并
    显著告知（行为变更：此前为致命错退出；文档已同步更新），确定性不变，`--downsample N` 可覆盖；
  - **venn --area 高残差主动建议**：椭圆拟合偏差 >15% 时打印具体补救措施（减少集合数/
    去掉悬殊区域/改等圆模式）；
  - **文档**：--hatch 口径统一；limits.md 新增实测性能参考表；data-formats.md 新增
    JSON vs CSV 能力对照表。
- **v3.0.1**（2026-09-20）—— 热修：KM 自动风险表在『已加载中文字体+组名为英文』场景
  静默丢失（未定义符号，v2.9.0 起携带）；修复并加回归锁+22 模板 CJK 全量扫描。另新增
  『相关资源（同一作者）』节（MedWiki 医学参考站披露+免责声明）。
- **v3.0.0**（2026-09-19）—— 主文档信息分层、速查卡与脚本模块化（对标 v2.9.0 评测
  最低项：trigger 4.5、progressive 4.5 与 structure 的脚本体量点名）：
  - **图表类型表新增「类别」列**（比较/构成/分布/趋势/矩阵/统计推断/生存分析/诊断试验/
    集合/流程），一眼扫到目标图型；
  - **常用参数表瘦身**为高频 6 项，全量参数迁入新增的 `references/cheatsheet.md`
    （一页速查：22 种图型命令骨架+全量参数+退出码+边界 Top 5）；
  - **期刊预设交互行内前置**（--journal 锁宽度、theme 自动联动），不必翻 limits.md；
  - **脚本模块化第一刀**：选图向导（af_wizard.py）与异常诊断系统（af_diagnostics.py：
    分级退出码+中文三段式诊断+字段近似纠错）自 gen_figure.py 拆出，原名保持可从
    gen_figure 导入（调用方零改动）；gen_figure.py 4760→4522 行；
  - 主文档版本历史压缩为单行+指针（去重）。

- **v2.9.0**（2026-09-19）—— 边界收拢与独立快速入门（对标 v2.8.0 评测两个最低项：
  boundary 4.5、progressive 4.5）：
  - **references/quickstart.md（新增）**：独立快速入门指南——完整选图决策树、选图三件套
    （--wizard/--suggest/--explain）、上手四步、Python 内调用入口、常见第一坑 Top 6；
    主文档保留精简映射+指针。
  - **references/limits.md §六/§七（新增）**：参数交互矩阵收拢（--journal 锁宽度、
    PDF 重叠检测需显式 --verify、默认 DPI、看门狗、journal×theme、--stats multi×auto）
    与运行环境边界（内置 Agg 无显示环境开箱即跑、中文字体检测、import 嵌入需自行 Agg、
    输出目录可写、cluster 行数预判）。
  - **cluster_heatmap 预判式提示**：行数 >1500（半限）渲染时即输出 --downsample 建议，
    不再等 3000 行硬限报错。
  - **KeyError 字段纠错**：JSON 字段拼写错误时在中文诊断中给出最接近的合法字段名
    （difflib 近似匹配）。
  - 快速开始前置 Python API 入口；版本号升至 2.9.0。

- **v2.8.0** (2026-09-17) — Watchdog + zero-friction onboarding (targets the v2.7.0
  evaluation's lowest items: stability 4.3, doc length, exception coverage):
  - **Render watchdog**: adaptive per-type/size budget (30-1800s, `--timeout N` to
    override, `0` to disable); on breach prints a Chinese three-part diagnosis and
    hard-exits with code 5 — no more indefinite hangs.
  - **Graded exit codes**: 3=data/format error, 4=environment/dependency error,
    5=watchdog timeout, 6=memory guard rejected (0/1/2 semantics unchanged).
  - **Auto-degrade retry**: on MemoryError the figure is rebuilt at ×0.85 size and
    half output DPI, announced on stderr; second failure exits 6.
  - **`--downsample N`**: deterministic equidistant row sampling for cluster_heatmap;
    the >3000-row fatal error now suggests the exact command.
  - **venn 4-set ellipse** (v2.8 flagship): deterministic pinwheel layout validated
    so all 15 regions are non-empty; `--area` fits ellipse geometry to target areas
    (least-squares on a deterministic grid, eulerAPE-style) and honestly discloses
    the max residual; region counts stay exact; labels de-cluttered deterministically.
  - **`--wizard`**: 4 questions -> a ready-to-run command; non-TTY environments get
    a decision-tree guide instead of hanging.
  - **Exception coverage**: ImportError/ModuleNotFoundError/OSError/TimeoutExpired
    etc. now map to Chinese diagnoses (exit 4); FAQ error table 8 -> 12 rows.
  - **Docs**: SKILL_ZH 536 -> 316 lines (decision tree, exit-code table, single
    boundary source); deep-dive sections moved to references/pitfalls.md; a
    regression test now locks chart-count claims in all docs to the registry.
- **v2.7.0** (2026-09-16) — Stability + Cox regression workstation:
  - `--stats cox`: raw per-subject survival data -> automatic multi-variable Cox
    proportional hazards -> HR[95%CI] forest (self-implemented Efron ties +
    Newton-Raphson + Grambsch-Therneau PH test, zero new dependencies; cross-checked
    against lifelines to |Δβ| < 1e-6 on rossi/GBSG2).
  - `--size` aspect presets (16:9/4:5/9:16...); exception handler v3 (Chinese
    three-part diagnosis + original error + targeted tips, AF_DEBUG escape).
  - Deterministic output (same input -> byte-identical file), memory guard,
    200-chart soak; package hygiene (zero duplicate files; `scripts/journal/*.json`
    as the single journal-preset source); SKILL docs slimmed ~30%.
- **v2.6.0** (2026-09-15) — Pipeline edition (targets the v2.5.0 review's 4.7):
  - `--pipeline analysis.yaml|json`: whole-paper multi-figure pipeline with
    global `defaults` + per-figure `figures` list (previous `--batch` kept).
  - `--multi-format tiff,png,pdf`: one run renders every format from one
    source filename.
  - `references/python-api.md`: call from Python via subprocess or import
    (load_data / validate_data / gen_*), examples verified end-to-end.
  - Templates 16 → 22, now covering all 22 chart types, plus a full README
    index (fixes the "only 10 templates" discovery gap).
  - KM data-trap fix: CSV long tables (time/event/group columns) are rejected
    with a how-to-convert hint instead of silently rendering a meaningless
    single curve; validation messages are now Chinese-first (~10 English
    leftovers cleared) and the FAQ gained an error-message lookup table.
  - Mechanism fixes from the Pro audit ship here: KM risk-table group-name
    placement, venn set-label mirroring, PRISMA box heights with measured
    self-healing.
  - Forest null reference line now defaults by effect measure (OR/RR/HR → 1.0,
    MD/SMD → 0.0) instead of always 0 — natural-scale significance reads
    correctly without setting ref_line (found by real-data review).
- **v2.5.0** (2026-09-14) — Submission polish:
  - `--annotate "x,y:text"`: repeatable arrow annotations at data coordinates
    (category axes accept tick labels), auto declutter, arrows track texts.
  - NEJM + Science (AAAS) color themes; `--journal nejm|lancet|science|nature`
    now auto-links the matching color theme (explicit `--theme` wins).
  - venn `--area`: area-proportional Euler mode (2 sets analytic, 3 sets
    least-squares fit of centers+radii with honest fit report); new `"regions"`
    count input fixes the never-parseable numeric `"sets"` format from v2.3.
  - `--legend-loc` + `--legend-outside` (composite figures merge to one shared
    legend, duplicates removed).
  - Library exception Chinese mapping 9 → 18; payload description now states
    21 chart types / 9 themes (fixes stale "15 chart types" store summary).
- **v2.4.0** (2026-09-13) — Meta analysis workstation:
  - KM auto median survival + 95% CI (Greenwood log-log, lifelines-identical
    on 20 randomized datasets) annotated in-plot; `--no-median` opts out.
  - `forest --sensitivity`: leave-one-out DL re-pooling rendered under the main plot.
  - Library exception Chinese explanations (9 entries) + FAQ (references/faq.md).
  - CJK font enforcement mechanism: any CJK text found before render gets the
    CJK font automatically (kills tofu blocks at the mechanism level).
- **v2.3.0** (2026-09-12) — 6 new chart types (21 total): funnel (DL pooled line,
  `--egger`), bland_altman, pca (grouping ellipses + loadings), paired
  (paired-test brackets), venn (exact region counts), cluster_heatmap (Ward
  reorder); `--batch` manifest rendering with report JSON; `--caption` sidecar;
  vectorized KM (50k rows ≈ 3 s).
- **v2.2.0** (2026-09-11) — Journal & workflow expansion:
  - Journal presets 2 → 9: added `science`, `cell`, `nejm`, `jama`, `ieee`, and
    Chinese presets `cma` (中华医学会系列) + `cn-core` (中文核心通用) with auto CJK.
  - Excel input: `.xlsx/.xls` direct load with `--sheet` selection (openpyxl).
  - `--stats auto` (box/violin): pairwise-vs-first significance with automatic
    test selection (Shapiro → Welch t / Mann-Whitney U), brackets + stars drawn,
    per-comparison report on stderr.
  - `--alt`: accessibility (alt) text sidecar `<output>.alt.txt` generated from
    the data dict — groups, medians, AUC, overall effect, PRISMA counts, panels.
  - `templates/`: 10 scenario templates (data JSON + command + caption template)
    covering meta-analysis, RCT, survival, ROC, correlation, PRISMA,
    dose-response, composite, survey, Chinese-journal figures.
  - Mechanism fixes (staged 09-08): tick-label overlap ladder now rotates to 90°
    before any thinning and warns loudly when labels are hidden; PRISMA side
    boxes auto-fit long reason text (measured width + wrap + height); KM
    non-monotonic input auto-sorts with an honest warning. Tests 96 → 118.
- **v2.1.0** (2026-09-08) — Reviewer toolkit release: PRISMA 2020 flow + chart-type suggester.
  - New chart type `-t prisma`: PRISMA 2020 systematic-review flow diagram — three-phase spine
    (Identification / Screening / Included) with left-rail phase labels, exclusion boxes with
    per-reason counts, and standard EN/ZH wording via `"lang": "en"|"zh"`. `validate_data()`
    gates the arithmetic: screened = identified − duplicates, sought = screened − excluded,
    assessed = sought − not retrieved, exclusion reasons + included = assessed. Inconsistent
    counts are rejected with ERROR (exit 1) — catching the most common reviewer complaint
    before the figure ever ships.
  - New `--suggest`: structural analyzer recommends chart types from any data file (ranked
    scores + reasons + ready-to-run command). Recognizes prisma/diagram/composite/roc/km/
    forest/heatmap/dual_axis/violin/box/scatter/bar signatures.
  - `gen_legend.py` now covers prisma (journal-format flow description).
  - 13th example dataset (`examples/example_prisma.json`); regression tests 78 → 96 (prisma
    validation gates ×7, CLI EN/ZH renders ×2, suggest unit tests ×7 + CLI ×2); evals 8 → 10.
- **v2.0.1** (2026-08-13) — UX improvements (targeting SkillHub official review T5.0/R4.5/A4.4/C4.8/E4.6 gaps):
  - **Default theme changed to `glm`** (muted Morandi, colorblind-safe; old `default` renamed `classic`, kept for compatibility).
  - New: `--list-themes` (in-terminal color swatches), `--theme-swatch <theme> -o out.png`, `--style glm-hatch` (GLM signature style one-liner), `--demo` (interactive menu, 12 built-in sample datasets), `--explain <type>` (limitations/notes), theme aliases + case/prefix tolerance (`okabe`/`colorblind`/`glm-blog`/`default`→glm).
  - `--hatch` extended to stacked_bar and forest (overall diamond).
  - **Heatmap default colormap fix**: when `--cmap` is omitted the default is now RdBu_r (red-blue diverging) — previously the kwargs default silently fell through to matplotlib's viridis (yellow-green); explicit `--cmap` still overrides.
  - **Data-driven heatmap colormap (added)**: all-positive data now auto-switches to warm YlOrRd sequential (removes the "broken band" look from RdBu_r's white midpoint on low positive cells); diverging RdBu_r only for data with negatives; vmin/vmax follow data range. Regression tests ×2.
  - Error messages for known limits (e.g., CSV+error bars) now include HINT with the fix.
  - New `scripts/setup_env.py`: one-command env setup (deps/CJK font/font-cache cleanup/self-check).
  - New `examples/`: 5 sample data JSONs + 7 theme swatch previews + README.
  - Docs: new FAQ section (font cache/deps/CSV limits/theme cheatsheet).
- **v2.0.0** (2026-08-12) — Hardening release: data validation layer, journal presets, verification tooling, regression/evals suites.
  - `validate_data()`: structural validation across all 18 type/alias branches, called centrally from `main()`; fatal → `ERROR:` + exit 1 (no output), warning → `WARNING:` (accepted). Examples: empty series, length-mismatched series, box/violin labels ≠ group count, missing required keys, ROC `curves[].auc` outside [0,1].
  - `--journal nature|lancet` + `--column single|double`: official column widths (nature 89/183mm, lancet 85/183mm), font size (7/8pt), family (Helvetica/Arial), 600dpi.
  - `--verify`: in-line pixel-level overlap check on PDF output, exit 2 on real overlaps.
  - `scripts/audit_pdf.py`: font-size audit with `--min-size`/`--fail-below`/`--max-reports` — journal minimum text gate (nature 5pt, lancet 6pt).
  - `scripts/gen_legend.py`: journal-format supplementary legends from the same data JSON.
  - `legend_audit()`: empty-legend detection for Python-API misuse.
  - Bug fixes: box/violin `labels` validated as group names (series count, not value count); ROC AUC bounds checked per curve; `has_cjk()` extended to supplementary planes (Ext-B..F U+20000–U+2EBEF, Ext-G U+30000–U+3134F); composite legend double-period removed; `_scan_cjk()` now scans dict **keys** too (Chinese series names trigger font loading).
  - `tests/run_tests.py`: 50 unittest tests (14 chart-type CLI smoke tests + validate_data units + CSV edge cases + CJK + legend audit + PDF audit + legend gen).
  - `evals/evals.json`: 8 behavioral evals, each validated against real CLI behavior (exit codes, CJK auto-load, nature double=183mm, no-false-warning legend audit, CSV long-format, box group labels, KM legend formatting).
- **v1.6.6** (2026-08-12) — Scatter readability fixes: (1) `gen_scatter` now renders point labels from `data["labels"]` (one per x/y point, alternating above/below with growing offset so clustered points like years 1950/1953/1955 don't collide); (2) trend line now carries `label='Linear trend'` so the legend explains the dashed regression line instead of leaving it unlabeled. Rebuilt demo3 with full annotations (title, axis labels, point labels, legend) — verified 0 real overlaps.
- **v1.6.5** (2026-08-12) — Documentation: made overlap verification a mandatory step for PDF delivery. Added "Verification" section to SKILL.md/SKILL_ZH.md (3-stage pixel verifier usage + warning that PyMuPDF bbox intersections are line-height-model artifacts, 100% false positives on this generator's output), added `verify_overlap_pixel.py` to file-structure docs, and added `pymupdf`/`scipy` to the `requires` pip list (verifier dependencies). Demo figures regenerated with real KEGG pathway gene counts (demo2) and ChEMBL pchembl values (demo3) after the previous demo datasets were found to contain degenerate synthetic values (all-50 gene counts / all-4.0 max_phase) that compressed axes into misleading density.
- **v1.6.4** (2026-08-12) — Verifier fix: `confirm_min_dist` now uses unique assignment (a component whose centroid falls in both spans' candidate windows is assigned to the nearer origin) instead of shared assignment, eliminating false positives for rotated y-axis labels (e.g. scatter `(max phase)` label vs top tick `4.00` — claimed overlap was verifier cross-assignment, not real ink contact). Re-verified all 14 production figures + 4 demo figures: **0 real overlaps**. Added `_ensure_ylabel_clear()` safety net to `gen_figure.py` (auto-increases y-label labelpad when matplotlib's measured bbox actually collides with tick labels; inert when no conflict, as in all current figures).
- **v1.6.3** (2026-08-12) — Label overlap verification closed at pixel level. Root cause of all reported "overlaps": PyMuPDF span/char bboxes use the font line-height model (Noto CJK 2.856em, DejaVu 1.695em), which systematically overestimates rotated text (45°: 32.3pt claimed vs 16.8pt real ink for fs=9) and stacked labels (char row bbox spans full line height). Verified all 14 production figures with a 3-stage pixel verifier (connected components → component centroid ownership → min ink distance at 600dpi): **0 real ink overlaps**. matplotlib `get_window_extent` (20.9pt vs 16.8pt real) is slightly conservative, so the anti-overlap mechanism is correct as-is. Verifier at `scripts/verify_overlap_pixel.py`. Removed dead `math` import from `gen_figure.py`.
- **v1.6.2** (2026-08-11) — Fixed two quality issues found in production use. (1) CJK detection is now recursive: `_text_has_cjk()` scans the entire data dict including nested composite panels/diagram text, so Chinese titles inside composite panels correctly trigger Noto Sans CJK loading (previously they rendered as tofu boxes). (2) Automatic label anti-overlap: x-axis labels rotate 45° when >8 bars or >12-char labels (bar) / >10 points (line) / >6 columns or >14-char labels (heatmap); hbar y-labels shrink one point when >12 categories; composite panels pass `alternate` through to hbar subplots.
- **v1.6.1** (2026-08-07) — Brightened GLM theme yellow from `#D49356` to `#D79D55` (true mean pixel value of the GLM-5.2 blog chart, sampled from 143k yellow pixels; previous value was an unrepresentatively dark sample). All alternate-style bar charts now render with the brighter warm yellow.
- **v1.6.0** (2026-08-07) — Added `--alternate` flag: GLM-5.2 blog style blue/yellow alternating bars for single-series bar/hbar charts (`--theme glm --hatch --alternate` reproduces the blog's yellow+black-hatch look: `#D79D55` yellow / `#70A0D0` blue alternating per bar with black hatch lines). Colors come from the first two theme colors, so it also works with `cool`/`okabe-ito` themes.
- **v1.5.2** (2026-06-18) — Added `cool` theme: 8-color cool-toned palette (navy `#1B4965`, ocean `#2E6F9E`, sky `#4FA3C5`, dark teal `#3D8080`, medium teal `#62A0A8`, steel `#5B7BA0`, slate `#7B9AB5`, pale steel `#9DB5CC`), all hues in 190-260° range, colorblind-safe. Created in response to user rejecting warm/saturated palettes and requesting 素雅冷色调配色.
- **v1.5.1** (2026-06-18) — Bug fixes: `gen_km()` crashes when `median_survival` value is `null` (median not reached); `gen_scatter()` crashes when `groups` array length exceeds `x`/`y` length (composite panels). Both fixed with null/length guards. Added `cool` theme (navy/ocean/teal/slate cool-toned palette, colorblind-safe). See `references/pitfalls.md`.
- **v1.5.0** (2026-06-17) — Added 3 new chart types: horizontal bar charts (hbar, with ratio annotations like "4.96x"), multi-panel composite figures (Panel A+B+C with GridSpec, any chart type per panel), architecture/flow diagrams (colored blocks, arrows, groupings, annotations); added GLM theme (muted/dusty palette pixel-extracted from GLM-5.2 blog: `#70A0D0` blue + `#D79D55` yellow, mean pixel values); added bar hatching with BLACK lines on ALL bars (print-friendly, 9 patterns: `//`, `\\`, `||`, `--`, `++`, `xx`, etc.); added `--hatch`, `--show-ratio`, `--ratio-base`, `--horizontal` CLI flags; **white background mandatory** for all themes (publication standard); see `references/reverse-engineering-colors.md` for pixel extraction technique
- **v1.4.0** (2026-05-17) — Added 4 new chart types: Kaplan-Meier survival curves (log-rank test, risk tables, median survival, censor marks), ROC curves (AUC, 95% CI, optimal cutoff, multi-model comparison), stacked bar charts (compositional data, percentage labels), dual Y-axis line charts (clinical score + lab marker); expanded data validation for new types
- **v1.3.0** (2026-05-17) — Added Okabe-Ito colorblind-safe theme (Nature Methods standard); DPI upgraded 300→600 for line art; added PDF/TIFF/EPS output; enhanced forest plot (weight bubbles, I² heterogeneity, events/total, separator line); accessibility alt-text guidance; smart DPI by content type
- **v1.2.0** (2026-05-16) — Added version metadata, requires declaration, negative triggers, file structure docs
- **v1.1.0** — Added auto CJK detection, CSV long-format auto-conversion, empty data validation
- **v1.0.0** — Initial release: 7 chart types, 4 themes, CJK support, statistical annotations

## 中文

## 版本历史

- **v2.8.0**（2026-09-17）— 看门狗与上手零门槛（对标 v2.7.0 评测最低项：稳定性 4.3、文档偏长、异常覆盖）：
  - **渲染看门狗**：按图型与数据量自适应预算（30~1800s，`--timeout N` 覆盖、`0` 禁用）；超时输出中文三段式诊断并强制中断（退出码 5）——不再无限挂起。
  - **退出码分级**：3=数据/格式错、4=环境/依赖错、5=看门狗超时、6=内存护栏拒绝（0/1/2 语义不变）。
  - **自动降级重试**：MemoryError 时按 ×0.85 图幅+DPI 减半重建一次并在 stderr 明示；再失败退出码 6。
  - **`--downsample N`**：cluster_heatmap 确定性等距采样；超 3000 行的致命报错直接给出该命令。
  - **venn 4 集合椭圆**（本版旗舰）：确定性风车布局经验证 15 区域全非空；`--area` 按目标面积椭圆联合最优拟合（确定性网格最小二乘，eulerAPE 思路），残差如实中文披露；区域数字保持精确计数；标签确定性疏散防相撞。
  - **`--wizard`**：四问生成完整命令；非交互环境打印选图决策树，绝不挂起。
  - **异常词条扩容**：ImportError/ModuleNotFoundError/OSError/TimeoutExpired 等映射中文诊断（退出码 4）；FAQ 报错速查表 8→12 行。
  - **文档**：SKILL_ZH 536→316 行（新增选图决策树、退出码表、边界单一真源）；深水区内容外移 references/pitfalls.md；新增回归测试将全文档图型计数表述锁死到代码注册表。
- **v2.7.0**（2026-09-16）— 稳健基石+Cox 回归工作站：
  - `--stats cox`：原始逐例生存数据 → 自动多因素 Cox 比例风险回归 → HR[95%CI] 森林图（自研 Efron 结基线+Newton-Raphson+Grambsch-Therneau PH 检验，零新依赖；与 lifelines 对拍 |Δβ|<1e-6）。
  - `--size` 画幅预设（16:9/4:5/9:16）；异常兜底 v3（中文三段式诊断+原文+建议，AF_DEBUG 逃生门）。
  - 确定性输出、内存护栏、200 图压测；包结构治理（重复清零、journal/*.json 单一参数表）；主文档瘦身约 30%。
- **v2.6.0** (2026-09-15) — 流水线版（对标 v2.5.0 评测 4.7 定向改进）：
  - `--pipeline analysis.yaml|json`：多图流水线，defaults 全局默认 + figures 逐图条目，
    一篇论文全套图一条命令出齐（原 --batch 保留可用）。
  - `--multi-format tiff,png,pdf`：一次渲染输出多种格式，文件名同源。
  - 新增 `references/python-api.md`：subprocess 与 import 函数级两种编程调用，
    示例全部实测跑通；校验消息 100% 中文化收尾（~10 条英文残留清除），
    FAQ 新增报错速查表。
  - 模板 16→22，覆盖全部 22 种图型 + README 全索引（修"只见 10 个模板"）。
  - KM 数据陷阱机制修复：CSV 长表（time/event/group 列）拦截并给转换指引，
    不再静默渲染无意义单曲线；KM 风险表组名实测定位、韦恩图集合标签镜像、
    PRISMA 盒高实测自愈三项机制修复随本版发布。
  - 森林图无效参考线改按效应尺度自动取值（OR/RR/HR→1.0，MD/SMD→0.0），
    不再恒为 0——自然尺度 OR 的显著性判读不再画错位置（真实数据审核发现）。
- **v2.5.0** (2026-09-14) — 投稿精修：`--annotate "x,y:文字"` 数据坐标箭头注释（类别轴支持标签定位，
  自动防重叠+箭头跟随）；NEJM/Science 期刊配色主题 + `--journal` 自动联动配色；
  venn `--area` 面积比例 Euler 模式（2 集合解析解/3 集合最优拟合，拟合偏差如实报告）+
  `regions` 区域计数键（修复 v2.3 数字型 sets 从未可用的缺陷）；`--legend-loc`/`--legend-outside`
  （组合图合并共享图例）；库异常中文映射 9→18；发布描述更正为 21 图表/9 配色（修复"15 chart types"旧文案）。
- **v2.4.0** (2026-09-12) — Meta 分析工作站：KM 自动中位生存（95%CI，与 lifelines 全等对拍）图内标注；
  forest --sensitivity 留一法敏感性分析（自动画在同一图下方）；库异常中文名映射；常见问题 FAQ。
- **v2.3.0** (2026-09-11) — 统计深水区：KM 自动风险表+log-rank、--stats multi（Tukey/Dunn+Hochberg）、
  ROC --compare DeLong、新图型 funnel/bland_altman/pca/paired/venn/cluster_heatmap、--batch 批量、
  --caption 双语图注、CLI 全面中文化、极端输入友好报错。
- **v2.1.0** (2026-09-08) — 审稿人工具箱版本：PRISMA 2020 流程图 + 图表类型推荐器。
  - 新图表类型 `-t prisma`：PRISMA 2020 系统综述流程图——识别/筛选/纳入三阶段主轴 + 左侧
    旋转相位标签 + 右侧排除盒（含逐条排除原因计数），`"lang": "zh"|"en"` 输出中/英文标准
    措辞。`validate_data()` 对数字做自洽性闸门：初筛数=检索数−重复数、寻求获取数=初筛数−
    排除数、评估数=寻求数−未获取数、排除原因合计+纳入数=评估数——**数字对不上直接 ERROR
    拒绝出图**，把审稿人最常见的投诉拦在投稿之前。
  - 新 `--suggest`：分析任意数据文件的结构，推荐最合适的图表类型（评分排序 + 理由 +
    可直接运行的完整命令）。识别 prisma/diagram/composite/roc/km/forest/heatmap/
    dual_axis/violin/box/scatter/bar 特征签名。
  - `gen_legend.py` 支持 prisma（期刊格式流程描述图例）。
  - 第 13 个示例数据（examples/example_prisma.json）；回归测试 78 → 96（prisma 校验闸门
    ×7、CLI 中英渲染 ×2、suggest 单元+CLI ×9）；evals 8 → 10。
- **v2.0.1** (2026-08-13) — 用户体验优化（基于 SkillHub 官方评测 T5.0/R4.5/A4.4/C4.8/E4.6 的失分点）：
  - **默认配色改为 `glm`**（素雅莫兰迪、色盲安全；旧 default 改名 `classic` 兼容保留）。
  - 新增 `--list-themes`（终端彩色色块一览 7 套配色）、`--theme-swatch <主题> -o out.png`（色板预览图）、`--style glm-hatch`（GLM 黄蓝斜线招牌风格一键预设）、`--demo`（交互演示菜单，内置 12 类示例数据）、`--explain <类型>`（限制条件说明）、主题别名+大小写/前缀容错（`okabe`/`colorblind`/`glm-blog`/`default`→glm）。
  - `--hatch` 扩展支持 stacked_bar 与 forest（overall 菱形斜纹）。
  - **热力图默认色阶修复**：`--cmap` 未指定时默认 RdBu_r（红蓝发散，正红负蓝）——此前因 kwargs 默认值失效，热力图实际渲染为 matplotlib 默认 viridis（黄绿色）；显式 `--cmap` 仍可覆盖。
  - **热力图色阶数据驱动（v2.0.1 追加）**：全正数据自动改用 YlOrRd 暖色单渐变（消除 RdBu_r 白色中点导致的低值单元格"断层"感）；含负值才用 RdBu_r 红蓝发散；vmin/vmax 跟随数据范围。回归测试 ×2 锁定。
  - CSV+误差棒等已知限制的错误提示附带解决方案（HINT）。
  - 新增 `scripts/setup_env.py` 一键环境准备（依赖安装/中文字体检测/字体缓存清理/自检）。
  - 新增 `examples/` 目录：5 个示例数据 JSON + 7 套配色 swatch 预览 + README。
  - 文档新增 FAQ 章节（字体缓存/依赖/CSV 限制/配色速查）。
- **v2.0.0** (2026-08-12) — 加固版本：数据校验层、期刊预设、验证工具链、回归/评测套件。
  - `validate_data()`：覆盖全部 18 种类型/别名分支的结构校验，`main()` 集中调用；致命 → `ERROR:` + exit 1（不落盘），警告 → `WARNING:`（继续）。示例：空系列、长度不匹配系列、box/violin labels≠组数、缺少必需键、ROC `curves[].auc` 超出 [0,1]。
  - `--journal nature|lancet` + `--column single|double`：官方栏宽（nature 89/183mm，lancet 85/183mm）、字号（7/8pt）、字体族（Helvetica/Arial）、600dpi。
  - `--verify`：PDF 输出内联像素级重叠检查，真实重叠 exit 2。
  - `scripts/audit_pdf.py`：字号审计，`--min-size`/`--fail-below`/`--max-reports` — 期刊最小字号门禁（nature 5pt，lancet 6pt）。
  - `scripts/gen_legend.py`：从同一数据JSON生成期刊格式补充图例。
  - `legend_audit()`：Python API 误用导致的空图例检测。
  - Bug修复：box/violin `labels` 按组名校验（系列数而非值数）；ROC AUC 逐条曲线检查边界；`has_cjk()` 扩展到补充平面（Ext-B..F U+20000–U+2EBEF、Ext-G U+30000–U+3134F）；组合图图例重复句点移除；`_scan_cjk()` 现在也扫描字典**键**（中文系列名触发字体加载）。
  - `tests/run_tests.py`：50个unittest测试（14图型CLI冒烟 + validate_data单元 + CSV边界 + CJK + 图例审计 + PDF审计 + 图例生成）。
  - `evals/evals.json`：8个行为评测，每个都对照真实CLI行为验证（退出码、CJK自动加载、nature双栏=183mm、图例审计不误报、CSV长格式、box组标签、KM图例格式）。
- **v1.6.6** (2026-08-12) — 散点图可读性修复：(1) `gen_scatter` 现在渲染 `data["labels"]` 点标签（每个 x/y 点一个，上下交替偏移且偏移随索引增长，防止 1950/1953/1955 这类聚集点标签碰撞）；(2) 趋势线加 `label='Linear trend'`，图例会说明虚线是线性回归线（此前虚线无任何标注，读者无法理解）。demo3 以完整标注重建（标题、双轴标签、点标签、图例）——验证 0 处真实重叠。
- **v1.6.5** (2026-08-12) — 文档补强：交付 PDF 前必须运行像素级重叠验证器。SKILL.md/SKILL_ZH.md 新增"输出验证"章节（三级验证器用法 + 明确警告 PyMuPDF bbox 相交是行高模型产物，在本工具输出上 100% 为假阳性），文件结构文档补入 `verify_overlap_pixel.py`，`requires` pip 列表补入 `pymupdf`/`scipy`（验证器依赖）。demo 图改用真实数据重新生成（demo2 = KEGG 通路基因数、demo3 = ChEMBL pchembl 值）——此前 demo 数据集含退化合成值（基因数全 50 / max_phase 全 4.0），导致坐标轴被压缩成误导性密集刻度。
- **v1.6.4** (2026-08-12) — 验证器修复：`confirm_min_dist` 三级归属改为"唯一归属"（分量质心同时落入双方候选窗时归属距 origin 更近者），消除旋转 y 轴标签场景的假阳性（scatter 的 `(max phase)` 标签 × 顶部刻度 `4.00`——此前报告的"重叠"是验证器交叉归属所致，并非真实墨迹接触）。重验全部 14 张生产图 + 4 张 demo：**0 处真实重叠**。`gen_figure.py` 新增 `_ensure_ylabel_clear()` 安全网（matplotlib 实测 bbox 与刻度真实冲突时自动增大 y 轴 labelpad；无冲突时惰性不触发，当前全部图形均未触发）。
- **v1.6.3** (2026-08-12) — 标签重叠问题像素级验证闭环。所有"重叠"报告的根因：PyMuPDF 的 span/char bbox 采用字体行高模型（Noto CJK 2.856em、DejaVu 1.695em），对旋转文本系统性高估（45° 时 fs=9 报 32.3pt，真实墨迹仅 16.8pt），对竖排/堆叠标签的行 bbox 也覆盖整行行高。用三级像素验证器（连通分量 → 分量质心归属 → 600dpi 最小墨迹距离）验证全部 14 张生产图：**0 处真实墨迹重叠**。matplotlib `get_window_extent`（20.9pt vs 真实 16.8pt）略保守，防重叠机制本身正确无需改动。验证器归档于 `scripts/verify_overlap_pixel.py`；移除 `gen_figure.py` 中死导入 `math`。
- **v1.6.2** (2026-08-11) — 修复两个生产环境发现的质量问题。(1) CJK 检测改为递归：`_text_has_cjk()` 会扫描整个 data 字典（含嵌套的 composite 面板/diagram 文本），composite 面板内的中文标题现在能正确触发 Noto Sans CJK 字体加载（此前渲染成方框乱码）。(2) 标签自动防重叠：bar 图 x 轴标签 >8 个或标签 >12 字符、line 图 >10 个点、heatmap 列 >6 个或 >14 字符时自动旋转 45°；hbar 类别 >12 个时 y 轴标签字号缩小 1pt；composite 面板将 `alternate` 透传给 hbar 子图。
- **v1.6.1** (2026-08-07) — GLM 主题黄色提亮：`#D49356` → `#D79D55`（GLM-5.2 博客原图 14.3 万黄色像素的真实均值；此前取到了分布中偏暗的样本）。所有交替风格柱状图现使用更亮的暖黄色
- **v1.6.0** (2026-08-07) — 新增 `--alternate` 参数：GLM-5.2博客风格黄蓝交替柱状图。单系列 bar/hbar 图逐柱交替使用主题前两色（glm 主题下为黄 `#D79D55` / 蓝 `#70A0D0`），配合 `--hatch` 即复现博客的"黄蓝交替+黑色斜线"样式；也可与 `cool`/`okabe-ito` 等主题组合使用
- **v1.5.2** (2026-08-12) — 新增 `cool` 主题：8色冷色调配色（藏青 `#1B4965`、海蓝 `#2E6F9E`、天蓝 `#4FA3C5`、深青 `#3D8080`、中青 `#62A0A8`、钢蓝 `#5B7BA0`、石板 `#7B9AB5`、浅钢蓝 `#9DB5CC`），色相全在190-260°，色盲安全。因用户拒绝暖/饱和配色并需求素雅冷色调而创建。
- **v1.5.1** (2026-06-18) — Bug修复：`gen_km()` 在 `median_survival` 为 `null`（中位生存未达到）时崩溃；`gen_scatter()` 在 `groups` 数组长度超过 `x`/`y` 长度（composite面板）时崩溃。均已用 null/长度守卫修复。新增 `cool` 主题（藏青/海蓝/青灰/石板冷色调，色盲安全）。见 `references/pitfalls.md`。
- **v1.5.0** (2026-06-17) — 新增3种图表：水平柱状图（hbar，含比率标注"4.96x"）、多面板组合图（composite，GridSpec布局，每面板任意图表类型）、架构/流程图（diagram，色块+箭头+分组标注）；新增GLM配色方案（GLM-5.2像素提取柔和配色：`#70A0D0`蓝+`#D79D55`黄，取原图像素均值）；新增斜纹填充功能（`--hatch`，黑色线条，9种图案，打印友好）；新增 `--hatch`、`--show-ratio`、`--ratio-base`、`--horizontal` CLI参数；强制白底输出（出版标准）
- **v1.4.0** (2026-05-17) — 新增4种图表：Kaplan-Meier生存曲线（Log-rank检验、风险表、中位生存、删失标记）、ROC曲线（AUC、95%CI、最优截断点、多模型对比）、堆叠柱状图（构成比、百分比标签）、双Y轴折线图（临床评分+实验室指标同图展示）；扩展数据校验
- **v1.3.0** (2026-05-17) — 新增Okabe-Ito色盲安全配色（Nature Methods金标准）；DPI升级300→600线稿默认；新增PDF/TIFF/EPS输出；增强森林图（权重气泡、I²异质性、事件数列、分隔线）；无障碍Alt Text指南；智能DPI分场景
- **v1.2.0** (2026-05-16) — 新增版本元数据、依赖声明、负触发词、文件结构文档
- **v1.1.0** — 新增中文自动检测、CSV长格式自动转换、空数据校验
- **v1.0.0** — 初始版本：7种图表、4套配色、中文支持、统计标注

---
