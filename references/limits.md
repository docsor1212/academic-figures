# 边界与限制速查（Limits & Compatibility）

> 一页说清所有"数字边界"和"参数能不能一起用"，免试错。投稿前建议通读一遍。
> 数值边界由代码强制执行：越界时不会出半成品图，而是中文报错并给出修正建议。

## 一、数据量边界（代码强制）

| 维度 | 上限 | 超出行为 |
|---|---|---|
| km / survival 每组样本 | 无硬上限（5 万行实测 3s 渲染） | — |
| cluster_heatmap 行数 | **3000 行** | 友好报错：请先筛选特征/样本 |
| pca 特征列数 | **200 列** | 友好报错：请先降维/筛选 |
| pca 最少样本 | 3 行 | 报错提示 |
| venn 集合数 | **2~3 个** | 报错提示 |
| paired / bland_altman | 两组**等长**数据 | 报错提示实际长度差 |
| heatmap 矩阵 | 无硬上限；>200×200 建议 PNG/SVG（TIFF 会很大） | — |
| Shapiro 正态检验 | 每组 n>5000 自动跳过（视为正态） | stderr 提示 |
| --stats multi 括号绘制 | 最多画 8 对显著对比 | stderr 提示（完整结果仍在） |
| paired 配对检验 | n≥6 才做统计标注 | stderr 提示"效力不足" |

## 二、参数兼容矩阵（谁能和谁一起用）

| 参数 | 适用图型 | 其他图型上传入时 |
|---|---|---|
| `--stats auto` / `--stats multi` | 仅 box / violin | 静默忽略 |
| `--compare`（DeLong） | 仅 roc，且需 `labels` + 各曲线 `scores` | 只有 fpr/tpr 时 stderr 提示无法检验 |
| `--egger` | 仅 funnel（≥3 研究） | 静默忽略 |
| `--no-risk-table` / `--risk-times` | 仅 km（原始 `[时间,事件]` 格式） | 预计算曲线格式时 stderr 提示 |
| `--hatch` | bar 系（bar/grouped_bar/hbar/stacked_bar） | 静默忽略 |
| `--cmap` / `--vmin` / `--vmax` | heatmap / cluster_heatmap | 静默忽略 |
| `--trend` / `--no-trend` | scatter | 静默忽略 |
| `--sheet` | 仅 `--data *.xlsx` | CSV/JSON 时忽略 |
| `--show-ratio` / `--ratio-base` | grouped_bar | 静默忽略 |
| `--lang zh` | prisma（中文标准措辞版） | 静默忽略 |
| `--horizontal` | bar（等同 hbar） | — |
| `--annotate "x,y:文字"` | 所有图型（组合图自动选面板） | 坐标越界/类别不匹配 → 中文报错 exit 1 |
| `--legend-loc` / `--legend-outside` | 有图例的图型；组合图 outside=共享图例 | 无图例时 stderr 提示未生效 |
| `--area` | 仅 venn | 其他图型 → 中文报错 exit 1 |

## 三、参数组合的注意事项

- `--journal` 与 `--width`：journal 预设**锁定宽度**（单/双栏），`--width` 会被覆盖；`--height` 仍生效。要自定义尺寸就别用 `--journal`，改 `--width/--height`。
- `--journal cma / cn-core` 自动启用中文字体，无需再加 `--cjk`（加了也不冲突）。
- `--stats multi` 与 `--stats auto` 互斥（后者被忽略）；**两组数据请用 auto**（multi 会提示需 ≥3 组）。
- `--verify` 仅对 PDF 输出有意义（像素级文字重叠检查，发现重叠退出码 2）。
- `--demo` 不需要 `--data`；`--suggest` 需要 `--data`。
- 组合图（composite）的 panels 子图支持除 composite/diagram 外的所有图型；**面板内不能再嵌套 composite**。
- `--journal nejm|lancet|science|nature` 未显式给 `--theme` 时自动联动同款配色；显式 `--theme` 优先。
- venn `--area`：2 集合精确；3 集合为最优拟合（圆无法精确实现任意 7 区域面积），拟合偏差在
  stderr 如实报告；0 计数区域无面积、图中省略数字（stderr 说明）。

## 四、输出格式边界

| 格式 | 说明 |
|---|---|
| png / tiff | 位图；默认 DPI：线条图 600、照片类 300（`--dpi` 覆盖，建议 72–600） |
| pdf / svg / eps | 矢量，DPI 不适用；**投稿矢量图优先 PDF/EPS** |
| tiff | 自动 LZW 无损压缩 |
| 中文 | 任何格式均可；`--cjk` 自动探测，或 `--cjk-font` 指定字体文件 |

## 五、数据格式入口

各图型字段要求见 `references/data-formats.md`；十场景+六新图型的可运行示例在
`templates/`（每个 JSON 头部带 `_command`，复制即可跑）；组合图布局见
`references/composite-layouts.md`。PRISMA 数字自洽校验规则见 `--explain prisma`。
