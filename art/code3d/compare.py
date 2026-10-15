# Mevcut (Meshy / oyundaki) ↔ yeni (kodla) varlıkları OYUNDAKİ GİBİ yan yana çizer: EEVEE (gerçek zamanlı),
# oyunun toon ışığına benzer iki tonlu gölgelendirme (Pofi/Toon'un aynısı: güneş + soğuk gölge tonu + alt yüz koyulaşması),
# oyun gökyüzü rengi, oyun kamerası (52° görüş, yukarıdan-arkadan). Fotoğraf değil: dosyalar oyuna giden FBX + dokular.
# Kullanım: EGL_PLATFORM=surfaceless python -I compare.py -- <yeni_klasör> <çıktı.png> <çift> [çift ...]
#   çift: palm|rock|bush|flowers|cloud|home
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, mathutils, random
from kit import srgb
ENV = '/home/user/pofi-adasi/Assets/_Pofi/Resources/Env'
args = sys.argv[sys.argv.index('--') + 1:]
NEW, OUTP, PAIRS = args[0], args[1], args[2:]

PAIR = {   # ad: (mevcut, yeni, hedef boy/genişlik, kamera uzaklığı, kamera yüksekliği açısı)
    'palm': ('palm', 'c_palm', ('h', 4.6), 9.0, 18),
    'rock': ('p_rock', 'c_rock', ('w', 1.8), 4.0, 24),
    'bush': ('p_bush', 'c_bush', ('w', 1.5), 3.8, 24),
    'flowers': ('p_flowers', 'c_flowers', ('w', 1.1), 2.8, 28),
    'home': ('b_home', 'c_house', ('w', 5.2), 10.5, 22),
    'home_close': ('b_home', 'c_house', ('w', 5.2), 5.2, 14),
    'cloud': ('*cloud', 'g_cloud', ('w', 5.0), 12.0, 4),
    # parti 1 (yapılar ve süsler)
    'fence': ('p_fence', 'c_fence', ('w', 1.9), 3.0, 20),
    'lantern': ('p_lantern', 'c_lantern', ('h', 2.0), 3.2, 16),
    'sign': ('p_sign', 'c_sign', ('h', 1.9), 3.2, 16),
    'crates': ('p_crates', 'c_crates', ('w', 1.8), 3.6, 22),
    'boat': ('p_boat', 'c_boat', ('w', 2.4), 3.8, 30),
    'shop': ('b_shop', 'c_shop', ('w', 3.4), 5.6, 20),
    'pier': ('b_pier', 'c_pier', ('w', 3.4), 5.4, 30),
    'lighthouse': ('b_lighthouse', 'c_lighthouse', ('h', 4.8), 8.0, 14),
    'board': ('b_task_board', 'c_board', ('h', 2.3), 4.0, 14),
    # parti 2
    'garden': ('b_garden', 'c_garden', ('w', 3.4), 5.2, 32),
    'surf': ('b_surf', 'c_surf', ('w', 3.4), 5.4, 22),
    'swim': ('b_swim', 'c_swim', ('w', 3.6), 5.6, 34),
    'game_hut': ('b_game_hut', 'c_game_hut', ('w', 3.4), 5.8, 20),
    'festival': ('b_festival', 'c_festival', ('w', 3.8), 6.4, 20),
    'cave': ('b_cave', 'c_cave', ('w', 3.8), 6.0, 20),
    'mountain': ('b_mountain', 'c_mountain', ('w', 3.8), 7.2, 20),
    'ski': ('b_ski_hill', 'c_ski', ('w', 3.8), 6.4, 24),
}
GROUND = {'rock': '#f1d89c', 'boat': '#f1d89c', 'crates': '#f1d89c', 'pier': '#4fb6d8', 'surf': '#f1d89c', 'ski': '#e8f0fb'}

def toon_mat(name, tex_path=None, color=None):
    """Oyundaki Pofi/Toon'a yakın: L = güneş (gölge dahil); t = yumuşak eşik; renk = doku × karışım(gölge, ışık)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.use_backface_culling = True          # oyundaki gibi (Unity: arkaya bakan yüz çizilmez)
    nt = m.node_tree; n = nt.nodes; l = nt.links
    for x in list(n): n.remove(x)
    out = n.new('ShaderNodeOutputMaterial')
    dif = n.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = n.new('ShaderNodeShaderToRGB'); l.new(dif.outputs[0], s2r.inputs[0])
    bw = n.new('ShaderNodeRGBToBW'); l.new(s2r.outputs['Color'], bw.inputs[0])
    ramp = n.new('ShaderNodeMapRange'); ramp.interpolation_type = 'SMOOTHSTEP'
    ramp.inputs['From Min'].default_value = 0.0; ramp.inputs['From Max'].default_value = 0.16   # güneş 1 W: aydınlık ≈ 0.32·cos; geniş, yumuşak geçiş
    l.new(bw.outputs[0], ramp.inputs['Value'])
    if tex_path:
        tex = n.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(tex_path); tex.interpolation = 'Closest' if '/g_' in tex_path or os.path.basename(tex_path).startswith('g_') else 'Linear'
        alb = tex.outputs['Color']
    else:
        rgb = n.new('ShaderNodeRGB'); rgb.outputs[0].default_value = color or (1, 1, 1, 1); alb = rgb.outputs[0]
    # alt yüzler koyu (ortam ışığı yarım küre): amb = 0.55..0.9
    geo = n.new('ShaderNodeNewGeometry'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Normal'], sep.inputs[0])
    amb = n.new('ShaderNodeMapRange'); amb.inputs['From Min'].default_value = -1; amb.inputs['From Max'].default_value = 1
    amb.inputs['To Min'].default_value = 0.5; amb.inputs['To Max'].default_value = 0.88; l.new(sep.outputs['Z'], amb.inputs['Value'])
    shade = n.new('ShaderNodeMix'); shade.data_type = 'RGBA'; shade.blend_type = 'MULTIPLY'; shade.inputs['Factor'].default_value = 1
    shade.inputs[7].default_value = (0.72, 0.76, 1.0, 1)          # soğuk-mor gölge tonu
    l.new(alb, shade.inputs[6])
    sh2 = n.new('ShaderNodeVectorMath'); sh2.operation = 'SCALE'; l.new(shade.outputs[2], sh2.inputs[0]); l.new(amb.outputs[0], sh2.inputs['Scale'])
    lit = n.new('ShaderNodeMix'); lit.data_type = 'RGBA'; lit.blend_type = 'MULTIPLY'; lit.inputs['Factor'].default_value = 1
    lit.inputs[7].default_value = (1.08, 1.03, 0.95, 1); l.new(alb, lit.inputs[6])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; l.new(ramp.outputs[0], mix.inputs['Factor'])
    l.new(sh2.outputs[0], mix.inputs[6]); l.new(lit.outputs[2], mix.inputs[7])
    em = n.new('ShaderNodeEmission'); l.new(mix.outputs[2], em.inputs['Color'])
    l.new(em.outputs[0], out.inputs['Surface'])
    return m

def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    try: sc.eevee.taa_render_samples = 16
    except Exception: pass
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x, sc.render.resolution_y = 960, 640
    # gökyüzü: yalnız kamerada görünür, sahneyi aydınlatmaz (ışık güneşten; ortam toon malzemesinde)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    bg = n['Background']; tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); rp = n.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = srgb('#bfe8ff'); rp.color_ramp.elements[1].position = 0.5; rp.color_ramp.elements[1].color = srgb('#5cb8f5')
    l.new(tc.outputs['Window'], sep.inputs[0]); l.new(sep.outputs['Y'], rp.inputs['Fac']); l.new(rp.outputs['Color'], bg.inputs['Color'])
    lp = n.new('ShaderNodeLightPath'); mixw = n.new('ShaderNodeMixShader'); blk = n.new('ShaderNodeBackground'); blk.inputs['Strength'].default_value = 0
    l.new(lp.outputs['Is Camera Ray'], mixw.inputs['Fac']); l.new(blk.outputs[0], mixw.inputs[1]); l.new(bg.outputs[0], mixw.inputs[2])
    l.new(mixw.outputs[0], n['World Output'].inputs['Surface'])
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 1.0; sun.angle = math.radians(2.5); sun.color = (1, 1, 1)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(46), 0, math.radians(-38))
    return sc

def load_fbx(path, tex):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    m = toon_mat(os.path.basename(path), tex)
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(m)
    return objs

def cur_cloud():
    """Oyundaki mevcut bulut: Clouds.cs ile aynı yöntem (gürültülü küre pufları, rastgele küme)."""
    from mathutils import noise
    m = toon_mat('cloudcur', None, (1, 1, 1, 1)); objs = []
    rnd = random.Random(5); s = 2.0
    for k in range(12):
        pr = s * (0.32 + rnd.random() * 0.38)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.5)
        o = bpy.context.object
        for v in o.data.vertices:
            nrm = v.co.normalized()
            bump = (noise.noise(nrm * 2.3) * 0.5 + 0.5) * 0.22 + (noise.noise(nrm * 6) * 0.5 + 0.5) * 0.06
            p = nrm * (0.5 + bump)
            if p.z < -0.18: p.z = -0.18 + (p.z + 0.18) * 0.25
            v.co = p
        o.scale = (pr, pr, pr * 0.8)
        o.location = ((rnd.random() * 2 - 1) * s * 1.5, (rnd.random() * 2 - 1) * s * 0.6, rnd.random() * s * 0.45)
        for p in o.data.polygons: p.use_smooth = True
        o.data.materials.append(m); objs.append(o)
    return objs

def fit(objs, target, x_off):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
    mn = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size = mx - mn
    k = target[1] / (size.z if target[0] == 'h' else max(size.x, size.y))
    root = bpy.data.objects.new('root', None); bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None or o.parent not in objs: o.parent = root
    for o in objs:
        if o.parent == root: o.location -= mathutils.Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    root.scale = (k, k, k); root.location = (x_off, 0, 0)
    return size * k

def tris(objs):
    dg = bpy.context.evaluated_depsgraph_get(); t = 0
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); t += sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear()
    return t

from PIL import Image, ImageDraw, ImageFont
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
rows = []
for name in PAIRS:
    cur, new, target, dist, pitch = PAIR[name]
    panels = []
    for side, label in ((cur, 'Mevcut'), (new, 'Yeni (kodla)')):
        sc = scene()
        if side == '*cloud': objs = cur_cloud()
        elif side.startswith(('g_', 'c_')) and os.path.exists(f'{NEW}/{side}.fbx'): objs = load_fbx(f'{NEW}/{side}.fbx', f'{NEW}/{side}_basecolor.png')
        elif side.startswith('g_'): objs = load_fbx(f'{ENV}/{side}/{side}.fbx', f'{ENV}/{side}/{side}_basecolor.png')
        else:
            tex = f'{ENV}/{side}/{side}_basecolor.jpg'
            objs = load_fbx(f'{ENV}/{side}/{side}.fbx', tex if os.path.exists(tex) else tex[:-3] + 'png')
        t = tris(objs)
        size = fit(objs, target, 0)
        if name != 'cloud':
            bpy.ops.mesh.primitive_circle_add(vertices=48, radius=60, fill_type='NGON'); g = bpy.context.object
            g.data.materials.append(toon_mat('ground', None, srgb(GROUND.get(name, '#7cc24e'))))   # kayalar oyunda kumsalda
        cam = bpy.data.cameras.new('c'); cam.sensor_fit = 'VERTICAL'; cam.angle = math.radians(52 if name != 'cloud' else 40)
        co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
        tgt = mathutils.Vector((0, 0, size.z * (0.32 if name == 'home_close' else 0.45)))
        p = math.radians(pitch); y = math.radians(-25)
        co.location = tgt + mathutils.Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
        co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
        path = f'/tmp/claude-0/-home-user/627c1edb-353e-56ac-a5e6-566ce82843ea/scratchpad/cmp_{name}_{label[:2]}.png'
        sc.render.filepath = path; bpy.ops.render.render(write_still=True)
        im = Image.open(path).convert('RGB'); d = ImageDraw.Draw(im)
        txt = f'{label} · {t} üçgen'
        d.rounded_rectangle((12, 12, 36 + d.textlength(txt, font=font), 54), 12, fill=(255, 255, 255))
        d.text((24, 18), txt, font=font, fill=(30, 50, 80))
        panels.append(im)
        print(name, label, t, flush=True)
    row = Image.new('RGB', (1920, 640), 'white'); row.paste(panels[0], (0, 0)); row.paste(panels[1], (960, 0)); rows.append(row)
sheet = Image.new('RGB', (1920, 640 * len(rows)), 'white')
for i, r in enumerate(rows): sheet.paste(r, (0, 640 * i))
sheet.save(OUTP, quality=88)
