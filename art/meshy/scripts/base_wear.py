"""
Okti'nin temel giysisi (sarı tişört + mercan şort), vücudun kendi ağından (24 Ekim 2026, kullanıcı: "ilk kıyafetler karakterin
vücuduna optimal oturmuyor"). Eski yol: tek parça katı tişört/şort modeli kemiğe takılıyordu; kollar kumaşın içinden çıkıyor,
şortun beli tişörtün ortasına geliyordu.

Bu betik evre modelini (Resources/Pets/pet_13_<evre>/pet_13_<evre>.fbx) açar, gövde ağından giysi bölgesini keser:
  tişört: gövde + omuz + üst kolun yarısı (kısa kol), boyun başın eteğinin altında kalır, etek bel hizasının biraz altında;
  şort:   kalça + uyluğun üst kısmı, beli tişörtün altında kalır.
Kesimler kemik ağırlıkları + düz kesim düzlemleriyle (kol ve bacak kemiğine dik, etek yatay) yapılır: kenarlar düzgün.
Parçalar yüzey normali boyunca biraz dışarı itilir, hafif yumuşatılır ve kalınlık verilir (Solidify). Kemik ağırlıkları vücuttan
gelir: oyunda vücutla aynı kemiklere bağlanır (CosmeticModels.BuildBase), her harekette vücutla birlikte esner.

  python3.11 -I art/meshy/scripts/base_wear.py -- <evre klasörü> [önizleme.png]
Çıktı: <evre klasörü>/<ad>_wear.fbx (iskelet + base_top + base_bottom; animasyon yok).
"""
import math
import os
import sys

import bpy
import bmesh  # bpy'den sonra (PyPI bpy)
from mathutils import Vector as V

args = sys.argv[sys.argv.index("--") + 1:]
STAGE_DIR = os.path.abspath(args[0])
PREVIEW = args[1] if len(args) > 1 else None
NAME = os.path.basename(STAGE_DIR.rstrip("/"))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(STAGE_DIR, NAME + ".fbx"))
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
body = next(o for o in bpy.context.scene.objects if o.type == "MESH")


def short(n):
    return n.split(":")[-1]


def bone(n):
    for b in arm.data.bones:
        if short(b.name) == n:
            return arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local
    raise KeyError(n)


HEAD = {"Head", "HeadTop_End", "headfront"}
TORSO = {"Spine", "Spine1", "Spine2", "Neck", "LeftShoulder", "RightShoulder"}
ARM = {"L": {"LeftArm", "LeftForeArm", "LeftHand", "Bone_029", "Bone_020", "Bone_019"},
       "R": {"RightArm", "RightForeArm", "RightHand", "Bone_030", "Bone_025", "Bone_024"}}
LEG = {"L": {"LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"}, "R": {"RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"}}
GNAME = {g.index: short(g.name) for g in body.vertex_groups}

zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
H = max(zs) - min(zs)
hips, spine = bone("Hips")[0], bone("Spine")[0]
Z_HEM = hips.z + 0.30 * (spine.z - hips.z)          # tişört eteği: belin biraz altı
Z_TOP = hips.z + 0.62 * (spine.z - hips.z)          # şort beli: eteğin altında kalır
Z_NECK = bone("Neck")[0].z + 0.02 * H                 # yaka
_u = [bone(n + "UpLeg")[0].z for n in ("Left", "Right")]; _k = [bone(n + "Leg")[0].z for n in ("Left", "Right")]
Z_LEG = sum(_u) / 2 - 0.40 * (sum(_u) / 2 - sum(_k) / 2)   # şort paçası: uyluğun üst kısmı
print("boy %.3f etek %.3f bel %.3f" % (H, Z_HEM, Z_TOP))


def cats(v, dl):
    d = v[dl]
    s = {"head": 0.0, "torso": 0.0, "hips": 0.0, "armL": 0.0, "armR": 0.0, "legL": 0.0, "legR": 0.0}
    for gi, w in d.items():
        n = GNAME.get(gi, "")
        if n in HEAD: s["head"] += w
        elif n in TORSO: s["torso"] += w
        elif n == "Hips": s["hips"] += w
        elif n in ARM["L"]: s["armL"] += w
        elif n in ARM["R"]: s["armR"] += w
        elif n in LEG["L"]: s["legL"] += w
        elif n in LEG["R"]: s["legR"] += w
    return s


def face_cat(f, dl, key):
    return sum(cats(v, dl)[key] for v in f.verts) / len(f.verts)


def delete_faces(bm, faces):
    bmesh.ops.delete(bm, geom=list(set(faces)), context="FACES")


def cut(bm, faces, co, no):
    """Yalnız bu yüzleri düzlemle böl; düzlemin no yönündeki tarafını sil."""
    faces = [f for f in faces if f.is_valid]
    if not faces:
        return
    geom = list({e for f in faces for e in f.edges}) + list({v for f in faces for v in f.verts}) + faces
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no)
    region = set()
    # bölünen yüzler artık yeni yüzler; kesimden sonra aynı bölgedeki yüzleri yeniden seç (ağırlığa göre çağıran yapar)
    return region


def keep_big(bm, frac=0.03):
    faces = set(bm.faces)
    comps = []
    while faces:
        f0 = faces.pop(); comp = {f0}; stack = [f0]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in faces:
                        faces.discard(g); comp.add(g); stack.append(g)
        comps.append(comp)
    total = len(bm.faces)
    for c in comps:
        if len(c) < frac * total:
            delete_faces(bm, c)


def build(kind):
    me = body.data.copy()
    bm = bmesh.new(); bm.from_mesh(me)
    dl = bm.verts.layers.deform.active
    # baş (etek) ve karşı bölge
    delete_faces(bm, [f for f in bm.faces if face_cat(f, dl, "head") > 0.5])
    if kind == "top":
        # yaka: boyun hizasında düz kesim (başın eteğinin altında kalır)
        cut(bm, list(bm.faces), V((0, 0, Z_NECK)), V((0, 0, 1)))
        delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z > Z_NECK])
        for side in ("L", "R"):
            a0 = bone(("Left" if side == "L" else "Right") + "Arm")[0]
            hand = bone(("Left" if side == "L" else "Right") + "Hand")[0]
            fore = bone(("Left" if side == "L" else "Right") + "ForeArm")[0]
            d = (hand - a0).normalized()
            co = a0 + d * (0.5 * (fore - a0).length)          # kısa kol: üst kolun yarısı
            key = "arm" + side
            faces = [f for f in bm.faces if face_cat(f, dl, key) > 0.4]
            cut(bm, faces, co, d)
            delete_faces(bm, [f for f in bm.faces if face_cat(f, dl, key) > 0.4 and (f.calc_center_median() - co).dot(d) > 0])
        cut(bm, list(bm.faces), V((0, 0, Z_HEM)), V((0, 0, -1)))
        delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z < Z_HEM])
    else:
        delete_faces(bm, [f for f in bm.faces if face_cat(f, dl, "armL") + face_cat(f, dl, "armR") > 0.4])
        cut(bm, list(bm.faces), V((0, 0, Z_TOP)), V((0, 0, 1)))
        delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z > Z_TOP])
        # paça: iki bacakta aynı yükseklikte yatay kesim (Meshy iskeleti asimetrik: kemiğe dik kesim paçaları eğri yapıyordu)
        cut(bm, list(bm.faces), V((0, 0, Z_LEG)), V((0, 0, -1)))
        delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z < Z_LEG])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    keep_big(bm)
    # kumaş: iç noktaları yumuşat (Meshy yüzey pürüzü); kenarlar kesim düzleminde kalır (düz etek, düz kol ağzı)
    inner = [v for v in bm.verts if not v.is_boundary]
    for _ in range(4):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    off = (0.0085 if kind == "top" else 0.0055) * H
    # dışarı itme yönü: iç noktada yüzey normali; kenarda komşu iç noktaların normal ortalaması (kenar normali dağınık → tırtık)
    push = {}
    for v in bm.verts:
        if not v.is_boundary:
            push[v] = v.normal.copy()
    for v in bm.verts:
        if v.is_boundary:
            ns = [e.other_vert(v).normal for e in v.link_edges if not e.other_vert(v).is_boundary]
            n = sum(ns, V((0, 0, 0))) if ns else v.normal.copy()
            push[v] = n.normalized() if n.length > 1e-6 else v.normal.copy()
    for v in bm.verts:
        v.co += push[v] * off * (1.25 if v.is_boundary else 1.0)   # kenar biraz açık: kumaş gibi dursun
    # kenar halkası boyunca hafif düzle (kesim tırtığı kalmasın)
    ring = [v for v in bm.verts if v.is_boundary]
    for _ in range(3):
        new = {}
        for v in ring:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items():
            v.co = c
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("base_" + ("top" if kind == "top" else "bottom"), me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = body.parent; ob.matrix_world = body.matrix_world.copy()
    for g in body.vertex_groups:
        if g.name not in ob.vertex_groups:
            ob.vertex_groups.new(name=g.name)
    sol = ob.modifiers.new("kalınlık", "SOLIDIFY")
    sol.thickness = off * 0.6; sol.offset = -1.0; sol.use_rim = True; sol.use_even_offset = False; sol.use_quality_normals = True
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=sol.name)
    ob.select_set(False)
    mod = ob.modifiers.new("Armature", "ARMATURE"); mod.object = arm
    bpy.ops.object.select_all(action="DESELECT")
    ob.data.materials.clear()
    print(kind, "köşe", len(ob.data.vertices), "yüz", len(ob.data.polygons))
    return ob


top = build("top")
bottom = build("bottom")

out = os.path.join(STAGE_DIR, NAME + "_wear.fbx")
if PREVIEW is None or os.environ.get("WEAR_EXPORT") == "1":
    body_hidden = body
    bpy.ops.object.select_all(action="DESELECT")
    for o in (arm, top, bottom):
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, path_mode="RELATIVE", embed_textures=False,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y",
                             add_leaf_bones=False, bake_anim=False, object_types={"ARMATURE", "MESH"})
    print("YAZILDI", out, os.path.getsize(out))

if PREVIEW:
    # önizleme: dinlenme önden/yandan + yürüme, el sallama, dans kareleri (klip dosyalarından)
    sc = bpy.context.scene
    def mat(name, rgba, tex=None):
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        if tex:
            t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex)
            m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
        else:
            b.inputs["Base Color"].default_value = rgba
        b.inputs["Roughness"].default_value = 0.6
        return m
    body.data.materials.clear(); body.data.materials.append(mat("skin", None, os.path.join(STAGE_DIR, NAME + "_basecolor.jpg")))
    body.hide_render = os.environ.get("WEAR_HIDE_BODY") == "1"   # yalnız giysiyi gör (boşluk denetimi)
    top.data.materials.append(mat("top", (0.98, 0.76, 0.16, 1)))
    bottom.data.materials.append(mat("bottom", (1.0, 0.40, 0.33, 1)))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = H * 1.15; sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16; sc.cycles.use_denoising = False
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.9, 0.95, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(sun)
    sc.render.resolution_x = 360; sc.render.resolution_y = 480
    shots = [("rest", None, 0, 0), ("rest_yan", None, 0, 90), ("rest_arka", None, 0, 180)]
    for clip, fr in [tuple(x.split(":")) for x in os.environ.get("WEAR_SHOTS", "walk:6,walk:18,wave:20,happy:25,dance:30,dance:60,run:8,jump:15").split(",") if x]:
        fr = int(fr)
        if os.path.exists(os.path.join(STAGE_DIR, "%s@%s.fbx" % (NAME, clip))):
            shots.append((clip + "_%d" % fr, clip, fr, 20))
    actions = {}
    import glob
    out_files = []
    for label, clip, fr, yaw in shots:
        if clip and clip not in actions:
            before = set(bpy.data.objects); acts = set(bpy.data.actions)
            bpy.ops.import_scene.fbx(filepath=os.path.join(STAGE_DIR, "%s@%s.fbx" % (NAME, clip)))
            new = [a for a in bpy.data.actions if a not in acts]
            for o in [o for o in bpy.data.objects if o not in before]:
                bpy.data.objects.remove(o, do_unlink=True)
            actions[clip] = new[0] if new else None
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = actions.get(clip) if clip else None
        if not clip:
            for pb in arm.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
        sc.frame_set(fr)
        r = math.radians(yaw)
        cam.location = (math.sin(r) * 6, -math.cos(r) * 6, H * 0.5); cam.rotation_euler = (math.radians(90), 0, r)
        f = PREVIEW.replace(".png", "_%s.png" % label)
        sc.render.filepath = f; bpy.ops.render.render(write_still=True); out_files.append(f)
    print("ONIZLEME", " ".join(out_files))
