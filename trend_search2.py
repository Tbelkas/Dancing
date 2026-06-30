"""trend_search2.py — round 2 candidate search. Writes _proto/trend_cand2.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)

# (name, styleId, musicId, query)
C = [
 # Amapiano (28/16)
 ("TwaTwa", 28, 16, "TwaTwa amapiano dance tutorial"),
 ("Sbhujwa", 28, 16, "Sbhujwa dance tutorial south africa"),
 ("Tap In", 28, 16, "Tap In amapiano dance tutorial"),
 ("Mavusana", 28, 16, "Mavusana dance tutorial amapiano"),
 # Shuffle (29/6)
 ("Running Man Shuffle", 29, 6, "running man shuffle dance tutorial"),
 ("V-Step", 29, 6, "v-step shuffle dance tutorial"),
 ("Diamond Step", 29, 6, "diamond step shuffle tutorial"),
 ("Hard Style", 29, 6, "hardstyle shuffle dance tutorial"),
 # Litefeet (30/3)
 ("Get Lite", 30, 3, "get lite litefeet dance tutorial"),
 ("Bad One", 30, 3, "bad one litefeet dance tutorial"),
 # Afrobeats (13/11)
 ("Soapy", 13, 11, "Soapy dance tutorial Naira Marley"),
 ("Kupe", 13, 11, "Kupe dance tutorial"),
 ("Gwo Gwo Gwo", 13, 11, "Gwo Gwo Gwo dance tutorial"),
 # Dancehall (14/12)
 ("Tek Weh Yuhself", 14, 12, "Tek Weh Yuhself dancehall tutorial"),
 ("Wacky Dip", 14, 12, "Wacky Dip dancehall dance tutorial"),
 ("Skip To Ma Lou", 14, 12, "Skip To Ma Lou dancehall tutorial"),
 ("Row Di Boat", 14, 12, "Row Di Boat dancehall dance tutorial"),
 # Vogue (16/6)
 ("Catwalk", 16, 6, "vogue catwalk tutorial"),
 ("Floor Performance", 16, 6, "vogue floor performance tutorial"),
 # Jazz (20/4)
 ("Jazz Pirouette", 20, 4, "jazz pirouette turn tutorial"),
 # K-Pop (31/3)
 ("APT. Challenge", 31, 3, "APT Rose Bruno Mars dance tutorial mirrored"),
 ("Magnetic (ILLIT)", 31, 3, "ILLIT Magnetic dance tutorial mirrored"),
 ("Supernova (aespa)", 31, 3, "aespa Supernova dance tutorial mirrored"),
 # Contemporary (7/2)
 ("Floorwork", 7, 2, "contemporary dance floorwork tutorial beginner"),
 ("Tilt", 7, 2, "contemporary dance tilt tutorial"),
 # Flamenco (18/10)
 ("Marcaje", 18, 10, "flamenco marcaje tutorial"),
 ("Vuelta", 18, 10, "flamenco vuelta turn tutorial"),
]
out = open("_proto/trend_cand2.tsv", "w", encoding="utf-8")
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
print("\nwrote _proto/trend_cand2.tsv")
