# Ön tasarım v5 (20 Ekim 2026, kullanıcının sanat yönü): resimsi yarı-gerçekçi stilize, canlı palet, soğuk mavi/mor renkli
# gölgeler, sinematik yönlü ışık, el boyaması hissi; düşük poligon + yumuşak gölgeleme. Referans görseller yalnız hedef
# kalite/hava; hiçbir şey kopyalanmadı, her şey kodla özgün.
#   /tmp/claude-0/bpyenv/bin/python -I scenes_v5.py -- <çıktı_klasörü> [g2 g3 g8]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', 'v4'))
import bpy, bmesh
from mathutils import Vector as V, noise as mnoise
import kit
from kit import srgb, mat, blob, tube, nodes_mat, ramp
import assets_v3 as A
from assets_v3 import m_leaf, m_bark, m_rock, m_flat, mesh_from_blades, blade, pebble, flower_heads, link_mesh
from assets_town import lush
import ski_mountain_v4 as SM

# ------------------------------------------------------------------ ortak: ışık, gökyüzü, uzak sis

def setup(samples=56, sun_yaw=-40, sun_pitch=38, exp=-0.35):
    sc = kit.reset(); sc.cycles.samples = samples
    sc.view_settings.exposure = exp
    for o in list(sc.objects):
        if o.type == 'LIGHT' and o.data.type == 'AREA': bpy.data.objects.remove(o)
        elif o.type == 'LIGHT':
            o.rotation_euler = (math.radians(90 - sun_pitch), 0, math.radians(sun_yaw)); o.data.energy = 3.6
            o.data.color = (1.0, 0.92, 0.80); o.data.angle = math.radians(3)
    return sc

def sky(sc, top='#3f7fd8', mid='#8fc4f2', hor='#dff1fb', clouds=0.55, strength=1.0, warm=None):
    """Boyalı gökyüzü: yükseklikle mavi geçiş + yumuşak bulut lekeleri. Ortam ışığı mavi → gölgeler soğuk mavi/mor."""
    w = sc.world; nt = w.node_tree; N = nt.nodes; L = nt.links
    bg = N['Background']; tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    stops = [(0.0, hor), (0.08, mid), (0.45, top)] if warm is None else [(0.0, warm), (0.06, hor), (0.18, mid), (0.5, top)]
    rp = ramp(nt, stops); L.new(sep.outputs['Z'], rp.inputs['Fac'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 4; nz.inputs['Roughness'].default_value = 0.55
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 3.2); L.new(tc.outputs['Generated'], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs['Vector'])
    cr = N.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.55; cr.inputs['From Max'].default_value = 0.72
    L.new(nz.outputs['Fac'], cr.inputs['Value'])
    hz = N.new('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = 0.02; hz.inputs['From Max'].default_value = 0.2; L.new(sep.outputs['Z'], hz.inputs['Value'])
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(cr.outputs[0], mul.inputs[0]); L.new(hz.outputs[0], mul.inputs[1])
    mul2 = N.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; mul2.inputs[1].default_value = clouds; L.new(mul.outputs[0], mul2.inputs[0])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb('#fbfdff')
    L.new(mul2.outputs[0], mx.inputs['Factor']); L.new(rp.outputs[0], mx.inputs[6]); L.new(mx.outputs[2], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength

def haze(m_name, base_hex, far_hex='#a9cbe6', near=18.0, far=70.0):
    """Atmosferik perspektif: uzaklaştıkça maviye çalan düz-boyalı malzeme (uzak dağlar için)."""
    def b(nt, bsdf):
        N = nt.nodes; L = nt.links
        cd = N.new('ShaderNodeCameraData'); mr = N.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = near; mr.inputs['From Max'].default_value = far; L.new(cd.outputs['View Z Depth'], mr.inputs['Value'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; nz.inputs['Detail'].default_value = 6
        tc = N.new('ShaderNodeTexCoord'); L.new(tc.outputs['Object'], nz.inputs['Vector'])
        sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
        # kaya (gri) / çim (yeşil) / kar (beyaz): yükseklik + gürültü
        hz = N.new('ShaderNodeMath'); hz.operation = 'MULTIPLY_ADD'; hz.inputs[1].default_value = 0.35
        L.new(nz.outputs['Fac'], hz.inputs[0]); L.new(sep.outputs['Z'], hz.inputs[2])
        rp = ramp(nt, base_hex); L.new(hz.outputs[0], rp.inputs['Fac'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb(far_hex)
        L.new(mr.outputs[0], mx.inputs['Factor']); L.new(rp.outputs[0], mx.inputs[6]); L.new(mx.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.9
    return nodes_mat(m_name, b)

def mountain(loc, r, h, seed, m, peaks=3):
    """Uzak dağ: gürültüyle şekillendirilmiş koni kümeleri (düşük poligon, yumuşak gölgeleme)."""
    R = random.Random(seed)
    for k in range(peaks):
        bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=r * R.uniform(0.6, 1.0), depth=h * R.uniform(0.6, 1.0),
                                        location=(loc[0] + R.uniform(-r, r) * 0.9, loc[1] + R.uniform(-r, r) * 0.4, loc[2]))
        o = bpy.context.object; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.subdivide(number_cuts=6); bpy.ops.object.mode_set(mode='OBJECT')
        for v in o.data.vertices:
            n = mnoise.noise(v.co * 0.25 + V((seed + k, 0, 0)))
            v.co += V((v.co.x, v.co.y, 0)).normalized() * n * r * 0.18 + V((0, 0, n * h * 0.12))
            if v.co.z < -h * 0.45: v.co.z = -h * 0.5
        o.location.z += o.dimensions.z * 0.5 - 0.2
        o.data.materials.append(m); A.smooth(o)

def painted_ground(name, size, hfun, cols, dirt=None, res=120, patch=0.18):
    """Zemin: yükseklik fonksiyonlu ızgara; renk = gürültülü iki-üç çim tonu (+ isteğe bağlı toprak lekeleri) — el boyaması dokusu."""
    bm = bmesh.new(); n = res; s = size
    for j in range(n + 1):
        for i in range(n + 1):
            x = -s / 2 + s * i / n; y = -s / 2 + s * j / n; bm.verts.new((x, y, hfun(x, y)))
    bm.verts.ensure_lookup_table()
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i; bm.faces.new([bm.verts[a], bm.verts[a + 1], bm.verts[a + n + 2], bm.verts[a + n + 1]])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    def b(nt, bsdf):
        N = nt.nodes; L = nt.links; tc = N.new('ShaderNodeTexCoord')
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = patch; nz.inputs['Detail'].default_value = 5
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, cols); L.new(nz.outputs['Fac'], rp.inputs['Fac'])
        out = rp.outputs[0]
        if dirt:
            n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = dirt[2]; n2.inputs['Detail'].default_value = 8
            L.new(tc.outputs['Object'], n2.inputs['Vector'])
            mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = dirt[0]; mr.inputs['From Max'].default_value = dirt[0] + 0.05
            L.new(n2.outputs['Fac'], mr.inputs['Value'])
            dr = ramp(nt, dirt[1]); L.new(n2.outputs['Fac'], dr.inputs['Fac'])
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(mr.outputs[0], mx.inputs['Factor']); L.new(out, mx.inputs[6]); L.new(dr.outputs[0], mx.inputs[7])
            out = mx.outputs[2]
        # fırça dokusu: küçük ölçekli açık-koyu oynama
        n3 = N.new('ShaderNodeTexNoise'); n3.inputs['Scale'].default_value = 9; L.new(tc.outputs['Object'], n3.inputs['Vector'])
        ov = N.new('ShaderNodeMix'); ov.data_type = 'RGBA'; ov.blend_type = 'OVERLAY'; ov.inputs['Factor'].default_value = 0.18
        L.new(out, ov.inputs[6]); L.new(n3.outputs['Color'], ov.inputs[7]); L.new(ov.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.95
    o.data.materials.append(nodes_mat(name + '_m', b)); A.smooth(o)
    return o

def grass_carpet(area, density, hfun, seed, h=(0.12, 0.26), mats=None, near=None):
    """Sık çim yaprakları (tek birleşik ağ). near=(x,y,r): kameraya yakın yerde sık, uzakta seyrek."""
    R = random.Random(seed)
    G1 = m_leaf('#2c6e2a', '#4fa83c', '#9bd457', '#c4ea8a', 'gA'); G2 = m_leaf('#3a7d2c', '#63b845', '#b8e06a', '#d6f0a0', 'gB')
    G3 = m_leaf('#5a7a2c', '#8fae3e', '#d2d86e', '#e8eaa0', 'gC')
    ms = mats or [G1, G2, G3]
    x0, x1, y0, y1 = area
    def build(bm):
        out = []
        cnt = int((x1 - x0) * (y1 - y0) * density)
        for k in range(cnt):
            x = R.uniform(x0, x1); y = R.uniform(y0, y1)
            if near:
                d = math.hypot(x - near[0], y - near[1])
                if d > near[2] and R.random() > (near[2] / d) ** 2: continue
            z = hfun(x, y) - 0.01
            b_ = R.uniform(0, 6.28); up = R.uniform(0.72, 0.97)
            dd = V((math.cos(b_) * (1 - up), math.sin(b_) * (1 - up), up)).normalized(); side = V((-math.sin(b_), math.cos(b_), 0))
            for f in blade(bm, V((x, y, z)), dd, side, R.uniform(*h), R.uniform(0.012, 0.02), R.uniform(0.1, 0.35), segs=2):
                out.append((f, k % len(ms)))
        return out
    return mesh_from_blades('grass', build, ms)

def broadleaf(loc, h, seed, cols=('#2f6e2b', '#4f9a37', '#8cc94e', '#b8e276'), spread=1.0, name='broad', droop=0.0):
    """Stilize yayvan ağaç: kıvrımlı kalın gövde + 3-5 kol + her kol ucunda yaprak kartı kümesi (yassı, katmanlı taç)."""
    R = random.Random(seed); x, y, z = loc
    BK = m_bark(); LF = m_leaf(*cols, name=name)
    k1 = V((x + R.uniform(-0.3, 0.3), y + R.uniform(-0.3, 0.3), z + h * 0.45)); top = V((x + R.uniform(-0.4, 0.4), y + R.uniform(-0.3, 0.3), z + h * 0.72))
    tube('trunk', [(x, y, z - 0.2), (x, y, z + h * 0.1), tuple(k1), tuple(top)], [h * 0.075, h * 0.055, h * 0.042, h * 0.03], BK, res=5)
    blob('root', (x, y, z + 0.05), (h * 0.11, h * 0.1, h * 0.05), BK, sub=1, seg=10)
    tips = []
    for a in range(R.randint(4, 6)):
        ang = a * 6.28 / 5 + R.uniform(-0.4, 0.4); L_ = h * R.uniform(0.28, 0.42) * spread
        base = k1 + (top - k1) * R.uniform(0.2, 0.9)
        tip = base + V((math.cos(ang) * L_, math.sin(ang) * L_, h * R.uniform(0.08, 0.25)))
        mid = (base + tip) / 2 + V((0, 0, h * 0.06))
        tube('arm', [tuple(base), tuple(mid), tuple(tip)], [h * 0.03, h * 0.02, h * 0.01], BK, res=3)
        tips.append(tip)
    tips.append(top + V((0, 0, h * 0.12)))
    def build(bm):
        out = []
        for t in tips:
            for c in range(R.randint(3, 4)):
                cc = t + V((R.uniform(-0.5, 0.5), R.uniform(-0.5, 0.5), R.uniform(-0.15, 0.25))) * h * 0.18
                rad = h * R.uniform(0.17, 0.24) * spread
                for q in range(int(70 * spread)):
                    th = R.uniform(0, 6.28); ph = R.uniform(-0.25, 1.2)
                    d = V((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph))).normalized()
                    p = cc + V((d.x * rad, d.y * rad, d.z * rad * 0.45))
                    od = (d + V((0, 0, -0.4 - droop))).normalized(); side = V((-od.y, od.x, 0)).normalized() if abs(od.z) < 0.99 else V((1, 0, 0))
                    for f in blade(bm, p, od, side, h * R.uniform(0.07, 0.11), h * 0.028, 0.2 + droop, segs=2): out.append((f, 0))
        return out
    mesh_from_blades(name + '_crown', build, [LF])

def willow(loc, h, seed):
    """Söğüt: kıvrık gövde, yukarı açılan kollar ve uzun sarkan yaprak saçakları."""
    R = random.Random(seed); x, y, z = loc; BK = m_bark(); LF = m_leaf('#3c7a33', '#6aa84a', '#a9d36a', '#cfe89a', 'willow')
    tube('wtrunk', [(x, y, z - 0.2), (x + 0.2, y, z + h * 0.3), (x - 0.1, y + 0.1, z + h * 0.6)], [h * 0.07, h * 0.05, h * 0.035], BK, res=5)
    crown = V((x - 0.1, y + 0.1, z + h * 0.62))
    def build(bm):
        out = []
        for s in range(46):
            th = R.uniform(0, 6.28); rr = R.uniform(0.1, 1.0) * h * 0.36
            st = crown + V((math.cos(th) * rr, math.sin(th) * rr, h * R.uniform(0.05, 0.3)))
            Lh = h * R.uniform(0.35, 0.6)
            for k in range(11):
                c = st + V((math.cos(th) * 0.05 * k, math.sin(th) * 0.05 * k, -Lh * k / 11))
                for sg in (-1, 1):
                    dd = V((math.cos(th + sg * 1.2), math.sin(th + sg * 1.2), -0.9)).normalized(); side = V((-dd.y, dd.x, 0)).normalized()
                    for f in blade(bm, c, dd, side, h * 0.06, h * 0.012, 0.1, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('willow_leaves', build, [LF])

def move_new(before, off, rot=0.0, scale=1.0):
    for o in bpy.context.scene.objects:
        if o.name not in before and o.type in ('MESH', 'CURVE'):
            o.location = V((o.location.x * scale, o.location.y * scale, o.location.z * scale)); o.scale = o.scale * scale
            o.rotation_euler.z += rot; o.location += V(off)

def water(name, size, loc, col='#2a8fa8', deep='#155f7a'):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc); o = bpy.context.object; o.name = name
    def b(nt, bsdf):
        N = nt.nodes; L = nt.links
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; tc = N.new('ShaderNodeTexCoord'); L.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.3, deep), (0.7, col)]); L.new(nz.outputs['Fac'], rp.inputs['Fac']); L.new(rp.outputs[0], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.04
        bm_ = N.new('ShaderNodeBump'); bm_.inputs['Strength'].default_value = 0.0
        n2 = N.new('ShaderNodeTexWave'); n2.inputs['Scale'].default_value = 2.5; L.new(tc.outputs['Object'], n2.inputs['Vector'])
        L.new(n2.outputs['Fac'], bm_.inputs['Height']); L.new(bm_.outputs[0], bsdf.inputs['Normal'])
    o.data.materials.append(nodes_mat(name + '_m', b)); return o

# ------------------------------------------------------------------ GÖRSEL 2: orman zemini makro

def leaf_litter(area, n, seed, hfun):
    """Yere düşmüş yapraklar: kırmızımsı kahve, turuncu, sarı ve solgun yeşil; hafif kıvrık, yere yatık."""
    R = random.Random(seed)
    LS = [m_leaf('#6e2a1a', '#9a3f22', '#c26a33', '#d79a5a', 'lf_red'), m_leaf('#7a4a1c', '#b87a2c', '#e0a84a', '#efcb7a', 'lf_or'),
          m_leaf('#6a5a2a', '#a08a3c', '#d4c060', '#e6d88a', 'lf_yel'), m_leaf('#4a5a2a', '#6f803c', '#a0a85a', '#c4c88a', 'lf_old')]
    x0, x1, y0, y1 = area
    def build(bm):
        out = []
        for k in range(n):
            x = R.uniform(x0, x1); y = R.uniform(y0, y1); z = hfun(x, y) + 0.004 + R.uniform(0, 0.01)
            a = R.uniform(0, 6.28); d = V((math.cos(a), math.sin(a), R.uniform(-0.05, 0.12))).normalized(); side = V((-d.y, d.x, 0))
            for f in blade(bm, V((x, y, z)), d, side, R.uniform(0.07, 0.13), R.uniform(0.028, 0.045), -0.25, segs=3): out.append((f, k % 4))
        return out
    return mesh_from_blades('litter', build, LS)

def mushroom(loc, h, seed, cap='#c4462e', spots=True, stem='#efe3cc'):
    R = random.Random(seed); x, y, z = loc
    ST = m_flat(stem, 0.08, 14, 'mst' + str(seed)); CP = m_flat(cap, 0.12, 6, 'mcp' + str(seed))
    lean = V((R.uniform(-0.15, 0.15), R.uniform(-0.15, 0.15), 1)).normalized()
    top = V(loc) + lean * h
    tube('mstem', [loc, tuple(V(loc) + lean * h * 0.5 + V((0.005, 0, 0))), tuple(top)], [h * 0.14, h * 0.11, h * 0.1], ST, res=3)
    blob('mcap', tuple(top + V((0, 0, h * 0.06))), (h * 0.42, h * 0.42, h * 0.22), CP, sub=1, seg=14)
    if spots:
        DT = m_flat('#fff6e6', 0.05, 8, 'mspot')
        for q in range(7):
            th = q * 0.9 + R.uniform(0, 0.4); rr = h * R.uniform(0.12, 0.3)
            blob('ms', tuple(top + V((math.cos(th) * rr, math.sin(th) * rr, h * 0.22 - rr * 0.35))), (h * 0.05, h * 0.05, h * 0.02), DT, sub=0, seg=6)

def twig(p0, p1, seed):
    R = random.Random(seed); m = (V(p0) + V(p1)) / 2 + V((R.uniform(-0.03, 0.03), R.uniform(-0.03, 0.03), 0.01))
    tube('twig', [p0, tuple(m), p1], [0.012, 0.009, 0.005], m_flat('#5a3f2a', 0.2, 12, 'twig'), res=2)

def scene_g2(out):
    sc = setup(samples=56, sun_yaw=-55, sun_pitch=30, exp=-0.3)
    sky(sc, top='#4a86d6', mid='#9cc9ee', hor='#e6f3fa', clouds=0.4, strength=1.1)
    hf = lambda x, y: 0.06 * mnoise.noise(V((x * 0.6, y * 0.6, 3))) + 0.03 * mnoise.noise(V((x * 2.2, y * 2.2, 1)))
    painted_ground('floor', 12, hf, [(0.2, '#3e5a26'), (0.5, '#5f7a2f'), (0.8, '#7a8a3a')],
                   dirt=(0.5, [(0.3, '#5a3a24'), (0.7, '#7a5232')], 0.9), res=110, patch=0.5)
    leaf_litter((-1.6, 1.6, -0.6, 2.2), 420, 3, hf)
    grass_carpet((-2.2, 2.2, -0.8, 3.5), 140, hf, 5, h=(0.06, 0.18), near=(0, 0.2, 1.2))
    for k, (x, y, s, c) in enumerate([(0.15, 0.55, 0.16, '#c4462e'), (0.32, 0.62, 0.11, '#c4462e'), (-0.45, 0.9, 0.13, '#b07a3a'),
                                      (-0.55, 1.0, 0.09, '#b07a3a'), (0.8, 1.4, 0.14, '#d0623a'), (-0.1, 1.6, 0.1, '#9a5ab0')]):
        mushroom((x, y, hf(x, y)), s, k, cap=c, spots=c in ('#c4462e', '#d0623a'))
    RK = m_rock((0.85, 1.05), name='frock')
    for k, (x, y, r) in enumerate([(-0.8, 0.4, 0.12), (0.6, 0.2, 0.07), (1.1, 1.0, 0.18), (-1.2, 1.6, 0.22), (0.4, 1.9, 0.09), (-0.2, 0.3, 0.04), (0.9, 0.5, 0.05)]):
        pebble((x, y, hf(x, y) + r * 0.25), r, RK, k)
    for k in range(9):
        R = random.Random(40 + k); x = R.uniform(-1.4, 1.4); y = R.uniform(0.2, 2.4); a = R.uniform(0, 6.28); L_ = R.uniform(0.15, 0.4)
        twig((x, y, hf(x, y) + 0.01), (x + math.cos(a) * L_, y + math.sin(a) * L_, hf(x + math.cos(a) * L_, y + math.sin(a) * L_) + 0.01), k)
    # devrik kütük + yosun
    BK = m_bark(); tube('log', [(-1.6, 2.4, 0.08), (-0.6, 2.7, 0.1), (0.4, 3.0, 0.09)], [0.13, 0.12, 0.11], BK, res=8)
    for x, y in ((-0.9, 1.3), (0.9, 0.9), (-0.3, 2.3), (1.3, 2.2)): SM.fern(x, y, hf(x, y), int(x * 100 + y * 7), size=0.42)
    lush((0.5, 1.1, hf(0.5, 1.1)), 0.1, 2, 9, h=(0.1, 0.22))
    # arka plan: kalın gövdeler (orman hissi)
    for k, (x, y) in enumerate([(-2.6, 5.5), (1.8, 6.5), (3.6, 4.8), (-4.0, 7.5)]):
        tube('bgtrunk', [(x, y, -0.2), (x, y, 3), (x, y, 6)], [0.45, 0.35, 0.3], BK, res=8)
    sc.render.resolution_percentage = 100
    cam = bpy.data.cameras.new('cam'); cam.dof.use_dof = True; cam.dof.focus_distance = 1.25; cam.dof.aperture_fstop = 2.2
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    kit.shoot(sc, os.path.join(out, 'g2_orman_zemini.png'), (0.1, 0.9, 0.08), 1.4, 0, 18, lens=30, size=(1600, 900))

# ------------------------------------------------------------------ GÖRSEL 3: biyom ağaçları

def scene_g3(out):
    sc = setup(samples=48, sun_yaw=-30, sun_pitch=40, exp=-0.4)
    sky(sc, top='#3d78d0', mid='#88bff0', hor='#dcefff', clouds=0.6, strength=1.05)
    hf = lambda x, y: 0.15 * mnoise.noise(V((x * 0.15, y * 0.15, 2)))
    painted_ground('ground', 60, hf, [(0.25, '#4a8f2e'), (0.55, '#66ad3a'), (0.85, '#8fc24a')], res=120, patch=0.12)
    grass_carpet((-9, 9, -3, 4), 40, hf, 11, h=(0.12, 0.28), near=(0, -1.0, 3.0))
    # soldan sağa: sonbahar · çam · söğüt · yayvan yaz ağacı · palmiye · karlı çam (her biyom bir örnek)
    broadleaf((-6.5, 4.5, 0), 4.2, 3, cols=('#8a2a14', '#c65020', '#f0a032', '#f7cf6a'), name='autumn')
    SM.pine_v4((-3.2, 5.5, 0), 5.6, 7, lod=1.0)
    willow((0.2, 4.6, 0), 4.6, 9)
    broadleaf((3.6, 5.2, 0), 4.8, 13, spread=1.25, name='summer')
    before = {o.name for o in bpy.context.scene.objects}; A.c_palm(); move_new(before, (6.6, 4.2, 0), rot=0.5, scale=1.0)
    for k, (x, y) in enumerate([(-8.5, 9), (-1.5, 10), (5.5, 11), (9.5, 8)]): SM.pine_v4((x, y, 0), 6.5, 30 + k, lod=1.0)
    RK = m_rock(name='g3rock')
    for k, (x, y, r) in enumerate([(-4.6, 2.0, 0.3), (2.2, 1.6, 0.22), (5.2, 2.6, 0.4)]): pebble((x, y, r * 0.2), r, RK, k)
    for x, y in ((-5.2, 2.8), (1.4, 2.6), (4.4, 3.4), (-2.0, 3.0)): SM.fern(x, y, hf(x, y), int(abs(x) * 31), size=0.6)
    flower_heads([(R_x, R_y, 0.22) for R_x, R_y in ((-1.0, 0.6), (-0.6, 1.1), (0.8, 0.9), (2.6, 0.4), (-3.4, 1.0))], random.Random(5), size=1.2)
    kit.shoot(sc, os.path.join(out, 'g3_agaclar.png'), (0.3, 4.0, 2.4), 13.5, 0, 9, lens=32, size=(1600, 900))

# ------------------------------------------------------------------ GÖRSEL 8: göl kenarı + çiçekli çayır

def scene_g8(out):
    sc = setup(samples=56, sun_yaw=-25, sun_pitch=35, exp=-0.38)
    sky(sc, top='#3a74cf', mid='#8cc2f0', hor='#e2f2fc', clouds=0.65, strength=1.05)
    def hf(x, y):
        z = 0.25 * mnoise.noise(V((x * 0.12, y * 0.12, 4))) + 0.02 * mnoise.noise(V((x, y, 1)))
        d = math.hypot((x - 2.0) / 7.0, (y - 14.0) / 3.6)          # göl çanağı
        if d < 1.25: z -= 0.7 * (1 - d / 1.25) ** 1.4
        return z
    painted_ground('meadow', 80, hf, [(0.25, '#3f8a2c'), (0.55, '#5fae38'), (0.85, '#93c84c')], res=150, patch=0.1)
    water('lake', 18, (2.0, 14.0, -0.18))
    MT = haze('mtn', [(0.2, '#4f8a3e'), (0.5, '#6f8a5a'), (0.75, '#8c949a'), (0.92, '#f2f5f8')], far_hex='#9cc0e0', near=40, far=160)
    for k, (x, y, r, h) in enumerate([(-34, 95, 16, 16), (6, 110, 22, 24), (40, 92, 15, 14), (-66, 112, 20, 18), (70, 116, 18, 17)]):
        mountain((x, y, 0), r, h, 50 + k, MT, peaks=2)
    grass_carpet((-6, 8, -3, 8), 55, hf, 21, h=(0.14, 0.32), near=(0.5, -0.5, 3.5))
    # çiçek tarlası: mavi, pembe, sarı, beyaz papatya — kümelenmiş
    R = random.Random(8); spots = []
    for c in range(18):
        cx = R.uniform(-5, 7); cy = R.uniform(-1.5, 9)
        for q in range(R.randint(4, 9)):
            x = cx + R.gauss(0, 0.35); y = cy + R.gauss(0, 0.35); spots.append((x, y, hf(x, y) + R.uniform(0.16, 0.3)))
    flower_heads(spots, R, size=0.9)
    BL = m_flat('#5a8fe8', 0.12, 9, 'p_blue')
    for k in range(70):
        x = R.uniform(-4, 6); y = R.uniform(0, 9); z = hf(x, y) + R.uniform(0.1, 0.2)
        blob('bluef', (x, y, z), (0.035, 0.035, 0.05), BL, sub=0, seg=6)
    broadleaf((-4.2, 8.5, hf(-4.2, 8.5)), 6.0, 41, spread=1.3, name='oakA')
    broadleaf((7.8, 9.8, hf(7.8, 9.8)), 5.4, 43, spread=1.2, name='oakB')
    RK = m_rock(name='g8rock')
    for k, (x, y, r) in enumerate([(-1.6, 10.2, 0.5), (5.2, 10.8, 0.35), (-0.4, 11.2, 0.25), (8.6, 13.4, 0.6)]): pebble((x, y, hf(x, y) + r * 0.2), r, RK, k)
    for x, y in ((-3.4, 7.4), (6.6, 8.6), (-5.2, 9.2)): SM.fern(x, y, hf(x, y), int(abs(x) * 17), size=0.7)
    kit.shoot(sc, os.path.join(out, 'g8_gol_cayir.png'), (1.2, 9.0, 1.4), 12.5, 0, 8, lens=30, size=(1600, 900))

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = args[0] if args else '/tmp'; which = args[1:] or ['g2', 'g3', 'g8']
    os.makedirs(out, exist_ok=True)
    for w in which:
        {'g2': scene_g2, 'g3': scene_g3, 'g8': scene_g8}[w](out); print('ok', w)
