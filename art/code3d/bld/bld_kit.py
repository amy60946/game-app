# Yapıların oyun modeli hattı (24 Ekim 2026; kullanıcı: "haritadaki kulübe, sirk, mağaza, ev gibi bütün yapılar ayrıntılı ve ada
# hayatına uygun eskitmeli olsun"). Eski yol (kit.export_baked_fbx, assets_town.py ana bölümü): bütün yapı tek ağa birleşip 6–10 bin
# üçgene KÜRESEL sadeleşiyor, yalnız renk + AO pişiyordu → tahta damarı, çivi, yosun, kiremit kenarı, halat burgusu eriyordu; normal
# haritası yoktu. Tapınaktaki yol (v6/temple_game.py) genelleştirildi:
#   kaynak (high) = ayrıntılı taslak: assets_town / house_cottage yapıcıları + bld/<ad>.py eskitme eklemeleri (tam çözünürlük);
#   hedef (low)   = AYNI ağ; yalnız eğri/yoğun parçalar kendi içinde sadeleşir (decim tablosu), görünmeyen yüzler silinir,
#                   UV adaları önem katsayısıyla büyür (weights tablosu; aşağı bakan yüz ×0,45), adalar sıkı paketlenir;
#   pişirme       = v6/proxy_bake.export_proxy: renk × yumuşak AO + teğet uzayı normal haritası, ada kenarı taşırma (dikiş yok).
# Çıktı: <klasör>/<ad>.fbx, <ad>_basecolor.png, <ad>_normal.png (eksen/ölçek eski FBX ile aynı: -Z ileri, Y yukarı, dünya koordinatı).
# Oyuna: export_game.py (ASSETS: betik bld/<ad>.py). Önizleme: render_low() (yalnız oyun modeli + dokular, Cycles).
import os, sys, re, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, '..'), os.path.join(HERE, '..', 'v6')):
    if p not in sys.path: sys.path.insert(0, p)
import bpy, bmesh
import proxy_bake as PB


def _key(name):
    return re.sub(r'\.\d+$', '', name)


def _lookup(table, name, default):
    k = _key(name)
    for pat, v in table:
        if re.search(pat, k): return v
    return default


def prepare():
    """Yapıcıdan sonra: eğriler ağa döner, 'grain' UV'si olmayan ağlara eklenir (assets_town malzemeleri ahşap damarını ondan okur)."""
    import kit
    kit.to_mesh_all()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and 'grain' not in o.data.uv_layers: kit.grain_uv(o)
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def build_low(high, decim=(), weights=(), down=0.45, default_weight=1.0):
    """Taslak nesnelerinden oyun hedefi (temple_game.build_low gibi): aynı ağ (değiştiriciler uygulanmış), decim'de eşleşen parçalar
    kendi içinde o oranda sadeleşir; her yüze UV katsayısı ('uvw'; aşağı bakan yüz × down); hepsi üçgen.
    decim / weights: [(düzenli ifade, değer), …] — nesne adına (sondaki .001 atılır) ilk eşleşen."""
    dg = bpy.context.evaluated_depsgraph_get(); out = []
    col = bpy.context.scene.collection
    for o in high:
        if o.type != 'MESH': continue
        ratio = _lookup(decim, o.name, 1.0)
        if ratio < 1.0:
            d = o.modifiers.new('dec_low', 'DECIMATE'); d.ratio = ratio; d.use_collapse_triangulate = True
            dg.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        if ratio < 1.0:
            o.modifiers.remove(o.modifiers['dec_low']); dg.update()
        if len(me.polygons) == 0:
            bpy.data.meshes.remove(me); continue
        c = bpy.data.objects.new(o.name + '_low', me); c.matrix_world = o.matrix_world.copy(); col.objects.link(c)
        w = _lookup(weights, o.name, default_weight)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        lay = bm.faces.layers.float.new('uvw'); bm.normal_update()
        mw3 = c.matrix_world.to_3x3()
        for f in bm.faces:
            nz = (mw3 @ f.normal).normalized().z if f.normal.length > 0 else 0.0
            f[lay] = w * (down if nz < -0.5 else 1.0)
        bm.to_mesh(me); bm.free()
        out.append(c)
    return out


def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).to_mesh(); n += sum(len(p.vertices) - 2 for p in me.polygons); o.evaluated_get(dg).to_mesh_clear()
    return n


def bake(out_dir, name, high, decim=(), weights=(), tex=1024, budget=None, ao_dist=0.5, ao_strength=0.6, cage=0.03, ray=0.12, **kw):
    """high → oyun modeli. budget: üçgen üst sınırı (aşılırsa hedef bütünüyle o sınıra iner — son çare; önce decim tablosunu ayarla).
    Döner: üçgen sayısı."""
    os.makedirs(out_dir, exist_ok=True)
    tex = int(os.environ.get('POFI_TEX', '0') or 0) or tex
    low = build_low(high, decim, weights)
    tris = PB.export_proxy(os.path.join(out_dir, name), high, low, target=budget, size=tex, nsize=tex, cage=cage, ray=ray,
                           cull_hidden=True, uv_weight='uvw', dilate=16, ao_dist=ao_dist, ao_strength=ao_strength, **kw)
    print(name, 'üçgen', tris, flush=True)
    return tris


def render_low(fbx_noext, png, yaw=35.0, pitch=24.0, dist=None, size=(900, 700), target=None, lens=50):
    """Oyun modeli önizlemesi: FBX + _basecolor + _normal (oyundaki gibi tek doku), güneş + gök ışığı, Cycles (bu ortamda Workbench yok).
    dist None → sınır kutusuna göre. Tasarım denetimi ve önce/sonra kareleri için."""
    import kit
    from mathutils import Vector as V
    kit.reset()
    bpy.ops.import_scene.fbx(filepath=fbx_noext + '.fbx')
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    m = bpy.data.materials.new('game'); m.use_nodes = True; nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.8
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = bpy.data.images.load(fbx_noext + '_basecolor.png')
    nt.links.new(tc.outputs['Color'], bsdf.inputs['Base Color'])
    if os.path.exists(fbx_noext + '_normal.png'):
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(fbx_noext + '_normal.png'); tn.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    for o in obs:
        o.data.materials.clear(); o.data.materials.append(m)
    lo = V((1e9,) * 3); hi = V((-1e9,) * 3)
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ V(c); lo = V(map(min, lo, w)); hi = V(map(max, hi, w))
    ctr = target or (lo + hi) / 2
    r = (hi - lo).length * 0.5
    d = dist or r * 2.6
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48
    sc.render.resolution_x, sc.render.resolution_y = size; sc.render.film_transparent = False
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True; bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.62, 0.78, 0.95, 1); bg.inputs['Strength'].default_value = 0.9
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(4)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(yaw + 40))
    cam = bpy.data.cameras.new('cam'); cam.lens = lens
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    yr, pr = math.radians(yaw), math.radians(pitch)
    co.location = ctr + V((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
