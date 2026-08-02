# 原始样本 PDF（公开披露）

手动下载的城投公司**公开披露**文件样本，用于 `scripts/parse_report.py` 的解析参考实现（含真实样本数值，但仅作方法演示）。

| 文件 | 主体 | 说明 |
|---|---|---|
| `shanghai_chengtou.pdf` | 上海城投（集团）有限公司 | 公开发行债券募集说明书 / 年度报告 |
| `chengdu_chengtou.pdf` | 成都城建投资发展股份有限公司 | 公开披露文件 |
| `huzhou_chengtou.pdf` | 湖州城投 | 公开披露文件 |
| `sina_chengtou.pdf` | 新浪财经聚合的城投债资料 | 聚合样本 |

> 全部为发行人对外**公开披露**资料，不含任何私密 / 涉密内容。
> 解析逻辑见仓库 `scripts/parse_report.py`；生成的演示报告输出到 `reports/`（不入库，可由脚本再生）。
