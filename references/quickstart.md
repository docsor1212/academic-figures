# 快速入门指南（独立版）

> 主文档保留精简选图映射；本页是完整的首次上手指南：完整选图决策树、选图三件套、
> 上手四步、Python 内调用、常见第一坑。目标：五分钟从数据到投稿级图。

## 一、完整选图决策树

```text
分组比较（各组一批数值）────→ bar / box / violin（两组前后配对 → paired）
均值±误差棒 ────────────────→ bar（JSON errors 字段）
两列连续值看相关 ───────────→ scatter
时间-事件结局 ──────────────→ km（分组生存）/ forest --stats cox（多因素 HR）
标志物 vs 金标准诊断 ───────→ roc（多模型对比加 --compare）
元素/基因集合交并 ──────────→ venn（2~4 集合；要面积比例加 --area）
行×列数值矩阵 ──────────────→ heatmap（要聚类重排 → cluster_heatmap）
多变量样本分类展示 ─────────→ pca
效应值+SE 汇总 ─────────────→ forest（Meta；发表偏移加 --egger）
两次测量一致性 ─────────────→ bland_altman
流程/构成步骤 ──────────────→ diagram / stacked_bar / prisma（系统综述）
多面板 A+B+C ───────────────→ composite
```

每类的数据格式细节见 `references/data-formats.md`；组合图面板布局见
`references/composite-layouts.md`；临床实验室数据（医学方向）见
`references/clinical-lab-trends.md`。

## 二、选图三件套（拿不准就用它们）

```bash
python3 scripts/gen_figure.py --wizard          # 四问 → 生成完整命令（非交互环境打印决策树）
python3 scripts/gen_figure.py --suggest -d 数据文件   # 自动分析数据并推荐图型
python3 scripts/gen_figure.py --explain bar     # 某图型的用法、参数与边界
```

## 三、上手四步

1. **环境准备**：`python3 scripts/setup_env.py`（装依赖/检测中文字体/清理字体缓存/自检）。
2. **用模板先跑通**：`templates/` 覆盖 22 种图型，每个 JSON 头部带可复制的 `_command`；
   先用示例数据渲染一张确认环境无问题。
3. **换成自己的数据**：数据格式对照 `references/data-formats.md`；先小尺寸
   （如 `--dpi 150`）快速出一张核对内容，再出 600dpi 成品。
4. **投稿成品**：默认 DPI（线条图 600）+ `--multi-format tiff,png`；PDF 记得加
   `--verify`（像素级重叠检查）。数字边界与参数交互见 `references/limits.md`。

## 四、Python 内调用

- **subprocess（推荐）**：CLI 是全部功能的完整入口（期刊预设/统计标注/KM 风险表/
  多格式导出只在 CLI 生效）。
- **import 嵌入**：把引擎当库用——`load_data → validate_data → gen_*` 三步；
  嵌入前必须自己 `matplotlib.use("Agg")`（引擎顶层已对 CLI 路径设置）。
- 完整示例与退出码约定见 `references/python-api.md`。

## 五、常见第一坑（Top 6）

1. **中文乱码**：加 `--cjk` 自动探测系统中文字体（`--journal cma|cn-core` 自动启用，
   无需再加）；字体缺失先跑 `scripts/setup_env.py`。
2. **CSV 要误差棒**：CSV 不支持误差棒——改用 JSON 的 `errors` 字段（见 --explain bar）。
3. **`--journal` 锁宽度**：journal 预设覆盖 `--width`（`--height` 仍生效）；要自定义
   尺寸就别加 `--journal`。
4. **cluster_heatmap 行数偏大**：>1500 行即建议 `--downsample N` 等距采样（硬上限
   3000 行，层次聚类内存随行数平方增长）。
5. **组合图面板内不能再嵌 composite**；面板支持除 composite/diagram 外的所有图型。
6. **投稿 PDF 忘加 `--verify`**：重叠检测只在显式加 `--verify` 时执行（重叠→退出码 2）。
