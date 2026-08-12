"""
seed_vogue_foundations.py [apply]

Seed the Vogue vocabulary the catalog was missing, so the vogue roadmap has real moves and
real context to point at.

Why this was needed: Vogue had 9 dances and 9 videos. Five of them were the Five Elements of
Vogue Fem, which is a good start — but the catalog had *nothing* for the other two styles
(Old Way beyond one bootcamp video, New Way not at all), and nothing at all about ballroom
itself: no houses, no balls, no categories, no realness, no herstory. Vogue is not a neutral
movement vocabulary that happens to have a backstory. It was made by Black and Latino
LGBTQ+ people in Harlem's ball scene, the moves are scored in categories at balls, and a
path that taught the arms without the ballroom would be teaching the wrong thing.

Structure the vocabulary follows — the three styles, which every source agrees on:
  - Old Way (pre-1990, originally "Pop, Dip and Spin"): lines, symmetry, precision,
    controlled transitions, face framing; competitively, pinning an opponent.
  - New Way (c. 1990): arms control (illusions with wrists and arms, borrowing locking and
    tutting), clicks (joint contortions), boxes, flexibility.
  - Vogue Fem (c. 1995): the Five Elements — hand performance, catwalk, duckwalk, spins and
    dips, floor performance — performed anywhere between Dramatics and Soft.

Sources cross-checked against each other: the House of B. Poderosa "Ballroom Basics" six-part
series (herstory / runway / five elements / vogue femme / old way / new way), NYC Parks'
six-part "Learn to Vogue", Gravity Jacobs' "Five Elements of Vogue", Ronald Murray's TEDx
"Ballroom Culture: the Language of Vogue", and Koppi Mizrahi's Vogue Fem basics.

Every video below was resolved back to YouTube and checked by description and chapter list,
not by title alone. Durations and view counts are the real ones as of seeding.

Sliced entries carry StartTime/EndTime with the FULL video duration in DurationSeconds, the
convention the rest of the catalog uses. Four videos are sliced because their chapters teach
genuinely separate things, and slicing into their own dances keeps learned state per-step
(progress is stored per dance):
  cL5uGHqhnYw  Ballroom Basics 1 -> herstory / realness / houses+balls / categories
  zYsz9s8Pv3k  mary_dusa        -> new way lines / new way boxes
  eBCs9n0p93E  Old Way Bootcamp -> switches / pose to the beat / slides
  tqUEcEsA3gQ  Five Elements 4  -> fan kick / leg circles / knee moves

Also renames dance 1822 `death-drop`. "Death drop" is an outsider/media term; the ballroom
scene calls it a dip. The catalog already contains a video literally titled "Don't Call It
Death Drop", so carrying the wrong name on a dance was inconsistent with our own source.

Idempotent: skips any dance whose slug already exists in the Vogue style, any video whose
YouTube id is already attached to the dance it would be added to, and the rename if it has
already happened.

Dry-run unless 'apply'.
"""
import json
import os
import re
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

STYLE_ID = 16   # Vogue
MUSIC_ID = 6    # Electronic / EDM — matches eight of the nine existing Vogue dances. Ballroom
                # runs on its own house-derived sound (the "ha" crash); there is no Ballroom
                # or House musical style, and adding one is a taxonomy call, not a seeding
                # side effect.

# (name, difficulty, description, [(ytid, full_duration, views, title, start, end), ...])
# start/end of 0 means the whole video.
DANCES = [
    # ------------------------------------------------------------------ the culture
    ("What Vogue Is", 1,
     "Vogue is a competitive dance from the Harlem ball scene, built by Black and Latino "
     "LGBTQ+ people from the 1960s onward. It is judged, it is walked in categories, and it "
     "belongs to a community — start here before any movement.",
     [("c2uAf7aLX24", 130, 19812, "What Is Vogue", 0, 0),
      ("XJ6fqQX_e9U", 228, 1342567, "How the LGBTQ Community Created Voguing", 0, 0),
      ("vt9AwsS0_6A", 210, 21521, "Voguing History and Legendary Voguers", 0, 0)]),

    ("Ballroom Herstory", 1,
     "The ball scene goes back to 19th-century drag balls and was reshaped in 1970 when "
     "Crystal LaBeija, refusing the racism of the pageant circuit, founded the House of "
     "LaBeija. Vogue came out of that room, not out of a music video.",
     [("zjfzvo-zRPo", 957, 290000, "Ballroom History", 0, 0),
      ("vbaCmDvrFxw", 338, 253628, "Crystal LaBeija", 0, 0),
      ("cL5uGHqhnYw", 611, 118, "History of Ballroom", 133, 178)]),

    ("Houses and Balls", 1,
     "A house is a chosen family with a mother or father, not a building. A ball is where "
     "houses compete. Both exist because the people who built them were thrown out of "
     "somewhere else, and the structure is the point.",
     [("cL5uGHqhnYw", 611, 118, "The House and How a Ball Works", 277, 437),
      ("8ej86oHMJ8o", 314, 190476, "Inside the House of Xtravaganza", 0, 0),
      ("QS5j7PCSdtg", 806, 179637, "House and Ballroom", 192, 413)]),

    ("Ballroom Categories", 1,
     "You do not simply vogue at a ball — you walk a category. Face, body, runway, realness, "
     "and the vogue categories each have their own criteria, and knowing which one you are "
     "in is half of doing well in it.",
     [("cL5uGHqhnYw", 611, 118, "Categories", 437, 486)]),

    ("Realness", 2,
     "A category judged on passing convincingly as something — executive, schoolboy, femme "
     "queen. It is the part of ballroom that is least like a dance and most like the reason "
     "ballroom exists, and it is worth understanding before you walk anything.",
     [("cL5uGHqhnYw", 611, 118, "Realness", 178, 277)]),

    ("Runway", 2,
     "The walk itself, judged as its own category: posture, timing, and command of the floor. "
     "European and American runway are scored differently, and both are older than the vogue "
     "categories.",
     [("fBCgb7A466o", 553, 833, "Runway", 0, 0)]),

    # ------------------------------------------------------------------ common vocabulary
    ("Vogue Arm Lines", 1,
     "The arms are the through-line of all three styles: long lines, clean shapes, and detail "
     "in the wrists and fingers. Drill them before choosing a style, because every style "
     "assumes them.",
     [("h2U3i30ZCf4", 290, 43413, "Beginner Arm Movements", 0, 0)]),

    ("Vogue Poses", 1,
     "The magazine poses the dance is named after — struck cleanly, held, and framed around "
     "the face. Vogue began as posing to a beat, and the pose is still what the arms are "
     "travelling between.",
     [("wnSMHrmYqVs", 388, 25154, "Beginner Poses", 0, 0)]),

    ("Vogue Musicality", 2,
     "Ballroom tracks are built on a house beat with a crash — the \"ha\" — that everything "
     "lands on. Counting a vogue track like an ordinary eight-count pop song is the most "
     "common beginner mistake.",
     [("y3Uk_ZxiLV0", 339, 48689, "Spoken Count Tutorial", 0, 0)]),

    # ------------------------------------------------------------------ old way
    ("Pop, Dip and Spin", 2,
     "What Old Way was actually called before anyone said \"vogue\": a pose popped to the "
     "beat, a dip, and a spin. The form seen in Paris Is Burning, and the root of everything "
     "that followed.",
     [("iVmvapZhoJg", 707, 9153, "Pop Dip and Spin", 0, 0)]),

    ("Old Way Switches", 2,
     "Switching the arms between front, side, up and down positions without losing the line "
     "or the symmetry. The basic drill of Old Way and the one that exposes sloppy shoulders.",
     [("eBCs9n0p93E", 237, 0, "Front Switch and Side Switch", 48, 108)]),

    ("Pose to the Beat", 1,
     "Landing each pose exactly on the beat rather than flowing through it. Old Way is popped, "
     "not swum — this is the difference between voguing and posing prettily.",
     [("eBCs9n0p93E", 237, 0, "Pose to the Beat", 108, 132)]),

    ("Old Way Slides", 2,
     "Travelling one arm along a fixed line into the next position — front slide and up slide. "
     "How Old Way gets between poses without breaking the geometry.",
     [("eBCs9n0p93E", 237, 0, "Front Slide and Up Slide", 132, 192)]),

    # ------------------------------------------------------------------ new way
    ("New Way Vogue", 2,
     "The style that emerged around 1990: rigid arms, precise angles, and illusions built out "
     "of flexibility. Where Old Way is symmetric and popped, New Way is continuous and "
     "controlled.",
     [("J39Drfl1dM8", 763, 212, "New Way", 0, 0)]),

    ("Arms Control", 2,
     "The signature New Way skill — creating illusions with the wrists and arms, borrowing "
     "openly from locking and tutting. The arms appear to move through each other rather than "
     "around each other.",
     [("JqnXibZ8QKM", 679, 803, "Arms Control", 0, 0),
      ("gbtpL86VLHE", 33, 206598, "Arms Control Demonstration", 0, 0)]),

    ("New Way Lines", 2,
     "Drilling straight, fully extended lines through the arms as the base that every New Way "
     "illusion is bent out of. Boring, and the reason good New Way looks effortless.",
     [("zYsz9s8Pv3k", 893, 41186, "Lines Exercises", 331, 457)]),

    ("New Way Boxes", 3,
     "Right-angled boxes drawn with the forearms and passed around the body — the tutting "
     "borrowing at its clearest, and the shape most New Way combinations are assembled from.",
     [("zYsz9s8Pv3k", 893, 41186, "Boxes Exercises", 457, 678)]),

    # ------------------------------------------------------------------ vogue fem
    ("Vogue Fem", 2,
     "The style that emerged around 1995 emphasising exaggerated femininity, and the one most "
     "people mean by voguing today. Performed anywhere on a spectrum from Dramatics to Soft, "
     "and built from the Five Elements.",
     [("vySNZKVK2xY", 118, 559354, "Vogue Fem Basics", 0, 0),
      ("VDMFYe7UOtQ", 672, 209, "Vogue Femme", 0, 0)]),

    ("Vogue Fem Dramatics", 3,
     "The high-energy end of Vogue Fem: stunts, speed and tricks, with the dip as the "
     "punctuation. The other end is Soft — graceful, flowing, and judged just as hard.",
     [("D-s3gsiKpDM", 673, 26135, "Dramatics", 0, 0),
      ("kAx5xUA_PEo", 203, 287973, "The Dip in Dramatics", 0, 0)]),

    ("Fan Kick", 2,
     "A straight leg swept in a wide arc from the floor — the most recognisable single move in "
     "floor performance, and usually the first one taught.",
     [("tqUEcEsA3gQ", 584, 26481, "Fan Kick", 79, 140)]),

    ("Leg Circles", 2,
     "Continuous circles traced with one leg while the upper body keeps performing. What keeps "
     "floor performance moving between the bigger shapes.",
     [("tqUEcEsA3gQ", 584, 26481, "Leg Circles", 140, 200)]),

    ("Knee Moves", 2,
     "Working on and around the knees on the floor — drops, slides and turns. Wear pads; this "
     "is the element that ends careers when it is drilled on a hard floor.",
     [("tqUEcEsA3gQ", 584, 26481, "Knee Moves", 200, 292)]),
]

# Extra videos onto dances that already exist. NYC Parks' and Gravity Jacobs' series both
# cover the Five Elements better than the single clips already attached, and the House of
# B. Poderosa Old Way episode belongs on the existing old-way-vogue dance.
EXTRA_VIDEOS = {
    "catwalk": [("dLWhfvs-t-k", 241, 63589, "Cat Walk", 0, 0)],
    "duckwalk": [("ZJzwq0Aj_V0", 203, 66758, "Duck Walk", 0, 0),
                 ("qzdXauUVYoI", 224, 46021, "How to Duckwalk", 0, 0)],
    "floor-performance": [("1E3xsNHT-Hc", 150, 16101, "Floor Performance", 0, 0)],
    "hand-performance": [("Mp5LFK_BYNI", 945, 83108, "Hands Performance", 0, 0),
                         ("ln8msNBsWk0", 60, 331295, "Figure Eights and Rolls", 0, 0)],
    "spin-and-dip": [("LwpLdzz0muI", 129, 5853, "Basic Spin and Dip", 0, 0)],
    "old-way-vogue": [("U_R3mOnIVLg", 753, 313, "Old Way", 0, 0)],
}

# "Death drop" is a media term the ballroom scene rejects; the move is a dip. Renaming rather
# than deleting: the video behind it is a real tutorial, it is just filed under the wrong name.
RENAMES = [
    (1822, "death-drop", "Dramatic Dip", "dramatic-dip"),
]


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


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "dance"


existing = {s: int(i) for i, s in psql(
    f'select d."Id", d."Slug" from "Dances" d join "DanceStyles" ds on ds."DanceId"=d."Id" '
    f'where ds."StyleId"={STYLE_ID};')}

new_dances, new_videos, skipped = [], [], []
for name, diff, desc, vids in DANCES:
    sl = slugify(name)
    if sl in existing:
        skipped.append(sl)
        continue
    new_dances.append((name, sl, diff, desc, vids))
    new_videos.extend(v[0] for v in vids)

print(f"=== {len(new_dances)} new dances, {len(new_videos)} new videos ===")
for name, sl, diff, desc, vids in new_dances:
    print(f"  + {name:24} diff {diff}  slug {sl}")
    for ytid, dur, views, title, st, en in vids:
        span = f"  [{st}-{en}]" if en else ""
        print(f"      {ytid:<12} {dur:>4}s {views:>9,} views  {title[:42]}{span}")
if skipped:
    print(f"\n  already present, skipped: {', '.join(skipped)}")

print("\n=== extra videos on existing dances ===")
extra_plan = []
for sl, vids in EXTRA_VIDEOS.items():
    did = existing.get(sl)
    if did is None:
        print(f"  ! {sl}: not a Vogue dance, skipping")
        continue
    have = {r[0] for r in psql(f'select "VideoId" from "Videos" where "DanceId"={did};')}
    for ytid, dur, views, title, st, en in vids:
        if ytid in have:
            print(f"  = {sl}: {ytid} already attached")
            continue
        extra_plan.append((did, sl, ytid, dur, views, title, st, en))
        print(f"  + {sl} (dance {did}) <- {ytid} {dur}s  {title[:42]}")

print("\n=== renames ===")
rename_plan = []
for did, old_slug, new_name, new_slug in RENAMES:
    row = psql(f'select "Slug" from "Dances" where "Id"={did};')
    if not row:
        print(f"  ! dance {did} not found, skipping")
        continue
    if row[0][0] != old_slug:
        print(f"  = dance {did} is already '{row[0][0]}', skipping")
        continue
    rename_plan.append((did, old_slug, new_name, new_slug))
    print(f"  ~ dance {did}: '{old_slug}' -> '{new_slug}' ({new_name})")

if not APPLY:
    print("\n(dry-run; pass 'apply' to write)")
    raise SystemExit(0)

for name, sl, diff, desc, vids in new_dances:
    vals = ", ".join(
        f'({q(t)}, {q(y)}, {vw}, {dur}, {st}, {en})' for y, dur, vw, t, st, en in vids)
    sql = f"""begin;
with d as (
  insert into "Dances" ("Name","Slug","Description","DateAdded","Difficulty")
  values ({q(name)}, {q(sl)}, {q(desc)}, now(), {diff}) returning "Id"),
 s as (insert into "DanceStyles" ("DanceId","StyleId") select "Id",{STYLE_ID} from d returning 1),
 m as (insert into "DanceMusicalStyles" ("DanceId","MusicalStyleId") select "Id",{MUSIC_ID} from d returning 1),
 v as (insert into "Videos" ("Title","VideoId","Platform","VideoType","DateAdded","ViewCount","DurationSeconds","StartTime","EndTime","DanceId")
       select x.title, x.ytid, 'youtube', 'tutorial', now(), x.views, x.dur, x.st, x.en, d."Id"
       from d cross join (values {vals}) as x(title, ytid, views, dur, st, en)
       returning "Id","DanceId")
select "DanceId", count(*) from v group by 1;
commit;"""
    psql(sql, fetch=False)
    got = psql(f'select d."Id", (select count(*) from "Videos" v where v."DanceId"=d."Id") '
               f'from "Dances" d join "DanceStyles" ds on ds."DanceId"=d."Id" '
               f'where ds."StyleId"={STYLE_ID} and d."Slug"={q(sl)};')
    print(f"  + {sl:28} dance {got[0][0]}, {got[0][1]} video(s)")

for did, sl, ytid, dur, views, title, st, en in extra_plan:
    psql(f'insert into "Videos" ("Title","VideoId","Platform","VideoType","DateAdded",'
         f'"ViewCount","DurationSeconds","StartTime","EndTime","DanceId") '
         f'values ({q(title)},{q(ytid)},\'youtube\',\'tutorial\', now(), {views}, {dur}, '
         f'{st}, {en}, {did});', fetch=False)
    print(f"  + {sl:28} <- {ytid}")

for did, old_slug, new_name, new_slug in rename_plan:
    psql(f'update "Dances" set "Name"={q(new_name)}, "Slug"={q(new_slug)} where "Id"={did};',
         fetch=False)
    print(f"  ~ {old_slug:28} -> {new_slug}")

print(f"\napplied: {len(new_dances)} dances, {len(new_videos) + len(extra_plan)} videos, "
      f"{len(rename_plan)} rename(s)")
print("""
Follow-ups:
  - Run scripts/validate_roadmaps.py to confirm every vogue.json step resolves.
  - Four dip dances still overlap: vogue-dip, dip-with-a-kick, spin-and-dip and the renamed
    dramatic-dip are four tutorials of one element. The roadmap uses spin-and-dip and
    dip-with-a-kick; merging the other two is a catalog cleanup worth doing deliberately
    (scripts/merge_variant_dances.py), not as part of a seed.
  - Old Way Bootcamp (eBCs9n0p93E) has no ViewCount on record; enrich_views.py will fill it.
  - Clicks, pinning and Soft have no good tutorial footage found — those steps are authored
    unlinked on purpose, which renders as "no video yet" rather than pointing somewhere wrong.
""")
