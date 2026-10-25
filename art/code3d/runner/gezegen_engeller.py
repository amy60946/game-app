# Gezegen Koşusu — engeller, toplanabilirler, varış kapısı (25 Ekim 2026). Gerçek boy (m), orijin güverte üstünde (z = 0) ve x/y'de
# ortada; yönlü olanların ÖNÜ Blender −Y'ye (yaklaşan koşucuya) bakar. Kuyruklu yıldızın orijini baş merkezi; toplanabilirler alt orta.
#   rs_block   şerit kapatan asteroit parçası (1,9 × 1,2 × 1,7): kraterli yumru kaya, mor/camgöbeği kristal öbekleri, dipte kırıntı
#   rs_block2  aynı boy: kargo sandığı yığını (nane + mercan), köşe koruyucu, mandal, tutamak, çıkartma; üstte minik çanak + yanıp sönen lamba
#   rs_low     tam genişlik alçak engel (7,0 × 0,8 × ≤ 0,55): ayaklı, mercan/krem çizgili yakıt borusu, flanşlar, vana çarkı, gösterge
#   rs_high    kayılacak kemer: ayaklar x = ±3,5, kiriş x ±3,9, ALT 1,16, üst ~1,72; önde dost halkalı gezegen, uçlarda uyarı şeridi,
#              tepede iki işaret lambası + anten (yetişkin Okti çömelince baş ≈ 1,14 m)
#   rs_crystal ~0,5 m yüzeyli mücevher (mor → camgöbeği) · rs_card ~0,6 m gezegen kartı (mercan çerçeve, halkalı gezegen ekranı)
#   rs_comet   ~0,7 m baş: sevimli yüz +Y'ye (kaçıyor), tombul kuyruk öbekleri −Y'ye (koşucuya doğru)
#   rs_gate    istasyon geçit halkası (dış ~10 m, merkez z 2,5): açıklık x ±3,4, z 0–5 boş; güverte altına kollarla tutturulmuş
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
import uzay_kit as UK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep
import kit
from kit import blob, tube, cyl


def decal(name, wm, hm, draw, ppm=300, depth=0.006, groove=0.003, fade=0.15, chips=0.2, seed=0):
    cv = EK.Canvas(wm, hm, ppm); draw(cv)
    h, over, shade = EK.finish_relief(cv, depth=depth, groove=groove, bevel=0.003, fade=fade, chips=chips, seed=seed, stone_dark=0.0)
    H, W = h.shape; e = max(1, int(0.015 * ppm))
    rx = np.minimum(np.arange(W), np.arange(W)[::-1]) / e; ry = np.minimum(np.arange(H), np.arange(H)[::-1]) / e
    ramp = np.clip(np.minimum(ry[:, None], rx[None, :]), 0, 1)
    h *= ramp; over[..., 3] *= ramp; shade = 1 + (shade - 1) * ramp[..., None]
    return EK.Decal(name, over=over, shade=shade, normal=EK.normal_from_height(h, ppm, (False, False)), ext='CLIP')


def front_dec(o, x0, y, z0, w, h, face=(0, -1, 0)):
    bpy.context.view_layer.update()
    if face[1] < 0: EK.planar_dec_uv(o, (x0, y, z0), (1, 0, 0), (0, 0, 1), w, h, face_dir=face)
    else: EK.planar_dec_uv(o, (x0 + w, y, z0), (-1, 0, 0), (0, 0, 1), w, h, face_dir=face)


def crystal(name, base, direction, length, radius, mat, sides=6, tip=0.38, twist=0.0, bevel=0.006):
    """Altıgen kristal: tabanda biraz daralan gövde + sivri uç; düz gölgeli yüzeyler, ince pah (kenar parlar). Nesnenin kendi +z'si boyunca."""
    bm = bmesh.new(); ring0 = []; ring1 = []
    L1 = length * (1 - tip)
    for k in range(sides):
        a = k / sides * TAU + twist
        ring0.append(bm.verts.new((math.cos(a) * radius * 0.82, math.sin(a) * radius * 0.82, -radius * 0.3)))
        ring1.append(bm.verts.new((math.cos(a) * radius, math.sin(a) * radius, L1)))
    top = bm.verts.new((0, 0, length)); bot = bm.verts.new((0, 0, -radius * 0.6))
    for k in range(sides):
        k2 = (k + 1) % sides
        bm.faces.new((ring0[k], ring0[k2], ring1[k2], ring1[k])); bm.faces.new((ring1[k], ring1[k2], top)); bm.faces.new((ring0[k2], ring0[k], bot))
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = EK.A.link_mesh(name, bm, [mat])
    o.data.polygons.foreach_set('use_smooth', [False] * len(o.data.polygons))
    if bevel:
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = V(direction).normalized().to_track_quat('Z', 'Y'); o.location = base
    return o


def lumpy_rock(name, size, mat, seed=0, sub=4, craters=(), flat=0.0, rough=0.12):
    """Yumru kaya: ikosfer + iki ölçekli gürültü; craters = [(yön, yarıçap, derinlik)] küresel göçük + kabarık kenar; flat: taban düz."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    R = random.Random(seed); so = V((R.uniform(0, 40), R.uniform(0, 40), R.uniform(0, 40)))
    cr = [(V(d).normalized(), r, dpt) for (d, r, dpt) in craters]
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + rough * MN.noise(d * 1.6 + so) + rough * 0.45 * MN.noise(d * 4.2 + so * 1.7) + rough * 0.15 * MN.noise(d * 11 + so)
        for (cd, r, dpt) in cr:
            a = d.angle(cd)
            if a < r * 1.5:
                t = a / r
                k += -dpt * max(0.0, 1 - t * t) + dpt * 0.45 * math.exp(-((t - 1.05) / 0.22) ** 2)
        p = V((d.x * size[0] / 2 * k, d.y * size[1] / 2 * k, d.z * size[2] / 2 * k))
        v.co = p
    o = EK.A.link_mesh(name, bm, [mat]); EK.A.smooth(o)
    if flat is not None:
        zmin = min(v.co.z for v in o.data.vertices)
        for v in o.data.vertices:
            if v.co.z < zmin + flat: v.co.z = zmin + flat + (v.co.z - zmin - flat) * 0.15
        zmin = min(v.co.z for v in o.data.vertices)
        for v in o.data.vertices: v.co.z -= zmin
    return o


# ================================================================== rs_block

def build_block():
    ROCK = UK.m_regolith('astrock', ('#6e6a80', '#928da4', '#b9b4c8'), craters=0.8, dust=0.35, seed=1.0, scale=1.6)
    rock = lumpy_rock('rock', (1.85, 1.15, 1.25), ROCK, seed=4, sub=5, flat=0.18, rough=0.16,
                      craters=[((-0.3, -1, 0.4), 0.34, 0.2), ((0.75, -0.7, 0.15), 0.22, 0.16), ((-0.65, 0.2, 0.9), 0.26, 0.14), ((0.4, 0.8, 0.5), 0.3, 0.16),
                               ((-0.9, -0.5, 0.0), 0.18, 0.12), ((0.2, -0.9, -0.3), 0.14, 0.1)])
    hi = [rock]
    C1 = UK.m_crystal('cryv', UK.VIOLET, UK.CYAN, -0.1, 0.55); C2 = UK.m_crystal('cryc', '#3a6fd1', '#7ff0f0', -0.1, 0.45)
    C3 = UK.m_crystal('cryp', '#8a4fd8', '#f0a8ff', -0.1, 0.4)
    R = random.Random(3)
    clusters = [((0.15, -0.15, 1.05), (0.05, -0.35, 1.0), 0.62, 0.11, C1, 5), ((-0.55, 0.05, 0.95), (-0.5, 0.0, 1.0), 0.42, 0.085, C3, 4),
                ((0.68, -0.35, 0.7), (0.9, -0.5, 0.7), 0.36, 0.075, C2, 4), ((-0.3, -0.52, 0.45), (-0.25, -1.0, 0.35), 0.3, 0.065, C1, 3),
                ((0.35, 0.4, 0.9), (0.3, 0.6, 1.0), 0.34, 0.07, C2, 3)]
    for ci, (base, d, L, r, m, n) in enumerate(clusters):
        d = V(d).normalized()
        for k in range(n):
            jit = V((R.uniform(-0.45, 0.45), R.uniform(-0.45, 0.45), R.uniform(-0.2, 0.3)))
            dd = (d + jit * (0.0 if k == 0 else 1.0)).normalized()
            b = V(base) + V((R.uniform(-0.08, 0.08), R.uniform(-0.08, 0.08), 0)) * (0 if k == 0 else 1)
            hi.append(crystal('cry', tuple(b), tuple(dd), L * (1.0 if k == 0 else R.uniform(0.45, 0.7)), r * (1.0 if k == 0 else R.uniform(0.55, 0.8)),
                              m, twist=R.uniform(0, 1)))
    # dipte kırıntı + minik kristal kırıkları (güvertede)
    for k in range(6):
        a = R.uniform(0, TAU); rr = R.uniform(0.85, 1.0)
        x, y = math.cos(a) * 0.95 * rr, math.sin(a) * 0.6 * rr
        s = R.uniform(0.06, 0.13)
        hi.append(lumpy_rock('pebble', (s * 1.4, s * 1.1, s), ROCK, seed=20 + k, sub=2, flat=s * 0.15, rough=0.2))
        hi[-1].location = (x, y, 0)
    for k in range(3):
        a = R.uniform(-2.6, -0.5); hi.append(crystal('cry', (math.cos(a) * 0.9, math.sin(a) * 0.62, 0.02), (R.uniform(-0.5, 0.5), R.uniform(-0.5, 0.5), 1.0), 0.14, 0.035, C1))
    decim = [(r'^rock$', 700), (r'^cry$', 40), (r'^pebble$', 30)]
    weights = [(r'^rock$', 1.0), (r'^cry$', 1.5), (r'^pebble$', 0.4)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2500, ao_dist=0.3)


# ================================================================== rs_block2

def crate(name, size, loc, paint, rot=0.0, dec=None, seed=0, sticker_face=True):
    """Kargo sandığı: gövde + her yüzde kabarık çerçeve şeritleri, 8 köşe koruyucu (top metal), yan tutamak, ön mandallar."""
    w, d, h = size; x, y, z = loc
    P = UK.m_paint(name + '_p', paint, chips=0.45, dust=0.3, grime=0.45, dec=dec, seed=seed)
    G_ = UK.m_metal(name + '_m', UK.GUN, dust=0.35)
    parts = []
    body = EK.rounded_box(name, (w, d, h), 0.03, 0.03, [P], loc=(0, 0, h / 2), chips=0.006, lump=0.001, seed=seed)
    parts.append(body)
    # kabarık çerçeve: ön/arka yüzlerde dikey + yatay şeritler
    for sy in (-1, 1):
        for (fx, fz, fw, fh) in ((0, 0.06, w - 0.1, 0.06), (0, h - 0.06, w - 0.1, 0.06), (-w / 2 + 0.06, h / 2, 0.06, h - 0.1), (w / 2 - 0.06, h / 2, 0.06, h - 0.1)):
            parts.append(EK.rounded_box(name + '_rib', (fw, 0.025, fh), 0.008, 0.02, [P], loc=(fx, sy * (d / 2 + 0.008), fz), chips=0.003, seed=seed + 1))
    for sx in (-1, 1):
        for (fy, fz, fw, fh) in ((0, 0.06, d - 0.1, 0.06), (0, h - 0.06, d - 0.1, 0.06)):
            parts.append(EK.rounded_box(name + '_rib', (0.025, fw, fh), 0.008, 0.02, [P], loc=(sx * (w / 2 + 0.008), fy, fz), chips=0.003, seed=seed + 2))
        # tutamak
        parts.append(tube(name + '_handle', [(sx * (w / 2 + 0.01), -0.12, h * 0.62), (sx * (w / 2 + 0.06), -0.1, h * 0.66), (sx * (w / 2 + 0.06), 0.1, h * 0.66), (sx * (w / 2 + 0.01), 0.12, h * 0.62)],
                          [0.016] * 4, G_, res=3))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for zz in (0.0, h):
                parts.append(EK.rounded_box(name + '_corner', (0.1, 0.1, 0.1), 0.015, 0.02, [G_], loc=(sx * (w / 2 - 0.035), sy * (d / 2 - 0.035), zz + (0.04 if zz == 0 else -0.04)), seed=seed + 3))
    # ön mandallar
    for lx in (-w * 0.28, w * 0.28):
        parts.append(EK.rounded_box(name + '_latch', (0.09, 0.03, 0.11), 0.008, 0.015, [G_], loc=(lx, -d / 2 - 0.02, h - 0.12), seed=seed + 4))
        parts.append(UK.rivet((lx, -d / 2 - 0.036, h - 0.1), (0, -1, 0), 0.012))
    root = bpy.data.objects.new(name + '_root', None); bpy.context.scene.collection.objects.link(root)
    for p in parts: p.parent = root
    root.location = (x, y, z); root.rotation_euler = (0, 0, math.radians(rot)); bpy.context.view_layer.update()
    for p in parts:
        mw = p.matrix_world.copy(); p.parent = None; p.matrix_world = mw
    bpy.data.objects.remove(root)
    return parts


def build_block2():
    def front1(cv):
        W, H = cv.wm, cv.H / cv.ppm
        UK.d_planet(cv, W * 0.3, H * 0.52, 0.17, body=UK.CORAL, ring=UK.SUN)
        UK.d_hazard(cv, W * 0.55, H * 0.15, W * 0.4, 0.14, c1=UK.SUN, c2=UK.NAVY, step=0.14)
        for k in range(3): UK.d_star(cv, W * 0.62 + k * 0.17, H * 0.68, 0.06, col=(UK.CREAM, UK.SUN, UK.CREAM)[k])
        UK.d_chevrons(cv, W * 0.88 - 0.06, H * 0.4, 0.12, 0.2, 2, col=UK.CREAM)
    def front2(cv):
        W, H = cv.wm, cv.H / cv.ppm
        UK.d_star(cv, W * 0.25, H * 0.5, 0.12, col=UK.SUN)
        cv.rect(W * 0.45, H * 0.35, W * 0.9, H * 0.65, carve=False, col=EK.C(UK.CREAM))
        for k in range(4): cv.rect(W * 0.48 + k * 0.08, H * 0.4, W * 0.48 + k * 0.08 + 0.05, H * 0.6, carve=True, col=EK.C(UK.NAVY), val=80)
    d1 = decal('cr1front', 1.5, 0.6, front1, seed=1); d2 = decal('cr2front', 0.95, 0.38, front2, seed=2)
    hi = []
    p1 = crate('crate1', (1.9, 1.2, 0.86), (0, 0, 0), UK.MINT, dec=d1, seed=10)
    front_dec(p1[0], -0.75, -0.6, 0.13, 1.5, 0.6); hi += p1
    p2 = crate('crate2', (1.22, 0.92, 0.55), (-0.18, 0.06, 0.86), UK.CORAL, rot=6, dec=d2, seed=20)
    bpy.context.view_layer.update()
    front_dec(p2[0], -0.18 - 0.475, -0.6, 0.94, 0.95, 0.38); hi += p2
    # küçük kutu + çanak + lamba
    BX = UK.m_paint('smallbox', UK.SUN, chips=0.45, dust=0.3, seed=30); GM = UK.m_metal('dishm', UK.ALU, dust=0.3)
    hi.append(EK.rounded_box('sbox', (0.42, 0.36, 0.22), 0.025, 0.02, [BX], loc=(0.52, 0.18, 0.86 + 0.11), rot=(0, 0, -8), chips=0.005, seed=31))
    for k in range(4):
        hi.append(UK.rivet((0.52 - 0.15 + k * 0.1, 0.18 - 0.185, 0.86 + 0.18), (0, -1, 0), 0.008))
    mast = cyl('mast', (0.52, 0.18, 1.08 + 0.12), 0.022, 0.24, GM, verts=10, bevel=0.0); hi.append(mast)
    dish = EK.lathe_grid('dish', [(0.0, 0.0), (0.06, 0.004), (0.12, 0.018), (0.17, 0.042), (0.19, 0.06), (0.175, 0.062), (0.12, 0.03), (0.06, 0.014), (0.0, 0.01)][::-1][::-1],
                         24, [UK.m_paint('dishp', UK.CREAM, chips=0.3, dust=0.2, seed=32)], uv=False)
    dish.rotation_euler = (math.radians(-55), 0, math.radians(-20)); dish.location = (0.52, 0.18, 1.33); hi.append(dish)
    hi.append(cyl('feed', (0.52, 0.12, 1.4), 0.012, 0.16, GM, rot=(-55, 0, -20), verts=8, bevel=0.0))
    hi.append(blob('feedtip', (0.52 - 0.02, 0.06, 1.46), (0.025, 0.025, 0.025), UK.m_glow('feedglow', UK.CYAN), seg=12))
    lp = UK.lamp('beacon', (-0.45, -0.12, 1.41), 0.07, UK.CORAL, cage=True, base_h=0.05)
    hi += lp
    hi.append(UK.cable('bcable', [(-0.4, -0.06, 1.41), (-0.1, 0.1, 1.42), (0.3, 0.2, 1.08)], 0.012, UK.m_rubber('bcab', UK.NAVY), res=3))
    for k in range(4):
        a = k / 4 * TAU + 0.3
        hi.append(UK.bolt((-0.45 + math.cos(a) * 0.075, -0.12 + math.sin(a) * 0.075, 1.415), (0, 0, 1), 0.008))
    kit.to_mesh_all()
    decim = [(r'^crate[12]$', 60), (r'_rib$', 12), (r'_corner$', 12), (r'_latch$', 12), (r'_handle$', 40), (r'^sbox$', 30),
             (r'^dish$', 120), (r'^(mast|feed)$', 30), (r'^feedtip$', 20), (r'^beacon_bulb$', 60), (r'^beacon_base$', 30), (r'^beacon_cage$', 40), (r'^bcable$', 40)]
    weights = [(r'^crate[12]$', 1.2), (r'^beacon_', 1.4), (r'^dish', 1.2), (r'_corner$', 0.6)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2500, ao_dist=0.3, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_low

def build_low():
    PIPE = UK.m_paint('pipep', UK.CREAM, chips=0.25, dust=0.2, grime=0.4, seed=1.0, scale=3.0)
    STRIPE = UK.m_paint('pipes', UK.CORAL, chips=0.25, dust=0.2, grime=0.4, seed=2.0, scale=3.0)
    FL = UK.m_metal('flange', UK.STEEL, dust=0.3); GN = UK.m_metal('pfoot', UK.GUN, dust=0.3)
    GL = UK.m_glow('pglow', UK.CYAN, hot=0.6); WH = UK.m_paint('wheel', UK.SUN, chips=0.4, dust=0.2, seed=3.0)
    R0, ZC, X1 = 0.2, 0.32, 3.1
    hi = []
    # düz boru: 0,3 m'lik mercan/krem bantlar (ayrı parçalar: renk sınırı keskin)
    n = int(round(2 * X1 / 0.3))
    for k in range(n):
        x0 = -X1 + k * 2 * X1 / n; x1 = x0 + 2 * X1 / n
        c = cyl('pipe', ((x0 + x1) / 2, 0, ZC), R0, x1 - x0, STRIPE if k % 2 == 0 else PIPE, rot=(0, 90, 0), verts=14, bevel=0.0)
        hi.append(c)
    # uçlarda dirsek: aşağı kıvrılıp flanşlı tabana iner
    for sx in (-1, 1):
        rr = 0.3
        pts = []
        for k in range(9):
            a = k / 8 * math.pi / 2
            pts.append((sx * (X1 + rr * math.sin(a)), 0.0, ZC - rr * (1 - math.cos(a))))
        pts.append((sx * (X1 + rr), 0.0, 0.05))
        hi.append(tube('elbow', pts, [R0] * len(pts), STRIPE, res=6))
        hi.append(cyl('basefl', (sx * (X1 + rr), 0, 0.03), 0.26, 0.06, FL, verts=24, bevel=0.01))
        for k in range(8):
            a = k / 8 * TAU; hi.append(UK.bolt((sx * (X1 + rr) + math.cos(a) * 0.21, math.sin(a) * 0.21, 0.06), (0, 0, 1), 0.016))
        hi.append(cyl('flange', (sx * (X1 + rr), 0, 0.16), R0 + 0.03, 0.05, FL, verts=24, bevel=0.008))
    # flanşlar + ışık halkası (1,1 m'de bir), ayaklar
    for fx in (-2.2, -1.1, 0.0, 1.1, 2.2):
        hi.append(cyl('flange', (fx, 0, ZC), R0 + 0.035, 0.07, FL, rot=(0, 90, 0), verts=28, bevel=0.01))
        hi.append(cyl('glowring', (fx, 0, ZC), R0 + 0.038, 0.018, GL, rot=(0, 90, 0), verts=28, bevel=0.0))
        for k in range(8):
            a = k / 8 * TAU + 0.2
            for s in (-1, 1): hi.append(UK.bolt((fx + s * 0.037, math.cos(a) * (R0 + 0.022), ZC + math.sin(a) * (R0 + 0.022)), (s, 0, 0), 0.011))
    for fx in (-1.65, 1.65, -2.75, 2.75, -0.55, 0.55):
        hi.append(EK.rounded_box('foot', (0.12, 0.62, 0.05), 0.015, 0.02, [GN], loc=(fx, 0.05, 0.025), seed=int(fx * 10)))
        hi.append(EK.rounded_box('saddle', (0.1, 0.06, ZC - 0.05), 0.012, 0.02, [GN], loc=(fx, 0, (ZC - 0.05) / 2 + 0.03), seed=int(fx * 10) + 1))
        bpy.ops.mesh.primitive_torus_add(major_radius=R0 + 0.012, minor_radius=0.014, major_segments=24, minor_segments=6, location=(fx, 0, ZC), rotation=(0, math.radians(90), 0))
        t = bpy.context.object; t.name = 'clamp'; t.data.materials.append(GN); hi.append(t)
        for s in (-1, 1): hi.append(UK.bolt((fx, 0.05 + s * 0.24, 0.05), (0, 0, 1), 0.012))
    # ikinci ince boru (arkada) + vana çarkı + gösterge (önde)
    hi.append(cyl('pipe2', (0, 0.27, 0.11), 0.055, 2 * X1 + 0.5, UK.m_paint('pipe2p', UK.TEAL, chips=0.4, dust=0.3, seed=4.0), rot=(0, 90, 0), verts=16, bevel=0.0))
    vx = 1.35; vy = -R0 - 0.075                                   # vana çarkı önde (−Y), dik
    hi.append(cyl('vstem', (vx, -R0 - 0.035, ZC), 0.024, 0.08, FL, rot=(90, 0, 0), verts=10, bevel=0.0))
    hi.append(cyl('vbody', (vx, -R0 + 0.01, ZC), 0.06, 0.06, FL, rot=(90, 0, 0), verts=14, bevel=0.006))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.11, minor_radius=0.017, major_segments=24, minor_segments=6, location=(vx, vy, ZC), rotation=(math.radians(90), 0, 0))
    t = bpy.context.object; t.name = 'vwheel'; t.data.materials.append(WH); hi.append(t)
    for k in range(4):
        a = k / 4 * TAU + 0.4
        hi.append(tube('vspoke', [(vx, vy, ZC), (vx + math.cos(a) * 0.11, vy, ZC + math.sin(a) * 0.11)], [0.013, 0.013], WH, res=2))
    hi.append(cyl('vhub', (vx, vy, ZC), 0.032, 0.035, WH, rot=(90, 0, 0), verts=12, bevel=0.005))
    gx = -1.1 + 0.3
    hi.append(cyl('gauge', (gx, -R0 - 0.03, ZC + 0.04), 0.075, 0.05, FL, rot=(90, 0, 0), verts=20, bevel=0.008))
    hi.append(cyl('gface', (gx, -R0 - 0.056, ZC + 0.04), 0.06, 0.004, UK.m_flatc('gface', UK.CREAM, 0.02, 0.1) if hasattr(UK, 'm_flatc') else EK.m_flatc('gface', UK.CREAM, 0.02, 0.1), rot=(90, 0, 0), verts=20, bevel=0.0))
    hi.append(EK.rounded_box('gneedle', (0.008, 0.004, 0.05), 0.002, 0.005, [EK.m_flatc('gneedle', UK.CORAL, 0.0, 0.0)], loc=(gx + 0.012, -R0 - 0.06, ZC + 0.055), rot=(0, 35, 0)))
    kit.to_mesh_all()
    decim = [(r'^pipe$', 1.0), (r'^elbow$', 120), (r'^(basefl|flange)$', 48), (r'^glowring$', 32), (r'^(foot|saddle)$', 12), (r'^clamp$', 32),
             (r'^pipe2$', 1.0), (r'^(vstem|vhub|vbody)$', 24), (r'^vspoke$', 10), (r'^vwheel$', 72), (r'^(gauge|gface)$', 40), (r'^gneedle$', 12)]
    weights = [(r'^(pipe|elbow)$', 1.0), (r'^(vwheel|vhub|vspoke|gauge|gface|gneedle)$', 1.6), (r'^(flange|glowring)$', 1.2)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2500, ao_dist=0.25, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_high

def build_high():
    def beamfront(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cv.rect(0.0, 0.0, W, H, carve=False, col=EK.C(UK.NAVY))
        for s in (0, 1):
            x0 = 0.04 if s == 0 else W - 0.84
            UK.d_hazard(cv, x0, 0.09, 0.8, H - 0.18, c1=UK.SUN, c2='#2a2f5c', step=0.2)
        cv.rect(0.9, H * 0.42, W - 0.9, H * 0.58, carve=False, col=EK.C(UK.MINT))
        cv.ell(W / 2, H / 2, 0.36, 0.36, col=EK.C('#24295a'), carve=False)
        UK.d_planet(cv, W / 2, H / 2, 0.16, body=UK.CORAL, ring=UK.SUN)
        for k in range(3):
            for s in (-1, 1): UK.d_star(cv, W / 2 + s * (0.55 + k * 0.32), H / 2 + (0.06 if k % 2 else -0.06), 0.055 - k * 0.008, col=(UK.SUN, UK.CREAM, UK.CYAN)[k])
        for k in range(int(W / 0.1)):
            for v in (0.035, H - 0.035): UK.d_bolt(cv, 0.05 + k * 0.1, v, 0.009)
    d = decal('hbeam', 7.6, 0.46, beamfront, ppm=200, seed=5)
    BEAM = UK.m_paint('beamp', UK.NAVY, chips=0.3, dust=0.25, grime=0.45, dec=d, seed=1.0)
    PIL = UK.m_paint('pillarp', UK.NAVY, chips=0.4, dust=0.3, grime=0.45, seed=2.0)
    BAND = UK.m_paint('bandp', UK.CORAL, chips=0.4, dust=0.25, seed=3.0); TRIMP = UK.m_paint('trimp', UK.CREAM, chips=0.35, dust=0.3, seed=4.0)
    GM = UK.m_metal('hmetal', UK.GUN, dust=0.3); BOX = UK.m_paint('hbox', UK.SUN, chips=0.4, dust=0.2, seed=5.0)
    hi = []
    for sx in (-1, 1):
        x = sx * 3.5
        hi.append(EK.rounded_box('pillar', (0.42, 0.5, 1.16), 0.035, 0.03, [PIL], loc=(x, 0, 0.58), chips=0.01, seed=10 + sx))
        for zb in (0.12, 1.02):
            hi.append(EK.rounded_box('pband', (0.45, 0.53, 0.07), 0.015, 0.02, [BAND], loc=(x, 0, zb), seed=12 + sx))
        hi.append(EK.rounded_box('pfoot', (0.62, 0.7, 0.06), 0.02, 0.03, [GM], loc=(x, 0, 0.03), seed=14 + sx))
        for (dx, dy) in ((-0.25, -0.29), (0.25, -0.29), (-0.25, 0.29), (0.25, 0.29)): hi.append(UK.bolt((x + dx, dy, 0.06), (0, 0, 1), 0.016))
        # iç yüzde düğmeli küçük kutu
        bx = x - sx * 0.23
        hi.append(EK.rounded_box('ctrl', (0.06, 0.24, 0.3), 0.015, 0.015, [BOX], loc=(bx, -0.05, 0.62), seed=16 + sx))
        for k, c in enumerate((UK.CYAN, UK.CORAL, UK.MINT)):
            hi.append(blob('btn', (bx - sx * 0.035, -0.12 + k * 0.07, 0.68), (0.018, 0.018, 0.018), UK.m_glow('btn' + c, c, hot=0.5), seg=12, sub=1))
        for k in range(6):
            for dy in (-0.255,):
                hi.append(UK.rivet((x + (-0.15 + k * 0.06), dy, 0.5), (0, -1, 0), 0.009))
    beam = EK.rounded_box('beam', (7.8, 0.55, 0.5), 0.04, 0.03, [BEAM], loc=(0, 0, 1.16 + 0.25), chips=0.008, lump=0.0, seed=20)
    front_dec(beam, -3.8, -0.275, 1.18, 7.6, 0.46); hi.append(beam)
    hi.append(EK.rounded_box('btrim', (7.86, 0.6, 0.06), 0.02, 0.03, [TRIMP], loc=(0, 0, 1.66 + 0.03), chips=0.006, seed=21))
    # önde büyük yuvarlak amblem levhası (alt kenarı 1,19: kayma boşluğu korunur)
    def emb(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cv.ell(W / 2, H / 2, W / 2 - 0.02, H / 2 - 0.02, col=EK.C('#262c5e'), carve=False)
        cv.line(EK.arcpts(W / 2, H / 2, W / 2 - 0.05, H / 2 - 0.05, 0, 360, 48), 0.02, col=EK.C(UK.SUN))
        UK.d_planet(cv, W / 2, H / 2, W * 0.19, body=UK.CORAL, ring=UK.SUN)
        for k in range(6):
            a = math.radians(30 + k * 60); UK.d_star(cv, W / 2 + math.cos(a) * W * 0.36, H / 2 + math.sin(a) * H * 0.36, 0.03, col=(UK.CREAM, UK.CYAN)[k % 2])
    de = decal('hemblem', 0.72, 0.72, emb, ppm=400, seed=9)
    EMB = UK.m_paint('hembp', UK.CREAM, chips=0.2, dust=0.1, dec=de, seed=6.0)
    em = cyl('hemblem', (0, -0.275 - 0.035, 1.55), 0.36, 0.06, EMB, rot=(90, 0, 0), verts=32, bevel=0.015)
    bpy.context.view_layer.update()
    EK.planar_dec_uv(em, (-0.36, -0.4, 1.55 - 0.36), (1, 0, 0), (0, 0, 1), 0.72, 0.72, face_dir=(0, -1, 0)); hi.append(em)
    for k in range(8):
        a = k / 8 * TAU + 0.2; hi.append(UK.bolt((math.cos(a) * 0.32, -0.345, 1.55 + math.sin(a) * 0.32), (0, -1, 0), 0.012))
    # tepe: iki işaret lambası (ayakların üstünde) + anten
    for sx, c in ((-1, UK.CORAL), (1, UK.SUN)):
        hi += UK.lamp('hbeacon', (sx * 3.5, 0, 1.72), 0.1, c, cage=True, base_h=0.06)
    hi.append(cyl('antmast', (2.6, 0.1, 1.72 + 0.25), 0.015, 0.5, GM, verts=8, bevel=0.0))
    hi.append(blob('anttip', (2.6, 0.1, 2.23), (0.035, 0.035, 0.035), UK.m_glow('anttip', UK.CYAN), seg=12))
    hi.append(EK.rounded_box('antbase', (0.12, 0.12, 0.05), 0.01, 0.015, [GM], loc=(2.6, 0.1, 1.745), seed=22))
    kit.to_mesh_all()
    decim = [(r'^pillar$', 48), (r'^pband$', 24), (r'^pfoot$', 12), (r'^ctrl$', 24), (r'^btn$', 20), (r'^beam$', 90), (r'^btrim$', 30),
             (r'^hbeacon_bulb$', 60), (r'^hbeacon_base$', 30), (r'^hbeacon_cage$', 40), (r'^(antmast)$', 1.0), (r'^anttip$', 24), (r'^antbase$', 12),
             (r'^hemblem$', 80)]
    weights = [(r'^beam$', 1.3), (r'^hemblem$', 2.4), (r'^hbeacon', 1.3), (r'^(ctrl|btn)$', 1.3), (r'^pillar$', 1.0)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=3000, ao_dist=0.3, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_crystal

def build_crystal():
    """Uzun sekizgen çift piramit mücevher (altta uç z = 0, kuşak 0,19, tepe 0,52) + kuşak bandı; düz gölgeli, pahlı."""
    M = UK.m_crystal('gem', '#5a2bb8', '#56bfe6', 0.02, 0.8, local=True)
    n = 8; rg = 0.16; zg = 0.19; hb = 0.035
    verts = [(0, 0, 0.0)]
    for z in (zg, zg + hb):
        for k in range(n):
            a = k / n * TAU + math.pi / n; verts.append((math.cos(a) * rg, math.sin(a) * rg, z))
    for k in range(n):        # taç: üstte küçük düz masa
        a = k / n * TAU + math.pi / n; verts.append((math.cos(a) * rg * 0.42, math.sin(a) * rg * 0.42, 0.5))
    faces = []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((0, 1 + k2, 1 + k)); faces.append((1 + k, 1 + k2, 1 + n + k2, 1 + n + k)); faces.append((1 + n + k, 1 + n + k2, 1 + 2 * n + k2, 1 + 2 * n + k))
    faces.append(tuple(1 + 2 * n + k for k in range(n)))
    o = EK.mesh_obj('gem', verts, faces, [M], smooth=False)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.006; bv.segments = 2; bv.limit_method = 'ANGLE'
    return [o], None, dict(decim=[(r'.', 1.0)], weights=[], tex=256, budget=800, ao_dist=0.05, cage=0.008, ray=0.03)


# ================================================================== rs_card

def build_card():
    def screen(cv):
        W, H = cv.wm, cv.H / cv.ppm
        # holo zemin: lacivertten mora dikey geçiş (şeritler), yıldızlar, halkalı gezegen
        for k in range(24):
            t = k / 23; c = tuple(int((a * (1 - t) + b * t)) for a, b in zip((0x2c, 0x32, 0x63), (0x5b, 0x4c, 0xa0)))
            cv.rect(0, H * k / 24, W, H * (k + 1) / 24 + 0.001, carve=False, col=tuple(x / 255 for x in c))
        R = random.Random(4)
        for k in range(14):
            UK.d_star(cv, R.uniform(0.03, W - 0.03), R.uniform(0.03, H - 0.03), R.uniform(0.008, 0.018), col=R.choice((UK.CREAM, UK.SUN, UK.CYAN)))
        UK.d_planet(cv, W / 2, H * 0.52, W * 0.2, body='#9a7fe0', ring=UK.CYAN, col_ring2=UK.CREAM)
        cv.ell(W * 0.78, H * 0.82, W * 0.06, W * 0.06, col=EK.C(UK.MINT))
        cv.rect(W * 0.18, H * 0.1, W * 0.82, H * 0.14, carve=True, col=EK.C(UK.CYAN), val=80)
    def back(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cv.rect(0, 0, W, H, carve=False, col=EK.C('#3a3f78'))
        for i in range(4):
            for j in range(6): UK.d_star(cv, W * (i + 0.5) / 4, H * (j + 0.5) / 6, 0.022, col=(UK.SUN if (i + j) % 2 else UK.CYAN))
    W, H, T = 0.4, 0.58, 0.05
    ds = decal('cardscr', W - 0.06, H - 0.06, screen, ppm=900, depth=0.002, groove=0.001, chips=0.0, fade=0.05, seed=6)
    db = decal('cardback', W - 0.06, H - 0.06, back, ppm=600, depth=0.002, groove=0.001, chips=0.0, fade=0.05, seed=7)
    FR = UK.m_paint('cardframe', UK.CORAL, chips=0.25, dust=0.0, grime=0.35, scale=3.0, seed=1.0)
    SC = UK.m_paint('cardscreen', '#3a3f78', chips=0.0, scratch=0.0, dust=0.0, grime=0.2, dec=ds, seed=2.0)
    BK_ = UK.m_paint('cardback', '#3a3f78', chips=0.0, scratch=0.0, dust=0.0, grime=0.2, dec=db, seed=3.0)
    GD = EK.m_gold('cardgold')
    hi = []
    frame = EK.rounded_box('frame', (W, T, H), 0.04, 0.008, [FR], loc=(0, 0, H / 2), seed=1)
    hi.append(frame)
    scr = EK.rounded_box('screen', (W - 0.06, 0.006, H - 0.06), 0.002, 0.006, [SC], loc=(0, -T / 2 - 0.0, H / 2), seed=2)
    front_dec(scr, -(W - 0.06) / 2, -T / 2 - 0.003, 0.03, W - 0.06, H - 0.06); hi.append(scr)
    bck = EK.rounded_box('back', (W - 0.06, 0.006, H - 0.06), 0.002, 0.006, [BK_], loc=(0, T / 2, H / 2), seed=3)
    front_dec(bck, -(W - 0.06) / 2, T / 2 + 0.003, 0.03, W - 0.06, H - 0.06, face=(0, 1, 0)); hi.append(bck)
    for (x, z) in ((-W / 2 + 0.035, 0.035), (W / 2 - 0.035, 0.035), (-W / 2 + 0.035, H - 0.035), (W / 2 - 0.035, H - 0.035)):
        for sy in (-1, 1): hi.append(blob('stud', (x, sy * (T / 2 + 0.002), z), (0.014, 0.008, 0.014), GD, seg=12, sub=1))
    hi.append(blob('topnub', (0, 0, H + 0.012), (0.04, 0.02, 0.02), GD, seg=16, sub=1))
    decim = [(r'^frame$', 70), (r'^(screen|back)$', 12), (r'^stud$', 16), (r'^topnub$', 30)]
    weights = [(r'^(screen|back)$', 2.0), (r'^frame$', 0.8)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=800, ao_dist=0.03, cage=0.004, ray=0.015)


# ================================================================== rs_comet (orijin baş merkezi)

def m_tail(name):
    """Kuyruk ışık boyası: başta sıcak sarı → mercan → pembe → uçta lavanta (dünya y'sine göre), yukarı-dışa bakan yüzde açık çekirdek."""
    def b(nt, bsdf):
        G = EK.EG(nt); x, y, z = G.sep(G.pos()); nx, ny, nz = G.sep(G.nrm())
        t = G.rng(y, -0.15, -1.55)
        r = EK.ramp(nt, [(0.0, '#ffd257'), (0.35, '#ffa45c'), (0.68, '#f283a6'), (1.0, '#b08cec')]); G.l.new(t, r.inputs['Fac'])
        f = G.math('ADD', G.math('MULTIPLY', nz, 0.6), G.math('MULTIPLY', G.math('ABSOLUTE', nx), -0.3))
        col = G.mix(G.rng(f, 0.0, 0.9, 0, 0.55), r.outputs[0], '#fff6e0')
        col = G.mix(G.rng(f, -0.4, -0.9, 0, 0.25), col, '#c7609a')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def build_comet():
    HEAD = UK.m_glow('comethead', '#ffd257', core='#fffaf0', hot=0.95)
    TL = m_tail('cometail')
    EYE = EK.m_flatc('ceye', '#3a2440', 0.0, 0.0); WH = EK.m_flatc('cshine', '#ffffff', 0.0, 0.0); BL = EK.m_flatc('cblush', '#ff8a7a', 0.05, 0.0)
    hi = [blob('head', (0, 0, 0), (0.35, 0.35, 0.34), HEAD, seg=32)]
    # ana kuyruk: başın arkasından −Y'ye kıvrılarak incelen alev (tombul, yumuşak)
    pts = [(0.0, -0.05, 0.0), (0.03, -0.45, 0.06), (-0.04, -0.85, 0.15), (0.04, -1.18, 0.25), (0.0, -1.42, 0.34)]
    hi.append(tube('tail', pts, [0.33, 0.3, 0.24, 0.16, 0.09], TL, res=16))
    hi.append(blob('tailtip', (0.0, -1.44, 0.35), (0.09, 0.1, 0.09), TL, seg=16))
    # yan alev dilimleri: kuyruğa kaynaşan, geriye uzanan yumuşak loblar (tombul, uçları yuvarlak)
    for (c, r, rot) in (((0.22, -0.6, 0.14), (0.15, 0.34, 0.14), (12, 0, -22)), ((-0.21, -0.72, 0.1), (0.14, 0.32, 0.13), (10, 0, 24)),
                        ((0.04, -0.62, -0.17), (0.15, 0.3, 0.12), (-14, 0, 6)), ((0.08, -0.95, 0.33), (0.11, 0.26, 0.1), (28, 0, -10)),
                        ((-0.14, -1.08, 0.12), (0.09, 0.22, 0.09), (16, 0, 18))):
        hi.append(blob('lick', c, r, TL, rot=rot, seg=20))
    for sx in (-1, 1):
        hi.append(blob('ceye', (sx * 0.12, 0.315, 0.06), (0.045, 0.02, 0.06), EYE, rot=(0, 0, -sx * 12), seg=16, sub=1))
        hi.append(blob('cshine', (sx * 0.11, 0.33, 0.085), (0.015, 0.006, 0.018), WH, seg=8, sub=0))
        hi.append(blob('cblush', (sx * 0.2, 0.285, -0.04), (0.05, 0.012, 0.03), BL, rot=(0, 0, -sx * 30), seg=12, sub=1))
    hi.append(tube('csmile', [(-0.07, 0.335, -0.06), (0.0, 0.345, -0.1), (0.07, 0.335, -0.06)], [0.012, 0.014, 0.012], EYE, res=3))
    ST = UK.m_glow('cstar', '#fff1b0', core='#ffffff', hot=0.6)
    for (c, r, rot) in (((0.48, -0.65, 0.42), 0.065, 20), ((-0.5, -1.0, 0.0), 0.055, -15), ((0.3, -1.5, 0.55), 0.045, 40), ((-0.25, -1.45, 0.5), 0.035, 10)):
        pts_ = []
        for i in range(10):
            a = math.radians(90 + i * 36); rr = r if i % 2 == 0 else r * 0.45; pts_.append((math.cos(a) * rr, math.sin(a) * rr))
        verts = [(x, -0.012, z) for (x, z) in pts_] + [(x, 0.012, z) for (x, z) in pts_] + [(0, -0.02, 0), (0, 0.02, 0)]
        faces = []
        for i in range(10):
            i2 = (i + 1) % 10; faces.append((20, i2, i)); faces.append((21, 10 + i, 10 + i2)); faces.append((i, i2, 10 + i2, 10 + i))
        o = EK.mesh_obj('cstar', verts, faces, [ST], smooth=False)
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
        o.location = c; o.rotation_euler = (math.radians(10), math.radians(rot), math.radians(25)); hi.append(o)
    kit.to_mesh_all()
    decim = [(r'^head$', 300), (r'^tail$', 300), (r'^tailtip$', 40), (r'^lick$', 90), (r'^(ceye|cblush)$', 30), (r'^cshine$', 12), (r'^csmile$', 40), (r'^cstar$', 1.0)]
    weights = [(r'^(head|ceye|cshine|cblush|csmile)$', 1.6), (r'^tail$', 1.2)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=1500, ao_dist=0.12)


# ================================================================== rs_gate

def build_gate():
    C_, RI, RO, DEP = 2.5, 4.3, 5.0, 1.0           # merkez z, iç/dış yarıçap, derinlik (y)
    NSEG = 16
    COR = UK.m_paint('gcoral', UK.CORAL, chips=0.2, dust=0.0, grime=0.45, seed=1.0, scale=1.6)
    TEA = UK.m_paint('gteal', UK.TEAL, chips=0.2, dust=0.0, grime=0.45, seed=2.0, scale=1.6)
    CRM = UK.m_paint('gcream', UK.CREAM, chips=0.15, dust=0.0, grime=0.4, seed=3.0, scale=1.6)
    NAV = UK.m_paint('gnavy', UK.NAVY, chips=0.15, dust=0.0, grime=0.45, seed=4.0, scale=1.6)
    GM = UK.m_metal('gmetal', UK.GUN, dust=0.0); ST = UK.m_metal('gsteel', UK.STEEL, dust=0.0)
    hi = []
    def ring_seg(name, a0, a1, r0, r1, y0, y1, mat, n=8):
        """Halka dilimi: dört yüzlü (iç, dış, ön, arka) kapalı dilim; köşeler hafif pahlı."""
        th = np.linspace(a0, a1, n + 1)
        loop = [(r0 + 0.02, y0), (r0, y0 + 0.02), (r0, y1 - 0.02), (r0 + 0.02, y1), (r1 - 0.02, y1), (r1, y1 - 0.02), (r1, y0 + 0.02), (r1 - 0.02, y0)]
        P = np.zeros((len(loop) + 1, n + 1, 3))
        for i, (r, y) in enumerate(loop + [loop[0]]):
            P[i, :, 0] = r * np.cos(th); P[i, :, 1] = y; P[i, :, 2] = C_ + r * np.sin(th)
        o = EK.grid_obj(name, P, None, [mat]); EK.weld(o)
        bm = bmesh.new(); bm.from_mesh(o.data)
        for (a, ) in ((a0,), (a1,)):
            ring = sorted([v for v in bm.verts if abs(math.atan2(v.co.z - C_, v.co.x) - (a if a <= math.pi else a - TAU)) < 1e-4],
                          key=lambda v: (math.hypot(v.co.x, v.co.z - C_), v.co.y))
            if len(ring) >= 3:
                cen = sum((v.co for v in ring), V((0, 0, 0))) / len(ring)
                ring = sorted(ring, key=lambda v: math.atan2(v.co.y - cen.y, math.hypot(v.co.x, v.co.z - C_) - math.hypot(cen.x, cen.z - C_)))
                try: bm.faces.new(ring)
                except ValueError: pass
        bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
        return o
    for k in range(NSEG):
        a0 = k / NSEG * TAU; a1 = (k + 1) / NSEG * TAU
        gap = 0.012
        hi.append(ring_seg('ring', a0 + gap, a1 - gap, RI, RO, -DEP / 2, DEP / 2, COR if k % 2 == 0 else TEA, n=6))
    # ön ve arkada krem kenar şeritleri, iç kenarda koyu iç bant
    for (y0, y1) in ((-DEP / 2 - 0.04, -DEP / 2 + 0.02), (DEP / 2 - 0.02, DEP / 2 + 0.04)):
        for (r0, r1) in ((RO - 0.12, RO + 0.03), (RI - 0.03, RI + 0.1)):
            hi.append(ring_seg('trim', 0.0, TAU, r0, r1, y0, y1, CRM, n=96))
    hi.append(ring_seg('inband', 0.0, TAU, RI - 0.05, RI + 0.005, -0.32, 0.32, NAV, n=96))
    # iç kenarda yuvarlak ışıklar (24), dilim eklerinde cıvatalar
    for k in range(24):
        a = (k + 0.5) / 24 * TAU
        p = V((math.cos(a) * (RI - 0.05), 0.0, C_ + math.sin(a) * (RI - 0.05)))
        n = V((-math.cos(a), 0, -math.sin(a)))
        for (yy, c) in (((-0.2 if k % 2 else 0.2), (UK.CYAN if k % 2 else UK.SUN)),):
            base = cyl('glamp_base', (0, 0, 0), 0.07, 0.03, GM, verts=14, bevel=0.005)
            bulb = blob('glamp_bulb', (0, 0, 0.025), (0.05, 0.05, 0.035), UK._cached('glow' + c, lambda c=c: UK.m_glow('glow' + c, c)), seg=14, sub=1)
            for o in (base, bulb):
                q = n.to_track_quat('Z', 'Y'); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
                o.location = p + V((0, yy, 0)) + (q @ V(o.location))
                hi.append(o)
    for k in range(NSEG):
        a = k / NSEG * TAU
        for rr in (RI + 0.15, RO - 0.17):
            for sy in (-1, 1):
                hi.append(UK.bolt((math.cos(a) * rr, sy * (DEP / 2 + 0.002), C_ + math.sin(a) * rr), (0, sy, 0), 0.02))
    # tepe: amblem levhası (önde), işaret lambası, iki anten; yanlarda küçük itici nozullar
    def emblem(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cv.ell(W / 2, H / 2, W / 2 - 0.02, H / 2 - 0.02, col=EK.C(UK.NAVY), carve=False)
        UK.d_planet(cv, W / 2, H / 2, W * 0.2, body=UK.SUN, ring=UK.CORAL)
        for k in range(5):
            a = math.radians(90 + k * 72); UK.d_star(cv, W / 2 + math.cos(a) * W * 0.4, H / 2 + math.sin(a) * H * 0.4, 0.05, col=UK.CREAM)
    de = decal('gemblem', 2.0, 2.0, emblem, ppm=200, seed=8)
    EM = UK.m_paint('gemb', UK.CREAM, chips=0.3, dust=0.0, dec=de, seed=5.0)
    em = cyl('emblem', (0, -DEP / 2 - 0.08, C_ + RO - 0.35), 1.0, 0.12, EM, rot=(90, 0, 0), verts=40, bevel=0.03)
    bpy.context.view_layer.update()
    EK.planar_dec_uv(em, (-1.0, -DEP / 2 - 0.2, C_ + RO - 0.35 - 1.0), (1, 0, 0), (0, 0, 1), 2.0, 2.0, face_dir=(0, -1, 0))
    for k in range(12):
        a = k / 12 * TAU; hi.append(UK.bolt((math.cos(a) * 0.9, -DEP / 2 - 0.145, C_ + RO - 0.35 + math.sin(a) * 0.9), (0, -1, 0), 0.025))
    hi.append(em)
    hi += UK.lamp('gbeacon', (0, 0.2, C_ + RO), 0.2, UK.CORAL, cage=True, base_h=0.1)
    for sx in (-1, 1):
        a = math.radians(90 + sx * 28); bx, bz = math.cos(a) * RO, C_ + math.sin(a) * RO
        hi.append(cyl('gant', (bx, 0.2, bz + 0.45), 0.025, 0.9, ST, rot=(0, -sx * 28, 0), verts=8, bevel=0.0))
        hi.append(blob('ganttip', (bx - sx * 0.21, 0.2, bz + 0.88), (0.06, 0.06, 0.06), UK.m_glow('ganttip', UK.MINT), seg=12))
        for a_deg in (200, 340) if sx > 0 else ():
            pass
    for a_deg in (200, 340):
        a = math.radians(a_deg); px, pz = math.cos(a) * (RO + 0.12), C_ + math.sin(a) * (RO + 0.12)
        nz = EK.lathe_grid('gthr', [(0.0, -0.05), (0.12, -0.04), (0.16, 0.12), (0.13, 0.14), (0.09, 0.03), (0.0, 0.03)], 16, [GM], uv=False)
        nz.rotation_mode = 'QUATERNION'; nz.rotation_quaternion = V((math.cos(a), 0, math.sin(a))).to_track_quat('Z', 'Y'); nz.location = (px, 0, pz)
        hi.append(nz)
    # güverte altına bağlantı kolları (x ±3,4 → halka), kelepçe levhaları
    for sx in (-1, 1):
        hi.append(EK.rounded_box('arm', (1.05, 0.5, 0.16), 0.03, 0.03, [NAV], loc=(sx * 3.88, 0, -0.4), chips=0.01, seed=40 + sx))
        hi.append(EK.rounded_box('clamp', (0.4, 0.62, 0.06), 0.015, 0.03, [GM], loc=(sx * 3.5, 0, -0.33), seed=42 + sx))
        for (dx, dy) in ((-0.13, -0.24), (0.13, -0.24), (-0.13, 0.24), (0.13, 0.24)): hi.append(UK.bolt((sx * 3.5 + dx, dy, -0.36), (0, 0, -1), 0.016))
        for dy in (-0.15, 0.15):
            hi.append(UK.cable('gcab', [(sx * 3.55, dy, -0.36), (sx * 3.9, dy * 1.2, -0.62), (sx * 4.3, dy, -0.42)], 0.025, UK.m_rubber('gcab', UK.CORAL if dy < 0 else UK.TEAL), res=4))
    kit.to_mesh_all()
    decim = [(r'^ring$', 1.0), (r'^trim$', 200), (r'^inband$', 200), (r'^glamp_base$', 16), (r'^glamp_bulb$', 20), (r'^emblem$', 64),
             (r'^gbeacon_bulb$', 60), (r'^gbeacon_base$', 30), (r'^gbeacon_cage$', 40), (r'^gant$', 1.0), (r'^ganttip$', 24), (r'^gthr$', 60),
             (r'^arm$', 24), (r'^clamp$', 12), (r'^gcab$', 40)]
    weights = [(r'^ring$', 1.0), (r'^emblem$', 2.2), (r'^gbeacon', 1.4), (r'^(trim|inband)$', 0.7), (r'^glamp', 0.8)]
    return hi, None, dict(decim=decim, weights=weights, tex=1024, budget=6000, ao_dist=0.6, exclude=[r'^(bolt|rivet)$'])


BUILD = {'rs_block': build_block, 'rs_block2': build_block2, 'rs_low': build_low, 'rs_high': build_high, 'rs_crystal': build_crystal,
         'rs_card': build_card, 'rs_comet': build_comet, 'rs_gate': build_gate}
