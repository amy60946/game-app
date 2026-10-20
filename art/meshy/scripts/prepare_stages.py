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
outdir = os.path.join(root, name)
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
for o in list(bpy.context.scene.objects):   # iskelete bağlı olmayan yardımcı mesh'ler (ör. "Icosphere") gitsin
    if o.type == "MESH" and not any(m.type == "ARMATURE" for m in o.modifiers):
        bpy.data.objects.remove(o, do_unlink=True)

# doku: tek temel renk dokusu → 1024 px JPEG
for img in list(bpy.data.images):
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
        if a.name == k or a.name.startswith(k + "_"):
            actions[k] = a
ad = arm.animation_data or arm.animation_data_create()
for track in list(ad.nla_tracks):
    ad.nla_tracks.remove(track)

# 1) model: dinlenme pozu, animasyonsuz
ad.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
export(os.path.join(outdir, name + ".fbx"), False)

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
