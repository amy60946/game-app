# Ada v6 arazisi (21 Ekim 2026, kullanıcı: 56 referansla haritanın son hâli, ada büyütülür).
# Saf numpy: Blender taslağı da, oyun da aynı yükseklik haritasını kullanır (oyuna pişmiş ızgara olarak girer → onaylanan görüntü 1:1).
# Biçim: katmanlı kayalık platolar (dik yar + tabaka basamakları + dikey oluklar), ortada basamaklı kaya tepe (yer imi),
# tepeyi dolanan kumlu kanyon, güneyde kumsal + köy düzlüğü, batıda inişli çıkışlı çiçekli çayır + göl, doğuda orman platosu,
# kuzeybatıda karlı zirve, kuzeydoğuda fener burnu. Referans görseller yalnız hava/kalite hedefi; biçimler özgün.
#   python3 terrain_v6.py <çıktı.npz> [önizleme.png]
import sys, json, math, os
import numpy as np

STEP = 0.2
X0, X1, Z0, Z1 = -100.0, 100.0, -88.0, 88.0
SEA_FLOOR = -7.0
LAKE = dict(x=-28.0, z=6.0, r=9.0, level=6.75)

# ------------------------------------------------------------------ yerleşim (oyundaki regions.json'a gidecek; x doğu, z kuzey)
REGIONS = [
    # id, ad, x, z, şekil, boy, yön(°)
    ('region_home', 'Evim', 0.0, -30.0, 'house', 8.6, 0),
    ('region_shop', 'Dükkan', -22.0, -23.0, 'house', 8.0, 18),
    ('region_task_board', 'Ev Görevleri', 17.0, -24.0, 'board', 5.5, -16),
    ('region_festival', 'Festival Alanı', 0.0, -6.0, 'tent', 9.0, 0),
    ('region_garden', 'Bahçe', 28.0, -38.0, 'garden', 8.6, -10),
    ('region_pier', 'İskele', 40.0, -61.0, 'pier', 8.6, 0),
    ('region_swim_cove', 'Yüzme Koyu', 61.0, -37.0, 'pool', 8.6, -30),
    ('region_surf_beach', 'Sörf Plajı', 75.0, -12.0, 'board', 6.8, -70),
    ('region_coconut_grove', 'Hindistan Cevizi Bahçesi', -79.5, -7.5, 'palm', 7.4, 0),   # GB17: kumsalın geniş yeri (dar geçidi kapatmasın)
    ('region_cave', 'Mağara', -60.0, 12.0, 'hill', 8.6, 127),
    ('region_game_hut', 'Oyun Kulübesi', 30.0, 4.0, 'house', 8.0, -27),   # GB18: tapınak yolunun üstünden düz açıklığa
    ('region_ski_hill', 'Kayak Tepesi', -38.0, 40.0, 'hill', 8.6, 30),
    ('region_mountain', 'Dağ', 20.0, 56.0, 'hill', 9.8, 0),
    ('region_lighthouse', 'Fener', 60.0, 46.0, 'tower', 5.5, 0),
]
PLAZA = (0.0, -17.0)
ISLET = (24.0, -79.0, 7.5)
SNOW_PATH = [(-36.5, 40.5), (-46, 42), (-53, 47), (-54, 53), (-49, 59), (-43, 61.5), (-38, 58), (-41, 56.5)]
BEACH_REGIONS = ('region_swim_cove', 'region_surf_beach', 'region_coconut_grove')
# süs alanları (yalnız görsel; oyunda dekor)
SPOTS = dict(temple=(28.0, 38.0), camp=(54.0, 2.0), spire=(9.0, 25.0), lake=(LAKE['x'], LAKE['z']), bluebell=(-40.0, -8.0),
             forest=(44.0, 22.0), boulders=(-60.0, 14.0), canyon=(-3.0, 22.0))

# patikalar (çoklu çizgi); platoya çıkan yerlerde arazi rampa olur
PATHS = [
    [(0, -17), (0, -25)],                                   # meydan → Evim
    [(0, -17), (-10, -19), (-18, -21)],                     # → Dükkan
    [(0, -17), (8, -19), (14, -22)],                        # → Ev Görevleri
    [(0, -17), (0, -10)],                                   # → Festival
    [(0, -17), (12, -28), (26, -36)],                       # → Bahçe
    [(26, -36), (34, -48), (39, -58)],                      # → İskele
    [(14, -22), (32, -26), (46, -30), (56, -34)],           # → Yüzme Koyu
    [(56, -34), (60, -36)], [(56, -34), (68, -24), (74, -14)],   # → Yüzme koyu, Sörf
    [(-18, -21), (-34, -18), (-52, -22), (-62, -20), (-70, -16)],   # → Hindistan cevizi
    [(-34, -18), (-42, -6), (-50, 4), (-56, 10)],           # → Mağara
    [(-42, -6), (-34, 0), (-30, -2)],                       # → göl kıyısı
    [(0, -6), (-2, 2), (-4, 12), (-6, 22), (-9, 33), (-12, 42)],   # festival → kanyon → yukarı plato
    [(-12, 42), (-24, 42), (-34, 38)],                      # → Kayak
    [(-12, 42), (2, 46), (14, 50)],                         # → Dağ
    [(14, -22), (26, -14), (34, -4), (44, 2), (52, 2)],     # → doğu platosu → kamp
    [(44, 2), (40, 10), (36, 14)],                          # → Oyun Kulübesi
    [(40, 10), (46, 24), (52, 34), (58, 42)],               # orman → Fener
    [(36, 14), (32, 20), (28, 26)],                          # → Tapınak
]

# ------------------------------------------------------------------ gürültü (taşınabilir: tamsayı karması + yumuşak ara değer)

def _hash(i, j, seed):
    h = (i.astype(np.int64) * 374761393 + j.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF) * 2.0 - 1.0

def vnoise(x, z, seed=0):
    xi = np.floor(x); zi = np.floor(z); fx = x - xi; fz = z - zi
    xi = xi.astype(np.int64); zi = zi.astype(np.int64)
    ux = fx * fx * (3 - 2 * fx); uz = fz * fz * (3 - 2 * fz)
    a = _hash(xi, zi, seed); b = _hash(xi + 1, zi, seed); c = _hash(xi, zi + 1, seed); d = _hash(xi + 1, zi + 1, seed)
    return (a + (b - a) * ux) + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uz

def fbm(x, z, freq, seed, octs=4, gain=0.5):
    out = np.zeros_like(x); amp = 1.0; tot = 0.0; f = freq
    for o in range(octs):
        out += vnoise(x * f, z * f, seed + o * 31) * amp; tot += amp; amp *= gain; f *= 2.03
    return out / tot

def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)

def sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

def blur(a, sigma_m):
    """Üç kez kutu bulanıklığı ≈ Gauss (kenarlar tekrarlı)."""
    r = max(1, int(round(sigma_m / STEP * 0.9)))
    out = a.astype(np.float64)
    for ax in (0, 1):
        for _ in range(3):
            pad = [(0, 0), (0, 0)]; pad[ax] = (r + 1, r)
            p = np.pad(out, pad, mode='edge'); c = np.cumsum(p, axis=ax)
            if ax == 0: out = (c[2 * r + 1:, :] - c[:-2 * r - 1, :]) / (2 * r + 1)
            else: out = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return out.astype(np.float32)

def TV_h_at(h, p):
    return float(h[int(round((p[1] - Z0) / STEP)), int(round((p[0] - X0) / STEP))])

def blobs_sd(x, z, circles, k=6.0):
    """Daire birleşimi (yumuşak): içeride pozitif, metre."""
    acc = None
    for (cx, cz, r) in circles:
        d = r - np.hypot(x - cx, z - cz)
        acc = d if acc is None else np.log(np.exp(acc / k) + np.exp(d / k)) * k   # yumuşak maksimum
    return acc

def seg_dist(x, z, pts):
    best = np.full(x.shape, 1e9, np.float32); tpos = np.zeros(x.shape, np.float32); run = 0.0
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        vx, vz = bx - ax, bz - az; ll = vx * vx + vz * vz; L = math.sqrt(ll)
        t = np.clip(((x - ax) * vx + (z - az) * vz) / ll, 0, 1)
        d = np.hypot(x - (ax + vx * t), z - (az + vz * t))
        m = d < best; best = np.where(m, d, best); tpos = np.where(m, run + t * L, tpos); run += L
    return best, tpos, run

# ------------------------------------------------------------------ arazi

def build():
    xs = np.arange(X0, X1 + 1e-6, STEP, dtype=np.float32); zs = np.arange(Z0, Z1 + 1e-6, STEP, dtype=np.float32)
    X, Z = np.meshgrid(xs, zs)
    # kıyı çizgisi: elips + açısal gürültü + koylar / burunlar
    ang = np.arctan2(Z / 66.0, X / 80.0)
    wob = fbm(np.cos(ang) * 3 + 10, np.sin(ang) * 3 + 10, 1.0, 5, 4) * 0.10 + fbm(X, Z, 1 / 9.0, 6, 3) * 0.02
    rad = np.hypot(X / 80.0, Z / 66.0)
    sd_land = (1.0 + wob - rad) * 70.0
    for (cx, cz, r, k) in [(70, -44, 15, 5), (-82, -36, 13, 6), (8, -82, 20, 8), (-30, 74, 10, 4), (82, 30, 9, 4)]:   # koylar
        sd_land = -np.log(np.exp(-sd_land / k) + np.exp(-(np.hypot(X - cx, Z - cz) - r) / k)) * k
    for (cx, cz, r) in [(62, 50, 16), (-50, 58, 18), (-74, 6, 12)]:                                            # burunlar
        sd_land = np.log(np.exp(sd_land / 6) + np.exp((r - np.hypot(X - cx, Z - cz)) / 6)) * 6
    # kumsal genişliği (açıya göre): güney + güneybatı + koylar geniş, kayalık kıyılar dar
    def arc(a0, a1, soft=0.25):
        a = np.arctan2(Z, X)
        d = np.angle(np.exp(1j * (a - (a0 + a1) / 2)))
        return ss((a1 - a0) / 2 + soft, (a1 - a0) / 2 - soft * 0.2, np.abs(d))
    rd = math.radians
    beach_w = 1.5 + 13.0 * np.maximum.reduce([arc(rd(-120), rd(-60), 0.15), arc(rd(-200), rd(-160), 0.12) * 0.8]) + 3.0 * (fbm(X, Z, 1 / 30.0, 8, 2) > 0.15)
    cove = np.exp(-((X - 64) ** 2 + (Z + 38) ** 2) / (2 * 12 ** 2)); beach_w = np.maximum(beach_w, 14 * cove)
    beach_w = np.maximum(beach_w, 10 * np.exp(-((X - 76) ** 2 + (Z + 12) ** 2) / (2 * 14 ** 2)))   # sörf plajı
    beach_w = np.maximum(beach_w, 6 * np.exp(-((X - 70) ** 2 + (Z - 40) ** 2) / (2 * 8 ** 2)))     # fener altı küçük koy
    beach_w *= 1.0 + 0.25 * fbm(X, Z, 1 / 14.0, 9, 2)

    # alçak zemin: köy düzlüğü 2.4 m + batı çayır tepeleri (yumuşak) + hafif dalga
    low = 6.0 + 0.45 * fbm(X, Z, 1 / 18.0, 11, 3)
    for (cx, cz, hh, r) in [(-48, -6, 3.0, 11), (-56, 10, 4.5, 10), (-40, 12, 2.0, 8), (-62, -10, 1.8, 8), (-20, 8, 1.2, 9), (30, -46, -1.5, 8)]:
        low += hh * np.exp(-((X - cx) ** 2 + (Z - cz) ** 2) / (2 * r * r))
    # göl çukuru
    dl = np.hypot(X - LAKE['x'], Z - LAKE['z']) + 2.0 * fbm(X, Z, 1 / 6.0, 13, 2)
    low = np.where(dl < LAKE['r'] + 4, low - (low - (LAKE['level'] - 1.3)) * ss(LAKE['r'] + 3.5, LAKE['r'] - 2.5, dl), low)
    beachp = 1.25 * ss(0.0, 1.0, sd_land / np.maximum(beach_w, 1.0))                                 # kum yokuşu 0 → 1.25
    cliffm = sig((sd_land - beach_w - 1.2 * fbm(X, Z, 1 / 2.5, 17, 2) - 1.6 * fbm(X, Z, 1 / 7.0, 19, 2)) / 0.6)                       # kıyı yarı: kumsalın arkasında dik
    h = np.maximum(beachp, low * cliffm)

    # yüksek platolar (dik yar): ad, daireler, yükseklik, kenar genişliği, kıyı payı
    def warp(seed, amp=5.0, f=1 / 22.0, famp=0.85, ff=0.55):
        return (X + amp * fbm(X, Z, f, seed, 3) + famp * fbm(X, Z, ff, seed + 7, 2),
                Z + amp * fbm(X, Z, f, seed + 3, 3) + famp * fbm(X, Z, ff, seed + 9, 2))
    tables = [
        ('east_mid', [(40, 6, 15), (52, 16, 13), (30, -2, 8), (60, 0, 10), (46, 28, 12)], 11.0, 0.55, 1.5, 21),
        ('upper', [(-10, 30, 20), (14, 36, 17), (-26, 24, 10), (32, 34, 12), (2, 46, 14), (-20, 46, 10)], 16.0, 0.6, 1.0, 31),
        ('headland', [(58, 42, 15), (48, 48, 10), (66, 52, 10)], 18.5, 0.55, 0.8, 41),
        ('north_peak', [(20, 58, 13), (8, 60, 9), (30, 62, 9)], 21.5, 0.6, 1.0, 51),
        ('north_peak2', [(22, 60, 8), (14, 62, 6)], 26.0, 0.5, 1.0, 53),
        ('west_rocks', [(-64, 14, 5.5), (-58, 20, 4.5)], 12.0, 0.5, 1.5, 61),
        ('west_step', [(-66, -2, 7), (-72, 8, 6), (-52, 26, 7)], 10.0, 0.5, 1.0, 63),
        ('mid_step', [(22, 12, 6), (-30, 34, 7), (-44, 22, 5)], 12.5, 0.5, 2.0, 65),
        ('stack1', [(84, 8, 4.5)], 13.0, 0.45, None, 77),
        ('stack2', [(-20, 74, 4)], 11.0, 0.45, None, 79),
        ('stack3', [(76, -52, 3.2)], 8.0, 0.45, None, 83),
        ('spire1', [(9, 25, 11), (4, 22, 6)], 22.0, 0.5, 9, 71),
        ('spire2', [(10, 26, 7.2), (7, 28, 4.5)], 28.0, 0.45, 9, 73),
        ('spire3', [(11, 27, 4.2)], 34.0, 0.4, 9, 75),
    ]
    masks = {}; stacks = []
    for (name, circ, H, w, margin, seed) in tables:
        wx, wz = warp(seed, amp=3.0 if name.startswith('spire') else 5.0)
        sd = blobs_sd(wx, wz, circ, k=4.0)
        if margin is not None: sd = np.minimum(sd, sd_land - margin - beach_w * 0.15)
        m = sig(sd / w)
        Hn = H + 0.6 * fbm(X, Z, 1 / 10.0, seed + 1, 2)
        h = h + np.maximum(0, Hn - h) * m
        masks[name] = m
        if margin is None: stacks.append((Hn, m))
    # karlı zirve (kuzeybatı): sırtlı koni, denize kayalarla iner
    pk = (-44.0, 54.0); dpk = np.hypot(X - pk[0], (Z - pk[1]) * 1.15)
    ridge = 1 - np.abs(fbm(X, Z, 1 / 9.0, 81, 4)); cone = 38.0 * np.exp(-(dpk / 21.0) ** 1.6) * (0.82 + 0.3 * ridge)
    shoulder = 20.0 * np.exp(-((X + 30) ** 2 + (Z - 50) ** 2) / (2 * 11 ** 2))
    peak = np.maximum(cone, shoulder) * ss(-2.0, 6.0, sd_land)
    h = np.maximum(h, peak)
    # kayak pisti: zirveden güneydoğuya düzgün kar yokuşu, alt ucu kayak alanı düzlüğü
    pdk, ptk, plk = seg_dist(X + 0.8 * fbm(X, Z, 1 / 9.0, 85, 2), Z, [(-37, 41), (-40.5, 46.5), (-44, 52)])
    prof = 19.4 + (33.0 - 19.4) * (ptk / plk) ** 1.2
    wk = ss(6.5, 3.0, pdk) * ss(-2, 1, ptk) * ss(plk + 2, plk - 1, ptk)
    h = h + (prof - h) * wk
    # kanyon: festivalden kuzeye, kaya tepenin batısından dolanır; taban kum, kuzeye doğru yükselir
    cpts = [(-2, -2), (-3, 8), (-5, 18), (-8, 28), (-11, 38), (-13, 46)]
    cd, ct, clen = seg_dist(X + 1.5 * fbm(X, Z, 1 / 8.0, 91, 2), Z, cpts)
    cw = 6.5 + 2.0 * fbm(X, Z, 1 / 12.0, 93, 2) + 2.5 * ss(0, clen * 0.4, ct) * ss(clen, clen * 0.6, ct)
    floor = 6.3 + 9.0 * ss(clen * 0.15, clen * 1.0, ct) + 0.15 * fbm(X, Z, 1 / 3.0, 95, 2)
    cm = sig((cw - cd) / 0.6) * ss(-4, 2, ct)
    h = np.where(h > floor, h + (floor - h) * cm, h)
    # kanyon içi kaya sütunları (üstü çimli)
    for (px, pz, r, ph, seed) in [(-1, 14, 2.6, 14.0, 101), (-9, 31, 3.0, 17.0, 103), (-4, 25, 1.8, 12.5, 105)]:
        wx, wz = warp(seed, amp=1.2, famp=0.4)
        msk = sig((r - np.hypot(wx - px, wz - pz)) / 0.35)
        h = h + np.maximum(0, ph - h) * msk
    # tabakalar (yatay basamak çizgileri) + çatlak oluklar: yalnız dik yerlerde
    gz, gx = np.gradient(h, STEP); slope = np.hypot(gx, gz)
    tabm = np.maximum.reduce([m for k, m in masks.items()])
    steep = ss(0.8, 1.8, slope) * (1 - ss(14, 20, peak))
    st = 1.6 + 0.0 * X
    tt = h / st; fr = tt - np.floor(tt)
    terr = (np.floor(tt) + ss(0.62, 0.98, fr)) * st
    h = h + (terr - h) * steep * 0.55
    # patikalar: rampa (geniş bulanık yükseklik) + hafif çukur
    pd = np.full(X.shape, 1e9, np.float32)
    for p in PATHS: pd = np.minimum(pd, seg_dist(X, Z, p)[0])
    hb = blur(h, 6.0)
    pw = ss(6.5, 2.0, pd)
    h = h + (hb - h) * pw
    h -= 0.06 * ss(1.4, 0.4, pd)
    # karlı zirve patikası: kayak alanından zirveye dolanan, yamaca oyulmuş raf yol; iki yanında kar seti (oyunda yürünür)
    spts = SNOW_PATH; sdd, stt, sll = seg_dist(X, Z, spts)
    # yol profili: arazinin kendi yüksekliğini izler (az kazı), yalnız sürekli yükselir ve yumuşatılır
    cs, ch = [], []; run = 0.0
    for (ax, az), (bx, bz) in zip(spts[:-1], spts[1:]):
        L_ = math.hypot(bx - ax, bz - az); n = max(2, int(L_ / 0.5))
        for q in range(n):
            u = q / n; cs.append(run + u * L_); ch.append(TV_h_at(h, (ax + (bx - ax) * u, az + (bz - az) * u)))
        run += L_
    cs.append(run); ch.append(TV_h_at(h, spts[-1]) + 0.2)
    ch = np.maximum.accumulate(np.convolve(np.pad(ch, 6, mode='edge'), np.ones(13) / 13, mode='valid'))
    # oyunda yürünür: eğim en çok 0,6 (ileri geçiş sınırlar, geri geçiş sona yetiştirir; yol yamaca oyulur ya da hafif dolgu)
    ski = [r for r in REGIONS if r[0] == 'region_ski_hill'][0]
    padh_ = float(hb[int((ski[3] - Z0) / STEP), int((ski[2] - X0) / STEP)])          # raf kayak alanı yastığından başlar (basamak yok)
    for q in range(len(ch)):
        if cs[q] <= ski[5] * 0.8: ch[q] = padh_
    ds_ = np.diff(np.array(cs))
    for q in range(1, len(ch)): ch[q] = min(ch[q], ch[q - 1] + 0.6 * ds_[q - 1])
    for q in range(len(ch) - 2, -1, -1): ch[q] = max(ch[q], ch[q + 1] - 0.6 * ds_[q])
    sprof = np.interp(stt, np.array(cs), ch)
    alongm = ss(-1.0, 0.5, stt) * ss(sll + 1.5, sll - 0.5, stt)
    shelf = ss(3.2, 1.6, sdd) * alongm
    h = h + (sprof - h) * shelf
    h = h + 0.6 * np.exp(-((sdd - 1.9) / 0.5) ** 2) * alongm * ss(4.2, 2.0, sdd)       # kar setleri
    h = h - 0.22 * ss(1.4, 0.4, sdd) * alongm                                           # ortası sıkışmış çukur (iz)
    snowpath = (ss(1.65, 1.1, sdd) * alongm).astype(np.float32)
    # kum tepecikleri / birikintileri: kumsalda irili ufaklı yumuşak tümsekler
    beachm = np.clip(1.0 - ss(beach_w * 0.75, beach_w + 0.5, sd_land), 0, 1) * ss(0.25, 0.9, h) * ss(2.4, 1.6, h)
    mounds = 0.32 * ss(0.55, 0.85, fbm(X, Z, 1 / 3.2, 311, 3) * 0.5 + 0.5) + 0.12 * ss(0.5, 0.8, fbm(X, Z, 1 / 1.2, 313, 2) * 0.5 + 0.5)
    h = h + mounds * beachm
    # mağara tüneli: ağızdan yamaca 9 m giren yarık (tavanı tünel ağı kapatır)
    cv = [r for r in REGIONS if r[0] == 'region_cave'][0]; ya = math.radians(cv[6]); fxc, fzc = math.sin(ya), math.cos(ya)
    y0c = TV_h_at(h, (cv[2], cv[3]))
    tdd, ttt, tll = seg_dist(X, Z, [(cv[2] + fxc * 0.5, cv[3] + fzc * 0.5), (cv[2] - fxc * 9.5, cv[3] - fzc * 9.5)])
    trench = ss(2.6, 2.1, tdd) * ss(0.0, 0.8, ttt) * ss(tll + 0.5, tll - 0.5, ttt)
    h = np.where(trench > 0, h + (np.minimum(h, y0c - 0.15 - 0.06 * ttt) - h) * trench, h)
    # bina yastıkları (düz)
    for (rid, nm, rx, rz, shp, size, yaw) in REGIONS:
        if shp == 'pier' or rid in BEACH_REGIONS: continue
        dr = np.hypot(X - rx, Z - rz); padh = float(hb[int((rz - Z0) / STEP), int((rx - X0) / STEP)])
        h = h + (padh - h) * ss(size * 0.75 + 2.5, size * 0.6, dr) * (1 - shelf * ss(size * 0.55, size * 0.75, dr))   # karlı patika rafı yastıkla ezilmez (oyunda yürünür eğim)
    # deniz tabanı
    sea = sd_land < 0
    depth = SEA_FLOOR * ss(0, 30, -sd_land) - 0.8 * ss(0, 3, -sd_land)
    h = np.where(sea, np.minimum(h, depth + (h - depth) * ss(-1.5, 0, sd_land)), h)
    for (Hn, m) in stacks: h = h + np.maximum(0, Hn - h) * m     # denizdeki kaya sütunları
    # açıkta küçük ada (kumsaldan görünür): alçak kum tepe, ortası çimen
    di = np.hypot(X - ISLET[0], (Z - ISLET[1]) * 1.25) + 1.5 * fbm(X, Z, 1 / 5.0, 301, 2)
    h = np.maximum(h, -0.6 + 2.6 * ss(ISLET[2] + 2.5, ISLET[2] * 0.25, di))
    h = h.astype(np.float32)
    gz, gx = np.gradient(h, STEP); slope = np.hypot(gx, gz).astype(np.float32)
    # yüzey katmanları
    sand = np.clip(1.0 - ss(beach_w * 0.8, beach_w + 1.0, sd_land), 0, 1) * (h < 2.2)
    sand = np.maximum(sand, cm * ss(1.0, 0.6, slope) * 0.9)                         # kanyon tabanı kum
    lake_m = (np.hypot(X - LAKE['x'], Z - LAKE['z']) < LAKE['r'] + 5) & (h < LAKE['level'])
    path = ss(1.6, 0.9, pd)
    snow = ss(16.5, 19.0, h + 2.5 * fbm(X, Z, 1 / 7.0, 111, 3)) * ss(-15, -26, X) * ss(31, 38, Z)
    snow = np.maximum(snow, ss(12.0, 8.0, np.hypot(X + 38, Z - 40)) * (h > 17.5))     # kayak alanı düzlüğü karlı
    out = dict(h=h, slope=slope, sand=sand.astype(np.float32), path=path.astype(np.float32), snow=snow.astype(np.float32),
               coast=sd_land.astype(np.float32), canyon=cm.astype(np.float32), snowpath=snowpath, lake=lake_m, pathd=pd.astype(np.float32))
    for k, v in masks.items(): out['t_' + k] = v.astype(np.float32)
    return out

def layout_json():
    regs = [dict(id=r[0], name=r[1], pos=[r[2], r[3]], shape=r[4], size=r[5], yaw=r[6]) for r in REGIONS]
    return dict(regions=regs, plaza=list(PLAZA), spots={k: list(v) for k, v in SPOTS.items()}, paths=[[list(p) for p in P] for P in PATHS],
                lake=LAKE, grid=dict(step=STEP, x0=X0, x1=X1, z0=Z0, z1=Z1))

def height_at(T, x, z):
    fi = (x - X0) / STEP; fj = (z - Z0) / STEP; i = int(fi); j = int(fj); tx = fi - i; tz = fj - j; h = T['h']
    return float((h[j, i] * (1 - tx) + h[j, i + 1] * tx) * (1 - tz) + (h[j + 1, i] * (1 - tx) + h[j + 1, i + 1] * tx) * tz)

def preview(T, path):
    from PIL import Image
    h = T['h']; sl = T['slope']
    col = np.zeros(h.shape + (3,), np.float32)
    grass = np.stack([0.42 + 0.02 * h, 0.72 - 0.005 * h, 0.28 + 0.0 * h], -1)
    col[:] = grass
    rock = np.array([0.66, 0.6, 0.62]) * (0.75 + 0.25 * np.clip(h / 25, 0, 1))[..., None]
    rw = ss(0.9, 1.4, sl)[..., None]; col = col * (1 - rw) + rock * rw
    sw = T['sand'][..., None]; col = col * (1 - sw) + np.array([0.93, 0.85, 0.66]) * sw
    pw = T['path'][..., None] * 0.8; col = col * (1 - pw) + np.array([0.72, 0.55, 0.36]) * pw
    snw = T['snow'][..., None]; col = col * (1 - snw) + np.array([0.96, 0.97, 1.0]) * snw
    wat = (h < 0)[..., None]; dep = np.clip(-h / 7, 0, 1)[..., None]
    col = np.where(wat, np.array([0.35, 0.85, 0.85]) * (1 - dep) + np.array([0.1, 0.4, 0.7]) * dep, col)
    col = np.where(T['lake'][..., None], np.array([0.3, 0.7, 0.8]), col)
    # tepe gölgelemesi
    gz, gx = np.gradient(h, STEP); shade = np.clip(0.8 + (-gx * 0.5 + gz * 0.5) * 0.35, 0.45, 1.2)[..., None]
    col = np.clip(col * shade, 0, 1)
    img = Image.fromarray((col[::-1] * 255).astype(np.uint8)).resize((1000, 880))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(img); sx = 1000 / (X1 - X0); sz = 880 / (Z1 - Z0)
    for r in REGIONS:
        u = (r[2] - X0) * sx; v = (Z1 - r[3]) * sz; dr.ellipse((u - 5, v - 5, u + 5, v + 5), fill=(255, 60, 60)); dr.text((u + 7, v - 6), r[1], fill=(0, 0, 0))
    img.save(path)

if __name__ == '__main__':
    T = build()
    np.savez_compressed(sys.argv[1], **T)
    json.dump(layout_json(), open(os.path.splitext(sys.argv[1])[0] + '_layout.json', 'w'), ensure_ascii=False, indent=1)
    print('grid', T['h'].shape, 'h', float(T['h'].min()), float(T['h'].max()))
    for r in REGIONS: print(r[0], round(height_at(T, r[2], r[3]), 2))
    if len(sys.argv) > 2: preview(T, sys.argv[2])
