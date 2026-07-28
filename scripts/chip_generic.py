"""
chip_generic.py [apply]
Fallback chips for the no-signal remainder of the chip-everything push
(2026-07-13). Reads _proto/chip_all_inventory.tsv (must be freshly rebuilt):

- lane E/B rows typed 'tutorial' with dur>=180: proportional
  Intro / Tutorial / Outro split (no transcript signal exists; honest generic).
- other lane E/B rows (performance/steps or short): single chip spanning the
  clip, labeled with the dance name. keeptype.
- lane T (tiktok): single chip "<dance>@0" (open end; duration unknown). keeptype.

EXCLUDED (handled elsewhere or unfixable):
  multimodal set, p2JrE6JICKk mis-sourced rows, dead sFt9yqACiuI.
"""
import os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
apply = "apply" in sys.argv[1:]

MULTIMODAL = {"3ftJELfXvGs", "oj-S6T4oZeU", "JR3Dtyj4Ik4", "0ZVLG0E72Kw",
              "_9JZuOO9E_w", "7V1eFdUbP7w", "-qEONlQBBl0"}
EXCLUDE_YTID = MULTIMODAL | {"p2JrE6JICKk", "sFt9yqACiuI"}

rows = [l.split("\t") for l in open(os.path.join(ROOT, "_proto", "chip_all_inventory.tsv"),
                                     encoding="utf-8").read().splitlines()[1:]]
done = fails = 0
for lane, vid_db, ytid, platform, vtype, st, et, dur, ch, cap, dance_id, dance in rows:
    if lane not in ("E", "B", "T") or ytid in EXCLUDE_YTID:
        continue
    dur = int(dur or 0)
    if lane == "T" or dur == 0:
        spec = f"{dance}@0"
        how = "tiktok-open" if lane == "T" else "nodur-open"
    elif vtype == "tutorial" and dur >= 180:
        intro = min(30, max(8, dur // 10))
        outro = max(dur - max(15, dur // 15), intro + 30)
        spec = f"Intro@0-{intro};Tutorial@{intro}-{outro};Outro@{outro}-{dur}"
        how = "proportional"
    else:
        spec = f"{dance}@0-{dur}"
        how = "single"
    print(f"db{vid_db} ({how}): {spec}")
    if apply:
        p = subprocess.run(["python", os.path.join(ROOT, "scripts", "apply_sections.py"),
                            vid_db, spec, "apply", "keeptype"],
                           capture_output=True, text=True, encoding="utf-8")
        if "APPLIED" in (p.stdout or ""):
            done += 1
        else:
            fails += 1
            print(f"  FAIL {(p.stderr or p.stdout or '')[-120:]}")
print(f"\n{'applied ' + str(done) if apply else 'dry-run'}; fails={fails}")
