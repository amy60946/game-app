# Masa oyunları, ceviz oyunu ve festival için 3B görünümlü arayüz görselleri (kredisiz, prosedürel Blender).
# Not: Ceviz Yakala'nın sepeti, arka planı ve ceviz simgeleri artık art/scripts/coconut_scene.py'den (basket burada eski sürüm).
# Kullanım: python -I ui_games.py -- çıktı_klasörü [yalnız_bu_ad ...]
# Katmanlı kart: card_body (beyaz kenar), card_inner (gri → oyunda renge boyanır), card_oval (beyaz eğik oval), card_back.
# Domino: domino_tile (fildişi taş, ortada çizgi), domino_pip (gömük nokta). Kule: block_wood. Ceviz: basket.
# Oyun seçimi: thumb_cards, thumb_domino, thumb_tower, thumb_coconut. Festival: lantern_off, lantern_on (beyaz; oyunda boyanır).
import bpy, math, sys, mathutils
args = sys.argv[sys.argv.index('--') + 1:]
OUT = args[0]; ONLY = set(args[1:])

def reset(w, h, samples=48):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new('w'); sc.world = wd; wd.use_nodes = True
    wd.node_tree.nodes['Background'].inputs['Color'].default_value = (0.78, 0.82, 0.9, 1)
    wd.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
    sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(8)
    so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(40), math.radians(-28), math.radians(-25))
    return sc

def cam(sc, scale, loc=(0, -10, 0), rot=(90, 0, 0), persp=None):
    c = bpy.data.cameras.new('c')
    if persp: c.type = 'PERSP'; c.lens = persp
    else: c.type = 'ORTHO'; c.ortho_scale = scale
    o = bpy.data.objects.new('c', c); sc.collection.objects.link(o); sc.camera = o
    o.location = loc; o.rotation_euler = tuple(math.radians(r) for r in rot)
    return o

def aim(camobj, target):
    d = mathutils.Vector(target) - camobj.location
    camobj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def mat(name, rgb, rough=0.4, metal=0.0, emit=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1); b.inputs['Emission Strength'].default_value = emit
    return m

sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', 'code3d'))
import assets_v3 as A3                                     # ortak düğüm yardımcıları (_G): kodla 3B tasarım diliyle aynı ahşap

def _hex(rgb): return '#%02x%02x%02x' % tuple(int(max(0, min(1, c)) ** (1 / 2.2) * 255) for c in rgb)

def wood(name, base=(0.78, 0.55, 0.3), dark=(0.55, 0.34, 0.16)):
    """Ahşap (kodla 3B tasarım dili): boyuna yıllık halka bantları ve lifler, düğüm, ince boyuna çatlak, çizik,
    güneşte solma, kenarlarda aşınma (açık); hafif kabartı."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']; b.inputs['Roughness'].default_value = 0.6
    G = A3._G(nt); o = G.obj()
    wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
    wv.inputs['Scale'].default_value = 1.3; wv.inputs['Distortion'].default_value = 7; wv.inputs['Detail'].default_value = 3
    l.new(G.mapping(o, (0.35, 6.0, 6.0)), wv.inputs['Vector'])
    col = G.mix(G.rng(wv.outputs['Fac'], 0.1, 0.9), _hex(dark), _hex(base))
    fib = G.noise(G.mapping(o, (0.6, 30.0, 30.0)), 3.0, 5)
    col = G.mix(0.3, col, G.noise(G.mapping(o, (0.6, 30.0, 30.0)), 3.0, 5, out='Color'), 'OVERLAY')
    col = G.mix(G.rng(G.vor(G.mapping(o, (0.8, 2.5, 2.5)), 1.2), 0.07, 0.0, 0, 0.7), col, _hex(tuple(c * 0.55 for c in dark)))
    crack = G.math('MULTIPLY', G.rng(G.vor(G.mapping(o, (0.25, 6.0, 6.0)), 2.0, 'DISTANCE_TO_EDGE'), 0.03, 0.0, 0, 1), G.rng(G.noise(o, 2.2), 0.52, 0.62))
    col = G.mix(G.math('MULTIPLY', crack, 0.7), col, '#3a2414')
    col = G.mix(G.rng(G.noise(o, 1.2, 5), 0.58, 0.76, 0, 0.18), col, '#a59d90')
    sc = G.vor(G.mapping(o, (6, 2, 6)), 3.0, 'DISTANCE_TO_EDGE')
    col = G.mix(G.math('MULTIPLY', G.math('MULTIPLY', G.rng(sc, 0.012, 0.0, 0, 1), G.rng(G.noise(o, 4.0), 0.55, 0.62)), 0.3), col, '#e3cfaa')
    col = G.mix(G.math('MULTIPLY', G.edges(0.53, 0.62), 0.35), col, '#f0dcb8')
    l.new(col, b.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.18
    l.new(G.math('ADD', fib, G.math('MULTIPLY', crack, -0.8)), bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def wicker(name='wicker'):
    """Hasır örgü: yatay ve dikey şeritlerin altlı-üstlü dokuması (dama düzeni), şerit kenarlarında koyu çizgi, kabartı."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']; b.inputs['Roughness'].default_value = 0.7
    G = A3._G(nt); o = G.obj()
    sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
    ang = G.math('ARCTAN2', sp.outputs['Y'], sp.outputs['X'])
    u = G.math('MULTIPLY', ang, 30.0); v = G.math('MULTIPLY', sp.outputs['Z'], 26.0)
    cu = G.math('SINE', u); cv = G.math('SINE', v)
    weave = G.math('MULTIPLY', cu, cv)                       # >0: yatay şerit üstte, <0: dikey
    lineu = G.math('ABSOLUTE', G.math('COSINE', u)); linev = G.math('ABSOLUTE', G.math('COSINE', v))
    edge = G.math('MAXIMUM', G.rng(linev, 0.92, 1.0), G.rng(lineu, 0.92, 1.0))
    col = G.mix(G.rng(weave, -0.2, 0.2), '#b0782f', '#e2b066')
    col = G.mix(0.25, col, G.noise(G.mapping(o, (12, 12, 40)), 2.0, 4, out='Color'), 'OVERLAY')
    col = G.mix(G.math('MULTIPLY', edge, 0.55), col, '#5e3a16')
    l.new(col, b.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.5
    l.new(G.math('ABSOLUTE', weave), bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def coco_mat(name='coco'):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']; b.inputs['Roughness'].default_value = 0.9
    G = A3._G(nt); o = G.obj()
    fib = G.noise(G.mapping(o, (4, 4, 40)), 1.5, 6)
    col = G.mix(G.rng(fib, 0.3, 0.7), '#3a2410', '#8a6234')
    col = G.mix(G.rng(G.noise(o, 18, 4), 0.62, 0.72, 0, 0.5), col, '#c9a26a')
    l.new(col, b.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.45
    l.new(fib, bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def slab(w, h, d, r, m, loc=(0, 0, 0), name='slab', segs=6):
    """Köşeleri yuvarlak ince levha (kart, taş, blok). w x (derinlik d) x h; ön yüz -Y."""
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name; o.scale = (w / 2, d / 2, h / 2)
    bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = r; bv.segments = segs; bv.limit_method = 'NONE'
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o

def text(s, size, m, loc, rot=(90, 0, 0), extrude=0.02):
    bpy.ops.object.text_add(location=loc, rotation=tuple(math.radians(r) for r in rot))
    t = bpy.context.object; t.data.body = s; t.data.size = size; t.data.extrude = extrude
    t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'; t.data.materials.append(m)
    bpy.ops.object.convert(target='MESH'); return t

def render(sc, name, show=None):
    if ONLY and name not in ONLY: return
    if show is not None:
        for o in sc.objects:
            if o.type == 'MESH': o.hide_render = o.name not in show
    sc.render.filepath = f"{OUT}/{name}.png"; bpy.ops.render.render(write_still=True)

def want(*names): return not ONLY or any(n in ONLY for n in names)

# ---------------------------------------------------------------- kart katmanları (256 x 360)
if want('card_body', 'card_inner', 'card_oval', 'card_back'):
    sc = reset(256, 360); cam(sc, 3.6)
    W, H = 2.4, 3.4
    slab(W, H, 0.12, 0.24, mat('white', (0.95, 0.95, 0.93), 0.35, coat=0.6), name='body')
    slab(W - 0.28, H - 0.28, 0.12, 0.17, mat('inner', (0.86, 0.86, 0.86), 0.32, coat=0.6), loc=(0, -0.02, 0), name='inner')
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.0, depth=0.05, location=(0, -0.09, 0), rotation=(math.radians(90), 0, 0))
    ov = bpy.context.object; ov.name = 'oval'; ov.scale = (0.78, 1.18, 1); ov.rotation_euler[1] = math.radians(28)
    ov.data.materials.append(mat('ov', (0.97, 0.97, 0.96), 0.3, coat=0.5)); bpy.ops.object.shade_smooth()
    render(sc, 'card_body', {'body'}); render(sc, 'card_inner', {'inner'}); render(sc, 'card_oval', {'oval'})
    # arka yüz: lacivert, kırmızı eğik oval, ortada yıldız
    for o in list(sc.objects):
        if o.type == 'MESH': bpy.data.objects.remove(o)
    slab(W, H, 0.12, 0.24, mat('white2', (0.95, 0.95, 0.93), 0.35, coat=0.6), name='b')
    slab(W - 0.28, H - 0.28, 0.12, 0.17, mat('navy', (0.08, 0.1, 0.25), 0.3, coat=0.6), loc=(0, -0.02, 0), name='i')
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.0, depth=0.05, location=(0, -0.09, 0), rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.name = 'o'; o.scale = (0.78, 1.18, 1); o.rotation_euler[1] = math.radians(28)
    o.data.materials.append(mat('gold', (1.0, 0.7, 0.12), 0.3, coat=0.5)); bpy.ops.object.shade_smooth()
    t = text('P', 1.4, mat('pw', (0.98, 0.98, 0.98), 0.3), (0, -0.14, -0.08), extrude=0.04); t.name = 't'
    render(sc, 'card_back', None)

# ---------------------------------------------------------------- domino taşı (360 x 180) + nokta (64)
if want('domino_tile', 'domino_pip'):
    sc = reset(360, 180); cam(sc, 2.1)
    slab(2.0, 1.0, 0.3, 0.14, mat('ivory', (0.97, 0.94, 0.86), 0.3, coat=0.7), name='tile')
    bpy.ops.mesh.primitive_cube_add(location=(0, -0.16, 0)); g = bpy.context.object; g.name = 'groove'
    g.scale = (0.012, 0.02, 0.4); g.data.materials.append(mat('groove', (0.35, 0.3, 0.25), 0.6))
    render(sc, 'domino_tile', None)
    sc = reset(64, 64); cam(sc, 1.1)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(0, 0.2, 0)); p = bpy.context.object
    p.scale = (1, 0.4, 1); p.data.materials.append(mat('pip', (0.06, 0.05, 0.06), 0.25, coat=0.8)); bpy.ops.object.shade_smooth()
    render(sc, 'domino_pip', None)

# ---------------------------------------------------------------- Kule bloğu (512 x 128)
if want('block_wood'):
    sc = reset(512, 128); cam(sc, 4.1, loc=(0, -10, 0.02))
    slab(4.0, 0.95, 1.0, 0.07, wood('wood'), name='blk', segs=4)
    render(sc, 'block_wood', None)

# ---------------------------------------------------------------- sepet (512 x 320)
def basket(loc=(0, 0, 0), s=1.0):
    m = wicker()
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1.6 * s, depth=1.1 * s, location=loc)
    b = bpy.context.object; b.name = 'basket'
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
    for f in b.data.polygons: f.select = f.normal.z > 0.9                # üst kapak
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='FACE'); bpy.ops.object.mode_set(mode='OBJECT')
    bm = b.modifiers.new('s', 'SOLIDIFY'); bm.thickness = 0.12 * s
    b.data.materials.append(m); bpy.ops.object.shade_smooth()
    # örgü: yatay halkalar
    for i in range(5):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.62 * s, minor_radius=0.07 * s, location=(loc[0], loc[1], loc[2] - 0.45 * s + i * 0.23 * s))
        r = bpy.context.object; r.name = f'ring{i}'; r.data.materials.append(m); bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_torus_add(major_radius=1.65 * s, minor_radius=0.13 * s, location=(loc[0], loc[1], loc[2] + 0.55 * s))
    r = bpy.context.object; r.name = 'rim'; r.data.materials.append(m); bpy.ops.object.shade_smooth()

def coconut(loc, s=0.5, gold=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=s, location=loc)
    c = bpy.context.object; c.scale = (0.95, 0.95, 1.05)
    c.data.materials.append(mat('gc', (1.0, 0.72, 0.15), 0.35, metal=0.45) if gold else coco_mat())
    bpy.ops.object.shade_smooth(); return c

if 'basket' in ONLY:   # oyundaki sepet artık art/scripts/coconut_scene.py'den (24 Ekim 2026); bu eski sürüm yalnız adıyla istenirse
    sc = reset(512, 320); cam(sc, 4.0, loc=(0, -10, 2.2), rot=(78, 0, 0))
    basket()
    render(sc, 'basket', None)

# ---------------------------------------------------------------- oyun seçim görselleri (512 x 400, perspektif)
def card3d(color, num, loc, rot):
    W, H = 2.4, 3.4
    parent = bpy.data.objects.new('card', None); bpy.context.scene.collection.objects.link(parent)
    a = slab(W, H, 0.08, 0.24, mat('wb', (0.95, 0.95, 0.93), 0.35, coat=0.6))
    b = slab(W - 0.28, H - 0.28, 0.08, 0.17, mat('c' + num, color, 0.32, coat=0.6), loc=(0, -0.02, 0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=0.04, location=(0, -0.07, 0), rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.scale = (0.78, 1.18, 1); o.rotation_euler[1] = math.radians(28)
    o.data.materials.append(mat('ovw', (0.97, 0.97, 0.96), 0.3)); bpy.ops.object.shade_smooth()
    t = text(num, 1.5, mat('n' + num, color, 0.3), (0, -0.1, -0.05), extrude=0.03)
    for x in (a, b, o, t): x.parent = parent
    parent.location = loc; parent.rotation_euler = tuple(math.radians(r) for r in rot)
    return parent

def ground_shadow(z=-1.8, size=30):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z)); p = bpy.context.object
    p.is_shadow_catcher = True

if want('thumb_cards'):
    sc = reset(512, 400, 64); co = cam(sc, 0, loc=(0, -12, 1.6), persp=50); aim(co, (0, 0, -0.2))
    cols = [((0.8, 0.07, 0.05), '7'), ((1.0, 0.62, 0.0), '3'), ((0.03, 0.5, 0.12), '5'), ((0.02, 0.25, 0.8), '9')]
    for i, (c, n) in enumerate(cols):
        ang = (i - 1.5) * 18
        r = math.radians(ang)
        card3d(c, n, (math.sin(r) * 2.6, -i * 0.12, math.cos(r) * 2.6 - 2.9), (-8, ang, 0))   # alttan yelpaze
    ground_shadow(-2.6)
    render(sc, 'thumb_cards', None)

def domino3d(a, b, loc, rot):
    parent = bpy.data.objects.new('dom', None); bpy.context.scene.collection.objects.link(parent)
    t = slab(1.0, 2.0, 0.35, 0.12, mat('iv', (0.97, 0.94, 0.86), 0.3, coat=0.7))
    t.parent = parent
    pip = mat('pp', (0.05, 0.05, 0.06), 0.25)
    layout = {1: [(0, 0)], 2: [(-0.22, 0.22), (0.22, -0.22)], 3: [(-0.22, 0.22), (0, 0), (0.22, -0.22)],
              4: [(-0.22, 0.22), (0.22, 0.22), (-0.22, -0.22), (0.22, -0.22)], 5: [(-0.22, 0.22), (0.22, 0.22), (0, 0), (-0.22, -0.22), (0.22, -0.22)],
              6: [(-0.22, 0.25), (0.22, 0.25), (-0.22, 0), (0.22, 0), (-0.22, -0.25), (0.22, -0.25)]}
    for half, v in ((0.5, a), (-0.5, b)):
        for (x, z) in layout.get(v, []):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.09, location=(x, -0.17, half + z * 0.85))
            p = bpy.context.object; p.scale = (1, 0.35, 1); p.data.materials.append(pip); bpy.ops.object.shade_smooth(); p.parent = parent
    bpy.ops.mesh.primitive_cube_add(location=(0, -0.18, 0)); g = bpy.context.object; g.scale = (0.4, 0.01, 0.012)
    g.data.materials.append(mat('gr', (0.4, 0.35, 0.3), 0.6)); g.parent = parent
    parent.location = loc; parent.rotation_euler = tuple(math.radians(r) for r in rot)

if want('thumb_domino'):
    sc = reset(512, 400, 64); co = cam(sc, 0, loc=(1.5, -9.5, 2.6), persp=45); aim(co, (0, 0.6, -0.2))
    vals = [(6, 3), (3, 5), (5, 1), (1, 4), (4, 2)]
    for i, (a, b) in enumerate(vals):
        tilt = -28 if i == 0 else 0                                    # ilki devriliyor
        domino3d(a, b, (-3.0 + i * 1.5, i * 0.55, -1.0 + (0.15 if i == 0 else 0)), (tilt, 0, 18 - i * 6))
    ground_shadow(-2.0)
    render(sc, 'thumb_domino', None)

if want('thumb_tower'):
    sc = reset(512, 400, 64); co = cam(sc, 0, loc=(9.0, -13.0, 3.2), persp=34); aim(co, (0, 0, -0.5))
    w = wood('tw')
    for lvl in range(8):
        for k in range(3):
            off = (k - 1) * 1.02
            out = 0.9 if (lvl == 5 and k == 1) else 0.0
            if lvl % 2 == 0: slab(3.0, 0.62, 0.98, 0.05, w, loc=(out, off, -2.6 + lvl * 0.64), segs=3)
            else:
                o = slab(3.0, 0.62, 0.98, 0.05, w, loc=(off, -out, -2.6 + lvl * 0.64), segs=3); o.rotation_euler[2] = math.radians(90)
    ground_shadow(-2.95)
    render(sc, 'thumb_tower', None)

if want('thumb_coconut'):
    sc = reset(512, 400, 64); co = cam(sc, 0, loc=(0, -9.5, 3.0), persp=45); aim(co, (0, 0, -0.2))
    basket((0, 0, -1.4), 1.0)
    for i, (x, y, z) in enumerate([(-0.6, -0.3, -0.55), (0.55, -0.2, -0.5), (0.0, 0.3, -0.3), (-0.2, -0.6, -0.2)]):
        coconut((x, y, z), 0.55)
    coconut((0.9, -1.2, 1.6), 0.5, gold=True)                       # düşen altın ceviz
    coconut((-1.2, -0.8, 2.3), 0.5)
    ground_shadow(-1.95)
    render(sc, 'thumb_coconut', None)

# ---------------------------------------------------------------- festival feneri (256 x 320): kapalı ve yanık
def lantern(lit):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0)
    o = bpy.context.object; o.scale = (1.0, 1.0, 1.15); bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new('paper'); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links
    b = n['Principled BSDF']; b.inputs['Base Color'].default_value = (0.97, 0.95, 0.9, 1); b.inputs['Roughness'].default_value = 0.8
    # kâğıt kaburgaları: dikey çizgiler (wave)
    tc = n.new('ShaderNodeTexCoord'); wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 2.2
    wv.bands_direction = 'X'; l.new(tc.outputs['Object'], wv.inputs['Vector'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6
    l.new(wv.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    if lit:
        b.inputs['Base Color'].default_value = (1.0, 0.92, 0.8, 1)
        b.inputs['Emission Color'].default_value = (1.0, 0.72, 0.38, 1); b.inputs['Emission Strength'].default_value = 0.55
    o.data.materials.append(m)
    cap = mat('cap', (0.25, 0.2, 0.18), 0.5)
    for z in (1.08, -1.08):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.45, depth=0.16, location=(0, 0, z)); c = bpy.context.object; c.data.materials.append(cap)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.25, minor_radius=0.04, location=(0, 0, 1.3), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(cap)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.6, location=(0, 0, -1.45)); bpy.context.object.data.materials.append(mat('tassel', (0.9, 0.25, 0.2), 0.7))

for lit, name in ((False, 'lantern_off'), (True, 'lantern_on')):
    if not want(name): continue
    sc = reset(256, 320); cam(sc, 3.4, loc=(0, -10, 0.05))
    if not lit: sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
    lantern(lit)
    render(sc, name, None)
