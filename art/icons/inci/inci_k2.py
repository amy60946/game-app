"""İnci simgesini K2 (kehribar çakıl) çizim dilinde yeniden işle — yalnız kodla, OKLab.
Çizim dili: kenara doğru belirgin gölge/derinlik, içten hafif ışıma, net parlama, bir iki küçük ışıltı.
Öz: yuvarlak inci, sedef yanardönerliği, açık ve değerli görünüş, sarı/altın yok, dış çizgi yok.
Yanardöner desen bugünkü S'den alınır (delik bölgesi doldurulur), gövde küre geometrisiyle yeniden gölgelenir.
Kullanım: python3 inci_k2.py <S.png> <çıktı klasörü>
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keh"))
from oklab import lch, to_lab, to_lch, to_srgb  # noqa: E402

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
N = 256


def gblur(x, r):
    n = int(np.ceil(3 * r))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / r) ** 2); k /= k.sum()
    p = np.pad(x, [(n, n), (n, n)] + [(0, 0)] * (x.ndim - 2), mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 1, p)


def save(rgb, a, name):
    o = np.concatenate([np.clip(rgb, 0, 1), np.clip(a, 0, 1)[..., None]], -1)
    Image.fromarray(np.round(o * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, name + ".png"))


# ---------- S'den yanardöner desen ----------
s = np.asarray(Image.open(SRC).convert("RGBA")).astype(np.float64) / 255
sa = s[..., 3]
slab = to_lab(s[..., :3])
yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
SC, SR = 127.5, 112.5
# delik (üstte): koyu küçük elips -> maskeli bulanıklıkla doldur
hole = np.hypot((xx - 127.5) / 36, (yy - 25) / 21) < 1
w = ((sa > 0.98) & ~hole).astype(float)
fillab = np.stack([gblur(slab[..., k] * w, 12) for k in range(3)], -1) / np.maximum(gblur(w, 12)[..., None], 1e-4)
feather = np.clip(gblur(hole.astype(float), 4.0) * 1.3, 0, 1)[..., None]
slab_f = slab * (1 - feather) + fillab * feather
# desen = renk sapması (a, b), ortancadan
m = sa > 0.98
sheenA = slab_f[..., 1] - np.median(slab_f[..., 1][m])
sheenB = slab_f[..., 2] - np.median(slab_f[..., 2][m])
sheen = np.stack([gblur(sheenA, 1.2), gblur(sheenB, 1.2)], -1)
sL = slab_f[..., 0]


def sample_sheen(R, cx=128.0, cy=128.0):
    """S'nin desenini yarıçapı R olan yeni küreye ölçekle (bilineer)."""
    u = (xx - cx) / R * SR + SC
    v = (yy - cy) / R * SR + SC
    u = np.clip(u, 0, N - 1.001); v = np.clip(v, 0, N - 1.001)
    x0, y0 = np.floor(u).astype(int), np.floor(v).astype(int)
    fx, fy = u - x0, v - y0
    def bil(img):
        a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
        if img.ndim == 3:
            fx_, fy_ = fx[..., None], fy[..., None]
        else:
            fx_, fy_ = fx, fy
        return a * (1 - fx_) * (1 - fy_) + b * fx_ * (1 - fy_) + c * (1 - fx_) * fy_ + d * fx_ * fy_
    return bil(sheen), bil(sL)


def norm(v):
    v = np.array(v, float); return v / np.linalg.norm(v)


LIGHT = norm([-0.45, -0.55, 0.70])
HALF = norm(LIGHT + np.array([0, 0, 1.0]))
BOUNCE = norm([0.55, 0.62, 0.25])


def pearl(P, R, cx=128.0, cy=128.0):
    """Küre inci: P ayarları. Döner: rgb, alfa, geometri."""
    d = np.hypot(xx - cx, yy - cy)
    a = np.clip(R + 0.5 - d, 0, 1)
    nx, ny = (xx - cx) / R, (yy - cy) / R
    r2 = np.clip(nx ** 2 + ny ** 2, 0, 1)
    nz = np.sqrt(1 - r2)
    lam = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    wrap = P.get("wrap", 0.35)
    diff = (lam + wrap) / (1 + wrap)
    fres = (1 - nz) ** 1.0
    L = P["Lmin"] + (P["Lmax"] - P["Lmin"]) * diff ** P.get("gamma", 1.2)
    L = L - P.get("rimL", 0.10) * fres ** 2.2
    # S'nin parlaklık dokusundan biraz (özgün yumuşak yansımalar)
    sh, sl = sample_sheen(R, cx, cy)
    L = L + P.get("tex", 0.35) * (sl - np.median(sL[m]))
    # sağ altta geri yansıma (derinlik)
    rr = np.sqrt(r2)
    diag = np.clip((nx + ny) / np.sqrt(2), -1, 1)
    b = np.exp(-((rr - 0.80) / 0.09) ** 2) * np.clip((diag - 0.15) / 0.7, 0, 1)
    L = L + P.get("bounceL", 0.10) * b
    # içten ışıma (sedefin "orient" parıltısı)
    g = np.exp(-((nx + 0.16) ** 2 + (ny + 0.18) ** 2) / (2 * P.get("glow_s", 0.40) ** 2))
    L = L + P.get("glowL", 0.05) * g
    # renk: gövde + S'nin yanardöner deseni + kenarda ince film gökkuşağı
    h0 = np.interp(fres, [0, 1], P["hue"])
    C0 = P["C"] * (0.85 + 0.3 * fres)
    A = C0 * np.cos(np.deg2rad(h0)) + P.get("sheen", 1.0) * sh[..., 0]
    B = C0 * np.sin(np.deg2rad(h0)) + P.get("sheen", 1.0) * sh[..., 1]
    tf = P.get("film", 0.025) * np.clip((fres - 0.25) / 0.6, 0, 1)
    ht = P.get("film_h", 330) + 300 * fres
    A = A + tf * np.cos(np.deg2rad(ht)); B = B + tf * np.sin(np.deg2rad(ht))
    bt = P.get("bounce_tint", None)
    if bt is not None:
        A = A + bt[0] * b; B = B + bt[1] * b
    # parlama: K2'deki gibi sol üstte net, yumuşak kenarlı elips + küçük nokta; ayrıca geniş yumuşak parıltı
    nh = np.clip(nx * HALF[0] + ny * HALF[1] + nz * HALF[2], 0, 1)
    soft = nh ** 9 * P.get("soft", 0.10)
    L = L + soft
    ex, ey = P.get("hl", (-0.40, -0.44))
    rot = np.deg2rad(38)
    u, v = nx - ex, ny - ey
    rx = (u * np.cos(rot) + v * np.sin(rot)) / P.get("hl_w", 0.25)
    ry = (-u * np.sin(rot) + v * np.cos(rot)) / P.get("hl_h", 0.13)
    spec = np.clip(1 - (rx ** 2 + ry ** 2), 0, 1) ** 1.3 * P.get("spec", 0.95)
    dot = np.clip(1 - (((nx - ex - 0.30) / 0.055) ** 2 + ((ny - ey - 0.17) / 0.045) ** 2), 0, 1) ** 1.3 * 0.85
    spec = np.maximum(spec, dot)
    L = L * (1 - spec) + 1.0 * spec
    A = A * (1 - spec); B = B * (1 - spec)
    # küçük ışıltılar
    for (sx, sy, sr, k) in P.get("glints", []):
        gd = np.hypot(xx - (cx + sx * R), yy - (cy + sy * R))
        gk = np.clip((sr - gd) / max(sr * 0.6, 0.8) + 0.5, 0, 1) * k
        L = L * (1 - gk) + 1.0 * gk
        A = A * (1 - gk); B = B * (1 - gk)
    rgb = to_srgb(np.stack([np.clip(L, 0, 1), A, B], -1))
    return rgb, a, dict(nx=nx, ny=ny, nz=nz, R=R, cx=cx, cy=cy, d=d)


def add_hole(rgb, a, g, depth=0.70):
    """Bugünkü S'deki gibi üstte küçük delik (yalnız S'ye yakın seçeneklerde)."""
    L, C, h = to_lch(rgb)
    cx, cy, R = g["cx"], g["cy"] - 0.86 * g["R"], g["R"]
    ex = np.hypot((xx - cx) / (0.105 * R), (yy - cy) / (0.050 * R))
    inner = np.clip((1 - ex) * 3.0, 0, 1)
    lip = np.clip(1 - np.abs(ex - 1.08) / 0.22, 0, 1) * (yy > cy)
    L = L * (1 - inner) + depth * inner + 0.05 * lip
    C = C * (1 - 0.5 * inner)
    return to_srgb(lch(np.clip(L, 0, 1), C, np.where(inner > 0, 300, h)))


# ---------- S tabanlı K2 işlemi ----------
def from_s(P, D, keep_hole=False):
    """Bugünkü S'nin kendi parlaklık dokusu + yanardöner deseni korunur; üstüne K2 dili:
    küre gölgesi, kenara doğru derinlik, sağ altta geri yansıma, içten ışıma, net parlama, ışıltı."""
    lab = slab if keep_hole else slab_f
    L0 = lab[..., 0]
    nx, ny = (xx - SC) / SR, (yy - SC) / SR
    r2 = np.clip(nx ** 2 + ny ** 2, 0, 1)
    nz = np.sqrt(1 - r2)
    rr = np.sqrt(r2)
    lam = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    diff = (lam + 0.35) / 1.35
    fres = 1 - nz
    t0 = np.clip((L0 - 0.74) / 0.24, 0, 1)
    t = P.get("mix", 0.5) * t0 + (1 - P.get("mix", 0.5)) * diff ** P.get("gamma", 1.05)
    L = P["Lmin"] + (P["Lmax"] - P["Lmin"]) * t
    L = L - P.get("rimL", 0.07) * fres ** 2.2
    diag = np.clip((nx + ny) / np.sqrt(2), -1, 1)
    bnc = np.exp(-((rr - 0.80) / 0.09) ** 2) * np.clip((diag - 0.15) / 0.7, 0, 1)
    L = L + P.get("bounceL", 0.10) * bnc
    g = np.exp(-((nx + 0.16) ** 2 + (ny + 0.18) ** 2) / (2 * P.get("glow_s", 0.40) ** 2))
    L = L + P.get("glowL", 0.04) * g
    # renk: gövde + S'nin deseni (gölgede biraz azalır: çamurlaşmasın)
    h0 = np.interp(fres, [0, 1], P["hue"])
    C0 = P["C"] * (0.85 + 0.3 * fres)
    k = P.get("sheen", 1.0) * (0.55 + 0.45 * diff) * (1 - P.get("rim_sheen", 0.0) * np.clip((rr - 0.55) / 0.35, 0, 1))
    A = C0 * np.cos(np.deg2rad(h0)) + k * sheen[..., 0]
    B = C0 * np.sin(np.deg2rad(h0)) + k * sheen[..., 1]
    bt = P.get("bounce_tint", (0, 0))
    A = A + bt[0] * bnc; B = B + bt[1] * bnc
    # net parlama (K2 gibi) + küçük nokta
    ex, ey = P.get("hl", (-0.40, -0.44))
    rot = np.deg2rad(38)
    u, v = nx - ex, ny - ey
    rx = (u * np.cos(rot) + v * np.sin(rot)) / 0.25
    ry = (-u * np.sin(rot) + v * np.cos(rot)) / 0.13
    spec = np.clip(1 - (rx ** 2 + ry ** 2), 0, 1) ** 1.3 * P.get("spec", 0.95)
    dot = np.clip(1 - (((nx - ex - 0.30) / 0.055) ** 2 + ((ny - ey - 0.17) / 0.045) ** 2), 0, 1) ** 1.3 * 0.85
    spec = np.maximum(spec, dot)
    for (gx, gy, gr, gk) in P.get("glints", []):
        gd = np.hypot(xx - (SC + gx * SR), yy - (SC + gy * SR))
        spec = np.maximum(spec, np.clip((gr - gd) / max(gr * 0.6, 0.8) + 0.5, 0, 1) * gk)
    L = L * (1 - spec) + 1.0 * spec
    A = A * (1 - spec); B = B * (1 - spec)
    if keep_hole:   # delik özgün koyuluğunu korusun
        hk = (np.hypot((xx - 127.5) / 18, (yy - 23) / 9) < 1) & (L0 < 0.86)
        hk = np.clip(gblur(hk.astype(float), 0.8) * 1.5, 0, 1)
        L = L * (1 - hk) + (L0 - 0.18) * hk
    rgb = to_srgb(np.stack([np.clip(L, 0, 1), A, B], -1))
    # çapı D olacak şekilde küçült (önçarpımlı)
    kk = D / 226.0
    big = int(round(N * kk))
    pm = np.concatenate([rgb * sa[..., None], sa[..., None]], -1)
    ch = [np.asarray(Image.fromarray(pm[..., i].astype(np.float32), "F").resize((big, big), Image.LANCZOS)) for i in range(4)]
    o = (N - big) // 2
    cv = np.zeros((N, N, 4)); cv[o:o + big, o:o + big] = np.stack(ch, -1)
    A_ = np.clip(cv[..., 3], 0, 1)
    return np.clip(cv[..., :3] / np.maximum(A_[..., None], 1e-4), 0, 1), A_


# ---------- seçenekler ----------
D_MAIN = 212        # İ1–İ4 çapı (S 226)
D_EQ = 202          # İ6: K2 ile aynı alan (32 000 px²)
NEUTRAL = dict(Lmin=0.62, Lmax=0.93, hue=[300, 285], C=0.010, sheen=1.15, rimL=0.11, glowL=0.04,
               bounceL=0.10, bounce_tint=(-0.008, -0.020), spec=0.97)

# İ1: derinleştirilmiş S (aynı renk ve desen, K2 kadar hacim ve kontrast), delik korunur
P_I1 = dict(NEUTRAL, Lmin=0.68, Lmax=0.95, rimL=0.15, C=0.020, hue=[305, 290], sheen=1.45, bounceL=0.08,
            glints=[(0.50, 0.30, 2.2, 0.7)])
save(*from_s(P_I1, D_MAIN, keep_hole=True), "I1")
# İ1b: aynı ayarlar, delik yok (delik bölgesi S'nin çevresinden maskeli bulanıklıkla doldurulur)
save(*from_s(P_I1, D_MAIN, keep_hole=False), "I1b")
# İ2: pembe sedef, deliksiz
save(*from_s(dict(NEUTRAL, hue=[10, -12], C=0.050, sheen=0.75, rim_sheen=0.3, bounce_tint=(0.018, -0.012),
                  glints=[(0.50, 0.30, 2.2, 0.7)]), D_MAIN), "I2")
# İ3: soğuk lavanta / gümüş-mavi sedef, deliksiz
save(*from_s(dict(NEUTRAL, hue=[292, 252], C=0.040, Lmin=0.58, Lmax=0.92, sheen=0.75, bounce_tint=(-0.014, -0.028),
                  glints=[(0.50, 0.30, 2.2, 0.7)]), D_MAIN), "I3")
# İ4: krem inci + daha güçlü iç ışıma + iki ışıltı, deliksiz (fildişi: doygunluk çok düşük, altın değil)
save(*from_s(dict(NEUTRAL, hue=[45, 20], C=0.022, Lmin=0.63, Lmax=0.94, sheen=0.45, rim_sheen=0.5, glowL=0.08, glow_s=0.36,
                  bounce_tint=(0.012, -0.006),
                  glints=[(0.42, -0.08, 2.6, 0.85), (0.12, 0.55, 2.0, 0.75)]), D_MAIN), "I4")

# İ6: en sade — bugünkü S, yalnız boyu K2 ile eşit alana indirilir ve gölgesi biraz derinleşir (delik korunur)
s_rgb, s_a = s[..., :3], s[..., 3]
L, C, h = to_lch(s_rgb)
nx, ny = (xx - SC) / SR, (yy - SC) / SR
rr = np.clip(np.hypot(nx, ny), 0, 1)
L2 = 0.985 - (0.985 - L) * 1.45 - 0.06 * rr ** 4
C2 = C * 1.15
s2 = to_srgb(lch(np.clip(L2, 0, 1), C2, h))
k = D_EQ / 226.0
big = int(round(N * k))
pm = np.concatenate([s2 * s_a[..., None], s_a[..., None]], -1)
ch = [np.asarray(Image.fromarray(pm[..., i].astype(np.float32), "F").resize((big, big), Image.LANCZOS)) for i in range(4)]
o = (N - big) // 2
canvas = np.zeros((N, N, 4))
canvas[o:o + big, o:o + big] = np.stack(ch, -1)
A6 = np.clip(canvas[..., 3], 0, 1)
RGB6 = np.clip(canvas[..., :3] / np.maximum(A6[..., None], 1e-4), 0, 1)
save(RGB6, A6, "I6")

# İ5: açık istiridye kabuğunun içinde inci
S5 = 4
NS = N * S5
Y5, X5 = np.mgrid[0:NS, 0:NS].astype(np.float64) / S5
cxs, cys = 128.0, 150.0
# alt kabuk: geniş yelpaze/çanak (yarım elips + dalgalı kenar), üst kabuk arkada açık kapak
def shell_mask(cx, cy, rx, ry, up, ribs=9, wav=0.045):
    ang = np.arctan2((Y5 - cy) / ry, (X5 - cx) / rx)
    rad = np.hypot((X5 - cx) / rx, (Y5 - cy) / ry)
    edge = 1 + wav * np.cos(ribs * 2 * ang)
    half = (Y5 >= cy) if not up else (Y5 <= cy)
    return np.clip((edge - rad) * rx * S5 / 2.0, 0, 1) * half, rad, ang
low, rad_l, ang_l = shell_mask(cxs, cys - 6, 112, 82, up=False)
top, rad_t, ang_t = shell_mask(cxs, cys - 40, 104, 92, up=True)
down = lambda x: np.asarray(Image.fromarray(x.astype(np.float32), "F").resize((N, N), Image.BOX))
low_a, top_a = down(low), down(top)
rad_l, ang_l = down(rad_l), down(ang_l)
rad_t, ang_t = down(rad_t), down(ang_t)
def shell_color(rad, ang, inner_tone, outer, a_):
    ribs = 0.5 + 0.5 * np.cos(18 * ang)
    Lb = inner_tone[0] - 0.10 * rad ** 2 + 0.05 * ribs * rad
    Cb = inner_tone[1]
    hb = inner_tone[2] + 20 * rad
    # dış kenar şeridi (kabuğun kalınlığı) daha koyu
    rim = np.clip((rad - 0.86) / 0.12, 0, 1)
    Lb = Lb * (1 - rim) + outer[0] * rim
    Cb = Cb * (1 - rim) + outer[1] * rim
    hb = hb * (1 - rim) + outer[2] * rim
    return to_srgb(lch(np.clip(Lb, 0, 1), Cb, hb))
top_rgb = shell_color(rad_t, ang_t, (0.74, 0.030, 280), (0.58, 0.035, 250), top_a)
low_rgb = shell_color(rad_l, ang_l, (0.86, 0.028, 300), (0.62, 0.040, 250), low_a)
P5 = dict(NEUTRAL, hue=[300, 270], C=0.014, glints=[(-0.30, -0.52, 2.2, 0.9)])
pr, pa, pg = pearl(P5, 62, cx=128, cy=128)
# katmanlar: üst kabuk (arka) -> inci -> alt kabuk (önde, incinin alt kısmını sarar)
lowL = (yy > 150).astype(float)
out_rgb = top_rgb * top_a[..., None]
out_a = top_a.copy()
out_rgb = pr * pa[..., None] + out_rgb * (1 - pa[..., None]); out_a = pa + out_a * (1 - pa)
la = low_a * np.clip((yy - 140) / 6, 0, 1) + low_a * (np.hypot(xx - 128, yy - 128) > 62)
la = np.clip(la, 0, 1) * low_a
out_rgb = low_rgb * la[..., None] + out_rgb * (1 - la[..., None]); out_a = la + out_a * (1 - la)
# kabuk içine incinin altında hafif gölge
A5 = np.clip(out_a, 0, 1)
rgb5 = np.clip(out_rgb / np.maximum(A5[..., None], 1e-4), 0, 1)
sh5 = np.exp(-((xx - 132) ** 2 / (2 * 40 ** 2) + (yy - 178) ** 2 / (2 * 10 ** 2))) * la
Lx, Cx, hx = to_lch(rgb5)
rgb5 = to_srgb(lch(np.clip(Lx - 0.10 * sh5, 0, 1), Cx, hx))
save(rgb5, A5, "I5")
print("ok")
