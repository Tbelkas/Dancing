import requests
import json
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

BASELINE_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\baseline.json"
PHASE1_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\phase1_results.json"

with open(BASELINE_FILE) as f:
    baseline = json.load(f)

with open(PHASE1_FILE) as f:
    phase1 = json.load(f)

# Re-login for fresh token
print("Logging in...")
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
print(f"Token: {token[:30]}...")

existing_names = set(baseline["existing_names"])
styles = baseline["styles"]
musical_styles = baseline["musical_styles"]

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

style_name_to_id = {s["name"].lower(): s["id"] for s in styles}
music_name_to_id = {s["name"].lower(): s["id"] for s in musical_styles}

style_names = [s["name"] for s in styles]
music_names = [s["name"] for s in musical_styles]

print("=== Phase 2: Seed from timestamped videos ===")

def ollama_classify(name, retries=2):
    prompt = (
        f'Classify dance move "{name}". '
        f'Available dance styles: {style_names}. '
        f'Available musical styles: {music_names}. '
        f'Return JSON: {{"dance_styles": [...], "musical_styles": [...], '
        f'"difficulty": "Beginner" or "Intermediate" or "Advanced" or "None", '
        f'"description": "one sentence describing this move"}}'
    )
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False},
                timeout=30
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "{}")
            data = json.loads(raw)
            return data
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
            else:
                print(f"  Ollama error for '{name}': {e}")
                return {}
    return {}

def map_styles(names_list, name_to_id):
    ids = []
    for n in (names_list or []):
        n_lower = n.lower()
        for key, vid in name_to_id.items():
            if n_lower in key or key in n_lower:
                if vid not in ids:
                    ids.append(vid)
                break
    return ids

def create_dance(name, classification):
    dance_style_ids = map_styles(classification.get("dance_styles", []), style_name_to_id)
    musical_style_ids = map_styles(classification.get("musical_styles", []), music_name_to_id)
    difficulty = classification.get("difficulty", "None")
    if difficulty not in ["Beginner", "Intermediate", "Advanced", "None"]:
        difficulty = "None"
    description = classification.get("description", "") or ""

    payload = {
        "name": name,
        "description": description,
        "difficulty": difficulty,
        "styleIds": dance_style_ids,
        "musicalStyleIds": musical_style_ids
    }

    try:
        resp = requests.post(f"{API_BASE}/dances", headers=headers, json=payload, timeout=15)
        if resp.status_code == 409:
            return None, "duplicate"
        if resp.status_code >= 500:
            print(f"  5xx error creating '{name}': {resp.status_code} {resp.text[:100]}")
            return None, "server_error"
        resp.raise_for_status()
        dance = resp.json()
        dance_id = dance.get("id") or dance.get("danceId")
        return dance_id, "created"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        if code == 409:
            return None, "duplicate"
        print(f"  HTTP error creating '{name}': {e}")
        return None, "error"
    except Exception as e:
        print(f"  Error creating '{name}': {e}")
        return None, "error"

def create_video(dance_id, video_id, start_sec, end_sec):
    # Try different payload formats
    payload = {
        "danceId": dance_id,
        "youtubeVideoId": video_id,
        "startTime": start_sec,
        "endTime": end_sec
    }
    try:
        resp = requests.post(f"{API_BASE}/videos", headers=headers, json=payload, timeout=15)
        if resp.status_code == 409:
            return "duplicate"
        if resp.status_code >= 500:
            return "server_error"
        if resp.status_code == 404:
            return "not_found"
        if resp.status_code == 400:
            # Try alternate format
            payload2 = {
                "danceId": dance_id,
                "videoId": video_id,
                "platform": "YouTube",
                "startTime": start_sec,
                "endTime": end_sec
            }
            resp2 = requests.post(f"{API_BASE}/videos", headers=headers, json=payload2, timeout=15)
            if resp2.status_code in [200, 201]:
                return "created"
            return f"error_{resp2.status_code}"
        resp.raise_for_status()
        return "created"
    except Exception as e:
        return f"error: {e}"

created_count = 0
skipped_count = 0
error_count = 0
video_count = 0
video_errors = {}

all_videos = phase1["all_videos"]
print(f"Processing {len(all_videos)} videos with new moves...")

for video_data in all_videos:
    vid_id = video_data["video_id"]
    vid_title = video_data["title"]
    moves = video_data["moves"]

    print(f"\nVideo [{vid_id}]: {vid_title[:60]}")
    print(f"  {len(moves)} new moves")

    for move in moves:
        name = move["name"]
        start_sec = move["start_sec"]
        end_sec = move["end_sec"]

        if name.lower() in existing_names:
            skipped_count += 1
            continue

        # Classify with Ollama
        classification = ollama_classify(name)

        # Create dance
        dance_id, status = create_dance(name, classification)

        if status == "created" and dance_id:
            existing_names.add(name.lower())
            created_count += 1

            # Create video
            v_status = create_video(dance_id, vid_id, start_sec, end_sec)
            if v_status == "created":
                video_count += 1
            else:
                video_errors[v_status] = video_errors.get(v_status, 0) + 1
            print(f"  + '{name}' (id={dance_id}, video={v_status})")

        elif status == "duplicate":
            existing_names.add(name.lower())
            skipped_count += 1
        else:
            error_count += 1
            print(f"  ! Failed '{name}' ({status})")

print(f"\n=== Phase 2 Summary ===")
print(f"Created: {created_count} dances")
print(f"Videos linked: {video_count}")
print(f"Video errors: {video_errors}")
print(f"Skipped (duplicate): {skipped_count}")
print(f"Errors: {error_count}")

# Update baseline
baseline["existing_names"] = list(existing_names)
baseline["phase2_created"] = created_count
with open(BASELINE_FILE, "w") as f:
    json.dump(baseline, f, indent=2)

print("Baseline updated.")
