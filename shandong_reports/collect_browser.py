"""
山东城投债券采集 - Playwright浏览器版
使用Playwright直接搜索各平台，提取PDF链接
"""
import asyncio
import json
import re
import os
import sys
import time
from datetime import datetime

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw")

sys.path.insert(0, os.path.dirname(__file__))
from shandong_companies import get_shandong_companies

def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()

def ts_to_date(ts):
    try:
        ts = int(str(ts)[:10])
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except:
        return ''

async def search_on_page(page, url, keyword, wait_time=5):
    """
    在给定页面搜索关键词，等待结果加载
    返回页面内容（用于后续解析）
    """
    try:
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(wait_time * 1000)
        html = await page.content()
        return html, resp.status if resp else None
    except Exception as e:
        return None, str(e)


async def search_cninfo_bond(keyword):
    """
    巨潮资讯 - 债券公告搜索
    搜索: https://www.cninfo.com.cn/new/fulltextSearch/full
    """
    import urllib.parse
    params = urllib.parse.urlencode({
        'searchkey': keyword,
        'sdate': '2020-01-01',
        'edate': datetime.now().strftime('%Y-%m-%d'),
        'isfulltext': 'false',
        'sortName': 'nothing',
        'sortType': 'desc',
        'pageNum': 1,
        'pageSize': 20,
    })
    url = f'https://www.cninfo.com.cn/new/fulltextSearch/full?{params}'

    results = []
    async with asyncio.Lock():
        pass  # 不需要锁

    async def _search_cninfo():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800},
                locale='zh-CN',
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(6000)

            # 提取结果
            data = await page.evaluate(r"""
                () => {
                    const els = document.querySelectorAll('[ref="e2"]');
                    for (const el of els) {
                        const text = el.textContent || '';
                        if (text.includes('announcements') && text.includes('totalRecordNum')) {
                            try { return JSON.parse(text); } catch(e) {}
                        }
                    }
                    const body = document.body.innerHTML;
                    const idx = body.indexOf('totalRecordNum');
                    if (idx >= 0) {
                        const start = Math.max(0, idx - 200);
                        const snippet = body.slice(start, idx + 2000);
                        const m = snippet.match(/"announcements"\s*:\s*\[(.*?)\]\s*,\s*"categoryList"/);
                        if (m) {
                            try { return {announcements: JSON.parse('[' + m[1] + ']')}; } catch(e) {}
                        }
                    }
                    return null;
                }
            """)

            if data:
                for item in data.get('announcements') or []:
                    ts = item.get('announcementTime', 0)
                    results.append({
                        'title': strip_html(item.get('announcementTitle', '')),
                        'date': ts_to_date(ts),
                        'ann_id': item.get('announcementId', ''),
                        'pdf_url': 'https://static.cninfo.com.cn/' + item.get('adjunctUrl', ''),
                        'source': 'cninfo',
                    })

            await browser.close()

    await _search_cninfo()

    return results


async def search_em_bonds(keyword):
    """
    东方财富债券搜索
    使用东方财富债券搜索API（通过浏览器访问搜索页）
    """
    import urllib.parse
    encoded_kw = urllib.parse.quote(keyword)
    # 东方财富债券搜索结果页
    search_url = f'https://data.eastmoney.com/notices/?keyword={encoded_kw}'

    results = []
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )
        page = await ctx.new_page()

        # 拦截JSON响应
        json_responses = []

        async def handle_response(resp):
            if resp.ok and 'json' in (resp.headers.get('content-type') or ''):
                url = resp.url
                if 'notice' in url.lower() or 'ann' in url.lower():
                    try:
                        data = await resp.json()
                        json_responses.append({'url': url[:60], 'data': data})
                    except:
                        pass

        page.on('response', handle_response)
        try:
            await page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
        except Exception as e:
            print(f"       goto error: {e}")
        await page.wait_for_timeout(4000)

        for r in json_responses:
            d = r['data']
            items = None
            if isinstance(d, dict):
                items = d.get('data') or d.get('list') or (d.get('result') or {}).get('list') or []
            if isinstance(items, list):
                for item in items[:10]:
                    art_code = item.get('art_code') or item.get('noticeId') or item.get('id', '')
                    title = item.get('title') or item.get('title_ch') or item.get('noticeTitle', '')
                    notice_date = item.get('notice_date') or item.get('publishTime') or ''
                    if isinstance(notice_date, int):
                        notice_date = ts_to_date(notice_date)
                    url = f'https://data.eastmoney.com/notices/detail/{str(art_code)[:10]}/{art_code}.html'
                    results.append({
                        'title': strip_html(title),
                        'date': str(notice_date)[:10],
                        'art_id': art_code,
                        'detail_url': url,
                        'source': 'eastmoney',
                    })

        await browser.close()

    return results


async def search_shclearing(keyword):
    """
    上海清算所债券搜索
    https://www.shclearing.com.cn/xxpl/fxpl/GN_1/
    """
    import urllib.parse
    encoded_kw = urllib.parse.quote(keyword)
    search_url = f'https://www.shclearing.com.cn/xxpl/fxpl/GN_1/?keyword={encoded_kw}'

    results = []
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )
        page = await ctx.new_page()

        try:
            await page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
        except Exception as e:
            print(f"       goto error: {e}")
        await page.wait_for_timeout(4000)

        # 提取结果链接
        links = await page.evaluate("""
            () => {
                const results = [];
                // 找所有指向PDF的链接
                document.querySelectorAll('a[href*=".PDF"], a[href*=".pdf"]').forEach(a => {
                    results.push({
                        title: a.textContent.trim(),
                        href: a.href,
                    });
                });
                // 找表格行
                document.querySelectorAll('table tr, .list-item, .ann-item').forEach(row => {
                    const a = row.querySelector('a');
                    if (a && (a.href.includes('.PDF') || a.textContent.includes('募集'))) {
                        results.push({
                            title: row.textContent.trim().slice(0, 100),
                            href: a.href,
                        });
                    }
                });
                return results;
            }
        """)
        for link in links[:10]:
            results.append({
                'title': link.get('title', '')[:100],
                'pdf_url': link.get('href', ''),
                'source': 'shclearing',
            })

        await browser.close()

    return results


async def collect_company_browser(company_name, city, progress):
    """使用浏览器采集单家公司"""
    safe_city = city.replace("/", "_")
    safe_name = re.sub(r'[\\/:*?"<>|]', '', company_name)[:30]
    out_dir = os.path.join(RAW_DIR, safe_city, safe_name)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  [{city}] {company_name}")
    print(f"{'='*50}")

    all_results = []
    downloaded = 0

    # 并行搜索三个平台（使用gather）
    print("  [1/3] 巨潮资讯...")
    cninfo_results = await search_cninfo_bond(company_name)
    print(f"       找到 {len(cninfo_results)} 条")
    for r in cninfo_results[:3]:
        print(f"       - [{r['date']}] {r['title'][:50]}")

    print("  [2/3] 东方财富...")
    em_results = await search_em_bonds(company_name)
    print(f"       找到 {len(em_results)} 条")
    for r in em_results[:3]:
        print(f"       - [{r['date']}] {r['title'][:50]}")

    print("  [3/3] 上海清算所...")
    shc_results = await search_shclearing(company_name)
    print(f"       找到 {len(shc_results)} 条")

    all_results = cninfo_results + em_results + shc_results

    # 下载PDF
    if all_results:
        print(f"\n  下载PDF...")
        for i, r in enumerate(all_results[:5]):  # 最多下前5个
            url = r.get('pdf_url') or r.get('detail_url', '')
            if url and (url.endswith('.pdf') or url.endswith('.PDF') or '/notices/detail/' in url):
                fname = f"{r['date'].replace('-','')}_{safe_name}_{r.get('art_id', r.get('ann_id', f'n{i}'))[:8]}.pdf"
                if r.get('detail_url'):
                    # EM详情页 -> 需要从页面提取PDF
                    pass
                else:
                    ok = await download_pdf_async(url, os.path.join(out_dir, fname))
                    if ok:
                        downloaded += 1

    # 保存结果
    out_file = os.path.join(out_dir, "_search_result.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            "company": company_name,
            "city": city,
            "search_time": datetime.now().isoformat(),
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  已保存: {out_file}")

    # 更新进度
    progress["completed"].append({
        "name": company_name,
        "city": city,
        "time": datetime.now().isoformat(),
        "found": len(all_results),
        "downloaded": downloaded,
    })
    progress_save_browser(progress)

    return all_results


def progress_save_browser(p):
    with open(os.path.join(BASE_DIR, "collection_progress_browser.json"), 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


async def download_pdf_async(url, save_path):
    """异步下载PDF"""
    import urllib.request
    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        print(f"  [EXISTS] {os.path.basename(save_path)}")
        return True

    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = resp.read()
            with open(save_path, "wb") as f:
                f.write(data)
            size = len(data) / 1024
            print(f"  [OK] {os.path.basename(save_path)} ({size:.0f}KB)")
            return True
    except Exception as e:
        print(f"  [FAIL] {os.path.basename(save_path)}: {e}")
        return False


async def main():
    test_mode = '--test' in sys.argv
    single_company = None
    city_filter = None

    for arg in sys.argv[1:]:
        if arg.startswith('--company='):
            single_company = arg.split('=', 1)[1]
        elif arg.startswith('--city='):
            city_filter = arg.split('=', 1)[1]

    progress_file = os.path.join(BASE_DIR, "collection_progress_browser.json")
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {"completed": [], "stats": {"searched": 0, "found": 0, "downloaded": 0}}

    companies = get_shandong_companies()
    if single_company:
        companies = [c for c in companies if single_company in c["name"]]
    elif city_filter:
        companies = [c for c in companies if city_filter in c["city"]]
    elif test_mode:
        companies = companies[:3]

    completed_names = {c["name"] for c in progress["completed"]}
    companies = [c for c in companies if c["name"] not in completed_names]

    print(f"\n{'#'*55}")
    print(f"  山东城投债券采集 - Playwright浏览器版")
    print(f"  目标: {len(companies)}家  跳过: {len(completed_names)}家")
    print(f"  模式: {'测试' if test_mode else '全量'}")
    print(f"{'#'*55}")

    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}]")
        try:
            await collect_company_browser(company["name"], company["city"], progress)
        except Exception as e:
            print(f"  [ERROR] {e}")
        await asyncio.sleep(1)  # 礼貌延迟

    print(f"\n\n{'#'*55}")
    print(f"  完成！")
    print(f"  累计: 搜索{progress['stats']['searched']}家 | 发现{progress['stats']['found']}条 | 下载{progress['stats']['downloaded']}个")
    print(f"{'#'*55}")


if __name__ == '__main__':
    asyncio.run(main())
