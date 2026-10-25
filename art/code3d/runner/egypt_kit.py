# Piramit Koşusu (koşu mini oyunu, Antik Mısır teması) için ortak 3B araçlar (25 Ekim 2026).
# Neden ayrı kit: koşu yolu ve yan duvar UÇ UCA DÖŞENİR (10 m'lik parçalar art arda) → renk, oyuk gölgesi ve normal haritası
# y = ±5 kenarlarında birebir aynı olmalı. Bunun için:
#   - düğümlü taş/kum malzemeleri isteğe bağlı "dönemli" koordinatla çalışır: y, yarıçapı L/2π olan bir çembere sarılır ve 4B gürültüye
#     verilir (x, z, R·cos θ, R·sin θ) → desen y'de tam L = 10 m'de tekrar eder, dikiş yok;
#   - tasarlanmış ayrıntı (döşeme taşı yerleşimi, kabartma hiyeroglif benzeri resimler, boya bantları) numpy + PIL ile 2B haritada
#     çizilir (y'de sarmalı) ve taslağın 'dec' UV'sinden okunur: üst renk (RGBA), gölge çarpanı (oyuk kiri, taş tonu), normal haritası;
#   - pişirme v6/proxy_bake.export_proxy ile (renk × yumuşak AO + teğet normal); taslak y'de ±5'in ötesine de uzar, böylece uçlardaki
#     AO komşu parçayı "görür".
# Engeller, toplanabilirler ve arka plan aynı malzemelerle (dönemsiz) bld_kit tarzında pişirilir.
# Stil: boyalı maket + yumuşak "vinyl oyuncak"; canlı ama dengeli renk (soluk değil, neon değil); dış çizgi yok; tasarımlar özgün
# (yazı/gerçek işaret yok: kuş, göz, güneş, nilüfer, kedi, balık, yıldız…), korkutucu öğe yok.
import os, sys, math, random, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, '..'), os.path.join(HERE, '..', 'v6'), os.path.join(HERE, '..', 'bld')):
    if p not in sys.path: sys.path.insert(0, p)
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, noise as MN
import kit
from kit import srgb, ramp, nodes_mat
import assets_v3 as A
import proxy_bake as PB
import bld_kit as BK

ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
TAU = 2 * math.pi

# ------------------------------------------------------------------ renkler (sRGB)
SANDSTONE = ('#bd8a52', '#d8a86c', '#ebc68e')       # sıcak kumtaşı (koyu, orta, açık)
SLAB = ('#c49562', '#dcb27c', '#efd09c')            # yol taşı: biraz daha açık
LIMESTONE = ('#cdbf9f', '#e4d6b8', '#f4ead4')       # güneşte ağarmış kireçtaşı
SAND = ('#d2a96c', '#e6c48c', '#f3dcac')            # kum (çukur, orta, tepe)
BLUE, LAPIS, TURQ = '#2f6db5', '#294f9a', '#3aaea2'
TERRA, GOLD, GREEN, CREAM, OCHRE = '#c4573a', '#e8b13c', '#4f9a5e', '#f3ead8', '#d99a3a'


def lin(h):
    return np.array(srgb(h)[:3], np.float32)


# ------------------------------------------------------------------ düğüm yardımcısı

class EG(A._G):
    """A._G + dünya konumu, 4B (dönemli) gürültü, görüntü düğümü."""
    def pos(self):
        g = self.n.new('ShaderNodeNewGeometry'); return g.outputs['Position']
    def nrm(self):
        g = self.n.new('ShaderNodeNewGeometry'); return g.outputs['Normal']
    def sep(self, v):
        s = self.n.new('ShaderNodeSeparateXYZ'); self.l.new(v, s.inputs[0]); return s.outputs['X'], s.outputs['Y'], s.outputs['Z']
    def comb(self, x, y, z):
        c = self.n.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)): c.inputs[i].default_value = v
            else: self.l.new(v, c.inputs[i])
        return c.outputs[0]
    def coords(self, period=None, stretch=(1.0, 1.0, 1.0), off=(0.0, 0.0, 0.0)):
        """(vektör, w): period verilirse y dönemli (4B), değilse 3B dünya konumu (w None)."""
        x, y, z = self.sep(self.pos()); sx, sy, sz = stretch
        x = self.math('MULTIPLY', self.math('ADD', x, off[0]), sx); z = self.math('MULTIPLY', self.math('ADD', z, off[2]), sz)
        if period is None:
            return self.comb(x, self.math('MULTIPLY', self.math('ADD', y, off[1]), sy), z), None
        th = self.math('MULTIPLY', y, TAU / period); R = period * sy / TAU
        return self.comb(x, z, self.math('MULTIPLY', self.math('COSINE', th), R)), self.math('MULTIPLY', self.math('SINE', th), R)
    def coords_xy(self, period, off=(0.0, 0.0, 0.0)):
        """Yükseklik alanı için ucuz dönemli koordinat: (x, R·cos θ, R·sin θ) — z yok, 3B gürültü/Voronoi (4B'nin yaklaşık yarı maliyeti)."""
        x, y, z = self.sep(self.pos())
        th = self.math('MULTIPLY', self.math('ADD', y, off[1]), TAU / period); R = period / TAU
        return self.comb(self.math('ADD', x, off[0]), self.math('MULTIPLY', self.math('COSINE', th), R), self.math('MULTIPLY', self.math('SINE', th), R)), None
    def noise4(self, cw, scale, detail=4, rough=0.5, out='Fac', distort=0.0):
        vec, w = cw; z = self.n.new('ShaderNodeTexNoise')
        z.noise_dimensions = '4D' if w is not None else '3D'
        z.inputs['Scale'].default_value = scale; z.inputs['Detail'].default_value = detail; z.inputs['Roughness'].default_value = rough
        z.inputs['Distortion'].default_value = distort
        self.l.new(vec, z.inputs['Vector'])
        if w is not None: self.l.new(w, z.inputs['W'])
        return z.outputs[out]
    def vor4(self, cw, scale, feature='F1', out='Distance', rnd=1.0):
        vec, w = cw; v = self.n.new('ShaderNodeTexVoronoi')
        v.voronoi_dimensions = '4D' if w is not None else '3D'; v.feature = feature
        v.inputs['Scale'].default_value = scale; v.inputs['Randomness'].default_value = rnd
        self.l.new(vec, v.inputs['Vector'])
        if w is not None: self.l.new(w, v.inputs['W'])
        return v.outputs[out]
    def ao(self, dist=0.15, samples=8):
        a = self.n.new('ShaderNodeAmbientOcclusion'); a.samples = samples; a.only_local = True
        a.inputs['Distance'].default_value = dist; return a.outputs['AO']
    def img(self, image, uv='dec', ext='REPEAT', out='Color'):
        t = self.n.new('ShaderNodeTexImage'); t.image = image; t.extension = ext; t.interpolation = 'Linear'
        u = self.n.new('ShaderNodeUVMap'); u.uv_map = uv; self.l.new(u.outputs[0], t.inputs['Vector'])
        return t
    def mul(self, a, b):
        return self.mix(1.0, a, b, 'MULTIPLY')


def _shade(h, k): return A._shade(h, k)


# ------------------------------------------------------------------ yüzey renkleri (düğüm)

def stone_col(G, pal=SANDSTONE, period=None, bands=0.5, pits=0.6, wear=0.5, cav=0.5, dust=0.35, grime=0.3, seed=0.0, ground_z=0.0):
    """Kumtaşı/kireçtaşı: iri ton lekeleri, yatay tortul bantlar (dünya z), ince tane, gözenek benekleri, aşınmış açık kenar
    (Pointiness), oyukta kir (AO), yukarı bakan yüzde kum tozu, dipte kum lekesi. Döner: renk soketi."""
    cw = G.coords(period, off=(seed * 3.1, seed * 1.7, seed * 2.3))
    n1 = G.noise4(cw, 0.55, 3, 0.55)
    rp = ramp(G.nt, [(0.32, pal[0]), (0.5, pal[1]), (0.7, pal[2])]); G.l.new(n1, rp.inputs['Fac'])
    col = rp.outputs[0]
    col = G.mix(G.rng(G.noise4(cw, 2.4, 4), 0.35, 0.68, 0, 0.35), col, _shade(pal[1], 0.86))         # orta ölçek leke
    if bands:
        x, y, z = G.sep(G.pos())
        zz = G.math('ADD', z, G.math('MULTIPLY', G.noise4(cw, 1.2, 3), 0.18))
        bd = G.math('SINE', G.math('MULTIPLY', zz, 48.0))
        col = G.mix(G.rng(bd, 0.2, 1.0, 0, 0.16 * bands), col, _shade(pal[2], 1.04))
        bd2 = G.math('SINE', G.math('MULTIPLY', zz, 17.0))
        col = G.mix(G.rng(bd2, 0.55, 1.0, 0, 0.14 * bands), col, _shade(pal[0], 0.95))
    col = G.mix(0.22, col, G.noise4(G.coords(period, (1, 1, 1), (seed, 0, 0)), 34.0, 3, 0.6, 'Color'), 'OVERLAY')   # ince tane
    if pits:
        pv = G.vor4(cw, 26.0)
        col = G.mix(G.math('MULTIPLY', G.rng(pv, 0.07, 0.0, 0, 0.5 * pits), G.rng(G.noise4(cw, 3.0), 0.4, 0.6)), col, _shade(pal[0], 0.7))
        pv2 = G.vor4(cw, 9.0)
        col = G.mix(G.rng(pv2, 0.035, 0.0, 0, 0.35 * pits), col, _shade(pal[0], 0.62))
    if wear:
        col = G.mix(G.math('MULTIPLY', G.edges(0.53, 0.62), 0.55 * wear), col, '#f6e2b8')
    if cav:
        col = G.mix(G.rng(G.ao(0.12), 0.85, 0.35, 0, 0.5 * cav), col, '#7d5734')
    if dust:
        up = G.rng(G.nz(), 0.55, 0.9)
        d = G.math('MULTIPLY', up, G.rng(G.noise4(cw, 1.6, 4), 0.42, 0.66, 0, dust))
        col = G.mix(d, col, SAND[2])
    if grime:
        x, y, z = G.sep(G.pos())
        zn = G.math('ADD', G.math('SUBTRACT', z, ground_z), G.math('MULTIPLY', G.noise4(cw, 6.0, 4), 0.12))
        col = G.mix(G.rng(zn, 0.28, 0.0, 0, 0.45 * grime), col, '#c99e66')
    return col


def sand_col(G, period=None, seed=0.0, ripple=0.16):
    """Kum: rüzgâr dalgacıkları (y'de dönemli: dalga boyu 10 m'ye tam bölünür), iri ton dalgası, açık tepe / koyu oyuk, tane benekleri."""
    cw = G.coords(period, off=(seed, 0, 0))
    x, y, z = G.sep(G.pos())
    k = TAU * round(10.0 / ripple) / 10.0
    ph = G.math('ADD', G.math('MULTIPLY', G.math('ADD', y, G.math('MULTIPLY', x, 0.42)), k), G.math('MULTIPLY', G.noise4(cw, 0.9, 3), 5.0))
    rip = G.math('SINE', ph)
    col = G.mix(G.rng(G.noise4(cw, 0.35, 3), 0.3, 0.72), SAND[0], SAND[1])
    col = G.mix(G.rng(G.noise4(cw, 1.4, 3), 0.45, 0.7, 0, 0.45), col, SAND[2])
    col = G.mix(G.math('MULTIPLY', G.rng(rip, -0.2, 1.0, 0, 0.22), G.rng(G.noise4(cw, 0.6, 2), 0.3, 0.6, 0.3, 1.0)), col, _shade(SAND[2], 1.03))
    col = G.mix(G.math('MULTIPLY', G.rng(rip, -0.75, -1.0, 0, 0.18), 1.0), col, _shade(SAND[0], 0.92))
    col = G.mix(G.rng(G.vor4(cw, 70.0), 0.0, 0.07, 0.55, 0), col, '#fbf1da')
    col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 4, 0, 0)), 55.0), 0.0, 0.05, 0.4, 0), col, '#a87a48')
    return col


def bump_noise(G, normal_in=None, period=None, strength=0.25, scale=30.0, dist=0.01):
    b = G.n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
    G.l.new(G.noise4(G.coords(period), scale, 4, 0.6), b.inputs['Height'])
    if normal_in is not None: G.l.new(normal_in, b.inputs['Normal'])
    return b.outputs['Normal']


class Decal:
    """2B harita (numpy) → Blender görüntüleri: üst renk RGBA, gölge çarpanı RGB, normal RGB (+ kum maskesi)."""
    def __init__(self, name, over=None, shade=None, normal=None, sandmask=None, ext='REPEAT'):
        self.name = name; self.ext = ext
        self.over = to_image(name + '_over', over, alpha=True) if over is not None else None
        one = lambda a: np.concatenate([a, np.ones(a.shape[:2] + (1,), np.float32)], -1)    # alfa 1: CLIP dışında 0 → nötr
        self.shade = to_image(name + '_shade', one(shade), alpha=True) if shade is not None else None
        self.normal = to_image(name + '_nrm', one(normal), alpha=True, noncolor=True) if normal is not None else None
        self.sand = to_image(name + '_sand', one(np.repeat(sandmask[..., None], 3, -1)), alpha=True, noncolor=True) if sandmask is not None else None


def apply_dec(G, col, dec, period=None):
    """Decal katmanları: kum maskesi, gölge çarpanı, üst boya, normal. CLIP decal'de alan dışı (alfa 0) nötr kalır. Döner (renk, normal|None)."""
    clip = dec.ext == 'CLIP'
    def sample(img, neutral):
        t = G.img(img, ext=dec.ext)
        return G.mix(t.outputs['Alpha'], neutral, t.outputs['Color']) if clip else t.outputs['Color']
    if dec.sand is not None:
        sf = getattr(dec, 'sand_fn', None) or sand_col                 # uzay kiti: Ay tozu rengi
        col = G.mix(sample(dec.sand, '#000000'), col, sf(G, period))
    if dec.shade is not None:
        col = G.mul(col, sample(dec.shade, '#ffffff'))
    if dec.over is not None:
        t = G.img(dec.over, ext=dec.ext); col = G.mix(t.outputs['Alpha'], col, t.outputs['Color'])
    nin = None
    if dec.normal is not None:
        nc = sample(dec.normal, '#bcbcff')     # sRGB #bcbcff ≈ doğrusal (0,5; 0,5; 1)
        nm = G.n.new('ShaderNodeNormalMap'); nm.space = 'TANGENT'; nm.uv_map = 'dec'
        G.l.new(nc, nm.inputs['Color']); nin = nm.outputs['Normal']
    return col, nin


def m_stone(name, pal=SANDSTONE, period=None, dec=None, bump=0.22, bump_scale=30.0, **kw):
    """Taş malzemesi; dec (Decal) verilirse kum maskesi, gölge çarpanı, üst boya ve normal haritası eklenir ('dec' UV)."""
    def b(nt, bsdf):
        G = EG(nt)
        col = stone_col(G, pal, period, **kw)
        nin = None
        if dec is not None:
            col, nin = apply_dec(G, col, dec, period)
        G.l.new(col, bsdf.inputs['Base Color'])
        if bump: G.l.new(bump_noise(G, nin, period, bump, bump_scale), bsdf.inputs['Normal'])
        elif nin is not None: G.l.new(nin, bsdf.inputs['Normal'])
    return nodes_mat(name, b)


def m_sand(name='sand_eg', period=None, seed=0.0):
    def b(nt, bsdf):
        G = EG(nt); G.l.new(sand_col(G, period, seed), bsdf.inputs['Base Color'])
        G.l.new(bump_noise(G, None, period, 0.12, 14.0), bsdf.inputs['Normal'])
    return nodes_mat(name, b)


def m_gold(name='gold_eg', base=GOLD, dec=None, hammer=0.5):
    """Cilalı altın (oyunda metal yok: parlaklık renge işlenir): yukarı bakan yüz açık sarı, aşağı bakan sıcak turuncu-kahve,
    dış kenarda parlak çizgi, oyukta koyu; hafif dövme benekleri. dec: lapis kakma vb. üst boya."""
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords()
        nz = G.nz()
        col = G.mix(G.rng(nz, -0.6, 0.9), '#9a5a1c', _shade(base, 0.95))
        col = G.mix(G.rng(nz, 0.35, 0.95, 0, 0.75), col, '#ffe9a0')
        col = G.mix(G.math('MULTIPLY', G.edges(0.52, 0.6), 0.6), col, '#fff3c6')
        col = G.mix(G.rng(G.ao(0.08), 0.85, 0.3, 0, 0.6), col, '#7a4512')
        col = G.mix(G.rng(G.noise4(cw, 18.0, 3), 0.35, 0.75, 0, 0.18 * hammer), col, '#c98a26')
        if dec is not None and dec.over is not None:
            t = G.img(dec.over, ext=dec.ext); col = G.mix(t.outputs['Alpha'], col, t.outputs['Color'])
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.12 * hammer; bb.inputs['Distance'].default_value = 0.004
        G.l.new(G.vor4(cw, 40.0), bb.inputs['Height']); G.l.new(bb.outputs['Normal'], bsdf.inputs['Normal'])
    return nodes_mat(name, b)


def m_paint(name, hexc, fade=0.25, chips=0.3, base=None, scale=1.0, ao=0.4):
    """Boyalı yüzey (taş/ahşap üstü): güneşte solma lekeleri, pul pul dökülme (altından base tonu), oyukta koyulaşma."""
    base = base or SANDSTONE[1]
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords()
        col = G.mix(G.rng(G.noise4(cw, 1.1 * scale, 4), 0.35, 0.75, 0, fade), hexc, _shade(hexc, 1.25))
        col = G.mix(0.12, col, G.noise4(cw, 25.0 * scale, 3, 0.6, 'Color'), 'OVERLAY')
        if chips:
            ch = G.rng(G.noise4(cw, 3.2 * scale, 6, 0.65), 0.68 - 0.06 * chips, 0.66 - 0.06 * chips)
            col = G.mix(G.math('SUBTRACT', 1.0, ch), col, base)
        col = G.mix(G.rng(G.ao(0.1), 0.85, 0.35, 0, ao), col, _shade(hexc, 0.55))
        col = G.mix(G.math('MULTIPLY', G.edges(0.53, 0.62), 0.35), col, _shade(hexc, 1.35))
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_clay(name='clay_eg', hexc='#c9774a', band=None):
    """Pişmiş toprak küp: sıcak turuncu, kaba benek, yukarıda açık toz, dipte kum; isteğe bağlı boyalı bant (z aralığı)."""
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords()
        col = G.mix(G.rng(G.noise4(cw, 1.4, 4), 0.3, 0.75), _shade(hexc, 0.85), _shade(hexc, 1.12))
        col = G.mix(G.rng(G.vor4(cw, 40.0), 0.0, 0.08, 0.4, 0), col, '#f1c69a')
        if band:
            x, y, z = G.sep(G.obj())
            for (z0, z1, hc) in band:
                m = G.math('MULTIPLY', G.rng(z, z0 - 0.004, z0 + 0.004), G.rng(z, z1 + 0.004, z1 - 0.004))
                col = G.mix(G.math('MULTIPLY', m, G.rng(G.noise4(cw, 4.0, 4), 0.25, 0.4, 0.4, 0.92)), col, hc)
        col = G.mix(G.rng(G.nz(), 0.6, 0.95, 0, 0.35), col, SAND[2])
        col = G.mix(G.rng(G.ao(0.1), 0.85, 0.35, 0, 0.5), col, '#5e321c')
        col = G.mix(G.math('MULTIPLY', G.edges(0.53, 0.62), 0.4), col, '#f4c8a0')
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_cloth(name, c1, c2=None, stripes=6.0, axis='Z', fade=0.2):
    """Bayrak/flama kumaşı: iki renk şerit (nesne koordinatı), dokuma tanesi, güneş solması, kıvrım oyuğunda koyu."""
    def b(nt, bsdf):
        G = EG(nt); o = G.obj(); x, y, z = G.sep(o)
        ax = {'X': x, 'Y': y, 'Z': z}[axis]
        col = G.mix(0.0, c1, c1)
        if c2:
            st = G.math('SINE', G.math('MULTIPLY', ax, stripes * TAU))
            col = G.mix(G.rng(st, -0.08, 0.08), c1, c2)
        col = G.mix(G.rng(G.noise(o, 1.2, 3), 0.35, 0.75, 0, fade), col, '#fff4dc')
        col = G.mix(0.12, col, G.noise(o, 60.0, 2, 0.5, 'Color'), 'OVERLAY')
        col = G.mix(G.rng(G.ao(0.1), 0.85, 0.35, 0, 0.45), col, '#3a2a20')
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_flatc(name, hexc, var=0.1, ao=0.35):
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords()
        col = G.mix(G.rng(G.noise4(cw, 3.0, 3), 0.3, 0.7, 0, var), hexc, _shade(hexc, 1.2))
        col = G.mix(G.rng(G.ao(0.1), 0.85, 0.35, 0, ao), col, _shade(hexc, 0.55))
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_decal(name, base_mat_fn, dec):
    """Görüntü renkli yüzey (ör. altın üstüne lapis): base_mat_fn(G) → renk; dec üst boya + normal."""
    def b(nt, bsdf):
        G = EG(nt); col = base_mat_fn(G)
        col, nin = apply_dec(G, col, dec)
        if nin is not None: G.l.new(nin, bsdf.inputs['Normal'])
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


# ------------------------------------------------------------------ 2B harita araçları (numpy, satır 0 = v 0 = alt)

def to_image(name, arr, alpha=False, noncolor=False):
    """numpy (h, w, 3|4) doğrusal → Blender kayan noktalı görüntü (satır 0 alt)."""
    h, w = arr.shape[:2]
    a = np.ones((h, w, 4), np.float32)
    a[..., :arr.shape[2]] = arr
    if not alpha: a[..., 3] = 1.0
    else: a[..., :3] *= a[..., 3:4]          # Blender'da kayan noktalı görüntü tamponu önçarpımlı sayılır (düz renk alfaya bölünüp parlıyordu)
    img = bpy.data.images.new(name, w, h, alpha=alpha, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color' if noncolor else 'Linear Rec.709'
    if alpha: img.alpha_mode = 'STRAIGHT'
    img.pixels.foreach_set(a.ravel())
    return img


def save_png(path, arr):
    """Denetim için (doğrusal → sRGB, üst satır = üst)."""
    from PIL import Image
    a = np.clip(arr[..., :3], 0, 1)
    s = np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)
    Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8)[::-1]).save(path)


def blur(a, sigma, wrap=(False, True)):
    """Gauss bulanıklığı (FFT). wrap: (satır ekseni dönemli mi, sütun ekseni dönemli mi); dönemsiz eksen yansıtmalı dolgu."""
    sg = sigma if isinstance(sigma, (tuple, list)) else (sigma, sigma)
    out = a.astype(np.float32)
    for ax, wr in ((0, wrap[0]), (1, wrap[1])):
        sigma = sg[ax]
        if sigma <= 0: continue
        n = out.shape[ax]; pad = 0 if wr else int(3 * sigma) + 1
        if pad:
            pw = [(0, 0)] * out.ndim; pw[ax] = (pad, pad); x = np.pad(out, pw, mode='reflect')
        else: x = out
        m = x.shape[ax]; f = np.fft.rfftfreq(m)
        g = np.exp(-2 * (math.pi * f * sigma) ** 2)
        sh = [1] * x.ndim; sh[ax] = len(f)
        x = np.fft.irfft(np.fft.rfft(x, axis=ax) * g.reshape(sh), n=m, axis=ax)
        if pad:
            sl = [slice(None)] * x.ndim; sl[ax] = slice(pad, pad + n); x = x[tuple(sl)]
        out = x.astype(np.float32)
    return out


def fnoise(shape, feat, seed=0, octaves=3, gain=0.5):
    """İki eksende dönemli gürültü (FFT, 1/f): feat = taban özellik boyu (piksel). Çıkış ~0..1."""
    rng = np.random.default_rng(seed); h, w = shape; acc = np.zeros(shape, np.float32); amp = 1.0; tot = 0.0
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]; r = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        f0 = 1.0 / max(feat / (2 ** o), 1.5)
        spec = np.exp(-((r - 0.0) / f0) ** 2 * 1.0) * (rng.normal(size=r.shape) + 1j * rng.normal(size=r.shape))
        spec[0, 0] = 0
        x = np.fft.irfft2(spec, s=shape).astype(np.float32); x /= (x.std() + 1e-8)
        acc += amp * x; tot += amp; amp *= gain
    acc /= tot
    return np.clip(0.5 + acc * 0.18 * 1.6, 0, 1)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def normal_from_height(h, ppm, wrap=(False, True), strength=1.0):
    """Yükseklik (m) → teğet uzayı normal (OpenGL: x = +u sütun, y = +v satır), 0..1 kodlu."""
    def d(a, ax, wr):
        if wr: return (np.roll(a, -1, ax) - np.roll(a, 1, ax)) * 0.5 * ppm
        g = np.gradient(a, axis=ax) * ppm; return g
    dx = d(h, 1, wrap[1]); dy = d(h, 0, wrap[0])
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def cavity(h, ppm, r=0.03, k=40.0, wrap=(False, True)):
    """Oyuk: çevre ortalamasından aşağıda kalan yerler (m) → 0..1 koyulaşma."""
    c = blur(h, r * ppm, wrap) - h
    return np.clip(c * k, 0, 1)


# ------------------------------------------------------------------ resim çizimi (PIL; özgün, yazısız simgeler)

class Canvas:
    """Kabartma/boya tuvali: metre koordinatı (u sağ, v yukarı; satır = v·ppm). Katmanlar: carve (oyma alanı), groove (ince çizgi),
    raise (oyma içinde kabarık kalan), paint RGB + paint alfa. wrap_u: u dönemli (sınırı aşan şekil öbür yandan da çizilir)."""
    def __init__(self, wm, hm, ppm, wrap_u=False, u0=0.0, v0=0.0, wrap_v=False):
        from PIL import Image, ImageDraw
        self.W, self.H = int(round(wm * ppm)), int(round(hm * ppm)); self.ppm = ppm; self.wm = wm; self.wrap = wrap_u
        self.hm = hm; self.wrapv = wrap_v
        self.u0, self.v0 = u0, v0
        self.L = {k: Image.new('L', (self.W, self.H), 0) for k in ('carve', 'groove', 'raise', 'pa', 'mask')}
        self.P = Image.new('RGB', (self.W, self.H), (0, 0, 0))
        self.D = {k: ImageDraw.Draw(v) for k, v in self.L.items()}; self.DP = ImageDraw.Draw(self.P)
    def px(self, u, v):
        return ((u - self.u0) * self.ppm, (v - self.v0) * self.ppm)
    def _shifts(self):
        su = (0.0, -self.wm, self.wm) if self.wrap else (0.0,)
        sv = (0.0, -self.hm, self.hm) if self.wrapv else (0.0,)
        return [(a, b) for a in su for b in sv]
    def _draw(self, fn, layers, col):
        for sh in self._shifts():
            for k, val in layers:
                fn(self.D[k], sh, val)
            if col is not None:
                c = tuple(int(255 * x) for x in col)
                fn(self.DP, sh, c); fn(self.D['pa'], sh, 255)
    def poly(self, pts, carve=True, col=None, layer='carve', val=255):
        def f(d, sh, fill): d.polygon([self.px(u + sh[0], v + sh[1]) for u, v in pts], fill=fill)
        self._draw(f, [(layer, val)] if carve else [], col)
    def ell(self, cu, cv, ru, rv, carve=True, col=None, layer='carve', val=255):
        def f(d, sh, fill):
            a = self.px(cu - ru + sh[0], cv - rv + sh[1]); b = self.px(cu + ru + sh[0], cv + rv + sh[1]); d.ellipse([a, b], fill=fill)
        self._draw(f, [(layer, val)] if carve else [], col)
    def line(self, pts, w, carve=True, col=None, layer='groove', val=255):
        def f(d, sh, fill):
            q = [self.px(u + sh[0], v + sh[1]) for u, v in pts]; wp = max(1, int(round(w * self.ppm)))
            d.line(q, fill=fill, width=wp, joint='curve')
            r = wp / 2.0
            for (x, y) in (q[0], q[-1]): d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        self._draw(f, [(layer, val)] if carve else [], col)
    def rect(self, u0, v0, u1, v1, carve=True, col=None, layer='carve', val=255):
        self.poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], carve, col, layer, val)
    def arr(self, k):
        return np.asarray(self.L[k], np.float32) / 255.0
    def paint(self):
        p = np.asarray(self.P, np.float32) / 255.0
        p = np.where(p <= 0.04045, p / 12.92, ((p + 0.055) / 1.055) ** 2.4)        # sRGB → doğrusal
        return p.astype(np.float32), self.arr('pa')


class Pen:
    """Simge kalemi: birim kutu (0..1, y yukarı) → tuvalde (u0, v0) köşeli w × h alan. flip: yatay ayna."""
    def __init__(self, cv, u0, v0, w, h, flip=False):
        self.c, self.u0, self.v0, self.w, self.h, self.f = cv, u0, v0, w, h, flip
    def P(self, x, y):
        if self.f: x = 1 - x
        return (self.u0 + x * self.w, self.v0 + y * self.h)
    def poly(self, pts, col=None, **kw):
        self.c.poly([self.P(x, y) for x, y in pts], col=col, **kw)
    def ell(self, cx, cy, rx, ry, col=None, rot=0.0, n=28, **kw):
        if abs(rot) < 1e-6 and not self.f:
            u, v = self.P(cx, cy); self.c.ell(u, v, rx * self.w, ry * self.h, col=col, **kw); return
        a = math.radians(rot); pts = []
        for i in range(n):
            t = i / n * TAU; x = rx * math.cos(t); y = ry * math.sin(t)
            pts.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
        self.poly(pts, col=col, **kw)
    def line(self, pts, w, col=None, **kw):
        self.c.line([self.P(x, y) for x, y in pts], w * self.w, col=col, **kw)
    def circle(self, cx, cy, r, col=None, **kw):
        self.ell(cx, cy, r, r * self.w / self.h, col=col, **kw)


def C(h):
    """sRGB hex → 0..1 (çizim rengi)."""
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def arcpts(cx, cy, rx, ry, a0, a1, n=12):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


# Simgeler (hepsi özgün, basit biçimler; yazı ya da gerçek işaret yok). Renkler: gövde dolgusu, ayrıntı oluk çizgisi.
def g_duck(p, c1=BLUE, c2=TURQ, c3=GOLD):
    p.ell(0.48, 0.38, 0.34, 0.2, C(c1))
    p.ell(0.78, 0.66, 0.12, 0.12, C(c1))
    p.poly([(0.86, 0.69), (1.0, 0.64), (0.87, 0.6)], C(c3))
    p.poly([(0.14, 0.42), (0.02, 0.56), (0.12, 0.34)], C(c1))
    p.ell(0.44, 0.42, 0.2, 0.1, C(c2), rot=-8, layer='raise')
    p.line([(0.3, 0.4), (0.55, 0.43)], 0.025); p.line([(0.32, 0.36), (0.56, 0.38)], 0.025)
    p.line([(0.42, 0.18), (0.4, 0.04)], 0.035, C(c3), layer='carve'); p.line([(0.54, 0.18), (0.56, 0.04)], 0.035, C(c3), layer='carve')
    p.circle(0.8, 0.69, 0.025, C('#2a2a3a'), layer='raise')


def g_ibis(p, c1=CREAM, c2=LAPIS, c3=GOLD):
    p.ell(0.42, 0.5, 0.26, 0.17, C(c1))
    p.poly([(0.16, 0.52), (0.02, 0.42), (0.18, 0.44)], C(c2))
    p.line([(0.62, 0.56), (0.7, 0.74), (0.72, 0.84)], 0.07, C(c2), layer='carve')
    p.ell(0.73, 0.86, 0.07, 0.07, C(c2))
    p.line([(0.78, 0.86), (0.92, 0.72), (0.98, 0.56)], 0.03, C(c3), layer='carve')
    p.line([(0.4, 0.34), (0.38, 0.02)], 0.03, C(c3), layer='carve'); p.line([(0.48, 0.34), (0.52, 0.02)], 0.03, C(c3), layer='carve')
    p.ell(0.36, 0.52, 0.16, 0.08, C(c2), layer='raise')


def g_eye(p, c1=CREAM, c2=BLUE, c3=LAPIS):
    pts = arcpts(0.5, 0.38, 0.46, 0.3, 20, 160, 14) + arcpts(0.5, 0.62, 0.46, 0.3, 200, 340, 14)
    p.poly(pts, C(c1))
    p.circle(0.5, 0.5, 0.15, C(c2), layer='raise'); p.circle(0.5, 0.5, 0.06, C('#2a2a3a'))
    p.line(arcpts(0.5, 0.52, 0.48, 0.34, 25, 155, 10), 0.05, C(c3))
    p.line([(0.04, 0.5), (0.0, 0.48)], 0.04, C(c3))


def g_sun(p, c1=TERRA, c2=GOLD):
    p.circle(0.5, 0.5, 0.42, C(c2)); p.circle(0.5, 0.5, 0.28, C(c1), layer='raise')
    p.line(arcpts(0.5, 0.5, 0.35, 0.35 * p.w / p.h, 0, 360, 24), 0.025)


def g_lotus(p, c1=BLUE, c2=GREEN, c3=TURQ):
    p.line([(0.5, 0.0), (0.5, 0.45)], 0.06, C(c2), layer='carve')
    p.poly([(0.5, 0.42), (0.38, 0.62), (0.5, 1.0), (0.62, 0.62)], C(c1))
    p.poly([(0.46, 0.44), (0.14, 0.6), (0.06, 0.92), (0.3, 0.72)], C(c3))
    p.poly([(0.54, 0.44), (0.86, 0.6), (0.94, 0.92), (0.7, 0.72)], C(c3))
    p.ell(0.5, 0.42, 0.16, 0.06, C(c2))


def g_scarab(p, c1=TURQ, c2=LAPIS, c3=GOLD):
    p.ell(0.5, 0.4, 0.24, 0.28, C(c1))
    p.ell(0.5, 0.74, 0.14, 0.09, C(c2))
    p.line([(0.5, 0.14), (0.5, 0.64)], 0.025)
    for s in (-1, 1):
        for (a, b2) in (((0.28, 0.56), (0.1, 0.66)), ((0.27, 0.42), (0.06, 0.4)), ((0.3, 0.24), (0.12, 0.1))):
            p.line([(0.5 + s * (a[0] - 0.5), a[1]), (0.5 + s * (b2[0] - 0.5), b2[1])], 0.035, C(c2), layer='carve')
    p.circle(0.5, 0.92, 0.07, C(c3))


def g_cat(p, c1=LAPIS, c2=GOLD, c3=CREAM):
    p.ell(0.45, 0.32, 0.24, 0.3, C(c1))
    p.ell(0.58, 0.72, 0.15, 0.15, C(c1))
    p.poly([(0.47, 0.8), (0.48, 0.98), (0.57, 0.84)], C(c1)); p.poly([(0.62, 0.84), (0.71, 0.98), (0.71, 0.8)], C(c1))
    p.line([(0.24, 0.1), (0.1, 0.12), (0.06, 0.28), (0.14, 0.36)], 0.05, C(c1), layer='carve')
    p.line([(0.47, 0.6), (0.68, 0.6)], 0.04, C(c2), layer='raise')
    p.circle(0.63, 0.75, 0.025, C(c3), layer='raise')
    p.ell(0.6, 0.06, 0.12, 0.05, C(c1))


def g_fish(p, c1=TURQ, c2=BLUE, c3=GOLD):
    p.ell(0.45, 0.5, 0.36, 0.22, C(c1))
    p.poly([(0.1, 0.5), (0.0, 0.72), (0.0, 0.28)], C(c2))
    p.poly([(0.38, 0.7), (0.55, 0.86), (0.6, 0.68)], C(c2))
    p.circle(0.68, 0.56, 0.035, C('#2a2a3a'), layer='raise')
    for k in range(3): p.line(arcpts(0.38 + k * 0.1, 0.5, 0.05, 0.14, 120, 240, 6), 0.02)
    p.line(arcpts(0.62, 0.5, 0.05, 0.18, -70, 70, 6), 0.025, C(c3))


def g_star(p, c1=GOLD):
    pts = []
    for i in range(10):
        a = math.radians(90 + i * 36); r = 0.48 if i % 2 == 0 else 0.2
        pts.append((0.5 + r * math.cos(a), 0.5 + r * math.sin(a) * p.w / p.h))
    p.poly(pts, C(c1))


def g_feather(p, c1=TURQ, c2=BLUE, c3=GOLD):
    p.poly(arcpts(0.5, 0.15, 0.22, 0.85, 0, 180, 14), C(c1))
    p.line([(0.5, 0.0), (0.5, 0.95)], 0.04, C(c3), layer='raise')
    for k in range(5):
        y = 0.25 + k * 0.13; p.line([(0.5, y), (0.32, y + 0.08)], 0.02); p.line([(0.5, y), (0.68, y + 0.08)], 0.02)
    p.poly([(0.3, 0.15), (0.7, 0.15), (0.7, 0.24), (0.3, 0.24)], C(c2))


def g_waves(p, c1=BLUE, rows=3):
    for r in range(rows):
        y = 0.2 + r * 0.3; pts = [(i / 8, y + (0.1 if i % 2 else -0.1)) for i in range(9)]
        p.line(pts, 0.07, C(c1), layer='carve')


def g_palm(p, c1=GREEN, c2=OCHRE, c3=TURQ):
    p.line([(0.5, 0.0), (0.52, 0.4), (0.5, 0.7)], 0.08, C(c2), layer='carve')
    for a in (20, 55, 90, 125, 160):
        r = math.radians(a); p.line([(0.5, 0.7), (0.5 + 0.22 * math.cos(r), 0.7 + 0.18 * math.sin(r)), (0.5 + 0.42 * math.cos(r), 0.62 + 0.24 * math.sin(r))], 0.07, C(c1 if a % 2 else c3), layer='carve')
    p.circle(0.44, 0.62, 0.04, C(TERRA)); p.circle(0.56, 0.6, 0.04, C(TERRA))


def g_boat(p, c1=OCHRE, c2=CREAM, c3=TERRA):
    p.poly(arcpts(0.5, 0.36, 0.48, 0.24, 180, 360, 16) + [(0.98, 0.42), (0.02, 0.42)], C(c1))
    p.line([(0.5, 0.36), (0.5, 0.98)], 0.035, C(c3), layer='carve')
    p.poly([(0.52, 0.94), (0.8, 0.86), (0.8, 0.5), (0.52, 0.46)], C(c2))
    p.line([(0.0, 0.5), (0.06, 0.4)], 0.04, C(c1))


def g_jar(p, c1=TERRA, c2=BLUE):
    p.poly(arcpts(0.5, 0.42, 0.34, 0.4, 200, 340, 12) + [(0.66, 0.8), (0.66, 0.92), (0.34, 0.92), (0.34, 0.8)], C(c1))
    p.rect if False else None
    p.line([(0.2, 0.45), (0.8, 0.45)], 0.05, C(c2), layer='raise'); p.line([(0.25, 0.32), (0.75, 0.32)], 0.04, C(c2), layer='raise')


def g_papyrus(p, c1=GREEN, c2=TURQ):
    p.line([(0.5, 0.0), (0.5, 0.62)], 0.06, C(c1), layer='carve')
    p.poly([(0.5, 0.58), (0.14, 0.98), (0.86, 0.98)], C(c2))
    for k in range(5): p.line([(0.5, 0.62), (0.22 + k * 0.14, 0.96)], 0.018)


GLYPHS = dict(duck=g_duck, ibis=g_ibis, eye=g_eye, sun=g_sun, lotus=g_lotus, scarab=g_scarab, cat=g_cat, fish=g_fish,
              star=g_star, feather=g_feather, waves=g_waves, palm=g_palm, boat=g_boat, jar=g_jar, papyrus=g_papyrus)


def finish_relief(cv, depth=0.012, groove=0.004, bevel=0.006, fade=0.3, chips=0.25, seed=0, wrap=(False, False), stone_dark=0.1):
    """Tuval → (yükseklik m, üst renk RGBA, gölge RGB). Gömük kabartma: carve alanı depth kadar çukur (yumuşak kenar), raise
    ayrıntıları yarıya kalkar, groove ince oluk; boya alfası solma + dökülme gürültüsüyle; oyma içi taş biraz koyu."""
    ppm = cv.ppm
    car = blur(cv.arr('carve'), bevel * ppm, wrap); car = smoothstep(0.15, 0.85, car)
    rai = blur(cv.arr('raise'), bevel * 0.7 * ppm, wrap); rai = smoothstep(0.2, 0.8, rai)
    gro = blur(cv.arr('groove'), 0.0025 * ppm, wrap)
    h = -depth * car + depth * 0.55 * rai * car - groove * gro
    rgb, pa = cv.paint()
    sh = (h.shape[0], h.shape[1])
    n1 = fnoise(sh, 0.25 * ppm, seed + 1); n2 = fnoise(sh, 0.11 * ppm, seed + 2, 3)
    alpha = pa * np.clip(0.95 - fade * smoothstep(0.4, 0.75, n1), 0, 1)
    alpha *= 1.0 - smoothstep(0.72 - 0.08 * chips, 0.75 - 0.08 * chips, n2) * smoothstep(0.45, 0.6, n1)   # dökülme: seyrek, iri pul
    rgb = rgb * (0.92 + 0.16 * n1[..., None])
    over = np.concatenate([rgb, alpha[..., None]], -1)
    cav = cavity(h, ppm, 0.02, 60.0, wrap)
    shade = np.ones(sh + (3,), np.float32) * (1.0 - stone_dark * car)[..., None]
    shade *= (1.0 - 0.45 * cav)[..., None]
    return h, over, shade


# ------------------------------------------------------------------ geometri

def grid_obj(name, P, UV=None, mats=(), flip=False, smooth=True, col=None):
    """P: (nv, nu, 3) düzenli ızgara → dörtgen ağ; UV: (nv, nu, 2) → 'dec' katmanı. Yüz normali du × dv (flip: ters)."""
    nv, nu = P.shape[:2]
    idx = np.arange(nv * nu).reshape(nv, nu)
    a = idx[:-1, :-1]; b = idx[:-1, 1:]; c = idx[1:, 1:]; d = idx[1:, :-1]
    f = np.stack([a, b, c, d], -1).reshape(-1, 4)
    if flip: f = f[:, ::-1]
    me = bpy.data.meshes.new(name)
    me.vertices.add(nv * nu); me.vertices.foreach_set('co', P.reshape(-1).astype(np.float32))
    me.loops.add(f.size); me.loops.foreach_set('vertex_index', f.reshape(-1).astype(np.int32))
    me.polygons.add(len(f)); me.polygons.foreach_set('loop_start', np.arange(0, f.size, 4, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(len(f), 4, np.int32))
    me.update(); me.validate()
    if UV is not None:
        uvl = me.uv_layers.new(name='dec'); uvl.data.foreach_set('uv', UV.reshape(-1, 2)[f.reshape(-1)].reshape(-1).astype(np.float32))
    me.polygons.foreach_set('use_smooth', [smooth] * len(f))
    o = bpy.data.objects.new(name, me); (col or bpy.context.scene.collection).objects.link(o)
    for m in mats: o.data.materials.append(m)
    return o


def mesh_obj(name, verts, faces, mats=(), smooth=True, uvs=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, q)) for q in faces]); me.update()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for m in mats: o.data.materials.append(m)
    return o


def box_bm(size, cell):
    """Eksen başına çözünürlüklü ızgara kutu (bmesh, merkez 0): uzun ince kutular gereksiz sık bölünmez."""
    bm = bmesh.new(); h = [x / 2 for x in size]; n = [max(1, int(math.ceil(size[i] / cell))) for i in range(3)]
    X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
    faces = [(V((-h[0], -h[1], h[2])), X * size[0], Y * size[1], n[0], n[1]), (V((-h[0], h[1], -h[2])), X * size[0], -Y * size[1], n[0], n[1]),
             (V((h[0], -h[1], -h[2])), Y * size[1], Z * size[2], n[1], n[2]), (V((-h[0], h[1], -h[2])), -Y * size[1], Z * size[2], n[1], n[2]),
             (V((h[0], h[1], -h[2])), -X * size[0], Z * size[2], n[0], n[2]), (V((-h[0], -h[1], -h[2])), X * size[0], Z * size[2], n[0], n[2])]
    for (o, du, dv, nu, nv) in faces:
        g = [[bm.verts.new(o + du * (i / nu) + dv * (j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
        for j in range(nv):
            for i in range(nu): bm.faces.new((g[j][i], g[j][i + 1], g[j + 1][i + 1], g[j + 1][i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return bm


def rounded_box(name, size, r, cell=0.03, mats=(), loc=(0, 0, 0), rot=(0, 0, 0), chips=0.0, lump=0.0, seed=0, flat_bottom=True):
    """Yuvarlak kenarlı kutu (ızgara kutu → yuvarlatılmış kutu yüzeyine izdüşüm), isteğe bağlı kenar kırığı + hafif yumruluk.
    chips: kenara yakın köşelerde içe göçük (m); lump: yüzey dalgası (m). Taban (z−) düz kalır (yere oturur)."""
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    bm = box_bm(size, cell)
    R = random.Random(seed); so = V((R.uniform(0, 50), R.uniform(0, 50), R.uniform(0, 50)))
    for v in bm.verts:
        p = v.co.copy()
        q = V((max(-hx + r, min(hx - r, p.x)), max(-hy + r, min(hy - r, p.y)), max(-hz + r, min(hz - r, p.z))))
        d = p - q
        if d.length > 1e-9: p = q + d.normalized() * r
        n = (p - q).normalized() if (p - q).length > 1e-9 else V((0, 0, 1))
        if chips or lump:
            ex = [1.0 - min(1.0, (hh - abs(c)) / max(0.08, r * 2.5)) for c, hh in ((p.x, hx), (p.y, hy), (p.z, hz))]
            ex.sort(reverse=True); edge = ex[1]
            dn = MN.noise(p * 5.0 + so); dn2 = MN.noise(p * 13.0 + so * 1.3)
            k = -chips * max(0.0, dn * 1.6 + 0.35 * dn2 - 0.15) * edge ** 1.5 + lump * (MN.noise(p * 2.2 + so) * 0.7 + 0.3 * dn2)
            if flat_bottom and p.z < -hz + r * 1.2: k *= max(0.0, (p.z + hz) / (r * 1.2))
            p = p + n * k
        v.co = p
    o = A.link_mesh(name, bm, list(mats)); A.smooth(o)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o


def lathe_grid(name, prof, n=32, mats=(), loc=(0, 0, 0), rfn=None, uv=True, cap_top=False):
    """Döner yüzey: prof = [(r, z)] (alttan üste), n kenar; rfn(theta, z, r) → r' (oluk/yaprak). 'dec' UV: u = θ/2π, v = yay oranı."""
    th = np.linspace(0, TAU, n + 1)
    rs = np.array([p[0] for p in prof], np.float32); zs = np.array([p[1] for p in prof], np.float32)
    seg = np.sqrt(np.diff(rs) ** 2 + np.diff(zs) ** 2); s = np.concatenate([[0], np.cumsum(seg)]); s /= max(s[-1], 1e-6)
    P = np.zeros((len(prof), n + 1, 3), np.float32); UV = np.zeros((len(prof), n + 1, 2), np.float32)
    for i, (r, z) in enumerate(prof):
        for j, t in enumerate(th):
            rr = rfn(t, z, r) if rfn else r
            P[i, j] = (loc[0] + rr * math.cos(t), loc[1] + rr * math.sin(t), loc[2] + z)
            UV[i, j] = (t / TAU, s[i])
    o = grid_obj(name, P, UV if uv else None, mats)
    if cap_top:
        pass
    weld(o)
    return o


def weld(o, dist=1e-5):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist); bm.to_mesh(o.data); bm.free()


def disc(name, r, z, n=32, mats=(), loc=(0, 0), down=False):
    verts = [(loc[0] + r * math.cos(i / n * TAU), loc[1] + r * math.sin(i / n * TAU), z) for i in range(n)]
    f = list(range(n)) if not down else list(reversed(range(n)))
    return mesh_obj(name, verts, [f], mats)


def planar_dec_uv(o, origin, uaxis, vaxis, size_u, size_v, face_dir=None, min_dot=0.6):
    """'dec' UV = düzleme izdüşüm: u = (p−o)·uaxis/size_u, v = (p−o)·vaxis/size_v (dünya). face_dir verilirse ona bakmayan yüzler
    (−5, −5)'e (görüntü dışı → CLIP ile boyasız)."""
    me = o.data; mw = o.matrix_world; m3 = mw.to_3x3()
    uvl = me.uv_layers.get('dec') or me.uv_layers.new(name='dec')
    org, ua, va = V(origin), V(uaxis).normalized(), V(vaxis).normalized()
    fd = V(face_dir).normalized() if face_dir else None
    for poly in me.polygons:
        ok = True
        if fd is not None: ok = (m3 @ poly.normal).normalized().dot(fd) > min_dot
        for li in poly.loop_indices:
            if not ok: uvl.data[li].uv = (-5.0, -5.0); continue
            p = mw @ me.vertices[me.loops[li].vertex_index].co - org
            uvl.data[li].uv = (p.dot(ua) / size_u, p.dot(va) / size_v)


# ------------------------------------------------------------------ pişirme, önizleme, boy tablosu

def out_dir(name):
    d = os.path.join(ENV, name); os.makedirs(d, exist_ok=True); return os.path.join(d, name)


def obj_tris(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear(); return n


def build_low2(objs, decim=(), weights=()):
    """BK.build_low gibi; decim değeri > 1 ise MUTLAK üçgen hedefi (nesne başına), ≤ 1 ise oran. Alt bölmeli küreler oranla
    öngörülemez büyüyordu (16 işaret lambası 13 bin üçgen)."""
    out = []
    for o in objs:
        if o.type != 'MESH': continue
        v = BK._lookup(decim, o.name, 1.0)
        r = v if v <= 1.0 else min(1.0, v / max(1, obj_tris(o)))
        out += BK.build_low([o], [(r'.', r)], weights)
    return out


def bake_auto(name, high, decim=(), weights=(), tex=512, budget=None, exclude=(), ao_dist=0.35, ao_strength=0.55, cage=0.03, ray=0.12,
              cull=True, low_extra=(), **kw):
    """Engeller/arka plan: hedef = taslağın aynı ağı (decim: parça içi sadeleşme), exclude: hedefe girmeyen yalnız-taslak parçalar
    (düzenli ifade), low_extra: elle kurulmuş hedef parçaları. Döner: üçgen sayısı."""
    tex = int(os.environ.get('POFI_TEX', '0') or 0) or tex
    srcs = [o for o in high if not any(re.search(p, BK._key(o.name)) for p in exclude)]
    low = build_low2(srcs, decim, weights) + list(low_extra)
    tris = PB.export_proxy(out_dir(name), high, low, target=budget, size=tex, nsize=tex, cage=cage, ray=ray, cull_hidden=cull,
                           uv_weight='uvw', dilate=16, ao_dist=ao_dist, ao_strength=ao_strength, **kw)
    print(name, 'üçgen', tris, flush=True)
    return tris


def tag_uvw(o, w=1.0, down=0.45):
    """Elle kurulan hedef parçası: UV katsayısı yüz niteliği ('uvw'; build_low ile aynı kural)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    lay = bm.faces.layers.float.new('uvw'); bm.normal_update(); m3 = o.matrix_world.to_3x3()
    for f in bm.faces:
        nz = (m3 @ f.normal).normalized().z if f.normal.length > 0 else 0.0
        f[lay] = w * (down if nz < -0.5 else 1.0)
    bm.to_mesh(o.data); bm.free()
    return o


def preview(name, png, yaw=35.0, pitch=22.0, size=(800, 640), dist=None, target=None, lens=50, samples=40, back=True, light=None):
    """Oyun modelinin (FBX + dokular) Cycles çizimi; arka yüzler (oyunda çizilmez) macenta görünür → ters normal denetimi.
    light(sc): isteğe bağlı ışık kurulumu (ör. Ay sahnesi)."""
    from mathutils import Vector as Vv
    kit.reset()
    if light: light(bpy.context.scene)
    p = out_dir(name)
    bpy.ops.import_scene.fbx(filepath=p + '.fbx')
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    m = game_mat(p, back)
    for o in obs: o.data.materials.clear(); o.data.materials.append(m)
    lo = Vv((1e9,) * 3); hi = Vv((-1e9,) * 3)
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ Vv(c); lo = Vv(map(min, lo, w)); hi = Vv(map(max, hi, w))
    ctr = Vv(target) if target else (lo + hi) / 2; r = (hi - lo).length * 0.5; d = dist or r * 2.5
    sc = bpy.context.scene; sc.cycles.samples = samples; sc.render.resolution_x, sc.render.resolution_y = size
    cam = bpy.data.cameras.new('cam'); cam.lens = lens; co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    yr, pr = math.radians(yaw), math.radians(pitch)
    co.location = ctr + Vv((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    cam.clip_end = max(200.0, d * 4)
    sc.render.filepath = png; bpy.ops.render.render(write_still=True)
    return lo, hi


def game_mat(path_noext, back=True, name=None):
    """Oyundaki gibi tek doku malzemesi (renk + normal); back: arka yüz macenta (denetim)."""
    m = bpy.data.materials.new(name or ('game_' + os.path.basename(path_noext))); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.85
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = bpy.data.images.load(path_noext + '_basecolor.png', check_existing=True)
    nt.links.new(tc.outputs['Color'], bsdf.inputs['Base Color'])
    if os.path.exists(path_noext + '_normal.png'):
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(path_noext + '_normal.png', check_existing=True)
        tn.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if back:
        out = nt.nodes['Material Output']; geo = nt.nodes.new('ShaderNodeNewGeometry'); em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1, 0, 1, 1); mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(geo.outputs['Backfacing'], mx.inputs['Fac']); nt.links.new(bsdf.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m


def draft(png, yaw=35.0, pitch=22.0, size=(800, 640), samples=24, dist=None, target=None, light=None):
    """Taslağın (pişirmesiz) çizimi."""
    import koy_eskitme as KE
    if light: light(bpy.context.scene)
    lo, hi = KE.scene_bounds(); ctr = V(target) if target else (lo + hi) / 2; r = (hi - lo).length * 0.5; d = dist or r * 2.5
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = size
    cam = bpy.data.cameras.new('dcam'); co = bpy.data.objects.new('dcam', cam); sc.collection.objects.link(co); sc.camera = co
    cam.clip_end = max(200.0, d * 4)
    yr, pr = math.radians(yaw), math.radians(pitch)
    co.location = ctr + V((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = png; bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co)


def fbx_stats(name):
    """Dışa aktarılmış modelin üçgen sayısı, sınırları (Blender ekseni), doku boyları."""
    from PIL import Image
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p = out_dir(name); bpy.ops.import_scene.fbx(filepath=p + '.fbx'); bpy.context.view_layer.update()
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    tris = sum(sum(len(pl.vertices) - 2 for pl in o.data.polygons) for o in obs)
    pts = [o.matrix_world @ V(c) for o in obs for v in [0] for c in [vv.co for vv in o.data.vertices]]
    lo = [min(p_[i] for p_ in pts) for i in range(3)]; hi = [max(p_[i] for p_ in pts) for i in range(3)]
    tex = {k: Image.open(p + k + '.png').size[0] for k in ('_basecolor', '_normal') if os.path.exists(p + k + '.png')}
    return dict(tris=tris, lo=[round(x, 3) for x in lo], hi=[round(x, 3) for x in hi], tex=tex)


def sweep(name, pts, radii, mats=(), sides=12, caps=True):
    """Yol boyunca boru (paralel taşıma çerçeveli; Bezier tutamak taşması yok). pts: [(x,y,z)], radii: nokta başına yarıçap."""
    P = [V(p) for p in pts]; n = len(P)
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    N = T[0].orthogonal().normalized(); frames = []
    for i in range(n):
        if i:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-6:
                ang = T[i - 1].angle(T[i]); from mathutils import Matrix
                N = Matrix.Rotation(ang, 3, b.normalized()) @ N
        frames.append((N.copy(), T[i].cross(N).normalized()))
    G = np.zeros((n, sides + 1, 3))
    for i in range(n):
        Nn, Bn = frames[i]
        for j in range(sides + 1):
            a = j / sides * TAU; G[i, j] = tuple(P[i] + (Nn * math.cos(a) + Bn * math.sin(a)) * radii[i])
    o = grid_obj(name, G, None, mats)
    weld(o)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    if caps:
        for i in (0, n - 1):
            ring = [v for v in bm.verts if (v.co - P[i]).length < radii[i] * 1.01 + 1e-5 and abs((v.co - P[i]).dot(T[i])) < 1e-4]
            if len(ring) >= 3:
                c = P[i]; Nn, Bn = frames[i]
                ring.sort(key=lambda v: math.atan2((v.co - c).dot(Bn), (v.co - c).dot(Nn)))
                try: bm.faces.new(ring)
                except ValueError: pass
    bm.normal_update()
    ctr = sum((V(p) for p in pts), V((0, 0, 0))) / n
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o
