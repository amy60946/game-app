# Piramit Koşusu — uzak arka plan (25 Ekim 2026): kamera bunları küçük görür → iri biçim, okunur renk; ayrıntı normal haritasında.
#   rn_pyramid  ~60 × 60 taban, ~40 m: basamaklı, aşınmış kireçtaşı; basamaklarda kum, dipte kum eteği ve dökülmüş bloklar, altın tepe
#   rn_obelisk  ~7 m: iki basamaklı kaide, eğimli gövde, dört yüzde simge sütunu, altın piramitçik
#   rn_palm     ~6 m hurma: elmas desenli gövde, 16 taraklı yaprak (yaprakçık başına üçgen, iki yüzlü), hurma salkımları
#   rn_dune     ~30 × 20 kum tepesi: rüzgâr yönünde yumuşak, arkada dik; kenarı zemine (z = 0) iner, dalgacıklar normalde
#   rn_sphinx   ~6 m sevimli sfenks: yatan aslan gövdesi, yuvarlak dost yüz, mavi-altın çizgili başlık, göğüste renkli gerdanlık; önü −Y
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep
import kit
from kit import blob, tube, cyl
import kosu_engeller as KE


def m_blocks(name, pal=EK.LIMESTONE, row=0.66, length=1.3, dust=0.75, streak=0.35, seed=0.0):
    """Taş blok örgüsü (dik yüzlerde): dünya normaline göre yatay koordinat seçilir (x ya da y), Tuğla dokusuyla derz + blok tonu;
    yukarı bakan yüzde kalın kum tozu, dikey koyu yağmur/akıntı izleri."""
    def b(nt, bsdf):
        G = EK.EG(nt)
        col = EK.stone_col(G, pal, None, bands=0.3, pits=0.5, wear=0.5, cav=0.3, dust=dust, grime=0.25, seed=seed)
        x, y, z = G.sep(G.pos()); nx, ny, nz = G.sep(G.nrm())
        u = G.math('ADD', G.math('MULTIPLY', x, G.math('ABSOLUTE', ny)), G.math('MULTIPLY', y, G.math('ABSOLUTE', nx)))
        br = G.n.new('ShaderNodeTexBrick'); br.offset = 0.5; br.squash_frequency = 2
        br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.035; br.inputs['Mortar Smooth'].default_value = 0.3
        br.inputs['Brick Width'].default_value = length; br.inputs['Row Height'].default_value = row; br.inputs['Bias'].default_value = 0.0
        br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (0.86, 0.86, 0.86, 1); br.inputs['Mortar'].default_value = (0, 0, 0, 1)
        G.l.new(G.comb(u, z, 0.0), br.inputs['Vector'])
        side = G.rng(G.math('ABSOLUTE', nz), 0.6, 0.4)
        tone = G.mix(G.math('SUBTRACT', 1.0, side), br.outputs['Color'], '#ffffff')
        col = G.mix(G.math('MULTIPLY', side, 0.55), col, G.mul(col, tone))
        mort = G.math('MULTIPLY', G.rng(br.outputs['Fac'], 0.5, 0.0), side)
        col = G.mix(G.math('MULTIPLY', mort, 0.5), col, EK._shade(pal[0], 0.7))
        st = G.noise(G.mapping(G.pos(), (3.0, 3.0, 0.12)), 2.0, 3)
        col = G.mix(G.math('MULTIPLY', G.rng(st, 0.55, 0.7, 0, streak), side), col, EK._shade(pal[0], 0.82))
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.5; bb.inputs['Distance'].default_value = 0.05
        G.l.new(G.math('MULTIPLY', br.outputs['Fac'], side), bb.inputs['Height']); G.l.new(bb.outputs['Normal'], bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def low_box(name, cx, cy, z0, w, d, h, bev=0.0, taper=1.0, drop_bottom=True):
    """Elle hedef kutu (alt yüz yok), isteğe bağlı pah ve üstte daralma."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        t = v.co.z + 0.5; k = 1 - (1 - taper) * t
        v.co.x *= w * k; v.co.y *= d * k; v.co.z = z0 + t * h
        v.co.x += cx; v.co.y += cy
    if bev:
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=bev, segments=1, affect='EDGES', profile=0.5)
    if drop_bottom:
        bm.normal_update()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.9 and f.calc_center_median().z < z0 + 1e-4], context='FACES')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


# ================================================================== rn_pyramid

def build_pyramid():
    N, H = 14, 2.64
    MB = m_blocks('pyrblocks'); GD = EK.m_gold('pyrgold')
    hi = []; lo = []
    R = random.Random(3)
    for i in range(N):
        hw = 30.0 - i * (30.0 - 3.6) / 13.5; z0 = i * H
        b = EK.rounded_box('course', (2 * hw, 2 * hw, H + 0.1), 0.45, max(0.9, 2 * hw / 45), [MB], loc=(0, 0, z0 + H / 2 - 0.05),
                           chips=0.7, lump=0.12, seed=100 + i)
        hi.append(b)
        lo.append(EK.tag_uvw(low_box('course_lo', 0, 0, z0 - 0.05, 2 * hw, 2 * hw, H + 0.1, bev=0.32), 1.0))
    zc = N * H - 0.05
    verts = [(-3.3, -3.3, zc), (3.3, -3.3, zc), (3.3, 3.3, zc), (-3.3, 3.3, zc), (0, 0, zc + 3.6)]
    cap = EK.mesh_obj('cap', verts, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], [GD], smooth=False)
    hi.append(cap)
    lo.append(EK.tag_uvw(EK.mesh_obj('cap_lo', verts, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], [], smooth=False), 1.5))
    # dipte kum eteği + dökülmüş bloklar
    SD = EK.m_sand('pyrsand')
    hi.append(KE.sand_rect('psand', 0, 0, 60.0, 60.0, 2.5, 7.0, SD, 7, seg_len=1.5, rows=6, r=0.6))
    ls = KE.sand_rect('psand_lo', 0, 0, 60.0, 60.0, 2.5, 7.0, SD, 7, seg_len=7.5, rows=3, r=0.6); ls.data.materials.clear(); lo.append(EK.tag_uvw(ls, 0.25))
    for k in range(7):
        a = R.uniform(0, TAU); r = R.uniform(31, 34); s = R.uniform(1.4, 2.4)
        o = EK.rounded_box('rubble', (s * 1.3, s, s * 0.8), s * 0.15, s / 5, [MB], loc=(math.cos(a) * r, math.sin(a) * r, s * 0.3),
                           rot=(R.uniform(-15, 15), R.uniform(-15, 15), R.uniform(0, 90)), chips=s * 0.12, lump=s * 0.03, seed=200 + k)
        hi.append(o)
        lo += [EK.tag_uvw(q, 0.3) for q in EK.BK.build_low([o], [(r'rubble', 0.012)])]
    return hi, lo, dict(cull=True, tex=1024, ao_dist=2.5, ao_strength=0.6, cage=0.6, ray=1.6)


# ================================================================== rn_obelisk

def build_obelisk():
    def draw(cv):
        W, Hh = cv.wm, cv.H / cv.ppm
        seq = ['sun', 'duck', 'eye', 'lotus', 'star', 'scarab', 'feather', 'cat', 'fish']
        n = len(seq); step = (Hh - 0.1) / n
        for k, g in enumerate(seq):
            w = W - 0.12 if g != 'feather' else 0.2
            EK.GLYPHS[g](EK.Pen(cv, (W - w) / 2, Hh - 0.05 - (k + 1) * step + 0.03, w, step - 0.06))
        cv.line([(0.03, 0.03), (0.03, Hh - 0.03)], 0.02, col=EK.C(EK.LAPIS)); cv.line([(W - 0.03, 0.03), (W - 0.03, Hh - 0.03)], 0.02, col=EK.C(EK.LAPIS))
    d = KE.relief('obel', 0.5, 4.6, draw, ppm=160, depth=0.015, seed=21)
    ST = EK.m_stone('obst', EK.LIMESTONE, dec=d, bands=0.3, seed=2.0)
    sh = EK.rounded_box('shaft', (0.95, 0.95, 5.7), 0.03, 0.06, [ST], loc=(0, 0, 0.5 + 2.85), chips=0.03, lump=0.004, seed=31)
    for v in sh.data.vertices:
        t = (v.co.z + 2.85) / 5.7; k = 1 - 0.34 * t; v.co.x *= k; v.co.y *= k
    bpy.context.view_layer.update()
    side_dec(sh, 0.5, 1.0, 5.6)
    GD = EK.m_gold('obgold')
    zt = 6.2; a = 0.95 * 0.66 / 2 + 0.005
    verts = [(-a, -a, zt), (a, -a, zt), (a, a, zt), (-a, a, zt), (0, 0, zt + 0.65)]
    cap = EK.mesh_obj('obcap', verts, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], [GD], smooth=False)
    PL = EK.m_stone('obplinth', EK.SANDSTONE, seed=3.0)
    p1 = EK.rounded_box('plinth', (1.65, 1.65, 0.3), 0.04, 0.05, [PL], loc=(0, 0, 0.15), chips=0.04, lump=0.004, seed=32)
    p2 = EK.rounded_box('plinth', (1.28, 1.28, 0.22), 0.035, 0.05, [PL], loc=(0, 0, 0.3 + 0.11 - 0.005), chips=0.035, lump=0.004, seed=33)
    SD = EK.m_sand('obsand')
    sk = KE.sand_rect('obsand', 0, 0, 1.65, 1.65, 0.13, 0.35, SD, 34, seg_len=0.2, rows=3, r=0.04)
    hi = [sh, cap, p1, p2, sk]
    decim = [(r'^shaft$', 0.003), (r'^plinth$', 0.01), (r'^obsand$', 0.4)]
    weights = [(r'^shaft$', 1.3), (r'^obcap$', 1.0), (r'^plinth$', 0.6), (r'sand', 0.3)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=600, ao_dist=0.4)


def side_dec(o, w, z0, z1):
    """Dört yan yüze aynı panel: her yüzde u yüzün yatayı (dışarıdan bakınca sağa), v = (z − z0)/(z1 − z0); üst/alt yüzler dışarıda."""
    me = o.data; mw = o.matrix_world; m3 = mw.to_3x3()
    uvl = me.uv_layers.get('dec') or me.uv_layers.new(name='dec')
    for poly in me.polygons:
        n = (m3 @ poly.normal).normalized()
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) > 0.7: uvl.data[li].uv = (-5, -5); continue
            if abs(n.x) > abs(n.y): h = -p.y if n.x < 0 else p.y
            else: h = p.x if n.y < 0 else -p.x
            uvl.data[li].uv = (0.5 + h / w, (p.z - z0) / (z1 - z0))


# ================================================================== rn_palm

def m_frond(name='frond'):
    """Hurma yaprağı: yaprakçık kökü koyu zeytin yeşili, uca doğru açık sarımsı yeşil (köşe niteliği 'lt'), orta damar açık, yer yer
    kuru uç; tozlu (çöl)."""
    def b(nt, bsdf):
        G = EK.EG(nt)
        at = G.n.new('ShaderNodeAttribute'); at.attribute_name = 'lt'; at.attribute_type = 'GEOMETRY'
        t = at.outputs['Fac']; cw = G.coords()
        col = G.mix(G.rng(t, 0.0, 1.0), '#3f6e2c', '#8fb04a')
        col = G.mix(G.rng(G.noise4(cw, 1.2, 3), 0.4, 0.7, 0, 0.35), col, '#6c8f3a')
        col = G.mix(G.math('MULTIPLY', G.rng(t, 0.85, 1.0), G.rng(G.noise4(cw, 2.5, 3), 0.55, 0.65, 0, 0.6)), col, '#c9a25a')
        col = G.mix(G.rng(t, 0.06, 0.0, 0, 0.7), col, '#c8c27a')
        col = G.mix(G.rng(G.ao(0.4), 0.85, 0.3, 0, 0.45), col, '#2a3d1c')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def m_trunk(name='palmtrunk'):
    def b(nt, bsdf):
        G = EK.EG(nt); x, y, z = G.sep(G.obj())
        ang = G.math('ARCTAN2', y, x)
        a1 = G.math('SINE', G.math('ADD', G.math('MULTIPLY', ang, 7.0), G.math('MULTIPLY', z, 9.0)))
        a2 = G.math('SINE', G.math('SUBTRACT', G.math('MULTIPLY', ang, 7.0), G.math('MULTIPLY', z, 9.0)))
        dia = G.math('MULTIPLY', G.math('ABSOLUTE', a1), G.math('ABSOLUTE', a2))
        col = G.mix(G.rng(dia, 0.05, 0.5), '#5a3d24', '#a07a4c')
        col = G.mix(G.rng(G.noise(G.obj(), 6.0, 3), 0.4, 0.7, 0, 0.3), col, '#c9a678')
        col = G.mix(G.rng(G.ao(0.08), 0.85, 0.35, 0, 0.5), col, '#3a2614')
        col = G.mix(G.rng(z, 0.5, 0.0, 0, 0.4), col, EK.SAND[1])
        G.l.new(col, bsdf.inputs['Base Color'])
        bb = G.n.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.6; bb.inputs['Distance'].default_value = 0.03
        G.l.new(dia, bb.inputs['Height']); G.l.new(bb.outputs['Normal'], bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def build_palm():
    R = random.Random(9)
    TOP = V((0.32, 0.05, 5.15))
    def tpath(t): return V((0.32 * t ** 1.6, 0.05 * t, 5.15 * t))
    # gövde (taslak: elmas yumruları geometride; hedef: 8 kenar)
    th = np.linspace(0, TAU, 49); ts = np.linspace(0, 1, 90)
    TH, T = np.meshgrid(th, ts)
    r0 = 0.2 - 0.04 * T + 0.1 * np.exp(-T / 0.03)
    knob = 0.018 * np.abs(np.sin(7 * TH + 9 * T * 5.15)) * np.abs(np.sin(7 * TH - 9 * T * 5.15))
    RR = r0 + knob
    C = np.array([tuple(tpath(t)) for t in ts])
    P = np.stack([C[:, 0:1] + RR * np.cos(TH), C[:, 1:2] + RR * np.sin(TH), np.repeat(C[:, 2:3], len(th), 1)], -1)
    TR = m_trunk()
    trunk = EK.grid_obj('trunk', P, None, [TR]); EK.weld(trunk)
    thl = np.linspace(0, TAU, 9); tl = np.array([0, 0.02, 0.06, 0.2, 0.45, 0.7, 0.9, 1.0])
    THL, TL = np.meshgrid(thl, tl); RL = 0.2 - 0.04 * TL + 0.1 * np.exp(-TL / 0.03) + 0.008
    CL = np.array([tuple(tpath(t)) for t in tl])
    PL = np.stack([CL[:, 0:1] + RL * np.cos(THL), CL[:, 1:2] + RL * np.sin(THL), np.repeat(CL[:, 2:3], 9, 1)], -1)
    trunk_lo = EK.grid_obj('trunk_lo', PL, None, []); EK.weld(trunk_lo)
    hi = [trunk]; lo = [EK.tag_uvw(trunk_lo, 1.0)]
    # taç topağı + eski yaprak sapları
    crown = blob('crown', tuple(TOP + V((0, 0, 0.05))), (0.3, 0.3, 0.26), EK.m_flatc('crownfib', '#6b5232', 0.2, 0.5))
    hi.append(crown); lo += [EK.tag_uvw(q, 0.8) for q in EK.BK.build_low([crown], [(r'crown', 0.06)])]
    # yapraklar: tarak (orta damar + iki yan yaprakçık ucu), V kıvrım; hedef = taslak (iki yüzlü)
    FR = m_frond()
    NF = 16
    for k in range(NF):
        az = k / NF * TAU + R.uniform(-0.12, 0.12)
        tier = k % 3
        elev = (0.75, 0.25, -0.2)[tier] + R.uniform(-0.12, 0.12)
        Lf = R.uniform(2.3, 2.8) * (0.85 if tier == 0 else 1.0)
        d = V((math.cos(az) * math.cos(elev), math.sin(az) * math.cos(elev), math.sin(elev)))
        side = V((-math.sin(az), math.cos(az), 0.0))
        S = 15; verts = []; faces = []; lt = []
        spine = []
        for j in range(S + 1):
            t = j / S
            p = TOP + d * (Lf * t) + V((0, 0, -0.55 * Lf * t * t * (1.2 if tier == 2 else 1.0)))
            spine.append(p)
        for j in range(S + 1):
            t = j / S; p = spine[j]
            tg = (spine[min(S, j + 1)] - spine[max(0, j - 1)]).normalized()
            sd = (side - tg * side.dot(tg)).normalized(); up = tg.cross(sd).normalized()
            wl = 0.42 * math.sin(min(1.0, t * 1.25) * math.pi * 0.92) * (0.25 if t < 0.08 else 1.0)
            verts.append(tuple(p)); lt.append(0.0)
            for s in (-1, 1):
                tip = p + tg * (0.16 * wl / 0.42) + sd * (s * wl) + up * (0.12 * wl)
                verts.append(tuple(tip)); lt.append(1.0)
        for j in range(S):
            a, l1, r1 = 3 * j, 3 * j + 1, 3 * j + 2; b2 = 3 * (j + 1)
            faces.append((a, b2, l1)); faces.append((a, r1, b2))
        o = EK.mesh_obj('frond', verts, faces, [FR], smooth=True)
        at = o.data.attributes.new('lt', 'FLOAT', 'POINT'); at.data.foreach_set('value', lt)
        o.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(o.data.polygons))
        hi.append(o)
        c = EK.mesh_obj('frond_lo', verts, faces, [], smooth=True)
        c.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(c.data.polygons))
        lo.append(EK.tag_uvw(c, 1.0))
    # hurma salkımları
    DT = EK.m_clay('dates', '#d9792f')
    for k in range(3):
        az = k / 3 * TAU + 0.5
        cpos = TOP + V((math.cos(az) * 0.28, math.sin(az) * 0.28, -0.35))
        st = tube('stalk', [tuple(TOP + V((math.cos(az) * 0.15, math.sin(az) * 0.15, -0.05))), tuple(cpos + V((0, 0, 0.12)))], [0.03, 0.025], EK.m_flatc('stalk', '#c99a3a'), res=3)
        hi.append(st)
        bm = bmesh.new()
        for q in range(14):
            off = V((R.uniform(-0.12, 0.12), R.uniform(-0.12, 0.12), R.uniform(-0.22, 0.05)))
            res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.055)
            for v in res['verts']: v.co = v.co * V((1, 1, 1.35)) + cpos + off
        cl = EK.A.link_mesh('dates', bm, [DT]); EK.A.smooth(cl); hi.append(cl)
    kit.to_mesh_all()
    lo += [EK.tag_uvw(q, 0.6) for q in EK.BK.build_low([o for o in hi if o.name.startswith(('dates', 'stalk'))], [(r'^dates', 0.06), (r'^stalk', 0.5)])]
    return hi, lo, dict(cull=False, tex=512, ao_dist=0.6, ao_strength=0.5, cage=0.02, ray=0.06, ds_low=True)


# ================================================================== rn_dune

def dune_h(x, y):
    x = np.asarray(x); y = np.asarray(y)
    s = np.where(y < 0, 0.55, 2.4)
    main = 3.1 * np.exp(-(x / 8.0) ** 2 - (y + 0.04 * x ** 2 - 1.0) ** 2 / 5.5 ** 2 * s)
    sec = 1.2 * np.exp(-((x + 8.5) / 4.0) ** 2 - ((y + 4.0) / 3.0) ** 2)
    fade = smoothstep(15.0, 11.5, np.abs(x)) * smoothstep(10.0, 7.0, np.abs(y))
    return (main + sec) * fade


def build_dune():
    SD = EK.m_sand('dunesand', seed=3.0)
    xs = np.linspace(-15, 15, 301); ys = np.linspace(-10, 10, 201); X, Y = np.meshgrid(xs, ys)
    Z = dune_h(X, Y)
    rip = 0.018 * np.sin((Y + 0.05 * X ** 2 * 0.2 + 0.4 * np.sin(X * 0.7)) * TAU / 0.38) * smoothstep(0.05, 0.5, Z)
    hi = [EK.grid_obj('dune', np.stack([X, Y, Z + rip], -1), None, [SD])]
    xl = np.linspace(-15, 15, 25); yl = np.linspace(-10, 10, 17); XL, YL = np.meshgrid(xl, yl)
    lo = [EK.tag_uvw(EK.grid_obj('dune_lo', np.stack([XL, YL, dune_h(XL, YL)], -1), None, []), 1.0)]
    return hi, lo, dict(cull=False, tex=512, ao_dist=1.5, ao_strength=0.4, cage=0.15, ray=0.5)


# ================================================================== rn_sphinx

def m_nemes(name='nemes'):
    """Başlık: mavi-altın yatay çizgiler (nesnenin kendi z'si), boya hafif solmuş, oyukta koyu."""
    def b(nt, bsdf):
        G = EK.EG(nt); x, y, z = G.sep(G.obj()); cw = G.coords()
        st = G.math('SINE', G.math('MULTIPLY', z, 15.0))
        col = G.mix(G.rng(st, -0.1, 0.1), '#2c5fae', '#e7b13f')
        col = G.mix(G.rng(G.noise4(cw, 1.5, 3), 0.4, 0.7, 0, 0.25), col, '#f1dcae')
        col = G.mix(G.rng(G.ao(0.15), 0.85, 0.35, 0, 0.5), col, '#2a2030')
        col = G.mix(G.math('MULTIPLY', G.edges(0.52, 0.6), 0.3), col, '#fff1c8')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def draw_collar(cv):
    W, Hh = cv.wm, cv.H / cv.ppm; cx, cy = W / 2, Hh
    cols = (EK.TURQ, EK.GOLD, EK.BLUE, EK.TERRA, EK.GOLD, EK.TURQ)
    for k, c in enumerate(cols):
        r0 = 0.25 + k * 0.1; r1 = r0 + 0.085
        pts = EK.arcpts(cx, cy, r1, r1, 180, 360, 30) + EK.arcpts(cx, cy, r0, r0, 360, 180, 30)
        cv.poly(pts, col=EK.C(c), val=180)
    for k in range(13):
        a = math.radians(190 + k * 160 / 12); r = 0.25 + 6 * 0.1 + 0.04
        cv.ell(cx + math.cos(a) * r, cy + math.sin(a) * r, 0.04, 0.05, col=EK.C(EK.BLUE if k % 2 else EK.TERRA))


def build_sphinx():
    ST = EK.m_stone('sphst', ('#c8975e', '#dcae74', '#ecca96'), bands=0.4, seed=2.0)
    dcol = KE.relief('collar', 1.9, 1.0, draw_collar, ppm=200, depth=0.012, seed=5)
    STC = EK.m_stone('sphchest', ('#c8975e', '#dcae74', '#ecca96'), dec=dcol, bands=0.4, seed=2.0)
    FACE = EK.m_stone('sphface', ('#d6a96f', '#e8c08a', '#f4d8a8'), bands=0.0, seed=4.0, pits=0.3)
    NM = m_nemes(); GD = EK.m_gold('sphgold')
    EYE = EK.m_flatc('spheye', '#2b2236', 0.05, 0.0); WH = EK.m_flatc('sphwhite', '#ffffff', 0.0, 0.0); BL = EK.m_flatc('sphblush', '#e3876a', 0.08, 0.1)
    LN = EK.m_flatc('sphliner', '#24345e', 0.05, 0.0)
    hi = []
    def B(n, c, r, m, rot=(0, 0, 0), seg=32, sub=2): o = blob(n, c, r, m, rot=rot, seg=seg, sub=sub); hi.append(o); return o
    # kaide (önünde simge bandı)
    def pdraw(cv):
        W, Hh = cv.wm, cv.H / cv.ppm
        for k, g in enumerate(('star', 'lotus', 'sun', 'lotus', 'star')):
            EK.GLYPHS[g](EK.Pen(cv, 0.1 + k * (W - 0.2) / 5 + 0.04, 0.05, (W - 0.2) / 5 - 0.08, Hh - 0.1))
    dp = KE.relief('sphbase', 2.2, 0.34, pdraw, ppm=200, seed=6)
    base = EK.rounded_box('sbase', (2.7, 6.3, 0.5), 0.06, 0.06, [EK.m_stone('sbasest', EK.SANDSTONE, dec=dp, seed=5.0)], loc=(0, 0.1, 0.25), chips=0.06, lump=0.008, seed=41)
    KE.front_dec(base, -1.1, -3.05, 0.08, 2.2, 0.34); hi.append(base)
    z0 = 0.5
    B('torso', (0, 0.7, z0 + 0.72), (0.92, 2.0, 0.72), ST)
    for sx in (-1, 1):
        B('haunch', (sx * 0.72, 1.85, z0 + 0.5), (0.42, 0.85, 0.5), ST)
        B('rpaw', (sx * 0.95, 1.05, z0 + 0.16), (0.24, 0.5, 0.17), ST, seg=24)
        hi.append(tube('fleg', [(sx * 0.55, -0.75, z0 + 0.62), (sx * 0.56, -1.7, z0 + 0.25), (sx * 0.56, -2.45, z0 + 0.18)], [0.28, 0.24, 0.22], ST, res=8))
        B('fpaw', (sx * 0.56, -2.62, z0 + 0.17), (0.3, 0.36, 0.17), ST, seg=24)
        for t in (-1, 0, 1):
            B('toe', (sx * 0.56 + t * 0.15, -2.92, z0 + 0.12), (0.085, 0.09, 0.08), ST, seg=16, sub=1)
    B('chest', (0, -0.75, z0 + 1.0), (0.82, 0.72, 0.85), STC)
    hi.append(tube('tail', [(0.6, 2.7, z0 + 0.2), (1.1, 2.3, z0 + 0.12), (1.18, 1.3, z0 + 0.1), (1.12, 0.4, z0 + 0.12)], [0.11, 0.1, 0.09, 0.08], ST, res=6))
    B('tuft', (1.12, 0.32, z0 + 0.16), (0.14, 0.2, 0.12), ST, seg=16)
    hz = z0 + 2.1; hy = -1.25
    B('nemes', (0, hy + 0.12, hz + 0.08), (0.7, 0.62, 0.66), NM)
    B('head', (0, hy - 0.06, hz), (0.6, 0.56, 0.58), FACE)
    B('cheeks', (0, hy - 0.42, hz - 0.2), (0.44, 0.26, 0.26), FACE)
    B('nose', (0, hy - 0.66, hz - 0.08), (0.08, 0.06, 0.065), FACE, seg=16, sub=1)
    for sx in (-1, 1):
        B('lappet', (sx * 0.56, hy - 0.2, hz - 0.62), (0.2, 0.17, 0.52), NM, rot=(8, sx * -6, 0))
        B('eye', (sx * 0.22, hy - 0.6, hz + 0.08), (0.1, 0.035, 0.125), EYE, rot=(0, 0, sx * -10), seg=16, sub=1)
        B('shine', (sx * 0.19, hy - 0.635, hz + 0.13), (0.03, 0.01, 0.035), WH, seg=8, sub=0)
        hi.append(tube('liner', [(sx * 0.12, hy - 0.62, hz + 0.2), (sx * 0.28, hy - 0.615, hz + 0.19), (sx * 0.4, hy - 0.57, hz + 0.13)], [0.016, 0.016, 0.012], LN, res=3))
        B('blush', (sx * 0.34, hy - 0.58, hz - 0.12), (0.1, 0.02, 0.06), BL, seg=12, sub=1)
    hi.append(tube('smile', [(-0.1, hy - 0.67, hz - 0.22), (0.0, hy - 0.69, hz - 0.26), (0.1, hy - 0.67, hz - 0.22)], [0.014, 0.016, 0.014], LN, res=3))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.62, minor_radius=0.04, location=(0, hy + 0.02, hz + 0.18), rotation=(math.radians(70), 0, 0))
    t = bpy.context.object; t.name = 'band'; t.scale = (1.06, 1.0, 1.0); t.data.materials.append(GD); hi.append(t)
    B('sundisc', (0, hy - 0.52, hz + 0.5), (0.12, 0.05, 0.12), GD, seg=16, sub=1)
    kit.to_mesh_all()
    decim = [(r'^sbase$', 0.012), (r'^(torso|chest|nemes|head)$', 0.06), (r'^(haunch|cheeks|lappet)$', 0.08), (r'^(rpaw|fpaw|fleg|tail)$', 0.08),
             (r'^(toe|tuft)$', 0.15), (r'^(eye|nose|shine|blush|sundisc)$', 0.3), (r'^(liner|smile)$', 0.4), (r'^band$', 0.15)]
    weights = [(r'^(head|cheeks|eye|nose|nemes|liner|smile|shine|blush|sundisc|band)$', 1.8), (r'^chest$', 1.3), (r'^sbase$', 0.7)]
    return hi, None, dict(decim=decim, weights=weights, tex=1024, budget=4000, ao_dist=0.5)


BUILD = {'rn_pyramid': build_pyramid, 'rn_obelisk': build_obelisk, 'rn_palm': build_palm, 'rn_dune': build_dune, 'rn_sphinx': build_sphinx}
