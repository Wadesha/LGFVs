# 城投公司研究（LGFV Credit Research）· 在线演示

> **GitHub Pages 演示（模拟数据）：https://wadesha.github.io/LGFVs/**

城投公司（地方政府融资平台，LGFV）信用研究的数据驱动框架：把分散在公开披露 PDF 中的非结构化信息，
转化为**多主体 × 多年份**的可分析结构化数据，支撑横向对比、趋势观察、区域聚合与风险预警。

> **核心思路（数据驱动、模拟先行）**：不纠结 PDF 解析细节，先定义清楚"结构化字段"；
> 用**合成模拟数据**把整套分析框架（看板）跑通，再按相同 schema 灌入真实、易获取的数据。

---

## 一、目录结构

```
LGFVs/
├── README.md                  # 本文件（首行为 Pages 链接）
├── index.html                 # 模拟数据展示看板（GitHub Pages 入口，自包含无 CDN）
├── docs/
│   ├── architecture.md        # 项目架构与数据 schema
│   └── methodology.md         # 采集方法、字段定义、风险逻辑、数据保护
├── scripts/
│   └── parse_report.py        # 真实 PDF 解析参考实现（需本地 PDF，输出被 gitignore）
├── data/
│   └── mock/                  # 模拟数据（合成，可复现，进仓库）
│       ├── chengtou_mock.json #   8 家主体 × 5 年结构化数据
│       └── generate_mock_data.py  # 生成脚本
└── .gitignore                 # 保护原始/获取/隐私数据
```

> 本地另有 `raw_files/`（样本 PDF）、`shandong_reports/`（山东采集体系）、`reports/`（真实报告），
> 均被 `.gitignore` 排除，**绝不进入本仓库**。

---

## 二、快速开始（仅仓库内代码）

```bash
# 1) 生成模拟数据 + 展示页（固定种子，可复现）
cd data/mock
python generate_mock_data.py
#   → 生成 chengtou_mock.json 与仓库根目录 index.html（内嵌数据）

# 2) 预览看板
#    浏览器直接打开仓库根目录的 index.html

# 3) （可选）接入真实 PDF 解析
#    将 PDF 放入本地 raw_files/，运行 scripts/parse_report.py
#    真实报告输出在 reports/（已被 gitignore 排除，不进仓库）
```

---

## 三、数据保护声明（重要）

本项目严格区分**公开演示**与**私有数据**：

| 类型 | 位置 | 是否进仓库 |
|------|------|-----------|
| 原始 PDF（手动下载样本） | `raw_files/` | ❌ 本地 |
| 真实采集数据（山东体系） | `shandong_reports/` | ❌ 本地 |
| 真实数据解析报告 | `reports/` | ❌ 本地（gitignore） |
| 合成模拟数据 | `data/mock/` | ✅ 进仓库 |
| 展示看板 | `index.html` | ✅ 进仓库（仅含模拟数据） |

- 公开仓库与 GitHub Pages **只包含代码、文档与合成模拟数据**；
- 任何原始 / 获取 / 隐私数据，**未经显式确认不得上传**；
- 任何访问凭证（如 GitHub Token）只存在于环境变量，绝不写入仓库文件 / 脚本 / 日志 / 提交历史。

详见 `docs/methodology.md` 第六节与 `docs/architecture.md` 第五节。

---

## 四、分析方法速览

- **指标维度**：规模（总资产/负债/资产负债率）、盈利（营收/净利/ROE）、偿债（EBITDA 利息保障倍数/经营现金流）、流动性（流动/速动比率）。
- **风险预警**：基于阈值自动触发标签（资产负债率>70%、EBITDA 利保<1.5x、经营现金流<0、ROE<1% 等）。
- **可视化**：KPI 卡片、评级分布、杠杆对比、ROE/资产趋势、风险预警表（均见 `index.html`）。

完整字段定义见 `docs/architecture.md`，采集与解析方法见 `docs/methodology.md`。

---

## 五、免责声明

本项目用于研究方法与框架演示。所有示例数据（样本 PDF 提取、模拟数据）仅供参考，
**不构成任何投资建议**。真实投资决策请以原始披露文件及专业意见为准。
