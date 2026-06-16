"""
Dance Platform seeder — uses Ollama (llama3.2) to classify dance names,
then creates them in the database via the API.

Usage:
  python seed_dances.py                        # interactive mode
  python seed_dances.py names.txt              # file with one dance name per line
  python seed_dances.py video.txt              # file with YouTube URL + timestamps

Timestamp format (same as the admin Import tool):
  https://youtube.com/watch?v=VIDEO_ID
  Running Man [00:29]
  Cabbage Patch [01:04]
  Roger Rabbit [01:45]
"""

import sys
import re
import json
import getpass
import urllib.request
import urllib.error

API_BASE = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

YT_RE = re.compile(r"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})")
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
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body}")


def ollama_classify(name, style_names, music_names):
    styles_str = ", ".join(style_names) if style_names else "(none defined yet)"
    music_str = ", ".join(music_names) if music_names else "(none defined yet)"

    prompt = f"""You are a dance classification expert. Classify this dance move for a learning platform.

Available dance styles: {styles_str}
Available musical styles: {music_str}

Dance name: "{name}"

Return ONLY valid JSON, no explanation:
{{
  "dance_styles": [list of matching names from Available dance styles, or []],
  "musical_styles": [list of matching names from Available musical styles, or []],
  "difficulty": "Beginner" or "Intermediate" or "Advanced" or "None",
  "description": "one sentence describing what this move is"
}}

Use ONLY names exactly as listed above. Use [] if nothing matches."""

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode()

    req = urllib.request.Request(OLLAMA_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            return json.loads(resp["response"])
    except Exception as e:
        print(f"  [Ollama error] {e} — using empty classification")
        return {"dance_styles": [], "musical_styles": [], "difficulty": "None", "description": ""}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_timestamp(ts):
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def parse_input(text):
    """Returns (youtube_id_or_None, [(name, start_sec), ...])"""
    yt_match = YT_RE.search(text)
    yt_id = yt_match.group(1) if yt_match else None

    entries_with_ts = [(m.group(1).strip(), parse_timestamp(m.group(2))) for m in ENTRY_RE.finditer(text)]

    if entries_with_ts:
        return yt_id, entries_with_ts

    # No timestamps — treat each non-empty, non-URL line as a dance name
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

    # --- Login ---
    print("Admin credentials for dance-api.takelord.com")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    print("\nLogging in...")
    auth = api_post("/auth/login", {"username": username, "password": password})
    token = auth["token"]
    print(f"Logged in as {auth['user']['username']}\n")

    # --- Fetch styles ---
    styles = api_get("/styles", token)
    music_styles = api_get("/musicalstyles", token)

    style_map = {s["name"].lower(): s["id"] for s in styles}
    music_map = {ms["name"].lower(): ms["id"] for ms in music_styles}
    style_names = [s["name"] for s in styles]
    music_names = [ms["name"] for ms in music_styles]

    print(f"Dance styles available: {', '.join(style_names) or '(none)'}")
    print(f"Musical styles available: {', '.join(music_names) or '(none)'}\n")

    # --- Input ---
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
        print(f"Reading from {sys.argv[1]}\n")
    else:
        print("Paste YouTube URL + timestamps (or just dance names), then press Enter twice:\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        text = "\n".join(lines)

    yt_id, entries = parse_input(text)
    if not entries:
        print("No dance names found in input.")
        return

    if yt_id:
        print(f"YouTube video: {yt_id}")
    print(f"Found {len(entries)} dance(s) to seed\n")

    # --- Process each dance ---
    created = 0
    failed = 0

    for i, (name, start_sec) in enumerate(entries, 1):
        end_sec = entries[i][1] - 1 if i < len(entries) and entries[i][1] is not None else None

        print(f"[{i}/{len(entries)}] {name}")
        print(f"  Asking Ollama to classify...")

        classification = ollama_classify(name, style_names, music_names)

        # Map names to IDs (case-insensitive)
        dance_style_ids = [
            style_map[s.lower()]
            for s in classification.get("dance_styles", [])
            if s.lower() in style_map
        ]
        music_style_ids = [
            music_map[m.lower()]
            for m in classification.get("musical_styles", [])
            if m.lower() in music_map
        ]
        difficulty = classification.get("difficulty", "None")
        if difficulty not in ("Beginner", "Intermediate", "Advanced", "None"):
            difficulty = "None"
        description = classification.get("description", "")

        print(f"  Styles: {classification.get('dance_styles', [])} → IDs {dance_style_ids}")
        print(f"  Music:  {classification.get('musical_styles', [])} → IDs {music_style_ids}")
        print(f"  Level:  {difficulty}")

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

            if yt_id and start_sec is not None:
                api_post("/videos", {
                    "title": name,
                    "videoId": yt_id,
                    "platform": "youtube",
                    "danceId": dance_id,
                    "startTime": start_sec,
                    "endTime": end_sec
                }, token)
                print(f"  Linked video at {start_sec}s–{end_sec}s")

            created += 1
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            failed += 1

        print()

    print(f"Done — {created} created, {failed} failed.")


if __name__ == "__main__":
    main()
