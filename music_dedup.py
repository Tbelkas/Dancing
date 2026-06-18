"""
music_dedup.py [apply]
Reduce each dance with 2+ musical styles to ONE, chosen by the dance's (single) style.
Keeps the first music in that style's preference list that the dance has; drops the rest.
Dry-run unless 'apply'.
"""
import os, subprocess, sys
from collections import Counter
PGPW="dancebabydance"; APPLY=len(sys.argv)>1 and sys.argv[1]=="apply"
def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing","-v","ON_ERROR_STOP=1","-At","-F","\t"],
                     input=sql,capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

# music ids: 1 Salsa 2 Classical 3 HipHop 4 Jazz 5 Tango 6 EDM 7 Blues 8 Reggaeton
#            9 Cumbia 10 Flamenco 11 Afrobeats 12 Dancehall 13 Bhangra 14 JKpop
# style id -> ordered preferred music ids
PREF={1:[1,8,9,5],2:[5,2,4,1],3:[3],4:[2],5:[4,3],6:[4,7],7:[2,6,4],8:[6,3],9:[6],
 10:[3],11:[6],12:[3],13:[11],14:[12,8],15:[3],16:[6,3],17:[13],18:[10],19:[4,7],20:[4,7],21:[14]}
MNAME={1:"Salsa",2:"Classical",3:"Hip-Hop",4:"Jazz",5:"Tango",6:"EDM",7:"Blues",8:"Reggaeton",
 9:"Cumbia",10:"Flamenco",11:"Afrobeats",12:"Dancehall",13:"Bhangra",14:"J/K-Pop"}

rows=psql('''SELECT d."Id",
  (SELECT min("StyleId") FROM "DanceStyles" ds WHERE ds."DanceId"=d."Id"),
  string_agg(dms."MusicalStyleId"::text, ',' ORDER BY dms."MusicalStyleId")
FROM "Dances" d JOIN "DanceMusicalStyles" dms ON dms."DanceId"=d."Id"
GROUP BY d."Id" HAVING count(*)>=2;''')

drops=[]; kept_counter=Counter()
for did,sid,musics in rows:
    did=int(did); sid=int(sid) if sid else 0
    mids=[int(x) for x in musics.split(",")]
    pref=PREF.get(sid,[])
    keep=next((m for m in pref if m in mids), min(mids))  # fallback: lowest id
    kept_counter[MNAME.get(keep,keep)]+=1
    for m in mids:
        if m!=keep: drops.append((did,m))

T=["BEGIN;"]+[f'DELETE FROM "DanceMusicalStyles" WHERE "DanceId"={d} AND "MusicalStyleId"={m};' for d,m in drops]+["COMMIT;" if APPLY else "ROLLBACK;"]
print(f"multi-music dances: {len(rows)}  links to drop: {len(drops)}")
print("kept-music tally:", dict(kept_counter.most_common()))
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
psql("\n".join(T))
# verify
after=psql('SELECT count(*) FROM (SELECT "DanceId" FROM "DanceMusicalStyles" GROUP BY "DanceId" HAVING count(*)>1) t;')
print("multi-music dances after:", after[0][0])
