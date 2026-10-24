# Bahçe oyun modeli (24 Ekim 2026; kullanıcı: "haritadaki bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Eski model (assets_town.c_garden) 8 bin üçgene küresel sadeleşip yalnız renk + AO pişiyordu: kütük çerçeveler düz boru, basamak taşları
# kaybolmuş, ayçiçekleri yandan halka gibi görünüyordu, sağ tarh boş topraktı. Aynı yerleşim (orijin, ön = −Y, boy ve yatay kapsam
# eskisiyle aynı) yeniden kuruldu; oyun kamerasından (8–14 m) okunacak iri ayrıntılar:
#   tarhlar   iki yükseltilmiş tahta tarh: iki kat damarlı tahta, köşe dikmeleri (biri yosun başlıklı), paslı çiviler + pas akıntısı,
#             biri sonradan değiştirilmiş açık renk tahta, biri dışa bombeli; dipte yosun ve kum; toprak sıra sıra kabarık (çizgili).
#   sol tarh  havuç sıraları + lahanalar; arkada ada usulü korkuluk: hindistan cevizi kafa (düğme göz, gülen ağız), hasır şapka,
#             çiçekli gömlek, kollarından saman taşan, hurma yaprağı etek.
#   sağ tarh  arkada fasulye çardağı (kafes + tırmanan sarmaşık, yaprak, çiçek, fasulye), iki sırıklı domates (bağlı, olgun/ham),
#             iki ayçiçeği (öne-yukarı bakan tabla), önde karpuzlar.
#   ara       basamak taşları (kenarı yosunlu, biraz gömülü) + aşınmış toprak yol; tarh önlerinde tohum paketi kazıkları (havuç, domates).
#   kenarlar  solda turkuaz sulama kabı (boyası dökük, pas lekeli); sağda alet askısı (tırmık, kürek, çapa: paslı demir, aşınmış sap)
#             ve çıtalı kompost kasası (içinde kompost, yeşil kırpıntı, muz kabuğu); arkada boyası dökük çit (bir çıtası eksik,
#             biri yamuk), uç direkleri yosunlu.
# Oyun modeli: ada_eskitme.bake (bld_kit). Kullanım: python -I bld/b_garden.py -- <çıktı> [b_garden] [--draft <png> [yaw]]
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
from assets_v3 import m_wood, m_flat, m_leaf, blade, mesh_from_blades, _shade

NAME = 'b_garden'
CAP = 14000
BEDS = [(-0.66, 0.0), (0.66, 0.0)]
BW, BD = 0.85, 1.7                  # tarh iç ölçüsü (aradaki yol taşlara yetsin diye eskisinden 10 cm dar)
BH = 0.22                           # tahta yüksekliği (iki kat)


def board(name, c, size, m, seed, bow=0.0, axis=0):
    """Tarh tahtası: AT.plank + istenirse dışa bombe (orta kısım dışa itilir)."""
    o = AT.plank(name, c, size, m, seed=seed, amt=0.005)
    if bow:
        L = size[axis]
        for v in o.data.vertices:
            t = (v.co[axis] / L) + 0.5
            d = math.sin(math.pi * max(0.0, min(1.0, t))) * bow
            if axis == 0: v.co.y += d
            else: v.co.x += d
    return o


def beds():
    R = random.Random(13)
    W1 = m_wood('#8e6a48', 'bedw', age=1.3, grime=(-1, -0.9))
    W2 = m_wood('#a37a52', 'bedw2', age=1.2, grime=(-1, -0.9))
    NEW = m_wood('#c99c68', 'bednew', age=0.4, grime=(-1, -0.9))                     # sonradan değiştirilmiş tahta
    PO = m_wood('#7d5a3a', 'bedpost', age=1.4, grime=(-1, -0.9))
    for m in (W1, W2, NEW, PO):
        E.layer(m, E.grime(0.12, 0.55)); E.layer(m, E.base_moss(0.13, 0.9, back=(-0.2, 0.9)))
    SOIL = AT.m_soil('bedsoil')
    E.layer(SOIL, lambda G, c: G.mix(G.rng(G.noise(G.obj(), 25, 3), 0.62, 0.72, 0, 0.5), c, '#8a6a46'))
    th = 0.04
    for bi, (bx, by) in enumerate(BEDS):
        for row in range(2):
            z = 0.055 + row * 0.11
            for sy in (-1, 1):
                m = NEW if (bi == 1 and row == 1 and sy == -1) else (W1, W2)[(row + bi) % 2]
                board('bedboard', (bx, by + sy * (BD / 2 + th / 2), z), (BW + 2 * th + 0.01, th, 0.105), m, seed=bi * 20 + row * 4 + sy,
                      bow=(0.018 * -sy if (bi == 0 and row == 0 and sy == -1) else 0.0), axis=0)
            for sx in (-1, 1):
                board('bedboard', (bx + sx * (BW / 2 + th / 2), by, z), (th, BD + 0.005, 0.105), (W2, W1)[(row + bi) % 2], seed=bi * 20 + row * 4 + sx + 10, axis=1)
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = bx + sx * (BW / 2 + th + 0.03), by + sy * (BD / 2 + th + 0.03)
                h = 0.3 + R.uniform(-0.02, 0.02)
                AT.plank('bedpost', (px, py, h / 2 - 0.03), (0.07, 0.07, h + 0.06), PO, seed=bi * 7 + sx * 2 + sy, amt=0.004)
                AT.nail((px, py + sy * 0.036, 0.12), (0, sy, 0))
                if sy > 0 and (bi + sx) % 2 == 0:
                    E.moss_clump((px + sx * 0.05, py + 0.04, 0.0), 0.06, seed=bi * 5 + sx, n=2)
                if sy > 0 and bi == 1 and sx > 0:
                    AT.moss_cap((px, py, h - 0.03 + 0.012), 0.045, seed=3)
        # toprak: sıra sıra kabarık (y boyunca), kenarda tahtaya doğru iner
        nx, ny = 12, 22
        verts = []; faces = []
        for iy in range(ny + 1):
            for ix in range(nx + 1):
                u, v = ix / nx, iy / ny
                x = bx - BW / 2 + 0.005 + (BW - 0.01) * u; y = by - BD / 2 + 0.005 + (BD - 0.01) * v
                edge = min(u, 1 - u, v, 1 - v)
                fur = 0.022 * (0.5 + 0.5 * math.cos(u * 3 * 2 * math.pi + math.pi)) if 0.06 < u < 0.94 else 0.0
                z = 0.17 + 0.04 * min(1.0, edge / 0.08) + fur + 0.006 * mnoise.noise(V((x * 9, y * 9, bi)))
                verts.append((x, y, z))
        for iy in range(ny):
            for ix in range(nx):
                a_ = iy * (nx + 1) + ix; faces.append((a_, a_ + 1, a_ + nx + 2, a_ + nx + 1))
        E.mesh_obj('soil', verts, faces, [SOIL])
        E.sand_mound(bx + 0.25, by - BD / 2 - 0.08, 0.2, 0.06, 0.016, 40 + bi, m=E.m_sandy('beddirt', '#a98258'), name='bedsand', n=14, rings=2)


def soil_z(x, y):
    bx = BEDS[0][0] if x < 0 else BEDS[1][0]
    u = (x - (bx - BW / 2)) / BW
    return 0.21 + 0.022 * (0.5 + 0.5 * math.cos(u * 3 * 2 * math.pi + math.pi))


def left_bed():
    R = random.Random(7)
    LEAFC = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'carrotleaf')
    carrots = [(x, y) for y in (-0.62, -0.33, -0.04, 0.25) for x in (-0.94, -0.68)]
    for (x, y) in carrots:
        z = soil_z(x, y)
        o = blob('carrot', (x, y, z + 0.01), (0.045, 0.045, 0.045), AT.m_fruit('carrot'), sub=1, seg=10)
    def ctops(bm):
        out = []
        for (x, y) in carrots:
            z = soil_z(x, y) + 0.04
            for k in range(4):
                a = k * 1.57 + R.uniform(0, 0.5); up = R.uniform(0.7, 0.92)
                d = V((math.cos(a) * (1 - up), math.sin(a) * (1 - up), up)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((x, y, z)), d, side, R.uniform(0.19, 0.26), 0.035, 0.5, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('ctops', ctops, [LEAFC])
    CAB = m_leaf('#6fb24e', '#9ad37a', '#cdebaa', '#e6f6cc', 'cabbage')
    cab = [(-0.42, -0.55), (-0.4, -0.12), (-0.43, 0.3)]
    def cabbages(bm):
        out = []
        for (x, y) in cab:
            z = soil_z(x, y)
            for ring, (nn, up, L) in enumerate(((5, 0.25, 0.22), (4, 0.55, 0.16), (3, 0.85, 0.1))):
                for k in range(nn):
                    a = k * 2 * math.pi / nn + ring * 0.5
                    d = V((math.cos(a) * (1 - up), math.sin(a) * (1 - up), up)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                    for f in blade(bm, V((x, y, z + 0.01 + ring * 0.02)), d, side, L, 0.1 - ring * 0.015, 0.6 - ring * 0.25, segs=3, lift=0.2): out.append((f, 0))
        return out
    mesh_from_blades('cabbages', cabbages, [CAB])
    for (x, y) in cab: blob('cabheart', (x, y, soil_z(x, y) + 0.08), (0.075, 0.075, 0.065), m_flat('#c4e69a', 0.12, 10, 'cabheart'), sub=1, seg=12)
    scarecrow(-0.66, 0.6)


def scarecrow(x, y):
    """Ada korkuluğu: sırık + kol çıtası, hindistan cevizi kafa (düğme göz, gülen ağız, yanak), hasır şapka (kırmızı bant),
    çiçekli gömlek + kollarda saman, hurma yaprağı etek. Yerel kurulur, (x, y)'ye taşınır (hafif döndürülmüş)."""
    before = set(bpy.context.scene.objects.keys())
    R = random.Random(19)
    ST = m_wood('#8a6440', 'scstick', grime=(-1, -0.9))
    z0 = 0.2
    tube('scpole', [(0, 0, z0 - 0.05), (0, 0, z0 + 0.95)], [0.022, 0.018], ST, res=1)
    tube('scarm', [(-0.29, 0.0, 0.8), (0.29, 0.0, 0.8)], [0.016, 0.016], ST, res=1)
    # gömlek: turkuaz zemin, iri çiçek baskı (voronoi benek), güneşte solmuş
    def mshirt(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 3, 3), 0.3, 0.7), '#2c9aa5', '#3fb2b8')
        d = G.vor(o, 14.0)
        col = G.mix(G.rng(d, 0.2, 0.14), col, '#f5d05a')
        d2 = G.vor(G.mapping(o, (1.3, 1.3, 1.3)), 11.0)
        col = G.mix(G.rng(d2, 0.17, 0.11), col, '#f07aa0')
        col = G.mix(G.rng(G.noise(o, 2, 3), 0.5, 0.75, 0, 0.3), col, '#fff3dc')
        nt.links.new(col, bsdf.inputs['Base Color'])
    SH = kit.nodes_mat('shirt', mshirt)
    body = blob('shirt', (0, 0, 0.7), (0.15, 0.085, 0.16), SH, sub=1, seg=14)
    AT.wobble(body, 0.008, 6.0, 4)
    for s in (-1, 1):
        tube('sleeve', [(s * 0.1, 0, 0.79), (s * 0.18, 0, 0.8), (s * 0.24, 0, 0.795)], [0.055, 0.05, 0.046], SH, res=2)
    STRAW = m_leaf('#b98a3e', '#d4a855', '#e8c674', '#f0d58e', 'straw')
    def straw(bm):
        out = []
        for s in (-1, 1):
            for k in range(7):
                a = R.uniform(-0.9, 0.9); d = V((s * 1.0, math.sin(a) * 0.6, math.cos(a) * 0.5 - 0.2)).normalized()
                side = V((0, math.cos(a), -math.sin(a))) if abs(d.y) < 0.9 else V((1, 0, 0))
                for f in blade(bm, V((s * 0.25, 0, 0.795)), d, side, R.uniform(0.07, 0.11), 0.012, 0.2, segs=2): out.append((f, 0))
        for k in range(5):                                             # yakadan taşan saman
            a = k / 5 * 2 * math.pi
            d = V((math.cos(a) * 0.6, math.sin(a) * 0.5, 0.6)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V((0, 0, 0.85)), d, side, 0.06, 0.012, 0.2, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('scstraw', straw, [STRAW])
    PALM = m_leaf('#4a8a2c', '#76b244', '#b8d86a', '#d6ea96', 'palmskirt')
    def skirt(bm):
        out = []
        for k in range(16):
            a = k / 16 * 2 * math.pi + R.uniform(-0.05, 0.05)
            d = V((math.cos(a) * 0.32, math.sin(a) * 0.22, -1.0)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V((math.cos(a) * 0.13, math.sin(a) * 0.075, 0.57)), d, side, R.uniform(0.2, 0.26), 0.035, -0.1, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('scskirt', skirt, [PALM])
    bpy.ops.mesh.primitive_torus_add(major_radius=0.135, minor_radius=0.014, location=(0, 0, 0.57), major_segments=16, minor_segments=4)
    o = bpy.context.object; o.name = 'scbelt'; o.scale = (1.0, 0.62, 1.0); o.data.materials.append(AT.m_rope())
    # kafa: hindistan cevizi + yüz
    head = AT.fruit('coconut', (0, 0, 1.0), 0.1, seed=3)
    for o in [o for o in bpy.context.scene.objects if o.name.startswith('eye') and o.name not in before]: bpy.data.objects.remove(o)   # şapka altında kalıyor
    DK = m_flat('#2b2420', 0.05, 6, 'button')
    for s in (-1, 1):
        cyl('sceye', (s * 0.038, -0.094, 1.02), 0.017, 0.012, DK, rot=(90 - 8, 0, 0), verts=10, bevel=0.003)
        blob('sccheek', (s * 0.06, -0.088, 0.985), (0.018, 0.006, 0.012), m_flat('#f08a7a', 0.05, 6, 'cheek'), rot=(0, 0, s * 20), sub=0, seg=8)
    mouth = [(math.sin(a) * 0.04, -0.095 + 0.008 * (1 - math.cos(a)), 0.965 - 0.018 * math.cos(a)) for a in [-1.0 + k * 0.5 for k in range(5)]]
    tube('scmouth', mouth, [0.005] * 5, DK, res=2)
    # hasır şapka: geniş, hafif sarkık kenar + tepe + kırmızı bant
    HT = m_wood('#d9b26a', 'hat', age=0.6, grime=(-1, -0.9))
    verts = [(0, 0, 1.1)]; faces = []
    n = 20
    for j, (rr, dz) in enumerate(((0.09, 1.1), (0.15, 1.085), (0.2, 1.06))):
        for i in range(n):
            a = i / n * 2 * math.pi; droop = 0.012 * (1 + math.sin(a * 2 + 1)) * (j == 2)
            verts.append((math.cos(a) * rr, math.sin(a) * rr, dz - droop))
    for i in range(n): faces.append((0, 1 + i, 1 + (i + 1) % n))
    for j in range(2):
        for i in range(n):
            a_, b_ = 1 + j * n + i, 1 + (j + 1) * n + i
            faces.append((a_, b_, 1 + (j + 1) * n + (i + 1) % n, 1 + j * n + (i + 1) % n))
    br = E.mesh_obj('hatbrim', verts, faces, [HT])
    s_ = br.modifiers.new('sol', 'SOLIDIFY'); s_.thickness = 0.01
    AT.lathe('hatcrown', [(0.085, 1.09), (0.088, 1.13), (0.075, 1.17), (0.04, 1.185), (0.001, 1.188)], HT, segs=16)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.087, minor_radius=0.013, location=(0, 0, 1.11), major_segments=16, minor_segments=4)
    o = bpy.context.object; o.name = 'hatband'; o.data.materials.append(m_flat('#e5504b', 0.08, 8, 'hatbandm'))
    bpy.context.view_layer.update()
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(-8), 4, 'Z')
    for o in [o for o in bpy.context.scene.objects if o.name not in before]: o.matrix_world = M @ o.matrix_world


def right_bed():
    R = random.Random(11)
    # fasulye çardağı (arkada)
    TW = m_wood('#a07c58', 'trellis', age=1.5, grime=(-1, -0.9))
    E.layer(TW, E.grime(0.3, 0.4))
    ty = 0.79; x0, x1 = 0.29, 1.04
    for x in (x0, x1):
        AT.plank('trpost', (x, ty, 0.68), (0.035, 0.035, 1.0), TW, seed=int(x * 10), amt=0.004)
    for k in range(4):
        x = x0 + (x1 - x0) * (k + 0.5) / 4
        rbox('trslat', (x, ty, 0.7), (0.016, 0.012, 0.92), TW, bevel=0.003)
    for k in range(5):
        rbox('trslat', ((x0 + x1) / 2, ty, 0.3 + k * 0.2), (x1 - x0, 0.012, 0.016), TW, bevel=0.003)
    rbox('trtop', ((x0 + x1) / 2, ty, 1.19), (x1 - x0 + 0.08, 0.04, 0.03), TW, bevel=0.006)
    VN = m_flat('#4f8f35', 0.15, 8, 'beanvine')
    BL = m_leaf('#2f7d35', '#4f9d45', '#8bc65a', '#a8d87a', 'beanleaf')
    vines = []
    for k, vx in enumerate((0.4, 0.66, 0.9)):
        pts = []
        for i in range(12):
            t = i / 11; z = 0.22 + t * 0.92
            pts.append((vx + 0.05 * math.sin(t * 9 + k), ty - 0.02 + 0.02 * math.cos(t * 9 + k), z))
        tube('beanvine', pts, [0.008] * len(pts), VN, res=1); vines.append(pts)
    def leaves(bm):
        out = []
        for k, pts in enumerate(vines):
            for i in range(2, 12):
                p = V(pts[i]); a = R.uniform(-1.2, 1.2) + (0 if i % 2 else math.pi)
                d = V((math.cos(a) * 0.8, -0.55, R.uniform(-0.2, 0.3))).normalized(); side = V((-d.y, d.x, 0)).normalized()
                for f in blade(bm, p, d, side, R.uniform(0.1, 0.14), 0.056, 0.3, segs=3, lift=0.1): out.append((f, 0))
        return out
    mesh_from_blades('beanleaves', leaves, [BL])
    POD = m_flat('#6fae3c', 0.12, 10, 'pod'); FL = m_flat('#fbf2e2', 0.06, 8, 'beanflower')
    for k, pts in enumerate(vines):
        for i in (4, 7, 10):
            p = V(pts[i]) + V((0.03, -0.035, 0))
            tube('pod', [tuple(p), tuple(p + V((0.008, -0.004, -0.05))), tuple(p + V((0.0, -0.006, -0.1)))], [0.009, 0.01, 0.005], POD, res=2)
        for i in (5, 9):
            blob('beanfl', tuple(V(pts[i]) + V((-0.03, -0.04, 0.01))), (0.02, 0.014, 0.018), FL, sub=0, seg=8)
    # domates: iki sırık, bağlar, olgun + ham meyveler
    ST = m_wood('#a8693d', 'stake', grime=(-1, -0.9)); TL = m_leaf('#2f7d35', '#4f9d45', '#8bc65a', '#a8d87a', 'tomleaf')
    TOMS = [m_flat('#e0402f', 0.15, 12, 'tom_r'), m_flat('#f07a3a', 0.15, 12, 'tom_o'), m_flat('#8cc04a', 0.15, 12, 'tom_g')]
    for j, (x, y) in enumerate(((0.44, -0.5), (0.46, 0.02))):
        tube('stake', [(x, y, 0.15), (x + 0.01, y, 0.9)], [0.018, 0.015], ST, res=1)
        pts = [(x + math.cos(t * 6) * 0.05, y + math.sin(t * 6) * 0.05, 0.22 + t * 0.62) for t in [i / 8 for i in range(9)]]
        tube('vine', pts, [0.012] * len(pts), m_flat('#4f8f35', 0.15, 8, 'tvine'), res=1)
        for z in (0.45, 0.72):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.006, location=(x, y, z), major_segments=8, minor_segments=3)
            bpy.context.object.name = 'tie'; bpy.context.object.data.materials.append(AT.m_rope('#e8d6b0', 'tie'))
        for k in range(5):
            blob('tom', (x + math.cos(k * 2.3 + j) * 0.075, y - 0.03 + math.sin(k * 2.3 + j) * 0.06, 0.42 + k * 0.1), (0.05, 0.05, 0.046),
                 TOMS[0 if k < 3 else (1 if k == 3 else 2)], sub=1, seg=10)
        def tl(bm, x=x, y=y):
            out = []
            for k in range(7):
                a = k * 2.3; z = 0.3 + k * 0.085
                d = V((math.cos(a), math.sin(a), 0.2)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((x, y, z)), d, side, 0.15, 0.06, 0.5, segs=3): out.append((f, 0))
            return out
        mesh_from_blades('tleaves', tl, [TL])
    # ayçiçekleri: tabla öne-yukarı (−Y, 35° yukarı)
    SS = m_flat('#4f8f35', 0.15, 8, 'sstem'); PE = m_leaf('#f2b51e', '#ffcd2e', '#ffe066', '#fff0a0', 'sunpet')
    SL = m_leaf('#3a7d30', '#55a03c', '#8cc35a', '#a8d87a', 'sunleaf')
    def mdisc(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.vor(o, 60.0), 0.0, 0.25), '#3b2412', '#7a4a22')
        nt.links.new(col, bsdf.inputs['Base Color'])
    DM = kit.nodes_mat('sundisc', mdisc)
    for (x, y, h, sd) in ((0.88, -0.42, 1.29, 1), (0.9, 0.2, 1.06, 2)):
        tube('sstem', [(x, y, 0.2), (x + 0.02, y - 0.01, h * 0.6), (x, y - 0.05, h - 0.03)], [0.02, 0.018, 0.016], SS, res=2)
        c = V((x, y - 0.07, h)); nrm = V((0, -math.cos(math.radians(35)), math.sin(math.radians(35))))
        up = V((0, 0, 1)); ax = nrm.cross(up).normalized(); ay = ax.cross(nrm).normalized()
        d = cyl('sundisc', tuple(c), 0.075, 0.03, DM, verts=16, bevel=0.012)
        d.rotation_euler = nrm.to_track_quat('Z', 'Y').to_euler()
        def pets(bm, c=c, ax=ax, ay=ay, nrm=nrm):
            out = []
            for k in range(14):
                b = k / 14 * 2 * math.pi
                dd = (ax * math.cos(b) + ay * math.sin(b)).normalized()
                side = nrm.cross(dd).normalized()
                for f in blade(bm, c + dd * 0.065 - nrm * 0.005, (dd + nrm * 0.12).normalized(), side, 0.075, 0.026, 0.05, segs=2): out.append((f, 0))
            return out
        mesh_from_blades('sunpetals', pets, [PE])
        def sl(bm, x=x, y=y, h=h):
            out = []
            for k, (zz, a) in enumerate(((0.45, 0.5), (0.7, 3.5))):
                d = V((math.cos(a), math.sin(a), 0.15)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((x, y, h * zz)), d, side, 0.16, 0.065, 0.5, segs=3): out.append((f, 0))
            return out
        mesh_from_blades('sunleaves', sl, [SL])
    # karpuzlar (önde) + yaprak
    AT.fruit('melon', (0.74, -0.68, 0.29), 0.105, seed=2).rotation_euler = (0, 0, math.radians(25))
    AT.fruit('melon', (0.98, -0.2, 0.27), 0.075, seed=5).rotation_euler = (0, 0, math.radians(-40))
    ML = m_leaf('#2f7d35', '#4f9d45', '#8bc65a', '#a8d87a', 'melonleaf')
    def ml(bm):
        out = []
        for (x, y, a) in ((0.6, -0.6, 2.2), (0.86, -0.78, -0.6), (0.88, -0.3, 0.6), (0.62, -0.32, 2.8)):
            d = V((math.cos(a), math.sin(a), 0.25)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V((x, y, soil_z(x, y) + 0.01)), d, side, 0.13, 0.06, 0.3, segs=3, lift=0.05): out.append((f, 0))
        return out
    mesh_from_blades('melonleaves', ml, [ML])
    tube('melonvine', [(0.6, -0.6, 0.235), (0.68, -0.5, 0.24), (0.8, -0.4, 0.235), (0.95, -0.27, 0.235)], [0.007] * 4, m_flat('#4f8f35', 0.15, 8, 'mvine'), res=2)


def path_and_signs():
    R = random.Random(3)
    AT.dirt_patch(0.0, 0.0, 0.17, 0.98, 21, name='wornground')
    STN = A.m_rock(moss_th=(0.62, 0.95), name='pathstone')
    for k in range(5):
        y = -0.82 + k * 0.41
        o = AT.rock((R.uniform(-0.03, 0.03), y, 0.0), 0.12, STN, 70 + k, sq=(1.05, 0.85, 0.32), sub=2, amt=0.12)
        o.name = 'pathstone'
    # tohum paketleri: tarh önünde kazık + paket (havuç / domates resimli)
    PK = m_wood('#c8a878', 'pkstake', grime=(-1, -0.9))
    for (x, kind) in ((-0.95, 'carrot'), (0.32, 'tomato')):
        y = -0.78; z = 0.38
        rbox('pkstake', (x, y, 0.27), (0.014, 0.014, 0.24), PK, bevel=0.002)
        def mpaper(nt, bsdf, kind=kind):
            G = A._G(nt); o = G.obj()
            base = '#f6e7c4' if kind == 'carrot' else '#e9f2d2'
            col = G.mix(G.rng(G.noise(o, 8, 3), 0.3, 0.7), base, _shade(base, 0.92))
            nt.links.new(col, bsdf.inputs['Base Color'])
        rbox('packet', (x, y - 0.012, z), (0.085, 0.006, 0.11), kit.nodes_mat('packet' + kind, mpaper), rot=(0, 4 if kind == 'carrot' else -5, 0), bevel=0.002)
        if kind == 'carrot':
            AT.prism('pkicon', [(-0.014, 0.025), (0.014, 0.025), (0.0, -0.03)], 0.004, m_flat('#f07a2a', 0.05, 8, 'pkcar'), loc=(x, y - 0.017, z), bevel=0.001)
            for dx in (-0.008, 0.0, 0.008):
                rbox('pkleaf', (x + dx, y - 0.017, z + 0.035), (0.004, 0.003, 0.016), m_flat('#4f9d45', 0.05, 8, 'pkleafm'), rot=(0, dx * 1500, 0), bevel=0)
        else:
            cyl('pkicon', (x, y - 0.017, z - 0.004), 0.024, 0.004, m_flat('#e0402f', 0.05, 8, 'pktom'), rot=(90, 0, 0), verts=12, bevel=0)
            rbox('pkleaf', (x, y - 0.019, z + 0.02), (0.02, 0.003, 0.008), m_flat('#4f9d45', 0.05, 8, 'pkleafm2'), bevel=0)


def watering_can():
    """Sulama kabı (eski yerinde): turkuaz boya dökük, dikişlerde pas, hafif ezik; delikli süzgeç başı."""
    TEAL = AT.m_metal('#2fa3a0', '#b0663a', 'canm', age=0.7)
    E.layer(TEAL, lambda G, c: G.mix(G.math('MULTIPLY', G.edges(0.55, 0.62), 0.6), c, '#8a8f94'))
    cx, cy = -1.35, -0.85
    can = AT.lathe('can', [(0.001, 0.0), (0.12, 0.0), (0.135, 0.02), (0.14, 0.12), (0.125, 0.22), (0.09, 0.25), (0.001, 0.252)], TEAL, segs=18)
    can.location = (cx, cy, 0); AT.dent(can, 2, 0.012, 4)
    for z in (0.02, 0.22):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.135 if z < 0.1 else 0.122, minor_radius=0.008, location=(cx, cy, z), major_segments=18, minor_segments=4)
        bpy.context.object.name = 'canrim'; bpy.context.object.data.materials.append(TEAL)
    tube('spout', [(cx + 0.11, cy, 0.06), (cx + 0.24, cy, 0.17), (cx + 0.32, cy, 0.27)], [0.024, 0.018, 0.016], TEAL, res=2)
    rose = AT.lathe('rose', [(0.001, -0.02), (0.02, -0.02), (0.045, 0.02), (0.046, 0.026), (0.001, 0.027)], TEAL, segs=12)
    rose.location = (cx + 0.335, cy, 0.285); rose.rotation_euler = (0, math.radians(60), 0)
    DK = m_flat('#24302f', 0.05, 6, 'roseholes')
    bpy.context.view_layer.update()
    for k in range(7):
        a = k / 6 * 2 * math.pi; rr = 0.0 if k == 6 else 0.025
        p = rose.matrix_world @ V((math.cos(a) * rr, math.sin(a) * rr, 0.028))
        blob('rosehole', tuple(p), (0.006, 0.006, 0.003), DK, rot=(0, 60, 0), sub=0, seg=6)
    tube('canhandle', [(cx - 0.1, cy, 0.14), (cx - 0.1, cy, 0.33), (cx + 0.03, cy, 0.34), (cx + 0.08, cy, 0.25)], [0.014] * 4, TEAL, res=3)
    E.sand_mound(cx + 0.03, cy, 0.13, 0.13, 0.014, 9, name='cansand', n=14, rings=2)


def tool_rack():
    """Sağda alet askısı (yüzü +X): iki dikme + kiriş + çiviler; tırmık, kürek, çapa (paslı demir, aşınmış sap)."""
    W = m_wood('#8a6646', 'rackw', age=1.4, grime=(-1, -0.9)); E.layer(W, E.grime(0.15, 0.5)); E.layer(W, E.base_moss(0.15, 0.8))
    HD = m_wood('#c09a6a', 'handle', age=0.9, grime=(-1, -0.9))
    IR = AT.m_metal('#55515c', '#b0663a', 'toolm', age=1.6)
    x = 1.36; ya, yb = -0.5, 0.12
    for y in (ya, yb):
        AT.plank('rackpost', (x, y, 0.32), (0.05, 0.05, 0.7), W, seed=int(y * 10) + 5, amt=0.004)
        E.sand_mound(x, y, 0.07, 0.07, 0.015, int(y * 10) + 20, m=E.m_sandy('rackdirt', '#a98258'), name='racksand', n=10, rings=2)
    AT.plank('rackbar', (x + 0.03, (ya + yb) / 2, 0.6), (0.03, 0.78, 0.06), W, seed=8, amt=0.004)
    pegs = [-0.38, -0.12, 0.08]
    for py in pegs:
        rbox('rackpeg', (x + 0.07, py, 0.6), (0.06, 0.014, 0.014), W, bevel=0.002)
    # tırmık (başı yukarıda)
    py = pegs[0]; px = x + 0.06
    tube('rakehandle', [(px, py, 0.62), (px + 0.01, py, 0.08)], [0.011, 0.011], HD, res=1)
    rbox('rakehead', (px, py, 0.66), (0.022, 0.2, 0.02), IR, bevel=0.003)
    for k in range(7):
        rbox('raketooth', (px + 0.012, py - 0.09 + k * 0.03, 0.69), (0.008, 0.008, 0.05), IR, rot=(0, -10, 0), bevel=0)
    # kürek
    py = pegs[1]
    tube('spadehandle', [(px, py, 0.72), (px + 0.01, py, 0.25)], [0.012, 0.012], HD, res=1)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.008, location=(px, py, 0.75), rotation=(0, math.radians(90), 0), major_segments=10, minor_segments=4)
    bpy.context.object.name = 'spadegrip'; bpy.context.object.data.materials.append(HD)
    AT.prism('spadeblade', [(-0.055, 0.0), (0.055, 0.0), (0.055, -0.12), (0.0, -0.16), (-0.055, -0.12)], 0.01, IR, loc=(px + 0.012, py, 0.26), rot=(0, 0, 90), bevel=0.003)
    # çapa
    py = pegs[2]
    tube('hoehandle', [(px, py, 0.64), (px + 0.01, py, 0.05)], [0.011, 0.011], HD, res=1)
    rbox('hoeblade', (px + 0.04, py, 0.06), (0.07, 0.1, 0.008), IR, rot=(0, -70, 0), bevel=0.002)
    rbox('hoeneck', (px + 0.015, py, 0.075), (0.012, 0.012, 0.04), IR, bevel=0)


def compost():
    """Çıtalı kompost kasası (sağ arka): aralıklı çıtalar, köşe dikmeleri, içinde kompost tümseği + yeşil kırpıntı + muz kabuğu."""
    R = random.Random(23)
    W = m_wood('#7f5d3e', 'compw', age=1.5, grime=(-1, -0.9)); E.layer(W, E.grime(0.12, 0.6)); E.layer(W, E.base_moss(0.2, 0.9, back=(0.0, 1.2)))
    cx, cy, s = 1.3, 0.6, 0.3            # köşe dikmesi döndürülmüş sınır kutusunu büyütmesin (bölge −10°)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox('comppost', (cx + sx * s / 2, cy + sy * s / 2, 0.17), (0.04, 0.04, 0.34), W, bevel=0.005)
    for k in range(3):
        z = 0.06 + k * 0.1
        for side in range(4):
            if side % 2 == 0:
                AT.plank('compslat', (cx, cy + (-1 if side == 0 else 1) * (s / 2 + 0.01), z), (s, 0.016, 0.065), W, seed=side * 3 + k, amt=0.004)
            else:
                AT.plank('compslat', (cx + (-1 if side == 3 else 1) * (s / 2 + 0.01), cy, z), (0.016, s, 0.065), W, seed=side * 3 + k + 20, amt=0.004)
    o = E.sand_mound(cx, cy, s * 0.47, s * 0.47, 0.1, 5, m=AT.m_soil('compostm'), name='compost', n=14, rings=3)
    o.location.z = 0.2
    GR = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'clippings'); BR = m_leaf('#7a5a2a', '#9a7a3a', '#b89a5a', '#c8aa6a', 'deadleaf')
    def clips(bm):
        out = []
        for k in range(16):
            a = R.uniform(0, 6.28); r = R.uniform(0, s * 0.35)
            p = V((cx + math.cos(a) * r, cy + math.sin(a) * r, 0.2 + 0.1 * (1 - (r / (s * 0.47)) ** 2) * 0.9))
            b = R.uniform(0, 6.28); d = V((math.cos(b), math.sin(b), R.uniform(0.1, 0.5))).normalized(); side = V((-math.sin(b), math.cos(b), 0))
            for f in blade(bm, p, d, side, R.uniform(0.06, 0.1), 0.02, 0.2, segs=2): out.append((f, k % 2))
        return out
    mesh_from_blades('clippings', clips, [GR, BR])
    BN = m_flat('#f0c83a', 0.12, 10, 'peel')
    for k in range(3):
        a = k * 2.1 + 0.4
        tube('peel', [(cx + 0.03, cy - 0.02, 0.33), (cx + 0.03 + math.cos(a) * 0.05, cy - 0.02 + math.sin(a) * 0.05, 0.32), (cx + 0.03 + math.cos(a) * 0.08, cy - 0.02 + math.sin(a) * 0.08, 0.3)], [0.012, 0.014, 0.006], BN, res=2)


def fence():
    """Arka çit: boyası dökük krem çıtalar (biri eksik, biri yamuk), iki kat kiriş, yosunlu uç direkleri."""
    R = random.Random(13)
    PK = m_wood('#c9a77a', 'picket', paint='#f4e6c6', age=1.4, grime=(-1, -0.9))
    E.layer(PK, E.grime(0.16, 0.55)); E.layer(PK, E.base_moss(0.18, 0.8, back=(0.6, 1.2)))
    for k in range(11):
        if k == 7: continue
        x = -1.25 + k * 0.25
        lean = 7 if k == 2 else R.uniform(-2.5, 2.5)
        AT.prism('picket', [(-0.05, 0), (0.05, 0), (0.05, 0.42), (0, 0.48), (-0.05, 0.42)], 0.03, PK, loc=(x, 1.12, -0.02), rot=(0, lean, 0), bevel=0.006)
    for z in (0.12, 0.32):
        AT.plank('prail', (0, 1.14, z), (2.65, 0.03, 0.05), PK, seed=int(z * 100))
    PO = m_wood('#8a6646', 'fencepost', age=1.4, grime=(-1, -0.9)); E.layer(PO, E.base_moss(0.25, 0.9, back=(0.5, 1.2)))
    for s in (-1, 1):
        AT.plank('fpost', (s * 1.36, 1.14, 0.25), (0.06, 0.06, 0.56), PO, seed=s + 30, amt=0.004)
        AT.moss_cap((s * 1.36, 1.14, 0.53 + 0.01), 0.04, seed=s + 7)
        E.moss_clump((s * 1.36, 1.17, 0.0), 0.05, seed=s + 12, n=2)


def build():
    beds(); left_bed(); right_bed(); path_and_signs(); watering_can(); tool_rack(); compost(); fence()
    before = set(bpy.context.scene.objects.keys())
    AT.dress(1.55, 41, n_tufts=8, flowers=5, pebbles=2, bushes=[(-1.35, 0.6), (1.35, -0.85)],
             exclude=lambda x, y: abs(x) < 1.15 and abs(y) < 1.15)
    def under(x, y):
        return (abs(x - 1.34) < 0.25 and (-0.62 < y < 0.24 or 0.4 < y < 0.85)) or (abs(x + 1.3) < 0.25 and abs(y + 0.85) < 0.22)
    print('silinen dip süsü', E.clear_area(before, under), flush=True)


DECIM = [
    (r'^(bedboard|bedpost|rackpost|rackbar|compslat|prail|fpost|trpost)$', 0.06), (r'^soil$', 0.6), (r'^(picket)$', 0.3),
    (r'^(carrot|cabheart|tom)$', 0.16), (r'^beanfl$', 0.4), (r'^(vine|beanvine|sstem|stake|melonvine|scpole|scarm)$', 0.3),
    (r'^(pod|peel|spout|canhandle|rakehandle|spadehandle|hoehandle|scmouth)$', 0.3), (r'^(melon|coconut)$', 0.18),
    (r'^(shirt)$', 0.3), (r'^(sleeve)$', 0.4), (r'^(hatcrown|hatbrim)$', 0.6), (r'^(hatband|scbelt|tie|canrim|spadegrip)$', 0.5),
    (r'^(pathstone)$', 0.3), (r'^(mossclump|moss)$', 0.1), (r'^(nail|streak)$', 0.3), (r'^(pet|fc)$', 0.4), (r'^stem$', 0.4),
    (r'^Icosphere$', 0.3), (r'^lush$', 0.5), (r'^rosette$', 0.5), (r'^(sundisc|rose|can)$', 0.55), (r'^(rosehole)$', 0.5),
    (r'^(trslat|trtop|rackpeg|rakehead|raketooth|hoeblade|hoeneck|comppost|pkstake)$', 0.22), (r'^(bedsand|cansand|racksand)$', 0.6),
    (r'^(sceye|sccheek)$', 0.25),
]
WEIGHTS = [
    (r'^(packet|pkicon|pkleaf)$', 2.5), (r'^(shirt|sleeve|coconut|sceye|sccheek|scmouth|hatbrim|hatcrown|hatband)$', 1.6),
    (r'^(can|spout|rose|canrim|canhandle)$', 1.5), (r'^(bedboard|bedpost)$', 1.15), (r'^(sundisc|sunpetals)$', 1.4),
    (r'^(soil)$', 0.7), (r'^(lush|rosette|wornground|bedsand|cansand|racksand|clippings|compost)$', 0.55),
]


if __name__ == '__main__':
    out, dr, yaw = E.args()
    kit.reset(); build(); hi = E.BK.prepare()
    print('taslak üçgen', E.BK.tri_count(hi), 'nesne', len(hi), flush=True)
    if dr:
        E.draft(dr, yaw)
    else:
        # kafes 1,2 cm: toprağa yakın yaprakların (lahana, korkuluk eteği) altında ışın yaprağa çarpıp toprağı karartıyordu
        E.bake(out, NAME, hi, DECIM, WEIGHTS, CAP, cage=0.012, ray=0.1)
