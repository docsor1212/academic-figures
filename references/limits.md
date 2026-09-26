# 边界与限制速查（Limits & Compatibility）

> 一页说清所有"数字边界"和"参数能不能一起用"，免试错。投稿前建议通读一遍。
> 数值边界由代码强制执行：越界时不会出半成品图，而是中文报错并给出修正建议。

## 一、数据量边界（代码强制）

| 维度 | 上限 | 超出行为 |
|---|---|---|
| km / survival 每组样本 | 无硬上限（5 万行实测 3s 渲染） | — |
| cluster_heatmap 行数 | **3000 行** | v3.1 起 >3000 行自动等距采样到 2000 行并显著告知（`--downsample N` 可自定行数） |
| pca 特征列数 | **200 列** | 友好报错：请先降维/筛选 |
| pca 最少样本 | 3 行 | 报错提示 |
| venn 集合数 | **2~4 个**（4 集合为椭圆布局；区域计数需恰 15 键） | 报错提示 |
| paired / bland_altman | 两组**等长**数据 | 报错提示实际长度差 |
| heatmap 矩阵 | 无硬上限；>200×200 建议 PNG/SVG（TIFF 会很大） | — |
| Shapiro 正态检验 | 每组 n>5000 自动跳过（视为正态） | stderr 提示 |
| --stats multi 括号绘制 | 最多画 8 对显著对比 | stderr 提示（完整结果仍在） |
| paired 配对检验 | n≥6 才做统计标注 | stderr 提示"效力不足" |

## 二、参数兼容矩阵（谁能和谁一起用）

| 参数 | 适用图型 | 其他图型上传入时 |
|---|---|---|
| `--stats auto` / `--stats multi` / `--stats bootstrap` | 仅 box / violin | 静默忽略 |
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

## 六、输出与默认行为交互（v2.9 收拢：易忽略的参数交互）

| 交互/默认 | 事实 | 建议 |
|---|---|---|
| `--journal` × `--width` | journal 预设锁定宽度，`--width` 被覆盖（`--height` 仍生效） | 要自定义尺寸就不加 `--journal` |
| PDF 重叠检测 | 仅 PDF 输出有意义，且**必须显式 `--verify`**（发现重叠→退出码 2，不落盘）；不加则不做像素级检查 | 投稿 PDF 一律加 `--verify` |
| 默认 DPI | 线条图 600、照片类 300（`--dpi` 72–600 覆盖） | 期刊成品保持默认即可 |
| 渲染看门狗 | 默认自适应 30–1800s；`--timeout N` 覆盖，`--timeout 0` 禁用 | 超大图适当调大 |
| journal × theme | `--journal nejm/lancet/science/nature` 未显式 `--theme` 时自动联动同款配色 | 显式 `--theme` 优先 |
| `--stats multi` × `auto` | 互斥（multi 优先）；两组数据用 auto（multi 需 ≥3 组） | 两组比较选 auto |
| `--demo` / `--suggest` | `--demo` 不需要 `--data`；`--suggest` 需要 | — |

## 七、运行环境边界

- **无显示环境（CI/容器/SSH）**：引擎已内置 `matplotlib.use('Agg')`，无需 display/X11，开箱即跑。
- **中文字体**：`--cjk` 自动探测系统字体；`scripts/setup_env.py` 一键检测/修复；
  `--journal cma|cn-core` 自动启用中文（无需 `--cjk`，加了也不冲突）。
- **import 嵌入调用**：作为库使用时需自行 `matplotlib.use('Agg')`（见 `references/python-api.md` 方式二）。
- **输出目录**：必须可写；输出文件被占用（如 PDF 阅读器开着）会 PermissionError——
  换目录或关闭占用程序后重试。
- **cluster_heatmap 行数**：>1500 行渲染时即输出建议降采样的 WARNING（硬上限 3000 行，
  层次聚类内存随行数平方增长）——提前预判，不等超限报错。

## 八、性能参考表（实测，2026-09 v3.0/v3.1 基线）

| 场景 | 实测 |
|---|---|
| km 原始数据 5 万行 | ~3 秒（无硬上限） |
| cluster_heatmap 3000 行 | 内存护栏内（层次聚类 O(n²)，超限自动采样） |
| 200 图连跑压测 | 162 秒全成（15 图型轮转） |
| 22 模板带 CJK 全量渲染 | 全部通过（v3.0 扫描基线） |
| 输出 600dpi TIFF | 单图 0.1~0.6MB（LZW 压缩） |

数值随机器而异，此处为 82 开发机（RTX A5000/24GB）实测口径。

## 九、--stats bootstrap（v3.5 新增）

| 项 | 说明 |
|---|---|
| 方法 | percentile bootstrap（Efron 1979 经典方法），默认 5000 次重采样 |
| 输出 | 每组均值 95%CI 误差棒 + 组间均值差 95%CI 括号（CI 含 0 明示） |
| 确定性 | 固定种子（AF_BOOTSTRAP_SEED 可覆盖），同输入同 CI |
| 对拍口径 | 自研实现 + scipy.stats.bootstrap 与正态解析 CI 双对拍（测试锁定） |
| 适用 | box / violin；偏态/小样本/不满足正态假设时的稳健推断 |
