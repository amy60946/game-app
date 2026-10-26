# Kıyı yengeci v2 (26 Ekim 2026, kullanıcı: "Sahildeki hareket eden yengeçleri daha gerçekçi 3D ve zengin detaylı olana tasarımını
# optimize et"). Eski p_crab (kit2_v6.crab): tek parça ikosfer + düz tüpler, 700 üçgen, 256 px — bacaklar oynamıyordu.
# Yeni model gerçek yengeç yapısında, adanın yumuşak boyalı dilinde:
#   kabuk  geniş oval (yandan bakınca kubbe), önde göz çukuru ve alın çentiği, ön yan kenarda 5'er diş, sırtta "H" oluğu,
#          tanecikli yüzey (ince yumrular), turuncu-kırmızıdan koyu kenara geçiş + krem benekler; altı krem.
#   göz    sap + parlak siyah göz + ışık noktası.  kıskaç  kol (3 boğum) + şişkin avuç (yumrulu, sağ kıskaç biraz iri) + sabit parmak
#          + oynar parmak (iç kenarında dişler, uçları koyu).  bacak  4 çift, yassı 3 boğum + sivri uç, boğumlarda açık halka, kıl dikenleri.
# Oyun için parçalar AYRI nesnedir (oyun CrabLegs ile oynatır): body, leg_a0..3 / leg_b0..3 (a = +Y yanı), claw_a/b, finger_a/b
# (menteşede; oyunda kıskaca bağlanır), eye_a/b. Her parçanın orijini eklem yeridir. Tek doku: renk × AO + normal haritası (yüksek → hedef).
# Yön: önü +X (eski modelle aynı; oyunda EnvScaled 180° + yerleşim açısı), taban z = 0, boy ~0,17 m (Data/env_v6_sizes.json).
#
# Kullanım: /tmp/claude-0/bpyenv/bin/python -I art/code3d/crab_v2.py -- build            → Resources/Env/p_crab/
#           /tmp/claude-0/bpyenv/bin/python -I art/code3d/crab_v2.py -- preview <png>    → oyun modelinin çizimi (yan yana 3 açı)
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'v6'))
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, Matrix, noise as MN
import kit

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env', 'p_crab')
TEX, NTEX = 1024, 512

def c3(h):
    return V(kit.srgb(h)[:3])

SHELL_TOP, SHELL_MID, SHELL_EDGE = c3('#e8642e'), c3('#b8352a'), c3('#5e1f2a')
BODY_Z = 0.062   # kabuk ortasının yerden yüksekliği (bacaklar yana açılıp yere basar)
SPECK, BELLY, JOINT, TIP = c3('#f7d7a8'), c3('#f2d3a6'), c3('#f4b27a'), c3('#3b2226')
EYE, GLINT = c3('#141018'), c3('#ffffff')

def lerp(a, b, t):
    t = max(0.0, min(1.0, t)); return a * (1 - t) + b * t

# ------------------------------------------------------------------ ağ yardımcıları

def vc_mat(name, rough=0.42, coat=0.3):
    """Köşe rengi (Col) → taban rengi; pişirmede doğrudan dokuya aktarılır."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    at = nt.nodes.new('ShaderNodeVertexColor'); at.layer_name = 'Col'
    nt.links.new(at.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Coat Weight'].default_value = coat
    return m

MAT = None

def make_obj(name, verts, faces, colors):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    for i, c in enumerate(colors): ca.data[i].color = (c[0], c[1], c[2], 1.0)
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); me.materials.append(MAT)
    return o

def ico(sub):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    vs = [v.co.copy() for v in bm.verts]; fs = [[v.index for v in f.verts] for f in bm.faces]; bm.free()
    return vs, fs

def sweep(path, radii, around=12, flat=0.7, up=V((0, 0, 1)), cap=True):
    """Yol boyunca elips kesitli tüp: genişlik r (yatay), yükseklik r*flat. Uçlar kapalı. Döner: (köşeler, yüzler, t değerleri)."""
    vs, fs, ts = [], [], []
    n = len(path)
    for i, p in enumerate(path):
        d = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        x = d.cross(up)
        if x.length < 1e-4: x = d.cross(V((1, 0, 0)))
        x.normalize(); y = x.cross(d).normalized()
        r = radii[i]
        for k in range(around):
            a = k / around * math.tau
            vs.append(p + x * math.cos(a) * r + y * math.sin(a) * r * flat); ts.append(i / (n - 1))
    for i in range(n - 1):
        for k in range(around):
            a, b = i * around + k, i * around + (k + 1) % around
            fs.append((a, b, b + around, a + around))
    if cap:
        c0 = len(vs); vs.append(path[0] - (path[1] - path[0]).normalized() * radii[0] * 0.4); ts.append(0.0)
        c1 = len(vs); vs.append(path[-1] + (path[-1] - path[-2]).normalized() * radii[-1] * 0.4); ts.append(1.0)
        for k in range(around):
            fs.append((c0, (k + 1) % around, k))
            fs.append((c1, (n - 1) * around + k, (n - 1) * around + (k + 1) % around))
    return vs, fs, ts

def spline(pts, per=6):
    """Catmull-Rom ile yumuşak yol."""
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out

class Part:
    """Bir parçanın yüksek ve düşük ağları + eklem yeri."""
    def __init__(self, name, pivot, parent=None):
        self.name, self.pivot, self.parent = name, V(pivot), parent
        self.hv, self.hf, self.hc = [], [], []
        self.lv, self.lf, self.lc = [], [], []

    def add(self, verts, faces, colors, low=True, high=True):
        if high:
            o = len(self.hv); self.hv += verts; self.hf += [tuple(i + o for i in f) for f in faces]; self.hc += colors
        if low:
            o = len(self.lv); self.lv += verts; self.lf += [tuple(i + o for i in f) for f in faces]; self.lc += colors

    def add_hl(self, high, low):
        self.add(*high, low=False); self.add(*low, high=False)

PARTS = []

# ------------------------------------------------------------------ kabuk

def carapace_shape(q, fine):
    """Birim küre noktası → kabuk yüzeyi + renk. fine: tanecik ve dişler (yüksek model)."""
    x, y, z = q
    ang = math.atan2(y, x)
    # taban elips: önü (x>0) geniş ve düz, arkası daralan
    rx = 0.135 * (1.0 + 0.06 * x); ry = 0.19 * (1.0 - 0.18 * max(0.0, -x) ** 2)
    # ön yan kenar dişleri (5'er): kenar bandında, önde
    edge = max(0.0, 1.0 - abs(z) * 3.2)
    side = abs(math.sin(ang))
    front = max(0.0, math.cos(ang))
    teeth = 0.0
    a = abs(ang)
    if 0.55 < a < 1.85:   # ön yan kenarda dişler; düşük modelde de biçim olarak (yumuşak) kalır
        if True:
            ph = (a - 0.55) / 1.3 * 5.0
            teeth = (0.5 + 0.5 * math.cos(ph * math.tau)) ** (6 if fine else 2) * edge * (0.13 if fine else 0.07)
    # alın çentiği: tam önde, gözlerin arası
    notch = max(0.0, 1.0 - abs(ang) / 0.22) * edge * 0.10
    r = 1.0 + teeth - notch
    px, py = x * rx * r, y * ry * r
    # yükseklik: üst kubbe basık, alt düz
    pz = (z ** 0.8 if z > 0 else z) * (0.05 if z > 0 else 0.022)   # yassı kubbe, belirgin kenar
    # sırttaki "H" oluğu ve kenar sırtları
    nx, ny = px / 0.135, py / 0.19
    groove = 0.0
    if z > 0.2:
        groove += math.exp(-((abs(ny) - 0.33) / 0.07) ** 2) * math.exp(-(nx / 0.5) ** 2)       # iki boyuna oluk
        groove += math.exp(-((nx + 0.05) / 0.06) ** 2) * math.exp(-(ny / 0.3) ** 2)           # enine bağ
        pz -= groove * (0.011 if fine else 0.007) * z
    if fine and z > -0.1:
        g = MN.noise(V((px * 140, py * 140, pz * 140)))
        cell = MN.voronoi(V((px * 90, py * 90, 0.0)))[0][0]
        pz += (max(0.0, 0.32 - cell) * 0.006 + g * 0.0008) * max(0.0, z + 0.1)
    # renk
    t = (z + 0.1) / 1.0
    col = lerp(SHELL_EDGE, SHELL_MID, t * 2.2)
    col = lerp(col, SHELL_TOP, (t - 0.45) * 2.0)
    col = col * (1.0 - groove * 0.35)
    col = lerp(col, SHELL_EDGE, max(0.0, 1.0 - abs(z - 0.05) / 0.12) * 0.55)   # kenar çizgisi (sırt kenarı koyu)
    col = lerp(col, SHELL_EDGE, teeth * 6.0)                                   # dişlerin ucu koyu
    sp = MN.noise(V((px * 75, py * 75, 3.1)))
    if z > 0.15 and sp > 0.46: col = lerp(col, SPECK, (sp - 0.46) * 3.0)
    mot = MN.noise(V((px * 22, py * 22, 9.0)))                                 # koyu alacalar (gerçek kabuk deseni)
    if z > 0.2 and mot > 0.25: col = lerp(col, SHELL_MID * 0.75, (mot - 0.25) * 1.2)
    if z < -0.05: col = lerp(col, BELLY, min(1.0, -z * 2.5))
    col = col * (0.93 + 0.1 * MN.noise(V((px * 30, py * 30, 7.0))))
    return V((px, py, pz + BODY_Z)), col

def build_body():
    body = Part('body', (0, 0, BODY_Z))
    hv, hf = ico(6); lv, lf = ico(4)
    hp = [carapace_shape(q, True) for q in hv]; lp = [carapace_shape(q, False) for q in lv]
    body.add_hl(([p for p, c in hp], hf, [c for p, c in hp]), ([p for p, c in lp], lf, [c for p, c in lp]))
    # alt gövde (karın plakası) ve ağız parçaları: kabuğun altında, öne doğru
    PARTS.append(body)
    return body

# ------------------------------------------------------------------ göz

def build_eyes(body):
    for s, tag in ((1, 'a'), (-1, 'b')):
        base = V((0.118, s * 0.034, BODY_Z + 0.03))
        e = Part('eye_' + tag, base, body)
        top = base + V((0.012, s * 0.012, 0.042))
        pts = spline([base, base + V((0.004, s * 0.004, 0.02)), top], 4)
        v, f, t = sweep(pts, [0.0085 - 0.002 * i / (len(pts) - 1) for i in range(len(pts))], 10, 1.0)
        e.add(v, f, [lerp(SHELL_MID, JOINT, 0.3 + 0.4 * tt) for tt in t])
        for sub, low in ((3, False), (2, True)):
            iv, if_ = ico(sub)
            c = top + V((0.002, s * 0.001, 0.006))
            pv = [c + V((q.x * 0.011, q.y * 0.011, q.z * 0.012)) for q in iv]
            cols = [GLINT if (q.x > 0.45 and q.z > 0.35 and q.y * s < 0.2 and q.y * s > -0.35) else EYE for q in iv]
            e.add(pv, if_, cols, low=low, high=not low)
        PARTS.append(e)

# ------------------------------------------------------------------ bacak

def leg_colors(t, i0, n, tip_from=0.86):
    out = []
    for tt in t:
        c = lerp(SHELL_MID, SHELL_TOP, 0.35 + 0.3 * math.sin(tt * 9.0))
        for j in (0.34, 0.62):                                         # boğum halkası
            c = lerp(c, JOINT, max(0.0, 1.0 - abs(tt - j) / 0.035) * 0.8)
        if tt > tip_from: c = lerp(c, TIP, (tt - tip_from) / (1.0 - tip_from))
        out.append(c)
    return out

def build_legs(body):
    xs = [0.058, 0.02, -0.022, -0.062]
    splay = [0.07, 0.025, -0.03, -0.075]
    reach = [0.135, 0.15, 0.145, 0.12]
    for s, tag in ((1, 'a'), (-1, 'b')):
        for k in range(4):
            base = V((xs[k], s * 0.165, BODY_Z - 0.006))
            p = Part('leg_%s%d' % (tag, k), base, body)
            out = V((splay[k], s * 1.0, 0.0)).normalized()
            knee = base + out * reach[k] * 0.62 + V((0, 0, 0.035))      # uyluk yana ve hafif yukarı
            ank = knee + out * reach[k] * 0.38 + V((0, 0, -0.03))       # kaval aşağı-dışa
            tip = ank + out * 0.03 + V((0, 0, 0.0))
            tip.z = 0.0                                                  # sivri uç yere basar
            pts = spline([base, base + (knee - base) * 0.5 + V((0, 0, 0.012)), knee, ank, tip], 7)
            n = len(pts)
            def rad(i):
                t = i / (n - 1)
                r = 0.0125 * (1.0 - 0.35 * t)
                if t > 0.62: r *= max(0.12, 1.0 - (t - 0.62) / 0.38 * 0.9)
                for j in (0.34, 0.62): r *= 1.0 - 0.18 * max(0.0, 1.0 - abs(t - j) / 0.03)
                return r
            rh = [rad(i) for i in range(n)]
            v, f, t = sweep(pts, rh, 12, 0.62); p.add(v, f, leg_colors(t, 0, n), low=False)
            pl = pts[::2] + ([pts[-1]] if (len(pts) - 1) % 2 else [])
            rl = [rad(min(n - 1, i * 2)) for i in range(len(pl))]
            v, f, t = sweep(pl, rl, 7, 0.62); p.add(v, f, leg_colors(t, 0, len(pl)), high=False)
            # kıl dikenleri (yalnız yüksek modelde; normal haritasına geçer)
            R = random.Random(k * 7 + (s > 0))
            for j in range(9):
                i = int(n * (0.4 + 0.45 * j / 9))
                a = pts[i]; d = (pts[min(n - 1, i + 1)] - pts[i]).normalized()
                side_v = d.cross(V((0, 0, 1))).normalized() * (1 if j % 2 else -1)
                b = a + side_v * rh[i] * 0.9 + V((0, 0, -rh[i] * 0.3))
                e = b + side_v * 0.006 + d * 0.004 + V((0, 0, -0.002 * R.random()))
                vv, ff, tt = sweep([b, e], [0.0018, 0.0004], 4, 1.0)
                p.add(vv, ff, [lerp(JOINT, TIP, 0.4)] * len(vv), low=False)
            PARTS.append(p)

# ------------------------------------------------------------------ kıskaç

def tubercles(part, center, radii, count, seed, color, size=0.0035):
    R = random.Random(seed)
    for _ in range(count):
        q = V((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(0.0, 1))).normalized()
        p = center + V((q.x * radii[0], q.y * radii[1], q.z * radii[2])) * 0.98
        iv, if_ = ico(1)
        sz = size * R.uniform(0.6, 1.3)
        part.add([p + V((a.x * sz, a.y * sz, a.z * sz * 0.7)) for a in iv], if_, [color] * len(iv), low=False)

def build_claws(body):
    for s, tag in ((1, 'a'), (-1, 'b')):
        big = 1.12 if s > 0 else 1.0
        base = V((0.1, s * 0.11, BODY_Z - 0.004))
        cl = Part('claw_' + tag, base, body)
        elbow = base + V((0.05, s * 0.06, 0.012)) * big
        wrist = elbow + V((0.05, -s * 0.022, 0.006)) * big
        palm = wrist + V((0.038, -s * 0.018, -0.004)) * big
        arm = spline([base, elbow, wrist], 6)
        na = len(arm)
        v, f, t = sweep(arm, [0.018 * big * (1.0 - 0.2 * i / (na - 1)) for i in range(na)], 12, 0.75)
        cl.add(v, f, [lerp(SHELL_MID, JOINT, max(0.0, 1.0 - abs(tt - 0.5) / 0.08) * 0.7) for tt in t], low=False)
        v, f, t = sweep(arm[::2], [0.018 * big * (1.0 - 0.2 * i * 2 / (na - 1)) for i in range(len(arm[::2]))], 8, 0.75); cl.add(v, f, [SHELL_MID] * len(v), high=False)
        # avuç: şişkin elips, öne-içe doğru
        pr = V((0.04, 0.026, 0.03)) * big
        for sub, low in ((5, False), (3, True)):
            iv, if_ = ico(sub)
            pts, cols = [], []
            for q in iv:
                bulge = 1.0 + 0.12 * max(0.0, q.z) - 0.08 * max(0.0, -q.x)
                pp = palm + V((q.x * pr.x * bulge, q.y * pr.y, q.z * pr.z * bulge))
                c = lerp(SHELL_EDGE, SHELL_TOP, 0.5 + 0.5 * q.z)
                c = lerp(c, BELLY, max(0.0, -q.z - 0.3) * 1.2)
                if not low:
                    pp += V((0, 0, 1)) * MN.noise(pp * 160) * 0.0008
                    sp = MN.noise(pp * 70 + V((s, 0, 0)))
                    if q.z > 0.1 and sp > 0.45: c = lerp(c, SPECK, (sp - 0.45) * 3.0)
                pts.append(pp); cols.append(c)
            cl.add(pts, if_, cols, low=low, high=not low)
        tubercles(cl, palm, pr, 26, 11 + (s > 0), lerp(SHELL_TOP, SPECK, 0.4))
        # sabit parmak (avucun alt önünden)
        f0 = palm + V((pr.x * 0.8, -s * 0.004, -pr.z * 0.35))
        f1 = f0 + V((0.05, -s * 0.008, -0.006)) * big
        fixed = spline([f0, f0 + (f1 - f0) * 0.55 + V((0, 0, 0.003)), f1], 6)
        nf = len(fixed)
        def frad(i, r0=0.011):
            t = i / (nf - 1); return r0 * big * (1.0 - 0.85 * t ** 1.4)
        v, f, t = sweep(fixed, [frad(i) for i in range(nf)], 10, 0.8)
        cl.add(v, f, [lerp(SHELL_MID, TIP, (tt - 0.55) * 2.2) for tt in t], low=False)
        v, f, t = sweep(fixed[::2], [frad(i * 2) for i in range(len(fixed[::2]))], 6, 0.8)
        cl.add(v, f, [lerp(SHELL_MID, TIP, (tt - 0.55) * 2.2) for tt in t], high=False)
        for j in range(5):                                         # iç kenar dişleri (yukarı)
            i = 1 + j * (nf - 2) // 5; a = fixed[i] + V((0, 0, frad(i) * 0.55))
            vv, ff, tt = sweep([a, a + V((0.002, 0, 0.0045))], [0.0026, 0.0004], 5, 1.0)
            cl.add(vv, ff, [lerp(JOINT, SPECK, 0.5)] * len(vv), low=False)
        PARTS.append(cl)
        # oynar parmak: avucun üst önünde menteşe, aşağı-öne kıvrık
        hinge = palm + V((pr.x * 0.7, -s * 0.002, pr.z * 0.55))
        fg = Part('finger_' + tag, hinge, cl)
        g1 = hinge + V((0.052, -s * 0.008, -0.022)) * big
        mov = spline([hinge, hinge + (g1 - hinge) * 0.5 + V((0, 0, 0.007)), g1], 6)
        nm = len(mov)
        v, f, t = sweep(mov, [frad(i, 0.0105) for i in range(nm)], 10, 0.8)
        fg.add(v, f, [lerp(SHELL_TOP, TIP, (tt - 0.5) * 2.0) for tt in t], low=False)
        v, f, t = sweep(mov[::2], [frad(i * 2, 0.0105) for i in range(len(mov[::2]))], 6, 0.8)
        fg.add(v, f, [lerp(SHELL_TOP, TIP, (tt - 0.5) * 2.0) for tt in t], high=False)
        for j in range(5):
            i = 1 + j * (nm - 2) // 5; a = mov[i] - V((0, 0, frad(i, 0.0105) * 0.55))
            vv, ff, tt = sweep([a, a + V((0.002, 0, -0.0045))], [0.0024, 0.0004], 5, 1.0)
            fg.add(vv, ff, [lerp(JOINT, SPECK, 0.5)] * len(vv), low=False)
        PARTS.append(fg)

# ------------------------------------------------------------------ kurulum, pişirme, dışa aktarma

def construct():
    global MAT
    kit.reset()
    for o in [o for o in bpy.context.scene.objects]: bpy.data.objects.remove(o)
    PARTS.clear()
    MAT = vc_mat('crab')
    body = build_body(); build_eyes(body); build_legs(body); build_claws(body)
    high, low = [], []
    for i, p in enumerate(PARTS):
        h = make_obj(p.name + '_hi', p.hv, p.hf, p.hc)
        if p.name.startswith('leg') or p.name.startswith('claw') or p.name.startswith('finger') or p.name.startswith('eye'):
            m = h.modifiers.new('sub', 'SUBSURF'); m.levels = 1; m.render_levels = 1
        l = make_obj(p.name, p.lv, p.lf, p.lc)
        at = l.data.attributes.new('part', 'INT', 'FACE'); at.data.foreach_set('value', [i] * len(l.data.polygons))
        high.append(h); low.append(l)
    return high, low

def bake(path_noext, high, low):
    import proxy_bake as PB
    from PIL import Image
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    H = PB._join(high, 'high')
    L = PB._join(low, 'model', keep_materials=False)
    bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); bpy.context.view_layer.objects.active = L
    for l in list(L.data.uv_layers): L.data.uv_layers.remove(l)
    L.data.uv_layers.active = L.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='SCALED', margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    bm = bpy.data.materials.new('bake'); bm.use_nodes = True; L.data.materials.append(bm)
    tex = bm.node_tree.nodes.new('ShaderNodeTexImage'); bm.node_tree.nodes.active = tex
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_shadow', 'visible_volume_scatter'):
        if hasattr(L, attr): setattr(L, attr, False)
    bk = sc.render.bake
    bk.use_selected_to_active = True; bk.cage_extrusion = 0.006; bk.max_ray_distance = 0.02; bk.margin = 8; bk.use_clear = True
    def run(kind, sz):
        img = bpy.data.images.new(kind, sz, sz, alpha=False, float_buffer=True)
        img.colorspace_settings.name = 'Non-Color' if kind == 'nrm' else 'Linear Rec.709'
        tex.image = img
        bpy.ops.object.select_all(action='DESELECT'); H.select_set(True); L.select_set(True); bpy.context.view_layer.objects.active = L
        if kind == 'col':
            undo = PB._emission_swap(H.data.materials); bpy.ops.object.bake(type='EMIT'); PB._emission_restore(undo)
        elif kind == 'ao':
            sc.world.light_settings.distance = 0.03; bpy.ops.object.bake(type='AO')
        else:
            bk.normal_space = 'TANGENT'; bk.normal_r = 'POS_X'; bk.normal_g = 'POS_Y'; bk.normal_b = 'POS_Z'
            bpy.ops.object.bake(type='NORMAL')
        return np.array(img.pixels[:], np.float32).reshape(sz, sz, 4)
    col = PB._dilate(run('col', TEX), 12); ao = PB._dilate(run('ao', TEX), 12); nrm = PB._dilate(run('nrm', NTEX), 12)
    lin = np.clip(col[..., :3] * (1.0 - 0.55 * (1.0 - ao[..., :1])), 0, 1)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    Image.fromarray((np.clip(srgb, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_noext + '_basecolor.png', optimize=True)
    Image.fromarray((np.clip(nrm[..., :3], 0, 1) * 255).astype(np.uint8)[::-1]).save(path_noext + '_normal.png', optimize=True)
    bpy.data.objects.remove(H)
    L.data.materials.clear()
    for ca in list(L.data.color_attributes): L.data.color_attributes.remove(ca)
    return L

def split(L):
    """Pişmiş tek ağı parçalarına ayırır; her parçanın orijini eklem yeri, parmak kıskacın çocuğu."""
    vals = np.empty(len(L.data.polygons), np.int32); L.data.attributes['part'].data.foreach_get('value', vals)
    objs = {}
    for i, p in enumerate(PARTS):
        bm = bmesh.new(); bm.from_mesh(L.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if vals[f.index] != i], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        me = bpy.data.meshes.new(p.name); bm.to_mesh(me); bm.free()
        me.attributes.remove(me.attributes['part'])
        me.transform(Matrix.Translation(-p.pivot))
        o = bpy.data.objects.new(p.name, me); bpy.context.scene.collection.objects.link(o)
        o.location = p.pivot
        objs[p.name] = o
    # parmak FBX'te kıskacın çocuğu yapılmaz (Blender → FBX eksen çevirisinde çocuk iki kez dönüşüyordu); oyunda CrabLegs bağlar
    bpy.data.objects.remove(L)
    return list(objs.values())

def build():
    os.makedirs(OUT, exist_ok=True)
    high, low = construct()
    tris_high = sum(len(o.data.polygons) for o in high)
    L = bake(os.path.join(OUT, 'p_crab'), high, low)
    tris = sum(len(p.vertices) - 2 for p in L.data.polygons)
    objs = split(L)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'p_crab.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False,
                             use_tspace=True, object_types={'MESH'})
    hz = max((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    print('YAZILDI p_crab: hedef üçgen', tris, '· kaynak yüz', tris_high, '· boy', round(hz, 4), '· parça', len(objs), flush=True)

def preview(png):
    """Oyun modeli (FBX + dokular) üç açıdan, kumsal renginde zemin."""
    import bld.bld_kit as BK
    tmp = []
    for i, yaw in enumerate((30.0, 110.0, 200.0)):
        p = png.replace('.png', '_%d.png' % i); tmp.append(p)
        BK.render_low(os.path.join(OUT, 'p_crab'), p, yaw=yaw, pitch=28.0, size=(700, 520), lens=60)
    from PIL import Image
    ims = [Image.open(p) for p in tmp]
    w, h = ims[0].size; s = Image.new('RGB', (w * 3, h))
    for i, im in enumerate(ims): s.paste(im, (i * w, 0))
    s.save(png)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if not argv or argv[0] == 'build': build()
    elif argv[0] == 'preview': preview(argv[1])
