# Evim (oyuncunun ada evi) — oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Temel: house_cottage.py v3 (onaylı tasarım: kazıklar üstünde güverte, yatay tahta duvar, mercan kiremit çatı, taş baca, turkuaz
# kapı/panjur, krem pervaz, çiçek kasaları, fener, pati tabelası, korkuluk, fıçı, sandık). O betik içe aktarılınca kendini çalıştırdığı
# için yerleşim buraya aynen taşındı (aynı ölçü ve rastgele sıra); oyun EnvFootprint ile 8,6 m'ye ölçekler → dış ölçüler eski FBX
# ile aynı tutuldu (eski FBX'te küresel sadeleşmeyle silinen en dıştaki basamak taşı yok; ikinci taş içeri alındı).
# Sıcak, içinde yaşanan bir ev + ada eskitmesi:
#   - çatı: kiremitler hafif düzensiz, birkaç tanesi sonradan konmuş (açık/koyu ton), birkaçı kırık-küçük; oyuklarda ve kuzey (arka)
#     eğimde yosun öbekleri, sırtta yosun; saçak altında tuz/su izi; bacada liken + tepede is;
#   - duvar: sıcak bal tonu tahtalar, birkaç değiştirilmiş açık tahta (çivili), pencere ve saçak altlarında su izi, dipte toprak + yosun;
#   - kapı ve panjurlar güneşte solmuş, pul pul dökülmüş turkuaz; kapıda deniz yıldızı, önünde hasır paspas;
#   - pencerelerde perde (içerisi yaşanıyor), çiçek kasalarında gerçek yapraklı çiçekler;
#   - verandada saksı çiçeği, duvara yaslı olta, deniz kabuğu rüzgâr çanı, yağmur fıçısı (su yüzeyli), güverte kenarında ve
#     basamaklarda kum, değiştirilmiş güverte tahtaları; kazık diplerinde yosun; basamak önünde kabuk ve deniz yıldızı.
# Kullanım: python -I bld/b_home.py -- <çıktı> [b_home] [--draft <png>] [--stats]
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import koy_eskitme as KE
from koy_eskitme import AT, A, V, MN, bpy, bmesh, rbox, blob, cyl, tube, m_flat, m_leaf

NAME = 'b_home'
CAP = 18000
W, D, H = 2.6, 2.2, 1.7          # duvar genişliği (x), derinlik (y), yükseklik
Z0 = 0.38                        # döşeme üstü
TOP = Z0 + H
RISE, OVY, OVX = 0.95, 0.38, 0.3


def m_chimney():
    """Baca taşı: taş taş ton farkı (sıcak gri ↔ kum rengi), koyu benek, sarı-yeşil ve turuncu liken, tepeye doğru is; oyukta kir.
    Desen dünya konumunda (taşlar küçük: nesne koordinatında her taş tek düze görünüyordu)."""
    def b(nt, bsdf):
        G = KE.G2(nt); p = G.pos()
        rp = KE.ramp(nt, list(zip((0.3, 0.45, 0.6, 0.75), ('#756e64', '#938a7d', '#ad9f88', '#bdb3a2')))); nt.links.new(G.noise(p, 3.2, 3), rp.inputs['Fac'])
        col = G.mix(G.rng(G.vor(p, 34), 0.0, 0.12, 0.45, 0), rp.outputs[0], '#4f4a44')
        lich = G.math('MULTIPLY', G.rng(G.vor(p, 11), 0.0, 0.2, 1, 0), G.rng(G.noise(p, 2.5, 3), 0.45, 0.6, 0, 0.85))
        col = G.mix(lich, col, '#cfcb8a')
        lich2 = G.math('MULTIPLY', G.rng(G.vor(G.mapping(p, (1.3, 1.3, 1.3)), 9), 0.0, 0.12, 1, 0), G.rng(G.noise(p, 2.0, 3), 0.6, 0.7, 0, 0.7))
        col = G.mix(lich2, col, '#d8954a')
        soot = G.rng(G.math('ADD', G.wz(), G.math('MULTIPLY', G.noise(p, 4, 4), 0.25)), TOP + RISE + 0.15, TOP + RISE + 0.6, 0, 0.85)
        col = G.mix(soot, col, '#3a3530')
        col = G.mix(G.rng(G.ao(0.12), 0.8, 0.35, 0, 0.55), col, '#3f3a35')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat('chstone', b)


def curtain(cx, cy, cz, w, h, axis, M, side, seed=0):
    """Pencerede toplanmış perde (yanda kıvrımlı kumaş şerit). Camın hemen önünde durur: cam pişirmede opak, arkasındaki perde
    görünmezdi. axis 'x': ön duvar (−Y'ye bakar), 'y': yan duvar."""
    NY, NZ = 8, 4; verts = []; faces = []; grid = []
    for i in range(NZ + 1):
        t = i / NZ; row = []
        for j in range(NY + 1):
            u = j / NY
            a = (side * (w / 2) - side * u * w * 0.34)
            fold = 0.018 * math.sin(u * math.pi * 4 + seed)
            z = cz + h / 2 - t * h
            if axis == 'x': p = (cx + a, cy - 0.024 - fold, z)                   # camın önünde, pervaz/kayıtların arkasında
            else: p = (cx + (0.024 + fold if cx > 0 else -0.024 - fold), cy + a, z)
            row.append(len(verts)); verts.append(p)
        grid.append(row)
    for i in range(NZ):
        for j in range(NY):
            faces.append((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    o = KE._mesh('curtain', verts, faces, M)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    out = V((0, -1, 0)) if axis == 'x' else V((1 if cx > 0 else -1, 0, 0))
    if sum(f.normal.dot(out) for f in bm.faces) < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o


def build():
    R = random.Random(7)
    hex_w = ['#b8763f', '#a6662f', '#c48650', '#9a5e32', '#b06d3c']
    WOOD = [KE.m_wood2(c, f'wood{i}', salt=0.75, ground=0.0, moss=0.0) for i, c in enumerate(hex_w)]
    DARK = KE.m_wood2('#6a4226', 'darkwood', salt=0.5, ground=0.45)
    DECK = [KE.m_wood2(c, f'deck{i}', salt=0.4, ground=0.0) for i, c in enumerate(['#c4935c', '#b5844f', '#cfa26a'])]
    TEAL = KE.m_wood2('#a87a4c', 'teal', paint='#22a19c', age=1.2, salt=0.7, ground=0.0, chips=1.15)
    CREAM = KE.m_wood2('#b98e5e', 'trim', paint='#f3e4c2', age=1.1, salt=0.8, ground=0.0)
    ROOF = [KE.m_tile2(c, f'roof{i}') for i, c in enumerate(['#d9613f', '#cb5639', '#e2724e', '#c96447'])]
    ROOF_NEW = KE.m_tile2('#ee8a5f', 'roofnew', age=0.3, moss=0.1); ROOF_OLD = KE.m_tile2('#a9553e', 'roofold', age=1.4, moss=0.9)
    WSH = KE.m_wood2('#9a7048', 'woodshingle', salt=0.8, ground=0.0)
    STONE = KE.m_stone2('housestone'); CH = m_chimney()
    def glass(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 2, 3), 0.3, 0.7), '#7fc4de', '#b9e4f2')
        col = G.mix(G.rng(G.noise(G.mapping(o, (1, 1, 8)), 1.5, 3), 0.55, 0.65, 0, 0.35), col, '#e9f7fb')   # yansıma şeridi
        col = G.mix(G.rng(G.noise(o, 6, 4), 0.62, 0.72, 0, 0.35), col, '#cfd6cc')                       # tuz buğusu
        nt.links.new(col, bsdf.inputs['Base Color'])
    GLASS = KE.nodes_mat('glass2', glass)
    GOLD = KE._cached('brass', _brass)
    LAMP = AT.m_glow('#ffc861', 'lampglow', lamp=(0.0, 0.0, 0.0, 0.12))   # nesnenin kendi merkezi
    objs = []

    def plank_row(axis, fixed, a0, a1, z, h, holes=()):
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

    # kazıklar + güverte + basamaklar
    for x in (-1.5, 0, 1.5):
        for y in (-1.75, 0, 1.25):
            objs.append(cyl('post', (x, y, 0.15), 0.08, 0.36, DARK, verts=10))
    n = 0; y = -1.85
    while y < 1.4:
        objs.append(rbox('deck', (0, y + 0.09, Z0 - 0.04), (3.5, 0.17, 0.07), DECK[n % 3], rot=(0, R.uniform(-0.5, 0.5), 0), bevel=0.015)); y += 0.185; n += 1
    STEP = KE.m_wood2('#c79a64', 'step', salt=0.3, ground=0.0)
    for i, (yy, zz) in enumerate(((-2.12, 0.22), (-2.38, 0.08))):
        objs.append(rbox('step', (0, yy, zz), (1.0, 0.26, 0.07), STEP, bevel=0.015))
        for sx in (-0.48, 0.48): objs.append(rbox('stepside', (sx, yy + 0.05, zz - 0.06), (0.06, 0.3, 0.14), DARK, bevel=0.01))
    # duvarlar
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
    objs.append(rbox('inner', (0, 0, Z0 + H / 2), (W - 0.1, D - 0.1, H), m_flat('#3a2818', 0.1, 6, 'hin'), bevel=0))
    # kapı
    for i in range(4):
        objs.append(rbox('door', (-0.285 + i * 0.19, -D / 2 - 0.01, Z0 + 0.6), (0.18, 0.05, 1.18), TEAL, bevel=0.012))
    for zz in (Z0 + 0.25, Z0 + 0.95):
        objs.append(rbox('brace', (0, -D / 2 - 0.045, zz), (0.72, 0.03, 0.09), TEAL, bevel=0.01))
    objs.append(blob('knob', (0.25, -D / 2 - 0.08, Z0 + 0.6), (0.04, 0.04, 0.04), GOLD, sub=1, seg=12))
    for (cx, cz, sx, sz) in ((-0.44, Z0 + 0.62, 0.1, 1.28), (0.44, Z0 + 0.62, 0.1, 1.28), (0, Z0 + 1.27, 0.98, 0.12)):
        objs.append(rbox('dframe', (cx, -D / 2 - 0.04, cz), (sx, 0.07, sz), CREAM, bevel=0.015))

    CUR = [AT.m_cloth('#f3a7b3', '#fff4ea', stripes=10.0, name='curtain1', age=0.6), AT.m_cloth('#f6d36e', '#fff4ea', stripes=10.0, name='curtain2', age=0.6)]
    BOXW = KE.m_wood2('#9a5e32', 'flowerbox', salt=0.8, ground=0.0)
    def window(cx, cy, cz, w, h, axis, k):
        def box(dx, dz, sx, sz, m, depth=0.07, off=0.0, name='w'):
            if axis == 'x': return rbox(name, (cx + dx, cy - off, cz + dz), (sx, depth, sz), m, bevel=0.012)
            return rbox(name, (cx + (off if cx > 0 else -off), cy + dx, cz + dz), (depth, sx, sz), m, bevel=0.012)
        out = 0.06
        objs.append(box(0, 0, w, h, GLASS, depth=0.02, name='glass'))
        for dz in (-h / 2, h / 2): objs.append(box(0, dz, w + 0.14, 0.08, CREAM, off=out, name='wframe'))
        for dx in (-w / 2, w / 2): objs.append(box(dx, 0, 0.08, h + 0.14, CREAM, off=out, name='wframe'))
        objs.append(box(0, 0, 0.04, h, CREAM, off=out, name='wframe')); objs.append(box(0, 0, w, 0.04, CREAM, off=out, name='wframe'))
        for s in (-1, 1):
            objs.append(box(s * (w / 2 + 0.2), 0, 0.28, h + 0.1, TEAL, off=out + 0.01, name='shutter'))
            curtain(cx, cy, cz, w, h, axis, CUR[k % 2], s, seed=k * 3 + s)
        objs.append(box(0, -h / 2 - 0.12, w + 0.2, 0.14, BOXW, depth=0.16, off=out + 0.06, name='fbox'))
        # çiçek kasası: toprak + yaprak demeti + çiçekler
        fz = cz - h / 2 - 0.05
        if axis == 'x': base = (cx, cy - out - 0.08)
        else: base = (cx + (out + 0.08 if cx > 0 else -out - 0.08), cy)
        objs.append(box(0, -h / 2 - 0.06, w + 0.12, 0.02, m_flat('#5a3e26', 0.2, 10, 'soil2'), depth=0.12, off=out + 0.06, name='soil'))
        RR = random.Random(50 + k); pts = []
        for i in range(4):
            fx = -w / 2 + 0.08 + i * (w - 0.16) / 3
            pts.append((base[0] + fx, base[1]) if axis == 'x' else (base[0], base[1] + fx))
        lv = A.mesh_from_blades('boxleaf', A.rosette(pts, RR, sizes=(0.1, 0.15), leaves=6), [m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'boxleafm')])
        lv.location.z = fz
        KE.flowers_at([(p[0], p[1], fz, RR.uniform(0.1, 0.16)) for p in pts], RR, size=0.75)

    window((winF[0] + winF[1]) / 2, -D / 2, (winF[2] + winF[3]) / 2, 0.5, 0.5, 'x', 0)
    window(-W / 2, 0, (winS[2] + winS[3]) / 2, 0.6, 0.45, 'y', 1)
    window(W / 2, 0, (winS[2] + winS[3]) / 2, 0.6, 0.45, 'y', 2)

    # çatı: sırt x yönünde; şaşırtmalı kiremit sıraları — birkaçı sonradan konmuş/eski/kırık
    half = D / 2 + OVY
    ang = math.atan2(RISE, D / 2)
    slope = math.hypot(half, RISE * half / (D / 2))
    RW = random.Random(77)
    for side in (-1, 1):
        cy = side * half / 2; cz = TOP + RISE * (1 - (half / 2) / (D / 2)) + 0.02
        objs.append(rbox('roofbase', (0, cy, cz), (W + 2 * OVX, slope, 0.05), DARK, rot=(-side * math.degrees(ang), 0, 0), bevel=0.01))
        rows = int(slope / 0.17)
        for r in range(rows):
            t = 1 - (r + 0.5) / rows
            yy = side * half * t
            zz = TOP + RISE * (1 - abs(yy) / (D / 2)) + 0.07
            x = -W / 2 - OVX + (0.16 if r % 2 else 0.0); xi = 0
            while x < W / 2 + OVX - 0.05:
                wdt = min(0.31, W / 2 + OVX - x)
                m = R.choice(ROOF); rot = (-side * math.degrees(ang) + R.uniform(-2, 2), R.uniform(-1.5, 1.5), 0)
                sz = (wdt - 0.02, 0.24, 0.035); off = (0, 0, 0)
                q = RW.random()
                if q < 0.06: m = ROOF_NEW                                              # sonradan konmuş, parlak
                elif q < 0.13: m = ROOF_OLD                                            # eski, koyu, yosunlu
                elif q < 0.17: sz = (wdt * 0.7, 0.2, 0.035); off = (RW.uniform(-0.03, 0.03), -side * 0.02, 0)   # kırık, kaymış
                rot = (rot[0] + RW.uniform(-2.5, 2.5), rot[1] + RW.uniform(-2, 2), RW.uniform(-3, 3))
                if side < 0 and (r, xi) in ((3, 2), (3, 3), (4, 2)): m = WSH        # ön eğimde tahta pul yaması (okunur onarım)
                if not (side < 0 and (r, xi) == (5, 9)):                            # bir kiremit düşmüş: alttaki koyu tahta görünür
                    objs.append(rbox('shingle', (x + wdt / 2 + off[0], yy + off[1], zz), sz, m, rot=rot, bevel=0.012))
                x += 0.32; xi += 1
    objs.append(cyl('ridge', (0, 0, TOP + RISE + 0.1), 0.09, W + 2 * OVX + 0.05, ROOF[1], rot=(0, 90, 0), verts=14))
    # alınlıklar + yuvarlak tavan penceresi
    for sx in (-1, 1):
        k = 0; yy = -D / 2 + 0.1
        while yy < D / 2:
            hh = RISE * (1 - abs(yy) / (D / 2))
            if hh > 0.05: objs.append(rbox('gable', (sx * W / 2, yy, TOP + hh / 2), (0.07, 0.18, hh), WOOD[k % 5], bevel=0.015))
            yy += 0.19; k += 1
        bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.04, location=(sx * (W / 2 + 0.05), 0, TOP + 0.35), rotation=(0, math.radians(90), 0), major_segments=40, minor_segments=10)
        t = bpy.context.object; t.name = 'attic'; t.data.materials.append(CREAM); [setattr(p, 'use_smooth', True) for p in t.data.polygons]; objs.append(t)
        objs.append(cyl('attic', (sx * (W / 2 + 0.03), 0, TOP + 0.35), 0.15, 0.03, GLASS, rot=(0, 90, 0), verts=20))
    # taş baca (arka eğim): liken + tepede is
    cz = TOP + 0.35
    while cz < TOP + RISE + 0.7:
        for dx in (-0.12, 0.12):
            objs.append(rbox('stone', (0.75 + dx + R.uniform(-0.02, 0.02), 0.55, cz), (0.22, 0.42, 0.15), CH, rot=(0, 0, R.uniform(-4, 4)), bevel=0.04, seg=3))
        cz += 0.15
    objs.append(rbox('chcap', (0.75, 0.55, cz + 0.02), (0.56, 0.5, 0.08), DARK, bevel=0.02))
    # fener, tabela, korkuluk, fıçı, sandık
    objs.append(rbox('arm', (-0.7, -D / 2 - 0.12, Z0 + 1.35), (0.05, 0.25, 0.05), KE.IRON(), bevel=0.01))
    objs.append(rbox('lamp', (-0.7, -D / 2 - 0.22, Z0 + 1.2), (0.14, 0.14, 0.2), LAMP, bevel=0.02))
    objs.append(rbox('lamptop', (-0.7, -D / 2 - 0.22, Z0 + 1.32), (0.2, 0.2, 0.05), KE.IRON(), bevel=0.015))
    objs.append(cyl('sign', (0, -D / 2 - 0.06, TOP - 0.3), 0.15, 0.05, CREAM, rot=(90, 0, 0), verts=24))
    PAW = m_flat('#e0684a', 0.1, 8, 'pawm')
    for (dx, dz, r) in ((0, -0.03, 0.06), (-0.07, 0.05, 0.028), (-0.025, 0.08, 0.028), (0.025, 0.08, 0.028), (0.07, 0.05, 0.028)):
        objs.append(blob('paw', (dx * 0.75, -D / 2 - 0.095, TOP - 0.3 + dz * 0.75), (r * 0.75, 0.015, r * 0.68), PAW, sub=1, seg=12))
    for sx in (-1, 1):
        for yy in (-1.8, -1.45):
            objs.append(rbox('rpost', (sx * 1.65, yy, Z0 + 0.3), (0.08, 0.08, 0.6), DARK, bevel=0.015))
        objs.append(rbox('rail', (sx * 1.65, -1.45, Z0 + 0.58), (0.07, 0.75, 0.07), WOOD[2], bevel=0.015))
        objs.append(rbox('rail2', (sx * 1.65, -1.45, Z0 + 0.32), (0.05, 0.75, 0.05), WOOD[0], bevel=0.012))
    # yağmur fıçısı: şişkin gövde, demir çemberler, üstte su yüzeyi
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.22, depth=0.5, location=(1.2, -1.6, Z0 + 0.25))
    bar = bpy.context.object; bar.name = 'barrel'; bar.data.materials.append(KE.m_wood2('#9c6238', 'barrelw', salt=0.5, ground=0.0))
    bm = bmesh.new(); bm.from_mesh(bar.data)
    for v in bm.verts:
        k = 1 + 0.18 * (1 - (v.co.z / 0.25) ** 2); v.co.x *= k; v.co.y *= k
    bm.to_mesh(bar.data); bm.free(); [setattr(p, 'use_smooth', True) for p in bar.data.polygons]; objs.append(bar)
    for zz in (Z0 + 0.08, Z0 + 0.42, Z0 + 0.5):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.235 if zz < Z0 + 0.49 else 0.215, minor_radius=0.015, location=(1.2, -1.6, zz), major_segments=24, minor_segments=6)
        t = bpy.context.object; t.name = 'hoop'; t.data.materials.append(KE.IRON()); objs.append(t)
    WATER = m_flat('#2f7f8c', 0.15, 6, 'water')
    cyl('water', (1.2, -1.6, Z0 + 0.503), 0.2, 0.006, WATER, verts=20, bevel=0)
    objs.append(rbox('crate', (-1.25, -1.55, Z0 + 0.2), (0.4, 0.4, 0.4), WOOD[2], rot=(0, 0, 12), bevel=0.03))
    for d in (-0.13, 0, 0.13):
        objs.append(rbox('slat', (-1.25 + d * math.cos(math.radians(12)), -1.55 - 0.205 + d * math.sin(math.radians(12)), Z0 + 0.2), (0.08, 0.02, 0.42), WOOD[3], rot=(0, 0, 12), bevel=0.01))

    # --- ada hayatı ve eskitme eklemeleri (ayrı rastgele kaynak: eski yerleşimin sırası bozulmasın)
    E = random.Random(2024)
    # değiştirilmiş açık tahtalar (duvar + güverte), çivili
    NEWW = KE.m_wood2('#d2a26a', 'newplank', salt=0.15, ground=0.0, silver=0.03)
    walls = [o for o in objs if o.name.startswith('plank') and o.dimensions.x > 0.6 and abs(o.location.y + D / 2) < 0.01]
    side_w = [o for o in objs if o.name.startswith('plank') and o.dimensions.y > 0.6 and abs(abs(o.location.x) - W / 2) < 0.01]
    for o in E.sample(walls, 2) + E.sample(side_w, 2):
        o.data.materials.clear(); o.data.materials.append(NEWW)
        if abs(o.location.y + D / 2) < 0.01:
            for sx in (-1, 1): AT.nail((o.location.x + sx * (o.dimensions.x / 2 - 0.06), -D / 2 - 0.036, o.location.z), (0, -1, 0), streak=True)
        else:
            sgn = 1 if o.location.x > 0 else -1
            for sy in (-1, 1): AT.nail((sgn * (W / 2 + 0.036), o.location.y + sy * (o.dimensions.y / 2 - 0.06), o.location.z), (sgn, 0, 0), streak=True)
    decks = [o for o in objs if o.name.startswith('deck')]
    for o in (decks[1], decks[6]):
        o.data.materials.clear(); o.data.materials.append(NEWW)
    # kapıda deniz yıldızı, önünde hasır paspas, yanında saksı
    KE.starfish((-0.12, -D / 2 - 0.04, Z0 + 1.1), 0.07, yaw=12, nrm=(0, -1, 0), hexc='#f0844a')
    def mat_weave(nt, bsdf):
        G = KE.G2(nt); o = G.obj(); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(o, sp.inputs[0])
        wv = G.math('SINE', G.math('MULTIPLY', G.math('ADD', sp.outputs['X'], G.math('MULTIPLY', G.math('SINE', G.math('MULTIPLY', sp.outputs['Y'], 60)), 0.01)), 70))
        col = G.mix(G.rng(wv, -0.6, 0.8), '#9c7a46', '#d6b77c')
        col = G.mix(G.rng(G.math('ABSOLUTE', sp.outputs['Y']), 0.11, 0.13), col, '#b8503a')            # kenar şeridi
        col = G.mix(G.rng(G.noise(o, 5, 4), 0.55, 0.7, 0, 0.3), col, '#6e5636')
        nt.links.new(col, bsdf.inputs['Base Color'])
    rbox('mat', (0, -D / 2 - 0.28, Z0 + 0.006), (0.66, 0.32, 0.014), KE.nodes_mat('mat', mat_weave), rot=(0, 0, 2), bevel=0.005)
    POT = AT.m_plaster('#cf6f48', name='pot2', dirt=0.25)
    AT.lathe('pot', [(0.001, 0.0), (0.1, 0.0), (0.14, 0.2), (0.155, 0.22)], POT, segs=14).location = (-0.62, -D / 2 - 0.28, Z0)
    cyl('pot', (-0.62, -D / 2 - 0.28, Z0 + 0.205), 0.135, 0.01, m_flat('#5a3e26', 0.2, 10, 'soil3'), verts=14, bevel=0)
    RP = random.Random(5)
    pl = A.mesh_from_blades('potplant', A.rosette([(-0.62, -D / 2 - 0.28)], RP, sizes=(0.2, 0.3), leaves=9), [m_leaf('#2f8a3a', '#56b64a', '#a6dc6a', '#cdee92', 'fleaf2')])
    pl.location.z = Z0 + 0.19
    KE.flowers_at([(-0.58, -D / 2 - 0.25, Z0 + 0.2, 0.25), (-0.67, -D / 2 - 0.32, Z0 + 0.2, 0.21)], RP)
    # duvara yaslı olta (makara, misina, yüzdürücü)
    ROD = KE.m_wood2('#a77a46', 'rod', ground=0.0)
    tube('rod', [(-1.02, -1.32, Z0 + 0.02), (-0.97, -1.22, Z0 + 0.9), (-0.92, -1.165, Z0 + 1.62)], [0.014, 0.011, 0.006], ROD, res=3)
    cyl('reel', (-0.995, -1.3, Z0 + 0.32), 0.045, 0.03, KE.IRON(), rot=(0, 90, 0), verts=12, bevel=0.004)
    tube('line', [(-0.92, -1.165, Z0 + 1.62), (-0.9, -1.2, Z0 + 1.25), (-0.9, -1.21, Z0 + 1.0)], [0.0035, 0.0035, 0.0035], m_flat('#e9e4d4', 0.05, 6, 'line'), res=3)
    KE.buoy((-0.9, -1.21, Z0 + 0.97), 0.03, '#e8463c', name='bobber')
    # kabuk rüzgâr çanı (saçak altından, kapı ile pencere arası)
    DRIFT = KE.m_wood2('#b7ab95', 'driftw', ground=0.0, silver=0.5)
    zc = 1.72
    tube('chimebar', [(0.4, -1.36, zc), (0.56, -1.36, zc)], [0.012, 0.012], DRIFT, res=2)
    tube('chimestr', [(0.48, -1.36, zc), (0.48, -1.36, zc + 0.05)], [0.003, 0.003], m_flat('#e9e4d4', 0.05, 6, 'line'), res=2)
    for i, (x, L) in enumerate(((0.41, 0.16), (0.46, 0.24), (0.51, 0.19), (0.555, 0.27))):
        tube('chimestr', [(x, -1.36, zc), (x, -1.36, zc - L)], [0.0028, 0.0028], m_flat('#e9e4d4', 0.05, 6, 'line'), res=2)
        KE.shell((x, -1.36, zc - L - 0.035), 0.032, yaw=0, nrm=(0, -1, 0.15), hexc=('#f6e2d0', '#f3d2c6', '#fbeedd', '#f1d9b8')[i], band='#d9907a')
    # güverte kenarında ve basamaklarda kum; basamak önünde kabuk ve deniz yıldızı
    KE.sand_drift(0.15, -1.76, 0.75, 0.12, 0.03, seed=11, lean=(0, 0.6), z0=Z0 - 0.005)
    KE.sand_drift(-0.1, -2.12, 0.42, 0.1, 0.025, seed=12, lean=(0, 0.5), z0=0.255)
    KE.sand_drift(0.0, -2.6, 0.75, 0.28, 0.05, seed=13, lean=(0, 0.6))
    KE.shell((0.42, -2.78, 0.012), 0.055, yaw=-20); KE.shell((-0.45, -2.6, 0.012), 0.045, yaw=50, hexc='#f3dcd0', band='#d98f7a')
    KE.starfish((0.55, -2.5, 0.01), 0.08, yaw=25, hexc='#ee7444')
    # yosun: arka çatı eğiminde (kuzey) ve oyuklarda, sırtta, baca dibinde; kazık ve dip
    def roof_pt(x, t, side):
        yy = side * half * t; zz = TOP + RISE * (1 - abs(yy) / (D / 2)) + 0.07 + 0.03
        return (x, yy, zz)
    nrm_b = (0, math.sin(ang), math.cos(ang)); nrm_f = (0, -math.sin(ang), math.cos(ang))
    for k, (x, t, rr) in enumerate(((-1.1, 0.82, 0.11), (-0.3, 0.55, 0.09), (0.35, 0.9, 0.1), (1.25, 0.7, 0.085), (-0.85, 0.3, 0.07), (0.9, 0.35, 0.075))):
        KE.moss_clump(roof_pt(x, t, 1), rr, 30 + k, nrm_b)
    for k, (x, t, rr) in enumerate(((-1.45, 0.88, 0.07), (1.4, 0.85, 0.06), (-0.62, 0.7, 0.06), (0.42, 0.93, 0.055), (1.02, 0.55, 0.05))):
        KE.moss_clump(roof_pt(x, t, -1), rr, 40 + k, nrm_f)
    for k, x in enumerate((-1.2, -0.2, 0.95)):
        KE.moss_clump((x, 0.02, TOP + RISE + 0.17), 0.06, 45 + k, (0, 0.3, 1))
    KE.moss_clump((0.75, 0.3, TOP + 0.5), 0.08, 48, (0, -0.4, 0.9))
    for k, (x, y) in enumerate(((-1.5, 1.25), (0, 1.25), (1.5, 1.25), (-1.5, 0.0), (1.5, -1.75))):
        KE.moss_clump((x, y + 0.07, 0.05), 0.08, 50 + k, (0, 0.6, 0.8))
    KE.moss_clump((-W / 2 + 0.1, D / 2 + 0.06, Z0 + 0.04), 0.07, 56, (0, 0.6, 0.8))

    # arka duvar dibinde (güverte üstünde) saçak altına istiflenmiş odun + duvarda asılı eski şamandıralar
    LOGM = KE.m_bark2('homelog', '#7a5536'); EG = KE.m_endgrain2('homeend')
    for k in range(7):
        row = 0 if k < 4 else 1
        x = -1.05 + (k % 4) * 0.15 + row * 0.075; z = Z0 + 0.065 + row * 0.12; yc = D / 2 + 0.21
        lg = AT.lathe('wood', [(0.001, -0.175), (0.065, -0.175), (0.065, 0.175), (0.001, 0.175)], LOGM, segs=10)
        lg.rotation_euler = (math.radians(90), 0, 0); lg.location = (x, yc, z)
        cyl('wend', (x, yc + 0.178, z), 0.06, 0.008, EG, rot=(90, 0, 0), verts=10, bevel=0)
    for k, (x, c) in enumerate(((0.55, '#f0663a'), (0.78, '#f2b632'))):
        KE.buoy((x, D / 2 + 0.11, Z0 + 0.95 - 0.08 * k), 0.07, c)
        KE.rope3([(x, D / 2 + 0.06, Z0 + 1.3), (x, D / 2 + 0.1, Z0 + 1.1), (x, D / 2 + 0.11, Z0 + 1.03 - 0.08 * k)], 0.008, seg=0.03, around=6)
    AT.nail((0.665, D / 2 + 0.04, Z0 + 1.3), (0, 1, 0), streak=True)
    # evin dibi (house_cottage v3): kazık diplerinde taş, basamak taşları, ot öbekleri, çalı, çiçek
    R3 = random.Random(31)
    for x in (-1.5, 0, 1.5):
        for y in (-1.75, 0, 1.25):
            for k in range(3):
                a = k * 2.1 + R3.uniform(0, 1)
                A.pebble((x + math.cos(a) * 0.14, y + math.sin(a) * 0.14, 0.04), R3.uniform(0.07, 0.1), STONE, k + int(x * 10 + y * 7))
    # basamak taşları: eski betikte taşın ölçeği DÜNYA orijinine göre veriliyordu (pebble konumu ağa işler) → taşlar (x, 0,8·y)'de,
    # 0,35 basık duruyordu; oyundaki FBX böyle (ölçü ondan). Aynı yerler, ölçek artık taşın kendi merkezinde; basamak altındaki taş yok.
    for k, (x, y) in enumerate(((-0.12, -2.66), (0.1, -3.0))):
        st = A.pebble((x, y, 0.0), 0.2, STONE, 41 + k)
        for v in st.data.vertices: v.co = V((x + (v.co.x - x), y + (v.co.y - y) * 0.8, v.co.z * 0.35 + 0.012))
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    A.mesh_from_blades('tufts', A.tufts((0.0, 0.0, 0.0), 2.4, 26, 5, h=(0.2, 0.36)), [G1])
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    A.mesh_from_blades('basebush', A.rosette([(1.9, -1.0), (-1.95, -0.8), (1.85, 1.1), (-1.9, 1.2)], R3, sizes=(0.3, 0.45), leaves=10), [BL])
    A.flower_heads([(1.95, -1.25, 0.32), (-2.0, -1.0, 0.28), (1.7, 1.35, 0.3), (-0.75, -2.35, 0.22), (0.8, -2.4, 0.24)], R3)


def _brass():
    def b(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 6, 4), 0.3, 0.7), '#c9952e', '#efc155')
        col = G.mix(G.rng(G.noise(o, 9, 5), 0.6, 0.72, 0, 0.5), col, '#5fa38a')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat('brass', b)


DECIM = [(r'^shingle$', 0.12), (r'^(plank|gable)$', 0.25), (r'^(deck|step|stepside)$', 0.25), (r'^(roofbase)$', 0.3),
         (r'^(corner|rpost|rail|rail2|dframe|door|brace|wframe|shutter|fbox|soil|slat|crate|chcap|arm|lamptop|lamp)$', 0.3),
         (r'^stone$', 0.15), (r'^(tufts|basebush|boxleaf|potplant|lush|rosette)$', 0.3), (r'^(pet|fc)$', 0.2), (r'^(Icosphere)$', 0.25),
         (r'^moss$', 0.18), (r'^(stem)$', 0.25), (r'^(nail|streak)$', 0.3), (r'^(starfish|shell)$', 0.18), (r'^(attic)$', 0.15), (r'^(ridge)$', 0.5),
         (r'^(paw|knob)$', 0.12), (r'^barrel$', 0.4), (r'^hoop$', 0.25), (r'^(post)$', 0.25), (r'^(pot|reel|rod|line|chimebar|chimestr)$', 0.4),
         (r'^(bobber|buoy)$', 0.12), (r'^(curtain)$', 0.5), (r'^(sign|mat)$', 0.4), (r'^(rope)$', 0.3), (r'^(wood|wend)$', 0.4)]
WEIGHTS = [(r'^(door|brace|knob|dframe|sign|paw|starfish|mat)$', 1.6), (r'^(glass|wframe|shutter|curtain|fbox|boxleaf)$', 1.4),
           (r'^(shingle|ridge)$', 1.1), (r'^(plank)$', 1.0), (r'^(gable)$', 0.9), (r'^(deck|step)$', 1.0),
           (r'^(tufts|basebush|stem|pet|fc|Icosphere|sand)$', 0.5), (r'^(inner|post|roofbase)$', 0.4)]

if __name__ == '__main__':
    KE.main(NAME, build, DECIM, WEIGHTS, CAP, ds_low=True, cage=0.025, ray=0.1)
