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
PHASE1B_FILE = r"C:\Users\valot\Documents\Git\Projects\Dance\phase1b_results.json"

# Login
print("Logging in...")
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print(f"Token acquired.")

# Fetch styles
styles_resp = requests.get(f"{API_BASE}/styles", headers=headers)
styles = styles_resp.json()
music_resp = requests.get(f"{API_BASE}/musicalstyles", headers=headers)
music_styles = music_resp.json()

style_name_to_id = {s["name"].lower(): s["id"] for s in styles}
music_name_to_id = {s["name"].lower(): s["id"] for s in music_styles}
style_names = [s["name"] for s in styles]
music_names = [s["name"] for s in music_styles]

# Fetch existing dances
print("Fetching existing dances...")
dances_resp = requests.get(f"{API_BASE}/dances", headers=headers)
all_dances = dances_resp.json()
existing_names = set(d["name"].lower().strip() for d in all_dances)
print(f"Existing: {len(existing_names)}")

# Load phase1b results
with open(PHASE1B_FILE, 'r', encoding='utf-8') as f:
    phase1b = json.load(f)

total_entries = sum(len(r["entries"]) for r in phase1b)
print(f"Loaded {len(phase1b)} videos with {total_entries} entries")

def ollama_classify(name):
    prompt = (
        f'Classify this dance move: "{name}"\n'
        f'Available dance styles: {", ".join(style_names)}\n'
        f'Available musical styles: {", ".join(music_names)}\n'
        f'Return ONLY valid JSON: {{"dance_styles": ["exact name from list"], "musical_styles": ["exact name from list"], '
        f'"difficulty": "Beginner" or "Intermediate" or "Advanced" or "None", "description": "one sentence"}}\n'
        f'Only use names exactly as listed. Use [] if nothing fits.'
    )
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=90)
        if r.status_code == 200:
            data = r.json()
            return json.loads(data.get("response", "{}"))
    except Exception as e:
        print(f"    Ollama error: {e}")
    return {}

def get_style_ids(names_list):
    ids = []
    for n in (names_list or []):
        if not n:
            continue
        nid = style_name_to_id.get(n.lower())
        if nid:
            ids.append(nid)
    return ids

def get_music_ids(names_list):
    ids = []
    for n in (names_list or []):
        if not n:
            continue
        nid = music_name_to_id.get(n.lower())
        if nid:
            ids.append(nid)
    return ids

ok_count = 0
skip_count = 0
fail_count = 0
entry_num = 0

print("\n=== Phase 2b: Seeding from timestamped videos ===\n")

for video in phase1b:
    vid_id = video["video_id"]
    for entry in video["entries"]:
        entry_num += 1
        name = entry["name"].strip()
        start_sec = entry.get("start_sec", 0)
        end_sec = entry.get("end_sec", start_sec + 60)

        # Skip if already exists
        if name.lower() in existing_names:
            print(f"[{entry_num}] SKIP (exists): {name}")
            skip_count += 1
            continue

        print(f"[{entry_num}] Classifying: {name}")
        classification = ollama_classify(name)

        dance_styles = classification.get("dance_styles", [])
        musical_styles = classification.get("musical_styles", [])
        difficulty = classification.get("difficulty", "None")
        description = classification.get("description", f"A dance move: {name}")

        if difficulty not in ("Beginner", "Intermediate", "Advanced"):
            difficulty = "None"

        style_ids = get_style_ids(dance_styles)
        music_ids = get_music_ids(musical_styles)

        # Create dance
        dance_payload = {
            "name": name,
            "description": description,
            "difficulty": difficulty,
            "styleIds": style_ids,
            "musicalStyleIds": music_ids,
            "instructorIds": []
        }

        try:
            r = requests.post(f"{API_BASE}/dances", json=dance_payload, headers=headers, timeout=30)
            if r.status_code == 409:
                print(f"  SKIP 409: {name}")
                skip_count += 1
                existing_names.add(name.lower())
                continue
            elif r.status_code >= 400:
                print(f"  FAIL {r.status_code}: {name} — {r.text[:100]}")
                fail_count += 1
                continue
            dance_id = r.json().get("id")
        except Exception as e:
            print(f"  FAIL (dance POST): {e}")
            fail_count += 1
            continue

        # Create video
        video_payload = {
            "title": name,
            "videoId": vid_id,
            "platform": "youtube",
            "danceId": dance_id,
            "startTime": start_sec,
            "endTime": end_sec
        }
        try:
            vr = requests.post(f"{API_BASE}/videos", json=video_payload, headers=headers, timeout=30)
            if vr.status_code >= 400 and vr.status_code != 409:
                print(f"  WARN video {vr.status_code}: {vr.text[:80]}")
        except Exception as e:
            print(f"  WARN video error: {e}")

        existing_names.add(name.lower())
        ok_count += 1
        print(f"  OK (dance {dance_id}, vid {vid_id} [{start_sec}-{end_sec}s])")

print(f"\n=== Phase 2b Complete ===")
print(f"OK: {ok_count} | SKIP: {skip_count} | FAIL: {fail_count}")
