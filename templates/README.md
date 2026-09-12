# 场景模板库（v2.2）

10 个端到端模板 = 数据 JSON + 命令 + 图注模板。用法：

```bash
cp templates/01-meta-forest.json my_data.json
# 编辑 my_data.json，把示例数字换成你的真实数据
python3 scripts/gen_figure.py -t forest -d my_data.json -o forest.pdf --theme okabe-ito --verify
```

| 模板 | 场景 | 图型 | 推荐命令要点 |
|---|---|---|---|
| 01-meta-forest | 荟萃分析 | forest | enhanced 格式：权重气泡+events 列+异质性脚注 |
| 02-rct-baseline-bar | RCT 结局对比 | bar | +journal jama；significance 手工标注 |
| 03-survival-km | 生存分析 | km | 风险表+log-rank 自动标注 |
| 04-diagnostic-roc | 诊断试验 | roc | 多曲线 AUC 自动标注 |
| 05-correlation-heatmap | 变量相关 | heatmap | RdBu_r ±1 |
| 06-prisma-review | 系统综述筛选 | prisma | 算术自检，对不上拒绝出图 |
| 07-dose-response-line | 剂量-反应 | line | 误差带 |
| 08-panel-composite | 期刊主图 | composite | A/B/C 面板；--alt 生成图注描述 |
| 09-survey-stacked | 构成比 | stacked_bar | 百分比 + 总数 |
| 10-cn-journal-hbar | 中文期刊横柱 | hbar | --journal cn-core 自动开中文；--alt |

每个 JSON 顶部有 `_scene/_command/_caption_template` 元字段，渲染时会被忽略。
示例数字仅示意，发表前请替换为真实数据。
