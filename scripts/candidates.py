"""
candidates.py [ytid ...] [--gold] [--eval] [--force]

Stage 02: turn the raw signals into ONE scored list of places a section could
start, so the model that follows picks a candidate id instead of inventing a
timecode. Invented timestamps are the dominant failure mode in transcript-driven
chaptering; choosing from a fixed list removes the failure instead of checking
for it afterwards.

    python scripts/candidates.py --gold --eval    build, then measure recall
    python scripts/candidates.py FaLYQUa1PDg      one video

Reads  _proto/sig_<ytid>.json      (stage 01)
Writes _proto/cand_<ytid>.json

Signals merged, each with a weight reflecting how much it means on its own:

  chapter       the creator said a section starts here            3.0
  desc-stamp    a timestamp list in the description               2.5
  cue           a discourse cue: "now we", "five six seven eight" 1.5
  music-onset   speech stops and stays stopped                    1.2
  scene         the video cuts                                    1.0
  silence       a pause long enough to be deliberate              0.5

HOLD-OUT
--------
For a video in the eval set (gold entry with "holdout": true) the chapter AND
desc-stamp signals are dropped. Both are authored by the creator, and the eval
scores against exactly those chapters - feeding them back in would score the
pipeline on its ability to copy the answer. Description timestamps count as the
same leak, because that is frequently where YouTube's chapters come from.

--eval reports candidate RECALL: the share of gold boundaries that have any
candidate within the tolerance. That is the ceiling on stage 03 - the model can
only ever pick from what this produced, so a boundary missing here is a boundary
that can never be found.
"""
import argparse
import glob
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
import chip_runstate as rs  # noqa: E402

PROTO = rs.PROTO
GOLD_AUTO = os.path.join(PROTO, "gold_auto")
GOLD = os.path.join(PROTO, "gold")

CLUSTER = 2.0   # candidates within this many seconds are the same boundary
TOL = 3         # matches chip_gold.TOL

# Deliberately small. An earlier 12s floor thinned "confetti" away and took real
# boundaries with it - recall here is a hard ceiling on everything downstream, and
# precision is stage 03's job, not this one's. Over-supplying is nearly free;
# under-supplying is unrecoverable.
MIN_GAP = 3

WEIGHTS = {"chapter": 3.0, "desc-stamp": 2.5, "cue": 1.5,
           "music-onset": 1.2, "scene": 1.0, "silence": 0.5,
           # Every utterance start is a place a section COULD begin - a section
           # starts when someone starts saying something. Weighted near zero so it
           # never outranks real evidence, but present so the boundary is reachable.
           "segment-start": 0.2}

# What an instructor says when they move on. Ordered roughly by how strongly each
# implies a NEW section rather than a continuation.
CUES = [
    (r"\b(five,? ?six,? ?seven,? ?eight|5,? ?6,? ?7,? ?8)\b", 1.6),
    (r"\b(let'?s (go|try|add|do|start)|here we go)\b", 1.5),
    (r"\b(next (one|move|step|part)?|moving on|after (that|this))\b", 1.5),
    (r"\b(now (we|i|you|let'?s)|so now|okay so|alright so)\b", 1.3),
    (r"\b(variation|number (one|two|three|four|five|\d+))\b", 1.5),
    (r"\b(first|second|third|fourth|fifth)( (one|move|step|part))?\b", 1.2),
    (r"\b(with (the )?music|to the music|full speed|from the top)\b", 1.6),
    (r"\b(break (it|this) down|slow(ly)? (it )?down|step by step)\b", 1.4),
    (r"\b(put (it|them) together|all together|combine)\b", 1.4),
    (r"\b(one more time|again from|repeat)\b", 1.0),
    (r"\b(welcome back|what'?s up|hey guys|in (today'?s|this) video)\b", 1.2),
    (r"\b(thanks for watching|see you|don'?t forget to|subscribe)\b", 1.1),
]
CUES = [(re.compile(p, re.I), w) for p, w in CUES]


def sig_path(y):
    return os.path.join(PROTO, f"sig_{y}.json")


def cand_path(y):
    return os.path.join(PROTO, f"cand_{y}.json")


def gold_entries():
    """vid/ytid -> gold entry, for hold-out and for --eval."""
    out = {}
    for d in (GOLD_AUTO, GOLD):
        for p in glob.glob(os.path.join(d, "*.json")):
            if os.path.basename(p).startswith("_"):
                continue
            e = rs._read(p, None)
            if e and e.get("ytid"):
                out[e["ytid"]] = e
    return out


# ------------------------------------------------------------------ building

def raw_signals(sig, holdout):
    """(time, source, weight, note) for every signal the video offers."""
    out = []

    if not holdout:
        for c in sig.get("chapters") or []:
            out.append((float(c["start"]), "chapter", WEIGHTS["chapter"],
                        c.get("label", "")))
        for d in sig.get("desc_timestamps") or []:
            out.append((float(d["start"]), "desc-stamp", WEIGHTS["desc-stamp"],
                        d.get("label", "")))

    for t in sig.get("scenes") or []:
        out.append((float(t), "scene", WEIGHTS["scene"], ""))

    # The END of a silence is the boundary: the pause is before the new thing,
    # so the new section starts when the talking resumes.
    for s in sig.get("silence") or []:
        if s["end"] - s["start"] >= 0.8:
            out.append((float(s["end"]), "silence", WEIGHTS["silence"], ""))

    segs = (sig.get("asr") or {}).get("segments") or []
    for i, s in enumerate(segs):
        # Base coverage. A gap before this utterance makes it a likelier start.
        gap = s["start"] - segs[i - 1]["end"] if i else 0.0
        out.append((float(s["start"]), "segment-start",
                    WEIGHTS["segment-start"] + min(0.6, gap * 0.3),
                    (s.get("text") or "").strip()[:70]))
    for s in segs:
        text = s.get("text") or ""
        for rx, w in CUES:
            m = rx.search(text)
            if m:
                out.append((float(s["start"]), "cue", w, text.strip()[:70]))
                break

    # Speech stops and stays stopped: the practice-with-music stretch.
    dens = sig.get("density") or []
    for i in range(1, len(dens)):
        prev, cur = dens[i - 1]["v"], dens[i]["v"]
        nxt = dens[i + 1]["v"] if i + 1 < len(dens) else cur
        if prev > 0.35 and cur < 0.15 and nxt < 0.2:
            out.append((float(dens[i]["t"]), "music-onset",
                        WEIGHTS["music-onset"], "speech drops out"))
    return out


def cluster(raw, dur):
    """Collapse near-simultaneous signals into one candidate boundary.

    Independent agreement is the point: a scene cut that lands on a discourse cue
    that lands at the end of a pause is a real boundary; any one of them alone is
    a guess.
    """
    raw = sorted(raw, key=lambda x: x[0])
    groups, cur = [], []
    for item in raw:
        if cur and item[0] - cur[0][0] <= CLUSTER:
            cur.append(item)
        else:
            if cur:
                groups.append(cur)
            cur = [item]
    if cur:
        groups.append(cur)

    out = []
    for g in groups:
        srcs = {}
        for t, src, w, note in g:
            if src not in srcs or w > srcs[src][0]:
                srcs[src] = (w, note)
        # Anchor on the highest-weight signal in the cluster rather than the mean:
        # a chapter marker's time is authoritative, a silence edge is fuzzy.
        best = max(g, key=lambda x: x[2])
        score = round(sum(w for w, _ in srcs.values()), 2)
        out.append({
            "t": round(best[0], 2),
            "score": score,
            "sources": sorted(srcs),
            "notes": [n for _, n in srcs.values() if n][:3],
        })

    out = [c for c in out if 0 <= c["t"] <= (dur or 1e9)]
    out.sort(key=lambda c: c["t"])

    # Thin out near-neighbours that survived clustering, keeping the stronger.
    thinned = []
    for c in out:
        if thinned and c["t"] - thinned[-1]["t"] < MIN_GAP:
            if c["score"] > thinned[-1]["score"]:
                thinned[-1] = c
            continue
        thinned.append(c)
    for i, c in enumerate(thinned):
        c["id"] = i
    return thinned


def build(ytid, gold, force=False):
    if os.path.exists(cand_path(ytid)) and not force:
        return "cached", None
    sig = rs._read(sig_path(ytid), None)
    if not sig:
        return "no-signals", None

    entry = gold.get(ytid)
    holdout = bool(entry and entry.get("holdout"))
    dur = sig.get("dur") or 0

    cands = cluster(raw_signals(sig, holdout), dur)
    doc = {
        "ytid": ytid, "dur": dur, "holdout": holdout,
        "n": len(cands),
        "suggested_sections": max(3, min(14, round((dur or 300) / 90))),
        "candidates": cands,
    }
    json.dump(doc, open(cand_path(ytid), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return "ok", doc


# -------------------------------------------------------------------- eval

def evaluate(gold):
    """Candidate recall: can the boundaries even be reached from this list?"""
    rows = []
    for ytid, e in sorted(gold.items()):
        doc = rs._read(cand_path(ytid), None)
        if not doc:
            continue
        gts = sorted({s["start"] for s in e["sections"] if s["start"] > TOL})
        if not gts:
            continue
        cts = [c["t"] for c in doc["candidates"]]
        hit = sum(1 for g in gts if any(abs(c - g) <= TOL for c in cts))
        # How well does raw candidate STRENGTH rank the true boundaries? If the
        # top-N by score are the right ones, stage 03 has an easy job.
        top = sorted(doc["candidates"], key=lambda c: -c["score"])[:len(gts)]
        tophit = sum(1 for g in gts if any(abs(c["t"] - g) <= TOL for c in top))
        rows.append({"ytid": ytid, "gold": len(gts), "cands": len(cts),
                     "recall": hit / len(gts), "top_prec": tophit / len(gts),
                     "holdout": doc.get("holdout")})

    if not rows:
        print("nothing to evaluate - build candidates for gold videos first")
        return
    n = len(rows)
    print(f"\nCANDIDATE RECALL over {n} gold videos (tolerance +/-{TOL}s)")
    print(f"  gold boundaries      : {sum(r['gold'] for r in rows)}")
    print(f"  candidates generated : {sum(r['cands'] for r in rows)}"
          f"  (median {sorted(r['cands'] for r in rows)[n//2]} per video)")
    print(f"  RECALL               : {sum(r['recall'] for r in rows)/n:.3f}"
          "   <- ceiling for stage 03")
    print(f"  top-N by score alone : {sum(r['top_prec'] for r in rows)/n:.3f}"
          "   <- what pure ranking gets you")
    worst = sorted(rows, key=lambda r: r["recall"])[:8]
    print("\n  weakest recall:")
    for r in worst:
        print(f"    {r['ytid']:<14} recall {r['recall']:.2f}  "
              f"{r['gold']:>3} gold  {r['cands']:>3} candidates")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ytids", nargs="*")
    ap.add_argument("--gold", action="store_true")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    gold = gold_entries()
    ids = list(args.ytids)
    if args.gold or args.eval:
        ids += [y for y in gold if os.path.exists(sig_path(y))]
    ids = list(dict.fromkeys(ids))
    if not ids:
        ap.error("nothing to do: pass ytids, --gold, or --eval")

    counts = {}
    held = 0
    for ytid in ids:
        status, doc = build(ytid, gold, force=args.force)
        counts[status] = counts.get(status, 0) + 1
        if doc and doc.get("holdout"):
            held += 1
    print("  ".join(f"{k}={v}" for k, v in sorted(counts.items()))
          + f"   (chapters withheld on {held})")

    if args.eval:
        evaluate({y: e for y, e in gold.items() if e.get("sections")})


if __name__ == "__main__":
    main()
