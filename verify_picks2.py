"""verify_picks2.py — embeddability + duration for round-2 picks. Writes _proto/picks_verified2.tsv."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")

PICKS = [
 ("Mnike", 28, 16, "AQJY7H9YzEM", "Mnike Dance Tutorial | Tyler ICU | Amapiano"),
 ("Sbhujwa", 28, 16, "2v1r6dU5cNU", "Original Sbhujwa Dance Footwork Tutorial | Itshu'Prince"),
 ("Vrrr", 28, 16, "CgiQS6NOhjk", "Lithi Vrrr Amapiano Dance Tutorial | Officixl RSA & Benzoo"),
 ("Zenzele", 28, 16, "4R25tgsDqRs", "Learn the Zenzele Amapiano Dance Step-by-Step"),
 ("Running Man Shuffle", 29, 6, "EP3Q3ttFwtU", "The Easiest Running Man Tutorial Ever! | Shuffle Dance Basics 101"),
 ("V-Step", 29, 6, "p62KZ-JWPOM", "V-Step - Shuffle Dance Tutorial | Shuffle Shred"),
 ("Diamond Step", 29, 6, "MfxMSQNrPi4", "Diamond Shuffle Tutorial | Learn the Basics + Tips"),
 ("Hard Style", 29, 6, "8_5lEw14f9w", "Hardstyle Shuffle Tutorial (Learn in 6 Steps)"),
 ("Get Lite", 30, 3, "CNLZv3J45mw", "Learn to Dance Litefeet (Foundations) with Rob Wilson"),
 ("Bad One", 30, 3, "9rUfaClye8A", "How To Do A Bad One - Litefeet Tutorial"),
 ("Soapy", 13, 11, "TZodOPRfwVc", "Naira Marley - Soapy (Dance Workshop)"),
 ("Kupe", 13, 11, "blU1AkJmICk", "How To Kupe Dance Tutorial (In Less Than 5 Minutes)"),
 ("Tek Weh Yuhself", 14, 12, "QsRAJwvLvsA", "How to dance dancehall: Tek Weh Yuhself - Blacka Di Danca"),
 ("Wacky Dip", 14, 12, "mmvZ-XPV904", "Wacky Dip Dancehall Dance Tutorial"),
 ("Skip To Ma Lou", 14, 12, "qCtFxIb3Bm0", "How to Dancehall - Skip to My Lou"),
 ("Row Di Boat", 14, 12, "KO7DMEbObDw", "How Fi Dance Reggae - Row the Boat"),
 ("Catwalk", 16, 6, "pFB7otywSTc", "The Five Elements of Vogue Episode 1 - Catwalk"),
 ("Floor Performance", 16, 6, "tqUEcEsA3gQ", "The Five Elements of Vogue Episode 4: Floor Performance"),
 ("Jazz Pirouette", 20, 4, "6YfqrebP99o", "Jazz Pirouette Tutorial - 5 Easy Steps!"),
 ("APT. Challenge", 31, 3, "zgM_WKCjq6Y", "APT. - Rose & Bruno Mars Step-by-Step Dance Tutorial"),
 ("Magnetic (ILLIT)", 31, 3, "KfU37WXmWYc", "ILLIT 'Magnetic' Lisa Rhee Dance Tutorial"),
 ("Supernova (aespa)", 31, 3, "41hudRIS8Hs", "aespa 'Supernova' Lisa Rhee Dance Tutorial"),
 ("Floorwork", 7, 2, "wY8919ZVOwU", "5 Beautiful Floorwork Moves For Beginners - Part 1"),
 ("Tilt", 7, 2, "GBBIFWRIHqY", "How To Do A Tilt | 5 Minute Tutorial"),
 ("Marcaje", 18, 10, "pAT7TNSRzGk", "Flamenco Basics: Marking (Marcaje) Technique"),
 ("Vuelta", 18, 10, "_drm7f0eqtM", "Flamenco Basics: Turns (Vueltas) Technique"),
]
out = open("_proto/picks_verified2.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download", "-J",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout)
        emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:22} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1
            out.write(f"{name}\t{sid}\t{mid}\t{vid}\t{dur}\t{title}\n")
        else:
            bad += 1
    except Exception as e:
        bad += 1
        print(f"  [ERR ] {name:22} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified2.tsv")
