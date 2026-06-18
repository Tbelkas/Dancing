"""
map_times.py <youtube_id> [apply]
For a multi-dance video whose dance NAMES are correct but timestamps are missing:
match each dance to a chapter (or desc-timestamp) by normalized name and set the
dance's Video row StartTime/EndTime. Keeps dances (no deletion). Dry-run unless 'apply'.
"""
import json, os, re, subprocess, sys, unicodedata
PGHOST="192.168.0.197"; PGUSER="dance_user"; PGDB="dancing"; PGPW="dancebabydance"
vid=sys.argv[1]; APPLY=len(sys.argv)>2 and sys.argv[2]=="apply"

def psql(sql,ret=True):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h",PGHOST,"-U",PGUSER,"-d",PGDB,"-v","ON_ERROR_STOP=1","-At","-F","\t","-c",sql],
                     capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower().strip()
    s=re.sub(r"^the\s+","",s); s=re.sub(r"^\d+[\.\):\-]?\s*","",s); s=re.sub(r"[^a-z0-9]+","",s)
    return s

d=json.load(open(f"_proto/{vid}.json",encoding="utf-8"))
dur=d.get("duration") or 0
src=[(int(c["start_time"]),c["title"]) for c in (d.get("chapters") or [])]
if not src:
    for l in (d.get("description") or "").splitlines():
        m=re.match(r'\s*(\d{1,2}):(\d{2})\s+(.+)',l)
        if m: src.append((int(m.group(1))*60+int(m.group(2)), m.group(3).strip()))
src.sort()
# build name->(start,end) using next-start as end
starts=[t for t,_ in src]
seg={}
for idx,(t,ti) in enumerate(src):
    end=src[idx+1][0] if idx+1<len(src) else (dur or t+10)
    seg[norm(ti)]=(t,end)

rows=psql(f'''SELECT d."Id", d."Name", v."Id" FROM "Videos" v JOIN "Dances" d ON d."Id"=v."DanceId"
WHERE v."VideoId"='{vid}';''')
upd=[]; miss=[]
for did,name,vrow in rows:
    k=norm(name)
    if k in seg:
        st,et=seg[k]; upd.append((int(vrow),name,st,et))
    else: miss.append(name)

print(f"== {vid} == chapters/ts:{len(src)} dances:{len(rows)} matched:{len(upd)} unmatched:{len(miss)}")
for vrow,name,st,et in upd[:8]: print(f"   set {st:4d}-{et:<4d}  {name}")
if len(upd)>8: print(f"   ... +{len(upd)-8} more")
if miss: print("   UNMATCHED (left as-is):", ", ".join(miss[:10]))

if APPLY and upd:
    sqls=["BEGIN;"]+[f'UPDATE "Videos" SET "StartTime"={st},"EndTime"={et} WHERE "Id"={vrow};'
                     for vrow,_,st,et in upd]+["COMMIT;"]
    psql("\n".join(sqls),ret=False)
    print(f"APPLIED {len(upd)} timestamp updates.")
elif upd:
    print("DRY RUN (pass 'apply' to write).")
