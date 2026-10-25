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
from kit import blob, tube, cyl

SEG = 10.0
ROAD = 3.7
TRIM = 3.3                 # bordür iç kenarı
LANES = (-2.2, 0.0, 2.2)
STRIPS = (-1.1, 1.1)


# ================================================================== ortak yardımcılar (uç uca döşenen parçalar)

def repeats(y, lo=-6.6, hi=6.6):
    """y konumundaki tekil parçanın taslakta (−6,6..6,6) kopyaları: [(kaydırma, hedefe_girer_mi)]."""
    out = []
    for sh in (-SEG, 0.0, SEG):
        if lo <= y + sh <= hi: out.append((sh, sh == 0.0))
    return out


def ptube(name, fn, y0, y1, r, mats, sides=10, step=0.08, flip=False):
    """y boyunca giden dönemli tüp (kablo/boru): fn(y) → (x, z) eksen; uçlar açık (komşu parçayla birleşir)."""
    ys = np.linspace(y0, y1, max(2, int(round((y1 - y0) / step)) + 1))
    C = np.array([fn(y) for y in ys]); th = np.linspace(0, TAU, sides + 1)
    P = np.zeros((len(ys), sides + 1, 3))
    for i, y in enumerate(ys):
        # yaklaşık çerçeve: teğet ~ +y (sarkma küçük); kesit x–z düzleminde
        P[i, :, 0] = C[i, 0] + r * np.cos(th); P[i, :, 1] = y; P[i, :, 2] = C[i, 1] + r * np.sin(th)
    o = EK.grid_obj(name, P, None, mats, flip=not flip)
    EK.weld(o)
    return o


def prism(name, loop, y0, y1, mats, rows=2, flip=False):
    """Kapalı (x, z) kesitin y boyunca uzatılması (uçlar açık). loop saat yönünde verilirse normaller dışa."""
    L = list(loop) + [loop[0]]; ys = np.linspace(y0, y1, rows)
    P = np.zeros((len(L), len(ys), 3))
    for i, (x, z) in enumerate(L):
        P[i, :, 0] = x; P[i, :, 1] = ys; P[i, :, 2] = z
    o = EK.grid_obj(name, P, None, mats, flip=not flip)
    EK.weld(o)
    return o


def rbox_loop(w, h, cx, cz, r=0.02, n=3):
    """Yuvarlak köşeli dikdörtgen kesit (saat yönünde: sol alt → sol üst → sağ üst → sağ alt)."""
    pts = []
    corners = ((cx - w / 2 + r, cz - h / 2 + r, 180, 90), (cx - w / 2 + r, cz + h / 2 - r, 180, 90), (cx + w / 2 - r, cz + h / 2 - r, 90, 0), (cx + w / 2 - r, cz - h / 2 + r, 0, -90), (cx - w / 2 + r, cz - h / 2 + r, -90, -180))
    seq = [(cx - w / 2 + r, cz - h / 2 + r, 180, 90 + 0)]
    for (qx, qz, a0, a1) in ((cx - w / 2 + r, cz + h / 2 - r, 180, 90), (cx + w / 2 - r, cz + h / 2 - r, 90, 0), (cx + w / 2 - r, cz - h / 2 + r, 0, -90), (cx - w / 2 + r, cz - h / 2 + r, -90, -180)):
        for k in range(n):
            a = math.radians(a0 + (a1 - a0) * k / (n - 1)); pts.append((qx + r * math.cos(a), qz + r * math.sin(a)))
    return pts


# ================================================================== rs_floor (uzayda süzülen yürüyüş yolu)

def deck_profile(step=0.01):
    """Güverte kesiti (saat yönünde, normaller dışa): sol alt kenar → sol yan yüz → sol bordür → üst (z = 0) → sağ bordür → sağ yan →
    sağ alt kenar. Bordür: 3,30'da yükselen yuvarlak kenarlı kalın şerit (tepe 0,12), dış yüz 3,70'te −0,26'ya iner, alt kenar −0,30."""
    def arc(cx, cz, r, a0, a1, n):
        return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
    R_ = [(0.0, 0.0), (TRIM, 0.0), (TRIM, 0.04)] + arc(3.38, 0.04, 0.08, 180, 90, 8) + [(3.62, 0.12)] + arc(3.62, 0.04, 0.08, 90, 0, 8) + \
         [(ROAD, -0.26)] + arc(3.66, -0.26, 0.04, 0, -90, 5) + [(3.4, -0.3), (3.4, -0.24)]
    L_ = [(-x, z) for (x, z) in reversed(R_)]
    full = L_ + R_[1:]
    pts = [full[0]]
    for a, b in zip(full[:-1], full[1:]):
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        for k in range(1, n + 1): pts.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    P = np.array(pts); s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    sparse = np.array(full)
    return P, s, sparse


def floor_layout(seed=5):
    """Plaka yerleşimi: her şerit bölgesinde tek sütun plaka, 1,25 m (şeritler arası kaydırmalı); tür: tırtıklı / düz / ızgara / kapak / yamalı."""
    R = random.Random(seed); S = []
    zones = ((-TRIM, -1.18), (-1.02, 1.02), (1.18, TRIM))
    for zi, (a, b) in enumerate(zones):
        off = (0.0, 0.42, 0.83)[zi]
        for k in range(8):
            y0 = -SEG / 2 + off + k * 1.25
            r = R.random()
            kind = 'tread' if r < 0.48 else 'plain' if r < 0.74 else 'vent' if r < 0.84 else 'hatch' if r < 0.93 else 'patch'
            S.append(dict(x0=a, x1=b, y0=y0, y1=y0 + 1.25, kind=kind, sticker=(kind == 'plain' and R.random() < 0.6), seed=R.randint(0, 9999)))
    return S


def floor_maps(ppm=140, seed=5):
    """Haritalar (u = kesit yay uzunluğu s, v = y; y dönemli): plakalar, cıvatalar, ışık şeritleri, bordür boyası, yan yüz şeridi."""
    from PIL import Image, ImageDraw
    R = random.Random(seed)
    P, s, _ = deck_profile(0.005); S_ = float(s[-1])
    i_top = int(np.argmin(np.abs(P[:, 0] + TRIM) + np.abs(P[:, 1]) * 10)); s_top = float(s[i_top])
    def sx(x): return s_top + (x + TRIM)                        # üst yüzde x → s
    def s_of(x, z):                                               # kesitte (x, z)'ye en yakın noktanın s'si
        return float(s[int(np.argmin((P[:, 0] - x) ** 2 + (P[:, 1] - z) ** 2))])
    cv = EK.Canvas(S_, SEG, ppm, u0=0.0, v0=-SEG / 2, wrap_v=True)
    nx, ny = cv.W, cv.H
    Ss = (np.arange(nx) + 0.5) / ppm; Ys = (np.arange(ny) + 0.5) / ppm - SEG / 2
    SS, YY = np.meshgrid(Ss, Ys)
    Xtop = SS - s_top - TRIM                                       # üst yüzde x (yalnız orada anlamlı)
    ontop = (SS >= s_top - 0.002) & (SS <= s_top + 2 * TRIM + 0.002)
    S = floor_layout(seed)
    ids = Image.new('I', (nx, ny), 0); di = ImageDraw.Draw(ids)
    def px(u, v): return (u * ppm, (v + SEG / 2) * ppm)
    J = 0.006
    for i, p in enumerate(S):
        for sh in (-SEG, 0.0, SEG):
            a = px(sx(p['x0']) + J, p['y0'] + J + sh); b = px(sx(p['x1']) - J, p['y1'] - J + sh)
            di.rectangle([a, (b[0] - 1, b[1] - 1)], fill=i + 1)
    ID = np.asarray(ids, np.int64); inside = ID > 0
    N = 4; cur = inside.copy(); dist = np.zeros(inside.shape, np.float32)
    for _ in range(N):
        cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1); dist += cur
    bev = (1.0 - smoothstep(0.0, N, dist + 0.5)) ** 1.5
    h = np.where(inside, -0.007 * bev, np.where(ontop, -0.008, 0.0))
    u = (Xtop + YY) / 0.07; v = (Xtop - YY) / 0.07
    du = np.abs(u - np.round(u)); dv = np.abs(v - np.round(v))
    dia = np.clip(smoothstep(0.32, 0.18, np.sqrt((du * 0.55) ** 2 + (dv * 1.8) ** 2)) + smoothstep(0.32, 0.18, np.sqrt((du * 1.8) ** 2 + (dv * 0.55) ** 2)), 0, 1)
    kinds = np.array([''] + [p['kind'] for p in S])
    tread = (kinds[ID] == 'tread') & inside & (dist >= N)
    wear = sum(np.exp(-((Xtop - c) / 0.33) ** 2) for c in LANES) * ontop
    h += 0.0016 * dia * tread * (1 - 0.6 * wear)
    for p in S:
        x0, x1, y0, y1 = sx(p['x0']), sx(p['x1']), p['y0'], p['y1']; Rp = random.Random(p['seed'])
        for (bx, by) in ((x0 + 0.07, y0 + 0.07), (x1 - 0.07, y0 + 0.07), (x0 + 0.07, y1 - 0.07), (x1 - 0.07, y1 - 0.07), ((x0 + x1) / 2, y0 + 0.07), ((x0 + x1) / 2, y1 - 0.07)):
            UK.d_bolt(cv, bx, by, 0.016)
        if p['kind'] == 'vent':
            vx0 = x0 + 0.18 if Rp.random() < 0.5 else x1 - 0.18 - 0.62
            cv.rect(vx0 - 0.03, y0 + 0.2, vx0 + 0.65, y1 - 0.2, carve=True, col=EK.C(UK.GUN), layer='groove', val=60)
            for k in range(9):
                yk = y0 + 0.27 + k * (1.25 - 0.54) / 8
                cv.line([(vx0 + 0.03, yk), (vx0 + 0.59, yk)], 0.028, col=EK.C('#24223a'), layer='carve')
        elif p['kind'] == 'hatch':
            cx_, cy_ = (x0 + x1) / 2 + Rp.uniform(-0.3, 0.3), (y0 + y1) / 2
            cv.line(EK.arcpts(cx_, cy_, 0.36, 0.36, 0, 360, 40), 0.014, layer='groove')
            cv.line(EK.arcpts(cx_, cy_, 0.31, 0.31, 0, 360, 40), 0.012, col=EK.C(UK.SUN), layer='groove')
            cv.ell(cx_, cy_ + 0.12, 0.09, 0.035, col=EK.C('#3a3852'), layer='carve')
            cv.line([(cx_ - 0.06, cy_ + 0.12), (cx_ + 0.06, cy_ + 0.12)], 0.016, col=EK.C(UK.STEEL), layer='raise')
            for a in range(8):
                aa = a * TAU / 8 + 0.2; UK.d_bolt(cv, cx_ + math.cos(aa) * 0.4, cy_ + math.sin(aa) * 0.4, 0.011)
        elif p['kind'] == 'patch':
            pw, ph_ = Rp.uniform(0.45, 0.8), Rp.uniform(0.35, 0.6); cx_ = Rp.uniform(x0 + 0.2 + pw / 2, x1 - 0.2 - pw / 2); cy_ = (y0 + y1) / 2
            cv.rect(cx_ - pw / 2, cy_ - ph_ / 2, cx_ + pw / 2, cy_ + ph_ / 2, carve=True, col=EK.C(Rp.choice(('#8fb7c9', '#b9a6c9', '#9fc7b2'))), layer='raise', val=120)
            for k in range(int(pw / 0.09)):
                for yy in (cy_ - ph_ / 2 + 0.03, cy_ + ph_ / 2 - 0.03): UK.d_bolt(cv, cx_ - pw / 2 + 0.04 + k * 0.09, yy, 0.009)
            for k in range(int(ph_ / 0.09)):
                for xx in (cx_ - pw / 2 + 0.03, cx_ + pw / 2 - 0.03): UK.d_bolt(cv, xx, cy_ - ph_ / 2 + 0.06 + k * 0.09, 0.009)
        if p['sticker']:
            cx_ = (x0 + x1) / 2
            if Rp.random() < 0.6: UK.d_chevrons(cv, cx_ - 0.32, y0 + 0.25, 0.64, 0.75, 3, col=UK.SUN)
            else: UK.d_star(cv, cx_, (y0 + y1) / 2, 0.22, col=Rp.choice((UK.MINT, UK.CORAL, UK.SUN)))
    # ışık şeritleri (x = ±1,1)
    for c in STRIPS:
        cv.rect(sx(c - 0.08), -SEG / 2, sx(c + 0.08), SEG / 2, carve=True, col=EK.C('#353452'), layer='groove', val=200)
        for k in range(20):
            ya = -SEG / 2 + k * 0.5
            cv.rect(sx(c - 0.05), ya + 0.035, sx(c + 0.05), ya + 0.465, carve=True, col=EK.C('#4fd2de'), layer='raise', val=160)
            cv.rect(sx(c - 0.016), ya + 0.06, sx(c + 0.016), ya + 0.44, carve=False, col=EK.C('#d9fbff'))
            for sgn in (-1, 1): UK.d_bolt(cv, sx(c + sgn * 0.068), ya + 0.25, 0.008)
    # bordür (iki yan): üstte krem/mercan çapraz şerit, iç eğimde lacivert, cıvatalar; dış yüzde lacivert + nane çizgi + perçin
    for sgn in (-1, 1):
        a = s_of(sgn * 3.40, 0.12); b = s_of(sgn * 3.60, 0.12); lo_, hi_ = min(a, b), max(a, b)
        UK.d_hazard(cv, lo_, -SEG / 2 - 1, hi_ - lo_, SEG + 2, c1=UK.CORAL, c2=UK.CREAM, step=0.25)
        t0 = s_of(sgn * TRIM, 0.0); t1 = s_of(sgn * 3.36, 0.11)
        cv.rect(min(t0, t1), -SEG / 2 - 1, max(t0, t1), SEG / 2 + 1, carve=False, col=EK.C(UK.NAVY))
        f0 = s_of(sgn * ROAD, 0.0); f1 = s_of(sgn * ROAD, -0.26)
        cv.rect(min(f0, f1) - 0.04, -SEG / 2 - 1, max(f0, f1) + 0.03, SEG / 2 + 1, carve=False, col=EK.C(UK.NAVY))
        mid = s_of(sgn * ROAD, -0.07)
        cv.rect(mid - 0.018, -SEG / 2 - 1, mid + 0.018, SEG / 2 + 1, carve=False, col=EK.C(UK.MINT))
        for k in range(40):
            yk = -SEG / 2 + 0.125 + k * 0.25
            for zz in (-0.02, -0.22): UK.d_bolt(cv, s_of(sgn * ROAD, zz), yk, 0.009)
        for k in range(8):
            ys_ = -SEG / 2 + k * 1.25
            cv.line([(min(f0, f1), ys_), (max(f0, f1), ys_)], 0.01, layer='groove')
    hc, over, shade = EK.finish_relief(cv, depth=0.006, groove=0.004, bevel=0.003, fade=0.22, chips=0.45, seed=seed, wrap=(True, False), stone_dark=0.05)
    h = h + hc
    # çizik + lastik sürtme izi (şerit ortasında), oyuk kiri
    sc = Image.new('L', (nx, ny), 0); ds = ImageDraw.Draw(sc)
    for k in range(260):
        c = R.choice(LANES) + R.gauss(0, 0.3); y = R.uniform(-5, 5); Ln = R.uniform(0.15, 0.6); ang = R.gauss(math.pi / 2, 0.25)
        pts = [px(sx(c + math.cos(ang) * Ln * t), y + math.sin(ang) * Ln * t) for t in (0, 0.5, 1)]
        for sh in (-SEG, 0, SEG): ds.line([(q[0], q[1] + sh * ppm) for q in pts], fill=R.randint(90, 200), width=1)
    SCR = EK.blur(np.asarray(sc, np.float32) / 255, 0.5, (True, False)) * ontop
    scuff = smoothstep(0.62, 0.8, fnoise(h.shape, 0.25 * ppm, seed + 4, 3)) * wear * smoothstep(0.35, 0.65, fnoise(h.shape, 0.08 * ppm, seed + 5, 3))
    cav = EK.cavity(h, ppm, 0.02, 70.0, (True, False))
    tones = [(1, 1, 1), (0.97, 0.98, 1.03), (1.03, 1.0, 0.98), (0.95, 0.95, 0.99), (1.02, 1.02, 1.04)]
    tint = np.ones((len(S) + 1, 3), np.float32)
    for i in range(1, len(S) + 1): tint[i] = np.array(R.choice(tones), np.float32) * R.uniform(0.96, 1.04)
    sh3 = shade * tint[ID] * np.where(inside | ~ontop, 1.0, 0.7)[..., None]
    sh3 *= (1.0 - 0.45 * cav)[..., None]
    sh3 *= (1.0 + 0.05 * wear)[..., None]
    sh3 *= (0.95 + 0.1 * fnoise(h.shape, 0.4 * ppm, seed + 9, 3))[..., None]
    o3 = over[..., :3]; oa = over[..., 3]
    sca = scuff * 0.45; o3 = np.where((sca > oa)[..., None], EK.lin('#4a465c'), o3); oa = np.maximum(oa, sca)
    sra = SCR * 0.55; o3 = np.where((sra > oa)[..., None], EK.lin('#d7dbe3'), o3); oa = np.maximum(oa, sra)
    over = np.concatenate([o3, oa[..., None]], -1)
    h = h - 0.0006 * SCR
    nrm = EK.normal_from_height(h, ppm, (True, False))
    return dict(over=over.astype(np.float32), shade=sh3.astype(np.float32), nrm=nrm, P=P, s=s, S=S_)


def under_mat(name, hexc=UK.GUN):
    """Güverte altı sacı: 1,25 m × 1,1 m panel dikişleri (dünya koordinatı, 10 m'de dönemli) + perçin sırası."""
    def b(nt, bsdf):
        G = EK.EG(nt); cw = G.coords(SEG)
        x, y, z = G.sep(G.pos())
        col = G.mix(G.rng(G.noise4(cw, 0.8, 3), 0.3, 0.7), UK._sh(hexc, 0.92), UK._sh(hexc, 1.08))
        def seam(v, per):
            f = G.math('FRACT', G.math('DIVIDE', v, per)); d = G.math('ABSOLUTE', G.math('SUBTRACT', f, 0.5))
            return G.rng(d, 0.5 - 0.008 / per * 1.0, 0.5 - 0.002 / per)
        sm = G.math('MAXIMUM', seam(y, 1.25), seam(G.math('ADD', x, 0.55), 1.1))
        col = G.mix(G.math('MULTIPLY', sm, 0.7), col, '#1f1d2e')
        col = G.mix(G.rng(G.ao(0.15), 0.85, 0.35, 0, 0.5), col, '#1f1d2e')
        col = G.mix(G.math('MULTIPLY', G.edges(0.53, 0.62), 0.35), col, UK._sh(hexc, 1.35))
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.4; bb.inputs['Distance'].default_value = 0.01
        G.l.new(G.math('SUBTRACT', 1.0, sm), bb.inputs['Height']); G.l.new(bb.outputs['Normal'], bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def build_floor():
    M = floor_maps()
    dec = EK.Decal('rsfloor', over=M['over'], shade=M['shade'], normal=M['nrm'], ext='REPEAT')
    TOP = UK.m_paint('deckpaint', UK.DECK, period=SEG, chips=0.0, scratch=0.0, dust=0.0, grime=0.35, fade=0.12, dec=dec, bump=0.06)
    P, s, S_ = M['P'], M['s'], M['S']
    ys = np.linspace(-6.5, 6.5, 261)
    PP = np.zeros((len(P), len(ys), 3)); UV = np.zeros((len(P), len(ys), 2))
    PP[..., 0] = P[:, 0:1]; PP[..., 1] = ys[None, :]; PP[..., 2] = P[:, 1:2]
    UV[..., 0] = s[:, None] / S_; UV[..., 1] = (ys[None, :] + SEG / 2) / SEG
    hi = [EK.grid_obj('deck_hi', PP, UV, [TOP], flip=True)]
    lo = []
    _, _, SP = deck_profile()
    for (ya, yb) in ((-5.0, 0.0), (0.0, 5.0)):
        Pk = np.zeros((len(SP), 3, 3)); Pk[..., 0] = SP[:, 0:1]; Pk[..., 2] = SP[:, 1:2]; Pk[..., 1] = np.linspace(ya, yb, 3)[None, :]
        lo.append(EK.tag_uvw(EK.grid_obj('deck_lo', Pk, None, [], flip=True), 1.0))
    # alt sac
    UM = under_mat('undermat')
    xs = np.linspace(-3.4, 3.4, 69); X, Y = np.meshgrid(xs, ys)
    hi.append(EK.grid_obj('under_hi', np.stack([X, Y, np.full_like(X, -0.24)], -1), None, [UM], flip=True))
    XL, YL = np.meshgrid(np.array([-3.4, 0.0, 3.4]), np.linspace(-5, 5, 3))
    lo.append(EK.tag_uvw(EK.grid_obj('under_lo', np.stack([XL, YL, np.full_like(XL, -0.24)], -1), None, [], flip=True), 0.3))
    # kirişler (lacivert, I kesitli): x = ±2,0, z −0,24..−0,56
    GD = UK.m_paint('girder', UK.NAVY, period=SEG, chips=0.5, dust=0.0, grime=0.5, under=UK.STEEL, seed=2.0)
    def ibeam(cx):
        return [(cx - 0.05, -0.53), (cx - 0.05, -0.27), (cx - 0.13, -0.27), (cx - 0.13, -0.24), (cx + 0.13, -0.24), (cx + 0.13, -0.27), (cx + 0.05, -0.27),
                (cx + 0.05, -0.53), (cx + 0.13, -0.53), (cx + 0.13, -0.56), (cx - 0.13, -0.56), (cx - 0.13, -0.53)]
    for cx in (-2.0, 2.0):
        hi.append(prism('girder', ibeam(cx), -6.5, 6.5, [GD], rows=131))
        lo.append(EK.tag_uvw(prism('girder_lo', ibeam(cx), -5.0, 5.0, [], rows=2), 0.6))
    # çapraz kiriş (sarı) + kirişten bordüre çapraz dikme (çelik boru), perçinli bağlantı levhası
    YB = UK.m_paint('crossbeam', UK.SUN, chips=0.6, dust=0.0, grime=0.5, under=UK.STEEL, seed=3.0)
    ST = UK.m_metal('strut', UK.STEEL, dust=0.0)
    for yb in (-3.75, -1.25, 1.25, 3.75):
        for sh, keep in repeats(yb):
            y = yb + sh
            o = EK.rounded_box('crossb', (4.3, 0.16, 0.14), 0.02, 0.03, [YB], loc=(0, y, -0.49), chips=0.008, seed=int(y * 10) + 50)
            hi.append(o)
            if keep: lo += [EK.tag_uvw(q, 0.5) for q in EK.BK.build_low([o], [(r'.', 0.012)])]
    for k in range(8):
        yb = -4.375 + k * 1.25; d = 0.5 if k % 2 == 0 else -0.5
        for sgn in (-1, 1):
            for sh, keep in repeats(yb):
                y = yb + sh
                a = (sgn * 2.08, y - d * 0.5, -0.5); b = (sgn * 3.42, y + d * 0.5, -0.29)
                t = UK.cable('strut', [a, tuple((V(a) + V(b)) / 2), b], 0.028, ST, res=2)
                hi.append(t)
                if keep:
                    q = ptube_seg('strut_lo', a, b, 0.03, 6); lo.append(EK.tag_uvw(q, 0.4))
    # sarkan kablo demetleri (mercan, camgöbeği): çapraz kirişler arasında sarkar
    CC = UK.m_rubber('cab_coral', UK.CORAL, period=SEG); CT = UK.m_rubber('cab_teal', UK.TEAL, period=SEG)
    for (cx, r, m, ph) in ((-0.45, 0.035, CC, 0.0), (-0.36, 0.028, CT, 0.4), (0.55, 0.032, CT, 0.9)):
        def fn(y, cx=cx, ph=ph):
            q = ((y - 1.25) % 2.5) / 2.5
            return (cx + 0.02 * math.sin(y * 1.3 + ph), -0.5 - 0.22 * math.sin(math.pi * q) ** 1.3)
        hi.append(ptube('cable', fn, -6.5, 6.5, r, [m], sides=10, step=0.06))
        lo.append(EK.tag_uvw(ptube('cable_lo', fn, -5.0, 5.0, r, [], sides=5, step=0.42), 0.4))
    # itici kapsüller (y = 0, iki yanda) ve dengeleyici kanatçıklar (y = ±2,5)
    for sgn in (-1, 1):
        parts = thruster((sgn * 3.15, 0.0, -0.3))
        hi += parts; lo += [EK.tag_uvw(q, 0.9) for q in EK.BK.build_low([q for q in parts if not q.name.startswith('rivet')], [(r'_body$', 0.06), (r'_cap$', 0.12), (r'_nozzle$', 0.3), (r'_glow$', 0.3), (r'_bracket$', 0.02)])]
        for yb in (-2.5, 2.5):
            for sh, keep in repeats(yb):
                f = fin((sgn * 3.5, yb + sh, -0.3), sgn)
                hi.append(f)
                if keep: lo += [EK.tag_uvw(q, 0.6) for q in EK.BK.build_low([f], [(r'.', 0.3)])]
    # bordür üstünde yuvarlak işaret lambaları (1,25 m'de bir, camgöbeği/sarı)
    for sgn in (-1, 1):
        for k in range(8):
            yb = -4.375 + k * 1.25
            for sh, keep in repeats(yb):
                parts = UK.lamp('mlamp', (sgn * 3.5, yb + sh, 0.12), 0.045, UK.CYAN if k % 2 == 0 else UK.SUN, cage=False, base_h=0.025)
                hi += parts
                if keep: lo += [EK.tag_uvw(q, 1.0) for q in EK.BK.build_low(parts, [(r'_bulb$', 0.12), (r'_base$', 0.5)])]
    return hi, lo, dict(cull=False, ao_dist=0.45, ao_strength=0.5, tex=1024, cage=0.02, ray=0.08, draft=dict(yaw=24, pitch=6, target=(2.6, 0, -0.2), dist=6.5))


def ptube_seg(name, a, b, r, sides=6):
    """Düz boru (hedef): a → b, uçlar kapalı değil (kısa dikmeler kirişe/bordüre gömülü)."""
    a = V(a); b = V(b); d = (b - a).normalized(); t = d.orthogonal().normalized(); u = d.cross(t)
    verts = []; faces = []
    for p in (a, b):
        for k in range(sides):
            ang = k / sides * TAU; verts.append(tuple(p + (t * math.cos(ang) + u * math.sin(ang)) * r))
    for k in range(sides):
        k2 = (k + 1) % sides; faces.append((k, k2, sides + k2, sides + k))
    o = EK.mesh_obj(name, verts, faces, [])
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    if sum((f.calc_center_median() - (a + b) / 2).dot(f.normal) for f in bm.faces) < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(o.data); bm.free()
    return o


def thruster(loc):
    """Küçük itici kapsül: krem gövde, mercan başlık bandı, top metal meme (aşağı), içte camgöbeği ışık halkası, bağlantı levhası."""
    x, y, z = loc
    BODY = UK.m_paint('thr_body', UK.CREAM, chips=0.5, dust=0.0, seed=4.0); CAP = UK.m_paint('thr_cap', UK.CORAL, chips=0.5, dust=0.0, seed=5.0)
    NZ = UK.m_metal('thr_nz', UK.GUN, dust=0.0); GL = UK.m_glow('thr_glow', UK.CYAN)
    parts = [EK.rounded_box('thr_bracket', (0.18, 0.4, 0.06), 0.015, 0.02, [UK.m_metal('thr_br', UK.STEEL, dust=0.0)], loc=(x, y, z - 0.03))]
    parts.append(blob('thr_body', (x, y, z - 0.2), (0.13, 0.17, 0.16), BODY, seg=24))
    parts.append(EK.lathe_grid('thr_cap', [(0.0, 0.0), (0.135, 0.0), (0.135, 0.06), (0.1, 0.1), (0.0, 0.1)], 20, [CAP], loc=(x, y, z - 0.14), uv=False))
    nz = EK.lathe_grid('thr_nozzle', [(0.0, -0.07), (0.065, -0.075), (0.085, -0.135), (0.1, -0.13), (0.075, -0.06), (0.06, 0.0), (0.0, 0.0)], 16, [NZ], loc=(x, y, z - 0.33), uv=False)
    parts.append(nz)
    parts.append(EK.disc('thr_glow', 0.07, z - 0.33 - 0.1, 16, [GL], loc=(x, y), down=True))
    for k in range(6):
        a = k / 6 * TAU; parts.append(UK.rivet((x + math.cos(a) * 0.12, y + math.sin(a) * 0.12, z - 0.02), (0, 0, -1), 0.01))
    return parts


def fin(loc, sgn):
    """Dengeleyici kanatçık: bordür altından aşağı ve dışa süpürülmüş kalın üçgen (mercan, kenarı pahlı)."""
    x, y, z = loc
    FN = UK.m_paint('finpaint', UK.CORAL, chips=0.6, dust=0.0, seed=6.0)
    prof = [(0.0, 0.0), (0.0, -0.3), (0.16, -0.36), (0.3, 0.0)]          # (y boyunca, z boyunca)
    mid = [(x + sgn * (-b * 0.45), y - 0.15 + a, z + b) for (a, b) in prof]
    th = 0.022
    verts = [(vx - th, vy, vz) for (vx, vy, vz) in mid] + [(vx + th, vy, vz) for (vx, vy, vz) in mid]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4)] + [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)]
    o = EK.mesh_obj('fin', verts, faces, [FN], smooth=False)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.01; bv.segments = 2
    return o


# ================================================================== çalıştırma

BUILD = {'rs_floor': build_floor}


def preview_angle(name):
    return {'rs_wall': dict(yaw=-58, pitch=18), 'rs_floor': dict(yaw=28, pitch=14)}.get(name, {})


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
        for o in (lo or []): bpy.data.objects.remove(o)
        for o in [o for o in bpy.data.objects if o.name.startswith('occ')]: bpy.data.objects.remove(o)
        d = dict(opt.get('draft', {}))
        if '--angle' in args: y_, p_ = args[args.index('--angle') + 1].split(','); d['yaw'] = float(y_); d['pitch'] = float(p_)
        EK.draft(args[args.index('--draft') + 1], **d); return
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
