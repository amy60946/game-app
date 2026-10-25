# Gezegen Koşusu — Ay yüzeyi zemin karoları (25 Ekim 2026; kullanıcı: "Ay yüzeyi + bir krater köprüsü anı"; en önemlisi HIZ hissi,
# DERİNLİK — düz gri çöl gibi okunmasın — ve ada yapıları düzeyinde AYRINTI).
#   rs_ground_a / rs_ground_b  40 m (y −20..+20) × 140 m (x ±70), orijin ortada. Yol koridoru x ±5 düz, z = −0,08 (güverte üstüne oturur).
#   Dışarı doğru yumuşak tepeler (kenarda +3..+6 m), her boyda krater (güneşte parlayan kabarık kenar, mor tonlu iç), koridora yakın
#   sık taş/çakıl (hızla akar → hız hissi), yola paralel gezgin araç izleri, renk çeşitliliği: açık sıcak lavanta-gri yayla, koyu mavi-gri
#   "deniz" lekeleri, mor krater içleri, birkaç kraterde ışıltılı mor/camgöbeği kristal öbeği.
# Uç uca: iki karonun ve krater köprüsünün y kenarlarında yükseklik YALNIZ x'e bağlı ortak kesit (E(x) + iz), karoya özgü değişim
# kenara doğru sıfırlanır (w(y)); kenarı aşan krater/taş yok; renk gürültüsü 40 m dönemli (köprüde y + 20 kaydırmalı).
# Hedef ağ: x'te bantlı çözünürlük (koridora yakın 0,6 m, uzakta 4 m), y'de 1,25 m; taşlar/kristaller dokunun üst şeridinde ayrı adalarda.
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
import uzay_kit as UK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep
import kit

L_TILE, W_HALF, CORR = 40.0, 70.0, 5.0
ZC = -0.08


# ------------------------------------------------------------------ ortak kesit

def E(x):
    """Kenar kesiti (yalnız x): koridor −0,08 düz, 5–7,5 m omuz, dışarı doğru yükselen yumuşak tepeler (sağ +6, sol +4,5)."""
    x = np.asarray(x, np.float64); a = np.abs(x); right = x > 0
    sh = 0.08 * smoothstep(5.0, 7.5, a)
    amp = np.where(right, 6.0, 4.6)
    rise = amp * smoothstep(9.0, 70.0, a) ** 1.4
    ph = np.where(right, 0.7, 2.9)
    und = (0.45 * np.sin(a / 5.3 + ph) + 0.3 * np.sin(a / 2.4 + 1.7 * ph)) * smoothstep(8.0, 16.0, a) + 0.9 * np.sin(a / 11.0 + 2 * ph) * smoothstep(18, 35, a)
    return ZC + sh + rise + und


TRACKS = (6.35, 7.0)


def track(x):
    """Gezgin araç izleri (iki tekerlek izi, her iki yanda): 3 cm oluk + kenarında hafif kabarık set. Döner (yükseklik, maske)."""
    a = np.abs(np.asarray(x, np.float64)); h = np.zeros_like(a); m = np.zeros_like(a)
    for c in TRACKS:
        d = np.abs(a - c)
        h += -0.035 * smoothstep(0.15, 0.09, d) + 0.015 * np.exp(-((d - 0.19) / 0.04) ** 2)
        m = np.maximum(m, smoothstep(0.16, 0.1, d))
    return h, m


def w_edge(y, half=L_TILE / 2, band=6.0):
    return smoothstep(half, half - band, np.abs(np.asarray(y)))


def periodic_field(x, y, seed, terms=10, L=L_TILE, kx=(0.03, 0.12), amp=1.0):
    """y'de L dönemli düşük frekans alan (sinüs toplamı)."""
    R = random.Random(seed); f = np.zeros(np.broadcast(x, y).shape)
    for _ in range(terms):
        ky = TAU * R.randint(1, 3) / L; kxx = R.uniform(*kx) * R.choice((-1, 1)); ph = R.uniform(0, TAU)
        f += np.sin(x * kxx + y * ky + ph)
    return amp * f / math.sqrt(terms)


# ------------------------------------------------------------------ karo içi: tepeler, kraterler

def make_craters(seed, half=L_TILE / 2, n=(4, 10, 30), extra=()):
    """Krater listesi [(cx, cy, r, derinlik)] — büyük (uzak), orta, küçük (koridor yakını). Kenarı aşmaz, koridora girmez."""
    R = random.Random(seed); out = list(extra)
    specs = [(n[0], (5.0, 8.5), (22, 62), 0.22), (n[1], (1.8, 3.6), (9, 45), 0.25), (n[2], (0.35, 1.2), (5.8, 16), 0.3)]
    for cnt, (r0, r1), (a0, a1), dk in specs:
        tries = 0; k = 0
        while k < cnt and tries < cnt * 40:
            tries += 1
            r = R.uniform(r0, r1); a = R.uniform(a0, a1); x = a * R.choice((-1, 1)); y = R.uniform(-half + r * 1.7, half - r * 1.7)
            if abs(x) - r * 1.5 < 5.6: continue
            if any(math.hypot(x - c[0], y - c[1]) < (r + c[2]) * 0.9 for c in out): continue
            out.append((x, y, r, r * dk * R.uniform(0.8, 1.15))); k += 1
    return out


def crater_field(X, Y, craters):
    """Krater yüksekliği + maskeler (iç, kenar, ışınsal saçılım)."""
    h = np.zeros_like(X); cin = np.zeros_like(X); rim = np.zeros_like(X); ej = np.zeros_like(X)
    for (cx, cy, r, d) in craters:
        dx = X - cx; dy = Y - cy; rho = np.sqrt(dx * dx + dy * dy) / r
        near = rho < 2.6
        if not near.any(): continue
        rr = rho[near]
        bowl = -d * np.clip(1 - rr ** 2, 0, 1) ** 0.9
        ridge = d * 0.42 * np.exp(-((rr - 1.0) / 0.2) ** 2)
        apron = d * 0.12 * np.exp(-((rr - 1.45) / 0.45) ** 2)
        h[near] += bowl + ridge + apron
        cin[near] = np.maximum(cin[near], smoothstep(0.95, 0.6, rr))
        rim[near] = np.maximum(rim[near], np.exp(-((rr - 1.02) / 0.16) ** 2))
        if r > 1.5:
            ang = np.arctan2(dy[near], dx[near]); rays = np.abs(np.sin(ang * (5 + int(r) % 4) + cx))
            ej[near] = np.maximum(ej[near], smoothstep(0.75, 0.95, rays) * smoothstep(2.4, 1.15, rr) * smoothstep(1.0, 1.15, rr))
    return h, cin, rim, ej


def hills(X, Y, seed):
    """Karoya özgü tepe dalgası: uzakta iri, yakında küçük; koridor ve omuz düz kalır."""
    R = random.Random(seed); h = np.zeros_like(X); a = np.abs(X)
    for _ in range(26):
        cx = R.uniform(10, 70) * R.choice((-1, 1)); cy = R.uniform(-22, 22); r = R.uniform(4, 12); amp = R.uniform(-1.2, 1.8)
        h += amp * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (r * r)))
    h *= smoothstep(9.0, 24.0, a)
    for _ in range(18):
        cx = R.uniform(6.5, 16) * R.choice((-1, 1)); cy = R.uniform(-22, 22); r = R.uniform(1.0, 3.0); amp = R.uniform(-0.12, 0.2)
        h += amp * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (r * r))) * smoothstep(5.8, 7.5, a)
    return h


def height(X, Y, seed, craters, half=L_TILE / 2, extra_fn=None):
    """Toplam yükseklik + maskeler. extra_fn(X, Y) → (h, maskeler) (krater köprüsü çanağı)."""
    th, tm = track(X)
    w = w_edge(Y, half)
    H = E(X) + th + w * hills(X, Y, seed)
    ch, cin, rim, ej = crater_field(X, Y, craters)
    H = H + ch
    if extra_fn is not None:
        H, cin, rim, ej = extra_fn(X, Y, H, cin, rim, ej)
    H = np.where(np.abs(X) <= CORR, ZC, H)
    # deniz lekeleri: 40 m dönemli ortak alan (kenar) ↔ karoya özgü (iç)
    a = np.abs(X)
    mc = periodic_field(X, Y, 77, 12, kx=(0.02, 0.09))
    mt = periodic_field(X, Y + seed * 13.7, seed + 5, 12, L=97.0, kx=(0.02, 0.09))
    mar = smoothstep(-0.35, 0.25, (1 - w) * mc + w * mt) * smoothstep(6.0, 10.0, a)
    return H, dict(cin=cin, rim=rim, trk=tm * smoothstep(5.2, 5.6, a), mar=mar, ej=ej)


# ------------------------------------------------------------------ malzeme

def m_moon(name, period=L_TILE, off_y=0.0, seed=0.0):
    """Ay toprağı: yayla (sıcak lavanta-gri) + deniz (koyu mavi-gri) + krater içi (mor ton) + güneşli kenar (açık sıcak) + ışınsal saçılım
    (açık) + araç izi (koyu, tırtıl desenli kabartma); ince tane, minik çukur benekleri; 'mask' (R iç, G kenar, B iz, A deniz) ve
    'mask2' (R saçılım) köşe nitelikleri."""
    def b(nt, bsdf):
        G = EK.EG(nt); cw = G.coords(period, off=(seed * 3.1, off_y, 0.0))
        m1 = G.n.new('ShaderNodeAttribute'); m1.attribute_name = 'mask'; m1.attribute_type = 'GEOMETRY'
        m2 = G.n.new('ShaderNodeAttribute'); m2.attribute_name = 'mask2'; m2.attribute_type = 'GEOMETRY'
        cin, rim, trk = G.sep(m1.outputs['Vector']); mar = m1.outputs['Alpha']
        ej, _, _ = G.sep(m2.outputs['Vector'])
        rp = EK.ramp(nt, [(0.28, '#857f95'), (0.5, '#a19bb0'), (0.74, '#bdb6c6')]); G.l.new(G.noise4(cw, 0.08, 3), rp.inputs['Fac'])
        col = rp.outputs[0]
        col = G.mix(G.rng(G.noise4(cw, 0.18, 4), 0.4, 0.7, 0, 0.5), col, '#bfae98')          # sıcak bej yayla lekeleri
        col = G.mix(G.rng(G.noise4(cw, 0.6, 4), 0.35, 0.65, 0, 0.25), col, '#8c84a3')        # morumsu ara ton
        col = G.mix(G.math('MULTIPLY', mar, 0.92), col, G.mix(G.rng(G.noise4(cw, 0.5, 3), 0.3, 0.7), '#4a5172', '#626a8c'))
        col = G.mix(G.math('MULTIPLY', cin, 0.85), col, G.mix(G.rng(G.noise4(cw, 0.9, 3), 0.3, 0.7), '#6e5e94', '#8a7cb0'))
        col = G.mix(G.math('MULTIPLY', ej, 0.45), col, '#e6e1ec')
        col = G.mix(G.math('MULTIPLY', rim, 0.55), col, '#ece4d8')
        col = G.mix(0.16, col, G.noise4(cw, 6.0, 3, 0.6, 'Color'), 'OVERLAY')
        pv = G.vor4(cw, 2.2)
        col = G.mix(G.rng(pv, 0.05, 0.0, 0, 0.35), col, '#5d5672')
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 4, off_y, 0)), 30.0), 0.0, 0.08, 0.5, 0), col, '#f1eef6')
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 8, off_y, 0)), 22.0), 0.0, 0.07, 0.4, 0), col, '#4e4862')
        # araç izi: koyu, sıkıştırılmış toz + tırtıl çizgisi (y'de 0,32 m — 40 m'ye tam bölünür)
        x, y, z = G.sep(G.pos())
        tread = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', G.math('ADD', y, G.math('MULTIPLY', G.math('ABSOLUTE', G.math('SUBTRACT', G.math('FRACT', G.math('MULTIPLY', x, 3.6)), 0.5)), 0.25)), TAU / 0.32 / 2)))
        col = G.mix(G.math('MULTIPLY', trk, 0.55), col, G.mix(G.rng(tread, 0.3, 0.8), '#6d6680', '#8c86a0'))
        col = G.mix(G.rng(G.ao(0.6), 0.85, 0.35, 0, 0.45), col, '#3d3854')
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.35; bb.inputs['Distance'].default_value = 0.02
        hgt = G.math('ADD', G.math('MULTIPLY', G.noise4(cw, 3.0, 4, 0.6), 1.0), G.math('MULTIPLY', G.math('MULTIPLY', trk, G.rng(tread, 0.3, 0.8)), 1.5))
        hgt = G.math('ADD', hgt, G.math('MULTIPLY', G.rng(pv, 0.06, 0.0), -0.8))
        G.l.new(hgt, bb.inputs['Height']); G.l.new(bb.outputs['Normal'], bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def set_masks(o, M):
    """Köşe nitelikleri: mask (R iç, G kenar, B iz, A deniz), mask2 (R saçılım)."""
    me = o.data; n = len(me.vertices)
    a = me.color_attributes.new('mask', 'FLOAT_COLOR', 'POINT'); b = me.color_attributes.new('mask2', 'FLOAT_COLOR', 'POINT')
    A = np.stack([M['cin'].ravel(), M['rim'].ravel(), M['trk'].ravel(), M['mar'].ravel()], -1).astype(np.float32)
    B = np.stack([M['ej'].ravel(), np.zeros(n), np.zeros(n), np.ones(n)], -1).astype(np.float32)
    a.data.foreach_set('color', A.ravel()); b.data.foreach_set('color', B.ravel())


# ------------------------------------------------------------------ parçalar

def rock(name, size, loc, mat, seed, sub=3, rough=0.22, sink=0.25, rot=None):
    import gezegen_engeller as GE
    o = GE.lumpy_rock(name, size, mat, seed=seed, sub=sub, flat=size[2] * 0.12, rough=rough,
                      craters=[((random.Random(seed).uniform(-1, 1), -1, 0.6), 0.3, 0.12)] if size[0] > 0.6 else ())
    R = random.Random(seed)
    o.location = (loc[0], loc[1], loc[2] - size[2] * sink)
    o.rotation_euler = rot or (math.radians(R.uniform(-8, 8)), math.radians(R.uniform(-8, 8)), R.uniform(0, TAU))
    return o


def crystal_cluster(cx, cy, cz, scale, seed, name='gcry'):
    import gezegen_engeller as GE
    R = random.Random(seed)
    mats = [UK._cached('gcv', lambda: UK.m_crystal('gcv', UK.VIOLET, UK.CYAN, -0.1, 0.9)), UK._cached('gcc', lambda: UK.m_crystal('gcc', '#3a6fd1', '#86f2f2', -0.1, 0.8)),
            UK._cached('gcp', lambda: UK.m_crystal('gcp', '#8a4fd8', '#f0a8ff', -0.1, 0.8))]
    out = []
    for k in range(R.randint(4, 6)):
        d = V((R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), 1.0)).normalized() if k else V((0, 0, 1))
        L = scale * (1.0 if k == 0 else R.uniform(0.45, 0.75))
        out.append(GE.crystal(name, (cx + R.uniform(-0.25, 0.25) * scale * (k > 0), cy + R.uniform(-0.25, 0.25) * scale * (k > 0), cz - 0.05 * scale),
                              tuple(d), L, L * 0.2, mats[(k + seed) % 3], twist=R.uniform(0, 1)))
    return out


def scatter(H_fn, seed, half, n_rocks=22, n_boulders=4, n_pebbles=380, avoid=()):
    """Taşlar (hedefte) + çakıllar (yalnız taslak): koridora yakın sık. H_fn(x, y) → z."""
    R = random.Random(seed); ROCK = UK._cached('gl_rock', lambda: UK.m_regolith('gl_rock', ('#6e6a80', '#928da4', '#bab5c8'), craters=0.6, dust=0.35, seed=2.0, scale=1.5))
    rocks = []; pebbles = []
    def ok(x, y, r):
        return abs(y) < half - r - 0.3 and all(math.hypot(x - ax, y - ay) > r + ar for (ax, ay, ar) in avoid)
    k = 0; t = 0
    while k < n_rocks and t < 500:
        t += 1
        x = R.uniform(5.7, 13.5) * R.choice((-1, 1)); x = math.copysign(5.7 + (abs(x) - 5.7) ** 1.0 * R.uniform(0.3, 1.0), x)
        y = R.uniform(-half, half); s = R.uniform(0.18, 0.7)
        if not ok(x, y, s) or any(abs(abs(x) - c) < 0.3 for c in TRACKS): continue
        rocks.append(rock('grock', (s * R.uniform(1.0, 1.5), s * R.uniform(0.8, 1.2), s * R.uniform(0.55, 0.9)), (x, y, float(H_fn(x, y))), ROCK, seed * 100 + k, sub=3))
        k += 1
    k = 0; t = 0
    while k < n_boulders and t < 300:
        t += 1
        x = R.uniform(14, 30) * R.choice((-1, 1)); y = R.uniform(-half + 3, half - 3); s = R.uniform(1.1, 2.4)
        if not ok(x, y, s * 1.2): continue
        rocks.append(rock('gboulder', (s * 1.3, s, s * 0.8), (x, y, float(H_fn(x, y))), ROCK, seed * 100 + 50 + k, sub=4, rough=0.18))
        k += 1
    PEB = UK._cached('gl_peb', lambda: UK.m_regolith('gl_peb', ('#77728a', '#9a95ab', '#c4bfd2'), craters=0.2, dust=0.3, seed=5.0, scale=4.0))
    for k in range(n_pebbles):
        a = 5.3 + R.expovariate(1 / 3.0); x = math.copysign(min(a, 22.0), R.choice((-1, 1))); y = R.uniform(-half - 2.5, half + 2.5)
        s = R.uniform(0.04, 0.16) * (1.0 if a < 9 else 1.6)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        so = V((R.uniform(0, 30), R.uniform(0, 30), 0))
        for v in bm.verts:
            v.co = V((v.co.x * s * 1.3, v.co.y * s, v.co.z * s * 0.6)) * (1 + 0.25 * MN.noise(v.co * 2 + so))
        o = EK.A.link_mesh('pebble', bm, [PEB]); o.location = (x, y, float(H_fn(x, ((y + half) % (2 * half)) - half)) - s * 0.15)
        o.rotation_euler = (0, 0, R.uniform(0, TAU)); pebbles.append(o)
    return rocks, pebbles


# ------------------------------------------------------------------ hedef ağ ve UV

def band_columns(half_w=W_HALF):
    near = list(np.arange(CORR, 14.0 + 1e-6, 0.6)); mid = list(np.arange(16.5, 34.0 + 1e-6, 2.5)); far = list(np.arange(39.0, half_w + 1e-6, 5.0))
    side = sorted(set([round(v, 3) for v in near + mid + far + [half_w]]))
    return np.array(sorted([-v for v in side] + [0.0] + side))


def u_of_x(x):
    """Dokuda x yerleşimi: koridor dar, yakın bant geniş (≈ 41 px/m), orta 15, uzak 7 px/m (2048'de)."""
    xs = [-70, -34, -14, -5, 5, 14, 34, 70]; us = [0.0, 0.12, 0.27, 0.47, 0.53, 0.73, 0.88, 1.0]
    return np.interp(x, xs, us)


def ground_uv(y0=-20.0, y1=20.0, v_terrain=0.9, groups=10):
    """uv_fn: arazi yüzleri (part 0) üstten izdüşüm, v 0..0,9; taş/kristal yüzleri (part ≥ 1) grup grup akıllı açılıp üst şeride
    (v 0,9..1) yan yana paketlenir."""
    def f(L):
        me = L.data
        for l in list(me.uv_layers): me.uv_layers.remove(l)
        uv = me.uv_layers.new(name='UVMap'); me.uv_layers.active = uv
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
        part = np.zeros(len(me.polygons), np.int32)
        if 'part' in me.attributes: me.attributes['part'].data.foreach_get('value', part)
        ls = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', ls)
        lt = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', lt)
        lpart = np.repeat(part, lt)
        U = u_of_x(co[vi, 0]); Vv = (co[vi, 1] - y0) / (y1 - y0) * v_terrain
        uvd = np.stack([U, Vv], -1).astype(np.float32)
        uv.data.foreach_set('uv', uvd.reshape(-1))
        ng = int(part.max())
        bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); bpy.context.view_layer.objects.active = L
        for g in range(1, ng + 1):
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='FACE'); bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            sel = (part == g)
            me.polygons.foreach_set('select', sel.tolist())
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02, scale_to_bounds=True)
            bpy.ops.uv.pack_islands(rotate=True, margin=0.01)
            bpy.ops.object.mode_set(mode='OBJECT')
            d = np.empty(len(me.loops) * 2, np.float32); uv.data.foreach_get('uv', d); d = d.reshape(-1, 2)
            m = lpart == g
            gi = g - 1
            d[m, 0] = (gi % groups + d[m, 0]) / groups; d[m, 1] = v_terrain + d[m, 1] * (1 - v_terrain)
            uv.data.foreach_set('uv', d.reshape(-1))
        bpy.ops.object.select_all(action='DESELECT')
    return f


def tag_part(o, g):
    a = o.data.attributes.get('part') or o.data.attributes.new('part', 'INT', 'FACE')
    a.data.foreach_set('value', [g] * len(o.data.polygons))
    return o


# ================================================================== rs_ground_a / rs_ground_b

def build_ground(seed):
    half = L_TILE / 2
    craters = make_craters(seed * 31 + 7, half)
    hfn = lambda x, y: height(np.array([[x]]), np.array([[y]]), seed, craters, half)[0][0, 0]
    mat = m_moon('moon%d' % seed, seed=0.0)
    # taslak: yakın bantta 0,15 m, uzakta 0,5 m; y −23..23 (uç AO'su)
    xs = np.concatenate([np.arange(-W_HALF, -20, 0.5), np.arange(-20, -CORR, 0.15), np.linspace(-CORR, CORR, 9), np.arange(CORR + 0.15, 20, 0.15), np.arange(20, W_HALF + 0.01, 0.5)])
    ys = np.arange(-half - 3, half + 3 + 1e-6, 0.15)
    X, Y = np.meshgrid(xs, ys)
    Yp = ((Y + half) % (2 * half)) - half                         # uç dışındaki taslak: komşunun kenar bölgesi (w ≈ 0 → ortak kesit)
    H, M = height(X, Yp, seed, craters, half)
    hi_t = EK.grid_obj('terrain_hi', np.stack([X, Y, H], -1), None, [mat])
    set_masks(hi_t, M)
    hi = [hi_t]
    # hedef arazi
    XL, YL = np.meshgrid(band_columns(), np.linspace(-half, half, 33))
    HL, _ = height(XL, YL, seed, craters, half)
    lo_t = EK.grid_obj('terrain_lo', np.stack([XL, YL, HL], -1), None, []); tag_part(lo_t, 0)
    lo = [lo_t]
    # kristal öbekleri: 1–2 orta boy kraterin dibinde
    cands = sorted([c for c in craters if 1.8 < c[2] < 4.0 and abs(c[0]) < 30], key=lambda c: abs(c[0]))[:2]
    props = []; avoid = [(c[0], c[1], c[2] * 1.1) for c in craters if c[2] > 1.5]
    for i, (cx, cy, r, d) in enumerate(cands):
        props.append(crystal_cluster(cx, cy, float(hfn(cx, cy)), 0.9 + r * 0.25, seed * 10 + i))
    rocks, pebbles = scatter(hfn, seed, half, avoid=avoid)
    hi += rocks + pebbles + [o for p in props for o in p]
    g = 1
    for i, o in enumerate(rocks):
        tgt = 90 if o.name.startswith('gboulder') else 32
        lo += [tag_part(q, 1 + i % 8) for q in EK.build_low2([o], [(r'.', tgt)])]
    for i, grp in enumerate(props):
        lo += [tag_part(q, 9 + i) for q in EK.build_low2(grp, [(r'.', 30)])]
    return hi, lo, dict(uv_fn=ground_uv(-half, half), cull=False, tex=2048, ao_dist=1.5, ao_strength=0.5, cage=0.35, ray=1.4,
                        draft=dict(yaw=-20, pitch=12, target=(0, -8, 1.0), dist=26))


def build_ground_a(): return build_ground(1)
def build_ground_b(): return build_ground(2)


BUILD = {'rs_ground_a': build_ground_a, 'rs_ground_b': build_ground_b}
