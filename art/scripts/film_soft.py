# Giriş filmi arka planı (24 Ekim 2026): FilmPlayer sahne görselini ekrana TAM sığdırır (hiçbir yeri kesilmez); görselin
# dışında kalan yer (iPhone'da yanlar, iPad'de üst/alt şerit, altyazı şeridi) aynı görselin bulanık, koyulaştırılmış kopyasıyla dolar.
# Kullanım: python3 art/scripts/film_soft.py  → Assets/_Pofi/Resources/Art/Soft/<ad>.jpg (küçük; oyunda büyütülünce yumuşak)
import os
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Assets', '_Pofi', 'Resources', 'Art')
NAMES = ['film_1_ada', 'film_2_firtina', 'film_3_sis', 'film_4_misafir', 'load_okti']

os.makedirs(os.path.join(ROOT, 'Soft'), exist_ok=True)
for n in NAMES:
    im = Image.open(os.path.join(ROOT, n + '.jpg')).convert('RGB')
    im = im.resize((320, round(320 * im.height / im.width)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(9))
    im = ImageEnhance.Color(im).enhance(0.85)
    im = ImageEnhance.Brightness(im).enhance(0.58)   # altyazı beyaz yazısı her sahnede okunur
    im.save(os.path.join(ROOT, 'Soft', n + '.jpg'), quality=88)
    print('ok', n, im.size)
