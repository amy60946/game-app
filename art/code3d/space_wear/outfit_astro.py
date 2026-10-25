# Klasik astronot (25 Ekim 2026, onaylı konsept 1): kabarık beyaz tulum, mercan-turuncu omuz ve diz yastıkları, kapitone dilimli
# kol/bacak, bilekte ve baldırda turuncu bant, beyaz eldiven (turuncu ağız), iri ay botu (gri tırtıklı taban), göğüste 3 ışıklı
# yaşam ünitesi + iki alt köşesinden önde U çizip göğsün yanındaki bağlantılara çıkan tırtıklı hortum. Kask (cam fanus + yaka halkası) ve sırt çantası ayrı eşya
# (space_items.py). Yama: sol göğüste gezegenli yuvarlak arma, sağda ada güneşi. Özgün tasarım.
import math
import numpy as np
from mathutils import Vector as V
import bpy, bmesh
import space_kit as K

ID = 'outfit_astro'
AO = 0.5
STATE = {}

WHITE = '#f2f0eb'; WHITE2 = '#e4e3e0'; ORANGE = '#f27d4a'; ORANGE_D = '#d9653a'; GREY = '#bfc4cf'; GREY_D = '#9aa1b0'
NAVY = '#2c4672'; HOSE = '#a3aac6'; METAL = '#c8ccd6'


def _arm_up(B, S):
    """Kol armasının yukarısı: kol zinciri boyunca omuza doğru."""
    c, d = B.arms[S].point(B.elbow_t[S] * 0.6); return tuple(-np.array(d))


def _seg(B):
    H = B.H
    return dict(arm=(0.048 * H, 0.03 * H), leg=(0.052 * H, 0.06 * H))     # dilim boyu, başlangıç (zincirde)


def _pads(B):
    """Omuz ve diz yastıklarının merkezleri (vücut yüzeyinde) ve yönleri."""
    if B.stage in STATE.get('pads', {}): return STATE['pads'][B.stage]
    H = B.H; out = {}
    for S in 'LR':
        ch = B.arms[S]
        c, u = K.anchor_limb(B, 'arm', S, 0.035 * H + 0.02 * ch.L, math.pi / 2 * 0.75)      # omuz başı: dış-üst
        up = np.array([0, 0, 1.0])
        out['sh' + S] = (c + up * 0.012 * H, u)
        c, u = K.anchor_limb(B, 'leg', S, B.knee_t[S], 0.0)
        out['kn' + S] = (c, u)
    STATE.setdefault('pads', {})[B.stage] = out
    return out


def spec(B):
    H = B.H

    def disp(B, C, piece, S):
        n = len(C['P']); out = np.zeros(n)
        seg = _seg(B)
        if piece == 'torso':
            g = C['g5']
            for S_, gi_a, gi_l in (('L', 1, 3), ('R', 2, 4)):
                for kind, gi in (('arm', gi_a), ('leg', gi_l)):
                    L, st = seg[kind]; t = C[kind + S_ + '_t']
                    f = np.mod((t - st) / L, 1.0)
                    on = K.sstep(st + 0.3 * L, st + 0.8 * L, t)
                    # diz/dirsek bükülme bölgesinde dilim kabarığı yok (derin bükülmede kat kat buruşuyordu)
                    jt = B.knee_t[S_] if kind == 'leg' else B.elbow_t[S_]
                    calm = K.sstep(0.03 * H, 0.06 * H, np.abs(t - jt))
                    out += g[:, gi] * on * calm * K.puff(f) * 0.0032 * H
            # gövde: hafif yatay kapitone
            w0 = g[:, 0]
            zf = (C['tz'] - B.hips_z) / max(1e-6, K.torso_z(B, 1.0) - B.hips_z)
            out += w0 * K.puff(np.mod(zf * 4.0, 1.0)) * 0.0012 * H * K.sstep(0.05, 0.15, zf)
            # yastıklar
            pads = _pads(B)
            for key, (c, u) in pads.items():
                d = np.linalg.norm(C['P'] - c, axis=1)
                r = 0.060 * H if key.startswith('sh') else 0.050 * H
                amp = 0.0055 if key.startswith('sh') else 0.0028          # diz yastığı ince (bükülmede katlanmasın)
                out += amp * H * (1 - K.sstep(r * 0.6, r * 1.02, d)) * K.sstep(-0.3, 0.2, (C['P'] - c) @ u / max(1e-6, r) + 0.6)
        elif piece and piece.startswith('glove'):
            ch = B.arms[S]; t = C['arm' + S + '_t'] - ch.L * 0.66
            out += 0.004 * H * np.exp(-((t - 0.012 * H) / (0.009 * H)) ** 2)        # ağız kıvrımı
        return out

    def boot_profile(B, S, zf):
        H = 1.0
        return 0.008 * K.sstep(0.22, 0.12, zf) + 0.005 * np.exp(-((zf - 0.93) / 0.06) ** 2)   # taban taşkını + ağız kıvrımı

    return K.SuitSpec(off_suit=0.012, off_glove=0.016, off_boot=0.022, boot_k=0.5, disp=disp, boot_profile=boot_profile)


# ------------------------------------------------------------------ göğüs yaşam ünitesi + hortumlar

def extras(B, ob, bvh):
    H = B.H
    z = K.torso_z(B, 0.58)
    c, n = K.surf_point(B, bvh, 'torso', z=z, a=0.0)
    cl, _ = K.surf_point(B, bvh, 'torso', z=z, a=math.pi / 2); cr, _ = K.surf_point(B, bvh, 'torso', z=z, a=-math.pi / 2)
    width = np.linalg.norm(cl - cr)
    W = 0.40 * width; Hh = 0.62 * W; D = 0.30 * W
    n = np.array(n); n[2] *= 0.3; n /= np.linalg.norm(n)
    up = np.array([0, 0, 1.0]); up = up - n * (up @ n); up /= np.linalg.norm(up); rt = np.cross(up, n)   # rt ≈ +X
    ctr = c + n * (D * 0.42)
    STATE['box'] = dict(c=ctr, n=n, up=up, rt=rt, W=W, Hh=Hh, D=D)
    M = np.eye(4); M[:3, 0] = rt; M[:3, 1] = up; M[:3, 2] = n; M[:3, 3] = ctr
    from mathutils import Matrix
    Mm = Matrix(M.tolist())
    bpy.ops.mesh.primitive_cube_add(size=1)
    box = bpy.context.object; box.scale = (W, Hh, D); bpy.ops.object.transform_apply(scale=True)
    bv = box.modifiers.new('bv', 'BEVEL'); bv.width = D * 0.32; bv.segments = 3; bv.limit_method = 'NONE'
    box.matrix_world = Mm
    bm = K.obj_to_bm(box, 20)
    # ışıklar: üç yuvarlak kubbe (camgöbeği, yeşil, mercan)
    for k, code in enumerate((22, 23, 24)):
        x = (k - 1) * W * 0.27
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1)
        s = bpy.context.object; s.scale = (W * 0.095, W * 0.095, D * 0.22)
        s.location = V(ctr + rt * x + up * Hh * 0.13 + n * (D * 0.5)); s.rotation_euler = Mm.to_euler()
        K.merge_bm(bm, K.obj_to_bm(s, code))
    # iki küçük düğme (alt sıra)
    for k in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=W * 0.05, depth=D * 0.25)
        s = bpy.context.object; s.location = V(ctr + rt * (k * W * 0.2) - up * Hh * 0.24 + n * (D * 0.5)); s.rotation_euler = Mm.to_euler()
        K.merge_bm(bm, K.obj_to_bm(s, 26))
    parts = [K.extra_object(bm, B, 20, 'astro_box', labels=lambda b: {v: 0 for v in b.verts})]     # ünite tek parça (göğüsle)
    # hortumlar: kutunun alt köşelerinden aşağı sarkar, yana kıvrılıp göğsün yan önündeki bağlantıya girer
    hr = 0.0085 * H
    for sgn in (1, -1):        # +1: Okti'nin solu (+X)
        start = ctr + rt * (W * 0.36) * sgn - up * (Hh * 0.45)            # rt = +X (Okti'nin solu)
        pts = [start]
        # önde U: aşağı sarkar, yana kıvrılıp göğsün yan önündeki bağlantıya çıkar (kolun altından geçmez: koltuk altında kol çarpıyordu)
        for fr, a in ((0.40, 0.30), (0.22, 0.55), (0.24, 0.86), (0.42, 1.04), (0.54, 1.10)):
            p, nn = K.surf_point(B, bvh, 'torso', z=K.torso_z(B, fr), a=sgn * a, out=hr + 0.004 * H)
            pts.append(p)
        curve = K.catmull([V(p) for p in pts], per=10)
        # yüzeye yapıştır (eksenden dışa ışın)
        out = [curve[0]]
        for p in curve[1:]:
            cx, cy = B.spine_xy(p.z); d = V((p.x - cx, p.y - cy, 0)); dl = d.length
            if dl < 1e-6: out.append(p); continue
            d /= dl
            hit = bvh.ray_cast(V((cx, cy, p.z)), d, 2.0)
            out.append(hit[0] + hit[1] * (hr + 0.004 * H) if hit[0] is not None else p)
        # yeniden örnekle (eşit aralık)
        res = [out[0]]; acc = 0.0; step = 0.004 * H
        for a_, b_ in zip(out, out[1:]):
            seg = (b_ - a_).length; t = step - acc
            while t <= seg:
                res.append(a_.lerp(b_, t / seg)); t += step
            acc = seg - (t - step)
        res.append(out[-1])
        hb = bmesh.new()
        K.tube_along(hb, res, hr, seg=8, rib=(0.013 * H, 0.16), code=25)
        # bağlantı halkaları (iki uçta)
        for p, q in ((res[0], res[1]), (res[-1], res[-2])):
            d = (q - p).normalized()
            K.tube_along(hb, [p - d * 0.006 * H, p + d * 0.012 * H], hr * 1.35, seg=12, code=26)
        cl = np.array([tuple(p) for p in res])
        def lab(b, cl=cl):                                   # hortum: merkez çizgisindeki en yakın örnek → halka kümesi
            return {v: int(np.argmin(np.linalg.norm(cl - np.array(tuple(v.co)), axis=1))) for v in b.verts}
        parts.append(K.extra_object(hb, B, 25, 'astro_hose', labels=lab, smooth=3))
    return parts


# ------------------------------------------------------------------ boya

def _quilt(Pt, kind, S, seg, start, depth=0.0024):
    H = Pt.H; L = Pt.lim[kind + S]; t = L['t']
    m = Pt.limb_of(kind, S) * (1 - Pt.m_reg(5, 6, 7, 8))
    f = np.mod((t - start) / seg, 1.0); on = K.sstep(start + 0.3 * seg, start + 0.8 * seg, t) * m
    Pt.bump(on * K.puff(f) * depth * H)
    dseam = np.minimum(f, 1 - f) * seg
    d = np.where(on > 0.5, dseam, 1e3)
    Pt.seam(d, width=0.0032 * H, depth=0.0014 * H, dark=0.8)
    arc = L['a'] * np.maximum(L['r'], 0.01)
    ds = np.where(on > 0.5, np.where(f < 0.5, f * seg, (f - 1) * seg), 1e3)      # en yakın dikişe işaretli uzaklık
    for off in (-0.0055 * H, 0.0055 * H):
        Pt.stitches(ds, off, along=arc, col='#d9d6cf', alpha=0.9, width=0.0009 * H, period=0.007 * H)


def paint(Pt):
    B = Pt.B; H = Pt.H
    Pt.fill(np.ones(Pt.n), WHITE)
    Pt.fabric(amt=0.035)
    reg = Pt.reg
    seg = _seg(B)
    for S in 'LR':
        _quilt(Pt, 'arm', S, *seg['arm'])
        _quilt(Pt, 'leg', S, *seg['leg'])
    # gövde: ön orta kapama (gizli fermuar), bel dikişi, hafif yatay kapitone
    m0 = Pt.m_reg(0)
    zf = (Pt.tz - B.hips_z) / max(1e-6, K.torso_z(B, 1.0) - B.hips_z)
    front = np.abs(Pt.ta) < 1.2
    dz = np.where((m0 > 0.5) & front, Pt.ta * Pt.tr, 1e3)
    Pt.seam(dz, width=0.003 * H, depth=0.0016 * H, dark=0.82)
    Pt.stitches(dz, 0.006 * H, along=Pt.tz, col='#d6d3cc', width=0.0009 * H, period=0.007 * H)
    Pt.stitches(dz, -0.006 * H, along=Pt.tz, col='#d6d3cc', width=0.0009 * H, period=0.007 * H)
    fq = np.mod(zf * 4.0, 1.0); qon = (m0 > 0.5) & (zf > 0.12)
    Pt.bump(np.where(qon, K.puff(fq) * 0.0012 * H, 0))
    Pt.seam(np.where(qon & (np.abs(Pt.ta) > 0.12), np.minimum(fq, 1 - fq) / 4.0 * (K.torso_z(B, 1.0) - B.hips_z), 1e3), width=0.0022 * H, depth=0.0008 * H, dark=0.88)
    # omuz ve diz yastıkları (turuncu, kenarı dikişli)
    for key, (c, u) in _pads(B).items():
        d = np.linalg.norm(Pt.P - c, axis=1)
        r = 0.060 * H if key.startswith('sh') else 0.050 * H
        side = K.sstep(-0.3, 0.2, (Pt.P - c) @ u / r + 0.6)
        sd = (d - r * 0.92)
        m = K.inside(sd, 0.0012 * H) * side * (1 - Pt.m_reg(5, 6, 7, 8, 9))
        Pt.fill(m, ORANGE)
        Pt.fill(m * K.sstep(r * 0.2, r * 0.9, d) * 0.35, ORANGE_D)
        Pt.bump(m * 0.0008 * H)
        Pt.seam(np.where(side > 0.5, sd, 1e3), width=0.0025 * H, depth=0.0012 * H, dark=0.75)
        Xp, Yp, _ = Pt.decal(c, u, reach=0.2 * H)
        Pt.stitches(np.where((side > 0.5) & (m > 0.5), sd, 1e3), -0.006 * H, col='#ffd9c4', alpha=0.85, width=0.0009 * H, period=0.007 * H,
                    along=np.arctan2(Yp, Xp) * r)
    # bilekte ve baldırda turuncu bant
    for S in 'LR':
        L = Pt.lim['arm' + S]; tg = L['L'] * 0.66
        m = Pt.m_reg(1 if S == 'L' else 2)
        band = m * K.sstep(tg - 0.045 * H, tg - 0.042 * H, L['t']) * (1 - K.sstep(tg - 0.012 * H, tg - 0.009 * H, L['t']))
        Pt.fill(band, ORANGE); Pt.bump(band * 0.0012 * H)
        for e in (tg - 0.0435 * H, tg - 0.0105 * H):
            Pt.seam(np.where(m > 0.5, L['t'] - e, 1e3), width=0.002 * H, depth=0.001 * H, dark=0.78)
        Lg = Pt.lim['leg' + S]; bz = K._boot_z(B, K.SuitSpec(boot_k=0.5), S)
        ml = Pt.m_reg(3 if S == 'L' else 4)
        bandl = ml * K.sstep(bz + 0.012 * H, bz + 0.015 * H, Pt.tz) * (1 - K.sstep(bz + 0.04 * H, bz + 0.043 * H, Pt.tz))
        Pt.fill(bandl, ORANGE); Pt.bump(bandl * 0.0012 * H)
        for e in (bz + 0.0135 * H, bz + 0.0415 * H):
            Pt.seam(np.where(ml > 0.5, Pt.tz - e, 1e3), width=0.002 * H, depth=0.001 * H, dark=0.78)
    # eldiven: beyaz, turuncu ağız, dış yanda dikiş
    for S, rg in (('L', 5), ('R', 6)):
        L = Pt.lim['arm' + S]; tg = L['L'] * 0.66; m = Pt.m_reg(rg)
        cuff = m * (1 - K.sstep(tg + 0.026 * H, tg + 0.029 * H, L['t']))
        Pt.fill(m, '#f4f2ee'); Pt.fill(cuff, '#d3d7df')
        Pt.seam(np.where(m > 0.5, L['t'] - (tg + 0.0275 * H), 1e3), width=0.002 * H, depth=0.001 * H, dark=0.75)
        Pt.seam(np.where((m > 0.5) & (L['t'] > tg + 0.03 * H), (L['a'] - math.pi / 2) * L['r'], 1e3), width=0.0022 * H, depth=0.001 * H, dark=0.84)
        Pt.stitches(np.where((m > 0.5) & (L['t'] > tg + 0.03 * H), (L['a'] - math.pi / 2) * L['r'], 1e3), 0.004 * H, along=L['t'], col='#d4d0c8', width=0.0008 * H, period=0.006 * H)
    # botlar: beyaz gövde, gri tırtıklı taban, gri ağız, önde turuncu kayış + toka
    for S, rg in (('L', 7), ('R', 8)):
        m = Pt.m_reg(rg); bz = K._boot_z(B, K.SuitSpec(boot_k=0.5), S); zb = B.minz
        zf = (Pt.tz - zb) / (bz - zb)
        Pt.fill(m, '#efede8')
        sole = m * (1 - K.sstep(0.24, 0.26, zf))
        Pt.fill(sole, GREY)
        rib = np.mod(Pt.tz / (0.0075 * H), 1.0)
        Pt.bump(sole * K.puff(rib) * 0.0012 * H)
        Pt.shade(sole * (1 - K.puff(rib)) ** 3, 0.82)
        Pt.seam(np.where(m > 0.5, zf - 0.25, 1e3) * (bz - zb), width=0.0024 * H, depth=0.0014 * H, dark=0.72)
        under = m * (1 - K.sstep(0.015, 0.03, zf)) * (Pt.N[:, 2] < -0.5)
        tread = K.puff(np.mod((Pt.P[:, 1] + 0.3 * Pt.P[:, 0]) / (0.012 * H), 1.0))
        Pt.fill(under, GREY_D); Pt.bump(under * tread * 0.0015 * H)
        cuffm = m * K.sstep(0.84, 0.86, zf)
        Pt.fill(cuffm, '#d6d9e0'); Pt.bump(cuffm * 0.001 * H)
        Pt.seam(np.where(m > 0.5, zf - 0.85, 1e3) * (bz - zb), width=0.002 * H, depth=0.001 * H, dark=0.8)
        # yatay kapitone halkalar (gövde kısmı)
        q = np.mod(zf * 3.0, 1.0); body = m * (zf > 0.27) * (zf < 0.83)
        Pt.bump(body * K.puff(q) * 0.0012 * H)
        # ön kayış
        c, u = K.anchor_limb(B, 'leg', S, B.ankle_t[S] - 0.01 * H, 0.0)
        X, Y, mm = Pt.decal(c, u)
        strap = mm * m * K.inside(np.abs(Y - 0.0) - 0.011 * H, 0.0008 * H) * K.inside(np.abs(X) - 0.06 * H, 0.002 * H)
        Pt.fill(strap, ORANGE); Pt.bump(strap * 0.0014 * H)
        buckle = mm * m * K.inside(K.sd_rrect(X, Y, 0.026 * H, 0.02 * H, 0.004 * H), 0.0008 * H)
        hole = mm * m * K.inside(K.sd_rrect(X, Y, 0.014 * H, 0.009 * H, 0.002 * H), 0.0008 * H)
        Pt.fill(buckle, METAL); Pt.fill(hole, ORANGE_D); Pt.bump((buckle - hole * 0.6) * 0.0018 * H)
    # yamalar: sol göğüs gezegen arması, sağ göğüs ada güneşi
    # kol armaları (omuz yastığının altında, dış yanda): sol kolda gezegenli arma, sağ kolda ada güneşi
    c, u = K.anchor_limb(B, 'arm', 'L', B.elbow_t['L'] * 0.62, math.pi / 2)
    X, Y, mm = Pt.decal(c, u, up=_arm_up(B, 'L')); mm = mm * Pt.m_reg(1)
    R = 0.026 * H
    Pt.h = Pt.h * (1 - mm * K.inside(K.sd_circle(X, Y, R + 0.004 * H), 0.002 * H))     # arma düz dursun (kapitone altında kalmasın)
    sdo = K.sd_circle(X, Y, R)
    disk = mm * K.inside(sdo, 0.0008 * H)
    Pt.fill(disk, NAVY); Pt.bump(disk * 0.0012 * H)
    Pt.fill(mm * K.line_mask(sdo + 0.0035 * H, 0.0018 * H, 0.0006 * H), '#ffffff')
    Pt.fill(mm * K.line_mask(sdo, 0.0014 * H, 0.0005 * H), ORANGE)
    pl = mm * K.inside(K.sd_circle(X + 0.006 * H, Y + 0.004 * H, 0.011 * H), 0.0006 * H)
    Pt.fill(pl, '#ffa25c'); Pt.fill(pl * K.sstep(-0.004 * H, 0.008 * H, X + Y), '#e8763a', 0.7)
    ring = mm * K.line_mask(K.sd_ellipse(X + 0.006 * H, (Y + 0.004 * H) * 2.6 - X * 0.9, 0.019 * H, 0.019 * H), 0.0012 * H, 0.0005 * H)
    Pt.fill(ring * (1 - pl * K.sstep(0, 0.001 * H, (Y + 0.004 * H))), '#ffe08a')
    st = mm * K.inside(K.star_sdf(X - 0.014 * H, Y - 0.015 * H, 0.0075 * H), 0.0005 * H)
    Pt.fill(st, '#ffd84d')
    for (sx, sy, sr) in ((-0.018, 0.008, 0.0028), (-0.012, -0.017, 0.0022), (0.019, -0.012, 0.002)):
        Pt.fill(mm * K.inside(K.star_sdf(X - sx * H, Y - sy * H, sr * H), 0.0004 * H), '#ffffff')
    c, u = K.anchor_limb(B, 'arm', 'R', B.elbow_t['R'] * 0.62, math.pi / 2)
    X, Y, mm = Pt.decal(c, u, up=_arm_up(B, 'R')); mm = mm * Pt.m_reg(2)
    sdr = K.sd_rrect(X, Y, 0.042 * H, 0.03 * H, 0.006 * H)
    Pt.h = Pt.h * (1 - mm * K.inside(sdr - 0.004 * H, 0.002 * H))
    tag = mm * K.inside(sdr, 0.0008 * H)
    Pt.fill(tag, '#4aa3df'); Pt.bump(tag * 0.0011 * H)
    Pt.fill(tag * K.inside(K.sd_circle(X, Y + 0.012 * H, 0.011 * H), 0.0005 * H), '#ffd24d')
    for k in range(5):
        a = math.radians(30 + k * 30); rx, ry = math.cos(a), math.sin(a)
        Pt.fill(tag * K.line_mask((X * ry - (Y + 0.012 * H) * rx), 0.0011 * H, 0.0004 * H) * K.sstep(0.0135 * H, 0.015 * H, np.sqrt(X * X + (Y + 0.012 * H) ** 2)) * (Y > -0.011 * H), '#ffd24d')
    Pt.fill(tag * K.sstep(0.0, -0.002 * H, Y + 0.011 * H), '#2f7fc4')
    Pt.fill(mm * K.line_mask(sdr + 0.003 * H, 0.0008 * H, 0.0004 * H) * K.dashes(X + Y, 0.005 * H), '#ffffff', 0.9)
    Pt.seam(np.where(mm > 0.5, sdr, 1e3), width=0.0012 * H, depth=0.0006 * H, dark=0.8)
    # ek parçalar: yaşam ünitesi, ışıklar, hortum, halkalar
    pc = Pt.piece
    if 'box' in STATE:
        bx = STATE['box']
        X, Y, mm = Pt.decal(bx['c'] + bx['n'] * bx['D'] * 0.5, bx['n'], up=bx['up'], reach=bx['D'] * 0.8)
        boxm = (pc == 20).astype(np.float32)
        Pt.fill(boxm, '#eef0f4')
        panel = boxm * mm * K.inside(K.sd_rrect(X, Y, bx['W'] * 0.86, bx['Hh'] * 0.8, bx['W'] * 0.08), 0.0008 * H)
        Pt.fill(panel, '#33456a'); Pt.bump(-panel * 0.0012 * H)
        for k in range(3):
            x = (k - 1) * bx['W'] * 0.27
            bez = boxm * mm * K.line_mask(K.sd_circle(X - x, Y - bx['Hh'] * 0.13, bx['W'] * 0.115), bx['W'] * 0.02, 0.0005 * H)
            Pt.fill(bez, METAL)
        for sx in (-1, 1):
            for sy in (-1, 1):
                scr = boxm * mm * K.inside(K.sd_circle(X - sx * bx['W'] * 0.47, Y - sy * bx['Hh'] * 0.43, bx['W'] * 0.025), 0.0004 * H)
                Pt.fill(scr, '#8e96a8'); Pt.bump(scr * 0.0006 * H)
        Pt.fill(boxm * mm * K.inside(K.sd_rrect(X, Y + bx['Hh'] * 0.24, bx['W'] * 0.62, bx['Hh'] * 0.1, bx['Hh'] * 0.04), 0.0005 * H), '#1f2c45')
        for code, colr in ((22, '#5fe8ee'), (23, '#7be38f'), (24, '#ff8c6e')):
            m = (pc == code).astype(np.float32)
            Pt.fill(m, colr)
            Pt.fill(m * K.sstep(0.75, 0.98, Pt.N @ bx['n']), '#ffffff', 0.55)
        Pt.fill((pc == 26).astype(np.float32), METAL)
    hm = (pc == 25).astype(np.float32)
    Pt.fill(hm, HOSE)
    Pt.fill((pc == 26).astype(np.float32), METAL)
    Pt.wear(0.05)
