# Pişmiş zemin dokusunda (ground_v6.png) kanyon tabanı ve kaya kenarı: üstten bakışta sıkışan yüksek frekanslı çakıl/çatlak
# gürültüsü yumuşatılır (oyunda dik yüzleri gölgelendirici çizer). Kanyon tabanı ılık kum-çakıl tonuna çekilir.
#   python3 soften_ground.py <terr.npz>
import sys, os, numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'Assets', '_Pofi', 'Resources', 'Env', 'ground_v6', 'ground_v6.png'))
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
