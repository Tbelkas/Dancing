"""
seed_tutting_foundations.py [apply]

Seed the Tutting vocabulary the catalog was missing, so the tutting roadmap has real moves
to point at.

Why this was needed: Tutting had three dances (`tutting`, `king-tut`, `finger-tutting`) and
ten videos, and eight of those ten videos hung off the single `tutting` dance. Every one of
them is a *beginner combo* tutorial. Authoring a roadmap against that catalog would have
produced the exact failure the Waacking path was rebuilt to fix — a tree that is really one
video's chapter list — because the catalog had no vocabulary in it at all: no angles, no
grid, no boxes, no tracing, no hinges, no digits.

The vocabulary below is the intersection of five independent syllabi that agree with each
other:
  - Dance Djedi Academy's "Tutting I" course      (King Tut -> Box Tut -> Grid Tuts)
  - Mr. Wiggles' "The Menu 3: Learn Tutting" DVD  (basic tut positions -> box tuts -> combos)
  - The Tutting Institution's course ladder       (grids & body geometry -> leg tutting ->
                                                   advanced grids; fingers as its own track)
  - JayFunk's "Tutorial Tuesdays" series          (basics -> tracing -> hinges/isolation
                                                   points -> digits -> tunneling -> freestyle)
  - Pnut / StatusSilver's finger-tutting tiers    (Finger Tuts -> Digits -> Monstas)

Every video below was resolved back to YouTube and checked by description and chapter list,
not by title alone — the mistake that put a tutting choreo demo on a Waacking step. Durations
and view counts are the real ones as of seeding.

Sliced entries carry StartTime/EndTime with the FULL video duration in DurationSeconds, which
is the convention the rest of the catalog already uses (see dance `mc-rock` et al). Three
videos are sliced because their chapters teach genuinely separate concepts:
  5FX5H72B71k  Pnut     -> Finger Tuts / Digits / Monstas
  A4viOzllZNM  JayFunk  -> Isolation Points / Hinges
  2UkfqGko9tw  Raphael  -> Crumbling / Folds
Slicing rather than pinning one dance to three steps keeps progress per-step, since learned
state is stored per *dance*.

Idempotent: skips any dance whose slug already exists in the Tutting style, and any video
whose YouTube id is already attached to the dance it would be added to.

Dry-run unless 'apply'.
"""
import json
import os
import re
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

STYLE_ID = 22   # Tutting
MUSIC_ID = 3    # Hip-Hop — matches the three existing Tutting dances. Tutting is really a
                # funk/popping style, but there is still no Funk musical style (the same gap
                # noted when Disco was added for Waacking); don't invent one as a side effect
                # of seeding.

# (name, difficulty, description, [(ytid, full_duration, views, title, start, end), ...])
# start/end of 0 means the whole video.
DANCES = [
    # ---------------------------------------------------------------- popping foundation
    ("The Hit", 1,
     "Tutting's actual mechanic: pop into a position, hold it, then snap to the next one. "
     "The shapes are only half the dance — what makes it read as tutting rather than posing "
     "is that each position arrives on a hit and nothing drifts between them.",
     [("IAEV8KrZ4hY", 109, 16460, "How to Do Popping", 0, 0),
      ("ycPeDQUKjq4", 522, 13567, "Popping Basics for Tutting", 0, 0)]),

    ("Right Angles", 1,
     "The 90-degree angle is the single basic unit of the style. Elbows, wrists and "
     "shoulders held square, lines kept clean and parallel to the floor or straight up. "
     "Everything else in tutting is built by stacking these.",
     [("BVLh5Xiuioo", 198, 375496, "Tutting Concepts — Lines and Angles", 0, 0),
      ("wJdGN1gviko", 143, 2802, "Right Angles", 0, 0)]),

    ("Tutting Stretches", 1,
     "Wrists, forearms and finger joints, before every session. Tutting holds the hands at "
     "the end of their range for minutes at a time, and the range is what limits how clean "
     "an angle you can actually make.",
     [("nXnfZ0WjvOg", 55, 59672, "Hand Stretches for Tutting", 0, 0),
      ("iEcQPvvrfNM", 443, 1907, "Arm and Hand Stretches", 0, 0),
      ("dz3axgdqaIA", 81, 573, "Stretching Tips — Three Levels", 0, 0)]),

    ("Wrist Rolls", 1,
     "Rolling the wrist through its range while the forearm stays fixed. The joint that "
     "connects one angle to the next, and the cheapest way to make a flat shape look "
     "three-dimensional.",
     [("wegRpQ-V4fM", 74, 227, "What Are Wrist Rolls", 0, 0)]),

    ("Fixed Points", 2,
     "Pick a point in space — a knuckle, an elbow, a fingertip — and refuse to let it move "
     "while everything else rotates around it. The concept that turns a sequence of poses "
     "into an illusion, and the one most often skipped.",
     [("B0pQQysjOZA", 200, 483, "Fixed Points", 0, 0),
      ("vOzWGnvtyVk", 653, 6277, "Fixed Point Technique", 0, 0)]),

    # ---------------------------------------------------------------- body geometry (module)
    ("Four Body Points", 1,
     "Chin, chest, waist, shoulder — the reference points on your own body that arms travel "
     "between. Tutting is learnable rather than mimicry precisely because the targets are "
     "fixed and they are all on you.",
     [("QISey0UTy7c", 134, 355, "Four Body Points", 0, 0)]),

    ("The Four Square", 1,
     "Two forearms and two upper arms making four right angles in front of the chest. The "
     "first real tutting position and the one every later shape is a deviation from.",
     [("_IjKj2kteSY", 205, 7609, "The Four Square", 0, 0),
      ("rX_Unv9M0HA", 316, 6655, "The Four Squares for Beginners", 0, 0),
      ("OO3Z0ILaONA", 239, 490, "Four Square Combo Breakdown", 0, 0)]),

    ("The Grid", 2,
     "Expanding the four square up and down into levels, so the arms have a whole lattice of "
     "positions to hit instead of one plane. Taught as \"the holy grid\" — the map the rest "
     "of the vocabulary is drawn on.",
     [("bqGEzcFYpJw", 181, 4457, "Levels and the Grid", 0, 0)]),

    ("Box Tuts", 1,
     "Closing the arms into an actual box or rectangle, with the hands completing the shape. "
     "The move most people picture when they hear tutting, and the second thing every "
     "syllabus teaches after the King Tut.",
     [("yDIL5pNT3KQ", 162, 922, "Boxes", 0, 0),
      ("c47gWAwQtgY", 92, 928, "The Box Concept", 0, 0)]),

    ("Squaring the Boxes", 2,
     "Keeping a box genuinely square as it travels and rotates, instead of letting it "
     "collapse into a parallelogram the moment the arms move. Where clean tutting separates "
     "from approximate tutting.",
     [("lnK2pKtyBG0", 173, 482, "Squaring the Boxes", 0, 0)]),

    ("The Magic Box", 3,
     "A box that appears to stay fixed in space while the arms reassemble it around a "
     "different pair of limbs. Fixed points and boxes applied together.",
     [("3WThD9uy4AY", 160, 338, "The Magic Box", 0, 0)]),

    ("Advanced Four Square", 3,
     "The four square taken off the front plane — rotated, inverted and stacked behind and "
     "above the body once the basic version is automatic.",
     [("5Zk9zvEt02U", 163, 3037, "Advanced Four Square", 0, 0)]),

    # ---------------------------------------------------------------- joining the shapes
    ("Tutting Transitions", 2,
     "Getting from one position to the next without a visible scramble. The positions are the "
     "easy part; a path between them that stays on the grid is the actual craft.",
     [("fk7mA7BgnLU", 115, 7161, "How to Transition", 0, 0)]),

    ("Tracing", 2,
     "One hand follows the edge of the other arm, or of an imaginary shape held in the air. "
     "The concept that gives a phrase continuity, and the one JayFunk teaches second — "
     "before any combo — because everything else hangs off it.",
     [("r_7zXbpBf2U", 700, 143003, "Tracing", 0, 0),
      ("l85Mc7hALw4", 166, 3711, "Corners and Tracing", 0, 0),
      ("s62WZrPeLV4", 135, 373, "Tracing Breakdown", 0, 0)]),

    ("Isolation Points", 2,
     "Holding one joint absolutely still as the reference the rest of the movement is read "
     "against. Related to fixed points but applied inside a moving phrase rather than to a "
     "single shape.",
     [("A4viOzllZNM", 832, 48316, "Isolation Points", 45, 122)]),

    ("Hinges", 2,
     "Treating a joint as a hinge with one axis, so a limb folds flat and opens flat instead "
     "of swinging. What makes tutting look mechanical rather than merely angular.",
     [("A4viOzllZNM", 832, 48316, "Hinges", 122, 305),
      ("bb-ohIks-hM", 153, 215, "Hinging Breakdown", 0, 0)]),

    ("Folds and Unfolds", 2,
     "Collapsing a shape into itself and opening it back out along the same path. The cheapest "
     "way to get out of a position you have painted yourself into.",
     [("-tsf1UzJKLw", 186, 209, "Unfolds Breakdown", 0, 0),
      ("2UkfqGko9tw", 525, 1080, "Folds", 281, 385)]),

    ("Crumbling", 3,
     "Letting a shape fall apart joint by joint rather than all at once, so the exit from a "
     "position is itself a move. Taught as a fix for freezing up mid-phrase.",
     [("2UkfqGko9tw", 525, 1080, "Crumbling", 158, 281)]),

    # ---------------------------------------------------------------- off the flat plane
    ("3D Space", 3,
     "Building shapes that have depth away from the body instead of living on one flat pane "
     "in front of the chest. Often taught as a Rubik's-cube idea: the shape has a back and "
     "two sides, not just a face.",
     [("XZR8h_0rUR8", 252, 453, "3D Space", 0, 0),
      ("751f7MqhXB4", 70, 3026, "3D Tutting", 0, 0)]),

    ("Back Tuts", 3,
     "Shapes made behind the torso, where you cannot see your own hands and have to work "
     "entirely off the body points. Adds a whole second stage to the grid.",
     [("wSn9tUNCv4Y", 139, 175, "Back Tuts", 0, 0)]),

    ("Floor Tuts", 3,
     "Taking the grid down to the ground, using the floor itself as one of the fixed planes. "
     "The lower-body half of the style that arm-only tutters never build.",
     [("h8BPawC_iXk", 132, 313, "Floor Tuts", 0, 0)]),

    # ---------------------------------------------------------------- making it dance
    ("Tutting Patterns", 2,
     "A stock of ready-made shapes and short sequences to draw on, so a freestyle is a choice "
     "between known patterns rather than an attempt to invent geometry in real time.",
     [("FiT3L6q5gr8", 371, 53724, "50 Tutting Patterns", 0, 0)]),

    ("Tutting Combo", 2,
     "A full routine stringing angles, boxes and transitions into one phrase — the first "
     "thing on the path that looks like dancing rather than drilling.",
     [("NTpbV--zJYU", 1464, 6491, "Beginner to Advanced Combo", 0, 0),
      ("5QkCBJ1GJtc", 371, 2082762, "Basics of Tutting and a Combo", 0, 0)]),

    ("Tutting Musicality", 3,
     "Putting the hits where the record puts them. Tutting is danced to a beat, and a "
     "technically clean phrase landing off the music reads as worse than a rough one landing "
     "on it.",
     [("WTS1f1zcf2A", 836, 514144, "Tutting to Music", 0, 0),
      ("lQgGOEcs6Is", 963, 1172740, "Combo with Music", 0, 0)]),

    ("Freestyle Tutting", 3,
     "Improvising shapes to a record with no combo in mind. The point of the whole style, and "
     "the part that never arrives on its own from learning routines.",
     [("_WEYSsmAg6A", 214, 32048, "How to Freestyle — Part I", 0, 0),
      ("SJpdilUrnG0", 288, 90406, "How to Freestyle — Part II", 0, 0),
      ("onJahzd74_E", 395, 19591, "How to Freestyle — Part III", 0, 0)]),

    # ---------------------------------------------------------------- fingers (module)
    ("Finger Tuts", 1,
     "The beginner tier of finger tutting: simple right-angle shapes made with the fingers of "
     "both hands, held still enough to read.",
     [("5FX5H72B71k", 423, 6017588, "Finger Tuts", 49, 120)]),

    ("Digits", 2,
     "Interlocking the fingers of both hands into a shape and rotating it as one unit. The "
     "middle tier, and the one that makes finger tutting look like a mechanism.",
     [("5FX5H72B71k", 423, 6017588, "Digits", 120, 199),
      ("y2H95jnZf0Y", 133, 96, "The Basic Digit", 0, 0),
      ("NIKS_Mop1lw", 769, 22501, "Digit Concept — Whips", 0, 0)]),

    ("Monstas", 3,
     "The advanced tier: compound digits that fold several shapes through each other, at the "
     "limit of what most hands will physically do.",
     [("5FX5H72B71k", 423, 6017588, "Monstas", 199, 423)]),

    ("Finger Stacking", 2,
     "Layering the fingers of both hands into a single stacked column, then peeling them "
     "apart in order. Builds the finger independence the harder digits need.",
     [("esysjy9XKn8", 559, 3559, "Finger Stacking", 0, 0)]),

    ("Tunneling", 3,
     "Passing one hand through the gap made by the other without breaking either shape. The "
     "finger-scale version of tracing.",
     [("8vpUHRvPn5w", 948, 21608, "Tunneling", 0, 0)]),

    ("Finger Tutting Combo", 3,
     "A full finger-tutting phrase using the digits, tunnels and traces together, at the "
     "speed they are meant to be done.",
     [("fP-ERh8RXFo", 995, 61579, "Finger Tutting Combo", 0, 0)]),
]

# Extra videos onto dances that already exist. Mr Wiggles' King Tut lesson is the most
# authoritative footage of the origin move anywhere on YouTube and belongs on the existing
# king-tut dance rather than on a duplicate; the three finger-tutting tutorials go onto the
# existing finger-tutting dance, whose only video is a Pnut performance clip.
EXTRA_VIDEOS = {
    "king-tut": [
        ("JWZY0ZBL8Sw", 186, 123790, "King Tut — Cleaner Angles", 0, 0),
    ],
    "finger-tutting": [
        ("2gxZfHRvJ5w", 137, 2100684, "What Is Finger Tutting", 0, 0),
        ("n1YsuRczyyU", 307, 2143138, "Finger Tutting Tutorial", 0, 0),
        ("f8MtG1ErtwY", 199, 433517, "Basic Finger Tutting", 0, 0),
    ],
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
        print(f"      {ytid:<12} {dur:>4}s {views:>9,} views  {title[:44]}{span}")
if skipped:
    print(f"\n  already present, skipped: {', '.join(skipped)}")

print("\n=== extra videos on existing dances ===")
extra_plan = []
for sl, vids in EXTRA_VIDEOS.items():
    did = existing.get(sl)
    if did is None:
        print(f"  ! {sl}: not a Tutting dance, skipping")
        continue
    have = {r[0] for r in psql(f'select "VideoId" from "Videos" where "DanceId"={did};')}
    for ytid, dur, views, title, st, en in vids:
        if ytid in have:
            print(f"  = {sl}: {ytid} already attached")
            continue
        extra_plan.append((did, sl, ytid, dur, views, title, st, en))
        print(f"  + {sl} (dance {did}) <- {ytid} {dur}s  {title[:44]}")

if not APPLY:
    print("\n(dry-run; pass 'apply' to write)")
    raise SystemExit(0)

for name, sl, diff, desc, vids in new_dances:
    # The video rows have to be cross-joined onto the inserted dance: a VALUES list is
    # its own scope and cannot see the `d` CTE.
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

print(f"\napplied: {len(new_dances)} dances, {len(new_videos) + len(extra_plan)} videos")
print("""
Follow-ups:
  - Run scripts/validate_roadmaps.py to confirm every tutting.json step resolves.
  - Tutting is tagged Hip-Hop for want of a Funk musical style. Popping, locking and tutting
    all want one; adding it is a taxonomy decision, not a seeding side effect.
  - The long class videos (JayFunk's Tutorial Tuesdays, Elliott's ULTIMATE tutorial) are
    good candidates for the find-chips flow so later steps can pin a section.
""")
