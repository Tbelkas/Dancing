"""insert_general11.py [apply] — round 11 GENERAL dances, picks INLINED. WITH music + difficulty.
Writes _proto/inserted11.tsv (ytid,videoDbId,danceId,dur,name)."""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

# name, styleId, musicId, difficulty, ytid, dur, title
ROWS = [
 ("Haka", 5, 2, 2, "H2deYzImsT0", 411, "AIS | How to do the Haka"),
 ("Sirtaki", 5, 2, 1, "ZR8_A9i5gck", 223, "Learn how to perform Sirtaki (Greek Dance)"),
 ("Tarantella", 5, 2, 2, "9eef7ENpmO8", 203, "Tarantella - Italian Folk Dance"),
 ("Kalbeliya", 5, 2, 2, "SypNK7RtMg8", 281, "Kalbelia dance tutorial: 3 beginner hand movements"),
 ("Mexican Folklorico", 5, 2, 2, "0b8MX4atrRo", 269, "Folklorico Tutorial: Basic Steps Part 1"),
 ("Jarabe Tapatio", 5, 2, 2, "p31lF-hY9u0", 187, "Mexican Hat Dance (El Jarabe Tapatio)"),
 ("Dandiya Raas", 17, 13, 1, "l8btRbzpNu4", 524, "Learn 5 Basic Dandiya Steps For Beginners | MGS Dance Studio"),
 ("Bharatanatyam Adavu", 5, 2, 2, "vmwZ9R03bXs", 748, "Bharatanatyam Lesson 1 - Learn adavus - Thattadavu 1 to 8"),
 ("Adowa", 5, 2, 1, "0uWdm5mJmwM", 302, "Adowa Lesson 4"),
 ("Kpanlogo", 13, 11, 2, "41XK66HezWc", 345, "Kpanlogo!"),
 ("Soukous", 13, 11, 2, "RZLJxxdlkHA", 849, "How To Dance Ndombolo Part 2 (Congolese Soukous Tutorial)"),
 ("Kuduro", 13, 11, 2, "oun94VXBvUY", 238, "African dance tutorial from Angola | Manuel Kanza"),
 ("Salsa Enchufla", 1, 1, 2, "3tUcawE0Bhs", 165, "Learn Cuban Salsa: Enchufla"),
 ("Cuban Dile Que No", 1, 1, 1, "Jexcy9LGKjo", 288, "Learn Cuban Salsa: Dile Que No!"),
 ("Tango Boleo", 1, 5, 3, "tfTvgX_vVFA", 1032, "Argentine Tango Boleo: Learn How to Do a Boleo (Guide + Exercises)"),
 ("Tango Sacada", 1, 5, 3, "ONC06TWPmOQ", 507, "3 Simple Sacadas For Tango Dancing (Leaders & Followers)"),
 ("Milonga Basics", 1, 5, 2, "BqDj9Kp0nRg", 618, "The 5 Most Common Milonga Steps (Argentine Tango)"),
 ("Cha Cha New York", 1, 1, 2, "cHeTjxD6ddY", 657, "Cha Cha New Yorkers Lesson For Beginners"),
 ("Rumba Walks", 1, 1, 1, "_6As0zdyj0A", 643, "International Rumba Walks Technique with Amanda Besyedin"),
 ("Samba Voltas", 1, 1, 2, "S9Q1WWVVOxE", 555, "How to dance SAMBA VOLTAS | Latin Dance Tutorial"),
 ("Salsa Setenta", 1, 1, 2, "itL9fcP4Q6M", 607, "Salsa Cuban Setenta | Salsa Tutorial for Beginner"),
 ("Bachata Turn", 36, 17, 1, "fSvr8GThrnU", 514, "8 Bachata Turns For The Party! | Beginner Bachata Tutorial"),
 ("Foxtrot Feather Step", 2, 4, 2, "FlgobWrEoUE", 496, "Slow Foxtrot for Beginners Lesson 1 | Feather Step, Three Step"),
 ("Quickstep Lock Step", 2, 4, 2, "fnrvjdtS0rM", 586, "Quickstep Basic Figure - Lock Step | Ballroom Dance"),
 ("Tango Corte", 2, 5, 2, "IVC-ZqZZxuo", 722, "The Corte Check: Tips for Dancing a Back Corte (in Tango)"),
 ("Jive Kicks", 2, 4, 2, "0S-yMpfzurY", 564, "Jive Tutorial: Kicks and Flicks"),
 ("Jitterbug", 6, 4, 1, "0NTa1CXQS6w", 886, "Easy Swing Dance Steps for Beginners - The Jitterbug"),
 ("Collegiate Shag", 6, 4, 2, "dUarTZW1s9M", 774, "Collegiate Shag | Lesson 1 Basic Footwork"),
 ("Boogie Woogie", 6, 4, 2, "hCYSITp-qhg", 525, "SWING DANCE CLASS - Boogie Woogie 1"),
 ("Grand Jete", 4, 2, 3, "qkihwqYWKKE", 263, "How to Do & Improve a Split Leap / Grand Jete"),
 ("Tap Riff", 19, 4, 2, "G-MxzasXGcw", 404, "Beginning Tap Tutorial Series | Learn To Tap | RIFFS"),
 ("Tap Flaps", 19, 4, 2, "FtDDZD5GuL4", 581, "Beginner Tap Dance Steps - FLAPS"),
 ("Tap Scuff", 19, 4, 1, "yFBSMfmJkwU", 151, "How to Tap Dance: Brush vs. Scuff"),
 ("Vogue Spins and Dips", 16, 6, 3, "nCsIqNFfOZw", 344, "Learn to Vogue with NYC Parks: Spins and Dips"),
 ("Chipping", 37, 18, 1, "EUIPhTlOZ9Q", 273, "5 SOCA DANCE MOVES | Tutorial"),
 ("Belly Dance Undulation", 5, 2, 2, "3k2XqPxmJDU", 607, "10-Min Belly Dance TUTORIAL: Undulations"),
 ("Belly Dance Maya", 5, 2, 2, "f1cO5qBHYl4", 776, "Maya and Hip Drop Belly Dance Combinations for Beginners"),
 ("Highland Fling", 5, 2, 2, "GAJQ9jMkNHE", 307, "Learn the Highland Fling"),
 ("Clogging", 5, 2, 1, "eQFNvhxdPXo", 390, "Learn to clog in 5 minutes!!!"),
 ("Hopak", 5, 2, 2, "TwGMF58xriI", 485, "How to dance Hopak BUT EASIER"),
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

out = open("_proto/inserted11.tsv", "w", encoding="utf-8")
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
