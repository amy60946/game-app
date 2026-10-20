# Bahçe v4 arayüz taslağı (ÖN TASARIM): yandan açılan küçük panel + tarlada eylem animasyonu storyboard'u.
#   python3 garden_ui_v4.py <klasör>   (klasörde garden_v4_genel.png, garden_v4_yatak.png, can_icon.png olmalı)
import sys, os, math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

D = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
RES = os.path.join(ROOT, 'Assets/_Pofi/Resources')
FONT = os.path.join(RES, 'Fonts/Baloo2-ExtraBold.ttf')
def F(s): return ImageFont.truetype(FONT, s)
def icon(n, s):
    p = os.path.join(RES, 'Icons', n + '.png')
    if not os.path.exists(p): p = os.path.join(D, n + '.png')
    im = Image.open(p).convert('RGBA'); im = im.crop(im.getbbox()); k = s / max(im.size)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
def ui(n): return Image.open(os.path.join(RES, 'UI', n + '.png')).convert('RGBA')

def text(img, xy, s, size, fill=(255, 255, 255, 255), stroke=(60, 40, 25, 255), sw=5, anchor='mm'):
    ImageDraw.Draw(img).text(xy, s, font=F(size), fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)

def shadow(layer, r=8, off=(0, 6), a=90):
    sh = Image.new('RGBA', layer.size, (0, 0, 0, 0)); m = layer.getchannel('A').point(lambda v: v * a // 255)
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(r)))
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0)); out.alpha_composite(sh, off); out.alpha_composite(layer); return out

def nine(src, w, h, b):
    """9 dilimli germe (kenar b piksel)."""
    sw, sh = src.size; out = Image.new('RGBA', (w, h))
    xs = [(0, b, 0, b), (b, sw - b, b, w - b), (sw - b, sw, w - b, w)]
    ys = [(0, b, 0, b), (b, sh - b, b, h - b), (sh - b, sh, h - b, h)]
    for x0, x1, X0, X1 in xs:
        for y0, y1, Y0, Y1 in ys:
            if X1 > X0 and Y1 > Y0: out.paste(src.crop((x0, y0, x1, y1)).resize((X1 - X0, Y1 - Y0), Image.LANCZOS), (X0, Y0))
    return out

def put(img, im, c):
    l = Image.new('RGBA', img.size, (0, 0, 0, 0)); l.alpha_composite(im, (int(c[0] - im.width / 2), int(c[1] - im.height / 2)))
    img.alpha_composite(shadow(l, 5, (0, 4), 70))

def button(img, name, box, label, size=34, ic=None):
    x0, y0, x1, y1 = box; b = nine(ui(name), x1 - x0, y1 - y0, 90)
    l = Image.new('RGBA', img.size, (0, 0, 0, 0)); l.alpha_composite(b, (x0, y0)); img.alpha_composite(shadow(l, 5, (0, 4), 80))
    cx = (x0 + x1) / 2
    if ic is not None:
        put(img, ic, (x0 + 44, (y0 + y1) / 2 - 2)); cx += 22
    text(img, (cx, (y0 + y1) / 2 - 3), label, size, stroke=(40, 70, 20, 255) if 'green' in name else (40, 50, 90, 255))

# ------------------------------------------------------------------ 1) yandan panel
scene = Image.open(os.path.join(D, 'garden_v4_genel.png')).convert('RGBA')
W, H = scene.size
img = scene.copy()
# seçili tarh: yumuşak sarı halka (dış çizgi değil, yere düşen ışık)
glow = Image.new('RGBA', img.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
g.ellipse((470, 330, 840, 560), fill=(255, 230, 120, 120)); img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)))
# karartma yalnız sağ kenarda (oyun görünür kalır)
fade = Image.new('RGBA', img.size, (0, 0, 0, 0)); fd = ImageDraw.Draw(fade)
for i in range(420): fd.line([(W - 420 + i, 0), (W - 420 + i, H)], fill=(10, 20, 30, int(110 * i / 420)))
img.alpha_composite(fade)
px0, py0, px1, py1 = W - 420, 70, W - 30, H - 40
card = nine(ui('card'), px1 - px0, py1 - py0, 110)
l = Image.new('RGBA', img.size, (0, 0, 0, 0)); l.alpha_composite(card, (px0, py0)); img.alpha_composite(shadow(l, 12, (0, 10), 110))
pl = nine(ui('plank'), 300, 84, 70); l = Image.new('RGBA', img.size, (0, 0, 0, 0)); l.alpha_composite(pl, ((px0 + px1) // 2 - 150, py0 - 34)); img.alpha_composite(shadow(l))
text(img, ((px0 + px1) / 2, py0 + 6), 'Tarh 2 · Havuç', 34)
put(img, icon('close', 70) if os.path.exists(os.path.join(RES, 'Icons', 'close.png')) else ui('close').resize((64, 69)), (px1 - 14, py0 - 6))
# durum satırı
cx = (px0 + px1) / 2
put(img, icon('food_carrot', 120), (cx - 95, py0 + 125))
text(img, (cx + 40, py0 + 100), 'Büyüyor', 34, fill=(110, 75, 40, 255), stroke=(255, 255, 255, 255), sw=4)
bar = ui('track_dark').resize((190, 36), Image.LANCZOS); fill = ui('fill_orange').resize((120, 28), Image.LANCZOS)
img.alpha_composite(bar, (int(cx - 55), py0 + 128)); img.alpha_composite(fill, (int(cx - 51), py0 + 132))
text(img, (cx + 40, py0 + 182), '3 dk kaldı', 26, fill=(140, 110, 80, 255), stroke=(255, 255, 255, 255), sw=3)
# tohum seçimi
text(img, (cx, py0 + 238), 'Tohum ek', 30, fill=(110, 75, 40, 255), stroke=(255, 255, 255, 255), sw=4)
for i, (n, c) in enumerate((('seed_carrot', 4), ('seed_tomato', 2), ('seed_corn', 3), ('seed_watermelon', 1))):
    x = px0 + 62 + i * 88; y = py0 + 300
    put(img, ui('round').resize((80, 80)), (x, y)); put(img, icon(n, 52), (x, y - 2))
    text(img, (x + 24, y + 30), f'x{c}', 22, sw=4)
can = icon('can_icon', 56) if os.path.exists(os.path.join(D, 'can_icon.png')) else None
button(img, 'btn_blue', (px0 + 40, py0 + 370, px1 - 40, py0 + 450), 'Sula', 38, can)
button(img, 'btn_green', (px0 + 40, py0 + 470, px1 - 40, py0 + 550), 'Topla', 38, icon('tool_hand', 56))
text(img, (cx, py1 - 40), 'Panel ekranın sağında; bahçe görünür kalır', 20, fill=(140, 110, 80, 255), stroke=(255, 255, 255, 255), sw=3)
img.convert('RGB').save(os.path.join(D, 'garden_v4_panel.png'))

# ------------------------------------------------------------------ 2) storyboard: ek → sula → filiz → topla
base = Image.open(os.path.join(D, 'garden_v4_yatak.png')).convert('RGBA')
bw, bh = base.size
fw, fh = 640, 400
def frame(k):
    f = base.resize((fw, int(bh * fw / bw)), Image.LANCZOS).crop((0, 0, fw, fh)); return f
spot = (330, 250)
frames = []
# 1 tohum düşer
f = frame(0); put(f, icon('seed_carrot', 70), (spot[0], spot[1] - 120))
d = ImageDraw.Draw(f)
for i in range(3): d.ellipse((spot[0] - 6, spot[1] - 90 + i * 22, spot[0] + 6, spot[1] - 78 + i * 22), fill=(120, 80, 40, 160 - i * 40))
put(f, icon('ui_hand', 90), (spot[0] + 90, spot[1] - 40)); frames.append((f, '1. Tohum düşer, toprak kabarır'))
# 2 su kavisi + ıslak toprak
f = frame(1); wet = Image.new('RGBA', f.size, (0, 0, 0, 0)); ImageDraw.Draw(wet).ellipse((spot[0] - 120, spot[1] - 40, spot[0] + 120, spot[1] + 50), fill=(20, 12, 6, 175))
f.alpha_composite(wet.filter(ImageFilter.GaussianBlur(14)))
if can is not None: put(f, icon('can_icon', 150).rotate(-28, expand=True, resample=Image.BICUBIC), (spot[0] - 150, spot[1] - 150))
d = ImageDraw.Draw(f)
for i in range(14):
    t = i / 13; x = spot[0] - 80 + t * 110; y = spot[1] - 150 + t * t * 160
    d.ellipse((x - 5, y - 7, x + 5, y + 7), fill=(150, 210, 245, 230))
frames.append((f, '2. Su kavisi, toprak koyulaşır'))
# 3 filiz fırlar + parıltı
f = frame(2); d = ImageDraw.Draw(f)
for a in (-35, 0, 35):
    r = math.radians(a - 90); d.line([(spot[0], spot[1]), (spot[0] + math.cos(r) * 60, spot[1] + math.sin(r) * 60)], fill=(80, 170, 60, 255), width=10)
    d.ellipse((spot[0] + math.cos(r) * 60 - 16, spot[1] + math.sin(r) * 60 - 10, spot[0] + math.cos(r) * 60 + 16, spot[1] + math.sin(r) * 60 + 10), fill=(120, 205, 80, 255))
for (dx, dy) in ((-90, -70), (80, -90), (100, 10), (-70, 20)):
    put(f, icon('ui_star', 34), (spot[0] + dx, spot[1] + dy))
text(f, (spot[0], spot[1] - 120), '+5 XP', 40); frames.append((f, '3. Filiz "pop" ile çıkar'))
# 4 hasat: ürün zıplar, sepete uçar
f = frame(3); put(f, icon('food_carrot', 110), (spot[0], spot[1] - 70))
d = ImageDraw.Draw(f)
for i in range(6):
    t = i / 5; d.ellipse((spot[0] + 40 + t * 200 - 4, spot[1] - 90 - math.sin(t * 3.1) * 70 - 4, spot[0] + 40 + t * 200 + 4, spot[1] - 90 - math.sin(t * 3.1) * 70 + 4), fill=(255, 220, 120, 220))
put(f, icon('food_carrot', 54), (spot[0] + 250, spot[1] - 100)); text(f, (spot[0] + 250, spot[1] - 40), '+2', 34)
frames.append((f, '4. Hasat zıplar, envantere uçar'))
SB = Image.new('RGBA', (fw * 2 + 60, fh * 2 + 250), (246, 240, 226, 255))
for i, (fr, cap) in enumerate(frames):
    x = 20 + (i % 2) * (fw + 20); y = 70 + (i // 2) * (fh + 60)
    SB.alpha_composite(fr, (x, y)); text(SB, (x + fw / 2, y + fh + 26), cap, 28, fill=(90, 60, 35, 255), stroke=(255, 255, 255, 255), sw=3)
text(SB, (SB.width / 2, 36), 'Bahçe eylemi: oyuncu yaptığını tarlada görür', 36, fill=(90, 60, 35, 255), stroke=(255, 255, 255, 255), sw=3)
text(SB, (SB.width / 2, SB.height - 40), 'Aynı kalıp: Kes (talaş + kütük sallanır) · Topla (yaprak savrulur) · Kaz (taş kırığı) · Yap (toz + kalaslar yerine oturur)',
     22, fill=(120, 90, 60, 255), stroke=(255, 255, 255, 255), sw=3)
SB.convert('RGB').save(os.path.join(D, 'garden_v4_storyboard.png'))
print('ok')
