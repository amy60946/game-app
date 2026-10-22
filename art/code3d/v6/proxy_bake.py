# Yüksek ayrıntıdan düşük çokgene pişirme (22 Ekim 2026, geri bildirim 12: "oyundaki görseller taslaktan uzak").
# Eski yol (kit.export_baked_fbx) modeli bütçeye indirip kendi rengini pişiriyordu: yaprak kartları ve kaya çatlakları
# sadeleşmede kayboluyordu. Burada onaylı taslağın TAM modeli (binlerce yaprak, kabartmalı kaya) kaynak, oyun modeli hedef:
#   renk (taslak malzemesinin taban rengi), oyuk gölgesi (AO) ve teğet uzayı normal haritası hedefe ışınla aktarılır.
# Hedef verilmezse kaynağın bütçeye indirilmiş kopyası kullanılır (kaya, kütük…); ağaçta hedef = taç kabukları + seyrek kenar yaprakları.
import os, math
import bpy, bmesh
import numpy as np


def _join(objs, name, keep_materials=True):
    """Nesneleri (değiştiriciler uygulanmış) tek ağa birleştirir; dünya dönüşümü ağa işlenir."""
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); parts = []
    for o in objs:
        if o.type not in ('MESH', 'CURVE'): continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg); me.transform(o.matrix_world)
        if not keep_materials: me.materials.clear()
        p = bpy.data.objects.new(name, me); sc.collection.objects.link(p); parts.append(p)
    for o in objs:
        try: bpy.data.objects.remove(o)
        except Exception: pass
    if not parts: return None
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = name
    return ob


def _decimate(ob, target):
    cur = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if target and cur > target:
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        d = ob.modifiers.new('dec', 'DECIMATE'); d.ratio = target / cur; d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def _emission_swap(mats):
    """Pişirme için: her malzemenin çıkışını taban rengi kaynağına bağlı bir Emission'a çevir (gerçek albedo, ışıksız)."""
    undo = []
    for m in mats:
        if m is None or not m.use_nodes: continue
        nt = m.node_tree; out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
        if out is None: continue
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
        if bsdf is not None:
            bc = bsdf.inputs['Base Color']
            if bc.links: nt.links.new(bc.links[0].from_socket, em.inputs['Color'])
            else: em.inputs['Color'].default_value = bc.default_value
        prev = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].links else None
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        undo.append((nt, out, prev, em))
    return undo


def _emission_restore(undo):
    for nt, out, prev, em in undo:
        if prev is not None: nt.links.new(prev, out.inputs['Surface'])
        nt.nodes.remove(em)


def export_proxy(path_noext, high, low=None, target=1500, size=1024, nsize=None, cage=0.03, ray=0.12,
                 ao_strength=0.65, ao_dist=0.35, normal_strength=1.0, margin=8, ds_low=None, tone=1.0):
    """high: kaynak nesneler (taslak malzemeleriyle). low: hedef nesneler ya da None (kaynağın kopyası bütçeye indirilir).
    Çıktı: <yol>.fbx, <yol>_basecolor.png (renk × yumuşak AO), <yol>_normal.png (teğet uzayı, OpenGL +Y). Üçgen sayısını döndürür."""
    size = int(os.environ.get('POFI_TEX', '0') or 0) or size; nsize = nsize or size
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    H = _join(high, 'high')
    if low is None:
        me = H.data.copy(); me.materials.clear(); L = bpy.data.objects.new('model', me); sc.collection.objects.link(L)
    else:
        L = _join(low, 'model', keep_materials=False)
    L.name = 'model'
    tris = _decimate(L, target)
    # UV: yalnız hedefte
    for l in list(L.data.uv_layers): L.data.uv_layers.remove(l)
    uv = L.data.uv_layers.new(name='UVMap'); L.data.uv_layers.active = uv
    bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); bpy.context.view_layer.objects.active = L
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.006, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    bm = bpy.data.materials.new('bake'); bm.use_nodes = True; L.data.materials.append(bm)
    tex = bm.node_tree.nodes.new('ShaderNodeTexImage'); bm.node_tree.nodes.active = tex
    # hedef ağ kaynağın üstünde/içinde durur: oyuk gölgesi (AO) ışınları ona çarpıp her yeri karartmasın
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_shadow', 'visible_volume_scatter'):
        if hasattr(L, attr): setattr(L, attr, False)
    bk = sc.render.bake
    bk.use_selected_to_active = True; bk.cage_extrusion = cage; bk.max_ray_distance = ray; bk.margin = margin; bk.use_clear = True
    def select_for_bake():
        bpy.ops.object.select_all(action='DESELECT'); H.select_set(True); L.select_set(True); bpy.context.view_layer.objects.active = L
    def run(kind, sz, colorspace='sRGB'):
        img = bpy.data.images.new(kind, sz, sz, alpha=False, float_buffer=True); img.colorspace_settings.name = 'Non-Color' if colorspace != 'sRGB' else 'Linear Rec.709'
        tex.image = img; select_for_bake()
        if kind == 'col':
            undo = _emission_swap(H.data.materials)
            bpy.ops.object.bake(type='EMIT')
            _emission_restore(undo)
        elif kind == 'ao':
            sc.world.light_settings.distance = ao_dist
            bpy.ops.object.bake(type='AO')
        else:
            bk.normal_space = 'TANGENT'; bk.normal_r = 'POS_X'; bk.normal_g = 'POS_Y'; bk.normal_b = 'POS_Z'
            bpy.ops.object.bake(type='NORMAL')
        return np.array(img.pixels[:], np.float32).reshape(sz, sz, 4)
    col = run('col', size); ao = run('ao', size); nrm = run('nrm', nsize, 'Non-Color')
    from PIL import Image
    a = 1.0 - ao_strength * (1.0 - ao[..., :1])
    lin = np.clip(col[..., :3] * a, 0, 1)
    if tone != 1.0: lin = np.power(lin, tone)          # >1: orta tonlar koyulaşır (soluk kaya oyunda saydam gibi görünüyordu)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    Image.fromarray((np.clip(srgb, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_noext + '_basecolor.png', optimize=True)
    n = nrm[..., :3] * 2 - 1
    if normal_strength != 1.0:
        n[..., :2] *= normal_strength; n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    Image.fromarray((np.clip(n * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_noext + '_normal.png', optimize=True)
    # iki yüzlü kenar yaprakları: arka yüz (aynı UV, ters yön) eklenir
    if ds_low and 'ds' in L.data.attributes:
        b2 = bmesh.new(); b2.from_mesh(L.data); lay = b2.faces.layers.int.get('ds')
        faces = [f for f in b2.faces if f[lay] == 1]
        if faces:
            res = bmesh.ops.duplicate(b2, geom=faces); nf = [g for g in res['geom'] if isinstance(g, bmesh.types.BMFace)]
            bmesh.ops.reverse_faces(b2, faces=nf); b2.normal_update()
        b2.to_mesh(L.data); b2.free()
    for k in [k for k in L.data.attributes.keys() if k in ('ds',)]: L.data.attributes.remove(L.data.attributes[k])
    for ca in list(L.data.color_attributes): L.data.color_attributes.remove(ca)
    L.data.materials.clear()
    bpy.data.objects.remove(H)
    bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); bpy.context.view_layer.objects.active = L
    bpy.ops.export_scene.fbx(filepath=path_noext + '.fbx', use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False,
                             use_tspace=True)
    return sum(len(p.vertices) - 2 for p in L.data.polygons)


# ------------------------------------------------------------------ ağaç tacı hedefleri

def shell_cluster(cc, rr, sub=2, bumps=0.06, seed=0, flat_bottom=-0.55):
    """Taç kümesinin dış kabuğu (yaprak katmanının ortası): hafif yumrulu ikosfer; alt yüz taslaktaki gibi basık."""
    from mathutils import noise as MN, Vector as V
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
    pts = []
    for v in b.verts:
        d = v.co.copy()
        if d.z < flat_bottom: d.z = flat_bottom + (d.z - flat_bottom) * 0.3
        k = 1.0 + bumps * MN.noise(d * 2.2 + V((seed * 1.7, seed * 0.3, 0)))
        pts.append((cc[0] + d.x * rr[0] * k, cc[1] + d.y * rr[1] * k, cc[2] + d.z * rr[2] * k))
    faces = [[v.index for v in f.verts] for f in b.faces]; b.free()
    return pts, faces


def mesh_from(name, verts, faces, ds=False, col=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if ds:
        a = me.attributes.new('ds', 'INT', 'FACE'); a.data.foreach_set('value', [1] * len(me.polygons))
    o = bpy.data.objects.new(name, me); (col or bpy.context.scene.collection).objects.link(o); return o
