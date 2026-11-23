"""Moyo Oyun simgesi: kol uçları + vantuzlar kodla (kullanıcı, 23 Kasım 2026: "Kodla yarat"; Meshy denemeleri yüzü koruyamadı).

Bugünkü simge (art/icons/moyo_oyun/src_oyun.png) piksel piksel korunur. Resmin alt kenarında kesilen bacakların uçları sudan
yukarı kıvrılmış 3B tüpler olarak Blender'da (Cycles, saydam zemin, dik kamera: 1 birim = 1 piksel) çizilir; kıvrımın iç yüzünde
vantuz halkaları durur. Çizim simgenin üstüne yumuşak gölgesiyle bindirilir; sağ alttaki rozet alanına (x ≥ 694, y ≥ 699) girilmez.

Kullanım (bpy yalnız python3.11'de):
    python3.11 -I art/scripts/app_icon_tentacles.py <çıktı_klasörü> [vantuz: pembe|mavi] [uçlar: 2|3]
Çıktı: <klasör>/tentacles.png (saydam çizim), <klasör>/icon_raw.png (rozetsiz simge).
Rozet sonra art/scripts/app_icon_moyo.py ile eklenir (girdi olarak icon_raw.png verilerek).
"""
import math, os, sys

import bpy
import bmesh
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = sys.argv[1]
SUCKER = sys.argv[2] if len(sys.argv) > 2 else "pembe"
TIPS = int(sys.argv[3]) if len(sys.argv) > 3 else 2
os.makedirs(OUT, exist_ok=True)
S = 1024

# Yol noktaları (resim pikseli: x sağa, y aşağı), taban kalınlığı, uç kalınlığı. Ölçüler alt ajanın yerleşim ölçümünden:
# A bacağı sol alta, C bacağı rozetin soluna (x < 694), B bacağı ortada. iOS köşe maskesi: y 1000'de x ≥ 130, y 1024'te x ≥ 229.
PATHS = {
    "A": ([(300, 1075), (268, 1010), (228, 968), (186, 948), (150, 950), (131, 968), (134, 990), (152, 999), (169, 989), (170, 973)], 33, 7),
    "C": ([(567, 1075), (588, 1018), (614, 986), (642, 972), (665, 980), (670, 1001), (657, 1013), (641, 1007), (641, 994)], 30, 6),
    "B": ([(432, 1075), (410, 1020), (380, 993), (350, 987), (333, 1000), (337, 1016), (352, 1020), (360, 1009)], 27, 6),
}
ORDER = ["A", "C", "B"][:TIPS]


def srgb(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


def catmull(points, n):
    """Noktalardan geçen düzgün eğri (Catmull–Rom), n örnek."""
    p = [points[0]] + list(points) + [points[-1]]
    out = []
    segs = len(points) - 1
    for i in range(n):
        t = i / (n - 1) * segs
        k = min(int(t), segs - 1)
        u = t - k
        p0, p1, p2, p3 = p[k], p[k + 1], p[k + 2], p[k + 3]
        out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u * u
                                + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u * u * u) for j in range(2)))
    return out


def world(x, y, z=0.0):
    return Vector((x, -y, z))


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, rough, coat=0.0, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(rgb)
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    return m


def tube(name, pts, r0, r1, mat):
    """Yol boyunca kalınlığı azalan tüp; iç yüz (kıvrım merkezine bakan taraf) yönleri ve yarıçaplar döner."""
    n = 140
    path = catmull(pts, n)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    ring = 28
    rings, info = [], []
    for i, (x, y) in enumerate(path):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        tx, ty = tx / l, ty / l
        nx, ny = -ty, tx                     # yolun solu
        # kıvrımın içi: eğrilik işareti
        a2 = path[max(i - 4, 0)]
        b2 = path[min(i + 4, n - 1)]
        cross = (x - a2[0]) * (b2[1] - y) - (y - a2[1]) * (b2[0] - x)
        sgn = 1.0 if cross > 0 else -1.0
        t = i / (n - 1)
        r = r0 + (r1 - r0) * (t ** 1.15)
        nrm = Vector((nx, -ny, 0.0))         # dünya koordinatında (y ters)
        zv = Vector((0, 0, 1))
        c = world(x, y)
        vs = []
        for k in range(ring):
            ph = 2 * math.pi * k / ring
            vs.append(bm.verts.new(c + r * (math.cos(ph) * nrm + math.sin(ph) * zv)))
        rings.append(vs)
        info.append((c, nrm * sgn, r, t))
    for i in range(n - 1):
        for k in range(ring):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % ring], rings[i + 1][(k + 1) % ring], rings[i + 1][k]))
    tip = bm.verts.new(info[-1][0] + (Vector(info[-1][0]) - Vector(info[-2][0])).normalized() * r1 * 0.9)
    for k in range(ring):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % ring], tip))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return info


def sucker(c, inward, r, ring_mat, hole_mat):
    """Tüp yüzeyinde, kıvrımın içine ve kameraya yarı dönük vantuz (halka + çukur)."""
    d = (inward.normalized() * math.cos(math.radians(48)) + Vector((0, 0, 1)) * math.sin(math.radians(48))).normalized()
    pos = c + d * (r * 0.93)
    rad = r * 0.46
    bpy.ops.mesh.primitive_torus_add(major_radius=rad, minor_radius=rad * 0.34, major_segments=24, minor_segments=10,
                                     location=pos)
    tor = bpy.context.active_object
    tor.rotation_mode = "QUATERNION"
    tor.rotation_quaternion = d.to_track_quat("Z", "Y")
    tor.data.materials.append(ring_mat)
    for p in tor.data.polygons:
        p.use_smooth = True
    bpy.ops.mesh.primitive_cylinder_add(radius=rad * 0.72, depth=rad * 0.25, vertices=24, location=pos - d * rad * 0.05)
    cyl = bpy.context.active_object
    cyl.rotation_mode = "QUATERNION"
    cyl.rotation_quaternion = d.to_track_quat("Z", "Y")
    cyl.data.materials.append(hole_mat)


def main():
    clear()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 96
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = S
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"

    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = S
    cam.clip_start, cam.clip_end = 1.0, 5000.0
    co = bpy.data.objects.new("cam", cam)
    co.location = (S / 2, -S / 2, 2000)
    sc.collection.objects.link(co)
    sc.camera = co

    # ışık: güneş sağ üstten ve önden, sıcak; ortam serin (simgenin ışığı)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.4
    sun.color = (1.0, 0.94, 0.84)
    sun.angle = math.radians(18)
    so = bpy.data.objects.new("sun", sun)
    so.rotation_mode = "QUATERNION"
    so.rotation_quaternion = Vector((-0.55, -0.62, -1.0)).normalized().to_track_quat("-Z", "Y")
    sc.collection.objects.link(so)
    rim = bpy.data.lights.new("rim", "SUN")
    rim.energy = 1.2
    rim.color = (1.0, 0.96, 0.88)
    ro = bpy.data.objects.new("rim", rim)
    ro.rotation_mode = "QUATERNION"
    ro.rotation_quaternion = Vector((0.7, 0.2, 0.35)).normalized().to_track_quat("-Z", "Y")
    sc.collection.objects.link(ro)
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = srgb((150, 185, 215))
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.75
    sc.world = w

    skin = material("deri", (78, 152, 204), 0.33, coat=0.45)
    ring_rgb = (247, 196, 208) if SUCKER == "pembe" else (205, 232, 248)
    hole_rgb = (214, 140, 160) if SUCKER == "pembe" else (120, 170, 214)
    ring_m = material("vantuz", ring_rgb, 0.4, coat=0.3)
    hole_m = material("cukur", hole_rgb, 0.55)

    for key in ORDER:
        pts, r0, r1 = PATHS[key]
        info = tube("kol_" + key, pts, r0, r1, skin)
        # vantuzlar: yolun görünen son %55'inde, aralık yerel kalınlığa göre
        t_next = 0.42
        for c, inward, r, t in info:
            if t >= t_next and t < 0.94 and c.y > -1020:
                sucker(c, inward, r, ring_m, hole_m)
                t_next = t + max(0.07, (r / 30.0) * 0.13)

    sc.render.filepath = os.path.join(OUT, "tentacles.png")
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    print("yazıldı", sc.render.filepath)


main()
