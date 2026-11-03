"""OKLab yardımcıları (kehribar + güneş taşı yeniden boyama)."""
import numpy as np

M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717876, -0.8086757248]])
iM1, iM2 = np.linalg.inv(M1), np.linalg.inv(M2)


def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def to_lab(rgb): return np.cbrt(s2l(rgb) @ M1.T) @ M2.T


def to_lin(lab): return ((lab @ iM2.T) ** 3) @ iM1.T


def to_srgb(lab):
    L, ab = lab[..., :1], lab[..., 1:]
    lo, hi = np.zeros(L.shape), np.ones(L.shape)
    for _ in range(18):
        s = (lo + hi) / 2
        lin = to_lin(np.concatenate([L, ab * s], -1))
        g = np.all((lin >= -1e-4) & (lin <= 1 + 1e-4), -1, keepdims=True)
        lo, hi = np.where(g, s, lo), np.where(g, hi, s)
    lin = to_lin(lab)
    ok = np.all((lin >= -1e-4) & (lin <= 1 + 1e-4), -1, keepdims=True)
    return l2s(to_lin(np.concatenate([L, ab * np.where(ok, 1.0, lo)], -1)))


def lch(L, C, h_deg):
    h = np.deg2rad(h_deg)
    return np.stack([L, C * np.cos(h), C * np.sin(h)], -1)


def to_lch(rgb):
    lab = to_lab(rgb)
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.rad2deg(np.arctan2(lab[..., 2], lab[..., 1]))
