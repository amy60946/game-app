# v5 · Görsel 4: çimenlikte yosunlu kaya kümesi + dikili taşlar (menhir). Özgün, kodla.
#   /tmp/claude-0/bpyenv/bin/python g4_kayalar.py -- <çıktı.png> [örnek]
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, mathutils
from common import *

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = args[0] if args else '/tmp/g4.png'
samples = int(args[1]) if len(args) > 1 else 56
sc = reset(samples, (int(os.environ.get("RW", 1600)), int(os.environ.get("RH", 900))))
sky(sc, strength=1.15, cloud_amt=0.8, seed=2.0)
sun(elev=34, azim=-58, energy=4.6)

def h(x, y):
    n = mathutils.noise.noise(V((x * 0.05, y * 0.05, 0.3))) * 1.6 + mathutils.noise.noise(V((x * 0.18, y * 0.18, 1.7))) * 0.25
    rise = max(0.0, y - 18) * 0.35   # arkada yükselen yamaç
    return n + rise

def col(x, y, z, n):
    g1 = srgb('#4a8f26'); g2 = srgb('#86c43a'); dry = srgb('#b3b552')
    t = 0.5 + 0.5 * mathutils.noise.noise(V((x * 0.09, y * 0.09, 4.1)))
    d = max(0.0, mathutils.noise.noise(V((x * 0.04, y * 0.04, 9.3))) - 0.15) * 2.2
    c = [g1[i] * (1 - t) + g2[i] * t for i in range(3)]
    return [c[i] * (1 - d) + dry[i] * d for i in range(3)]

ground = grid_terrain('ground', 90, 180, h, vcol_mat('ground', 0.9, 0.15), col)

rm = rock_mat('rock', moss_amt=0.4)
rnd = random.Random(7)
rocks = []
# küme: merkezde dağınık yuvarlak taşlar, kenarda birkaç uzun dikili taş
for i in range(34):
    a = rnd.uniform(0, math.tau); r = rnd.uniform(0.5, 7.5) ** 1.0
    x = math.cos(a) * r * 1.2; y = 4 + math.sin(a) * r * 0.9
    s = rnd.uniform(0.35, 1.2) * (1.35 if r < 3 else 1.0)
    tall = rnd.uniform(0.6, 1.0)
    o = rock('r%d' % i, (x, y, h(x, y) + s * 0.15), s, rm, seed=i, flat=rnd.uniform(0.55, 0.9), rot=rnd.uniform(0, 6.3), tall=tall)
    rocks.append(o)
for i, (x, y, s, t) in enumerate([(-6.5, 3.0, 0.6, 3.2), (-5.2, 5.8, 0.5, 2.6), (6.8, 6.2, 0.5, 3.4), (2.6, 9.5, 0.45, 2.4), (-2.8, 10.8, 0.4, 2.9), (4.2, 2.2, 0.35, 2.2)]):
    o = rock('m%d' % i, (x, y, h(x, y) + s * t * 0.55), s, rm, seed=100 + i, flat=1.0, sharp=0.9, rot=rnd.uniform(0, 6.3), tall=t, thin=0.42)
    rocks.append(o)

# uzakta kıyı yamacı ve deniz şeridi
cliff = rock('cliff', (18, 46, 6), 9, rock_mat('cliff', moss_amt=0.35), seed=55, flat=0.55, sharp=0.6, rot=0.6, tall=1.0)
sea = bpy.data.meshes.new('sea'); sea.from_pydata([(-200, 60, 1.2), (200, 60, 1.2), (200, 400, 1.2), (-200, 400, 1.2)], [], [(0, 1, 2, 3)])
wm = bpy.data.materials.new('sea'); wm.use_nodes = True; wb = wm.node_tree.nodes['Principled BSDF']
wb.inputs['Base Color'].default_value = srgb('#2aa7c4'); wb.inputs['Roughness'].default_value = 0.08
link('sea', sea, wm)

# çim telleri: kameraya yakın alanda yoğun
gm = grass_mat('grass', base='#3d7d1e', tip='#c4e85a', translucent=0.35)
rg = random.Random(5); pts = []
for i in range(420000):
    x = rg.uniform(-45, 45); y = rg.uniform(-9, 44)
    far = max(0.0, (y - 6) / 38.0) + max(0.0, abs(x) - 14) / 31.0
    if rg.random() < min(0.92, far * 0.85): continue
    ok = all((V((x, y)) - o.location.xy).length > o.scale.x * 0.85 for o in rocks)
    if ok: pts.append((x, y, h(x, y) - 0.01, 1.0 + far * 1.2))
blades('grass', pts, gm, h=(0.12, 0.26), w=(0.02, 0.04), bend=0.5)
fp = [(x, y, z, 1.0) for (x, y, z, k) in pts[::90]]
daisies('flowers', fp[: len(fp) // 2], petal='#ffffff'); daisies('flowers2', fp[len(fp) // 2:], petal='#f4d23a', heart='#e08a1a', seed=8)

camera((-1.0, -8.5, 3.4), (1.0, 8.0, 1.6), lens=28)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('OK', out)
