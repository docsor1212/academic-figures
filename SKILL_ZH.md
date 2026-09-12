---
name: academic-figures
version: 2.4.0
date: 2026-09-11
author: docsor1212
lang: zh
description: >
  Academic-figures 论文配图一键生成（publication-ready figures）：别再为返工改图发愁。一条命令生成顶刊级论文配图：
  21种图表（柱状/散点/热力/森林/KM/ROC/
  小提琴/组合/流程/PRISMA系统综述流程图…）、7套配色（含Okabe-Ito色盲安全）、
  Nature/Lancet期刊预设，内置PDF文字重叠+最小字号双重门禁，导出前自动拦截拒稿级
  缺陷，--suggest 还能根据你的数据自动推荐该用哪种图。600dpi出版级输出
  PNG/SVG/PDF/TIFF/EPS，纯本地运行，数据不出机。中文零配置，告别乱码。
  触发词：论文配图、学术绘图、科研绘图、科研示意图、论文插图、画图、柱状图、
  热力图、散点图、森林图、KM生存曲线、ROC、小提琴图、组合图、流程图、
  PRISMA流程图、系统综述、SCI配图、数据可视化、期刊配图、色盲安全。
metadata:
  clawdbot:
    emoji: "📊"
    category: visualization
requires:
  python: ">=3.8"
  pip: ["matplotlib", "numpy", "pymupdf", "scipy"]
---

# Academic Figures — 论文配图一键生成工具

> 📊 **21种图表 · 7套配色（含色盲安全） · 零配置中文 · 600dpi出版级输出 · PDF/TIFF/SVG全支持 · PRISMA流程图**
> 纯本地运行 · 数据不出本机 · Python一条命令搞定 · 内置校验+验证门禁

**一条命令，输出即验证：**
```bash
python3 scripts/gen_figure.py -t bar -d data.json -o fig.pdf --theme okabe-ito --verify
# exit 0 = 渲染成功且无真实文字重叠；exit 2 = 检测到重叠（修复机制，不要交付）
```

## ✨ 核心亮点

| 特性 | 说明 |
|------|------|
| 📊 **15种学术图表** | 柱状图、水平柱状图、堆叠柱状图、热力图、散点图、折线图、双Y轴图、箱线图、森林图、KM生存曲线、ROC曲线、小提琴图、组合图、流程图、PRISMA流程图 |
| 🎨 **7套配色方案** | **Okabe-Ito色盲安全**（Nature Methods金标准）、GLM科技博客、cool素雅冷色调、Nature、Lancet、保守学术、通用 |
| 📐 **期刊预设** | `--journal nature/lancet --column single/double`：官方栏宽（89/183mm）、字号、字体族、600dpi 一键应用 |
| 🛡️ **数据校验** | 18种类型/别名全覆盖的结构校验；致命错误→exit 1 不落盘，警告→继续运行 |
| ✅ **验证门禁** | `--verify` 像素级重叠检查（exit 2）；`audit_pdf.py` 字号门禁（期刊最小字号） |
| 🇨🇳 **中文零配置** | 自动检测中文字体（含字典键、补充平面），彻底告别乱码，支持中英双语标签 |
| 📈 **统计标注** | 误差棒、显著性标记(p值星号)、趋势线、置信区间 |
| 🔠 **斜纹填充** | `--hatch` 一键添加黑色斜纹图案（打印友好，色盲友好） |
| 🔷🔶 **黄蓝交替** | `--alternate` 单系列柱状图逐柱交替黄蓝（GLM-5.2博客风格） |
| 📊 **比率标注** | `--show-ratio` 自动计算并标注分组间倍数（如"4.96x"） |
| 🌲 **增强森林图** | 权重气泡、I²异质性标注、事件数列、分隔线、效应量标签 |
| 📉 **KM生存曲线** | 阶梯函数、删失标记、Log-rank检验、风险表、中位生存 |
| 📐 **ROC曲线** | AUC值、95%CI、最优截断点、多模型对比 |
| 🧩 **组合图** | 多面板A+B+C，每个面板可放任意图表类型，期刊figure标准布局 |
| 📐 **流程图** | 架构/流程块、箭头、分组标注，CONSORT式研究设计图 |
| 📄 **补充图例** | `gen_legend.py` 用同一数据JSON生成期刊格式图例（"Figure 1 |"） |
| 📐 **多格式输出** | PNG 600dpi + SVG + **PDF** + **TIFF** + **EPS** |
| ♿ **无障碍支持** | Okabe-Ito色盲安全配色 + Alt Text撰写指南 |

## 图表类型

| 类型 | 命令 | 核心功能 |
|------|------|---------|
| 柱状图 | `-t bar` | 分组柱状图、误差棒、显著性标记、斜纹填充 |
| 水平柱状图 | `-t hbar` | 横向柱状图、比率标注（"4.96x"） |
| 堆叠柱状图 | `-t stacked_bar` | 构成比、百分比标签、总计标注 |
| 热力图 | `-t heatmap` | 单元格标注、自定义色阶、colorbar |
| 散点图 | `-t scatter` | 趋势线、相关系数、分组着色、点标签 |
| 折线图 | `-t line` | 多系列、误差带、标记点 |
| 双Y轴图 | `-t dual_axis` | 左右Y轴、实线+虚线、合并图例 |
| 箱线图 | `-t box` | 箱线图+抖动散点 |
| 森林图 | `-t forest` | CI横线、权重气泡、总效应菱形、I²、事件数 |
| KM生存曲线 | `-t km` | 阶梯函数、删失标记、Log-rank检验、风险表、中位生存 |
| ROC曲线 | `-t roc` | AUC、95%CI、最优截断点、多模型对比 |
| 小提琴图 | `-t violin` | 密度估计、内置均值/中位线 |
| **组合图** | `-t composite` | 多面板A+B+C，每面板任意图表类型，期刊figure布局 |
| **流程图** | `-t diagram` | 架构/流程块、箭头、分组标注，CONSORT式研究设计 |
| **PRISMA流程图** | `-t prisma` | PRISMA 2020 系统综述流程图；数字自洽自动校验（对不上拒绝出图），`lang=zh` 中文标准版 |

## 快速开始

```bash
# 0️⃣ 首次使用：一键环境准备（装依赖/检测中文字体/清理字体缓存/自检）
python3 scripts/setup_env.py

# 0️⃣ 快速体验：交互演示（选择图表类型 → 内置数据直接出图）
python3 scripts/gen_figure.py --demo --cjk
# 查看全部配色：python3 scripts/gen_figure.py --list-themes
# 某图型限制说明：python3 scripts/gen_figure.py --explain bar

# 1️⃣ 柱状图（默认 glm 素雅配色，色盲安全）
python3 scripts/gen_figure.py -t bar -d data.json -o figure.png \
  --title "图2 主标题 / Subtitle" --ylabel "准确率 Accuracy (%)"

# 水平柱状图 + 比率标注 + GLM配色（科技博客风格）
python3 scripts/gen_figure.py -t hbar -d throughput.json -o perf.png --theme glm \
  --show-ratio --title "吞吐量提升" --xlabel "归一化吞吐量"

# 柱状图 + 斜纹填充（GLM 黄蓝斜线招牌风格，打印友好，色盲友好）
python3 scripts/gen_figure.py -t bar -d data.json -o hatch.png --style glm-hatch \
  --show-values --title "ACR50缓解率"

# Meta分析森林图（PDF输出）
python3 scripts/gen_figure.py -t forest -d forest.json -o forest.pdf --theme okabe-ito

# Kaplan-Meier生存曲线 + Log-rank检验
python3 scripts/gen_figure.py -t km -d survival.json -o km.png --theme okabe-ito \
  --title "图3 Kaplan-Meier生存曲线" --xlabel "时间 (月)" --ylabel "生存概率"

# ROC曲线 + AUC
python3 scripts/gen_figure.py -t roc -d roc.json -o roc.png --theme okabe-ito \
  --title "图4 ROC曲线" --xlabel "1 - 特异度" --ylabel "敏感度"

# 堆叠柱状图（亚组构成比）
python3 scripts/gen_figure.py -t stacked_bar -d subgroups.json -o stacked.png --theme okabe-ito \
  --title "图5 ANCA相关血管炎器官受累"

# 双Y轴图（临床评分+实验室指标）
python3 scripts/gen_figure.py -t dual_axis -d dual.json -o dual.png --theme okabe-ito \
  --title "图6 CRP与DAS28随治疗变化"

# Nature双栏投稿：栏宽183mm、7pt Helvetica、最小字号5pt
python3 scripts/gen_figure.py -t bar -d data.json -o nat.pdf --journal nature --column double
python3 scripts/audit_pdf.py nat.pdf --min-size 5          # 字号门禁（nature=5pt）

# 多面板组合图（Panel A+B+C，期刊figure布局）
python3 scripts/gen_figure.py -t composite -d composite.json -o figure4.png --theme okabe-ito

# 架构/流程图（研究设计，CONSORT式）
python3 scripts/gen_figure.py -t diagram -d flow.json -o flow.png --theme glm --width 12 --height 6

# 热力图（自定义色阶 + 中文）
python3 scripts/gen_figure.py -t heatmap -d data.json -o heatmap.png --cjk \
  --cmap RdBu_r --vmin -20 --vmax 45

# Lancet投稿TIFF格式（照片内容 → 300dpi）
python3 scripts/gen_figure.py -t bar -d data.json -o figure.tiff --dpi 300 --theme lancet

# 补充图例（期刊格式，同一数据JSON）
python3 scripts/gen_legend.py -d data.json -t "治疗应答" -f 1 -o legend.txt
```

## ⚠️ 边界与限制（先看这个，免试错）

**数据量**：cluster_heatmap ≤3000 行；pca ≤200 特征列；venn 2~3 集合；paired/bland_altman 需等长；km 无硬上限（5 万行实测 3s）。
**参数兼容**：`--stats` 仅 box/violin；`--compare` 仅 roc（需 labels+scores）；`--egger` 仅 funnel；`--hatch` 仅 bar 系；`--sheet` 仅 xlsx；`--journal` 会锁定宽度（`--width` 被覆盖）。
**输出**：投稿矢量图用 PDF/EPS；位图默认 600dpi（线条）/300（照片）。

完整矩阵见 `references/limits.md`（超限一律中文报错+修正建议，不出半成品图）。
常见问题速答见 `references/faq.md`（安装/数据/参数/投稿四组高频 Q&A）。

## 配色方案

**默认配色 = `glm`**（素雅莫兰迪风，色盲安全）——美观不刺眼，单序列图表也有暖黄点缀，不单调。

| 方案 | 说明 | 色盲安全 |
|------|------|---------|
| `glm` ⭐默认 | 素雅莫兰迪（钢蓝/暖黄/鼠尾草绿/灰紫/珊瑚）— 美观+色盲安全，默认首选 | ✅ 是 |
| `okabe-ito` | Nature Methods金标准（Wong 2011）— 鲜艳，期刊投稿首选 | ✅ 是 |
| `cool` | 素雅冷色调（藏青/海蓝/青灰/石板色，色相190-260°） | ✅ 是 |
| `classic` | 经典 matplotlib 色板（v2.0 前的旧默认，兼容保留） | ❌ |
| `nature` | NPG Nature期刊配色 | ❌ |
| `lancet` | Lancet医学配色 | ❌ |
| `conservative` | 保守学术配色 | ❌ |

### 查看与选择配色（v2.0.1 新增）

```bash
# 终端内直接查看全部配色（彩色色块 + 说明）
python3 scripts/gen_figure.py --list-themes

# 生成某套配色的色板预览图（可放文档/投稿材料）
python3 scripts/gen_figure.py --theme-swatch glm -o swatch.png

# 便捷别名（记不住全名也能用）
#   okabe → okabe-ito   colorblind → okabe-ito   default/classic → glm
# 大小写不敏感、自动前缀匹配（--theme gla → glm）
```

> **⚠️ 投稿建议**：期刊投稿用 `--theme okabe-ito`（Nature、Science、Cell 等主流期刊强制要求色盲友好图表，红绿配色是常见退稿原因）。
>
> **🎨 日常偏好**：非投稿场景（演示、博客、报告）用默认 `glm` 即可——素雅柔和、色盲安全、有品牌辨识度。避免大红大绿大黄配色方案。

### GLM 黄蓝斜线风格（招牌风格，v2.0.1 新增）

```bash
# 一键启用：GLM 素雅莫兰迪配色 + 黑色斜纹填充
python3 scripts/gen_figure.py -t bar -d data.json -o fig.png --style glm-hatch --cjk

# 等价于 --theme glm --hatch
```

- **适合**：柱状图/水平柱状图/堆叠柱状图/森林图（`--style glm-hatch` 自动作用于这些类型）
- **优势**：黄蓝交替+斜纹，打印/黑白/复印场景依然清晰可辨；色盲安全
- **更多样式**：`--alternate` 单系列黄蓝逐柱交替；`--hatch` 可搭配任意主题使用

### 为什么选 Okabe-Ito？

Okabe-Ito配色是色盲安全学术可视化的金标准：
- **Nature Methods专栏明确推荐**（Wong 2011, Nat Methods 8:441）
- 8种颜色在红色盲、绿色盲、蓝色盲下均可区分
- 视觉鲜明——与传统配色无审美差距

## 期刊投稿预设（v2.0）

`--journal nature|lancet` + `--column single|double` 自动应用期刊官方栏宽、字号、字体族和DPI。栏宽取自官方作者指南：

| 期刊 | 栏位 | 宽度 | 字号 | 最小字号 | 字体族 | DPI |
|------|------|------|------|---------|--------|-----|
| `nature` | 单栏 | 89mm (3.50in) | 7pt | **5pt** | Helvetica | 600 |
| `nature` | 双栏 | 183mm (7.20in) | 7pt | **5pt** | Helvetica | 600 |
| `lancet` | 单栏 | 85mm (3.35in) | 8pt | **6pt** | Arial | 600 |
| `lancet` | 双栏 | 183mm (7.20in) | 8pt | **6pt** | Arial | 600 |

高度按主题纵横比自动计算；显式 `--width/--height` 可覆盖。stderr 会打印预设信息和对应的 `audit_pdf.py --min-size` 门禁提示：

```bash
python3 scripts/gen_figure.py -t forest -d forest.json -o nat.pdf --journal nature --column double
# stderr: Journal preset: nature (double-column, width=7.20in, font=Helvetica 7pt, min text 5pt
#          — verify with audit_pdf.py --min-size 5)
python3 scripts/audit_pdf.py nat.pdf --min-size 5
# OK: no text below 5pt in nat.pdf
```

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
  `-t venn`（2~3 集合精确区域计数，不按面积比例）、`-t cluster_heatmap`（Ward 聚类重排，行数上限 3000）。
- **`--batch figures.json`** 批量出图（逐项独立进程，输出 .batch-report.json 汇总）；
  **`--caption`** 生成中英双语期刊式图注（<输出名>.caption.txt）。
- 极端输入统一友好报错（中文提示+修正建议，绝不裸 traceback）；写出失败自动重试一次。

## 数据校验与退出码（v2.0）

每次运行都经过 `validate_data(data, chart_type)` —— 覆盖全部 18 种类型/别名分支的结构校验。两个严重级别：

| 级别 | stderr前缀 | 效果 | 退出码 |
|------|-----------|------|--------|
| **致命** | `ERROR:` | 数据不可用（如空系列、系列长度不匹配、缺少必需键、ROC AUC超出[0,1]） | `1`（不落盘） |
| **警告** | `WARNING:` | 数据可用但有隐患（如缺少建议键） | `0` |
| **验证失败** | （来自`--verify`） | PDF已渲染但像素级检测到文字重叠 | `2` |

致命错误示例：bar 的 `series` 长度不一致；box/violin 的 `labels` 数量 ≠ 组数（见边界情况）；ROC 的 `curves[].auc` > 1。

## 验证与质量门禁（v2.0）

任何可交付图片必须通过两道门禁，补充材料再加一道：

### 1. `--verify`（内联，PDF输出时）

```bash
python3 scripts/gen_figure.py -t km -d survival.json -o km.pdf --theme okabe-ito --verify
# 检测到像素级文字重叠 → exit 2 + 提示 — 修复机制本身，不要逐图特判。
```

### 2. `audit_pdf.py` — 字号门禁（期刊最小字号）

```bash
python3 scripts/audit_pdf.py figure.pdf --min-size 5 --fail-below
# --fail-below: 存在小于 --min-size 的文本时以非零码退出
# --max-reports N: 限制违规列表条数（默认20）
```

### 3. `verify_overlap_pixel.py` — 重叠验证器（交付每个 PDF 前必跑）

```bash
python3 scripts/verify_overlap_pixel.py output.pdf
# 输出 "文本对=N 候选=M 真实重叠=K" — K 必须为 0。
```

**关键警告——不要相信 PyMuPDF bbox 相交报告。** PyMuPDF 的 span/char bbox 采用字体行高模型（Noto CJK 2.856em、DejaVu 1.695em），对旋转文本/竖排标签**系统性高估**（45° 时 fs=9 报 32.3pt，真实墨迹仅 16.8pt）。两个 bbox 相交 ≠ 真实重叠——在本工具的输出上，此类报告 100% 是假阳性。验证器用三级流程消除误报：

1. 全页渲染 → 连通分量（网格线/矢量图的大分量被过滤）
2. 分量质心归属到 char bbox
3. 候选对 600dpi 局部重渲染 → 最小墨迹距离（> 0.05pt 即判定分离）

**防重叠机制已内建于 `gen_figure.py`**（密集柱状图 x 轴标签自动 45° 旋转、hbar >12 类目字号缩小、`_ensure_ylabel_clear()` labelpad 自动避让）。若验证器报出真实重叠>0，说明图确实坏了——应修机制，不要逐图特判。

### 质量门禁可回归测试

仓库附带回归套件，任何改动后都可重新验证门禁：

```bash
python3 tests/run_tests.py          # 50 个 unittest 测试 — 必须全过
# evals/evals.json: 8 个行为评测（退出码、CJK自动加载、期刊预设、图例审计…）
```

## 补充图例（v2.0）

禁止图内图例的期刊（如Nature）需要单独的图例块。`gen_legend.py` 用**与出图相同的**数据JSON生成期刊格式图例（"Figure 1 | 标题…"），图例文字与系列/颜色永远一致：

```bash
python3 scripts/gen_legend.py -d data.json -t "治疗应答" -f 1 -o legend.txt
# -d/--data: 与 gen_figure.py 相同的数据JSON   -t/--title: 图例标题
# -f/--figure: 图号（默认1）   --type: 图表类型（默认bar）
# --error-type: 误差棒描述（默认 "s.e.m."）   -o: 输出文件（默认stdout）
```

## 中文支持（CJK）

传 `--cjk` 自动检测并加载系统中文字体，零手动配置：

```bash
python3 scripts/gen_figure.py -t bar -d data.json -o fig.png --cjk
```

字体检测优先级：Noto Sans CJK → PingFang → Microsoft YaHei → WQY → AR PL → Droid。

自定义字体：`--cjk-font /path/to/font.ttf`

**CJK 自动检测是递归的**（v1.6.2+）：`_scan_cjk()` 遍历整个 data 字典——**值和键**（v2.0），包括嵌套的 composite 面板和 diagram 文本——所以中文系列名（如 `"对照组"`）独自即可触发字体加载。检测覆盖**补充平面**（Ext-B..F `U+20000–U+2EBEF`、Ext-G `U+30000–U+3134F`）加基本 BMP 区段（v2.0）。

## 输出格式

| 格式 | 扩展名 | DPI | 适用场景 |
|------|--------|-----|----------|
| PNG | `.png` | 600（默认） | 通用、演示文稿 |
| SVG | `.svg` | 矢量 | Web、可编辑图形 |
| **PDF** | `.pdf` | 矢量 | **期刊投稿首选** |
| TIFF | `.tiff` | 600（可 `--dpi 300`） | Nature/Lancet照片要求 |
| EPS | `.eps` | 矢量 | 传统期刊要求 |

> **投稿技巧**：Nature和Science偏好**PDF/EPS矢量**格式用于线稿。使用 `.pdf` 或 `.eps` 扩展名即可。

### DPI标准（2026年）

| 内容类型 | 所需DPI | 用法 |
|----------|---------|------|
| 线稿（图表） | 600-1000+ | 默认600；严格期刊用 `--dpi 1000` |
| 照片/显微图 | 300-600 | 用 `--dpi 300` |
| 混合型 | 600 | 默认 |
| 矢量（PDF/SVG/EPS） | 不适用 | 分辨率无关 |

## 常用参数

| 参数 | 说明 |
|------|------|
| `--title "文字"` | 图表标题 |
| `--xlabel`, `--ylabel` | 坐标轴标签 |
| `--width N`, `--height N` | 图表尺寸（英寸） |
| `--format F` | 强制输出格式：png, svg, pdf, tiff, eps |
| `--dpi N` | 覆盖DPI设置 |
| `--show-values` | 柱状图显示数值标签 |
| `--show-ratio` | 显示分组间比率标注（如"4.96x"） |
| `--ratio-base N` | 比率计算的基准系列索引（默认0） |
| `--hatch` | 添加黑色斜纹图案（打印友好，10种图案循环） |
| `--alternate` | GLM-5.2博客风格：单系列柱状图逐柱交替使用主题前两色（配合 `--theme glm --hatch` 即黄蓝交替黑斜线） |
| `--no-trend` | 隐藏散点趋势线 |
| `--no-legend` | 隐藏图例 |
| `--cmap NAME` | 热力图色阶（默认数据驱动：全正数据自动用 YlOrRd 暖色渐变无断层；含负值用 RdBu_r 红蓝发散；显式指定覆盖） |
| `--vmin`, `--vmax` | 热力图数值范围 |
| `--cjk` | 强制加载中文字体（数据含中文时也会自动检测） |
| `--cjk-font PATH` | 自定义中文字体文件 |
| `--journal nature\|lancet` | 应用期刊预设（栏宽/字号/DPI，见上） |
| `--column single\|double` | `--journal` 的栏位布局（默认双栏） |
| `--verify` | 对PDF输出做像素级重叠验证，发现重叠 exit 2 |

## 常见问题 FAQ（v2.0.1）

1. **首次使用报 ModuleNotFoundError？** 运行 `python3 scripts/setup_env.py` 一键安装依赖（matplotlib/numpy/pymupdf/scipy）、检测中文字体、清理字体缓存并自检。
2. **中文显示成方块/乱码？** 多为字体缓存问题：先 `python3 scripts/setup_env.py`（自动清缓存），或手动删除 `~/.cache/matplotlib` 后重跑。需系统已装中文字体（Linux: `fonts-noto-cjk`；macOS/Win 系统自带）。
3. **CSV 数据支持误差棒吗？** 不支持——CSV 只有标签+数值列。误差棒/显著性标注需用 JSON 的 `errors`/`significance` 字段。触发时报错会附带此提示。
4. **如何快速看全部配色？** `python3 scripts/gen_figure.py --list-themes`（终端内彩色色块）或 `--theme-swatch glm -o swatch.png` 生成色板图。
5. **记不住主题全名？** 别名可用：`okabe`/`colorblind`→okabe-ito，`default`/`classic`→glm；大小写不敏感，支持前缀匹配（`--theme gla` → glm）。
6. **如何快速上手？** `python3 scripts/gen_figure.py --demo --cjk` 交互式选择图表类型直接出图；`--explain <类型>` 查看该类型的限制与推荐用法。

## 边界情况（v2.0，来自回归测试）

1. **Box/Violin 的 `labels` = 组名。** `labels` 按**系列/组数**校验，不是按数值个数。`{"labels": ["A","B"], "series": [[..],[..]]}` 正确；逐值标签列表会校验失败。
2. **ROC AUC 逐条曲线检查边界。** `curves[].auc` 必须在 [0,1]；检查覆盖每条模型曲线，不只看顶层 `auc`。
3. **组合图图例绝不重复句点。** 图例文字恰好以一个 `.` 结尾（`_fmt_n` 格式化器自带句点——不再追加）。
4. **字典键中的中文。** `series`/`groups` 中的中文键通过键扫描触发 CJK 字体加载；否则系列标签在图例中渲染成方块乱码。
5. **CJK 补充平面。** 极罕见的中文表意文字在 Ext-B..G 区段（如 㐀、𠀀）也能检测；发布前用 `detect_cjk_font.py` 验证字形覆盖。

## ♿ 无障碍 & Alt Text

投稿时需为每个图表提供**Alt Text**描述。示例：
> "柱状图显示治疗组（均值75，标准差3）与对照组（均值68，标准差2）的比较。误差棒表示标准差。星号表示统计学显著性（p < 0.001）。"

Springer Nature、NSF等主要出版商均要求Alt Text以符合无障碍标准。

## 数据输入

JSON（完整功能）或 CSV（基础功能）。详见 `references/data-formats.md`。

**JSON柱状图示例:**
```json
{
  "labels": ["对照组", "实验组"],
  "series": {"治疗前": [75, 82], "治疗后": [68, 70]},
  "errors": {"治疗前": [3, 2], "治疗后": [2, 1]},
  "significance": {"治疗前:0": "***", "治疗后:1": "NS"}
}
```

**KM生存曲线示例:**
```json
{
  "groups": {
    "治疗组": [[12,1],[24,1],[36,0],[48,1],[60,0],[72,0]],
    "对照组": [[6,1],[10,1],[18,1],[30,1],[42,0],[48,1]]
  },
  "log_rank": {"p": 0.032, "method": "Log-rank"},
  "risk_table": {
    "times": [0, 12, 24, 36, 48],
    "治疗组": [50, 42, 35, 28, 20],
    "对照组": [50, 38, 25, 15, 8]
  }
}
```

**ROC曲线示例:**
```json
{
  "fpr": [0.0, 0.05, 0.10, 0.15, 0.30, 0.50, 1.0],
  "tpr": [0.0, 0.45, 0.68, 0.82, 0.92, 0.96, 1.0],
  "auc": 0.912,
  "ci": {"low": 0.854, "high": 0.958},
  "cutoff": {"fpr": 0.15, "tpr": 0.88, "threshold": 2.35}
}
```

## Agent 用 Python 出图时（非CLI）

若通过 Python 脚本而非 CLI 出图：

1. 任何标签可能含中文时，先调用 `detect_cjk_font()`
2. 所有含中文的文本调用都使用 `fontproperties=font_prop`
3. 设置 `plt.rcParams['axes.unicode_minus'] = False`（防止负号变方框）
4. **多类别图使用 Okabe-Ito 配色**
5. 验证输出：多标签图文件 >20KB 说明字体已加载
6. 首选输出：投稿用 **PDF**，预览用 600 DPI PNG
7. **斜纹偏好**：用户偏爱斜纹/条纹柱状图（`--hatch`），打印友好且系列可区分。斜纹线为**黑色**（`edgecolor='black'`）。斜纹激活时不要手动覆盖 `edgecolor`——由 `gen_bar` 处理。
8. **强制白底**：本工具面向期刊投稿。所有输出必须白底（`facecolor='white'`）。深色/黑色背景**永不接受**。不要添加深色主题或深色背景选项。
9. **校验**：渲染前运行 `validate_data(data, chart_type)` 并检查致命信息（与CLI同一套门禁）。
10. **验证**：交付任何 PDF 前运行 `verify_overlap_pixel.py`。

## 设计原则

1. **白底不可妥协。** 本技能面向期刊投稿（Nature、Lancet、Science）。`save_kwargs["facecolor"]` 硬编码为 `'white'`。永不添加深色主题支持。
2. **斜纹 = 彩色填充上的黑线。** `--hatch` 激活时斜纹线为黑色，保证任何填充色上都可见，无需深色背景。每个系列循环不同图案以便黑白打印区分。
3. **glm 为默认，okabe-ito 用于投稿。** 默认主题为 `glm`（素雅、色盲安全）。期刊投稿始终推荐 `--theme okabe-ito` 保证色盲安全。`cool` 适合全冷色调内容。

## CJK 陷阱

1. **CJK 字体可能缺少 Unicode 上下标。** 如 `⁹` (U+2079)、`³` (U+00B3)、`²` (U+00B2) 常触发 Noto Sans CJK 的 "Glyph X missing" 警告。改用纯文本写法：`10^9/L` 代替 `×10⁹/L`。发布前用 `detect_cjk_font.py` 检查字形覆盖。

## 流程图陷阱

1. **块颜色绝不使用 `#FFFFFF`** —— 白块在强制白底上不可见。用主题配色或任何可见十六进制色。
2. **同一轴线上两个相连块之间不要放中间块** —— 箭头路由算法按中心坐标选最近边。夹在垂直相连两块之间的块会导致箭头连错目标。改为把旁注并入目标块的 `sublabel`。
3. **CONSORT式排除框**应从主垂直流程水平偏移（同Y不同X），用水平箭头连接。

## 负向触发（不要为本技能触发）

- SVG医学示意图（→ medical-svg）
- 终端/CLI图表（→ data-viz）
- 频谱图/时频分析（→ pywayne-plot）
- HTML幻灯片演示（→ html-presentation-restyler）
- 纯数据分析不含可视化（→ data-analysis）

## 文件结构

```
academic-figures/
├── SKILL.md                 ← 英文文档
├── SKILL_ZH.md              ← 中文文档（本文件）
├── scripts/
│   ├── gen_figure.py        ← 主生成器（matplotlib+numpy）
│   ├── gen_legend.py        ← 补充图例生成器（期刊格式，v2.0）
│   ├── audit_pdf.py         ← 字号审计器（--min-size 门禁，v2.0）
│   ├── detect_cjk_font.py   ← CJK字体自动检测器
│   ├── verify_overlap_pixel.py ← 像素级标签重叠验证器（每个PDF交付前必跑）
│   └── setup_env.py         ← 一键环境准备（依赖/CJK字体/缓存/自检，v2.0.1）
├── tests/
│   └── run_tests.py         ← 96个unittest回归测试（v2.1.0）
├── evals/
│   └── evals.json           ← 8个行为评测（退出码、CJK、期刊预设，v2.0）
├── examples/
│   └── example_*.json       ← 21种图表类型可直接运行的示例数据
└── references/
    ├── data-formats.md      ← 各图表类型JSON/CSV schema
    ├── pitfalls.md          ← 常见错误和白底规则
    └── reverse-engineering-colors.md  ← 从参考图提取精确颜色
```

## 版本历史

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

## 🚀 进阶版：论文配图一键生成 Pro

不想配 Python 环境、或需要团队批量出图？**academic-figures-pro** 提供同一渲染引擎的云端服务：
上传数据即出图，投稿级 300dpi TIFF+PNG 双文件直出，内置中华医学会/中文核心期刊规格，
按次计费（¥0.5/次）。在 SkillHub 搜索 `academic-figures-pro` 即可使用。
