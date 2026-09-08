"""check_dead_videos.py — find catalogue videos whose source upload has gone away, and remove them.

A YouTube video that is deleted, made private, or blocked still renders a perfectly normal-looking
embed on a dance page. Nothing on the site notices; the reader clicks play and gets a grey box.
This is the only thing that catches that, so it is meant to run nightly on the Pi.

Availability comes from YouTube's oEmbed endpoint, which needs no API key and no quota:

    200  the video is playable
    401  private
    404  deleted, or never existed

Anything else (429, a timeout, a 5xx) is treated as UNKNOWN and left alone — a flag raised because
YouTube was rate-limiting us is worse than no flag, because it teaches you to ignore the queue.

WHAT IT DOES, PER VIDEO
-----------------------
    alive, but flagged      resolve the flag — it came back, and a stale report is noise
    dead, not yet flagged   open a flag in /admin/flags (Source='checker')
    dead, flagged recently  leave it: inside the grace window, waiting for a second opinion
    dead, flagged long ago  DELETE the video row

NOTHING IS DELETED ON FIRST SIGHTING, and that is the whole safety design. A creator can make a
video private for a week and put it back; YouTube can 404 through a blip. Deleting a row takes its
VideoSegments with it — the chips are hours of GPU and human judgement — along with every rating,
note and saved loop anyone left on it, and none of that comes back. So a video has to be dead on
two separate runs, GRACE_DAYS apart, before it is removed. The open flag IS the record of the
first sighting, so this needs no state of its own.

Practice history survives: PracticeSessionItem.VideoId is SetNull, so the log keeps the minutes and
loses only the attribution. Everything else on the video cascades away, including its own flags —
which is why each deletion is written to a restore log first. That log is the audit trail; the
flags table can't be, because the delete erases it.

Usage:
    python scripts/check_dead_videos.py                  # check, flag, and delete what is due
    python scripts/check_dead_videos.py --dry-run        # report only, write nothing
    python scripts/check_dead_videos.py --limit 50       # a taste, for a first run
    python scripts/check_dead_videos.py --grace-days 0   # delete everything dead RIGHT NOW
    python scripts/check_dead_videos.py --no-delete      # the old behaviour: flag, never delete

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
from datetime import datetime, timezone

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PG_HOST = "192.168.0.197"
PG_USER = "dance_user"
PG_DB = "dancing"

# Polite, and well under anything YouTube throttles. ~1150 videos takes about twelve minutes,
# which is nothing for a job that runs while nobody is awake.
DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 10

# How long a video must have been flagged dead before it is deleted. Seven days is long enough
# to outlast a creator privatising something over a weekend, and short enough that a genuinely
# dead video isn't left breaking a page for a month.
GRACE_DAYS = 7

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append-only, one JSON object per deletion. The only record that survives the delete.
RESTORE_LOG = os.path.join(ROOT, "_proto", "deleted_videos.jsonl")


def _prod_password():
    """Read the live password out of the gitignored appsettings, never from a literal here."""
    cfg_path = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")
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


def sql_str(value):
    """A Postgres string literal, or NULL. Everything user-supplied goes through here."""
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def snapshot(row_id):
    """
    Everything needed to reconstruct the video by hand, captured BEFORE the delete.

    Deliberately includes the segments in full: they are the expensive part, and a deletion that
    turns out to be wrong is recoverable only if the chips were written down somewhere.
    """
    rows = psql(f'''
        SELECT row_to_json(t) FROM (
          SELECT v.*,
                 d."Name" AS dance_name,
                 (SELECT coalesce(json_agg(row_to_json(s)), '[]'::json)
                    FROM "VideoSegments" s WHERE s."VideoId" = v."Id") AS segments,
                 (SELECT count(*) FROM "VideoRatings" r WHERE r."VideoId" = v."Id") AS rating_count,
                 (SELECT count(*) FROM "VideoNotes" n WHERE n."VideoId" = v."Id") AS note_count,
                 (SELECT count(*) FROM "UserVideoLoops" l WHERE l."VideoId" = v."Id") AS loop_count,
                 (SELECT count(*) FROM "PracticeSessionItems" p WHERE p."VideoId" = v."Id") AS practice_count
          FROM "Videos" v JOIN "Dances" d ON d."Id" = v."DanceId"
          WHERE v."Id" = {int(row_id)}
        ) t;
    ''')
    return json.loads(rows[0][0]) if rows else None


def delete_video(row_id, dance_id, state):
    """
    Remove one dead video and repair what the delete leaves stale.

    The dance's rating aggregate is denormalized (Dance.AverageRating / RatingCount) and the
    cascade takes the video's ratings with it, so recomputing here is not optional -- skipping it
    leaves a dance advertising an average built partly from ratings that no longer exist. The
    recompute mirrors VideoService.RecomputeDanceRatingAsync, which counts only approved videos'
    ratings because VideoRatings carries the intake query filter.
    """
    record = snapshot(row_id)
    if record is not None:
        record["deleted_at"] = datetime.now(timezone.utc).isoformat()
        record["deleted_because"] = f"YouTube says: {state}"
        os.makedirs(os.path.dirname(RESTORE_LOG), exist_ok=True)
        with open(RESTORE_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    # One statement: the delete and the aggregate repair must not be separable, or an interrupted
    # run leaves a dance quoting a rating average for videos that are gone.
    psql(f'''
        BEGIN;
        DELETE FROM "Videos" WHERE "Id" = {int(row_id)};
        UPDATE "Dances" SET
          "RatingCount" = COALESCE((SELECT count(*) FROM "VideoRatings" r
                                      JOIN "Videos" v ON v."Id" = r."VideoId"
                                     WHERE v."DanceId" = {int(dance_id)}
                                       AND v."ReviewState" = 'approved'), 0),
          "AverageRating" = COALESCE((SELECT avg(r."Rating") FROM "VideoRatings" r
                                        JOIN "Videos" v ON v."Id" = r."VideoId"
                                       WHERE v."DanceId" = {int(dance_id)}
                                         AND v."ReviewState" = 'approved'), 0)
        WHERE "Id" = {int(dance_id)};
        COMMIT;
    ''')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="check at most this many videos")
    parser.add_argument("--dry-run", action="store_true", help="report findings, write nothing")
    parser.add_argument("--no-delete", action="store_true",
                        help="flag dead videos but never delete them")
    parser.add_argument("--grace-days", type=int, default=GRACE_DAYS,
                        help=f"days a video must have been flagged dead before deletion "
                             f"(default {GRACE_DAYS}; 0 deletes on sight)")
    args = parser.parse_args()

    # Every approved global YouTube video, with the age in days of its oldest open dead-video
    # flag (NULL when it has none). That age is what decides flag-vs-delete, so it has to come
    # back with the row rather than be looked up per video.
    rows = psql('''
        SELECT v."Id", v."VideoId", v."Title", v."DanceId", d."Name",
               COALESCE(EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'UTC' - (
                 SELECT min(f."CreatedAt") FROM "VideoFlags" f
                  WHERE f."VideoId" = v."Id" AND f."Reason" = 'dead-video'
                    AND f."Source" = 'checker' AND f."ResolvedAt" IS NULL
               ))) / 86400, -1)::text
        FROM "Videos" v
        JOIN "Dances" d ON d."Id" = v."DanceId"
        WHERE v."ReviewState" = 'approved'
          AND v."OwnerUserId" IS NULL
          AND v."Platform" = 'youtube'
        ORDER BY v."Id";
    ''')
    if args.limit:
        rows = rows[:args.limit]

    # flush= on every progress line: this is meant to run nightly with its output redirected to a
    # log, and print() to a pipe is block-buffered -- without it a twelve-minute run shows nothing
    # at all until it exits, which reads as a hang.
    print(f"checking {len(rows)} video(s), grace {args.grace_days}d"
          f"{' [DRY RUN]' if args.dry_run else ''}", flush=True)

    flagged, deleted, waiting, revived, unknown, fine = [], [], 0, 0, 0, 0

    for index, (row_id, source_id, title, dance_id, dance, flag_age) in enumerate(rows, 1):
        state = availability(source_id)
        age = float(flag_age)
        has_flag = age >= 0

        if state == "unknown":
            unknown += 1
        elif state == "ok":
            if has_flag:
                # It came back. Clearing the report matters as much as raising one: a queue full
                # of things that already fixed themselves is a queue nobody reads.
                revived += 1
                print(f"  BACK  {dance} — {title} ({source_id})", flush=True)
                if not args.dry_run:
                    psql(f'''UPDATE "VideoFlags"
                                SET "ResolvedAt" = NOW() AT TIME ZONE 'UTC',
                                    "Resolution" = 'the video came back'
                              WHERE "VideoId" = {int(row_id)} AND "Reason" = 'dead-video'
                                AND "Source" = 'checker' AND "ResolvedAt" IS NULL;''')
            else:
                fine += 1
        elif not has_flag:
            flagged.append((int(row_id), source_id, title, dance, state))
            print(f"  DEAD  [{state}] {dance} — {title} ({source_id})", flush=True)
        elif args.no_delete or age < args.grace_days:
            waiting += 1
            print(f"  DEAD  [{state}] {dance} — {title} — flagged {age:.1f}d ago, "
                  f"{'delete disabled' if args.no_delete else f'deleting at {args.grace_days}d'}",
                  flush=True)
        else:
            deleted.append((int(row_id), int(dance_id), source_id, title, dance, state, age))
            print(f"  GONE  [{state}] {dance} — {title} — dead {age:.1f}d, deleting", flush=True)

        time.sleep(DELAY_SECONDS)

    print(f"\n{fine} fine, {revived} came back, {len(flagged)} newly flagged, "
          f"{waiting} waiting out grace, {len(deleted)} to delete, {unknown} inconclusive",
          flush=True)

    if args.dry_run:
        print("--dry-run: nothing written", flush=True)
        return

    if flagged:
        values = ",\n".join(
            f"({row_id}, 'dead-video', {sql_str(f'YouTube says: {state}')}, 'checker', "
            f"NOW() AT TIME ZONE 'UTC')"
            for row_id, _, _, _, state in flagged)
        psql(f'''INSERT INTO "VideoFlags" ("VideoId", "Reason", "Detail", "Source", "CreatedAt")
                 VALUES {values};''')
        print(f"flagged {len(flagged)} — waiting in /admin/flags", flush=True)

    for row_id, dance_id, source_id, title, dance, state, age in deleted:
        delete_video(row_id, dance_id, state)
        print(f"  deleted #{row_id} {dance} — {title}", flush=True)

    if deleted:
        print(f"deleted {len(deleted)} video(s); each one is written to {RESTORE_LOG} "
              f"in full, chips included", flush=True)


if __name__ == "__main__":
    main()
