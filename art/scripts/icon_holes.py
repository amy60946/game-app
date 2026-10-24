"""Simge delik maskeleri (24 Ekim 2026, kullanıcı: "çantada kopça ile çanta arasında beyaz görüntü var, yok et").

Gösterge çerçevesi (GoldKit.Sticker) simgenin kopyalarını beyaz çizer; kopyalar simgenin İÇİNDEKİ kapalı boşlukları
(çanta sapının içi gibi) da doldurur. Bu betik her simgede dışarıya açılmayan boşlukları bulur ve
Resources/Icons/Holes/<ad>.png yazar (beyaz, alfa = delik). Pofi/UISticker beyaz/gölge kopyalarını bu maskede siler,
delikten arkadaki harita görünür. Deliği olmayan simge için dosya yazılmaz.

    python3 art/scripts/icon_holes.py            # tümü
    python3 art/scripts/icon_holes.py backpack_small act_enter
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Assets", "_Pofi", "Resources", "Icons")
OUT = os.path.join(ROOT, "Holes")
SIZE = 128          # maske çözünürlüğü (simge oyunda ~140 px)
MIN_AREA = 0.0006   # simge alanına oran: daha küçük delikler (göz parıltısı vb.) beyaz kalabilir, görünmez


def holes_of(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)[..., 3].astype(np.float32) / 255.0
    h, w = a.shape
    solid = a > 0.5
    # kenara 1 px boşluk ekle, dışarıyı (0) köşeden doldur: dolmayan boşluklar = kapalı delik
    pad = np.zeros((h + 2, w + 2), np.uint8)
    pad[1:-1, 1:-1] = np.where(solid, 255, 0)
    img = Image.fromarray(pad, "L").copy()   # fromarray salt okunur: floodfill kopyaya yazar
    ImageDraw.floodfill(img, (0, 0), 128)
    filled = np.asarray(img)[1:-1, 1:-1]
    hole = filled == 0
    if hole.sum() < MIN_AREA * h * w:
        return None
    # küçük delik parçalarını at (bileşen başına alan)
    lab = Image.fromarray(np.where(hole, 0, 255).astype(np.uint8), "L").copy()
    keep = np.zeros_like(hole)
    ys, xs = np.nonzero(hole)
    seen = np.zeros_like(hole)
    for y, x in zip(ys, xs):
        if seen[y, x]:
            continue
        tmp = lab.copy()
        ImageDraw.floodfill(tmp, (int(x), int(y)), 77)
        comp = np.asarray(tmp) == 77
        seen |= comp
        if comp.sum() >= MIN_AREA * h * w:
            keep |= comp
    if not keep.any():
        return None
    # deliğe komşu yarı saydam kenar pikselleri de maskeye (yoksa ince beyaz saçak kalır)
    grow = np.asarray(Image.fromarray((keep * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(5))) > 0
    mask = keep | (grow & (a < 0.98))
    m = Image.fromarray((mask * 255).astype(np.uint8), "L").resize((SIZE, SIZE), Image.BOX)
    out = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    out.putalpha(m)
    return out, keep.sum() / (h * w)


def main(names):
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(ROOT) if f.endswith(".png"))
    if names:
        files = [n + ".png" for n in names]
    made = []
    for f in files:
        r = holes_of(os.path.join(ROOT, f))
        dst = os.path.join(OUT, f)
        if r is None:
            if os.path.exists(dst):
                os.remove(dst)
            continue
        r[0].save(dst, optimize=True)
        made.append((f[:-4], r[1]))
    for n, frac in made:
        print("%-24s delik %%%.2f" % (n, frac * 100))
    print(len(made), "maske")


if __name__ == "__main__":
    main(sys.argv[1:])
