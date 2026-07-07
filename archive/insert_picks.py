"""insert_picks.py [apply] — insert verified trending dances (dance+style+music+video) from
_proto/picks_verified.tsv. Per-style-unique slug. Writes _proto/inserted.tsv (ytid,videoDbId,danceId,dur,name)."""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

def psql(sql, capture=True):
    env = dict(os.environ); env["PGPASSWORD"] = PGPW; env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", "192.168.0.197", "-U", "dance_user", "-d", "dancing",
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(1)
    return p.stdout

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "dance"

rows = []
for line in open("_proto/picks_verified.tsv", encoding="utf-8"):
    line = line.rstrip("\n")
    if not line: continue
    name, sid, mid, vid, dur, title = line.split("\t")
    rows.append((name, int(sid), int(mid), vid, int(float(dur)), title))

out = open("_proto/inserted.tsv", "w", encoding="utf-8")
for name, sid, mid, vid, dur, title in rows:
    # per-style unique slug: existing slugs among dances that share this style
    existing = psql(f'''SELECT d."Slug" FROM "Dances" d JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
                        WHERE ds."StyleId"={sid};''').split()
    base = slug(name); sl = base; i = 2
    while sl in existing:
        sl = f"{base}-{i}"; i += 1
    if not APPLY:
        print(f"  DRY + {name:22} style {sid} music {mid} slug {sl} <- {vid} ({dur}s)")
        continue
    sql = f"""BEGIN;
WITH d AS (INSERT INTO "Dances"("Name","Slug","Description","DateAdded","Difficulty")
   VALUES ($${name}$$,'{sl}',$$Trending tutorial: {title.replace('$','')}$$, now(), 1) RETURNING "Id"),
 s AS (INSERT INTO "DanceStyles"("DanceId","StyleId") SELECT "Id",{sid} FROM d RETURNING 1),
 m AS (INSERT INTO "DanceMusicalStyles"("DanceId","MusicalStyleId") SELECT "Id",{mid} FROM d RETURNING 1),
 v AS (INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
   SELECT $${title}$$,'{vid}','youtube','tutorial', now(), 0, "Id" FROM d RETURNING "Id","DanceId")
SELECT "Id","DanceId" FROM v;
COMMIT;"""
    res = psql(sql).strip().splitlines()
    row = next(l for l in res if "\t" in l)
    vid_db, dance_id = row.split("\t")
    print(f"  + {name:22} dance {dance_id} video {vid_db} slug {sl} <- {vid} ({dur}s)")
    out.write(f"{vid}\t{vid_db}\t{dance_id}\t{dur}\t{name}\n")
out.close()
print(f"\nMode: {'APPLY' if APPLY else 'DRY RUN'}  rows={len(rows)}")
