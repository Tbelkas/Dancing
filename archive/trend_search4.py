"""trend_search4.py — round 4 (double batch). Writes _proto/trend_cand4.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)

C = [
 # Twerk (34/3)
 ("Basic Twerk", 34, 3, "how to twerk for beginners tutorial"),
 ("Twerk Bounce", 34, 3, "twerk bounce tutorial beginner"),
 ("Booty Pop", 34, 3, "booty pop twerk tutorial"),
 # Jersey Club (35/6)
 ("Jersey Club Bounce", 35, 6, "jersey club dance tutorial bounce"),
 ("Gum Sole", 35, 6, "gum sole jersey club dance tutorial"),
 ("Jersey Club Footwork", 35, 6, "jersey club footwork tutorial"),
 # K-Pop (31/3)
 ("Armageddon (aespa)", 31, 3, "aespa Armageddon dance tutorial mirrored"),
 ("Super Shy (NewJeans)", 31, 3, "NewJeans Super Shy dance tutorial mirrored"),
 ("Queencard (G-IDLE)", 31, 3, "G-IDLE Queencard dance tutorial mirrored"),
 ("Love Dive (IVE)", 31, 3, "IVE Love Dive dance tutorial mirrored"),
 ("OMG (NewJeans)", 31, 3, "NewJeans OMG dance tutorial mirrored"),
 # Heels (32/3)
 ("Heels Spin", 32, 3, "heels dance spin turn tutorial"),
 ("Heels Knee Spin", 32, 3, "heels dance knee spin tutorial"),
 ("Heels Hip Sway", 32, 3, "heels dance hip sway tutorial"),
 # Reggaeton (33/8)
 ("Reggaeton Shoulders", 33, 8, "reggaeton shoulder movement tutorial"),
 ("Sandungueo", 33, 8, "sandungueo reggaeton dance tutorial"),
 # Shuffle (29/6)
 ("Shuffle Slide", 29, 6, "shuffle slide dance tutorial"),
 ("Shuffle Spin", 29, 6, "shuffle spin tutorial dance"),
 # Litefeet (30/3)
 ("Pause (Litefeet)", 30, 3, "pause litefeet dance tutorial"),
 ("Hat Trick", 30, 3, "hat trick litefeet dance tutorial"),
 # Amapiano (28/16)
 ("Pelo", 28, 16, "Pelo amapiano dance tutorial"),
 ("Sgija", 28, 16, "Sgija amapiano dance tutorial"),
 # Afrobeats (13/11)
 ("Buga", 13, 11, "Buga Kizz Daniel dance tutorial"),
 ("Soso", 13, 11, "Soso Omah Lay dance tutorial"),
 # Dancehall (14/12)
 ("Wave (Dancehall)", 14, 12, "dancehall wave dance tutorial"),
 ("Gas (Dancehall)", 14, 12, "gas dancehall dance tutorial Ding Dong"),
 # Jazz (20/4)
 ("Switch Leap", 20, 4, "switch leap dance tutorial jazz"),
 ("Pique Turn", 20, 4, "pique turn dance tutorial"),
 # Tap (19/4)
 ("Time Step", 19, 4, "tap dance time step tutorial"),
 ("Cramp Roll", 19, 4, "tap dance cramp roll tutorial"),
 # Vogue (16/6)
 ("Death Drop", 16, 6, "vogue death drop dip tutorial"),
 # Flamenco (18/10)
 ("Llamada", 18, 10, "flamenco llamada tutorial"),
 # Contemporary (7/2)
 ("Contemporary Leap", 7, 2, "contemporary dance leap tutorial"),
 # Latin (1/1)
 ("Salsa Shines", 1, 1, "salsa shines footwork tutorial"),
 # Hip-hop classics still missing (10/3)
 ("Dougie", 10, 3, "how to dougie dance tutorial"),
 ("Nae Nae", 10, 3, "how to nae nae dance tutorial"),
 ("Two Step", 10, 3, "hip hop two step dance tutorial"),
]
out = open("_proto/trend_cand4.tsv", "w", encoding="utf-8")
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
print("\nwrote _proto/trend_cand4.tsv")
