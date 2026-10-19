# Geri bildirim 6 (19 Ekim 2026) görsel taslak: sade HUD + yazı tipi. Kullanım:
#   python3 hud_mockup.py <scratchpad> <font.ttf> <çıktı.png>
# Zemin: ground_mockup.py "new" çıktısı; simgeler: icons_mockup.py. Oyuna girmez, yalnız onay için.
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S, FONT, OUT = sys.argv[1:4]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
W, H = 1280, 720
bg = Image.open(f'{S}/ground_new.png').convert('RGBA').resize((W, H))
img = bg.copy()

NAVY = (36, 49, 94, 255); WHITE = (255, 255, 255, 255); GOLD = (255, 201, 61, 255)
def font(size, weight='ExtraBold'):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_name(weight)
    except Exception:
        try: f.set_variation_by_axes([800])
        except Exception: pass
    return f

def shadow(layer, r=10, off=(0, 5), a=70):
    a_ = layer.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: v * a // 255)
    sh = Image.new('RGBA', layer.size, (20, 30, 60, 0)); sh.putalpha(a_)
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0)); out.alpha_composite(sh, off); out.alpha_composite(layer); return out

def chip(box, radius, fill=(255, 255, 255, 236), outline=None):
    l = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    d.rounded_rectangle(box, radius, fill=fill, outline=outline, width=3 if outline else 0)
    img.alpha_composite(shadow(l))

def icon(name, center, size):
    im = Image.open(f'{S}/icons_new/{name}.png').convert('RGBA'); bb = im.getbbox(); im = im.crop(bb)
    k = size / max(im.size); im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    img.alpha_composite(im, (int(center[0] - im.width / 2), int(center[1] - im.height / 2)))

def text(xy, s, size, fill=NAVY, anchor='mm', stroke=0, stroke_fill=None, weight='ExtraBold'):
    d = ImageDraw.Draw(img)
    d.text(xy, s, font=font(size, weight), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)

# ---- sol üst: pet madalyonu + ad + XP kapsülü (kısa, kalın) + 4 gösterge noktası
chip((22, 18, 330, 112), 47)
por = Image.open(os.path.join(ROOT, 'Assets/_Pofi/Resources/Portraits/pet_01.png')).convert('RGBA').resize((84, 84))
m = Image.new('L', (84, 84), 0); ImageDraw.Draw(m).ellipse((0, 0, 83, 83), fill=255)
circ = Image.new('RGBA', (92, 92), (0, 0, 0, 0)); ImageDraw.Draw(circ).ellipse((0, 0, 91, 91), fill=(255, 226, 170, 255))
circ.paste(por, (4, 4), m); img.alpha_composite(circ, (24, 20))
text((128, 44), 'Turunç', 26, anchor='lm')
d = ImageDraw.Draw(img)
d.rounded_rectangle((128, 66, 290, 88), 11, fill=(36, 49, 94, 40))
d.rounded_rectangle((131, 69, 131 + int(156 * 0.62), 85), 8, fill=GOLD)
icon('star', (300, 77), 34); text((300, 79), '3', 18, fill=(110, 60, 0, 255))
for i, (c, v) in enumerate((((255, 120, 90), 0.8), ((90, 170, 255), 0.55), ((120, 210, 120), 0.9), ((255, 200, 80), 0.35))):
    x = 352 + i * 34
    l = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(l)
    dl.ellipse((x - 15, 40, x + 15, 70), fill=(255, 255, 255, 230))
    dl.arc((x - 12, 43, x + 12, 67), -90, -90 + 360 * v, fill=(*c, 255), width=5)
    img.alpha_composite(shadow(l, 6, (0, 3), 60))

# ---- sağ üst: coin, harita, görev (aynı yükseklikte sade kapsüller)
chip((1072, 18, 1258, 76), 29); icon('coin', (1102, 47), 46); text((1180, 47), '125', 30)
chip((1072, 88, 1258, 138), 25); text((1165, 113), 'Harita', 24)
chip((960, 18, 1058, 76), 29); icon('star', (990, 47), 36); text((1030, 47), '2', 26)

# ---- üst orta: ipucu şeridi
chip((490, 18, 890, 70), 26, fill=(36, 49, 94, 215))
text((690, 44), 'Solda kaydır: Turunç yürüsün!', 24, fill=WHITE)

# ---- sol kenar: Besle / Yıka
for y, ic, lab in ((290, 'apple', 'Besle'), (440, 'soap', 'Yıka')):
    l = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(l).ellipse((40, y - 48, 136, y + 48), fill=(255, 255, 255, 236)); img.alpha_composite(shadow(l))
    icon(ic, (88, y - 4), 58); text((88, y + 62), lab, 22, fill=WHITE, stroke=4, stroke_fill=(36, 49, 94, 200))

# ---- sağ alt: tek bağlamsal eylem (Topla: el) + küçük yan eylem (Zıpla)
l = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(l).ellipse((1110, 520, 1250, 660), fill=(255, 255, 255, 240)); img.alpha_composite(shadow(l))
icon('hand', (1180, 584), 84); text((1180, 684), 'Topla', 26, fill=WHITE, stroke=4, stroke_fill=(36, 49, 94, 200))
l = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(l).ellipse((1020, 590, 1090, 660), fill=(255, 255, 255, 230)); img.alpha_composite(shadow(l))
icon('jump', (1055, 625), 40)

# ---- yer etiketi (sahne üstü yazı)
text((640, 150), 'Ev Görevleri', 30, fill=WHITE, stroke=5, stroke_fill=(36, 49, 94, 210))
img.convert('RGB').save(OUT)
print('ok', OUT)
