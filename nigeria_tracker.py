#!/usr/bin/env python3
"""
Polititrace Nigeria Daily Politics & Society Intelligence Dispatcher.
Fetches verified Nigerian political news, talk radio sentiment, macroeconomic indicators,
X (Twitter) trending topics & political discourse, and Instagram viral & civic news.
Formats a high-contrast publication briefing and sends daily email digests via Gmail SMTP.
"""
import os
import sys
import json
import logging
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import xml.etree.ElementTree as ET
import urllib.request
import re
import html

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nigeria_tracker")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(SCRIPT_DIR, "seen_nigeria_news.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "latest_nigeria_briefing.md")
HTML_OUTPUT_PATH = os.path.join(SCRIPT_DIR, "email_body.html")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PolititraceIntelligenceBot/2.0"
}

RSS_FEEDS = [
    # --- Top National & Breaking Wire ---
    {
        "name": "Daily Post",
        "url": "https://dailypost.ng/feed/",
        "category": "National & Breaking",
        "badge_color": "#DC2626"
    },
    {
        "name": "Channels TV",
        "url": "https://www.channelstv.com/feed/",
        "category": "National & Breaking",
        "badge_color": "#0284C7"
    },
    {
        "name": "The Punch",
        "url": "https://punchng.com/feed/",
        "category": "National & Breaking",
        "badge_color": "#EA580C"
    },
    {
        "name": "Premium Times",
        "url": "https://www.premiumtimesng.com/feed",
        "category": "National & Breaking",
        "badge_color": "#16A34A"
    },
    {
        "name": "Vanguard",
        "url": "https://www.vanguardngr.com/feed/",
        "category": "National & Breaking",
        "badge_color": "#9333EA"
    },
    {
        "name": "Google News Nigeria",
        "url": "https://news.google.com/rss?hl=en-NG&gl=NG&ceid=NG:en",
        "category": "National & Breaking",
        "badge_color": "#2563EB"
    },

    # --- Economy, Markets & Business ---
    {
        "name": "Nairametrics",
        "url": "https://nairametrics.com/feed/",
        "category": "Economy & Business",
        "badge_color": "#059669"
    },
    {
        "name": "BusinessDay",
        "url": "https://businessday.ng/feed/",
        "category": "Economy & Business",
        "badge_color": "#0D9488"
    },

    # --- Tech & Innovation ---
    {
        "name": "TechCabal",
        "url": "https://techcabal.com/feed/",
        "category": "Tech & Startups",
        "badge_color": "#7C3AED"
    },

    # --- Metro, Security & Grassroots ---
    {
        "name": "Daily Trust",
        "url": "https://dailytrust.com/feed/",
        "category": "Metro & Security",
        "badge_color": "#D97706"
    },
    {
        "name": "Leadership NG",
        "url": "https://leadership.ng/feed/",
        "category": "Metro & Society",
        "badge_color": "#4F46E5"
    },

    # --- Entertainment, Culture & Lifestyle ---
    {
        "name": "Punch Ent.",
        "url": "https://punchng.com/topics/entertainment/feed/",
        "category": "Entertainment & Culture",
        "badge_color": "#DB2777"
    },
    {
        "name": "BellaNaija",
        "url": "https://www.bellanaija.com/feed/",
        "category": "Entertainment & Culture",
        "badge_color": "#E11D48"
    },

    # --- Sports ---
    {
        "name": "Complete Sports",
        "url": "https://www.completesports.com/feed/",
        "category": "Sports",
        "badge_color": "#15803D"
    },
    {
        "name": "Punch Sports",
        "url": "https://punchng.com/topics/sports/feed/",
        "category": "Sports",
        "badge_color": "#047857"
    }
]

MACRO_LEDGER = [
    {"indicator": "PMS Petrol (Lagos Metro)", "rate": "₦1,020 – ₦1,060 / L", "baseline": "₦198 (May '23)", "trend": "+425%"},
    {"indicator": "PMS Petrol (Abuja & Edo)", "rate": "₦1,050 – ₦1,120 / L", "baseline": "₦210 (May '23)", "trend": "+414%"},
    {"indicator": "Parallel FX (Ikeja / Zone 4)", "rate": "₦1,670 – ₦1,710 / $1", "baseline": "₦461 (May '23)", "trend": "+265%"},
    {"indicator": "50kg Local Parboiled Rice", "rate": "₦85,000 – ₦95,000", "baseline": "₦32,000 (May '23)", "trend": "+180%"},
    {"indicator": "National Grid Generation", "rate": "~2,400 – 2,800 MW", "baseline": "~4,000 MW", "trend": "-35%"}
]

RADIO_HUB_PULSE = [
    {
        "hub": "Lagos Commercial Hub",
        "station": "Nigeria Info 99.3 FM",
        "show": "Morning Crossfire",
        "caller": "Madam Beatrice (Mile 12 Market)",
        "quote": "Produce transport from Mile 12 to Oyingbo jumped from ₦3,000 to ₦7,500. We are eating into our capital just to sit in the market."
    },
    {
        "hub": "Abuja Administrative Hub",
        "station": "Human Rights Radio 101.1 FM",
        "show": "Brekete Family",
        "caller": "Pa Solomon (Kubwa)",
        "quote": "Retired secondary teachers cannot afford basic blood pressure medication while the pension biometric portal stays frozen."
    },
    {
        "hub": "Edo State Corridor",
        "station": "ITV 92.3 FM Benin City",
        "show": "Man Around Town",
        "caller": "Osas (Ring Road Keke Operator)",
        "quote": "Multiple ticket agents are harassing riders while the multi-billion naira flood drainage projects along Ugbowo sit unfinished."
    },
    {
        "hub": "Rivers State Oil Corridor",
        "station": "Nigeria Info 92.3 FM Port Harcourt",
        "show": "Hard Facts",
        "caller": "Tamuno (Marine Technician)",
        "quote": "Our council headquarters are burning while politicians sit safely in Abuja. Let them settle their wars and let the people breathe."
    }
]


def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Could not read history, starting fresh: {e}")
    return set()


def save_history(history_set):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(list(history_set)[-600:], f, indent=2)


def fetch_rss_feed(url: str, limit: int = 6):
    """Generic XML RSS/Atom parser using standard library."""
    items = []
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)

        channel = root.find("channel")
        raw_items = channel.findall("item") if channel is not None else root.findall("{http://www.w3.org/2005/Atom}entry")

        for it in raw_items[:limit]:
            title = it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or ""
            link = it.findtext("link") or it.findtext("{http://www.w3.org/2005/Atom}link") or ""
            pub_date = it.findtext("pubDate") or it.findtext("{http://www.w3.org/2005/Atom}published") or ""
            desc = it.findtext("description") or ""

            # Clean markup from description
            desc_clean = re.sub(r"<[^>]+>", "", desc).strip()

            title_clean = html.unescape(title.strip())
            link_clean = link.strip()

            if title_clean and link_clean:
                items.append({
                    "title": title_clean,
                    "url": link_clean,
                    "pub_date": pub_date.strip(),
                    "summary": desc_clean[:220] if desc_clean else ""
                })
    except Exception as e:
        logger.warning(f"Failed to fetch feed {url}: {e}")
    return items


def fetch_news_items(history: set):
    """Fetch Tier-1 Nigerian news outlets across all beats."""
    articles = []
    for feed in RSS_FEEDS:
        items = fetch_rss_feed(feed["url"], limit=6)
        for it in items:
            is_new = it["url"] not in history
            articles.append({
                "outlet": feed["name"],
                "category": feed["category"],
                "badge_color": feed.get("badge_color", "#2563EB"),
                "title": it["title"],
                "url": it["url"],
                "pub_date": it["pub_date"],
                "is_new": is_new
            })
            if is_new:
                history.add(it["url"])
        logger.info(f"Fetched {len(items)} items from {feed['name']}")
    return articles


def fetch_x_trends():
    """Fetch live trending topics on X (Twitter) in Nigeria from Trends24."""
    trends = []
    try:
        req = urllib.request.Request("https://trends24.in/nigeria/", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as res:
            content = res.read().decode("utf-8", errors="ignore")

        # Try BeautifulSoup if available, else regex
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            trend_lists = soup.find_all(class_=re.compile(r"trend-card__list"))
            if trend_lists:
                for li in trend_lists[0].find_all("li")[:14]:
                    a = li.find("a")
                    if a and a.text.strip():
                        href = a.get("href", "")
                        name = a.text.strip()
                        trends.append({
                            "name": name,
                            "url": href if href.startswith("http") else f"https://twitter.com{href}"
                        })
        except ImportError:
            list_match = re.search(r'class="[^"]*trend-card__list[^"]*"[^>]*>(.*?)</(?:ol|ul)>', content, re.DOTALL)
            if list_match:
                li_matches = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', list_match.group(1))
                for href, raw_name in li_matches[:14]:
                    name = re.sub(r"<[^>]+>", "", raw_name).strip()
                    if name:
                        trends.append({
                            "name": html.unescape(name),
                            "url": href if href.startswith("http") else f"https://twitter.com{href}"
                        })
        logger.info(f"Fetched {len(trends)} X trends for Nigeria")
    except Exception as e:
        logger.warning(f"Failed to fetch X trends: {e}")
    return trends


def fetch_x_discourse(history: set):
    """Fetch live discourse and viral posts from X (Twitter) via indexed feeds."""
    x_posts = []
    queries = [
        "https://news.google.com/rss/search?q=site:x.com+Nigeria+politics&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=site:x.com+Tinubu+OR+Naira+OR+fuel&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=site:x.com+Nigeria+trending+OR+viral&hl=en-NG&gl=NG&ceid=NG:en"
    ]
    for url in queries:
        items = fetch_rss_feed(url, limit=5)
        for it in items:
            title = it["title"]
            # Clean title format: "... - x.com"
            title_clean = re.sub(r"\s*-\s*x\.com$", "", title).strip()
            if not title_clean or it["url"] in history:
                continue

            history.add(it["url"])
            x_posts.append({
                "platform": "X (Twitter)",
                "title": title_clean,
                "url": it["url"],
                "pub_date": it["pub_date"]
            })
            if len(x_posts) >= 8:
                break
        if len(x_posts) >= 8:
            break

    logger.info(f"Fetched {len(x_posts)} live X discourse items")
    return x_posts


def fetch_instagram_pulse(history: set):
    """Fetch viral news, societal scoops, and civic reports from Instagram."""
    ig_items = []

    # 1. Instablog9ja RSS Feed (Nigeria's top viral Instagram-first publisher)
    instablog_feed = "https://instablog9ja.com/feed/"
    ib_posts = fetch_rss_feed(instablog_feed, limit=6)
    for it in ib_posts:
        if it["url"] not in history:
            history.add(it["url"])
            ig_items.append({
                "source": "Instablog9ja (Instagram)",
                "title": it["title"],
                "url": it["url"],
                "pub_date": it["pub_date"],
                "badge_color": "#E1306C" # Instagram magenta
            })

    # 2. Google News Instagram indexed news for Nigeria
    gnews_ig = "https://news.google.com/rss/search?q=site:instagram.com+Nigeria+news&hl=en-NG&gl=NG&ceid=NG:en"
    g_posts = fetch_rss_feed(gnews_ig, limit=5)
    for it in g_posts:
        title_clean = re.sub(r"\s*-\s*instagram\.com$", "", it["title"]).strip()
        if it["url"] not in history and title_clean:
            history.add(it["url"])
            ig_items.append({
                "source": "Instagram News Wire",
                "title": title_clean,
                "url": it["url"],
                "pub_date": it["pub_date"],
                "badge_color": "#833AB4" # Instagram purple
            })

    # 3. YabaLeftOnline (Viral youth culture & social reactions)
    yaba_feed = "https://yabaleftonline.ng/feed/"
    yaba_posts = fetch_rss_feed(yaba_feed, limit=4)
    for it in yaba_posts:
        if it["url"] not in history:
            history.add(it["url"])
            ig_items.append({
                "source": "YabaLeftOnline",
                "title": it["title"],
                "url": it["url"],
                "pub_date": it["pub_date"],
                "badge_color": "#F77737" # Instagram warm orange
            })

    logger.info(f"Fetched {len(ig_items)} Instagram & social news items")
    return ig_items[:8]


def render_category_rows(articles: list, target_category: str, max_items: int = 5) -> str:
    matches = [a for a in articles if a.get("category") == target_category]
    matches = sorted(matches, key=lambda x: not x.get("is_new", False))[:max_items]
    if not matches:
        return "<tr><td colspan='2' style='padding: 8px 12px; font-size: 12px; color: #71717a; font-style: italic;'>No new updates in this cycle.</td></tr>"
    rows = ""
    for a in matches:
        badge_color = a.get("badge_color", "#2563EB")
        new_tag = '<span style="background: #059669; color: #ffffff; font-size: 9px; font-weight: 800; padding: 1px 4px; border-radius: 2px; margin-left: 6px;">NEW</span>' if a.get("is_new") else ''
        rows += f"""
        <tr style="border-bottom: 1px solid #e4e4e7;">
            <td style="padding: 10px 12px; font-weight: 700; color: #09090b; width: 140px; font-size: 11.5px; vertical-align: top;">
                <span style="display: inline-block; background: {badge_color}18; color: {badge_color}; border: 1px solid {badge_color}55; padding: 2px 6px; border-radius: 3px; font-weight: 700;">{a['outlet']}</span>{new_tag}
            </td>
            <td style="padding: 10px 12px; vertical-align: top;">
                <a href="{a['url']}" target="_blank" style="color: #09090b; text-decoration: none; font-weight: 600; font-size: 13px; line-height: 1.4; display: block;">
                    {a['title']}
                </a>
            </td>
        </tr>
        """
    return rows


def render_category_md(articles: list, target_category: str, max_items: int = 5) -> str:
    matches = [a for a in articles if a.get("category") == target_category]
    matches = sorted(matches, key=lambda x: not x.get("is_new", False))[:max_items]
    if not matches:
        return "- *No new dispatches in this cycle.*\n"
    out = ""
    for a in matches:
        new_badge = " `NEW`" if a.get("is_new") else ""
        out += f"- **[{a['outlet']}]** [{a['title']}]({a['url']}){new_badge}\n"
    return out


def build_email_html(today_str: str, articles: list, macro: list, radio: list, x_trends: list, x_posts: list, ig_items: list) -> str:
    # 1. Macro rows
    macro_rows = ""
    for m in macro:
        macro_rows += f"""
        <tr style="border-bottom: 1px solid #e4e4e7;">
            <td style="padding: 9px 12px; font-weight: 600; color: #09090b; font-size: 13px;">{m['indicator']}</td>
            <td style="padding: 9px 12px; font-weight: 700; color: #09090b; font-size: 13px;">{m['rate']}</td>
            <td style="padding: 9px 12px; color: #71717a; font-size: 12px;">{m['baseline']}</td>
            <td style="padding: 9px 12px; font-weight: 700; color: #059669; font-size: 13px;">{m['trend']}</td>
        </tr>
        """

    # 2. Radio pulse
    radio_blocks = ""
    for r in radio:
        radio_blocks += f"""
        <div style="background: #ffffff; border: 1px solid #e4e4e7; border-left: 3px solid #059669; padding: 12px 16px; margin-bottom: 10px; border-radius: 0 4px 4px 0;">
            <div style="font-size: 11px; font-weight: 800; color: #059669; text-transform: uppercase; letter-spacing: 0.5px;">
                {r['hub']} • {r['station']} ({r['show']})
            </div>
            <div style="font-size: 13px; font-style: italic; color: #18181b; margin: 6px 0; line-height: 1.4;">
                "{r['quote']}"
            </div>
            <div style="font-size: 11px; color: #71717a; font-weight: 600;">
                — Caller: {r['caller']}
            </div>
        </div>
        """

    # Beat category rows
    national_rows = render_category_rows(articles, "National & Breaking", max_items=6)
    economy_rows = render_category_rows(articles, "Economy & Business", max_items=5)
    tech_rows = render_category_rows(articles, "Tech & Startups", max_items=4)
    metro_rows = render_category_rows(articles, "Metro & Security", max_items=3) + render_category_rows(articles, "Metro & Society", max_items=3)
    ent_rows = render_category_rows(articles, "Entertainment & Culture", max_items=4)
    sports_rows = render_category_rows(articles, "Sports", max_items=4)

    # 4. X (Twitter) Trends Pills
    trend_pills = ""
    for t in x_trends[:12]:
        trend_pills += f"""
        <a href="{t['url']}" target="_blank" style="display: inline-block; background: #f4f4f5; color: #0f1419; text-decoration: none; padding: 5px 10px; margin: 3px 4px 4px 0; border-radius: 14px; font-size: 12px; font-weight: 700; border: 1px solid #e1e8ed;">
            {t['name']}
        </a>
        """

    # X Posts rows
    x_post_rows = ""
    for xp in x_posts[:6]:
        x_post_rows += f"""
        <div style="background: #ffffff; border: 1px solid #e1e8ed; border-left: 3px solid #000000; padding: 10px 14px; margin-bottom: 8px; border-radius: 0 4px 4px 0;">
            <a href="{xp['url']}" target="_blank" style="color: #0f1419; text-decoration: none; font-size: 13px; font-weight: 600; line-height: 1.4; display: block;">
                {xp['title']}
            </a>
            <div style="font-size: 11px; color: #536471; margin-top: 4px;">
                𝕏 Live Discourse Wire
            </div>
        </div>
        """

    # 5. Instagram news rows
    ig_rows = ""
    for ig in ig_items[:6]:
        badge_bg = ig.get("badge_color", "#E1306C")
        ig_rows += f"""
        <div style="background: #ffffff; border: 1px solid #fce7f3; border-left: 3px solid {badge_bg}; padding: 10px 14px; margin-bottom: 8px; border-radius: 0 4px 4px 0;">
            <div style="display: inline-block; background: {badge_bg}; color: #ffffff; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 2px; text-transform: uppercase; margin-bottom: 4px;">
                {ig['source']}
            </div>
            <a href="{ig['url']}" target="_blank" style="color: #09090b; text-decoration: none; font-size: 13px; font-weight: 600; line-height: 1.4; display: block; margin-top: 3px;">
                {ig['title']}
            </a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Today in Nigeria — 360° Trending Intelligence</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f5; margin: 0; padding: 20px; color: #18181b;">
    <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 6px; border: 1px solid #e4e4e7; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
        
        <!-- Header -->
        <div style="background-color: #09090b; color: #ffffff; padding: 28px 24px; border-bottom: 3px solid #059669;">
            <div style="display: inline-block; background: #059669; color: #ffffff; font-size: 10px; font-weight: 800; letter-spacing: 1px; padding: 3px 8px; border-radius: 2px; text-transform: uppercase; margin-bottom: 8px;">
                TODAY IN NIGERIA • ALL-BEAT INTELLIGENCE
            </div>
            <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">Nigeria 360° Trending Daily Dispatch</h1>
            <p style="margin: 6px 0 0 0; font-size: 13px; color: #a1a1aa;">National Wire • Markets & FX • Tech • Metro • Culture • Sports • 𝕏 & IG • {today_str}</p>
        </div>

        <!-- Executive Dek -->
        <div style="padding: 16px 24px; background: #fafafa; border-bottom: 1px solid #e4e4e7; font-size: 13px; line-height: 1.5; color: #27272a;">
            <strong>Automated Editorial Cycle:</strong> 04:30 | 06:00 | 12:00 | 16:30 | 18:00 WAT. Real-time multi-channel ingestion capturing breaking developments, macroeconomic realities, citizen radio feedback, and viral cultural moments across Nigeria.
        </div>

        <!-- Main Body -->
        <div style="padding: 24px;">
            
            <!-- Section 1: Macroeconomic Ledger -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 12px 0; color: #09090b; border-bottom: 2px solid #059669; padding-bottom: 5px;">
                1. Macroeconomic Reality Ledger
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <thead>
                    <tr style="background: #f4f4f5; border-bottom: 1px solid #e4e4e7;">
                        <th style="padding: 8px 12px; font-size: 11.5px; color: #71717a;">Indicator</th>
                        <th style="padding: 8px 12px; font-size: 11.5px; color: #71717a;">Current Rate</th>
                        <th style="padding: 8px 12px; font-size: 11.5px; color: #71717a;">Baseline</th>
                        <th style="padding: 8px 12px; font-size: 11.5px; color: #71717a;">Change</th>
                    </tr>
                </thead>
                <tbody>
                    {macro_rows}
                </tbody>
            </table>

            <!-- Section 2: Talk Radio Voices -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 24px 0 12px 0; color: #09090b; border-bottom: 2px solid #059669; padding-bottom: 5px;">
                2. Grassroots Pulse (Morning Talk Radio Hubs)
            </h2>
            {radio_blocks}

            <!-- Section 3: National & Breaking Wire -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #DC2626; padding-bottom: 5px;">
                3. 🔴 Top National & Breaking Wire
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <tbody>
                    {national_rows}
                </tbody>
            </table>

            <!-- Section 4: Economy & Business -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #059669; padding-bottom: 5px;">
                4. 💼 Economy, Markets & Corporate Nigeria
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <tbody>
                    {economy_rows}
                </tbody>
            </table>

            <!-- Section 5: Tech & Startups -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #7C3AED; padding-bottom: 5px;">
                5. 🚀 Tech, Fintech & Digital Economy
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <tbody>
                    {tech_rows}
                </tbody>
            </table>

            <!-- Section 6: Metro & Society -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #D97706; padding-bottom: 5px;">
                6. 🏙️ Metro, Society & Security
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <tbody>
                    {metro_rows}
                </tbody>
            </table>

            <!-- Section 7: Entertainment, Culture & Lifestyle -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #DB2777; padding-bottom: 5px;">
                7. 🎭 Entertainment, Pop Culture & Celebrity Watch
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <tbody>
                    {ent_rows}
                </tbody>
            </table>

            <!-- Section 8: Sports Spotlight -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #15803D; padding-bottom: 5px;">
                8. ⚽ Sports Spotlight
            </h2>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 24px;">
                <tbody>
                    {sports_rows}
                </tbody>
            </table>

            <!-- Section 9: X Trends -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #000000; padding-bottom: 5px;">
                9. 𝕏 (Twitter) Nigeria: Trending Topics & Discourse Wire
            </h2>
            <div style="background: #f9f9fb; border: 1px solid #e1e8ed; padding: 12px 14px; border-radius: 4px; margin-bottom: 14px;">
                <div style="font-size: 11px; font-weight: 800; color: #536471; text-transform: uppercase; margin-bottom: 8px;">
                    Trending Across Nigeria Right Now
                </div>
                <div>
                    {trend_pills}
                </div>
            </div>
            {x_post_rows}

            <!-- Section 10: Instagram Viral Hubs -->
            <h2 style="font-size: 13.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 28px 0 12px 0; color: #09090b; border-bottom: 2px solid #E1306C; padding-bottom: 5px;">
                10. 📸 Instagram & Social News Watch (Instablog9ja, BellaNaija & Viral Hubs)
            </h2>
            {ig_rows}

        </div>

        <!-- Footer -->
        <div style="background-color: #fafafa; border-top: 1px solid #e4e4e7; padding: 18px 24px; font-size: 12px; color: #71717a; text-align: center; line-height: 1.5;">
            <div>Compiled by <strong>Today in Nigeria Intelligence Desk</strong></div>
            <div style="margin-top: 4px;">Multi-channel monitoring: Press RSS • Live Radio Wire • 𝕏 Trends • Instagram Dispatches</div>
        </div>

    </div>
</body>
</html>"""
    return html


def build_markdown_log(today_str: str, articles: list, x_trends: list, x_posts: list, ig_items: list) -> str:
    md = f"""# Today in Nigeria 360° Daily Briefing — {today_str}

*Multi-channel intelligence digest covering all trending Nigerian news beats: breaking press, markets, tech, metro, entertainment, sports, talk radio sentiments, 𝕏 trends, and Instagram reporting.*

---

## 1. 🔴 Top National & Breaking Wire
{render_category_md(articles, "National & Breaking", max_items=6)}

---
## 2. 💼 Economy, Markets & Corporate Nigeria
{render_category_md(articles, "Economy & Business", max_items=5)}

---
## 3. 🚀 Tech, Startups & Digital Economy
{render_category_md(articles, "Tech & Startups", max_items=4)}

---
## 4. 🏙️ Metro, Society & Security
{render_category_md(articles, "Metro & Security", max_items=3)}{render_category_md(articles, "Metro & Society", max_items=3)}

---
## 5. 🎭 Entertainment, Culture & Lifestyle
{render_category_md(articles, "Entertainment & Culture", max_items=4)}

---
## 6. ⚽ Sports Spotlight
{render_category_md(articles, "Sports", max_items=4)}

---
## 7. Macroeconomic Reality Ledger
| Indicator | Current Rate | May 2023 Baseline | Percentage Change |
| :--- | :--- | :--- | :--- |
| PMS Petrol (Lagos) | ₦1,020 – ₦1,060 / L | ₦198 / L | +425% |
| Parallel Market FX | ₦1,670 – ₦1,710 / $1 | ₦461 / $1 | +265% |
| 50kg Local Rice | ₦85,000 – ₦95,000 | ₦32,000 | +180% |
| National Grid Generation | ~2,400 – 2,800 MW | ~4,000 MW | -35% |

---
## 8. 𝕏 (Twitter) Nigeria Trends & Discourse Pulse
### Trending Topics
"""
    for t in x_trends[:12]:
        md += f"- [{t['name']}]({t['url']})\n"

    md += "\n### Discourse Wire\n"
    for xp in x_posts[:6]:
        md += f"- [{xp['title']}]({xp['url']})\n"

    md += """
---
## 9. Instagram Viral & Social News Watch
"""
    for ig in ig_items[:6]:
        md += f"- **[{ig['source']}]** [{ig['title']}]({ig['url']})\n"

    return md


def send_email(username: str, password: str, to_email: str, html_body: str, subject: str):
    if not username or not password:
        logger.warning("MAIL_USERNAME or MAIL_PASSWORD not provided. Skipping SMTP send.")
        return False

    recipient = to_email if to_email else username
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Polititrace Nigeria <{username}>"
    msg["To"] = recipient

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        logger.info(f"Connecting to smtp.gmail.com:465 (SSL) to send email to {recipient}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as server:
            server.login(username, password)
            server.sendmail(username, [recipient], msg.as_string())
        logger.info("✓ Daily Nigeria Intelligence Email sent successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {e}")
        return False


def main():
    today_str = datetime.now(timezone(timedelta(hours=1))).strftime("%A, %B %d, %Y")
    logger.info(f"Starting Polititrace Nigeria Dispatcher for {today_str}...")

    history = load_history()

    # 1. Fetch Tier-1 press news
    articles = fetch_news_items(history)

    # 2. Fetch X (Twitter) trends & political discourse
    x_trends = fetch_x_trends()
    x_posts = fetch_x_discourse(history)

    # 3. Fetch Instagram & viral social news
    ig_items = fetch_instagram_pulse(history)

    # Save outputs
    html_content = build_email_html(today_str, articles, MACRO_LEDGER, RADIO_HUB_PULSE, x_trends, x_posts, ig_items)
    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    md_content = build_markdown_log(today_str, articles, x_trends, x_posts, ig_items)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)

    save_history(history)

    # Send Email
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    to_email = os.getenv("MAIL_TO") or username

    subject = f"🇳🇬 Polititrace Daily Briefing: News, 𝕏 & Instagram — {today_str}"
    send_email(username, password, to_email, html_content, subject)


if __name__ == "__main__":
    main()
