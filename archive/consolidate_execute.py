"""
EXECUTOR for DancePlatform prod cleanup. Two phases in transactions.
  python consolidate_execute.py          -> DRY RUN (rolls back, prints plan)
  python consolidate_execute.py apply     -> COMMITS

Phase 1: merge name-variant duplicate dances (delete losers; repoint any user data first).
Phase 2: strip redundant 2nd style from 2-style dances (keep more-specific; manual overrides).
"""
import json, os, subprocess, sys, unicodedata, re
from collections import Counter

PGHOST="192.168.0.197"; PGUSER="dance_user"; PGDB="dancing"; PGPW="dancebabydance"
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"

def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h",PGHOST,"-U",PGUSER,"-d",PGDB,"-v","ON_ERROR_STOP=1","-At","-F","\t","-c",sql],
                     capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode!=0: sys.stderr.write("SQL ERROR:\n"+p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

def norm(name):
    s=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().lower().strip()
    s=re.sub(r"^the\s+","",s); s=re.sub(r"[^a-z0-9]+","",s); return s

RANK={ "Street / Urban":0,"Hip-hop":1,"House":2,"Jazz":3,"Folk / Traditional":3,
 "Ballroom":3,"Swing":3,"Latin":4,"Contemporary":4,"Breakdance":6,"Krump":6,
 "Waacking":7,"Vogue":7,"Tap":7,"Tektonik":7,"Afrobeats":7,"Dancehall":7,
 "Flamenco":8,"Bhangra":8,"Classical / Ballet":8,"K-Pop":8 }
# dance_id -> style NAME to KEEP (override the rank). drops the other.
OVERRIDE_KEEP={272:"Ballroom",664:"Ballroom",722:"Latin",742:"Latin",
 844:"Breakdance",1284:"Breakdance",1016:"Latin"}

merge_plan=json.load(open("merge_plan.json"))
loser_ids=sorted(int(i) for g in merge_plan for i in g["losers"])

# ---------- build one big transactional script ----------
T=["BEGIN;"]
# Phase 1: defensive repoint of user data from loser -> survivor, then delete losers
for g in merge_plan:
    surv=g["survivor"]
    for lo in g["losers"]:
        for tbl in ("UserFavoriteDances","UserLearnedDances","UserInProgressDances"):
            T.append(f'UPDATE "{tbl}" SET "DanceId"={surv} WHERE "DanceId"={lo} '
                     f'AND "UserId" NOT IN (SELECT "UserId" FROM "{tbl}" WHERE "DanceId"={surv});')
        T.append(f'UPDATE "DanceRatings" SET "DanceId"={surv} WHERE "DanceId"={lo} '
                 f'AND "UserId" NOT IN (SELECT "UserId" FROM "DanceRatings" WHERE "DanceId"={surv});')
        T.append(f'UPDATE "PracticeSessions" SET "DanceId"={surv} WHERE "DanceId"={lo};')
if loser_ids:
    T.append(f'DELETE FROM "Dances" WHERE "Id" IN ({",".join(map(str,loser_ids))});')

# Phase 2: recompute 2-style dances AFTER deletions, pick style to drop
# (done inside same tx via a temp staging using DELETEs computed in python from a fresh read)
# We must read current 2-style dances; do it pre-tx (losers among them are gone post-delete, so skip deleted)
rows=psql('''SELECT d."Id", string_agg(s."Id"::text||':'||s."Name", '\t' ORDER BY s."Name")
FROM "Dances" d JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
JOIN "Styles" s ON s."Id"=ds."StyleId"
GROUP BY d."Id" HAVING count(*)=2;''')
loser_set=set(loser_ids)
style_drops=[]  # (dance_id, style_id_to_drop)
for r in rows:
    did=int(r[0])
    if did in loser_set: continue  # will be deleted in phase 1
    entries=[(int(c.split(":",1)[0]), c.split(":",1)[1]) for c in r[1:]]
    a,b=entries
    if did in OVERRIDE_KEEP:
        keepname=OVERRIDE_KEEP[did]
        keep,drop=(a,b) if a[1]==keepname else (b,a)
    else:
        ra,rb=RANK.get(a[1],5),RANK.get(b[1],5)
        if ra==rb: keep,drop=(a,b) if a[0]<b[0] else (b,a)
        else: keep,drop=(a,b) if ra>rb else (b,a)
    style_drops.append((did,drop[0]))
for did,sid in style_drops:
    T.append(f'DELETE FROM "DanceStyles" WHERE "DanceId"={did} AND "StyleId"={sid};')

T.append("COMMIT;" if APPLY else "ROLLBACK;")
script="\n".join(T)

print(f"Phase 1: merge away {len(loser_ids)} duplicate dances")
print(f"Phase 2: strip 2nd style from {len(style_drops)} dances")
print(f"Mode: {'APPLY (COMMIT)' if APPLY else 'DRY RUN (ROLLBACK)'}\n")

# run it (pipe via stdin; -c has a Windows cmdline length limit)
env=dict(os.environ); env["PGPASSWORD"]=PGPW
p=subprocess.run(["psql","-h",PGHOST,"-U",PGUSER,"-d",PGDB,"-v","ON_ERROR_STOP=1","-f","-"],
                 input=script,capture_output=True,text=True,encoding="utf-8",env=env)
sys.stdout.write(p.stdout); sys.stderr.write(p.stderr)
if p.returncode!=0: raise SystemExit("TRANSACTION FAILED - rolled back")

# verify counts
for label,sql in [("dances",'SELECT count(*) FROM "Dances"'),
                  ("two_style_dances",'SELECT count(*) FROM (SELECT "DanceId" FROM "DanceStyles" GROUP BY "DanceId" HAVING count(*)>1) t'),
                  ("untagged_dances",'SELECT count(*) FROM "Dances" d WHERE NOT EXISTS (SELECT 1 FROM "DanceStyles" ds WHERE ds."DanceId"=d."Id")')]:
    print(f"{label}: {psql(sql)[0][0]}")
