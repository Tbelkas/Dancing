"""
finish_waacking_cleanup.py [apply]

The three open decisions left by the Waacking rebuild, plus the taxonomy gap it exposed.

  1. Delete two dances whose videos teach nothing:
     - gazelle (882): its only video is a 21s clip of the Gazelle character from Zootopia.
       Not a dance tutorial, and there is no style it belongs in.
     - waacking-arm (328): its only video is a 35s tutting x waacking choreography demo with
       no instruction. The concept is now covered properly by the-whack, waacking-lines,
       overheads, arm-rolls, outside-rolls and inside-rolls, and no roadmap step links it.
     Both were checked for user progress, favourites, practice items and roadmap steps first —
     all zero. Every FK into Dances cascades except RoadmapSteps.DanceId, which is SET NULL.

  2. Add a Disco musical style. Waacking is a disco style tagged Electronic / EDM, which is
     simply wrong — Tyrone Proctor pinned the distinction at tempo, disco running roughly
     127-145 BPM against the 112-121 of the house that vogue was danced to. The hustle is the
     other obvious disco-era entry and moves too.
     Deliberately NOT retagged: locking (funk, not disco — and there is no Funk style either)
     and vogue (house).

  3. Rename the-heel-toe (476). Its video does not teach a heel-toe: it teaches placing the
     feet and the arms on the bass line together while travelling. The name was the invented
     part, not the video, so the name moves to match the content.

Chipping the 5-drill arm drills video is done separately with scripts/apply_sections.py.

Re-running is safe: each phase checks its own state first.

Dry-run unless 'apply'.
"""
import json
import os
import subprocess
import sys

# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

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
DELETE_DANCES = [(882, "gazelle"), (328, "waacking-arm")]
HUSTLE_DANCE_ID = 1994

RENAME = {
    476: ("Feet and Arm Placement", "feet-and-arm-placement",
          "Placing the feet and the arms on the bass line together while travelling forward, "
          "back and side to side. The drill for when the arms look right but the dance looks "
          "static."),
}


def psql(sql, fetch=True):
    env = dict(os.environ)
    env["PGPASSWORD"] = PGPW
    env["PGCLIENTENCODING"] = "UTF8"
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


# ---- phase 1: deletions -------------------------------------------------------------
print("=== deletions ===")
to_delete = []
for did, slug in DELETE_DANCES:
    row = psql(f'select "Slug","Name" from "Dances" where "Id"={did};')
    if not row:
        print(f"  = {slug} ({did}) already gone")
        continue
    if row[0][0] != slug:
        print(f"  ! id {did} is now {row[0][0]!r}, not {slug!r} — refusing to delete")
        continue
    blockers = []
    for t, c in [("UserLearnedDances", "DanceId"), ("UserInProgressDances", "DanceId"),
                 ("UserFavoriteDances", "DanceId"), ("PracticeSessionItems", "DanceId"),
                 ("RoadmapSteps", "DanceId")]:
        n = int(psql(f'select count(*) from "{t}" where "{c}"={did};')[0][0])
        if n:
            blockers.append(f"{t}={n}")
    vids = psql(f'select "Id","Title" from "Videos" where "DanceId"={did};')
    if blockers:
        print(f"  ! {slug} ({did}) is referenced by {', '.join(blockers)} — skipping")
        continue
    to_delete.append(did)
    print(f"  - {slug} ({did}) + {len(vids)} video(s): {vids[0][1][:56] if vids else ''}")

# ---- phase 2: Disco musical style ---------------------------------------------------
print("\n=== Disco musical style ===")
disco = psql("""select "Id" from "MusicalStyles" where lower("Name")='disco';""")
disco_id = int(disco[0][0]) if disco else None
print(f"  {'exists, id ' + str(disco_id) if disco_id else 'will be created'}")

retag_ids = [int(i) for (i,) in
             (r for r in psql(f'select d."Id" from "Dances" d join "DanceStyles" ds on '
                              f'ds."DanceId"=d."Id" where ds."StyleId"={WAACKING_STYLE_ID};'))]
retag_ids = [i for i in retag_ids if i not in to_delete]
if psql(f'select 1 from "Dances" where "Id"={HUSTLE_DANCE_ID};'):
    retag_ids.append(HUSTLE_DANCE_ID)
print(f"  retagging {len(retag_ids)} dances ({len(retag_ids) - 1} Waacking + the hustle)")

# ---- phase 3: rename ----------------------------------------------------------------
print("\n=== renames ===")
rename_plan = []
for did, (name, slug, desc) in RENAME.items():
    row = psql(f'select "Name","Slug" from "Dances" where "Id"={did};')
    if not row:
        print(f"  ! dance {did} is gone, skipping")
        continue
    if row[0][1] == slug:
        print(f"  = {slug} already renamed")
        continue
    rename_plan.append((did, name, slug, desc))
    print(f"  ~ [{did}] {row[0][0]!r} ({row[0][1]}) -> {name!r} ({slug})")

if not APPLY:
    print("\n(dry-run; pass 'apply' to write)")
    raise SystemExit(0)

stmts = ["begin;"]
for did in to_delete:
    stmts.append(f'delete from "Dances" where "Id"={did};')
if disco_id is None:
    # Name/DateAdded are both NOT NULL and there is no default on either.
    stmts.append("""insert into "MusicalStyles" ("Name","Description","DateAdded")
                    values ('Disco',
                            'Four-on-the-floor 1970s club music, typically 127-145 BPM — '
                            'the records waacking and the hustle were built on.',
                            now());""")
stmts.append("""create temp table _disco on commit drop as
                select "Id" from "MusicalStyles" where lower("Name")='disco';""")
if retag_ids:
    ids = ",".join(str(i) for i in retag_ids)
    stmts.append(f'delete from "DanceMusicalStyles" where "DanceId" in ({ids});')
    stmts.append(f'insert into "DanceMusicalStyles" ("DanceId","MusicalStyleId") '
                 f'select d, (select "Id" from _disco) from unnest(array[{ids}]) as d;')
for did, name, slug, desc in rename_plan:
    stmts.append(f'update "Dances" set "Name"={q(name)}, "Slug"={q(slug)}, '
                 f'"Description"={q(desc)} where "Id"={did};')
stmts.append("commit;")
psql("\n".join(stmts), fetch=False)

print(f"\napplied: {len(to_delete)} deletions, {len(retag_ids)} retags, "
      f"{len(rename_plan)} renames")
print("""
Remember: waacking.json links the renamed dance by slug. Update its danceSlug in the same
commit, then re-run scripts/validate_roadmaps.py.
""")
