import os
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from datetime import datetime

logger = logging.getLogger("notifiers")

def send_email_notification(username: str, password: str, to_email: str | None, updates: list[dict]):
    """
    Sends email notifications via Gmail SMTP (SSL 465).
    """
    if not username or not password or not updates:
        return

    recipient = to_email if to_email else username
    subject = f"🚨 Open Source News: {len(updates)} New Update(s) Detected"

    # Plain text fallback
    text_lines = [f"Open Source News Tracker - {len(updates)} New Update(s)\n"]
    for u in updates:
        text_lines.append(f"• [{u.get('category', 'Tech')}] {u['project']}: {u['title']}")
        text_lines.append(f"  Time: {u['formatted_time']}")
        text_lines.append(f"  Link: {u['url']}\n")
    plain_text = "\n".join(text_lines)

    # HTML formatted email
    rows_html = ""
    for u in updates:
        rows_html += f"""
        <tr style="border-bottom: 1px solid #e1e4e8;">
            <td style="padding: 10px 12px; font-weight: bold; color: #24292e;">{u['project']}</td>
            <td style="padding: 10px 12px; color: #586069; font-size: 13px;">{u.get('category', 'General')}</td>
            <td style="padding: 10px 12px; color: #0366d6;"><a href="{u['url']}" style="color: #0366d6; text-decoration: none; font-weight: 500;">{u['title']}</a></td>
            <td style="padding: 10px 12px; color: #6a737d; font-size: 13px;">{u['formatted_time']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6f8fa; margin: 0; padding: 20px;">
        <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #d1d5da; overflow: hidden;">
            <div style="background-color: #24292e; color: #ffffff; padding: 16px 20px;">
                <h2 style="margin: 0; font-size: 18px;">📡 Open Source YouTube News Digest</h2>
                <p style="margin: 4px 0 0 0; font-size: 13px; color: #cfd3d6;">{len(updates)} new open-source release(s) or article(s) detected.</p>
            </div>
            <div style="padding: 20px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="background-color: #f1f3f5; border-bottom: 2px solid #e1e4e8;">
                            <th style="padding: 10px 12px; font-size: 13px; color: #444d56;">Project</th>
                            <th style="padding: 10px 12px; font-size: 13px; color: #444d56;">Category</th>
                            <th style="padding: 10px 12px; font-size: 13px; color: #444d56;">Title / Release</th>
                            <th style="padding: 10px 12px; font-size: 13px; color: #444d56;">Date (UTC)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            <div style="background-color: #fafbfc; border-top: 1px solid #eaecef; padding: 12px 20px; font-size: 12px; color: #586069; text-align: center;">
                Generated automatically by <a href="https://github.com/TherealE2O/opensource-news-tracker" style="color: #0366d6;">opensource-news-tracker</a>.
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Open Source Tracker <{username}>"
    msg["To"] = recipient

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(username, password)
            server.sendmail(username, [recipient], msg.as_string())
        logger.info(f"Email alert sent successfully to {recipient} ({len(updates)} updates).")
    except Exception as e:
        logger.error(f"Failed to send email alert via Gmail SMTP: {e}")


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
