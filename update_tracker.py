"""update_tracker.py <videoId> <status> <result> [notes]
Updates the row for <videoId> in VIDEO_FIXUP.md and refreshes the progress line.
"""
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
vid,status,result=sys.argv[1],sys.argv[2],sys.argv[3]
notes=sys.argv[4] if len(sys.argv)>4 else ""
lines=open("VIDEO_FIXUP.md",encoding="utf-8").read().splitlines()
for i,l in enumerate(lines):
    if re.match(rf'^\| \d+ \| {re.escape(vid)} \|', l):
        cells=[c.strip() for c in l.split("|")]
        # cells: ['', #, vid, ndances, status, result, notes, '']
        cells[4]=status; cells[5]=result
        if notes: cells[6]=notes
        lines[i]="| "+" | ".join(cells[1:-1])+" |"
        break
else:
    print(f"row for {vid} not found"); sys.exit(1)
# refresh progress count = rows whose status starts with done/verified marker
done=sum(1 for l in lines if re.match(r'^\| \d+ \|',l) and ("DONE" in l or "VERIFIED" in l))+1  # +demo row #0
total=sum(1 for l in lines if re.match(r'^\| \d+ \|',l))
for i,l in enumerate(lines):
    if l.startswith("**Progress:"):
        lines[i]=f"**Progress: {done} resolved / {total} total** (updated live during grind)"
        break
open("VIDEO_FIXUP.md","w",encoding="utf-8").write("\n".join(lines)+"\n")
print(f"{vid} -> {status} | {result} | resolved {done}/{total}")
