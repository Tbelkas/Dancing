"""
gate_tune.py - work out where the intake gate's thresholds actually belong.

    python scripts/gate_tune.py coverage          what evidence the gate is working from
    python scripts/gate_tune.py label [--n 60]    build a labelling worksheet
    python scripts/gate_tune.py curve             precision/recall against the labels
    python scripts/gate_tune.py suggest           the thresholds the labels imply

WHY
---
0.65 (admit) and 0.35 (reject) were picked before anything had been scored. Run over
prod they put 1136 of 1153 videos in "admit" and one in "reject". A gate that admits
98.5% is not discriminating; it is a formality.

But the numbers were never the real problem. When those thresholds were set, only 142
of 1153 rows had tier-2 evidence - 883 were graded on yt-dlp metadata alone and 128 on
the database row alone. A video scores 1.0 when nothing has looked at it, so most of
that 98.5% was ignorance wearing the costume of confidence. Retuning thresholds against
scores like that would only calibrate the gate to its own blind spot, which is why this
script refuses to suggest anything until coverage is real.

LABELS
------
A threshold is a claim about what a person would call good. That needs labels, and
labels are a human's to give. `label` builds a worksheet of the most informative videos
- the ones nearest the current boundaries, where a threshold move actually changes the
verdict - and writes _proto/gate_labels.json for a person to fill in with good/bad.

Entries carry "by": "human" or "auto". Auto-labels come only from evidence that is not
in dispute (a dead video, a Short filed as a tutorial) and are reported separately, so
a curve drawn mostly from auto-labels is visibly that.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import chip_health as ch     # noqa: E402
import video_gate as vg      # noqa: E402

ROOT = ch.ROOT
PROTO = os.path.join(ROOT, "_proto")
LABELS = os.path.join(PROTO, "gate_labels.json")


def _read(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _write(p, o):
    tmp = p + ".tmp"
    json.dump(o, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def graded_rows():
    raw = json.loads(ch.psql(vg.FETCH).strip() or "[]")
    out = []
    for r in raw:
        meta = vg.load_meta(r["ytid"]) if r["platform"] == "youtube" else None
        sig = vg.load_sig(r["ytid"]) if r["platform"] == "youtube" else None
        score, verdict, flags, tier = vg.grade(r, meta, sig)
        out.append({**r, "score": score, "verdict": verdict,
                    "flags": flags, "tier": tier})
    return out


# ------------------------------------------------------------------ coverage

def cmd_coverage(args):
    """Coverage of the APPROVED catalogue, which is what a threshold governs.

    Measuring across every row instead makes the number meaningless while discovery is
    running: each newly-inserted pending video arrives at tier 0, so a run that inserts
    400 candidates drops "coverage" by a third without a single approved video having
    become less understood. The denominator has to be the thing being calibrated.
    """
    allrows = graded_rows()
    rows = [r for r in allrows if r["state"] == "approved"]
    pending = [r for r in allrows if r["state"] != "approved"]

    tiers = {0: 0, 1: 0, 2: 0}
    for r in rows:
        tiers[r["tier"]] += 1
    n = len(rows) or 1
    t2 = tiers[2] / n
    print(f"{len(rows)} approved videos (plus {len(pending)} held in review, "
          "excluded - they are not what a threshold governs)")
    print(f"  tier 0 (database row only) : {tiers[0]:>5}  {tiers[0]/n:>6.1%}")
    print(f"  tier 1 (+ yt-dlp metadata) : {tiers[1]:>5}  {tiers[1]/n:>6.1%}")
    print(f"  tier 2 (+ transcript)      : {tiers[2]:>5}  {t2:>6.1%}")
    ceiling = sum(1 for r in rows if r["score"] >= 0.999)
    print(f"\n  scoring exactly 1.0: {ceiling} ({ceiling/n:.1%})"
          "  <- mostly videos nothing has looked at, not videos known to be good")
    print(f"\ntier-2 coverage is {'sufficient' if t2 >= 0.75 else 'NOT sufficient'} "
          "for a retune (want >= 75%).")
    if t2 < 0.75:
        print("  run: python scripts/tier2_backfill.py")
    return t2


# --------------------------------------------------------------------- label

def informative(rows, n):
    """The videos where moving a threshold would change the answer.

    Sampling uniformly would spend the labelling budget on the uncontested middle of a
    pile that is 98% "admit". What decides a boundary is the rows nearest it.
    """
    scored = sorted(rows, key=lambda r: abs(r["score"] - vg.ADMIT))
    near_admit = scored[:n // 2]
    scored = sorted(rows, key=lambda r: abs(r["score"] - vg.REVIEW))
    near_reject = scored[:n // 4]
    # A few from the top, or the curve has no way to see a false negative.
    top = sorted(rows, key=lambda r: -r["score"])[:n - len(near_admit) - len(near_reject)]
    out, seen = [], set()
    for r in near_admit + near_reject + top:
        if r["vid"] in seen:
            continue
        seen.add(r["vid"])
        out.append(r)
    return out


def cmd_label(args):
    rows = graded_rows()
    labels = _read(LABELS, {})
    picks = informative(rows, args.n)
    added = 0
    for r in picks:
        k = str(r["vid"])
        if k in labels:
            continue
        labels[k] = {"ytid": r["ytid"], "dance": r["dance"], "title": r["title"],
                     "score": r["score"], "tier": r["tier"], "flags": r["flags"],
                     "url": f"https://youtu.be/{r['ytid']}",
                     "label": None, "by": None, "note": ""}
        added += 1
    _write(LABELS, labels)
    todo = sum(1 for v in labels.values() if v["label"] is None)
    print(f"worksheet: {len(labels)} entries ({added} new), {todo} unlabelled")
    print(f"  {LABELS}")
    print('  set "label" to "good" or "bad" and "by" to "human".')


# --------------------------------------------------------------------- curve

def labelled():
    return [v for v in _read(LABELS, {}).values() if v.get("label") in ("good", "bad")]


def cmd_curve(args):
    lab = labelled()
    if not lab:
        print("no labels yet - run 'label' and fill in the worksheet")
        return
    human = sum(1 for v in lab if v.get("by") == "human")
    print(f"{len(lab)} labelled ({human} by hand, {len(lab)-human} auto)")
    if human < len(lab) * 0.5:
        print("  WARNING: mostly auto-labels. The curve below describes the auto-rule,")
        print("  not a person's judgement. Treat it as a sanity check, not a decision.")

    print(f"\n  {'thr':>5} {'admit':>6} {'kept-bad':>9} {'lost-good':>10} "
          f"{'precision':>10} {'recall':>7}")
    best = None
    for i in range(0, 21):
        thr = i / 20
        tp = sum(1 for v in lab if v["label"] == "good" and v["score"] >= thr)
        fp = sum(1 for v in lab if v["label"] == "bad" and v["score"] >= thr)
        fn = sum(1 for v in lab if v["label"] == "good" and v["score"] < thr)
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        if best is None or f1 > best[1]:
            best = (thr, f1, prec, rec)
        print(f"  {thr:>5.2f} {tp+fp:>6} {fp:>9} {fn:>10} {prec:>10.3f} {rec:>7.3f}")
    print(f"\n  best F1 at {best[0]:.2f} (F1 {best[1]:.3f}, "
          f"precision {best[2]:.3f}, recall {best[3]:.3f})")
    print(f"  current admit threshold: {vg.ADMIT}")


def cmd_suggest(args):
    t2 = cmd_coverage(args)
    print()
    lab = labelled()
    if t2 < 0.75:
        print("Not suggesting thresholds: the gate is still mostly guessing.")
        return
    if len(lab) < 40:
        print(f"Not suggesting thresholds: {len(lab)} labels is too few to move a "
              "boundary on. Want 40+.")
        return
    cmd_curve(args)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coverage"); c.set_defaults(fn=cmd_coverage)
    l = sub.add_parser("label"); l.add_argument("--n", type=int, default=60)
    l.set_defaults(fn=cmd_label)
    u = sub.add_parser("curve"); u.set_defaults(fn=cmd_curve)
    s = sub.add_parser("suggest"); s.add_argument("--n", type=int, default=60)
    s.set_defaults(fn=cmd_suggest)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
