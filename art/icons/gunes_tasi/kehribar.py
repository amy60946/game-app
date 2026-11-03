"""Kehribar + güneş taşı (oligoklaz) karışımı Güneş Taşı simgeleri — yalnız kodla, OKLab.
K1: G biçimi (taş + ışınlar), orta kehribar, az benek.
K2: G'nin taşı oval çakıl, ışınsız, derin kehribar (bal merkez -> kızıl kenar), orta benek + hava kabarcığı.
K3: T3 kesme taş, şeftali-kızıl güneş taşı, yoğun benek.
K4: T4 gövdesi, derin kehribar kaya + ışık sızan çatlaklar, az benek.
Kullanım: python3 kehribar.py <gunes_tasi klasörü>
"""
import os
import sys

import numpy as np
from PIL import Image

from oklab import lch, to_lch, to_srgb

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "icons")
N = 256
BOX = 226


# ---------- yardımcılar ----------
def load(path):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(np.float64) / 255
    return a[..., :3].copy(), a[..., 3].copy()


def shift_or(m):
    o = m.copy()
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def edge_dist(mask, maxr=80):
    """Kenara uzaklık (px, 4-komşu aşındırma sayısı)."""
    d = np.zeros(mask.shape)
    cur = mask.copy()
    for i in range(maxr):
        if not cur.any():
            break
        d += cur
        cur = ~shift_or(~cur)
    return d


def gblur(x, r):
    n = int(np.ceil(3 * r))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / r) ** 2); k /= k.sum()
    p = np.pad(x, n, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 1, p)


def resample(rgb, a, M, size):
    """Önçarpımlı afin dönüşüm. M: çıktı (x,y) -> girdi (x,y) için PIL katsayıları."""
    pm = np.concatenate([rgb * a[..., None], a[..., None]], -1)
    ch = [np.asarray(Image.fromarray(pm[..., i].astype(np.float32), "F")
                     .transform(size, Image.AFFINE, M, resample=Image.BICUBIC)) for i in range(4)]
    A = np.clip(ch[3], 0, 1)
    RGB = np.stack(ch[:3], -1) / np.maximum(A[..., None], 1e-4)
    return np.clip(RGB, 0, 1), A


def fit_canvas(rgb, a, box=BOX):
    """Nesneyi 256 tuvalin ortasına, en uzun kenarı box olacak şekilde yerleştir."""
    ys, xs = np.nonzero(a > 0.02)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    s = box / max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # çıktı (u,v) -> girdi: x = (u - N/2)/s + cx
    M = (1 / s, 0, cx - (N / 2) / s, 0, 1 / s, cy - (N / 2) / s)
    return resample(rgb, a, M, (N, N))


def smooth_alpha(a):
    a = np.clip((a - 0.10) / 0.80, 0, 1)
    return a * a * (3 - 2 * a)


def save(rgb, a, name):
    o = np.concatenate([np.clip(rgb, 0, 1), np.clip(a, 0, 1)[..., None]], -1)
    Image.fromarray(np.round(o * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, name + ".png"))
    ys, xs = np.nonzero(a > 0.02)
    print(name, "sınır", xs.min(), ys.min(), xs.max(), ys.max())


# ---------- kehribar gövde ----------
def amberize(rgb, a, region, P):
    """region içinde kehribar/güneş taşı rengine boya. P: palet ve ayarlar."""
    H, W = a.shape
    L0, C0, h0 = to_lch(rgb)
    m = region & (a > 0.5)
    lo, hi = np.percentile(L0[m], 4), np.percentile(L0[m], 97)
    t = np.clip((L0 - lo) / max(hi - lo, 1e-3), 0, 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    ys, xs = np.nonzero(m)
    cx, cy = xs.mean(), ys.mean()
    R = np.sqrt(m.sum() / np.pi)
    nx, ny = (xx - cx) / R, (yy - cy) / R
    rr = np.hypot(nx, ny)
    diag = np.clip((nx + ny) / np.sqrt(2), -1.5, 1.5)
    d = edge_dist(region & (a > 0.35))

    L = P["Lmin"] + (P["Lmax"] - P["Lmin"]) * t ** P.get("gamma", 1.0)
    # kenarlık: kenarda 1, içe doğru 0 (kehribar kenara doğru koyulaşır, kızıllaşır)
    q = np.clip(1 - d / (P.get("rim_w", 0.55) * R), 0, 1) ** 1.3
    hc, he = P["hue"]
    h = hc - (hc - he) * q - P.get("shade_h", 8) * (1 - t)
    C = P["C"] * (0.92 + 0.12 * q)
    L = L - P.get("rim_L", 0.07) * q ** 1.5
    # merkezden sıcak iç ışıma (ışığın geçtiği yer: biraz sağ alt)
    gx, gy = nx - P.get("glow_dx", 0.10), ny - P.get("glow_dy", 0.14)
    glow = np.exp(-(gx ** 2 + gy ** 2) / (2 * P.get("glow_s", 0.42) ** 2))
    L = L + P.get("glow_L", 0.12) * glow * (1 - 0.5 * t)
    h = h + P.get("glow_h", 6) * glow
    C = C + 0.015 * glow
    # sağ alt iç kenarda geri yansıma (yarı saydamlık hissi)
    bounce = np.exp(-((rr - 0.74) / 0.10) ** 2) * np.clip((diag - 0.2) / 0.7, 0, 1)
    L = L + P.get("bounce", 0.06) * bounce
    h = h + 8 * bounce
    # parlak yansımalar özgün görüntüden: çok parlak yerler beyazımsı kalsın
    spec0 = np.clip((L0 - P.get("spec_from", 0.90)) / 0.06, 0, 1)
    L = L * (1 - spec0) + np.maximum(L, L0) * spec0
    C = C * (1 - 0.75 * spec0)
    new = to_srgb(lch(np.clip(L, 0, 1), C, h))
    keep = (region & (a > 0))[..., None]
    return np.where(keep, new, rgb), dict(cx=cx, cy=cy, R=R, d=d, nx=nx, ny=ny)


def specular(rgb, a, g, ex=-0.42, ey=-0.46, sx=0.26, sy=0.12, ang=37, k=0.85, dot=True):
    """Sol üstte net parlama (yumuşak elips) + küçük nokta."""
    L, C, h = to_lch(rgb)
    nx, ny = g["nx"], g["ny"]
    r = np.deg2rad(ang)
    u, v = nx - ex, ny - ey
    rx, ry = (u * np.cos(r) + v * np.sin(r)) / sx, (-u * np.sin(r) + v * np.cos(r)) / sy
    sp = np.clip(1 - (rx ** 2 + ry ** 2), 0, 1) ** 1.5 * k
    if dot:
        dd = np.clip(1 - (((nx - ex - 0.30) / 0.06) ** 2 + ((ny - ey - 0.16) / 0.045) ** 2), 0, 1) ** 1.4 * 0.8
        sp = np.maximum(sp, dd)
    sp = sp * (a > 0.5)
    L = L * (1 - sp) + 0.985 * sp
    C = C * (1 - sp)
    return to_srgb(lch(np.clip(L, 0, 1), C, h))


def flecks(rgb, a, g, n, seed, region, size=(5.5, 9.0), aspect=(1.4, 2.0), bright=0.70, micro=2.0,
           keep_out=None, S=4, hue=48, opac=0.95):
    """Güneş taşı aventürsansı: serpiştirilmiş metal pullar (yüksek çözünürlükte çizilir).
    Pulların bir kısmı ışığı yakalar (parlak altın + beyaz parıltı + ışıma), çoğu koyu bakır/hematit.
    micro: pul başına kaç küçük ışıltı noktası."""
    rng = np.random.default_rng(seed)
    H, W = a.shape
    R = g["R"]
    ok = region & (g["d"] > 0.16 * R) & (a > 0.99)
    if keep_out is not None:
        ok &= ~keep_out
    ys, xs = np.nonzero(ok)

    def sample(k, min_d, pts):
        tries = 0
        while k > 0 and tries < 8000:
            tries += 1
            i = rng.integers(len(xs))
            p = np.array([xs[i] + rng.random(), ys[i] + rng.random()])
            if all(np.hypot(*(p - q)) > min_d for q in pts):
                pts.append(p); k -= 1
        return pts

    main = sample(n, 0.85 * R / np.sqrt(max(n, 1)), [])
    HS, WS = H * S, W * S
    Y, X = np.mgrid[0:HS, 0:WS].astype(np.float64) / S
    cov = np.zeros((HS, WS)); fl = np.zeros((HS, WS)); fc = np.zeros((HS, WS)); gl = np.zeros((HS, WS))
    halo = np.zeros((H, W))
    for p in main:
        ln = rng.uniform(*size); wd = ln / rng.uniform(*aspect); th = rng.uniform(0, np.pi)
        lit = rng.random() < bright
        if not lit:
            ln *= 0.7; wd *= 0.8
        x0, y0 = int(max(0, (p[0] - 10) * S)), int(max(0, (p[1] - 10) * S))
        x1, y1 = int(min(WS, (p[0] + 10) * S)), int(min(HS, (p[1] + 10) * S))
        Xs, Ys = X[y0:y1, x0:x1] - p[0], Y[y0:y1, x0:x1] - p[1]
        u = Xs * np.cos(th) + Ys * np.sin(th); v = -Xs * np.sin(th) + Ys * np.cos(th)
        # yuvarlatılmış köşeli pul (süper elips): pirinç tanesi gibi değil, levha gibi
        e = np.abs(u / (ln / 2)) ** 2.6 + np.abs(v / (wd / 2)) ** 2.6
        c = np.clip((1 - e) * 3, 0, 1)
        if lit:
            Lv = 0.90 + 0.07 * np.clip(0.5 - (u + v) / (ln * 0.8), 0, 1)
            Cv = 0.09
            gc = np.clip((1 - ((u / (ln * 0.26)) ** 2 + (v / (wd * 0.26)) ** 2)) * 2.0, 0, 1)
            gl[y0:y1, x0:x1] = np.maximum(gl[y0:y1, x0:x1], gc * c)
            iy, ix = int(p[1]), int(p[0])
            halo[max(0, iy - 1):iy + 2, max(0, ix - 1):ix + 2] += 1
        else:
            Lv = rng.uniform(0.56, 0.62) + 0.10 * np.clip(0.5 - (u + v) / (ln * 0.8), 0, 1)
            Cv = 0.16
        sel = c > cov[y0:y1, x0:x1]
        cov[y0:y1, x0:x1] = np.where(sel, c, cov[y0:y1, x0:x1])
        fl[y0:y1, x0:x1] = np.where(sel, Lv, fl[y0:y1, x0:x1])
        fc[y0:y1, x0:x1] = np.where(sel, Cv, fc[y0:y1, x0:x1])
    # küçük ışıltı noktaları
    for p in sample(int(round(micro * n)), 4.0, list(main)):
        r0 = rng.uniform(0.6, 1.0)
        x0, y0 = int(max(0, (p[0] - 3) * S)), int(max(0, (p[1] - 3) * S))
        x1, y1 = int(min(WS, (p[0] + 3) * S)), int(min(HS, (p[1] + 3) * S))
        dd = np.hypot(X[y0:y1, x0:x1] - p[0], Y[y0:y1, x0:x1] - p[1])
        c = np.clip((r0 - dd) * S / 1.5, 0, 1) * 0.75
        gl[y0:y1, x0:x1] = np.maximum(gl[y0:y1, x0:x1], c)
    down = lambda x: np.asarray(Image.fromarray(x.astype(np.float32), "F").resize((W, H), Image.BOX))
    flw, fcw = down(fl * cov), down(fc * cov)
    cov, gl = down(cov), down(gl)
    fL = np.where(cov > 1e-3, flw / np.maximum(cov, 1e-3), 0)
    fC = np.where(cov > 1e-3, fcw / np.maximum(cov, 1e-3), 0)
    halo = np.clip(gblur(halo, 2.6) * 2.6, 0, 1)
    L, C, h = to_lch(rgb)
    L = L + 0.06 * halo * (a > 0.5)                  # parlak pulun çevresinde ışıma (schiller)
    h = h + 6 * halo
    k = cov * opac
    L = L * (1 - k) + fL * k
    C = C * (1 - k) + fC * k
    h = h * (1 - k) + np.where(fL > 0.8, 80, 38) * k
    L = L * (1 - gl) + 0.99 * gl
    C = C * (1 - gl) + 0.03 * gl
    h = h * (1 - gl) + 82 * gl
    return to_srgb(lch(np.clip(L, 0, 1), C, h))


def bubble(rgb, a, g, bx, by, br):
    """Kehribarın içinde küçük hava kabarcığı."""
    L, C, h = to_lch(rgb)
    cx, cy, R = g["cx"] + bx * g["R"], g["cy"] + by * g["R"], br
    H, W = a.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    r = np.hypot(xx - cx, yy - cy) / R
    inside = np.clip((1 - r) * R, 0, 1)
    ang = np.arctan2(yy - cy, xx - cx)
    ring = np.exp(-((r - 0.86) / 0.12) ** 2)
    tl = np.clip(-np.cos(ang + np.pi / 4), 0, 1)       # sol üst kenar
    br_ = np.clip(np.cos(ang + np.pi / 4), 0, 1)       # sağ alt kenar
    L = L + inside * 0.05 + ring * (0.22 * tl ** 2) - ring * (0.05 * br_)
    C = C * (1 - 0.25 * inside) * (1 - 0.6 * ring * tl ** 2)
    return to_srgb(lch(np.clip(L, 0, 1), C, h))


def recolor_rays(rgb, a, region, hue_shift=-8, cmul=1.08, lmul=0.98):
    L, C, h = to_lch(rgb)
    new = to_srgb(lch(L * lmul, C * cmul, h + hue_shift))
    return np.where((region & (a > 0))[..., None], new, rgb)


# ---------- K1: G biçimi, ışınlı ----------
rgbG, aG = load(os.path.join(OUT, "G.png"))
yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
ys, xs = np.nonzero(aG > 0.5)
cG = 126.3
rG = np.hypot(xx - cG, yy - cG)
gem = rG < 72.0
P1 = dict(Lmin=0.52, Lmax=0.90, hue=[78, 46], C=0.160, gamma=0.95, glow_L=0.12)
rgb1, g1 = amberize(rgbG, aG, gem, P1)
rgb1 = flecks(rgb1, aG, g1, 9, seed=11, region=gem, keep_out=(g1["nx"] < -0.05) & (g1["ny"] < -0.1))
rgb1 = specular(rgb1, aG, g1)
rgb1 = recolor_rays(rgb1, aG, ~gem, hue_shift=-9, cmul=1.10, lmul=0.97)
save(rgb1, aG, "K1")

# ---------- K2: oval kehribar çakıl, ışınsız ----------
gem_a = np.where(gem, aG, 0.0)
# taşı büyüt + yatay oval + hafif eğim (çıktı -> girdi eşlemesi)
sx, sy, ang = 1.62, 1.28, np.deg2rad(-14)
ca, sa = np.cos(ang), np.sin(ang)
# girdi = Rot(-ang) * (u - c) / s + c
Minv = np.linalg.inv(np.array([[sx * ca, -sy * sa], [sx * sa, sy * ca]]))
off = np.array([cG, cG]) - Minv @ np.array([N / 2, N / 2])
M = (Minv[0, 0], Minv[0, 1], off[0], Minv[1, 0], Minv[1, 1], off[1])
rgb2, a2 = resample(rgbG, gem_a, M, (N, N))
rgb2, a2 = fit_canvas(rgb2, a2, box=BOX)
a2 = smooth_alpha(a2)
reg2 = a2 > 0
P2 = dict(Lmin=0.50, Lmax=0.89, hue=[72, 36], C=0.165, gamma=1.0, rim_L=0.03,
          glow_L=0.14, glow_h=8, glow_s=0.40)
rgb2, g2 = amberize(rgb2, a2, reg2, P2)
rgb2 = flecks(rgb2, a2, g2, 14, seed=5, region=reg2, keep_out=(g2["nx"] < 0.0) & (g2["ny"] < -0.15))
rgb2 = bubble(rgb2, a2, g2, 0.34, 0.20, 5.5)
rgb2 = specular(rgb2, a2, g2, ex=-0.40, ey=-0.42, sx=0.30, sy=0.12, ang=24)
save(rgb2, a2, "K2")

# ---------- K3: T3 kesme güneş taşı ----------
rgb3, a3 = load(os.path.join(ROOT, "cut_raw", "T3.png"))
rgb3, a3 = fit_canvas(rgb3, a3, box=BOX - 4)
reg3 = a3 > 0
P3 = dict(Lmin=0.50, Lmax=0.90, hue=[67, 41], C=0.150, gamma=0.9, rim_L=0.06,
          glow_L=0.10, glow_h=8, glow_s=0.45, spec_from=0.86)
rgb3, g3 = amberize(rgb3, a3, reg3, P3)
rgb3 = flecks(rgb3, a3, g3, 22, seed=3, region=reg3, size=(4.5, 8.0), micro=2.5, keep_out=(g3["nx"] < -0.1) & (g3["ny"] < -0.25))
rgb3 = specular(rgb3, a3, g3, ex=-0.46, ey=-0.52, sx=0.22, sy=0.09, ang=35, k=0.75)
save(rgb3, a3, "K3")

# ---------- K4: T4 gövdesi, kehribar kaya + çatlak ışığı ----------
rgb4, a4 = load(os.path.join(ROOT, "cut_raw", "T4.png"))
rgb4, a4 = fit_canvas(rgb4, a4, box=BOX)
L4, C4, h4 = to_lch(rgb4)
crack = (L4 > 0.80) & (h4 > 70) & (C4 > 0.10) & (a4 > 0.5)
crack_soft = np.clip(gblur(crack.astype(float), 1.0) * 1.6, 0, 1)
reg4 = a4 > 0
P4 = dict(Lmin=0.40, Lmax=0.86, hue=[68, 34], C=0.160, gamma=1.0, rim_L=0.06,
          glow_L=0.10, glow_h=8, glow_s=0.5, bounce=0.03, spec_from=0.99)
body4, g4 = amberize(rgb4, a4, reg4, P4)
# çatlaklar: daha sıcak, daha parlak altın ışık + çevresine ışıma
Lc, Cc, hc = to_lch(rgb4)
crack_col = to_srgb(lch(np.clip(Lc * 1.04 + 0.03, 0, 0.99), Cc * 1.05, hc - 4))
near = np.clip(gblur(crack.astype(float), 3.0) * 2.2, 0, 1) * (1 - crack_soft)
Lb, Cb, hb = to_lch(body4)
body4 = to_srgb(lch(np.clip(Lb + 0.10 * near, 0, 1), Cb * (1 + 0.1 * near), hb + 10 * near))
rgb4 = body4 * (1 - crack_soft[..., None]) + crack_col * crack_soft[..., None]
rgb4 = flecks(rgb4, a4, g4, 7, seed=8, region=reg4 & ~(gblur(crack.astype(float), 2) > 0.05),
              keep_out=(g4["nx"] < -0.1) & (g4["ny"] < -0.3))
save(rgb4, a4, "K4")
