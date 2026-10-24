# Festival Alanı oyun modeli (24 Ekim 2026; kullanıcı: "haritadaki bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Eski model (assets_town.c_festival) 6,5 bin üçgene küresel sadeleşip yalnız renk + AO pişiyordu: çadır düz koni, kumaş soluk lekeli,
# ipler ve kazıklar çizgi kadar. Burada aynı yerleşim (orijin, ön = −Y, boy ve yatay kapsam eskisiyle aynı) yeniden kuruldu ve oyun
# kamerasından (8–14 m) okunacak iri ayrıntılar eklendi:
#   çadır  16 kumaş paneli (şerit başına bir panel): duvar panelleri hafif şişkin, dipte etek; çatı panelleri dikişler arasında sarkık;
#          şerit başına ton farkı (birkaçı güneşte açılmış), dikiş çizgileri, dipte çamur sıçraması, saçak altından akıntı lekesi;
#          dikişli üç yama (hardal, turkuaz puantiyeli, leylak); içeride koyu astar + taban + kilim (kapıdan bakınca içi karanlık);
#          kapı = ön panel, iki yanda rulo yapılıp iple bağlanmış kanat; fisto saçak (hardal, turuncu biye) + halat şerit + ponpon;
#          tepede yaka, direk, altın top, çatal flama; duvar dibinde kum birikintisi ve kazıklı etek ilmekleri.
#   gergi  dört gergi ipi + solmuş/eksik/yırtık bayraklar, tahta kazık (eğik, başlıklı, dibi kum tümseği), kazığa dolanmış ip + püskül.
#   giriş  iki fener direği (kafesli sıcak fener, metal başlık), aralarında sarkık flama, önde talaşlı kum.
#   gişe   sağda küçük bilet gişesi: turkuaz boyası dökülmüş tahta gövde, tezgâh, çizgili tente, bilet biçimli tabela + yıldız,
#          bilet rulosu, zil; arka direğe bağlı üç balon.
#   sol    fıçı (içinde lobut) + açık sandık (içinde renkli toplar).
# Oyun modeli: ada_eskitme.bake (bld_kit: aynı ağ, yalnız eğri parçalar kendi içinde sadeleşir; renk × AO + normal haritası).
# Kullanım: python -I bld/b_festival.py -- <çıktı> [b_festival] [--draft <png> [yaw]]
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import ada_eskitme as E
import bpy, bmesh
from mathutils import Vector as V, Matrix, noise as mnoise
from mathutils.bvhtree import BVHTree
import kit
from kit import blob, rbox, cyl, tube
import assets_v3 as A
import assets_town as AT
from assets_v3 import m_wood, m_flat, _shade

NAME = 'b_festival'
CAP = 15000
RAD, H = 1.1, 1.0          # duvar (köşe) yarıçapı, saçak yüksekliği (eskisiyle aynı)
NP, SUB = 16, 6            # kumaş paneli sayısı, panel başına sütun
NA = NP * SUB
A0 = -math.pi / 2 - math.pi / NP          # panel 0 = kapı (−Y merkezli)
RE, RH = RAD + 0.15, 1.15                 # çatı saçak yarıçapı, çatı yüksekliği
RED, CREAM, MUSTARD, TEAL = '#e5504b', '#f8e6c4', '#f1b83e', '#33a8b0'
SAND_Y = '#f8d98a'          # duvar şeridi: eski çadırdaki gibi sıcak sarı (krem beyaz göz alıyordu)


def ang(i):
    return A0 + i / NA * 2 * math.pi


def wall_r(a, z):
    """16 köşeli duvar: dikişler köşe, panel ortası hafif dışa şişkin; ortada bel, dipte etek."""
    k = ((a - A0) / (2 * math.pi / NP)) % 1.0
    poly = RAD * math.cos(math.pi / NP) / math.cos((k - 0.5) * 2 * math.pi / NP)
    zz = min(z, H)
    bulge = 0.016 * math.sin(math.pi * k) * math.sin(math.pi * zz / H)
    waist = 1 - 0.03 * math.sin(math.pi * zz / H)
    flare = 0.04 * max(0.0, 1 - z / 0.18) ** 2
    r = poly * waist + bulge + flare
    if z > H: r -= (z - H) * 0.25
    return r


def roof_pt(i, t):
    a = ang(i); k = (i % SUB) / SUB
    r = RE * (1 - t) ** 1.15 + 0.001
    z = H + RH * (1 - (1 - t) ** 1.35)
    s = math.sin(math.pi * k) * math.sin(math.pi * min(1.0, t * 1.1)) ** 0.8
    z -= 0.052 * s; r -= 0.016 * s
    return V((math.cos(a) * r, math.sin(a) * r, z))


def tent():
    """Duvar + çatı (ayrı nesneler: doku önemi ayrı), astar, taban, kilim, saçak, yaka."""
    CW = E.m_canvas(RED, SAND_Y, stripes=NP / 2, name='canvas_wall', mud=0.2, drip=H - 0.02, fade=0.25)
    CR = E.m_canvas(RED, CREAM, stripes=NP / 2, name='canvas_roof', mud=0, fade=0.35, bleach=(H + 0.35, H + RH, 0.55), stain=(H, H + 0.3))
    # duvar (kapı paneli = panel 0 boş)
    zs = [0.0, 0.06, 0.16, 0.32, 0.5, 0.68, 0.84, H, H + 0.12, H + 0.21]
    verts = []; faces = []; uvs = []
    for i in range(NA + 1):
        a = ang(i)
        for z in zs:
            r = wall_r(a, z); verts.append((math.cos(a) * r, math.sin(a) * r, z))
    nz = len(zs)
    for i in range(SUB, NA):
        for j in range(nz - 1):
            a_, b_ = i * nz + j, (i + 1) * nz + j
            faces.append((a_, b_, b_ + 1, a_ + 1))
            uvs.append([(i / NA, zs[j]), ((i + 1) / NA, zs[j]), ((i + 1) / NA, zs[j + 1]), (i / NA, zs[j + 1])])
    wall = E.mesh_obj('tentwall', verts, faces, [CW], uvs=uvs)
    # çatı
    ts = [0.0, 0.06, 0.14, 0.24, 0.35, 0.47, 0.6, 0.72, 0.83, 0.92, 0.965]
    verts = []; faces = []; uvs = []
    for i in range(NA + 1):
        for t in ts: verts.append(tuple(roof_pt(i, t)))
    nt = len(ts)
    for i in range(NA):
        for j in range(nt - 1):
            a_, b_ = i * nt + j, (i + 1) * nt + j
            faces.append((a_, b_, b_ + 1, a_ + 1))
            uvs.append([(i / NA, ts[j] * 2), ((i + 1) / NA, ts[j] * 2), ((i + 1) / NA, ts[j + 1] * 2), (i / NA, ts[j + 1] * 2)])
    roof = E.mesh_obj('tentroof', verts, faces, [CR], uvs=uvs)
    # iç astar: kapıdan bakınca içi gölgeli kumaş (arka yüz oyunda çizilmez → dış duvarın arkası görünmesin)
    LN = m_flat('#4a2627', 0.1, 6, 'liner')
    n = 24; verts = []; faces = []
    for k in range(n):
        a = k / n * 2 * math.pi
        verts += [(math.cos(a) * 0.99, math.sin(a) * 0.99, 0.02), (math.cos(a) * 0.99, math.sin(a) * 0.99, H + 0.14)]
    top = len(verts); verts.append((0, 0, H + 1.0))
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((2 * k, 2 * k + 1, 2 * k2 + 1, 2 * k2))
        faces.append((2 * k + 1, top, 2 * k2 + 1))
    E.mesh_obj('liner', verts, faces, [LN], smooth_=True)
    cyl('tfloor', (0, 0, 0.015), 0.98, 0.03, m_wood('#7d5634', 'tentfloor'), verts=24)
    RUG = AT.m_cloth('#36a3ab', '#f2c14e', stripes=5.0, name='rug', age=0.5)
    rug = cyl('rug', (0, -0.15, 0.033), 0.5, 0.006, RUG, verts=20, bevel=0)
    rug.scale = (1.0, 0.75, 1.0)
    # saçak fistosu: panel başına bir dil, hardal + turuncu biye (grain v: 0 alt kenar)
    VL = E.layer(m_flat(MUSTARD, 0.1, 10, 'valance'), lambda G, c: G.mix(G.rng(_v(G), 0.16, 0.1), c, '#d9792c'))
    verts = []; faces = []; uvs = []
    rows = 3
    for k in range(NP):
        base = len(verts)
        for c in range(SUB + 1):
            q = c / SUB; a = ang(k * SUB + c)
            zb = H - 0.05 - 0.125 * math.sin(math.pi * q) ** 0.8
            for rr in range(rows):
                t = rr / (rows - 1)
                z = zb + (H + 0.012 - zb) * t
                r = RE + 0.016 + 0.012 * (1 - t) * math.sin(math.pi * q)
                verts.append((math.cos(a) * r, math.sin(a) * r, z)); uvs.append((q, t))
        for c in range(SUB):
            for rr in range(rows - 1):
                a_, b_ = base + c * rows + rr, base + (c + 1) * rows + rr
                faces.append((a_, b_, b_ + 1, a_ + 1))
    fuv = [[uvs[i] for i in f] for f in faces]
    E.mesh_obj('valance', verts, faces, [VL], uvs=fuv, ds=True)
    # saçak halat şeridi + dikiş yerlerinde ponpon
    bpy.ops.mesh.primitive_torus_add(major_radius=RE + 0.02, minor_radius=0.013, location=(0, 0, H + 0.014), major_segments=72, minor_segments=5)
    tr = bpy.context.object; tr.name = 'trim'; tr.data.materials.append(AT.m_rope('#e8cf9a', 'trimrope'))
    PP = m_flat('#fff3e0', 0.1, 14, 'pompom')
    for k in range(NP):
        a = ang(k * SUB)
        blob('pompom', (math.cos(a) * (RE + 0.024), math.sin(a) * (RE + 0.024), H - 0.07), (0.025, 0.025, 0.027), PP, sub=0, seg=8)
    # tepe: yaka, direk, altın top, çatal flama
    G2 = m_flat('#f3c443', 0.08, 8, 'gold')
    AT.lathe('collar', [(0.12, H + RH - 0.11), (0.145, H + RH - 0.075), (0.13, H + RH - 0.04), (0.05, H + RH + 0.05), (0.001, H + RH + 0.06)], m_flat(MUSTARD, 0.1, 8, 'collarm'), segs=16)   # aşağıdan yukarı: normal dışa
    DK = m_wood('#7a5232', 'fpole')
    tube('pole', [(0, 0, H + 1.08), (0, 0, H + 1.65)], [0.026, 0.02], DK, res=2)
    blob('topball', (0, 0, H + 1.67), (0.042, 0.042, 0.042), G2, sub=1, seg=10)
    PN = E.m_flag(TEAL, False, 'pennant')
    pts = [(0.0, 0.0), (0.2, 0.012), (0.4, -0.02), (0.31, -0.11), (0.42, -0.2), (0.2, -0.205), (0.0, -0.22)]
    pn = AT.prism('pennant', pts, 0.012, PN, loc=(0.024, 0, H + 1.63), bevel=0.003)
    return wall, roof


def _v(G):
    sp = G.n.new('ShaderNodeSeparateXYZ'); G.l.new(kit.uv_node(G.nt).outputs[0], sp.inputs[0]); return sp.outputs['Y']


def patches(wall, roof):
    """Dikişli yamalar: yüzeye ışınla oturtulmuş 5×5 ızgara, 6 mm dışarıda + ince kalınlık (kenar gölgesi okunsun)."""
    dg = bpy.context.evaluated_depsgraph_get()
    pc = lambda k: A0 + (k + 0.5) * 2 * math.pi / NP          # panel ortası
    spec = [  # (yüzey, açı, z ya da t, en, boy, dönme°, malzeme) — yama bir panelin içinde (dikişe binmesin)
        (roof, pc(1), 0.3, 0.22, 0.25, 7, E.m_patch('#f0b63c', name='patch_mustard')),
        (wall, pc(2), 0.36, 0.22, 0.25, -6, E.m_patch('#36a3ab', name='patch_teal', dots='#fbecd0')),
        (roof, pc(11), 0.4, 0.17, 0.2, -9, E.m_patch('#9c80d8', name='patch_lilac')),
        (wall, pc(14), 0.58, 0.2, 0.22, 4, E.m_patch('#f3e3c0', '#8a5a3a', name='patch_cream')),
        (roof, pc(8), 0.24, 0.2, 0.22, 3, E.m_patch('#36a3ab', name='patch_teal2')),
    ]
    for surf, a, h, w, hh, rot, M in spec:
        bvh = BVHTree.FromObject(surf, dg)
        if surf is wall:
            r = wall_r(a, h); c = V((math.cos(a) * r, math.sin(a) * r, h))
        else:
            i = (a - A0) / (2 * math.pi) * NA; c = roof_pt(i, h)
        nrm = V((math.cos(a), math.sin(a), 0.0 if surf is wall else 0.75)).normalized()
        tx = V((-math.sin(a), math.cos(a), 0)); ty = nrm.cross(tx).normalized()
        R = Matrix.Rotation(math.radians(rot), 3, nrm); tx = R @ tx; ty = R @ ty
        verts = []; faces = []; uvs = []
        n = 5
        for iy in range(n):
            for ix in range(n):
                u, v = ix / (n - 1), iy / (n - 1)
                p = c + tx * (u - 0.5) * w + ty * (v - 0.5) * hh
                hit = bvh.ray_cast(p + nrm * 0.3, -nrm, 0.6)
                q = (hit[0] + hit[1] * 0.007) if hit[0] is not None else p
                verts.append(q); uvs.append((u, v))
        for iy in range(n - 1):
            for ix in range(n - 1):
                a_ = iy * n + ix; faces.append((a_, a_ + 1, a_ + n + 1, a_ + n))
        o = E.mesh_obj('patch', verts, faces, [M], uvs=[[uvs[i] for i in f] for f in faces])
        s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = 0.005; s.offset = -1


def flaps():
    """Kapı kanatları: iki yanda rulo yapılmış kumaş, ortadan iple bağlı (iple sıkılan yerde ince bel) + sarkan ip ucu."""
    FC = E.m_flag(RED, False, 'flapc'); RP = AT.m_rope()
    for s in (-1, 1):
        a = -math.pi / 2 + s * math.pi / NP
        r = wall_r(a, 0.5) + 0.035; x, y = math.cos(a) * r, math.sin(a) * r
        zs = [0.1, 0.3, 0.5, 0.56, 0.62, 0.8, 0.98]
        rr = [0.032, 0.052, 0.058, 0.04, 0.058, 0.055, 0.04]
        tube('flaproll', [(x + s * 0.004 * k, y, z) for k, z in enumerate(zs)], rr, FC, res=3)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.046, minor_radius=0.011, location=(x, y, 0.56), major_segments=14, minor_segments=5)
        bpy.context.object.name = 'flaptie'; bpy.context.object.data.materials.append(RP)
        tube('flaptail', [(x + s * 0.03, y - 0.03, 0.55), (x + s * 0.05, y - 0.05, 0.47), (x + s * 0.045, y - 0.06, 0.4)], [0.008, 0.007, 0.006], RP, res=2)


def guys():
    """Gergi ipleri (çapraz dört yön) + bayraklar + kazık + kazığa dolanmış ip + püskül."""
    RP = AT.m_rope('#d8b985', 'guyrope')
    PW = A.m_wood('#a27a4c', 'pegw')
    spec = [(-math.pi / 4, (), (2,)), (-3 * math.pi / 4, (1,), ()), (math.pi / 4, (), ()), (3 * math.pi / 4, (), (0,))]
    for k, (a, skip, torn) in enumerate(spec):
        p0 = V((math.cos(a) * (RE + 0.02), math.sin(a) * (RE + 0.02), H - 0.03))
        pe = V((math.cos(a) * 1.93, math.sin(a) * 1.93, 0.0))
        p1 = pe + V((0, 0, 0.075))
        E.bunting(tuple(p0), tuple(p1), 0.05, 4, seed=k * 3 + 1, size=0.085, skip=skip, torn=torn, rope=RP, thick=0.0095, name='guy')
        E.peg(pe.x, pe.y, (math.cos(a), math.sin(a)), h=0.22, w=0.042, m=PW, seed=k)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.008, location=(pe.x, pe.y, 0.06), major_segments=12, minor_segments=4)
        o = bpy.context.object; o.name = 'pegwrap'; o.data.materials.append(RP)
        o.rotation_euler = (0, math.radians(18), a)
        side = V((-math.sin(a), math.cos(a), 0))
        tl = [pe + V((0, 0, 0.055)) + side * 0.03, pe + side * 0.06 + V((0, 0, 0.03)), pe + side * 0.08 + V((math.cos(a) * 0.02, math.sin(a) * 0.02, 0.008))]
        tube('pegtail', [tuple(p) for p in tl], [0.008, 0.007, 0.006], RP, res=2)
        AT.frays([tuple(tl[-1])] * 2, 4, k * 11 + 5, length=0.035)


def lanterns():
    """Giriş: iki fener direği (kafesli sıcak fener, metal başlık), aralarında sarkık flama; direk dibinde kum + yosun."""
    DK = m_wood('#7a5232', 'lpostw'); I = AT.m_metal('#3f3b45', '#a8643a', 'lmetal')
    for s in (-1, 1):
        x, y = s * 0.55, -1.45
        AT.post('lpost', (x, y, -0.03), (x, y, 0.96), 0.036, DK, seed=s + 4)
        GL = AT.m_glow('#ffc65a', 'lamp' + str(s), lamp=(0, 0, 1.035, 0.07))   # nesne koordinatı (orijin direğin dibinde)
        cyl('lbase', (x, y, 0.965), 0.058, 0.02, I, verts=12)
        AT.lathe('lamp', [(0.001, 0.975), (0.046, 0.976), (0.058, 1.0), (0.062, 1.035), (0.056, 1.075), (0.04, 1.095), (0.001, 1.096)], GL, segs=12).location = (x, y, 0)
        for q in range(4):
            b = q * math.pi / 2 + math.pi / 4
            rbox('lbar', (x + math.cos(b) * 0.06, y + math.sin(b) * 0.06, 1.036), (0.008, 0.008, 0.12), I, rot=(0, 0, math.degrees(b)), bevel=0)
        AT.lathe('lcap', [(0.001, 1.094), (0.076, 1.094), (0.074, 1.104), (0.016, 1.148), (0.001, 1.15)], I, segs=12).location = (x, y, 0)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.014, minor_radius=0.004, location=(x, y, 1.158), major_segments=8, minor_segments=4, rotation=(math.radians(90), 0, 0))
        bpy.context.object.name = 'lring'; bpy.context.object.data.materials.append(I)
        E.sand_mound(x, y, 0.1, 0.09, 0.025, 30 + s, name='postmound', n=12, rings=2)
        E.moss_clump((x + 0.02, y + 0.035, 0.0), 0.035, seed=50 + s, n=1)
        AT.nail((x, y - 0.036, 0.42), (0, -1, 0))
    E.bunting((-0.55, -1.45, 0.93), (0.55, -1.45, 0.93), 0.11, 7, seed=4, size=0.072, skip=(), torn=(5,), thick=0.006, name='entr')


def booth(cx, cy, yaw):
    """Bilet gişesi (yerel: ön −Y): boyası dökülmüş tahta gövde, tezgâh, çizgili tente, bilet biçimli tabela + yıldız, bilet rulosu, zil,
    arka direğe bağlı üç balon."""
    before = set(bpy.context.scene.objects.keys())
    BW = m_wood('#5d3a22', 'bcorew')
    PT = m_wood('#9a7048', 'bteal', paint='#2f9fa6', age=1.3, grime=(-0.26, -0.12))
    PC = m_wood('#9a7048', 'bcream', paint='#f1dfb8', age=1.2, grime=(-0.26, -0.12))
    NW = m_wood('#b98a5a', 'bcounterw', grime=(-1, -0.9))
    E.layer(PT, E.grime(0.14, 0.5)); E.layer(PC, E.grime(0.14, 0.5))
    rbox('bcore', (0, 0, 0.24), (0.36, 0.22, 0.48), BW, bevel=0.01)
    for k in range(5):
        x = -0.144 + k * 0.072
        AT.plank('bplank', (x, -0.122, 0.24 + (0.005 if k % 2 else 0)), (0.068, 0.024, 0.48 - (0.02 if k == 3 else 0)), PC if k == 3 else PT, seed=70 + k, amt=0.004)
    for s in (-1, 1):
        AT.plank('bside', (s * 0.19, 0.0, 0.24), (0.024, 0.24, 0.48), PT, seed=80 + s, amt=0.004)
    AT.plank('bcounter', (0, -0.03, 0.5), (0.46, 0.33, 0.032), NW, seed=85, amt=0.004)
    I = AT.m_metal('#4a4650', '#b0663a', 'bnail')
    for (x, z) in ((-0.144, 0.08), (-0.144, 0.4), (0.144, 0.08), (0.144, 0.4), (0.0, 0.08), (0.0, 0.4)):
        AT.nail((x, -0.136, z), (0, -1, 0), I)
    for (x, y, h) in ((-0.17, -0.105, 0.42), (0.17, -0.105, 0.42), (-0.17, 0.095, 0.5), (0.17, 0.095, 0.5)):
        rbox('bpost', (x, y, 0.515 + h / 2), (0.028, 0.028, h), NW, bevel=0.005)
    AT.plank('bback', (0, 0.1, 0.76), (0.36, 0.018, 0.42), PC, seed=88, amt=0.003)
    star = []
    for k in range(10):
        b = math.pi / 2 + k * math.pi / 5; rr = 0.085 if k % 2 == 0 else 0.038
        star.append((math.cos(b) * rr, math.sin(b) * rr))
    AT.prism('bstar', star, 0.012, m_flat('#e5504b', 0.08, 8, 'bstarm'), loc=(0, 0.086, 0.78), bevel=0.004)
    # tente: arkadan öne eğik, ön kenarı dilli; çizgili (çadırla aynı renkler)
    AW = E.m_canvas(RED, CREAM, stripes=3.0, name='bawningm', mud=0, fade=0.3)
    verts = []; faces = []; uvs = []
    nx, ny = 9, 4
    for iy in range(ny + 1):
        t = iy / ny
        for ix in range(nx + 1):
            u = ix / nx; x = -0.23 + 0.46 * u
            y = 0.13 - 0.34 * t; z = 0.955 - 0.1 * t - 0.012 * math.sin(math.pi * u) * math.sin(math.pi * t)
            verts.append((x, y, z)); uvs.append((u, t * 0.4))
    for iy in range(ny):
        for ix in range(nx):
            a_ = iy * (nx + 1) + ix; faces.append((a_, a_ + 1, a_ + nx + 2, a_ + nx + 1))
    base = len(verts)
    for ix in range(nx + 1):                                    # ön dil (3 dil)
        u = ix / nx; x = -0.23 + 0.46 * u
        q = (u * 3) % 1.0
        verts.append((x, -0.21, 0.855)); uvs.append((u, 0.4))
        verts.append((x, -0.213, 0.855 - 0.055 * math.sin(math.pi * q) ** 0.8 - 0.01)); uvs.append((u, 0.48))
    for ix in range(nx):
        a_ = base + ix * 2; faces.append((a_, a_ + 2, a_ + 3, a_ + 1))
    E.mesh_obj('bawning', verts, faces, [AW], uvs=[[uvs[i] for i in f] for f in faces], ds=True)
    # bilet tabelası (yarım ay çentikli uçlar) + yıldız
    tk = [(-0.17, -0.065), (0.17, -0.065)] + [(0.17 - 0.032 * math.cos(b), -0.032 * math.sin(b)) for b in [math.pi / 2 - k * math.pi / 6 for k in range(7)]] \
         + [(0.17, 0.065), (-0.17, 0.065)] + [(-0.17 + 0.032 * math.cos(b), 0.032 * math.sin(b)) for b in [math.pi / 2 - k * math.pi / 6 for k in range(7)]]
    SG = m_wood('#b98a5a', 'bsignw', paint='#f4c548', age=1.1, grime=(-1, -0.9))
    AT.prism('bsign', [(x, z) for x, z in tk], 0.022, SG, loc=(0, 0.105, 1.045), rot=(4, 0, 0), bevel=0.006)
    star2 = [(x * 0.42, y * 0.42) for x, y in star]
    AT.prism('bstar', star2, 0.01, m_flat('#e5504b', 0.08, 8, 'bstarm2'), loc=(0, 0.09, 1.046), rot=(4, 0, 0), bevel=0.003)
    for s in (-1, 1):
        rbox('bsignleg', (s * 0.1, 0.11, 0.99), (0.02, 0.016, 0.07), NW, bevel=0.003)
    # tezgâh üstü: bilet rulosu + sarkan bilet şeridi, zil
    TR = m_flat('#e0574f', 0.08, 10, 'tickets')
    cyl('btickets', (0.1, -0.08, 0.538), 0.033, 0.04, TR, rot=(90, 0, 0), verts=14, bevel=0.004)
    rbox('bticket', (0.1, -0.2, 0.47), (0.034, 0.003, 0.11), TR, bevel=0)
    for z in (0.44, 0.48): rbox('bperf', (0.1, -0.202, z), (0.03, 0.002, 0.003), m_flat('#fbe6c8', 0.05, 8, 'perf'), bevel=0)
    blob('bbell', (-0.1, -0.08, 0.535), (0.03, 0.03, 0.024), m_flat('#e9b23c', 0.12, 12, 'bell'), sub=1, seg=10)
    blob('bbelltop', (-0.1, -0.08, 0.563), (0.008, 0.008, 0.01), I, sub=0, seg=8)
    # balonlar (arka sağ direğe bağlı)
    for k, (bx, by, bz, c) in enumerate(((0.2, 0.17, 1.4, '#f2bf45'), (0.05, 0.2, 1.5, '#36aab2'), (-0.06, 0.13, 1.36, '#ee7a9c'))):
        M = m_flat(c, 0.06, 6, 'balloon' + c)
        o = blob('balloon', (bx, by, bz), (0.068, 0.068, 0.084), M, sub=1, seg=12)
        blob('bknot', (bx, by, bz - 0.088), (0.012, 0.012, 0.014), M, sub=0, seg=8)
        tube('bstring', [(0.17, 0.095, 1.0), ((0.17 + bx) / 2 + 0.02, (0.095 + by) / 2, (1.0 + bz) / 2 - 0.04), (bx, by, bz - 0.1)], [0.0035] * 3, AT.m_rope('#f2ead8', 'bstr'), res=3)
    # yerel → dünya
    Mx = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    bpy.context.view_layer.update()                 # blob ölçeği matrix_world'e işlensin
    for o in [o for o in bpy.context.scene.objects if o.name not in before]:
        o.matrix_world = Mx @ o.matrix_world


def props_left():
    """Sol: fıçı (lobutlar) + açık sandık (renkli toplar)."""
    W = m_wood('#9b6a40', 'barrelw', grime=(-0.2, -0.08)); I = AT.m_metal('#47434d', '#a8643a', 'hoopm')
    AT.barrel((-1.52, -0.28, 0.17), r=0.13, h=0.34, wood=W, iron=I)
    PIN = m_flat('#f6efe2', 0.06, 8, 'pinw'); PR = m_flat('#e5504b', 0.06, 8, 'pinr')
    for k, (dx, dy, tl) in enumerate(((-0.03, 0.02, 8), (0.035, -0.01, -10), (0.0, -0.04, 3))):
        x, y = -1.52 + dx, -0.28 + dy
        o = AT.lathe('jpin', [(0.001, 0.0), (0.018, 0.0), (0.03, 0.06), (0.026, 0.11), (0.012, 0.15), (0.016, 0.19), (0.001, 0.2)], PIN, segs=10)
        o.location = (x, y, 0.24); o.rotation_euler = (math.radians(tl), math.radians(-tl * 0.7), 0)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.016, minor_radius=0.005, location=(0, 0, 0.165), major_segments=10, minor_segments=4)
        t = bpy.context.object; t.name = 'jpinband'; t.data.materials.append(PR); t.parent = o
    bpy.context.view_layer.update()
    for o in [o for o in bpy.context.scene.objects if o.name.startswith('jpinband')]:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    s = 0.25
    m1 = m_wood('#a8784a', 'cratew', grime=(-1, -0.9)); m2 = m_wood('#8a5f38', 'cratew2', grime=(-1, -0.9))
    for m in (m1, m2): E.layer(m, E.grime(0.1, 0.5))
    AT.crate((-1.28, -0.72, 0.0), s, m1, m2, yaw=-18, open_top=True, seed=5)
    for k, (dx, dy, c) in enumerate(((-0.05, -0.03, '#f2bf45'), (0.05, 0.02, '#36aab2'), (0.0, 0.07, '#ee7a9c'), (-0.07, 0.06, '#86c25a'))):
        blob('jball', (-1.28 + dx, -0.72 + dy, s * 0.9 + 0.02 * (k % 2)), (0.05, 0.05, 0.05), m_flat(c, 0.08, 8, 'jb' + c), sub=1, seg=10)


def ground():
    """Duvar dibinde kum birikintisi (kapı önü açık), girişte talaşlı kum, yer yer yosun."""
    door = math.pi / NP + 0.08
    E.sand_ring(0, 0, lambda a: wall_r(a, 0.0) + 0.02, 0.1, 0.04, seed=3, m=E.m_sandy('festsand', '#d2b484'), a0=-math.pi / 2 + door, a1=-math.pi / 2 + 2 * math.pi - door, n=80)
    AT.dirt_patch(0.0, -1.22, 0.42, 0.3, 77, name='wornground', sand=True)
    for k, a in enumerate((math.radians(70), math.radians(100), math.radians(140), math.radians(40))):
        r = wall_r(a, 0.0) + 0.05
        E.moss_clump((math.cos(a) * r, math.sin(a) * r, 0.01), 0.055, seed=60 + k, n=2)


def build():
    R = random.Random(23)
    wall, roof = tent()
    patches(wall, roof)
    flaps(); guys(); lanterns()
    booth(1.5, -0.35, -10)
    props_left()
    ground()
    # dip süsü: eski yapıcıyla aynı tohum (sınır kutusu korunur); yeni parçaların altına düşenler silinir
    before = set(bpy.context.scene.objects.keys())
    AT.dress(1.9, 61, n_tufts=9, flowers=6, pebbles=2, bushes=[(-1.45, 0.3), (1.4, 0.55), (0.3, 1.5)],
             exclude=lambda x, y: math.hypot(x, y) < 1.35 or (abs(x) < 0.4 and y < 0))
    def under(x, y):
        return (abs(x - 1.5) < 0.3 and abs(y + 0.37) < 0.25) or (abs(x + 1.4) < 0.28 and -0.95 < y < -0.1) or (abs(x) < 0.5 and -1.6 < y < -1.0)
    print('silinen dip süsü', E.clear_area(before, under), flush=True)


DECIM = [
    (r'^(pet|fc)$', 0.4), (r'^stem$', 0.4), (r'^Icosphere$', 0.3), (r'^mossclump$', 0.12), (r'^(balloon|jball|topball)$', 0.16),
    (r'^flaproll$', 0.4), (r'^(trim|flaptie|pegwrap|Torus|jpinband)$', 0.45), (r'^pompom$', 0.5), (r'^(lpost|pole)$', 0.6),
    (r'^(barrel|jpin)$', 0.55), (r'^(bbell|bknot|bbelltop)$', 0.5), (r'^(guyrope|entrrope|bstring|pegtail|flaptail)$', 0.5),
    (r'^(bplank|bside|bcounter|bback)$', 0.3), (r'^(slat|brace|edge|core|lid)$', 0.3), (r'^(sandmound|pegmound|postmound)$', 0.6),
    (r'^(peg|peghead)$', 0.3), (r'^(bstar|bsign)$', 0.45), (r'^(bsignleg|bpost|lbase|tfloor|lbar)$', 0.3), (r'^(nail|streak)$', 0.3),
    (r'^lush$', 0.5), (r'^rosette$', 0.5), (r'^(tentroof|tentwall)$', 0.72), (r'^(collar|lcap)$', 0.6),
]
WEIGHTS = [
    (r'^patch$', 2.2), (r'^(bsign|bstar)$', 2.0), (r'^valance$', 1.3), (r'^(tentwall)$', 1.15), (r'^tentroof$', 1.0),
    (r'^(lamp|lcap|lbar)$', 1.6), (r'^(bplank|bawning|bcounter)$', 1.3), (r'^(flaproll|flaptie)$', 1.2),
    (r'^(lush|rosette|sanddrift|wornground|sawdust)$', 0.55), (r'^(liner|tfloor|rug)$', 0.3), (r'^(bcore)$', 0.3),
]


if __name__ == '__main__':
    out, dr, yaw = E.args()
    kit.reset(); build(); hi = E.BK.prepare()
    print('taslak üçgen', E.BK.tri_count(hi), 'nesne', len(hi), flush=True)
    if dr:
        E.draft(dr, yaw)
    else:
        E.bake(out, NAME, hi, DECIM, WEIGHTS, CAP)
