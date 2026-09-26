# 常见问题 FAQ（高频问题速答）

> 按场景分组。没找到答案时：`--explain <图型>` 看单图型说明，或翻 `pitfalls.md`（深度避坑）。

## 安装与环境

**Q：需要装什么？**
Python 3.9+ 和 matplotlib/numpy/scipy。跑一次 `python3 scripts/setup_env.py` 自动配齐并检测中文字体。

**Q：中文显示成方框？**
`--cjk` 自动探测系统字体；仍不行用 `--cjk-font /path/to/字体.ttf` 指定。`--journal cma/cn-core` 会自动开中文，无需手动加。

**Q：不联网能用吗？**
能。渲染全程本地，数据不出本机。仅首次装依赖需要网络。

## 数据与格式

**Q：CSV 能画哪些图？误差棒为什么报错？**
CSV 适合 bar/line/box/scatter 等常规图。误差棒、显著性等复杂字段是 JSON 专属——CSV 不支持（报错会提示改用 JSON）。

**Q：KM 生存数据报「检测到长表结构」？**
你的表是 time/event/group 各占一列（一行记录一名患者），这种长表画不了生存曲线。请转成分组格式：
`{"groups": {"对照组": [[12, 1], [24, 0]], "处理组": [[10, 1], [30, 0]]}}`（每组一个数组，元素是 [时间, 事件 1/0]）。字段详解见 `data-formats.md` §KM。

**Q：xlsx 怎么指定工作表？**
`--data 文件.xlsx --sheet 表名`。默认取活动工作表。

**Q：数据量有上限吗？**
无统一上限，分图型限制：cluster_heatmap >3000 行自动等距采样到 2000 行（v3.1）、pca ≤200 特征列、venn 2~4 集合、km 无硬上限（5 万行实测 3 秒）。完整表见 `limits.md`。超限中文报错+给修正建议，不出废图（v3.1 起 cluster_heatmap 超限自动降采样）。

**Q：报错里有英文单词（如 KeyError/BadZipFile）怎么办？**
那是底层库的原始异常名。中文部分已说明哪里错、怎么改；英文关键词可直接搜索，或对照下方「报错信息速查」与 `pitfalls.md` 的同款案例。

## 参数与图型选择

**Q：论文一组 6~8 张图，要敲 8 次命令吗？**
不用。`--pipeline analysis.yaml`：`defaults` 写全局默认（主题/DPI/格式），`figures` 列出每张图的 type/data/out，一条命令批量渲染并生成 `.batch-report.json` 报告。YAML 需 `pip install pyyaml`；不想装就写 JSON（免依赖）。

**Q：投稿要同时交 TIFF 和 PDF，得跑两遍？**
`--multi-format tiff,png,pdf` 一条命令全出，文件名同源（`-o fig1` → fig1.tiff/fig1.png/fig1.pdf）。可与 `--pipeline` 组合，逐图指定不同格式组合。

**Q：森林图的无效参考线画在哪？**
缺省按效应尺度自动：OR/RR/HR（比率尺度）画在 1.0，MD/SMD（差值尺度）画在 0.0。数据若是 log 尺度请显式传 `"ref_line": 0`。（v2.5.x 及以前默认恒为 0，会把自然尺度 OR 的显著性判读画错位置。）

**Q：--stats auto 和 multi 有什么区别？**
auto=各组对第一组（两组就能用）；multi=全两两（需 ≥3 组，正态用 Tukey，否则 Dunn+Hochberg）。仅 box/violin 有效。

**Q：--journal 和 --width 为什么冲突？**
期刊预设锁定栏宽（这是预设的意义）。`--height` 仍可调；要自由尺寸就别用 `--journal`。

**Q：KM 的风险表能不能关掉？**
`--no-risk-table` 关闭；`--risk-times 2,6,10` 自定义显示时间点。预计算生存曲线格式无原始数据，不自动出风险表（stderr 会提示）。

**Q：ROC 想比较两个模型 A 谁更准？**
`--compare` 配对 DeLong 检验。需要 `labels`（0/1）+ 每条曲线的原始 `scores`；只有 fpr/tpr 曲线无法做 DeLong（会提示）。

**Q：组合图（composite）里能嵌组合图吗？**
不能。面板支持除 composite/diagram 外的所有图型，布局参考 `references/composite-layouts.md`。

**Q：能在自己的 Python 代码里调用吗？**
能。subprocess 调 CLI（功能全）或 import 引擎函数级嵌入（load_data/validate_data/gen_*），示例代码见 `references/python-api.md`。

## 输出与投稿

**Q：投稿用哪个格式？**
矢量优先 PDF/EPS（期刊排版可缩放）；位图 PNG/TIFF 默认 600dpi（线条图）。TIFF 自动 LZW 压缩。

**Q：怎么确认没有文字重叠、字号达标？**
`--verify`（PDF 像素级重叠检查，发现重叠退出码 2；`--multi-format` 中含 PDF 时自动核查那份）；期刊预设会打印最小字号提示，配套 `scripts/audit_pdf.py --min-size 6` 复核。

**Q：图注/无障碍描述能自动生成吗？**
`--caption` 生成中英双语期刊式图注；`--alt` 生成无障碍描述，均为旁车文件，不覆盖图片。

## 报错信息速查

校验消息已全部中文化（报错原因 + 怎么改直接写在消息里），高频条目对照：

| 报错（节选） | 什么意思 | 怎么改 |
|---|---|---|
| 系列 'X' 的值全部相同（恒为 …） | 该列所有值一样，图会是一条平线 | 多半取错了列，换列或确认数据本意 |
| 系列 'X' 里有 N 个非数值项 | 源数据混入 NA/—/文字 | 清洗源数据；这些项会被跳过 |
| 'series' 里这些系列没有数据 | 空系列无法画 | 删掉空系列或补数据 |
| labels 有 N 个组名但 series 有 M 组 | box/violin 组名和数据对不齐 | 每组恰好一个名字，检查错位 |
| km: 检测到长表结构 | CSV 一行一患者的长表 | 转 JSON groups 分组格式（见上） |
| km: …必须是 [时间, 事件(1/0)] 成对列表 | groups 值是普通数组不是对 | 改成 [[时间, 事件], ...] |
| prisma 数字自洽校验失败 | 流程图各步人数加总不平 | 复核识别/筛选/排除/纳入人数 |
| 不支持的数据格式 | 扩展名不在支持列表 | 改用 .json / .csv / .tsv / .xlsx |
| No module named 'xxx'（ImportError） | 缺少依赖库（环境侧，退出码 4） | 按提示 pip install；核心功能只需 matplotlib/numpy/scipy |
| 内存不足（MemoryError） | 数据量超出可用内存（退出码 6=自动降级重试仍失败） | 减少行数/列数；cluster_heatmap 可加 --downsample 2000 |
| 渲染看门狗超时（退出码 5） | 图表未在预算时间内完成，被强制中断并给出建议 | 瘦身数据，或 --timeout 600 调大预算；--timeout 0 禁用 |
| 退出码 1/3/4 怎么区分 | 1=参数或校验错误，3=数据或格式问题，4=环境或依赖问题 | 按报错里的中文建议逐条处理；AF_DEBUG=1 看完整细节 |

## 付费版

**Q：免费版和 Pro 什么关系？**
同一渲染引擎。Pro 是云端服务（无需 Python，上传数据即出图，¥0.5/次），见 SkillHub `academic-figures-pro`。本地能用免费版就够，团队/无环境场景选 Pro。

## 参数冲突与边界 FAQ（v3.2 扩充）

**Q：`--journal` 和 `--width` 一起给会怎样？**
`--journal` 锁定图宽，`--width` 被忽略（stderr 以 `[auto]` 明示）；`--height` 仍生效。
要自定义尺寸就别加 `--journal`。

**Q：`--verify` 对 PNG/TIFF 输出有效吗？**
无效——仅 PDF 输出生效（像素级文字重叠检查）。非 PDF 输出时 stderr 会以 `[auto]` 提示。
矢量投稿图建议 PDF + `--verify`。

**Q：`--stats auto` 能用在折线图/散点图上吗？**
不能——仅 box/violin（其他图型静默忽略）。两组前后配对数据请用 `-t paired`。

**Q：`--compare`（DeLong）能用在没有 scores 的 ROC 数据上吗？**
不能——需各曲线提供 `scores`（原始打分）；只有 fpr/tpr 时无法做配对检验（stderr 提示）。

**Q：`--egger` 能用在森林图上吗？**
不能——仅 funnel（≥3 研究）。森林图的 Meta 功能是 `--stats cox`（多因素回归）。

**Q：`--hatch` 和 `--style glm-hatch` 什么区别？**
`--hatch` 仅 bar 系（柱状填充斜纹）；`--style glm-hatch` 是主题级开关（glm 配色+全图斜纹风格）。

**Q：cluster_heatmap 超过 3000 行会失败吗？**
v3.1 起不会——自动等距采样到 2000 行并显著告知（`AUTO-DOWNSAMPLE`）；`--downsample N`
可指定其他行数。

**Q：CSV 能带误差棒吗？**
不能——JSON 的 `errors` 字段才支持。详见 data-formats.md 的 JSON/CSV 能力对照表。

**Q：数据不满足正态/样本量小，--stats auto 可信吗？**
`--stats bootstrap`（v3.5）：非参数 bootstrap 置信区间——每组均值 95%CI + 组间均值差 CI
括号（CI 含 0 明示，不给误导性星号）。确定性输出（固定种子）。仅 box/violin。
