"""
chinamoney.com.cn 债券文档采集器
基于前期逆向发现的 filterLevel onclick 结构编写
网站恢复后即可运行

数据结构（每个contentId对应2个onclick）：
  filterLevel(level, contentId, channel, scid, title, ctime, isOpen, url)
  其中 isOpen=true 的条目带有 dealPath 直接下载URL

采集流程：
  1. 搜索 /chinese/qwjsn/?searchValue=关键词
  2. 提取所有 filterLevel onclick
  3. 按 contentId 分组，取 isOpen=true 的条目
  4. 直接下载 dealPath URL（需携带Referer和User-Agent）
"""

import asyncio
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from playwright.async_api import async_playwright

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw")

sys.path.insert(0, os.path.dirname(__file__))
from shandong_companies import get_shandong_companies

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER = "https://www.chinamoney.com.cn/chinese/qwjsn/"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)[:50].strip()


def parse_filterLevel_params(onclick_str):
    """解析 filterLevel('1','3336500','cwbg',null,null,null,true,'url') 参数"""
    match = re.search(r'filterLevel\s*\(([^)]+)\)', onclick_str)
    if not match:
        return None

    params_str = match[1]
    parts = []
    current = ''
    in_quote = False
    quote_char = ''

    for c in params_str:
        if not in_quote and c in "'\"":
            in_quote = True
            quote_char = c
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
        'level': clean[0],
        'contentId': clean[1],
        'channel': clean[2],
        'scid': clean[3],
        'title': clean[4],
        'ctime': clean[5],
        'isOpen': clean[6] == 'true',
        'url': clean[7],
    }


def load_progress():
    progress_file = os.path.join(BASE_DIR, "collection_progress_chinamoney.json")
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "stats": {"searched": 0, "found": 0, "downloaded": 0}}


def save_progress(progress):
    progress_file = os.path.join(BASE_DIR, "collection_progress_chinamoney.json")
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def download_file(url, save_path, headers=None):
    """直接下载文件，返回 (success, content_type, size_bytes)"""
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        return True, 'cached', os.path.getsize(save_path)

    h = {
        "User-Agent": UA,
        "Referer": REFERER,
        "Accept": "application/pdf,application/octet-stream,*/*",
    }
    if headers:
        h.update(headers)

    req = urllib.request.Request(url, headers=h)

    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = resp.read()
            ct = resp.headers.get('Content-Type', '')
            size = len(data)

            # 检测是否被重定向到维护页面
            if 'text/html' in ct and size < 50000:
                text = data.decode('utf-8', errors='replace')[:500]
                if '维护' in text or 'maintenance' in text.lower():
                    return False, 'maintenance', size

            with open(save_path, 'wb') as f:
                f.write(data)
            return True, ct, size
    except Exception as e:
        return False, str(e), 0


async def search_chinamoney(company_name, page):
    """
    在 chinamoney 搜索关键词，返回提取的文档列表
    page: 已初始化的 Playwright 页面对象
    """
    encoded_kw = urllib.parse.quote(company_name)
    search_url = f"https://www.chinamoney.com.cn/chinese/qwjsn/?searchValue={encoded_kw}"

    print(f"  [搜索] {search_url[:80]}")

    try:
        resp = await page.goto(search_url, wait_until='networkidle', timeout=25000)
        status = resp.status if resp else None
    except Exception:
        try:
            resp = await page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
            status = resp.status if resp else None
        except Exception as e:
            print(f"  页面加载失败: {e}")
            return []

    await page.wait_for_timeout(4000)

    title = await page.title()
    if '维护' in title:
        print(f"  ⚠️ 网站维护中，无法搜索")
        return []

    # 提取所有 filterLevel onclick
    results = await page.evaluate("""
        () => {
            const items = [];
            const seen = new Set();

            document.querySelectorAll('[onclick*="filterLevel"]').forEach(el => {
                const onclick = el.getAttribute('onclick') || '';
                // 获取文本用于标题
                let text = '';
                const row = el.closest('tr') || el.closest('.result-item') || el.closest('li');
                if (row) {
                    text = row.textContent || '';
                } else {
                    text = el.textContent || '';
                }

                const match = onclick.match(/filterLevel\\s*\\(([^)]+)\\)/);
                if (match) {
                    const raw = match[0];
                    // 避免重复contentId
                    const cidMatch = raw.match(/'([^']+)'/);
                    // 找第2个引号包裹的值作为contentId
                    const allQuoted = [...raw.matchAll(/'([^']*)'/g)].map(m => m[1]);
                    const cid = allQuoted[1] || '';
                    if (cid && !seen.has(cid + '_' + allQuoted[6])) {
                        seen.add(cid + '_' + allQuoted[6]);
                        items.push({
                            onclick: onclick,
                            text: text.trim().slice(0, 200),
                        });
                    }
                }
            });

            return items;
        }
    """)

    # 解析为结构化数据
    documents = {}
    for item in results:
        parsed = parse_filterLevel_params(item['onclick'])
        if not parsed:
            continue

        cid = parsed['contentId']
        if parsed['isOpen']:
            documents[cid] = {
                'contentId': cid,
                'channel': parsed['channel'],
                'title': parsed['title'] or item['text'][:80],
                'url': parsed['url'],
                'ctime': parsed['ctime'],
            }

    return list(documents.values())


async def collect_company(company_name, city, page, progress):
    """采集单家公司在 chinamoney 的债券文档"""
    safe_city = city.replace("/", "_")
    safe_name = safe_filename(company_name)
    out_dir = os.path.join(RAW_DIR, safe_city, safe_name)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  [{city}] {company_name}")
    print(f"{'='*60}")

    docs = await search_chinamoney(company_name, page)
    print(f"  发现 {len(docs)} 个可下载文档")

    downloaded = 0
    for i, doc in enumerate(docs[:5]):  # 每家最多下5个
        url = doc.get('url', '')
        cid = doc.get('contentId', '')
        if not url or not url.startswith('http'):
            continue

        # 确定文件扩展名
        if '.pdf' in url.lower():
            ext = '.pdf'
        else:
            ext = '.pdf'

        fname = f"{safe_name}_{cid}{ext}"
        save_path = os.path.join(out_dir, fname)

        print(f"  [{i+1}] 下载 {cid} -> {fname}")
        ok, ct, size = download_file(url, save_path)

        if ok:
            downloaded += 1
            print(f"      ✅ {size/1024:.1f}KB ({ct[:30]})")
        else:
            print(f"      ❌ {ct}")

    # 保存搜索记录
    meta_file = os.path.join(out_dir, "_chinamoney_meta.json")
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump({
            'company': company_name,
            'city': city,
            'search_time': datetime.now().isoformat(),
            'documents': docs,
            'downloaded': downloaded,
        }, f, ensure_ascii=False, indent=2)

    # 更新进度
    progress["completed"].append({
        'name': company_name,
        'city': city,
        'time': datetime.now().isoformat(),
        'found': len(docs),
        'downloaded': downloaded,
    })
    progress["stats"]["searched"] += 1
    progress["stats"]["found"] += len(docs)
    progress["stats"]["downloaded"] += downloaded
    save_progress(progress)

    return len(docs), downloaded


async def main():
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
        companies = companies[:2]

    completed_names = {c["name"] for c in progress["completed"]}
    companies = [c for c in companies if c["name"] not in completed_names]

    print(f"\n{'#'*60}")
    print(f"  chinamoney.com.cn 债券文档采集器")
    print(f"  目标: {len(companies)}家  已跳过: {len(completed_names)}家")
    print(f"  模式: {'测试' if test_mode else '全量'}")
    print(f"{'#'*60}")

    if not companies:
        print("  所有公司已采集完成！")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={'width': 1280, 'height': 900},
            locale='zh-CN',
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        )
        page = await ctx.new_page()
        page.set_default_timeout(30000)

        for i, company in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}] {company['name']}")
            try:
                await collect_company(company["name"], company["city"], page, progress)
            except Exception as e:
                print(f"  [ERROR] {e}")
            await asyncio.sleep(1)

        await browser.close()

    print(f"\n{'#'*60}")
    print(f"  完成！")
    print(f"  累计: 搜索{progress['stats']['searched']}家 | 发现{progress['stats']['found']}条 | 下载{progress['stats']['downloaded']}个")
    print(f"{'#'*60}")


if __name__ == '__main__':
    asyncio.run(main())
