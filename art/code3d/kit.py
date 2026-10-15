# Kodla 3D üretim için ortak araçlar (Blender bpy). Tüm varlıklar orijinal; referanslardan kopya yok.
# Stil: yumuşak "vinyl oyuncak" karakterler + boyalı/maket ada yapıları, ince koyu dış çizgi (oyundaki Pofi/Toon ile aynı fikir).
import bpy, bmesh, math, random, mathutils
V = mathutils.Vector

def srgb(h):
    """'#RRGGBB' → doğrusal RGBA (Blender renkleri doğrusal)."""
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)

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
    if m: o.data.materials.append(m)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if sub:
        s = o.modifiers.new('sub', 'SUBSURF'); s.levels = sub; s.render_levels = sub
    return o

def blob(name, loc, radii, m, rot=(0, 0, 0), sub=2, seg=24):
    """Elipsoit parça (vinyl oyuncak parçası)."""
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
    if bevel:
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = seg; bv.limit_method = 'ANGLE'
    o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    return o

def cyl(name, loc, r, depth, m, rot=(0, 0, 0), verts=16, bevel=0.01):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc)
    o = bpy.context.object; o.name = name; o.rotation_euler = [math.radians(a) for a in rot]
    if bevel:
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
