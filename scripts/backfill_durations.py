"""Backfill Videos.DurationSeconds from cached yt-dlp metadata, fetching what's missing.

Sources, in order: _proto/<ytid>.json ("duration"), _proto/durations.tsv, then live yt-dlp.
Usage: python backfill_durations.py [--cached-only]
"""
import glob, json, os, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")

PSQL = ["psql", "-h", "192.168.0.197", "-U", "dance_user", "-d", "dancing"]
os.environ["PGPASSWORD"] = "LW3Q19jZyVSXRzNyGoRnWY2G3TKFT8eoRuYR"
os.environ["PGCLIENTENCODING"] = "UTF8"

def q(sql: str) -> str:
    return subprocess.run(PSQL + ["-t", "-A", "-F", "\t", "-c", sql],
                          capture_output=True, text=True, encoding="utf-8").stdout

# 1. Videos needing a duration (youtube only; tiktok/instagram have no cached metadata)
rows = [l.split("\t") for l in q(
    'SELECT "Id", "VideoId" FROM "Videos" '
    "WHERE \"Platform\" = 'youtube' AND \"DurationSeconds\" IS NULL ORDER BY \"Id\";"
).strip().splitlines() if l]
print(f"videos needing duration: {len(rows)}")

# 2. Build ytid -> seconds from the caches
durations: dict[str, int] = {}
for f in glob.glob("_proto/*.json"):
    ytid = os.path.basename(f)[:-5]
    if len(ytid) != 11:
        continue
    try:
        d = json.load(open(f, encoding="utf-8"))
        if isinstance(d.get("duration"), (int, float)) and d["duration"] > 0:
            durations[ytid] = int(d["duration"])
    except Exception:
        pass
if os.path.exists("_proto/durations.tsv"):
    for l in open("_proto/durations.tsv", encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) == 2 and p[1].isdigit():
            durations.setdefault(p[0], int(p[1]))
print(f"cached durations: {len(durations)}")

cached_only = "--cached-only" in sys.argv
updates: list[tuple[str, int]] = []
missing: list[tuple[str, str]] = []
for vid_id, ytid in rows:
    if ytid in durations:
        updates.append((vid_id, durations[ytid]))
    else:
        missing.append((vid_id, ytid))
print(f"from cache: {len(updates)}, to fetch: {len(missing)}")

if not cached_only:
    fetched: dict[str, int] = {}
    for i, (vid_id, ytid) in enumerate(missing, 1):
        if ytid in fetched:
            updates.append((vid_id, fetched[ytid]))
            continue
        r = subprocess.run(["yt-dlp", "--no-warnings", "--print", "duration",
                            f"https://www.youtube.com/watch?v={ytid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip().split("\n")[0].strip()
        if out and out.replace(".", "", 1).isdigit() and float(out) > 0:
            fetched[ytid] = int(float(out))
            updates.append((vid_id, fetched[ytid]))
            print(f"[{i}/{len(missing)}] {ytid} -> {fetched[ytid]}s")
        else:
            print(f"[{i}/{len(missing)}] {ytid} FAILED")

if updates:
    sql = "BEGIN;\n" + "\n".join(
        f'UPDATE "Videos" SET "DurationSeconds" = {secs} WHERE "Id" = {vid_id};'
        for vid_id, secs in updates) + "\nCOMMIT;"
    r = subprocess.run(PSQL + ["-q", "-v", "ON_ERROR_STOP=1"], input=sql,
                       capture_output=True, text=True, encoding="utf-8")
    print("psql rc:", r.returncode, r.stderr.strip()[:200])
print(f"updated: {len(updates)}")
