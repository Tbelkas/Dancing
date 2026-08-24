"""
split_stretch_routines.py [apply]

Separates follow-along stretch *routines* from stretch *positions* in the Stretching catalog.

Why: a stretch (Pigeon Pose, Front Splits) has one canonical demo, so one entry = one video
reads correctly. A routine ("15 min full body stretch") has no best version - the versions
differ by length and focus, not quality - so stacking several under one bucket name produced
a page of collapsed rows with nothing to choose between. Worse, the bucket names attract the
next seeding pass, so the piles grow.

Two things are fixed here:

1. "Balance & Stretch" (1323) is not a stretching routine at all. It is the 23:06-26:21
   section of a ballet class video (GWGPOHZazgY), sibling to Coupe & Tendu, Sous Sous,
   Releve on 1 Leg and three more - all of which sit in Classical / Ballet at the same
   difficulty. It was filed under Stretching on the word "Stretch" in its name, and a
   stretching seeding pass then hung four unrelated full-body routines off it. The ballet
   move goes back to Classical / Ballet keeping only its own segment.

2. The three multi-video Stretching entries (1323, 1711 "Dancer's Stretching Routine",
   1958 "Daily Full Body Stretch") are split so every routine is its own entry, named for
   what it is rather than for the bucket it landed in. Browse already shows "1 video - N min"
   per card, so length - the attribute people actually pick a routine on - becomes visible
   without opening anything.

Practice history follows the video: PracticeSessionItems rows carry VideoId, so each row
moves to the entry its video landed on. The four legacy rows with VideoId NULL predate that
column and stay on the entry they were logged against.

Idempotent: re-running after a successful apply is a no-op (it checks the videos' current
DanceId before moving them).
"""
import json, os, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")

PGHOST = "192.168.0.197"; PGUSER = "dance_user"; PGDB = "dancing"
STRETCHING, BALLET = 23, 4


def _prod_password():
    """Read the prod DB password from appsettings (gitignored) rather than hardcoding it.

    This repo is public: a literal here leaks the production database on every push.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = os.path.join(root, "DancePlatform.API", "appsettings.Development.json")
    for v in json.load(open(cfg, encoding="utf-8-sig")).get("ConnectionStrings", {}).values():
        if PGHOST in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p).get("Password", "")
    raise SystemExit(f"No prod ({PGHOST}) connection string in {cfg}")


PGPW = _prod_password()


def psql(sql):
    env = dict(os.environ); env["PGPASSWORD"] = PGPW
    p = subprocess.run(["psql", "-h", PGHOST, "-U", PGUSER, "-d", PGDB,
                        "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def slugify(name):
    """Mirror of Services/SlugGenerator.Slugify - lowercase, non-alphanumerics collapsed to '-'."""
    out, last_dash = [], True
    for c in name:
        if c.isascii() and c.isalnum():
            out.append(c.lower()); last_dash = False
        elif not last_dash:
            out.append('-'); last_dash = True
    return "".join(out).rstrip('-') or "dance"


def q(s):
    return "'" + s.replace("'", "''") + "'"


# (videoDbId, new dance name, description) - one new Stretching entry per routine.
# Difficulty 1 (Beginner) throughout, matching the routines already in the catalog.
NEW_ENTRIES = [
    # off "Balance & Stretch" (1323), where they never belonged
    (2101, "Stretch & Core Recovery",
     "Full-body recovery session pairing mobility work with core: no equipment, done at home."),
    (2106, "Daily Stretch Routine",
     "A full-body stretch to run daily - flexibility and mobility in one pass, no warm-up needed."),
    (2110, "Full Body Stretch",
     "Head-to-toe stretch for mobility and flexibility - the default session when nothing in "
     "particular is tight."),
    (2232, "Rest Day Stretch",
     "Short full-body stretch built for rest days: keeps mobility ticking over without loading "
     "anything."),
    # off "Dancer's Stretching Routine" (1711)
    (1715, "Dancer's Flexibility Routine",
     "Follow-along dancer's stretch for flexibility, working range of motion end to end."),
    (1716, "Dancer's At-Home Stretch",
     "A dancer's stretching routine for increased flexibility, floor-based and follow-along at home."),
    (1717, "Dancer's Full Body Stretch",
     "The long one: a full-body follow-along stretch routine for dancers, every major group covered."),
    # off "Daily Full Body Stretch" (1958)
    (2004, "Total Body Stretch",
     "Ten-minute total-body stretch - the short daily flexibility routine."),
]

# Video titles that were stored wrong. 2232 was seeded as "5 MIN FULL BODY STRETCH ..." but
# the upload is "DAY 7 Back to Basics - 15 MIN ..." and runs 960s - the wrong length is exactly
# the kind of thing that makes a routine unpickable.
VIDEO_TITLE_FIXES = [
    (2232, "DAY 7 Back to Basics - 15 MIN FULL BODY STRETCH For Rest Day, "
           "Improve Mobility & Flexibility"),
]

# Entries that keep one video and lose the bucket name that attracted the rest.
RENAMES = [
    (1711, "Dancer's Hips & Arabesque Stretch",
     "Full-body flexibility stretch for dancers, weighted towards open hips and the arabesque line."),
]

apply = "apply" in sys.argv[1:]
tag = "APPLY" if apply else "DRY-RUN"
print(f"=== split_stretch_routines [{tag}] ===\n")

# --- 1. Balance & Stretch back to Classical / Ballet ------------------------------------
style_now = psql(f'SELECT "StyleId" FROM "DanceStyles" WHERE "DanceId"=1323;')
print(f'1323 "Balance & Stretch" styles now: {[s[0] for s in style_now]} -> [{BALLET}] (Classical / Ballet)')

# --- 2. Report what moves ---------------------------------------------------------------
ids = ",".join(str(v) for v, _, _ in NEW_ENTRIES)
rows = psql(f'SELECT "Id","DanceId",left("Title",64),coalesce("DurationSeconds",0) '
            f'FROM "Videos" WHERE "Id" IN ({ids}) ORDER BY "DanceId","Id";')
current = {int(r[0]): int(r[1]) for r in rows}
meta = {int(r[0]): (r[2], int(r[3])) for r in rows}

print()
for vid, name, _ in NEW_ENTRIES:
    if vid not in meta:
        print(f"  ! video {vid} not found - skipping"); continue
    title, dur = meta[vid]
    mins = f"{round(dur / 60)} min" if dur else "?"
    print(f'  video {vid} (from dance {current[vid]}, {mins:>6}) -> new "{name}"')
    print(f'      {title}')

print()
for did, name, _ in RENAMES:
    old = psql(f'SELECT "Name" FROM "Dances" WHERE "Id"={did};')
    print(f'  rename {did}: "{old[0][0]}" -> "{name}"')

if not apply:
    print("\nDry run. Re-run with 'apply' to write.")
    raise SystemExit(0)

# --- 3. Write ----------------------------------------------------------------------------
sql = ["BEGIN;",
       f'UPDATE "DanceStyles" SET "StyleId"={BALLET} WHERE "DanceId"=1323 AND "StyleId"={STRETCHING};']

for vid, name, desc in NEW_ENTRIES:
    if vid not in current:
        continue
    slug = slugify(name)
    sql.append(f'''
WITH nd AS (
  INSERT INTO "Dances" ("Name","Slug","Description","Difficulty","DateAdded",
                        "AverageRating","RatingCount","FavoriteCount","LearnedCount")
  SELECT {q(name)}, {q(slug)}, {q(desc)}, 1, now(), 0, 0, 0, 0
  WHERE NOT EXISTS (SELECT 1 FROM "Dances" WHERE "Slug"={q(slug)})
  RETURNING "Id"
), ds AS (
  INSERT INTO "DanceStyles" ("DanceId","StyleId") SELECT "Id", {STRETCHING} FROM nd
), mv AS (
  UPDATE "Videos" SET "DanceId"=(SELECT "Id" FROM nd) WHERE "Id"={vid} AND EXISTS (SELECT 1 FROM nd)
)
UPDATE "PracticeSessionItems" SET "DanceId"=(SELECT "Id" FROM nd)
WHERE "VideoId"={vid} AND EXISTS (SELECT 1 FROM nd);'''.strip())

for did, name, desc in RENAMES:
    sql.append(f'UPDATE "Dances" SET "Name"={q(name)}, "Slug"={q(slugify(name))}, '
               f'"Description"={q(desc)} WHERE "Id"={did};')

for vid, title in VIDEO_TITLE_FIXES:
    sql.append(f'UPDATE "Videos" SET "Title"={q(title)} WHERE "Id"={vid};')

sql.append("COMMIT;")
psql("\n".join(sql))

# --- 4. Verify ---------------------------------------------------------------------------
print("\n=== after ===")
check = psql(f'''SELECT d."Id", d."Name", s."Name", count(v."Id")
FROM "Dances" d
JOIN "DanceStyles" ds ON ds."DanceId"=d."Id"
JOIN "Styles" s ON s."Id"=ds."StyleId"
LEFT JOIN "Videos" v ON v."DanceId"=d."Id"
WHERE ds."StyleId"={STRETCHING} OR d."Id"=1323
GROUP BY 1,2,3 ORDER BY count(v."Id") DESC, d."Name";''')
piles = [r for r in check if int(r[3]) > 1]
print(f"Stretching entries: {len([r for r in check if r[2] == 'Stretching'])}, "
      f"still holding more than one video: {len(piles)}")
for r in piles:
    print(f"  ! {r[0]} {r[1]} ({r[2]}) - {r[3]} videos")
print(f"1323 is now: " + ", ".join(f"{r[1]} / {r[2]} / {r[3]} video(s)" for r in check if r[0] == '1323'))
