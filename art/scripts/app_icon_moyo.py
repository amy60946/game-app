"""Moyo Oyun uygulama simgesi (kullanıcı seçimi R2, 20 Kasım 2026): oyun görseli + sağ altta küçük Moyo Ebeveyn simgesi.

Rozet: Moyo Ebeveyn'in güncel simgesi (18 Kasım seti: lacivert #16113A zemin, yeşil #0FD354 işaret 1E), beyaz çizgi YOK,
yumuşak gölge; boyu 14/60 birim (%23,3), köşeden 4/60 birim (%6,7). Ölçüler 60 px ana ekran ızgarasına oturur (1 birim =
1024/60 px), rozetin köşe yarıçapı iOS köşe oranıyla aynı (%22,37); telefonun yuvarlak köşesine köşegende ~17 px pay kalır.
Simgede yazı yok (Apple önermez). Çıktı 1024 × 1024, saydamlıksız (App Store şartı).

Girdiler art/icons/moyo_oyun/: src_oyun.png (özgün oyun görseli, 24 Ekim simgesi), moyo_ebeveyn_1024.png (parent-app
assets/icon.png, 18 Kasım seti). Moyo Ebeveyn simgesi değişirse yeni dosyayı oraya kopyala ve betiği yeniden çalıştır.
Seçenekler (R1–R6, M1–M3) ve dinleme/önizleme sayfası yalnız sohbette gösterildi; bu betik seçilen R2'yi üretir.

    python3 -I art/scripts/app_icon_moyo.py            # → Assets/_Pofi/Art/AppIcon.png
    python3 -I art/scripts/app_icon_moyo.py <çıktı.png>
"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "art", "icons", "moyo_oyun")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Assets", "_Pofi", "Art", "AppIcon.png")

S = 1024
U = S / 60          # 60 px ana ekran ızgarası
BADGE_UNITS = 14    # rozet kenarı
INSET_UNITS = 4     # köşeden içeri
RAD = 0.2237        # iOS köşe oranı
SHADOW = (0, 5, 12, 0.32)   # (x, y kayma px, bulanıklık px, koyuluk)
SS = 4


def rounded(size, rad):
    m = Image.new("L", (size * SS, size * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size * SS - 1, size * SS - 1], radius=round(size * SS * rad), fill=255)
    return m.resize((size, size), Image.LANCZOS)


def main():
    base = Image.open(os.path.join(SRC, "src_oyun.png")).convert("RGB").resize((S, S), Image.LANCZOS)
    b = round(BADGE_UNITS * U); x1 = round(S - INSET_UNITS * U); x0 = x1 - b
    mask = rounded(b, RAD)
    dx, dy, blur, alpha = SHADOW
    sh = Image.new("L", (S, S), 0); sh.paste(mask, (x0 + dx, x0 + dy))
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha))
    base = Image.composite(Image.new("RGB", (S, S), (0, 0, 0)), base, sh)
    moyo = Image.open(os.path.join(SRC, "moyo_ebeveyn_1024.png")).convert("RGB").resize((b, b), Image.LANCZOS)
    base.paste(moyo, (x0, x0), mask)
    base.save(OUT, optimize=True)
    print("yazıldı:", OUT, base.size, base.mode)


if __name__ == "__main__":
    main()
