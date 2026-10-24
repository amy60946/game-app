# Ev Görevleri panosu — oyun modeli v2 (24 Ekim 2026; kullanıcı: "haritadaki bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli").
# Köy meydanındaki ilan panosu: ebeveynin gönderdiği ev görevleri burada asılı (oyunda "Ev Görevleri" bölgesi, MapWorld region_task_board).
# Eski yapıcı (assets_town.c_board) temel alındı, yerleşim ve dış ölçüler aynı (oyun EnvFootprint ile 5,5 m'ye ölçekler); eklenenler:
#   - üstte "ev + onay işareti" resimli başlık tahtası (yazısız, her yaşta okunur), öne eğik;
#   - notlar okunur: koyu satırlar, her notta bir simge (kalp, onay kutusu, yıldız, güneş, damla), kıvrılmış alt köşe, renkli raptiye;
#     köşede güneşte solmuş, yırtık eski bir not;
#   - eskitme: solmuş/lekeli kiremitler (biri sonradan konmuş tahta pul, biri kırık), çatı oyuklarında ve sırtta yosun öbekleri,
#     saçak altında tuz/su izi, çerçeve köşelerinde paslı demir köşebent + pas akıntısı, ayaklarda halat bağ, dipte toprak/yosun;
#   - ada hayatı: sağ saçakta yeni görev zili (pirinç, yeşil pas), rafta deniz kabuğu, ayakta deniz yıldızı, ayak diplerinde kum.
# Kullanım: python -I bld/b_task_board.py -- <çıktı> [b_task_board] [--draft <png>] [--stats]
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import koy_eskitme as KE
from koy_eskitme import AT, A, V, bpy, bmesh, rbox, blob, cyl, tube, m_flat, m_leaf

NAME = 'b_task_board'
CAP = 9000


def note_mesh(name, c, w, h, rot_y, m, curl=0.0, tear=False, seed=0):
    """Kâğıt not: ızgara düzlem (öne bakar, −Y), alt sağ köşe öne kıvrılır; tear → üst kenar yırtık."""
    R = random.Random(seed); NX, NZ = 6, 7; verts = []; faces = []; idx = {}
    for j in range(NZ + 1):
        for i in range(NX + 1):
            u, v = i / NX, j / NZ
            x = (u - 0.5) * w; z = (v - 0.5) * h
            if tear and j == NZ: z -= R.uniform(0.0, 0.035)
            y = 0.0
            k = max(0.0, (u - 0.55) / 0.45) * max(0.0, (0.45 - v) / 0.45)        # alt sağ köşe
            y -= curl * k ** 1.6
            z += curl * 0.35 * k ** 2
            idx[(i, j)] = len(verts); verts.append((x, y, z))
    for j in range(NZ):
        for i in range(NX):
            faces.append((idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    o = KE._mesh(name, verts, faces, m, smooth_on=True)
    o.location = c; o.rotation_euler = (0, math.radians(rot_y), 0)
    return o


def leg_center(sx, z):
    """AT.post ayağının z yüksekliğindeki ekseni (taban–orta–tepe noktalarından ikinci derece yaklaşık; orta nokta gürültüyle kayık)."""
    from mathutils import noise as mn
    seed = sx + 5
    b = V((sx * 0.62, 0, -0.05)); t = V((sx * 0.6, 0, 2.05))
    m = (b + t) / 2 + V((mn.noise(V((seed, 1, 2))) * 0.04, mn.noise(V((2, seed, 1))) * 0.04, 0))
    u = (z - b.z) / (t.z - b.z)
    p = b * (1 - u) * (1 - 2 * u) + m * 4 * u * (1 - u) + t * u * (2 * u - 1)
    return p.x, p.y


def build():
    W = KE.m_wood2('#87562f', 'boardw', salt=0.7, ground=0.45)
    FR = KE.m_wood2('#a8713f', 'boardfr', salt=0.8, ground=0.0)
    for sx in (-1, 1):
        AT.post('leg', (sx * 0.62, 0, -0.05), (sx * 0.6, 0, 2.05), 0.08, W, seed=sx + 5)
    # mantar pano + çerçeve
    def m_cork(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 3, 4), 0.3, 0.7), '#b8844f', '#d2a26c')
        col = G.mix(G.rng(G.vor(o, 90), 0.0, 0.25, 0.6, 0), col, '#8a5d34')
        col = G.mix(G.rng(G.noise(o, 1.4, 4), 0.55, 0.72, 0, 0.35), col, '#e2c79c')     # güneşte açılmış
        col = G.mix(G.rng(G.ao(0.1), 0.8, 0.4, 0, 0.5), col, '#5a3c22')
        nt.links.new(col, bsdf.inputs['Base Color'])
    CORK = KE.nodes_mat('cork2', m_cork)
    rbox('cork', (0, 0, 1.15), (1.1, 0.06, 0.8), CORK, bevel=0.02)
    for (x, z, sx, sz) in ((0, 0.73, 1.28, 0.08), (-0.6, 1.15, 0.08, 0.92), (0.6, 1.15, 0.08, 0.92), (0, 1.57, 1.28, 0.08)):
        AT.plank('frame', (x, -0.02, z), (sx, 0.09, sz), FR, seed=int(x * 10 + z * 10))
    # paslı köşebentler (çerçeve köşeleri, önden)
    for sx in (-1, 1):
        for zc in (0.73, 1.57):
            sz = 1 if zc > 1 else -1
            KE.iron_strap((sx * 0.56, -0.066, zc), (1, 0, 0), (0, -1, 0), 0.16, 0.045, nails=1)
            KE.iron_strap((sx * 0.6, -0.066, zc - sz * 0.07), (0, 0, 1), (0, -1, 0), 0.12, 0.045, nails=1)
    # başlık tahtası: ev + onay işareti (yazısız), öne eğik
    HB = KE.m_wood2('#a8713f', 'headw', paint='#f3e3bf', salt=0.6, ground=0.0, chips=1.2)
    tilt = -10
    AT.plank('header', (0, -0.1, 1.635), (1.06, 0.045, 0.19), HB, rot=(tilt, 0, 0), seed=21, amt=0.004)
    def onb(x, z, depth=0.0):   # başlık ön yüzünde nokta (üst kenar geriye yatık)
        return (x, -0.124 - depth + (z - 1.635) * math.sin(math.radians(-tilt)), z)
    CORAL = m_flat('#e0603f', 0.08, 8, 'icon_coral'); TEALI = m_flat('#2e9c98', 0.08, 8, 'icon_teal')
    GREEN = m_flat('#4caf3a', 0.08, 8, 'icon_green'); DARK = m_flat('#5a3a24', 0.08, 8, 'icon_dark')
    # ev: gövde + çatı üçgeni + kapı
    rbox('icon', onb(-0.25, 1.615), (0.13, 0.012, 0.09), TEALI, rot=(tilt, 0, 0), bevel=0.006)
    AT.prism('icon', [(-0.095, 0), (0.095, 0), (0, 0.075)], 0.012, CORAL, loc=onb(-0.25, 1.655), rot=(tilt, 0, 0), bevel=0.004)
    rbox('icon', onb(-0.25, 1.6, 0.004), (0.035, 0.008, 0.055), DARK, rot=(tilt, 0, 0), bevel=0.003)
    # onay işareti
    rbox('icon', onb(0.2, 1.615), (0.05, 0.014, 0.022), GREEN, rot=(tilt, 40, 0), bevel=0.008)
    rbox('icon', onb(0.27, 1.64), (0.13, 0.014, 0.022), GREEN, rot=(tilt, -52, 0), bevel=0.008)
    for x in (-0.48, 0.48):
        AT.nail((x, -0.13, 1.635), (0, -1, 0), streak=True)
    # notlar: koyu satırlar + simge + kıvrık köşe + raptiye
    PAP = ['#fff3d6', '#bfe0ff', '#ffd2e2', '#fff09a', '#cdeebb']
    R = random.Random(4)
    LN = m_flat('#6a5d52', 0.05, 6, 'lines2')
    PINC = ['#e8463c', '#2f8adf', '#f2b632', '#3fae5a', '#e8463c']
    spots = ((-0.33, 1.32), (0.05, 1.36), (0.36, 1.28), (-0.25, 0.95), (0.18, 0.96))
    for k, (x, z) in enumerate(spots):
        rot = R.uniform(-7, 7)
        def M(dx, dz, dy=0.0):   # not düzleminde nokta (not açısıyla döndürülmüş)
            a = math.radians(rot)
            return (x + dx * math.cos(a) + dz * math.sin(a), -0.046 - dy, z - dx * math.sin(a) + dz * math.cos(a))
        pm = KE._cached('paper' + str(k), lambda c=PAP[k], k=k: _paper_mat(c, k))
        note_mesh('paper', (x, -0.044, z), 0.24, 0.28, rot, pm, curl=0.035 if k in (0, 2, 4) else 0.012, seed=k)
        nl = 3 if k != 3 else 2
        for j in range(nl):
            ln = 0.15 - 0.04 * (j == nl - 1)
            rbox('line', M(-0.02 + (0.15 - ln) * -0.5, 0.06 - j * 0.055), (ln, 0.004, 0.016), LN, rot=(0, rot, 0), bevel=0)
        ic = (0.06, -0.085)
        if k == 0:      # kalp
            HRT = m_flat('#e84a5f', 0.06, 8, 'heart')
            for s in (-1, 1): blob('icon', M(ic[0] + s * 0.016, ic[1] + 0.01, 0.002), (0.022, 0.006, 0.022), HRT, sub=0, seg=10)
            rbox('icon', M(ic[0], ic[1] - 0.008, 0.002), (0.03, 0.006, 0.03), HRT, rot=(0, rot + 45, 0), bevel=0.004)
        elif k in (1, 4):   # onay kutusu
            BX = m_flat('#4a6fa8' if k == 1 else '#3f8a3a', 0.05, 6, 'box' + str(k))
            for (dx, dz, sx, sz) in ((0, 0.025, 0.055, 0.008), (0, -0.025, 0.055, 0.008), (-0.025, 0, 0.008, 0.055), (0.025, 0, 0.008, 0.055)):
                rbox('icon', M(ic[0] - 0.06 + dx, ic[1] + dz, 0.001), (sx, 0.004, sz), BX, rot=(0, rot, 0), bevel=0)
            CK = m_flat('#2f9e44', 0.05, 6, 'check')
            rbox('icon', M(ic[0] - 0.07, ic[1] - 0.004, 0.003), (0.03, 0.006, 0.011), CK, rot=(0, rot + 45, 0), bevel=0.003)
            rbox('icon', M(ic[0] - 0.045, ic[1] + 0.008, 0.003), (0.06, 0.006, 0.011), CK, rot=(0, rot - 55, 0), bevel=0.003)
        elif k == 2:    # yıldız çıkartması
            star(M(ic[0] - 0.02, ic[1], 0.004), 0.045, 0.012)
        elif k == 3:    # güneş resmi (bahçeyi sula)
            SUN = m_flat('#f39a2b', 0.06, 8, 'sun')
            cyl('icon', M(ic[0] - 0.05, ic[1] + 0.03, 0.002), 0.035, 0.006, SUN, rot=(90, 0, 0), verts=14, bevel=0)
            for q in range(8):
                a = q * math.pi / 4
                rbox('icon', M(ic[0] - 0.05 + math.cos(a) * 0.055, ic[1] + 0.03 + math.sin(a) * 0.055, 0.002), (0.02, 0.004, 0.008), SUN,
                     rot=(0, rot - math.degrees(a), 0), bevel=0)
        # raptiye: renkli baş + kısa gövde
        PIN = m_flat(PINC[k], 0.1, 6, 'pin' + str(k))
        blob('pin', M(0, 0.11, 0.022), (0.022, 0.016, 0.022), PIN, sub=0, seg=10)
        cyl('pin', M(0, 0.11, 0.008), 0.008, 0.02, PIN, rot=(90, 0, 0), verts=8, bevel=0)
    # eski, solmuş, yırtık not (sol alt köşe, yarısı arkada)
    OLD = KE._cached('paperold', lambda: _paper_mat('#e8dfc4', 9, old=True))
    note_mesh('paper', (-0.43, -0.038, 0.92), 0.2, 0.22, 12, OLD, curl=0.05, tear=True, seed=9)
    blob('pin', (-0.45, -0.06, 1.01), (0.02, 0.015, 0.02), m_flat('#9a8d7a', 0.1, 6, 'pinold'), sub=0, seg=10)
    # çatı: solmuş kiremit + bir tahta pul + bir kırık kiremit + yosun
    RF = [KE.m_tile2(c, f'brf{i}') for i, c in enumerate(('#d9653f', '#c95a3c', '#e2794f'))]
    WSH = KE.m_wood2('#9a7048', 'woodshingle', salt=0.8, ground=0.0)
    ang = math.radians(34); RZ = 2.17
    RW = KE.m_wood2('#6e4a2c', 'roofw', salt=0.5, ground=0.0)
    for side in (-1, 1):
        AT.plank('roofbase', (0, side * 0.24 * math.cos(ang), RZ - 0.24 * math.sin(ang) - 0.03), (1.6, 0.5, 0.03), RW, rot=(-side * 34, 0, 0), seed=side + 90)
        for r in range(4):
            d = 0.06 + r * 0.125
            for xi in range(6):
                x = -0.72 + xi * 0.29 + (0.145 if r % 2 else 0)
                if x > 0.75: continue
                m = RF[(xi * 7 + r * 3 + (side > 0)) % 3]
                sz = (0.28, 0.16, 0.03); jit = R.uniform(-3, 3); lift = 0.0
                if side < 0 and r == 2 and xi == 1: m = WSH                         # sonradan konmuş tahta pul
                if side < 0 and r == 3 and xi == 4: sz = (0.2, 0.12, 0.03); jit = 9   # kırık, kaymış
                if side > 0 and r == 1 and xi == 3: lift = 0.012; jit = -6
                AT.plank('shingle', (x + (0.03 if sz[0] < 0.28 else 0), side * d * math.cos(ang), RZ - d * math.sin(ang) + 0.01 + lift), sz, m,
                         rot=(-side * (34 + 4) + R.uniform(-1.5, 1.5), 0, jit), seed=xi + r * 7 + side * 3, amt=0.005)
    cyl('ridge', (0, 0, RZ + 0.04), 0.055, 1.62, RF[1], rot=(0, 90, 0), verts=12)
    # yosun: sırtta, arka eğimde, ön saçak köşesinde
    for (p, rr, sd, nrm) in (((-0.42, 0.02, RZ + 0.08), 0.06, 1, (0, 0.2, 1)), ((0.3, 0.33, 2.0), 0.07, 2, (0, 0.55, 0.83)),
                             ((-0.55, 0.45, 1.93), 0.06, 3, (0, 0.55, 0.83)), ((0.62, -0.42, 1.89), 0.045, 4, (0, -0.55, 0.83))):
        KE.moss_clump(p, rr, sd, nrm)
    star((0, 0, 2.3), 0.13, 0.05, pitch=90, gold=True)
    # yeni görev zili (sağ saçak altı): halat askı, pirinç çan (yeşil pas), tokmak, çekme ipi
    BR = KE._cached('brass', _brass)
    AT.strand_rope([(0.71, -0.05, 1.98), (0.71, -0.05, 1.86)], 0.012, KE.ROPE())
    AT.lathe('bell', [(0.001, 1.68), (0.08, 1.68), (0.075, 1.69), (0.055, 1.74), (0.045, 1.82), (0.03, 1.86), (0.001, 1.86)], BR, segs=16).location = (0.71, -0.05, 0)
    blob('bell', (0.71, -0.05, 1.67), (0.018, 0.018, 0.02), BR, sub=0, seg=8)
    AT.strand_rope([(0.71, -0.05, 1.67), (0.72, -0.06, 1.45), (0.71, -0.07, 1.3)], 0.008, KE.ROPE())
    # raf: kalem kutusu + deniz kabuğu
    AT.plank('ledge', (0, -0.08, 0.68), (0.9, 0.16, 0.035), FR, seed=77)
    CUP = KE.m_wood2('#a8713f', 'cup2', paint='#2fa3a0', ground=0.0)
    AT.lathe('cup', [(0.001, 0.7), (0.06, 0.7), (0.065, 0.82)], CUP, segs=12).location = (0.3, -0.08, 0)
    cyl('cup', (0.3, -0.08, 0.805), 0.058, 0.01, m_flat('#3a2a1c', 0.1, 6, 'cupin'), verts=12, bevel=0)
    for k, c in enumerate(('#e8463c', '#ffc93a', '#2f8adf')):
        tube('pencil', [(0.29 + k * 0.02, -0.08, 0.74), (0.27 + k * 0.03, -0.09, 0.93)], [0.01, 0.01], m_flat(c, 0.05, 6, 'pc' + c), res=2)
    KE.shell((-0.22, -0.09, 0.7), 0.06, yaw=-20, nrm=(0, -0.35, 1))
    # ayakta deniz yıldızı, ayak diplerinde halat bağ
    KE.starfish((-0.6, -0.078, 1.0), 0.075, yaw=15, nrm=(0, -1, 0.05))
    for sx in (-1, 1):
        for (z0, z1, rr, sd) in ((1.47, 1.55, 0.079, 3), (0.62, 0.7, 0.085, 7)):
            cx, cy = leg_center(sx, (z0 + z1) / 2)
            AT.rope_wrap((cx, cy, 0), rr, z0, z1, 2.5, KE.ROPE(), thick=0.014, seed=sx + sd)
    # dip: kum, okuyanların bastığı toprak, ot/çiçek/çakıl (eski yerleşim, aynı tohumlar)
    AT.dirt_patch(0, -0.42, 0.55, 0.28, 34)
    for sx in (-1, 1): KE.sand_drift(sx * 0.6, 0.0, 0.22, 0.2, 0.05, seed=sx + 2)
    KE.shell((0.32, -0.55, 0.012), 0.05, yaw=40, hexc='#f3e0cf', band='#d9a07a')
    for sx in (-1, 1):
        KE.moss_clump((sx * 0.6, 0.075, 0.07), 0.07, 10 + sx, (0, 0.7, 0.7))
        AT.base_ring(sx * 0.62, 0.0, 0.17, 60 + sx, flowers=1)
    AT.dress(0.95, 33, n_tufts=9, flowers=5, pebbles=3, bushes=[(-0.75, -0.3), (0.75, -0.25)], exclude=lambda x, y: abs(x) < 0.55 and abs(y) < 0.2)


def _paper_mat(hexc, k, old=False):
    """Kâğıt: hafif lif, kenara doğru sarımsı; eski notta su halkası ve güneş solması."""
    def b(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 8, 3), 0.3, 0.7, 0, 0.5), hexc, A._shade(hexc, 0.94))
        if old:
            col = G.mix(G.rng(G.noise(o, 3, 4), 0.45, 0.7, 0, 0.6), col, '#c9b48a')
            ring = G.rng(G.vor(o, 4.0, 'DISTANCE_TO_EDGE'), 0.02, 0.0, 0, 0.5)
            col = G.mix(ring, col, '#9a7f58')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat('paper' + hexc + str(k), b)


def _brass():
    def b(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 6, 4), 0.3, 0.7), '#c9952e', '#efc155')
        col = G.mix(G.rng(G.noise(o, 9, 5), 0.6, 0.72, 0, 0.6), col, '#5fa38a')          # yeşil pas
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat('brass', b)


def star(c, r, depth, yaw=0, pitch=90, gold=False):
    M = KE._cached('star_gold' if gold else 'star_y', lambda: _star_gold() if gold else m_flat('#ffc93a', 0.1, 8, 'star'))
    bm = bmesh.new(); pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5; rr = r if k % 2 == 0 else r * 0.45
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    top = [bm.verts.new((x, y, depth / 2)) for x, y in pts]; bot = [bm.verts.new((x, y, -depth / 2)) for x, y in pts]
    bm.faces.new(top); bm.faces.new(list(reversed(bot)))
    for i in range(10):
        j = (i + 1) % 10; bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = A.link_mesh('star', bm, [M]); o.location = c; o.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = depth * 0.35; bv.segments = 2
    return o


def _star_gold():
    """Çatı yıldızı: altın boya, kenarda aşınmış, yer yer pas/kir (yıllarca güneş ve tuzda)."""
    def b(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 5, 4), 0.3, 0.7), '#f2b62c', '#ffd24a')
        col = G.mix(G.math('MULTIPLY', G.edges(0.55, 0.65), 0.5), col, '#b8823a')
        col = G.mix(G.rng(G.noise(o, 12, 5), 0.64, 0.74, 0, 0.5), col, '#8a5a2a')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat('stargold', b)


# hedef: eğri/yoğun parçalar kendi içinde sadeleşir; kutular kalır
DECIM = [(r'^shingle$', 0.16), (r'^roofbase$', 0.12), (r'^(frame|ledge|header|patch)$', 0.3), (r'^(lush|tufts|rosette)$', 0.4),
         (r'^(pet|fc)$', 0.55), (r'^(Icosphere|moss)$', 0.4), (r'^(rope|fray)$', 0.45), (r'^(stem)$', 0.6), (r'^(nail|streak)$', 0.5),
         (r'^(starfish|shell)$', 0.35), (r'^(sand|wornground)$', 0.35), (r'^(ridge)$', 0.6), (r'^bell$', 0.6)]
# UV önemi: okunması gereken notlar/başlık/simgeler büyük, çimen/çakıl küçük
WEIGHTS = [(r'^(paper|line|icon|header)$', 1.9), (r'^(pin|star)$', 1.4), (r'^(cork)$', 1.3), (r'^(frame|strap)$', 1.15), (r'^(shingle|ridge)$', 1.05),
           (r'^(lush|tufts|rosette|stem|pet|fc|Icosphere|fray|sand|wornground)$', 0.5), (r'^(roofbase)$', 0.7)]

if __name__ == '__main__':
    KE.main(NAME, build, DECIM, WEIGHTS, CAP, ds_low=True)
