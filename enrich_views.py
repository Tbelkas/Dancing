"""enrich_views.py — backfill Videos.ViewCount from YouTube for rows with ViewCount=0.
Fetches each distinct youtube VideoId once (--print view_count), updates all its rows.
Resumable via _proto/views.tsv (videoId\tcount). Commits in batches of 25."""
import os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
DONE="_proto/views.tsv"
def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]="dancebabydance"
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing","-v","ON_ERROR_STOP=1","-At","-F","\t"],
        input=sql,capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]
done={l.split("\t")[0] for l in open(DONE,encoding="utf-8")} if os.path.exists(DONE) else set()
vids=[r[0] for r in psql('''SELECT DISTINCT "VideoId" FROM "Videos"
   WHERE "ViewCount"=0 AND "Platform"='youtube';''')]
todo=[v for v in vids if v not in done]
print(f"distinct youtube videos to enrich: {len(todo)} (skipping {len(done)} done)")
f=open(DONE,"a",encoding="utf-8")
batch=[]; n=0
for v in todo:
    p=subprocess.run(["yt-dlp","--skip-download","--no-warnings","--print","%(view_count)s",
                      f"https://www.youtube.com/watch?v={v}"],
                     capture_output=True,text=True,encoding="utf-8")
    vc=p.stdout.strip()
    cnt=int(vc) if vc.isdigit() else 0
    f.write(f"{v}\t{cnt}\n"); f.flush()
    if cnt>0: batch.append((v,cnt))
    n+=1
    if len(batch)>=25:
        psql("BEGIN;\n"+"\n".join(f'UPDATE "Videos" SET "ViewCount"={c} WHERE "VideoId"=\'{vid}\';' for vid,c in batch)+"\nCOMMIT;")
        batch=[]
if batch:
    psql("BEGIN;\n"+"\n".join(f'UPDATE "Videos" SET "ViewCount"={c} WHERE "VideoId"=\'{vid}\';' for vid,c in batch)+"\nCOMMIT;")
f.close()
print(f"enriched {n} videos")
rem=psql('SELECT count(*) FROM "Videos" WHERE "ViewCount"=0;')
print("rows still ViewCount=0:", rem[0][0])
