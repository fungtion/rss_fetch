import xml.etree.ElementTree as ET
import feedparser
import json
import os
from datetime import datetime, timedelta, timezone
from time import mktime

# === 配置 ===
OPML_FILE = 'feeds.xml'  # 请确保你的 OPML 文件名也是这个
SAVE_DIR = 'daily_news'
# ============

def get_feeds(file_path):
    feeds = []
    if not os.path.exists(file_path): return []
    try:
        tree = ET.parse(file_path)
        for outline in tree.getroot().findall('.//outline'):
            if 'xmlUrl' in outline.attrib:
                feeds.append({
                    'title': outline.attrib.get('title', 'Unknown'),
                    'url': outline.attrib['xmlUrl'],
                    'category': outline.attrib.get('text', 'Uncategorized')
                })
        return feeds
    except: return []

def fetch_articles(feeds):
    # 定义北京时区 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now(beijing_tz)
    
    print(f"Current Beijing Time: {now_bj}")

    # 根据当前时间确定抽取窗口
    # 容错范围：假设脚本在预定时间前后 1 小时内执行
    h = now_bj.hour
    start_time = None
    end_time = None
    
    if 7 <= h < 9: # 早上 8 点运行 -> 抽取今天 0-8 点
        end_time = now_bj.replace(hour=8, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=8)
    elif 15 <= h < 17: # 下午 16 点运行 -> 抽取今天 8-16 点
        end_time = now_bj.replace(hour=16, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=8)
    elif h >= 23 or h < 1: # 凌晨 0 点运行 -> 抽取昨天 16-24 点
        # 如果是 0 点左右运行，基准应该是当天的 00:00
        # (即昨天的 24:00)
        end_time = now_bj.replace(hour=0, minute=0, second=0, microsecond=0)
        # 如果现在是 23点 (实际上稍微早跑了)，要把 end_time 设为明天 0 点
        if h >= 23:
            end_time = end_time + timedelta(days=1)
        
        start_time = end_time - timedelta(hours=8) # 昨天 16:00
    else:
        print("Running outside of standard schedule (0, 8, 16 Beijing Time). Defaulting to past 24 hours.")
        end_time = now_bj
        start_time = end_time - timedelta(hours=24)

    print(f"Extraction Window (Beijing Time): {start_time} to {end_time}")
    
    collected = []

    for feed in feeds:
        try:
            # 缩短超时时间，避免卡顿
            d = feedparser.parse(feed['url'])
            for entry in d.entries:
                try:
                    # 解析时间
                    t = None
                    if hasattr(entry, 'published_parsed'): t = entry.published_parsed
                    elif hasattr(entry, 'updated_parsed'): t = entry.updated_parsed
                    
                    if t:
                        # feedparser 解析出的通常是 UTC 时间 (struct_time)
                        # 先构建 UTC datetime
                        pub_time_utc = datetime(*t[:6], tzinfo=timezone.utc)
                        
                        # 转换为北京时间进行比较
                        pub_time_bj = pub_time_utc.astimezone(beijing_tz)
                        
                        # 筛选指定时间窗口
                        if start_time <= pub_time_bj <= end_time:
                            collected.append({
                                'source': feed['title'],
                                'category': feed['category'],
                                'title': entry.get('title', 'No Title'),
                                'link': entry.get('link', ''),
                                'date': pub_time_bj.strftime('%Y-%m-%d %H:%M'), # 保存为北京时间字符串
                                'summary': entry.get('summary', '')
                            })
                except: continue
        except: continue
    return collected

if __name__ == "__main__":
    feeds = get_feeds(OPML_FILE)
    if feeds:
        articles = fetch_articles(feeds)
        
        # 准备保存
        # 准备保存目录
        if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

        # 按日期分组
        articles_by_date = {}
        for article in articles:
            date_str = article['date'][:10]  # 取 YYYY-MM-DD
            if date_str not in articles_by_date:
                articles_by_date[date_str] = []
            articles_by_date[date_str].append(article)

        for date_str, date_articles in articles_by_date.items():
            filename = os.path.join(SAVE_DIR, f'{date_str}.json')
            
            # 读取现有数据以追加（去重）
            existing_articles = []
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_articles = json.load(f)
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
            
            # 使用链接去重
            existing_links = set(item.get('link') for item in existing_articles)
            new_count = 0
            
            for article in date_articles:
                if article.get('link') not in existing_links:
                    existing_articles.append(article)
                    existing_links.add(article.get('link'))
                    new_count += 1
            
            if new_count > 0:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(existing_articles, f, ensure_ascii=False, indent=2)
                print(f"Saved to {filename}: {len(existing_articles)} total ({new_count} new)")
            else:
                print(f"No new articles for {filename}")
    else:
        print("No feeds found.")