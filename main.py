import xml.etree.ElementTree as ET
import feedparser
import json
import os
from datetime import datetime, timedelta
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
    print(f"Time: {datetime.now()}")
    # Use UTC for reliable comparison
    now = datetime.now().astimezone() # Local time with timezone info
    yesterday = now - timedelta(hours=24)
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
                        # feedparser returns UTC struct_time
                        # Create UTC aware datetime
                        from datetime import timezone
                        pub_time_utc = datetime(*t[:6], tzinfo=timezone.utc)
                        
                        # Convert to local time for comparison and storage
                        pub_time = pub_time_utc.astimezone()
                        
                        # 筛选过去 24 小时
                        if yesterday <= pub_time <= now:
                            collected.append({
                                'source': feed['title'],
                                'category': feed['category'],
                                'title': entry.get('title', 'No Title'),
                                'link': entry.get('link', ''),
                                'date': pub_time.strftime('%Y-%m-%d %H:%M'),
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