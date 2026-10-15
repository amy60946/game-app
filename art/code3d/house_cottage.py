# Orijinal ada kulübesi (Pofi'nin evi için deneme), tamamen kodla: kazıklar üstünde ahşap güverte, yatay tahta duvarlar,
# kiremit kiremit mercan çatı, taş baca, turkuaz kapı ve panjurlar, çiçek kasası, fener, korkuluk, fıçı ve sandık.
# Kullanım: python -I house_cottage.py -- <çıktı_klasörü> [unity]
#   unity: düşük çokgen + palet dokusu ile FBX (Resources/Env/g_hut) — oyundaki "Kulübe" inşası
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
ARGS = sys.argv[sys.argv.index('--') + 1:]; OUT = ARGS[0]; UNITY = 'unity' in ARGS; os.makedirs(OUT, exist_ok=True)
import kit
kit.LOW = UNITY
R = random.Random(7)
sc = reset()

WOOD = [mat(f'wood{i}', c, rough=0.75, coat=0) for i, c in enumerate(['#b9794a', '#a8693d', '#c48a57', '#9c6239', '#b27247'])]
DARK = mat('darkwood', '#6e4528', rough=0.8, coat=0)
DECK = [mat(f'deck{i}', c, rough=0.8, coat=0) for i, c in enumerate(['#c99a66', '#bb8b58', '#d3a873'])]
TEAL = mat('teal', '#2fa3a0', rough=0.5, coat=0.15)
CREAM = mat('trim', '#f4e6c6', rough=0.6, coat=0.1)
ROOF = [mat(f'roof{i}', c, rough=0.6, coat=0.1) for i, c in enumerate(['#e0684a', '#d45b3f', '#ea7b58', '#cf6a4d'])]
STONE = [mat(f'stone{i}', c, rough=0.85, coat=0) for i, c in enumerate(['#a9a39a', '#968f86', '#bbb5aa'])]
GLASS = mat('glass', '#9fd8f0', rough=0.1, coat=0.6, emit=0.15)
GOLD = mat('gold', '#f2c14e', rough=0.3, coat=0.5)
LAMP = mat('lamp', '#ffd36b', rough=0.3, coat=0, emit=3.0)
LEAF = mat('leaf', '#4caf50', rough=0.6, coat=0)
FLW = [mat('fpink', '#ff7aa8', 0.5, 0), mat('fyel', '#ffd23f', 0.5, 0), mat('fwht', '#ffffff', 0.5, 0)]

W, D, H = 2.6, 2.2, 1.7          # duvar genişliği (x), derinlik (y), yükseklik
Z0 = 0.38                        # döşeme üstü
TOP = Z0 + H
objs = []

def plank_row(axis, fixed, a0, a1, z, h, holes=()):
    """Yatay tahta sırası; holes = [(a0, a1, z0, z1)] açıklıkları atlar."""
    segs = [(a0, a1)]
    for (h0, h1, hz0, hz1) in holes:
        if z + h / 2 <= hz0 or z - h / 2 >= hz1: continue
        new = []
        for s0, s1 in segs:
            if h1 <= s0 or h0 >= s1: new.append((s0, s1)); continue
            if h0 > s0: new.append((s0, h0))
            if h1 < s1: new.append((h1, s1))
        segs = new
    for s0, s1 in segs:
        if s1 - s0 < 0.05: continue
        c = (s0 + s1) / 2; L = s1 - s0
        jit = R.uniform(-0.8, 0.8)
        if axis == 'x': o = rbox('plank', (c, fixed, z), (L, 0.07, h * 0.94), R.choice(WOOD), rot=(jit, 0, 0), bevel=0.018)
        else: o = rbox('plank', (fixed, c, z), (0.07, L, h * 0.94), R.choice(WOOD), rot=(0, jit, 0), bevel=0.018)
        objs.append(o)

# kazıklar + güverte
for x in (-1.5, 0, 1.5):
    for y in (-1.75, 0, 1.25):
        objs.append(cyl('post', (x, y, 0.15), 0.08, 0.36, DARK, verts=10))
n = 0
y = -1.85
while y < 1.4:
    objs.append(rbox('deck', (0, y + 0.09, Z0 - 0.04), (3.5, 0.17, 0.07), DECK[n % 3], rot=(0, R.uniform(-0.5, 0.5), 0), bevel=0.015)); y += 0.185; n += 1
for i, (yy, zz) in enumerate(((-2.12, 0.22), (-2.38, 0.08))):        # basamaklar
    objs.append(rbox('step', (0, yy, zz), (1.0, 0.26, 0.07), DECK[i], bevel=0.015))
    for sx in (-0.48, 0.48): objs.append(rbox('stepside', (sx, yy + 0.05, zz - 0.06), (0.06, 0.3, 0.14), DARK, bevel=0.01))

# duvarlar (kapı ve pencere açıklıklarıyla)
door = (-0.38, 0.38, Z0, Z0 + 1.2)
winF = (0.62, 1.12, Z0 + 0.65, Z0 + 1.15)
winS = (-0.3, 0.3, Z0 + 0.7, Z0 + 1.15)
rows = int(H / 0.17)
for r in range(rows):
    z = Z0 + 0.085 + r * 0.17
    plank_row('x', -D / 2, -W / 2, W / 2, z, 0.17, holes=(door, winF))
    plank_row('x', D / 2, -W / 2, W / 2, z, 0.17)
    plank_row('y', -W / 2, -D / 2, D / 2, z, 0.17, holes=(winS,))
    plank_row('y', W / 2, -D / 2, D / 2, z, 0.17, holes=(winS,))
for sx in (-1, 1):
    for sy in (-1, 1):
        objs.append(rbox('corner', (sx * W / 2, sy * D / 2, Z0 + H / 2), (0.15, 0.15, H + 0.04), DARK, bevel=0.02))
objs.append(rbox('inner', (0, 0, Z0 + H / 2), (W - 0.1, D - 0.1, H), DARK, bevel=0))     # içi koyu (açıklıktan bakınca)

# kapı: dikey turkuaz tahtalar + çapraz destek + topuz + krem çerçeve
for i in range(4):
    objs.append(rbox('door', (-0.285 + i * 0.19, -D / 2 - 0.01, Z0 + 0.6), (0.18, 0.05, 1.18), TEAL, bevel=0.012))
for zz in (Z0 + 0.25, Z0 + 0.95):
    objs.append(rbox('brace', (0, -D / 2 - 0.045, zz), (0.72, 0.03, 0.09), TEAL, bevel=0.01))
objs.append(blob('knob', (0.25, -D / 2 - 0.08, Z0 + 0.6), (0.04, 0.04, 0.04), GOLD, sub=1, seg=12))
for (cx, cz, sx, sz) in ((-0.44, Z0 + 0.62, 0.1, 1.28), (0.44, Z0 + 0.62, 0.1, 1.28), (0, Z0 + 1.27, 0.98, 0.12)):
    objs.append(rbox('dframe', (cx, -D / 2 - 0.04, cz), (sx, 0.07, sz), CREAM, bevel=0.015))

def window(cx, cy, cz, w, h, axis):
    """Krem çerçeve, haç kayıt, cam, turkuaz panjurlar, altta çiçek kasası."""
    def box(dx, dz, sx, sz, m, depth=0.07, off=0.0):
        if axis == 'x': return rbox('w', (cx + dx, cy - off, cz + dz), (sx, depth, sz), m, bevel=0.012)
        return rbox('w', (cx + (off if cx > 0 else -off), cy + dx, cz + dz), (depth, sx, sz), m, bevel=0.012)
    out = 0.06
    objs.append(box(0, 0, w, h, GLASS, depth=0.02))
    for dz in (-h / 2, h / 2): objs.append(box(0, dz, w + 0.14, 0.08, CREAM, off=out))
    for dx in (-w / 2, w / 2): objs.append(box(dx, 0, 0.08, h + 0.14, CREAM, off=out))
    objs.append(box(0, 0, 0.04, h, CREAM, off=out)); objs.append(box(0, 0, w, 0.04, CREAM, off=out))
    for s in (-1, 1):
        objs.append(box(s * (w / 2 + 0.2), 0, 0.28, h + 0.1, TEAL, off=out + 0.01))
    # çiçek kasası
    objs.append(box(0, -h / 2 - 0.12, w + 0.2, 0.14, WOOD[3], depth=0.16, off=out + 0.06))
    for i in range(7):
        fx = -w / 2 + i * (w / 6)
        fz = cz - h / 2 - 0.02 + R.uniform(0, 0.05)
        if axis == 'x': p = (cx + fx, cy - out - 0.08, fz)
        else: p = (cx + (out + 0.08 if cx > 0 else -out - 0.08), cy + fx, fz)
        objs.append(blob('leaf', p, (0.06, 0.06, 0.05), LEAF, sub=1, seg=10))
        q = (p[0], p[1], p[2] + 0.06)
        objs.append(blob('flower', q, (0.035, 0.035, 0.03), FLW[i % 3], sub=1, seg=10))

window((winF[0] + winF[1]) / 2, -D / 2, (winF[2] + winF[3]) / 2, 0.5, 0.5, 'x')
window(-W / 2, 0, (winS[2] + winS[3]) / 2, 0.6, 0.45, 'y')
window(W / 2, 0, (winS[2] + winS[3]) / 2, 0.6, 0.45, 'y')

# çatı: sırt x yönünde; iki eğim, kiremit sıraları (şaşırtmalı), alt tahta, sırt kapağı
RISE, OVY, OVX = 0.95, 0.38, 0.3
half = D / 2 + OVY
ang = math.atan2(RISE, D / 2)
slope = math.hypot(half, RISE * half / (D / 2))
for side in (-1, 1):
    # alt kaplama
    cy = side * half / 2; cz = TOP + RISE * (1 - (half / 2) / (D / 2)) + 0.02
    objs.append(rbox('roofbase', (0, cy, cz), (W + 2 * OVX, slope, 0.05), DARK, rot=(-side * math.degrees(ang), 0, 0), bevel=0.01))
    rows = int(slope / 0.17)
    for r in range(rows):
        t = 1 - (r + 0.5) / rows                 # 1: saçak, 0: sırt
        yy = side * half * t
        zz = TOP + RISE * (1 - abs(yy) / (D / 2)) + 0.07
        x = -W / 2 - OVX + (0.16 if r % 2 else 0.0)
        while x < W / 2 + OVX - 0.05:
            wdt = min(0.31, W / 2 + OVX - x)
            o = rbox('shingle', (x + wdt / 2, yy, zz), (wdt - 0.02, 0.24, 0.035), R.choice(ROOF),
                     rot=(-side * math.degrees(ang) + R.uniform(-2, 2), R.uniform(-1.5, 1.5), 0), bevel=0.012)
            objs.append(o); x += 0.32
objs.append(cyl('ridge', (0, 0, TOP + RISE + 0.1), 0.09, W + 2 * OVX + 0.05, ROOF[1], rot=(0, 90, 0), verts=14))
# yan alınlıklar: dikey tahtalarla üçgen + yuvarlak tavan penceresi
for sx in (-1, 1):
    k = 0; yy = -D / 2 + 0.1
    while yy < D / 2:
        hh = RISE * (1 - abs(yy) / (D / 2))
        if hh > 0.05: objs.append(rbox('gable', (sx * W / 2, yy, TOP + hh / 2), (0.07, 0.18, hh), WOOD[k % 5], bevel=0.015))
        yy += 0.19; k += 1
    bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.04, location=(sx * (W / 2 + 0.05), 0, TOP + 0.35), rotation=(0, math.radians(90), 0), major_segments=20 if UNITY else 48, minor_segments=6 if UNITY else 12)
    t = bpy.context.object; t.data.materials.append(CREAM); [setattr(p, 'use_smooth', True) for p in t.data.polygons]; objs.append(t)
    objs.append(cyl('attic', (sx * (W / 2 + 0.03), 0, TOP + 0.35), 0.15, 0.03, GLASS, rot=(0, 90, 0), verts=20))
# taş baca (arka eğim)
cz = TOP + 0.35; i = 0
while cz < TOP + RISE + 0.7:
    for dx in (-0.12, 0.12):
        objs.append(rbox('stone', (0.75 + dx + R.uniform(-0.02, 0.02), 0.55, cz), (0.22, 0.42, 0.15), R.choice(STONE), rot=(0, 0, R.uniform(-4, 4)), bevel=0.04, seg=3))
    cz += 0.15; i += 1
objs.append(rbox('chcap', (0.75, 0.55, cz + 0.02), (0.56, 0.5, 0.08), DARK, bevel=0.02))

# fener (kapı yanı), tabela, korkuluk, fıçı, sandık
objs.append(rbox('arm', (-0.7, -D / 2 - 0.12, Z0 + 1.35), (0.05, 0.25, 0.05), DARK, bevel=0.01))
objs.append(rbox('lamp', (-0.7, -D / 2 - 0.22, Z0 + 1.2), (0.14, 0.14, 0.2), LAMP, bevel=0.02))
objs.append(rbox('lamptop', (-0.7, -D / 2 - 0.22, Z0 + 1.32), (0.2, 0.2, 0.05), DARK, bevel=0.015))
objs.append(cyl('sign', (0, -D / 2 - 0.06, TOP - 0.3), 0.15, 0.05, CREAM, rot=(90, 0, 0), verts=24))
for (dx, dz, r) in ((0, -0.03, 0.06), (-0.07, 0.05, 0.028), (-0.025, 0.08, 0.028), (0.025, 0.08, 0.028), (0.07, 0.05, 0.028)):   # pati izi
    objs.append(blob('paw', (dx * 0.75, -D / 2 - 0.095, TOP - 0.3 + dz * 0.75), (r * 0.75, 0.015, r * 0.68), mat('pawm', '#e0684a', 0.5, 0), sub=1, seg=12))
for sx in (-1, 1):
    for yy in (-1.8, -1.45):
        objs.append(rbox('rpost', (sx * 1.65, yy, Z0 + 0.3), (0.08, 0.08, 0.6), DARK, bevel=0.015))
    objs.append(rbox('rail', (sx * 1.65, -1.45, Z0 + 0.58), (0.07, 0.75, 0.07), WOOD[2], bevel=0.015))
    objs.append(rbox('rail2', (sx * 1.65, -1.45, Z0 + 0.32), (0.05, 0.75, 0.05), WOOD[0], bevel=0.012))
bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.22, depth=0.5, location=(1.2, -1.6, Z0 + 0.25))
bar = bpy.context.object; bar.data.materials.append(WOOD[1])
bm = bmesh.new(); bm.from_mesh(bar.data)
for v in bm.verts:
    k = 1 + 0.18 * (1 - (v.co.z / 0.25) ** 2); v.co.x *= k; v.co.y *= k
bm.to_mesh(bar.data); bm.free(); [setattr(p, 'use_smooth', True) for p in bar.data.polygons]; objs.append(bar)
for zz in (Z0 + 0.08, Z0 + 0.42):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.235, minor_radius=0.015, location=(1.2, -1.6, zz), major_segments=20 if UNITY else 48, minor_segments=5 if UNITY else 12); t = bpy.context.object
    t.data.materials.append(DARK); objs.append(t)
objs.append(rbox('crate', (-1.25, -1.55, Z0 + 0.2), (0.4, 0.4, 0.4), WOOD[2], rot=(0, 0, 12), bevel=0.03))
for d in (-0.13, 0, 0.13):
    objs.append(rbox('slat', (-1.25 + d * math.cos(math.radians(12)), -1.55 - 0.205 + d * math.sin(math.radians(12)), Z0 + 0.2), (0.08, 0.02, 0.42), WOOD[3], rot=(0, 0, 12), bevel=0.01))

parts = [o for o in sc.objects if o.type == 'MESH']
if UNITY:
    tris, ncol = export_palette_fbx(f'{OUT}/g_hut', parts)
    print('g_hut üçgen', tris, 'renk', ncol, flush=True); sys.exit(0)
tris = tri_count(parts)
export_glb(f'{OUT}/house_cottage.glb', parts)
outline(parts, width=0.018)
g = ground(14, '#8fd06a')
for (yaw, pitch, tag) in ((-35, 26, 'a'), (0, 12, 'b'), (145, 30, 'c')):
    shoot(sc, f'{OUT}/house_{tag}.png', (0, -0.2, 1.5), 9.5, yaw, pitch, lens=42, size=(1200, 1000))
print('house üçgen', tris, 'parça', len(parts), flush=True)
