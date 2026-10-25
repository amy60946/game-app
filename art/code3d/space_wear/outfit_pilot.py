# Roket pilotu (25 Ekim 2026, onaylı konsept 2): lacivert uçuş tulumu, kolda/bacakta/gövde yanında ayçiçeği sarısı şerit,
# cepler (iki göğüs cebi kapaklı, iki uyluk cebi, sol kolda kalemlikli cep), önde fermuar + çekeceği, camgöbeği diz ve
# dirsek yaması, yumuşak gri-mavi eldiven (cırtlı bilek bandı), arduvaz mavisi bağcıklı bot; boyunda yıldız desenli camgöbeği
# fular (düğüm + üçgen uç). Gözlük ve jetpack ayrı eşya (space_items.py). Özgün tasarım.
import math
import numpy as np
from mathutils import Vector as V
import bpy, bmesh
import space_kit as K

ID = 'outfit_pilot'
AO = 0.45
STATE = {}

NAVY = '#2a4272'; NAVY_D = '#1f3259'; TEAL = '#2b9ba5'; TEAL_D = '#217f88'; YELLOW = '#f5c23c'; YELLOW_D = '#d9a12a'
GLOVE = '#8199bb'; GLOVE_D = '#5f7899'; BOOT = '#56698d'; BOOT_D = '#36445f'; METAL = '#cdd2db'; SCARF = '#2aa9a6'


def _spots(B):
    """Cep, yama ve bant yerleri (vücut yüzeyinde merkez + yön)."""
    if B.stage in STATE.get('spots', {}): return STATE['spots'][B.stage]
    H = B.H; sp = {}
    for S, sg in (('L', 1), ('R', -1)):
        sp['chest' + S] = K.anchor_torso(B, K.torso_z(B, 0.5), sg * 0.55)
        sp['thigh' + S] = K.anchor_limb(B, 'leg', S, B.knee_t[S] * 0.5, math.pi / 2 * 0.72)
        sp['knee' + S] = K.anchor_limb(B, 'leg', S, B.knee_t[S], 0.0)
        sp['elbow' + S] = K.anchor_limb(B, 'arm', S, B.elbow_t[S], math.pi * 0.85)
    sp['sleeve'] = K.anchor_limb(B, 'arm', 'L', B.elbow_t['L'] * 0.55, math.pi / 2 * 0.8)
    STATE.setdefault('spots', {})[B.stage] = sp
    return sp


def _dims(B):
    H = B.H
    return dict(chest=(0.052 * H, 0.046 * H), thigh=(0.05 * H, 0.056 * H), knee=(0.05 * H, 0.056 * H), elbow=(0.036 * H, 0.04 * H), sleeve=(0.032 * H, 0.04 * H))


def spec(B):
    H = B.H

    def disp(B, C, piece, S):
        out = np.zeros(len(C['P']))
        if piece != 'torso': return out
        sp = _spots(B); dm = _dims(B)
        for key, (c, u) in sp.items():
            kind = key.rstrip('LR') if key != 'sleeve' else 'sleeve'
            w, h = dm[kind]
            d = C['P'] - c; z = d @ u
            up = np.array([0, 0, 1.0]); up -= u * (up @ u); up /= np.linalg.norm(up) + 1e-9; x_ = np.cross(up, u)
            X = d @ x_; Y = d @ up
            m = K.inside(K.sd_rrect(X, Y, w, h, 0.01 * H), 0.004 * H) * (np.abs(z) < 0.05 * H)
            out += m * (0.0024 if kind in ('chest', 'thigh', 'sleeve') else 0.0018) * H
        return out

    def boot_profile(B, S, zf):
        return 0.004 * K.sstep(0.16, 0.08, zf) + 0.0025 * np.exp(-((zf - 0.95) / 0.05) ** 2)

    return K.SuitSpec(off_suit=0.0095, off_glove=0.0125, off_boot=0.015, boot_k=0.34, disp=disp, boot_profile=boot_profile)


# ------------------------------------------------------------------ fular (düğüm + üçgen uç + iki küçük kuyruk)

def extras(B, ob, bvh):
    H = B.H
    zt = B.rim_at(B.spine_xy(B.hips_z)[0], -1.0) - 0.014 * H          # önde başın eteğinin hemen altı (düğüm görünsün)
    c, n = K.surf_point(B, bvh, 'torso', z=zt, a=0.0)
    n = np.array(n); n[2] = 0; n /= np.linalg.norm(n)
    up = np.array([0, 0, 1.0]); rt = np.cross(up, n)
    torso_w = np.linalg.norm(K.surf_point(B, bvh, 'torso', z=zt - 0.04 * H, a=math.pi / 2)[0] - K.surf_point(B, bvh, 'torso', z=zt - 0.04 * H, a=-math.pi / 2)[0])
    Wt = 0.44 * torso_w; Ht = 0.78 * Wt
    STATE['scarf'] = dict(c=c, n=n, up=up, rt=rt, W=Wt, Ht=Ht)
    bm = bmesh.new()
    # üçgen uç: üst kenar boyunda, uç aşağıda; göğüs yüzeyine izdüşüm + hafif kabarık
    nu, nv = 14, 12; grid = []
    for j in range(nv + 1):
        v = j / nv; row = []
        half = (1 - v) * Wt / 2 + 0.02 * Wt
        for i in range(nu + 1):
            u = (i / nu - 0.5) * 2 * half
            p = c + rt * u - up * (v * Ht) + n * 0.15 * H
            hit = bvh.ray_cast(V(p), V(-n), 0.4 * H)
            q = np.array(hit[0]) if hit[0] is not None else c + rt * u - up * v * Ht
            lift = 0.0045 * H + 0.004 * H * (1 - v) + 0.0025 * H * math.sin(math.pi * (i / nu)) * (1 - v)
            row.append(bm.verts.new(V(q + n * lift)))
        grid.append(row)
    lay = bm.faces.layers.int.new('piece')
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1])); f[lay] = 30
    sol = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    vs = [g for g in sol['geom'] if isinstance(g, bmesh.types.BMVert)]
    for v in vs: v.co -= V(n) * 0.0022 * H
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces: f[lay] = 30
    # düğüm
    kc = c + n * (0.012 * H) - up * 0.004 * H
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1)
    k = bpy.context.object; k.scale = (Wt * 0.16, Wt * 0.12, Wt * 0.11)
    from mathutils import Matrix
    M = Matrix(np.array([[*rt, 0], [*up, 0], [*n, 0], [0, 0, 0, 1]]).T.tolist()); M.translation = V(kc)
    k.matrix_world = M @ Matrix.Diagonal((Wt * 0.16, Wt * 0.12, Wt * 0.11, 1))
    K.merge_bm(bm, K.obj_to_bm(k, 31))
    # iki küçük kuyruk (düğümden yanlara)
    for sg in (1, -1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1)
        t = bpy.context.object
        Mt = Matrix(np.array([[*rt, 0], [*up, 0], [*n, 0], [0, 0, 0, 1]]).T.tolist())
        Mt.translation = V(kc + rt * sg * Wt * 0.2 - up * Wt * 0.1 + n * 0.002 * H)
        t.matrix_world = Mt @ Matrix.Rotation(sg * 0.6, 4, 'Z') @ Matrix.Diagonal((Wt * 0.07, Wt * 0.17, Wt * 0.03, 1))
        K.merge_bm(bm, K.obj_to_bm(t, 31))
    return [K.extra_object(bm, B, 30, 'pilot_scarf', labels=lambda b: {v: 0 for v in b.verts})]      # fular göğüsle tek parça


# ------------------------------------------------------------------ boya

def _pocket(Pt, key, c, u, w, h, flap=True, body_col=NAVY_D, flap_col=TEAL, button=True, pens=False, up=None):
    H = Pt.H
    X, Y, mm = Pt.decal(c, u, up=up or (0, 0, 1))
    reg = Pt.m_reg(0, 1, 2, 3, 4)
    mm = mm * reg
    sd = K.sd_rrect(X, Y, w, h, 0.006 * H)
    m = mm * K.inside(sd, 0.0008 * H)
    Pt.fill(m, body_col); Pt.bump(m * 0.0006 * H)
    Pt.seam(np.where(mm > 0.5, sd, 1e3), width=0.0014 * H, depth=0.0008 * H, dark=0.72)
    Pt.stitches(np.where(mm > 0.5, sd, 1e3), -0.0035 * H, along=X + Y, col='#c9d6ea', alpha=0.75, width=0.0007 * H, period=0.005 * H)
    if flap:
        fy = h / 2 - 0.3 * h
        sdf = np.maximum(K.sd_rrect(X, Y - (h / 2 - 0.15 * h), w * 1.04, 0.32 * h, 0.004 * H), -(Y - fy + 0.25 * h - np.abs(X) * 0.35))
        fm = mm * K.inside(sdf, 0.0008 * H)
        Pt.fill(fm, flap_col); Pt.bump(fm * 0.0016 * H)
        Pt.seam(np.where(mm > 0.5, sdf, 1e3), width=0.0014 * H, depth=0.0011 * H, dark=0.62)
        Pt.stitches(np.where(fm > 0.5, sdf, 1e3), -0.003 * H, along=X + Y, col='#d2f0f0', alpha=0.7, width=0.0007 * H, period=0.005 * H)
        if button:
            b = mm * K.inside(K.sd_circle(X, Y - (fy - 0.18 * h), 0.0055 * H), 0.0005 * H)
            Pt.fill(b, METAL); Pt.bump(b * 0.0012 * H)
            Pt.fill(b * K.inside(K.sd_circle(X - 0.0015 * H, Y - (fy - 0.18 * h) - 0.0015 * H, 0.0018 * H), 0.0005 * H), '#ffffff', 0.6)
    if pens:
        for k, colr in ((-0.35, '#f5c23c'), (0.0, '#ff7a5c'), (0.3, '#e9eef6')):
            pm = mm * K.inside(K.sd_rrect(X - k * w, Y - h / 2 - 0.01 * H, 0.004 * H, 0.022 * H, 0.002 * H), 0.0005 * H)
            Pt.fill(pm, colr); Pt.bump(pm * 0.0018 * H)


def paint(Pt):
    B = Pt.B; H = Pt.H
    Pt.fill(np.ones(Pt.n), NAVY)
    # dimi dokuma: ince çapraz çizgiler + kumaş
    tw = K.puff(np.mod((Pt.P[:, 0] + Pt.P[:, 2] + Pt.P[:, 1]) / (0.0028 * H), 1.0))
    Pt.shade(np.ones(Pt.n) * 0.08 * (1 - tw), 0.0); Pt.bump(tw * 0.00012 * H)
    Pt.fabric(amt=0.05)
    suit = Pt.m_reg(0, 1, 2, 3, 4)
    # sarı yan şerit: gövde yanı, kol dışı, bacak dışı (koyu biyeli)
    sw = 0.0085 * H
    dside = np.full(Pt.n, 1e3)
    for sg in (1, -1):
        d = (Pt.ta - sg * math.pi / 2) * Pt.tr
        dside = np.where((Pt.reg == 0) & (np.abs(d) < np.abs(dside)), d, dside)
    for S in 'LR':
        for kind in ('arm', 'leg'):
            L = Pt.lim[kind + S]; rg = (1 if S == 'L' else 2) if kind == 'arm' else (3 if S == 'L' else 4)
            d = (L['a'] - math.pi / 2) * L['r']
            dside = np.where(Pt.reg == rg, d, dside)
    st = suit * K.line_mask(dside, sw, 0.0006 * H)
    Pt.fill(st, YELLOW); Pt.bump(st * 0.0005 * H)
    Pt.fill(suit * K.line_mask(np.abs(dside) - sw - 0.0012 * H, 0.0009 * H, 0.0004 * H), '#16233f', 0.8)
    Pt.stitches(np.where(suit > 0.5, dside, 1e3), sw - 0.0022 * H, along=Pt.tz, col='#fff1c4', alpha=0.6, width=0.0006 * H, period=0.005 * H)
    Pt.stitches(np.where(suit > 0.5, dside, 1e3), -sw + 0.0022 * H, along=Pt.tz, col='#fff1c4', alpha=0.6, width=0.0006 * H, period=0.005 * H)
    # ön fermuar (metal dişler) + bel dikişi
    m0 = Pt.m_reg(0); front = np.abs(Pt.ta) < 1.0
    dz = np.where((m0 > 0.5) & front, Pt.ta * Pt.tr, 1e3)
    zip_m = K.line_mask(dz, 0.0032 * H, 0.0005 * H) * (Pt.tz > B.hips_z - 0.02 * H)
    teeth = K.puff(np.mod(Pt.tz / (0.0026 * H), 1.0))
    Pt.fill(zip_m, '#9aa3b5'); Pt.fill(zip_m * teeth, METAL); Pt.bump(zip_m * (0.0004 + 0.0004 * teeth) * H)
    Pt.seam(np.where(zip_m < 0.5, dz, 1e3) - np.sign(dz) * 0.0034 * H, width=0.0012 * H, depth=0.0006 * H, dark=0.7)
    # kemer: camgöbeği dokuma bant + metal toka (önde)
    zw = K.torso_z(B, 0.26); bw = 0.012 * H
    belt = m0 * K.line_mask(Pt.tz - zw, bw, 0.0006 * H)
    Pt.fill(belt, TEAL); Pt.bump(belt * 0.0016 * H)
    Pt.fill(belt * K.puff(np.mod(Pt.ta * Pt.tr / (0.0018 * H), 1.0)) * 0.12, '#000000')
    for e in (zw - bw, zw + bw):
        Pt.seam(np.where(m0 > 0.5, Pt.tz - e, 1e3), width=0.0014 * H, depth=0.0009 * H, dark=0.66)
    for e in (zw - bw + 0.0025 * H, zw + bw - 0.0025 * H):
        Pt.stitches(np.where(m0 > 0.5, Pt.tz - e, 1e3), 0.0, along=Pt.ta * Pt.tr, col='#d8f3f3', alpha=0.7, width=0.0006 * H, period=0.005 * H)
    c, u = K.anchor_torso(B, zw, 0.0)
    X, Y, mm = Pt.decal(c, u); mm = mm * m0
    bk = K.sd_rrect(X, Y, 0.034 * H, 0.03 * H, 0.006 * H)
    ring = mm * K.inside(bk, 0.0006 * H) * (1 - K.inside(K.sd_rrect(X, Y, 0.02 * H, 0.016 * H, 0.003 * H), 0.0006 * H))
    Pt.fill(ring, METAL); Pt.bump(ring * 0.0022 * H)
    Pt.fill(ring * K.sstep(0.0, 0.015 * H, Y - X) * 0.4, '#ffffff')
    pin = mm * K.inside(K.sd_rrect(X - 0.002 * H, Y, 0.003 * H, 0.016 * H, 0.0015 * H), 0.0004 * H)
    Pt.fill(pin, '#aab2c2'); Pt.bump(pin * 0.0018 * H)
    # bilekte camgöbeği manşet (eldivenin üstünde)
    for S in 'LR':
        L = Pt.lim['arm' + S]; tg = L['L'] * 0.66; m = Pt.m_reg(1 if S == 'L' else 2)
        cf = m * K.sstep(tg - 0.03 * H, tg - 0.028 * H, L['t'])
        Pt.fill(cf, TEAL); Pt.bump(cf * 0.0010 * H)
        Pt.seam(np.where(m > 0.5, L['t'] - (tg - 0.029 * H), 1e3), width=0.0016 * H, depth=0.0009 * H, dark=0.68)
        Pt.fill(cf * K.puff(np.mod(L['a'] * L['r'] / (0.0025 * H), 1.0)) * 0.15, '#000000')
    # cepler ve yamalar
    sp = _spots(B); dm = _dims(B)
    for S in 'LR':
        _pocket(Pt, 'chest' + S, *sp['chest' + S], *dm['chest'])
        _pocket(Pt, 'thigh' + S, *sp['thigh' + S], *dm['thigh'], body_col=NAVY_D, flap_col=NAVY_D, up=tuple(-np.array(B.legs[S].point(B.knee_t[S] * 0.5)[1])))
        for key in ('knee', 'elbow'):
            c, u = sp[key + S]; w, h = dm[key]
            upv = tuple(-np.array((B.legs if key == 'knee' else B.arms)[S].point(B.knee_t[S] if key == 'knee' else B.elbow_t[S])[1]))
            X, Y, mm = Pt.decal(c, u, up=upv); mm = mm * suit
            sd = K.sd_rrect(X, Y, w, h, 0.012 * H); m = mm * K.inside(sd, 0.0008 * H)
            Pt.fill(m, TEAL); Pt.bump(m * 0.0010 * H)
            Pt.seam(np.where(mm > 0.5, sd, 1e3), width=0.0014 * H, depth=0.0008 * H, dark=0.7)
            Pt.stitches(np.where(mm > 0.5, sd, 1e3), -0.003 * H, along=X + Y, col='#d2f0f0', alpha=0.7, width=0.0007 * H, period=0.005 * H)
            if key == 'knee':
                for k in (-1, 1):
                    q = mm * K.line_mask(Y - k * h * 0.18, 0.0011 * H, 0.0004 * H) * K.inside(sd + 0.006 * H, 0.001 * H)
                    Pt.shade(q, 0.75); Pt.bump(-q * 0.0005 * H)
    _pocket(Pt, 'sleeve', *sp['sleeve'], *dm['sleeve'], flap_col=TEAL, pens=True, up=tuple(-np.array(B.arms['L'].point(B.elbow_t['L'] * 0.55)[1])))
    # sağ kolda küçük roket arması
    c, u = K.anchor_limb(B, 'arm', 'R', B.elbow_t['R'] * 0.55, math.pi / 2 * 0.8)
    X, Y, mm = Pt.decal(c, u, up=tuple(-np.array(B.arms['R'].point(B.elbow_t['R'] * 0.55)[1]))); mm = mm * Pt.m_reg(2)
    sh = K.sd_circle(X, Y, 0.02 * H); m = mm * K.inside(sh, 0.0006 * H)
    Pt.fill(m, YELLOW); Pt.fill(mm * K.line_mask(sh, 0.0014 * H, 0.0005 * H), '#16233f'); Pt.bump(m * 0.001 * H)
    body = mm * K.inside(K.sd_ellipse(X, Y, 0.0055 * H, 0.012 * H), 0.0004 * H)
    Pt.fill(body, '#ffffff'); Pt.fill(mm * K.inside(K.sd_circle(X, Y - 0.003 * H, 0.0026 * H), 0.0004 * H), TEAL)
    for sg in (-1, 1):
        Pt.fill(mm * K.inside(K.sd_ellipse(X - sg * 0.006 * H, Y + 0.008 * H, 0.0028 * H, 0.004 * H), 0.0004 * H), '#ff6f4f')
    Pt.fill(mm * K.inside(K.sd_ellipse(X, Y + 0.015 * H, 0.003 * H, 0.004 * H), 0.0004 * H), '#ff9a3c')
    # eldiven: gri-mavi, koyu cırtlı bilek bandı, dış yanda dikiş
    for S, rg in (('L', 5), ('R', 6)):
        L = Pt.lim['arm' + S]; tg = L['L'] * 0.66; m = Pt.m_reg(rg)
        Pt.fill(m, GLOVE)
        band = m * K.sstep(tg + 0.006 * H, tg + 0.008 * H, L['t']) * (1 - K.sstep(tg + 0.024 * H, tg + 0.026 * H, L['t']))
        Pt.fill(band, GLOVE_D); Pt.bump(band * 0.0012 * H)
        Pt.fill(band * K.puff(np.mod(L['a'] * L['r'] / (0.002 * H), 1.0)) * 0.25, '#ffffff')
        for e in (tg + 0.007 * H, tg + 0.025 * H):
            Pt.seam(np.where(m > 0.5, L['t'] - e, 1e3), width=0.0016 * H, depth=0.0009 * H, dark=0.72)
        dd = np.where((m > 0.5) & (L['t'] > tg + 0.03 * H), (L['a'] - math.pi / 2) * L['r'], 1e3)
        Pt.seam(dd, width=0.0018 * H, depth=0.0009 * H, dark=0.82)
        Pt.stitches(dd, 0.0035 * H, along=L['t'], col='#c8d6ea', width=0.0007 * H, period=0.005 * H)
    # botlar: arduvaz mavisi, koyu taban, önde bağcık, burun kapağı dikişi
    for S, rg in (('L', 7), ('R', 8)):
        m = Pt.m_reg(rg); bz = K._boot_z(B, K.SuitSpec(boot_k=0.34), S); zb = B.minz
        zf = (Pt.tz - zb) / (bz - zb)
        Pt.fill(m, BOOT)
        sole = m * (1 - K.sstep(0.15, 0.17, zf)); Pt.fill(sole, BOOT_D)
        Pt.bump(sole * K.puff(np.mod(Pt.tz / (0.005 * H), 1.0)) * 0.0008 * H)
        Pt.seam(np.where(m > 0.5, (zf - 0.16) * (bz - zb), 1e3), width=0.0018 * H, depth=0.0012 * H, dark=0.7)
        cuff = m * K.sstep(0.86, 0.88, zf); Pt.fill(cuff, BOOT_D); Pt.bump(cuff * 0.0008 * H)
        c, u = K.anchor_limb(B, 'leg', S, B.ankle_t[S] - 0.005 * H, 0.0)
        X, Y, mm = Pt.decal(c, u); mm = mm * m
        lace_zone = mm * K.inside(K.sd_rrect(X, Y - 0.01 * H, 0.024 * H, 0.07 * H, 0.008 * H), 0.0006 * H)
        Pt.fill(lace_zone, '#46587a'); Pt.bump(-lace_zone * 0.0004 * H)
        for sgn in (1, -1):
            lace = lace_zone * K.line_mask(np.mod(Y + sgn * X * 0.9, 0.012 * H) - 0.006 * H, 0.0013 * H, 0.0005 * H)
            Pt.fill(lace, '#f2f4f8'); Pt.bump(lace * 0.0008 * H)
        for k in range(5):
            for sgn in (1, -1):
                ey = mm * K.inside(K.sd_circle(X - sgn * 0.012 * H, Y - (0.02 - k * 0.012) * H, 0.0018 * H), 0.0004 * H)
                Pt.fill(ey, METAL)
    # fular: camgöbeği, sarı yıldız ve nokta deseni
    pc = Pt.piece
    if 'scarf' in STATE:
        sc = STATE['scarf']
        sm = np.isin(pc, (30, 31)).astype(np.float32)
        Pt.fill(sm, SCARF)
        X, Y, mm = Pt.decal(sc['c'], sc['n'], up=sc['up'], reach=0.2 * H)
        gx = np.mod(X / (0.016 * H), 1.0) - 0.5; gy = np.mod((Y + (np.floor(X / (0.016 * H)) % 2) * 0.008 * H) / (0.016 * H), 1.0) - 0.5
        stars = sm * K.inside(K.star_sdf(gx * 0.016 * H, gy * 0.016 * H, 0.0042 * H), 0.0003 * H)
        Pt.fill(stars, '#ffd34d')
        dots = sm * K.inside(K.sd_circle(np.mod(X / (0.016 * H) + 0.5, 1.0) - 0.5, np.mod(Y / (0.016 * H) + 0.5, 1.0) - 0.5, 0.08), 0.02) * (1 - stars)
        Pt.fill(dots, '#e6fbff', 0.8)
        Pt.fill((pc == 31).astype(np.float32) * 0.25, '#1a7f7c')
        Pt.bump(sm * K.fbm(Pt.P, 30 / H, 2, 4) * 0.0012 * H)
    Pt.wear(0.05)
