# Oyundaki bir Env modelini şeffaf arka planla çizer (taslak panelleri için). python3.11 -I render_model.py -- <ad> çıktı.png
import bpy, math, sys, os, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code3d'))
import kit
V = mathutils.Vector
name, out = sys.argv[sys.argv.index('--') + 1:][:2]
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Assets', '_Pofi', 'Resources', 'Env', name)
sc = kit.reset(); sc.cycles.samples = 48; sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 640; sc.view_settings.exposure = -0.4
bpy.ops.import_scene.fbx(filepath=os.path.join(d, name + '.fbx'))
m = bpy.data.materials.new('m'); m.use_nodes = True
t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(d, name + '_basecolor.png'))
m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.7
ms = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in ms: o.data.materials.clear(); o.data.materials.append(m)
bpy.context.view_layer.update()
mn = V((1e9,) * 3); mx = V((-1e9,) * 3)
for o in ms:
    for c in o.bound_box:
        w = o.matrix_world @ V(c); mn = V(map(min, mn, w)); mx = V(map(max, mx, w))
ctr = (mn + mx) / 2; size = (mx - mn).length
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = size * 0.95
co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
co.location = ctr + V((size * 0.9, -size * 1.2, size * 0.9)); co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('ok', out)
