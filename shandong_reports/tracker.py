"""
山东城投债券采集进度跟踪器
=============================
功能：
1. 按城市/优先级显示采集清单
2. 记录已采集的公司及文件
3. 生成待采集清单（用于企业预警通操作）

使用方法：
  python tracker.py              # 显示所有公司采集状态
  python tracker.py --city 青岛  # 只看青岛
  python tracker.py --todo       # 生成待采集清单
  python tracker.py --progress   # 显示进度统计
"""
import json
import os
import sys
from datetime import datetime

BASE_DIR = r"C:\Users\wade\OneDrive\claw\城投\shandong_reports"
RAW_DIR = os.path.join(BASE_DIR, "raw")
PROGRESS_FILE = os.path.join(BASE_DIR, "collection_progress.json")

sys.path.insert(0, BASE_DIR)
from shandong_companies import get_shandong_companies


def load_progress():
    """加载采集进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_progress(progress):
    """保存采集进度"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def scan_local_files(company_name, city):
    """扫描本地已有的文件"""
    company_dir = os.path.join(RAW_DIR, city, company_name)
    if not os.path.exists(company_dir):
        return []
    
    files = []
    for f in os.listdir(company_dir):
        if f.endswith('.pdf') or f.endswith('.PDF'):
            fpath = os.path.join(company_dir, f)
            size = os.path.getsize(fpath) / 1024 / 1024  # MB
            files.append({
                'name': f,
                'path': fpath,
                'size_mb': round(size, 2)
            })
    return files


def get_status(company, progress):
    """获取公司采集状态"""
    company_key = company['name']
    if company_key in progress:
        return progress[company_key].get('status', 'unknown')
    
    # 检查本地文件
    files = scan_local_files(company['name'], company['city'])
    if files:
        return 'partial'  # 有本地文件但未记录
    
    return 'pending'  # 待采集


def show_progress():
    """显示采集进度"""
    companies = get_shandong_companies()
    progress = load_progress()
    
    # 按城市分组统计
    cities = {}
    for c in companies:
        city = c['city']
        if city not in cities:
            cities[city] = {'total': 0, 'completed': 0, 'partial': 0, 'pending': 0}
        cities[city]['total'] += 1
        
        status = get_status(c, progress)
        if status == 'completed':
            cities[city]['completed'] += 1
        elif status == 'partial':
            cities[city]['partial'] += 1
        else:
            cities[city]['pending'] += 1
    
    print("\n" + "="*60)
    print("  山东城投债券采集进度")
    print("="*60)
    print(f"  总公司数: {len(companies)}")
    print(f"  统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-"*60)
    
    total_done = sum(cities[c]['completed'] + cities[c]['partial'] for c in cities)
    total_pending = sum(cities[c]['pending'] for c in cities)
    
    # 按总数排序
    sorted_cities = sorted(cities.items(), key=lambda x: x[1]['total'], reverse=True)
    
    print(f"\n{'城市':<12} {'总数':>6} {'已完成':>8} {'部分':>8} {'待采集':>8}")
    print("-"*60)
    for city, stats in sorted_cities:
        done_pct = (stats['completed'] + stats['partial']) / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"{city:<12} {stats['total']:>6} {stats['completed']:>8} {stats['partial']:>8} {stats['pending']:>8}  {done_pct:>5.1f}%")
    
    print("-"*60)
    total = len(companies)
    print(f"{'合计':<12} {total:>6} {total_done:>8} {'':>8} {total_pending:>8}  {total_done/total*100:>5.1f}%")
    print("="*60)


def show_todo(city=None):
    """显示待采集清单"""
    companies = get_shandong_companies()
    progress = load_progress()
    
    if city:
        companies = [c for c in companies if c['city'] == city]
    
    print("\n" + "="*60)
    print(f"  待采集清单 {'(' + city + ')' if city else '(全部)'}")
    print("="*60)
    
    # 按优先级和城市分组
    by_city = {}
    for c in companies:
        c_status = get_status(c, progress)
        if c_status not in ['completed']:
            city = c['city']
            if city not in by_city:
                by_city[city] = []
            by_city[city].append({
                'name': c['name'],
                'priority': c['priority'],
                'status': c_status
            })
    
    # 输出
    for city, items in sorted(by_city.items(), key=lambda x: -len(x[1])):
        print(f"\n【{city}】({len(items)}家待采集)")
        print("-"*40)
        for i, item in enumerate(sorted(items, key=lambda x: x['priority']), 1):
            priority_label = ['⭐⭐⭐', '⭐⭐', '⭐'][item['priority']-1] if item['priority'] <= 3 else ''
            status_icon = '📋' if item['status'] == 'pending' else '🔄'
            print(f"  {i:2}. {status_icon} {item['name']} {priority_label}")
    
    print("\n" + "="*60)
    total_todo = sum(len(by_city[c]) for c in by_city)
    print(f"  共 {total_todo} 家公司待采集")


def show_company_detail(company_name):
    """显示单个公司的详细信息"""
    progress = load_progress()
    companies = get_shandong_companies()
    
    # 找到公司
    company = None
    for c in companies:
        if company_name in c['name']:
            company = c
            break
    
    if not company:
        print(f"未找到公司: {company_name}")
        return
    
    print(f"\n{'='*60}")
    print(f"  {company['name']}")
    print(f"  城市: {company['city']} | 优先级: {company['priority']}")
    print("="*60)
    
    # 本地文件
    files = scan_local_files(company['name'], company['city'])
    if files:
        print(f"\n📁 本地文件 ({len(files)}个):")
        for f in files:
            print(f"  - {f['name']} ({f['size_mb']} MB)")
    else:
        print("\n📁 本地文件: 无")
    
    # 进度记录
    company_key = company['name']
    if company_key in progress:
        p = progress[company_key]
        print(f"\n📊 采集记录:")
        print(f"  状态: {p.get('status', 'unknown')}")
        print(f"  时间: {p.get('updated', 'unknown')}")
        if p.get('notes'):
            print(f"  备注: {p['notes']}")
    
    print()


def mark_done(company_name, status='completed', notes=''):
    """标记公司采集状态"""
    progress = load_progress()
    companies = get_shandong_companies()
    
    # 找到公司
    company = None
    for c in companies:
        if company_name in c['name']:
            company = c
            break
    
    if not company:
        print(f"未找到公司: {company_name}")
        return
    
    company_key = company['name']
    progress[company_key] = {
        'status': status,
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'city': company['city'],
        'notes': notes
    }
    
    save_progress(progress)
    print(f"✅ 已标记: {company['name']} -> {status}")


def generate_report():
    """生成采集汇总报告"""
    companies = get_shandong_companies()
    progress = load_progress()
    
    # 统计
    stats = {
        'total': len(companies),
        'by_status': {'completed': 0, 'partial': 0, 'pending': 0},
        'by_city': {},
        'by_priority': {1: 0, 2: 0, 3: 0}
    }
    
    for c in companies:
        status = get_status(c, progress)
        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        city = c['city']
        if city not in stats['by_city']:
            stats['by_city'][city] = {'total': 0, status: 0}
        stats['by_city'][city]['total'] += 1
        stats['by_city'][city][status] = stats['by_city'][city].get(status, 0) + 1
        
        pri = c['priority']
        stats['by_priority'][pri] = stats['by_priority'].get(pri, 0) + 1
    
    # 输出报告
    report = f"""
# 山东城投债券采集报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 采集概况

| 指标 | 数值 |
|------|------|
| 目标公司总数 | {stats['total']} |
| 已完成 | {stats['by_status']['completed']} ({stats['by_status']['completed']/stats['total']*100:.1f}%) |
| 部分完成 | {stats['by_status']['partial']} |
| 待采集 | {stats['by_status']['pending']} ({stats['by_status']['pending']/stats['total']*100:.1f}%) |

## 按优先级

| 优先级 | 数量 | 说明 |
|--------|------|------|
| ⭐⭐⭐ 最高 | {stats['by_priority'][1]} | 债券余额最大，优先采集 |
| ⭐⭐ 高 | {stats['by_priority'][2]} | 重要城投 |
| ⭐ 普通 | {stats['by_priority'][3]} | 一般城投 |

## 按城市

| 城市 | 总数 | 已完成 | 待采集 |
|------|------|--------|--------|
"""
    
    for city in sorted(stats['by_city'].keys(), key=lambda x: -stats['by_city'][x]['total']):
        s = stats['by_city'][city]
        done = s.get('completed', 0) + s.get('partial', 0)
        report += f"| {city} | {s['total']} | {done} | {s.get('pending', 0)} |\n"
    
    report += f"""
## 操作建议

1. **优先采集高优先级公司**（⭐⭐⭐）- 债券余额最大，信息价值最高
2. **从青岛、济南开始** - 城投债余额最大，样本最丰富
3. **使用企业预警通APP** - 全量覆盖，手动操作效率最高

---
*本报告由 tracker.py 自动生成*
"""
    
    # 保存报告
    report_file = os.path.join(BASE_DIR, '采集进度报告.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 报告已生成: {report_file}")
    print(report)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='山东城投债券采集跟踪器')
    parser.add_argument('--city', type=str, help='只看指定城市')
    parser.add_argument('--todo', action='store_true', help='显示待采集清单')
    parser.add_argument('--progress', action='store_true', help='显示采集进度')
    parser.add_argument('--detail', type=str, help='显示公司详情')
    parser.add_argument('--mark', type=str, nargs=2, metavar=('公司名', '状态'), help='标记公司状态')
    parser.add_argument('--report', action='store_true', help='生成汇总报告')
    
    args = parser.parse_args()
    
    if args.progress or (not args.todo and not args.detail and not args.mark and not args.report):
        show_progress()
    elif args.todo:
        show_todo(args.city)
    elif args.detail:
        show_company_detail(args.detail)
    elif args.mark:
        mark_done(args.mark[0], args.mark[1])
    elif args.report:
        generate_report()
    else:
        show_progress()
