"""3x3 simge sayfasını tek tek şeffaf PNG'lere böler.
Kullanım: python slice_icons.py sayfa.png hedef_klasör id1,id2,…,id9 [boyut=256]
Arka plan: kenarlardan bağlı, beyaza yakın pikseller (flood fill). Nesneler bileşen olarak bulunur, 9 büyüğü satır/sütuna göre sıralanır."""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage

src, out, ids = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
size = int(sys.argv[4]) if len(sys.argv) > 4 else 256
im = np.asarray(Image.open(src).convert("RGB")).astype(np.int16)
h, w, _ = im.shape
near_white = (im.min(axis=2) > 228) & ((im.max(axis=2) - im.min(axis=2)) < 22)
lab, _ = ndimage.label(near_white)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
bg = np.isin(lab, list(border))
fg = ~bg
fg = ndimage.binary_opening(fg, iterations=1)
# nesneler: yakın parçaları birleştirmek için genişletip etiketle
grown = ndimage.binary_dilation(fg, iterations=max(4, w // 120))
objs, n = ndimage.label(grown)
sizes = ndimage.sum(np.ones_like(objs), objs, range(1, n + 1))
keep = [i + 1 for i in np.argsort(sizes)[::-1][:len(ids)]]
boxes = []
for k in keep:
    ys, xs = np.where(objs == k)
    boxes.append((ys.min(), ys.max(), xs.min(), xs.max()))
if len(boxes) < len(ids):
    raise SystemExit(f"yalnız {len(boxes)} nesne bulundu")
# satır/sütun: merkezleri 3 banda ayır
cy = np.array([(b[0] + b[1]) / 2 for b in boxes]); cx = np.array([(b[2] + b[3]) / 2 for b in boxes])
order = sorted(range(len(boxes)), key=lambda i: (int(cy[i] // (h / 3)), cx[i]))
# yumuşak kenar: arka plan maskesinin kenarını biraz bulanıklaştır
alpha = ndimage.gaussian_filter(fg.astype(np.float32), 0.8)
alpha = np.clip((alpha - 0.15) / 0.7, 0, 1)
rgba = np.dstack([im.astype(np.uint8), (alpha * 255).astype(np.uint8)])
os.makedirs(out, exist_ok=True)
for slot, i in enumerate(order):
    y0, y1, x0, x1 = boxes[i]
    pad = 6
    y0, x0 = max(0, y0 - pad), max(0, x0 - pad); y1, x1 = min(h, y1 + pad), min(w, x1 + pad)
    crop = Image.fromarray(rgba[y0:y1, x0:x1], "RGBA")
    s = max(crop.width, crop.height)
    sq = Image.new("RGBA", (s, s), (0, 0, 0, 0)); sq.paste(crop, ((s - crop.width) // 2, (s - crop.height) // 2))
    sq.resize((size, size), Image.LANCZOS).save(os.path.join(out, ids[slot] + ".png"))
    print(ids[slot], (x0, y0, x1, y1))
