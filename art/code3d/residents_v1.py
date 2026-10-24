# Adalılar v1 — kodla 3B (24 Ekim 2026, kullanıcı: "Palmiye, Tosbi karakteri (ada sakinleri) dahil bütün tasarımlar detaylı 3D olsun").
# Kıskaç / Mavi / Pus Meshy'den geldi; hikâyenin diğer adalıları burada Blender bpy ile, aynı "vinyl oyuncak" dilinde kurulur:
#   res_tosbi  Tosbi Dede: yaşlı, bilge, güler yüzlü deniz kaplumbağası (iskelede). Yuvarlak gözlük, beyaz kaş + keçi sakal,
#              örgü atkı, bastonu sağ elinde, sol eliyle selam verir. Kabuk sırtta: kabarık altıgen plakalar + kenar halkası. ~1,2 m.
#   res_pitir  Pıtır: geveze, heyecanlı palmiye (Hindistan Cevizi Bahçesi). Uzun (~2,6 m), açık limon yeşili dik/sivri yapraklar,
#              tepede perçem, kocaman parlak gözler, açık gülen ağız, bir yaprak-eli havada; 3 kahverengi ceviz.
#   res_hisir  Hışır: utangaç ikizi (Pıtır'ın cümle sonlarını yineler). Kısa (~2,25 m), koyu deniz yeşili, sarkık yumuşak yapraklar,
#              aşağı bakan yarı kapalı gözler, büyük al yanak, küçük gülümseme, yaprak-elleri önde birleşik; 2 yeşil ceviz.
# Üretim (v6/proxy_bake ile aynı fikir): TAM ayrıntılı model (alt bölmeli parçalar + göz parıltısı, yanak, ağız, tırnak gibi
# "çıkartmalar") kaynak; hedef = gövde parçalarının voksel ile tek kabuğa örülmüş + ayrı kalan ince parçaların (gözlük, baston, yaprak)
# bütçeye indirgenmiş ağı, göz boncukları sabit payla yuvarlak. Renk + yumuşak AO + teğet normal haritası hedefe ışınla aktarılır.
# UV önem gruplarıyla açılır (bake_export/unwrap): yüz ~2,5 kat yoğun doku, yaprak/kabuk sırtı az.
# Çıktı (Kıskaç/Mavi/Pus ile aynı düzen): Assets/_Pofi/Resources/Env/res_<ad>/res_<ad>.fbx + _basecolor.png + _normal.png.
# Yön: önü Blender −Y (oyunda +Z: Resident3D kökü Okti'ye döner), taban z = 0, gerçek boy; iskelet yok (oyun bütün modeli oynatır).
#
# Kullanım (bpy 4.2: /tmp/claude-0/bpyenv/bin/python):
#   python -I art/code3d/residents_v1.py -- build [tosbi pitir hisir]     # dışa aktar (varsayılan: hepsi)
#   python -I art/code3d/residents_v1.py -- draft <klasör> [ad ...]       # yüksek modelin pişirmesiz hızlı çizimi (tasarım denemesi)
#   python -I art/code3d/residents_v1.py -- preview <klasör> [ad ...]     # oyundaki dosyalardan önizleme sayfası (Kıskaç yanında)
# Portreler: art/scripts/resident_portraits.py tosbi pitir hisir
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'v6'))
import bpy, bmesh
from mathutils import Vector as V, Matrix, Quaternion, noise as MN
from mathutils.bvhtree import BVHTree
import kit
from kit import mat, blob, tube, srgb, ramp, nodes_mat, uv_node

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')

# ------------------------------------------------------------------ yardımcılar

def mesh_obj(name, verts, faces, mats, uvs=None, smooth=True, recalc=True):
    """Köşe/yüz listesinden nesne. uvs: yüz başına köşe uv listesi (grain katmanı). recalc: kapalı ağda normaller dışa."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    if uvs is not None:
        lay = me.uv_layers.new(name='grain')
        k = 0
        for poly, fu in zip(me.polygons, uvs):
            for li, uv in zip(poly.loop_indices, fu): lay.data[li].uv = uv
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    if recalc:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for m in mats: o.data.materials.append(m)
    return o

def add_mods(o, sub=2, solid=0.0, solid_offset=0.0):
    if solid:
        s = o.modifiers.new('solid', 'SOLIDIFY'); s.thickness = solid; s.offset = solid_offset; s.use_even_offset = True
    if sub:
        m = o.modifiers.new('sub', 'SUBSURF'); m.levels = sub; m.render_levels = sub
    return o

def frame(normal, up=V((0, 0, 1))):
    """Yüzey çerçevesi: Z = normal, X = yatay teğet, Y = yukarı teğet (dördey)."""
    n = V(normal).normalized()
    x = up.cross(n)
    if x.length < 1e-4: x = V((1, 0, 0))
    x.normalize(); y = n.cross(x).normalized()
    return Matrix((x, y, n)).transposed().to_quaternion()

def blob_q(name, loc, radii, m, q, roll=0.0, sub=2, seg=24):
    o = blob(name, tuple(loc), tuple(radii), m, sub=sub, seg=seg)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = q @ Quaternion((0, 0, 1), math.radians(roll))
    return o

class Surf:
    """Bir ya da birkaç nesnenin (değiştiriciler uygulanmış, dünya uzayında) yüzeyi: yüz özelliklerini oturtmak için."""
    def __init__(self, objs):
        dg = bpy.context.evaluated_depsgraph_get(); vs, fs = [], []
        for o in objs:
            e = o.evaluated_get(dg); me = e.to_mesh()
            off = len(vs); vs += [o.matrix_world @ v.co for v in me.vertices]
            fs += [[off + i for i in p.vertices] for p in me.polygons]
            e.to_mesh_clear()
        self.bvh = BVHTree.FromPolygons(vs, fs)
        c = V((0, 0, 0))
        for v in vs: c += v
        self.c = c / max(1, len(vs))

    def hit(self, center, d):
        """center'dan d yönünde dışarıdan içeri atılan ışının ilk (en dıştaki) çarpması: (konum, normal)."""
        d = V(d).normalized(); o = V(center) + d * 3.0
        loc, nrm, _, _ = self.bvh.ray_cast(o, -d, 6.0)
        if loc is None: return V(center), d
        if nrm.dot(d) < 0: nrm = -nrm
        return loc, nrm.normalized()

def ring_mesh(name, center, ax1, ax2, r1, r2, minor, m, n=48, nm=12, sub=2, minor_fn=None):
    """Elips halka (simit): center + ax1*r1*cos + ax2*r2*sin; grain uv: u = halka boyunca (0..1), v = kesit çevresi."""
    ax1, ax2 = V(ax1).normalized(), V(ax2).normalized(); nrm = ax1.cross(ax2).normalized()
    verts, faces, uvs = [], [], []
    for i in range(n):
        t = i / n * math.tau
        p = V(center) + ax1 * r1 * math.cos(t) + ax2 * r2 * math.sin(t)
        out = (ax1 * math.cos(t) * r2 + ax2 * math.sin(t) * r1).normalized()   # dışa (elips normali yaklaşık)
        mr = minor_fn(i / n) if minor_fn else minor
        for j in range(nm):
            a = j / nm * math.tau
            verts.append(p + out * math.cos(a) * mr + nrm * math.sin(a) * mr)
    for i in range(n):
        for j in range(nm):
            a, b = i * nm + j, i * nm + (j + 1) % nm
            c, d = ((i + 1) % n) * nm + (j + 1) % nm, ((i + 1) % n) * nm + j
            faces.append((a, b, c, d))
            uvs.append([(i / n, j / nm), (i / n, (j + 1) / nm), ((i + 1) / n, (j + 1) / nm), ((i + 1) / n, j / nm)])
    return add_mods(mesh_obj(name, verts, faces, [m], uvs), sub)

def lathe(name, path_fn, rad_fn, rows, around, m, cap_bottom=True, cap_top=True, sub=2):
    """Eğri boyunca dönel gövde. path_fn(t) → nokta, rad_fn(t, a) → yarıçap. grain uv: u = çevre, v = yay uzunluğu (m)."""
    verts, faces, uvs = [], [], []
    pts = [V(path_fn(i / rows)) for i in range(rows + 1)]
    arc = [0.0]
    for i in range(1, rows + 1): arc.append(arc[-1] + (pts[i] - pts[i - 1]).length)
    for i in range(rows + 1):
        t = i / rows
        tg = (pts[min(rows, i + 1)] - pts[max(0, i - 1)]).normalized()
        sx = V((0, 1, 0)).cross(tg).normalized(); sy = tg.cross(sx).normalized()
        for j in range(around):
            a = j / around * math.tau
            r = rad_fn(t, a)
            # a = 0 → −Y (ön): x = sin(a), y = −cos(a)
            verts.append(pts[i] + sx * math.sin(a) * r - sy * math.cos(a) * r if abs(tg.z) > 0.2 else pts[i] + V((math.sin(a), -math.cos(a), 0)) * r)
    for i in range(rows):
        for j in range(around):
            j2 = (j + 1) % around
            faces.append((i * around + j, i * around + j2, (i + 1) * around + j2, (i + 1) * around + j))
            uvs.append([(j / around, arc[i]), ((j + 1) / around, arc[i]), ((j + 1) / around, arc[i + 1]), (j / around, arc[i + 1])])
    if cap_bottom:
        c = len(verts); verts.append(pts[0])
        for j in range(around):
            faces.append((c, (j + 1) % around, j)); uvs.append([(0.5, 0), (0.5, 0), (0.5, 0)])
    if cap_top:
        c = len(verts); verts.append(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.002)
        base = rows * around
        for j in range(around):
            faces.append((c, base + j, base + (j + 1) % around)); uvs.append([(0.5, arc[-1])] * 3)
    o = mesh_obj(name, verts, faces, [m], uvs)
    return add_mods(o, sub), pts, arc

# ------------------------------------------------------------------ malzemeler (temiz boyalı vinyl: geçişler yumuşak, gürültü az)

def vinyl(name, hexc, rough=0.36, coat=0.3):
    return mat(name, hexc, rough=rough, coat=coat)

def glossy_black():
    return mat('eye', '#1b1420', rough=0.08, coat=1.0)

def glint():
    return mat('glint', '#ffffff', rough=0.2, coat=0.0, emit=1.2)

def m_skin(name, base, spot, spot_amt=0.35, scale=5.0):
    """Kaplumbağa derisi: yumuşak, seyrek koyu benekler (nesnenin kendi koordinatında)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord')
        vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = scale; vo.inputs['Randomness'].default_value = 0.8
        l.new(tc.outputs['Object'], vo.inputs['Vector'])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.12; mr.inputs['From Max'].default_value = 0.26
        mr.inputs['To Min'].default_value = spot_amt; mr.inputs['To Max'].default_value = 0.0; l.new(vo.outputs['Distance'], mr.inputs['Value'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = srgb(base); mx.inputs[7].default_value = srgb(spot)
        l.new(mr.outputs[0], mx.inputs['Factor']); l.new(mx.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.42; bsdf.inputs['Coat Weight'].default_value = 0.25
    return nodes_mat(name, b)

def m_uv_ramp(name, stops, axis='Y', rough=0.4, coat=0.25, scale=1.0, offset=0.0, repeat=False, bump=None):
    """grain uv'nin bir ekseni boyunca renk geçişi (repeat: kesirli kısım → halka/şerit deseni). bump: [(konum, yükseklik)] aynı eksende."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        ma = n.new('ShaderNodeMath'); ma.operation = 'MULTIPLY_ADD'; ma.inputs[1].default_value = scale; ma.inputs[2].default_value = offset
        l.new(sep.outputs[axis], ma.inputs[0]); src = ma
        if repeat:
            fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(ma.outputs[0], fr.inputs[0]); src = fr
        rp = ramp(nt, stops); l.new(src.outputs[0], rp.inputs['Fac']); l.new(rp.outputs[0], bsdf.inputs['Base Color'])
        if bump:
            br = n.new('ShaderNodeValToRGB'); el = br.color_ramp.elements
            while len(el) < len(bump): el.new(0.5)
            for e, (pos, h) in zip(el, bump): e.position = pos; e.color = (h, h, h, 1)
            l.new(src.outputs[0], br.inputs['Fac'])
            bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6; bp.inputs['Distance'].default_value = 0.01
            l.new(br.outputs[0], bp.inputs['Height']); l.new(bp.outputs[0], bsdf.inputs['Normal'])
        bsdf.inputs['Roughness'].default_value = rough; bsdf.inputs['Coat Weight'].default_value = coat
    return nodes_mat(name, b)

def m_radial(name, inner, outer, edge, rough=0.36, coat=0.35):
    """grain uv (−1..1) merkezinden kenara: plaka ortası açık, kenarı koyu (kabuk plakaları)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); vl = n.new('ShaderNodeVectorMath'); vl.operation = 'LENGTH'; l.new(uv.outputs[0], vl.inputs[0])
        rp = ramp(nt, [(0.0, inner), (0.55, outer), (0.92, edge)]); l.new(vl.outputs['Value'], rp.inputs['Fac'])
        # ince eş merkezli büyüme halkaları (gerçek kaplumbağa plakası; çok hafif)
        mu = n.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 22.0; l.new(vl.outputs['Value'], mu.inputs[0])
        sn = n.new('ShaderNodeMath'); sn.operation = 'SINE'; l.new(mu.outputs[0], sn.inputs[0])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.6; mr.inputs['From Max'].default_value = 1.0
        mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 0.10; l.new(sn.outputs[0], mr.inputs['Value'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb(edge)
        l.new(mr.outputs[0], mx.inputs['Factor']); l.new(rp.outputs[0], mx.inputs[6]); l.new(mx.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = rough; bsdf.inputs['Coat Weight'].default_value = coat
    return nodes_mat(name, b)

def m_plastron(name, base, seam):
    """Karın plakası: kendi koordinatında yatay ek yerleri + orta dikey çizgi (renk + oluk)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs[0])
        # yatay ekler: |sin(z * k)| küçükken çizgi
        mu = n.new('ShaderNodeMath'); mu.operation = 'MULTIPLY_ADD'; mu.inputs[1].default_value = 2.6; mu.inputs[2].default_value = 0.35
        l.new(sep.outputs['Z'], mu.inputs[0])
        sn = n.new('ShaderNodeMath'); sn.operation = 'SINE'; l.new(mu.outputs[0], sn.inputs[0])
        ab = n.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; l.new(sn.outputs[0], ab.inputs[0])
        h1 = n.new('ShaderNodeMapRange'); h1.inputs['From Min'].default_value = 0.0; h1.inputs['From Max'].default_value = 0.09
        h1.inputs['To Min'].default_value = 1.0; h1.inputs['To Max'].default_value = 0.0; l.new(ab.outputs[0], h1.inputs['Value'])
        ax = n.new('ShaderNodeMath'); ax.operation = 'ABSOLUTE'; l.new(sep.outputs['X'], ax.inputs[0])
        h2 = n.new('ShaderNodeMapRange'); h2.inputs['From Min'].default_value = 0.0; h2.inputs['From Max'].default_value = 0.035
        h2.inputs['To Min'].default_value = 1.0; h2.inputs['To Max'].default_value = 0.0; l.new(ax.outputs[0], h2.inputs['Value'])
        mx = n.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; l.new(h1.outputs[0], mx.inputs[0]); l.new(h2.outputs[0], mx.inputs[1])
        # alt ve üst uçta ek yeri yok (yalnız orta bölge)
        az = n.new('ShaderNodeMath'); az.operation = 'ABSOLUTE'; l.new(sep.outputs['Z'], az.inputs[0])
        gate = n.new('ShaderNodeMapRange'); gate.inputs['From Min'].default_value = 0.8; gate.inputs['From Max'].default_value = 0.92
        gate.inputs['To Min'].default_value = 1.0; gate.inputs['To Max'].default_value = 0.0; l.new(az.outputs[0], gate.inputs['Value'])
        g = n.new('ShaderNodeMath'); g.operation = 'MULTIPLY'; l.new(mx.outputs[0], g.inputs[0]); l.new(gate.outputs[0], g.inputs[1])
        cm = n.new('ShaderNodeMix'); cm.data_type = 'RGBA'; cm.inputs[6].default_value = srgb(base); cm.inputs[7].default_value = srgb(seam)
        l.new(g.outputs[0], cm.inputs['Factor']); l.new(cm.outputs[2], bsdf.inputs['Base Color'])
        inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; l.new(g.outputs[0], inv.inputs[1])
        bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5; bp.inputs['Distance'].default_value = 0.012
        l.new(inv.outputs[0], bp.inputs['Height']); l.new(bp.outputs[0], bsdf.inputs['Normal'])
        bsdf.inputs['Roughness'].default_value = 0.4; bsdf.inputs['Coat Weight'].default_value = 0.3
    return nodes_mat(name, b)

def m_wood(name, a, b_, grain=(30, 30, 2.5)):
    """Baston: boyuna damar (nesne koordinatı z boyunca uzamış gürültü)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = grain
        l.new(tc.outputs['Object'], mp.inputs['Vector'])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.5; nz.inputs['Detail'].default_value = 3; l.new(mp.outputs[0], nz.inputs['Vector'])
        rp = ramp(nt, [(0.35, a), (0.65, b_)]); l.new(nz.outputs['Fac'], rp.inputs['Fac']); l.new(rp.outputs[0], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.45; bsdf.inputs['Coat Weight'].default_value = 0.35
    return nodes_mat(name, b)

def m_knit(name, c1, c2, stripes=6.0, rib=70.0, axis='X'):
    """Örgü atkı: boyunca iki renk şerit + ince örgü sırtları (grain uv: X = boy, Y = kesit)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        mu = n.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = stripes; l.new(sep.outputs[axis], mu.inputs[0])
        fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(mu.outputs[0], fr.inputs[0])
        rp = ramp(nt, [(0.0, c1), (0.62, c1), (0.66, c2), (0.96, c2), (1.0, c1)]); l.new(fr.outputs[0], rp.inputs['Fac'])
        l.new(rp.outputs[0], bsdf.inputs['Base Color'])
        # örgü: boyunca sık dalga (V ilmekleri yerine sade sırt)
        mu2 = n.new('ShaderNodeMath'); mu2.operation = 'MULTIPLY'; mu2.inputs[1].default_value = rib; l.new(sep.outputs[axis], mu2.inputs[0])
        sn = n.new('ShaderNodeMath'); sn.operation = 'SINE'; l.new(mu2.outputs[0], sn.inputs[0])
        bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.004
        l.new(sn.outputs[0], bp.inputs['Height']); l.new(bp.outputs[0], bsdf.inputs['Normal'])
        bsdf.inputs['Roughness'].default_value = 0.75; bsdf.inputs['Coat Weight'].default_value = 0.0; bsdf.inputs['Sheen Weight'].default_value = 0.3
    return nodes_mat(name, b)

def m_leaf(name, base, mid, tip, rib, rough=0.38):
    """Vinyl palmiye yaprağı: dipten uca koyu → açık, ortada açık damar oluğu, yanlarda çok hafif çapraz damar (grain uv: X = boy 0..1, Y = en −1..1)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        rp = ramp(nt, [(0.0, base), (0.5, mid), (1.0, tip)]); l.new(sep.outputs['X'], rp.inputs['Fac'])
        ab = n.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; l.new(sep.outputs['Y'], ab.inputs[0])
        vm = n.new('ShaderNodeMapRange'); vm.inputs['From Min'].default_value = 0.04; vm.inputs['From Max'].default_value = 0.11
        vm.inputs['To Min'].default_value = 1.0; vm.inputs['To Max'].default_value = 0.0; l.new(ab.outputs[0], vm.inputs['Value'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb(rib)
        l.new(vm.outputs[0], mx.inputs['Factor']); l.new(rp.outputs[0], mx.inputs[6])
        # yan damarlar: u + 0.35|v| boyunca dalga, kenara doğru söner
        ad = n.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.35
        l.new(ab.outputs[0], ad.inputs[0]); l.new(sep.outputs['X'], ad.inputs[2])
        mu = n.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 70.0; l.new(ad.outputs[0], mu.inputs[0])
        sn = n.new('ShaderNodeMath'); sn.operation = 'SINE'; l.new(mu.outputs[0], sn.inputs[0])
        sv = n.new('ShaderNodeMapRange'); sv.inputs['From Min'].default_value = 0.82; sv.inputs['From Max'].default_value = 1.0
        sv.inputs['To Min'].default_value = 0.0; sv.inputs['To Max'].default_value = 0.16; l.new(sn.outputs[0], sv.inputs['Value'])
        mx2 = n.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; mx2.inputs[7].default_value = srgb(rib)
        l.new(sv.outputs[0], mx2.inputs['Factor']); l.new(mx.outputs[2], mx2.inputs[6]); l.new(mx2.outputs[2], bsdf.inputs['Base Color'])
        # damar oluğu (normal haritasına geçer)
        bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5; bp.inputs['Distance'].default_value = 0.008
        l.new(vm.outputs[0], bp.inputs['Height']); bp.invert = True; l.new(bp.outputs[0], bsdf.inputs['Normal'])
        bsdf.inputs['Roughness'].default_value = rough; bsdf.inputs['Coat Weight'].default_value = 0.3
    return nodes_mat(name, b)

# ------------------------------------------------------------------ ortak yüz parçaları

def bead_eye(tag, surf, center, d, w, h, depth, glint_at=(0.32, 0.36), glint2=True, sink=0.35, roll=0.0):
    """Parlak siyah boncuk göz (yüzeye oturur) + iki ışık noktası. Döndürür: (biçim parçaları, ayrıntı parçaları, (konum, normal))."""
    p, nrm = surf.hit(center, d)
    q = frame(nrm)
    eye = blob_q('eye_' + tag, p + nrm * depth * (1 - sink), (w, h, depth), glossy_black(), q, roll=roll)
    det = []
    qx, qy = q @ V((1, 0, 0)), q @ V((0, 1, 0))
    for (gx, gy, gs) in [(glint_at[0], glint_at[1], 0.30)] + ([(-glint_at[0] * 0.8, -glint_at[1] * 0.9, 0.13)] if glint2 else []):
        k = math.sqrt(max(0.0, 1 - gx * gx - gy * gy))
        gp = p + nrm * (depth * (1 - sink) + depth * k) + qx * gx * w + qy * gy * h
        det.append(blob_q('glint_' + tag, gp, (w * gs, h * gs * 0.85, depth * 0.25), glint(), q, sub=1, seg=12))
    return [eye], det, (p, nrm, q)

def stroke(name, surf, center, dirs, radii, m, lift=0.002, res=10):
    """Yüzeye oturan ince çizgi (ağız, kaş, çizgi): dirs = yüzeydeki noktalara yönler."""
    pts = []
    for d in dirs:
        p, nrm = surf.hit(center, d); pts.append(tuple(p + nrm * lift))
    return tube(name, pts, radii, m, res=res)

def decal(name, surf, center, d, radii, m, lift=0.004, roll=0.0, sub=1, seg=16):
    """Yüzeye yapışık yassı leke (yanak, burun deliği, benek)."""
    p, nrm = surf.hit(center, d)
    return blob_q(name, p + nrm * lift, (radii[0], radii[1], radii[2] if len(radii) > 2 else 0.006), m, frame(nrm), roll=roll, sub=sub, seg=seg)

def shape_decal(name, surf, center, d, outline, m, lift=0.003, rings=4):
    """Yüzeye oturan düz biçimli çıkartma (ör. D biçimli açık ağız): outline = teğet düzlemde (x sağ, y yukarı, metre) kapalı çizgi.
    İç dolgu eş merkezli halkalarla; her köşe yüzeye ışınla oturtulur."""
    p0, n0 = surf.hit(center, d); q = frame(n0)
    qx, qy = q @ V((1, 0, 0)), q @ V((0, 1, 0))
    cu = sum(u for u, v in outline) / len(outline); cv = sum(v for u, v in outline) / len(outline)
    verts, faces = [], []
    def put(u, v):
        a = p0 + qx * u + qy * v
        loc, nrm, _, _ = surf.bvh.ray_cast(a + n0 * 0.2, -n0, 0.5)
        if loc is None: loc, nrm = a, n0
        if nrm.dot(n0) < 0: nrm = -nrm
        verts.append(loc + nrm * lift)
    n = len(outline)
    for r in range(rings):
        f = 1.0 - r / rings
        for (u, v) in outline: put(cu + (u - cu) * f, cv + (v - cv) * f)
    put(cu, cv); c = len(verts) - 1
    for r in range(rings - 1):
        for j in range(n):
            a, b = r * n + j, r * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    last = (rings - 1) * n
    for j in range(n): faces.append((last + j, last + (j + 1) % n, c))
    o = mesh_obj(name, verts, faces, [m])
    me = o.data
    if sum(pp.normal.dot(n0) for pp in me.polygons) < 0:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return add_mods(o, 1)

# ------------------------------------------------------------------ Tosbi Dede

def pad_on_ellipsoid(name, c, radii, d, size, height, m, sides=6, spin=0.0, sub=2):
    """Elipsoid kabuğa oturan kabarık plaka (altıgen): kenarı yuvarlatılmış, merkezi şişkin; grain uv = plaka içi (−1..1)."""
    c = V(c); rx, ry, rz = radii
    def proj(q):   # elipsoit yüzeyine merkezden ışınla
        u = V(((q.x - c.x) / rx, (q.y - c.y) / ry, (q.z - c.z) / rz)); u.normalize()
        p = V((c.x + u.x * rx, c.y + u.y * ry, c.z + u.z * rz))
        nrm = V(((p.x - c.x) / rx ** 2, (p.y - c.y) / ry ** 2, (p.z - c.z) / rz ** 2)).normalized()
        return p, nrm
    d = V(d).normalized()
    p0, n0 = proj(c + V((d.x * rx, d.y * ry, d.z * rz)))
    qf = frame(n0, up=V((0, 0, 1)) if abs(n0.z) < 0.95 else V((0, 1, 0)))
    tx, ty = qf @ V((1, 0, 0)), qf @ V((0, 1, 0))
    rings = [(0.0, height), (0.45, height * 0.96), (0.78, height * 0.82), (1.0, height * 0.45)]
    verts, uvs2 = [], []
    idx = []
    for k, (rf, h) in enumerate(rings):
        row = []
        cnt = 1 if rf == 0 else sides * (2 if k >= 2 else 1)
        for j in range(cnt):
            a = j / cnt * math.tau + math.radians(spin)
            # altıgen sınır: kenar ortasında yarıçap cos(pi/6) oranında
            if rf > 0:
                sec = math.pi / sides; aa = (a - math.radians(spin)) % (2 * sec) - sec
                hexr = math.cos(sec) / math.cos(aa)
                lu, lv = math.cos(a) * rf * hexr, math.sin(a) * rf * hexr
            else:
                lu = lv = 0.0
            q = p0 + tx * lu * size + ty * lv * size
            p, nn = proj(q)
            row.append(len(verts)); verts.append(p + nn * h); uvs2.append((lu, lv))
        idx.append(row)
    # alt halka (kabuğun içine gömülü)
    bot = []
    for j, vi in enumerate(idx[-1]):
        lu, lv = uvs2[vi]; q = p0 + tx * lu * size * 0.97 + ty * lv * size * 0.97
        p, nn = proj(q); bot.append(len(verts)); verts.append(p - nn * 0.02); uvs2.append((lu, lv))
    faces = []
    # merkez → 1. halka
    r1 = idx[1]
    for j in range(len(r1)): faces.append((idx[0][0], r1[j], r1[(j + 1) % len(r1)]))
    def bridge(a, b):
        out = []
        if len(a) == len(b):
            for j in range(len(a)): out.append((a[j], b[j], b[(j + 1) % len(b)], a[(j + 1) % len(a)]))
        else:   # a: n, b: 2n
            for j in range(len(a)):
                out.append((a[j], b[2 * j], b[2 * j + 1], a[(j + 1) % len(a)]))
                out.append((a[(j + 1) % len(a)], b[2 * j + 1], b[(2 * j + 2) % len(b)]))
        return out
    faces += bridge(idx[1], idx[2]) + bridge(idx[2], idx[3]) + bridge(idx[3], bot)
    bc = len(verts); pb, nb = proj(p0); verts.append(pb - nb * 0.03); uvs2.append((0.0, 0.0))
    for j in range(len(bot)): faces.append((bc, bot[(j + 1) % len(bot)], bot[j]))
    uvs = [[uvs2[i] for i in f] for f in faces]
    o = mesh_obj(name, verts, faces, [m], uvs)
    # dışa bakmalı: tepe yüzü elipsoit normali yönünde
    me = o.data; top = me.polygons[0]
    if top.normal.dot(n0) < 0:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return add_mods(o, sub)

def tosbi():
    """Tosbi Dede (~1,2 m): dik duran yaşlı deniz kaplumbağası."""
    SK = m_skin('skin', '#86c99e', '#5ea67e', spot_amt=0.28, scale=4.0)
    SKD = vinyl('skin_lid', '#79bb91', rough=0.4, coat=0.2)
    PL = m_plastron('plastron', '#f6e2a2', '#cfa761')
    DOME = vinyl('dome', '#5e3a22', rough=0.45, coat=0.2)
    PAD = m_radial('pad', '#f0b764', '#d08a45', '#9a5a2c')
    RIM = m_uv_ramp('rim', [(0.0, '#e7b56c'), (0.5, '#d9a05a'), (0.86, '#c98c4c'), (0.93, '#7d4a26'), (1.0, '#e7b56c')], axis='X', scale=22.0,
                    repeat=True, bump=[(0.0, 1.0), (0.86, 1.0), (0.93, 0.0), (1.0, 1.0)])
    WHITE = vinyl('white', '#f6f2ea', rough=0.55, coat=0.1)
    GOLD = vinyl('gold', '#d39a2e', rough=0.22, coat=0.6)
    BLUSH = vinyl('blush', '#ff9d95', rough=0.6, coat=0.0)
    DARK = vinyl('dark', '#3a2722', rough=0.3, coat=0.3)
    NAIL = vinyl('nail', '#f3e6c4', rough=0.35, coat=0.4)
    WOOD = m_wood('cane', '#8a5730', '#b67b45')
    SCARF = m_knit('scarf', '#e5534b', '#fff1d8', stripes=7.0)
    SCARF_T = m_knit('scarf_t', '#e5534b', '#fff1d8', stripes=5.0, axis='X')
    form, fuse, det = [], [], []    # fuse: tek kabuğa örülecek gövde parçaları; form: ayrı kalan biçim parçaları; det: yalnız pişirme

    # ayaklar + bacaklar
    for s in (-1, 1):
        fuse.append(blob('foot%d' % s, (0.15 * s, -0.07, 0.05), (0.105, 0.15, 0.058), SK, rot=(0, 0, s * 14)))
        fuse.append(blob('leg%d' % s, (0.14 * s, -0.01, 0.15), (0.088, 0.088, 0.11), SK))
    # gövde + karın plakası
    body = blob('body', (0, 0, 0.42), (0.27, 0.235, 0.30), SK); fuse.append(body)
    fuse.append(blob('plastron', (0, -0.15, 0.42), (0.215, 0.11, 0.275), PL))
    # kabuk: koyu kubbe (oluk rengi) + kabarık plakalar + kenar halkası
    SC, SR = (0, 0.14, 0.46), (0.34, 0.25, 0.37)
    fuse.append(blob('dome', SC, SR, DOME))
    pads = [(0, 72), (0, 38), (0, 4), (0, -30)] + [(s * 50, e) for s in (-1, 1) for e in (52, 18, -16)] + [(s * 82, e) for s in (-1, 1) for e in (30, -6)]
    for k, (az, el) in enumerate(pads):
        a, e = math.radians(az), math.radians(el)
        d = V((math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)))
        sz = 0.118 if az == 0 else (0.112 if abs(az) < 60 else 0.092)
        fuse.append(pad_on_ellipsoid('pad%d' % k, SC, SR, d, sz, 0.022, PAD, spin=90 if az == 0 else 90))
    fuse.append(ring_mesh('rim', (0, 0.06, 0.465), (1, 0, 0), (0, 0, 1), 0.335, 0.365, 0.05, RIM, n=64, nm=12,
                          minor_fn=lambda u: 0.05 * (0.8 + 0.2 * math.cos(u * math.tau))))   # yanlarda biraz ince
    # boyun + baş + burun
    fuse.append(blob('neck', (0, -0.05, 0.74), (0.13, 0.12, 0.13), SK))
    head = blob('head', (0, -0.08, 0.93), (0.235, 0.22, 0.2), SK); fuse.append(head)
    snout = blob('snout', (0, -0.21, 0.875), (0.155, 0.13, 0.115), SK); fuse.append(snout)
    S = Surf([head, snout])
    HC = V((0, -0.11, 0.91))
    # gözler (biraz küçük, yaşlı ve tatlı) + yarım göz kapağı
    eyes = []
    for s in (-1, 1):
        f, dd, (p, nrm, q) = bead_eye('t%d' % s, S, HC, (0.42 * s, -0.86, 0.33), 0.037, 0.047, 0.024, glint_at=(-0.3, 0.38))
        form += f; det += dd; eyes.append((p, nrm, q))
        qx, qy = q @ V((1, 0, 0)), q @ V((0, 1, 0))
        lid = blob_q('lid%d' % s, p + nrm * 0.016 + qy * 0.026, (0.05, 0.03, 0.03), SKD, q, roll=-s * 10)
        fuse.append(lid)
    # yuvarlak gözlük (çerçeve + köprü + sap)
    rims = []
    for s, (p, nrm, q) in zip((-1, 1), eyes):
        qx, qy = q @ V((1, 0, 0)), q @ V((0, 1, 0))
        cc = p + nrm * 0.03
        form.append(ring_mesh('glass%d' % s, cc, qx, qy, 0.062, 0.058, 0.0085, GOLD, n=40, nm=8))
        rims.append((cc, qx, qy, nrm))
    (cl, qxl, qyl, nl), (cr, qxr, qyr, nr) = rims
    inner_l, inner_r = cl + qxl * 0.062, cr - qxr * 0.062
    mid = (inner_l + inner_r) / 2 + V((0, -0.025, 0.012))
    form.append(tube('bridge', [tuple(inner_l), tuple(mid), tuple(inner_r)], [0.0075, 0.007, 0.0075], GOLD))
    for s, (cc, qx, qy, nrm) in zip((-1, 1), rims):
        outer = cc + qx * 0.062 * s
        e1, _ = S.hit(HC, (0.9 * s, -0.3, 0.32)); e2, _ = S.hit(HC, (1.0 * s, 0.25, 0.3))
        form.append(tube('temple%d' % s, [tuple(outer), tuple(e1 + V((0.012 * s, 0, 0))), tuple(e2 + V((0.006 * s, 0, 0)))], [0.0065, 0.006, 0.005], GOLD))
    # bembeyaz gür kaşlar (dışa doğru sarkık), keçi sakal
    for s in (-1, 1):
        # her kaş 3 kabarık tutam: içte küçük, ortada büyük, dışta aşağı sarkan uç (gözlük çerçevesinin üstünde)
        for k, (dx, dz, r, rl) in enumerate([(0.17, 0.8, 0.022, 0.03), (0.36, 0.86, 0.029, 0.042), (0.56, 0.78, 0.025, 0.038), (0.72, 0.6, 0.018, 0.03)]):
            p, nrm = S.hit(HC, (dx * s, -0.72, dz))
            fuse.append(blob_q('brow%d_%d' % (s, k), p + nrm * r * 0.55, (rl, r * 0.85, r), WHITE, frame(nrm), roll=s * (8 + 22 * k)))
    # yumuşak keçi sakal: çenenin altında kabarık tutamlar (sivri değil, bulut gibi)
    cp, cn = S.hit(V((0, -0.2, 0.86)), (0, -0.5, -0.87))
    for k, (dx, dy, dz, r) in enumerate([(0.0, -0.005, -0.02, 0.05), (-0.04, -0.0, -0.035, 0.036), (0.04, -0.0, -0.035, 0.036),
                                         (0.0, -0.012, -0.07, 0.04), (-0.02, -0.01, -0.1, 0.026), (0.02, -0.01, -0.1, 0.026), (0.0, -0.012, -0.125, 0.02)]):
        fuse.append(blob('beard%d' % k, tuple(cp + V((dx, dy, dz))), (r, r * 0.8, r * 0.95), WHITE))
    # gülümseme, burun delikleri, yanaklar, başta benekler
    SN = Surf([snout]); NC = V((0, -0.21, 0.875))
    det.append(stroke('smile', SN, NC, [((x / 2.0) * 0.62, -1, -0.42 + 0.17 * (x / 2.0) ** 2) for x in range(-2, 3)], [0.008, 0.0095, 0.0105, 0.0095, 0.008], DARK))
    for s in (-1, 1):
        det.append(stroke('dimple%d' % s, SN, NC, [(0.6 * s, -0.9, -0.3), (0.68 * s, -0.85, -0.38)], [0.005, 0.004], DARK))
        det.append(decal('nostril%d' % s, SN, NC, (0.14 * s, -1, 0.22), (0.011, 0.008, 0.005), DARK))
        det.append(decal('blush%d' % s, S, HC, (0.78 * s, -0.62, -0.02), (0.052, 0.033, 0.006), BLUSH))
    # atkı: boyunda halka + önde sarkan uç (saçaklı)
    fuse.append(ring_mesh('scarf', (0, -0.06, 0.745), (1, 0, 0), V((0, 1, 0.22)).normalized(), 0.155, 0.15, 0.048, SCARF, n=48, nm=12,
                          minor_fn=lambda u: 0.048 * (1.0 + 0.12 * math.sin(u * math.tau * 3))))
    tail = [V((0.085, -0.19, 0.71)), V((0.11, -0.25, 0.64)), V((0.125, -0.27, 0.55)), V((0.13, -0.275, 0.46))]
    fuse.append(ribbon('scarf_tail', tail, [0.075, 0.08, 0.08, 0.078], V((0, -1, 0.05)), 0.03, SCARF_T))
    end = tail[-1]
    for k in range(5):
        x = end.x - 0.032 + 0.016 * k
        det.append(tube('fringe%d' % k, [(x, end.y - 0.004, end.z + 0.005), (x + 0.002, end.y - 0.006, end.z - 0.035)], [0.008, 0.006], SCARF_T))
    # kollar: sağ (−X) bastona dayalı, sol (+X) selam veriyor
    fuse.append(tube('arm_r', [(-0.24, -0.02, 0.64), (-0.32, -0.1, 0.6), (-0.385, -0.19, 0.575)], [0.07, 0.062, 0.056], SK))
    fuse.append(blob('hand_r', (-0.4, -0.225, 0.565), (0.062, 0.058, 0.07), SK, rot=(0, 10, 0)))
    fuse.append(tube('arm_l', [(0.24, -0.02, 0.64), (0.34, -0.06, 0.7), (0.41, -0.1, 0.79), (0.43, -0.108, 0.83)], [0.07, 0.062, 0.052, 0.042], SK))
    fuse.append(blob('flip_l', (0.44, -0.11, 0.86), (0.058, 0.044, 0.095), SK, rot=(8, -24, 0)))
    for s in (-1, 1):    # ayakta küçük krem tırnaklar
        for k in range(3):
            a = math.radians(s * 14 + (k - 1) * 22)
            det.append(blob('toe%d%d' % (s, k), (0.15 * s + math.sin(a) * 0.075 + 0.0, -0.07 - math.cos(a) * 0.135, 0.045), (0.022, 0.016, 0.02), NAIL, sub=1, seg=12))
    # baston: yerden ele, üstte kanca
    cane = [(-0.405, -0.235, 0.0), (-0.405, -0.235, 0.3), (-0.405, -0.232, 0.6), (-0.4, -0.232, 0.665), (-0.365, -0.232, 0.70), (-0.325, -0.232, 0.685), (-0.312, -0.232, 0.645)]
    form.append(tube('cane', cane, [0.02, 0.021, 0.022, 0.022, 0.022, 0.021, 0.019], WOOD, res=16))
    det.append(blob('cane_tip', (-0.405, -0.235, 0.012), (0.026, 0.026, 0.016), DARK, sub=1, seg=12))
    def imp(p):   # doku payı: yüz (gözlük, kaş, sakal, atkı) en çok, kabuk sırtı az
        if p.z > 0.7 and p.y < 0.0: return 2.3
        if p.z > 0.7: return 1.2
        if p.y > 0.1: return 0.85
        return 1.0
    return dict(fuse=fuse, form=form, det=det, voxel=0.006, face=HC, imp=imp)

def ribbon(name, pts, widths, facing, thick, m, sub=2):
    """Yassı şerit (atkı ucu): pts boyunca, genişlik widths, yüzü 'facing' yönüne bakar; kalınlık thick. grain uv: X = boy (m), Y = en."""
    pts = [V(p) for p in pts]; facing = V(facing).normalized()
    verts, faces, uvs = [], [], []
    n = len(pts); cols = 4; arc = 0.0
    for i in range(n):
        tg = (pts[min(n - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
        side = tg.cross(facing).normalized()
        if i: arc += (pts[i] - pts[i - 1]).length
        for j in range(cols + 1):
            v = j / cols * 2 - 1
            verts.append(pts[i] + side * v * widths[i] / 2);
    for i in range(n - 1):
        for j in range(cols):
            a = i * (cols + 1) + j
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    # uv
    arcs = [0.0]
    for i in range(1, n): arcs.append(arcs[-1] + (pts[i] - pts[i - 1]).length)
    for i in range(n - 1):
        for j in range(cols):
            uvs.append([(arcs[i], j / cols), (arcs[i], (j + 1) / cols), (arcs[i + 1], (j + 1) / cols), (arcs[i + 1], j / cols)])
    o = mesh_obj(name, verts, faces, [m], uvs)
    return add_mods(o, sub, solid=thick)

# ------------------------------------------------------------------ palmiyeler (Pıtır, Hışır)

def frond(name, base, az, el0, length, width, droop, m, lobes=5, lobe_depth=0.8, fold=0.2, seg=72, cols=6, thick=0.024,
          twist=0.0, sub=2, side_tilt=0.0, sweep=0.55):
    """Kalın vinyl palmiye yaprağı: dipte ince sap, ortada geniş, sivri uç; kenarlar uca doğru süpürülmüş parmak dilimlere bölünmüş.
    el0: başlangıç eğimi (derece, yukarı +), droop: uca kadar toplam aşağı dönüş (derece)."""
    az, el0r, dr = math.radians(az), math.radians(el0), math.radians(droop)
    d0 = V((math.cos(az), math.sin(az), 0)); side0 = V((-math.sin(az), math.cos(az), 0))
    spine, tans, nrms = [], [], []
    p = V(base)
    for i in range(seg + 1):
        s = i / seg
        el = el0r - dr * s ** 1.35
        d = d0 * math.cos(el) + V((0, 0, math.sin(el)))
        nrm = d.cross(side0).normalized()
        if nrm.z < 0 and abs(d.z) < 0.9: nrm = -nrm
        tw = math.radians(twist * s + side_tilt)
        sd = side0 * math.cos(tw) + nrm * math.sin(tw); nr = nrm * math.cos(tw) - side0 * math.sin(tw)
        spine.append(p.copy()); tans.append(d); nrms.append((sd, nr))
        p = p + d * (length / seg)
    s0 = 0.12                                         # sap (dilimsiz) bölümün sonu
    def env(s):                                       # yaprak dış çizgisi (dilimler hariç): dipte ince sap, ortada geniş, sivri uç
        if s < s0: return 0.07 + 0.2 * (s / s0) ** 2
        k = (s - s0) / (1 - s0)
        return max(0.03, 0.27 + 0.73 * math.sin(math.pi * min(0.999, 0.08 + 0.92 * k ** 0.8)) ** 0.75)
    def finger(s):                                    # testere: kenar dilim dibinden (çentik) uca doğru yavaşça yükselir, sonra keskin iner
        if s < s0 or lobes <= 0: return 1.0
        ph = ((s - s0) / (1 - s0) * lobes) % 1.0
        if ph < 0.86: return 1.0 - lobe_depth + lobe_depth * math.sin(math.pi * ph / 0.86) ** 0.55   # yuvarlak uçlu parmak
        return 1.0 - lobe_depth                                                                     # parmaklar arası dar boşluk
    verts, faces, uvs = [], [], []
    for i in range(seg + 1):
        s = i / seg
        sd, nr = nrms[i]
        e = width * env(s)
        w = max(0.006, e * finger(s))
        for j in range(cols + 1):
            v = j / cols * 2 - 1
            lat = v * w
            fwd = sweep * abs(v) ** 1.5 * w * (1 if s > s0 else 0)   # parmaklar uca doğru süpürülür
            pt = spine[i] + sd * lat + tans[i] * fwd - nr * fold * (v * e) ** 2 / max(1e-4, width)
            verts.append(pt)
    for i in range(seg):
        for j in range(cols):
            a = i * (cols + 1) + j
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
            uvs.append([(i / seg, j / cols * 2 - 1), (i / seg, (j + 1) / cols * 2 - 1), ((i + 1) / seg, (j + 1) / cols * 2 - 1), ((i + 1) / seg, j / cols * 2 - 1)])
    o = mesh_obj(name, verts, faces, [m], uvs)
    add_mods(o, sub, solid=thick)
    o.modifiers['solid'].use_even_offset = False      # sivri uçta ve dar dilim dibinde "çivi" çıkmasın
    return o

def coconut(name, loc, r, m, top_m, eye_m, tilt=(0, 0, 0)):
    """Parlak ceviz: hafif yumurta biçimi, üstte sap tacı, altta üç küçük göz (ayrıntı)."""
    o = blob(name, loc, (r, r, r * 1.08), m, rot=tilt)
    cap = blob(name + '_cap', (loc[0], loc[1], loc[2] + r * 1.0), (r * 0.42, r * 0.42, r * 0.16), top_m, sub=2, seg=16)
    det = []
    for k in range(3):
        a = k * math.tau / 3 + 0.4
        det.append(blob(name + '_eye%d' % k, (loc[0] + math.cos(a) * r * 0.22, loc[1] + math.sin(a) * r * 0.22, loc[2] - r * 1.04), (r * 0.09, r * 0.09, r * 0.04), eye_m, sub=1, seg=12))
    return [o, cap], det

def palm_char(kind):
    P = dict(
        pitir=dict(Ht=1.35, rmax=0.32, c_b=0.37, lean=(0.07, -0.03), seg_len=0.12, r_trunk=0.19,
                   trunk=['#9a6234', '#d49b58', '#ecbb78', '#8a5530'], face='#f2cb92', lid='#e2b47a',
                   leaf=('#3c9a3c', '#7cd146', '#d4f27a', '#e9fb9e'), fronds=7, fl=1.35, fw=0.24, el=(48, 62), droop=(112, 132),
                   lobes=8, lobe_depth=0.88, sweep=1.0, nut=('#8b5a2b', '#5d3a1d', '#3b2414'), nuts=3, tuft=True),
        hisir=dict(Ht=1.3, rmax=0.30, c_b=0.35, lean=(-0.04, 0.03), seg_len=0.11, r_trunk=0.185,
                   trunk=['#8a5a3a', '#c2916a', '#d9ab82', '#7a4f33'], face='#ecc8a0', lid='#d9ae86',
                   leaf=('#226f4a', '#3caa6a', '#93d98a', '#bdeca4'), fronds=6, fl=1.2, fw=0.28, el=(25, 38), droop=(115, 130),
                   lobes=5, lobe_depth=0.75, sweep=0.6, nut=('#9fb44a', '#6e7f2c', '#4f5a22'), nuts=2, tuft=False),
    )[kind]
    R = random.Random(7 if kind == 'pitir' else 11)
    form, fuse, det = [], [], []
    H0 = P['Ht']                                                 # halkalı gövdenin üstü (baş şişkinliği buradan başlar)
    c_b, rmax = P['c_b'], P['rmax']
    zc = H0 + c_b * 0.72; top = zc + c_b                          # yüz merkezi, baş tepesi
    lx, ly = P['lean']
    def path(t):
        z = t * top
        u = min(1.0, z / H0)
        # gövde hafif eğik (Pıtır öne-yana neşeli, Hışır geriye çekingen); baş bölgesinde dik
        return V((lx * math.sin(u * math.pi * 0.5) ** 1.3, ly * math.sin(u * math.pi * 0.5), z))
    seg_len, rt = P['seg_len'], P['r_trunk']
    def smax(a, b, k):
        h = max(k - abs(a - b), 0.0) / k
        return max(a, b) + h * h * k * 0.25
    def rad(t, a):
        z = t * top
        if z < 0.16: base = rt * (1 + 0.85 * (1 - z / 0.16) ** 2)     # kök genişlemesi
        else: base = rt * (1 - 0.13 * min(1, (z - 0.16) / max(0.01, H0 - 0.16)))
        if z < H0:
            ph = (z / seg_len) % 1.0
            fade = min(1.0, (H0 - z) / 0.06)
            base *= 1 + (0.16 * ph ** 2.2 - 0.05) * fade            # her halka üstte şişkin, dipte boğum ("üst üste kâseler")
        bulb = rmax * math.sqrt(max(0.0, 1 - ((z - zc) / c_b) ** 2))
        r = bulb if z > zc else smax(base if z < H0 + 0.1 else 0.0, bulb, 0.05)
        r *= 1 - 0.06 * max(0.0, math.cos(a)) * max(0.0, 1 - abs(z - zc) / c_b)   # yüz biraz yassı
        return max(0.012, r)
    TR = m_trunk('trunk_' + kind, P['trunk'], P['face'], seg_len, H0)
    trunk, pts, arc = lathe('trunk', path, rad, 120, 24, TR, cap_top=True)
    fuse.append(trunk)
    S = Surf([trunk])
    FC = path(zc / top) + V((0, 0.02, 0))                         # yüz merkezi (baş şişkinliğinin ortası)
    # kök "parmakları"
    ROOTM = vinyl('root_' + kind, P['trunk'][0], rough=0.5, coat=0.15)
    for k in range(5):
        a = k * math.tau / 5 + 0.3
        fuse.append(blob('root%d' % k, (math.sin(a) * rt * 1.25, -math.cos(a) * rt * 1.25, 0.03), (0.075, 0.075, 0.05), ROOTM, rot=(0, 0, -math.degrees(a))))
    # taç: ortada lifli yaprak dibi + yapraklar
    cz = top - 0.06; ctop = path(1.0)
    BOOT = vinyl('boot_' + kind, '#7a5532' if kind == 'pitir' else '#6b4a33', rough=0.6, coat=0.1)
    fuse.append(blob('boot', (ctop.x, ctop.y, cz + 0.02), (0.17, 0.17, 0.09), BOOT))
    LEAF = m_leaf('leaf_' + kind, *P['leaf'])
    LEAFB = vinyl('leafb_' + kind, P['leaf'][0], rough=0.4, coat=0.2)
    nf = P['fronds']
    # yapraklar sağ-sol aynalı çiftler (aynı rastgele değerler): modelin yatay sınır kutusu gövde eksenine ortalı kalır — oyun
    # (RealAssets.Fit) modeli sınır kutusunun ortasına oturtur ve Resident3D bu noktanın çevresinde döner (gövde kaymasın)
    pairs = [(R.uniform(-6, 6), R.uniform(*sorted(P['el'])), R.uniform(*sorted(P['droop'])), P['fl'] * R.uniform(0.9, 1.08),
              P['fw'] * R.uniform(0.92, 1.08), R.uniform(-12, 12)) for _ in range((nf + 1) // 2)]
    for f in range(nf):
        k = min(f, nf - 1 - f); sg = 1 if f <= nf - 1 - f else -1
        daz, el, dr, ln, fw, tw = pairs[k]
        if f == nf - 1 - f: daz = tw = 0.0                        # tam arkadaki tek yaprak düz
        az = 320 + f * 260 / (nf - 1) + daz * sg                   # önde (−Y = 270°) 100° boşluk: sarkan yaprak yüzü örtmez
        base = V((ctop.x, ctop.y, cz + 0.06)) + V((math.cos(math.radians(az)), math.sin(math.radians(az)), 0)) * 0.06
        form.append(frond('frond%d' % f, base, az, el, ln, fw, dr, LEAF, lobes=P['lobes'], lobe_depth=P['lobe_depth'],
                          sweep=P['sweep'], twist=tw * sg))
    if P['tuft']:   # Pıtır: tepede dik perçem (heyecanlı)
        for k, (az, el, ln) in enumerate([(250, 86, 0.62), (310, 76, 0.52), (190, 78, 0.48)]):
            base = V((ctop.x, ctop.y, cz + 0.08))
            form.append(frond('tuft%d' % k, base, az, el, ln, 0.11, 55, LEAF, lobes=4, lobe_depth=0.85, sweep=0.9, seg=40, cols=6, thick=0.022))
    # cevizler (arkada / yanlarda: yüzü kapatmaz)
    NUT = vinyl('nut_' + kind, P['nut'][0], rough=0.3, coat=0.5); NCAP = vinyl('ncap_' + kind, P['nut'][1], rough=0.5, coat=0.1)
    NEYE = vinyl('neye', P['nut'][2], rough=0.4, coat=0.2)
    # ceviz salkımı: tacın altında arkada, tek yana kayık (önden simetrik iki top "kulak" gibi okunuyordu); Pıtır 3, Hışır 2
    if P['nuts'] == 3: bunch = [(60, 0.28, 0.0), (88, 0.29, -0.03), (74, 0.24, -0.13)]
    else: bunch = [(102, 0.28, -0.01), (124, 0.27, -0.1)]
    for k, (az, rr, dz) in enumerate(bunch):
        a = math.radians(az)
        loc = (ctop.x + math.cos(a) * rr, ctop.y + math.sin(a) * rr, cz + dz)
        f, dd = coconut('nut%d' % k, loc, 0.097, NUT, NCAP, NEYE, tilt=(R.uniform(-15, 15), R.uniform(-15, 15), 0)); form += f; det += dd
    # yüz
    BLK = glossy_black(); BL = vinyl('blush_' + kind, '#ff8f9a' if kind == 'hisir' else '#ff9a86', rough=0.6, coat=0.0)
    DK = vinyl('mouth', '#5b2330', rough=0.3, coat=0.3); TG = vinyl('tongue', '#ff7a8a', rough=0.4, coat=0.2)
    BRW = vinyl('brow_' + kind, '#6a3f22', rough=0.4, coat=0.2)
    LID = vinyl('lid_' + kind, P['lid'], rough=0.4, coat=0.25)
    if kind == 'pitir':
        for s in (-1, 1):
            f, dd, (p, nrm, q) = bead_eye('p%d' % s, S, FC, (0.38 * s, -0.92, 0.3), 0.05, 0.066, 0.03, glint_at=(-0.32, 0.4), sink=0.3)
            form += f; det += dd
            qx, qy = q @ V((1, 0, 0)), q @ V((0, 1, 0))
            det.append(blob_q('sparkle%d' % s, p + nrm * 0.045 + qx * 0.02 + qy * -0.028, (0.008, 0.008, 0.004), glint(), q, sub=1, seg=10))
            # kalkık kaşlar (heyecan)
            det.append(stroke('brow%d' % s, S, FC, [(0.22 * s, -0.9, 0.62), (0.38 * s, -0.85, 0.7), (0.54 * s, -0.78, 0.64)], [0.011, 0.014, 0.01], BRW, lift=0.006))
            det.append(decal('blush%d' % s, S, FC, (0.66 * s, -0.72, -0.08), (0.055, 0.034, 0.006), BL))
        # açık gülen ağız (D): üstü hafif gülümseyen düz kenar, altı yuvarlak; içinde dil
        a, b = 0.075, 0.062
        m_top = [(-a + 2 * a * k / 10, 0.014 * ((-a + 2 * a * k / 10) / a) ** 2 - 0.004) for k in range(11)]
        m_bot = [(a * math.cos(math.pi * k / 18), -b * math.sin(math.pi * k / 18) - 0.004) for k in range(1, 18)]
        det.append(shape_decal('mouth', S, FC, (0, -1, -0.34), m_top + m_bot, DK, lift=0.003))
        p, nrm = S.hit(FC, (0, -1, -0.34)); q = frame(nrm); qy = q @ V((0, 1, 0))
        det.append(blob_q('tongue', p + nrm * 0.0045 - qy * 0.042, (0.038, 0.019, 0.004), TG, q, sub=1, seg=16))
        # neşeli yaprak elleri: sağ (−X) havada sallıyor, sol yana açık
        for s, (az, el, dr, ln) in [(-1, (200, 66, 62, 0.5)), (1, (340, 22, 58, 0.46))]:
            bz = H0 - 0.02
            b = path(bz / top) + V((s * rt * 0.95, 0, 0))
            fuse.append(blob('shoulder%d' % s, tuple(b), (0.045, 0.045, 0.04), LEAFB))
            form.append(frond('hand%d' % s, b, az, el, ln, 0.1, dr, LEAF, lobes=3, lobe_depth=0.8, sweep=0.9, seg=36, cols=6, thick=0.024))
    else:
        for s in (-1, 1):
            # aşağı-yana bakan gözler (ışık noktası altta-yanda), yarı kapalı kapak
            f, dd, (p, nrm, q) = bead_eye('h%d' % s, S, FC, (0.37 * s, -0.93, 0.2), 0.042, 0.054, 0.026, glint_at=(-0.3, -0.05), glint2=False, sink=0.35)
            form += f; det += dd
            qx, qy = q @ V((1, 0, 0)), q @ V((0, 1, 0))
            fuse.append(blob_q('lid%d' % s, p + nrm * 0.014 + qy * 0.04, (0.052, 0.028, 0.03), LID, q, roll=-s * 16))
            # endişeli kaşlar (içte yukarı)
            det.append(stroke('brow%d' % s, S, FC, [(0.18 * s, -0.9, 0.7), (0.34 * s, -0.86, 0.6), (0.5 * s, -0.8, 0.46)], [0.01, 0.012, 0.009], BRW, lift=0.006))
            det.append(decal('blush%d' % s, S, FC, (0.62 * s, -0.75, -0.1), (0.07, 0.042, 0.007), BL))
            for k in range(3):   # yanakta küçük utanç çizgileri
                det.append(stroke('shy%d%d' % (s, k), S, FC, [((0.55 + 0.07 * k) * s, -0.8, -0.03), ((0.59 + 0.07 * k) * s, -0.78, -0.15)], [0.0045, 0.0035], vinyl('shy', '#e05a70', 0.5, 0.0), lift=0.011))
        # küçük kapalı gülümseme
        det.append(stroke('smile', S, FC, [(-0.16, -1, -0.36), (-0.07, -1, -0.43), (0.0, -1, -0.44), (0.07, -1, -0.43), (0.16, -1, -0.36)],
                          [0.006, 0.008, 0.008, 0.008, 0.006], DK))
        # çekingen yaprak elleri: iki yandan öne, gövdenin önünde birleşir
        for s in (-1, 1):
            bz = H0 - 0.16
            b = path(bz / top) + V((s * rt * 0.95, -0.02, 0))
            fuse.append(blob('shoulder%d' % s, tuple(b), (0.045, 0.045, 0.04), LEAFB))
            form.append(frond('hand%d' % s, b, 270 - s * 60, -12, 0.46, 0.11, 26, LEAF, lobes=3, lobe_depth=0.7, sweep=0.6, seg=36, cols=6, thick=0.024,
                              side_tilt=s * 35))
    def imp(p):   # doku payı: yüz en çok; yapraklar/eller/cevizler az (düz geçiş renkleri)
        r = math.hypot(p.x - ctop.x, p.y - ctop.y)
        if abs(p.z - zc) < c_b * 0.9 and r < rmax + 0.07:
            return 2.8 if p.y < ctop.y + 0.02 else 1.2
        if p.z > top - 0.12 or r > rmax + 0.1: return 0.55
        return 0.8
    return dict(fuse=fuse, form=form, det=det, voxel=0.009, face=FC, imp=imp)

def m_trunk(name, cols, face, seg_len, H0):
    """Halkalı gövde: her halkanın dibi koyu oluk, üstü açık; baş bölgesinde (yay uzunluğu > H0) düz yüz rengi. grain uv: Y = yay uzunluğu."""
    dark, mid, light, groove = cols
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        mu = n.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 1.0 / seg_len; l.new(sep.outputs['Y'], mu.inputs[0])
        fr = n.new('ShaderNodeMath'); fr.operation = 'FRACT'; l.new(mu.outputs[0], fr.inputs[0])
        rp = ramp(nt, [(0.0, groove), (0.1, dark), (0.45, mid), (0.9, light), (1.0, groove)]); l.new(fr.outputs[0], rp.inputs['Fac'])
        # ince boyuna lif (çok hafif)
        mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (60, 3, 1); l.new(uv.outputs[0], mp.inputs['Vector'])
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 2; l.new(mp.outputs[0], nz.inputs['Vector'])
        fb = n.new('ShaderNodeMix'); fb.data_type = 'RGBA'; fb.blend_type = 'MULTIPLY'; fb.inputs['Factor'].default_value = 0.12
        l.new(rp.outputs[0], fb.inputs[6]); l.new(nz.outputs['Color'], fb.inputs[7])
        # baş bölgesi: yüz rengi (yumuşak geçiş)
        hm = n.new('ShaderNodeMapRange'); hm.inputs['From Min'].default_value = H0 - 0.03; hm.inputs['From Max'].default_value = H0 + 0.07
        l.new(sep.outputs['Y'], hm.inputs['Value'])
        mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb(face)
        l.new(hm.outputs[0], mx.inputs['Factor']); l.new(fb.outputs[2], mx.inputs[6]); l.new(mx.outputs[2], bsdf.inputs['Base Color'])
        # halka oluğu tümseği (gövdede)
        br = ramp(nt, [(0.0, '#000000'), (0.12, '#ffffff'), (0.9, '#ffffff'), (1.0, '#000000')]); l.new(fr.outputs[0], br.inputs['Fac'])
        gm = n.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; l.new(br.outputs[0], gm.inputs[0])
        inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; l.new(hm.outputs[0], inv.inputs[1]); l.new(inv.outputs[0], gm.inputs[1])
        bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.45; bp.inputs['Distance'].default_value = 0.01
        l.new(gm.outputs[0], bp.inputs['Height']); l.new(bp.outputs[0], bsdf.inputs['Normal'])
        bsdf.inputs['Roughness'].default_value = 0.5; bsdf.inputs['Coat Weight'].default_value = 0.2
    return nodes_mat(name, b)

BUILDERS = {'tosbi': (tosbi, 8500, 1024), 'pitir': (lambda: palm_char('pitir'), 8800, 1024), 'hisir': (lambda: palm_char('hisir'), 8400, 1024)}

# ------------------------------------------------------------------ hedef (oyun) ağı + pişirme

def _copy_obj(o, sub=1):
    c = o.copy()
    if o.data is not None: c.data = o.data.copy()
    bpy.context.scene.collection.objects.link(c)
    for md in c.modifiers:
        if md.type == 'SUBSURF': md.levels = min(md.levels, sub); md.render_levels = md.levels
    return c

def _apply_join(objs, name):
    dg = bpy.context.evaluated_depsgraph_get(); parts = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg); me.transform(o.matrix_world); me.materials.clear()
        p = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(p); parts.append(p)
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1: bpy.ops.object.join()
    return bpy.context.view_layer.objects.active

def _tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

def _decimate(o, target):
    cur = _tris(o)
    if cur > target:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = target / cur; d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
    return _tris(o)

EYE_TRIS = 300   # her göz boncuğu hedefte bu kadar üçgenle yuvarlak kalır (oran ile indirgemede köşeli görünüyordu)

def make_low(spec, target):
    """Hedef ağ: gövde parçaları voksel ile tek kabuk (iç yüzeyler gider), diğer biçim parçaları ayrı; bütçe alan oranıyla paylaşılır.
    Göz boncukları kendi sabit payıyla (yüzün en önemli yeri)."""
    eyes = [o for o in spec['form'] if o.name.startswith('eye_')]
    rest = [o for o in spec['form'] if o not in eyes]
    eye_lows = []
    for o in eyes:
        c = _copy_obj(o, 1); e = _apply_join([c], 'low_eye'); _decimate(e, EYE_TRIS); eye_lows.append(e)
    budget = target - sum(_tris(e) for e in eye_lows)
    fuse = _apply_join([_copy_obj(o, 1) for o in spec['fuse']], 'low_fuse')
    bpy.ops.object.select_all(action='DESELECT'); fuse.select_set(True); bpy.context.view_layer.objects.active = fuse
    r = fuse.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = spec['voxel']; r.adaptivity = 0.0; r.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier='rm')
    parts = [fuse]
    if rest:
        parts.append(_apply_join([_copy_obj(o, 1) for o in rest], 'low_form'))
    area = [sum(p.area for p in o.data.polygons) for o in parts]
    tot = sum(area)
    # ince ayrıntılı ayrı parçalar (yaprak dilimleri, gözlük) alanlarına göre biraz daha fazla pay alır; toplam = bütçe
    fs = min(0.75, area[1] / tot * 1.25) if len(parts) > 1 else 0.0
    for o, share in zip(parts, (1.0 - fs, fs)):
        _decimate(o, int(budget * share * 0.985))
    parts += eye_lows
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    low = bpy.context.view_layer.objects.active; low.name = 'low'
    for p in low.data.polygons: p.use_smooth = True
    return low

def unwrap(ob, imp=None, angle=66):
    """UV: önem gruplarına (imp: yüz, gövde, yaprak …) göre ayrı ayrı açılır (bir ada iki grubu kapsamasın), adalar aynı doku
    yoğunluğuna eşitlenir, sonra her ada kendi grubunun katıyla büyütülüp hepsi yeniden yerleştirilir."""
    from bpy_extras import bmesh_utils
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    me = ob.data
    for l in list(me.uv_layers): me.uv_layers.remove(l)
    me.uv_layers.active = me.uv_layers.new(name='UVMap')
    fimp = [round(imp(ob.matrix_world @ p.center), 3) if imp else 1.0 for p in me.polygons]
    groups = sorted(set(fimp))
    bpy.ops.object.mode_set(mode='EDIT')
    for g in groups:
        bm = bmesh.from_edit_mesh(me); bm.faces.ensure_lookup_table()
        for f in bm.faces: f.select_set(fimp[f.index] == g)
        bmesh.update_edit_mesh(me)
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    if imp and len(groups) > 1:
        bm = bmesh.from_edit_mesh(me); lay = bm.loops.layers.uv.active; bm.faces.ensure_lookup_table()
        for isl in bmesh_utils.bmesh_linked_uv_islands(bm, lay):
            a = sum(f.calc_area() for f in isl) or 1e-9
            k = sum(fimp[f.index] * f.calc_area() for f in isl) / a
            if abs(k - 1.0) < 1e-3: continue
            us = [l[lay].uv.copy() for f in isl for l in f.loops]
            cu = sum(u.x for u in us) / len(us); cv = sum(u.y for u in us) / len(us)
            for f in isl:
                for l in f.loops:
                    u = l[lay].uv; l[lay].uv = (cu + (u.x - cu) * k, cv + (u.y - cv) * k)
        bmesh.update_edit_mesh(me)
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='SCALED', margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')

def bake_export(path_noext, high, L, size=1024, imp=None, cage=0.025, ray=0.08, ao_strength=0.45, ao_dist=0.18, margin=8):
    """proxy_bake.export_proxy ile aynı pişirme (renk + yumuşak AO + teğet normal, yüksek → hedef), farkı uv: yüz/göz adaları
    büyütülüp yeniden yerleştirilir (imp). Çıktı: <yol>.fbx, _basecolor.png, _normal.png."""
    import numpy as np
    import proxy_bake as PB
    from PIL import Image
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    H = PB._join(high, 'high'); PB._remap_coords(H)
    L.name = 'model'
    unwrap(L, imp)
    bmat = bpy.data.materials.new('bake'); bmat.use_nodes = True; L.data.materials.append(bmat)
    tex = bmat.node_tree.nodes.new('ShaderNodeTexImage'); bmat.node_tree.nodes.active = tex
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_shadow', 'visible_volume_scatter'):
        if hasattr(L, attr): setattr(L, attr, False)
    bk = sc.render.bake
    bk.use_selected_to_active = True; bk.cage_extrusion = cage; bk.max_ray_distance = ray; bk.margin = margin; bk.use_clear = True
    def run(kind, colorspace='sRGB'):
        img = bpy.data.images.new(kind, size, size, alpha=False, float_buffer=True)
        img.colorspace_settings.name = 'Non-Color' if colorspace != 'sRGB' else 'Linear Rec.709'
        tex.image = img
        bpy.ops.object.select_all(action='DESELECT'); H.select_set(True); L.select_set(True); bpy.context.view_layer.objects.active = L
        if kind == 'col':
            undo = PB._emission_swap(H.data.materials); bpy.ops.object.bake(type='EMIT'); PB._emission_restore(undo)
        elif kind == 'ao':
            sc.world.light_settings.distance = ao_dist; bpy.ops.object.bake(type='AO')
        else:
            bk.normal_space = 'TANGENT'; bk.normal_r = 'POS_X'; bk.normal_g = 'POS_Y'; bk.normal_b = 'POS_Z'
            bpy.ops.object.bake(type='NORMAL')
        return np.array(img.pixels[:], np.float32).reshape(size, size, 4)
    col = run('col'); ao = run('ao'); nrm = run('nrm', 'Non-Color')
    a = 1.0 - ao_strength * (1.0 - ao[..., :1])
    lin = np.clip(col[..., :3] * a, 0, 1)
    srgb_ = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    Image.fromarray((np.clip(srgb_, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_noext + '_basecolor.png', optimize=True)
    n = nrm[..., :3]
    Image.fromarray((np.clip(n, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_noext + '_normal.png', optimize=True)
    for k in [k for k in L.data.attributes.keys() if k in ('ocoord', 'gcoord')]: L.data.attributes.remove(L.data.attributes[k])
    L.data.materials.clear()
    bpy.data.objects.remove(H)
    bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); bpy.context.view_layer.objects.active = L
    bpy.ops.export_scene.fbx(filepath=path_noext + '.fbx', use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False,
                             use_tspace=True)
    return _tris(L)

def construct(name):
    """Modeli kurar; eğriler meshe çevrilir, her parçada tek uv katmanı 'grain' kalır (birleştirmede katmanlar karışmasın)."""
    sc = kit.reset()
    for o in [o for o in sc.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
    spec = BUILDERS[name][0]()
    names = {k: [o.name for o in spec[k]] for k in ('fuse', 'form', 'det')}
    kit.to_mesh_all()
    for k in names: spec[k] = [bpy.data.objects[n] for n in names[k]]
    for k in names:
        for o in spec[k]:
            uv = o.data.uv_layers
            keep = 'grain' if 'grain' in uv else (uv[0].name if len(uv) else None)
            for nm in [l.name for l in uv if l.name != keep]: uv.remove(uv[nm])
            if keep is None: uv.new(name='grain')
            else: uv[keep].name = 'grain'
    return sc, spec

def build(name, out_dir):
    fn, target, size = BUILDERS[name]
    sc, spec = construct(name)
    low = make_low(spec, target)
    high = spec['fuse'] + spec['form'] + spec['det']
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'res_' + name)
    tris = bake_export(path, high, low, size=size, imp=spec.get('imp'))
    print('YAZILDI', path, 'üçgen', tris, flush=True)
    return tris

# ------------------------------------------------------------------ önizleme

def studio(sc, target=(0, 0, 0.6), sun=3.0):
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = srgb('#d6ecfb'); bg.inputs['Strength'].default_value = 0.85
    s = bpy.data.lights.new('sun', 'SUN'); s.energy = sun; s.angle = math.radians(6); s.color = (1.0, 0.96, 0.9)
    so = bpy.data.objects.new('sun', s); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(-38))
    f = bpy.data.lights.new('fill', 'AREA'); f.energy = 300; f.size = 5; f.color = (1.0, 0.88, 0.92)
    fo = bpy.data.objects.new('fill', f); sc.collection.objects.link(fo); fo.location = (4, -4, 2.5)
    fo.rotation_euler = (V(target) - fo.location).to_track_quat('-Z', 'Y').to_euler()

def render_cfg(sc, w, h, samples=32):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 3
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.3
    sc.render.film_transparent = False

def cam_shot(sc, path, target, dist, yaw, pitch, lens=50, ortho=None):
    cam = sc.camera
    if cam is None:
        c = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', c); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = lens
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho: cam.data.ortho_scale = ortho
    t = V(target); y = math.radians(yaw); p = math.radians(pitch)
    cam.location = t + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

def draft(names, out):
    os.makedirs(out, exist_ok=True)
    for n in names:
        sc, spec = construct(n)
        render_cfg(sc, 900, 900, 24)
        objs = spec['fuse'] + spec['form'] + spec['det']
        zs = [ (o.matrix_world @ V(c)).z for o in objs if o.type == 'MESH' for c in o.bound_box]
        hgt = max(zs)
        studio(sc, (0, 0, hgt * 0.55))
        g = kit.ground(4, '#e8d9b0')
        for yaw, tag in ((-28, 'a'), (90, 'b'), (180, 'c')):
            cam_shot(sc, os.path.join(out, f'draft_{n}_{tag}.png'), (0, 0, hgt * 0.52), hgt * 2.6, yaw, 10, lens=50)
        fc = spec['face']
        cam_shot(sc, os.path.join(out, f'draft_{n}_face.png'), (fc.x, fc.y, fc.z), 1.25, -14, 6, lens=50)
        print('draft', n, 'boy', round(hgt, 3), flush=True)

def load_game(name, height=None):
    """Oyundaki FBX + dokular (taban renk + normal). height: hedef boy (Kıskaç oyunda 1,25 m)."""
    d = os.path.join(ENV, name)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(d, name + '.fbx'))
    obs = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
    o = obs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for x in obs: x.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value = 0.45; p.inputs['Coat Weight'].default_value = 0.15
    base = next((os.path.join(d, name + '_basecolor' + e) for e in ('.png', '.jpg') if os.path.exists(os.path.join(d, name + '_basecolor' + e))), None)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(base); nt.links.new(t.outputs[0], p.inputs['Base Color'])
    nrm = next((os.path.join(d, name + '_normal' + e) for e in ('.png', '.jpg') if os.path.exists(os.path.join(d, name + '_normal' + e))), None)
    if nrm:
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(nrm); n.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(n.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], p.inputs['Normal'])
    o.data.materials.clear(); o.data.materials.append(m)
    for pl in o.data.polygons: pl.use_smooth = True
    bb = [o.matrix_world @ V(c) for c in o.bound_box]
    lo = V((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))); hi = V((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    s = (height / (hi.z - lo.z)) if height else 1.0
    o.scale = (s, s, s); o.location = (-(lo.x + hi.x) / 2 * s, -(lo.y + hi.y) / 2 * s, -lo.z * s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o, _tris(o), (hi.z - lo.z) * s

def preview(names, out):
    """Her adalı (oyundaki dosyadan) Kıskaç'ın yanında (Kıskaç oyundaki boyu 1,25 m): dik izdüşümlü döner tabla — 3/4 ön, yan, 3/4 arka
    (ölçek/üslup karşılaştırması, perspektif bozmaz) + yakın yüz + oyun boyutu (küçük, oyun kamerasına yakın açı)."""
    from PIL import Image
    os.makedirs(out, exist_ok=True)
    for n in names:
        sc = kit.reset(); render_cfg(sc, 900, 640, 32)
        for o in list(sc.objects):
            if o.type == 'LIGHT': bpy.data.objects.remove(o)
        k, ktris, kh = load_game('res_kiskac', 1.25)
        r, rtris, rh = load_game('res_' + n)
        gap = 0.75 if n == 'tosbi' else 1.0
        k.location.x = -gap; r.location.x = gap * 0.8
        hgt = max(kh, rh)
        studio(sc, (0, 0, hgt * 0.5))
        kit.ground(8, '#ead9b2')
        shots = []
        for yaw, tag in ((-32, 'a'), (90, 'b'), (148, 'c')):
            p = os.path.join(out, f'_pv_{n}_{tag}.png'); shots.append(p)
            k.rotation_euler = (0, 0, math.radians(-yaw)); r.rotation_euler = (0, 0, math.radians(-yaw))
            cam_shot(sc, p, (0, 0, hgt * 0.52), 12, 0, 8, ortho=max(hgt * 1.25 * 900 / 640, 3.4))
        k.rotation_euler = r.rotation_euler = (0, 0, 0)
        # yakın yüz (pişmiş doku ve normal haritası denetimi)
        pf = os.path.join(out, f'_pv_{n}_face.png'); shots.append(pf)
        fz = {'tosbi': 0.92, 'pitir': 1.62, 'hisir': 1.55}.get(n, rh * 0.7)
        cam_shot(sc, pf, (r.location.x, -0.1, fz), 1.5, -18, 6, lens=50)
        # oyun boyutu: uzaktan, küçük (oyun kamerası B'ye yakın: yukarıdan ~24°)
        sc.render.resolution_x, sc.render.resolution_y = 300, 214
        pg = os.path.join(out, f'_pv_{n}_game.png'); shots.append(pg)
        cam_shot(sc, pg, (0, 0, hgt * 0.4), 11, -20, 24, lens=50)
        ims = [Image.open(p).convert('RGB') for p in shots]
        w0, h0 = ims[0].size
        sheet = Image.new('RGB', (w0 * 3, h0 * 2), (255, 255, 255))
        for i, im in enumerate(ims[:4]): sheet.paste(im, ((i % 3) * w0, (i // 3) * h0))
        g = ims[4].resize((ims[4].width * 3, ims[4].height * 3), Image.NEAREST)
        sheet.paste(g, (w0 + (w0 - g.width) // 2, h0 + (h0 - g.height) // 2))
        sp = os.path.join(out, f'preview_{n}.png'); sheet.save(sp)
        for p in shots: os.remove(p)
        print('önizleme', sp, 'Kıskaç üçgen', ktris, n, 'üçgen', rtris, 'boy', round(rh, 3), flush=True)

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    cmd = args[0] if args else 'build'
    if cmd == 'build':
        names = args[1:] or list(BUILDERS)
        for n in names:
            stage = os.environ.get('POFI_STAGE', '/tmp/pofi_residents')
            build(n, os.path.join(stage, n))
            import shutil
            dst = os.path.join(ENV, 'res_' + n); os.makedirs(dst, exist_ok=True)
            for f in os.listdir(dst):
                if not f.endswith('.meta'): os.remove(os.path.join(dst, f))
            for suf in ('.fbx', '_basecolor.png', '_normal.png'):
                shutil.copy(os.path.join(stage, n, 'res_' + n + suf), os.path.join(dst, 'res_' + n + suf))
            print('OK', n, dst, flush=True)
    elif cmd == 'draft':
        draft(args[2:] or list(BUILDERS), args[1])
    elif cmd == 'preview':
        preview(args[2:] or list(BUILDERS), args[1])
