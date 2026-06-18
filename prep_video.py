"""
prep_video.py <youtube_id>
Gathers all signals for one video + current DB state + a name-match verdict.
Caches yt-dlp JSON in _proto/<id>.json. No DB writes.
"""
import json, os, re, subprocess, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")

PGHOST="192.168.0.197"; PGUSER="dance_user"; PGDB="dancing"; PGPW="dancebabydance"
vid=sys.argv[1]
os.makedirs("_proto", exist_ok=True)
cache=f"_proto/{vid}.json"

def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h",PGHOST,"-U",PGUSER,"-d",PGDB,"-At","-F","\t","-c",sql],
                     capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower().strip()
    s=re.sub(r"^the\s+","",s); s=re.sub(r"^\d+[\.\):\-]?\s*","",s); s=re.sub(r"[^a-z0-9]+","",s)
    return s

if not os.path.exists(cache):
    p=subprocess.run(["yt-dlp","--skip-download","--no-warnings","-J",
                      f"https://www.youtube.com/watch?v={vid}"],
                     capture_output=True,text=True,encoding="utf-8")
    if p.returncode: sys.stderr.write(p.stderr[-500:]); print("FETCH_FAILED"); raise SystemExit(2)
    open(cache,"w",encoding="utf-8").write(p.stdout)
d=json.load(open(cache,encoding="utf-8"))

title=d.get("title"); dur=d.get("duration")
chapters=[(int(c["start_time"]), c["title"]) for c in (d.get("chapters") or [])]
desc=d.get("description") or ""
dl=[]
for l in desc.splitlines():
    m=re.match(r'\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s+(.+)', l)
    if m:
        h=int(m.group(3) or 0); mm=int(m.group(1)); ss=int(m.group(2))
        # if 3 groups, format is M:SS:?? unlikely; treat group1:group2 as M:SS
        t=mm*60+ss
        dl.append((t, m.group(4).strip()))
auto=[a for a in (d.get("automatic_captions") or {}) if a.startswith("en")]

# DB current state
db=psql(f'''SELECT d."Id", d."Name", v."StartTime", v."EndTime"
FROM "Videos" v JOIN "Dances" d ON d."Id"=v."DanceId"
WHERE v."VideoId"='{vid}' ORDER BY v."StartTime" NULLS FIRST, d."Id";''')
db=[(int(r[0]), r[1], r[2] or None, r[3] or None) for r in db]

src=chapters or dl
src_norms={norm(t):t for _,t in src}  # norm(title) -> title
db_norms=[(i,n,norm(n),st,et) for i,n,st,et in db]
matched=sum(1 for i,n,nn,st,et in db_norms if nn in src_norms)
have_times=sum(1 for i,n,st,et in db if st not in (None,'') )

print(f"== {vid} ==")
print(f"title : {title}")
print(f"dur   : {dur}s   chapters:{len(chapters)}  desc_ts:{len(dl)}  en_caps:{bool(auto)}")
print(f"DB    : {len(db)} dances, {have_times} with timestamps, {matched}/{len(db)} names match text-source")
if chapters:
    print("-- chapters --")
    for t,ti in chapters: print(f"   {t:4d}  {ti}")
elif dl:
    print("-- desc timestamps --")
    for t,ti in dl: print(f"   {t:4d}  {ti}")
print("-- DB dances --")
for i,n,st,et in db:
    hit="" if norm(n) in src_norms else "  <NO-MATCH>"
    print(f"   #{i:<5} {st if st else '-':>4}-{et if et else '-':<4} {n}{hit}")

# verdict
if not src and not auto:
    v="NEEDS_MULTIMODAL (no text signal)"
elif src and matched >= max(1,int(0.6*len(db))) and have_times==len(db):
    v="TIMED_OK (names match + all timed) -> verify only"
elif src and matched >= max(1,int(0.6*len(db))):
    v="NAMES_MATCH_NEED_TIMES -> map chapter/desc times onto existing dances"
else:
    v="MISMATCH -> likely wrong-source; rebuild (multimodal if needed)"
print(f"VERDICT: {v}")
