import os
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger("notifiers")

def send_discord_notification(webhook_url: str, updates: list[dict]):
    """
    Sends batched notifications to Discord via webhook.
    """
    if not webhook_url or not updates:
        return

    # Discord allows max 10 embeds per message
    batch_size = 10
    for i in range(0, len(updates), batch_size):
        chunk = updates[i:i + batch_size]
        embeds = []
        for item in chunk:
            embed = {
                "title": f"📢 {item['project']}: {item['title'][:200]}",
                "url": item["url"],
                "color": 0x3498DB if "Engine" in item.get("category", "") else 0x2ECC71,
                "fields": [
                    {"name": "Project", "value": item["project"], "inline": True},
                    {"name": "Category", "value": item.get("category", "General"), "inline": True},
                    {"name": "Date & Time", "value": item["formatted_time"], "inline": False}
                ],
                "footer": {"text": f"Source: {item.get('source_type', 'Tracker')}"}
            }
            embeds.append(embed)

        payload = {
            "content": f"🚨 **New Open Source Updates ({len(chunk)})**",
            "embeds": embeds
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=15)
            if resp.status_code in [200, 204]:
                logger.info(f"Discord notification sent successfully ({len(chunk)} items).")
            else:
                logger.error(f"Failed to send Discord notification: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error sending Discord webhook: {e}")

def send_telegram_notification(bot_token: str, chat_id: str, updates: list[dict]):
    """
    Sends formatted notifications via Telegram Bot.
    """
    if not bot_token or not chat_id or not updates:
        return

    for item in updates:
        text = (
            f"🚀 <b>{item['project']}</b>\n"
            f"📌 <b>Title:</b> {item['title']}\n"
            f"📁 <b>Category:</b> {item.get('category', 'Open Source')}\n"
            f"🕒 <b>Date & Time:</b> {item['formatted_time']}\n"
            f"🔗 <a href=\"{item['url']}\">Read Details / Release</a>"
        )
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                logger.info(f"Telegram alert sent for {item['project']}.")
            else:
                logger.error(f"Telegram error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

def update_markdown_log(log_path: str, updates: list[dict]):
    """
    Updates the markdown changelog table with new updates.
    """
    if not updates:
        return

    header = "# 📡 Open Source Release & News Tracker Log\n\n| Date & Time (UTC) | Project | Category | Update / Release | Source |\n|---|---|---|---|---|\n"
    
    existing_content = ""
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

    new_rows = []
    for item in updates:
        row = f"| {item['formatted_time']} | **{item['project']}** | {item.get('category', '-')} | [{item['title']}]({item['url']}) | {item.get('source_type', '-')} |"
        new_rows.append(row)

    if not existing_content.startswith("# 📡 Open Source"):
        content = header + "\n".join(new_rows) + "\n"
    else:
        # Insert right after header table
        parts = existing_content.split("|---|---|---|---|---|\n", 1)
        if len(parts) == 2:
            content = parts[0] + "|---|---|---|---|---|\n" + "\n".join(new_rows) + "\n" + parts[1]
        else:
            content = existing_content + "\n" + "\n".join(new_rows)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Updated markdown log at {log_path}")

def log_github_summary(updates: list[dict]):
    """
    Appends updates to GITHUB_STEP_SUMMARY when running inside GitHub Actions.
    """
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file or not updates:
        return

    try:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(f"\n## 🔔 Open Source Updates Detected ({len(updates)})\n\n")
            f.write("| Date & Time | Project | Category | Release / Update |\n")
            f.write("|---|---|---|---|\n")
            for item in updates:
                f.write(f"| {item['formatted_time']} | **{item['project']}** | {item.get('category', '-')} | [{item['title']}]({item['url']}) |\n")
        logger.info("GitHub Step Summary updated.")
    except Exception as e:
        logger.error(f"Failed to write to GITHUB_STEP_SUMMARY: {e}")
