"""Find oscillations in the per-frame DOM samples: a value that changes and then changes
back within a second. That is the shape of a flicker."""
import json, sys
from collections import defaultdict

data = json.load(open(sys.argv[1]))
KEYS = ['danceCards', 'roadmapCards', 'steps', 'treeNodes', 'empty', 'skeletons', 'spinners', 'textLen']

for sc in data:
    print(f"\n===== {sc['scenario']} ({sc['url']}) =====")
    s = sc['samples']
    if not s:
        continue
    for k in KEYS:
        # compress to runs
        runs = []
        for smp in s:
            v = smp[k]
            if k == 'textLen':
                v = v // 200 * 200          # bucket, text jitters by a char
            if runs and runs[-1][0] == v:
                runs[-1][2] = smp['t']
                runs[-1][4] = smp['label']
            else:
                runs.append([v, smp['t'], smp['t'], smp['label'], smp['label']])
        if len(runs) < 2:
            continue
        # A -> B -> A within 1.2s
        osc = []
        for i in range(1, len(runs) - 1):
            a, b, c = runs[i - 1], runs[i], runs[i + 1]
            if a[0] == c[0] and b[0] != a[0] and (c[1] - b[1]) < 1200:
                osc.append(f"{a[0]}->{b[0]}->{c[0]} @{b[1]}ms for {c[1]-b[1]}ms [{b[3]}]")
        if osc:
            print(f"  !! {k}: " + '; '.join(osc[:8]) + (f"  (+{len(osc)-8} more)" if len(osc) > 8 else ''))
    # transitions summary for the eyeballs
    tr = []
    prev = None
    for smp in s:
        sig = (smp['danceCards'], smp['roadmapCards'], smp['steps'], smp['treeNodes'],
               smp['empty'], smp['skeletons'], smp['spinners'], smp['textLen'] // 200, smp['url'])
        if sig != prev:
            tr.append((smp['t'], smp['label'], sig))
            prev = sig
    print(f"  timeline ({len(tr)} states):")
    for t, lab, sig in tr[:60]:
        print(f"    {t:6}ms {lab:16} cards={sig[0]:3} rm={sig[1]:2} steps={sig[2]:3} nodes={sig[3]:3} "
              f"empty={sig[4]} skel={sig[5]} spin={sig[6]} text~{sig[7]*200:5} {sig[8]}")
    if len(tr) > 60:
        print(f"    ... {len(tr)-60} more")
