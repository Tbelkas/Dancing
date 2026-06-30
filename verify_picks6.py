"""verify_picks6.py — round 6 embeddability. Writes _proto/picks_verified6.tsv."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")
PICKS = [
 ("Kizomba Basic", 39, 19, "e2fTPLwC62g", "How to Dance Kizomba - 3 Basic Kizomba Steps"),
 ("Kizomba Saida", 39, 19, "_2a2B3wE8VA", "Kizomba Basics - Saida Women | OKS"),
 ("Tarraxinha", 39, 19, "VgTzMiiBKSo", "Tarraxa and Tarraxo Basics Tutorial - Gwany & Liliana"),
 ("Afro House Footwork", 40, 20, "cB08BrQKJsI", "Afro House Footwork Tutorial | manuelkanza"),
 ("Bhenga", 40, 20, "SgWRA3T9Q8A", "Bhenga Dance Tutorial | Box Step (Basic)"),
 ("Vosho", 41, 21, "o2gkbrUVsMk", "How To Vosho (South African Dance) | Chop Daily"),
 ("Gqom Dance", 41, 21, "8hPWO4RqagI", "Hip Hop & Gqom Dance Class"),
 ("Toprock", 12, 3, "KbtWKixraFQ", "5 Beginner Toprocks - How To Breakdance | Coach Sambo"),
 ("Locking Basics", 3, 3, "nuo-6UKqBMI", "Locking Basics | Moon Lee | Beginner's Guide"),
 ("Wrist Rolls", 3, 3, "YexhU2RskzQ", "How to do Wrist Rolls (4 Tips) | Locking Dance Basics"),
 ("Whichaway", 3, 3, "O4nXX4Q_2TI", "How to do the Which-A-Way | Locking Dance Tutorial"),
 ("House Jack", 11, 6, "b-O5ZCVDrHs", "How to Jack: Breakdown of the Jack | Beginner House Dance"),
 ("Loft", 11, 6, "LwaZlJlN3mE", "Legacy of Lofting: Loft Style Dance Session"),
 ("Pink Venom", 31, 3, "0vqH0DcCxzU", "BLACKPINK 'Pink Venom' Lisa Rhee Dance Tutorial"),
 ("Shut Down", 31, 3, "-Y_n2RxTXyc", "BLACKPINK 'Shut Down' Dance Tutorial (Explanation & Mirrored)"),
 ("Baddie (IVE)", 31, 3, "q4yRiSEaNpA", "IVE 'Baddie' Dance Tutorial | Explained + Mirrored"),
 ("Boom Boom Bass (RIIZE)", 31, 3, "CIUO9EuYOhs", "RIIZE 'Boom Boom Bass' Dance Tutorial | SHERO"),
 ("Pullback", 19, 4, "SNhKNaH47bU", "Tap Dance TAP-torial: Learn Pullbacks"),
 ("Popping Basics", 10, 3, "7fXaWDqtuko", "Popping Dance Tutorial For Beginners - Pop And Lock Basics"),
 ("Waving", 10, 3, "9Lk9LAwv6Ng", "Arm Wave Tutorial | Step by Step Dance Tutorial"),
 ("Network", 13, 11, "dRzdtpT6jQQ", "How To Network (Dance Tutorial) | Chop Daily"),
 ("Sare", 13, 11, "jRUYwKvOMr8", "Sare - Ayra Starr | Dance Class with Jinnxx"),
]
out = open("_proto/picks_verified6.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp","--no-warnings","--skip-download","-J",f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout); emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:24} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1; out.write(f"{name}\t{sid}\t{mid}\t{vid}\t{dur}\t{title}\n")
        else: bad += 1
    except Exception as e:
        bad += 1; print(f"  [ERR ] {name:24} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified6.tsv")
