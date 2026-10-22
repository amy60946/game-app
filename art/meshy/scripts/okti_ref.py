# Okti tam boy referans çekimi (Meshy görsel üretiminde karakter tutarlılığı için; yalnız kendi modelimiz).
import bpy, sys, math, os
from mathutils import Vector as V
args = sys.argv[sys.argv.index('--') + 1:]
src, tex, out, frame_frac, yaw = args[0], args[1], args[2], float(args[3]), float(args[4])
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 1024; sc.render.film_transparent = True
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
base = src.split('@')[0] + '.fbx'
bpy.ops.import_scene.fbx(filepath=base)
keep = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=src)
anim_objs = [o for o in bpy.data.objects if o not in keep]
act = next((o.animation_data.action for o in anim_objs if o.animation_data and o.animation_data.action), None)
for o in anim_objs: bpy.data.objects.remove(o, do_unlink=True)
m = bpy.data.materials.new('okti'); m.use_nodes = True; nt = m.node_tree
t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(tex)
b = nt.nodes['Principled BSDF']; nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.55
b.inputs['Subsurface Weight'].default_value = 0.08
meshes = [o for o in sc.objects if o.type == 'MESH']
for o in meshes: o.data.materials.clear(); o.data.materials.append(m)
arm = next((o for o in sc.objects if o.type == 'ARMATURE'), None)
if arm and act:
    arm.animation_data_create(); arm.animation_data.action = act
if arm and arm.animation_data and arm.animation_data.action:
    a = arm.animation_data.action; f0, f1 = a.frame_range
    sc.frame_set(int(f0 + (f1 - f0) * frame_frac))
root = arm or meshes[0]
root.rotation_euler.z += math.radians(yaw)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in meshes:
    e = o.evaluated_get(dg); me = e.to_mesh()
    pts += [o.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
mn = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
h = mx.z - mn.z; c = (mn + mx) / 2
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 70
cam.location = c + V((0, -h * 3.6, h * 0.35)); cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
for e, (el, az, en) in enumerate([(50, -35, 3.2), (25, 140, 1.4)]):
    L = bpy.data.objects.new(f'l{e}', bpy.data.lights.new(f'l{e}', 'SUN')); sc.collection.objects.link(L)
    L.data.energy = en; L.data.angle = math.radians(8); L.rotation_euler = (math.radians(90 - el), 0, math.radians(az))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.75, 0.85, 1.0, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
