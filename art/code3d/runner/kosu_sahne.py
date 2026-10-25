# Piramit Koşusu — önizleme ve simgeler (25 Ekim 2026).
#   render(png): dışa aktarılmış oyun modelleriyle (FBX + tek doku, oyundaki gibi) yol kompozisyonu: 5 yol parçası + iki yan duvar
#                (sol = sağın x'te −1 ölçeklisi, oyundaki gibi), engeller, skarabe/papirüs, uzakta kapı, piramit, kum tepesi, hurma,
#                dikili taş, sfenks. Kamera orta şeridin arkasında (0, −6, 3,4), ileri ve ~15° aşağı bakar. Koordinat = Blender = Unity
#                (EnvScaled 180° dönüşünden sonra Blender (x, y) → Unity (x, z)).
#   icons():     ui_scarab.png, ui_scroll.png → Assets/_Pofi/Resources/Icons (256 px, saydam zemin, 3/4 üstten, nesne karenin ~%85'i).
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
from egypt_kit import bpy, V
import kit

ICONS = os.path.join(EK.ROOT, 'Assets', '_Pofi', 'Resources', 'Icons')


def place(name, loc=(0, 0, 0), yaw=0.0, sx=1.0, s=1.0):
    """Modeli içe aktar, oyun malzemesini ver, yerleştir. Döner: nesneler."""
    before = set(bpy.data.objects)
    p = EK.out_dir(name)
    if not os.path.exists(p + '.fbx'):
        print('YOK', name); return []
    bpy.ops.import_scene.fbx(filepath=p + '.fbx')
    obs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    m = bpy.data.materials.get('game_' + name) or EK.game_mat(p, back=False, name='game_' + name)
    root = bpy.data.objects.new(name + '_root', None); bpy.context.scene.collection.objects.link(root)
    for o in obs:
        o.data.materials.clear(); o.data.materials.append(m); o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw)); root.scale = (sx * s, s, s)
    return obs


def sand_ground(size=600):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, -0.01)); g = bpy.context.object; g.name = 'ground'
    g.data.materials.append(EK.m_sand('groundsand', seed=11.0))
    return g


def sky(sc):
    w = sc.world; nt = w.node_tree; bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sp.inputs[0])
    r = kit.ramp(nt, [(0.48, '#f3e2c2'), (0.56, '#a9d3ee'), (0.8, '#5fa6dc')]); nt.links.new(sp.outputs['Z'], r.inputs['Fac'])
    nt.links.new(r.outputs[0], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0


def render(png, size=(1280, 720), samples=96):
    sc = kit.reset(); sky(sc)
    sun = bpy.data.objects['sun']; sun.rotation_euler = (math.radians(52), 0, math.radians(-28)); sun.data.energy = 3.4
    sand_ground()
    for i in range(-1, 5):
        y = 10 * i + 5
        place('rn_floor', (0, y, 0)); place('rn_wall', (0, y, 0)); place('rn_wall', (0, y, 0), sx=-1.0)
    place('rn_block', (-2.2, 9.0, 0)); place('rn_low', (0, 15.0, 0)); place('rn_block2', (2.2, 20.0, 0)); place('rn_high', (0, 25.0, 0))
    for k in range(5): place('rn_scarab', (0, 3.0 + k * 1.2, 0.45), yaw=25 * k)
    place('rn_scarab', (-2.2, 17.5, 0.45), yaw=40); place('rn_scarab', (2.2, 12.0, 0.45), yaw=-20)
    place('rn_scroll', (2.2, 7.5, 0.4), yaw=30); place('rn_scroll', (0, 21.0, 0.4), yaw=-15)
    place('rn_gate', (0, 34.0, 0))
    place('rn_pyramid', (-55, 150, 0)); place('rn_pyramid', (60, 210, 0), yaw=20); place('rn_pyramid', (5, 270, 0), yaw=8, s=0.8)
    for (x, y, yaw) in ((-26, 45, 10), (28, 60, -20), (-34, 95, 30), (38, 110, 0), (-6, 120, 5)):
        place('rn_dune', (x, y, 0), yaw=yaw)
    for (x, y) in ((-7.0, 30.0), (7.0, 30.0)): place('rn_obelisk', (x, y, 0))
    for (x, y, yaw, s) in ((-7.5, 12.0, 30, 1.0), (8.0, 18.0, 160, 0.9), (-8.5, 22.0, 250, 1.1), (7.6, 41.0, 90, 1.0), (-9.0, 44.0, 10, 0.95), (10.5, 8.0, 200, 1.05)):
        place('rn_palm', (x, y, 0), yaw=yaw, s=s)
    place('rn_sphinx', (-16, 58, 0), yaw=-35)
    cam = bpy.data.cameras.new('cam'); cam.lens = 24; cam.clip_end = 1000
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, -6.0, 3.4); co.rotation_euler = (math.radians(75), 0, 0)
    sc.cycles.samples = samples; sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.filepath = png; bpy.ops.render.render(write_still=True)


def icons():
    for name, yaw, pitch in (('rn_scarab', 32.0, 34.0), ('rn_scroll', 28.0, 30.0)):
        sc = kit.reset()
        for o in list(bpy.data.objects):
            if o.type == 'LIGHT': bpy.data.objects.remove(o)
        obs = place(name)
        bpy.context.view_layer.update()
        # ışık: yumuşak ana (sol üst ön), hafif dolgu (sağ), arka kenar ışığı
        def area(n, loc, e, s, col):
            l = bpy.data.lights.new(n, 'AREA'); l.energy = e; l.size = s; l.color = col
            o = bpy.data.objects.new(n, l); sc.collection.objects.link(o); o.location = loc
            o.rotation_euler = (V((0, 0, 0.1)) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
        area('key', (-1.2, -1.6, 2.0), 260, 1.6, (1.0, 0.96, 0.9)); area('fill', (1.8, -0.8, 0.8), 90, 2.0, (0.85, 0.92, 1.0))
        area('rim', (0.6, 1.8, 1.4), 120, 1.2, (1.0, 0.95, 0.85))
        sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
        sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = 256
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
        sc.cycles.samples = 96
        cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'
        co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
        yr, pr = math.radians(yaw), math.radians(pitch)
        pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
        ctr = sum(pts, V((0, 0, 0))) / len(pts)
        d = 5.0
        co.location = ctr + V((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
        co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        inv = co.matrix_world.inverted()
        cp = [inv @ p for p in pts]
        xs = [p.x for p in cp]; ys = [p.y for p in cp]
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        co.location = co.matrix_world @ V((cx, cy, 0))
        cam.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) / 0.85
        sc.render.filepath = os.path.join(ICONS, 'ui_' + name[3:] + '.png')
        bpy.ops.render.render(write_still=True)
        print('simge', sc.render.filepath, flush=True)
