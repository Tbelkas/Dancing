"""
rebuild_video.py <vid> <mode> ... [apply]
Replaces the wrong dances attached to a multi-dance video. Dry-run unless last arg 'apply'.

Modes:
  single  <vid> single  "<Move Name>" <styleId>                      -> 1 dance, video full (no segments)
  tutorial <vid> tutorial "<Dance Name>" <styleId> "<lbl@st-et;...>" -> 1 tutorial dance + segments
  delete  <vid> delete                                               -> delete all its dances (not a moves video)

Always: delete existing dances sharing this VideoId (cascade clears their videos/links), then build anew.
"""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY = sys.argv[-1]=="apply"
args = sys.argv[1:-1] if APPLY else sys.argv[1:]
vid, mode = args[0], args[1]
PGPW="dancebabydance"

def slugify(s):
    s=re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-"); return s

def run(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing",
                      "-v","ON_ERROR_STOP=1","-At","-F","\t"],input=sql,
                     capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return p.stdout

# fetch yt title for naming + the old dance ids
import json
title=json.load(open(f"_proto/{vid}.json",encoding="utf-8")).get("title","")
old=run(f'''SELECT string_agg(DISTINCT d."Id"::text,',') FROM "Videos" v
JOIN "Dances" d ON d."Id"=v."DanceId" WHERE v."VideoId"='{vid}';''').strip()

old_ids=[x for x in old.split(",") if x]
keep_id = args[2] if mode=="keep" else None
del_ids=[i for i in old_ids if i!=keep_id]
T=["BEGIN;"]
if del_ids:
    T.append(f'DELETE FROM "Dances" WHERE "Id" IN ({",".join(del_ids)});')

def uniq_slug(base):
    base=slugify(base)
    ex=run(f'''SELECT "Slug" FROM "Dances" WHERE "Slug" LIKE '{base}%';''').split()
    if base not in ex: return base
    i=2
    while f"{base}-{i}" in ex: i+=1
    return f"{base}-{i}"

if mode=="delete":
    summary=f"DELETE {len(old_ids)} dances (not a moves video)"
elif mode=="keep":
    nm=run(f'SELECT "Name" FROM "Dances" WHERE "Id"={keep_id};').strip()
    summary=f"-> keep #{keep_id} ({nm}), delete {len(del_ids)} sibling(s)"
elif mode=="attach":
    did=int(args[2])
    T.append(f"""INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
 VALUES ($${title}$$,'{vid}','youtube','tutorial',now(),0,{did});""")
    nm=run(f'SELECT "Name",\'/\',"Slug" FROM "Dances" WHERE "Id"={did};').strip()
    summary=f"-> attach video to existing dance #{did} ({nm})"
elif mode=="single":
    name, sid = args[2], int(args[3]); slug=uniq_slug(name)
    T.append(f"""WITH d AS (INSERT INTO "Dances"("Name","Slug","Description","DateAdded","Difficulty")
 VALUES ($${name}$$,'{slug}',$$Tutorial: {title}$$,now(),1) RETURNING "Id"),
 ds AS (INSERT INTO "DanceStyles"("DanceId","StyleId") SELECT "Id",{sid} FROM d RETURNING 1)
 INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
 SELECT $${title}$$,'{vid}','youtube','tutorial',now(),0,"Id" FROM d;""")
    summary=f"-> 1 dance '{name}' (slug {slug}), style {sid}"
elif mode=="tutorial":
    name, sid, segspec = args[2], int(args[3]), args[4]; slug=uniq_slug(name)
    segs=[]
    for part in segspec.split(";"):
        part=part.strip()
        if not part: continue
        lbl,times=part.rsplit("@",1); st,et=times.split("-")
        segs.append((lbl.strip(), int(st), int(et)))
    vals=",".join(f"($${l}$$,{s},{e})" for l,s,e in segs)
    T.append(f"""WITH d AS (INSERT INTO "Dances"("Name","Slug","Description","DateAdded","Difficulty")
 VALUES ($${name}$$,'{slug}',$${title}$$,now(),1) RETURNING "Id"),
 ds AS (INSERT INTO "DanceStyles"("DanceId","StyleId") SELECT "Id",{sid} FROM d RETURNING 1),
 v AS (INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
   SELECT $${title}$$,'{vid}','youtube','tutorial',now(),0,"Id" FROM d RETURNING "Id")
 INSERT INTO "VideoSegments"("Label","StartTime","EndTime","VideoId")
 SELECT s.l,s.st,s.et,v."Id" FROM v,(VALUES {vals}) AS s(l,st,et);""")
    summary=f"-> tutorial '{name}' (slug {slug}), {len(segs)} segments, style {sid}"
else:
    raise SystemExit("unknown mode")

T.append("COMMIT;" if APPLY else "ROLLBACK;")
print(f"{vid} [{title[:50]}] : drop ids [{old}] {summary} | {'APPLY' if APPLY else 'DRY'}")
run("\n".join(T))
print("done")
