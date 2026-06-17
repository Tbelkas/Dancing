"""Phase 3: Gap-fill dance moves via Ollama knowledge, then find YouTube videos."""
import requests
import json
import sys
import io
import time
import subprocess
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

BASELINE_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\baseline.json"

print("=== Phase 3: Gap-fill via Ollama ===")

# Fresh login
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get fresh state
resp = requests.get(f"{API_BASE}/dances", headers=headers)
resp.raise_for_status()
dances = resp.json()
existing_names = {d["name"].lower() for d in dances}
print(f"Current dances: {len(dances)} (will not duplicate)")

resp = requests.get(f"{API_BASE}/styles", headers=headers)
styles = resp.json()
resp = requests.get(f"{API_BASE}/musicalstyles", headers=headers)
musical_styles = resp.json()

style_name_to_id = {s["name"].lower(): s["id"] for s in styles}
music_name_to_id = {ms["name"].lower(): ms["id"] for ms in musical_styles}
style_names = [s["name"] for s in styles]
music_names = [ms["name"] for ms in musical_styles]

print(f"Styles: {style_names}")

def ollama_list_moves(style_name, count=40):
    prompt = (
        f'List {count} well-known {style_name} dance moves or steps. '
        f'These should be real, named dance moves used in {style_name} dance. '
        f'Return ONLY a JSON array of strings, no explanations. '
        f'Example: ["Move Name 1", "Move Name 2", ...]'
    )
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False},
            timeout=60
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "[]")
        # Parse the JSON array
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(item) for item in data]
        # Maybe it's {"moves": [...]} or similar
        for v in data.values():
            if isinstance(v, list):
                return [str(item) for item in v]
        return []
    except Exception as e:
        print(f"  Ollama list error for '{style_name}': {e}")
        return []

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
            return json.loads(raw)
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
            else:
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
    description = str(classification.get("description", "") or "")

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
            return None, "server_error"
        resp.raise_for_status()
        dance = resp.json()
        dance_id = dance.get("id") or dance.get("danceId")
        return dance_id, "created"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        if code == 409:
            return None, "duplicate"
        return None, "error"
    except Exception as e:
        return None, "error"

def search_youtube(query, style_name):
    """Search for YouTube video for a dance move."""
    search_query = f"ytsearch3:{query} {style_name} dance tutorial"
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings", search_query],
            capture_output=True, text=True, timeout=30
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                v = json.loads(line)
                videos.append(v)
            except:
                pass

        if not videos:
            return None, None

        # Pick highest view count
        best = max(videos, key=lambda v: v.get("view_count", 0) or 0)
        return best.get("id"), best.get("title", "")
    except Exception as e:
        return None, None

def create_video(dance_id, video_id, title):
    payload = {
        "title": (title or "Dance Tutorial")[:200],
        "videoId": video_id,
        "platform": "youtube",
        "videoType": "steps",
        "danceId": dance_id
    }
    try:
        resp = requests.post(f"{API_BASE}/videos", headers=headers, json=payload, timeout=15)
        if resp.status_code in [200, 201]:
            return "created"
        if resp.status_code == 409:
            return "duplicate"
        return f"error_{resp.status_code}"
    except Exception as e:
        return "error"

# Expanded style list with targeted prompts
style_targets = [
    ("Latin", "Latin"),
    ("Ballroom", "Ballroom"),
    ("Street / Urban", "Street Urban"),
    ("Classical / Ballet", "Ballet Classical"),
    ("Folk / Traditional", "Folk Traditional"),
    ("Swing", "Swing"),
    ("Contemporary", "Contemporary"),
    ("Waacking", "Waacking"),
    ("Tektonik", "Tektonik"),
    ("Hip-hop", "Hip-Hop"),
    ("House", "House"),
]

# Also add some genre-specific prompts
extra_prompts = [
    ("Salsa", "Salsa"),
    ("Breakdance", "Breakdance bboy"),
    ("Popping", "Popping"),
    ("Locking", "Locking"),
    ("Reggaeton", "Reggaeton"),
    ("Tango", "Tango"),
    ("Jazz Dance", "Jazz dance"),
    ("Bachata", "Bachata"),
    ("Zouk", "Zouk"),
    ("Kizomba", "Kizomba"),
]

total_created = 0
total_videos = 0
total_skipped = 0
total_errors = 0

all_style_targets = style_targets + extra_prompts

for style_name, search_suffix in all_style_targets:
    print(f"\n--- Style: {style_name} ---")

    moves = ollama_list_moves(style_name, count=40)
    print(f"  Ollama suggested {len(moves)} moves")

    new_moves = [m for m in moves if m and m.lower() not in existing_names and len(m.strip()) >= 3 and len(m.strip()) <= 100]
    print(f"  {len(new_moves)} are new")

    for name in new_moves:
        name = name.strip()
        if not name or name.lower() in existing_names:
            total_skipped += 1
            continue

        # Classify
        classification = ollama_classify(name)

        # Create dance
        dance_id, status = create_dance(name, classification)

        if status == "created" and dance_id:
            existing_names.add(name.lower())
            total_created += 1

            # Search YouTube
            vid_id, vid_title = search_youtube(name, search_suffix)
            if vid_id:
                v_status = create_video(dance_id, vid_id, vid_title)
                if v_status == "created":
                    total_videos += 1
                print(f"  + '{name}' (id={dance_id}, yt={vid_id or 'none'}, video={v_status if vid_id else 'no_video'})")
            else:
                print(f"  + '{name}' (id={dance_id}, no YouTube result)")

        elif status == "duplicate":
            existing_names.add(name.lower())
            total_skipped += 1
        else:
            total_errors += 1

    print(f"  Running totals: created={total_created}, videos={total_videos}, skip={total_skipped}")

print(f"\n=== Phase 3 Summary ===")
print(f"Total created: {total_created} dances")
print(f"Videos linked: {total_videos}")
print(f"Skipped (dup): {total_skipped}")
print(f"Errors: {total_errors}")

# Update baseline
with open(BASELINE_FILE) as f:
    baseline = json.load(f)
baseline["phase3_created"] = total_created
baseline["existing_names"] = list(existing_names)
with open(BASELINE_FILE, "w") as f:
    json.dump(baseline, f, indent=2)
print("Baseline updated.")
