# Komik giyilebilir eşyalar B (kullanıcı, 23 Ekim 2026; kodla yapılanlar): akvaryum kask (+ dönen japon balıkları),
# kalp gözlük, bıyıklı burun gözlük, şnorkel + dalış gözlüğü, kahraman maskesi.
# Dil assets_items ile aynı: parlak "vinyl oyuncak" yüzeyler, tıknaz yuvarlak biçimler, pişirilmiş renk + yumuşak AO,
# dış çizgi yok. Oyunun gölgelendiricisi opak: cam/su saydam değil, açık renk + boyalı beyaz parlama şeritleriyle okunur.
# Yön: ön = Blender −Y, yukarı = +Z. Ölçü: parçalar "pet boyu = 1" biriminde kurulur (yüz ölçüleri çocuk Okti'den:
# göz hizası z = 0, göz hizasında yüzün önü y = 0, gözler x = ±0,049), sonda U kat büyütülür (AO/pah ölçeği diğer eşyalarla aynı).
# Göz eşyalarında sınır kutusu merkezi göz hizasına gelir (oyun "up" kullanmaz) → üst/alt taşmalar dengeli tutulur.
# Kullanım: python -I assets_wear_b.py -- <çıktı_klasörü> [w_hat_fishbowl ...]   (oyuna: export_game.py <id>)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets_town import *
import assets_town as T
import assets_v3 as A
from mathutils import Matrix

U = 2.5          # pet boyu birimi → model birimi

# ------------------------------------------------------------------ çocuk Okti'nin yüzü (fit_test_okti ölçümü, pet boyu birimi)

def face_back(x, z):
    """Göz hizasındaki en ön noktaya göre yüz yüzeyinin ne kadar geride olduğu (yanlara ve yukarı doğru kubbe).
    Göz hizasının 0,045 altında ortada ağız öne taşar (orada eşya parçası olmamalı)."""
    return 1.6 * x * x + (0.28 * z + 1.8 * z * z if z > 0 else 0.0)

# ------------------------------------------------------------------ malzemeler

def gloss(hexc, name=None, var=0.05):
    """Parlak vinyl düz renk (çok hafif dalgalanma)."""
    return A.m_flat(hexc, var, 5, name or ('gl' + hexc))

def m_paint(name, base, layers, var=0.05, noise_scale=5):
    """Düz renk + nesne koordinatına bağlı boya katmanları (parlama şeridi, su çizgisi, çakıl…).
    layers: [(fn(G, X, Y, Z) → 0..1, renk)]; renk '#hex' ya da fn(G, X, Y, Z) → renk soketi. X, Y, Z pet boyu biriminde.
    Pişirmede tüm parçalar dünya koordinatında birleşir → önizlemede de dönüşümler uygulanmış olmalı (finalize)."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links
        o = G.obj(); sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
        X, Y, Z = (G.math('DIVIDE', sp.outputs[k], U) for k in ('X', 'Y', 'Z'))
        col = G.mix(var, base, G.noise(o, noise_scale, 2, out='Color'), 'OVERLAY') if var else G.mix(0.0, base, base)
        for fn, c in layers:
            cc = c(G, X, Y, Z) if callable(c) else c
            col = G.mix(fn(G, X, Y, Z), col, cc)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_hair(c1, c2, name):
    """Gür kıl (kaş, bıyık): yatay uzun lif çizgileri + koyu dip, açık uçlar."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        st = G.noise(G.mapping(o, (2.5, 70, 55)), 1.0, 3, 0.6)
        col = G.mix(G.rng(st, 0.35, 0.65), c1, c2)
        col = G.mix(G.rng(G.noise(o, 9, 3), 0.45, 0.7, 0, 0.35), col, _shade(c1, 0.6), 'MIX')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

# maske yardımcıları (düğüm soketleriyle)
def smooth_in(G, v, lo, hi, soft):
    """v ∈ [lo, hi] → 1 (kenarlar 'soft' genişlikte yumuşak)."""
    return G.math('MULTIPLY', G.rng(v, lo - soft, lo + soft), G.rng(v, hi - soft, hi + soft, 1.0, 0.0))

def rot2(G, X, Z, cx, cz, ang):
    """(X, Z) noktasını (cx, cz) etrafında −ang döndürülmüş yerel eksenlere: (boyuna, enine)."""
    dx = G.math('SUBTRACT', X, cx); dz = G.math('SUBTRACT', Z, cz)
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    u = G.math('ADD', G.math('MULTIPLY', dx, c), G.math('MULTIPLY', dz, s))
    v = G.math('SUBTRACT', G.math('MULTIPLY', dz, c), G.math('MULTIPLY', dx, s))
    return u, v

def stroke(cx, cz, ang, length, width, soft=0.004, bow=0.0):
    """Düz/kavisli parlama çizgisi maskesi (x–z düzleminde; y'den bağımsız)."""
    def fn(G, X, Y, Z):
        u, v = rot2(G, X, Z, cx, cz, ang)
        if bow: v = G.math('SUBTRACT', v, G.math('MULTIPLY', G.math('MULTIPLY', u, u), bow))
        a = smooth_in(G, u, -length / 2, length / 2, soft); b = smooth_in(G, v, -width / 2, width / 2, soft * 0.6)
        # uçlar sivri: genişlik uca doğru daralır
        taper = G.rng(G.math('ABSOLUTE', u), length * 0.25, length * 0.5, 1.0, 0.25)
        b2 = smooth_in(G, G.math('DIVIDE', v, G.math('MAXIMUM', taper, 0.05)), -width / 2, width / 2, soft * 0.6)
        return G.math('MULTIPLY', a, G.math('MINIMUM', b, b2))
    return fn

def dot(cx, cz, r, soft=0.003):
    def fn(G, X, Y, Z):
        d = G.math('SQRT', G.math('ADD', G.math('POWER', G.math('SUBTRACT', X, cx), 2.0), G.math('POWER', G.math('SUBTRACT', Z, cz), 2.0)))
        return G.rng(d, r + soft, r - soft)
    return fn

def union(*fns):
    def fn(G, X, Y, Z):
        out = fns[0](G, X, Y, Z)
        for f in fns[1:]: out = G.math('MAXIMUM', out, f(G, X, Y, Z))
        return out
    return fn

# ------------------------------------------------------------------ biçim yardımcıları

def realize(o):
    """Değiştiricileri ve dönüşümü meshe uygula (eğri → mesh)."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if o.type == 'CURVE':
        bpy.ops.object.convert(target='MESH')
        o = bpy.context.object
    for md in list(o.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=md.name)
        except Exception: o.modifiers.remove(md)
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    return o

def finalize():
    """Her şey mesh, dönüşümler uygulanmış, U kat büyük (dışa aktarım ve önizleme aynı koordinatı görür)."""
    for o in list(bpy.context.scene.objects):
        if o.type not in ('MESH', 'CURVE'): continue
        o = realize(o)
        o.data.transform(Matrix.Scale(U, 4))
        for p in o.data.polygons: p.use_smooth = True
        o.data.update()

def catmull(pts, n=8, closed=True):
    """Kontrol noktalarından yumuşak kapalı/açık eğri (x, z)."""
    out = []; N = len(pts)
    rng = range(N) if closed else range(N - 1)
    for i in rng:
        p0 = pts[(i - 1) % N] if closed or i > 0 else pts[0]; p1 = pts[i]; p2 = pts[(i + 1) % N]
        p3 = pts[(i + 2) % N] if closed or i + 2 < N else pts[-1]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    if not closed: out.append(pts[-1])
    return out

def mirror_half(half):
    """Sağ yarı kontrol noktaları (x ≥ 0, üst ortadan saat yönünde alt ortaya) → simetrik kapalı çevre."""
    left = [(-x, z) for (x, z) in reversed(half[1:-1])]
    return half + left

def flat_shape(name, loops, depth, bevel, m, bres=3, loc=(0, 0, 0), yaw=0.0):
    """x–z düzleminde 2B biçim (ilk halka dış çevre, içtekiler delik) → y boyunca 'depth' kalınlık, yuvarlak pahlı kenar."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = max(0.0, depth / 2 - bevel); cu.bevel_depth = bevel; cu.bevel_resolution = bres
    for pts in loops:
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for p, (x, z) in zip(sp.points, pts): p.co = (x, z, 0, 1)
        sp.use_cyclic_u = True
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (math.radians(90), 0, math.radians(yaw))
    o.data.materials.append(m)
    return realize(o)

def remesh(o, vs, smooth_iter=0):
    o = realize(o)
    md = o.modifiers.new('rm', 'REMESH'); md.mode = 'VOXEL'; md.voxel_size = vs; md.use_smooth_shade = True
    if smooth_iter:
        sm = o.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); sm.iterations = smooth_iter; sm.smooth_type = 'SIMPLE'
    return realize(o)

def bend(o, fn):
    """Her köşe y'de fn(x, z) kadar kayar (yüz kubbesine sarılma)."""
    for v in o.data.vertices: v.co.y += fn(v.co.x, v.co.z)
    o.data.update(); return o

def fur(o, amt, scale, seed=0):
    """Gür kıl yumruları: yüzey normali boyunca gürültüyle şişir (kaş, bıyık)."""
    o = realize(o)
    for v in o.data.vertices:
        p = v.co * scale + V((seed, seed * 2, 0))
        d = mnoise.noise(p) * 0.6 + mnoise.noise(p * 2.7) * 0.4
        v.co += v.normal * d * amt
    o.data.update(); return o

def fix_normals(o):
    """Kapalı parçalarda normaller dışa (Unity arka yüzleri çizmez)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return o

def ytube(name, pts, radii, m, res=6, bres=3):
    t = tube(name, pts, radii, m, res=res); t.data.bevel_resolution = bres
    return realize(t)

def report(tag):
    pts = [o.matrix_world @ v.co for o in bpy.context.scene.objects if o.type == 'MESH' for v in o.data.vertices]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    print('ÖLÇÜ', tag, 'min', [round(x / U, 4) for x in mn], 'max', [round(x / U, 4) for x in mx],
          'merkez', [round((a + b) / 2 / U, 4) for a, b in zip(mn, mx)], flush=True)

# ------------------------------------------------------------------ 1) Akvaryum kask

BOWL_RX, BOWL_RZ, BOWL_CZ = 0.25, 0.2, 0.205      # cam küre (yarıçaplar, merkez yüksekliği)
BOWL_BASE, BOWL_NECK, WATER = 0.04, 0.36, 0.345   # taban kesiti, boyun kesiti, su yüzeyi
FISH_R = 0.098                                     # balıkların yörünge yarıçapı

def bowl_r(z):
    t = (z - BOWL_CZ) / BOWL_RZ
    return BOWL_RX * math.sqrt(max(0.0, 1 - t * t))

def _bowl_glass():
    ZW = WATER
    def below(G, X, Y, Z): return G.rng(Z, ZW + 0.004, ZW - 0.004)
    def wline(G, X, Y, Z): return smooth_in(G, Z, ZW - 0.012, ZW - 0.004, 0.002)
    def meniscus(G, X, Y, Z): return smooth_in(G, Z, ZW - 0.004, ZW + 0.002, 0.0015)
    def gravel(G, X, Y, Z):
        nz = G.noise(G.obj(), 3.0, 2)
        return G.rng(G.math('ADD', Z, G.math('MULTIPLY', nz, 0.02)), 0.085, 0.07)
    def gravel_col(G, X, Y, Z):
        # çakıl taneleri: hücre rengi (mercan, kum sarısı, krem, deniz yeşili, lila) cam rengiyle yumuşatılmış
        cell = G.vor(G.obj(), 13.0, out='Color')
        rp = G.n.new('ShaderNodeValToRGB'); rp.color_ramp.interpolation = 'CONSTANT'
        el = rp.color_ramp.elements
        stops = [(0.0, '#f08a78'), (0.2, '#f2cf7a'), (0.4, '#f6ecd8'), (0.6, '#5cc2a8'), (0.8, '#b79ae0')]
        while len(el) < len(stops): el.new(0.5)
        for e, (p, c) in zip(el, stops): e.position = p; e.color = srgb(c)
        sp = G.n.new('ShaderNodeSeparateColor'); G.l.new(cell, sp.inputs[0]); G.l.new(sp.outputs[0], rp.inputs['Fac'])
        edge = G.rng(G.vor(G.obj(), 13.0, 'DISTANCE_TO_EDGE'), 0.0, 0.08)
        c = G.mix(0.25, rp.outputs[0], '#8fdcd2')
        return G.mix(edge, '#5aa8a0', c)
    def theta_band(t0, w, z0, z1, soft=0.012):
        def fn(G, X, Y, Z):
            th = G.math('ARCTAN2', Y, X)
            d = G.math('ABSOLUTE', G.math('SUBTRACT', th, math.radians(t0)))
            # z boyunca uçlara doğru incelen şerit
            zc = (z0 + z1) / 2; zh = (z1 - z0) / 2
            zz = G.math('ABSOLUTE', G.math('DIVIDE', G.math('SUBTRACT', Z, zc), zh))
            wz = G.math('MULTIPLY', G.math('SUBTRACT', 1.0, G.math('POWER', zz, 2.0)), math.radians(w))
            a = G.rng(G.math('SUBTRACT', d, wz), 0.02, -0.02)
            return G.math('MULTIPLY', a, G.rng(zz, 1.0, 0.85))
        return fn
    hl = []
    for off in (0, 180):          # önden ve arkadan bakınca (oyun kamerası arkada) parlama görünsün
        hl += [theta_band(-128 + off, 8, 0.07, 0.31), theta_band(-104 + off, 3.2, 0.2, 0.3), theta_band(-58 + off, 2.5, 0.1, 0.2)]
    layers = [(below, '#8ad8cf'), (gravel, gravel_col), (wline, '#3e9fa3'), (meniscus, '#e9fbf7'), (union(*hl), '#ffffff')]
    return m_paint('bowlglass', '#d6f3ef', layers, var=0.03)

def _water():
    def ring(r0, w):
        def fn(G, X, Y, Z):
            rr = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', X, X), G.math('MULTIPLY', Y, Y)))
            wob = G.math('MULTIPLY', G.noise(G.obj(), 4.0, 2), 0.012)
            return smooth_in(G, G.math('ADD', rr, wob), r0 - w, r0 + w, w * 0.6)
        return fn
    def sparkle(G, X, Y, Z):
        return G.rng(G.noise(G.mapping(G.obj(), (1, 1, 1)), 5.0, 3), 0.66, 0.7)
    layers = [(ring(0.058, 0.006), '#7fe3e0'), (ring(0.135, 0.007), '#7fe3e0'), (ring(0.098, 0.004), '#5cd6d6'), (sparkle, '#e8fffd'),
              (ring(0.168, 0.01), '#bdf2ee')]
    return m_paint('water', '#2fbac6', layers, var=0.06, noise_scale=3)

def fishbowl(spin=False):
    R = random.Random(7)
    if not spin:
        GL = _bowl_glass()
        # cam kabuk: dış yüz (taban → gövde → boyun), dudak, iç yüz suyun biraz altına kadar (üstten bakınca görünür)
        prof = [(0.001, 0.055), (0.06, 0.05), (0.1, 0.035), (0.112, 0.016), (0.118, 0.004), (0.126, 0.0), (0.134, 0.006), (0.138, 0.02)]
        n = 26
        for k in range(n + 1):
            z = BOWL_BASE + (BOWL_NECK - BOWL_BASE) * k / n
            prof.append((bowl_r(z) + 0.0, z))
        rn = bowl_r(BOWL_NECK)
        prof += [(rn + 0.004, BOWL_NECK + 0.008), (rn + 0.014, BOWL_NECK + 0.014), (rn + 0.02, BOWL_NECK + 0.024),
                 (rn + 0.016, BOWL_NECK + 0.034), (rn + 0.006, BOWL_NECK + 0.037), (rn - 0.006, BOWL_NECK + 0.03), (rn - 0.012, BOWL_NECK + 0.016)]
        for k in range(1, 4):
            z = BOWL_NECK - (BOWL_NECK - WATER + 0.01) * k / 3
            prof.append((bowl_r(z) - 0.013, z))
        o = T.lathe('bowl', prof, GL, segs=56)
        # normaller dışa: dış yüzün ortasındaki bir yüz merkezden uzağa bakmalı
        me = o.data; me.update()
        mid = max(me.polygons, key=lambda p: (p.center.z > 0.15 and p.center.z < 0.25) * (p.center.x ** 2 + p.center.y ** 2))
        if mid.normal.dot(V((mid.center.x, mid.center.y, 0)).normalized()) < 0:
            bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        # su yüzeyi: hafif dalgacıklı disk
        WT = _water()
        bm = bmesh.new(); rows = []
        NR, NA = 7, 56; rw = bowl_r(WATER) - 0.008
        center = bm.verts.new((0, 0, WATER))
        for j in range(1, NR + 1):
            r = rw * j / NR; row = []
            for i in range(NA):
                a = i / NA * 2 * math.pi
                z = WATER + 0.003 * math.sin(r * 90 + a * 3) * (j / NR)
                row.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
            rows.append(row)
        for i in range(NA): bm.faces.new((center, rows[0][i], rows[0][(i + 1) % NA]))
        for j in range(NR - 1):
            for i in range(NA):
                i2 = (i + 1) % NA; bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][i2], rows[j][i2]))
        bm.normal_update()
        if sum(f.normal.z for f in bm.faces) < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces)
        link_mesh('water', bm, [WT])
        # ortada çakıl adacığı + sudan çıkan yosunlar (balıkların yörüngesinin içinde kalır)
        STN = gloss('#c9b8a6', 'stone'); STN2 = gloss('#e9a08c', 'stone2'); STN3 = gloss('#f3e6c8', 'stone3')
        T.rock((0.0, 0.0, WATER + 0.004), 0.034, STN, 3, sq=(1.15, 1.0, 0.55), sub=2, amt=0.14)
        T.rock((0.03, -0.022, WATER + 0.002), 0.016, STN2, 5, sq=(1.0, 0.9, 0.6), sub=2, amt=0.12)
        T.rock((-0.03, 0.02, WATER + 0.001), 0.014, STN3, 6, sq=(1.0, 1.0, 0.6), sub=2, amt=0.12)
        SW = A.m_leaf('#2f8f45', '#45b45a', '#8edc6a', '#b9ea8a', 'weed')
        def weeds(bm):
            out = []
            for k, (a, L) in enumerate(((-0.3, 0.13), (1.9, 0.105), (3.9, 0.09), (5.2, 0.075))):
                base = V((math.cos(a) * 0.014, math.sin(a) * 0.014, WATER + 0.01))
                d = V((math.cos(a) * 0.25, math.sin(a) * 0.25, 1)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                rows = []
                segs = 6
                for i in range(segs + 1):
                    s = i / segs
                    c = base + d * (L * s) + V((math.cos(a + 1.6) * 0.012 * math.sin(s * 6.0 + k), math.sin(a + 1.6) * 0.012 * math.sin(s * 6.0 + k), 0))
                    w = 0.011 * math.sin(math.pi * min(1.0, 0.25 + s * 0.75)) if i < segs else 0.0
                    rows.append(((bm.verts.new(c + side * w), (s, 1.0)), (bm.verts.new(c + V((0, 0, 0.002))), (s, 0.0)), (bm.verts.new(c - side * w), (s, -1.0))))
                for i in range(segs):
                    (l0, c0, r0), (l1, c1, r1) = rows[i], rows[i + 1]
                    if i < segs - 1: out += [([l0, l1, c1, c0], 0), ([c0, c1, r1, r0], 0)]
                    else: out += [([l0, c1, c0], 0), ([c0, c1, r0], 0)]
            return out
        A.mesh_from_blades('weeds', weeds, [SW])
        # iki minik kabarcık (su yüzeyinde, yosunun dibinde)
        BU = gloss('#f2fffd', 'bubble')
        blob('bub', (0.04, 0.03, WATER + 0.004), (0.008, 0.008, 0.006), BU, sub=0, seg=10)
        blob('bub', (-0.026, -0.04, WATER + 0.003), (0.006, 0.006, 0.005), BU, sub=0, seg=10)
    else:
        # iki japon balığı, yörüngede karşılıklı (180° simetri → dönen parçanın sınır merkezi kasenin ekseninde)
        OR = m_paint('fish', '#ff8a2e', [(lambda G, X, Y, Z: G.rng(Z, WATER + 0.016, WATER + 0.026), '#ffb35c')], var=0.05)
        FIN = gloss('#ffc07a', 'fin'); WH = gloss('#fffaf2', 'eyew'); BK = gloss('#1d1b24', 'eyeb')
        for sgn in (1, -1):
            yaw = 0 if sgn > 0 else 180
            M = Matrix.Rotation(math.radians(yaw), 4, 'Z')
            def P(x, y, z): return tuple(M @ V((x, y, z)))
            # balık +y yönüne yüzer, yörüngenin x = +FISH_R noktasında
            cx = FISH_R; zc = WATER - 0.004
            b = blob('fish', P(cx, 0.0, zc), (0.02, 0.036, 0.021), OR, rot=(0, 0, yaw), sub=1, seg=16)
            blob('head', P(cx, 0.02, zc + 0.002), (0.019, 0.022, 0.019), OR, rot=(0, 0, yaw), sub=1, seg=14)
            # sırt yüzgeci (yuvarlak yelpaze) ve kuyruk (iki loblu)
            d = T.prism('dorsal', [(0.0, 0.0), (0.012, 0.022), (-0.012, 0.03), (-0.03, 0.012), (-0.026, 0.0)], 0.006, FIN, loc=(0, 0, 0), bevel=0.0025)
            d.rotation_euler = (0, 0, math.radians(90 + yaw)); d.location = P(cx, 0.0, zc + 0.016)
            for s2 in (1, -1):
                t = T.prism('tail', [(0.0, 0.0), (-0.026, 0.024 * s2), (-0.036, 0.012 * s2), (-0.03, 0.0)], 0.006, FIN, bevel=0.0025)
                t.rotation_euler = (0, 0, math.radians(90 + yaw)); t.location = P(cx, -0.03, zc + 0.006)
            # iri gözler (başın üstünde, sudan dışarıda)
            for ex in (-1, 1):
                blob('eyew', P(cx + ex * 0.012, 0.028, zc + 0.016), (0.0095, 0.0095, 0.0095), WH, sub=1, seg=12)
                blob('eyeb', P(cx + ex * 0.0145, 0.033, zc + 0.019), (0.0055, 0.0055, 0.0055), BK, sub=0, seg=10)
                blob('glint', P(cx + ex * 0.0135, 0.0365, zc + 0.0225), (0.0018, 0.0018, 0.0018), WH, sub=0, seg=6)
    finalize()
    report('fishbowl_spin' if spin else 'fishbowl')
    return 'akvaryum kask'

def w_hat_fishbowl(): return fishbowl(False)
def w_hat_fishbowl_spin(): return fishbowl(True)

# ------------------------------------------------------------------ 2) Kalp gözlük

def heart_pts(w, h, n=72, fat=0.0):
    """Tombul kalp: klasik eğri, alt ucu kısaltılmış, lobları dolgun; (w, h) kutusuna, merkez (0, 0)."""
    pts = []
    for i in range(n):
        t = i / n * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        if z < -6: z = -6 + (z + 6) * 0.72          # sivri alt ucu kısa, tombul
        pts.append((x * (1 + fat * math.cos(t) ** 2), z))
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    sx = w / (max(xs) - min(xs)); sz = h / (max(zs) - min(zs)); cz = (max(zs) + min(zs)) / 2
    return [(x * sx, (z - cz) * sz) for x, z in pts]

def w_glasses_heart():
    FR = gloss('#e8406f', 'heartframe')
    W, H, CX, YAW = 0.176, 0.152, 0.094, 13.0
    for sgn in (-1, 1):
        cx = sgn * CX
        outer = heart_pts(W, H, fat=0.04)
        inner = [(x * 0.74, z * 0.72 - 0.004) for x, z in heart_pts(W, H, fat=0.04)]
        fb = face_back(cx, 0) + 0.0
        y0 = fb - 0.012                                   # çerçeve ortası: arka yüzü yüzün önünde
        flat_shape('frame', [outer, [p for p in reversed(inner)]], 0.02, 0.0075, FR, bres=3, loc=(cx, y0, 0), yaw=sgn * YAW)
        # opak pembe cam + beyaz parlama çizgileri (sol üst lobda kavisli çizgi + küçük nokta)
        hl = union(stroke(cx - 0.028 * 1.0, 0.02, 62 if sgn < 0 else 62, 0.05, 0.011, bow=6.0), dot(cx + 0.032, 0.03, 0.0065), stroke(cx + 0.012, -0.036, 30, 0.02, 0.006))
        LN = m_paint('heartlens%d' % sgn, '#ff9fc2', [(lambda G, X, Y, Z: G.rng(Z, 0.04, -0.06, 0, 0.35), '#f77fae'), (hl, '#ffffff')], var=0.03)
        flat_shape('lens', [[(x * 0.99, z * 0.99) for x, z in inner]], 0.008, 0.003, LN, bres=2, loc=(cx, y0 + 0.002, 0), yaw=sgn * YAW)
        # kısa sap: dış kenardan geriye (başın içine girer)
        ox = sgn * (CX + W / 2 * math.cos(math.radians(YAW)) - 0.006)
        oy = y0 + W / 2 * math.sin(math.radians(YAW))
        ytube('arm', [(ox, oy, 0.036), (ox + sgn * 0.01, oy + 0.035, 0.038), (ox + sgn * 0.014, oy + 0.075, 0.034)], [0.0085, 0.008, 0.007], FR, res=4)
    # köprü: iki kalbin iç üst lobları arasında küçük kemer
    ytube('bridge', [(-0.03, face_back(0.03, 0) - 0.018, 0.03), (0.0, -0.016, 0.042), (0.03, face_back(0.03, 0) - 0.018, 0.03)], [0.009, 0.0095, 0.009], FR, res=6)
    finalize(); report('glasses_heart')
    return 'kalp gözlük'

# ------------------------------------------------------------------ 3) Bıyıklı burun gözlük

def w_glasses_nose():
    hl_rings = union(stroke(-0.088, 0.026, 52, 0.03, 0.005, bow=10.0), stroke(0.026, 0.026, 52, 0.03, 0.005, bow=10.0))
    FR = m_paint('noseframe', '#26222b', [(hl_rings, '#77727f')], var=0.03)
    CX = 0.057; RM, RN = 0.044, 0.0115
    for sgn in (-1, 1):
        cx = sgn * CX
        bpy.ops.mesh.primitive_torus_add(major_radius=RM, minor_radius=RN, major_segments=40, minor_segments=12, location=(cx, 0, 0))
        r = bpy.context.object; r.scale = (1, 1, 0.78); r.data.materials.append(FR)
        r.rotation_euler = (math.radians(90), 0, math.radians(sgn * 9)); r.location.y = face_back(cx, 0) - 0.006 - RN * 0.78
        r = realize(r)
        ox = sgn * (CX + RM + RN * 0.6)
        ytube('arm', [(ox, face_back(ox, 0) - 0.02, 0.012), (ox + sgn * 0.006, 0.04, 0.016), (ox + sgn * 0.01, 0.085, 0.012)], [0.008, 0.0075, 0.007], FR, res=4)
    blob('bridge', (0, face_back(0, 0) - 0.012, 0.014), (0.012, 0.008, 0.008), FR, sub=1, seg=12)
    # gür kaşlar (kahverengi, yay biçimi, kıl yumruları)
    HB = m_hair('#4b2e1c', '#7a5236', 'brow')
    for sgn in (-1, 1):
        pts = [(sgn * 0.012, 0, 0.062), (sgn * 0.045, 0, 0.082), (sgn * 0.08, 0, 0.083), (sgn * 0.112, 0, 0.066)]
        pts = [(x, face_back(x, z) - 0.02, z) for x, _, z in pts]
        o = ytube('brow', pts, [0.012, 0.017, 0.015, 0.008], HB, res=6, bres=4)
        fur(o, 0.006, 90.0, seed=sgn + 3)
    # iri pembe plastik burun (köprüden sarkar, ağzın üstüne oturur)
    NS = m_paint('nose', '#f39aa6', [(dot(-0.014, -0.02, 0.006), '#ffd6dc'), (lambda G, X, Y, Z: G.rng(Z, -0.05, -0.068, 0, 0.5), '#d77486')], var=0.03)
    blob('nosebridge', (0, -0.028, -0.004), (0.016, 0.022, 0.026), NS, rot=(-28, 0, 0), sub=1, seg=14)
    blob('nose', (0, -0.058, -0.036), (0.031, 0.034, 0.029), NS, sub=1, seg=18)
    for sgn in (-1, 1):
        blob('wing', (sgn * 0.027, -0.044, -0.045), (0.014, 0.016, 0.014), NS, sub=1, seg=12)
    NO = gloss('#8a3a4a', 'nostril')
    for sgn in (-1, 1):
        blob('nostril', (sgn * 0.013, -0.06, -0.062), (0.007, 0.009, 0.004), NO, sub=0, seg=10)
    # gür bıyık: burnun altında, ağzın üst dudağına konar; uçları yanlara ve yukarı kıvrık
    HM = m_hair('#5a3622', '#8a5a3a', 'stache')
    for sgn in (-1, 1):
        pts = [(sgn * 0.004, -0.083, -0.062), (sgn * 0.045, -0.072, -0.07), (sgn * 0.095, -0.04, -0.062), (sgn * 0.135, -0.01, -0.04), (sgn * 0.148, 0.0, -0.016)]
        o = ytube('stache', pts, [0.019, 0.02, 0.015, 0.009, 0.005], HM, res=8, bres=4)
        fur(o, 0.005, 95.0, seed=sgn + 9)
    finalize(); report('glasses_nose')
    return 'bıyıklı burun gözlük'

# ------------------------------------------------------------------ 4) Şnorkel ve dalış gözlüğü

def goggle_outline(a, b, n=3.2, notch=0.02, cz=0.0, N=96):
    pts = []
    for i in range(N):
        t = i / N * 2 * math.pi
        c, s = math.cos(t), math.sin(t)
        x = a * (abs(c) ** (2 / n)) * (1 if c >= 0 else -1)
        z = b * (abs(s) ** (2 / n)) * (1 if s >= 0 else -1)
        if z < 0: z += notch * math.exp(-(x / 0.034) ** 2)
        pts.append((x, z + cz))
    return pts

def w_glasses_snorkel():
    YF = m_paint('mframe', '#ffc23a', [(lambda G, X, Y, Z: G.rng(Z, 0.02, 0.09, 0, 0.3), '#ffe08a')], var=0.04)
    hl = union(stroke(-0.07, 0.02, 58, 0.075, 0.016), stroke(-0.035, 0.022, 58, 0.045, 0.008), stroke(0.085, -0.02, 58, 0.03, 0.007))
    LN = m_paint('mlens', '#9ad9f2', [(lambda G, X, Y, Z: G.rng(Z, 0.05, -0.05, 0, 0.45), '#5fb8e4'), (hl, '#ffffff')], var=0.02)
    CZ = 0.006
    outer = goggle_outline(0.152, 0.074, notch=0.03, cz=CZ)
    lens = goggle_outline(0.122, 0.05, notch=0.03, cz=CZ)
    wrap = lambda x, z: face_back(x, z) * 0.92
    fr = flat_shape('mframe', [outer, list(reversed(lens))], 0.026, 0.009, YF, bres=3)
    fr = remesh(fr, 0.0028); bend(fr, lambda x, z: wrap(x, z) - 0.003 - 0.013)
    ln = flat_shape('mlens', [[(x * 1.02, (z - CZ) * 1.04 + CZ) for x, z in lens]], 0.008, 0.003, LN, bres=2)
    ln = remesh(ln, 0.0025); bend(ln, lambda x, z: wrap(x, z) - 0.003 - 0.016)
    # kayış uçları (koyu mavi) + toka: çerçevenin iki yanından geriye
    ST = gloss('#2f5fa8', 'strap'); BK = gloss('#e8e4dc', 'buckle')
    for sgn in (-1, 1):
        x0 = sgn * 0.15
        ytube('strap', [(x0, wrap(x0, 0.012) - 0.012, 0.012), (sgn * 0.176, wrap(0.176, 0.012) - 0.006, 0.013), (sgn * 0.195, wrap(0.195, 0.012) + 0.004, 0.013)],
              [0.016, 0.015, 0.014], ST, res=4, bres=2)
        rbox('buckle', (sgn * 0.168, wrap(0.168, 0.012) - 0.016, 0.013), (0.012, 0.006, 0.036), BK, rot=(0, 0, sgn * 22), bevel=0.003)
    # J biçimli şnorkel: ağzın sağ yanındaki ağızlıktan aşağı-yana kıvrılır, yüzün sağında yukarı çıkar, başın üstüne doğru
    TB = m_paint('tube', '#ff7a36', [(lambda G, X, Y, Z: smooth_in(G, Z, 0.06, 0.075, 0.002), '#fff6ea'),
                                    (lambda G, X, Y, Z: smooth_in(G, Z, 0.1, 0.115, 0.002), '#fff6ea')], var=0.04)
    pts = [(0.055, -0.092, -0.098), (0.09, -0.078, -0.132), (0.15, -0.045, -0.128), (0.188, -0.008, -0.075), (0.196, 0.008, 0.0),
           (0.192, 0.03, 0.08), (0.175, 0.07, 0.132)]
    ytube('snorkel', pts, [0.014, 0.0145, 0.0145, 0.0145, 0.0145, 0.0145, 0.0145], TB, res=10, bres=3)
    CP = gloss('#2fb6c4', 'cap')
    blob('cap', (0.172, 0.076, 0.142), (0.024, 0.022, 0.02), CP, rot=(-25, 0, 10), sub=1, seg=14)
    MP = gloss('#2fb6c4', 'mouthp')
    blob('mouthpiece', (0.048, -0.098, -0.096), (0.02, 0.013, 0.016), MP, rot=(0, 0, -30), sub=1, seg=12)
    # boruyu kayışa bağlayan küçük klips
    blob('clip', (0.19, wrap(0.19, 0.03) - 0.02, 0.035), (0.012, 0.012, 0.018), CP, sub=1, seg=10)
    finalize(); report('glasses_snorkel')
    return 'şnorkel'

# ------------------------------------------------------------------ 5) Kahraman maskesi

def w_mask_hero():
    half = [(0.0, 0.046), (0.05, 0.055), (0.11, 0.062), (0.165, 0.068), (0.212, 0.074), (0.2, 0.03), (0.178, -0.022),
            (0.15, -0.062), (0.118, -0.06), (0.085, -0.04), (0.05, -0.034), (0.02, -0.028), (0.0, -0.016)]
    outline = catmull(mirror_half(half), n=10)
    zc = (max(z for _, z in outline) + min(z for _, z in outline)) / 2
    holes = []
    for sgn in (-1, 1):
        cx, cz = sgn * 0.053, zc + 0.0
        hole = []
        for i in range(48):
            t = i / 48 * 2 * math.pi
            x = 0.037 * math.cos(t); z = 0.025 * math.sin(t) * (1 - 0.18 * math.cos(t) * sgn)
            a = math.radians(sgn * 9)
            hole.append((cx + x * math.cos(a) - z * math.sin(a), cz + x * math.sin(a) + z * math.cos(a)))
        holes.append(list(reversed(hole)))
    hl = union(stroke(-0.13, 0.045, 12, 0.07, 0.007, bow=-3.0), stroke(0.12, 0.05, -10, 0.04, 0.005, bow=3.0))
    MK = m_paint('mask', '#7d47d1', [(lambda G, X, Y, Z: G.rng(Z, -0.06, 0.07, 0.25, 0), '#5a2fa8'), (hl, '#e9dcff')], var=0.03)
    o = flat_shape('mask', [outline] + holes, 0.016, 0.0065, MK, bres=3)
    o = remesh(o, 0.0022)
    bend(o, lambda x, z: face_back(x, z) * 0.95 - 0.004 - 0.008)
    finalize(); report('mask_hero')
    return 'kahraman maskesi'

BUILDERS = {'w_hat_fishbowl': (w_hat_fishbowl, 512, None), 'w_hat_fishbowl_spin': (w_hat_fishbowl_spin, 256, None),
            'w_glasses_heart': (w_glasses_heart, 512, None), 'w_glasses_nose': (w_glasses_nose, 512, None),
            'w_glasses_snorkel': (w_glasses_snorkel, 512, None), 'w_mask_hero': (w_mask_hero, 512, None)}

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    OUT = args[0]; only = args[1:] or list(BUILDERS)
    os.makedirs(OUT, exist_ok=True)
    for name in only:
        fn, size, dec = BUILDERS[name]
        reset(); fn(); to_mesh_all()
        for o in bpy.context.scene.objects:
            if o.type == 'MESH' and 'grain' not in o.data.uv_layers: grain_uv(o)
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        tris = export_baked_fbx(f'{OUT}/{name}', objs, size=size, decimate=dec, ao_strength=float(os.environ.get('POFI_AO', '0.55')))
        print(name, 'üçgen', tris, flush=True)
