# Gezegen Koşusu — önizleme ve simgeler (25 Ekim 2026).
#   render(png): dışa aktarılmış oyun modelleriyle yol kompozisyonu (oyundaki gibi tek doku): 6 güverte parçası + iki yan korkuluk
#                (sol = sağın x'te −1 ölçeklisi), engeller, kristaller, kartlar, önde kuyruklu yıldız, uzakta geçit halkası. Gökyüzünü oyun
#                kendisi çizer; burada yalnız kamera ışınına koyu lacivert-mor uzay + yıldız (aydınlatma ayrı, nötr). Kamera orta şeridin
#                arkasında (0, −6, 3,4), ileri ve ~15° aşağı. Koordinat = Blender = Unity (EnvScaled 180° sonrası (x, y) → (x, z)).
#   icons():     ui_crystal.png, ui_card.png → Assets/_Pofi/Resources/Icons (256 px, saydam, 3/4 üstten, nesne karenin ~%85'i).
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
from egypt_kit import bpy, V
import kit
import kosu_sahne as KS

ICONS = KS.ICONS


def space_world(sc, ambient=0.85):
    """Kamera ışınında: lacivert → mor geçişli uzay + seyrek yıldız; diğer ışınlarda nötr lavanta ortam ışığı."""
    w = sc.world; nt = w.node_tree; n = nt.nodes; l = nt.links
    for x in list(n): n.remove(x)
    out = n.new('ShaderNodeOutputWorld'); mix = n.new('ShaderNodeMixShader')
    lp = n.new('ShaderNodeLightPath')
    amb = n.new('ShaderNodeBackground'); amb.inputs['Color'].default_value = kit.srgb('#c9c6e0'); amb.inputs['Strength'].default_value = ambient
    sky = n.new('ShaderNodeBackground'); sky.inputs['Strength'].default_value = 1.0
    tc = n.new('ShaderNodeTexCoord'); sp = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sp.inputs[0])
    r = kit.ramp(nt, [(0.35, '#141634'), (0.55, '#2a2160'), (0.8, '#3b2a6e')]); l.new(sp.outputs['Z'], r.inputs['Fac'])
    vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 180.0; l.new(tc.outputs['Generated'], vo.inputs['Vector'])
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.06; mr.inputs['From Max'].default_value = 0.0; l.new(vo.outputs['Distance'], mr.inputs['Value'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; l.new(mr.outputs[0], mx.inputs['Factor']); l.new(r.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (1, 1, 1, 1)
    l.new(mx.outputs[2], sky.inputs['Color'])
    l.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac']); l.new(amb.outputs[0], mix.inputs[1]); l.new(sky.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs['Surface'])


def moon_light(sc, sun_e=3.2, rim=1.3):
    """Oyundaki ışık (RunnerScreen, 25 Ekim 2026): güneş Euler(24°, 68°) → ışık yönü Unity (0,85; −0,41; 0,34) = Blender (0,85; 0,34;
    −0,41): alçak (24°), soldan ve hafif arkadan, sıcak; "Rim" Euler(14°, 200°) → önden-sağdan gelen serin mavi kenar ışığı; ortam
    lavanta (oyun üç renkli ortam #8E95CC / #ABA0CC / #726B94). Unity yoğunluğu (1,4 / 0,6) Cycles'ta ≈ π× (Lambert'te 1/π yok);
    Pofi/Toon basamağı ışığı biraz sıkıştırdığı için biraz altında tutulur. Kamera ışınında koyu uzay."""
    space_world(sc, ambient=0.5)
    w = sc.world.node_tree.nodes
    for n in w:
        if n.type == 'BACKGROUND' and abs(n.inputs['Strength'].default_value - 0.5) < 1e-6: n.inputs['Color'].default_value = kit.srgb('#aba0cc')
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
    d = V((0.847, 0.342, -0.407)).normalized()
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = sun_e; sun.angle = math.radians(2.5); sun.color = (1.0, 0.96, 0.9)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    f = bpy.data.lights.new('rim', 'SUN'); f.energy = rim; f.angle = math.radians(6); f.color = (0.55, 0.72, 1.0)
    fo = bpy.data.objects.new('rim', f); sc.collection.objects.link(fo); fo.rotation_euler = V((-0.332, -0.912, -0.242)).normalized().to_track_quat('-Z', 'Y').to_euler()


def game_cam(sc, y=-5.3, h=2.75, aspect=(1280, 720)):
    """Oyun kamerası (RunnerScreen.Cam): koşucunun 5,3 m arkası, 2,75 m yukarı, 12,3 m ilerideki 1,25 m'ye bakar (≈ 7° aşağı),
    düşey görüş 54° (16:9)."""
    cam = bpy.data.cameras.new('cam'); cam.sensor_fit = 'VERTICAL'; cam.angle_y = math.radians(54.0); cam.clip_end = 3000
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, y, h); co.rotation_euler = (math.radians(90.0) - math.atan2(h - 1.25, 12.3), 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = aspect
    return co


def matte(prefixes=('game_rs_ground', 'game_rs_crater', 'game_rs_ridge'), spec=0.12):
    """Oyundaki Pofi/Toon parlama yapmaz (yalnız hafif mavi kenar): alçak bakışta Principled'ın yansıması araziyi ağartıp gri
    gösteriyordu → önizlemede arazi malzemelerinin yansıması kısılır."""
    for m in bpy.data.materials:
        if not m.use_nodes or not m.name.startswith(tuple(prefixes)): continue
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                for k in ('Specular IOR Level', 'Specular'):
                    if k in n.inputs: n.inputs[k].default_value = spec; break


def render(png, size=(1280, 720), samples=96, moon=True):
    sc = kit.reset()
    moon_light(sc)
    P = KS.place
    if moon:
        P('rs_ground_a', (0, 14.0, 0)); P('rs_ground_b', (0, 54.0, 0)); P('rs_ground_a', (0, 94.0, 0)); P('rs_ground_b', (0, 134.0, 0))
        P('rs_ridge', (0, 230.0, 0)); P('rs_ridge', (-150, 260.0, 0), yaw=12, s=1.2); P('rs_ridge', (160, 250.0, 0), yaw=-15)
        P('rs_earth', (-70.0, 520.0, 150.0), s=2.2)
        P('rs_dome', (-15.0, 34.0, 0), yaw=20); P('rs_rocket', (19.0, 62.0, 0)); P('rs_dish', (-11.5, 52.0, 0), yaw=-30)
        P('rs_rover', (8.8, 21.0, 0), yaw=-70); P('rs_cargo', (-7.6, 15.0, 0), yaw=15); P('rs_pennant', (6.3, 9.0, 0)); P('rs_pennant', (-6.3, 45.0, 0), yaw=180)
        P('rs_rocks', (8.5, 33.0, 0), yaw=40); P('rs_rocks', (-9.0, 26.0, 0), yaw=200, s=0.8); P('rs_crystals', (-8.7, 40.0, 0), yaw=30); P('rs_crystals', (10.5, 47.0, 0), yaw=-50)
    for i in range(-1, 9):
        y = 10 * i + 5
        P('rs_floor', (0, y, 0)); P('rs_wall', (0, y, 0)); P('rs_wall', (0, y, 0), sx=-1.0)
    P('rs_block', (-2.2, 9.0, 0)); P('rs_low', (0, 15.0, 0)); P('rs_block2', (2.2, 20.0, 0)); P('rs_high', (0, 25.0, 0))
    for k in range(5): P('rs_crystal', (0, 2.5 + k * 1.2, 0.35), yaw=20 * k)
    P('rs_crystal', (-2.2, 17.0, 0.35)); P('rs_crystal', (2.2, 12.0, 0.35), yaw=30)
    P('rs_card', (2.2, 6.5, 0.35), yaw=-20); P('rs_card', (0, 21.0, 0.35), yaw=15)
    P('rs_comet', (0.4, 31.0, 1.7))
    P('rs_gate', (0, 37.0, 0))
    matte()
    cam = bpy.data.cameras.new('cam'); cam.lens = 24; cam.clip_end = 3000
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, -6.0, 3.4); co.rotation_euler = (math.radians(75), 0, 0)
    sc.cycles.samples = samples; sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.filepath = png; bpy.ops.render.render(write_still=True)


def close(png, size=(1280, 720), samples=64, ground='rs_ground_a'):
    """Oyun kamerasıyla alçak bakış (RunnerScreen.Cam): x = 0, 2,75 m, koridor boyunca; 4 zemin karosu + uzak sırt + Dünya."""
    sc = kit.reset(); moon_light(sc)
    P = KS.place
    other = 'rs_ground_b' if ground == 'rs_ground_a' else 'rs_ground_a'
    for k in range(4): P(ground if k % 2 == 0 else other, (0, 14.0 + 40.0 * k, 0))
    for i in range(-1, 15):
        y = 10 * i + 5
        P('rs_floor', (0, y, 0)); P('rs_wall', (0, y, 0)); P('rs_wall', (0, y, 0), sx=-1.0)
    P('rs_ridge', (0, 200.0, 0)); P('rs_earth', (-60.0, 450.0, 110.0), s=2.0)
    matte()
    game_cam(sc, aspect=size)
    sc.cycles.samples = samples
    sc.render.filepath = png; bpy.ops.render.render(write_still=True)


def icons():
    only = [a for a in sys.argv[sys.argv.index('--') + 1:] if a.startswith('rs_')] if '--' in sys.argv else []
    for name, out, yaw, pitch in (('rs_crystal', 'ui_crystal', 28.0, 26.0), ('rs_card', 'ui_card', -26.0, 18.0), ('rs_earth', 'ui_earth', 0.0, 8.0)):
        if only and name not in only: continue
        sc = kit.reset()
        for o in list(bpy.data.objects):
            if o.type == 'LIGHT': bpy.data.objects.remove(o)
        obs = P_icon(name)
        if not obs: continue
        def area(n_, loc, e, s, col):
            li = bpy.data.lights.new(n_, 'AREA'); li.energy = e; li.size = s; li.color = col
            o = bpy.data.objects.new(n_, li); sc.collection.objects.link(o); o.location = loc
            o.rotation_euler = (V((0, 0, 0.25)) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
        area('key', (-1.4, -1.8, 2.0), 210, 1.6, (1.0, 0.97, 0.92)); area('fill', (1.8, -1.0, 0.8), 90, 2.0, (0.85, 0.9, 1.0))
        area('rim', (0.6, 1.8, 1.4), 140, 1.2, (1.0, 0.95, 0.9))
        sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
        sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = 256
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
        sc.cycles.samples = 128
        cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'
        co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
        yr, pr = math.radians(yaw), math.radians(pitch)
        pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
        ctr = sum(pts, V((0, 0, 0))) / len(pts)
        co.location = ctr + V((math.sin(yr) * math.cos(pr) * 5, -math.cos(yr) * math.cos(pr) * 5, math.sin(pr) * 5))
        co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        inv = co.matrix_world.inverted(); cp = [inv @ p for p in pts]
        xs = [p.x for p in cp]; ys = [p.y for p in cp]
        co.location = co.matrix_world @ V(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
        cam.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) / 0.85
        sc.render.filepath = os.path.join(ICONS, out + '.png')
        bpy.ops.render.render(write_still=True)
        print('simge', sc.render.filepath, flush=True)


def P_icon(name):
    obs = KS.place(name)
    bpy.context.view_layer.update()
    return obs
