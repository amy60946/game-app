# ui_hand.py çıktısına çizgi film konturu + yumuşak gölge ekler. Kullanım: python3 ui_hand_outline.py girdi.png çıktı.png
import sys
from PIL import Image, ImageFilter
im = Image.open(sys.argv[1]).convert('RGBA')
pad = 12; W, H = im.size
src = Image.new('RGBA', (W + pad * 2, H + pad * 2)); src.alpha_composite(im, (pad, pad))
a = src.split()[3].point(lambda v: 255 if v > 90 else 0)
ring = a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(0.8))
shadow = a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(5)).point(lambda v: v * 0.35)
out = Image.new('RGBA', src.size)
out.paste((40, 25, 10, 255), (4, 7), shadow)
line = Image.new('RGBA', src.size, (120, 50, 10, 255)); line.putalpha(ring)
out.alpha_composite(line); out.alpha_composite(src)
out.resize((256, 256), Image.LANCZOS).save(sys.argv[2])
