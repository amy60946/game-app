# Gezegen Koşusu — Ay yüzeyi donatıları (25 Ekim 2026): yolun yanındaki yakın süsler + uzak sırt + gökte Dünya.
# Orijin zeminde (z = 0), x/y'de ortada; önü Blender −Y (yaklaşan koşucuya). Gökteki Dünya ve halkalı gezegen: orijin küre merkezi.
#   rs_dome     ~8 m yaşam kubbesi: panelli kubbe, sıcak ışıklı lomboz pencereler, hava kilidi kapısı, güneş panelleri, anten
#   rs_rocket   ~10 m sevimli roket + fırlatma rampası + kafes kule (servis kolu, lamba)
#   rs_dish     ~5 m üç ayaklı uydu çanağı · rs_rover ~3 m altı tekerlekli Ay arabası · rs_cargo ~2,5 m sandık + varil yığını
#   rs_pennant  ~3 m renkli flama direği (gerçek bayrak/yazı yok) · rs_rocks 3–5 Ay taşı · rs_crystals ~1,5 m yer kristali öbeği
#   rs_ridge    ~220 × 35 m uzak krater duvarı / dağ sırtı (daha açık ve mavimsi: derinlik)
#   rs_earth    ~40 m Dünya (stilize: mavi okyanus, yeşil-aşı kara, beyaz bulut girdapları)
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
import uzay_kit as UK
import gezegen_engeller as GE
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep
import kit
from kit import blob, tube, cyl

REG = lambda: UK._cached('don_rock', lambda: UK.m_regolith('don_rock', ('#6e6a80', '#928da4', '#bab5c8'), craters=0.6, dust=0.4, seed=3.0, scale=1.4))
DUSTM = lambda: UK._cached('don_dust', lambda: UK.m_regolith('don_dust', ('#8c879c', '#a6a1b4', '#c4bfd0'), craters=0.15, dust=0.3, seed=6.0, scale=2.5))


def place(o, loc=None, rot=None, scale=None):
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = [math.radians(a) for a in rot]
    if scale is not None: o.scale = scale
    return o


def group_transform(parts, loc=(0, 0, 0), rot=(0, 0, 0), s=1.0):
    root = bpy.data.objects.new('grp', None); bpy.context.scene.collection.objects.link(root)
    for p in parts: p.parent = root
    root.location = loc; root.rotation_euler = [math.radians(a) for a in rot]; root.scale = (s, s, s); bpy.context.view_layer.update()
    for p in parts:
        mw = p.matrix_world.copy(); p.parent = None; p.matrix_world = mw
    bpy.data.objects.remove(root)
    return parts


def dust_mound(name, rx, ry, h, loc=(0, 0, 0), seed=0):
    return GE_mound(name, loc[0], loc[1], rx, ry, h, seed)


def GE_mound(name, cx, cy, rx, ry, h, seed):
    import kosu_engeller as KE
    return KE.sand_mound(name, cx, cy, rx, ry, h, DUSTM(), seed)


def m_panels(name, base=UK.CREAM, seam='#3b3656', mer=8, ring=0.55, var=0.06):
    """Kubbe/kapsül paneli: nesne koordinatında meridyen + paralel dikiş, panel başına ton, kenar aşınması, oyukta kir, tepede toz."""
    def b(nt, bsdf):
        G = EK.EG(nt); x, y, z = G.sep(G.obj()); cw = G.coords()
        ang = G.math('ARCTAN2', y, x)
        m1 = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', ang, mer)))
        m2 = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', z, math.pi / ring)))
        seamm = G.math('MAXIMUM', G.rng(m1, 0.06, 0.02), G.rng(m2, 0.06, 0.02))
        cell = G.math('ADD', G.math('ROUND', G.math('MULTIPLY', ang, mer / math.pi)), G.math('MULTIPLY', G.math('ROUND', G.math('DIVIDE', z, ring)), 7.3))
        tone = G.math('FRACT', G.math('MULTIPLY', G.math('SINE', G.math('MULTIPLY', cell, 12.9898)), 43758.5))
        col = G.mix(G.rng(tone, 0.0, 1.0, 0, var * 2), UK._sh(base, 0.97), UK._sh(base, 1.06))
        col = G.mix(G.rng(tone, 0.85, 1.0, 0, 0.5), col, UK._sh(base, 0.88))
        col = G.mix(0.08, col, G.noise4(cw, 25.0, 3, 0.6, 'Color'), 'OVERLAY')
        col = G.mix(G.math('MULTIPLY', seamm, 0.75), col, seam)
        col = G.mix(G.rng(G.ao(0.2), 0.85, 0.35, 0, 0.45), col, '#3b3656')
        col = G.mix(G.math('MULTIPLY', G.rng(G.nz(), 0.55, 0.95), G.rng(G.noise4(cw, 1.2, 3), 0.45, 0.68, 0, 0.45)), col, UK.DUST)
        x2, y2, z2 = G.sep(G.pos())
        col = G.mix(G.rng(z2, 0.5, 0.0, 0, 0.5), col, UK._sh(UK.DUST, 0.92))
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.6; bb.inputs['Distance'].default_value = 0.02
        G.l.new(G.math('SUBTRACT', 1.0, seamm), bb.inputs['Height']); G.l.new(bb.outputs['Normal'], bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def porthole(name, loc, nrm, r, glow=UK.SUN, frame=UK.CORAL):
    """Lomboz: çerçeve halkası + sıcak ışıklı cam + 6 cıvata."""
    FR = UK._cached('ph_' + frame, lambda: UK.m_paint('ph_' + frame, frame, chips=0.3, dust=0.2))
    GL = UK._cached('phg_' + glow, lambda: UK.m_glow('phg_' + glow, glow, core='#fff4d8', hot=0.8))
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=r * 0.2, major_segments=24, minor_segments=8)
    t = bpy.context.object; t.name = name + '_frame'; t.data.materials.append(FR)
    g = cyl(name + '_glass', (0, 0, -r * 0.02), r * 0.95, r * 0.12, GL, verts=24, bevel=0.0)
    parts = [t, g]
    for k in range(6):
        a = k / 6 * TAU; parts.append(UK.bolt((math.cos(a) * r, math.sin(a) * r, r * 0.18), (0, 0, 1), r * 0.09))
    q = V(nrm).normalized().to_track_quat('Z', 'Y')
    for p in parts:
        p.rotation_mode = 'QUATERNION'; p.rotation_quaternion = q @ (p.rotation_quaternion if p.rotation_mode == 'QUATERNION' else p.rotation_euler.to_quaternion())
        p.location = V(loc) + q @ V(p.location)
    return parts


def solar_panel(name, loc, w, h, tilt, yaw):
    """Güneş paneli: lacivert hücre ızgarası (çıkartma), alüminyum çerçeve, tek ayak + eğik mafsal."""
    def cells(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cv.rect(0, 0, W, H, carve=False, col=EK.C('#2a3570'))
        nx, ny = 6, 4
        for i in range(1, nx): cv.line([(W * i / nx, 0.02), (W * i / nx, H - 0.02)], 0.012, col=EK.C('#9fb3e8'))
        for j in range(1, ny): cv.line([(0.02, H * j / ny), (W - 0.02, H * j / ny)], 0.012, col=EK.C('#9fb3e8'))
        for i in range(nx):
            for j in range(ny): cv.line([(W * (i + 0.15) / nx, H * (j + 0.8) / ny), (W * (i + 0.45) / nx, H * (j + 0.8) / ny)], 0.01, carve=False, col=EK.C('#5a73c8'))
    d = GE.decal(name + 'd', w, h, cells, ppm=160, depth=0.003, groove=0.002, chips=0.0, fade=0.05)
    P = UK.m_paint(name + 'p', '#2a3570', chips=0.0, scratch=0.2, dust=0.4, dec=d)
    AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3))
    pan = EK.rounded_box(name, (w, h, 0.05), 0.012, 0.04, [P], loc=(0, 0, 0))
    bpy.context.view_layer.update()
    EK.planar_dec_uv(pan, (-w / 2, -h / 2, 0.03), (1, 0, 0), (0, 1, 0), w, h, face_dir=(0, 0, 1))
    frame = []
    for (fx, fy, fw, fh) in ((0, -h / 2, w + 0.06, 0.05), (0, h / 2, w + 0.06, 0.05), (-w / 2, 0, 0.05, h), (w / 2, 0, 0.05, h)):
        frame.append(EK.rounded_box(name + '_fr', (fw, fh, 0.07), 0.01, 0.03, [AL], loc=(fx, fy, 0.0)))
    grp = group_transform([pan] + frame, (loc[0], loc[1], loc[2]), (tilt, 0, yaw))
    pole = cyl(name + '_pole', (loc[0], loc[1], loc[2] / 2), 0.05, loc[2], AL, verts=10, bevel=0.0)
    foot = cyl(name + '_foot', (loc[0], loc[1], 0.04), 0.22, 0.08, UK._cached('gunm', lambda: UK.m_metal('gunm', UK.GUN, dust=0.4)), verts=12, bevel=0.01)
    return grp + [pole, foot]


# ================================================================== rs_dome

def build_dome():
    R0 = 3.9; ZB = 0.6
    BASE = UK.m_paint('domebase', UK.NAVY, chips=0.35, dust=0.5, grime=0.5, seed=1.0)
    GUN = UK._cached('gunm', lambda: UK.m_metal('gunm', UK.GUN, dust=0.4))
    hi = []
    hi.append(cyl('dbase', (0, 0, ZB / 2), R0 + 0.05, ZB, BASE, verts=64, bevel=0.03))
    hi.append(cyl('dskirt', (0, 0, 0.08), R0 + 0.3, 0.16, GUN, verts=64, bevel=0.03))
    prof = [(R0 * math.cos(math.radians(a)), R0 * math.sin(math.radians(a))) for a in range(0, 91, 3)]
    prof = [(r, z) for (r, z) in prof]
    dome = EK.lathe_grid('dome', prof + [(0.0, R0)], 64, [m_panels('domep', UK.CREAM)], loc=(0, 0, ZB), uv=False)
    hi.append(dome)
    # bant: kubbe dibinde mercan halka + sarı çizgi
    hi.append(cyl('dband', (0, 0, ZB + 0.12), R0 + 0.06, 0.24, UK.m_paint('dbandp', UK.CORAL, chips=0.35, dust=0.4, seed=2.0), verts=64, bevel=0.02))
    for k in range(32):
        a = k / 32 * TAU; hi.append(UK.bolt((math.cos(a) * (R0 + 0.06), math.sin(a) * (R0 + 0.06), ZB / 2), (math.cos(a), math.sin(a), 0), 0.04))
    # lomboz pencereler (önde yarım çevre)
    for k, a_deg in enumerate((-148, -112, -68, -32, 160, 20)):
        a = math.radians(a_deg); el = math.radians(30 if k % 2 == 0 else 22)
        n = V((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        hi += porthole('port', tuple(V((0, 0, ZB)) + n * (R0 + 0.02)), tuple(n), 0.42 if k % 2 == 0 else 0.32, glow=UK.SUN if k % 3 else '#ffcf6a')
    # hava kilidi tüneli (önde, −Y) + kapı
    TUN = UK.m_paint('tunnel', UK.CREAM, chips=0.35, dust=0.5, seed=3.0)
    tun = cyl('tunnel', (0, -R0 - 0.55, 1.35), 1.05, 2.2, TUN, rot=(90, 0, 0), verts=32, bevel=0.03)
    hi.append(tun)
    hi.append(cyl('tunring', (0, -R0 - 1.62, 1.35), 1.12, 0.14, UK.m_paint('tunr', UK.TEAL, chips=0.35, dust=0.4, seed=4.0), rot=(90, 0, 0), verts=32, bevel=0.02))
    def doorart(cv):
        W, H = cv.wm, cv.H / cv.ppm
        UK.d_hazard(cv, 0.05, 0.05, W - 0.1, 0.22, c1=UK.SUN, c2=UK.NAVY, step=0.18)
        cv.ell(W / 2, H * 0.68, 0.22, 0.22, col=EK.C('#ffd76a'))
        cv.line(EK.arcpts(W / 2, H * 0.68, 0.25, 0.25, 0, 360, 32), 0.04, col=EK.C(UK.STEEL))
        cv.rect(W * 0.78, H * 0.38, W * 0.88, H * 0.5, carve=True, col=EK.C(UK.SUN), layer='raise')
        UK.d_planet(cv, W * 0.3, H * 0.4, 0.09, body=UK.CORAL, ring=UK.SUN)
    dd = GE.decal('doorart', 1.2, 1.8, doorart, ppm=220, seed=11)
    DOOR = UK.m_paint('door', UK.NAVY, chips=0.3, dust=0.4, dec=dd, seed=5.0)
    door = EK.rounded_box('door', (1.2, 0.12, 1.8), 0.1, 0.04, [DOOR], loc=(0, -R0 - 1.68, 1.12), seed=6)
    bpy.context.view_layer.update(); GE.front_dec(door, -0.6, -R0 - 1.74, 0.22, 1.2, 1.8); hi.append(door)
    hi.append(EK.rounded_box('step', (1.6, 0.6, 0.16), 0.03, 0.05, [GUN], loc=(0, -R0 - 2.0, 0.08), seed=7))
    hi.append(EK.rounded_box('step', (1.4, 0.45, 0.16), 0.03, 0.05, [GUN], loc=(0, -R0 - 1.9, 0.24), seed=8))
    hi += UK.lamp('doorlamp', (0, -R0 - 1.62, 2.52), 0.12, UK.SUN, cage=True, base_h=0.06)
    # anten direği + minik çanak + lamba (tepede)
    AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3))
    hi.append(cyl('mast', (0.6, 0.4, ZB + R0 + 0.6), 0.05, 1.6, AL, verts=10, bevel=0.0))
    dish = EK.lathe_grid('mdish', [(0.0, 0.0), (0.12, 0.01), (0.3, 0.06), (0.42, 0.13), (0.45, 0.16), (0.4, 0.15), (0.0, 0.03)], 24,
                         [UK.m_paint('mdishp', UK.CREAM, chips=0.3, dust=0.3, seed=9.0)], uv=False)
    place(dish, (0.6, 0.25, ZB + R0 + 1.1), (-60, 0, 20)); hi.append(dish)
    hi += UK.lamp('mlamp', (0.6, 0.4, ZB + R0 + 1.4), 0.09, UK.CORAL, cage=True, base_h=0.05)
    # güneş panelleri (sağda) + kablo
    hi += solar_panel('solar', (5.4, -1.2, 1.3), 2.2, 1.3, 35, 20)
    hi += solar_panel('solar', (5.9, 1.4, 1.3), 2.2, 1.3, 35, 20)
    CC = UK.m_rubber('dcab', UK.CORAL)
    hi.append(UK.cable('dcable', [(3.95, -0.6, 0.25), (4.6, -0.9, 0.06), (5.3, -1.1, 0.06), (5.4, -1.2, 0.5)], 0.045, CC, res=4))
    hi.append(UK.cable('dcable', [(3.95, 0.6, 0.2), (4.8, 1.0, 0.05), (5.8, 1.35, 0.05), (5.9, 1.4, 0.5)], 0.045, UK.m_rubber('dcab2', UK.TEAL), res=4))
    # yanda küçük sandık + toz eteği
    hi += GE.crate('dcrate', (0.9, 0.7, 0.6), (-4.6, -1.6, 0.0), UK.SUN, rot=20, seed=12)
    import kosu_engeller as KE
    hi.append(KE.sand_rect('ddust', 0, 0, 2 * (R0 + 0.3), 2 * (R0 + 0.3), 0.18, 0.7, DUSTM(), 3, seg_len=0.4, r=R0 + 0.29))
    kit.to_mesh_all()
    decim = [(r'^dbase$', 160), (r'^dskirt$', 130), (r'^dome$', 700), (r'^dband$', 130), (r'^port_frame$', 40), (r'^port_glass$', 24), (r'^tunnel$', 120),
             (r'^tunring$', 64), (r'^door$', 40), (r'^step$', 12), (r'^doorlamp_', 30), (r'^mast$', 1.0), (r'^mdish$', 60), (r'^mlamp_', 30),
             (r'^solar$', 12), (r'^solar_fr$', 12), (r'^solar_(pole|foot)$', 30), (r'^dcable$', 50), (r'^dcrate', 14), (r'^ddust$', 200)]
    weights = [(r'^(door|doorlamp_|port_)', 1.6), (r'^dome$', 1.0), (r'^solar', 1.2), (r'^ddust$', 0.3), (r'^dskirt$', 0.5)]
    return hi, None, dict(decim=decim, weights=weights, tex=1024, budget=3000, ao_dist=0.6, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_rocks

def build_rocks():
    hi = []
    for k, (x, y, s) in enumerate(((0.0, 0.0, 1.25), (0.95, -0.35, 0.75), (-0.8, 0.2, 0.6), (0.4, 0.75, 0.45), (-0.25, -0.75, 0.32))):
        o = GE.lumpy_rock('mrock', (s * 1.35, s * 1.05, s * 0.85), REG(), seed=60 + k, sub=4, flat=s * 0.15, rough=0.2,
                          craters=[((0.3, -1, 0.6), 0.32, 0.16), ((-0.7, 0.2, 0.8), 0.22, 0.12)] if s > 0.5 else ())
        o.location = (x, y, -s * 0.1); o.rotation_euler = (0, 0, k * 1.3); hi.append(o)
    hi.append(GE_mound('rdust', 0.1, 0.0, 1.45, 1.1, 0.09, 4))
    R = random.Random(5)
    for k in range(10):
        s = R.uniform(0.06, 0.16); a = R.uniform(0, TAU); r = R.uniform(1.1, 1.9)
        o = GE.lumpy_rock('pebble', (s * 1.3, s, s * 0.7), REG(), seed=80 + k, sub=2, flat=s * 0.1, rough=0.25)
        o.location = (math.cos(a) * r, math.sin(a) * r * 0.8, 0); hi.append(o)
    decim = [(r'^mrock$', 150), (r'^rdust$', 1.0), (r'^pebble$', 20)]
    weights = [(r'^mrock$', 1.0), (r'^rdust$', 0.3), (r'^pebble$', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=1000, ao_dist=0.4)


# ================================================================== rs_crystals

def build_crystals():
    hi = []
    base = GE.lumpy_rock('cbase', (1.3, 1.0, 0.45), REG(), seed=91, sub=4, flat=0.06, rough=0.22); hi.append(base)
    import ay_zemin as AZ
    hi += AZ.crystal_cluster(0.0, 0.0, 0.28, 1.15, 7, name='gcry')
    hi += AZ.crystal_cluster(0.45, -0.25, 0.2, 0.6, 8, name='gcry')
    hi += AZ.crystal_cluster(-0.45, 0.15, 0.18, 0.55, 9, name='gcry')
    R = random.Random(2)
    for k in range(5):
        a = R.uniform(0, TAU); hi.append(GE.crystal('gcry', (math.cos(a) * 0.85, math.sin(a) * 0.7, 0.0), (R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), 1.0), R.uniform(0.15, 0.28), 0.04,
                                                    UK._cached('gcv', lambda: UK.m_crystal('gcv', UK.VIOLET, UK.CYAN, -0.1, 0.9)), twist=R.uniform(0, 1)))
    hi.append(GE_mound('cdust', 0.0, 0.0, 0.95, 0.8, 0.07, 6))
    decim = [(r'^cbase$', 200), (r'^gcry$', 36), (r'^cdust$', 1.0)]
    weights = [(r'^gcry$', 1.5), (r'^cbase$', 0.8), (r'^cdust$', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=1200, ao_dist=0.3)


# ================================================================== rs_pennant

def build_pennant():
    AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3)); GUN = UK._cached('gunm', lambda: UK.m_metal('gunm', UK.GUN, dust=0.4))
    hi = [cyl('ppole', (0, 0, 1.55), 0.04, 3.1, AL, verts=12, bevel=0.0), blob('pball', (0, 0, 3.14), (0.07, 0.07, 0.07), EK.m_gold('pgold'), seg=16),
          cyl('pbase', (0, 0, 0.05), 0.28, 0.1, GUN, verts=16, bevel=0.015)]
    for k in range(4):
        a = k / 4 * TAU + 0.4; hi.append(UK.bolt((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.1), (0, 0, 1), 0.02))
    # flama: zikzak şeritli üçgen (mercan / ayçiçeği / camgöbeği), rüzgârsız Ay'da tel çubukla açık tutulur
    def art(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cols = (UK.CORAL, UK.SUN, UK.TEAL, UK.CREAM)
        for k in range(8):
            cv.rect(W * k / 8, 0, W * (k + 1) / 8 + 0.002, H, carve=False, col=EK.C(cols[k % 4]))
        UK.d_star(cv, W * 0.18, H * 0.5, 0.11, col=UK.CREAM)
    d = GE.decal('pennart', 1.3, 0.7, art, ppm=200, depth=0.002, chips=0.1, fade=0.1)
    FL = UK.m_paint('pennp', UK.CORAL, chips=0.0, scratch=0.0, dust=0.15, dec=d)
    us = np.linspace(0, 1, 14); vs = np.linspace(-1, 1, 5)
    U, Vv = np.meshgrid(us, vs)
    X = 0.03 + U * 1.3; Z = 2.75 + Vv * 0.35 * (1 - U) - 0.05 * U; Y = 0.05 * np.sin(U * 6.0) * U
    f = EK.grid_obj('pflag', np.stack([X, Y, Z], -1), np.stack([U, (Vv + 1) / 2], -1), [FL], flip=True)
    f.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(f.data.polygons))
    hi.append(f)
    hi.append(cyl('prod', (0.68, 0.0, 3.1), 0.012, 1.3, AL, rot=(0, 90, 0), verts=6, bevel=0.0))
    hi.append(GE_mound('pdust', 0, 0, 0.45, 0.45, 0.06, 2))
    decim = [(r'^ppole$', 1.0), (r'^pball$', 40), (r'^pbase$', 40), (r'^pflag$', 1.0), (r'^prod$', 1.0), (r'^pdust$', 1.0)]
    weights = [(r'^pflag$', 2.0), (r'^pdust$', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=600, ao_dist=0.2, ds_low=True, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_cargo

def build_cargo():
    hi = []
    hi += GE.crate('cg1', (1.4, 1.0, 0.8), (-0.35, 0.1, 0.0), UK.MINT, rot=4, seed=21)
    hi += GE.crate('cg2', (0.95, 0.75, 0.6), (-0.4, 0.15, 0.8), UK.CORAL, rot=-9, seed=22)
    hi += GE.crate('cg3', (0.7, 0.55, 0.45), (-0.3, 0.1, 1.4), UK.SUN, rot=12, seed=23)
    def barrel(name, loc, col, rot=(0, 0, 0), h=0.9, r=0.3):
        P = UK.m_paint(name + 'p', col, chips=0.4, dust=0.4, seed=len(name))
        B = UK.m_paint(name + 'b', UK.NAVY, chips=0.3, dust=0.4, seed=len(name) + 1)
        prof = [(0.0, 0.0), (r * 0.95, 0.0), (r, 0.03), (r, h * 0.2), (r * 1.04, h * 0.22), (r, h * 0.24), (r, h * 0.76), (r * 1.04, h * 0.78), (r, h * 0.8),
                (r, h - 0.03), (r * 0.95, h), (r * 0.2, h), (r * 0.2, h + 0.03), (0.0, h + 0.03)]
        o = EK.lathe_grid(name, prof, 24, [P], uv=False)
        bands = [cyl(name + '_band', (0, 0, z), r + 0.012, 0.05, B, verts=24, bevel=0.005) for z in (h * 0.22, h * 0.78)]
        return group_transform([o] + bands, loc, rot)
    hi += barrel('brl1', (0.85, -0.25, 0.0), UK.CORAL)
    hi += barrel('brl2', (0.95, 0.45, 0.0), UK.TEAL)
    hi += barrel('brl3', (0.55, -0.85, 0.3), UK.SUN, rot=(90, 0, 35))
    hi.append(GE_mound('cgdust', 0.1, 0.0, 1.5, 1.2, 0.1, 7))
    kit.to_mesh_all()
    decim = [(r'^cg[123]$', 50), (r'_rib$', 12), (r'_corner$', 12), (r'_latch$', 12), (r'_handle$', 30), (r'^brl[123]$', 140), (r'_band$', 40), (r'^cgdust$', 1.0)]
    weights = [(r'^cg[123]$', 1.1), (r'^brl', 1.0), (r'^cgdust$', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2000, ao_dist=0.3, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_dish

def build_dish():
    AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3)); GUN = UK._cached('gunm', lambda: UK.m_metal('gunm', UK.GUN, dust=0.4))
    hi = []
    top = V((0, 0, 2.3))
    for k in range(3):
        a = k / 3 * TAU + math.pi / 2
        foot = V((math.cos(a) * 1.5, math.sin(a) * 1.5, 0.05))
        hi.append(UK.cable('leg', [tuple(foot), tuple((foot + top) / 2 + V((0, 0, 0.05))), tuple(top)], 0.07, UK.m_paint('legp', UK.NAVY, chips=0.3, dust=0.4), res=3))
        hi.append(cyl('dfoot', tuple(foot), 0.22, 0.1, GUN, verts=12, bevel=0.015))
    hi.append(EK.rounded_box('head', (0.7, 0.7, 0.55), 0.06, 0.05, [UK.m_paint('headp', UK.SUN, chips=0.35, dust=0.4, seed=2.0)], loc=(0, 0, 2.5), seed=3))
    hi.append(cyl('yoke', (0, 0, 2.95), 0.18, 0.4, GUN, verts=14, bevel=0.02))
    prof = [(0.0, 0.0), (0.4, 0.03), (0.9, 0.14), (1.4, 0.33), (1.8, 0.56), (2.0, 0.7), (1.95, 0.72), (1.75, 0.6), (1.35, 0.4), (0.9, 0.23), (0.4, 0.12), (0.0, 0.1)]
    dish = EK.lathe_grid('dish', prof, 40, [m_panels('dishp', UK.CREAM, mer=8, ring=0.35)], uv=False)
    feed = [cyl('feed', (0, 0, 1.25), 0.1, 0.3, GUN, verts=12, bevel=0.01), blob('feedtip', (0, 0, 1.42), (0.09, 0.09, 0.07), UK.m_glow('feedg', UK.CYAN), seg=12)]
    for k in range(3):
        a = k / 3 * TAU
        feed.append(UK.cable('strut', [(math.cos(a) * 1.6, math.sin(a) * 1.6, 0.5), (math.cos(a) * 0.8, math.sin(a) * 0.8, 0.95), (0, 0, 1.15)], 0.025, AL, res=2))
    back = [cyl('dhub', (0, 0, -0.05), 0.35, 0.2, GUN, verts=16, bevel=0.02)]
    grp = group_transform([dish] + feed + back, (0, -0.1, 3.2), (48, 0, 0))
    hi += grp
    hi += UK.lamp('dlamp', (0.0, 0.42, 2.78), 0.08, UK.CORAL, cage=True, base_h=0.05)
    kit.to_mesh_all()
    decim = [(r'^leg$', 60), (r'^dfoot$', 30), (r'^head$', 40), (r'^yoke$', 40), (r'^dish$', 420), (r'^feed$', 40), (r'^feedtip$', 30), (r'^strut$', 30),
             (r'^dhub$', 40), (r'^dlamp_', 30), (r'^ddust$', 1.0)]
    weights = [(r'^dish$', 1.3), (r'^ddust$', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=1500, ao_dist=0.4, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_rover

def wheel(name, loc, r=0.32, w=0.24):
    """Tombul tekerlek: lastik halka + kabartı (tırtıl) bölmeleri + jant göbeği."""
    TY = UK._cached('tyre', lambda: UK.m_rubber('tyre', '#3a3848')); HUB = UK._cached('hub', lambda: UK.m_paint('hub', UK.SUN, chips=0.3, dust=0.4))
    th = np.linspace(0, TAU, 49); yy = np.linspace(-w / 2, w / 2, 7)
    TH, YY = np.meshgrid(th, yy)
    lug = 0.035 * (np.cos(TH * 12) > 0.3) * (np.abs(YY) < w * 0.42)
    RR = r * (0.86 + 0.14 * np.sqrt(np.clip(1 - (YY / (w / 2)) ** 2, 0, 1))) + lug
    P = np.stack([YY, RR * np.cos(TH), RR * np.sin(TH)], -1)
    t = EK.grid_obj(name, P, None, [TY], flip=False); EK.weld(t)
    parts = [t]
    for s in (-1, 1):
        parts.append(EK.disc(name + '_side', r * 0.9, 0, 24, [TY], loc=(0, 0)))
        o = parts[-1]; o.rotation_euler = (0, math.radians(90 * s), 0); o.location = (s * w * 0.5, 0, 0)
    parts.append(cyl(name + '_hub', (-w * 0.5, 0, 0), r * 0.5, 0.06, HUB, rot=(0, 90, 0), verts=16, bevel=0.01))
    parts.append(cyl(name + '_hub', (w * 0.5, 0, 0), r * 0.5, 0.06, HUB, rot=(0, 90, 0), verts=16, bevel=0.01))
    return group_transform(parts, loc)


def build_rover():
    hi = []
    BODY = UK.m_paint('rbody', UK.CREAM, chips=0.35, dust=0.5, grime=0.5, seed=1.0)
    COR = UK.m_paint('rcoral', UK.CORAL, chips=0.35, dust=0.5, seed=2.0)
    GUN = UK._cached('gunm', lambda: UK.m_metal('gunm', UK.GUN, dust=0.4)); AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3))
    GLASS = UK.m_glow('rglass', '#5fc7e0', core='#e8fbff', hot=0.6)
    def side_art(cv):
        W, H = cv.wm, cv.H / cv.ppm
        cv.rect(0.0, H * 0.4, W, H * 0.58, carve=False, col=EK.C(UK.TEAL))
        UK.d_planet(cv, W * 0.75, H * 0.48, 0.13, body=UK.CORAL, ring=UK.SUN)
        for k in range(3): UK.d_star(cv, W * 0.2 + k * 0.18, H * 0.48, 0.05, col=UK.CREAM)
    ds = GE.decal('rside', 2.2, 0.5, side_art, ppm=220, seed=3)
    BODYD = UK.m_paint('rbodyd', UK.CREAM, chips=0.35, dust=0.5, grime=0.5, dec=ds, seed=1.0)
    chassis = EK.rounded_box('chassis', (1.5, 2.6, 0.5), 0.12, 0.05, [BODYD], loc=(0, 0, 0.72), chips=0.01, seed=4)
    bpy.context.view_layer.update()
    EK.planar_dec_uv(chassis, (0.76, 1.1, 0.48), (0, -1, 0), (0, 0, 1), 2.2, 0.5, face_dir=(1, 0, 0))
    hi.append(chassis)
    hi.append(EK.rounded_box('skirt', (1.62, 2.7, 0.12), 0.05, 0.05, [COR], loc=(0, 0, 0.5), seed=5))
    # kabin: kubbe camlı küçük oturak (önde)
    cab = blob('cab', (0, -0.55, 1.18), (0.58, 0.62, 0.5), GLASS, seg=32); hi.append(cab)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.06, major_segments=32, minor_segments=8, location=(0, -0.55, 1.0))
    t = bpy.context.object; t.name = 'cabring'; t.scale = (0.98, 1.05, 1.0); t.data.materials.append(COR); hi.append(t)
    # arka: güneş paneli tablası + anten + flama + minik çanak
    sp = solar_panel('rsolar', (0, 0.75, 1.22), 1.25, 0.9, 12, 0); hi += sp[:5]
    for o in sp[5:]: bpy.data.objects.remove(o)
    hi.append(cyl('rmast', (0.55, 1.05, 1.6), 0.025, 1.3, AL, verts=8, bevel=0.0))
    us = np.linspace(0, 1, 6); vs = np.linspace(0, 1, 3); U, Vv = np.meshgrid(us, vs)
    fl = EK.grid_obj('rflag', np.stack([0.57 + U * 0.42, 1.05 + 0.03 * np.sin(U * 5), 2.2 - Vv * 0.26 * (1 - U * 0.7)], -1), None,
                     [UK.m_paint('rflagp', UK.SUN, chips=0.0, scratch=0.0, dust=0.1)])
    fl.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(fl.data.polygons)); hi.append(fl)
    d = EK.lathe_grid('rdish', [(0.0, 0.0), (0.12, 0.02), (0.22, 0.07), (0.25, 0.09), (0.21, 0.09), (0.0, 0.03)], 20,
                      [UK.m_paint('rdishp', UK.CREAM, chips=0.3, dust=0.3)], uv=False)
    place(d, (-0.45, 1.05, 1.38), (-50, 0, 160)); hi.append(d)
    hi.append(cyl('rdmast', (-0.45, 1.05, 1.15), 0.025, 0.3, AL, verts=8, bevel=0.0))
    # farlar (önde), tampon, alet kutusu, uyarı şeridi
    for sx in (-1, 1):
        hi += UK.lamp('rhead', (sx * 0.5, -1.3, 0.82), 0.11, UK.SUN, cage=False, base_h=0.04)
        for o in hi[-2:]:
            q = V((0, -1, 0)).to_track_quat('Z', 'Y'); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
            o.location = V((sx * 0.5, -1.3, 0.8)) + q @ (V(o.location) - V((sx * 0.5, -1.3, 0.82)))
    hi.append(EK.rounded_box('bumper', (1.55, 0.14, 0.18), 0.05, 0.04, [GUN], loc=(0, -1.36, 0.6), seed=6))
    hi += GE.crate('rbox', (0.5, 0.36, 0.3), (0.45, 0.25, 0.97), UK.SUN, rot=0, seed=7)
    # süspansiyon kolları + altı tekerlek
    for sx in (-1, 1):
        for k, wy in enumerate((-0.95, 0.0, 0.95)):
            hi += wheel('wheel', (sx * 0.98, wy, 0.32))
            hi.append(UK.cable('arm', [(sx * 0.7, wy * 0.9, 0.62), (sx * 0.85, wy, 0.45), (sx * 0.9, wy, 0.33)], 0.04, AL, res=2))
            hi.append(EK.rounded_box('fender', (0.32, 0.62, 0.06), 0.03, 0.04, [COR], loc=(sx * 0.98, wy, 0.7), rot=(0, sx * -8, 0), seed=10 + k))
    kit.to_mesh_all()
    decim = [(r'^chassis$', 120), (r'^skirt$', 90), (r'^cab$', 300), (r'^cabring$', 80), (r'^rsolar', 12), (r'^rmast$', 1.0), (r'^rflag$', 1.0), (r'^rdish$', 50),
             (r'^rdmast$', 1.0), (r'^rhead_', 30), (r'^bumper$', 24), (r'^rbox$', 24), (r'^rbox_', 10), (r'^wheel$', 220), (r'^wheel_side$', 16), (r'^wheel_hub$', 24),
             (r'^arm$', 20), (r'^fender$', 16), (r'^rvdust$', 1.0)]
    weights = [(r'^(chassis|cab|rhead_)', 1.4), (r'^wheel', 0.8), (r'^rvdust$', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=1024, budget=2500, ao_dist=0.3, ds_low=True, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_rocket

def build_rocket():
    hi = []
    BODY = m_panels('rkbody', UK.CREAM, mer=6, ring=1.2, var=0.04)
    COR = UK.m_paint('rkcoral', UK.CORAL, chips=0.3, dust=0.3, seed=1.0); TEA = UK.m_paint('rkteal', UK.TEAL, chips=0.3, dust=0.3, seed=2.0)
    GUN = UK._cached('gunm', lambda: UK.m_metal('gunm', UK.GUN, dust=0.4)); AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3))
    PAD = UK.m_paint('pad', '#8f8aa3', chips=0.3, dust=0.6, grime=0.5, seed=3.0)
    # rampa: sekizgen platform + uyarı halkası + cıvatalar
    hi.append(cyl('pad', (0, 0, 0.3), 3.2, 0.6, PAD, verts=8, bevel=0.06))
    hi.append(cyl('padring', (0, 0, 0.61), 2.2, 0.03, UK.m_paint('padr', UK.SUN, chips=0.4, dust=0.5, seed=4.0), verts=8, bevel=0.0))
    hi.append(cyl('padhole', (0, 0, 0.625), 1.4, 0.03, GUN, verts=24, bevel=0.0))
    for k in range(16):
        a = k / 16 * TAU; hi.append(UK.bolt((math.cos(a) * 2.8, math.sin(a) * 2.8, 0.6), (0, 0, 1), 0.06))
    # roket: gövde (lathe), burun, bant, lomboz, kanatçıklar, motor çanı
    z0 = 1.1
    prof = [(0.0, 0.0), (0.55, 0.0), (0.82, 0.4), (0.9, 1.2), (0.92, 2.6), (0.88, 4.0), (0.78, 5.0)]
    body = EK.lathe_grid('rkbody', prof + [(0.0, 5.0)], 32, [BODY], loc=(0, 0, z0), uv=False); hi.append(body)
    nose = EK.lathe_grid('rknose', [(0.0, 0.0), (0.78, 0.0), (0.7, 0.8), (0.48, 1.6), (0.2, 2.15), (0.0, 2.3)], 32, [COR], loc=(0, 0, z0 + 5.0), uv=False); hi.append(nose)
    hi.append(cyl('rkband', (0, 0, z0 + 3.2), 0.94, 0.45, TEA, verts=32, bevel=0.02))
    hi.append(blob('rktip', (0, 0, z0 + 7.32), (0.08, 0.08, 0.12), EK.m_gold('rkgold'), seg=12))
    hi += porthole('rkport', (0, -0.9, z0 + 4.2), (0, -1, 0), 0.38, glow='#8fe3f2', frame=UK.SUN)
    for k in range(4):
        a = k / 4 * TAU + math.pi / 4
        verts = [(0.0, 0.0), (1.05, -0.35), (1.15, 0.2), (0.0, 1.6)]
        fin = EK.mesh_obj('rkfin', [(0.6 + vx, -0.06, z0 + 0.2 + vz) for (vx, vz) in verts] + [(0.6 + vx, 0.06, z0 + 0.2 + vz) for (vx, vz) in verts],
                          [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], [COR], smooth=False)
        bm = bmesh.new(); bm.from_mesh(fin.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(fin.data); bm.free()
        bv = fin.modifiers.new('bv', 'BEVEL'); bv.width = 0.05; bv.segments = 3
        fin.rotation_euler = (0, 0, a); hi.append(fin)
    bell = EK.lathe_grid('rkbell', [(0.0, 0.0), (0.62, 0.0), (0.5, 0.35), (0.38, 0.6), (0.3, 0.6), (0.4, 0.35), (0.5, 0.05), (0.0, 0.05)][::-1][::-1], 24, [GUN], loc=(0, 0, z0 - 0.5), uv=False)
    hi.append(bell)
    # kafes kule (sağda): 4 ayak + çapraz bağlar + servis kolu + lamba
    TW = UK.m_paint('tower', UK.CORAL, chips=0.35, dust=0.4, seed=5.0)
    tx, ty, tw = 2.6, 0.6, 0.9
    for (dx, dy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        hi.append(EK.rounded_box('tleg', (0.12, 0.12, 8.6), 0.02, 0.1, [TW], loc=(tx + dx * tw / 2, ty + dy * tw / 2, 0.6 + 4.3), seed=20))
    for lv in range(9):
        z = 0.8 + lv * 0.95
        for (a, b2) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            pa = V((tx + a[0] * tw / 2, ty + a[1] * tw / 2, z)); pb = V((tx + b2[0] * tw / 2, ty + b2[1] * tw / 2, z + 0.95))
            hi.append(UK.cable('tbrace', [tuple(pa), tuple((pa + pb) / 2), tuple(pb)], 0.03, TW, res=1))
            pc = V((tx + b2[0] * tw / 2, ty + b2[1] * tw / 2, z))
            hi.append(UK.cable('tring', [tuple(pa), tuple((pa + pc) / 2), tuple(pc)], 0.03, TW, res=1))
    hi.append(EK.rounded_box('tarm', (1.6, 0.4, 0.12), 0.03, 0.05, [UK.m_paint('tarmp', UK.SUN, chips=0.35, dust=0.4, seed=6.0)], loc=(tx - 1.15, ty - 0.2, z0 + 4.4), seed=21))
    hi.append(EK.rounded_box('ttop', (1.1, 1.1, 0.12), 0.03, 0.05, [TW], loc=(tx, ty, 9.25), seed=22))
    hi += UK.lamp('tlamp', (tx, ty, 9.31), 0.16, UK.CORAL, cage=True, base_h=0.07)
    kit.to_mesh_all()
    decim = [(r'^pad$', 60), (r'^padring$', 40), (r'^padhole$', 40), (r'^rkbody$', 300), (r'^rknose$', 200), (r'^rkband$', 70), (r'^rktip$', 30),
             (r'^rkport_frame$', 50), (r'^rkport_glass$', 30), (r'^rkfin$', 60), (r'^rkbell$', 100), (r'^tleg$', 12), (r'^tbrace$', 12), (r'^tring$', 12),
             (r'^tarm$', 16), (r'^ttop$', 16), (r'^tlamp_', 30), (r'^rkdust$', 1.0)]
    weights = [(r'^(rkbody|rknose|rkband|rkport)', 1.4), (r'^(tleg|tbrace|tring)$', 0.5), (r'^rkdust$', 0.3), (r'^pad', 0.7)]
    return hi, None, dict(decim=decim, weights=weights, tex=1024, budget=3000, ao_dist=0.6, exclude=[r'^(bolt|rivet)$'])


# ================================================================== rs_ridge (uzak sırt)

def m_far(name):
    """Uzak arazi: açık, mavimsi lavanta (hava perspektifi yok ama derinlik için daha açık/soğuk), tepelerde açık, yamaçta mor."""
    def b(nt, bsdf):
        G = EK.EG(nt); cw = G.coords()
        x, y, z = G.sep(G.pos())
        col = G.mix(G.rng(z, 0.0, 30.0), '#8f93b6', '#c6c6dc')
        col = G.mix(G.rng(G.noise4(cw, 0.05, 3), 0.35, 0.7, 0, 0.35), col, '#9a8fbf')
        col = G.mix(G.rng(G.nz(), 0.5, 0.95, 0, 0.35), col, '#dcdbea')
        col = G.mix(G.rng(G.ao(4.0), 0.85, 0.35, 0, 0.35), col, '#6f6f98')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def build_ridge():
    R = random.Random(4)
    def hgt(X, Y):
        a = np.abs(X)
        base = 35.0 * np.exp(-((Y - 2.0) / 9.0) ** 2)
        peaks = np.zeros_like(X)
        for k in range(14):
            cx = R2[k][0]; w = R2[k][1]; hh = R2[k][2]
            peaks += hh * np.exp(-((X - cx) / w) ** 2 - ((Y - R2[k][3]) / 7.0) ** 2)
        jag = 3.0 * np.sin(X / 3.1 + 0.4) * np.sin(X / 5.3) + 2.0 * np.sin(X / 1.7 + 1.1)
        ridge = (base * (0.45 + 0.3 * np.cos(X / 23.0 + 0.7) + 0.25 * np.cos(X / 8.0 + 2.0)) + peaks + jag * smoothstep(-6, 4, Y) * smoothstep(12, 4, Y))
        ridge *= smoothstep(110.0, 85.0, a) * smoothstep(-20.0, -8.0, Y) * smoothstep(20.0, 10.0, Y)
        ter = np.round(ridge / 3.5) * 3.5
        return (0.75 * ridge + 0.25 * ter) * 0.74                      # tepe ≈ 35 m
    R2 = [(R.uniform(-100, 100), R.uniform(3, 14), R.uniform(3, 16), R.uniform(-4, 6)) for _ in range(14)]
    xs = np.linspace(-110, 110, 441); ys = np.linspace(-20, 20, 81); X, Y = np.meshgrid(xs, ys)
    Z = hgt(X, Y)
    hi = [EK.grid_obj('ridge', np.stack([X, Y, Z], -1), None, [m_far('ridgem')])]
    xl = np.linspace(-110, 110, 56); yl = np.linspace(-20, 20, 9); XL, YL = np.meshgrid(xl, yl)
    lo = [EK.tag_uvw(EK.grid_obj('ridge_lo', np.stack([XL, YL, hgt(XL, YL)], -1), None, []), 1.0)]
    return hi, lo, dict(cull=False, tex=1024, ao_dist=6.0, ao_strength=0.4, cage=1.5, ray=5.0)


# ================================================================== rs_earth (orijin merkez)

def m_earth(name):
    """Stilize Dünya: derinden sığa mavi okyanus, yeşil-aşı uydurma kıtalar (gerçek harita değil), kutup buzu, beyaz bulut girdapları."""
    def b(nt, bsdf):
        G = EK.EG(nt); o = G.obj(); x, y, z = G.sep(o)
        ocean = G.mix(G.rng(G.noise(o, 0.07, 2), 0.3, 0.7), '#1d58b0', '#3a8ddc')
        land = G.noise(G.mapping(o, (1.0, 1.0, 1.0)), 0.075, 3, 0.5)
        landm = G.rng(land, 0.52, 0.56)
        shore = G.math('MULTIPLY', G.rng(land, 0.47, 0.52), G.rng(land, 0.56, 0.52))
        lc = G.mix(G.rng(G.noise(o, 0.25, 3), 0.35, 0.7), '#4f9a4a', '#c9a45a')
        col = G.mix(G.math('MULTIPLY', shore, 0.6), ocean, '#7fd0ee')
        col = G.mix(landm, col, lc)
        polar = G.rng(G.math('ABSOLUTE', z), 15.0, 18.0)
        col = G.mix(polar, col, '#f2f6fb')
        sw = G.n.new('ShaderNodeTexNoise'); sw.noise_dimensions = '3D'; sw.inputs['Scale'].default_value = 0.055; sw.inputs['Detail'].default_value = 2
        sw.inputs['Distortion'].default_value = 5.0; G.l.new(o, sw.inputs['Vector'])
        cloud = G.rng(sw.outputs['Fac'], 0.6, 0.68)
        col = G.mix(G.math('MULTIPLY', cloud, 0.92), col, '#ffffff')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def build_earth():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=20.0, location=(0, 0, 0))
    hi = bpy.context.object; hi.name = 'earth'; hi.data.materials.append(m_earth('earthm')); EK.A.smooth(hi)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=20.0, location=(0, 0, 0))
    lo = bpy.context.object; lo.name = 'earth_lo'; EK.A.smooth(lo)
    for l in list(lo.data.uv_layers): lo.data.uv_layers.remove(l)
    # yalnız ön yarıküre ayrıntılı: arka yüzlere az doku
    EK.tag_uvw(lo, 1.0)
    bm = bmesh.new(); bm.from_mesh(lo.data); lay = bm.faces.layers.float.get('uvw'); bm.normal_update()
    for f in bm.faces: f[lay] = 1.0 if f.normal.y < 0.2 else 0.25
    bm.to_mesh(lo.data); bm.free()
    return [hi], [lo], dict(cull=False, tex=512, ao_dist=0.1, ao_strength=0.0, cage=0.3, ray=0.8)


# ================================================================== rs_planet (orijin merkez; küçük halkalı gezegen)

def m_bands(name):
    """Gezegen bantları (nesne z'si, gürültüyle dalgalı): mercan, kum, lavanta, krem; ince koyu ayrım çizgileri; bir girdap lekesi."""
    def b(nt, bsdf):
        G = EK.EG(nt); o = G.obj(); x, y, z = G.sep(o)
        zz = G.math('ADD', z, G.math('MULTIPLY', G.noise(o, 0.12, 3), 2.2))
        r = EK.ramp(nt, [(0.0, '#e07a5f'), (0.2, '#f1c27d'), (0.38, '#b39ddb'), (0.55, '#f6e3c3'), (0.72, '#e8936a'), (0.88, '#9e8bd0'), (1.0, '#f1c27d')])
        G.l.new(G.math('FRACT', G.math('DIVIDE', G.math('ADD', zz, 12.0), 7.5)), r.inputs['Fac'])
        col = r.outputs[0]
        col = G.mix(G.rng(G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', zz, 2.6))), 0.06, 0.0, 0, 0.35), col, '#6b4f7a')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def m_ring(name):
    def b(nt, bsdf):
        G = EK.EG(nt); o = G.obj(); x, y, z = G.sep(o)
        rr = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', x, x), G.math('MULTIPLY', y, y)))
        r = EK.ramp(nt, [(0.0, '#d9c7a3'), (0.25, '#f2e2c0'), (0.45, '#b9a6d9'), (0.6, '#e9d2a8'), (0.8, '#c8b6e2'), (1.0, '#efe0c4')])
        G.l.new(G.rng(rr, 16.0, 27.0), r.inputs['Fac'])
        col = G.mix(G.rng(G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', rr, 5.0))), 0.1, 0.0, 0, 0.4), r.outputs[0], '#8f7fb0')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def build_planet():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=12.0, location=(0, 0, 0))
    hi = bpy.context.object; hi.name = 'planet'; hi.data.materials.append(m_bands('pbands')); EK.A.smooth(hi)
    def annulus(name, r0, r1, n, rows, mats):
        th = np.linspace(0, TAU, n + 1); rs = np.linspace(r0, r1, rows)
        TH, RR = np.meshgrid(th, rs)
        o = EK.grid_obj(name, np.stack([RR * np.cos(TH), RR * np.sin(TH), np.zeros_like(TH)], -1), None, mats); EK.weld(o)
        o.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(o.data.polygons))
        o.rotation_euler = (math.radians(68), math.radians(-14), 0)
        return o
    ring = annulus('ring', 16.0, 27.0, 128, 12, [m_ring('pring')])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=12.0, location=(0, 0, 0))
    lo = bpy.context.object; lo.name = 'planet_lo'; EK.A.smooth(lo)
    for l in list(lo.data.uv_layers): lo.data.uv_layers.remove(l)
    lr = annulus('ring_lo', 16.0, 27.0, 48, 3, [])
    return [hi, ring], [EK.tag_uvw(lo, 1.0), EK.tag_uvw(lr, 0.8)], dict(cull=False, tex=1024, ao_dist=0.5, ao_strength=0.2, cage=0.25, ray=0.6, ds_low=True)


BUILD = {'rs_planet': build_planet, 'rs_dome': build_dome, 'rs_rocks': build_rocks, 'rs_crystals': build_crystals, 'rs_pennant': build_pennant, 'rs_cargo': build_cargo,
         'rs_dish': build_dish, 'rs_rover': build_rover, 'rs_rocket': build_rocket, 'rs_ridge': build_ridge, 'rs_earth': build_earth}
