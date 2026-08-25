"""
apply_sections.py <videoDbId> "Label@start-end;Label@start-end;..." [apply] [keeptype]
                  [--source S] [--confidence C]

Inserts VideoSegments for one Videos row and sets its VideoType='tutorial'.
Pass 'keeptype' to leave VideoType untouched (steps/performance clips that get
chips must NOT be relabeled as tutorials).
Times accept seconds (int) or m:ss. End optional ("Label@start"). Dry-run unless 'apply'.
Replaces any existing segments on that video.

PROVENANCE
----------
Every row is written with "Source", "Confidence", "Model" (a run id) and
"GeneratedAt", the same four columns apply_chips.py fills in. Without them a chip
set is anonymous: chip_health cannot bucket it, and apply_chips' overwrite rule -
which only replaces a set whose recorded confidence is lower, and never replaces
"manual" - has nothing to compare against, so it treats the row as unrateable.

--source defaults to "transcript" because that is what this path actually is: a
transcript read by hand or by the find-chips skill, per SECTIONS_FIXUP.md. Pass
`--source manual` for chips a person genuinely authored - that value is the one
apply_chips.py refuses to overwrite, so it is how you make a set permanent, and
it should be a deliberate choice rather than a default that quietly freezes the
whole back catalogue.

The run id is printed and goes in "Model", so a batch is reversible with the tool
that already exists:

    python scripts/apply_chips.py --undo <runid>
"""
import argparse
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

PGHOST = "192.168.0.197"; PGUSER = "dance_user"; PGDB = "dancing"
MAX_LABEL = 34


def _prod_password():
    """Read the prod DB password from appsettings (gitignored) rather than hardcoding it.

    This repo is public: a literal here leaks the production database on every push.
    """
    import json as _json
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _cfg = os.path.join(_root, "DancePlatform.API", "appsettings.Development.json")
    for _v in _json.load(open(_cfg, encoding="utf-8-sig")).get("ConnectionStrings", {}).values():
        if "192.168.0.197" in _v:
            return dict(_p.split("=", 1) for _p in _v.split(";") if "=" in _p).get("Password", "")
    raise SystemExit(f"No prod (192.168.0.197) connection string in {_cfg}")


def to_sec(s):
    s = s.strip()
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + int(sec)
    return int(s)


def parse_spec(spec):
    segs = []
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        label, times = part.rsplit("@", 1)
        if "-" in times:
            st, et = times.split("-", 1)
            segs.append((label.strip(), to_sec(st), to_sec(et)))
        else:
            segs.append((label.strip(), to_sec(times), None))
    return segs


def sql_lit(s):
    return s.replace("'", "''")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videoDbId", type=int)
    ap.add_argument("spec")
    # 'apply' and 'keeptype' stay positional so every call already written down in
    # SECTIONS_FIXUP.md keeps working unchanged.
    ap.add_argument("flags", nargs="*", help="apply | keeptype")
    ap.add_argument("--source", default="transcript",
                    help="provenance tier: transcript (default) | manual | generic")
    ap.add_argument("--confidence", type=float,
                    help="0-1 quality of this set; apply_chips compares against it")
    args = ap.parse_args()

    unknown = [f for f in args.flags if f not in ("apply", "keeptype")]
    if unknown:
        ap.error(f"unknown positional flag(s): {' '.join(unknown)}")
    apply = "apply" in args.flags
    keeptype = "keeptype" in args.flags
    if args.confidence is not None and not 0 <= args.confidence <= 1:
        ap.error("--confidence must be between 0 and 1")

    vid_db = args.videoDbId
    segs = parse_spec(args.spec)

    conf = "NULL" if args.confidence is None else f"{args.confidence}"
    runid = ("sections-run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
             + "-" + uuid.uuid4().hex[:6])

    print(f"video {vid_db}: {len(segs)} segments   source={args.source} "
          f"confidence={'-' if args.confidence is None else args.confidence}")
    for lbl, st, et in segs:
        print(f"  {st:>4}-{'' if et is None else et:>4}  {lbl}")
    long = [l for l, _, _ in segs if len(l) > MAX_LABEL]
    if long:
        print(f"  WARNING: {len(long)} label(s) over {MAX_LABEL} chars will be "
              "truncated in the UI: " + "; ".join(long[:3]))

    if not apply:
        print("(dry-run; pass 'apply' to write)")
        raise SystemExit(0)

    values = ",".join(
        f"('{sql_lit(lbl)}',{st},{'NULL' if et is None else et},{vid_db},"
        f"'{sql_lit(args.source)}',{conf},'{runid}',now())"
        for lbl, st, et in segs
    )
    type_sql = "" if keeptype else f"""UPDATE "Videos" SET "VideoType"='tutorial' WHERE "Id"={vid_db};
"""
    sql = f"""BEGIN;
{type_sql}DELETE FROM "VideoSegments" WHERE "VideoId"={vid_db};
INSERT INTO "VideoSegments"("Label","StartTime","EndTime","VideoId",
                            "Source","Confidence","Model","GeneratedAt")
VALUES {values};
COMMIT;"""

    env = dict(os.environ)
    env["PGPASSWORD"] = _prod_password()
    env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", PGHOST, "-U", PGUSER, "-d", PGDB,
                        "-v", "ON_ERROR_STOP=1"],
                       input=sql, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    sys.stdout.write(p.stdout)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(1)
    print(f"APPLIED  run id {runid}")
    print(f"undo with: python scripts/apply_chips.py --undo {runid}")


if __name__ == "__main__":
    main()
