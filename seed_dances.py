"""
Dance Platform seeder — classifies dance names via Ollama and finds tutorial
videos on YouTube and TikTok using yt-dlp, then seeds the database via the API.

Requires: yt-dlp  (pip install yt-dlp)

Usage:
  python seed_dances.py                  # interactive — paste names or YouTube URL+timestamps
  python seed_dances.py names.txt        # one dance name per line
  python seed_dances.py video.txt        # YouTube URL + "Dance Name [MM:SS]" timestamps

Timestamp file format:
  https://youtube.com/watch?v=VIDEO_ID
  Running Man [00:29]
  Cabbage Patch [01:04]
"""

import sys
import re
import json
import getpass
import subprocess
import urllib.request
import urllib.error

API_BASE   = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

YT_RE    = re.compile(r"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})")
ENTRY_RE = re.compile(r"^\s*(?:\d+[\.\)]|\*|-)?\s*(.+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def api_get(path, token=None):
    req = urllib.request.Request(f"{API_BASE}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def api_post(path, body, token=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}")


# ---------------------------------------------------------------------------
# Ollama classification
# ---------------------------------------------------------------------------

def ollama_classify(name, style_names, music_names):
    styles_str = ", ".join(style_names) if style_names else "(none defined yet)"
    music_str  = ", ".join(music_names) if music_names else "(none defined yet)"

    prompt = (
        f'You are a dance classification expert. Classify this dance move for a learning platform.\n\n'
        f'Available dance styles: {styles_str}\n'
        f'Available musical styles: {music_str}\n\n'
        f'Dance name: "{name}"\n\n'
        f'Return ONLY valid JSON:\n'
        f'{{"dance_styles": ["exact name from list or []"],'
        f'"musical_styles": ["exact name from list or []"],'
        f'"difficulty": "Beginner" or "Intermediate" or "Advanced" or "None",'
        f'"description": "one sentence describing the move"}}\n\n'
        f'Only use names exactly as listed. Use [] if nothing matches.'
    )

    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
            return json.loads(resp["response"])
    except Exception as e:
        print(f"  [Ollama error] {e}")
        return {"dance_styles": [], "musical_styles": [], "difficulty": "None", "description": ""}


# ---------------------------------------------------------------------------
# Video search via yt-dlp
# ---------------------------------------------------------------------------

def _ytdlp_search(query, count=3, timeout=30):
    """Run yt-dlp search and return list of result dicts."""
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings",
             "--flat-playlist", f"{query}:{count}"],
            capture_output=True, text=True, timeout=timeout
        )
        results = []
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return results
    except FileNotFoundError:
        print("  [warn] yt-dlp not found — install with: pip install yt-dlp")
        return []
    except subprocess.TimeoutExpired:
        print("  [warn] yt-dlp search timed out")
        return []


def search_youtube(dance_name, style_hint=""):
    """Search YouTube for a dance tutorial. Returns {platform, video_id, title, url} or None."""
    query_term = f"{dance_name} {style_hint} dance tutorial".strip()
    results = _ytdlp_search(f"ytsearch{query_term}", count=3)
    if not results:
        return None
    best = max(results, key=lambda v: v.get("view_count") or 0)
    vid_id = best.get("id") or best.get("webpage_url", "")
    if not vid_id or len(vid_id) != 11:
        # Try extracting from URL
        m = YT_RE.search(best.get("webpage_url", ""))
        vid_id = m.group(1) if m else None
    if not vid_id:
        return None
    return {
        "platform": "youtube",
        "video_id": vid_id,
        "title": best.get("title", dance_name),
        "url": best.get("webpage_url", f"https://youtube.com/watch?v={vid_id}"),
        "views": best.get("view_count", 0),
    }


def search_tiktok(dance_name):
    """Search TikTok for a dance clip. Returns {platform, video_id, title, url} or None."""
    results = _ytdlp_search(f"ttsearch{dance_name} dance", count=3)
    if not results:
        return None
    best = max(results, key=lambda v: v.get("view_count") or 0)
    vid_id = best.get("id")
    if not vid_id:
        return None
    url = best.get("webpage_url", f"https://www.tiktok.com/@_/video/{vid_id}")
    return {
        "platform": "tiktok",
        "video_id": str(vid_id),
        "title": best.get("title", dance_name),
        "url": url,
        "views": best.get("view_count", 0),
    }


def find_best_video(dance_name, classification):
    """Try YouTube first, fall back to TikTok."""
    style_hint = classification.get("dance_styles", [""])[0] if classification else ""
    print(f"  Searching YouTube...")
    yt = search_youtube(dance_name, style_hint)
    if yt:
        print(f"  Found YouTube: {yt['title']} ({(yt['views'] or 0):,} views)")
        return yt
    print(f"  YouTube miss — trying TikTok...")
    tt = search_tiktok(dance_name)
    if tt:
        print(f"  Found TikTok: {tt['title']} ({(tt['views'] or 0):,} views)")
        return tt
    print(f"  No video found")
    return None


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def parse_timestamp(ts):
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def parse_input(text):
    """Returns (youtube_id_or_None, [(name, start_sec_or_None), ...])"""
    yt_match = YT_RE.search(text)
    yt_id = yt_match.group(1) if yt_match else None

    timestamped = [(m.group(1).strip(), parse_timestamp(m.group(2))) for m in ENTRY_RE.finditer(text)]
    if timestamped:
        return yt_id, timestamped

    names = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not YT_RE.search(line) and not line.startswith("#")
    ]
    return yt_id, [(n, None) for n in names]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Dance Platform Seeder ===\n")

    # Login
    print("Admin credentials for dance-api.takelord.com")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    print("\nLogging in...")
    auth  = api_post("/auth/login", {"username": username, "password": password})
    token = auth["token"]
    print(f"Logged in as {auth['user']['username']}\n")

    # Fetch styles
    styles        = api_get("/styles", token)
    music_styles  = api_get("/musicalstyles", token)
    style_map     = {s["name"].lower(): s["id"] for s in styles}
    music_map     = {ms["name"].lower(): ms["id"] for ms in music_styles}
    style_names   = [s["name"] for s in styles]
    music_names   = [ms["name"] for ms in music_styles]
    print(f"Dance styles:   {', '.join(style_names) or '(none)'}")
    print(f"Musical styles: {', '.join(music_names) or '(none)'}\n")

    # Input
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
        print(f"Reading from {sys.argv[1]}\n")
    else:
        print("Paste YouTube URL + timestamps, or just dance names (one per line).")
        print("Press Enter twice when done:\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        text = "\n".join(lines)

    pinned_yt_id, entries = parse_input(text)
    if not entries:
        print("No dance names found.")
        return

    if pinned_yt_id:
        print(f"Pinned YouTube video: {pinned_yt_id} (all dances will link to this video)")
    print(f"Found {len(entries)} dance(s)\n")

    created = failed = 0

    for i, (name, start_sec) in enumerate(entries, 1):
        end_sec = entries[i][1] - 1 if i < len(entries) and entries[i][1] is not None else None

        print(f"[{i}/{len(entries)}] {name}")

        # Ollama classification
        print(f"  Classifying with Ollama ({OLLAMA_MODEL})...")
        classification = ollama_classify(name, style_names, music_names)

        dance_style_ids = [style_map[s.lower()] for s in classification.get("dance_styles", []) if s.lower() in style_map]
        music_style_ids = [music_map[m.lower()] for m in classification.get("musical_styles", []) if m.lower() in music_map]
        difficulty      = classification.get("difficulty", "None")
        if difficulty not in ("Beginner", "Intermediate", "Advanced", "None"):
            difficulty = "None"
        description = classification.get("description", "")

        print(f"  Styles: {classification.get('dance_styles', [])} → IDs {dance_style_ids}")
        print(f"  Music:  {classification.get('musical_styles', [])} → IDs {music_style_ids}")
        print(f"  Level:  {difficulty}")

        # Video — either pinned YouTube or auto-searched
        video = None
        if pinned_yt_id and start_sec is not None:
            video = {"platform": "youtube", "video_id": pinned_yt_id, "title": name,
                     "start_sec": start_sec, "end_sec": end_sec}
        else:
            found = find_best_video(name, classification)
            if found:
                found["start_sec"] = None
                found["end_sec"]   = None
                video = found

        try:
            dance = api_post("/dances", {
                "name": name,
                "description": description or None,
                "difficulty": difficulty,
                "styleIds": dance_style_ids,
                "musicalStyleIds": music_style_ids,
                "instructorIds": []
            }, token)
            dance_id = dance["id"]
            print(f"  Created dance #{dance_id}")

            if video:
                api_post("/videos", {
                    "title": video["title"],
                    "videoId": video["video_id"],
                    "platform": video["platform"],
                    "danceId": dance_id,
                    "startTime": video.get("start_sec"),
                    "endTime": video.get("end_sec"),
                }, token)
                print(f"  Linked {video['platform']} video: {video['video_id']}")

            created += 1
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            failed += 1

        print()

    print(f"Done — {created} created, {failed} failed.")


if __name__ == "__main__":
    main()
