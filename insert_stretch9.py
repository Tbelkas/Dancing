"""insert_stretch9.py [apply] — round 9 stretching dances, picks INLINED (dodges sync-stale file race).
NO music tag, per-dance difficulty. Writes _proto/inserted9.tsv."""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

# name, styleId, difficulty, ytid, dur, title
ROWS = [
 ("Ballet Flexibility Workout", 23, 1, "qsrBmwqNmnk", 1632, "Full Body Strength and Flexibility Ballet Workout - Follow-Along"),
 ("Bedtime Stretch", 23, 1, "_9JZuOO9E_w", 618, "10 Minute Evening Stretch for Beginners | Better Sleep & Relaxation"),
 ("Cobra Stretch", 23, 1, "jwoTJNgh8BY", 338, "Cobra Pose For Beginners - Effective stretch for low back pain"),
 ("Camel Pose", 23, 2, "lVmESFGCdYo", 469, "Camel Pose Yoga Tutorial - Yoga Backbends For Beginners!"),
 ("Wheel Pose", 23, 3, "aXpRAJC8ylM", 397, "How To: Wheel Pose for Beginners - Improve Your Backbend"),
 ("Inner Thigh Stretch", 23, 1, "nsHxDciEuOk", 660, "10 Minute Adductor Mobility Routine | Follow Along, With Coaching"),
 ("Deep Squat Mobility", 23, 1, "BTfEFDXp-cw", 546, "Improve Your Squat Mobility Forever (FULL WORKOUT)"),
 ("Chest Opener", 23, 1, "ufrzM7apn1o", 911, "15 Minute Chest and Shoulder Mobility Workout | Follow Along"),
 ("Leg Extension Hold", 23, 2, "JZ7QVHNmAG4", 758, "GET better extensions for ballet and dance"),
 ("Hip CARs", 23, 1, "MO1BPuabR44", 703, "Tabletop Hip CARs - Controlled Articular Rotations Tutorial"),
 ("Daily Full Body Stretch", 23, 1, "COO2S7lPBzA", 648, "10 Minute Total Body Stretch! [Daily Flexibility Routine]"),
 ("PNF Stretching", 23, 2, "ISD7xLUrNJ4", 1509, "PNF Stretching Routine & Techniques - How To Contract Hold Relax"),
 ("Cossack Squat", 23, 1, "CXiLxTpF_nA", 645, "Improve Your Cossack Squats for Flexibility & Strength in Hips and Legs"),
 ("Resistance Band Stretch", 23, 1, "JR3Dtyj4Ik4", 735, "12 Min. Resistance Band Mobility Routine | Full Body Flow"),
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

out = open("_proto/inserted9.tsv", "w", encoding="utf-8")
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
