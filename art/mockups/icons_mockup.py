# Geri bildirim 6 (19 Ekim 2026) görsel taslak: minimal HUD simgeleri. Kullanım:
#   python3.11 -I icons_mockup.py -- <çıktı klasörü>
# Tek dil: kalın, yuvarlak hatlı, tek ana renk + tek vurgu, ince parça yok; aynı ışık, aynı kamera, aynı doluluk.
# Oyunun "vinyl oyuncak" diliyle uyumlu ama daha sade (bugünkü simgeler farklı ölçek ve ayrıntıda).
import bpy, math, sys, os, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code3d'))
import kit
from kit import srgb, mat, blob, rbox, cyl, tube
V = mathutils.Vector
outdir = sys.argv[sys.argv.index('--') + 1]
os.makedirs(outdir, exist_ok=True)

def scene():
    sc = kit.reset()
    sc.cycles.samples = 40
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 256
    for o in list(sc.collection.objects):
        if o.type == 'LIGHT': bpy.data.objects.remove(o)
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(12)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(40), math.radians(-28), math.radians(-20))
    rim = bpy.data.lights.new('rim', 'AREA'); rim.energy = 120; rim.size = 3; rim.color = (1.0, 0.97, 0.92)
    ro = bpy.data.objects.new('rim', rim); sc.collection.objects.link(ro); ro.location = (2.5, -2, 2.5); ro.rotation_euler = (math.radians(55), 0, math.radians(50))
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.1
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = 2.5
    co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, -6, 0); co.rotation_euler = (math.radians(90), 0, 0)
    return sc

def M(h, rough=0.42, coat=0.15): return mat('m' + h, h, rough, coat)

def curve2d(name, pts, depth=0.22, bevel=0.1, m=None, closed=True):
    """2B kapalı şekil (x,z) → kalın, kenarı yuvarlatılmış katı (kalp, yıldız, ok, üçgen)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = depth; cu.bevel_depth = bevel; cu.bevel_resolution = 6; cu.resolution_u = 24
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (x, z) in zip(sp.points, pts): p.co = (x, z, 0, 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90), 0, 0)
    if m: o.data.materials.append(m)
    return o

def bez2d(name, pts, depth=0.22, bevel=0.1, m=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = depth; cu.bevel_depth = bevel; cu.bevel_resolution = 6; cu.resolution_u = 32
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, (x, z) in zip(sp.bezier_points, pts):
        p.co = (x, z, 0); p.handle_left_type = p.handle_right_type = 'AUTO'
    sp.use_cyclic_u = True
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90), 0, 0)
    if m: o.data.materials.append(m)
    return o

def rounded_poly(pts, r=0.12, n=6):
    """Köşeleri yuvarlatılmış çokgen noktaları."""
    out = []
    k = len(pts)
    for i in range(k):
        p0, p1, p2 = V(pts[i - 1] + (0,)), V(pts[i] + (0,)), V(pts[(i + 1) % k] + (0,))
        a = (p0 - p1).normalized(); b = (p2 - p1).normalized()
        s = p1 + a * r; e = p1 + b * r
        for j in range(n + 1):
            t = j / n
            q = (1 - t) ** 2 * s + 2 * (1 - t) * t * p1 + t ** 2 * e
            out.append((q.x, q.y))
    return out

def render(name):
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(outdir, name + '.png')
    bpy.ops.render.render(write_still=True)

ICONS = {}
def icon(f): ICONS[f.__name__] = f; return f

@icon
def hand():
    m = M('#ffd166')
    blob('palm', (0, 0, -0.25), (0.48, 0.24, 0.46), m)
    for i, (x, h) in enumerate(((-0.34, 0.5), (-0.115, 0.6), (0.115, 0.6), (0.34, 0.5))):
        blob(f'f{i}', (x * 1.04, 0, h * 0.55), (0.12, 0.14, 0.32 if i in (1, 2) else 0.28), m, rot=(0, -x * 18, 0))
    blob('thumb', (-0.58, 0, -0.12), (0.13, 0.15, 0.3), m, rot=(0, -48, 0))

@icon
def axe():
    w = M('#c98a4f', 0.6); st = M('#8f9aa6', 0.35); e = M('#e6eef6', 0.3)
    tube('h', [(-0.25, 0, -0.95), (-0.12, 0, 0.0), (-0.1, 0, 0.85)], [0.12, 0.11, 0.12], w)
    head = curve2d('head', rounded_poly([(-0.22, 0.95), (-0.22, 0.42), (0.25, 0.32), (0.62, 0.05), (0.8, 0.62), (0.62, 1.22), (0.25, 0.98)], 0.1), 0.22, 0.07, st)
    head.location.y = 0.1
    edge = curve2d('edge', rounded_poly([(0.55, 0.12), (0.62, 0.05), (0.8, 0.62), (0.62, 1.22), (0.55, 1.12), (0.7, 0.62)], 0.04), 0.24, 0.06, e)
    edge.location.y = 0.11

@icon
def pickaxe():
    w = M('#c98a4f', 0.6); s = M('#a9bccf', 0.35)
    tube('h', [(0.0, 0, -0.95), (0.0, 0, 0.0), (0.0, 0, 0.6)], [0.12, 0.11, 0.12], w)
    tube('head', [(-0.85, 0, 0.22), (-0.45, 0, 0.62), (0.0, 0, 0.76), (0.45, 0, 0.62), (0.85, 0, 0.22)],
         [0.08, 0.17, 0.21, 0.17, 0.08], s)

@icon
def heart():
    pts = []
    for i in range(72):
        t = i / 72 * math.tau
        pts.append((16 * math.sin(t) ** 3 / 17, (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 17 + 0.1))
    pts = pts[1:36] + pts[37:]          # iki sivri ucu (üst çentik, alt uç) kaldır: kalın kenar yuvarlatması sivri çıkıntı yapmasın
    curve2d('heart', pts, 0.22, 0.1, M('#ff5a6e'))

@icon
def apple():
    r = M('#ff5b4d'); g = M('#5fcf6a'); b = M('#8a5a2b', 0.6)
    blob('a', (0, 0, -0.12), (0.72, 0.6, 0.68), r)
    blob('dimple', (0, -0.05, 0.5), (0.18, 0.18, 0.08), M('#d8443a'))
    tube('stem', [(0, 0, 0.45), (0.03, 0, 0.7), (0.12, 0, 0.86)], [0.07, 0.065, 0.06], b)
    blob('leaf', (0.36, 0, 0.74), (0.28, 0.07, 0.14), g, rot=(0, -28, 0))

@icon
def soap():
    p = M('#8fd3ff', 0.3, 0.4); wb = M('#ffffff', 0.2, 0.3)
    rbox('bar', (0, 0, -0.25), (1.7, 0.7, 0.8), p, bevel=0.28, seg=6)
    for (x, z, r) in ((-0.42, 0.36, 0.22), (0.0, 0.5, 0.28), (0.4, 0.34, 0.18), (0.62, 0.66, 0.12)):
        blob('b', (x, -0.12, z), (r, r, r), wb)

@icon
def jump():
    curve2d('arrow', rounded_poly([(0, 0.9), (0.7, 0.18), (0.3, 0.18), (0.3, -0.8), (-0.3, -0.8), (-0.3, 0.18), (-0.7, 0.18)], 0.12),
            0.2, 0.1, M('#4fd1a5'))

@icon
def enter():
    d = M('#ffb54a', 0.5); k = M('#7a4a1e', 0.4); f = M('#fff4e2', 0.5)
    pts = [(-0.5, -0.85), (0.5, -0.85), (0.5, 0.25)] + [(0.5 * math.cos(a), 0.25 + 0.5 * math.sin(a)) for a in [math.radians(t) for t in range(10, 171, 20)]] + [(-0.5, 0.25)]
    curve2d('frame', [(x * 1.25, z * 1.12 - 0.02) for x, z in pts], 0.12, 0.05, f)
    o = curve2d('door', pts, 0.2, 0.06, d); o.location.y = -0.08
    blob('knob', (0.28, -0.32, -0.15), (0.08, 0.08, 0.08), k)

@icon
def play():
    curve2d('tri', rounded_poly([(-0.45, 0.75), (0.75, 0.0), (-0.45, -0.75)], 0.2), 0.2, 0.12, M('#5bd36b'))

@icon
def star():
    pts = []
    for i in range(10):
        a = math.radians(90 + i * 36); r = 0.92 if i % 2 == 0 else 0.42
        pts.append((r * math.cos(a), r * math.sin(a) - 0.05))
    curve2d('star', rounded_poly(pts, 0.1), 0.22, 0.12, M('#ffc93d', 0.35, 0.3))

@icon
def coin():
    gold = M('#ffc93d', 0.3, 0.35); dark = M('#e9a417', 0.35, 0.3)
    c = cyl('c', (0, 0, 0), 0.85, 0.24, gold, rot=(90, 0, 0), verts=64, bevel=0.1)
    ring = cyl('r', (0, -0.1, 0), 0.62, 0.1, dark, rot=(90, 0, 0), verts=64, bevel=0.03)
    blob('pad', (0, -0.18, -0.1), (0.2, 0.06, 0.16), gold)
    for x, z in ((-0.24, 0.16), (-0.08, 0.28), (0.08, 0.28), (0.24, 0.16)):
        blob('t', (x, -0.17, z), (0.07, 0.05, 0.08), gold)

@icon
def music():
    w = M('#ffffff', 0.35)
    blob('head', (-0.3, 0, -0.55), (0.36, 0.24, 0.27), w, rot=(0, 20, 0))
    tube('stem', [(0.02, 0, -0.5), (0.02, 0, 0.8)], [0.1, 0.1], w)
    tube('flag', [(0.02, 0, 0.76), (0.38, 0, 0.52), (0.46, 0, 0.16)], [0.11, 0.11, 0.08], w)

@icon
def sunstone():
    core = mat('sun', '#ffb21f', 0.25, 0.5, emit=0.25); rim = M('#ff7a1a', 0.3, 0.4); glow = mat('sg', '#fff1a8', 0.2, 0.3, emit=0.6)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.72, location=(0, 0, 0))
    o = bpy.context.object; o.scale = (1.0, 0.6, 1.05); o.data.materials.append(core)
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = 0.06; bv.segments = 3
    for k in range(8):
        a = k / 8 * math.tau
        r_ = blob('ray', (math.cos(a) * 0.86, 0.05, math.sin(a) * 0.86), (0.13, 0.08, 0.22), rim)
        r_.rotation_euler = (0, -a + math.pi / 2, 0)
    blob('hl', (-0.22, -0.42, 0.25), (0.16, 0.05, 0.1), glow)

@icon
def log():
    bark = M('#9a6234', 0.6); cut = M('#f2c98a', 0.55); ring = M('#c78f52', 0.5)
    for (x, z) in ((-0.42, -0.25), (0.42, -0.25), (0.0, 0.35)):
        c = cyl('l', (x, 0, z), 0.4, 1.1, bark, rot=(90, 0, 0), verts=24, bevel=0.06)
        cyl('c', (x, -0.56, z), 0.33, 0.04, cut, rot=(90, 0, 0), verts=24, bevel=0.01)
        cyl('r', (x, -0.58, z), 0.16, 0.02, ring, rot=(90, 0, 0), verts=24, bevel=0.0)

@icon
def twig():
    w = M('#8a5a2e', 0.6); g = M('#5fcf6a')
    tube('t', [(-0.85, 0, -0.75), (-0.1, 0, 0.0), (0.8, 0, 0.8)], [0.11, 0.09, 0.07], w)
    tube('b', [(0.0, 0, 0.08), (0.25, 0, 0.5), (0.2, 0, 0.82)], [0.07, 0.06, 0.05], w)
    blob('lf', (0.32, 0, 0.92), (0.2, 0.06, 0.11), g, rot=(0, -40, 0))

@icon
def rocks():
    rr = [M('#a9a59c', 0.7, 0.05), M('#8f8b83', 0.7, 0.05)]
    for i, (x, z, sx, sz) in enumerate(((-0.4, -0.3, 0.55, 0.42), (0.38, -0.36, 0.48, 0.36), (0.0, 0.25, 0.5, 0.4))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, 0, z))
        o = bpy.context.object; o.scale = (sx, 0.4, sz); o.data.materials.append(rr[i % 2])
        import random as _r; rn = _r.Random(i)
        for v in o.data.vertices: v.co *= rn.uniform(0.9, 1.08)
        sd = o.modifiers.new('s', 'SUBSURF'); sd.levels = sd.render_levels = 1
        for pl in o.data.polygons: pl.use_smooth = True

@icon
def hammer():
    w = M('#c98a4f', 0.6); s = M('#8f9aa6', 0.35)
    tube('h', [(0.0, 0, -0.95), (0.0, 0, 0.0), (0.0, 0, 0.45)], [0.11, 0.1, 0.11], w)
    rbox('head', (0.05, 0, 0.6), (1.1, 0.42, 0.42), s, bevel=0.12, seg=4)

only = sys.argv[sys.argv.index('--') + 2:] if len(sys.argv) > sys.argv.index('--') + 2 else None
for name, build in ICONS.items():
    if only and name not in only: continue
    scene(); build()
    render(name)
    print('ok', name, flush=True)
