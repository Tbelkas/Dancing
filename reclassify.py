#!/usr/bin/env python3
"""
reclassify.py — Reclassify all 1,654 dances using Ollama llama3.1:8b.
Assigns dance styles, musical styles, difficulty, and description.
Supports resuming from reclassify_progress.json if interrupted.
"""
import json
import os
import re
import sys
import time
import requests

API_BASE = "https://dance-api.takelord.com/api"
USERNAME = "justas"
PASSWORD = "Dance@Admin2026"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT = 90
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reclassify_progress.json")
SAVE_EVERY = 50

STYLE_DEFINITIONS = """Dance style definitions:
- Hip-hop: Street dances born from hip-hop culture -- popping, locking, b-boying, krumping, tutting, etc.
- Street / Urban: Broader street dance umbrella -- shuffling, turfing, lite feet, jerkin, etc.
- Latin: Partner dances from Latin America -- salsa, bachata, merengue, cumbia, cha-cha, etc.
- Waacking: Arm-throwing club dance from the 1970s gay disco scene.
- Ballroom: Formal partner dances -- waltz, foxtrot, quickstep, tango, viennese waltz, etc.
- Classical / Ballet: Ballet and classical dance technique -- plies, arabesques, pirouettes, etc.
- House: Dance style from Chicago/NYC house music clubs -- jacking, footwork, lofting.
- Contemporary: Modern concert dance blending ballet, jazz, and improvisation.
- Swing: Partner dances to swing/jazz music -- lindy hop, east coast swing, jive, balboa.
- Folk / Traditional: Traditional cultural dances -- irish step, flamenco, bhangra, polka, etc.
- Tektonik: French electro dance with sharp arm movements and footwork.
- Breakdance: Breaking / b-boying -- toprock, downrock, freezes, power moves.
- Afrobeats: West African-influenced club dance to afrobeats/afropop music.
- Dancehall: Jamaican dance style to dancehall/reggae music.
- Krump: Highly expressive, aggressive street dance -- chest pops, stomps, arm swings.
- Vogue: Ballroom culture dance -- catwalk, dips, spins, hand performance.
- Bhangra: Punjabi harvest dance with energetic jumps and dhol drumbeat.
- Flamenco: Spanish dance with footwork (zapateado), arm gestures, and emotional expression.
- Tap: Percussive dance using metal taps on shoes -- shuffles, flaps, time steps.
- Jazz: Theatre/commercial dance style -- kicks, leaps, turns, isolations, splits.
- K-Pop: Korean pop idol dance style -- synchronized group choreography, sharp movements."""


def login():
    r = requests.post(f"{API_BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["token"]


def fetch_all(token, endpoint):
    r = requests.get(f"{API_BASE}/{endpoint}", params={"pageSize": 5000},
                     headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def build_name_to_id(items):
    """Build a case-insensitive name -> id mapping."""
    return {item["name"].lower(): item["id"] for item in items}


def ollama_classify(dance_name, music_style_names):
    prompt = f"""You are a dance taxonomy expert for a learning platform. Classify this dance move.

Dance name: "{dance_name}"

{STYLE_DEFINITIONS}

Musical style options: {", ".join(music_style_names)}

Rules:
1. Assign 1-2 dance styles maximum. Prefer 1 unless the move genuinely spans two distinct styles.
2. Assign 1-3 musical styles that best match where this dance move is performed.
3. Difficulty: Beginner (simple steps, little coordination), Intermediate (moderate skill), Advanced (high skill, strength, or flexibility). Use "None" only if truly unclassifiable.
4. Description: one clear sentence about what the move is and how it's performed.
5. Use EXACT style names from the list above.

Return ONLY valid JSON:
{{"dance_styles": ["exact style name"], "musical_styles": ["exact music style name"], "difficulty": "Beginner|Intermediate|Advanced|None", "description": "one sentence"}}"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
    r.raise_for_status()
    raw = r.json()["response"]
    return json.loads(raw)


def update_dance(token, dance_id, style_ids, musical_style_ids, difficulty, description):
    payload = {
        "styleIds": style_ids,
        "musicalStyleIds": musical_style_ids,
        "difficulty": difficulty,
        "description": description,
    }
    r = requests.put(
        f"{API_BASE}/dances/{dance_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()


def map_styles(names, name_to_id):
    """Map a list of style names (case-insensitive) to IDs, skipping unknowns."""
    ids = []
    for name in names:
        key = name.lower().strip()
        if key in name_to_id:
            ids.append(name_to_id[key])
        else:
            # Try partial match
            matched = [v for k, v in name_to_id.items() if key in k or k in k]
            # Ignore ambiguous partial matches
    return list(dict.fromkeys(ids))  # deduplicate preserving order


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed_ids": [], "results": {}}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def main():
    print("Logging in...")
    token = login()

    print("Fetching styles, musical styles, and dances...")
    styles = fetch_all(token, "styles")
    music_styles = fetch_all(token, "musicalstyles")
    dances = fetch_all(token, "dances")

    style_name_to_id = build_name_to_id(styles)
    music_name_to_id = build_name_to_id(music_styles)
    music_style_names = [m["name"] for m in music_styles]

    print(f"  {len(styles)} dance styles, {len(music_styles)} musical styles, {len(dances)} dances")

    # Load progress for resume
    progress = load_progress()
    processed_ids = set(progress.get("processed_ids", []))
    results = progress.get("results", {})

    if processed_ids:
        print(f"Resuming: {len(processed_ids)} already processed, {len(dances) - len(processed_ids)} remaining")

    total = len(dances)
    reclassified = 0
    timeout_count = 0
    fail_count = 0
    since_last_save = 0

    for i, dance in enumerate(dances, 1):
        dance_id = dance["id"]
        dance_name = dance["name"]

        if dance_id in processed_ids:
            print(f"[{i}/{total}] SKIP {dance_name!r} (already processed)")
            continue

        # Call Ollama
        try:
            result = ollama_classify(dance_name, music_style_names)
        except requests.Timeout:
            print(f"[TIMEOUT] {dance_name!r}")
            timeout_count += 1
            processed_ids.add(dance_id)
            progress["processed_ids"] = list(processed_ids)
            since_last_save += 1
            if since_last_save >= SAVE_EVERY:
                save_progress(progress)
                since_last_save = 0
            continue
        except Exception as e:
            print(f"[OLLAMA-FAIL] {dance_name!r}: {e}")
            fail_count += 1
            continue

        # Extract fields
        raw_dance_styles = result.get("dance_styles", [])
        raw_music_styles = result.get("musical_styles", [])
        difficulty = result.get("difficulty", "None")
        description = result.get("description", "")

        # Validate difficulty
        if difficulty not in ("Beginner", "Intermediate", "Advanced", "None"):
            difficulty = "None"

        # Map to IDs
        style_ids = map_styles(raw_dance_styles, style_name_to_id)
        music_style_ids = map_styles(raw_music_styles, music_name_to_id)

        # Update via API
        try:
            update_dance(token, dance_id, style_ids, music_style_ids, difficulty, description)
            style_names = [s for s in raw_dance_styles if s.lower().strip() in style_name_to_id]
            print(f"[{i}/{total}] {dance_name!r} -> {style_names} | {difficulty}")
            reclassified += 1

            # Track results for summary
            for s in style_names:
                results[s] = results.get(s, 0) + 1

        except requests.HTTPError as e:
            print(f"[FAIL] {dance_name!r}: {e}")
            fail_count += 1

        processed_ids.add(dance_id)
        progress["processed_ids"] = list(processed_ids)
        progress["results"] = results
        since_last_save += 1

        if since_last_save >= SAVE_EVERY:
            save_progress(progress)
            since_last_save = 0
            print(f"  [CHECKPOINT] Progress saved ({len(processed_ids)}/{total})")

    # Final save
    save_progress(progress)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total reclassified: {reclassified}")
    print(f"Timeouts:           {timeout_count}")
    print(f"Failures:           {fail_count}")
    print()

    # Count zero-style and None difficulty from re-fetching all dances
    print("Fetching final state for summary...")
    final_dances = fetch_all(token, "dances")
    zero_style = sum(1 for d in final_dances if not d.get("styles"))
    none_diff = sum(1 for d in final_dances if d.get("difficulty") == "None")
    print(f"Dances with 0 styles:       {zero_style}")
    print(f"Dances with difficulty None: {none_diff}")

    print()
    print("Per-style counts (from this run):")
    for style_name, count in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  {style_name}: {count}")


if __name__ == "__main__":
    main()
