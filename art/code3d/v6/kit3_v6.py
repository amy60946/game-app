# v6 Tapınak (22 Ekim 2026, kullanıcı madde 8 + örnek görsel): uzak doğu tarzı tapınak avlusu — çimenli taş teraslar ve basamaklar,
# ucu kalkık kiremit çatılı ana salon, 4 katlı pagoda, yan yapı, dalgalı kiremit başlıklı avlu duvarı, dikili taş bahçesi,
# pembe çiçekli ağaç, kırmızı fenerler. Hepsi kodla özgün (örnek yalnız hava/yerleşim hedefi).
import bpy, math, random
import numpy as np
from mathutils import Vector as V, noise as MN
import kit_v6 as K
import kit2_v6 as K2
from kit_v6 import srgb, mesh_obj, _mat

def c3(h): return np.array(srgb(h))

def vmat(name, rough=0.7, bump=0.15, bscale=25):
    return K2.vc_mat(name, rough=rough, bump=bump, bscale=bscale)

# ------------------------------------------------------------------ kutu (köşe rengi fonksiyonlu)

def box(name, x0, x1, y0, y1, z0, z1, colf, mat, col=None, seg=(1, 1, 1)):
    """Eksene hizalı kutu; colf(p, n) → renk. seg: x,y,z bölme (renk bandı için)."""
    V_, F_, C_ = [], [], []
    def quad_grid(o, du, dv, nu, nv, nrm):
        b = len(V_)
        for j in range(nv + 1):
            for i in range(nu + 1):
                p = o + du * (i / nu) + dv * (j / nv); V_.append(tuple(p)); C_.append(colf(p, nrm))
        for j in range(nv):
            for i in range(nu):
                a = b + j * (nu + 1) + i; F_.append((a, a + 1, a + nu + 2, a + nu + 1))
    sx, sy, sz = seg
    quad_grid(V((x0, y0, z0)), V((x1 - x0, 0, 0)), V((0, 0, z1 - z0)), sx, sz, V((0, -1, 0)))
    quad_grid(V((x1, y1, z0)), V((x0 - x1, 0, 0)), V((0, 0, z1 - z0)), sx, sz, V((0, 1, 0)))
    quad_grid(V((x1, y0, z0)), V((0, y1 - y0, 0)), V((0, 0, z1 - z0)), sy, sz, V((1, 0, 0)))
    quad_grid(V((x0, y1, z0)), V((0, y0 - y1, 0)), V((0, 0, z1 - z0)), sy, sz, V((-1, 0, 0)))
    quad_grid(V((x0, y0, z1)), V((x1 - x0, 0, 0)), V((0, y1 - y0, 0)), sx, sy, V((0, 0, 1)))
    o = mesh_obj(name, V_, F_, mat, colors=np.array(C_), col=col, smooth=False)
    return o

# ------------------------------------------------------------------ ucu kalkık kiremit çatı

def roof(name, cx, cy, z, w, d, h, over=0.9, curl=0.6, ridge=0.45, tile='terra', col=None, mat=None, res=56):
    """Kalçalı-beşik çatı: içbükey yamaçlar, saçak köşeleri kalkık; yamaç boyunca kiremit sıraları (köşe rengi oluk çizgileri),
    altta kalınlık + koyu saçak altı; mahya ve kalça sırtlarında yuvarlak kiremit başlıklar, uçlarında kıvrık süs."""
    W, D = w / 2 + over, d / 2 + over; rr = ridge
    pal = {'terra': ('#b9553d', '#7d3125', '#d27552'), 'grey': ('#75717a', '#4a4750', '#918d96')}[tile]
    base, groove, lite = c3(pal[0]), c3(pal[1]), c3(pal[2])
    V_, F_, C_ = [], [], []
    def surf(u, v):
        ax, ay = abs(u), abs(v)
        t = max(ay, (ax - rr) / (1 - rr) if ax > rr else 0.0)            # mahyadan saçağa 0..1
        zz = h * (1 - t) ** 1.7                                          # içbükey yamaç
        zz += curl * (max(0, ax - 0.75) / 0.25) ** 2.2 * (max(0, ay - 0.75) / 0.25) ** 2.2 * 1.0   # köşe kalkışı
        zz += curl * 0.35 * (max(ax, ay) ** 8)                              # saçak boyunca hafif kalkış
        return V((cx + u * W, cy + v * D, z + zz)), t, ax, ay
    n = res
    for j in range(n + 1):
        for i in range(n + 1):
            u = -1 + 2 * i / n; v = -1 + 2 * j / n; p, t, ax, ay = surf(u, v); V_.append(tuple(p))
            side = ay >= (ax - rr) / (1 - rr)                               # ön/arka yamaç mı
            coord = u * W if side else v * D
            g = 0.5 + 0.5 * math.cos(coord / 0.32 * math.tau)
            c = base * (0.92 + 0.12 * MN.noise(V((u * 9, v * 9, 3))))
            c = c + (groove - c) * (g ** 6) * 0.9 + (lite - c) * max(0, 1 - g * 3) * 0.0
            c = c + (lite - c) * 0.25 * (1 - t)
            C_.append(c)
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i; F_.append((a, a + 1, a + n + 2, a + n + 1))
    # kalınlık: saçak kenarından aşağı şerit + alt yüz (koyu ahşap)
    b0 = len(V_); edge = []
    for k in range(4 * n):
        s = k / n
        if s < 1: u, v = -1 + 2 * s, -1
        elif s < 2: u, v = 1, -1 + 2 * (s - 1)
        elif s < 3: u, v = 1 - 2 * (s - 2), 1
        else: u, v = -1, 1 - 2 * (s - 3)
        p, _, _, _ = surf(u, v); edge.append(p)
    for p in edge: V_.append(tuple(p)); C_.append(c3('#5a2a1e'))
    for p in edge: V_.append(tuple(p - V((0, 0, 0.28)))); C_.append(c3('#3a1c14'))
    m4 = 4 * n
    for k in range(m4):
        a = b0 + k; b = b0 + (k + 1) % m4; F_.append((a, b, b + m4, a + m4))
    ctr = len(V_); V_.append((cx, cy, z - 0.1)); C_.append(c3('#2e1812'))
    for k in range(m4): F_.append((b0 + m4 + (k + 1) % m4, b0 + m4 + k, ctr))
    o = mesh_obj(name, V_, F_, mat or vmat(name + '_m', 0.55, 0.25, 40), colors=np.array(C_), col=col)
    # sırtlar
    rm = vmat(name + '_r', 0.5, 0.1)
    rpts = [surf(u, 0)[0] + V((0, 0, 0.12)) for u in np.linspace(-rr, rr, 8)]
    K2.lathe(name + '_ridge', rpts, lambda t, a: 0.18, res=10, mat=rm, col=col, colfun=lambda t, a, q: groove * 1.1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            hp = [surf(sx * (rr + (1 - rr) * s), sy * s)[0] + V((0, 0, 0.1)) for s in np.linspace(0, 1, 12)]
            K2.lathe(name + '_hip', hp, lambda t, a: 0.13, res=8, mat=rm, col=col, colfun=lambda t, a, q: groove * 1.1)
            tip = hp[-1]; K2.lathe(name + '_curl', [tip, tip + V((sx * 0.25, sy * 0.25, 0.35)), tip + V((sx * 0.18, sy * 0.18, 0.6))], lambda t, a: 0.11 * (1 - 0.6 * t), res=8, mat=rm, col=col, colfun=lambda t, a, q: groove)
    for sx in (-1, 1):   # mahya uç süsleri
        p = surf(sx * rr, 0)[0] + V((0, 0, 0.1)); K2.lathe(name + '_orn', [p, p + V((sx * 0.1, 0, 0.5)), p + V((-sx * 0.15, 0, 0.85))], lambda t, a: 0.12 * (1 - 0.5 * t), res=8, mat=rm, col=col, colfun=lambda t, a, q: groove)
    return o

# ------------------------------------------------------------------ duvarlı yapı katı (sütun, sıva, ahşap kafes pencere)

def hall_body(name, cx, cy, z, w, d, hgt, col=None, doors=3, windows=True):
    wall_m = vmat(name + '_wm', 0.85, 0.2, 18)
    def wc(p, n):
        zz = p.z - z
        if zz < 0.55: return c3('#9b4436') * (0.9 + 0.1 * MN.noise(V((p.x * 3, p.y * 3, 1))))     # alt kırmızı taban
        if zz > hgt - 0.5: return c3('#a83a2c')                                                   # üst kırmızı kuşak
        return c3('#efe5d3') * (0.93 + 0.07 * MN.noise(V((p.x * 1.5, p.y * 1.5, zz))))          # beyaz sıva
    box(name + '_w', cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, z, z + hgt, wc, wall_m, col, seg=(int(w * 2), int(d * 2), 8))
    col_m = vmat(name + '_cm', 0.5, 0.05)
    nx = max(2, int(w / 2.2)) + 1
    for i in range(nx):
        x = cx - w / 2 - 0.25 + (w + 0.5) * i / (nx - 1)
        for y in (cy - d / 2 - 0.3, cy + d / 2 + 0.3):
            K2.lathe(name + '_col', [V((x, y, z)), V((x, y, z + hgt + 0.1))], lambda t, a: 0.2, res=10, mat=col_m, col=col, colfun=lambda t, a, q: c3('#b3342a'))
            box(name + '_cb', x - 0.3, x + 0.3, y - 0.3, y + 0.3, z - 0.05, z + 0.25, lambda p, n: c3('#b5aa98'), wall_m, col)
    # kapılar / kafes pencereler (ön yüz)
    dm = vmat(name + '_dm', 0.6, 0.15, 60)
    for i in range(doors):
        x = cx + (i - (doors - 1) / 2) * (w / max(1, doors))
        lat = lambda p, n, x=x: c3('#5c2a1f') if (int((p.x - x) * 8) % 2 == 0 or int((p.z - z) * 8) % 2 == 0) else c3('#2a120c')
        box(name + '_door', x - 0.7, x + 0.7, cy - d / 2 - 0.06, cy - d / 2 + 0.02, z + 0.55, z + hgt - 0.7, lat, dm, col, seg=(12, 1, 16))
    if windows:
        for sx in (-1, 1):
            x = cx + sx * (w / 2 - 0.9)
            lat = lambda p, n, x=x: c3('#5c2a1f') if (int((p.x - x + 5) * 10) % 2 == 0 or int((p.z + 5) * 10) % 2 == 0) else c3('#1e0e08')
            box(name + '_win', x - 0.5, x + 0.5, cy - d / 2 - 0.06, cy - d / 2 + 0.02, z + 1.6, z + 2.5, lat, dm, col, seg=(10, 1, 10))

def lanterns(name, pts, col=None):
    m, N, L, b = _mat(name + '_lm'); b.inputs['Base Color'].default_value = srgb('#e23b22') + (1,); b.inputs['Emission Color'].default_value = srgb('#ff7a3a') + (1,); b.inputs['Emission Strength'].default_value = 1.2
    b.inputs['Subsurface Weight'].default_value = 0.3
    g, N2, L2, b2 = _mat(name + '_lg'); b2.inputs['Base Color'].default_value = srgb('#e0b23a') + (1,); b2.inputs['Metallic'].default_value = 0.6
    ico = K._ico(2)
    for (x, y, z, s) in pts:
        mesh_obj(name, [(x + q[0] * 0.26 * s, y + q[1] * 0.26 * s, z + q[2] * 0.34 * s) for q in ico], K._ICO_F[2], m, col=col)
        box(name + '_cap', x - 0.14 * s, x + 0.14 * s, y - 0.14 * s, y + 0.14 * s, z + 0.3 * s, z + 0.38 * s, lambda p, n: c3('#e0b23a'), g, col)
        box(name + '_bot', x - 0.12 * s, x + 0.12 * s, y - 0.12 * s, y + 0.12 * s, z - 0.38 * s, z - 0.31 * s, lambda p, n: c3('#e0b23a'), g, col)

# ------------------------------------------------------------------ taş teras (çimenli üst, yontulmuş kaya yüz)

def terrace(name, outline, z0, z1, col=None, rock=None, seed=0):
    """outline: [(x,y)] kapalı, saat yönü tersine. Yüz: hafif içe eğik, düzensiz kaya bloklar (köşe rengi + kabartma);
    üst: çim (kenarda hafif kıvrık dudak)."""
    R = random.Random(seed); rock = rock or K.rock_mat(name + '_rk', base='#cbbda3', dark='#8c7f6c', light='#e6dcc8', moss_amt=0.15, cracks=0.6)
    pts = [V((x, y, 0)) for (x, y) in outline]; n = len(pts); rows = 6
    V_, F_ = [], []
    cen = sum(pts, V()) / n
    for r in range(rows + 1):
        t = r / rows; zz = z0 + (z1 - z0) * t
        for k, p in enumerate(pts):
            out = (p - cen); out.z = 0; out.normalize()
            jag = 0.12 * MN.noise(V((p.x * 0.8, p.y * 0.8, zz * 1.5 + seed))) + 0.06 * (r % 2)
            q = p + out * (jag - 0.18 * t); V_.append((q.x, q.y, zz))
    for r in range(rows):
        for k in range(n):
            a = r * n + k; b = r * n + (k + 1) % n; F_.append((a, b, b + n, a + n))
    wall = mesh_obj(name + '_face', V_, F_, rock, col=col)
    md = wall.modifiers.new('sub', 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = 0; md.render_levels = 2
    # üst çim (yelpaze)
    gm, N, L, b = _mat(name + '_g'); vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.0; nz.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    fz = N.new('ShaderNodeTexNoise'); fz.inputs['Scale'].default_value = 90.0; fz.inputs['Detail'].default_value = 2; L.new(tc.outputs['Object'], fz.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = srgb('#3f7f26') + (1,); mx.inputs[7].default_value = srgb('#9acd4e') + (1,)
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.6; L.new(fz.outputs['Fac'], ad.inputs[0]); L.new(nz.outputs['Fac'], ad.inputs[2])
    sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = 0.35; L.new(ad.outputs[0], sub.inputs[0]); L.new(sub.outputs[0], mx.inputs['Factor'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 0.6; L.new(mx.outputs[2], mul.inputs[6]); L.new(vc.outputs['Color'], mul.inputs[7])
    L.new(mx.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.9
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.6; bn.inputs['Distance'].default_value = 0.02; L.new(fz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    top = [(V_[rows * n + k][0], V_[rows * n + k][1], z1 + 0.02) for k in range(n)]
    lip = []
    for k, p in enumerate(pts):
        out = (p - cen); out.z = 0; out.normalize(); q = V(top[k]) + out * 0.12 + V((0, 0, -0.08)); lip.append(tuple(q))
    tv = top + lip + [(cen.x, cen.y, z1 + 0.02)]
    tf = [(k, (k + 1) % n, 2 * n) for k in range(n)] + [((k + 1) % n, k, n + k, n + (k + 1) % n) for k in range(n)]
    gc = [c3('#5fa13a') * (0.9 + 0.2 * R.random()) for _ in range(n)] + [c3('#3f7a2a')] * n + [c3('#6cae40')]
    mesh_obj(name + '_top', tv, tf, gm, colors=np.array(gc), col=col)

def steps(name, x, y, z0, z1, width, depth=0.45, col=None, rock=None):
    """Yontulmuş taş basamaklar: her basamak hafif düzensiz kutu (köşe rengi taş tonu), üst kenarı açık, arası koyu derz."""
    n = max(2, int(round((z1 - z0) / 0.28))); dz = (z1 - z0) / n; R = random.Random(int(x * 10 + y))
    m = vmat(name + '_m', 0.85, 0.5, 14)
    for i in range(n):
        yy0 = y - depth * (n - i); w2 = width / 2 * R.uniform(0.96, 1.04)
        def cf(p, nrm, zt=z0 + dz * (i + 1)):
            c = c3('#c8bba3') * (0.85 + 0.2 * MN.noise(V((p.x * 1.3, p.y * 1.3, p.z * 2))))
            if nrm.z > 0.5: c = c * 1.12
            if abs(p.z - zt) < 0.03 and nrm.z < 0.5: c = c * 1.2
            return c
        box(name + '_%d' % i, x - w2, x + w2, yy0, y + 0.2, z0 + dz * i - 0.05, z0 + dz * (i + 1), cf, m, col, seg=(int(width * 2), 2, 1))

def rounded_rect(cx, cy, w, d, r=1.2, n=10, noise=0.25, seed=0):
    pts = []
    for (qx, qy, a0) in ((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)):
        ccx, ccy = cx + qx * (w / 2 - r), cy + qy * (d / 2 - r)
        for k in range(n):
            a = math.radians(a0 + 90 * k / (n - 1)); rr = r + noise * MN.noise(V((math.cos(a) * 3 + qx, math.sin(a) * 3 + qy, seed)))
            pts.append((ccx + math.cos(a) * rr, ccy + math.sin(a) * rr))
    return pts

# ------------------------------------------------------------------ duvar (dalgalı kiremit başlıklı)

def court_wall(name, path, hgt=2.4, col=None):
    wm = vmat(name + '_m', 0.85, 0.3, 30)
    for (a, b) in zip(path[:-1], path[1:]):
        a, b = V(a + (0,)), V(b + (0,)); L = (b - a).length; dvec = (b - a).normalized(); sd = V((-dvec.y, dvec.x, 0)) * 0.3
        nseg = max(2, int(L * 3)); V_, F_, C_ = [], [], []
        for i in range(nseg + 1):
            p = a + dvec * (L * i / nseg)
            top = hgt + 0.18 * math.sin(L * i / nseg / 2.2 * math.tau)          # dalgalı başlık
            for (s, zz) in ((-1, 0), (-1, top), (1, top), (1, 0)):
                q = p + sd * s; V_.append((q.x, q.y, zz))
                C_.append(c3('#a8473a') if zz > hgt - 0.6 else (c3('#c9b48e') * (0.88 + 0.12 * MN.noise(V((q.x * 2, q.y * 2, zz * 4))))))
        for i in range(nseg):
            for k in range(3):
                a_ = i * 4 + k; F_.append((a_, a_ + 1, a_ + 5, a_ + 4))
        mesh_obj(name, V_, F_, wm, colors=np.array(C_), col=col)
        # kiremit başlık (koyu, iki yana taşan)
        cv, cf, cc = [], [], []
        for i in range(nseg + 1):
            p = a + dvec * (L * i / nseg); top = hgt + 0.18 * math.sin(L * i / nseg / 2.2 * math.tau)
            for (s, zz) in ((-1.9, -0.12), (0, 0.22), (1.9, -0.12)):
                q = p + sd * s; cv.append((q.x, q.y, top + zz)); cc.append(c3('#7d3125'))
        for i in range(nseg):
            for k in range(2):
                a_ = i * 3 + k; cf.append((a_, a_ + 1, a_ + 4, a_ + 3))
        mesh_obj(name + '_cap', cv, cf, wm, colors=np.array(cc), col=col)

# ------------------------------------------------------------------ tapınak avlusu

PAL_BLOSSOM = [(0.0, '#7a1f4f'), (0.35, '#b52f7a'), (0.65, '#dc4d9c'), (0.9, '#f07ec0'), (1.0, '#ffb3dc')]

def temple(col=None, seed=0):
    """Yerel koordinat: ön = −y (güney). Taban z = 0 (plato). Teraslar: alt 0→1.0, üst 1.0→2.1."""
    R = random.Random(seed)
    rock = K.rock_mat('tmp_rock', base='#cdbfa5', dark='#8b7e6b', light='#e8decb', moss_amt=0.12, cracks=0.6)
    terrace('tmp_t1', rounded_rect(0, 1.0, 30, 22, 2.0, seed=1), -0.3, 1.0, col, rock, 1)
    terrace('tmp_t2', rounded_rect(0, 4.5, 21, 13, 1.5, seed=2), 1.0, 2.1, col, rock, 2)
    terrace('tmp_t0', rounded_rect(-9, -8.5, 7, 3.5, 1.0, seed=3), -0.3, 0.45, col, rock, 3)          # önde küçük basamak sekisi
    steps('tmp_s1', 0, -10.0, -0.25, 1.0, 5.0, col=col, rock=rock)
    steps('tmp_s2', 0, -2.0, 1.0, 2.1, 4.0, col=col, rock=rock)
    steps('tmp_s3', -12.5, -10.0, -0.25, 1.0, 3.0, col=col, rock=rock)
    # ana salon (üst terasta)
    hall_body('tmp_hall', 0, 6.5, 2.1, 11, 6.5, 4.2, col, doors=3)
    roof('tmp_hall_roof', 0, 6.5, 2.1 + 4.2, 11, 6.5, 2.8, over=1.4, curl=0.9, ridge=0.5, tile='grey', col=col)
    lanterns('tmp_lan', [(x, 6.5 - 3.25 - 1.0, 2.1 + 3.6, 1.0) for x in (-4.5, -1.5, 1.5, 4.5)], col)
    # pagoda (sol arka, alt terasta)
    px, py = -10.5, 6.0; z = 1.0; s = 6.0
    for i in range(4):
        hh = 3.3 if i == 0 else 2.3
        hall_body('tmp_pg%d' % i, px, py, z, s, s, hh, col, doors=1 if i == 0 else 0, windows=(i == 0))
        roof('tmp_pg_roof%d' % i, px, py, z + hh, s, s, 1.2 + 0.2 * (i == 3), over=1.15 - 0.1 * i, curl=0.7, ridge=0.02, tile='terra', col=col)
        z += hh + 0.6; s *= 0.8
    gm, N, L, b = _mat('tmp_gold'); b.inputs['Base Color'].default_value = srgb('#e0b23a') + (1,); b.inputs['Metallic'].default_value = 0.7; b.inputs['Roughness'].default_value = 0.35
    K2.lathe('tmp_finial', [V((px, py, z + 0.2)), V((px, py, z + 2.4))], lambda t, a: 0.12 * (1 - 0.8 * t) + 0.08 * (math.sin(t * 18) > 0.6), res=10, mat=gm, col=col)
    # yan yapı (sağ, alt terasta) + küçük köşk
    hall_body('tmp_side', 11.5, 4.5, 1.0, 6.0, 5.0, 3.4, col, doors=1)
    roof('tmp_side_roof', 11.5, 4.5, 4.4, 6.0, 5.0, 1.9, over=1.0, curl=0.6, ridge=0.35, tile='terra', col=col)
    # avlu duvarı (arka ve yanlar)
    court_wall('tmp_wall', [(-14.5, -6), (-14.5, 11.5), (14.5, 11.5), (14.5, -6)], 2.6, col)
    # dikili taş bahçesi (sol önde) + iri taşlar
    rk2 = K.rock_mat('tmp_rock2', base='#c9c3b6', dark='#8a8478', light='#e4ded2', moss_amt=0.3, cracks=0.5)
    for k, (x, y, sx, sy, sz) in enumerate(((-6.5, -3.0, 0.9, 0.8, 1.9), (-5.4, -3.6, 0.6, 0.5, 1.2), (-7.4, -4.0, 0.5, 0.5, 0.8), (6.5, -4.5, 0.8, 0.7, 1.0), (3.5, 9.6, 0.9, 0.8, 1.7))):
        o = K.boulder('tmp_st%d' % k, (sx, sy, sz), 600 + k, cuts=12, mat=rk2, col=col, top_flat=0.1); o.location = (x, y, (1.0 if y > -5 else 0.0) + sz * 0.85)
    # ağaçlar: arkada pembe çiçekli, önde yeşil yuvarlaklar + çalı
    fol = K.foliage_mat('tmp_fol'); bark = K.bark_mat('tmp_bark')
    pinkc = bpy.data.collections.new('C_tmp_pink'); K.round_tree('tmp_pink', 9.0, 77, col=pinkc, palette=PAL_BLOSSOM, spread=1.2, fol=K.foliage_mat('tmp_fol_p', translucent=0.35), bark=bark, clumps=13)
    greens = []
    for k in range(3):
        c = bpy.data.collections.new('C_tmp_g%d' % k); K.round_tree('tmp_g%d' % k, 7.0 + k, 80 + k, col=c, palette=(K.PAL_BROAD, K.PAL_BROAD3, K.PAL_BROAD2)[k], spread=1.1, fol=fol, bark=bark); greens.append(c)
    bushc = bpy.data.collections.new('C_tmp_bush'); K.bush('tmp_bush', 1.3, 90, col=bushc, fol=fol, leaf=0.09)
    trees = [(pinkc, -5.0, 12.8, 1.0, 1.25), (greens[0], -16.5, 2.0, 0.0, 1.0), (greens[1], 16.5, -1.0, 0.0, 0.9), (greens[2], 8.0, 13.0, 1.0, 1.0),
             (greens[0], -7.0, 13.5, 1.0, 0.85), (bushc, -3.5, -8.0, 0.0, 1.0), (bushc, 4.5, -8.5, 0.0, 0.8)]
    return trees

def place_temple(L, inst_fn, cx, cz, yaw=0.0):
    col = bpy.data.collections.new('C_temple'); trees = temple(col)
    y0 = L.height(cx, cz)
    inst_fn(col, cx, cz, y0, yaw, 1.0)
    for (c, x, y, z, s) in trees:
        ca, sa = math.cos(yaw), math.sin(yaw); wx, wz = cx + x * ca - y * sa, cz + x * sa + y * ca
        inst_fn(c, wx, wz, y0 + z - 0.1, random.uniform(0, 6.3), s)
