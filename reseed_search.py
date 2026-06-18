"""reseed_search.py — for each candidate deleted move, ytsearch3 and dump titles for judgment."""
import subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
# real-move candidates (junk/video-section names excluded)
NAMES=["Swim Buggy","Rápido salsa","Rondilla salsa","Lazo salsa","Forward Lock ballroom",
 "Turn à gauche","Tango Pas de basque","En dedans ballet","Désarmé","Alembra dance",
 "Inside Swivels swing","Détendu ballet","The Swim dance move","The Ska dance",
 "Bicycle dance move","Froggy dance move","Salud rueda casino","Meneo salsa","El Perico rueda",
 "Guapo rueda","Pasa la Olla rueda","Chupa rueda","Guantera rueda","Salsa Limpio",
 "Perico Limpio","Salsero rueda","Ojo Que Pasa rueda","La India rueda","Tumbando Caja rueda",
 "Walk Over breakdance","Airporkchop power move","Aja afro dance","Dudupe afro dance",
 "Mumu Rara afro dance","Odunsi afro dance","Oyi afro dance","Sisi E afro dance","Hip Bop afro dance",
 "Eje Aje afro dance","Killer Bee dancehall","Festival Stance dancehall"]
out=open("_proto/reseed_search.tsv","w",encoding="utf-8")
for nm in NAMES:
    try:
        r=subprocess.run(["yt-dlp","--no-warnings","--flat-playlist","--print",
                          "%(id)s||%(title)s||%(duration)ss",f"ytsearch3:{nm} tutorial how to"],
                         capture_output=True,text=True,encoding="utf-8",timeout=60)
        lines=[l for l in r.stdout.splitlines() if l][:3]
    except Exception as e:
        lines=[f"ERR||{e}||"]
    print(f"### {nm}")
    for l in lines: print("   "+l)
    out.write(f"{nm}\t"+" ;; ".join(lines)+"\n")
out.close()
print("\nwrote _proto/reseed_search.tsv")
