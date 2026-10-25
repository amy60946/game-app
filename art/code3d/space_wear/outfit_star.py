# Yıldız kaşifi (25 Ekim 2026, onaylı konsept 3): lila-mor tulum, dikiş yerlerinde camgöbeği biye (ön orta, göğüs boyunduruğu,
# gövde yanları, bacak dışı, bilek ve diz yaması kenarı), irili ufaklı yıldız/gezegen/ay yamaları, koyu lila diz yastığı,
# mor eldiven (camgöbeği ağız), camgöbeği kenarlı mor bot (yanında sarı yıldız). Kuyrukluyıldız pelerini ve antenli taç ayrı
# eşya (space_items.py). Özgün tasarım.
import math
import numpy as np
import space_kit as K

ID = 'outfit_star'
AO = 0.45
STATE = {}

LILAC = '#b39ae6'; LILAC_D = '#9178d2'; LILAC_L = '#cbb8f0'; CYAN = '#43d2e2'; CYAN_D = '#22a9bd'
YELLOW = '#ffd34d'; PINK = '#ff8db6'; ORANGE = '#ff9e4f'; BLUE = '#6aa8ff'; MINT = '#7fe0b4'
GLOVE = '#a284dc'; BOOT = '#7556c6'; BOOT_D = '#5d40a8'

# yamalar: (yer, …, boy × H, tür, renk)
#   gövde: ('t', z oranı, açı) · uzuv: ('arm'|'leg', taraf, t oranı (dirsek/diz), açı)
PATCHES = [
    (('t', 0.62, 0.45), 0.030, 'planet', ORANGE), (('t', 0.70, -0.38), 0.016, 'star', YELLOW), (('t', 0.48, -0.55), 0.012, 'star', PINK),
    (('t', 0.40, 0.30), 0.010, 'star', CYAN), (('t', 0.28, -0.25), 0.014, 'moon', YELLOW), (('t', 0.22, 0.62), 0.011, 'star', YELLOW),
    (('t', 0.55, 2.7), 0.022, 'planet', BLUE), (('t', 0.38, -2.6), 0.014, 'star', YELLOW), (('t', 0.70, 3.0), 0.012, 'star', PINK),
    (('arm', 'L', 0.65, 1.3), 0.018, 'moon', YELLOW), (('arm', 'R', 0.6, 1.3), 0.016, 'star', PINK), (('arm', 'L', 1.6, 0.6), 0.010, 'star', CYAN),
    (('arm', 'R', 1.7, 0.5), 0.010, 'star', YELLOW),
    (('leg', 'L', 0.45, 0.9), 0.016, 'star', YELLOW), (('leg', 'R', 0.5, 1.1), 0.020, 'planet', MINT), (('leg', 'L', 1.35, 0.4), 0.010, 'star', PINK),
    (('leg', 'R', 1.4, -0.3), 0.011, 'star', CYAN), (('leg', 'L', 0.75, 2.6), 0.012, 'star', YELLOW),
]


def _patch_place(B, where):
    if where[0] == 't':
        return K.anchor_torso(B, K.torso_z(B, where[1]), where[2]), (0, 0, 1)
    kind, S, tf, a = where
    ch = (B.arms if kind == 'arm' else B.legs)[S]
    t = (B.elbow_t[S] if kind == 'arm' else B.knee_t[S]) * tf
    c, d = ch.point(t)
    return K.anchor_limb(B, kind, S, t, a), tuple(-np.array(d))


def spec(B):
    H = B.H

    def disp(B, C, piece, S):
        out = np.zeros(len(C['P']))
        if piece != 'torso': return out
        for S_ in 'LR':
            c, u = K.anchor_limb(B, 'leg', S_, B.knee_t[S_], 0.0)
            d = np.linalg.norm(C['P'] - c, axis=1)
            out += 0.0035 * H * (1 - K.sstep(0.03 * H, 0.04 * H, d))
        return out

    def boot_profile(B, S, zf):
        return 0.004 * K.sstep(0.14, 0.07, zf) + 0.0045 * np.exp(-((zf - 0.94) / 0.05) ** 2)

    return K.SuitSpec(off_suit=0.0095, off_glove=0.0125, off_boot=0.016, boot_k=0.45, disp=disp, boot_profile=boot_profile)


def _piping(Pt, d, mask, w=None):
    """Camgöbeği yuvarlak biye (kabarık kordon) d = 0 çizgisinde."""
    H = Pt.H; w = w or 0.0028 * H
    dd = np.where(mask > 0.5, d, 1e3)
    m = K.line_mask(dd, w, 0.0006 * H)
    Pt.fill(m, CYAN)
    x = np.clip(np.abs(dd) / w, 0, 1)
    Pt.bump(m * np.sqrt(np.maximum(0, 1 - x * x)) * 0.0016 * H)
    Pt.fill(m * K.sstep(0.2, -0.6, dd / w), '#a6f4fb', 0.5)          # üst kenarda ışık
    Pt.shade(K.line_mask(np.abs(dd) - w - 0.0012 * H, 0.0012 * H, 0.0005 * H) * mask, 0.82)


def _shape(kind, X, Y, r):
    if kind == 'star': return K.star_sdf(X, Y, r, inner=0.48)
    if kind == 'moon': return np.maximum(K.sd_circle(X, Y, r), -K.sd_circle(X - 0.42 * r, Y - 0.22 * r, r * 0.82))
    return K.sd_circle(X, Y, r * 0.62)


def paint(Pt):
    B = Pt.B; H = Pt.H
    Pt.fill(np.ones(Pt.n), LILAC)
    # yumuşak örme: ince dikey ilmek çizgisi + kumaş
    Pt.fabric(amt=0.045)
    suit = Pt.m_reg(0, 1, 2, 3, 4); m0 = Pt.m_reg(0)
    # biyeler: ön orta, göğüs boyunduruğu (önde yay), gövde yanları
    front = np.abs(Pt.ta) < 1.2
    _piping(Pt, Pt.ta * Pt.tr, m0 * front)
    zy = K.torso_z(B, 0.80) - 0.07 * H * np.cos(np.clip(Pt.ta, -1.5, 1.5)) ** 2
    _piping(Pt, Pt.tz - zy, m0 * (np.abs(Pt.ta) < 1.45))
    for sg in (1, -1):
        _piping(Pt, (Pt.ta - sg * math.pi / 2) * Pt.tr, m0 * (Pt.tz < K.torso_z(B, 0.62)))
    for S in 'LR':
        L = Pt.lim['leg' + S]; rg = 3 if S == 'L' else 4
        _piping(Pt, (L['a'] - math.pi / 2) * L['r'], Pt.m_reg(rg))
        A = Pt.lim['arm' + S]; tg = A['L'] * 0.66; ra = 1 if S == 'L' else 2
        _piping(Pt, A['t'] - (tg - 0.006 * H), Pt.m_reg(ra))                     # bilekte halka
        _piping(Pt, (A['a'] - math.pi * 0.98) * A['r'], Pt.m_reg(ra) * (A['t'] > A['L'] * 0.12))   # kolun altı (iç dikiş)
    # diz yastıkları: koyu lila oval + biye kenar
    for S in 'LR':
        c, u = K.anchor_limb(B, 'leg', S, B.knee_t[S], 0.0)
        up = tuple(-np.array(B.legs[S].point(B.knee_t[S])[1]))
        X, Y, mm = Pt.decal(c, u, up=up); mm = mm * suit
        sd = K.sd_ellipse(X, Y, 0.036 * H, 0.042 * H)
        m = mm * K.inside(sd, 0.0008 * H)
        Pt.fill(m, LILAC_D); Pt.bump(m * 0.0008 * H)
        _piping(Pt, sd, mm, w=0.0022 * H)
        Pt.fill(m * K.inside(K.star_sdf(X, Y, 0.014 * H, inner=0.5), 0.0005 * H), LILAC_L, 0.8)
    # yamalar: yıldız, gezegen (halkalı), hilal
    for where, size, kind, colr in PATCHES:
        if where[0] in ('arm', 'leg') and where[1] not in 'LR': continue
        (c, u), up = _patch_place(B, where)
        X, Y, mm = Pt.decal(c, u, up=up)
        rg = 0 if where[0] == 't' else ((1 if where[1] == 'L' else 2) if where[0] == 'arm' else (3 if where[1] == 'L' else 4))
        mm = mm * Pt.m_reg(rg)
        r = size * H * 1.35
        sd = _shape(kind, X, Y, r)
        Pt.h = Pt.h * (1 - mm * K.inside(sd - 0.004 * H, 0.002 * H))
        rim = mm * K.inside(sd - 0.0022 * H, 0.0005 * H)
        Pt.fill(rim, '#ffffff', 0.9); Pt.bump(rim * 0.0008 * H)
        m = mm * K.inside(sd, 0.0005 * H)
        Pt.fill(m, colr); Pt.bump(m * 0.0005 * H)
        Pt.fill(m * K.sstep(-0.2 * r, 0.6 * r, -X + Y) * 0.35, '#ffffff')
        if kind == 'planet':
            ring = mm * K.line_mask(K.sd_ellipse(X, Y * 2.8 - X * 0.6, r * 1.05, r * 1.05), 0.0016 * H, 0.0005 * H)
            front_half = (Y * 2.8 - X * 0.6) < 0
            Pt.fill(ring * np.where(front_half | (sd > 0), 1.0, 0.0), '#fff1a8'); Pt.bump(ring * 0.0006 * H)
            Pt.fill(m * K.line_mask(Y - 0.15 * r, 0.06 * r, 0.03 * r) * 0.35, '#000000')
        Pt.stitches(np.where(mm > 0.5, sd, 1e3), 0.0012 * H, along=np.arctan2(Y, X) * r, col='#6e56b0', alpha=0.55, width=0.0005 * H, period=0.0035 * H)
    # eldiven: mor, camgöbeği ağız
    for S, rg in (('L', 5), ('R', 6)):
        L = Pt.lim['arm' + S]; tg = L['L'] * 0.66; m = Pt.m_reg(rg)
        Pt.fill(m, GLOVE)
        cf = m * (1 - K.sstep(tg + 0.018 * H, tg + 0.02 * H, L['t']))
        Pt.fill(cf, CYAN); Pt.bump(cf * 0.0008 * H)
        Pt.seam(np.where(m > 0.5, L['t'] - (tg + 0.019 * H), 1e3), width=0.0014 * H, depth=0.0008 * H, dark=0.75)
        dd = np.where((m > 0.5) & (L['t'] > tg + 0.022 * H), (L['a'] - math.pi / 2) * L['r'], 1e3)
        Pt.seam(dd, width=0.0016 * H, depth=0.0008 * H, dark=0.85)
    # botlar: mor, camgöbeği ağız ve taban, yanda sarı yıldız
    for S, rg in (('L', 7), ('R', 8)):
        m = Pt.m_reg(rg); bz = K._boot_z(B, K.SuitSpec(boot_k=0.45), S); zb = B.minz
        zf = (Pt.tz - zb) / (bz - zb)
        Pt.fill(m, BOOT)
        top = m * K.sstep(0.82, 0.84, zf); Pt.fill(top, CYAN); Pt.bump(top * 0.001 * H)
        sole = m * (1 - K.sstep(0.13, 0.15, zf)); Pt.fill(sole, CYAN_D)
        Pt.bump(sole * K.puff(np.mod(Pt.tz / (0.0045 * H), 1.0)) * 0.0007 * H)
        for e in (0.83, 0.14):
            Pt.seam(np.where(m > 0.5, (zf - e) * (bz - zb), 1e3), width=0.0016 * H, depth=0.001 * H, dark=0.72)
        Pt.fill(m * K.line_mask(zf - 0.5, 0.012, 0.004) * 0.0, BOOT_D)
        c, u = K.anchor_limb(B, 'leg', S, B.ankle_t[S] - 0.02 * H, math.pi / 2)
        X, Y, mm = Pt.decal(c, u); mm = mm * m
        sd = K.star_sdf(X, Y - 0.004 * H, 0.016 * H, inner=0.48)
        st = mm * K.inside(sd, 0.0005 * H)
        Pt.fill(mm * K.inside(sd - 0.002 * H, 0.0005 * H), '#ffffff', 0.9)
        Pt.fill(st, YELLOW); Pt.bump(st * 0.0012 * H)
    Pt.wear(0.04)
