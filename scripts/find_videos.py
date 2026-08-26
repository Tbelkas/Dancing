"""
find_videos.py - gated discovery of better tutorial videos.

    python scripts/find_videos.py targets [--limit N]   rank the dances that need help
    python scripts/find_videos.py scan [--limit N]      search YouTube, score, shortlist
    python scripts/find_videos.py review [--min S]      read the shortlist
    python scripts/find_videos.py apply [--min S] apply insert the keepers as "pending"

WHY THIS IS NOT THE OLD SEEDER
------------------------------
The archived flow (archive/SEED_FLOW.md) took a move name, ran one YouTube search, and
inserted whatever came back. Nothing checked that the video taught the move. Its success
criteria were counts - "50 new dances, 60% with a video" - so a salsa move pointing at an
electro clip scored as a win. That is how the catalogue ended up with 1153 videos nobody
had watched.

This inverts the order. A candidate has to earn its way in:

  1. it must not already be in the catalogue
  2. its title must actually overlap the dance or its style   <- the missing check
  3. it must be long enough to teach something and not a Short
  4. it must not read as a course advert or a performance clip
  5. what survives is INSERTED AS "pending", never as approved

Step 5 is the point. Discovery does not get to publish. It fills the Intake tab in
scripts/chip_ui.py, and a person decides. The database default already quarantines raw
inserts; this leans on that rather than working around it.

WHAT IT TARGETS
---------------
Not empty dances - there is exactly one of those. 980 of 1051 dances have exactly one
video, so the real deficit is depth: if that single video is bad, the dance is bad and
nothing on the site says so. Targets are ranked by how badly the dance is served today -
the gate's own score on what it already has, whether it has chips, how thin the video is -
so the search effort goes where a second source changes the most.

COST: yt-dlp searches only. No API, no model, no quota. Roughly one second per query,
three queries per dance. Safe to run for hours and safe to interrupt - state lives in
_proto/discovery.json and every stage is resumable.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch          # noqa: E402  psql + appsettings connection
import video_gate as vg           # noqa: E402  toks/_stem/PROMO - one rubric, not two

ROOT = ch.ROOT
PROTO = os.path.join(ROOT, "_proto")
STATE = os.path.join(PROTO, "discovery.json")
TARGETS = os.path.join(PROTO, "discovery_targets.json")

# A tutorial that teaches a move. Below 60s is a Short; above an hour is a class
# recording or a livestream, neither of which is what a move page wants.
MIN_DUR, MAX_DUR = 60, 3600

# Signals that a title is teaching rather than performing. Weak evidence on its own -
# used to rank, never to admit.
TEACHY = re.compile(r"\b(tutorial|how to|how-to|basics?|beginners?|lesson"
                    r"|step by step|breakdown|learn|explained)\b", re.I)
PERFORMY = re.compile(r"\b(performance|showcase|battle|cypher|competition"
                      r"|music video|official video|live at|compilation"
                      r"|reaction|vlog|behind the scenes)\b", re.I)

# Vocabulary a person teaching a dance cannot avoid: they name body parts and they
# count. This is the check that separates a dance tutorial from a video that merely
# shares a word with the move - searching the Breakdance move "Blade" returns a Super
# Smash Bros guide to "Dancing Blade" that says the word, teaches, and is not a dance
# video at all.
#
# The threshold is measured, not guessed. Over 49 transcribed catalogue videos the
# median is 10 distinct terms and the minimum is 2; the Smash guide scores 1 and a
# real K-pop tutorial scores 23. Four sits below every real tutorial in that sample
# and well above the impostor.
BODY = re.compile(r"\b(foot|feet|leg|legs|knee|knees|arm|arms|hand|hands|hip|hips"
                  r"|shoulder|shoulders|chest|torso|wrist|elbow|ankle|heel|heels"
                  r"|toe|toes|head|body|weight|posture|bounce|groove|rhythm"
                  r"|beat|beats|count|counts|eight|choreo|choreography|footwork"
                  r"|step|steps|routine|freestyle|five six seven eight|5 6 7 8"
                  r"|one two three)\b", re.I)
MIN_BODY_TERMS = 4


def _read(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(path, obj):
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)


# ------------------------------------------------------------------- targets

TARGET_SQL = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select d."Id" as "danceid", d."Name" as "dance", d."Slug" as "slug",
         coalesce((select string_agg(s."Name", ' / ' order by s."Name")
                   from "DanceStyles" ds join "Styles" s on s."Id" = ds."StyleId"
                   where ds."DanceId" = d."Id"), '') as "styles",
         (select count(*) from "Videos" v where v."DanceId" = d."Id") as "nvideos",
         (select min(coalesce(v."QualityScore", 1.0)) from "Videos" v
           where v."DanceId" = d."Id") as "worstscore",
         (select coalesce(string_agg(distinct v."QualityFlags", ','), '')
            from "Videos" v where v."DanceId" = d."Id") as "flags",
         (select count(*) from "Videos" v
            join "VideoSegments" g on g."VideoId" = v."Id"
           where v."DanceId" = d."Id") as "nchips",
         (select max(coalesce(v."DurationSeconds", 0)) from "Videos" v
           where v."DanceId" = d."Id") as "bestdur"
  from "Dances" d
) t;
"""


def deficit(r):
    """How badly this dance is served today. Higher = search for it sooner.

    Built from what the gate already knows rather than from a guess: a low score on the
    only video it has is the strongest signal, because that is the case where the dance
    looks fine on the site and is not.
    """
    d = 0.0
    d += (1.0 - float(r["worstscore"] or 1.0)) * 3.0   # the gate doubts what it has
    if r["nvideos"] <= 1:
        d += 1.0                                        # one source, no second opinion
    if r["nvideos"] == 0:
        d += 2.0
    if not r["nchips"]:
        d += 0.5                                        # no sections bar
    bd = int(r["bestdur"] or 0)
    if 0 < bd < 90:
        d += 0.8                                        # too thin to teach
    for f in ("title-dance-mismatch", "dance-never-mentioned", "not-instructional"):
        if f in (r["flags"] or ""):
            d += 1.2                                    # may be the wrong video entirely
    return round(d, 3)


def cmd_targets(args):
    rows = json.loads(ch.psql(TARGET_SQL).strip() or "[]")
    for r in rows:
        r["deficit"] = deficit(r)
    rows.sort(key=lambda r: -r["deficit"])
    _write(TARGETS, rows)
    print(f"{len(rows)} dances ranked -> {TARGETS}")
    print(f"  {'def':>5} {'nv':>2} {'score':>5} {'dance':<28} {'style':<22} flags")
    for r in rows[:args.limit or 25]:
        print(f"  {r['deficit']:>5.2f} {r['nvideos']:>2} "
              f"{float(r['worstscore'] or 1):>5.2f} {r['dance'][:26]:<28} "
              f"{(r['styles'] or '')[:20]:<22} {(r['flags'] or '')[:44]}")


# ---------------------------------------------------------------------- scan

def catalogue_ids():
    out = ch.psql('select distinct "VideoId" from "Videos";').strip()
    return {l.strip() for l in out.splitlines() if l.strip()}


def search(query, n=5):
    p = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", "--no-warnings",
         "--flat-playlist", f"ytsearch{n}:{query}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (p.stdout or "").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("id"):
            out.append({"ytid": d["id"], "title": d.get("title") or "",
                        "dur": int(d.get("duration") or 0),
                        "views": int(d.get("view_count") or 0),
                        "channel": d.get("channel") or d.get("uploader") or ""})
    return out


def queries(dance, styles):
    """Three angles on the same move. The style-qualified one matters most: "Spiral"
    alone returns contemporary, and that is exactly how a House move ended up pointing
    at a Contemporary clip in the 2026-06 audit."""
    style = (styles or "").split(" / ")[0].strip()
    qs = [f"{style} {dance} tutorial".strip(),
          f"how to {dance} {style} dance".strip(),
          f"{dance} dance tutorial beginner"]
    return [re.sub(r"\s+", " ", q).strip() for q in dict.fromkeys(qs)]


def score_candidate(c, dance, styles):
    """Tier 0/1 of the same rubric, applied BEFORE anything is written.

    Returns (score, flags, fatal). A fatal flag means never insert this - it is not a
    judgement call the Intake tab should have to make, because the candidate does not
    even claim to be about this dance.

    The score starts LOW and is earned, rather than starting at 1.0 and being chipped
    at. Starting from the top made every plausible candidate score exactly 1.0 after
    the clamp, which ranked a 12-minute yoga video level with a real tutorial for the
    same dance. A ranking that cannot separate its own top 30 is not a ranking.
    """
    flags = []
    score = 0.40
    title_t = vg.toks(c["title"])
    dance_t = vg.toks(dance)
    style_t = vg.toks(styles)
    hit_dance = bool(dance_t & title_t)
    hit_style = bool(style_t & title_t)

    # THE check the old seeder never made.
    if dance_t and not hit_dance and not hit_style:
        return 0.0, ["title-matches-nothing"], True

    if c["dur"] and c["dur"] < MIN_DUR:
        return 0.0, ["short-form"], True
    if c["dur"] > MAX_DUR:
        score -= 0.20
        flags.append("very-long")
    if not c["dur"]:
        score -= 0.10
        flags.append("no-duration")

    # Naming the move is the strongest title-level evidence there is.
    if hit_dance:
        score += 0.25
        flags.append("names-the-move")
    if hit_style:
        score += 0.10
        flags.append("names-the-style")
    # Matching the style but NOT the move is how a generic clip for the right genre
    # gets attached to a specific step. Worth surfacing, not worth rejecting on.
    if hit_style and not hit_dance:
        flags.append("style-only-match")

    if TEACHY.search(c["title"]):
        score += 0.20
        flags.append("teachy-title")
    if vg.PROMO.search(c["title"]):
        score -= 0.30
        flags.append("promo-title")
    if PERFORMY.search(c["title"]):
        score -= 0.25
        flags.append("performance-not-tutorial")

    # Views are a weak prior for "someone found this useful", deliberately small so a
    # viral performance clip cannot outrank a small, correct tutorial.
    if c["views"] >= 500_000:
        score += 0.08
    elif c["views"] >= 50_000:
        score += 0.05
    elif c["views"] < 500:
        score -= 0.10
        flags.append("almost-unwatched")

    return round(max(0.0, min(1.0, score)), 3), flags, False


def cmd_scan(args):
    targets = _read(TARGETS, None)
    if targets is None:
        print("no targets yet - run: python scripts/find_videos.py targets")
        return
    state = _read(STATE, {"scanned": {}, "candidates": {}})
    known = catalogue_ids()
    todo = [t for t in targets if str(t["danceid"]) not in state["scanned"]]
    if args.style:
        todo = [t for t in todo if args.style.lower() in (t["styles"] or "").lower()]
    todo = todo[:args.limit or 40]
    print(f"scanning {len(todo)} dances ({len(state['scanned'])} already done)")

    for n, t in enumerate(todo, 1):
        found, seen = [], set()
        for q in queries(t["dance"], t["styles"]):
            for c in search(q, args.per_query):
                if c["ytid"] in known or c["ytid"] in seen:
                    continue
                seen.add(c["ytid"])
                sc, fl, fatal = score_candidate(c, t["dance"], t["styles"])
                if fatal:
                    continue
                found.append({**c, "score": sc, "flags": fl, "query": q,
                              "danceid": t["danceid"], "dance": t["dance"],
                              "styles": t["styles"]})
        found.sort(key=lambda x: -x["score"])
        state["scanned"][str(t["danceid"])] = {"at": time.time(), "n": len(found)}
        if found:
            state["candidates"][str(t["danceid"])] = found[:5]
        if n % 5 == 0 or n == len(todo):
            _write(STATE, state)
        best = f"{found[0]['score']:.2f} {found[0]['title'][:44]}" if found else "-"
        print(f"  [{n}/{len(todo)}] {t['dance'][:24]:<26} {len(found):>2} kept   {best}",
              flush=True)

    _write(STATE, state)
    tot = sum(len(v) for v in state["candidates"].values())
    print(f"\n{tot} candidates across {len(state['candidates'])} dances -> {STATE}")


# -------------------------------------------------------------------- verify

def verify_one(c):
    """Tier 2 on a candidate: does the person in it actually teach this move?

    A title is a claim. The scan stage can only weigh the claim, and the claim is
    often wrong in a way that reads perfectly: searching the Breakdance move "Blade"
    returns a rollerblading lesson whose title contains the word, scores well on every
    title signal, and is not remotely the right video. Nothing but the audio settles it.

    Reuses signals.py for the transcript and video_gate's tier-2 rules for the verdict,
    so a candidate is judged by the same standard as the catalogue it wants to join.
    Returns a dict merged into the candidate.
    """
    sig = vg.load_sig(c["ytid"])
    if sig is None:
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "signals.py"),
                            "--", c["ytid"]],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=ROOT)
        sig = vg.load_sig(c["ytid"])
        if sig is None:
            return {"verified": "no-transcript",
                    "vnote": (p.stderr or "extraction failed")[-160:]}

    a = sig.get("asr") or {}
    text = " ".join(s.get("text", "") for s in (a.get("segments") or []))
    dens = [d["v"] for d in (sig.get("density") or [])]
    speechy = sum(1 for v in dens if v > 0.15) / len(dens) if dens else 0.0

    tt = vg.toks(text)
    dance_t = vg.toks(c["dance"])
    style_t = vg.toks(c["styles"])
    says_move = bool(dance_t & tt)
    says_style = bool(style_t & tt)
    teaches = bool(vg.TEACH_CUES.search(text))
    body = {m.group(0).lower() for m in BODY.finditer(text)}

    # A deliberately wordless tutorial is a real format (mirrored K-pop walkthroughs
    # carry the instruction on screen), so silence is "unknown", never "bad".
    if speechy < 0.10:
        return {"verified": "silent", "speechy": round(speechy, 3),
                "says_move": False, "teaches": False, "body": len(body),
                "vnote": "no speech - cannot be judged from audio"}

    base = {"speechy": round(speechy, 3), "says_move": says_move,
            "says_style": says_style, "teaches": teaches, "body": len(body),
            "lang": a.get("language"),
            "vnote": f"move={'y' if says_move else 'n'} "
                     f"style={'y' if says_style else 'n'} "
                     f"teaching={'y' if teaches else 'n'} body={len(body)}"}

    # Nobody is teaching a dance here, whatever the title claimed.
    if len(body) < MIN_BODY_TERMS:
        return {**base, "verified": "not-a-dance-video"}

    if says_move and teaches:
        v = "confirmed"
    elif teaches and (says_style or says_move):
        v = "partial"
    elif teaches:
        # A real dance tutorial that never says the move's name. Common and legitimate
        # when the "move" is a song title or the teacher just demonstrates - but it is
        # not evidence that THIS video teaches THIS dance, so it needs eyes.
        v = "dance-but-unnamed"
    else:
        v = "unconfirmed"
    return {**base, "verified": v}


def cmd_verify(args):
    state = _read(STATE, {"candidates": {}})
    # Only the leader per dance is worth transcribing: verification costs a download
    # and a Whisper pass, and the aim is one good second source, not a ranked five.
    queue = []
    for did, cands in state["candidates"].items():
        for c in sorted(cands, key=lambda x: -x["score"]):
            if c["score"] < args.min:
                break
            if "verified" not in c:
                queue.append((did, c))
                break
    queue = queue[:args.limit or 25]
    print(f"verifying {len(queue)} candidates (score >= {args.min})")

    for n, (did, c) in enumerate(queue, 1):
        t0 = time.time()
        c.update(verify_one(c))
        _write(STATE, state)
        print(f"  [{n}/{len(queue)}] {c['dance'][:22]:<24} {c['verified']:<13} "
              f"{c.get('vnote', '')[:44]}  ({time.time()-t0:.0f}s)", flush=True)

    tally = {}
    for cands in state["candidates"].values():
        for c in cands:
            if "verified" in c:
                tally[c["verified"]] = tally.get(c["verified"], 0) + 1
    print("\nverdicts so far:", "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))


# -------------------------------------------------------------------- review

def shortlist(min_score):
    state = _read(STATE, {"candidates": {}})
    out = []
    for cands in state["candidates"].values():
        for c in cands:
            if c["score"] >= min_score:
                out.append(c)
    out.sort(key=lambda x: (-x["score"], -x["views"]))
    return out


def cmd_review(args):
    rows = shortlist(args.min)
    print(f"{len(rows)} candidates at score >= {args.min}")
    print(f"  {'score':>5} {'verified':<13} {'dur':>5} {'views':>10}  {'dance':<22} title")
    for r in rows[:args.limit or 40]:
        print(f"  {r['score']:>5.2f} {r.get('verified', '-'):<13} {r['dur']:>5} "
              f"{r['views']:>10,}  {r['dance'][:20]:<22} {r['title'][:52]}")


# --------------------------------------------------------------------- apply

def cmd_apply(args):
    rows = shortlist(args.min)
    # Only what the transcript backed up. "confirmed" means the person in the video
    # says the move's name AND is audibly teaching; "partial" means one of the two.
    # Everything else - unverified, silent, unconfirmed - stays out of the database
    # entirely rather than landing in Intake for a human to sort out, because an
    # Intake queue full of maybes is how a review step stops being used.
    allowed = {"confirmed"} if not args.include_partial else {"confirmed", "partial"}
    rejected = [r for r in rows if r.get("verified") not in allowed]
    rows = [r for r in rows if r.get("verified") in allowed]
    if rejected:
        print(f"{len(rejected)} candidate(s) held back as unverified "
              f"(run 'verify' first, or pass --include-partial)")

    # One new video per dance per run: the aim is a second opinion, not a pile.
    best, seen = [], set()
    for r in rows:
        if r["danceid"] in seen:
            continue
        seen.add(r["danceid"])
        best.append(r)
    best = best[:args.limit or 50]

    print(f"{len(best)} videos would be inserted as 'pending' (one per dance)")
    for r in best[:20]:
        print(f"  {r['score']:>5.2f}  d{r['danceid']:<5} {r['dance'][:20]:<22} "
              f"{r['ytid']}  {r['title'][:44]}")
    if not args.apply:
        print("\ndry run - pass 'apply' to write")
        return

    known = catalogue_ids()
    ins = 0
    for r in best:
        if r["ytid"] in known:
            continue
        title = r["title"].replace("'", "''")[:300]
        flags = ",".join(r["flags"]).replace("'", "''")
        dur = int(r["dur"]) if r["dur"] else None
        # Explicitly 'pending' rather than relying on the column default, so the
        # quarantine is readable at the call site and survives a default change.
        ch.psql('insert into "Videos" '
                '("Title","VideoId","Platform","VideoType","DanceId","DateAdded",'
                '"ViewCount","DurationSeconds","ReviewState","QualityScore",'
                '"QualityFlags","ReviewNote","AverageRating","RatingCount") values ('
                f"'{title}','{r['ytid']}','youtube','tutorial',{int(r['danceid'])},"
                f"now(),{int(r['views'])},{dur if dur else 'null'},'pending',"
                f"{r['score']},'{flags}','discovered by find_videos.py',0,0);")
        ins += 1
    print(f"\ninserted {ins} as pending - review them in the dashboard's Intake tab")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("targets")
    t.add_argument("--limit", type=int)
    t.set_defaults(fn=cmd_targets)

    s = sub.add_parser("scan")
    s.add_argument("--limit", type=int)
    s.add_argument("--style")
    s.add_argument("--per-query", type=int, default=5)
    s.set_defaults(fn=cmd_scan)

    v = sub.add_parser("verify")
    v.add_argument("--min", type=float, default=0.75)
    v.add_argument("--limit", type=int)
    v.set_defaults(fn=cmd_verify)

    r = sub.add_parser("review")
    r.add_argument("--min", type=float, default=0.75)
    r.add_argument("--limit", type=int)
    r.set_defaults(fn=cmd_review)

    a = sub.add_parser("apply")
    a.add_argument("--min", type=float, default=0.75)
    a.add_argument("--limit", type=int)
    a.add_argument("--include-partial", action="store_true")
    a.add_argument("apply", nargs="?")
    a.set_defaults(fn=cmd_apply)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
