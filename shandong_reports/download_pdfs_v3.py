"""
山东城投PDF批量下载器 v3
=====================
核心思路：直接尝试已知有效的URL模式，不依赖搜索

使用方法：
  python download_pdfs_v3.py           # 尝试下载所有已知公司
  python download_pdfs_v3.py --test    # 只测试前3家
"""

import urllib.request
import ssl
import os
import sys
import json
import re
from datetime import datetime

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

def download_pdf(url, save_path, timeout=30):
    """下载PDF到本地"""
    if os.path.exists(save_path):
        size = os.path.getsize(save_path)
        if size > 10240:  # >10KB
            print(f"  [已存在] {os.path.basename(save_path)} ({size//1024}KB)")
            return True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 10240:  # <10KB，可能是错误页面
                print(f"  [文件过小] {len(data)} bytes - 可能不是PDF")
                return False
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(data)
            print(f"  [成功] {os.path.basename(save_path)} ({len(data)//1024}KB)")
            return True
    except Exception as e:
        print(f"  [失败] {str(e)[:60]}")
        return False


def try_sse_static(company_name, city, bond_keywords):
    """
    尝试上交所static服务器PDF
    URL模式: https://static.sse.com.cn/bond/bridge2/disclosure/announcement/c/{date}/{id}.PDF
    
    已知有效URL（参考）:
    - 湖州城投: https://static.sse.com.cn/bond/bridge2/disclosure/announcement/c/202412/052536_20241217_SPZC.pdf
    """
    print(f"\n  尝试上交所static服务器...")
    
    # 从公司名提取关键词，用于构造搜索
    # 实际使用时需要债券公告ID，这里先尝试已知模式
    
    # 尝试直接访问（需要知道完整的filename）
    # 这里先跳过，因为没有债券代码/公告ID
    print("  [跳过] 需要债券公告ID（请通过企业预警通获取）")
    return False


def try_cninfo_direct(company_name, city):
    """
    尝试从巨潮资讯直接下载
    需要：股票代码或债券代码
    """
    print(f"\n  尝试巨潮资讯...")
    # 巨潮需要股票代码，城投公司大多没有
    print("  [跳过] 巨潮需要股票代码")
    return False


def try_known_urls(company_name, city):
    """
    尝试已知有效的直接PDF URL
    这些URL来自之前的成功案例
    """
    print(f"\n  尝试已知URL模式...")
    
    # 已知有效的URL模式
    known_patterns = [
        # 新浪财经镜像（需要完整的文件ID）
        "http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/BOND/{year}/{date}/{file_id}.PDF",
        # 上交所static（需要公告ID）
        "https://static.sse.com.cn/bond/bridge2/disclosure/announcement/c/{date}/{ann_id}.PDF",
    ]
    
    # 如果没有具体的URL，无法下载
    print("  [需要] 请提供具体的PDF URL")
    return False


def search_and_download_with_browser(company_name, city):
    """
    使用Playwright浏览器搜索并下载PDF
    这个方法实际访问网站，搜索PDF链接
    """
    import asyncio
    from playwright.async_api import async_playwright
    
    print(f"\n  启动浏览器搜索 {company_name}...")
    
    result = False
    
    async def _search():
        nonlocal result
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent=UA,
                viewport={'width': 1280, 'height': 800},
            )
            page = await ctx.new_page()
            
            # 访问上交所债券披露页面
            try:
                await page.goto(
                    'https://www.sse.com.cn/disclosure/bond/',
                    wait_until='domcontentloaded',
                    timeout=20000
                )
                await page.wait_for_timeout(3000)
                
                # 查找搜索框
                search_input = await page.query_selector('input[type="search"], input[placeholder*="搜索"], input[placeholder*="债券"]')
                if search_input:
                    await search_input.click()
                    await search_input.fill(company_name)
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(5000)
                    
                    # 提取PDF链接
                    pdf_links = await page.evaluate("""
                        () => {
                            const links = Array.from(document.querySelectorAll('a[href*=".pdf"], a[href*=".PDF"]'));
                            return links.map(a => ({href: a.href, text: a.textContent.trim()}));
                        }
                    """)
                    
                    if pdf_links:
                        print(f"  找到 {len(pdf_links)} 个PDF链接")
                        # 下载前3个
                        save_dir = os.path.join(RAW_DIR, city, company_name)
                        os.makedirs(save_dir, exist_ok=True)
                        for i, link in enumerate(pdf_links[:3]):
                            url = link['href']
                            fname = url.split('/')[-1] or f"doc_{i}.pdf"
                            save_path = os.path.join(save_dir, fname)
                            if download_pdf(url, save_path):
                                result = True
                    else:
                        print("  未找到PDF链接")
            except Exception as e:
                print(f"  浏览器错误: {e}")
            
            await browser.close()
    
    asyncio.run(_search())
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='只测试前3家')
    parser.add_argument('--company', type=str, help='指定公司名')
    args = parser.parse_args()
    
    sys.path.insert(0, BASE_DIR)
    from shandong_companies import get_shandong_companies
    
    companies = get_shandong_companies()
    
    if args.company:
        companies = [c for c in companies if args.company in c['name']]
        if not companies:
            print(f"未找到公司: {args.company}")
            return
    
    if args.test:
        companies = companies[:3]
    
    print(f"\n{'='*60}")
    print(f"  山东城投PDF下载器 v3")
    print(f"  目标: {len(companies)} 家公司")
    print(f"{'='*60}\n")
    
    success_count = 0
    
    for i, company in enumerate(companies, 1):
        name = company['name']
        city = company['city']
        print(f"[{i}/{len(companies)}] {name[:30]} ({city})")
        
        # 方法1: 尝试已知URL（需要手动提供）
        # try_known_urls(name, city)
        
        # 方法2: 使用浏览器搜索
        if search_and_download_with_browser(name, city):
            success_count += 1
        
        if i % 3 == 0:
            print(f"\n  已处理 {i}/{len(companies)}，成功 {success_count} 家\n")
    
    print(f"\n{'='*60}")
    print(f"  完成！")
    print(f"  总计: {len(companies)} 家，成功: {success_count} 家")
    print(f"  文件保存至: {RAW_DIR}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
