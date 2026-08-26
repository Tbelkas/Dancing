"""
video_gate.py — the intake quality rubric.

    python scripts/video_gate.py audit [--limit N]   score the existing catalogue
    python scripts/video_gate.py check <ytid> <danceId> [--type tutorial]

Same shape as chip_health.py: deterministic checks first because they are free,
transcript evidence only where it exists. Produces a score, a verdict, and the
list of flag codes that explain it - never a bare number, because the whole point
is being able to see why something was held back.

Three tiers, cheapest first:

  0  from the database alone      duplicates, duration, title/dance coherence
  1  from cached yt-dlp metadata  availability, shorts, promo titles, engagement
  2  from _proto/sig_<ytid>.json  is anyone actually teaching this dance?

Tier 2 is the one that catches the failure the seeding pitfalls describe - yt-dlp
returning an electro clip for a salsa move. Nothing else in the pipeline can tell
that the video is wrong rather than merely thin, because the only evidence is what
the person in it says.

Verdicts: admit >= 0.65, review 0.35-0.65, reject < 0.35.
This script NEVER writes to the database. Applying a verdict is a separate,
deliberate step.
"""
import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import chip_health as ch  # noqa: E402  (psql plumbing + appsettings connection)

ROOT = ch.ROOT
PROTO = os.path.join(ROOT, "_proto")
OUT = os.path.join(PROTO, "gate_audit.json")

ADMIT, REVIEW = 0.65, 0.35

PROMO = re.compile(r"(enroll|sign\s?up|link in bio|full course|masterclass|discount"
                   r"|promo code|patreon|subscribe now|join my|book now)", re.I)

# Someone teaching says these. A performance clip does not.
TEACH_CUES = re.compile(
    r"\b(let'?s|we'?re going to|i'?m going to|now we|next|first|second|third"
    r"|step|follow|repeat|practice|try it|one more time|from the top"
    r"|five six seven eight|5 6 7 8|break it down|slow(ly)? |together)\b", re.I)

STOP = {"the", "a", "an", "and", "of", "to", "in", "on", "with", "for", "dance",
        "dancing", "tutorial", "how", "step", "steps", "move", "moves", "basic",
        "beginner", "easy", "learn", "lesson"}


def _stem(w):
    """Crude singularisation. "Old Way Switches" vs "Front Switch and Side Switch"
    is the same move, and a bare set-intersection called it a mismatch."""
    for suf in ("ies", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)] + ("y" if suf == "ies" else "")
    return w


def toks(s):
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", (s or "").lower())
            if w not in STOP and len(w) > 2}


def _flat(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def name_matches(dance, text):
    """Does `text` name this dance? Tolerant of how the same move gets written.

    A bare token intersection produced a steady stream of false accusations against
    perfectly correct videos, because move names are not written consistently:

      "Waacking"   vs "Beginner Whacking Tutorial"    one substitution
      "Breakdance" vs "10 Easy Break Dance TOPROCKS"  a space, and toks() cannot see
                                                      it because "dance" is a stop word

    Both were being flagged title-dance-mismatch and dance-never-mentioned, which is
    how a rubble of good videos ends up on a "probably wrong" list and the list stops
    being trusted.

    It stays deliberately strict about genuinely different moves: Tendu does not match
    a plie combination, and Blade does not match a backspin. What it cannot fix is a
    move that is simply called something else - "Dramatic Dip" against "Death Drop" is
    the same move under two names, and only a person knows that.
    """
    dt, tt = toks(dance), toks(text)
    if dt & tt:
        return True
    ft = _flat(text)
    for w in dt:
        if len(w) >= 5 and w in ft:
            return True
    fd = _flat(dance)
    if len(fd) >= 5 and fd in ft:
        return True
    for w in dt:
        if len(w) < 6:
            continue
        for t in tt:
            if (abs(len(w) - len(t)) <= 2
                    and difflib.SequenceMatcher(None, w, t).ratio() >= 0.85):
                return True
    return False


FETCH = """
select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
  select v."Id" as "vid", v."VideoId" as "ytid", v."Platform" as "platform",
         v."VideoType" as "vtype", v."Title" as "title",
         v."StartTime" as "clipstart",
         coalesce(v."DurationSeconds", 0) as "dur",
         coalesce(v."ViewCount", 0) as "views",
         v."ReviewState" as "state",
         v."QualityFlags" as "qflags",
         v."ReviewNote" as "qnote",
         coalesce(d."Name", '') as "dance",
         coalesce((select string_agg(s."Name", ' ')
                   from "DanceStyles" ds join "Styles" s on s."Id" = ds."StyleId"
                   where ds."DanceId" = d."Id"), '') as "styles",
         (select count(*) from "Videos" o
           where o."VideoId" = v."VideoId" and o."Platform" = v."Platform"
             and o."DanceId" <> v."DanceId") as "otherdances"
  from "Videos" v
  left join "Dances" d on d."Id" = v."DanceId"
) t;
"""


def load_meta(ytid):
    p = os.path.join(PROTO, f"{ytid}.json")
    if not os.path.exists(p):
        return None
    try:
        d = json.load(open(p, encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def load_sig(ytid):
    p = os.path.join(PROTO, f"sig_{ytid}.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def grade(r, meta=None, sig=None):
    """Return (score, verdict, flags, tier_reached)."""
    flags = []
    score = 1.0
    tier = 0

    dance_t = toks(r.get("dance"))
    style_t = toks(r.get("styles"))
    title_t = toks(r.get("title"))
    is_slice = r.get("clipstart") is not None

    # ---- tier 0: the database alone ------------------------------------
    if not is_slice and 0 < r["dur"] < 30:
        score -= 0.25
        flags.append("too-short")
    if r["dur"] == 0:
        score -= 0.10
        flags.append("no-duration")

    # A clip legitimately spans several dances when it is a montage that has been
    # cut into windows. The same clip on many dances with NO start time is the
    # mis-sourcing signature instead.
    other = r.get("otherdances") or 0
    if other >= 3 and not is_slice:
        score -= 0.25
        flags.append(f"same-clip-on-{other}-dances")
    elif other >= 8:
        score -= 0.10
        flags.append(f"same-clip-on-{other}-dances")

    # A montage window is titled for the whole video, not for the one move this
    # slice teaches - "Top 5 Afro Dance Moves" will never contain "Wankele".
    # Checking the title against the dance name there produces nothing but noise.
    montage = is_slice or other >= 3
    if (dance_t and title_t and not montage
            and not name_matches(r.get("dance"), r.get("title"))
            and not (style_t & title_t)):
        score -= 0.30
        flags.append("title-dance-mismatch")

    if PROMO.search(r.get("title") or ""):
        score -= 0.20
        flags.append("promo-title")

    # ---- tier 1: cached metadata ---------------------------------------
    if meta:
        tier = 1
        avail = (meta.get("availability") or "public")
        if avail not in ("public", "unlisted"):
            score -= 0.40
            flags.append(f"availability-{avail}")
        if meta.get("age_limit"):
            score -= 0.15
            flags.append("age-restricted")
        if meta.get("live_status") in ("is_live", "is_upcoming"):
            score -= 0.30
            flags.append("livestream")
        mdur = meta.get("duration") or 0
        if 0 < mdur <= 60 and (meta.get("width") or 0) < (meta.get("height") or 0):
            score -= 0.10
            flags.append("short-form")
        if PROMO.search(meta.get("description") or "")and len(
                (meta.get("description") or "")) < 200:
            score -= 0.10
            flags.append("promo-description")

    # ---- tier 2: what the person actually says -------------------------
    if sig:
        tier = 2
        a = sig.get("asr") or {}
        text = " ".join(s.get("text", "") for s in (a.get("segments") or []))
        dens = [d["v"] for d in (sig.get("density") or [])]
        speechy = sum(1 for v in dens if v > 0.15) / len(dens) if dens else 0

        # Some tutorials are deliberately wordless - mirrored K-pop walkthroughs
        # carry their instruction on screen, not in speech. Charge that ONCE, and
        # skip the text-derived checks below: with no transcript, "the dance is
        # never mentioned" and "not instructional" are not independent evidence,
        # they are the same silence counted three times.
        silent_format = speechy < 0.10
        if r["vtype"] == "tutorial" and speechy < 0.25:
            score -= 0.15 if silent_format else 0.30
            flags.append("silent-tutorial-format" if silent_format
                         else "no-speech-for-a-tutorial")

        if text.strip() and not silent_format:
            tt = toks(text)
            # Same reasoning: in a montage the instructor names each move once, and
            # a missed word is weak evidence. Penalise it only on a standalone video.
            if (dance_t and not name_matches(r.get("dance"), text)
                    and not (style_t & tt)):
                if montage:
                    flags.append("dance-not-heard(montage)")
                else:
                    score -= 0.30
                    flags.append("dance-never-mentioned")
            if r["vtype"] == "tutorial" and not TEACH_CUES.search(text):
                score -= 0.20
                flags.append("not-instructional")
            lang = a.get("language")
            if lang and lang != "en":
                flags.append(f"spoken-{lang}")  # informational, not penalised
        elif speechy < 0.05:
            flags.append("silent")

    score = round(max(0.0, min(1.0, score)), 3)
    verdict = "admit" if score >= ADMIT else "review" if score >= REVIEW else "reject"
    return score, verdict, flags, tier


def cmd_audit(args):
    rows = json.loads(ch.psql(FETCH).strip() or "[]")
    if args.limit:
        rows = rows[:args.limit]
    out, tiers = [], {0: 0, 1: 0, 2: 0}
    for r in rows:
        meta = load_meta(r["ytid"]) if r["platform"] == "youtube" else None
        sig = load_sig(r["ytid"]) if r["platform"] == "youtube" else None
        score, verdict, flags, tier = grade(r, meta, sig)
        tiers[tier] += 1
        out.append({**{k: r[k] for k in
                       ("vid", "ytid", "platform", "vtype", "title", "dance",
                        "dur", "views", "state")},
                    "score": score, "verdict": verdict, "flags": flags, "tier": tier})

    out.sort(key=lambda x: x["score"])
    by_v, by_f = {}, {}
    for x in out:
        by_v[x["verdict"]] = by_v.get(x["verdict"], 0) + 1
        for f in x["flags"]:
            key = re.sub(r"\d+", "N", f)
            by_f[key] = by_f.get(key, 0) + 1

    print(f"audited {len(out)} videos")
    print("  verdict :", "  ".join(f"{k}={v}" for k, v in sorted(by_v.items())))
    print("  evidence:", f"tier0(db only)={tiers[0]}  tier1(+metadata)={tiers[1]}  "
                         f"tier2(+transcript)={tiers[2]}")
    print("\n  flags raised:")
    for f, n in sorted(by_f.items(), key=lambda x: -x[1]):
        print(f"    {n:>5}  {f}")

    worst = [x for x in out if x["verdict"] != "admit"]
    print(f"\n  lowest-scoring {min(20, len(worst))}:")
    print(f"    {'vid':>5} {'score':>5} {'t':>1} {'views':>10}  {'dance':<22} flags")
    for x in worst[:20]:
        print(f"    {x['vid']:>5} {x['score']:>5.2f} {x['tier']:>1} {x['views']:>10,}  "
              f"{(x['dance'] or '')[:20]:<22} {','.join(x['flags'])}")

    json.dump({"admit": ADMIT, "review": REVIEW, "videos": out},
              open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\nwrote {OUT}")
    print("Read-only: nothing was written to the database.")


def cmd_check(args):
    rows = json.loads(ch.psql(FETCH).strip() or "[]")
    match = [r for r in rows if r["ytid"] == args.ytid
             and (not args.dance or str(r["vid"]) == args.dance)]
    if not match:
        print(f"no catalogue row for {args.ytid}")
        return
    for r in match:
        score, verdict, flags, tier = grade(
            r, load_meta(r["ytid"]), load_sig(r["ytid"]))
        print(f"#{r['vid']} {r['dance']}: {verdict} ({score:.2f}, tier {tier})")
        for f in flags:
            print(f"   - {f}")


def cmd_stamp(args):
    """Score videos in a given ReviewState and write the score back.

    This is the step to run after a seeding batch: the database default drops raw
    inserts into "pending", this grades them, and --auto-admit promotes the ones
    that clear the bar so only the questionable remainder needs a human.
    """
    rows = json.loads(ch.psql(FETCH).strip() or "[]")
    rows = [r for r in rows if r["state"] == args.state]

    # Never overwrite a verdict that came from looking at the video.
    #
    # This rubric and verify_visual.py write the same three columns, and this one runs
    # far more often. A visual verdict costs a download, a contact sheet and a model
    # call, and it exists precisely for videos this rubric cannot judge - so re-stamping
    # would replace the only real evidence those rows have with a score derived from
    # their silence, and do it silently.
    held = [r for r in rows if (r.get("qflags") or "").startswith("visual:")]
    if held:
        rows = [r for r in rows if not (r.get("qflags") or "").startswith("visual:")]
        print(f"keeping {len(held)} visual verdict(s) - frames beat this rubric on the "
              "videos it cannot hear")

    if not rows:
        print(f"no videos in state '{args.state}'")
        return

    graded = []
    for r in rows:
        meta = load_meta(r["ytid"]) if r["platform"] == "youtube" else None
        sig = load_sig(r["ytid"]) if r["platform"] == "youtube" else None
        score, verdict, flags, tier = grade(r, meta, sig)
        graded.append((r, score, verdict, flags))

    by_v = {}
    for _, _, v, _ in graded:
        by_v[v] = by_v.get(v, 0) + 1
    print(f"{len(graded)} video(s) in '{args.state}': "
          + "  ".join(f"{k}={v}" for k, v in sorted(by_v.items())))
    promote = [g for g in graded if g[2] == "admit"] if args.auto_admit else []
    print(f"would write scores to {len(graded)}"
          + (f", and promote {len(promote)} to approved" if args.auto_admit else ""))
    for r, score, verdict, flags in graded[:15]:
        print(f"  #{r['vid']:<5} {score:>5.2f} {verdict:<7} {','.join(flags) or '-'}")

    if not args.apply:
        print("\ndry run - pass 'apply' to write")
        return

    for i in range(0, len(graded), 200):
        chunk = graded[i:i + 200]
        values = ",".join(
            "({},{},{})".format(
                r["vid"], score,
                "null" if not flags else "'" + ",".join(flags).replace("'", "''") + "'")
            for r, score, verdict, flags in chunk)
        ch.psql(f'''
        update "Videos" v
           set "QualityScore" = t.score, "QualityFlags" = t.flags
          from (values {values}) as t(vid, score, flags)
         where v."Id" = t.vid;''')
    print(f"scored {len(graded)}")

    if promote:
        ids = ",".join(str(r["vid"]) for r, _, _, _ in promote)
        ch.psql(f'''update "Videos" set "ReviewState" = 'approved',
                    "ReviewedAt" = now(), "ReviewNote" = 'auto-admitted by video_gate'
                     where "Id" in ({ids});''')
        print(f"promoted {len(promote)} to approved")
    left = ch.psql(f"""select count(*) from "Videos"
                       where "ReviewState" = '{args.state}';""").strip()
    print(f"still '{args.state}': {left}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--limit", type=int)
    a.set_defaults(fn=cmd_audit)
    st = sub.add_parser("stamp")
    st.add_argument("--state", default="pending")
    st.add_argument("--auto-admit", action="store_true")
    st.add_argument("apply", nargs="?")
    st.set_defaults(fn=cmd_stamp)
    c = sub.add_parser("check")
    c.add_argument("ytid")
    c.add_argument("dance", nargs="?")
    c.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
