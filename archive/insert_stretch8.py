"""insert_stretch8.py [apply] — round 8 stretching dances, picks INLINED (no tsv read to dodge
sync-stale file races). NO music tag, per-dance difficulty. Writes _proto/inserted8.tsv."""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

# name, styleId, difficulty, ytid, dur, title
ROWS = [
 ("Deep Splits Stretch", 23, 2, "GFuhJQloXu8", 1306, "15 Minute Deep Stretch for Splits"),
 ("Full Body Mobility Flow", 23, 1, "F4oF_vXjIV8", 841, "15 Min Full Body Mobility Flow Routine (FOLLOW ALONG)"),
 ("Hip Flexor Stretch", 23, 1, "Z04ldN6WnRY", 1319, "20 Minute Hip Flexor Flexibility Routine (FOLLOW ALONG)"),
 ("Frog Stretch", 23, 2, "BVVCAZrIjXY", 376, "How To Do Frog Pose | Benefits, Breakdown, Mobility Exercises"),
 ("Pigeon Pose", 23, 1, "46phRH_09yM", 320, "How to do PIGEON Pose for beginners (Hip External Rotation)"),
 ("Lizard Pose", 23, 1, "14rq7Gfm4aM", 418, "Lizard Pose: Achieve Optimal Hip Mobility"),
 ("Couch Stretch", 23, 1, "WKo4APrwfXQ", 354, "Couch Stretch Progressions: Beginner To Advanced (Hip Flexors & Quads)"),
 ("Calf Stretch", 23, 1, "uQohpNbzyUg", 626, "10 min CALF STRETCHES for Flexibility (Easy Follow Along)"),
 ("IT Band & Glute Stretch", 23, 1, "WbDS4XE5SKs", 631, "Yoga for IT Band - 10 min Stretches for Iliotibial Band"),
 ("Lower Back Relief", 23, 1, "7V-EbW-DmN0", 866, "12 Min Lower Back Pain Stretches - Exercises for Pain Relief"),
 ("Neck & Traps Release", 23, 1, "4bRmTmd9lmM", 886, "15 min Tight Neck, Traps & Shoulders Follow Along"),
 ("Wrist & Forearm Mobility", 23, 1, "7xY-JrvtnC0", 650, "Wrist Mobility Follow Along Routine: 6 Simple Wrist Exercises"),
 ("Thoracic Rotation", 23, 1, "w-6awp5LT6k", 769, "12 Minute T-Spine Mobility Workout (Follow Along)"),
 ("Morning Mobility", 23, 1, "t2jel6q1GRk", 551, "Quick Morning Stretching Routine For Flexibility & Mobility"),
 ("Flexibility for High Kicks", 23, 2, "EiRLRiqsQJk", 434, "Follow Along Kick Exercises for Dance [Improve in 5 Minutes]"),
 ("Jefferson Curl", 23, 2, "y_APeWo643w", 379, "Jefferson Curl | Do It Right!"),
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

out = open("_proto/inserted8.tsv", "w", encoding="utf-8")
for name, sid, diff, vid, dur, title in ROWS:
    existing = psql(f'''SELECT d."Slug" FROM "Dances" d JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
                        WHERE ds."StyleId"={sid};''').split()
    base = slug(name); sl = base; i = 2
    while sl in existing:
        sl = f"{base}-{i}"; i += 1
    if not APPLY:
        print(f"  DRY + {name:28} style {sid} diff {diff} slug {sl} <- {vid} ({dur}s)")
        continue
    sql = f"""BEGIN;
WITH d AS (INSERT INTO "Dances"("Name","Slug","Description","DateAdded","Difficulty")
   VALUES ($${name}$$,'{sl}',$$Flexibility & mobility for dancers: {title.replace('$','')}$$, now(), {diff}) RETURNING "Id"),
 s AS (INSERT INTO "DanceStyles"("DanceId","StyleId") SELECT "Id",{sid} FROM d RETURNING 1),
 v AS (INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
   SELECT $${title}$$,'{vid}','youtube','tutorial', now(), 0, "Id" FROM d RETURNING "Id","DanceId")
SELECT "Id","DanceId" FROM v;
COMMIT;"""
    res = psql(sql).strip().splitlines()
    row = next(l for l in res if "\t" in l)
    vid_db, dance_id = row.split("\t")
    print(f"  + {name:28} dance {dance_id} video {vid_db} slug {sl} diff {diff} <- {vid} ({dur}s)")
    out.write(f"{vid}\t{vid_db}\t{dance_id}\t{dur}\t{name}\n")
out.close()
print(f"\nMode: {'APPLY' if APPLY else 'DRY RUN'}  rows={len(ROWS)}")
