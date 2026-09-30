"""backfill_channels.py - fill Videos.ChannelName/ChannelUrl for rows that don't have one yet.

The API credits a video on create (VideoChannelService), but the seeding scripts insert with raw
SQL and never pass through it - so rerun this after every seed run, like enrich_views.py.

Source, in order: the cached _proto/<ytid>.json yt-dlp metadata, else the platform's public
oEmbed endpoint (keyless; YouTube and TikTok). Instagram has no keyless lookup and is skipped.
The name MUST come out the same whichever source supplied it: browse filters on an exact match,
so "blogilates" from the cache and "Blogilates" from oEmbed would split one creator in two.
yt-dlp's `channel` field is the same string oEmbed returns as author_name.

    python scripts/backfill_channels.py            # everything still missing
    python scripts/backfill_channels.py --limit 20 # a quick trial
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _prod_password():
    cfg = json.load(open("DancePlatform.API/appsettings.Development.json", encoding="utf-8"))
    return re.search(r"Password=([^;]+)", cfg["ConnectionStrings"]["Default"]).group(1)


PW = _prod_password()


def psql(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PW
    p = subprocess.run(["psql", "-h", "192.168.0.196", "-U", "dance_user", "-d", "dancing",
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def q(s):
    return "'" + s.replace("'", "''") + "'"


def from_cache(platform, vid):
    if platform != "youtube": return None
    path = f"_proto/{vid}.json"
    if not os.path.exists(path): return None
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(d, dict): return None
    name = (d.get("channel") or d.get("uploader") or "").strip()
    # The @handle URL, to match what oEmbed hands back for everything else.
    url = (d.get("uploader_url") or d.get("channel_url") or "").strip()
    return (name, url) if name and url else None


def from_oembed(platform, vid):
    if platform == "youtube":
        endpoint = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
            f"https://www.youtube.com/watch?v={vid}", safe="")
    elif platform == "tiktok":
        endpoint = "https://www.tiktok.com/oembed?url=" + urllib.parse.quote(
            f"https://www.tiktok.com/video/{vid}", safe="")
    else:
        return None
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
    except Exception:
        # 401/404 = private or removed. Left NULL; the next run tries again.
        return None
    name = (d.get("author_name") or "").strip()
    url = (d.get("author_url") or "").strip()
    return (name, url) if name and url else None


def lookup(row):
    platform, vid = row
    return platform, vid, from_cache(platform, vid) or from_oembed(platform, vid)


limit = None
if "--limit" in sys.argv:
    limit = int(sys.argv[sys.argv.index("--limit") + 1])

rows = [tuple(r) for r in psql('''SELECT DISTINCT "Platform", "VideoId" FROM "Videos"
   WHERE "ChannelName" IS NULL AND "Platform" IN ('youtube', 'tiktok') ORDER BY 1, 2;''')]
if limit: rows = rows[:limit]
print(f"distinct source videos without a channel: {len(rows)}")

found, missed, batch = 0, [], []


def flush():
    if not batch: return
    psql("BEGIN;\n" + "\n".join(
        f'UPDATE "Videos" SET "ChannelName"={q(n)}, "ChannelUrl"={q(u)} '
        f'WHERE "Platform"={q(p)} AND "VideoId"={q(v)} AND "ChannelName" IS NULL;'
        for p, v, n, u in batch) + "\nCOMMIT;")
    batch.clear()


with ThreadPoolExecutor(max_workers=8) as pool:
    for i, (platform, vid, hit) in enumerate(pool.map(lookup, rows), 1):
        if hit:
            found += 1
            batch.append((platform, vid, hit[0], hit[1]))
            if len(batch) >= 50: flush()
        else:
            missed.append(f"{platform}/{vid}")
        if i % 200 == 0: print(f"  {i}/{len(rows)}  found {found}")
flush()

print(f"credited {found}; no answer for {len(missed)}")
for m in missed[:20]: print("  missing:", m)
left = psql('''SELECT count(*) FROM "Videos" WHERE "ChannelName" IS NULL;''')[0][0]
top = psql('''SELECT "ChannelName", count(*) FROM "Videos" WHERE "ChannelName" IS NOT NULL
   GROUP BY 1 ORDER BY 2 DESC LIMIT 5;''')
print("rows still without a channel:", left)
print("top channels:", ", ".join(f"{n} ({c})" for n, c in top))
