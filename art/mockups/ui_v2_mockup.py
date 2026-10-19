# Görsel taslak v2 (19 Ekim 2026): kalın çerçeveli göstergeler, parlak yeşil düğme, krem kart, şeritli seviye ekranı.
#   python3 ui_v2_mockup.py <scratchpad> <font.ttf>
# Kalite/hava hedefi kullanıcının paylaştığı ticari oyun ekranları; buradaki her şekil, simge ve metin özgün.
import sys, os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S, FONT = sys.argv[1:3]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
W, H = 1600, 740
INK = (52, 40, 30, 255)          # yazı konturu: sıcak koyu kahve (siyah değil)
WHITE = (255, 255, 255, 255)

def font(size):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_name('ExtraBold')
    except Exception: pass
    return f

def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))
def shadow(l, r=8, off=(0, 6), a=90):
    al = l.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: v * a // 255)
    sh = Image.new('RGBA', l.size, (30, 20, 10, 0)); sh.putalpha(al)
    o = layer(); o.alpha_composite(sh, off); o.alpha_composite(l); return o

def text(img, xy, s, size, fill=WHITE, anchor='mm', stroke=None, sw=None):
    d = ImageDraw.Draw(img); f = font(size)
    sw = sw if sw is not None else max(3, size // 9)
    x, y = xy
    d.text((x, y + max(2, size // 14)), s, font=f, fill=(0, 0, 0, 90), anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0, 90))
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=stroke or INK)

def icon(img, name, c, size, folder='icons_new'):
    p = f'{S}/{folder}/{name}.png' if folder else f'{S}/{name}.png'
    im = Image.open(p).convert('RGBA'); im = im.crop(im.getbbox())
    k = size / max(im.size); im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    img.alpha_composite(im, (int(c[0] - im.width / 2), int(c[1] - im.height / 2)))

def vgrad(w, h, top, bot):
    g = Image.new('RGBA', (w, h))
    for y in range(h):
        t = y / max(1, h - 1); g.paste(tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(4)), (0, y, w, y + 1))
    return g

def rrect_fill(img, box, r, top, bot, outline=None, ow=0):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    l = layer(); l.paste(vgrad(w, h, top, bot), (x0, y0), m)
    if outline: ImageDraw.Draw(l).rounded_rectangle(box, r, outline=outline, width=ow)
    return l

def bar(img, x, y, w, val01, label, fill_top, fill_bot, ic, plus=True):
    hl = fill_top[3] > 0
    """Koyu kapsül + renkli dolgu + soldan taşan iri simge + yeşil artı."""
    h = 52
    l = rrect_fill(img, (x, y, x + w, y + h), h // 2, (58, 64, 74, 235), (44, 49, 58, 235), outline=(30, 26, 22, 255), ow=4)
    img.alpha_composite(shadow(l, 6, (0, 4), 80))
    if val01 > 0:
        fw = max(h, int((w - 10) * val01))
        img.alpha_composite(rrect_fill(img, (x + 5, y + 5, x + 5 + fw, y + h - 5), (h - 10) // 2, fill_top, fill_bot))
        if hl: ImageDraw.Draw(img).rounded_rectangle((x + 14, y + 9, x + fw - 6, y + 17), 4, fill=(255, 255, 255, 80))
    text(img, (x + w / 2 + (18 if ic else 0), y + h / 2 - 1), label, 30)
    if ic: icon(img, ic, (x + 4, y + h / 2), 78)
    if plus: plus_badge(img, (x + 30, y + h + 2))

def plus_badge(img, c, r=19):
    l = layer(); d = ImageDraw.Draw(l)
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(110, 200, 40, 255), outline=WHITE, width=4)
    d.rounded_rectangle((c[0] - 9, c[1] - 3, c[0] + 9, c[1] + 3), 2, fill=WHITE); d.rounded_rectangle((c[0] - 3, c[1] - 9, c[0] + 3, c[1] + 9), 2, fill=WHITE)
    img.alpha_composite(shadow(l, 3, (0, 2), 70))

def green_button(img, box, label, size=40):
    x0, y0, x1, y1 = box
    lip = rrect_fill(img, (x0, y0 + 8, x1, y1 + 8), 22, (62, 140, 24, 255), (52, 120, 20, 255))
    img.alpha_composite(shadow(lip, 6, (0, 4), 90))
    img.alpha_composite(rrect_fill(img, box, 22, (168, 232, 62, 255), (104, 196, 34, 255), outline=(70, 140, 26, 255), ow=3))
    ImageDraw.Draw(img).rounded_rectangle((x0 + 22, y0 + 9, x1 - 22, y0 + 18), 5, fill=(255, 255, 255, 45))
    text(img, ((x0 + x1) / 2, (y0 + y1) / 2 + 2), label, size, stroke=(46, 104, 16, 255))

def round_button(img, c, r, ic, label=None, ring=(255, 255, 255, 255), fill=(255, 250, 238, 245)):
    l = layer(); d = ImageDraw.Draw(l)
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=fill, outline=ring, width=6)
    img.alpha_composite(shadow(l, 8, (0, 6), 90))
    icon(img, ic, (c[0], c[1] - 2), int(r * 1.25))
    if label: text(img, (c[0], c[1] + r + 18), label, 28)

def bubble(img, c, ic):
    """Nesne üstü alet baloncuğu: beyaz damla, aşağı sivri uç."""
    l = layer(); d = ImageDraw.Draw(l); r = 54
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(255, 255, 255, 250), outline=(225, 215, 200, 255), width=3)
    d.polygon([(c[0] - 20, c[1] + r - 12), (c[0] + 20, c[1] + r - 12), (c[0], c[1] + r + 22)], fill=(255, 255, 255, 250))
    img.alpha_composite(shadow(l, 6, (0, 5), 80)); icon(img, ic, c, 74)

def glove(img, tip, size=170, rot=0):
    g = Image.open(f'{S}/glove.png').convert('RGBA'); g = g.crop(g.getbbox())
    k = size / max(g.size); g = g.resize((int(g.width * k), int(g.height * k)), Image.LANCZOS)
    if rot: g = g.rotate(rot, expand=True, resample=Image.BICUBIC)
    # parmak ucu görselin üst ortası civarı
    sh = layer(); sh.alpha_composite(g, (int(tip[0] - g.width * 0.42), int(tip[1] - g.height * 0.06)))
    img.alpha_composite(shadow(sh, 10, (6, 10), 110))

def fog_layer(seed=3):
    """Kenarlarda yumuşak sis: üst üste binen beyaz bulut kümeleri, kenarı bulanık, gövdesi hafif gölgeli."""
    import random
    rnd = random.Random(seed)
    base = Image.new('L', (W, H), 0); d = ImageDraw.Draw(base)
    def cluster(cx, cy, n, sx, sy, rmin, rmax):
        for _ in range(n):
            x, y, r = cx + rnd.uniform(-sx, sx), cy + rnd.uniform(-sy, sy), rnd.uniform(rmin, rmax)
            d.ellipse((x - r * 1.3, y - r, x + r * 1.3, y + r), fill=255)
    cluster(260, 20, 26, 280, 60, 50, 110); cluster(800, -30, 20, 260, 40, 60, 110)
    cluster(1430, 90, 30, 200, 120, 60, 120); cluster(1590, 380, 18, 60, 160, 60, 110)
    a = base.filter(ImageFilter.GaussianBlur(22))
    shade = base.filter(ImageFilter.GaussianBlur(40))
    fog = Image.new('RGBA', (W, H), (255, 255, 255, 0))
    body = Image.new('RGBA', (W, H), (248, 250, 252, 255))
    # alt kenarda hafif gri-mavi gölge (bulut hacmi)
    sh = Image.new('RGBA', (W, H), (205, 214, 226, 255)); smask = Image.eval(shade, lambda v: max(0, min(255, int((255 - v) * 0.9)) if v > 40 else 0))
    body.paste(sh, (0, 0), smask)
    body.putalpha(a.point(lambda v: min(255, int(v * 1.05))))
    fog.alpha_composite(body); return fog

def scene():
    im = Image.open(f'{S}/scene_v2.png').convert('RGBA').resize((W, H))
    im.alpha_composite(fog_layer()); return im

# ======================================================================== 1) Ada + HUD
img = scene()
# sol üst: madalyon (beyaz kalın halka) + seviye yıldızı + XP çubuğu
por = Image.open(os.path.join(ROOT, 'Assets/_Pofi/Resources/Portraits/pet_01.png')).convert('RGBA').resize((104, 104))
l = layer(); d = ImageDraw.Draw(l); d.ellipse((24, 14, 140, 130), fill=(140, 200, 255, 255), outline=WHITE, width=7)
img.alpha_composite(shadow(l, 6, (0, 5), 90))
m = Image.new('L', (104, 104), 0); ImageDraw.Draw(m).ellipse((0, 0, 103, 103), fill=255)
pc = Image.new('RGBA', (104, 104), (140, 200, 255, 255)); pc.alpha_composite(por); img.paste(pc, (30, 20), m)
bar(img, 150, 46, 280, 0.42, '42 / 100', (255, 214, 64, 255), (246, 166, 20, 255), None, plus=False)
icon(img, 'star', (118, 112), 62); text(img, (118, 115), '3', 30, stroke=(120, 64, 0, 255))
# orta üst: Güneş Taşı ve coin
bar(img, 640, 36, 250, 0.6, '3', (255, 196, 70, 255), (255, 140, 30, 255), 'sunstone')
bar(img, 950, 36, 250, 1.0, '125', (120, 120, 130, 0), (120, 120, 130, 0), 'coin')
# sağ üst: harita düğmesi (yeşil kare, beyaz iç simge yok: üç çizgi yerine harita kıvrımı)
img.alpha_composite(rrect_fill(img, (1480, 26, 1570, 112), 24, (170, 232, 66, 255), (98, 186, 30, 255), outline=(60, 128, 22, 255), ow=4))
d = ImageDraw.Draw(img)
for i in range(3): d.rounded_rectangle((1500, 46 + i * 18, 1550, 56 + i * 18), 5, fill=WHITE)
text(img, (1525, 132), 'Harita', 24)
# sol: görev kısa yolları (beyaz halkalı yuvarlak) + rozet
round_button(img, (84, 250), 54, 'star', 'Görev')
round_button(img, (84, 390), 54, 'sunstone', 'Ev')
# sol alt: Besle / Yıka
round_button(img, (84, 600), 50, 'apple', 'Besle'); round_button(img, (210, 640), 42, 'soap', 'Yıka')
# sağ alt: bağlamsal büyük eylem + küçük zıpla
round_button(img, (1470, 610), 74, 'axe', 'Kes', ring=(255, 255, 255, 255), fill=(255, 244, 214, 250))
round_button(img, (1320, 650), 42, 'jump')
# nesne üstü baloncuk + eldiven + ipucu yazısı
bubble(img, (1100, 300), 'axe')
glove(img, (1080, 420), 150, rot=18)
text(img, (800, 690), 'Ağaca dokun, odun topla!', 40)
img.convert('RGB').save(f'{S}/v2_hud.png')

# ======================================================================== 2) Seviye atlama
img = scene().filter(ImageFilter.GaussianBlur(10))
img.alpha_composite(Image.new('RGBA', (W, H), (10, 20, 30, 120)))
# şerit: iki yanda mavi kurdele, ortada yıldız
l = layer(); d = ImageDraw.Draw(l)
for sgn in (-1, 1):
    cx = 800 + sgn * 180
    d.polygon([(800 + sgn * 70, 120), (800 + sgn * 250, 108), (800 + sgn * 290, 150), (800 + sgn * 250, 196), (800 + sgn * 70, 186)], fill=(56, 168, 230, 255), outline=(26, 96, 150, 255))
    d.polygon([(800 + sgn * 250, 130), (800 + sgn * 330, 126), (800 + sgn * 300, 160), (800 + sgn * 330, 200), (800 + sgn * 250, 186)], fill=(36, 132, 196, 255), outline=(26, 96, 150, 255))
img.alpha_composite(shadow(l, 8, (0, 6), 110))
d = ImageDraw.Draw(img)
for sgn in (-1, 1):
    d.line([(800 + sgn * 90, 135), (800 + sgn * 240, 128)], fill=(140, 214, 255, 255), width=5)
icon(img, 'star', (800, 152), 200); text(img, (800, 160), '4', 84, stroke=(120, 64, 0, 255), sw=8)
text(img, (800, 300), 'Yeni seviyeye ulaştın!', 52)
d.line([(560, 350), (1040, 350)], fill=(255, 255, 255, 110), width=3)
text(img, (800, 400), 'Ödülün', 40, fill=(255, 236, 190, 255))
icon(img, 'coin', (720, 480), 92); text(img, (805, 482), '25', 54)
icon(img, 'sunstone', (900, 480), 86); text(img, (975, 482), '1', 54)
green_button(img, (680, 580, 920, 662), 'Harika!', 44)
img.convert('RGB').save(f'{S}/v2_levelup.png')

# ======================================================================== 3) Onarım paneli (Kulübe)
img = scene().filter(ImageFilter.GaussianBlur(10))
img.alpha_composite(Image.new('RGBA', (W, H), (10, 20, 30, 90)))
text(img, (380, 76), 'Kulübe · Sv 1', 54)
text(img, (380, 132), 'Onar, eşyaların burada dursun', 32)
l = layer(); ImageDraw.Draw(l).ellipse((140, 420, 620, 610), fill=(241, 214, 168, 255), outline=(214, 180, 128, 255), width=6)
img.alpha_composite(shadow(l, 10, (0, 10), 120))
icon(img, 'p_site', (380, 440), 360, folder=None)
green_button(img, (250, 580, 510, 668), 'Yap', 46)
text(img, (1150, 76), 'Hepsini topla, kulübe senin olsun', 36)
icon(img, 'star', (1150, 162), 70); text(img, (1150, 210), '40 XP', 28)
cards = (('log', 6, 6, True), ('twig', 3, 4, False), ('rocks', 1, 3, False))
for i, (ic, have, need, done) in enumerate(cards):
    x0 = 800 + i * 240; y0 = 260
    card = rrect_fill(img, (x0, y0, x0 + 210, y0 + 280), 26, (255, 238, 206, 255), (246, 220, 176, 255), outline=(224, 186, 132, 255), ow=4)
    img.alpha_composite(shadow(card, 8, (0, 8), 100))
    dd = ImageDraw.Draw(img)
    for (sx, sy, sr) in ((30, 30, 16), (170, 60, 12), (60, 230, 14), (150, 200, 18)):
        dd.ellipse((x0 + sx - sr, y0 + sy - sr, x0 + sx + sr, y0 + sy + sr), fill=(240, 214, 170, 255))
    if done:
        # kalın yeşil onay işareti
        l = layer(); dl = ImageDraw.Draw(l)
        pts = [(x0 + 50, y0 + 150), (x0 + 92, y0 + 192), (x0 + 166, y0 + 92)]
        dl.line(pts, fill=(46, 120, 20, 255), width=40, joint='curve')
        dl.line(pts, fill=(130, 214, 52, 255), width=28, joint='curve')
        img.alpha_composite(shadow(l, 4, (0, 4), 90))
    else:
        icon(img, ic, (x0 + 105, y0 + 120), 130)
        col = (90, 190, 40, 255) if have >= need else (230, 70, 50, 255)
        text(img, (x0 + 105, y0 + 222), f'{have} / {need}', 40, fill=col, stroke=WHITE, sw=5)
        green_button(img, (x0 + 30, y0 + 252, x0 + 180, y0 + 310), 'Bul', 32)
# kapat
text(img, (1550, 50), '×', 80)
glove(img, (1065, 520), 150, rot=-10)
img.convert('RGB').save(f'{S}/v2_panel.png')
print('ok')
