# Ada aksiyonları için görseller, tamamen kodla (15 Ekim 2026):
#  simgeler (256², şeffaf): tool_axe, tool_pickaxe, tool_hammer, mat_wood, mat_branch, mat_stone → Resources/Icons
#  oyun modelleri (palet dokulu FBX): g_log (kesilecek kütük), g_site (kulübe inşaat alanı) → Resources/Env/<ad>/
# Kullanım: python -I gather_art.py -- <ikon_klasörü> <çıktı_klasörü>  (sonra g_log.* → Env/g_log/, g_site.* → Env/g_site/)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
import kit
ICONS, ENV = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(ICONS, exist_ok=True); os.makedirs(ENV, exist_ok=True)

def icon_scene():
    sc = reset()
    sc.render.film_transparent = True; sc.cycles.samples = 48
    sc.render.resolution_x = sc.render.resolution_y = 256
    c = bpy.data.cameras.new('c'); c.type = 'ORTHO'; c.ortho_scale = 2.4
    co = bpy.data.objects.new('c', c); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, -6, 0); co.rotation_euler = (math.radians(90), 0, 0)
    return sc

def render_icon(sc, name):
    sc.render.filepath = f'{ICONS}/{name}.png'; bpy.ops.render.render(write_still=True)

BARK = '#7a4a2b'; WOODC = '#e8b57a'; RING = '#c98f55'; HANDLE = '#a8683b'; STEEL = '#b9c7d6'; EDGE = '#eef4fa'; GREEN = '#5fb84f'

def ring_cap(loc, r, rot, normal, depth=0.04):
    """Kesik odun yüzü: açık renk disk + önünde koyu yıllık halkalar. normal: yüzün dışa baktığı yön."""
    o = [cyl('cap', loc, r * 0.97, depth, mat('woodc', WOODC, 0.6, 0), rot=rot, verts=28, bevel=0.01)]
    front = tuple(loc[i] + normal[i] * (depth / 2 + 0.004) for i in range(3))
    for k, rr in enumerate((0.7, 0.42, 0.16)):
        bpy.ops.mesh.primitive_torus_add(major_radius=r * rr, minor_radius=r * 0.035, location=front, rotation=[math.radians(a) for a in rot],
                                         major_segments=20 if kit.LOW else 48, minor_segments=5 if kit.LOW else 12)
        t = bpy.context.object; t.scale = (1, 1, 0.4); t.data.materials.append(mat('ring', RING, 0.6, 0)); o.append(t)
    return o

# ------------------------------------------------------------------ simgeler
# balta: sap + kama biçimli baş (arkası kalın, ağzı ince ve açık renk)
sc = icon_scene()
tube('handle', [(-0.5, 0, -0.95), (-0.12, 0, -0.1), (0.05, 0, 0.75)], [0.075, 0.07, 0.08], mat('handle', HANDLE, 0.55, 0.1))
def wedge(name, x0, x1, h0, h1, t0, t1, cz, m):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(x0, -t0, cz - h0), (x0, t0, cz - h0), (x0, t0, cz + h0), (x0, -t0, cz + h0),
                                    (x1, -t1, cz - h1), (x1, t1, cz - h1), (x1, t1, cz + h1), (x1, -t1, cz + h1)]]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)): bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.03; bv.segments = 3
    o.data.materials.append(m); [setattr(p, 'use_smooth', True) for p in o.data.polygons]
    return o
wedge('head', -0.12, 0.5, 0.17, 0.36, 0.11, 0.05, 0.62, mat('steel', STEEL, 0.25, 0.4))
wedge('edge', 0.48, 0.62, 0.36, 0.4, 0.05, 0.012, 0.62, mat('edge', EDGE, 0.2, 0.5))
render_icon(sc, 'tool_axe')
# açık el (topla): avuç + 4 parmak + başparmak, sıcak sarı (oyun içi "topla" işareti)
sc = icon_scene()
HM = mat('hand', '#ffd45c', 0.45, 0.2)
blob('palm', (0, 0, -0.3), (0.5, 0.22, 0.55), HM)
for i, (x, l) in enumerate(((-0.34, 0.4), (-0.115, 0.48), (0.115, 0.46), (0.34, 0.38))):
    blob(f'f{i}', (x * 1.05, 0, 0.12 + l * 0.42), (0.13, 0.14, l * 0.62), HM, rot=(0, x * 25, 0))
blob('thumb', (-0.5, 0, -0.25), (0.13, 0.14, 0.32), HM, rot=(0, -50, 0))
render_icon(sc, 'tool_hand')
# kazma
sc = icon_scene()
tube('handle', [(0.0, 0, -1.0), (0.02, 0, 0.0), (0.0, 0, 0.6)], [0.075, 0.07, 0.075], mat('handle', HANDLE, 0.55, 0.1))
tube('pick', [(-0.85, 0, 0.35), (-0.4, 0, 0.62), (0.0, 0, 0.7), (0.4, 0, 0.62), (0.85, 0, 0.35)], [0.02, 0.09, 0.13, 0.09, 0.02], mat('steel', '#a3b1c2', 0.3, 0.4))
cyl('collar', (0, 0, 0.66), 0.12, 0.22, mat('band', '#6b7b8f', 0.4, 0.2), verts=16)
render_icon(sc, 'tool_pickaxe')
# çekiç (inşa et)
sc = icon_scene()
tube('handle', [(-0.4, 0, -0.95), (-0.1, 0, 0.0), (0.05, 0, 0.55)], [0.075, 0.07, 0.075], mat('handle', HANDLE, 0.55, 0.1))
rbox('hhead', (0.06, 0, 0.66), (0.9, 0.3, 0.32), mat('steel', '#8e9bad', 0.3, 0.4), rot=(0, -12, 0), bevel=0.06, seg=3)
rbox('face', (0.52, 0, 0.56), (0.1, 0.32, 0.34), mat('edge', EDGE, 0.2, 0.5), rot=(0, -12, 0), bevel=0.04, seg=3)
render_icon(sc, 'tool_hammer')
# odun (iki kesik kütük)
sc = icon_scene()
for (x, z, r) in ((-0.32, -0.25, 0.42), (0.38, -0.3, 0.36), (0.02, 0.32, 0.38)):
    cyl('bark', (x, 0.15, z), r, 0.9, mat('bark', BARK, 0.8, 0), rot=(90, 0, 0), verts=24, bevel=0.03)
    ring_cap((x, -0.31, z), r, (90, 0, 0), (0, -1, 0))
render_icon(sc, 'mat_wood')
# dal
sc = icon_scene()
B = mat('branch', '#8a5a33', 0.7, 0)
tube('b1', [(-0.95, 0, -0.65), (-0.2, 0, -0.05), (0.85, 0, 0.6)], [0.07, 0.06, 0.035], B)
tube('b2', [(-0.2, 0, -0.05), (0.15, 0, 0.45), (0.25, 0, 0.9)], [0.05, 0.04, 0.025], B)
tube('b3', [(0.3, 0, 0.22), (0.65, 0, 0.1), (0.95, 0, 0.12)], [0.04, 0.03, 0.02], B)
L = mat('leaf', GREEN, 0.5, 0.1)
for (x, z, a) in ((0.28, 0.95, 20), (0.98, 0.15, -60), (0.88, 0.66, 10)):
    blob('leaf', (x, -0.02, z), (0.16, 0.04, 0.09), L, rot=(0, a, 0))
render_icon(sc, 'mat_branch')
# taş
sc = icon_scene()
st = blob('stone', (0, 0, -0.05), (0.85, 0.7, 0.62), mat('stone', '#a7a39b', 0.75, 0), seg=32)
bm = bmesh.new(); bm.from_mesh(st.data); R = random.Random(3)
for v in bm.verts: v.co *= 1 + R.uniform(-0.06, 0.06)
bm.to_mesh(st.data); bm.free()
blob('stone2', (0.55, -0.15, -0.35), (0.38, 0.3, 0.28), mat('stone2', '#8f8a82', 0.75, 0), seg=24)
render_icon(sc, 'mat_stone')

# eylem düğmesi simgeleri: zıpla (iki ok), gir (kapı), oyna (üçgen)
sc = icon_scene()
Y = mat('jump', '#ffb21a', 0.4, 0.2)
for dz in (-0.35, 0.3):
    tube('chev', [(-0.6, 0, dz - 0.3), (0, 0, dz + 0.3), (0.6, 0, dz - 0.3)], [0.13] * 3, Y, res=2)
render_icon(sc, 'act_jump')
sc = icon_scene()
rbox('frame', (0, 0.05, -0.05), (1.15, 0.2, 1.75), mat('trim', '#f4e6c6', 0.6, 0.1), bevel=0.08, seg=3)
rbox('door', (0, -0.05, -0.12), (0.85, 0.2, 1.5), mat('teal', '#2fa3a0', 0.5, 0.15), bevel=0.06, seg=3)
for x in (-0.2, 0.2): rbox('slit', (x, -0.16, -0.12), (0.03, 0.02, 1.3), mat('teal2', '#24807d', 0.5, 0.1), bevel=0)
blob('knob', (0.28, -0.2, -0.1), (0.08, 0.06, 0.08), mat('gold', '#f2c14e', 0.3, 0.5), sub=1)
render_icon(sc, 'act_enter')
sc = icon_scene()
bm = bmesh.new()
pts = [(-0.55, 0.75), (-0.55, -0.75), (0.75, 0.0)]
top = [bm.verts.new((x, -0.15, z)) for x, z in pts]; bot = [bm.verts.new((x, 0.15, z)) for x, z in pts]
bm.faces.new(top); bm.faces.new(list(reversed(bot)))
for i in range(3):
    j = (i + 1) % 3; bm.faces.new((top[i], bot[i], bot[j], top[j]))
me = bpy.data.meshes.new('tri'); bm.to_mesh(me); bm.free()
o = bpy.data.objects.new('tri', me); bpy.context.scene.collection.objects.link(o)
bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.12; bv.segments = 4
o.data.materials.append(mat('play', '#3dbb5a', 0.4, 0.3)); [setattr(p, 'use_smooth', True) for p in o.data.polygons]
render_icon(sc, 'act_play')

# ------------------------------------------------------------------ oyun modelleri (düşük çokgen, palet dokusu)
kit.LOW = True
# kesilecek kütük: yatık gövde, kabuk çıkıntıları, iki ucu kesik, küçük dal ve yosun
reset()
objs = []
L0 = 1.6; RR = 0.3
objs.append(cyl('log', (0, 0, RR), RR, L0, mat('bark', BARK, 0.8, 0), rot=(0, 90, 0), verts=14, bevel=0.03))
R2 = random.Random(5)
for i in range(9):   # kabuk çizgileri
    a = R2.uniform(0, math.pi * 2); x = R2.uniform(-0.6, 0.6)
    objs.append(rbox('ridge', (x, math.cos(a) * RR * 0.98, RR + math.sin(a) * RR * 0.98), (R2.uniform(0.3, 0.6), 0.05, 0.05), mat('bark2', '#5e3820', 0.85, 0), rot=(math.degrees(a), 0, 0), bevel=0.015))
for sx in (-1, 1):
    objs += ring_cap((sx * L0 / 2, 0, RR), RR, (0, 90, 0), (sx, 0, 0), depth=0.05)
objs.append(tube('stub', [(0.3, 0, RR * 1.8), (0.38, 0.0, RR * 2.4), (0.5, 0.05, RR * 2.7)], [0.07, 0.05, 0.03], mat('bark', BARK, 0.8, 0)))
for (x, y) in ((-0.35, -0.1), (-0.15, 0.12), (0.55, -0.05)):
    objs.append(blob('moss', (x, y, RR * 1.92), (0.13, 0.11, 0.045), mat('moss', '#7ac45a', 0.7, 0), sub=1, seg=10))
to_mesh_all()
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print('g_log üçgen/renk', export_palette_fbx(f'{ENV}/g_log', objs), flush=True)

# inşaat alanı: köşelerde kazık, aralarında ip, ortada tahta yığını ve küçük tabela
reset()
objs = []
P = mat('stake', '#9c6239', 0.8, 0); ROPE = mat('rope', '#e2c58f', 0.8, 0)
corners = [(-1.4, -1.2), (1.4, -1.2), (1.4, 1.2), (-1.4, 1.2)]
for (x, y) in corners:
    objs.append(cyl('stake', (x, y, 0.3), 0.06, 0.6, P, verts=8))
    objs.append(blob('tip', (x, y, 0.62), (0.07, 0.07, 0.05), P, sub=1, seg=8))
for i in range(4):
    (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
    objs.append(tube('rope', [(ax, ay, 0.5), ((ax + bx) / 2, (ay + by) / 2, 0.42), (bx, by, 0.5)], [0.018] * 3, ROPE))
for k in range(5):
    objs.append(rbox('plank', (0.15 + R2.uniform(-0.05, 0.05), -0.1 + R2.uniform(-0.05, 0.05), 0.05 + k * 0.08), (1.3, 0.22, 0.07),
                     mat(f'pl{k % 3}', ['#c48a57', '#b9794a', '#d29c66'][k % 3], 0.75, 0), rot=(0, 0, R2.uniform(-12, 12)), bevel=0.015))
objs.append(cyl('post', (-0.9, -0.5, 0.35), 0.04, 0.7, P, verts=8))
objs.append(rbox('board', (-0.9, -0.54, 0.72), (0.5, 0.05, 0.3), mat('board', '#f4e6c6', 0.6, 0), bevel=0.02))
objs.append(rbox('mark', (-0.9, -0.575, 0.72), (0.22, 0.02, 0.06), mat('mark', '#e0684a', 0.5, 0), bevel=0.01))
to_mesh_all()
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print('g_site üçgen/renk', export_palette_fbx(f'{ENV}/g_site', objs), flush=True)
