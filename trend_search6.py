"""trend_search6.py — round 6. Writes _proto/trend_cand6.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)
C = [
 ("Kizomba Basic", 39, 19, "kizomba basic steps tutorial beginners"),
 ("Kizomba Saida", 39, 19, "kizomba saida tutorial"),
 ("Tarraxinha", 39, 19, "tarraxinha kizomba tutorial"),
 ("Afro House Footwork", 40, 20, "afro house dance tutorial footwork south africa"),
 ("Bhenga", 40, 20, "bhenga dance tutorial south africa"),
 ("Vosho", 41, 21, "vosho dance tutorial south africa"),
 ("Gqom Dance", 41, 21, "gqom dance moves tutorial"),
 ("Toprock", 12, 3, "breakdance toprock tutorial beginners"),
 ("6-Step", 12, 3, "breakdance 6 step tutorial beginners"),
 ("Baby Freeze", 12, 3, "breakdance baby freeze tutorial"),
 ("Chair Freeze", 12, 3, "breakdance chair freeze tutorial"),
 ("Cabbage Patch", 10, 3, "cabbage patch dance move tutorial"),
 ("Reject", 10, 3, "reject dance move tutorial hip hop"),
 ("Wu-Tang", 10, 3, "wu tang dance move tutorial"),
 ("Smurf", 10, 3, "smurf dance move tutorial old school"),
 ("Locking Basics", 3, 3, "locking dance tutorial basics beginners"),
 ("Wrist Rolls", 3, 3, "locking wrist roll tutorial"),
 ("Whichaway", 3, 3, "whichaway locking dance tutorial"),
 ("House Jack", 11, 6, "house dance jack tutorial jacking"),
 ("Loft", 11, 6, "house dance loft tutorial"),
 ("Skate", 11, 6, "house dance skate tutorial"),
 ("Pink Venom", 31, 3, "BLACKPINK Pink Venom dance tutorial mirrored"),
 ("Shut Down", 31, 3, "BLACKPINK Shut Down dance tutorial mirrored"),
 ("Baddie (IVE)", 31, 3, "IVE Baddie dance tutorial mirrored"),
 ("Boom Boom Bass (RIIZE)", 31, 3, "RIIZE Boom Boom Bass dance tutorial mirrored"),
 ("Pullback", 19, 4, "tap dance pullback tutorial"),
 ("Paddle Turn", 19, 4, "tap dance paddle turn tutorial"),
 ("Popping Basics", 10, 3, "popping dance tutorial hits beginners"),
 ("Waving", 10, 3, "arm wave dance tutorial popping beginners"),
 ("Snake", 10, 3, "body snake dance tutorial"),
 ("Network", 13, 11, "network afro dance tutorial"),
 ("Sare", 13, 11, "Sare afro dance tutorial"),
]
out = open("_proto/trend_cand6.tsv", "w", encoding="utf-8")
for name, sid, mid, q in C:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "--print",
                            "%(id)s||%(title)s||%(duration)ss", f"ytsearch5:{q}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
        lines = [l for l in r.stdout.splitlines() if l][:5]
    except Exception as e:
        lines = [f"ERR||{e}||"]
    print(f"### {name}  [style {sid} music {mid}]")
    for l in lines:
        print("   " + l)
    out.write(f"{name}\t{sid}\t{mid}\t" + " ;; ".join(lines) + "\n")
out.close()
print("\nwrote _proto/trend_cand6.tsv")
