"""
check_alive.py <ids_file>
Check each YouTube id via the oembed endpoint. 200=OK/embeddable, 401=private or
embedding-disabled, 404=deleted. Prints "<id>\t<status>" for anything not 200.
"""
import sys, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

ids = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
bad = 0
for i, vid in enumerate(ids):
    url = f"https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v={vid}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        print(f"{vid}\t{e.code}", flush=True); bad += 1
    except Exception as e:
        print(f"{vid}\tERR {type(e).__name__}", flush=True); bad += 1
print(f"# checked {len(ids)}, bad {bad}")
