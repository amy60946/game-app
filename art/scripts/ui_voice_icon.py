"""
Sesli okuma hoparlör simgesi (23 Ekim 2026): Resources/Icons/ui_voice.png, 256×256. Müzik notası simgesiyle (ui_music, v3) aynı dil:
parlak beyaz-açık mavi 3B gövde, mavi-gri yumuşak kenar, üst kenarda parıltı, alt kenarda gölge. Kodla çizilir (kredi harcanmaz).
Kullanım: python3 art/scripts/ui_voice_icon.py [çıkış.png]
"""
import os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 1024                      # 4× örnekle çiz, sonra küçült
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "Assets", "_Pofi", "Resources", "Icons", "ui_voice.png")


def shape():
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    p = lambda x, y: (x * S, y * S)
    # hoparlör gövdesi + koni (yuvarlatılmış)
    d.rounded_rectangle([p(0.14, 0.37), p(0.36, 0.63)], radius=int(S * 0.05), fill=255)
    d.polygon([p(0.30, 0.37), p(0.52, 0.17), p(0.56, 0.18), p(0.56, 0.82), p(0.52, 0.83), p(0.30, 0.63)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(S * 0.012)).point(lambda v: 255 if v > 128 else 0)
    # iki ses dalgası (yuvarlak uçlu yaylar)
    for r, w in ((0.17, 0.065), (0.29, 0.065)):
        arc = Image.new("L", (S, S), 0)
        a = ImageDraw.Draw(arc)
        cx, cy = 0.56 * S, 0.5 * S
        rr = r * S
        a.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=-48, end=48, fill=255, width=int(w * S))
        # yuvarlak uçlar
        import math
        for ang in (-48, 48):
            t = math.radians(ang)
            ex, ey = cx + (rr - w * S / 2) * math.cos(t), cy + (rr - w * S / 2) * math.sin(t)
            a.ellipse([ex - w * S / 2, ey - w * S / 2, ex + w * S / 2, ey + w * S / 2], fill=255)
        m = ImageChops.lighter(m, arc)
    return m


def shift(m, dy):
    out = Image.new("L", m.size, 0)
    out.paste(m, (0, dy))
    return out


def main():
    m = shape()
    edge = m.filter(ImageFilter.MaxFilter(int(S * 0.035) | 1)).filter(ImageFilter.GaussianBlur(S * 0.004))
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # yumuşak gölge
    sh = edge.filter(ImageFilter.GaussianBlur(S * 0.02)).point(lambda v: int(v * 0.28))
    img.paste((40, 60, 100, 255), (0, int(S * 0.02)), sh)
    # kenar
    img.paste((125, 145, 180, 255), (0, 0), edge)
    # gövde: dikey geçiş beyaz → açık mavi-gri
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        k = y / S
        c = tuple(int(a + (b - a) * k) for a, b in zip((255, 255, 255), (196, 210, 232)))
        gd.line([(0, y), (S, y)], fill=c + (255,))
    img.paste(grad, (0, 0), m)
    # alt kenar gölgesi ve üst kenar parıltısı
    low = ImageChops.subtract(m, shift(m, -int(S * 0.045))).filter(ImageFilter.GaussianBlur(S * 0.012))
    img.paste((150, 170, 205, 255), (0, 0), low.point(lambda v: int(v * 0.85)))
    hi = ImageChops.subtract(m, shift(m, int(S * 0.035))).filter(ImageFilter.GaussianBlur(S * 0.01))
    img.paste((255, 255, 255, 255), (0, 0), hi.point(lambda v: int(v * 0.95)))
    # parlak benek (gövdenin sol üstü)
    gl = Image.new("L", (S, S), 0)
    ImageDraw.Draw(gl).ellipse([0.19 * S, 0.40 * S, 0.30 * S, 0.47 * S], fill=200)
    img.paste((255, 255, 255, 255), (0, 0), ImageChops.multiply(gl.filter(ImageFilter.GaussianBlur(S * 0.012)), m))
    img = img.resize((256, 256), Image.LANCZOS)
    img.save(OUT)
    print("yazıldı", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
