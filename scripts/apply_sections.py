"""
apply_sections.py <videoDbId> "Label@start-end;Label@start-end;..." [apply]
Inserts VideoSegments for one Videos row and sets its VideoType='tutorial'.
Times accept seconds (int) or m:ss. End optional ("Label@start"). Dry-run unless 'apply'.
Replaces any existing segments on that video.
"""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

PGHOST = "192.168.0.197"; PGUSER = "dance_user"; PGDB = "dancing"
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

vid_db = int(sys.argv[1])
spec = sys.argv[2]
apply = len(sys.argv) > 3 and sys.argv[3] == "apply"

def to_sec(s):
    s = s.strip()
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + int(sec)
    return int(s)

segs = []
for part in spec.split(";"):
    part = part.strip()
    if not part:
        continue
    label, times = part.rsplit("@", 1)
    if "-" in times:
        st, et = times.split("-", 1)
        segs.append((label.strip(), to_sec(st), to_sec(et)))
    else:
        segs.append((label.strip(), to_sec(times), None))

print(f"video {vid_db}: {len(segs)} segments")
for lbl, st, et in segs:
    print(f"  {st:>4}-{'' if et is None else et:>4}  {lbl}")

if not apply:
    print("(dry-run; pass 'apply' to write)")
    raise SystemExit(0)

def sql_lit(s):
    return s.replace("'", "''")

values = ",".join(
    f"('{sql_lit(lbl)}',{st},{'NULL' if et is None else et},{vid_db})"
    for lbl, st, et in segs
)
sql = f"""BEGIN;
UPDATE "Videos" SET "VideoType"='tutorial' WHERE "Id"={vid_db};
DELETE FROM "VideoSegments" WHERE "VideoId"={vid_db};
INSERT INTO "VideoSegments"("Label","StartTime","EndTime","VideoId") VALUES {values};
COMMIT;"""

env = dict(os.environ); env["PGPASSWORD"] = PGPW; env["PGCLIENTENCODING"] = "UTF8"
p = subprocess.run(["psql", "-h", PGHOST, "-U", PGUSER, "-d", PGDB, "-v", "ON_ERROR_STOP=1"],
                   input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
sys.stdout.write(p.stdout)
if p.returncode:
    sys.stderr.write(p.stderr)
    raise SystemExit(1)
print("APPLIED")
