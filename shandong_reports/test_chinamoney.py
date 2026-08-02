"""
测试 chinamoney.com.cn 搜索和下载
使用 Playwright 模拟浏览器操作
"""
import asyncio
import re
import os
import ssl
import urllib.request
import urllib.parse

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
TEST_COMPANY = "青岛城市建设投资"


def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


async def test_chinamoney_search():
    """测试中国货币网搜索功能"""
    from playwright.async_api import async_playwright

    print(f"\n{'='*60}")
    print(f"  测试 chinamoney.com.cn 搜索: {TEST_COMPANY}")
    print(f"{'='*60}")

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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 900},
            locale='zh-CN',
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        )
        page = await ctx.new_page()

        # 设置超时
        page.set_default_timeout(30000)

        # 1. 访问搜索页面
        encoded_kw = urllib.parse.quote(TEST_COMPANY)
        search_url = f"https://www.chinamoney.com.cn/chinese/qwjsn/?searchValue={encoded_kw}"
        print(f"\n[1] 访问: {search_url}")

        try:
            resp = await page.goto(search_url, wait_until='networkidle', timeout=25000)
            print(f"    状态: {resp.status if resp else 'None'}")
        except Exception as e:
            print(f"    访问异常: {e}")
            # 尝试 domcontentloaded
            try:
                await page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
                print("    使用 domcontentloaded 模式加载")
            except Exception as e2:
                print(f"    再次失败: {e2}")
                await browser.close()
                return

        # 等待搜索结果加载
        print("\n[2] 等待搜索结果...")
        await page.wait_for_timeout(5000)

        # 检查页面标题
        title = await page.title()
        print(f"    页面标题: {title}")

        # 2. 提取 filterLevel onclick 中的 contentId
        print("\n[3] 提取搜索结果...")

        # 尝试多种选择器
        result_data = await page.evaluate("""
            () => {
                const results = [];

                // 方法1: 直接找所有 onclick 包含 filterLevel 的元素
                document.querySelectorAll('[onclick*="filterLevel"]').forEach(el => {
                    const onclick = el.getAttribute('onclick') || '';
                    const match = onclick.match(/filterLevel\\s*\\(([^)]+)\\)/);
                    if (match) {
                        const params = match[1].split(',').map(p => p.trim().replace(/['"]/g, ''));
                        results.push({
                            method: 'onclick_filterLevel',
                            params: params,
                            contentId: params[1] || '',
                            title: params[3] || params[4] || el.textContent?.trim() || '',
                            time: params[2] || '',
                        });
                    }
                });

                // 方法2: 找表格中的链接
                document.querySelectorAll('table a, .result-list a, .search-result a').forEach(a => {
                    const onclick = a.getAttribute('onclick') || '';
                    if (onclick.includes('filterLevel')) {
                        const match = onclick.match(/filterLevel\\s*\\(([^)]+)\\)/);
                        if (match) {
                            const params = match[1].split(',').map(p => p.trim().replace(/['"]/g, ''));
                            results.push({
                                method: 'table_onclick',
                                contentId: params[1] || '',
                                title: params[4] || a.textContent?.trim() || '',
                                time: params[2] || '',
                            });
                        }
                    }
                });

                // 方法3: 找所有包含 'PDF' 或 'pdf' 的链接
                document.querySelectorAll('a[href*="PDF"], a[href*="pdf"], a[href*="downLoad"]').forEach(a => {
                    results.push({
                        method: 'pdf_link',
                        href: a.href,
                        text: a.textContent?.trim(),
                    });
                });

                // 方法4: 抓页面HTML片段
                const bodyHTML = document.body.innerHTML;
                const filterMatches = [];
                const regex = /filterLevel\\s*\\([^)]+\\)/g;
                let m;
                while ((m = regex.exec(bodyHTML)) !== null) {
                    filterMatches.push(m[0].slice(0, 300));
                }

                return {
                    onclick_count: document.querySelectorAll('[onclick*="filterLevel"]').length,
                    pdf_link_count: document.querySelectorAll('a[href*="PDF"], a[href*="pdf"]').length,
                    filter_match_count: filterMatches.length,
                    filter_matches: filterMatches.slice(0, 5),
                    results: results.slice(0, 20),
                };
            }
        """)

        print(f"    onclick(filterLevel) 数量: {result_data['onclick_count']}")
        print(f"    PDF链接数量: {result_data['pdf_link_count']}")
        print(f"    filterLevel匹配数: {result_data['filter_match_count']}")

        if result_data['filter_matches']:
            print("\n    示例 filterLevel onclick:")
            for i, m in enumerate(result_data['filter_matches'][:3]):
                print(f"    [{i+1}] {m[:200]}")

        if result_data['results']:
            print(f"\n    解析出的结果 ({len(result_data['results'])}条):")
            for r in result_data['results'][:5]:
                print(f"    - [{r.get('method')}] contentId={r.get('contentId','')[:20]} | {r.get('title','')[:50]}")

        # 3. 如果找到 contentId，尝试构造下载URL
        if result_data['results']:
            first = result_data['results'][0]
            content_id = first.get('contentId', '')
            if content_id:
                download_url = f"https://www.chinamoney.com.cn/ags/cm-s-security/fileDownLoad.do?mode=open&contentId={content_id}&priority=0"
                print(f"\n[4] 构造下载URL: {download_url}")

                # 测试能否直接下载
                UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                req = urllib.request.Request(download_url, headers={"User-Agent": UA, "Referer": "https://www.chinamoney.com.cn/"})
                SSL_CTX = ssl.create_default_context()
                SSL_CTX.check_hostname = False
                SSL_CTX.verify_mode = ssl.CERT_NONE

                try:
                    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp2:
                        data = resp2.read()
                        ct = resp2.headers.get('Content-Type', '')
                        cd = resp2.headers.get('Content-Disposition', '')
                        print(f"    下载响应: {resp2.status}, size={len(data)/1024:.1f}KB, type={ct[:30]}")
                        print(f"    Content-Disposition: {cd[:80]}")

                        # 如果是PDF，保存测试
                        if ct.startswith('application/pdf') or '.pdf' in cd.lower():
                            test_file = os.path.join(BASE_DIR, "test_download.pdf")
                            with open(test_file, 'wb') as f:
                                f.write(data)
                            print(f"    ✅ PDF已保存: {test_file}")
                        else:
                            # 打印前200字节
                            print(f"    前200字节: {data[:200]}")
                except Exception as e:
                    print(f"    下载失败: {e}")

        # 4. 保存完整页面HTML用于分析
        html = await page.content()
        debug_file = os.path.join(BASE_DIR, "chinamoney_debug.html")
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n[5] 页面HTML已保存: {debug_file} ({len(html)/1024:.0f}KB)")

        await browser.close()


async def main():
    await test_chinamoney_search()


if __name__ == '__main__':
    asyncio.run(main())
