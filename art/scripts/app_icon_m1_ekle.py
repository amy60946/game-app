"""M1 simgesine kum ayrıntıları + daha görünür fener (kullanıcı, 23 Kasım 2026: "M1'e A2'deki kum üzerindeki detayları ekle;
M1'e entegre için A1'deki gibi fener daha görünür olabilir; şimdiki M1 versiyonu hâlâ koru").

M1'in Okti'si ve sahnesi piksel piksel korunur. Meshy denemeleri (app_icon_m1_kum1/kum2) resmi baştan çizdiği için yalnız parçaları
alınır: kum2'nin feneri + adacığı (M1 ile aynı sıcak gün doğumu ışığı) ve kumdaki küçük öğeler (deniz yıldızı, külah kabuk, çakıl, küçük
kabuklar). Her parça yerel kum/gök renginden ayrılarak kesilir, M1'in ışığına göre renklenir, gölgesi M1'deki gibi sol-alta düşer.
A2'nin asıl kum ayrıntısı (ince tane + rüzgâr dalgacıkları) M1'in kumuna hafif doku olarak işlenir. Konumlar alt ajan ölçümünden.

    python3 -I art/scripts/app_icon_m1_ekle.py <çıktı.png>
Rozet sonra: python3 -I art/scripts/app_icon_moyo.py <simge.png> <çıktı.png>
"""
import glob, os, sys
import numpy as np, cv2
from scipy import ndimage

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = sys.argv[1]
src = lambda name: cv2.cvtColor(cv2.imread(glob.glob(os.path.join(ROOT, "art", "meshy", "out", name, "concept_*.png"))[0]), cv2.COLOR_BGR2RGB).astype(np.float32)
M1 = src("app_icon_k1_m1"); K2 = src("app_icon_m1_kum2"); K1 = src("app_icon_m1_kum1")
img = M1.copy()
S = 1024
rng = np.random.default_rng(3)

# ---------------------------------------------------------------- 1) eski adacığı sil, kum2'nin fenerini koy
y0, y1, x0 = 296, 394, 892
ref = img[y0:y1, 856:890].mean(axis=1)                          # her satırda adacığın solundaki gök/deniz
img[y0:y1, x0:] = ref[:, None, :] + rng.normal(0, 1.2, (y1 - y0, S - x0, 3))
img[y0 - 4:y1 + 4, x0 - 6:x0 + 6] = cv2.GaussianBlur(img, (0, 0), 2)[y0 - 4:y1 + 4, x0 - 6:x0 + 6]

def grabcut_cut(im, box, pad=10):
    bx0, by0, bx1, by1 = box
    crop = im[max(by0 - pad, 0):by1 + pad, max(bx0 - pad, 0):min(bx1 + pad, S)].astype(np.uint8).copy()
    m = np.zeros(crop.shape[:2], np.uint8); bg = np.zeros((1, 65)); fg = np.zeros((1, 65))
    r = (min(pad, bx0), min(pad, by0), (min(bx1, S - 1) - bx0), (by1 - by0))
    cv2.grabCut(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), m, r, bg, fg, 8, cv2.GC_INIT_WITH_RECT)
    a = ((m == 1) | (m == 3)).astype(np.float32)
    lab, n = ndimage.label(a > 0)
    if n: a = (lab == (np.argmax(ndimage.sum(a, lab, range(1, n + 1))) + 1)).astype(np.float32)
    a = ndimage.binary_fill_holes(a > 0).astype(np.float32)
    a = cv2.GaussianBlur(ndimage.binary_erosion(a > 0, iterations=1).astype(np.float32), (0, 0), 0.8)
    return crop.astype(np.float32), a

lh, la = grabcut_cut(K2, (770, 53, 1024, 404))
# deniz şeridini kes: suyun (turkuaz) altta kalan kısmı fenerin parçası değil
hsv = cv2.cvtColor(lh.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(float)
water = (hsv[..., 0] * 2 > 160) & (hsv[..., 0] * 2 < 220) & (hsv[..., 1] > 60)
la = la * (~ndimage.binary_dilation(water, iterations=1)).astype(np.float32)
# M1 göğüne uyum: kum2 göğü daha turuncu → nesnenin rengine %25 oranında göğün oranı, + %8 uzaklık pusu
sky_k2 = np.array([247, 145, 71], np.float32); sky_m1 = np.array([255, 205, 115], np.float32)
lh = lh * (1 + 0.25 * (sky_m1 / sky_k2 - 1))
lh = lh * 0.92 + sky_m1 * 0.08
sc = 0.43
lh = cv2.resize(lh, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); la = cv2.resize(la, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
ys, xs = np.where(la > 0.5)
base_y = 391                                                     # M1 sağ ufuk / adacık su çizgisi
oy = base_y - ys.max(); ox = S - la.shape[1]
h, w = la.shape
def paste(im, rgb, a, ox, oy):
    X0, Y0 = max(ox, 0), max(oy, 0); X1, Y1 = min(ox + a.shape[1], S), min(oy + a.shape[0], S)
    aa = a[Y0 - oy:Y1 - oy, X0 - ox:X1 - ox, None]
    im[Y0:Y1, X0:X1] = im[Y0:Y1, X0:X1] * (1 - aa) + rgb[Y0 - oy:Y1 - oy, X0 - ox:X1 - ox] * aa
paste(img, lh, la, ox, oy)
# su çizgisinde ince yansıma/köpük: adacık tabanının altına yumuşak koyu yansıma
ref_strip = np.zeros_like(la); ref_strip[ys.max() - 6:ys.max() + 1] = la[ys.max() - 6:ys.max() + 1]
refl = cv2.GaussianBlur(np.flipud(la[:ys.max() + 1])[:14], (0, 0), 2.0) * 0.18
if refl.size:
    Y0 = base_y + 1; ry = refl.shape[0]
    X0, X1 = max(ox, 0), min(ox + w, S)
    rr = refl[:min(ry, S - Y0), X0 - ox:X1 - ox, None]
    img[Y0:Y0 + rr.shape[0], X0:X1] = img[Y0:Y0 + rr.shape[0], X0:X1] * (1 - rr) + np.array([120, 90, 70]) * rr
print("fener+adacık:", "x", ox + xs.min(), "–", ox + xs.max(), " y", oy + ys.min(), "–", oy + ys.max())

# ---------------------------------------------------------------- 2) kum öğeleri
def cut_item(im, box, pad=6):
    bx0, by0, bx1, by1 = box
    c = im[by0 - pad:by1 + pad, bx0 - pad:bx1 + pad].copy()
    border = np.concatenate([c[:3].reshape(-1, 3), c[-3:].reshape(-1, 3), c[:, :3].reshape(-1, 3), c[:, -3:].reshape(-1, 3)])
    sand = np.median(border, axis=0)
    ratio = c / np.maximum(sand, 1)
    d = np.abs(c - sand).sum(2)
    shadow = (ratio.std(2) < 0.06) & (ratio.mean(2) < 0.97)           # yalnız kararmış kum = gölge, nesne değil
    a = np.clip((d - 22) / 30, 0, 1) * (~shadow)
    a = ndimage.binary_fill_holes(ndimage.binary_closing(a > 0.5, iterations=2)).astype(np.float32)
    lab, n = ndimage.label(a > 0)
    if n: a = (lab == (np.argmax(ndimage.sum(a, lab, range(1, n + 1))) + 1)).astype(np.float32)
    a = cv2.GaussianBlur(ndimage.binary_erosion(a > 0, iterations=1).astype(np.float32), (0, 0), 0.7)
    return c, a, sand

def place_item(im, source, box, centre, scale, rot=0.0):
    c, a, sand = cut_item(source, box)
    cx, cy = centre
    local = im[cy - 12:cy + 12, cx - 12:cx + 12].reshape(-1, 3)
    m1sand = np.median(local, axis=0)
    c = c * (1 + 0.6 * (m1sand / np.maximum(sand, 1) - 1))           # M1 kumunun ışığına
    if rot:
        M = cv2.getRotationMatrix2D((c.shape[1] / 2, c.shape[0] / 2), rot, 1.0)
        c = cv2.warpAffine(c, M, (c.shape[1], c.shape[0]), borderMode=cv2.BORDER_REPLICATE); a = cv2.warpAffine(a, M, (a.shape[1], a.shape[0]))
    c = cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA); a = cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    h, w = a.shape
    ox, oy = cx - w // 2, cy - h // 2
    # temas gölgesi: sol-alta 5 px, sıcak kahve, %35
    sh = np.zeros((S, S), np.float32)
    sh[oy + 4:oy + 4 + h, ox - 5:ox - 5 + w] = a
    sh = cv2.GaussianBlur(sh, (0, 0), 3.0) * 0.35
    im[:] = im * (1 - sh[..., None]) + np.array([200, 150, 90], np.float32) * sh[..., None] * (im / 240.0)
    paste(im, c, a, ox, oy)
    return (ox, oy, ox + w, oy + h)

items = [
    ("deniz yıldızı", K2, (308, 840, 428, 920), (425, 945), 0.75, -8),
    ("külah kabuk", K2, (180, 912, 280, 960), (605, 962), 0.85, 6),
    ("çakıl", K2, (696, 751, 756, 781), (40, 655), 0.7, 0),
    ("pembe kabuk", K1, (790, 640, 843, 672), (982, 652), 0.8, 0),
    ("küçük çakıl", K2, (190, 830, 244, 860), (655, 930), 0.5, 20),
    ("beyaz kabuk", K2, (468, 860, 508, 890), (348, 975), 0.8, -15),
]
for name, s, box, cen, scl, rot in items:
    b = place_item(img, s, box, cen, scl, rot)
    print("%-14s" % name, b)

# ---------------------------------------------------------------- 3) A2'deki gibi ince kum dokusu (yalnız açık kumda)
hsv = cv2.cvtColor(np.clip(M1, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(float)
H, Sa, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
sandm = (H > 24) & (H < 48) & (Sa > 0.25) & (Sa < 0.7) & (V > 0.62) & (yy > 625)
sandm = ndimage.binary_opening(sandm, iterations=3)
sandm = cv2.GaussianBlur(sandm.astype(np.float32), (0, 0), 6)
noise = cv2.GaussianBlur(rng.normal(0, 1, (S, S)).astype(np.float32), (0, 0), 0.7) * 3.0
warp = cv2.GaussianBlur(rng.normal(0, 1, (S, S)).astype(np.float32), (0, 0), 40) * 260
ripple = np.sin((yy * 0.11 + xx * 0.018 + warp * 0.02)) * 2.6 * np.clip((yy - 640) / 200, 0, 1)
img = img + (noise + ripple)[..., None] * sandm[..., None] * np.array([1.0, 0.92, 0.75], np.float32)

cv2.imwrite(OUT, cv2.cvtColor(np.clip(img, 0, 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
print("yazıldı", OUT)
