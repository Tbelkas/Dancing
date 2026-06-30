"""fetch_durations.py <tsv_with_ytid_in_col2> — yt-dlp duration for each distinct ytid.
Writes _proto/durations.tsv (ytid<TAB>duration_seconds or ERR). Resumable."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")

src = sys.argv[1]
ids = []
for line in open(src, encoding="utf-8"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) >= 2 and parts[1] and parts[1] != "ytid":
        ids.append(parts[1])
ids = sorted(set(ids))

done = {}
out_path = "_proto/durations.tsv"
if os.path.exists(out_path):
    for l in open(out_path, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) == 2:
            done[p[0]] = p[1]

f = open(out_path, "a", encoding="utf-8")
for i, vid in enumerate(ids):
    if vid in done:
        continue
    try:
        p = subprocess.run(["yt-dlp", "--no-warnings", "--print", "duration",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        dur = p.stdout.strip().splitlines()[0] if p.stdout.strip() else "ERR"
    except Exception:
        dur = "ERR"
    f.write(f"{vid}\t{dur}\n"); f.flush()
    if i % 20 == 0:
        print(f"{i}/{len(ids)} {vid}={dur}", flush=True)
f.close()
print(f"done {len(ids)} ids")
