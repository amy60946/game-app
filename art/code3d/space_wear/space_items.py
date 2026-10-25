# Uzay kıyafeti aksesuarları (kemiğe takılan sert eşyalar; 25 Ekim 2026). Ölçü yetişkin Okti'ye göre metre (oyun eşyayı sınır
# kutusuyla ölçekler, evre başına boy/yukarı/ileri ayarı space_fit.py). Ön = −Y, yukarı = +Z. Tasarımlar özgün.
#   hat_astro_helmet   cam fanus kask: başın eteğinin alt kenarını saran beyaz yaka halkası (turuncu şerit, mandallar, lamba,
#                      cıvatalar, küçük anten); cam ayrı dosya (_glass, aynı koordinat) → oyun camı seçer/saydam çizer
#   hat_pilot_goggles  alına itilmiş yuvarlak pilot gözlüğü: kahverengi deri kayış (toka, perçin), gri-mavi metal çerçeve, mavi cam
#   hat_star_antenna   başın üstünden geçen lila taç bandı (camgöbeği kenar, uçlarda yıldızlı yastık), yaylı anten + altın yıldız
#   back_astro_pack    yaşam destek çantası: yuvarlak köşeli beyaz gövde, sırtta 3 ışıklı panel, havalandırma, turuncu yan
#                      şeritler, tutamak, yan hortum halkaları, cıvatalar
#   back_pilot_jetpack lacivert sırt plakası + iki beyaz roket (camgöbeği bant, sarı burun, kanatçık, lüle), gösterge, perçin
#   back_star_cape     kuyrukluyıldız pelerini: sarıdan krem-beyaza, yumuşak dalgalı (3 dilli) kenar, kuyruk çizgileri,
#                      parıltılar, üstte altın yıldız broş + camgöbeği tutturma
# Kullanım: python -I space_items.py -- <çıktı> [id ...]
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
CODE3D = os.path.normpath(os.path.join(HERE, '..'))
for p in (HERE, CODE3D, os.path.join(CODE3D, 'v6')):
    if p not in sys.path: sys.path.insert(0, p)
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, Matrix
import kit
from kit import blob, rbox, cyl, tube, nodes_mat, ramp
import assets_v3 as A
from assets_v3 import _shade, smooth, link_mesh
from assets_wear_a import m_plastic, m_gold, m_gem, vinyl, revolve
from assets_items import m_fabric
import proxy_bake as PB

TAU = 2 * math.pi
WHITE, ORANGE, GREY, METAL, NAVY, TEAL, YELLOW, CYAN, LILAC = '#f1efea', '#f27d4a', '#c3c8d2', '#9aa3b2', '#2a4272', '#2b9ba5', '#f5c23c', '#43d2e2', '#b39ae6'


def reset():
    kit.reset()


def place(o, loc=(0, 0, 0), rot=(0, 0, 0)):
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; return o


def apply_all(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception: pass
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def torus(name, R, r, m, loc=(0, 0, 0), rot=(0, 0, 0), seg=64, mseg=14, sz=1.0):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=mseg)
    o = bpy.context.object; o.name = name; o.scale = (1, 1, sz); place(o, loc, rot)
    o.data.materials.append(m); smooth(o); return o


def star_prism(name, r, depth, m, inner=0.48, n=5, loc=(0, 0, 0), rot=(90, 0, 0), puff=0.35):
    """Kabarık 5 köşeli yıldız (vinyl): ortası şişkin, kenarları yuvarlak."""
    bm = bmesh.new(); ring = []
    for k in range(2 * n):
        a = math.pi / 2 + k * math.pi / n; rr = r if k % 2 == 0 else r * inner
        ring.append((math.cos(a) * rr, math.sin(a) * rr))
    top = []; bot = []
    for (x, y) in ring:
        top.append(bm.verts.new((x, y, depth / 2))); bot.append(bm.verts.new((x, y, -depth / 2)))
    ct = bm.verts.new((0, 0, depth / 2 + puff * r * 0.5)); cb = bm.verts.new((0, 0, -depth / 2 - puff * r * 0.3))
    N = len(ring)
    for k in range(N):
        k2 = (k + 1) % N
        bm.faces.new((top[k], top[k2], ct)); bm.faces.new((bot[k2], bot[k], cb)); bm.faces.new((top[k2], top[k], bot[k], bot[k2]))
    o = link_mesh(name, bm, [m])
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = depth * 0.35; bv.segments = 3; bv.limit_method = 'ANGLE'
    s = o.modifiers.new('sub', 'SUBSURF'); s.levels = 1
    smooth(o); place(o, loc, rot)
    return o


def ellipsoid_dome(name, rx, rz, z0, m, seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1)
    o = bpy.context.object; o.name = name
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02], context='VERTS')
    for v in bm.verts: v.co = V((v.co.x * rx, v.co.y * rx, max(0.0, v.co.z) * rz + z0))
    bm.to_mesh(o.data); bm.free(); o.data.materials.append(m); smooth(o)
    return o


# ------------------------------------------------------------------ malzemeler

def m_leather(hexc='#8a5634', name='leather'):
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 6, 4), 0.3, 0.75), _shade(hexc, 0.82), _shade(hexc, 1.12))
        col = G.mix(G.rng(G.vor(o, 120), 0.0, 0.08, 0.25, 0), col, _shade(hexc, 0.7), 'MULTIPLY')     # gözenek
        col = G.mix(G.math('MULTIPLY', G.edges(0.55, 0.65), 0.35), col, '#c99a72')                   # kenar aşınması
        col = vinyl(G, col, hexc, hl=0.25, top=0.1, low=0.12)
        G.l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_cape(name='cape'):
    """Kuyrukluyıldız: üstte sarı → altta krem-beyaz (nesne −Z boyunca), boyuna kuyruk çizgileri, minik parıltılar."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj(); n = nt.nodes; l = nt.links
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
        rp = ramp(nt, [(0.0, '#ffd23e'), (0.35, '#ffe07a'), (0.7, '#fff0bf'), (1.0, '#fffaf0')])
        v = G.math('MULTIPLY', G.math('SUBTRACT', 0.0, sp.outputs['Z']), 1.0 / 0.62)
        l.new(v, rp.inputs['Fac']); col = rp.outputs[0]
        # kuyruk çizgileri: x boyunca bantlar (aşağı doğru kayar)
        streak = G.math('SINE', G.math('MULTIPLY', G.math('ADD', sp.outputs['X'], G.math('MULTIPLY', sp.outputs['Z'], 0.35)), 70.0))
        col = G.mix(G.math('MULTIPLY', G.rng(streak, 0.2, 1.0), 0.12), col, '#fff6d8')
        col = G.mix(G.math('MULTIPLY', G.rng(streak, -0.2, -1.0), 0.08), col, '#e8b830', 'MULTIPLY')
        spark = G.rng(G.vor(o, 38), 0.06, 0.0)
        col = G.mix(G.math('MULTIPLY', spark, G.rng(G.noise(o, 9), 0.55, 0.62)), col, '#ffffff')
        col = vinyl(G, col, '#ffe07a', hl=0.3, top=0.06, low=0.1)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


# ------------------------------------------------------------------ 1. cam fanus kask

HELM_R = 0.39          # yaka halkası yarıçapı (yetişkin ölçüsü); fanus yarı eksenleri (R, R, 1.6 R)
HELM_K = 1.6


def hat_astro_helmet(glass=False):
    R = HELM_R
    if glass:
        g = ellipsoid_dome('glass', R * 0.985, R * HELM_K, 0.03, bpy.data.materials.new('glass'), seg=40)
        return [g]
    W = m_plastic(WHITE, 'hwhite', hl=0.45); OR = m_plastic(ORANGE, 'horange', hl=0.4); GR = m_plastic('#aeb5c2', 'hgrey', hl=0.3)
    MT = m_plastic(METAL, 'hmetal', hl=0.6)
    objs = []
    objs.append(torus('ring', R, 0.046, W, (0, 0, 0), sz=0.85))
    objs.append(revolve('band', [(R * 0.95, -0.075), (R * 1.0, -0.072), (R * 1.03, -0.05), (R * 1.035, -0.025), (R * 1.0, -0.012)], [W], segs=64))
    objs.append(torus('stripe', R * 1.033, 0.011, OR, (0, 0, -0.045), mseg=10))
    objs.append(torus('gasket', R * 0.975, 0.016, GR, (0, 0, 0.036), mseg=10))
    for k in range(16):                                   # cıvatalar halkanın üstünde
        a = k / 16 * TAU + 0.1
        objs.append(blob('bolt', (math.cos(a) * (R + 0.012), math.sin(a) * (R + 0.012), 0.034), (0.008, 0.008, 0.005), MT, sub=0, seg=10))
    for a in (40, 140, 220, 320):                          # mandallar
        r = math.radians(a); c = V((math.cos(r), math.sin(r), 0))
        b = rbox('latch', tuple(c * (R + 0.045) + V((0, 0, -0.012))), (0.034, 0.05, 0.052), GR, rot=(0, 0, a), bevel=0.01)
        objs.append(b)
        objs.append(rbox('lever', tuple(c * (R + 0.066) + V((0, 0, -0.005))), (0.012, 0.028, 0.036), OR, rot=(0, 0, a), bevel=0.005))
    # yan lamba (sol yan, öne bakar)
    lc = V((R + 0.035, -0.03, 0.05))
    objs.append(cyl('lamp', tuple(lc), 0.03, 0.06, W, rot=(90, 0, 0), verts=20, bevel=0.008))
    objs.append(blob('lens', tuple(lc + V((0, -0.032, 0))), (0.024, 0.008, 0.024), m_gem('#ffe47a', 'hlens'), sub=1, seg=16))
    objs.append(rbox('lampmount', tuple(lc + V((-0.03, 0.0, -0.035))), (0.03, 0.04, 0.05), GR, bevel=0.008))
    # sağ yanda telsiz kutusu + kısa anten (lambanın karşılığı: sınır kutusu iki yanda eşit, oyun ortalarken kaymasın)
    rc = V((-(R + 0.035), 0.02, 0.05))
    objs.append(rbox('radio', tuple(rc), (0.05, 0.07, 0.06), W, bevel=0.012))
    objs.append(rbox('radiomount', tuple(rc + V((0.03, 0, -0.03))), (0.03, 0.04, 0.05), GR, bevel=0.008))
    for k in range(3):
        objs.append(rbox('grill', tuple(rc + V((-0.026, 0.0, 0.018 - k * 0.016))), (0.004, 0.045, 0.006), GR, bevel=0.002))
    objs.append(cyl('ant', tuple(rc + V((0.0, 0.025, 0.1))), 0.006, 0.14, MT, verts=8, bevel=0))
    objs.append(blob('antball', tuple(rc + V((0.0, 0.025, 0.175))), (0.016, 0.016, 0.016), OR, sub=1, seg=12))
    return objs


# ------------------------------------------------------------------ 2. pilot gözlüğü (alında)

GOG_R = 0.245


def hat_pilot_goggles():
    R = GOG_R
    LE = m_leather('#8a5634', 'gstrap'); FR = m_plastic('#5d7189', 'gframe', hl=0.55); BR = m_gold('gbrass')
    LN = m_gem('#7cc7f2', 'glens'); RB = m_plastic('#3a3f4c', 'grubber', hl=0.15)
    objs = []
    objs.append(revolve('strap', [(R, -0.02), (R + 0.008, -0.019), (R + 0.01, 0.0), (R + 0.008, 0.019), (R, 0.02)], [LE], segs=72))
    # toka (sol yanda)
    objs.append(rbox('buckle', (R + 0.012, 0.05, 0.0), (0.012, 0.05, 0.05), BR, bevel=0.006))
    objs.append(rbox('buckleh', (R + 0.016, 0.05, 0.0), (0.006, 0.026, 0.028), LE, bevel=0.003))
    # iki mercek kabı: alnın üstünde, hafif yukarı bakar
    tilt = 24
    for sx in (-1, 1):
        cx = sx * 0.072
        base = V((cx, -R - 0.004, 0.012))
        cup = cyl('cup', tuple(base + V((0, -0.022, 0))), 0.056, 0.05, RB, rot=(90 - tilt, 0, 0), verts=32, bevel=0.012)
        objs.append(cup)
        d = V((0, -math.cos(math.radians(tilt)), math.sin(math.radians(tilt))))
        fc = base + d * 0.05
        objs.append(torus('frame', 0.056, 0.012, FR, tuple(fc), rot=(90 - tilt, 0, 0), seg=40, mseg=10))
        objs.append(blob('lens', tuple(fc - d * 0.002), (0.05, 0.05, 0.012), LN, rot=(90 - tilt, 0, 0), sub=1, seg=24))
        for k in range(6):
            a = k / 6 * TAU
            p = fc + V((math.cos(a) * 0.056, 0, math.sin(a) * 0.056 * math.cos(math.radians(tilt))))
            objs.append(blob('rivet', tuple(p + d * 0.011), (0.006, 0.006, 0.006), BR, sub=0, seg=8))
        objs.append(rbox('tab', (sx * 0.135, -R + 0.01, 0.008), (0.03, 0.03, 0.03), LE, bevel=0.008))
        objs.append(blob('tabrivet', (sx * 0.142, -R - 0.006, 0.008), (0.008, 0.008, 0.008), BR, sub=0, seg=8))
    objs.append(tube('bridge', [(-0.03, -R - 0.05, 0.03), (0, -R - 0.06, 0.04), (0.03, -R - 0.05, 0.03)], [0.011] * 3, FR, res=6))
    return objs


# ------------------------------------------------------------------ 3. antenli taç (başın üstünden)

BAND_A, BAND_B = 0.272, 0.315        # yarım elips: yarı genişlik, yükseklik (uçlar z = 0)


def _arc(t):
    """t 0..1 sol uçtan (+X) sağ uca (−X); yarım elips."""
    th = t * math.pi
    return V((math.cos(th) * BAND_A, 0.0, math.sin(th) * BAND_B)), V((math.cos(th) * BAND_B, 0, math.sin(th) * BAND_A)).normalized()


def hat_star_antenna():
    LI = m_plastic(LILAC, 'blilac', hl=0.45); CY = m_plastic(CYAN, 'bcyan', hl=0.5); GD = m_gold('bgold'); SP = m_plastic('#bfeaf2', 'bspring', hl=0.7)
    objs = []
    # bant: yuvarlak köşeli dikdörtgen kesit (n: dışa, y: genişlik)
    bm = bmesh.new(); N = 64; prof = []
    for k in range(16):
        a = k / 16 * TAU
        prof.append((math.cos(a) * 0.0075, math.sin(a) * 0.019))
    rows = []
    for i in range(N + 1):
        p, n = _arc(i / N)
        rows.append([bm.verts.new(p + n * (0.0075 + x) + V((0, y, 0))) for (x, y) in prof])
    for A_, B_ in zip(rows, rows[1:]):
        for k in range(16): bm.faces.new((A_[k], A_[(k + 1) % 16], B_[(k + 1) % 16], B_[k]))
    for row, rev in ((rows[0], True), (rows[-1], False)):
        c = bm.verts.new(sum((v.co for v in row), V()) / len(row))
        for k in range(16): bm.faces.new((row[(k + 1) % 16], row[k], c) if rev else (row[k], row[(k + 1) % 16], c))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    o = link_mesh('band', bm, [LI]); smooth(o); objs.append(o)
    for sy in (-1, 1):                                       # camgöbeği kenar biyeleri
        pts = []
        for i in range(0, N + 1, 2):
            p, n = _arc(i / N); pts.append(tuple(p + n * 0.009 + V((0, sy * 0.019, 0))))
        objs.append(tube('pipe', pts, [0.0045] * len(pts), CY, res=2))
    for t, sx in ((0.0, 1), (1.0, -1)):                      # uç yastıkları + yıldız
        p, n = _arc(t)
        objs.append(blob('pad', tuple(p + V((sx * 0.012, 0, 0.01))), (0.014, 0.032, 0.032), CY, sub=1, seg=20))
        objs.append(star_prism('padstar', 0.018, 0.006, GD, loc=tuple(p + V((sx * 0.027, 0, 0.012))), rot=(0, sx * 90, 0)))
    # anten: tepeye yakın (biraz sağda) yuva + yay + çubuk + altın yıldız
    p, n = _arc(0.58)
    base = p + n * 0.012
    objs.append(cyl('socket', tuple(base + n * 0.008), 0.014, 0.022, CY, rot=(0, -math.degrees(math.atan2(n.x, n.z)), 0), verts=16, bevel=0.004))
    pts = []
    turns = 6; Hs = 0.12; rs = 0.013
    up = n; side = V((0, 1, 0)); fw = up.cross(side).normalized()
    for k in range(turns * 12 + 1):
        a = k / 12 * TAU; z = k / (turns * 12) * Hs
        pts.append(tuple(base + up * (0.02 + z) + side * math.cos(a) * rs + fw * math.sin(a) * rs))
    objs.append(tube('spring', pts, [0.0035] * len(pts), SP, res=1))
    top = base + up * (0.02 + Hs + 0.03)
    objs.append(tube('rod', [tuple(base + up * (0.02 + Hs - 0.005)), tuple(top)], [0.0045, 0.0045], SP, res=1))
    objs.append(star_prism('star', 0.058, 0.024, GD, loc=tuple(top + up * 0.05), rot=(90, 12, 0)))
    objs.append(blob('starball', tuple(top + up * 0.006), (0.011, 0.011, 0.011), GD, sub=1, seg=12))
    return objs


# ------------------------------------------------------------------ 4. yaşam destek çantası

def back_astro_pack():
    W = m_plastic(WHITE, 'pwhite', hl=0.4); OR = m_plastic(ORANGE, 'porange', hl=0.4); NV = m_plastic('#33456a', 'ppanel', hl=0.2)
    GR = m_plastic('#aeb5c2', 'pgrey', hl=0.3); HO = m_plastic('#a3aac6', 'phose', hl=0.25); MT = m_plastic(METAL, 'pmetal', hl=0.6)
    objs = []
    Wd, Dp, Ht = 0.30, 0.14, 0.34
    yb = Dp / 2 + 0.005                                     # gövde arkası (sırta değen yüz y ≈ 0)
    objs.append(rbox('body', (0, yb, 0), (Wd, Dp, Ht), W, bevel=0.045, seg=4))
    objs.append(rbox('lid', (0, yb + 0.004, Ht / 2 - 0.02), (Wd * 0.92, Dp * 0.9, 0.05), W, bevel=0.02, seg=3))
    for sx in (-1, 1):
        objs.append(rbox('side', (sx * (Wd / 2 + 0.004), yb, -0.01), (0.012, Dp * 0.7, Ht * 0.75), OR, bevel=0.005))
    # arka yüz: ışık paneli + havalandırma
    face = yb + Dp / 2
    objs.append(rbox('panel', (0, face + 0.002, 0.075), (Wd * 0.72, 0.012, 0.085), NV, bevel=0.012, seg=3))
    for k, colr in enumerate(('#5fe8ee', '#7be38f', '#5fe8ee')):
        x = (k - 1) * 0.065
        objs.append(torus('bezel', 0.024, 0.006, MT, (x, face + 0.01, 0.075), rot=(90, 0, 0), seg=24, mseg=8))
        objs.append(blob('light', (x, face + 0.01, 0.075), (0.021, 0.012, 0.021), m_gem(colr, 'plight%d' % k), sub=1, seg=16))
    for k in range(5):
        objs.append(rbox('vent', (0, face + 0.001, -0.025 - k * 0.022), (Wd * 0.56, 0.008, 0.009), GR, bevel=0.003))
    for sx in (-1, 1):
        for sz in (-1, 1):
            objs.append(blob('bolt', (sx * (Wd / 2 - 0.03), face + 0.003, sz * (Ht / 2 - 0.035)), (0.009, 0.005, 0.009), MT, sub=0, seg=10))
    # tutamak
    objs.append(tube('handle', [(-0.08, yb + 0.02, Ht / 2), (-0.07, yb + 0.03, Ht / 2 + 0.05), (0.07, yb + 0.03, Ht / 2 + 0.05), (0.08, yb + 0.02, Ht / 2)], [0.012] * 4, GR, res=6))
    # yan hortum halkaları (yandan çıkıp alt köşeye girer)
    for sx in (-1, 1):
        p0 = V((sx * (Wd / 2 + 0.01), yb, 0.06)); p3 = V((sx * (Wd / 2 - 0.05), yb, -Ht / 2 - 0.005))
        pts = [p0, p0 + V((sx * 0.05, 0, -0.02)), V((sx * (Wd / 2 + 0.05), yb, -0.12)), p3 + V((sx * 0.04, 0, -0.03)), p3]
        cv = kit.tube('hose', [tuple(p) for p in pts], [0.016] * len(pts), HO, res=6)
        objs.append(cv)
        objs.append(cyl('port', tuple(p0 + V((sx * 0.006, 0, 0))), 0.022, 0.024, MT, rot=(0, 90, 0), verts=20, bevel=0.004))
        objs.append(cyl('port2', tuple(p3 + V((0, 0, 0.006))), 0.022, 0.024, MT, verts=20, bevel=0.004))
    return objs


# ------------------------------------------------------------------ 5. jetpack

def back_pilot_jetpack():
    NV = m_plastic(NAVY, 'jnavy', hl=0.3); W = m_plastic('#f3f1ec', 'jwhite', hl=0.45); TL = m_plastic(TEAL, 'jteal', hl=0.4)
    YL = m_plastic(YELLOW, 'jyellow', hl=0.45); GM = m_plastic('#4b5160', 'jgun', hl=0.35); MT = m_plastic(METAL, 'jmetal', hl=0.6)
    objs = []
    objs.append(rbox('plate', (0, 0.018, 0.0), (0.22, 0.03, 0.28), NV, bevel=0.03, seg=4))
    objs.append(rbox('strapL', (0.0, 0.004, 0.11), (0.25, 0.012, 0.04), NV, bevel=0.01))
    for sx in (-1, 1):
        cx = sx * 0.088; cy = 0.09
        prof = [(0.0, 0.205), (0.022, 0.2), (0.042, 0.18), (0.055, 0.15), (0.058, 0.12), (0.058, -0.08), (0.054, -0.1), (0.042, -0.115)]
        body = revolve('rocket', [(r, z) for (r, z) in reversed(prof)], [W], segs=40)
        body.location = (cx, cy, 0.0); objs.append(body)
        tip = blob('tip', (cx, cy, 0.19), (0.026, 0.026, 0.03), YL, sub=1, seg=16); objs.append(tip)
        for z, m in ((0.07, TL), (-0.045, TL)):
            objs.append(torus('band', 0.0585, 0.008, m, (cx, cy, z), seg=40, mseg=8))
        objs.append(torus('band2', 0.0588, 0.004, YL, (cx, cy, 0.05), seg=40, mseg=6))
        # lüle
        noz = revolve('nozzle', [(0.03, -0.11), (0.036, -0.13), (0.048, -0.165), (0.044, -0.168), (0.03, -0.14), (0.0, -0.14)], [GM], segs=32)
        noz.location = (cx, cy, 0.0); objs.append(noz)
        # kanatçıklar: dış yanda ve arkada
        for ang in (0.0 if sx > 0 else 180.0, 90.0):
            a = math.radians(ang)
            bm = bmesh.new()
            pts2 = [(0.05, -0.02), (0.1, -0.11), (0.1, -0.15), (0.05, -0.1)]
            vs = []
            for (r, z) in pts2:
                for t in (-0.006, 0.006):
                    p = V((math.cos(a) * r - math.sin(a) * t, math.sin(a) * r + math.cos(a) * t, z))
                    vs.append(bm.verts.new(p))
            q = [vs[i] for i in range(0, 8, 2)]; q2 = [vs[i] for i in range(1, 8, 2)]
            bm.faces.new(q); bm.faces.new(list(reversed(q2)))
            for i in range(4):
                j = (i + 1) % 4; bm.faces.new((q[i], q[j], q2[j], q2[i]))
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            f = link_mesh('fin', bm, [TL]); f.location = (cx, cy, 0)
            bv = f.modifiers.new('bv', 'BEVEL'); bv.width = 0.004; bv.segments = 2
            objs.append(f)
        # kelepçe (plakaya)
        for z in (0.09, -0.06):
            objs.append(cyl('bracket', (cx, 0.045, z), 0.012, 0.05, MT, rot=(90, 0, 0), verts=12, bevel=0.003))
    # gösterge (plakanın ortası, iki roket arasında)
    objs.append(cyl('gauge', (0, 0.04, 0.02), 0.03, 0.02, MT, rot=(90, 0, 0), verts=24, bevel=0.004))
    objs.append(cyl('gface', (0, 0.051, 0.02), 0.024, 0.004, W, rot=(90, 0, 0), verts=24, bevel=0))
    objs.append(rbox('needle', (0.006, 0.054, 0.026), (0.004, 0.002, 0.02), m_plastic('#e24b3b', 'jred', hl=0.3), rot=(0, 30, 0), bevel=0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            objs.append(blob('rivet', (sx * 0.095, 0.034, sz * 0.12), (0.007, 0.004, 0.007), MT, sub=0, seg=8))
    return objs


# ------------------------------------------------------------------ 6. kuyrukluyıldız pelerini

def back_star_cape():
    CP = m_cape('cape'); GD = m_gold('cgold'); CY = m_plastic(CYAN, 'ccyan', hl=0.5)
    nu, nv = 28, 30
    L = 0.62
    bm = bmesh.new(); grid = []
    for j in range(nv + 1):
        v = j / nv; row = []
        for i in range(nu + 1):
            u = i / nu * 2 - 1
            # alt kenar: 3 yumuşak dil (ortadaki uzun), kuyruk Okti'nin sağına (−X) hafif kayar
            lobe = 0.5 - 0.5 * math.cos(TAU * 1.5 * (u + 1))
            vend = 1.0 - 0.10 * lobe - 0.05 * abs(u) ** 1.5
            vv = v * vend
            w = 0.10 + 0.13 * vv ** 0.75
            x = u * w - 0.06 * vv ** 2
            z = -vv * L
            y = 0.035 - 0.07 * (1 - vv) * u * u + 0.20 * vv ** 1.6 + 0.012 * math.sin(3 * u + vv * 4)    # sırtı sarar, aşağıda geriye açılır
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    cape = link_mesh('cape', bm, [CP]); smooth(cape)
    s = cape.modifiers.new('sol', 'SOLIDIFY'); s.thickness = 0.008; s.offset = 0; s.use_rim = True
    sb = cape.modifiers.new('sub', 'SUBSURF'); sb.levels = 1
    objs = [cape]
    # üstte camgöbeği tutturma bandı + altın yıldız broş
    pts = []
    for i in range(13):
        u = i / 12 * 2 - 1; pts.append((u * 0.105, 0.035 - 0.07 * u * u + 0.004, -0.005))
    objs.append(tube('clasp', pts, [0.009] * len(pts), CY, res=3))
    objs.append(star_prism('brooch', 0.042, 0.016, GD, loc=(0.0, 0.05, -0.02), rot=(-90, 0, 0)))
    return objs


BUILDERS = {
    'hat_astro_helmet': (hat_astro_helmet, 3500, 1024),
    'hat_pilot_goggles': (hat_pilot_goggles, 3200, 512),
    'hat_star_antenna': (hat_star_antenna, 2800, 512),
    'back_astro_pack': (back_astro_pack, 4200, 1024),
    'back_pilot_jetpack': (back_pilot_jetpack, 4800, 1024),
    'back_star_cape': (back_star_cape, 2600, 1024),
}


def build(iid):
    reset()
    fn = BUILDERS[iid][0]
    objs = fn()
    kit.to_mesh_all()
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def export_item(iid, out):
    """Taslak (tam ayrıntı) → oyun ağı (bütçe) + renk × AO + normal haritası (v6/proxy_bake)."""
    fn, target, size = BUILDERS[iid]
    objs = build(iid)
    os.makedirs(out, exist_ok=True)
    tris = PB.export_proxy(os.path.join(out, iid), objs, None, target=target, size=size, nsize=size, cage=0.01, ray=0.04,
                           ao_strength=0.55, ao_dist=0.08, dilate=16)
    print('ESYA', iid, 'üçgen', tris, flush=True)
    if iid == 'hat_astro_helmet':
        export_glass(out)
    return tris


def export_glass(out):
    """Fanus camı: ayrı ağ ve malzeme ('glass'), aynı koordinat. Doku RGBA: hafif mavi ton, alfa kenarda/parıltıda yüksek."""
    from PIL import Image
    reset()
    g = hat_astro_helmet(glass=True)[0]
    me = g.data
    for l in list(me.uv_layers): me.uv_layers.remove(l)
    uv = me.uv_layers.new(name='UVMap')
    R = HELM_R
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a = math.atan2(co.y, co.x); h = (co.z - 0.03) / (R * HELM_K)
            uv.data[li].uv = ((a + math.pi) / TAU, min(1.0, max(0.0, h)))
    me.materials.clear(); me.materials.append(bpy.data.materials.new('glass'))
    g.name = 'glass'; me.name = 'glass'
    S = 256
    u = (np.arange(S) + 0.5) / S; U, Vv = np.meshgrid(u, u)
    a = U * TAU - math.pi
    # parıltı: sol-ön-üstte geniş yumuşak leke + ince yay; tabana yakın hafif buğu
    hl = np.exp(-(((a - (-2.2)) / 0.35) ** 2 + ((Vv - 0.62) / 0.12) ** 2)) * 0.9
    arc = np.exp(-(((a - 1.0) / 0.9) ** 2)) * np.exp(-((Vv - 0.78) / 0.03) ** 2) * 0.6
    fog = np.clip((0.18 - Vv) / 0.18, 0, 1) * 0.25
    alpha = np.clip(0.10 + hl + arc + fog, 0, 1)
    rgb = np.stack([0.86 + 0.14 * (hl + arc), 0.94 + 0.06 * (hl + arc), np.ones_like(hl)], -1)
    img = np.concatenate([np.clip(rgb, 0, 1), alpha[..., None]], -1)
    Image.fromarray((img * 255).astype(np.uint8)[::-1]).save(os.path.join(out, 'hat_astro_helmet_glass_basecolor.png'))
    bpy.ops.object.select_all(action='DESELECT'); g.select_set(True); bpy.context.view_layer.objects.active = g
    bpy.ops.export_scene.fbx(filepath=os.path.join(out, 'hat_astro_helmet_glass.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False)
    print('ESYA hat_astro_helmet_glass üçgen', sum(len(p.vertices) - 2 for p in me.polygons), flush=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    out = args[0]; ids = args[1:] or list(BUILDERS)
    for i in ids: export_item(i, out)
