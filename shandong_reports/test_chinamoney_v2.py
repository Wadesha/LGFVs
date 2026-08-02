"""
测试 chinamoney.com.cn checkMessage API 和文件下载
"""
import asyncio
import ssl
import urllib.request
import json

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"

# 已知的 contentId 列表（从测试中提取）
TEST_CONTENT_IDS = ["3336500", "3336630", "3314968"]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def test_check_message_api(content_id):
    """测试 checkMessage API"""
    url = "https://www.chinamoney.com.cn/ags/ms/cm-u-notice-issue/cm-s-security/checkMessage"
    data = json.dumps({"ctnId": content_id}).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.chinamoney.com.cn/chinese/qwjsn/",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.chinamoney.com.cn",
    })

    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            result = resp.read().decode('utf-8')
            print(f"\n[checkMessage] contentId={content_id}")
            print(f"  响应: {result[:500]}")
            return result
    except Exception as e:
        print(f"\n[checkMessage] contentId={content_id}")
        print(f"  错误: {e}")
        return None


def test_direct_download(content_id, ut=None, sign=None):
    """测试直接下载URL"""
    url = f"https://www.chinamoney.com.cn/ags/cm-s-security/fileDownLoad.do?mode=open&contentId={content_id}&priority=0"
    if ut and sign:
        url += f"&ut={ut}&sign={sign}"

    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://www.chinamoney.com.cn/chinese/qwjsn/",
    })

    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as resp:
            data = resp.read()
            ct = resp.headers.get('Content-Type', '')
            cd = resp.headers.get('Content-Disposition', '')
            print(f"\n[下载] contentId={content_id}")
            print(f"  URL: {url[:100]}")
            print(f"  状态: {resp.status}, 大小: {len(data)/1024:.1f}KB")
            print(f"  Content-Type: {ct}")
            print(f"  Content-Disposition: {cd[:80]}")

            # 保存PDF
            if 'pdf' in ct.lower() or '.pdf' in cd.lower():
                fname = f"test_{content_id}.pdf"
                with open(f"{BASE_DIR}/{fname}", 'wb') as f:
                    f.write(data)
                print(f"  ✅ 保存: {fname}")
            return data
    except Exception as e:
        print(f"\n[下载] contentId={content_id}")
        print(f"  错误: {e}")
        return None


async def test_browser_download():
    """使用Playwright测试下载（带完整session）"""
    from playwright.async_api import async_playwright

    print(f"\n{'='*60}")
    print(f"  Playwright 浏览器内下载测试")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={'width': 1280, 'height': 900},
            locale='zh-CN',
        )
        page = await ctx.new_page()
        page.set_default_timeout(30000)

        # 先访问主页获取cookie
        print("\n[1] 访问主页获取cookie...")
        await page.goto("https://www.chinamoney.com.cn/chinese/", wait_until='networkidle', timeout=20000)
        await page.wait_for_timeout(2000)

        # 访问搜索页
        print("[2] 访问搜索页...")
        await page.goto(
            "https://www.chinamoney.com.cn/chinese/qwjsn/?searchValue=青岛城市建设投资",
            wait_until='networkidle',
            timeout=20000
        )
        await page.wait_for_timeout(3000)

        # 获取 cookies
        cookies = await ctx.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print(f"    Cookies数量: {len(cookies)}")
        print(f"    Cookie字符串前100字符: {cookie_str[:100]}")

        # 提取第一个 contentId
        first_content_id = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[onclick*="filterLevel"]');
                if (els.length > 0) {
                    const onclick = els[0].getAttribute('onclick') || '';
                    const match = onclick.match(/filterLevel\\s*\\([^)]+\\)/);
                    if (match) {
                        const params = match[0].match(/'([^']+)'/g) || [];
                        return params.map(p => p.replace(/'/g, ''));
                    }
                }
                return null;
            }
        """)

        if first_content_id:
            print(f"\n[3] 提取到内容: {first_content_id}")
            content_id = first_content_id[1] if len(first_content_id) > 1 else None
            is_open = first_content_id[6] if len(first_content_id) > 6 else None
            direct_url = first_content_id[7] if len(first_content_id) > 7 else None

            print(f"    contentId: {content_id}")
            print(f"    isOpen: {is_open}")
            print(f"    directURL: {direct_url}")

            # 尝试直接访问 directURL
            if direct_url and direct_url.startswith('http'):
                print(f"\n[4] 尝试直接URL下载...")
                try:
                    resp = await page.goto(direct_url, timeout=15000)
                    print(f"    状态: {resp.status if resp else 'None'}")
                except Exception as e:
                    print(f"    错误: {e}")

            # 尝试调用 checkMessage API 并下载
            if content_id:
                print(f"\n[5] 调用 checkMessage API...")
                api_result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const resp = await fetch('https://www.chinamoney.com.cn/ags/ms/cm-u-notice-issue/cm-s-security/checkMessage', {{
                                method: 'POST',
                                body: JSON.stringify({{ ctnId: '{content_id}' }}),
                                headers: {{
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json',
                                    'Referer': 'https://www.chinamoney.com.cn/chinese/qwjsn/',
                                    'Origin': 'https://www.chinamoney.com.cn',
                                }}
                            }});
                            return await resp.json();
                        }} catch(e) {{
                            return {{ error: e.message }};
                        }}
                    }}
                """)
                print(f"    API结果: {api_result}")

                if isinstance(api_result, dict) and 'data' in api_result:
                    path_val = api_result['data'].get('result') or api_result['data'].get('path') or ''
                    if path_val:
                        download_url = f"https://www.chinamoney.com.cn/ags/cm-s-security/{path_val}" if not path_val.startswith('http') else path_val
                        print(f"    下载路径: {download_url}")

        # 保存截图用于调试
        screenshot_path = f"{BASE_DIR}/chinamoney_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n[6] 截图已保存: {screenshot_path}")

        await browser.close()


async def main():
    print("=" * 60)
    print("  chinamoney.com.cn API 测试")
    print("=" * 60)

    # 测试 checkMessage API（直接HTTP）
    print("\n--- 直接HTTP API测试 ---")
    for cid in TEST_CONTENT_IDS[:1]:
        test_check_message_api(cid)

    # 测试直接下载（无认证）
    print("\n--- 直接下载测试 ---")
    for cid in TEST_CONTENT_IDS[:2]:
        test_direct_download(cid)

    # Playwright 浏览器内测试
    print("\n--- Playwright 浏览器内测试 ---")
    await test_browser_download()


if __name__ == '__main__':
    asyncio.run(main())
