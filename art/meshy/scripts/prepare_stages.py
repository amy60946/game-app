"""
Meshy web sitesinden gelen "Rigged_All_Animations" GLB → Unity'ye hazır evre klasörü (Okti, 20 Ekim 2026).
  python prepare_stages.py <giriş.glb> <Resources/Pets> <ad>        # ör. pet_13_yavru
Çıktı: <ad>/<ad>.fbx (mesh + iskelet, dinlenme pozu), <ad>/<ad>@<klip>.fbx (yalnız iskelet + o klip),
<ad>/<ad>_basecolor.jpg (1024 px). Klip adları oyunun adlarına çevrilir (CLIPS); ayak temas anları yazdırılır
(PetWalker adım sesleri için: sol/sağ ayak kemiğinin en alçak olduğu an, döngü içinde 0..1).
"""
import os, sys, bpy

src, root, name = sys.argv[1:4]
TEX = 1024
CLIPS = {"Idle_3": "idle", "Walking": "walk", "Running": "run", "Cheer_with_Both_Hands_Up": "happy",
         "Wave_One_Hand": "wave", "Sleep_Normally": "sleep", "Regular_Jump": "jump"}
# dosyada asıl klip yoksa yerine geçen (kıyafetsiz çocuk Okti, 23 Ekim 2026: sevinç = 360° dönerek zıplama).
# Bekleme (idle) dosyada yoksa kodla üretilir (make_idle). Eski dosyanın klipleri KULLANILAMAZ: iskelet ölçüsü farklıysa
# (eski 0,01 ölçekli santim, yeni metre) kemik konumları 100 kat kayar ve pet ekrandan kaybolur (23 Ekim 2026).
FALLBACK = {"Cheer_with_Both_Hands_Up": "_360_Power_Spin_Jump", "Sleep_Normally": "Cough_While_Sleeping"}
TRIS = int(os.environ.get("POFI_TRIS", "12500"))   # oyun bütçesi (eski evreler ~12,4 bin üçgen)
outdir = os.path.join(root, name)
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
for o in list(bpy.context.scene.objects):   # iskelete bağlı olmayan yardımcı mesh'ler (ör. "Icosphere") gitsin
    if o.type == "MESH" and not any(m.type == "ARMATURE" for m in o.modifiers):
        bpy.data.objects.remove(o, do_unlink=True)

# yeni Meshy dışa aktarımları ~200 bin üçgen: deri ağırlıklarıyla birlikte bütçeye indir (Decimate, Armature'dan önce).
# Bu kadar indirgeme UV dikişlerini kaydırıyor (yüzde ince koyu çatlaklar, 23 Ekim 2026) → indirgenmiş meshe yeni UV açılır ve
# renk dokusu yüksek çokgen kopyadan yeniden pişirilir (POFI_REBAKE=0 ile kapatılır).
import math
from mathutils import Vector
REBAKE = os.environ.get("POFI_REBAKE", "1") == "1"

def deband(o, ya, yb, edge=0.03):
    """Ergen/yetişkin Okti'nin başında yandan yana geçen ince "kulaklık" bandını siler (kullanıcı, 23 Ekim 2026: çocuktaki gibi olsun).
    POFI_DEBAND="ya,yb": bandın derinlik dilimi (dünya y, önden arkaya; art/meshy/scripts ile ölçülür). Dilimdeki her köşe, başın
    merkezinden aynı açıda, dilimin hemen önündeki ve arkasındaki yüzeyin yarıçapına (derinliğe göre ara değer) çekilir; dışarı
    taşmayan (kol gibi kalın) parçalar kalır. Taşınan köşelere değen her yüz, en yakın taşınmamış baş köşesinin rengini alır
    (UV o noktaya): bandın rengi kalmaz."""
    from mathutils import kdtree
    mw = o.matrix_world; inv = mw.inverted(); me = o.data
    bones = {b.name.split(":")[-1]: arm.matrix_world @ b.head_local for b in arm.data.bones}
    nz = bones["Neck"].z; hz = bones["Head"].z
    W = [mw @ v.co for v in me.vertices]
    top = max(w.z for w in W)
    zlo = nz - float(os.environ.get("POFI_DEBAND_LOW", "0.08")) * (top - nz)   # bandın en alt ucu (kollara inmesin)
    head = [i for i, w in enumerate(W) if w.z > zlo]
    cx = (min(W[i].x for i in head) + max(W[i].x for i in head)) / 2; cz = hz + (top - hz) * 0.35
    def polar(w): return math.degrees(math.atan2(w.z - cz, w.x - cx)) % 360, math.hypot(w.x - cx, w.z - cz)
    rf = [0.0] * 360; rb = [0.0] * 360
    # kubbe profili: açı (2°) × derinlik (dilimin iki yanında 4'er şerit) → en büyük yarıçap; dilim içinde ikinci derece eğri
    NB, SW = 4, edge / 2
    prof = {}
    for i in head:
        w = W[i]
        if ya - NB * SW <= w.y < ya or yb < w.y <= yb + NB * SW:
            a, r = polar(w); k = int(a) % 360
            if w.y < ya and w.y >= ya - edge: rf[k] = max(rf[k], r)
            if w.y > yb and w.y <= yb + edge: rb[k] = max(rb[k], r)
            j = int((w.y - ya) // SW) if w.y < ya else int((w.y - yb) // SW) + 1000
            key = (k // 2, j); prof[key] = max(prof.get(key, 0.0), r)
    import numpy as np
    curve = {}
    for kk in range(180):
        ys, rs = [], []
        for j in list(range(-NB, 0)) + list(range(1000, 1000 + NB)):
            r = prof.get((kk, j))
            if r: ys.append(ya + (j + 0.5) * SW if j < 0 else yb + (j - 1000 + 0.5) * SW); rs.append(r)
        if len(ys) >= 5 and min(ys) < ya and max(ys) > yb:
            curve[kk] = np.polyfit(ys, rs, 2)
    def near(arr, k):
        for n in range(2, 12):
            vals = [arr[(k + d) % 360] for d in range(-n, n + 1) if arr[(k + d) % 360] > 0]
            if vals: return max(vals)
        return 0.0
    moved = set()
    for i in head:
        w = W[i]
        if not (ya <= w.y <= yb): continue
        a, r = polar(w); k = int(a) % 360
        f, b = near(rf, k), near(rb, k)
        if f <= 0 or b <= 0: continue
        t = (w.y - ya) / max(1e-6, yb - ya); rt = f + (b - f) * t
        c = curve.get(k // 2)
        if c is not None:
            rq = float(np.polyval(c, w.y))
            if min(f, b) * 0.95 <= rq <= max(f, b) * 1.15: rt = rq   # kubbe eğrisi makulse onu kullan (düz çizgi çukur bırakıyordu)
        if r <= rt + 0.002: continue
        s = rt / r
        nw = w.copy(); nw.x = cx + (w.x - cx) * s; nw.z = cz + (w.z - cz) * s
        me.vertices[i].co = inv @ nw; W[i] = nw
        moved.add(i)
    # renk: taşınan köşeye değen yüz → en yakın taşınmamış baş köşesinin UV'si (tek renk; küçük yüzlerde göze batmaz)
    cm = float(os.environ.get("POFI_DEBAND_COLOR", "0"))   # renk kaynağı dilimden bu kadar uzakta (bant kenarındaki renk karışmasın)
    keep = [i for i in head if i not in moved and not (ya - cm <= W[i].y <= yb + cm)]
    kd = kdtree.KDTree(len(keep))
    for n, i in enumerate(keep): kd.insert(W[i], n)
    kd.balance()
    uv = me.uv_layers.active.data
    first = {}
    for l in me.loops: first.setdefault(l.vertex_index, l.index)
    faces = 0
    for p in me.polygons:
        if not any(v in moved for v in p.vertices): continue
        c = sum((W[v] for v in p.vertices), Vector((0, 0, 0))) / len(p.vertices)
        _, n, _ = kd.find(c)
        src = uv[first[keep[n]]].uv.copy()
        for li in p.loop_indices: uv[li].uv = src
        faces += 1
    me.update()
    # dilim kenarındaki sırtı ve sivrilikleri yumuşat (dilim ± kenar, baş bölgesi; taşınan köşelerin çevresi)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    ring = set(moved)
    for _ in range(int(os.environ.get("POFI_DEBAND_RING", "5"))):
        ring |= {e.other_vert(bm.verts[i]).index for i in list(ring) for e in bm.verts[i].link_edges}
    sel = [bm.verts[i] for i in ring if W[i].z > zlo and ya - edge <= W[i].y <= yb + edge]
    for _ in range(int(os.environ.get("POFI_DEBAND_SMOOTH", "12"))):
        bmesh.ops.smooth_vert(bm, verts=sel, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(me); bm.free(); me.update()
    print("BANT SİLİNDİ", len(moved), "köşe,", faces, "yüz boyandı,", len(sel), "köşe yumuşatıldı")

baked = None
for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if tris > TRIS * 1.1 or os.environ.get("POFI_DEBAND"):
        # glTF içe aktarımı UV dikişlerinde köşeleri ayırır: indirgemede dikişler ayrı ayrı çöker ve yüzeyde ince yarıklar açılır
        # (yüzde koyu çatlaklar, 23 Ekim 2026) → önce aynı yerdeki köşeleri kaynak (UV köşe başına kalır)
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=max(o.dimensions) * 1e-5)
        bpy.ops.object.mode_set(mode="OBJECT")
        hi = None
        if os.environ.get("POFI_DEBAND"):
            sub = int(os.environ.get("POFI_SUBDIV", "0"))
            if sub:
                bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
                sd = o.modifiers.new("subdiv", "SUBSURF"); sd.levels = sub; sd.render_levels = sub
                bpy.ops.object.modifier_move_to_index(modifier="subdiv", index=0); bpy.ops.object.modifier_apply(modifier="subdiv")
                print("ALT BÖLÜNDÜ", len(o.data.polygons), "yüz")
            deband(o, *[float(x) for x in os.environ["POFI_DEBAND"].split(",")])
            # bant yerinde katlanan yüzler ince koyu çizgi bırakıyordu → yüzey voksel ile yeniden örülür (temiz, kapalı yüzey),
            # deri ağırlıkları eski ağdan aktarılır; renk aşağıda eski ağdan yeniden pişirilir
            hi = o.copy(); hi.data = o.data.copy(); bpy.context.scene.collection.objects.link(hi)
            bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
            rm = o.modifiers.new("remesh", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = max(o.dimensions) * float(os.environ.get("POFI_VOXEL", "0.0035"))
            bpy.ops.object.modifier_move_to_index(modifier="remesh", index=0); bpy.ops.object.modifier_apply(modifier="remesh")
            o.vertex_groups.clear()
            for g in hi.vertex_groups: o.vertex_groups.new(name=g.name)
            dt = o.modifiers.new("weights", "DATA_TRANSFER"); dt.object = hi; dt.use_vert_data = True
            dt.data_types_verts = {"VGROUP_WEIGHTS"}; dt.vert_mapping = "POLYINTERP_NEAREST"
            dt.layers_vgroup_select_src = "ALL"; dt.layers_vgroup_select_dst = "NAME"
            bpy.ops.object.modifier_move_to_index(modifier="weights", index=0); bpy.ops.object.modifier_apply(modifier="weights")
            if not o.data.uv_layers: o.data.uv_layers.new(name="UVMap")
            # örülen yüzeyde dilim kenarlarındaki ince oluklar: yalnız bant şeridinde yumuşat, sonra yumuşak gölgelendirme
            import bmesh
            ya, yb = [float(x) for x in os.environ["POFI_DEBAND"].split(",")]
            mw = o.matrix_world; nzz = (arm.matrix_world @ next(b for b in arm.data.bones if b.name.endswith("Neck")).head_local).z
            bm = bmesh.new(); bm.from_mesh(o.data)
            band = [v for v in bm.verts if (mw @ v.co).z > nzz and ya - 0.06 <= (mw @ v.co).y <= yb + 0.06]
            for _ in range(int(os.environ.get("POFI_DEBAND_SMOOTH2", "25"))):
                bmesh.ops.smooth_vert(bm, verts=band, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            bm.to_mesh(o.data); bm.free()
            o.data.shade_smooth()
            tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
            print("YENİDEN ÖRÜLDÜ", tris, "üçgen")
        if REBAKE and hi is None:
            hi = o.copy(); hi.data = o.data.copy(); bpy.context.scene.collection.objects.link(hi)
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        d = o.modifiers.new("decimate", "DECIMATE"); d.ratio = TRIS / tris
        bpy.ops.object.modifier_move_to_index(modifier="decimate", index=0)
        bpy.ops.object.modifier_apply(modifier="decimate")
        print("AZALTILDI", o.name, tris, "→", sum(len(p.vertices) - 2 for p in o.data.polygons), "üçgen")
        if hi is None:
            continue
        sc = bpy.context.scene
        arm.data.pose_position = "REST"; bpy.context.view_layer.update()
        sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 4
        old_uv = [l.name for l in o.data.uv_layers]
        uv = o.data.uv_layers.new(name="rebake"); o.data.uv_layers.active = uv
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
        bpy.ops.object.mode_set(mode="OBJECT")
        baked = bpy.data.images.new("rebaked", TEX * 2, TEX * 2, alpha=False)
        mat = o.data.materials[0]
        node = mat.node_tree.nodes.new("ShaderNodeTexImage"); node.image = baked; mat.node_tree.nodes.active = node
        # kaynak dokuyu eski UV'ye sabitle (indirgenmiş meshte etkin UV artık "rebake")
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n is not node and not n.inputs["Vector"].links:
                uvn = mat.node_tree.nodes.new("ShaderNodeUVMap"); uvn.uv_map = old_uv[0]
                mat.node_tree.links.new(uvn.outputs["UV"], n.inputs["Vector"])
        dims = max(o.dimensions); hi.data.uv_layers[0].name = old_uv[0]
        bpy.ops.object.select_all(action="DESELECT"); hi.select_set(True); o.select_set(True); bpy.context.view_layer.objects.active = o
        sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.use_pass_color = True
        sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = dims * 0.003; sc.render.bake.max_ray_distance = dims * 0.012
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=8, use_clear=True)
        bpy.data.objects.remove(hi, do_unlink=True)
        for n in old_uv:
            o.data.uv_layers.remove(o.data.uv_layers[n])
        o.data.uv_layers["rebake"].name = "UVMap"
        m2 = bpy.data.materials.new("okti"); m2.use_nodes = True
        t2 = m2.node_tree.nodes.new("ShaderNodeTexImage"); t2.image = baked
        m2.node_tree.links.new(t2.outputs["Color"], m2.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        o.data.materials.clear(); o.data.materials.append(m2)
        arm.data.pose_position = "POSE"
        print("YENIDEN PIŞIRILDI", o.name)

# doku: tek temel renk dokusu → 1024 px JPEG (yeniden pişirildiyse o)
def base_color_images():
    out = []
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                for l in n.inputs["Base Color"].links:
                    if l.from_node.type == "TEX_IMAGE" and l.from_node.image: out.append(l.from_node.image)
    return out + [i for i in bpy.data.images if i not in out]
for img in ([baked] if baked is not None else base_color_images()):
    if img.size[0] == 0:
        continue
    if max(img.size) > TEX:
        img.scale(TEX, TEX)
    path = os.path.join(outdir, f"{name}_basecolor.jpg")
    img.filepath_raw = path
    img.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 90
    img.save()
    img.filepath = path
    break

def export(path, bake):
    bpy.ops.export_scene.fbx(filepath=path, use_selection=False, path_mode="RELATIVE", embed_textures=False,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y",
                             add_leaf_bones=False, bake_anim=bake, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=1.0)
    print("YAZILDI", os.path.basename(path), os.path.getsize(path))

# glTF içe aktarıcı eylem adına nesne adını ekler ("Idle_3_target_character"): öneki eşle
actions = {}
for a in bpy.data.actions:
    for k in CLIPS:
        for src in (k, FALLBACK.get(k)):
            if src and (a.name == src or a.name.startswith(src + "_")) and (k not in actions or src == k):
                actions[k] = a
ad = arm.animation_data or arm.animation_data_create()
for track in list(ad.nla_tracks):
    ad.nla_tracks.remove(track)

def rest_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)

def make_idle(walk, frames=60):
    """Kodla bekleme klibi (2 sn döngü): kollar yürüyüşteki ortalama duruşta (yanlarda), gövde nefes alır gibi hafifçe esner,
    baş hafifçe yana sallanır, kalça çok az iner kalkar. Tüm kemikler anahtarlanır (yürüyüşten geçişte bacak açık kalmasın)."""
    import math, mathutils
    sc = bpy.context.scene
    arms = ["mixamorig:" + sd + part for sd in ("Left", "Right") for part in ("Shoulder", "Arm", "ForeArm", "Hand")]
    acc = {}
    if walk is not None:
        ad.action = walk
        f0, f1 = int(walk.frame_range[0]), int(walk.frame_range[1])
        for f in range(f0, f1):
            sc.frame_set(f)
            for n in arms:
                pb = arm.pose.bones.get(n)
                if pb is None: continue
                q = pb.rotation_quaternion.copy() if pb.rotation_mode == "QUATERNION" else pb.rotation_euler.to_quaternion()
                if n in acc:
                    if acc[n].dot(q) < 0: q.negate()
                    acc[n] = mathutils.Quaternion([acc[n][i] + q[i] for i in range(4)])
                else:
                    acc[n] = q
    mean = {n: q.normalized() for n, q in acc.items()}
    ad.action = None; rest_pose()
    idle = bpy.data.actions.new("Idle_3"); ad.action = idle
    R = math.radians
    for f in range(0, frames + 1, 5):
        t = f / frames * 2 * math.pi
        rest_pose()
        for pb in arm.pose.bones:
            n = pb.name
            if n in mean:
                sway = mathutils.Quaternion((0, 0, 1), R(2.0 * math.sin(t + (0 if "Left" in n else math.pi))))
                pb.rotation_quaternion = mean[n] @ sway
            elif n.endswith(("Spine", "Spine1", "Spine2")):
                pb.rotation_quaternion = mathutils.Quaternion((1, 0, 0), R(1.2 * math.sin(t)))
            elif n.endswith("Neck"):
                pb.rotation_quaternion = mathutils.Quaternion((1, 0, 0), R(-0.8 * math.sin(t)))
            elif n.endswith("Head"):
                pb.rotation_quaternion = mathutils.Quaternion((0, 0, 1), R(2.2 * math.sin(t + 0.7)))
            elif n.endswith("Hips"):
                pb.location = (0, 0.004 * (pb.bone.length or 1.0) * math.sin(2 * t), 0)
            pb.keyframe_insert("rotation_quaternion", frame=f); pb.keyframe_insert("location", frame=f)
    ad.action = None; rest_pose()
    print("ÜRETİLDİ idle", frames, "kare")
    return idle

if "Idle_3" not in actions:
    actions["Idle_3"] = make_idle(actions.get("Walking"))

# 1) model: dinlenme pozu, animasyonsuz
ad.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
export(os.path.join(outdir, name + ".fbx"), False)

if os.environ.get("POFI_MESH_ONLY") == "1":   # yalnız model + doku (klipler aynı kalır)
    sys.exit(0)

# 2) klipler: mesh'siz, tek klip
for o in list(bpy.context.scene.objects):
    if o.type == "MESH":
        bpy.data.objects.remove(o, do_unlink=True)
scene = bpy.context.scene
for src_name, clip in CLIPS.items():
    act = actions.get(src_name)
    if act is None:
        print("YOK", src_name); continue
    act.name = clip
    ad.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    scene.frame_start, scene.frame_end = f0, f1
    export(os.path.join(outdir, f"{name}@{clip}.fbx"), True)
    if clip in ("walk", "run"):
        # ayak temas anları: ayak kemiğinin dünya yüksekliği en alçak kare
        def foot_z(bone, f):
            scene.frame_set(f)
            pb = arm.pose.bones.get(bone)
            return (arm.matrix_world @ pb.head).z if pb else 0.0
        n = f1 - f0
        for side in ("mixamorig:LeftFoot", "mixamorig:RightFoot"):
            zs = [foot_z(side, f) for f in range(f0, f1)]
            k = min(range(len(zs)), key=lambda i: zs[i])
            print("TEMAS", clip, side.split(":")[-1], round(k / max(1, n), 2))
    print("KLIP", clip, f0, f1, "kare")
