"""
fix_waacking_catalog.py [apply]

Catalog hygiene for the Waacking style, ahead of the roadmap rewrite.

Three problems, all found by resolving every Waacking dance's video back to YouTube:

  1. Nine of the ten Waacking dance descriptions were wrong. They read like they were
     generated from the slug alone during the 2026-07 description pass: `en-dehors` and
     `sous-sous` (both classical ballet terms) were described as arm throws, `the-heel-toe`
     was described as "a fundamental step in hip-hop dance", and `ololufe` / `gazelle` were
     described as waacking arm moves when their videos are an Afrobeats choreo and a
     Zootopia clip.

  2. Video 319's stored VideoId pointed at the wrong YouTube video. The title is a real
     Korean waacking-basics clip ("J KI | Waacking Basic ... | New Flare Dance Academy"),
     but the id `zdbG5BFuBLE` resolves to "How to Flare Tutorial (Breakdance Powermove)"
     by pigmie. The studio is called *New Flare* Dance Academy, which is probably how the
     two got crossed. The real video is hyxUBMVd0_Y (40s).

  3. `ololufe` is an Afrobeats choreography routine filed under Waacking.

`sous-sous` and `en-dehors` move to Classical / Ballet. That was held back on the first run
because waacking.json still linked them and moving them would have left live roadmap steps
unresolvable; the rewritten roadmap does not link them, so they can go.

Still deliberately NOT done here: deleting `gazelle`, whose only video is a Zootopia movie
clip. There is no correct style to move it to, so it needs a delete decision rather than a
quiet reassignment.

Re-running is safe: descriptions already matching are skipped, and the video and style
updates are idempotent.

Dry-run unless 'apply'.
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

PGHOST = "192.168.0.197"; PGUSER = "dance_user"; PGDB = "dancing"


def _prod_password():
    """Read the prod DB password from appsettings (gitignored) rather than hardcoding it.

    This repo is public: a literal here leaks the production database on every push.
    """
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _cfg = os.path.join(_root, "DancePlatform.API", "appsettings.Development.json")
    for _v in json.load(open(_cfg, encoding="utf-8-sig")).get("ConnectionStrings", {}).values():
        if "192.168.0.197" in _v:
            return dict(_p.split("=", 1) for _p in _v.split(";") if "=" in _p).get("Password", "")
    raise SystemExit(f"No prod (192.168.0.197) connection string in {_cfg}")


PGPW = _prod_password()
APPLY = "apply" in sys.argv[1:]

WAACKING_STYLE_ID = 8
AFROBEATS_STYLE_ID = 13

# dance id -> corrected description. Keyed by id, not slug: slugs are unique per style
# and `ololufe` moves out of Waacking in this same run.
DESCRIPTIONS = {
    342: "A classical ballet turn that rotates outward, away from the supporting leg — "
         "the opposite direction to an en dedans turn.",
    393: "Sharp arm flicks thrown while the body pivots a quarter turn underneath, so the "
         "rotation and the whip land on the same beat.",
    364: "A turn on the ball of one supporting foot with the other leg extended, holding an "
         "open shape all the way through the rotation.",
    476: "A waacking footwork basic that rocks between the heel and the ball of the foot, "
         "keeping the lower half alive underneath the arm work.",
    989: "An Afrobeats choreography routine set to Oxlade's \"Ololufe\" — the song danced "
         "through in sequence rather than a single named step.",
    1315: "A classical ballet step: a quick rise onto both feet in a tight fifth position, "
          "so the legs read as a single line.",
    328: "The rotational arm work the style is named for — the arm travels from the chest, "
         "over the head and back down, driven from the shoulder rather than the elbow.",
    1676: "The 1970s Los Angeles club style of rotational arm work, sharp poses and dramatic "
          "musicality — created by Black, Latino and Asian LGBTQ+ dancers in the disco era.",
    2057: "Held shapes that end a phrase, drawn from old Hollywood glamour — the Marilyn "
          "Monroe and screen-icon poses the original dancers played out on the floor.",
}

# video id -> (correct YouTube id, correct duration in seconds)
VIDEO_FIXES = {
    319: ("hyxUBMVd0_Y", 40),
}

BALLET_STYLE_ID = 4

# (danceId, fromStyleId, toStyleId)
RESTYLE = [
    (989, WAACKING_STYLE_ID, AFROBEATS_STYLE_ID),   # ololufe — an Oxlade choreo routine
    # sous-sous and en-dehors are classical ballet terms whose videos are a beginner pointe
    # class and a pirouette-tips video. They were held back on the first run because
    # waacking.json still linked them; the rewritten roadmap does not, so they can move.
    (1315, WAACKING_STYLE_ID, BALLET_STYLE_ID),
    (342, WAACKING_STYLE_ID, BALLET_STYLE_ID),
]


def psql(sql, fetch=True):
    env = dict(os.environ)
    env["PGPASSWORD"] = PGPW
    env["PGCLIENTENCODING"] = "UTF8"
    # SQL on stdin, not -c: the descriptions contain em dashes, and an argv round-trip
    # through the Windows console mangles them into invalid UTF-8.
    p = subprocess.run(
        ["psql", "-h", PGHOST, "-U", PGUSER, "-d", PGDB,
         "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
        input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(2)
    return [l.split("\t") for l in p.stdout.splitlines() if l] if fetch else None


def q(s):
    return "'" + s.replace("'", "''") + "'"


before = {int(i): (s, d) for i, s, d in psql(
    'select "Id", "Slug", coalesce("Description", \'\') from "Dances" '
    f'where "Id" in ({",".join(str(k) for k in DESCRIPTIONS)});')}

print("=== descriptions ===")
changed = []
for did, new in DESCRIPTIONS.items():
    slug, old = before.get(did, ("?", ""))
    if old.strip() == new.strip():
        print(f"  [{did}] {slug}: already correct, skipping")
        continue
    changed.append(did)
    print(f"\n  [{did}] {slug}")
    print(f"    - {old}")
    print(f"    + {new}")

print("\n=== videos ===")
for vid, (ytid, dur) in VIDEO_FIXES.items():
    row = psql(f'select "VideoId", coalesce("DurationSeconds"::text, \'-\'), "Title" '
               f'from "Videos" where "Id"={vid};')
    if row:
        print(f"  [{vid}] {row[0][2][:60]}")
        print(f"    - VideoId={row[0][0]}  DurationSeconds={row[0][1]}")
        print(f"    + VideoId={ytid}  DurationSeconds={dur}")

print("\n=== styles ===")
for did, frm, to in RESTYLE:
    cur = psql(f'select s."Id", s."Name" from "DanceStyles" ds join "Styles" s on s."Id"=ds."StyleId" '
               f'where ds."DanceId"={did};')
    print(f"  [{did}] currently: {', '.join(n for _, n in cur)} -> move {frm} to {to}")

if not APPLY:
    print("\n(dry-run; pass 'apply' to write)")
    raise SystemExit(0)

stmts = ["begin;"]
for did in changed:
    stmts.append(f'update "Dances" set "Description"={q(DESCRIPTIONS[did])} where "Id"={did};')
for vid, (ytid, dur) in VIDEO_FIXES.items():
    stmts.append(f'update "Videos" set "VideoId"={q(ytid)}, "DurationSeconds"={dur} where "Id"={vid};')
for did, frm, to in RESTYLE:
    # Insert the new pairing before dropping the old one so the dance is never style-less.
    stmts.append(f'insert into "DanceStyles" ("DanceId","StyleId") values ({did},{to}) '
                 f'on conflict do nothing;')
    stmts.append(f'delete from "DanceStyles" where "DanceId"={did} and "StyleId"={frm};')
stmts.append("commit;")

psql("\n".join(stmts), fetch=False)
print(f"\napplied: {len(changed)} descriptions, {len(VIDEO_FIXES)} video(s), {len(RESTYLE)} restyle(s)")

print("""
Still open, deliberately not done here:
  - gazelle (882): its only video is a 21s Zootopia movie clip, not a dance tutorial.
    No correct style to move it to — needs a delete decision.
  - sous-sous (1315) and en-dehors (342): both are ballet videos (a beginner pointe class
    and a pirouette-tips video) and belong in Classical / Ballet (4), but waacking.json
    still links them. Restyle them in the same commit that drops those roadmap steps.
  - the-heel-toe (476): the dance name says heel-toe, but the video teaches arm-and-foot
    coordination on the bassline. Either rename the dance or find a real heel-toe video.
  - waacking-arm (328): its video is a 35s tutting x waacking choreo demo, not instruction.
    The roadmap rewrite points the whack at Versa-Style's tutorial instead.
""")
