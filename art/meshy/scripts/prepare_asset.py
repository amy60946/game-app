"""
Meshy GLB → Unity'ye hazır FBX + 1024 px dokular.
  python prepare_asset.py model <giriş.glb> <çıkış_klasörü> <ad>         # mesh (+ varsa iskelet)
  python prepare_asset.py anim  <giriş.glb> <çıkış_klasörü> <ad>@<klip>  # yalnız iskelet + animasyon (mesh silinir)
Dokular <ad>_basecolor.jpg ve <ad>_normal.jpg olarak FBX'in yanına yazılır (Unity çalışma anında URP Lit malzemesine bağlar).
Telefon için dokular 1024 px'e küçültülür.
"""
import os, sys, bpy

mode, src, outdir, name = sys.argv[1:5]
TEX = int(sys.argv[5]) if len(sys.argv) > 5 else 1024   # küçük eşyalar için 512
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

if mode == "anim":
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    for a in bpy.data.actions:
        a.name = name.split("@", 1)[1]
else:
    # Meshy iskelet dosyasında yardımcı nesneler olabiliyor (ör. "Icosphere"): iskelet varsa yalnız ona bağlı mesh kalır
    arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if arm:
        for o in list(bpy.context.scene.objects):
            if o.type == "MESH" and not any(m.type == "ARMATURE" for m in o.modifiers):
                print("SILINDI", o.name)
                bpy.data.objects.remove(o, do_unlink=True)
    seen = {}
    for img in list(bpy.data.images):
        if img.size[0] == 0:
            continue
        role = "tex"
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for n in mat.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image == img:
                    for l in n.outputs[0].links:
                        sock = l.to_socket.name.lower()
                        if "base color" in sock: role = "basecolor"
                        elif "color" in sock and l.to_node.type == "NORMAL_MAP": role = "normal"
                    for l in n.outputs[0].links + (n.outputs[1].links if len(n.outputs) > 1 else []):
                        if l.to_node.type == "NORMAL_MAP": role = "normal"
                        if l.to_node.type in ("SEPRGB", "SEPARATE_COLOR", "SEPARATE_RGB"): role = "mr"
        if role in seen.values() and role != "tex":
            role = role + str(len(seen))
        seen[img.name] = role
        if role.startswith("mr"):
            continue   # Unity'de sabit pürüzlülük kullanılır; depo küçük kalsın
        if max(img.size) > TEX:
            img.scale(TEX, TEX)
        path = os.path.join(outdir, f"{name}_{role}.jpg")
        img.filepath_raw = path
        img.file_format = "JPEG"
        bpy.context.scene.render.image_settings.quality = 92
        img.save()
        img.filepath = path
    print("DOKULAR", seen)

out = os.path.join(outdir, name + ".fbx")
bpy.ops.export_scene.fbx(filepath=out, use_selection=False, path_mode="RELATIVE", embed_textures=False,
                         apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y",
                         add_leaf_bones=False, bake_anim=(mode == "anim"), bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, bake_anim_simplify_factor=1.0)
print("YAZILDI", out, os.path.getsize(out))
