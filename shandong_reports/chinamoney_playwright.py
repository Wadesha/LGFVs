#!/usr/bin/env python3
"""
中国货币网(chinamoney.com.cn)债券披露文件批量下载脚本 - Playwright版本
无需登录，免费获取银行间市场债券披露文件

用法:
    python chinamoney_playwright.py --keyword "山东城资" --output ./downloads
    python chinamoney_playwright.py --keyword "山东高速" --output ./downloads
"""

import argparse
import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


class ChinamoneyPlaywrightScraper:
    """中国货币网债券披露文件爬虫 - Playwright版本"""
    
    BASE_URL = "https://www.chinamoney.com.cn"
    
    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def search_and_download(self, keyword: str) -> dict:
        """
        搜索并下载债券披露文件
        
        Args:
            keyword: 搜索关键词，如"山东城资"
            
        Returns:
            统计信息
        """
        print(f"正在搜索: {keyword}")
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # 访问首页
                print("访问首页...")
                page.goto(f"{self.BASE_URL}/chinese/", wait_until="networkidle", timeout=30000)
                
                # 等待搜索框加载
                print("等待搜索框...")
                page.wait_for_selector("input[placeholder*='请输入债券名称']", timeout=10000)
                
                # 输入搜索关键词
                print(f"输入关键词: {keyword}")
                page.fill("input[placeholder*='请输入债券名称']", keyword)
                
                # 按回车搜索
                print("执行搜索...")
                page.press("input[placeholder*='请输入债券名称']", "Enter")
                
                # 等待新页面打开
                print("等待搜索结果页面...")
                page.wait_for_timeout(5000)
                
                # 检查是否有新页面打开
                pages = context.pages
                if len(pages) > 1:
                    print(f"检测到 {len(pages)} 个页面，切换到新页面")
                    page = pages[-1]
                    page.wait_for_load_state("networkidle")
                else:
                    print("未检测到新页面，当前页面可能已跳转")
                    page.wait_for_load_state("networkidle")
                
                # 检查是否有结果
                if page.locator("text=暂无数据").count() > 0:
                    print("暂无数据")
                    return {"total": 0, "success": 0, "failed": 0}
                
                # 等待搜索结果加载
                print("等待搜索结果加载...")
                page.wait_for_timeout(5000)
                
                # 保存页面截图和HTML用于调试
                page.screenshot(path="debug_screenshot.png")
                page.content()
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("已保存调试信息: debug_screenshot.png, debug_page.html")
                
                # 获取所有下载链接 (通过img的title属性)
                print("获取下载链接...")
                download_links = page.locator("img[title='点击下载']").all()
                print(f"找到 {len(download_links)} 个下载链接")
                
                if not download_links:
                    print("未找到下载链接")
                    return {"total": 0, "success": 0, "failed": 0}
                
                # 获取所有标题和日期
                titles = []
                dates = []
                
                # 获取列表项
                list_items = page.locator("li:has(img[title='点击下载'])").all()
                for item in list_items:
                    try:
                        # 获取日期
                        date_elem = item.locator("span.text-date, .text-date span").first
                        date = date_elem.inner_text().strip() if date_elem.count() > 0 else ""
                        dates.append(date)
                        
                        # 获取标题 (第一个a标签)
                        title_elem = item.locator("a").first
                        title = title_elem.inner_text().strip() if title_elem.count() > 0 else ""
                        # 移除HTML标签
                        title = re.sub(r'<[^>]+>', '', title)
                        titles.append(title)
                    except Exception as e:
                        print(f"解析条目失败: {e}")
                        titles.append("")
                        dates.append("")
                
                # 下载文件
                stats = {"total": len(download_links), "success": 0, "failed": 0}
                
                for i, link in enumerate(download_links):
                    try:
                        title = titles[i] if i < len(titles) else f"file_{i}"
                        date = dates[i] if i < len(dates) else ""
                        
                        # 构造文件名
                        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
                        if date:
                            filename = f"{date}_{safe_title}.pdf"
                        else:
                            filename = f"{safe_title}.pdf"
                        
                        filepath = self.output_dir / filename
                        
                        print(f"[{i+1}/{len(download_links)}] 下载: {title[:50]}...")
                        
                        # 点击下载
                        with page.expect_download() as download_info:
                            link.click()
                        
                        download = download_info.value
                        download.save_as(str(filepath))
                        
                        print(f"已保存: {filepath}")
                        stats["success"] += 1
                        
                        # 等待一下，避免请求过快
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"下载失败: {e}")
                        stats["failed"] += 1
                        continue
                
                return stats
                
            except Exception as e:
                print(f"搜索失败: {e}")
                return {"total": 0, "success": 0, "failed": 0}
            finally:
                browser.close()


def main():
    parser = argparse.ArgumentParser(description="中国货币网债券披露文件批量下载")
    parser.add_argument("--keyword", required=True, help="搜索关键词，如\"山东城资\"")
    parser.add_argument("--output", default="./downloads", help="输出目录")
    args = parser.parse_args()
    
    scraper = ChinamoneyPlaywrightScraper(output_dir=args.output)
    stats = scraper.search_and_download(args.keyword)
    
    print(f"\n{'='*50}")
    print(f"下载完成!")
    print(f"总计: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
