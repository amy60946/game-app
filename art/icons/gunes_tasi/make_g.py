"""G = mevcut Güneş Taşı simgesinin geliştirilmiş hali (kredisiz, görüntü işleme, OKLab).
- Taş: %22 büyür; içteki küçük koyu leke temizlenir; alt-sağ gölge derinleşir (daha koyu, daha turuncu),
  merkezde sıcak iç ışıma, sol üstte net parlama, alt-sağ iç kenarda yumuşak geri yansıma.
- Işınlar: ince ve kopuk 8 çizgi yerine taşa yakın, kalın, yuvarlak uçlu 8 bal rengi "vinyl" çubuk
  (sol üstten ışık, yumuşak gölgeleme, parlama; dış çizgi yok).
Kullanım: python3 make_g.py <mevcut.png> <çıktı.png>
"""
import sys

import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
S = 4                 # ışınları yüksek çözünürlükte çiz, sonra küçült (yumuşak kenar)
N = 256


def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717876, -0.8086757248]])
iM1, iM2 = np.linalg.inv(M1), np.linalg.inv(M2)


def to_lab(rgb): return np.cbrt(s2l(rgb) @ M1.T) @ M2.T


def to_lin(lab): return ((lab @ iM2.T) ** 3) @ iM1.T


def to_srgb(lab):
    """Renk uzayı dışına taşanı açıklık ve ton aynı kalacak şekilde doygunluktan kırp."""
    L, ab = lab[..., :1], lab[..., 1:]
    lo, hi = np.zeros(L.shape), np.ones(L.shape)
    for _ in range(18):
        s = (lo + hi) / 2
        lin = to_lin(np.concatenate([L, ab * s], -1))
        g = np.all((lin >= -1e-4) & (lin <= 1 + 1e-4), -1, keepdims=True)
        lo, hi = np.where(g, s, lo), np.where(g, hi, s)
    lin = to_lin(lab)
    ok = np.all((lin >= -1e-4) & (lin <= 1 + 1e-4), -1, keepdims=True)
    return l2s(to_lin(np.concatenate([L, ab * np.where(ok, 1.0, lo)], -1)))


def lch(L, C, h_deg):
    h = np.deg2rad(h_deg)
    return np.stack([L, C * np.cos(h), C * np.sin(h)], -1)


src = np.asarray(Image.open(SRC).convert("RGBA")).astype(np.float64) / 255
al = src[..., 3]

# --- 1) taşı ayır (merkezdeki büyük parça; ışınlar r > 74 px'te) ---
yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
cx = cy = 126.6
r = np.hypot(xx - cx, yy - cy)
gem_a = np.where(r < 74.5, al, 0.0)
gem_rgb = src[..., :3]

# içteki küçük koyu lekeyi (sol altta, 88,165 -> 106,152 çizgisi) temizle: maskeli bulanıklıkla doldur
def gblur(x, r):
    n = int(np.ceil(3 * r))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / r) ** 2); k /= k.sum()
    p = np.pad(x, n, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 1, p)


p0, p1 = np.array([88.0, 166.0]), np.array([107.0, 151.0])
dv = p1 - p0
tt = np.clip(((xx - p0[0]) * dv[0] + (yy - p0[1]) * dv[1]) / (dv @ dv), 0, 1)
dd = np.hypot(xx - (p0[0] + tt * dv[0]), yy - (p0[1] + tt * dv[1]))
spot = np.clip((6.5 - dd) / 2.5, 0, 1)
wgt = (1 - spot) * (gem_a > 0.99)
fill = np.stack([gblur(gem_rgb[..., k] * wgt, 4) for k in range(3)], -1) / np.maximum(gblur(wgt, 4)[..., None], 1e-4)
gem_rgb = gem_rgb * (1 - spot[..., None]) + np.clip(fill, 0, 1) * spot[..., None]

# --- 2) taşı %12 büyüt (önçarpımlı) ---
K = 1.12


def scale_rgba(rgb, a, k):
    pm = np.concatenate([rgb * a[..., None], a[..., None]], -1)
    big = int(round(N * k))
    ch = [np.asarray(Image.fromarray(pm[..., i].astype(np.float32), "F").resize((big, big), Image.LANCZOS)) for i in range(4)]
    o = (big - N) // 2
    ch = [c[o:o + N, o:o + N] for c in ch]
    A = np.clip(ch[3], 0, 1)
    RGB = np.stack(ch[:3], -1) / np.maximum(A[..., None], 1e-4)
    return np.clip(RGB, 0, 1), A


g_rgb, g_a = scale_rgba(gem_rgb, gem_a, K)
_big = int(round(N * K))
c2 = cx * _big / N - (_big - N) // 2     # taşın yeni merkezi
gx, gy = (xx - c2), (yy - c2)
R = 60.0 * K                          # taşın yarıçapı (~73 px)
nx, ny = gx / R, gy / R
rr = np.clip(np.hypot(nx, ny), 0, 1.2)

# kenarı netleştir (büyütmenin yumuşattığı alfa) + hafif keskinleştirme
g_a = np.clip((g_a - 0.12) / 0.76, 0, 1)
g_a = g_a * g_a * (3 - 2 * g_a)

# --- 3) OKLab gölgeleme ---
lab = to_lab(g_rgb)
L, A_, B_ = lab[..., 0], lab[..., 1], lab[..., 2]
L = L + 0.55 * (L - gblur(L, 1.2)) * (g_a > 0.98)
C = np.hypot(A_, B_)
h = np.rad2deg(np.arctan2(B_, A_))
diag = np.clip((nx + ny) / np.sqrt(2), -1, 1)            # -1 sol üst … +1 sağ alt
shade = np.clip((diag + 0.1) / 1.0, 0, 1) ** 1.3 * np.clip(rr / 0.95, 0, 1) ** 0.8
L = L - 0.10 * shade                                       # derin gölge
h = h - 9 * shade                                          # gölgede daha turuncu/kehribar
C = C * (1 + 0.18 * shade)
glow = np.exp(-((nx + 0.05) ** 2 + (ny + 0.02) ** 2) / (2 * 0.36 ** 2))
L = L + 0.065 * glow                                       # sıcak iç ışıma
h = h + 6 * glow                                           # merkez bala/sarıya
C = C * (1 + 0.10 * glow)
# alt-sağ iç kenarda geri yansıma (ışık taşın içinden kenara vurur)
bounce = np.exp(-((rr - 0.80) / 0.07) ** 2) * np.clip((diag - 0.25) / 0.6, 0, 1)
L = L + 0.06 * bounce
h = h + 8 * bounce
# sol üstte net parlama (yumuşak elips)
ex, ey = nx + 0.42, ny + 0.46
rx, ry = (ex * 0.80 + ey * 0.60) / 0.26, (-ex * 0.60 + ey * 0.80) / 0.13
spec = np.clip(1 - (rx ** 2 + ry ** 2), 0, 1) ** 1.6
L = L * (1 - 0.85 * spec) + 0.985 * 0.85 * spec
C = C * (1 - 0.85 * spec)
dot = np.clip(1 - (((nx + 0.18) / 0.065) ** 2 + ((ny + 0.60) / 0.045) ** 2), 0, 1) ** 1.4
L = L * (1 - 0.8 * dot) + 0.98 * 0.8 * dot
C = C * (1 - 0.8 * dot)
g_out = to_srgb(lch(np.clip(L, 0, 1), C, h))

# --- 4) ışınlar: kalın, yuvarlak uçlu, vinyl gölgeli çubuklar ---
NS = N * S
Y, X = np.mgrid[0:NS, 0:NS].astype(np.float64) / S
r_in, r_out, half_w = 84.0, 104.0, 8.8
ray_a = np.zeros((NS, NS))
ray_L = np.zeros((NS, NS))
ray_spec = np.zeros((NS, NS))
ray_soft = np.zeros((NS, NS))
light = np.array([-0.52, -0.62, 0.58]); light /= np.linalg.norm(light)
for k in range(8):
    ang = np.deg2rad(-90 + 45 * k)
    d = np.array([np.cos(ang), np.sin(ang)])
    p0 = np.array([c2, c2]) + d * r_in
    p1 = np.array([c2, c2]) + d * r_out
    vx, vy = X - p0[0], Y - p0[1]
    t = np.clip((vx * d[0] + vy * d[1]) / (r_out - r_in), 0, 1)
    qx, qy = p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])
    dx, dy = X - qx, Y - qy
    w = half_w * (1.06 - 0.12 * t)                         # içte biraz daha kalın
    dist = np.hypot(dx, dy)
    inside = dist < w
    a = np.clip((w - dist) * S / 1.2, 0, 1)                # yumuşak kenar
    # kapsül yüzeyinin normali
    q = np.clip(dist / w, 0, 0.999)
    nz = np.sqrt(1 - q ** 2)
    nxx, nyy = np.where(dist > 0, dx / np.maximum(dist, 1e-6), 0) * q, np.where(dist > 0, dy / np.maximum(dist, 1e-6), 0) * q
    lam = np.clip(nxx * light[0] + nyy * light[1] + nz * light[2], 0, 1)
    hv = light + np.array([0, 0, 1.0]); hv /= np.linalg.norm(hv)
    sp = np.clip(nxx * hv[0] + nyy * hv[1] + nz * hv[2], 0, 1) ** 40
    sel = a > ray_a
    ray_a = np.where(sel, a, ray_a)
    ray_L = np.where(sel, lam, ray_L)
    ray_spec = np.where(sel, sp, ray_spec)
    ray_soft = np.where(sel, np.clip(nxx * hv[0] + nyy * hv[1] + nz * hv[2], 0, 1) ** 10, ray_soft)
# bal-amber renk: aydınlıkta bal sarısı, gölgede kehribar turuncu (taşla aynı aile, yıldızdan daha turuncu)
rl = 0.58 + 0.30 * ray_L ** 1.2
rh = 55 + 22 * ray_L
rc = 0.165 - 0.035 * ray_L
rl = rl * (1 - 0.8 * ray_spec) + 0.97 * 0.8 * ray_spec
rc = rc * (1 - 0.8 * ray_spec)
rl = rl + 0.10 * ray_soft
rc = rc * (1 - 0.25 * ray_soft)
ray_rgb = to_srgb(lch(rl, rc, rh))
# küçült
def down(x):
    return np.asarray(Image.fromarray(x.astype(np.float32), "F").resize((N, N), Image.BOX))
ra = down(ray_a)
rrgb = np.stack([down(ray_rgb[..., i] * ray_a) for i in range(3)], -1) / np.maximum(ra[..., None], 1e-4)

# --- 5) birleştir: ışınlar altta, taş üstte ---
out_a = g_a + ra * (1 - g_a)
out_rgb = (g_out * g_a[..., None] + rrgb * ra[..., None] * (1 - g_a[..., None])) / np.maximum(out_a[..., None], 1e-4)
o = np.concatenate([np.clip(out_rgb, 0, 1), np.clip(out_a, 0, 1)[..., None]], -1)
Image.fromarray(np.round(o * 255).astype(np.uint8), "RGBA").save(OUT)
ys, xs = np.nonzero(out_a > 0.02)
print(OUT, 'K', K, "sınır", xs.min(), ys.min(), xs.max(), ys.max())
