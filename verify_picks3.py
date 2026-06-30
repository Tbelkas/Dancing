"""verify_picks3.py — embeddability + duration for round-3 picks. Writes _proto/picks_verified3.tsv."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")

PICKS = [
 ("Heels Walk", 32, 3, "zS3vy8_ajiY", "Heels Walking Tutorial | Heels Dance for Beginners"),
 ("Heels Floorwork", 32, 3, "aKOujaCkCRY", "Easy Heels Dance Tutorial | Top 5 Floor Work Moves + Choreography"),
 ("Heels Body Roll", 32, 3, "7Y-moWI31tA", "How To Body Roll in Heels - Beginner Heels Tutorial"),
 ("Hair Flip", 32, 3, "OSaHk-m6ouk", "How to Hair Flip in Heels | 2 Options"),
 ("Reggaeton Basic", 33, 8, "pfml5qilCfI", "Basic Reggaeton for Beginners"),
 ("Dembow", 33, 8, "mOifsJ8lbgk", "Dembow & Reparto Tutorial - Step by Step"),
 ("Reggaeton Hips", 33, 8, "Gwjz_fo5IG4", "Reggaeton Hips | Hip Isolation Tutorial"),
 ("Whiplash (aespa)", 31, 3, "uEhobpQaKUM", "aespa 'Whiplash' Lisa Rhee Dance Tutorial"),
 ("Smart (LE SSERAFIM)", 31, 3, "v4EI6cNJvTs", "LE SSERAFIM 'Smart' Dance Tutorial - Explained"),
 ("How Sweet (NewJeans)", 31, 3, "EDwRljcJJvE", "NewJeans 'How Sweet' Dance Tutorial (Slow + Mirrored + Counts) | SHERO"),
 ("Drip (BABYMONSTER)", 31, 3, "h1K-9hkMyDw", "BABYMONSTER 'Drip' Lisa Rhee Dance Tutorial"),
 ("Sticky (KISS OF LIFE)", 31, 3, "wLbVfAlpsMk", "KISS OF LIFE 'Sticky' Dance Tutorial - Explained + Mirrored"),
 ("Heel Toe", 29, 6, "A-9RWQc4tzE", "How to do the Heel Toe / Happy Feet | Mihran Kirakosian"),
 ("Tshwala Bam", 28, 16, "64iHc91Ho-M", "Tshwala Bami Dance Tutorial | Amapiano"),
 ("Umlando", 28, 16, "ikvvPMqnowo", "Umlando Easy Amapiano Dance Move Tutorial | Beginner Level"),
 ("Rush", 13, 11, "iMEXly1SqiY", "Rush - Ayra Starr (Easy Tutorial, Beginner Friendly)"),
 ("Ginger", 13, 11, "TVD4bz6QaB0", "WizKid - Ginger | Afro Fusion Dance Choreography Tutorial"),
 ("Pon Di River", 14, 12, "NX_hn5HOrwk", "How to dance dancehall: Pon Di River - Blacka Di Danca"),
]
out = open("_proto/picks_verified3.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download", "-J",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout)
        emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:24} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1
            out.write(f"{name}\t{sid}\t{mid}\t{vid}\t{dur}\t{title}\n")
        else:
            bad += 1
    except Exception as e:
        bad += 1
        print(f"  [ERR ] {name:24} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified3.tsv")
