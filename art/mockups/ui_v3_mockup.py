# Görsel taslak v3 (19 Ekim 2026): Meshy (nano-banana-pro) simge ve arayüz parçalarıyla aynı üç ekran.
#   python3 ui_v3_mockup.py <scratchpad> <font.ttf>
# Parçalar: art/meshy/out/ui_v3_{a,b,c} → cut_sheet.py → <scratchpad>/meshy_icons. Zemin: scene_v2.png + ui_v2 sisi.
import sys, os, importlib.util
from PIL import Image, ImageDraw, ImageFilter
S, FONT = sys.argv[1:3]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
# v2'nin yardımcılarını (yazı, gölge, sis) yeniden kullan: modülü çalıştırmadan fonksiyonlarını al
src = open(os.path.join(HERE, 'ui_v2_mockup.py')).read()
helpers = src.split('# ======================================================================== 1)')[0]
helpers = helpers.replace("S, FONT = sys.argv[1:3]", "")
ns = {'S': S, 'FONT': FONT, '__file__': os.path.join(HERE, 'ui_v2_mockup.py')}
exec(compile(helpers, 'ui_v2_helpers', 'exec'), ns)
W, H = ns['W'], ns['H']; text = ns['text']; shadow = ns['shadow']; layer = ns['layer']; scene = ns['scene']; INK = ns['INK']
M = f'{S}/meshy_icons'

def piece(name): return Image.open(f'{M}/{name}.png').convert('RGBA')
def put(img, name, c, size=None, w=None, h=None, sh=True):
    p = piece(name)
    if size: k = size / max(p.size); p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
    elif w and h: p = p.resize((w, h), Image.LANCZOS)
    l = layer(); l.alpha_composite(p, (int(c[0] - p.width / 2), int(c[1] - p.height / 2)))
    img.alpha_composite(shadow(l, 5, (0, 4), 70) if sh else l)

def stretch3(name, w, h):
    """Yatay üç parça germe: uçlar oranı korur, orta uzar (çubuk, düğme, tahta)."""
    p = piece(name); k = h / p.height; p = p.resize((max(1, int(p.width * k)), h), Image.LANCZOS)
    cap = min(int(h * 0.9), p.width // 3)
    left, right, mid = p.crop((0, 0, cap, h)), p.crop((p.width - cap, 0, p.width, h)), p.crop((cap, 0, p.width - cap, h))
    o = Image.new('RGBA', (w, h), (0, 0, 0, 0)); o.alpha_composite(left, (0, 0)); o.alpha_composite(right, (w - cap, 0))
    o.alpha_composite(mid.resize((max(1, w - 2 * cap), h), Image.LANCZOS), (cap, 0)); return o

def put_stretch(img, name, box, sh=True):
    x0, y0, x1, y1 = box; p = stretch3(name, x1 - x0, y1 - y0)
    l = layer(); l.alpha_composite(p, (x0, y0)); img.alpha_composite(shadow(l, 5, (0, 4), 80) if sh else l)

def dark_bar(img, box):
    """Koyu kömür çerçeveli boş çubuk (Meshy çubuklarının çerçeve tonunda)."""
    x0, y0, x1, y1 = box; h = y1 - y0
    l = ns['rrect_fill'](img, box, h // 2, (62, 66, 74, 255), (40, 43, 50, 255), outline=(30, 32, 38, 255), ow=5)
    ImageDraw.Draw(l).rounded_rectangle((x0 + 12, y0 + 8, x1 - 12, y0 + 16), 4, fill=(255, 255, 255, 30))
    img.alpha_composite(shadow(l, 5, (0, 4), 80))

def round_btn(img, c, r, ic, label=None, icon_k=1.15):
    put(img, 'round', c, size=r * 2)
    put(img, ic, (c[0], c[1] - 2), size=int(r * icon_k), sh=False)
    if label: text(img, (c[0], c[1] + r + 16), label, 28)

def green_btn(img, box, label, size=40):
    put_stretch(img, 'btn_green', box)
    x0, y0, x1, y1 = box; text(img, ((x0 + x1) / 2, (y0 + y1) / 2 - 3), label, size, stroke=(40, 100, 16, 255))

# ======================================================================== 1) Ada + HUD
img = scene()
# sol üst: madalyon + seviye yıldızı + XP çubuğu
por = Image.open(os.path.join(ROOT, 'Assets/_Pofi/Resources/Portraits/pet_01.png')).convert('RGBA').resize((100, 100))
put(img, 'round', (82, 72), size=132)
m = Image.new('L', (100, 100), 0); ImageDraw.Draw(m).ellipse((0, 0, 99, 99), fill=255)
pc = Image.new('RGBA', (100, 100), (150, 205, 255, 255)); pc.alpha_composite(por); img.paste(pc, (32, 22), m)
put_stretch(img, 'bar_orange', (150, 44, 440, 98)); text(img, (300, 70), '42 / 100', 30)
put(img, 'star', (128, 116), size=66); text(img, (128, 120), '3', 30, stroke=(120, 64, 0, 255))
# orta üst: Güneş Taşı ve coin
put_stretch(img, 'bar_blue', (650, 44, 890, 98)); put(img, 'sunstone', (648, 70), size=92); text(img, (785, 70), '3', 32)
put(img, 'plus', (688, 104), size=44)
dark_bar(img, (960, 44, 1200, 98)); put(img, 'coin', (960, 70), size=86); text(img, (1090, 70), '125', 32)
put(img, 'plus', (998, 104), size=44)
# sağ üst: harita
round_btn(img, (1520, 74), 56, 'map', 'Harita', icon_k=1.35)
# sol: Görev, Ev Görevleri
round_btn(img, (84, 250), 54, 'star', 'Görev')
round_btn(img, (84, 392), 54, 'board', 'Ev', icon_k=1.3)
# sol alt: Besle, Yıka
round_btn(img, (84, 600), 50, 'apple', 'Besle'); round_btn(img, (210, 640), 42, 'soap', 'Yıka', icon_k=1.3)
# sağ alt: büyük eylem + küçük zıpla
round_btn(img, (1470, 606), 78, 'axe', 'Kes', icon_k=1.1); round_btn(img, (1318, 650), 44, 'jump', icon_k=1.1)
# nesne üstü baloncuk + işaret eli + ipucu
l = layer(); d = ImageDraw.Draw(l); c = (1100, 300); r = 54
d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(255, 255, 255, 250), outline=(225, 215, 200, 255), width=3)
d.polygon([(c[0] - 20, c[1] + r - 12), (c[0] + 20, c[1] + r - 12), (c[0], c[1] + r + 22)], fill=(255, 255, 255, 250))
img.alpha_composite(shadow(l, 6, (0, 5), 80)); put(img, 'axe', c, size=80, sh=False)
put(img, 'glove', (1110, 470), size=150)
text(img, (800, 690), 'Ağaca dokun, odun topla!', 40)
img.convert('RGB').save(f'{S}/v3_hud.png')

# ======================================================================== 2) Seviye atlama
img = scene().filter(ImageFilter.GaussianBlur(10)); img.alpha_composite(Image.new('RGBA', (W, H), (10, 20, 30, 120)))
put(img, 'ribbon', (800, 168), w=640, h=150)
put(img, 'star_big', (800, 150), size=210); text(img, (800, 160), '4', 84, stroke=(120, 64, 0, 255), sw=8)
text(img, (800, 305), 'Yeni seviyeye ulaştın!', 52)
ImageDraw.Draw(img).line([(560, 352), (1040, 352)], fill=(255, 255, 255, 110), width=3)
text(img, (800, 400), 'Ödülün', 40, fill=(255, 236, 190, 255))
put(img, 'coin', (710, 480), size=96); text(img, (800, 482), '25', 54)
put(img, 'sunstone', (905, 480), size=100); text(img, (985, 482), '1', 54)
green_btn(img, (660, 572, 940, 664), 'Harika!', 46)
img.convert('RGB').save(f'{S}/v3_levelup.png')

# ======================================================================== 3) Kulübe onarım paneli
img = scene().filter(ImageFilter.GaussianBlur(10)); img.alpha_composite(Image.new('RGBA', (W, H), (10, 20, 30, 90)))
put_stretch(img, 'plank', (170, 40, 590, 120)); text(img, (380, 78), 'Kulübe · Sv 1', 46)
text(img, (380, 152), 'Onar, eşyaların burada dursun', 30)
l = layer(); ImageDraw.Draw(l).ellipse((140, 430, 620, 610), fill=(241, 214, 168, 255), outline=(214, 180, 128, 255), width=6)
img.alpha_composite(shadow(l, 10, (0, 10), 120))
site = Image.open(f'{S}/p_site.png').convert('RGBA'); site = site.crop(site.getbbox()); k = 360 / max(site.size)
site = site.resize((int(site.width * k), int(site.height * k))); img.alpha_composite(site, (380 - site.width // 2, 446 - site.height // 2))
green_btn(img, (250, 580, 510, 670), 'Yap', 46)
text(img, (1150, 76), 'Hepsini topla, kulübe senin olsun', 36)
put(img, 'star', (1150, 160), size=72); text(img, (1150, 210), '40 XP', 28)
cards = (('log', 6, 6, True), ('twig', 3, 4, False), ('rocks', 1, 3, False))
for i, (ic, have, need, done) in enumerate(cards):
    x0 = 800 + i * 240; y0 = 250
    put(img, 'card', (x0 + 105, y0 + 145), w=220, h=290)
    if done: put(img, 'check', (x0 + 105, y0 + 130), size=150)
    else:
        put(img, ic, (x0 + 105, y0 + 120), size=130, sh=False)
        col = (90, 190, 40, 255) if have >= need else (230, 70, 50, 255)
        text(img, (x0 + 105, y0 + 222), f'{have} / {need}', 40, fill=col, stroke=(255, 255, 255, 255), sw=5)
        green_btn(img, (x0 + 30, y0 + 252, x0 + 180, y0 + 318), 'Bul', 32)
put(img, 'close', (1540, 60), size=80)
put(img, 'glove', (1110, 600), size=140)
img.convert('RGB').save(f'{S}/v3_panel.png')

# ======================================================================== 4) parça sayfası
names = ['star', 'coin', 'sunstone', 'apple', 'soap', 'hand', 'axe', 'jump', 'enter', 'play', 'map', 'board', 'plus', 'check', 'pickaxe', 'hammer', 'music', 'glove', 'log', 'twig', 'rocks', 'heart', 'hut', 'gift', 'shop', 'lock', 'magnifier']
sheet = Image.new('RGBA', (9 * 150 + 20, 3 * 160 + 20), (236, 242, 230, 255))
for i, n in enumerate(names):
    p = piece(n); k = 130 / max(p.size); p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
    sheet.alpha_composite(p, (10 + (i % 9) * 150 + (140 - p.width) // 2, 10 + (i // 9) * 160 + (140 - p.height) // 2))
sheet.convert('RGB').save(f'{S}/v3_sheet.png')
print('ok')
