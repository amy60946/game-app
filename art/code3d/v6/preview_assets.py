# Oyun modellerinin (Resources/Env/<ad>) kontrol sayfası: FBX + pişirilmiş doku, ızgarada, Cycles ile.
#   /tmp/claude-0/bpyenv/bin/python -I preview_assets.py -- <çıktı.png> ad1 ad2 ...
import sys, os, math
import bpy
from mathutils import Vector as V
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'Assets', '_Pofi', 'Resources', 'Env'))
args = sys.argv[sys.argv.index('--') + 1:]
out, names = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.7, 0.9, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.8
cols = int(math.ceil(math.sqrt(len(names)))); cell = 1.0
for k, n in enumerate(names):
    p = os.path.join(ENV, n, n)
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=p + '.fbx')
    new = [o for o in bpy.data.objects if o.name not in before and o.type == 'MESH']
    m = bpy.data.materials.new(n); m.use_nodes = True; nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(p + '_basecolor.png')
    b = nt.nodes['Principled BSDF']; nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.8
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ V(c) for o in new for c in o.bound_box]
    mn = V((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts))); mx = V((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
    size = max((mx - mn).x, (mx - mn).y, (mx - mn).z); s = 0.85 / max(size, 1e-4)
    cx, cy = (k % cols) * cell, -(k // cols) * cell
    for o in new:
        o.data.materials.clear(); o.data.materials.append(m)
        o.matrix_world = __import__('mathutils').Matrix.Translation((cx - (mn.x + mx.x) / 2 * s, cy - (mn.y + mx.y) / 2 * s, -mn.z * s)) @ __import__('mathutils').Matrix.Scale(s, 4) @ o.matrix_world
bpy.ops.mesh.primitive_plane_add(size=cols * cell * 3, location=((cols - 1) * cell / 2, -(cols - 1) * cell / 2, 0))
g = bpy.data.materials.new('g'); g.use_nodes = True; g.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.5, 0.55, 0.45, 1); bpy.context.object.data.materials.append(g)
sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 4.0; so = bpy.data.objects.new('s', sun); so.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(so)
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = cols * cell * 1.15
co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
ctr = V(((cols - 1) * cell / 2, -(cols - 1) * cell / 2, 0.3))
co.location = ctr + V((0, -6, 4.2)); co.rotation_euler = (math.radians(55), 0, 0)
sc.render.resolution_x = sc.render.resolution_y = 1400
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
