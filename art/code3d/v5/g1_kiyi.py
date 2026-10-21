# v5 · Görsel 1: kıyı şeridi + kayalık burun: berrak turkuaz su (derinlik tonu), kıyı köpüğü, kumsal, yosun/çim kapaklı kayalar. Özgün, kodla.
#   /tmp/claude-0/bpyenv/bin/python g1_kiyi.py -- <çıktı.png> [örnek]
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, mathutils
from common import *

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = args[0] if args else '/tmp/g1.png'
samples = int(args[1]) if len(args) > 1 else 56
sc = reset(samples, (int(os.environ.get("RW", 1600)), int(os.environ.get("RH", 900))))
sc.cycles.transmission_bounces = 8; sc.cycles.volume_bounces = 2
sky(sc, strength=1.2, cloud_amt=0.75, seed=9.0)
sun(elev=40, azim=-35, energy=4.6)

def shore(x):                     # kıyı çizgisi (y), hafif koylu
    return 2.0 * math.sin(x * 0.12) + 0.8 * math.sin(x * 0.31 + 1.0)

def h(x, y):
    d = y - shore(x)              # + kara, − deniz
    if d < 0:
        z = d * 0.16 - max(0, -d - 8) * 0.25
    else:
        z = d * 0.1 + max(0, d - 7) * 0.12 + mathutils.noise.noise(V((x * 0.05, y * 0.05, 2.2))) * 1.2 * min(1.0, d / 10)
    z += mathutils.noise.noise(V((x * 0.15, y * 0.15, 0.5))) * 0.12
    return z

def col(x, y, z, n):
    sand = srgb('#ecd7a6'); wet = srgb('#b99d6c'); deep = srgb('#f2e2b6'); grass = srgb('#73b236'); g2 = srgb('#4f9128')
    d = y - shore(x)
    t = 0.5 + 0.5 * mathutils.noise.noise(V((x * 0.4, y * 0.4, 3.0)))
    if d < -0.2:
        c = [deep[i] * (0.9 + 0.1 * t) for i in range(3)]
    elif d < 1.2:
        k = (d + 0.2) / 1.4; c = [wet[i] * (1 - k) + sand[i] * k for i in range(3)]
    else:
        g = min(1.0, max(0.0, (d - 5.5 + 1.6 * (t - 0.5)) / 1.4))       # kumdan çime gürültülü geçiş
        gc = [g2[i] * (1 - t) + grass[i] * t for i in range(3)]
        c = [sand[i] * (1 - g) + gc[i] * g for i in range(3)]
    # kıyı köpüğü: su çizgisinin hemen altında/üstünde kırık beyaz şeritler
    f = max(0.0, 1.0 - abs(d + 0.15) / 0.55)
    f *= max(0.0, mathutils.noise.noise(V((x * 0.9, y * 2.5, 5.0))) * 1.6 + 0.75)
    f = min(1.0, f)
    return [c[i] * (1 - f) + 0.95 * f for i in range(3)]

ground = grid_terrain('ground', 140, 280, h, vcol_mat('ground', 0.85, 0.12), col)

# su: kapalı kutu → yüzeyde kırılma + içte soğurma (derinleştikçe turkuazdan laciverte)
bpy.ops.mesh.primitive_cube_add(size=1)
water = bpy.context.active_object; water.name = 'water'
water.scale = (140, 90, 6); water.location = (0, shore(0) - 45 - 0.02, -3.0 - 0.02)
wm = bpy.data.materials.new('water'); wm.use_nodes = True
nt = wm.node_tree; N = nt.nodes; L = nt.links
b = N['Principled BSDF']; b.inputs['Base Color'].default_value = srgb('#e8fbff'); b.inputs['Roughness'].default_value = 0.03
b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.33
nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.4; nz.inputs['Detail'].default_value = 6
bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.06; L.new(nz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
va = N.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = srgb('#12d6d2'); va.inputs['Density'].default_value = 0.22
L.new(va.outputs[0], N['Material Output'].inputs['Volume'])
water.data.materials.append(wm)

# kayalık burun (solda) + denizdeki kayalar; üstleri yosun/çim
rm = rock_mat('cliff', base='#a29d95', dark='#6e6b6a', moss_amt=0.55, warm='#c3b49c')
rnd = random.Random(11)
rocks = []
for i, (x, y, s, fl) in enumerate([(-15, 7, 11, 0.6), (-23, 1, 9.0, 0.65), (-8, 11, 7.0, 0.55), (-27, -8, 6.5, 0.7), (-12, -4, 2.2, 0.6),
                                    (-6, -2.5, 0.9, 0.6), (-3, -6, 1.3, 0.55), (9, -14, 3.2, 0.7), (14, -12, 1.4, 0.6)]):
    rocks.append(rock('c%d' % i, (x, y, h(x, y) + s * 0.22), s, rm, seed=40 + i, flat=fl, sharp=0.9, rot=rnd.uniform(0, 6.3)))
# kumsalda küçük çakıl ve deniz kabukları
pm = rock_mat('peb', base='#b8b1a6', dark='#8d877e', moss_amt=0.0)
for i in range(26):
    x = rnd.uniform(-6, 18); y = shore(x) + rnd.uniform(0.4, 4.5)
    rock('p%d' % i, (x, y, h(x, y) + 0.02), rnd.uniform(0.06, 0.16), pm, seed=500 + i, flat=0.5, sharp=0.4, sub=2, rot=rnd.uniform(0, 6.3))

# kumsalın üstünde çim teli şeridi
gm = grass_mat('grass', base='#3b7a1c', tip='#c2e65a', translucent=0.35)
rg = random.Random(3); pts = []
for i in range(380000):
    x = rg.uniform(-40, 45); y = rg.uniform(2, 40)
    d = y - shore(x)
    if d < 5.0 + 1.6 * (mathutils.noise.noise(V((x * 0.4, y * 0.4, 3.0))) * 0.5): continue
    if any((V((x, y)) - o.location.xy).length < o.scale.x * 0.9 for o in rocks): continue
    k = 1.0 + max(0.0, y - 12) / 9.0
    if rg.random() < (k - 1.0) * 0.45: continue
    pts.append((x, y, h(x, y) - 0.01, k))
blades('grass', pts, gm, h=(0.12, 0.3), w=(0.02, 0.045), bend=0.5)
daisies('cicek', pts[::160], petal='#ffffff', r=(0.03, 0.05))

camera((9.0, -16.0, 5.2), (-3.0, 3.5, 0.8), lens=26)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('OK', out)
