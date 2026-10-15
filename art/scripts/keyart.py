# Tam ekran sahne görselleri (kredisiz, Meshy modelleriyle Blender'da): festival_bg (Ada Festivali arka planı),
# keyart (oyun yükleme ekranı). Kullanım: python -I keyart.py -- çıktı_klasörü [festival_bg|keyart ...]
import bpy, math, sys, mathutils, random
R = '/home/user/pofi-adasi'
args = sys.argv[sys.argv.index('--') + 1:]
OUT = args[0]; ONLY = set(args[1:])

def reset(w=1920, h=1080, samples=64):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.2
    # stilize gökyüzü: ufukta açık camgöbeği → tepede açık mavi (oyundaki Pofi/Sky ile aynı ton)
    wd = bpy.data.worlds.new('w'); sc.world = wd; wd.use_nodes = True
    n = wd.node_tree.nodes; l = wd.node_tree.links
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); rp = n.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = (0.55, 0.82, 1.0, 1)
    rp.color_ramp.elements[1].position = 0.45; rp.color_ramp.elements[1].color = (0.09, 0.38, 0.92, 1)
    l.new(tc.outputs['Generated'], sep.inputs[0]); l.new(sep.outputs['Z'], rp.inputs['Fac'])
    l.new(rp.outputs['Color'], n['Background'].inputs['Color']); n['Background'].inputs['Strength'].default_value = 1.0
    sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3.6; sun.angle = math.radians(3); sun.color = (1.0, 0.95, 0.86)
    so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(52), 0, math.radians(-38))
    return sc

def load(name, height=None, footprint=None, loc=(0, 0, 0), yaw=0, path=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path or f'{R}/art/meshy/out/{name}/{name}.glb')
    objs = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name + '_root', None); bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ mathutils.Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    mn = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size = mx - mn
    s = 1.0
    if height: s = height / max(size.z, 1e-3)
    if footprint: s = footprint / max(size.x, size.y, 1e-3)
    for o in objs:
        if o.parent == root: o.location -= mathutils.Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    root.scale = (s, s, s); root.rotation_euler = (0, 0, math.radians(yaw)); root.location = loc
    return root

def mat(rgb, rough=0.6):
    m = bpy.data.materials.new('m'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    return m

def ground(size=200, rgb=(0.36, 0.68, 0.22)):
    bpy.ops.mesh.primitive_plane_add(size=size); g = bpy.context.object; g.data.materials.append(mat(rgb, 0.9)); return g

def camera(sc, loc, target, lens=32):
    c = bpy.data.cameras.new('c'); c.lens = lens
    o = bpy.data.objects.new('c', c); sc.collection.objects.link(o); sc.camera = o
    o.location = loc; o.rotation_euler = (mathutils.Vector(target) - mathutils.Vector(loc)).to_track_quat('-Z', 'Y').to_euler()

def bunting(p0, p1, sag=0.8, n=14, colors=((0.95, 0.3, 0.3), (1.0, 0.8, 0.15), (0.2, 0.6, 0.95), (0.35, 0.8, 0.35), (0.9, 0.45, 0.9))):
    """İki direk arasında sarkan ip + üçgen bayraklar."""
    p0 = mathutils.Vector(p0); p1 = mathutils.Vector(p1)
    pts = [p0.lerp(p1, t) - mathutils.Vector((0, 0, sag * 4 * t * (1 - t))) for t in [i / 40 for i in range(41)]]
    cu = bpy.data.curves.new('rope', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.02
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p.x, p.y, p.z, 1)
    ob = bpy.data.objects.new('rope', cu); bpy.context.scene.collection.objects.link(ob); ob.data.materials.append(mat((0.3, 0.25, 0.2)))
    for i in range(n):
        t = (i + 0.5) / n
        p = p0.lerp(p1, t) - mathutils.Vector((0, 0, sag * 4 * t * (1 - t)))
        d = (p1 - p0).normalized()
        a = p - d * 0.22; b = p + d * 0.22; c = p - mathutils.Vector((0, 0, 0.5))
        me = bpy.data.meshes.new('flag'); me.from_pydata([a, b, c], [], [(0, 1, 2)]); me.update()
        f = bpy.data.objects.new('flag', me); bpy.context.scene.collection.objects.link(f)
        f.data.materials.append(mat(colors[i % len(colors)], 0.5))

def cloud(loc, s=1.0):
    m = mat((1, 1, 1), 0.9)
    for (x, y, z, r) in [(0, 0, 0, 1.0), (1.1, 0.1, -0.15, 0.8), (-1.1, 0, -0.2, 0.75), (0.4, 0.2, 0.55, 0.7), (-0.5, 0.1, 0.4, 0.65)]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r * s, location=(loc[0] + x * s, loc[1] + y * s, loc[2] + z * s))
        o = bpy.context.object; o.scale = (1, 0.8, 0.8); o.data.materials.append(m); bpy.ops.object.shade_smooth()

def render(sc, name):
    sc.render.filepath = f"{OUT}/{name}.png"; bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------- Ada Festivali arka planı
if not ONLY or 'festival_bg' in ONLY:
    sc = reset()
    ground(rgb=(0.4, 0.7, 0.25))
    bpy.ops.mesh.primitive_plane_add(size=1); p = bpy.context.object; p.scale = (4.5, 30, 1); p.location = (0, -12, 0.01)
    p.data.materials.append(mat((0.86, 0.66, 0.38), 0.95))                                  # kum yol
    load('b_festival', footprint=9.0, loc=(0, 8, 0), yaw=180)
    for (x, y, h) in [(-9, 4, 7.5), (9.5, 5, 8.0), (-14, 12, 9), (15, 13, 8.5), (-6.5, -2, 6.5), (7, -3, 7)]:
        load('palm', height=h, loc=(x, y, 0), yaw=random.Random(int(x * 10)).uniform(0, 360))
    load('decor_umbrella', height=2.8, loc=(-4.5, 1.5, 0), yaw=20)
    load('decor_umbrella', height=2.6, loc=(5.0, 2.0, 0), yaw=-30)
    load('p_crates', height=1.1, loc=(-3.2, 4.2, 0), yaw=15)
    load('p_flowers', footprint=1.6, loc=(3.4, -1.0, 0), yaw=0)
    load('p_flowers', footprint=1.4, loc=(-3.0, -1.5, 0), yaw=40)
    # direkler + bayrak süsleri
    for x in (-6.5, 6.5):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=5.2, location=(x, 0.5, 2.6)); bpy.context.object.data.materials.append(mat((0.5, 0.32, 0.18)))
    bunting((-6.5, 0.5, 5.0), (6.5, 0.5, 5.0), sag=0.9)
    bunting((-6.5, 0.5, 4.2), (-1.5, 8.0, 5.6), sag=0.5, n=8)
    bunting((6.5, 0.5, 4.2), (1.5, 8.0, 5.6), sag=0.5, n=8)
    cloud((-12, 40, 14), 2.2); cloud((10, 45, 16), 2.6); cloud((26, 50, 11), 1.8)
    camera(sc, (0, -11.5, 2.3), (0, 6, 3.4), lens=26)
    render(sc, 'festival_bg')

# ---------------------------------------------------------------- yükleme ekranı anahtar görseli
if not ONLY or 'keyart' in ONLY:
    sc = reset()
    bpy.ops.mesh.primitive_plane_add(size=400); sea = bpy.context.object
    sm = mat((0.05, 0.45, 0.75), 0.15); sea.data.materials.append(sm)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=17, depth=1.0, location=(0, 10, 0.0))
    isl = bpy.context.object; isl.scale = (1.25, 1.0, 1); isl.data.materials.append(mat((0.95, 0.85, 0.6), 0.95))   # kumsal
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=14, depth=1.2, location=(0, 11, 0.12))
    gr = bpy.context.object; gr.scale = (1.25, 1.0, 1); gr.data.materials.append(mat((0.38, 0.7, 0.24), 0.9))     # çimen
    top = 0.72
    load('b_home', footprint=6.5, loc=(-1.0, 14, top), yaw=200)
    load('b_shop', footprint=5.0, loc=(-9.5, 10, top), yaw=160)
    load('b_festival', footprint=6.0, loc=(8.5, 16, top), yaw=210)
    load('b_lighthouse', height=9.0, loc=(14, 22, top), yaw=200)
    for (x, y, h) in [(-14, 5, 7), (-5.5, 4, 6.5), (5.5, 6, 7.2), (12, 7, 6.8), (-12, 18, 8), (3, 22, 8.5)]:
        load('palm', height=h, loc=(x, y, top), yaw=random.Random(int(x * 7)).uniform(0, 360))
    load('decor_umbrella', height=2.4, loc=(3.0, 1.0, 0.5), yaw=10)
    load('decor_sandcastle', footprint=1.4, loc=(-2.8, 0.6, 0.5), yaw=0)
    load('p_boat', footprint=3.5, loc=(10.5, -4.5, 0.05), yaw=60)
    # Pofi ön planda
    load('pofi', height=3.0, loc=(0.4, -1.2, 0.5), yaw=-15, path=f'{R}/art/meshy/out/pofi/pofi.glb')
    cloud((-18, 60, 18), 3.0); cloud((8, 70, 22), 3.6); cloud((30, 65, 14), 2.4); cloud((-36, 70, 12), 2.2)
    camera(sc, (0, -11.0, 3.4), (0, 8, 3.2), lens=28)
    render(sc, 'keyart')
