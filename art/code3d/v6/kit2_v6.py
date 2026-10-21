# v6 ek varlıklar (22 Ekim 2026, kullanıcı notları 1–12): uzun ince palmiye (halka + lif), yıpranmış kütük/kesik kütük,
# büyük kamp ateşi (katmanlı alev), deniz kıyısında eskimiş oyuk kütük, deniz yıldızı, yengeç, kar topağı, koy havuzu kayaları.
# Hepsi kodla özgün; referans görseller yalnız kalite/hava hedefi.
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector as V, noise as MN
import kit_v6 as K
from kit_v6 import srgb, mesh_obj, ramp3, _mat, _ico, _ICO_F

# ------------------------------------------------------------------ yardımcı: kesitli tüp (yarıçap fonksiyonu ile)

def lathe(name, path, rfun, res=18, mat=None, col=None, colfun=None, inward=False):
    """path: [(V)], rfun(t, a) → yarıçap. colfun(t, a, p) → renk. Uç kapakları yok."""
    pts = [V(p) for p in path]; n = len(pts); verts, faces, cols = [], [], []
    for i, p in enumerate(pts):
        t = i / (n - 1)
        tg = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ax = V((1, 0, 0)) if abs(tg.z) > 0.9 else V((0, 0, 1)); u = tg.cross(ax).normalized(); w = tg.cross(u)
        for k in range(res):
            a = k / res * math.tau; r = rfun(t, a)
            q = p + (u * math.cos(a) + w * math.sin(a)) * r; verts.append(q)
            if colfun: cols.append(colfun(t, a, q))
    for i in range(n - 1):
        for k in range(res):
            a = i * res + k; b = i * res + (k + 1) % res
            faces.append((a, a + res, b + res, b) if inward else (a, b, b + res, a + res))
    return mesh_obj(name, verts, faces, mat, colors=np.array(cols) if cols else None, col=col)

def vc_mat(name, rough=0.8, bump=0.3, bscale=30.0, stretch=None, emission=0.0):
    m, N, L, b = _mat(name)
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; L.new(vc.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if bump:
        tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = bscale; nz.inputs['Detail'].default_value = 5
        if stretch:
            mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch; L.new(tc.outputs['Object'], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs['Vector'])
        else: L.new(tc.outputs['Object'], nz.inputs['Vector'])
        bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; L.new(nz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    if emission:
        L.new(vc.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emission
    return m

def c3(h): return np.array(srgb(h))
def lerp3(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))

# ------------------------------------------------------------------ 1+3: uzun ince palmiye (çeşitli)

def palm(name, h=12.0, seed=0, col=None, rings=None, lean=None, fronds=None, leaf=None, thick=1.0):
    """İnce uzun gövde: kavisli eğim, tepeye doğru incelir; gövdede halka sırtları (sayısı çeşitli) + dikey lif çizgileri
    (köşe rengi + tümsek), tepede lifli yaprak dibi, hindistan cevizleri; 12–18 sarkan yaprak (her biri çok sayıda ince yaprakçık)."""
    R = random.Random(seed)
    rings = rings or R.randint(int(h * 3.2), int(h * 5.0)); lean = lean if lean is not None else R.uniform(0.08, 0.28)
    la = R.uniform(0, math.tau); bend = R.uniform(0.6, 1.4)
    path = []
    for i in range(80):
        t = i / 79; off = lean * h * (t ** bend)
        path.append(V((math.cos(la) * off, math.sin(la) * off, h * t - 0.3)))
    r0 = 0.19 * thick * R.uniform(0.85, 1.15) * (h / 12) ** 0.5; r1 = r0 * R.uniform(0.55, 0.7)
    def rf(t, a):
        base = r0 + (r1 - r0) * t ** 0.7 + r0 * 0.5 * max(0, 0.06 - t) * 10
        fr = (t * rings) % 1.0
        ridge = 0.06 * math.exp(-((fr - 0.15) / 0.12) ** 2)       # halka sırtı
        fib = 0.012 * MN.noise(V((math.cos(a) * 6, math.sin(a) * 6, t * 3)))
        return base * (1 + ridge + fib)
    cA, cB, cD, cF = c3('#8d7356'), c3('#b39a78'), c3('#5a4632'), c3('#c7b18e')
    def cf(t, a, q):
        fr = (t * rings) % 1.0
        ring = math.exp(-((fr - 0.12) / 0.07) ** 2)
        fib = MN.noise(V((math.cos(a) * 9, math.sin(a) * 9, t * h * 0.6))) * 0.5 + 0.5
        c = lerp3(cA, cB, fib * 0.8 + 0.1 * MN.noise(V((t * 20, a, 1))))
        c = lerp3(c, cD, ring * 0.75)
        c = lerp3(c, cF, max(0, fr - 0.7) * 1.2 * fib)
        return lerp3(c, c3('#6b5a46'), max(0, 0.15 - t) * 4)     # dipte koyu, ıslak
    tm = vc_mat(name + '_tm', rough=0.85, bump=0.6, bscale=14, stretch=(4, 4, 0.25))
    lathe(name + '_trunk', path, rf, res=16, mat=tm, col=col, colfun=cf)
    top = path[-1]; tg = (path[-1] - path[-4]).normalized()
    # lifli yaprak dibi (boot) + hindistan cevizleri
    bootm = vc_mat(name + '_bm', rough=0.9, bump=0.8, bscale=40, stretch=(2, 2, 0.3))
    bp = [top - tg * 0.6, top - tg * 0.2, top + tg * 0.25]
    lathe(name + '_boot', bp, lambda t, a: r1 * (1.5 + 0.6 * math.sin(math.pi * t)) * (1 + 0.08 * MN.noise(V((math.cos(a) * 5, math.sin(a) * 5, t * 4)))),
          res=14, mat=bootm, col=col, colfun=lambda t, a, q: lerp3(c3('#6a5236'), c3('#9b7f58'), MN.noise(V((math.cos(a) * 12, math.sin(a) * 12, t * 6))) * 0.5 + 0.5))
    cm = vc_mat(name + '_cm', rough=0.6, bump=0.2)
    ico = _ico(2); cv, cfz, cc = [], [], []
    for k in range(R.randint(3, 7)):
        a = R.uniform(0, math.tau); p = top - tg * 0.35 + V((math.cos(a), math.sin(a), 0)) * r1 * 1.6
        rr = R.uniform(0.11, 0.15); o = len(cv)
        cv += [tuple(p + V(q) * rr) for q in ico]; cfz += [tuple(f + o) for f in _ICO_F[2]]
        col_ = c3('#7a8a32') if R.random() < 0.5 else c3('#8a5a2a'); cc += [col_] * len(ico)
    mesh_obj(name + '_nuts', cv, cfz, cm, colors=np.array(cc), col=col)
    # yapraklar
    nf = fronds or R.randint(12, 18); L0 = (leaf or R.uniform(0.32, 0.45)) * h ** 0.85
    fol = K.foliage_mat(name + '_fol', translucent=0.38)
    V_, F_, C_, N_ = [], [], [], []
    for f in range(nf):
        az = f / nf * math.tau + R.uniform(-0.2, 0.2); up = R.uniform(-0.15, 0.55); Lf = L0 * R.uniform(0.75, 1.15)
        d = V((math.cos(az), math.sin(az), 0)); side = V((-d.y, d.x, 0))
        def rach(s, d=d, up=up, Lf=Lf): return top + d * (Lf * s * 0.92) + V((0, 0, Lf * (up * s - (0.55 + up) * s * s)))
        nl = 30
        for j in range(nl):
            s = 0.08 + 0.9 * j / nl; p = rach(s); tg2 = (rach(min(1, s + 0.02)) - p).normalized()
            for sg in (-1, 1):
                ll = Lf * (0.3 * math.sin(math.pi * min(1, s * 1.05)) + 0.04) * R.uniform(0.7, 1.15)
                dd = (side * sg * 0.6 + tg2 * 0.5 + V((0, 0, -0.95 - 0.4 * s))).normalized()
                w = Lf * 0.0075
                b0 = p; b1 = p + dd * ll * 0.5 + V((0, 0, -ll * 0.08)); b2 = p + dd * ll + V((0, 0, -ll * 0.25))
                nn = side.cross(tg2) if sg > 0 else tg2.cross(side); nn = (nn + V((0, 0, 0.6))).normalized()
                pp = V(dd.cross(V((0, 0, 1)))).normalized() * w
                o = len(V_)
                V_ += [b0 - pp, b0 + pp, b1 + pp * 0.9, b1 - pp * 0.9, b2]
                F_ += [(o, o + 1, o + 2, o + 3), (o + 3, o + 2, o + 4, o + 4)]
                tt = R.uniform(0, 1); C_ += [0.25 + 0.2 * tt, 0.25 + 0.2 * tt, 0.55 + 0.3 * tt, 0.55 + 0.3 * tt, 0.75 + 0.25 * tt]
                N_ += [nn] * 5
        # orta damar
        o = len(V_); rv = [rach(s) for s in np.linspace(0, 1, 10)]
        for q in rv: V_ += [q + side * 0.02, q - side * 0.02]; C_ += [0.1, 0.1]; N_ += [V((0, 0, 1))] * 2
        for q in range(9): F_ += [(o + q * 2, o + q * 2 + 1, o + q * 2 + 3, o + q * 2 + 2)]
    F_ = [f if f[2] != f[3] else (f[0], f[1], f[2]) for f in F_]
    pal = [(0.0, '#2f5a22'), (0.35, '#4f8a2e'), (0.7, '#86b843'), (1.0, '#c6dc6a')] if R.random() < 0.6 else [(0.0, '#3c5a24'), (0.4, '#6a8f34'), (0.75, '#a6b950'), (1.0, '#d9d77a')]
    return mesh_obj(name + '_fronds', [tuple(v) for v in V_], F_, fol, colors=ramp3(np.array(C_), pal), normals=[tuple(n) for n in N_], col=col)

# ------------------------------------------------------------------ 4: yıpranmış odun (kütük + kesik kütük), büyük ateş

def wood_mat(name, bark='#5e4330', bark2='#7c5c40', wood='#c4a07a', grey=False):
    """Kabuk + yer yer kalkmış kabuk (açık odun görünür) + boyuna çatlaklar; nesne z'si boyunca uzamış gürültü."""
    m, N, L, b = _mat(name)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.12, 6.0, 6.0)
    L.new(tc.outputs['Object'], mp.inputs[0])
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 2.2; n1.inputs['Detail'].default_value = 2; L.new(mp.outputs[0], n1.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 1.2; n2.inputs['Detail'].default_value = 3; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    c1 = N.new('ShaderNodeMix'); c1.data_type = 'RGBA'; c1.inputs[6].default_value = srgb(bark) + (1,); c1.inputs[7].default_value = srgb(bark2) + (1,)
    L.new(n1.outputs['Fac'], c1.inputs['Factor'])
    pe = N.new('ShaderNodeMapRange'); pe.inputs[1].default_value = 0.56; pe.inputs[2].default_value = 0.6; L.new(n2.outputs['Fac'], pe.inputs[0])
    c2 = N.new('ShaderNodeMix'); c2.data_type = 'RGBA'; c2.inputs[7].default_value = srgb(wood) + (1,); L.new(pe.outputs[0], c2.inputs['Factor']); L.new(c1.outputs[2], c2.inputs[6])
    # boyuna çatlak çizgileri
    ab = N.new('ShaderNodeMath'); ab.operation = 'SUBTRACT'; ab.inputs[1].default_value = 0.5; L.new(n1.outputs['Fac'], ab.inputs[0])
    ab2 = N.new('ShaderNodeMath'); ab2.operation = 'ABSOLUTE'; L.new(ab.outputs[0], ab2.inputs[0])
    cr = N.new('ShaderNodeMapRange'); cr.inputs[1].default_value = 0.0; cr.inputs[2].default_value = 0.03; cr.inputs[3].default_value = 0.35; cr.inputs[4].default_value = 1.0; L.new(ab2.outputs[0], cr.inputs[0])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    cmb = N.new('ShaderNodeCombineXYZ'); [L.new(cr.outputs[0], cmb.inputs[k]) for k in range(3)]
    L.new(c2.outputs[2], mul.inputs[6]); L.new(cmb.outputs[0], mul.inputs[7])
    if grey:
        hs = N.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.35; hs.inputs['Value'].default_value = 1.35
        L.new(mul.outputs[2], hs.inputs['Color']); L.new(hs.outputs['Color'], b.inputs['Base Color'])
    else: L.new(mul.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.9
    hb = N.new('ShaderNodeMath'); hb.operation = 'ADD'; L.new(cr.outputs[0], hb.inputs[0]); L.new(pe.outputs[0], hb.inputs[1])
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.7; bn.inputs['Distance'].default_value = 0.02; L.new(hb.outputs[0], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m

def ring_cap(name, center, normal, r, mat_seed=0, col=None, cracks=True, bark_w=0.08, rings=None):
    """Kesit: yaş halkaları (merkezden dışa açık-koyu), radyal çatlaklar, dışta koyu kabuk halkası; köşe rengiyle."""
    R = random.Random(mat_seed); nr, na = 14, 40
    nrm = V(normal).normalized(); ax = V((0, 0, 1)) if abs(nrm.z) < 0.9 else V((1, 0, 0)); u = nrm.cross(ax).normalized(); w = nrm.cross(u)
    rings = rings or R.randint(9, 18); verts, faces, cols = [], [], []
    crk = [R.uniform(0, math.tau) for _ in range(R.randint(2, 5))]
    for i in range(nr + 1):
        s = i / nr
        for k in range(na):
            a = k / na * math.tau; rr = r * s * (1 + 0.04 * MN.noise(V((math.cos(a) * 3, math.sin(a) * 3, mat_seed))))
            verts.append(V(center) + (u * math.cos(a) + w * math.sin(a)) * rr - nrm * 0.01 * (1 - s))
            ring = 0.5 + 0.5 * math.cos((s + 0.03 * MN.noise(V((math.cos(a) * 4, math.sin(a) * 4, 2)))) * rings * math.tau)
            c = lerp3(c3('#d9b98a'), c3('#a77d52'), ring * 0.7)
            c = lerp3(c, c3('#8a5e3a'), max(0, 0.25 - s) * 2)                  # öz koyu
            if s > 1 - bark_w: c = c3('#4a3424')
            if cracks:
                for ca in crk:
                    if abs(math.atan2(math.sin(a - ca), math.cos(a - ca))) < 0.05 * (1 - s * 0.6) and s > 0.15: c = c3('#3a2818')
            cols.append(c)
    for i in range(nr):
        for k in range(na):
            a = i * na + k; b = i * na + (k + 1) % na; faces.append((a, b, b + na, a + na))
    m = vc_mat(name + '_m', rough=0.85, bump=0.4, bscale=60)
    return mesh_obj(name, verts, faces, m, colors=np.array(cols), col=col)

def log_v2(name, length=3.0, r=0.3, seed=0, col=None, mat=None):
    """Devrik kütük: hafif eğri, düzensiz kesit, kabuk yer yer kalkmış, iki uçta yaş halkalı kesit."""
    R = random.Random(seed); mat = mat or wood_mat(name + '_w')
    path = [V((-length / 2 + length * t, R.uniform(-0.04, 0.04) * length * math.sin(math.pi * t), r * 0.95)) for t in np.linspace(0, 1, 16)]
    def rf(t, a): return r * (1 + 0.08 * MN.noise(V((math.cos(a) * 2, math.sin(a) * 2, t * 4 + seed))) - 0.06 * t + 0.1 * max(0, 0.05 - t) * 20)
    o = lathe(name, path, rf, res=20, mat=mat, col=col)
    ring_cap(name + '_c0', path[0], path[0] - path[1], rf(0, 0) * 0.98, seed, col)
    ring_cap(name + '_c1', path[-1], path[-1] - path[-2], rf(1, 0) * 0.98, seed + 1, col)
    return o

def stump_v2(name, r=0.45, h=0.55, seed=0, col=None, mat=None):
    R = random.Random(seed); mat = mat or wood_mat(name + '_w')
    def rf(t, a):
        roots = 0.5 * (1 - t) ** 3 * (0.5 + 0.5 * math.sin(a * R.choice((4, 5, 6)) + seed))
        return r * (1 + roots + 0.06 * MN.noise(V((math.cos(a) * 3, math.sin(a) * 3, t * 3 + seed))))
    path = [V((0, 0, -0.15 + (h + 0.15) * t)) for t in np.linspace(0, 1, 10)]
    lathe(name, path, rf, res=24, mat=mat, col=col)
    ring_cap(name + '_top', V((0, 0, h)), V((R.uniform(-0.08, 0.08), R.uniform(-0.08, 0.08), 1)), r * 0.97, seed, col)

def fire_mat(name):
    """Alev: dipte beyaz-sarı → ortada turuncu → uçta koyu kırmızı ve saydam; yükseklik özniteliği 'fh' + dalgalı gürültü."""
    m, N, L, b = _mat(name)
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'fh'
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.25; L.new(nz.outputs['Fac'], ad.inputs[0]); L.new(at.outputs['Fac'], ad.inputs[2])
    rp = N.new('ShaderNodeValToRGB'); cr = rp.color_ramp
    cr.elements[0].position = 0.1; cr.elements[0].color = srgb('#fff4c8') + (1,); cr.elements[1].position = 0.95; cr.elements[1].color = srgb('#8a1c08') + (1,)
    e = cr.elements.new(0.4); e.color = srgb('#ffb02e') + (1,); e = cr.elements.new(0.7); e.color = srgb('#f05a14') + (1,)
    L.new(ad.outputs[0], rp.inputs[0])
    em = N.new('ShaderNodeEmission'); L.new(rp.outputs['Color'], em.inputs['Color'])
    st = N.new('ShaderNodeMapRange'); st.inputs[1].default_value = 0.0; st.inputs[2].default_value = 1.0; st.inputs[3].default_value = 9.0; st.inputs[4].default_value = 2.5
    L.new(ad.outputs[0], st.inputs[0]); L.new(st.outputs[0], em.inputs['Strength'])
    tr = N.new('ShaderNodeBsdfTransparent'); al = N.new('ShaderNodeMapRange'); al.inputs[1].default_value = 0.55; al.inputs[2].default_value = 1.05
    L.new(ad.outputs[0], al.inputs[0])
    mx = N.new('ShaderNodeMixShader'); L.new(al.outputs[0], mx.inputs[0]); L.new(em.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], N['Material Output'].inputs['Surface'])
    return m

def campfire_v2(name, col=None, seed=0, scale=1.6):
    """Büyük kamp ateşi: iri taş halka, çapraz yanmış odunlar (kömürleşmiş, çatlaklarda kızıl kor), katmanlı dil dil alevler,
    kor parçacıkları. Işık: sıcak, geniş, yumuşak (iki küçük ışık + titreşimsiz; "fener" gibi tek nokta değil)."""
    R = random.Random(seed); S = scale
    sm = K.rock_mat(name + '_st', base='#77716f', dark='#3f3a3c', light='#9a938e', moss_amt=0.0, cracks=0.3)
    for k in range(12):
        a = k / 12 * math.tau + R.uniform(-0.1, 0.1); o = K.boulder(name + '_s%d' % k, (0.2 * S, 0.16 * S, 0.13 * S), seed + k, cuts=7, mat=sm, col=col, bevel=0.12, top_flat=0.0)
        o.location = (math.cos(a) * 0.62 * S, math.sin(a) * 0.62 * S, 0.04 * S)
    # odunlar: koyu kömür + kor çatlakları
    cm, N, L, b = _mat(name + '_char')
    tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 9; L.new(tc.outputs['Object'], vo.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs[1].default_value = 0.0; mr.inputs[2].default_value = 0.05; mr.inputs[3].default_value = 6.0; mr.inputs[4].default_value = 0.0; L.new(vo.outputs['Distance'], mr.inputs[0])
    b.inputs['Base Color'].default_value = srgb('#1d1714') + (1,); b.inputs['Emission Color'].default_value = srgb('#ff5a14') + (1,); L.new(mr.outputs[0], b.inputs['Emission Strength']); b.inputs['Roughness'].default_value = 0.95
    for k in range(6):
        a = k / 6 * math.tau + 0.3
        K.trunk_obj(name + '_w%d' % k, [([(math.cos(a) * 0.55 * S, math.sin(a) * 0.55 * S, 0.06 * S), (math.cos(a + 0.2) * 0.05 * S, math.sin(a + 0.2) * 0.05 * S, 0.5 * S)], [0.07 * S, 0.05 * S])], cm, col=col, res=8)
    # alevler: kıvrımlı, sivrilen dil şeritleri (iki yüzlü), içte kısa beyaz-sarı, dışta uzun kırmızı uçlu
    fm = fire_mat(name + '_fire'); V_, F_, H_ = [], [], []
    for k in range(44):
        a = R.uniform(0, math.tau); rr = R.uniform(0.0, 0.32) * S; hh = R.uniform(0.45, 1.35) * S * (1.25 - rr / S)
        p0 = V((math.cos(a) * rr, math.sin(a) * rr, 0.1 * S)); twist = R.uniform(-1.2, 1.2); w0 = R.uniform(0.14, 0.26) * S
        face_a = R.uniform(0, math.tau); segs = 10
        for i in range(segs + 1):
            t = i / segs; c = p0 + V((math.sin(t * 3 + k) * 0.08 * S * t, math.cos(t * 2.5 + k) * 0.08 * S * t, hh * t))
            ww = w0 * (1 - t) ** 1.3 * (0.75 + 0.25 * math.sin(math.pi * min(1, 0.3 + t)))
            fa = face_a + twist * t; sd = V((math.cos(fa), math.sin(fa), 0))
            V_ += [c - sd * ww, c + sd * ww]; H_ += [t, t]
        o = len(V_) - (segs + 1) * 2
        for i in range(segs):
            q = o + i * 2; F_ += [(q, q + 1, q + 3, q + 2)]
    me = bpy.data.meshes.new(name + '_fl'); me.from_pydata([tuple(v) for v in V_], [], F_); me.update()
    at = me.attributes.new('fh', 'FLOAT', 'POINT'); at.data.foreach_set('value', H_); me.materials.append(fm)
    fo = bpy.data.objects.new(name + '_fl', me); K.link(fo, col); fo.visible_shadow = False
    # çekirdek: alçak, geniş yarı saydam alev kütlesi (dil aralarını doldurur, yumuşak geçiş)
    ico = _ico(3); cvv = [(q[0] * 0.38 * S, q[1] * 0.38 * S, 0.1 * S + (q[2] * 0.5 + 0.5) * 0.75 * S * (1 - 0.3 * abs(q[0]))) for q in ico]
    mc = bpy.data.meshes.new(name + '_core'); mc.from_pydata(cvv, [], [tuple(f) for f in _ICO_F[3]]); mc.update()
    atc = mc.attributes.new('fh', 'FLOAT', 'POINT'); atc.data.foreach_set('value', [min(1, (q[2] * 0.5 + 0.5) * 1.1 + 0.15) for q in ico]); mc.materials.append(fm)
    mc.polygons.foreach_set('use_smooth', [True] * len(mc.polygons))
    co_ = bpy.data.objects.new(name + '_core', mc); K.link(co_, col); co_.visible_shadow = False
    # korlar
    em, N, L, b = _mat(name + '_ember'); b.inputs['Base Color'].default_value = srgb('#ff7a1a') + (1,); b.inputs['Emission Color'].default_value = srgb('#ff8a2a') + (1,); b.inputs['Emission Strength'].default_value = 12
    ico = _ico(1); cv, cf = [], []
    for k in range(40):
        p = V((R.gauss(0, 0.25), R.gauss(0, 0.25), R.uniform(0.3, 2.4))) * S; rr = R.uniform(0.004, 0.01) * S; o = len(cv)
        cv += [tuple(p + V(q) * rr) for q in ico]; cf += [tuple(f + o) for f in _ICO_F[1]]
    eo = mesh_obj(name + '_emb', cv, cf, em, col=col); eo.visible_shadow = False
    for (z, e, s_) in ((0.7, 55.0, 0.9), (1.4, 25.0, 1.2)):
        ld = bpy.data.lights.new(name + '_l', 'POINT'); ld.energy = e * S; ld.color = srgb('#ff9a42'); ld.shadow_soft_size = s_ * S
        lo = bpy.data.objects.new(name + '_l', ld); lo.location = (0, 0, z * S); K.link(lo, col)

# ------------------------------------------------------------------ 9: kıyıda eskimiş, oyuk büyük kütük

def driftwood(name, length=5.5, r=0.65, seed=0, col=None):
    """Tuzdan ağarmış, çatlamış, ufalanacak gibi yaşlı kütük: bir uçta yaş halkalı kesit, öbür uçta içi çürüyüp oyulmuş ağız
    (iç yüzey içe bakar, kendiliğinden kararır: mağara ağzı gibi derinlik). Kenarı kırık, yanında ufalanmış parçalar."""
    R = random.Random(seed); mat = wood_mat(name + '_w', bark='#8a8072', bark2='#a59886', wood='#d2c4ac', grey=True)
    inner = wood_mat(name + '_iw', bark='#5a4632', bark2='#7a5e42', wood='#9a7a55')
    path = [V((-length / 2 + length * t, 0.25 * math.sin(t * 2.2 + seed), r * 0.8)) for t in np.linspace(0, 1, 30)]
    def rf(t, a):
        return r * (1 + 0.1 * MN.noise(V((math.cos(a) * 2, math.sin(a) * 2, t * 5 + seed))) + 0.05 * math.sin(a * 7) * 0.4 - 0.12 * t) * (1 + 0.25 * max(0, 0.08 - t) * 12)
    lathe(name, path, rf, res=28, mat=mat, col=col)
    ring_cap(name + '_cap', path[0], path[0] - path[1], rf(0, 0) * 0.98, seed, col, rings=26, bark_w=0.06)
    # oyuk uç: kırık kenarlı halka + içe bakan iç yüzey (3 m derin, daralan)
    hol = path[-1]; dirv = (path[-1] - path[-2]).normalized()
    ipath = [hol - dirv * (3.0 * t) for t in np.linspace(0, 1, 14)]
    lathe(name + '_in', ipath, lambda t, a: rf(1, a) * (0.78 - 0.35 * t) * (1 + 0.06 * MN.noise(V((math.cos(a) * 3, math.sin(a) * 3, t * 4)))), res=24, mat=inner, col=col, inward=True)
    # kırık dudak (dış ile iç arası, testere dişli)
    lv, lf = [], []
    for k in range(24):
        a = k / 24 * math.tau; ro = rf(1, a); ri = rf(1, a) * 0.78; jag = R.uniform(0.0, 0.35) * r if k % 2 else 0
        tg = dirv; ax = V((0, 0, 1)); u = tg.cross(ax).normalized(); w = tg.cross(u); e = u * math.cos(a) + w * math.sin(a)
        lv += [tuple(hol + e * ro - tg * jag * 0.5), tuple(hol + e * ri - tg * jag * 0.5)]
    for k in range(24):
        a, b = k * 2, ((k + 1) % 24) * 2; lf.append((a, b, b + 1, a + 1))
    mesh_obj(name + '_lip', lv, lf, inner, col=col)
    # ufalanmış parçalar
    for k in range(9):
        p = path[R.randrange(10, 28)] + V((R.uniform(-0.3, 0.3), R.choice((-1, 1)) * R.uniform(r * 1.1, r * 2.0), -r * 0.75))
        o = K.boulder(name + '_bit%d' % k, (R.uniform(0.08, 0.25), R.uniform(0.04, 0.1), R.uniform(0.03, 0.07)), seed * 7 + k, cuts=6, mat=mat, col=col, bevel=0.1, top_flat=0.3)
        o.location = p; o.rotation_euler = (0, 0, R.uniform(0, 6.3))

# ------------------------------------------------------------------ 10: deniz yıldızı, yengeç

def starfish(name, r=0.13, seed=0, col=None):
    """Beş kollu, kollar uca incelir ve hafif kıvrılır; üstte kabarcık dizileri, kol kenarlarında ince tüp ayaklar (kıllar)."""
    R = random.Random(seed); base = R.choice(['#e8642c', '#d9483a', '#f0903a', '#c6523e'])
    m = vc_mat(name + '_m', rough=0.6, bump=0.5, bscale=120)
    V_, F_, C_ = [], [], []
    seg, rs = 12, 10
    for armi in range(5):
        a0 = armi / 5 * math.tau + R.uniform(-0.1, 0.1); curl = R.uniform(-0.4, 0.4)
        for i in range(seg + 1):
            t = i / seg; a = a0 + curl * t * t; c = V((math.cos(a) * r * t, math.sin(a) * r * t, 0.012 * (1 - t) + 0.006 * math.sin(t * 9 + armi)))
            w = r * 0.28 * (1 - t * 0.8); hgt = r * 0.16 * (1 - t * 0.75)
            d = V((math.cos(a), math.sin(a), 0)); s = V((-d.y, d.x, 0))
            for k in range(rs):
                th = k / (rs - 1) * math.pi; V_.append(tuple(c + s * math.cos(th) * w + V((0, 0, math.sin(th) * hgt))))
                C_.append(c3(base) * (0.85 + 0.25 * math.sin(th)))
        o = armi * (seg + 1) * rs
        for i in range(seg):
            for k in range(rs - 1):
                q = o + i * rs + k; F_.append((q, q + 1, q + rs + 1, q + rs))
    body = mesh_obj(name, V_, F_, m, colors=np.array(C_), col=col)
    # kabarcıklar + kenar tüp ayakları
    bm = vc_mat(name + '_b', rough=0.5); ico = _ico(1); bv, bf, bc = [], [], []
    tv, tf, tcol = [], [], []
    for armi in range(5):
        a0 = armi / 5 * math.tau
        for i in range(1, 11):
            t = i / 11; p = V((math.cos(a0) * r * t, math.sin(a0) * r * t, r * 0.16 * (1 - t * 0.75) + 0.008))
            rr = r * 0.035 * (1 - t * 0.6); o = len(bv); bv += [tuple(p + V(q) * rr) for q in ico]; bf += [tuple(f + o) for f in _ICO_F[1]]
            bc += [c3('#fbe2b8') if i % 2 else c3(base) * 1.2] * len(ico)
            for sg in (-1, 1):
                d = V((math.cos(a0), math.sin(a0), 0)); s = V((-d.y, d.x, 0)) * sg
                for q in range(3):
                    b0 = V((math.cos(a0) * r * (t + q * 0.03), math.sin(a0) * r * (t + q * 0.03), 0.004)) + s * r * 0.27 * (1 - t * 0.8)
                    b1 = b0 + s * r * 0.08 + V((0, 0, -0.002)); o = len(tv); tv += [tuple(b0), tuple(b0 + d * 0.002), tuple(b1)]; tf.append((o, o + 1, o + 2))
                    tcol += [c3('#f6c39a')] * 3
    mesh_obj(name + '_bumps', bv, bf, bm, colors=np.array(bc), col=col)
    mesh_obj(name + '_feet', tv, tf, bm, colors=np.array(tcol), col=col)
    return body

def crab(name, s=0.22, seed=0, col=None):
    """Yengeç: yassı oval kabuk (önde dişli kenar), sapa oturmuş iki göz, iki iri kıskaç, dört çift eklemli bacak."""
    R = random.Random(seed); m = vc_mat(name + '_m', rough=0.45, bump=0.3, bscale=40)
    shell = c3(R.choice(['#d9542e', '#c8452a', '#e2703a'])); belly = c3('#f2c08a')
    ico = _ico(3); V_, F_, C_ = [], [], []
    def add(pts, faces, cols):
        o = len(V_); V_.extend(pts); F_.extend([tuple(int(i) + o for i in f) for f in faces]); C_.extend(cols)
    pts = []; cols = []
    for q in ico:
        x, y, z = q; zz = z * 0.38 if z > 0 else z * 0.22
        rr = 1 + 0.08 * math.sin(math.atan2(y, x) * 10) * max(0, x)            # ön kenar dişli
        pts.append((x * s * rr, y * s * 0.78, zz * s)); cols.append(lerp3(belly, shell, (z + 0.2) * 1.6) * (0.9 + 0.2 * MN.noise(V((x * 4, y * 4, z * 4)))))
    add(pts, _ICO_F[3], cols)
    def limb(pts_, r_):
        v, f = K.tube_data(pts_, r_, 8, 0); add([tuple(p) for p in v], f, [shell * 0.95] * len(v))
    for sg in (-1, 1):
        for k in range(4):                                                           # bacaklar
            ax = -0.25 + k * 0.22; b0 = V((ax * s, sg * 0.6 * s, -0.02 * s)); kn = b0 + V((ax * 0.4 * s, sg * 0.6 * s, 0.3 * s)); tip = kn + V((ax * 0.3 * s, sg * 0.45 * s, -0.55 * s))
            limb([b0, kn, tip], [0.07 * s, 0.05 * s, 0.015 * s])
        b0 = V((0.75 * s, sg * 0.45 * s, 0)); el = b0 + V((0.35 * s, sg * 0.35 * s, 0.12 * s)); cl = el + V((0.35 * s, sg * 0.05 * s, 0.05 * s))
        limb([b0, el, cl], [0.08 * s, 0.07 * s, 0.09 * s])                         # kıskaç kolu
        pts = [(cl.x + q[0] * 0.22 * s, cl.y + q[1] * 0.14 * s, cl.z + q[2] * 0.12 * s) for q in _ico(2)]
        add(pts, _ICO_F[2], [shell * 1.08] * len(pts))
        for (dz, ln) in ((0.05, 0.3), (-0.04, 0.26)):                                # kıskaç uçları
            v0 = cl + V((0.15 * s, 0, dz * s)); limb([v0, v0 + V((ln * s, -sg * 0.05 * s, dz * 0.5 * s))], [0.05 * s, 0.012 * s])
        e0 = V((0.55 * s, sg * 0.18 * s, 0.25 * s)); limb([e0, e0 + V((0.05 * s, 0, 0.22 * s))], [0.025 * s, 0.022 * s])
        pts = [(e0.x + 0.05 * s + q[0] * 0.05 * s, e0.y + q[1] * 0.05 * s, e0.z + 0.24 * s + q[2] * 0.05 * s) for q in _ico(1)]
        add(pts, _ICO_F[1], [c3('#141414')] * len(pts))
    return mesh_obj(name, V_, F_, m, colors=np.array(C_), col=col)

# ------------------------------------------------------------------ 12: kar topağı

def snow_mat(name='snow_lump'):
    m, N, L, b = _mat(name)
    b.inputs['Base Color'].default_value = srgb('#e9eef6') + (1,); b.inputs['Roughness'].default_value = 0.55
    b.inputs['Subsurface Weight'].default_value = 0.25; b.inputs['Subsurface Radius'].default_value = (0.25, 0.35, 0.6)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 25; nz.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], nz.inputs['Vector']); bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.35; L.new(nz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m

def snow_lump(name, r=0.3, seed=0, col=None, mat=None):
    """Topak: yassı, gürültüyle şişkin, altı düz; birkaç yan yumru."""
    R = random.Random(seed); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        n = MN.noise(v.co * 1.8 + V((seed, 0, 0))) * 0.25 + MN.noise(v.co * 4 + V((0, seed, 0))) * 0.08
        v.co = V((v.co.x * (1 + n), v.co.y * (1 + n) * R.uniform(0.8, 1.1), max(-0.35, v.co.z) * 0.7 * (1 + n))) * r
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.materials.append(mat or snow_mat()); o = bpy.data.objects.new(name, me); K.link(o, col); return o

# ------------------------------------------------------------------ 7: koy havuzu (yuvarlak hazır kayalar yerine yontulmuş kaya halkası)

def swim_pool(name, col=None, seed=0, mats=None):
    """Kaya halkası (farklı boy, yontulmuş, yosunlu; diğer kayalarla aynı malzeme), ortada sığ turkuaz havuz,
    tahta atlama iskelesi, can simidi."""
    R = random.Random(seed); rmA, rmB = mats
    for k in range(16):
        a = k / 16 * math.tau + R.uniform(-0.12, 0.12); rr = 3.6 + R.uniform(-0.3, 0.5)
        sz = (R.uniform(0.6, 1.3), R.uniform(0.5, 0.9), R.uniform(0.45, 0.95))
        o = K.boulder(name + '_r%d' % k, sz, seed * 31 + k, cuts=R.randint(9, 14), mat=rmA if k % 3 else rmB, col=col)
        o.location = (math.cos(a) * rr, math.sin(a) * rr, R.uniform(-0.25, 0.05)); o.rotation_euler = (R.uniform(-0.15, 0.15), R.uniform(-0.15, 0.15), R.uniform(0, 6.3))
    wm, N, L, b = _mat(name + '_w'); b.inputs['Base Color'].default_value = srgb('#3fc6c8') + (1,); b.inputs['Roughness'].default_value = 0.08
    b.inputs['Transmission Weight'].default_value = 0.6
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=3.4, fill_type='NGON', location=(0, 0, 0.12)); p = bpy.context.object; p.data.materials.append(wm)
    for c in list(p.users_collection): c.objects.unlink(p)
    K.link(p, col)
    plank = wood_mat(name + '_pl', bark='#9a7650', bark2='#b88f62', wood='#d9b88a')
    for i in range(5):
        v, f = [], []
        x0 = 2.6 + i * 0.0; y0 = -0.6 + i * 0.3
        mesh_obj(name + '_p%d' % i, [(x0, y0, 0.45), (x0 + 2.2, y0, 0.45), (x0 + 2.2, y0 + 0.27, 0.45), (x0, y0 + 0.27, 0.45),
                                      (x0, y0, 0.38), (x0 + 2.2, y0, 0.38), (x0 + 2.2, y0 + 0.27, 0.38), (x0, y0 + 0.27, 0.38)],
                 [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], plank, col=col, smooth=False)
    rm, N, L, b = _mat(name + '_ring'); tc = N.new('ShaderNodeTexCoord'); g = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], g.inputs[0])
    at = N.new('ShaderNodeMath'); at.operation = 'ARCTAN2'; L.new(g.outputs['Y'], at.inputs[0]); L.new(g.outputs['X'], at.inputs[1])
    sn = N.new('ShaderNodeMath'); sn.operation = 'SINE'; mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 4; L.new(at.outputs[0], mu.inputs[0]); L.new(mu.outputs[0], sn.inputs[0])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = srgb('#f4f2ee') + (1,); mx.inputs[7].default_value = srgb('#e8423a') + (1,)
    gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0; L.new(sn.outputs[0], gt.inputs[0]); L.new(gt.outputs[0], mx.inputs['Factor'])
    L.new(mx.outputs[2], b.inputs['Base Color'])
    bpy.ops.mesh.primitive_torus_add(major_radius=0.45, minor_radius=0.13, location=(-0.8, 0.9, 0.18)); t = bpy.context.object; t.data.materials.append(rm)
    for c in list(t.users_collection): c.objects.unlink(t)
    K.link(t, col)
