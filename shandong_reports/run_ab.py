"""
城投债采集：CNINFO(A) + chinamoney(B) 交替执行控制器

使用方式：
  python run_ab.py                  # 交替模式（默认）
  python run_ab.py --cninfo-only    # 仅跑 CNINFO
  python run_ab.py --chinamoney-only # 仅跑 chinamoney
  python run_ab.py --test           # 测试模式（每队列2家）
  python run_ab.py --batch=5        # 每批交替5家

负载均衡策略：
  A (CNINFO):  HTTP请求，轻量，可并发3个线程
  B (chinamoney): Playwright浏览器，较重，串行执行
  两者交替执行，每轮结束后短暂暂停让系统冷却
"""

import asyncio
import json
import os
import re
import ssl
import sys
import time
import signal
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from playwright.async_api import async_playwright

# ===== 路径配置 =====
BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
sys.path.insert(0, BASE_DIR)
from shandong_companies import get_shandong_companies

# ===== 常量 =====
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER_CM = "https://www.chinamoney.com.cn/chinese/qwjsn/"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
DOWNLOAD_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Referer": "https://www.cninfo.com.cn/new/information/topSearch/query",
}

# ===== 进度文件 =====
PROGRESS_A = os.path.join(BASE_DIR, "collection_progress_cninfo.json")
PROGRESS_B = os.path.join(BASE_DIR, "collection_progress_chinamoney.json")
PROGRESS_META = os.path.join(BASE_DIR, "collection_progress_meta.json")  # 共享元数据


def load_meta():
    if os.path.exists(PROGRESS_META):
        with open(PROGRESS_META, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "run_id": datetime.now().strftime('%Y%m%d%H%M%S'),
        "started_at": datetime.now().isoformat(),
        "last_run": None,
        "交替轮次": 0,
        "a轮次": 0,
        "b轮次": 0,
        "a_done": [],
        "b_done": [],
    }


def save_meta(meta):
    meta["last_run"] = datetime.now().isoformat()
    with open(PROGRESS_META, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def load_progress(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "stats": {"searched": 0, "found": 0, "downloaded": 0}}


def save_progress(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)[:80].strip()


# ============================================================
# A任务：CNINFO HTTP 采集
# ============================================================

def timestamp_to_date(ts):
    try:
        ts = int(str(ts)[:10])
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except:
        return ''


def classify_doc_type(title):
    t = title
    if '募集说明书' in t:
        return '募集说明书摘要' if '摘要' in t else '募集说明书'
    if '跟踪评级' in t or '评级报告' in t or '信用评级' in t:
        return '评级报告'
    if '年度报告' in t:
        return '年度报告'
    if '半年度' in t or '中期' in t:
        return '半年度报告'
    if '受托管理' in t:
        return '受托管理报告'
    return '其他'


def search_cninfo(keyword, page_size=50):
    params = urllib.parse.urlencode({
        'searchkey': keyword,
        'tabName': 'fulltext',
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
        print(f"    [CNINFO搜索失败] {e}")
        return []


def download_pdf(url, save_path):
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        return True, os.path.getsize(save_path), 'cached'
    req = urllib.request.Request(url, headers=DOWNLOAD_HEADERS)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = resp.read()
            ct = resp.headers.get('Content-Type', '')
            if 'html' in ct and len(data) < 50000:
                return False, 0, 'html_rejected'
            with open(save_path, 'wb') as f:
                f.write(data)
            return True, len(data), 'ok'
    except Exception as e:
        return False, 0, str(e)


def collect_company_a(company):
    """采集单家公司 CNINFO 文档"""
    name = company['name']
    city = company['city']
    safe_city = city.replace("/", "_")
    safe_name = safe_filename(name)
    out_dir = os.path.join(BASE_DIR, "raw_cninfo", safe_city, safe_name)
    os.makedirs(out_dir, exist_ok=True)

    doc_types = ['募集说明书', '评级报告']
    all_docs = []
    seen_ids = set()

    for dt in doc_types:
        keyword = f"{name} {dt}"
        results = search_cninfo(keyword, 30)
        for item in results:
            ann_id = item.get('announcementId', '')
            if ann_id in seen_ids:
                continue
            seen_ids.add(ann_id)
            title = re.sub(r'<[^>]+>', '', item.get('announcementTitle', ''))
            adjunct_url = item.get('adjunctUrl', '')
            pdf_url = f'https://static.cninfo.com.cn/{adjunct_url}' if adjunct_url else ''
            ann_time = item.get('announcementTime', 0)
            all_docs.append({
                'ann_id': ann_id,
                'title': title,
                'date': timestamp_to_date(ann_time),
                'doc_type': classify_doc_type(title),
                'pdf_url': pdf_url,
                'source': 'cninfo',
            })

    # 去重
    deduped = []
    seen_bond = {}
    for doc in all_docs:
        bond_match = re.match(r'(\d{2}[\u4e00-\u9fa5]{2}\d{2})', doc['title'])
        bond_code = bond_match.group(1) if bond_match else ''
        key = f"{bond_code}_{doc['doc_type']}"
        if key not in seen_bond:
            seen_bond[key] = doc['date']
            deduped.append(doc)
        elif doc['date'] > seen_bond[key]:
            seen_bond[key] = doc['date']
            for i, d in enumerate(deduped):
                if f"{bond_code}_{d['doc_type']}" == key and d['date'] < doc['date']:
                    deduped[i] = doc
                    break

    # 下载
    downloaded = 0
    for doc in deduped[:8]:  # 每类最多4个
        if not doc['pdf_url']:
            continue
        fname = f"{doc['date']}_{safe_filename(doc['title'])[:40]}_{doc['ann_id']}.pdf"
        save_path = os.path.join(out_dir, fname)
        ok, size, status = download_pdf(doc['pdf_url'], save_path)
        if ok:
            downloaded += 1

    # 保存元数据
    meta_file = os.path.join(out_dir, "_cninfo_meta.json")
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump({
            'company': name, 'city': city,
            'search_time': datetime.now().isoformat(),
            'documents': deduped, 'downloaded': downloaded,
        }, f, ensure_ascii=False, indent=2)

    return {
        'name': name, 'city': city,
        'time': datetime.now().isoformat(),
        'found': len(deduped), 'downloaded': downloaded,
    }


def run_batch_a(companies, progress_a):
    """并发执行 A 任务批次"""
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(collect_company_a, c): c for c in companies}
        for future in as_completed(futures):
            c = futures[future]
            try:
                result = future.result()
                results.append(result)
                progress_a["completed"].append(result)
                progress_a["stats"]["searched"] += 1
                progress_a["stats"]["found"] += result['found']
                progress_a["stats"]["downloaded"] += result['downloaded']
                save_progress(PROGRESS_A, progress_a)
                status = "✅" if result['downloaded'] > 0 else "⚪"
                print(f"  A {status} {c['city']}/{c['name'][:20]} → 发现{result['found']} 下{result['downloaded']}")
            except Exception as e:
                print(f"  A ❌ {c['name'][:20]} → {e}")
    return results


# ============================================================
# B任务：chinamoney Playwright 采集
# ============================================================

def parse_filterLevel_params(onclick_str):
    match = re.search(r'filterLevel\s*\(([^)]+)\)', onclick_str)
    if not match:
        return None
    params_str = match[1]
    parts, current, in_quote, quote_char = [], '', False, ''
    for c in params_str:
        if not in_quote and c in "'\"":
            in_quote, quote_char = True, c
            current += c
        elif in_quote and c == quote_char:
            in_quote = False
            current += c
        elif not in_quote and c == ',':
            parts.append(current.strip())
            current = ''
        else:
            current += c
    parts.append(current.strip())
    clean = [p.strip("'\"") if p.strip("'\"\t ") not in ('null', 'false', 'true', '') else p.strip("'\"\t ") for p in parts]
    if len(clean) < 8:
        return None
    return {
        'contentId': clean[1], 'channel': clean[2], 'title': clean[4],
        'ctime': clean[5], 'isOpen': clean[6] == 'true', 'url': clean[7],
    }


async def search_chinamoney(page, company_name):
    encoded_kw = urllib.parse.quote(company_name)
    search_url = f"https://www.chinamoney.com.cn/chinese/qwjsn/?searchValue={encoded_kw}"
    try:
        resp = await page.goto(search_url, wait_until='networkidle', timeout=25000)
    except Exception:
        try:
            resp = await page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
        except Exception as e:
            print(f"    [chinamoney加载失败] {e}")
            return [], 'network_error'

    await page.wait_for_timeout(4000)
    title = await page.title()
    if '维护' in title:
        return [], 'maintenance'

    # 检测页面内容
    body_text = await page.inner_text('body')
    if '维护' in body_text[:500]:
        return [], 'maintenance'

    results = await page.evaluate("""
        () => {
            const items = [];
            const seen = new Set();
            document.querySelectorAll('[onclick*="filterLevel"]').forEach(el => {
                const onclick = el.getAttribute('onclick') || '';
                let text = '';
                const row = el.closest('tr') || el.closest('.result-item') || el.closest('li') || el;
                text = row.textContent || '';
                const match = onclick.match(/filterLevel\\s*\\(([^)]+)\\)/);
                if (match) {
                    const raw = match[0];
                    const allQuoted = [...raw.matchAll(/'([^']*)'/g)].map(m => m[1]);
                    const cid = allQuoted[1] || '';
                    if (cid && !seen.has(cid)) {
                        seen.add(cid);
                        items.push({ onclick, text: text.trim().slice(0, 200) });
                    }
                }
            });
            return items;
        }
    """)

    documents = {}
    for item in results:
        parsed = parse_filterLevel_params(item['onclick'])
        if not parsed or not parsed['isOpen']:
            continue
        cid = parsed['contentId']
        documents[cid] = {
            'contentId': cid, 'channel': parsed['channel'],
            'title': parsed['title'] or item['text'][:80],
            'url': parsed['url'], 'ctime': parsed['ctime'],
        }
    return list(documents.values()), 'ok'


def get_lt_tokens():
    """获取 chinamoney 下载所需的 UT + sign token（无需 session）"""
    req = urllib.request.Request(
        'https://www.chinamoney.com.cn/lss/rest/cm-s-account/getLT',
        data=b'',
        headers={
            'User-Agent': UA,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.chinamoney.com.cn/chinese/qwjsn/',
        }
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read())
            return data['data']['UT'].strip(), data['data']['sign'].strip()
    except Exception:
        return None, None


def download_cm_file(content_id, save_path, referer=None):
    """
    chinamoney PDF 下载（2步：getLT token → 真实下载URL）
    content_id: 从 filterLevel onclick 提取的 contentId
    """
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024 * 50:
        # 已有文件且 > 50KB，跳过（假文件 ~8KB会被覆盖）
        return True, os.path.getsize(save_path), 'cached'

    # Step 1: 获取 token
    ut, sign = get_lt_tokens()
    if not ut or not sign:
        return False, 0, 'no_token'

    # Step 2: 构造真实下载 URL
    path = f'fileDownLoad.do?mode=open&contentId={content_id}&priority=0&ut={urllib.parse.quote(ut)}&sign={urllib.parse.quote(sign)}'
    url = 'https://www.chinamoney.com.cn/dqs/cm-s-notice-query/' + path

    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': referer or 'https://www.chinamoney.com.cn/dqs/rest/cm-s-security/dealPath',
        'Accept': 'application/pdf,application/octet-stream,*/*',
    })
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = resp.read()
            ct = resp.headers.get('Content-Type', '')
            # 验证是真实 PDF（> 50KB）
            if 'html' in ct.lower() or len(data) < 50000:
                return False, 0, 'not_pdf'
            with open(save_path, 'wb') as f:
                f.write(data)
            return True, len(data), 'ok'
    except Exception as e:
        return False, 0, str(e)


async def collect_company_b(page, company, progress_b):
    """采集单家公司 chinamoney 文档"""
    name = company['name']
    city = company['city']
    safe_city = city.replace("/", "_")
    safe_name = safe_filename(name)
    out_dir = os.path.join(BASE_DIR, "raw", safe_city, safe_name)
    os.makedirs(out_dir, exist_ok=True)

    docs, status = await search_chinamoney(page, name)
    if status == 'maintenance':
        print(f"    ⚠️ chinamoney 维护中，跳过")
        return {'name': name, 'city': city, 'time': datetime.now().isoformat(),
                'found': 0, 'downloaded': 0, 'status': 'maintenance'}
    if status == 'network_error':
        print(f"    ⚠️ 网络错误，跳过")
        return {'name': name, 'city': city, 'time': datetime.now().isoformat(),
                'found': 0, 'downloaded': 0, 'status': 'network_error'}

    downloaded = 0
    for doc in docs[:5]:
        content_id = doc.get('contentId', '')
        if not content_id:
            continue
        fname = f"{safe_name}_{content_id}.pdf"
        save_path = os.path.join(out_dir, fname)
        ok, size, st = download_cm_file(content_id, save_path)
        if ok:
            downloaded += 1
            print(f"      ✅ {fname} ({size//1024}KB)")

    meta_file = os.path.join(out_dir, "_chinamoney_meta.json")
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump({
            'company': name, 'city': city,
            'search_time': datetime.now().isoformat(),
            'documents': docs, 'downloaded': downloaded,
        }, f, ensure_ascii=False, indent=2)

    result = {'name': name, 'city': city, 'time': datetime.now().isoformat(),
              'found': len(docs), 'downloaded': downloaded, 'status': 'ok'}
    progress_b["completed"].append(result)
    progress_b["stats"]["searched"] += 1
    progress_b["stats"]["found"] += len(docs)
    progress_b["stats"]["downloaded"] += downloaded
    save_progress(PROGRESS_B, progress_b)
    return result


async def run_batch_b(companies, progress_b):
    """串行执行 B 任务批次（Playwright 需要共享 browser）"""
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled',
                  '--disable-dev-shm-usage', '--disable-setuid-sandbox']
        )
        ctx = await browser.new_context(
            user_agent=UA, viewport={'width': 1280, 'height': 900},
            locale='zh-CN',
            extra_http_headers={'Accept-Language': 'zh-CN,zh;q=0.9'}
        )
        page = await ctx.new_page()
        page.set_default_timeout(30000)

        for company in companies:
            print(f"  B 🔍 {company['city']}/{company['name'][:20]}", end='', flush=True)
            try:
                result = await collect_company_b(page, company, progress_b)
                results.append(result)
                if result['status'] == 'maintenance':
                    print(f" → ⚠️ 维护中")
                    break  # 遇到维护，暂停B
                elif result['downloaded'] > 0:
                    print(f" → ✅ 下{result['downloaded']}")
                else:
                    print(f" → ⚪ 0")
            except Exception as e:
                print(f" → ❌ {e}")
            await asyncio.sleep(1.5)

        await browser.close()
    return results


# ============================================================
# 主控制器
# ============================================================

def get_pending_companies(progress_a, progress_b, companies):
    """获取未完成的公司列表，优先队列优先"""
    done_a = {c['name'] for c in progress_a['completed']}
    done_b = {c['name'] for c in progress_b['completed']}
    pending = []
    for c in sorted(companies, key=lambda x: x['priority']):
        name = c['name']
        if name not in done_a or name not in done_b:
            pending.append({
                **c,
                'a_done': name in done_a,
                'b_done': name in done_b,
            })
    return pending


async def run_ab(mode='alternating', batch_size=3, test=False):
    """交替执行 A/B"""
    meta = load_meta()
    progress_a = load_progress(PROGRESS_A)
    progress_b = load_progress(PROGRESS_B)

    companies = get_shandong_companies()
    if test:
        companies = [c for c in companies if c['priority'] == 1][:4]

    pending = get_pending_companies(progress_a, progress_b, companies)
    print(f"\n{'='*60}")
    print(f"  🦾 城投债采集控制器")
    print(f"  模式: {'交替' if mode=='alternating' else mode}")
    print(f"  批大小: {batch_size} | 测试: {test}")
    print(f"  公司: {len(companies)}家 | 待采集: {len(pending)}家")
    print(f"  A已完成: {len(progress_a['completed'])} | B已完成: {len(progress_b['completed'])}")
    print(f"{'='*60}\n")

    if mode == 'cninfo-only':
        # 只跑 A
        batches = [pending[i:i+batch_size] for i in range(0, len(pending), batch_size)]
        for batch in batches:
            run_batch_a(batch, progress_a)
            time.sleep(2)
        print("\n✅ CNINFO 采集完成")
        return

    if mode == 'chinamoney-only':
        # 只跑 B
        await run_batch_b(pending, progress_b)
        print("\n✅ chinamoney 采集完成")
        return

    # ===== 交替模式 =====
    # 分配：A 优先给未完成的，B 优先给A已完成的（互补）
    pending_a = [c for c in pending if not c['a_done']]
    pending_b = [c for c in pending if not c['b_done']]

    round_num = 0
    while pending_a or pending_b:
        round_num += 1
        meta['交替轮次'] = round_num
        print(f"\n{'='*60}")
        print(f"  🔄 第 {round_num} 轮 | A待:{len(pending_a)} B待:{len(pending_b)}")
        print(f"{'='*60}")

        # ---- A 批次 ----
        if pending_a:
            batch_a = pending_a[:batch_size]
            meta['a轮次'] += 1
            print(f"\n  [A] CNINFO 批次 ({len(batch_a)}家)")
            run_batch_a(batch_a, progress_a)
            pending_a = pending_a[batch_size:]
            time.sleep(3)  # 冷却
        else:
            print("\n  [A] ✓ 已全部完成")

        # ---- B 批次 ----
        if pending_b:
            meta['b轮次'] += 1
            print(f"\n  [B] chinamoney 批次 ({len(pending_b[:batch_size])}家)")
            b_results = await run_batch_b(pending_b[:batch_size], progress_b)

            # 如果遇到维护，暂停B
            if any(r.get('status') == 'maintenance' for r in b_results):
                print("\n  ⚠️ chinamoney 维护中，B暂停，等待下一轮手动检查")
                save_meta(meta)
                return

            pending_b = pending_b[batch_size:]
            time.sleep(5)  # Playwright 较重，多等一会
        else:
            print("\n  [B] ✓ 已全部完成")

        save_meta(meta)

        # 全部完成退出
        pending_a = [c for c in pending_a if c['name'] not in {r['name'] for r in progress_a['completed']}]
        pending_b = [c for c in pending_b if c['name'] not in {r['name'] for r in progress_b['completed']}]

        if not pending_a and not pending_b:
            break

        # 防止死循环：重新计算
        pending_a = [c for c in pending if not any(x['name'] == c['name'] for x in progress_a['completed'])]
        pending_b = [c for c in pending if not any(x['name'] == c['name'] for x in progress_b['completed'])]

        print(f"\n  📊 轮次汇总: 累计A完成{len(progress_a['completed'])} B完成{len(progress_b['completed'])}")

    save_meta(meta)
    print(f"\n{'='*60}")
    print(f"  ✅ 全部完成！")
    print(f"  A: {len(progress_a['completed'])}家 | 发现{progress_a['stats']['found']}条 | 下载{progress_a['stats']['downloaded']}个")
    print(f"  B: {len(progress_b['completed'])}家 | 发现{progress_b['stats']['found']}条 | 下载{progress_b['stats']['downloaded']}个")
    print(f"{'='*60}")


def main():
    mode = 'alternating'
    batch_size = 3
    test = False

    for arg in sys.argv[1:]:
        if arg == '--cninfo-only':
            mode = 'cninfo-only'
        elif arg == '--chinamoney-only':
            mode = 'chinamoney-only'
        elif arg == '--test':
            test = True
        elif arg.startswith('--batch='):
            batch_size = int(arg.split('=', 1)[1])

    asyncio.run(run_ab(mode, batch_size, test))


if __name__ == '__main__':
    main()
