"""
Okti (pet_13) 3 evre × giyilebilir eşya oturma testi (22 Ekim 2026, kullanıcı madde 14).
Oyundaki CosmeticModels.BuildReal yerleşimini Blender'da taklit eder ve her eşya için önden + yandan küçük resim çizer.
  python fit_test_okti.py <çıktı_klasörü> [kural.json]
kural.json: {"slot": {"bone": "...", "size": .., "up": .., "fwd": .., "side": .., "bottom": bool}, "stage_slot": {...}} (yoksa oyundaki kural)
"""
import sys, os, json, math
import bpy
from mathutils import Vector as V
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
RES = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources')
out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else sys.argv[1]
rules_path = sys.argv[sys.argv.index('--') + 2] if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 2 else None
os.makedirs(out, exist_ok=True)
items = [i for i in json.load(open(os.path.join(RES, 'Data', 'items.json')))['items'] if i.get('slot')]
if os.environ.get('ONLY'): items = [i for i in items if i['id'] in os.environ['ONLY'].split(',')]   # yalnız bu eşyalar
# oyundaki kural (Meshy kemik adlarıyla) — Okti'de karşılıkları
GAME = {'head': ('head_end', 0.55, -0.07, 0, 0, True), 'eyes': ('headfront', 0.32, 0, -0.03, 0, False), 'body': ('Spine02', 0.44, 0.02, 0, 0, False),
        'back': ('Spine01', 0.30, -0.08, -0.12, 0, False), 'hand': ('RightHand', 0.16, 0, 0, 0.04, False)}
OVR = json.load(open(rules_path)) if rules_path else {}

def bone_pos(arm, name):
    for b in arm.data.bones:
        if b.name == name or b.name.endswith(':' + name): return arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local
    return None

def import_fbx(p):
    before = set(bpy.data.objects.keys()); bpy.ops.import_scene.fbx(filepath=p)
    return [o for o in bpy.data.objects if o.name not in before]

def tex_mat(name, jpg):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(jpg)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color']); return m

def bounds(objs):
    pts = [o.matrix_world @ V(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    return V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

MAP = {'head_end': 'Head', 'headfront': 'Head', 'Spine02': 'Spine2', 'Spine01': 'Spine1', 'RightHand': 'RightHand'}

def face_front(objs, z, h):
    ys = [(o.matrix_world @ v.co).y for o in objs if o.type == 'MESH' for v in o.data.vertices if abs((o.matrix_world @ v.co).z - z) < 0.03 * h and abs((o.matrix_world @ v.co).x) < 0.12 * h]
    return min(ys) if ys else 0.0

def place(pet_objs, arm, item, stage, rule):
    bone, size, up, fwd, side, bottom = rule
    io = OVR.get('item:' + item['id'], {}); size *= io.get('size', 1.0); up += io.get('up', 0.0); fwd += io.get('fwd', 0.0)
    mn, mx = bounds(pet_objs); h = mx.z - mn.z
    bp = bone_pos(arm, bone) or bone_pos(arm, MAP.get(bone, bone))
    if bp is None: return None, 'kemik yok: ' + bone
    head, tail = bp
    new = import_fbx(os.path.join(RES, 'Items', item['id'], item['id'] + '.fbx'))
    jpg = os.path.join(RES, 'Items', item['id'], item['id'] + '_basecolor.jpg')
    if os.path.exists(jpg):
        m = tex_mat(item['id'], jpg)
        for o in new:
            if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(m)
    root = bpy.data.objects.new('it_' + item['id'], None); bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    # oyunda: pet ve eşya dosyada aynı yöne (+z) bakar, ikisi de 180° çevrilir → göreli yön aynı, döndürme yok
    bpy.context.view_layer.update()
    imn, imx = bounds(new); w = max(imx.x - imn.x, imx.y - imn.y)
    root.scale = V((1, 1, 1)) * (size * h / max(w, 1e-4)); bpy.context.view_layer.update()
    imn, imx = bounds(new); c = (imn + imx) / 2
    front = V((0, -1, 0)); right = V((1, 0, 0))
    tgt = head + V((0, 0, up * h)) + front * (fwd * h) + right * (side * h)
    if bone in ('head_end',):          # Okti'de uç kemik yok: baş tepesi = gövde ağının en üstü
        tgt = V((head.x, head.y, mx.z + up * h))
    if item['slot'] == 'eyes':
        tgt.z = head.z + OVR.get('eyeline', {}).get(stage, 0.48) * (mx.z - head.z)
    y = tgt.z - (imn.z - root.location.z) if bottom else tgt.z - (c.z - root.location.z)
    yy = tgt.y - (c.y - root.location.y)
    if item['slot'] == 'eyes':      # camların önü yüz yüzeyinin hemen önünde (göz hizasındaki en ön nokta)
        fy = face_front(pet_objs, tgt.z, h)
        yy = (fy + fwd * h) - (imn.y - root.location.y)
    root.location = V((tgt.x - (c.x - root.location.x), yy, y))
    return root, None

def render(path, cam_loc, look, ortho):
    sc = bpy.context.scene; cam = sc.camera; cam.location = cam_loc; cam.rotation_euler = (V(look) - V(cam_loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; sc.render.filepath = path; bpy.ops.render.render(write_still=True)

report = {}
FACE = {}
for stage in os.environ.get('STAGES', 'yavru,genc,yetiskin').split(','):
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 3
    sc.render.resolution_x = sc.render.resolution_y = 320
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.6
    s_ = bpy.data.lights.new('s', 'SUN'); s_.energy = 3.0; so = bpy.data.objects.new('s', s_); sc.collection.objects.link(so); so.rotation_euler = (0.7, 0.2, 0.4)
    cd = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
    base = os.path.join(RES, 'Pets', 'pet_13_' + stage, 'pet_13_' + stage)
    pet = import_fbx(base + '.fbx'); pm = tex_mat('pet', base + '_basecolor.jpg')
    for o in pet:
        if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(pm)
    arm = next(o for o in pet if o.type == 'ARMATURE'); bpy.context.view_layer.update()
    mn, mx = bounds(pet); h = mx.z - mn.z; c = (mn + mx) / 2
    report[stage] = {'h': round(h, 3), 'bones': {b: [round(v, 3) for v in (bone_pos(arm, b)[0])] for b in ('Head', 'Spine2', 'Spine1', 'RightHand', 'Neck') if bone_pos(arm, b)}}
    render(os.path.join(out, stage + '__pet_front.png'), c + V((0, -h * 3, 0)), c, h * 1.3)
    hp = bone_pos(arm, 'Head')[0]; ez = hp.z + OVR.get('eyeline', {}).get(stage, 0.48) * (mx.z - hp.z)
    FACE[stage] = {'h': h, 'head_z': (hp.z - mn.z) / h, 'top': 1.0, 'eye_z': (ez - mn.z) / h, 'face_front_at_eye': (face_front(pet, ez, h) - hp.y) / h}
    for it in items:
        rule = OVR.get(stage + ':' + it['slot']) or OVR.get(it['slot']) or GAME[it['slot']]
        if isinstance(rule, dict): rule = (rule['bone'], rule['size'], rule.get('up', 0), rule.get('fwd', 0), rule.get('side', 0), rule.get('bottom', False))
        root, err = place(pet, arm, it, stage, rule)
        if err: report[stage][it['id']] = err; continue
        render(os.path.join(out, '%s__%s__on.png' % (stage, it['id'])), c + V((0, -h * 3, 0)), c, h * 1.3)
        render(os.path.join(out, '%s__%s__side.png' % (stage, it['id'])), c + V((h * 3, 0, 0)), c, h * 1.3)
        for o in list(root.children_recursive) + [root]: bpy.data.objects.remove(o, do_unlink=True)
report['face'] = FACE
json.dump(report, open(os.path.join(out, 'report.json'), 'w'), indent=1, ensure_ascii=False)
print('BITTI')
