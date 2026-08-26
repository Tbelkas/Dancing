"""
tier2_backfill.py [--batch N] [--limit N] [--rebuild-queue]

Give video_gate.py tier-2 evidence for the whole catalogue.

WHY THIS EXISTS
---------------
The intake gate has three tiers, and only tier 2 - what the person in the video
actually says - can tell that a video is *wrong* rather than merely thin. When the
gate was first run over prod, 883 of 1153 rows were graded on metadata alone and
128 on the database row alone. Only 142 reached tier 2. That is why 735 videos
scored exactly 1.0: not because they are good, because nothing had looked.

So this walks every distinct YouTube id with no _proto/sig_<ytid>.json and runs
stage 01 (signals.py) on it. Ordered by how many Videos rows each id covers, so
the extractions that grade the most catalogue land first and an interrupted run
still leaves the gate better than it found it.

Resumable and idempotent: signals.py skips anything already cached, so re-running
after a crash, a reboot, or a Ctrl-C picks up where it stopped. Failures are
recorded and skipped rather than retried forever - one dead video must not stall
seven hundred.

Batched because argparse (and the Windows command line) will not take 700 ids at
once, and because a batch boundary is a safe place to stop.

    python scripts/tier2_backfill.py --rebuild-queue   refresh the todo list
    python scripts/tier2_backfill.py                   drain it
    python scripts/tier2_backfill.py --limit 50        just a taste
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "_proto")
QUEUE = os.path.join(PROTO, "tier2_queue.txt")
FAILED = os.path.join(PROTO, "tier2_failed.tsv")


def cached():
    return {os.path.basename(p)[4:-5] for p in glob.glob(os.path.join(PROTO, "sig_*.json"))}


def rebuild_queue():
    import chip_health as ch
    rows = ch.psql('''
    select v."VideoId", count(*) as nrows, max(coalesce(v."DurationSeconds",0)) as dur
      from "Videos" v where v."Platform"='youtube'
     group by 1;''').strip().splitlines()
    have = cached()
    todo = []
    for line in rows:
        ytid, n, dur = line.split("|")
        if ytid not in have:
            todo.append((ytid, int(n), int(dur)))
    # Most catalogue rows graded per extraction first; longer video breaks the tie
    # because a long one is more likely to be a real tutorial worth judging.
    todo.sort(key=lambda t: (-t[1], -t[2]))
    with open(QUEUE, "w", encoding="utf-8") as f:
        for t in todo:
            f.write(t[0] + "\n")
    print(f"queue rebuilt: {len(todo)} to extract, {len(have)} already cached")
    return [t[0] for t in todo]


def load_queue():
    if not os.path.exists(QUEUE):
        return rebuild_queue()
    return [l.strip() for l in open(QUEUE, encoding="utf-8") if l.strip()]


def failed_ids():
    if not os.path.exists(FAILED):
        return set()
    return {l.split("\t")[0] for l in open(FAILED, encoding="utf-8") if l.strip()}


def run_chunk(ids, timeout):
    """Run signals.py over these ids. Returns False if it had to be killed.

    The timeout is a guard, deliberately generous, and a trip is NOT treated as proof
    the video is bad.

    An extraction once recorded 23,199 seconds - 6.4 hours on an 11-minute clip - which
    reads exactly like a stalled download, and a tight per-video deadline is the obvious
    response. It would have been wrong. The extraction log shows one hard gap, 01:44:13
    to 08:10:49, across every process on the machine: it slept. The video was in flight
    at the time and wore the whole suspend on its own clock.

    A wall-clock deadline cannot tell "hung" from "the lid was closed", so anything it
    kills goes back on the queue rather than into the permanent skip list. Being slow
    twice is cheap; being blacklisted for sleeping through your turn is not.
    """
    try:
        # "--" so ids beginning with "-" are not read as flags. Three of them are.
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "signals.py"),
                            "--"] + ids,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=ROOT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    sys.stdout.write(p.stdout or "")
    if p.returncode:
        sys.stderr.write((p.stderr or "")[-800:])
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--per-video", type=int, default=900,
                    help="seconds per video before a batch is retried "
                         "one at a time; generous on purpose")
    ap.add_argument("--rebuild-queue", action="store_true")
    args = ap.parse_args()

    if args.rebuild_queue:
        rebuild_queue()
        return

    ids = load_queue()
    have, bad = cached(), failed_ids()
    todo = [i for i in ids if i not in have and i not in bad]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(ids)} queued  {len(ids)-len(todo)} done/skipped  {len(todo)} to go")

    t0, done = time.monotonic(), 0
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        timed_out = not run_chunk(chunk, args.per_video * len(chunk))
        if timed_out:
            # One slow video must not cost the batch. Retry the survivors one at a
            # time so a genuinely stuck one is isolated rather than the whole chunk
            # being written off - but leave it on the queue, not in FAILED.
            print("  batch timed out - retrying individually", flush=True)
            have = cached()
            for ytid in chunk:
                if ytid in have:
                    continue
                if not run_chunk([ytid], args.per_video):
                    print(f"  {ytid:<14} timed out - leaving on the queue", flush=True)

        now = cached()
        with open(FAILED, "a", encoding="utf-8") as f:
            for ytid in chunk:
                # A timeout is not a verdict (see run_chunk), so only a genuine
                # extraction failure earns a permanent skip.
                if ytid not in now and not timed_out:
                    f.write(f"{ytid}\tno sig written\n")
        done += len(chunk)
        # Monotonic, not wall clock: this machine sleeps, and a wall-clock rate turns
        # a 6-hour suspend into "0.1 videos/min, 71 hours remaining" - a number that
        # describes the lid, not the job.
        el = time.monotonic() - t0
        rate = done / el if el else 0
        left = (len(todo) - done) / rate if rate else 0
        print(f"[{done}/{len(todo)}]  {el/60:.0f}m working  "
              f"~{left/60:.0f}m left  ({rate*60:.1f}/min)", flush=True)

    print(f"\nbackfill pass complete: {len(cached())} signal caches on disk")


if __name__ == "__main__":
    main()
