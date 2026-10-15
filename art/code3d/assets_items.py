# Ev eşyaları ve süsler (Resources/Items) — kodla, aynı tasarım dili (assets_town / assets_v3): dokulu ahşap, kumaş, halat,
# eskime ve yumuşak gölge; özgün tasarımlar. Ön yüz Blender −Y (oyunda kameraya döner).
# Kullanım: python -I assets_items.py -- <çıktı_klasörü> [i_bed ...]   (oyuna: export_game.py)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets_town import *
import assets_town as T
import assets_v3 as A
from assets_v3 import _shade

def m_fabric(c1, c2=None, name=None, check=0.0):
    """Yumuşak kumaş: dokuma, hafif tüylenme, kıvrımlarda koyulaşma; check > 0 ise ekose desen."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 3, 4), 0.3, 0.7), _shade(c1, 0.9), _shade(c1, 1.08))
        if check and c2:
            sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
            a = G.rng(G.math('SINE', G.math('MULTIPLY', sp.outputs['X'], check)), 0.3, 0.6)
            b2 = G.rng(G.math('SINE', G.math('MULTIPLY', sp.outputs['Y'], check)), 0.3, 0.6)
            col = G.mix(G.math('MULTIPLY', G.math('MAXIMUM', a, b2), 0.6), col, c2)
        col = G.mix(0.2, col, G.noise(G.mapping(o, (120, 120, 120)), 1.0, 2, out='Color'), 'OVERLAY')
        col = G.mix(G.rng(G.noise(o, 5, 6), 0.62, 0.75, 0, 0.2), col, '#8a7a6a', 'MULTIPLY')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name or ('fab' + c1 + (c2 or '')), b)

def i_bed():
    """Pet yatağı: kalın, yuvarlak dikişli kumaş halka (lacivert, krem biyeli), içte yumuşak krem minder, ekose yastık,
    minder üstünde küçük örgü battaniye kıvrımı."""
    RING = m_fabric('#2f6f9a', name='bedring'); PIP = m_fabric('#f2e6cf', name='bedpip')
    bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.2, location=(0, 0, 0.2), major_segments=48, minor_segments=16)
    t = bpy.context.object; t.scale = (1.0, 0.92, 1.0); t.data.materials.append(RING); smooth(t)
    for z in (0.08, 0.36):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.55 + (0.17 if z < 0.2 else 0.05), minor_radius=0.018, location=(0, 0, z + (0.02 if z < 0.2 else 0.02)), major_segments=48, minor_segments=6)
        b = bpy.context.object; b.scale = (1.0, 0.92, 1.0); b.data.materials.append(PIP)
    MAT = m_fabric('#efe2c8', name='bedmat')
    m = blob('mattress', (0, 0, 0.12), (0.5, 0.46, 0.09), MAT, sub=2, seg=24); wobble(m, 0.01, 5.0, 2)
    PIL = m_fabric('#7fb6d8', '#f4ead6', name='pillow', check=40.0)
    p = blob('pillow', (0.12, 0.18, 0.28), (0.2, 0.13, 0.08), PIL, rot=(10, -8, 20), sub=2, seg=16); wobble(p, 0.01, 6.0, 3)
    BL = m_fabric('#f2a64a', '#fff1d6', name='blanket', check=30.0)
    k = blob('blanket', (-0.18, -0.12, 0.22), (0.24, 0.16, 0.05), BL, rot=(0, 6, -25), sub=2, seg=16); wobble(k, 0.015, 6.0, 4)
    return 'yatak'

def i_bookshelf():
    """Kitaplık: aşınmış boyalı ahşap gövde (krem, köşelerde ahşap görünür), iki raf, farklı boy/renkte kitaplar (sırtta
    altın bantlar), yatık kitap yığını, minik saksı bitki ve yıldız kupası."""
    R = random.Random(5)
    BODY = m_wood('#b98a5a', 'shelfbody', paint='#f1e3c4', age=0.8); BACK = m_wood('#8f5d36', 'shelfback', age=0.6)
    Wd, Dp, H = 1.2, 0.36, 1.25
    plank('back', (0, Dp / 2 - 0.02, H / 2), (Wd, 0.03, H), BACK, seed=1)
    for sx in (-1, 1): plank('side', (sx * (Wd / 2 - 0.03), 0, H / 2), (0.06, Dp, H + 0.02), BODY, seed=sx + 3)
    for z in (0.04, H * 0.5, H - 0.02): plank('shelf', (0, 0, z), (Wd, Dp, 0.05), BODY, seed=int(z * 10) + 7)
    plank('crown', (0, -0.01, H + 0.04), (Wd + 0.08, Dp + 0.06, 0.05), BODY, seed=9)
    COLS = ['#d6453c', '#2f8a6e', '#2f6fb2', '#e8a83a', '#8a5cc0', '#e0684a', '#3a9ad0', '#6ab04c']
    GOLD = A.m_flat('#e8c45a', 0.1, 8, 'gold')
    for row, z0 in enumerate((0.065, H * 0.5 + 0.025)):
        x = -Wd / 2 + 0.08
        while x < Wd / 2 - (0.42 if row == 0 else 0.3):
            w = R.uniform(0.05, 0.08); h = R.uniform(0.32, 0.46) if row == 0 else R.uniform(0.3, 0.42)
            tilt = R.uniform(-3, 3)
            c = R.choice(COLS); m = m_fabric(c, name='book' + c)
            rbox('book', (x + w / 2, -0.02, z0 + h / 2), (w, Dp * 0.75, h), m, rot=(0, tilt, 0), bevel=0.008)
            for dz in (0.06, h - 0.06): rbox('band', (x + w / 2, -0.02 - Dp * 0.375 - 0.002, z0 + dz), (w * 0.9, 0.004, 0.012), GOLD, rot=(0, tilt, 0), bevel=0)
            x += w + 0.008
    # yatık kitap yığını + kupa (alt raf sağ), saksı (üst raf sağ)
    for k in range(3):
        c = COLS[k + 2]; rbox('flat', (Wd / 2 - 0.25, -0.02, 0.09 + k * 0.055), (0.32 - k * 0.03, 0.24, 0.05), m_fabric(c, name='book' + c), rot=(0, 0, R.uniform(-6, 6)), bevel=0.006)
    T.lathe('cup', [(0.001, 0.26), (0.05, 0.26), (0.03, 0.3), (0.025, 0.36), (0.07, 0.42), (0.075, 0.48), (0.001, 0.48)], GOLD, segs=16).location = (Wd / 2 - 0.25, -0.02, 0)
    POT = m_plaster('#d9774f', name='pot', dirt=0.15)
    T.lathe('pot', [(0.001, H * 0.5 + 0.025), (0.07, H * 0.5 + 0.025), (0.09, H * 0.5 + 0.17), (0.1, H * 0.5 + 0.18)], POT, segs=14).location = (Wd / 2 - 0.18, -0.02, 0)
    LF = m_leaf('#2f8a3a', '#56b64a', '#a6dc6a', '#cdee92', 'fleaf')
    mesh_from_blades('plant', rosette([(Wd / 2 - 0.18, -0.02)], R, sizes=(0.16, 0.24), leaves=8), [LF])
    for o in bpy.context.scene.objects:
        if o.name.startswith('plant'): o.location.z = H * 0.5 + 0.15
    return 'kitaplık'

def i_lamp():
    """Masa lambası: tornalanmış ahşap ayak, pirinç boyun, deniz kabuğu dilimli kumaş abajur (içi sıcak ışıklı), çekme ipi."""
    W = m_wood('#a8693d', 'lampbase', age=0.5); BR = m_metal('#c9a04a', '#7a8a5a', 'brass', age=0.4)
    T.lathe('base', [(0.001, 0.0), (0.22, 0.0), (0.23, 0.04), (0.16, 0.09), (0.09, 0.14), (0.06, 0.4), (0.08, 0.46), (0.001, 0.47)], W, segs=24)
    tube('neck', [(0, 0, 0.46), (0, 0, 0.75)], [0.02, 0.018], BR, res=3)
    SH = m_fabric('#ffb6a0', name='shade'); GL = m_glow('#ffd88a', 'lampglow')
    prof = [(0.36, 0.62), (0.3, 0.8), (0.16, 0.98), (0.12, 1.0)]
    n = 10
    for k in range(n):                                  # dilimli abajur: her dilim hafif şişkin
        a = k * 2 * math.pi / n
        sh = T.lathe('rib', prof, SH, segs=6)
        sh.scale = (1.0, 1.0, 1.0); sh.rotation_euler = (0, 0, a)
    T.lathe('shade', [(p[0] * 0.98, p[1]) for p in prof], SH, segs=40)
    blob('bulb', (0, 0, 0.74), (0.12, 0.12, 0.12), GL, sub=1, seg=16)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.012, location=(0, 0, 0.62), major_segments=40, minor_segments=6)
    bpy.context.object.data.materials.append(BR)
    tube('cord', [(0.1, 0, 0.75), (0.14, -0.02, 0.6), (0.14, -0.02, 0.5)], [0.004] * 3, m_rope(), res=2)
    blob('knob', (0.14, -0.02, 0.49), (0.015, 0.015, 0.02), W, sub=0, seg=8)
    return 'lamba'

def i_rug():
    """Örgü halı: içten dışa sarmal halat örgüsü, her turda renk değişir (deniz mavisi, kum, mercan, yosun), kenarda püsküller."""
    COLS = ['#3a8ad0', '#e8c890', '#e86f50', '#6ab04c', '#2f6fb2', '#f2d9a8']
    mats = [m_rope(c, 'rug' + c) for c in COLS]
    turns = 9; per = 40
    for k in range(turns):
        pts = []
        for i in range(per + 1):
            t = (k + i / per); a = t * 2 * math.pi; r = 0.06 + t * 0.075
            pts.append((math.cos(a) * r * 1.0, math.sin(a) * r * 0.8, 0.02))
        o = tube('coil', pts, [0.036] * len(pts), mats[k % len(COLS)], res=2)
    R = random.Random(2)
    rmax = 0.06 + turns * 0.075
    for k in range(36):                                 # püsküller
        a = k * 2 * math.pi / 36
        p0 = (math.cos(a) * rmax, math.sin(a) * rmax * 0.8, 0.012)
        tube('tassel', [p0, (p0[0] * 1.08, p0[1] * 1.08, 0.006)], [0.008, 0.005], mats[k % 3], res=1)
    return 'halı'

def i_aquarium():
    """Akvaryum: ahşap ayaklı dolap üstünde dikdörtgen tank (çerçeveli; ön cam yok sayılır, içi görünür): mavi su geçişi
    (arka duvar), kum zemin, taşlar, dalgalanan deniz otları, mercan, iki turuncu-beyaz balık ve kabarcıklar."""
    R = random.Random(9)
    W = m_wood('#8f5d36', 'aqwood', age=0.5)
    Wd, Dp, H, Z0 = 1.0, 0.45, 0.6, 0.55
    plank('cab', (0, 0, Z0 / 2), (Wd + 0.06, Dp + 0.06, Z0), W, seed=1)
    for sx in (-1, 1): plank('door', (sx * Wd / 4, -Dp / 2 - 0.035, Z0 / 2), (Wd / 2 - 0.04, 0.02, Z0 - 0.08), m_wood('#b98a5a', 'aqdoor', paint='#2fa3a0', age=0.7), seed=sx + 3)
    WATER = A.m_flat('#3fa8d8', 0.12, 3, 'aqwater')
    BACK = T.m_plaster('#2f7fc0', stripe=None, name='aqback', dirt=0.0)
    rbox('backwall', (0, Dp / 2 - 0.02, Z0 + H / 2), (Wd, 0.02, H), BACK, bevel=0.005)
    for sx in (-1, 1): rbox('sidewall', (sx * (Wd / 2 - 0.01), 0, Z0 + H / 2), (0.02, Dp, H), WATER, bevel=0.005)
    rbox('surface', (0, 0, Z0 + H - 0.08), (Wd - 0.03, Dp - 0.03, 0.01), A.m_flat('#8fd8f0', 0.15, 6, 'aqsurf'), bevel=0.002)
    FR = m_metal('#3a3a44', name='aqframe', age=0.3)
    for z in (Z0 + 0.01, Z0 + H):
        for sy in (-1, 1): rbox('fr', (0, sy * Dp / 2, z), (Wd + 0.02, 0.03, 0.03), FR, bevel=0.006)
        for sx in (-1, 1): rbox('fr', (sx * Wd / 2, 0, z), (0.03, Dp + 0.02, 0.03), FR, bevel=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1): rbox('frv', (sx * Wd / 2, sy * Dp / 2, Z0 + H / 2), (0.03, 0.03, H), FR, bevel=0.006)
    SAND = T.m_sand('aqsand', '#ead2a0')
    blob('sand', (0, 0.02, Z0 + 0.04), (Wd / 2 - 0.03, Dp / 2 - 0.03, 0.05), SAND, sub=1, seg=20)
    STN = m_rock()
    for k in range(4): pebble((R.uniform(-0.4, 0.4), R.uniform(-0.1, 0.15), Z0 + 0.08), R.uniform(0.04, 0.07), STN, k)
    SW = m_leaf('#2f7d35', '#4fb041', '#8fd06a', '#b5e28a', 'aqweed')
    def weeds(bm):
        out = []
        for k in range(7):
            x = -0.42 + k * 0.14 + R.uniform(-0.03, 0.03); base = V((x, 0.12, Z0 + 0.06))
            for f in blade(bm, base, V((R.uniform(-0.2, 0.2), -0.1, 1)).normalized(), V((1, 0, 0)), R.uniform(0.25, 0.42), 0.03, -0.1, segs=5): out.append((f, 0))
        return out
    mesh_from_blades('weeds', weeds, [SW])
    CO = A.m_flat('#ff7a8a', 0.15, 8, 'coral')
    for k in range(5):
        a = k * 1.2; tube('coral', [(0.3, 0.05, Z0 + 0.06), (0.3 + math.cos(a) * 0.06, 0.05 + math.sin(a) * 0.03, Z0 + 0.16 + 0.03 * k % 2)], [0.018, 0.01], CO, res=2)
    OR = A.m_flat('#ff8a2a', 0.1, 8, 'fishor'); WH = A.m_flat('#fff6ea', 0.05, 8, 'fishwh'); EY = A.m_flat('#1a1a22', 0.05, 6, 'eye')
    for (x, z, s, d) in ((-0.15, Z0 + 0.32, 1.0, 1), (0.22, Z0 + 0.22, 0.8, -1)):
        blob('fish', (x, -0.05, z), (0.08 * s, 0.035 * s, 0.05 * s), OR, sub=1, seg=12)
        blob('band', (x + 0.01 * d, -0.05, z), (0.012 * s, 0.037 * s, 0.045 * s), WH, sub=0, seg=8)
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.04 * s, depth=0.05 * s, location=(x - d * 0.09 * s, -0.05, z), rotation=(0, math.radians(90 * d), 0))
        bpy.context.object.data.materials.append(OR)
        blob('eye', (x + d * 0.055 * s, -0.08, z + 0.012), (0.009, 0.006, 0.009), EY, sub=0, seg=6)
    BU = A.m_flat('#e8fbff', 0.05, 6, 'bubble')
    for k in range(6): blob('bub', (-0.05 + 0.02 * k % 3, -0.04, Z0 + 0.25 + k * 0.05), (0.012 + 0.003 * k, 0.012 + 0.003 * k, 0.012 + 0.003 * k), BU, sub=0, seg=8)
    return 'akvaryum'

def i_lanterns():
    """Fener dizisi: iki kısa direk arasında sarkan üç kollu halat, üzerinde 5 renkli kağıt fener (kaburgalı, alt püsküllü)."""
    W = m_wood('#7e5232', 'lpost'); RP = m_rope()
    for x in (-0.9, 0.9): post('post', (x, 0, -0.03), (x, 0, 0.75), 0.03, W, seed=int(x * 10))
    rope_sag((-0.9, 0, 0.72), (0.9, 0, 0.72), 0.16, RP, thick=0.014)
    COLS = ['#ff7aa8', '#ffd447', '#7fd0e8', '#ff8a5c', '#8fd06a']
    for k in range(5):
        t = (k + 1) / 6; x = -0.9 + 1.8 * t; z = 0.72 - 0.16 * 4 * t * (1 - t)
        P = m_fabric(COLS[k], name='lp' + COLS[k])
        o = T.lathe('lan', [(0.03, z - 0.25), (0.09, z - 0.21), (0.1, z - 0.15), (0.09, z - 0.09), (0.03, z - 0.06)], P, segs=12)
        o.location.x = x
        for zz in (z - 0.21, z - 0.15, z - 0.09):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.09 + (0.008 if zz == z - 0.15 else 0), minor_radius=0.005, location=(x, 0, zz), major_segments=16, minor_segments=4)
            bpy.context.object.data.materials.append(A.m_flat('#8a5a36', 0.1, 6, 'lrib'))
        tube('hook', [(x, 0, z), (x, 0, z - 0.06)], [0.004, 0.004], RP, res=1)
        tube('tassel', [(x, 0, z - 0.25), (x, 0, z - 0.32)], [0.008, 0.004], m_rope('#e86f50', 'tas'), res=1)
    base_ring(-0.9, 0, 0.1, 3, flowers=1); base_ring(0.9, 0, 0.1, 4, flowers=1)
    return 'fener dizisi'

def i_palm():
    """Saksı palmiye: eskimiş pişmiş toprak saksı (kenarı kalın, dibi kirli), içinde toprak ve çakıl, kısa halkalı gövde,
    damarlı kürek yapraklar."""
    R = random.Random(4)
    POT = m_plaster('#d9774f', name='palmpot', dirt=0.4)
    T.lathe('pot', [(0.001, 0.0), (0.18, 0.0), (0.24, 0.32), (0.28, 0.34), (0.28, 0.4), (0.23, 0.4), (0.001, 0.36)], POT, segs=24)
    blob('soil', (0, 0, 0.37), (0.22, 0.22, 0.02), T.m_soil(), sub=0, seg=16)
    STN = m_rock()
    for k in range(5): pebble((math.cos(k * 1.3) * 0.13, math.sin(k * 1.3) * 0.13, 0.39), 0.03, STN, k)
    tube('trunk', [(0, 0, 0.36), (0.03, 0.0, 0.6), (0.0, 0.02, 0.85)], [0.05, 0.04, 0.035], A.m_bark(), res=4)
    LEAF = m_leaf('#3f9a3a', '#6cc94c', '#b5e26a', '#d8f08a', 'palmleaf')
    def fronds(bm):
        out = []
        for k in range(8):
            a = k * 2 * math.pi / 8 + R.uniform(-0.2, 0.2); d = V((math.cos(a), math.sin(a), 0.55)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V((0, 0.02, 0.85)), d, side, R.uniform(0.45, 0.6), 0.13, 1.0, segs=6, lift=0.25): out.append((f, 0))
        return out
    mesh_from_blades('fronds', fronds, [LEAF])
    return 'saksı palmiye'

def i_sandcastle():
    """Kumdan kale: ıslak-kuru geçişli kum dokusu, katmanlı ana kule + iki yan kule (mazgallı), kapı kemeri, sur duvarı,
    tepede bayrak, kabuklarla süslü; yanında kova ve kürek."""
    SND = T.m_sand('castle', '#e2c084'); WET = T.m_sand('wetcastle', '#c9a46a')
    blob('mound', (0, 0, 0.0), (0.6, 0.5, 0.12), WET, sub=1, seg=24)
    def tower(x, y, r, h, top):
        o = T.lathe('tower', [(0.001, 0.0), (r * 1.05, 0.0), (r, h * 0.5), (r * 0.95, h), (r * 1.1, h + 0.01), (r * 1.1, h + 0.06), (0.001, h + 0.06)], SND, segs=20, noise_amt=0.04)
        o.location = (x, y, top)
        for k in range(6):
            a = k * 2 * math.pi / 6
            rbox('crenel', (x + math.cos(a) * r * 0.95, y + math.sin(a) * r * 0.95, top + h + 0.09), (0.05, 0.05, 0.06), SND, rot=(0, 0, math.degrees(a)), bevel=0.012)
    tower(0, 0.05, 0.2, 0.35, 0.05); tower(0, 0.05, 0.13, 0.22, 0.46)
    tower(-0.32, -0.08, 0.1, 0.25, 0.04); tower(0.32, -0.08, 0.1, 0.25, 0.04)
    rbox('wall', (0, -0.12, 0.13), (0.62, 0.08, 0.16), SND, bevel=0.02)
    blob('gate', (0, -0.165, 0.1), (0.07, 0.02, 0.09), A.m_flat('#6a4e2c', 0.1, 6, 'gate'), sub=1, seg=12)
    tube('pole', [(0, 0.05, 0.74), (0, 0.05, 1.0)], [0.008, 0.007], m_wood('#c48a57', 'flagpole'), res=2)
    T.prism('flag', [(0, 0), (0.16, -0.04), (0, -0.09)], 0.005, A.m_flat('#e8463c', 0.08, 8, 'redflag'), loc=(0.005, 0.05, 0.99), bevel=0.002)
    SH = [A.m_flat('#ffb6a0', 0.1, 10, 'shell2'), A.m_flat('#f7d9c4', 0.1, 10, 'shell1')]
    for k in range(6):
        a = -0.6 + k * 0.25
        blob('shell', (math.cos(a - 1.57) * 0.21, -0.03 + math.sin(a - 1.57) * 0.2, 0.25 + 0.05 * (k % 2)), (0.018, 0.012, 0.022), SH[k % 2], sub=0, seg=8)
    B = A.m_flat('#2fa3d8', 0.1, 8, 'bucket')
    T.lathe('bucket', [(0.001, 0.0), (0.08, 0.0), (0.1, 0.16), (0.105, 0.17), (0.001, 0.02)], B, segs=16).location = (0.5, -0.3, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.1, minor_radius=0.006, location=(0.5, -0.3, 0.2), rotation=(math.radians(90), 0, 0), major_segments=16, minor_segments=4)
    bpy.context.object.data.materials.append(A.m_flat('#ffd447', 0.1, 6, 'handle'))
    tube('spade', [(-0.45, -0.3, 0.02), (-0.35, -0.2, 0.2)], [0.012, 0.012], A.m_flat('#ff7a59', 0.1, 6, 'spadeh'), res=2)
    blob('blade', (-0.48, -0.33, 0.015), (0.06, 0.045, 0.01), A.m_flat('#ff7a59', 0.1, 6, 'spadeb'), rot=(0, 0, 45), sub=1, seg=10)
    return 'kumdan kale'

def i_umbrella():
    """Plaj şemsiyesi: şeritli (mercan-krem-turkuaz), solmuş ve lekeli kumaş, fistolu kenar, ahşap direk + metal eklem,
    altında katlı çizgili havlu, kumda kabuk ve terlik."""
    CL = m_cloth('#f05d5e', '#fff1d6', stripes=8.0, name='umbr', age=1.0)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); ds = bm.faces.layers.int.new('ds')
    NA, NR = 48, 8; R0 = 0.95; Hh = 1.55
    rows = []
    for j in range(NR + 1):
        t = j / NR; r = R0 * t
        row = []
        for i in range(NA + 1):
            a = i / NA * 2 * math.pi
            sag = 0.05 * (math.sin(a * 8) ** 2) * t
            row.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, Hh + 0.32 * (1 - t ** 1.4) - sag)))
        rows.append(row)
    for j in range(NR):
        for i in range(NA):
            f = bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][i + 1], rows[j][i + 1])); f[ds] = 1
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))): lp[uvl].uv = (ii / NA, jj / NR)
    link_mesh('canopy', bm, [CL])
    W = m_wood('#c48a57', 'upole', age=0.6)
    tube('pole', [(0, 0, -0.05), (0, 0, Hh + 0.34)], [0.03, 0.025], W, res=3)
    blob('cap', (0, 0, Hh + 0.36), (0.04, 0.04, 0.04), W, sub=1, seg=10)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.01, location=(0, 0, Hh * 0.6), major_segments=12, minor_segments=4)
    bpy.context.object.data.materials.append(m_metal('#a9acb4', name='steel', age=0.4))
    TW = m_cloth('#2fb6c4', '#fff1d6', stripes=5.0, name='towel', age=0.6)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    g = [[bm.verts.new((-0.55 + 1.1 * i / 8, -0.35 + 0.7 * j / 4 - 0.2, 0.012 + 0.008 * math.sin(i * 1.3 + j))) for i in range(9)] for j in range(5)]
    for j in range(4):
        for i in range(8):
            f = bm.faces.new((g[j][i], g[j][i + 1], g[j + 1][i + 1], g[j + 1][i]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / 8, jj / 4)
    link_mesh('towel', bm, [TW])
    for sx in (-1, 1):
        blob('flipflop', (0.7 + sx * 0.07, -0.55, 0.012), (0.04, 0.09, 0.01), A.m_flat('#ffd447', 0.1, 6, 'ff'), rot=(0, 0, 10 * sx), sub=1, seg=10)
    SHL = A.m_flat('#f7d9c4', 0.1, 10, 'shell1')
    for j in range(5):
        b_ = math.radians(-50 + j * 25)
        blob('shell', (-0.7 + math.sin(b_) * 0.04, 0.4 + math.cos(b_) * 0.04, 0.012), (0.018, 0.05, 0.012), SHL, rot=(0, 0, -math.degrees(b_)), sub=0, seg=8)
    return 'şemsiye'

BUILDERS = {'i_bed': (i_bed, 512, None), 'i_bookshelf': (i_bookshelf, 512, None), 'i_lamp': (i_lamp, 512, None), 'i_rug': (i_rug, 512, None),
            'i_aquarium': (i_aquarium, 512, None), 'i_lanterns': (i_lanterns, 512, None), 'i_palm': (i_palm, 512, None),
            'i_sandcastle': (i_sandcastle, 512, None), 'i_umbrella': (i_umbrella, 512, None)}

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
