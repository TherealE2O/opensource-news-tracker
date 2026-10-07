#!/usr/bin/env python3
"""
On-Demand Local Broadcast Transcriber for Nigerian TV & Talk Radio YouTube Streams.
Bypasses YouTube's delayed auto-captions by combining fast caption API check
with an instant local audio rip (yt-dlp + ffmpeg) and local OpenAI Whisper transcription.
"""
import os
import sys
import re
import argparse
import tempfile
import logging
from datetime import datetime, timezone, timedelta

# Ensure UTF-8 output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("broadcast_transcriber")

# Ensure ffmpeg binary in antigravity path is available if not in system PATH
ANTIGRAVITY_BIN = os.path.expanduser(r"~\.gemini\antigravity\bin")
if os.path.exists(ANTIGRAVITY_BIN) and ANTIGRAVITY_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ANTIGRAVITY_BIN + os.pathsep + os.environ.get("PATH", "")


def extract_video_id(url_or_id: str) -> str:
    """Extract 11-char YouTube video ID from URL or bare ID."""
    match = re.search(r"(?:v=|\/|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})", url_or_id)
    if match:
        return match.group(1)
    if len(url_or_id) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", url_or_id):
        return url_or_id
    return url_or_id


def try_fetch_youtube_captions(video_id: str):
    """Attempt fast caption extraction via youtube_transcript_api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        logger.info(f"Checking YouTube cloud captions for [{video_id}]...")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
        if transcript_list:
            logger.info("✓ Cloud captions available and fetched in seconds!")
            return transcript_list
    except Exception as e:
        logger.info(f"Cloud captions not available yet ({e}). Switching to local Whisper pipeline.")
    return None


def download_audio_stream(youtube_url: str, output_path: str, max_minutes: int = None) -> bool:
    """Download audio stream via yt_dlp."""
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt_dlp is required. Install via pip install yt-dlp")
        return False

    ydl_opts = {
        'format': 'bestaudio/ba',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }

    if max_minutes:
        # Download only up to max_minutes using ffmpeg download section
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(0, max_minutes * 60)])
        ydl_opts['force_keyframes_at_cuts'] = True

    logger.info(f"Downloading broadcast audio stream via yt-dlp...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        return True
    except Exception as e:
        logger.error(f"Failed to download audio: {e}")
        return False


def transcribe_audio_locally(audio_file: str, model_name: str = "base") -> list:
    """Transcribe audio using local OpenAI Whisper."""
    try:
        import whisper
    except ImportError:
        logger.error("openai-whisper is not installed. Install via pip install openai-whisper")
        return []

    logger.info(f"Loading Whisper model '{model_name}' on local machine...")
    model = whisper.load_model(model_name)

    logger.info(f"Transcribing audio file locally: {audio_file}...")
    result = model.transcribe(audio_file, fp16=False, language="en")
    
    segments = []
    for s in result.get("segments", []):
        segments.append({
            "start": s.get("start", 0),
            "end": s.get("end", 0),
            "text": s.get("text", "").strip()
        })
    return segments


def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def generate_editorial_takeaways(segments: list, max_points: int = 5) -> list:
    """Extract key sentences and speaking moments from transcript segments."""
    if not segments:
        return ["No speech detected in broadcast snippet."]
    
    # Filter non-trivial sentences
    key_lines = []
    for s in segments:
        text = s["text"]
        if len(text.split()) >= 6:
            key_lines.append(f"[{format_timestamp(s['start'])}] {text}")
        if len(key_lines) >= max_points:
            break
            
    return key_lines if key_lines else [f"[{format_timestamp(segments[0]['start'])}] {segments[0]['text']}"]


def transcribe_broadcast(
    youtube_url_or_id: str,
    output_md: str = None,
    whisper_model: str = "base",
    max_minutes: int = 20
) -> dict:
    """
    Main orchestration:
    1. Try youtube_transcript_api (cloud captions)
    2. Fallback to local yt-dlp + Whisper (instant local transcription)
    3. Generate talking points & save markdown briefing.
    """
    video_id = extract_video_id(youtube_url_or_id)
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(f"Initiating on-demand transcription for: {clean_url}")

    segments = try_fetch_youtube_captions(video_id)
    source_type = "YouTube Auto-Captions (Cloud)"

    if not segments:
        logger.info("Falling back to instant local audio download + Whisper...")
        source_type = f"Local Whisper ({whisper_model}) via yt-dlp"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_base = os.path.join(temp_dir, f"audio_{video_id}")
            wav_path = f"{temp_base}.wav"

            success = download_audio_stream(clean_url, temp_base, max_minutes=max_minutes)
            if not success or not os.path.exists(wav_path):
                # Try finding any audio file in temp_dir
                files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith(('.wav', '.mp3', '.m4a', '.webm'))]
                if files:
                    wav_path = files[0]
                else:
                    logger.error("Audio download failed. Could not locate extracted audio.")
                    return {"success": False, "error": "Audio extraction failed"}

            raw_segments = transcribe_audio_locally(wav_path, model_name=whisper_model)
            segments = []
            for s in raw_segments:
                segments.append({
                    "start": s["start"],
                    "duration": s["end"] - s["start"],
                    "text": s["text"]
                })

    if not segments:
        return {"success": False, "error": "Transcription returned empty result"}

    # Assemble transcript text
    full_text_lines = []
    for s in segments:
        start_time = format_timestamp(s["start"])
        full_text_lines.append(f"**[{start_time}]** {s['text']}")

    full_transcript_str = "\n\n".join(full_text_lines)
    takeaways = generate_editorial_takeaways(segments, max_points=6)

    # Date header
    now_str = datetime.now(timezone(timedelta(hours=1))).strftime("%A, %B %d, %Y - %H:%M WAT")

    md_report = f"""# Broadcast Intelligence Briefing
**Source:** [{clean_url}]({clean_url})
**Engine:** {source_type}
**Captured At:** {now_str}

---

## 🎯 Executive Talking Points & Angle
"""
    for pt in takeaways:
        md_report += f"- {pt}\n"

    md_report += f"""
---

## 🎙️ Verbatim Timed Transcript
{full_transcript_str}
"""

    if output_md:
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(md_report)
        logger.info(f"✓ Saved transcript briefing to: {output_md}")

    return {
        "success": True,
        "video_id": video_id,
        "source": source_type,
        "takeaways": takeaways,
        "transcript": full_transcript_str,
        "markdown": md_report
    }


def main():
    parser = argparse.ArgumentParser(description="On-demand local TV/Radio YouTube transcriber")
    parser.add_argument("url", help="YouTube video URL or Video ID (e.g. Channels TV, Arise, Nigeria Info)")
    parser.add_argument("--output", "-o", default=None, help="Output markdown file path")
    parser.add_argument("--model", "-m", default="base", help="Whisper model (tiny, base, small)")
    parser.add_argument("--minutes", type=int, default=15, help="Max minutes to download if using local audio rip")
    args = parser.parse_args()

    out_file = args.output
    if not out_file:
        video_id = extract_video_id(args.url)
        out_file = f"transcript_{video_id}.md"

    res = transcribe_broadcast(args.url, output_md=out_file, whisper_model=args.model, max_minutes=args.minutes)
    if res.get("success"):
        print("\n" + "="*50)
        print("BROADCAST INTELLIGENCE GENERATED")
        print("="*50)
        for pt in res["takeaways"]:
            print(f"• {pt}")
        print("="*50)
        print(f"Full transcript written to: {out_file}\n")
    else:
        print(f"Error: {res.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
