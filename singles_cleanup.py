"""
singles_cleanup.py [apply]
For wrong-source + dead single-move videos:
  - if the dance has user data OR other videos -> DETACH (delete the bad Video row), keep dance
  - else -> DELETE the dance (orphan obscure entry)
Dry-run unless 'apply'.
"""
import os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
PGPW="dancebabydance"; APPLY=len(sys.argv)>1 and sys.argv[1]=="apply"

def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing","-v","ON_ERROR_STOP=1","-At","-F","\t"],
                     input=sql,capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

WRONG={9,10,261,279,289,290,297,305,306,313,341,356,358,383,405,422,427,460,486,626,
 715,717,718,719,721,724,729,734,736,740,742,746,748,751,753,758,762,764,773,845,849,
 944,946,960,972,981,994,1000,1016,1043,1048,1138,1593}
# map did->vid and gather dead/fail
did2vid={}; dead=set()
for l in open("_proto/singles_triage.tsv",encoding="utf-8"):
    p=l.rstrip("\n").split("\t")
    if len(p)<4: continue
    vid,did,verd=p[0],int(p[1]),p[2]
    did2vid[did]=vid
    if verd in ("DEAD","FETCH_FAIL"): dead.add(did)
targets=WRONG|dead

detach=[]; delete=[]
for did in sorted(targets):
    vid=did2vid.get(did)
    rows=psql(f'''SELECT
      (SELECT count(*) FROM "UserFavoriteDances" x WHERE x."DanceId"={did})
     +(SELECT count(*) FROM "UserLearnedDances" x WHERE x."DanceId"={did})
     +(SELECT count(*) FROM "UserInProgressDances" x WHERE x."DanceId"={did})
     +(SELECT count(*) FROM "DanceRatings" x WHERE x."DanceId"={did})
     +(SELECT count(*) FROM "PracticeSessions" x WHERE x."DanceId"={did}),
      (SELECT count(*) FROM "Videos" v WHERE v."DanceId"={did}),
      (SELECT "Name" FROM "Dances" WHERE "Id"={did});''')
    if not rows or not rows[0][2]: continue  # already gone
    ud=int(rows[0][0]); nv=int(rows[0][1]); name=rows[0][2]
    if ud>0 or nv>1:
        detach.append((did,vid,name,ud,nv))
    else:
        delete.append((did,vid,name))

T=["BEGIN;"]
for did,vid,name,ud,nv in detach:
    T.append(f'DELETE FROM "Videos" WHERE "DanceId"={did} AND "VideoId"=\'{vid}\';')
if delete:
    T.append(f'DELETE FROM "Dances" WHERE "Id" IN ({",".join(str(d[0]) for d in delete)});')
T.append("COMMIT;" if APPLY else "ROLLBACK;")

print(f"DETACH bad video (keep dance): {len(detach)}")
for did,vid,name,ud,nv in detach: print(f"   keep #{did} {name} (ud={ud}, vids={nv}) — drop its {vid} row")
print(f"\nHARD-DELETE orphan dance: {len(delete)}")
for did,vid,name in delete: print(f"   del #{did} {name}")
print(f"\nMode: {'APPLY' if APPLY else 'DRY RUN'}")
psql("\n".join(T))
print("done")
