"""Pofi Adası — konsept render'ları (Aşama 0A/0B).

Kullanım (bpy kurulu Python ile):
  python art/scripts/render.py turnaround pet_01 [--clay]   → art/out/turnaround/pet_01.png
  python art/scripts/render.py all                           → tüm 0B çıktıları
Çıktılar art/out/ altına yazılır; seçilenler docs/art/ altına kopyalanır.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import pets  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'art', 'out')


def reset(samples=48, res=(640, 640), transparent=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pets._mats.clear()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = -0.9
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    world = bpy.data.worlds.new('w')
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = pets.hex_rgba('#E3F4FF')
    bg.inputs['Strength'].default_value = 0.8
    return sc


def light(name, kind, loc, energy, color='#FFFFFF', size=1.0, target=(0, 0, 0.35)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = pets.hex_rgba(color)[:3]
    if kind == 'AREA':
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(ob)
    return ob


def studio(rim=True):
    """Güçlü sıcak ana ışık + renkli (camgöbeği) kenar ışığı + pembe dolgu: referanstaki "parlak oyuncak" havası."""
    light('key', 'AREA', (-1.6, -2.2, 2.2), 260, '#FFF1DC', size=1.6)
    light('fill', 'AREA', (2.0, -1.6, 0.9), 70, '#FFD6E8', size=2.0)
    if rim:
        light('rim', 'AREA', (1.4, 2.0, 1.6), 220, '#7FE8FF', size=1.0)
        light('rim2', 'AREA', (-1.6, 1.6, 1.2), 120, '#FFC27F', size=1.0)


def ground(color='#FFE2B8', size=20):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    g = bpy.context.active_object
    g.data.materials.append(pets.vinyl('ground', color, rough=0.7, coat=0.0, sss=0.0))
    return g


def camera(loc, target, ortho=None, lens=70):
    cd = bpy.data.cameras.new('cam')
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    ob = bpy.data.objects.new('cam', cd)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('yazıldı', path)


# ------------------------------------------------------------------ çıktılar

def turnaround(pet_id, clay=False, stage='genc'):
    """Ön / yan / arka (ortografik). Işık kameraya göre sabit; pet döndürülür."""
    from PIL import Image
    tiles = []
    for view, yaw in (('on', 0), ('yan', 90), ('arka', 180)):
        reset(samples=40, res=(560, 640))
        studio()
        ground('#F4F1EC' if clay else '#FFE2B8')
        b = pets.build(pet_id, stage, clay=clay)
        b.root.rotation_euler = (0, 0, math.radians(yaw))
        camera((0, -6, 1.3), (0, 0, 0.45), ortho=1.25)
        p = os.path.join(OUT, 'tmp', f'{pet_id}_{view}.png')
        render(p)
        tiles.append(Image.open(p).convert('RGBA'))
    w, h = tiles[0].size
    sheet = Image.new('RGBA', (w * 3, h), (255, 255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.alpha_composite(t, (i * w, 0))
    out = os.path.join(OUT, 'turnaround' + ('_clay' if clay else ''), f'{pet_id}.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.convert('RGB').save(out)
    print('yazıldı', out)


def hero(pet_id, size=512, stage='genc', name=None):
    """Seçim kartı portresi denemesi: şeffaf arka plan, 3/4 açı."""
    reset(samples=64, res=(size, size), transparent=True)
    studio()
    b = pets.build(pet_id, stage)
    b.root.rotation_euler = (0, 0, math.radians(-28))
    camera((0, -2.9, 0.75), (0, 0, 0.47), lens=85)
    render(os.path.join(OUT, name or 'portrait', f'{pet_id}.png'))


def lineup():
    """12 pet iki sıra (renk ve silüet ayrışmasını tek bakışta görmek için). Arka sıra basamak üstünde."""
    sc = reset(samples=64, res=(1920, 1080))
    sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = pets.hex_rgba('#FFE7C4')
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    light('key', 'AREA', (-3.0, -4.5, 5.0), 900, '#FFF1DC', size=4.0, target=(0, 0.6, 0.4))
    light('rim', 'AREA', (3.5, 4.5, 3.0), 700, '#7FE8FF', size=3.0, target=(0, 0.6, 0.4))
    light('rim2', 'AREA', (-3.5, 4.0, 2.5), 400, '#FFC27F', size=3.0, target=(0, 0.6, 0.4))
    # sonsuz fon (yere kıvrılan arka plan)
    import bmesh
    cyc_mat = pets.vinyl('cyc', '#FFD9A8', rough=0.9, coat=0.0, sss=0.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=4, depth=30, location=(0, 2.0, 4.0),
                                        rotation=(0, math.radians(90), 0))
    cyc = bpy.context.active_object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new(); bm.from_mesh(cyc.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < 1.99 or v.co.z > 4.0], context='VERTS')
    bm.to_mesh(cyc.data); bm.free()
    cyc.data.materials.append(cyc_mat)
    for p in cyc.data.polygons:
        p.use_smooth = True
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 2.0 - 15, 0))
    bpy.context.active_object.data.materials.append(cyc_mat)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.05, 0.12))
    step = bpy.context.active_object
    step.scale = (4.4, 0.7, 0.24)
    step.data.materials.append(pets.vinyl('step', '#FFC98A', rough=0.6, coat=0.1, sss=0.0))
    bv = step.modifiers.new('bevel', 'BEVEL'); bv.width = 0.06; bv.segments = 4
    for i, pid in enumerate(pets.PETS):
        row, col = divmod(i, 6)
        b = pets.build(pid)
        b.root.location = ((col - 2.5) * 0.66, row * 1.05, 0.24 if row else 0)
        b.root.rotation_euler = (0, 0, math.radians(-12))
    camera((0, -6.2, 1.55), (0, 0.5, 0.55), lens=42)
    render(os.path.join(OUT, 'lineup.png'))


def silhouettes():
    """Her pet'in 3/4 açıdan siyah silüeti (alfa kanalından)."""
    from PIL import Image, ImageDraw, ImageFont
    tiles = []
    for pid in pets.PETS:
        reset(samples=8, res=(360, 420), transparent=True)
        b = pets.build(pid)
        b.root.rotation_euler = (0, 0, math.radians(-40))
        camera((0, -6, 0.5), (0, 0, 0.5), ortho=1.35)
        p = os.path.join(OUT, 'tmp', f'sil_{pid}.png')
        bpy.context.scene.cycles.use_denoising = False
        render(p)
        a = Image.open(p).split()[-1].point(lambda v: 255 if v > 40 else 0)
        tile = Image.new('RGB', a.size, 'white')
        tile.paste((18, 18, 24), mask=a)
        tiles.append((pets.PETS[pid]['name'], tile))
    w, h = tiles[0][1].size
    sheet = Image.new('RGB', (w * 6, (h + 40) * 2), 'white')
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, t) in enumerate(tiles):
        r, c = divmod(i, 6)
        sheet.paste(t, (c * w, r * (h + 40)))
        d.text((c * w + w // 2, r * (h + 40) + h + 6), name, fill=(60, 60, 70), font=font, anchor='mt')
    out = os.path.join(OUT, 'silhouettes.png')
    sheet.save(out)
    print('yazıldı', out)


def stages(pet_id='pet_01'):
    """0A oran kılavuzu: Yavru / Genç / Yetişkin yan yana + boy çizgileri."""
    reset(samples=48, res=(1400, 900))
    studio()
    ground('#F4F1EC')
    for i, st in enumerate(('yavru', 'genc', 'yetiskin')):
        b = pets.build(pet_id, st, clay=True)
        b.root.location = ((i - 1) * 0.75, 0, 0)
    camera((0, -7, 1.6), (0, 0, 0.5), ortho=2.3)
    render(os.path.join(OUT, f'stages_{pet_id}.png'))


SOCKET_COLORS = {'socket_head': '#FF3B6B', 'socket_eyes': '#2F8CFF', 'socket_body': '#16B37A',
                 'socket_back': '#9B5CFF', 'socket_hand_L': '#FF9A1F', 'socket_hand_R': '#FF9A1F'}


def sockets(pet_id='pet_01', yaw=-35):
    """0A soket şeması: kil (clay) model + 6 soket renkli işaret ve etiketle."""
    from bpy_extras.object_utils import world_to_camera_view
    from PIL import Image, ImageDraw, ImageFont
    sc = reset(samples=40, res=(900, 1000))
    studio()
    ground('#F4F1EC')
    b = pets.build(pet_id, clay=True)
    b.root.rotation_euler = (0, 0, math.radians(yaw))
    cam = camera((0, -6, 1.3), (0, 0, 0.45), ortho=1.25)
    bpy.context.view_layer.update()
    marks = []
    for ob in b.root.children:
        if ob.type == 'EMPTY' and ob.name.startswith('socket_'):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=ob.matrix_world.translation)
            s = bpy.context.active_object
            s.data.materials.append(pets.vinyl('m_' + ob.name, SOCKET_COLORS[ob.name], coat=0.0))
            p = world_to_camera_view(sc, cam, ob.matrix_world.translation)
            marks.append((ob.name, p.x * sc.render.resolution_x, (1 - p.y) * sc.render.resolution_y))
    path = os.path.join(OUT, f'sockets_{pet_id}.png')
    render(path)
    im = Image.open(path).convert('RGB')
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 22)
    # Etiketler: solda/sağda, üst üste binmesin diye dikeyde en az 44 px aralıklı
    placed = {True: [], False: []}
    for name, x, y in sorted(marks, key=lambda m: m[2]):
        right = name in ('socket_back', 'socket_hand_R', 'socket_head')
        ly = y
        for py in placed[right]:
            if abs(ly - py) < 44:
                ly = py + 44
        placed[right].append(ly)
        tx = im.width - 290 if right else 30
        ex = tx - 10 if right else tx + 250
        d.line((x, y, ex, ly), fill=SOCKET_COLORS[name], width=3)
        d.text((tx, ly - 14), name, fill=SOCKET_COLORS[name], font=f)
    im.save(path)
    print('yazıldı', path)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    clay = '--clay' in sys.argv
    if cmd == 'turnaround':
        turnaround(sys.argv[2], clay=clay)
    elif cmd == 'hero':
        hero(sys.argv[2])
    elif cmd == 'lineup':
        lineup()
    elif cmd == 'silhouettes':
        silhouettes()
    elif cmd == 'stages':
        stages(sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 'pet_01')
    elif cmd == 'sockets':
        sockets(sys.argv[2] if len(sys.argv) > 2 else 'pet_01')
    elif cmd == 'all':
        silhouettes()
        lineup()
        stages()
        sockets()
        for pid in pets.PETS:
            turnaround(pid)
            hero(pid)
