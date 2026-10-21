# Ada v6 taslağı (21 Ekim 2026): haritanın son hâli — 56 referansın sanat yönüyle büyütülmüş ada.
# Arazi terrain_v6.py'den (numpy, oyunla ortak ızgara); burada boyanır, bitki/kaya/bina yerleşir, çekimler alınır.
# Referans görseller yalnız kalite/hava hedefi; hiçbir biçim/doku kopyalanmaz, hepsi kodla özgün.
#   /tmp/claude-0/bpyenv/bin/python -I island_v6.py -- <terr.npz> <çıktı_klasörü> <çekim,...> [örnek] [ölçek]
import sys, os, json, math, random, time
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', 'v5'), os.path.join(HERE, '..', 'v4')): sys.path.insert(0, p)
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, noise as MN
import kit_v6 as K
import terrain_v6 as TV
import island_v6_near as NR
NEAR = []
CLOUDS = []

ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
PETS = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Pets')
T0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - T0), *a, flush=True)

def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0); return t * t * (3 - 2 * t)
def C3(h): return np.array(K.srgb(h), np.float32)
def mix(a, b, t): return a + (b - a) * (t[..., None] if np.ndim(t) else t)

# ------------------------------------------------------------------ arazi

class Land:
    def __init__(self, path):
        d = np.load(path); self.d = {k: d[k] for k in d.files}
        self.h = self.d['h']; self.nz, self.nx = self.h.shape; self.step = TV.STEP; self.x0, self.z0 = TV.X0, TV.Z0
        xs = np.arange(self.nx, dtype=np.float32) * self.step + self.x0; zs = np.arange(self.nz, dtype=np.float32) * self.step + self.z0
        self.X, self.Z = np.meshgrid(xs, zs)
        self.slope = self.d['slope']; self.slope_b = TV.blur(self.slope, 0.8)
        self.lay = TV.layout_json()
    def idx(self, x, z):
        i = np.clip(np.round((np.asarray(x) - self.x0) / self.step).astype(int), 0, self.nx - 1)
        j = np.clip(np.round((np.asarray(z) - self.z0) / self.step).astype(int), 0, self.nz - 1); return i, j
    def height(self, x, z): return TV.height_at(self.d, x, z)
    def get(self, key, x, z):
        i, j = self.idx(x, z); a = self.d[key] if key in self.d else getattr(self, key); return a[j, i]

FLOWER_FIELDS = [(-46, 3, 11, 'b'), (-38, -10, 8, 'b'), (-52, -6, 6, 'o'), (-30, 16, 6, 'b'), (8, -12, 5, 'o'), (-8, -12, 5, 'b'), (30, -18, 6, 'b'),
                 (40, -4, 6, 'o'), (58, -4, 5, 'b'), (-6, 40, 8, 'b'), (14, 40, 6, 'o'), (-50, 30, 6, 'b')]

def biome_fields(L):
    X, Z = L.X, L.Z; d = L.d
    def gauss(cx, cz, r): return np.exp(-((X - cx) ** 2 + (Z - cz) ** 2) / (2 * r * r))
    f = {}
    f['forest'] = np.clip(gauss(50, 20, 9) * 1.4, 0, 1) * ss(9.5, 10.5, L.h)
    f['meadow'] = np.clip(gauss(-44, 0, 20) * 1.4 + gauss(-28, 8, 10), 0, 1)
    f['village'] = np.clip(gauss(0, -22, 22) * 1.3, 0, 1)
    f['upper'] = np.clip(d['t_upper'] + d['t_north_peak'] * 0.8, 0, 1)
    f['snowpeak'] = np.clip(gauss(-44, 54, 20) * 1.5, 0, 1)
    f['spire'] = np.clip(d['t_spire1'], 0, 1)
    return f

def terrain_colors(L, B):
    X, Z, h, d = L.X, L.Z, L.h, L.d
    n1 = TV.fbm(X, Z, 1 / 14.0, 201, 4) * 0.5 + 0.5; n2 = TV.fbm(X, Z, 1 / 4.0, 203, 3) * 0.5 + 0.5
    n3 = TV.fbm(X, Z, 1 / 1.3, 205, 2) * 0.5 + 0.5; n4 = TV.fbm(X, Z, 1 / 40.0, 207, 3) * 0.5 + 0.5
    # çim: canlı limon yeşili, açık lekeler, ormanda koyu, kuru sarı alanlar
    g = mix(C3('#4c9a2a'), C3('#7cc63d'), n1)
    g = mix(g, C3('#a9d64e'), ss(0.6, 0.85, n2) * 0.55)
    g = mix(g, C3('#3a7a2c'), B['forest'] * 0.75)
    g = mix(g, C3('#5a9a3a'), B['snowpeak'] * 0.5)
    dry = ss(0.62, 0.8, n4) * (1 - B['meadow']) * (1 - B['forest']); L.dry = dry.astype(np.float32)
    g = mix(g, C3('#b8b052'), dry * 0.45)
    g = mix(g, C3('#c2a75c'), ss(3.2, 1.5, d['pathd']) * 0.4)                     # patika kenarı aşınmış
    # çiçek lekeleri (kuşbakışı): mavi çan çiçeği + turuncu; benekli
    fb = ss(0.6, 0.7, TV.fbm(X, Z, 1 / 8.0, 211, 3) * 0.5 + 0.5) * np.clip(B['meadow'] * 1.2 + B['upper'] * 0.45 + B['village'] * 0.2, 0, 1)
    fo = ss(0.66, 0.74, TV.fbm(X, Z, 1 / 7.0, 213, 3) * 0.5 + 0.5) * np.clip(B['meadow'] + B['upper'] * 0.4 + B['village'] * 0.3, 0, 1)
    for (fx_, fz_, fr_, kind) in FLOWER_FIELDS:
        w_ = ss(fr_, fr_ * 0.4, np.hypot(X - fx_, Z - fz_) + 3.0 * TV.fbm(X, Z, 1 / 5.0, 215, 2)) * ss(0.25, 0.45, TV.fbm(X, Z, 1 / 3.0, 217, 2) * 0.5 + 0.5)
        if kind == 'b': fb = np.maximum(fb, w_)
        else: fo = np.maximum(fo, w_)
    sp = ss(0.45, 0.65, n3)
    g = mix(g, mix(C3('#5d62d8'), C3('#8d84ee'), n2), fb * sp * 0.9)
    g = mix(g, C3('#ef9a46'), fo * (1 - sp) * 0.85)
    c = g
    # kaya: sıcak leylak-gri; yatay tabaka bantları + dikey çizgiler (x,z yüksek frekans → yarda dikey iner)
    band = np.sin(h * (2 * math.pi / 1.6) + TV.fbm(X, Z, 1 / 6.0, 221, 2) * 2.0) * 0.5 + 0.5
    streak = TV.fbm(X * 3.0, Z * 3.0, 1 / 2.2, 223, 3) * 0.5 + 0.5
    rk = mix(C3('#a3929a'), C3('#d0c2b8'), band * 0.7 + 0.15)
    rk = mix(rk, C3('#6e5f76'), ss(0.52, 0.78, streak) * 0.7)
    rk = mix(rk, C3('#e0d4c8'), ss(0.3, 0.12, streak) * 0.5)
    rk = mix(rk, C3('#6f6872'), ss(1.6, 0.0, h) * 0.55)                              # deniz kıyısında ıslak koyu
    rk = mix(rk, C3('#7f7b88'), B['snowpeak'] * 0.4)
    rw = np.maximum(ss(0.85, 1.25, L.slope + (n2 - 0.5) * 0.35), ss(0.75, 1.1, L.slope_b) * 0.45)   # basamak üstleri çimenli (çimen kayadan taşar)
    rw = np.clip(rw, 0, 1) * (1 - ss(0.0, 0.3, TV.blur(d['snowpath'], 2.5)))
    rw = np.maximum(rw, d['snow'] * ss(0.9, 1.4, L.slope) * (1 - ss(0.0, 0.3, TV.blur(d['snowpath'], 2.5))))   # karlı dağda dik yüz = kaya çıkıntısı
    L.dispw = None
    c = mix(c, rk, rw)
    # kum: kumsal + kanyon tabanı; ıslak kıyı koyu; su altı açık
    sandc = mix(C3('#e9d4a4'), C3('#f2e2bb'), n2)
    sandc = mix(sandc, C3('#c4ab80'), ss(0.45, 0.05, h) * ss(-0.6, 0.0, h))
    sandc = mix(sandc, C3('#a69f9c'), ss(0.62, 0.75, n3) * np.clip(d['canyon'], 0, 1) * 0.6)  # kanyonda çakıl
    sw = np.clip(d['sand'] * (1 - rw * 0.8), 0, 1)
    c = mix(c, sandc, sw)
    c = mix(c, C3('#d8c397'), (h < 0) * 1.0)                                          # deniz tabanı (sığda görünür)
    c = mix(c, C3('#9c8e8a'), (h < 0) * ss(-1.0, -4.0, h) * 0.6)
    # kıyı kayalıkları (kumsalsız kıyı): ıslak çakıl
    cx_, cz_ = TV.SPOTS['camp']; dc = np.hypot(X - cx_, Z - cz_) + 0.8 * TV.fbm(X, Z, 1 / 2.0, 231, 2)
    c = mix(c, mix(C3('#b98a52'), C3('#d2a86c'), n2), ss(6.8, 5.6, dc) * (1 - rw))                       # kamp açıklığı: toprak
    # patika
    pc = mix(C3('#b98c55'), C3('#d1aa72'), n2)
    c = mix(c, pc, np.clip(ss(2.1, 1.1, d['pathd']) * (1 - rw), 0, 1) * 0.92)
    # kar: beyaz, dik yerde kaya şeritleri kalır
    snw = np.clip(d['snow'] * (1 - ss(1.25, 2.1, L.slope + (n3 - 0.5) * 0.8) * 0.85), 0, 1)
    snw = np.maximum(snw, np.clip(TV.blur(d['snowpath'], 2.0) * 3, 0, 1) * ss(0.2, 0.5, d['snow']))
    L.dispw = (rw * (1 - ss(0.35, 0.7, snw))).astype(np.float32)
    L.gravel = np.clip((np.clip(d['canyon'], 0, 1) * 0.95 + d['sand'] * ss(0.35, 0.9, L.slope_b) * ss(2.5, 1.0, h) * 0.8 + ss(0.3, 0.7, L.slope_b) * ss(0.7, 0.35, L.slope) * ss(0.45, 0.7, TV.fbm(X, Z, 1 / 2.5, 251, 2) * 0.5 + 0.5) * 0.85) * (1 - rw) * (1 - d['path'] * 0.35), 0, 1).astype(np.float32)
    c = mix(c, mix(C3('#cdd8ea'), C3('#e6edf7'), n2), snw)
    # karlı patika: sıkışmış, hafif mavi-gri, ayak izi benekli
    pk = mix(C3('#7f8daa'), C3('#9aa7bf'), n2); pk = mix(pk, C3('#7a6550'), ss(0.55, 0.72, n3) * 0.85)   # sıkışmış kar + eriyip açılmış toprak lekeleri
    pk = mix(pk, C3('#7f8ea8'), ss(0.55, 0.7, TV.fbm(X * 3, Z * 3, 1 / 0.6, 241, 2) * 0.5 + 0.5) * 0.5)     # ayak izi benekleri
    c = mix(c, pk, d['snowpath'] * 0.95)
    # göl kıyısı
    dl = np.hypot(X - TV.LAKE['x'], Z - TV.LAKE['z'])
    c = mix(c, C3('#7a6a48'), ss(0.35, 0.0, np.abs(h - TV.LAKE['level'])) * (dl < TV.LAKE['r'] + 6) * 0.6)
    L.fb, L.fo = (fb * sp).astype(np.float32), (fo * (1 - sp)).astype(np.float32); L.snw = snw.astype(np.float32)
    L.gw = np.clip((1 - rw) * (1 - np.clip(d['sand'] * 1.3, 0, 1)) * (1 - ss(2.0, 1.0, d['pathd']) * 0.97) * (1 - ss(6.6, 5.4, dc) * 0.95) * (1 - ss(0.01, 0.08, d['snow'])) * (h > 0.5), 0, 1).astype(np.float32)
    return c.astype(np.float32), rw.astype(np.float32)

def terrain_mesh(L, cols, rw, crop=None, snw=None):
    """İki nesne: kaya yüzleri (gerçek kabartma: uyarlamalı alt bölme + yer değiştirme) ve geri kalan zemin."""
    nz, nx = L.h.shape
    verts = np.stack([L.X.ravel(), L.Z.ravel(), L.h.ravel()], -1).astype(np.float32)
    ii = np.arange(nx - 1); jj = np.arange(nz - 1)
    I, J = np.meshgrid(ii, jj); a = (J * nx + I).ravel()
    quads = np.stack([a, a + 1, a + nx + 1, a + nx], -1)
    sn = (L.snw if snw is None else snw).ravel(); rwv = rw.ravel()
    isrock = rwv[quads].max(1) > 0.03
    mat = terrain_mat(); objs = []
    for name, qs, adaptive in (('terrain', quads[~isrock], False), ('terrain_rock', quads[isrock], True)):
        uv_, inv = np.unique(qs.ravel(), return_inverse=True); q2 = inv.reshape(-1, 4)
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(uv_)); me.vertices.foreach_set('co', verts[uv_].ravel())
        me.loops.add(q2.size); me.loops.foreach_set('vertex_index', q2.ravel().astype(np.int32))
        me.polygons.add(len(q2)); me.polygons.foreach_set('loop_start', (np.arange(len(q2)) * 4).astype(np.int32))
        me.polygons.foreach_set('loop_total', np.full(len(q2), 4, np.int32))
        me.update(); me.validate(clean_customdata=False)
        me.polygons.foreach_set('use_smooth', np.ones(len(q2), bool))
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); c4 = np.ones((len(uv_), 4), np.float32); c4[:, :3] = cols.reshape(-1, 3)[uv_]
        ca.data.foreach_set('color', c4.ravel())
        at = me.attributes.new('rock', 'FLOAT', 'POINT'); at.data.foreach_set('value', rwv[uv_])
        at = me.attributes.new('snow', 'FLOAT', 'POINT'); at.data.foreach_set('value', sn[uv_])
        at = me.attributes.new('dispw', 'FLOAT', 'POINT'); at.data.foreach_set('value', L.dispw.ravel()[uv_])
        at = me.attributes.new('gravel', 'FLOAT', 'POINT'); at.data.foreach_set('value', L.gravel.ravel()[uv_])
        o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.data.materials.append(mat)
        if adaptive:
            # uyarlamalı bölme bu makinede belleği aşıyor: sabit 2 kat basit bölme (0,2 m → 5 cm), yer değiştirme köşelere
            md = o.modifiers.new('sub', 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = 0; md.render_levels = int(os.environ.get('ROCK_SUB', '2'))
            log('kaya yüzü dörtgen', len(q2))
        objs.append(o)
    return objs[0]

def terrain_mat():
    """Köşe rengi + el boyaması gürültü tonu. Kayada (rock özniteliği): yatay tabaka çizgileri (dünya z), dikey ince çatlaklar
    (z'de uzamış gürültünün eş-değer çizgileri), basamak tümseği. Karda hafif rüzgâr dalgası tümseği."""
    m = bpy.data.materials.new('terrain_m'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links; b = N['Principled BSDF']
    def node(t, **kw):
        n = N.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def math_(op, a, b_=None, v=None):
        n = node('ShaderNodeMath', operation=op)
        if isinstance(a, (int, float)): n.inputs[0].default_value = a
        else: L.new(a, n.inputs[0])
        if b_ is not None:
            if isinstance(b_, (int, float)): n.inputs[1].default_value = b_
            else: L.new(b_, n.inputs[1])
        return n.outputs[0]
    def mr(sock, a, b_, c=0.0, d=1.0):
        n = node('ShaderNodeMapRange'); n.inputs[1].default_value = a; n.inputs[2].default_value = b_; n.inputs[3].default_value = c; n.inputs[4].default_value = d
        L.new(sock, n.inputs[0]); return n.outputs[0]
    vc = node('ShaderNodeVertexColor', layer_name='Col')
    rk = node('ShaderNodeAttribute', attribute_name='rock').outputs['Fac']
    sw = node('ShaderNodeAttribute', attribute_name='snow').outputs['Fac']
    tc = node('ShaderNodeTexCoord'); sep = node('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    nz = node('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.35; nz.inputs['Detail'].default_value = 5; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    ov = node('ShaderNodeMix', data_type='RGBA', blend_type='OVERLAY'); ov.inputs['Factor'].default_value = 0.2
    L.new(vc.outputs['Color'], ov.inputs[6]); L.new(nz.outputs['Color'], ov.inputs[7])
    # tabaka: z/1.35 + yatay gürültü → kesir; kesirin başı koyu ince çizgi, sonu açık kenar
    wn = node('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 0.08; wn.inputs['Detail'].default_value = 2; L.new(tc.outputs['Object'], wn.inputs['Vector'])
    zz = math_('MULTIPLY_ADD', sep.outputs['Z'], 1 / 2.3); L.new(wn.outputs['Fac'], zz.node.inputs[2]); zz.node.inputs[2].default_value = 0
    zf = math_('FRACT', zz)
    line = mr(zf, 0.0, 0.05, 0.78, 1.0)                                   # 0..0.05: koyu ince çizgi
    lite = mr(zf, 0.85, 1.0, 1.0, 1.1)                                    # üst kenar açık
    # dikey çatlak: (x,y) yüksek, z düşük frekanslı gürültünün 0.5 eş-değer çizgisi
    mp = node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 0.035); L.new(tc.outputs['Object'], mp.inputs[0])
    vn = node('ShaderNodeTexNoise'); vn.inputs['Scale'].default_value = 0.32; vn.inputs['Detail'].default_value = 2.5; L.new(mp.outputs[0], vn.inputs['Vector'])
    ab = math_('ABSOLUTE', math_('SUBTRACT', vn.outputs['Fac'], 0.5))
    crack = mr(ab, 0.0, 0.035, 0.62, 1.0)
    vn2 = node('ShaderNodeTexNoise'); vn2.inputs['Scale'].default_value = 2.2; vn2.inputs['Detail'].default_value = 4; L.new(mp.outputs[0], vn2.inputs['Vector'])
    blot = mr(vn2.outputs['Fac'], 0.3, 0.7, 0.82, 1.08)
    f = math_('MULTIPLY', math_('MULTIPLY', line, lite), math_('MULTIPLY', crack, blot))
    rkn = math_('MULTIPLY', rk, math_('SUBTRACT', 1.0, sw))
    fr = math_('ADD', math_('MULTIPLY', math_('SUBTRACT', f, 1.0), rkn), 1.0)   # yalnız (karsız) kayada
    cm = node('ShaderNodeCombineXYZ'); [L.new(fr, cm.inputs[k]) for k in range(3)]
    dk = node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); dk.inputs['Factor'].default_value = 1.0
    L.new(ov.outputs[2], dk.inputs[6]); L.new(cm.outputs[0], dk.inputs[7]); L.new(dk.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.9; b.inputs['Specular IOR Level'].default_value = 0.25
    # tümsek: kayada çatlak + tabaka basamağı, karda rüzgâr dalgası, çimde ince
    hb = math_('MULTIPLY', math_('ADD', math_('MULTIPLY', crack, 0.6), math_('MULTIPLY', zf, 0.5)), rkn)
    sn = node('ShaderNodeTexWave', wave_type='BANDS'); sn.inputs['Scale'].default_value = 0.6; sn.inputs['Distortion'].default_value = 8; sn.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], sn.inputs['Vector'])
    hb = math_('ADD', hb, math_('MULTIPLY', sn.outputs['Fac'], math_('MULTIPLY', sw, 0.15)))
    gn = node('ShaderNodeTexNoise'); gn.inputs['Scale'].default_value = 9.0; gn.inputs['Detail'].default_value = 3; L.new(tc.outputs['Object'], gn.inputs['Vector'])
    hb = math_('ADD', hb, math_('MULTIPLY', gn.outputs['Fac'], 0.06))
    bn = node('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.3; bn.inputs['Distance'].default_value = 0.3
    L.new(hb, bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    # GERÇEK KABARTMA (metre): her tabakanın üst kısmı dışa taşar, alttaki tabakanın üstüne saçak yapar (gölge düşer);
    # dikey çatlaklar içe oyuk; büyük kaya blokları arasında derz; ince yüzey pürüzü. Yalnız karsız kayada.
    ledge = math_('SUBTRACT', mr(zf, 0.0, 0.75, 0.0, 0.26), mr(zf, 0.8, 1.0, 0.0, 0.18))
    crk = math_('MULTIPLY', mr(ab, 0.0, 0.07, -0.42, 0.0), 1.0)
    mpb = node('ShaderNodeMapping'); mpb.inputs['Scale'].default_value = (1.0, 1.0, 0.55); L.new(tc.outputs['Object'], mpb.inputs[0])
    vo = node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); vo.inputs['Scale'].default_value = 0.26; L.new(mpb.outputs[0], vo.inputs['Vector'])
    blk = mr(vo.outputs['Distance'], 0.0, 0.09, -0.28, 0.0)
    rough = mr(vn2.outputs['Fac'], 0.3, 0.7, -0.06, 0.06)
    dw = node('ShaderNodeAttribute', attribute_name='dispw').outputs['Fac']
    disp = math_('MULTIPLY', math_('ADD', math_('ADD', ledge, crk), math_('ADD', blk, rough)), dw)
    dn = node('ShaderNodeDisplacement'); dn.inputs['Midlevel'].default_value = 0.0; dn.inputs['Scale'].default_value = 1.0
    L.new(disp, dn.inputs['Height']); L.new(dn.outputs['Displacement'], N['Material Output'].inputs['Displacement'])
    # derzlerde ve çatlak diplerinde renk de koyulaşsın (gölgeyi destekler)
    try: m.displacement_method = 'BOTH'
    except Exception: m.cycles.displacement_method = 'BOTH'
    # EL BOYAMASI IŞIK-GÖLGE (kullanıcı örneği): kabartmanın kendi biçiminden — çıkıntı kenarında açık parıltı,
    # saçak altı / çatlak içi / blok derzi koyu; düz yüzde basamaklı (posterize) ton lekeleri.
    def band(sock, a0, a1, b1, b0):      # a0→a1 artar, b1→b0 azalır (bant)
        return math_('MINIMUM', mr(sock, a0, a1), mr(sock, b0, b1))
    lip = band(zf, 0.66, 0.78, 0.83, 0.86)                                # tabaka çıkıntısının üst kenarı
    under = mr(zf, 0.86, 0.97, 1.0, 0.0)                                  # saçak altı gölgesi (0..1)
    crim = band(ab, 0.055, 0.075, 0.1, 0.14)                              # çatlak dudağı
    brim = band(vo.outputs['Distance'], 0.08, 0.1, 0.13, 0.17)            # blok kenarı
    bgap = mr(vo.outputs['Distance'], 0.0, 0.05, 1.0, 0.0)                # blok derzi
    pn = node('ShaderNodeTexNoise'); pn.inputs['Scale'].default_value = 0.6; pn.inputs['Detail'].default_value = 1.0; L.new(tc.outputs['Object'], pn.inputs['Vector'])
    pst = math_('MULTIPLY', math_('FLOOR', math_('MULTIPLY', pn.outputs['Fac'], 4.0)), 0.25)   # 4 basamaklı ton
    rim = math_('MINIMUM', math_('ADD', math_('ADD', lip, crim), brim), 1.0)
    dark = math_('MINIMUM', math_('ADD', math_('MULTIPLY', under, 0.8), bgap), 1.0)
    lit = node('ShaderNodeMix', data_type='RGBA'); lit.inputs[7].default_value = K.srgb('#f3ece3') + (1,)
    L.new(math_('MULTIPLY', math_('MULTIPLY', rim, 0.75), rkn), lit.inputs['Factor']); L.new(dk.outputs[2], lit.inputs[6])
    shd = node('ShaderNodeMix', data_type='RGBA'); shd.inputs[7].default_value = K.srgb('#4a3f52') + (1,)
    L.new(math_('MULTIPLY', math_('MULTIPLY', dark, 0.7), rkn), shd.inputs['Factor']); L.new(lit.outputs[2], shd.inputs[6])
    pv = node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    cp = node('ShaderNodeCombineXYZ'); pval = math_('ADD', math_('MULTIPLY', pst, 0.22), 0.88)
    [L.new(pval, cp.inputs[q]) for q in range(3)]
    L.new(math_('MULTIPLY', rkn, 1.0), pv.inputs['Factor']); L.new(shd.outputs[2], pv.inputs[6]); L.new(cp.outputs[0], pv.inputs[7])
    # ÇAKIL ZEMİN (kanyon tabanı, yar dipleri): tek tek taşlar — taş başına gri ton, üst kenarda parıltı, aralar koyu toprak
    gv = node('ShaderNodeAttribute', attribute_name='gravel').outputs['Fac']
    mpg = node('ShaderNodeMapping'); mpg.inputs['Scale'].default_value = (1.0, 1.0, 0.0); L.new(tc.outputs['Object'], mpg.inputs[0])
    gw = node('ShaderNodeTexNoise'); gw.inputs['Scale'].default_value = 3.0; L.new(mpg.outputs[0], gw.inputs['Vector'])
    mpw = node('ShaderNodeVectorMath', operation='MULTIPLY_ADD'); mpw.inputs[1].default_value = (0.08, 0.08, 0.0)
    L.new(gw.outputs['Color'], mpw.inputs[0]); L.new(mpg.outputs[0], mpw.inputs[2])
    ge = node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); ge.inputs['Scale'].default_value = 5.5; L.new(mpw.outputs[0], ge.inputs['Vector'])
    gc = node('ShaderNodeTexVoronoi'); gc.inputs['Scale'].default_value = 5.5; L.new(mpw.outputs[0], gc.inputs['Vector'])
    gsep = node('ShaderNodeSeparateColor'); L.new(gc.outputs['Color'], gsep.inputs[0])
    stone = node('ShaderNodeMix', data_type='RGBA'); stone.inputs[6].default_value = K.srgb('#5f6672') + (1,); stone.inputs[7].default_value = K.srgb('#9aa1ad') + (1,)
    L.new(gsep.outputs[0], stone.inputs['Factor'])
    srim = node('ShaderNodeMix', data_type='RGBA'); srim.inputs[7].default_value = K.srgb('#e6e9ee') + (1,)
    L.new(math_('MULTIPLY', band(ge.outputs['Distance'], 0.12, 0.15, 0.18, 0.24), 0.6), srim.inputs['Factor']); L.new(stone.outputs[2], srim.inputs[6])
    gap = node('ShaderNodeMix', data_type='RGBA'); gap.inputs[7].default_value = K.srgb('#4f3e2b') + (1,)
    soil = mr(gw.outputs['Fac'], 0.5, 0.62, 0.0, 1.0)                                    # yer yer taşlar seyrek, toprak görünür
    gapw = math_('ADD', 0.13, math_('MULTIPLY', soil, 0.14))
    gapm = math_('MINIMUM', math_('DIVIDE', ge.outputs['Distance'], gapw), 1.0)
    # aralarda küçük taşlar (ikinci kat): toprak tamamen boş kalmasın
    se = node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); se.inputs['Scale'].default_value = 16.0; L.new(mpw.outputs[0], se.inputs['Vector'])
    small = mr(se.outputs['Distance'], 0.1, 0.16)
    gapf = math_('MULTIPLY', math_('SUBTRACT', 1.0, math_('POWER', gapm, 2.0)), math_('SUBTRACT', 1.0, math_('MULTIPLY', small, math_('SUBTRACT', 1.0, soil))))
    L.new(gapf, gap.inputs['Factor']); L.new(srim.outputs[2], gap.inputs[6])
    # DİKEY SU İZLERİ (örnek görsel): kaya yüzünde yukarıdan aşağı inen koyu lekeler ve açık şeritler
    mps = node('ShaderNodeMapping'); mps.inputs['Scale'].default_value = (1.0, 1.0, 0.04); L.new(tc.outputs['Object'], mps.inputs[0])
    sn1 = node('ShaderNodeTexNoise'); sn1.inputs['Scale'].default_value = 0.45; sn1.inputs['Detail'].default_value = 3; sn1.inputs['Roughness'].default_value = 0.55; L.new(mps.outputs[0], sn1.inputs['Vector'])
    stain = math_('MULTIPLY', mr(sn1.outputs['Fac'], 0.56, 0.66), rkn)
    lband = math_('MULTIPLY', mr(sn1.outputs['Fac'], 0.4, 0.33), rkn)
    st1 = node('ShaderNodeMix', data_type='RGBA'); st1.inputs[7].default_value = K.srgb('#3c3742') + (1,)
    L.new(math_('MULTIPLY', stain, 0.62), st1.inputs['Factor']); L.new(pv.outputs[2], st1.inputs[6])
    st2 = node('ShaderNodeMix', data_type='RGBA'); st2.inputs[7].default_value = K.srgb('#ddd3c8') + (1,)
    L.new(math_('MULTIPLY', lband, 0.45), st2.inputs['Factor']); L.new(st1.outputs[2], st2.inputs[6])
    gm = node('ShaderNodeMix', data_type='RGBA'); L.new(gv, gm.inputs['Factor']); L.new(st2.outputs[2], gm.inputs[6]); L.new(gap.outputs[2], gm.inputs[7])
    L.new(gm.outputs[2], b.inputs['Base Color'])
    # çakıl kabartması (tümsek): taşlar yükselir
    gb = node('ShaderNodeBump'); gb.inputs['Strength'].default_value = 1.0; gb.inputs['Distance'].default_value = 0.04
    L.new(math_('MULTIPLY', math_('SUBTRACT', 1.0, gapf), gv), gb.inputs['Height'])
    L.new(bn.outputs['Normal'], gb.inputs['Normal']); L.new(gb.outputs['Normal'], b.inputs['Normal'])
    return m

# ------------------------------------------------------------------ su + gökyüzü

def img_from(name, arr):
    nz, nx = arr.shape[:2]; img = bpy.data.images.new(name, nx, nz, float_buffer=True)
    px = np.zeros((nz, nx, 4), np.float32)
    if arr.ndim == 2: px[..., 0] = arr
    else: px[..., :arr.shape[2]] = arr
    img.colorspace_settings.name = 'Non-Color'; px[..., 3] = 1.0; img.pixels.foreach_set(px.ravel()); img.pack(); return img

def ramp_node(nt, stops):
    r = nt.nodes.new('ShaderNodeValToRGB'); cr = r.color_ramp
    cr.elements[0].position = stops[0][0]; cr.elements[0].color = K.srgb(stops[0][1]) + (1,)
    cr.elements[1].position = stops[-1][0]; cr.elements[1].color = K.srgb(stops[-1][1]) + (1,)
    for p, c in stops[1:-1]: e = cr.elements.new(p); e.color = K.srgb(c) + (1,)
    return r

def water(L):
    """Deniz: derinlikten renk (sığ turkuaz → derin mavi), sığda saydam (kum görünür), kıyıda kırık köpük + açıkta köpük çizgileri,
    uzakta ufuk pusu (ışın uzunluğu)."""
    h = L.h; sd = L.d['coast']
    depth = np.clip(-h / 6.5, 0, 1); depth = np.maximum(depth, ss(0, 35, -sd))
    edge = np.clip(1 - np.abs(h + 0.08) / 0.3, 0, 1) * (h < 0.05)
    ring = np.exp(-((-sd - 4.0) / 2.2) ** 2) * (sd < 0) * ss(-5, -1.0, h)                    # açıkta ikinci köpük çizgisi
    img = img_from('wdepth', np.stack([depth, edge, ring], -1))
    x0, z0 = TV.X0, TV.Z0; x1, z1 = TV.X1, TV.Z1; pad = 3000.0
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -9.0))
    bed = bpy.context.object; bed.scale = (8000, 8000, 1); bmat = bpy.data.materials.new('seabed'); bmat.use_nodes = True
    bmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#0f5a8e') + (1,); bed.data.materials.append(bmat)
    bpy.ops.mesh.primitive_plane_add(size=1, location=((x0 + x1) / 2, (z0 + z1) / 2, 0.0))
    w = bpy.context.object; w.name = 'sea'; w.scale = (x1 - x0 + 2 * pad, z1 - z0 + 2 * pad, 1)
    m = bpy.data.materials.new('sea_m'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.22; b.inputs['Coat Weight'].default_value = 0.12; b.inputs['Coat Roughness'].default_value = 0.1
    b.inputs['Specular IOR Level'].default_value = 0.35
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    sx = (x1 - x0 + 2 * pad) / (x1 - x0); sz = (z1 - z0 + 2 * pad) / (z1 - z0)
    mp.inputs['Scale'].default_value = (sx, sz, 1); mp.inputs['Location'].default_value = (0.5, 0.5, 0); Lk.new(tc.outputs['Object'], mp.inputs[0])
    t = N.new('ShaderNodeTexImage'); t.image = img; t.extension = 'EXTEND'; t.interpolation = 'Cubic'; Lk.new(mp.outputs[0], t.inputs[0])
    sep = N.new('ShaderNodeSeparateColor'); Lk.new(t.outputs['Color'], sep.inputs[0])
    # dışarıda (ızgara dışı) derin
    rp = ramp_node(nt, [(0.0, '#a6f2e2'), (0.08, '#4fd6cf'), (0.25, '#25b3c9'), (0.55, '#1d8cc2'), (1.0, '#1a6eae')]); Lk.new(sep.outputs[0], rp.inputs['Fac'])
    # köpük
    nzt = N.new('ShaderNodeTexNoise'); nzt.inputs['Scale'].default_value = 0.9; nzt.inputs['Detail'].default_value = 6; nzt.inputs['Roughness'].default_value = 0.7
    Lk.new(tc.outputs['Object'], nzt.inputs['Vector'])
    wn = N.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 0.25; wn.inputs['Detail'].default_value = 2; Lk.new(tc.outputs['Object'], wn.inputs['Vector'])
    def mul(a, b_):
        n = N.new('ShaderNodeMath'); n.operation = 'MULTIPLY'; Lk.new(a, n.inputs[0]); Lk.new(b_, n.inputs[1]); return n.outputs[0]
    def mrange(sock, a, b_, c=0.0, d=1.0):
        n = N.new('ShaderNodeMapRange'); n.inputs[1].default_value = a; n.inputs[2].default_value = b_; n.inputs[3].default_value = c; n.inputs[4].default_value = d; Lk.new(sock, n.inputs[0]); return n.outputs[0]
    f1 = mrange(mul(sep.outputs[1], nzt.outputs['Fac']), 0.3, 0.42)
    f2 = mrange(mul(sep.outputs[2], mrange(wn.outputs['Fac'], 0.42, 0.62)), 0.35, 0.6, 0.0, 0.85)
    f2 = mrange(mul(f2, nzt.outputs['Fac']), 0.12, 0.3)
    fm = N.new('ShaderNodeMath'); fm.operation = 'MAXIMUM'; Lk.new(f1, fm.inputs[0]); Lk.new(f2, fm.inputs[1])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (0.95, 0.98, 1.0, 1)
    Lk.new(fm.outputs[0], mx.inputs['Factor']); Lk.new(rp.outputs[0], mx.inputs[6])
    # ufuk pusu
    lp = N.new('ShaderNodeLightPath'); hz = mrange(lp.outputs['Ray Length'], 700, 3000, 0.0, 0.7)
    mh = N.new('ShaderNodeMix'); mh.data_type = 'RGBA'; mh.inputs[7].default_value = K.srgb('#8fc3ea') + (1,)
    Lk.new(hz, mh.inputs['Factor']); Lk.new(mx.outputs[2], mh.inputs[6]); Lk.new(mh.outputs[2], b.inputs['Base Color'])
    # sığda saydam
    al = mrange(sep.outputs[0], 0.0, 0.22, 0.35, 0.96)
    amx = N.new('ShaderNodeMath'); amx.operation = 'MAXIMUM'; Lk.new(al, amx.inputs[0]); Lk.new(fm.outputs[0], amx.inputs[1])
    Lk.new(amx.outputs[0], b.inputs['Alpha'])
    # dalga tümseği
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.18; bn.inputs['Distance'].default_value = 0.3
    wv = N.new('ShaderNodeTexNoise'); wv.inputs['Scale'].default_value = 0.6; wv.inputs['Detail'].default_value = 5
    mpw = N.new('ShaderNodeMapping'); mpw.inputs['Scale'].default_value = (1.0, 2.2, 1.0); Lk.new(tc.outputs['Object'], mpw.inputs[0])
    Lk.new(mpw.outputs[0], wv.inputs['Vector']); Lk.new(wv.outputs['Fac'], bn.inputs['Height']); Lk.new(bn.outputs['Normal'], b.inputs['Normal'])
    w.data.materials.append(m)
    # göl
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=TV.LAKE['r'] + 6, fill_type='NGON', location=(TV.LAKE['x'], TV.LAKE['z'], TV.LAKE['level']))
    lk = bpy.context.object; lm = bpy.data.materials.new('lake'); lm.use_nodes = True; lb = lm.node_tree.nodes['Principled BSDF']
    lb.inputs['Base Color'].default_value = K.srgb('#2f9fb8') + (1,); lb.inputs['Roughness'].default_value = 0.04; lb.inputs['Alpha'].default_value = 0.85
    lk.data.materials.append(lm)

def sky(sc):
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True; nt = w.node_tree; N = nt.nodes; Lk = nt.links; N.clear()
    out = N.new('ShaderNodeOutputWorld'); bg = N.new('ShaderNodeBackground'); bg.inputs[1].default_value = 1.15
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(tc.outputs['Generated'], sep.inputs[0])
    r = ramp_node(nt, [(0.0, '#b4d8f4'), (0.04, '#86bdf0'), (0.18, '#4f92e6'), (0.5, '#2c6dd6'), (1.0, '#2462cc')])
    Lk.new(sep.outputs['Z'], r.inputs['Fac'])
    # ince yüksek bulut tülü
    vm = N.new('ShaderNodeMapping'); vm.inputs['Scale'].default_value = (1.0, 3.0, 6.0); Lk.new(tc.outputs['Generated'], vm.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 5; Lk.new(vm.outputs[0], nz.inputs['Vector'])
    cr = N.new('ShaderNodeMapRange'); cr.inputs[1].default_value = 0.58; cr.inputs[2].default_value = 0.78; cr.inputs[4].default_value = 0.45; Lk.new(nz.outputs['Fac'], cr.inputs[0])
    band = N.new('ShaderNodeMapRange'); band.inputs[1].default_value = 0.05; band.inputs[2].default_value = 0.25; Lk.new(sep.outputs['Z'], band.inputs[0])
    fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; Lk.new(cr.outputs[0], fm.inputs[0]); Lk.new(band.outputs[0], fm.inputs[1])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (0.95, 0.97, 1.0, 1)
    Lk.new(fm.outputs[0], mx.inputs['Factor']); Lk.new(r.outputs[0], mx.inputs[6]); Lk.new(mx.outputs[2], bg.inputs[0]); Lk.new(bg.outputs[0], out.inputs[0])

def clouds(seed=3):
    cm = K.cloud_mat(); R = random.Random(seed); col = bpy.data.collections.new('clouds'); bpy.context.scene.collection.children.link(col)
    protos = []
    pc = bpy.data.collections.new('cloud_protos')
    for k in range(5):
        o = K.cumulus('cu%d' % k, 100.0, seed + k, mat=cm, col=pc, tall=R.uniform(0.9, 1.5)); protos.append(o)
    out = []
    for i in range(26):
        if i < 14: a = math.radians(R.uniform(25, 155)); r = R.uniform(420, 1300); z = R.uniform(45, 110)   # adanın arkası (çekimler kuzeye bakar)
        else: a = R.uniform(0, math.tau); r = R.uniform(700, 1600); z = R.uniform(80, 160)
        e = bpy.data.objects.new('cloud%d' % i, protos[i % len(protos)].data); col.objects.link(e)
        s = R.uniform(1.8, 3.2) * (r / 900) ** 0.5; e.scale = (s, s * R.uniform(0.7, 1.0), s * R.uniform(0.9, 1.3))
        e.location = (math.cos(a) * r, math.sin(a) * r, z); e.rotation_euler = (0, 0, R.uniform(0, math.tau)); e.visible_shadow = False; e.visible_glossy = False
        out.append(e)
    return out

def lights(sc, elev=48, azim=35, energy=5.4):
    s = bpy.data.lights.new('sun', 'SUN'); s.energy = energy; s.color = K.srgb('#fff0d6'); s.angle = math.radians(1.6)
    o = bpy.data.objects.new('sun', s); sc.collection.objects.link(o); o.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    fl = bpy.data.lights.new('fill', 'SUN'); fl.energy = 0.9; fl.color = (0.62, 0.7, 1.0); fl.angle = math.radians(40); fl.cycles.cast_shadow = False
    fo = bpy.data.objects.new('fill', fl); fo.visible_glossy = False; sc.collection.objects.link(fo); fo.rotation_euler = (math.radians(55), 0, math.radians(azim + 180))
    return o

# ------------------------------------------------------------------ örnekler

PROTO = bpy.data.collections.new('protos') if False else None
def proto(name, fn):
    col = bpy.data.collections.new('P_' + name); fn(col); return col

def inst(col, x, z, y, rot=0.0, s=1.0, sxyz=None):
    e = bpy.data.objects.new('i_' + col.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = col
    e.location = (x, z, y); e.rotation_euler = (0, 0, rot); e.scale = sxyz or (s, s, s); bpy.context.scene.collection.objects.link(e)
    return e

def tex_mat(name, png):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(png)
    b = nt.nodes['Principled BSDF']; nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.75
    return m

def fbx_proto(path_noext, name, tex_suffixes=('_basecolor.png', '_basecolor.jpg')):
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=path_noext + '.fbx')
    new = [o for o in bpy.data.objects if o.name not in before]
    png = next((path_noext + sfx for sfx in tex_suffixes if os.path.exists(path_noext + sfx)), None)
    m = tex_mat(name + '_m', png) if png else None
    for o in new:
        if o.type == 'MESH' and m: o.data.materials.clear(); o.data.materials.append(m)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ V(c) for o in new if o.type == 'MESH' for c in o.bound_box]
    mn = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    col = bpy.data.collections.new('F_' + name)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    return col, max(mx.x - mn.x, mx.y - mn.y), mn

ENV_CACHE = {}
def env(name, x, z, y, footprint, yaw_deg):
    if name not in ENV_CACHE:
        p = os.path.join(ENV, name, name)
        ENV_CACHE[name] = fbx_proto(p, name) if os.path.exists(p + '.fbx') else None
    if ENV_CACHE[name] is None: return None
    col, w, mn = ENV_CACHE[name]; s = footprint / max(0.01, w)
    return inst(col, x, z, y - mn.z * s, -math.radians(yaw_deg), s)

def make_protos():
    P = {}
    bark = K.bark_mat(); fol = K.foliage_mat('fol_broad'); fol_c = K.foliage_mat('fol_cyp', translucent=0.15); fol_p = K.foliage_mat('fol_pine', translucent=0.18)
    P['round'] = [proto('round%d' % k, lambda c, k=k: K.round_tree('rt%d' % k, 1.0, 10 + k, col=c, palette=K.PAL_BROAD if k % 2 else K.PAL_BROAD2,
                                                                     spread=1.0 + 0.1 * (k % 3), fol=fol, bark=bark, clumps=9 + k % 4)) for k in range(6)]
    P['cypress'] = [proto('cyp%d' % k, lambda c, k=k: K.cypress('cy%d' % k, 1.0, 30 + k, col=c, fol=fol_c, bark=bark)) for k in range(3)]
    P['birch'] = [proto('bir%d' % k, lambda c, k=k: K.birch('bi%d' % k, 1.0, 40 + k, col=c, fol=fol)) for k in range(3)]
    P['pine'] = [proto('pine%d' % k, lambda c, k=k: K.pine('pi%d' % k, 1.0, 50 + k, col=c, fol=fol_p, bark=bark)) for k in range(3)]
    P['pine_snow'] = [proto('pines%d' % k, lambda c, k=k: K.pine('ps%d' % k, 1.0, 55 + k, col=c, fol=fol_p, bark=bark, palette=K.PAL_PINE_SNOW)) for k in range(2)]
    P['bush'] = [proto('bush%d' % k, lambda c, k=k: K.bush('bu%d' % k, 1.0, 60 + k, col=c, fol=fol, leaf=0.09)) for k in range(4)]
    rmA = K.rock_mat('rockA', base='#b3a8a8', dark='#7f7386', light='#d4c9c0', moss_amt=0.18)
    rmB = K.rock_mat('rockB', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.28)        # soğuk mavi-gri (çayır)
    rmW = K.rock_mat('rockW', base='#d6d0cc', dark='#a49ca0', light='#ece8e2', moss_amt=0.0, cracks=0.2)  # kıyı/kanyon açık yuvarlak
    P['boulder'] = [proto('bd%d' % k, lambda c, k=k: K.boulder('bd%d' % k, (1.0, 0.8 + 0.1 * (k % 3), 0.7 + 0.1 * (k % 4)), 70 + k, mat=rmA, col=c)) for k in range(5)]
    P['boulderB'] = [proto('bb%d' % k, lambda c, k=k: K.boulder('bb%d' % k, (1.0, 0.85, 0.75 + 0.1 * (k % 3)), 80 + k, mat=rmB, col=c)) for k in range(4)]
    P['pebW'] = [proto('bw%d' % k, lambda c, k=k: K.boulder('bw%d' % k, (1.0, 0.85, 0.7), 90 + k, cuts=4, mat=rmW, col=c, bevel=0.25, top_flat=0.0)) for k in range(3)]
    P['palm'] = 'palm'
    return P

# ------------------------------------------------------------------ yerleşim

class Spacer:
    """Basit en yakın mesafe denetimi (ızgara kova)."""
    def __init__(self, cell=2.0): self.cell = cell; self.b = {}
    def ok(self, x, z, r):
        cx, cz = int(x // self.cell), int(z // self.cell); k = int(math.ceil(r / self.cell)) + 1
        for i in range(cx - k, cx + k + 1):
            for j in range(cz - k, cz + k + 1):
                for (px, pz, pr) in self.b.get((i, j), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 < (max(r, pr)) ** 2: return False
        return True
    def add(self, x, z, r): self.b.setdefault((int(x // self.cell), int(z // self.cell)), []).append((x, z, r))

def free_mask(L):
    X, Z = L.X, L.Z; m = np.ones(L.h.shape, np.float32)
    for (px, pz, hd) in SHOTS.values():   # çekim koridoru: kamera ile pet arası + önü boş (oyunda da yakın bitki saydamlaşır)
        a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
        for t in (-7.0, -5.0, -3.0, -1.0, 1.0, 3.0):
            m *= ss(2.6, 4.2, np.hypot(X - (px + fx * t), Z - (pz + fz * t)))
            if os.environ.get('WIDE'): m *= ss(4.0, 6.5, np.hypot(X - (px + fx * t), Z - (pz + fz * t)))
    cx, cz = TV.SPOTS['camp']; m *= ss(8.0, 11.0, np.hypot(X - cx, Z - cz))
    m *= 1 - ss(0.0, 0.5, TV.blur(L.d['snowpath'], 1.5) * 3)
    cv = [r for r in TV.REGIONS if r[0] == 'region_cave'][0]; ya = math.radians(cv[6])
    m *= ss(5.0, 8.0, np.hypot(X - (cv[2] + math.sin(ya) * 5), Z - (cv[3] + math.cos(ya) * 5)))
    for r in L.lay['regions']:
        x, z = r['pos']; m *= ss(r['size'] * 0.7 + 1.0, r['size'] * 0.7 + 4.0, np.hypot(X - x, Z - z))
    m *= ss(1.8, 3.2, L.d['pathd'])
    return m

def scatter(L, R, dens, n_try, rmin, sp, avoid_slope=0.65, hmin=0.4):
    """dens: ızgara olasılık haritası; döner [(x, z, y)]."""
    xs = R.uniform(TV.X0 + 2, TV.X1 - 2, n_try); zs = R.uniform(TV.Z0 + 2, TV.Z1 - 2, n_try)
    i, j = L.idx(xs, zs); p = dens[j, i] * (L.slope[j, i] < avoid_slope) * (L.h[j, i] > hmin)
    keep = R.uniform(0, 1, n_try) < p; out = []
    for x, z in zip(xs[keep], zs[keep]):
        if sp.ok(x, z, rmin): sp.add(x, z, rmin); out.append((float(x), float(z), L.height(x, z)))
    return out

def place_world(L, B, P):
    R = np.random.default_rng(7); rr = random.Random(7)
    fm = free_mask(L); sp = Spacer(3.0); d = L.d
    lakem = np.hypot(L.X - TV.LAKE['x'], L.Z - TV.LAKE['z']) < TV.LAKE['r'] + 2.5
    grass = (1 - np.clip(d['sand'] * 1.5, 0, 1)) * (1 - d['snow']) * (1 - lakem) * fm * (L.h > 3.0)
    edge_far = ss(0.4, 0.15, L.slope_b)    # yar kenarından biraz içeri
    cnt = {}
    def put(kind, pts, hs, sink=0.15):
        for (x, z, y) in pts:
            col = rr.choice(P[kind]); s = rr.uniform(*hs)
            inst(col, x, z, y - sink, rr.uniform(0, math.tau), s)
        cnt[kind] = cnt.get(kind, 0) + len(pts)
    # doğu orman: çam ağırlıklı + yuvarlak
    put('pine', scatter(L, R, grass * edge_far * B['forest'] * 0.8, 90000, 3.2, sp), (6.5, 10.0))
    put('round', scatter(L, R, grass * edge_far * B['forest'] * 0.35, 30000, 4.5, sp), (6.5, 9.0))
    # karlı zirve etekleri: çam
    peakz = ss(8.0, 12.0, L.h) * ss(24.0, 18.0, L.h) * B['snowpeak']
    put('pine', scatter(L, R, (1 - d['snow']) * fm * peakz * 0.15, 40000, 3.6, sp, avoid_slope=0.9), (5.5, 8.5))
    def groves(kind, dens, n_try, n=(4, 9), rad=(5.0, 9.0), sep=3.6, hs=(6.0, 9.5), csep=14.0, sink=0.15):
        cs = scatter(L, R, dens, n_try, csep, Spacer(6.0))
        pts = []
        for (x, z, y) in cs:
            rad_ = rr.uniform(*rad)
            for k in range(rr.randint(*n) * 3):
                a = rr.uniform(0, math.tau); r_ = rad_ * math.sqrt(rr.random()); px, pz = x + math.cos(a) * r_, z + math.sin(a) * r_
                i, j = L.idx(px, pz)
                if grass[j, i] * edge_far[j, i] < 0.3 or L.slope[j, i] > 0.6: continue
                if sp.ok(px, pz, sep): sp.add(px, pz, sep); pts.append((px, pz, L.height(px, pz)))
        put(kind, pts, hs, sink)
    ge = grass * edge_far
    snowok = ss(0.4, 0.7, d['snow']) * fm * (L.slope < 0.75)
    put('pine_snow', scatter(L, R, snowok * 0.05, 60000, 3.5, sp, avoid_slope=0.75), (5.0, 8.5))
    # yukarı plato + kuzey tepe: yuvarlak ağaç koruları (aralarda açık çayır), servi öbekleri
    groves('round', ge * B['upper'] * 0.35, 40000)
    groves('round', ge * B['village'] * 0.025, 40000, n=(2, 4), csep=20)
    groves('round', ge * B['meadow'] * 0.05, 40000, n=(2, 5), csep=18)
    groves('birch', ge * B['meadow'] * 0.15, 40000, n=(4, 8), sep=2.6, hs=(7.0, 10.5))
    groves('birch', ge * B['upper'] * 0.05, 40000, n=(3, 5), sep=2.6, hs=(7.0, 10.0))
    cyc = scatter(L, R, ge * (B['upper'] * 0.10 + B['village'] * 0.03 + B['meadow'] * 0.03 + B['forest'] * 0.02 + B['spire'] * 0.05), 40000, 2.4, sp)
    cyc = cyc[::2] if len(cyc) > 60 else cyc
    cyp_pts = []
    for (x, z, y) in cyc:
        for k in range(rr.randint(2, 5)):
            a = rr.uniform(0, math.tau); r_ = rr.uniform(1.2, 3.2); px, pz = x + math.cos(a) * r_, z + math.sin(a) * r_
            if L.get('slope', px, pz) < 0.6 and sp.ok(px, pz, 1.1): sp.add(px, pz, 1.1); cyp_pts.append((px, pz, L.height(px, pz)))
    put('cypress', cyc + cyp_pts, (7.5, 12.0), sink=0.1)
    # kaya tepe (yer imi) basamakları: ağaçlar
    spm = (d['t_spire1'] > 0.5) * ss(0.35, 0.1, L.slope_b) * fm
    put('round', scatter(L, R, spm * 0.6, 30000, 3.2, sp, hmin=12), (4.5, 6.5))
    put('cypress', scatter(L, R, spm * 0.35, 30000, 2.2, sp, hmin=12), (6.0, 8.5))
    # genel serpinti (tek ağaçlar)
    put('round', scatter(L, R, ge * 0.025, 80000, 7.0, sp), (5.0, 8.5))
    # çalılar: yar dudağı boyunca + ağaç diplerinde + genel
    lip = ss(0.15, 0.45, L.slope_b) * ss(0.9, 0.5, L.slope) * (1 - d['sand'])
    spb = Spacer(1.5)
    put('bush', scatter(L, R, lip * fm * 0.2 + grass * 0.012, 120000, 1.8, spb, avoid_slope=0.9), (0.7, 1.6), sink=0.2)
    # palmiyeler: geniş kumsalın iç kenarı
    sandin = ss(0.4, 0.8, d['sand']) * ss(0.6, 1.0, L.h) * ss(2.0, 1.5, L.h) * fm
    pts = scatter(L, R, sandin * 0.4, 60000, 4.0, sp, hmin=0.5)
    for (x, z, y) in pts: env('palm', x, z, y - 0.1, rr.uniform(4.2, 6.0), rr.uniform(0, 360))
    cpal = scatter(L, R, ss(0.4, 0.8, d['canyon']) * ss(0.1, 0.4, L.slope_b) * fm * 0.05, 80000, 4.0, sp, avoid_slope=0.5)   # kanyonda palmiye
    for (x, z, y) in cpal[:14]: env('palm', x, z, y - 0.1, rr.uniform(4.5, 6.5), rr.uniform(0, 360))
    cnt['palm'] = len(pts) + len(cpal[:14])
    # kayalar: yar dibinde (kıyı + plato), kumsal/koy iri beyaz yuvarlaklar, çayırda soğuk gri öbekler
    base = ss(0.3, 0.9, L.slope_b) * ss(0.6, 0.2, L.slope)
    spr = Spacer(2.0)
    for (x, z, y) in scatter(L, R, base * fm * 0.14, 200000, 2.5, spr, avoid_slope=0.7, hmin=-0.8):
        s = rr.uniform(0.9, 2.8); inst(rr.choice(P['boulder']), x, z, y - s * 0.25, rr.uniform(0, math.tau), s)
    beachr = d['sand'] * ss(1.2, 0.2, L.h) * (1 - ss(0.6, 0.9, d['canyon']))
    for (x, z, y) in scatter(L, R, (beachr * ss(0.5, 1.2, L.slope_b) * 0.03 + d['canyon'] * 0.008) * fm, 200000, 5.0, spr, avoid_slope=1.2, hmin=-1.5):
        s = rr.uniform(1.4, 3.2); inst(rr.choice(P['pebW']), x, z, y - s * 0.2, rr.uniform(0, math.tau), s)
    for (x, z, y) in scatter(L, R, (grass * B['meadow'] * 0.006 + grass * B['upper'] * 0.004) * fm, 200000, 6.0, spr):
        for k in range(rr.randint(2, 5)):
            a = rr.uniform(0, math.tau); r_ = rr.uniform(0.5, 3.0); px, pz = x + math.cos(a) * r_, z + math.sin(a) * r_
            if L.get('slope', px, pz) > 0.5: continue
            s = rr.uniform(0.6, 2.2) * (1.4 if k == 0 else 1.0); inst(rr.choice(P['boulderB']), px, pz, L.height(px, pz) - s * 0.25, rr.uniform(0, math.tau), s)
    # mağara: iri kaya yığını + karanlık ağız (batı tepesi)
    cx, cz = [r['pos'] for r in L.lay['regions'] if r['id'] == 'region_cave'][0]
    cave(L, P, cx, cz, rr)
    camp(L, P, rr)
    trail_poles(L)
    log('yerleşim', cnt)

def trail_poles(L):
    """Karlı patika işaret direkleri: her ~3,5 m'de bir, iki yana sırayla; turuncu başlıklı ahşap direk + aralarında halat."""
    bark = K.bark_mat('pole_bark', base='#7a5536', dark='#4a3222', light='#a67c55')
    cap = bpy.data.materials.new('pole_cap'); cap.use_nodes = True; cap.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#f07a1a') + (1,)
    rope = bpy.data.materials.new('rope'); rope.use_nodes = True; rope.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#c9a56a') + (1,)
    pts = TV.SNOW_PATH; vs, fs, cvs, cfs = [], [], [], []; tops = {-1: [], 1: []}
    seg = [(V(a + (0,)), V(b + (0,))) for a, b in zip(pts[:-1], pts[1:])]
    k = 0
    for (a, b) in seg:
        L_ = (b - a).length; n = max(1, int(L_ / 3.5)); d = (b - a).normalized(); side = V((-d.y, d.x, 0))
        for i in range(n):
            for sgn in (-1, 1):
                p = a + d * (L_ * (i + 0.5) / n) + side * sgn * 2.25; y = L.height(p.x, p.y)
                v, f = K.tube_data([(p.x, p.y, y - 0.2), (p.x, p.y, y + 1.15)], [0.045, 0.04], 6, len(vs)); vs += v; fs += f
                v, f = K.tube_data([(p.x, p.y, y + 1.15), (p.x, p.y, y + 1.4)], [0.06, 0.06], 6, len(cvs)); cvs += v; cfs += f
                tops[sgn].append((p.x, p.y, y + 0.95))
    K.mesh_obj('trail_poles', vs, fs, bark); K.mesh_obj('trail_caps', cvs, cfs, cap)
    rv, rf = [], []
    for sgn in (-1, 1):
        T = tops[sgn]
        for p, q in zip(T[:-1], T[1:]):
            if (V(p) - V(q)).length > 6: continue
            mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2 - 0.15)
            v, f = K.tube_data([p, mid, q], [0.015, 0.015, 0.015], 5, len(rv)); rv += v; rf += f
    K.mesh_obj('trail_rope', rv, rf, rope)

def camp(L, P, rr):
    """Kamp alanı: toprak açıklık ortasında taş halkalı ateş, çevresinde devrik kütükler, kesik kütükler, iri kayalar."""
    cx, cz = TV.SPOTS['camp']; y = L.height(cx, cz)
    col = bpy.data.collections.new('camp'); bpy.context.scene.collection.children.link(col)
    K.campfire('fire', col=col, seed=4)
    for o in col.objects: o.location = (o.location.x + cx, o.location.y + cz, o.location.z + y)
    bark = K.bark_mat('camp_bark')
    for k, (a, r_, ln) in enumerate(((0.3, 3.6, 3.4), (2.3, 3.8, 2.8), (4.0, 3.4, 3.0))):
        c2 = bpy.data.collections.new('C_clog%d' % k); K.log('clog%d' % k, ln, 0.3, 20 + k, col=c2, bark=bark)
        x, z = cx + math.cos(a) * r_, cz + math.sin(a) * r_; e = inst(c2, x, z, L.height(x, z) - 0.06, a + math.pi / 2, 1.0)
    for k, a in enumerate((1.2, 3.2, 5.2, 5.9)):
        c2 = bpy.data.collections.new('C_cst%d' % k); K.stump('cst%d' % k, 0.42 + 0.05 * k, 0.55 + 0.1 * (k % 2), 30 + k, col=c2, bark=bark)
        x, z = cx + math.cos(a) * 4.6, cz + math.sin(a) * 4.6; inst(c2, x, z, L.height(x, z) - 0.05, rr.uniform(0, 6.3), 1.0)
    for k, a in enumerate((0.8, 1.8, 2.9, 4.6, 5.5)):
        x, z = cx + math.cos(a) * rr.uniform(5.6, 6.8), cz + math.sin(a) * rr.uniform(5.6, 6.8); s = rr.uniform(1.0, 1.9)
        inst(rr.choice(P['boulder']), x, z, L.height(x, z) - s * 0.25, rr.uniform(0, 6.3), s)

def cave(L, P, cx, cz, rr):
    """Mağara: soğuk gri iri kayalardan kemer (iki yan söve + üstte lento) ve arkasında höyük; ağız karanlık, önü kum açıklık."""
    yaw = math.radians([r['yaw'] for r in L.lay['regions'] if r['id'] == 'region_cave'][0])
    fx, fz = math.sin(yaw), math.cos(yaw); sx, sz = fz, -fx          # ağız yönü (dışa) ve yan
    y0 = L.height(cx, cz)
    dark = bpy.data.materials.new('cave_dark'); dark.use_nodes = True; db = dark.node_tree.nodes['Principled BSDF']
    db.inputs['Base Color'].default_value = (0.01, 0.01, 0.014, 1); db.inputs['Roughness'].default_value = 1.0
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(cx - fx * 1.2, cz - fz * 1.2, y0 + 1.2)); m = bpy.context.object
    m.scale = (1.9, 2.2, 1.9); m.rotation_euler = (0, 0, -yaw); m.data.materials.append(dark)
    B_ = P['boulderB']
    def put(f, sd, up, s, k, sq=None):
        x = cx + fx * f + sx * sd; z = cz + fz * f + sz * sd
        inst(B_[k % len(B_)], x, z, y0 + up, rr.uniform(0, 6.3), s, sxyz=sq)
    put(0.2, -2.6, -0.2, 2.6, 0); put(0.4, 2.7, -0.2, 2.8, 1)                      # söveler
    put(-0.3, 0.0, 2.6, 0, 2, sq=(3.6, 3.0, 1.6))                                   # lento
    put(-2.5, -4.6, 0.0, 3.2, 3); put(-2.2, 4.8, 0.2, 3.4, 0); put(-4.0, 0.0, 1.5, 3.8, 1)
    put(-4.2, -3.0, 3.6, 2.8, 2); put(-4.4, 3.2, 3.4, 2.6, 3); put(-6.0, 0.5, 4.2, 3.0, 0)
    put(1.6, -4.2, -0.3, 1.4, 1); put(2.0, 4.6, -0.3, 1.2, 2); put(2.8, -3.0, -0.2, 0.7, 3)
    for k in range(5):                                                                 # ağız önünde çalılar
        put(rr.uniform(0.5, 2.5), rr.choice((-1, 1)) * rr.uniform(3.2, 5.5), -0.1, 0, 0) if False else None

def buildings(L):
    assets = {'region_home': 'b_home', 'region_shop': 'b_shop', 'region_task_board': 'b_task_board', 'region_swim_cove': 'b_swim',
              'region_surf_beach': 'b_surf', 'region_game_hut': 'b_game_hut', 'region_garden': 'b_garden', 'region_pier': 'b_pier',
              'region_festival': 'b_festival', 'region_mountain': 'b_mountain', 'region_lighthouse': 'b_lighthouse'}
    for r in L.lay['regions']:
        a = assets.get(r['id']); x, z = r['pos']
        if r['id'] == 'region_coconut_grove':
            for k, (ox, oz, s) in enumerate([(-1.8, 0.8, 5.4), (1.6, -0.6, 4.8), (0.2, 2.2, 6.0), (2.4, 2.6, 5.0)]):
                env('palm', x + ox, z + oz, L.height(x + ox, z + oz) - 0.1, s, k * 95)
            continue
        if not a: continue
        y = L.height(x, z) if a != 'b_pier' else 0.6
        env(a, x, z, y, r['size'], r['yaw'])

OKTI = None
def okti(L, x, z, yaw_deg):
    global OKTI
    if OKTI is None:
        p = os.path.join(PETS, 'pet_13_genc', 'pet_13_genc'); OKTI = fbx_proto(p, 'okti', ('_basecolor.jpg',))
    col, w, mn = OKTI
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ V(c) for o in col.objects if o.type == 'MESH' for c in o.bound_box]
    hgt = max(p.z for p in pts) - min(p.z for p in pts); s = 1.75 / hgt
    return inst(col, x, z, L.height(x, z) - mn.z * s, math.radians(yaw_deg), s)

# ------------------------------------------------------------------ çekimler

def look_cam(pos, look, fov=50, lens=None):
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(fov); cd.clip_end = 6000; cd.clip_start = 0.1
    o = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(o)
    o.location = V(pos); o.rotation_euler = (V(look) - V(pos)).to_track_quat('-Z', 'Y').to_euler(); bpy.context.scene.camera = o
    return o

def game_shot(L, px, pz, heading_deg, dist=6.0, pitch=16, look_ahead=2.0, lift=0.0):
    """Oyundaki üçüncü şahıs kamera: petin arkasından ~20°, pet alt üçte birde."""
    a = math.radians(heading_deg); fwd = V((math.sin(a), math.cos(a), 0))
    py = L.height(px, pz); hgt = 1.75
    pivot = V((px, pz, py + hgt * 0.9)); look = V((px, pz, py + hgt * 0.55 + lift)) + fwd * look_ahead
    dirv = (-fwd * math.cos(math.radians(pitch))) + V((0, 0, math.sin(math.radians(pitch))))
    pos = pivot + dirv * dist; pos.z = max(pos.z, L.height(pos.x, pos.y) + 0.8)
    return pos, look

SHOTS = {   # x, z, bakış (° , 0 = kuzey)
    'koy': (1.5, -19.5, 2), 'cayir': (-44.0, 0.0, 305), 'kanyon': (-2.5, 6.0, 352), 'kamp': (46.5, -3.5, 52),
    'orman': (44.0, 12.0, 22), 'yamac': (-15.0, 3.0, 2), 'koy_kiyi': (56.0, -29.5, 138), 'kar': (-38.0, 40.6, 284), 'kar_patika': (-44.5, 41.7, 300),
}

SHOT_CAM = {'yamac': dict(pitch=5, dist=6.0, lift=2.6), 'kar': dict(pitch=9, dist=6.5, lift=1.6), 'kar_patika': dict(pitch=6, dist=6.5, lift=2.2), 'kanyon': dict(pitch=11, lift=0.6), 'orman': dict(pitch=13, lift=0.5)}

AERIAL = {
    'ada_kusbakisi': ((-8, -128, 56), (0, 40, 12), 50),
    'ada_dogu': ((118, -58, 46), (4, 16, 10), 48),
    'harita_ust': None,
}

def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    npz, out = args[0], args[1]; shots = args[2].split(','); samples = int(args[3]) if len(args) > 3 else 48; k = float(args[4]) if len(args) > 4 else 1.0
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.cycles.use_denoising = True; sc.cycles.max_bounces = 5; sc.cycles.transparent_max_bounces = 12
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
    L = Land(npz); B = biome_fields(L); log('arazi', L.h.shape)
    cols, rw = terrain_colors(L, B); terrain_mesh(L, cols, rw); log('zemin')
    water(L); sky(sc); CLOUDS[:] = clouds(); lights(sc); log('su/gök')
    P = make_protos(); log('örnekler')
    place_world(L, B, P); buildings(L); log('yapılar')
    for s in shots:
        for o in [o for o in sc.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
        for o in NEAR: bpy.data.objects.remove(o, do_unlink=True)
        NEAR[:] = []
        for o in [o for o in sc.objects if o.name.startswith('i_F_okti')]: bpy.data.objects.remove(o)
        for o in CLOUDS: o.hide_render = (s == 'harita_ust')
        if s == 'harita_ust':   # kuşbakışı harita: dik izdüşüm, bulutsuz
            cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = TV.X1 - TV.X0 - 10; cd.clip_end = 2000
            co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co; co.location = (0, 0, 300); co.rotation_euler = (0, 0, 0)
            sc.render.resolution_x = int(1600 * k); sc.render.resolution_y = int(1600 * k * (TV.Z1 - TV.Z0 - 10) / (TV.X1 - TV.X0 - 10)); sc.view_settings.exposure = 0.05
        elif s in AERIAL:
            pos, look, fov = AERIAL[s]; look_cam(pos, look, fov)
            sc.render.resolution_x, sc.render.resolution_y = int(1600 * k), int(900 * k); sc.view_settings.exposure = 0.1
        else:
            x, z, hd = SHOTS[s]; okti(L, x, z, -hd + 180)
            NEAR[:] = NR.build(L, B, P, s, x, z, hd); log('yakın ayrıntı', s, len(NEAR))
            pos, look = game_shot(L, x, z, hd, **SHOT_CAM.get(s, {})); look_cam(pos, look, 52)
            sc.render.resolution_x, sc.render.resolution_y = int(1600 * k), int(900 * k); sc.view_settings.exposure = 0.15
        sc.render.filepath = os.path.join(out, s + '.png'); bpy.ops.render.render(write_still=True); log('çekim', s)

if __name__ == '__main__':
    main()
