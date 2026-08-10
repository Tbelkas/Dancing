"""Diff the captured page videos per phase.

Phases come from results.json (written by .flicker-capture.mjs):
  load   — navigation until the network went quiet
  idle   — 4s of nothing happening: ANY pixel change here is unexplained repaint
  scroll — scripted scroll down and back up

Flicker signals reported:
  * idle changes  — content moving while the user does nothing
  * reverts       — A -> B -> A within ~0.5s (something appeared then vanished)
"""
import subprocess, sys, os, glob, json
from PIL import Image, ImageChops

ROOT = sys.argv[1]
FPS = 15
W, H = 480, 300
STEP = 2  # pixel sampling stride

def extract(video, workdir):
    os.makedirs(workdir, exist_ok=True)
    for f in glob.glob(os.path.join(workdir, '*.png')):
        os.remove(f)
    subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-vf',
                    f'fps={FPS},scale={W}:{H}', os.path.join(workdir, 'f%04d.png')], check=True)
    return sorted(glob.glob(os.path.join(workdir, 'f*.png')))

def gray(p):
    return Image.open(p).convert('L').tobytes()

def diff(a, b):
    changed = 0
    total = 0
    for i in range(0, len(a), STEP):
        d = a[i] - b[i]
        if d < 0: d = -d
        if d > 14: changed += 1
        total += 1
    return changed / total

results = {r['name']: r for r in json.load(open(os.path.join(ROOT, 'results.json')))}
report = []

for name in sorted(os.listdir(ROOT)):
    d = os.path.join(ROOT, name)
    if not os.path.isdir(d) or name not in results:
        continue
    vids = glob.glob(os.path.join(d, '*.webm'))
    if not vids:
        continue
    r = results[name]
    ph = r['phases']
    fs = extract(vids[0], os.path.join(d, 'frames'))
    imgs = [gray(p) for p in fs]
    ms = lambda i: round(i * 1000 / FPS)

    def phase_of(t):
        if t < ph.get('idleStart', 0): return 'load'
        if t < ph.get('idleEnd', 0): return 'idle'
        if t < ph.get('scrollEnd', 10**9): return 'scroll'
        return 'after'

    changes = []
    for i in range(1, len(imgs)):
        c = diff(imgs[i - 1], imgs[i])
        if c > 0.002:
            changes.append({'t': ms(i), 'phase': phase_of(ms(i)), 'pct': round(c * 100, 2), 'i': i})

    reverts = []
    for ch in changes:
        i, c = ch['i'], ch['pct'] / 100
        for j in range(i + 1, min(i + 9, len(imgs))):
            back = diff(imgs[i - 1], imgs[j])
            moved = diff(imgs[i], imgs[j])
            if back < c * 0.3 and moved > c * 0.5:
                reverts.append({'t': ch['t'], 'phase': ch['phase'], 'back_t': ms(j),
                                'pct': ch['pct']})
                break

    idle = [c for c in changes if c['phase'] == 'idle']
    report.append({'page': name, 'frames': len(imgs), 'settleMs': r['settleMs'],
                   'phases': ph, 'idle_changes': idle, 'reverts': reverts,
                   'all_changes': changes})
    print(f"{name:24} idle_changes={len(idle):3} reverts={len(reverts):3} "
          f"(load={sum(1 for c in changes if c['phase']=='load')} scroll={sum(1 for c in changes if c['phase']=='scroll')})")

json.dump(report, open(os.path.join(ROOT, 'analysis.json'), 'w'), indent=2)
print('\nwrote analysis.json')
