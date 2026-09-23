# Advanced Usage / 深水区进阶

> 从主文档外移的进阶内容：统计深水区与投稿精修。主文档保持精简，按需查阅本文件。

## Statistics Deep-Dive (English)

## Statistics Deep-Dive (v2.3)

- **KM auto risk table + log-rank**: raw `[time, event]` data with >=2 groups now
  auto-renders a "Number at risk" table under the plot and auto-runs a
  Mantel-Haenszel log-rank test (annotated in-plot). `--no-risk-table` opts out;
  `--risk-times T1,T2,...` sets custom display times. Precomputed survival curves
  are now detected and drawn correctly.
- **`--stats multi`** (box/violin): all-pairs comparisons — ANOVA+Tukey HSD when
  all groups pass Shapiro, otherwise Kruskal-Wallis + Dunn with Hochberg adjust.
- **ROC `--compare`**: paired DeLong test between >=2 model AUCs (needs `labels`
  plus per-curve raw `scores`; fpr/tpr-only curves cannot be DeLong-tested).
- **New chart types**: `-t funnel` (Meta funnel, DL pooled line, `--egger`),
  `-t bland_altman` (LoA), `-t pca` (scores + group ellipses + top-5 loadings),
  `-t paired` (before-after lines + paired test), `-t venn` (2-3 sets, exact
  region counts; `--area` for area-proportional Euler mode), `-t cluster_heatmap`
  (Ward-reordered matrix, <=3000 rows).

## Submission Polish (English)

## Submission Polish (v2.5)

- **`--annotate "x,y:text"`** — reviewer-request tweaks on the exact data point:
  arrow annotation at data coordinates, repeatable, with automatic declutter
  (texts repel + spring back to anchor; arrows follow). Category axes accept
  tick labels instead of numbers:
  ```bash
  python3 scripts/gen_figure.py -t scatter -d d.json -o f.png \
      --annotate "3.2,5.1:p=0.01" --annotate "6.0,7.4:outlier"
  python3 scripts/gen_figure.py -t bar -d d.json -o f.png --annotate "高剂量,4.2:显著上调"
  ```
  Coordinates must land inside the plotted range (or match a tick label);
  otherwise the CLI exits 1 listing the valid ranges/labels.
- **`--legend-loc LOC`** — explicit legend position (best/upper right/.../center);
  **`--legend-outside`** — moves the legend outside the plot area; on composite
  figures it merges all panels' legends into one shared figure legend
  (duplicate entries deduped).
- **venn `--area`** (Euler mode) — circles sized so areas match region counts
  (default mode stays equal-circle with exact numbers). 2 sets: exact analytic
  layout; 3 sets: least-squares fit of centers+radii (circles cannot realize
  every region combination exactly — achieved fit is reported on stderr).
  Region counts now also accept a dedicated `"regions"` key:
  `{"regions": {"A": 30, "B": 25, "AB": 9}}` (2 sets, exactly 3 keys) or all
  7 keys for 3 sets. (The numeric form of `"sets"` documented in v2.3 never
  parsed — fixed in v2.5.)
- **NEJM / Science color themes** — official-style palettes joining lancet;
  `--journal nejm|science` auto-selects the matching theme (see Color Themes).
- Library exception Chinese mapping expanded 9 → 18 (ParserError → "CSV 解析失败",
  MemoryError → "数据规模超出可用内存", InvalidFileException → "不是有效的 xlsx", ...).

## 统计深水区（中文）

## 统计深水区（v2.3）

- **KM 自动风险表 + 自动 log-rank**：原始 `[时间, 事件]` 数据且 >=2 组时，自动在图下渲染
  "Number at risk" 风险表、自动做 Mantel-Haenszel log-rank 检验并图内标注；
  `--no-risk-table` 关闭；`--risk-times 2,6,10` 自定义显示时间点。预计算生存曲线格式自动识别正确绘制。
- **KM 自动中位生存（v2.4）**：每组自动计算中位生存时间及 95%CI（Greenwood log-log 法），与 log-rank 同框标注；`--no-median` 关闭。曲线未降到 50% 时如实标注"未到达"。
- **forest --sensitivity（v2.4）**：留一法敏感性分析——自动省略每项研究重新合并，13+N 行画在同一图下方；需 se_list 或对称 CI。
- **`--stats multi`**（box/violin）：全两两比较——全组过 Shapiro→ANOVA+Tukey HSD；
  否则 Kruskal-Wallis+Dunn（Hochberg 校正）。
- **ROC `--compare`**：>=2 个模型 AUC 的配对 DeLong 检验（需 labels + 各曲线原始 scores）。
- **新图型**：`-t funnel`（Meta 漏斗，DL 合并线，`--egger` 不对称检验）、`-t bland_altman`
  （一致性界值）、`-t pca`（得分+分组椭圆+载荷 top5）、`-t paired`（配对前后线+配对检验）、
  `-t venn`（2~3 集合精确区域计数；`--area` 面积比例 Euler 模式）、`-t cluster_heatmap`（Ward 聚类重排，行数上限 3000）。
- **`--pipeline analysis.yaml`**（v2.6）多图流水线：defaults 全局默认 + figures 逐图清单，
  一篇论文全部图表一条命令出齐（YAML 需 pyyaml，JSON 免依赖；原 --batch 保留）；
  **`--multi-format tiff,png,pdf`**（v2.6）一次渲染多格式导出，文件名同源；
  **`--batch figures.json`** 批量出图（逐项独立进程，输出 .batch-report.json 汇总）；
  **`--caption`** 生成中英双语期刊式图注（<输出名>.caption.txt）。
- 极端输入统一友好报错（中文提示+修正建议，绝不裸 traceback）；写出失败自动重试一次。

## 投稿精修（中文）

## 投稿精修（v2.5）

- **`--annotate "x,y:文字"`**——审稿改稿第一刚需：在数据坐标处画箭头注释，可重复使用；
  文字自动防重叠（互斥+锚点回弹，箭头跟随）。类别轴可直接写刻度标签：
  ```bash
  python3 scripts/gen_figure.py -t scatter -d d.json -o f.png \
      --annotate "3.2,5.1:p=0.01" --annotate "6.0,7.4:离群点"
  python3 scripts/gen_figure.py -t bar -d d.json -o f.png --annotate "高剂量,4.2:显著上调"
  ```
  坐标须落在图内数据范围（或匹配刻度标签），否则 exit 1 并列出可用范围/标签。
- **`--legend-loc 位置`**——图例九宫格定位（best/upper right/…/center）；
  **`--legend-outside`**——图例移到绘图区外侧；组合图自动合并为全图共享图例（同名去重）。
- **venn `--area`**（Euler 面积比例模式）——圆的大小与交集面积按区域计数比例
  （默认仍为等圆示意+精确数字）。2 集合解析解精确；3 集合圆心+半径联合最优拟合
  （圆无法精确实现任意区域组合，实际拟合偏差在 stderr 如实报告）。
  区域计数也可用独立键：`{"regions": {"A": 30, "B": 25, "AB": 9}}`（2 集合恰 3 键，
  3 集合恰 7 键）。（v2.3 文档承诺的数字型 `"sets"` 从未可用，v2.5 修复。）
- **NEJM / Science 配色主题**——与 lancet 并列的官方风色板；
  `--journal nejm|science` 自动联动同款配色（见配色方案）。
- 库异常中文映射 9 → 18 条（ParserError→"CSV 解析失败"、MemoryError→"数据规模超出
  可用内存"、InvalidFileException→"不是有效的 xlsx" 等）。
