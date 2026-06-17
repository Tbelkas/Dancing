import requests
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
BEFORE_COUNT = 834

TARGET_STYLES = [
    "Contemporary",
    "Swing",
    "House",
    "Classical / Ballet",
    "Folk / Traditional",
    "Tektonik",
]

print("Logging in...")
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

print("Fetching all dances...")
dances_resp = requests.get(f"{API_BASE}/dances", headers=headers)
all_dances = dances_resp.json()
total_after = len(all_dances)

print(f"\n=== Phase 4: Verification ===")
print(f"Before: {BEFORE_COUNT}")
print(f"After:  {total_after}")
print(f"Added:  {total_after - BEFORE_COUNT}")

# Per-style counts
style_counts = {}
video_counts = {}
for d in all_dances:
    has_videos = bool(d.get("videoCount", 0) > 0)
    for s in (d.get("styles") or []):
        # styles is a list of strings
        sname = s if isinstance(s, str) else s.get("name", "")
        if sname:
            style_counts[sname] = style_counts.get(sname, 0) + 1
            if has_videos:
                video_counts[sname] = video_counts.get(sname, 0) + 1

print(f"\nPer-style breakdown (target styles highlighted):")
for sname, count in sorted(style_counts.items(), key=lambda x: x[1]):
    marker = " <-- TARGET" if sname in TARGET_STYLES else ""
    vc = video_counts.get(sname, 0)
    pct = int(100 * vc / count) if count else 0
    print(f"  {sname}: {count} dances, {vc} with videos ({pct}%){marker}")

# Overall video coverage
total_with_vid = sum(1 for d in all_dances if d.get("videos") or d.get("videoCount"))
overall_pct = int(100 * total_with_vid / total_after) if total_after else 0
print(f"\nOverall video coverage: {total_with_vid}/{total_after} ({overall_pct}%)")
