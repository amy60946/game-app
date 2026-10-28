"""Ebeveyn avatarı taslakları: oyundaki yetişkin Okti'nin anne/baba yorumları, profil fotoğrafı kadrajı (27 Ekim 2026).

ParentApp penceresinin isteği (kullanıcı: "Okti'nin kadın ve erkek versiyonları, profil foto şeklinde; taslakları ilet, beraber seçelim").
Model ve eşyalar oyundakiler (Resources/Pets/pet_13_yetiskin, Resources/Items/*); süs parçaları (kirpik, çiçek, fiyonk, bıyık) kodla.
Meshy kredisi harcanmaz.

Kullanım (bpy 4.2 + Pillow kurulu Python):
  nice -n 10 <python> -I art/parent_avatars/make_drafts.py [kimlik ...] [--out KLASÖR] [--samples N] [--size PX]
    kimlik: okti_anne_1..3, okti_baba_1..3 (boşsa hepsi); çıktı <kimlik>.png (kare, sade açık zemin),
    seffaf/<kimlik>.png (aynı kare, şeffaf zemin; oyun içi kullanım için) + sheet.png (kare + yuvarlak kırpma yan yana)
"""
import json
import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector as V

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
RES = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources')
RULES = json.load(open(os.path.join(ROOT, 'art', 'meshy', 'scripts', 'okti_fit_rules.json')))
STAGE = 'yetiskin'   # evre (çocuk portreleri 'yavru'); main her taslakta ayarlar
K = 1.0              # baş ölçeği: yetişkin Okti'de göz → baş tepesi 0,181 m = 1; süsler ve kamera bununla büyür


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def reset(samples, res):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 3
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = -0.45
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = srgb('#EAF4FF'); bg.inputs[1].default_value = 0.55


def import_fbx(p):
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=p)
    return [o for o in bpy.data.objects if o.name not in before]


def bounds(objs):
    pts = [o.matrix_world @ V(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    return (V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def bone_pos(arm, name):
    for b in arm.data.bones:
        if b.name == name or b.name.endswith(':' + name):
            return arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local
    return None


def tex_material(name, path, hue=0.5, sat=1.0, val=1.0, rough=0.45, mix=None, keep_red=False):
    """Renk dokusu + ton kaydırma (Hue/Saturation). mix=(renk, oran): dokuyu bir renge doğru boyar (giysi tonu).
    keep_red: kırmızı bölgeler (Okti'nin ağzı) özgün renginde kalır; yalnız mavi gövde kayar."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
    hs = nt.nodes.new('ShaderNodeHueSaturation')
    hs.inputs['Hue'].default_value = hue; hs.inputs['Saturation'].default_value = sat; hs.inputs['Value'].default_value = val
    nt.links.new(t.outputs['Color'], hs.inputs['Color'])
    out = hs.outputs['Color']
    if keep_red:
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        sub = nt.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'
        nt.links.new(sep.outputs['Red'], sub.inputs[0]); nt.links.new(sep.outputs['Blue'], sub.inputs[1])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.use_clamp = True; mul.inputs[1].default_value = 5.0
        nt.links.new(sub.outputs[0], mul.inputs[0])
        km = nt.nodes.new('ShaderNodeMix'); km.data_type = 'RGBA'
        nt.links.new(mul.outputs[0], km.inputs['Factor']); nt.links.new(out, km.inputs[6]); nt.links.new(t.outputs['Color'], km.inputs[7])
        out = km.outputs[2]
    if mix:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = mix[1]
        nt.links.new(out, mx.inputs[6]); mx.inputs[7].default_value = srgb(mix[0])
        out = mx.outputs[2]
    nt.links.new(out, p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = rough
    return m


def flat_material(name, hexc, rough=0.4, metal=0.0, sss=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = srgb(hexc)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
    if emit:   # göz ışıltısı: ışıktan bağımsız beyaz
        p.inputs['Emission Color'].default_value = srgb(hexc); p.inputs['Emission Strength'].default_value = emit
    return m


def set_mat(objs, m):
    for o in objs:
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(m)


# ---------------------------------------------------------------- Okti + giysi

def load_okti(look):
    base = os.path.join(RES, 'Pets', 'pet_13_' + STAGE, 'pet_13_' + STAGE)
    pet = import_fbx(base + '.fbx')
    set_mat(pet, tex_material('okti', base + '_basecolor.jpg', *look.get('body', (0.5, 1.0, 1.0)), rough=0.38, keep_red=True))
    arm = next(o for o in pet if o.type == 'ARMATURE')
    wear = import_fbx(base + '_wear.fbx')
    for o in wear:
        if o.type != 'MESH':
            continue
        part = 'base_bottom' if 'bottom' in o.name.lower() or 'short' in o.name.lower() else 'base_top'
        tex = os.path.join(RES, 'Items', part, 'shell_basecolor.png')
        if not os.path.exists(tex):
            tex = os.path.join(RES, 'Items', part, part + '_basecolor.jpg')
        o.data.materials.clear()
        o.data.materials.append(tex_material(o.name, tex, *look.get('top', (0.5, 1.0, 1.0)), rough=0.7, mix=look.get('top_mix')))
    bpy.context.view_layer.update()
    return pet, arm, wear


def eyes(pet):
    """Göz merkezleri: renk dokusunda en koyu (siyah göz) noktaların 3B konumu, sağ/sol küme."""
    me = next(o for o in pet if o.type == 'MESH')
    img = next(n.image for n in me.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')
    w, h = img.size; px = list(img.pixels)
    uv = me.data.uv_layers.active.data
    mn, mx = bounds(pet); H = mx.z - mn.z
    hits = []
    for poly in me.data.polygons:
        for li in poly.loop_indices:
            u, v = uv[li].uv
            x = min(w - 1, max(0, int(u * w))); y = min(h - 1, max(0, int(v * h)))
            i = (y * w + x) * 4
            if px[i] + px[i + 1] + px[i + 2] < 0.25:
                co = me.matrix_world @ me.data.vertices[me.data.loops[li].vertex_index].co
                # yalnız yüzün önü, baş yüksekliği (eteğin içindeki koyu dikişler sayılmaz)
                if co.z > mn.z + 0.75 * H and co.y < mn.y + 0.25 * (mx.y - mn.y):
                    hits.append(co)
    out = []
    for side in (-1, 1):
        pts = [p for p in hits if p.x * side > 0]
        if pts:
            out.append(sum(pts, V()) / len(pts))
    return out, H


# ---------------------------------------------------------------- oyundaki eşyalar (CosmeticModels yerleşimi)

def place_item(pet, arm, item_id, slot, tweak=None):
    rule = dict(RULES.get(STAGE + ':' + slot) or RULES.get(slot))
    io = RULES.get(STAGE + ':item:' + item_id) or RULES.get('item:' + item_id, {})
    tw = tweak or {}
    size = rule['size'] * io.get('size', 1.0) * tw.get('size', 1.0)
    up = rule.get('up', 0) + io.get('up', 0.0) + tw.get('up', 0.0)
    fwd = rule.get('fwd', 0) + io.get('fwd', 0.0) + tw.get('fwd', 0.0)
    mn, mx = bounds(pet); h = mx.z - mn.z
    fbx = os.path.join(RES, 'Items', item_id, item_id + '.fbx')
    objs = import_fbx(fbx)
    tex = next((p for p in (os.path.join(RES, 'Items', item_id, item_id + '_basecolor.' + e) for e in ('jpg', 'png')) if os.path.exists(p)), None)
    if tex:
        set_mat(objs, tex_material(item_id, tex, *tw.get('tone', (0.5, 1.0, 1.0)), rough=0.5))
    root = bpy.data.objects.new('it_' + item_id, None); bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    if io.get('flip'):
        root.rotation_euler = (0, 0, math.pi)
    bpy.context.view_layer.update()
    imn, imx = bounds(objs); w = max(imx.x - imn.x, imx.y - imn.y)
    root.scale = V((1, 1, 1)) * (size * h / max(w, 1e-4)); bpy.context.view_layer.update()
    imn, imx = bounds(objs); c = (imn + imx) / 2
    head = (bone_pos(arm, 'Head') or bone_pos(arm, 'head'))[0]
    if slot == 'head':
        tgt = V((head.x, head.y + fwd * h, mx.z + up * h))
        y = tgt.z - (imn.z - root.location.z)
        root.location = V((tgt.x - (c.x - root.location.x), tgt.y - (c.y - root.location.y), y))
    else:   # eyes: camlar yüzün hemen önünde, göz hizasında
        ez = head.z + RULES.get('eyeline', {}).get(STAGE, 0.6) * (mx.z - head.z)
        me = [o for o in pet if o.type == 'MESH']
        ys = [(o.matrix_world @ v.co).y for o in me for v in o.data.vertices
              if abs((o.matrix_world @ v.co).z - ez) < 0.03 * h and abs((o.matrix_world @ v.co).x) < 0.12 * h]
        fy = min(ys) if ys else head.y
        root.location = V((head.x - (c.x - root.location.x), (fy + fwd * h) - (imn.y - root.location.y), ez - (c.z - root.location.z)))
    if tw.get('tilt'):
        root.rotation_euler.y += math.radians(tw['tilt'])
    bpy.context.view_layer.update()
    return objs


# ---------------------------------------------------------------- yüz yüzeyi ve kodla süsler

def surface(x, z, from_top=False, y=-0.05):
    """Okti'nin yüzeyinde (önden ya da yukarıdan ışın) nokta + normal."""
    dg = bpy.context.evaluated_depsgraph_get()
    if from_top:
        ok, loc, nor, *_ = bpy.context.scene.ray_cast(dg, V((x, y, 3.0)), V((0, 0, -1)))
    else:
        ok, loc, nor, *_ = bpy.context.scene.ray_cast(dg, V((x, -2.0, z)), V((0, 1, 0)))
    return (loc, nor) if ok else (None, None)


def blob(name, loc, scale, mat, rot=(0, 0, 0), seg=24, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc)
    o = bpy.context.active_object; o.name = name
    o.scale = scale; o.rotation_mode = 'XYZ'; o.rotation_euler = rot
    if smooth:
        bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def facing(nor, roll=0.0):
    """Nesnenin −Y ekseni (ön yüzü) yüzey normaline baksın."""
    q = V((0, -1, 0)).rotation_difference(nor.normalized())
    e = q.to_euler(); e.y += roll
    return e


def lashes(eye_pts, mat, n=3, length=0.034, up=0.016):
    """Kirpik: her gözün üst-dış kenarından yukarı ve dışa kıvrılan ince koniler."""
    length *= K; up *= K
    for e in eye_pts:
        side = 1 if e.x > 0 else -1
        for i in range(n):
            a = math.radians(70 - i * 24)               # dış kenara doğru yatıklaşır
            base = V((e.x + side * (0.006 + i * 0.006) * K, e.y - 0.004 * K, e.z + up - i * 0.003 * K))
            d = V((side * math.cos(a) * 0.55, -0.25, math.sin(a))).normalized()
            bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.0045 * K, radius2=0.0009 * K, depth=length,
                                            location=base + d * (length / 2))
            o = bpy.context.active_object
            o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = V((0, 0, 1)).rotation_difference(d)
            bpy.ops.object.shade_smooth(); o.data.materials.append(mat)


def brows(eye_pts, mat, lift=0.05, tilt=6):
    for e in eye_pts:
        side = 1 if e.x > 0 else -1
        loc, nor = surface(e.x + side * 0.004 * K, e.z + lift * K)
        if loc is None:
            continue
        rot = facing(nor); rot.y += math.radians(tilt * side)   # iç uç biraz yukarıda: sıcak, kızgın değil
        blob('brow', loc + nor * 0.005 * K, (0.034 * K, 0.011 * K, 0.012 * K), mat, rot)


def blush(eye_pts, mat):
    for e in eye_pts:
        side = 1 if e.x > 0 else -1
        loc, nor = surface(e.x + side * 0.05 * K, e.z - 0.055 * K)
        if loc is not None:
            blob('blush', loc + nor * 0.001 * K, (0.026 * K, 0.004 * K, 0.017 * K), mat, facing(nor))


def big_eyes(eye_pts, mat, shine, r=0.021):
    """Çocuk portresi: göz noktasının üstüne iri, parlak göz + beyaz ışıltı (iki nokta: büyük üst-dış, küçük alt-iç)."""
    r *= K
    for e in eye_pts:
        side = 1 if e.x > 0 else -1
        loc, nor = surface(e.x, e.z)
        if loc is None:
            continue
        nor = nor.normalized()
        blob('eye', loc + nor * r * 0.12, (r, r * 0.42, r * 1.12), mat, facing(nor), seg=32)
        q = V((0, -1, 0)).rotation_difference(nor)
        blob('shine', loc + nor * r * 0.42 + q @ V((-side * r * 0.36, 0, r * 0.42)), (r * 0.34, r * 0.12, r * 0.34), shine, facing(nor), seg=16)
        blob('shine2', loc + nor * r * 0.40 + q @ V((side * r * 0.30, 0, -r * 0.40)), (r * 0.15, r * 0.08, r * 0.15), shine, facing(nor), seg=12)


def freckles(eye_pts, mat):
    """Çil: iki yanakta üçer küçük nokta."""
    for e in eye_pts:
        side = 1 if e.x > 0 else -1
        for dx, dz in ((0.040, -0.050), (0.058, -0.044), (0.050, -0.064)):
            loc, nor = surface(e.x + side * dx * K, e.z + dz * K)
            if loc is not None:
                blob('freckle', loc + nor * 0.001 * K, (0.0055 * K, 0.002 * K, 0.0055 * K), mat, facing(nor), seg=12)


def snout_top(eye_y, eye_z, x=0.0):
    """Ağzın (kırmızı burun) üst kenarı: önden ışınla yüzeyin göz yüzeyinden 3 cm öne çıktığı en yüksek nokta."""
    z = eye_z
    while z > eye_z - 0.22 * K:
        loc, _ = surface(x, z)
        if loc is not None and loc.y < eye_y - 0.03 * K:
            return z, loc
        z -= 0.003 * K
    return None, None


def mustache(mat, eye_y, eye_z):
    z, loc = snout_top(eye_y, eye_z)
    if z is None:
        return
    for side in (-1, 1):
        l2, n2 = surface(side * 0.045, z + 0.004)
        if l2 is None:
            continue
        p = V((side * 0.045, min(l2.y, loc.y + 0.02) - 0.006, z + 0.006))
        rot = facing(V((side * 0.35, -1, 0.15))); rot.y += math.radians(18 * side)
        blob('mustache', p, (0.062, 0.021, 0.023), mat, rot)
        tip = V((side * 0.118, p.y + 0.014, z + 0.032))
        blob('mustache_tip', tip, (0.021, 0.014, 0.016), mat, rot)


def hibiscus(where, petal_mat, heart_mat, size=0.115, roll=0.4):
    loc, nor = where
    if loc is None:
        return
    nor = nor.normalized(); c = loc + nor * 0.01 * K
    q = V((0, -1, 0)).rotation_difference(nor)
    for i in range(5):
        a = roll + i * 2 * math.pi / 5
        off = q @ V((math.cos(a) * size * 0.55, 0, math.sin(a) * size * 0.55))
        o = blob('petal', c + off, (size * 0.46, size * 0.10, size * 0.36), petal_mat)
        o.rotation_mode = 'QUATERNION'   # yaprak düzlemde, uzun ekseni dışa; uçları hafif öne kıvrık (çanak)
        o.rotation_quaternion = q @ Quaternion((0, 1, 0), -a) @ Quaternion((0, 0, 1), -0.22)
    blob('heart', c - nor * 0.002 + q @ V((0, -size * 0.10, 0)), (size * 0.18, size * 0.16, size * 0.18), heart_mat)
    for i in range(3):   # dişi organ: küçük sarı tanecikler
        a = roll + 0.5 + i * 0.5
        blob('pollen', c + q @ V((math.cos(a) * size * 0.16, -size * 0.30, math.sin(a) * size * 0.16 + size * 0.08)),
             (size * 0.05,) * 3, heart_mat, seg=12)


def wing_mesh(name, side, L, R, mat):
    """Fiyonk kanadı: düğümde ince, dışa doğru genişleyen yassı yuvarlak üçgen (halkalar + uç kapak, yumuşatılmış)."""
    import bmesh
    bm = bmesh.new(); rings = []
    for t, r in ((0.06, 0.22), (0.35, 0.70), (0.72, 1.0), (0.95, 0.92)):
        ring = []
        for i in range(16):
            a = 2 * math.pi * i / 16
            ring.append(bm.verts.new((side * t * L, math.cos(a) * r * R * 0.38, math.sin(a) * r * R)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(16):
            bm.faces.new((r0[i], r0[(i + 1) % 16], r1[(i + 1) % 16], r1[i]))
    for ring, flip in ((rings[0], side > 0), (rings[-1], side < 0)):
        bm.faces.new(ring[::-1] if flip else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    sub = o.modifiers.new('s', 'SUBSURF'); sub.levels = sub.render_levels = 2
    for f in me.polygons:
        f.use_smooth = True
    me.materials.append(mat)
    return o


def bow(where, mat, knot_mat, size=0.20, roll=0.30):
    """Fiyonk: ortadaki düğümden iki yana açılan iki kanat + iki kısa kuyruk; ön yüzü kameraya bakar, başın yan-üstünde yatık."""
    loc, nor = where
    if loc is None:
        return
    c = loc + nor.normalized() * 0.035 * K + V((0, -0.015 * K, 0))
    tilt = Quaternion((0, 1, 0), roll) @ Quaternion((1, 0, 0), 0.25)
    for side in (-1, 1):
        w = wing_mesh('bow_wing', side, size * 0.62, size * 0.36, mat)
        w.location = c; w.rotation_mode = 'QUATERNION'; w.rotation_quaternion = tilt @ Quaternion((0, 1, 0), side * -0.18)
        t = blob('bow_tail', c + tilt @ V((side * size * 0.14, 0.004, -size * 0.34)), (size * 0.09, size * 0.04, size * 0.22), mat)
        t.rotation_mode = 'QUATERNION'; t.rotation_quaternion = tilt @ Quaternion((0, 1, 0), side * 0.40)
    blob('bow_knot', c + tilt @ V((0, -size * 0.03, 0)), (size * 0.15, size * 0.12, size * 0.16), knot_mat)


# ---------------------------------------------------------------- taslaklar
# body/top: (ton, doygunluk, parlaklık) Hue/Saturation; ton 0,5 = değişmez. bg: zemin (iç, dış)
LASH = '#22264A'
VARIANTS = {
    'okti_anne_1': dict(name='Çiçekli', body=(0.5, 1.0, 1.0), top=(0.41, 1.05, 0.98),
                        lashes=True, blush='#FF9FB4', flower=('#FF6F7D', '#FFD45A'), bg=('#FFF6EC', '#FFE3D3')),
    'okti_anne_2': dict(name='Hasır şapkalı', body=(0.47, 1.05, 1.02), top=(0.80, 0.85, 1.0),
                        lashes=True, blush='#FFA6BA', items=[('hat_straw', 'head', {'up': 0.085})], bg=('#F4FBF4', '#DDF2E4'), aim=1.46),
    'okti_anne_3': dict(name='Fiyonklu gözlüklü', body=(0.56, 0.95, 1.04), top=(0.5, 1.0, 1.0),
                        lashes=True, blush='#FF9FB4', bow=('#FF7FA8', '#FF5C8E'),
                        items=[('glasses_round', 'eyes', {'tone': (0.42, 1.0, 1.0)})], bg=('#FBF3FF', '#EBDDFB')),
    'okti_baba_1': dict(name='Bıyıklı gözlüklü', body=(0.53, 1.1, 0.88), top=(0.98, 0.75, 0.62),
                        mustache='#3A2A22', items=[('glasses_round', 'eyes', {'tone': (0.5, 0.6, 0.35)})],
                        bg=('#F1F7FF', '#D9E8FA')),
    'okti_baba_2': dict(name='Kaptan', body=(0.45, 1.05, 0.95), top=(0.95, 0.15, 1.15),
                        brows=True, items=[('set_captain_hat', 'head', {'up': 0.075})], bg=('#F2FAFB', '#D7EEF2'), aim=1.47),
    # varsayılan yüz (oyun: avatar seçilmemiş, eski/tanınmayan değer ya da photo:); süssüz yetişkin Okti, taslak sayfasında yok
    'okti': dict(name='Okti', body=(0.5, 1.0, 1.0), top=(0.5, 1.0, 1.0), bg=('#F3F8FF', '#DCEBFB'), sheet=False),
    'okti_baba_3': dict(name='Kasketli', body=(0.52, 1.08, 0.9), top=(0.47, 1.1, 1.0),
                        brows=True, items=[('hat_cap', 'head', {'up': 0.035})], bg=('#FFF8EE', '#F6E6CF'), aim=1.45),
}

# Çocuk profilleri (ParentApp çocuk avatarı; kullanıcı 28 Ekim 2026: "6 kız 6 erkek, çocuk gibi"): çocuk evresi Okti (yavru),
# iri parlak göz; kızlarda kirpik + yanak pembesi, erkeklerde bazen çil. Tişört tonu (ton kayması; sarı tişört 0,5).
KID = dict(stage='yavru', group='cocuk', eyes=True, zoom=1.14)
KIDS = {
    'okti_kiz_1': dict(name='Kurdeleli', top=(0.29, 0.9, 1.05), lashes=True, blush='#FF9FB4',
                       bow=('#FF7FA8', '#FF5C8E'), bg=('#FFF3F6', '#FFDDE7')),
    'okti_kiz_2': dict(name='Çiçek tokalı', body=(0.53, 1.0, 1.02), top=(0.12, 0.7, 1.08), lashes=True, blush='#FFA6BA',
                       flowers=('#FFB13B', '#FFF0A8'), bg=('#FFF9EC', '#FCEBC9')),
    'okti_kiz_3': dict(name='Taçlı', top=(0.80, 0.85, 1.0), lashes=True, blush='#FF9FB4',
                       items=[('hat_crown_tilt', 'head', {'up': 0.045, 'size': 0.82})], bg=('#FBF4FF', '#ECDDFB')),
    'okti_kiz_4': dict(name='Kalp gözlüklü', body=(0.47, 1.05, 1.02), top=(0.41, 1.05, 0.98), lashes=True, blush='#FF9FB4',
                       items=[('glasses_heart', 'eyes', {})], bg=('#FFF5EE', '#FFE0D2')),
    'okti_kiz_5': dict(name='Bereli', top=(0.85, 0.9, 1.05), lashes=True, blush='#FFA6BA',
                       items=[('hat_beanie', 'head', {'up': 0.055, 'tone': (0.04, 0.7, 1.35)})], bg=('#F1FBFA', '#D8F1EE')),
    'okti_kiz_6': dict(name='Kulaklıklı', body=(0.55, 0.95, 1.04), top=(0.5, 1.0, 1.0), lashes=True, blush='#FF9FB4',
                       items=[('headphones', 'head', {})], bg=('#FFFBEA', '#FBF0C4')),
    'okti_erkek_1': dict(name='Kasketli', top=(0.45, 1.05, 1.0), freckles=True,
                         items=[('hat_cap', 'head', {'tone': (0.10, 1.0, 0.95)})], bg=('#F0F7FF', '#D6E7FB')),
    'okti_erkek_2': dict(name='Pervaneli', body=(0.48, 1.05, 1.0), top=(0.75, 0.9, 1.0),
                         items=[('hat_propeller', 'head', {})], bg=('#F3FBEF', '#DCF1D3')),
    'okti_erkek_3': dict(name='Pilot', top=(0.5, 1.0, 1.0), freckles=True,
                         items=[('hat_pilot_goggles', 'head', {})], bg=('#FBF8EE', '#EFE7CF')),
    'okti_erkek_4': dict(name='Güneş gözlüklü', body=(0.52, 1.05, 0.98), top=(0.37, 1.1, 1.0),
                         items=[('glasses_sun', 'eyes', {})], bg=('#FFF6EE', '#FCE2CF')),
    'okti_erkek_5': dict(name='Antenli', body=(0.53, 1.08, 0.94), top=(0.99, 0.75, 0.62), freckles=True,
                         items=[('hat_star_antenna', 'head', {'up': -0.07, 'size': 0.9})], bg=('#F3F3FF', '#DEDDF8'),
                         aim=1.49, zoom=1.2),
    'okti_erkek_6': dict(name='Köpek balığı şapkalı', body=(0.47, 1.0, 1.0), top=(0.95, 0.15, 1.15),
                         items=[('hat_shark', 'head', {'up': 0.03})], bg=('#EEF9FC', '#D3EDF4')),
}
for _k, _v in KIDS.items():
    VARIANTS[_k] = dict(KID, **_v)


def light(name, loc, energy, color, size, target):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = srgb(color)[:3]; ld.size = size
    o = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (V(target) - V(loc)).to_track_quat('-Z', 'Y').to_euler()


def studio(t):
    light('key', (t.x - 1.5, t.y - 2.2, t.z + 1.6), 230, '#FFF1DC', 2.2, t)
    light('fill', (t.x + 2.0, t.y - 1.6, t.z + 0.3), 80, '#FFE1EC', 2.4, t)
    light('rim', (t.x + 1.4, t.y + 2.0, t.z + 1.0), 160, '#A8F0FF', 1.2, t)
    light('rim2', (t.x - 1.6, t.y + 1.6, t.z + 0.6), 70, '#FFC98F', 1.2, t)


def camera(target, yaw=-14.0, dist=2.45, lens=95):
    cd = bpy.data.cameras.new('cam'); cd.lens = lens
    o = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(o)
    a = math.radians(yaw)
    o.location = V((math.sin(a) * dist, -math.cos(a) * dist, target.z + 0.06 * K))
    o.rotation_euler = (target - o.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o


def build(key, cfg):
    global K
    pet, arm, wear = load_okti(cfg)
    eye_pts, H = eyes(pet)
    mn, mx = bounds(pet)
    ez = sum(p.z for p in eye_pts) / len(eye_pts)
    K = (mx.z - ez) / 0.181
    dark = flat_material('dark', LASH, rough=0.35)
    if cfg.get('eyes'):
        big_eyes(eye_pts, flat_material('eye', '#151832', rough=0.12), flat_material('shine', '#FFFFFF', rough=0.3, emit=2.0))
    if cfg.get('freckles'):
        freckles(eye_pts, flat_material('freckle', '#E58A5C', rough=0.6))
    if cfg.get('lashes'):
        lashes(eye_pts, dark)
    if cfg.get('brows'):
        brows(eye_pts, flat_material('brow', '#2A2C52', rough=0.5))
    if cfg.get('blush'):
        blush(eye_pts, flat_material('blush', cfg['blush'], rough=0.6))
    if cfg.get('mustache'):
        mustache(flat_material('stache', cfg['mustache'], rough=0.65), sum(p.y for p in eye_pts) / len(eye_pts), ez)
    if cfg.get('flower'):
        hibiscus(surface(-0.17 * K, ez + 0.11 * K), flat_material('petal', cfg['flower'][0], rough=0.45, sss=0.2),
                 flat_material('heart', cfg['flower'][1], rough=0.4), size=0.115 * K)
    if cfg.get('flowers'):   # iki yanda küçük çiçek toka
        pm = flat_material('petal', cfg['flowers'][0], rough=0.45, sss=0.2); hm = flat_material('heart', cfg['flowers'][1], rough=0.4)
        for side in (-1, 1):
            hibiscus(surface(side * 0.16 * K, ez + 0.095 * K), pm, hm, size=0.085 * K, roll=0.4 + side * 0.3)
    if cfg.get('bow'):
        bow(surface(-0.15 * K, ez + 0.13 * K), flat_material('bow', cfg['bow'][0], rough=0.4),
            flat_material('knot', cfg['bow'][1], rough=0.4), size=0.20 * K)
    for item_id, slot, tw in cfg.get('items', []):
        place_item(pet, arm, item_id, slot, tw)
    return pet, eye_pts, ez


def composite(raw, out, bg, size):
    from PIL import Image, ImageDraw, ImageFilter
    fg = Image.open(raw).convert('RGBA').resize((size, size), Image.LANCZOS)
    inner, outer = (tuple(int(c.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) for c in bg)
    base = Image.new('RGB', (size, size), outer)
    glow = Image.new('L', (size, size), 0)
    ImageDraw.Draw(glow).ellipse((size * 0.12, size * 0.06, size * 0.88, size * 0.82), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.12))
    base = Image.composite(Image.new('RGB', (size, size), inner), base, glow)
    # yumuşak yer gölgesi (omuzların altı kadrajdan çıkar; yalnız arkada hafif hale)
    sh = fg.split()[3].filter(ImageFilter.GaussianBlur(size * 0.02)).point(lambda a: int(a * 0.10))
    base.paste(Image.new('RGB', (size, size), (40, 60, 90)), (int(size * 0.012), int(size * 0.02)), sh)
    base.paste(fg, (0, 0), fg)
    base.save(out)


def sheet(paths, out, cell=360):
    from PIL import Image, ImageDraw
    cols = 3; rows = (len(paths) + cols - 1) // cols
    im = Image.new('RGB', (cols * cell * 2 + 40, rows * cell + 20), (248, 248, 250))
    for i, p in enumerate(paths):
        a = Image.open(p).resize((cell, cell), Image.LANCZOS)
        x = 10 + (i % cols) * (cell * 2 + 10); y = 10 + (i // cols) * cell
        im.paste(a, (x, y))
        m = Image.new('L', (cell, cell), 0); ImageDraw.Draw(m).ellipse((0, 0, cell - 1, cell - 1), fill=255)
        im.paste(a.resize((cell - 40, cell - 40)), (x + cell + 20, y + 20), m.resize((cell - 40, cell - 40)))
    im.save(out)


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    opt = {argv[i][2:]: argv[i + 1] for i in range(len(argv) - 1) if argv[i].startswith('--')}
    args = [a for a in args if a not in opt.values()]
    group = opt.get('group', 'ebeveyn')   # ebeveyn | cocuk
    out = opt.get('out', os.path.join(ROOT, 'art', 'parent_avatars' if group == 'ebeveyn' else 'child_avatars', 'drafts'))
    samples = int(opt.get('samples', 96)); size = int(opt.get('size', 1024))
    os.makedirs(out, exist_ok=True); raw_dir = os.path.join(out, 'seffaf'); os.makedirs(raw_dir, exist_ok=True)
    keys = args or [k for k, v in VARIANTS.items() if v.get('group', 'ebeveyn') == group]
    done = []
    global STAGE
    for k in keys:
        cfg = VARIANTS[k]
        STAGE = cfg.get('stage', 'yetiskin')
        reset(samples, int(size * 1.0))
        _, _, ez = build(k, cfg)
        # kadraj göze göre (yetişkinde göz 1,47 m); çocuk Okti'nin başı büyük → K ile uzaklaşır
        t = V((0.0, 0.0, ez + (cfg.get('aim', 1.43) - 1.47) * K))
        studio(t); camera(t, yaw=cfg.get('yaw', -14.0), dist=2.45 * K * cfg.get('zoom', 1.0))
        raw = os.path.join(raw_dir, k + '.png')
        bpy.context.scene.render.filepath = raw
        bpy.ops.render.render(write_still=True)
        composite(raw, os.path.join(out, k + '.png'), cfg['bg'], size)
        done.append(os.path.join(out, k + '.png'))
        print('TASLAK', k, cfg['name'])
    allp = [os.path.join(out, k + '.png') for k, v in VARIANTS.items()
            if v.get('sheet', True) and v.get('group', 'ebeveyn') == group and os.path.exists(os.path.join(out, k + '.png'))]
    sheet(allp, os.path.join(out, 'sheet.png'))


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
