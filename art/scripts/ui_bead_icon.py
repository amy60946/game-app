"""Boncuk simgesi (K3, kullanıcı kararı 3 Kasım 2026: oyun parasının görünen adı "Boncuk").

Turkuaz, ortası delikli yuvarlak boncuk; hafif yukarıdan bakış, yumuşak ışık + parlama (vinyl oyuncak dili).
Eski altın coin simgesinin yerine Resources/Icons/ui_coin.png (ad aynı kalır, kod değişmez); delik maskesi için
ardından `python3 art/scripts/icon_holes.py ui_coin`.

    python3 art/scripts/ui_bead_icon.py [çıktı.png]
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                                           "Assets", "_Pofi", "Resources", "Icons", "ui_coin.png")
N, SS = 256, 4                      # çıktı boyu, süper örnekleme
S = N * SS
R_OUT, R_IN = 0.45, 0.16            # dış ve delik yarıçapı (boya oranla; kalın tüp, delik 64 px'te de görünür)
TILT = 0.92                         # dikey basıklık: hafif yukarıdan bakış (az basık: lastik değil boncuk)
BASE = np.array([0.15, 0.74, 0.76]) # turkuaz
DEEP = np.array([0.03, 0.40, 0.50]) # gölge tarafı
LIGHT = np.array([-0.45, 0.62, 0.64]); LIGHT /= np.linalg.norm(LIGHT)

y, x = np.mgrid[0:S, 0:S].astype(np.float32)
u = (x + 0.5) / S - 0.5
v = ((y + 0.5) / S - 0.5) / TILT
d = np.sqrt(u * u + v * v)
rc, a = (R_OUT + R_IN) / 2, (R_OUT - R_IN) / 2   # simit tüpünün merkezi ve yarıçapı
t = np.clip((d - rc) / a, -1, 1)
inside = (d <= R_OUT) & (d >= R_IN)
nz = np.sqrt(np.clip(1 - t * t, 0, 1)) * 1.6   # tüp kesiti yüksek: simit değil, yuvarlak boncuk
norm = np.sqrt(t * t + nz * nz); nz = nz / norm; t = t / norm
dirx, diry = np.where(d > 1e-6, u / np.maximum(d, 1e-6), 0), np.where(d > 1e-6, -v / np.maximum(d, 1e-6), 0)
nx, ny = t * dirx, t * diry
lam = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
col = DEEP[None, None, :] + (BASE - DEEP)[None, None, :] * (0.25 + 0.75 * lam)[..., None]
# yansıyan ışık (alt kenar biraz açık), parlama (sol üst)
col += np.clip(-ny, 0, 1)[..., None] * 0.10 * np.array([0.6, 1.0, 1.0])
hx, hy, hz = LIGHT + np.array([0, 0, 1.0]); hn = math.sqrt(hx * hx + hy * hy + hz * hz)
spec = np.clip((nx * hx + ny * hy + nz * hz) / hn, 0, 1) ** 38
col = col * (1 - spec[..., None] * 0.85) + spec[..., None] * 0.85
# dış çizgi YOK (proje kuralı): deliğin iç yüzü yalnız gölgeyle derinleşir
inner = np.clip(1 - (d - R_IN) / 0.05, 0, 1) * (v < 0)   # deliğin üst kenarının içi (yukarıdan bakış)
col = col * (1 - inner[..., None] * 0.35)
alpha = inside.astype(np.float32)
rgba = np.dstack([np.clip(col, 0, 1), alpha])
img = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").resize((N, N), Image.LANCZOS)
# küçük ikinci parlama noktası (canlılık)
img.save(OUT)
print("yazıldı", OUT)
