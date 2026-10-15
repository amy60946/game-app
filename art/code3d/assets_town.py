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

def m_rope(hexc='#cfae78', name='rope', age=1.0):
    """Halat: boy boyunca eğik burgu çizgileri + lif gürültüsü; parça parça ton farkı (her sarım aynı renk olmasın),
    kir/nem lekeleri, güneşte solmuş açık bölgeler, dipte toprak kiri."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        add = n.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 3.0
        l.new(sep.outputs['Y'], add.inputs[0]); l.new(sep.outputs['X'], add.inputs[2])
        mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 60.0; l.new(add.outputs[0], mul.inputs[0])
        s = n.new('ShaderNodeMath'); s.operation = 'SINE'; l.new(mul.outputs[0], s.inputs[0])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; l.new(s.outputs[0], mr.inputs['Value'])
        rp = ramp(nt, [(0.0, _shade(hexc, 0.62)), (0.6, hexc), (1.0, _shade(hexc, 1.15))]); l.new(mr.outputs[0], rp.inputs['Fac'])
        o = G.obj()
        col = G.mix(G.rng(G.noise(o, 2.0, 3), 0.3, 0.7), rp.outputs[0], rp.outputs[0])
        # parça parça ton: koyu-sıcak ↔ açık-soluk
        tone = G.noise(o, 1.6, 2)
        col = G.mix(G.rng(tone, 0.35, 0.5, 0, 0.55), col, _shade('#8a6a44', 1.0), 'MULTIPLY')
        col = G.mix(G.rng(tone, 0.58, 0.72, 0, 0.5), col, '#efe2c2')
        # lif tüyleri: çok ince açık benekler
        col = G.mix(G.rng(G.noise(G.mapping(uv.outputs[0], (60, 20, 1)), 1.0), 0.62, 0.7, 0, 0.35), col, '#f6ead0')
        col = A.weather(G, col, age, (0.0, 0.25))
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_metal(hexc='#47434d', rust='#a8643a', name='iron', age=1.0):
    """Dövme demir: koyu, hafif dalgalı; turuncu pas lekeleri, pastan aşağı akan izler (dikey uzatılmış gürültü),
    kenarlarda parlayan aşınmış metal, oyuk yerlerde koyu kir."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        o = G.obj()
        rp = ramp(nt, [(0.35, _shade(hexc, 0.8)), (0.65, _shade(hexc, 1.25))]); l.new(G.noise(o, 9, 5), rp.inputs['Fac'])
        col = rp.outputs[0]
        spot = G.rng(G.noise(o, 4, 6), 0.6, 0.7)
        streak = G.rng(G.noise(G.mapping(o, (16, 16, 1.4)), 1.0, 3), 0.58, 0.72, 0, 0.75 * age)
        col = G.mix(G.math('MAXIMUM', spot, streak), col, rust)
        col = G.mix(G.rng(G.noise(o, 22, 3), 0.55, 0.7, 0, 0.5), col, _shade(rust, 0.65))      # pas içinde koyu benek
        col = G.mix(G.math('MULTIPLY', G.edges(0.6, 0.72), 0.3), col, '#8d8a93')
        l.new(col, bsdf.inputs['Base Color'])
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

def m_cloth(c1, c2, stripes=6.0, name=None, age=1.0):
    """Tente kumaşı: şeritler (yumuşak kenar), dokuma, güneşte solma (üstten ve lekeli), su lekesi halkaları,
    kenara doğru kir, ince yırtık/aşınma izleri."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = stripes; l.new(sep.outputs['X'], mul.inputs[0])
        fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(mul.outputs[0], fr.inputs[0])
        mk = ramp(nt, [(0.0, '#000000'), (0.03, '#ffffff'), (0.5, '#ffffff'), (0.53, '#000000')]); l.new(fr.outputs[0], mk.inputs['Fac'])
        bw = n.new('ShaderNodeRGBToBW'); l.new(mk.outputs[0], bw.inputs[0])
        o = G.obj()
        # her şeritte ton geçişi (koyudan açığa)
        c1v = G.mix(G.rng(G.noise(o, 1.5, 3), 0.3, 0.75), _shade(c1, 0.86), _shade(c1, 1.12))
        c2v = G.mix(G.rng(G.noise(o, 1.5, 3), 0.3, 0.75), _shade(c2, 0.92), _shade(c2, 1.04))
        col = G.mix(bw.outputs[0], c2v, c1v)
        col = G.mix(0.16, col, G.noise(G.mapping(uv.outputs[0], (90, 90, 1)), 1.0, 2, out='Color'), 'OVERLAY')
        # solma: geniş açık lekeler
        col = G.mix(G.rng(G.noise(o, 1.1, 4), 0.5, 0.78, 0, 0.42 * age), col, '#fff4dc')
        # su lekesi halkaları (voronoi kenarı, seyrek)
        ring = G.math('MULTIPLY', G.rng(G.vor(o, 2.2, 'DISTANCE_TO_EDGE'), 0.03, 0.0, 0, 1), G.rng(G.noise(o, 3), 0.55, 0.62))
        col = G.mix(G.math('MULTIPLY', ring, 0.35 * age), col, '#8a6f50', 'MULTIPLY')
        # kir lekeleri
        col = G.mix(G.rng(G.noise(o, 6, 8, 0.65), 0.62, 0.78, 0, 0.35 * age), col, '#7d6a52', 'MULTIPLY')
        # kenar aşınması (fisto ucu, katlar)
        col = G.mix(G.math('MULTIPLY', G.edges(0.5, 0.58), 0.5 * age), col, '#f4ead6')
        l.new(col, bsdf.inputs['Base Color'])
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

def plank(name, loc, size, m, rot=(0, 0, 0), bevel=0.012, seed=None, amt=0.01, wear=True):
    """Tahta: yuvarlatılmış kutu, alt bölümlü (ezik/yamukluk için yeterli köşe), elle yapılmış yamukluk, köşe kırıkları."""
    o = rbox(name, loc, size, m, rot=rot, bevel=bevel, seg=2)
    sd = seed if seed is not None else random.random() * 50
    if wear and max(size) > 0.25:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        for md in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=md.name)
        cuts = max(1, int(max(size) / 0.12))
        bm = bmesh.new(); bm.from_mesh(o.data)
        long_edges = [e for e in bm.edges if (e.verts[0].co - e.verts[1].co).length > 0.1]
        if long_edges: bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=min(cuts, 12), use_grid_fill=True)
        bm.to_mesh(o.data); bm.free()
        dent(o, 2, 0.008, int(sd * 13))
    return wobble(o, amt, 3.0, sd)

def post(name, base, top, r, m, verts=10, taper=0.85, seed=0):
    """Hafif eğri, köşeli-yuvarlak kütük direk (uv: boyuna damar)."""
    mid = (V(base) + V(top)) / 2 + V((mnoise.noise(V((seed, 1, 2))) * 0.04, mnoise.noise(V((2, seed, 1))) * 0.04, 0))
    o = tube(name, [base, tuple(mid), top], [r, r * (1 + taper) / 2, r * taper], m, res=4)
    o.data.bevel_resolution = 2 if verts <= 10 else 3
    return o

def rope_wrap(center, r, z0, z1, turns, m, thick=0.016, axis='z', seed=0):
    """Direğe sarılmış halat (sarmal, üç kollu), her sarımın kendi ton farkı halat dokusunda; uçta sarkan kısa kuyruk + lif uçları."""
    pts = []; n = int(turns * 12)
    for i in range(n + 1):
        t = i / n; a = t * turns * 2 * math.pi + seed
        p = V((math.cos(a) * r, math.sin(a) * r, z0 + (z1 - z0) * t))
        if axis == 'x': p = V((z0 + (z1 - z0) * t, math.cos(a) * r, math.sin(a) * r))
        elif axis == 'y': p = V((math.cos(a) * r, z0 + (z1 - z0) * t, math.sin(a) * r))
        pts.append(tuple(V(center) + p))
    end = V(pts[-1]); a = turns * 2 * math.pi + seed
    tail = [tuple(end), tuple(end + V((math.cos(a) * 0.04, math.sin(a) * 0.04, -0.05))), tuple(end + V((math.cos(a) * 0.05, math.sin(a) * 0.05, -0.13)))]
    o = strand_rope(pts + tail[1:], thick, m)
    return o

def rope_sag(a, b, sag, m, thick=0.02, n=8):
    pts = []
    for i in range(n + 1):
        t = i / n; p = V(a).lerp(V(b), t); p.z -= sag * 4 * t * (1 - t); pts.append(tuple(p))
    return strand_rope(pts, thick, m)

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
        lush((x, y, 0.0), 0.08, 1, seed * 31 + k, h=(0.16, 0.3))
    for k, (x, y) in enumerate(at):                       # dip öbekleri (direk/duvar dibi): çakıl halkası + sık ot + çiçek
        base_ring(x, y, 0.16, seed * 17 + k, flowers=1)
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
    """Çit: üç kalın, hafif eğri kütük direk (tepede yosun yastığı; çatlak, ezik, dipte kir/yosun), iki yuvarlak kütük çubuk,
    üç kollu halat bağlar (her biri farklı ton, lif uçları, sarkan kuyruk), çiçekli sarmaşık; direk diplerinde çakıl halkası,
    canlı ot ve çiçek."""
    W = m_wood('#9c6a40', 'fencew'); W2 = m_wood('#b07b4a', 'fencew2')
    RPS = [m_rope('#cfae78', 'rope1'), m_rope('#bf9a62', 'rope2'), m_rope('#d9bf8e', 'rope3')]
    xs = (-0.8, 0.0, 0.8)
    for i, x in enumerate(xs):
        top = (x + (0.02 if i == 1 else -0.03), 0.01 * i, 0.95 + 0.07 * (i % 2))
        p = post('post', (x, 0, -0.05), top, 0.105, W, seed=i)
        moss_cap((top[0], top[1], top[2] + 0.01), 0.1, seed=i)
        for j, z in enumerate((0.7, 0.36)):
            rope_wrap((x, 0, 0), 0.118, z - 0.06, z + 0.06, 2.4, RPS[(i + j) % 3], thick=0.017, seed=i * 2 + j)
        base_ring(x, 0.0, 0.2, 10 + i, flowers=1 if i != 1 else 2)
    tube('rail', [(-1.0, 0.1, 0.69), (0.0, 0.12, 0.72), (1.0, 0.1, 0.7)], [0.062, 0.066, 0.06], W2, res=6)
    tube('rail', [(-1.0, 0.1, 0.32), (0.0, 0.13, 0.36), (1.0, 0.1, 0.41)], [0.058, 0.062, 0.056], W, res=6)
    for x in (-1.0, 1.0):
        for z in (0.7, 0.37 + 0.04 * (x > 0)):
            cyl('cut', (x, 0.1, z), 0.058, 0.02, m_wood('#e0b884', 'endgrain'), rot=(0, 90, 0), verts=12)
    # çubuk üstünde çivi + pas izi (direğe tutturma)
    for x in xs:
        for z in (0.7, 0.36):
            nail((x + 0.03, 0.17, z + 0.02), (0, 1, 0))
    V1 = A.m_flat('#3f7f2f', 0.2, 8, 'vine'); LV = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'vineleaf')
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
    flower_heads([(0.14, -0.05, 0.55), (-0.08, -0.1, 0.78)], R)
    lush((0, 0, 0), 1.0, 7, 4)
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('rosette', rosette([(-0.42, -0.2), (0.45, 0.22)], R, sizes=(0.22, 0.34), leaves=9), [BL])
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
    """Sokak feneri: kalın kütük direk (çatlak, dipte kir/yosun), kıvrık demir kol ve fener kafesi (pas lekeleri, aşağı akan
    pas izleri, kenarda parlayan aşınmış metal), sıcak ışıklı cam, halat bağ, sarmaşık; dipte çakıl halkası + ot + çiçek."""
    W = m_wood('#7e5232', 'lampw'); I = m_metal(age=1.2); GL = m_glow()
    post('post', (0, 0, -0.05), (0.03, 0.02, 1.6), 0.115, W, taper=0.8, seed=2)
    moss_cap((0.03, 0.02, 1.62), 0.1, seed=3)
    tube('arm', [(0.05, 0.02, 1.48), (0.3, 0.02, 1.6), (0.5, 0.02, 1.55), (0.56, 0.02, 1.44)], [0.028, 0.026, 0.024, 0.022], I, res=6)
    tube('brace', [(0.08, 0.02, 1.22), (0.25, 0.02, 1.33), (0.38, 0.02, 1.56)], [0.016, 0.016, 0.016], I, res=4)
    blob('curl', (0.12, 0.02, 1.56), (0.04, 0.012, 0.04), I, sub=1, seg=12)
    # kolun direğe bağlandığı demir kelepçe + cıvatalar
    bpy.ops.mesh.primitive_torus_add(major_radius=0.118, minor_radius=0.016, location=(0.03, 0.02, 1.47), major_segments=24, minor_segments=6)
    bpy.context.object.data.materials.append(I)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.016, location=(0.025, 0.02, 1.22), major_segments=24, minor_segments=6)
    bpy.context.object.data.materials.append(I)
    rope_wrap((0.0, 0.0, 0), 0.122, 0.95, 1.05, 2.0, m_rope('#c4a06a', 'lrope'), thick=0.016, seed=1)
    cx, cz = 0.56, 1.17
    rbox('glass', (cx, 0.02, cz), (0.22, 0.22, 0.3), GL, bevel=0.03)
    for sx in (-1, 1):
        for sy in (-1, 1):
            o = rbox('bar', (cx + sx * 0.115, 0.02 + sy * 0.115, cz), (0.032, 0.032, 0.34), I, bevel=0.008)
    for zz in (cz - 0.06, cz + 0.06):                             # cam önünde ince yatay demir
        for sy in (-1, 1): rbox('hbar', (cx, 0.02 + sy * 0.118, zz), (0.24, 0.012, 0.012), I, bevel=0.003)
    rbox('base', (cx, 0.02, cz - 0.18), (0.28, 0.28, 0.05), I, bevel=0.012)
    blob('drop', (cx, 0.02, cz - 0.23), (0.05, 0.05, 0.04), I, sub=1, seg=12)
    roof = lathe('roof', [(0.18, cz + 0.15), (0.185, cz + 0.18), (0.1, cz + 0.27), (0.02, cz + 0.32), (0.001, cz + 0.33)], I, segs=4); roof.location = (cx, 0.02, 0)
    roof.rotation_euler = (0, 0, math.radians(45))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.011, location=(cx, 0.02, cz + 0.37), rotation=(math.radians(90), 0, 0), major_segments=12, minor_segments=5)
    bpy.context.object.data.materials.append(I)
    for (p, nn) in (((0.03, -0.1, 1.47), (0, -1, 0)), ((0.025, -0.1, 1.22), (0, -1, 0))):
        nail(p, nn, I)
    V1 = A.m_flat('#3f7f2f', 0.2, 8, 'vine'); LV = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'vineleaf')
    pts = []; leafs = []
    for i in range(30):
        t = i / 29; a = t * 3.0 * 2 * math.pi
        r = 0.125 - 0.02 * t
        p = (math.cos(a) * r, math.sin(a) * r, 0.04 + t * 0.85); pts.append(p)
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
    flower_heads([(0.1, -0.12, 0.62), (-0.12, 0.05, 0.8)], R)
    STN = m_rock()
    for k in range(6):
        a = k * 1.05 + 0.3
        pebble((math.cos(a) * 0.22, math.sin(a) * 0.22, 0.04), 0.09 + 0.025 * (k % 2), STN, k)
    lush((0, 0, 0), 0.35, 4, 9)
    flower_heads([(0.3, 0.1, 0.22), (-0.25, -0.2, 0.2), (0.05, 0.32, 0.24)], R)
    return 'fener'

def c_sign():
    """Yön tabelası: kalın kütük direk + kiremit şapka, üç doğal biçimli ok tahtası (dalgalı kenar, yumuşak ok, kırık köşe;
    aşınmış boya, çatlak, çizik, kenarda boya dökülmesi), üzerlerinde boyalı simgeler, paslı çiviler (aşağı akan pas izi),
    dipte çakıl halkası + ot + çiçek."""
    W = m_wood('#8a5a36', 'signpost')
    post('post', (0, 0, -0.05), (0.01, 0, 1.55), 0.1, W, taper=0.85, seed=4)
    roof = m_tile('#e0684a', 'signroof')
    for s_ in (-1, 1):
        plank('roof', (0.0, s_ * 0.1, 1.62), (0.36, 0.24, 0.04), roof, rot=(s_ * 32, 0, 0), seed=s_ + 2)
    cyl('ridge', (0, 0, 1.69), 0.035, 0.4, roof, rot=(0, 90, 0), verts=10)
    BOARDS = [('#2fa3a0', 25, 1.28), ('#e86f50', 160, 0.98), ('#f4e6c6', -40, 0.68)]
    ICON = [A.m_flat('#fff6e6', 0.05, 8, 'ic_w'), A.m_flat('#ffd447', 0.08, 8, 'ic_y'), A.m_flat('#e86f50', 0.08, 8, 'ic_c')]
    L, Hb, T = 0.78, 0.24, 0.06
    for i, (col, yaw, z) in enumerate(BOARDS):
        m = m_wood('#b98a5a', f'board{i}', paint=col, age=1.2)
        a = math.radians(yaw)
        o = prism('board', board_shape(L, Hb, i * 7), T, m, loc=(math.cos(a) * 0.1, math.sin(a) * 0.1, z), rot=(0, R_i(i) * 3, yaw), bevel=0.018)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier='bv')
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if (e.verts[0].co - e.verts[1].co).length > 0.05], cuts=2, use_grid_fill=True)
        bm.to_mesh(o.data); bm.free()
        dent(o, 3, 0.01, i)
        wobble(o, 0.006, 6.0, i)
        fw = V((math.cos(a), math.sin(a), 0)); nrm = V((math.sin(a), -math.cos(a), 0))
        c = V((math.cos(a) * 0.1, math.sin(a) * 0.1, z)) + fw * (L * 0.45) + nrm * (T / 2 + 0.006)
        ic = ICON[i]
        if i == 0:
            prism('ic', [(-0.07, -0.07), (0.07, -0.07), (0.07, 0.02), (0.0, 0.08), (-0.07, 0.02)], 0.012, ic, loc=tuple(c), rot=(0, 0, yaw), bevel=0.004)
        elif i == 1:
            pts = []
            for k in range(10):
                b_ = math.pi / 2 + k * math.pi / 5; rr = 0.085 if k % 2 == 0 else 0.038
                pts.append((math.cos(b_) * rr, math.sin(b_) * rr))
            prism('ic', pts, 0.012, ic, loc=tuple(c), rot=(0, 0, yaw), bevel=0.004)
        else:
            pts = [(0, -0.07)] + [(math.sin(math.radians(t)) * 0.085, -0.07 + math.cos(math.radians(t)) * 0.13 * (0.92 + 0.08 * math.cos(math.radians(t * 5)))) for t in range(-60, 61, 12)]
            prism('ic', pts, 0.012, ic, loc=tuple(c), rot=(0, 0, yaw), bevel=0.004)
        for d in (0.02, L - 0.26):
            for dz in (-0.06, 0.06):
                p = V((math.cos(a) * 0.1, math.sin(a) * 0.1, z + dz)) + fw * d + nrm * (T / 2)
                nail(tuple(p), tuple(nrm))
    base_ring(0, 0, 0.2, 5, flowers=2)
    lush((0, 0, 0), 0.6, 5, 12)
    R = random.Random(3)
    flower_heads([(0.35, -0.2, 0.22), (-0.3, 0.25, 0.2), (0.28, 0.3, 0.24)], R)
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('rosette', rosette([(0.32, -0.3), (-0.35, -0.1)], R, sizes=(0.2, 0.3), leaves=8), [BL])
    return 'tabela'

def R_i(i): return (-1, 1, -0.5)[i % 3]

def c_crates():
    """Liman yükü: iki sandık (eskimiş, dipleri kirli/yosunlu, köşe kırıkları, çatlaklar, paslı çiviler), üstteki açık sandıkta
    gerçekçi meyveler (gözenekli portakal, yanaklı elma, lifli hindistan cevizi, benekli muz salkımı; bir-ikisi ezik),
    yanda fıçı (paslı çember), bağlı çuval, üç kollu kangal halat (lifli); altta yıpranmış toprak/kum zemin, canlı ot öbekleri."""
    W = m_wood('#b07b4a', 'cratew', age=1.3); W2 = m_wood('#8f5d36', 'cratew2', age=1.3)
    dirt_patch(0.0, 0.0, 1.0, 0.8, 5, sand=True)
    dirt_patch(-0.15, 0.05, 0.55, 0.5, 9)
    crate((-0.2, 0.05, 0.0), 0.62, W, W2, yaw=8, seed=1)
    crate((-0.15, 0.0, 0.62), 0.5, W, W2, yaw=-14, open_top=True, seed=2)
    a = math.radians(8)
    for (dx, dz) in ((-0.22, 0.3), (0.22, 0.3), (-0.22, 0.12), (0.22, 0.12)):
        nail((-0.2 + dx * math.cos(a) + 0.33 * math.sin(a), 0.05 + dx * math.sin(a) - 0.33 * math.cos(a), dz), (math.sin(a), -math.cos(a), 0))
    R = random.Random(3)
    kinds = ['orange', 'apple', 'orange', 'coconut', 'apple', 'orange', 'apple']
    for k in range(7):
        ang = k * 2.4; r = 0.05 + 0.13 * math.sqrt(k / 7)
        fruit(kinds[k], (-0.15 + math.cos(ang) * r, math.sin(ang) * r, 0.62 + 0.43 + R.uniform(0, 0.03)), 0.075 if kinds[k] != 'coconut' else 0.085, seed=k)
    banana_bunch((-0.05, -0.12, 1.12), 5, seed=2, yaw=30)
    fruit('orange', (0.15, -0.38, 0.07), 0.07, seed=20)                    # düşmüş meyve
    barrel((0.5, -0.12, 0.27), r=0.2, h=0.52, wood=m_wood('#a8693d', 'barrelw', age=1.3), iron=m_metal(age=1.3))
    SK = A.m_flat('#d9c08e', 0.3, 30, 'sack'); RP = m_rope()
    s = blob('sack', (0.42, 0.42, 0.2), (0.22, 0.2, 0.22), SK, sub=2, seg=16); wobble(s, 0.03, 4.0, 2)
    blob('neck', (0.42, 0.42, 0.44), (0.07, 0.07, 0.08), SK, sub=1, seg=12)
    rope_wrap((0.42, 0.42, 0), 0.072, 0.4, 0.44, 1.3, RP, thick=0.014, seed=3)
    pts = []
    for i in range(80):
        t = i / 79; ang = t * 3 * 2 * math.pi; r = 0.18 - 0.025 * (t * 3)
        pts.append((-0.55 + math.cos(ang) * r, -0.45 + math.sin(ang) * r, 0.03 + 0.035 * (t * 3) * 0.6))
    pts += [(-0.4, -0.62, 0.03), (-0.2, -0.75, 0.025), (0.05, -0.7, 0.025)]
    strand_rope(pts, 0.026, RP)
    lush((0, 0, 0), 1.0, 6, 21, h=(0.22, 0.38))
    base_ring(0.85, 0.35, 0.16, 8, flowers=2)
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('rosette', rosette([(-0.75, 0.45), (0.8, -0.45)], R, sizes=(0.25, 0.36), leaves=9), [BL])
    return 'sandık'

def hull_mesh(name, L, Wd, Hh, m, strakes=5):
    """Kayık gövdesi: boyuna kesitlerden örülen bindirme tahtaları (her sıra hafif dışa taşar). grain: u boy, v sıra."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    NS = 30
    def sec(s, t):
        w = Wd / 2 * (1 - abs(s) ** 2.4) ** 0.6
        sheer = Hh * (1 + 0.35 * s ** 2)
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
    """Kayık: bindirme tahtalı gövde (her tahta sırasında aşınmış turkuaz boya, pul pul dökülme, çatlak, çizik, kenarda
    aşınma; tahta sıraları boyunca çivi başları + pas izleri), krem küpeşte, oturaklar, ayrıntılı iki kürek (sap, topuz,
    halat sargı, boyalı-dökülmüş pala), pruva halkası ve üç kollu halat; ıslak kum, kıyı yosunu, deniz otu, kabuk, deniz yıldızı."""
    L, Wd, Hh = 2.0, 0.85, 0.42
    OUT = m_wood('#b98a5a', 'hullout', paint='#2f9fa8', age=1.4, grime=(0.05, 0.3))
    hull, sec = hull_mesh('hull', L, Wd, Hh, OUT)
    hull.location.z = 0.06
    INW = m_wood('#c08d5b', 'hullin', age=1.2)
    inner, _ = hull_mesh('inner', L * 0.97, Wd * 0.9, Hh * 0.95, INW, strakes=4)
    inner.location.z = 0.075
    for m in inner.modifiers: m.thickness = 0.01
    # çiviler: tahta sırası bindirme çizgileri boyunca
    NM = m_metal('#6a646e', name='boatnail', age=1.3)
    for side in (1, -1):
        for k in range(1, 5):
            t = k / 5 + 0.02
            for i in range(9):
                s = -0.8 + 1.6 * i / 8
                p = sec(s, t); lap = 0.012 * (k + 1)
                q = V((p.x, side * (p.y + lap + 0.012), p.z + 0.06))
                nrm = V((0, side, -0.3 + 0.6 * t)).normalized()
                nail(tuple(q), tuple(nrm), NM, streak=(i % 3 == 0))
    TR = m_wood('#c9a77a', 'gunwale', paint='#f4e6c6', age=1.3)
    for side in (1, -1):
        pts = []
        for i in range(9):
            s = -0.97 + 1.94 * i / 8; p = sec(s, 1.0); pts.append((p.x, side * (p.y + 0.05), p.z + 0.075))
        tube('gunwale', pts, [0.03] * len(pts), TR, res=4)
        # ıskarmoz (kürek yuvası)
        p = sec(0.0, 1.0)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.01, location=(0.05, side * (p.y + 0.06), p.z + 0.13), rotation=(math.radians(90), 0, 0), major_segments=12, minor_segments=4)
        bpy.context.object.data.materials.append(NM)
    for x in (-0.45, 0.35):
        w = sec(x / (L / 2), 0.85).y * 2 + 0.06
        plank('seat', (x, 0, Hh * 0.72), (0.24, w, 0.04), INW, seed=int(x * 10))
    for k in range(3):
        plank('floor', (0, -0.14 + k * 0.14, 0.1), (L * 0.7, 0.12, 0.025), m_wood('#a8693d', 'floorb'), seed=k + 40)
    # biraz su birikintisi (dipte)
    blob('puddle', (-0.2, 0.0, 0.118), (0.3, 0.12, 0.004), A.m_flat('#5fa8b0', 0.15, 6, 'puddle'), sub=0, seg=16)
    oar((-0.75, 0.2, 0.42), (0.95, -0.12, 0.34), '#e86f50', seed=1)
    oar((-0.35, 0.62, 0.66), (0.95, 0.7, 0.02), '#e86f50', seed=2)
    RP = m_rope()
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.012, location=(L / 2 + 0.02, 0, Hh * 1.3), rotation=(math.radians(90), 0, 0), major_segments=14, minor_segments=5)
    bpy.context.object.data.materials.append(NM)
    strand_rope([(L / 2 + 0.05, 0, Hh * 1.25), (L / 2 + 0.25, 0.05, 0.25), (L / 2 + 0.4, 0.2, 0.03), (L / 2 + 0.55, 0.45, 0.03), (L / 2 + 0.35, 0.62, 0.03)], 0.02, RP)
    # zemin: ıslak kum + kıyı yosunu + deniz otu
    blob('wetsand', (0.1, 0, 0.0), (1.35, 0.7, 0.008), A.m_flat('#c9a76c', 0.25, 14, 'wetsand'), sub=1, seg=24)
    MS = A.m_flat('#5f8f3a', 0.35, 22, 'shoremoss')
    for k, (x, y, r) in enumerate(((-0.95, 0.42, 0.16), (0.7, -0.45, 0.14), (-0.3, -0.48, 0.1), (1.1, 0.3, 0.12))):
        o = blob('moss', (x, y, 0.01), (r, r * 0.8, 0.025), MS, sub=1, seg=12); wobble(o, r * 0.25, 6.0, k)
    seaweed(-0.8, -0.55, 3, 7); seaweed(1.2, -0.2, 5, 6); seaweed(0.2, 0.6, 7, 5)
    SH = [A.m_flat('#f7d9c4', 0.1, 10, 'shell1'), A.m_flat('#ffb6a0', 0.1, 10, 'shell2')]
    for k, (x, y) in enumerate(((-0.95, 0.55), (0.3, -0.6), (-0.4, -0.62))):
        for j in range(5):
            b = math.radians(-50 + j * 25)
            blob('shell', (x + math.sin(b) * 0.04, y + math.cos(b) * 0.04, 0.012), (0.018, 0.05, 0.012), SH[k % 2], rot=(0, 0, -math.degrees(b)), sub=0, seg=8)
    ST = A.m_flat('#ff8a5c', 0.15, 12, 'starfish')
    for j in range(5):
        b = j * 2 * math.pi / 5
        blob('arm', (0.95 + math.cos(b) * 0.06, -0.45 + math.sin(b) * 0.06, 0.015), (0.075, 0.028, 0.015), ST, rot=(0, 0, math.degrees(b)), sub=0, seg=8)
    G1 = m_leaf('#4f8a35', '#7cb04f', '#c2db84', '#dbe9a8', 'dunegrass')
    for k, (x, y) in enumerate(((-0.95, -0.35), (1.05, 0.55), (-1.15, 0.2))):
        mesh_from_blades('tuft', tufts((x, y, 0.0), 0.14, 2, 5 + k, h=(0.22, 0.38)), [G1])
    return 'kayık'

def c_shop():
    """Pazar tezgâhı: eskimiş direkler ve boyalı tahtalar, şeritli fistolu tente (solmuş, lekeli, kenarı aşınmış, ton geçişli),
    tezgâhta gerçekçi meyve-sebze (portakal, elma, domates, havuç demeti, karpuz, muz salkımı), kavanozlar, asılı fenerler,
    tabela; önde açık meyve kasaları; arkada palmiye ve çalılar; dipte yıpranmış toprak, ot ve çiçek."""
    W = m_wood('#9c6a40', 'shopw', age=1.2); W2 = m_wood('#b98552', 'shopw2', age=1.2); TOPW = m_wood('#c99a66', 'shoptop', age=1.2)
    PAINT = m_wood('#b98a5a', 'shoppaint', paint='#2fa3a0', age=1.3)
    Wd, Dp = 2.2, 1.1
    dirt_patch(0, -0.2, 1.6, 1.0, 11)
    # arka plan: palmiye + çalılar (assets_v3 palmiyesi küçültülüp arkaya)
    before = set(bpy.context.scene.objects)
    A.c_palm()
    for o in set(bpy.context.scene.objects) - before:
        o.scale = (o.scale[0] * 0.72, o.scale[1] * 0.72, o.scale[2] * 0.72)
        o.location = (o.location[0] * 0.72 - 1.25, o.location[1] * 0.72 + 1.0, o.location[2] * 0.72)
        o.rotation_euler[2] += 0.0
    R = random.Random(5)
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('backbush', rosette([(0.6, 1.0), (1.2, 0.85), (-0.2, 1.05), (1.55, 0.3)], R, sizes=(0.35, 0.55), leaves=11), [BL])
    flower_heads([(0.7, 1.15, 0.4), (1.3, 0.95, 0.45), (-0.1, 1.2, 0.38)], R)
    for sx in (-1, 1):
        for sy in (-1, 1):
            post('post', (sx * Wd / 2, sy * Dp / 2, -0.03), (sx * Wd / 2, sy * Dp / 2, 2.0 if sy > 0 else 1.75), 0.06, W, seed=sx * 3 + sy)
    n = 11
    for i in range(n):
        x = -Wd / 2 + 0.1 + i * (Wd - 0.2) / (n - 1)
        plank('front', (x, -Dp / 2 + 0.04, 0.45), (0.18, 0.04, 0.88), PAINT, seed=i, amt=0.006)
        for z in (0.2, 0.75): nail((x, -Dp / 2 + 0.015, z), (0, -1, 0), streak=(i % 2 == 0))
    for sx in (-1, 1):
        plank('side', (sx * (Wd / 2 - 0.03), 0, 0.45), (0.04, Dp - 0.1, 0.88), PAINT, seed=sx + 30)
    plank('top', (0, -0.02, 0.92), (Wd + 0.16, Dp * 0.75, 0.06), TOPW, seed=7)
    plank('trim', (0, -Dp / 2 + 0.01, 0.12), (Wd, 0.06, 0.08), W2, seed=8)
    for z in (1.15, 1.45):
        plank('shelf', (0, Dp / 2 - 0.1, z), (Wd - 0.1, 0.22, 0.04), W2, seed=int(z * 10))
    # tente (kumaş: solma, leke, aşınma)
    CL = m_cloth('#f05d5e', '#fff4e2', stripes=7.0, name='awning', age=1.3)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); ds = bm.faces.layers.int.new('ds')
    NX, NY = 36, 8
    grid = []
    for j in range(NY + 1):
        t = j / NY
        row = []
        for i in range(NX + 1):
            s = i / NX
            x = -Wd / 2 - 0.15 + s * (Wd + 0.3)
            y = Dp / 2 + 0.05 - t * (Dp + 0.45)
            z = 2.06 - t * 0.42 - 0.05 * math.sin(math.pi * t) - 0.04 * (math.sin(s * math.pi * 3) ** 2) * t + 0.008 * mnoise.noise(V((x * 6, y * 6, 0)))
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(NY):
        for i in range(NX):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])); f[ds] = 1
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / NX, jj / NY)
    nsc = 7
    for k in range(nsc):
        s0, s1 = k / nsc, (k + 1) / nsc
        top = []; bot = []
        for q in range(9):
            s = s0 + (s1 - s0) * q / 8
            x = -Wd / 2 - 0.15 + s * (Wd + 0.3)
            y = Dp / 2 + 0.05 - (Dp + 0.45); z = 2.06 - 0.42
            d = math.sin(math.pi * (s - s0) / (s1 - s0))
            fray_ = 0.012 * mnoise.noise(V((x * 40, 0, k)))             # aşınmış, hafif tırtıklı kenar
            top.append((bm.verts.new((x, y, z)), s)); bot.append((bm.verts.new((x, y - 0.01, z - 0.04 - 0.13 * d ** 0.7 + fray_)), s))
        for q in range(8):
            f = bm.faces.new((top[q][0], top[q + 1][0], bot[q + 1][0], bot[q][0])); f[ds] = 1
            for lp, uu in zip(f.loops, (top[q][1], top[q + 1][1], bot[q + 1][1], bot[q][1])): lp[uvl].uv = (uu, 1.0)
    awn = link_mesh('awning', bm, [CL]); smooth(awn)
    # yamalı bir köşe (dikilmiş kare yama)
    rbox('patch', (0.55, -0.3, 1.86), (0.2, 0.18, 0.006), A.m_flat('#e9d7b0', 0.2, 30, 'patchc'), rot=(-22, 0, 8), bevel=0.003)
    # tezgâhta ürünler: sepetler + kasalar + kavanoz
    BS = m_wood('#c8955d', 'basket')
    for (x, kind) in ((-0.62, 'orange'), (-0.18, 'apple'), (0.26, 'tomato')):
        lathe('basket', [(0.001, 0.95), (0.16, 0.95), (0.2, 1.08), (0.21, 1.1)], BS, segs=16).location.x = x
        for j in range(7):
            ang = j * 2.4; r = 0.03 + 0.11 * math.sqrt(j / 7)
            fruit(kind, (x + math.cos(ang) * r, math.sin(ang) * r - 0.02, 1.13 + 0.03 * (j % 2)), 0.06, seed=j + int(x * 10))
    fruit('melon', (0.72, 0.05, 1.07), 0.13, seed=1)
    fruit('melon', (0.92, 0.12, 1.06), 0.12, seed=2)
    banana_bunch((-0.95, 0.05, 1.0), 6, seed=5, yaw=-20)
    for k in range(4):
        fruit('carrot', (0.5 + k * 0.03, -0.18, 0.96), 0.03, seed=k)
    LEAFC = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'carrotleaf')
    def ctops(bm):
        out = []
        for k in range(4):
            base = V((0.5 + k * 0.03 + 0.027, -0.18, 0.96 + 0.078))
            for j in range(4):
                a = j * 1.6 + k; d = V((math.cos(a) * 0.3, math.sin(a) * 0.3, 1)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, base, d, side, 0.16, 0.025, 0.6, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('ctops', ctops, [LEAFC])
    JAR = [A.m_flat('#ffb347', 0.15, 10, 'jar1'), A.m_flat('#ff7aa8', 0.15, 10, 'jar2'), A.m_flat('#8fd06a', 0.15, 10, 'jar3')]
    LID = m_metal('#c9524a', name='lid', age=0.8)
    for k in range(7):
        x = -0.9 + k * 0.3; z = 1.18 if k % 2 else 1.48
        blob('jar', (x, Dp / 2 - 0.1, z + 0.08), (0.06, 0.06, 0.09), JAR[(k + 1) % 3], sub=1, seg=12)
        cyl('lid', (x, Dp / 2 - 0.1, z + 0.17), 0.05, 0.025, LID, verts=12)
    GL = m_glow(); I = m_metal()
    for x in (-0.75, 0.75):
        strand_rope([(x, -0.25, 1.86), (x, -0.25, 1.7)], 0.01, m_rope())
        blob('lamp', (x, -0.25, 1.6), (0.08, 0.08, 0.1), GL, sub=1, seg=12)
        cyl('lcap', (x, -0.25, 1.69), 0.06, 0.03, I, verts=10)
    SB = m_wood('#b98a5a', 'shopsign', paint='#f4e6c6', age=1.3)
    plank('sign', (0, -0.2, 2.22), (0.9, 0.05, 0.3), SB, rot=(12, 0, 0), seed=11)
    BAG = A.m_flat('#e86f50', 0.08, 8, 'bagicon')
    rbox('bag', (0, -0.235, 2.2), (0.16, 0.02, 0.14), BAG, rot=(12, 0, 0), bevel=0.02)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.01, location=(0, -0.22, 2.3), rotation=(math.radians(102), 0, 0), major_segments=12, minor_segments=4)
    bpy.context.object.data.materials.append(BAG)
    for sx in (-0.35, 0.35):
        tube('signpost', [(sx, -0.12, 2.0), (sx, -0.16, 2.1)], [0.02, 0.02], W, res=2)
        nail((sx, -0.24, 2.22), (0, -1, 0))
    for (x, kind, yaw) in ((-0.55, 'orange', 6), (0.5, 'apple', -8)):
        crate((x, -Dp / 2 - 0.32, 0.0), 0.38, W2, W, yaw=yaw, open_top=True, seed=int(x * 10) + 20)
        for j in range(7):
            ang = j * 2.4; r = 0.03 + 0.1 * math.sqrt(j / 7)
            fruit(kind, (x + math.cos(ang) * r, -Dp / 2 - 0.32 + math.sin(ang) * r, 0.31 + 0.02 * (j % 2)), 0.065, seed=j + 30)
    crate((1.45, -0.2, 0.0), 0.42, W2, W, yaw=-10, seed=4)
    POT = m_plaster('#d9774f', name='pot', dirt=0.25)
    lathe('pot', [(0.001, 0.0), (0.12, 0.0), (0.17, 0.26), (0.19, 0.28)], POT, segs=16).location = (-1.45, -0.35, 0)
    LF = m_leaf('#2f8a3a', '#56b64a', '#a6dc6a', '#cdee92', 'fleaf')
    mesh_from_blades('potplant', rosette([(-1.45, -0.35)], R, sizes=(0.25, 0.35), leaves=9), [LF])
    for o in bpy.context.scene.objects:
        if o.name.startswith('potplant'): o.location.z = 0.24
    flower_heads([(-1.4, -0.3, 0.5), (-1.52, -0.4, 0.46)], R)
    for (x, y) in ((-Wd / 2, -Dp / 2), (Wd / 2, -Dp / 2)):
        base_ring(x, y, 0.14, int(x * 10) + 40, flowers=1)
    lush((0, -0.3, 0), 1.6, 8, 6)
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
        for yy in (-Wd / 2 + 0.06, 0.0, Wd / 2 - 0.06):
            if k % 2 == 0 or yy == 0.0: nail((x + w / 2, yy, 0.47), (0, 0, 1), streak=False)
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
    for (x, z) in ((-0.6, 1.55), (0.6, 1.55), (-0.6, 0.75), (0.6, 0.75)):
        nail((x, -0.07, z), (0, -1, 0))
    for sx in (-1, 1): base_ring(sx * 0.62, 0.0, 0.17, 60 + sx, flowers=1)
    CUP = m_wood('#b98a5a', 'cup', paint='#2fa3a0')
    lathe('cup', [(0.001, 0.7), (0.06, 0.7), (0.065, 0.82)], CUP, segs=12).location = (0.3, -0.08, 0)
    for k, c in enumerate(('#e8463c', '#ffc93a', '#2f8adf')):
        tube('pencil', [(0.29 + k * 0.02, -0.08, 0.74), (0.27 + k * 0.03, -0.09, 0.93)], [0.01, 0.01], m_flat(c, 0.05, 6, 'pc' + c), res=2)
    dress(0.95, 33, n_tufts=9, flowers=5, pebbles=3, bushes=[(-0.75, -0.3), (0.75, -0.25)], exclude=lambda x, y: abs(x) < 0.55 and abs(y) < 0.2)
    return 'görev panosu'

# ------------------------------------------------------------------ parti 2

def m_soil(name='soil'):
    """Ekili toprak: koyu kahve, topak gürültüsü, yer yer açık kuru benek."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 8; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.35, '#3d2817'), (0.55, '#5a3c22'), (0.72, '#7a5532')]); l.new(nz.outputs['Fac'], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_sand(name='sand', hexc='#ecd29a'):
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 30; nz.inputs['Detail'].default_value = 4; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.35, _shade(hexc, 0.9)), (0.65, _shade(hexc, 1.08))]); l.new(nz.outputs['Fac'], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_snow(name='snow'):
    """Kar: beyaz, girintilerde (aşağı bakan) mavimsi; çok hafif pırıltı benekleri."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        geo = n.new('ShaderNodeNewGeometry'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Normal'], sep.inputs[0])
        tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        ad = n.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.4; l.new(nz.outputs['Fac'], ad.inputs[0]); l.new(sep.outputs['Z'], ad.inputs[2])
        rp = ramp(nt, [(0.0, '#b9cdea'), (0.6, '#e8f0fb'), (1.0, '#ffffff')]); l.new(ad.outputs[0], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_water(name='pool'):
    """Havuz suyu: ortası derin turkuaz, kenara doğru açık; yumuşak dalga deseni (pişirmede sabit)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); vm = n.new('ShaderNodeVectorMath'); vm.operation = 'LENGTH'; l.new(tc.outputs['Object'], vm.inputs[0])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.0; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        ad = n.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.25; l.new(nz.outputs['Fac'], ad.inputs[0]); l.new(vm.outputs['Value'], ad.inputs[2])
        rp = ramp(nt, [(0.0, '#1f9fc4'), (0.6, '#3cc4d8'), (0.95, '#8fe6e0'), (1.1, '#e8fbf6')]); l.new(ad.outputs[0], rp.inputs['Fac'])
        vo = n.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 5; l.new(tc.outputs['Object'], vo.inputs['Vector'])
        cr = n.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.0; cr.inputs['From Max'].default_value = 0.04; cr.inputs['To Min'].default_value = 0.35; cr.inputs['To Max'].default_value = 0
        l.new(vo.outputs['Distance'], cr.inputs['Value'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb('#e8fbff')
        l.new(cr.outputs[0], mx.inputs['Factor']); l.new(rp.outputs[0], mx.inputs[6])
        l.new(mx.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def rock(loc, r, m, seed, sq=(1.0, 1.0, 0.8), sub=3, amt=0.16):
    """Yuvarlak hatlı, gürültüyle bozulmuş kaya (keskin değil)."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object; o.scale = sq; bpy.ops.object.transform_apply(scale=True)
    for v in o.data.vertices:
        p = v.co
        d = mnoise.noise(p * (1.3 / r) + V((seed * 3, 0, 0))) * amt + mnoise.noise(p * (3.5 / r) + V((0, seed, 0))) * amt * 0.3
        v.co = p + p.normalized() * d * r
    o.data.materials.append(m); smooth(o)
    return o

def pine(loc, h, seed, snow=False):
    """Çam: kahve gövde + 4-5 kat sarkık iğne eteği (her kat yaprak şeritlerinden), karlıysa katların üstünde kar yastığı."""
    R = random.Random(seed)
    x, y, z = loc
    tube('trunk', [(x, y, z - 0.05), (x, y, z + h * 0.5), (x, y, z + h * 0.95)], [0.06 * h, 0.045 * h, 0.02 * h], m_bark(), res=2)
    ND = m_leaf('#1f5e3a', '#2f7d45', '#4f9d55', '#5fae62', 'needle')
    tiers = 5
    def build(bm):
        out = []
        for t in range(tiers):
            k = t / (tiers - 1)
            zt = z + h * (0.28 + 0.62 * k); rad = h * (0.42 - 0.3 * k)
            n = int(16 - 8 * k)
            for i in range(n):
                a = i * 2 * math.pi / n + R.uniform(-0.15, 0.15) + t
                d = V((math.cos(a), math.sin(a), -0.35)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((x, y, zt)), d, side, rad, 0.14 * h * (1 - 0.4 * k), 0.25, segs=3, lift=0.15):
                    out.append((f, 0))
        return out
    mesh_from_blades('pine', build, [ND])
    if snow:
        SN = m_snow()
        for t in range(tiers):
            k = t / (tiers - 1)
            zt = z + h * (0.28 + 0.62 * k); rad = h * (0.42 - 0.3 * k)
            o = blob('snowcap', (x, y, zt - rad * 0.12), (rad * 0.62, rad * 0.62, rad * 0.16), SN, sub=1, seg=16)
            wobble(o, rad * 0.06, 5.0, seed + t)
        blob('snowtop', (x, y, z + h * 0.97), (0.05 * h, 0.05 * h, 0.04 * h), SN, sub=1, seg=10)

def thatch(cx, cy, z0, z1, r0, r1, seed, layers=6, m=None):
    """Saz çatı: aşağıdan yukarı halka halka sarkan saz demetleri (yaprak şeritleri); tepe topuzu."""
    R = random.Random(seed)
    M = m or m_leaf('#b98a3e', '#d4a855', '#e8c674', '#f0d58e', 'straw')
    def build(bm):
        out = []
        for L in range(layers):
            k = L / (layers - 1)
            z = z0 + (z1 - z0) * k; rad = r0 + (r1 - r0) * k
            n = int(56 - 36 * k)
            for i in range(n):
                a = i * 2 * math.pi / n + R.uniform(-0.04, 0.04) + L * 0.3
                base = V((cx + math.cos(a) * rad * 0.6, cy + math.sin(a) * rad * 0.6, z + (z1 - z0) / layers * 0.9))
                d = V((math.cos(a), math.sin(a), -0.75)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, base, d, side, rad * 0.5 + 0.1 + R.uniform(-0.03, 0.03), 0.12 + 0.05 * (1 - k), 0.02, segs=2):
                    out.append((f, 0))
        return out
    mesh_from_blades('thatch', build, [M])

def c_garden():
    """Bahçe: iki kütük çerçeveli yükseltilmiş tarh (koyu ekili toprak), sıra sıra havuç (turuncu omuz + tüylü yaprak),
    lahana (iç içe yuvarlak yapraklar), sırıklı domates, iki ayçiçeği; aradan basamak taşlı patika, turkuaz sulama kabı,
    arkada alçak çit; kenarlarda ot ve çiçek."""
    W = m_wood('#8f5d36', 'bedw'); SOIL = m_soil(); R = random.Random(13)
    beds = [(-0.62, 0.0), (0.62, 0.0)]
    BW, BD = 0.95, 1.7
    for (bx, by) in beds:
        for sy in (-1, 1):
            tube('log', [(bx - BW / 2 - 0.05, by + sy * BD / 2, 0.11), (bx, by + sy * BD / 2, 0.12), (bx + BW / 2 + 0.05, by + sy * BD / 2, 0.11)], [0.09, 0.095, 0.09], W, res=4)
        for sx in (-1, 1):
            tube('log', [(bx + sx * BW / 2, by - BD / 2 - 0.05, 0.11), (bx + sx * BW / 2, by, 0.12), (bx + sx * BW / 2, by + BD / 2 + 0.05, 0.11)], [0.088, 0.092, 0.088], W, res=4)
        s_ = rbox('soil', (bx, by, 0.12), (BW - 0.04, BD - 0.04, 0.2), SOIL, bevel=0.05, seg=3)
        bpy.ops.object.select_all(action='DESELECT')
        sm = s_.modifiers.new('sub', 'SUBSURF'); sm.levels = 2
        wobble(s_, 0.03, 6.0, int(bx * 10))
        for zz in range(3):                                    # tarh sıraları (hafif tümsek)
            blob('row', (bx - 0.28 + zz * 0.28, by, 0.22), (0.1, BD * 0.44, 0.04), SOIL, sub=1, seg=12)
    # sol tarh: havuç + lahana
    LEAFC = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'carrotleaf'); CAR = m_flat('#f07a2a', 0.15, 10, 'carrot')
    CAB = m_leaf('#7fbf5a', '#a8d982', '#d2efb0', '#e8f8d0', 'cabbage')
    carrots = []
    for j in range(5):
        for xi in (-0.28, 0.0):
            carrots.append((-0.62 + xi, -0.65 + j * 0.32))
    for (x, y) in carrots:
        blob('carrot', (x, y, 0.24), (0.045, 0.045, 0.05), CAR, sub=1, seg=10)
    def ctops(bm):
        out = []
        for (x, y) in carrots:
            for k in range(5):
                a = k * 1.26 + R.uniform(0, 0.4); up = R.uniform(0.7, 0.95)
                d = V((math.cos(a) * (1 - up), math.sin(a) * (1 - up), up)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((x, y, 0.27)), d, side, R.uniform(0.18, 0.26), 0.03, 0.5, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('ctops', ctops, [LEAFC])
    cab = [(-0.34, -0.55 + j * 0.37) for j in range(4)]
    def cabbages(bm):
        out = []
        for (x, y) in cab:
            for ring, (nn, up, L) in enumerate(((7, 0.25, 0.2), (6, 0.55, 0.15), (5, 0.85, 0.1))):
                for k in range(nn):
                    a = k * 2 * math.pi / nn + ring * 0.5
                    d = V((math.cos(a) * (1 - up), math.sin(a) * (1 - up), up)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                    for f in blade(bm, V((x, y, 0.23 + ring * 0.02)), d, side, L, 0.09 - ring * 0.015, 0.6 - ring * 0.25, segs=3, lift=0.2): out.append((f, 0))
        return out
    mesh_from_blades('cabbages', cabbages, [CAB])
    for (x, y) in cab: blob('heart', (x, y, 0.3), (0.07, 0.07, 0.06), m_flat('#c9e8a0', 0.1, 10, 'cabheart'), sub=1, seg=12)
    # sağ tarh: domates sırıkları + ayçiçekleri
    ST = m_wood('#a8693d', 'stake'); TOM = m_flat('#e8463c', 0.15, 12, 'tomato'); TL = m_leaf('#2f7d35', '#4f9d45', '#8bc65a', '#a8d87a', 'tomleaf')
    for j in range(3):
        x, y = 0.45, -0.55 + j * 0.55
        tube('stake', [(x, y, 0.15), (x + 0.01, y, 0.95)], [0.018, 0.016], ST, res=2)
        pts = [(x + math.cos(t * 6) * 0.05, y + math.sin(t * 6) * 0.05, 0.22 + t * 0.7) for t in [i / 10 for i in range(11)]]
        tube('vine', pts, [0.012] * len(pts), m_flat('#4f8f35', 0.15, 8, 'tvine'), res=2)
        for k in range(4):
            blob('tom', (x + math.cos(k * 2.1) * 0.08, y + math.sin(k * 2.1) * 0.08, 0.45 + k * 0.12), (0.055, 0.055, 0.05), TOM, sub=1, seg=12)
        def tl(bm, x=x, y=y):
            out = []
            for k in range(8):
                a = k * 2.3; z = 0.3 + k * 0.08
                d = V((math.cos(a), math.sin(a), 0.2)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((x, y, z)), d, side, 0.16, 0.06, 0.5, segs=3): out.append((f, 0))
            return out
        mesh_from_blades('tleaves', tl, [TL])
    for (x, y, h) in ((0.82, -0.35, 1.25), (0.84, 0.45, 1.05)):
        tube('sstem', [(x, y, 0.2), (x + 0.03, y, h * 0.6), (x + 0.06, y - 0.03, h)], [0.022, 0.02, 0.018], m_flat('#4f8f35', 0.15, 8, 'sstem'), res=3)
        PETS = m_flat('#ffcf2e', 0.12, 9, 'sunpet')
        for k in range(14):
            b_ = k * 2 * math.pi / 14
            blob('sp', (x + 0.06, y - 0.03 - 0.03 + math.cos(b_) * 0.13 * 0.3, h + math.sin(b_) * 0.13), (0.03, 0.09, 0.012), PETS,
                 rot=(math.degrees(b_) - 90, 0, 0), sub=0, seg=8).location = (x + 0.06 - 0.02, y - 0.03 + math.cos(b_) * 0.13, h + math.sin(b_) * 0.13)
        blob('sc', (x + 0.05, y - 0.03, h), (0.03, 0.09, 0.09), m_flat('#6b4224', 0.25, 30, 'seedc'), sub=1, seg=12)
    # patika taşları + sulama kabı + arka çit
    STN = m_rock()
    for k in range(5):
        o = pebble((0.0 + R.uniform(-0.05, 0.05), -0.85 + k * 0.42, 0.02), 0.13, STN, 70 + k); o.scale = (1.0, 0.85, 0.35)
    TEAL = m_metal('#2fa3a0', '#d7c06a', 'canm')
    can = lathe('can', [(0.001, 0.0), (0.13, 0.0), (0.14, 0.12), (0.12, 0.24), (0.001, 0.25)], TEAL, segs=16); can.location = (-1.35, -0.85, 0)
    tube('spout', [(-1.25, -0.85, 0.08), (-1.1, -0.85, 0.2), (-1.02, -0.85, 0.3)], [0.025, 0.02, 0.018], TEAL, res=3)
    blob('rose', (-1.0, -0.85, 0.31), (0.04, 0.04, 0.03), TEAL, sub=1, seg=10)
    tube('handle', [(-1.45, -0.85, 0.12), (-1.42, -0.85, 0.36), (-1.32, -0.85, 0.36), (-1.28, -0.85, 0.25)], [0.015] * 4, TEAL, res=3)
    PK = m_wood('#c9a77a', 'picket', paint='#f4e6c6')
    for k in range(11):
        x = -1.25 + k * 0.25
        prism('picket', [(-0.05, 0), (0.05, 0), (0.05, 0.42), (0, 0.48), (-0.05, 0.42)], 0.03, PK, loc=(x, 1.12, -0.02), rot=(0, R.uniform(-3, 3), 0))
    for z in (0.12, 0.32):
        plank('prail', (0, 1.14, z), (2.65, 0.03, 0.05), PK, seed=int(z * 100))
    dress(1.55, 41, n_tufts=8, flowers=5, pebbles=2, bushes=[(-1.35, 0.6), (1.35, -0.85)], exclude=lambda x, y: abs(x) < 1.15 and abs(y) < 1.15)
    return 'bahçe'

def surfboard(loc, L, wdt, c1, c2, rot, name):
    """Sörf tahtası: damla biçimli yassı gövde (alt-üst kenar yuvarlak), ortada şerit."""
    CL = m_cloth(c1, c2, stripes=3.0, name=name)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1)
    o = bpy.context.object; o.scale = (wdt / 2, L / 2, 0.035)
    bpy.ops.object.transform_apply(scale=True)
    for v in o.data.vertices:
        t = v.co.y / (L / 2)
        v.co.x *= (1 - 0.35 * max(0, t)) * (1 - 0.15 * max(0, -t))
    o.data.materials.append(CL); smooth(o)
    me = o.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = (co.x / wdt * 0.9 + 0.5, co.y)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o

def c_surf():
    """Sörf kulübesi: kazıklar üstünde küçük ahşap kulübe (boyalı yatay tahtalar, açık tezgâh penceresi), saz çatı,
    yanına yaslanmış üç renkli sörf tahtası, dalga simgeli tabela, kumda kabuklar, yanında küçük palmiye fidanı ve ot."""
    W = [m_wood(c, f'surfw{i}', paint=p) for i, (c, p) in enumerate((('#b98a5a', '#7fd0d8'), ('#b98a5a', '#f6e6c4')))]
    DK = m_wood('#7a5232', 'surfdark'); FL = m_wood('#c99a66', 'surffloor')
    SW, SD, SH, Z0 = 1.7, 1.3, 1.2, 0.25
    for x in (-SW / 2, SW / 2):
        for y in (-SD / 2, SD / 2):
            post('stilt', (x, y, -0.05), (x, y, Z0 + SH), 0.07, DK, seed=int(x * 10 + y * 7))
    for k in range(8):
        plank('floor', (0, -SD / 2 - 0.2 + k * 0.2, Z0), (SW + 0.2, 0.18, 0.05), FL, seed=k + 3)
    rows = int(SH / 0.16)
    for r in range(rows):
        z = Z0 + 0.1 + r * 0.16
        m = W[(r // 2) % 2]
        plank('back', (0, SD / 2, z), (SW, 0.05, 0.15), m, seed=r)
        for sx in (-1, 1): plank('side', (sx * SW / 2, 0, z), (0.05, SD, 0.15), m, seed=r + sx * 20)
        if z < Z0 + 0.55 or z > Z0 + 1.05:          # ön: tezgâh penceresi açık
            plank('front', (0, -SD / 2, z), (SW, 0.05, 0.15), m, seed=r + 40)
    plank('counter', (0, -SD / 2 - 0.08, Z0 + 0.55), (SW + 0.1, 0.24, 0.05), FL, seed=9)
    thatch(0, 0, Z0 + SH + 0.02, Z0 + SH + 0.62, 1.2, 0.2, 5, layers=7)
    blob('knot', (0, 0, Z0 + SH + 0.68), (0.12, 0.12, 0.1), m_leaf('#b98a3e', '#d4a855', '#e8c674', '#f0d58e', 'straw'), sub=1, seg=12)
    # tahtalar
    surfboard((-1.05, -0.95, 0.82), 1.6, 0.42, '#ff7a59', '#fff1d6', (16, 0, 18), 'sb1')
    surfboard((-1.2, -0.3, 0.8), 1.6, 0.4, '#2fb6c4', '#fff1d6', (12, -10, 6), 'sb2')
    surfboard((1.15, -0.85, 0.78), 1.55, 0.4, '#ffd447', '#ff7aa8', (16, 6, -16), 'sb3')
    # tabela: dalga simgesi
    SB = m_wood('#b98a5a', 'surfsign', paint='#2f8a8a')
    plank('sign', (0, -SD / 2 - 0.04, Z0 + SH + 0.0), (0.8, 0.04, 0.24), SB, seed=12)
    WV = m_flat('#fff6e6', 0.05, 8, 'waveic')
    pts = [(-0.25 + i * 0.025, -0.05 + 0.06 * math.sin(i * 0.42) + (0.06 if i > 16 else 0) * math.sin((i - 16) * 0.8)) for i in range(21)]
    tube('wave', [(x, -SD / 2 - 0.07, Z0 + SH + z) for x, z in pts], [0.018] * len(pts), WV, res=2)
    # kumda kabuklar, deniz yıldızı, fidan
    SHL = m_flat('#f7d9c4', 0.1, 10, 'shell1')
    for k, (x, y) in enumerate(((0.6, -1.15), (-0.4, -1.2), (1.3, 0.6))):
        for j in range(5):
            b_ = math.radians(-50 + j * 25)
            blob('shell', (x + math.sin(b_) * 0.04, y + math.cos(b_) * 0.04, 0.012), (0.018, 0.05, 0.012), SHL, rot=(0, 0, -math.degrees(b_)), sub=0, seg=8)
    LEAF = m_leaf('#3f9a3a', '#6cc94c', '#b5e26a', '#d8f08a', 'palmling')
    def sprout(bm):
        out = []
        for k in range(7):
            a = k * 0.9; d = V((math.cos(a), math.sin(a), 0.7)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, V((1.35, 0.9, 0.05)), d, side, 0.5, 0.11, 0.9, segs=4, lift=0.2): out.append((f, 0))
        return out
    mesh_from_blades('sprout', sprout, [LEAF])
    G1 = m_leaf('#5f9a3d', '#86b85a', '#c7dd8a', '#dbe9a8', 'dunegrass')
    for k, (x, y) in enumerate(((-1.3, 0.85), (1.2, -1.0), (-0.9, -1.15))):
        mesh_from_blades('tuft', tufts((x, y, 0.0), 0.14, 2, 50 + k, h=(0.22, 0.38)), [G1])
    return 'sörf'

def c_swim():
    """Yüzme gölü: yuvarlak kayalarla çevrili doğal havuz (ortası derin turkuaz, kenarı açık), kayadan uzanan tahta
    atlama iskelesi, demir merdiven, suda yüzen simit, kenarda şemsiye gibi geniş yapraklı bitkiler ve çiçekler."""
    STN = m_rock(moss_th=(0.95, 1.25), warm=('#a39586', '#bba996', '#d2c2a8'), name='poolrock'); R = random.Random(9)
    # su yüzeyi: düzensiz elips disk
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    N = 40; ctr = bm.verts.new((0, 0, 0.12)); ring = []
    def rad(a): return 1.0 + 0.12 * math.sin(a * 3 + 1) + 0.07 * math.sin(a * 5)
    for i in range(N):
        a = i / N * 2 * math.pi; ring.append(bm.verts.new((math.cos(a) * rad(a) * 1.15, math.sin(a) * rad(a) * 0.85, 0.12)))
    for i in range(N): bm.faces.new((ctr, ring[i], ring[(i + 1) % N]))
    water = link_mesh('water', bm, [m_water()])
    sm = water.modifiers.new('sub', 'SUBSURF'); sm.levels = 2
    # havuz tabanı (su altında koyu kum çanak)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(0, 0, -0.26))
    bowl = bpy.context.object; bowl.scale = (1.2, 0.9, 0.35); bowl.data.materials.append(m_sand('poolbed', '#c9b58a'))
    # kenar kayaları
    for i in range(22):
        a = i / 22 * 2 * math.pi + R.uniform(-0.05, 0.05)
        rr = rad(a); r = R.uniform(0.17, 0.27)
        rock((math.cos(a) * rr * 1.25, math.sin(a) * rr * 0.95, 0.1), r, STN, i, sq=(1.0, 1.0, 0.75))
    for i in range(10):
        a = i / 10 * 2 * math.pi + 0.3; rr = rad(a) + 0.3
        rock((math.cos(a) * rr * 1.25, math.sin(a) * rr * 0.98, 0.18), R.uniform(0.22, 0.32), STN, i + 40, sq=(1.0, 1.0, 0.9))
    # atlama iskelesi (arka kenardan)
    DK = m_wood('#c99a66', 'diveb'); DW = m_wood('#8f5d36', 'divep')
    plank('dive', (0.3, 0.65, 0.42), (0.36, 0.95, 0.06), m_wood('#c9a77a', 'divepaint', paint='#2fa3a0'), rot=(-4, 0, 0), seed=3)
    for y in (0.95, 1.12):
        post('dpost', (0.18, y, 0.0), (0.18, y, 0.42), 0.04, DW, seed=int(y * 10)); post('dpost', (0.42, y, 0.0), (0.42, y, 0.42), 0.04, DW, seed=int(y * 10) + 1)
    # merdiven
    I = m_metal('#c9ccd6', '#9aa0aa', 'steel')
    for sx in (-0.12, 0.12):
        tube('lrail', [(-1.1 + sx, -0.3, 0.05), (-1.15 + sx, -0.3, 0.5), (-1.3 + sx, -0.3, 0.55), (-1.38 + sx, -0.3, 0.4)], [0.02] * 4, I, res=4)
    for z in (0.15, 0.3):
        tube('rung', [(-1.24, -0.3, z), (-1.0, -0.3, z)], [0.015, 0.015], I, res=2)
    # simit
    RING = m_cloth('#ff7aa8', '#fff1d6', stripes=4.0, name='floatie')
    bpy.ops.mesh.primitive_torus_add(major_radius=0.2, minor_radius=0.075, location=(-0.3, -0.15, 0.15), major_segments=28, minor_segments=10)
    t = bpy.context.object; t.data.materials.append(RING); t.rotation_euler = (math.radians(6), 0, 0)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, 0)
    # su bitkileri: nilüfer yaprakları + kenarda geniş yapraklı bitkiler
    LP = m_leaf('#3f9a3a', '#5fb446', '#8fd06a', '#b5e26a', 'lilypad')
    for k, (x, y) in enumerate(((0.6, -0.35), (0.75, -0.15), (-0.55, 0.35))):
        o = blob('lily', (x, y, 0.13), (0.13, 0.13, 0.01), LP, sub=1, seg=16)
    flower_heads([(0.6, -0.35, 0.16), (-0.55, 0.36, 0.16)], R, size=1.1)
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('plants', rosette([(1.55, 0.35), (-1.5, 0.55), (1.2, -1.0), (-0.9, -1.15)], R, sizes=(0.35, 0.5), leaves=9), [BL])
    dress(1.8, 22, n_tufts=8, flowers=5, pebbles=0, stone=STN, exclude=lambda x, y: (x / 1.55) ** 2 + (y / 1.2) ** 2 < 1.0)
    return 'havuz'

def c_game_hut():
    """Oyun kulübesi: yuvarlak, dikey tahtalı duvar (aşınmış mor-krem boya), kat kat pul kiremitli konik çatı (mor-turkuaz),
    tepede yıldız bayrak, saçaktan sarkan renkli flama, kemerli kapı + "▶" boyalı tabela; önde büyük zar ve top."""
    R = random.Random(17)
    RAD, H = 1.0, 1.2
    WP = [m_wood('#b98a5a', 'ghw1', paint='#f6e6c4'), m_wood('#b98a5a', 'ghw2', paint='#ffd9a8')]
    n = 30
    for k in range(n):
        a = k / n * 2 * math.pi
        if abs(((a - 3 * math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < 0.32: continue   # kapı boşluğu (önde, -y)
        plank('wall', (math.cos(a) * RAD, math.sin(a) * RAD, H / 2), (0.05, 0.22, H + R.uniform(-0.03, 0.03)), WP[k % 2], rot=(0, 0, math.degrees(a)), seed=k, amt=0.006)
    cyl('inner', (0, 0, H / 2), RAD - 0.04, H, m_wood('#5d3a22', 'ghin'), verts=24)
    DK = m_wood('#7a5232', 'ghdark')
    for z in (0.08, H - 0.05):
        bpy.ops.mesh.primitive_torus_add(major_radius=RAD + 0.03, minor_radius=0.04, location=(0, 0, z), major_segments=40, minor_segments=6)
        bpy.context.object.data.materials.append(DK)
    # kapı
    DR = m_wood('#b98a5a', 'ghdoor', paint='#2fa3a0')
    for k in range(3): plank('door', (-0.13 + k * 0.13, -RAD + 0.02, 0.45), (0.12, 0.05, 0.85), DR, seed=k + 30)
    blob('darch', (0, -RAD + 0.02, 0.88), (0.2, 0.05, 0.12), DR, sub=1, seg=12)
    blob('knob', (0.12, -RAD - 0.03, 0.45), (0.025, 0.02, 0.025), m_flat('#f2c14e', 0.1, 6, 'gold'), sub=0, seg=8)
    # çatı: halka halka pul kiremit
    TILES = [m_tile('#7c5cd6', 'ght1'), m_tile('#9a7ae8', 'ght2'), m_tile('#2fa3a0', 'ght3')]
    RB, RH = RAD + 0.32, 1.2                                    # çatı taban yarıçapı, yüksekliği
    phi = math.atan2(RH, RB)
    lathe('roofcore', [(RB - 0.02, H + 0.02), (RB * 0.5, H + RH * 0.55), (0.05, H + RH), (0.001, H + RH + 0.01)], m_tile('#6a4cc0', 'ghcore'), segs=32)
    rows = 8
    for r in range(rows):
        k = (r + 0.5) / rows
        rr = RB * (1 - k) + 0.06; z = H + RH * k + 0.03
        cnt = max(5, int(2 * math.pi * rr / 0.19))
        for i in range(cnt):
            a = i / cnt * 2 * math.pi + (math.pi / cnt if r % 2 else 0)
            t = V((-math.sin(a), math.cos(a), 0)); sdn = V((math.cos(a) * math.cos(phi), math.sin(a) * math.cos(phi), -math.sin(phi)))
            nrm = sdn.cross(t).normalized()
            if nrm.z < 0: nrm = -nrm
            M = mathutils.Matrix((t, nrm, t.cross(nrm))).transposed()
            o = blob('scale', (math.cos(a) * rr + nrm.x * 0.02, math.sin(a) * rr + nrm.y * 0.02, z + nrm.z * 0.02), (0.11, 0.02, 0.13),
                     TILES[2 if r == rows - 1 else (r // 2) % 2], sub=0, seg=10)
            o.rotation_euler = M.to_euler()
    STAR = m_flat('#ffc93a', 0.1, 8, 'star')
    tube('pole', [(0, 0, H + 1.15), (0, 0, H + 1.65)], [0.02, 0.016], DK, res=2)
    pts = []
    for k in range(10):
        b_ = math.pi / 2 + k * math.pi / 5; rr = 0.14 if k % 2 == 0 else 0.065
        pts.append((math.cos(b_) * rr, math.sin(b_) * rr))
    prism('star', pts, 0.04, STAR, loc=(0, 0, H + 1.73), rot=(0, 0, -25), bevel=0.012)
    # flama
    FLAGS = [m_flat(c, 0.08, 8, 'fl' + c) for c in ('#ff7a59', '#ffd447', '#2fb6c4', '#ff7aa8', '#8fd06a')]
    for i in range(16):
        a0 = i / 16 * 2 * math.pi; a1 = (i + 1) / 16 * 2 * math.pi
        p0 = V((math.cos(a0) * (RAD + 0.3), math.sin(a0) * (RAD + 0.3), H + 0.0)); p1 = V((math.cos(a1) * (RAD + 0.3), math.sin(a1) * (RAD + 0.3), H + 0.0))
        mid = (p0 + p1) / 2 - V((0, 0, 0.08))
        tube('string', [tuple(p0), tuple(mid), tuple(p1)], [0.006] * 3, m_rope(), res=2)
        c = mid; d = (p1 - p0).normalized()
        bpy.ops.mesh.primitive_cylinder_add(vertices=3, radius=0.08, depth=0.01, location=c - V((0, 0, 0.06)), rotation=(math.radians(90), 0, math.atan2(d.y, d.x)))
        o = bpy.context.object; o.rotation_euler = (math.radians(90), math.radians(-90), math.atan2(d.y, d.x)); o.data.materials.append(FLAGS[i % 5])
    # oyun tabelası: oynat simgesi
    SB = m_wood('#b98a5a', 'ghsign', paint='#ff7a59')
    plank('sign', (0, -RAD - 0.05, 1.05), (0.42, 0.04, 0.22), SB, seed=4)
    prism('play', [(-0.05, -0.06), (0.07, 0.0), (-0.05, 0.06)], 0.012, m_flat('#fff6e6', 0.05, 6, 'ic_w'), loc=(0, -RAD - 0.075, 1.05), bevel=0.004)
    # zar + top
    DICE = m_plaster('#fff6e8', name='dice', dirt=0.0); DOT = m_flat('#3a3550', 0.05, 6, 'dot')
    rbox('dice', (0.75, -1.15, 0.2), (0.4, 0.4, 0.4), DICE, rot=(0, 0, 25), bevel=0.07, seg=3)
    a = math.radians(25)
    for (u, v) in ((-0.1, 0.1), (0.1, -0.1), (0, 0)):
        blob('dot', (0.75 + (u * math.cos(a)) - (-0.205) * math.sin(a) * 0 + math.sin(a) * 0.0, -1.15 - 0.205 * math.cos(a) + u * math.sin(a), 0.2 + v), (0.035, 0.012, 0.035), DOT, rot=(0, 0, 25), sub=0, seg=8)
    for (u, v) in ((-0.1, -0.1), (0.1, 0.1), (-0.1, 0.1), (0.1, -0.1)):
        blob('dot', (0.75 + u, -1.15 + v, 0.405), (0.035, 0.035, 0.01), DOT, sub=0, seg=8)
    BALL = m_cloth('#ff7aa8', '#ffd447', stripes=3.0, name='ball')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.18, location=(-0.85, -1.05, 0.18))
    b = bpy.context.object; b.data.materials.append(BALL); smooth(b)
    me = b.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0 * 2, 0)
    dress(1.55, 51, n_tufts=9, flowers=5, pebbles=3, bushes=[(-1.2, 0.5), (1.15, 0.6), (-0.4, 1.2)], exclude=lambda x, y: math.hypot(x, y) < 1.2 or (abs(x) < 1.1 and -1.4 < y < -0.9))
    return 'oyun kulübesi'

def c_festival():
    """Festival çadırı: sekizgen, şeritli (mercan-krem) duvar, kubbe gibi yumuşak eğimli tepe, fistolu saçak, tepede
    flama, aralık giriş perdesi (bağlı), dışarıya gerilmiş renkli flama ipleri ve kazıklar, girişte iki fener."""
    R = random.Random(23)
    RAD, H = 1.1, 1.0
    CL = m_cloth('#f05d5e', '#ffd86b', stripes=8.0, name='tentwall')
    # duvar: sekizgen, biraz içeri bombeli; giriş açıklığı (önde)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); ds = bm.faces.layers.int.new('ds')
    NA, NZ = 48, 6
    grid = []
    for j in range(NZ + 1):
        z = H * j / NZ; row = []
        for i in range(NA + 1):
            a = i / NA * 2 * math.pi - math.pi / 2 + 0.38
            k8 = math.cos(math.pi / 8) / math.cos(((a % (math.pi / 4)) - math.pi / 8))
            r = RAD * k8 * (1 - 0.04 * math.sin(math.pi * j / NZ))
            row.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        grid.append(row)
    for j in range(NZ):
        for i in range(NA - 3):                                # son birkaç dilim = giriş
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])); f[ds] = 1
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / NA, jj / NZ)
    # çatı: kubbe-koni
    CR = m_cloth('#f05d5e', '#fff1d6', stripes=8.0, name='tentroof')
    rows = []
    NR = 8
    for j in range(NR + 1):
        t = j / NR; r = (RAD + 0.15) * (1 - t) ** 1.15 + 0.001; z = H + 1.15 * (1 - (1 - t) ** 1.35)
        row = []
        for i in range(NA + 1):
            a = i / NA * 2 * math.pi - math.pi / 2 + 0.38
            row.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rows.append(row)
    for j in range(NR):
        for i in range(NA):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])); f[ds] = 1; f.material_index = 1
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / NA, jj / NR)
    # saçak fistosu
    for k in range(16):
        top = []; bot = []
        for q in range(5):
            i = k * 3 + q * 3 / 4
            a = i / NA * 2 * math.pi - math.pi / 2 + 0.38; r = RAD + 0.16
            d = math.sin(math.pi * q / 4)
            top.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, H + 0.0)))
            bot.append(bm.verts.new((math.cos(a) * (r + 0.01), math.sin(a) * (r + 0.01), H - 0.05 - 0.12 * d ** 0.7)))
        for q in range(4):
            f = bm.faces.new((top[q], top[q + 1], bot[q + 1], bot[q])); f[ds] = 1; f.material_index = 2
            for lp in f.loops: lp[uvl].uv = (k % 2 * 0.5 / 8 + 0.01, 0)
    tent = link_mesh('tent', bm, [CL, CR, m_flat('#ffc93a', 0.08, 8, 'scallop')]); smooth(tent)
    # giriş perdeleri (bağlı, iki yanda)
    for s_ in (-1, 1):
        a = -math.pi / 2 + s_ * 0.2
        o = blob('flap', (math.cos(a) * RAD * 1.02 + s_ * 0.02, math.sin(a) * RAD * 1.02, 0.55), (0.12, 0.05, 0.5), m_flat('#f05d5e', 0.1, 8, 'flapc'), rot=(0, s_ * 6, math.degrees(a) + 90), sub=1, seg=12)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.08, minor_radius=0.014, location=(math.cos(a) * RAD * 1.05, math.sin(a) * RAD * 1.05, 0.5), major_segments=14, minor_segments=4)
        bpy.context.object.data.materials.append(m_rope())
    cyl('floor', (0, 0, 0.02), RAD * 0.98, 0.04, m_wood('#8f5d36', 'tentfloor'), verts=24)
    # tepe: direk + flama
    DK = m_wood('#7a5232', 'fpole')
    tube('pole', [(0, 0, H + 1.1), (0, 0, H + 1.65)], [0.025, 0.02], DK, res=2)
    blob('ball', (0, 0, H + 1.67), (0.04, 0.04, 0.04), m_flat('#ffc93a', 0.08, 8, 'gold2'), sub=1, seg=10)
    pts = [(0.0, 0.0), (0.38, -0.05), (0.32, -0.12), (0.4, -0.2), (0.0, -0.22)]
    prism('pennant', [(x, z) for x, z in pts], 0.012, m_flat('#2fb6c4', 0.08, 8, 'penn'), loc=(0.02, 0, H + 1.63), rot=(0, 0, 0), bevel=0.004)
    # dış ipler + kazıklar + flamalar
    FLAGS = [m_flat(c, 0.08, 8, 'fl' + c) for c in ('#ffd447', '#2fb6c4', '#ff7aa8', '#8fd06a', '#7c5cd6')]
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        p0 = V((math.cos(a) * (RAD + 0.15), math.sin(a) * (RAD + 0.15), H - 0.02)); p1 = V((math.cos(a) * (RAD + 0.85), math.sin(a) * (RAD + 0.85), 0.12))
        tube('guy', [tuple(p0), tuple((p0 + p1) / 2 - V((0, 0, 0.05))), tuple(p1)], [0.008] * 3, m_rope(), res=2)
        post('stake', tuple(p1 - V((0, 0, 0.12))), tuple(p1 + V((0, 0, 0.08))), 0.025, DK, seed=k)
        for q in range(4):
            t = (q + 0.5) / 4; c = p0.lerp(p1, t) - V((0, 0, 0.05 * 4 * t * (1 - t)))
            o = prism('flag', [(-0.05, 0), (0.05, 0), (0, -0.11)], 0.008, FLAGS[(k + q) % 5], loc=tuple(c), rot=(0, 0, math.degrees(a) + 90), bevel=0.002)
    GL = m_glow(); I = m_metal()
    for s_ in (-1, 1):
        x = s_ * 0.55; y = -RAD - 0.35
        post('lpost', (x, y, -0.03), (x, y, 0.95), 0.035, DK, seed=s_ + 4)
        blob('lamp', (x, y, 1.02), (0.08, 0.08, 0.1), GL, sub=1, seg=12)
        cyl('lcap', (x, y, 1.12), 0.07, 0.03, I, verts=10)
    dress(1.9, 61, n_tufts=9, flowers=6, pebbles=2, bushes=[(-1.45, 0.3), (1.4, 0.55), (0.3, 1.5)], exclude=lambda x, y: math.hypot(x, y) < 1.35 or (abs(x) < 0.4 and y < 0))
    return 'festival'

def c_cave():
    """Mağara: yumuşak hatlı kaya tepeciği içinde kemerli karanlık giriş, üstte yosun örtüsü ve sarkan sarmaşıklar,
    girişin iki yanında ışıldayan turkuaz kristaller, önünde basamak taşlı toprak patika, kenarlarda çalı ve çiçek."""
    STN = m_rock(moss_th=(0.9, 1.15), warm=('#7d7684', '#958d98', '#b0a79c'), name='caverock'); R = random.Random(31)
    # ana kütle: kaya kümesi (gürültülü küreler) → voksel birleştir
    parts = []
    for (loc, r, sq) in (((0, 0.25, 0.55), 1.05, (1.15, 0.9, 0.85)), ((-0.85, 0.35, 0.35), 0.7, (1.0, 1.0, 0.9)), ((0.9, 0.3, 0.4), 0.72, (1.0, 1.0, 0.95)),
                         ((0.2, 0.75, 0.8), 0.75, (1.0, 0.9, 0.9)), ((-0.5, -0.25, 0.25), 0.45, (1.0, 1.0, 0.9)), ((0.6, -0.25, 0.22), 0.42, (1.0, 1.0, 0.9))):
        parts.append(rock(loc, r, STN, len(parts), sq=sq, sub=3, amt=0.14))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    mass = bpy.context.object
    rm = mass.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.05
    bpy.ops.object.modifier_apply(modifier='rm')
    # giriş: kesme (boolean) — kemer biçimli tünel
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.55, depth=1.4, location=(0, -0.55, 0.38), rotation=(math.radians(90), 0, 0))
    cut = bpy.context.object; cut.scale = (1.0, 1.3, 1.0)
    bo = mass.modifiers.new('bo', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = mass; bpy.ops.object.modifier_apply(modifier='bo')
    bpy.data.objects.remove(cut)
    for v in mass.data.vertices:
        if v.co.z < 0: v.co.z = v.co.z * 0.2
    sm = mass.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.5; sm.iterations = 4
    smooth(mass)
    # içi karanlık
    blob('dark', (0, 0.2, 0.35), (0.42, 0.5, 0.5), m_flat('#1d1a2a', 0.1, 6, 'cavedark'), sub=1, seg=16)
    # tepede ot öbekleri (yosun dokunun içinden)
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    for k in range(8):
        x, y = R.uniform(-0.9, 0.9), R.uniform(0.0, 0.8)
        ok, loc, nrm, *_ = bpy.context.scene.ray_cast(dg, V((x, y, 4)), V((0, 0, -1)))
        if ok: mesh_from_blades('toptuft', tufts(tuple(loc - V((0, 0, 0.02))), 0.15, 2, 90 + k, h=(0.16, 0.28)), [G1])
    # sarkan sarmaşıklar (giriş üstü)
    V1 = m_flat('#3f7f2f', 0.2, 8, 'vine'); LV = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'vineleaf')
    leafs = []
    for k in range(7):
        x = -0.5 + k * 0.165; y0 = -0.72
        L = R.uniform(0.25, 0.5)
        pts = [(x, y0, 1.1), (x + 0.02, y0 - 0.04, 1.1 - L * 0.5), (x, y0 - 0.02, 1.1 - L)]
        tube('hang', pts, [0.008] * 3, V1, res=3)
        for q in range(4):
            leafs.append((V((x, y0 - 0.03, 1.07 - L * q / 4)), R.uniform(0, 6.28)))
    def lv(bm):
        out = []
        for (p, a) in leafs:
            d = V((math.cos(a), math.sin(a), -0.2)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, p, d, side, 0.08, 0.035, 0.3, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('vleaves', lv, [LV])
    # kristaller
    CR = m_plaster('#5fe0e8', name='crystal', dirt=0.0)
    for (x, y, h, tilt) in ((-0.72, -0.92, 0.36, 18), (-0.58, -1.0, 0.22, -12), (0.7, -0.9, 0.32, -16), (0.82, -0.82, 0.2, 22)):
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.07, radius2=0.0, depth=h, location=(x, y, h / 2 - 0.02), rotation=(0, math.radians(tilt), 0))
        bpy.context.object.data.materials.append(CR)
    # patika: yere yapışık düzensiz toprak + basamak taşları
    DIRT = m_dirt()
    bm = bmesh.new(); c0 = bm.verts.new((0, -1.15, 0.008)); ring = []
    for i in range(24):
        a = i / 24 * 2 * math.pi; r = 1 + 0.15 * mnoise.noise(V((math.cos(a) * 2, math.sin(a) * 2, 3)))
        ring.append(bm.verts.new((math.cos(a) * 0.38 * r, -1.15 + math.sin(a) * 0.55 * r, 0.008)))
    for i in range(24): bm.faces.new((c0, ring[i], ring[(i + 1) % 24]))
    link_mesh('path', bm, [DIRT])
    for k in range(3):
        o = pebble((R.uniform(-0.08, 0.08), -0.85 - k * 0.3, 0.02), 0.13, STN, 80 + k); o.scale = (1.0, 0.8, 0.3)
    dress(1.9, 71, n_tufts=10, flowers=5, pebbles=3, bushes=[(-1.25, -0.75), (1.25, -0.7), (-1.5, 0.3)], stone=STN, at=[(-0.95, -0.8), (1.0, -0.8)], exclude=lambda x, y: (abs(x) < 0.5 and y < -0.3) or math.hypot(x, y - 0.3) < 1.15)
    return 'mağara'

def c_mountain():
    """Tırmanma tepesi: yumuşak, katmanlı kaya tepe (yamaçlarda çimen yamaları), etrafından dolanan toprak patika
    (kenarında taşlar), tepede bayrak, yamaçlarda çam ve çalılar."""
    STN = m_rock(); HILL = m_rock(moss_th=(0.62, 0.85), grass=('#4f9a35', '#6db845', '#a6d65e'), warm=('#9a7f6e', '#b0917a', '#c8aa8c'), name='hillrock'); R = random.Random(41)
    parts = []
    for (loc, r, sq) in (((0, 0, 0.6), 1.2, (1.0, 1.0, 1.0)), ((0.15, 0.1, 1.35), 0.75, (1.0, 1.0, 1.0)), ((-0.6, 0.4, 0.4), 0.8, (1.0, 1.0, 0.8)),
                         ((0.7, -0.3, 0.35), 0.75, (1.0, 1.0, 0.8)), ((0.1, 0.25, 1.9), 0.4, (1.0, 1.0, 1.0))):
        parts.append(rock(loc, r, HILL, len(parts) + 5, sq=sq, sub=3, amt=0.12))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join(); hill = bpy.context.object
    rm = hill.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.06; bpy.ops.object.modifier_apply(modifier='rm')
    for v in hill.data.vertices:
        if v.co.z < 0: v.co.z *= 0.15
    sm = hill.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = 5
    smooth(hill)
    # patika: tepenin etrafında sarmal, yüzeye oturan yassı şerit (ışın ile yüzey bulunur)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    DIRT = m_sand('mpath', '#d9b27a')
    pts = []
    for i in range(70):
        t = i / 69; a = -math.pi / 2 + t * 2.3 * math.pi
        z = 0.12 + t * 2.05
        ok, loc, nrm, idx, ob, mx = bpy.context.scene.ray_cast(dg, V((math.cos(a) * 4, math.sin(a) * 4, z)), V((-math.cos(a), -math.sin(a), 0)))
        if ok: pts.append((loc + nrm * 0.05, nrm, a))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    prev = None
    for k, (p, nrm, a) in enumerate(pts):
        tan = (pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]).normalized()
        side = nrm.cross(tan).normalized()
        w = 0.22
        l = bm.verts.new(p + side * w); r = bm.verts.new(p - side * w)
        if prev:
            f = bm.faces.new((prev[0], prev[1], r, l))
        prev = (l, r)
    path = link_mesh('path', bm, [DIRT]); smooth(path)
    for k in range(0, len(pts), 5):
        p, nrm, a = pts[k]
        pebble(tuple(p + V((math.cos(a), math.sin(a), 0)) * 0.12 + V((0, 0, 0.17))), 0.06, STN, k)
    # bayrak
    DK = m_wood('#7a5232', 'mpole')
    tube('pole', [(0.1, 0.25, 2.2), (0.1, 0.25, 2.85)], [0.025, 0.02], DK, res=2)
    prism('flag', [(0, 0), (0.42, -0.08), (0, -0.2)], 0.015, m_flat('#ff5a5a', 0.08, 8, 'redflag'), loc=(0.12, 0.25, 2.83), bevel=0.004)
    for (x, y, h) in ((1.2, 0.6, 1.0), (-1.15, -0.4, 0.85), (-0.6, 1.0, 1.1)):
        pine((x, y, 0.0), h, int(x * 10 + y * 3))
    dress(1.9, 81, n_tufts=10, flowers=4, pebbles=3, bushes=[(1.35, -0.5), (-1.3, 0.35), (0.4, 1.35)], stone=STN, exclude=lambda x, y: math.hypot(x, y) < 1.2)
    return 'dağ'

def c_ski():
    """Kayak tepesi: karla örtülü yumuşak tepe, önden aşağı kayan oluklu pist (mavi gölgeli), tepede bayrak ve başlangıç
    kapısı, yanlarda karlı çamlar, aşağıda kırmızı kızak ve kardan küçük tümsekler."""
    SN = m_snow(); R = random.Random(51)
    # tepe: kutupsal ızgara (yuvarlak taban), önde (−y) oluklu pist
    def hgt(x, y):
        r = math.hypot(x / 1.15, (y - 0.4) / 1.35)
        h = 1.45 * max(0.0, 1 - r * r) ** 1.4 + 0.06
        groove = -0.07 * max(0.0, 1 - abs(x) / 0.32) ** 2 * (1 if y < 0.55 else 0)
        edge = max(0.0, 1 - math.hypot(x, y) / 1.85)
        return max(0.0, (h + groove + 0.03 * mnoise.noise(V((x * 2, y * 2, 0))))) * min(1.0, edge / 0.12)
    bm = bmesh.new()
    NR, NA = 30, 64; S = 1.85
    ctr = bm.verts.new((0, 0, hgt(0, 0))); rings = []
    for i in range(1, NR + 1):
        r = S * i / NR; row = []
        for j in range(NA):
            a = j / NA * 2 * math.pi; x, y = math.cos(a) * r, math.sin(a) * r
            row.append(bm.verts.new((x, y, hgt(x, y))))
        rings.append(row)
    for j in range(NA): bm.faces.new((ctr, rings[0][j], rings[0][(j + 1) % NA]))
    for i in range(NR - 1):
        for j in range(NA):
            j2 = (j + 1) % NA; bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j2], rings[i][j2]))
    hillo = link_mesh('snowhill', bm, [SN]); smooth(hillo)
    # pist kenar çizgileri (mavi bayrakçıklar) + başlangıç kapısı + bayrak
    DK = m_wood('#7a5232', 'skipole'); BL = m_flat('#2f8adf', 0.08, 8, 'blueflag'); RD = m_flat('#ff5a5a', 0.08, 8, 'redflag')
    for k in range(4):
        y = -1.1 + k * 0.45
        for sx in (-1, 1):
            x = sx * 0.42; z = hgt(x, y)
            tube('gate', [(x, y, z - 0.05), (x, y, z + 0.32)], [0.012, 0.012], DK, res=2)
            prism('pf', [(0, 0), (0.12 * sx, -0.04), (0, -0.09)], 0.008, BL if k % 2 else RD, loc=(x, y, z + 0.31), bevel=0.002)
    zt = hgt(0, 0.5)
    for sx in (-1, 1): post('gp', (sx * 0.3, 0.45, zt - 0.1), (sx * 0.3, 0.45, zt + 0.55), 0.035, DK, seed=sx)
    plank('gbar', (0, 0.45, zt + 0.52), (0.72, 0.06, 0.1), m_wood('#b98a5a', 'gbarp', paint='#ff5a5a'), seed=3)
    tube('fpole', [(0.2, 0.75, hgt(0.2, 0.75) - 0.05), (0.2, 0.75, hgt(0.2, 0.75) + 0.75)], [0.02, 0.018], DK, res=2)
    prism('flag', [(0, 0), (0.36, -0.07), (0, -0.18)], 0.012, RD, loc=(0.22, 0.75, hgt(0.2, 0.75) + 0.72), bevel=0.004)
    # karlı çamlar
    for (x, y, h) in ((-1.05, 0.6, 1.1), (1.0, 0.75, 1.25), (-0.95, -0.7, 0.85), (1.05, -0.55, 0.9), (0.5, 1.25, 0.9)):
        pine((x, y, hgt(x, y) - 0.05), h, int(x * 13 + y * 7), snow=True)
    # kızak
    SLED = m_wood('#b98a5a', 'sled', paint='#e8463c'); I = m_metal()
    plank('sledtop', (0.55, -1.45, 0.16), (0.3, 0.6, 0.04), SLED, rot=(0, 0, 18), seed=8)
    for sx in (-1, 1):
        a = math.radians(18); ox, oy = math.cos(a) * sx * 0.12, math.sin(a) * sx * 0.12
        tube('runner', [(0.55 + ox + 0.1 * math.sin(a), -1.45 + oy - 0.3 * math.cos(a), 0.03), (0.55 + ox, -1.45 + oy, 0.03), (0.55 + ox - 0.12 * math.sin(a), -1.45 + oy + 0.38 * math.cos(a), 0.14)], [0.015] * 3, I, res=4)
    for k in range(5):
        o = blob('mound', (R.uniform(-1.4, 1.4), R.uniform(-1.6, -1.0), 0.0), (R.uniform(0.15, 0.3), R.uniform(0.15, 0.3), 0.08), SN, sub=1, seg=12)
    return 'kayak'

def m_fiber_rope():
    return m_leaf('#a8865a', '#c9a874', '#e2c99a', '#efdcb4', 'ropefray')

def frays(pts, count, seed, length=0.05):
    """Halattan dışarı taşan lif uçları (kısa, açık renkli iki yüzlü şeritler)."""
    R = random.Random(seed)
    def build(bm):
        out = []
        for k in range(count):
            p = V(R.choice(pts)); a = R.uniform(0, 6.28)
            d = V((math.cos(a), math.sin(a), R.uniform(-0.6, 0.6))).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, p, d, side, R.uniform(length * 0.5, length), 0.006, 0.2, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('fray', build, [m_fiber_rope()])

def strand_rope(pts, thick, m, twist=7.0, name='rope', res=2):
    """Gerçek halat: merkez çizgi etrafında birbirine sarılmış üç kol (çok sarmal). pts: kaba çizgi; kendi içinde sıklaştırılır."""
    P = [V(p) for p in pts]
    dense = []
    for i in range(len(P) - 1):
        L = (P[i + 1] - P[i]).length; nseg = max(2, int(L / (thick * 1.8)))
        for k in range(nseg): dense.append(P[i].lerp(P[i + 1], k / nseg))
    dense.append(P[-1])
    # yumuşat (köşeleri yuvarla)
    for _ in range(2):
        dense = [dense[0]] + [(dense[i - 1] + dense[i] * 2 + dense[i + 1]) / 4 for i in range(1, len(dense) - 1)] + [dense[-1]]
    total = 0.0; acc = [0.0]
    for i in range(1, len(dense)): total += (dense[i] - dense[i - 1]).length; acc.append(total)
    up = V((0, 0, 1))
    objs = []
    for sidx in range(3):
        sp = []
        for i, c in enumerate(dense):
            t = (dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]).normalized()
            nx = t.cross(up); nx = nx.normalized() if nx.length > 1e-4 else t.cross(V((1, 0, 0))).normalized()
            ny = t.cross(nx).normalized()
            a = acc[i] / thick * (2 * math.pi / twist) * 2.2 + sidx * 2 * math.pi / 3
            sp.append(tuple(c + (nx * math.cos(a) + ny * math.sin(a)) * thick * 0.42))
        o = tube(name, sp, [thick * 0.6] * len(sp), m, res=1); o.data.bevel_resolution = 1; objs.append(o)
    frays([tuple(p) for p in dense], max(2, len(dense) // 6), int(total * 100))
    return objs

def lush(center, radius, clumps, seed, h=(0.2, 0.36), bright=True):
    """Canlı ot öbekleri: her öbekte 12-18 yaprak (iki ton: koyu dip + açık uç), farklı boy ve kıvrım, araya geniş yapraklı
    yabani ot ve yonca. mesh_from_blades yüzeyi döner."""
    R = random.Random(seed)
    G1 = m_leaf('#2b7a2c', '#4fb341', '#a8df5c', '#cdeea0', 'lushA')
    G2 = m_leaf('#3a8a30', '#6cc24a', '#c4e872', '#e2f5b0', 'lushB')
    CL = m_leaf('#2f8a3a', '#5cbf4f', '#97d86b', '#bfe98e', 'clover')
    def build(bm):
        out = []
        for k in range(clumps):
            a = R.uniform(0, 6.28); rr = R.uniform(0, radius)
            base = V(center) + V((math.cos(a) * rr, math.sin(a) * rr, 0))
            for j in range(R.randint(12, 18)):
                b_ = R.uniform(0, 6.28); up = R.uniform(0.62, 0.98)
                d = V((math.cos(b_) * (1 - up) * 1.3, math.sin(b_) * (1 - up) * 1.3, up)).normalized()
                side = V((-math.sin(b_), math.cos(b_), 0))
                off = V((math.cos(b_), math.sin(b_), 0)) * R.uniform(0, 0.04)
                for f in blade(bm, base + off, d, side, R.uniform(*h) * (0.6 + 0.4 * up), R.uniform(0.022, 0.034), R.uniform(0.2, 0.7), segs=3):
                    out.append((f, j % 2))
            if R.random() < 0.6:                      # yonca / yabani ot: 3-5 yuvarlak yaprak
                c = base + V((R.uniform(-0.06, 0.06), R.uniform(-0.06, 0.06), 0))
                for q in range(R.randint(3, 5)):
                    b_ = q * 2 * math.pi / 4 + R.uniform(0, 0.5)
                    d = V((math.cos(b_), math.sin(b_), 0.35)).normalized(); side = V((-math.sin(b_), math.cos(b_), 0))
                    for f in blade(bm, c + V((0, 0, 0.03)), d, side, 0.06, 0.035, 0.1, segs=3, lift=0.1): out.append((f, 2))
        return out
    return mesh_from_blades('lush', build, [G1, G2, CL])

def base_ring(cx, cy, r, seed, flowers=2, stone=None):
    """Direk/ayak dibi süsü (fenerin dibindeki gibi): çakıl halkası + canlı ot + çiçek."""
    R = random.Random(seed); STN = stone or m_rock()
    n = 5
    for k in range(n):
        a = k * 2 * math.pi / n + R.uniform(-0.3, 0.3)
        pebble((cx + math.cos(a) * r, cy + math.sin(a) * r, 0.03), R.uniform(0.06, 0.09), STN, seed * 7 + k)
    lush((cx, cy, 0), r * 0.9, 2, seed + 3, h=(0.18, 0.32))
    if flowers:
        flower_heads([(cx + math.cos(a) * r * 1.1, cy + math.sin(a) * r * 1.1, R.uniform(0.16, 0.26)) for a in [R.uniform(0, 6.28) for _ in range(flowers)]], R)

def dirt_patch(cx, cy, rx, ry, seed, name='wornground', sand=False):
    """Yıpranmış zemin: yere yapışık düzensiz toprak/kum lekesi (kenarı yırtık), üstünde kırıntı çakıllar."""
    R = random.Random(seed)
    M = m_dirt() if not sand else A.m_flat('#d8bb84', 0.25, 20, 'wornsand')
    bm = bmesh.new(); c0 = bm.verts.new((cx, cy, 0.006)); ring = []
    N = 36
    for i in range(N):
        a = i / N * 2 * math.pi; k = 1 + 0.22 * mnoise.noise(V((math.cos(a) * 1.7, math.sin(a) * 1.7, seed))) + 0.08 * mnoise.noise(V((math.cos(a) * 5, math.sin(a) * 5, seed + 3)))
        ring.append(bm.verts.new((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k, 0.006)))
    for i in range(N): bm.faces.new((c0, ring[i], ring[(i + 1) % N]))
    o = link_mesh(name, bm, [M])
    STN = m_rock()
    for k in range(6):
        a = R.uniform(0, 6.28); r = R.uniform(0.3, 0.95)
        pebble((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r, 0.015), R.uniform(0.025, 0.045), STN, seed + k)
    return o

def nail(p, nrm, m=None, streak=True):
    """Çivi başı (yassı yuvarlak) + altında pas akıntısı izi (ince, aşağı uzanan koyu-turuncu leke)."""
    I = m or m_metal('#5a5560', name='nailm')
    q = V(nrm).to_track_quat('Z', 'Y').to_euler()
    o = blob('nail', tuple(V(p) + V(nrm) * 0.004), (0.014, 0.014, 0.006), I, sub=0, seg=8); o.rotation_euler = q
    if streak and abs(V(nrm).z) < 0.5:
        RS = A.m_flat('#8a4a28', 0.3, 30, 'ruststreak')
        s = blob('streak', tuple(V(p) + V(nrm) * 0.002 - V((0, 0, 0.035))), (0.008, 0.002, 0.03), RS, sub=0, seg=8)
        s.rotation_euler = (0, 0, math.atan2(nrm[1], nrm[0]) + math.pi / 2)
    return o

def dent(o, n=3, depth=0.012, seed=0):
    """Ezik/kırık: parçanın birkaç noktasında yüzeyi içeri bastır (köşe kırığı, darbe izi)."""
    bpy.context.view_layer.update()
    R = random.Random(seed); me = o.data
    if len(me.vertices) < 20: return o
    for _ in range(n):
        c = me.vertices[R.randrange(len(me.vertices))].co.copy(); rad = R.uniform(0.03, 0.06)
        for v in me.vertices:
            d = (v.co - c).length
            if d < rad: v.co -= v.normal * depth * (1 - d / rad) ** 2
    return o

def m_fruit(kind):
    """Gerçekçi meyve/sebze dokuları: portakal (gözenekli kabuk, sap tarafı yeşilimsi, ezik leke), elma (yanaklı kırmızı-sarı
    geçiş, benek), hindistan cevizi (lifli), muz (sarı + kahve benek, uçlar koyu), domates, havuç (halka çizgili)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        if kind == 'orange':
            col = G.mix(G.rng(G.noise(o, 3, 3), 0.3, 0.7), '#e9801f', '#f8a73a')
            col = G.mix(G.rng(G.vor(o, 90), 0.0, 0.18, 0.25, 0), col, '#b85f12')
            col = G.mix(G.rng(G.noise(o, 5, 6), 0.68, 0.75, 0, 0.6), col, '#8a5a2a')
        elif kind == 'apple':
            col = G.mix(G.rng(G.noise(o, 1.2, 2), 0.35, 0.65), '#d63a2c', '#f2b43c')
            col = G.mix(G.rng(G.vor(o, 60), 0.0, 0.08, 0.5, 0), col, '#fff0b0')
            col = G.mix(G.rng(G.noise(o, 6, 6), 0.7, 0.76, 0, 0.5), col, '#7a3a20')
        elif kind == 'coconut':
            col = G.mix(G.rng(G.noise(G.mapping(o, (3, 3, 30)), 1.5, 6), 0.3, 0.7), '#5c3d1d', '#a07a45')
            col = G.mix(G.rng(G.noise(o, 18, 4), 0.6, 0.7, 0, 0.5), col, '#d1b17a')
        elif kind == 'banana':
            col = G.mix(G.rng(G.noise(o, 2, 3), 0.3, 0.7), '#e9c43a', '#f7de6a')
            col = G.mix(G.rng(G.vor(o, 40), 0.0, 0.1, 0.8, 0), col, '#6a4a22')
        elif kind == 'tomato':
            col = G.mix(G.rng(G.noise(o, 2, 3), 0.3, 0.7), '#c8281f', '#f0503a')
            col = G.mix(G.rng(G.noise(o, 7, 6), 0.7, 0.78, 0, 0.4), col, '#f2a04a')
        elif kind == 'carrot':
            sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
            rings = G.math('SINE', G.math('MULTIPLY', sp.outputs['Z'], 160.0))
            col = G.mix(G.rng(rings, 0.75, 1.0, 0, 0.45), '#f07a2a', '#a8471a')
        elif kind == 'melon':
            sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
            ang = G.math('ARCTAN2', sp.outputs['Y'], sp.outputs['X'])
            stripe = G.math('SINE', G.math('ADD', G.math('MULTIPLY', ang, 9.0), G.math('MULTIPLY', G.noise(o, 6), 3.0)))
            col = G.mix(G.rng(stripe, 0.0, 0.5), '#2f7d2e', '#1d4f1e')
            col = G.mix(G.rng(G.noise(o, 12, 4), 0.55, 0.7, 0, 0.3), col, '#8fc76a')
        else:
            col = G.mix(0.5, '#ffffff', '#ffffff')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat('fruit_' + kind, b)

def fruit(kind, loc, r, seed=0, rot=(0, 0, 0)):
    """Tek meyve/sebze: biçim + doku + sap/yaprak (meyveye göre)."""
    R = random.Random(seed); x, y, z = loc
    M = m_fruit(kind)
    STEM = A.m_flat('#5a3a1e', 0.2, 6, 'stemb'); LF = m_leaf('#2f7d35', '#4fb041', '#8fd06a', '#b5e28a', 'fruitleaf')
    if kind in ('orange', 'tomato', 'apple'):
        sq = (1.0, 1.0, 0.88 if kind != 'apple' else 0.92)
        o = blob(kind, loc, (r * sq[0], r * sq[1], r * sq[2]), M, sub=1, seg=14)
        wobble(o, r * 0.05, 6.0, seed)
        tube('stem', [(x, y, z + r * 0.8), (x + 0.005, y, z + r * 1.1)], [r * 0.08, r * 0.06], STEM, res=2)
        if R.random() < 0.6 or kind == 'tomato':
            def lv(bm):
                out = []
                for k in range(5 if kind == 'tomato' else 1):
                    a = k * 1.256 + R.uniform(0, 0.4); d = V((math.cos(a), math.sin(a), 0.3 if kind != 'tomato' else -0.2)).normalized()
                    side = V((-math.sin(a), math.cos(a), 0))
                    for f in blade(bm, V((x, y, z + r * 0.92)), d, side, r * (0.9 if kind != 'tomato' else 0.55), r * 0.3, 0.3, segs=3): out.append((f, 0))
                return out
            mesh_from_blades('fleaf', lv, [LF])
    elif kind == 'coconut':
        o = blob(kind, loc, (r, r, r * 1.08), M, sub=1, seg=14); wobble(o, r * 0.06, 5.0, seed)
        for k in range(3):
            a = k * 2.09
            blob('eye', (x + math.cos(a) * r * 0.22, y + math.sin(a) * r * 0.22, z + r * 1.03), (r * 0.09, r * 0.09, r * 0.04), STEM, sub=0, seg=8)
    elif kind == 'melon':
        o = blob(kind, loc, (r * 1.25, r, r * 0.95), M, sub=1, seg=16); wobble(o, r * 0.04, 4.0, seed)
    elif kind == 'carrot':
        o = tube('carrot', [(x, y, z), (x + r * 0.4, y, z + r * 1.2), (x + r * 0.9, y, z + r * 2.6)], [r * 0.45, r * 0.32, r * 0.05], M, res=4)
    return o

def banana_bunch(loc, n, seed=0, yaw=0.0):
    """Muz salkımı: ortak sap + kavisli, köşeli (5 kenar), uçları koyu muzlar."""
    R = random.Random(seed); M = m_fruit('banana'); TIP = A.m_flat('#4a3418', 0.2, 6, 'bantip')
    x, y, z = loc; a0 = math.radians(yaw)
    tube('bstem', [(x, y, z), (x, y, z + 0.05)], [0.018, 0.015], A.m_flat('#7d8a3a', 0.2, 6, 'bstemm'), res=2)
    for k in range(n):
        a = a0 + (k - (n - 1) / 2) * 0.28
        d = V((math.cos(a), math.sin(a), 0))
        pts = [tuple(V(loc) + d * 0.02), tuple(V(loc) + d * 0.1 + V((0, 0, -0.03))), tuple(V(loc) + d * 0.2 + V((0, 0, 0.02))), tuple(V(loc) + d * 0.26 + V((0, 0, 0.08)))]
        o = tube('banana', pts, [0.012, 0.026, 0.024, 0.008], M, res=5); o.data.bevel_resolution = 1
        blob('btip', pts[-1], (0.01, 0.01, 0.012), TIP, sub=0, seg=6)

def board_shape(L, H, seed, arrow=True):
    """Doğal, kesik olmayan tahta biçimi: kenarlar hafif dalgalı, köşeler yuvarlatılmış, ok ucu yumuşak; bir köşede kırık."""
    R = random.Random(seed); pts = []
    def jit(v): return v + R.uniform(-0.008, 0.008)
    n = 10
    for i in range(n + 1):                                     # alt kenar
        pts.append((-0.06 + (L - 0.2) * i / n, jit(-H / 2)))
    if arrow:
        for k in range(1, 6):                                  # ok ucu: yay
            t = k / 6; a = -math.pi / 2 + t * math.pi
            pts.append((L - 0.14 + 0.14 * math.cos(a) * (1 - 0.1 * abs(math.sin(a))) , H / 2 * math.sin(a) * 1.0))
    for i in range(n + 1):                                     # üst kenar
        pts.append((L - 0.2 - 0.06 - (L - 0.2) * i / n + 0.06 - 0.06, jit(H / 2)))
    # sol uç: kırık köşe (çentik)
    pts.append((-0.075, H * 0.25)); pts.append((-0.05, H * 0.05)); pts.append((-0.075, -H * 0.3))
    return pts

def oar(handle, blade_end, paint, seed=0):
    """Kürek: ince sap (elle yontulmuş, hafif yamuk), ucunda tutma topuzu, ortada halat sargı (ıskarmoz yeri),
    geniş-yassı, uca doğru incelen pala; palanın ucu boyalı ve dökülmüş, kenarı ezik."""
    WD = m_wood('#c48a57', 'oarw', age=1.2); PW = m_wood('#c48a57', 'oarp' + paint, paint=paint, age=1.4)
    h = V(handle); e = V(blade_end); d = (e - h).normalized(); Lt = (e - h).length
    mid = h.lerp(e, 0.62)
    tube('oarshaft', [tuple(h), tuple(h.lerp(e, 0.3) + V((0, 0, 0.005))), tuple(mid)], [0.02, 0.022, 0.024], WD, res=4)
    blob('grip', tuple(h - d * 0.03), (0.03, 0.03, 0.03), WD, sub=1, seg=10)
    # sargı: sapın etrafında kısa sarmal
    up = V((0, 0, 1)); nx = d.cross(up).normalized(); ny = d.cross(nx).normalized()
    c0 = h.lerp(e, 0.45); pts = []
    for i in range(30):
        t = i / 29; a = t * 5 * 2 * math.pi
        pts.append(tuple(c0 + d * (t * 0.1) + (nx * math.cos(a) + ny * math.sin(a)) * 0.026))
    tube('oarwrap', pts, [0.009] * len(pts), m_rope('#c9a46e', 'oarrope'), res=2)
    # pala: yassı, damla biçimli
    bL = Lt * 0.38
    bm_ = bmesh.new(); uvl = bm_.loops.layers.uv.new('grain')
    prof = []
    for i in range(9):
        t = i / 8; w = 0.035 + 0.075 * math.sin(min(1.0, t * 1.3) * math.pi / 2) * (1 - 0.15 * t)
        prof.append((t, w))
    top = []; bot = []
    for (t, w) in prof:
        c = mid + d * (t * bL)
        for sgn, arr in ((1, top), (-1, bot)):
            row = [bm_.verts.new(c + nx * (w * j / 2) + ny * (sgn * 0.012 * (1 - abs(j) / 2.2))) for j in (-2, -1, 0, 1, 2)]
            arr.append(row)
    for i in range(len(prof) - 1):
        for j in range(4):
            bm_.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm_.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
        for j in (0, 4):
            q = (top[i][j], bot[i][j], bot[i + 1][j], top[i + 1][j])
            bm_.faces.new(q if j == 0 else tuple(reversed(q)))
    bm_.faces.new(tuple(top[-1]) + tuple(reversed(bot[-1])))
    bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces)
    for f in bm_.faces:
        for lp in f.loops:
            rel = lp.vert.co - mid; lp[uvl].uv = (rel.dot(d), rel.dot(nx))
    o = link_mesh('oarblade', bm_, [PW]); smooth(o)
    sm = o.modifiers.new('sub', 'SUBSURF'); sm.levels = 1
    return o

def seaweed(cx, cy, seed, n=6):
    """Kıyıya vurmuş yosun/deniz otu: kuma serilmiş dalgalı koyu yeşil-kahve şeritler."""
    R = random.Random(seed)
    SW = m_leaf('#2f4a22', '#4d6a2a', '#7a8a3a', '#9aa04a', 'seaweed')
    def build(bm):
        out = []
        for k in range(n):
            a = R.uniform(0, 6.28); base = V((cx + R.uniform(-0.08, 0.08), cy + R.uniform(-0.08, 0.08), 0.008))
            d = V((math.cos(a), math.sin(a), 0.02)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, base, d, side, R.uniform(0.18, 0.32), 0.035, -0.02, segs=5): out.append((f, 0))
        return out
    mesh_from_blades('seaweed', build, [SW])

BUILDERS = {
    'c_fence': (c_fence, 512, None), 'c_lantern': (c_lantern, 512, None), 'c_sign': (c_sign, 512, None),
    'c_crates': (c_crates, 1024, None), 'c_boat': (c_boat, 1024, None),
    'c_shop': (c_shop, 1024, None), 'c_pier': (c_pier, 1024, None), 'c_lighthouse': (c_lighthouse, 1024, None), 'c_board': (c_board, 1024, None),
    'c_garden': (c_garden, 1024, None), 'c_surf': (c_surf, 1024, None), 'c_swim': (c_swim, 1024, None), 'c_game_hut': (c_game_hut, 1024, None),
    'c_festival': (c_festival, 1024, None), 'c_cave': (c_cave, 1024, 0.5), 'c_mountain': (c_mountain, 1024, 0.5), 'c_ski': (c_ski, 1024, None),
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
