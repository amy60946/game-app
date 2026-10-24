"""Evim zemini (24 Ekim 2026, kullanıcı geri bildirimi): sahne adacığının düz kum rengi yerine kodla boyanmış kum.

Boyalı maket stili (dış çizgi yok, ışık dokuya boyalı, renk canlı ama dengeli):
  tepecikler ve rüzgâr çizgileri (güneş yönünden boyanmış), kum taneleri, küçük deniz kabukları (tarak, midye, sarmal,
  kum doları), çakıl öbekleri, petin altında yuvarlak hasır, arka solda çizgili hasır halı (kenar gölgeleriyle),
  kenarda ıslak kum + gelgit izi + kıyı köpüğü. Mesh: eski silindirle aynı üst elips (6,6 × 6,2 m), kenarda alçak tepecikler
  ve suya yuvarlanan omuz.

Kullanım (bpy 4.2 + Pillow + numpy, ör. /tmp/claude-0/bpyenv/bin/python):
  nice -n 10 <python> -I art/scripts/home_floor.py                 # doku + FBX → Assets/_Pofi/Resources/Env/floor_home/
  nice -n 10 <python> -I art/scripts/home_floor.py --preview KLASÖR  # + oyun kamerasından önce/sonra çizimi (Cycles)
  --tex-only: yalnız doku (bpy gerekmez)

Oyunda: World/Stage.cs → RealAssets.EnvFootprint("floor_home", …, FloorWidth, 180°) (Blender (x, y) = Unity (x, z));
dosya yoksa eski düz kum silindiri kalır. Doku 2048 px (PofiArtImporter: floor_ öneki), normal haritası yok
(Pofi/Toon'da güneşe bakan düz zeminde etkisi ~%3; ışık zaten dokuya boyalı).
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env', 'floor_home')
NAME = 'floor_home'

A, B = 3.3, 3.1            # üst kenar elipsi (eski "Island" silindiri 6,6 × 6,2 m)
R_OUT = 1.12               # mesh dış kenarı (elips oranı); su altında
HALF = A * R_OUT           # doku kare: [-HALF, HALF]² (m) → FloorWidth = 2 * HALF = 7,392 m
N = 2048
PPM = N / (2 * HALF)       # piksel / m (~277)
CENTER_Z = 0.9             # adacığın merkezi (Unity z); pet Unity (0, 0, 0) = yerel (0, -0.9)
PET = (0.0, -CENTER_Z)
WATER_Y = -0.10            # su yüzeyi (Stage: silindir y −0,12, kalınlık 0,04)
SUN = np.array([0.394, -0.630, 0.669])   # ışığın geldiği yön (Stage güneşi Euler(42, −32, 0)), yerel (x, y, yukarı)
SEED = 24102026
# ön kenarda hafif 3B süsler (mevcut Env modelleri; Stage.Build'deki Prop satırlarıyla aynı): ad, Unity konumu, taban, dönüş
FRONT_PROPS = [('p_starfish', (-1.55, 0.0, -1.15), 0.36, 25.0), ('r_pebble', (1.3, 0.0, -1.2), 0.22, 40.0),
               ('r_pebble', (1.5, 0.0, -1.02), 0.15, 160.0)]


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def lerp(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 else t
    return a + (b - a) * t


# ------------------------------------------------------------------ gürültü
_rng = np.random.default_rng(SEED)


def noise(cells, n=N):
    g = _rng.random((cells + 3, cells + 3)).astype(np.float32)
    im = Image.fromarray(g, 'F').resize((n + n // cells * 3, n + n // cells * 3), Image.BICUBIC)
    a = np.asarray(im)
    o = n // cells
    return a[o:o + n, o:o + n]


def fbm(cells, octaves=4, n=N):
    s, w, tot = 0, 1.0, 0
    for k in range(octaves):
        s = s + noise(cells * 2 ** k, n) * w
        tot += w
        w *= 0.5
    s = s / tot
    lo, hi = np.percentile(s, 1), np.percentile(s, 99)
    return np.clip((s - lo) / (hi - lo), 0, 1)


# ------------------------------------------------------------------ geometri (mesh ve doku ortak)
def mound(r, th):
    """Kenar tepecikleri (m): r 0,84–0,99 arası, en çok ~3 cm (Stage süsleri y −0,05'te: gömülmez, havada kalmaz)."""
    m = 0.028 * (0.55 + 0.45 * np.sin(3 * th + 0.7) * np.sin(5 * th - 1.1)) * np.sin(np.pi * np.clip((r - 0.84) / 0.15, 0, 1)) ** 2
    return np.where((r > 0.84) & (r < 0.99), np.maximum(m, 0), 0)


def profile(r, th):
    """Yerel yükseklik (m), r = elips oranı, th = açı. Ortası düz (pet ve eşyalar y = 0,01), kenarda alçak tepecikler, suya omuz."""
    edge = np.clip((r - 1.0) / (R_OUT - 1.0), 0, 1)
    return 0.01 + mound(r, th) - 0.31 * edge ** 2


WATER_R = 1.0 + (R_OUT - 1.0) * math.sqrt((0.01 - WATER_Y) / 0.31)   # su çizgisi (≈ 1,0715)


def coords():
    j = (np.arange(N, dtype=np.float32) + 0.5) / N
    x = -HALF + 2 * HALF * j
    y = HALF - 2 * HALF * j          # görüntü satırı 0 = üst = +y (UV v = 1)
    return np.meshgrid(x, y)


# ------------------------------------------------------------------ küçük nesneler (kabuk, çakıl): RGBA çıkartma + yükseklik
def sprite_shell(kind, size_px, rng):
    """Boyalı kabuk: üst-sağdan ışık (dokuya göre güneş), yumuşak gölge ayrı eklenir. 4× büyük çizilip küçültülür."""
    S = size_px * 4
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pal = {
        'scallop': [('#F6B39A', '#FFD9C7', '#D9876C'), ('#F3A7B8', '#FFD3DD', '#C9798C'), ('#F6E1BF', '#FFF4E0', '#CFAF84'),
                    ('#F49A72', '#FFCDB0', '#C8704C')],
        'clam': [('#EFD9C0', '#FFF2E2', '#B99C80'), ('#D8C3E0', '#F3E8F7', '#A58FAF'), ('#F2C6A8', '#FFE6D2', '#C49577')],
        'spiral': [('#F4D8B0', '#FFF0D8', '#C79E6E'), ('#F5B98F', '#FFE0C8', '#C88158')],
        'dollar': [('#EDE3CF', '#FBF6EA', '#C4B497')],
        'star': [('#F28A5B', '#FFB98F', '#C4613A'), ('#F6B04E', '#FFD58A', '#C98428')],
    }[kind]
    base, hi_c, lo_c = [tuple(int(c * 255) for c in hexc(h)) for h in pal[rng.integers(len(pal))]]
    c = S / 2
    if kind == 'scallop':
        # yelpaze: alt orta menteşe, üstte dalgalı kenar; ışınsal kaburgalar
        r = S * 0.46
        pts = [(c, c + r * 0.62)]
        for k in range(0, 41):
            a = math.radians(200 + k * 140 / 40)
            rr = r * (1 + 0.035 * math.cos(k * math.pi / 2.5))
            pts.append((c + rr * math.cos(a) * 1.02, c + r * 0.62 + rr * math.sin(a) * 1.18))
        d.polygon(pts, fill=base)
        for k in range(1, 9):
            a = math.radians(200 + k * 140 / 9)
            d.line([(c, c + r * 0.62), (c + r * 0.95 * math.cos(a), c + r * 0.62 + r * 1.1 * math.sin(a))], fill=lo_c, width=max(2, S // 40))
        d.polygon([(c - r * 0.28, c + r * 0.70), (c + r * 0.28, c + r * 0.70), (c + r * 0.14, c + r * 0.48), (c - r * 0.14, c + r * 0.48)], fill=base)
    elif kind == 'clam':
        r = S * 0.42
        d.ellipse([c - r, c - r * 0.82, c + r, c + r * 0.82], fill=base)
        for k in range(1, 4):
            q = 1 - k * 0.22
            d.arc([c - r * q, c - r * 0.82 * q + r * 0.18 * (1 - q), c + r * q, c + r * 0.82 * q + r * 0.18 * (1 - q)], 200, 340, fill=lo_c, width=max(2, S // 45))
        d.ellipse([c - r * 0.18, c + r * 0.52, c + r * 0.18, c + r * 0.78], fill=lo_c)
    elif kind == 'spiral':
        # sarmal (deniz salyangozu): damla gövde + spiral çizgi
        r = S * 0.40
        d.ellipse([c - r * 0.62, c - r * 0.25, c + r * 0.62, c + r * 0.95], fill=base)
        d.polygon([(c - r * 0.45, c + r * 0.05), (c + r * 0.45, c + r * 0.05), (c, c - r * 1.0)], fill=base)
        for k in range(4):
            yy = c + r * (0.55 - k * 0.38)
            w = r * (0.55 - k * 0.12)
            d.arc([c - w, yy - w * 0.35, c + w, yy + w * 0.35], 10, 170, fill=lo_c, width=max(2, S // 40))
        d.ellipse([c - r * 0.22, c + r * 0.35, c + r * 0.22, c + r * 0.75], fill=lo_c)
    elif kind == 'dollar':
        r = S * 0.42
        d.ellipse([c - r, c - r, c + r, c + r], fill=base)
        for k in range(5):
            a = math.radians(-90 + k * 72)
            px, py = c + r * 0.42 * math.cos(a), c + r * 0.42 * math.sin(a)
            d.ellipse([px - r * 0.1, py - r * 0.22, px + r * 0.1, py + r * 0.22], fill=lo_c)
        d.ellipse([c - r * 0.07, c - r * 0.07, c + r * 0.07, c + r * 0.07], fill=lo_c)
    else:   # küçük deniz yıldızı
        r = S * 0.46
        pts = []
        for k in range(10):
            a = math.radians(-90 + k * 36)
            rr = r if k % 2 == 0 else r * 0.42
            pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
        d.polygon(pts, fill=base)
        for k in range(5):
            a = math.radians(-90 + k * 72)
            for t in (0.3, 0.5, 0.7):
                px, py = c + r * t * math.cos(a), c + r * t * math.sin(a)
                d.ellipse([px - S * 0.018, py - S * 0.018, px + S * 0.018, py + S * 0.018], fill=hi_c)
    return finish_sprite(im, size_px, hi_c, rng)


def sprite_pebble(size_px, rng):
    S = size_px * 4
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pal = ['#A9B4BE', '#BDB3A6', '#C99577', '#8E9CAB', '#D7CDBF', '#9FB2A4', '#B9A08C']
    base = tuple(int(c * 255) for c in hexc(pal[rng.integers(len(pal))]))
    hi_c = tuple(min(255, int(v * 1.18 + 18)) for v in base)
    c = S / 2
    rx, ry = S * 0.44, S * 0.44 * rng.uniform(0.55, 0.85)
    pts = []
    for k in range(24):
        a = 2 * math.pi * k / 24
        j = 1 + rng.uniform(-0.06, 0.06)
        pts.append((c + rx * j * math.cos(a), c + ry * j * math.sin(a)))
    d.polygon(pts, fill=base)
    return finish_sprite(im, size_px, hi_c, rng)


def finish_sprite(im, size_px, hi_c, rng):
    """Boyalı ışık: üst-sağ kenarda açık ton, alt-sol yarıda hafif koyulaşma (nesne kendi içinde yuvarlak görünür)."""
    im = im.rotate(rng.uniform(0, 360), resample=Image.BICUBIC, expand=True)   # önce döndür: ışık hep aynı yönden
    S = im.size[0]
    a = np.asarray(im).astype(np.float32) / 255.0
    alpha = a[..., 3]
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S - 0.5   # görüntü: x sağ, y aşağı
    lx, ly = SUN[0], SUN[1]            # dokuda ışık sağdan (+x) ve aşağıdan (−y = görüntüde aşağı)
    lnorm = math.hypot(lx, ly)
    side = (xx * lx / lnorm + yy * (-ly) / lnorm)   # ışığa doğru +
    blur = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S * 0.06))).astype(np.float32) / 255
    rim = np.clip(alpha - blur, 0, 1)   # kenar bandı
    hi = np.array(hi_c, np.float32) / 255
    rgb = a[..., :3]
    rgb = rgb * (1 - 0.18 * np.clip(-side * 2.2, 0, 1)[..., None])
    rgb = rgb + (hi - rgb) * (np.clip(side * 2.5, 0, 1) * 0.55 + rim * np.clip(side * 3, 0, 1) * 0.9)[..., None]
    out = np.dstack([np.clip(rgb, 0, 1), alpha])
    img = Image.fromarray((out * 255).astype(np.uint8), 'RGBA')
    w = max(3, int(round(img.size[0] / 4)))
    return img.resize((w, w), Image.LANCZOS)


# ------------------------------------------------------------------ doku
def build_texture():
    X, Y = coords()
    r = np.sqrt((X / A) ** 2 + (Y / B) ** 2)
    th = np.arctan2(Y / B, X / A)

    # --- hasırlar: yuvarlak (pet altında) + çizgili dikdörtgen (arka sol)
    mc = (0.0, PET[1] + 0.15)
    mrx, mry = 0.98, 0.80
    q = np.sqrt(((X - mc[0]) / mrx) ** 2 + ((Y - mc[1]) / mry) ** 2)
    mat_round = sstep(1.0, 0.985, q)
    rc, ra = (-1.85, 0.55), math.radians(14)
    lu = (X - rc[0]) * math.cos(ra) + (Y - rc[1]) * math.sin(ra)
    lv = -(X - rc[0]) * math.sin(ra) + (Y - rc[1]) * math.cos(ra)
    rw, rh = 0.62, 0.40
    mat_rect = sstep(0.008, -0.004, np.maximum(np.abs(lu) - rw, np.abs(lv) - rh))
    fringe_zone = (np.abs(lv) < rh - 0.02) & (np.abs(lu) > rw) & (np.abs(lu) < rw + 0.05)
    fringe = fringe_zone & (np.mod(lv, 0.022) < 0.009)
    mats = np.clip(mat_round + mat_rect, 0, 1)

    # --- yükseklik (boyalı ışık için): tepecik + rüzgâr çizgisi
    wet = sstep(0.975, 1.035, r + (fbm(20, 3) - 0.5) * 0.035)
    dune = (fbm(5, 4) - 0.5) * 0.06 * (0.55 + 0.9 * sstep(0.55, 0.95, r))
    # rüzgâr çizgileri: tepe çizgileri ışığa dik (eğim ışık yönünde → boyalı ışık/gölge görünür; kameradan yatay çizgiler)
    dirx, diry = math.cos(math.radians(-52)), math.sin(math.radians(-52))
    warp = (fbm(4, 3) - 0.5) * 7.0 + (fbm(9, 2) - 0.5) * 1.5
    lam = 0.16
    phi = 2 * np.pi * (X * dirx + Y * diry) / lam + warp
    rip = np.sin(phi) + 0.3 * np.sin(2 * phi)
    rmask = sstep(0.42, 0.75, fbm(3, 3)) * (0.12 + 0.88 * sstep(0.45, 0.88, r)) * (1 - wet) * (1 - mats)
    H = dune + rip * 0.0022 * rmask + mound(r, th) * 0.6

    # --- renk
    # canlı ama dengeli: en açık ton R ≤ ~240 (Pofi/Toon güneşli zeminde ×1,2 → patlamasın; kullanıcı ışık uyarısı)
    dry_lo, dry, dry_hi = hexc('#DDAF74'), hexc('#EAC487'), hexc('#F2D69E')
    t = fbm(10, 4)
    col = lerp(dry_lo, dry_hi, sstep(0.05, 0.95, t * 0.8 + 0.1))
    col = lerp(col, dry, 0.35)
    warm = sstep(0.55, 0.85, fbm(6, 3))
    col = lerp(col, hexc('#EBBE92'), warm * 0.30)           # pembe-sıcak lekeler
    cool = sstep(0.6, 0.9, fbm(7, 3))
    col = lerp(col, hexc('#E3CB98'), cool * 0.25)           # sarımsı lekeler
    # ıslak kum + gelgit izi + su altı
    col = lerp(col, hexc('#B99470'), wet * 0.85)
    col = lerp(col, hexc('#9C8268'), sstep(WATER_R - 0.01, WATER_R + 0.03, r) * 0.8)
    tide = np.exp(-((r + (fbm(14, 3) - 0.5) * 0.03 - 0.985) / 0.006) ** 2) * (1 - wet * 0.5)
    col = col * (1 - 0.09 * tide[..., None])
    gloss = sstep(1.035, 1.05, r) * (1 - sstep(1.05, WATER_R - 0.008, r))
    col = lerp(col, hexc('#D5DCD8'), gloss * 0.12)           # ıslak parıltı (gök yansıması)
    lace = sstep(0.45, 0.62, fbm(40, 2))
    foam = sstep(WATER_R - 0.016, WATER_R - 0.009, r) * (1 - sstep(WATER_R + 0.002, WATER_R + 0.012, r))
    foam = np.clip(foam * (0.55 + 0.45 * lace) + sstep(WATER_R - 0.03, WATER_R - 0.02, r) * (1 - sstep(WATER_R - 0.02, WATER_R - 0.012, r)) * lace * 0.6, 0, 1)
    col = lerp(col, hexc('#FBFDFC'), foam * 0.9)

    # boyalı ışık (tepecik + rüzgâr çizgisi), güneş yönünde
    gy, gx = np.gradient(H, 1.0 / PPM)
    gy = -gy                                                 # satır aşağı = −y
    nx, ny, nz = -gx, -gy, np.ones_like(H)
    nl = np.sqrt(nx * nx + ny * ny + 1)
    lamb = (nx * SUN[0] + ny * SUN[1] + nz * SUN[2]) / nl
    shade = 1 + 0.9 * (lamb - SUN[2])
    col = col * np.clip(shade, 0.84, 1.14)[..., None]
    # tepeciklerin ve çizgilerin gölgeli yüzünde hafif serin ton (boyalı gölge, gri değil)
    col = lerp(col, col * np.array([0.93, 0.93, 1.03], np.float32), np.clip((SUN[2] - lamb) * 3, 0, 1) * 0.35)

    # kum taneleri
    g = _rng.random((N, N)).astype(np.float32)
    grains = np.zeros((N, N), np.float32)
    grains[g < 0.006] = -1
    grains[g > 0.993] = 1
    grains = np.asarray(Image.fromarray(((grains + 1) * 127.5).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 127.5 - 1
    col = col * (1 + 0.3 * grains * (1 - mats))[..., None]

    # --- hasır desenleri
    # yuvarlak: sarmal örgü (halka + çapraz dikiş), turkuaz iç halka, koyu dış örgü
    dm = q * 0.89
    ring = dm / 0.042 + (np.arctan2((Y - mc[1]) / mry, (X - mc[0]) / mrx) / (2 * np.pi))
    rf = np.mod(ring, 1.0)
    hump = np.sin(np.pi * rf)
    ang = np.arctan2((Y - mc[1]) / mry, (X - mc[0]) / mrx)
    nst = np.maximum(8, np.floor(ring) * 2 * np.pi * 0.042 / 0.032)
    braid = 0.5 + 0.5 * np.cos(ang * nst + rf * 2 * np.pi * 1.2 + np.floor(ring) * 1.7)
    straw = lerp(hexc('#AD8746'), hexc('#EFD497'), np.clip(hump ** 0.7 * (0.62 + 0.38 * braid), 0, 1))
    straw = lerp(straw, hexc('#D3AE68'), sstep(0.3, 0.8, fbm(30, 2)) * 0.25)
    accent = sstep(0.61, 0.625, q) * (1 - sstep(0.67, 0.685, q))
    straw = lerp(straw, lerp(hexc('#3A9EA0'), hexc('#6CCFC9'), hump * (0.6 + 0.4 * braid)), accent * 0.85)
    border = sstep(0.90, 0.915, q)
    straw = lerp(straw, straw * np.array([0.82, 0.76, 0.7], np.float32), border)
    # hasır kenarının ışık/gölge boyası: ışığa bakan kenar açık
    edge_band = sstep(0.93, 1.0, q)
    gxq, gyq = (X - mc[0]) / mrx, (Y - mc[1]) / mry
    toward = (gxq * SUN[0] + gyq * SUN[1]) / np.maximum(1e-4, np.sqrt(gxq ** 2 + gyq ** 2)) / math.hypot(SUN[0], SUN[1])
    straw = straw * (1 + edge_band * (0.10 * toward - 0.04))[..., None]

    # dikdörtgen: sepet örgüsü + iki renkli şerit + saçak
    cu, cv = np.floor(lu / 0.03), np.floor(lv / 0.03)
    chk = np.mod(cu + cv, 2)
    fu, fv = np.mod(lu, 0.03) / 0.03, np.mod(lv, 0.03) / 0.03
    weave = np.where(chk > 0, np.sin(np.pi * fu), np.sin(np.pi * fv))
    rect = lerp(hexc('#A9844A'), hexc('#E9CD93'), weave ** 0.6)
    stripe_a = (np.abs(np.abs(lv) - 0.25) < 0.05)
    stripe_b = (np.abs(lv) < 0.035)
    rect = lerp(rect, lerp(hexc('#C55B4E'), hexc('#EE8A73'), weave), stripe_a * 0.85)
    rect = lerp(rect, lerp(hexc('#2E8E93'), hexc('#5CC3C0'), weave), stripe_b * 0.85)
    rect_border = sstep(rh - 0.04, rh - 0.03, np.abs(lv)) + sstep(rw - 0.04, rw - 0.03, np.abs(lu))
    rect = lerp(rect, rect * 0.82, np.clip(rect_border, 0, 1))

    # hasır gölgeleri (kenar yüksekliği ~1 cm): ışığın tersine kayık, yumuşak
    def drop(mask, height, blur_px):
        off = height / math.tan(math.asin(SUN[2])) * PPM
        dx, dy = -SUN[0] / math.hypot(SUN[0], SUN[1]) * off, SUN[1] / math.hypot(SUN[0], SUN[1]) * off   # görüntü y aşağı
        m = Image.fromarray((mask * 255).astype(np.uint8))
        m = m.transform(m.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR)
        m = m.filter(ImageFilter.GaussianBlur(blur_px))
        return np.asarray(m).astype(np.float32) / 255

    mats_all = np.clip(mats + fringe * 0.9, 0, 1)
    sh = np.clip(drop(mats_all, 0.012, 3.5) - mats_all, 0, 1)
    ao = np.clip(np.asarray(Image.fromarray((mats_all * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))).astype(np.float32) / 255 - mats_all, 0, 1)
    shadow_tint = hexc('#6E5E86')
    dark = np.clip(sh * 0.38 + ao * 0.22, 0, 0.5)
    col = col * (1 - dark[..., None]) + shadow_tint * (dark * 0.18)[..., None]
    col = lerp(col, straw, mat_round)
    col = lerp(col, rect, mat_rect)
    col = lerp(col, hexc('#D9BC84'), fringe * 0.85)

    # --- kabuklar ve çakıllar
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8), 'RGB').convert('RGBA')
    shadow_layer = np.zeros((N, N), np.float32)
    rng = np.random.default_rng(SEED + 7)
    placed = []

    def free(x, y, rad):
        rr = math.sqrt((x / A) ** 2 + (y / B) ** 2)
        if rr > 1.045 or math.hypot(x - PET[0], y - PET[1]) < 0.75:
            return False
        qq = math.sqrt(((x - mc[0]) / mrx) ** 2 + ((y - mc[1]) / mry) ** 2)
        if qq < 1.08:
            return False
        uu = (x - rc[0]) * math.cos(ra) + (y - rc[1]) * math.sin(ra)
        vv = -(x - rc[0]) * math.sin(ra) + (y - rc[1]) * math.cos(ra)
        if abs(uu) < rw + 0.12 and abs(vv) < rh + 0.08:
            return False
        return all(math.hypot(x - px, y - py) > rad + pr for px, py, pr in placed)

    def weight(x, y):
        rr = math.sqrt((x / A) ** 2 + (y / B) ** 2)
        return 0.12 + 0.88 * float(sstep(0.55, 0.97, np.array(rr)))

    def put(sp, x, y, height):
        nonlocal shadow_layer
        px = int(round((x + HALF) * PPM - sp.size[0] / 2))
        py = int(round((HALF - y) * PPM - sp.size[1] / 2))
        a = np.asarray(sp.getchannel('A')).astype(np.float32) / 255
        off = height / math.tan(math.asin(SUN[2])) * PPM
        dx = int(round(-SUN[0] / math.hypot(SUN[0], SUN[1]) * off))
        dy = int(round(SUN[1] / math.hypot(SUN[0], SUN[1]) * off))
        blur = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 255
        h, w = blur.shape
        y0, x0 = py + dy, px + dx
        if 0 <= y0 and y0 + h < N and 0 <= x0 and x0 + w < N:
            shadow_layer[y0:y0 + h, x0:x0 + w] = np.maximum(shadow_layer[y0:y0 + h, x0:x0 + w], blur)
        img.alpha_composite(sp, (px, py))

    items = []
    tries = 0
    shells = [('scallop', 10), ('clam', 8), ('spiral', 7), ('dollar', 4), ('star', 3)]
    for kind, n in shells:
        k = 0
        while k < n and tries < 20000:
            tries += 1
            x, y = rng.uniform(-A * 1.05, A * 1.05), rng.uniform(-B * 1.05, B * 1.05)
            size = rng.uniform(0.10, 0.15) if kind != 'star' else rng.uniform(0.11, 0.14)
            if rng.random() > weight(x, y) or not free(x, y, size * 0.6):
                continue
            placed.append((x, y, size * 0.6))
            items.append((y, sprite_shell(kind, int(size * PPM), rng), x, y, 0.012))
            k += 1
    # çakıl öbekleri (kenara yakın) + tek tük
    for _ in range(9):
        while True:
            a_ = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0.8, 1.0)
            cx_, cy_ = A * rr * math.cos(a_), B * rr * math.sin(a_)
            if free(cx_, cy_, 0.12):
                break
        for _ in range(int(rng.integers(4, 9))):
            x, y = cx_ + rng.normal(0, 0.1), cy_ + rng.normal(0, 0.07)
            size = rng.uniform(0.05, 0.10)
            if free(x, y, size * 0.5):
                placed.append((x, y, size * 0.5))
                items.append((y, sprite_pebble(int(size * PPM), rng), x, y, 0.01))
    for _ in range(40):
        x, y = rng.uniform(-A, A), rng.uniform(-B, B)
        size = rng.uniform(0.04, 0.07)
        if rng.random() < weight(x, y) and free(x, y, size * 0.5):
            placed.append((x, y, size * 0.5))
            items.append((y, sprite_pebble(int(size * PPM), rng), x, y, 0.008))
    # arkadakiler önce (üst üste binerse öndeki üstte)
    base = np.asarray(img).astype(np.float32) / 255
    for _, sp, x, y, h in sorted(items, key=lambda it: -it[0]):
        put(sp, x, y, h)
    out = np.asarray(img).astype(np.float32) / 255
    rgb = out[..., :3]
    occupied = (np.asarray(img).astype(np.int16)[..., :3] != (base[..., :3] * 255).astype(np.int16)).any(-1)
    s = shadow_layer * (~occupied) * 0.42
    rgb = rgb * (1 - s[..., None]) + shadow_tint * (s * 0.2)[..., None]
    print('kabuk/çakıl', len(items))
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), 'RGB')


# ------------------------------------------------------------------ mesh (Blender) + FBX
def build_mesh_fbx(path):
    import bpy
    import bmesh
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new(NAME)
    ob = bpy.data.objects.new(NAME, me)
    bpy.context.scene.collection.objects.link(ob)
    seg = 96
    rings = [0.0, 0.18, 0.36, 0.54, 0.70, 0.84, 0.87, 0.9, 0.93, 0.96, 0.99, 1.0, 1.02, 1.04, 1.06, 1.08, 1.1, R_OUT]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    grid = []
    for ri, rr in enumerate(rings):
        row = []
        for k in range(seg if rr > 0 else 1):
            th = 2 * math.pi * k / seg
            x, y = A * rr * math.cos(th), B * rr * math.sin(th)
            z = float(profile(np.array(rr), np.array(th)))
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)

    def face(vs):
        f = bm.faces.new(vs)
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = ((co.x + HALF) / (2 * HALF), (co.y + HALF) / (2 * HALF))
        return f

    for k in range(seg):
        face([grid[0][0], grid[1][k], grid[1][(k + 1) % seg]])
    for ri in range(1, len(rings) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([grid[ri][k], grid[ri + 1][k], grid[ri + 1][k2], grid[ri][k2]])
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
    print('yazıldı', path, 'üçgen', sum(len(p.vertices) - 2 for p in me.polygons), 'genişlik', 2 * HALF)


# ------------------------------------------------------------------ önizleme (oyun kamerası, Cycles)
def preview(out_dir, samples=48):
    """Evim kamerası (HomeScreen.PetCamera: (0, 0,964, −4,924), dikey görüş 34°, 19,5:9), güneş Stage ile aynı yönde.
    önce: eski düz kum silindiri (#FFDB99); sonra: yeni zemin. Okti (çocuk) + Stage süsleri ölçek için."""
    import bpy
    from mathutils import Vector, Euler
    env = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')

    def setup():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device = 'CPU'
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.render.threads_mode = 'FIXED'
        sc.render.threads = 3
        sc.render.resolution_x, sc.render.resolution_y = 1300, 600
        sc.view_settings.view_transform = 'Standard'
        sc.view_settings.look = 'None'
        w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
        bg = w.node_tree.nodes['Background']
        bg.inputs['Color'].default_value = (0.36, 0.62, 0.95, 1)
        bg.inputs['Strength'].default_value = 0.4
        sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 5.0; sun.angle = math.radians(4)
        sun.color = (1.0, 0.89, 0.71)
        so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
        # Unity güneşi Euler(42, −32, 0): ışık yönü (Unity) = (−0,394, −0,669, 0,630) → Blender (x, y, z) = (x, z, y)
        so.rotation_euler = Vector((-0.394, 0.630, -0.669)).to_track_quat('-Z', 'Y').to_euler()
        cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(34)
        cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
        cam.location = (0, -4.924, 0.964)
        cam.rotation_euler = Euler((math.radians(90), 0, 0))
        return sc

    def mat(name, color=None, tex=None, rough=0.9):
        m = bpy.data.materials.new(name); m.use_nodes = True
        p = m.node_tree.nodes['Principled BSDF']
        p.inputs['Roughness'].default_value = rough
        p.inputs['Specular IOR Level'].default_value = 0.2
        if tex:
            t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(tex)
            m.node_tree.links.new(t.outputs['Color'], p.inputs['Base Color'])
        else:
            p.inputs['Base Color'].default_value = (*color, 1)
        return m

    def srgb(h):
        c = hexc(h)
        return tuple(float(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c)

    def fbx(name, loc, footprint=None, height=None, yaw=0.0):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(env, name, name + '.fbx') if '/' not in name else name)
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == 'MESH']
        tex = None
        base = name.split('/')[-1].replace('.fbx', '')
        for ext in ('png', 'jpg'):
            p = os.path.join(os.path.dirname(name) if '/' in name else os.path.join(env, name), f'{base}_basecolor.{ext}')
            if os.path.exists(p):
                tex = p
        m = mat(base, tex=tex, rough=0.7) if tex else mat(base, (0.8, 0.8, 0.8))
        for o in meshes:
            o.data.materials.clear(); o.data.materials.append(m)
        root = bpy.data.objects.new(base + '_root', None); bpy.context.scene.collection.objects.link(root)
        for o in new:
            if o.parent is None:
                o.parent = root
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        s = 1.0
        if footprint:
            s = footprint / max(hi.x - lo.x, hi.y - lo.y)
        elif height:
            s = height / (hi.z - lo.z)
        root.scale = (s, s, s)
        root.rotation_euler = (0, 0, math.radians(yaw))
        # Unity (x, y, z) → Blender (x, z, y); taban: footprint = orijin, height = alt kenar
        root.location = (loc[0], loc[2], loc[1] - (lo.z * s if height else 0))
        return root

    def scene(new_floor):
        sc = setup()
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=20, depth=0.04, location=(0, 0, -0.12))   # su (Stage ile aynı)
        bpy.context.active_object.data.materials.append(mat('water', srgb('#40BFF2'), rough=0.2))
        if new_floor:
            fbx(os.path.join(OUT, NAME + '.fbx'), (0, 0, CENTER_Z), footprint=2 * HALF)
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1, depth=2, location=(0, CENTER_Z, -0.05))
            o = bpy.context.active_object; o.scale = (3.3, 3.1, 0.06)
            o.data.materials.append(mat('sand', srgb('#FFDB99'), rough=0.85))
        pet = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Pets', 'pet_13_yavru', 'pet_13_yavru.fbx')
        if os.path.exists(pet):
            fbx(pet, (0, 0, 0), height=1.75 * 0.8, yaw=18)
        fbx('p_flowers', (-2.9, -0.05, 0.5), footprint=0.8, yaw=190)
        fbx('p_rock', (2.95, -0.05, 1.4), footprint=0.8, yaw=160)
        fbx('p_lantern', (2.5, -0.05, 3.1), footprint=0.5, yaw=200)
        fbx('palm', (-1.45, -0.05, 2.4), height=2.6, yaw=60)
        fbx('palm', (1.5, -0.05, 3.2), height=2.1, yaw=-140)
        if new_floor:   # ön kenarda hafif 3B süsler (Stage.Build ile aynı yerler)
            for name, pos, fp, yaw in FRONT_PROPS:
                fbx(name, pos, footprint=fp, yaw=yaw)
        return sc

    os.makedirs(out_dir, exist_ok=True)
    for new_floor, tag in ((False, 'once'), (True, 'sonra')):
        sc = scene(new_floor)
        sc.render.filepath = os.path.join(out_dir, f'evim_zemin_{tag}.png')
        bpy.ops.render.render(write_still=True)
        print('yazıldı', sc.render.filepath)


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    tex = os.path.join(OUT, NAME + '_basecolor.jpg')
    if '--no-tex' not in argv:
        im = build_texture()
        im.save(tex, quality=90, optimize=True, subsampling=0)
        print('yazıldı', tex, im.size)
    if '--tex-only' not in argv:
        build_mesh_fbx(os.path.join(OUT, NAME + '.fbx'))
    if '--preview' in argv:
        preview(argv[argv.index('--preview') + 1])


if __name__ == '__main__':
    main(sys.argv[1:])
