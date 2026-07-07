"""
phase_newstyles.py — Add NEW dance styles + seed dances for them.

Phase 0: Baseline (login, get styles/music/dances)
Phase 1: Ask Ollama for new styles, create them + missing musical styles
Phase 2: For each new style, ask Ollama for 40 moves, classify & create dances + videos
Phase 3: YouTube timestamp discovery for new styles
Phase 4: Verification summary
"""

import json
import urllib.request
import urllib.error
import subprocess
import time
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

API_BASE = "https://dance-api.takelord.com/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"
YT_RE = re.compile(r"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})")

KNOWN_STYLES = {
    "hip-hop", "street / urban", "latin", "waacking", "ballroom",
    "classical / ballet", "house", "contemporary", "swing",
    "folk / traditional", "tektonik"
}

# Target styles to add — canonical list we want created
TARGET_STYLES = [
    {"name": "Breakdance", "description": "An acrobatic street dance style featuring power moves, freezes, and footwork, originating from the Bronx in the 1970s."},
    {"name": "Afrobeats", "description": "A high-energy dance style rooted in West African rhythms and modern Afropop music, featuring hip-centric isolations and fluid body movements."},
    {"name": "Dancehall", "description": "A vibrant Jamaican dance style born from reggae and dancehall music, known for its energetic footwork, body rolls, and expressive partner or solo movements."},
    {"name": "Krump", "description": "An intense, emotionally expressive street dance style from Los Angeles characterized by big arm movements, chest pops, and stomps."},
    {"name": "Vogue", "description": "A highly stylized dance style originating in the Harlem ballroom scene, featuring model-like poses, catwalk struts, and fluid arm movements inspired by fashion magazine poses."},
    {"name": "Bhangra", "description": "A lively folk dance from the Punjab region of South Asia, traditionally performed to dhol drumming and characterized by high-energy kicks, jumps, and arm movements."},
    {"name": "Flamenco", "description": "A passionate Spanish art form combining intricate footwork, expressive arm movements, and emotional vocals, originating in Andalusia."},
    {"name": "Tap", "description": "A percussive dance style in which dancers use metal-tipped tap shoes to create rhythmic sounds, blending jazz, Irish jig, and African rhythms."},
    {"name": "Jazz", "description": "An energetic theatrical dance style that evolved from African American vernacular dance, characterized by improvisation, syncopated rhythms, and expressive movements."},
    {"name": "K-Pop", "description": "A synchronized and highly choreographed pop dance style originating from South Korean pop music, featuring sharp formations, precise arm work, and idol group aesthetics."},
]

# Musical styles we expect to exist or create
DESIRED_MUSICAL_STYLES = [
    {"name": "Afrobeats", "description": "West African-influenced contemporary popular music blending traditional African rhythms with modern production."},
    {"name": "Dancehall", "description": "Jamaican popular music evolved from reggae, typically featuring digital riddims and toasting vocals."},
    {"name": "Bhangra", "description": "Punjabi folk music driven by the dhol drum, with energetic rhythms traditionally tied to harvest celebrations."},
    {"name": "Flamenco", "description": "Traditional Andalusian music combining guitar, handclaps, and passionate vocals in complex rhythmic patterns."},
    {"name": "J-Pop / K-Pop", "description": "East Asian pop music produced in Japan and South Korea, known for polished production, synchronized choreography, and idol culture."},
]


# ─── HTTP helpers ────────────────────────────────────────────────────────────

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
            code = e.code
            body_text = e.read().decode()[:300]
            if code == 409:
                raise RuntimeError(f"HTTP 409: {body_text}")
            if code in (400, 401, 403, 404):
                raise RuntimeError(f"HTTP {code}: {body_text}")
            # 5xx — retry
            last_err = RuntimeError(f"HTTP {code}: {body_text}")
            if attempt < retries - 1:
                print(f" [retry {attempt+1} after {code}]", end="", flush=True)
                time.sleep(3)
        except (TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries - 1:
                print(f" [retry {attempt+1}]", end="", flush=True)
                time.sleep(3)
    raise RuntimeError(f"Failed after {retries} attempts: {last_err}")


# ─── Ollama helpers ───────────────────────────────────────────────────────────

def ollama(prompt, timeout=90):
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    return json.loads(resp["response"])


def ollama_list_moves(style_name, count=40):
    prompt = (
        f"You are a dance expert. List {count} well-known {style_name} dance moves, steps, or techniques "
        f"that would appear on a dance learning platform. Include specific named moves, not generic descriptions. "
        f'Return JSON object: {{"moves": ["Move Name 1", "Move Name 2", ...]}}'
    )
    try:
        result = ollama(prompt, timeout=120)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("moves", "steps", "dance_moves", "list", "dances", "results", "techniques"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            for v in result.values():
                if isinstance(v, list) and len(v) > 0:
                    return v
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
        f"dance_styles (array of exact names from the list — pick the most relevant, can be multiple),\n"
        f"musical_styles (array of exact names from the list, or empty array),\n"
        f"difficulty (one of: Beginner, Intermediate, Advanced, None),\n"
        f"description (one sentence describing the move)\n\n"
        f"Only use names EXACTLY as listed. Empty array [] if nothing matches."
    )
    try:
        result = ollama(prompt, timeout=90)
        if isinstance(result, dict):
            return result
    except Exception as e:
        print(f"  [Ollama classify error] {e}")
    return {"dance_styles": [], "musical_styles": [], "difficulty": "None", "description": ""}


# ─── YouTube helpers ──────────────────────────────────────────────────────────

def ytdlp_search(query, count=3, timeout=45):
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings",
             "--flat-playlist", f"ytsearch{count}:{query}"],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace"
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


def ytdlp_full(url, timeout=60):
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings", url],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace"
        )
        for line in r.stdout.strip().splitlines():
            if line.strip():
                try:
                    return json.loads(line)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def search_youtube_best(dance_name, style_hint=""):
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
        "view_count": best.get("view_count") or 0,
    }


TS_PATTERNS = [
    re.compile(r"^[\s\d\.\)\-\*]*(.+?)\s*[\[\(](\d{1,2}:\d{2}(?::\d{2})?)[\]\)]\s*$"),
    re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*$"),
]


def parse_timestamp_lines(text):
    """Extract (name, timestamp_str) pairs from video description text."""
    moves = []
    for line in (text or "").splitlines():
        line = line.strip()
        for pat in TS_PATTERNS:
            m = pat.match(line)
            if m:
                if pat.pattern.startswith(r"^[\s\d"):
                    name, ts = m.group(1).strip(), m.group(2)
                else:
                    ts, name = m.group(1), m.group(2).strip()
                if len(name) >= 3 and not name.isdigit():
                    moves.append((name, ts))
                break
    return moves


def ts_to_seconds(ts):
    parts = ts.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


def create_dance(name, classification, style_map, music_map, token):
    """Create dance via API, return (dance_id, status_str)."""
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
    description = classification.get("description", "") or ""

    try:
        dance = api_post("/dances", {
            "name": name,
            "description": description or None,
            "difficulty": difficulty,
            "styleIds": dance_style_ids,
            "musicalStyleIds": music_style_ids,
            "instructorIds": [],
        }, token)
        return dance["id"], "created"
    except RuntimeError as e:
        err = str(e)
        if "409" in err:
            return None, "duplicate"
        return None, f"error: {err[:100]}"


def link_video(dance_id, video_id, platform, title, token, start=None, end=None):
    try:
        api_post("/videos", {
            "title": title,
            "videoId": video_id,
            "platform": platform,
            "danceId": dance_id,
            "startTime": start,
            "endTime": end,
        }, token)
        return "ok"
    except RuntimeError as e:
        return f"fail: {str(e)[:80]}"


# ─── Phase 0: Baseline ────────────────────────────────────────────────────────

print("\n" + "="*60)
print("PHASE 0 — BASELINE")
print("="*60)

auth = api_post("/auth/login", {"username": "justas", "password": "Dance@Admin2026"})
TOKEN = auth["token"]
print(f"Logged in. Token: {TOKEN[:30]}...")

styles = api_get("/styles", TOKEN)
musical_styles = api_get("/musicalstyles", TOKEN)
dances = api_get("/dances", TOKEN)

existing_names = {d["name"].lower() for d in dances}
style_map = {s["name"].lower(): s["id"] for s in styles}
music_map = {ms["name"].lower(): ms["id"] for ms in musical_styles}
style_names_all = [s["name"] for s in styles]
music_names_all = [ms["name"] for ms in musical_styles]

print(f"Existing styles ({len(styles)}): {[s['name'] for s in styles]}")
print(f"Existing musical styles ({len(musical_styles)}): {[ms['name'] for ms in musical_styles]}")
print(f"Existing dances: {len(dances)}")

INITIAL_DANCE_COUNT = len(dances)

# ─── Phase 1: Create new styles ──────────────────────────────────────────────

print("\n" + "="*60)
print("PHASE 1 — CREATE NEW STYLES")
print("="*60)

new_styles_created = []

for style_def in TARGET_STYLES:
    sname = style_def["name"]
    sname_lower = sname.lower()

    # Check if it already exists (case-insensitive)
    already = any(
        sname_lower == ex.lower() or sname_lower in ex.lower() or ex.lower() in sname_lower
        for ex in style_map
    )
    if already:
        print(f"  SKIP (exists): {sname}")
        # Still add to our map so we can reference it
        # Find the real one
        for real_name, real_id in style_map.items():
            if sname_lower in real_name or real_name in sname_lower:
                new_styles_created.append({"id": real_id, "name": sname, "real_name": real_name})
                break
        continue

    try:
        result = api_post("/styles", {"name": sname, "description": style_def["description"]}, TOKEN)
        new_id = result["id"]
        style_map[sname_lower] = new_id
        style_names_all.append(sname)
        new_styles_created.append({"id": new_id, "name": sname})
        print(f"  OK: {sname} (id={new_id})")
    except RuntimeError as e:
        err = str(e)
        if "409" in err:
            print(f"  SKIP 409: {sname}")
            # Try to find it
            styles_fresh = api_get("/styles", TOKEN)
            for s in styles_fresh:
                if s["name"].lower() == sname_lower:
                    style_map[sname_lower] = s["id"]
                    if sname not in style_names_all:
                        style_names_all.append(sname)
                    new_styles_created.append({"id": s["id"], "name": sname})
                    break
        else:
            print(f"  FAIL: {sname} — {err[:120]}")

print(f"\nStyles created/found: {len(new_styles_created)}")
for s in new_styles_created:
    print(f"  {s['name']} (id={s['id']})")

# Refresh style_map from API
styles_fresh = api_get("/styles", TOKEN)
style_map = {s["name"].lower(): s["id"] for s in styles_fresh}
style_names_all = [s["name"] for s in styles_fresh]

# ─── Create missing musical styles ───────────────────────────────────────────
print("\n--- Creating missing musical styles ---")
for ms_def in DESIRED_MUSICAL_STYLES:
    msname = ms_def["name"]
    msname_lower = msname.lower()
    already = any(msname_lower in k or k in msname_lower for k in music_map)
    if already:
        print(f"  SKIP (exists): {msname}")
        continue
    try:
        result = api_post("/musicalstyles", {"name": msname, "description": ms_def["description"]}, TOKEN)
        new_id = result["id"]
        music_map[msname_lower] = new_id
        music_names_all.append(msname)
        print(f"  OK: {msname} (id={new_id})")
    except RuntimeError as e:
        err = str(e)
        if "409" in err:
            print(f"  SKIP 409: {msname}")
        else:
            print(f"  FAIL: {msname} — {err[:120]}")

# Refresh music map
musical_styles_fresh = api_get("/musicalstyles", TOKEN)
music_map = {ms["name"].lower(): ms["id"] for ms in musical_styles_fresh}
music_names_all = [ms["name"] for ms in musical_styles_fresh]

print(f"\nAll dance styles now ({len(style_names_all)}): {style_names_all}")
print(f"All musical styles now ({len(music_names_all)}): {music_names_all}")

# ─── Phase 2: Seed dances for each new style ─────────────────────────────────

print("\n" + "="*60)
print("PHASE 2 — SEED DANCES FOR NEW STYLES")
print("="*60)

phase2_stats = {}
total_created = 0
total_skipped = 0
total_failed = 0
total_videos = 0

for style_entry in new_styles_created:
    style_name = style_entry["name"]
    style_id = style_entry["id"]
    print(f"\n--- Style: {style_name} ---")

    print(f"  Asking Ollama for {style_name} moves...")
    moves = ollama_list_moves(style_name, count=40)
    print(f"  Got {len(moves)} moves: {moves[:5]}...")

    new_moves = [
        m.strip() for m in moves
        if isinstance(m, str) and m.strip() and m.strip().lower() not in existing_names
    ]
    print(f"  {len(new_moves)} new to create")

    style_created = 0
    style_skipped = 0
    style_failed = 0
    style_videos = 0

    for i, move_name in enumerate(new_moves):
        name_lower = move_name.lower()
        if name_lower in existing_names:
            style_skipped += 1
            continue

        print(f"  [{i+1}/{len(new_moves)}] {move_name}...", end=" ", flush=True)

        # Classify
        classification = ollama_classify(move_name, style_names_all, music_names_all)

        # Ensure at least the current style is tagged
        if not classification.get("dance_styles"):
            classification["dance_styles"] = [style_name]

        dance_id, status = create_dance(move_name, classification, style_map, music_map, TOKEN)

        if status == "created":
            existing_names.add(name_lower)
            style_created += 1
            total_created += 1

            diff = classification.get("difficulty", "None")
            print(f"OK (id={dance_id}, diff={diff})", end=" ")

            # Find video
            style_hint = style_name
            video = search_youtube_best(move_name, style_hint)
            if video:
                v_status = link_video(dance_id, video["video_id"], video["platform"], video["title"], TOKEN)
                if "ok" in v_status:
                    style_videos += 1
                    total_videos += 1
                    print(f"| video={video['video_id'][:8]}")
                else:
                    print(f"| video fail: {v_status[:50]}")
            else:
                print("| no video")

        elif "duplicate" in status:
            existing_names.add(name_lower)
            style_skipped += 1
            total_skipped += 1
            print("SKIP")
        else:
            style_failed += 1
            total_failed += 1
            print(f"FAIL: {status[:80]}")

        time.sleep(0.2)

    phase2_stats[style_name] = {
        "created": style_created,
        "skipped": style_skipped,
        "failed": style_failed,
        "videos": style_videos,
    }
    print(f"\n  [{style_name}] created={style_created}, skip={style_skipped}, fail={style_failed}, videos={style_videos}")

print(f"\n=== Phase 2 Summary ===")
print(f"Total created: {total_created}")
print(f"Total skipped: {total_skipped}")
print(f"Total failed:  {total_failed}")
print(f"Total videos:  {total_videos}")

# ─── Phase 3: YouTube timestamp discovery for new styles ─────────────────────

print("\n" + "="*60)
print("PHASE 3 — YOUTUBE TIMESTAMP DISCOVERY")
print("="*60)

phase3_created = 0
phase3_skipped = 0
phase3_failed = 0
phase3_videos = 0

TIMESTAMP_QUERIES = [
    "{style} dance moves tutorial timestamps",
    "{style} dance tutorial how to beginners",
    "how to {style} dance complete guide",
]

processed_video_ids = set()

for style_entry in new_styles_created:
    style_name = style_entry["name"]
    print(f"\n--- Phase 3 / {style_name} ---")

    candidate_videos = []

    for tmpl in TIMESTAMP_QUERIES:
        query = tmpl.format(style=style_name)
        results = ytdlp_search(query, count=5, timeout=45)
        for r in results:
            vid_id = r.get("id", "")
            if vid_id and len(vid_id) == 11 and vid_id not in processed_video_ids:
                candidate_videos.append(r)

    print(f"  Found {len(candidate_videos)} candidate videos")

    for vid in candidate_videos:
        vid_id = vid.get("id", "")
        if not vid_id or vid_id in processed_video_ids:
            continue
        processed_video_ids.add(vid_id)

        # Fetch full metadata
        full = ytdlp_full(f"https://youtube.com/watch?v={vid_id}", timeout=60)
        if not full:
            continue

        duration = full.get("duration") or 0
        if duration < 120:  # skip very short clips
            continue

        # Try chapters first
        chapters = full.get("chapters") or []
        ts_moves = []
        if chapters:
            for ch in chapters:
                title = ch.get("title", "").strip()
                start = ch.get("start_time")
                end_t = ch.get("end_time")
                if title and start is not None and len(title) >= 3:
                    ts_moves.append((title, int(start), int(end_t) if end_t else None))

        # Also parse description
        if not ts_moves:
            desc = full.get("description", "")
            parsed = parse_timestamp_lines(desc)
            if parsed:
                # Build (name, start_sec, end_sec) with end = next start
                starts = [ts_to_seconds(ts) for _, ts in parsed]
                for idx, (name, ts) in enumerate(parsed):
                    s = starts[idx]
                    e = starts[idx + 1] if idx + 1 < len(starts) else None
                    ts_moves.append((name, s, e))

        if len(ts_moves) < 4:
            continue  # not enough moves

        new_ts_moves = [(n, s, e) for n, s, e in ts_moves if n.lower() not in existing_names]
        if not new_ts_moves:
            continue

        vid_title = full.get("title", vid_id)
        print(f"  Video [{vid_id}]: {vid_title[:60]} → {len(new_ts_moves)} new moves")

        for (move_name, start_sec, end_sec) in new_ts_moves:
            name_lower = move_name.lower()
            if name_lower in existing_names:
                phase3_skipped += 1
                continue

            print(f"    {move_name}...", end=" ", flush=True)

            classification = ollama_classify(move_name, style_names_all, music_names_all)
            if not classification.get("dance_styles"):
                classification["dance_styles"] = [style_name]

            dance_id, status = create_dance(move_name, classification, style_map, music_map, TOKEN)

            if status == "created":
                existing_names.add(name_lower)
                phase3_created += 1

                v_status = link_video(dance_id, vid_id, "youtube", move_name, TOKEN, start_sec, end_sec)
                if "ok" in v_status:
                    phase3_videos += 1
                    print(f"OK (id={dance_id}) video@{start_sec}s")
                else:
                    print(f"OK (id={dance_id}) no-video")

            elif "duplicate" in status:
                existing_names.add(name_lower)
                phase3_skipped += 1
                print("SKIP")
            else:
                phase3_failed += 1
                print(f"FAIL: {status[:80]}")

            time.sleep(0.2)

print(f"\n=== Phase 3 Summary ===")
print(f"Created: {phase3_created}")
print(f"Skipped: {phase3_skipped}")
print(f"Failed:  {phase3_failed}")
print(f"Videos:  {phase3_videos}")

# ─── Phase 4: Verification ────────────────────────────────────────────────────

print("\n" + "="*60)
print("PHASE 4 — VERIFICATION")
print("="*60)

dances_final = api_get("/dances", TOKEN)
styles_final = api_get("/styles", TOKEN)

final_count = len(dances_final)
added_total = final_count - INITIAL_DANCE_COUNT

style_id_to_name = {s["id"]: s["name"] for s in styles_final}
style_counts = {s["name"]: 0 for s in styles_final}

dances_with_styles = 0
dances_without_styles = 0
diff_counts = {}
desc_count = 0

for d in dances_final:
    dance_styles = d.get("styles") or d.get("danceStyles") or []
    difficulty = d.get("difficulty") or "None"
    description = d.get("description") or ""

    if dance_styles:
        dances_with_styles += 1
        for s in dance_styles:
            if isinstance(s, dict):
                sname = s.get("name") or style_id_to_name.get(s.get("id") or s.get("styleId"), "Unknown")
            else:
                sname = style_id_to_name.get(s, "Unknown")
            if sname in style_counts:
                style_counts[sname] += 1
    else:
        dances_without_styles += 1

    diff_counts[difficulty] = diff_counts.get(difficulty, 0) + 1
    if description and len(description) > 5:
        desc_count += 1

print(f"\nBEFORE: {INITIAL_DANCE_COUNT} dances")
print(f"AFTER:  {final_count} dances")
print(f"ADDED:  {added_total} new dances")
print(f"\nNew styles created: {[s['name'] for s in new_styles_created]}")

print(f"\n--- Per-Style Breakdown (new styles only) ---")
new_style_names_set = {s["name"] for s in new_styles_created}
for sname in sorted(new_style_names_set):
    count = style_counts.get(sname, 0)
    print(f"  {sname:25s}: {count:4d} dances")

print(f"\n--- Per-Style Breakdown (all styles) ---")
for sname, count in sorted(style_counts.items(), key=lambda x: -x[1]):
    pct = (count / final_count * 100) if final_count > 0 else 0
    print(f"  {sname:30s}: {count:4d} ({pct:.1f}%)")

pct_with = dances_with_styles / final_count * 100 if final_count > 0 else 0
print(f"\n  Dances WITH styles:    {dances_with_styles} ({pct_with:.1f}%)")
print(f"  Dances WITHOUT styles: {dances_without_styles} ({100-pct_with:.1f}%)")

print(f"\n--- Difficulty ---")
for diff, cnt in sorted(diff_counts.items(), key=lambda x: -x[1]):
    pct = cnt / final_count * 100 if final_count > 0 else 0
    print(f"  {str(diff):15s}: {cnt:4d} ({pct:.1f}%)")

print(f"\n--- Phase Contributions ---")
print(f"  Phase 2 (Ollama gap-fill per style): {total_created}")
print(f"  Phase 3 (YouTube timestamps):        {phase3_created}")
print(f"  Grand total new dances:              {added_total}")

print(f"\n{'='*60}")
target = 200
if added_total >= target:
    print(f"SUCCESS: Added {added_total} dances (target was {target})")
else:
    print(f"PARTIAL: Added {added_total} dances (target: {target}) — need {target - added_total} more")
print("="*60)
