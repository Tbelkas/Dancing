"""trend_search.py — yt-dlp search candidate tutorials for trending dances across target styles.
Writes _proto/trend_cand.tsv (name<TAB>styleId<TAB>musicId<TAB>id||title||durs ;; ...)."""
import subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("_proto", exist_ok=True)

# (name, styleId, musicId, search query)
C = [
 # Afrobeats (13 / 11)
 ("Shaku Shaku", 13, 11, "Shaku Shaku dance tutorial"),
 ("Gwara Gwara", 13, 11, "Gwara Gwara dance tutorial"),
 ("Azonto", 13, 11, "Azonto dance tutorial how to"),
 ("Legwork", 13, 11, "Legwork afro dance tutorial"),
 ("Sekem", 13, 11, "Sekem dance tutorial MC Galaxy"),
 ("Pilolo", 13, 11, "Pilolo dance tutorial"),
 # Dancehall (14 / 12)
 ("Dutty Wine", 14, 12, "Dutty Wine dance tutorial"),
 ("Gully Creeper", 14, 12, "Gully Creeper dance tutorial"),
 ("Nuh Linga", 14, 12, "Nuh Linga dance tutorial"),
 ("Willie Bounce", 14, 12, "Willie Bounce dancehall tutorial"),
 ("Bogle", 14, 12, "Bogle dance tutorial dancehall"),
 ("Genna Bounce", 14, 12, "Genna Bounce dance tutorial"),
 # Jazz (20 / 4)
 ("Pas de Bourree", 20, 4, "pas de bourree jazz dance tutorial"),
 ("Fan Kick", 20, 4, "fan kick jazz dance tutorial"),
 ("Chaine Turns", 20, 4, "chaine turns jazz dance tutorial"),
 ("Pivot Step", 20, 4, "jazz pivot step turn tutorial"),
 # Vogue (16 / 6)
 ("Duckwalk", 16, 6, "vogue duckwalk tutorial"),
 ("Hand Performance", 16, 6, "vogue hand performance tutorial"),
 ("Old Way Vogue", 16, 6, "old way vogue tutorial"),
 ("Spin and Dip", 16, 6, "vogue spins and dips tutorial"),
 # Contemporary (7 / 2)
 ("Contraction", 7, 2, "contemporary dance contraction tutorial"),
 ("Floor Roll", 7, 2, "contemporary floor roll tutorial"),
 ("Spiral", 7, 2, "contemporary dance spiral tutorial"),
 # Flamenco (18 / 10)
 ("Zapateado", 18, 10, "flamenco zapateado footwork tutorial"),
 ("Braceo", 18, 10, "flamenco braceo arms tutorial"),
 ("Floreo", 18, 10, "flamenco floreo hands tutorial"),
 # Tutting (22 / 3)
 ("King Tut", 22, 3, "King Tut dance tutorial tutting"),
 # Amapiano (28 / 16)
 ("Bacardi", 28, 16, "Bacardi amapiano dance tutorial"),
 ("Pouncing Cat", 28, 16, "Pouncing Cat amapiano dance tutorial"),
 ("Zekethe", 28, 16, "Zekethe amapiano dance tutorial"),
 ("John Vuli Gate", 28, 16, "John Vuli Gate dance tutorial"),
 # Shuffle (29 / 6)
 ("T-Step", 29, 6, "shuffle t-step tutorial cutting shapes"),
 ("Charleston Shuffle", 29, 6, "shuffle charleston tutorial"),
 ("Spongebob Shuffle", 29, 6, "spongebob shuffle dance tutorial"),
 ("Cutting Shapes", 29, 6, "cutting shapes shuffle tutorial beginner"),
 # Litefeet (30 / 3)
 ("Chicken Noodle Soup", 30, 3, "Chicken Noodle Soup dance tutorial litefeet"),
 ("Toe Wop", 30, 3, "Toe Wop dance tutorial litefeet"),
 ("Rev Up", 30, 3, "Rev Up litefeet dance tutorial"),
]

out = open("_proto/trend_cand.tsv", "w", encoding="utf-8")
for name, sid, mid, q in C:
    try:
        r = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "--print",
                            "%(id)s||%(title)s||%(duration)ss",
                            f"ytsearch5:{q}"],
                           capture_output=True, text=True, encoding="utf-8", timeout=90)
        lines = [l for l in r.stdout.splitlines() if l][:5]
    except Exception as e:
        lines = [f"ERR||{e}||"]
    print(f"### {name}  [style {sid} music {mid}]")
    for l in lines:
        print("   " + l)
    out.write(f"{name}\t{sid}\t{mid}\t" + " ;; ".join(lines) + "\n")
out.close()
print("\nwrote _proto/trend_cand.tsv")
