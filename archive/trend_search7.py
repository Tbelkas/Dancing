"""trend_search7.py — round 7, STRETCHING focus (style 23, no music). Writes _proto/trend_cand7.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)
C = [
 ("Front Splits", 23, 0, "how to get your front splits stretch tutorial dancers"),
 ("Middle Splits", 23, 0, "middle splits stretch tutorial flexibility"),
 ("Oversplits", 23, 0, "oversplit training stretch tutorial dancers"),
 ("Backbend", 23, 0, "backbend tutorial flexibility beginners back flexibility"),
 ("Bridge Pose", 23, 0, "bridge pose stretch tutorial back flexibility beginner"),
 ("Back Flexibility", 23, 0, "back flexibility stretches follow along dancers"),
 ("Hamstring Stretch", 23, 0, "hamstring flexibility stretch routine follow along"),
 ("Hip Openers", 23, 0, "hip opening stretches flexibility follow along dancers"),
 ("Pancake Stretch", 23, 0, "pancake straddle stretch flexibility tutorial"),
 ("Needle Scale", 23, 0, "needle scale standing splits stretch tutorial flexibility"),
 ("Shoulder Mobility", 23, 0, "shoulder mobility flexibility stretches follow along"),
 ("Ankle & Foot Mobility", 23, 0, "ankle foot flexibility stretches dancers pointe"),
 ("Dynamic Warm-Up", 23, 0, "dynamic warm up before dancing stretch routine"),
 ("Cool-Down Stretch", 23, 0, "cool down stretch after dancing follow along"),
 ("Splits Warm-Up", 23, 0, "warm up before splits stretch routine follow along"),
 ("Active Flexibility", 23, 0, "active flexibility leg control stretch dancers"),
 ("Spine Mobility", 23, 0, "spine mobility flexibility stretch routine follow along"),
 ("Contortion Basics", 23, 0, "contortion flexibility beginner stretch tutorial"),
]
out = open("_proto/trend_cand7.tsv", "w", encoding="utf-8")
for name, sid, mid, q in C:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "--print",
                            "%(id)s||%(title)s||%(duration)ss", f"ytsearch6:{q}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        lines = [l for l in r.stdout.splitlines() if l][:6]
    except Exception as e:
        lines = [f"ERR||{e}||"]
    print(f"### {name}  [style {sid} music {mid}]")
    for l in lines:
        print("   " + l)
    out.write(f"{name}\t{sid}\t{mid}\t" + " ;; ".join(lines) + "\n")
out.close()
print("\nwrote _proto/trend_cand7.tsv")
