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
from kit import blob, tube, cyl

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
    for _ in range(3):                                                  # uzun sırtlar (y boyunca), dış bantta
        cx = R.uniform(28, 60) * R.choice((-1, 1)); amp = R.uniform(1.0, 2.2); r = R.uniform(2.5, 4.5); ph = R.uniform(0, TAU)
        h += amp * np.exp(-((X - cx - 2.0 * np.sin(Y / 9.0 + ph)) / r) ** 2)
    h *= smoothstep(9.0, 24.0, a)
    for _ in range(18):
        cx = R.uniform(6.5, 16) * R.choice((-1, 1)); cy = R.uniform(-22, 22); r = R.uniform(1.0, 3.0); amp = R.uniform(-0.12, 0.2)
        h += amp * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (r * r))) * smoothstep(5.8, 7.5, a)
    return h


def height(X, Y, seed, craters, half=L_TILE / 2, extra_fn=None, corridor_fn=None):
    """Toplam yükseklik + maskeler. extra_fn(X, Y) → (h, maskeler) (krater köprüsü çanağı)."""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    th, tm = track(X)
    w = w_edge(Y, half)
    H = E(X) + th + w * hills(X, Y, seed)
    ch, cin, rim, ej = crater_field(X, Y, craters)
    H = H + ch
    if extra_fn is not None:
        H, cin, rim, ej = extra_fn(X, Y, H, cin, rim, ej)
    cm = (np.abs(X) <= CORR) if corridor_fn is None else corridor_fn(X, Y)
    H = np.where(cm, ZC, H)
    # deniz lekeleri: 40 m dönemli ortak alan (kenar) ↔ karoya özgü (iç)
    a = np.abs(X)
    mc = periodic_field(X, Y, 77, 12, kx=(0.02, 0.09))
    mt = periodic_field(X, Y + seed * 13.7, seed + 5, 12, L=97.0, kx=(0.02, 0.09))
    mar = smoothstep(-0.35, 0.25, (1 - w) * mc + w * mt) * smoothstep(6.0, 10.0, a)
    return H, dict(cin=cin, rim=rim, trk=tm * smoothstep(5.2, 5.6, a), mar=mar, ej=ej)


# ------------------------------------------------------------------ malzeme

def imprints(G, cw, scale, density, depth, seed=0.0):
    """Çok sayıda küçük krater izi (Voronoi hücresi başına rastgele boy, yalnız hücrelerin bir kısmında): çukur + kabarık halka.
    Döner (yükseklik, iç maske, halka maske)."""
    vec, w = cw
    v = G.n.new('ShaderNodeTexVoronoi'); v.voronoi_dimensions = '4D' if w is not None else '3D'; v.feature = 'F1'
    v.inputs['Scale'].default_value = scale; v.inputs['Randomness'].default_value = 0.9
    G.l.new(vec, v.inputs['Vector'])
    if w is not None: G.l.new(G.math('ADD', w, seed), v.inputs['W'])
    d = v.outputs['Distance']; rc, gc, bc = G.sep(v.outputs['Color'])
    present = G.rng(rc, 1.0 - density, 1.0 - density + 0.02)
    size = G.math('ADD', 0.14, G.math('MULTIPLY', gc, 0.24))
    t = G.math('DIVIDE', d, size)
    bowl = G.math('MULTIPLY', G.rng(t, 1.0, 0.55), present)
    ring = G.math('MULTIPLY', G.rng(G.math('ABSOLUTE', G.math('SUBTRACT', t, 1.08)), 0.22, 0.0), present)
    h = G.math('ADD', G.math('MULTIPLY', bowl, -depth), G.math('MULTIPLY', ring, depth * 0.55))
    return h, bowl, ring


def m_moon(name, period=L_TILE, off_y=0.0, seed=0.0):
    """Ay toprağı (ada zemini yoğunluğunda ayrıntı, piştirilir): yayla (sıcak lavanta-gri) + deniz (koyu mavi-gri, benekli kenar) + krater içi
    (mor) + güneşli kenar + ışınsal saçılım + araç izi ('mask'/'mask2' köşe nitelikleri); çok ölçekli küçük krater izleri, rüzgârsız Ay'da
    yumuşak toz dalgacıkları, koridor yanında iki bot izi patikası (sol/sağ adım, tabanda tırtıl), regolit tanesi, renk lekeleri."""
    def b(nt, bsdf):
        G = EK.EG(nt); cw = G.coords(period, off=(seed * 3.1, off_y, 0.0))
        m1 = G.n.new('ShaderNodeAttribute'); m1.attribute_name = 'mask'; m1.attribute_type = 'GEOMETRY'
        m2 = G.n.new('ShaderNodeAttribute'); m2.attribute_name = 'mask2'; m2.attribute_type = 'GEOMETRY'
        cin, rim, trk = G.sep(m1.outputs['Vector']); mar = m1.outputs['Alpha']
        ej, _, _ = G.sep(m2.outputs['Vector'])
        x, y, z = G.sep(G.pos()); ax = G.math('ABSOLUTE', x)
        yy = G.math('ADD', y, off_y)
        rp = EK.ramp(nt, [(0.28, '#857f95'), (0.5, '#a19bb0'), (0.74, '#bdb6c6')]); G.l.new(G.noise4(cw, 0.08, 3), rp.inputs['Fac'])
        col = rp.outputs[0]
        col = G.mix(G.rng(G.noise4(cw, 0.18, 4), 0.4, 0.7, 0, 0.5), col, '#bfae98')          # sıcak bej yayla lekeleri
        col = G.mix(G.rng(G.noise4(cw, 0.6, 4), 0.35, 0.65, 0, 0.25), col, '#8c84a3')        # morumsu ara ton
        col = G.mix(G.rng(G.noise4(cw, 1.7, 4), 0.42, 0.62, 0, 0.18), col, '#d2cbd8')        # açık leke
        mfl = G.math('MULTIPLY', G.rng(G.noise4(cw, 2.6, 3), 0.55, 0.62), G.rng(G.noise4(cw, 0.3, 3), 0.45, 0.6))
        col = G.mix(G.math('MAXIMUM', G.math('MULTIPLY', mar, 0.9), G.math('MULTIPLY', mfl, 0.55)), col,
                    G.mix(G.rng(G.noise4(cw, 0.5, 3), 0.3, 0.7), '#4a5172', '#626a8c'))            # deniz + benekli kenar
        col = G.mix(G.math('MULTIPLY', cin, 0.85), col, G.mix(G.rng(G.noise4(cw, 0.9, 3), 0.3, 0.7), '#6e5e94', '#8a7cb0'))
        col = G.mix(G.math('MULTIPLY', ej, 0.45), col, '#e6e1ec')
        col = G.mix(G.math('MULTIPLY', rim, 0.55), col, '#ece4d8')
        # küçük krater izleri: üç ölçek (hücre ≈ 0,5 / 1,6 / 4,5 m)
        hsum = None
        for (sc_, den, dp, sd) in ((2.0, 0.35, 0.6, 1.0), (0.62, 0.3, 1.0, 7.0), (0.22, 0.28, 1.4, 13.0)):
            h_, bowl, ring = imprints(G, cw, sc_, den, dp, sd)
            col = G.mix(G.math('MULTIPLY', bowl, 0.5), col, '#7a6d97')
            col = G.mix(G.math('MULTIPLY', ring, 0.45), col, '#ddd6e2')
            hsum = h_ if hsum is None else G.math('ADD', hsum, h_)
        # toz dalgacıkları (bölge bölge)
        k = TAU * 140 / 40.0
        rip = G.math('SINE', G.math('ADD', G.math('MULTIPLY', G.math('ADD', yy, G.math('MULTIPLY', x, 0.35)), k), G.math('MULTIPLY', G.noise4(cw, 0.4, 2), 6.0)))
        ripm = G.rng(G.noise4(cw, 0.12, 3), 0.5, 0.62)
        col = G.mix(G.math('MULTIPLY', G.rng(rip, 0.3, 1.0), G.math('MULTIPLY', ripm, 0.18)), col, '#d0c9d9')
        # bot izi patikaları (iki yanda, hafif kıvrılarak; 0,3636 m adım = 40 m'de 110 adım)
        fp_sum = None
        for (x0, amp, ph) in ((-5.7, 0.35, 0.3), (8.2, 0.5, 2.1)):
            xc = G.math('ADD', x0, G.math('MULTIPLY', G.math('SINE', G.math('ADD', G.math('MULTIPLY', yy, TAU * 3 / 40.0), ph)), amp))
            dx = G.math('SUBTRACT', x, xc)
            st = G.math('DIVIDE', yy, 0.3636)
            side = G.math('SUBTRACT', G.math('MULTIPLY', G.math('MODULO', G.math('FLOOR', st), 2.0), 2.0), 1.0)
            cy = G.math('MULTIPLY', G.math('SUBTRACT', G.math('FRACT', st), 0.5), 0.3636)
            cx = G.math('SUBTRACT', dx, G.math('MULTIPLY', side, 0.1))
            e = G.math('ADD', G.math('POWER', G.math('DIVIDE', cx, 0.055), 2.0), G.math('POWER', G.math('DIVIDE', cy, 0.125), 2.0))
            fp = G.rng(e, 1.0, 0.6)
            fp_sum = fp if fp_sum is None else G.math('MAXIMUM', fp_sum, fp)
        tread2 = G.rng(G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', yy, 140.0))), 0.4, 0.8)
        col = G.mix(G.math('MULTIPLY', fp_sum, 0.55), col, G.mix(tread2, '#6f6884', '#857e98'))
        col = G.mix(0.16, col, G.noise4(cw, 6.0, 3, 0.6, 'Color'), 'OVERLAY')
        pv = G.vor4(cw, 2.2)
        col = G.mix(G.rng(pv, 0.05, 0.0, 0, 0.35), col, '#5d5672')
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 4, off_y, 0)), 30.0), 0.0, 0.08, 0.5, 0), col, '#f1eef6')
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 8, off_y, 0)), 22.0), 0.0, 0.07, 0.4, 0), col, '#4e4862')
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 12, off_y, 0)), 60.0), 0.0, 0.06, 0.45, 0), col, '#b9b2c8')
        # araç izi: koyu, sıkıştırılmış toz + tırtıl çizgisi (y'de 0,32 m — 40 m'ye tam bölünür)
        tread = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', G.math('ADD', y, G.math('MULTIPLY', G.math('ABSOLUTE', G.math('SUBTRACT', G.math('FRACT', G.math('MULTIPLY', x, 3.6)), 0.5)), 0.25)), TAU / 0.32 / 2)))
        col = G.mix(G.math('MULTIPLY', trk, 0.55), col, G.mix(G.rng(tread, 0.3, 0.8), '#6d6680', '#8c86a0'))
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.4; bb.inputs['Distance'].default_value = 0.02
        hgt = G.math('ADD', G.math('MULTIPLY', G.noise4(cw, 3.0, 4, 0.6), 0.8), G.math('MULTIPLY', G.math('MULTIPLY', trk, G.rng(tread, 0.3, 0.8)), 1.5))
        hgt = G.math('ADD', hgt, G.math('MULTIPLY', G.rng(pv, 0.06, 0.0), -0.8))
        hgt = G.math('ADD', hgt, G.math('MULTIPLY', hsum, 1.0))
        hgt = G.math('ADD', hgt, G.math('MULTIPLY', G.math('MULTIPLY', rip, ripm), 0.12))
        hgt = G.math('ADD', hgt, G.math('MULTIPLY', fp_sum, -0.7))
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


def scatter(H_fn, seed, half, n_boulders=10, n_pebbles=160, avoid=(), ok_fn=None):
    """Hedefe giren 1–3 m kaya blokları (|x| 9–60; koridora yakın küçük taş/çakılı oyun kodu (MoonField) 3B serper) + yalnız taslakta
    uzak bant (|x| > 25) çakılları. H_fn(x, y) → z."""
    R = random.Random(seed); ROCK = UK._cached('gl_rock', lambda: UK.m_regolith('gl_rock', ('#6e6a80', '#928da4', '#bab5c8'), craters=0.6, dust=0.35, seed=2.0, scale=1.5))
    rocks = []; pebbles = []
    def ok(x, y, r):
        return abs(y) < half - r - 0.3 and all(math.hypot(x - ax, y - ay) > r + ar for (ax, ay, ar) in avoid) and (ok_fn is None or ok_fn(x, y))
    k = 0; t = 0
    while k < n_boulders and t < 600:
        t += 1
        a = R.uniform(9, 26) if k < n_boulders * 0.6 else R.uniform(26, 60)
        x = a * R.choice((-1, 1)); y = R.uniform(-half + 3, half - 3); s = R.uniform(1.0, 2.8)
        if not ok(x, y, s * 1.2): continue
        rocks.append(rock('gboulder', (s * R.uniform(1.1, 1.5), s, s * R.uniform(0.6, 0.85)), (x, y, float(H_fn(x, y))), ROCK, seed * 100 + 50 + k, sub=4, rough=0.2))
        k += 1
    PEB = UK._cached('gl_peb', lambda: UK.m_regolith('gl_peb', ('#77728a', '#9a95ab', '#c4bfd2'), craters=0.2, dust=0.3, seed=5.0, scale=4.0))
    for k in range(n_pebbles):
        x = math.copysign(R.uniform(25.5, 60.0), R.choice((-1, 1))); y = R.uniform(-half - 2.5, half + 2.5)
        s = R.uniform(0.12, 0.35)
        if ok_fn is not None and not ok_fn(x, y): continue
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        so = V((R.uniform(0, 30), R.uniform(0, 30), 0))
        for v in bm.verts:
            v.co = V((v.co.x * s * 1.3, v.co.y * s, v.co.z * s * 0.6)) * (1 + 0.25 * MN.noise(v.co * 2 + so))
        o = EK.A.link_mesh('pebble', bm, [PEB]); o.location = (x, y, float(H_fn(x, ((y + half) % (2 * half)) - half)) - s * 0.15)
        o.rotation_euler = (0, 0, R.uniform(0, TAU)); pebbles.append(o)
    return rocks, pebbles


# ------------------------------------------------------------------ hedef ağ ve UV

def band_columns(half_w=W_HALF):
    near = list(np.arange(CORR, 14.0 + 1e-6, 0.75)); mid = list(np.arange(15.25, 25.0 + 1e-6, 1.25)); m2 = list(np.arange(28.0, 40.0 + 1e-6, 3.0))
    far = list(np.arange(45.0, half_w + 1e-6, 5.0))
    side = sorted(set([round(v, 3) for v in near + mid + m2 + far + [half_w]]))
    return np.array(sorted([-v for v in side] + [0.0] + side))


U_GROUND = ([-70, -25, -4.2, 4.2, 25, 70], [0.0, 0.2033, 0.485, 0.515, 0.7967, 1.0])     # iç bant 3× yoğun (≈ 28 px/m), dış ≈ 9 px/m
U_BRIDGE = ([-70, -45, -20, 20, 45, 70], [0.0, 0.11, 0.29, 0.71, 0.89, 1.0])


def u_of_x(x, um=U_GROUND):
    """Dokuda x yerleşimi: koridor dar, yakın bant geniş (≈ 41 px/m), orta 15, uzak 7 px/m (2048'de)."""
    return np.interp(x, um[0], um[1])


def prep_uvs(lo, y0, y1, um=U_GROUND, v_terrain=0.86, rows=2):
    """UV'ler birleştirmeden ÖNCE, nesne başına: arazi (part 0) üstten izdüşüm (x bantlı), v 0..v_terrain; diğer her nesne tek başına
    akıllı açılıp üst şeritte kendi kutucuğuna paketlenir. (Birleşik ağda seçimle grup grup açmak tüm yüzleri yeniden açıyordu.)"""
    others = [o for o in lo if int(o.get('part', 0)) != 0]
    cols = max(1, int(math.ceil(len(others) / rows))); cw = 1.0 / cols; rh = (1.0 - v_terrain) / rows
    k = 0
    for o in lo:
        me = o.data
        for l in list(me.uv_layers): me.uv_layers.remove(l)
        uv = me.uv_layers.new(name='UVMap'); me.uv_layers.active = uv
        if int(o.get('part', 0)) == 0:
            co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
            co = co @ np.array(o.matrix_world.to_3x3()).T + np.array(o.matrix_world.translation)
            vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
            d = np.stack([u_of_x(co[vi, 0], um), (co[vi, 1] - y0) / (y1 - y0) * v_terrain], -1).astype(np.float32)
            uv.data.foreach_set('uv', d.reshape(-1)); me.update(); continue
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.03, scale_to_bounds=True)
        bpy.ops.uv.pack_islands(rotate=True, margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
        me = o.data; uv = me.uv_layers['UVMap']                    # düzenleme kipinden sonra eski başvuru geçersiz (çöküyordu)
        d = np.empty(len(me.loops) * 2, np.float32); uv.data.foreach_get('uv', d); d = d.reshape(-1, 2)
        r, c = divmod(k, cols)
        d[:, 0] = (c + 0.03 + d[:, 0] * 0.94) * cw; d[:, 1] = v_terrain + (r + 0.03 + d[:, 1] * 0.94) * rh
        uv.data.foreach_set('uv', d.reshape(-1)); me.update(); k += 1      # update: birleştirme değerlendirilmiş ağı okur (yoksa eski UV)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.update()


def keep_uv(L):
    """uv_fn: birleşik ağda hazır 'UVMap' korunur."""
    me = L.data
    for l in [l for l in me.uv_layers if l.name != 'UVMap']: me.uv_layers.remove(l)
    me.uv_layers.active = me.uv_layers['UVMap']


def tag_part(o, g):
    o['part'] = g
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
    for i, o in enumerate(rocks):
        lo += [tag_part(q, 1 + i % 8) for q in EK.build_low2([o], [(r'.', 110)])]
    for i, grp in enumerate(props):
        lo += [tag_part(q, 9 + i) for q in EK.build_low2(grp, [(r'.', 30)])]
    prep_uvs(lo, -half, half)
    return hi, lo, dict(uv_fn=keep_uv, cull=False, tex=2048, ntex=1024, ao_dist=1.5, ao_strength=0.5, cage=0.35, ray=1.4,
                        draft=dict(yaw=-20, pitch=12, target=(0, -8, 1.0), dist=26))


def build_ground_a(): return build_ground(1)
def build_ground_b(): return build_ground(2)


BUILD = {'rs_ground_a': build_ground_a, 'rs_ground_b': build_ground_b}


# ================================================================== rs_crater_bridge (80 m: yol krateri köprüyle geçer)

BR_HALF = 40.0
CR_RX, CR_RY, CR_D = 46.0, 30.0, 20.0


def crater_rho(X, Y):
    return np.sqrt((X / CR_RX) ** 2 + (Y / CR_RY) ** 2)


def big_crater(X, Y, H, cin, rim, ej):
    """Büyük krater: elips (x 46 m, y 30 m), 20 m derin, basamaklı iç duvar, düz taban, kabarık kenar (koridorda çentikli: güverte
    dudaktan krater üstüne çıkar). Kenarlarda (|y| → 40) etkisi sıfır: uçlar zemin karolarıyla aynı kesitte."""
    rho = crater_rho(X, Y); w = smoothstep(BR_HALF, BR_HALF - 6.0, np.abs(Y))
    t = np.clip(1 - rho ** 2, 0, 1)
    bowl = -CR_D * t ** 0.75
    q = bowl / 3.2; fl = np.floor(q)
    terr = (fl + smoothstep(0.3, 0.7, q - fl)) * 3.2                                 # yumuşak basamak (keskin kenar çentik çizgisi yapıyordu)
    inner = smoothstep(0.3, 0.45, rho) * smoothstep(0.98, 0.9, rho)
    bowl = bowl * (1 - 0.45 * inner) + terr * 0.45 * inner
    bowl = np.where(rho < 0.36, -CR_D + 0.8 * np.sin(X * 0.4) * np.cos(Y * 0.5) * smoothstep(0.36, 0.2, rho), bowl)
    notch = smoothstep(5.0, 10.0, np.abs(X))
    ridge = 2.2 * np.exp(-((rho - 1.0) / 0.07) ** 2) * notch + 0.9 * np.exp(-((rho - 1.18) / 0.15) ** 2) * notch
    Hn = H + w * (np.where(rho < 1.0, bowl - (H - ZC) * t, 0.0) + ridge)
    cin2 = np.maximum(cin, smoothstep(1.0, 0.7, rho) * w)
    rim2 = np.maximum(rim, np.exp(-((rho - 1.0) / 0.06) ** 2) * notch * w)
    ang = np.arctan2(Y, X); rays = np.abs(np.sin(ang * 7 + 1.3))
    ej2 = np.maximum(ej, smoothstep(0.8, 0.97, rays) * smoothstep(1.6, 1.05, rho) * smoothstep(1.0, 1.06, rho) * w)
    return Hn, cin2, rim2, ej2


def bridge_corridor(X, Y):
    return (np.abs(X) <= CORR) & (crater_rho(X, Y) >= 1.0)


def tower(name, y, zg, mat, cap_mat):
    """Kafes destek kulesi: 4 ayak (dikdörtgen kutu), her 2,5 m'de yatay halka + çapraz, tepede güverte kirişlerini taşıyan başlık
    (z −0,7'ye dek). zg: tabandaki zemin yüksekliği."""
    parts = []; hw = 1.2; top = -0.7; z0 = zg - 0.3
    for (dx, dy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        parts.append(EK.rounded_box(name + '_leg', (0.28, 0.28, top - 0.25 - z0), 0.04, 0.12, [mat], loc=(dx * hw, y + dy * hw, (z0 + top - 0.25) / 2), seed=int(y)))
    n = max(2, int((top - z0) / 2.5))
    for k in range(n):
        za = z0 + 0.8 + k * (top - 0.6 - z0 - 0.8) / n; zb = za + (top - 0.6 - z0 - 0.8) / n
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            pa = V((a[0] * hw, y + a[1] * hw, za)); pb = V((b[0] * hw, y + b[1] * hw, zb)); pc = V((b[0] * hw, y + b[1] * hw, za))
            parts.append(UK.cable(name + '_br', [tuple(pa), tuple((pa + pb) / 2), tuple(pb)], 0.07, mat, res=1))
            parts.append(UK.cable(name + '_ring', [tuple(pa), tuple((pa + pc) / 2), tuple(pc)], 0.07, mat, res=1))
    parts.append(EK.rounded_box(name + '_cap', (6.6, 1.0, 0.35), 0.05, 0.1, [cap_mat], loc=(0, y, top - 0.175), seed=int(y) + 3))
    parts.append(EK.rounded_box(name + '_head', (3.0, 3.0, 0.3), 0.05, 0.1, [cap_mat], loc=(0, y, top - 0.5), seed=int(y) + 4))
    parts.append(EK.rounded_box(name + '_foot', (3.2, 3.2, 0.5), 0.06, 0.12, [cap_mat], loc=(0, y, z0 + 0.1), seed=int(y) + 5))
    for sx in (-1, 1):
        parts += UK.lamp(name + '_lamp', (sx * 3.1, y - 0.3, top), 0.12, UK.SUN if sx < 0 else UK.CYAN, cage=True, base_h=0.06)
    return parts


def tent(name, loc, yaw):
    """Küçük araştırma çadırı: çizgili kubbe çadır, kapı perdesi, kazık + gergi ipleri, minik lamba."""
    TN = EK.m_cloth(name + 'c', UK.CORAL, UK.CREAM, stripes=1.6, axis='Z', fade=0.15)
    prof = [(0.0, 0.0), (1.45, 0.0), (1.4, 0.45), (1.2, 0.9), (0.85, 1.25), (0.4, 1.45), (0.0, 1.5)]
    t = EK.lathe_grid(name, prof, 24, [TN], uv=False)
    door = EK.rounded_box(name + '_door', (0.8, 0.12, 1.0), 0.1, 0.05, [EK.m_cloth(name + 'd', UK.NAVY, None)], loc=(0, -1.38, 0.5))
    parts = [t, door]
    AL = UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3))
    for k in range(4):
        a = k / 4 * TAU + 0.6; p0 = V((math.cos(a) * 1.25, math.sin(a) * 1.25, 0.9)); p1 = V((math.cos(a) * 2.1, math.sin(a) * 2.1, 0.02))
        parts.append(UK.cable(name + '_rope', [tuple(p0), tuple((p0 + p1) / 2), tuple(p1)], 0.015, AL, res=1))
        parts.append(cyl(name + '_stake', tuple(p1 + V((0, 0, 0.08))), 0.03, 0.18, AL, verts=6, bevel=0.0))
    parts += UK.lamp(name + '_lamp', (0.9, -1.0, 0.0), 0.1, UK.SUN, cage=True, base_h=0.05)
    import ay_donatim as AD
    return AD.group_transform(parts, loc, (0, 0, yaw))


def build_crater_bridge():
    half = BR_HALF
    ok_out = lambda x, y: crater_rho(np.array(x), np.array(y)) > 1.25
    craters = [c for c in make_craters(911, half, n=(5, 12, 36)) if ok_out(c[0], c[1]) and crater_rho(np.array(c[0]), np.array(c[1])) > 1.25 + c[2] / 30]
    floor_c = [(-12.0, 4.0, 2.2, 0.6), (9.0, -6.0, 1.6, 0.45), (3.0, 9.0, 1.2, 0.35), (-6.0, -8.0, 1.4, 0.4), (15.0, 8.0, 1.8, 0.5)]
    def extra(X, Y, H, cin, rim, ej):
        H, cin, rim, ej = big_crater(X, Y, H, cin, rim, ej)
        h2, c2, r2, e2 = crater_field(X, Y, floor_c)                 # taban kraterleri büyük çanaktan SONRA
        return H + h2, np.maximum(cin, c2), np.maximum(rim, r2), np.maximum(ej, e2)
    hk = dict(extra_fn=extra, corridor_fn=bridge_corridor, half=half)
    hfn = lambda x, y: height(np.array([[x]]), np.array([[y]]), 3, craters, **hk)[0][0, 0]
    mat = m_moon('moonbr', off_y=L_TILE / 2)
    xs = np.concatenate([np.arange(-W_HALF, -20, 0.5), np.arange(-20, 20, 0.2), np.arange(20, W_HALF + 0.01, 0.5)])
    ys = np.arange(-half - 3, half + 3 + 1e-6, 0.2)
    X, Y = np.meshgrid(xs, ys)
    Yp = np.where(np.abs(Y) > half, np.sign(Y) * (half - (np.abs(Y) - half)), Y)     # uç dışı: kenara simetrik (w ≈ 0: ortak kesit)
    H, M = height(X, Yp, 3, craters, **hk)
    hi_t = EK.grid_obj('terrain_hi', np.stack([X, Y, H], -1), None, [mat]); set_masks(hi_t, M)
    hi = [hi_t]
    cols = sorted(set(list(band_columns()) + [-4.0, -3.0, -2.0, -1.0, 1.0, 2.0, 3.0, 4.0] + list(np.arange(-20, 20.1, 2.0))))
    XL, YL = np.meshgrid(np.array(cols), np.linspace(-half, half, 41))
    HL, _ = height(XL, YL, 3, craters, **hk)
    lo_t = EK.grid_obj('terrain_lo', np.stack([XL, YL, HL], -1), None, []); tag_part(lo_t, 0)
    lo = [lo_t]
    groups = []
    # destek kuleleri (y = −20, 0, 20)
    TW = UK.m_paint('brtower', UK.CORAL, chips=0.35, dust=0.3, grime=0.45, seed=1.0); CP = UK.m_paint('brcap', UK.NAVY, chips=0.35, dust=0.3, seed=2.0)
    for yt in (-20.0, 0.0, 20.0):
        zg = min(float(hfn(-1.2, yt)), float(hfn(1.2, yt)), float(hfn(0, yt)))
        groups.append(tower('tw', yt, zg, TW, CP))
    kit.to_mesh_all()
    # krater tabanı: kaya blokları, kristal öbekleri, park etmiş minik araç, çadır, lambalar
    ROCK = UK._cached('gl_rock', lambda: UK.m_regolith('gl_rock', ('#6e6a80', '#928da4', '#bab5c8'), craters=0.6, dust=0.35, seed=2.0, scale=1.5))
    R = random.Random(8); bould = []
    for k in range(7):
        a = R.uniform(0, TAU); r = R.uniform(0.15, 0.5); x, y = math.cos(a) * r * CR_RX * 0.7, math.sin(a) * r * CR_RY * 0.7
        if abs(x) < 3.5: x += 6 * (1 if x >= 0 else -1)
        s = R.uniform(1.0, 2.6)
        bould.append(rock('cboulder', (s * 1.3, s, s * 0.8), (x, y, float(hfn(x, y))), ROCK, 700 + k, sub=4, rough=0.18))
    cl = []
    for i, (x, y, sc) in enumerate(((-4.0, 12.0, 1.6), (12.0, 3.0, 1.3), (-14.0, -5.0, 1.4), (5.0, -13.0, 1.1))):
        cl.append(crystal_cluster(x, y, float(hfn(x, y)), sc, 40 + i))
    import ay_donatim as AD
    rv_hi, _, _ = AD.build_rover()
    kit.to_mesh_all()
    rv = AD.group_transform(rv_hi, (-9.0, 6.0, float(hfn(-9.0, 6.0)) - 0.02), (0, 0, 35))
    tn = tent('tent', (8.0, -4.0, float(hfn(8.0, -4.0)) - 0.03), -25)
    lamps = []
    for (x, y) in ((6.0, -1.5), (-6.5, 3.5), (0.0, -9.0)):
        z = float(hfn(x, y))
        lamps.append([cyl('flpole', (x, y, z + 0.9), 0.05, 1.8, UK._cached('alu', lambda: UK.m_metal('alu', UK.ALU, dust=0.3)), verts=8, bevel=0.0)]
                     + UK.lamp('fllamp', (x, y, z + 1.8), 0.14, UK.SUN, cage=True, base_h=0.06))
    kit.to_mesh_all()
    hi += [o for g in groups for o in g] + bould + [o for c in cl for o in c] + rv + tn + [o for l in lamps for o in l]
    rocks_out, pebbles = scatter(hfn, 3, half, n_boulders=10, n_pebbles=200, avoid=[(c[0], c[1], c[2] * 1.1) for c in craters if c[2] > 1.5],
                                 ok_fn=lambda x, y: crater_rho(np.array(x), np.array(y)) > 1.06)
    hi += rocks_out + pebbles
    gi = 1
    def add_low(objs, table, g):
        return [tag_part(q, g) for q in EK.build_low2([o for o in objs if not o.name.startswith(('bolt', 'rivet', 'tie'))], table)]
    for i, g in enumerate(groups):
        lo += add_low(g, [(r'_leg$', 12), (r'_(br|ring)$', 8), (r'_(cap|head|foot)$', 16), (r'_lamp_bulb$', 24), (r'_lamp_base$', 12), (r'_lamp_cage$', 12)], 1 + i)
    lo += add_low(bould, [(r'.', 70)], 4)
    for i, c in enumerate(cl): lo += add_low(c, [(r'.', 26)], 5 + (i % 2))
    lo += add_low(rv, [(r'^cab$', 60), (r'^wheel$', 24), (r'.', 10)], 7)
    lo += add_low(tn, [(r'^tent$', 80), (r'.', 12)], 8)
    for l in lamps: lo += add_low(l, [(r'.', 16)], 8)
    for i, o in enumerate(rocks_out): lo += add_low([o], [(r'.', 90)], 9 + (i % 2))
    prep_uvs(lo, -half, half, um=U_BRIDGE)
    return hi, lo, dict(uv_fn=keep_uv, cull=False, tex=2048, ntex=1024, ao_dist=2.0, ao_strength=0.5, cage=0.35, ray=1.6,
                        draft=dict(yaw=-25, pitch=22, target=(0, 0, -8.0), dist=70))


BUILD['rs_crater_bridge'] = build_crater_bridge
