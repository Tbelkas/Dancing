"""trend_search3.py — round 3 candidate search. Writes _proto/trend_cand3.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)

C = [
 # Heels (32/3)
 ("Heels Walk", 32, 3, "heels dance walk tutorial beginner"),
 ("Heels Floorwork", 32, 3, "heels dance floorwork tutorial"),
 ("Heels Body Roll", 32, 3, "heels dance body roll tutorial"),
 ("Hair Flip", 32, 3, "heels dance hair flip tutorial"),
 # Reggaeton (33/8)
 ("Perreo", 33, 8, "perreo tutorial dance basic"),
 ("Dembow", 33, 8, "dembow dance tutorial steps"),
 ("Reggaeton Basic", 33, 8, "reggaeton basic steps dance tutorial"),
 ("Zapateo", 33, 8, "reggaeton zapateo dance tutorial"),
 # K-Pop (31/3)
 ("Whiplash (aespa)", 31, 3, "aespa Whiplash dance tutorial mirrored"),
 ("Smart (LE SSERAFIM)", 31, 3, "LE SSERAFIM Smart dance tutorial mirrored"),
 ("How Sweet (NewJeans)", 31, 3, "NewJeans How Sweet dance tutorial mirrored"),
 ("Drip (BABYMONSTER)", 31, 3, "BABYMONSTER Drip dance tutorial mirrored"),
 ("Sticky (KISS OF LIFE)", 31, 3, "KISS OF LIFE Sticky dance tutorial mirrored"),
 # Shuffle (29/6)
 ("Heel Toe", 29, 6, "heel toe shuffle dance tutorial"),
 ("Phonk Shuffle", 29, 6, "phonk shuffle dance tutorial beginner"),
 # Amapiano (28/16)
 ("Tshwala Bam", 28, 16, "Tshwala Bam dance tutorial amapiano"),
 ("Umlando", 28, 16, "Umlando dance tutorial amapiano"),
 # Afrobeats (13/11)
 ("Rush", 13, 11, "Rush Ayra Starr dance tutorial"),
 ("Ginger", 13, 11, "Ginger Wizkid Burna Boy dance tutorial"),
 # Dancehall (14/12)
 ("Out & Bad", 14, 12, "Out and Bad dancehall dance tutorial"),
 ("Pon Di River", 14, 12, "Pon Di River Pon Di Bank dancehall tutorial"),
]
out = open("_proto/trend_cand3.tsv", "w", encoding="utf-8")
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
print("\nwrote _proto/trend_cand3.tsv")
