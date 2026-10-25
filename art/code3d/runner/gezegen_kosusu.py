# Gezegen Koşusu (koşu mini oyunu, Ay yüzeyi) — kodla 3B varlıklar (25 Ekim 2026; kullanıcı kararı: koşu uzay/gezegen temasıyla başlar,
# Mısır seti rn_* ileride ayrı dünya olarak depoda kalır). Okti Ay'daki neşeli bir yürüyüş yolunda kaçan kuyruklu yıldızı kovalar:
# 3 şerit (x = −2,2 / 0 / +2,2; yol üstü z = 0), alçak engelden zıplar, kirişin altından kayar, kristal ve gezegen kartı toplar.
# Oyunda RealAssets.EnvScaled(ad, …, 1f): 180° dönüşle Blender (x, y) → Unity (x, z); koşu yönü Unity +Z = Blender +Y. Yönlü varlıkların
# ÖNÜ Blender −Y'ye bakar (yaklaşan koşucuya). Yol/duvar parçası y −5..+5, uç uca döşenir (renk, AO, normal iki uçta aynı).
# Ayrıntı yoğunluğu ada yapıları gibi (bld/*.py): cıvata, perçin, panel dikişi, kablo, lamba, çıkartma, dökülmüş boya, oyukta toz.
# Kullanım (bpy ortamı):  /tmp/claude-0/bpyenv/bin/python -I gezegen_kosusu.py -- <ad> [--draft <png>] [--preview <png>]
#   ad: rs_floor rs_wall rs_block rs_block2 rs_low rs_high rs_crystal rs_card rs_comet rs_gate
#       rs_planet rs_earth rs_dome rs_rocket rs_dish rs_crater rs_hills
#   scene <png>  → yol kompozisyonu önizlemesi · icons → Resources/Icons/ui_crystal.png, ui_card.png
# Çıktı: Assets/_Pofi/Resources/Env/<ad>/<ad>.fbx + _basecolor.png + _normal.png; boylar: v6/measure_sizes.py -- <adlar>.
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
import uzay_kit as UK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep, blur, fnoise
import kit

SEG = 10.0
ROAD = 3.7
TRIM = 3.3                 # bordür iç kenarı
LANES = (-2.2, 0.0, 2.2)
STRIPS = (-1.1, 1.1)


# ================================================================== ortak: yol kenarı / duvar dibi toz yüksekliği

def dust_edge(y):
    """x = ±3,7'de (yol bordürünün dış ucu = duvar dibi) toz yüksekliği; 10 m'de dönemli; yol ve duvar aynı işlevi kullanır."""
    t = np.asarray(y) * TAU / SEG
    return 0.045 + 0.02 * np.sin(t + 0.9) + 0.012 * np.sin(3 * t + 2.0)


def trim_z(ax):
    """Bordür kesiti (|x| → z): 3,30'da 0'dan yuvarlak yükselir, 0,11 m düz tepe, 3,70'te 0,03'e iner."""
    ax = np.asarray(ax, np.float64)
    up = 0.1 * np.sin(np.clip((ax - TRIM) / 0.045, 0, 1) * math.pi / 2) ** 0.7
    top = up + 0.01 * np.sin(np.clip((ax - 3.345) / 0.31, 0, 1) * math.pi)
    down = np.where(ax > 3.66, (0.11 - 0.08 * np.sin(np.clip((ax - 3.66) / 0.04, 0, 1) * math.pi / 2)), top)
    return np.where(ax <= TRIM, 0.0, np.where(ax > 3.66, down, top))


def drift(x, y):
    """Bordürün iç dibine yığılan Ay tozu (iki yanda farklı evre); bordür dışında (3,66–3,7) duvara doğru ince örtü."""
    x = np.asarray(x, np.float64); t = np.asarray(y) * TAU / SEG; ax = np.abs(x)
    ph = np.where(x > 0, 0.4, 3.0)
    amp = 0.045 + 0.02 * np.sin(t + ph) + 0.012 * np.sin(4 * t + 2 * ph)
    w = 0.26 + 0.08 * np.sin(2 * t + ph)
    inner = amp * smoothstep(TRIM - w, TRIM, ax) * (ax <= TRIM + 0.03)
    outer = dust_edge(y) * smoothstep(3.6, 3.7, ax)
    return inner + outer


def floor_z(x, y):
    return np.maximum(trim_z(np.abs(x)), drift(x, y)) if True else 0


# ================================================================== rs_floor

def floor_layout(seed=5):
    """Plaka yerleşimi: her şerit bölgesinde tek sütun plaka, 1,25 m (şeritler arası kaydırmalı); tür: tırtıklı / düz / ızgara / kapak."""
    R = random.Random(seed); S = []
    zones = ((-TRIM, -1.18), (-1.02, 1.02), (1.18, TRIM))
    for zi, (a, b) in enumerate(zones):
        off = (0.0, 0.42, 0.83)[zi]
        for k in range(8):
            y0 = -SEG / 2 + off + k * 1.25
            r = R.random()
            kind = 'tread' if r < 0.5 else 'plain' if r < 0.78 else 'vent' if r < 0.9 else 'hatch'
            S.append(dict(x0=a, x1=b, y0=y0, y1=y0 + 1.25, kind=kind, sticker=(kind == 'plain' and R.random() < 0.55), seed=R.randint(0, 9999)))
    return S


def floor_maps(ppm=160, seed=5):
    from PIL import Image, ImageDraw
    R = random.Random(seed)
    nx, ny = int(round(2 * ROAD * ppm)), int(round(SEG * ppm))
    xs = (np.arange(nx) + 0.5) / ppm - ROAD; ys = (np.arange(ny) + 0.5) / ppm - SEG / 2
    X, Y = np.meshgrid(xs, ys); AX = np.abs(X)
    cv = EK.Canvas(2 * ROAD, SEG, ppm, wrap_u=False, u0=-ROAD, v0=-SEG / 2)
    # tuval u = x, v = y; y'de sarmalı çizim için kendi kaydırmamız: her şekli y ± 10'da da çiz
    def W(fn, *a, **k):
        for sh in (-SEG, 0.0, SEG): fn(sh, *a, **k)
    S = floor_layout(seed)
    ids = Image.new('I', (nx, ny), 0); di = ImageDraw.Draw(ids)
    def px(x, y): return ((x + ROAD) * ppm, (y + SEG / 2) * ppm)
    J = 0.006
    for i, p in enumerate(S):
        for sh in (-SEG, 0.0, SEG):
            a = px(p['x0'] + J, p['y0'] + J + sh); b = px(p['x1'] - J, p['y1'] - J + sh)
            di.rectangle([a, (b[0] - 1, b[1] - 1)], fill=i + 1)
    ID = np.asarray(ids, np.int64); inside = ID > 0
    # plaka kenarı pahı
    N = 4; cur = inside.copy(); dist = np.zeros(inside.shape, np.float32)
    for _ in range(N):
        cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1); dist += cur
    bev = (1.0 - smoothstep(0.0, N, dist + 0.5)) ** 1.5
    h = np.where(inside, -0.007 * bev, -0.008)
    # tırtıklı plaka: 45° elmas kabartma (7 cm); şerit ortasında aşınmış (alçak)
    u = (X + Y) / 0.07; v = (X - Y) / 0.07
    du = np.abs(u - np.round(u)); dv = np.abs(v - np.round(v))
    dia = smoothstep(0.32, 0.18, np.sqrt((du * 0.55) ** 2 + (dv * 1.8) ** 2)) + smoothstep(0.32, 0.18, np.sqrt((du * 1.8) ** 2 + (dv * 0.55) ** 2))
    dia = np.clip(dia, 0, 1)
    kinds = np.array([''] + [p['kind'] for p in S])
    tread = (kinds[ID] == 'tread') & inside & (dist >= N)
    wear = sum(np.exp(-((X - c) / 0.33) ** 2) for c in LANES)
    h += 0.0016 * dia * tread * (1 - 0.6 * wear)
    # çizimler: ızgara yarıkları, kapak, cıvatalar, çıkartmalar, ok işaretleri
    for p in S:
        x0, x1, y0, y1 = p['x0'], p['x1'], p['y0'], p['y1']; Rp = random.Random(p['seed'])
        for sh in (-SEG, 0.0, SEG):
            yy0, yy1 = y0 + sh, y1 + sh
            for (bx, by) in ((x0 + 0.07, yy0 + 0.07), (x1 - 0.07, yy0 + 0.07), (x0 + 0.07, yy1 - 0.07), (x1 - 0.07, yy1 - 0.07),
                             ((x0 + x1) / 2, yy0 + 0.07), ((x0 + x1) / 2, yy1 - 0.07)):
                UK.d_bolt(cv, bx, by, 0.016)
            if p['kind'] == 'vent':
                side = Rp.choice((0, 1)); vx0 = x0 + 0.18 if side == 0 else x1 - 0.18 - 0.62
                cv.rect(vx0 - 0.03, yy0 + 0.2, vx0 + 0.65, yy1 - 0.2, carve=True, col=EK.C(UK.GUN), layer='groove', val=60)
                for k in range(9):
                    yk = yy0 + 0.27 + k * (1.25 - 0.54) / 8
                    cv.line([(vx0 + 0.03, yk), (vx0 + 0.59, yk)], 0.028, col=EK.C('#2a2840'), layer='carve')
            elif p['kind'] == 'hatch':
                cx_, cy_ = (x0 + x1) / 2 + Rp.uniform(-0.3, 0.3), (yy0 + yy1) / 2
                cv.line(EK.arcpts(cx_, cy_, 0.36, 0.36, 0, 360, 40), 0.014, layer='groove')
                cv.line(EK.arcpts(cx_, cy_, 0.31, 0.31, 0, 360, 40), 0.01, col=EK.C(UK.SUN), layer='groove')
                cv.ell(cx_, cy_ + 0.12, 0.09, 0.035, col=EK.C('#3a3852'), layer='carve')
                cv.line([(cx_ - 0.06, cy_ + 0.12), (cx_ + 0.06, cy_ + 0.12)], 0.016, col=EK.C(UK.STEEL), layer='raise')
                for a in range(8):
                    aa = a * TAU / 8 + 0.2; UK.d_bolt(cv, cx_ + math.cos(aa) * 0.4, cy_ + math.sin(aa) * 0.4, 0.011)
            if p['sticker']:
                cx_ = (x0 + x1) / 2
                if Rp.random() < 0.6:
                    UK.d_chevrons(cv, cx_ - 0.32, yy0 + 0.25, 0.64, 0.75, 3, col=UK.SUN)
                else:
                    UK.d_star(cv, cx_, (yy0 + yy1) / 2, 0.22, col=Rp.choice((UK.MINT, UK.CORAL, UK.SUN)), layer='carve')
    # ışık şeritleri (x = ±1,1): kanal, camgöbeği "ışık" camı, 0,5 m'de bir koyu ayraç, kenarda perçinler
    for c in STRIPS:
        for sh in (-SEG, 0.0, SEG):
            cv.rect(c - 0.08, -SEG / 2 + sh, c + 0.08, SEG / 2 + sh, carve=True, col=EK.C('#3b3a58'), layer='groove', val=200)
            for k in range(20):
                ya = -SEG / 2 + k * 0.5 + sh
                cv.rect(c - 0.05, ya + 0.035, c + 0.05, ya + 0.465, carve=True, col=EK.C('#56d6e0'), layer='raise', val=160)
                cv.rect(c - 0.016, ya + 0.06, c + 0.016, ya + 0.44, carve=False, col=EK.C('#d9fbff'))
                for s in (-1, 1): UK.d_bolt(cv, c + s * 0.068, ya + 0.25, 0.008)
    # bordür üstü: mercan/krem çapraz şerit + 1,25 m'de bir sarı yansıtıcı + cıvata
    for s in (-1, 1):
        a, b = (TRIM + 0.06, 3.62) if s > 0 else (-3.62, -TRIM - 0.06)
        for sh in (-SEG, 0.0, SEG):
            UK.d_hazard(cv, a, -SEG / 2 + sh, b - a, SEG, c1=UK.CORAL, c2=UK.CREAM, step=0.25)
            for k in range(8):
                yk = -SEG / 2 + 0.3 + k * 1.25 + sh
                cv.ell((a + b) / 2, yk, 0.04, 0.06, col=EK.C('#ffcf3a'), layer='raise')
                for d in (-0.35, 0.35): UK.d_bolt(cv, (a + b) / 2, yk + d, 0.012)
    hc, over, shade = EK.finish_relief(cv, depth=0.006, groove=0.004, bevel=0.003, fade=0.25, chips=0.45, seed=seed, wrap=(True, False), stone_dark=0.05)
    h = h + hc
    # çizik + sürtme izi (şerit ortasında), dökülmüş boya pulları (cıvata/kenar çevresinde)
    rng = np.random.default_rng(seed + 3)
    sc = Image.new('L', (nx, ny), 0); ds = ImageDraw.Draw(sc)
    for k in range(260):
        c = R.choice(LANES) + R.gauss(0, 0.3); y = R.uniform(-5, 5); L = R.uniform(0.15, 0.6); a = R.gauss(math.pi / 2, 0.25)
        pts = [px(c + math.cos(a) * L * t, y + math.sin(a) * L * t) for t in (0, 0.5, 1)]
        for sh in (-SEG, 0, SEG): ds.line([(q[0], q[1] + sh * ppm) for q in pts], fill=R.randint(90, 200), width=1)
    SCR = EK.blur(np.asarray(sc, np.float32) / 255, 0.5, (True, False))
    scuff = smoothstep(0.62, 0.8, fnoise(h.shape, 0.25 * ppm, seed + 4, 3)) * wear * smoothstep(0.35, 0.65, fnoise(h.shape, 0.08 * ppm, seed + 5, 3))
    # Ay tozu maskesi: birikinti + derz + bordür dibi + rastgele savrulmuş lekeler
    D = drift(X, Y)
    sm = smoothstep(0.003, 0.012, D)
    seam = (~inside).astype(np.float32) * (AX < TRIM) * smoothstep(0.3, 0.55, fnoise(h.shape, 0.3 * ppm, seed + 6, 3))
    near = smoothstep(2.4, 3.3, AX)
    patch = smoothstep(0.58, 0.75, fnoise(h.shape, 0.6 * ppm, seed + 7, 3) + 0.25 * near - 0.12) * (0.2 + 0.8 * near) * (AX < TRIM)
    ontrim = (AX > TRIM) * smoothstep(0.55, 0.7, fnoise(h.shape, 0.3 * ppm, seed + 8, 3)) * 0.7
    cav = EK.cavity(h, ppm, 0.02, 70.0, (True, False))
    smask = np.clip(np.maximum.reduce([sm, seam * 0.8, patch * 0.65, ontrim, cav * 0.4 * (AX < TRIM)]), 0, 1)
    # gölge: plaka başına ton, oyuk, şerit ortası aşınması
    tones = [(1, 1, 1), (0.97, 0.98, 1.03), (1.03, 1.0, 0.98), (0.95, 0.95, 0.99), (1.02, 1.02, 1.04)]
    tint = np.ones((len(S) + 1, 3), np.float32)
    for i in range(1, len(S) + 1): tint[i] = np.array(R.choice(tones), np.float32) * R.uniform(0.96, 1.04)
    sh3 = shade * tint[ID] * np.where(inside, 1.0, 0.82)[..., None]
    sh3 *= (1.0 - 0.45 * cav)[..., None]
    sh3 *= (1.0 + 0.05 * wear)[..., None]
    sh3 *= (0.95 + 0.1 * fnoise(h.shape, 0.4 * ppm, seed + 9, 3))[..., None]
    # üst: sürtme izi (koyu lastik), çizik (açık metal)
    o3 = over[..., :3]; oa = over[..., 3]
    sca = scuff * 0.45; o3 = np.where((sca > oa)[..., None], EK.lin('#4a465c'), o3); oa = np.maximum(oa, sca)
    sra = SCR * 0.55 * (AX < TRIM); o3 = np.where((sra > oa)[..., None], EK.lin('#d7dbe3'), o3); oa = np.maximum(oa, sra)
    over = np.concatenate([o3, oa[..., None]], -1)
    h = h - 0.0006 * SCR
    h = np.where(sm > 0.6, h * 0.2, h)
    nrm = EK.normal_from_height(h, ppm, (True, False))
    return dict(over=over.astype(np.float32), shade=sh3.astype(np.float32), nrm=nrm, sand=smask.astype(np.float32))


def build_floor():
    M = floor_maps()
    dec = EK.Decal('rsfloor', over=M['over'], shade=M['shade'], normal=M['nrm'], sandmask=M['sand'], ext='REPEAT')
    dec.sand_fn = UK.dust_col
    mat = UK.m_paint('deckpaint', UK.DECK, period=SEG, chips=0.0, scratch=0.0, dust=0.0, grime=0.0, fade=0.12, dec=dec, bump=0.06)
    xs = np.concatenate([np.linspace(-ROAD, -3.24, 47), np.linspace(-3.2, 3.2, 161), np.linspace(3.24, ROAD, 47)])
    ys = np.linspace(-6.5, 6.5, 261)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X, Y, floor_z(X, Y)], -1)
    UV = np.stack([(X + ROAD) / (2 * ROAD), (Y + SEG / 2) / SEG], -1)
    hi = EK.grid_obj('rsfloor_hi', P, UV, [mat])
    for s in (-1, 1):   # AO gölgeleyici: duvar dibi (seçilmez, dışa aktarılmaz)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(s * 4.05, 0, 0.15)); o = bpy.context.object; o.scale = (0.4, 16, 0.3); o.name = 'occ'
    half = [3.0, 3.12, 3.22, TRIM, 3.315, 3.33, 3.345, 3.5, 3.66, 3.68, ROAD]
    xl = sorted(set([-v for v in half] + [-1.1, 0.0, 1.1] + half))
    yl = np.linspace(-5, 5, 41)
    XL, YL = np.meshgrid(np.array(xl), yl)
    lo = EK.grid_obj('rsfloor_lo', np.stack([XL, YL, floor_z(XL, YL)], -1), None, [])
    return [hi], [lo], dict(uv_fn=UK.planar_uv(-ROAD, ROAD, -SEG / 2, SEG / 2), cull=False, ao_dist=0.5, ao_strength=0.5, tex=1024)


# ================================================================== çalıştırma

BUILD = {'rs_floor': build_floor}


def preview_angle(name):
    return {'rs_wall': dict(yaw=-58, pitch=18), 'rs_floor': dict(yaw=20, pitch=35)}.get(name, {})


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    name = args[0]
    kit.reset()
    if name == 'scene':
        import uzay_sahne; uzay_sahne.render(args[1]); return
    if name == 'icons':
        import uzay_sahne; uzay_sahne.icons(); return
    hi, lo, opt = BUILD[name]()
    kit.to_mesh_all()
    if '--draft' in args:
        EK.draft(args[args.index('--draft') + 1], **opt.get('draft', {})); return
    opt.pop('draft', None)
    if lo is None: EK.bake_auto(name, hi, **opt)
    else: UK.bake_custom(name, hi, lo, **opt)
    if '--preview' in args:
        png = args[args.index('--preview') + 1]
        EK.preview(name, png, **preview_angle(name))


try:
    import gezegen_engeller; BUILD.update(gezegen_engeller.BUILD)
except ImportError as e:
    if 'gezegen_engeller' not in str(e): raise
try:
    import uzay_arka; BUILD.update(uzay_arka.BUILD)
except ImportError as e:
    if 'uzay_arka' not in str(e): raise

if __name__ == '__main__':
    main()
