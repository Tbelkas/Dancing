"""audit_videos.py — pull every Video with dance/style, platform, VideoType, StartTime,
segment stats. Buckets:
  A) standalone (StartTime NULL) youtube videos with NO chips -> chip candidates
  B) shared ytid across >1 dance with NO StartTime -> misplacement (whole montage on each)
  C) bad segment timing
  D) all distinct ytids -> for embeddability scan
Read-only. Writes _proto/audit_videos.tsv, _proto/all_ytids.txt, _proto/nochip_standalone.tsv"""
import os, subprocess, sys
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")
PGPW = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"

def psql(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PGPW; env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", "192.168.0.197", "-U", "dance_user", "-d", "dancing",
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(1)
    return p.stdout

sql = """
SELECT v."Id", v."VideoId", v."Platform", v."VideoType", v."DanceId",
       d."Name", COALESCE(st.styles,''),
       COALESCE(seg.cnt,0),
       COALESCE(v."StartTime",-1), COALESCE(v."EndTime",-1),
       COALESCE(seg.bad,0), v."Title"
FROM "Videos" v
JOIN "Dances" d ON d."Id"=v."DanceId"
LEFT JOIN (SELECT ds."DanceId", string_agg(s."Name", ',' ORDER BY s."Name") styles
           FROM "DanceStyles" ds JOIN "Styles" s ON s."Id"=ds."StyleId" GROUP BY ds."DanceId") st
  ON st."DanceId"=v."DanceId"
LEFT JOIN (SELECT "VideoId", count(*) cnt,
                  count(*) FILTER (WHERE "EndTime" IS NOT NULL AND "EndTime"<="StartTime") bad
           FROM "VideoSegments" GROUP BY "VideoId") seg ON seg."VideoId"=v."Id"
ORDER BY v."Id";
"""
cols = "vid ytid platform vtype danceid dance styles segcnt start end bad title".split()
rows = [dict(zip(cols, l.split("\t"))) for l in psql(sql).splitlines() if l]
for r in rows:
    for k in ("segcnt", "start", "end", "bad"):
        r[k] = int(r[k])

with open("_proto/audit_videos.tsv", "w", encoding="utf-8") as f:
    f.write("\t".join(cols) + "\n")
    for r in rows:
        f.write("\t".join(str(r[c]) for c in cols) + "\n")

yt = [r for r in rows if r["platform"] == "youtube"]
# distinct ytids
ytids = sorted({r["ytid"] for r in rows})
with open("_proto/all_ytids.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(ytids))

# B) shared ytid, no StartTime on any -> whole video duplicated across dances
byid = defaultdict(list)
for r in yt:
    byid[r["ytid"]].append(r)
misplaced = []
for vid, rs in byid.items():
    if len(rs) > 1 and all(r["start"] < 0 for r in rs):
        misplaced.extend(rs)

# A) standalone no-chip youtube (StartTime null, not a montage slice)
nochip_standalone = [r for r in yt if r["start"] < 0 and r["segcnt"] == 0]
# montage slices with no chips (expected - they are sub-slices)
slice_nochip = [r for r in yt if r["start"] >= 0 and r["segcnt"] == 0]

badtiming = [r for r in rows if r["bad"] > 0]

print(f"Total videos {len(rows)} | youtube {len(yt)} | distinct ytids {len(ytids)}")
print(f"A) standalone youtube, NO chips: {len(nochip_standalone)}")
print(f"   montage-slice youtube, no chips (expected): {len(slice_nochip)}")
print(f"B) shared ytid w/ NO StartTime (whole video on >1 dance): {len(misplaced)} rows")
print(f"C) bad segment timing: {len(badtiming)}")
print()
print("=== B) misplacement: same whole video on multiple dances ===")
for vid, rs in sorted(byid.items(), key=lambda kv: -len(kv[1])):
    if len(rs) > 1 and all(r["start"] < 0 for r in rs):
        print(f"  {vid}: " + " | ".join(f"v{r['vid']}/d{r['danceid']} {r['dance']}" for r in rs))

with open("_proto/nochip_standalone.tsv", "w", encoding="utf-8") as f:
    for r in nochip_standalone:
        f.write(f"{r['vid']}\t{r['ytid']}\t{r['danceid']}\t{r['dance']}\t{r['styles']}\t{r['title']}\n")
