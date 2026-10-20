# Görsel v4 ön tasarım (20 Ekim 2026, kullanıcı listesi): Yüzme Koyu + İskele zemine gömülü, ayrıntılı.
# Yüzme Koyu: havuz araziye oyulmuş (yamaç → kum şeridi → ıslak kum → sığ su → derin), kayalar yarı gömülü, çakıl öbekleri,
#   kamış + nilüfer + çiçek, kumdan suya basamak taşları, yıpranmış atlama iskelesi (kütük uçlarında yıllık halka), halat korkuluk.
# İskele: kumsaldan başlayan rampa (ilk tahtalar kuma gömülü), sudaki kazıklar (yosun bandı, midye/istiridye kabuğu, deniz yıldızı),
#   kesik kazık başlarında ve tahta uçlarında halka, aşınmış güverte (boşluk, çatlak, çivi pası), halat korkuluk, baba + bağlama halatı,
#   can simidi, fener, kova, sandık; kıyıda deniz kabuğu, çakıl, sahil otu, karaya vurmuş odun; su yarı saydam, kıyıda köpük.
# Dış çizgi yok; yumuşak boyalı/vinyl hava. Taslak (oyuna girmez): oyun sürümü onaydan sonra export_game.py yoluyla.
#   /tmp/claude-0/bpyenv/bin/python -I swim_pier_v4.py -- <çıktı_klasörü> [swim|pier|all]
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from assets_town import *
import assets_town as T
import assets_v3 as A
from assets_v3 import _shade
import kit
import bmesh
from mathutils import Vector as V, noise as mnoise

OUT = sys.argv[sys.argv.index('--') + 1]
WHAT = (sys.argv[sys.argv.index('--') + 2:] or ['all'])[0]
os.makedirs(OUT, exist_ok=True)
STATS = {}

# ------------------------------------------------------------------ malzemeler

def m_endgrain(hexc, name, axes=('X', 'Y'), rings=9.0, r=0.1):
    """Kesik ahşap yüzü: merkezden dışa yıllık halkalar (gürültüyle hafif dalgalı), koyu öz, ince ışınsal çatlaklar,
    dış kenarda koyu kabuk bandı. Halka sayısı yarıçapa göre (r)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs[0])
        cb = n.new('ShaderNodeCombineXYZ'); l.new(sep.outputs[axes[0]], cb.inputs['X']); l.new(sep.outputs[axes[1]], cb.inputs['Y'])
        ln = n.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; l.new(cb.outputs[0], ln.inputs[0])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0 / r; nz.inputs['Detail'].default_value = 3; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        wob = n.new('ShaderNodeMath'); wob.operation = 'MULTIPLY_ADD'; wob.inputs[1].default_value = r * 0.12
        l.new(nz.outputs['Fac'], wob.inputs[0]); l.new(ln.outputs['Value'], wob.inputs[2])
        fr = n.new('ShaderNodeMath'); fr.operation = 'MULTIPLY'; fr.inputs[1].default_value = rings * 2 * math.pi / r; l.new(wob.outputs[0], fr.inputs[0])
        si = n.new('ShaderNodeMath'); si.operation = 'SINE'; l.new(fr.outputs[0], si.inputs[0])
        rp = ramp(nt, [(0.0, _shade(hexc, 0.62)), (0.45, _shade(hexc, 0.95)), (1.0, _shade(hexc, 1.2))])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; l.new(si.outputs[0], mr.inputs['Value']); l.new(mr.outputs[0], rp.inputs['Fac'])
        col = rp.outputs[0]
        # öz (merkez) ve kabuk bandı
        core = n.new('ShaderNodeMapRange'); core.inputs['From Min'].default_value = r * 0.12; core.inputs['From Max'].default_value = r * 0.04
        l.new(ln.outputs['Value'], core.inputs['Value'])
        m1 = n.new('ShaderNodeMix'); m1.data_type = 'RGBA'; l.new(core.outputs[0], m1.inputs['Factor']); l.new(col, m1.inputs[6]); m1.inputs[7].default_value = srgb(_shade(hexc, 0.5))
        bark = n.new('ShaderNodeMapRange'); bark.inputs['From Min'].default_value = r * 0.86; bark.inputs['From Max'].default_value = r * 0.95
        l.new(ln.outputs['Value'], bark.inputs['Value'])
        m2 = n.new('ShaderNodeMix'); m2.data_type = 'RGBA'; l.new(bark.outputs[0], m2.inputs['Factor']); l.new(m1.outputs[2], m2.inputs[6]); m2.inputs[7].default_value = srgb('#4a3020')
        # ışınsal çatlaklar: açıya göre uzatılmış voronoi kenarı
        vo = n.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 1.4 / r; l.new(cb.outputs[0], vo.inputs['Vector'])
        ck = n.new('ShaderNodeMapRange'); ck.inputs['From Min'].default_value = 0.0; ck.inputs['From Max'].default_value = 0.02
        ck.inputs['To Min'].default_value = 0.7; ck.inputs['To Max'].default_value = 0.0; l.new(vo.outputs['Distance'], ck.inputs['Value'])
        m3 = n.new('ShaderNodeMix'); m3.data_type = 'RGBA'; l.new(ck.outputs[0], m3.inputs['Factor']); l.new(m2.outputs[2], m3.inputs[6]); m3.inputs[7].default_value = srgb('#2e2015')
        l.new(m3.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.85
    return nodes_mat(name, b)

def m_terrain(levels, name='terrain'):
    """Arazi: yüksekliğe göre derin kum → ıslak kum → kuru kum → çim (geçişler gürültüyle yırtık, keskin çizgi yok).
    levels = (su, ıslak üst, kum üst, çim başlangıcı)."""
    wz, wet, sand, grass = levels
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs[0])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 6; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        jit = n.new('ShaderNodeMath'); jit.operation = 'MULTIPLY_ADD'; jit.inputs[1].default_value = 0.09
        l.new(nz.outputs['Fac'], jit.inputs[0]); l.new(sep.outputs['Z'], jit.inputs[2])
        def band(a, b_):
            mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = a; mr.inputs['From Max'].default_value = b_
            l.new(jit.outputs[0], mr.inputs['Value']); return mr.outputs[0]
        def mix(f, c1, c2):
            m = n.new('ShaderNodeMix'); m.data_type = 'RGBA'; l.new(f, m.inputs['Factor'])
            if isinstance(c1, str): m.inputs[6].default_value = srgb(c1)
            else: l.new(c1, m.inputs[6])
            if isinstance(c2, str): m.inputs[7].default_value = srgb(c2)
            else: l.new(c2, m.inputs[7])
            return m.outputs[2]
        # çim: iki tonlu benek + kuru ot lekesi
        g1 = n.new('ShaderNodeTexNoise'); g1.inputs['Scale'].default_value = 0.9; g1.inputs['Detail'].default_value = 5; l.new(tc.outputs['Object'], g1.inputs['Vector'])
        gr = mix(g1.outputs['Fac'], '#4f8a2c', '#86b33f')
        g2 = n.new('ShaderNodeTexNoise'); g2.inputs['Scale'].default_value = 0.35; l.new(tc.outputs['Object'], g2.inputs['Vector'])
        dry = n.new('ShaderNodeMapRange'); dry.inputs['From Min'].default_value = 0.58; dry.inputs['From Max'].default_value = 0.7; dry.inputs['To Max'].default_value = 0.6
        l.new(g2.outputs['Fac'], dry.inputs['Value'])
        gr = mix(dry.outputs[0], gr, '#a3a35a')
        # kum: ince tane + rüzgâr çizgisi
        s1 = n.new('ShaderNodeTexNoise'); s1.inputs['Scale'].default_value = 40; l.new(tc.outputs['Object'], s1.inputs['Vector'])
        sd = mix(s1.outputs['Fac'], '#dcc28a', '#f0dcaa')
        wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 3.0; wv.inputs['Distortion'].default_value = 4; l.new(tc.outputs['Object'], wv.inputs['Vector'])
        wvr = n.new('ShaderNodeMapRange'); wvr.inputs['From Min'].default_value = 0.7; wvr.inputs['From Max'].default_value = 1.0; wvr.inputs['To Max'].default_value = 0.25
        l.new(wv.outputs['Fac'], wvr.inputs['Value'])
        sd = mix(wvr.outputs[0], sd, '#c8ad78')
        wetc = mix(s1.outputs['Fac'], '#a88a5c', '#bb9d6c')
        deep = mix(s1.outputs['Fac'], '#b59a68', '#c7ad7a')
        c = mix(band(wz - 0.05, wz + 0.005), deep, wetc)          # su altı kumu → ıslak kum
        c = mix(band(wet - 0.01, wet + 0.02), c, sd)              # ıslak → kuru kum
        c = mix(band(sand, grass), c, gr)                          # kum → çim (yırtık geçiş)
        l.new(c, bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.92
    return nodes_mat(name, b)

def m_sea(name='seaglass', deep='#1c8fb4', shallow='#4fd0d6', density=2.2):
    """Yarı saydam su: kırılma + hacim soğurması (derinleştikçe koyulaşan turkuaz, sığda kum görünür), hafif dalga pürüzü."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(shallow); b.inputs['Roughness'].default_value = 0.06
    b.inputs['IOR'].default_value = 1.33; b.inputs['Transmission Weight'].default_value = 0.92
    tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 4
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12; l.new(nz.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    va = n.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = srgb(deep); va.inputs['Density'].default_value = density
    l.new(va.outputs[0], n['Material Output'].inputs['Volume'])
    return m

# ------------------------------------------------------------------ yardımcılar

def log_post(name, base, top, r, wood, cap, seed=0, taper=0.9, tilt_cap=0.0):
    """Kütük direk + kesik ucunda halkalı kapak (yıllık halka görünür)."""
    o = post(name, base, top, r, wood, taper=taper, seed=seed)
    rr = r * taper
    c = cyl(name + '_cap', (top[0], top[1], top[2] + 0.002), rr * 0.97, 0.012, cap, verts=18, bevel=0)
    c.rotation_euler = (math.radians(tilt_cap), math.radians(tilt_cap * 0.6), 0)
    return o

def plank_end_caps(loc, size, axis, cap):
    """Tahtanın iki ucunda halka deseni (uçlardaki kesik yüzler)."""
    x, y, z = loc; sx, sy, sz = size
    for s in (-1, 1):
        if axis == 'x':
            rbox('pend', (x + s * (sx / 2 + 0.002), y, z), (0.004, sy * 0.96, sz * 0.9), cap, bevel=0)
        else:
            rbox('pend', (x, y + s * (sy / 2 + 0.002), z), (sx * 0.96, 0.004, sz * 0.9), cap, bevel=0)

def barnacles(c, r, z0, z1, seed, n=14):
    """Su çizgisi civarında kazığa yapışık küçük kabuklar (açık gri-beyaz, ağzı koyu)."""
    R = random.Random(seed); SH = A.m_flat('#e6e1d4', 0.2, 30, 'barnacle'); MO = A.m_flat('#3d3a36', 0.1, 10, 'barnmouth')
    for k in range(n):
        a = R.uniform(0, 6.28); z = R.uniform(z0, z1); rr = R.uniform(0.012, 0.022)
        p = V((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, z))
        o = blob('barn', tuple(p), (rr, rr, rr * 0.7), SH, sub=0, seg=8); o.rotation_euler = (0, math.radians(90), a)
        blob('barnm', tuple(p + V((math.cos(a), math.sin(a), 0)) * rr * 0.6), (rr * 0.35, rr * 0.35, rr * 0.2), MO, sub=0, seg=6).rotation_euler = (0, math.radians(90), a)

def shell(loc, s, seed, kind=0):
    """Deniz kabuğu: tarak (yelpaze, kaburgalı) ya da salyangoz (sarmal koni)."""
    R = random.Random(seed)
    if kind == 0:
        M = A.m_flat(R.choice(('#f4d2c0', '#f7e6cf', '#eec0a8')), 0.15, 25, 'scallop%d' % (seed % 3))
        bm = bmesh.new(); ctr = bm.verts.new((0, 0, 0)); ring = []
        N = 22
        for i in range(N + 1):
            a = math.radians(-70 + 140 * i / N); rr = s * (1 + 0.06 * math.cos(i * math.pi))   # kaburga dalgası
            ring.append(bm.verts.new((math.sin(a) * rr, math.cos(a) * rr, s * 0.25 * (1 + 0.3 * math.cos(i * math.pi)))))
        for i in range(N): bm.faces.new((ctr, ring[i], ring[i + 1]))
        o = A.link_mesh('scallop', bm, [M]); o.location = loc; o.rotation_euler = (0, 0, R.uniform(0, 6.28))
    else:
        M = A.m_flat(R.choice(('#e9d6b8', '#d8b894')), 0.2, 30, 'conch%d' % (seed % 2))
        prof = [(0.001, 0.0)] + [(s * (1 - t) * (0.55 + 0.12 * math.sin(t * 25)), s * 1.6 * t) for t in [i / 10 for i in range(1, 11)]]
        o = lathe('conch', prof, M, segs=12); o.location = loc; o.rotation_euler = (math.radians(80), 0, R.uniform(0, 6.28))
    return o

def reeds(c, radius, n, seed):
    """Kamış öbeği: uzun ince yapraklar + kahverengi püskül başlıklar."""
    R = random.Random(seed)
    L1 = m_leaf('#3d7a2c', '#5f9e3a', '#a6c55a', '#c8dc86', 'reed')
    def build(bm):
        out = []
        for k in range(n):
            a = R.uniform(0, 6.28); rr = R.uniform(0, radius)
            base = V((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr, c[2]))
            b_ = R.uniform(0, 6.28); d = V((math.cos(b_) * 0.12, math.sin(b_) * 0.12, 1)).normalized(); side = V((-math.sin(b_), math.cos(b_), 0))
            for f in blade(bm, base, d, side, R.uniform(0.45, 0.8), 0.018, R.uniform(0.05, 0.25), segs=4): out.append((f, 0))
        return out
    mesh_from_blades('reeds', build, [L1])
    CT = A.m_flat('#6b4526', 0.2, 20, 'cattail')
    for k in range(max(2, n // 5)):
        a = R.uniform(0, 6.28); rr = R.uniform(0, radius * 0.7); h = R.uniform(0.55, 0.85)
        x, y = c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr
        tube('stem', [(x, y, c[2]), (x + 0.01, y, c[2] + h)], [0.006, 0.005], A.m_flat('#6e8a3a', 0.1, 10, 'stem'), res=2)
        blob('tail', (x + 0.01, y, c[2] + h + 0.06), (0.022, 0.022, 0.07), CT, sub=1, seg=10)

def foam_along(points, seed, size=0.07):
    """Kıyı köpüğü: su çizgisi boyunca yassı, düzensiz beyaz parçalar (yan yana, arada boşluk)."""
    R = random.Random(seed); F = A.m_flat('#f6fbfb', 0.08, 12, 'foam')
    for k, (x, y, z) in enumerate(points):
        if R.random() < 0.25: continue
        s = size * R.uniform(0.6, 1.4)
        o = blob('foam', (x + R.uniform(-0.03, 0.03), y + R.uniform(-0.03, 0.03), z + 0.004), (s * 1.6, s, 0.006), F, sub=1, seg=10)
        o.rotation_euler = (0, 0, R.uniform(0, 6.28)); wobble(o, s * 0.25, 9.0, seed + k)

def terrain(name, W, D, res, height, mat_):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=int(res * D / W), size=1)
    g = bpy.context.object; g.name = name; g.scale = (W, D, 1); bpy.ops.object.transform_apply(scale=True)
    for v in g.data.vertices: v.co.z = height(v.co.x, v.co.y)
    g.data.materials.append(mat_); smooth(g)
    return g

def nz2(x, y, s=1.0, seed=0):
    return mnoise.noise(V((x * s, y * s, seed)))

def sky_light(sc):
    sc.cycles.samples = int(os.environ.get('SAMPLES', '48')); sc.view_settings.exposure = -0.45

def count(tag, objs):
    STATS[tag] = kit.tri_count(objs)

# ------------------------------------------------------------------ Yüzme Koyu

def build_swim():
    sc = reset(); sky_light(sc)
    R = random.Random(21)
    WZ = 0.06                                                    # su seviyesi
    def rad(a): return 1.0 + 0.12 * math.sin(a * 3 + 1) + 0.07 * math.sin(a * 5)
    def rr(x, y):                                                # havuz elipsine göre normalize uzaklık
        a = math.atan2(y / 0.85, x / 1.15); return math.hypot(x / 1.15, y / 0.85) / rad(a), a
    def H(x, y):
        d, a = rr(x, y)
        base = 0.3 + 0.05 * nz2(x, y, 0.6) + 0.12 * max(0.0, y - 1.2) * 0.4          # arkası hafif yükselir
        beach = max(0.0, -math.sin(a)) ** 2                                             # önde (−y) geniş kumsal, yumuşak eğim
        edge = 1.25 + 0.55 * beach
        if d < edge:
            t = max(0.0, (edge - d) / edge)
            depth = 0.62 * (t ** (0.9 if beach < 0.3 else 1.6))
            base -= depth + (0.26 if d < 1.0 else 0.26 * (edge - d) / max(0.01, edge - 1.0))
        return base
    TM = m_terrain((WZ, WZ + 0.035, WZ + 0.12, WZ + 0.2), 'swimground')
    g = terrain('ground', 7.5, 6.5, 220, H, TM)
    wtr = bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, -0.2, WZ)); w = bpy.context.object; w.name = 'water'
    w.scale = (0.75, 0.62, 1); w.data.materials.append(m_sea('poolglass', '#1688ad', '#56d4d2', 1.7))
    # köpük ve ıslak kenar: su çizgisi boyunca (arazinin suyu kestiği yer)
    pts = []
    for i in range(90):
        a = i / 90 * 2 * math.pi
        r0 = 0.3
        while r0 < 3.0 and H(math.cos(a) * r0 * 1.15, math.sin(a) * r0 * 0.85) < WZ: r0 += 0.01
        pts.append((math.cos(a) * r0 * 1.15, math.sin(a) * r0 * 0.85, WZ))
    foam_along(pts, 5, 0.06)
    STN = m_rock(moss_th=(1.12, 1.4), warm=('#a39586', '#bba996', '#d2c2a8'), name='poolrock')
    asset = []
    # yarı gömülü kenar kayaları (arka ve yanlar; ön kumsal açık)
    for i in range(26):
        a = i / 26 * 2 * math.pi + R.uniform(-0.06, 0.06)
        if -2.4 < a - math.pi * 2 * (a > math.pi) < -0.7: continue      # ön kumsal boş
        x, y = pts[int(a / (2 * math.pi) * 90) % 90][:2]
        x *= 1.06; y *= 1.06; r = R.uniform(0.15, 0.3)
        asset.append(rock((x, y, H(x, y) - r * 0.35), r, STN, i, sq=(1.0, 0.9, 0.7)))
    for k in range(6):                                               # büyük arka kayalar, yosunlu
        a = math.radians(40 + k * 22); x, y = math.cos(a) * 2.0 * 1.15, math.sin(a) * 1.85
        asset.append(rock((x, y, H(x, y) - 0.1), R.uniform(0.3, 0.42), STN, 60 + k, sq=(1.1, 0.9, 0.85)))
    # kumdan suya basamak taşları
    FL = m_rock(moss_th=(1.2, 1.4), warm=('#b9ab98', '#cbbca6', '#ddd0b8'), name='flatstone')
    for k, (x, y) in enumerate(((0.15, -2.15), (0.02, -1.75), (0.2, -1.38))):
        asset.append(rock((x, y, max(H(x, y), WZ - 0.03) + 0.01), 0.17, FL, 80 + k, sq=(1.2, 1.0, 0.32)))
    # çakıl öbekleri (kumsal + kaya dipleri)
    PB = m_rock(moss_th=(1.6, 1.9), warm=('#9a8f84', '#b8aa98', '#d6c8b2'), name='pebble')
    for k in range(70):
        a = R.uniform(math.radians(200), math.radians(340)); r0 = R.uniform(1.25, 2.1)
        x, y = math.cos(a) * r0 * 1.15, math.sin(a) * r0 * 0.85
        if k % 3 == 0: x += R.uniform(-0.1, 0.1)
        pr = R.uniform(0.02, 0.05); asset.append(pebble((x, y, H(x, y) + pr * 0.2), pr, PB, k))
    for k in range(5): shell((R.uniform(-1.2, 1.2), R.uniform(-2.3, -1.7), 0.0), R.uniform(0.04, 0.06), k, k % 2)
    # atlama iskelesi: kayalığın üstünden suya (yıpranmış, halkalı uçlar, halat korkuluk)
    PL = m_wood('#7a5232', 'divepile', age=1.4); CAP = m_endgrain('#b98a5a', 'divecap', r=0.05)
    DK = [m_wood(c, 'dived%d' % i, age=1.3) for i, c in enumerate(('#c99a66', '#b8875a', '#d3a873'))]
    PCAP = m_endgrain('#c49763', 'plankend', axes=('Y', 'Z'), r=0.03, rings=5)
    bx, by = 0.55, 1.05                                               # arka kenar
    for (px, py) in ((bx - 0.22, by + 0.45), (bx + 0.22, by + 0.45), (bx - 0.22, by - 0.15), (bx + 0.22, by - 0.15)):
        log_post('dpost', (px, py, H(px, py) - 0.25), (px, py, 0.42), 0.045, PL, CAP, seed=int(px * 10 + py * 7), tilt_cap=4)
    k = 0; y = by + 0.5
    while y > by - 0.55:
        sz = (0.56, 0.11, 0.035); loc = (bx + R_j(k) * 0.01, y, 0.44 + (by + 0.5 - y) * 0.02)
        plank('dplank', loc, sz, DK[k % 3], rot=(0, 0, R_j(k) * 1.5), seed=k + 5)
        plank_end_caps(loc, sz, 'x', PCAP)
        nail((loc[0] - 0.22, y, 0.46), (0, 0, 1), streak=False); nail((loc[0] + 0.22, y, 0.46), (0, 0, 1), streak=False)
        y -= 0.125; k += 1
    RP = m_rope()
    for sx in (-0.26, 0.26):
        log_post('rpost', (bx + sx, by + 0.5, 0.42), (bx + sx, by + 0.5, 0.72), 0.03, PL, CAP, seed=3)
        rope_sag((bx + sx, by + 0.5, 0.68), (bx + sx, by - 0.1, 0.55), 0.05, RP, thick=0.014)
    rope_wrap((bx - 0.22, by - 0.15, 0), 0.05, 0.25, 0.38, 2.2, RP, thick=0.012)
    # merdiven (paslı demir) ve simit
    I = m_metal('#c9ccd6', '#a8643a', 'steelrust')
    for sx in (-0.11, 0.11):
        tube('lrail', [(-1.05 + sx, -0.55, -0.2), (-1.12 + sx, -0.55, 0.3), (-1.28 + sx, -0.55, 0.36), (-1.36 + sx, -0.55, 0.22)], [0.018] * 4, I, res=4)
    for z in (-0.05, 0.1):
        tube('rung', [(-1.2, -0.55, z), (-0.97, -0.55, z)], [0.013, 0.013], I, res=2)
    RING = m_cloth('#ff7aa8', '#fff1d6', stripes=4.0, name='floatie')
    bpy.ops.mesh.primitive_torus_add(major_radius=0.18, minor_radius=0.065, location=(-0.25, -0.05, WZ + 0.03), major_segments=28, minor_segments=10)
    t = bpy.context.object; t.data.materials.append(RING); t.rotation_euler = (math.radians(5), 0, 0)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, 0)
    # nilüfer + çiçek, kamışlar, kenar bitkileri, çim öbekleri (zemine karışan dip)
    LP = m_leaf('#3f9a3a', '#5fb446', '#8fd06a', '#b5e26a', 'lilypad')
    for k, (x, y) in enumerate(((0.75, -0.25), (0.92, -0.05), (-0.65, 0.4), (0.55, 0.35))):
        o = blob('lily', (x, y, WZ + 0.005), (0.12, 0.12, 0.006), LP, sub=1, seg=16); o.rotation_euler = (0, 0, k)
    flower_heads([(0.75, -0.25, WZ + 0.03), (-0.65, 0.41, WZ + 0.03)], R, size=1.0)
    reeds((-1.55, 0.35, H(-1.55, 0.35) - 0.05), 0.28, 22, 4)
    reeds((1.6, 0.6, H(1.6, 0.6) - 0.05), 0.22, 16, 7)
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('plants', rosette([(1.9, -0.2), (-1.95, -0.4), (1.3, 1.65), (-1.2, 1.6)], R, sizes=(0.3, 0.45), leaves=9), [BL])
    for k in range(70):                                           # çim öbekleri: havuz çevresinde, kumdan çime geçişte sıklaşır
        a = R.uniform(0, 6.28); r0 = R.uniform(1.55, 2.9)
        x, y = math.cos(a) * r0 * 1.15, math.sin(a) * r0 * 0.85
        if H(x, y) < WZ + 0.2: continue
        lush((x, y, H(x, y) - 0.01), 0.12, 2, 300 + k, h=(0.14, 0.28))
    flower_heads([(1.7 + R.uniform(-0.3, 0.3), 1.0 + R.uniform(-0.3, 0.3), H(1.7, 1.0) + 0.2) for _ in range(4)], R)
    to_mesh_all()
    count('yuzme_koyu', [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name not in ('ground', 'water')])
    shoot(sc, f'{OUT}/yeni_yuzme_koyu.png', (0, -0.1, 0.1), 7.2, 18, 42, lens=45, size=(1280, 800))
    shoot(sc, f'{OUT}/yeni_yuzme_koyu_yakin.png', (0.5, 0.75, 0.35), 2.4, 30, 26, lens=50, size=(1280, 800))
    shoot(sc, f'{OUT}/yeni_yuzme_koyu_kumsal.png', (0.0, -1.5, 0.05), 2.2, -15, 30, lens=50, size=(1280, 800))

# ------------------------------------------------------------------ İskele

def build_pier():
    sc = reset(); sky_light(sc)
    R = random.Random(33)
    WZ = 0.0
    def shoreline(x): return 0.9 + 0.25 * math.sin(x * 0.8 + 0.4)
    def H(x, y):
        s = shoreline(x)
        d = y - s                                                # >0 kara, <0 deniz
        if d > 0.9: return 0.22 + 0.05 * nz2(x, y, 0.7) + (d - 0.9) * 0.06     # çimen düzlüğü
        if d > 0: return 0.02 + 0.2 * (d / 0.9) ** 1.4 + 0.015 * nz2(x, y, 3)   # kumsal yamacı (yumuşak)
        return max(-0.9, d * 0.28 + 0.02 + 0.02 * nz2(x, y, 2))                # sığdan derine
    TM = m_terrain((WZ, WZ + 0.05, WZ + 0.14, WZ + 0.22), 'shoreground')
    terrain('ground', 9.0, 9.0, 220, H, TM)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -2.5, WZ)); w = bpy.context.object; w.name = 'water'
    w.scale = (9.0, 7.0, 1); w.data.materials.append(m_sea('seaglass', '#127fa8', '#5fd6d4', 1.4))
    pts = []
    x = -4.4
    while x < 4.4:
        y = shoreline(x)
        while H(x, y) > WZ and y > -3: y -= 0.01
        pts.append((x, y, WZ)); pts.append((x + 0.03, y - 0.09, WZ))   # iki sıra: kıyıya vuran köpük şeridi
        x += 0.07
    foam_along(pts, 9, 0.07)
    # iskele: kumsaldan suya, −y yönünde
    PL = m_wood('#6f4a2c', 'pile', age=1.5); CAP = m_endgrain('#a37a4e', 'pilecap', r=0.12)
    DK = [m_wood(c, 'pdeck%d' % i, age=1.35) for i, c in enumerate(('#c99a66', '#b08052', '#d3a873', '#a77a4e'))]
    PCAP = m_endgrain('#c49763', 'deckend', axes=('X', 'Z'), r=0.035, rings=5)
    BCAP = m_endgrain('#9a6f45', 'beamend', axes=('X', 'Z'), r=0.06, rings=7)
    MOSS = m_plaster('#4f6a40', stripe=None, name='wetpile', dirt=0.0)
    RP = m_rope(); I = m_metal()
    Wd = 1.25; y0, y1 = 1.05, -3.6                                 # kara ucu → deniz ucu
    deck_z = lambda y: 0.42 if y < 0.55 else 0.42 - (y - 0.55) * 0.55   # kara tarafında rampa (kuma iner)
    piles = []
    for yy in (0.35, -0.75, -1.85, -2.95, -3.55):
        for sx in (-1, 1):
            x = sx * (Wd / 2 + 0.05); top = (0.78 if yy in (-3.55, 0.35) else deck_z(yy) - 0.06)
            log_post('pile', (x, yy, -0.95), (x + 0.01, yy, top), 0.12, PL, CAP, seed=int(yy * 9 + sx * 3), tilt_cap=6 if top > 0.6 else 0)
            if H(x, yy) < WZ:                                         # sudaki kazık: yosun bandı + kabuklar + halat
                cyl('wet', (x, yy, -0.12), 0.128, 0.3, MOSS, verts=16)
                barnacles((x, yy), 0.122, -0.2, 0.08, int(yy * 50 + sx * 7))
                rope_wrap((x, yy, 0), 0.125, 0.28, 0.38, 1.6, RP, thick=0.015, seed=int(yy))
            else:
                for k in range(4): pebble((x + R.uniform(-0.2, 0.2), yy + R.uniform(-0.2, 0.2), H(x, yy) + 0.01), R.uniform(0.04, 0.07), m_rock(moss_th=(1.6, 1.9), name='pierpeb'), k + 90)
            piles.append((x, yy))
    for yy in (0.35, -0.75, -1.85, -2.95, -3.55):                     # kiriş: uçlarında halka
        loc = (0, yy, deck_z(yy) - 0.09); sz = (Wd + 0.32, 0.12, 0.1)
        plank('beam', loc, sz, PL, seed=int(yy * 10) + 50)
        plank_end_caps(loc, sz, 'x', BCAP)
    k = 0; y = y0
    while y > y1:
        w_ = 0.165 + R.uniform(-0.01, 0.015)
        if k == 11: y -= w_; k += 1; continue                         # eksik tahta (boşluktan su görünür)
        z = deck_z(y) + (0.02 if k == 17 else 0)                      # biri hafif kalkık
        sz = (Wd + R.uniform(-0.04, 0.06), w_ - 0.014, 0.05); loc = (R_j(k) * 0.03, y - w_ / 2, z)
        plank('deck', loc, sz, DK[k % 4], rot=(math.degrees(math.atan2(-0.55, 1)) if y > 0.55 else (3 if k == 17 else 0), 0, R_j(k) * 1.2), seed=k + 60)
        plank_end_caps(loc, sz, 'x', PCAP)
        for xx in (-Wd / 2 + 0.07, 0.0, Wd / 2 - 0.07):
            if k % 2 == 0 or xx == 0.0: nail((xx, y - w_ / 2, z + 0.03), (0, 0, 1), streak=True)
        y -= w_; k += 1
    # kara ucunda kuma gömülü ilk tahtalar + çakıl
    for j in range(5):
        pebble((R.uniform(-0.8, 0.8), R.uniform(1.0, 1.4), H(0, 1.2) + 0.01), R.uniform(0.04, 0.08), m_rock(moss_th=(1.6, 1.9), name='rootpeb'), 120 + j)
    # halat korkuluk (bir yan), baba + bağlama halatı, can simidi, fener, kova, sandık
    side = Wd / 2 + 0.05
    for (a, b) in ((0.35, -0.75), (-0.75, -1.85), (-1.85, -2.95), (-2.95, -3.55)):
        rope_sag((side, a, 0.66), (side, b, 0.66), 0.1, RP, thick=0.02)
        log_post('rp', (side, b, deck_z(b) - 0.06), (side, b, 0.74), 0.05, PL, m_endgrain('#a37a4e', 'rpcap', r=0.05), seed=int(b * 3)) if b not in (-3.55,) else None
    bb = lathe('bollard', [(0.001, 0.0), (0.1, 0.0), (0.08, 0.13), (0.075, 0.21), (0.11, 0.25), (0.09, 0.29), (0.001, 0.3)], I, segs=16)
    bb.location = (-0.35, -3.25, deck_z(-3.25) + 0.03)
    tube('moor', [(-0.35, -3.25, 0.62), (-0.55, -3.5, 0.5), (-0.85, -3.75, 0.1), (-1.15, -3.9, -0.02)], [0.02] * 4, RP, res=4)
    LB = m_cloth('#ffffff', '#f05d5e', stripes=4.0, name='lifering')
    bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.055, location=(-side - 0.17, -2.95, 0.5), rotation=(0, math.radians(90), 0), major_segments=28, minor_segments=10)
    t = bpy.context.object; t.data.materials.append(LB)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.z, co.y) / (2 * math.pi)) % 1.0, 0)
    GL = m_glow()
    post('lamppost', (side, -3.55, 0.78), (side, -3.55, 1.45), 0.045, PL, seed=9)
    tube('arm', [(side, -3.55, 1.4), (side - 0.2, -3.55, 1.45), (side - 0.28, -3.55, 1.38)], [0.014] * 3, I, res=4)
    blob('lamp', (side - 0.28, -3.55, 1.26), (0.07, 0.07, 0.09), GL, sub=1, seg=12)
    crate((-0.3, -1.3, deck_z(-1.3) + 0.03), 0.36, DK[1], PL, yaw=14, seed=6)
    BK = m_wood('#a8693d', 'bucket')
    lathe('bucket', [(0.001, 0.0), (0.1, 0.0), (0.13, 0.22), (0.135, 0.24)], BK, segs=16).location = (0.3, -2.4, deck_z(-2.4) + 0.03)
    # deniz yıldızı (kazıkta), su yosunu
    ST = A.m_flat('#ff8a5c', 0.15, 12, 'starfish')
    sx_, sy_ = piles[2]
    for j in range(5):
        b = j * 2 * math.pi / 5
        blob('arm', (sx_ - 0.12, sy_ + math.cos(b) * 0.05, 0.12 + math.sin(b) * 0.05), (0.012, 0.055, 0.02), ST, rot=(math.degrees(b), 0, 0), sub=0, seg=8)
    SW = m_leaf('#2f6a3a', '#3f8a46', '#6aa858', '#8cc070', 'seaweed')
    def weeds(bm):
        out = []
        for (x, yy) in piles:
            if H(x, yy) >= WZ: continue
            for q in range(5):
                a = R.uniform(0, 6.28); base = V((x + math.cos(a) * 0.14, yy + math.sin(a) * 0.14, -0.5))
                d = V((math.cos(a) * 0.2, math.sin(a) * 0.2, 1)).normalized(); s_ = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, base, d, s_, R.uniform(0.3, 0.5), 0.02, 0.1, segs=4): out.append((f, 0))
        return out
    mesh_from_blades('seaweed', weeds, [SW])
    # kumsal: deniz kabukları, çakıl, karaya vurmuş odun (uçları halkalı), sahil otu
    for j in range(14):
        x = R.uniform(-3.8, 3.8); yy = shoreline(x) + R.uniform(-0.1, 0.6)
        shell((x, yy, H(x, yy) + 0.005), R.uniform(0.035, 0.06), 200 + j, j % 3 == 0)
    for j in range(40):
        x = R.uniform(-3.8, 3.8); yy = shoreline(x) + R.uniform(-0.15, 0.5)
        pr = R.uniform(0.02, 0.05); pebble((x, yy, H(x, yy) + pr * 0.2), pr, m_rock(moss_th=(1.6, 1.9), warm=('#9a8f84', '#b8aa98', '#d6c8b2'), name='beachpeb'), 300 + j)
    DW = m_wood('#b9a78e', 'driftwood', age=2.0); DWC = m_endgrain('#c8b498', 'driftend', axes=('Y', 'Z'), r=0.07)
    dx, dy = 2.1, shoreline(2.1) + 0.35
    tube('drift', [(dx - 0.5, dy, H(dx, dy) + 0.05), (dx, dy + 0.05, H(dx, dy) + 0.07), (dx + 0.45, dy - 0.04, H(dx, dy) + 0.05)], [0.07, 0.075, 0.06], DW, res=4)
    for ex, er in ((dx - 0.5, 0.07), (dx + 0.45, 0.06)):
        c = cyl('dcap', (ex + (0.001 if ex > dx else -0.001), dy, H(dx, dy) + 0.05), er * 0.97, 0.01, DWC, rot=(0, 90, 0), verts=16, bevel=0)
    for j in range(16):
        x = R.uniform(-4, 4); yy = shoreline(x) + R.uniform(0.55, 1.4)
        lush((x, yy, H(x, yy) - 0.01), 0.1, 2, 400 + j, h=(0.18, 0.34))
    to_mesh_all()
    count('iskele', [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name not in ('ground', 'water')])
    shoot(sc, f'{OUT}/yeni_iskele.png', (0, -1.0, 0.2), 8.2, 35, 34, lens=45, size=(1280, 800))
    shoot(sc, f'{OUT}/yeni_iskele_kazik.png', (0.65, -2.95, 0.2), 2.0, 60, 12, lens=50, size=(1280, 800))
    shoot(sc, f'{OUT}/yeni_iskele_kiyi.png', (0.3, 0.9, 0.2), 2.6, -30, 30, lens=50, size=(1280, 800))

if WHAT in ('swim', 'all'): build_swim()
if WHAT in ('pier', 'all'): build_pier()
print('UCGEN', STATS)
