"""enrich_views.py — backfill Videos.ViewCount from YouTube for rows still missing a real count.
Targets ViewCount<=100 (0 = never enriched; 1..100 = only on-site play bumps, drowned out by any
real YouTube count). Uses the cached _proto/<ytid>.json yt-dlp metadata when present, otherwise
fetches view_count live. Resumable via _proto/views2.tsv (videoId\tcount). Commits in batches of 25.
"""
import json, os, re, subprocess, sys
# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
DONE = "_proto/views2.tsv"

def db_password():
    cfg = json.load(open("DancePlatform.API/appsettings.Development.json", encoding="utf-8"))
    return re.search(r"Password=([^;]+)", cfg["ConnectionStrings"]["Default"]).group(1)

PW = db_password()

def psql(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PW
    p = subprocess.run(["psql", "-h", "192.168.0.197", "-U", "dance_user", "-d", "dancing",
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]

def cached_count(vid):
    path = f"_proto/{vid}.json"
    if not os.path.exists(path): return None
    try:
        vc = json.load(open(path, encoding="utf-8")).get("view_count")
        return int(vc) if vc else None
    except (ValueError, json.JSONDecodeError):
        return None

def fetch_count(vid):
    p = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "--print", "%(view_count)s",
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    vc = (p.stdout or "").strip()
    return int(vc) if vc.isdigit() else 0

done = {l.split("\t")[0] for l in open(DONE, encoding="utf-8")} if os.path.exists(DONE) else set()
vids = [r[0] for r in psql('''SELECT DISTINCT "VideoId" FROM "Videos"
   WHERE "ViewCount" <= 100 AND "Platform" = 'youtube';''')]
todo = [v for v in vids if v not in done]
print(f"distinct youtube videos to enrich: {len(todo)} (skipping {len(done)} done)")

f = open(DONE, "a", encoding="utf-8")
batch = []; n = 0; from_cache = 0
for v in todo:
    cnt = cached_count(v)
    if cnt is not None:
        from_cache += 1
    else:
        cnt = fetch_count(v)
    f.write(f"{v}\t{cnt}\n"); f.flush()
    if cnt > 0: batch.append((v, cnt))
    n += 1
    if len(batch) >= 25:
        psql("BEGIN;\n" + "\n".join(f'UPDATE "Videos" SET "ViewCount"={c} WHERE "VideoId"=\'{vid}\';' for vid, c in batch) + "\nCOMMIT;")
        batch = []
if batch:
    psql("BEGIN;\n" + "\n".join(f'UPDATE "Videos" SET "ViewCount"={c} WHERE "VideoId"=\'{vid}\';' for vid, c in batch) + "\nCOMMIT;")
f.close()
print(f"enriched {n} videos ({from_cache} from _proto cache)")
rem = psql('SELECT count(*) FROM "Videos" WHERE "ViewCount"<=100 AND "Platform"=\'youtube\';')
print("youtube rows still ViewCount<=100:", rem[0][0])
