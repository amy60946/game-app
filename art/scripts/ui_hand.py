# Tanıtım ipuçları için işaret eden çizgi film eli (kredisiz, prosedürel). Kullanım: python -I ui_hand.py -- çıktı.png
# Parmak ucu görselin üst ortasına (u=0.5, v≈0.94) denk gelir; Coach pivotu buna göre ayarlıdır.
import bpy, math, sys, mathutils
out = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 256; sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'

def mat(name, rgb, rough=0.45, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1); b.inputs['Emission Strength'].default_value = emit
    return m
glove = mat('glove', (0.86, 0.84, 0.8), 0.5)
cuff = mat('cuff', (1.0, 0.62, 0.12), 0.4)

parts = []
def blob(loc, scale, m=glove, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m)
    bpy.ops.object.shade_smooth(); parts.append(o); return o
def finger(a, b, r, m=glove):
    a = mathutils.Vector(a); b = mathutils.Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(m); bpy.ops.object.shade_smooth(); parts.append(o)
    blob(a, (r, r, r), m); blob(b, (r, r, r), m)

# avuç, işaret parmağı (yukarı), kıvrık üç parmak, başparmak, bilek manşeti
blob((0, 0, 0), (0.62, 0.36, 0.58))
finger((0.12, -0.02, 0.35), (0.12, -0.02, 1.45), 0.19)
for i, x in enumerate((-0.1, -0.32, -0.5)):
    blob((x, -0.3, 0.32 - i * 0.12), (0.17, 0.2, 0.2))
finger((0.42, -0.18, -0.12), (0.58, -0.35, 0.28), 0.16)
bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.5, depth=0.28, location=(0, 0, -0.66))
c = bpy.context.object; c.scale = (1.0, 0.72, 1); c.data.materials.append(cuff); bpy.ops.object.shade_smooth(); parts.append(c)

# birleştir (kontur 2B'de: art/scripts/ui_hand_outline.py)
bpy.ops.object.select_all(action='DESELECT')
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
h = bpy.context.object
h.rotation_euler = (0, math.radians(-18), 0)

cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = 3.0
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0.12, -6, 0.42); co.rotation_euler = (math.radians(90), 0, 0)
sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3.2; so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(55), math.radians(-25), math.radians(-30))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
