# Düz krem zeminli taslak hücresinden saydam portre: köşelerden taşma (flood fill) ile zemin maskesi, yumuşak kenar.
import sys
import numpy as np
from PIL import Image, ImageFilter
from collections import deque
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB'); a = np.asarray(im).astype(np.int16); h, w, _ = a.shape
bg = np.median(np.concatenate([a[:6, :6].reshape(-1, 3), a[:6, -6:].reshape(-1, 3), a[-6:, :6].reshape(-1, 3), a[-6:, -6:].reshape(-1, 3)]), 0)
d = np.abs(a - bg).sum(2)
near = d < 34
mask = np.zeros((h, w), bool); q = deque()
for y in range(h):
    for x in (0, w - 1):
        if near[y, x] and not mask[y, x]: mask[y, x] = True; q.append((y, x))
for x in range(w):
    for y in (0, h - 1):
        if near[y, x] and not mask[y, x]: mask[y, x] = True; q.append((y, x))
while q:
    y, x = q.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not mask[ny, nx]:
            mask[ny, nx] = True; q.append((ny, nx))
alpha = Image.fromarray(((~mask) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
rgba = im.copy(); rgba.putalpha(alpha)
bb = rgba.getbbox(); rgba = rgba.crop(bb)
rgba.thumbnail((420, 420)); rgba.save(out, optimize=True)
print(out, rgba.size)
