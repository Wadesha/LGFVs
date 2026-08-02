# 山东城投公开披露采集体系（原始数据）

本目录为「山东省城投公司公开披露资料」采集系统的**原始数据 + 采集脚本 + 进度快照**。
数据来源均为发行人对外**公开披露**渠道（中国货币网 / 巨潮资讯等），不含任何私密或涉密内容。

## 目录布局

```
shandong_reports/
├── raw/                      # 主采集源（中国货币网等）原始 PDF
│   └── <城市>/
│       └── <公司>/
│           └── <公司>_<编号>.pdf
├── raw_cninfo/              # 巨潮资讯(CNINFO) 源：原始 JSON 元数据 + 部分 PDF
│   └── <城市>/
│       └── ...
├── collect_shandong.py      # 主采集脚本（山东，中国货币网）
├── collect_v2.py            # 采集脚本 v2
├── collect_browser.py      # 浏览器自动化采集
├── collect_cninfo.py        # 巨潮资讯源采集
├── chinamoney_playwright.py # 中国货币网 Playwright 实现
├── chinamoney_playwright_v2.py
├── chinamoney_scraper.py
├── chinamoney_screenshot.png (已排除)
├── download_pdfs_v3.py      # PDF 下载
├── run_ab.py / run_ab.bat   # 批量执行入口
├── workflow.py              # 工作流编排
├── tracker.py               # 采集进度追踪
├── shandong_companies.py    # 山东城投主体清单
├── test_*.py                # 各来源测试脚本
├── collection_progress*.json   # 采集进度快照（含 chinamoney / cninfo / browser / v2 等维度）
├── *_debug.html / *_screenshot.png  # 调试产物（已被 .gitignore 排除，不入库）
├── 操作指南.md              # 采集操作说明
└── 采集进度报告.md          # 采集进度汇总报告
```

## 数据规模（入库部分）

- `raw/`：**28** 个地级市 / 新区，**100** 家城投主体，**403** 份披露 PDF
- `raw_cninfo/`：**100** 份 JSON 元数据 + **29** 份 PDF
- 单文件最大约 42 MB（远低于 GitHub 100 MB 单文件上限，未启用 Git LFS）

## 说明

- 调试截图（`*_screenshot.png`）、调试页面（`debug_*.html` 等）属一次性产物，已通过根目录 `.gitignore` 排除，保持仓库清晰。
- 如需再生解析报告，运行 `scripts/parse_report.py`（输出到 `reports/`，不入库）。
- 采集脚本的相对路径依赖本目录结构，请勿随意移动脚本位置。
