# Ceviz Yakala mini oyununun görselleri (kredisiz, kodla 3B; Blender Cycles) — 24 Ekim 2026, kullanıcı:
# "Oyunun içindeki görsellere 3D izlenimi ver, detaylar daha belli olsun, ince detaylar ekle".
#   bg      → Resources/Games/coconut_bg.jpg (2048 x 1024): boyalı maket kumsal. Yumuşak güneş + gökyüzü dolgusu, turkuaz deniz
#             (sığdan derine renk, kıyı köpüğü, dalga çizgileri), kum (rüzgâr kırışıkları, ıslak kum, köpük izi, ayak izleri,
#             deniz kabukları, deniz yıldızı, çakıl, küçük yengeç), iki yanda gerçek 3B yapraklı palmiyeler ve sarkan cevizler,
#             uzakta adacık, birkaç pamuk bulut. Alt ~%25 (sepetin gezdiği yer) sakin kum; üst orta (cevizlerin düştüğü yer) açık.
#   basket  → Resources/Games/basket.png (512 x 320, şeffaf): çubuk + sarma hasır örgü (altlı üstlü), örgülü ağız, yumuşak temas gölgesi.
#   coconut → Resources/Icons/ui_coconut.png, ui_coconut_gold.png (256², şeffaf): lifli kabuk (gerçek lif telleri), bir uçta üç göz
#             ve dikişler, parlak vurgu + kenar ışığı; altın ceviz cilalı metal, çevresinde parıltılar. Küçükte de okunur.
# Palmiye, deniz yıldızı, yengeç, bulut ve kaya kodla 3B kitinden (art/code3d/v6: kit_v6, kit2_v6) — adanın diliyle aynı.
# Kullanım: python3.11 -I art/scripts/coconut_scene.py -- <çıktı_klasörü> [bg] [basket] [coconut] [--fast]
#   (oyuna: çıktı klasörü = Assets/_Pofi/Resources; bg → Games/, basket → Games/, coconut → Icons/ alt klasörlerine yazılır)
#   --fast: yarı çözünürlük + az örnek (taslak); SAMPLES=n örnek sayısını ezer. Süre (4 çekirdek): bg ~13 dk, sepet + cevizler ~3 dk.
import bpy, bmesh, math, os, random, sys
import numpy as np
from mathutils import Vector as V, noise as MN

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'code3d', 'v6'))
import kit_v6 as K
import kit2_v6 as K2
from kit_v6 import srgb

args = sys.argv[sys.argv.index('--') + 1:]
FAST = '--fast' in args
args = [a for a in args if a != '--fast']
OUT = args[0]
ONLY = set(args[1:]) or {'bg', 'basket', 'coconut'}


# ------------------------------------------------------------------ ortak

class G:
    """Düğüm kurmayı kısaltan yardımcı (malzeme ağacı içinde)."""
    def __init__(self, m):
        self.nt = m.node_tree; self.n = self.nt.nodes; self.l = self.nt.links
        self.b = self.n['Principled BSDF']

    def _in(self, sock, x):
        if isinstance(x, (int, float)): sock.default_value = x
        elif isinstance(x, str): sock.default_value = srgb(x) + (1,)
        elif isinstance(x, tuple): sock.default_value = x
        else: self.l.new(x, sock)

    def math(self, op, a, b=None, c=None, clamp=False):
        m = self.n.new('ShaderNodeMath'); m.operation = op; m.use_clamp = clamp
        for i, x in enumerate((a, b, c)):
            if x is not None: self._in(m.inputs[i], x)
        return m.outputs[0]

    def rng(self, x, f0, f1, t0=0.0, t1=1.0, smooth=True):
        r = self.n.new('ShaderNodeMapRange'); r.clamp = True
        if smooth: r.interpolation_type = 'SMOOTHSTEP'
        r.inputs['From Min'].default_value = f0; r.inputs['From Max'].default_value = f1
        r.inputs['To Min'].default_value = t0; r.inputs['To Max'].default_value = t1
        self.l.new(x, r.inputs['Value']); return r.outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        m = self.n.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = blend
        self._in(m.inputs['Factor'], fac); self._in(m.inputs[6], a); self._in(m.inputs[7], b)
        return m.outputs[2]

    def noise(self, vec, scale, detail=4, rough=0.5, out='Fac'):
        z = self.n.new('ShaderNodeTexNoise'); z.inputs['Scale'].default_value = scale; z.inputs['Detail'].default_value = detail
        z.inputs['Roughness'].default_value = rough; self.l.new(vec, z.inputs['Vector']); return z.outputs[out]

    def vor(self, vec, scale, feature='F1', out='Distance', rand=1.0):
        v = self.n.new('ShaderNodeTexVoronoi'); v.feature = feature; v.inputs['Scale'].default_value = scale
        v.inputs['Randomness'].default_value = rand; self.l.new(vec, v.inputs['Vector']); return v.outputs[out]

    def wave(self, vec, scale, dist=0.0, detail=0.0, direction='Y', profile='SIN'):
        w = self.n.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = direction; w.wave_profile = profile
        w.inputs['Scale'].default_value = scale; w.inputs['Distortion'].default_value = dist; w.inputs['Detail'].default_value = detail
        self.l.new(vec, w.inputs['Vector']); return w.outputs['Fac']

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
        m = self.n.new('ShaderNodeMapping'); m.inputs['Scale'].default_value = scale; m.inputs['Location'].default_value = loc
        m.inputs['Rotation'].default_value = rot; self.l.new(vec, m.inputs['Vector']); return m.outputs[0]

    def obj(self): return self.n.new('ShaderNodeTexCoord').outputs['Object']
    def pos(self): return self.n.new('ShaderNodeNewGeometry').outputs['Position']

    def xyz(self, vec):
        s = self.n.new('ShaderNodeSeparateXYZ'); self.l.new(vec, s.inputs[0]); return s.outputs

    def attr(self, name):
        a = self.n.new('ShaderNodeAttribute'); a.attribute_name = name; return a.outputs['Fac']

    def bump(self, h, strength, dist=0.02, normal=None):
        b = self.n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
        self.l.new(h, b.inputs['Height'])
        if normal is not None: self.l.new(normal, b.inputs['Normal'])
        return b.outputs['Normal']

    def ramp(self, x, stops):
        r = self.n.new('ShaderNodeValToRGB'); el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], srgb(stops[0][1]) + (1,)
        el[1].position, el[1].color = stops[-1][0], srgb(stops[-1][1]) + (1,)
        for p, c in stops[1:-1]:
            e = el.new(p); e.color = srgb(c) + (1,)
        self.l.new(x, r.inputs['Fac']); return r.outputs['Color']

    def out(self, col=None, rough=None, normal=None, metal=None, coat=None):
        if col is not None: self._in(self.b.inputs['Base Color'], col)
        if rough is not None: self._in(self.b.inputs['Roughness'], rough)
        if normal is not None: self.l.new(normal, self.b.inputs['Normal'])
        if metal is not None: self._in(self.b.inputs['Metallic'], metal)
        if coat is not None: self._in(self.b.inputs['Coat Weight'], coat)


def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; return m, G(m)


def flat_mat(name, hexc, rough=0.6, coat=0.0, spec=0.5):
    m, g = new_mat(name); g.out(hexc, rough, coat=coat if coat else None)
    g.b.inputs['Specular IOR Level'].default_value = spec
    return m


def reset(w, h, samples, transparent=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = int(os.environ.get('SAMPLES', max(8, samples // 4) if FAST else samples))
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 50 if FAST else 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    return sc


def save(sc, path, fmt='PNG', quality=90):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s = sc.render.image_settings; s.file_format = fmt
    if fmt == 'JPEG': s.quality = quality; s.color_mode = 'RGB'
    else: s.color_mode = 'RGBA' if sc.render.film_transparent else 'RGB'; s.compression = 100
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    print('yazıldı', path, flush=True)


def post_alpha(path, fn):
    """Kaydedilen PNG'nin saydamlığını numpy ile düzenler: fn(alfa, x01, y01_alttan) → yeni alfa."""
    img = bpy.data.images.load(path); w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); xx = (xx + 0.5) / w; yy = (yy + 0.5) / h
    px[..., 3] = fn(px[..., 3], xx, yy)
    img.pixels.foreach_set(px.ravel()); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


def sun(sc, direction, energy, angle=4.0, color=(1.0, 0.95, 0.86)):
    l = bpy.data.lights.new('sun', 'SUN'); l.energy = energy; l.angle = math.radians(angle); l.color = color
    o = bpy.data.objects.new('sun', l); sc.collection.objects.link(o)
    o.rotation_euler = V(direction).normalized().to_track_quat('-Z', 'Y').to_euler()
    return o


def area_light(sc, loc, target, energy, size, color=(1, 1, 1)):
    l = bpy.data.lights.new('area', 'AREA'); l.energy = energy; l.size = size; l.color = color; l.shape = 'DISK'   # yuvarlak parlama
    o = bpy.data.objects.new('area', l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (V(target) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def mesh_from_grid(name, X, Y, Z, mat, attrs=None):
    """Düzenli ızgaradan ağ (numpy): dörtgen yüzler, yumuşak gölge; attrs = {ad: (ny, nx) dizi} köşe öznitelikleri."""
    ny, nx = X.shape
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], -1).astype(np.float32)
    idx = np.arange(nx * ny, dtype=np.int32).reshape(ny, nx)
    quads = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], -1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel())
    me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    for k, a in (attrs or {}).items():
        at = me.attributes.new(k, 'FLOAT', 'POINT'); at.data.foreach_set('value', a.astype(np.float32).ravel())
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def group(name, objs):
    root = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None: o.parent = root
    return root


def new_objects(before):
    return [o for o in bpy.data.objects if o not in before]


# ------------------------------------------------------------------ kumsal sahnesi (arka plan)

SHORE0 = 23.0                      # kıyı çizgisi (y): kum z = 0'da denize girer
SLOPE = 0.055                      # kumun denize eğimi


def shore_y(x):
    return SHORE0 + 0.9 * np.sin(0.19 * x + 0.7) + 0.4 * np.sin(0.47 * x + 2.1)


def shore_d_node(g):
    """Kıyıya uzaklık (m, deniz yönü +): y − kıyı(x); dünya konumundan, gölgelendiricide."""
    p = g.xyz(g.pos())
    s1 = g.math('SINE', g.math('MULTIPLY_ADD', p['X'], 0.19, 0.7))
    s2 = g.math('SINE', g.math('MULTIPLY_ADD', p['X'], 0.47, 2.1))
    sh = g.math('ADD', g.math('MULTIPLY_ADD', s1, 0.9, SHORE0), g.math('MULTIPLY', s2, 0.4))
    return g.math('SUBTRACT', p['Y'], sh), p


def sky_world(sc):
    """Kamera gökyüzünü (ufukta açık camgöbeği → tepede canlı mavi) görür; sahne ise yumuşak, hafif mavi bir dolgu ışığı alır
    (gölgeler siyah değil, mavimsi; boyalı maket hissi)."""
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    n = w.node_tree.nodes; l = w.node_tree.links
    bg = n['Background']; out = n['World Output']
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs[0])
    rp = n.new('ShaderNodeValToRGB'); el = rp.color_ramp.elements
    el[0].position = 0.0; el[0].color = srgb('#e8f6ff') + (1,)
    el[1].position = 0.42; el[1].color = srgb('#3f9be8') + (1,)
    e = el.new(0.06); e.color = srgb('#c4ebff') + (1,)
    e = el.new(0.2); e.color = srgb('#7cc6f6') + (1,)
    l.new(sep.outputs['Z'], rp.inputs['Fac'])
    l.new(rp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    amb = n.new('ShaderNodeBackground'); amb.inputs['Color'].default_value = srgb('#bfd9f2') + (1,); amb.inputs['Strength'].default_value = 0.75
    lp = n.new('ShaderNodeLightPath'); mx = n.new('ShaderNodeMixShader')
    l.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); l.new(amb.outputs[0], mx.inputs[1]); l.new(bg.outputs[0], mx.inputs[2])
    l.new(mx.outputs[0], out.inputs['Surface'])


def sand_mat():
    """Kum: kuru (sıcak bej, ton oynaması, tane pırıltısı, çakıl beneği), rüzgâr kırışıkları (kabartı), kıyıya yakın ıslak kum
    (koyu, düzgün, hafif yansıma), son dalganın bıraktığı dantel köpük izi; ayak izlerinin içi biraz koyu ('fp' özniteliği)."""
    m, g = new_mat('sand')
    d, p = shore_d_node(g)
    o = g.pos()
    # kuru kum renk: iri lekeler + ince tane
    big = g.noise(g.mapping(o, (0.35, 0.5, 0.35)), 2.0, 3)
    col = g.ramp(big, [(0.3, '#ebc584'), (0.55, '#f3d398'), (0.75, '#f8dfac')])
    grain = g.noise(o, 140.0, 2)
    col = g.mix(g.rng(grain, 0.35, 0.75, 0.0, 0.18), col, '#d8b276')
    speck = g.vor(g.mapping(o, (1, 1, 1)), 70.0, 'F1', 'Distance')
    col = g.mix(g.math('MULTIPLY', g.rng(speck, 0.08, 0.0, 0, 1), g.rng(g.noise(o, 9.0), 0.55, 0.65)), col, '#fff6dc')   # parlak tane
    col = g.mix(g.math('MULTIPLY', g.rng(speck, 0.05, 0.0, 0, 0.8), g.rng(g.noise(o, 6.0), 0.6, 0.7)), col, '#a98a63')     # koyu tane / çakıl tozu
    # rüzgâr kırışıkları: kıyıya paralel dalgalı bantlar, yer yer kırık
    rip = g.wave(g.mapping(o, (1.0, 1.0, 1.0), rot=(0, 0, 0.12)), 2.6, dist=5.0, detail=2.0, direction='Y')
    ripm = g.math('MULTIPLY', rip, g.rng(g.noise(o, 0.6, 2), 0.35, 0.6, 0.25, 1.0))
    col = g.mix(g.math('MULTIPLY', g.rng(ripm, 0.6, 0.95, 0, 1), 0.1), col, '#fff0cc')
    # ıslak kum (kıyıya 0..2,4 m)
    wet = g.rng(d, -2.4, -0.4)
    edge = g.math('MULTIPLY', g.noise(g.mapping(o, (3, 1, 3)), 1.5, 3), 0.8)
    wet = g.rng(g.math('ADD', d, g.math('SUBTRACT', edge, 0.4)), -4.2, -0.8)
    col = g.mix(g.math('MULTIPLY', wet, 0.75), col, '#c99f69')
    col = g.mix(g.math('MULTIPLY', g.rng(d, -0.9, -0.1), 0.5), col, '#b78f5f')     # su kenarı en koyu
    # son dalganın izi: ıslak sınırda ince, dantel köpük çizgisi
    lace = g.vor(g.mapping(o, (2.0, 4.0, 2.0)), 2.2, 'DISTANCE_TO_EDGE')
    lacem = g.rng(lace, 0.06, 0.0, 0, 1)
    line = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('ADD', g.math('ADD', d, 3.2), g.math('MULTIPLY', edge, 0.8))), 0.45, 0.0), lacem)
    col = g.mix(g.math('MULTIPLY', line, 0.75), col, '#fffaf0')
    # ayak izlerinin içi: hafif koyu, sıkışmış kum
    col = g.mix(g.math('MULTIPLY', g.attr('fp'), 0.55), col, '#c09460')
    rough = g.math('SUBTRACT', 0.95, g.math('MULTIPLY', wet, 0.6))
    nrm = g.bump(g.math('ADD', g.math('MULTIPLY', ripm, 0.6), g.math('MULTIPLY', grain, 0.25)), 0.22, 0.03)
    g.out(col, rough, nrm)
    g.b.inputs['Specular IOR Level'].default_value = 0.35
    return m


def sea_mat():
    """Deniz: kıyıdan uzaklığa göre sığ kum-turkuaz → turkuaz → derin mavi, ufukta hafif pus; köpük: kıyı teması (dantel),
    açıkta 3 kırılan dalga çizgisi (gürültüyle kıvrık, yer yer kopuk), ufka doğru söner. Yansıma Fresnel'siz ve hafif
    (yatık bakışta deniz gri aynaya dönmesin), ince kabartı = pırıltı; az miktar yayma = canlı ama parlamayan renk."""
    m, g = new_mat('sea')
    d, p = shore_d_node(g)
    o = g.pos()
    wig = g.math('MULTIPLY', g.math('SUBTRACT', g.noise(g.mapping(o, (0.08, 0.25, 0.08)), 1.0, 2), 0.5), 3.0)
    dw = g.math('ADD', d, wig)
    col = g.ramp(g.math('DIVIDE', d, 160.0), [(0.0, '#c8f4dc'), (0.012, '#86e8d6'), (0.035, '#3fd0d8'), (0.1, '#18b1df'),
                                              (0.3, '#118bd9'), (1.0, '#1b74cc')])
    col = g.mix(g.math('MULTIPLY', g.rng(g.noise(g.mapping(o, (0.3, 0.9, 0.3)), 2.5, 3), 0.42, 0.72), 0.14), col, '#e2fff8')   # akıntı lekeleri
    col = g.mix(g.rng(d, 300.0, 2500.0, 0.0, 0.45), col, '#9fd6f2')                                                          # ufuk pusu
    lace = g.rng(g.vor(g.mapping(o, (0.9, 2.0, 0.9)), 1.4, 'DISTANCE_TO_EDGE'), 0.1, 0.0)
    lace2 = g.rng(g.vor(g.mapping(o, (0.6, 1.3, 0.6)), 1.8, 'DISTANCE_TO_EDGE'), 0.07, 0.0)
    brk = g.rng(g.noise(g.mapping(o, (0.18, 0.45, 0.18)), 2.0, 3), 0.36, 0.52)          # dalga çizgisini koparır
    foam = g.math('MULTIPLY', g.rng(d, 3.6, 0.3), g.math('MAXIMUM', lace, g.rng(d, 1.4, 0.0)))   # kıyı teması
    for c, wdt, amt in ((4.5, 1.0, 0.95), (10.0, 1.5, 0.8), (18.0, 2.2, 0.6)):
        a = g.math('ABSOLUTE', g.math('SUBTRACT', dw, c))
        band = g.math('MULTIPLY', g.math('MULTIPLY', g.rng(a, wdt, 0.0), g.math('MAXIMUM', lace2, g.rng(a, wdt * 0.4, 0.0))), brk)
        foam = g.math('MAXIMUM', foam, g.math('MULTIPLY', band, amt))
        # dalga çizgisinin kıyı tarafında açık turkuaz yükselti (dalganın gövdesi)
        body = g.math('MULTIPLY', g.rng(g.math('SUBTRACT', dw, c), -wdt * 2.5, 0.0), g.rng(g.math('SUBTRACT', dw, c), 0.0, -wdt * 0.3))
        col = g.mix(g.math('MULTIPLY', body, 0.4 * amt), col, '#a4f4ea')
    foam = g.math('MINIMUM', foam, 1.0)
    col = g.mix(foam, col, '#fbfffe')
    nrm = g.bump(g.noise(g.mapping(o, (1.0, 2.2, 1.0)), 3.0, 6), 0.1, 0.05)
    g.out(col, g.math('MULTIPLY_ADD', foam, 0.6, 0.3), nrm)
    g.b.inputs['Specular IOR Level'].default_value = 0.0
    g.b.inputs['IOR'].default_value = 1.0
    g._in(g.b.inputs['Emission Color'], col); g.b.inputs['Emission Strength'].default_value = 0.22
    gl = g.n.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.1; g.l.new(nrm, gl.inputs['Normal'])
    mx = g.n.new('ShaderNodeMixShader')
    g._in(mx.inputs[0], g.math('MULTIPLY', g.math('SUBTRACT', 1.0, foam), 0.1))
    g.l.new(g.b.outputs[0], mx.inputs[1]); g.l.new(gl.outputs[0], mx.inputs[2])
    g.l.new(mx.outputs[0], g.n['Material Output'].inputs['Surface'])
    return m


def footprints(X, Y, steps):
    """Ayak izleri yükseklik farkı ve iç maskesi: her iz = topuk + taban + 5 parmak çukuru, kenarda hafif kabarık sırt."""
    dz = np.zeros_like(X); mask = np.zeros_like(X)
    for (cx, cy, ang, side, s) in steps:
        ca, sa = math.cos(ang), math.sin(ang)
        sel = (np.abs(X - cx) < 0.3 * s) & (np.abs(Y - cy) < 0.3 * s)
        if not sel.any(): continue
        lx = (X[sel] - cx) * ca + (Y[sel] - cy) * sa            # ileri
        ly = -(X[sel] - cx) * sa + (Y[sel] - cy) * ca           # yan
        dep = np.zeros_like(lx)
        for (fx, fy, rx, ry, dd) in ((-0.075, 0.0, 0.045, 0.038, 1.0), (0.025, 0.006 * side, 0.06, 0.044, 1.0),
                                     (0.1, 0.014 * side, 0.02, 0.018, 0.8), (0.112, -0.006 * side, 0.015, 0.013, 0.7),
                                     (0.112, -0.022 * side, 0.013, 0.011, 0.65), (0.105, -0.036 * side, 0.011, 0.01, 0.6),
                                     (0.094, -0.048 * side, 0.01, 0.009, 0.55)):
            r2 = ((lx - fx * s) / (rx * s)) ** 2 + ((ly - fy * s) / (ry * s)) ** 2
            dep = np.maximum(dep, dd * np.clip(1.0 - r2, 0, 1) ** 0.6)
        # kenar sırtı: çukurun hemen dışı
        rr2 = ((lx + 0.01 * s) / (0.15 * s)) ** 2 + (ly / (0.075 * s)) ** 2
        rim = np.exp(-((rr2 - 1.15) / 0.35) ** 2) * 0.35
        dz[sel] += -0.03 * s * dep + 0.008 * s * rim
        mask[sel] = np.maximum(mask[sel], np.clip(dep * 1.5, 0, 1))
    return dz, mask


def scallop(name, s, hexc, seed):
    """Tarak kabuğu: kubbe yelpaze, belirgin ışınsal kaburgalar (kenarı dalgalı), menteşede iki kulakçık; altı kapalı (kuma oturur).
    Renk: kaburga oluklarında koyu, kenara doğru açık eşmerkezli bantlar."""
    bm = bmesh.new(); nr, na = 14, 61
    A = math.radians(66); NR = 9                       # yarım açı, kaburga sayısı
    rows = []
    for i in range(nr + 1):
        t = 0.03 + 0.97 * i / nr; row = []
        for j in range(na):
            a = -A + 2 * A * j / (na - 1); an = a / A
            rib = math.cos(an * NR * math.pi)
            r = s * t * (1 + 0.035 * rib * t)
            z = s * 0.3 * math.sin(math.pi * t) ** 0.7 * (1 - abs(an) ** 3) + s * 0.03 * rib * t * (1 - abs(an) ** 3)   # menteşe ve kenar kuma değer (iç boşluk görünmez)
            row.append(bm.verts.new((math.sin(a) * r, math.cos(a) * r - s * 0.45, max(0.0, z))))
        rows.append(row)
    for i in range(nr):
        for j in range(na - 1):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    loop = [rows[i][0] for i in range(nr + 1)] + rows[nr][1:-1] + [rows[i][na - 1] for i in range(nr, -1, -1)] + rows[0][-2:0:-1]
    try: bm.faces.new(list(reversed(loop)))            # alt yüz
    except ValueError: pass
    ear = [bm.verts.new(p) for p in ((-s * 0.3, -s * 0.5, 0.0), (s * 0.3, -s * 0.5, 0.0), (s * 0.27, -s * 0.33, s * 0.05), (-s * 0.27, -s * 0.33, s * 0.05))]
    bm.faces.new(ear)                                    # menteşe kulakçıkları (tek parça)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    m, g = new_mat(name + '_m')
    xyz = g.xyz(g.obj())
    yy = g.math('ADD', xyz['Y'], s * 0.45)
    rr = g.math('POWER', g.math('ADD', g.math('POWER', xyz['X'], 2.0), g.math('POWER', yy, 2.0)), 0.5)
    ang = g.math('DIVIDE', g.math('ARCTAN2', xyz['X'], yy), A)
    groove = g.rng(g.math('COSINE', g.math('MULTIPLY', ang, NR * math.pi)), -1.0, -0.3, 1.0, 0.0)
    bands = g.math('SINE', g.math('MULTIPLY', rr, 7.0 * math.pi / s))
    col = g.mix(g.rng(bands, 0.0, 1.0, 0, 0.35), hexc, '#fff4ea')
    col = g.mix(g.math('MULTIPLY', groove, 0.45), col, '#a8645a')
    col = g.mix(g.rng(rr, s * 0.15, s * 0.0, 0.0, 0.5), col, '#fff8f0')
    g.out(col, 0.38, coat=0.35)
    me.materials.append(m)
    return K.link(bpy.data.objects.new(name, me))


def conch(name, s, hexc, seed):
    """Deniz salyangozu: sarmal koni (her tur bir öncekine biner → belirgin dikiş çizgileri), sivri tepe, geniş açılmış ağız
    dudağı; krem üstünde kahverengi sarmal benekler. Yan yatık durur."""
    pts, rad = [], []
    turns = 4.2; n = 220; R0 = s * 0.34; H = s * 1.25
    for i in range(n):
        t = i / (n - 1)
        a = t * turns * math.tau; Rh = R0 * (1 - 0.94 * t)
        pts.append((math.cos(a) * Rh, math.sin(a) * Rh, H * t ** 0.9))
        rad.append(max(0.002, Rh * 0.98 * (1 + 0.5 * max(0.0, 0.06 - t) / 0.06) * (1 + 0.05 * math.sin(a * 9) * (1 - t))))
    v, f = K.tube_data(pts, rad, 20)
    m, g = new_mat(name + '_m')
    o_ = g.obj(); xyz = g.xyz(o_)
    sp = g.math('SINE', g.math('ADD', g.math('MULTIPLY', g.math('ARCTAN2', xyz['Y'], xyz['X']), 3.0), g.math('MULTIPLY', xyz['Z'], 40.0 / s)))
    dots = g.rng(g.noise(o_, 9.0 / s, 2), 0.55, 0.65)
    col = g.mix(g.math('MULTIPLY', g.rng(sp, 0.4, 0.8), dots), hexc, '#9a5a32')
    col = g.mix(g.rng(xyz['Z'], H * 0.9, H, 0.0, 0.5), col, '#c98f6a')
    g.out(col, 0.32, coat=0.45)
    return K.mesh_obj(name, v, f, m)


def pebble(name, s, hexc, seed):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for vv in bm.verts:
        n = MN.noise(vv.co * 1.6 + V((seed, seed * 0.3, 0))) * 0.12
        vv.co = V((vv.co.x * s, vv.co.y * s * 0.8, vv.co.z * s * 0.45)) * (1 + n)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    m, g = new_mat(name + '_m')
    o_ = g.obj()
    col = g.mix(g.rng(g.noise(o_, 30.0 / max(s, 0.01) * 0.05, 4), 0.4, 0.7, 0, 0.5), hexc, '#f4efe6')
    g.out(col, 0.5, coat=0.25)
    me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


class Cam:
    """Ekran noktası (u, v; 0..1, sol alt) → kum üzerindeki dünya noktası (ışın + zemin kesişimi)."""
    def __init__(self, sc, cam, height_fn):
        self.sc = sc; self.cam = cam; self.h = height_fn
        bpy.context.view_layer.update()
        fr = cam.data.view_frame(scene=sc)          # sağ üst, sağ alt, sol alt, sol üst (kamera uzayı)
        self.tr, self.br, self.bl, self.tl = [V(c) for c in fr]
        self.M = cam.matrix_world.copy()

    def ray(self, u, v):
        lp = self.bl + (self.br - self.bl) * u + (self.tl - self.bl) * v
        o = self.M.translation; d = (self.M.to_3x3() @ lp).normalized()
        return o, d

    def ground(self, u, v):
        o, d = self.ray(u, v)
        z = 0.0
        for _ in range(8):
            t = (z - o.z) / d.z
            p = o + d * t
            z = float(self.h(np.array([p.x]), np.array([p.y]))[0])
        return V((p.x, p.y, z))

    def at(self, u, v, dist):
        o, d = self.ray(u, v); return o + d * dist


def palm_leaf_mat(name, dark=0.0):
    """Palmiye yaprağı (oyuncak): köşe rengi; alt yüz açık sarımsı yeşil (gerçekte de alt yüz soluk), güneşte yarı saydam
    ışıma, az yayma → alttan bakınca kararmaz, yumuşak; ton oynaması nesne başına."""
    m, g = new_mat(name)
    vc = g.n.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    geo = g.n.new('ShaderNodeNewGeometry')
    oi = g.n.new('ShaderNodeObjectInfo')
    hs = g.n.new('ShaderNodeHueSaturation'); g.l.new(vc.outputs['Color'], hs.inputs['Color'])
    g._in(hs.inputs['Hue'], g.math('MULTIPLY_ADD', oi.outputs['Random'], 0.04, 0.48))
    hs.inputs['Value'].default_value = 1.0 - dark
    col = g.mix(g.math('MULTIPLY', geo.outputs['Backfacing'], 0.45), hs.outputs['Color'], '#b9d77a')
    vein = g.rng(g.noise(g.mapping(g.obj(), (8, 8, 8)), 4.0, 3), 0.45, 0.6, 0.0, 0.12)
    col = g.mix(vein, col, '#e4f29a')
    g.out(col, 0.5)
    g.b.inputs['Specular IOR Level'].default_value = 0.35
    g._in(g.b.inputs['Emission Color'], col); g.b.inputs['Emission Strength'].default_value = 0.16
    tr = g.n.new('ShaderNodeBsdfTranslucent'); g.l.new(col, tr.inputs['Color'])
    mx = g.n.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.42
    g.l.new(g.b.outputs[0], mx.inputs[1]); g.l.new(tr.outputs[0], mx.inputs[2])
    g.l.new(mx.outputs[0], g.n['Material Output'].inputs['Surface'])
    return m


def lathe_rmf(name, path, rfun, res=18, mat=None, colfun=None):
    """Kesitli tüp (K2.lathe gibi) ama dönmeyen (paralel taşınan) çerçeveyle: eğik gövdede eksen değişince oluşan kırık olmaz."""
    pts = [V(p) for p in path]; n = len(pts)
    tg0 = (pts[1] - pts[0]).normalized()
    u = tg0.cross(V((1, 0, 0)) if abs(tg0.x) < 0.9 else V((0, 1, 0))).normalized()
    verts, faces, cols = [], [], []
    prev = tg0
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        u = (u - tg * u.dot(tg)).normalized(); w = tg.cross(u)
        t = i / (n - 1)
        for k in range(res):
            a = k / res * math.tau; r = rfun(t, a)
            q = p + (u * math.cos(a) + w * math.sin(a)) * r; verts.append(q)
            if colfun: cols.append(colfun(t, a, q))
    for i in range(n - 1):
        for k in range(res):
            a = i * res + k; b = i * res + (k + 1) % res
            faces.append((a, b, b + res, a + res))
    return K.mesh_obj(name, verts, faces, mat, colors=np.array(cols) if cols else None)


def toy_palm(name, base, h, seed, lean_to, lean=0.25, nfr=10, frond=None, nut_scale=1.15, dark=0.0):
    """Oyuncak (vinyl) palmiye: halka halka boğumlu, dibi genişleyen kavisli gövde; tepeden yükselip sarkan geniş yapraklar
    (her yaprak = orta damar + iki yanda V katlı, sivri uçlu iri yaprakçıklar; yumuşak taç normali → boyalı hacim),
    yaprak dibinde kuru lifli yaka ve iri ceviz salkımı. lean_to: eğim yönü (derece, dünya). dark: ön plan için koyulaştırma."""
    R = random.Random(seed)
    la = math.radians(lean_to); dv = V((math.cos(la), math.sin(la), 0))
    bend = R.uniform(1.4, 1.9)
    path = [V(base) + dv * (lean * h * t ** bend) + V((0, 0, h * t - 0.25)) for t in np.linspace(0, 1, 48)]
    r0 = 0.2 * (h / 5.0) ** 0.6; r1 = r0 * 0.66; rings = int(h * 2.6)
    def rf(t, a):
        b = r0 + (r1 - r0) * t ** 0.8 + r0 * 0.7 * max(0.0, 0.07 - t) * 12
        fr = (t * rings) % 1.0
        return b * (1 + 0.1 * math.sin(math.pi * fr) ** 0.6 - 0.04 + 0.02 * MN.noise(V((math.cos(a) * 3, math.sin(a) * 3, t * 9))))
    k = 1.0 - dark
    cA, cB, cC, cD = K2.c3('#9a6a3a') * k, K2.c3('#c08a50') * k, K2.c3('#6a4224') * k, K2.c3('#d9a868') * k
    def cf(t, a, q):
        fr = (t * rings) % 1.0
        lit = 0.5 + 0.5 * MN.noise(V((math.cos(a) * 5, math.sin(a) * 5, t * 20)))
        c = K2.lerp3(cA, cB, lit)
        c = K2.lerp3(c, cC, math.exp(-((fr - 0.02) / 0.08) ** 2) * 0.8)        # boğum çizgisi
        c = K2.lerp3(c, cD, math.exp(-((fr - 0.9) / 0.07) ** 2) * 0.55)        # boğum dudağı (açık)
        return K2.lerp3(c, K2.c3('#5a3a20') * k, max(0.0, 0.12 - t) * 5)
    tm = K2.vc_mat(name + '_tm', rough=0.7, bump=0.3, bscale=18, stretch=(3, 3, 0.4))
    objs = [lathe_rmf(name + '_trunk', path, rf, res=22, mat=tm, colfun=cf)]
    top = path[-1]; tg = (path[-1] - path[-4]).normalized()
    # kuru lifli yaka (yaprak dibi)
    bootm = K2.vc_mat(name + '_bm', rough=0.9, bump=0.7, bscale=40, stretch=(2, 2, 0.3))
    bp = [top - tg * 0.55, top - tg * 0.15, top + tg * 0.2]
    objs.append(lathe_rmf(name + '_boot', bp, lambda t, a: r1 * (1.45 + 0.5 * math.sin(math.pi * t)) * (1 + 0.1 * MN.noise(V((math.cos(a) * 6, math.sin(a) * 6, t * 4)))),
                         res=16, mat=bootm, colfun=lambda t, a, q: K2.lerp3(K2.c3('#6a4a2a') * k, K2.c3('#a98352') * k, MN.noise(V((math.cos(a) * 14, math.sin(a) * 14, t * 6))) * 0.5 + 0.5)))
    # yapraklar: her biri tek parça geniş yaprak bıçağı — kenarları derin çentikli "parmaklar" (uca doğru süpürülmüş),
    # orta damar boyunca hafif V katlı ve kenarları aşağı kıvrık; tepeden yükselip kavisle sarkar. Oyuncak/vinyl silüet.
    L0 = frond or 0.52 * h ** 0.8
    cen = top + V((0, 0, -0.1 * L0))
    V_, F_, C_, N_ = [], [], [], []
    rib_v, rib_f = [], []
    plan = [(f / nfr * math.tau + R.uniform(-0.22, 0.22), R.uniform(0.1, 0.7), R.uniform(0.85, 1.12)) for f in range(nfr)]
    plan += [(R.uniform(0, math.tau), R.uniform(1.1, 1.5), R.uniform(0.5, 0.65)) for f in range(max(2, nfr // 4))]   # genç dik yapraklar
    NS_, NX = 130, 7
    for fi, (az, up, lk) in enumerate(plan):
        L = L0 * lk; Wm = L * R.uniform(0.21, 0.25); nf = R.randint(12, 15)
        d = V((math.cos(az), math.sin(az), 0)); side = V((-d.y, d.x, 0))
        twist = R.uniform(-0.25, 0.25)
        def rach(s, d=d, up=up, L=L): return top + d * (L * s * 0.95) + V((0, 0, L * (up * s - (0.46 + up) * s * s)))
        o = len(V_)
        for i in range(NS_ + 1):
            s = i / NS_
            p = rach(s); t2 = (rach(min(1.0, s + 0.01)) - rach(max(0.0, s - 0.01))).normalized()
            sd = (side * math.cos(twist * s) + V((0, 0, 1)) * math.sin(twist * s))
            sd = (sd - t2 * sd.dot(t2)).normalized(); fn = t2.cross(sd).normalized()
            if fn.z < 0: fn = -fn
            W = Wm * math.sin(math.pi * min(1.0, 0.05 + s * 0.97)) ** 0.55 * (0.35 + 0.65 * min(1.0, s * 4))
            for j in range(NX):
                v = j / (NX - 1) * 2 - 1                     # −1 sol kenar … +1 sağ kenar
                ph = (s * nf + (0.5 if v > 0 else 0.0)) % 1.0
                notch = 1.0 - 0.8 * math.exp(-(ph / 0.075) ** 2) - 0.8 * math.exp(-((1 - ph) / 0.075) ** 2)
                av = abs(v)
                ww = W * av * (notch if av > 0.6 else 1.0 - (1.0 - notch) * (av / 0.6) ** 3)
                sweep = t2 * (L * 0.05 * av ** 2 * ph)                       # parmak uçları ileri süpürülür
                drop = fn * (-W * (0.22 * av + 0.35 * av ** 2.2))               # V kat + kenar kıvrımı
                q = p + sd * (ww * (1 if v >= 0 else -1)) + sweep + drop
                V_.append(q)
                C_.append(min(1.0, 0.2 + 0.62 * s + 0.12 * (1 - av) + 0.06 * R.random()))
                N_.append((fn * 0.7 + (q - cen).normalized() * 0.3 + sd * (0.35 * v)).normalized())
        for i in range(NS_):
            for j in range(NX - 1):
                a0 = o + i * NX + j
                F_.append((a0, a0 + 1, a0 + NX + 1, a0 + NX))
        pts = [rach(s) + V((0, 0, 0.012 * L)) for s in np.linspace(0.0, 0.97, 16)]
        rv, rfc = K.tube_data(pts, [L * 0.018 * (1 - 0.85 * t) for t in np.linspace(0, 1, 16)], 6, len(rib_v))
        rib_v += rv; rib_f += rfc
    pal = [(0.0, '#2c6a27'), (0.3, '#3f8f35'), (0.6, '#64b23f'), (0.85, '#96cf4c'), (1.0, '#c8e46c')]
    cols = K.ramp3(np.array(C_), pal)
    fol = palm_leaf_mat(name + '_fol', dark)
    objs.append(K.mesh_obj(name + '_fronds', V_, F_, fol, colors=cols, normals=N_))
    objs.append(K.mesh_obj(name + '_ribs', rib_v, rib_f, flat_mat(name + '_rib', '#9cc455' if not dark else '#86ad48', 0.6)))
    # ceviz salkımı (oyundaki cevizlerle aynı: kahverengi lifli + birkaç yeşil)
    if nut_scale > 0:
        nm, g = new_mat(name + '_coco')
        o_ = g.obj()
        fib = g.noise(g.mapping(o_, (6, 6, 30)), 2.0, 5)
        g.out(g.mix(g.rng(fib, 0.3, 0.7), '#6a3a1a', '#97602e'), 0.55, g.bump(fib, 0.2, 0.01), coat=0.25)
        gm = flat_mat(name + '_cocog', '#5c7d22', 0.45, coat=0.25)
        for kk in range(R.randint(5, 7)):
            a = kk / 6 * math.tau + R.uniform(-0.3, 0.3); rr = R.uniform(0.17, 0.22) * nut_scale
            bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=18, radius=rr,
                                                 location=top - tg * (0.45 + R.uniform(0, 0.3)) + V((math.cos(a), math.sin(a), 0)) * (r1 * 1.4 + rr * 0.85))
            c = bpy.context.object; c.scale = (0.94, 0.94, 1.08); bpy.ops.object.shade_smooth()
            c.data.materials.append(gm if R.random() < 0.3 else nm); objs.append(c)
    return objs


def drop_specks(o, keep=0.15):
    """Bulut ağından kopuk küçük parçaları (havada yüzen kabarcıklar) siler."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen = bytearray(len(bm.verts)); comps = []
    for v in bm.verts:
        if seen[v.index]: continue
        stack = [v]; comp = []; seen[v.index] = 1
        while stack:
            x = stack.pop(); comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if not seen[y.index]: seen[y.index] = 1; stack.append(y)
        comps.append(comp)
    big = max(len(c) for c in comps)
    kill = [v for c in comps if len(c) < big * keep for v in c]
    if kill: bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(o.data); bm.free()


def islet(loc, s=1.0):
    """Uzak adacık: kumsal etekli yeşil tepe, iki küçük palmiye, kıyısında birkaç kaya (havayla soluk: hava perspektifi)."""
    objs = []
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    for vv in bm.verts:
        n = MN.noise(vv.co * 1.4 + V((3, 1, 0))) * 0.18
        z = max(vv.co.z, -0.2)
        pk = math.exp(-((vv.co.x + 0.25) / 0.55) ** 2)
        vv.co = V((vv.co.x * 11 * s * (1 + n), vv.co.y * 7 * s * (1 + n), z * (2.6 + 3.2 * pk) * s * (1 + n * 0.5)))
    me = bpy.data.meshes.new('islet'); bm.to_mesh(me); bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    m, g = new_mat('islet_m')
    zz = g.xyz(g.obj())['Z']
    nz = g.noise(g.obj(), 0.6, 3)
    t = g.math('ADD', zz, g.math('MULTIPLY', nz, 0.8))
    col = g.mix(g.rng(t, 0.3 * s, 0.9 * s), '#f3e2bd', g.mix(g.rng(nz, 0.4, 0.7), '#6fb85e', '#9ccf78'))
    col = g.mix(0.22, col, '#cfe9f7')                                   # hava perspektifi (uzak = soluk mavimsi)
    g.out(col, 0.9)
    me.materials.append(m)
    o = bpy.data.objects.new('islet', me); bpy.context.scene.collection.objects.link(o); o.location = loc; objs.append(o)
    for i, (dx, dy, h, sd, la) in enumerate(((-2.5, 0.5, 7.5, 31, 200), (2.6, 1.2, 6.2, 33, -20), (5.8, -0.5, 4.8, 35, 10))):
        objs += toy_palm('ip%d' % i, (loc[0] + dx * s, loc[1] + dy * s, loc[2] + 2.0 * s - abs(dx) * 0.25 * s), h * s, sd, la, lean=0.18, nfr=8, nut_scale=0.0)
    rm = K.rock_mat('islet_rock', base='#b8b0b4', dark='#8f8794', light='#d6cfca', moss_amt=0.0, cracks=0.3)
    for i in range(5):
        a = -0.4 + i * 0.35
        b = K.boulder('ir%d' % i, (1.2 * s, 1.0 * s, 0.8 * s), 40 + i, cuts=9, mat=rm, bevel=0.1)
        b.location = (loc[0] + math.cos(a) * 10.5 * s, loc[1] + math.sin(a) * 6 * s - 4 * s, loc[2] - 0.2)
    return objs


def build_bg(path):
    W, H = 2048, 1024
    sc = reset(W, H, 96)
    sc.view_settings.exposure = -0.15
    sky_world(sc)
    sun(sc, (0.42, 0.2, -0.88), 3.3, angle=6.0)

    # kamera: alçak, hafif aşağı bakan geniş açı; ufuk ekranın ~%57'sinde
    cd = bpy.data.cameras.new('cam'); cd.lens = 24; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36
    cd.clip_end = 9000; cd.shift_y = 0.065
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, 0, 3.2); cam.rotation_euler = (math.radians(90 - 9.0), 0, 0)

    # --------------------------------------------------- kum
    def base_h(x, y):
        z = SLOPE * (shore_y(x) - y)
        z = z + 0.06 * np.sin(x * 0.45 + y * 0.3) * np.clip((shore_y(x) - y) / 3, 0, 1)
        return z
    nx, ny = (700, 520) if FAST else (1500, 1100)
    xs = np.linspace(-24, 24, nx); ys = np.concatenate([np.linspace(4.0, 12.0, ny // 3), np.linspace(12.0, SHORE0 + 6, ny - ny // 3)[1:]])
    X, Y = np.meshgrid(xs, ys)
    Z = base_h(X, Y)
    cam_tool = Cam(sc, cam, base_h)
    # tümsekler (palmiye diplerinde, arka kenarda)
    for (u, v, r, hh) in ((0.04, 0.3, 3.2, 0.3), (0.96, 0.3, 3.0, 0.28), (0.3, 0.37, 2.4, 0.1), (0.72, 0.37, 2.6, 0.1)):
        q = cam_tool.ground(u, v)
        Z += hh * np.exp(-(((X - q.x) / r) ** 2 + ((Y - q.y) / (r * 0.7)) ** 2))
    # ayak izleri: sağ ön çeyrekten kıyıya doğru yürüyen küçük çocuk izleri (alt sakin şeridin üstünde)
    steps = []
    p0 = cam_tool.ground(0.68, 0.24); p1 = cam_tool.ground(0.57, 0.38)
    n_st = 9
    for i in range(n_st):
        t = i / (n_st - 1)
        cx = p0.x + (p1.x - p0.x) * t + 0.12 * math.sin(t * 4); cy = p0.y + (p1.y - p0.y) * t
        ang = math.atan2(p1.y - p0.y, p1.x - p0.x) + 0.1 * math.cos(t * 4)
        side = 1 if i % 2 else -1
        steps.append((cx - math.sin(ang) * 0.17 * side, cy + math.cos(ang) * 0.17 * side, ang, side, 2.5))
    dz, fp = footprints(X, Y, steps)
    Z = Z + dz
    mesh_from_grid('sand', X, Y, Z, sand_mat(), {'fp': fp})

    # --------------------------------------------------- deniz
    sx = np.concatenate([np.linspace(-6000, -60, 30), np.linspace(-60, 60, 241)[1:-1], np.linspace(60, 6000, 30)])
    sy = np.concatenate([np.linspace(SHORE0 - 3, 90, 260), np.linspace(90, 8000, 60)[1:]])
    SX, SY = np.meshgrid(sx, sy)
    mesh_from_grid('sea', SX, SY, np.zeros_like(SX), sea_mat())

    # --------------------------------------------------- palmiyeler (ön plan iri ve koyu, kıyıda küçük)
    def palm(name, u, v, h, seed, lean_to, **kw):
        q = cam_tool.ground(u, v); toy_palm(name, (q.x, q.y, q.z), h, seed, lean_to, **kw)
    palm('palmL', 0.025, 0.25, 5.2, 7, 22, lean=0.42, dark=0.06)
    palm('palmR', 0.98, 0.25, 5.5, 3, 155, lean=0.42, dark=0.06)
    palm('palmL2', 0.2, 0.385, 4.8, 12, 70, lean=0.14, nfr=9)
    palm('palmR2', 0.83, 0.39, 4.2, 21, 115, lean=0.18, nfr=9)

    # --------------------------------------------------- uzak adacık, bulutlar
    q = cam_tool.at(0.64, 0.585, 1.0)
    d = (q - cam.location); t = -cam.location.z / d.z if d.z < 0 else 260.0
    il = cam.location + d * min(t, 260.0)
    islet((il.x, il.y, -0.6), 1.7)
    cm = K.cloud_mat()
    for i, (u, v, dist, s_, tall) in enumerate(((0.12, 0.64, 3000, 1100, 0.8), (0.33, 0.6, 3600, 800, 0.5), (0.78, 0.605, 3400, 1000, 0.65),
                                                (0.97, 0.68, 2800, 900, 0.7))):
        p_ = cam_tool.at(u, v, dist)
        c = K.cumulus('cl%d' % i, size=s_, seed=11 + i, mat=cm, tall=tall); c.location = (p_.x, p_.y, p_.z - s_ * 0.1)
        drop_specks(c)

    # --------------------------------------------------- kum süsleri (alt sakin şeridin üstünde ve köşelerde)
    def put(obj, u, v, rot=None, sink=0.0):
        p = cam_tool.ground(u, v); obj.location = (p.x, p.y, p.z - sink)
        obj.rotation_euler = (0, 0, rot if rot is not None else random.uniform(0, math.tau))
        return obj
    random.seed(5)
    put(scallop('sc1', 0.42, '#f2a99a', 1), 0.3, 0.315, rot=0.3)
    put(scallop('sc2', 0.32, '#f6dcc2', 2), 0.345, 0.29, rot=-0.5)
    put(scallop('sc3', 0.4, '#e99cbc', 3), 0.76, 0.33, rot=0.9)
    put(scallop('sc6', 0.34, '#a9c8f0', 8), 0.205, 0.235, rot=0.2)
    put(scallop('sc4', 0.5, '#f3c29a', 4), 0.085, 0.11, rot=-0.2)
    put(scallop('sc5', 0.42, '#b6a8ee', 5), 0.925, 0.1, rot=0.4)
    c1 = put(conch('co1', 0.42, '#f3dcbc', 6), 0.45, 0.35, sink=-0.1); c1.rotation_euler = (math.radians(-80), 0, 0.9)
    c2 = put(conch('co2', 0.5, '#f6d2a8', 7), 0.87, 0.2, sink=-0.12); c2.rotation_euler = (math.radians(-80), 0, 2.2)
    for i, (u, v, s_) in enumerate(((0.63, 0.335, 0.5), (0.13, 0.215, 0.55), (0.82, 0.255, 0.42))):
        before = set(bpy.data.objects); K2.starfish('sf%d' % i, r=s_, seed=i + 3)
        grp = group('sfg%d' % i, new_objects(before)); put(grp, u, v)
    peb = [('#cfc6bb', 0.18), ('#e8e1d6', 0.14), ('#a99f95', 0.12), ('#d8cbbb', 0.16), ('#bfb5aa', 0.11)]
    for i, (u, v) in enumerate(((0.385, 0.33), (0.403, 0.322), (0.705, 0.31), (0.69, 0.328), (0.235, 0.35), (0.5, 0.375), (0.515, 0.37),
                                (0.79, 0.36), (0.05, 0.1), (0.95, 0.22), (0.97, 0.05), (0.03, 0.04), (0.255, 0.27), (0.745, 0.265))):
        hx, s_ = peb[i % len(peb)]; put(pebble('pb%d' % i, s_, hx, i), u, v, sink=s_ * 0.15)
    before = set(bpy.data.objects); K2.crab('crab', s=0.55, seed=2)
    put(group('crabg', new_objects(before)), 0.275, 0.375, rot=math.radians(-110))
    # palmiye diplerinde geniş yapraklı kumsal bitkisi
    fol = K.foliage_mat('ros_m', translucent=0.35)
    for i, (u, v, L) in enumerate(((0.075, 0.27, 1.5), (0.925, 0.27, 1.6), (0.235, 0.39, 1.0), (0.79, 0.395, 1.0))):
        put(K.rosette('ros%d' % i, n=12, length=L, width=0.2, seed=i, mat=fol), u, v)

    tmp = path + '.tmp.png'
    save(sc, tmp)
    grade_bg(tmp, path)


def grade_bg(src, dst):
    """Boyalı maket bitişi: kenarlara doğru çok hafif sıcak karartma (göz ortaya, derinlik), alt kenarda yumuşak kum gölgesi;
    sonra JPEG (repo boyutu)."""
    img = bpy.data.images.load(src); w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); x = (xx + 0.5) / w - 0.5; y = (yy + 0.5) / h       # y: alttan
    r = np.sqrt((x * 1.0) ** 2 + ((y - 0.55) * 1.25) ** 2)
    k = 1.0 - 0.16 * np.clip((r - 0.38) / 0.45, 0, 1) ** 1.6 - 0.06 * np.clip(1.0 - y / 0.12, 0, 1) ** 2
    tint = np.array([1.0, 0.97, 0.92], np.float32)
    px[..., :3] = px[..., :3] * (k[..., None] * (1 - (1 - k[..., None]) * (1 - tint) * 2.5))
    out = bpy.data.images.new('graded', w, h, alpha=False)
    out.pixels.foreach_set(np.clip(px, 0, 1).ravel())
    out.filepath_raw = dst; out.file_format = 'JPEG'
    out.save(quality=88)
    os.remove(src)
    print('yazıldı', dst, flush=True)


# ------------------------------------------------------------------ hasır sepet

def wicker_mat(name, base='#d9a55a', dark='#9a6428'):
    """Hasır çubuk: boyuna lifler, hafif ton oynaması (çubuk başına), uçlarda koyulaşma; düşük parlaklık."""
    m, g = new_mat(name)
    o = g.obj()
    oi = g.n.new('ShaderNodeObjectInfo')
    fib = g.noise(g.mapping(o, (40, 40, 4)), 3.0, 6)
    col = g.mix(g.rng(fib, 0.3, 0.75), dark, base)
    col = g.mix(g.math('MULTIPLY', oi.outputs['Random'], 0.35), col, '#efc888')
    col = g.mix(g.math('MULTIPLY', g.rng(g.noise(o, 60.0, 3), 0.6, 0.75), 0.4), col, '#7a4a1c')
    g.out(col, 0.55, g.bump(fib, 0.35, 0.005), coat=0.15)
    return m


def build_basket(path):
    sc = reset(512, 320, 128, transparent=True)
    sc.view_settings.exposure = 0.0
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = srgb('#dfe9f5') + (1,)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
    sun(sc, (0.3, 0.35, -0.89), 3.2, angle=8.0)
    area_light(sc, (-3, -4, 4), (0, 0, 0.4), 260, 4.0, (1.0, 0.97, 0.92))
    area_light(sc, (3.5, 3, 2.5), (0, 0, 0.5), 160, 3.0, (0.85, 0.92, 1.0))      # kenar ışığı
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = 4.0
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    el = math.radians(20)
    cam.location = (0, -10 * math.cos(el), 10 * math.sin(el) + 0.5); cam.rotation_euler = (math.radians(90) - el, 0, 0)
    cd.shift_y = 0.012

    R0, Rt, Hh = 1.5, 1.66, 1.02                     # dip yarıçapı, ağız yarıçapı, yükseklik
    def rad(z): return R0 + (Rt - R0) * (z / Hh) ** 0.8
    NS = 26                                          # dikme sayısı (çift)
    mats = [wicker_mat('wk%d' % i) for i in range(3)]
    stake_m = wicker_mat('stake', base='#c58f48', dark='#80501f')
    band_m = wicker_mat('band', base='#ec7a52', dark='#b8432a')          # boyalı süs şeridi (mercan)
    rows = 11
    # dikmeler
    for k in range(NS):
        a = k / NS * math.tau
        pts = [(math.cos(a) * rad(z), math.sin(a) * rad(z), z) for z in np.linspace(0.02, Hh, 10)]
        v, f = K.tube_data(pts, [0.032] * len(pts), 8)
        K.mesh_obj('st%d' % k, v, f, stake_m)
    # sarma çubuklar: her sıra dikmelerin bir önünden bir arkasından (altlı üstlü), sıradan sıraya kayar
    for r in range(rows):
        z = 0.09 + r * (Hh - 0.16) / (rows - 1)
        pts, rr = [], []
        n = NS * 8
        for i in range(n + 1):
            a = i / n * math.tau
            off = 0.05 * math.cos(a * NS / 2 + (math.pi if r % 2 else 0.0))
            R_ = rad(z) + off
            pts.append((math.cos(a) * R_, math.sin(a) * R_, z + 0.008 * math.sin(a * 3 + r)))
            rr.append(0.046)
        v, f = K.tube_data(pts, rr, 10)
        K.mesh_obj('wv%d' % r, v, f, band_m if r in (7, 8) else mats[r % 3])
    # iç yüz ve dip: açık tüp (kapaksız) + disk; örgü deseni gölgelendiricide (içerisi koyu, derin)
    inner_m, g = new_mat('inner')
    xyz = g.xyz(g.obj())
    ang = g.math('ARCTAN2', xyz['Y'], xyz['X'])
    u = g.math('MULTIPLY', ang, NS / 2.0); v = g.math('MULTIPLY', xyz['Z'], 1.0 / ((Hh - 0.16) / (rows - 1)) * math.pi)
    weave = g.math('MULTIPLY', g.math('SINE', u), g.math('SINE', v))
    col = g.mix(g.rng(weave, -0.25, 0.25), '#8a5626', '#c48d4c')
    col = g.mix(g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('COSINE', v)), 0.9, 1.0), 0.6), col, '#4a2a10')
    g.out(col, 0.75, g.bump(g.math('ABSOLUTE', weave), 0.5, 0.02))
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.0, depth=1.0, location=(0, 0, 0.5), end_fill_type='NOTHING')
    inn = bpy.context.object; inn.scale = (R0 - 0.045, R0 - 0.045, Hh); inn.location.z = Hh * 0.5 + 0.02
    inn.data.materials.append(inner_m); bpy.ops.object.shade_smooth()
    disc_m, g = new_mat('disc')
    xyz = g.xyz(g.obj())
    ang = g.math('ARCTAN2', xyz['Y'], xyz['X'])
    rr_ = g.math('POWER', g.math('ADD', g.math('POWER', xyz['X'], 2.0), g.math('POWER', xyz['Y'], 2.0)), 0.5)
    spokes = g.math('SINE', g.math('MULTIPLY', ang, NS / 2.0))
    spiral = g.math('SINE', g.math('MULTIPLY_ADD', rr_, 40.0, g.math('MULTIPLY', ang, 1.0)))
    col = g.mix(g.rng(g.math('MULTIPLY', spokes, spiral), -0.25, 0.25), '#8a5626', '#c48d4c')
    g.out(col, 0.75, g.bump(g.math('ABSOLUTE', g.math('MULTIPLY', spokes, spiral)), 0.4, 0.02))
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R0 - 0.03, depth=0.06, location=(0, 0, 0.05))
    b = bpy.context.object; b.data.materials.append(disc_m); bpy.ops.object.shade_smooth()
    # dip halkası: kalın bükümlü halat (altta boşluk kalmasın, sepet yere otursun)
    for j in range(2):
        pts, rr = [], []
        for i in range(241):
            a = i / 240 * math.tau; ph = a * 30 + j * math.pi
            R_ = R0 + 0.02 + 0.035 * math.cos(ph)
            pts.append((math.cos(a) * R_, math.sin(a) * R_, 0.06 + 0.035 * math.sin(ph)))
            rr.append(0.05)
        v, f = K.tube_data(pts, rr, 10)
        K.mesh_obj('foot%d' % j, v, f, mats[j])
    # örgülü ağız: üç bükümlü halat halkası
    for j in range(3):
        pts, rr = [], []
        n = 260
        for i in range(n + 1):
            a = i / n * math.tau; ph = a * 38 + j * math.tau / 3
            R_ = Rt + 0.035 + 0.05 * math.cos(ph)
            pts.append((math.cos(a) * R_, math.sin(a) * R_, Hh + 0.04 + 0.05 * math.sin(ph)))
            rr.append(0.055)
        v, f = K.tube_data(pts, rr, 10)
        K.mesh_obj('rim%d' % j, v, f, mats[(j + 1) % 3])
    # gölge yakalayıcı zemin (şeffaf arka planda yumuşak temas gölgesi)
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    pl = bpy.context.object; pl.is_shadow_catcher = True
    save(sc, path)
    # gölge: yalnız sepetin altında yumuşak temas gölgesi (kenarlara doğru sıfıra iner; gürültü kırpılır)
    def fade(a, xx, yy):
        dx = (xx - 0.5) / 0.5; dy = (yy - 0.1) / 0.24
        k = np.clip((1.0 - np.sqrt(dx * dx + dy * dy)) / 0.3, 0, 1) ** 1.5
        return np.where(a > 0.985, a, np.where(a < 0.03, 0.0, a * k))
    post_alpha(path, fade)


# ------------------------------------------------------------------ hindistan cevizi simgeleri

def coconut_mesh(name, gold):
    """Hafif oval, üç sırtlı ceviz gövdesi; bir uçta (+Z) üç göz çukuru ve göze inen üç dikiş."""
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=64, radius=1.0)
    eyes = []
    for i in range(3):
        a = math.radians(90 + i * 120)
        eyes.append(V((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.95)).normalized())
    for vv in bm.verts:
        p = vv.co.copy()
        ang = math.atan2(p.y, p.x)
        ridge = 0.035 * max(0.0, math.cos(3 * (ang - math.radians(30)))) ** 6 * (1 - abs(p.z) ** 2)   # üç sırt
        lump = MN.noise(p * 1.8 + V((2, 5, 1))) * 0.035
        dent = 0.0
        for e in eyes:
            dd = (p - e).length
            dent += 0.05 * math.exp(-(dd / 0.09) ** 2)
            dent -= 0.012 * math.exp(-((dd - 0.13) / 0.04) ** 2)        # göz çevresi hafif kabarık halka
        r = 1.0 + ridge + lump - dent
        sx = 0.9; sz = 1.08 + 0.06 * max(0, p.z)
        vv.co = V((p.x * sx * r, p.y * sx * r, p.z * sz * r))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o, eyes


def coconut_husk_mat(gold):
    m, g = new_mat('husk_gold' if gold else 'husk')
    o = g.obj(); xyz = g.xyz(o)
    # lifler: boylamasına uzatılmış gürültü (Z ekseni boyunca uzun)
    fib = g.noise(g.mapping(o, (22, 22, 2.2)), 3.0, 8, 0.6)
    fib2 = g.noise(g.mapping(o, (60, 60, 6)), 2.0, 4)
    # göz ucuna (Z+) doğru koyu ve lifsiz, düz
    tip = g.rng(xyz['Z'], 0.72, 1.0)
    if gold:
        col = g.ramp(fib, [(0.25, '#f0a820'), (0.55, '#ffcf45'), (0.8, '#ffe68a')])
        col = g.mix(g.math('MULTIPLY', tip, 0.3), col, '#ffdc6a')
        g.out(col, g.math('MULTIPLY_ADD', fib2, 0.08, 0.13), g.bump(g.math('ADD', fib, g.math('MULTIPLY', fib2, 0.4)), 0.07, 0.01), metal=1.0, coat=0.6)
        g.b.inputs['Coat Roughness'].default_value = 0.04
    else:
        col = g.ramp(fib, [(0.2, '#3d2010'), (0.45, '#6a3c1c'), (0.7, '#9a6634'), (0.85, '#b98549')])
        col = g.mix(g.math('MULTIPLY', g.rng(fib2, 0.55, 0.75), 0.35), col, '#c99a5c')
        col = g.mix(g.math('MULTIPLY', tip, 0.55), col, '#4a2814')
        g.out(col, g.math('MULTIPLY_ADD', fib, 0.25, 0.5), g.bump(g.math('ADD', fib, g.math('MULTIPLY', fib2, 0.5)), 0.55, 0.012), coat=0.18)
        g.b.inputs['Coat Roughness'].default_value = 0.3
    return m


def fibers(o, gold, n=1300, seed=3):
    """Gerçek lif telleri: gövdeye yatık, boylamasına kısa kıvrık teller (silüette tüylü kenar)."""
    R = random.Random(seed)
    me = o.data; mw = o.matrix_world
    verts = [mw @ v.co for v in me.vertices]; norms = [(mw.to_3x3() @ v.normal).normalized() for v in me.vertices]
    cu = bpy.data.curves.new('fib', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0038; cu.bevel_resolution = 1
    for i in range(n):
        k = R.randrange(len(verts)); p = verts[k]; nn = norms[k]
        if p.z > 0.82 * 1.1: continue                       # göz ucu temiz
        up = V((0, 0, 1)); t = (up - nn * nn.dot(up)).normalized()
        if t.length < 0.5: continue
        side = nn.cross(t)
        L = R.uniform(0.06, 0.16); tw = R.uniform(-0.3, 0.3)
        sp = cu.splines.new('POLY'); sp.points.add(3)
        for j in range(4):
            s = j / 3
            q = p + (t * math.cos(tw) + side * math.sin(tw)) * L * s + nn * (0.003 + 0.018 * s * s * R.uniform(0.2, 1.0))
            sp.points[j].co = (q.x, q.y, q.z, 1)
            sp.points[j].radius = 1.0 - 0.7 * s
    fo = bpy.data.objects.new('fibers', cu); bpy.context.scene.collection.objects.link(fo)
    m, g = new_mat('fib_m')
    oi = g.n.new('ShaderNodeObjectInfo')
    rnd = g.noise(g.obj(), 40.0, 2)
    if gold:
        g.out(g.mix(rnd, '#e9a21e', '#fff0a0'), 0.25, metal=1.0)
    else:
        g.out(g.mix(rnd, '#5e351a', '#a8743f'), 0.65)
    cu.materials.append(m)
    return fo


def sparkle(name, loc, size, m):
    """Dört köşeli parıltı yıldızı (kameraya dönük, yayan)."""
    pts = []
    for i in range(8):
        a = i / 8 * math.tau; r = size if i % 2 == 0 else size * 0.22
        pts.append((math.cos(a) * r, 0, math.sin(a) * r))
    o = K.mesh_obj(name, [(0, 0, 0)] + pts, [(0, 1 + i, 1 + (i + 1) % 8) for i in range(8)], m, smooth=False)
    o.location = loc
    return o


def build_coconut(path, gold):
    sc = reset(256, 256, 160, transparent=True)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    n = w.node_tree.nodes; l = w.node_tree.links
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs[0])
    # ortam: altta sıcak kum, ufukta parlak bant, üstte gök mavisi (altın cevizde net, canlı yansıma çizgileri verir)
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1.0; mr.inputs['From Max'].default_value = 1.0
    l.new(sep.outputs['Z'], mr.inputs['Value'])
    rp = n.new('ShaderNodeValToRGB'); el = rp.color_ramp.elements
    stops = ([(0.0, '#5a3a1c'), (0.44, '#b07a3a'), (0.5, '#fff8e6'), (0.56, '#ffe8b4'), (1.0, '#f2d08e')] if gold else   # altın: sıcak ortam
             [(0.0, '#4e331c'), (0.44, '#b58a5a'), (0.5, '#fff4dc'), (0.53, '#d8ecff'), (1.0, '#5d9ee8')])
    el[0].position = 0.0; el[0].color = srgb(stops[0][1]) + (1,); el[1].position = 1.0; el[1].color = srgb(stops[-1][1]) + (1,)
    for p_, c_ in stops[1:-1]:
        e = el.new(p_); e.color = srgb(c_) + (1,)
    l.new(mr.outputs[0], rp.inputs['Fac']); l.new(rp.outputs['Color'], n['Background'].inputs['Color'])
    n['Background'].inputs['Strength'].default_value = 1.0 if gold else 0.6
    area_light(sc, (-3.2, -3.5, 3.6), (0, 0, 0), 520 if gold else 420, 2.2, (1.0, 0.96, 0.9))     # anahtar ışık (sol üst)
    area_light(sc, (3.2, 2.2, 1.2), (0, 0, 0.2), 420 if gold else 300, 1.6, (0.8, 0.9, 1.0))      # kenar ışığı (sağ arka)
    area_light(sc, (0.5, -4, -2.5), (0, 0, 0), 60, 4.0, (1.0, 0.9, 0.8))                         # alt dolgu
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = 2.6
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, -8, 0); cam.rotation_euler = (math.radians(90), 0, 0)
    o, eyes = coconut_mesh('coco', gold)
    o.data.materials.append(coconut_husk_mat(gold))
    em_, g = new_mat('eye')
    if gold: g.out('#a2620a', 0.3, metal=1.0)
    else: g.out('#1e0f07', 0.55)
    # gözler gövdeyle aynı ağda: göz çukurlarını koyu boyamak için ayrı küçük diskler
    for i, e in enumerate(eyes):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.075)
        d = bpy.context.object; d.scale = (1, 1, 0.35)
        p = V((e.x * 0.9, e.y * 0.9, e.z * 1.14)) * 0.955
        d.location = p; d.rotation_euler = e.to_track_quat('Z', 'Y').to_euler()
        d.data.materials.append(em_); bpy.ops.object.shade_smooth(); d.parent = o
    if not gold: fibers(o, gold).parent = o             # altın cilalı: lif teli yok, lifler yalnız kabartı
    # duruş: göz ucu sağ üstte, kameraya hafif dönük (eski simgeyle aynı kadraj)
    o.rotation_euler = (math.radians(40), math.radians(30), math.radians(4))
    if gold:
        sm, g = new_mat('spark')
        em = g.n.new('ShaderNodeEmission'); em.inputs['Color'].default_value = srgb('#fff4c0') + (1,); em.inputs['Strength'].default_value = 6.0
        g.l.new(em.outputs[0], g.n['Material Output'].inputs['Surface'])
        for i, (x, z, s_) in enumerate(((-0.98, 0.86, 0.17), (1.0, -0.5, 0.14), (0.8, 1.02, 0.1), (-1.02, -0.86, 0.08))):
            sparkle('sp%d' % i, (x, -2, z), s_, sm)
    save(sc, path)


if 'bg' in ONLY: build_bg(os.path.join(OUT, 'Games', 'coconut_bg.jpg'))
if 'basket' in ONLY: build_basket(os.path.join(OUT, 'Games', 'basket.png'))
if 'coconut' in ONLY:
    build_coconut(os.path.join(OUT, 'Icons', 'ui_coconut.png'), False)
    build_coconut(os.path.join(OUT, 'Icons', 'ui_coconut_gold.png'), True)
