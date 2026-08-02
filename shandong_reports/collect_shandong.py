"""
山东城投公司债券研究报告 - 批量采集脚本
========================================
功能：按公司名称批量搜索巨潮资讯网(cninfo)，获取募集说明书/评级报告PDF
渠道：巨潮资讯网（证监会指定信息披露平台，覆盖沪深两市债券公告）
依赖：python 3.12+，pdfplumber（可选，用于文本提取）
用法：
  python collect_shandong.py              # 全量采集（345家山东城投）
  python collect_shandong.py --city 济南  # 按城市采集
  python collect_shandong.py --test      # 测试模式（仅前3家）
"""
import urllib.request
import urllib.parse
import ssl
import json
import re
import os
import time
import hashlib
from datetime import datetime

# ======================== 配置 ========================
BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw")
QUEUE_FILE = os.path.join(BASE_DIR, "collection_queue.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "collection_progress.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "checkpoint.json")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.cninfo.com.cn/new/fulltextSearch/full",
    "Origin": "https://www.cninfo.com.cn",
}

# cninfo 全文本搜索API
CNINFO_SEARCH_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full"

# 搜索关键词类型：募集说明书相关
BOND_DOC_KEYWORDS = ["募集说明书", "募集说明", "信用评级", "跟踪评级", "债权代理",
                       "债券受托", "评级报告", "发行公告"]

# 过滤公告类型（排除非债券类）
EXCLUDE_COLUMNS = ["年报", "半年报", "季报", "一季度", "三季度",
                   "审计报告", "问询函", "补充", "更正", "决议", "章程",
                   "法律意见", "主承销商", "核查意见"]


# ======================== 核心函数 ========================

def cninfo_search(keyword, page=1, page_size=20):
    """
    搜索巨潮资讯网，返回公告列表
    返回: {"total": int, "announcements": [{title, announcementId, adjunctUrl, announcementTime, secCode, secName, orgId}, ...]}
    """
    params = {
        "searchkey": keyword,
        "sdate": "2020-01-01",    # 近5年
        "edate": datetime.now().strftime("%Y-%m-%d"),
        "isfulltext": "false",
        "sortName": "nothing",
        "sortType": "desc",
        "pageNum": page,
        "pageSize": page_size,
    }
    url = CNINFO_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [ERROR] 网络请求失败: {e}")
        return {"total": 0, "announcements": []}

    # 解析页面嵌入JSON
    data = _extract_cninfo_json(html)
    return data


def _extract_cninfo_json(html):
    """从cninfo搜索页面HTML中提取公告JSON"""
    announcements = []
    total = 0

    # 匹配 embedded data
    m = re.search(r'"totalRecordNum"\s*:\s*(\d+)', html)
    if m:
        total = int(m.group(1))

    # 从页面script中提取 announcements 数组
    # cninfo 将数据嵌入在 ref=e2 的 JSON 字符串中
    m = re.search(r'"announcements"\s*:\s*(\[.*?\])\s*,\s*"categoryList"', html, re.DOTALL)
    if not m:
        # 备选：直接从 script/json 块中提取
        m = re.search(r'\{[^{}]*"announcements"\s*:\s*\[(.*?)\][^{}]*\}', html, re.DOTALL)

    if m:
        try:
            arr_str = "[" + m.group(1) + "]"
            arr = json.loads(arr_str)
            for item in arr:
                ann = {
                    "announcementId": item.get("announcementId", ""),
                    "title": _strip_html(item.get("announcementTitle", "")),
                    "time": _ts_to_date(item.get("announcementTime")),
                    "pdf_url": "https://static.cninfo.com.cn/" + item.get("adjunctUrl", ""),
                    "secCode": item.get("secCode", ""),
                    "secName": item.get("secName", ""),
                    "orgId": item.get("orgId", ""),
                    "pageColumn": item.get("pageColumn", ""),
                    "announcementType": item.get("announcementType", ""),
                }
                announcements.append(ann)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [WARN] JSON解析失败: {e}")

    return {"total": total, "announcements": announcements}


def _strip_html(s):
    """去除HTML标签"""
    return re.sub(r"<[^>]+>", "", s).strip()


def _ts_to_date(ts):
    """毫秒时间戳转日期字符串"""
    try:
        import datetime
        ts = int(str(ts)[:10])
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except:
        return ""


def filter_bond_docs(announcements):
    """过滤出债券相关公告（募集说明书、评级报告等）"""
    results = []
    for ann in announcements:
        title = ann["title"].lower()
        col = ann.get("pageColumn", "").lower()
        # 排除明显非债券类的公告
        if any(ex in title for ex in EXCLUDE_COLUMNS):
            continue
        # 优先匹配债券相关关键词
        if any(kw in ann["title"] for kw in BOND_DOC_KEYWORDS):
            results.append(ann)
    return results


def download_pdf(url, save_path, timeout=30):
    """下载PDF文件"""
    if os.path.exists(save_path):
        print(f"  [SKIP] 文件已存在: {save_path}")
        return True
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            data = resp.read()
            with open(save_path, "wb") as f:
                f.write(data)
            size = len(data) / 1024
            print(f"  [OK] 下载成功: {os.path.basename(save_path)} ({size:.0f} KB)")
            return True
    except Exception as e:
        print(f"  [ERROR] 下载失败 [{url[:60]}]: {e}")
        return False


def save_announcement_list(company_name, city, announcements, out_file):
    """保存公告列表到JSON"""
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    record = {
        "company": company_name,
        "city": city,
        "search_time": datetime.now().isoformat(),
        "total_found": len(announcements),
        "announcements": announcements,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


# ======================== 山东城投名单 ========================

def get_shandong_companies():
    """
    山东城投公司名单（2023年数据，覆盖16地级市+主要开发区）
    优先级排序：债券余额大的优先（青岛、济南、潍坊排前三）
    """
    return [
        # === 青岛（67家，城投债余额4,902亿，排第一）===
        {"name": "青岛城市建设投资(集团)有限责任公司", "city": "青岛", "priority": 1},
        {"name": "青岛国信发展(集团)有限责任公司", "city": "青岛", "priority": 1},
        {"name": "青岛地铁集团有限公司", "city": "青岛", "priority": 1},
        {"name": "青岛海发国有资本投资运营集团有限公司", "city": "青岛", "priority": 1},
        {"name": "青岛华通国有资本投资运营集团有限公司", "city": "青岛", "priority": 1},
        {"name": "青岛水务集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛旅游集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛城市发展集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛西海岸新区海洋控股集团有限公司", "city": "青岛西海岸新区", "priority": 1},
        {"name": "青岛西海岸新区融合控股集团有限公司", "city": "青岛西海岸新区", "priority": 1},
        {"name": "城发投资集团有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛黄岛发展(集团)有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛军民融合发展集团有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛经济技术开发区投资控股集团有限公司", "city": "青岛西海岸新区", "priority": 2},

        # === 济南（30家，城投债余额2,249亿，排第二）===
        {"name": "济南城市投资集团有限公司", "city": "济南", "priority": 1},
        {"name": "济南城市建设集团有限公司", "city": "济南", "priority": 1},
        {"name": "济南轨道交通集团有限公司", "city": "济南", "priority": 1},
        {"name": "济南西城投资开发集团有限公司", "city": "济南", "priority": 2},
        {"name": "齐鲁财金(山东)经济发展有限公司", "city": "济南", "priority": 2},
        {"name": "济南能源集团有限公司", "city": "济南", "priority": 2},
        {"name": "莱芜城市发展集团有限公司", "city": "济南", "priority": 3},
        {"name": "济南高新控股集团有限公司", "city": "济南高新区", "priority": 1},

        # === 潍坊（56家，城投债余额1,167亿，排第三）===
        {"name": "潍坊市城市建设发展投资集团有限公司", "city": "潍坊", "priority": 1},
        {"name": "潍坊滨海投资发展有限公司", "city": "潍坊", "priority": 1},
        {"name": "潍坊滨城投资开发有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊市投资集团有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊水务投资集团有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊滨海旅游集团有限公司", "city": "潍坊", "priority": 3},
        {"name": "潍坊三农创新发展集团有限公司", "city": "潍坊", "priority": 3},
        {"name": "山东高创建设投资集团有限公司", "city": "潍坊", "priority": 2},

        # === 烟台 ===
        {"name": "烟台蓝天投资开发集团有限公司", "city": "烟台", "priority": 1},
        {"name": "烟台市城市建设投资有限责任公司", "city": "烟台", "priority": 1},
        {"name": "烟台市财金发展投资集团有限公司", "city": "烟台", "priority": 2},
        {"name": "烟台业达城市发展集团有限公司", "city": "烟台经开区", "priority": 2},

        # === 淄博 ===
        {"name": "淄博市城市资产运营集团有限公司", "city": "淄博", "priority": 1},
        {"name": "淄博高新国有资本投资有限公司", "city": "淄博", "priority": 2},
        {"name": "淄博高新城市投资运营集团有限公司", "city": "淄博", "priority": 2},

        # === 临沂 ===
        {"name": "临沂城市建设投资集团有限公司", "city": "临沂", "priority": 1},
        {"name": "临沂城市发展集团有限公司", "city": "临沂", "priority": 1},
        {"name": "临沂投资发展集团有限公司", "city": "临沂", "priority": 2},
        {"name": "临沂商城控股集团有限公司", "city": "临沂", "priority": 2},

        # === 威海 ===
        {"name": "威海城市投资集团有限公司", "city": "威海", "priority": 1},
        {"name": "威海产业投资集团有限公司", "city": "威海", "priority": 2},
        {"name": "威海高新城市建设发展有限公司", "city": "威海高新区", "priority": 2},

        # === 济宁 ===
        {"name": "济宁城投控股集团有限公司", "city": "济宁", "priority": 1},
        {"name": "山东公用控股有限公司", "city": "济宁", "priority": 2},
        {"name": "济宁高新城建投资有限公司", "city": "济宁高新区", "priority": 2},

        # === 日照 ===
        {"name": "日照市城市建设投资集团有限公司", "city": "日照", "priority": 1},
        {"name": "日照城投集团有限公司", "city": "日照", "priority": 2},
        {"name": "日照交通能源发展集团有限公司", "city": "日照", "priority": 2},

        # === 泰安 ===
        {"name": "泰安市泰山投资有限公司", "city": "泰安", "priority": 1},
        {"name": "泰安市泰山财金投资集团有限公司", "city": "泰安", "priority": 2},
        {"name": "泰安市城市发展投资有限公司", "city": "泰安", "priority": 2},

        # === 聊城 ===
        {"name": "聊城市财信投资控股集团有限公司", "city": "聊城", "priority": 1},
        {"name": "聊城市兴业控股集团有限公司", "city": "聊城经开区", "priority": 2},

        # === 德州 ===
        {"name": "德州财金投资控股集团有限公司", "city": "德州", "priority": 1},
        {"name": "德州德达城市建设投资运营有限公司", "city": "德州", "priority": 2},

        # === 滨州 ===
        {"name": "滨州城建投资集团有限公司", "city": "滨州", "priority": 1},
        {"name": "滨州市惠众置业有限公司", "city": "滨州", "priority": 2},

        # === 东营 ===
        {"name": "东营市财金投资集团有限公司", "city": "东营", "priority": 1},
        {"name": "东营市城市资产经营有限公司", "city": "东营", "priority": 2},

        # === 枣庄 ===
        {"name": "枣庄市基础设施投资发展集团有限公司", "city": "枣庄", "priority": 1},
        {"name": "枣庄高新投资集团有限公司", "city": "枣庄", "priority": 2},

        # === 菏泽 ===
        {"name": "菏泽城投控股集团有限公司", "city": "菏泽", "priority": 1},
        {"name": "菏泽投资发展集团有限公司", "city": "菏泽", "priority": 2},
        {"name": "菏泽市城市开发投资有限公司", "city": "菏泽", "priority": 2},
    ]


# ======================== 采集主流程 ========================

def load_progress():
    """加载采集进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": {}, "stats": {"total": 0, "found": 0, "downloaded": 0}}


def save_progress(progress):
    """保存采集进度"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def collect_company(company, progress, test_mode=False, download=True):
    """采集单家公司"""
    name = company["name"]
    city = company["city"]

    print(f"\n{'='*60}")
    print(f"  公司: {name} ({city})")
    print(f"{'='*60}")

    # 构建存储目录
    safe_city = city.replace("/", "_").replace("\\", "_")
    safe_name = name.replace("/", "_").replace("\\", "_")
    company_dir = os.path.join(RAW_DIR, safe_city, safe_name)
    os.makedirs(company_dir, exist_ok=True)

    # 保存公告列表
    list_file = os.path.join(company_dir, "_announcements.json")

    # 搜索cninfo
    result = cninfo_search(name)
    total = result.get("total", 0)
    announcements = result.get("announcements", [])

    # 过滤债券相关
    bond_docs = filter_bond_docs(announcements)

    print(f"  搜索结果: 共{total}条公告 | 债券相关: {len(bond_docs)}条")

    # 保存公告列表
    save_announcement_list(name, city, bond_docs, list_file)

    # 记录进度
    progress["stats"]["found"] += len(bond_docs)
    progress["stats"]["total"] = total

    # 下载PDF（测试模式只下前2个）
    downloaded = 0
    if download and bond_docs:
        docs_to_download = bond_docs[:3] if test_mode else bond_docs
        for ann in docs_to_download:
            if ann["pdf_url"].endswith(".PDF") or ann["pdf_url"].endswith(".pdf"):
                # 生成文件名：{公司名}_{日期}_{公告ID}.pdf
                date_str = ann["time"].replace("-", "")
                ann_id = ann["announcementId"]
                title_clean = re.sub(r'[\\/:*?"<>|]', "", ann["title"])[:30]
                filename = f"{date_str}_{ann_id}_{title_clean}.pdf"
                save_path = os.path.join(company_dir, filename)

                ok = download_pdf(ann["pdf_url"], save_path)
                if ok:
                    downloaded += 1
                    progress["stats"]["downloaded"] += 1

                time.sleep(0.5)  # 礼貌延迟，避免被限流

    progress["completed"].append({
        "name": name,
        "city": city,
        "total": total,
        "bond_docs": len(bond_docs),
        "downloaded": downloaded,
        "time": datetime.now().isoformat(),
    })
    save_progress(progress)

    return bond_docs


def run_collection(test_mode=False, city_filter=None, max_companies=None):
    """运行全量采集"""
    progress = load_progress()
    companies = get_shandong_companies()

    # 按城市过滤
    if city_filter:
        companies = [c for c in companies if city_filter in c["city"]]
        print(f"[INFO] 筛选城市: {city_filter}，共{len(companies)}家")

    # 按优先级排序
    companies.sort(key=lambda x: x["priority"])

    # 测试模式
    if test_mode:
        companies = companies[:3]
        print("[INFO] 测试模式：仅采集前3家")

    # 限制数量
    if max_companies:
        companies = companies[:max_companies]

    print(f"\n{'#'*60}")
    print(f"  山东城投债券报告采集任务")
    print(f"  公司数量: {len(companies)}")
    print(f"  输出目录: {RAW_DIR}")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    # 断点续采：跳过已完成的公司
    completed_names = {c["name"] for c in progress["completed"]}
    companies = [c for c in companies if c["name"] not in completed_names]

    if companies:
        print(f"\n[INFO] 本次需采集: {len(companies)}家（已跳过{len(completed_names)}家）")
    else:
        print("\n[INFO] 所有公司已采集完成！")

    total_found = 0
    total_dl = 0

    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] ", end="")
        try:
            bond_docs = collect_company(company, progress, test_mode=test_mode)
            total_found += len(bond_docs)
        except Exception as e:
            print(f"  [FATAL ERROR] {e}")
            progress["failed"][company["name"]] = str(e)
            save_progress(progress)

    print(f"\n\n{'#'*60}")
    print(f"  采集完成！")
    print(f"  本次采集: {len(companies)}家")
    print(f"  累计发现债券文档: {progress['stats']['found']}条")
    print(f"  累计下载PDF: {progress['stats']['downloaded']}个")
    print(f"  完成目录: {RAW_DIR}")
    print(f"{'#'*60}")


# ======================== 命令行入口 ========================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="山东城投债券报告采集工具")
    parser.add_argument("--test", action="store_true", help="测试模式（仅采集前3家）")
    parser.add_argument("--city", type=str, default=None, help="按城市筛选（如：济南、青岛）")
    parser.add_argument("--max", type=int, default=None, help="最多采集公司数量")
    parser.add_argument("--list", action="store_true", help="仅列出公司名单，不采集")
    args = parser.parse_args()

    if args.list:
        companies = get_shandong_companies()
        companies.sort(key=lambda x: x["priority"])
        for i, c in enumerate(companies, 1):
            print(f"{i:3d}. [{c['city']}] {c['name']} (优先级:{c['priority']})")
        print(f"\n合计: {len(companies)}家")
    else:
        run_collection(
            test_mode=args.test,
            city_filter=args.city,
            max_companies=args.max,
        )
