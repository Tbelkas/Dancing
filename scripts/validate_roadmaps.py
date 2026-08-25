"""validate_roadmaps.py — check every authored roadmap against the prod catalog.

RoadmapSeeder is deliberately forgiving: an unresolvable danceSlug, a segmentLabel that
matches nothing, or an edge naming an unknown key is skipped with a logged error rather
than failing the boot. That is the right behaviour for a Pi that must come up, but it
means a typo ships silently and only shows up as a step with no video. Run this before
deploying a roadmap change.

Checks, per file:
  - styleName resolves against Styles (case-insensitively)
  - step keys unique; no self-prerequisite; no unknown prerequisite; no cycle
  - exactly one root, and every node reachable from it
  - danceSlug resolves inside the roadmap's own style (slugs are unique per style)
  - segmentLabel matches exactly one segment on that dance's videos (ambiguous = warning,
    since the seeder silently takes the earliest)
  - every linked step ends up with at least one playable video
  - flags dances backing more than one step (progress is stored per dance, so ticking one
    such step off flips all of them at once)

And across files, for module gateways (a step's `module` naming another roadmap):
  - the named module is a roadmap file that exists
  - no step declares both a module and a danceSlug (a step is one or the other)
  - no module is claimed by two different steps (the breadcrumb needs one answer)
  - no module chain loops, and none nests deeper than MAX_MODULE_DEPTH
  - flags a module with nothing completable in it: it can never be finished, so its gateway
    would sit unlearnable forever

Detection only — never writes. Exit code 1 if anything is an error.
"""
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict

# pythonw.exe (used to run the dashboard detached) has no stdout, and an
# unguarded reconfigure() throws on import - which surfaced as an HTTP handler
# dying with an empty response rather than an error.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPSETTINGS = os.path.join(ROOT, "DancePlatform.API", "appsettings.Development.json")
RMDIR = os.path.join(ROOT, "DancePlatform.API", "Data", "Roadmaps")


def prod_conn():
    cfg = json.load(open(APPSETTINGS, encoding="utf-8-sig"))
    for v in cfg.get("ConnectionStrings", {}).values():
        if "192.168.0.197" in v:
            return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    raise SystemExit(f"No prod (192.168.0.197) connection string in {APPSETTINGS}")


def psql(sql):
    c = prod_conn()
    env = dict(os.environ)
    env["PGPASSWORD"] = c.get("Password", "")
    env["PGCLIENTENCODING"] = "UTF8"
    # SQL goes in on stdin, not via -c: labels contain em dashes, and an argv round-trip
    # through the Windows console mangles them into invalid UTF-8.
    p = subprocess.run(
        ["psql", "-h", c["Host"], "-U", c["Username"], "-d", c["Database"],
         "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"],
        input=sql, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit(2)
    return [l.split("\t") for l in p.stdout.splitlines() if l]


def check(path, styles):
    errs, warns = [], []
    rm = json.load(open(path, encoding="utf-8"))
    slug = rm.get("slug", os.path.basename(path))

    sid = styles.get(str(rm.get("styleName", "")).lower())
    if sid is None:
        return [f"styleName {rm.get('styleName')!r} is not a row in Styles"], [], rm, 0, 0

    dances = {s: int(i) for i, s in psql(
        f'select d."Id", d."Slug" from "Dances" d '
        f'join "DanceStyles" ds on ds."DanceId"=d."Id" where ds."StyleId"={sid};')}

    steps = [s for st in rm["stages"] for s in st["steps"]]
    keys = set()
    for s in steps:
        if s["key"] in keys:
            errs.append(f"duplicate key {s['key']!r}")
        keys.add(s["key"])

    graph = {s["key"]: list(s.get("requires", [])) for s in steps}
    for k, reqs in graph.items():
        for r in reqs:
            if r == k:
                errs.append(f"{k}: lists itself as a prerequisite")
            elif r not in keys:
                errs.append(f"{k}: unknown prerequisite {r!r}")

    # cycles
    state = {}

    def visit(k, stack):
        if state.get(k) == 2:
            return
        if state.get(k) == 1:
            errs.append("cycle: " + " -> ".join(stack + [k]))
            return
        state[k] = 1
        for r in graph.get(k, []):
            if r in graph:
                visit(r, stack + [k])
        state[k] = 2

    for k in graph:
        visit(k, [])

    roots = [k for k, v in graph.items() if not v]
    if not roots:
        errs.append("no root step (every step has a prerequisite)")
    elif len(roots) > 1:
        warns.append(f"{len(roots)} roots ({', '.join(roots)}) — the tree will fan from several centres")

    # reachability from the roots, following prerequisites forwards
    children = defaultdict(list)
    for k, reqs in graph.items():
        for r in reqs:
            children[r].append(k)
    seen, stack = set(roots), list(roots)
    while stack:
        for c in children[stack.pop()]:
            if c not in seen:
                seen.add(c)
                stack.append(c)
    for k in keys - seen:
        errs.append(f"{k}: unreachable from any root")

    linked = 0
    per_dance = defaultdict(list)
    for s in steps:
        ds = s.get("danceSlug")
        if not ds:
            continue
        linked += 1
        if ds not in dances:
            errs.append(f"{s['key']}: danceSlug {ds!r} is not a {rm['styleName']} dance")
            continue
        per_dance[ds].append(s["key"])
        did = dances[ds]

        vids = psql(f'select count(*) from "Videos" where "DanceId"={did} and "OwnerUserId" is null;')
        if not vids or int(vids[0][0]) == 0:
            errs.append(f"{s['key']}: dance {ds!r} has no playable video")

        lbl = s.get("segmentLabel")
        if lbl:
            hits = psql(
                f'select vs."Id" from "VideoSegments" vs join "Videos" v on v."Id"=vs."VideoId" '
                f'where v."DanceId"={did} and vs."Label"=\'{lbl.replace(chr(39), chr(39) * 2)}\';')
            if not hits:
                errs.append(f"{s['key']}: segmentLabel {lbl!r} matches no segment on {ds!r}")
            elif len(hits) > 1:
                warns.append(f"{s['key']}: segmentLabel {lbl!r} matches {len(hits)} segments on "
                             f"{ds!r} — the seeder will take the earliest")

    for ds, ks in sorted(per_dance.items()):
        if len(ks) > 1:
            warns.append(f"dance {ds!r} backs {len(ks)} steps ({', '.join(ks)}) — marking it "
                         f"learned flips all of them, since progress is per dance")

    return errs, warns, rm, len(steps), linked


# Mirrors RoadmapGraph.MaxModuleDepth. Counts the top-level path as 1, so 3 allows
# "Waacking > Posing > Screen icons" and no further.
MAX_MODULE_DEPTH = 3


def check_modules(loaded):
    """Cross-file checks for module gateways. `loaded` maps slug -> parsed roadmap."""
    errs, warns = [], []
    parent_of = {}       # module slug -> slug of the roadmap whose step claims it
    claimed_by = {}      # module slug -> "roadmap#step" that claimed it

    for slug, rm in sorted(loaded.items()):
        for step in (s for st in rm["stages"] for s in st["steps"]):
            mod = step.get("module")
            if not mod:
                continue
            where = f"{slug}#{step['key']}"
            if step.get("danceSlug"):
                errs.append(f"{where}: has both a module and a danceSlug — a step is one or the other")
                continue
            if mod not in loaded:
                errs.append(f"{where}: names module {mod!r}, which is not a roadmap file")
                continue
            if mod in claimed_by:
                errs.append(f"{where}: module {mod!r} is already claimed by {claimed_by[mod]}")
                continue
            claimed_by[mod] = where
            parent_of[mod] = slug

    # Cycles and depth, walking upwards from each module.
    for mod in sorted(parent_of):
        seen, depth, cur = {mod}, 0, mod
        while cur in parent_of:
            cur = parent_of[cur]
            depth += 1
            if cur in seen:
                errs.append(f"module chain loops at {mod!r}")
                break
            seen.add(cur)
            if depth >= MAX_MODULE_DEPTH:
                errs.append(f"module {mod!r} nests deeper than {MAX_MODULE_DEPTH}")
                break

    # A module with nothing completable in it can never be finished, so its gateway is stuck.
    for mod in sorted(claimed_by):
        steps = [s for st in loaded[mod]["stages"] for s in st["steps"]]
        if not any(s.get("danceSlug") or s.get("module") for s in steps):
            warns.append(f"module {mod!r} has no completable step — {claimed_by[mod]} can never be finished")

    return errs, warns, claimed_by


def main():
    styles = {n.lower(): int(i) for i, n in psql('select "Id","Name" from "Styles";')}
    files = sorted(glob.glob(os.path.join(RMDIR, "*.json")))
    if not files:
        raise SystemExit(f"no roadmap files in {RMDIR}")

    total_errs = 0
    loaded = {}
    for path in files:
        errs, warns, rm, n, linked = check(path, styles)
        loaded[rm.get("slug", os.path.basename(path))] = rm
        total_errs += len(errs)
        head = f"{os.path.basename(path):<22} {n:>3} steps, {linked:>3} linked"
        print(f"{head}  {'FAIL' if errs else 'ok'}")
        for w in warns:
            print(f"    warn  {w}")
        for e in errs:
            print(f"    ERROR {e}")

    merrs, mwarns, claimed = check_modules(loaded)
    total_errs += len(merrs)
    if claimed or merrs or mwarns:
        print(f"\nmodules: {len(claimed)} gateway(s)  {'FAIL' if merrs else 'ok'}")
        for m, where in sorted(claimed.items()):
            n = sum(len(st["steps"]) for st in loaded[m]["stages"])
            print(f"    {where} -> {m} ({n} steps)")
        for w in mwarns:
            print(f"    warn  {w}")
        for e in merrs:
            print(f"    ERROR {e}")

    print(f"\n{len(files)} roadmap(s), {total_errs} error(s)")
    return 1 if total_errs else 0


if __name__ == "__main__":
    sys.exit(main())
