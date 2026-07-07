"""trend_search9.py — round 9, STRETCHING focus #3 (style 23). 3rd col = difficulty. Writes _proto/trend_cand9.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)
C = [
 ("Yoga for Dancers", 23, 1, "yoga for dancers flexibility flow follow along"),
 ("Bedtime Stretch", 23, 1, "bedtime stretch routine before bed relax follow along"),
 ("Standing Splits", 23, 2, "standing splits stretch tutorial flexibility"),
 ("Cobra Stretch", 23, 1, "cobra pose stretch back flexibility tutorial"),
 ("Camel Pose", 23, 2, "camel pose ustrasana backbend tutorial beginners"),
 ("Wheel Pose", 23, 3, "wheel pose tutorial backbend flexibility beginners"),
 ("Butterfly Stretch", 23, 1, "butterfly stretch groin hip opener tutorial"),
 ("Inner Thigh Stretch", 23, 1, "inner thigh adductor stretch routine follow along"),
 ("Deep Squat Mobility", 23, 1, "deep squat mobility hip ankle stretch follow along"),
 ("Chest Opener", 23, 1, "chest opener stretch posture follow along routine"),
 ("Side Body Stretch", 23, 1, "side body oblique stretch routine follow along"),
 ("Leg Extension Hold", 23, 2, "active flexibility leg extension hold develope dancers"),
 ("Hip CARs", 23, 1, "hip CARs controlled articular rotations mobility tutorial"),
 ("Static Full Body Stretch", 23, 1, "static full body stretch routine follow along flexibility"),
 ("PNF Stretching", 23, 2, "PNF stretching technique tutorial flexibility"),
 ("Cossack Squat", 23, 1, "cossack squat mobility stretch tutorial"),
 ("Resistance Band Stretch", 23, 1, "resistance band stretching routine flexibility follow along"),
]
out = open("_proto/trend_cand9.tsv", "w", encoding="utf-8")
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
print("\nwrote _proto/trend_cand9.tsv")
