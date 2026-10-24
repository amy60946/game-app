"""
Okti kıyafet × hareket denemesi (24 Ekim 2026, kullanıcı: "kıyafetlerin oturmasını farklı hareketlerde dene; yürürken uzuvlar
gereksiz sallanmasın"). Oyundaki yerleşimi taklit eder: eşyalar dinlenme duruşunda CosmeticModels kurallarıyla yerleşir ve
kemiğe bağlanır, temel giysi (tişört + şort) vücudun kemiklerine deri olarak bağlanır; sonra her klibin karelerinde
  - eşyanın gövdeye girme payı (köşelerin gövde içinde kalan oranı ve en derin nokta, boyun yüzdesi) dinlenme duruşuna göre ölçülür,
  - örnek kombinlerin önden + yandan kareleri çizilir (pafta),
  - CALM=1 iken yürüme/koşuda oyundaki "sakin yürüyüş" (World/GaitCalm) aynı formülle uygulanır.
Kullanım: python3.11 -I art/meshy/scripts/anim_fit_test.py -- <çıktı> [kural.json]
Ortam: STAGES=yavru,genc,yetiskin  CLIPS=walk,run,…  CALM=0|1  RENDER=0|1  SETS=a,b,c
"""
import sys, os, json, math
import bpy, bmesh
from mathutils import Vector as V, Quaternion as Q
from mathutils.bvhtree import BVHTree

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
RES = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources')
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
OUT = args[0]; os.makedirs(OUT, exist_ok=True)
OVR = json.load(open(args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'okti_fit_rules.json')))
CALM = os.environ.get('CALM', '0') == '1'
RENDER = os.environ.get('RENDER', '1') == '1'
# SKIN=body: bu yuvalardaki eşyalar tek kemiğe sert bağlanmaz, en yakın vücut yüzeyinden kemik ağırlığı alıp deri olur
# (oyunda CosmeticModels.SkinToBody ile aynı fikir)
SKIN = set(x for x in os.environ.get('SKIN', '').split(',') if x)
# Deri olan gövde giysileri (oyunda CosmeticModels.SkinItems); kabarık kostümler (tavuk, hamburger, çim etek, simit) sert kalır:
# deri olunca vücuttan uzak kabuk bacak/kalça ağırlıkları arasında gerilip yırtılmış gibi görünüyordu
SKIN_ITEMS = {'shirt_stripes', 'shirt_hawaii', 'apron_sailor', 'hoodie_soft', 'vest_explorer', 'raincoat', 'set_captain', 'scarf_knit', 'sash_belt'}
# BONE=outfit_hula:Hips,…: eşyaya özel kemik (oyunda CosmeticModels.OktiItemBone)
BONE = dict(x.split(':') for x in os.environ.get('BONE', '').split(',') if ':' in x)
ITEMS = {i['id']: i for i in json.load(open(os.path.join(RES, 'Data', 'items.json')))['items'] if i.get('slot')}
SETS = {
    'a': ['hat_beanie', 'glasses_round', 'vest_explorer', 'backpack_small', 'hand_flag'],
    'b': ['hat_shark', 'outfit_chicken', 'cape_hero', 'socks_arm'],
    'c': ['hat_propeller', 'mask_hero', 'float_flamingo', 'backpack_rocket', 'pompom'],
}
GAME = {'head': ('head_end', 0.55, -0.07, 0, 0, True), 'eyes': ('headfront', 0.32, 0, -0.03, 0, False), 'body': ('Spine02', 0.44, 0.02, 0, 0, False),
        'back': ('Spine01', 0.30, -0.08, -0.12, 0, False), 'hand': ('RightHand', 0.16, 0, 0, 0.04, False)}
MAP = {'head_end': 'Head', 'headfront': 'Head', 'Spine02': 'Spine2', 'Spine01': 'Spine1', 'RightHand': 'RightHand', 'Hips': 'Hips'}
# Oyundaki GaitCalm ile aynı: klibin ortalama duruşuna doğru çekme oranı (1 = klip olduğu gibi)
CALM_KEEP = {
    'walk': {'Arm': 0.5, 'ForeArm': 0.45, 'Hand': 0.45, 'Shoulder': 0.6, 'Head': 0.7, 'Neck': 0.7},
    'run':  {'Arm': 0.42, 'ForeArm': 0.4, 'Hand': 0.4, 'Shoulder': 0.5, 'Head': 0.6, 'Neck': 0.6},
}

def calm_keep(clip, bone):
    t = CALM_KEEP.get(clip)
    if not t: return 1.0
    b = bone.split(':')[-1]
    for side in ('Left', 'Right'):
        if b.startswith(side): b = b[len(side):]
    if b in ('Spine', 'Spine1', 'Spine2'): b = 'Spine'
    return t.get(b, 1.0)

def import_fbx(p):
    before = set(bpy.data.objects.keys()); bpy.ops.import_scene.fbx(filepath=p)
    return [o for o in bpy.data.objects if o.name not in before]

def tex_mat(name, img):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color']); return m

def world_verts(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    pts = [o.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear(); return pts

def bounds_pts(pts):
    return V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

def bone_world(arm, name):
    for pb in arm.pose.bones:
        if pb.name == name or pb.name.endswith(':' + name): return arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail, pb.name
    return None

def body_bvh(body):
    dg = bpy.context.evaluated_depsgraph_get(); e = body.evaluated_get(dg); me = e.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(body.matrix_world); bm.normal_update()
    t = BVHTree.FromBMesh(bm); bm.free(); e.to_mesh_clear(); return t

def inside_stats(tree, pts, h):
    """Köşelerin gövde içinde kalan oranı ve en derin noktanın boya oranı (en yakın yüz normaline göre içeride mi)."""
    n = 0; deep = 0.0
    for p in pts:
        loc, nor, _, d = tree.find_nearest(p)
        if loc is None: continue
        if (p - loc).dot(nor) < 0:
            n += 1; deep = max(deep, d)
    return n / max(1, len(pts)), deep / h

def load_item(iid, parent_name):
    new = []
    for part in (iid, iid + '_spin'):
        fbx = os.path.join(RES, 'Items', iid, part + '.fbx')
        if not os.path.exists(fbx): continue
        objs = import_fbx(fbx); new += objs
        tex = next((p for p in (os.path.join(RES, 'Items', iid, part + '_basecolor.' + e) for e in ('jpg', 'png')) if os.path.exists(p)), None)
        if tex:
            m = tex_mat(part, tex)
            for o in objs:
                if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(m)
    root = bpy.data.objects.new(parent_name, None); bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    return root, new

def mesh_pts(objs):
    return [p for o in objs if o.type == 'MESH' for p in world_verts(o)]

def attach(root, arm, bone_name):
    mw = root.matrix_world.copy()
    root.parent = arm; root.parent_type = 'BONE'; root.parent_bone = bone_name
    bpy.context.view_layer.update(); root.matrix_world = mw; bpy.context.view_layer.update()

def place(stage, item, arm, pet_pts, h, mn, mx):
    rule = OVR.get(stage + ':' + item['slot']) or OVR.get(item['slot']) or GAME[item['slot']]
    if isinstance(rule, dict): rule = (rule['bone'], rule['size'], rule.get('up', 0), rule.get('fwd', 0), rule.get('side', 0), rule.get('bottom', False))
    bone, size, up, fwd, side, bottom = rule
    io = OVR.get(stage + ':item:' + item['id']) or OVR.get('item:' + item['id'], {})
    size *= io.get('size', 1.0); up += io.get('up', 0.0); fwd += io.get('fwd', 0.0)
    bind_bone = BONE.get(item['id'])
    if item.get('pair') and item['slot'] == 'hand':
        roots = []
        for sd in ('Right', 'Left'):
            hp = bone_world(arm, sd + 'Hand'); fp = bone_world(arm, sd + 'ForeArm')
            d = (hp[0] - fp[0]).normalized()
            root, objs = load_item(item['id'], 'it_' + item['id'] + sd)
            imn, imx = bounds_pts(mesh_pts(objs)); w = max(imx.x - imn.x, imx.y - imn.y); s = size * h / max(w, 1e-4)
            root.rotation_mode = 'QUATERNION'; root.rotation_quaternion = V((0, 0, -1)).rotation_difference(d); root.scale = V((s, s, s))
            bpy.context.view_layer.update()
            imn, imx = bounds_pts(mesh_pts(objs)); c = (imn + imx) / 2
            root.location = root.location + (hp[0] + d * (fwd * h) - c); bpy.context.view_layer.update()
            attach(root, arm, hp[2]); roots.append((root, objs))
        return roots
    b = bone_world(arm, bone) or bone_world(arm, MAP.get(bone, bone))
    head = b[0]; bname = b[2]
    if bone == 'head_end': bname = bone_world(arm, 'Head')[2]
    root, objs = load_item(item['id'], 'it_' + item['id'])
    if io.get('flip'): root.rotation_euler = (0, 0, math.pi)
    bpy.context.view_layer.update()
    imn, imx = bounds_pts(mesh_pts(objs)); w = max(imx.x - imn.x, imx.y - imn.y)
    root.scale = V((1, 1, 1)) * (size * h / max(w, 1e-4)); bpy.context.view_layer.update()
    imn, imx = bounds_pts(mesh_pts(objs)); c = (imn + imx) / 2
    front = V((0, -1, 0)); right = V((1, 0, 0))
    tgt = head + V((0, 0, up * h)) + front * (fwd * h) + right * (side * h)
    if bone == 'head_end': tgt = V((head.x, head.y, mx.z + up * h))
    yy = tgt.y - (c.y - root.location.y)
    if item['slot'] == 'eyes':
        tgt.z = head.z + OVR.get('eyeline', {}).get(stage, 0.48) * (mx.z - head.z)
        ys = [p.y for p in pet_pts if abs(p.z - tgt.z) < 0.03 * h and abs(p.x) < 0.12 * h]
        fy = min(ys) if ys else head.y
        yy = (fy + fwd * h) - (imn.y - root.location.y)
    z = tgt.z - (imn.z - root.location.z) if bottom else tgt.z - (c.z - root.location.z)
    root.location = V((tgt.x - (c.x - root.location.x), yy, z)); bpy.context.view_layer.update()
    if item['slot'] in SKIN and item['id'] in SKIN_ITEMS:
        skin_to_body(objs, arm, BODY[0])
        return [(root, objs)]
    if bind_bone: bname = bone_world(arm, bind_bone)[2]   # yer aynı, bağlandığı kemik farklı
    attach(root, arm, bname)
    return [(root, objs)]

BODY = [None]

TORSO = ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'LeftShoulder', 'RightShoulder')
LEG = ('UpLeg', 'Leg', 'Foot', 'Toe')

def skin_to_body(objs, arm, body):
    """Oyundaki CosmeticModels.SkinToBody ile aynı: eşya köşesi en yakın 4 vücut köşesinin kemik ağırlıklarını uzaklığın
    karesiyle ters orantılı alır (en büyük 4). Kol/yen bölgesi (koltuk altının üstü ve omuzdan dışarı) dışındaki köşeler yalnız
    gövde köşelerinden alır (dinlenme duruşunda sarkan kol yeleğin yanını çekip zıplarken açıyordu); bacak payı kalçaya."""
    from mathutils.kdtree import KDTree
    dg = bpy.context.evaluated_depsgraph_get()
    bme = body.evaluated_get(dg).to_mesh()
    names = [g.name for g in body.vertex_groups]
    short = [n.split(':')[-1] for n in names]
    hips_i = short.index('Hips') if 'Hips' in short else None
    pts = []; wts = []; torso_idx = []
    for v in bme.vertices:
        w = {}
        for ge in v.groups:
            gi = ge.group
            if hips_i is not None and any(k in short[gi] for k in LEG): gi = hips_i
            w[gi] = w.get(gi, 0.0) + ge.weight
        pts.append(body.matrix_world @ v.co); wts.append(w)
        if w and short[max(w, key=w.get)] in TORSO: torso_idx.append(len(pts) - 1)
    body.evaluated_get(dg).to_mesh_clear()
    kd_all = KDTree(len(pts)); [kd_all.insert(p, i) for i, p in enumerate(pts)]; kd_all.balance()
    kd_t = KDTree(len(torso_idx)); [kd_t.insert(pts[i], i) for i in torso_idx]; kd_t.balance()
    la = bone_world(arm, 'LeftArm')[0]; ra = bone_world(arm, 'RightArm')[0]
    mid = (la + ra) / 2; side = (ra - la).normalized(); half = (ra - la).length / 2; pit = min(la.z, ra.z)
    hb = max(p.z for p in pts) - min(p.z for p in pts)
    for o in objs:
        if o.type != 'MESH': continue
        mw = o.matrix_world.copy(); o.parent = None; o.data.transform(mw); o.matrix_world.identity()
        for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
        groups = [o.vertex_groups.new(name=n) for n in names]
        for v in o.data.vertices:
            p = v.co
            sleeve = abs((p - mid).dot(side)) > half * 0.85 and p.z > pit - 0.025 * hb   # oyunda BodyGrid.Sleeve
            near = (kd_all if sleeve else kd_t).find_n(p, 4)
            acc = {}
            for (_, idx, d) in near:
                iw = 1.0 / (d * d + 1e-8)
                for gi, gw in wts[idx].items(): acc[gi] = acc.get(gi, 0.0) + gw * iw
            top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
            for gi, x in top: groups[gi].add([v.index], x / tot, 'REPLACE')
        am = o.modifiers.new('arm', 'ARMATURE'); am.object = arm
        o.parent = arm; o.matrix_parent_inverse = arm.matrix_world.inverted()
    bpy.context.view_layer.update()

def set_action(arm, clip_path):
    objs = import_fbx(clip_path)
    src = next((o for o in objs if o.type == 'ARMATURE'), None)
    act = src.animation_data.action if src and src.animation_data else None
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)
    if act is None: return None
    arm.animation_data_create(); arm.animation_data.action = act
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    return act

def clip_means(arm, act):
    f0, f1 = [int(x) for x in act.frame_range]; acc = {}
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        for pb in arm.pose.bones:
            q = pb.rotation_quaternion.copy(); a = acc.get(pb.name)
            if a is None: acc[pb.name] = q
            else:
                if a.dot(q) < 0: q.negate()
                acc[pb.name] = Q((a.w + q.w, a.x + q.x, a.y + q.y, a.z + q.z))
    return {k: v.normalized() for k, v in acc.items()}

def apply_calm(arm, clip, means):
    for pb in arm.pose.bones:
        k = calm_keep(clip, pb.name)
        if k >= 0.999 or pb.name not in means: continue
        pb.rotation_quaternion = means[pb.name].slerp(pb.rotation_quaternion, k)
    bpy.context.view_layer.update()

def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 6; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 2   # bu ortamda GL yok: Cycles (CPU)
    sc.render.resolution_x = 260; sc.render.resolution_y = 300
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.5
    s_ = bpy.data.lights.new('s', 'SUN'); s_.energy = 3.0; so = bpy.data.objects.new('s', s_); sc.collection.objects.link(so); so.rotation_euler = (0.7, 0.2, 0.4)
    cd = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
    return sc

def render(path, cam_loc, look, ortho):
    sc = bpy.context.scene; cam = sc.camera; cam.location = cam_loc; cam.rotation_euler = (V(look) - V(cam_loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; sc.render.filepath = path; bpy.ops.render.render(write_still=True)

report = {}
for stage in os.environ.get('STAGES', 'yavru,genc,yetiskin').split(','):
    base = os.path.join(RES, 'Pets', 'pet_13_' + stage, 'pet_13_' + stage)
    clips = [c for c in os.environ.get('CLIPS', 'idle,walk,run,happy,wave,jump,spin,sleep,dance,strut,dance2,genie,squat,tumble').split(',')
             if os.path.exists(base + '@' + c + '.fbx')]
    sets = os.environ.get('SETS', 'all,a,b,c').split(',')
    for set_name in sets:
        sc = setup_scene()
        pet = import_fbx(base + '.fbx'); pm = tex_mat('pet', base + '_basecolor.jpg')
        for o in pet:
            if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(pm)
        arm = next(o for o in pet if o.type == 'ARMATURE'); body = next(o for o in pet if o.type == 'MESH'); BODY[0] = body
        # temel giysi: aynı kemiklere deri (oyunda CosmeticModels.BuildSkinWear)
        wear_p = base + '_wear.fbx'
        if os.path.exists(wear_p):
            wr = import_fbx(wear_p)
            for o in wr:
                if o.type == 'MESH':
                    for m in o.modifiers:
                        if m.type == 'ARMATURE': m.object = arm
                    o.parent = arm
                    if not o.data.materials or o.data.materials[0] is None:
                        o.data.materials.clear(); mm = bpy.data.materials.new('wear'); mm.diffuse_color = (1.0, 0.82, 0.25, 1); o.data.materials.append(mm)
            for o in wr:
                if o.type == 'ARMATURE': bpy.data.objects.remove(o, do_unlink=True)
        # oyunda eşyalar dinlenme duruşunda yerleşir (CosmeticModels.Apply → RestPose): kurallar da bu duruşta ölçüldü
        for pb in arm.pose.bones: pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        pet_pts = world_verts(body); mn, mx = bounds_pts(pet_pts); h = mx.z - mn.z
        ids = [i for i in ITEMS if i in ITEMS] if set_name == 'all' else SETS[set_name]
        placed = {}
        if set_name == 'all':
            for iid in ids: placed[iid] = place(stage, ITEMS[iid], arm, pet_pts, h, mn, mx)
        else:
            for iid in ids: placed[iid] = place(stage, ITEMS[iid], arm, pet_pts, h, mn, mx)
        # dinlenme duruşundaki taban ölçü
        tree = body_bvh(body)
        baseline = {iid: max((inside_stats(tree, mesh_pts(objs), h) for _, objs in parts), key=lambda s: s[1]) for iid, parts in placed.items()}
        rep = report.setdefault(stage, {}).setdefault(set_name, {'h': round(h, 3), 'baseline': {k: [round(a, 3), round(b, 3)] for k, (a, b) in baseline.items()}, 'clips': {}})
        for clip in clips:
            act = set_action(arm, base + '@' + clip + '.fbx')
            if act is None: continue
            f0, f1 = [int(x) for x in act.frame_range]
            means = clip_means(arm, act) if CALM and clip in CALM_KEEP else None
            frames = sorted(set(int(round(f0 + (f1 - f0) * i / 7.0)) for i in range(8)))
            worst = {}
            for fi, f in enumerate(frames):
                sc.frame_set(f)
                if means: apply_calm(arm, clip, means)
                if set_name == 'all':
                    tree = body_bvh(body)
                    for iid, parts in placed.items():
                        frac, deep = max((inside_stats(tree, mesh_pts(objs), h) for _, objs in parts), key=lambda s: s[1])
                        b = baseline[iid]
                        if deep - b[1] > worst.get(iid, (0, 0, 0))[1]: worst[iid] = (round(frac - b[0], 3), round(deep - b[1], 3), f)
                elif RENDER and fi % 2 == 0:
                    c = V(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, (mn.z + mx.z) / 2))
                    tag = '%s__%s__%s__f%02d' % (stage, set_name, clip + ('_calm' if means else ''), fi)
                    render(os.path.join(OUT, tag + '_on.png'), c + V((0, -h * 3, 0)), c, h * 1.55)
                    render(os.path.join(OUT, tag + '_side.png'), c + V((h * 3, 0, 0)), c, h * 1.55)
            if set_name == 'all': rep['clips'][clip] = {k: v for k, v in sorted(worst.items(), key=lambda kv: -kv[1][1]) if v[1] > 0.01}
        json.dump(report, open(os.path.join(OUT, 'report.json'), 'w'), indent=1, ensure_ascii=False)
print('BITTI')
