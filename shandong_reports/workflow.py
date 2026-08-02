"""
山东城投债券采集 - 完整工作流
=============================
【工作模式】
  模式A（推荐）：你提供PDF URL → 我下载+提取+生成报告
  模式B：你提供PDF文件 → 我提取+生成报告

【使用方法】
  # 模式A：提供URL列表（CSV格式）
  python workflow.py --url-list urls.csv
  
  # 模式B：处理已有PDF
  python workflow.py --process-pdfs
  
  # 生成报告
  python workflow.py --report

【URL列表格式】（urls.csv）
  公司名,城市,PDF_URL,类型
  青岛城市建设投资(集团)有限责任公司,青岛,https://static.sse.com.cn/...,募集说明书
  济南城市投资集团有限公司,济南,http://file.finance.sina.com.cn/...,评级报告

【输出】
  raw/{城市}/{公司名}/XXXX.pdf  ← 下载的PDF
  reports/shandong_report_YYYYMMDD.html  ← HTML报告
"""

import csv
import urllib.request
import ssl
import os
import sys
import json
import pdfplumber
from datetime import datetime
import re

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw")
REPORT_DIR = os.path.join(BASE_DIR, "..", "reports")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def download_pdf(url, save_path, timeout=30):
    """下载PDF"""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    if os.path.exists(save_path):
        size = os.path.getsize(save_path)
        if size > 10240:
            print(f"  [已存在] {os.path.basename(save_path)} ({size//1024}KB)")
            return True
    
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 10240:
                print(f"  [文件过小] {len(data)} bytes，可能不是PDF")
                return False
            with open(save_path, 'wb') as f:
                f.write(data)
            print(f"  [成功] {os.path.basename(save_path)} ({len(data)//1024}KB)")
            return True
    except Exception as e:
        print(f"  [失败] {str(e)[:80]}")
        return False


def extract_pdf_data(pdf_path):
    """从PDF提取结构化数据"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:20]:  # 只看前20页
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"  [提取失败] {e}")
        return {}
    
    if not text:
        return {}
    
    data = {"raw_text": text[:2000]}  # 保存前2000字符用于调试
    
    # 提取公司名
    m = re.search(r'(.+?)(?:有限责任公司|有限公司)', text)
    if m:
        data['company_name'] = m.group(1).strip() + (text[m.end():m.end()+4] if m.end() < len(text) else '')
    
    # 提取财务指标
    patterns = {
        'total_assets': r'资产总额[^\d]*?([\d,.]+)\s*亿',
        'asset_liability_ratio': r'资产负债率[^\d]*?([\d.]+)\s*%',
        'net_profit': r'净利润[^\d]*?([\d,.]+)\s*亿',
        'revenue': r'营业收入[^\d]*?([\d,.]+)\s*亿',
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).replace(',', '')
            try:
                data[key] = float(val)
            except:
                pass
    
    return data


def process_url_list(csv_path):
    """处理URL列表CSV"""
    print(f"\n读取URL列表: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"文件不存在: {csv_path}")
        return
    
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get('公司名', '')
            city = row.get('城市', '')
            url = row.get('PDF_URL', '')
            doc_type = row.get('类型', '募集说明书')
            
            if not company or not url:
                continue
            
            print(f"\n处理: {company[:20]}...")
            
            # 下载PDF
            save_dir = os.path.join(RAW_DIR, city, company)
            fname = url.split('/')[-1] or f"{doc_type}.pdf"
            save_path = os.path.join(save_dir, fname)
            
            if download_pdf(url, save_path):
                # 提取数据
                data = extract_pdf_data(save_path)
                data['company'] = company
                data['city'] = city
                data['pdf_path'] = save_path
                data['doc_type'] = doc_type
                data['pdf_url'] = url
                results.append(data)
    
    # 保存提取结果
    output_file = os.path.join(BASE_DIR, 'extracted_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 提取完成！共 {len(results)} 个PDF")
    print(f"   数据已保存: {output_file}")
    return results


def generate_report(data_list):
    """生成HTML报告"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, f"shandong_report_{datetime.now().strftime('%Y%m%d')}.html")
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>山东城投债券研究报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background: #f5f5f5; }}
.header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 30px; border-radius: 8px; }}
.card {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f8f9fa; font-weight: 600; }}
.risk-low {{ color: #28a745; }}
.risk-mid {{ color: #ffc107; }}
.risk-high {{ color: #dc3545; }}
</style>
</head>
<body>
<div class="header">
    <h1>山东城投债券研究报告</h1>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 纳入公司: {len(data_list)} 家</p>
</div>
"""
    
    for data in data_list:
        company = data.get('company', '未知')
        city = data.get('city', '')
        doc_type = data.get('doc_type', '')
        pdf_url = data.get('pdf_url', '')
        
        html += f"""
<div class="card">
    <h2>{company}</h2>
    <p>城市: {city} | 类型: {doc_type}</p>
    <table>
        <tr><th>指标</th><th>数值</th></tr>
"""
        
        for key in ['total_assets', 'asset_liability_ratio', 'net_profit', 'revenue']:
            val = data.get(key)
            if val:
                unit = '亿' if key != 'asset_liability_ratio' else '%'
                html += f"        <tr><td>{key}</td><td>{val}{unit}</td></tr>\n"
        
        html += f"""    </table>
    <p><a href="{pdf_url}" target="_blank">下载PDF</a></p>
</div>
"""
    
    html += """
</body>
</html>
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ 报告已生成: {report_file}")
    return report_file


def main():
    import argparse
    parser = argparse.ArgumentParser(description='山东城投债券采集-完整工作流')
    parser.add_argument('--url-list', type=str, help='URL列表CSV文件')
    parser.add_argument('--process-pdfs', action='store_true', help='处理已有PDF')
    parser.add_argument('--report', action='store_true', help='生成报告')
    args = parser.parse_args()
    
    if args.url_list:
        results = process_url_list(args.url_list)
        if results and args.report:
            generate_report(results)
    elif args.process_pdfs:
        # 扫描raw目录，处理所有PDF
        print("扫描本地PDF文件...")
        # TODO: implement
    elif args.report:
        # 从extracted_data.json生成报告
        data_file = os.path.join(BASE_DIR, 'extracted_data.json')
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
            generate_report(data_list)
        else:
            print("没有提取数据，请先运行 --url-list")
    else:
        print("""
使用方法：
  python workflow.py --url-list urls.csv   # 提供URL列表，自动下载+提取
  python workflow.py --report            # 生成报告
  
URL列表格式（CSV）：
  公司名,城市,PDF_URL,类型
  青岛城市建设投资(集团)有限责任公司,青岛,https://...,募集说明书
""")


if __name__ == '__main__':
    main()
