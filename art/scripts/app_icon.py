# Uygulama simgesi (1024x1024, saydamlıksız — App Store kuralı): Pofi (pet_01) yakın çekim, arkada gökyüzü-deniz geçişi,
# önde çimenli kumsal tümseği ve palmiye yaprakları. Kullanım: python -I app_icon.py -- <çıktı.png>
import bpy, math, sys, os, mathutils
OUT = sys.argv[sys.argv.index('--') + 1]
R = '/home/user/pofi-adasi/Assets/_Pofi/Resources'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 96; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 1024; sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
nt = w.node_tree; n = nt.nodes; l = nt.links
bg = n['Background']; bg.inputs['Strength'].default_value = 1.0
tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); rp = n.new('ShaderNodeValToRGB')
rp.color_ramp.elements[0].position = 0.45; rp.color_ramp.elements[0].color = (0.55, 0.85, 1.0, 1)
rp.color_ramp.elements[1].position = 0.8; rp.color_ramp.elements[1].color = (0.12, 0.5, 0.95, 1)
l.new(tc.outputs['Window'], sep.inputs[0]); l.new(sep.outputs['Y'], rp.inputs['Fac']); l.new(rp.outputs['Color'], bg.inputs['Color'])
sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(6)
so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30))
fill = bpy.data.lights.new('f', 'AREA'); fill.energy = 300; fill.size = 6
fo = bpy.data.objects.new('f', fill); sc.collection.objects.link(fo); fo.location = (-3, -4, 2); fo.rotation_euler = (math.radians(65), 0, math.radians(-35))
bpy.ops.import_scene.fbx(filepath=f'{R}/Pets/pet_01/pet_01.fbx')
objs = [o for o in sc.objects if o.type == 'MESH']
m = bpy.data.materials.new('pet'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{R}/Pets/pet_01/pet_01_basecolor.jpg')
m.node_tree.links.new(t.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.45; b.inputs['Coat Weight'].default_value = 0.3
for o in objs: o.data.materials.clear(); o.data.materials.append(m)
bpy.context.view_layer.update()
pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
H = mx.z - mn.z; ctr = (mn + mx) / 2
# zemin: çimenli tümsek + kum
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1, location=(ctr.x, ctr.y, mn.z - H * 0.55))
g = bpy.context.object; g.scale = (H * 1.6, H * 1.6, H * 0.6)
gm = bpy.data.materials.new('g'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.25, 0.62, 0.16, 1)
g.data.materials.append(gm)
cam = bpy.data.cameras.new('c'); cam.lens = 70; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
tgt = mathutils.Vector((ctr.x, ctr.y, mn.z + H * 0.6))
d = H * 2.15
# pet ham önü Blender'da -Y (Meshy); kamera önden, hafif yukarıdan ve yandan
co.location = tgt + mathutils.Vector((math.sin(math.radians(-20)), -math.cos(math.radians(-20)), 0.25)).normalized() * d
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
from PIL import Image
Image.open(OUT).convert('RGB').save(OUT)
