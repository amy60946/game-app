"""Adalı portreleri (konuşma balonu köşesi): oyundaki 3B modelden (Resources/Env/res_*) Cycles ile çizilir.

Kullanım (bpy 4.2 + Pillow kurulu Python, ör. /tmp/claude-0/bpyenv/bin/python):
  nice -n 10 <python> -I art/scripts/resident_portraits.py [ad ...] [--out KLASÖR] [--samples N] [--glb ad=YOL]
    ad: kiskac, mavi, pus (boşsa hepsi)
    --out: varsayılan Assets/_Pofi/Resources/Portraits (res_<ad>.png, 512 x 512, şeffaf)
    --glb kiskac=/yol/res3d_kiskac_a.glb: oyundaki FBX yerine Meshy kaynağını kullan (isteğe bağlı)

Görünüm (24 Ekim 2026): yumuşak stüdyo ışığı (sıcak ana + pembe dolgu + camgöbeği kenar; render.py ile aynı aile),
3/4 açı, baş + gövde üstü; alt kenar gövdeyi keser (Okti portresiyle aynı çerçeve: Portraits/pet_13.png).
Oyun kodu: UI/StoryPlayer ve MapScreen istek kartı Ui.Portrait("res_" + kim) okur; yoksa eski simgeye döner.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')

# ad → model klasörü, dönüş (derece), kamera yüksekliği ve bakış hizası (boyun oranı), kesim: görüntüde kalan üst kısım
#        (boyun oranı; alt kenar gövdeyi keser), yatay odak kayması (genişlik oranı); fit='whole': bütün model (Pus: bulut)
LOOK = {
    'kiskac': dict(model='res_kiskac', yaw=-26, cam_h=0.62, aim_h=0.55, keep=0.88, shift=-0.02),
    'mavi': dict(model='res_mavi', yaw=-24, cam_h=0.80, aim_h=0.70, keep=0.66, shift=0.0),
    'pus': dict(model='res_pus', yaw=-20, cam_h=0.60, aim_h=0.50, fit='whole'),
}

SIZE = 512


def hex_rgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def reset(samples, res):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 3   # paylaşılan bilgisayar: bir çekirdek boş kalsın
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = -0.55
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('w')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (*hex_rgb('#DCEEFF'), 1)
    bg.inputs['Strength'].default_value = 0.75
    return sc


def light(name, loc, energy, color, size, target):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.color = hex_rgb(color)
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(ob)


def studio(target):
    """Yumuşak stüdyo: büyük sıcak ana ışık (sol önden), pembe dolgu (sağ), camgöbeği + turuncu kenar (arkadan)."""
    tx, ty, tz = target
    light('key', (tx - 1.5, ty - 2.2, tz + 1.6), 230, '#FFF1DC', 2.2, target)
    light('fill', (tx + 2.0, ty - 1.6, tz + 0.3), 75, '#FFD6E8', 2.4, target)
    light('rim', (tx + 1.4, ty + 2.0, tz + 1.0), 170, '#9FEFFF', 1.2, target)
    light('rim2', (tx - 1.6, ty + 1.6, tz + 0.6), 80, '#FFC27F', 1.2, target)


def load_model(name, glb=None):
    if glb:
        bpy.ops.import_scene.gltf(filepath=glb)
    else:
        bpy.ops.import_scene.fbx(filepath=os.path.join(ENV, name, name + '.fbx'))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    # boş kök / iskelet varsa dönüşümü meshe aktarılır, sonra silinir
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    for o in list(bpy.context.scene.objects):
        if o != ob and o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    if not glb:
        ob.data.materials.clear()
        ob.data.materials.append(game_material(name))
    else:
        for m in ob.data.materials:   # Meshy PBR: biraz daha yumuşak parlama (vinyl)
            p = m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
            if p is not None and not p.inputs['Roughness'].is_linked:
                p.inputs['Roughness'].default_value = 0.5
    bpy.ops.object.shade_smooth()
    # boyu 1 m, tabanı z = 0, yatayda ortada
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    s = 1.0 / max(1e-6, hi.z - lo.z)
    ob.scale = (s, s, s)
    ob.location = (-(lo.x + hi.x) / 2 * s, -(lo.y + hi.y) / 2 * s, -lo.z * s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


def game_material(name):
    """Oyundaki dokular (taban renk + normal): Unity'deki Pofi/Toon ile aynı kaynak."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value = 0.48
    p.inputs['Coat Weight'].default_value = 0.15
    p.inputs['Coat Roughness'].default_value = 0.3
    base = os.path.join(ENV, name, name + '_basecolor.jpg')
    if not os.path.exists(base):
        base = os.path.join(ENV, name, name + '_basecolor.png')
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(base)
    nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    nrm = os.path.join(ENV, name, name + '_normal.jpg')
    if os.path.exists(nrm):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(nrm)
        n.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = 0.8
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    return m


def camera(loc, target, lens=70):
    cd = bpy.data.cameras.new('cam')
    cd.lens = lens
    cd.clip_start = 0.05
    ob = bpy.data.objects.new('cam', cd)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def frame_box(cfg, bb):
    """Önizleme alfa sınırından (0..1, üst-sol köken) kare kesim kutusu: 'bust' üstten hizalı, alt kenar gövdeyi keser;
    'whole' bütün model ortada (Pus: bulut)."""
    x0, y0, x1, y1 = bb
    w, h = x1 - x0, y1 - y0
    if cfg.get('fit') == 'whole':
        side = max(w, h) * 1.08
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return cx - side / 2, cy - side / 2, side
    side = h * cfg['keep'] * 1.04
    cx = (x0 + x1) / 2 + cfg['shift'] * w
    return cx - side / 2, y0 - 0.04 * h, side


def render_one(who, out_dir, samples, glb=None, raw_dir=None):
    from PIL import Image
    cfg = LOOK[who]
    sc = reset(samples, 256)
    ob = load_model(cfg['model'], glb)
    ob.rotation_euler = (0, 0, math.radians(cfg['yaw']))
    bpy.ops.object.transform_apply(rotation=True)
    aim = (0.0, 0.0, cfg['aim_h'])
    studio(aim)
    camera((0.0, -3.2, cfg['cam_h']), aim, lens=58)   # tüm model çerçevede, kenarda boşluk
    tmp = os.path.join(raw_dir or out_dir, f'_raw_{who}.png')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    # 1) kaba geçiş (256 px, 1 örnek): yalnız alfa sınırı
    sc.cycles.samples, sc.cycles.use_denoising = 1, False
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    a = Image.open(tmp).getchannel('A')
    px = a.point(lambda v: 255 if v > 8 else 0).getbbox()
    bb = tuple(v / 256.0 for v in px)
    left, top, side = frame_box(cfg, bb)
    # 2) yalnız kesim bölgesi, kesim 2×SIZE piksel olacak çözünürlükte (sonra küçültülür: yumuşak kenar)
    full = int(round(2 * SIZE / side))
    sc.render.resolution_x = sc.render.resolution_y = full
    sc.cycles.samples, sc.cycles.use_denoising = samples, True
    l, r = max(0.0, left), min(1.0, left + side)
    t, b = max(0.0, top), min(1.0, top + side)
    sc.render.use_border, sc.render.use_crop_to_border = True, True
    sc.render.border_min_x, sc.render.border_max_x = l, r
    sc.render.border_min_y, sc.render.border_max_y = 1.0 - b, 1.0 - t
    bpy.ops.render.render(write_still=True)
    im = Image.open(tmp).convert('RGBA')
    sq = int(round(side * full))
    canvas = Image.new('RGBA', (sq, sq), (0, 0, 0, 0))
    canvas.alpha_composite(im, (int(round((l - left) * full)), int(round((t - top) * full))))
    out = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f'res_{who}.png')
    out.save(path, optimize=True)
    print('yazıldı', path, out.size, 'kesim', round(side, 3), 'çözünürlük', full)
    if raw_dir is None:
        os.remove(tmp)
    return path


def main(argv):
    names, out, samples, glbs, raw_dir = [], os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Portraits'), 96, {}, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--out':
            out = argv[i + 1]; i += 2; continue
        if a == '--samples':
            samples = int(argv[i + 1]); i += 2; continue
        if a == '--glb':
            k, v = argv[i + 1].split('=', 1); glbs[k] = v; i += 2; continue
        if a == '--raw':
            raw_dir = argv[i + 1]; i += 2; continue
        names.append(a); i += 1
    for who in names or list(LOOK):
        render_one(who, out, samples, glbs.get(who), raw_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
