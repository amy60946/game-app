# Pişmiş zemin dokusunda (ground_v6.png) kanyon tabanı ve kaya kenarı: üstten bakışta sıkışan yüksek frekanslı çakıl/çatlak
# gürültüsü yumuşatılır (oyunda dik yüzleri gölgelendirici çizer). Kanyon tabanı ılık kum-çakıl tonuna çekilir.
#   python3 soften_ground.py <terr.npz>
#   python3 soften_ground.py --grade-only   (yalnız renk ayarı; pişirmeden sonra bir kez — soften zaten çağırır)
import sys, os, numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'Assets', '_Pofi', 'Resources', 'Env', 'ground_v6', 'ground_v6.png'))
def grade(P):
    """Oyun ışığında taslağın doğal tonu (22 Ekim 2026 karşılaştırması): çimen biraz koyu ve az doygun, patika/kamp
    toprağı turuncudan soluk kahveye, genel doygunluk hafif düşük. Kum ve kar değişmez."""
    im = Image.open(P).convert('RGBA'); a = np.asarray(im).astype(np.float32); rgb = a[..., :3] / 255.0
    mx = rgb.max(-1); mn = rgb.min(-1); c = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hue = np.where(mx == r, ((g - b) / c) % 6, np.where(mx == g, (b - r) / c + 2, (r - g) / c + 4)) * 60
    sat = c / (mx + 1e-6)
    green = np.clip(1 - np.abs(hue - 100) / 45, 0, 1) * np.clip((sat - 0.2) / 0.2, 0, 1)
    orange = np.clip(1 - np.abs(hue - 33) / 16, 0, 1) * np.clip((sat - 0.35) / 0.2, 0, 1)
    lum = (rgb * np.array([0.3, 0.59, 0.11])).sum(-1, keepdims=True)
    k = 1 - (0.08 + 0.18 * green[..., None] + 0.3 * orange[..., None])                 # doygunluk azaltma
    out = lum + (rgb - lum) * k
    out *= (1 - 0.12 * green[..., None] - 0.06 * orange[..., None])                   # çimen biraz koyu
    a[..., :3] = np.clip(out, 0, 1) * 255
    Image.fromarray(a.astype(np.uint8), 'RGBA').save(P, optimize=True)

if sys.argv[1] == '--grade-only':
    grade(P); print('renk ayarı'); sys.exit(0)
d = np.load(sys.argv[1])
im = Image.open(P).convert('RGBA'); W, H = im.size
def mask(a, blur=4):
    m = Image.fromarray((np.clip(a, 0, 1)[::-1] * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(blur)), np.float32)[..., None] / 255
rgb = np.asarray(im, np.float32)[..., :3]; alpha = np.asarray(im)[..., 3:]
soft = np.asarray(im.convert('RGB').filter(ImageFilter.GaussianBlur(5)), np.float32)
soft2 = np.asarray(im.convert('RGB').filter(ImageFilter.GaussianBlur(2)), np.float32)
can = mask(d['canyon'])
gz, gx = np.gradient(d['h'], 0.2); slope = np.hypot(gx, gz)
rock = mask(np.clip((slope - 0.6) / 0.6, 0, 1), 3)
sand = np.array([214, 192, 150], np.float32)
canf = soft * 0.55 + sand * 0.45
out = rgb * (1 - can) + canf * can
out = out * (1 - rock * 0.7) + soft2 * (rock * 0.7)
Image.fromarray(np.concatenate([np.clip(out, 0, 255).astype(np.uint8), alpha], -1), 'RGBA').save(P, optimize=True)
print('ok', W, H)
grade(P)
