"""trend_search5.py — round 5. Writes _proto/trend_cand5.tsv."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)

C = [
 ("Bachata Basic", 36, 17, "bachata basic steps tutorial beginners"),
 ("Bachata Side Step", 36, 17, "bachata side step tutorial"),
 ("Bachata Body Wave", 36, 17, "bachata body wave tutorial"),
 ("Bachata Turn", 36, 17, "bachata lady styling turn tutorial"),
 ("Soca Wine", 37, 18, "soca wine tutorial how to wine"),
 ("Soca Wave", 37, 18, "soca dance wave tutorial carnival"),
 ("Soca Bumper", 37, 18, "soca bumper dance tutorial"),
 ("Passinho", 38, 6, "passinho brazilian funk dance tutorial"),
 ("Rebolation", 38, 6, "rebolation dance tutorial"),
 ("Beat Drop", 38, 6, "brazilian funk beat drop dance tutorial"),
 ("Spicy (aespa)", 31, 3, "aespa Spicy dance tutorial mirrored"),
 ("Hype Boy (NewJeans)", 31, 3, "NewJeans Hype Boy dance tutorial mirrored"),
 ("Ditto (NewJeans)", 31, 3, "NewJeans Ditto dance tutorial mirrored"),
 ("Kitsch (IVE)", 31, 3, "IVE Kitsch dance tutorial mirrored"),
 ("Antifragile (LE SSERAFIM)", 31, 3, "LE SSERAFIM Antifragile dance tutorial mirrored"),
 ("One Leg Get Back", 35, 6, "one leg get back jersey club tutorial"),
 ("KB Bounce", 35, 6, "KB bounce jersey club dance tutorial"),
 ("Sharp Bounce", 35, 6, "sharp bounce jersey club dance tutorial"),
 ("Heels Strut", 32, 3, "heels dance strut walk tutorial"),
 ("Heels Chair Dance", 32, 3, "heels chair dance tutorial"),
 ("Heel Twerk", 34, 3, "how to heel twerk tutorial"),
 ("Knee Twerk", 34, 3, "twerk on knees tutorial beginners"),
 ("Sthwathwa", 28, 16, "Sthwathwa amapiano dance tutorial"),
 ("Phuze", 28, 16, "Phuze amapiano dance challenge tutorial"),
 ("Calm Down", 13, 11, "Calm Down Rema dance tutorial"),
 ("Unavailable", 13, 11, "Unavailable Davido dance tutorial"),
 ("Crocodile", 14, 12, "crocodile dancehall dance tutorial"),
 ("Wine Up", 14, 12, "how to wine dancehall tutorial waist"),
 ("Buffalo", 19, 4, "buffalo tap dance step tutorial"),
 ("Shim Sham", 19, 4, "shim sham tap dance tutorial"),
 ("Stomp", 15, 3, "krump stomp tutorial basics"),
 ("Jab", 15, 3, "krump jab tutorial basics"),
 ("Runway", 16, 6, "vogue runway tutorial"),
 ("Cumbia", 1, 1, "how to dance cumbia tutorial basic steps"),
 ("Mambo", 1, 1, "how to dance mambo tutorial basic"),
 ("Attitude Turn", 7, 2, "attitude turn dance tutorial"),
]
out = open("_proto/trend_cand5.tsv", "w", encoding="utf-8")
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
print("\nwrote _proto/trend_cand5.tsv")
