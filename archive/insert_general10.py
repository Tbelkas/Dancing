"""insert_general10.py [apply] — round 10 GENERAL dances, picks INLINED (dodges sync-stale file race).
WITH music tag + per-dance difficulty. Writes _proto/inserted10.tsv (ytid,videoDbId,danceId,dur,name)."""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

# name, styleId, musicId, difficulty, ytid, dur, title
ROWS = [
 ("Viennese Waltz", 2, 2, 2, "QwBHYOgs3q0", 514, "Learn Viennese Waltz Basic Steps - Super Easy Beginner Tutorial"),
 ("Argentine Tango Gancho", 1, 5, 3, "zB_3pDRI-FU", 210, "How to Do the Hook aka the Gancho | Argentine Tango"),
 ("Lindy Hop Swingout", 6, 4, 2, "LEmIgdYzy1o", 618, "Lindy Hop Swingout with Swivels Lesson with Frankie Manning"),
 ("Balboa Basic", 6, 4, 2, "9TyBUAcc5P0", 227, "Balboa Basics Summary - Peter and Lorraine"),
 ("Contemporary Floor Work", 7, 2, 2, "ifQ1RrSZNYM", 950, "Contemporary Dance Floor Work Tutorial (Intermediate/Advanced)"),
 ("Lyrical Dance Basics", 7, 2, 1, "QmA4DZC_qwY", 681, "Beginner Lyrical Dance with trainwithkendall"),
 ("Jazz Funk Basics", 20, 3, 1, "zkVDBGQnbms", 642, "Jazz Funk Dance Tutorial | Dari"),
 ("Shuffle Off to Buffalo", 19, 4, 2, "pmUJD1bHyzI", 100, "How To Do Shuffle Off To Buffalo Tap Step | 92Y How To"),
 ("Tap Wings", 19, 4, 3, "0BkFwdca9vU", 314, "Tap Dance TAP-torial: Learn WINGS"),
 ("Belly Dance Hip Drop", 5, 2, 1, "5vaRt2KQHCU", 919, "Belly dance Fundamentals - Hip drop Variations - Beginners"),
 ("Belly Dance Shimmy", 5, 2, 1, "Q4XoBzePoE8", 898, "Best BEGINNER SHIMMY - How to Belly Dance 15 Minute Class"),
 ("Bollywood Basics", 17, 13, 1, "SsGtNa3Oo3Y", 1219, "12 Basic Bollywood Dance Moves | Beginner Level | ABDC"),
 ("Irish Jig", 5, 2, 2, "3N2RsCuzFPg", 313, "Learn Your First Irish Dance Jig: START HERE!"),
 ("Hula Basics", 5, 2, 1, "rb1hNeyU60w", 292, "Basic Hula: Hip Movements & Basic Foot Steps"),
 ("Reggaeton Perreo", 33, 8, 2, "-qEONlQBBl0", 1483, "10 PERREO STEPS | Kaphar"),
 ("Dancehall Gallis", 14, 12, 2, "Xv9U-xS7F6U", 180, "Gallis Sassa Step - Mr. Vegas | Choreography by Mikel Carpio"),
 ("Bachata Sensual", 36, 17, 2, "QQ2UQMKBZkI", 442, "StepFlix Bachata Sensual Fundamentals - Sensual basic"),
 ("Bachata Footwork", 36, 17, 2, "8SGd3za49B8", 699, "Bachata Footwork Tutorial - Tap, Tap, Triple Step"),
 ("Heels Choreography", 32, 3, 2, "3gBbvQ_mgjw", 856, "Learn How to Dance High Heels in 15 min | Tutorial for Beginners"),
 ("Belly Dance Figure 8", 5, 2, 1, "Rgj1936jtV0", 488, "Learn to do FIGURE 8 HIPS [Easy Dance Moves]"),
 ("Belly Dance Snake Arms", 5, 2, 1, "jISak5LL8Bk", 550, "How to do SNAKE ARMS | All you need to know"),
 ("Dabke Basics", 5, 2, 1, "gC5jdLOscyI", 408, "Dabke Tutorial - Basic Steps"),
 ("Tahitian Otea", 5, 2, 2, "3tMkYnbEV3w", 354, "How to Tahitian Dance With Leolani - Ori Tahiti 1 - The Tamau"),
 ("Capoeira Ginga", 5, 2, 1, "2dNkRNXTuH4", 342, "Ginga Capoeira Tutorial - Capoeira Moves Beginner"),
 ("Tinikling", 5, 2, 1, "1u-DJRCYwnI", 115, "Tinikling - Basic Steps Tutorial"),
 ("Kathak Spins", 5, 2, 2, "Qk22EcoYsIk", 468, "Learn the Techniques of Chakkars (Kathak Spins)"),
 ("Garba", 17, 13, 1, "M2GO52YmBek", 1529, "Garba Tutorial Video | 10 Basic Steps | LiveToDance with Sonali"),
 ("Sevillanas", 18, 10, 2, "NkA5hQUpSkw", 815, "How to Dance the First Sevillana (Sevillanas Flamencas)"),
 ("Tilt Jump", 7, 2, 2, "FmIhZmN1PGU", 283, "HOW TO DO A TILT JUMP"),
 ("Floor Rolls", 7, 2, 1, "Kh8FMlMs1sI", 559, "Different Dance Rolls - Demonstration and Tutorial"),
 ("Heels Hair Flip", 32, 3, 1, "OSaHk-m6ouk", 146, "How to Hair Flip in Heels | 2 options"),
 ("West Coast Swing", 6, 4, 2, "zsle7AwtEYk", 394, "Learn to Dance West Coast Swing in 5 Minutes!"),
 ("Hustle Basics", 6, 6, 1, "JsqmmlhZpj8", 691, "LEARN TO DANCE THE HUSTLE - Basic Hustle Steps for Beginners"),
 ("Country Two-Step", 5, 2, 1, "YORegW3-hOc", 679, "Texas Two Step for Beginners - A Complete Tutorial"),
 ("Salsa Shines", 1, 1, 2, "IuLLOgjT2Is", 639, "Salsa: Heel Step, Cross Step, Suzy Q & New York"),
 ("Bachata Dip", 36, 17, 2, "3ftJELfXvGs", 381, "10 EASY Falls & Dips In Bachata Sensual You Must Know!"),
 ("Kizomba Virgula", 39, 19, 2, "t4do_ZAHVbY", 394, "Kizomba Tutorial 07: Virgula 90 - Armand & Lavinia"),
 ("Ndombolo", 13, 11, 2, "blF4Uv5Enco", 491, "LEARN THESE MUST KNOW NDOMBOLO MOVES"),
 ("Coupe-Decale", 13, 11, 2, "HIs57-VNDko", 817, "How to dance Coupe Decale & Congolese Dance Moves TUTORIAL"),
 ("Dancehall Wine", 14, 12, 1, "eqIBxrKPbZY", 419, "How To DANCEHALL Wine | Club Dance Moves Tutorial 34"),
 ("Shim Sham", 19, 4, 2, "Fqfv4hvxFdA", 533, "Learn the SHIM SHAM - TAP DANCE tutorial"),
 ("Maxie Ford", 19, 4, 3, "FnfHXAg0fgU", 631, "Learn How to do a Maxi Ford for Beginner Tap Dancers"),
 ("Paddle and Roll", 19, 4, 2, "08Y7vgSTieQ", 633, "LEARN TO TAP DANCE | Paddle & Roll | Easy Steps for Beginners"),
 ("Pas de Bourree", 20, 4, 1, "d5-TKHTOTdU", 441, "Learn the Pas de Bourree (Jazz style) - Jazz Dance Basics"),
 ("Stag Leap", 20, 4, 3, "Rs5fpL8uI0w", 462, "How to Stag Leap - Dance Muscle Training"),
 ("Waltz Natural Turn", 2, 2, 2, "AgqXSjVJ4bc", 382, "Natural Turn - Waltz dance Lesson (International Style)"),
 ("Tango Promenade", 2, 5, 2, "1AwO5pq33Do", 431, "Tango for Beginners | Walks, Progressive Link, Closed Promenade"),
 ("Samba Whisk", 1, 1, 2, "Ku2t4mtRl0M", 529, "Samba Whisk - Basic step in 4 steps PLUS Arm Styling"),
 ("Bolero Basics", 1, 1, 1, "F8eMTP993-s", 590, "7 Bolero Dance Steps for Beginners"),
]

def psql(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PGPW; env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", "192.168.0.197", "-U", "dance_user", "-d", "dancing",
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(1)
    return p.stdout

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "dance"

out = open("_proto/inserted10.tsv", "w", encoding="utf-8")
for name, sid, mid, diff, vid, dur, title in ROWS:
    existing = psql(f'''SELECT d."Slug" FROM "Dances" d JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
                        WHERE ds."StyleId"={sid};''').split()
    base = slug(name); sl = base; i = 2
    while sl in existing:
        sl = f"{base}-{i}"; i += 1
    if not APPLY:
        print(f"  DRY + {name:24} style {sid} music {mid} diff {diff} slug {sl} <- {vid} ({dur}s)")
        continue
    sql = f"""BEGIN;
WITH d AS (INSERT INTO "Dances"("Name","Slug","Description","DateAdded","Difficulty")
   VALUES ($${name}$$,'{sl}',$$Trending tutorial: {title.replace('$','')}$$, now(), {diff}) RETURNING "Id"),
 s AS (INSERT INTO "DanceStyles"("DanceId","StyleId") SELECT "Id",{sid} FROM d RETURNING 1),
 m AS (INSERT INTO "DanceMusicalStyles"("DanceId","MusicalStyleId") SELECT "Id",{mid} FROM d RETURNING 1),
 v AS (INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
   SELECT $${title}$$,'{vid}','youtube','tutorial', now(), 0, "Id" FROM d RETURNING "Id","DanceId")
SELECT "Id","DanceId" FROM v;
COMMIT;"""
    res = psql(sql).strip().splitlines()
    row = next(l for l in res if "\t" in l)
    vid_db, dance_id = row.split("\t")
    print(f"  + {name:24} dance {dance_id} video {vid_db} slug {sl} <- {vid} ({dur}s)")
    out.write(f"{vid}\t{vid_db}\t{dance_id}\t{dur}\t{name}\n")
out.close()
print(f"\nMode: {'APPLY' if APPLY else 'DRY RUN'}  rows={len(ROWS)}")
