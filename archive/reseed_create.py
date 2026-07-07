"""reseed_create.py [apply] — create the 8 verified re-seed dances (dance+style+music+video)."""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
APPLY=len(sys.argv)>1 and sys.argv[1]=="apply"
# (vid, name, styleId, musicId, title)
E=[("YV5_GjfSr2k","Lazo",1,1,"Salsa Dancing Tutorial - The Lasso Move"),
   ("1ihB6N2Jsdk","Forward Lock",2,4,"Quickstep Lesson 3, Forward Lock Step"),
   ("vVLu5CfPs8c","En Dedans",4,2,"Pirouette En Dedans Tutorial"),
   ("apA78gskWBk","Inside Swivels",6,4,"Lindy Hop: Follower's Swivels"),
   ("EoGTN1YzjBo","The Swim",10,4,"How to do the Swim dance (60's)"),
   ("aFYqDe10XVo","The Ska",5,4,"How to Dance Traditional Ska - Basic"),
   ("yvYg26-yKo4","Guapo",1,1,"Saludo del Guapo - Rueda"),
   ("MVWO9Y-u1Ow","Meneo",1,1,"Meneo - Salsa Estilo Femenino")]
def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]="dancebabydance"
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing","-v","ON_ERROR_STOP=1","-At","-F","\t"],
                     input=sql,capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return p.stdout
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
T=["BEGIN;"]
for vid,name,sid,mid,title in E:
    ex=psql(f'''SELECT "Slug" FROM "Dances" WHERE "Slug" LIKE '{slug(name)}%';''').split()
    sl=slug(name); i=2
    while sl in ex: sl=f"{slug(name)}-{i}"; i+=1
    T.append(f"""WITH d AS (INSERT INTO "Dances"("Name","Slug","Description","DateAdded","Difficulty")
 VALUES ($${name}$$,'{sl}',$$Re-sourced tutorial: {title}$$,now(),1) RETURNING "Id"),
 s AS (INSERT INTO "DanceStyles"("DanceId","StyleId") SELECT "Id",{sid} FROM d RETURNING 1),
 m AS (INSERT INTO "DanceMusicalStyles"("DanceId","MusicalStyleId") SELECT "Id",{mid} FROM d RETURNING 1)
 INSERT INTO "Videos"("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DanceId")
 SELECT $${title}$$,'{vid}','youtube','tutorial',now(),0,"Id" FROM d;""")
    print(f"  + {name} (slug {sl}) style {sid} music {mid} <- {vid}")
T.append("COMMIT;" if APPLY else "ROLLBACK;")
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
psql("\n".join(T))
print("done")
