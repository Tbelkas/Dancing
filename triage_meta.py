"""
triage_meta.py <ids_file>
Metadata-only triage (no caption download): ensure _proto/<id>.json exists for each
ytid (yt-dlp -J, cached) and emit  ytid<TAB>dur<TAB>nchapters<TAB>autocap<TAB>title
to stdout. Light first pass to decide which videos are worth full transcript processing.
"""
import json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)

ids = [l.split("\t")[0].strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
for vid in ids:
    cache = f"_proto/{vid}.json"
    d = None
    if os.path.exists(cache):
        try:
            d = json.load(open(cache, encoding="utf-8"))
        except Exception:
            d = None
    if not isinstance(d, dict):  # missing, or cached null/garbage -> (re)fetch
        p = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "-J",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8")
        if p.returncode:
            print(f"{vid}\t-1\t0\t0\tFETCH_FAILED")
            continue
        open(cache, "w", encoding="utf-8").write(p.stdout)
        try:
            d = json.load(open(cache, encoding="utf-8"))
        except Exception:
            d = None
    if not isinstance(d, dict):
        print(f"{vid}\t-1\t0\t0\tBAD_CACHE")
        continue
    dur = int(d.get("duration") or 0)
    nch = len(d.get("chapters") or [])
    autocap = 1 if [a for a in (d.get("automatic_captions") or {}) if a.startswith("en")] else 0
    title = (d.get("title") or "").replace("\t", " ").replace("\n", " ")
    print(f"{vid}\t{dur}\t{nch}\t{autocap}\t{title}")
