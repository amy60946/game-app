# Kuşbakışı harita görseline bölge adları (onay sayfası için). python3 map_labels.py <harita_ust.png> <çıktı.jpg> <yazı tipi.ttf>
import sys, os
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terrain_v6 as TV
src, dst, font = sys.argv[1:4]
im = Image.open(src).convert('RGB'); W, H = im.size
sw = TV.X1 - TV.X0 - 10; sh = sw * H / W
def px(x, z): return ((x + sw / 2) / sw * W, (sh / 2 - z) / sh * H)
dr = ImageDraw.Draw(im, 'RGBA'); F = ImageFont.truetype(font, max(16, W // 70)); F2 = ImageFont.truetype(font, max(14, W // 85))
names = [(r[1], r[2], r[3], 0) for r in TV.REGIONS]
extra = [('Tapınak', 28, 38), ('Kaya Tepe', 9, 31), ('Kanyon', -6, 16), ('Kamp', 54, -3), ('Çam Ormanı', 52, 24), ('Çiçek Çayırı', -44, -6), ('Göl', -28, 1),
         ('Kayak Pisti', -46, 47), ('Kaya sütunu', 76, -47)]
names += [(n, x, z, 1) for (n, x, z) in extra]
for (n, x, z, kind) in names:
    u, v = px(x, z); f = F if kind == 0 else F2
    tw, th = dr.textbbox((0, 0), n, font=f)[2:]
    bx = (u - tw / 2 - 10, v - th / 2 - 6, u + tw / 2 + 10, v + th / 2 + 8)
    dr.rounded_rectangle(bx, radius=12, fill=(255, 255, 255, 225) if kind == 0 else (35, 60, 40, 200))
    dr.text((u - tw / 2, v - th / 2), n, font=f, fill=(35, 48, 31) if kind == 0 else (240, 248, 235))
# ölçek çubuğu
u0, v0 = W * 0.06, H * 0.95; L = 20 / sw * W
dr.rectangle((u0, v0, u0 + L, v0 + 6), fill=(255, 255, 255, 230)); dr.text((u0, v0 - 30), '20 m', font=F2, fill=(255, 255, 255))
dr.text((W * 0.93, H * 0.04), 'K ↑', font=F, fill=(255, 255, 255))
im.save(dst, quality=88); print(W, H)
