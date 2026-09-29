# 🚀 Automated Open Source Release & News Tracker for YouTube

A lightweight, automated system that monitors open-source game engines, creative software (video editors, 3D tools), and major open-source releases to give you instant, timely alerts with **Project Name**, **Date & Time of Update**, and **Direct Links**.

---

## 📋 What It Tracks Out-of-the-Box

1. **Open Source Game Engines & Frameworks:**
   - **Godot Engine** (Releases & official dev snapshots / blog)
   - **Bevy Engine**
   - **Raylib**
   - **Defold**
   - **O3DE (Open 3D Engine)**

2. **Open Source Video Editors & Creative Software:**
   - **Blender** (GitHub releases & official news feed)
   - **Kdenlive**
   - **Shotcut**
   - **OpenShot**
   - **OBS Studio**
   - **Audacity**
   - **FreeCAD**

3. **Programming Languages & Runtimes (Your Stack):**
   - **Python** (`python/cpython` + Python Insider Blog)
   - **TypeScript** (`microsoft/TypeScript` + Official Microsoft TypeScript DevBlog)
   - **Kotlin** (`JetBrains/kotlin` + Official JetBrains Kotlin Blog)
   - **JavaScript** (`nodejs/node` + `oven-sh/bun`)
   - **C / C++** (`llvm/llvm-project` - LLVM & Clang compiler toolchains)
   - **Rust Language** (`rust-lang/rust`)

4. **Game Streaming, Physics & 2D Animation:**
   - **Sunshine** (`LizardByte/Sunshine`)
   - **Box2D Physics** (`erincatto/box2d`)
   - **OpenToonz** (`opentoonz/opentoonz`)

5. **Major Open Source & Developer Tech:**
   - **Linux Kernel**
   - **Rust Language**
   - **Neovim**
   - **Phoronix** (Linux, GPU drivers, benchmarks, open-source hardware news)

4. **Community Discussions & Release Buzz:**
   - **Reddit r/opensource** (Hot posts > 25 upvotes)
   - **Reddit r/gamedev** (Engine/tool announcements > 40 upvotes)
   - **Hacker News** (Top trending release announcements > 50 points)

---

## 🔔 Setting Up Instant Free Alerts

You can choose either **Discord Webhook** or **Telegram Bot** (or both!). Both are 100% free and send instant push notifications to your phone and desktop so you never miss a breaking release.

### Option A: Discord Webhook (Recommended & Easiest)
1. In your Discord server, right-click any text channel (or create a private `#youtube-news-alerts` channel).
2. Click **Edit Channel** (gear icon) ➡️ **Integrations** ➡️ **Webhooks** ➡️ **New Webhook**.
3. Name it `Open Source News Bot` and click **Copy Webhook URL**.
4. In GitHub, go to your repository:
   - **Settings** ➡️ **Secrets and variables** ➡️ **Actions** ➡️ **New repository secret**.
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: paste your Discord Webhook URL.

### Option B: Telegram Bot
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, follow the prompts, and copy the **Bot Token**.
3. Start a chat with your bot or add it to a channel/group.
4. Get your Chat ID (using `@userinfobot` or `@RawDataBot`).
5. In GitHub Secrets:
   - Add secret `TELEGRAM_BOT_TOKEN`
   - Add secret `TELEGRAM_CHAT_ID`

---

## ⚙️ How the GitHub Action Works

The workflow is located in [`.github/workflows/track_opensource.yml`](file:///c:/Users/DELL/Desktop/school_stuff/EEE532/.github/workflows/track_opensource.yml):

- **Automatic Schedule**: Runs automatically every 6 hours (`cron: '0 */6 * * *'`).
- **Manual Trigger**: You can run it anytime manually with one click from GitHub Actions (Actions tab ➡️ select "Open Source News & Release Tracker" ➡️ **Run workflow**).
- **Persistent State**: Maintains `seen_history.json` and updates [`latest_updates.md`](file:///c:/Users/DELL/Desktop/school_stuff/EEE532/opensource_tracker/latest_updates.md) in the repository so you only receive alerts for *new* items and never get spammed with duplicates.

---

## ➕ Adding More Projects

To track any new project, just open [`opensource_tracker/config.json`](file:///c:/Users/DELL/Desktop/school_stuff/EEE532/opensource_tracker/config.json) and add it:

### Adding a GitHub Repository:
```json
{
  "name": "Godot Engine",
  "repo": "godotengine/godot",
  "category": "Game Engine"
}
```

### Adding an RSS / Blog Feed:
```json
{
  "name": "Blender News",
  "url": "https://www.blender.org/feed/",
  "category": "3D & Video"
}
```

---

## 💻 Running Locally

You can also run it locally on your computer at any time:

```bash
# Optional: test with your Discord webhook locally
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python opensource_tracker/tracker.py
```
