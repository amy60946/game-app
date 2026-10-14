"""GLB'yi Blender'da açar: üçgen sayısı, boyut, doku çözünürlüğü; ön/3-4/arka render (Cycles CPU, düşük örnek).
Kullanım: python inspect.py model.glb cikti_onek"""
import sys, math, bpy, mathutils
src, out = sys.argv[1], sys.argv[2]
views = sys.argv[3].split(",") if len(sys.argv) > 3 else ["on", "ucdort", "arka"]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
mins = mathutils.Vector((1e9,) * 3); maxs = mathutils.Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        mins = mathutils.Vector(map(min, mins, w)); maxs = mathutils.Vector(map(max, maxs, w))
size = maxs - mins
imgs = [(i.name, i.size[0], i.size[1]) for i in bpy.data.images]
print(f"BILGI tris={tris} size={tuple(round(v,3) for v in size)} images={imgs} objs={[o.name for o in meshes]}")
center = (mins + maxs) / 2
h = max(size)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'
sc.render.resolution_x = 640; sc.render.resolution_y = 800
sc.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.82, 0.88, 0.95, 1); world.node_tree.nodes['Background'].inputs[1].default_value = 0.8
key = bpy.data.lights.new("key", 'AREA'); key.energy = 160 * h * h; key.size = h
ko = bpy.data.objects.new("key", key); sc.collection.objects.link(ko)
ko.location = center + mathutils.Vector((-h, -1.5 * h, 1.5 * h)); ko.rotation_euler = (math.radians(50), 0, math.radians(-35))
cam = bpy.data.cameras.new("cam"); cam.lens = 70
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
# glTF: +Y yukarı → Blender'da Z yukarı (içe aktarıcı çevirir); ön yüz -Y
for name, ang in [v for v in (("on", 0), ("ucdort", -35), ("arka", 180)) if v[0] in views]:
    a = math.radians(ang)
    d = 3.2 * h
    co.location = center + mathutils.Vector((math.sin(a) * d, -math.cos(a) * d, 0.15 * h))
    direction = center - co.location
    co.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}_{name}.png"
    bpy.ops.render.render(write_still=True)
