"""verify_picks10.py — round 10 GENERAL embeddability. Cols: name, styleId, musicId, difficulty, ytid, title.
Writes _proto/picks_verified10.tsv: name<TAB>sid<TAB>mid<TAB>diff<TAB>vid<TAB>dur<TAB>title."""
import subprocess, sys, json
sys.stdout.reconfigure(encoding="utf-8")
PICKS = [
 ("Viennese Waltz", 2, 2, 2, "QwBHYOgs3q0", "Learn Viennese Waltz Basic Steps - Super Easy Beginner Tutorial"),
 ("Argentine Tango Gancho", 1, 5, 3, "zB_3pDRI-FU", "How to Do the Hook aka the Gancho | Argentine Tango"),
 ("Lindy Hop Swingout", 6, 4, 2, "LEmIgdYzy1o", "Lindy Hop Swingout with Swivels Lesson with Frankie Manning"),
 ("Balboa Basic", 6, 4, 2, "9TyBUAcc5P0", "Balboa Basics Summary - Peter and Lorraine"),
 ("Contemporary Floor Work", 7, 2, 2, "ifQ1RrSZNYM", "Contemporary Dance Floor Work Tutorial (Intermediate/Advanced)"),
 ("Lyrical Dance Basics", 7, 2, 1, "QmA4DZC_qwY", "Beginner Lyrical Dance with trainwithkendall"),
 ("Jazz Funk Basics", 20, 3, 1, "zkVDBGQnbms", "Jazz Funk Dance Tutorial | Dari"),
 ("Shuffle Off to Buffalo", 19, 4, 2, "pmUJD1bHyzI", "How To Do Shuffle Off To Buffalo Tap Step | 92Y How To"),
 ("Tap Wings", 19, 4, 3, "0BkFwdca9vU", "Tap Dance TAP-torial: Learn WINGS"),
 ("Belly Dance Hip Drop", 5, 2, 1, "5vaRt2KQHCU", "Belly dance Fundamentals - Hip drop Variations - Beginners"),
 ("Belly Dance Shimmy", 5, 2, 1, "Q4XoBzePoE8", "Best BEGINNER SHIMMY - How to Belly Dance 15 Minute Class"),
 ("Bollywood Basics", 17, 13, 1, "SsGtNa3Oo3Y", "12 Basic Bollywood Dance Moves | Beginner Level | ABDC"),
 ("Irish Jig", 5, 2, 2, "3N2RsCuzFPg", "Learn Your First Irish Dance Jig: START HERE!"),
 ("Hula Basics", 5, 2, 1, "rb1hNeyU60w", "Basic Hula: Hip Movements & Basic Foot Steps"),
 ("Reggaeton Perreo", 33, 8, 2, "-qEONlQBBl0", "10 PERREO STEPS | Kaphar"),
 ("Dancehall Gallis", 14, 12, 2, "Xv9U-xS7F6U", "Gallis Sassa Step - Mr. Vegas | Choreography by Mikel Carpio"),
 ("Bachata Sensual", 36, 17, 2, "QQ2UQMKBZkI", "StepFlix Bachata Sensual Fundamentals - Sensual basic"),
 ("Bachata Footwork", 36, 17, 2, "8SGd3za49B8", "Bachata Footwork Tutorial - Tap, Tap, Triple Step"),
 ("Heels Choreography", 32, 3, 2, "3gBbvQ_mgjw", "Learn How to Dance High Heels in 15 min | Tutorial for Beginners"),
 ("Belly Dance Figure 8", 5, 2, 1, "Rgj1936jtV0", "Learn to do FIGURE 8 HIPS [Easy Dance Moves]"),
 ("Belly Dance Snake Arms", 5, 2, 1, "jISak5LL8Bk", "How to do SNAKE ARMS | All you need to know"),
 ("Dabke Basics", 5, 2, 1, "gC5jdLOscyI", "Dabke Tutorial - Basic Steps"),
 ("Tahitian Otea", 5, 2, 2, "3tMkYnbEV3w", "How to Tahitian Dance With Leolani - Ori Tahiti 1 - The Tamau"),
 ("Capoeira Ginga", 5, 2, 1, "2dNkRNXTuH4", "Ginga Capoeira Tutorial - Capoeira Moves Beginner"),
 ("Tinikling", 5, 2, 1, "1u-DJRCYwnI", "Tinikling - Basic Steps Tutorial"),
 ("Kathak Spins", 5, 2, 2, "Qk22EcoYsIk", "Learn the Techniques of Chakkars (Kathak Spins)"),
 ("Garba", 17, 13, 1, "6MB2L5uUV_U", "Garba Dance Course | Beginners | Level 1 | DAY 1"),
 ("Sevillanas", 18, 10, 2, "NkA5hQUpSkw", "How to Dance the First Sevillana (Sevillanas Flamencas)"),
 ("Tilt Jump", 7, 2, 2, "FmIhZmN1PGU", "HOW TO DO A TILT JUMP"),
 ("Floor Rolls", 7, 2, 1, "Kh8FMlMs1sI", "Different Dance Rolls - Demonstration and Tutorial"),
 ("Heels Hair Flip", 32, 3, 1, "OSaHk-m6ouk", "How to Hair Flip in Heels | 2 options"),
 ("West Coast Swing", 6, 4, 2, "zsle7AwtEYk", "Learn to Dance West Coast Swing in 5 Minutes!"),
 ("Hustle Basics", 6, 6, 1, "JsqmmlhZpj8", "LEARN TO DANCE THE HUSTLE - Basic Hustle Steps for Beginners"),
 ("Country Two-Step", 5, 2, 1, "YORegW3-hOc", "Texas Two Step for Beginners - A Complete Tutorial"),
 ("Salsa Shines", 1, 1, 2, "IuLLOgjT2Is", "Salsa: Heel Step, Cross Step, Suzy Q & New York"),
 ("Bachata Dip", 36, 17, 2, "3ftJELfXvGs", "10 EASY Falls & Dips In Bachata Sensual You Must Know!"),
 ("Kizomba Virgula", 39, 19, 2, "t4do_ZAHVbY", "Kizomba Tutorial 07: Virgula 90 - Armand & Lavinia"),
 ("Ndombolo", 13, 11, 2, "blF4Uv5Enco", "LEARN THESE MUST KNOW NDOMBOLO MOVES"),
 ("Coupe-Decale", 13, 11, 2, "HIs57-VNDko", "How to dance Coupe Decale & Congolese Dance Moves TUTORIAL"),
 ("Dancehall Wine", 14, 12, 1, "eqIBxrKPbZY", "How To DANCEHALL Wine | Club Dance Moves Tutorial 34"),
 ("Shim Sham", 19, 4, 2, "Fqfv4hvxFdA", "Learn the SHIM SHAM - TAP DANCE tutorial"),
 ("Maxie Ford", 19, 4, 3, "FnfHXAg0fgU", "Learn How to do a Maxi Ford for Beginner Tap Dancers"),
 ("Paddle and Roll", 19, 4, 2, "08Y7vgSTieQ", "LEARN TO TAP DANCE | Paddle & Roll | Easy Steps for Beginners"),
 ("Pas de Bourree", 20, 4, 1, "d5-TKHTOTdU", "Learn the Pas de Bourree (Jazz style) - Jazz Dance Basics"),
 ("Stag Leap", 20, 4, 3, "Rs5fpL8uI0w", "How to Stag Leap - Dance Muscle Training"),
 ("Waltz Natural Turn", 2, 2, 2, "AgqXSjVJ4bc", "Natural Turn - Waltz dance Lesson (International Style)"),
 ("Tango Promenade", 2, 5, 2, "1AwO5pq33Do", "Tango for Beginners | Walks, Progressive Link, Closed Promenade"),
 ("Samba Whisk", 1, 1, 2, "Ku2t4mtRl0M", "Samba Whisk - Basic step in 4 steps PLUS Arm Styling"),
 ("Bolero Basics", 1, 1, 1, "F8eMTP993-s", "7 Bolero Dance Steps for Beginners"),
]
out = open("_proto/picks_verified10.tsv", "w", encoding="utf-8")
good = bad = 0
for name, sid, mid, diff, vid, title in PICKS:
    try:
        r = subprocess.run(["yt-dlp","--no-warnings","--skip-download","-J",f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        d = json.loads(r.stdout); emb = d.get("playable_in_embed"); dur = d.get("duration") or 0
        print(f"  [{'OK' if emb else 'BAD-EMBED'}] {name:24} {vid}  emb={emb} dur={dur}s")
        if emb:
            good += 1; out.write(f"{name}\t{sid}\t{mid}\t{diff}\t{vid}\t{dur}\t{title}\n")
        else: bad += 1
    except Exception as e:
        bad += 1; print(f"  [ERR ] {name:24} {vid}  {e}")
out.close()
print(f"\nOK={good} BAD={bad} -> _proto/picks_verified10.tsv")
