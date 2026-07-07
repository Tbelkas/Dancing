"""Phase 4: Verify final database state and print summary."""
import requests
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
BASELINE_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\baseline.json"

with open(BASELINE_FILE) as f:
    baseline = json.load(f)

INITIAL_COUNT = baseline.get("dance_count", 489)

print("=== Phase 4: Final Verification ===")

# Fresh login
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get all dances
resp = requests.get(f"{API_BASE}/dances", headers=headers)
resp.raise_for_status()
dances = resp.json()
final_count = len(dances)

# Get styles and music
resp = requests.get(f"{API_BASE}/styles", headers=headers)
styles = resp.json()
resp = requests.get(f"{API_BASE}/musicalstyles", headers=headers)
musical_styles = resp.json()

style_map = {s["id"]: s["name"] for s in styles}
music_map = {ms["id"]: ms["name"] for ms in musical_styles}

# Per-style breakdown
style_counts = {s["name"]: 0 for s in styles}

dances_with_styles = 0
dances_without_styles = 0
difficulty_counts = {}
dances_with_description = 0

for d in dances:
    dance_styles = d.get("styles") or d.get("danceStyles") or []
    difficulty = d.get("difficulty") or "None"
    description = d.get("description") or ""

    if dance_styles:
        dances_with_styles += 1
        for s in dance_styles:
            if isinstance(s, dict):
                sname = s.get("name") or style_map.get(s.get("id") or s.get("styleId"), "Unknown")
            else:
                sname = style_map.get(s, "Unknown")
            if sname in style_counts:
                style_counts[sname] += 1
    else:
        dances_without_styles += 1

    difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

    if description and len(description) > 5:
        dances_with_description += 1

print(f"\n{'='*50}")
print(f"BEFORE: {INITIAL_COUNT} dances")
print(f"AFTER:  {final_count} dances")
print(f"ADDED:  {final_count - INITIAL_COUNT} new dances")
print(f"{'='*50}")

print(f"\n--- Per-Style Breakdown ---")
for sname, count in sorted(style_counts.items(), key=lambda x: -x[1]):
    pct = (count / final_count * 100) if final_count > 0 else 0
    print(f"  {sname:30s}: {count:4d} ({pct:.1f}%)")

pct_with = dances_with_styles/final_count*100 if final_count > 0 else 0
pct_without = dances_without_styles/final_count*100 if final_count > 0 else 0
print(f"\n  Dances WITH styles:    {dances_with_styles} ({pct_with:.1f}%)")
print(f"  Dances WITHOUT styles: {dances_without_styles} ({pct_without:.1f}%)")

print(f"\n--- Video Coverage ---")
try:
    resp2 = requests.get(f"{API_BASE}/videos", headers=headers)
    if resp2.status_code == 200:
        videos = resp2.json()
        dance_ids_with_video = {v.get("danceId") for v in videos if v.get("danceId")}
        video_coverage = len(dance_ids_with_video)
        print(f"  Total videos in DB: {len(videos)}")
        print(f"  Dances with video: {video_coverage} ({video_coverage/final_count*100:.1f}%)")
        print(f"  Dances without video: {final_count - video_coverage} ({(final_count-video_coverage)/final_count*100:.1f}%)")
    else:
        print(f"  (Could not fetch /api/videos: {resp2.status_code})")
        total_with_video = sum(1 for d in dances if d.get("videos") and len(d.get("videos")) > 0)
        print(f"  Dances with video (from list): {total_with_video} ({total_with_video/final_count*100:.1f}%)")
except Exception as e:
    print(f"  Error: {e}")

print(f"\n--- Difficulty Breakdown ---")
for diff, count in sorted(difficulty_counts.items(), key=lambda x: -x[1]):
    pct = (count / final_count * 100) if final_count > 0 else 0
    print(f"  {str(diff):15s}: {count:4d} ({pct:.1f}%)")

diff_classified = sum(v for k, v in difficulty_counts.items() if k not in ["None", None, "null", ""])
print(f"\n  Difficulty classified: {diff_classified} ({diff_classified/final_count*100:.1f}%)")

print(f"\n--- Description Coverage ---")
print(f"  With description: {dances_with_description} ({dances_with_description/final_count*100:.1f}%)")

print(f"\n{'='*50}")
added = final_count - INITIAL_COUNT
if added >= 150:
    print(f"SUCCESS: Added {added} dances (target was 150)")
else:
    print(f"PARTIAL: Added {added} dances (target: 150) - need {150 - added} more")
print(f"{'='*50}")

print(f"\n--- Phase Contributions ---")
print(f"  Phase 2 (YouTube videos): {baseline.get('phase2_created', '?')}")
print(f"  Phase 3 (Ollama gap-fill): {baseline.get('phase3_created', '?')}")
print(f"  Total new: {final_count - INITIAL_COUNT}")
