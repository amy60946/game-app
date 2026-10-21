# v5 · Görsel 9: yere çok yakın makro çim + düz basamak taşları + papatyalar (arkadan vuran güneşte parlayan teller). Özgün, kodla.
#   /tmp/claude-0/bpyenv/bin/python g9_makro.py -- <çıktı.png> [örnek]
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, mathutils
from common import *

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = args[0] if args else '/tmp/g9.png'
samples = int(args[1]) if len(args) > 1 else 56
sc = reset(samples, (int(os.environ.get("RW", 1600)), int(os.environ.get("RH", 900))))
sky(sc, strength=1.2, cloud_amt=0.85, seed=5.0)
sun(elev=24, azim=160, energy=4.8, col='#fff0d0')   # kameranın karşısından: teller arkadan aydınlanır

def h(x, y):
    n = mathutils.noise.noise(V((x * 0.06, y * 0.06, 0.7))) * 1.2
    return n + max(0.0, y - 6) * 0.22        # ileride yükselen çayır yamacı

def col(x, y, z, n):
    a = srgb('#4b8d24'); b = srgb('#8cc63c'); d = srgb('#7a6a42')
    t = 0.5 + 0.5 * mathutils.noise.noise(V((x * 0.3, y * 0.3, 2.0)))
    c = [a[i] * (1 - t) + b[i] * t for i in range(3)]
    p = max(0.0, 1.0 - abs(x - 0.25 * y) / 0.9) * (1.0 if y < 5 else 0.0)   # patika: toprak tonu
    return [c[i] * (1 - p * 0.7) + d[i] * p * 0.7 for i in range(3)]

ground = grid_terrain('ground', 120, 240, h, vcol_mat('ground', 0.9, 0.2), col)

# düz basamak taşları (patika), ön planda
sm = rock_mat('stone', base='#a7a39c', dark='#7b7774', moss_amt=0.18, warm='#c2b6a2')
stones = []
rnd = random.Random(4)
for i in range(9):
    y = -0.6 + i * 0.55 + rnd.uniform(-0.08, 0.08); x = 0.25 * y + rnd.uniform(-0.25, 0.25)
    s = rnd.uniform(0.28, 0.42)
    o = rock('st%d' % i, (x, y, h(x, y) + 0.01), s, sm, seed=200 + i, flat=0.16, sharp=0.5, rot=rnd.uniform(0, 6.3))
    stones.append(o)
# uzakta kayalık yamaç ve bir çalı kümesi
far = rock('far', (-14, 60, 8), 20, rock_mat('far', moss_amt=0.45), seed=77, flat=0.5, sharp=0.8, rot=0.4)
far2 = rock('far2', (22, 70, 7), 17, rock_mat('far2', moss_amt=0.4), seed=78, flat=0.45, sharp=0.8, rot=1.4)
gm = grass_mat('grass', base='#356f1a', tip='#d0ec62', translucent=0.45)
rg = random.Random(9); pts = []
for i in range(520000):
    x = rg.uniform(-16, 20); y = rg.uniform(-1.6, 30)
    d = max(0.0, (y - 3) / 27.0) + max(0.0, abs(x - 1) - 5) / 13.0
    if rg.random() < min(0.95, d * 0.9): continue
    if abs(x - 0.25 * y) < 0.42 and y < 4.6: continue   # patikada çim yok
    if any((V((x, y)) - o.location.xy).length < o.scale.x * 0.95 for o in stones): continue
    pts.append((x, y, h(x, y) - 0.005, 1.0 + d * 2.5))
blades('grass', pts, gm, h=(0.09, 0.24), w=(0.008, 0.02), bend=0.55, segs=4)
fp = [p for p in pts[::140]]
daisies('papatya', fp, petal='#ffffff', r=(0.018, 0.03))
daisies('sari', pts[7::400], petal='#f6d43c', heart='#e38a1c', r=(0.012, 0.02), seed=12)

cam = camera((-0.35, -2.2, 0.42), (0.9, 6.0, 0.55), lens=24)
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 2.4; cam.data.dof.aperture_fstop = 2.8
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('OK', out)
