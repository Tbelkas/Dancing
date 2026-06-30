"""trend_search8.py — round 8, STRETCHING focus #2 (style 23). 3rd col = difficulty. Writes _proto/trend_cand8.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)
C = [
 ("Splits Progression", 23, 2, "splits in 30 days follow along stretch routine beginner"),
 ("Full Body Mobility Flow", 23, 1, "full body mobility flow routine follow along"),
 ("Hip Flexor Stretch", 23, 1, "hip flexor stretch routine follow along tight hips"),
 ("Frog Stretch", 23, 2, "frog stretch hip opener flexibility tutorial"),
 ("Pigeon Pose", 23, 1, "pigeon pose stretch hip opener tutorial"),
 ("Lizard Pose", 23, 1, "lizard pose hip flexor stretch tutorial"),
 ("Couch Stretch", 23, 1, "couch stretch hip flexor quad tutorial"),
 ("Calf Stretch", 23, 1, "calf stretch flexibility routine follow along"),
 ("IT Band & Glute Stretch", 23, 1, "IT band glute stretch routine follow along"),
 ("Lower Back Relief", 23, 1, "lower back stretch relief routine follow along"),
 ("Neck & Traps Release", 23, 1, "neck and trap stretch release follow along tension"),
 ("Wrist & Forearm Mobility", 23, 1, "wrist forearm mobility stretches follow along"),
 ("Thoracic Rotation", 23, 1, "thoracic spine mobility rotation stretch follow along"),
 ("Morning Mobility", 23, 1, "morning stretch mobility routine follow along wake up"),
 ("Flexibility for High Kicks", 23, 2, "flexibility for high kicks stretches tutorial dancers"),
 ("Seated Forward Fold", 23, 1, "seated forward fold hamstring stretch tutorial"),
 ("Jefferson Curl", 23, 2, "jefferson curl tutorial spinal flexibility how to"),
]
out = open("_proto/trend_cand8.tsv", "w", encoding="utf-8")
for name, sid, diff, q in C:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "--print",
                            "%(id)s||%(title)s||%(duration)ss", f"ytsearch6:{q}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        lines = [l for l in r.stdout.splitlines() if l][:6]
    except Exception as e:
        lines = [f"ERR||{e}||"]
    print(f"### {name}  [style {sid} diff {diff}]")
    for l in lines:
        print("   " + l)
    out.write(f"{name}\t{sid}\t{diff}\t" + " ;; ".join(lines) + "\n")
out.close()
print("\nwrote _proto/trend_cand8.tsv")
