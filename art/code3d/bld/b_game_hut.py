# Oyun Kulübesi oyun modeli (24 Ekim 2026; kullanıcı: "haritadaki bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Eski model (assets_town.c_game_hut) 8 bin üçgene küresel sadeleşip yalnız renk + AO pişiyordu: tahta damarı, boya pulları, pul
# kiremitlerin kenarı eriyordu, normal haritası yoktu. Aynı yerleşim (orijin, kapı = −Y, boy ve yatay kapsam eskisiyle aynı) yeniden
# kuruldu; oyun kamerasından (8–14 m) okunacak iri ayrıntılar:
#   duvar   30 dikey tahta (krem / şeftali, boyası kenarlardan dökülmüş); üç tahta sonradan değiştirilmiş (biri ham, biri boyasız gri,
#           biri nane yeşili); sağda çatlağın üstüne çivilenmiş çapraz yama tahtası (paslı çiviler, pas akıntısı); saçak altında tuz
#           izleri, dipte toprak sıçraması ve arka yüzde yosun; dipte taş temel (arkadakiler yosunlu) + kum birikintisi.
#   kapı    turkuaz tahtalar (boya dökük), Z kuşak, iki paslı demir menteşe, pirinç topuz, krem kasa + kemer; önde taş eşik.
#   tabela  kapı üstünde iki iple asılı oyun kolu biçimli tabela (sarı çerçeve, mercan zemin, beyaz yön tuşu + dört renkli düğme).
#   pencere sağ önde yuvarlak lomboz (turkuaz çerçeve, haç kayıt, cam parıltısı) + üstünde güneşte solmuş dilli tente.
#   çatı    tek tek pul kiremit (ucu kalkık, sıra sıra gölge): mor/leylak bantlar, tepede turkuaz; tepeye doğru güneş solması,
#           arka alt sıralarda yosunlu kiremit + yosun yastıkları, birkaç solmuş / yamuk / eksik kiremit, iki yamalı (hardal, turkuaz);
#           paslı soba borusu + şapkası; tepede yıldızlı direk (iple sarılı).
#   süs     saçak boyunca flama (birkaçı solmuş, biri eksik, biri yırtık).
#   oyuncak önde büyük zar (boyası aşınmış) ve deniz topu (solmuş dilimler), solda duvara yaslı uçurtma (kuyruğunda fiyonklar),
#           sağda duvara yaslı çember, sağ yanda kapağı açık oyuncak sandığı (içinde renkli küpler).
# Oyun modeli: ada_eskitme.bake (bld_kit). Kullanım: python -I bld/b_game_hut.py -- <çıktı> [b_game_hut] [--draft <png> [yaw]]
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import ada_eskitme as E
import bpy, bmesh
from mathutils import Vector as V, Matrix, noise as mnoise
import kit
from kit import blob, rbox, cyl, tube
import assets_v3 as A
import assets_town as AT
from assets_v3 import m_wood, m_flat, m_tile, _shade

NAME = 'b_game_hut'
CAP = 15000
RAD, H = 1.0, 1.2
RB, RH = RAD + 0.32, 1.2                       # çatı taban yarıçapı, yüksekliği (eskisiyle aynı)
DOOR = 0.32                                    # kapı boşluğu yarı açısı (rad)
TEAL = '#2fa3a0'


def frame_at(a, z, r=RAD + 0.026):
    """Duvar yüzeyinde yerel çerçeve: (nokta, dışa normal, teğet (sola), yukarı)."""
    n = V((math.cos(a), math.sin(a), 0)); t = V((-math.sin(a), math.cos(a), 0))
    return V((math.cos(a) * r, math.sin(a) * r, z)), n, t, V((0, 0, 1))


def place(objs, origin, n, t):
    """Yerelde (x = teğet, y = −normal yani duvardan dışa −y, z yukarı) kurulmuş parçaları duvara taşır."""
    bpy.context.view_layer.update()
    M = Matrix((t, -n, V((0, 0, 1)))).transposed().to_4x4(); M.translation = origin
    for o in objs: o.matrix_world = M @ o.matrix_world


def walls():
    R = random.Random(17)
    gz = (-H / 2 - 0.02, -H / 2 + 0.22)              # m_wood dip kiri nesne z'sinde (tahta merkezi orijin)
    cream = m_wood('#b98a5a', 'ghw1', paint='#f8e0b0', age=1.1, grime=gz)
    peach = m_wood('#b98a5a', 'ghw2', paint='#fcbf8e', age=1.1, grime=gz)
    mint = m_wood('#a8845c', 'ghw3', paint='#93d6c0', age=0.8, grime=gz)
    raw = m_wood('#b0875a', 'ghraw', age=0.7, grime=gz)
    grey = m_wood('#9a8a76', 'ghgrey', age=1.4, grime=gz)
    for m in (cream, peach, mint, raw, grey):
        E.layer(m, E.salt(H - 0.06, 0.55, 0.4)); E.layer(m, E.grime(0.18, 0.5)); E.layer(m, E.base_moss(0.24, 0.85, back=(0.05, 0.9)))
    special = {25: raw, 10: mint, 4: grey}           # sonradan değiştirilmiş tahtalar (sağ ön, arka sol, arka sağ)
    n = 30
    for k in range(n):
        a = k / n * 2 * math.pi
        if abs(((a - 3 * math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < DOOR: continue
        m = special.get(k, (cream, peach)[k % 2])
        hj = R.uniform(-0.03, 0.03) + (0.02 if k in special else 0)
        AT.plank('wall', (math.cos(a) * RAD, math.sin(a) * RAD, (H + hj) / 2), (0.05, 0.22, H + hj), m, rot=(0, 0, math.degrees(a)), seed=k, amt=0.006)
    cyl('inner', (0, 0, H / 2), RAD - 0.04, H, m_wood('#4a2f1c', 'ghin'), verts=24)
    DK = m_wood('#7a5232', 'ghdark')
    bpy.ops.mesh.primitive_torus_add(major_radius=RAD + 0.03, minor_radius=0.04, location=(0, 0, H - 0.05), major_segments=40, minor_segments=6)
    bpy.context.object.name = 'topring'; bpy.context.object.data.materials.append(DK)
    # sağda çatlak üstüne çivilenmiş çapraz yama tahtası
    p, nn, t, up = frame_at(math.radians(8), 0.62, RAD + 0.034)
    pb = AT.plank('patchboard', (0, 0, 0), (0.06, 0.02, 0.36), m_wood('#a07a52', 'patchb', age=1.2), rot=(0, 28, 0), seed=91, amt=0.004)
    place([pb], p, nn, t)
    for s in (-1, 1):
        q = p + (t * math.sin(math.radians(28)) * -s + up * math.cos(math.radians(28)) * s) * 0.14
        AT.nail(tuple(q + nn * 0.012), tuple(nn))
    # taş temel (kapı önü hariç), arkadakiler yosunlu
    STN = A.m_rock(moss_th=(0.85, 1.1), name='footstone'); STN2 = A.m_rock(moss_th=(0.45, 0.75), name='footstone_moss')
    for k in range(28):
        a = k / 28 * 2 * math.pi + R.uniform(-0.05, 0.05)
        if abs(((a - 3 * math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < DOOR + 0.05: continue
        r = RAD + 0.05 + R.uniform(-0.01, 0.02); s = R.uniform(0.07, 0.1)
        o = AT.rock((math.cos(a) * r, math.sin(a) * r, s * 0.25), s, STN2 if math.sin(a) > 0.2 else STN, k * 3 + 1, sq=(1.25, 1.0, 0.75), sub=2, amt=0.22)
        o.name = 'footstone'
    E.sand_ring(0, 0, lambda a: RAD + 0.1, 0.12, 0.035, seed=7, a0=-math.pi / 2 + DOOR + 0.12, a1=-math.pi / 2 + 2 * math.pi - DOOR - 0.12, n=72)
    for k, a in enumerate((math.radians(60), math.radians(105), math.radians(150), math.radians(20))):
        E.moss_clump((math.cos(a) * (RAD + 0.1), math.sin(a) * (RAD + 0.1), 0.03), 0.05, seed=20 + k, n=2)


def door():
    DR = m_wood('#9a7048', 'ghdoor', paint=TEAL, age=1.45, grime=(-0.45, -0.25))
    E.layer(DR, E.grime(0.2, 0.55))
    y0 = -RAD + 0.02
    for k in range(3): AT.plank('door', (-0.13 + k * 0.13, y0, 0.45), (0.125, 0.05, 0.86), DR, seed=k + 30, amt=0.005)
    blob('darch', (0, y0, 0.88), (0.2, 0.05, 0.12), DR, sub=1, seg=12)
    BR = m_wood('#b08a5e', 'ghbrace', age=1.1, grime=(-1.0, -0.9))
    for z in (0.2, 0.68): AT.plank('dbatten', (0, y0 - 0.035, z), (0.36, 0.022, 0.07), BR, seed=int(z * 50), amt=0.003)
    AT.plank('dbrace', (0, y0 - 0.035, 0.44), (0.4, 0.02, 0.06), BR, rot=(0, -50, 0), seed=37, amt=0.003)
    for z in (0.2, 0.68):
        E.rust_strap((-0.1, y0 - 0.05, z), (0, -1, 0), 0.2, w=0.035)
    blob('knob', (0.13, y0 - 0.06, 0.45), (0.026, 0.022, 0.026), m_flat('#e9b23c', 0.12, 10, 'brass'), sub=1, seg=10)
    rbox('keyplate', (0.13, y0 - 0.048, 0.4), (0.035, 0.006, 0.06), AT.m_metal('#8a6a3a', '#7a5a2e', 'plate'), bevel=0.004)
    # kasa + kemer (kapı ile duvar arasındaki boşluk kapanır)
    FR = m_wood('#a8845c', 'ghframe', paint='#f3e3c0', age=1.3, grime=(-0.52, -0.3))
    for s in (-1, 1):
        AT.plank('dframe', (s * 0.3, -RAD + 0.045, 0.5), (0.17, 0.06, 1.0), FR, seed=40 + s, amt=0.004)
    AT.plank('dlintel', (0, -RAD + 0.035, 1.02), (0.78, 0.06, 0.08), FR, seed=44, amt=0.004)
    o = AT.rock((0.0, -RAD - 0.14, 0.012), 0.2, A.m_rock(moss_th=(0.9, 1.2), name='stepstone'), 5, sq=(1.35, 0.6, 0.18), sub=2, amt=0.08)
    o.name = 'doorstep'


def sign():
    """Oyun kolu tabelası: kapının solunda direğe çakılı (kapı üstü saçağın gölgesinde kalıyordu, oyun kamerası görmüyordu).
    Sarı çerçeveli mercan levha, beyaz yön tuşu + dört renkli düğme; levha hafif yamuk, direk dibinde kum + ot."""
    before = set(bpy.context.scene.objects.keys())
    def rrect(w, h, r, n=4):
        pts = []
        for (cx, cz, a0) in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
            for k in range(n + 1):
                a = math.radians(a0 + k * 90 / n); pts.append((cx + math.cos(a) * r, cz + math.sin(a) * r))
        return pts
    YF = m_wood('#b98a5a', 'signframe', paint='#f4c548', age=1.2, grime=(-1, -0.9))
    CO = m_wood('#b98a5a', 'signface', paint='#ff7a59', age=1.0, grime=(-1, -0.9))
    AT.prism('signboard', rrect(0.46, 0.21, 0.06), 0.035, YF, loc=(0, 0, 0), bevel=0.008)
    AT.prism('signface', rrect(0.39, 0.145, 0.045), 0.012, CO, loc=(0, -0.022, 0), bevel=0.004)
    W = m_flat('#fff6e6', 0.05, 8, 'ic_w')
    for (w, h) in ((0.1, 0.032), (0.032, 0.1)):
        rbox('dpad', (-0.1, -0.031, 0), (w, 0.012, h), W, bevel=0.004)
    for (dx, dz, c) in ((0.1, 0.04, '#f4c548'), (0.142, 0.0, '#36aab2'), (0.1, -0.04, '#86c25a'), (0.058, 0.0, '#ee7a9c')):
        cyl('gbtn', (dx, -0.03, dz), 0.02, 0.014, m_flat(c, 0.06, 8, 'btn' + c), rot=(90, 0, 0), verts=12, bevel=0.003)
    bpy.context.view_layer.update()
    M = Matrix.Translation((-0.47, -1.3, 0.66)) @ Matrix.Rotation(math.radians(12), 4, 'Z') @ Matrix.Rotation(math.radians(-4), 4, 'Y')
    for o in [o for o in bpy.context.scene.objects if o.name not in before]: o.matrix_world = M @ o.matrix_world
    PW = m_wood('#8a6440', 'signpost')
    AT.post('signpost', (-0.47 - 0.0, -1.3 + 0.035, -0.04), (-0.47, -1.3 + 0.035, 0.74), 0.028, PW, seed=3)
    for z in (0.6, 0.72): AT.nail((-0.47, -1.3 - 0.02, z), (0, -1, 0))
    E.sand_mound(-0.47, -1.265, 0.08, 0.07, 0.02, 12, name='postmound', n=12, rings=2)


def window():
    """Sağ önde yuvarlak lomboz + güneşte solmuş dilli tente."""
    before = set(bpy.context.scene.objects.keys())
    FR = m_wood('#9a7048', 'winframe', paint=TEAL, age=1.2)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.03, location=(0, -0.012, 0), rotation=(math.radians(90), 0, 0), major_segments=20, minor_segments=6)
    o = bpy.context.object; o.name = 'winframe'; o.data.materials.append(FR)
    def mglass(nt, bsdf):
        G = A._G(nt); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(G.obj(), sp.inputs[0])
        col = G.mix(G.rng(sp.outputs['Z'], -0.1, 0.1), '#173c48', '#2f6d78')
        band = G.math('MULTIPLY', G.rng(G.math('ADD', sp.outputs['X'], sp.outputs['Z']), 0.02, 0.05), G.rng(G.math('ADD', sp.outputs['X'], sp.outputs['Z']), 0.11, 0.08))
        col = G.mix(G.math('MULTIPLY', band, 0.8), col, '#d9f2f0')
        nt.links.new(col, bsdf.inputs['Base Color'])
    cyl('winglass', (0, 0.0, 0), 0.1, 0.01, kit.nodes_mat('winglass', mglass), rot=(90, 0, 0), verts=20, bevel=0)
    for rot in (0, 90):
        rbox('winbar', (0, -0.012, 0), (0.2, 0.012, 0.018), FR, rot=(0, rot, 0), bevel=0.003)
    AW = E.m_canvas('#e5504b', '#fbecd0', stripes=2.5, name='winawning', mud=0, fade=0.45)
    E.layer(AW, E.sunfade(0.3, tint='#fff2dc'))
    verts = []; faces = []; uvs = []
    nx, ny = 8, 3
    for iy in range(ny + 1):
        t = iy / ny
        for ix in range(nx + 1):
            u = ix / nx; x = -0.18 + 0.36 * u
            verts.append((x * (1 + 0.1 * t), -0.005 - 0.16 * t, 0.2 - 0.08 * t - 0.012 * math.sin(math.pi * u) * math.sin(math.pi * t))); uvs.append((u, t * 0.3))
    for iy in range(ny):
        for ix in range(nx):
            a_ = iy * (nx + 1) + ix; faces.append((a_, a_ + 1, a_ + nx + 2, a_ + nx + 1))
    base = len(verts)
    for ix in range(nx + 1):
        u = ix / nx; x = -0.18 * 1.1 + 0.36 * 1.1 * u; q = (u * 4) % 1.0
        verts.append((x, -0.165, 0.12)); uvs.append((u, 0.3))
        verts.append((x, -0.168, 0.12 - 0.045 * math.sin(math.pi * q) ** 0.8 - 0.008)); uvs.append((u, 0.36))
    for ix in range(nx):
        a_ = base + ix * 2; faces.append((a_, a_ + 2, a_ + 3, a_ + 1))
    E.mesh_obj('winawning', verts, faces, [AW], uvs=[[uvs[i] for i in f] for f in faces], ds=True)
    for s in (-1, 1):
        tube('winrod', [(s * 0.17, -0.005, 0.12), (s * 0.19, -0.16, 0.13)], [0.006, 0.006], AT.m_metal('#4a4650', '#b0663a', 'rodm'), res=1)
    p, n, t, up = frame_at(math.radians(-35), 0.7)
    place([o for o in bpy.context.scene.objects if o.name not in before], p, n, t)


def roof():
    """Pul kiremitler: üstü bir üst sıranın altında, alt ucu yarım yuvarlak ve hafif kalkık (sıra gölgesi okunur)."""
    R = random.Random(29)
    core = AT.lathe('roofcore', [(RB - 0.02, H + 0.02), (RB * 0.5, H + RH * 0.55), (0.05, H + RH), (0.001, H + RH + 0.01)], m_tile('#3f2c78', 'ghcore'), segs=32)
    def tmat(hexc, nm, fade=0.0, moss=False):
        m = m_tile(hexc, nm)
        E.layer(m, E.sunfade(0.22 + fade, H + 0.4, H + RH, tint='#efe6ff'))
        if moss:
            E.layer(m, lambda G, c: G.mix(G.rng(G.noise(G.obj(), 9, 4), 0.42, 0.6, 0, 0.85), c, G.mix(G.rng(G.noise(G.obj(), 30, 2), 0.4, 0.6), '#4d7a2c', '#86a843')))
        return m
    PUR = tmat('#7656d0', 'ght_pur'); LIL = tmat('#9878e6', 'ght_lil'); TL = tmat('#2fa3a0', 'ght_teal')
    FPUR = tmat('#9a86d8', 'ght_pur_f', 0.2); FLIL = tmat('#b4a2ea', 'ght_lil_f', 0.2)
    MPUR = tmat('#7656d0', 'ght_pur_m', moss=True); MLIL = tmat('#9878e6', 'ght_lil_m', moss=True)
    PATCH = [tmat('#f2b84a', 'ght_mustard'), tmat('#36aab2', 'ght_teal2')]
    phi = math.atan2(RH, RB)
    rows = 8
    W, L, TH = 0.21, 0.27, 0.016
    # dış hat (yerel x: teğet, s: yamaç aşağı): üst kenar düz, alt yarım daire
    outline = [(-W / 2, 0.0), (W / 2, 0.0), (W / 2, L - W / 2)] + [(W / 2 * math.cos(b), L - W / 2 + W / 2 * math.sin(b)) for b in [k * math.pi / 6 for k in range(1, 6)]] + [(-W / 2, L - W / 2)]
    missing = {(3, 0.62), (5, 0.3), (2, 0.15)}            # (sıra, açı oranı): eksik kiremit (ön yüzde görünür)
    special = {(4, 0.7): PATCH[0], (1, 0.82): PATCH[1], (6, 0.55): PATCH[0]}
    for r in range(rows):
        k = (r + 0.5) / rows
        rr = RB * (1 - k) + 0.06; z = H + RH * k + 0.03
        cnt = max(5, int(2 * math.pi * rr / 0.19))
        for i in range(cnt):
            a = i / cnt * 2 * math.pi + (math.pi / cnt if r % 2 else 0)
            fa = ((a + math.pi / 2) / (2 * math.pi)) % 1.0         # 0 = ön (−Y)
            if any(rw == r and abs(fa - f) < 0.5 / cnt for rw, f in missing): continue
            t = V((-math.sin(a), math.cos(a), 0)); sdn = V((math.cos(a) * math.cos(phi), math.sin(a) * math.cos(phi), -math.sin(phi)))
            nrm = sdn.cross(t).normalized()
            if nrm.z < 0: nrm = -nrm
            back = math.sin(a) > 0.25
            if r == rows - 1: M = TL
            else:
                M = (PUR, LIL)[(r // 2) % 2]
                x = R.random()
                if back and r < 3 and x < 0.45: M = (MPUR, MLIL)[(r // 2) % 2]
                elif x < 0.14: M = (FPUR, FLIL)[(r // 2) % 2]
            for (rw, f), pm in special.items():
                if rw == r and abs(fa - f) < 0.5 / cnt: M = pm
            yaw_j = math.radians(R.uniform(-4, 4) + (9 if R.random() < 0.06 else 0)); lift = R.uniform(0.012, 0.022) + (0.02 if R.random() < 0.05 else 0)
            tt = Matrix.Rotation(yaw_j, 3, nrm) @ t; ss = Matrix.Rotation(yaw_j, 3, nrm) @ sdn
            top = V((math.cos(a) * rr, math.sin(a) * rr, z)) + nrm * 0.014 - ss * 0.13
            verts = []
            for (x_, s_) in outline:
                bow = 0.008 * (1 - (2 * x_ / W) ** 2)
                c = top + tt * x_ + ss * s_ + nrm * (bow + lift * (s_ / L) ** 2)
                verts += [c, c - nrm * TH]
            nO = len(outline)
            faces = [tuple(2 * q for q in range(nO)), tuple(2 * q + 1 for q in reversed(range(nO)))]
            for q in range(nO):
                q2 = (q + 1) % nO; faces.append((2 * q, 2 * q + 1, 2 * q2 + 1, 2 * q2))
            o = E.mesh_obj('tile', verts, faces, [M], smooth_=False)
            bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    # soba borusu (arka sağ), paslı, şapkalı
    I = AT.m_metal('#55515c', '#b0663a', 'pipem', age=1.4)
    a = math.radians(55); rr = 0.62; x, y = math.cos(a) * rr, math.sin(a) * rr
    cyl('pipe', (x, y, 2.0), 0.05, 0.5, I, verts=12, bevel=0.004)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.053, minor_radius=0.008, location=(x, y, 2.12), major_segments=12, minor_segments=4)
    bpy.context.object.name = 'pipering'; bpy.context.object.data.materials.append(I)
    AT.lathe('pipecap', [(0.001, 2.27), (0.1, 2.3), (0.11, 2.31), (0.02, 2.37), (0.001, 2.372)], I, segs=12).location = (x, y, 0)
    for q in range(3):
        b = q * 2 * math.pi / 3
        rbox('capleg', (x + math.cos(b) * 0.045, y + math.sin(b) * 0.045, 2.285), (0.008, 0.008, 0.05), I, bevel=0)
    # tepe: yıldızlı direk + ip sargısı
    DK = m_wood('#7a5232', 'starpole')
    tube('pole', [(0, 0, H + 1.15), (0, 0, H + 1.65)], [0.022, 0.017], DK, res=2)
    for z in (H + 1.24, H + 1.27):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.024, minor_radius=0.007, location=(0, 0, z), major_segments=10, minor_segments=4)
        bpy.context.object.name = 'polerope'; bpy.context.object.data.materials.append(AT.m_rope())
    pts = []
    for k in range(10):
        b_ = math.pi / 2 + k * math.pi / 5; r_ = 0.14 if k % 2 == 0 else 0.065
        pts.append((math.cos(b_) * r_, math.sin(b_) * r_))
    AT.prism('star', pts, 0.04, m_wood('#c89a5a', 'starm', paint='#ffc93a', age=0.9), loc=(0, 0, H + 1.73), rot=(0, 0, -25), bevel=0.012)


def eave_bunting():
    """Saçak flaması: tek ip (16 sarkık yay), her yayda iki bayrak; birkaçı solmuş, biri eksik, biri yırtık."""
    R = random.Random(5)
    pts = []; flags = []
    n = 16; r0 = RAD + 0.31
    for i in range(n):
        a0 = i / n * 2 * math.pi + 0.1; a1 = (i + 1) / n * 2 * math.pi + 0.1
        for q in range(4):
            t = q / 4; a = a0 + (a1 - a0) * t
            pts.append((math.cos(a) * r0, math.sin(a) * r0, H + 0.0 - 0.09 * 4 * t * (1 - t)))
    pts.append(pts[0])
    o = tube('buntrope', pts, [0.006] * len(pts), AT.m_rope('#e2c99a', 'buntr'), res=1); o.data.bevel_resolution = 0
    verts = []; faces = []; uvs = []; mi = []; mats = []; idx = {}
    for i in range(n):
        a0 = i / n * 2 * math.pi + 0.1; a1 = (i + 1) / n * 2 * math.pi + 0.1
        for q in range(2):
            if (i, q) in ((3, 1), (11, 0)): continue                       # eksik bayrak
            ta, tb = 0.12 + q * 0.42, 0.42 + q * 0.42
            def P(t):
                a = a0 + (a1 - a0) * t; return V((math.cos(a) * r0, math.sin(a) * r0, H - 0.09 * 4 * t * (1 - t)))
            pa, pb = P(ta), P(tb); mid = (pa + pb) / 2; side = V((math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0))
            Lf = 0.11 * R.uniform(0.95, 1.15)
            tip = mid + V((0, 0, -Lf)) + side * R.uniform(-0.03, 0.03)
            fold = mid + side * 0.008
            c = E.FLAG_COLORS[(i * 2 + q) % len(E.FLAG_COLORS)]; faded = R.random() < 0.35
            if (c, faded) not in idx: idx[(c, faded)] = len(mats); mats.append(E.m_flag(c, faded))
            b0 = len(verts)
            if (i, q) == (6, 0):                                           # yırtık uç
                verts += [pa, fold, pb, mid + (tip - mid) * 0.65 + side * 0.01, mid + (tip - mid) * 0.58 - (pb - pa).normalized() * 0.02]
                faces += [(b0, b0 + 1, b0 + 4), (b0 + 1, b0 + 2, b0 + 3), (b0 + 1, b0 + 3, b0 + 4)]
                uvs += [[(0, 1), (0.5, 1), (0.3, 0.3)], [(0.5, 1), (1, 1), (0.7, 0.3)], [(0.5, 1), (0.7, 0.3), (0.3, 0.3)]]; mi += [idx[(c, faded)]] * 3
            else:
                verts += [pa, fold, pb, tip]
                faces += [(b0, b0 + 1, b0 + 3), (b0 + 1, b0 + 2, b0 + 3)]
                uvs += [[(0, 1), (0.5, 1), (0.5, 0)], [(0.5, 1), (1, 1), (0.5, 0)]]; mi += [idx[(c, faded)]] * 2
    E.mesh_obj('buntflags', verts, faces, mats, uvs=uvs, mat_idx=mi, smooth_=False, ds=True)


def toys():
    R = random.Random(41)
    # zar (eski yerinde): aşınmış krem boya, koyu benekler, biraz gömülü ve eğik
    DM = m_wood('#c8a878', 'dicem', paint='#fbf2e2', age=0.9, grime=(-1, -0.9))
    E.layer(DM, E.grime(0.12, 0.5))
    D = rbox('dice', (0, 0, 0.19), (0.4, 0.4, 0.4), DM, bevel=0.07, seg=3)
    DOT = m_flat('#3a3550', 0.05, 6, 'dot')
    pips = [((-0.1, 0.1), (0.1, -0.1), (-0.1, -0.1), (0.1, 0.1)), ((0, 0), (-0.1, 0.1), (0.1, -0.1)), ((-0.1, 0.1), (0.1, -0.1))]
    dots = []
    for (u, v) in pips[0]: dots.append(blob('dot', (u, v, 0.392), (0.036, 0.036, 0.008), DOT, sub=0, seg=10))
    for (u, v) in pips[1]: dots.append(blob('dot', (u, -0.202, 0.19 + v), (0.036, 0.008, 0.036), DOT, sub=0, seg=10))
    for (u, v) in pips[2]: dots.append(blob('dot', (0.202, u, 0.19 + v), (0.008, 0.036, 0.036), DOT, sub=0, seg=10))
    bpy.context.view_layer.update()
    M = Matrix.Translation((0.75, -1.15, -0.02)) @ Matrix.Rotation(math.radians(25), 4, 'Z') @ Matrix.Rotation(math.radians(3), 4, 'X')
    for o in [D] + dots: o.matrix_world = M @ o.matrix_world
    # deniz topu (eski yerinde): solmuş dilimler
    BALL = AT.m_cloth('#ff7aa8', '#ffd447', stripes=3.0, name='ball', age=0.8)
    E.layer(BALL, E.sunfade(0.25, tint='#fff4e4'))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=10, radius=0.18, location=(-0.85, -1.05, 0.17))
    b = bpy.context.object; b.name = 'beachball'; b.data.materials.append(BALL); A.smooth(b)
    me = b.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0 * 2, co.z)
    b.rotation_euler = (math.radians(25), math.radians(-15), 0)
    blob('ballcap', (0, 0, 0.178), (0.035, 0.035, 0.008), m_flat('#fff6ea', 0.05, 8, 'ballcapm'), sub=0, seg=10).parent = b
    # uçurtma: solda duvara yaslı (yerel: x teğet, −y dışa)
    before = set(bpy.context.scene.objects.keys())
    KM = [m_flat(c, 0.08, 8, 'kite' + c) for c in ('#f2bf45', '#e5504b', '#36aab2', '#fbecd0')]
    top, bot, lft, rgt, ctr = V((0, 0, 0.62)), V((0, 0, 0.0)), V((-0.19, 0, 0.42)), V((0.19, 0, 0.42)), V((0, -0.025, 0.42))
    E.mesh_obj('kite', [top, rgt, bot, lft, ctr], [(0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)], KM, uvs=[[(0.5, 1), (0.5, 0.5), (1, 0.5)]] * 4, mat_idx=[0, 1, 2, 3], smooth_=False, ds=True)
    SK = m_wood('#b98a5a', 'kitestick')
    tube('kitestick', [(0, -0.008, 0.62), (0, -0.008, 0.0)], [0.007, 0.007], SK, res=1)
    tube('kitestick', [(-0.19, -0.008, 0.42), (0.19, -0.008, 0.42)], [0.006, 0.006], SK, res=1)
    tail = [(0, -0.01, 0.0), (0.04, -0.06, -0.0), (0.0, -0.14, 0.0), (0.06, -0.22, 0.0), (0.02, -0.3, 0.0)]
    tube('kitetail', [(x, y, 0.012) for x, y, _ in tail], [0.004] * 5, AT.m_rope('#f2ead8', 'kitestr'), res=2)
    for k, (x, y, _) in enumerate(tail[1:]):
        c = ('#e5504b', '#36aab2', '#f2bf45', '#ee7a9c')[k]
        for s in (-1, 1):
            E.mesh_obj('kitebow', [(x, y, 0.014), (x + s * 0.035, y + 0.02, 0.02), (x + s * 0.035, y - 0.02, 0.02)], [(0, 1, 2)], [m_flat(c, 0.06, 8, 'bow' + c)], uvs=[[(0, 0), (1, 0), (1, 1)]], smooth_=False, ds=True)
    p, n, t, up = frame_at(math.radians(-128), 0.0, RAD + 0.22)
    bpy.context.view_layer.update()
    lean = Matrix.Rotation(math.radians(-18), 4, 'X')                 # üstü duvara yaslı
    Mw = Matrix((t, -n, V((0, 0, 1)))).transposed().to_4x4(); Mw.translation = p
    for o in [o for o in bpy.context.scene.objects if o.name not in before]:
        if o.name.startswith(('kitetail', 'kitebow')): o.matrix_world = Mw @ o.matrix_world
        else: o.matrix_world = Mw @ lean @ o.matrix_world
    # çember: sağda duvara yaslı
    HM = AT.m_cloth('#ee7a9c', '#fbecd0', stripes=12.0, name='hoopm', age=0.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.25, minor_radius=0.016, location=(0, 0, 0), major_segments=28, minor_segments=6, rotation=(math.radians(90), 0, 0))
    hp = bpy.context.object; hp.name = 'hoop'; hp.data.materials.append(HM)
    me = hp.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, 0)
    p, n, t, up = frame_at(math.radians(-50), 0.0, RAD + 0.09)
    bpy.context.view_layer.update()
    Mw = Matrix((t, -n, V((0, 0, 1)))).transposed().to_4x4(); Mw.translation = p
    hp.matrix_world = Mw @ Matrix.Translation((0, 0, 0.24)) @ Matrix.Rotation(math.radians(-16), 4, 'X') @ hp.matrix_world
    # oyuncak sandığı: sağ yanda, kapağı açık, içinde renkli küpler
    before = set(bpy.context.scene.objects.keys())
    CB = m_wood('#9a7048', 'chestw', paint='#36aab2', age=1.2, grime=(-1, -0.9)); CY = m_wood('#9a7048', 'chesty', paint='#f2bf45', age=1.1, grime=(-1, -0.9))
    E.layer(CB, E.grime(0.12, 0.5))
    rbox('chest', (0, 0, 0.11), (0.36, 0.24, 0.22), CB, bevel=0.012)
    for z in (0.05, 0.17): rbox('chestband', (0, 0, z), (0.372, 0.252, 0.035), CY, bevel=0.006)
    lid = rbox('chestlid', (0, 0.12, 0.33), (0.37, 0.025, 0.24), CB, rot=(-12, 0, 0), bevel=0.01)
    I = AT.m_metal('#4a4650', '#b0663a', 'chestm')
    for s in (-1, 1):
        rbox('chestcorner', (s * 0.18, -0.12, 0.11), (0.03, 0.03, 0.23), I, bevel=0.004)
    rbox('chestlock', (0, -0.126, 0.18), (0.05, 0.012, 0.05), m_flat('#e9b23c', 0.1, 8, 'brass2'), bevel=0.004)
    for k, (dx, dy, c, rz) in enumerate(((-0.08, -0.03, '#e5504b', 12), (0.06, 0.02, '#86c25a', -20), (0.0, -0.06, '#9a7ee0', 35))):
        rbox('toyblock', (dx, dy, 0.235 + 0.01 * k), (0.08, 0.08, 0.08), m_flat(c, 0.08, 8, 'blk' + c), rot=(0, 8 * k, rz), bevel=0.012)
    bpy.context.view_layer.update()
    a = math.radians(-14); M = Matrix.Translation((math.cos(a) * 1.25, math.sin(a) * 1.25, 0)) @ Matrix.Rotation(a + math.pi / 2, 4, 'Z')
    for o in [o for o in bpy.context.scene.objects if o.name not in before]: o.matrix_world = M @ o.matrix_world


def build():
    walls(); door(); sign(); window(); roof(); eave_bunting(); toys()
    before = set(bpy.context.scene.objects.keys())
    AT.dress(1.55, 51, n_tufts=9, flowers=5, pebbles=3, bushes=[(-1.2, 0.5), (1.15, 0.6), (-0.4, 1.2)],
             exclude=lambda x, y: math.hypot(x, y) < 1.2 or (abs(x) < 1.1 and -1.4 < y < -0.9))
    a = math.radians(-14); cx, cy = math.cos(a) * 1.25, math.sin(a) * 1.25
    print('silinen dip süsü', E.clear_area(before, lambda x, y: math.hypot(x - cx, y - cy) < 0.3), flush=True)


DECIM = [
    (r'^wall$', 0.055), (r'^(door|dframe|dlintel|dbatten|dbrace|patchboard)$', 0.15), (r'^footstone$', 0.35), (r'^doorstep$', 0.25),
    (r'^mossclump$', 0.12), (r'^(pet|fc)$', 0.4), (r'^stem$', 0.4), (r'^Icosphere$', 0.3), (r'^lush$', 0.5), (r'^rosette$', 0.5),
    (r'^(darch|knob|beachball)$', 0.35), (r'^(nail|streak)$', 0.3), (r'^(topring)$', 0.4), (r'^(inner)$', 0.4),
    (r'^(signboard|signface)$', 0.5), (r'^(gbtn|dpad)$', 0.4), (r'^(signpost|winrod|kitestick|kitetail|polerope)$', 0.5), (r'^postmound$', 0.6),
    (r'^(winframe|hoop)$', 0.45), (r'^(pipering|pipecap|pipeflash|pipe)$', 0.6), (r'^(star)$', 0.5), (r'^(pole)$', 0.6),
    (r'^(dice)$', 0.35), (r'^dot$', 0.4), (r'^(chest|chestband|chestlid|chestcorner|toyblock|chestlock|keyplate|strap)$', 0.35),
    (r'^buntrope$', 0.6), (r'^(sanddrift)$', 0.7),
]
WEIGHTS = [
    (r'^(signboard|signface|dpad|gbtn)$', 2.2), (r'^(door|darch|dbatten|dbrace|knob|strap)$', 1.5), (r'^(winframe|winglass|winbar|winawning)$', 1.6),
    (r'^wall$', 1.1), (r'^tile$', 0.85), (r'^(dice|dot|beachball|kite|chest.*|toyblock|hoop)$', 1.2),
    (r'^(lush|rosette|sanddrift|footstone)$', 0.55), (r'^(inner|roofcore)$', 0.3),
]


if __name__ == '__main__':
    out, dr, yaw = E.args()
    kit.reset(); build(); hi = E.BK.prepare()
    print('taslak üçgen', E.BK.tri_count(hi), 'nesne', len(hi), flush=True)
    if dr:
        E.draft(dr, yaw)
    else:
        E.bake(out, NAME, hi, DECIM, WEIGHTS, CAP)
