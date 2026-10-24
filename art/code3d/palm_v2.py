# Ada palmiyesi v2 (24 Ekim 2026, kullanıcı: "palmiye dahil bütün tasarımlar detaylı 3D olsun").
# Eski "palm" (assets_v3.c_palm) ~12 geniş, düz, köşeli yaprak kartıydı ve normal haritası yoktu. Burada v6 ağaçları gibi
# ayrıntılı bir TASLAK kurulur ve v6 hattıyla (v6/proxy_bake.py: renk + AO + teğet normal haritası) oyun modeline pişirilir:
#   taslak: hafif kavisli, halka halka şişkin, lifli gövde + kök topağı; lif örgülü taç sapı; 20 sarkan tüylü yaprak (her biri
#           orta damarlı, V kıvrımlı ~40-50 yaprakçık), tepede açılmamış genç yaprak, hindistan cevizi salkımı, 2 kuru sarkık yaprak.
#   oyun:   gövde 10 kenarlı halka dişli tüp, yaprakçık başına tek üçgen (gerçek tarak siluet; iki yüzlü), yaprak sapı, ceviz,
#           kök çıkıntıları — ~3250 üçgen; ayrıntı (yaprakçık rengi, orta damar, lif, halka gölgesi) dokuda.
#           UV elle yerleşir (uv_layout): gövde silindirik, yaprakçıklar sıra döşeme, katı parçalar akıllı açılım (doku verimi ~%90).
# Boy ve yön eski modelle aynı: orijin gövde dibinde (zemin), gövde +x'e yatık, yatay en büyük boy 4,68 m, tepe 4,67 m
# → island_v6_layout.json'daki "palm" ölçekleri (fp, RealAssets.EnvFootprint), sallanma yarıçapı ve toplama yerleri değişmez.
# Stil: boyalı "vinyl oyuncak" (canlı ama dengeli renk, yumuşak); dış çizgi yok.
# Kullanım (bpy ortamı):
#   /tmp/claude-0/bpyenv/bin/python -I palm_v2.py -- <çıktı_klasörü> [c_palm2]   → c_palm2.fbx, c_palm2_basecolor.png, c_palm2_normal.png
#   /tmp/claude-0/bpyenv/bin/python -I palm_v2.py -- <çıktı_klasörü> --draft <png>   → yalnız taslağın çizimi (tasarım denetimi)
#   Oyuna: python3 export_game.py palm   (Resources/Env/palm/palm.fbx + _basecolor + _normal)
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'v6')); sys.path.insert(0, HERE)
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, noise as MN
import kit_v6 as K
import proxy_bake as PB

SEED = 7
H = 3.62             # gövde tepesi (taç sapının dibi)
LEAN = 1.45          # tepe yatay kayması (+x; eski palmiye ile aynı yön)
RINGS = 13
F = 20               # yeşil yaprak sayısı
TARGET_SPAN = 4.68   # yatay en büyük boy (eski model 4,684)
TARGET_TOP = 4.67    # tepe (eski model 4,674)
Z = V((0.0, 0.0, 1.0))

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def c3(h): return np.array(K.srgb(h))
def mixc(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))

# ------------------------------------------------------------------ ağ yardımcıları

class Mesh:
    """Biriken köşe/yüz/renk (+ isteğe bağlı yüz köşesi UV'si) listesi → tek nesne. part: oyun ağında parça kimliği (UV yerleşimi)."""
    def __init__(self): self.v, self.f, self.c, self.uv = [], [], [], []
    def add(self, verts, faces, cols=None, uvs=None):
        o = len(self.v); self.v += [tuple(p) for p in verts]; self.f += [tuple(i + o for i in q) for q in faces]
        if cols is not None: self.c += [tuple(c) for c in cols]
        self.uv += list(uvs) if uvs is not None else [None] * len(faces)
        return o
    def obj(self, name, mat=None, ds=False, part=None):
        cols = np.array(self.c) if self.c and len(self.c) == len(self.v) else None
        o = K.mesh_obj(name, self.v, self.f, mat, colors=cols)
        if ds:
            a = o.data.attributes.new('ds', 'INT', 'FACE'); a.data.foreach_set('value', [1] * len(o.data.polygons))
        if part is not None:
            a = o.data.attributes.new('part', 'INT', 'FACE'); a.data.foreach_set('value', [part] * len(o.data.polygons))
            lay = o.data.uv_layers.new(name='UVMap'); flat = []
            for poly, uv in zip(o.data.polygons, self.uv):
                flat += [c for q in (uv or [(0.0, 0.0)] * poly.loop_total) for c in q]
            lay.data.foreach_set('uv', flat)
        return o

def ring_frame(tg):
    ax = V((1, 0, 0)) if abs(tg.z) > 0.9 else V((0, 0, 1))
    u = tg.cross(ax).normalized(); w = tg.cross(u).normalized()
    return u, w

def tube(rows, res, cols=None, cap_end=False, uv=None):
    """rows: [(merkez V, teğet V, yarıçap ya da fn(a))]; dışa bakan yüzler; halka çerçevesi eğri boyunca taşınır (burulma yok).
    cols: fn(i, k, p) → renk ya da None. uv: (x0, y0, en, boy) → silindirik açılım (u = çevre, v = yay uzunluğu)."""
    verts, faces, cc, uvs = [], [], [], []
    u, w = ring_frame(rows[0][1])
    for i, (p, tg, r) in enumerate(rows):
        if i:
            u2 = u - tg * u.dot(tg)
            if u2.length < 1e-6: u, w = ring_frame(tg)
            else: u = u2.normalized(); w = tg.cross(u).normalized()
        for k in range(res):
            a = k / res * math.tau; rr = r(a) if callable(r) else r
            q = p + (u * math.cos(a) + w * math.sin(a)) * rr; verts.append(q)
            if cols: cc.append(cols(i, k, q))
    arc = [0.0]
    for i in range(1, len(rows)): arc.append(arc[-1] + (rows[i][0] - rows[i - 1][0]).length)
    tot = max(arc[-1], 1e-6)
    def U(i, k):
        x0, y0, ww, hh = uv; return (x0 + ww * k / res, y0 + hh * arc[i] / tot)
    for i in range(len(rows) - 1):
        for k in range(res):
            a = i * res + k; b = i * res + (k + 1) % res
            faces.append((a, a + res, b + res, b))
            if uv: uvs.append((U(i, k), U(i + 1, k), U(i + 1, k + 1), U(i, k + 1)))
    if cap_end:
        tip = len(verts); p, tg, _ = rows[-1]; verts.append(p + tg * 0.001)
        if cols: cc.append(cols(len(rows) - 1, 0, p))
        o = (len(rows) - 1) * res; n = len(rows) - 1
        for k in range(res):
            faces.append((o + k, tip, o + (k + 1) % res))
            if uv: uvs.append((U(n, k), U(n, k + 0.5), U(n, k + 1)))
    # yön denetimi: ilk yüz dışa baksın
    a, b, c = (V(verts[i]) for i in faces[0][:3])
    n = (b - a).cross(c - a)
    if n.dot((a + b + c) / 3 - rows[0][0]) < 0:
        faces = [tuple(reversed(f)) for f in faces]; uvs = [tuple(reversed(q)) for q in uvs]
    return verts, faces, (cc if cols else None), (uvs if uv else None)

def curve_rows(fn, ts):
    out = []
    for t in ts:
        p = fn(t); tg = (fn(min(ts[-1], t + 1e-3)) - fn(max(ts[0], t - 1e-3))).normalized()
        out.append((p, tg))
    return out

# ------------------------------------------------------------------ malzemeler (yalnız taslak; oyuna pişmiş doku gider)

def vc_bump_mat(name, rough=0.8, bump=0.3, scale=30.0, stretch=None, detail=5):
    m, N, L, b = K._mat(name)
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; L.new(vc.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if bump:
        tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = detail
        if stretch:
            mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch; L.new(tc.outputs['Object'], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs['Vector'])
        else: L.new(tc.outputs['Object'], nz.inputs['Vector'])
        bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; bn.inputs['Distance'].default_value = 0.01
        L.new(nz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m

# ------------------------------------------------------------------ gövde + taç sapı

def tpath(t):
    tt = max(t, 0.0)
    return V((LEAN * (1.7 * tt * tt - 0.7 * tt ** 3) + 0.03 * math.sin(tt * 6.0),
              0.07 * math.sin(tt * 2.6) - 0.025 * math.sin(tt * 7.0),
              H * t))
T0 = -0.15 / H                      # gövde zeminin 15 cm altından başlar (eğimde havada kalmasın; eski modelde de −0,15)
def ttan(t): return (tpath(min(1.0, t + 0.004)) - tpath(t - 0.004)).normalized()

def r_base(t):
    tt = max(t, 0.0)
    return 0.33 - 0.125 * tt ** 0.85 + 0.16 * math.exp(-tt / 0.045) + (0.03 if t < 0 else 0.0)
def ring_ph(t): return (t * RINGS + 0.3) % 1.0
def ring_amp(t): return smoothstep(0.035, 0.1, t) * (1 - 0.45 * smoothstep(0.9, 1.0, t))
def ring_mod(t):
    """Halka: altta boğum (ph≈0) → yukarı şişer → üst kenarda yuvarlak dudak, sonra keskin iniş (üst üste kaplar)."""
    ph = ring_ph(t)
    prof = 0.12 * ph ** 1.4 + 0.035 * math.exp(-((ph - 0.94) / 0.04) ** 2) - 0.06
    return 1.0 + ring_amp(t) * prof

TOP = None; AX = None
BL = 0.5                             # taç sapı boyu
def setup_axes():
    global TOP, AX
    TOP = tpath(1.0); AX = (ttan(1.0) + Z * 1.6).normalized()
def boot_pt(u): return TOP + AX * (BL * u)
def boot_r(u): return 0.2 + 0.085 * math.sin(math.pi * min(max(u, 0.0) / 0.85, 1.0)) - 0.105 * smoothstep(0.7, 1.0, u)

def stem_rows_low():
    """Oyun gövdesi: kök genişlemesi + halka başına iki sıra (boğum, dudak) → dişli siluet; sonra taç sapı."""
    ts = [T0, 0.0, 0.025, 0.06]
    for k in range(RINGS + 1):
        for ph in (0.015, 0.93):
            t = (k + ph - 0.3) / RINGS
            if 0.085 < t < 0.985: ts.append(t)
    ts.append(1.0)
    rows = [(tpath(t), ttan(t), r_base(t) * ring_mod(t)) for t in sorted(ts)]
    for u in (0.3, 0.6, 0.85, 0.97):
        rows.append((boot_pt(u), AX, boot_r(u)))
    return rows

def stem_high(mat):
    cG, cB, cL, cH = c3('#5a3a22'), c3('#8d6038'), c3('#bf8d58'), c3('#d9a86e')
    cGrey, cWet, cFib = c3('#8f8570'), c3('#5e4430'), c3('#7a5434')
    n = 360; ts = [T0 + (1 - T0) * i / (n - 1) for i in range(n)]
    rows = []
    for t in ts:
        z = H * t; rb = r_base(t) * ring_mod(t)
        def rf(a, z=z, rb=rb, t=t):
            fib = MN.noise(V((math.cos(a) * 7.0, math.sin(a) * 7.0, z * 0.7)))
            fib2 = MN.noise(V((math.cos(a) * 19.0, math.sin(a) * 19.0, z * 2.2)))
            knob = 0.05 * max(0.0, MN.noise(V((math.cos(a) * 3, math.sin(a) * 3, z * 9)))) * (1 - smoothstep(0.0, 0.07, t))   # kök topağı yumruları
            return rb * (1 + 0.02 * fib + 0.009 * fib2 + knob)
        rows.append((tpath(t), ttan(t), rf))
    nb = 40
    for i in range(1, nb):
        u = i / (nb - 1) * 0.97; rows.append((boot_pt(u), AX, boot_r(u)))
    nt = len(ts)
    def col(i, k, q):
        a = k / 72 * math.tau
        if i >= nt:   # taç sapı: altta lifli kahve, üstte genç yaprak kınlarının zeytin yeşili (çizgili)
            ub = (i - nt + 1) / (nb - 1) * 0.97
            st = MN.noise(V((math.cos(a) * 9.0, math.sin(a) * 9.0, ub * 2))) * 0.5 + 0.5
            return mixc(mixc(c3('#6e4b2e'), cFib, 0.5), c3('#7f8f3e') * (0.8 + 0.35 * st), smoothstep(0.45, 0.75, ub))
        t = ts[i]; z = H * t; ph = ring_ph(t); amp = ring_amp(t)
        fib = MN.noise(V((math.cos(a) * 7.0, math.sin(a) * 7.0, z * 0.7))) * 0.5 + 0.5
        c = mixc(cB, cL, ph ** 1.2)
        c = mixc(c, cH, math.exp(-((ph - 0.93) / 0.035) ** 2) * 0.8 * amp)
        c = mixc(c, cG, (1 - smoothstep(0.0, 0.12, ph)) * 0.85 * amp)
        c = c * (0.74 + 0.42 * fib)
        crack = MN.noise(V((math.cos(a) * 11.0, math.sin(a) * 11.0, z * 0.35)))
        c = mixc(c, cG * 0.8, smoothstep(0.42, 0.55, crack) * 0.55 * amp)   # boyuna lif çatlakları
        g = MN.noise(V((math.cos(a) * 1.5, math.sin(a) * 1.5, z * 0.6)))
        c = mixc(c, cGrey, smoothstep(0.15, 0.55, g) * 0.4 * (1 - t))
        c = mixc(c, cWet, (1 - smoothstep(-0.02, 0.09, t)) * 0.75)
        c = mixc(c, cFib, smoothstep(0.86, 1.0, t) * 0.6)
        return c
    v, f, cc, _ = tube(rows, 72, col, cap_end=True)
    m = Mesh(); m.add(v, f, cc)
    return m.obj('hi_stem', mat)

# ------------------------------------------------------------------ yapraklar

LEAF_PAL = [(0.0, '#123f13'), (0.25, '#256f22'), (0.6, '#45a530'), (1.0, '#92d64c')]
DRY_PAL = [(0.0, '#6b4c2e'), (0.4, '#8f6b40'), (0.75, '#b48d58'), (1.0, '#cfae74')]

class Frond:
    def __init__(self, i, Ls, rise, R):
        age = 1.0 - i / (F - 1)                        # 1 = en yaşlı (altta, sarkık), 0 = en genç (tepede, dik)
        self.age = age
        self.az = i * 2.39996 + R.uniform(-0.15, 0.15)
        self.ub = 0.16 + 0.66 * (1 - age)
        hv = V((math.cos(self.az), math.sin(self.az), 0.0)); hv = (hv - AX * AX.dot(hv)).normalized(); self.hv = hv
        self.B = boot_pt(self.ub) + hv * boot_r(self.ub) * 0.8
        e = math.radians(lerp(58.0 * rise, -1.0, age ** 0.8) + R.uniform(-5, 5))
        self.d0 = (hv * math.cos(e) + Z * math.sin(e)).normalized()
        self.L = lerp(1.5, 2.4, age ** 0.6) * R.uniform(0.93, 1.06) * Ls
        self.g = lerp(0.2, 0.5, age) * R.uniform(0.9, 1.1)
        self.side0 = Z.cross(hv).normalized()
        self.curl = R.uniform(-0.2, 0.2); self.twist = R.uniform(-0.6, 0.6)
        self.N = int(round(lerp(18, 25, age ** 0.5)))
        self.dl0, self.dl1 = math.radians(lerp(10, 24, age)), math.radians(lerp(42, 64, age))
        self.phi = math.radians(R.uniform(34, 42))
        self.s0 = 0.12; self.s1 = 0.985
        self.seed = R.randint(0, 10 ** 6)
        self.LL = 0.4 * R.uniform(0.95, 1.05)
    def R(self, s):
        return self.B + self.d0 * (self.L * s) + Z * (-self.g * self.L * s * s) + self.side0 * (self.curl * self.L * s * s)
    def frame(self, s):
        T = (self.R(s + 1e-3) - self.R(s - 1e-3)).normalized()
        S = Z.cross(T)
        S = S.normalized() if S.length > 1e-4 else self.side0
        U = T.cross(S).normalized()
        tw = self.twist * s
        S2 = (S * math.cos(tw) + U * math.sin(tw)).normalized(); U2 = T.cross(S2).normalized()
        return T, S2, U2
    def ds(self): return (self.s1 - self.s0) / self.N
    def leaflet(self, j, sg, rnd):
        """j. yaprakçık (sg = ±1 yan): taban ortası, yön, boy, sarkma, uç, üst yüz normali."""
        ds = self.ds(); s = self.s0 + (j + 0.5) * ds
        x = (s - self.s0) / (self.s1 - self.s0)
        T, S, U = self.frame(s)
        dl = lerp(self.dl0, self.dl1, x)
        dd = ((S * (sg * math.cos(dl)) - U * math.sin(dl)) * math.cos(self.phi) + T * math.sin(self.phi)).normalized()
        prof = math.sin(math.pi * (0.06 + 0.9 * x)) ** 0.75 * (1 - 0.25 * x) + 0.08
        ln = self.L * self.LL * prof * rnd.uniform(0.9, 1.07)
        k = 0.14 + 0.2 * x + 0.1 * self.age
        Bm = self.R(s)
        tip = Bm + dd * ln - Z * (k * ln)
        n_top = (T.cross(dd) * sg).normalized()
        return s, x, T, Bm, dd, ln, k, tip, n_top

OV = 1.7     # oyun yaprakçığının taban kenarı aralığın kaç katı (komşular bindirmeli → dolgun yaprak; uçlar ayrık → tarak)

def frond_low(fr, out):
    """Oyun yaprağı: yaprakçık başına tek üçgen (taban orta damarda, uç ayrık). Tabanlar komşusuyla bindirmeli; z çakışması
    olmasın diye tek/çift yaprakçıklar üst yüz yönünde ±6 mm ayrık."""
    rnd = random.Random(fr.seed)
    ds = fr.ds()
    for j in range(fr.N):
        for sg in (1, -1):
            s, x, T, Bm, dd, ln, k, tip, n_top = fr.leaflet(j, sg, rnd)
            lift = n_top * (0.006 if j % 2 else -0.006)
            b0 = fr.R(s - OV * ds / 2) + lift; b1 = fr.R(s + OV * ds / 2) + lift
            out.add([b0, b1, tip + lift] if sg > 0 else [b1, b0, tip + lift], [(0, 1, 2)])

def leaf_uv_layout(n, x0=0.24, x1=1.0, xs=0.54, ys=0.70, aspect=4.2, px=1.0 / 1024):
    """n yaprakçık üçgeni için UV: sıralar halinde ters-düz dizilmiş eş üçgenler (taban altta/üstte, uç karşıda).
    Bölge: y < ys için x0..x1, üstünde xs..x1 (sol üst köşe katı parçalara ayrılır). Döndürür: üçgen başına (taban0, taban1, uç)."""
    gap = 2 * px
    def rows_for(w):
        h = aspect * w; out = []; y = gap
        while y + h <= 1.0 - gap:
            lo = x0 if y + h <= ys else xs
            cap = max(0, int((x1 - lo - gap) / (w / 2)) - 1)
            out.append((lo + gap / 2, y, cap)); y += h + gap
        return out, h
    w = 0.08
    while True:
        rows, h = rows_for(w)
        if sum(r[2] for r in rows) >= n: break
        w *= 0.985
    uvs = []
    for (lx, y, cap) in rows:
        for k in range(cap):
            if len(uvs) >= n: break
            xa = lx + (k // 2) * w + (w / 2 if k % 2 else 0.0)
            if k % 2 == 0: tri = [(xa, y), (xa + w, y), (xa + w / 2, y + h)]
            else: tri = [(xa, y + h), (xa + w, y + h), (xa + w / 2, y)]
            cx = sum(p[0] for p in tri) / 3; cy = sum(p[1] for p in tri) / 3
            # 1 piksel içeri: süzmede komşu üçgen taşmasın
            tri = [(p[0] + (cx - p[0]) * (1.2 * px / max(abs(cx - p[0]) + abs(cy - p[1]), 1e-6)), p[1] + (cy - p[1]) * (1.2 * px / max(abs(cx - p[0]) + abs(cy - p[1]), 1e-6))) for p in tri]
            uvs.append(tuple(tri))
    print('yaprak UV: %d üçgen, hücre %.1f x %.1f px' % (len(uvs), w / px, h / px), flush=True)
    return uvs

SOLID_REGION = (0.24, 0.70, 0.30, 0.30)   # x, y, en, boy: sap, ceviz, kök, genç yaprak, kuru yapraklar (akıllı açılım buraya sığdırılır)

def uv_layout(L):
    """proxy_bake hedef ağı UV'si: gövde silindirik (kurulumda), yaprakçıklar sıra döşeme (kurulumda), katı parçalar akıllı açılım → kendi bölgesi."""
    me = L.data
    for l in [l for l in me.uv_layers if l.name != 'UVMap']: me.uv_layers.remove(l)
    me.uv_layers.active = me.uv_layers['UVMap']
    part = np.zeros(len(me.polygons), np.int32); me.attributes['part'].data.foreach_get('value', part)
    sel = (part == 1) | (part == 3)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='FACE'); bpy.ops.mesh.select_all(action='DESELECT')
    bm = bmesh.from_edit_mesh(me); bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if sel[f.index]: f.select_set(True)
    bmesh.update_edit_mesh(me)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    li = np.zeros(len(me.loops), bool)
    for p in me.polygons:
        if sel[p.index]: li[p.loop_start:p.loop_start + p.loop_total] = True
    x, y, w, h = SOLID_REGION
    uv[li, 0] = x + uv[li, 0] * w; uv[li, 1] = y + uv[li, 1] * h
    me.uv_layers['UVMap'].data.foreach_set('uv', uv.ravel())
    me.attributes.remove(me.attributes['part'])

def frond_high(fr, leaf, rach, petiole):
    rnd = random.Random(fr.seed)
    ds = fr.ds()
    young = 1 - fr.age
    base_tint = c3('#8fd456'); old_tint = c3('#93a443')
    mid = c3('#d2e48a'); dry = c3('#c4a95a')
    NU, VS = 9, (-1.0, -0.5, 0.0, 0.5, 1.0)
    for j in range(fr.N):
        for sg in (1, -1):
            s, x, T, Bm, dd, ln, k, tip, n_top = fr.leaflet(j, sg, rnd)
            hl = (fr.R(s + ds / 2) - fr.R(s - ds / 2)).length / 2
            w0 = 2.0 * max(hl * 1.45, 0.025)
            Wv = dd.cross(n_top).normalized()
            fold = rnd.uniform(0.16, 0.26)
            twist = rnd.uniform(-0.25, 0.25)
            lum = rnd.uniform(0.84, 1.1); yel = rnd.uniform(0.0, 0.1) + 0.14 * fr.age * x
            drytip = rnd.random() < 0.07 + 0.08 * fr.age
            verts, cols = [], []
            for i in range(NU + 1):
                u = i / NU
                uu = -0.04 + 1.04 * u
                pc = Bm + dd * (ln * uu) - Z * (k * ln * uu * uu)
                w = w0 * max(1 - uu, 0.0) ** 0.78 * (1 + 0.18 * math.sin(math.pi * min(1, max(uu, 0)))) + 0.003
                tw = twist * u
                Wt = (Wv * math.cos(tw) + n_top * math.sin(tw)); Nt = (n_top * math.cos(tw) - Wv * math.sin(tw))
                for v in VS:
                    p = pc + Wt * (v * w / 2) + Nt * (fold * abs(v) ** 1.3 * w / 2)
                    verts.append(p)
                    c = K.ramp3(np.array([0.08 + 0.92 * u]), LEAF_PAL)[0]
                    c = mixc(c, base_tint, young * 0.35)
                    c = mixc(c, old_tint, yel)
                    c = c * lum * (0.9 if abs(v) == 1.0 else 1.0)
                    if v == 0.0: c = mixc(c, mid, 0.42 * (1 - u * 0.5))
                    if drytip: c = mixc(c, dry, smoothstep(0.72, 0.95, u))
                    cols.append(c)
            faces = []
            nv = len(VS)
            for i in range(NU):
                for q in range(nv - 1):
                    a = i * nv + q; faces.append((a, a + 1, a + 1 + nv, a + nv))
            leaf.add(verts, faces, cols)
    # yaprakçıkların altında koyu "gölge" yüzeyi: oyun üçgeninde yaprakçık dışına düşen ışınlar siyah yerine koyu yeşil alır
    bk = c3('#1d4519')
    for sg in (1, -1):
        rnd2 = random.Random(fr.seed); verts, faces, cols = [], [], []
        for j in range(fr.N):
            r1 = fr.leaflet(j, 1, rnd2); r2 = fr.leaflet(j, -1, rnd2)
            s, x, T, Bm, dd, ln, k, tip, n_top = r1 if sg > 0 else r2
            verts += [Bm - n_top * 0.02, Bm + (tip - Bm) * 0.4 - n_top * 0.03, Bm + (tip - Bm) * 0.75 - n_top * 0.03]
            cols += [bk * 0.8, bk, bk * 1.1]
        for j in range(fr.N - 1):
            for q in range(2):
                a = j * 3 + q; faces.append((a, a + 1, a + 4, a + 3))
        if faces:
            a_, b_, c_ = (V(verts[i]) for i in faces[0][:3])
            if (b_ - a_).cross(c_ - a_).dot(fr.leaflet(0, sg, random.Random(fr.seed))[8]) < 0: faces = [tuple(reversed(f)) for f in faces]
            leaf.add(verts, faces, cols)
    # orta damar (yaprakçıklı kısım) ve yaprak sapı
    ctop, cbot = c3('#c9d06a'), c3('#7f8f3c')
    rows = []
    n = 26
    for q in range(n):
        s = fr.s0 + (fr.s1 - fr.s0) * q / (n - 1)
        T, S, U = fr.frame(s)
        rows.append((fr.R(s), T, lerp(0.03, 0.006, (s - fr.s0) / (fr.s1 - fr.s0)) * (fr.L / 2.2)))
    def rc(i, kk, p, rows=rows):
        c0 = rows[i][0]; T, S, U = fr.frame(fr.s0 + (fr.s1 - fr.s0) * i / (n - 1))
        d = (V(p) - c0).normalized().dot(U)
        return mixc(cbot, ctop, d * 0.5 + 0.5)
    v, f, cc, _ = tube(rows, 6, rc)
    rach.add(v, f, cc)
    rows = []
    for q in range(8):
        s = fr.s0 * q / 7
        T, S, U = fr.frame(max(s, 1e-3))
        rows.append((fr.R(s), T, lerp(0.07, 0.03, q / 7) * (fr.L / 2.2)))
    pc0, pc1 = c3('#6b5a32'), c3('#7f9440')
    v, f, cc, _ = tube(rows, 8, lambda i, kk, p: mixc(pc0, pc1, i / 7))
    petiole.add(v, f, cc)

def petiole_low(fr, out):
    rows = []
    for q in range(3):
        s = (fr.s0 + 0.02) * q / 2
        T, S, U = fr.frame(max(s, 1e-3))
        rows.append((fr.R(s), T, lerp(0.075, 0.035, q / 2) * (fr.L / 2.2)))
    v, f, _, _ = tube(rows, 3)
    out.add(v, f)

# ------------------------------------------------------------------ kuru sarkık yapraklar

class Dry:
    def __init__(self, az, ub, ln, seed):
        hv = V((math.cos(az), math.sin(az), 0.0)); hv = (hv - AX * AX.dot(hv)).normalized()
        self.hv = hv; self.side = Z.cross(hv).normalized(); self.seed = seed; self.ln = ln
        self.B = boot_pt(ub) + hv * boot_r(ub) * 0.85
    def R(self, s):
        return self.B + self.hv * (0.36 * (1 - (1 - s) ** 3)) - Z * (self.ln * s ** 1.6)

def dry_high(d, m):
    rnd = random.Random(d.seed)
    rows = [(d.R(s), (d.R(min(1, s + 1e-3)) - d.R(max(0, s - 1e-3))).normalized(), lerp(0.035, 0.01, s)) for s in np.linspace(0, 1, 16)]
    v, f, cc, _ = tube(rows, 6, lambda i, k, p: K.ramp3(np.array([0.3 + 0.3 * i / 15]), DRY_PAL)[0])
    m.add(v, f, cc)
    for j in range(46):
        s = rnd.uniform(0.18, 0.98); p0 = d.R(s); sg = 1 if j % 2 else -1
        dn = (-Z * 1.0 + d.side * (sg * rnd.uniform(0.15, 0.45)) + d.hv * rnd.uniform(0.0, 0.25)).normalized()
        ln = rnd.uniform(0.22, 0.42) * (1.1 - 0.4 * s); w = rnd.uniform(0.018, 0.03)
        nrm = d.hv; Wv = dn.cross(nrm).normalized(); tw = rnd.uniform(-1.2, 1.2)
        verts, cols, faces = [], [], []
        tone = rnd.uniform(0.15, 0.95)
        for i in range(7):
            u = i / 6; a = tw * u
            wv = (Wv * math.cos(a) + nrm * math.sin(a))
            pc = p0 + dn * (ln * u) + d.hv * (0.03 * math.sin(u * 5 + j))
            ww = w * (1 - u * 0.7)
            for vv in (-1, 0, 1):
                verts.append(pc + wv * (vv * ww / 2) + nrm * (0.006 * (1 - abs(vv))))
                cols.append(K.ramp3(np.array([min(1, tone + 0.1 * (vv == 0))]), DRY_PAL)[0] * (0.9 + 0.2 * u))
        for i in range(6):
            for q in range(2):
                a = i * 3 + q; faces.append((a, a + 1, a + 4, a + 3))
        m.add(verts, faces, cols)

def dry_low(d, out):
    """Sarkık kuru yaprak: orta damar boyunca dikey şerit (yaprakçıklar aşağı sarkar), alt ucu dişli; iki yüzlü."""
    ss = [0.12, 0.3, 0.48, 0.66, 0.83, 1.0]
    verts, faces = [], []
    for i, s in enumerate(ss):
        p = d.R(s); w = 0.16 * (1.1 - 0.4 * s)
        verts += [p + d.side * w + d.hv * 0.04 - Z * 0.05, p - d.side * w + d.hv * 0.04 - Z * 0.05]
    tip = len(verts); verts.append(d.R(1.0) - Z * 0.3 + d.hv * 0.05)
    for i in range(len(ss) - 1):
        a = i * 2; faces.append((a, a + 2, a + 3, a + 1))
    faces.append((len(ss) * 2 - 2, tip, len(ss) * 2 - 1))
    # yön: dışa (hv)
    a, b, c = V(verts[faces[0][0]]), V(verts[faces[0][1]]), V(verts[faces[0][2]])
    if (b - a).cross(c - a).dot(d.hv) < 0: faces = [tuple(reversed(f)) for f in faces]
    out.add(verts, faces)

# ------------------------------------------------------------------ hindistan cevizleri, kökler, lif örgüsü, genç yaprak

def nuts_spec(R):
    out = []
    for q in range(6):
        az = q * 1.05 + 0.4 + R.uniform(-0.15, 0.15)
        hv = V((math.cos(az), math.sin(az), 0.0)); hv = (hv - AX * AX.dot(hv)).normalized()
        u = 0.12 + 0.08 * (q % 2)
        r = R.uniform(0.16, 0.18)
        c = boot_pt(u) + hv * (boot_r(u) + r * 0.75) - Z * (0.06 + 0.05 * (q % 3))
        out.append((c, r, hv, q))
    return out

def nut_high(spec, m):
    c, r, hv, q = spec
    ico = K._ico(3); ff = K._ICO_F[3]
    green = q % 3 != 2
    c0, c1 = (c3('#5f7f27'), c3('#a2b848')) if green else (c3('#6e4523'), c3('#a8763f'))
    ax = (hv * 0.5 - Z).normalized()   # uç aşağı-dışa
    verts, cols = [], []
    for p in ico:
        d = V(tuple(p)); h = d.dot(ax)
        side = (d - ax * h)
        ang = math.atan2(side.dot(ax.cross(hv).normalized()), side.dot((hv - ax * ax.dot(hv)).normalized() if (hv - ax * ax.dot(hv)).length > 1e-4 else V((1, 0, 0))))
        lob = 1 + 0.05 * math.cos(3 * ang)
        elong = 1 + 0.16 * max(h, 0) ** 2
        bump = 0.03 * MN.noise(d * 6 + V((q * 3.1, 0, 0)))
        pp = c + (side * lob + ax * h * elong) * r * (1 + bump)
        verts.append(pp)
        lit = 0.5 + 0.5 * (-h)
        col = mixc(c0, c1, lit * 0.8 + 0.2 * (MN.noise(d * 3) * 0.5 + 0.5))
        if h > 0.85: col = mixc(col, c3('#4a3420'), (h - 0.85) / 0.15)
        if h < -0.85: col = mixc(col, c3('#6a5a2a'), (-h - 0.85) / 0.15)   # sap ucu
        cols.append(col)
    m.add(verts, [tuple(f) for f in ff], cols)
    # sap
    top = c - ax * r * 0.95
    rows = [(top, -ax, 0.025), (top + (-ax * 0.08 + hv * -0.04), -ax, 0.02)]
    v, f, cc, _ = tube(rows, 6, lambda i, k, p: c3('#8a7a3a'))
    m.add(v, f, cc)

def nut_low(spec, out):
    c, r, hv, q = spec
    seg, rings = 8, 4
    ax = (hv * 0.5 - Z).normalized(); u0, w0 = ring_frame(ax)
    verts = [c - ax * r * 0.98]
    for i in range(1, rings):
        h = -math.cos(math.pi * i / rings)
        rr = math.sin(math.pi * i / rings) * r * 0.99
        for k in range(seg):
            a = k / seg * math.tau
            verts.append(c + ax * (h * r * (1 + (0.16 * h * h if h > 0 else 0))) + (u0 * math.cos(a) + w0 * math.sin(a)) * rr)
    verts.append(c + ax * r * 1.12)
    faces = []
    for k in range(seg): faces.append((0, 1 + (k + 1) % seg, 1 + k))
    for i in range(rings - 2):
        o = 1 + i * seg
        for k in range(seg): faces.append((o + k, o + (k + 1) % seg, o + seg + (k + 1) % seg, o + seg + k))
    last = len(verts) - 1; o = 1 + (rings - 2) * seg
    for k in range(seg): faces.append((o + k, o + (k + 1) % seg, last))
    a, b, cc = (V(verts[i]) for i in faces[0])
    if (b - a).cross(cc - a).dot((a + b + cc) / 3 - c) < 0: faces = [tuple(reversed(f)) for f in faces]
    out.add(verts, faces)

def roots_spec(R):
    out = []
    for q in range(22):
        az = q / 22 * math.tau + R.uniform(-0.12, 0.12)
        big = q % 3 == 0
        ln = R.uniform(0.26, 0.4) if big else R.uniform(0.14, 0.26)
        r = R.uniform(0.055, 0.07) if big else R.uniform(0.026, 0.04)
        out.append((az, ln, r, big))
    return out

def root_pts(spec, n):
    az, ln, r, big = spec
    hv = V((math.cos(az), math.sin(az), 0.0)); p0 = V((tpath(0.0).x, tpath(0.0).y, 0.0)) + hv * 0.3
    pts = []
    for i in range(n):
        u = i / (n - 1)
        pts.append(p0 + hv * (ln * u) + Z * (0.1 * (1 - u) ** 1.5 - 0.09 * u + 0.02))
    return pts

def root_high(spec, m):
    az, ln, r, big = spec
    pts = root_pts(spec, 10)
    rows = [(p, ((pts[min(i + 1, 9)] - pts[max(i - 1, 0)]).normalized()), r * (1 - 0.45 * i / 9)) for i, p in enumerate(pts)]
    v, f, cc, _ = tube(rows, 8, lambda i, k, p: mixc(c3('#6a4426'), c3('#a06a3a'), 0.3 + 0.5 * (MN.noise(V(p) * 9) * 0.5 + 0.5)) * (0.8 + 0.25 * i / 9), cap_end=True)
    m.add(v, f, cc)

def root_low(spec, out):
    az, ln, r, big = spec
    pts = root_pts(spec, 3)
    rows = [(p, ((pts[min(i + 1, 2)] - pts[max(i - 1, 0)]).normalized()), r * (1 - 0.4 * i / 2) * 1.08) for i, p in enumerate(pts)]
    v, f, _, _ = tube(rows, 5, cap_end=True)   # beş kenar: üç kenarlı kök diken gibi görünüyordu
    out.add(v, f)

def fibers_high(R, m):
    """Taç sapında çapraz örülmüş lif şeritleri + dipten sarkan lif püskülleri (gerçek hindistan cevizi palmiyesinin "bezi")."""
    cols = [c3('#5c3d24'), c3('#7a5432'), c3('#9b7346'), c3('#b48c5c')]
    for q in range(170):
        sg = 1 if q % 2 else -1
        a0 = R.uniform(0, math.tau); u0 = R.uniform(-0.35, 0.15); u1 = min(u0 + R.uniform(0.35, 0.6), 0.62)
        da = sg * R.uniform(0.8, 1.6); w = R.uniform(0.008, 0.016); col = cols[R.randrange(4)] * R.uniform(0.9, 1.1)
        lift = R.uniform(0.004, 0.02)
        verts, cc, faces = [], [], []
        n = 12
        for i in range(n + 1):
            t = i / n; u = lerp(u0, u1, t); a = a0 + da * t
            c = boot_pt(u) if u >= 0 else tpath(1.0 + u * BL / H)
            ax = AX if u >= 0 else ttan(1.0 + u * BL / H)
            e1, e2 = ring_frame(ax)
            rad = (boot_r(u) if u >= 0 else r_base(1.0 + u * BL / H) * ring_mod(1.0 + u * BL / H))
            nrm = (e1 * math.cos(a) + e2 * math.sin(a)); tng = ax.cross(nrm).normalized()
            p = c + nrm * (rad * 1.03 + lift)
            side = (ax * math.cos(0.6) * sg + tng * math.sin(0.6)).normalized().cross(nrm).normalized()
            verts += [p - side * w / 2, p + side * w / 2]; cc += [col, col * 1.08]
        for i in range(n):
            a = i * 2; faces.append((a, a + 2, a + 3, a + 1))
        a_, b_, c_ = (V(verts[i]) for i in faces[0][:3])
        mid = boot_pt(max(u0, 0.0))
        if (b_ - a_).cross(c_ - a_).dot(a_ - mid) < 0: faces = [tuple(reversed(f)) for f in faces]
        m.add(verts, faces, cc)
    for q in range(34):
        a = R.uniform(0, math.tau); u = R.uniform(0.0, 0.12)
        e1, e2 = ring_frame(AX); nrm = (e1 * math.cos(a) + e2 * math.sin(a))
        p0 = boot_pt(u) + nrm * (boot_r(u) * 1.05 + 0.01)
        ln = R.uniform(0.12, 0.32); w = R.uniform(0.01, 0.022); col = cols[R.randrange(3)]
        side = Z.cross(nrm).normalized()
        verts, cc, faces = [], [], []
        for i in range(6):
            t = i / 5; p = p0 - Z * (ln * t) + nrm * (0.03 * t + 0.01 * math.sin(t * 6 + q))
            verts += [p - side * w / 2 * (1 - 0.6 * t), p + side * w / 2 * (1 - 0.6 * t)]; cc += [col * (1 - 0.15 * t), col]
        for i in range(5):
            b = i * 2; faces.append((b, b + 1, b + 3, b + 2))
        a_, b_, c_ = (V(verts[i]) for i in faces[0][:3])
        if (b_ - a_).cross(c_ - a_).dot(nrm) < 0: faces = [tuple(reversed(f)) for f in faces]
        m.add(verts, faces, cc)

def spear_axis(): return (AX + Z).normalized()
def spear_high(m):
    a = spear_axis(); base = boot_pt(0.9); ln = 0.5
    rows = []
    for i in range(14):
        t = i / 13
        rows.append((base + a * (ln * t), a, (lambda ang, t=t: 0.075 * (1 - t) ** 0.9 * (1 + 0.12 * math.cos(ang * 7)) + 0.002)))
    v, f, cc, _ = tube(rows, 28, lambda i, k, p: mixc(c3('#8fbf4e'), c3('#d6ec8c'), i / 13), cap_end=True)
    m.add(v, f, cc)

def spear_low(out):
    a = spear_axis(); base = boot_pt(0.9); ln = 0.5
    rows = [(base, a, 0.075), (base + a * (ln * 0.55), a, 0.04)]
    v, f, _, _ = tube(rows, 4)
    tip = len(v); v.append(base + a * ln)
    for k in range(4): f.append((4 + k, 4 + (k + 1) % 4, tip))
    a_, b_, c_ = (V(v[i]) for i in f[-1])
    if (b_ - a_).cross(c_ - a_).dot((a_ + b_) / 2 - (base + a * ln * 0.55)) < 0: f[-4:] = [tuple(reversed(x)) for x in f[-4:]]
    out.add(v, f)

def dries():
    return [Dry(3.35, 0.06, 1.05, 501), Dry(4.55, 0.1, 0.85, 502)]

# ------------------------------------------------------------------ kurulum

def build_low(Ls, rise):
    setup_axes()
    R = random.Random(SEED)
    fronds = [Frond(i, Ls, rise, R) for i in range(F)]
    STEM_UV = (0.004, 0.004, 0.232, 0.992)
    stem = Mesh(); v, f, _, uvs = tube(stem_rows_low(), 10, uv=STEM_UV)
    o = stem.add(v, f, uvs=uvs)
    # taç sapı tepesi: kapak (genç yaprağın dibine)
    last = len(v) - 10; top = (STEM_UV[1] + STEM_UV[3]) - 0.002
    cap, cuv = [], []
    for k in range(10):
        cap.append((o + last + k, o + last + (k + 1) % 10, len(stem.v)))
        x = lambda q: STEM_UV[0] + STEM_UV[2] * q / 10
        cuv.append(((x(k), top), (x(k + 1), top), (x(k + 0.5), top - 0.001)))
    a_, b_, c_ = V(stem.v[cap[0][0]]), V(stem.v[cap[0][1]]), boot_pt(1.0)
    if (b_ - a_).cross(c_ - a_).dot(AX) < 0: cap = [(c[1], c[0], c[2]) for c in cap]; cuv = [(q[1], q[0], q[2]) for q in cuv]
    stem.v.append(tuple(boot_pt(1.0))); stem.f += cap; stem.uv += cuv
    solid = Mesh(); leaves = Mesh(); dry = Mesh()
    for fr in fronds:
        frond_low(fr, leaves); petiole_low(fr, solid)
    leaves.uv = leaf_uv_layout(len(leaves.f))
    for spec in nuts_spec(random.Random(SEED + 1)): nut_low(spec, solid)
    for spec in roots_spec(random.Random(SEED + 2)):
        if spec[3]: root_low(spec, solid)
    spear_low(solid)
    for d in dries(): dry_low(d, dry)
    return fronds, [(stem, False, 0), (solid, False, 1), (leaves, True, 2), (dry, True, 3)]

def bbox(meshes):
    pts = np.array([p for m, _, _ in meshes for p in m.v])
    return pts.min(0), pts.max(0)

def fit():
    Ls, rise = 1.0, 1.0
    for it in range(6):
        fronds, meshes = build_low(Ls, rise)
        lo, hi = bbox(meshes); span = max(hi[0] - lo[0], hi[1] - lo[1]); top = hi[2]
        print('uydurma', it, 'Ls %.3f rise %.3f' % (Ls, rise), 'boyut', np.round(hi - lo, 3), 'alt', np.round(lo, 3), 'üst', np.round(hi, 3), flush=True)
        if abs(span - TARGET_SPAN) < 0.01 and abs(top - TARGET_TOP) < 0.02: break
        Ls *= TARGET_SPAN / span
        rise *= 1 + (TARGET_TOP - top) / 0.9
    return Ls, rise

def build_all(Ls, rise, high=True):
    fronds, meshes = build_low(Ls, rise)
    low = [m.obj('lo_%d' % i, ds=ds, part=part) for i, (m, ds, part) in enumerate(meshes)]
    hi = []
    if high:
        leafm = vc_bump_mat('palm_leaf', rough=0.55, bump=0.08, scale=60.0, stretch=(1, 1, 1), detail=2)
        trunkm = vc_bump_mat('palm_trunk', rough=0.85, bump=0.45, scale=26.0, stretch=(7, 7, 0.35), detail=6)
        fibm = vc_bump_mat('palm_fiber', rough=0.9, bump=0.5, scale=80.0, detail=4)
        solidm = vc_bump_mat('palm_solid', rough=0.6, bump=0.15, scale=40.0, detail=3)
        hi.append(stem_high(trunkm))
        leaf, rach, pet = Mesh(), Mesh(), Mesh()
        for fr in fronds: frond_high(fr, leaf, rach, pet)
        hi += [leaf.obj('hi_leaf', leafm), rach.obj('hi_rachis', solidm), pet.obj('hi_petiole', solidm)]
        fib = Mesh(); fibers_high(random.Random(SEED + 3), fib); hi.append(fib.obj('hi_fiber', fibm))
        nm = Mesh()
        for spec in nuts_spec(random.Random(SEED + 1)): nut_high(spec, nm)
        hi.append(nm.obj('hi_nuts', vc_bump_mat('palm_nut', rough=0.5, bump=0.25, scale=45.0, stretch=(1, 1, 3), detail=4)))
        rm = Mesh()
        for spec in roots_spec(random.Random(SEED + 2)): root_high(spec, rm)
        hi.append(rm.obj('hi_roots', trunkm))
        sp = Mesh(); spear_high(sp); hi.append(sp.obj('hi_spear', solidm))
        dm = Mesh()
        for d in dries(): dry_high(d, dm)
        hi.append(dm.obj('hi_dry', fibm))
    return hi, low

def draft_render(path, objs_hide=()):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 20; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.72, 0.95, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.55
    for o in objs_hide: o.hide_render = True
    bpy.ops.mesh.primitive_plane_add(size=60); g = bpy.context.object
    gm = bpy.data.materials.new('g'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#e9d3a0') + (1,); g.data.materials.append(gm)
    sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(3); so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(42), 0, math.radians(-38))
    cam = bpy.data.cameras.new('c'); cam.lens = 35; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = 700, 700
    from PIL import Image
    views = [((5.2, -6.8, 5.6), (1.2, 0, 2.8)), ((1.3, -9.5, 2.6), (1.3, 0, 2.5)), ((1.31, -0.6, 10.5), (1.3, 0, 2.5))]
    ims = []
    for k, (loc, tgt) in enumerate(views):
        co.location = V(loc); co.rotation_euler = (V(tgt) - co.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = path[:-4] + '_%d.png' % k; bpy.ops.render.render(write_still=True); ims.append(Image.open(sc.render.filepath).convert('RGB'))
    sheet = Image.new('RGB', (700 * len(ims), 700)); [sheet.paste(im, (700 * k, 0)) for k, im in enumerate(ims)]; sheet.save(path)

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    out = args[0]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    Ls, rise = fit()
    if '--draft' in args:
        hi, low = build_all(Ls, rise, high=True)
        draft_render(args[args.index('--draft') + 1], low)
        print('taslak üçgen', sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in hi), 'oyun (tek yüz)', sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in low))
        sys.exit(0)
    name = ([a for a in args[1:] if not a.startswith('-')] or ['c_palm2'])[0]
    target = int(os.environ.get('POFI_TARGET', '0') or 0) or 3600
    tex = int(os.environ.get('POFI_TEX', '0') or 0) or 1024
    hi, low = build_all(Ls, rise, high=True)
    print('taslak üçgen', sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in hi), flush=True)
    # ışın: yaprakçık kemeri hedef üçgenin en çok ~7 cm üstünde; gövde/ceviz hedefi taslağın içinde (iç teğet çokgen)
    tris = PB.export_proxy(os.path.join(out, name), hi, low, target=target, size=tex, nsize=tex, cage=0.085, ray=0.2,
                           ao_strength=0.75, ao_dist=0.5, ds_low=True, uv_fn=uv_layout)
    print('üçgen', tris, flush=True)
