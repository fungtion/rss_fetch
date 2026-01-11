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
        if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join(SAVE_DIR, f'{date_str}.json')
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(articles)} articles to {filename}")
    else:
        print("No feeds found.")