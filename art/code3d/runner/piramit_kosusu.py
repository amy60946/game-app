# Piramit Koşusu (koşu mini oyunu, Antik Mısır) — kodla 3B varlıklar (25 Ekim 2026). Ortak araçlar: runner/egypt_kit.py.
# Okti kumtaşı tapınak yolunda koşar (3 şerit: x = −2,2 / 0 / +2,2; yol üstü z = 0), alçak engelden zıplar, kirişin altından kayar,
# altın skarabe ve papirüs toplar. Oyunda RealAssets.EnvScaled(ad, …, 1f): 180° dönüşle Blender (x, y) → Unity (x, z); koşu yönü
# Unity +Z = Blender +Y. Yönlü varlıkların ÖNÜ Blender −Y'ye bakar (yaklaşan koşucuya). Yol/duvar parçası y −5..+5'te, uç uca döşenir.
# Kullanım (bpy ortamı):  /tmp/claude-0/bpyenv/bin/python -I piramit_kosusu.py -- <ad> [--draft <png>] [--preview <png>]
#   ad: rn_floor rn_wall rn_block rn_block2 rn_low rn_high rn_scarab rn_scroll rn_gate rn_pyramid rn_obelisk rn_palm rn_dune rn_sphinx
#   scene <png>   → yol kompozisyonu önizlemesi (dışa aktarılmış modellerle)
#   icons         → ui_scarab.png, ui_scroll.png (Resources/Icons, 256 px, saydam)
# Çıktı: Assets/_Pofi/Resources/Env/<ad>/<ad>.fbx + _basecolor.png + _normal.png; boylar: v6/measure_sizes.py -- <adlar>.
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep, blur, fnoise
import kit

SEG = 10.0                 # parça boyu (m)
ROAD = 3.7                 # yol yarı genişliği
LANES = (-2.2, 0.0, 2.2)


# ================================================================== ortak kum seti (yol kenarı = duvar dibi; döşemede eşleşir)

def h_edge(y):
    """x = ±3,7'de (yol ile duvarın birleştiği yer) kum yüksekliği; 10 m'de dönemli. Yol ve duvar aynı işlevi kullanır."""
    t = np.asarray(y) * TAU / SEG
    return 0.2 + 0.045 * np.sin(t + 0.6) + 0.03 * np.sin(2 * t + 2.2) + 0.015 * np.sin(5 * t + 0.4)


def drift(x, y):
    """Yol kenarı kum birikintisi (m): iç sınırı dalgalı (2,8–3,2 m), duvara doğru içbükey yükselir; iki yan farklı evrede."""
    x = np.asarray(x, np.float64); t = np.asarray(y) * TAU / SEG
    ph = np.where(x > 0, 1.3, 4.1)
    xs = 2.98 + 0.16 * np.sin(t + ph) + 0.07 * np.sin(3 * t + 2 * ph)
    u = np.clip((np.abs(x) - xs) / (ROAD - xs), 0, 1)
    return h_edge(y) * u ** 1.7


# ================================================================== rn_floor

def floor_layout(seed=11):
    """Taş yerleşimi: [(x0, x1, y0, y1, tür)] (y 10 m'de sarmalı). Şerit bölgeleri arasında dar ayırıcı taş, kenarda bordür."""
    R = random.Random(seed); S = []
    def rows(x0, x1, choices, kind, split=0.55, off=None):
        y = -5.0 + (off if off is not None else R.uniform(0, 1.2)); tot = 0.0; Ls = []
        while tot < SEG - 0.0001:
            L = R.choice(choices)
            if SEG - tot - L < min(choices) * 0.7: L = SEG - tot
            Ls.append(L); tot += L
        prev = 0.5
        for L in Ls:
            if kind == 'slab' and R.random() < split:
                f = 0.5 + (0.17 if prev < 0.5 else -0.17) + R.uniform(-0.06, 0.06); prev = f
                xm = x0 + (x1 - x0) * f
                S.append((x0, xm, y, y + L, kind)); S.append((xm, x1, y, y + L, kind))
            else:
                S.append((x0, x1, y, y + L, kind))
            y += L
    for (a, b) in ((-3.3, -1.16), (-1.04, 1.04), (1.16, 3.3)):
        rows(a, b, (0.85, 1.0, 1.15, 1.3, 1.45), 'slab')
    for c in (-1.1, 1.1):
        rows(c - 0.06, c + 0.06, (1.6, 1.9, 2.2, 2.5), 'sep')
    for s in (-1, 1):
        a, b = (3.3, 3.78) if s > 0 else (-3.78, -3.3)
        rows(a, b, (1.25,), 'kerb', off=R.uniform(0, 1.25))
    return S


def floor_maps(ppm=160, seed=11):
    """Yol haritaları (satır = y, sütun = x; y dönemli): yükseklik ayrıntısı (normal), kum maskesi, gölge çarpanı, üst boya."""
    from PIL import Image, ImageDraw
    R = random.Random(seed)
    nx, ny = int(round(2 * ROAD * ppm)), int(round(SEG * ppm))
    xs = (np.arange(nx) + 0.5) / ppm - ROAD; ys = (np.arange(ny) + 0.5) / ppm - SEG / 2
    X, Y = np.meshgrid(xs, ys)
    S = floor_layout(seed)
    ids = Image.new('I', (nx, ny), 0); di = ImageDraw.Draw(ids)
    J = 0.008
    def px(x, y): return ((x + ROAD) * ppm, (y + SEG / 2) * ppm)
    for i, (x0, x1, y0, y1, k) in enumerate(S):
        for sh in (-SEG, 0.0, SEG):
            a = px(x0 + J, y0 + J + sh); b = px(x1 - J, y1 - J + sh)
            di.rectangle([a, (b[0] - 1, b[1] - 1)], fill=i + 1)
    ID = np.asarray(ids, np.int64)
    inside = ID > 0
    n = len(S) + 1
    # taş başına özellik
    tint = np.ones((n, 3), np.float32); sink = np.zeros(n); tx = np.zeros(n); ty = np.zeros(n)
    cx = np.zeros(n); cy = np.zeros(n)
    tones = [(1.0, 1.0, 1.0), (1.08, 1.06, 1.02), (0.96, 0.9, 0.82), (1.03, 0.95, 0.86), (0.93, 0.91, 0.9), (1.07, 1.07, 1.05), (0.98, 0.88, 0.76)]
    lane_slabs = [i for i, s in enumerate(S) if s[4] == 'slab']
    sunk = set(R.sample(lane_slabs, 2)); cracked = set(R.sample([i for i in lane_slabs if i not in sunk], 5))
    for i, (x0, x1, y0, y1, k) in enumerate(S):
        j = i + 1; cx[j] = (x0 + x1) / 2; cy[j] = (y0 + y1) / 2
        t = np.array(R.choice(tones), np.float32) * R.uniform(0.94, 1.05)
        if k == 'sep': t = t * np.array((0.93, 0.83, 0.74), np.float32)
        if k == 'kerb': t = t * np.array((0.95, 0.9, 0.84), np.float32)
        tint[j] = t
        sink[j] = R.uniform(-0.003, 0.0); tx[j] = R.uniform(-0.002, 0.002); ty[j] = R.uniform(-0.002, 0.002)
        if i in sunk: sink[j] = -0.028; tx[j] = R.uniform(-0.012, 0.012); ty[j] = R.uniform(-0.012, 0.012)
    dY = (Y - cy[ID] + SEG / 2) % SEG - SEG / 2
    hs = sink[ID] + tx[ID] * (X - cx[ID]) + ty[ID] * dY
    # kenar pahı: derzden uzaklık (piksel, en çok N)
    N = 6; cur = inside.copy(); dist = np.zeros(inside.shape, np.float32)
    for _ in range(N):
        cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
        dist += cur
    bev = (1.0 - smoothstep(0.0, N, dist + 0.6)) ** 1.6
    h = np.where(inside, hs - 0.022 * bev, -0.022)
    # kırık köşe + çatlak
    chip = Image.new('L', (nx, ny), 0); dc = ImageDraw.Draw(chip)
    crack = Image.new('L', (nx, ny), 0); dk = ImageDraw.Draw(crack)
    for i, (x0, x1, y0, y1, k) in enumerate(S):
        for (xx, yy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            if R.random() < (0.28 if k != 'sep' else 0.12):
                r = R.uniform(0.03, 0.075); ox = xx + (r * 0.35 if xx == x0 else -r * 0.35); oy = yy + (r * 0.35 if yy == y0 else -r * 0.35)
                for sh in (-SEG, 0.0, SEG):
                    a = px(ox - r, oy - r + sh); b = px(ox + r, oy + r + sh); dc.ellipse([a, b], fill=255)
        if i in cracked:
            # kenardan kenara kırık çizgi + kısa dal
            if R.random() < 0.5: p0 = (x0 + 0.01, R.uniform(y0, y1)); p1 = (x1 - 0.01, R.uniform(y0, y1))
            else: p0 = (R.uniform(x0, x1), y0 + 0.01); p1 = (R.uniform(x0, x1), y1 - 0.01)
            pts = []
            for q in range(9):
                f = q / 8; pts.append((p0[0] + (p1[0] - p0[0]) * f + (R.uniform(-0.05, 0.05) if 0 < q < 8 else 0),
                                       p0[1] + (p1[1] - p0[1]) * f + (R.uniform(-0.05, 0.05) if 0 < q < 8 else 0)))
            br = pts[R.randint(2, 5)]; bp = [br, (br[0] + R.uniform(-0.25, 0.25), br[1] + R.uniform(-0.25, 0.25))]
            for sh in (-SEG, 0.0, SEG):
                dk.line([px(a, b + sh) for a, b in pts], fill=255, width=3); dk.line([px(a, b + sh) for a, b in bp], fill=200, width=2)
    CH = blur(np.asarray(chip, np.float32) / 255, 1.6, (True, False)) * inside
    CK = blur(np.asarray(crack, np.float32) / 255, 0.7, (True, False)) * inside
    h = h - 0.014 * smoothstep(0.2, 0.8, CH) - 0.01 * CK
    # gözenek + ince tane (normal için)
    sh_ = h.shape
    pits = fnoise(sh_, 0.012 * ppm, seed + 5, 2)
    h = h - 0.0022 * smoothstep(0.62, 0.78, pits) * inside
    h = h + 0.0012 * (fnoise(sh_, 0.05 * ppm, seed + 6, 3) - 0.5)
    # derzde kum dolgusu (çukurları doldurur)
    sfill = -0.013 + 0.004 * fnoise(sh_, 0.2 * ppm, seed + 7, 2)
    sandj = ((h < sfill) & ~inside).astype(np.float32)
    h = np.where(inside, h, np.maximum(h, sfill))
    # kum maskesi: kenar birikintisi + derz + çukur taş + savrulmuş kum lekeleri
    D = drift(X, Y)
    sm = smoothstep(0.002, 0.012, D)
    edge = smoothstep(1.8, 3.1, np.abs(X))
    patch = smoothstep(0.6, 0.76, fnoise(sh_, 0.7 * ppm, seed + 8, 3) + 0.25 * edge - 0.12) * (0.25 + 0.75 * edge)
    streak = blur(np.random.default_rng(seed + 9).random(sh_).astype(np.float32), (0.02 * ppm, 0.5 * ppm), (True, False))
    streak = smoothstep(0.515, 0.54, streak) * smoothstep(0.4, 0.6, fnoise(sh_, 1.5 * ppm, seed + 10, 2)) * (0.35 + 0.65 * edge)
    smask = np.clip(np.maximum.reduce([sm, sandj * 0.9, patch * 0.7, streak * 0.45]), 0, 1)
    low = smoothstep(-0.024, -0.034, hs) * inside * smoothstep(0.35, 0.6, fnoise(sh_, 0.3 * ppm, seed + 14, 3))
    smask = np.maximum(smask, low * 0.85)                                       # çukur taşın alçak köşesinde kum
    h = np.where(sm > 0.5, 0.0, h)                                              # birikinti altında taş ayrıntısı yok
    # gölge çarpanı: taş tonu, oyuk, şerit ortası aşınması (açık, pürüzsüz)
    sh3 = tint[ID] * inside[..., None] + (~inside)[..., None] * np.array((0.86, 0.8, 0.74), np.float32)
    cav = EK.cavity(h, ppm, 0.025, 55.0, (True, False))
    sh3 = sh3 * (1.0 - 0.4 * cav)[..., None]
    wear = sum(np.exp(-((X - c) / 0.42) ** 2) for c in LANES)
    sh3 = sh3 * (1.0 + 0.05 * wear)[..., None]
    sh3 = sh3 * (0.94 + 0.12 * fnoise(sh_, 0.35 * ppm, seed + 11, 3))[..., None]
    # üst boya: şerit ortasında soluk kakma çizgi (kireçtaşı, yer yer turkuaz iz), çatlak koyusu
    over = np.zeros(sh_ + (4,), np.float32)
    line = sum(smoothstep(0.026, 0.016, np.abs(X - c)) for c in LANES)
    gap = smoothstep(0.3, 0.42, fnoise(sh_, 0.45 * ppm, seed + 12, 3))
    la = line * gap * inside * 0.3 * (1 - smask)
    tq = smoothstep(0.55, 0.7, fnoise(sh_, 0.12 * ppm, seed + 13, 3))
    lc = EK.lin('#e8cf9e') * (1 - tq[..., None] * 0.55) + EK.lin('#5aa99c') * tq[..., None] * 0.55
    ck = smoothstep(0.15, 0.6, CK) * 0.6
    over[..., :3] = np.where((ck > la)[..., None], EK.lin('#5a3b24'), lc); over[..., 3] = np.maximum(la, ck)
    h = h - 0.0015 * line * gap * inside                                        # kakma hafif gömük
    nrm = EK.normal_from_height(h, ppm, (True, False))
    return dict(h=h, sand=smask, shade=sh3.astype(np.float32), over=over, nrm=nrm, ppm=ppm, X=X, Y=Y)


def build_floor():
    M = floor_maps()
    dec = EK.Decal('floor', over=M['over'], shade=M['shade'], normal=M['nrm'], sandmask=M['sand'], ext='REPEAT')
    mat = EK.m_stone('floorstone', EK.SLAB, period=SEG, dec=dec, bands=0, dust=0, grime=0, wear=0, cav=0, pits=0.45, bump=0.12)
    # taslak: 5 cm ızgara, y −6,5..6,5 (uçlarda AO komşuyu görür), kenar kum birikintisi gerçek yükseklik
    xs = np.linspace(-ROAD, ROAD, 149); ys = np.linspace(-6.5, 6.5, 261)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X, Y, drift(X, Y)], -1)
    UV = np.stack([(X + ROAD) / (2 * ROAD), (Y + SEG / 2) / SEG], -1)
    hi = EK.grid_obj('floor_hi', P, UV, [mat])
    # AO için duvar gölgeleyicileri (seçilmez, dışa aktarılmaz)
    occ = []
    for s in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(s * 4.55, 0, 1.6)); o = bpy.context.object; o.scale = (1.3, 16, 3.2); o.name = 'occ'
        occ.append(o)
    # hedef: kenarlarda 15 × 25 cm, ortada geniş dörtgenler; üst z = 0 (birikinti dışında)
    xl = [-3.7, -3.55, -3.4, -3.25, -3.1, -2.95, -2.8, -2.65, -1.1, 0.0, 1.1, 2.65, 2.8, 2.95, 3.1, 3.25, 3.4, 3.55, 3.7]
    yl = np.linspace(-5, 5, 41)
    XL, YL = np.meshgrid(np.array(xl), yl)
    PL = np.stack([XL, YL, drift(XL, YL)], -1)
    lo = EK.grid_obj('floor_lo', PL, None, [])
    return [hi], [lo], dict(uv_fn=planar_uv(-ROAD, ROAD, -SEG / 2, SEG / 2), cull=False, ao_dist=0.6, ao_strength=0.55, tex=1024)


def planar_uv(x0, x1, y0, y1):
    def f(L):
        me = L.data
        for l in list(me.uv_layers): me.uv_layers.remove(l)
        uv = me.uv_layers.new(name='UVMap'); me.uv_layers.active = uv
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
        u = (co[vi, 0] - x0) / (x1 - x0); v = (co[vi, 1] - y0) / (y1 - y0)
        uv.data.foreach_set('uv', np.stack([u, v], -1).reshape(-1).astype(np.float32))
    return f


# ================================================================== rn_wall (sağ duvar; sol = aynı model, x ölçeği −1)

def wall_profile(step=0.02):
    """Sağ duvarın kesiti (x, z), önü −x: kaide (kumun altına iner), eğimli yüz, yuvarlak silme (torus), içbükey Mısır saçağı
    (cavetto), üst şerit, düz tepe. Döner: noktalar (n, 2), yay uzunluğu s, adlı noktaların s değeri."""
    pts = []; key = {}
    def add(p, name=None):
        if name: key[name] = len(pts) if not pts or (abs(pts[-1][0] - p[0]) + abs(pts[-1][1] - p[1])) > 1e-9 else len(pts) - 1
        if pts and (abs(pts[-1][0] - p[0]) + abs(pts[-1][1] - p[1])) < 1e-9: return
        pts.append(p)
    def line(a, b, name=None):
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        for i in range(n + 1): add((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n), name if i == n else None)
    def arc(cx, cz, rx, rz, a0, a1, name=None):
        n = max(3, int(math.ceil(abs(math.radians(a1 - a0)) * max(rx, rz) / step)))
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n); add((cx + rx * math.cos(a), cz + rz * math.sin(a)), name if i == n else None)
    add((3.86, -0.15), 'A'); line((3.86, -0.15), (3.86, 0.32), 'B'); line((3.86, 0.32), (3.9, 0.36), 'C'); line((3.9, 0.36), (3.97, 0.36), 'D')
    line((3.97, 0.36), (4.06, 2.5), 'E'); arc(4.06, 2.59, 0.09, 0.09, 270, 90, 'F'); line((4.06, 2.68), (4.06, 2.72), 'G')
    arc(3.76, 2.72, 0.3, 0.38, 0, 90, 'H'); line((3.76, 3.1), (3.74, 3.1), 'I'); line((3.74, 3.1), (3.74, 3.22), 'J')
    line((3.74, 3.22), (5.2, 3.22), 'K')
    P = np.array(pts, np.float64); s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    return P, s, {k: s[i] for k, i in key.items()}


WALL_SPARSE = [(3.86, 0.08), (3.86, 0.32), (3.9, 0.36), (3.97, 0.36), (4.06, 2.5)] + \
    [(4.06 + 0.09 * math.cos(math.radians(a)), 2.59 + 0.09 * math.sin(math.radians(a))) for a in (225, 180, 135, 90)] + \
    [(3.76 + 0.3 * math.cos(math.radians(a)), 2.72 + 0.38 * math.sin(math.radians(a))) for a in (0, 22.5, 45, 67.5, 90)] + \
    [(3.74, 3.1), (3.74, 3.22), (5.2, 3.22)]
COL_X = 3.82             # sütun ekseni (y = 0)


def wall_maps(ppm=200, seed=21):
    """Duvar yüzü haritası: u = y (−5..5, sarmalı), v = kesit yay uzunluğu s. Taş sıraları (blok tonu + derz), kabartmalar, boya."""
    from PIL import Image, ImageDraw
    R = random.Random(seed)
    P, s, K = wall_profile(0.01); S = float(s[-1])
    cv = EK.Canvas(SEG, S, ppm, wrap_u=True, u0=-SEG / 2, v0=0.0)
    def sz(z): return K['D'] + (z - 0.36) / (2.5 - 0.36) * (K['E'] - K['D'])
    W, H = cv.W, cv.H
    # --- taş blokları (kimlik haritası → ton) + derzler
    ids = Image.new('I', (W, H), 0); di = ImageDraw.Draw(ids); blocks = []
    def px(u, v): return ((u + SEG / 2) * ppm, v * ppm)
    def block_row(v0, v1, lens, off):
        u = -SEG / 2 + off; tot = 0.0; Ls = []
        while tot < SEG - 1e-6:
            L = R.choice(lens)
            if SEG - tot - L < min(lens) * 0.7: L = SEG - tot
            Ls.append(L); tot += L
        for L in Ls:
            blocks.append((u, u + L, v0, v1))
            for sh in (-SEG, 0.0, SEG):
                a = px(u + sh, v0); b = px(u + L + sh, v1); di.rectangle([a, (b[0] - 1, b[1] - 1)], fill=len(blocks))
            if abs(u) > 0.35 or True: cv.line([(u, v0), (u, v1)], 0.012)
            u += L
        cv.line([(-SEG / 2 - 1, v1), (SEG / 2 + 1, v1)], 0.012)
    block_row(0.0, K['B'] + 0.02, (1.25,), 0.4)
    courses = [0.36, 0.79, 1.22, 1.65, 2.08, 2.5]
    for i in range(len(courses) - 1):
        block_row(sz(courses[i]), sz(courses[i + 1]), (0.95, 1.1, 1.3, 1.5), R.uniform(0, 0.9))
    block_row(K['E'], K['G'], (1.25, 1.6), 0.2)
    block_row(K['G'], K['J'], (1.25, 1.6), 0.7)
    block_row(K['J'], S, (1.0, 1.25), 0.1)
    BID = np.asarray(ids, np.int64)
    tints = np.ones((len(blocks) + 1, 3), np.float32)
    tones = [(1.0, 1.0, 1.0), (1.06, 1.04, 1.0), (0.96, 0.91, 0.84), (1.03, 0.96, 0.88), (0.95, 0.93, 0.92), (0.99, 0.9, 0.8)]
    for i in range(1, len(blocks) + 1): tints[i] = np.array(R.choice(tones), np.float32) * R.uniform(0.95, 1.05)
    # --- boya: kaide üstü bant (kiremit, aşı, mavi), yazmaç çizgileri
    for (z0, z1, c) in ((0.41, 0.47, EK.TERRA), (0.485, 0.535, EK.OCHRE), (0.55, 0.61, EK.BLUE)):
        cv.rect(-SEG / 2 - 1, sz(z0), SEG / 2 + 1, sz(z1), carve=False, col=EK.C(c))
    for z in (0.68, 1.5, 2.27):
        cv.rect(-SEG / 2 - 1, sz(z - 0.016), SEG / 2 + 1, sz(z + 0.016), carve=True, col=EK.C(EK.LAPIS), val=110)
    # --- dikiş ve sütun yanında dikey kenar bantları (renkli dikdörtgen dizisi)
    cols4 = [EK.BLUE, EK.TERRA, EK.GREEN, EK.OCHRE]
    def border(u0, u1):
        z = 0.7; k = 0
        while z < 2.2:
            z1 = min(z + 0.13, 2.25)
            cv.rect(u0 + 0.012, sz(z + 0.012), u1 - 0.012, sz(z1 - 0.012), carve=True, col=EK.C(cols4[k % 4]), val=150); z = z1; k += 1
    border(4.89, 5.11)
    for sgn in (-1, 1): border(sgn * 0.58 if sgn > 0 else -0.78, 0.78 if sgn > 0 else -0.58)
    # --- alt yazmaç: Nil sahnesi (su, balık, papirüs, nilüfer, ördek)
    for (a, b) in ((-4.86, -0.8), (0.8, 4.86)):
        cv.rect(a, sz(0.71), b, sz(0.84), carve=False, col=EK.C('#3d86c4'))
        n = int((b - a) / 0.16)
        for r_, zz in enumerate((0.745, 0.8)):
            pts = [(a + i * (b - a) / n, sz(zz + (0.018 if (i + r_) % 2 else -0.018))) for i in range(n + 1)]
            cv.line(pts, 0.018, col=EK.C('#8fd3e6'))
        x = a + 0.15
        while x < b - 0.2:
            kind = R.random()
            if kind < 0.42:
                hgt = R.uniform(0.42, 0.6); EK.g_papyrus(EK.Pen(cv, x - 0.09, sz(0.84), 0.18, sz(0.84 + hgt) - sz(0.84)), c1=EK.GREEN, c2=R.choice((EK.TURQ, EK.GREEN)))
                x += R.uniform(0.17, 0.26)
            elif kind < 0.66:
                hgt = R.uniform(0.3, 0.45); EK.g_lotus(EK.Pen(cv, x - 0.1, sz(0.84), 0.2, sz(0.84 + hgt) - sz(0.84)))
                x += R.uniform(0.2, 0.28)
            elif kind < 0.84:
                zf = R.uniform(1.12, 1.3); EK.g_duck(EK.Pen(cv, x - 0.14, sz(zf), 0.28, sz(zf + 0.17) - sz(zf), flip=R.random() < 0.5))
                x += 0.34
            else:
                EK.g_fish(EK.Pen(cv, x - 0.12, sz(0.735), 0.24, sz(0.83) - sz(0.735), flip=R.random() < 0.5), c1=EK.CREAM, c2=EK.TURQ)
                x += 0.3
    # --- üst yazmaç: simge dizisi
    seqs = (['duck', 'sun', 'eye', 'lotus', 'cat', 'scarab'], ['ibis', 'star', 'fish', 'feather', 'boat', 'palm'])
    for (a, b), seq in zip(((-4.86, -0.8), (0.8, 4.86)), seqs):
        n = len(seq); step = (b - a) / n
        for i, g in enumerate(seq):
            w = 0.5 if g not in ('boat', 'feather') else (0.56 if g == 'boat' else 0.3)
            u = a + step * (i + 0.5) - w / 2
            EK.GLYPHS[g](EK.Pen(cv, u, sz(1.63), w, sz(2.16) - sz(1.63), flip=(i % 2 == 1 and g in ('duck', 'ibis', 'cat', 'fish'))))
    # --- frizde nilüfer + tomurcuk (0,2 m'de bir)
    for i in range(50):
        u = -SEG / 2 + i * 0.2 + 0.1; z0 = 2.31; z1 = 2.47
        if i % 2 == 0:
            p = EK.Pen(cv, u - 0.07, sz(z0), 0.14, sz(z1) - sz(z0))
            p.poly([(0.5, 0.0), (0.38, 0.35), (0.5, 1.0), (0.62, 0.35)], EK.C(EK.BLUE))
            p.poly([(0.45, 0.1), (0.0, 0.55), (0.05, 0.95), (0.35, 0.5)], EK.C(EK.TURQ)); p.poly([(0.55, 0.1), (1.0, 0.55), (0.95, 0.95), (0.65, 0.5)], EK.C(EK.TURQ))
        else:
            p = EK.Pen(cv, u - 0.04, sz(z0), 0.08, sz(z1) - sz(z0))
            p.line([(0.5, 0.0), (0.5, 0.5)], 0.25, EK.C(EK.GREEN), layer='carve'); p.ell(0.5, 0.62, 0.42, 0.26, EK.C(EK.GREEN))
            p.circle(0.5, 0.95, 0.12, EK.C(EK.TERRA))
    # --- silme (torus): çapraz bağ şeritleri; saçak (cavetto): dikey yaprak çubukları
    for i in range(80):
        u = -SEG / 2 + i * 0.125; c = EK.TERRA if i % 2 == 0 else EK.BLUE
        cv.poly([(u, K['E']), (u + 0.06, K['E']), (u + 0.12, K['F']), (u + 0.06, K['F'])], carve=False, col=EK.C(c))
    lc = [EK.BLUE, EK.GREEN, EK.TERRA, EK.GREEN]
    for i in range(80):
        u = -SEG / 2 + i * 0.125 + 0.02; c = lc[i % 4]
        p = EK.Pen(cv, u, K['G'] + 0.02, 0.085, K['I'] - K['G'] - 0.04)
        p.poly([(0, 0)] + EK.arcpts(0.5, 0.86, 0.5, 0.14, 180, 0, 8)[::-1][::-1] + [(1, 0)], EK.C(c), val=140)
    cv.rect(-SEG / 2 - 1, K['I'] + 0.015, SEG / 2 + 1, K['J'] - 0.015, carve=False, col=EK.C(EK.OCHRE))
    # --- aşınma: derz kesişimlerinde kırık, saçak ağzında dökülme
    for (u0, u1, v0, v1) in blocks:
        for (uu, vv) in ((u0, v0), (u0, v1)):
            if R.random() < 0.18:     # derz köşesinde düzensiz kırık (yuvarlak delik gibi görünmesin)
                r = R.uniform(0.03, 0.07); cu, cv_ = uu + R.uniform(-0.015, 0.015), vv + R.uniform(-0.015, 0.015)
                pts = [(cu + r * R.uniform(0.4, 1.0) * math.cos(a), cv_ + r * R.uniform(0.3, 0.8) * math.sin(a)) for a in np.linspace(0, TAU, 8, endpoint=False)]
                cv.poly(pts, layer='carve', val=150)
    h, over, shade = EK.finish_relief(cv, depth=0.012, groove=0.005, bevel=0.005, fade=0.35, chips=0.35, seed=seed, wrap=(False, True))
    V_ = (np.arange(H) + 0.5) / ppm
    vfade = np.ones(H, np.float32)
    vfade *= 1.0 - 0.35 * smoothstep(K['G'], K['J'], V_)            # saçak: güneşte daha çok solmuş
    vfade *= smoothstep(sz(0.3), sz(0.5), V_) * 0.5 + 0.5 * (V_ > sz(0.3))
    over[..., 3] *= vfade[:, None]
    shade *= tints[BID]
    shade *= (0.95 + 0.1 * fnoise((H, W), 0.4 * ppm, seed + 30, 3))[..., None]
    nrm = EK.normal_from_height(h, ppm, (False, True))
    return dict(over=over, shade=shade, nrm=nrm, S=S, K=K, P=P, s=s)


def col_radius(th, z):
    """Sütun yarıçapı (θ, z): gömülü kaide diski, şişkin ayak, 8 dilimli demet gövde (papirüs sapları), bilezikler, nilüfer çanağı."""
    th = np.asarray(th); z = np.asarray(z, np.float64)
    lobe = np.abs(np.cos(4 * th)) ** 0.6 - 0.62
    foot = 0.2 + 0.055 * np.sin(np.clip((z - 0.12) / 0.5, 0, 1) * math.pi * 0.5)
    shaft = np.where(z < 0.37, foot, 0.255 - 0.02 * (z - 0.37) / 1.58)
    r = np.where(z < 1.95, shaft * (1 + 0.075 * lobe), 0.0)
    ring = 0.245 + 0.008 * np.cos(np.clip(z - 1.95, 0, 0.17) / 0.034 * math.pi * 2)
    r = np.where((z >= 1.95) & (z < 2.12), ring, r)
    t = np.clip((z - 2.12) / 0.48, 0, 1)
    bell = 0.235 + 0.215 * t ** 1.5
    pet = 0.035 * t ** 2 * (np.abs(np.cos(4 * th)) ** 3) + 0.012 * t ** 2 * np.abs(np.cos(8 * th))
    r = np.where(z >= 2.12, bell + pet, r)
    base = np.where(z < 0.12, 0.33 - 0.04 * np.clip((z - 0.06) / 0.06, 0, 1) ** 2, 0)
    return np.where(z < 0.12, base, r)


def column_maps(ppm_v=300, nu=512, seed=31):
    """Sütun haritası: u = θ/2π (ön θ = π → u 0,5), v = z/2,6. Ayakta yaprak üçgenleri, gövde önünde küçük simge sütunu, bilezik
    boyaları, çanakta büyük/küçük nilüfer yaprakları."""
    Hm = 2.6; R = random.Random(seed)
    circ = TAU * 0.25
    cv = EK.Canvas(circ, Hm * (ppm_v / (nu / circ)), nu / circ, wrap_u=True)   # v ekseni ppm_v ile örneklenir
    kz = ppm_v / (nu / circ)
    def Z(z): return z * kz
    du = circ / 8
    for k in range(8):
        u = k * du
        p = EK.Pen(cv, u - du * 0.42, Z(0.12), du * 0.84, Z(0.42) - Z(0.12))
        p.poly([(0, 0), (0.5, 1.0), (1, 0)], EK.C(EK.GREEN)); p.poly([(0.25, 0.0), (0.5, 0.6), (0.75, 0.0)], EK.C(EK.TURQ), layer='raise')
    for i, c in enumerate((EK.BLUE, EK.OCHRE, EK.TERRA, EK.OCHRE, EK.BLUE)):
        z0 = 1.95 + i * 0.034
        cv.rect(-1, Z(z0 + 0.004), circ + 1, Z(z0 + 0.03), carve=False, col=EK.C(c))
        cv.line([(-1, Z(z0)), (circ + 1, Z(z0))], 0.006)
    front = circ * 0.5
    for j, g in enumerate(('sun', 'duck', 'star', 'eye')):
        z0 = 1.25 + j * 0.16
        EK.GLYPHS[g](EK.Pen(cv, front - 0.07, Z(z0), 0.14, Z(z0 + 0.13) - Z(z0)))
    cv.line([(front - 0.085, Z(1.22)), (front - 0.085, Z(1.88))], 0.008); cv.line([(front + 0.085, Z(1.22)), (front + 0.085, Z(1.88))], 0.008)
    for k in range(8):
        u = k * du
        p = EK.Pen(cv, u - du * 0.5, Z(2.12), du, Z(2.6) - Z(2.12))
        p.poly([(0.5, 0.0), (0.22, 0.35), (0.15, 0.6), (0.3, 0.85), (0.5, 1.0), (0.7, 0.85), (0.85, 0.6), (0.78, 0.35)], EK.C(EK.BLUE))
        p.poly([(0.5, 0.15), (0.34, 0.55), (0.5, 0.85), (0.66, 0.55)], EK.C(EK.TURQ), layer='raise')
        p.line([(0.5, 0.0), (0.22, 0.35), (0.15, 0.6), (0.3, 0.85), (0.5, 1.0), (0.7, 0.85), (0.85, 0.6), (0.78, 0.35), (0.5, 0.0)], 0.03, EK.C(EK.GOLD))
        q = EK.Pen(cv, u + du * 0.5 - du * 0.3, Z(2.18), du * 0.6, Z(2.52) - Z(2.18))
        q.poly([(0.5, 0.0), (0.15, 0.5), (0.5, 1.0), (0.85, 0.5)], EK.C(EK.GREEN))
    h, over, shade = EK.finish_relief(cv, depth=0.008, groove=0.004, bevel=0.004, fade=0.3, chips=0.3, seed=seed, wrap=(False, True))
    nrm = EK.normal_from_height(h, cv.ppm, (False, True))
    return dict(over=over, shade=shade, nrm=nrm, kz=kz, Hm=Hm)


def wall_sand(x, y):
    """Duvar dibindeki kum: x = 3,7'de yoldaki birikintiyle aynı (h_edge), kaideye doğru kabarır, sütun dibinde öbek; x < 3,7'de yolun
    altına iner (birleşim görünmez)."""
    x = np.asarray(x); y = np.asarray(y)
    e = h_edge(y)
    up = 0.13 * smoothstep(3.7, 3.86, x) + 0.09 * np.exp(-(y / 0.55) ** 2) * smoothstep(3.6, 3.75, x)
    return np.where(x < 3.7, e - 0.6 * (3.7 - x), e + up)


def build_wall():
    M = wall_maps(); C_ = column_maps()
    dec = EK.Decal('wall', over=M['over'], shade=M['shade'], normal=M['nrm'], ext='REPEAT')
    ST = EK.m_stone('wallstone', EK.SANDSTONE, period=SEG, dec=dec, bands=0.6, dust=0.4, grime=0.35, wear=0.5, cav=0.35, pits=0.6, bump=0.18)
    decc = EK.Decal('col', over=C_['over'], shade=C_['shade'], normal=C_['nrm'], ext='REPEAT')
    CS = EK.m_stone('colstone', EK.SANDSTONE, period=SEG, dec=decc, bands=0.4, dust=0.4, grime=0.35, wear=0.5, cav=0.35, pits=0.5, bump=0.15)
    SD = EK.m_sand('wallsand', period=SEG)
    P, s, K = M['P'], M['s'], M['K']; S = M['S']
    ys = np.linspace(-6.5, 6.5, 261)
    PP = np.zeros((len(P), len(ys), 3)); UV = np.zeros((len(P), len(ys), 2))
    PP[..., 0] = P[:, 0:1]; PP[..., 1] = ys[None, :]; PP[..., 2] = P[:, 1:2]
    UV[..., 0] = (ys[None, :] + SEG / 2) / SEG; UV[..., 1] = s[:, None] / S
    hi = [EK.grid_obj('wall_hi', PP, UV, [ST], flip=True)]
    # sütun (taslak): θ 0..2π, z 0..2,6
    th = np.linspace(0, TAU, 257); zz = np.concatenate([np.linspace(0, 0.12, 13), np.linspace(0.125, 2.6, 496)])
    TH, ZZ = np.meshgrid(th, zz); RR = col_radius(TH, ZZ)
    PC = np.stack([COL_X + RR * np.cos(TH), RR * np.sin(TH), ZZ], -1)
    UVC = np.stack([TH / TAU, ZZ * C_['kz'] / (C_['Hm'] * C_['kz'])], -1)
    hi.append(EK.grid_obj('column_hi', PC, UVC, [CS]))
    ab = EK.rounded_box('abacus', (0.56, 0.56, 0.15), 0.025, 0.02, [EK.m_stone('abstone', EK.SANDSTONE, period=SEG, bands=0.3)], loc=(COL_X, 0, 2.675), chips=0.012, seed=3)
    hi.append(ab)
    # kum
    xs = np.linspace(3.6, 3.95, 15); X, Y = np.meshgrid(xs, ys)
    hi.append(EK.grid_obj('wsand_hi', np.stack([X, Y, wall_sand(X, Y)], -1), None, [SD]))
    # moloz: iki kırık taş parçası (dikişten uzak)
    for (x, y, sz_, sd) in ((3.78, -2.7, 0.2, 5), (3.8, 3.4, 0.16, 6)):
        hz = float(wall_sand(np.array(x), np.array(y)))
        hi.append(EK.rounded_box('rubble', (sz_ * 1.4, sz_, sz_ * 0.8), sz_ * 0.18, 0.02, [EK.m_stone('rubstone', EK.SANDSTONE, bands=0.3)],
                                 loc=(x, y, hz - 0.02), rot=(8, -6, 30 * sd), chips=0.02, lump=0.006, seed=sd))
    # AO gölgeleyici: yol zemini (seçilmez)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.0)); g = bpy.context.object; g.scale = (7.4, 16, 1); g.name = 'occ'
    # --- hedef
    lo = []
    WS = np.array(WALL_SPARSE)
    for k in range(4):
        y0, y1 = -5 + 2.5 * k, -2.5 + 2.5 * k
        for part, w in ((WS[:-1], 1.0), (WS[-2:], 0.25)):          # yüz + saçak | düz tepe (az görünür: az doku)
            Pk = np.zeros((len(part), 2, 3)); Pk[..., 0] = part[:, 0:1]; Pk[..., 2] = part[:, 1:2]; Pk[:, 0, 1] = y0; Pk[:, 1, 1] = y1
            o = EK.grid_obj('wall_lo', Pk, None, [], flip=True); EK.tag_uvw(o, w); lo.append(o)
    yl = np.linspace(-5, 5, 41); xs = np.array([3.62, 3.68, 3.74, 3.8, 3.88]); X, Y = np.meshgrid(xs, yl)
    lo.append(EK.tag_uvw(EK.grid_obj('wsand_lo', np.stack([X, Y, wall_sand(X, Y)], -1), None, []), 0.6))
    zl = [0, 0.06, 0.12, 0.13, 0.25, 0.37, 0.9, 1.45, 1.95, 2.12, 2.3, 2.45, 2.55, 2.6]
    thl = np.linspace(0, TAU, 17); TH, ZZ = np.meshgrid(thl, np.array(zl))
    RL = col_radius(TH, ZZ); RL = np.where(ZZ < 1.95, np.where(ZZ < 0.12, RL, RL * 0.985), RL)
    RL = np.where((ZZ >= 1.95) & (ZZ < 2.12), 0.246, RL)
    RL[ZZ >= 2.12] = (0.235 + 0.215 * np.clip((ZZ[ZZ >= 2.12] - 2.12) / 0.48, 0, 1) ** 1.5) + 0.012
    PC = np.stack([COL_X + RL * np.cos(TH), RL * np.sin(TH), ZZ], -1)
    co = EK.grid_obj('column_lo', PC, None, []); EK.weld(co); lo.append(EK.tag_uvw(co, 1.3))
    lo += [EK.tag_uvw(o, 0.9) for o in EK.BK.build_low([ab], [(r'abacus', 0.012)])]
    lo += [EK.tag_uvw(o, 0.6) for o in EK.BK.build_low([o for o in hi if o.name.startswith('rubble')], [(r'rubble', 0.05)])]
    return hi, lo, dict(cull=True, ao_dist=0.6, ao_strength=0.55, tex=1024,
                        draft=dict(yaw=-62, pitch=12, target=(3.9, 0, 1.4), dist=8))


# ================================================================== çalıştırma

def bake_custom(name, high, low, uv_fn=None, cull=False, tex=1024, ao_dist=0.5, ao_strength=0.55, cage=0.03, ray=0.12, **kw):
    """Elle kurulmuş hedefle pişirme (döşenen parçalar: kenar köşeleri iki uçta birebir)."""
    tex = int(os.environ.get('POFI_TEX', '0') or 0) or tex
    t = EK.PB.export_proxy(EK.out_dir(name), high, low, target=None, size=tex, nsize=tex, cage=cage, ray=ray, cull_hidden=cull,
                           uv_fn=uv_fn, uv_weight=None if uv_fn else 'uvw', dilate=16, ao_dist=ao_dist, ao_strength=ao_strength, **kw)
    print(name, 'üçgen', t, flush=True)
    return t


BUILD = {'rn_floor': build_floor, 'rn_wall': build_wall}
try:
    import kosu_engeller; BUILD.update(kosu_engeller.BUILD)
except ImportError: pass
try:
    import kosu_arka; BUILD.update(kosu_arka.BUILD)
except ImportError: pass


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    name = args[0]
    kit.reset()
    if name == 'scene':
        import kosu_sahne; kosu_sahne.render(args[1]); return
    if name == 'icons':
        import kosu_sahne; kosu_sahne.icons(); return
    hi, lo, opt = BUILD[name]()
    kit.to_mesh_all()                     # eğri (tüp) parçalar ağa
    if '--draft' in args:
        EK.draft(args[args.index('--draft') + 1], **opt.get('draft', {})); return
    opt.pop('draft', None)
    if lo is None:
        EK.bake_auto(name, hi, **opt)
    else:
        bake_custom(name, hi, lo, **opt)
    if '--preview' in args:
        EK.preview(name, args[args.index('--preview') + 1])


if __name__ == '__main__':
    main()
