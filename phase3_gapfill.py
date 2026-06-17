"""Phase 3: Gap-fill using Ollama knowledge per dance style."""
import json
import urllib.request
import urllib.error
import subprocess
import time
import re

API_BASE = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"
YT_RE = re.compile(r"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def api_get(path, token=None):
    req = urllib.request.Request(f"{API_BASE}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def api_post(path, body, token=None, retries=3):
    data = json.dumps(body).encode()
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{API_BASE}{path}", data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")
        except (TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries - 1:
                print(f" [retry {attempt+1}]", end="", flush=True)
                time.sleep(3)
    raise RuntimeError(f"Timeout after {retries} attempts: {last_err}")


def ollama_list_moves(style_name):
    prompt = (
        f"List 30 well-known {style_name} dance moves or steps a beginner should learn. "
        f"Return ONLY a JSON array of strings, no explanation. "
        f'Example: ["Running Man", "Cabbage Patch"]'
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
            raw = resp["response"]
            # Try to parse the response as JSON
            try:
                result = json.loads(raw)
                if isinstance(result, list):
                    return result
                # Sometimes Ollama wraps in an object
                for v in result.values():
                    if isinstance(v, list):
                        return v
            except Exception:
                # Try to extract a JSON array from the text
                m = re.search(r'\[.*?\]', raw, re.DOTALL)
                if m:
                    return json.loads(m.group(0))
    except Exception as e:
        print(f"  [Ollama list error] {e}")
    return []


def ollama_classify(name, style_names, music_names):
    styles_str = ", ".join(style_names)
    music_str = ", ".join(music_names)
    prompt = (
        f"You are a dance classification expert. Classify this dance move for a learning platform.\n\n"
        f"Available dance styles: {styles_str}\n"
        f"Available musical styles: {music_str}\n\n"
        f"Dance name: \"{name}\"\n\n"
        f"Return ONLY valid JSON with these exact keys:\n"
        f"dance_styles (array of exact names from the list, or empty array),\n"
        f"musical_styles (array of exact names from the list, or empty array),\n"
        f"difficulty (one of: Beginner, Intermediate, Advanced, None),\n"
        f"description (one sentence describing the move)\n\n"
        f"Only use names exactly as listed. Use empty array [] if nothing matches."
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
            return json.loads(resp["response"])
    except Exception as e:
        print(f"  [Ollama classify error] {e}")
        return {"dance_styles": [], "musical_styles": [], "difficulty": "None", "description": ""}


def ytdlp_search(query, count=3, timeout=45):
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings",
             "--flat-playlist", f"ytsearch{count}:{query}"],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
        results = []
        for line in r.stdout.strip().splitlines():
            if line.strip():
                try:
                    results.append(json.loads(line))
                except Exception:
                    pass
        return results
    except subprocess.TimeoutExpired:
        return []
    except Exception as e:
        print(f"  [yt-dlp error] {e}")
        return []


def search_youtube(dance_name, style_hint=""):
    query = f"{dance_name} {style_hint} dance tutorial".strip()
    results = ytdlp_search(query, count=3)
    if not results:
        return None
    best = max(results, key=lambda v: v.get("view_count") or 0)
    vid_id = best.get("id", "")
    if not vid_id or len(vid_id) != 11:
        m = YT_RE.search(best.get("webpage_url", ""))
        vid_id = m.group(1) if m else None
    if not vid_id:
        return None
    return {
        "platform": "youtube",
        "video_id": vid_id,
        "title": best.get("title", dance_name),
    }


def search_tiktok(dance_name):
    results = ytdlp_search(f"ttsearch:{dance_name} dance", count=3, timeout=30)
    if not results:
        return None
    best = max(results, key=lambda v: v.get("view_count") or 0)
    vid_id = best.get("id")
    if not vid_id:
        return None
    return {
        "platform": "tiktok",
        "video_id": str(vid_id),
        "title": best.get("title", dance_name),
    }


def main():
    # Login
    auth = api_post("/auth/login", {"username": "justas", "password": "Dance@Admin2026"})
    TOKEN = auth["token"]
    print("Logged in")

    styles = api_get("/styles", TOKEN)
    music_styles = api_get("/musicalstyles", TOKEN)
    style_map = {s["name"].lower(): s["id"] for s in styles}
    music_map = {ms["name"].lower(): ms["id"] for ms in music_styles}
    style_names = [s["name"] for s in styles]
    music_names = [ms["name"] for ms in music_styles]

    dances = api_get("/dances", TOKEN)
    existing_names = {d["name"].lower() for d in dances}
    print(f"Current dances: {len(dances)}")

    total_created = 0
    total_skipped = 0
    total_failed = 0
    created_dances = []

    for style in styles:
        style_name = style["name"]
        print(f"\n=== Style: {style_name} ===")

        # Ask Ollama for 30 moves for this style
        print(f"  Asking Ollama for {style_name} moves...")
        moves = ollama_list_moves(style_name)
        print(f"  Got {len(moves)} moves from Ollama")

        new_moves = [m for m in moves if m.lower() not in existing_names and m.strip()]
        print(f"  {len(new_moves)} new (not in database)")

        for i, move_name in enumerate(new_moves):
            move_name = move_name.strip()
            if not move_name:
                continue
            name_lower = move_name.lower()
            if name_lower in existing_names:
                total_skipped += 1
                continue

            print(f"  [{i+1}/{len(new_moves)}] {move_name}...", end=" ", flush=True)

            # Classify
            classification = ollama_classify(move_name, style_names, music_names)
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

            try:
                dance = api_post("/dances", {
                    "name": move_name,
                    "description": description or None,
                    "difficulty": difficulty,
                    "styleIds": dance_style_ids,
                    "musicalStyleIds": music_style_ids,
                    "instructorIds": []
                }, TOKEN)
                dance_id = dance["id"]
                existing_names.add(name_lower)
                print(f"OK (#{dance_id}) diff={difficulty}", end=" ")

                # Search YouTube for video
                style_hint = classification.get("dance_styles", [style_name])[0] if classification.get("dance_styles") else style_name
                print(f"| YT search...", end=" ", flush=True)
                video = search_youtube(move_name, style_hint)
                if not video:
                    print(f"| TikTok...", end=" ", flush=True)
                    video = search_tiktok(move_name)

                if video:
                    try:
                        api_post("/videos", {
                            "title": video["title"],
                            "videoId": video["video_id"],
                            "platform": video["platform"],
                            "danceId": dance_id,
                            "startTime": None,
                            "endTime": None,
                        }, TOKEN)
                        print(f"video={video['platform']}:{video['video_id'][:8]}")
                    except Exception as ve:
                        print(f"video fail: {str(ve)[:60]}")
                else:
                    print(f"no video found")

                total_created += 1
                created_dances.append({
                    "id": dance_id,
                    "name": move_name,
                    "difficulty": difficulty,
                    "styles": dance_style_ids,
                    "style_name": style_name
                })

            except RuntimeError as e:
                err = str(e)
                if "409" in err or "already" in err.lower() or "exist" in err.lower():
                    print(f"SKIP (409)")
                    existing_names.add(name_lower)
                    total_skipped += 1
                elif "5" in err[:8]:
                    print(f"5xx error, skip: {err[:80]}")
                    total_failed += 1
                else:
                    print(f"FAIL: {err[:100]}")
                    total_failed += 1

            time.sleep(0.3)

    print(f"\n=== Phase 3 Complete ===")
    print(f"Created: {total_created}")
    print(f"Skipped: {total_skipped}")
    print(f"Failed:  {total_failed}")

    result = {
        "created": total_created,
        "skipped": total_skipped,
        "failed": total_failed,
        "dances": created_dances
    }
    with open("/tmp/phase3_created.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("Saved to /tmp/phase3_created.json")
    return result


if __name__ == "__main__":
    main()
