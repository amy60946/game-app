# Kumsal sahnesi (giriş + tanışma ekranlarının arka planı, Resources/Art/pick_stage.jpg) — 24 Ekim 2026, kullanıcı:
# "kum zemin ve deniz detayları daha zengin". Kaynak: Meshy görseli art/meshy/out/pick_stage2 (karaktersiz kumsal).
# Kredisiz, yalnız görüntü işleme (numpy + PIL): 2048 genişliğe büyütme, kum tepecikleri (yer düzlemi perspektifiyle gölgelenen
# yumuşak tümsekler), rüzgâr çizgileri, ıslak kum şeridi + kıyıda dantel köpük izi, kum tanesi, denizde parıltılar.
# Okti'nin durduğu düz alan (ekranın sol-ortası) tümseksiz kalır. Deniz parıltılarının konumları (u, v) yazdırılır:
# oyunda bunlar yanıp söner (World/Stage.cs BeachGlintSpots → World/BeachFx.cs BeachGlints; görsel değişirse liste de).
# Kullanım: python3 -I art/scripts/beach_stage.py art/meshy/out/pick_stage2/concept_01a167cf_0.png Assets/_Pofi/Resources/Art/pick_stage.jpg [ayıklama_öneki]
import sys
import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
W = 2048
rng = np.random.default_rng(7)

img = Image.open(SRC).convert('RGB')
H = round(img.height * W / img.width)
img = img.resize((W, H), Image.LANCZOS)
a = np.asarray(img).astype(np.float32) / 255.0
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def blur(m, r):
    im = Image.fromarray(np.clip(m * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0


def hsv(c):
    mx = c.max(-1); mn = c.min(-1); d = mx - mn + 1e-6
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-6), mx


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def vnoise(x, y, seed):
    # değer gürültüsü (yumuşak), ızgara 1 birim
    r = np.random.default_rng(seed)
    g = r.random((256, 256)).astype(np.float32)
    xi = np.floor(x).astype(int); yi = np.floor(y).astype(int); fx = x - xi; fy = y - yi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    def at(i, j): return g[j % 256, i % 256]
    return (at(xi, yi) * (1 - fx) + at(xi + 1, yi) * fx) * (1 - fy) + (at(xi, yi + 1) * (1 - fx) + at(xi + 1, yi + 1) * fx) * fy


h, s, v = hsv(a)
HOR = 422 / 768 * H                       # ufuk çizgisi
# --- kıyı çizgisi: her sütunda alttan yukarı kum biten yer (köpük/su başlar)
sandish = (h > 26) & (h < 48) & (s > 0.18) & (s < 0.5) & (v > 0.72)
raw = np.full(W, np.nan, np.float32)
for x in range(W):
    col = sandish[:, x]
    y = int(HOR + 30)
    while y < 0.8 * H and not col[y:y + 8].all(): y += 1                  # ufuktan aşağı: kumun başladığı ilk satır
    if y < 0.8 * H: raw[x] = y
trunk = (h > 12) & (h < 34) & (s > 0.4) & (v < 0.82)                    # palmiye gövdesi kıyıyı örtüyor
for x in range(W):
    if not np.isnan(raw[x]) and trunk[max(0, int(raw[x]) - 60):int(raw[x]) + 4, x].any(): raw[x] = np.nan
def runmed(v, n):
    p = np.pad(v, n // 2, mode='edge')
    return np.array([np.nanmedian(p[i:i + n]) for i in range(len(v))], np.float32)
ref = runmed(raw, 301)
raw[np.abs(raw - ref) > 18] = np.nan                                    # palmiye gövdesi vb. kaçamaklar
ok = ~np.isnan(raw)
raw = np.interp(np.arange(W), np.flatnonzero(ok), raw[ok]).astype(np.float32)
k = np.ones(41) / 41
shore = np.convolve(np.pad(runmed(raw, 41), 20, mode='edge'), k, mode='valid').astype(np.float32)
d = yy - shore[None, :]                   # kıyıdan aşağı uzaklık (px)

# --- maskeler: kum (kabuk, deniz yıldızı, palmiye gövdesi hariç), deniz bandı
sand = (sandish & (d > 1)).astype(np.float32)
sand = blur(sand, 1.2) * (d > -2)
sea = ((yy > HOR + 6) & (d < -10) & (h > 170) & (h < 205) & (s > 0.15)).astype(np.float32)

# --- yer düzlemi (göz hizası kamera): satır → derinlik Z (m), sütun → X (m)
HC, F = 1.6, (H / 2) / np.tan(np.radians(20))
Z = HC * F / np.maximum(yy - HOR, 1.0)
X = (xx - W / 2) * Z / F

# kum tepecikleri: yayvan tümsekler (X'te uzun), Okti'nin durduğu alan düz
hf = np.zeros_like(Z)
mounds = [(-9.0, 9.5, 3.6, 2.2, 0.22), (-5.5, 15.0, 4.2, 2.6, 0.26), (3.5, 12.5, 3.8, 2.3, 0.2), (8.5, 8.5, 3.2, 2.0, 0.2),
          (10.5, 15.5, 4.5, 2.8, 0.24), (-2.0, 18.0, 5.0, 2.5, 0.16), (5.2, 5.6, 2.2, 1.4, 0.12), (-11.5, 16.5, 4.0, 2.4, 0.2),
          (-3.4, 9.6, 2.0, 1.4, 0.2), (1.6, 11.0, 2.5, 1.5, 0.2), (2.6, 5.4, 1.6, 1.0, 0.14)]
for mx_, mz, rx, rz, ht in mounds:
    hf += ht * np.exp(-(((X - mx_) / rx) ** 2 + ((Z - mz) / rz) ** 2))
hf += 0.05 * (vnoise(X * 0.35, Z * 0.5, 3) - 0.5)
flat = np.exp(-(((X + 1.5) / 2.6) ** 2 + ((Z - 7.0) / 2.2) ** 2))   # Okti'nin "sahnesi"
hf *= 1 - 0.92 * flat
dzx = np.gradient(hf, axis=1) / np.maximum(np.gradient(X, axis=1), 1e-4)
dzz = np.gradient(hf, axis=0) / np.minimum(np.gradient(Z, axis=0), -1e-4)
nx, ny, nz = -dzx, np.ones_like(hf), -dzz
nl = np.sqrt(nx * nx + ny * ny + nz * nz)
L = np.array([-0.5, 0.75, -0.42]); L /= np.linalg.norm(L)                # ışık: sol üst önden (görseldeki gölgelerle aynı)
diff = (nx * L[0] + ny * L[1] + nz * L[2]) / nl / L[1]
dune = np.clip(1 + (diff - 1) * 1.7, 0.84, 1.1)
dune = dune * (1 - 0.035 * smooth(0.02, 0.0, hf))                        # çukurlar hafif koyu

# rüzgâr çizgileri: kıyıya koşut, dalgalı; ekranda sık düşen yerde (uzakta) söner
LAM = 0.38
phase = (Z + 0.3 * np.sin(0.42 * X) + 0.14 * np.sin(1.3 * X + 0.8 * Z) + 0.6 * vnoise(X * 0.25, Z * 0.25, 5)) / LAM
px_per = LAM * HC * F / (Z * Z)                                          # bir çizgi aralığı kaç piksel
fr = phase - np.floor(phase)
prof = smooth(0.0, 0.62, fr) - smooth(0.62, 1.0, fr)                     # yavaş çıkış, keskin sırt
ripple = (prof * 2 - 1) * smooth(5, 14, px_per) * smooth(0.25, 0.65, vnoise(X * 0.3 + 7, Z * 0.3, 9))
ripple *= (1 - 0.8 * flat)

# ıslak kum şeridi + dantel köpük izi (eski dalganın bıraktığı)
# dalganın çekildiği yerin kenarı fistonlu (yay yay); şerit kıyıya yakın ufka doğru incelir
per = 150 + 90 * vnoise(xx / 400.0, 0 * yy, 11)
ph = np.cumsum(1.0 / per[0]) * 2 * np.pi                              # sütun başına faz (değişken aralıklı yaylar)
scal = np.abs(np.sin(ph / 2))[None, :]
wet_w = (16 + 20 * scal + 10 * vnoise(xx / 90.0, 0 * yy, 12)) * np.clip((shore[None, :] - HOR) / 120, 0.6, 1.4)
wet = smooth(wet_w + 3, wet_w * 0.4, d) * (d > 0)
# köpük izi: ıslak kenarda yumuşak, sürekli ama yer yer incelen açık çizgi + seyrek kabarcık
lace = np.exp(-((d - wet_w) / 2.2) ** 2) * (0.45 + 0.55 * smooth(0.3, 0.7, vnoise(xx / 60.0, 0 * yy, 33)))
bub = (rng.random((H, W)) > 0.985).astype(np.float32) * np.exp(-((d - wet_w + 4) / 5.0) ** 2)
lace = 0.75 * lace + 0.9 * blur(bub, 0.8) * 3

grain = (rng.random((H, W)).astype(np.float32) - 0.5)
grain = blur(grain * 0.5 + 0.5, 0.6) * 2 - 1
speck = (rng.random((H, W)) > 0.9965).astype(np.float32) * (rng.random((H, W)) - 0.4).astype(np.float32)
speck = blur(speck * 0.5 + 0.5, 0.7) * 2 - 1

out = a.copy()
lum = dune * (1 + 0.04 * ripple * (1 - wet)) * (1 + 0.035 * grain + 0.5 * speck)
out = out * (1 + (lum[..., None] - 1) * sand[..., None])
wet_mul = np.array([0.84, 0.78, 0.70], np.float32)                        # ıslak kum: koyu, sıcak
out = out * (1 - (wet * sand)[..., None] * (1 - wet_mul))
sheen = smooth(10, 0, d) * (d > 0) * sand                                 # su kenarında gökyüzü yansıması
out = out * (1 - 0.18 * sheen[..., None]) + np.array([0.86, 0.95, 0.98], np.float32) * 0.18 * sheen[..., None]
lace = np.clip(lace, 0, 1) * 0.6 * sand
out = out * (1 - lace[..., None]) + np.array([0.99, 0.98, 0.95], np.float32) * lace[..., None]
if len(sys.argv) > 3:   # ayıklama: kıyı çizgisi ve tümsek gölgesi
    dbg = (a * 255).astype(np.uint8).copy()
    dbg[np.clip(shore.astype(int), 0, H - 1), np.arange(W)] = (255, 0, 0)
    Image.fromarray(dbg).save(sys.argv[3] + '_shore.png')
    Image.fromarray(np.clip((dune - 0.84) / 0.26 * 255, 0, 255).astype(np.uint8)).save(sys.argv[3] + '_dune.png')

# deniz: kıyı bandında ince dantel köpük, parıltı çizgileri ve yıldız parıltıları
seaband = sea * smooth(-70, -14, d)
lace2 = smooth(0.55, 0.7, vnoise(xx / 9.0, yy / 2.4, 21) * 0.7 + vnoise(xx / 31.0, yy / 6.0, 23) * 0.3) * seaband
out = out * (1 - 0.35 * lace2[..., None]) + 0.97 * 0.35 * lace2[..., None]
glints = []
gl = np.zeros((H, W), np.float32)
tries = 0
while len(glints) < 22 and tries < 5000:
    tries += 1
    gx = rng.uniform(80, W - 80); gy = rng.uniform(HOR + 14, H)
    xi, yi = int(gx), int(gy)
    if sea[yi, xi] < 1 or d[yi, xi] > -24 or xx[0, xi] > 0.72 * W and gy < HOR + 40: continue
    if any((gx - p[0]) ** 2 + ((gy - p[1]) * 3) ** 2 < 140 ** 2 for p in glints): continue
    glints.append((gx, gy))
for i, (gx, gy) in enumerate(glints[:10]):                               # görselde sabit olanlar (küçük)
    r = 5 + 4 * (i % 3)
    dx, dy = np.abs(xx - gx), np.abs(yy - gy)
    star = np.exp(-(dx / (r * 1.4)) ** 2 - (dy / 1.1) ** 2) + np.exp(-(dy / (r * 0.8)) ** 2 - (dx / 1.1) ** 2)
    star += 0.8 * np.exp(-(dx * dx + dy * dy) / (r * 0.5) ** 2)
    gl = np.maximum(gl, np.clip(star, 0, 1))
out = out * (1 - 0.85 * gl[..., None]) + np.array([1.0, 0.99, 0.94]) * 0.85 * gl[..., None]

Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)).save(OUT, quality=88, optimize=True, progressive=True)
print('boyut', W, H)
print('parıltılar (u, v; v alttan):')
print(', '.join('(%.3f, %.3f)' % (gx / W, 1 - gy / H) for gx, gy in glints[10:]))
