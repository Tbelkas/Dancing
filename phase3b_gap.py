import requests
import json
import sys
import io
import subprocess
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

TARGET_STYLES = [
    "Contemporary",
    "Swing",
    "House",
    "Classical / Ballet",
    "Folk / Traditional",
    "Tektonik",
]

# Login
print("Logging in...")
resp = requests.post(f"{API_BASE}/auth/login", json={"username": "justas", "password": "Dance@Admin2026"})
resp.raise_for_status()
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("Token acquired.")

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
print(f"Existing dances: {len(existing_names)}")


def ollama_request(prompt, expect_json=True, timeout=90):
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        if expect_json:
            payload["format"] = "json"
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        if r.status_code == 200:
            text = r.json().get("response", "")
            if expect_json:
                return json.loads(text)
            return text
    except Exception as e:
        print(f"    Ollama error: {e}")
    return None


def ollama_classify(name):
    prompt = (
        f'Classify this dance move: "{name}"\n'
        f'Available dance styles: {", ".join(style_names)}\n'
        f'Available musical styles: {", ".join(music_names)}\n'
        f'Return ONLY valid JSON: {{"dance_styles": ["exact name from list"], "musical_styles": ["exact name from list"], '
        f'"difficulty": "Beginner" or "Intermediate" or "Advanced" or "None", "description": "one sentence"}}\n'
        f'Only use names exactly as listed. Use [] if nothing fits.'
    )
    result = ollama_request(prompt, expect_json=True)
    return result or {}


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


def search_youtube(query):
    """Search YouTube and return best video ID."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings",
             "--flat-playlist", f"ytsearch3:{query}"],
            capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace'
        )
        best = None
        best_views = -1
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                vid_id = item.get("id", "")
                if len(vid_id) != 11:
                    continue
                views = item.get("view_count") or 0
                if views > best_views:
                    best_views = views
                    best = vid_id
            except:
                pass
        return best
    except Exception as e:
        print(f"    yt-dlp error: {e}")
        return None


ok_count = 0
skip_count = 0
fail_count = 0

print("\n=== Phase 3b: Ollama gap-fill for underrepresented styles ===\n")

for style_name in TARGET_STYLES:
    print(f"\n--- Style: {style_name} ---")

    # Ask Ollama for 50 dance moves
    prompt = (
        f'List 50 well-known {style_name} dance moves, steps, or techniques that a dancer should learn.\n'
        f'Return ONLY a JSON array of strings, no explanation, no numbering.'
    )

    result = ollama_request(prompt, expect_json=True, timeout=90)

    if result is None:
        print(f"  Ollama failed for {style_name}, skipping")
        continue

    # Handle both list and dict responses
    if isinstance(result, list):
        moves = result
    elif isinstance(result, dict):
        # Try common keys
        for key in ("moves", "steps", "techniques", "dances", "list", "items"):
            if key in result and isinstance(result[key], list):
                moves = result[key]
                break
        else:
            # Flatten all values
            moves = []
            for v in result.values():
                if isinstance(v, list):
                    moves.extend(v)
                elif isinstance(v, str):
                    moves.append(v)
    else:
        moves = []

    print(f"  Got {len(moves)} moves from Ollama")

    # Filter existing
    new_moves = [m for m in moves if isinstance(m, str) and m.strip() and m.strip().lower() not in existing_names]
    print(f"  New moves: {len(new_moves)}")

    for move_name in new_moves:
        move_name = move_name.strip()
        print(f"\n  Processing: {move_name}")

        # Classify
        classification = ollama_classify(move_name)
        dance_styles_cls = classification.get("dance_styles", [])
        musical_styles_cls = classification.get("musical_styles", [])
        difficulty = classification.get("difficulty", "None")
        description = classification.get("description", f"{style_name} move: {move_name}")

        if difficulty not in ("Beginner", "Intermediate", "Advanced"):
            difficulty = "None"

        # If no style matched, use the target style
        style_ids = get_style_ids(dance_styles_cls)
        if not style_ids:
            style_ids = get_style_ids([style_name])

        music_ids = get_music_ids(musical_styles_cls)

        # Create dance
        dance_payload = {
            "name": move_name,
            "description": description,
            "difficulty": difficulty,
            "styleIds": style_ids,
            "musicalStyleIds": music_ids,
            "instructorIds": []
        }

        dance_id = None
        try:
            r = requests.post(f"{API_BASE}/dances", json=dance_payload, headers=headers, timeout=30)
            if r.status_code == 409:
                print(f"    SKIP 409: {move_name}")
                skip_count += 1
                existing_names.add(move_name.lower())
                continue
            elif r.status_code >= 400:
                print(f"    FAIL {r.status_code}: {move_name} — {r.text[:100]}")
                fail_count += 1
                continue
            dance_id = r.json().get("id")
            existing_names.add(move_name.lower())
            ok_count += 1
            print(f"    Dance OK (id={dance_id})")
        except Exception as e:
            print(f"    FAIL (dance POST): {e}")
            fail_count += 1
            continue

        # Search YouTube
        yt_query = f"{move_name} {style_name} dance tutorial"
        vid_id = search_youtube(yt_query)
        if vid_id:
            video_payload = {
                "title": move_name,
                "videoId": vid_id,
                "platform": "youtube",
                "danceId": dance_id
            }
            try:
                vr = requests.post(f"{API_BASE}/videos", json=video_payload, headers=headers, timeout=30)
                if vr.status_code < 400:
                    print(f"    Video OK ({vid_id})")
                else:
                    print(f"    Video WARN {vr.status_code}: {vr.text[:80]}")
            except Exception as e:
                print(f"    Video error: {e}")
        else:
            print(f"    No YouTube video found")

print(f"\n=== Phase 3b Complete ===")
print(f"OK: {ok_count} | SKIP: {skip_count} | FAIL: {fail_count}")
