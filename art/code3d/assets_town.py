# Ada yapıları ve süsleri v3 (kullanıcı isteği 15 Ekim 2026: "oyundaki mevcut bütün görselleri bu detaylarla kodla üret",
# önce tek tek onay, sonra oyundakilerle değiştirme). Yöntem assets_v3 ile aynı: prosedürel doku (ahşap damarı, aşınmış boya,
# halat, paslı demir, sıva, kumaş) → tek mesh → Cycles RENK + AO pişirme → tek doku + FBX.
# İlke: masal havası (canlı, yumuşak, sevimli), elle yapılmış hissi (hafif yamuk tahta, eğik direk), dış çizgi yok,
# dipte doğal geçiş (ot öbeği, çakıl, çiçek, yosun). Tasarımlar özgün; referanslardan hiçbir şey kopyalanmaz.
# Kullanım: python -I assets_town.py -- <çıktı_klasörü> [c_fence c_lantern ...]
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
import kit
import assets_v3 as A
from assets_v3 import m_wood, m_tile, m_rock, m_leaf, m_flat, m_bark, m_dirt, _shade, mesh_from_blades, tufts, rosette, flower_heads, pebble, blade, smooth, link_mesh
import mathutils
from mathutils import Vector as V, noise as mnoise

# ------------------------------------------------------------------ ek malzemeler

def m_rope(hexc='#cfae78', name='rope'):
    """Halat: boy boyunca eğik burgu çizgileri + lif gürültüsü."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        add = n.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 3.0
        l.new(sep.outputs['Y'], add.inputs[0]); l.new(sep.outputs['X'], add.inputs[2])
        mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 60.0; l.new(add.outputs[0], mul.inputs[0])
        s = n.new('ShaderNodeMath'); s.operation = 'SINE'; l.new(mul.outputs[0], s.inputs[0])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; l.new(s.outputs[0], mr.inputs['Value'])
        rp = ramp(nt, [(0.0, _shade(hexc, 0.7)), (0.6, hexc), (1.0, _shade(hexc, 1.15))]); l.new(mr.outputs[0], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_metal(hexc='#47434d', rust='#a8643a', name='iron'):
    """Dövme demir: koyu, hafif dalgalı; yer yer turuncu pas lekesi."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9; nz.inputs['Detail'].default_value = 5; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.35, _shade(hexc, 0.8)), (0.65, _shade(hexc, 1.25))]); l.new(nz.outputs['Fac'], rp.inputs['Fac'])
        nz2 = n.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 4; nz2.inputs['Detail'].default_value = 6; l.new(tc.outputs['Object'], nz2.inputs['Vector'])
        rr = n.new('ShaderNodeMapRange'); rr.interpolation_type = 'SMOOTHSTEP'; rr.inputs['From Min'].default_value = 0.6; rr.inputs['From Max'].default_value = 0.72
        l.new(nz2.outputs['Fac'], rr.inputs['Value'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb(rust)
        l.new(rr.outputs[0], mx.inputs['Factor']); l.new(rp.outputs[0], mx.inputs[6])
        l.new(mx.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_plaster(hexc, stripe=None, period=0.7, z0=0.0, name=None, dirt=0.35):
    """Sıva / boyalı yüzey: hafif lekeli; altta toprak kiri (nesne Z). stripe verilirse yatay bant (period m, yumuşak kenar)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs[0])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 5; nz.inputs['Detail'].default_value = 6; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        base = n.new('ShaderNodeMix'); base.data_type = 'RGBA'; base.blend_type = 'OVERLAY'; base.inputs['Factor'].default_value = 0.22
        base.inputs[6].default_value = srgb(hexc); l.new(nz.outputs['Color'], base.inputs[7])
        out = base.outputs[2]
        if stripe:
            # bant: z'yi gürültüyle biraz kaydır (fırça izi), fract → iki renk
            off = n.new('ShaderNodeMath'); off.operation = 'MULTIPLY_ADD'; off.inputs[1].default_value = 0.06
            l.new(nz.outputs['Fac'], off.inputs[0]); l.new(sep.outputs['Z'], off.inputs[2])
            sh = n.new('ShaderNodeMath'); sh.operation = 'SUBTRACT'; sh.inputs[1].default_value = z0; l.new(off.outputs[0], sh.inputs[0])
            dv = n.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = period; l.new(sh.outputs[0], dv.inputs[0])
            fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(dv.outputs[0], fr.inputs[0])
            mk = ramp(nt, [(0.0, '#000000'), (0.02, '#ffffff'), (0.5, '#ffffff'), (0.52, '#000000')]); l.new(fr.outputs[0], mk.inputs['Fac'])
            sc = n.new('ShaderNodeMix'); sc.data_type = 'RGBA'; sc.blend_type = 'OVERLAY'; sc.inputs['Factor'].default_value = 0.22
            sc.inputs[6].default_value = srgb(stripe); l.new(nz.outputs['Color'], sc.inputs[7])
            mm = n.new('ShaderNodeMix'); mm.data_type = 'RGBA'
            bw = n.new('ShaderNodeRGBToBW'); l.new(mk.outputs[0], bw.inputs[0])
            l.new(bw.outputs[0], mm.inputs['Factor']); l.new(out, mm.inputs[6]); l.new(sc.outputs[2], mm.inputs[7]); out = mm.outputs[2]
        # dip kiri
        dz = n.new('ShaderNodeMath'); dz.operation = 'MULTIPLY_ADD'; dz.inputs[1].default_value = 0.25
        l.new(nz.outputs['Fac'], dz.inputs[0]); l.new(sep.outputs['Z'], dz.inputs[2])
        dr = n.new('ShaderNodeMapRange'); dr.interpolation_type = 'SMOOTHSTEP'; dr.inputs['From Min'].default_value = z0 + 0.45; dr.inputs['From Max'].default_value = z0 + 0.1
        dr.inputs['To Max'].default_value = dirt; l.new(dz.outputs[0], dr.inputs['Value'])
        dm = n.new('ShaderNodeMix'); dm.data_type = 'RGBA'; dm.inputs[7].default_value = srgb('#7d6a4c')
        l.new(dr.outputs[0], dm.inputs['Factor']); l.new(out, dm.inputs[6])
        l.new(dm.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name or ('plaster' + hexc + (stripe or '')), b)

def m_cloth(c1, c2, stripes=6.0, name=None):
    """Tente kumaşı: grain u boyunca şeritler (yumuşak kenar), dokuma gürültüsü, kenara doğru hafif solma."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = stripes; l.new(sep.outputs['X'], mul.inputs[0])
        fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(mul.outputs[0], fr.inputs[0])
        mk = ramp(nt, [(0.0, '#000000'), (0.03, '#ffffff'), (0.5, '#ffffff'), (0.53, '#000000')]); l.new(fr.outputs[0], mk.inputs['Fac'])
        bw = n.new('ShaderNodeRGBToBW'); l.new(mk.outputs[0], bw.inputs[0])
        mm = n.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.inputs[6].default_value = srgb(c2); mm.inputs[7].default_value = srgb(c1)
        l.new(bw.outputs[0], mm.inputs['Factor'])
        mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (90, 90, 1); l.new(uv.outputs[0], mp.inputs['Vector'])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 2; l.new(mp.outputs[0], nz.inputs['Vector'])
        wv = n.new('ShaderNodeMix'); wv.data_type = 'RGBA'; wv.blend_type = 'OVERLAY'; wv.inputs['Factor'].default_value = 0.18
        l.new(mm.outputs[2], wv.inputs[6]); l.new(nz.outputs['Color'], wv.inputs[7])
        tc = n.new('ShaderNodeTexCoord'); nz2 = n.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 2.5; l.new(tc.outputs['Object'], nz2.inputs['Vector'])
        fd = n.new('ShaderNodeMix'); fd.data_type = 'RGBA'; fd.blend_type = 'SCREEN'; fd.inputs[7].default_value = srgb('#fff4dc')
        frr = n.new('ShaderNodeMapRange'); frr.inputs['From Min'].default_value = 0.5; frr.inputs['From Max'].default_value = 0.8; frr.inputs['To Max'].default_value = 0.25
        l.new(nz2.outputs['Fac'], frr.inputs['Value']); l.new(frr.outputs[0], fd.inputs['Factor']); l.new(wv.outputs[2], fd.inputs[6])
        l.new(fd.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name or ('cloth' + c1 + c2), b)

def m_glow(hexc='#ffd56a', name='glow'):
    """Fener camı: ortası parlak, kenarlara doğru turuncu (pişirmede sabit renk, oyunda ayrıca ışık yok)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        geo = n.new('ShaderNodeLayerWeight'); geo.inputs['Blend'].default_value = 0.4
        rp = ramp(nt, [(0.0, '#fff2b0'), (0.6, hexc), (1.0, '#f29a3a')]); l.new(geo.outputs['Facing'], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

# ------------------------------------------------------------------ ortak yardımcılar

def wobble(o, amt=0.012, scale=2.5, seed=0):
    """Elle yapılmış hissi: değiştiricileri uygula, köşeleri gürültüyle hafifçe kaydır (tahta dümdüz olmasın)."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception: pass
    mw = o.matrix_world
    for v in o.data.vertices:
        p = mw @ v.co
        d = V((mnoise.noise(p * scale + V((seed, 0, 0))), mnoise.noise(p * scale + V((0, seed + 7, 0))), mnoise.noise(p * scale + V((0, 0, seed + 13)))))
        v.co += mw.inverted().to_3x3() @ (d * amt)
    return o

def plank(name, loc, size, m, rot=(0, 0, 0), bevel=0.012, seed=None, amt=0.01):
    o = rbox(name, loc, size, m, rot=rot, bevel=bevel, seg=2)
    return wobble(o, amt, 3.0, seed if seed is not None else random.random() * 50)

def post(name, base, top, r, m, verts=10, taper=0.85, seed=0):
    """Hafif eğri, köşeli-yuvarlak kütük direk (uv: boyuna damar)."""
    mid = (V(base) + V(top)) / 2 + V((mnoise.noise(V((seed, 1, 2))) * 0.04, mnoise.noise(V((2, seed, 1))) * 0.04, 0))
    o = tube(name, [base, tuple(mid), top], [r, r * (1 + taper) / 2, r * taper], m, res=4)
    o.data.bevel_resolution = 2 if verts <= 10 else 3
    return o

def rope_wrap(center, r, z0, z1, turns, m, thick=0.016, axis='z'):
    """Direğe sarılmış halat (sarmal)."""
    pts = []; n = int(turns * 10)
    for i in range(n + 1):
        t = i / n; a = t * turns * 2 * math.pi
        p = V((math.cos(a) * r, math.sin(a) * r, z0 + (z1 - z0) * t))
        if axis == 'x': p = V((z0 + (z1 - z0) * t, math.cos(a) * r, math.sin(a) * r))
        elif axis == 'y': p = V((math.cos(a) * r, z0 + (z1 - z0) * t, math.sin(a) * r))
        pts.append(tuple(V(center) + p))
    return tube('rope', pts, [thick] * len(pts), m, res=2)

def rope_sag(a, b, sag, m, thick=0.02, n=6):
    pts = []
    for i in range(n + 1):
        t = i / n; p = V(a).lerp(V(b), t); p.z -= sag * 4 * t * (1 - t); pts.append(tuple(p))
    return tube('rope', pts, [thick] * len(pts), m, res=3)

def moss_cap(loc, r, seed=0):
    """Direk tepesine yosun yastığı + birkaç ot."""
    M = m_flat('#5f9a35', 0.3, 18, 'mossc')
    o = blob('moss', loc, (r, r * 0.95, r * 0.45), M, sub=1, seg=12)
    wobble(o, r * 0.18, 6.0, seed)
    return o

GRASS = None
def dress(radius, seed, n_tufts=8, flowers=3, pebbles=3, bushes=(), stone=None, exclude=None, at=()):
    """Dip süsü: ot öbekleri, birkaç çiçek, çakıl; isteğe bağlı rozet çalı merkezleri. exclude(x, y) → True ise yerleştirme."""
    R = random.Random(seed)
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    def ok(x, y): return exclude is None or not exclude(x, y)
    # tufts kendi rastgele dağıtır; dışlama için merkezleri elle seç
    centers = []
    for k in range(n_tufts * 4):
        if len(centers) >= n_tufts: break
        a = R.uniform(0, 6.28); r = R.uniform(radius * 0.35, radius)
        x, y = math.cos(a) * r, math.sin(a) * r
        if ok(x, y): centers.append((x, y))
    for k, (x, y) in enumerate(centers):
        mesh_from_blades('tuft', tufts((x, y, 0.0), 0.12, 1, seed * 31 + k, h=(0.16, 0.3)), [G1])
    for k, (x, y) in enumerate(at):                       # dip öbekleri (direk/duvar dibi): sık ve uzun
        mesh_from_blades('tuft', tufts((x, y, 0.0), 0.16, 3, seed * 17 + k, h=(0.2, 0.38)), [G1])
    if bushes:
        BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
        mesh_from_blades('rosette', rosette(list(bushes), R, sizes=(0.22, 0.34), leaves=8), [BL])
    spots = []
    for k in range(flowers * 4):
        if len(spots) >= flowers: break
        a = R.uniform(0, 6.28); r = R.uniform(radius * 0.4, radius * 0.95)
        x, y = math.cos(a) * r, math.sin(a) * r
        if ok(x, y): spots.append((x, y, R.uniform(0.16, 0.26)))
    if spots: flower_heads(spots, R)
    STN = stone or m_rock()
    for k in range(pebbles * 4):
        if pebbles <= 0: break
        a = R.uniform(0, 6.28); r = R.uniform(radius * 0.3, radius)
        x, y = math.cos(a) * r, math.sin(a) * r
        if not ok(x, y): continue
        rr = R.uniform(0.05, 0.1); pebble((x, y, rr * 0.35), rr, STN, seed + k); pebbles -= 1

def lathe(name, profile, m, segs=24, seed=0, noise_amt=0.0):
    """Profil (r, z) döndürülerek gövde (fener kulesi, fıçı…). uv grain: u = çevre, v = z."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    rows = []
    for (r, z) in profile:
        row = []
        for j in range(segs):
            a = j / segs * 2 * math.pi
            rr = r * (1 + noise_amt * mnoise.noise(V((math.cos(a) * 2, math.sin(a) * 2, z * 3 + seed))))
            row.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
        rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            f = bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                loop[uvl].uv = (jj / segs * 2 * math.pi * profile[0][0], profile[ii][1])
    o = link_mesh(name, bm, [m]); smooth(o)
    return o

def barrel(loc, r=0.22, h=0.5, wood=None, iron=None, rot=(0, 0, 0)):
    W = wood or m_wood('#a8693d', 'barrelw'); I = iron or m_metal()
    prof = [(r * (1 + 0.16 * (1 - ((z / (h / 2)) ** 2))), z) for z in [(-h / 2) + h * i / 8 for i in range(9)]]
    o = lathe('barrel', [(0.001, -h / 2)] + prof + [(0.001, h / 2)], W, segs=20)
    for z in (-h * 0.36, h * 0.36):
        rr = r * (1 + 0.16 * (1 - ((z / (h / 2)) ** 2))) + 0.008
        bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=0.012, location=(0, 0, z), major_segments=24, minor_segments=5)
        t = bpy.context.object; t.data.materials.append(I); t.parent = o
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.update()
    for c in list(o.children):
        mw = c.matrix_world.copy(); c.parent = None; c.matrix_world = mw
    return o

def crate(loc, s, m, m2, yaw=0, open_top=False, seed=0):
    """Tahta sandık: çerçeve + yatay çıtalar + çapraz destek; elle yapılmış yamukluk."""
    cx, cy, cz = loc; out = []
    def P(dx, dy, dz):
        a = math.radians(yaw); return (cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a), cz + dz)
    out.append(rbox('core', P(0, 0, s / 2), (s * 0.94, s * 0.94, s * (0.7 if open_top else 0.94)), m_wood('#5d3a22', 'cratein'), rot=(0, 0, yaw), bevel=0))
    if open_top: out[-1].location.z = cz + s * 0.35
    k = 0
    for side in range(4):
        ang = side * 90
        for row in range(3):
            z = s * (0.18 + row * 0.32)
            d = s / 2
            dx, dy = [(0, -d), (d, 0), (0, d), (-d, 0)][side]
            sz = (s * 0.92, 0.035, s * 0.27) if side % 2 == 0 else (0.035, s * 0.92, s * 0.27)
            out.append(plank('slat', P(dx, dy, z), sz, m if (k % 3) else m2, rot=(0, 0, yaw), seed=seed * 9 + k, amt=0.006)); k += 1
        dx, dy = [(0, -s / 2 - 0.02), (s / 2 + 0.02, 0), (0, s / 2 + 0.02), (-s / 2 - 0.02, 0)][side]
        L = s * 1.18
        if side % 2 == 0: out.append(plank('brace', P(dx, dy, s / 2), (L, 0.03, 0.07), m2, rot=(0, 40 * (1 if side == 0 else -1), yaw), seed=seed + side, amt=0.005))
        else: out.append(plank('brace', P(dx, dy, s / 2), (0.03, L, 0.07), m2, rot=(40, 0, yaw), seed=seed + side, amt=0.005))
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(rbox('edge', P(sx * s / 2, sy * s / 2, s / 2), (0.06, 0.06, s * 1.0), m2, rot=(0, 0, yaw), bevel=0.012))
    if not open_top:
        for i in range(4):
            out.append(plank('lid', P(0, -s * 0.36 + i * s * 0.24, s), (s * 1.02, s * 0.22, 0.035), m if i % 2 else m2, rot=(0, 0, yaw), seed=seed * 3 + i, amt=0.006))
    return out

# ------------------------------------------------------------------ süsler

def c_fence():
    """Çit: üç kalın, hafif eğri kütük direk (tepede yosun yastığı), iki yuvarlak kütük çubuk (biri hafif yamuk),
    halat bağlar, bir direğe sarılan çiçekli sarmaşık; dipte sık ot öbekleri, çalı ve çiçek."""
    W = m_wood('#9c6a40', 'fencew'); W2 = m_wood('#b07b4a', 'fencew2'); RP = m_rope()
    xs = (-0.8, 0.0, 0.8)
    for i, x in enumerate(xs):
        top = (x + (0.02 if i == 1 else -0.03), 0.01 * i, 0.95 + 0.07 * (i % 2))
        post('post', (x, 0, -0.05), top, 0.105, W, seed=i)
        moss_cap((top[0], top[1], top[2] + 0.01), 0.1, seed=i)
        for z in (0.7, 0.36):
            rope_wrap((x, 0, 0), 0.12, z - 0.06, z + 0.06, 2.4, RP, thick=0.016)
    tube('rail', [(-1.0, 0.1, 0.69), (0.0, 0.12, 0.72), (1.0, 0.1, 0.7)], [0.062, 0.066, 0.06], W2, res=6)
    tube('rail', [(-1.0, 0.1, 0.32), (0.0, 0.13, 0.36), (1.0, 0.1, 0.41)], [0.058, 0.062, 0.056], W, res=6)
    for x in (-1.0, 1.0):                                 # çubuk uçlarında kesik yüzey (açık ahşap)
        for z in (0.7, 0.37 + 0.04 * (x > 0)):
            cyl('cut', (x, 0.1, z), 0.058, 0.02, m_wood('#e0b884', 'endgrain'), rot=(0, 90, 0), verts=12)
    # sarmaşık (orta direk) + çiçekler
    V1 = m_flat('#3f7f2f', 0.2, 8, 'vine'); LV = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'vineleaf')
    pts = []; leafs = []
    for i in range(22):
        t = i / 21; a = t * 2.6 * 2 * math.pi
        p = (0.02 + math.cos(a) * 0.115, math.sin(a) * 0.115, 0.04 + t * 0.85); pts.append(p)
        if i % 2 == 0 and i > 0: leafs.append((p, a))
    tube('vine', pts, [0.009] * len(pts), V1, res=2)
    def lv(bm):
        out = []
        for (p, a) in leafs:
            d = V((math.cos(a), math.sin(a), 0.4)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V(p), d, side, 0.11, 0.045, 0.4, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('vleaves', lv, [LV])
    R = random.Random(1)
    flower_heads([(0.14, -0.05, 0.55), (-0.08, -0.1, 0.78), (0.1, 0.08, 0.3)], R)
    dress(1.0, 4, n_tufts=5, flowers=4, pebbles=3, bushes=[(-0.42, -0.2), (0.45, 0.22)], at=[(x, 0.0) for x in xs])
    return 'çit'

def prism(name, pts2d, depth, m, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.012):
    """2B çokgen (x, z) → y boyunca kalınlık verilmiş levha (ok tahtası, yıldız…). grain: u = x, v = z."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    fr = [bm.verts.new((x, -depth / 2, z)) for x, z in pts2d]; bk = [bm.verts.new((x, depth / 2, z)) for x, z in pts2d]
    faces = [bm.faces.new(list(reversed(fr))), bm.faces.new(bk)]
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n; faces.append(bm.faces.new((fr[i], fr[j], bk[j], bk[i])))
    for f in faces:
        for lp in f.loops: lp[uvl].uv = (lp.vert.co.x, lp.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = link_mesh(name, bm, [m]); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    if bevel:
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    return o

def c_lantern():
    """Sokak feneri (tombul oranlar): kalın, hafif eğik kütük direk, kıvrık demir kol, büyük sıcak ışıklı fener
    (demir kafes, tepe şapkası, halka), direğe sarılan yapraklı sarmaşık; dipte taş çemberi, ot, çiçek."""
    W = m_wood('#7e5232', 'lampw'); I = m_metal(); GL = m_glow()
    post('post', (0, 0, -0.05), (0.03, 0.02, 1.6), 0.115, W, taper=0.8, seed=2)
    moss_cap((0.03, 0.02, 1.62), 0.1, seed=3)
    tube('arm', [(0.05, 0.02, 1.48), (0.3, 0.02, 1.6), (0.5, 0.02, 1.55), (0.56, 0.02, 1.44)], [0.028, 0.026, 0.024, 0.022], I, res=6)
    tube('brace', [(0.08, 0.02, 1.22), (0.25, 0.02, 1.33), (0.38, 0.02, 1.56)], [0.016, 0.016, 0.016], I, res=4)
    blob('curl', (0.12, 0.02, 1.56), (0.04, 0.012, 0.04), I, sub=1, seg=12)
    cx, cz = 0.56, 1.17
    rbox('glass', (cx, 0.02, cz), (0.22, 0.22, 0.3), GL, bevel=0.03)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox('bar', (cx + sx * 0.115, 0.02 + sy * 0.115, cz), (0.032, 0.032, 0.34), I, bevel=0.008)
    rbox('base', (cx, 0.02, cz - 0.18), (0.28, 0.28, 0.05), I, bevel=0.012)
    blob('drop', (cx, 0.02, cz - 0.23), (0.05, 0.05, 0.04), I, sub=1, seg=12)
    lathe('roof', [(0.18, cz + 0.15), (0.185, cz + 0.18), (0.1, cz + 0.27), (0.02, cz + 0.32), (0.001, cz + 0.33)], I, segs=4).location = (cx, 0.02, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.011, location=(cx, 0.02, cz + 0.37), rotation=(math.radians(90), 0, 0), major_segments=12, minor_segments=5)
    bpy.context.object.data.materials.append(I)
    V1 = m_flat('#3f7f2f', 0.2, 8, 'vine'); LV = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'vineleaf')
    pts = []; leafs = []
    for i in range(30):
        t = i / 29; a = t * 3.0 * 2 * math.pi
        r = 0.125 - 0.02 * t
        p = (math.cos(a) * r, math.sin(a) * r, 0.04 + t * 1.15); pts.append(p)
        if i % 2 == 0 and i > 0: leafs.append((p, a))
    tube('vine', pts, [0.01] * len(pts), V1, res=2)
    def lv(bm):
        out = []
        for (p, a) in leafs:
            d = V((math.cos(a), math.sin(a), 0.45)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V(p), d, side, 0.13, 0.05, 0.4, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('vleaves', lv, [LV])
    R = random.Random(2)
    flower_heads([(0.1, -0.12, 0.62), (-0.12, 0.05, 0.9)], R)
    STN = m_rock()
    for k in range(6):
        a = k * 1.05 + 0.3
        pebble((math.cos(a) * 0.22, math.sin(a) * 0.22, 0.04), 0.09 + 0.025 * (k % 2), STN, k)
    dress(0.6, 9, n_tufts=4, flowers=3, pebbles=1, stone=STN, at=[(0.15, 0.12), (-0.12, -0.15)])
    return 'fener'

def c_sign():
    """Yön tabelası (tombul): kalın kütük direk + küçük kiremit şapka, üç ok tahtası (farklı yönlere, aşınmış boyalı:
    turkuaz, mercan, krem) üzerinde boyalı büyük simgeler (yazı yok — çocuk okumadan anlasın: ev, yıldız, deniz kabuğu),
    çivi başları; dipte çiçek ve ot."""
    W = m_wood('#8a5a36', 'signpost')
    post('post', (0, 0, -0.05), (0.01, 0, 1.55), 0.1, W, taper=0.85, seed=4)
    roof = m_tile('#e0684a', 'signroof')
    for s_ in (-1, 1):
        plank('roof', (0.0, s_ * 0.1, 1.62), (0.36, 0.24, 0.04), roof, rot=(s_ * 32, 0, 0), seed=s_ + 2)
    cyl('ridge', (0, 0, 1.69), 0.035, 0.4, roof, rot=(0, 90, 0), verts=10)
    BOARDS = [('#2fa3a0', 25, 1.28), ('#e86f50', 160, 0.98), ('#f4e6c6', -40, 0.68)]
    ICON = [m_flat('#fff6e6', 0.05, 8, 'ic_w'), m_flat('#ffd447', 0.08, 8, 'ic_y'), m_flat('#e86f50', 0.08, 8, 'ic_c')]
    NAIL = m_metal(name='nail')
    L, Hb, T = 0.78, 0.24, 0.06
    arrow = [(-0.06, -Hb / 2), (L - 0.14, -Hb / 2), (L, 0), (L - 0.14, Hb / 2), (-0.06, Hb / 2)]
    for i, (col, yaw, z) in enumerate(BOARDS):
        m = m_wood('#b98a5a', f'board{i}', paint=col)
        a = math.radians(yaw)
        prism('board', arrow, T, m, loc=(math.cos(a) * 0.1, math.sin(a) * 0.1, z), rot=(0, R_i(i) * 3, yaw))
        bpy.context.view_layer.update()
        mw = bpy.context.scene.objects[-1].matrix_world if False else None
        # simge: tahtanın ön yüzünde (yerel -y), ortada
        fw = V((math.cos(a), math.sin(a), 0)); nrm = V((math.sin(a), -math.cos(a), 0))
        c = V((math.cos(a) * 0.1, math.sin(a) * 0.1, z)) + fw * (L * 0.45) + nrm * (T / 2 + 0.006)
        ic = ICON[i]
        if i == 0:   # ev
            prism('ic', [(-0.07, -0.07), (0.07, -0.07), (0.07, 0.02), (0.0, 0.08), (-0.07, 0.02)], 0.012, ic, loc=tuple(c), rot=(0, 0, yaw), bevel=0.004)
        elif i == 1:  # yıldız
            pts = []
            for k in range(10):
                b_ = math.pi / 2 + k * math.pi / 5; rr = 0.085 if k % 2 == 0 else 0.038
                pts.append((math.cos(b_) * rr, math.sin(b_) * rr))
            prism('ic', pts, 0.012, ic, loc=tuple(c), rot=(0, 0, yaw), bevel=0.004)
        else:         # deniz kabuğu (yelpaze)
            pts = [(0, -0.07)] + [(math.sin(math.radians(t)) * 0.085, -0.07 + math.cos(math.radians(t)) * 0.13 * (0.92 + 0.08 * math.cos(math.radians(t * 5)))) for t in range(-60, 61, 12)]
            prism('ic', pts, 0.012, ic, loc=tuple(c), rot=(0, 0, yaw), bevel=0.004)
        for d in (0.02, L - 0.24):
            p = V((math.cos(a) * 0.1, math.sin(a) * 0.1, z)) + fw * d + nrm * (T / 2 + 0.004)
            blob('nail', tuple(p), (0.018, 0.018, 0.018), NAIL, sub=0, seg=8)
    dress(0.65, 12, n_tufts=4, flowers=5, pebbles=3, bushes=[(0.25, -0.22)], at=[(0.12, 0.1), (-0.1, -0.12)])
    return 'tabela'

def R_i(i): return (-1, 1, -0.5)[i % 3]

def c_crates():
    """Liman yükü: iki üst üste sandık (üstteki açık, içi meyve dolu), yanda fıçı, bağlı çuval ve kangal halat; dip kumlu."""
    W = m_wood('#b07b4a', 'cratew'); W2 = m_wood('#8f5d36', 'cratew2')
    crate((-0.2, 0.05, 0.0), 0.62, W, W2, yaw=8, seed=1)
    crate((-0.15, 0.0, 0.62), 0.5, W, W2, yaw=-14, open_top=True, seed=2)
    # meyveler (açık sandıkta): portakal, hindistan cevizi, muz demeti
    OR = m_flat('#f39a2e', 0.2, 14, 'orange'); CO = m_flat('#86662f', 0.35, 9, 'coco'); BA = m_flat('#f4d34c', 0.15, 6, 'banana')
    R = random.Random(3)
    for k in range(7):
        a = k * 2.4; r = 0.06 + 0.12 * math.sqrt(k / 7)
        blob('fruit', (-0.15 + math.cos(a) * r, math.sin(a) * r, 0.62 + 0.42 + R.uniform(0, 0.04)), (0.07, 0.07, 0.065), OR if k % 3 else CO, sub=0, seg=12)
    for k in range(4):
        tube('banana', [(-0.05 + k * 0.03, -0.12, 1.08), (0.0 + k * 0.03, -0.05, 1.15), (0.02 + k * 0.03, 0.05, 1.14)], [0.025, 0.03, 0.015], BA, res=4)
    barrel((0.5, -0.12, 0.27), r=0.2, h=0.52)
    # çuval: yumuşak, bağlı ağız
    SK = m_flat('#d9c08e', 0.3, 30, 'sack'); RP = m_rope()
    s = blob('sack', (0.42, 0.42, 0.2), (0.22, 0.2, 0.22), SK, sub=2, seg=16); wobble(s, 0.03, 4.0, 2)
    blob('neck', (0.42, 0.42, 0.44), (0.07, 0.07, 0.08), SK, sub=1, seg=12)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.013, location=(0.42, 0.42, 0.42), major_segments=16, minor_segments=5)
    bpy.context.object.data.materials.append(RP)
    # kangal halat (yerde)
    pts = []
    for i in range(60):
        t = i / 59; a = t * 3 * 2 * math.pi; r = 0.17 - 0.02 * math.floor(t * 3)
        pts.append((-0.55 + math.cos(a) * r, -0.45 + math.sin(a) * r, 0.025 + 0.03 * math.floor(t * 3)))
    tube('coil', pts, [0.022] * len(pts), RP, res=3)
    dress(0.95, 21, n_tufts=5, flowers=1, pebbles=3, exclude=lambda x, y: abs(x) < 0.7 and abs(y) < 0.6)
    return 'sandık'

def hull_mesh(name, L, Wd, Hh, m, strakes=5):
    """Kayık gövdesi: boyuna kesitlerden örülen bindirme tahtaları (her sıra hafif dışa taşar). grain: u boy, v sıra."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    NS = 22
    def sec(s, t):
        """s: -1..1 boy, t: 0 (omurga) .. 1 (küpeşte) → nokta (sağ yarı)."""
        w = Wd / 2 * (1 - abs(s) ** 2.4) ** 0.6
        sheer = Hh * (1 + 0.35 * s ** 2)                    # uçlar yukarı kalkık
        keel = Hh * 0.08 * abs(s) ** 3
        ang = t * math.pi / 2
        y = w * math.sin(ang) ** 0.8
        z = keel + (sheer - keel) * (1 - math.cos(ang)) ** 0.9
        return V((s * L / 2, y, z))
    for side in (1, -1):
        for k in range(strakes):
            t0, t1 = k / strakes, (k + 1) / strakes + 0.04
            rows = []
            for i in range(NS + 1):
                s = -1 + 2 * i / NS
                a = sec(s, t0); b = sec(s, min(1.0, t1))
                lap = 0.012 * (k + 1)
                a.y = side * (a.y + lap); b.y = side * (b.y + lap * 0.6)
                rows.append((bm.verts.new(a), bm.verts.new(b)))
            for i in range(NS):
                (a0, b0), (a1, b1) = rows[i], rows[i + 1]
                vs = (a0, a1, b1, b0) if side > 0 else (a0, b0, b1, a1)
                f = bm.faces.new(vs)
                uvs = {a0: (i / NS * L, k * 0.31), a1: ((i + 1) / NS * L, k * 0.31), b1: ((i + 1) / NS * L, k * 0.31 + 0.1), b0: (i / NS * L, k * 0.31 + 0.1)}
                for lp in f.loops: lp[uvl].uv = uvs[lp.vert]
    o = link_mesh(name, bm, [m]); smooth(o)
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = 0.03; s.offset = -1
    return o, sec

def c_boat():
    """Kayık: bindirme tahtalı gövde (dışı aşınmış turkuaz boya + krem şerit, içi doğal ahşap), oturak tahtaları,
    iki kürek (biri içeride, biri kuma dayalı), pruvada kangal halat ve küçük fener; kumda deniz kabukları."""
    L, Wd, Hh = 2.0, 0.85, 0.42
    OUT = m_wood('#b98a5a', 'hullout', paint='#2f9fa8')
    hull, sec = hull_mesh('hull', L, Wd, Hh, OUT)
    hull.location.z = 0.06
    INW = m_wood('#c08d5b', 'hullin')
    # iç kaplama: biraz içeride ikinci yüzey
    inner, _ = hull_mesh('inner', L * 0.97, Wd * 0.9, Hh * 0.95, INW, strakes=4)
    inner.location.z = 0.075
    for m in inner.modifiers: m.thickness = 0.01
    # küpeşte (krem boyalı) — iki yanda eğri tüp
    TR = m_wood('#c9a77a', 'gunwale', paint='#f4e6c6')
    for side in (1, -1):
        pts = []
        for i in range(9):
            s = -0.97 + 1.94 * i / 8; p = sec(s, 1.0); pts.append((p.x, side * (p.y + 0.05), p.z + 0.075))
        tube('gunwale', pts, [0.03] * len(pts), TR, res=4)
    # oturaklar + omurga içi döşeme
    for x in (-0.45, 0.35):
        w = sec(x / (L / 2), 0.85).y * 2 + 0.06
        plank('seat', (x, 0, Hh * 0.72), (0.24, w, 0.04), INW, seed=int(x * 10))
    for k in range(3):
        plank('floor', (0, -0.14 + k * 0.14, 0.1), (L * 0.7, 0.12, 0.025), m_wood('#a8693d', 'floorb'), seed=k + 40)
    # kürekler
    OAR = m_wood('#c48a57', 'oar')
    tube('oar', [(-0.7, 0.18, 0.4), (0.0, 0.08, 0.38), (0.5, -0.05, 0.36)], [0.022, 0.022, 0.02], OAR, res=3)
    blob('blade', (0.68, -0.09, 0.36), (0.22, 0.07, 0.015), m_wood('#c48a57', 'oarb', paint='#e86f50'), rot=(0, 0, -8), sub=1, seg=12)
    tube('oar2', [(0.6, 0.62, 0.0), (0.2, 0.55, 0.32), (-0.2, 0.48, 0.62)], [0.022, 0.022, 0.02], OAR, res=3)
    blob('blade2', (0.75, 0.66, 0.02), (0.2, 0.065, 0.015), m_wood('#c48a57', 'oarb', paint='#e86f50'), rot=(0, -35, 10), sub=1, seg=12)
    # pruva halkası + halat
    RP = m_rope()
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.012, location=(L / 2 + 0.02, 0, Hh * 1.3), rotation=(math.radians(90), 0, 0), major_segments=14, minor_segments=5)
    bpy.context.object.data.materials.append(m_metal())
    tube('line', [(L / 2 + 0.05, 0, Hh * 1.25), (L / 2 + 0.25, 0.05, 0.25), (L / 2 + 0.4, 0.2, 0.03), (L / 2 + 0.55, 0.45, 0.03)], [0.016] * 4, RP, res=4)
    # kumda kabuklar ve deniz yıldızı
    SH = [m_flat('#f7d9c4', 0.1, 10, 'shell1'), m_flat('#ffb6a0', 0.1, 10, 'shell2')]
    for k, (x, y) in enumerate(((-0.95, 0.55), (0.3, -0.6), (-0.4, -0.62))):
        for j in range(5):
            b = math.radians(-50 + j * 25)
            blob('shell', (x + math.sin(b) * 0.04, y + math.cos(b) * 0.04, 0.012), (0.018, 0.05, 0.012), SH[k % 2], rot=(0, 0, -math.degrees(b)), sub=0, seg=8)
    ST = m_flat('#ff8a5c', 0.15, 12, 'starfish')
    for j in range(5):
        b = j * 2 * math.pi / 5
        blob('arm', (0.95 + math.cos(b) * 0.06, -0.45 + math.sin(b) * 0.06, 0.015), (0.075, 0.028, 0.015), ST, rot=(0, 0, math.degrees(b)), sub=0, seg=8)
    G1 = m_leaf('#5f9a3d', '#86b85a', '#c7dd8a', '#dbe9a8', 'dunegrass')
    mesh_from_blades('tuft', tufts((-0.9, -0.5, 0.0), 0.12, 1, 5, h=(0.2, 0.34)), [G1])
    mesh_from_blades('tuft', tufts((1.0, 0.55, 0.0), 0.12, 1, 6, h=(0.2, 0.34)), [G1])
    return 'kayık'

# ------------------------------------------------------------------ yapılar

def c_shop():
    """Pazar tezgâhı (dükkân): dört direk, önünde ürün rafları olan tezgâh, şeritli ve fistolu tente (hafif sarkık),
    tezgâhta kavanozlar/meyve sepetleri, asılı fenerler, tepede boyalı tabela (simge: torba); yanda sandık ve saksı."""
    W = m_wood('#9c6a40', 'shopw'); W2 = m_wood('#b98552', 'shopw2'); TOPW = m_wood('#c99a66', 'shoptop')
    PAINT = m_wood('#b98a5a', 'shoppaint', paint='#2fa3a0')
    Wd, Dp = 2.2, 1.1
    for sx in (-1, 1):
        for sy in (-1, 1):
            post('post', (sx * Wd / 2, sy * Dp / 2, -0.03), (sx * Wd / 2, sy * Dp / 2, 2.0 if sy > 0 else 1.75), 0.06, W, seed=sx * 3 + sy)
    # tezgâh gövdesi: dikey boyalı tahtalar
    n = 11
    for i in range(n):
        x = -Wd / 2 + 0.1 + i * (Wd - 0.2) / (n - 1)
        plank('front', (x, -Dp / 2 + 0.04, 0.45), (0.18, 0.04, 0.88), PAINT, seed=i, amt=0.006)
    for sx in (-1, 1):
        plank('side', (sx * (Wd / 2 - 0.03), 0, 0.45), (0.04, Dp - 0.1, 0.88), PAINT, seed=sx + 30)
    plank('top', (0, -0.02, 0.92), (Wd + 0.16, Dp * 0.75, 0.06), TOPW, seed=7)
    plank('trim', (0, -Dp / 2 + 0.01, 0.12), (Wd, 0.06, 0.08), W2, seed=8)
    # arka raf
    for z in (1.15, 1.45):
        plank('shelf', (0, Dp / 2 - 0.1, z), (Wd - 0.1, 0.22, 0.04), W2, seed=int(z * 10))
    # tente: kumaş yüzey (eğik, ön kenarda fisto), şeritler grain u boyunca
    CL = m_cloth('#f05d5e', '#fff4e2', stripes=7.0, name='awning')
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); ds = bm.faces.layers.int.new('ds')
    NX, NY = 28, 6
    grid = []
    for j in range(NY + 1):
        t = j / NY
        row = []
        for i in range(NX + 1):
            s = i / NX
            x = -Wd / 2 - 0.15 + s * (Wd + 0.3)
            y = Dp / 2 + 0.05 - t * (Dp + 0.45)
            z = 2.06 - t * 0.42 - 0.05 * math.sin(math.pi * t) - 0.04 * (math.sin(s * math.pi * 3) ** 2) * t
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(NY):
        for i in range(NX):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])); f[ds] = 1
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / NX, jj / NY)
    # fisto: ön kenarda sarkan yarım daireler (şerit rengiyle)
    scal = []
    nsc = 7
    for k in range(nsc):
        s0, s1 = k / nsc, (k + 1) / nsc
        pts = []
        for q in range(7):
            s = s0 + (s1 - s0) * q / 6
            x = -Wd / 2 - 0.15 + s * (Wd + 0.3)
            pts.append((x, s))
        top = []; bot = []
        for (x, s) in pts:
            y = Dp / 2 + 0.05 - (Dp + 0.45); z = 2.06 - 0.42
            d = math.sin(math.pi * (s - s0) / (s1 - s0))
            top.append((bm.verts.new((x, y, z)), s)); bot.append((bm.verts.new((x, y - 0.01, z - 0.04 - 0.13 * d ** 0.7)), s))
        for q in range(6):
            f = bm.faces.new((top[q][0], top[q + 1][0], bot[q + 1][0], bot[q][0])); f[ds] = 1
            for lp, uu in zip(f.loops, (top[q][1], top[q + 1][1], bot[q + 1][1], bot[q][1])): lp[uvl].uv = (uu, 1.0)
    awn = link_mesh('awning', bm, [CL]); smooth(awn)
    # tezgâhta ürünler
    R = random.Random(5)
    JAR = [m_flat('#ffb347', 0.15, 10, 'jar1'), m_flat('#ff7aa8', 0.15, 10, 'jar2'), m_flat('#8fd06a', 0.15, 10, 'jar3')]
    LID = m_flat('#e0684a', 0.15, 10, 'lid')
    for k, x in enumerate((-0.85, -0.65, 0.55, 0.75, 0.95)):
        blob('jar', (x, -0.1, 1.06), (0.09, 0.09, 0.13), JAR[k % 3], sub=1, seg=12)
        cyl('lid', (x, -0.1, 1.19), 0.075, 0.04, LID, verts=12)
    BS = m_wood('#c8955d', 'basket')
    for (x, fruit) in ((-0.2, '#f39a2e'), (0.18, '#e8463c')):
        lathe('basket', [(0.001, 0.95), (0.16, 0.95), (0.2, 1.08), (0.21, 1.1)], BS, segs=16).location.x = x
        FR = m_flat(fruit, 0.2, 12, 'fr' + fruit)
        for j in range(6):
            a = j * 1.05; blob('fruit', (x + math.cos(a) * 0.09, math.sin(a) * 0.09, 1.12 + 0.03 * (j % 2)), (0.065, 0.065, 0.06), FR, sub=0, seg=12)
    # raf üstü: şişeler ve küçük kutular
    for k in range(7):
        x = -0.9 + k * 0.3; z = 1.18 if k % 2 else 1.48
        blob('bottle', (x, Dp / 2 - 0.1, z + 0.08), (0.05, 0.05, 0.08), JAR[(k + 1) % 3], sub=1, seg=12)
    # asılı fenerler (tente altında)
    GL = m_glow(); I = m_metal()
    for x in (-0.75, 0.75):
        rope_sag((x, -0.25, 1.86), (x, -0.25, 1.68), 0.0, m_rope(), thick=0.008, n=2)
        blob('lamp', (x, -0.25, 1.6), (0.08, 0.08, 0.1), GL, sub=1, seg=12)
        cyl('lcap', (x, -0.25, 1.69), 0.06, 0.03, I, verts=10)
    # tabela: tente üstünde, boyalı tahta + torba simgesi
    SB = m_wood('#b98a5a', 'shopsign', paint='#f4e6c6')
    plank('sign', (0, -0.2, 2.22), (0.9, 0.05, 0.3), SB, rot=(12, 0, 0), seed=11)
    BAG = m_flat('#e86f50', 0.08, 8, 'bagicon')
    rbox('bag', (0, -0.235, 2.2), (0.16, 0.02, 0.14), BAG, rot=(12, 0, 0), bevel=0.02)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.01, location=(0, -0.22, 2.3), rotation=(math.radians(102), 0, 0), major_segments=12, minor_segments=4)
    bpy.context.object.data.materials.append(BAG)
    for sx in (-0.35, 0.35):
        tube('signpost', [(sx, -0.12, 2.0), (sx, -0.16, 2.1)], [0.02, 0.02], W, res=2)
    # tezgâh önünde açık meyve kasaları (yerde, öne eğik)
    for (x, fruit, yaw) in ((-0.55, '#f39a2e', 6), (0.5, '#ffd447', -8)):
        crate((x, -Dp / 2 - 0.32, 0.0), 0.38, W2, W, yaw=yaw, open_top=True, seed=int(x * 10) + 20)
        FR = m_flat(fruit, 0.2, 12, 'frc' + fruit)
        for j in range(7):
            a = j * 2.4; r = 0.03 + 0.1 * math.sqrt(j / 7)
            blob('fruit', (x + math.cos(a) * r, -Dp / 2 - 0.32 + math.sin(a) * r, 0.3 + 0.02 * (j % 2)), (0.07, 0.07, 0.065), FR, sub=0, seg=12)
    # yanda sandık + saksı çiçek
    crate((1.45, -0.2, 0.0), 0.42, W2, W, yaw=-10, seed=4)
    POT = m_plaster('#d9774f', name='pot', dirt=0.1)
    lathe('pot', [(0.001, 0.0), (0.12, 0.0), (0.17, 0.26), (0.19, 0.28)], POT, segs=16).location = (-1.45, -0.35, 0)
    LF = m_leaf('#2f8a3a', '#56b64a', '#a6dc6a', '#cdee92', 'fleaf')
    mesh_from_blades('potplant', rosette([(-1.45, -0.35)], R, sizes=(0.25, 0.35), leaves=9), [LF])
    for o in bpy.context.scene.objects:
        if o.name.startswith('potplant'): o.location.z = 0.24
    flower_heads([(-1.4, -0.3, 0.5), (-1.52, -0.4, 0.46)], R)
    dress(1.5, 6, n_tufts=10, flowers=2, pebbles=4, exclude=lambda x, y: abs(x) < 1.3 and abs(y) < 0.7)
    return 'dükkân'

def c_pier():
    """İskele: sudan yükselen kalın kazıklar (dipte yosun, üstte halat), hafif yamuk güverte tahtaları,
    bir yanda halatlı korkuluk, uçta bağlama babası ve can simidi, sandık + fener."""
    PL = m_wood('#7a5232', 'pile'); DK = [m_wood(c, f'pdeck{i}') for i, c in enumerate(('#c99a66', '#b8875a', '#d3a873'))]
    RP = m_rope(); I = m_metal()
    MOSS = m_plaster('#5a6a4a', stripe=None, name='wetpile', dirt=0.0)
    L, Wd = 3.2, 1.3
    for x in (-L / 2 + 0.15, 0, L / 2 - 0.15):
        for y in (-Wd / 2 - 0.05, Wd / 2 + 0.05):
            top = 0.75 if abs(y) > 0 and x == L / 2 - 0.15 else 0.52
            post('pile', (x, y, -0.6), (x + 0.01, y, top), 0.13, PL, taper=0.92, seed=int(x * 7 + y * 3))
            cyl('wet', (x, y, -0.25), 0.142, 0.4, MOSS, verts=14)           # su çizgisinde yosunlu bant
            rope_wrap((x, y, 0), 0.14, 0.2, 0.3, 1.8, RP, thick=0.016)
    for x in (-L / 2 + 0.15, 0, L / 2 - 0.15):
        plank('beam', (x, 0, 0.36), (0.12, Wd + 0.3, 0.1), PL, seed=int(x * 10) + 50)
    k = 0; x = -L / 2
    while x < L / 2 - 0.05:
        w = 0.17
        plank('deck', (x + w / 2, R_j(k) * 0.03, 0.44), (w - 0.012, Wd + R_j(k + 1) * 0.04, 0.05), DK[k % 3], rot=(0, 0, R_j(k) * 1.2), seed=k + 60)
        x += w; k += 1
    # korkuluk: bir yanda halat iki kazık arasında sarkık
    for (a, b) in ((-L / 2 + 0.15, 0), (0, L / 2 - 0.15)):
        rope_sag((a, Wd / 2 + 0.05, 0.5), (b, Wd / 2 + 0.05, 0.5), 0.12, RP, thick=0.02)
    # uçta bağlama babası
    bb = lathe('bollard', [(0.001, 0.47), (0.1, 0.47), (0.08, 0.6), (0.075, 0.68), (0.11, 0.72), (0.09, 0.76), (0.001, 0.77)], I, segs=16)
    bb.location = (L / 2 - 0.45, -0.3, 0)
    tube('moor', [(L / 2 - 0.45, -0.22, 0.62), (L / 2 - 0.1, -0.5, 0.4), (L / 2 + 0.2, -0.8, 0.0), (L / 2 + 0.5, -1.0, -0.15)], [0.02] * 4, RP, res=4)
    # can simidi (kazığa asılı)
    LB = m_cloth('#ffffff', '#f05d5e', stripes=4.0, name='lifering')
    bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.055, location=(-L / 2 + 0.15, -Wd / 2 - 0.2, 0.42), rotation=(math.radians(90), 0, 0), major_segments=28, minor_segments=10)
    t = bpy.context.object; t.data.materials.append(LB)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.z, co.x) / (2 * math.pi)) % 1.0, 0)
    # güvertede sandık, kova, fener direği
    crate((-0.9, 0.25, 0.47), 0.4, DK[1], PL, yaw=12, seed=6)
    BK = m_wood('#a8693d', 'bucket')
    lathe('bucket', [(0.001, 0.47), (0.11, 0.47), (0.14, 0.7), (0.145, 0.72)], BK, segs=16).location = (-0.45, 0.4, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.13, minor_radius=0.008, location=(-0.45, 0.4, 0.66 - 0.47 + 0.47), major_segments=18, minor_segments=4)
    bpy.context.object.data.materials.append(I)
    GL = m_glow()
    post('lamppost', (L / 2 - 0.15, Wd / 2 + 0.05, 0.75), (L / 2 - 0.15, Wd / 2 + 0.05, 1.45), 0.045, PL, seed=9)
    tube('arm', [(L / 2 - 0.15, Wd / 2 + 0.05, 1.4), (L / 2 - 0.15, Wd / 2 - 0.15, 1.45), (L / 2 - 0.15, Wd / 2 - 0.25, 1.38)], [0.014] * 3, I, res=4)
    blob('lamp', (L / 2 - 0.15, Wd / 2 - 0.25, 1.26), (0.07, 0.07, 0.09), GL, sub=1, seg=12)
    cyl('lcap', (L / 2 - 0.15, Wd / 2 - 0.25, 1.35), 0.06, 0.03, I, verts=10)
    # kazık diplerinde yosun ve deniz yıldızı
    ST = m_flat('#ff8a5c', 0.15, 12, 'starfish')
    for j in range(5):
        b = j * 2 * math.pi / 5
        blob('arm', (0.0 + math.cos(b) * 0.05, -Wd / 2 - 0.16 + math.sin(b) * 0.05 * 0.3, 0.1 + math.sin(b) * 0.05), (0.06, 0.012, 0.022), ST, rot=(90, math.degrees(b), 0), sub=0, seg=8)
    return 'iskele'

def R_j(k): return ((k * 7919) % 13) / 6.5 - 1.0

def c_lighthouse():
    """Deniz feneri: kaba taş temel (yosunlu), hafif konik ve ele yapılmış hissi veren sıvalı kule (kırmızı-krem bantlar,
    dipte kir), iki küçük pencere ve ahşap kapı, balkon (demir korkuluk), camlı fener odası (sıcak ışık), kırmızı kubbe +
    rüzgâr gülü; dipte kayalar, ot, çiçek."""
    H = 3.6
    STN = m_rock()
    prof_base = [(0.001, 0.0), (0.9, 0.0), (0.92, 0.18), (0.88, 0.42), (0.76, 0.5), (0.001, 0.5)]
    base = lathe('base', prof_base, STN, segs=20, noise_amt=0.06)
    # temel taşları (kabarık)
    R = random.Random(2)
    for row, z in enumerate((0.1, 0.3)):
        for k in range(12):
            a = k * 2 * math.pi / 12 + row * 0.26
            r = 0.9 if row == 0 else 0.84
            o = pebble((math.cos(a) * r, math.sin(a) * r, z), 0.16, STN, k + row * 20)
            o.scale = (1.0, 0.8, 0.85); o.rotation_euler = (0, 0, a)
    TOW = m_plaster('#f6ecd8', stripe='#e0544a', period=0.9, z0=0.5, name='tower', dirt=0.4)
    prof = []
    for i in range(13):
        t = i / 12; z = 0.5 + t * (H - 0.5)
        prof.append((0.7 - 0.24 * t + 0.015 * math.sin(t * 9), z))
    tw = lathe('tower', [(0.001, 0.5)] + prof + [(0.001, H)], TOW, segs=28, noise_amt=0.012, seed=3)
    # kapı: kemerli ahşap
    DR = m_wood('#b98a5a', 'lhdoor', paint='#2f8a8a')
    for k in range(3):
        plank('door', (-0.12 + k * 0.12, -0.67, 0.85), (0.11, 0.06, 0.62), DR, seed=k)
    blob('arch', (0, -0.67, 1.15), (0.19, 0.05, 0.1), DR, sub=1, seg=12)
    blob('knob', (0.1, -0.715, 0.86), (0.025, 0.02, 0.025), m_flat('#f2c14e', 0.1, 6, 'gold'), sub=0, seg=8)
    TRIM = m_wood('#c9a77a', 'lhtrim', paint='#f4e6c6')
    WIN = m_flat('#2f4a6a', 0.15, 6, 'darkglass')
    for (z, a) in ((1.85, 200), (2.75, 30)):
        t = (z - 0.5) / (H - 0.5); r = 0.7 - 0.24 * t
        aa = math.radians(a)
        p = V((math.cos(aa) * r, math.sin(aa) * r, z))
        blob('win', tuple(p), (0.07, 0.07, 0.11), WIN, rot=(0, 0, a), sub=1, seg=12)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.1, minor_radius=0.022, location=p, rotation=(0, math.radians(90), aa), major_segments=16, minor_segments=5)
        tr = bpy.context.object; tr.scale = (1.0, 1.0, 1.0); tr.data.materials.append(TRIM)
    # balkon
    I = m_metal('#3e3b46', name='lhiron')
    DK = m_wood('#9c6a40', 'lhdeck')
    cyl('balcony', (0, 0, H + 0.04), 0.6, 0.08, DK, verts=28)
    for k in range(16):
        a = k * 2 * math.pi / 16
        cyl('rail', (math.cos(a) * 0.56, math.sin(a) * 0.56, H + 0.22), 0.012, 0.3, I, verts=6)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.56, minor_radius=0.018, location=(0, 0, H + 0.37), major_segments=32, minor_segments=5)
    bpy.context.object.data.materials.append(I)
    # fener odası: cam + çerçeve
    GL = m_glow('#ffe08a', 'lhglow')
    cyl('lantern', (0, 0, H + 0.42), 0.32, 0.6, GL, verts=8)
    for k in range(8):
        a = (k + 0.5) * 2 * math.pi / 8
        rbox('mull', (math.cos(a) * 0.31, math.sin(a) * 0.31, H + 0.42), (0.04, 0.04, 0.62), I, rot=(0, 0, math.degrees(a)), bevel=0.008)
    ROOF = m_plaster('#e0544a', name='lhroof', dirt=0.0)
    lathe('dome', [(0.001, H + 0.72), (0.42, H + 0.72), (0.4, H + 0.78), (0.3, H + 0.92), (0.15, H + 1.02), (0.001, H + 1.06)], ROOF, segs=24)
    blob('ball', (0, 0, H + 1.1), (0.06, 0.06, 0.06), I, sub=1, seg=12)
    tube('vane', [(0, 0, H + 1.1), (0, 0, H + 1.35)], [0.012, 0.01], I, res=2)
    blob('fish', (0.08, 0, H + 1.3), (0.12, 0.012, 0.045), I, sub=1, seg=12)
    # dip: kayalar, ot, çiçek
    for k, (x, y, r) in enumerate(((1.05, 0.3, 0.26), (-0.95, 0.6, 0.22), (0.7, -0.9, 0.18), (-1.0, -0.55, 0.2))):
        o = pebble((x, y, r * 0.45), r, STN, k + 50); o.scale = (1.0, 1.0, 1.4)
    dress(1.3, 15, n_tufts=12, flowers=4, pebbles=2, bushes=[(1.0, -0.45), (-0.95, 0.1), (0.35, 1.0), (-0.6, -0.85)], stone=STN, at=[(0.95, 0.0), (-0.7, 0.75), (0.5, -0.95)], exclude=lambda x, y: math.hypot(x, y) < 1.0 or (abs(x) < 0.3 and y < 0))
    return 'deniz feneri'

def c_board():
    """Görev panosu: iki kütük ayak, çerçeveli mantar pano (renkli kâğıtlar raptiyeyle, biri yıldız damgalı),
    küçük kiremit çatı (üstünde yıldız süsü), altta minik raf (kalem kutusu); dipte çiçekler."""
    W = m_wood('#8a5a36', 'boardw'); FR = m_wood('#b07b4a', 'boardfr')
    for sx in (-1, 1):
        post('leg', (sx * 0.62, 0, -0.05), (sx * 0.6, 0, 2.05), 0.08, W, seed=sx + 5)
    CORK = m_flat('#c99561', 0.35, 40, 'cork')
    rbox('cork', (0, 0, 1.15), (1.1, 0.06, 0.8), CORK, bevel=0.02)
    for (x, z, sx, sz) in ((0, 1.57, 1.28, 0.08), (0, 0.73, 1.28, 0.08), (-0.6, 1.15, 0.08, 0.92), (0.6, 1.15, 0.08, 0.92)):
        plank('frame', (x, -0.02, z), (sx, 0.09, sz), FR, seed=int(x * 10 + z * 10))
    PAP = ['#fff6e2', '#bfe6ff', '#ffd6e6', '#fff1a6', '#d4f5c2']
    R = random.Random(4)
    PIN = [m_flat('#e8463c', 0.1, 6, 'pinr'), m_flat('#2f8adf', 0.1, 6, 'pinb')]
    for k, (x, z) in enumerate(((-0.33, 1.32), (0.05, 1.36), (0.36, 1.28), (-0.25, 0.95), (0.18, 0.96))):
        rot = R.uniform(-8, 8)
        p = rbox('paper', (x, -0.04, z), (0.24, 0.008, 0.28), m_flat(PAP[k], 0.06, 30, f'paper{k}'), rot=(0, rot, 0), bevel=0.004)
        LN = m_flat('#9a8f86', 0.05, 6, 'lines')
        for j in range(3):
            rbox('line', (x, -0.046, z + 0.06 - j * 0.06), (0.16 - 0.03 * (j == 2), 0.004, 0.012), LN, rot=(0, rot, 0), bevel=0)
        blob('pin', (x, -0.06, z + 0.11), (0.02, 0.02, 0.02), PIN[k % 2], sub=0, seg=8)
    STAR = m_flat('#ffc93a', 0.1, 8, 'star')
    def star(c, r, depth, yaw=0, pitch=90):
        bm = bmesh.new(); pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5; rr = r if k % 2 == 0 else r * 0.45
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
        top = [bm.verts.new((x, y, depth / 2)) for x, y in pts]; bot = [bm.verts.new((x, y, -depth / 2)) for x, y in pts]
        bm.faces.new(top); bm.faces.new(list(reversed(bot)))
        for i in range(10):
            j = (i + 1) % 10; bm.faces.new((bot[i], bot[j], top[j], top[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        o = link_mesh('star', bm, [STAR]); o.location = c; o.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = depth * 0.35; bv.segments = 2
        return o
    star((0.36, -0.05, 1.18), 0.05, 0.015)
    # çatı
    RF = [m_tile(c, f'brf{i}') for i, c in enumerate(('#e0684a', '#d45b3f'))]
    ang = math.radians(34); RZ = 2.17
    for side in (-1, 1):
        plank('roofbase', (0, side * 0.24 * math.cos(ang), RZ - 0.24 * math.sin(ang) - 0.03), (1.6, 0.5, 0.03), W, rot=(-side * 34, 0, 0), seed=side + 90)
        for r in range(4):
            d = 0.06 + r * 0.125
            for xi in range(6):
                x = -0.72 + xi * 0.29 + (0.145 if r % 2 else 0)
                if x > 0.75: continue
                plank('shingle', (x, side * d * math.cos(ang), RZ - d * math.sin(ang) + 0.01), (0.28, 0.16, 0.03), RF[(xi + r) % 2],
                      rot=(-side * (34 + 4), 0, 0), seed=xi + r * 7 + side * 3, amt=0.005)
    cyl('ridge', (0, 0, RZ + 0.04), 0.055, 1.62, RF[1], rot=(0, 90, 0), verts=12)
    star((0, 0, 2.3), 0.13, 0.05, pitch=90)
    # raf + kalem kutusu
    plank('ledge', (0, -0.08, 0.68), (0.9, 0.16, 0.035), FR, seed=77)
    CUP = m_wood('#b98a5a', 'cup', paint='#2fa3a0')
    lathe('cup', [(0.001, 0.7), (0.06, 0.7), (0.065, 0.82)], CUP, segs=12).location = (0.3, -0.08, 0)
    for k, c in enumerate(('#e8463c', '#ffc93a', '#2f8adf')):
        tube('pencil', [(0.29 + k * 0.02, -0.08, 0.74), (0.27 + k * 0.03, -0.09, 0.93)], [0.01, 0.01], m_flat(c, 0.05, 6, 'pc' + c), res=2)
    dress(0.95, 33, n_tufts=9, flowers=5, pebbles=3, bushes=[(-0.75, -0.3), (0.75, -0.25)], exclude=lambda x, y: abs(x) < 0.55 and abs(y) < 0.2)
    return 'görev panosu'

BUILDERS = {
    'c_fence': (c_fence, 512, None), 'c_lantern': (c_lantern, 512, None), 'c_sign': (c_sign, 512, None),
    'c_crates': (c_crates, 1024, None), 'c_boat': (c_boat, 1024, None),
    'c_shop': (c_shop, 1024, None), 'c_pier': (c_pier, 1024, None), 'c_lighthouse': (c_lighthouse, 1024, None), 'c_board': (c_board, 1024, None),
}
AO = float(os.environ.get('POFI_AO', '0.6'))

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
        tris = export_baked_fbx(f'{OUT}/{name}', objs, size=size, decimate=dec, ao_strength=AO)
        print(name, 'üçgen', tris, flush=True)
