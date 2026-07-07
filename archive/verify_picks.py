"""verify_picks.py — check playable_in_embed + duration for each chosen video.
Prints OK/BAD per (name, ytid). Writes _proto/picks_verified.tsv for the good ones."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")

# (name, styleId, musicId, ytid, title)
PICKS = [
 ("Shaku Shaku", 13, 11, "cbVMLvbskfg", "How To Shaku Shaku (Dance Tutorial) | Chop Daily"),
 ("Gwara Gwara", 13, 11, "rUUgo766Ehc", "Gwara Gwara Dance (Easy Tutorial)"),
 ("Azonto", 13, 11, "AYD-UQNGvRw", "How to Dance Azonto - Class 1 - Afro Dance Tutorial for Beginners"),
 ("Legwork", 13, 11, "qKepPPx7GAo", "How To Legwork Tutorial | Basic, Crossed and Butterfly Variations"),
 ("Sekem", 13, 11, "evPLBXp3Mc4", "Sekem Dance Tutorial | Throwback With Amuna"),
 ("Pilolo", 13, 11, "mOo_uq-h2Lw", "How To Pilolo (Dance Tutorial) | Chop Daily"),
 ("Dutty Wine", 14, 12, "rfW-EqHTjP0", "How to Do the Dutty Wine | Reggae Dancehall | Chriss Choreo"),
 ("Gully Creeper", 14, 12, "SgKX3JMZbNw", "How to Do the Gully Creeper | Reggae Dancehall"),
 ("Nuh Linga", 14, 12, "CqXhQrB9SEc", "How to dance dancehall: Nuh Linga - Blacka Di Danca"),
 ("Willie Bounce", 14, 12, "gg6tDkdHZKo", "How to do Willie Bounce (Dancehall Move) | Jenny JC"),
 ("Bogle", 14, 12, "VE18GZjY3WI", "Bogle - Jamaican Dance Tutorial with Raah Vibez"),
 ("Genna Bounce", 14, 12, "w4aYwByX1WM", "How To Do Genna Bounce"),
 ("Pas de Bourree", 20, 4, "d5-TKHTOTdU", "Learn the Pas de Bourree (Jazz style) - Jazz Dance Basics"),
 ("Fan Kick", 20, 4, "uv4rtUf1CRA", "How to Do the Fan Kick | Jazz Dance"),
 ("Chaine Turns", 20, 4, "OkdUhoGgoOg", "How To Do A Chaine Turn [ Dance Skills Tutorial For Beginners ]"),
 ("Pivot Step", 20, 4, "KnjXoX55LYo", "How to do Pivot Turns"),
 ("Duckwalk", 16, 6, "oqaS2-aKE3c", "The Five Elements of Vogue Episode 3: Duckwalk"),
 ("Hand Performance", 16, 6, "mlYUWmEbrdQ", "Learn to Vogue with NYC Parks: Hand Performance"),
 ("Old Way Vogue", 16, 6, "eBCs9n0p93E", "Old Way Bootcamp Basic #1"),
 ("Spin and Dip", 16, 6, "nCsIqNFfOZw", "Learn to Vogue with NYC Parks: Spins and Dips"),
 ("Contraction", 7, 2, "hIlEb4gkIs4", "How to Do the Contraction | Graham Technique"),
 ("Floor Roll", 7, 2, "Kh8FMlMs1sI", "Different Dance Rolls - Demonstration and Tutorial"),
 ("Spiral", 7, 2, "TMrcOz5fSbE", "How to Dance Contemporary | Beginner's Workshop in Spiralling"),
 ("Zapateado", 18, 10, "Iq0xz59kdMU", "Introduction to Flamenco Footwork - Body Alignment"),
 ("Braceo", 18, 10, "NpRP16Nl3h0", "Flamenco Lesson 8 - Braceo: Introduction to Arm Movements"),
 ("Floreo", 18, 10, "4ceWuC1RRTk", "Floreo (Hand Articulation) - Flamenco Dance"),
 ("King Tut", 22, 3, "IiSIpUffStE", "Tutting - King Tuts - Dance Tutorial - Intro"),
 ("Bacardi", 28, 16, "7EPgy9LHK1o", "How to Bacardi | Dance Tutorial"),
 ("Pouncing Cat", 28, 16, "81ro7if1hdE", "Amapiano Dance Tutorial | Pouncing Cat | Champion Rolie"),
 ("Zekethe", 28, 16, "wbIfdEQpnns", "Zekethe Dance Tutorial Step by Step | Amapiano Dance Move"),
 ("John Vuli Gate", 28, 16, "2feLjpvVmII", "Beginners Amapiano Dance Tutorial | John Vuli Gate | YANA x GASTO"),
 ("T-Step", 29, 6, "LHSWApNdztg", "How To Basic T-Step - Shuffle/Cutting Shapes Dance Tutorial"),
 ("Charleston Shuffle", 29, 6, "4YhzRZDatn8", "Charleston (Beginner) | Cutting Shapes Tutorial"),
 ("Spongebob Shuffle", 29, 6, "ni8wYKZY2qg", "How To Do The Spongebob Dance FAST! For Beginners"),
 ("Cutting Shapes", 29, 6, "F9wrAAAcQL4", "Shuffling for Beginners: Your First 5 Moves to Master"),
 ("Chicken Noodle Soup", 30, 3, "Iogb7ET1GaE", "Chicken Noodle Soup | #ArionLitefeet | ARION Dance"),
 ("Toe Wop", 30, 3, "Q4H2YAsBjAc", "Tone Wop | Litefeet Dance | Tutorial 36"),
 ("Rev Up", 30, 3, "CJvCzHksm54", "How To Do The Whop (Rev Up) - Litefeet Tutorial"),
]

out = open("_proto/picks_verified.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download", "-J",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout)
        emb = d.get("playable_in_embed")
        dur = d.get("duration") or 0
        avail = d.get("availability")
        status = "OK" if emb else "BAD-EMBED"
        print(f"  [{status}] {name:22} {vid}  emb={emb} dur={dur}s avail={avail}")
        if emb:
            good += 1
            out.write(f"{name}\t{sid}\t{mid}\t{vid}\t{dur}\t{title}\n")
        else:
            bad += 1
    except Exception as e:
        bad += 1
        print(f"  [ERR ] {name:22} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified.tsv")
