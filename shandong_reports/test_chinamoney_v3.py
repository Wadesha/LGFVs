"""
测试 chinamoney.com.cn 的 dealPath 直接下载链接
从 filterLevel onclick 中提取的URL格式：
https://www.chinamoney.com.cn/dqs/rest/cm-s-security/dealPath?path=...
"""
import asyncio
import ssl
import urllib.request
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


async def extract_and_test_dealpaths():
    """提取所有dealPath链接并逐一测试"""
    print(f"\n{'='*60}")
    print(f"  提取并测试 dealPath 链接")
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

        # 访问搜索页面
        url = "https://www.chinamoney.com.cn/chinese/qwjsn/?searchValue=青岛城市建设投资"
        print(f"\n[1] 访问: {url}")

        try:
            resp = await page.goto(url, wait_until='networkidle', timeout=25000)
            status = resp.status if resp else None
            print(f"    状态码: {status}")
        except Exception as e:
            # 可能是maintenance，试试domcontentloaded
            print(f"    networkidle失败({e})，尝试domcontentloaded...")
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(5000)
            status = await page.evaluate("() => document.title")

        title = await page.title()
        print(f"    页面标题: {title}")

        # 如果显示维护页面，直接退出
        if '维护' in title:
            print("\n❌ 网站正在维护，无法继续测试")
            await browser.close()
            return

        # 提取所有filterLevel的完整参数（包括第8个参数directURL）
        all_links = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();

                document.querySelectorAll('[onclick*="filterLevel"]').forEach(el => {
                    const onclick = el.getAttribute('onclick') || '';
                    // 提取完整的 filterLevel(...) 参数
                    const match = onclick.match(/filterLevel\\s*\\(([^)]+)\\)/);
                    if (match) {
                        const paramsStr = match[1];
                        // 按逗号分割，注意字符串内的逗号和引号
                        const params = [];
                        let current = '';
                        let inString = false;
                        let quoteChar = '';

                        for (let i = 0; i < paramsStr.length; i++) {
                            const c = paramsStr[i];
                            if (!inString && (c === '"' || c === "'")) {
                                inString = true;
                                quoteChar = c;
                                current += c;
                            } else if (inString && c === quoteChar) {
                                inString = false;
                                current += c;
                            } else if (!inString && c === ',') {
                                params.push(current.trim());
                                current = '';
                            } else {
                                current += c;
                            }
                        }
                        params.push(current.trim());

                        // 去掉首尾引号
                        const cleanParams = params.map(p => {
                            return p.replace(/^["']|["']$/g, '');
                        });

                        const contentId = cleanParams[1];
                        if (contentId && !seen.has(contentId)) {
                            seen.add(contentId);
                            results.push({
                                contentId: contentId,
                                channel: cleanParams[2] || '',
                                isOpen: cleanParams[6],
                                directUrl: cleanParams[7] || '',
                                text: el.textContent?.trim().slice(0, 80),
                            });
                        }
                    }
                });

                return results;
            }
        """)

        print(f"\n[2] 找到 {len(all_links)} 个唯一 contentId")

        # 显示前几个链接详情
        for i, link in enumerate(all_links[:8]):
            cid = link['contentId']
            ch = link['channel']
            io = link['isOpen']
            du = (link['directUrl'] or '')[:80]
            txt = link['text']
            print(f"\n  [{i+1}] contentId={cid} | channel={ch} | isOpen={io}")
            print(f"      text: {txt}")
            print(f"      directURL: {du}")

        # 测试 dealPath 直接下载
        print(f"\n{'='*60}")
        print(f"[3] 测试 dealPath 直接下载...")
        print(f"{'='*60}")

        SSL_CTX = ssl.create_default_context()
        SSL_CTX.check_hostname = False
        SSL_CTX.verify_mode = ssl.CERT_NONE

        for i, link in enumerate(all_links):
            direct_url = link.get('directUrl')
            cid = link['contentId']

            if not direct_url.startswith('http'):
                continue

            print(f"\n  [{i+1}] contentId={cid}")
            print(f"       URL: {direct_url[:100]}...")

            try:
                req = urllib.request.Request(direct_url, headers={
                    "User-Agent": UA,
                    "Referer": "https://www.chinamoney.com.cn/chinese/qwjsn/",
                    "Accept": "*/*",
                })
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
                    data = resp.read()
                    ct = resp.headers.get('Content-Type', '')
                    cd = resp.headers.get('Content-Disposition', '')
                    size_kb = len(data) / 1024

                    print(f"       状态: {resp.status}, 大小: {size_kb:.1f}KB, 类型: {ct[:40]}")

                    if cd:
                        print(f"       CD: {cd[:80]}")

                    # 判断是否为有效文件
                    is_pdf = 'pdf' in ct.lower() or '.pdf' in cd.lower()
                    is_html = 'text/html' in ct

                    if is_html and size_kb < 50:
                        # 小HTML可能是错误页或维护页
                        preview = data.decode('utf-8', errors='replace')[:150]
                        print(f"       内容预览: {preview}")
                    elif is_pdf:
                        print(f"       ✅ 有效PDF! ({size_kb:.1f}KB)")
                        save_path = f"C:/Users/wade/OneDrive/claw/城投/shandong_reports/test_{cid}.pdf"
                        with open(save_path, 'wb') as f:
                            f.write(data)
                        print(f"       已保存: {save_path}")
                    else:
                        # 其他类型文件
                        ext = ''
                        if cd:
                            import re as _re
                            m = _re.search(r'\.(pdf|doc|docx|xls|xlsx|rar|zip)', cd.lower())
                            if m:
                                ext = f".{m.group(1)}"
                        print(f"       文件类型未知, Content-Type={ct}, 大小={size_kb:.1f}KB")
                        save_path = f"C:/Users/wade/OneDrive/claw/城投/shandong_reports/test_{cid}{ext}"
                        with open(save_path, 'wb') as f:
                            f.write(data)
                        print(f"       已保存: {save_path}")

            except Exception as e:
                print(f"       ❌ 错误: {e}")

            # 只测试前3个有directUrl的结果
            if i >= 6:
                break

        await browser.close()


async def main():
    await extract_and_test_dealpaths()


if __name__ == '__main__':
    asyncio.run(main())
