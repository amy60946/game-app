"""Pofi Adası — 12 pet için betikli blockout / konsept modelleri (Blender bpy).

Aşama 0A/0B içindir: oran, silüet, renk ve ayırt edici özellikleri göstermek.
Nihai karakterler yapay zekâ 3D üretim + temizlik ile gelecek; bu modeller
yer tutucu ve tasarım kılavuzu olarak kullanılır.

Koordinatlar: Blender, Z yukarı, ön yüz -Y. Birim metre (Unity'de 1 birim = 1 m).
Ortak gövde şablonu "Genç" evreye göre tanımlıdır; evreler STAGES ile ölçeklenir.
"""
import math
import bpy
from mathutils import Vector

# ---------------------------------------------------------------- palet

def hex_rgba(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


# Ana renkler renk ayrışma analizine göre revize edildi (docs/art/0B_konsept.md).
PETS = {
    'pet_01': dict(name='Pofi', species='tilki-tavşan', main='#FF7A2A', accent='#FFE9CC', extra='#FFB38A'),
    'pet_02': dict(name='Mavi', species='penguen', main='#1F6FE8', accent='#F4F8FF', extra='#FF9A2E'),
    'pet_03': dict(name='Kurbi', species='minik dino', main='#46D063', accent='#D5F7B0', extra='#FFD23F'),
    'pet_04': dict(name='Mimi', species='kedi', main='#FF86C2', accent='#FFE0EF', extra='#FFFFFF'),
    'pet_05': dict(name='Pıtı', species='civciv', main='#FFEA5C', accent='#FFF6C2', extra='#FF8A1F'),
    'pet_06': dict(name='Boncuk', species='ayı', main='#A77BFF', accent='#ECDFFF', extra='#5B3A9E'),
    'pet_07': dict(name='Tosbi', species='deniz kaplumbağası', main='#00A693', accent='#CFF7EE', extra='#0B5E66'),
    'pet_08': dict(name='Piko', species='kirpi', main='#8C5A3C', accent='#FFE6C2', extra='#5E3A22'),
    'pet_09': dict(name='Fifi', species='yavru fil', main='#8EDCFF', accent='#E6F7FF', extra='#FFD84A'),
    'pet_10': dict(name='Arlo', species='aslan yavrusu', main='#FFAE1A', accent='#FFE7B0', extra='#E8501A'),
    'pet_11': dict(name='Lolo', species='lama', main='#FFF1D6', accent='#FFFFFF', extra='#FF9B54'),
    'pet_12': dict(name='Benli', species='uğur böceği', main='#E8202E', accent='#FFE9D6', extra='#2E2438'),
}

# Büyüme evreleri: toplam ölçek, kafa ve gövde oranı (Yavru daha büyük kafalı ve tombul)
STAGES = {
    'yavru': dict(scale=0.80, head=1.12, body=0.88, leg=0.85),
    'genc': dict(scale=1.00, head=1.00, body=1.00, leg=1.00),
    'yetiskin': dict(scale=1.17, head=0.93, body=1.10, leg=1.25),
}

SOCKETS = ['socket_head', 'socket_eyes', 'socket_body', 'socket_back', 'socket_hand_L', 'socket_hand_R']

# ---------------------------------------------------------------- malzemeler

_mats = {}


def vinyl(name, hex_color, rough=0.34, coat=0.45, sss=0.12, clay=False):
    """Yumuşak parlak "vinil oyuncak" malzemesi (Unity'deki URP shader'ın Blender karşılığı)."""
    key = (name, hex_color, clay)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    col = hex_rgba('#BDBDBD' if clay else hex_color)
    b.inputs['Base Color'].default_value = col
    b.inputs['Roughness'].default_value = 0.55 if clay else rough
    b.inputs['Coat Weight'].default_value = 0.0 if clay else coat
    b.inputs['Coat Roughness'].default_value = 0.12
    b.inputs['Subsurface Weight'].default_value = 0.0 if clay else sss
    b.inputs['Subsurface Radius'].default_value = (0.4, 0.25, 0.2)
    b.inputs['Subsurface Scale'].default_value = 0.02
    _mats[key] = m
    return m


def eye_mat(clay=False):
    # Kil render'ında da gözler koyu kalır (yüz okunabilsin)
    return vinyl('eye', '#14141C', rough=0.05, coat=1.0, sss=0.0)


def glint_mat():
    if 'glint' in _mats:
        return _mats['glint']
    m = bpy.data.materials.new('glint')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (1, 1, 1, 1)
    b.inputs['Emission Color'].default_value = (1, 1, 1, 1)
    b.inputs['Emission Strength'].default_value = 3.0
    _mats['glint'] = m
    return m

# ---------------------------------------------------------------- şekil yardımcıları


class Builder:
    def __init__(self, pet_id, stage='genc', clay=False):
        self.id = pet_id
        self.spec = PETS[pet_id]
        self.st = STAGES[stage]
        self.clay = clay
        self.root = bpy.data.objects.new(f'{pet_id}_{stage}', None)
        bpy.context.scene.collection.objects.link(self.root)
        self.head = self.root  # gruplar
        self.parts = []

    def m(self, which):
        hx = self.spec[which] if which in self.spec else which
        return vinyl(f'{self.id}_{which}', hx, clay=self.clay)

    def _finish(self, ob, mat, subsurf=2):
        ob.data.materials.append(mat)
        for p in ob.data.polygons:
            p.use_smooth = True
        if subsurf:
            mod = ob.modifiers.new('subsurf', 'SUBSURF')
            mod.levels = 1
            mod.render_levels = subsurf
        ob.parent = self.root
        self.parts.append(ob)
        return ob

    def ellipsoid(self, name, loc, size, mat, rot=(0, 0, 0), seg=24):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc)
        ob = bpy.context.active_object
        ob.name = f'{self.id}_{name}'
        ob.scale = size
        ob.rotation_euler = [math.radians(a) for a in rot]
        return self._finish(ob, mat)

    def limb(self, name, a, b, r, mat, flat=1.0):
        """a→b doğrultusunda uzamış elipsoid (kol, bacak, kulak)."""
        a, b = Vector(a), Vector(b)
        d = b - a
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1, location=(a + b) / 2)
        ob = bpy.context.active_object
        ob.name = f'{self.id}_{name}'
        ob.scale = (r, r * flat, d.length / 2 + r * 0.4)
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = d.to_track_quat('Z', 'Y')
        return self._finish(ob, mat)

    def cone(self, name, base, tip, r, mat, r2=None):
        base, tip = Vector(base), Vector(tip)
        d = tip - base
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r, radius2=r2 if r2 is not None else r * 0.25,
                                        depth=d.length, location=(base + tip) / 2)
        ob = bpy.context.active_object
        ob.name = f'{self.id}_{name}'
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = d.to_track_quat('Z', 'Y')
        return self._finish(ob, mat, subsurf=2)

    def tube(self, name, points, radii, mat):
        """Yumuşak boru (bıyık, kuyruk, anten, hortum): nokta başına yarıçaplı eğri."""
        cu = bpy.data.curves.new(f'{self.id}_{name}', 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 1.0
        cu.bevel_resolution = 4
        cu.use_fill_caps = True
        sp = cu.splines.new('NURBS')
        sp.points.add(len(points) - 1)
        for p, co, r in zip(sp.points, points, radii):
            p.co = (*co, 1)
            p.radius = r
        sp.use_endpoint_u = True
        sp.order_u = min(4, len(points))
        ob = bpy.data.objects.new(f'{self.id}_{name}', cu)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(mat)
        ob.parent = self.root
        self.parts.append(ob)
        return ob

    def socket(self, name, loc):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = 'SPHERE'
        e.empty_display_size = 0.03
        e.location = loc
        e.parent = self.root
        bpy.context.scene.collection.objects.link(e)
        return e

# ---------------------------------------------------------------- ortak gövde şablonu


def base_body(B, head_z_extra=0.0, ears_top=0.0, belly=True, arms='round', feet='flat', head_size=(0.235, 0.205, 0.21),
              face=True, body_mat='main', head_mat='main'):
    st = B.st
    hs, bs, ls = st['head'], st['body'], st['leg']
    leg_top = 0.12 * ls
    body_c = leg_top + 0.08 * bs
    body_top = body_c + 0.12 * bs
    hx, hy, hz = (v * hs for v in head_size)
    head_c = body_top + hz * 0.82 + head_z_extra
    B.geo = dict(head_c=head_c, hx=hx, hy=hy, hz=hz, body_c=body_c, bs=bs, leg_top=leg_top)

    # ayaklar ve bacaklar
    for s in (-1, 1):
        if feet == 'flat':
            B.ellipsoid(f'foot_{"L" if s < 0 else "R"}', (s * 0.062, -0.018, 0.028), (0.048, 0.07, 0.032), B.m(body_mat))
        else:  # yüzgeç / kuş ayağı
            B.ellipsoid(f'foot_{"L" if s < 0 else "R"}', (s * 0.066, -0.03, 0.02), (0.06, 0.085, 0.022), B.m(feet))
        B.limb(f'leg_{"L" if s < 0 else "R"}', (s * 0.058, 0, 0.04), (s * 0.06, 0, leg_top), 0.045, B.m(body_mat))

    # gövde
    B.ellipsoid('body', (0, 0, body_c), (0.13 * bs, 0.115 * bs, 0.135 * bs), B.m(body_mat))
    if belly:
        B.ellipsoid('belly', (0, -0.062 * bs, body_c - 0.01), (0.092 * bs, 0.06 * bs, 0.1 * bs), B.m('accent'))

    # kollar
    sh_z = body_top - 0.04
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        hand = (s * 0.175 * bs, -0.035, body_c - 0.02)
        if arms == 'round':
            B.limb(f'arm_{side}', (s * 0.11 * bs, 0, sh_z), hand, 0.034, B.m(body_mat))
        else:  # yüzgeç / kanat
            B.limb(f'arm_{side}', (s * 0.11 * bs, 0.0, sh_z), (s * 0.19 * bs, -0.01, body_c - 0.04), 0.04,
                   B.m(arms), flat=0.45)
        B.socket(f'socket_hand_{side}', hand)

    # kafa
    B.ellipsoid('head', (0, 0, head_c), (hx, hy, hz), B.m(head_mat))
    if face:
        add_face(B)

    # Şapka kafa tepesine oturur; kulak/anten/püskül için şapka varyantı seçilir (0A §5).
    B.socket('socket_head', (0, 0, head_c + hz * 0.97))
    B.socket('socket_eyes', (0, -hy * 1.02, head_c + hz * 0.05))
    B.socket('socket_body', (0, -0.11 * bs, body_c))
    B.socket('socket_back', (0, 0.12 * bs, body_c + 0.03))


def add_face(B, eye_spread=0.08, eye_z=0.0, cheeks=True, nose=True, mouth=True, nose_mat='extra_dark'):
    g = B.geo
    hc, hx, hy, hz = g['head_c'], g['hx'], g['hy'], g['hz']
    ez = hc + eye_z + 0.005

    def front_y(x, z):
        v = 1 - (x / hx) ** 2 - ((z - hc) / hz) ** 2
        return -hy * math.sqrt(max(v, 0.02))

    for s in (-1, 1):
        x = s * eye_spread * (hx / 0.2)
        y = front_y(x, ez)
        B.ellipsoid(f'eye_{"L" if s < 0 else "R"}', (x, y + 0.004, ez), (0.036, 0.02, 0.049), eye_mat(B.clay))
        if not B.clay:
            B.ellipsoid(f'glint_{"L" if s < 0 else "R"}', (x + 0.013, y - 0.015, ez + 0.02), (0.011, 0.005, 0.013),
                        glint_mat())
        if cheeks:
            cx, cz = s * 0.125 * (hx / 0.2), hc - 0.045
            B.ellipsoid(f'cheek_{"L" if s < 0 else "R"}', (cx, front_y(cx, cz) + 0.006, cz), (0.028, 0.008, 0.017),
                        vinyl('cheek', '#FF7FA0', rough=0.6, coat=0.0))
    if nose:
        nz = hc - 0.032
        B.ellipsoid('nose', (0, front_y(0, nz) - 0.002, nz), (0.013, 0.011, 0.01),
                    vinyl('nose', '#3A2230' if nose_mat == 'extra_dark' else B.spec['extra']))
    if mouth:
        mz = hc - 0.062
        B.ellipsoid('mouth', (0, front_y(0, mz) + 0.004, mz), (0.014, 0.006, 0.008), vinyl('mouth', '#5A1E2A'))

# ---------------------------------------------------------------- türler


def ring_points(center, radius, n, plane='xz', start=0.0, end=360.0):
    pts = []
    for i in range(n):
        a = math.radians(start + (end - start) * i / max(1, n - (0 if end - start >= 360 else 1)))
        if plane == 'xz':
            pts.append(Vector(center) + Vector((math.cos(a) * radius, 0, math.sin(a) * radius)))
    return pts


def build(pet_id, stage='genc', clay=False):
    B = Builder(pet_id, stage, clay)
    f = SPECIES[pet_id]
    f(B)
    B.root.scale = (B.st['scale'],) * 3
    return B


def sp_pofi(B):  # tilki-tavşan: uzun yuvarlak uçlu tavşan kulakları + kabarık tilki kuyruğu (krem uçlu)
    base_body(B, ears_top=0.3, face=False)
    g = B.geo
    hc = g['head_c']
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        B.limb(f'ear_{side}', (s * 0.07, 0.01, hc + 0.12), (s * 0.12, 0.03, hc + 0.36), 0.05, B.m('main'), flat=0.55)
        B.limb(f'ear_in_{side}', (s * 0.07, -0.012, hc + 0.15), (s * 0.115, 0.008, hc + 0.33), 0.03, B.m('extra'),
               flat=0.3)
    B.ellipsoid('muzzle', (0, -g['hy'] * 0.8, hc - 0.045), (0.085, 0.045, 0.055), B.m('accent'))
    B.limb('tail', (0, 0.1, 0.13), (0.02, 0.24, 0.3), 0.07, B.m('main'))
    B.ellipsoid('tail_tip', (0.025, 0.26, 0.34), (0.06, 0.06, 0.06), B.m('accent'))
    add_face(B)


def sp_mavi(B):  # penguen: beyaz yüz maskesi, turuncu gaga ve ayaklar, yüzgeç kollar
    base_body(B, arms='main', feet='extra', face=False, head_size=(0.215, 0.195, 0.2))
    g = B.geo
    hc = g['head_c']
    B.ellipsoid('egg', (0, 0.005, (g['body_c'] + hc) / 2 - 0.02), (0.185, 0.16, 0.24), B.m('main'))
    B.ellipsoid('egg_belly', (0, -0.085, g['body_c'] + 0.02), (0.135, 0.09, 0.16), B.m('accent'))
    for s in (-1, 1):
        B.limb(f'flipper_{s}', (s * 0.17, 0.0, g['body_c'] + 0.12), (s * 0.28, -0.01, g['body_c'] - 0.07), 0.05,
               B.m('main'), flat=0.35)
    B.ellipsoid('face_mask', (0, -g['hy'] * 0.45, hc - 0.01), (0.15, 0.12, 0.13), B.m('accent'))
    B.geo['hy'] = g['hy']  # yüz, kafa yüzeyine göre
    add_face(B, nose=False, mouth=False)
    B.cone('beak', (0, -g['hy'] * 0.93, hc - 0.035), (0, -g['hy'] - 0.06, hc - 0.045), 0.03, B.m('extra'), r2=0.008)
    pass  # penguende tepe tüyü yok: tüy püskülü Pıtı'nın imzası


def sp_kurbi(B):  # minik dino: sırtta sarı plakalar, kalın kuyruk
    base_body(B, face=False)
    g = B.geo
    hc, bc = g['head_c'], g['body_c']
    i = 0
    for a, h in ((105, 0.1), (70, 0.13), (35, 0.12), (5, 0.1)):
        r = math.radians(a)
        d = Vector((0, math.cos(r), math.sin(r)))
        base = Vector((0, g['hy'] * 0.9 * d.y, hc + g['hz'] * 0.9 * d.z))
        B.cone(f'plate_{i}', base, base + d * h, 0.05, B.m('extra'), r2=0.012); i += 1
    for a, h in ((40, 0.09), (5, 0.08)):
        r = math.radians(a)
        d = Vector((0, math.cos(r), math.sin(r)))
        base = Vector((0, 0.1 * d.y, bc + 0.1 * d.z))
        B.cone(f'plate_{i}', base, base + d * h, 0.045, B.m('extra'), r2=0.012); i += 1
    B.tube('tail', [(0, 0.08, 0.13), (0.06, 0.22, 0.08), (0.18, 0.3, 0.06), (0.28, 0.3, 0.08)],
           [0.08, 0.06, 0.04, 0.02], B.m('main'))
    B.ellipsoid('snout', (0, -g['hy'] * 0.9, hc - 0.055), (0.13, 0.09, 0.075), B.m('main'))
    add_face(B, nose=False)
    for s in (-1, 1):
        B.ellipsoid(f'nostril_{s}', (s * 0.025, -g['hy'] - 0.035, hc - 0.04), (0.007, 0.004, 0.005), vinyl('mouth', '#5A1E2A'))


def sp_mimi(B):  # kedi: üçgen kulaklar, uzun bıyıklar, ince kıvrık kuyruk
    base_body(B, ears_top=0.1)
    g = B.geo
    hc = g['head_c']
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        B.cone(f'ear_{side}', (s * 0.11, 0.0, hc + 0.12), (s * 0.15, 0.0, hc + 0.24), 0.065, B.m('main'), r2=0.012)
        B.cone(f'ear_in_{side}', (s * 0.108, -0.03, hc + 0.13), (s * 0.145, -0.03, hc + 0.22), 0.038, B.m('accent'),
               r2=0.008)
        for k, dz in enumerate((-0.01, -0.03)):
            B.tube(f'whisker_{side}_{k}', [(s * 0.1, -0.15, hc - 0.03 + dz * 0.5), (s * 0.2, -0.16, hc - 0.02 + dz),
                                          (s * 0.28, -0.14, hc - 0.025 + dz * 1.4)], [0.005, 0.004, 0.003],
                   B.m('extra'))
    B.tube('tail', [(0, 0.1, 0.14), (0.05, 0.2, 0.15), (0.08, 0.24, 0.3), (0.03, 0.22, 0.42)], [0.03, 0.026, 0.022, 0.02],
           B.m('main'))


def sp_piti(B):  # civciv: tepe püskülü, kanat kollar, turuncu gaga ve ayaklar
    base_body(B, arms='main', feet='extra', face=False, head_size=(0.205, 0.19, 0.19), belly=False)
    g = B.geo
    hc = g['head_c']
    add_face(B, nose=False, mouth=False)
    B.cone('beak', (0, -g['hy'] * 0.95, hc - 0.03), (0, -g['hy'] - 0.05, hc - 0.035), 0.028, B.m('extra'), r2=0.006)
    for i, (dx, tilt) in enumerate(((-0.025, -25), (0.0, 0), (0.025, 25))):
        B.ellipsoid(f'tuft_{i}', (dx * 1.6, 0.0, hc + g['hz'] * 0.98 + 0.05), (0.022, 0.022, 0.075), B.m('extra'),
                    rot=(0, tilt, 0))
    B.ellipsoid('ball', (0, 0, (g['body_c'] + hc) / 2), (0.235, 0.215, 0.26), B.m('main'))
    B.ellipsoid('fluff_belly', (0, -0.15, g['body_c'] + 0.02), (0.12, 0.07, 0.12), B.m('accent'))
    add_face(B, nose=False, mouth=False)
    B.cone('beak2', (0, -0.2, hc - 0.03), (0, -0.27, hc - 0.035), 0.03, B.m('extra'), r2=0.006)


def sp_boncuk(B):  # ayı: yuvarlak kulaklar, açık renk burun bölgesi
    base_body(B, ears_top=0.05, face=False)
    g = B.geo
    hc = g['head_c']
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        B.ellipsoid(f'ear_{side}', (s * 0.17, 0.01, hc + 0.17), (0.075, 0.04, 0.075), B.m('main'))
        B.ellipsoid(f'ear_in_{side}', (s * 0.17, -0.022, hc + 0.17), (0.045, 0.015, 0.045), B.m('accent'))
    B.ellipsoid('muzzle', (0, -g['hy'] * 0.92, hc - 0.05), (0.09, 0.07, 0.06), B.m('accent'))
    B.ellipsoid('tummy', (0, 0, g['body_c'] - 0.01), (0.165, 0.14, 0.15), B.m('main'))
    B.ellipsoid('tummy_patch', (0, -0.1, g['body_c'] - 0.01), (0.11, 0.06, 0.11), B.m('accent'))
    add_face(B)


def sp_tosbi(B):  # deniz kaplumbağası: sırtta desenli kabuk (sırt soketi kabuğun üstünde), yüzgeçler
    base_body(B, arms='main', feet='main', belly=False, head_size=(0.2, 0.215, 0.175))
    g = B.geo
    bc = g['body_c']
    B.ellipsoid('plastron', (0, -0.075, bc), (0.1, 0.05, 0.11), B.m('accent'))
    B.ellipsoid('shell', (0, 0.1, bc + 0.06), (0.26, 0.17, 0.25), B.m('extra'))
    B.ellipsoid('shell_rim', (0, 0.07, bc + 0.06), (0.275, 0.11, 0.265), B.m('main'))
    for i, (x, z) in enumerate(((0, 0.07), (-0.07, 0.02), (0.07, 0.02), (0, -0.05), (-0.065, -0.07), (0.065, -0.07))):
        B.ellipsoid(f'scute_{i}', (x * 1.6, 0.265, bc + 0.06 + z * 1.6), (0.045, 0.014, 0.04), vinyl('tosbi_scute', '#7FE3D3'))
    for ob in bpy.context.scene.objects:
        if ob.name == 'socket_back' and ob.parent == B.root:
            ob.location = (0, 0.26, bc + 0.06)  # aksesuar kabuğun ÜSTÜNE oturur


def sp_piko(B):  # kirpi: sırtta yuvarlak uçlu yumuşak dikenler, krem yüz
    base_body(B, ears_top=0.08, face=False)
    g = B.geo
    hc, hx, hy, hz, bc = g['head_c'], g['hx'], g['hy'], g['hz'], g['body_c']
    B.ellipsoid('face_mask', (0, -hy * 0.45, hc - 0.02), (0.16, 0.13, 0.14), B.m('accent'))
    add_face(B)
    for s in (-1, 1):
        B.ellipsoid(f'ear_{"L" if s < 0 else "R"}', (s * 0.13, -0.02, hc + 0.12), (0.035, 0.022, 0.035), B.m('main'))
    n = 0
    for ring, (theta, rr, count) in enumerate(((12, 1.0, 5), (38, 1.0, 9), (65, 1.0, 11), (95, 1.0, 11), (125, 1.0, 9))):
        for k in range(count):
            phi = math.radians(-100 + 200 * k / (count - 1))
            th = math.radians(theta)
            d = Vector((math.sin(th) * math.sin(phi), math.sin(th) * math.cos(phi) * 0.9 + 0.25, math.cos(th)))
            d.normalize()
            base = Vector((d.x * hx * 0.85, d.y * hy * 0.85, hc + d.z * hz * 0.85))
            B.cone(f'spike_{n}', base, base + d * 0.11, 0.034, B.m('extra'), r2=0.013)
            n += 1
    for k in range(7):
        phi = math.radians(-60 + 120 * k / 6)
        d = Vector((math.sin(phi) * 0.8, math.cos(phi), 0.15)).normalized()
        base = Vector((d.x * 0.11, d.y * 0.09, bc + 0.02))
        B.cone(f'spike_b{k}', base, base + d * 0.07, 0.028, B.m('extra'), r2=0.011)


def sp_fifi(B):  # yavru fil: iri kulaklar (içi sarı), kısa kıvrık hortum
    base_body(B, face=False)
    g = B.geo
    hc, hy = g['head_c'], g['hy']
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        B.ellipsoid(f'ear_{side}', (s * 0.27, 0.04, hc + 0.02), (0.15, 0.03, 0.16), B.m('main'), rot=(0, s * -10, s * -15))
        B.ellipsoid(f'ear_in_{side}', (s * 0.27, 0.012, hc + 0.02), (0.11, 0.012, 0.12), B.m('extra'), rot=(0, s * -10, s * -15))
    add_face(B, nose=False, mouth=False, eye_z=0.02)
    B.tube('trunk', [(0, -hy * 0.92, hc - 0.02), (0, -hy - 0.04, hc - 0.06), (0, -hy - 0.07, hc - 0.11),
                     (0, -hy - 0.05, hc - 0.14), (0, -hy - 0.03, hc - 0.12)], [0.04, 0.034, 0.028, 0.024, 0.022],
           B.m('main'))


def sp_arlo(B):  # aslan yavrusu: kırmızı-turuncu yele, püsküllü kuyruk
    base_body(B, ears_top=0.08, face=False)
    g = B.geo
    hc, hx, hz = g['head_c'], g['hx'], g['hz']
    for i, p in enumerate(ring_points((0, 0.035, hc), 0.205, 14)):
        B.ellipsoid(f'mane_{i}', p, (0.07, 0.06, 0.07), B.m('extra'))
    B.ellipsoid('mane_back', (0, 0.09, hc), (0.2, 0.08, 0.2), B.m('extra'))
    for s in (-1, 1):
        B.ellipsoid(f'ear_{"L" if s < 0 else "R"}', (s * 0.12, -0.03, hc + 0.15), (0.04, 0.025, 0.04), B.m('main'))
    B.ellipsoid('muzzle', (0, -g['hy'] * 0.82, hc - 0.045), (0.08, 0.045, 0.05), B.m('accent'))
    add_face(B)
    B.tube('tail', [(0, 0.1, 0.13), (0.06, 0.2, 0.1), (0.1, 0.27, 0.2), (0.08, 0.28, 0.3)], [0.018, 0.016, 0.015, 0.014],
           B.m('main'))
    B.ellipsoid('tail_tuft', (0.08, 0.28, 0.33), (0.045, 0.045, 0.055), B.m('extra'))


def sp_lolo(B):  # lama: kısa tutulmuş uzun boyun, uzun kulaklar, boyunda renkli püsküller
    base_body(B, head_z_extra=0.07, ears_top=0.15, head_size=(0.175, 0.17, 0.17), face=False)
    g = B.geo
    hc, bc = g['head_c'], g['body_c']
    B.limb('neck', (0, 0, bc + 0.08), (0, -0.01, hc - 0.05), 0.085, B.m('main'))
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        B.limb(f'ear_{side}', (s * 0.08, 0.0, hc + 0.12), (s * 0.12, 0.01, hc + 0.27), 0.035, B.m('extra'), flat=0.6)
    for i, (dx, dz) in enumerate(((-0.05, 0.0), (0.0, 0.02), (0.05, 0.0), (-0.025, 0.04), (0.025, 0.04))):
        B.ellipsoid(f'wool_{i}', (dx, 0.0, hc + g['hz'] * 0.9 + dz), (0.04, 0.04, 0.035), B.m('accent'))
    B.ellipsoid('muzzle', (0, -g['hy'] * 0.82, hc - 0.05), (0.08, 0.05, 0.055), B.m('accent'))
    add_face(B)
    tassel = ['#FF4FA0', '#22C3B5', '#FFC42E', '#7A5CFF', '#FF6B3D']
    for i, p in enumerate(ring_points((0, -0.01, bc + 0.14), 0.095, 5, start=200, end=340)):
        B.ellipsoid(f'tassel_{i}', (p.x, p.y - 0.085, p.z), (0.022, 0.022, 0.03),
                    vinyl(f'tassel_{i}', tassel[i], clay=B.clay))


def sp_benli(B):  # uğur böceği: benekli kanat kapakları (açılıp kapanır), antenler, açık renk yüz
    base_body(B, face=False, ears_top=0.12, belly=False)
    for s_ in (-1, 1):  # kollar/bacaklar koyu (böcek bacakları)
        for part in ('arm', 'leg', 'foot'):
            ob = bpy.data.objects.get(f'{B.id}_{part}_{"L" if s_ < 0 else "R"}')
            if ob: ob.data.materials[0] = B.m('extra')
    g = B.geo
    hc, hy, bc = g['head_c'], g['hy'], g['body_c']
    B.ellipsoid('face_mask', (0, -hy * 0.42, hc - 0.015), (0.155, 0.13, 0.13), B.m('accent'))
    add_face(B)
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        B.ellipsoid(f'elytron_{side}', (s * 0.065, 0.07, bc + 0.02), (0.085, 0.085, 0.16), B.m('main'), rot=(0, 0, s * -8))
        for k, (dx, dz) in enumerate(((0.03, 0.08), (0.05, -0.02), (0.025, -0.08))):
            B.ellipsoid(f'spot_{side}_{k}', (s * dx + s * 0.03, 0.15, bc + 0.02 + dz), (0.022, 0.01, 0.022),
                        vinyl('spot', '#1A1A22', clay=B.clay))
        B.ellipsoid(f'head_spot_{side}', (s * 0.11, -0.02, hc + 0.13), (0.035, 0.03, 0.03), vinyl('spot', '#1A1A22', clay=B.clay))
        B.tube(f'antenna_{side}', [(s * 0.05, 0.0, hc + 0.16), (s * 0.08, -0.01, hc + 0.25), (s * 0.12, -0.02, hc + 0.3)],
               [0.009, 0.008, 0.007], B.m('extra'))
        B.ellipsoid(f'antenna_tip_{side}', (s * 0.125, -0.02, hc + 0.31), (0.022, 0.022, 0.022), B.m('main'))


SPECIES = {
    'pet_01': sp_pofi, 'pet_02': sp_mavi, 'pet_03': sp_kurbi, 'pet_04': sp_mimi,
    'pet_05': sp_piti, 'pet_06': sp_boncuk, 'pet_07': sp_tosbi, 'pet_08': sp_piko,
    'pet_09': sp_fifi, 'pet_10': sp_arlo, 'pet_11': sp_lolo, 'pet_12': sp_benli,
}
