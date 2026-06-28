"""
find_chip_candidates.py [--init]
Daily local check for tutorial videos that still have no "Sections" chips
(VideoSegments). Detection only — it never writes to the DB.

- Reads the prod DB connection string from DancePlatform.API/appsettings.Development.json
  (so it survives password rotations; no credential hardcoded here).
- A candidate = youtube video whose title says "tutorial" OR VideoType='tutorial'
  AND has zero VideoSegments.
- `_proto/chip_skip.tsv`  : video ids we've deliberately decided NOT to chip
  (music montages, no-caption/no-chapter clips, short single-move clips).
- `_proto/chip_seen.tsv`  : video ids already announced, so each new one is flagged once.
- Rewrites the block between the CHIP-QUEUE markers in SECTIONS_FIXUP.md with the
  current actionable queue (candidates minus skip) + a timestamp. New-since-last-run
  items are starred and logged to stdout (the scheduled task appends that to a log).

Run `--init` once to seed the skip list with everything currently un-chipped
(all already triaged), so only genuinely NEW future videos surface.
"""
import json, os, subprocess, sys, datetime
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
APPSETTINGS = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")
TRACKER = os.path.join(ROOT, "SECTIONS_FIXUP.md")
SKIP = os.path.join(ROOT, "_proto", "chip_skip.tsv")
SEEN = os.path.join(ROOT, "_proto", "chip_seen.tsv")
START, END = "<!-- CHIP-QUEUE:START -->", "<!-- CHIP-QUEUE:END -->"


def prod_conn():
    d = json.load(open(APPSETTINGS, encoding="utf-8-sig"))
    for v in d.get("ConnectionStrings", {}).values():
        if "192.168.0.197" in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    raise SystemExit("No prod (192.168.0.197) connection string in appsettings.Development.json")


def psql(sql):
    c = prod_conn()
    env = dict(os.environ); env["PGPASSWORD"] = c.get("Password", ""); env["PGCLIENTENCODING"] = "UTF8"
    p = subprocess.run(["psql", "-h", c["Host"], "-U", c["Username"], "-d", c["Database"],
                        "-At", "-F", "\t", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(2)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def load_ids(path):
    if not os.path.exists(path):
        return set()
    return {l.split("\t")[0] for l in open(path, encoding="utf-8").read().splitlines() if l.strip()}


def write_ids(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join("\t".join(r) for r in rows) + ("\n" if rows else ""))


def write_queue_block(pending, new_count):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [START, f"## Auto-detected chip queue _(last checked {ts})_", ""]
    if pending:
        lines.append(f"{len(pending)} tutorial video(s) awaiting section chips ({new_count} new since last check):")
        lines.append("")
        lines.append("| VideoDbId | YtId | Dance |")
        lines.append("|---|---|---|")
        for vid, yt, name in pending:
            star = " ⭐" if vid in NEW_IDS else ""
            lines.append(f"| {vid} | {yt} | {name}{star} |")
        lines.append("")
        lines.append("_Run `/find-chips` in a local session to process these (LAN DB access required)._")
    else:
        lines.append("No videos awaiting chips. ✅")
    lines.append(END)
    block = "\n".join(lines)

    text = open(TRACKER, encoding="utf-8").read() if os.path.exists(TRACKER) else ""
    if START in text and END in text:
        pre = text[:text.index(START)]
        post = text[text.index(END) + len(END):]
        text = pre + block + post
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    open(TRACKER, "w", encoding="utf-8").write(text)


NEW_IDS = set()


def main():
    init = "--init" in sys.argv
    rows = psql("""SELECT v."Id", v."VideoId", d."Name"
FROM "Videos" v JOIN "Dances" d ON d."Id"=v."DanceId"
WHERE v."Platform"='youtube'
  AND (v."Title" ILIKE '%tutorial%' OR v."VideoType"='tutorial')
  AND NOT EXISTS (SELECT 1 FROM "VideoSegments" s WHERE s."VideoId"=v."Id")
ORDER BY v."Id";""")
    cands = [(r[0], r[1], r[2]) for r in rows]
    cand_ids = {c[0] for c in cands}

    if init:
        write_ids(SKIP, [(c[0], c[1], c[2]) for c in cands])
        write_ids(SEEN, [(c[0],) for c in cands])
        write_queue_block([], 0)
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] init: seeded skip with {len(cands)} already-triaged videos; queue empty.")
        return

    skip = load_ids(SKIP)
    seen = load_ids(SEEN)
    pending = [c for c in cands if c[0] not in skip]
    NEW_IDS.update(c[0] for c in pending if c[0] not in seen)

    write_queue_block(pending, len(NEW_IDS))
    write_ids(SEEN, [(i,) for i in sorted(seen | cand_ids)])

    stamp = f"[{datetime.datetime.now():%Y-%m-%d %H:%M}]"
    if NEW_IDS:
        print(f"{stamp} {len(NEW_IDS)} NEW video(s) need chips: " +
              ", ".join(f"{c[2]}({c[0]})" for c in pending if c[0] in NEW_IDS))
    else:
        print(f"{stamp} no new videos need chips ({len(pending)} still pending).")


if __name__ == "__main__":
    main()
