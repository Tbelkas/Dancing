"""
seed_style_moves.py search [--styles A,B] [--per-move 2]   find tutorials (dry run)
seed_style_moves.py insert                                  insert them as PENDING
seed_style_moves.py promote [apply]                         take verified styles live
seed_style_moves.py status                                  where every style stands
seed_style_moves.py retry [apply]                           new candidates for stuck moves

Grow the catalogue into dance styles it lacks, from the authored move lists in
style_catalog.py.

THE PIPELINE, AND WHO DECIDES WHAT
----------------------------------
  1. search   - for every catalogue move not already in the database, ask YouTube for
                a tutorial. The move NAME is ours; YouTube only supplies the video.
                Candidates must name the move AND the style in their title (see gate()).
                Writes _proto/style_seed.json and touches nothing.
  2. insert   - writes exactly what the last search found: each move as a Dance with
                ReviewState='pending' (named explicitly - the column defaults to
                'approved'), its videos pending by the Videos default. Dances are NOT
                linked to their style yet; see "why styles are linked late".
  3. verify_intake.py apply, then promote_confirmed.py apply - the same transcript
                check every other intake batch goes through. Nothing here approves a
                video.
  4. promote  - a pending move that now has an approved video goes live: linked to its
                style and music tag, dance approved. A style that does not exist yet is
                created at this point, and only if MIN_LIVE of its moves are live -
                otherwise it waits. The style's "adopt" dances are moved into it at the
                same time.

WHY STYLES ARE LINKED LATE
--------------------------
StyleService counts a style's dances with DanceStyles.Count, pending or not, so a new
style linked to pending moves would appear in the style list with a count and an empty
page. Leaving pending moves unlinked means a style only exists once there is something
to see in it. promote() finds its moves again by name: a pending dance with no style
whose name is in the catalogue is one of ours.

Idempotent: search skips names already in the database (case/punctuation-insensitive,
pitfall 4), insert skips names already inserted, promote skips what is already live.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch          # noqa: E402
import video_gate as vg           # noqa: E402
from style_catalog import STYLES  # noqa: E402

OUT = os.path.join(ch.ROOT, "_proto", "style_seed.json")

MIN_DUR, MAX_DUR = 45, 2400
MIN_VIEWS = 1000
SEARCH_N = 10
MIN_LIVE = 4        # moves (own + adopted) a NEW style needs before it is created

NOT_TEACHING = re.compile(
    r"\b(official (video|audio)|music video|lyrics|remix|live (at|from)|concert"
    r"|full performance|reaction|vlog|feat\.?|ft\.|mixtape|compilation|album"
    r"|visualizer|battle|showcase|recital|competition|championship|judge)\b", re.I)
TEACHING = re.compile(
    r"\b(tutorial|how to|learn|lesson|breakdown|step by step|basics|beginners?"
    r"|technique|drill|explained|class|workshop|tips|exercises?|training|guide"
    r"|method|course|teach(es|ing)?)\b", re.I)
# A lesson on PLAYING the music. Dance names are also tune types - a reel, a slip jig
# and a hornpipe are all things a fiddle teacher teaches - so "Irish Reel lesson" is
# as likely to be about bowing as about feet.
INSTRUMENT = re.compile(
    r"\b(guitar|fiddle|violin|bowing|piano|chords?|tin whistle|whistle|flute|banjo"
    r"|accordion|mandolin|ukulele|bodhran|drums?|sheet music|playing|play)\b", re.I)


def q(s):
    return (s or "").replace("'", "''")


def flat(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def name_key(s):
    """Dedupe key for a dance name: "The Cha Cha Slide" == "Cha Cha Slide" and
    "Grapevines" == "Grapevine". flat() alone missed both, and the first became a
    duplicate entry in the dry run."""
    n = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
    n = re.sub(r"^the\s+", "", n.strip().lower())
    k = flat(n)
    return k[:-1] if k.endswith("s") and len(k) > 4 else k


def slugify(n):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", n.lower())).strip("-")


def rows(sql):
    return json.loads(ch.psql(
        f"select coalesce(json_agg(row_to_json(t)), '[]'::json) from ({sql}) t;"
    ).strip() or "[]")


def move_key_tokens(name, style):
    """The tokens of a move name that identify the MOVE, not the style.

    "Belly Dance Camel" -> {camel}. If nothing is left ("Popping" itself), the name
    is all style, and the whole token set is the key.
    """
    style_t = vg.toks(" ".join(STYLES[style]["words"]) + " " + style)
    t = vg.toks(name)
    return (t - style_t) or t


def gate(c, name, style):
    """Is this search result a tutorial of this move in this style? -> (ok, score, why)"""
    # Fold accents first: "Forró" and "Bênção" in a title must meet "Forro" and
    # "Bencao" in the catalogue, and flat()/toks() simply drop non-ASCII letters.
    title = unicodedata.normalize("NFKD", c["title"]).encode("ascii", "ignore").decode()
    tt = vg.toks(title)
    ft = flat(title)
    key = move_key_tokens(name, style)
    # The move: every distinctive token, or the whole name written without spaces
    # ("Twist-o-Flex" vs "twistoflex").
    if not key:
        # A name toks() cannot see at all - "Au" is under its three-letter floor - and
        # an empty key is a subset of every title. It picked "How to Do the Bancao"
        # and an aerial tutorial for Au. Such a name must appear as a whole word.
        names_move = bool(re.search(rf"\b{re.escape(name)}\b", title, re.I))
    else:
        names_move = key <= tt or flat(name) in ft or \
            all(flat(k) in ft for k in key)
    if not names_move:
        return False, 0, "move-not-in-title"
    # The style must be named by a word OTHER than the move's own. "The Lock" is in
    # Locking, and without this "Learn Lock Picking" passes both tests on one word.
    names_style = any(re.search(rf"\b{re.escape(w)}", title, re.I)
                      for w in STYLES[style]["words"]
                      if not (vg.toks(w) & key)) or \
        (flat(style) in ft and not (vg.toks(style) & key))
    if not names_style:
        return False, 0, "style-not-in-title"
    if not (MIN_DUR <= c["dur"] <= MAX_DUR):
        return False, 0, "duration"
    if c["views"] < MIN_VIEWS:
        return False, 0, "reach"
    if INSTRUMENT.search(title):
        return False, 0, "music-lesson"
    # An instructional word is REQUIRED. "Shahrzad dances Taqsim" names move and style
    # and is a performance; the title is all we have at this stage.
    if not TEACHING.search(title):
        return False, 0, "not-instructional"
    score = 0.85
    if NOT_TEACHING.search(title):
        score -= 0.4
    if c["views"] >= 50_000:
        score += 0.1
    if c["dur"] < 90:
        score -= 0.1
    if score < 0.6:
        return False, score, "not-instructional"
    return True, round(score, 2), ""


def search(query, n=SEARCH_N):
    p = subprocess.run(
        ["yt-dlp", f"ytsearch{n}:{query}", "--flat-playlist", "--no-warnings", "-q",
         "--print", "%(id)s\t%(duration)s\t%(view_count)s\t%(channel_id)s\t%(title)s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=240)
    out = []
    for line in (p.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        vid, dur, views, chid, title = parts
        try:
            out.append({"ytid": vid, "dur": int(float(dur or 0)),
                        "views": int(float(views or 0)), "channel": chid,
                        "title": title})
        except ValueError:
            continue
    return out


def existing():
    """name-key -> (id, style names, state) for every dance in the database."""
    got = rows('''select d."Id" as id, d."Name" as name, d."ReviewState" as state,
                  coalesce((select string_agg(s."Name", ', ') from "DanceStyles" ds
                            join "Styles" s on s."Id" = ds."StyleId"
                            where ds."DanceId" = d."Id"), '') as styles
                  from "Dances" d''')
    return {name_key(r["name"]): r for r in got}


def cmd_search(args):
    styles = [s for s in STYLES if not args.styles or
              s.lower() in {x.strip().lower() for x in args.styles.split(",")}]
    have = existing()
    known = set(json.loads(ch.psql(
        'select coalesce(json_agg("VideoId"), \'[]\'::json) from "Videos";'
    ).strip() or "[]"))
    plan, taken = [], set()
    for style in styles:
        spec = STYLES[style]
        print(f"\n== {style}")
        for mv in spec["moves"]:
            name, diff, desc = mv[0], mv[1], mv[2]
            music = mv[3] if len(mv) > 3 else spec["music"]
            hit = have.get(name_key(name))
            if hit:
                print(f"   skip  {name:<30} already #{hit['id']} "
                      f"({hit['styles'] or 'no style'}, {hit['state']})")
                continue
            query = name if flat(spec["query"]) in flat(name) or \
                any(flat(w) in flat(name) for w in spec["words"]) \
                else f"{name} {spec['query']}"
            query += " tutorial"
            try:
                cands = search(query)
            except subprocess.TimeoutExpired:
                print(f"   ???   {name:<30} search timed out")
                continue
            kept, why = [], {}
            for c in cands:
                if c["ytid"] in known or c["ytid"] in taken:
                    continue
                ok, sc, reason = gate(c, name, style)
                if not ok:
                    why[reason] = why.get(reason, 0) + 1
                    continue
                kept.append({**c, "score": sc})
            kept.sort(key=lambda c: (-c["score"], -c["views"]))
            pick, chans = [], set()
            for c in kept:
                if c["channel"] in chans:
                    continue
                pick.append(c)
                chans.add(c["channel"])
                if len(pick) >= args.per_move:
                    break
            for c in pick:
                taken.add(c["ytid"])
            mark = "ok   " if pick else "none "
            print(f"   {mark} {name:<30} {len(pick)} of {len(cands)}"
                  + (f"  {pick[0]['title'][:52]}" if pick else f"  {why}"))
            if pick:
                plan.append({"style": style, "name": name, "difficulty": diff,
                             "description": desc, "music": music, "query": query,
                             "videos": pick})
            time.sleep(0.4)
    json.dump({"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "plan": plan},
              open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n{len(plan)} move(s) with a tutorial, "
          f"{sum(len(p['videos']) for p in plan)} video(s). wrote {OUT}")
    print("next: seed_style_moves.py insert")


def cmd_insert(args):
    plan = json.load(open(OUT, encoding="utf-8"))["plan"]
    have = existing()
    made = vids = 0
    for p in plan:
        if name_key(p["name"]) in have:
            continue
        got = ch.psql(f"""
            insert into "Dances"("Name","Slug","Description","DateAdded",
                                 "Difficulty","ReviewState")
            values ('{q(p["name"])}','{slugify(p["name"])}','{q(p["description"])}',
                    now(), {int(p["difficulty"])}, 'pending')
            returning "Id";""").strip()
        did = next((ln for ln in got.splitlines() if ln.strip().isdigit()), None)
        if not did:
            continue
        made += 1
        for v in p["videos"]:
            ch.psql(f"""
            insert into "Videos"("Title","VideoId","Platform","VideoType","DateAdded",
                                 "ViewCount","DurationSeconds","DanceId")
            values ('{q(v["title"])[:300]}','{v["ytid"]}','youtube','tutorial', now(),
                    {int(v["views"])}, {int(v["dur"])}, {int(did)});""")
            vids += 1
    print(f"inserted {made} pending dance(s) and {vids} pending video(s)")
    print("next: verify_intake.py --only-unscored apply; promote_confirmed.py apply; "
          "seed_style_moves.py promote apply")


def catalogue_moves():
    """flat(name) -> (style, move tuple)"""
    out = {}
    for style, spec in STYLES.items():
        for mv in spec["moves"]:
            out[name_key(mv[0])] = (style, mv)
    return out


def ours_pending():
    """Pending, style-less dances whose name is a catalogue move, with live-video counts."""
    moves = catalogue_moves()
    got = rows('''select d."Id" as id, d."Name" as name, d."Slug" as slug,
        (select count(*) from "Videos" v where v."DanceId" = d."Id"
           and v."ReviewState" = 'approved') as live,
        (select count(*) from "Videos" v where v."DanceId" = d."Id"
           and v."ReviewState" = 'pending') as waiting
        from "Dances" d
        where d."ReviewState" = 'pending'
          and not exists (select 1 from "DanceStyles" ds where ds."DanceId" = d."Id")''')
    out = []
    for r in got:
        m = moves.get(name_key(r["name"]))
        if m:
            out.append({**r, "style": m[0],
                        "music": m[1][3] if len(m[1]) > 3 else STYLES[m[0]]["music"]})
    return out


def style_id(name, create_desc=None):
    got = ch.psql(f'''select "Id" from "Styles" where lower("Name") = lower('{q(name)}');''').strip()
    if got:
        return int(got.splitlines()[0])
    if create_desc is None:
        return None
    got = ch.psql(f'''insert into "Styles"("Name","Description","DateAdded")
                      values ('{q(name)}','{q(create_desc)}', now()) returning "Id";''')
    return int(next(ln for ln in got.splitlines() if ln.strip().isdigit()))


def music_id(name, create=False):
    got = ch.psql(f'''select "Id" from "MusicalStyles" where lower("Name") = lower('{q(name)}');''').strip()
    if got:
        return int(got.splitlines()[0])
    if not create:
        return None
    got = ch.psql(f'''insert into "MusicalStyles"("Name","DateAdded")
                      values ('{q(name)}', now()) returning "Id";''')
    return int(next(ln for ln in got.splitlines() if ln.strip().isdigit()))


def free_slug(slug, sid):
    """Slugs are unique per style in app code, not in the DB - so check here."""
    if sid is None:
        return slug
    taken = {r["slug"] for r in rows(f'''select d."Slug" as slug from "Dances" d
              join "DanceStyles" ds on ds."DanceId" = d."Id"
              where ds."StyleId" = {sid}''')}
    s, n = slug, 2
    while s in taken:
        s, n = f"{slug}-{n}", n + 1
    return s


def cmd_promote(args):
    apply = args.apply == "apply"
    pend = ours_pending()
    for style, spec in STYLES.items():
        mine = [p for p in pend if p["style"] == style]
        ready = [p for p in mine if p["live"] > 0]
        sid = spec["id"] or style_id(style)
        adopt = list(spec["adopt"])
        if sid is not None:
            # the style exists: adopt only what has not been moved in already
            adopt = [a for a in adopt if not ch.psql(
                f'''select 1 from "DanceStyles" where "DanceId"={a} and "StyleId"={sid};'''
            ).strip()]
        if not mine and not adopt:
            continue
        print(f"\n== {style}: {len(ready)} ready, {len(mine) - len(ready)} still "
              f"waiting, {len(adopt)} to adopt"
              + ("" if sid else " (style not created yet)"))
        if sid is None and len(ready) + len(adopt) < MIN_LIVE:
            print(f"   holding: a new style needs {MIN_LIVE} live moves")
            continue
        for p in ready:
            print(f"   live  #{p['id']:<5} {p['name']}")
        for a in adopt:
            print(f"   adopt #{a}")
        if not apply:
            continue
        if sid is None:
            sid = style_id(style, create_desc=spec["desc"])
            print(f"   created style #{sid}")
        for p in ready:
            mid = music_id(p["music"], create=True)
            slug = free_slug(p["slug"], sid)
            ch.psql(f'''
              insert into "DanceStyles"("DanceId","StyleId") values ({p["id"]},{sid})
                on conflict do nothing;
              insert into "DanceMusicalStyles"("DanceId","MusicalStyleId")
                values ({p["id"]},{mid}) on conflict do nothing;
              update "Dances" set "ReviewState" = 'approved', "Slug" = '{slug}'
               where "Id" = {p["id"]};''')
        for a in adopt:
            slug = rows(f'select "Slug" as slug from "Dances" where "Id"={a}')
            if not slug:
                continue
            new = free_slug(slug[0]["slug"], sid)
            ch.psql(f'''
              delete from "DanceStyles" where "DanceId" = {a};
              insert into "DanceStyles"("DanceId","StyleId") values ({a},{sid});
              update "Dances" set "Slug" = '{new}' where "Id" = {a};''')
    if not apply:
        print("\ndry run - pass 'apply' to take these live")


def cmd_retry(args):
    """More candidates for pending moves none of whose videos verified.

    A move sticks when every video it got came back silent, unclear or
    unnamed - often a non-English teacher, whom the English-only ASR can never
    confirm (asr-english-only). Differently phrased English queries give it
    fresh chances. New videos attach to the existing pending dance.
    """
    stuck = [p for p in ours_pending() if p["live"] == 0]
    if args.styles:
        want = {x.strip().lower() for x in args.styles.split(",")}
        stuck = [p for p in stuck if p["style"].lower() in want]
    known = set(json.loads(ch.psql(
        'select coalesce(json_agg("VideoId"), \'[]\'::json) from "Videos";'
    ).strip() or "[]"))
    added = 0
    for p in stuck:
        spec = STYLES[p["style"]]
        queries = [f"how to do {p['name']} {spec['query']}",
                   f"{p['name']} {spec['query']} lesson for beginners"]
        pick, chans = [], set()
        for qy in queries:
            try:
                cands = search(qy)
            except subprocess.TimeoutExpired:
                continue
            for c in sorted(cands, key=lambda c: -c["views"]):
                if c["ytid"] in known or c["channel"] in chans:
                    continue
                ok, sc, _ = gate(c, p["name"], p["style"])
                if ok:
                    pick.append(c)
                    chans.add(c["channel"])
                    known.add(c["ytid"])
                if len(pick) >= args.per_move:
                    break
            if len(pick) >= args.per_move:
                break
            time.sleep(0.4)
        print(f"   {len(pick)} new  {p['style'][:14]:<15} {p['name'][:28]:<29}"
              + (f" {pick[0]['title'][:50]}" if pick else ""))
        if args.apply != "apply":
            continue
        for v in pick:
            ch.psql(f"""
            insert into "Videos"("Title","VideoId","Platform","VideoType","DateAdded",
                                 "ViewCount","DurationSeconds","DanceId")
            values ('{q(v["title"])[:300]}','{v["ytid"]}','youtube','tutorial', now(),
                    {int(v["views"])}, {int(v["dur"])}, {int(p["id"])});""")
            added += 1
    print(f"\n{len(stuck)} stuck move(s); "
          + (f"inserted {added} pending video(s)" if args.apply == "apply"
             else "dry run - pass 'apply' to insert"))


def cmd_status(args):
    pend = ours_pending()
    for style, spec in STYLES.items():
        sid = spec["id"] or style_id(style)
        live = 0
        if sid:
            live = int(ch.psql(f'''select count(*) from "DanceStyles" ds join "Dances" d
                on d."Id" = ds."DanceId" where ds."StyleId" = {sid}
                and d."ReviewState" = 'approved';''').strip() or 0)
        mine = [p for p in pend if p["style"] == style]
        print(f"{style:<18} {'exists' if sid else 'NEW':<7} live={live:<4} "
              f"pending={len(mine):<3} ready={sum(1 for p in mine if p['live'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "insert", "promote", "status", "retry"])
    ap.add_argument("apply", nargs="?")
    ap.add_argument("--styles")
    ap.add_argument("--per-move", type=int, default=2)
    args = ap.parse_args()
    {"search": cmd_search, "insert": cmd_insert, "promote": cmd_promote,
     "status": cmd_status, "retry": cmd_retry}[args.cmd](args)


if __name__ == "__main__":
    main()
