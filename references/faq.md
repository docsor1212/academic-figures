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

**Q：xlsx 怎么指定工作表？**
`--data 文件.xlsx --sheet 表名`。默认取活动工作表。

**Q：数据量有上限吗？**
无统一上限，分图型限制：cluster_heatmap ≤3000 行、pca ≤200 特征列、venv 2~3 集合、km 无硬上限（5 万行实测 3 秒）。完整表见 `limits.md`。超限会中文报错+给修正建议，不出废图。

**Q：报错里有英文单词（如 KeyError/BadZipFile）怎么办？**
那是底层库的原始异常名。中文部分已说明哪里错、怎么改；英文关键词可直接搜索，或对照本 FAQ 与 `pitfalls.md` 的同款案例。

## 参数与图型选择

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

## 输出与投稿

**Q：投稿用哪个格式？**
矢量优先 PDF/EPS（期刊排版可缩放）；位图 PNG/TIFF 默认 600dpi（线条图）。TIFF 自动 LZW 压缩。

**Q：怎么确认没有文字重叠、字号达标？**
`--verify`（PDF 像素级重叠检查，发现重叠退出码 2）；期刊预设会打印最小字号提示，配套 `scripts/audit_pdf.py --min-size 6` 复核。

**Q：图注/无障碍描述能自动生成吗？**
`--caption` 生成中英双语期刊式图注；`--alt` 生成无障碍描述，均为旁车文件，不覆盖图片。

## 付费版

**Q：免费版和 Pro 什么关系？**
同一渲染引擎。Pro 是云端服务（无需 Python，上传数据即出图，¥0.5/次），见 SkillHub `academic-figures-pro`。本地能用免费版就够，团队/无环境场景选 Pro。
