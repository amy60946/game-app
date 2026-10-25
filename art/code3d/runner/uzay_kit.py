# Gezegen Koşusu (koşu mini oyunu, Ay yüzeyi; Okti kaçan kuyruklu yıldızı kovalar) — malzeme ve parça araçları (25 Ekim 2026).
# Genel hat egypt_kit.py'den (dönemli 4B koordinat, kabartma tuvali, ızgara ağ, pişirme/önizleme); burada uzay malzemeleri:
#   m_paint   boyalı metal: ton dalgası, güneş solması, kenarda ve pul pul dökülen boya (altından çıplak metal, koyu pul kenarı),
#             çizikler, oyukta lacivert kir + Ay tozu, yukarı bakan yüzde toz; isteğe bağlı decal (çıkartma/şerit/ışık şeridi)
#   m_metal   çıplak metal (çelik/alüminyum/top metal): parlaklık renge işlenir (yukarı açık, kenar parlak, oyuk koyu), fırça izi
#   m_rubber  kablo/lastik · m_glow ışık "boyası" (oyunda parlama yok: parlak boya + sıcak çekirdek) · m_regolith Ay toprağı/kaya
#   m_crystal yüzeyli kristal (mor → camgöbeği), yüz başına ton, parıltı benekleri
# Parçalar: cıvata/perçin (yalnız taslakta; normal haritasına geçer), kablo + kelepçe, lamba (ampul + kafes), çıkartma çizimleri.
# Renk: Ay grisi (hafif sıcak lavanta), koyu lacivert/mor; oyuncak vurgular camgöbeği, mercan, ayçiçeği sarısı, nane. Neon yok, soluk yok.
# Yazı, gerçek logo, bayrak yok; korkutucu öğe yok.
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep, EG
import kit
from kit import blob, tube, cyl

MOON = ('#7f7b8f', '#a29db2', '#c8c3d4')        # Ay grisi + lavanta (koyu, orta, açık)
DUST = '#cfc9d8'
DECK = '#a9a5ba'                                 # yol paneli boyası
NAVY, VIOLET = '#2c3263', '#5b4ca0'
CYAN, TEAL, CORAL, SUN, MINT, CREAM = '#3fcad6', '#21a5a6', '#f2775a', '#f5bf33', '#7fd6ae', '#f3efe6'
STEEL, ALU, GUN = '#9ca5b0', '#c4cad2', '#4b5160'
_sh = EK._shade


def m_paint(name, hexc, period=None, chips=0.5, scratch=0.5, dust=0.5, grime=0.45, fade=0.18, under=STEEL, dec=None, scale=1.0,
            bump=0.12, seed=0.0):
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords(period, off=(seed * 3.3, seed * 1.1, seed * 2.7))
        col = G.mix(G.rng(G.noise4(cw, 0.9 * scale, 3), 0.3, 0.72), _sh(hexc, 0.93), _sh(hexc, 1.05))
        col = G.mix(0.1, col, G.noise4(cw, 30.0 * scale, 3, 0.6, 'Color'), 'OVERLAY')
        col = G.mix(G.rng(G.noise4(cw, 0.55 * scale, 3), 0.55, 0.78, 0, fade), col, _sh(hexc, 1.2))       # güneş solması
        if chips:
            ch = G.math('ADD', G.noise4(cw, 3.2 * scale, 6, 0.62), G.math('MULTIPLY', G.edges(0.53, 0.62), 0.28))
            th = 0.72 - 0.05 * chips
            keep = G.rng(ch, th, th - 0.025)
            rim = G.math('MULTIPLY', G.rng(ch, th - 0.05, th - 0.025), G.rng(ch, th + 0.02, th))
            metal = G.mix(G.rng(G.noise4(cw, 8.0, 3), 0.3, 0.7), _sh(under, 0.85), _sh(under, 1.08))
            col = G.mix(keep, metal, col)
            col = G.mix(G.math('MULTIPLY', rim, 0.5), col, _sh(hexc, 0.6))
        if scratch:
            vec, w = cw
            sv = G.vor4((G.mapping(vec, (2.0, 2.0, 14.0)) if period is None else vec, w), 5.0 * scale, 'DISTANCE_TO_EDGE')
            sm = G.math('MULTIPLY', G.rng(sv, 0.012, 0.0, 0, 1.0), G.rng(G.noise4(cw, 2.4, 3), 0.56, 0.64, 0, scratch))
            col = G.mix(sm, col, _sh(under, 1.15))
        col = G.mix(G.math('MULTIPLY', G.edges(0.53, 0.62), 0.3), col, _sh(hexc, 1.3))                     # aşınmış kenar
        if dec is not None:
            col, nin = EK.apply_dec(G, col, dec, period)
        else: nin = None
        occl = G.ao(0.1)
        col = G.mix(G.rng(occl, 0.85, 0.35, 0, grime), col, '#3b3656')                                     # oyuk kiri
        if dust:
            dc = G.math('MULTIPLY', G.rng(occl, 0.75, 0.35, 0, 0.7 * dust), G.rng(G.noise4(cw, 6.0, 3), 0.35, 0.6))
            col = G.mix(dc, col, DUST)                                                                           # oyukta Ay tozu
            up = G.math('MULTIPLY', G.rng(G.nz(), 0.6, 0.95), G.rng(G.noise4(cw, 1.3, 4), 0.45, 0.68, 0, 0.6 * dust))
            col = G.mix(up, col, DUST)
            x, y, z = G.sep(G.pos())
            col = G.mix(G.rng(G.math('ADD', z, G.math('MULTIPLY', G.noise4(cw, 5.0, 3), 0.1)), 0.22, 0.0, 0, 0.5 * dust), col, _sh(DUST, 0.92))
        G.l.new(col, bsdf.inputs['Base Color'])
        if bump: G.l.new(EK.bump_noise(G, nin, period, bump, 40.0, 0.004), bsdf.inputs['Normal'])
        elif nin is not None: G.l.new(nin, bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def m_metal(name, hexc=STEEL, period=None, dust=0.4, brushed=0.4):
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords(period)
        nz = G.nz()
        col = G.mix(G.rng(nz, -0.7, 0.9), _sh(hexc, 0.62), _sh(hexc, 1.0))
        col = G.mix(G.rng(nz, 0.5, 0.95, 0, 0.45), col, _sh(hexc, 1.28))
        vec, w = cw
        col = G.mix(G.rng(G.noise4((G.mapping(vec, (1.0, 1.0, 30.0)) if period is None else vec, w), 3.0, 3), 0.35, 0.7, 0, brushed * 0.4), col, _sh(hexc, 1.18))
        col = G.mix(G.math('MULTIPLY', G.edges(0.52, 0.6), 0.55), col, _sh(hexc, 1.45))
        col = G.mix(G.rng(G.ao(0.06), 0.85, 0.3, 0, 0.6), col, '#2e2b40')
        if dust:
            col = G.mix(G.math('MULTIPLY', G.rng(G.ao(0.08), 0.7, 0.35, 0, dust), G.rng(G.noise4(cw, 7.0, 3), 0.35, 0.6)), col, DUST)
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def m_rubber(name, hexc, period=None):
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords(period)
        col = G.mix(G.rng(G.nz(), -0.6, 0.9), _sh(hexc, 0.65), _sh(hexc, 1.12))
        col = G.mix(G.rng(G.noise4(cw, 2.0, 3), 0.4, 0.7, 0, 0.2), col, _sh(hexc, 1.25))
        col = G.mix(G.rng(G.ao(0.05), 0.85, 0.3, 0, 0.5), col, '#22202e')
        col = G.mix(G.math('MULTIPLY', G.rng(G.nz(), 0.5, 0.95), G.rng(G.noise4(cw, 4.0, 3), 0.45, 0.65, 0, 0.5)), col, DUST)
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def m_glow(name, hexc, core='#fffbe8', hot=0.75):
    """Işık boyası: doygun dış, sıcak açık çekirdek (yukarı-öne bakan yüzde), kenara doğru hafif koyulaşma."""
    def b(nt, bsdf):
        G = EG(nt); nx, ny, nz = G.sep(G.nrm())
        f = G.math('ADD', G.math('ADD', G.math('MULTIPLY', nz, 0.65), G.math('MULTIPLY', ny, -0.6)), G.math('MULTIPLY', nx, -0.2))
        col = G.mix(G.rng(f, -0.9, 0.2), _sh(hexc, 0.8), hexc)
        col = G.mix(G.rng(f, 0.25, 0.95, 0, hot), col, core)
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def m_regolith(name, pal=MOON, period=None, craters=0.6, dust=0.5, seed=0.0, scale=1.0):
    """Ay toprağı / kaya: lavanta-gri ton dalgası, minik krater benekleri (koyu çukur + açık kenar), koyu/açık taneler, yukarıda toz."""
    def b(nt, bsdf):
        G = EG(nt); cw = G.coords(period, off=(seed * 2.1, seed * 0.7, seed * 1.3))
        rp = EK.ramp(nt, [(0.3, pal[0]), (0.52, pal[1]), (0.72, pal[2])]); G.l.new(G.noise4(cw, 0.45 * scale, 4), rp.inputs['Fac'])
        col = rp.outputs[0]
        col = G.mix(0.18, col, G.noise4(cw, 25.0 * scale, 3, 0.6, 'Color'), 'OVERLAY')
        if craters:
            v = G.vor4(cw, 3.0 * scale)
            col = G.mix(G.math('MULTIPLY', G.rng(v, 0.18, 0.08, 0, 0.45 * craters), G.rng(G.noise4(cw, 1.1, 2), 0.45, 0.6)), col, _sh(pal[0], 0.8))
            col = G.mix(G.math('MULTIPLY', G.math('MULTIPLY', G.rng(v, 0.18, 0.22), G.rng(v, 0.3, 0.22)), G.rng(G.noise4(cw, 1.1, 2), 0.45, 0.6, 0, 0.6 * craters)), col, _sh(pal[2], 1.06))
            v2 = G.vor4(cw, 11.0 * scale)
            col = G.mix(G.rng(v2, 0.12, 0.04, 0, 0.35 * craters), col, _sh(pal[0], 0.82))
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 5, 0, 0)), 60.0), 0.0, 0.07, 0.45, 0), col, '#ece8f2')
        col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 9, 0, 0)), 45.0), 0.0, 0.06, 0.4, 0), col, '#55506a')
        col = G.mix(G.rng(G.ao(0.15), 0.85, 0.35, 0, 0.45), col, '#3f3a55')
        col = G.mix(G.math('MULTIPLY', G.rng(G.nz(), 0.55, 0.95), G.rng(G.noise4(cw, 1.4, 3), 0.42, 0.66, 0, dust)), col, DUST)
        G.l.new(col, bsdf.inputs['Base Color'])
        G.l.new(EK.bump_noise(G, None, period, 0.3, 18.0 * scale, 0.01), bsdf.inputs['Normal'])
    return EK.nodes_mat(name, b)


def m_crystal(name, c0=VIOLET, c1=CYAN, z0=0.0, z1=0.5, local=True):
    """Yüzeyli kristal: alt (z0) c0 → üst (z1) c1; yüz normaline göre yüz başına ton (düz gölgeli yüzeyler ayrı okunur), kenar parlak,
    iç parıltı benekleri, yukarı bakan yüz açık. local: nesnenin kendi z'si (her kristal kendi boyunca)."""
    def b(nt, bsdf):
        G = EG(nt)
        if local:
            x, y, z = G.sep(G.obj())
        else:
            x, y, z = G.sep(G.pos())
        col = G.mix(G.rng(z, z0, z1), _sh(c0, 0.95), c1)
        nx, ny, nz = G.sep(G.nrm())
        f = G.math('ADD', G.math('ADD', G.math('MULTIPLY', nx, 0.45), G.math('MULTIPLY', ny, -0.35)), G.math('MULTIPLY', nz, 0.55))
        col = G.mix(G.rng(f, -0.8, 0.1, 0.45, 0), col, _sh(c0, 0.55))
        col = G.mix(G.rng(f, 0.2, 0.95, 0, 0.6), col, '#f2fbff')
        col = G.mix(G.math('MULTIPLY', G.edges(0.51, 0.56), 0.8), col, '#ffffff')
        cw = G.coords()
        col = G.mix(G.rng(G.vor4(cw, 14.0), 0.0, 0.06, 0.8, 0), col, '#ffffff')
        col = G.mix(G.rng(G.noise4(cw, 3.0, 3), 0.55, 0.75, 0, 0.25), col, _sh(c1, 1.3))
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


# ------------------------------------------------------------------ parçalar

def orient(o, loc, nrm, spin=0.0):
    q = V(nrm).normalized().to_track_quat('Z', 'Y')
    from mathutils import Quaternion
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q @ Quaternion((0, 0, 1), spin); o.location = loc
    return o


def bolt(loc, nrm=(0, 0, 1), r=0.018, mat=None, hexhead=True, name='bolt'):
    """Altıgen cıvata başı + pul (yalnız taslak: hedefe girmez, normal + renk olarak pişer)."""
    m = mat or _cached('boltmat', lambda: m_metal('boltmat', STEEL, dust=0.5))
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r * 1.45, radius2=r * 1.45, depth=r * 0.25)
    for v in bm.verts: v.co.z += r * 0.125
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=6 if hexhead else 12, radius1=r, radius2=r * 0.9, depth=r * 0.75)
    for v in res['verts']: v.co.z += r * 0.25 + r * 0.375
    o = EK.A.link_mesh(name, bm, [m]); o.data.polygons.foreach_set('use_smooth', [False] * len(o.data.polygons))
    return orient(o, loc, nrm, random.uniform(0, 1.0))


def rivet(loc, nrm=(0, 0, 1), r=0.012, mat=None):
    m = mat or _cached('boltmat', lambda: m_metal('boltmat', STEEL, dust=0.5))
    bm = bmesh.new(); res = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=5, radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context='VERTS')
    for v in bm.verts: v.co.z *= 0.6
    o = EK.A.link_mesh('rivet', bm, [m]); EK.A.smooth(o)
    return orient(o, loc, nrm)


_C = {}
def _cached(k, fn):
    m = _C.get(k)
    if m is None or m.name not in bpy.data.materials: m = fn(); _C[k] = m
    return m


def cable(name, pts, r, mat, res=6):
    o = tube(name, pts, [r] * len(pts), mat, res=res)
    o.data.bevel_resolution = 3
    return o


def tie(loc, axis, r, mat=None):
    """Kablo kelepçesi: kısa halka."""
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=r * 0.18, major_segments=12, minor_segments=6, location=loc)
    t = bpy.context.object; t.name = 'tie'
    t.rotation_mode = 'QUATERNION'; t.rotation_quaternion = V(axis).normalized().to_track_quat('Z', 'Y')
    t.data.materials.append(mat or _cached('tiemat', lambda: m_rubber('tiemat', '#2b2a38'))); return t


def lamp(name, loc, r, hexc, cage=True, base_h=0.04, metal=None):
    """Lamba: ampul (ışık boyası), metal taban halkası, isteğe bağlı 3 tel kafes. Döner: parçalar."""
    M = metal or _cached('lampmetal', lambda: m_metal('lampmetal', GUN, dust=0.4))
    G_ = m_glow(name + '_glow', hexc)
    parts = [blob(name + '_bulb', (loc[0], loc[1], loc[2] + r * 0.85), (r, r, r * 0.95), G_, seg=20)]
    parts.append(cyl(name + '_base', (loc[0], loc[1], loc[2] + base_h / 2), r * 0.8, base_h, M, verts=14, bevel=0.004))
    if cage:
        for k in range(3):
            a = k * math.pi / 3
            bpy.ops.mesh.primitive_torus_add(major_radius=r * 1.05, minor_radius=r * 0.06, major_segments=20, minor_segments=5,
                                             location=(loc[0], loc[1], loc[2] + r * 0.85), rotation=(math.pi / 2, 0, a))
            t = bpy.context.object; t.name = name + '_cage'; t.data.materials.append(M); parts.append(t)
    return parts


# ------------------------------------------------------------------ çıkartma çizimleri (tuval, metre; yazısız)

def d_planet(cv, cx, cy, r, body=CORAL, ring=SUN, band=None, face=True, col_ring2=CREAM):
    """Sevimli halkalı gezegen amblemi: gövde dairesi + bant + eğik halka (önde) + gülen yüz."""
    C = EK.C
    a = math.radians(-18)
    def ringpts(rx, ry, a0, a1):
        out = []
        for i in range(25):
            t = math.radians(a0 + (a1 - a0) * i / 24); x, y = rx * math.cos(t), ry * math.sin(t)
            out.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
        return out
    cv.line(ringpts(r * 1.7, r * 0.45, 180, 360), r * 0.16, col=C(ring), layer='carve', val=120)
    cv.ell(cx, cy, r, r, col=C(body))
    for k, (dy, w) in enumerate(((0.35, 0.16), (-0.25, 0.12))):
        bc = band or _sh(body, 1.18 if k == 0 else 0.86)
        pts = [(cx + math.sqrt(max(0, 1 - ((dy + w / 2) ** 2))) * r * s, cy + (dy + w / 2) * r) for s in (-1, 1)]
        pts += [(cx + math.sqrt(max(0, 1 - ((dy - w / 2) ** 2))) * r * s, cy + (dy - w / 2) * r) for s in (1, -1)]
        cv.poly(pts, carve=False, col=C(bc))
    cv.line(ringpts(r * 1.7, r * 0.45, 0, 180), r * 0.16, col=C(ring), layer='raise')
    cv.line(ringpts(r * 1.55, r * 0.38, 0, 180), r * 0.04, col=C(col_ring2), layer='raise')
    if face:
        for s in (-1, 1):
            cv.ell(cx + s * r * 0.32, cy + r * 0.08, r * 0.09, r * 0.12, col=C('#2a2240'), layer='raise')
            cv.ell(cx + s * r * 0.32 - r * 0.03, cy + r * 0.13, r * 0.03, r * 0.035, col=C('#ffffff'), layer='raise')
            cv.ell(cx + s * r * 0.52, cy - r * 0.12, r * 0.1, r * 0.06, col=C('#ff9a8a'), carve=False)
        cv.line([(cx - r * 0.18, cy - r * 0.15), (cx, cy - r * 0.27), (cx + r * 0.18, cy - r * 0.15)], r * 0.05, col=C('#2a2240'))


def d_star(cv, cx, cy, r, col=SUN, inner=0.45, layer='carve'):
    pts = []
    for i in range(10):
        a = math.radians(90 + i * 36); rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    cv.poly(pts, col=EK.C(col), layer=layer)


def d_chevrons(cv, x0, y0, w, h, n=3, col=SUN, layer='carve', val=90):
    """İleri (+v) gösteren ok başları (yolda yön işareti)."""
    step = h / n
    for k in range(n):
        y = y0 + k * step
        cv.poly([(x0, y), (x0 + w / 2, y + step * 0.55), (x0 + w, y), (x0 + w, y + step * 0.38), (x0 + w / 2, y + step * 0.93), (x0, y + step * 0.38)],
                col=EK.C(col), layer=layer, val=val)


def clip_rect(poly, x0, y0, x1, y1):
    """Dışbükey çokgeni eksen hizalı dikdörtgene kırp (Sutherland–Hodgman)."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            if inside(b):
                if not inside(a): out.append(inter(a, b))
                out.append(b)
            elif inside(a): out.append(inter(a, b))
        return out
    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / ((b[0] - a[0]) or 1e-9))
    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / ((b[1] - a[1]) or 1e-9), yc)
    p = poly
    for inside, inter in ((lambda q: q[0] >= x0, ix(x0)), (lambda q: q[0] <= x1, ix(x1)), (lambda q: q[1] >= y0, iy(y0)), (lambda q: q[1] <= y1, iy(y1))):
        p = clip(p, inside, inter)
        if not p: break
    return p


def d_hazard(cv, x0, y0, w, h, c1=SUN, c2=NAVY, step=0.12, carve=False):
    """Çapraz uyarı şeritleri (dikdörtgen içinde)."""
    cv.rect(x0, y0, x0 + w, y0 + h, carve=carve, col=EK.C(c2))
    k = -h
    while k < w:
        q = clip_rect([(x0 + k, y0), (x0 + k + step * 0.5, y0), (x0 + k + step * 0.5 + h, y0 + h), (x0 + k + h, y0 + h)], x0, y0, x0 + w, y0 + h)
        if len(q) >= 3: cv.poly(q, carve=False, col=EK.C(c1))
        k += step


def dust_col(G, period=None, seed=0.0):
    """Ay tozu (yüzeye yığılan): açık lavanta-gri, iri ton dalgası, ince tane benekleri."""
    cw = G.coords(period, off=(seed, 0, 0))
    col = G.mix(G.rng(G.noise4(cw, 0.8, 3), 0.3, 0.72), _sh(DUST, 0.88), _sh(DUST, 1.04))
    col = G.mix(G.rng(G.vor4(cw, 70.0), 0.0, 0.07, 0.5, 0), col, '#f1eef6')
    col = G.mix(G.rng(G.vor4(G.coords(period, off=(seed + 3, 0, 0)), 50.0), 0.0, 0.05, 0.35, 0), col, '#6d6782')
    return col


def d_bolt(cv, cx, cy, r=0.018):
    """Haritada cıvata: kabarık altıgen + pul (renk çelik)."""
    cv.ell(cx, cy, r * 1.45, r * 1.45, col=EK.C('#8d95a2'), layer='raise', val=140)
    pts = [(cx + r * math.cos(math.radians(30 + 60 * i)), cy + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    cv.poly(pts, col=EK.C('#b9c0ca'), layer='raise')


# ------------------------------------------------------------------ pişirme yardımcıları (uç uca döşenen parçalar)

def planar_uv(x0, x1, y0, y1):
    def f(L):
        me = L.data
        for l in list(me.uv_layers): me.uv_layers.remove(l)
        uv = me.uv_layers.new(name='UVMap'); me.uv_layers.active = uv
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
        u = (co[vi, 0] - x0) / (x1 - x0); v = (co[vi, 1] - y0) / (y1 - y0)
        uv.data.foreach_set('uv', np.stack([u, v], -1).reshape(-1).astype(np.float32))
    return f


def bake_custom(name, high, low, uv_fn=None, cull=False, tex=1024, ao_dist=0.5, ao_strength=0.55, cage=0.03, ray=0.12, **kw):
    tex = int(os.environ.get('POFI_TEX', '0') or 0) or tex
    t = EK.PB.export_proxy(EK.out_dir(name), high, low, target=None, size=tex, nsize=tex, cage=cage, ray=ray, cull_hidden=cull,
                           uv_fn=uv_fn, uv_weight=None if uv_fn else 'uvw', dilate=16, ao_dist=ao_dist, ao_strength=ao_strength, **kw)
    print(name, 'üçgen', t, flush=True)
    return t
