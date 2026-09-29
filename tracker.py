import os
import sys
import json
import logging
import email.utils
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
import requests

from notifiers import (
    send_discord_notification,
    send_telegram_notification,
    send_email_notification,
    update_markdown_log,
    log_github_summary
)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tracker")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
HISTORY_PATH = os.path.join(SCRIPT_DIR, "seen_history.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "latest_updates.md")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Config file not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read history, starting fresh: {e}")
    return {}

def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def parse_iso_or_rfc(date_str: str) -> datetime:
    """Attempts to parse ISO 8601 or RFC 2822 dates."""
    if not date_str:
        return datetime.now(timezone.utc)
    
    # Try RFC 2822 (common in RSS feeds)
    try:
        parsed_tuple = email.utils.parsedate_to_datetime(date_str)
        if parsed_tuple.tzinfo is None:
            return parsed_tuple.replace(tzinfo=timezone.utc)
        return parsed_tuple.astimezone(timezone.utc)
    except Exception:
        pass

    # Try ISO formats
    clean_str = date_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return datetime.now(timezone.utc)

def fetch_github_releases(repo_entry: dict, github_token: str | None, max_age_days: int) -> list[dict]:
    name = repo_entry["name"]
    repo = repo_entry["repo"]
    category = repo_entry.get("category", "Software")
    headers = {"User-Agent": "OpenSource-News-Tracker/1.0"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    releases_url = f"https://api.github.com/repos/{repo}/releases?per_page=5"
    updates = []

    try:
        resp = requests.get(releases_url, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            for r in data:
                if r.get("draft", False):
                    continue
                pub_date_str = r.get("published_at") or r.get("created_at")
                dt = parse_iso_or_rfc(pub_date_str)
                tag_or_title = r.get("name") or r.get("tag_name")
                html_url = r.get("html_url")
                unique_id = f"github:{repo}:{r.get('id') or r.get('tag_name')}"
                
                updates.append({
                    "id": unique_id,
                    "project": name,
                    "title": tag_or_title or "New Release",
                    "category": category,
                    "date_time": dt.isoformat(),
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "url": html_url,
                    "source_type": "GitHub Release"
                })
        elif resp.status_code == 404 or resp.status_code == 200:
            pass
        elif resp.status_code == 403:
            logger.warning(f"Rate limited or forbidden on GitHub repo {repo}")
    except Exception as e:
        logger.error(f"Error fetching GitHub releases for {repo}: {e}")

    return updates

def fetch_rss_feed(feed_entry: dict, max_age_days: int) -> list[dict]:
    name = feed_entry["name"]
    url = feed_entry["url"]
    category = feed_entry.get("category", "Blog / Feed")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OpenSource-Tracker/1.0"}
    updates = []

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            logger.warning(f"Feed error {resp.status_code} for {url}")
            return []

        root = ET.fromstring(resp.content)
        # Check RSS format
        channel = root.find("channel")
        if channel is not None:
            items = channel.findall("item")[:5]
            for item in items:
                title = item.findtext("title") or "Untitled"
                link = item.findtext("link") or ""
                pub_date = item.findtext("pubDate") or ""
                dt = parse_iso_or_rfc(pub_date)
                unique_id = f"rss:{url}:{link or title}"
                
                updates.append({
                    "id": unique_id,
                    "project": name,
                    "title": title.strip(),
                    "category": category,
                    "date_time": dt.isoformat(),
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "url": link.strip(),
                    "source_type": "RSS Feed"
                })
        else:
            # Check Atom format
            # Atom xmlns handling
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns) or root.findall("entry")
            for entry in entries[:5]:
                title = entry.findtext("atom:title", namespaces=ns) or entry.findtext("title") or "Untitled"
                link_elem = entry.find("atom:link", namespaces=ns) or entry.find("link")
                link = link_elem.attrib.get("href", "") if link_elem is not None else ""
                published = entry.findtext("atom:published", namespaces=ns) or entry.findtext("atom:updated", namespaces=ns) or entry.findtext("published") or entry.findtext("updated") or ""
                dt = parse_iso_or_rfc(published)
                unique_id = f"atom:{url}:{link or title}"

                updates.append({
                    "id": unique_id,
                    "project": name,
                    "title": title.strip(),
                    "category": category,
                    "date_time": dt.isoformat(),
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "url": link.strip(),
                    "source_type": "Atom Feed"
                })
    except Exception as e:
        logger.error(f"Error fetching RSS/Atom feed {url}: {e}")

    return updates

def fetch_reddit_posts(entry: dict, max_age_days: int) -> list[dict]:
    subreddit = entry.get("subreddit")
    name = entry.get("name", f"r/{subreddit}")
    min_upvotes = entry.get("min_upvotes", 30)
    category = entry.get("category", "Community")
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=15"
    headers = {"User-Agent": "OpenSourceNewsTrackerBot/1.0 (Educational YouTube Tracker)"}
    updates = []

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            posts = resp.json().get("data", {}).get("children", [])
            for post_obj in posts:
                post = post_obj.get("data", {})
                score = post.get("score", 0)
                if score < min_upvotes or post.get("stickied", False):
                    continue
                created_utc = post.get("created_utc")
                dt = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else datetime.now(timezone.utc)
                permalink = f"https://reddit.com{post.get('permalink')}"
                unique_id = f"reddit:{subreddit}:{post.get('id')}"

                updates.append({
                    "id": unique_id,
                    "project": name,
                    "title": f"[{score}↑] {post.get('title')}",
                    "category": category,
                    "date_time": dt.isoformat(),
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "url": permalink,
                    "source_type": "Reddit Discussion"
                })
    except Exception as e:
        logger.error(f"Error fetching Reddit r/{subreddit}: {e}")

    return updates

def fetch_hacker_news(entry: dict, max_age_days: int) -> list[dict]:
    query = entry.get("query", "release")
    name = entry.get("name", "Hacker News")
    min_points = entry.get("min_points", 50)
    category = entry.get("category", "Tech News")
    url = f"https://hn.algolia.com/api/v1/search_by_date?tags=story&query={query}&numericFilters=points>{min_points}&hitsPerPage=10"
    headers = {"User-Agent": "OpenSource-News-Tracker/1.0"}
    updates = []

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for hit in hits:
                created_at = hit.get("created_at")
                dt = parse_iso_or_rfc(created_at)
                title = hit.get("title", "")
                hn_id = hit.get("objectID")
                post_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"
                unique_id = f"hn:{hn_id}"

                updates.append({
                    "id": unique_id,
                    "project": name,
                    "title": f"[{hit.get('points', 0)} pts] {title}",
                    "category": category,
                    "date_time": dt.isoformat(),
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "url": post_url,
                    "source_type": "Hacker News"
                })
    except Exception as e:
        logger.error(f"Error fetching Hacker News query {query}: {e}")

    return updates

def main():
    logger.info("Starting Open Source Tracker check...")
    config = load_config()
    history = load_history()
    is_initial_run = len(history) == 0

    max_age_days = config.get("settings", {}).get("max_age_days", 7)
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    github_token = os.getenv("GITHUB_TOKEN")
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_to = os.getenv("MAIL_TO")

    all_fetched = []

    # 1. Fetch GitHub Repos
    logger.info(f"Scanning {len(config.get('github_repos', []))} GitHub repositories...")
    for repo_entry in config.get("github_repos", []):
        releases = fetch_github_releases(repo_entry, github_token, max_age_days)
        all_fetched.extend(releases)

    # 2. Fetch RSS Feeds
    logger.info(f"Scanning {len(config.get('rss_feeds', []))} RSS feeds...")
    for feed_entry in config.get("rss_feeds", []):
        feed_items = fetch_rss_feed(feed_entry, max_age_days)
        all_fetched.extend(feed_items)

    # 3. Fetch Community Sources
    logger.info(f"Scanning {len(config.get('community_sources', []))} community sources...")
    for comm in config.get("community_sources", []):
        c_type = comm.get("type")
        if c_type == "reddit":
            all_fetched.extend(fetch_reddit_posts(comm, max_age_days))
        elif c_type == "hacker_news":
            all_fetched.extend(fetch_hacker_news(comm, max_age_days))

    # Filter out updates older than cutoff_time or already seen
    new_unseen_updates = []
    for item in all_fetched:
        item_id = item["id"]
        try:
            item_dt = datetime.fromisoformat(item["date_time"])
            if item_dt < cutoff_time:
                continue
        except Exception:
            pass

        if item_id not in history:
            new_unseen_updates.append(item)
            history[item_id] = {
                "project": item["project"],
                "title": item["title"],
                "time": item["formatted_time"],
                "url": item["url"],
                "seen_at": datetime.now(timezone.utc).isoformat()
            }

    # Sort newest first
    new_unseen_updates.sort(key=lambda x: x["date_time"], reverse=True)

    print("\n" + "="*70)
    print(f"📊 TRACKER RUN REPORT - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*70)

    if is_initial_run:
        print(f"⚡ Initial setup detected! Populated database with {len(history)} recent items.")
        print(f"Displaying top {min(10, len(new_unseen_updates))} most recent open source updates:\n")
        # On first run, display top items and notify if webhooks exist
        display_items = new_unseen_updates[:10]
    else:
        print(f"Found {len(new_unseen_updates)} NEW updates since last check!\n")
        display_items = new_unseen_updates

    for item in display_items:
        print(f"🔹 [{item['formatted_time']}] {item['project']} ({item.get('category', 'General')})")
        print(f"   Title: {item['title']}")
        print(f"   Link:  {item['url']}")
        print("-" * 70)

    # Dispatch notifications if there are new items
    items_to_notify = new_unseen_updates if not is_initial_run else display_items
    if items_to_notify:
        if discord_webhook:
            logger.info("Sending notifications to Discord...")
            send_discord_notification(discord_webhook, items_to_notify)
        if telegram_bot_token and telegram_chat_id:
            logger.info("Sending notifications to Telegram...")
            send_telegram_notification(telegram_bot_token, telegram_chat_id, items_to_notify)
        if mail_username and mail_password:
            logger.info(f"Sending email notification via Gmail to {mail_to or mail_username}...")
            send_email_notification(mail_username, mail_password, mail_to, items_to_notify)

        update_markdown_log(LOG_PATH, items_to_notify)
        log_github_summary(items_to_notify)

    # Save state
    save_history(history)
    logger.info(f"History updated. Total tracked items remembered: {len(history)}")

if __name__ == "__main__":
    main()
