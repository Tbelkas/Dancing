"""check_dead_videos.py — find catalogue videos whose source upload has gone away.

A YouTube video that is deleted, made private, or blocked still renders a perfectly normal-looking
embed on a dance page. Nothing on the site notices; the reader clicks play and gets a grey box.
This is the only thing that catches that, so it is meant to run nightly on the Pi.

Availability comes from YouTube's oEmbed endpoint, which needs no API key and no quota:

    200  the video is playable
    401  private
    404  deleted, or never existed

Anything else (429, a timeout, a 5xx) is treated as UNKNOWN and left alone — a flag raised because
YouTube was rate-limiting us is worse than no flag, because it teaches you to ignore the queue.

A dead video is recorded as an open row in "VideoFlags" with Source='checker', which puts it in the
same admin Reports queue as viewer reports (/admin/flags). Re-running is safe: the same
one-open-flag-per-video-and-reason rule the API enforces is applied here, so a video already
flagged is not flagged again, and one that has been resolved is only re-flagged if it is still dead.

Usage:
    python scripts/check_dead_videos.py            # check everything approved
    python scripts/check_dead_videos.py --limit 50 # a taste, for a first run
    python scripts/check_dead_videos.py --dry-run  # report, write nothing

Only YouTube is checked. Instagram and TikTok have no keyless availability endpoint, and guessing
from an HTML fetch produces false positives on exactly the videos nobody wants re-checked.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PG_HOST = "192.168.0.197"
PG_USER = "dance_user"
PG_DB = "dancing"

# Polite, and well under anything YouTube throttles. ~800 videos takes about seven minutes,
# which is nothing for a job that runs while nobody is awake.
DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 10


def _prod_password():
    """Read the live password out of the gitignored appsettings, never from a literal here."""
    cfg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "DancePlatform.API", "appsettings.Development.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    return re.search(r"Password=([^;]+)", cfg["ConnectionStrings"]["Default"]).group(1)


PW = _prod_password()


def psql(sql):
    env = dict(os.environ)
    env["PGPASSWORD"] = PW
    p = subprocess.run(
        ["psql", "-h", PG_HOST, "-U", PG_USER, "-d", PG_DB,
         "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
        input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(1)
    return [line.split("\t") for line in p.stdout.splitlines() if line]


def availability(video_id):
    """'ok', 'private', 'gone', or 'unknown'. Never guesses on a transport failure."""
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "format": "json",
    })
    request = urllib.request.Request(url, headers={"User-Agent": "DancePlatform-link-checker/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return "ok" if response.status == 200 else "unknown"
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return "gone"
        if err.code == 401:
            return "private"
        # 429 and every 5xx say something about YouTube, not about the video.
        return "unknown"
    except (urllib.error.URLError, TimeoutError, OSError):
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="check at most this many videos")
    parser.add_argument("--dry-run", action="store_true", help="report findings, write nothing")
    args = parser.parse_args()

    # Approved, global, YouTube. A quarantined video is already off the site, and a personal one
    # belongs to whoever added it. Videos already carrying an open dead-video flag are skipped
    # here rather than after the request, so a re-run costs nothing for what is already known.
    rows = psql('''
        SELECT v."Id", v."VideoId", v."Title", d."Name"
        FROM "Videos" v
        JOIN "Dances" d ON d."Id" = v."DanceId"
        WHERE v."ReviewState" = 'approved'
          AND v."OwnerUserId" IS NULL
          AND v."Platform" = 'youtube'
          AND NOT EXISTS (
            SELECT 1 FROM "VideoFlags" f
            WHERE f."VideoId" = v."Id" AND f."Reason" = 'dead-video' AND f."ResolvedAt" IS NULL)
        ORDER BY v."Id";
    ''')
    if args.limit:
        rows = rows[:args.limit]

    # flush= on every progress line: this is meant to run nightly with its output
    # redirected to a log, and print() to a pipe is block-buffered -- without it a
    # ten-minute run shows nothing at all until it exits, which reads as a hang.
    print(f"checking {len(rows)} video(s)", flush=True)

    dead, unknown = [], 0
    for index, (row_id, source_id, title, dance) in enumerate(rows, 1):
        state = availability(source_id)
        if state in ("gone", "private"):
            dead.append((int(row_id), source_id, title, dance, state))
            print(f"  DEAD  [{state}] {dance} — {title} ({source_id})", flush=True)
        elif state == "unknown":
            unknown += 1
        if index % 50 == 0:
            print(f"  ...{index}/{len(rows)}", flush=True)
        time.sleep(DELAY_SECONDS)

    print(f"\n{len(dead)} dead, {unknown} inconclusive, {len(rows) - len(dead) - unknown} fine")

    if not dead:
        return
    if args.dry_run:
        print("--dry-run: no flags written")
        return

    # One statement, one transaction. A half-written batch would leave the queue in a state that
    # reads as "these are the only dead ones", which is worse than none.
    values = ",\n".join(
        "({}, 'dead-video', {}, 'checker', NOW() AT TIME ZONE 'UTC')".format(
            row_id, "'" + f"YouTube says: {state}".replace("'", "''") + "'")
        for row_id, _, _, _, state in dead)
    psql(f'''
        INSERT INTO "VideoFlags" ("VideoId", "Reason", "Detail", "Source", "CreatedAt")
        VALUES
        {values};
    ''')
    print(f"wrote {len(dead)} flag(s) — they are waiting in /admin/flags")


if __name__ == "__main__":
    main()
