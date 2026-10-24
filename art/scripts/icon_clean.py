"""Simgede arka plandan kalmış beyazı temizler (24 Ekim 2026, kullanıcı: "çantada kopça ile çanta arasında beyaz görüntü var").

Meshy simge sayfalarından kesilen bazı simgelerde, girintilerde (çanta askısı ile gövde arası, sap halkasının içi) kesme
maskesi kaba kaldığı için opak beyaz arka plan kalmış. Dışarıdan (saydam bölgeden) başlayarak beyazımsı pikselleri izler,
bunları saydam yapar; kenarı yumuşak bırakır. Simgenin içindeki gerçek beyazlara (dışarıya beyaz yolla bağlı değilse) dokunmaz.

    python3 art/scripts/icon_clean.py backpack_small          # yalnız dışarıya bağlı beyaz
    python3 art/scripts/icon_clean.py --all backpack_small    # kapalı beyaz boşluklar da (simgede gerçek beyaz yoksa)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Assets", "_Pofi", "Resources", "Icons")


def whiteness(rgb):
    mx = rgb.max(-1); mn = rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    # 1: saf beyaz/açık gri, 0: renkli ya da koyu
    return np.clip((mn - 0.72) / 0.18, 0, 1) * np.clip((0.22 - sat) / 0.12, 0, 1)


def clean(name, enclosed=False):
    path = os.path.join(ROOT, name + ".png")
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im).astype(np.float32) / 255.0
    rgb, a = arr[..., :3], arr[..., 3]
    w = whiteness(rgb)
    cand = (w > 0.35) | (a < 0.5)
    # dışarıdan erişilebilen aday bölge: saydam pikseller ve onlara beyaz yolla bağlı beyazlar
    h, wd = a.shape
    reach = np.zeros_like(cand)
    reach[0, :] = cand[0, :]; reach[-1, :] = cand[-1, :]; reach[:, 0] = cand[:, 0]; reach[:, -1] = cand[:, -1]
    while True:
        grown = reach.copy()
        grown[1:, :] |= reach[:-1, :]; grown[:-1, :] |= reach[1:, :]
        grown[:, 1:] |= reach[:, :-1]; grown[:, :-1] |= reach[:, 1:]
        grown &= cand
        if (grown == reach).all():
            break
        reach = grown
    kill = reach & (a >= 0.5)
    if enclosed:
        # kapalı beyaz boşluklar (sap halkasının içi, askı ile gövde arası): beyazımsı ve yeterince büyük her parça
        kill |= (w > 0.5) & (a >= 0.5)
    # yumuşak kenar: silinen bölgenin 1–2 px çevresinde beyazlık oranında saydamlaştır
    soft = np.asarray(Image.fromarray((kill * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(3))).astype(np.float32) / 255.0
    na = a * (1 - kill) * (1 - soft * w)
    na = np.asarray(Image.fromarray((na * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255.0
    na = np.minimum(na, a)
    out = np.dstack([rgb, na])
    Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save(path, optimize=True)
    print(name, "silinen piksel", int(kill.sum()))


if __name__ == "__main__":
    args = sys.argv[1:]
    enclosed = "--all" in args
    for n in [x for x in args if not x.startswith("--")]:
        clean(n, enclosed)
