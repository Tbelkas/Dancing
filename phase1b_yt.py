import subprocess
import json
import re
import sys
import io
import requests
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
OUTPUT_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\phase1b_results.json"

# Login
print("Logging in...")
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Fetch existing dances
print("Fetching existing dances...")
dances_resp = requests.get(f"{API_BASE}/dances", headers=headers)
dances_resp.raise_for_status()
all_dances = dances_resp.json()
existing_names = set(d["name"].lower().strip() for d in all_dances)
print(f"Existing dances: {len(existing_names)}")

QUERIES = [
    "contemporary dance moves tutorial timestamps",
    "contemporary dance techniques beginner",
    "lyrical contemporary dance moves list",
    "swing dance moves tutorial timestamps lindy hop",
    "east coast swing dance steps beginner",
    "jive swing dance moves compilation",
    "house dance footwork tutorial timestamps",
    "house dance moves beginner chicago",
    "house music dance tutorial steps",
    "classical ballet moves tutorial timestamps",
    "ballet barre exercises tutorial",
    "ballet technique moves for beginners",
    "tektonik dance moves tutorial",
    "tecktonik electro dance moves",
    "folk dance steps tutorial traditional",
    "irish step dance moves tutorial",
    "country folk dance steps tutorial",
    "flamenco dance moves tutorial timestamps",
    "jazz dance moves tutorial timestamps",
    "tap dance steps for beginners tutorial timestamps",
]

# Timestamp patterns in description
TIMESTAMP_RE = re.compile(
    r'^\s*(?:\d+[\.\)]\s*)?(?:[\*\-]\s*)?(.+?)\s*[\[\(](\d{1,2}:\d{2}(?::\d{2})?)\]?\)?\s*$'
)

def time_to_sec(ts):
    parts = ts.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def run_ytdlp(args, timeout=60):
    try:
        result = subprocess.run(
            ["yt-dlp"] + args,
            capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace'
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  yt-dlp timeout")
        return ""
    except Exception as e:
        print(f"  yt-dlp error: {e}")
        return ""

def extract_from_description(desc):
    """Extract name->timestamp pairs from description lines."""
    entries = []
    if not desc:
        return entries
    lines = desc.split('\n')
    for line in lines:
        m = TIMESTAMP_RE.match(line)
        if m:
            name = m.group(1).strip()
            ts = m.group(2).strip()
            # Filter out garbage: too short, too long, or looks like a URL
            if len(name) < 3 or len(name) > 80:
                continue
            if 'http' in name.lower() or 'www.' in name.lower():
                continue
            # Skip if it's just a number
            if re.match(r'^\d+$', name):
                continue
            start_sec = time_to_sec(ts)
            entries.append({"name": name, "start_sec": start_sec})
    return entries

def extract_from_chapters(chapters):
    """Extract name->start/end from chapters."""
    entries = []
    if not chapters:
        return entries
    for i, ch in enumerate(chapters):
        title = ch.get("title", "").strip()
        start = ch.get("start_time", 0)
        end = ch.get("end_time", None)
        if not title or title.lower() in ("intro", "introduction", "outro", "credits", "end"):
            continue
        if len(title) < 3 or len(title) > 80:
            continue
        entry = {"name": title, "start_sec": int(start)}
        if end is not None:
            entry["end_sec"] = int(end)
        entries.append(entry)
    return entries

# Collect video IDs from searches
print("\n=== Phase 1b: Collecting video IDs ===")
all_video_ids = set()

for query in QUERIES:
    print(f"\nSearching: {query}")
    out = run_ytdlp(["--dump-json", "--no-download", "--no-warnings", "--flat-playlist", f"ytsearch5:{query}"], timeout=60)
    count = 0
    for line in out.strip().split('\n'):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            vid_id = item.get("id") or item.get("url", "").replace("https://www.youtube.com/watch?v=", "")
            if vid_id and len(vid_id) == 11:
                all_video_ids.add(vid_id)
                count += 1
        except:
            pass
    print(f"  Found {count} video IDs")

print(f"\nTotal unique video IDs: {len(all_video_ids)}")

# Fetch full metadata for each video and extract dances
results = []
processed = 0

for vid_id in list(all_video_ids):
    processed += 1
    print(f"\n[{processed}/{len(all_video_ids)}] Fetching metadata for {vid_id}...")

    out = run_ytdlp(["--dump-json", "--no-download", "--no-warnings", f"https://youtube.com/watch?v={vid_id}"], timeout=90)

    if not out.strip():
        print(f"  No metadata returned")
        continue

    try:
        meta = json.loads(out.strip().split('\n')[0])
    except:
        print(f"  Failed to parse JSON")
        continue

    title = meta.get("title", "")
    desc = meta.get("description", "")
    chapters = meta.get("chapters", [])

    print(f"  Title: {title[:60]}")

    entries = []

    # Priority 1: chapters
    chapter_entries = extract_from_chapters(chapters)
    if chapter_entries:
        print(f"  Found {len(chapter_entries)} entries from chapters")
        entries = chapter_entries
    else:
        # Priority 2: description timestamps
        desc_entries = extract_from_description(desc)
        if desc_entries:
            print(f"  Found {len(desc_entries)} entries from description")
            entries = desc_entries

    # Filter to new names only and add end times where missing
    new_entries = []
    for i, e in enumerate(entries):
        name_lower = e["name"].lower().strip()
        if name_lower in existing_names:
            continue
        # Add end_sec if not present
        if "end_sec" not in e:
            # Use start of next entry or start + 60s
            if i + 1 < len(entries):
                e["end_sec"] = entries[i + 1]["start_sec"]
            else:
                e["end_sec"] = e["start_sec"] + 60
        new_entries.append(e)

    if new_entries:
        print(f"  New entries: {len(new_entries)}")
        results.append({"video_id": vid_id, "entries": new_entries})
        # Add to existing names to avoid cross-video dupes
        for e in new_entries:
            existing_names.add(e["name"].lower().strip())
    else:
        print(f"  No new entries")

total_entries = sum(len(r["entries"]) for r in results)
print(f"\n=== Phase 1b Complete ===")
print(f"Videos with entries: {len(results)}")
print(f"Total new dance entries: {total_entries}")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT_FILE}")
