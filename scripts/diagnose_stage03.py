"""
diagnose_stage03.py [--variant control]

Why stage 03 loses, in three measurements. Run after a sweep to see what to fix
next instead of guessing at prompt wording.

    python scripts/diagnose_stage03.py --variant control

1. CEILING vs ACHIEVED. Candidate recall is the ceiling on stage 03 - a boundary
   not in the candidate list cannot be chosen. Comparing it against what the model
   actually recalls separates "unreachable" from "reachable but not picked".

2. TOLERANCE CURVE. Boundary F1 is scored at +/-3s. If the model's boundaries sit
   6-10s off they score zero while being perfectly usable as a chip you click to
   jump. Scoring prod and the model at several tolerances says whether the metric
   is hiding a real result - and prod barely moves, because its chips are copied
   from the same chapters gold is made of, so a loosening helps the model far more
   than it helps prod. If the model still loses at +/-15s, the metric is not the
   problem.

3. STRENGTH AS A RANKER. Candidates carry a strength score. If the true boundaries
   were near the top of it, the fix would be to hand the model a shorter list.
   Recall at top-N/2N/3N against the full ceiling says whether that is true.

Read-only: no database writes, no proposal writes, and it does not rebuild
candidate files (`candidates.py --eval` would, and the sweep is reading them).
"""
import argparse
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import chip_runstate as rs  # noqa: E402
import candidates as cd  # noqa: E402
import chip_gold as cg  # noqa: E402
import score_sweep as ss  # noqa: E402

TOL = 3
TOLERANCES = (3, 5, 8, 10, 15)


def _gold_starts(g):
    return sorted({s["start"] for s in g["sections"] if s["start"] > TOL})


def load_proposals(variant, y2v, gold):
    """vid -> sections, from _proto/sweep/<variant>/ (or _proto/prop_*.json)."""
    out = {}
    d = os.path.join(rs.PROTO, "sweep", variant)
    if os.path.isdir(d):
        for name in os.listdir(d):
            if not name.startswith("prop_"):
                continue
            vid = y2v.get(name[5:-5])
            p = rs._read(os.path.join(d, name), None)
            if vid in gold and p and p.get("sections"):
                out[vid] = p["sections"]
    return out


def part1_ceiling(pred, gold, y2v, adopted):
    print("\n1. CEILING vs ACHIEVED  (tolerance +/-%ds)" % TOL)
    v2y = {v: y for y, v in y2v.items()}
    ceils, recs, precs, over = [], [], [], []
    for vid, secs in sorted(pred.items()):
        c = rs._read(cd.cand_path(v2y.get(vid, "")), None)
        gts = _gold_starts(gold[vid])
        if not c or not c.get("candidates") or not gts:
            continue
        cts = [x["t"] for x in c["candidates"]]
        ceils.append(sum(1 for t in gts if any(abs(x - t) <= TOL for x in cts)) / len(gts))
        _, pr, rc, _ = cg.boundary_f1(secs, gold[vid]["sections"])
        recs.append(rc)
        precs.append(pr)
        over.append(len(secs) / len(gts))
    if not ceils:
        print("   no proposals yet")
        return
    n = len(ceils)
    print(f"   videos                 : {n}")
    print(f"   candidate recall       : {sum(ceils)/n:.3f}   <- ceiling")
    print(f"   model recall           : {sum(recs)/n:.3f}")
    print(f"   reachable, not picked  : {sum(ceils)/n - sum(recs)/n:.3f}")
    print(f"   model precision        : {sum(precs)/n:.3f}   <- the expensive one")
    print(f"   sections vs gold       : {sum(over)/n:.2f}x  "
          f"(median {statistics.median(over):.2f}x)")


def part2_tolerance(pred, gold, adopted):
    prod = cg._prod_map()
    vids = sorted(pred)
    inf = [v for v in vids if v not in adopted]
    print(f"\n2. TOLERANCE CURVE  ({len(vids)} videos, {len(inf)} informative)")
    print(f"   {'tol':>5}  {'prod':>7} {'model':>7}   {'prod-inf':>9} {'model-inf':>9}")

    def mean(vs, src, tol):
        r = [cg.boundary_f1(src.get(v, []), gold[v]["sections"], tol=tol)[0] for v in vs]
        return sum(r) / len(r) if r else float("nan")

    for tol in TOLERANCES:
        print(f"   {tol:>4}s  {mean(vids, prod, tol):>7.3f} {mean(vids, pred, tol):>7.3f}"
              f"   {mean(inf, prod, tol):>9.3f} {mean(inf, pred, tol):>9.3f}")
    print("   prod hardly moves - its chips ARE the chapters. If the model does not")
    print("   overtake it even at +/-15s, the tolerance is not what is beating us.")


def part3_strength(gold, y2v, adopted):
    print("\n3. STRENGTH AS A RANKER")
    rows = []
    for y, vid in sorted(y2v.items()):
        if vid not in gold:
            continue
        c = rs._read(cd.cand_path(y), None)
        gts = _gold_starts(gold[vid])
        if not c or not c.get("candidates") or not gts:
            continue
        cs, N = c["candidates"], len(gts)
        byscore = sorted(cs, key=lambda x: -x["score"])

        def rec(lst):
            return sum(1 for t in gts if any(abs(x["t"] - t) <= TOL for x in lst)) / N

        rows.append({"ncand": len(cs), "inf": vid not in adopted, "all": rec(cs),
                     **{f"top{k}": rec(byscore[:k * N]) for k in (1, 2, 3, 5)}})
    if not rows:
        print("   no candidate files")
        return
    n = len(rows)
    print(f"   {n} gold videos, median {statistics.median([r['ncand'] for r in rows]):.0f} "
          f"candidates each (max {max(r['ncand'] for r in rows)})")
    for lbl, k in (("all candidates (ceiling)", "all"), ("top N (N=#gold)", "top1"),
                   ("top 2N", "top2"), ("top 3N", "top3"), ("top 5N", "top5")):
        print(f"   {lbl:<26} {sum(r[k] for r in rows)/n:.3f}")
    print("   If top-N is far below the ceiling, strength is a weak ranker: shortening")
    print("   the list by score would throw away real boundaries, and telling the model")
    print("   to trust strength is telling it to trust noise.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="control")
    args = ap.parse_args()

    gold = cg.load_gold()
    y2v = {y: e["vid"] for y, e in cd.gold_entries().items() if e.get("vid")}
    adopted = ss.adopted_vids(gold)
    pred = load_proposals(args.variant, y2v, gold)

    print(f"stage 03 diagnosis - variant '{args.variant}', "
          f"{len(pred)} proposals, {len(gold)} gold videos")
    part1_ceiling(pred, gold, y2v, adopted)
    if pred:
        part2_tolerance(pred, gold, adopted)
    part3_strength(gold, y2v, adopted)
    print()


if __name__ == "__main__":
    main()
