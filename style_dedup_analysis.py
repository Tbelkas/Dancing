"""
DRY-RUN: plan stripping the redundant 2nd style from 2-style dances.
Keep the MORE SPECIFIC style (higher rank). Flag ties / top-level-genre clashes.
Writes style_plan.json (dance_id -> style_id_to_remove). No writes to DB.
"""
import json, os, subprocess, sys

PGHOST="192.168.0.197"; PGUSER="dance_user"; PGDB="dancing"; PGPW="dancebabydance"

def q(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h",PGHOST,"-U",PGUSER,"-d",PGDB,"-At","-F","\t","-c",sql],
                     capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode!=0: sys.stderr.write(p.stderr); raise SystemExit("psql failed")
    return [l.split("\t") for l in p.stdout.splitlines() if l]

# specificity: higher = more specific = KEEP. lower = generic umbrella = strip.
RANK = {
 "Street / Urban":0, "Hip-hop":1, "House":2,
 "Jazz":3, "Folk / Traditional":3, "Ballroom":3, "Swing":3,
 "Latin":4, "Contemporary":4,
 "Breakdance":6, "Krump":6,
 "Waacking":7, "Vogue":7, "Tap":7, "Tektonik":7, "Afrobeats":7, "Dancehall":7,
 "Flamenco":8, "Bhangra":8, "Classical / Ballet":8, "K-Pop":8,
}

rows=q('''SELECT d."Id", d."Name",
  string_agg(s."Id"::text||':'||s."Name", '\t' ORDER BY s."Name")
FROM "Dances" d JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
JOIN "Styles" s ON s."Id"=ds."StyleId"
GROUP BY d."Id", d."Name" HAVING count(*)=2 ORDER BY d."Id";''')

plan=[]; ties=[]; toplevel=[]
for r in rows:
    did=int(r[0]); name=r[1]
    pairs=[p.split(":",1) for p in r[2:] ]
    # r[2] may contain the two tab-joined entries already split by outer split; rebuild:
    raw=r[2:]
    entries=[]
    for chunk in raw:
        sid,sname=chunk.split(":",1); entries.append((int(sid),sname))
    a,b=entries
    ra,rb=RANK.get(a[1],5),RANK.get(b[1],5)
    if ra==rb:
        # tie: keep lower style id deterministically, but flag
        keep,drop=(a,b) if a[0]<b[0] else (b,a)
        ties.append((did,name,a,b,keep,drop))
    else:
        keep,drop=(a,b) if ra>rb else (b,a)
        if min(ra,rb)>=3 and {a[1],b[1]} != {"Street / Urban","Hip-hop"}:
            toplevel.append((did,name,keep,drop))
    plan.append(dict(dance_id=did, remove_style_id=drop[0],
                     remove_style=drop[1], keep_style=keep[1], name=name))

from collections import Counter
c=Counter((p["keep_style"],p["remove_style"]) for p in plan)
print(f"=== STYLE DEDUP PLAN: {len(plan)} two-style dances -> 1 style each ===\n")
print("keep <- drop : count")
for (k,d),n in c.most_common():
    print(f"  {k:<20} <- {d:<20} : {n}")

print(f"\n=== TIES (same specificity, auto-kept lower id, REVIEW): {len(ties)} ===")
for did,name,a,b,keep,drop in ties:
    print(f"  #{did} {name:<26} {a[1]} / {b[1]}  -> keep {keep[1]}, drop {drop[1]}")

print(f"\n=== TOP-LEVEL GENRE CLASHES (auto by rank, REVIEW): {len(toplevel)} ===")
for did,name,keep,drop in toplevel:
    print(f"  #{did} {name:<26} -> keep {keep[1]}, drop {drop[1]}")

json.dump(plan, open("style_plan.json","w"), indent=2)
print(f"\nWrote style_plan.json ({len(plan)} removals)")
