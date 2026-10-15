# Ada varlıkları v2 — tamamen kodla, oyun stüdyosu stili (dış çizgi yok, canlı ama dengeli renk, düşük çokgen).
# Her işlev sahneye parçaları kurar ve export_palette_fbx ile oyuna hazır tek mesh + palet dokusu yazar.
# Kullanım: python -I assets_v2.py -- <çıktı_klasörü> [g_palm g_rock g_bush g_flowers g_cloud]
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from kit import _finish
import kit
import mathutils
from mathutils import noise as mnoise

# ------------------------------------------------------------------ yardımcılar

def faces_by_normal(o, rules):
    """Yüzlere yöne göre malzeme ata: rules = [(malzeme, koşul(normal, merkez) → bool)], ilk uyan kazanır."""
    me = o.data
    mats = []
    for m, _ in rules:
        if m.name not in [x.name for x in me.materials]: me.materials.append(m)
        mats.append([x.name for x in me.materials].index(m.name))
    mw = o.matrix_world.to_3x3()
    for p in me.polygons:
        n = (mw @ p.normal).normalized(); c = o.matrix_world @ p.center
        for (m, cond), idx in zip(rules, mats):
            if cond(n, c): p.material_index = idx; break

def lumpy(o, amp, scale, seed=0, flat_below=None):
    """Gürültüyle şişir (taş, çalı, bulut); isteğe bağlı alt düzlük."""
    for v in o.data.vertices:
        p = v.co
        d = mnoise.noise(p * scale + mathutils.Vector((seed * 7.1, seed * 3.3, seed * 1.7)))
        v.co = p + p.normalized() * d * amp
        if flat_below is not None and v.co.z < flat_below: v.co.z = flat_below + (v.co.z - flat_below) * 0.15

def ico(name, loc, r, sub, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(m)
    return o

def smooth(o, on=True):
    for p in o.data.polygons: p.use_smooth = on

# ------------------------------------------------------------------ palmiye

def g_palm():
    """Tombul, kesintisiz kavisli gövde (açık-koyu halka bantları); geniş, uçları sivri, kenarı birkaç çentikli
    9 sarkık yaprak (üstü parlak sarımsı yeşil, altı koyu), tepede 3 genç yaprak; 4 hindistan cevizi."""
    R = random.Random(11)
    H = 4.1; lean = 1.05
    def P(t): return mathutils.Vector((lean * t ** 1.9, 0.12 * math.sin(t * 2.4), H * t))
    def rad(t): return 0.33 - 0.15 * t
    BARK = [mat('bark_a', '#c08a52', 0.8, 0), mat('bark_b', '#9c6638', 0.8, 0)]
    segs = 10
    for i in range(segs):
        ts = [i / segs + k * (1 / segs) / 3 for k in range(4)]
        tube('trunk', [tuple(P(t)) for t in ts], [rad(t) for t in ts], BARK[i % 2], res=2)
    top = P(1.0)
    blob('crown', tuple(top + mathutils.Vector((0, 0, 0.02))), (0.3, 0.3, 0.2), mat('crown', '#86a63e', 0.7, 0), sub=1, seg=12)
    NUT = mat('nut', '#80592b', 0.5, 0.2)
    for k in range(4):
        a = k * 1.6 + 0.4
        blob('nut', tuple(top + mathutils.Vector((math.cos(a) * 0.25, math.sin(a) * 0.25, -0.22 - 0.05 * (k % 2)))), (0.2, 0.2, 0.21), NUT, sub=1, seg=12)
    LT = mat('frond_top', '#7fd04e', 0.5, 0.08); DK = mat('frond_under', '#4ea63f', 0.6, 0)
    TIP = mat('frond_tip', '#b7e36a', 0.5, 0.08); TIPDK = mat('frond_tip_under', '#74bf4a', 0.6, 0)
    fronds = [(f * 2 * math.pi / 9 + 0.15, R.uniform(2.2, 2.6), R.uniform(0.3, 0.45), 1.0) for f in range(9)] + \
             [(f * 2 * math.pi / 3 + 0.9, 1.3, 1.25, 0.7) for f in range(3)]
    for (az, L, rise, wk) in fronds:
        az += R.uniform(-0.1, 0.1)
        d = mathutils.Vector((math.cos(az), math.sin(az), 0)); side = mathutils.Vector((-d.y, d.x, 0))
        steps = 12
        notch = {4, 7, 10}                      # bu noktalarda kenar orta damara doğru çentilir
        bm = bmesh.new(); mids, lefts, rights = [], [], []
        for i in range(steps + 1):
            s = i / steps
            c = top + d * (L * s) + mathutils.Vector((0, 0, rise * L * s - 0.85 * L * s * s))
            w = 0.62 * wk * (math.sin(math.pi * s) ** 0.8) * (1 - 0.15 * s)
            wl = w * (0.45 if i in notch else 1.0); wr = w * (0.45 if (i + 1) in notch else 1.0)
            fold = lambda ww: mathutils.Vector((0, 0, -0.32 * ww))
            mids.append(bm.verts.new(c + mathutils.Vector((0, 0, 0.03))))
            lefts.append(bm.verts.new(c + side * wl + fold(wl) + d * (0.06 if i in notch else 0)))
            rights.append(bm.verts.new(c - side * wr + fold(wr) + d * (0.06 if (i + 1) in notch else 0)))
        for i in range(steps):
            mi = 2 if i >= steps * 0.72 else 0               # uçlar açık ton
            f1 = bm.faces.new((mids[i], lefts[i], lefts[i + 1], mids[i + 1])); f1.material_index = mi
            f2 = bm.faces.new((mids[i], mids[i + 1], rights[i + 1], rights[i])); f2.material_index = mi
        me = bpy.data.meshes.new('frond'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('frond', me); bpy.context.scene.collection.objects.link(o)
        for m in (LT, DK, TIP, TIPDK): o.data.materials.append(m)
        smooth(o, True)
        sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.04; sl.material_offset = 1; sl.offset = -1
    return 'palmiye'

# ------------------------------------------------------------------ kaya

def leaf_blade(bm, base, direction, length, width, up=0.25, curl=0.35):
    """Sivri uçlu, ortası kalkık tek yaprak (4 bölüt); bmesh'e eklenir, yüz listesi döner."""
    d = direction.normalized(); side = d.cross(mathutils.Vector((0, 0, 1))).normalized()
    if side.length < 0.1: side = mathutils.Vector((1, 0, 0))
    pts = []
    n = 4
    for i in range(n + 1):
        s = i / n
        c = base + d * length * s + mathutils.Vector((0, 0, up * length * s - curl * length * s * s))
        w = width * math.sin(math.pi * min(1.0, s * 0.95 + 0.05)) * (1 - 0.2 * s)
        pts.append((bm.verts.new(c + mathutils.Vector((0, 0, 0.012))), bm.verts.new(c + side * w - mathutils.Vector((0, 0, 0.25 * w))),
                    bm.verts.new(c - side * w - mathutils.Vector((0, 0, 0.25 * w)))))
    faces = []
    for i in range(n):
        m0, l0, r0 = pts[i]; m1, l1, r1 = pts[i + 1]
        faces.append(bm.faces.new((m0, l0, l1, m1))); faces.append(bm.faces.new((m0, m1, r1, r0)))
    return faces

def g_rock():
    """Üç yuvarlak kaya kümesi: yumuşak hatlı, sıcak gri; üstte güneş alan açık ton ve yosun şapkası; dibinde ot öbekleri."""
    A = mat('rock_side', '#8f8b97', 0.85, 0); T = mat('rock_top', '#b4b0bb', 0.8, 0); M = mat('moss', '#6a943c', 0.7, 0)
    GR = mat('tuft', '#5fb246', 0.6, 0); GR2 = mat('tuft2', '#8ad35a', 0.6, 0)
    R = random.Random(4)
    for (loc, r, sc, seed) in (((0, 0, 0.5), 0.55, (1.05, 0.95, 1.25), 1), ((0.6, -0.32, 0.26), 0.36, (1.05, 1.0, 1.1), 2), ((-0.52, 0.25, 0.2), 0.3, (1.1, 1.0, 1.0), 3)):
        o = ico('rock', loc, r, 3, A, sc)
        lumpy(o, 0.12 * r, 1.6 / r, seed, flat_below=-0.5 * r)
        smooth(o, True)
        top_z = max((o.matrix_world @ v.co).z for v in o.data.vertices)
        # yosun yalnız tepede tek şapka; açık ton üst yarıda (geçişler yumuşak: tek eşik)
        faces_by_normal(o, [
            (M, lambda n, c, tz=top_z, rr=r: n.z > 0.6 and c.z > tz - rr * 0.32),
            (T, lambda n, c: n.z > 0.3),
            (A, lambda n, c: True)])
    # dipte ot öbekleri
    bm = bmesh.new(); tops = []
    for k in range(7):
        a = R.uniform(0, 6.28); rr = R.uniform(0.55, 0.85)
        base = mathutils.Vector((math.cos(a) * rr, math.sin(a) * rr * 0.8, 0.0))
        for j in range(5):
            b = j * 1.25 + R.uniform(-0.3, 0.3)
            dirv = mathutils.Vector((math.cos(b) * 0.35, math.sin(b) * 0.35, 1.0))
            fs = leaf_blade(bm, base, dirv, R.uniform(0.2, 0.32), 0.035, up=0.0, curl=0.3)
            for f in fs: f.material_index = (j + k) % 2
    me = bpy.data.meshes.new('tufts'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('tufts', me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(GR); o.data.materials.append(GR2); smooth(o, True)
    sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.012
    return 'kaya'

def g_bush():
    """Yaprak yaprak çalı: kubbe yüzeyine dışa bakan ~60 sivri yaprak (üç yeşil tonu, üstte açık), içte koyu dolgu;
    aralarda pembe-beyaz küçük çiçekler."""
    G = [mat('leaf_a', '#4caa3d', 0.6, 0.05), mat('leaf_b', '#3d9636', 0.65, 0), mat('leaf_c', '#78c94e', 0.55, 0.05)]
    CORE = mat('core', '#2f7a2e', 0.8, 0)
    PK = mat('bloom', '#ff8fbc', 0.45, 0.1); WH = mat('bloom_w', '#fff3f6', 0.45, 0.1); YL = mat('bloom_c', '#ffd84a', 0.5, 0)
    R = random.Random(8)
    core = ico('core', (0, 0, 0.42), 0.5, 2, CORE, (1.15, 1.0, 0.85)); smooth(core, True)
    bm = bmesh.new()
    golden = math.pi * (3 - math.sqrt(5))
    N = 64
    for i in range(N):
        zf = 1 - (i / (N - 1)) * 1.15                        # yukarıdan aşağı (alt yarı biraz eksik)
        if zf < -0.15: continue
        rr = math.sqrt(max(0.0, 1 - zf * zf)); th = golden * i
        nrm = mathutils.Vector((math.cos(th) * rr, math.sin(th) * rr, zf))
        base = mathutils.Vector((nrm.x * 0.5 * 1.15, nrm.y * 0.5, 0.42 + nrm.z * 0.5 * 0.85)) * 0.92
        dirv = (nrm + mathutils.Vector((0, 0, 0.35))).normalized()
        fs = leaf_blade(bm, base, dirv, R.uniform(0.28, 0.38), R.uniform(0.09, 0.12), up=0.15, curl=0.55)
        mi = 2 if nrm.z > 0.55 else (i % 2)
        for f in fs: f.material_index = mi
    me = bpy.data.meshes.new('leaves'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('leaves', me); bpy.context.scene.collection.objects.link(o)
    for m in G: o.data.materials.append(m)
    smooth(o, True)
    sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.015
    for i in range(7):
        a = R.uniform(0, 6.28); z = R.uniform(0.45, 0.85)
        p = mathutils.Vector((math.cos(a) * 0.56, math.sin(a) * 0.5, z))
        nrm = (p - mathutils.Vector((0, 0, 0.42))).normalized()
        for j in range(5):
            b = j * 2 * math.pi / 5
            t1 = nrm.cross(mathutils.Vector((0, 0, 1))).normalized(); t2 = nrm.cross(t1)
            q = p + (t1 * math.cos(b) + t2 * math.sin(b)) * 0.045
            blob('pet', tuple(q), (0.04, 0.04, 0.02), PK if i % 3 else WH, sub=0, seg=6)
        blob('fc', tuple(p + nrm * 0.02), (0.022, 0.022, 0.02), YL, sub=0, seg=6)
    return 'çalı'

def g_flowers():
    """Dolgun çiçek öbeği: yaprak rozeti + 9 iri çiçek (5 yuvarlak taç yaprak, sarı göbek), farklı boylar ve renkler."""
    LF = [mat('fleaf', '#56b043', 0.6, 0.03), mat('fleaf2', '#3f9a3a', 0.65, 0)]
    ST = mat('stem', '#469c3a', 0.7, 0); CY = mat('fcenter', '#ffc93a', 0.5, 0.1)
    PET = [mat('p_pink', '#ff6fa3', 0.45, 0.08), mat('p_yel', '#ffd447', 0.45, 0.08), mat('p_wht', '#fff8ee', 0.45, 0.08),
           mat('p_pur', '#b088ff', 0.45, 0.08), mat('p_coral', '#ff8a5c', 0.45, 0.08)]
    R = random.Random(21)
    bm = bmesh.new()
    for k in range(16):
        a = k * 2 * math.pi / 16 + R.uniform(-0.15, 0.15)
        d = mathutils.Vector((math.cos(a), math.sin(a), 0.25))
        fs = leaf_blade(bm, mathutils.Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.02)), d, R.uniform(0.32, 0.45), 0.08, up=0.3, curl=0.7)
        for f in fs: f.material_index = k % 2
    me = bpy.data.meshes.new('rosette'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('rosette', me); bpy.context.scene.collection.objects.link(o)
    for m in LF: o.data.materials.append(m)
    smooth(o, True); sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.012
    for k in range(9):
        a = k * 2.4 + R.uniform(-0.3, 0.3); r = 0.08 + 0.2 * math.sqrt((k + 0.5) / 9)
        h = R.uniform(0.28, 0.5)
        base = mathutils.Vector((math.cos(a) * r * 0.6, math.sin(a) * r * 0.6, 0))
        head = mathutils.Vector((math.cos(a) * r, math.sin(a) * r, h))
        tube('stem', [tuple(base), tuple((base + head) / 2), tuple(head)], [0.016, 0.014, 0.012], ST, res=2)
        pm = PET[k % 5]; size = R.uniform(0.85, 1.15)
        tilt = (head - mathutils.Vector((0, 0, 0))).normalized() * 0.3 + mathutils.Vector((0, 0, 1))
        tilt.normalize(); t1 = tilt.cross(mathutils.Vector((1, 0, 0))).normalized(); t2 = tilt.cross(t1)
        blob('fc', tuple(head + tilt * 0.02), (0.035 * size, 0.035 * size, 0.025 * size), CY, sub=0, seg=8)
        for j in range(5):
            b = j * 2 * math.pi / 5 + a
            q = head + (t1 * math.cos(b) + t2 * math.sin(b)) * 0.06 * size
            blob('pet', tuple(q), (0.05 * size, 0.05 * size, 0.016), pm, sub=0, seg=8)
    return 'çiçek'

# ------------------------------------------------------------------ bulut

def g_cloud():
    """Pamuk bulut: kümelenmiş puflar tek yüzeyde birleşir (voksel), altı düz; az çokgen."""
    W = mat('cloud', '#ffffff', 0.9, 0)
    R = random.Random(5)
    parts = []
    spec = [((0, 0, 0.55), 1.0), ((1.05, 0.1, 0.35), 0.78), ((-1.05, 0, 0.3), 0.8), ((0.45, 0.2, 1.05), 0.7), ((-0.5, 0.1, 0.95), 0.62),
            ((1.75, 0, 0.12), 0.5), ((-1.8, 0, 0.1), 0.48), ((0, 0.55, 0.4), 0.6)]
    for (loc, r) in spec:
        parts.append(ico('puff', loc, r, 3, W, (1, 0.85, 0.9)))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join(); o = bpy.context.object
    rm = o.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.09; bpy.ops.object.modifier_apply(modifier='rm')
    for v in o.data.vertices:
        if v.co.z < 0.05: v.co.z = 0.05 + (v.co.z - 0.05) * 0.2                # alt düz
    cs = o.modifiers.new('cs', 'CORRECTIVE_SMOOTH'); cs.iterations = 12; cs.use_only_smooth = True; bpy.ops.object.modifier_apply(modifier='cs')
    dc = o.modifiers.new('dc', 'DECIMATE'); dc.ratio = 0.25; bpy.ops.object.modifier_apply(modifier='dc')
    smooth(o, True)
    return 'bulut'

BUILDERS = {'g_palm': g_palm, 'g_rock': g_rock, 'g_bush': g_bush, 'g_flowers': g_flowers, 'g_cloud': g_cloud}

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    OUT = args[0]; only = args[1:] or list(BUILDERS)
    os.makedirs(OUT, exist_ok=True)
    kit.LOW = True
    for name in only:
        reset()
        BUILDERS[name]()
        to_mesh_all()
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        tris, ncol = export_palette_fbx(f'{OUT}/{name}', objs)
        print(name, 'üçgen', tris, 'renk', ncol, flush=True)
