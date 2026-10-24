# Uygulama simgesi — tamamen kodla (Blender bpy yordamsal modelleme + Cycles CPU). Yapay zekâ görseli yok.
# Temel: S (Assets/_Pofi/Art/AppIcon.png) — yavru ahtapot, parlak açık mavi kubbe kafa, iri parlak gözler, kaş, yanak pembesi,
# sarı tişört, el sallayan dokunaç; gün doğumu ışınları, palmiyeler, adacıkta deniz feneri, turkuaz deniz.
# O'dan iki ayrıntı: (1) mercan kırmızısı, öne çıkan halka (simit) dudak, ortası derin koyu delik;
# (2) kafanın alt kenarı omuzlara sarkan 8 dolgun, yuvarlak jöle kıvrımından oluşan tek parça dalgalı etek.
#
# Kullanım:
#   python3.11 -I art/scripts/app_icon_code.py -- A            → art/icon_code/icon_A.png (A, B, C, D)
#   python3.11 -I art/scripts/app_icon_code.py -- A --preview  → hızlı küçük deneme (384 px, az örnek)
#   python3.11 -I art/scripts/app_icon_code.py -- A --out <yol.png> --samples 200 --res 1024 [--side]
#   python3    art/scripts/app_icon_code.py -- --sheet         → art/icon_code/sheet.png (PIL; 1024 + 120 + 60 px)
# Seçenekler: A = S'ye en yakın kompozisyon · B = yakın yüz (küçük boyda okunur) · C = daha uzun, daha saydam etek ·
#             D = iki dokunaç havada, neşeli.
import sys, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
OUTDIR = os.path.join(REPO, 'art', 'icon_code')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def _opt(name, default=None, cast=str):
    if name in ARGS:
        return cast(ARGS[ARGS.index(name) + 1])
    return default


# ---------------------------------------------------------------- iletişim sayfası (PIL, bpy gerekmez)
def contact_sheet():
    from PIL import Image, ImageDraw, ImageFont
    names = ['A', 'B', 'C', 'D']
    notes = {'A': "S'ye en yakın", 'B': 'Yakın yüz', 'C': 'Uzun, saydam etek', 'D': 'İki kol havada'}
    font_path = os.path.join(REPO, 'Assets/_Pofi/Resources/Fonts/Baloo2-ExtraBold.ttf')
    try:
        f_big = ImageFont.truetype(font_path, 40); f_small = ImageFont.truetype(font_path, 24)
    except Exception:
        f_big = f_small = ImageFont.load_default()

    def rounded(img, size):
        im = img.resize((size, size), Image.LANCZOS)
        k = 4
        m = Image.new('L', (size * k, size * k), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, size * k - 1, size * k - 1], radius=int(0.2237 * size * k), fill=255)
        m = m.resize((size, size), Image.LANCZOS)
        out = Image.new('RGBA', (size, size), (0, 0, 0, 0)); out.paste(im, (0, 0), m)
        return out

    cell, pad = 480, 36
    W = pad + len(names) * (cell + pad)
    H = pad + 60 + cell + 24 + 150 + pad
    sheet = Image.new('RGB', (W, H), (246, 242, 234))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        p = os.path.join(OUTDIR, f'icon_{n}.png')
        if not os.path.exists(p):
            continue
        img = Image.open(p).convert('RGB')
        x = pad + i * (cell + pad)
        d.text((x, pad), f'{n} — {notes[n]}', fill=(60, 50, 40), font=f_big)
        sheet.paste(rounded(img, cell), (x, pad + 60), rounded(img, cell))
        y = pad + 60 + cell + 24
        # ana ekran boyları: 120 px ve 60 px, açık ve koyu zemin üstünde
        for j, (bg, s) in enumerate([((250, 250, 250), 120), ((30, 32, 40), 120)]):
            bx = x + j * 140
            d.rounded_rectangle([bx, y, bx + 130, y + 130], 18, fill=bg)
            r = rounded(img, s); sheet.paste(r, (bx + 5, y + 5), r)
        bx = x + 290
        d.rounded_rectangle([bx, y, bx + 70, y + 70], 12, fill=(250, 250, 250))
        r = rounded(img, 60); sheet.paste(r, (bx + 5, y + 5), r)
        d.rounded_rectangle([bx + 80, y, bx + 150, y + 70], 12, fill=(30, 32, 40))
        sheet.paste(r, (bx + 85, y + 5), r)
        d.text((bx, y + 82), '120 / 60 px', fill=(110, 100, 90), font=f_small)
    sheet.save(os.path.join(OUTDIR, 'sheet.png'))
    print('sheet ->', os.path.join(OUTDIR, 'sheet.png'))


if '--sheet' in ARGS:
    contact_sheet()
    sys.exit(0)

# ---------------------------------------------------------------- Blender sahnesi
import bpy  # noqa: E402  (bmesh'ten önce)
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

VAR = next((a for a in ARGS if a in ('A', 'B', 'C', 'D')), 'A')
PREVIEW = '--preview' in ARGS
SIDE = '--side' in ARGS          # yandan/üç çeyrek denetim çekimi (etek biçimi)
RES = _opt('--res', 384 if PREVIEW else 1024, int)
SAMPLES = _opt('--samples', 40 if PREVIEW else 220, int)
OUT = _opt('--out', os.path.join(OUTDIR, f'icon_{VAR}.png'))

# Seçenek ayarları. Dünya birimi: kafa yarıçapı = 1. Kafa merkezi (0, 0, 0); kamera -Y'den +Y'ye bakar.
VARIANTS = {
    # frame: kadraj genişliği (karakter düzleminde), cx/cz: kadraj merkezi, yaw/roll: kafa dönüşü (derece)
    'A': dict(frame=3.95, cx=0.03, cz=-0.40, yaw=11, roll=0, arms='wave', droop=1.0, trans=0.0,
              palms=True, light=True, sea=0.155, sun=(0.60, 0.42), brow_up=0.0),
    'B': dict(frame=3.00, cx=0.08, cz=-0.20, yaw=8, roll=0, arms='wave_close', droop=1.0, trans=0.0,
              palms=True, light=True, sea=0.03, sun=(0.62, 0.40), brow_up=0.0),
    'C': dict(frame=3.95, cx=0.0, cz=-0.42, yaw=-10, roll=0, arms='wave_left', droop=1.45, trans=1.0,
              palms=True, light=True, sea=0.12, sun=(0.42, 0.42), brow_up=0.0),
    'D': dict(frame=4.20, cx=0.0, cz=-0.28, yaw=0, roll=-5, arms='both', droop=1.1, trans=0.0,
              palms=True, light=True, sea=0.135, sun=(0.50, 0.45), brow_up=0.04),
}
CFG = VARIANTS[VAR]
LENS = 80.0
F = CFG['frame']
DIST = F * LENS / 36.0           # kamera uzaklığı: kadraj genişliği = 36/80 × uzaklık
CX, CZ = CFG['cx'], CFG['cz']
YB = 6.5                         # arka perde derinliği


def img_to_world(u, v, y):
    """Kadraj koordinatı (u: soldan 0..1, v: alttan 0..1) + derinlik y → dünya (x, z)."""
    k = (DIST + y) / DIST
    return CX + (u - 0.5) * F * k, CZ + (v - 0.5) * F * k


def depth_scale(y):
    return (DIST + y) / DIST


def srgb(c):
    c = np.asarray(c, dtype=np.float64)
    c = c / (255.0 if c.max() > 1.0 else 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin(*c):
    v = srgb(c)
    return (float(v[0]), float(v[1]), float(v[2]), 1.0)


# ---------------------------------------------------------------- sahne
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.015
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 10
sc.cycles.diffuse_bounces = 3
sc.cycles.glossy_bounces = 4
sc.cycles.transmission_bounces = 8
sc.cycles.transparent_max_bounces = 8
sc.cycles.sample_clamp_indirect = 6.0
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
try:
    sc.render.threads_mode = 'AUTO'
except Exception:
    pass

world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(255, 204, 156)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.22


def link(o):
    sc.collection.objects.link(o)
    return o


def new_obj(name, me):
    return link(bpy.data.objects.new(name, me))


# ---------------------------------------------------------------- malzemeler
def principled(name, base, rough=0.5, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = base
    b.inputs['Roughness'].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m, b


def node(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def ramp(nt, stops):
    r = nt.nodes.new('ShaderNodeValToRGB')
    el = r.color_ramp.elements
    el[0].position, el[0].color = stops[0]
    el[1].position, el[1].color = stops[-1]
    for pos, col in stops[1:-1]:
        e = el.new(pos); e.color = col
    return r


def jelly_material(name, trans=0.0, blush=None):
    """Parlak, hafif içten ışıklı açık mavi jöle (vinil oyuncak). trans>0: etek bölgesi saydamlaşır."""
    m, b = principled(name, lin(118, 182, 238), 0.26)
    nt = m.node_tree; L = nt.links
    b.inputs['Subsurface Weight'].default_value = 0.45
    b.inputs['Subsurface Radius'].default_value = (0.35, 0.7, 1.0)
    b.inputs['Subsurface Scale'].default_value = 0.22
    b.inputs['Coat Weight'].default_value = 1.0
    b.inputs['Coat Roughness'].default_value = 0.035
    b.inputs['Coat IOR'].default_value = 1.45
    b.inputs['Specular IOR Level'].default_value = 0.45
    tc = node(nt, 'ShaderNodeTexCoord')
    sep = node(nt, 'ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    # dikey ton: tepe açık camgöbeği, alt daha doygun mavi
    g = ramp(nt, [(0.0, lin(78, 148, 226)), (0.42, lin(116, 182, 240)), (0.78, lin(148, 210, 250)), (1.0, lin(168, 224, 252))])
    mr = node(nt, 'ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1.1; mr.inputs['From Max'].default_value = 1.0
    L.new(sep.outputs['Z'], mr.inputs['Value']); L.new(mr.outputs['Result'], g.inputs['Fac'])
    col = g.outputs['Color']
    if blush:
        # iki yumuşak yanak lekesi (kafa yerel koordinatında)
        dmin = None
        for p in blush:
            sub = node(nt, 'ShaderNodeVectorMath', operation='SUBTRACT')
            L.new(tc.outputs['Object'], sub.inputs[0]); sub.inputs[1].default_value = p
            sc_ = node(nt, 'ShaderNodeVectorMath', operation='MULTIPLY')
            L.new(sub.outputs[0], sc_.inputs[0]); sc_.inputs[1].default_value = (1.0, 1.0, 1.45)
            ln = node(nt, 'ShaderNodeVectorMath', operation='LENGTH'); L.new(sc_.outputs[0], ln.inputs[0])
            if dmin is None:
                dmin = ln.outputs['Value']
            else:
                mn = node(nt, 'ShaderNodeMath', operation='MINIMUM')
                L.new(dmin, mn.inputs[0]); L.new(ln.outputs['Value'], mn.inputs[1]); dmin = mn.outputs[0]
        br = ramp(nt, [(0.0, (0.85, 0.85, 0.85, 1)), (0.5, (0.6, 0.6, 0.6, 1)), (1.0, (0, 0, 0, 1))])
        mr2 = node(nt, 'ShaderNodeMapRange'); mr2.inputs['From Min'].default_value = 0.0; mr2.inputs['From Max'].default_value = 0.2
        L.new(dmin, mr2.inputs['Value']); L.new(mr2.outputs['Result'], br.inputs['Fac'])
        mix = node(nt, 'ShaderNodeMix', data_type='RGBA')
        L.new(br.outputs['Color'], mix.inputs['Factor'])
        L.new(col, mix.inputs['A']); mix.inputs['B'].default_value = lin(255, 120, 140)
        col = mix.outputs['Result']
        # pembede alt yüzey saçılması bastırılır (renk mavide kaybolmasın)
        inv = node(nt, 'ShaderNodeMath', operation='MULTIPLY'); inv.inputs[1].default_value = -0.35
        L.new(br.outputs['Color'], inv.inputs[0])
        add = node(nt, 'ShaderNodeMath', operation='ADD'); add.inputs[1].default_value = 0.35
        L.new(inv.outputs[0], add.inputs[0]); L.new(add.outputs[0], b.inputs['Subsurface Weight'])
    L.new(col, b.inputs['Base Color'])
    lw = node(nt, 'ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    rim = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.55, (0, 0, 0, 1)), (1.0, lin(150, 225, 255))])
    L.new(lw.outputs['Facing'], rim.inputs['Fac']); L.new(rim.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 0.35
    if trans > 0:
        # etek (z < -0.42 → -0.85) ışığı içinden geçiren, daha açık ve camsı jöle:
        # açık camgöbeği renk + güçlü alt yüzey saçılması + biraz geçirgenlik + çok hafif mavi soğurma
        t = ramp(nt, [(0.0, (0, 0, 0, 1)), (1.0, (1, 1, 1, 1))])
        mr3 = node(nt, 'ShaderNodeMapRange'); mr3.inputs['From Min'].default_value = -0.40; mr3.inputs['From Max'].default_value = -0.90
        L.new(sep.outputs['Z'], mr3.inputs['Value']); L.new(mr3.outputs['Result'], t.inputs['Fac'])
        mul = node(nt, 'ShaderNodeMath', operation='MULTIPLY'); mul.inputs[1].default_value = 0.35 * trans
        L.new(t.outputs['Color'], mul.inputs[0]); L.new(mul.outputs[0], b.inputs['Transmission Weight'])
        lite = node(nt, 'ShaderNodeMix', data_type='RGBA')
        lm = node(nt, 'ShaderNodeMath', operation='MULTIPLY'); lm.inputs[1].default_value = 0.55 * trans
        L.new(t.outputs['Color'], lm.inputs[0]); L.new(lm.outputs[0], lite.inputs['Factor'])
        L.new(col, lite.inputs['A']); lite.inputs['B'].default_value = lin(170, 228, 255)
        L.new(lite.outputs['Result'], b.inputs['Base Color'])
        b.inputs['Subsurface Scale'].default_value = 0.4
        b.inputs['IOR'].default_value = 1.33
        b.inputs['Emission Strength'].default_value = 0.6
        vol = node(nt, 'ShaderNodeVolumeAbsorption')
        vol.inputs['Color'].default_value = lin(185, 230, 255); vol.inputs['Density'].default_value = 0.25
        L.new(vol.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    return m


def emission_material(name, color, strength=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = color; e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def np_image(name, arr):
    """arr: H×W×3|4 doğrusal float, satır 0 = alt."""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1))], axis=2)
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())   # renk uzayı değiştirilmez: görüntü yeniden üretilip silinir
    img.pack()
    return img


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- geometri yardımcıları
def catmull(pts, n_per_seg):
    P = [np.array(p, dtype=np.float64) for p in pts]
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(n_per_seg):
            t = j / n_per_seg; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def resample(C, M):
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], M)
    return np.stack([np.interp(t, s, C[:, k]) for k in range(C.shape[1])], axis=1), s[-1]


def mesh_from(name, verts, faces, uv=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    if uv is not None:
        lay = me.uv_layers.new(name='UVMap')
        for li, l in enumerate(me.loops):
            lay.data[li].uv = uv[l.vertex_index]
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def sweep(name, pts, radius_fn, K=36, M=140, ref=(0, 0, 1), flat=1.0, cap_end=True, cap_start=True, normal_dirs=None):
    """Merkez eğrisi boyunca daire (ya da basık elips) süpürür; uçlar yarım küre kapak.
    radius_fn(t) t∈[0,1]. flat: N yönündeki yarıçap çarpanı. Döner: obj, (C, T, N, B, r) örnekleri."""
    C = catmull(pts, 12)
    C, length = resample(C, M)
    T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.zeros_like(C); B = np.zeros_like(C)
    if normal_dirs is not None:
        for i in range(M):
            n = np.array(normal_dirs[i], dtype=float); n = n - n.dot(T[i]) * T[i]; N[i] = n / np.linalg.norm(n)
            B[i] = np.cross(T[i], N[i])
    else:
        r0 = np.array(ref, dtype=float); n = r0 - r0.dot(T[0]) * T[0]
        if np.linalg.norm(n) < 1e-4:
            n = np.array([1.0, 0, 0]) - T[0][0] * T[0]
        N[0] = n / np.linalg.norm(n); B[0] = np.cross(T[0], N[0])
        for i in range(1, M):
            n = N[i - 1] - N[i - 1].dot(T[i]) * T[i]; N[i] = n / np.linalg.norm(n); B[i] = np.cross(T[i], N[i])
    ts = np.linspace(0, 1, M)
    R = np.array([radius_fn(t) for t in ts])
    verts, uvs = [], []
    ang = np.linspace(0, 2 * np.pi, K, endpoint=False)
    rings = []
    for i in range(M):
        ring = []
        for a in ang:
            p = C[i] + R[i] * (np.cos(a) * N[i] * flat + np.sin(a) * B[i])
            ring.append(len(verts)); verts.append(p); uvs.append((a / (2 * np.pi), ts[i] * length))
        rings.append(ring)
    faces = []
    for i in range(M - 1):
        for j in range(K):
            a, b_ = rings[i][j], rings[i][(j + 1) % K]
            c, d = rings[i + 1][(j + 1) % K], rings[i + 1][j]
            faces.append((a, b_, c, d))

    def cap(idx, sign):
        prev = rings[idx]
        steps = 7
        for s in range(1, steps):
            be = s / steps * np.pi / 2
            ring = []
            for a in ang:
                p = C[idx] + sign * T[idx] * R[idx] * np.sin(be) + R[idx] * np.cos(be) * (np.cos(a) * N[idx] * flat + np.sin(a) * B[idx])
                ring.append(len(verts)); verts.append(p); uvs.append((a / (2 * np.pi), 0))
            for j in range(K):
                faces.append((prev[j], prev[(j + 1) % K], ring[(j + 1) % K], ring[j]))
            prev = ring
        tip = len(verts); verts.append(C[idx] + sign * T[idx] * R[idx]); uvs.append((0.5, 0))
        for j in range(K):
            faces.append((prev[j], prev[(j + 1) % K], tip))

    if cap_end:
        cap(M - 1, 1.0)
    if cap_start:
        cap(0, -1.0)
    me = mesh_from(name, verts, faces, uv=uvs)
    return new_obj(name, me), (C, T, N, B, R)


def add_subsurf(o, lv=1):
    m = o.modifiers.new('sub', 'SUBSURF'); m.levels = lv; m.render_levels = lv
    return m


def orient(o, loc, z_axis, x_hint=(1, 0, 0)):
    z = Vector(z_axis).normalized()
    x = Vector(x_hint); x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector(loc)
    o.matrix_world = M


def uv_sphere(name, r=1.0, seg=64, rings=32):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return new_obj(name, me)


def torus(name, R, r, seg=72, sseg=32):
    verts, faces = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for j in range(sseg):
            b = 2 * math.pi * j / sseg
            verts.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    for i in range(seg):
        for j in range(sseg):
            faces.append((i * sseg + j, i * sseg + (j + 1) % sseg, ((i + 1) % seg) * sseg + (j + 1) % sseg, ((i + 1) % seg) * sseg + j))
    return new_obj(name, mesh_from(name, verts, faces))


# ---------------------------------------------------------------- kafa: kubbe + 8 dolgun jöle kıvrımı (tek parça)
def head_profile(m, L):
    """Bir boylam (ρ, z): tepe → ekvator → etek dış karnı → kıvrım ucu → altta içe kıvrılıp boyna.
    m: kıvrım payı (1 = kıvrım ortası, 0 = iki kıvrım arası oluk). L: sarkma çarpanı."""
    return [
        (0.00, 0.99),
        (0.45, 0.90),
        (0.80, 0.65),
        (0.975, 0.29),
        (1.00, -0.05),
        (0.985, -0.30),
        (0.955 + 0.045 * m, -0.49 - 0.05 * m * L),
        (0.905 + 0.105 * m, -0.635 - 0.15 * m * L),
        (0.805 + 0.10 * m, -0.725 - 0.23 * m * L),
        (0.675 + 0.075 * m, -0.755 - 0.265 * m * L),
        (0.565 + 0.035 * m, -0.715 - 0.20 * m * L),
        (0.48, -0.64 - 0.085 * m * L),
        (0.34, -0.575),
        (0.17, -0.55),
        (0.00, -0.545),
    ]


def build_head(n_lobes=8, L=1.0, front='lobe', q=0.55, nphi=256, nseg=10, sx=1.08, sy=1.0):
    prof0 = np.array(head_profile(0, L)); prof1 = np.array(head_profile(1, L))
    C0 = catmull(prof0, nseg); C1 = catmull(prof1, nseg)
    nu = len(C0)
    verts, faces = [], []
    top = 0; verts.append((0, 0, C0[0][1]))
    ring_idx = []
    for k in range(nphi):
        phi = 2 * math.pi * k / nphi            # 0 = önden (-Y)
        th = n_lobes * phi / 2 + (math.pi / 2 if front == 'valley' else 0.0)
        m = abs(math.cos(th)) ** q          # q < 1: yarım daire gibi dolgun, geniş kıvrım; aralarda keskin oluk
        Cm = C0 + m * (C1 - C0)
        dx, dy = math.sin(phi), -math.cos(phi)
        col = []
        for i in range(1, nu - 1):
            rho, z = Cm[i]
            col.append(len(verts)); verts.append((rho * dx * sx, rho * dy * sy, z))
        ring_idx.append(col)
    bot = len(verts); verts.append((0, 0, C0[-1][1]))
    nr = nu - 2
    for k in range(nphi):
        a, b_ = ring_idx[k], ring_idx[(k + 1) % nphi]
        faces.append((top, b_[0], a[0]))
        for i in range(nr - 1):
            faces.append((a[i], b_[i], b_[i + 1], a[i + 1]))
        faces.append((a[nr - 1], b_[nr - 1], bot))
    me = mesh_from('head', verts, faces)
    return new_obj('head', me)


# ---------------------------------------------------------------- arka perde dokusu (numpy): gün doğumu ışınları
def sky_texture(n=1600, sun=(0.6, 0.42), sea_v=0.09, margin=1.12, seed=3):
    rng = np.random.default_rng(seed)
    j, i = np.meshgrid(np.arange(n), np.arange(n))
    u = ((j + 0.5) / n - 0.5) * margin + 0.5
    v = ((i + 0.5) / n - 0.5) * margin + 0.5
    dx, dy = u - sun[0], v - sun[1]
    r = np.sqrt(dx * dx + dy * dy)
    stops = [(0.00, (255, 250, 226)), (0.12, (255, 238, 178)), (0.26, (255, 214, 128)), (0.45, (255, 192, 96)),
             (0.70, (252, 170, 76)), (1.00, (246, 150, 62))]
    pos = np.array([s[0] for s in stops]); cols = np.array([s[1] for s in stops], dtype=np.float64)
    rr = np.clip(r, 0, 1)
    rgb = np.stack([np.interp(rr, pos, cols[:, k]) for k in range(3)], axis=2)
    # ışın yelpazesi: yumuşak kenarlı, merkezde ve kenarda solar
    a = np.arctan2(dy, dx)
    nr = 9
    w = np.sin(a * nr + 0.35)
    rays = smoothstep(-0.15, 0.25, w) * smoothstep(0.08, 0.30, r) * (1 - 0.55 * smoothstep(0.55, 1.1, r))
    ray_col = np.array([255, 238, 196], dtype=np.float64)
    rgb = rgb + (ray_col - rgb) * (0.34 * rays)[..., None]
    rgb *= (1 - 0.05 * (1 - rays) * smoothstep(0.1, 0.5, r))[..., None]   # ışın araları bir tık koyu
    # ufukta parlak sıcak bant
    hz = np.exp(-((v - sea_v - 0.02) / 0.07) ** 2)
    rgb = rgb + (np.array([255, 240, 200.0]) - rgb) * (0.45 * hz)[..., None]
    # yumuşak bulut kümeleri (ufuk üstü, iki yanda)
    cloud = np.zeros_like(u)
    for cxu, cyv, rad in [(0.08, sea_v + 0.10, 0.08), (0.17, sea_v + 0.07, 0.07), (0.01, sea_v + 0.06, 0.06),
                          (0.80, sea_v + 0.10, 0.075), (0.90, sea_v + 0.13, 0.085), (0.99, sea_v + 0.08, 0.07),
                          (0.71, sea_v + 0.06, 0.055)]:
        d = np.sqrt(((u - cxu) / 1.25) ** 2 + (v - cyv) ** 2)
        cloud = np.maximum(cloud, smoothstep(rad, rad * 0.55, d))
    cloud *= smoothstep(sea_v - 0.01, sea_v + 0.03, v)
    rgb = rgb + (np.array([255, 233, 196.0]) - rgb) * (0.55 * cloud)[..., None]
    # köşelerde hafif koyulaşma (odak)
    vig = np.sqrt((u - 0.5) ** 2 + (v - 0.55) ** 2)
    rgb *= (1 - 0.16 * smoothstep(0.45, 0.85, vig))[..., None]
    rgb += rng.normal(0, 0.6, rgb.shape)   # bantlaşmayı önleyen çok hafif tane
    return srgb(np.clip(rgb, 0, 255) / 255.0)


def eye_texture(n=512):
    j, i = np.meshgrid(np.arange(n), np.arange(n))
    x = (j + 0.5) / n * 2 - 1; y = (i + 0.5) / n * 2 - 1
    ix, iy, ir = 0.0, 0.05, 0.90
    d = np.sqrt((x - ix) ** 2 + (y - iy) ** 2) / ir
    sclera = np.array([248, 249, 253.0])
    top = np.array([16, 22, 52.0]); bottom = np.array([64, 146, 226.0])
    f = smoothstep(0.25, -1.0, (y - iy) / ir)  # alta doğru açılan mavi (yumuşak hilal)
    f = f * smoothstep(0.30, 1.0, d) ** 0.8
    iris = top + (bottom - top) * f[..., None]
    pupil = np.array([8, 10, 24.0])
    col = iris.copy()
    col = col + (pupil - col) * smoothstep(0.56, 0.48, d)[..., None]
    rim = np.array([10, 16, 40.0])
    col = col + (rim - col) * smoothstep(0.86, 0.97, d)[..., None]
    col = col + (sclera - col) * smoothstep(0.985, 1.02, d)[..., None]
    return srgb(np.clip(col, 0, 255) / 255.0)


# ================================================================ KURULUM
head = build_head(L=CFG['droop'], front='lobe')
head_bvh = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())


def surf(x, z, y0=-5.0):
    hit = head_bvh.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)))
    if hit[0] is None:
        raise RuntimeError(f'yüzey yok: {x},{z}')
    return Vector(hit[0]), Vector(hit[1]).normalized()


head_parts = [head]

# --- gözler
eye_img = np_image('eye_tex', eye_texture())
EYE_X, EYE_Z, EYE_W, EYE_H = 0.43, -0.04, 0.245, 0.285


def eye_material():
    m, b = principled('eye', (1, 1, 1, 1), 0.08)
    nt = m.node_tree; L = nt.links
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
    b.inputs['Specular IOR Level'].default_value = 0.6
    tc = node(nt, 'ShaderNodeTexCoord')
    mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.5, 0.5, 1); mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    tx = node(nt, 'ShaderNodeTexImage'); tx.image = eye_img; tx.extension = 'EXTEND'
    L.new(tc.outputs['Object'], mp.inputs[0]); L.new(mp.outputs[0], tx.inputs[0]); L.new(tx.outputs['Color'], b.inputs['Base Color'])
    return m


M_EYE = eye_material()
M_NAVY, _ = principled('navy', lin(28, 52, 110), 0.3, **{'Coat Weight': 0.8, 'Coat Roughness': 0.06})
M_SOCKET, _ = principled('socket', lin(22, 36, 82), 0.35, **{'Coat Weight': 0.6, 'Coat Roughness': 0.1})
M_SPARK = emission_material('spark', (1, 1, 1, 1), 4.0)

for s in (-1, 1):
    p, n = surf(s * EYE_X, EYE_Z)
    # koyu göz çukuru kenarı (üstte daha kalın)
    sock = uv_sphere(f'socket{s}', 1.0)
    orient(sock, p + n * 0.0 + Vector((0, 0, 0.014)), n)
    sock.scale = (EYE_W + 0.03, EYE_H + 0.036, 0.035)
    sock.data.materials.append(M_SOCKET)
    eye = uv_sphere(f'eye{s}', 1.0)
    orient(eye, p + n * (-0.01), n)
    eye.scale = (EYE_W, EYE_H, 0.115)
    eye.data.materials.append(M_EYE)
    bpy.context.view_layer.update()
    Mw = eye.matrix_world.copy()
    # parıltılar: büyük sağ üst, küçük sol alt
    for (ex, ey, rr) in [(0.30, 0.34, 0.25), (-0.30, -0.30, 0.11)]:
        zz = math.sqrt(max(0.0, 1 - ex * ex - ey * ey))
        lp = Mw @ Vector((ex, ey, zz * 1.05))
        sp = uv_sphere(f'spark{s}{ex}', 1.0, 24, 12)
        nrm = (Mw.to_quaternion() @ Vector((ex / EYE_W, ey / EYE_H, zz / 0.115))).normalized()
        orient(sp, lp, nrm)
        sp.scale = (rr * EYE_W, rr * EYE_W, 0.012)
        sp.data.materials.append(M_SPARK)
        sp.visible_shadow = False
        head_parts.append(sp)
    head_parts += [sock, eye]

# --- kaşlar: kısa, yuvarlak uçlu, iç uç biraz yukarıda
for s in (-1, 1):
    pts = []
    for t in np.linspace(0, 1, 7):          # t = 0 iç uç (burna yakın), t = 1 dış uç
        x = s * (EYE_X - 0.08 + 0.17 * t)
        z = 0.375 + CFG['brow_up'] + 0.03 * math.sin(math.pi * t) + 0.028 * (1 - t)
        p, n = surf(x, z)
        pts.append(tuple(p + n * 0.012))
    C = catmull(pts, 12); C, _ = resample(C, 60)
    ndirs = [tuple(surf(c[0], c[2])[1]) for c in C]
    brow, _ = sweep(f'brow{s}', pts, lambda t: 0.042 * (0.6 + 0.4 * math.sin(math.pi * t) ** 0.5), K=20, M=60,
                    flat=0.55, normal_dirs=ndirs)
    brow.data.materials.append(M_NAVY)
    head_parts.append(brow)

# --- halka dudak (simit) + derin koyu delik
MOUTH_Z = -0.335
p, n = surf(0.0, MOUTH_Z)
mdir = (n + Vector((0, -0.25, -0.12))).normalized()
LIP_R, LIP_r = 0.146, 0.08
lips = torus('lips', LIP_R, LIP_r, 72, 36)
orient(lips, p + mdir * (LIP_r * 0.95), mdir)
lips.scale = (1.06, 0.98, 1.0)
M_LIP, blip = principled('lip', lin(240, 88, 74), 0.22, **{'Coat Weight': 1.0, 'Coat Roughness': 0.04,
                                                          'Subsurface Weight': 0.15, 'Subsurface Scale': 0.05})
nt = M_LIP.node_tree
ao = node(nt, 'ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.12; ao.samples = 16
aor = ramp(nt, [(0.0, lin(70, 10, 14)), (0.55, lin(200, 60, 52)), (1.0, lin(244, 96, 80))])
nt.links.new(ao.outputs['AO'], aor.inputs['Fac']); nt.links.new(aor.outputs['Color'], blip.inputs['Base Color'])
lips.data.materials.append(M_LIP)
throat = uv_sphere('throat', 1.0, 32, 16)
orient(throat, p - mdir * 0.02, mdir)
throat.scale = (LIP_R * 1.1, LIP_R * 1.05, 0.036)
M_THROAT, _ = principled('throat', lin(46, 6, 12), 0.6)
throat.data.materials.append(M_THROAT)
head_parts += [lips, throat]

# --- yanak pembesi (kafa malzemesinde)
blush_pts = [tuple(surf(s * 0.63, -0.27)[0]) for s in (-1, 1)]
M_JELLY_HEAD = jelly_material('jelly_head', trans=CFG['trans'], blush=blush_pts)
M_JELLY = jelly_material('jelly')
head.data.materials.append(M_JELLY_HEAD)
add_subsurf(head, 1)

# kafa kökü: dönüş (yaw/roll) yalnız kafa ve yüzü etkiler
root = bpy.data.objects.new('head_root', None); link(root)
for o in head_parts:
    o.parent = root
root.rotation_euler = (0, math.radians(CFG['roll']), math.radians(CFG['yaw']))
# mavi jöle kafa, sarı tişörte yeşilimsi yansıyan ışık saçmasın (gölgeler sıcak kalsın)
head.visible_diffuse = False

# ---------------------------------------------------------------- gövde: sarı tişört (yumuşak kumaş)
def superellipse_ring(a, b, z, n=2.6, K=96, y0=0.0):
    pts = []
    for k in range(K):
        t = 2 * math.pi * k / K
        c, s_ = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / n), c), y0 + b * math.copysign(abs(s_) ** (2 / n), s_), z))
    return pts


def build_shirt():
    prof = [(-0.40, 0.24, 0.21), (-0.52, 0.40, 0.32), (-0.66, 0.60, 0.43), (-0.80, 0.735, 0.49), (-0.95, 0.79, 0.515),
            (-1.15, 0.80, 0.52), (-1.35, 0.80, 0.52), (-1.45, 0.805, 0.525), (-1.50, 0.825, 0.535), (-1.57, 0.82, 0.53),
            (-1.61, 0.74, 0.47), (-1.635, 0.5, 0.32), (-1.645, 0.2, 0.13)]
    K = 96
    verts, faces = [], []
    rings = []
    for z, a, b in prof:
        ring = []
        for p in superellipse_ring(a, b, z, 2.7, K, y0=0.03):
            ring.append(len(verts)); verts.append(p)
        rings.append(ring)
    for r in range(len(rings) - 1):
        for k in range(K):
            faces.append((rings[r][k], rings[r][(k + 1) % K], rings[r + 1][(k + 1) % K], rings[r + 1][k]))
    t0 = len(verts); verts.append((0, 0.03, prof[0][0] + 0.02))
    t1 = len(verts); verts.append((0, 0.03, prof[-1][0] - 0.005))
    for k in range(K):
        faces.append((rings[0][(k + 1) % K], rings[0][k], t0))
        faces.append((rings[-1][k], rings[-1][(k + 1) % K], t1))
    torso = new_obj('torso', mesh_from('torso', verts, faces))
    parts = [torso]
    for s in (-1, 1):
        a = Vector((s * 0.46, 0.03, -0.80)); e = Vector((s * 1.12, -0.02, -1.17))
        sl, _ = sweep(f'sleeve{s}', [tuple(a), tuple(a.lerp(e, 0.5) + Vector((0, 0, 0.02))), tuple(e)],
                      lambda t: 0.255 - 0.02 * t, K=48, M=40)
        parts.append(sl)
        cuff = torus(f'cuff{s}', 0.235, 0.032, 72, 20)
        orient(cuff, e - (e - a).normalized() * 0.03, (e - a).normalized())
        parts.append(cuff)
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = torso
    bpy.ops.object.join()
    rm = torso.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.014 if not PREVIEW else 0.022
    bpy.ops.object.modifier_apply(modifier='rm')
    sm = torso.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6
    bpy.ops.object.modifier_apply(modifier='sm')
    tex = bpy.data.textures.new('folds', 'CLOUDS'); tex.noise_scale = 0.32; tex.noise_depth = 1
    dp = torso.modifiers.new('dp', 'DISPLACE'); dp.texture = tex; dp.strength = 0.022; dp.mid_level = 0.5
    for p in torso.data.polygons:
        p.use_smooth = True
    return torso


bpy.ops.object.select_all(action='DESELECT')
shirt = build_shirt()
M_SHIRT, bs = principled('shirt', lin(246, 184, 32), 0.78, **{'Sheen Weight': 0.7, 'Sheen Roughness': 0.45,
                                                            'Specular IOR Level': 0.25})
bs.inputs['Sheen Tint'].default_value = lin(255, 240, 190)
nt = M_SHIRT.node_tree
tcs = node(nt, 'ShaderNodeTexCoord')
nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 420.0; nz.inputs['Detail'].default_value = 2.0
bump = node(nt, 'ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.22; bump.inputs['Distance'].default_value = 0.0015
nt.links.new(tcs.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
# kumaşta hafif ton oynaması (sıcak gölge)
sepS = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(tcs.outputs['Object'], sepS.inputs[0])
sr = ramp(nt, [(0.0, lin(242, 188, 40)), (1.0, lin(255, 218, 72))])
mrS = node(nt, 'ShaderNodeMapRange'); mrS.inputs['From Min'].default_value = -1.75; mrS.inputs['From Max'].default_value = -0.7
nt.links.new(sepS.outputs['Z'], mrS.inputs['Value']); nt.links.new(mrS.outputs['Result'], sr.inputs['Fac'])
aoS = node(nt, 'ShaderNodeAmbientOcclusion'); aoS.inputs['Distance'].default_value = 0.35; aoS.samples = 12
warm = node(nt, 'ShaderNodeMix', data_type='RGBA')
inv = node(nt, 'ShaderNodeMath', operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
nt.links.new(aoS.outputs['AO'], inv.inputs[1])
mulS = node(nt, 'ShaderNodeMath', operation='MULTIPLY'); mulS.inputs[1].default_value = 1.7
nt.links.new(inv.outputs[0], mulS.inputs[0]); mulS.use_clamp = True
nt.links.new(mulS.outputs[0], warm.inputs['Factor'])
nt.links.new(sr.outputs['Color'], warm.inputs['A']); warm.inputs['B'].default_value = lin(180, 84, 14)
nt.links.new(warm.outputs['Result'], bs.inputs['Base Color'])
shirt.data.materials.append(M_SHIRT)

# ---------------------------------------------------------------- dokunaçlar (kollar + bacak uçları)
M_SUCK = jelly_material('sucker')
M_SUCK.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.2


def tentacle(name, pts, r0, r1, suck_dir=None, n_suck=0, suck_range=(0.35, 0.92), bulb=1.0):
    def rf(t):
        base = r0 + (r1 - r0) * (t ** 0.9)
        return base * (1 + (bulb - 1) * smoothstep(0.75, 1.0, t))
    o, (C, T, N, B, R) = sweep(name, pts, rf, K=40, M=150)
    o.data.materials.append(M_JELLY)
    add_subsurf(o, 1)
    if suck_dir is not None and n_suck:
        W = np.array(suck_dir, dtype=float)
        for k in range(n_suck):
            t = suck_range[0] + (suck_range[1] - suck_range[0]) * k / max(1, n_suck - 1)
            i = int(t * (len(C) - 1))
            d = W - W.dot(T[i]) * T[i]; d /= np.linalg.norm(d)
            r = R[i]
            ring = torus(f'{name}_s{k}', 0.40 * r, 0.13 * r, 36, 16)
            orient(ring, tuple(C[i] + d * r * 0.93), tuple(d), x_hint=tuple(T[i]))
            ring.scale = (1.0, 1.15, 1.0)
            ring.data.materials.append(M_SUCK)
            dot = uv_sphere(f'{name}_d{k}', 1.0, 20, 10)
            orient(dot, tuple(C[i] + d * r * 0.90), tuple(d), x_hint=tuple(T[i]))
            dot.scale = (0.30 * r, 0.34 * r, 0.06 * r)
            dot.data.materials.append(M_SUCK)
    return o


arms = CFG['arms']
if arms in ('wave', 'wave_close', 'wave_left'):
    sgn = -1 if arms == 'wave_left' else 1
    up = [(0.80, 0.0, -1.0), (1.12, -0.04, -1.17), (1.34, -0.10, -1.10), (1.48, -0.15, -0.90), (1.54, -0.18, -0.64),
          (1.52, -0.20, -0.40), (1.44, -0.21, -0.24)]
    if arms == 'wave_close':   # yakın çekim: kol yüzün yanında, eteğin önünden kalkar
        up = [(0.80, 0.0, -1.0), (1.12, -0.04, -1.17), (1.24, -0.24, -1.06), (1.25, -0.42, -0.85), (1.19, -0.53, -0.64),
              (1.10, -0.58, -0.48), (1.00, -0.60, -0.39)]
    up = [(sgn * x, y, z) for x, y, z in up]
    sd_up = (sgn * 0.85, -0.45, 0.0) if arms != 'wave_close' else (0.5, -0.85, 0.0)
    tentacle('arm_up', up, 0.225, 0.125, suck_dir=sd_up, n_suck=5, suck_range=(0.38, 0.9), bulb=1.12)
    out = [(-0.80, 0.0, -1.0), (-1.12, -0.04, -1.18), (-1.28, -0.10, -1.31), (-1.42, -0.15, -1.36), (-1.53, -0.17, -1.30),
           (-1.58, -0.17, -1.17)]
    if arms == 'wave_close':   # öbür kol aşağı sarkar (kadraj dışına)
        out = [(-0.80, 0.0, -1.0), (-1.12, -0.04, -1.18), (-1.24, -0.12, -1.42), (-1.24, -0.16, -1.70), (-1.18, -0.16, -1.95)]
    if arms == 'wave_left':    # öbür kol rahat sarkar, ucu içe kıvrık (sağ alttaki fener görünsün)
        out = [(-0.80, 0.0, -1.0), (-1.12, -0.04, -1.18), (-1.25, -0.12, -1.40), (-1.28, -0.17, -1.62), (-1.21, -0.20, -1.80),
               (-1.08, -0.21, -1.86)]
    out = [(sgn * x, y, z) for x, y, z in out]
    sd_out = {'wave_close': None, 'wave_left': (sgn * 0.8, -0.6, 0.0)}.get(arms, (0.0, -0.55, -0.85))
    tentacle('arm_out', out, 0.225, 0.125, suck_dir=sd_out, n_suck=4, suck_range=(0.45, 0.9), bulb=1.1)
else:  # iki kol havada
    for s in (-1, 1):
        up = [(s * 0.80, 0.0, -1.0), (s * 1.12, -0.04, -1.17), (s * 1.33, -0.10, -1.04), (s * 1.45, -0.15, -0.78),
              (s * 1.48, -0.18, -0.48), (s * 1.50, -0.20, -0.20), (s * 1.57, -0.20, 0.02), (s * 1.68, -0.19, 0.11)]
        tentacle(f'arm{s}', up, 0.225, 0.125, suck_dir=(s * 0.85, -0.45, 0.0), n_suck=5, suck_range=(0.38, 0.9),
                 bulb=1.12)

# bacak dokunaçları (tişörtün altından dışa kıvrılıp suya girer)
legs = []
for k, (x, yy) in enumerate([(-0.56, 0.06), (-0.2, -0.16), (0.2, -0.16), (0.56, 0.06)]):
    sx_ = 1 if x > 0 else -1
    pts = [(x * 0.85, yy + 0.08, -1.35), (x * 0.98, yy - 0.02, -1.62), (x * 1.12 + sx_ * 0.04, yy - 0.08, -1.9),
           (x * 1.25 + sx_ * 0.08, yy - 0.1, -2.3)]
    o, leg = sweep(f'leg{k}', pts, lambda t: 0.215 - 0.05 * t, K=32, M=70)
    o.data.materials.append(M_JELLY); add_subsurf(o, 1)
    legs.append(leg)

# ---------------------------------------------------------------- deniz (eğik düzlem: ufku istenen yükseklikte tutar)
SEA_V = CFG['sea']
y_far, y_near = YB - 0.05, -6.0
_, z_far = img_to_world(0.5, SEA_V, y_far)
_, z_0 = img_to_world(0.5, SEA_V - 0.028, 0.0)     # karakterin durduğu derinlikte su çizgisi


def water_z(y):
    return z_0 + (z_far - z_0) * y / y_far


wv = []
for yy in (y_near, y_far):
    for xx in (-12, 12):
        wv.append((xx, yy, water_z(yy)))
sea = new_obj('sea', mesh_from('sea', [wv[0], wv[1], wv[3], wv[2]], [(0, 1, 2, 3)]))
M_SEA, bw = principled('sea', lin(6, 90, 110), 0.3, **{'Specular IOR Level': 0.0, 'Coat Weight': 0.0})
nt = M_SEA.node_tree
tcw = node(nt, 'ShaderNodeTexCoord')
mpw = node(nt, 'ShaderNodeMapping'); mpw.inputs['Scale'].default_value = (1.0, 7.0, 1.0)
nzw = node(nt, 'ShaderNodeTexNoise'); nzw.inputs['Scale'].default_value = 2.2; nzw.inputs['Detail'].default_value = 6.0
bmp = node(nt, 'ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.35; bmp.inputs['Distance'].default_value = 0.02
nt.links.new(tcw.outputs['Object'], mpw.inputs[0]); nt.links.new(mpw.outputs[0], nzw.inputs['Vector'])
nt.links.new(nzw.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], bw.inputs['Normal'])
sepw = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(tcw.outputs['Object'], sepw.inputs[0])
wr = ramp(nt, [(0.0, lin(8, 150, 168)), (0.6, lin(26, 190, 196)), (1.0, lin(110, 222, 214))])
mrw = node(nt, 'ShaderNodeMapRange'); mrw.inputs['From Min'].default_value = y_near; mrw.inputs['From Max'].default_value = y_far
nt.links.new(sepw.outputs['Y'], mrw.inputs['Value']); nt.links.new(mrw.outputs['Result'], wr.inputs['Fac'])
nt.links.new(wr.outputs['Color'], bw.inputs['Emission Color']); bw.inputs['Emission Strength'].default_value = 0.9
sea.data.materials.append(M_SEA)
sea.visible_glossy = False
sea.visible_diffuse = False   # turkuaz ışıma tişörtü yeşile boyamasın

# bacakların suya girdiği yerde köpük halkası
M_FOAM = bpy.data.materials.new('foam'); M_FOAM.use_nodes = True
_bf = M_FOAM.node_tree.nodes['Principled BSDF']
_bf.inputs['Base Color'].default_value = lin(235, 252, 250); _bf.inputs['Roughness'].default_value = 0.5
_bf.inputs['Emission Color'].default_value = lin(215, 250, 245); _bf.inputs['Emission Strength'].default_value = 0.45
_wn = Vector((0.0, -(z_far - z_0) / y_far, 1.0)).normalized()
for k, (C, T, N, B, R) in enumerate(legs):
    dz = np.array([c[2] - water_z(c[1]) for c in C])
    i = int(np.argmin(np.abs(dz)))
    if abs(dz[i]) > 0.05:
        continue
    for j, (sc_r, th) in enumerate([(1.28, 0.03), (1.75, 0.018)]):
        ring = torus(f'foam{k}_{j}', R[i] * sc_r, th, 64, 12)
        orient(ring, tuple(C[i]) if j == 0 else tuple(np.array(C[i]) + np.array([0, 0, -0.01])), tuple(_wn))
        ring.scale = (1.0, 1.0, 0.35)
        ring.data.materials.append(M_FOAM)
        ring.visible_shadow = False

# su parıltıları (dört köşeli yıldız)
M_STAR = emission_material('star', (1, 1, 0.96, 1), 3.0)


def star(name, loc, size):
    vs, fs = [(0, 0, 0)], []
    K = 8
    for k in range(K):
        a = 2 * math.pi * k / K
        rr = size if k % 2 == 0 else size * 0.16
        vs.append((rr * math.cos(a), 0, rr * math.sin(a)))
    for k in range(K):
        fs.append((0, 1 + k, 1 + (k + 1) % K))
    o = new_obj(name, mesh_from(name, vs, fs))
    o.location = loc
    o.data.materials.append(M_STAR)
    o.visible_shadow = False
    return o


def water_point(u, v):
    """Kadrajda (u, v) noktasına düşen deniz yüzeyi noktası (derinlik ikiye bölme ile)."""
    lo, hi = y_near, y_far
    for _ in range(50):
        mid = (lo + hi) / 2
        vz = 0.5 + (water_z(mid) - CZ) / (F * depth_scale(mid))
        lo, hi = (mid, hi) if vz < v else (lo, mid)
    y = (lo + hi) / 2
    x, _ = img_to_world(u, v, y)
    return x, y, water_z(y)


for k, (u, v, s) in enumerate([(0.10, 0.62, 0.022), (0.25, 0.30, 0.014), (0.80, 0.55, 0.02), (0.92, 0.25, 0.013),
                               (0.70, 0.20, 0.011), (0.04, 0.22, 0.012), (0.33, 0.75, 0.01)]):
    x, y, z = water_point(u, v * SEA_V)
    star(f'star{k}', (x, y - 0.05, z + 0.01), s * F * depth_scale(y))

# ---------------------------------------------------------------- arka perde (gökyüzü dokusu, ışık yaymaz)
MARGIN = 1.12
sky = np_image('sky', sky_texture(1024 if PREVIEW else 1800, sun=CFG['sun'], sea_v=SEA_V, margin=MARGIN))
pw = F * depth_scale(YB) * MARGIN
bx, bz = CX, CZ
bd = new_obj('backdrop', mesh_from('backdrop', [(-pw / 2, 0, -pw / 2), (pw / 2, 0, -pw / 2), (pw / 2, 0, pw / 2), (-pw / 2, 0, pw / 2)],
                                   [(0, 1, 2, 3)], uv=[(0, 0), (1, 0), (1, 1), (0, 1)]))
bd.location = (bx, YB, bz)
M_SKY = bpy.data.materials.new('sky'); M_SKY.use_nodes = True
nt = M_SKY.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
em = nt.nodes.new('ShaderNodeEmission'); tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = sky; tx.extension = 'EXTEND'
uvn = nt.nodes.new('ShaderNodeUVMap')
nt.links.new(uvn.outputs[0], tx.inputs[0]); nt.links.new(tx.outputs['Color'], em.inputs['Color'])
nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
bd.data.materials.append(M_SKY)
bd.visible_diffuse = False; bd.visible_shadow = False; bd.visible_volume_scatter = False

# ---------------------------------------------------------------- palmiyeler
M_TRUNK = bpy.data.materials.new('trunk'); M_TRUNK.use_nodes = True
nt = M_TRUNK.node_tree; bt = nt.nodes['Principled BSDF']; bt.inputs['Roughness'].default_value = 0.7
uvt = node(nt, 'ShaderNodeUVMap'); sept = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(uvt.outputs[0], sept.inputs[0])
mt = node(nt, 'ShaderNodeMath', operation='MULTIPLY'); mt.inputs[1].default_value = 16.0
nt.links.new(sept.outputs['Y'], mt.inputs[0])
fr = node(nt, 'ShaderNodeMath', operation='FRACT'); nt.links.new(mt.outputs[0], fr.inputs[0])
trr = ramp(nt, [(0.0, lin(120, 72, 40)), (0.7, lin(160, 104, 58)), (1.0, lin(96, 56, 32))])
nt.links.new(fr.outputs[0], trr.inputs['Fac']); nt.links.new(trr.outputs['Color'], bt.inputs['Base Color'])
bmt = node(nt, 'ShaderNodeBump'); bmt.inputs['Strength'].default_value = 0.6
nt.links.new(fr.outputs[0], bmt.inputs['Height']); nt.links.new(bmt.outputs['Normal'], bt.inputs['Normal'])

M_LEAF = bpy.data.materials.new('leaf'); M_LEAF.use_nodes = True
nt = M_LEAF.node_tree; bl = nt.nodes['Principled BSDF']
bl.inputs['Roughness'].default_value = 0.42; bl.inputs['Coat Weight'].default_value = 0.3
bl.inputs['Subsurface Weight'].default_value = 0.0
uvl = node(nt, 'ShaderNodeUVMap'); sepl = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(uvl.outputs[0], sepl.inputs[0])
lr = ramp(nt, [(0.0, lin(38, 118, 42)), (0.45, lin(70, 162, 50)), (1.0, lin(132, 198, 66))])
nt.links.new(sepl.outputs['X'], lr.inputs['Fac']); nt.links.new(lr.outputs['Color'], bl.inputs['Base Color'])
trl = node(nt, 'ShaderNodeBsdfTranslucent'); trl.inputs['Color'].default_value = lin(160, 220, 60)
mixl = node(nt, 'ShaderNodeMixShader'); mixl.inputs['Fac'].default_value = 0.25
nt.links.new(bl.outputs[0], mixl.inputs[1]); nt.links.new(trl.outputs[0], mixl.inputs[2])
nt.links.new(mixl.outputs[0], nt.nodes['Material Output'].inputs['Surface'])


def frond(name, origin, direction, length, droop, width, n_leaf=16):
    """Palmiye yaprağı: kavisli orta damar + iki yanda geniş, sivri yaprakçıklar (kenarı tırtıklı görünüm)."""
    o_ = np.array(origin, dtype=float); d = np.array(direction, dtype=float); d /= np.linalg.norm(d)
    up = np.array([0, 0, 1.0])
    side = np.cross(d, up)
    if np.linalg.norm(side) < 1e-3:
        side = np.array([1.0, 0, 0])
    side /= np.linalg.norm(side)
    spine = []
    S = 24
    for k in range(S + 1):
        t = k / S
        p = o_ + d * length * t + up * length * (0.28 * t - droop * t * t)
        spine.append(p)
    spine = np.array(spine)
    verts, faces, uvs = [], [], []
    T = np.gradient(spine, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    for side_s in (-1, 1):
        for li in range(n_leaf):
            t = 0.10 + 0.86 * li / (n_leaf - 1)
            i = int(round(t * S))
            base = spine[i]; tang = T[i]
            down = -up - (-up).dot(tang) * tang
            if np.linalg.norm(down) < 0.2:
                down = side * side_s
            down /= np.linalg.norm(down)
            sd = np.cross(down, tang); sd /= np.linalg.norm(sd)
            # yaprakçık sarkar (resimdeki gibi damarın altında perde), iki yana hafif V açılır
            dirl = tang * 0.42 + down * 0.80 + sd * side_s * 0.42
            dirl /= np.linalg.norm(dirl)
            wlen = width * (math.sin(math.pi * min(1.0, 0.08 + t)) ** 0.6) * (1.05 - 0.3 * t)
            bw = length / n_leaf * 2.1
            p0 = base - tang * bw * 0.35; p1 = base + tang * bw * 0.65
            tip = base + dirl * wlen + tang * bw * 0.6
            fold = np.cross(dirl, tang); fold /= np.linalg.norm(fold)
            mid0 = p0 + (tip - p0) * 0.5 - tang * bw * 0.16
            mid1 = p1 + (tip - p1) * 0.5 + tang * bw * 0.06
            midc = (mid0 + mid1) / 2 + fold * side_s * bw * 0.12
            vi = len(verts)
            verts += [tuple(p0), tuple(p1), tuple(mid1), tuple(tip), tuple(mid0), tuple(midc), tuple((p0 + p1) / 2)]
            uvs += [(0.1, 0), (0.1, 0), (0.55, 0), (1.0, 0), (0.55, 0), (0.6, 0), (0.1, 0)]
            faces += [(vi + 6, vi + 1, vi + 2, vi + 5), (vi, vi + 6, vi + 5, vi + 4), (vi + 5, vi + 2, vi + 3), (vi + 4, vi + 5, vi + 3)]
    # orta damar (ince şerit)
    me = mesh_from(name, verts, faces, uv=uvs)
    o = new_obj(name, me)
    o.data.materials.append(M_LEAF)
    rib, _ = sweep(name + '_rib', [tuple(p) for p in spine[::4]], lambda t: 0.018 * (1 - 0.8 * t) * length, K=8, M=30)
    rib.data.materials.append(M_LEAF)
    return o


def palm(name, base, crown, size=1.0, n_fronds=8, seed=1, bend=0.25):
    rng = np.random.default_rng(seed)
    b = np.array(base, dtype=float); c = np.array(crown, dtype=float)
    mid = (b + c) / 2 + np.array([-bend, 0, 0]) * np.linalg.norm(c - b)
    tr, _ = sweep(name + '_trunk', [tuple(b), tuple((b + mid) / 2), tuple(mid), tuple((mid + c) / 2), tuple(c)],
                  lambda t: size * (0.11 - 0.035 * t), K=24, M=80)
    tr.data.materials.append(M_TRUNK)
    angs = np.linspace(-0.45, math.pi + 0.45, n_fronds) + rng.uniform(-0.12, 0.12, n_fronds)
    for k, a in enumerate(angs):
        d = (math.cos(a), rng.uniform(-0.45, 0.15), 0.55 * math.sin(a) + 0.12)
        frond(f'{name}_f{k}', tuple(c), d, size * rng.uniform(1.0, 1.25), droop=0.45 + 0.25 * rng.uniform(),
              width=size * 0.36, n_leaf=11)
    M_COCO, _ = principled('coco', lin(110, 80, 40), 0.5)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        cc = uv_sphere(f'{name}_c{k}', size * 0.075, 24, 12)
        cc.location = tuple(c + np.array([math.cos(a) * 0.08, -0.05 + math.sin(a) * 0.05, -0.09]) * size)
        cc.data.materials.append(M_COCO)


if CFG['palms']:
    yp = 3.0
    s_ = depth_scale(yp)
    if VAR == 'B':
        x1, z1 = img_to_world(0.06, 0.88, yp); xb, zb = img_to_world(-0.12, 0.30, yp)
        palm('palm1', (xb, yp, zb), (x1, yp, z1), size=0.9 * s_ * F / 3.95, seed=2)
    elif VAR == 'C':
        x1, z1 = img_to_world(0.90, 0.86, yp); xb, zb = img_to_world(1.10, 0.10, yp)
        palm('palm1', (xb, yp, zb), (x1, yp, z1), size=0.95 * s_ * F / 3.95, seed=2, bend=-0.25)
        x2, z2 = img_to_world(0.96, 0.56, yp + 0.6); xb2, zb2 = img_to_world(1.08, 0.0, yp + 0.6)
        palm('palm2', (xb2, yp + 0.6, zb2), (x2, yp + 0.6, z2), size=0.75 * s_ * F / 3.95, seed=5, bend=-0.2)
    else:
        x1, z1 = img_to_world(0.10, 0.85, yp); xb, zb = img_to_world(-0.08, 0.10, yp)
        palm('palm1', (xb, yp, zb), (x1, yp, z1), size=0.95 * s_ * F / 3.95, seed=2)
        x2, z2 = img_to_world(0.07, 0.49, yp + 0.6); xb2, zb2 = img_to_world(-0.06, 0.0, yp + 0.6)
        palm('palm2', (xb2, yp + 0.6, zb2), (x2, yp + 0.6, z2), size=0.75 * s_ * F / 3.95, seed=5)

# ---------------------------------------------------------------- deniz feneri + adacık
if CFG['light']:
    yl = 4.2
    lu = {'A': 0.915, 'B': 0.93, 'C': 0.925, 'D': 0.915}[VAR]
    xl, zl = img_to_world(lu, SEA_V, yl)
    zl = water_z(yl)
    k = F * depth_scale(yl) / 3.95
    M_GRASS, _ = principled('grass', lin(96, 176, 70), 0.6, **{'Coat Weight': 0.2})
    M_SAND, _ = principled('sand', lin(240, 214, 160), 0.8)
    isl = uv_sphere('islet', 1.0); isl.location = (xl + 0.25 * k, yl, zl - 0.02 * k); isl.scale = (0.75 * k, 0.45 * k, 0.17 * k)
    isl.data.materials.append(M_GRASS)
    snd = uv_sphere('sand', 1.0); snd.location = (xl + 0.25 * k, yl - 0.02, zl - 0.03 * k); snd.scale = (0.85 * k, 0.5 * k, 0.09 * k)
    snd.data.materials.append(M_SAND)
    base_z = zl + 0.12 * k
    H = 0.62 * k
    # gövde: kesik koni, kırmızı-beyaz bantlar
    tw, _ = sweep('tower', [(xl, yl, base_z - 0.05 * k), (xl, yl, base_z + H * 0.5), (xl, yl, base_z + H)],
                  lambda t: k * (0.105 - 0.03 * t), K=40, M=40, cap_end=True, cap_start=False)
    M_TOWER = bpy.data.materials.new('tower'); M_TOWER.use_nodes = True
    nt = M_TOWER.node_tree; bt2 = nt.nodes['Principled BSDF']; bt2.inputs['Roughness'].default_value = 0.35
    bt2.inputs['Coat Weight'].default_value = 0.5
    tct = node(nt, 'ShaderNodeTexCoord'); sp2 = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(tct.outputs['Object'], sp2.inputs[0])
    mm = node(nt, 'ShaderNodeMapRange'); mm.inputs['From Min'].default_value = base_z; mm.inputs['From Max'].default_value = base_z + H
    mm.inputs['To Max'].default_value = 4.0
    nt.links.new(sp2.outputs['Z'], mm.inputs['Value'])
    fr2 = node(nt, 'ShaderNodeMath', operation='FRACT'); nt.links.new(mm.outputs[0], fr2.inputs[0])
    st = ramp(nt, [(0.0, lin(226, 50, 44)), (0.49, lin(226, 50, 44)), (0.5, lin(250, 246, 240)), (1.0, lin(250, 246, 240))])
    st.color_ramp.interpolation = 'CONSTANT'
    nt.links.new(fr2.outputs[0], st.inputs['Fac']); nt.links.new(st.outputs['Color'], bt2.inputs['Base Color'])
    tw.data.materials.append(M_TOWER)
    M_RED, _ = principled('red', lin(214, 44, 40), 0.3, **{'Coat Weight': 0.6})
    gal = torus('gallery', 0.085 * k, 0.018 * k, 48, 12); gal.location = (xl, yl, base_z + H + 0.005 * k); gal.data.materials.append(M_RED)
    disc = uv_sphere('galdisc', 1.0, 32, 16); disc.location = (xl, yl, base_z + H); disc.scale = (0.1 * k, 0.1 * k, 0.02 * k)
    disc.data.materials.append(M_RED)
    M_LAMP = emission_material('lamp', lin(255, 236, 160), 2.5)
    lamp = uv_sphere('lamp', 1.0, 32, 16); lamp.location = (xl, yl, base_z + H + 0.07 * k); lamp.scale = (0.06 * k, 0.06 * k, 0.065 * k)
    lamp.data.materials.append(M_LAMP)
    cap_ = uv_sphere('cap', 1.0, 32, 16); cap_.location = (xl, yl, base_z + H + 0.125 * k); cap_.scale = (0.085 * k, 0.085 * k, 0.065 * k)
    cap_.data.materials.append(M_RED)
    knob = uv_sphere('knob', 0.018 * k, 16, 8); knob.location = (xl, yl, base_z + H + 0.2 * k); knob.data.materials.append(M_RED)
    M_DOOR, _ = principled('door', lin(110, 60, 40), 0.6)
    door = uv_sphere('door', 1.0, 24, 12); door.location = (xl, yl - 0.1 * k, base_z + 0.06 * k)
    door.scale = (0.03 * k, 0.02 * k, 0.06 * k); door.data.materials.append(M_DOOR)

# ---------------------------------------------------------------- ışıklar
def area(name, loc, target, energy, size, color=(1, 1, 1), shape='DISK', size_y=None):
    li = bpy.data.lights.new(name, 'AREA'); li.energy = energy; li.color = color; li.shape = shape; li.size = size
    if size_y:
        li.size_y = size_y
    o = new_obj(name, li); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 1.6; sun.angle = math.radians(14); sun.color = (1.0, 0.96, 0.9)
so = new_obj('sun', sun); so.rotation_euler = (Vector((0.45, 1.0, -0.75))).to_track_quat('-Z', 'Y').to_euler()
area('key_spec', (-3.2, -6.0, 4.4), (0, 0, 0.2), 380, 1.5, (1.0, 0.98, 0.95), 'RECTANGLE', 1.0)
area('fill', (5.5, -7.0, -0.8), (0, 0, -0.3), 220, 6.0, (1.0, 0.95, 0.88))
area('rimL', (-3.2, 3.5, 1.8), (0, 0, -0.2), 520, 2.5, (1.0, 0.78, 0.5))
area('rimR', (3.4, 3.0, 1.0), (0, 0, -0.3), 560, 2.5, (1.0, 0.72, 0.42))
und = area('under', (0, -4.0, -3.5), (0, 0, -0.6), 170, 4.0, (0.62, 0.92, 1.0))
# alttan turkuaz deniz yansıması yalnız jöle parçalara (tişört sarı kalsın): ışık bağlama
jelly_col = bpy.data.collections.new('jelly_recv')
for o in sc.objects:
    if o.type == 'MESH' and o.active_material and o.active_material.name in ('jelly_head', 'jelly', 'sucker'):
        jelly_col.objects.link(o)
und.light_linking.receiver_collection = jelly_col

# ---------------------------------------------------------------- kamera
cam = bpy.data.cameras.new('cam'); cam.lens = LENS; cam.sensor_width = 36; cam.sensor_fit = 'HORIZONTAL'
co = new_obj('cam', cam); sc.camera = co
if SIDE:
    co.location = (DIST * 0.62, -DIST * 0.78, 0.6)
    co.rotation_euler = (Vector((0, 0, -0.5)) - co.location).to_track_quat('-Z', 'Y').to_euler()
else:
    co.location = (CX, -DIST, CZ)
    co.rotation_euler = (math.radians(90), 0, 0)
cam.clip_start = 0.1; cam.clip_end = 100

os.makedirs(os.path.dirname(OUT), exist_ok=True)
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('OK', OUT)
