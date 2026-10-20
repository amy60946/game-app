# Mağara v4 ön tasarım (kullanıcı geri bildirimi 20 Ekim 2026; onay bekliyor, oyuna girmedi).
# İstekler: ağız köşeli değil eğrisel; içi simsiyah değil, içeri ilerleyen ve gitgide koyulaşan patika (gölge geçişi pişirilir,
# gerçek zamanlı ışık gerekmez); ada zeminiyle bütünleşik (kaya tabanı tümsekli zeminden doğar); girişte daha çok çalı/çiçek;
# damarlı, farklı boylarda yapraklı sarmaşıklar; girişte biriken küçük çakıllar.
# Kullanım: /tmp/claude-0/bpyenv/bin/python -I cave_v4.py -- <çıktı_klasörü>
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import bpy, bmesh
from kit import *
import kit
import assets_v3 as A
from assets_v3 import m_rock, m_leaf, m_dirt, mesh_from_blades, blade, pebble, smooth, link_mesh, flower_heads, rosette
import assets_town as T
from assets_town import rock, lush, m_plaster
from mathutils import Vector as V, noise as mnoise

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp/cave_v4'
os.makedirs(OUT, exist_ok=True)
R = random.Random(7)

MOUTH_W, MOUTH_H, DEPTH = 0.62, 0.78, 2.2      # ağız yarı genişlik, yükseklik, tünel derinliği (m)
MOUTH_Y = -0.8                                  # ağız düzlemi (önü -Y; oyunda adanın merkezine döner)


def shade_by_attr(m, attr='shade'):
    """Malzemenin taban rengini 'shade' köşe rengiyle çarpar (ağızdan içeri koyulaşma pişirmede dokuya geçer)."""
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    link = next((l for l in nt.links if l.to_socket == b.inputs['Base Color']), None)
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = attr
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    if link:
        nt.links.new(link.from_socket, mx.inputs[6]); nt.links.remove(link)
    else:
        mx.inputs[6].default_value = b.inputs['Base Color'].default_value
    nt.links.new(at.outputs['Color'], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    return m


def depth_shade(y, x=0.0, z=0.3):
    """Ağızdan içeri koyulaşma: ağızda 1, ~1,6 m içeride en koyu (tam siyah değil: mor-lacivert 0,12)."""
    t = (y - (MOUTH_Y + 0.15)) / (DEPTH * 0.75)
    t = max(0.0, min(1.0, t))
    t = t * t * (3 - 2 * t)
    return 1.0 - 0.78 * t


def paint_shade(o, fn):
    me = o.data
    if 'shade' not in me.color_attributes: me.color_attributes.new('shade', 'FLOAT_COLOR', 'POINT')
    ca = me.color_attributes['shade']
    mw = o.matrix_world
    for v in me.vertices:
        w = mw @ v.co; k = fn(w)
        ca.data[v.index].color = (k, k * 0.97, k * 1.04 if k < 0.9 else k, 1.0)


# ------------------------------------------------------------------ zemin: tümsekli, kayanın dibine doğru yükselen
def path_mask(x, y):
    """Toprak/çakıl maskesi (0..1): ağızdan dışarı uzanan patika + ağız önünde yelpaze; kenarı gürültüyle yırtık."""
    cx = 0.06 * math.sin(y * 1.3)
    w = 0.42 + 0.1 * mnoise.noise(V((0, y * 1.4, 4)))
    k = max(0.0, 1.0 - abs(x - cx) / w)
    if y > MOUTH_Y - 0.1: k = 1.0 if abs(x) < MOUTH_W * 1.3 else k
    fan = max(0.0, 1.0 - math.hypot(x / 1.25, (y - MOUTH_Y) / 0.75))
    k = max(k, fan)
    k += 0.35 * mnoise.noise(V((x * 2.6, y * 2.6, 9)))
    if y < MOUTH_Y - 2.6: k *= max(0.0, 1 - (MOUTH_Y - 2.6 - y) / 0.8)
    return max(0.0, min(1.0, k * 1.4 - 0.2))


def m_turf_blend(name='turfblend'):
    """Çim ↔ toprak/çakıl: 'dirt' özniteliği + iki ölçekli gürültü; geçişte ezilmiş açık-sarımsı ot şeridi."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        at = n.new('ShaderNodeAttribute'); at.attribute_name = 'dirt'
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9; nz.inputs['Detail'].default_value = 6; l.new(tc.outputs['Object'], nz.inputs['Vector'])
        ad = n.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.45
        l.new(nz.outputs['Fac'], ad.inputs[0]); l.new(at.outputs['Fac'], ad.inputs[2])
        mk = n.new('ShaderNodeMapRange'); mk.interpolation_type = 'SMOOTHSTEP'; mk.inputs['From Min'].default_value = 0.55; mk.inputs['From Max'].default_value = 0.85
        l.new(ad.outputs[0], mk.inputs['Value'])
        g2 = n.new('ShaderNodeTexNoise'); g2.inputs['Scale'].default_value = 4; l.new(tc.outputs['Object'], g2.inputs['Vector'])
        grass = ramp(nt, [(0.3, '#5f9a3e'), (0.55, '#78ad4e'), (0.75, '#93bf5c')]); l.new(g2.outputs['Fac'], grass.inputs['Fac'])
        dn = n.new('ShaderNodeTexNoise'); dn.inputs['Scale'].default_value = 22; dn.inputs['Detail'].default_value = 8; l.new(tc.outputs['Object'], dn.inputs['Vector'])
        dirt = ramp(nt, [(0.3, '#7a5a3a'), (0.5, '#9c7a52'), (0.7, '#b89a70')]); l.new(dn.outputs['Fac'], dirt.inputs['Fac'])
        # çakıl benekleri toprağın içinde
        vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 38; l.new(tc.outputs['Object'], vo.inputs['Vector'])
        gv = n.new('ShaderNodeMapRange'); gv.inputs['From Min'].default_value = 0.0; gv.inputs['From Max'].default_value = 0.18
        gv.inputs['To Min'].default_value = 0.8; gv.inputs['To Max'].default_value = 0.0; l.new(vo.outputs['Distance'], gv.inputs['Value'])
        dm = n.new('ShaderNodeMix'); dm.data_type = 'RGBA'; dm.inputs[7].default_value = srgb('#c9c0b4')
        l.new(gv.outputs[0], dm.inputs['Factor']); l.new(dirt.outputs[0], dm.inputs[6])
        # geçiş şeridi: ezilmiş kuru ot
        ed = n.new('ShaderNodeMapRange'); ed.inputs['From Min'].default_value = 0.35; ed.inputs['From Max'].default_value = 0.6
        l.new(ad.outputs[0], ed.inputs['Value'])
        ed2 = n.new('ShaderNodeMath'); ed2.operation = 'PINGPONG'; ed2.inputs[1].default_value = 0.5; l.new(ed.outputs[0], ed2.inputs[0])
        gm = n.new('ShaderNodeMix'); gm.data_type = 'RGBA'; gm.inputs[7].default_value = srgb('#b3b866')
        e3 = n.new('ShaderNodeMath'); e3.operation = 'MULTIPLY'; e3.inputs[1].default_value = 1.1; l.new(ed2.outputs[0], e3.inputs[0])
        l.new(e3.outputs[0], gm.inputs['Factor']); l.new(grass.outputs[0], gm.inputs[6])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        l.new(mk.outputs[0], mx.inputs['Factor']); l.new(gm.outputs[2], mx.inputs[6]); l.new(dm.outputs[2], mx.inputs[7])
        l.new(mx.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.9
    return nodes_mat(name, b)


def terrain(size=9.0, n=90):
    G = m_turf_blend()
    bm = bmesh.new(); grid = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x = -size / 2 + size * i / n; y = -size / 2 + size * j / n
            # kayanın çevresinde yumuşak tümsek (zeminden doğsun), önde patika için hafif çukur
            d = math.hypot(x / 1.6, (y - 0.4) / 1.3)
            z = 0.42 * math.exp(-d * d * 0.9) + 0.06 * mnoise.noise(V((x * 0.6, y * 0.6, 2)))
            if y < MOUTH_Y + 0.2 and abs(x) < 0.8: z -= 0.04 * math.exp(-x * x * 4)
            if abs(x) < MOUTH_W * 1.5 and y > MOUTH_Y - 0.7:   # tünel tabanı: zemin ağza doğru yumuşakça iner, içeride patikanın altında kalır
                t = min(1.0, (y - (MOUTH_Y - 0.7)) / 0.7); edge = min(1.0, (MOUTH_W * 1.5 - abs(x)) / 0.3)
                z = min(z, z * (1 - t * edge) + (0.0 - 0.1 * max(0.0, (y - MOUTH_Y) / 0.3)) * t * edge)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(n):
        for i in range(n):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    o = link_mesh('terrain', bm, [G]); smooth(o)
    me = o.data; ca = me.color_attributes.new('dirt', 'FLOAT', 'POINT')
    for v in me.vertices: ca.data[v.index].value = path_mask(v.co.x, v.co.y)
    return o


def ground_z(dg, x, y):
    ok, loc, *_ = bpy.context.scene.ray_cast(dg, V((x, y, 6)), V((0, 0, -1)))
    return loc.z if ok else 0.0


# ------------------------------------------------------------------ kaya kütlesi + eğrisel ağız
def mass():
    STN = shade_by_attr(m_rock(moss_th=(0.85, 1.1), warm=('#7d7684', '#958d98', '#b0a79c'), name='caverock'))
    parts = []
    spec = (((0, 0.55, 0.6), 1.35, (1.15, 0.95, 0.9)), ((-1.05, 0.5, 0.4), 0.85, (1.0, 1.0, 0.9)), ((1.1, 0.45, 0.42), 0.88, (1.0, 1.0, 0.95)),
            ((0.25, 1.15, 1.05), 0.95, (1.0, 0.9, 0.9)), ((-0.62, -0.25, 0.25), 0.55, (1.0, 1.0, 0.9)), ((0.72, -0.25, 0.25), 0.52, (1.0, 1.0, 0.9)),
            ((-1.6, 0.1, 0.1), 0.45, (1.0, 1.0, 0.7)), ((1.65, 0.15, 0.1), 0.42, (1.0, 1.0, 0.7)))
    for k, (loc, r, sq) in enumerate(spec):
        parts.append(rock(loc, r, STN, k, sq=sq, sub=3, amt=0.12))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    M = bpy.context.object; M.name = 'cave'
    rm = M.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.045
    bpy.ops.object.modifier_apply(modifier='rm')
    # tünel: gürültüyle bozulmuş, içe doğru daralan ve hafif kıvrılan oval tüp (köşeli silindir yerine)
    bm = bmesh.new(); rings = []; NR, NS = 14, 28
    for j in range(NR + 1):
        s = j / NR; y = MOUTH_Y - 0.6 + s * (DEPTH + 0.6)
        w = MOUTH_W * (1.12 - 0.35 * s); h = MOUTH_H * (1.08 - 0.3 * s); cx = 0.18 * math.sin(s * 2.2)
        ring = []
        for i in range(NS):
            a = i / NS * 2 * math.pi
            rr = 1 + 0.1 * mnoise.noise(V((math.cos(a) * 2, math.sin(a) * 2, s * 3)))
            x = cx + math.cos(a) * w * rr; z = -0.2 + (math.sin(a) * 0.5 + 0.5) * (h + 0.25) * rr * (1.0 if math.sin(a) > 0 else 0.35)
            ring.append(bm.verts.new((x, y, z - 0.25 * (1 - s) * 0)))
        rings.append(ring)
    for j in range(NR):
        for i in range(NS):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % NS], rings[j + 1][(i + 1) % NS], rings[j + 1][i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cut = link_mesh('cut', bm, [])
    bo = M.modifiers.new('bo', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'
    bpy.context.view_layer.objects.active = M; bpy.ops.object.modifier_apply(modifier='bo')
    bpy.data.objects.remove(cut)
    # yumuşat (köşeli ağız kenarı → yuvarlak dudak), tabanı zemine bastır
    sm = M.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = 6
    bpy.ops.object.modifier_apply(modifier='sm')
    for v in M.data.vertices:
        if v.co.z < 0.05: v.co.z = 0.05 + (v.co.z - 0.05) * 0.15
    smooth(M)
    paint_shade(M, lambda w: depth_shade(w.y, w.x, w.z) if (abs(w.x) < MOUTH_W * 1.6 and w.z < MOUTH_H * 1.4 and w.y > MOUTH_Y - 0.1) else 1.0)
    PEB = m_rock(moss_th=(1.2, 1.5), warm=('#827b88', '#9a929d', '#b7ae a3'.replace(' ', '')), name='pebblerock')   # gölgesiz kopya (çakıl, yan taş)
    return M, PEB


# ------------------------------------------------------------------ içeri giden patika (koyulaşan)
def path_in(dg):
    D = shade_by_attr(m_turf_blend('cavepath'))   # zeminle aynı toprak: dikiş görünmesin
    bm = bmesh.new(); rows = []
    for j in range(26):
        s = j / 25; y = MOUTH_Y - 0.08 + s * (DEPTH - 0.02)
        w = MOUTH_W * (1.25 - 0.4 * s) * (1 + 0.05 * math.sin(s * 9))   # tünel tabanını kenardan kenara örter
        cx = 0.18 * math.sin(max(0.0, (y - MOUTH_Y)) / (DEPTH + 0.6) * 2.2)
        row = []
        for i in range(7):
            u = i / 6 * 2 - 1
            x = cx + u * w * (1 + 0.12 * mnoise.noise(V((u * 3, y * 2, 5))))
            z = (ground_z(dg, x, y) if y < MOUTH_Y + 0.02 else 0.0) + 0.012   # dışarıda zemine yapışık, içeride düz taban
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for j in range(25):
        for i in range(6):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    o = link_mesh('path', bm, [D]); smooth(o)
    paint_shade(o, lambda w: depth_shade(w.y))
    ca = o.data.color_attributes.new('dirt', 'FLOAT', 'POINT')
    for v in o.data.vertices: ca.data[v.index].value = 1.0
    # iç uç: tünelin sonunu kapatan, ışığı yutan koyu "derinlik" perdesi (gradyanlı, tam siyah değil)
    bm = bmesh.new(); vs = []
    yb = MOUTH_Y + DEPTH - 0.1
    for (x, z) in ((-0.7, 0.0), (0.7, 0.0), (0.7, 0.9), (-0.7, 0.9)): vs.append(bm.verts.new((x + 0.18 * math.sin(2.2), yb, z)))
    bm.faces.new(vs)
    back = link_mesh('deep', bm, [A.m_flat('#2a2340', 0.05, 4, 'deep')])
    return o


# ------------------------------------------------------------------ sarmaşıklar: farklı boy, damarlı kalp yapraklar
def vines(M):
    V1 = A.m_flat('#3d6f2a', 0.2, 8, 'vine')
    LVs = [m_leaf('#2a7a33', '#47a845', '#94d264', '#d4f0a0', 'ivyA'), m_leaf('#2f6d2c', '#3f9a3e', '#7cc456', '#c8e89a', 'ivyB'),
           m_leaf('#3c8a2c', '#62b847', '#b2de6c', '#e4f6b6', 'ivyC')]
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    leaves = []
    for k in range(14):
        x = -MOUTH_W * 1.25 + k * (MOUTH_W * 2.5 / 13) + R.uniform(-0.04, 0.04)
        ok, top, *_ = bpy.context.scene.ray_cast(dg, V((x, MOUTH_Y - 1.0, MOUTH_H + 0.32)), V((0, 1, 0)))
        if not ok: continue
        top = top + V((0, -0.02, 0))
        L = R.choice((0.22, 0.32, 0.45, 0.6, 0.75)) * (0.75 if abs(x) < MOUTH_W * 0.5 else 1.0)   # ortada kısa: ağız açık kalsın
        sway = R.uniform(-0.06, 0.06)
        pts = [tuple(top), tuple(top + V((sway * 0.5, -0.05, -L * 0.5))), tuple(top + V((sway, -0.03, -L)))]
        T.tube('ivy', pts, [0.009, 0.007, 0.004], V1, res=4)
        n = max(3, int(L / 0.07))
        for q in range(n):
            s = (q + 0.5) / n
            p = top + V((sway * s, -0.04 - 0.02 * math.sin(s * 3), -L * s))
            side = 1 if q % 2 == 0 else -1
            size = (0.05 + 0.04 * (1 - s)) * R.uniform(0.85, 1.2)          # uçta küçülen yapraklar
            leaves.append((p, side, size, R.randint(0, 2), R.uniform(-0.4, 0.4)))
    # duvar üstüne yayılan kısa sarmaşık örtüsü
    for k in range(40):
        a = R.uniform(-1.3, 1.3); x = math.sin(a) * 1.3; zt = MOUTH_H + 0.25 + R.uniform(0, 0.45)
        ok, p, nrm, *_ = bpy.context.scene.ray_cast(dg, V((x, MOUTH_Y - 1.5, zt)), V((0, 1, 0)))
        if ok: leaves.append((p + nrm * 0.01, R.choice((1, -1)), R.uniform(0.045, 0.075), R.randint(0, 2), R.uniform(-1, 1)))

    def build(bm):
        out = []
        for (p, side, size, mi, tw) in leaves:
            d = V((side * 0.75, -0.55, -0.35 + tw * 0.2)).normalized(); s = V((-d.y, d.x, 0.25)).normalized()
            for f in blade(bm, p, d, s, size * 1.6, size * 0.75, 0.35, segs=4, lift=0.05): out.append((f, mi))
        return out
    mesh_from_blades('ivyleaves', build, LVs)


# ------------------------------------------------------------------ giriş süsü: çalı, çiçek, biriken çakıl, kristal
def dressing(dg, STN):
    BL = m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'bushleaf')
    bushes = [(-1.15, MOUTH_Y - 0.35), (1.2, MOUTH_Y - 0.3), (-1.55, MOUTH_Y + 0.25), (1.6, MOUTH_Y + 0.3), (-0.85, MOUTH_Y - 0.85), (0.95, MOUTH_Y - 0.9),
              (-2.0, MOUTH_Y - 0.4), (2.05, MOUTH_Y - 0.35)]
    ro = mesh_from_blades('bush', rosette(bushes, R, sizes=(0.3, 0.46), leaves=11), [BL])
    for v in ro.data.vertices:
        v.co.z += ground_z(dg, v.co.x, v.co.y)
    for k, (x, y) in enumerate(((-0.8, MOUTH_Y - 0.2), (0.85, MOUTH_Y - 0.15), (-1.3, MOUTH_Y - 1.0), (1.35, MOUTH_Y - 1.05), (-0.55, MOUTH_Y - 1.4), (0.6, MOUTH_Y - 1.5),
                                 (-1.8, MOUTH_Y - 1.1), (1.85, MOUTH_Y - 0.9), (-0.3, MOUTH_Y - 2.0), (0.4, MOUTH_Y - 2.1))):
        o = lush((x, y, 0), 0.12, 2, 300 + k, h=(0.16, 0.32))
        for v in o.data.vertices: v.co.z += ground_z(dg, x, y)
    flower_heads([(x, y, ground_z(dg, x, y) + R.uniform(0.16, 0.26)) for (x, y) in
                  ((-1.0, MOUTH_Y - 0.6), (1.05, MOUTH_Y - 0.65), (-1.6, MOUTH_Y - 0.7), (1.7, MOUTH_Y - 0.55), (-0.7, MOUTH_Y - 1.7), (0.8, MOUTH_Y - 1.75))], R)
    # girişte biriken çakıllar: ağza yakın sık, uzaklaştıkça seyrek; kenarlara doğru yığılır
    for k in range(70):
        y = MOUTH_Y - R.random() ** 1.6 * 1.9 + 0.35
        x = R.choice((-1, 1)) * (0.25 + R.random() * 0.55) * (1.2 - 0.3 * (MOUTH_Y - y))
        if MOUTH_Y < y: x *= 0.8
        r = R.uniform(0.022, 0.06) * (1.25 if abs(x) > 0.5 else 1.0)
        gz = 0.06 if y > MOUTH_Y - 0.05 else ground_z(dg, x, y)   # ağız içinde patika hizası (tavana çarpmasın)
        o = pebble((x, y, gz + r * 0.25), r, STN, 500 + k)
    for k in range(26):   # eşikte biriken ince çakıl şeridi (ağız dudağı boyunca)
        x = -MOUTH_W * 1.25 + k * (MOUTH_W * 2.5 / 25) + R.uniform(-0.03, 0.03); y = MOUTH_Y - 0.08 + R.uniform(-0.06, 0.06)
        r = R.uniform(0.02, 0.045); pebble((x, y, ground_z(dg, x, y) + r * 0.2), r, STN, 800 + k)
    for k in range(5):   # büyük yan taşlar
        s = (-1, 1)[k % 2]
        rock((s * R.uniform(0.75, 1.0), MOUTH_Y - R.uniform(0.0, 0.5), 0.08), R.uniform(0.12, 0.2), STN, 40 + k, sq=(1.1, 0.9, 0.7), sub=2, amt=0.18)
    CR = m_plaster('#5fe0e8', name='crystal', dirt=0.0)
    for (x, y, h, tilt) in ((-0.7, MOUTH_Y + 0.15, 0.36, 18), (-0.56, MOUTH_Y + 0.05, 0.22, -12), (0.68, MOUTH_Y + 0.18, 0.32, -16), (0.8, MOUTH_Y + 0.25, 0.2, 22)):
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.07, radius2=0.0, depth=h, location=(x, y, h / 2 + 0.03), rotation=(0, math.radians(tilt), 0))
        bpy.context.object.data.materials.append(CR)


def ferns(dg, spots):
    FL = [m_leaf('#2a6f2c', '#3f9a3a', '#86c95a', '#c6ea94', 'fernA'), m_leaf('#326f28', '#4f9e36', '#9ccf5e', '#d2ee9e', 'fernB')]
    def build(bm):
        out = []
        for k, (x, y, sc_) in enumerate(spots):
            base = V((x, y, ground_z(dg, x, y) + 0.01)); Rr = random.Random(900 + k)
            for f in range(Rr.randint(6, 9)):
                a = f / 7 * 6.28 + Rr.uniform(-0.3, 0.3); up = Rr.uniform(0.35, 0.7)
                d = V((math.cos(a) * (1 - up), math.sin(a) * (1 - up), up)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
                L = Rr.uniform(0.32, 0.5) * sc_
                for f2 in blade(bm, base, d, side, L, 0.012, 0.9, segs=4, lift=0.2): out.append((f2, 0))    # orta damar (sap)
                nl = 9
                for q in range(1, nl):                                                                # yaprakçık çiftleri
                    s_ = q / nl; p = base + d * (L * s_) + V((0, 0, (0.2 - 0.9 * s_) * L * s_))
                    ln = 0.075 * sc_ * (1 - s_ * 0.75)
                    for sg in (1, -1):
                        dd = (side * sg + d * 0.45).normalized()
                        for f3 in blade(bm, p, dd, d.cross(dd).normalized() if d.cross(dd).length > 0 else side, ln, ln * 0.32, 0.4, segs=2): out.append((f3, q % 2))
        return out
    mesh_from_blades('fern', build, FL)


def scene_setup():
    sc = kit.reset(); sc.cycles.samples = int(os.environ.get('CAVE_SAMPLES', '48')); sc.view_settings.exposure = -0.3
    return sc


if __name__ == '__main__':
    sc = scene_setup()
    terrain()
    M, STN = mass()
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    path_in(dg)
    vines(M)
    dressing(dg, STN)
    ferns(dg, [(-0.95, MOUTH_Y - 0.05, 1.1), (0.98, MOUTH_Y - 0.02, 1.15), (-1.35, MOUTH_Y + 0.1, 1.2), (1.4, MOUTH_Y + 0.15, 1.2),
               (-0.72, MOUTH_Y - 0.45, 0.9), (0.78, MOUTH_Y - 0.5, 0.9), (-1.9, MOUTH_Y + 0.3, 1.0), (1.95, MOUTH_Y + 0.35, 1.0),
               (-1.15, MOUTH_Y - 0.75, 0.85), (1.2, MOUTH_Y - 0.8, 0.85), (-2.3, MOUTH_Y - 0.2, 0.9), (2.3, MOUTH_Y - 0.1, 0.9)])
    # tepe otları
    for k in range(10):
        x, y = R.uniform(-1.2, 1.2), R.uniform(0.0, 1.4)
        ok, loc, *_ = bpy.context.scene.ray_cast(dg, V((x, y, 6)), V((0, 0, -1)))
        if ok and loc.z > 0.8: lush(tuple(loc - V((0, 0, 0.02))), 0.1, 1, 700 + k, h=(0.14, 0.26))
    kit.to_mesh_all()
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    print('ucgen_toplam', kit.tri_count(objs), 'zemin_haric', kit.tri_count([o for o in objs if o.name != 'terrain']))
    tgt = (0, MOUTH_Y + 0.3, 0.55)
    if not os.environ.get('CAVE_QUICK'): shoot(sc, f'{OUT}/cave_v4_genel.png', tgt, 7.5, 28, 30, lens=50, size=(1280, 800))
    if os.environ.get('CAVE_QUICK'):
        shoot(sc, f'{OUT}/q_agiz.png', (0, MOUTH_Y + 0.4, 0.4), 3.6, 4, 9, lens=45, size=(640, 400)); sys.exit(0)
    shoot(sc, f'{OUT}/cave_v4_agiz.png', (0, MOUTH_Y + 0.4, 0.4), 3.6, 4, 9, lens=45, size=(1280, 800))
    shoot(sc, f'{OUT}/cave_v4_sarmasik.png', (-0.35, MOUTH_Y - 0.02, MOUTH_H + 0.05), 1.35, -18, 4, lens=55, size=(1280, 800))
    shoot(sc, f'{OUT}/cave_v4_ust.png', (0, MOUTH_Y + 0.4, 0.4), 9.5, 0, 55, lens=50, size=(1280, 800))
    print('ok')
