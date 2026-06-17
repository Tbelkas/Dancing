import subprocess
import json
import re
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PHASE1_OUTPUT = r"C:\Users\valot\Documents\Git\Projects\Dance\phase1_results.json"
BASELINE_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\baseline.json"

with open(BASELINE_FILE) as f:
    baseline = json.load(f)

existing_names = set(baseline["existing_names"])

SEARCHES = [
    "ytsearch5:hip hop dance moves tutorial timestamps 2024",
    "ytsearch5:breakdance bboy moves tutorial timestamps",
    "ytsearch5:latin salsa dance moves timestamps",
    "ytsearch5:ballroom dance steps tutorial timestamps",
    "ytsearch5:popping locking dance moves tutorial",
    "ytsearch5:house dance footwork moves tutorial",
    "ytsearch5:waacking vogue dance moves tutorial",
    "ytsearch5:contemporary dance moves tutorial timestamps",
    "ytsearch5:swing lindy hop dance steps tutorial",
]

TIMESTAMP_RE = re.compile(
    r'^\s*(?:\d+[\.\)]|\*|-)?\s*(.+?)\s*[\[\(](\d{1,2}:\d{2}(?::\d{2})?)[\]\)]\s*$'
)

def time_to_sec(t):
    parts = t.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def run_ytdlp(query):
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings", query],
            capture_output=True, text=True, timeout=60
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                videos.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return videos
    except subprocess.TimeoutExpired:
        print(f"  Timeout for: {query}")
        return []
    except Exception as e:
        print(f"  Error: {e}")
        return []

def extract_timestamps_from_description(description):
    """Extract timestamp lines from description."""
    if not description:
        return []
    entries = []
    lines = description.split("\n")
    for line in lines:
        m = TIMESTAMP_RE.match(line)
        if m:
            name = m.group(1).strip()
            time_str = m.group(2).strip()
            # Clean up name - remove leading numbers/symbols
            name = re.sub(r'^[\d\.\)\-\*\s]+', '', name).strip()
            name = re.sub(r'[\-–—]\s*$', '', name).strip()
            if len(name) >= 3 and len(name) <= 80:
                entries.append((name, time_to_sec(time_str)))
    return entries

def extract_from_chapters(chapters):
    """Extract from video chapters."""
    if not chapters:
        return []
    entries = []
    for ch in chapters:
        title = ch.get("title", "").strip()
        start = ch.get("start_time", 0)
        if title and len(title) >= 3 and len(title) <= 80:
            # Skip generic chapter names
            skip_words = ["intro", "introduction", "outro", "end", "conclusion", "chapter", "part", "section", "warm up", "warmup", "cool down", "cooldown"]
            if not any(sw in title.lower() for sw in skip_words):
                entries.append((title, int(start)))
    return entries

print("=== Phase 1: YouTube Timestamped Videos ===")

seen_video_ids = set()
all_videos_data = []  # (video_id, title, entries_count, new_names_entries)

for search in SEARCHES:
    print(f"\nSearching: {search}")
    videos = run_ytdlp(search)
    print(f"  Got {len(videos)} videos")

    for v in videos:
        vid_id = v.get("id", "")
        if not vid_id or vid_id in seen_video_ids:
            continue
        seen_video_ids.add(vid_id)

        title = v.get("title", "Unknown")
        description = v.get("description", "")
        chapters = v.get("chapters") or []
        duration = v.get("duration", 0) or 0

        # Extract timestamps
        ts_entries = extract_timestamps_from_description(description)
        ch_entries = extract_from_chapters(chapters)

        # Combine, prefer chapters if available
        if ch_entries:
            raw_entries = ch_entries
        else:
            raw_entries = ts_entries

        if not raw_entries:
            continue

        # Sort by time
        raw_entries.sort(key=lambda x: x[1])

        # Build (name, start_sec, end_sec) triples
        triples = []
        for i, (name, start) in enumerate(raw_entries):
            if i + 1 < len(raw_entries):
                end = raw_entries[i+1][1]
            else:
                end = int(duration) if duration else start + 60
            # Filter out very short clips
            if end - start < 5:
                end = start + 30
            triples.append((name, start, end))

        # Count new names
        new_triples = [(n, s, e) for n, s, e in triples if n.lower() not in existing_names]

        print(f"  [{vid_id}] {title[:60]} - {len(raw_entries)} timestamps, {len(new_triples)} new")

        if new_triples:
            all_videos_data.append({
                "video_id": vid_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "total_timestamps": len(raw_entries),
                "new_count": len(new_triples),
                "moves": [{"name": n, "start_sec": s, "end_sec": e} for n, s, e in new_triples]
            })

# Sort by new_count descending
all_videos_data.sort(key=lambda x: x["new_count"], reverse=True)

# Keep all videos with 5+ new names, plus top ones otherwise
top_videos = [v for v in all_videos_data if v["new_count"] >= 5]
if len(top_videos) < 3:
    # Take top 3 regardless
    top_videos = all_videos_data[:3]

print(f"\n=== Summary ===")
print(f"Total videos with timestamps: {len(all_videos_data)}")
print(f"Videos with 5+ new moves: {len(top_videos)}")

total_new = sum(v["new_count"] for v in top_videos)
print(f"Total new dance moves from videos: {total_new}")

for v in top_videos:
    print(f"  [{v['video_id']}] {v['title'][:60]} - {v['new_count']} new moves")

# Save results
with open(PHASE1_OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "all_videos": all_videos_data,
        "top_videos": top_videos,
        "total_new_from_top": total_new
    }, f, indent=2, ensure_ascii=False)

print(f"\nPhase 1 results saved to {PHASE1_OUTPUT}")
