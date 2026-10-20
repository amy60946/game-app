# Bahçe v4 (20 Ekim 2026, kullanıcı geri bildirimi; ÖN TASARIM — onay bekliyor, oyuna girmedi):
# kazılmış gerçekçi toprak (sıra tümsekleri, topak, çakıl), daha büyük alan (3 tarh), kıvrımları net bitkiler
# (domates, havuç, mısır, karpuz), yıpranmış ahşap kasa ve çit + kesik uçlarda yıllık halka, kıvrımlı sulama kabı.
# Kullanım: /tmp/claude-0/bpyenv/bin/python garden_v4.py -- <çıktı_klasörü> [hepsi|genel|bitki|ahsap|kap|yatak]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from kit import *
import kit
import assets_v3 as A
from assets_v3 import m_wood, m_rock, m_leaf, m_flat, _shade, mesh_from_blades, blade, smooth, link_mesh, pebble, rosette
from assets_town import m_metal, m_treebark, plank, wobble, lathe, lush, dress
import bmesh, mathutils
from mathutils import Vector as V, noise as mnoise

R = random.Random(20)

# ------------------------------------------------------------------ malzemeler

def m_soil4(name='soil4', wet=False):
    """Kazılmış toprak: koyu nemli dipler, açık kuru topak tepeleri (normal z + gürültü), ince kum benekleri, saman kırıntısı."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        base = ('#2e1d10', '#4a301a', '#6b4a2c') if not wet else ('#1e130a', '#2f1f12', '#45301d')
        col = G.mix(G.rng(G.noise(o, 9, 8), 0.35, 0.7), base[0], base[1])
        col = G.mix(G.rng(G.nz(), 0.75, 0.98, 0, 0.6), col, base[2])               # yukarı bakan topak tepeleri açık
        col = G.mix(G.rng(G.noise(o, 60, 2), 0.66, 0.72, 0, 0.55), col, '#8a6a48')  # kum benekleri
        col = G.mix(G.rng(G.vor(o, 30, 'F1'), 0.04, 0.0, 0, 0.35), col, '#b89a62')  # saman/kök kırıntısı
        l.new(col, bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.55 if wet else 0.95
    return nodes_mat(name, b)

def m_endgrain(hexc='#c79a62', name='endgrain'):
    """Kesik uç: merkezden dışa yıllık halkalar (hafif dalgalı), koyu kabuk kenarı, ışınsal çatlaklar, güneşte grileşme."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.rings_direction = 'Z'
        wv.inputs['Scale'].default_value = 7.0; wv.inputs['Distortion'].default_value = 1.6; wv.inputs['Detail'].default_value = 2
        l.new(G.mapping(o, (1, 1, 0)), wv.inputs['Vector'])
        col = G.mix(G.rng(wv.outputs['Fac'], 0.2, 0.8), _shade(hexc, 0.78), _shade(hexc, 1.12))
        col = G.mix(G.rng(G.noise(o, 3, 3), 0.55, 0.75, 0, 0.35), col, '#9d9690')       # grileşme
        # ışınsal çatlak: açı yönünde uzatılmış hücre kenarı
        ck = G.vor(G.mapping(o, (14, 14, 1)), 1.0, 'DISTANCE_TO_EDGE')
        col = G.mix(G.math('MULTIPLY', G.rng(ck, 0.02, 0.0), 0.6), col, '#3a2616')
        l.new(col, bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.85
    return nodes_mat(name, b)

def m_stripes(c1, c2, name, scale=9.0):
    """Karpuz kabuğu: boyuna dalgalı koyu şeritler."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'
        wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 5; wv.inputs['Detail'].default_value = 2
        sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
        ang = n.new('ShaderNodeMath'); ang.operation = 'ARCTAN2'; l.new(sep.outputs['Z'], ang.inputs[0]); l.new(sep.outputs['Y'], ang.inputs[1])
        cmb = n.new('ShaderNodeCombineXYZ'); l.new(ang.outputs[0], cmb.inputs['X']); l.new(sep.outputs['X'], cmb.inputs['Y'])
        l.new(cmb.outputs[0], wv.inputs['Vector'])
        col = G.mix(G.rng(wv.outputs['Fac'], 0.45, 0.6), c1, c2)
        col = G.mix(G.rng(G.noise(o, 8, 4), 0.5, 0.7, 0, 0.25), col, _shade(c1, 1.3))
        l.new(col, bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.3; bsdf.inputs['Coat Weight'].default_value = 0.3
    return nodes_mat(name, b)

def m_kernels(name='kernels'):
    """Mısır koçanı: dizili tane hücreleri (voronoi), tane arası koyu çizgi, tepeye doğru açık."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        cells = G.vor(G.mapping(o, (34, 34, 22)), 1.0, 'DISTANCE_TO_EDGE')
        col = G.mix(G.rng(G.noise(o, 6, 2), 0.4, 0.7), '#f2b62a', '#ffd864')
        col = G.mix(G.rng(cells, 0.06, 0.0, 0, 0.8), col, '#a86e12')
        l.new(col, bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.35; bsdf.inputs['Coat Weight'].default_value = 0.4
    return nodes_mat(name, b)

def m_can(name='can4'):
    """Sulama kabı: turkuaz boya, kenarlarda pul pul dökülmüş (altında galvaniz gri), dipte toprak kiri, birkaç pas izi."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        paint = G.mix(G.rng(G.noise(o, 2, 4), 0.35, 0.7), '#2b958f', '#43b7ac')
        chips = G.math('ADD', G.noise(o, 7, 8, 0.6), G.math('MULTIPLY', G.edges(0.55, 0.65), 0.25))
        keep = G.rng(chips, 0.69, 0.66)
        col = G.mix(keep, '#a9adb0', paint)
        col = G.mix(G.rng(G.noise(G.mapping(o, (10, 10, 2)), 1.0, 3), 0.62, 0.72, 0, 0.5), col, '#a8643a')   # pas akıntısı
        col = A.weather(G, col, 0.8, (0.0, 0.12))
        l.new(col, bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.42; bsdf.inputs['Metallic'].default_value = 0.25
    return nodes_mat(name, b)

def m_rose(name='rose4'):
    """Süzgeç başlığı yüzü: delik delik (koyu noktalar)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        dots = G.vor(G.mapping(o, (60, 60, 60)), 1.0, 'F1')
        col = G.mix(G.rng(dots, 0.12, 0.2), '#1b1f22', '#9aa3a6')
        l.new(col, bsdf.inputs['Base Color']); bsdf.inputs['Metallic'].default_value = 0.6; bsdf.inputs['Roughness'].default_value = 0.35
    return nodes_mat(name, b)

# ------------------------------------------------------------------ parçalar

def cut_log(loc, r, h, seed, bark=None, ring=None, tilt=0.0):
    """Kesik kütük: kabuklu gövde + üstte yıllık halkalı kesik yüz (ayrı nesne: halkalar merkezli kalsın)."""
    bark = bark or m_treebark('bark4'); ring = ring or m_endgrain()
    o = cyl('logb', (loc[0], loc[1], loc[2] + h / 2), r, h, bark, verts=14, bevel=0.0)
    wobble(o, r * 0.06, 5.0, seed)
    top = cyl('ring', (loc[0], loc[1], loc[2] + h + 0.004), r * 0.93, 0.012, ring, verts=20, bevel=0.0)
    if tilt:
        for ob in (o, top): ob.rotation_euler = (math.radians(tilt), 0, 0)
    return o, top

def post_ring(x, y, z0, h, r, wood, ring, seed):
    """Kare-yuvarlak köşe direği + üstte halkalı kesik uç."""
    o = cyl('post', (x, y, z0 + h / 2), r, h, wood, verts=10, bevel=0.0)
    wobble(o, 0.006, 4.0, seed)
    cyl('pring', (x, y, z0 + h + 0.003), r * 0.94, 0.01, ring, verts=16, bevel=0.0)
    return o

def soil_bed(cx, cy, w, d, rows, mat, seed):
    """Kazılmış toprak yüzeyi: sıra tümsekleri (sinüs), aralarında oluk, gürültülü topaklık; üstüne topak + çakıl serpintisi."""
    nx, ny = 40, int(40 * d / w)
    bm = bmesh.new()
    vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -w / 2 + w * i / nx; y = -d / 2 + d * j / ny
            ridge = 0.5 + 0.5 * math.cos(2 * math.pi * (x + w / 2) / (w / rows) + math.pi)   # 1 = sıra tepesi
            edge = min(1.0, (w / 2 - abs(x)) / 0.06, (d / 2 - abs(y)) / 0.06)
            z = 0.05 * ridge * edge + 0.012 * mnoise.noise(V((x * 9 + seed, y * 9, 0))) + 0.006 * mnoise.noise(V((x * 30, y * 30 + seed, 0)))
            row.append(bm.verts.new((cx + x, cy + y, 0.2 + z)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    o = link_mesh('soil', bm, [mat]); smooth(o)
    # topaklar ve çakıllar
    STN = m_rock()
    for k in range(int(w * d * 40)):
        x = cx + R.uniform(-w / 2 + 0.04, w / 2 - 0.04); y = cy + R.uniform(-d / 2 + 0.04, d / 2 - 0.04)
        r = R.uniform(0.012, 0.03)
        c = blob('clod', (x, y, 0.235), (r * 1.3, r, r * 0.7), mat, rot=(0, 0, R.uniform(0, 180)), sub=0, seg=8)
        wobble(c, r * 0.3, 40.0, k)
    for k in range(int(w * d * 8)):
        x = cx + R.uniform(-w / 2 + 0.05, w / 2 - 0.05); y = cy + R.uniform(-d / 2 + 0.05, d / 2 - 0.05)
        pebble((x, y, 0.235), R.uniform(0.012, 0.022), STN, 300 + k)
    return o

def raised_bed(cx, cy, w, d, wood, ring, seed):
    """Yıpranmış ahşap kasa: iki sıra tahta (yamuk, ezik, çatlak), köşede halkalı kesik direk, bir tahtanın ucu kırık."""
    for z in (0.06, 0.17):
        for sy in (-1, 1):
            plank('bedb', (cx, cy + sy * (d / 2 + 0.02), z), (w + 0.08, 0.04, 0.1), wood, seed=seed + z * 10 + sy, amt=0.008)
        for sx in (-1, 1):
            plank('bedb', (cx + sx * (w / 2 + 0.02), cy, z), (0.04, d, 0.1), wood, seed=seed + z * 20 + sx, amt=0.008)
    for sx in (-1, 1):
        for sy in (-1, 1):
            post_ring(cx + sx * (w / 2 + 0.03), cy + sy * (d / 2 + 0.03), 0.0, 0.29, 0.045, wood, ring, seed + sx * 3 + sy)

def tomato_plant(x, y, h, seed):
    """Domates: sırığa sarılı kıvrımlı gövde, bileşik (lobu) yapraklar, yeşil-turuncu-kırmızı meyveler + yıldız çanak."""
    Rr = random.Random(seed)
    ST = m_wood('#a8693d', 'stake4', age=1.4)
    tube('stake', [(x + 0.06, y, 0.18), (x + 0.065, y, h + 0.15)], [0.016, 0.014], ST, res=2)
    stem = [(x + math.cos(t * 7) * 0.035, y + math.sin(t * 7) * 0.035, 0.22 + t * h) for t in [i / 12 for i in range(13)]]
    tube('tstem', stem, [0.016 - i * 0.0006 for i in range(13)], m_flat('#4a8a32', 0.15, 8, 'tstem4'), res=3)
    TL = m_leaf('#2a6f2e', '#468f3c', '#7fbf55', '#a7d67c', 'tomleaf4')
    def leaves(bm):
        out = []
        for k in range(9):
            a = k * 2.4 + Rr.uniform(-0.2, 0.2); z = 0.3 + k * h / 10
            base = V((x + math.cos(k * 7 / 12 * 6) * 0.03, y + math.sin(k * 7 / 12 * 6) * 0.03, z))
            d = V((math.cos(a), math.sin(a), 0.25)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            # yaprak sapı boyunca 3 çift lob + uç lob (bileşik domates yaprağı)
            for q in range(4):
                p = base + d * (0.04 + q * 0.045)
                if q < 3:
                    for sgn in (-1, 1):
                        dd = (d * 0.4 + side * sgn).normalized() + V((0, 0, 0.1))
                        for f in blade(bm, p, dd.normalized(), d.cross(V((0, 0, 1))).normalized(), 0.07 - q * 0.008, 0.028, 0.4, segs=3): out.append((f, 0))
                else:
                    for f in blade(bm, p, d, side, 0.08, 0.032, 0.5, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('tleaves', leaves, [TL])
    COLS = [m_flat('#e33c33', 0.12, 12, 'tomR'), m_flat('#f08a2a', 0.12, 12, 'tomO'), m_flat('#8cc04a', 0.12, 12, 'tomG')]
    SEP = m_leaf('#2f7a2e', '#4a9a3a', '#6fbf4f', '#8fd06a', 'sepal')
    for k in range(6):
        a = k * 2.2; zz = 0.38 + k * h / 8
        p = V((x + math.cos(a) * 0.09, y + math.sin(a) * 0.09, zz))
        r = Rr.uniform(0.045, 0.06)
        tm = blob('tom', tuple(p), (r, r, r * 0.82), COLS[k % 3] if k > 1 else COLS[0], sub=1, seg=14)
        wobble(tm, r * 0.06, 12.0, k)
        def sep(bm, p=p, r=r):
            out = []
            for q in range(5):
                b_ = q * 2 * math.pi / 5
                d = V((math.cos(b_), math.sin(b_), 0.15)).normalized(); side = V((-math.sin(b_), math.cos(b_), 0))
                for f in blade(bm, p + V((0, 0, r * 0.78)), d, side, r * 0.75, r * 0.22, 0.6, segs=2): out.append((f, 0))
            return out
        mesh_from_blades('sepals', sep, [SEP])

def carrot_row(x0, y0, y1, n, seed):
    """Havuç: topraktan çıkan turuncu omuz (halka çizgili) + tüy gibi ince bölünmüş yapraklar."""
    Rr = random.Random(seed)
    CAR = m_flat('#ee7424', 0.18, 14, 'carrot4')
    FR = m_leaf('#2f7f2c', '#4ea33c', '#8cd05a', '#b5e581', 'frond4')
    spots = [(x0 + Rr.uniform(-0.015, 0.015), y0 + (y1 - y0) * k / (n - 1)) for k in range(n)]
    for (x, y) in spots:
        c = blob('cshoulder', (x, y, 0.235), (0.035, 0.035, 0.045), CAR, sub=1, seg=12)
    def fronds(bm):
        out = []
        for (x, y) in spots:
            for k in range(6):
                a = k * 1.05 + Rr.uniform(0, 0.5); up = Rr.uniform(0.72, 0.92)
                d = V((math.cos(a) * (1 - up), math.sin(a) * (1 - up), up)).normalized()
                side = V((-math.sin(a), math.cos(a), 0))
                base = V((x, y, 0.27)); L = Rr.uniform(0.2, 0.28)
                for f in blade(bm, base, d, side, L, 0.006, 0.35, segs=3): out.append((f, 0))      # sap
                for q in range(4):                                                                       # tüy dalcıkları
                    p = base + d * (L * (0.35 + q * 0.17)) + V((0, 0, -0.35 * L * (0.35 + q * 0.17) ** 2))
                    for sgn in (-1, 1):
                        dd = (d * 0.5 + side * sgn * 0.9 + V((0, 0, 0.2))).normalized()
                        for f in blade(bm, p, dd, d.cross(V((0, 0, 1))).normalized(), 0.05 - q * 0.007, 0.012, 0.3, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('fronds', fronds, [FR])

def corn(x, y, h, seed):
    """Mısır: boğumlu sap, kemer gibi sarkan uzun yapraklar (orta damarlı), kılçıklı tepe püskülü, kabuk içinden görünen koçan + püskül."""
    Rr = random.Random(seed)
    SC = m_flat('#6fa83f', 0.15, 10, 'cornstalk')
    tube('cstalk', [(x, y, 0.2), (x + 0.01, y, h * 0.5), (x - 0.01, y + 0.01, h)], [0.03, 0.025, 0.014], SC, res=3)
    for k in range(4):   # boğum halkaları
        cyl('node', (x, y, 0.4 + k * h / 5.5), 0.032 - k * 0.003, 0.02, m_flat('#5a8f34', 0.15, 10, 'cornnode'), verts=10, bevel=0)
    CL = m_leaf('#3d8a33', '#5fab42', '#a5d567', '#cdeb98', 'cornleaf')
    def leaves(bm):
        out = []
        for k in range(8):
            a = k * 2.6 + Rr.uniform(-0.3, 0.3); z = 0.35 + k * (h - 0.4) / 8
            d = V((math.cos(a) * 0.7, math.sin(a) * 0.7, 0.75)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V((x, y, z)), d, side, Rr.uniform(0.45, 0.65), 0.045, 1.3, segs=6): out.append((f, 0))
        return out
    mesh_from_blades('cleaves', leaves, [CL])
    TS = m_flat('#d8b45a', 0.2, 20, 'tassel')
    for k in range(7):
        a = k * 0.9
        tube('tassel', [(x - 0.01, y + 0.01, h), (x + math.cos(a) * 0.06, y + math.sin(a) * 0.06, h + 0.12), (x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, h + 0.08)],
             [0.004, 0.003, 0.002], TS, res=2)
    # koçan: sapın yanında eğik, kabuk yaprakları arasından taneler, tepede kahverengi püskül
    cz = h * 0.55
    cob = blob('cob', (x + 0.06, y - 0.02, cz), (0.032, 0.032, 0.11), m_kernels(), rot=(0, 22, 0), sub=1, seg=16)
    HK = m_leaf('#7fae4f', '#a2c76a', '#cfe39a', '#e5f0c0', 'husk')
    def husk(bm):
        out = []
        base = V((x + 0.04, y - 0.02, cz - 0.1))
        for q in range(5):
            a = q * 2 * math.pi / 5
            d = V((math.sin(math.radians(22)) + math.cos(a) * 0.25, math.sin(a) * 0.25, 1)).normalized()
            side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, base + V((math.cos(a) * 0.025, math.sin(a) * 0.025, 0)), d, side, 0.17, 0.035, -0.15, segs=4): out.append((f, 0))
        return out
    mesh_from_blades('husk', husk, [HK])
    SK = m_flat('#9a5a2a', 0.2, 20, 'silk')
    top = V((x + 0.06, y - 0.02, cz)) + V((math.sin(math.radians(22)) * 0.11, 0, 0.11))
    for k in range(6):
        a = k * 1.1
        tube('silk', [tuple(top), tuple(top + V((math.cos(a) * 0.03, math.sin(a) * 0.03, 0.04))), tuple(top + V((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.0)))],
             [0.003, 0.0025, 0.0015], SK, res=2)

def watermelon_patch(cx, cy, seed):
    """Karpuz: yerde kıvrılan sülükler, derin loblu geniş yapraklar, çizgili meyveler (biri yarım, kırmızı içli)."""
    Rr = random.Random(seed)
    VN = m_flat('#4c8a33', 0.15, 10, 'mvine')
    for k in range(4):
        a = k * 1.6
        pts = [(cx + math.cos(a + t) * (0.08 + t * 0.22), cy + math.sin(a + t) * (0.08 + t * 0.22), 0.235 + 0.01 * math.sin(t * 9)) for t in [i / 8 for i in range(9)]]
        tube('vine', pts, [0.008] * 9, VN, res=3)
        for q in range(3):   # sülük kıvrımı
            p = V(pts[2 + q * 2]); tw = [tuple(p + V((math.cos(s * 12) * 0.012, math.sin(s * 12) * 0.012, s * 0.03))) for s in [i / 6 for i in range(7)]]
            tube('tendril', tw, [0.0025] * 7, VN, res=2)
    ML = m_leaf('#2f7a33', '#4f9e40', '#8ac85c', '#a9d97d', 'mleaf')
    def leaves(bm):
        out = []
        for k in range(10):
            a = Rr.uniform(0, 6.28); rr = Rr.uniform(0.08, 0.32)
            base = V((cx + math.cos(a) * rr, cy + math.sin(a) * rr, 0.24))
            for lob in range(3):   # üç loblu yaprak
                b_ = Rr.uniform(0, 6.28) + lob * 0.9
                d = V((math.cos(b_), math.sin(b_), 0.45)).normalized(); side = V((-math.sin(b_), math.cos(b_), 0))
                for f in blade(bm, base, d, side, 0.09, 0.045, 0.3, segs=3, lift=0.1): out.append((f, 0))
        return out
    mesh_from_blades('mleaves', leaves, [ML])
    RIND = m_stripes('#1f5220', '#9ad46a', 'rind', scale=5.0)
    for k, (dx, dy, s) in enumerate(((0.12, -0.1, 1.0), (-0.16, 0.12, 0.8))):
        o = blob('melon', (cx + dx, cy + dy, 0.2 + 0.1 * s), (0.17 * s, 0.12 * s, 0.11 * s), RIND, rot=(0, 0, k * 40), sub=1, seg=20)
    # yarım karpuz: kırmızı iç + beyaz kabuk halkası + siyah çekirdek
    hx, hy = cx - 0.02, cy - 0.3
    blob('halfrind', (hx, hy, 0.24), (0.11, 0.11, 0.06), RIND, sub=1, seg=18)
    cyl('flesh', (hx, hy, 0.268), 0.1, 0.006, m_flat('#ef4a52', 0.12, 12, 'flesh'), verts=24, bevel=0)
    cyl('pith', (hx, hy, 0.266), 0.108, 0.004, m_flat('#f3f0d6', 0.05, 8, 'pith'), verts=24, bevel=0)
    for q in range(8):
        a = q * 0.78
        blob('seed', (hx + math.cos(a) * 0.05, hy + math.sin(a) * 0.05, 0.272), (0.008, 0.005, 0.003), m_flat('#1d1512', 0.1, 8, 'mseed'), rot=(0, 0, math.degrees(a)), sub=0, seg=8)

def watering_can(loc, yaw=0.0):
    """Sulama kabı: şişkin gövde (bel + taşkın ağız kenarı), uzun kavisli emzik, süzgeçli başlık, kemer sap + yan sap, bir ezik."""
    CAN = m_can(); x, y, z = loc
    body = lathe('canbody', [(0.001, 0.0), (0.12, 0.0), (0.14, 0.02), (0.155, 0.1), (0.15, 0.18), (0.13, 0.24), (0.115, 0.26), (0.12, 0.275), (0.001, 0.278)], CAN, segs=32)
    body.location = loc
    # ezik: ön yüzde küçük çöküntü
    for v in body.data.vertices:
        d = (v.co - V((0.13, -0.06, 0.12))).length
        if d < 0.06: v.co -= v.co.normalized() * (0.012 * (1 - d / 0.06))
    cyl('band', (x, y, z + 0.06), 0.152, 0.012, CAN, verts=32, bevel=0)
    cyl('band', (x, y, z + 0.2), 0.146, 0.012, CAN, verts=32, bevel=0)
    tube('spout', [(x + 0.12, y, z + 0.06), (x + 0.24, y, z + 0.14), (x + 0.33, y, z + 0.27), (x + 0.38, y, z + 0.36)], [0.022, 0.018, 0.015, 0.014], CAN, res=6)
    rose = lathe('rose', [(0.012, 0.0), (0.03, 0.025), (0.045, 0.04), (0.045, 0.045), (0.001, 0.046)], CAN, segs=24)
    rose.location = (x + 0.38, y, z + 0.355); rose.rotation_euler = (0, math.radians(52), 0)
    face = cyl('roseface', (x + 0.418, y, z + 0.385), 0.043, 0.004, m_rose(), verts=24, bevel=0)
    face.rotation_euler = (0, math.radians(52), 0)
    tube('handle', [(x - 0.11, y, z + 0.25), (x - 0.06, y, z + 0.4), (x + 0.06, y, z + 0.42), (x + 0.1, y, z + 0.27)], [0.014] * 4, CAN, res=6)
    tube('sidehandle', [(x - 0.15, y, z + 0.18), (x - 0.21, y, z + 0.14), (x - 0.15, y, z + 0.06)], [0.012] * 3, CAN, res=4)
    blob('drip', (x + 0.42, y, z + 0.33), (0.008, 0.008, 0.012), m_flat('#9fd8f0', 0.05, 8, 'drip'), sub=0, seg=8)

# ------------------------------------------------------------------ sahne

def build():
    WOOD = m_wood('#8a5a34', 'bed4', age=1.7, grime=(0.0, 0.25)); RING = m_endgrain()
    SOIL = m_soil4(); WET = m_soil4('wet4', wet=True)
    # zemin: çim + patika
    ground(r=9, hexcol='#79b257')
    beds = [(-1.15, 0.0, 0.9, 1.9), (0.0, 0.0, 0.9, 1.9), (1.15, 0.0, 0.9, 1.9)]   # 3 tarh: alan v3'e göre ~%60 büyük
    for i, (bx, by, bw, bd) in enumerate(beds):
        raised_bed(bx, by, bw, bd, WOOD, RING, 10 + i)
        soil_bed(bx, by, bw, bd, 3, WET if i == 1 else SOIL, i * 7)
    # bitkiler
    for j in range(3): tomato_plant(-1.35 + (j % 2) * 0.35, -0.6 + j * 0.6, 0.75, 40 + j)
    carrot_row(-0.28, -0.75, 0.75, 6, 50); carrot_row(0.0, -0.75, 0.75, 6, 51)
    corn(0.27, -0.55, 1.35, 60); corn(0.27, 0.35, 1.45, 61)
    watermelon_patch(1.15, 0.35, 70); watermelon_patch(1.15, -0.5, 71)
    # sulama kabı, kütük tabureler (halkalı), patika taşları, çit
    watering_can((-1.95, -1.35, 0.0))
    BARK = m_treebark('bark4')
    cut_log((1.85, -1.3, 0), 0.17, 0.32, 5, BARK, RING); cut_log((2.15, -1.05, 0), 0.13, 0.22, 6, BARK, RING)
    STN = m_rock()
    for k in range(9):   # önde basamak taşlı patika
        o = pebble((-1.7 + k * 0.42 + R.uniform(-0.05, 0.05), -1.38 + R.uniform(-0.05, 0.05), 0.02), 0.14, STN, 90 + k); o.scale = (1.0, 0.8, 0.3)
    PK = m_wood('#bfa078', 'picket4', paint='#efe2c2', age=1.8)
    for k in range(15):
        xk = -1.85 + k * 0.265
        o = plank('picket', (xk, 1.32, 0.27), (0.085, 0.03, 0.5), PK, rot=(0, R.uniform(-4, 4), 0), seed=200 + k, amt=0.006)
        cyl('pcap', (xk, 1.32, 0.525), 0.03, 0.01, RING, verts=12, bevel=0).rotation_euler = (math.radians(90), 0, 0)
    for z in (0.12, 0.38):
        plank('prail', (0.0, 1.35, z), (3.9, 0.03, 0.06), PK, seed=int(z * 100), amt=0.01)
    for xk in (-1.98, 0.0, 1.98):
        post_ring(xk, 1.37, 0.0, 0.62, 0.05, WOOD, RING, int(xk * 10) + 99)
    lush((0, 0, 0.0), 3.4, 70, 77, h=(0.12, 0.28))
    A.flower_heads([(-2.3, 0.6, 0.2), (2.4, 0.9, 0.22), (-2.1, -0.4, 0.18), (2.5, -0.2, 0.2), (0.9, 1.6, 0.24), (-0.9, 1.65, 0.22)], R)
    return beds

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    OUT = args[0] if args else '.'; what = args[1] if len(args) > 1 else 'hepsi'
    os.makedirs(OUT, exist_ok=True)
    sc = reset(); sc.cycles.samples = int(os.environ.get('SAMPLES', '48')); sc.view_settings.exposure = -0.45
    build(); to_mesh_all()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and 'grain' not in o.data.uv_layers: grain_uv(o)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name != 'ground']
    print('UCGEN_TAM', tri_count(objs), flush=True)
    shots = {
        'genel': ((0, -0.1, 0.35), 7.4, -32, 34, 40, (1280, 800)),
        'bitki': ((0.2, -0.35, 0.45), 2.9, -18, 22, 45, (1280, 800)),
        'ahsap': ((1.95, -1.15, 0.25), 1.6, -40, 30, 50, (1024, 1024)),
        'kap': ((-1.8, -1.35, 0.2), 1.3, 8, 14, 50, (1024, 1024)),
        'yatak': ((0.0, -0.4, 0.22), 1.9, -10, 38, 45, (1280, 800)),
    }
    for k, (t, dist, yaw, pitch, lens, size) in shots.items():
        if what not in ('hepsi', k): continue
        shoot(sc, os.path.join(OUT, f'garden_v4_{k}.png'), t, dist, yaw, pitch, lens, size)
        print('YAZILDI', k, flush=True)
