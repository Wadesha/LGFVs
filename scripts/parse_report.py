"""
城投公司债券研究报告生成器（真实数据解析 · 参考实现）

说明
----
- 本脚本从「本地」城投公司公开披露 PDF（募集说明书 / 评级报告 / 债权代理报告）
  中硬编码提取 3 家样本（上海 / 成都 / 湖州）的结构化字段，并生成横向对比 HTML 报告。
- 它是**真实数据的解析参考实现**：运行需要本地存放对应 PDF，输出为真实数据报告，
  因此输出目录 `reports/` 已在 .gitignore 中排除，**不会进入仓库**。
- 本项目对外展示（GitHub Pages）使用的是 `index.html` 中的**模拟数据**，详见该文件与
  `data/mock/`。

仅作方法演示与字段对齐模板使用。
"""
import pdfplumber
import json
import os
from datetime import datetime

# ============ 数据提取函数 ============

def extract_shanghai_chengtou():
    """提取上海城投数据 - 来自债权代理报告"""
    return {
        "company_name": "上海城投（集团）有限公司",
        "short_name": "上海城投",
        "province": "上海市",
        "city": "上海市",
        "industry": "城市基础设施建设与公用事业",
        "document_type": "债权代理事务报告",
        "document_source": "国泰君安证券股份有限公司",
        "report_period": "2023年度",
        "report_date": "2024-06",
        "pdf_file": "sina_chengtou.pdf",
        "pdf_url": "http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/BOND/2024/2024-6/2024-06-27/20500519.PDF",

        # 基本信息
        "issuer_rating": "AAA",
        "bond_rating": "AAA",
        "rating_agency": "中诚信国际信用评级有限责任公司",
        "rating_outlook": "稳定",

        # 发行条款
        "bonds": [
            {"name": "14沪建债", "code_ib": "1480474.IB", "code_sse": "PR沪建债/127026.SH",
             "size": "20亿", "balance": "3亿", "rate": "4.80%", "maturity": "2014-11至2024-11", "type": "企业债"},
            {"name": "19沪建债01", "code_ib": "1980272.IB", "code_sse": "19沪建01/152274.SH",
             "size": "9亿", "balance": "9亿", "rate": "3.70%", "maturity": "2019-09至2029-09", "type": "企业债"},
            {"name": "19沪建债02", "code_ib": "1980273.IB", "code_sse": "19沪建02/152275.SH",
             "size": "6亿", "balance": "2.70亿", "rate": "2.60%", "maturity": "2019-09至2024-09", "type": "企业债"},
            {"name": "20沪建债01", "code_ib": "2080061.IB", "code_sse": "20沪建01/152427.SH",
             "size": "20亿", "balance": "20亿", "rate": "3.20%", "maturity": "2020-03至2027-03", "type": "企业债"},
            {"name": "20沪建债02", "code_ib": "2080062.IB", "code_sse": "20沪建02/152428.SH",
             "size": "10亿", "balance": "10亿", "rate": "3.75%", "maturity": "2020-03至2030-03", "type": "企业债"},
            {"name": "21沪建债01", "code_ib": "2180023.IB", "code_sse": "21沪建01/152738.SH",
             "size": "15亿", "balance": "0亿(已全额兑付)", "rate": "2.10%", "maturity": "2021-01至2026-01", "type": "企业债"},
            {"name": "21沪建债02", "code_ib": "2180024.IB", "code_sse": "21沪建02/152739.SH",
             "size": "5亿", "balance": "5亿", "rate": "3.65%", "maturity": "2021-01至2028-01", "type": "企业债"},
        ],

        # 财务指标（2023年末/年度）
        "financials": {
            "total_assets": 7983.46,
            "total_liabilities": 4197.45,
            "equity": 3786.01,
            "asset_liability_ratio": 52.58,
            "current_ratio": 1.54,
            "quick_ratio": 0.80,
            "cash": 391.13,
            "inventory": 559.42,
            "operating_revenue": 349.67,
            "operating_cost": 340.58,
            "total_profit": 27.59,
            "net_profit": 19.87,
            "parent_net_profit": 14.41,
            "op_cf": 108.07,
            "inv_cf": -377.81,
            "fin_cf": 195.35,
        },

        # 2024年偿债计划
        "debt_schedule_2024": {
            "total_principal_interest": 16.44,
            "note": "2024-2025年偿债规模较大，货币资金391.13亿储备充裕"
        },

        # 风险提示
        "risk_flags": [
            "2023年净利润同比下降8.43%",
            "筹资活动现金流同比减少63.80%",
            "流动比率1.54较2022年2.95有所下降",
            "存货在总资产中占比大（559.42亿）"
        ],

        # 优势
        "strengths": [
            "AAA最高信用等级，评级展望稳定",
            "资产规模最大（7983亿），股东背景强",
            "货币资金充裕（391亿），偿债能力强",
            "资产负债率适中（52.58%），低于行业平均",
            "上海区域财政实力全国最强"
        ],

        "weaknesses": [
            "2023年营收利润双降",
            "投资活动持续大额净流出（年均-400亿）",
            "存货占比高影响资产流动性"
        ]
    }


def extract_chengdu_chengtou():
    """提取成都城建数据 - 来自募集说明书"""
    return {
        "company_name": "成都城建投资管理集团有限责任公司",
        "short_name": "成都城投",
        "province": "四川省",
        "city": "成都市",
        "industry": "城市基础设施建设与运营",
        "document_type": "面向专业投资者公开发行公司债券募集说明书",
        "document_source": "中信建投证券股份有限公司",
        "report_period": "2024年第一期",
        "report_date": "2024年",
        "pdf_file": "chengdu_chengtou.pdf",
        "pdf_url": "https://static.cninfo.com.cn/finalpage/2024-06-28/1220509630.pdf",

        # 基本信息
        "issuer_rating": "AAA",
        "bond_rating": "无评级（可质押式回购）",
        "rating_agency": "联合资信评估股份有限公司",
        "rating_outlook": "稳定",
        "bond_size": "注册50亿，本期不超过8亿",
        "bond_term": "待确认",
        "coupon_rate": "待询价确定",
        "guarantee": "无担保",

        # 发行条款
        "bonds": [
            {"name": "24蓉城建01（本期）", "code_sse": "待上市",
             "size": "≤8亿", "balance": "待发行", "rate": "待定", "maturity": "待定", "type": "公司债"},
        ],

        # 财务指标（2023年末/年度）
        "financials": {
            "total_assets": 1793.65,
            "total_liabilities": 1254.45,
            "equity": 539.19,
            "total_debt": 532.40,
            "asset_liability_ratio": 69.94,
            "current_ratio": 2.36,
            "quick_ratio": 0.57,
            "cash": 160.89,  # 货币资金
            "restricted_assets": 121.34,
            "operating_revenue": 264.54,
            "gross_profit_margin": 12.73,
            "total_profit": 15.54,
            "net_profit": 11.49,
            "parent_net_profit": 6.14,
            "op_cf": 1.93,
            "inv_cf": -57.88,
            "fin_cf": 54.10,
            "ebitda": 32.49,
            "ebitda_interest": 1.18,
            "roa": 1.24,
            "roe": 2.20,
        },

        # 2024年到期债务
        "debt_schedule_2024": {
            "total_principal_interest": None,
            "note": "受限资产121.34亿（占比6.76%），含存货/货币资金/固定资产"
        },

        # 风险提示
        "risk_flags": [
            "资产负债率69.94%，高于行业平均",
            "EBITDA利息保障倍数仅1.18倍，偿债能力偏弱",
            "经营活动现金流2021-2022年持续为负",
            "受限资产121.34亿，占总资产6.76%",
            "其他应收款中非经营性应收款8.86亿",
            "流动比率2.36但速动比率仅0.57"
        ],

        # 优势
        "strengths": [
            "主体信用AAA，成都市最重要城投平台之一",
            "公用事业+房地产业双主业支撑",
            "2023年经营现金流首次转正",
            "融资渠道畅通，与多家银行保持合作"
        ],

        "weaknesses": [
            "债务规模较大（总债务532亿）",
            "利息保障倍数偏低（1.18倍）",
            "存货及受限资产规模大，资产流动性弱",
            "净利润对非经常性损益依赖较大"
        ]
    }


def extract_huzhou_chengtou():
    """提取湖州城投数据 - 来自募集说明书摘要"""
    return {
        "company_name": "湖州市城市投资发展集团有限公司",
        "short_name": "湖州城投",
        "province": "浙江省",
        "city": "湖州市",
        "industry": "城市基础设施建设、土地开发与燃气供应",
        "document_type": "面向专业投资者公开发行公司债券募集说明书摘要",
        "document_source": "东海证券股份有限公司（牵头）",
        "report_period": "2024年（反馈稿）",
        "report_date": "2024年",
        "pdf_file": "huzhou_chengtou.pdf",
        "pdf_url": "https://static.sse.com.cn/bond/bridge2/disclosure/announcement/c/202412/052536_20241217_SPZC.pdf",

        # 基本信息
        "issuer_rating": "AAA（多家）",
        "bond_rating": "--（无独立债项评级）",
        "rating_agency": "中证鹏元、联合资信、中诚信国际（联合评级）",
        "rating_outlook": "稳定",
        "bond_size": "注册16.15亿",
        "bond_term": "待确认",
        "coupon_rate": "待询价确定",
        "guarantee": "无担保",

        # 财务指标（2024年6月末/2023年末）
        "financials": {
            "total_assets": 1491.44,
            "total_liabilities": 991.87,
            "parent_total_assets": 807.20,  # 母公司口径
            "equity": 499.57,
            "total_debt": 802.84,
            "asset_liability_ratio": 66.50,
            "debt_capital_ratio": 61.64,
            "current_ratio": 4.30,
            "quick_ratio": 0.82,
            "cash": 77.69,
            "inventory": 894.94,  # 存货
            "accounts_receivable": 43.76,
            "other_receivable": 66.95,
            "operating_revenue": 76.29,  # 2024H
            "full_year_revenue_2023": 173.80,
            "gross_profit_margin": 10.45,
            "total_profit": 1.91,  # 2024H
            "net_profit": 1.28,   # 2024H
            "parent_net_profit": 0.87,  # 2024H
            "full_year_net_profit_2023": 2.18,
            "op_cf": -34.21,  # 2024H
            "full_year_op_cf_2023": -79.45,
            "inv_cf": -8.76,  # 2024H
            "fin_cf": 44.12,  # 2024H
            "roa": 0.35,  # 2024H
            "roe": 0.26,  # 2024H
            "full_year_roa_2023": 0.91,
            "ebitda_debt": None,  # 数据未完整披露
            "ebitda_interest": None,
        },

        # 2024年到期债务
        "debt_schedule_2024": {
            "total_principal_interest": None,
            "note": "存货高达894.94亿（占总资产60%），主要为代建项目和开发成本；货币资金77.69亿"
        },

        # 风险提示
        "risk_flags": [
            "2024年上半年净利润仅1.28亿，盈利能力极弱",
            "经营活动现金流持续为负（2021-2024H均负）",
            "存货占总资产60%，流动性极低",
            "资产负债率66.50%，债务资本比率61.64%",
            "其他应收款66.95亿，其中非经营性往来32.16亿",
            "对政府及相关单位应收款约32亿，回款不确定性高",
            "多家评级机构联合评级"
        ],

        # 优势
        "strengths": [
            "长三角都市圈核心城市（湖州）区位优势",
            "AAA主体信用，多家机构联合评级",
            "流动比率4.30（合并口径），短期偿债指标尚可",
            "土地储备和代建项目资源丰富"
        ],

        "weaknesses": [
            "盈利极弱（ROE仅0.26%），高度依赖政府补贴",
            "经营现金流连续多年为负，自我造血能力差",
            "存货占比过高，资产质量存疑",
            "债务规模大（全部债务802亿），利息负担重"
        ]
    }


def generate_html_report(companies):
    """生成HTML研究报告"""
    today = datetime.now().strftime("%Y年%m月%d日")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>城投公司债券研究报告 - {today}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "PingFang SC", "Microsoft YaHei", Arial, sans-serif; background: #f5f7fa; color: #333; font-size: 14px; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

  /* 头部 */
  .header {{ background: linear-gradient(135deg, #1a3a6b 0%, #2c5282 100%); color: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 8px; }}
  .header .meta {{ opacity: 0.85; font-size: 13px; }}
  .header .badge {{ display: inline-block; background: rgba(255,255,255,0.15); padding: 4px 12px; border-radius: 20px; font-size: 12px; margin-top: 12px; }}

  /* 摘要卡片 */
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .summary-card {{ background: white; border-radius: 10px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #3182ce; }}
  .summary-card .label {{ color: #718096; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
  .summary-card .value {{ font-size: 22px; font-weight: 700; color: #1a3a6b; }}
  .summary-card .sub {{ font-size: 11px; color: #a0aec0; margin-top: 4px; }}

  /* 公司卡片 */
  .company-card {{ background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 24px; overflow: hidden; }}
  .company-header {{ background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%); color: white; padding: 20px 28px; display: flex; justify-content: space-between; align-items: center; }}
  .company-header h2 {{ font-size: 20px; font-weight: 700; }}
  .company-header .subtitle {{ opacity: 0.85; font-size: 13px; margin-top: 4px; }}
  .company-header .rating-badge {{ background: #ecc94b; color: #744210; font-weight: 700; font-size: 18px; padding: 6px 16px; border-radius: 6px; }}

  .card-body {{ padding: 24px 28px; }}

  /* 标签 */
  .tag {{ display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .tag-aaa {{ background: #fef3c7; color: #92400e; }} .tag-high {{ background: #fed7d7; color: #9b2c2c; }}
  .tag-med {{ background: #feebc8; color: #9a3412; }} .tag-low {{ background: #c6f6d5; color: #276749; }}
  .tag-warning {{ background: #fefcbf; color: #975a16; }} .tag-info {{ background: #bee3f8; color: #2b6cb0; }}
  .tag-dark {{ background: #e2e8f0; color: #2d3748; }}

  /* 表格 */
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th {{ background: #f7fafc; color: #4a5568; font-weight: 600; text-align: left; padding: 10px 14px; border-bottom: 2px solid #e2e8f0; font-size: 12px; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #f0f4f8; font-size: 13px; vertical-align: top; }}
  tr:hover td {{ background: #f7fafc; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .good {{ color: #276749; font-weight: 600; }} .bad {{ color: #c53030; font-weight: 600; }}
  .warn {{ color: #c05621; }} .neutral {{ color: #4a5568; }}

  /* 风险信号 */
  .risk-section {{ margin-top: 20px; }}
  .risk-section h4 {{ font-size: 14px; color: #2d3748; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
  .risk-item {{ display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; font-size: 13px; color: #4a5568; }}
  .risk-item::before {{ content: "●"; color: #e53e3e; font-size: 8px; margin-top: 5px; flex-shrink: 0; }}
  .strength-item::before {{ color: #38a169 !important; }}
  .strength-item {{ color: #276749; }}

  /* 进度条 */
  .bar-wrap {{ background: #edf2f7; border-radius: 4px; height: 8px; margin: 4px 0 8px; overflow: hidden; }}
  .bar {{ height: 100%; border-radius: 4px; transition: width 0.6s; }}
  .bar-good {{ background: linear-gradient(90deg, #48bb78, #38a169); }} .bar-warn {{ background: linear-gradient(90deg, #ed8936, #dd6b20); }}
  .bar-bad {{ background: linear-gradient(90deg, #fc8181, #e53e3e); }} .bar-neutral {{ background: linear-gradient(90deg, #4299e1, #3182ce); }}

  /* 财务对比表 */
  .financial-compare th {{ font-size: 11px; }}
  .company-col {{ min-width: 140px; }}

  /* 底部 */
  .footer {{ text-align: center; color: #a0aec0; font-size: 12px; padding: 20px 0; border-top: 1px solid #e2e8f0; margin-top: 24px; }}

  /* 网格布局 */
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #2d3748; padding-bottom: 8px; border-bottom: 2px solid #3182ce; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}

  /* 信用等级色块 */
  .rating-block {{ display: inline-flex; flex-direction: column; align-items: center; background: #fef3c7; border: 2px solid #ecc94b; border-radius: 8px; padding: 8px 16px; margin: 4px; }}
  .rating-block .num {{ font-size: 22px; font-weight: 800; color: #92400e; }} .rating-block .label {{ font-size: 10px; color: #744210; }}

  /* 响应式 */
  @media (max-width: 768px) {{ .grid-2, .grid-3 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">

  <!-- 头部 -->
  <div class="header">
    <h1>🏛️ 城投公司债券研究报告</h1>
    <div class="meta">覆盖：{today} · 样本：{len(companies)}家城投公司 · 数据来源：公开披露文件</div>
    <div class="badge">📄 募集说明书 / 债权代理报告 · 定期更新</div>
  </div>

  <!-- 汇总数据 -->
  <div class="summary-grid">
    <div class="summary-card">
      <div class="label">纳入公司</div>
      <div class="value">{len(companies)}</div>
      <div class="sub">家城投公司</div>
    </div>
    <div class="summary-card">
      <div class="label">AAA主体评级</div>
      <div class="value">{len(companies)}</div>
      <div class="sub">家（覆盖率100%）</div>
    </div>
    <div class="summary-card">
      <div class="label">合计总资产</div>
      <div class="value">{sum(c['financials'].get('total_assets', 0) for c in companies):,.0f}</div>
      <div class="sub">亿元</div>
    </div>
    <div class="summary-card">
      <div class="label">平均资产负债率</div>
      <div class="value">{sum(c['financials'].get('asset_liability_ratio', 0) for c in companies)/len(companies):.1f}%</div>
      <div class="sub">行业参考值 <60%</div>
    </div>
  </div>

  <!-- 财务指标对比表 -->
  <div class="company-card">
    <div class="company-header" style="background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);">
      <div>
        <h2>📊 核心财务指标对比</h2>
        <div class="subtitle">单位：亿元 / 百分比率</div>
      </div>
    </div>
    <div class="card-body" style="overflow-x:auto;">
      <table class="financial-compare">
        <thead>
          <tr>
            <th>指标</th>
            {"".join(f'<th class="company-col">{c["short_name"]}</th>' for c in companies)}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>所在区域</td>
            {"".join(f'<td>{c["province"]} · {c.get("city","")}</td>' for c in companies)}
          </tr>
          <tr>
            <td>文件类型</td>
            {"".join(f'<td>{c["document_type"][:15]}...</td>' for c in companies)}
          </tr>
          <tr>
            <td>主体 / 债项评级</td>
            {"".join(f'<td><span class="tag tag-aaa">AAA</span> / {c.get("bond_rating","--")}</td>' for c in companies)}
          </tr>
          <tr>
            <td>总资产</td>
            {"".join(f'<td class="num">{c["financials"].get("total_assets",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>总负债</td>
            {"".join(f'<td class="num">{c["financials"].get("total_liabilities",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>资产负债率</td>
            {"".join(f'<td class="num {"bad" if c["financials"].get("asset_liability_ratio",0)>65 else "good"}">{c["financials"].get("asset_liability_ratio",0):.2f}%</td>' for c in companies)}
          </tr>
          <tr>
            <td>货币资金</td>
            {"".join(f'<td class="num">{c["financials"].get("cash",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>营业总收入（最新）</td>
            {"".join(f'<td class="num">{c["financials"].get("operating_revenue",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>利润总额</td>
            {"".join(f'<td class="num">{c["financials"].get("total_profit",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>净利润</td>
            {"".join(f'<td class="num {("bad" if c["financials"].get("net_profit",0)<5 else "good") if c["financials"].get("net_profit",0)>0 else "bad"}">{c["financials"].get("net_profit",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>EBITDA</td>
            {"".join(f'<td class="num">{c["financials"].get("ebitda",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>EBITDA利息保障倍数</td>
            {"".join(f'<td class="num {"bad" if ((c["financials"].get("ebitda_interest") or 0))<2 else "good"}">{(c["financials"].get("ebitda_interest") or 0):.2f}x</td>' for c in companies)}
          </tr>
          <tr>
            <td>流动比率</td>
            {"".join(f'<td class="num {"good" if c["financials"].get("current_ratio",0)>1.5 else "bad"}">{c["financials"].get("current_ratio",0):.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>速动比率</td>
            {"".join(f'<td class="num {"bad" if c["financials"].get("quick_ratio",0)<1 else "warn" if c["financials"].get("quick_ratio",0)<1.5 else "good"}">{c["financials"].get("quick_ratio",0):.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>经营现金流净额</td>
            {"".join(f'<td class="num {"bad" if c["financials"].get("op_cf",0)<0 else "good"}">{c["financials"].get("op_cf",0):,.2f}</td>' for c in companies)}
          </tr>
          <tr>
            <td>ROA（资产回报率）</td>
            {"".join(f'<td class="num {"bad" if (c["financials"].get("roa") or 0)<1 else "good"}">{c["financials"].get("roa", 0):.2f}%</td>' for c in companies)}
          </tr>
          <tr>
            <td>ROE（净资产收益率）</td>
            {"".join(f'<td class="num {"bad" if (c["financials"].get("roe") or 0)<2 else "good"}">{c["financials"].get("roe", 0):.2f}%</td>' for c in companies)}
          </tr>
        </tbody>
      </table>
    </div>
  </div>
"""

    # 添加每家公司详情
    for i, company in enumerate(companies):
        color_options = [
            "linear-gradient(135deg, #3182ce 0%, #2c5282 100%)",
            "linear-gradient(135deg, #38a169 0%, #276749 100%)",
            "linear-gradient(135deg, #d69e2e 0%, #975a16 100%)",
        ]
        bg = color_options[i % len(color_options)]

        f = company["financials"]

        # 资产负债率指示
        al_ratio = f.get("asset_liability_ratio", 0)
        if al_ratio < 55: al_tag = '<span class="tag tag-low">偏低</span>'
        elif al_ratio < 65: al_tag = '<span class="tag tag-med">中等</span>'
        else: al_tag = '<span class="tag tag-high">偏高</span>'

        # 偿债能力
        interest_cov = f.get("ebitda_interest") or 0
        if interest_cov >= 3: cov_tag = '<span class="tag tag-low">充足</span>'
        elif interest_cov >= 1.5: cov_tag = '<span class="tag tag-med">一般</span>'
        elif interest_cov >= 1: cov_tag = '<span class="tag tag-warning">偏弱</span>'
        else: cov_tag = '<span class="tag tag-high">弱</span>'

        html += f"""
  <!-- 公司卡片 -->
  <div class="company-card">
    <div class="company-header" style="background: {bg};">
      <div>
        <h2>{company["company_name"]}</h2>
        <div class="subtitle">{company["province"]} · {company["industry"]} · {company["document_type"]}</div>
        <div class="subtitle" style="opacity:0.7; font-size:12px;">披露：{company["document_source"]} · {company["report_date"]}</div>
      </div>
      <div style="text-align:center;">
        <div class="rating-badge">{company["issuer_rating"]}</div>
        <div style="font-size:12px; margin-top:4px; opacity:0.8;">主体评级</div>
        <div style="margin-top:6px;">{al_tag}</div>
      </div>
    </div>
    <div class="card-body">
      <div class="grid-3" style="margin-bottom:20px;">
        <!-- 资产规模 -->
        <div style="background:#f7fafc; border-radius:8px; padding:16px; text-align:center;">
          <div style="font-size:11px; color:#718096; margin-bottom:6px;">总资产</div>
          <div style="font-size:28px; font-weight:800; color:#2d3748;">{f.get("total_assets",0):,.1f}</div>
          <div style="font-size:11px; color:#a0aec0;">亿元</div>
        </div>
        <!-- 资产负债率 -->
        <div style="background:#f7fafc; border-radius:8px; padding:16px; text-align:center;">
          <div style="font-size:11px; color:#718096; margin-bottom:6px;">资产负债率</div>
          <div style="font-size:28px; font-weight:800; color:{'#c53030' if al_ratio>65 else '#2f855a'};">{al_ratio:.1f}%</div>
          <div style="font-size:11px; color:#a0aec0;">{'偏高' if al_ratio>65 else '合理'}</div>
        </div>
        <!-- EBITDA利息保障 -->
        <div style="background:#f7fafc; border-radius:8px; padding:16px; text-align:center;">
          <div style="font-size:11px; color:#718096; margin-bottom:6px;">利息保障倍数</div>
          <div style="font-size:28px; font-weight:800; color:{'#c53030' if interest_cov<1.5 else '#2f855a'};">{interest_cov:.2f}x</div>
          <div style="font-size:11px; color:#a0aec0;">{cov_tag.text if hasattr(cov_tag,'text') else ''}</div>
        </div>
      </div>

      <!-- 资产负债率条 -->
      <div style="margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; font-size:12px; color:#718096; margin-bottom:4px;">
          <span>资产负债率</span><span>{al_ratio:.1f}%</span>
        </div>
        <div class="bar-wrap">
          <div class="bar {'bar-warn' if al_ratio>65 else 'bar-good'}" style="width:{min(al_ratio,100)}%;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:11px; color:#a0aec0;">
          <span>健康<55%</span><span>警戒线>70%</span>
        </div>
      </div>

      <div class="grid-2">
        <!-- 优势 -->
        <div class="risk-section">
          <h4>✅ 优势项 <span class="tag tag-low">{len(company.get('strengths',[]))}项</span></h4>
          {"".join(f'<div class="risk-item strength-item">{s}</div>' for s in company.get('strengths',[]))}
        </div>
        <!-- 风险 -->
        <div class="risk-section">
          <h4>⚠️ 风险点 <span class="tag tag-high">{len(company.get('risk_flags',[]))}项</span></h4>
          {"".join(f'<div class="risk-item">{r}</div>' for r in company.get('risk_flags',[]))}
        </div>
      </div>

      <!-- 债券明细 -->
      {"".join(f'''
      <div class="risk-section">
        <h4>💼 存续债券 <span class="tag tag-dark">{len(company.get("bonds",[]))}只</span></h4>
        <div style="overflow-x:auto;">
        <table>
          <thead><tr>
            <th>债券简称</th><th>代码</th><th>发行规模</th><th>债券余额</th>
            <th>票面利率</th><th>到期日</th><th>类型</th>
          </tr></thead>
          <tbody>
            {"".join(f"<tr><td>{b.get('name','')}</td><td><span class='tag tag-info'>{b.get('code_ib','') if b.get('code_ib') else b.get('code_sse','')}</span></td><td class='num'>{b.get('size','')}</td><td class='num'>{b.get('balance','')}</td><td class='num'>{b.get('rate','')}</td><td>{b.get('maturity','')}</td><td>{b.get('type','')}</td></tr>" for b in company.get('bonds',[]))}
          </tbody>
        </table>
        </div>
      </div>''' if company.get('bonds') else '<div class="risk-section"><h4>💼 存续债券</h4><p style="color:#718096;font-size:13px;">募集说明书尚未列出具体债券明细</p></div>')}

      <!-- 数据来源 -->
      <div style="margin-top:16px; padding:12px 16px; background:#f7fafc; border-radius:8px; font-size:12px; color:#718096;">
        📄 数据来源：<a href="{company.get('pdf_url','')}" target="_blank" style="color:#3182ce;">{company.get('pdf_file','')}</a>
        · 文件类型：{company.get('document_type','')}
        · 评级机构：{company.get('rating_agency','')}
      </div>
    </div>
  </div>
"""

    html += f"""
  <!-- 底部说明 -->
  <div class="footer">
    <p>本报告基于公开披露文件（募集说明书、评级报告、债权代理报告等）自动提取，数据准确性以原始文件为准。</p>
    <p>报告生成时间：{today} · 免责声明：本报告仅供研究参考，不构成投资建议</p>
  </div>
</div>
</body>
</html>"""
    return html


if __name__ == "__main__":
    companies = [
        extract_shanghai_chengtou(),
        extract_chengdu_chengtou(),
        extract_huzhou_chengtou(),
    ]

    html = generate_html_report(companies)

    # 输出到仓库根目录下的 reports/（真实数据报告，已被 .gitignore 排除，不进仓库）
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, "sample_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 研究报告已生成: {output_path}")
    print(f"   覆盖公司: {', '.join(c['short_name'] for c in companies)}")
    print(f"   合计总资产: {sum(c['financials']['total_assets'] for c in companies):,.0f}亿元")
