# Meshy 3x3 simge sayfasını hücrelere böler, beyaz arka planı kenarlardan sel dolgusuyla saydamlaştırır.
#   python3 cut_sheet.py sayfa.png çıktı_klasörü ad1 ad2 ... ad9
import sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops
src, outd, names = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(outd, exist_ok=True)
im = Image.open(src).convert('RGB'); W, H = im.size; cw, ch = W // 3, H // 3
for i, name in enumerate(names):
    if name == '-': continue
    c = im.crop(((i % 3) * cw, (i // 3) * ch, (i % 3 + 1) * cw, (i // 3 + 1) * ch))
    # beyaza yakın ve kenara bağlı pikseller = arka plan
    m = c.copy()
    for xy in ((0, 0), (cw - 1, 0), (0, ch - 1), (cw - 1, ch - 1), (cw // 2, 0), (cw // 2, ch - 1), (0, ch // 2), (cw - 1, ch // 2)):
        ImageDraw.floodfill(m, xy, (255, 0, 255), thresh=28)
    r, g, b = m.split()
    bg = ImageChops.multiply(r.point(lambda v: 255 if v > 250 else 0), ImageChops.multiply(g.point(lambda v: 255 if v < 5 else 0), b.point(lambda v: 255 if v > 250 else 0)))
    alpha = ImageChops.invert(bg).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    o = c.convert('RGBA'); o.putalpha(alpha)
    bb = o.getbbox(); o = o.crop(bb) if bb else o
    o.save(os.path.join(outd, name + '.png'))
print('ok', len([n for n in names if n != '-']))
