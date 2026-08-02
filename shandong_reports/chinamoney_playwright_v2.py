#!/usr/bin/env python3
"""
中国货币网(chinamoney.com.cn)债券披露文件批量下载脚本 - Playwright版本v2
无需登录，免费获取银行间市场债券披露文件

用法:
    python chinamoney_playwright_v2.py --keyword "山东城资" --output ./downloads
    python chinamoney_playwright_v2.py --keyword "山东高速" --output ./downloads
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
                
                # 等待搜索结果加载
                print("等待搜索结果加载...")
                page.wait_for_timeout(3000)
                
                # 提取下载链接和信息
                print("提取下载链接...")
                
                # 使用JavaScript提取所有下载链接
                results = page.evaluate("""
                    () => {
                        const items = [];
                        const listItems = document.querySelectorAll('#page-search-results li');
                        listItems.forEach(li => {
                            const dateElem = li.querySelector('.text-date span');
                            const date = dateElem ? dateElem.textContent.trim() : '';
                            
                            const titleElem = li.querySelector('a:not(.link-img)');
                            const title = titleElem ? titleElem.textContent.trim() : '';
                            
                            const downloadElem = li.querySelector('a.link-img');
                            const onclick = downloadElem ? downloadElem.getAttribute('onclick') : '';
                            
                            // 从onclick中提取URL - 处理两种情况
                            let downloadUrl = '';
                            if (onclick) {
                                // 尝试匹配有URL的情况 (第8个参数)
                                const matchWithUrl = onclick.match(/filterLevel\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*[^,]*\s*,\s*[^,]*\s*,\s*[^,]*\s*,\s*[^,]*\s*,\s*'([^']+)'\s*\)/);
                                if (matchWithUrl) {
                                    downloadUrl = matchWithUrl[1];
                                } else {
                                    // 尝试匹配无URL的情况 (第8个参数是null)
                                    const matchNoUrl = onclick.match(/filterLevel\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*[^,]*\s*,\s*[^,]*\s*,\s*[^,]*\s*,\s*[^,]*\s*,\s*null\s*\)/);
                                    if (matchNoUrl) {
                                        downloadUrl = '';
                                    }
                                }
                            }
                            
                            items.push({
                                date: date,
                                title: title,
                                downloadUrl: downloadUrl,
                                onclick: onclick
                            });
                        });
                        return items;
                    }
                """)
                
                print(f"找到 {len(results)} 条结果")
                
                if not results:
                    print("未找到下载链接")
                    return {"total": 0, "success": 0, "failed": 0}
                
                # 下载文件
                stats = {"total": len(results), "success": 0, "failed": 0}
                
                for i, item in enumerate(results):
                    try:
                        title = item['title']
                        date = item['date']
                        download_url = item['downloadUrl']
                        
                        if not download_url or download_url == 'null':
                            print(f"[{i+1}/{len(results)}] 跳过: {title[:50]}... (无下载链接)")
                            stats["failed"] += 1
                            continue
                        
                        # 构造文件名
                        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
                        if date:
                            filename = f"{date}_{safe_title}.pdf"
                        else:
                            filename = f"{safe_title}.pdf"
                        
                        filepath = self.output_dir / filename
                        
                        print(f"[{i+1}/{len(results)}] 下载: {title[:50]}...")
                        
                        # 使用JavaScript点击下载
                        with page.expect_download() as download_info:
                            page.evaluate(f"""
                                () => {{
                                    const links = document.querySelectorAll('#page-search-results li a.link-img');
                                    if (links[{i}]) {{
                                        links[{i}].click();
                                    }}
                                }}
                            """)
                        
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
