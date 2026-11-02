"""
"Yürü" simgesi (GB20-8, 2 Kasım 2026; kullanıcı: "harita görünümünde harita simgesi yerine adım/ayakkabı simgesi + Yürü"):
Resources/Icons/act_walk.png, 256×256, saydam zemin. Eylem simgeleriyle (act_jump, act_enter) aynı yumuşak kil/oyuncak dili:
mercan renkli bez ayakkabı, beyaz taban ve burun, beyaz bağcıklar, yanda sarı yıldız. Kodla (Blender Cycles) çizilir, kredi harcanmaz.
Marka çağrıştıran şerit/logo yok.
Kullanım: python3.11 -I art/scripts/ui_walk_icon.py [çıkış.png]
"""
import math
import os
import sys

if "--crop" not in sys.argv:
    import bpy
    from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
def crop(src, dst):
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    bb = im.getbbox()
    side = max(bb[2] - bb[0], bb[3] - bb[1])
    pad = int(side * 0.06)
    cx, cy = (bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2
    half = side // 2 + pad
    im.crop((cx - half, cy - half, cx + half, cy + half)).resize((256, 256), Image.LANCZOS).save(dst)


OUT = sys.argv[-1] if len(sys.argv) > 1 and sys.argv[-1].endswith(".png") else os.path.join(HERE, "..", "..", "Assets", "_Pofi", "Resources", "Icons", "act_walk.png")


def mat(name, rgb, rough=0.42, spec=0.35):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = spec
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 0.25; b.inputs["Coat Roughness"].default_value = 0.2
    return m


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def rounded_box(name, size, loc, bevel, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    mod = o.modifiers.new("b", "BEVEL"); mod.width = bevel; mod.segments = 8; mod.limit_method = "NONE"
    sub = o.modifiers.new("s", "SUBSURF"); sub.levels = 2; sub.render_levels = 2
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def blob(name, scale, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = scale
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def capsule(name, a, b, r, m):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object; o.name = name
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.data.materials.append(m)
    for p in (a, b):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=r, location=p)
        bpy.context.object.data.materials.append(m)
        bpy.ops.object.shade_smooth()
    return o


def star(name, loc, r, m, rot):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((math.cos(a) * rr, math.sin(a) * rr, 0))
    me = bpy.data.meshes.new(name)
    me.from_pydata(pts + [(0, 0, 0)], [], [(i, (i + 1) % 10, 10) for i in range(10)])
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    sol = o.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.06; sol.offset = 0
    bv = o.modifiers.new("b", "BEVEL"); bv.width = 0.02; bv.segments = 3; bv.limit_method = "NONE"
    me.materials.append(m)
    return o


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    coral, coral_d = mat("coral", srgb("#F4503C")), mat("coral_d", srgb("#C2342C"))
    white, sole_d = mat("white", srgb("#FFFFFF"), 0.5), mat("sole_d", srgb("#C9D3E2"), 0.55)
    yellow = mat("yellow", srgb("#FFD23F"), 0.35)
    # taban (beyaz + alt gri şerit), gövde (alçak ön + yüksek topuk), beyaz burun, bilek ağzı, dil, bağcıklar, yanda yıldız
    rounded_box("sole", (2.25, 0.92, 0.3), (0.0, 0, 0.17), 0.13, white)
    rounded_box("sole_b", (2.27, 0.94, 0.1), (0.0, 0, 0.05), 0.05, sole_d)
    rounded_box("body", (1.95, 0.84, 0.6), (-0.06, 0, 0.56), 0.28, coral)
    rounded_box("ankle", (0.95, 0.82, 0.62), (-0.52, 0, 0.98), 0.27, coral)
    blob("cap", (0.42, 0.46, 0.3), (0.86, 0, 0.42), white)
    rounded_box("tongue", (0.32, 0.56, 0.42), (-0.1, 0, 1.12), 0.15, coral_d, rot=(0, math.radians(-28), 0))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.33, minor_radius=0.08, location=(-0.55, 0, 1.3))   # bilek ağzı
    t = bpy.context.object; t.scale = (1.15, 1.0, 1); t.data.materials.append(coral_d); bpy.ops.object.shade_smooth()
    for i, (x, z) in enumerate(((-0.02, 0.93), (0.2, 0.9), (0.42, 0.86))):
        capsule(f"lace{i}", (x - 0.05, -0.34, z), (x + 0.05, 0.34, z), 0.055, white)
    star("star", (-0.42, -0.43, 0.72), 0.24, yellow, (math.radians(90), 0, 0))

    # kamera: 3/4 yan, hafif yukarıdan, dik izdüşüm
    cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = 2.9
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (1.5, -6.4, 2.2)
    co.rotation_euler = (Vector((0.0, 0, 0.65)) - co.location).to_track_quat("-Z", "Y").to_euler()
    # ışık: yumuşak üst-sol alan ışığı + doldurma + arka kenar
    for name, loc, energy, size in (("key", (-3, -4, 6), 620, 5), ("fill", (5, -3, 2), 160, 6), ("rim", (1, 5, 4), 400, 4)):
        L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size
        lo = bpy.data.objects.new(name, L); sc.collection.objects.link(lo); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0.5)) - lo.location).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.93, 1.0, 1); w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 96
    sc.render.resolution_x = sc.render.resolution_y = 512
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    tmp = OUT + ".512.png"
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    import subprocess   # PIL python3.11 ortamında yok: kırpma/küçültme sistem python3 ile
    subprocess.run(["python3", "-I", os.path.abspath(__file__), "--crop", tmp, OUT], check=True)
    os.remove(tmp)
    print("yazıldı", os.path.abspath(OUT))


if __name__ == "__main__":
    if "--crop" in sys.argv:
        i = sys.argv.index("--crop"); crop(sys.argv[i + 1], sys.argv[i + 2])
    else:
        build()
