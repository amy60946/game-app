"""
Sonradan eklenen patikaları (island_v6_layout.json "extra_paths") pişmiş zemin dokusuna boyar (GB20-7, 2 Kasım 2026: bahçe ve
festival taşındı, kapılarına kısa patika). Arazi yeniden pişirilmez; doku RGB'si mevcut bir patikanın (meydan → Evim) desenini
döşeyerek, yumuşak kenarla karışır. Alfa (kum ağırlığı) değişmez. Bir kez çalıştırılır; arazi yeniden pişirilirse bu patikalar
terrain_v6.PATHS'te zaten var (gerek kalmaz).
Kullanım: python3 -I art/scripts/paint_paths.py
"""
import json, os, math
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX = os.path.join(ROOT, "Assets", "_Pofi", "Resources", "Env", "ground_v6", "ground_v6.png")
LAY = os.path.join(ROOT, "Assets", "_Pofi", "Resources", "Data", "island_v6_layout.json")
X0, X1, Z0, Z1 = -100.0, 100.0, -88.0, 88.0
CORE, EDGE, OUT = 1.35, 1.85, 2.5   # oyundaki patika kesiti (meydan → Evim ölçüsü): toprak çekirdek, sarımsı kenar, çimene geçiş (m)
CORE_RGB = np.array([174.0, 146.0, 108.0])
EDGE_RGB = np.array([166.0, 155.0, 88.0])


def vnoise(x, z):
    """Yumuşak değer gürültüsü (1,2 m ölçek): toprakta hafif ton dalgası (döşeme karesi görünmesin)."""
    def h(i, j): return (math.sin(i * 127.1 + j * 311.7) * 43758.5453) % 1.0
    fx, fz = x / 1.2, z / 1.2
    i, j = math.floor(fx), math.floor(fz); tx, tz = fx - i, fz - j
    tx, tz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
    a = h(i, j) * (1 - tx) + h(i + 1, j) * tx
    b = h(i, j + 1) * (1 - tx) + h(i + 1, j + 1) * tx
    return a * (1 - tz) + b * tz


def main():
    lay = json.load(open(LAY))
    paths = lay.get("extra_paths") or []
    im = Image.open(TEX).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    mx, mz = W / (X1 - X0), H / (Z1 - Z0)               # piksel / m
    # her pikselde bütün yeni parçalara en yakın uzaklık (parça birleşimlerinde dikiş/halka kalmasın), sonra tek seferde kesit
    segs = [(ax, az, bx, bz) for line in paths for (ax, az), (bx, bz) in zip(line[:-1], line[1:])]
    if not segs: print("patika yok"); return
    lo_x = min(min(s_[0], s_[2]) for s_ in segs) - OUT; hi_x = max(max(s_[0], s_[2]) for s_ in segs) + OUT
    lo_z = min(min(s_[1], s_[3]) for s_ in segs) - OUT; hi_z = max(max(s_[1], s_[3]) for s_ in segs) + OUT
    done = 0
    for j in range(max(0, int((Z1 - hi_z) * mz)), min(H, int((Z1 - lo_z) * mz) + 1)):
        z = Z1 - (j + 0.5) / mz
        for i in range(max(0, int((lo_x - X0) * mx)), min(W, int((hi_x - X0) * mx) + 1)):
            x = X0 + (i + 0.5) / mx
            d = OUT
            for ax, az, bx, bz in segs:
                dx, dz = bx - ax, bz - az; l2 = dx * dx + dz * dz
                t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / l2)) if l2 > 0 else 0.0
                d = min(d, math.hypot(ax + t * dx - x, az + t * dz - z))
            if d >= OUT: continue
            core = CORE_RGB * (0.96 + 0.08 * vnoise(x, z))
            if d <= CORE: c, w = core, 1.0
            elif d <= EDGE: k = (d - CORE) / (EDGE - CORE); c, w = core * (1 - k) + EDGE_RGB * k, 1.0
            else: k = (d - EDGE) / (OUT - EDGE); c, w = EDGE_RGB, 1.0 - k * k * (3 - 2 * k)
            cur = a[j, i, :3]
            new = cur * (1 - w) + c * w
            # mevcut patikayla kesişimde: yalnız daha "toprak" olan renk yazılır (eski patikanın içinde kenar halkası çıkmasın)
            if d > CORE and np.abs(new - CORE_RGB).sum() > np.abs(cur - CORE_RGB).sum(): continue
            a[j, i, :3] = new
            done += 1
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA").save(TEX, optimize=True)
    print("boyandı", len(paths), "patika,", done, "piksel")


if __name__ == "__main__":
    main()
