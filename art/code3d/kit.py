# Kodla 3D üretim için ortak araçlar (Blender bpy). Tüm varlıklar orijinal; referanslardan kopya yok.
# Stil: yumuşak "vinyl oyuncak" karakterler + boyalı/maket ada yapıları, ince koyu dış çizgi (oyundaki Pofi/Toon ile aynı fikir).
import bpy, bmesh, math, random, mathutils
V = mathutils.Vector

def srgb(h):
    """'#RRGGBB' → doğrusal RGBA (Blender renkleri doğrusal)."""
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)

LOW = False   # True: oyun için düşük çokgen (yuvarlatma 1 kademe, alt bölme 1)
_mats = {}
def mat(name, hexcol, rough=0.35, coat=0.25, emit=0.0, sheen=0.0):
    key = (name, hexcol, rough, coat, emit)
    if key in _mats: return _mats[key]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(hexcol)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.12
    if sheen: b.inputs['Sheen Weight'].default_value = sheen
    if emit:
        b.inputs['Emission Color'].default_value = srgb(hexcol); b.inputs['Emission Strength'].default_value = emit
    _mats[key] = m
    return m

def _finish(o, m, sub=2, smooth=True):
    if LOW and sub: sub = 0 if seg_hint_small[0] else 1
    if m: o.data.materials.append(m)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if sub:
        s = o.modifiers.new('sub', 'SUBSURF'); s.levels = sub; s.render_levels = sub
    return o

seg_hint_small = [False]
def blob(name, loc, radii, m, rot=(0, 0, 0), sub=2, seg=24):
    """Elipsoit parça (vinyl oyuncak parçası). Oyun sürümünde küçük küreler (seg ≤ 12) alt bölünmez."""
    seg_hint_small[0] = seg <= 12
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = radii; o.rotation_euler = [math.radians(a) for a in rot]
    return _finish(o, m, sub)

def rbox(name, loc, size, m, rot=(0, 0, 0), bevel=0.02, seg=2):
    """Kenarları yuvarlatılmış kutu (tahta, kiremit, taş…)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = size; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel and (not LOW or max(size) >= 0.9):     # oyun sürümünde küçük parçalar (kiremit, taş) köşeli: çokgen bütçesi
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 1 if LOW else seg; bv.limit_method = 'ANGLE'
    o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = not LOW
    return o

def cyl(name, loc, r, depth, m, rot=(0, 0, 0), verts=16, bevel=0.01):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc)
    o = bpy.context.object; o.name = name; o.rotation_euler = [math.radians(a) for a in rot]
    if bevel and (not LOW or depth >= 0.9):
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    return o

def tube(name, pts, radii, m, res=12):
    """Eğri boyunca kalınlığı değişen tüp (kuyruk, ağız çizgisi, sap…). pts: [(x,y,z)], radii: her noktada yarıçap."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = 4
    cu.use_fill_caps = True; cu.resolution_u = res
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, c, r in zip(sp.bezier_points, pts, radii):
        p.co = c; p.handle_left_type = p.handle_right_type = 'AUTO'; p.radius = r
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m)
    return o

def outline(objs, width=0.012, hexcol='#3a2630'):
    """Ters kabuk dış çizgi (oyundaki ToonOutline geçişinin Blender karşılığı): yalnız arka yüzler görünür."""
    m = bpy.data.materials.get('outline')
    if m is None:
        m = bpy.data.materials.new('outline'); m.use_nodes = True
        nt = m.node_tree; n = nt.nodes; l = nt.links
        for x in list(n): n.remove(x)
        out = n.new('ShaderNodeOutputMaterial'); mix = n.new('ShaderNodeMixShader')
        geo = n.new('ShaderNodeNewGeometry'); tr = n.new('ShaderNodeBsdfTransparent'); em = n.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = srgb(hexcol)
        # yalnız kamera ışınında çiz; gölge/yansıma ışınlarında saydam (yoksa kabuk güneşi keser, figür kararır)
        lp = n.new('ShaderNodeLightPath'); inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        mx = n.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'
        l.new(lp.outputs['Is Camera Ray'], inv.inputs[1]); l.new(geo.outputs['Backfacing'], mx.inputs[0]); l.new(inv.outputs[0], mx.inputs[1])
        l.new(mx.outputs[0], mix.inputs['Fac']); l.new(em.outputs[0], mix.inputs[1]); l.new(tr.outputs[0], mix.inputs[2])   # çevrilmiş kabukta kameraya bakan yüz = arka yüz → saydam
        l.new(mix.outputs[0], out.inputs['Surface'])
    for o in objs:
        if o.type not in ('MESH', 'CURVE'): continue
        if o.type == 'MESH':
            o.data.materials.append(m)
            s = o.modifiers.new('outline', 'SOLIDIFY'); s.thickness = width; s.offset = 1; s.use_flip_normals = True
            s.material_offset = len(o.data.materials) - 1; s.use_rim = False
            s.show_render = True

def to_mesh_all():
    """Eğrileri meshe çevir (dış çizgi + dışa aktarım için)."""
    for o in list(bpy.context.scene.objects):
        if o.type == 'CURVE':
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
            bpy.ops.object.convert(target='MESH')
            for p in o.data.polygons: p.use_smooth = True

def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type != 'MESH': continue
        e = o.evaluated_get(dg); me = e.to_mesh()
        n += sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear()
    return n

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True); _mats.clear()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.35   # canlı renk (AgX soluklaştırıyordu)
    sc.render.film_transparent = False
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = srgb('#bfe3f5'); bg.inputs['Strength'].default_value = 0.9
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(4); sun.color = (1.0, 0.95, 0.88)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(48), 0, math.radians(-35))
    fill = bpy.data.lights.new('fill', 'AREA'); fill.energy = 220; fill.size = 4; fill.color = (0.8, 0.9, 1.0)
    fo = bpy.data.objects.new('fill', fill); sc.collection.objects.link(fo); fo.location = (-4, -3, 3); fo.rotation_euler = (math.radians(60), 0, math.radians(-50))
    return sc

def ground(r=6, hexcol='#8fd06a'):
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=r, fill_type='NGON'); g = bpy.context.object; g.name = 'ground'
    g.data.materials.append(mat('ground', hexcol, rough=0.9, coat=0)); return g

def shoot(sc, path, target, dist, yaw, pitch, lens=50, size=(1100, 1100)):
    sc.render.resolution_x, sc.render.resolution_y = size
    cam = sc.camera
    if cam is None:
        c = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', c); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = lens
    t = V(target); y = math.radians(yaw); p = math.radians(pitch)
    cam.location = t + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

def export_glb(path, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_apply=True)


def export_palette_fbx(path_noext, objs, cell=8, cells=16):
    """Oyun için dışa aktarım: tüm parçalar tek meshe birleşir, her malzemenin rengi küçük bir palet dokusunda
    bir kareye yazılır ve o yüzlerin UV'si o karenin ortasına konur → Unity'de tek doku + tek malzeme (RealAssets).
    path_noext + '.fbx' ve path_noext + '_basecolor.png' yazar."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    colors = []; meshes = []
    for o in objs:
        if o.type not in ('MESH', 'CURVE'): continue
        e = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(e, depsgraph=dg)
        me.transform(o.matrix_world)
        mats = [ms for ms in me.materials]
        idx = []
        for m in mats:
            c = tuple(round(x, 4) for x in m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[:3]) if m and m.use_nodes and 'Principled BSDF' in m.node_tree.nodes else (0.5, 0.5, 0.5)
            if c not in colors: colors.append(c)
            idx.append(colors.index(c))
        # tek UV katmanı, adı herkes için aynı ('UVMap'): birleştirmede ad farklıysa UV kaybolur (yüz siyah görünür)
        if not me.uv_layers: me.uv_layers.new(name='UVMap')
        while len(me.uv_layers) > 1: me.uv_layers.remove(me.uv_layers[-1])
        me.uv_layers[0].name = 'UVMap'; me.uv_layers.active = me.uv_layers[0]
        uv = me.uv_layers.active.data
        for poly in me.polygons:
            ci = idx[poly.material_index] if idx else 0
            u = ((ci % cells) + 0.5) / cells; v = 1.0 - ((ci // cells) + 0.5) / cells
            for li in poly.loop_indices: uv[li].uv = (u, v)
        me.materials.clear()
        meshes.append(me)
    assert len(colors) <= cells * cells, 'palet dolu'
    # birleştir
    ob = bpy.data.objects.new('model', meshes[0]); bpy.context.scene.collection.objects.link(ob)
    others = []
    for me in meshes[1:]:
        o2 = bpy.data.objects.new('p', me); bpy.context.scene.collection.objects.link(o2); others.append(o2)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [ob] + others: o.select_set(True)
    bpy.context.view_layer.objects.active = ob
    if others: bpy.ops.object.join()
    for o in objs:
        try: bpy.data.objects.remove(o)
        except Exception: pass
    # palet dokusu (sRGB)
    img = np.zeros((cells * cell, cells * cell, 4), dtype=np.uint8); img[..., 3] = 255
    def to_srgb(x): return 255 * (x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055)
    for i, c in enumerate(colors):
        r, cidx = divmod(i, cells)
        img[r * cell:(r + 1) * cell, cidx * cell:(cidx + 1) * cell, :3] = [int(min(255, max(0, to_srgb(x)))) for x in c]
    from PIL import Image
    Image.fromarray(img).save(path_noext + '_basecolor.png')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=path_noext + '.fbx', use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False)
    return sum(len(p.vertices) - 2 for p in ob.data.polygons), len(colors)


# ------------------------------------------------------------------ doku pişirme (v3: doğal yüzey)
# Parçalar prosedürel malzemelerle (ahşap damarı, kabuk lifi, yosun, yaprak damarı…) boyanır; hepsi tek meshe birleşir,
# otomatik UV açılır, Cycles ile RENK + ORTAM GÖLGESİ (AO) tek dokuya pişirilir → Unity'de tek doku + tek malzeme.
# AO: girinti ve dip kısımlar yumuşakça koyulaşır (keskin değil, geçişli) — oyundaki toon ışığın altında da kalır.

def nodes_mat(name, build):
    """Düğümlü malzeme: build(nt, bsdf) içinde Base Color'a bağlanacak düğümleri kurar."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.8
    build(nt, b)
    return m

def ramp(nt, stops, interp='LINEAR'):
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.interpolation = interp
    el = r.color_ramp.elements
    while len(el) < len(stops): el.new(0.5)
    for e, (pos, hexc) in zip(el, stops): e.position = pos; e.color = srgb(hexc)
    return r

def export_baked_fbx(path_noext, objs, size=1024, ao_strength=0.6, ao_dist=0.35, margin=6, decimate=None):
    import numpy as np
    sc = bpy.context.scene
    prev_engine = sc.render.engine
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48
    # birleştir (değiştiricileri uygula)
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for o in objs:
        if o.type not in ('MESH', 'CURVE'): continue
        e = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(e, depsgraph=dg); me.transform(o.matrix_world)
        for l in [l for l in me.uv_layers if l.name != 'grain']: me.uv_layers.remove(l)
        if 'grain' not in me.uv_layers: me.uv_layers.new(name='grain')
        o2 = bpy.data.objects.new('p', me); sc.collection.objects.link(o2); meshes.append(o2)
    for o in objs:
        try: bpy.data.objects.remove(o)
        except Exception: pass
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.object; ob.name = 'model'
    if decimate:
        d = ob.modifiers.new('dec', 'DECIMATE'); d.ratio = decimate; bpy.ops.object.modifier_apply(modifier='dec')
    # UV
    uvm = ob.data.uv_layers.new(name='UVMap'); ob.data.uv_layers.active = uvm
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(85), island_margin=0.004, area_weight=0.0, scale_to_bounds=True)   # yüksek açı: her yaprak tek ada (küçük adalarda kenar sızması dama deseni yapıyordu)
    bpy.ops.object.mode_set(mode='OBJECT')
    # pişir: renk ve AO ayrı görüntülere
    def bake(kind):
        img = bpy.data.images.new(kind, size, size, alpha=False)
        for m in ob.data.materials:
            if m is None or not m.use_nodes: continue
            n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; n.name = 'bake_target'
            m.node_tree.nodes.active = n
        if kind == 'col':
            sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.use_pass_color = True
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=margin, use_clear=True)
        else:
            sc.world.light_settings.distance = ao_dist
            bpy.ops.object.bake(type='AO', margin=margin, use_clear=True)
        for m in ob.data.materials:
            if m and m.use_nodes and 'bake_target' in m.node_tree.nodes: m.node_tree.nodes.remove(m.node_tree.nodes['bake_target'])
        return np.array(img.pixels[:]).reshape(size, size, 4)
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    col = bake('col'); ao = bake('ao')
    a = ao[..., :1]
    a = 1.0 - ao_strength * (1.0 - a)            # yumuşak: tam siyaha inmez
    out = col.copy(); out[..., :3] = col[..., :3] * a
    rgb = out[..., :3]   # bayt görüntü pikselleri zaten sRGB kodlu (ikinci dönüşüm soluklaştırıyordu)
    from PIL import Image
    im = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)[::-1]
    Image.fromarray(im).save(path_noext + '_basecolor.png')
    ob.data.materials.clear()
    if 'grain' in ob.data.uv_layers: ob.data.uv_layers.remove(ob.data.uv_layers['grain'])
    # iki yüzlü parçalar ('ds' = 1: yaprak, ot, lif): arka yüz aynı UV ile ters çevrilip eklenir (pişirmeyi bozmaz)
    if 'ds' in ob.data.attributes:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        lay = bm.faces.layers.int.get('ds')
        faces = [f for f in bm.faces if f[lay] == 1]
        if faces:
            res = bmesh.ops.duplicate(bm, geom=faces)
            nf = [g for g in res['geom'] if isinstance(g, bmesh.types.BMFace)]
            nv = [g for g in res['geom'] if isinstance(g, bmesh.types.BMVert)]
            bmesh.ops.reverse_faces(bm, faces=nf)
            bm.normal_update()
            for v in nv: v.co += v.normal * 0.004
        bm.to_mesh(ob.data); bm.free()
        ob.data.attributes.remove(ob.data.attributes['ds'])
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=path_noext + '.fbx', use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False)
    sc.render.engine = prev_engine
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def grain_uv(o, scale=1.0, along=None):
    """Parçanın KENDİ eksenlerinde damar koordinatı ('grain' UV): u = en uzun eksen boyunca (metre·scale), v = ikinci eksen.
    Birleştirmeden sonra da her tahta kendi yönünde damar taşır."""
    me = o.data
    if 'grain' in me.uv_layers: me.uv_layers.remove(me.uv_layers['grain'])
    lay = me.uv_layers.new(name='grain')
    xs = [v.co for v in me.vertices]
    size = [max(c[i] for c in xs) - min(c[i] for c in xs) for i in range(3)]
    order = sorted(range(3), key=lambda i: -size[i]) if along is None else [along] + [i for i in sorted(range(3), key=lambda i: -size[i]) if i != along]
    a, b = order[0], order[1]
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = (co[a] * scale, co[b] * scale + (sum(map(ord, o.name)) % 97) * 0.37)
    return lay

def uv_node(nt, name='grain'):
    n = nt.nodes.new('ShaderNodeUVMap'); n.uv_map = name; return n
