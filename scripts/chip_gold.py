"""
chip_gold.py — the eval set. Without this, "the chips got better" is unfalsifiable.

    python scripts/chip_gold.py auto [--n 60]     build gold from creator chapters
    python scripts/chip_gold.py select [--n 30]   pick a set for HAND review (optional)
    python scripts/chip_gold.py status            how much is reviewed
    python scripts/chip_gold.py baseline          score today's prod chips against gold
    python scripts/chip_gold.py score <file.json> score a candidate run against gold

Two sources of ground truth, and the free one carries most of the weight:

  chapters  The video creator's own chapter markers. A human watched their own video,
            decided where each section starts and named it -- which is exactly the
            label we want. Free, already cached, 226 videos available. Scored HELD
            OUT: the pipeline is forbidden to read the chapters for these videos and
            must infer from transcript/audio alone, or F1 is trivially 1.0. That
            hold-out is the whole validity of this set, so entries carry
            "holdout": true for any stage that builds candidates.
  human     Hand-marked in the dashboard's Gold tab. Only worth the time for the hard
            tier with no chapters AND no captions (montages, non-English, TikTok),
            where nothing free exists. A handful, not thirty.

Hand-review entries live in _proto/gold/<vid>.json, prefilled with whatever prod has now so
reviewing means correcting rather than authoring from scratch. An entry only counts
once "reviewed": true — a stub scored against itself would report a perfect 1.0 and
tell you nothing.

Metric: boundary F1 at +/-TOL seconds, plus a token-overlap proxy for label quality.
The trivial t=0 boundary is excluded from both sides; every chip set has it, and
counting it inflates F1 by a flat margin that hides real movement.
"""
import argparse
import json
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "_proto")
GOLD = os.path.join(PROTO, "gold")
HEALTH = os.path.join(PROTO, "chip_health.json")

TOL = 3  # seconds; a boundary this close to a gold boundary counts as a hit

STOP = {"the", "a", "an", "and", "to", "of", "with", "for", "your", "you", "it",
        "in", "on", "into", "up", "&"}


# ------------------------------------------------------------ signal detection

def signal_of(r):
    """What text signal exists for this video: chapters / captions / none / nonyt."""
    if r["platform"] != "youtube":
        return "nonyt"
    meta = os.path.join(PROTO, f"{r['ytid']}.json")
    if os.path.exists(meta):
        try:
            d = json.load(open(meta, encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        if len(d.get("chapters") or []) >= 3:
            return "chapters"
        auto = (d.get("automatic_captions") or {})
        subs = (d.get("subtitles") or {})
        if any(k.startswith("en") for k in list(auto) + list(subs)):
            return "captions"
        return "none"
    vtt = glob.glob(os.path.join(PROTO, f"sub_{r['ytid']}.*.vtt"))
    if vtt and sum(1 for l in open(vtt[0], encoding="utf-8", errors="ignore")
                   if "-->" in l) >= 20:
        return "captions"
    return "unknown"


def channel_of(r):
    """Who made it. Capping per channel stops the eval from measuring how well we
    reproduce one creator's chaptering habits instead of chaptering in general."""
    meta = os.path.join(PROTO, f"{r['ytid']}.json")
    if os.path.exists(meta):
        try:
            d = json.load(open(meta, encoding="utf-8"))
            ch = d.get("channel") or d.get("uploader") or d.get("uploader_id")
            if ch:
                return "ch:" + str(ch).strip().lower()
        except (OSError, ValueError):
            pass
    # "How to Moonwalk ... | Mihran Kirakosian" -> the trailing credit is the channel
    m = re.search(r"[|–—]\s*([^|–—]{3,40})\s*$", r.get("title") or "")
    if m:
        return "t:" + m.group(1).strip().lower()
    return f"v:{r['vid']}"  # unknown: unique, so it never triggers the cap


MAX_PER_CHANNEL = 2


def bucket_of(r):
    if not r["n"]:
        return "none"
    if r["score"] < 0.35:
        return "poor"
    if r["score"] < 0.65:
        return "weak"
    return "ok"


# ------------------------------------------------------------------- selection

QUOTA = {"none": 8, "poor": 7, "weak": 8, "ok": 7}


def cmd_select(args):
    health = json.load(open(HEALTH, encoding="utf-8"))
    rows = health["videos"]
    for r in rows:
        r["bucket"] = bucket_of(r)
        r["signal"] = signal_of(r)

    quota = dict(QUOTA)
    if args.n != 30:
        scale = args.n / 30
        quota = {k: max(1, round(v * scale)) for k, v in quota.items()}

    picked, seen_yt, chan = [], set(), {}
    for b, want in quota.items():
        pool = [r for r in rows if r["bucket"] == b]
        # Group by signal so the set doesn't end up all-chapters, then round-robin
        # the highest-priority video from each signal group until the quota is met.
        groups = {}
        for r in sorted(pool, key=lambda x: -x["priority"]):
            groups.setdefault(r["signal"], []).append(r)
        order = sorted(groups, key=lambda k: -len(groups[k]))
        took = 0
        while took < want and any(groups[k] for k in order):
            for k in order:
                if took >= want:
                    break
                while groups[k]:
                    r = groups[k].pop(0)
                    if r["ytid"] in seen_yt:
                        continue  # same source clip twice teaches nothing
                    c = channel_of(r)
                    if chan.get(c, 0) >= MAX_PER_CHANNEL:
                        continue
                    seen_yt.add(r["ytid"])
                    chan[c] = chan.get(c, 0) + 1
                    r["channel"] = c
                    picked.append(r)
                    took += 1
                    break
    os.makedirs(GOLD, exist_ok=True)

    fresh = 0
    for r in picked:
        path = os.path.join(GOLD, f"{r['vid']}.json")
        if os.path.exists(path):
            continue
        segs = prod_sections(r["vid"])
        json.dump({
            "vid": r["vid"], "ytid": r["ytid"], "platform": r["platform"],
            "title": r["title"], "dance": r["dance"], "dur": r["dur"],
            "views": r["views"], "bucket": r["bucket"], "signal": r["signal"],
            "reviewed": False,
            "note": "",
            "prefilled_from": "prod" if segs else "empty",
            "sections": segs,
        }, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        fresh += 1

    manifest = [{k: r[k] for k in
                 ("vid", "ytid", "title", "dance", "dur", "views", "bucket", "signal")}
                for r in picked]
    json.dump(manifest, open(os.path.join(GOLD, "_manifest.json"), "w",
                             encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"selected {len(picked)} videos ({fresh} new stubs) -> {GOLD}")
    by_b, by_s = {}, {}
    for r in picked:
        by_b[r["bucket"]] = by_b.get(r["bucket"], 0) + 1
        by_s[r["signal"]] = by_s.get(r["signal"], 0) + 1
    print("  by health tier:", "  ".join(f"{k}={v}" for k, v in by_b.items()))
    print("  by signal     :", "  ".join(f"{k}={v}" for k, v in by_s.items()))
    print(f"  distinct channels: {len({r.get('channel') for r in picked})} "
          f"(cap {MAX_PER_CHANNEL}/channel)")
    print(f"\n  {'vid':>5}  {'tier':<5} {'signal':<9} {'dur':>5} {'views':>11}  title")
    for r in picked:
        print(f"  {r['vid']:>5}  {r['bucket']:<5} {r['signal']:<9} {r['dur']:>5} "
              f"{r['views']:>11,}  {(r['title'] or r['dance'])[:52]}")


# ------------------------------------------------- gold from creator chapters

GOLD_AUTO = os.path.join(PROTO, "gold_auto")

# Chapter lists that are not section markers: promo/link dumps, bare numbering, and
# auto-generated transcript fragments. Adopting these as truth would teach the eval
# to reproduce junk.
PROMO = re.compile(r"(subscribe|patreon|instagram|follow|link|discord|course"
                   r"|sponsor|merch|www\.|http)", re.I)
NUMBERED = re.compile(r"^(part|section|chapter|step|move)\s*\d+$"
                      r"|^(intro|outro|untitled.*)$", re.I)
ELLIPSIS = ("...", "\u2026")


UNTITLED = re.compile(r"^<\s*untitled", re.I)


def usable_chapters(d):
    """The creator's chapters as sections, or None if they are not real markers.

    The distinction that matters is human-authored vs YouTube auto-generated.
    Auto-generated chapters are transcript fragments ("starts with a grapevine")
    and make a terrible target: a proposal that names the move properly scores
    zero against them, so the eval would punish exactly the behaviour we want.
    """
    ch = [c for c in (d.get("chapters") or []) if isinstance(c, dict)]
    if len(ch) < 4:
        return None
    labels = [(c.get("title") or "").strip() for c in ch]
    n = len(labels)
    if sum(1 for l in labels if PROMO.search(l)) > n * 0.3:
        return None
    if sum(1 for l in labels if NUMBERED.match(l)) > n * 0.6:
        return None
    if sum(1 for l in labels if len(l) > 45 or l.endswith(ELLIPSIS)) > n * 0.3:
        return None
    if len({l.lower() for l in labels}) < n * 0.8:
        return None

    # Sentence fragments starting lower-case are the auto-generation signature.
    # A stray one is fine; a third of them means nobody wrote these.
    if sum(1 for l in labels if l[:1].islower()) > n * 0.3:
        return None

    # "<Untitled Chapter 1>" is YouTube's placeholder when the first chapter does
    # not start at 0:00 - an artifact on an otherwise hand-written list, not a
    # reason to throw the video away. Rename it, and only reject if there are more.
    untitled = [i for i, l in enumerate(labels) if UNTITLED.match(l)]
    if untitled == [0]:
        labels[0] = "Intro"
    elif untitled:
        return None

    # A creator who put four chapters on a 31-minute class did not really chapter
    # it. Scoring against that punishes a proposal for being more useful than the
    # original, which is the opposite of what this measures.
    dur = d.get("duration") or 0
    if dur and n / (dur / 60) < 0.25:
        return None
    out = []
    for i, c in enumerate(ch):
        start = int(c.get("start_time") or 0)
        if i + 1 < len(ch):
            end = int(ch[i + 1].get("start_time") or 0)
        else:
            end = int(d.get("duration") or 0) or None
        out.append({"start": start, "end": end, "label": labels[i]})
    return out


def cmd_auto(args):
    health = json.load(open(HEALTH, encoding="utf-8"))
    byyt = {r["ytid"]: r for r in health["videos"] if r["ytid"]}
    found = []
    for f in glob.glob(os.path.join(PROTO, "*.json")):
        yt = os.path.basename(f)[:-5]
        if yt.startswith(("sec_", "sub_", "chip_", "gold")):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        secs = usable_chapters(d)
        r = byyt.get(yt)
        if secs and r:
            found.append((r, secs, d))

    # Keep iteration cheap: the pipeline must transcribe every eval video, and all
    # 226 is 40h of footage. Stratify a subset by duration so the default stays
    # representative; --all when the full number is wanted.
    found.sort(key=lambda x: -x[0]["views"])
    if not args.all and len(found) > args.n:
        bands = {"short": [], "mid": [], "long": []}
        for r, secs, d in found:
            dur = d.get("duration") or 0
            key = "short" if dur < 300 else "mid" if dur < 900 else "long"
            bands[key].append((r, secs, d))
        picked = []
        while len(picked) < args.n and any(bands.values()):
            for k in ("short", "mid", "long"):
                if bands[k] and len(picked) < args.n:
                    picked.append(bands[k].pop(0))
        found = picked

    os.makedirs(GOLD_AUTO, exist_ok=True)
    for old in glob.glob(os.path.join(GOLD_AUTO, "*.json")):
        os.remove(old)
    for r, secs, d in found:
        json.dump({
            "vid": r["vid"], "ytid": r["ytid"], "platform": r["platform"],
            "title": r["title"], "dance": r["dance"],
            "dur": d.get("duration") or r["dur"], "views": r["views"],
            "bucket": bucket_of(r), "signal": "chapters",
            "origin": "chapters", "reviewed": True,
            # The pipeline MUST NOT read this video's own chapters while being scored.
            "holdout": True,
            "prod_source": r["source"], "prod_n": r["n"],
            "sections": secs,
        }, open(os.path.join(GOLD_AUTO, str(r["vid"]) + ".json"), "w",
                encoding="utf-8"), indent=1, ensure_ascii=False)

    hours = sum((d.get("duration") or 0) for _, _, d in found) / 3600
    print("built " + str(len(found)) + " gold entries from creator chapters -> " + GOLD_AUTO)
    print("  gold boundaries : " + str(sum(len(x) - 1 for _, x, _ in found)))
    print("  footage         : " + format(hours, ".1f") + " h")
    by = {}
    for r, _, _ in found:
        by[r["source"]] = by.get(r["source"], 0) + 1
    print("  prod source mix : " + "  ".join(k + "=" + str(v) for k, v in sorted(by.items())))
    print()
    print("  Held out: a stage scoring against these must not read their chapters.")


def prod_sections(vid):
    """Current prod chips for one video, from the health snapshot's source data."""
    return _prod_map().get(vid, [])


_PROD = None


def _prod_map():
    """vid -> [{start,end,label}] straight from the DB, for prefill and baseline."""
    global _PROD
    if _PROD is None:
        import chip_health as ch
        raw = ch.psql("""
        select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
          select s."VideoId" as "vid", s."StartTime" as "start",
                 s."EndTime" as "end", s."Label" as "label"
          from "VideoSegments" s order by s."VideoId", s."StartTime", s."Id"
        ) t;""")
        _PROD = {}
        for row in json.loads(raw.strip() or "[]"):
            _PROD.setdefault(row["vid"], []).append(
                {"start": row["start"], "end": row["end"], "label": row["label"]})
    return _PROD


# --------------------------------------------------------------------- scoring

def _starts(sections):
    """Boundary starts, excluding the trivial 0 that every chip set has."""
    return sorted({s["start"] for s in sections if s["start"] > TOL})


def _toks(label):
    return {w for w in re.findall(r"[a-z0-9']+", (label or "").lower())
            if w not in STOP}


def boundary_f1(pred, gold, tol=TOL):
    """Greedy 1-1 match of predicted boundaries to gold within tol seconds."""
    p, g = _starts(pred), _starts(gold)
    if not p and not g:
        return 1.0, 1.0, 1.0, 0
    unused = list(g)
    hits = 0
    for t in p:
        best, bd = None, tol + 1
        for u in unused:
            d = abs(u - t)
            if d <= tol and d < bd:
                best, bd = u, d
        if best is not None:
            unused.remove(best)
            hits += 1
    prec = hits / len(p) if p else 0.0
    rec = hits / len(g) if g else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return f1, prec, rec, hits


def label_overlap(pred, gold, tol=TOL):
    """Token-F1 of labels on boundaries that matched. A cheap proxy for the judge:
    it rewards naming the same move, not identical phrasing."""
    gmap = {s["start"]: s.get("label", "") for s in gold}
    scores = []
    for s in pred:
        if s["start"] <= TOL:
            continue
        near = [gs for gs in gmap if abs(gs - s["start"]) <= tol]
        if not near:
            continue
        gl = _toks(gmap[min(near, key=lambda x: abs(x - s["start"]))])
        pl = _toks(s.get("label", ""))
        if not gl and not pl:
            scores.append(1.0)
            continue
        inter = len(gl & pl)
        if not inter:
            scores.append(0.0)
            continue
        prec, rec = inter / len(pl), inter / len(gl)
        scores.append(2 * prec * rec / (prec + rec))
    return sum(scores) / len(scores) if scores else 0.0


def load_gold(reviewed_only=True, origin=None):
    """Merge hand-reviewed entries with the creator-chapter set. Hand review wins a
    collision: a human who actually watched outranks the creator's own markers."""
    out = {}
    for src_dir, org in ((GOLD_AUTO, "chapters"), (GOLD, "human")):
        for path in glob.glob(os.path.join(src_dir, "*.json")):
            if os.path.basename(path).startswith("_"):
                continue
            try:
                d = json.load(open(path, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            d.setdefault("origin", org)
            if reviewed_only and not d.get("reviewed"):
                continue
            if origin and d["origin"] != origin:
                continue
            out[d["vid"]] = d
    return out


def evaluate(candidate, gold, title, detail=False):
    """candidate: vid -> [sections]. Aggregates, then breaks down by group."""
    if not gold:
        print("No gold entries yet. Build the free set with:")
        print("  python scripts/chip_gold.py auto")
        return
    print()
    print(title + "   (tolerance +/-" + str(TOL) + "s, t=0 boundary excluded)")

    rows = []
    for vid, g in sorted(gold.items()):
        pred = candidate.get(vid, [])
        f1, pr, rc, _ = boundary_f1(pred, g["sections"])
        lo = label_overlap(pred, g["sections"])
        rows.append({
            "vid": vid, "f1": f1, "prec": pr, "rec": rc, "lab": lo,
            "np": len(pred), "ng": len(g["sections"]),
            "origin": g.get("origin", "?"),
            "prod_source": g.get("prod_source", g.get("bucket", "?")),
            # Prod chips copied from the very chapters we score against cannot fail;
            # flagging them keeps the headline honest.
            "adopted": f1 >= 0.9 and g.get("origin") == "chapters",
        })

    if detail:
        print()
        print("  {:>5}  {:>5} {:>5} {:>5}  {:>5}  {:>4} {:>4}  {:<10} {}".format(
            "vid", "F1", "prec", "rec", "label", "pred", "gold", "origin", "prod"))
        for r in rows:
            print("  {:>5}  {:>5.2f} {:>5.2f} {:>5.2f}  {:>5.2f}  {:>4} {:>4}  "
                  "{:<10} {}{}".format(
                      r["vid"], r["f1"], r["prec"], r["rec"], r["lab"], r["np"],
                      r["ng"], r["origin"], r["prod_source"],
                      "  (adopted)" if r["adopted"] else ""))

    def agg(rs, label):
        if rs:
            print("  {:<27} n={:>3}   F1 {:.3f}   label {:.3f}".format(
                label, len(rs), sum(x["f1"] for x in rs) / len(rs),
                sum(x["lab"] for x in rs) / len(rs)))

    print()
    print("  " + "-" * 62)
    agg(rows, "ALL")
    print()
    for org in sorted({r["origin"] for r in rows}):
        agg([r for r in rows if r["origin"] == org], "origin: " + org)
    print()
    for src in sorted({r["prod_source"] for r in rows}):
        agg([r for r in rows if r["prod_source"] == src], "prod source: " + str(src))

    adopted = [r for r in rows if r["adopted"]]
    if adopted:
        print()
        agg(adopted, "chapter-adopted (trivial)")
        agg([r for r in rows if not r["adopted"]], "NOT adopted (informative)")
        print()
        print("  " + str(len(adopted)) + " video(s) score >=0.9 because prod copied the")
        print("  same chapters this set scores against. Read the NOT-adopted line as")
        print("  the real baseline; the headline is flattered by them.")


def cmd_status(args):
    all_g = load_gold(reviewed_only=False)
    done = [d for d in all_g.values() if d.get("reviewed")]
    print(f"gold entries: {len(all_g)}   reviewed: {len(done)}   "
          f"remaining: {len(all_g) - len(done)}")
    if all_g:
        by = {}
        for d in all_g.values():
            k = (d.get("bucket"), bool(d.get("reviewed")))
            by[k] = by.get(k, 0) + 1
        for b in ("none", "poor", "weak", "ok"):
            print(f"  {b:<5} reviewed {by.get((b,True),0)} / "
                  f"{by.get((b,True),0)+by.get((b,False),0)}")
    if not done:
        print("\nNothing reviewed yet. Open the dashboard's Gold tab to chip them:")
        print("  python scripts/chip_ui.py")


def cmd_baseline(args):
    evaluate(_prod_map(), load_gold(), "BASELINE - today's prod chips vs gold",
             detail=getattr(args, "detail", False))


def cmd_score(args):
    cand = json.load(open(args.file, encoding="utf-8"))
    if isinstance(cand, dict) and "videos" in cand:
        cand = {v["vid"]: v.get("sections", []) for v in cand["videos"]}
    else:
        cand = {int(k): v for k, v in cand.items()}
    evaluate(cand, load_gold(), "CANDIDATE - " + os.path.basename(args.file) + " vs gold",
             detail=getattr(args, "detail", False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select"); s.add_argument("--n", type=int, default=30)
    s.set_defaults(fn=cmd_select)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    a = sub.add_parser("auto")
    a.add_argument("--n", type=int, default=60)
    a.add_argument("--all", action="store_true")
    a.set_defaults(fn=cmd_auto)
    b = sub.add_parser("baseline")
    b.add_argument("--detail", action="store_true")
    b.set_defaults(fn=cmd_baseline)
    s = sub.add_parser("score"); s.add_argument("file")
    s.add_argument("--detail", action="store_true"); s.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
