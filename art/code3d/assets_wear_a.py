# Komik giyilebilir baş eşyaları A (kullanıcı, 23 Ekim 2026: F1–F17'nin kodla yapılanları) — pervaneli bere (+ dönen pervane),
# pasta şapka, karpuz şapka, yamuk taç, kova şapka. Aynı tasarım dili (assets_items / assets_town): dokulu kumaş, krema,
# yumuşak AO + Meshy eşyalarının parlak "vinyl oyuncak" havası (pişmiş yumuşak parlama lekesi). Dış çizgi yok; özgün tasarımlar.
# Yön: ön = −Y, yukarı = +Z. Birim: şapka genişliği ≈ 1 (oyun boy = kural × pet boyu / max(x, y)); alt = başın tepesine oturan
# açık/içbükey ağız (çocuk Okti'nin kubbe başı, oturma kuralı: alt, baş tepesinin 0,14 × boy altında).
# Kullanım: python -I assets_wear_a.py -- <çıktı_klasörü> [w_hat_cake ...]   (oyuna: export_game.py hat_cake)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets_town import *
import assets_town as T
import assets_v3 as A
from assets_v3 import _shade
from assets_items import m_fabric
import mathutils
from mathutils import Vector as V, Matrix, noise as mnoise

# ------------------------------------------------------------------ ortak: baş kubbesi (şapka birimi, genişlik 1 ≈ 0,62 × pet boyu)
# çocuk Okti'de ölçüldü (head_prof): şapka altından yukarı (z, yarıçap); oyuncak başın tepesi z ≈ 0,23
HEAD = [(0.0, 0.374), (0.048, 0.34), (0.097, 0.31), (0.145, 0.28), (0.194, 0.22), (0.226, 0.16), (0.235, 0.0)]

def cavity(scale=1.06, r0=None):
    """Şapka içi oyuk profili (r, z), ağızdan tepeye: baş kubbesinin biraz dışı (baş şapkadan taşmaz)."""
    out = [(r * scale + 0.01 if r > 0 else 0.0, z * scale + 0.012) for (z, r) in HEAD]
    if r0: out[0] = (r0, 0.0)
    return out

def cavity_down(scale=1.06, rim=None):
    """Oyuk yüzeyi tepeden ağıza (yüz normali başa/aşağı bakar). rim: (r, z) ağız kenarına bağlanacak son nokta."""
    out = list(reversed(cavity(scale)))
    return out + ([rim] if rim else [])

L_DIR = V((-0.45, -0.55, 0.70)).normalized()     # pişmiş parlama ışığı: sol-ön-üst (simge ve oyun kamerasıyla uyumlu)

def _dot_light(G):
    geo = G.n.new('ShaderNodeNewGeometry'); dp = G.n.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'
    G.l.new(geo.outputs['Normal'], dp.inputs[0]); dp.inputs[1].default_value = L_DIR
    return dp.outputs['Value']

def vinyl(G, col, hexc, hl=0.5, top=0.16, low=0.14, lo=0.9, hi=0.985):
    """Vinyl oyuncak yüzeyi: üst yüzler hafif açık, alt yüzler hafif koyu, sol-üstte yumuşak parlama lekesi (pişer)."""
    nz = G.nz()
    col = G.mix(G.rng(nz, 0.15, 1.0, 0, top), col, _shade(hexc, 1.18))
    col = G.mix(G.rng(nz, -0.1, -1.0, 0, low), col, _shade(hexc, 0.72))
    if hl: col = G.mix(G.rng(_dot_light(G), lo, hi, 0, hl), col, '#fffaf0')
    return col

def m_plastic(hexc, name=None, hl=0.5, var=0.06):
    """Parlak plastik (pervane, kova, mum): düz renk + çok hafif dalgalanma + vinyl parlaması."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(var, hexc, G.noise(o, 5, 2, out='Color'), 'OVERLAY')
        col = vinyl(G, col, hexc, hl)
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name or ('pl' + hexc), b)

def m_gold(name='wgold'):
    """Karikatür altın: aşağı bakan amber, yatay sarı altın, yukarı bakan açık; sol-üstte parlak leke; girintide koyu."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        rp = ramp(nt, [(0.0, '#9a5f16'), (0.42, '#e0a12e'), (0.7, '#f6c544'), (1.0, '#ffe68a')])
        f = G.math('ADD', G.math('MULTIPLY', G.nz(), 0.5), 0.5)
        f = G.math('ADD', f, G.math('MULTIPLY', G.noise(o, 3.5, 3), 0.18))
        G.l.new(f, rp.inputs['Fac'])
        col = G.mix(G.rng(_dot_light(G), 0.88, 0.98, 0, 0.75), rp.outputs[0], '#fff6d0')
        col = G.mix(G.rng(G.noise(o, 18, 3), 0.6, 0.75, 0, 0.12), col, '#b87a22')      # dövme izleri (hafif)
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_gem(hexc, name=None):
    """İri yuvarlak taş (kaboşon): ortası canlı, kenara doğru koyu, sol-üstte beyaz parlama."""
    def b(nt, bsdf):
        G = A._G(nt)
        d = _dot_light(G)
        col = G.mix(G.rng(d, -0.2, 0.75), _shade(hexc, 0.62), _shade(hexc, 1.12))
        col = G.mix(G.rng(d, 0.88, 0.97, 0, 0.9), col, '#ffffff')
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name or ('gem' + hexc), b)

PALETTE6 = ['#ff6f91', '#ffd447', '#58b8f0', '#7ed36a', '#ff9a4a', '#b48cf0']

def m_frost(hexc, name=None, sprinkles=0.0, hl=0.45):
    """Krema / şeker hamuru: yumuşak renk, çok hafif dalga, parlak leke; sprinkles > 0 ise rengârenk boncuk serpintisi (doku)."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj(); n = nt.nodes; l = nt.links
        col = G.mix(G.rng(G.noise(o, 4, 3), 0.3, 0.7), _shade(hexc, 0.95), _shade(hexc, 1.04))
        if sprinkles:
            vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 34; vo.inputs['Randomness'].default_value = 0.9
            l.new(o, vo.inputs['Vector'])
            sep = n.new('ShaderNodeSeparateColor'); l.new(vo.outputs['Color'], sep.inputs[0])
            rp = ramp(nt, [(k / 6, c) for k, c in enumerate(PALETTE6)], 'CONSTANT'); l.new(sep.outputs[0], rp.inputs['Fac'])
            dot = G.rng(vo.outputs['Distance'], 0.16, 0.12)
            keep = G.rng(sep.outputs[1], 1.0 - sprinkles - 0.02, 1.0 - sprinkles)
            col = G.mix(G.math('MULTIPLY', dot, keep), col, rp.outputs[0])
        col = vinyl(G, col, hexc, hl, top=0.08, low=0.12)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name or ('fr' + hexc + str(sprinkles)), b)

# ------------------------------------------------------------------ ortak geometri

def revolve(name, prof, mats, segs=64, rfun=None, mfun=None, closed=False, a0=0.0):
    """Profil (r, z) döndürülerek yüzey. rfun(a, i, r, z) → r (yarıçap kıvrımı), mfun(a, i) → malzeme sırası.
    r == 0 olan uç tek köşe (kutup). closed: son satır ilke bağlanır (halka kesiti, saat yönü tersine → normal dışa).
    Yüz normali profil yönünden: yukarı/içe yürüyen dış profil → dışa; tepeden ağıza inen oyuk profili → başa bakar."""
    bm = bmesh.new(); rows = []
    for i, (r, z) in enumerate(prof):
        if r <= 1e-6 and not closed:
            rows.append([bm.verts.new((0, 0, z))]); continue
        row = []
        for j in range(segs):
            a = a0 + j / segs * 2 * math.pi
            rr = rfun(a, i, r, z) if rfun else r
            row.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
        rows.append(row)
    n = len(rows); pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if closed else [])
    for (i, k) in pairs:
        A_, B_ = rows[i], rows[k]
        for j in range(segs):
            j2 = (j + 1) % segs; am = a0 + (j + 0.5) / segs * 2 * math.pi
            if len(A_) == 1: vs = (A_[0], B_[j2], B_[j])
            elif len(B_) == 1: vs = (A_[j], A_[j2], B_[0])
            else: vs = (A_[j], A_[j2], B_[j2], B_[j])
            try: f = bm.faces.new(vs)
            except ValueError: continue
            if mfun: f.material_index = mfun(am, i)
    o = link_mesh(name, bm, mats); smooth(o)
    return o

def ang_dist(a, b):
    d = (a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)

def paddle(name, root, d, L, W, T_, m, pitch=0.0, lift=0.0, seg=20):
    """Pervane kanadı / kürek: dipte dar, uçta geniş yuvarlak, ince; d yönünde, kendi ekseninde pitch kadar burulmuş."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1)
    o = bpy.context.object; o.name = name
    for v in o.data.vertices:
        x, y, z = v.co
        u = (x + 1) / 2                                        # 0 dip, 1 uç
        tw = 0.34 + 0.66 * (math.sin(min(1.0, u * 1.25) * math.pi / 2) ** 1.4)
        v.co = V((u * L, y * W / 2 * tw, z * T_ / 2 * (0.6 + 0.4 * tw)))
        v.co.z += lift * (u ** 2) * L                           # uca doğru hafif kalkık (dihedral)
    rot = Matrix.Rotation(pitch, 4, 'X')
    yaw = math.atan2(d[1], d[0])
    mw = Matrix.Translation(V(root)) @ Matrix.Rotation(yaw, 4, 'Z') @ rot
    o.data.transform(mw)
    o.data.materials.append(m); smooth(o)
    return o

def tilt_all(objs, ang_deg, pivot, axis='Y'):
    R = Matrix.Translation(V(pivot)) @ Matrix.Rotation(math.radians(ang_deg), 4, axis) @ Matrix.Translation(-V(pivot))
    bpy.context.view_layer.update()
    for o in objs: o.matrix_world = R @ o.matrix_world

def drips(name, r_edge, z_top, m, segs=160, tongues=14, seed=0, dmin=0.02, dmax=0.12, edge_r=0.028, cover=0.0, out=0.012, thick=0.012):
    """Damlayan krema/sır: üst diski örter (cover: iç yarıçap, 0 = tam disk), yuvarlak kenardan yan duvara iner; dil dil uzayan,
    uçları yuvarlak damlalar. Kalınlık (solidify) dil kenarında görünür."""
    R = random.Random(seed)
    T_ = [(2 * math.pi * (k + R.uniform(-0.3, 0.3)) / tongues, R.uniform(0.35, 0.75) * 2 * math.pi / tongues / 2, R.uniform(0.35, 1.0)) for k in range(tongues)]
    def depth(a):
        d = 0.0
        for (ak, wk, lk) in T_:
            x = ang_dist(a, ak) / wk
            if x < 1: d = max(d, lk * math.sqrt(1 - x * x))
        return dmin + (dmax - dmin) * d
    rows = 26; bm = bmesh.new(); ds = bm.faces.layers.int.new('ds')
    grid = []
    re = r_edge + out
    top_len = re - edge_r - cover; arc_len = edge_r * math.pi / 2
    center = bm.verts.new((0, 0, z_top + out * 0.6)) if cover <= 0 else None
    for j in range(segs):
        a = j / segs * 2 * math.pi; dd = depth(a); total = top_len + arc_len + dd
        col = []
        for i in range(rows + 1):
            s = total * (i / rows) ** 0.85 if i else 0.0
            if s <= top_len: r, z = cover + s, z_top + out * 0.6
            elif s <= top_len + arc_len:
                t = (s - top_len) / edge_r; r = re - edge_r + math.sin(t) * edge_r; z = z_top + out * 0.6 - edge_r + math.cos(t) * edge_r
            else: r, z = re, z_top + out * 0.6 - edge_r - (s - top_len - arc_len)
            col.append(center if (i == 0 and center is not None) else bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        grid.append(col)
    for j in range(segs):
        j2 = (j + 1) % segs
        for i in range(rows):
            vs = (grid[j][i], grid[j][i + 1], grid[j2][i + 1]) if (i == 0 and center is not None) else (grid[j][i], grid[j][i + 1], grid[j2][i + 1], grid[j2][i])
            try: bm.faces.new(vs)
            except ValueError: pass
    o = link_mesh(name, bm, [m]); smooth(o)
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = thick; s.offset = -1; s.use_even_offset = True
    # dil uçlarında tombul damla
    for (ak, wk, lk) in T_:
        if lk > 0.55:
            dd = dmin + (dmax - dmin) * lk; rr = 0.011 + 0.008 * lk
            z = z_top + out * 0.6 - edge_r - dd + rr * 0.6
            blob('drop', (math.cos(ak) * (re - 0.003), math.sin(ak) * (re - 0.003), z), (rr, rr, rr * 1.15), m, sub=0, seg=12)
    return o

# ------------------------------------------------------------------ 1. pervaneli bere

def _propeller(part):
    """Dilimli yumuşak kumaş bere (6 dilim: kırmızı, sarı, mavi), yeşil kıvrık bant, tepede yeşil kumaş düğme + sarı kısa sap.
    part='spin': yalnız göbek + 2 parlak plastik kanat (göbek dikey eksende, kanatlar karşılıklı → kendi ekseninde dengeli)."""
    TOPZ = 0.53; STEM = 0.085
    hub_z = TOPZ + 0.02 + STEM
    if part == 'spin':
        HUB = m_plastic('#ffcf3a', 'phub', hl=0.6); RB = m_plastic('#ff4b3e', 'pblade_r', hl=0.6); BB = m_plastic('#3c8df0', 'pblade_b', hl=0.6)
        T.lathe('hub', [(0.001, hub_z - 0.035), (0.062, hub_z - 0.035), (0.072, hub_z - 0.012), (0.07, hub_z + 0.016), (0.05, hub_z + 0.034), (0.001, hub_z + 0.038)], HUB, segs=28)
        blob('hubcap', (0, 0, hub_z + 0.04), (0.034, 0.034, 0.026), m_plastic('#ff4b3e', 'pcap', hl=0.7), sub=0, seg=16)
        ang = math.radians(28)                     # duruş açısı (simge ve durağan görüntü)
        for k, M in enumerate((RB, BB)):
            a = ang + k * math.pi
            d = (math.cos(a), math.sin(a))
            paddle('blade', (d[0] * 0.04, d[1] * 0.04, hub_z), d, 0.4, 0.21, 0.04, M, pitch=math.radians(22), lift=0.07, seg=24)
        return 'pervane'
    COLS = ['#e8433a', '#f5c534', '#3a86d8']
    mats = [m_fabric(c, name='gore' + c) for c in COLS]
    BAND = m_fabric('#4fae4a', name='beretband'); BTN = m_fabric('#4fae4a', name='beretbtn')
    STEMM = m_plastic('#ffcf3a', 'pstem', hl=0.6)
    # kubbe: dilimler arası dikiş oluğu, dilimler hafif şişkin
    prof = []
    for k in range(17):
        t = k / 16; ph = t * math.pi / 2
        prof.append((0.465 * math.cos(ph) ** 0.75, 0.085 + (TOPZ - 0.085) * math.sin(ph) ** 1.05))
    prof[-1] = (0.0, TOPZ)
    G6 = 2 * math.pi / 6; A0 = -math.pi / 2 + G6 / 2      # bir dilim tam önde
    def rf(a, i, r, z):
        t = i / 16; fade = math.sin(min(1.0, t * 1.4) * math.pi) if t < 0.95 else 0.0
        fade = max(0.0, min(1.0, (1 - t) * 3)) * min(1.0, t * 6 + 0.25)
        x = ((a - A0) % G6) / G6
        seam = math.exp(-((min(x, 1 - x)) / 0.05) ** 2)
        puff = math.sin(x * math.pi)
        return r * (1 + fade * (0.022 * puff - 0.03 * seam))
    def mf(a, i): return int(((a - A0) % (2 * math.pi)) // G6) % 3
    revolve('cap', prof, mats, segs=96, rfun=rf, mfun=mf)
    # iç astar (alttan bakınca kumaş içi; baş kubbesinin dışında)
    inner = cavity_down(1.08, rim=(0.44, 0.06))
    revolve('lining', inner, [m_fabric('#c23a32', name='lining')], segs=48)
    # kıvrık bant (örgü yivli halka)
    band = [(0.43, 0.0), (0.47, 0.0), (0.5, 0.025), (0.508, 0.06), (0.5, 0.095), (0.475, 0.115), (0.45, 0.11), (0.43, 0.07)]
    revolve('band', band, [BAND], segs=96, rfun=lambda a, i, r, z: r * (1 + (0.01 * math.cos(a * 40) if i in (2, 3, 4) else 0)), closed=True)
    # tepe: kumaş kaplı düğme + kısa sarı sap (pervane göbeğine girer)
    T.lathe('btn', [(0.001, TOPZ - 0.02), (0.075, TOPZ - 0.02), (0.08, TOPZ + 0.0), (0.066, TOPZ + 0.022), (0.035, TOPZ + 0.034), (0.001, TOPZ + 0.036)], BTN, segs=28)
    T.lathe('stem', [(0.001, TOPZ + 0.02), (0.024, TOPZ + 0.02), (0.022, hub_z - 0.02), (0.018, hub_z - 0.0), (0.001, hub_z)], STEMM, segs=16)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.01, location=(0, 0, TOPZ + 0.042), major_segments=20, minor_segments=8)
    bpy.context.object.data.materials.append(STEMM)
    return 'pervaneli bere'

def w_hat_propeller(): return _propeller('main')
def w_hat_propeller_spin(): return _propeller('spin')

# ------------------------------------------------------------------ 2. pasta şapka

def m_lace(name='lace'):
    """Dantel kâğıt: beyaz, kenar bandında delik delik nokta ızgarası (gri-pembe), ortası düz."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links; o = G.obj()
        sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
        rr = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', sep.outputs['X'], sep.outputs['X']), G.math('MULTIPLY', sep.outputs['Y'], sep.outputs['Y'])))
        dots = G.math('MULTIPLY', G.math('SINE', G.math('MULTIPLY', sep.outputs['X'], 150)), G.math('SINE', G.math('MULTIPLY', sep.outputs['Y'], 150)))
        hole = G.math('MULTIPLY', G.rng(dots, 0.45, 0.7), G.rng(rr, 0.455, 0.47))
        col = G.mix(hole, '#fffaf2', '#e6c6c8')
        col = vinyl(G, col, '#fffaf2', 0.3, top=0.0, low=0.1)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_candle(c1, c2, cx, cy, name):
    """Burgulu çizgili mum (kendi ekseni etrafında sarmal)."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links; o = G.obj()
        sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
        at = G.math('ARCTAN2', G.math('SUBTRACT', sep.outputs['Y'], cy), G.math('SUBTRACT', sep.outputs['X'], cx))
        ph = G.math('ADD', G.math('MULTIPLY', sep.outputs['Z'], 70.0), G.math('MULTIPLY', at, 2.0))
        st = G.rng(G.math('SINE', ph), -0.15, 0.15)
        col = G.mix(st, c1, c2)
        col = vinyl(G, col, c1, 0.5, top=0.1, low=0.1)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_flame(z0, h, name):
    def b(nt, bsdf):
        G = A._G(nt)
        rp = ramp(nt, [(0.0, '#ff6a1f'), (0.3, '#ffae2a'), (0.62, '#ffe04a'), (0.85, '#fff2a0'), (1.0, '#ffc43a')])
        f = G.rng(G.z(), z0, z0 + h, 0, 1, smooth=False)
        G.l.new(f, rp.inputs['Fac']); G.l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_berry(name='berry'):
    """Çilek: kırmızı, tepeye doğru açık; küçük sarı çekirdek noktaları; parlak."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj(); n = nt.nodes; l = nt.links
        vo = G.vor(o, 70)
        col = G.mix(G.rng(G.nz(), -0.6, 0.8), '#c51f2f', '#ff4a4a')
        col = G.mix(G.rng(vo, 0.14, 0.08), col, '#ffd96a')
        col = vinyl(G, col, '#e8303a', 0.6, top=0.0, low=0.1)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def swirl(name, loc, r, h, m, ridges=6, twist=9.0):
    """Sıkma krema gülü: yıldız uçlu, burgulu sivri topak."""
    prof = [(0.001, 0.0), (r * 0.9, 0.0), (r, h * 0.18), (r * 0.86, h * 0.42), (r * 0.58, h * 0.66), (r * 0.3, h * 0.86), (0.001, h)]
    o = revolve(name, prof, [m], segs=36, rfun=lambda a, i, rr, z: rr * (1 + 0.2 * math.cos(ridges * a + twist * z / h)) if 0 < i < 6 else rr)
    o.location = loc
    return o

def w_hat_cake():
    """İki katlı doğum günü pastası: pembe alt kat (beyaz krema damlaları + krema gülleri), vanilya üst kat (pembe sır damlaları),
    rengârenk serpinti (doku + birkaç iri boncuk), tepede çilek + 3 burgulu mum + alev; altta dantel kenarlı ince tabak.
    Altı içbükey: Okti'nin başı pastanın içine girer gibi oturur."""
    R = random.Random(7)
    PINK = m_frost('#f7a8c0', 'cakepink', sprinkles=0.08); VAN = m_frost('#fbe7bf', 'cakevan', sprinkles=0.08)
    WCR = m_frost('#fff8f0', 'cream', sprinkles=0.3, hl=0.6); PCR = m_frost('#ff7fa8', 'pinkglaze', sprinkles=0.34, hl=0.6)
    SP = m_frost('#e8b48a', 'sponge', hl=0.0)
    # tabak + dantel
    revolve('plate', [(0.40, 0.003), (0.47, 0.004), (0.5, 0.016), (0.49, 0.026), (0.40, 0.024)], [m_plastic('#bfe6ec', 'plate', hl=0.5)], segs=64, closed=True)
    revolve('lace', [(0.38, 0.026), (0.47, 0.03), (0.475, 0.033), (0.38, 0.033)], [m_lace()], segs=120,
            rfun=lambda a, i, r, z: r * (1 + (0.028 * abs(math.cos(a * 12)) if i in (1, 2) else 0)), closed=True)
    # alt kat: dış duvar + üst sahanlık; altı oyuk (baş kubbesi)
    Z1, R1 = 0.27, 0.43
    cv = cavity(1.04)
    t1 = [(R1 - 0.02, 0.03), (R1, 0.05), (R1 + 0.004, Z1 * 0.6), (R1, Z1 - 0.03), (R1 - 0.03, Z1), (0.001, Z1)]
    revolve('tier1', t1, [PINK], segs=96)
    revolve('tier1in', [(r, z + 0.03) for (r, z) in reversed(cv[1:])] + [(R1 - 0.02, 0.03)], [SP], segs=48)
    drips('drip1', R1, Z1, WCR, tongues=15, seed=3, dmin=0.025, dmax=0.13)
    # üst kat
    Z2, R2 = 0.47, 0.29
    t2 = [(0.001, Z1), (R2 - 0.01, Z1), (R2, Z1 + 0.02), (R2 + 0.003, (Z1 + Z2) / 2), (R2, Z2 - 0.025), (R2 - 0.025, Z2), (0.001, Z2)]
    revolve('tier2', t2, [VAN], segs=80)
    drips('drip2', R2, Z2, PCR, tongues=11, seed=5, dmin=0.02, dmax=0.1, edge_r=0.024)
    # krema gülleri: alt katın sahanlığında halka
    for k in range(12):
        a = k * 2 * math.pi / 12 + 0.12
        swirl('rose', (math.cos(a) * 0.365, math.sin(a) * 0.365, Z1 + 0.008), 0.042, 0.065, WCR, twist=8 + (k % 3))
    # iri serpinti boncukları (üst katın tepesi + sahanlık)
    for k in range(16):
        a = R.uniform(0, 2 * math.pi); top = k < 9
        rr = R.uniform(0.1, 0.24) if top else R.uniform(0.31, 0.41)
        z = (Z2 + 0.02) if top else (Z1 + 0.012)
        if not top and min(ang_dist(a, j * 2 * math.pi / 12 + 0.12) for j in range(12)) < 0.2: continue
        blob('spr', (math.cos(a) * rr, math.sin(a) * rr, z), (0.022, 0.009, 0.009), m_plastic(PALETTE6[k % 6], 'spr' + PALETTE6[k % 6], hl=0.5), rot=(0, 0, R.uniform(0, 180)), sub=0, seg=10)
    # çilek (ortada)
    BER = m_berry()
    BS = 1.45
    T.lathe('berry', [(0.001, Z2 + 0.012), (0.03 * BS, Z2 + 0.016), (0.058 * BS, Z2 + 0.045 * BS), (0.066 * BS, Z2 + 0.085 * BS), (0.056 * BS, Z2 + 0.112 * BS), (0.03 * BS, Z2 + 0.125 * BS), (0.001, Z2 + 0.128 * BS)], BER, segs=28)
    LF = m_leaf('#2f8a3a', '#4fb24a', '#8fd06a', '#b5e28a', 'calyx')
    def calyx(bm):
        out = []
        for k in range(6):
            a = k * math.pi / 3 + 0.3
            for f in A.blade(bm, V((0, 0, Z2 + 0.124 * BS)), V((math.cos(a), math.sin(a), 0.25)).normalized(), V((-math.sin(a), math.cos(a), 0)), 0.075, 0.026, 0.5, segs=3):
                out.append((f, 0))
        return out
    mesh_from_blades('calyx', calyx, [LF])
    tube('berrystem', [(0, 0, Z2 + 0.124 * BS), (0.008, 0, Z2 + 0.16 * BS), (0.022, 0.004, Z2 + 0.172 * BS)], [0.011, 0.009, 0.007], m_plastic('#4f9a3a', 'bstem', hl=0.2), res=3)
    # 3 burgulu mum + alev (ön-sol, ön-sağ, arka)
    CAN = [('#58b8f0', '#fffaf0'), ('#ffd447', '#fffaf0'), ('#7ed36a', '#fffaf0')]
    for k, a in enumerate((math.radians(-125), math.radians(-55), math.radians(90))):
        x, y = math.cos(a) * 0.19, math.sin(a) * 0.19; z0 = Z2 + 0.012; hc = 0.15; cr = 0.03
        T.lathe('candle', [(0.001, z0), (cr, z0), (cr, z0 + hc - 0.008), (cr * 0.8, z0 + hc), (0.001, z0 + hc)], m_candle(CAN[k][0], CAN[k][1], x, y, 'cand%d' % k), segs=16).data.transform(Matrix.Translation((x, y, 0)))
        tube('wick', [(x, y, z0 + hc - 0.002), (x, y, z0 + hc + 0.022)], [0.006, 0.005], m_plastic('#3a2a22', 'wick', hl=0.0), res=2)
        fz = z0 + hc + 0.014; fh = 0.1; fs = 1.35
        fl = T.lathe('flame', [(0.001, fz), (0.016 * fs, fz + 0.008), (0.024 * fs, fz + 0.028), (0.02 * fs, fz + 0.052), (0.011 * fs, fz + 0.076), (0.001, fz + fh)], m_flame(fz, fh, 'flame%d' % k), segs=16)
        fl.data.transform(Matrix.Translation((x, y, 0)))
    return 'pasta şapka'

# ------------------------------------------------------------------ 3. karpuz şapka

def m_rind(name='rind'):
    """Karpuz kabuğu: açık yeşil zemin, tepeden alta dalgalı koyu yeşil şeritler, hafif benek; parlak."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links; o = G.obj()
        sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
        at = G.math('ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
        wav = G.math('ADD', G.math('MULTIPLY', G.math('SINE', G.math('MULTIPLY', sep.outputs['Z'], 34.0)), 0.16),
                     G.math('MULTIPLY', G.noise(o, 3.0, 3), 0.55))
        ph = G.math('ADD', G.math('MULTIPLY', at, 9.0), wav)
        st = G.rng(G.math('SINE', ph), 0.05, 0.35)
        # tepede şeritler bir noktada toplanmasın: z yükseldikçe şerit inceltilir
        base = G.mix(G.rng(G.noise(o, 7, 4), 0.35, 0.7), '#5fae3c', '#7cc44e')
        dark = G.mix(G.rng(G.noise(o, 9, 4), 0.3, 0.7), '#1f5a2a', '#2c7334')
        col = G.mix(st, base, dark)
        col = G.mix(G.rng(G.vor(o, 40), 0.06, 0.02, 0, 0.25), col, '#a8dc7a')     # açık benekler
        col = vinyl(G, col, '#4f9a3a', 0.5, top=0.1, low=0.15)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_flesh(name='flesh', seeds=True):
    """Kırmızı meyve: hafif lifli, çekirdekler (siyah, dikine damla) ızgarada rastgele; parlak."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links; o = G.obj()
        col = G.mix(G.rng(G.noise(G.mapping(o, (6, 6, 30)), 1.0, 4), 0.35, 0.7), '#e8343c', '#ff5a5a')
        if seeds:
            sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
            at = G.math('ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
            cc = n.new('ShaderNodeCombineXYZ'); l.new(G.math('MULTIPLY', at, 3.4), cc.inputs[0]); l.new(G.math('MULTIPLY', sep.outputs['Z'], 13.0), cc.inputs[1])
            vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 1.0; vo.inputs['Randomness'].default_value = 0.6
            l.new(cc.outputs[0], vo.inputs['Vector'])
            seed = G.rng(vo.outputs['Distance'], 0.24, 0.19)
            sep2 = n.new('ShaderNodeSeparateColor'); l.new(vo.outputs['Color'], sep2.inputs[0])
            seed = G.math('MULTIPLY', seed, G.rng(sep2.outputs[0], 0.25, 0.29))
            col = G.mix(seed, col, '#1e1416')
        col = vinyl(G, col, '#e8343c', 0.55, top=0.06, low=0.14)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def w_hat_watermelon():
    """Yarım karpuz kask: parlak yeşil kabuk + dalgalı koyu şeritler; alt kenarda beyaz kabuk şeridi + çekirdekli kırmızı meyve bandı
    (karikatür: kesik yüz yana dönük okunur), iç oyuk kırmızı; tepede kıvrık sap + yaprak + kıvrımlı filiz."""
    RIND = m_rind(); WH = m_frost('#f4f7e4', 'melonwhite', hl=0.35); FL = m_flesh(); FLI = m_flesh('fleshin', seeds=False)
    TOP = 0.56
    # dış: kırmızı bant (0 → 0.1) → beyaz şerit (0.1 → 0.135) → yeşil kubbe (basamaklı, kabuk kenarı taşar)
    outer = [(0.455, 0.0), (0.468, 0.012), (0.474, 0.05), (0.47, 0.09), (0.462, 0.1), (0.476, 0.104), (0.482, 0.118), (0.478, 0.132),
             (0.47, 0.136), (0.494, 0.14), (0.505, 0.16)]
    for k in range(1, 15):
        ph = k / 14 * math.pi / 2
        outer.append((0.505 * math.cos(ph) ** 0.9, 0.16 + (TOP - 0.16) * math.sin(ph) ** 1.1))
    outer[-1] = (0.0, TOP)
    def mf(a, i):
        z = (outer[i][1] + outer[min(i + 1, len(outer) - 1)][1]) / 2
        return 0 if z < 0.1 else (1 if z < 0.138 else 2)
    revolve('melon', outer, [FL, WH, RIND], segs=96, mfun=mf)
    # alt ağız: kırmızı halka yüzü + oyuk
    cv = cavity(1.06)
    revolve('mouth', cavity_down(1.06, rim=(0.455, 0.0)), [FLI], segs=64)
    # sap + yaprak + filiz
    STM = m_plastic('#6b8a3a', 'mstem', hl=0.3)
    tube('stem', [(0, 0, TOP - 0.01), (0.005, -0.004, TOP + 0.045), (0.03, -0.01, TOP + 0.075), (0.06, -0.012, TOP + 0.07)], [0.028, 0.024, 0.02, 0.016], STM, res=4)
    LF = m_leaf('#2f8a3a', '#4fb24a', '#8fd06a', '#c5ea92', 'melonleaf')
    def leaf(bm):
        out = []
        for f in A.blade(bm, V((0.0, 0.0, TOP + 0.03)), V((-0.75, 0.3, 0.42)).normalized(), V((0.35, 0.9, 0.2)).normalized(), 0.27, 0.1, 0.4, segs=7, lift=0.12):
            out.append((f, 0))
        return out
    mesh_from_blades('leaf', leaf, [LF])
    pts = []
    for i in range(22):
        t = i / 21; a = t * 3.2 * math.pi
        pts.append((0.06 + 0.07 * t + math.cos(a) * 0.022 * (1 - t * 0.5), -0.012 + math.sin(a) * 0.022 * (1 - t * 0.5), TOP + 0.07 + 0.03 * t - 0.0 * t))
    tube('tendril', pts, [0.007] * len(pts), STM, res=2)
    return 'karpuz şapka'

# ------------------------------------------------------------------ 4. yamuk taç

def m_velvet(name='velvet'):
    return m_fabric('#c4243a', name=name)

def w_hat_crown_tilt():
    """Abartılı karikatür altın taç: tombul bant (üst/alt yuvarlak kenar), 5 tombul yuvarlak uçlu sivri diş (hafif eğri, boyları farklı),
    iri yuvarlak kaboşon taşlar (kırmızı, mavi, yeşil) altın yuvalarda; içte kırmızı kadife yastık + tepede altın top.
    ~18° yana yatık (kendi içinde); kadife yastık yatık değil: başa oturur, yüksek yanda bantla baş arasını doldurur."""
    R = random.Random(13)
    GOLD = m_gold(); objs = []
    RI, RO, HB = 0.44, 0.505, 0.18              # iç/dış yarıçap, bant yüksekliği
    N = 5; teeth = []
    for k in range(N):
        teeth.append((-math.pi / 2 + k * 2 * math.pi / N + math.radians(R.uniform(-5, 5)), R.uniform(0.17, 0.24), math.radians(R.uniform(-8, 8))))
    def top_z(a):
        z = HB
        for (ak, hk, lean) in teeth:
            x = ang_dist(a, ak) / (math.pi / N * 0.95)
            if x < 1: z = max(z, HB + hk * (1 - x) ** 1.15)
        return z
    # bant + dişler: sütun başına kesit (dış duvar şişkin, üstte yuvarlak)
    segs = 160; rows = 18; bm = bmesh.new(); grid = []
    for j in range(segs):
        a = j / segs * 2 * math.pi; zt = top_z(a)
        # diş eğriliği: dişin üst kısmı yana kayar
        sh = 0.0
        for (ak, hk, lean) in teeth:
            x = ang_dist(a, ak) / (math.pi / N * 0.95)
            if x < 1: sh += lean * (1 - x)
        col = []
        for i in range(rows):
            t = i / (rows - 1)
            # kesit döngüsü: iç alt → dış alt → dış üst → iç üst
            if t < 0.5:
                s = t * 2; z = s * zt; r = RO + 0.012 * math.sin(math.pi * min(1.0, z / HB)) if z < HB else RO + 0.004
            else:
                s = (t - 0.5) * 2; z = zt * (1 - s); r = RI
            col.append((r, z, a + sh * max(0.0, (z - HB)) / 0.2))
        grid.append(col)
    # yuvarlatılmış kesit için subsurf ile; köşeler kapalı döngü
    verts = [[bm.verts.new((math.cos(aa) * r, math.sin(aa) * r, z)) for (r, z, aa) in col] for col in grid]
    for j in range(segs):
        j2 = (j + 1) % segs
        for i in range(rows):
            i2 = (i + 1) % rows
            try: bm.faces.new((verts[j][i], verts[j2][i], verts[j2][i2], verts[j][i2]))
            except ValueError: pass
    band = link_mesh('band', bm, [GOLD]); smooth(band)
    s = band.modifiers.new('sub', 'SUBSURF'); s.levels = 1; s.render_levels = 1
    objs.append(band)
    # bant kenarlarında tombul yuvarlak sırt (üst ve alt)
    for z, rr in ((0.012, 0.024), (HB - 0.006, 0.02)):
        bpy.ops.mesh.primitive_torus_add(major_radius=RO + 0.006, minor_radius=rr, location=(0, 0, z), major_segments=64, minor_segments=10)
        o = bpy.context.object; o.data.materials.append(GOLD); smooth(o); objs.append(o)
    # diş uçlarında tombul toplar
    for (ak, hk, lean) in teeth:
        z = HB + hk + 0.03; aa = ak + lean * (hk) / 0.2
        objs.append(blob('ball', (math.cos(aa) * (RI + RO) / 2, math.sin(aa) * (RI + RO) / 2, z), (0.06, 0.06, 0.06), GOLD, sub=0, seg=20))
    # kaboşon taşlar: her diş altında bir iri taş (önde kırmızı), aralarda küçük
    GEMS = {'r': m_gem('#e8303a', 'gemr'), 'b': m_gem('#2f7fe0', 'gemb'), 'g': m_gem('#2fbf5a', 'gemg')}
    order = ['r', 'b', 'g', 'b', 'g']
    for k, (ak, hk, lean) in enumerate(teeth):
        for (aa, rr, key) in ((ak, 0.068, order[k]), (ak + math.pi / N, 0.038, 'r' if k % 2 else 'g')):
            c = V((math.cos(aa), math.sin(aa), 0)); zc = HB * 0.52 if rr > 0.04 else HB * 0.5
            p = c * (RO + 0.012) + V((0, 0, zc))
            bpy.ops.mesh.primitive_torus_add(major_radius=rr + 0.006, minor_radius=0.011, location=p, major_segments=24, minor_segments=8)
            o = bpy.context.object; o.rotation_euler = c.to_track_quat('Z', 'Y').to_euler(); o.data.materials.append(GOLD); smooth(o); objs.append(o)
            g = blob('gem', tuple(p + c * 0.004), (rr, rr, rr * 0.55), GEMS[key], sub=0, seg=20)
            g.rotation_euler = c.to_track_quat('Z', 'Y').to_euler(); objs.append(g)
    tilt_all(objs, 18, (0, 0, 0.1))
    # kadife yastık (yatık değil): ağız başa oturur, kubbe dişlerin arasından görünür; dikiş çizgileri altın
    VEL = m_velvet()
    prof = [(0.43, 0.0), (0.44, 0.05), (0.43, 0.12), (0.4, 0.2), (0.33, 0.28), (0.22, 0.34), (0.1, 0.37), (0.001, 0.375)]
    def rf(a, i, r, z):
        x = (a % (2 * math.pi / 8)) / (2 * math.pi / 8)
        return r * (1 - 0.035 * math.exp(-((min(x, 1 - x)) / 0.06) ** 2) * (1 if 0 < i < 7 else 0))
    revolve('cushion', prof, [VEL], segs=96, rfun=rf)
    revolve('cushin', cavity_down(1.04, rim=(0.43, 0.0)), [m_fabric('#8a1a2a', name='velin')], segs=48)
    blob('tuft', (0, 0, 0.372), (0.04, 0.04, 0.018), GOLD, sub=0, seg=16)
    return 'yamuk taç'

# ------------------------------------------------------------------ 5. kova şapka

def m_shell(name='wshell'):
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links; o = G.obj()
        sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
        col = G.mix(G.rng(G.math('SINE', G.math('MULTIPLY', G.math('ADD', sep.outputs['X'], G.math('MULTIPLY', sep.outputs['Z'], 0.3)), 160)), -0.2, 0.6), '#f08a8a', '#ffd2c2')
        col = vinyl(G, col, '#ffb6a0', 0.45)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_starfish(name='starfish'):
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.vor(o, 90), 0.2, 0.1), '#ff7a45', '#ffc27a')
        col = vinyl(G, col, '#ff8a4a', 0.4)
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_bucket(hexc, a0, z0, name='bucket'):
    """Kova plastiği + dökülen kum tozu: ağızdan (tepeden) aşağı daralan, benekli kum izi (a0 yönünde)."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links; o = G.obj()
        col = G.mix(0.05, hexc, G.noise(o, 5, 2, out='Color'), 'OVERLAY')
        col = vinyl(G, col, hexc, 0.55)
        sep = n.new('ShaderNodeSeparateXYZ'); l.new(o, sep.inputs[0])
        at = G.math('ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
        d = G.math('COSINE', G.math('SUBTRACT', at, a0))
        zz = G.math('ADD', sep.outputs['Z'], G.math('MULTIPLY', G.noise(o, 6, 3), 0.1))
        wide = G.math('SUBTRACT', d, G.math('MULTIPLY', G.math('SUBTRACT', z0, zz), 0.32))
        mask = G.math('MULTIPLY', G.rng(wide, 0.86, 0.96), G.rng(zz, z0 - 0.36, z0 - 0.05))
        speck = G.math('MAXIMUM', G.rng(G.noise(o, 55, 2), 0.5, 0.62), G.rng(G.vor(o, 90), 0.16, 0.08))
        col = G.mix(G.math('MULTIPLY', mask, G.math('ADD', 0.35, G.math('MULTIPLY', speck, 0.65))), col, '#e6c88e')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def w_hat_bucket():
    """Ters çevrilmiş parlak plastik kumsal kovası (mavi): yivli gövde, dipte (tepede) iki halka sırt, ağızda kalın kıvrık dudak;
    sarı kulp iki yandaki yuvadan öne doğru düşmüş, gövdeye yaslanır; tepede kum yığını (dökülen kum taneleri yan duvardan iner),
    üstünde deniz yıldızı; yanda yapışık deniz kabuğu. Açık ağız başın üstüne oturur."""
    R = random.Random(21)
    H = 0.52; a0 = math.radians(-35)
    BL = m_bucket('#2f8fe0', a0, H); BLI = m_plastic('#6fb8f4', 'bucketin', hl=0.2); YEL = m_plastic('#ffc93a', 'handle', hl=0.6)
    def wall_r(z): return 0.455 - (0.455 - 0.355) * (z - 0.06) / (H - 0.06)
    outer = [(0.43, 0.0), (0.462, 0.0), (0.49, 0.018), (0.495, 0.04), (0.485, 0.06), (0.462, 0.07)]
    zs = [0.1, 0.16, 0.22, 0.28, 0.34, 0.39, 0.405, 0.42, 0.435, 0.45, 0.465, 0.48, 0.5]
    ribs = {0.405: 0.018, 0.45: 0.018}
    for z in zs: outer.append((wall_r(z) + ribs.get(z, 0.0), z))
    outer += [(0.355, H - 0.005), (0.34, H + 0.012), (0.3, H + 0.018), (0.001, H + 0.02)]
    nfl = 26
    def rf(a, i, r, z):
        if 6 <= i <= 10: return r * (1 + 0.018 * (0.5 + 0.5 * math.cos(a * nfl)) ** 2)   # dikey yivler (gövdenin alt-orta kısmı)
        return r
    revolve('bucket', outer, [BL], segs=104, rfun=rf)
    inner = [(0.0, H - 0.02), (0.3, H - 0.02)] + [(wall_r(z) - 0.03, z) for z in (0.4, 0.25, 0.1)] + [(0.425, 0.03), (0.43, 0.0)]
    revolve('inside', inner, [BLI], segs=64)
    # kulp yuvaları + kulp (öne düşmüş, gövdeye yaslı)
    LZ = 0.11; LR = wall_r(LZ) + 0.012
    for sx in (-1, 1):
        cyl('lug', (sx * LR, 0, LZ), 0.032, 0.03, BL, rot=(0, 90, 0), verts=20, bevel=0.008)
        blob('pin', (sx * (LR + 0.018), 0, LZ), (0.012, 0.022, 0.022), YEL, sub=0, seg=12)
    al = math.radians(26); pts = []
    for i in range(25):
        t = i / 24 * math.pi; s = math.sin(t)
        pts.append((math.cos(t) * (LR + 0.02), -s * (LR + 0.02) * math.cos(al) - 0.012 * s, LZ + s * (LR + 0.02) * math.sin(al)))
    tube('handle', pts, [0.017] * len(pts), YEL, res=2)
    # tepede kum yığını + yandan dökülen taneler
    SND = T.m_sand('bsand', '#ecd29a'); WET = T.m_sand('bsandwet', '#d8b47a')
    s = blob('sand', (0.02, 0.03, H + 0.03), (0.27, 0.25, 0.07), SND, sub=1, seg=20); wobble(s, 0.02, 7.0, 3)
    for k in range(4):
        a = R.uniform(0, 6.28); rr = R.uniform(0.05, 0.16)
        o = blob('lump', (math.cos(a) * rr, math.sin(a) * rr + 0.02, H + 0.07 + R.uniform(0, 0.02)), (0.05, 0.045, 0.03), SND, sub=0, seg=12); wobble(o, 0.008, 12.0, k)
    # dökülen kum: ön-sağ duvardan aşağı azalan topaklar + ağız kenarında küçük birikinti
    o = blob('over', (math.cos(a0) * 0.33, math.sin(a0) * 0.33, H + 0.03), (0.1, 0.08, 0.05), SND, rot=(0, 0, math.degrees(a0)), sub=1, seg=16); wobble(o, 0.012, 9.0, 5)
    for k in range(4):                                     # kenardan sarkan birkaç küçük kum topağı (gerisi dokuda toz izi)
        z = H - 0.02 - k * 0.05; a = a0 + R.uniform(-0.12, 0.12)
        rr = wall_r(z) + (0.018 if z > 0.4 else 0.0); sz = 0.03 * (1 - k * 0.18)
        c = V((math.cos(a), math.sin(a), 0))
        o = blob('spill', tuple(c * (rr + sz * 0.1) + V((0, 0, z))), (sz * 0.5, sz, sz * 1.1), SND if k < 2 else WET, rot=(0, 0, math.degrees(a)), sub=0, seg=10)
        wobble(o, sz * 0.12, 30.0, k)
    for k in range(9):
        a = a0 + R.uniform(-0.3, 0.3); z = R.uniform(0.12, H - 0.05)
        rr = wall_r(z) + 0.004
        blob('grain', (math.cos(a) * rr, math.sin(a) * rr, z), (0.009, 0.009, 0.009), SND, sub=0, seg=6)
    # deniz yıldızı (kum yığınının üstünde, hafif eğik)
    SF = m_starfish(); cz = H + 0.105; parts = []
    parts.append(blob('sfc', (0, 0, cz), (0.055, 0.055, 0.03), SF, sub=0, seg=16))
    for k in range(5):
        a = math.pi / 2 + k * 2 * math.pi / 5 + 0.2
        o = blob('arm', (math.cos(a) * 0.085, math.sin(a) * 0.085, cz - 0.006), (0.09, 0.034, 0.022), SF, rot=(0, -8, math.degrees(a)), sub=0, seg=16)
        parts.append(o)
    tilt_all(parts, -22, (0, 0, cz), 'X'); tilt_all(parts, 8, (0, 0, cz), 'Y')
    for o in parts: o.location += V((-0.05, -0.05, 0.0))
    # yanda deniz kabuğu (sol-ön duvara yapışık)
    a = math.radians(-145); z = 0.3; c = V((math.cos(a), math.sin(a), 0)); rr = wall_r(z)
    sh = blob('shell', tuple(c * (rr + 0.014) + V((0, 0, z))), (0.08, 0.068, 0.02), m_shell(), sub=0, seg=20)
    sh.rotation_euler = (c.to_track_quat('Z', 'Y') @ mathutils.Quaternion((0, 0, 1), math.radians(-8))).to_euler()
    for sx in (-1, 1):
        o = blob('ear', tuple(c * (rr + 0.014) + V((0, 0, z - 0.06)) + V((-c.y, c.x, 0)) * sx * 0.018), (0.018, 0.015, 0.012), m_shell(), sub=0, seg=8)
    return 'kova şapka'

BUILDERS = {'w_hat_propeller': (w_hat_propeller, 512, None), 'w_hat_propeller_spin': (w_hat_propeller_spin, 256, None),
            'w_hat_cake': (w_hat_cake, 512, None), 'w_hat_watermelon': (w_hat_watermelon, 512, None),
            'w_hat_crown_tilt': (w_hat_crown_tilt, 512, None), 'w_hat_bucket': (w_hat_bucket, 512, None)}

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
        tris = export_baked_fbx(f'{OUT}/{name}', objs, size=size, decimate=dec, ao_strength=float(os.environ.get('POFI_AO', '0.5')))
        print(name, 'üçgen', tris, flush=True)
