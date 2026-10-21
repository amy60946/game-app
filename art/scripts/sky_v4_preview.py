# Pofi/Sky v4 önizlemesi (PofiSky.shader ile aynı matematik, numpy): doğal kümülüs (fbm + küme maskesi, güneşe doğru
# öz gölge, gümüş kenar, düz taban hissi), yüksek tül (cirrus) çizgileri, uzakta ufuk pusu. Rüzgârla kayar (T saniye).
# Kullanım: python3 sky_v4_preview.py <çıktı klasörü>
import math, sys, numpy as np
from PIL import Image
OUT = sys.argv[1]
def s2l(c): c = np.array(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
def ss(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def frac(x): return x - np.floor(x)

def hash12(x, y):   # Dave Hoskins hash12 (sin'siz: mobil GPU'da büyük sayılarda bozulmaz)
    p3x, p3y, p3z = frac(x * .1031), frac(y * .1031), frac(x * .1031)
    d = p3x * (p3y + 33.33) + p3y * (p3z + 33.33) + p3z * (p3x + 33.33)
    p3x, p3y, p3z = p3x + d, p3y + d, p3z + d
    return frac((p3x + p3y) * p3z)

def vnoise(x, y):
    ix, iy = np.floor(x), np.floor(y); fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = hash12(ix, iy), hash12(ix + 1, iy); c, d = hash12(ix, iy + 1), hash12(ix + 1, iy + 1)
    return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy

def fbm(x, y, octaves, fade):
    """fade: piksel ayak izi (uzakta ince oktavlar söner → titreşim yok)."""
    s, a, f, norm = 0.0, 0.5, 1.0, 0.0
    for _ in range(octaves):
        w = a * np.clip(1.5 - fade * f * 2.0, 0, 1)
        s = s + vnoise(x * f, y * f) * w; norm += a
        # dönmüş ızgara: tekrar deseni görünmesin
        x, y = x * 0.8 - y * 0.6 + 1.7, x * 0.6 + y * 0.8 + 9.2
        f *= 2.03; a *= 0.5
    return s / norm

P = dict(Zenith=s2l([0.33, 0.66, 0.97]), Mid=s2l([0.52, 0.80, 1.0]), Horizon=s2l([0.76, 0.92, 1.0]), Ground=s2l([0.45, 0.75, 0.95]),
         Lit=s2l([1.0, 0.99, 0.96]), Shade=s2l([0.66, 0.75, 0.89]))

def cumulus(az, el, L, cells, el0, el1, size, seed, T, cover):
    """Azimut hücresi başına en çok bir bulut. Yerel koordinat: x yatay, y tabandan yukarı (boyut birimi)."""
    drift = T * 0.004 * (1.0 + seed * 0.25)                     # yakın sıra biraz daha hızlı (derinlik)
    x = az / (2 * math.pi) * cells + drift
    alpha = np.zeros_like(az); tone = np.ones_like(az)
    sunAz = math.atan2(L[0], L[2])
    for dc in (-1, 0, 1):
        c = np.floor(x) + dc; cw = c - cells * np.floor(c / cells)
        r = lambda k: hash12(cw * 13.1 + k * 1.7, seed * 7.7 + k * 3.1)
        on = r(0) < cover
        cxp = c + 0.25 + r(1) * 0.5; ce = el0 + (el1 - el0) * r(2); s = size * (0.6 + r(3) * 0.9)
        lx = (x - cxp) * (2 * math.pi / cells) * np.cos(el) / s
        ly = (el - ce) / s
        W = 0.9 + r(5) * 1.4                                      # yarı genişlik
        Hh = 0.45 + r(6) ** 1.3 * 1.1                             # kabarıklık (yayvan .. kule)
        box = (np.abs(lx) < W * 1.7) & (ly > -0.35) & (ly < Hh * 1.6 + 0.3) & on
        if not box.any(): continue
        # karnabahar tepe: kubbe profili + iki ölçekli kabarık gürültü (bulut içinde sabit, yavaşça kaynar)
        k0 = r(9) * 50.0
        churn = T * 0.02
        u = np.clip(lx / W, -1.2, 1.2)
        dome = Hh * np.clip(1 - u * u, 0, 1) ** 0.55
        # tepe: yan yana yuvarlak loblar (ortadakiler yüksek ve büyük) → karnabahar; her lob kendi tepesinden ışık alır
        b3 = vnoise(lx * 9.0 + k0 + 3, ly * 9.0 + churn * 2.3)      # saçak dokusu
        top = np.full_like(lx, -1.0); lobLit = np.clip(0.3 + ly * 0.9, 0, 1)   # gövde: aşağı serin
        sx = 0.45 * np.sign(np.sin(sunAz - (cxp - drift) / cells * 2 * math.pi))
        for j in range(10):
            big = j < 6
            n_ = 6 if big else 4
            jj = j if big else j - 6
            uj = (jj + 0.5) / n_ * 2 - 1 + (r(20 + j) - 0.5) * (0.3 if big else 0.5)
            ox = uj * W * (0.85 if big else 0.55)
            rj = (0.26 + 0.28 * r(30 + j)) * (0.6 + Hh * 0.5) * (1 - 0.35 * abs(uj)) * (1.0 if big else 0.62) + 0.025 * np.sin(churn * 3 + j)
            cy = Hh * (1 - uj * uj) * ((0.3 + 0.4 * r(40 + j)) if big else (0.75 + 0.3 * r(40 + j)))
            dx, dy = lx - ox, ly - cy
            q = rj * rj - dx * dx
            hj = np.where(q > 0, cy + np.sqrt(np.maximum(q, 0)), -1.0)
            # yumuşak birleşim: loblar arasında dik kenar kalmaz
            hh_ = np.maximum(top, hj); top = hh_ + 0.06 * np.log(np.exp((top - hh_) / 0.06) + np.exp((hj - hh_) / 0.06))
            # lobun 2B normali: üst ve güneş tarafı aydınlık, altı serin
            ny = np.clip(dy / rj, -1, 1); nx = np.clip(dx / rj, -1, 1)
            lj = np.clip(0.6 + 0.38 * ny + sx * nx * 0.8, 0, 1)
            dd = np.sqrt(dx * dx + dy * dy)
            cov = ss(rj * 1.05, rj * 0.45, dd)                     # ressam sırası: sonraki lob öndekinin üstüne biner
            lobLit = lobLit + (lj - lobLit) * cov
        top = np.maximum(top, np.where(np.abs(lx) < W * 0.95, 0.18 * (1 - (lx / W) ** 2), -1.0))   # loblar arası gövde
        top = top + (b3 - 0.5) * 0.06
        dome = top
        inside = top - ly                                         # > 0: içeride
        base = ly + 0.04 + (b3 - 0.5) * 0.04                      # düz taban (hafif dalgalı)
        sdf = np.minimum(inside, base * 2.2)
        a = ss(0.0, 0.05 + 0.05 * b3, sdf) * box
        # ışık: tepede ve güneş tarafında aydınlık; taban ve kıvrım içleri serin gölge
        sunSide = np.sign(np.sin(sunAz - (cxp - drift) / cells * 2 * math.pi))
        hgt = np.clip(ly / np.maximum(top, 0.05), 0, 1)
        lit = 0.25 + 0.4 * ss(0.0, 0.9, hgt) + 0.45 * lobLit + 0.12 * np.clip(lx * sunSide / W, -1, 1)
        lit = lit - 0.3 * ss(0.14, 0.0, ly) - 0.16 * (0.5 - b3)
        lit = lit + 0.25 * ss(0.12, 0.0, inside) * ss(0.0, 0.1, ly)   # tepe kenarı ışık alır (gümüş kenar)
        lit = np.clip(lit, 0, 1)
        tone = np.where(a > alpha, lit, tone)
        alpha = np.maximum(alpha, a)
    return alpha, tone

def sky(d, L, T=0.0, cover=0.62):
    h = d[..., 1]; hp = np.clip(h, 0, 1)
    col = P['Horizon'] + (P['Mid'] - P['Horizon']) * ss(0, 0.3, hp)[..., None]
    col = col + (P['Zenith'] - col) * ss(0.2, 1, hp)[..., None]
    mu = (d * L).sum(-1)
    col = col * (0.95 + 0.08 * ((mu * 0.5 + 0.5) ** 2))[..., None]
    ang = np.arccos(np.clip(mu, -1, 1))
    col = col + np.array([1.0, 0.95, 0.82]) * ((1 - ss(0.022, 0.03, ang)) * 0.9 + np.exp(-ang * 9) * 0.12)[..., None]

    # --- yüksek tül (cirrus): rüzgâr yönünde uzamış ince, yarı saydam çizgiler (düzlem izdüşümü)
    hh = np.maximum(h, 0) + 0.035
    px, pz = d[..., 0] / hh, d[..., 2] / hh
    dist = 1.0 / hh
    cx, cz = (px * 0.9 + pz * 0.4) * 0.16 + T * 0.003, (pz * 0.9 - px * 0.4) * 0.7
    ci = fbm(cx, cz, 4, dist * 0.004)
    ci = ss(0.55, 0.85, ci) * ss(0.45, 0.7, vnoise(cx * 0.3 + 3.0, cz * 0.12)) * 0.32 * ss(0.05, 0.3, h)
    col = col + (P['Lit'] - col) * ci[..., None]
    # --- kümülüs sıraları (yandan görünüş): düz taban, karnabahar tepe, yumuşak saçaklı kenar
    el = np.arcsin(np.clip(h, -1, 1)); az = np.arctan2(d[..., 0], d[..., 2])
    for cells, e0, e1, size, seed, mix in ((22, 0.02, 0.045, 0.028, 1, 0.42), (12, 0.045, 0.1, 0.06, 2, 0.18), (7, 0.11, 0.3, 0.1, 3, 0.0)):
        a, t = cumulus(az, el, L, cells, e0, e1, size, seed, T, cover)
        cc = P['Shade'] + (P['Lit'] - P['Shade']) * t[..., None]
        cc = cc + (P['Horizon'] - cc) * mix
        col = col + (cc - col) * a[..., None]
    if True:
        below = h < 0
        col[below] = (P['Ground'] + (P['Horizon'] - P['Ground']) * np.exp(h * 8)[..., None])[below]
    return col

def cam_dirs(W, H, pitch, yaw, fov=58):
    t = math.tan(math.radians(fov) / 2); ar = W / H
    xs = (np.arange(W) + 0.5) / W * 2 - 1; ys = 1 - (np.arange(H) + 0.5) / H * 2
    X, Y = np.meshgrid(xs * t * ar, ys * t)
    d = np.stack([X, Y, np.ones_like(X)], -1)
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    d = np.stack([d[..., 0], d[..., 1] * cp + d[..., 2] * sp, -d[..., 1] * sp + d[..., 2] * cp], -1)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    d = np.stack([d[..., 0] * cy + d[..., 2] * sy, d[..., 1], -d[..., 0] * sy + d[..., 2] * cy], -1)
    return d / np.linalg.norm(d, axis=-1, keepdims=True)

if __name__ == '__main__':
    L = np.array([0.45, 0.55, 0.7]); L /= np.linalg.norm(L)
    W, H = 960, 540
    shots = [('ada_bakisi', 8, 10, 0), ('yukari', 30, 40, 0), ('gunese_karsi', 10, 35, 0), ('20sn_sonra', 8, 10, 20), ('60sn_sonra', 8, 10, 60)]
    for name, pitch, yaw, T in shots:
        d = cam_dirs(W, H, pitch, yaw)
        img = (l2s(sky(d, L, T)) * 255).astype(np.uint8)
        Image.fromarray(img).save(f"{OUT}/sky_{name}.png")
    print('ok')
