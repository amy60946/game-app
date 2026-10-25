# Uzay kıyafetleri — onay görselleri ve simgeler (Cycles; yumuşak anahtar + dolgu ışığı, açık lavanta zemin).
#   python -I space_preview.py -- <çıktı> <önizleme_klasörü>            yetişkin: her kıyafet ön/arka/koşu/zıplama/çömelme + çocuk/genç paftası
#   python -I space_preview.py -- <çıktı> <önizleme_klasörü> check      tüm evrelerde dinlenme (yerleşim denetimi)
#   python -I space_preview.py -- <çıktı> <simge_klasörü> icons         256² şeffaf simgeler (wear_icon.py havası)
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import bpy
import numpy as np
from mathutils import Vector as V
import space_kit as K
import space_fit as F

OUTFITS = {'outfit_astro': ('hat_astro_helmet', 'back_astro_pack'), 'outfit_pilot': ('hat_pilot_goggles', 'back_pilot_jetpack'),
           'outfit_star': ('hat_star_antenna', 'back_star_cape')}
BG = (236, 232, 248)
SAMPLES = int(os.environ.get('SAMPLES', '28'))


def tex_mat(name, img):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img)
    b = m.node_tree.nodes['Principled BSDF']; m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.45; b.inputs['Coat Weight'].default_value = 0.2
    return m


def lights(sc, c, r):
    for o in [o for o in sc.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
    def area(name, energy, size, loc, col):
        l = bpy.data.lights.new(name, 'AREA'); l.energy = energy * r * r; l.size = size * r; l.color = col
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = c + V(loc) * r * 3
        o.rotation_euler = (c - o.location).to_track_quat('-Z', 'Y').to_euler()
    area('key', 210, 2.2, (-0.9, -1.0, 1.0), (1.0, 0.97, 0.93))
    area('fill', 80, 3.5, (1.1, -0.8, 0.25), (0.88, 0.92, 1.0))
    area('rim', 120, 2.0, (0.4, 1.3, 0.8), (1.0, 1.0, 1.0))
    w = bpy.data.worlds.get('w') or bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.86, 0.84, 0.95, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55


def setup(sc, res):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4; sc.cycles.transparent_max_bounces = 8
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.1
    sc.render.film_transparent = True; sc.render.resolution_x, sc.render.resolution_y = res
    if sc.camera is None:
        cd = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co


def shoot(sc, path, c, h, yaw, pitch=6, lens=70, fill=1.18):
    cam = sc.camera; cam.data.lens = lens; cam.data.type = 'PERSP'
    aspect = sc.render.resolution_y / sc.render.resolution_x
    vfov = 2 * math.atan(18.0 / lens * (1.0 if aspect >= 1 else aspect))      # sensör uzun kenara oturur (AUTO)
    dist = (h * fill / 2) / math.tan(vfov / 2)
    y = math.radians(yaw); p = math.radians(pitch)
    cam.location = c + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    flatten(path)


def flatten(path):
    from PIL import Image
    im = Image.open(path).convert('RGBA'); bg = Image.new('RGBA', im.size, BG + (255,))
    # yumuşak zemin gölgesi yerine hafif alt degrade
    bg.alpha_composite(im); bg.convert('RGB').save(path)


def dress(B, out, oid, rules, glass=True, suit=True):
    hat, back = OUTFITS[oid]
    objs = []
    if suit: objs += F.load_suit(B, os.path.join(out, 'suits'), oid)
    for iid in (hat, back):
        it = F.load_item(os.path.join(out, 'items'), iid, glass=glass)
        F.place(B, iid, it, rules[B.stage][iid]); objs += it
    return objs


def pose(B, clip, frame):
    if clip is None:
        if B.arm.animation_data: B.arm.animation_data.action = None
        for pb in B.arm.pose.bones: pb.matrix_basis.identity()
        bpy.context.scene.frame_set(1)
    else:
        F.set_clip(B, clip); bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def stage_scene(st):
    K.reset_scene(); B = K.Body(st)
    B.body.data.materials.clear(); B.body.data.materials.append(tex_mat('pet', os.path.join(B.dir, B.name + '_basecolor.jpg')))
    for p in B.body.data.polygons: p.use_smooth = True
    return B


def compose(paths, out, cols, cell, labels=None):
    from PIL import Image, ImageDraw
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new('RGB', (cell[0] * cols, cell[1] * rows), BG)
    for i, p in enumerate(paths):
        im = Image.open(p).resize(cell, Image.LANCZOS); sheet.paste(im, ((i % cols) * cell[0], (i // cols) * cell[1]))
    sheet.save(out, quality=92)


def previews(out, pdir):
    os.makedirs(pdir, exist_ok=True)
    rules = json.load(open(os.path.join(out, 'rules.json')))
    sheets = []
    only = [x for x in os.environ.get('ONLY', '').split(',') if x]
    for oid in OUTFITS:
        if only and oid not in only: continue
        B = stage_scene('yetiskin'); sc = bpy.context.scene; setup(sc, (720, 900))
        dress(B, out, oid, rules)
        H = B.H; c = V((0, 0, H * (0.56 if oid == 'outfit_star' else 0.52))); lights(sc, c, H)      # antenli taçta yıldız kadraja girsin
        extra = 1.12 if oid == 'outfit_star' else 1.0
        shots = [('on', None, 1, 0), ('arka', None, 1, 180), ('kosu', 'run', 5, 28), ('ziplama', 'jump', 19, 28), ('comelme', 'squat', 21, 28)]
        paths = []
        for tag, clip, fr, yaw in shots:
            pose(B, clip, fr)
            p = os.path.join(pdir, '%s_yetiskin_%s.png' % (oid, tag))
            cz = c.copy()
            if clip == 'jump': cz.z += 0.25 * H
            if clip == 'squat': cz.z -= 0.08 * H
            shoot(sc, p, cz, H, yaw, pitch=8 if clip else 5, fill=(1.2 if clip != 'jump' else 1.35) * extra)
            paths.append(p)
        compose(paths, os.path.join(pdir, '%s_yetiskin.jpg' % oid), 5, (432, 540)); sheets.append(os.path.join(pdir, '%s_yetiskin.jpg' % oid))
    if only: return
    # çocuk + genç paftası: her kıyafet iki evrede ön (3/4) ve arka (3/4)
    paths = []
    for oid in OUTFITS:
        for st in ('yavru', 'genc'):
            B = stage_scene(st); sc = bpy.context.scene; setup(sc, (600, 760))
            dress(B, out, oid, rules); H = B.H; c = V((0, 0, H * 0.52)); lights(sc, c, H)
            for tag, yaw in (('on', 25), ('arka', 155)):
                p = os.path.join(pdir, '%s_%s_%s.png' % (oid, st, tag)); shoot(sc, p, c, H, yaw, pitch=6); paths.append(p)
    compose(paths, os.path.join(pdir, 'cocuk_genc.jpg'), 4, (400, 506))
    print('ONIZLEME', pdir, flush=True)


def check(out, pdir):
    os.makedirs(pdir, exist_ok=True)
    rules = json.load(open(os.path.join(out, 'rules.json')))
    global SAMPLES
    SAMPLES = 10
    paths = []
    for st in K.STAGES:
        for oid in OUTFITS:
            B = stage_scene(st); sc = bpy.context.scene; setup(sc, (360, 440))
            dress(B, out, oid, rules); H = B.H; c = V((0, 0, H * 0.52)); lights(sc, c, H)
            for tag, yaw in (('on', 0), ('yan', 90), ('arka', 180)):
                p = os.path.join(pdir, 'chk_%s_%s_%s.png' % (st, oid, tag)); shoot(sc, p, c, H, yaw, pitch=4); paths.append(p)
    compose(paths, os.path.join(pdir, 'check.jpg'), 9, (240, 293))


def icons(out, idir):
    """Simgeler: wear_icon.py ile aynı hava (parlak vinyl, 3/4 açı, kareyi dolduran çerçeve, 512 → 256 şeffaf)."""
    from PIL import Image
    os.makedirs(idir, exist_ok=True)
    jobs = [(iid, False) for hat, back in OUTFITS.values() for iid in (hat, back)] + [(oid, True) for oid in OUTFITS]
    for iid, suit in jobs:
        K.reset_scene(); sc = bpy.context.scene
        if suit:
            objs = [o for o in K.import_fbx(os.path.join(out, 'suits', iid + '.fbx')) if o.type == 'MESH']
            m = tex_mat(iid, os.path.join(out, 'suits', '%s_yetiskin_basecolor.png' % iid))
            for o in objs: o.data.materials.clear(); o.data.materials.append(m)
            yaw, pitch = 22, 8
        else:
            objs = F.load_item(os.path.join(out, 'items'), iid, glass=True); yaw, pitch = 28, 14
            if iid.startswith('back'): yaw = 205
        bpy.context.view_layer.update()
        pts = np.array([tuple(o.matrix_world @ v.co) for o in objs for v in o.data.vertices])
        mn, mx = pts.min(0), pts.max(0); c = V(((mn + mx) / 2).tolist()); r = float(np.linalg.norm(mx - mn) / 2)
        sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.3
        sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = 512
        lights(sc, c, r)
        cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
        y = math.radians(yaw); p = math.radians(pitch)
        co.location = c + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * r * 6
        co.rotation_euler = (c - co.location).to_track_quat('-Z', 'Y').to_euler(); bpy.context.view_layer.update()
        inv = co.matrix_world.inverted(); cp = np.array([tuple(inv @ V(q)) for q in pts])
        cd.ortho_scale = max(np.ptp(cp[:, 0]), np.ptp(cp[:, 1])) / 0.92
        co.location += co.matrix_world.to_3x3() @ V(((cp[:, 0].max() + cp[:, 0].min()) / 2, (cp[:, 1].max() + cp[:, 1].min()) / 2, 0))
        big = os.path.join(idir, iid + '.big.png'); sc.render.filepath = big; bpy.ops.render.render(write_still=True)
        Image.open(big).resize((256, 256), Image.LANCZOS).save(os.path.join(idir, iid + '.png')); os.remove(big)
        print('SIMGE', iid, flush=True)


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:]
    out, d = a[0], a[1]
    mode = a[2] if len(a) > 2 else 'previews'
    if mode == 'icons': icons(out, d)
    elif mode == 'check': check(out, d)
    else: previews(out, d)
