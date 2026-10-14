# Pofi/Sky v3 (stilize, oyunun çizgi film 3B tarzına uygun): açık mavi geçiş, net kenarlı iki tonlu yuvarlak bulut kümeleri
# (açısal hücrelerde metaball), küçük yumuşak güneş, kuş sürüleri. PofiSky.shader ile birebir aynı matematik.
# Kullanım: python3 sky_preview.py <klasör>  (klasörde cams.json + r_<sahne>.png: Blender'da şeffaf arka planla çizilmiş ada)
import json, math, sys, numpy as np
from PIL import Image, ImageDraw
D = sys.argv[1]; CAMS = json.load(open(D + '/cams.json'))
def s2l(c): c = np.array(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
P = dict(Zenith=s2l([0.33, 0.66, 0.97]), Mid=s2l([0.52, 0.80, 1.0]), Horizon=s2l([0.76, 0.92, 1.0]), Ground=s2l([0.45, 0.75, 0.95]),
         Lit=s2l([1.0, 1.0, 1.0]), Shade=s2l([0.80, 0.87, 0.98]), Deep=s2l([0.66, 0.77, 0.95]))
rx, rz = math.radians(50), math.radians(-30)
b = np.array([math.sin(rz) * math.sin(rx), -math.cos(rz) * math.sin(rx), math.cos(rx)])
L = np.array([b[0], b[2], b[1]]); L /= np.linalg.norm(L)
def ss(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def h1(n): return np.modf(np.sin(n * 91.345 + 47.0) * 43758.5453)[0] % 1.0
def smin(a, b, k): h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b + (a - b) * h - k * h * (1 - h)
PUFFS = [(-1.05, 0.02, 0.36), (-0.6, 0.26, 0.48), (-0.08, 0.5, 0.6), (0.48, 0.36, 0.5), (0.95, 0.1, 0.38), (0.2, 0.02, 0.46), (-0.35, 0.0, 0.42)]

def layer(az, el, cells, el0, el1, size, seed, T, aa):
    """Bir bulut sırası: azimut hücreleri; her hücrede %65 olasılıkla 1 bulut. Döner: alfa, ton (0 gölge..1 aydınlık)."""
    x = az / (2 * math.pi) * cells + T
    alpha = np.zeros_like(az); tone = np.ones_like(az)
    for dc in (-1, 0, 1):
        c = np.floor(x) + dc; cw = c - cells * np.floor(c / cells); r = lambda k: h1(cw * 13.1 + seed * 7.7 + k)
        on = r(0) < 0.65
        cx = c + 0.2 + r(1) * 0.6; ce = el0 + (el1 - el0) * r(2); s = size * (0.5 + r(3) * 1.0)
        px = (x - cx) * (2 * math.pi / cells) * np.cos(el) / s; py = (el - ce) / s
        cloudAz = (cx - T) / cells * 2 * math.pi; sunx = np.where(np.sin(math.atan2(L[0], L[2]) - cloudAz) > 0, 0.35, -0.35)
        # her bulut özgün: yarı genişlik, kabarıklık (yükseklik) ve tümsek sayısı buluta göre değişir
        Wd = 0.45 + r(5) * 1.2; Hh = 0.12 + r(6) ** 1.5 * 0.9; n = np.minimum(8, np.maximum(3 + np.floor(r(7) * 4), np.ceil(Wd * 3.2)))
        sp = 2 * Wd / n
        # gövde: tümsekleri birleştiren yatay kapsül (düz tabanlı)
        rb = 0.2 + 0.12 * Hh
        qx = np.clip(px, -Wd * 0.8, Wd * 0.8); body = np.sqrt((px - qx) ** 2 + (py - 0.06) ** 2) - rb
        dist = body; lt = np.ones_like(az)
        # ressam sırası: ortadaki (yüksek, arkadaki) tümsekten kenarlara (alçak, öndeki); öndekinin aydınlık tepesi
        # arkadakinin gölgeli altının üstüne biner → çizgi film bulut kıvrımları
        mid = np.floor(n / 2)
        for k in range(8):
            on_i = k < n
            i = mid + np.where(k % 2 == 1, -(k + 1) // 2, k // 2)
            u = ((i + 0.5) / n) * 2 - 1 + (r(20 + i) - 0.5) * 0.6 / n
            ox = u * Wd
            rr = np.maximum(sp * 0.72, (0.24 + 0.2 * r(40 + i)) * (0.7 + Hh * 0.6)) * (1 - 0.3 * np.abs(u))
            oy = np.minimum(Hh * (1 - u * u) * (0.55 + 0.7 * r(30 + i)), rb + rr * (0.5 + Hh * 0.9))
            dd = np.where(on_i, np.sqrt((px - ox) ** 2 + (py - oy) ** 2) - rr, 9.0)
            dist = smin(dist, dd, 0.08)
            cov = ss(0.02, -0.02, dd)
            lt = lt + (ss(-0.6, 0.3, (py - oy) / rr + (px - ox) / rr * sunx) - lt) * cov
        cov = ss(0.02, -0.02, body)
        lt = lt + (ss(-1.0, 0.7, (py - 0.06) / rb) - lt) * cov * ss(0.0, -0.15, py - 0.06)   # gövdenin alt yarısı en önde
        dist = np.maximum(dist, -(py + 0.1))                                    # düz taban
        a = (1 - ss(-aa / s, aa / s, dist)) * on
        tt = lt * ss(-0.1, 0.05, py)                                           # taban şeridi gölgede
        alpha, tone = np.maximum(alpha, a), np.where(a > alpha, tt, tone)
    return alpha, tone

def sky(d, T=0.0, aa=0.0025):
    h = d[..., 1]; hp = np.clip(h, 0, 1); el = np.arcsin(np.clip(h, -1, 1)); az = np.arctan2(d[..., 0], d[..., 2])
    t1 = ss(0.0, 0.3, hp)[..., None]; t2 = ss(0.2, 1.0, hp)[..., None]
    col = P['Horizon'] * (1 - t1) + P['Mid'] * t1; col = col * (1 - t2) + P['Zenith'] * t2
    mu = np.clip((d * L).sum(-1), -1, 1)
    col = col * (0.95 + 0.08 * ((mu * 0.5 + 0.5) ** 2))[..., None]
    below = h < 0
    e = np.exp(h[below] * 8)[:, None]; col[below] = P['Horizon'][None] * e + P['Ground'][None] * (1 - e)
    # güneş: yumuşak kenarlı yuvarlak disk + geniş, hafif hale (stilize)
    ang = np.arccos(np.clip(mu, -1, 1))
    col = col + np.array([1.0, 0.95, 0.82]) * ((1 - ss(0.022, 0.03, ang)) * 0.9 + np.exp(-ang * 9) * 0.12)[..., None]
    # bulut sıraları: uzak/alçak küçükler (ufka karışır), yakın/yüksek büyükler
    for cells, e0, e1, size, seed, mix in ((20, 0.025, 0.05, 0.03, 1, 0.35), (11, 0.05, 0.11, 0.065, 2, 0.14), (7, 0.13, 0.35, 0.1, 3, 0.0)):
        a, t = layer(az, el, cells, e0, e1, size, seed, T * 0.01, aa)
        cc = P['Shade'] * (1 - t[..., None]) + P['Lit'] * t[..., None]
        cc = cc * (1 - mix) + P['Horizon'] * mix                                 # uzaktakiler havaya karışır
        col = col * (1 - a[..., None]) + cc * a[..., None]
    return col

def birds(img, cam, seed):
    W, H = img.size; dr = ImageDraw.Draw(img, 'RGBA'); rng = np.random.default_rng(seed)
    R = np.array(cam['rot']); f = H / 2 / math.tan(cam['angle_y'] / 2)
    for flock in range(2):
        ang = rng.uniform(0.12, 0.42) * (1 if flock else -1); el = rng.uniform(0.1, 0.18); dist = rng.uniform(35, 70)
        fw = R @ np.array([0, 0, -1.0]); yaw = math.atan2(fw[0], fw[1]) + ang
        c = np.array([math.sin(yaw) * dist, math.cos(yaw) * dist, el * dist]) + np.array(cam['loc'])
        for i in range(rng.integers(3, 5)):
            p = c + np.array([-(i % 2 * 2 - 1) * (i + 1) // 2 * 1.4, rng.uniform(-0.6, 0.6), -((i + 1) // 2) * 0.9])
            q = R.T @ (p - np.array(cam['loc']))
            if q[2] >= -1: continue
            sx, sy = W / 2 + f * q[0] / -q[2], H / 2 - f * q[1] / -q[2]
            s = 0.85 / -q[2] * f; flap = math.sin(rng.uniform(0, 6.28)) * 0.3
            for side in (-1, 1):                                                  # yumuşak yay kanatlar (karikatür "m")
                dr.arc((sx + (side - 1) * s * 0.5, sy - s * (0.35 + flap), sx + (side + 1) * s * 0.5, sy + s * (0.35 - flap)), 200, 340, fill=(52, 70, 104, 230), width=max(3, int(s * 0.2)))

out = []
for name, cam in CAMS.items():
    fg = Image.open(f"{D}/r_{name}.png").convert('RGBA'); W, H = fg.size
    R = np.array(cam['rot']); f = H / 2 / math.tan(cam['angle_y'] / 2)
    yy, xx = np.mgrid[0:H, 0:W]
    v = np.stack([(xx - W / 2) / f, -(yy - H / 2) / f, -np.ones_like(xx, float)], -1)
    wb = v @ R.T; wb /= np.linalg.norm(wb, axis=-1, keepdims=True)
    d = np.stack([wb[..., 0], wb[..., 2], wb[..., 1]], -1)
    bg = Image.fromarray((l2s(sky(d, aa=1.2 / f)) * 255).astype(np.uint8)).convert('RGBA')
    birds(bg, cam, abs(hash(name)) % 1000)
    bg.alpha_composite(fg); bg.convert('RGB').save(f"{D}/v3_{name}.jpg", quality=90); out.append(bg.convert('RGB'))
H2 = sum(i.height for i in out) // 2; W2 = out[0].width // 2
sheet = Image.new('RGB', (W2, H2)); y = 0
for i in out: sheet.paste(i.resize((W2, i.height // 2)), (0, y)); y += i.height // 2
sheet.save(f"{D}/v3_sheet.jpg", quality=88)
