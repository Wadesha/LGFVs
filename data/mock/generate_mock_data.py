# -*- coding: utf-8 -*-
"""
城投研究 · 模拟数据生成器（单一数据源）

生成内容
--------
1. chengtou_mock.json  —— 多主体 × 多年份的合成结构化数据（字段与真实 schema 对齐）
2. ../index.html        —— 自包含展示看板（内嵌本数据 + 内联 SVG，无 CDN），用于 GitHub Pages

重要：本文件产生的全部数据均为**合成模拟数据**，不含任何真实披露、个人隐私或机密信息。
用于先跑通分析框架（看板 / 趋势 / 风险预警），真实数据按相同 schema 灌入即可复用。

复现：固定随机种子，多次运行结果一致。
用法：python generate_mock_data.py
依赖：仅标准库（json / random / datetime / os）
"""
import json
import os
import random
from datetime import datetime

SEED = 20260802
YEARS = list(range(2020, 2025))  # 2020 - 2024

# 主体蓝图：id, 简称, 全称, 省, 市, 评级, 行业
BLUEPRINTS = [
    ("sh", "沪城投",   "上海示范城投(集团)有限公司",       "上海市", "上海市", "AAA",  "城市基础设施建设与公用事业"),
    ("cd", "蓉城建设", "成都城市建设投资集团有限责任公司", "四川省", "成都市", "AAA",  "城市基础设施与运营"),
    ("gz", "穗城建设", "广州城投集团有限公司",             "广东省", "广州市", "AAA",  "城市基建与土地开发"),
    ("wh", "江城投资", "武汉城市发展投资集团有限责任公司", "湖北省", "武汉市", "AA+",  "城市基础设施建设"),
    ("tj", "滨海建投", "天津滨海新区建设投资集团",         "天津市", "天津市", "AA+",  "城市开发与园区建设"),
    ("km", "滇中开发", "昆明滇中开发投资集团",             "云南省", "昆明市", "AA",   "园区开发与基建"),
    ("cs", "星城发展", "长沙城市发展集团有限责任公司",     "湖南省", "长沙市", "AA",   "城市基础设施建设"),
    ("lz", "金城建发", "兰州金城建设发展集团",             "甘肃省", "兰州市", "AA-",  "城市基础设施建设"),
]

# 评级基线区间（亿元 / 百分比 / 倍数）
BASE = {
    "AAA": {"assets": (2200, 3800), "al": (50, 60), "roe": (2.0, 4.5), "ebi": (3.0, 6.0), "opcf": (20, 180), "rev": (200, 400), "cr": (1.3, 2.2)},
    "AA+": {"assets": (1100, 2000), "al": (58, 68), "roe": (1.4, 3.5), "ebi": (2.0, 4.0), "opcf": (-40, 120), "rev": (120, 300), "cr": (1.0, 1.8)},
    "AA":  {"assets": (550, 1200),  "al": (62, 72), "roe": (0.8, 2.6), "ebi": (1.3, 2.6), "opcf": (-90, 40),  "rev": (70, 200),  "cr": (0.8, 1.5)},
    "AA-": {"assets": (300, 700),   "al": (68, 78), "roe": (0.3, 1.8), "ebi": (0.9, 1.8), "opcf": (-60, 20),  "rev": (40, 120),  "cr": (0.7, 1.3)},
}


def rnd(a, b, nd=2):
    return round(random.uniform(a, b), nd)


def gen_entity(bp):
    eid, short, full, prov, city, rating, ind = bp
    b = BASE[rating]
    assets = rnd(*b["assets"], 0)
    al = rnd(*b["al"], 2)
    cr = rnd(*b["cr"], 2)
    series = []
    for i, yr in enumerate(YEARS):
        growth = 1 + random.uniform(0.03, 0.10)
        assets = assets * growth if i > 0 else assets
        al = max(45, min(82, al + rnd(-1.5, 1.5)))
        rev = rnd(*b["rev"], 1) * (1 + 0.06 * i)
        roe = max(0.1, min(6.0, rnd(*b["roe"], 2) * (1 + random.uniform(-0.12, 0.12))))
        ebi = max(0.6, b["ebi"][0] + (b["ebi"][1] - b["ebi"][0]) * random.random())
        ebi = round(ebi * (1 + random.uniform(-0.1, 0.1)), 2)
        opcf = rnd(*b["opcf"], 1)
        cr = max(0.6, min(2.6, cr + rnd(-0.12, 0.12)))
        qr = round(cr * random.uniform(0.3, 0.6), 2)
        liab = round(assets * al / 100.0, 1)
        equity = round(assets - liab, 1)
        net_profit = round(equity * roe / 100.0, 2)
        series.append({
            "year": yr,
            "total_assets": round(assets, 1),
            "total_liabilities": liab,
            "asset_liability_ratio": round(al, 2),
            "operating_revenue": round(rev, 1),
            "net_profit": net_profit,
            "roe": round(roe, 2),
            "ebitda_interest": ebi,
            "op_cf": opcf,
            "current_ratio": round(cr, 2),
            "quick_ratio": qr,
        })
    # 风险标记（基于最新年份）
    last = series[-1]
    flags = []
    if last["asset_liability_ratio"] > 70:
        flags.append("资产负债率超70%，杠杆偏高")
    if last["ebitda_interest"] < 1.5:
        flags.append("EBITDA利息保障倍数<1.5，偿债保障偏弱")
    if last["op_cf"] < 0:
        flags.append("经营现金流为负，自我造血能力不足")
    if last["roe"] < 1:
        flags.append("ROE低于1%，盈利能力偏弱")
    if last["current_ratio"] < 1.2:
        flags.append("流动比率偏低，短债压力较大")
    if last["quick_ratio"] < 0.6:
        flags.append("速动比率<0.6，资产流动性弱")
    if not flags:
        flags.append("各项指标处于健康区间")
    return {
        "id": eid, "short_name": short, "full_name": full,
        "province": prov, "city": city, "rating": rating, "industry": ind,
        "series": series, "risk_flags": flags,
    }


def build_data():
    random.seed(SEED)
    entities = [gen_entity(b) for b in BLUEPRINTS]
    return {
        "meta": {
            "note": "合成模拟数据，非真实披露；仅用于演示本项目分析框架。",
            "seed": SEED,
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "years": YEARS,
            "entity_count": len(entities),
            "source": "data/mock/generate_mock_data.py",
        },
        "entities": entities,
    }


# ---------------------------------------------------------------------------
# 展示页模板（内嵌数据 + 内联 SVG，无外部依赖）
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>城投公司研究 · 模拟数据看板（Demo）</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:"PingFang SC","Microsoft YaHei",Arial,sans-serif; background:#f4f6fb; color:#1f2937; line-height:1.6; }
  .wrap { max-width:1080px; margin:0 auto; padding:24px 16px 48px; }
  .header { background:linear-gradient(135deg,#0f2557 0%,#1d4ed8 100%); color:#fff; padding:28px 28px 24px; border-radius:14px; }
  .header h1 { font-size:24px; font-weight:800; }
  .header .sub { opacity:.85; font-size:13px; margin-top:6px; }
  .badge { display:inline-block; margin-top:12px; background:rgba(255,255,255,.16); padding:4px 12px; border-radius:20px; font-size:12px; }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:20px 0; }
  .kpi { background:#fff; border-radius:12px; padding:16px 18px; box-shadow:0 2px 10px rgba(15,37,87,.06); border-left:4px solid #2563eb; }
  .kpi .l { color:#6b7280; font-size:12px; }
  .kpi .v { font-size:22px; font-weight:800; color:#0f2557; margin-top:4px; }
  .kpi .s { font-size:11px; color:#9ca3af; margin-top:2px; }
  .card { background:#fff; border-radius:14px; padding:20px; box-shadow:0 2px 12px rgba(15,37,87,.06); margin-bottom:18px; }
  .card h2 { font-size:16px; color:#0f2557; margin-bottom:4px; display:flex; align-items:center; gap:8px; }
  .card .desc { font-size:12px; color:#6b7280; margin-bottom:12px; }
  .legend { display:flex; flex-wrap:wrap; gap:10px 16px; margin-top:10px; font-size:12px; color:#374151; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .legend i { width:11px; height:11px; border-radius:3px; display:inline-block; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th { background:#f3f5fb; text-align:left; padding:9px 10px; color:#4b5563; border-bottom:2px solid #e5e7eb; font-weight:600; }
  td { padding:9px 10px; border-bottom:1px solid #f0f2f7; vertical-align:top; }
  tr:hover td { background:#fafbff; }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .pill { display:inline-block; padding:2px 9px; border-radius:20px; font-size:11px; font-weight:700; }
  .good { color:#15803d; font-weight:700; } .bad { color:#b91c1c; font-weight:700; } .warn { color:#b45309; font-weight:700; }
  .foot { text-align:center; color:#9ca3af; font-size:12px; margin-top:24px; padding-top:16px; border-top:1px solid #e5e7eb; }
  .note { background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; font-size:12px; padding:10px 14px; border-radius:10px; margin-bottom:18px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🏛️ 城投公司信用研究 · 模拟数据看板</h1>
    <div class="sub">多主体 × 多年份分析框架演示 · 字段与真实披露 schema 对齐</div>
    <div class="badge">⚠️ 全部为合成模拟数据，非真实披露</div>
  </div>

  <div class="note" id="note"></div>

  <div class="kpis" id="kpis"></div>

  <div class="card">
    <h2>📊 主体评级分布</h2>
    <div class="desc">纳入样本的主体信用等级构成（AAA / AA+ / AA / AA-）。</div>
    <div id="chartRating"></div>
  </div>

  <div class="card">
    <h2>📉 最新年份资产负债率对比</h2>
    <div class="desc">条形越靠右杠杆越高；&lt;55% 绿 / 55–70% 橙 / &gt;70% 红（警戒）。</div>
    <div id="chartLeverage"></div>
  </div>

  <div class="card">
    <h2>📈 ROE 趋势（2020–2024）</h2>
    <div class="desc">净资产收益率年度走势，反映盈利能力的演变。</div>
    <div id="chartRoe"></div>
    <div class="legend" id="legendRoe"></div>
  </div>

  <div class="card">
    <h2>💰 总资产规模趋势（2020–2024）</h2>
    <div class="desc">资产体量年度增长，体现平台扩张节奏。</div>
    <div id="chartAssets"></div>
    <div class="legend" id="legendAssets"></div>
  </div>

  <div class="card">
    <h2>🚩 风险预警汇总（最新年份）</h2>
    <div class="desc">关键偿债与盈利指标 + 触发的风险标签。</div>
    <div style="overflow-x:auto;"><table id="riskTable"></table></div>
  </div>

  <div class="foot" id="foot"></div>
</div>

<script>
const DATA = __MOCK_DATA__;
const COLORS = ['#2563eb','#16a34a','#d97706','#dc2626','#7c3aed','#0891b2','#db2777','#65a30d'];
const YEARS = DATA.meta.years;
const ENTS = DATA.entities;

const fmt = (n,d=1)=> Number(n).toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d});
const svgOpen = (w,h)=>`<svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet" style="display:block">`;

function renderNote(){
  document.getElementById('note').textContent =
    '说明：' + DATA.meta.note + ' 生成日期 ' + DATA.meta.generated_at +
    ' · 样本 ' + DATA.meta.entity_count + ' 家 · 年份 ' + YEARS[0] + '–' + YEARS[YEARS.length-1] +
    '。真实数据按相同 schema 灌入即可复用，详见 README。';
}

function renderKPI(){
  const last = ENTS.map(e=>e.series[e.series.length-1]);
  const totalAssets = last.reduce((s,e)=>s+e.total_assets,0);
  const avgAL = last.reduce((s,e)=>s+e.asset_liability_ratio,0)/last.length;
  const aaa = ENTS.filter(e=>e.rating==='AAA').length;
  const cards = [
    {l:'纳入主体', v:ENTS.length, s:'家城投公司'},
    {l:'总资产合计（最新年）', v:fmt(totalAssets,0), s:'亿元'},
    {l:'平均资产负债率', v:fmt(avgAL,1)+'%', s:'行业参考 <60%'},
    {l:'AAA 主体占比', v:(aaa/ENTS.length*100).toFixed(0)+'%', s:aaa+' / '+ENTS.length+' 家'},
  ];
  document.getElementById('kpis').innerHTML = cards.map(c=>
    `<div class="kpi"><div class="l">${c.l}</div><div class="v">${c.v}</div><div class="s">${c.s}</div></div>`).join('');
}

function ratingDist(){
  const order=['AAA','AA+','AA','AA-'];
  const counts={}; order.forEach(r=>counts[r]=0);
  ENTS.forEach(e=>counts[e.rating]++);
  const max=Math.max(1,...Object.values(counts));
  const W=680,H=260,pad=30, bw=70, gap=(W-pad*2-order.length*bw)/(order.length+1);
  let s=svgOpen(W,H);
  order.forEach((r,i)=>{
    const bh=counts[r]/max*(H-pad*2);
    const x=pad+gap+i*(bw+gap), y=H-pad-bh;
    const col={'AAA':'#15803d','AA+':'#2563eb','AA':'#d97706','AA-':'#dc2626'}[r];
    s+=`<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="6" fill="${col}"/>`;
    s+=`<text x="${x+bw/2}" y="${y-8}" text-anchor="middle" font-size="14" font-weight="700" fill="#374151">${counts[r]}</text>`;
    s+=`<text x="${x+bw/2}" y="${H-pad+18}" text-anchor="middle" font-size="13" fill="#374151">${r}</text>`;
  });
  s+='</svg>';
  document.getElementById('chartRating').innerHTML=s;
}

function leverageBars(){
  const W=680, rowH=34, padL=92, padR=70, H=ENTS.length*rowH+16;
  const maxScale=85, innerW=W-padL-padR;
  let s=svgOpen(W,H);
  ENTS.forEach((e,i)=>{
    const al=e.series[e.series.length-1].asset_liability_ratio;
    const y=8+i*rowH, bh=18;
    const col= al>70?'#dc2626':(al>55?'#d97706':'#15803d');
    const bw=Math.max(2, al/maxScale*innerW);
    s+=`<text x="${padL-10}" y="${y+bh/2+4}" text-anchor="end" font-size="12" fill="#374151">${e.short_name}</text>`;
    s+=`<rect x="${padL}" y="${y}" width="${innerW}" height="${bh}" rx="4" fill="#eef2f7"/>`;
    s+=`<rect x="${padL}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${col}"/>`;
    s+=`<text x="${padL+bw+8}" y="${y+bh/2+4}" font-size="12" font-weight="700" fill="${col}">${al.toFixed(1)}%</text>`;
  });
  s+='</svg>';
  document.getElementById('chartLeverage').innerHTML=s;
}

function lineChart(elId, legendId, accessor, yFmt){
  const W=680,H=320, pad={l:58,r:18,t:16,b:36};
  const iw=W-pad.l-pad.r, ih=H-pad.t-pad.b;
  const series=ENTS.map((e,i)=>({name:e.short_name,color:COLORS[i%COLORS.length],
    points:e.series.map(p=>({v:accessor(p)}))}));
  let allv=[]; series.forEach(s=>s.points.forEach(p=>allv.push(p.v)));
  let min=Math.min(...allv), max=Math.max(...allv);
  if(min===max){min-=1;max+=1;}
  const x=i=> pad.l + (YEARS.length===1?iw/2: iw*i/(YEARS.length-1));
  const y=v=> pad.t + ih - ih*(v-min)/(max-min);
  let s=svgOpen(W,H);
  for(let g=0;g<=4;g++){ const val=min+(max-min)*g/4, yy=y(val);
    s+=`<line x1="${pad.l}" y1="${yy.toFixed(1)}" x2="${W-pad.r}" y2="${yy.toFixed(1)}" stroke="#eef2f7"/>`;
    s+=`<text x="${pad.l-8}" y="${yy+4}" text-anchor="end" font-size="10" fill="#9ca3af">${yFmt(val)}</text>`; }
  YEARS.forEach((yr,i)=> s+=`<text x="${x(i)}" y="${H-pad.b+18}" text-anchor="middle" font-size="10" fill="#9ca3af">${yr}</text>`);
  series.forEach(se=>{
    const d=se.points.map((p,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
    s+=`<path d="${d}" fill="none" stroke="${se.color}" stroke-width="2"/>`;
    se.points.forEach((p,i)=> s+=`<circle cx="${x(i).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="2.6" fill="${se.color}"/>`);
  });
  s+='</svg>';
  document.getElementById(elId).innerHTML=s;
  document.getElementById(legendId).innerHTML=series.map(se=>
    `<span><i style="background:${se.color}"></i>${se.name}</span>`).join('');
}

function riskTable(){
  const rows=ENTS.map(e=>{
    const f=e.series[e.series.length-1];
    const alCls= f.asset_liability_ratio>70?'bad':(f.asset_liability_ratio>55?'warn':'good');
    const ebiCls= f.ebitda_interest<1.5?'bad':(f.ebitda_interest<2.5?'warn':'good');
    const opCls= f.op_cf<0?'bad':'good';
    const roeCls= f.roe<1?'bad':(f.roe<2?'warn':'good');
    const rcol={'AAA':'#15803d','AA+':'#2563eb','AA':'#d97706','AA-':'#dc2626'}[e.rating];
    const flags=e.risk_flags.map(x=>`• ${x}`).join('<br>');
    return `<tr>
      <td><b>${e.short_name}</b><br><span style="color:#9ca3af;font-size:11px">${e.province}·${e.city}</span></td>
      <td><span class="pill" style="background:${rcol}1a;color:${rcol}">${e.rating}</span></td>
      <td class="num ${alCls}">${f.asset_liability_ratio.toFixed(1)}%</td>
      <td class="num ${ebiCls}">${f.ebitda_interest.toFixed(2)}x</td>
      <td class="num ${opCls}">${fmt(f.op_cf,1)}</td>
      <td class="num ${roeCls}">${f.roe.toFixed(2)}%</td>
      <td style="font-size:11.5px;color:#b45309;min-width:200px">${flags}</td>
    </tr>`;
  }).join('');
  document.getElementById('riskTable').innerHTML =
    `<thead><tr><th>主体</th><th>评级</th><th>资产负债率</th><th>EBITDA利保</th><th>经营现金流(亿)</th><th>ROE</th><th>风险标签</th></tr></thead><tbody>${rows}</tbody>`;
}

function renderFoot(){
  document.getElementById('foot').innerHTML =
    '本页为 <b>'+DATA.meta.entity_count+'</b> 家城投主体的<b>合成模拟数据</b>演示 · 生成于 '+DATA.meta.generated_at+
    '<br>数据驱动框架：公开披露 PDF → 结构化字段 → 多主体×多年份分析 → 看板/预警。真实数据按相同 schema 灌入即可复用。';
}

renderNote(); renderKPI(); ratingDist(); leverageBars();
lineChart('chartRoe','legendRoe', p=>p.roe, v=>fmt(v,1)+'%');
lineChart('chartAssets','legendAssets', p=>p.total_assets, v=>fmt(v,0));
riskTable(); renderFoot();
</script>
</body>
</html>
"""


def main():
    data = build_data()
    here = os.path.dirname(os.path.abspath(__file__))
    # 1) JSON
    json_path = os.path.join(here, "chengtou_mock.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 2) HTML（内嵌数据）
    html = TEMPLATE.replace("__MOCK_DATA__", json.dumps(data, ensure_ascii=False))
    html_path = os.path.join(here, "..", "..", "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ 模拟数据已生成")
    print("   -", json_path)
    print("   -", os.path.abspath(html_path))
    print("   主体数:", data["meta"]["entity_count"], "年份:", YEARS[0], "-", YEARS[-1])


if __name__ == "__main__":
    main()
