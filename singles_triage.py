"""
singles_triage.py  — triage the single-move videos (1 dance, 1 video).
For each: fetch yt title (cached), compare to dance name. Flag wrong-source suspects.
Resumable: skips videos already in _proto/singles_triage.tsv. No DB writes.
Output TSV cols: vid \t danceId \t verdict \t danceName \t title
"""
import json, os, re, subprocess, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
PGPW="dancebabydance"; OUT="_proto/singles_triage.tsv"
os.makedirs("_proto", exist_ok=True)

def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]=PGPW
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing","-At","-F","\t","-c",sql],
                     capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+"," ",s)

STOP={"the","a","to","do","of","and","how","dance","move","moves","tutorial","step","steps",
      "for","beginners","beginner","basic","basics","with","in","your","easy"}
def toks(s): return {w for w in norm(s).split() if w and w not in STOP and len(w)>2}

rows=psql('''SELECT v."VideoId", d."Id", d."Name" FROM "Videos" v JOIN "Dances" d ON d."Id"=v."DanceId"
WHERE v."VideoId" IN (SELECT "VideoId" FROM "Videos" GROUP BY "VideoId" HAVING count(DISTINCT "DanceId")=1)
ORDER BY d."Id";''')

done={l.split("\t")[0] for l in open(OUT,encoding="utf-8")} if os.path.exists(OUT) else set()
f=open(OUT,"a",encoding="utf-8")
n=0
for vid,did,name in rows:
    if vid in done: continue
    n+=1
    cache=f"_proto/{vid}.json"
    if not os.path.exists(cache):
        p=subprocess.run(["yt-dlp","--skip-download","--no-warnings","-J",
                          f"https://www.youtube.com/watch?v={vid}"],
                         capture_output=True,text=True,encoding="utf-8")
        if p.returncode:
            dead="not available" in (p.stderr or "")
            f.write(f"{vid}\t{did}\t{'DEAD' if dead else 'FETCH_FAIL'}\t{name}\t\n"); f.flush(); continue
        open(cache,"w",encoding="utf-8").write(p.stdout)
    try: title=json.load(open(cache,encoding="utf-8")).get("title","") or ""
    except: f.write(f"{vid}\t{did}\tFETCH_FAIL\t{name}\t\n"); f.flush(); continue
    nt=toks(name); tt=toks(title)
    overlap = nt & tt
    verdict = "OK" if (overlap or not nt) else "SUSPECT"
    f.write(f"{vid}\t{did}\t{verdict}\t{name}\t{title}\n"); f.flush()
f.close()
print(f"triaged {n} new (total rows now in {OUT})")
