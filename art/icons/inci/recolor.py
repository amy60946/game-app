import sys, os, json
from PIL import Image
import numpy as np

SRC = sys.argv[1]; OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
im = Image.open(SRC).convert('RGBA')
a = np.asarray(im).astype(np.float64) / 255
rgb = a[..., :3]; al = a[..., 3]
H, W = al.shape

def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
M1 = np.array([[0.4122214708,0.5363325363,0.0514459929],[0.2119034982,0.6806995451,0.1073969566],[0.0883024619,0.2817188376,0.6299787005]])
M2 = np.array([[0.2104542553,0.7936177850,-0.0040720468],[1.9779984951,-2.4285922050,0.4505937099],[0.0259040371,0.7827717876,-0.8086757248]])
iM2 = np.linalg.inv(M2); iM1 = np.linalg.inv(M1)
def to_lab(rgb): return np.cbrt(s2l(rgb) @ M1.T) @ M2.T
def to_lin(lab): return ((lab @ iM2.T) ** 3) @ iM1.T
def to_srgb(lab):
    # gamut map: shrink chroma until in gamut (keeps L and hue)
    L = lab[..., :1]; ab = lab[..., 1:]
    lo = np.zeros(L.shape); hi = np.ones(L.shape)
    lin = to_lin(lab)
    ok = np.all((lin >= -1e-4) & (lin <= 1 + 1e-4), axis=-1, keepdims=True)
    s = np.where(ok, 1.0, 0.5)
    for _ in range(18):
        t = np.concatenate([L, ab * s], -1)
        lin = to_lin(t)
        g = np.all((lin >= -1e-4) & (lin <= 1 + 1e-4), axis=-1, keepdims=True)
        lo = np.where(g & ~ok, s, lo); hi = np.where(~g & ~ok, s, hi)
        s = np.where(ok, 1.0, (lo + hi) / 2)
    t = np.concatenate([L, ab * np.where(ok, 1.0, lo)], -1)
    return l2s(to_lin(t))

lab = to_lab(rgb)
L = lab[..., 0]; A = lab[..., 1]; B = lab[..., 2]
m = al > 0.5
# base pink as a smooth function of L (binned means, interpolated)
bins = np.linspace(0.70, 1.0, 16)
cen, ma, mb = [], [], []
for lo, hi in zip(bins[:-1], bins[1:]):
    s = m & (L >= lo) & (L < hi)
    if s.sum() > 30:
        cen.append((lo + hi) / 2); ma.append(np.median(A[s])); mb.append(np.median(B[s]))
cen = np.array(cen)
baseA = np.interp(L, cen, ma); baseB = np.interp(L, cen, mb)
dA = A - baseA; dB = B - baseB          # iridescent sheen (rainbow film)
baseC = np.hypot(baseA, baseB)
# chroma envelope from original: how "coloured" each luminance is (tapers to 0 in the highlight)
Cmid = np.interp(0.76, cen, np.hypot(ma, mb))
env = np.clip(baseC / Cmid, 0, 1.6)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
ys, xs = np.nonzero(m)
cx, cy = xs.mean(), ys.mean(); R = np.sqrt(m.sum() / np.pi)
nx = (xx - cx) / R; ny = (yy - cy) / R
rr = np.clip(np.hypot(nx, ny), 0, 1)
diag = np.clip((nx + ny) / 2.0, -1, 1)   # -1 top-left .. +1 bottom-right

def hue_vec(deg):
    r = np.deg2rad(deg); return np.cos(r), np.sin(r)

def rot(dA, dB, deg):
    r = np.deg2rad(deg); c, s = np.cos(r), np.sin(r)
    return c * dA - s * dB, s * dA + c * dB

def variant(hue, chroma, k_sheen=1.0, sheen_rot=0.0, lmap=None, hue_field=None, chroma_field=None, warm_shadow=None):
    Ln = L.copy() if lmap is None else lmap(L)
    h = hue if hue_field is None else hue_field
    hr = np.deg2rad(h)
    hl0 = np.clip((Ln - 0.90) / 0.09, 0, 1)
    C = chroma * env if chroma_field is None else chroma_field * (1 - hl0)
    nA = C * np.cos(hr); nB = C * np.sin(hr)
    sA, sB = rot(dA, dB, sheen_rot)
    # sheen fades in the specular highlight so the highlight stays white
    hl = np.clip((Ln - 0.93) / 0.06, 0, 1)
    k = k_sheen * (1 - 0.85 * hl)
    nA = nA + k * sA; nB = nB + k * sB
    out = to_srgb(np.stack([Ln, nA, nB], -1))
    # edge bleed: soft-edge pixels take the colour of the opaque rim just inside (no light fringe)
    solid = (al >= 0.98).astype(np.float64)
    def box(x, r=3):
        k = 2 * r + 1
        p = np.pad(x, ((r, r), (r, r)) + ((0, 0),) * (x.ndim - 2), mode='edge')
        c = p.cumsum(0).cumsum(1)
        c = np.pad(c, ((1, 0), (1, 0)) + ((0, 0),) * (x.ndim - 2))
        return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    num = box(out * solid[..., None]); den = box(solid)[..., None]
    edge = (al < 0.98) & (den[..., 0] > 0)
    out = np.where(edge[..., None], num / np.maximum(den, 1e-6), out)
    o = np.concatenate([out, al[..., None]], -1)
    return Image.fromarray(np.round(np.clip(o, 0, 1) * 255).astype(np.uint8), 'RGBA')

V = {}
V['P'] = im.copy()
# W: klasik beyaz-krem — warm ivory, faint sheen
V['W'] = variant(hue=92, chroma=0.018, k_sheen=0.55, lmap=lambda L: np.clip(L + 0.025 * (1 - L) / 0.3, 0, 1))
# S: sedef — near-white body + iridescent pink→violet→blue→aqua across the sphere
sh = 350 + 60 * (diag + 1) * 1.25        # 350° (pink) top-left -> ~140°.. clamp
sh = np.interp(diag, [-1, -0.3, 0.3, 1], [355, 330, 265, 205])
V['S'] = variant(hue=0, chroma=0, k_sheen=0.9, hue_field=sh,
                 chroma_field=0.032 * np.clip(env, 0.35, 1.3) * (0.55 + 0.45 * rr),
                 lmap=lambda L: np.clip(L + 0.015, 0, 1))
# L: lavanta
V['L'] = variant(hue=305, chroma=0.060, k_sheen=0.8, lmap=lambda L: L - 0.03 * (1 - np.clip((L - 0.75) / 0.25, 0, 1)))
# T: açık turkuaz / aqua
V['T'] = variant(hue=200, chroma=0.075, k_sheen=0.7, lmap=lambda L: L - 0.05 * (1 - np.clip((L - 0.72) / 0.28, 0, 1)) ** 1.2)
# D: Tahiti — dark grey-green with peacock (green -> aubergine) sheen, white specular
from PIL import ImageFilter
_Lb = np.asarray(Image.fromarray(np.round(np.clip(L, 0, 1) * 65535 / 257).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3.0))).astype(np.float64) / 255
def lmap_dark(L):
    t = np.clip((L - 0.58) / 0.36, 0, 1)
    body = 0.27 + 0.33 * t ** 1.15     # charcoal 0.27..0.60
    spec = np.clip((_Lb - 0.945) / 0.05, 0, 1) ** 1.5   # tighter highlight, from smoothed L (no grain)
    return body * (1 - spec) + 0.96 * spec
pea = np.interp(diag, [-1, -0.1, 0.45, 1], [165, 160, 340, 320])  # green body -> aubergine rim
pea_c = 0.026 + 0.030 * rr ** 1.5
V['D'] = variant(hue=0, chroma=0, k_sheen=1.15, sheen_rot=25, hue_field=pea, chroma_field=pea_c, lmap=lmap_dark)
# M: mercan / şeftali
V['M'] = variant(hue=40, chroma=0.085, k_sheen=0.6, lmap=lambda L: L - 0.035 * (1 - np.clip((L - 0.72) / 0.28, 0, 1)))
# G: şampanya
V['G'] = variant(hue=76, chroma=0.068, k_sheen=0.6, lmap=lambda L: L - 0.02 * (1 - np.clip((L - 0.72) / 0.28, 0, 1)))

for k, v in V.items():
    v.save(os.path.join(OUT, k + '.png'))
print('ok', list(V))
