"""
CNINFO 债券文档采集器
使用直接HTTP请求（无需浏览器），支持断点续采

采集内容：
- 募集说明书（含摘要）
- 评级报告（含跟踪评级）
- 年度报告
- 受托管理事务报告

搜索策略：
1. 公司全称 + "募集说明书"
2. 公司全称 + "评级"
3. 公司全称 + "年度报告"（年份范围 2020-2025）
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw_cninfo")

sys.path.insert(0, os.path.dirname(__file__))
from shandong_companies import get_shandong_companies

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# 下载请求头
DOWNLOAD_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Referer": "https://www.cninfo.com.cn/new/information/topSearch/query",
}


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)[:80].strip()


def load_progress():
    pf = os.path.join(BASE_DIR, "collection_progress_cninfo.json")
    if os.path.exists(pf):
        with open(pf, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "stats": {"searched": 0, "found": 0, "downloaded": 0}}


def save_progress(p):
    pf = os.path.join(BASE_DIR, "collection_progress_cninfo.json")
    with open(pf, 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


def timestamp_to_date(ts):
    """CNINFO时间戳转日期"""
    try:
        ts = int(str(ts)[:10])
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except:
        return ''


def search_cninfo_api(keyword, tab_name='fulltext', page_size=50):
    """
    CNINFO 全文搜索API
    tab_name: fulltext(全部) | bond(债券)
    """
    params = urllib.parse.urlencode({
        'searchkey': keyword,
        'tabName': tab_name,
        'pageNum': 1,
        'pageSize': page_size,
        'sortName': 'nothing',
        'sortType': 'desc',
    })
    url = f'https://www.cninfo.com.cn/new/fulltextSearch/full?{params}'

    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get('announcements', []) or []
    except Exception as e:
        print(f"  [搜索失败] {keyword[:40]}: {e}")
        return []


def classify_doc_type(title):
    """根据标题分类文档类型"""
    t = title.lower()
    if '募集说明书' in t:
        if '摘要' in t:
            return '募集说明书摘要'
        return '募集说明书'
    if '跟踪评级' in t or '评级报告' in t or '信用评级' in t:
        return '评级报告'
    if '年度报告' in t:
        return '年度报告'
    if '半年度' in t or '中期' in t:
        return '半年度报告'
    if '受托管理' in t:
        return '受托管理报告'
    if '临时' in t:
        return '临时公告'
    return '其他'


def download_pdf(url, save_path):
    """下载PDF，返回 (success, size_bytes)"""
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        return True, os.path.getsize(save_path)

    req = urllib.request.Request(url, headers=DOWNLOAD_HEADERS)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = resp.read()
            ct = resp.headers.get('Content-Type', '')
            if 'html' in ct and len(data) < 50000:
                return False, 0
            with open(save_path, 'wb') as f:
                f.write(data)
            return True, len(data)
    except Exception:
        return False, 0


def collect_company(company_name, city, doc_types=None):
    """
    采集单家公司
    返回: (found_count, downloaded_count, docs_list)
    """
    if doc_types is None:
        doc_types = ['募集说明书', '评级报告']

    safe_city = city.replace("/", "_")
    safe_name = safe_filename(company_name)
    out_dir = os.path.join(RAW_DIR, safe_city, safe_name)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n  [{city}] {company_name}")

    all_docs = []
    seen_ids = set()

    # 每种文档类型分别搜索
    for doc_type in doc_types:
        keyword = f"{company_name} {doc_type}"
        results = search_cninfo_api(keyword, 'fulltext', 30)
        print(f"    {doc_type}: {len(results)} 条")

        for item in results:
            ann_id = item.get('announcementId', '')
            if ann_id in seen_ids:
                continue
            seen_ids.add(ann_id)

            title = re.sub(r'<[^>]+>', '', item.get('announcementTitle', ''))
            adjunct_url = item.get('adjunctUrl', '')
            pdf_url = f'https://static.cninfo.com.cn/{adjunct_url}' if adjunct_url else ''
            ann_time = item.get('announcementTime', 0)
            date_str = timestamp_to_date(ann_time)

            all_docs.append({
                'ann_id': ann_id,
                'title': title,
                'date': date_str,
                'doc_type': classify_doc_type(title),
                'pdf_url': pdf_url,
                'source': 'cninfo',
            })

    # 按日期降序排序
    all_docs.sort(key=lambda x: x['date'], reverse=True)

    # 去重：同一债券代码的同类文档只保留最新的
    deduped = []
    seen_bond = {}
    for doc in all_docs:
        # 提取债券代码（如 21青城10）
        bond_match = re.match(r'(\d{2}[\u4e00-\u9fa5]{2}\d{2})', doc['title'])
        bond_code = bond_match.group(1) if bond_match else ''
        key = f"{bond_code}_{doc['doc_type']}"

        if key not in seen_bond:
            seen_bond[key] = doc['date']
            deduped.append(doc)
        elif doc['date'] > seen_bond[key]:
            seen_bond[key] = doc['date']
            # 替换旧条目
            for i, d in enumerate(deduped):
                if f"{bond_code}_{d['doc_type']}" == key and d['date'] < doc['date']:
                    deduped[i] = doc
                    break

    print(f"    去重后: {len(deduped)} 条")

    # 下载PDF（限制数量避免过多）
    max_per_type = 5
    type_counts = {}
    downloaded = 0

    for doc in deduped:
        dt = doc['doc_type']
        type_counts[dt] = type_counts.get(dt, 0) + 1
        if type_counts[dt] > max_per_type:
            continue

        pdf_url = doc['pdf_url']
        if not pdf_url:
            continue

        fname = f"{doc['date']}_{safe_filename(doc['title'])[:40]}_{doc['ann_id']}.pdf"
        save_path = os.path.join(out_dir, fname)

        ok, size = download_pdf(pdf_url, save_path)
        if ok:
            downloaded += 1
            print(f"      ✅ [{doc['doc_type']}] {size/1024:.0f}KB")
        else:
            print(f"      ❌ [{doc['doc_type']}] 下载失败")

    # 保存元数据
    meta_file = os.path.join(out_dir, "_cninfo_meta.json")
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump({
            'company': company_name,
            'city': city,
            'search_time': datetime.now().isoformat(),
            'documents': deduped,
            'downloaded': downloaded,
        }, f, ensure_ascii=False, indent=2)

    return len(deduped), downloaded, deduped


def main():
    test_mode = '--test' in sys.argv
    single_company = None

    for arg in sys.argv[1:]:
        if arg.startswith('--company='):
            single_company = arg.split('=', 1)[1]

    progress = load_progress()
    companies = get_shandong_companies()

    if single_company:
        companies = [c for c in companies if single_company in c["name"]]
    elif test_mode:
        # 测试模式：取前3家高优先级公司
        companies = sorted(companies, key=lambda c: c['priority'])[:3]

    completed = {c["name"] for c in progress["completed"]}
    companies = [c for c in companies if c["name"] not in completed]

    print(f"\n{'#'*60}")
    print(f"  CNINFO 债券文档采集器")
    print(f"  目标: {len(companies)}家  已跳过: {len(completed)}家")
    print(f"  模式: {'测试' if test_mode else '全量'}")
    print(f"{'#'*60}")

    if not companies:
        print("  所有公司已采集完成！")
        return

    total_found = 0
    total_downloaded = 0

    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}]")
        try:
            found, dl, docs = collect_company(company["name"], company["city"])
            total_found += found
            total_downloaded += dl

            progress["completed"].append({
                'name': company["name"],
                'city': company["city"],
                'time': datetime.now().isoformat(),
                'found': found,
                'downloaded': dl,
            })
            progress["stats"]["searched"] += 1
            progress["stats"]["found"] += found
            progress["stats"]["downloaded"] += dl
            save_progress(progress)
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()

        time.sleep(0.5)  # 避免过快

    print(f"\n{'#'*60}")
    print(f"  完成！")
    print(f"  累计: 搜索{progress['stats']['searched']}家 | 发现{progress['stats']['found']}条 | 下载{progress['stats']['downloaded']}个")
    print(f"{'#'*60}")


if __name__ == '__main__':
    main()
