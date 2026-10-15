# Ada varlıkları v3 — doğal yüzey (kullanıcı yorumları 15 Ekim 2026): düz renk yerine pişirilmiş doku (renk + AO),
# organik ve hafif yamuk biçimler, geçişli gölgeler; masal havası korunur (canlı, yumuşak, sevimli).
# Kullanım: python -I assets_v3.py -- <çıktı_klasörü> [c_palm c_rock ...]
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from kit import _finish
import kit
import mathutils
from mathutils import Vector as V, noise as mnoise

def smooth(o, on=True):
    for p in o.data.polygons: p.use_smooth = on

def link_mesh(name, bm, mats):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for m in mats: o.data.materials.append(m)
    return o

def set_grain(o, uvs):
    """bmesh dışında: 'grain' katmanına döngü başına verilen uv'leri yaz (uvs: köşe indeksi → (u, v))."""
    me = o.data
    lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices: lay.data[li].uv = uvs[me.loops[li].vertex_index]

# ------------------------------------------------------------------ malzemeler

def m_bark():
    """Palmiye kabuğu: halka diplerinde koyu gölge, ortası açık; boyuna lifler; hafif yeşilimsi-gri yaşlanma lekeleri."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        # halka fazı: v (boy) * halka sayısı → 0..1 testere
        mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2.9; l.new(sep.outputs['Y'], mul.inputs[0])
        fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(mul.outputs[0], fr.inputs[0])
        rp = ramp(nt, [(0.0, '#5b3a22'), (0.18, '#8c5f38'), (0.55, '#b8875a'), (0.92, '#c99a69'), (1.0, '#6b4528')])
        l.new(fr.outputs[0], rp.inputs['Fac'])
        # lifler: boyuna uzatılmış gürültü
        mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (14, 1.2, 1); l.new(uv.outputs[0], mp.inputs['Vector'])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6; l.new(mp.outputs[0], nz.inputs['Vector'])
        fib = n.new('ShaderNodeMix'); fib.data_type = 'RGBA'; fib.blend_type = 'MULTIPLY'; fib.inputs['Factor'].default_value = 0.45
        l.new(rp.outputs[0], fib.inputs[6]); l.new(nz.outputs['Color'], fib.inputs[7])
        # yaşlanma lekeleri
        nz2 = n.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 1.6; l.new(uv.outputs[0], nz2.inputs['Vector'])
        r2 = ramp(nt, [(0.45, '#000000'), (0.7, '#ffffff')]); l.new(nz2.outputs['Fac'], r2.inputs['Fac'])
        age = n.new('ShaderNodeMix'); age.data_type = 'RGBA'; age.inputs[7].default_value = srgb('#8f8a6e')
        l.new(r2.outputs[0], age.inputs['Factor']); l.new(fib.outputs[2], age.inputs[6])
        fa = n.new('ShaderNodeMath'); fa.operation = 'MULTIPLY'; fa.inputs[1].default_value = 0.35
        l.new(r2.outputs[0], fa.inputs[0]); l.new(fa.outputs[0], age.inputs['Factor'])
        l.new(age.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat('bark', b)

def m_leaf(base='#3f9a3a', mid='#6cc24a', tip='#b5e26a', vein='#d8f08a', name='leaf'):
    """Yaprak: dipten uca koyu→açık geçiş, ortada açık damar, yanlara ince yan damarlar, hafif renk dalgalanması.
    grain uv: u = uzunluk boyunca 0..1, v = enine -1..1."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        rp = ramp(nt, [(0.0, base), (0.45, mid), (1.0, tip)]); l.new(sep.outputs['X'], rp.inputs['Fac'])
        # orta damar: |v| küçükse açık
        ab = n.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; l.new(sep.outputs['Y'], ab.inputs[0])
        vm = n.new('ShaderNodeMapRange'); vm.inputs['From Min'].default_value = 0.05; vm.inputs['From Max'].default_value = 0.16
        vm.inputs['To Min'].default_value = 1; vm.inputs['To Max'].default_value = 0; l.new(ab.outputs[0], vm.inputs['Value'])
        mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs[7].default_value = srgb(vein)
        l.new(vm.outputs[0], mix.inputs['Factor']); l.new(rp.outputs[0], mix.inputs[6])
        # yan damarlar: u + |v| boyunca dalga
        add = n.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 0.6
        l.new(ab.outputs[0], add.inputs[0]); l.new(sep.outputs['X'], add.inputs[2])
        wv = n.new('ShaderNodeMath'); wv.operation = 'SINE'
        sc_ = n.new('ShaderNodeMath'); sc_.operation = 'MULTIPLY'; sc_.inputs[1].default_value = 55.0
        l.new(add.outputs[0], sc_.inputs[0]); l.new(sc_.outputs[0], wv.inputs[0])
        sv = n.new('ShaderNodeMapRange'); sv.inputs['From Min'].default_value = 0.75; sv.inputs['From Max'].default_value = 1.0
        sv.inputs['To Min'].default_value = 0; sv.inputs['To Max'].default_value = 0.22; l.new(wv.outputs[0], sv.inputs['Value'])
        mix2 = n.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.inputs[7].default_value = srgb(vein)
        l.new(sv.outputs[0], mix2.inputs['Factor']); l.new(mix.outputs[2], mix2.inputs[6])
        # renk dalgalanması
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6
        tc = n.new('ShaderNodeTexCoord'); l.new(tc.outputs['Object'], nz.inputs['Vector'])
        mx3 = n.new('ShaderNodeMix'); mx3.data_type = 'RGBA'; mx3.blend_type = 'OVERLAY'; mx3.inputs['Factor'].default_value = 0.25
        l.new(mix2.outputs[2], mx3.inputs[6]); l.new(nz.outputs['Color'], mx3.inputs[7])
        l.new(mx3.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_rock():
    """Kaya: sıcak/serin gri dalgalanma, koyu benekler ve ince çatlaklar; üstte gürültüyle bozulmuş yumuşak yosun geçişi
    (yosunun kendisi iki yeşil + sarımsı uç tonlarıyla dokulu)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 6
        l.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.3, '#77737f'), (0.5, '#8e8994'), (0.72, '#aaa297')]); l.new(nz.outputs['Fac'], rp.inputs['Fac'])
        # benek
        vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 14; l.new(tc.outputs['Object'], vo.inputs['Vector'])
        sp = n.new('ShaderNodeMapRange'); sp.inputs['From Min'].default_value = 0.0; sp.inputs['From Max'].default_value = 0.12
        sp.inputs['To Min'].default_value = 0.35; sp.inputs['To Max'].default_value = 0; l.new(vo.outputs['Distance'], sp.inputs['Value'])
        sm = n.new('ShaderNodeMix'); sm.data_type = 'RGBA'; sm.inputs[7].default_value = srgb('#5f5b66')
        l.new(sp.outputs[0], sm.inputs['Factor']); l.new(rp.outputs[0], sm.inputs[6])
        # çatlak: voronoi kenarı
        # çatlak: gürültüyle bükülmüş voronoi kenarı, ince ve yer yer kaybolan (düzenli kabuk deseni olmasın)
        wn = n.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 1.5; l.new(tc.outputs['Object'], wn.inputs['Vector'])
        wm = n.new('ShaderNodeVectorMath'); wm.operation = 'MULTIPLY_ADD'; wm.inputs[1].default_value = (0.6, 0.6, 0.6)
        l.new(wn.outputs['Color'], wm.inputs[0]); l.new(tc.outputs['Object'], wm.inputs[2])
        vo2 = n.new('ShaderNodeTexVoronoi'); vo2.feature = 'DISTANCE_TO_EDGE'; vo2.inputs['Scale'].default_value = 2.2
        l.new(wm.outputs[0], vo2.inputs['Vector'])
        cr = n.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.0; cr.inputs['From Max'].default_value = 0.018
        cr.inputs['To Min'].default_value = 0.45; cr.inputs['To Max'].default_value = 0; l.new(vo2.outputs['Distance'], cr.inputs['Value'])
        gate = n.new('ShaderNodeTexNoise'); gate.inputs['Scale'].default_value = 2.5; l.new(tc.outputs['Object'], gate.inputs['Vector'])
        gr = n.new('ShaderNodeMapRange'); gr.inputs['From Min'].default_value = 0.45; gr.inputs['From Max'].default_value = 0.6
        l.new(gate.outputs['Fac'], gr.inputs['Value'])
        crm = n.new('ShaderNodeMath'); crm.operation = 'MULTIPLY'; l.new(cr.outputs[0], crm.inputs[0]); l.new(gr.outputs[0], crm.inputs[1])
        cr = crm
        cm = n.new('ShaderNodeMix'); cm.data_type = 'RGBA'; cm.inputs[7].default_value = srgb('#4d4954')
        l.new(cr.outputs[0], cm.inputs['Factor']); l.new(sm.outputs[2], cm.inputs[6])
        # yosun maskesi: yukarı bakan + gürültü, yumuşak
        geo = n.new('ShaderNodeNewGeometry'); sxyz = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Normal'], sxyz.inputs[0])
        nz3 = n.new('ShaderNodeTexNoise'); nz3.inputs['Scale'].default_value = 3.5; nz3.inputs['Detail'].default_value = 4
        l.new(tc.outputs['Object'], nz3.inputs['Vector'])
        addm = n.new('ShaderNodeMath'); addm.operation = 'MULTIPLY_ADD'; addm.inputs[1].default_value = 0.7
        l.new(nz3.outputs['Fac'], addm.inputs[0]); l.new(sxyz.outputs['Z'], addm.inputs[2])
        mk = n.new('ShaderNodeMapRange'); mk.interpolation_type = 'SMOOTHSTEP'
        mk.inputs['From Min'].default_value = 1.05; mk.inputs['From Max'].default_value = 1.3; l.new(addm.outputs[0], mk.inputs['Value'])
        nz4 = n.new('ShaderNodeTexNoise'); nz4.inputs['Scale'].default_value = 28; nz4.inputs['Detail'].default_value = 3
        l.new(tc.outputs['Object'], nz4.inputs['Vector'])
        moss = ramp(nt, [(0.3, '#4f7f2e'), (0.55, '#6f9c3a'), (0.8, '#a8c45a')]); l.new(nz4.outputs['Fac'], moss.inputs['Fac'])
        mm = n.new('ShaderNodeMix'); mm.data_type = 'RGBA'
        l.new(mk.outputs[0], mm.inputs['Factor']); l.new(cm.outputs[2], mm.inputs[6]); l.new(moss.outputs[0], mm.inputs[7])
        l.new(mm.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat('rock', b)

def m_flat(hexc, var=0.12, scale=8, name=None):
    """Düz renk + hafif gürültü dalgalanması (ot, çakıl, hindistan cevizi…)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale
        l.new(tc.outputs['Object'], nz.inputs['Vector'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'OVERLAY'; mx.inputs['Factor'].default_value = var
        mx.inputs[6].default_value = srgb(hexc); l.new(nz.outputs['Color'], mx.inputs[7])
        l.new(mx.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name or ('flat' + hexc), b)

def _shade(hexc, k):
    import colorsys
    h = hexc.lstrip('#'); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b); ll = max(0, min(1, ll * k))
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))

def m_wood(hexc, name=None, paint=None):
    """Ahşap: tahta boyunca (grain u) dalgalı yıllık halka bantları + ince lifler + düğüm lekeleri; paint verilirse üstünde
    aşınmış boya (kenarlara doğru ahşap görünür)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt)
        mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 7.0, 1.0); l.new(uv.outputs[0], mp.inputs['Vector'])
        wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
        wv.inputs['Scale'].default_value = 1.6; wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 3
        l.new(mp.outputs[0], wv.inputs['Vector'])
        rp = ramp(nt, [(0.0, _shade(hexc, 0.72)), (0.5, hexc), (1.0, _shade(hexc, 1.18))]); l.new(wv.outputs['Fac'], rp.inputs['Fac'])
        mp2 = n.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (2.0, 40.0, 1.0); l.new(uv.outputs[0], mp2.inputs['Vector'])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 5; l.new(mp2.outputs[0], nz.inputs['Vector'])
        fib = n.new('ShaderNodeMix'); fib.data_type = 'RGBA'; fib.blend_type = 'OVERLAY'; fib.inputs['Factor'].default_value = 0.35
        l.new(rp.outputs[0], fib.inputs[6]); l.new(nz.outputs['Color'], fib.inputs[7])
        vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 1.3; l.new(uv.outputs[0], vo.inputs['Vector'])
        kn = n.new('ShaderNodeMapRange'); kn.inputs['From Min'].default_value = 0.0; kn.inputs['From Max'].default_value = 0.06
        kn.inputs['To Min'].default_value = 0.6; kn.inputs['To Max'].default_value = 0; l.new(vo.outputs['Distance'], kn.inputs['Value'])
        knm = n.new('ShaderNodeMix'); knm.data_type = 'RGBA'; knm.inputs[7].default_value = srgb(_shade(hexc, 0.55))
        l.new(kn.outputs[0], knm.inputs['Factor']); l.new(fib.outputs[2], knm.inputs[6])
        out = knm.outputs[2]
        if paint:
            pn = n.new('ShaderNodeTexNoise'); pn.inputs['Scale'].default_value = 4.0; pn.inputs['Detail'].default_value = 6
            tcp = n.new('ShaderNodeTexCoord'); l.new(tcp.outputs['Object'], pn.inputs['Vector'])
            wear = n.new('ShaderNodeMapRange'); wear.interpolation_type = 'SMOOTHSTEP'
            wear.inputs['From Min'].default_value = 0.62; wear.inputs['From Max'].default_value = 0.7
            wear.inputs['To Min'].default_value = 1; wear.inputs['To Max'].default_value = 0; l.new(pn.outputs['Fac'], wear.inputs['Value'])
            pc = n.new('ShaderNodeMix'); pc.data_type = 'RGBA'; pc.blend_type = 'MULTIPLY'; pc.inputs['Factor'].default_value = 0.25
            pc.inputs[6].default_value = srgb(paint); l.new(nz.outputs['Color'], pc.inputs[7])
            pm = n.new('ShaderNodeMix'); pm.data_type = 'RGBA'
            l.new(wear.outputs[0], pm.inputs['Factor']); l.new(out, pm.inputs[6]); l.new(pc.outputs[2], pm.inputs[7])
            out = pm.outputs[2]
        l.new(out, bsdf.inputs['Base Color'])
    return nodes_mat(name or ('wood' + hexc + (paint or '')), b)

def m_tile(hexc, name=None):
    """Kiremit: ton dalgalanması, yer yer koyu yıpranma ve açık güneş yanığı, ince benek."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.2; nz.inputs['Detail'].default_value = 4; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.3, _shade(hexc, 0.82)), (0.5, hexc), (0.72, _shade(hexc, 1.14))]); l.new(nz.outputs['Fac'], rp.inputs['Fac'])
        nz2 = n.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 25; l.new(tc.outputs['Object'], nz2.inputs['Vector'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'OVERLAY'; mx.inputs['Factor'].default_value = 0.3
        l.new(rp.outputs[0], mx.inputs[6]); l.new(nz2.outputs['Color'], mx.inputs[7])
        l.new(mx.outputs[2], bsdf.inputs['Base Color'])
    return nodes_mat(name or ('tile' + hexc), b)

def m_dirt(name='dirt'):
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 6; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = ramp(nt, [(0.35, '#9a7048'), (0.55, '#b78a5c'), (0.75, '#cfa776')]); l.new(nz.outputs['Fac'], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

# ------------------------------------------------------------------ ortak parçalar

def blade_strip(bm, base, d, side, length, width, droop, segs=2, u0=0.0, u1=1.0, tilt=0.0):
    """Tek yaprakçık/ot yaprağı (iki yüzlü): dipten uca daralan, sarkan şerit. 'grain' (u boy, v en) ile döner: [(vert,(u,v))]."""
    out = []
    pts = []
    for i in range(segs + 1):
        s = i / segs
        c = base + d * (length * s) + V((0, 0, -droop * length * s * s))
        w = width * (1 - s) ** 0.8 if i < segs else 0.0
        l = c + side * w + V((0, 0, tilt * w)); r = c - side * w + V((0, 0, tilt * w))
        u = u0 + (u1 - u0) * s
        pts.append(((bm.verts.new(l), (u, 1.0)), (bm.verts.new(r), (u, -1.0)), (bm.verts.new(c + V((0, 0, 0.004))), (u, 0.0))))
    faces = []
    for i in range(segs):
        (l0, r0, c0), (l1, r1, c1) = pts[i], pts[i + 1]
        if i < segs - 1:
            faces.append([l0, l1, c1, c0]); faces.append([c0, c1, r1, r0])
        else:
            faces.append([l0, c1, c0]); faces.append([c0, c1, r0])
    for f in faces:
        bm.faces.new([v for v, _ in f]); bm.faces.new([v for v, _ in reversed(f)]) if False else None
        out.append(f)
    return out

def mesh_from_blades(name, build, mats, double=True):
    """build(bm) → yüz listeleri [(vert,(u,v))…]; 'grain' uv'si yazılır; iki yüzlü için ters kopya eklenir."""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('grain'); ds = bm.faces.layers.int.new('ds')
    groups = build(bm)
    for f, mi in groups:
        verts = [v for v, _ in f]
        try: face = bm.faces.new(verts)
        except ValueError: face = None
        if face is not None:
            face.material_index = mi
            for loop, (_, u) in zip(face.loops, f): loop[uv].uv = u
        if double and face is not None: face[ds] = 1   # arka yüz pişirmeden SONRA eklenir (kit.export_baked_fbx)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for m in mats: o.data.materials.append(m)
    smooth(o, True)
    return o

def blade(bm, base, d, side, length, width, droop, segs=3, lift=0.0):
    """Yaprak şeridi köşeleri: [(v,(u,vv))] dörtgen/üçgen listesi (yüzler mesh_from_blades'te kurulur)."""
    rows = []
    for i in range(segs + 1):
        s = i / segs
        c = base + d * (length * s) + V((0, 0, lift * length * s - droop * length * s * s))
        w = width * math.sin(math.pi * min(1.0, 0.15 + s * 0.85)) if i < segs else 0.0
        fold = V((0, 0, -0.35 * w))
        rows.append(((bm.verts.new(c + side * w + fold), (s, 1.0)), (bm.verts.new(c + V((0, 0, 0.006))), (s, 0.0)), (bm.verts.new(c - side * w + fold), (s, -1.0))))
    faces = []
    for i in range(segs):
        (l0, c0, r0), (l1, c1, r1) = rows[i], rows[i + 1]
        if i < segs - 1: faces += [[l0, l1, c1, c0], [c0, c1, r1, r0]]
        else: faces += [[l0, c1, c0], [c0, c1, r0]]
    return faces

def tufts(center, radius, count, seed, mats_idx=(0, 1), h=(0.18, 0.32)):
    """Ot öbekleri (çim yaprakları) — mesh_from_blades için yüz grubu üretici."""
    R = random.Random(seed)
    def build(bm):
        out = []
        for k in range(count):
            a = R.uniform(0, 6.28); rr = R.uniform(radius * 0.4, radius)
            base = V(center) + V((math.cos(a) * rr, math.sin(a) * rr, 0))
            for j in range(R.randint(6, 9)):
                b = R.uniform(0, 6.28); up = R.uniform(0.75, 1.0)
                d = V((math.cos(b) * (1 - up) * 1.2, math.sin(b) * (1 - up) * 1.2, up)).normalized()
                side = V((-math.sin(b), math.cos(b), 0))
                for f in blade(bm, base, d, side, R.uniform(*h), 0.028, R.uniform(0.15, 0.45), segs=3):
                    out.append((f, mats_idx[(k + j) % len(mats_idx)]))
        return out
    return build

def rosette(centers, R, sizes=(0.3, 0.45), leaves=9):
    """Geniş yapraklı alçak çalı/fide öbekleri (her merkezde yukarı-dışa açılan, uca doğru kıvrılan yapraklar)."""
    def build(bm):
        out = []
        for (cx, cy) in centers:
            for k in range(leaves):
                a = k * 2 * math.pi / leaves + R.uniform(-0.2, 0.2)
                up = R.uniform(0.35, 0.75)
                d = V((math.cos(a) * (1 - up * 0.6), math.sin(a) * (1 - up * 0.6), up)).normalized()
                side = V((-math.sin(a), math.cos(a), 0))
                for f in blade(bm, V((cx, cy, 0.02)), d, side, R.uniform(*sizes), 0.085, R.uniform(0.6, 1.0), segs=4, lift=0.05):
                    out.append((f, 0))
        return out
    return build

def flower_heads(spots, R, size=1.0):
    """Küçük çiçekler: sap + 5 yuvarlak taç yaprak + göbek (renk renk)."""
    ST = m_flat('#469c3a', 0.15, 6, 'stem'); CY = m_flat('#ffc93a', 0.15, 12, 'fcenter')
    PET = [m_flat('#ff7aa8', 0.12, 9, 'p_pink'), m_flat('#fff6ea', 0.08, 9, 'p_wht'), m_flat('#b78cff', 0.12, 9, 'p_pur'), m_flat('#ffd447', 0.1, 9, 'p_yel')]
    for k, (x, y, h) in enumerate(spots):
        head = V((x, y, h)); base = V((x * 0.9, y * 0.9, 0))
        tube('stem', [tuple(base), tuple((base + head) / 2 + V((0.02, 0, 0))), tuple(head)], [0.014, 0.012, 0.01], ST, res=2)
        pm = PET[k % len(PET)]; sz = R.uniform(0.9, 1.2) * size
        blob('fc', tuple(head + V((0, 0, 0.012))), (0.032 * sz, 0.032 * sz, 0.022 * sz), CY, sub=0, seg=8)
        for j in range(5):
            b = j * 2 * math.pi / 5 + k
            blob('pet', tuple(head + V((math.cos(b) * 0.055 * sz, math.sin(b) * 0.055 * sz, -0.004))), (0.048 * sz, 0.03 * sz, 0.012), pm,
                 rot=(0, 0, math.degrees(b)), sub=0, seg=8)

def pebble(loc, r, m, seed):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=loc)
    o = bpy.context.object; o.scale = (1.2, 1.0, 0.6); bpy.ops.object.transform_apply(scale=True)
    for v in o.data.vertices: v.co += v.co.normalized() * mnoise.noise(v.co * 6 + V((seed, 0, 0))) * r * 0.25
    o.data.materials.append(m); smooth(o)
    return o

# ------------------------------------------------------------------ palmiye

def c_palm():
    R = random.Random(11)
    H = 4.2; lean = 1.45
    def P(t): return V((lean * t ** 2.0 + 0.05 * math.sin(t * 7), 0.15 * math.sin(t * 2.4) + 0.04 * math.sin(t * 9), H * t * (1 - 0.06 * t)))
    def rad(t):
        base = 0.36 - 0.17 * t + 0.14 * max(0, 0.08 - t) / 0.08          # dipte kök genişlemesi
        ph = (t * H * 2.9) % 1.0                                         # halka: üstte şişkin, altta boğum
        return base * (0.9 + 0.13 * ph ** 1.6)
    BARK = m_bark()
    # gövde: halka halka şişkin tüp (uv: u çevre, v boy)
    rings, around = 48, 12
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    grid = []
    for i in range(rings + 1):
        t = i / rings; c = P(t)
        tan = (P(min(1, t + 0.01)) - P(max(0, t - 0.01))).normalized()
        nx = tan.cross(V((0, 1, 0))).normalized(); ny = tan.cross(nx).normalized()
        row = []
        for j in range(around):
            a = j / around * 2 * math.pi
            rr = rad(t) * (1 + 0.05 * mnoise.noise(V((math.cos(a) * 2, math.sin(a) * 2, t * 9))))
            row.append(bm.verts.new(c + (nx * math.cos(a) + ny * math.sin(a)) * rr))
        grid.append(row)
    for i in range(rings):
        for j in range(around):
            j2 = (j + 1) % around
            f = bm.faces.new((grid[i][j], grid[i][j2], grid[i + 1][j2], grid[i + 1][j]))
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                loop[uvl].uv = (jj / around * 1.2, ii / rings * H)
    trunk = link_mesh('trunk', bm, [BARK]); smooth(trunk)
    top = P(1.0)
    # tepe lifleri ("kıllanma"): tacın altında aşağı sarkan ince lif demetleri + halka ağızlarında kısa lifler
    FIB = m_leaf('#5a3a22', '#7a5233', '#a27a4e', '#b48a5a', 'fiber')
    def fibers(bm):
        out = []
        for k in range(30):
            t = R.uniform(0.84, 0.99); c = P(t)
            a = R.uniform(0, 6.28); dirv = V((math.cos(a), math.sin(a), -R.uniform(0.6, 1.4))).normalized()
            side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, c + V((math.cos(a), math.sin(a), 0)) * rad(t) * 0.9, dirv, side, R.uniform(0.15, 0.32), 0.035, 0.1, segs=2):
                out.append((f, 0))
        for k in range(30):
            t = R.uniform(0.12, 0.8); t = round(t * H * 2.9) / (H * 2.9) - 0.004; c = P(t)
            a = R.uniform(0, 6.28); dirv = V((math.cos(a), math.sin(a), -0.6)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in blade(bm, c + V((math.cos(a), math.sin(a), 0)) * rad(t) * 0.95, dirv, side, R.uniform(0.06, 0.11), 0.03, 0.0, segs=1):
                out.append((f, 0))
        return out
    mesh_from_blades('fibers', fibers, [FIB])
    # taç tabanı ve hindistan cevizleri (alttan görünür)
    blob('crown', tuple(top + V((0, 0, 0.02))), (0.32, 0.32, 0.22), m_flat('#6f7f34', 0.2, 10, 'crownm'), sub=0, seg=12)
    NUT = m_flat('#86662f', 0.35, 9, 'nutm'); NUTG = m_flat('#9aa843', 0.3, 9, 'nutg')
    for k in range(6):
        a = k * 1.05 + 0.3; rr = 0.2 + 0.06 * (k % 2)
        blob('nut', tuple(top + V((math.cos(a) * rr, math.sin(a) * rr, -0.24 - 0.07 * (k % 3)))), (0.18, 0.18, 0.2), NUT if k % 3 else NUTG, sub=0, seg=12)
    # yapraklar: orta damar (tüp) + iki yanda sarkan yaprakçıklar
    LEAF = m_leaf('#3f9a3a', '#6cc94c', '#c2e874', '#e2f59a', 'palmleaf')
    RIB = m_flat('#9bd060', 0.15, 6, 'ribm')
    fronds = [(f * 2 * math.pi / 9 + R.uniform(-0.12, 0.12), R.uniform(2.1, 2.5), R.uniform(0.7, 0.85)) for f in range(9)] + \
             [(f * 2 * math.pi / 3 + 0.9, 1.4, 1.3) for f in range(3)]
    def leaflets(bm):
        """Geniş kürek yaprak: 18 boy x 7 en ızgara; V kıvrım, boyuna bükülme, dalgalı kenar, 3 yumuşak çentik."""
        out = []
        for (az, L, rise) in fronds:
            d = V((math.cos(az), math.sin(az), 0)); side0 = V((-d.y, d.x, 0))
            twist = R.uniform(-0.35, 0.35)
            def C(s): return top + d * (L * s) + V((0, 0, rise * L * s - 1.05 * L * s * s))
            NL, NW = 12, 5
            notches = [R.uniform(0.35, 0.5), R.uniform(0.58, 0.7), R.uniform(0.76, 0.88)]
            grid = []
            for i in range(NL + 1):
                s = i / NL
                c = C(s); tan = (C(min(1, s + 0.02)) - C(max(0, s - 0.02))).normalized()
                ang = twist * s
                side = (side0 * math.cos(ang) + V((0, 0, 1)) * math.sin(ang)).normalized()
                up = side.cross(tan).normalized()
                w = 0.55 * (math.sin(math.pi * min(1.0, 0.1 + s * 0.92)) ** 0.75) * (1 - 0.2 * s) * (L / 2.5)
                row = []
                for j in range(NW):
                    v = (j / (NW - 1)) * 2 - 1                      # -1..1
                    cut = 1.0
                    for nc in notches:                                # çentik: kenara yakın, dar bant
                        k = math.exp(-((s - nc) / 0.025) ** 2)
                        if (v > 0) == (nc > 0.6): cut -= 0.45 * k * abs(v)
                    wave = 0.04 * math.sin(s * 40 + v * 3) * abs(v)
                    p = c + side * (v * w * cut) + up * (-0.38 * w * v * v + wave)
                    row.append((bm.verts.new(p), (s, v)))
                grid.append(row)
            for i in range(NL):
                for j in range(NW - 1):
                    out.append(([grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]], 0))
        return out
    mesh_from_blades('leaflets', leaflets, [LEAF])
    for (az, L, rise) in fronds:
        d = V((math.cos(az), math.sin(az), 0))
        pts = [tuple(top + d * (L * s) + V((0, 0, rise * L * s - 1.05 * L * s * s + 0.02))) for s in (0.0, 0.33, 0.66, 1.0)]
        tube('rib', pts, [0.035, 0.028, 0.018, 0.006], RIB, res=2)
    # dip: kök çıkıntıları, ot öbekleri, küçük çalı, çakıl, düşmüş hindistan cevizi
    for k in range(5):
        a = k * 1.26 + 0.4
        tube('root', [(math.cos(a) * 0.18, math.sin(a) * 0.18, 0.18), (math.cos(a) * 0.38, math.sin(a) * 0.38, 0.03)], [0.09, 0.04], BARK, res=2)
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    mesh_from_blades('tufts', tufts((0.0, 0.0, 0.0), 0.85, 7, 3, h=(0.22, 0.38)), [G1])
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    mesh_from_blades('basebush', rosette([(0.45, 0.32), (-0.42, -0.2), (0.1, -0.5)], R, sizes=(0.32, 0.45)), [BL])
    flower_heads([(0.55, 0.15, 0.3), (-0.3, -0.42, 0.26), (0.18, -0.6, 0.22)], R)
    STN = m_rock()
    for k, (x, y, r) in enumerate(((0.55, -0.35, 0.09), (0.7, -0.1, 0.06), (-0.5, 0.45, 0.08))):
        pebble((x, y, r * 0.4), r, STN, k)
    blob('fallen', (-0.55, -0.4, 0.12), (0.16, 0.16, 0.15), NUT, sub=0, seg=12)
    return 'palmiye'

# ------------------------------------------------------------------ kaya

def c_rock():
    STN = m_rock()
    specs = (((0, 0, 0.42), 0.55, (1.05, 0.95, 1.2), 1), ((0.62, -0.34, 0.24), 0.36, (1.05, 1.0, 1.05), 2), ((-0.55, 0.26, 0.2), 0.3, (1.15, 1.0, 0.95), 3))
    for (loc, r, sc, seed) in specs:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r, location=loc)
        o = bpy.context.object; o.scale = sc; bpy.ops.object.transform_apply(scale=True)
        for v in o.data.vertices:
            p = v.co
            d = mnoise.noise(p * (1.4 / r) + V((seed * 3, 0, 0))) * 0.13 + mnoise.noise(p * (4 / r) + V((0, seed, 0))) * 0.04
            v.co = p + p.normalized() * d * r
            if v.co.z < -0.55 * r: v.co.z = -0.55 * r + (v.co.z + 0.55 * r) * 0.1
        o.data.materials.append(STN); smooth(o)
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    mesh_from_blades('tufts', tufts((0.0, 0.0, 0.0), 1.0, 12, 7, h=(0.22, 0.4)), [G1])
    for k, (x, y, r) in enumerate(((0.9, 0.2, 0.08), (-0.2, -0.65, 0.07), (0.25, 0.62, 0.06), (-0.85, -0.2, 0.05))):
        pebble((x, y, r * 0.4), r, STN, k + 5)
    return 'kaya'

def c_bush():
    """Yaprak yaprak çalı: topraktan 5 kümeden dışa-yukarı açılan, uca doğru kıvrılan geniş yapraklar (damarlı, dipten uca
    renk geçişli; iç yapraklar koyu, dış/üst yapraklar açık); arada pembe-beyaz çiçekler. İçi dolu küre yok."""
    R = random.Random(8)
    LA = m_leaf('#3a9a40', '#5fc252', '#b2e478', '#d6f39c', 'bushleaf')
    LB = m_leaf('#33893a', '#52b14a', '#9bd668', '#c6ec8e', 'bushleaf2')
    def build(bm):
        out = []
        centers = [(0, 0, 0.42, 1.0), (0.24, 0.1, 0.32, 0.85), (-0.24, 0.06, 0.3, 0.85), (0.05, 0.24, 0.28, 0.8), (-0.03, -0.22, 0.26, 0.8),
                   (0.36, -0.2, 0.0, 0.8), (-0.38, -0.12, 0.0, 0.8), (0.3, 0.32, 0.0, 0.7), (-0.28, 0.32, 0.0, 0.7)]
        for ci, (cx, cy, cz, sc) in enumerate(centers):
            n = 20
            for k in range(n):
                a = k * 2.39996 + ci                               # altın açı: düzgün dağılım
                layer = k / n
                up = (1.0 - layer * 0.62) if cz < 0.05 else (0.9 - layer * 1.1)   # yerdekiler kubbe tabanı; dal uçlarındakiler her yöne
                d = V((math.cos(a) * (1 - abs(up)), math.sin(a) * (1 - abs(up)), up)).normalized()
                side = V((-math.sin(a), math.cos(a), 0))
                L = sc * (0.36 + 0.16 * layer) * R.uniform(0.85, 1.15)
                base = V((cx, cy, cz + 0.02 + 0.1 * (1 - layer)))
                for f in blade(bm, base, d, side, L, 0.1 * sc + 0.025, R.uniform(0.45, 0.8), segs=4, lift=0.12):
                    out.append((f, 0 if (k + ci) % 3 else 1))
        return out
    mesh_from_blades('bush', build, [LA, LB])
    BR = m_bark()
    for (x, y, z) in ((0, 0, 0.42), (0.24, 0.1, 0.32), (-0.24, 0.06, 0.3), (0.05, 0.24, 0.28), (-0.03, -0.22, 0.26)):   # dallar
        tube('branch', [(x * 0.2, y * 0.2, 0.0), (x * 0.6, y * 0.6, z * 0.55), (x, y, z)], [0.035, 0.025, 0.015], BR, res=2)
    flower_heads([(0.36, 0.2, 0.5), (-0.34, 0.16, 0.46), (0.05, 0.36, 0.55), (0.18, -0.32, 0.44), (-0.22, -0.26, 0.48), (0.02, 0.0, 0.66)], R)
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    mesh_from_blades('tufts', tufts((0.0, 0.0, 0.0), 0.75, 5, 9, h=(0.16, 0.26)), [G1])
    return 'çalı'

def c_flowers():
    """Çiçek öbeği: yaprak rozetleri + farklı boylarda 9 çiçek (yuvarlak taç yapraklar, sarı göbek), arada ot."""
    R = random.Random(21)
    LF = m_leaf('#2f8a3a', '#56b64a', '#a6dc6a', '#cdee92', 'fleaf')
    mesh_from_blades('rosettes', rosette([(0, 0), (0.22, 0.15), (-0.2, 0.12), (0.05, -0.22)], R, sizes=(0.22, 0.34), leaves=8), [LF])
    spots = []
    for k in range(14):
        a = k * 2.4; r = 0.04 + 0.28 * math.sqrt((k + 0.5) / 14)
        spots.append((math.cos(a) * r, math.sin(a) * r, R.uniform(0.18, 0.34) + 0.08 * (1 - r / 0.32)))
    flower_heads(spots, R, size=1.35)
    G1 = m_leaf('#3d8f35', '#5fb446', '#a3d862', '#c8ea86', 'grass')
    mesh_from_blades('tufts', tufts((0.0, 0.0, 0.0), 0.45, 5, 4, h=(0.18, 0.3)), [G1])
    return 'çiçek'

BUILDERS = {'c_palm': (c_palm, 1024, None), 'c_rock': (c_rock, 1024, 0.45), 'c_bush': (c_bush, 1024, None), 'c_flowers': (c_flowers, 512, None)}
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
