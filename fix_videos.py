"""Fix video creation for dances already created in Phase 2."""
import requests
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
PHASE1_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\phase1_results.json"
BASELINE_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\baseline.json"

# Fresh login
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

with open(PHASE1_FILE) as f:
    phase1 = json.load(f)

with open(BASELINE_FILE) as f:
    baseline = json.load(f)

# Get all current dances to build name->id map
resp = requests.get(f"{API_BASE}/dances", headers=headers)
resp.raise_for_status()
dances = resp.json()
name_to_id = {d["name"].lower(): d["id"] for d in dances}
print(f"Loaded {len(dances)} dances")

# Get existing videos to avoid duplicates
resp = requests.get(f"{API_BASE}/videos", headers=headers)
if resp.status_code == 200:
    videos = resp.json()
    dance_ids_with_video = {v.get("danceId") or v.get("dance_id") for v in videos if v.get("danceId") or v.get("dance_id")}
    print(f"Dances already with videos: {len(dance_ids_with_video)}")
else:
    dance_ids_with_video = set()
    print("Could not fetch existing videos")

created = 0
skipped = 0
errors = {}

for video_data in phase1["all_videos"]:
    vid_id = video_data["video_id"]
    vid_title = video_data["title"]
    moves = video_data["moves"]

    for move in moves:
        name = move["name"]
        start_sec = move["start_sec"]
        end_sec = move["end_sec"]

        dance_id = name_to_id.get(name.lower())
        if not dance_id:
            continue

        if dance_id in dance_ids_with_video:
            skipped += 1
            continue

        payload = {
            "title": vid_title[:200],
            "videoId": vid_id,
            "platform": "youtube",
            "videoType": "steps",
            "danceId": dance_id,
            "startTime": start_sec,
            "endTime": end_sec
        }

        try:
            resp = requests.post(f"{API_BASE}/videos", headers=headers, json=payload, timeout=15)
            if resp.status_code == 409:
                skipped += 1
                dance_ids_with_video.add(dance_id)
                continue
            if resp.status_code >= 400:
                err_key = f"{resp.status_code}"
                errors[err_key] = errors.get(err_key, 0) + 1
                if resp.status_code == 400:
                    print(f"  400 for '{name}': {resp.text[:200]}")
                continue
            resp.raise_for_status()
            created += 1
            dance_ids_with_video.add(dance_id)
        except Exception as e:
            errors["exception"] = errors.get("exception", 0) + 1

print(f"\nVideo fix complete: created={created}, skipped={skipped}, errors={errors}")
