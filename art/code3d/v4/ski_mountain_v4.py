# Ön tasarım v4 (20 Ekim 2026, kullanıcı geri bildirimi): Kayak Tepesi + Dağ — ada zeminiyle bütünleşik.
#   /tmp/claude-0/bpyenv/bin/python -I ski_mountain_v4.py -- <çıktı_klasörü> [ski mountain pine skis]
# Fikir: yapı zemine "konmuş" bir obje değil; arazinin kendi tepesi (IslandTerrain.Hills) kar/kaya ile boyanır, model tepenin
# yamacına oturur ve tabanında arazi rengine eriyen bir etek (skirt) taşır. Çam: palmiyedeki yaprakçık tekniği (orta dal +
# iki yanda sarkan iğne yaprakçıkları), kar dalların ÜSTÜNE yastık gibi oturur. Kayak askısı: iki A ayaklı ahşap sehpa,
# uçları kıvrık, bağlamalı kayaklar ve sepetli batonlar. Tasarımlar özgün; referanslardan kopya yok.
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import bpy, bmesh
from mathutils import Vector as V, noise as mnoise
import kit
from kit import srgb, mat, blob, rbox, tube, nodes_mat, ramp
import assets_v3 as A
from assets_v3 import m_leaf, m_bark, m_rock, m_flat, m_wood, mesh_from_blades, blade, smooth, link_mesh, pebble, rosette, flower_heads
import assets_town as T
from assets_town import m_snow, m_metal, plank, post, prism, rock, lush, m_sand

ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
OKTI = '/tmp/claude-0/-home-user/9d82c246-9212-5e5a-a688-80e5574aeba1/scratchpad/octo_dl/teen.glb'

# ------------------------------------------------------------------ arazi (oyundaki IslandTerrain.HillHeight ile aynı biçim)

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

class Terrain:
    """Gauss tepeler + hafif dalga; yüzey: çim (iki ton), kar (gürültülü, yumuşak geçişli kenar + 'kırağılı çim' bandı), kaya (dik yamaç)."""
    def __init__(self, hills, size, cx=0.0, cy=0.0, res=150):
        self.hills, self.size, self.cx, self.cy, self.res = hills, size, cx, cy, res
    def h(self, x, y):
        z = 0.25 + 0.12 * mnoise.noise(V((x * 0.12, y * 0.12, 1.3)))
        for (hx, hy, hh, hr, snow) in self.hills:
            g = math.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (2 * hr * hr))
            z += hh * g * (1 + 0.25 * (mnoise.noise(V((x * 0.3 + hx, y * 0.3, 0))) * 0.5))
        return z
    def snow_w(self, x, y):
        w = 0.0
        for (hx, hy, hh, hr, snow) in self.hills:
            if snow: w = max(w, math.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (2 * hr * hr)))
        n = mnoise.noise(V((x * 0.45, y * 0.45, 7.0))) * 0.09 + mnoise.noise(V((x * 1.6, y * 1.6, 3.0))) * 0.035
        return smoothstep(0.22, 0.42, w + n)              # oyun: SmoothStep(0.25, 0.5) — sınır gürültüyle kırılır, sert çizgi yok
    def normal(self, x, y):
        e = 0.15
        return V((self.h(x - e, y) - self.h(x + e, y), self.h(x, y - e) - self.h(x, y + e), 2 * e)).normalized()
    def snow_raw(self, x, y):
        w = 0.0
        for (hx, hy, hh, hr, snow) in self.hills:
            if snow: w = max(w, math.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (2 * hr * hr)))
        return w
    def zones(self, x, y):
        """Biyom ağırlıkları (kar, kaya, soğuk çim, çim): yumuşak, gürültülü geçiş — sert sınır yok."""
        s = self.snow_w(x, y); nz = self.normal(x, y).z
        n = mnoise.noise(V((x * 0.6, y * 0.6, 4.0)))
        edge = math.exp(-((s - 0.35) / 0.22) ** 2)                      # kar kenarı bandı
        rock = max(smoothstep(0.86, 0.7, nz) * 0.85, edge * smoothstep(-0.2, 0.4, n) * 0.55) * (1 - smoothstep(0.7, 1.0, s))
        cool = smoothstep(0.02, 0.35, self.snow_raw(x, y)) * (1 - s)      # kara yakın çim: soğuk, mavimsi yeşil
        return s, rock, cool
    def color(self, x, y):
        g1, g2, dry = V(srgb('#5f8f3a')[:3]), V(srgb('#7aa646')[:3]), V(srgb('#9aa45a')[:3])
        k = 0.5 + 0.5 * mnoise.noise(V((x * 0.25, y * 0.25, 2.0)))
        c = g1.lerp(g2, k).lerp(dry, max(0.0, mnoise.noise(V((x * 0.08, y * 0.08, 9.0)))) * 0.5)
        s, rockw, cool = self.zones(x, y)
        c = c.lerp(V(srgb('#5e8a6c')[:3]).lerp(V(srgb('#7c9c86')[:3]), k), cool * 0.85)     # soğuk çim tonu
        c = c.lerp(V(srgb('#8a8174')[:3]).lerp(V(srgb('#a89c8a')[:3]), k), rockw)          # kaya bandı / dik yamaç
        nz = self.normal(x, y).z
        c = c.lerp(V(srgb('#c4d0c4')[:3]), smoothstep(0.15, 0.5, s) * 0.45)               # kırağı
        snow = V(srgb('#ebf1fa')[:3]).lerp(V(srgb('#cddbf0')[:3]), (1 - nz) * 1.5)
        c = c.lerp(snow, smoothstep(0.42, 0.95, s))
        return c, s, rockw

    def build(self):
        n = self.res; S = self.size
        bm = bmesh.new(); col = bm.loops.layers.color.new('Col')
        vs = []
        for j in range(n + 1):
            row = []
            for i in range(n + 1):
                x = self.cx + (i / n - 0.5) * S; y = self.cy + (j / n - 0.5) * S
                row.append(bm.verts.new((x, y, self.h(x, y))))
            vs.append(row)
        cache = {}
        for j in range(n):
            for i in range(n):
                f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
                for lp in f.loops:
                    if lp.vert not in cache:
                        c, _, _ = self.color(lp.vert.co.x, lp.vert.co.y); cache[lp.vert] = (c.x, c.y, c.z, 1.0)
                    lp[col] = cache[lp.vert]
        me = bpy.data.meshes.new('terrain'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('terrain', me); bpy.context.scene.collection.objects.link(o)
        m = bpy.data.materials.new('terrain'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
        b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.92
        at = N.new('ShaderNodeVertexColor'); at.layer_name = 'Col'
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9; nz.inputs['Detail'].default_value = 6
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'OVERLAY'; mx.inputs['Factor'].default_value = 0.18
        L.new(at.outputs['Color'], mx.inputs[6]); L.new(nz.outputs['Color'], mx.inputs[7]); L.new(mx.outputs[2], b.inputs['Base Color'])
        o.data.materials.append(m); smooth(o)
        return o

def drape(tr, pts, width, m, lift=0.03, name='ribbon', uvlen=1.0):
    """Arazi üstüne oturan şerit (patika, pist): her nokta yüksekliği arazi fonksiyonundan."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); prev = None; acc = 0.0
    for k, (x, y) in enumerate(pts):
        a = pts[min(k + 1, len(pts) - 1)]; b_ = pts[max(k - 1, 0)]
        tx, ty = a[0] - b_[0], a[1] - b_[1]; L = math.hypot(tx, ty) or 1
        sx, sy = -ty / L, tx / L
        w = width(k / (len(pts) - 1)) if callable(width) else width
        l = bm.verts.new((x + sx * w, y + sy * w, tr.h(x + sx * w, y + sy * w) + lift))
        r = bm.verts.new((x - sx * w, y - sy * w, tr.h(x - sx * w, y - sy * w) + lift))
        if prev:
            acc += math.hypot(x - prev[2], y - prev[3])
            f = bm.faces.new((prev[0], prev[1], r, l))
            for lp, uv in zip(f.loops, ((0, prev[4]), (1, prev[4]), (1, acc * uvlen), (0, acc * uvlen))): lp[uvl].uv = uv
        prev = (l, r, x, y, acc * uvlen)
    o = link_mesh(name, bm, [m]); smooth(o); return o

# ------------------------------------------------------------------ çam v4 (palmiye yaprakçık tekniği)

def pine_v4(loc, h, seed, snow=False, lod=1.0):
    """Gövde (kabuk) + 10 kat dal; her dal = orta dal şeridi + iki yanda öne-aşağı eğik, ince-kısa iğne yaprakçıkları (palmiye
    yaprağındaki yaprakçık dizilimi, iğne ölçeğinde), dal ucu sarkık; alt katlar uzun ve aşağı eğik → koni silüeti. Tepe tomurcuğu.
    Kar: dalın üst yüzüne uzun yastıklar (alt yüz yeşil kalır). lod < 1: oyun sürümü için yaprakçık sayısı azalır."""
    R = random.Random(seed); x, y, z = loc
    tube('trunk', [(x, y, z - 0.1), (x, y, z + h * 0.5), (x, y, z + h * 0.97)], [0.045 * h, 0.032 * h, 0.01 * h], m_bark(), res=3)
    ND = m_leaf('#163a2a', '#22543a', '#356f45', '#3d7a4b', 'needle_v4')
    ND2 = m_leaf('#1a4430', '#2a6342', '#43834f', '#4b8c55', 'needle_v4b')
    TW = m_flat('#4a3626', 0.2, 12, 'twig')
    tiers = 14; branches_out = []
    def build(bm):
        out = []
        for t in range(tiers):
            k = t / (tiers - 1)
            zt = z + h * (0.12 + 0.83 * k); L = h * (0.44 - 0.37 * k ** 0.85) * R.uniform(0.88, 1.1)
            nb = max(6, int((12 - 5 * k) * (0.6 + 0.4 * lod)))
            for i in range(nb):
                az = i * 2 * math.pi / nb + R.uniform(-0.25, 0.25) + t * 0.9
                d = V((math.cos(az), math.sin(az), 0)); side = V((-d.y, d.x, 0))
                droop = R.uniform(0.18, 0.32) * (1.15 - 0.7 * k); rise = -0.18 + 0.38 * k
                def C(s, d=d, L=L, zt=zt, droop=droop, rise=rise): return V((x, y, zt)) + d * (L * s) + V((0, 0, rise * L * s - droop * L * s * s))
                branches_out.append((C, L))
                for f in blade(bm, C(0), (C(1) - C(0)).normalized(), side, L, 0.012 * h, 0.0, segs=1): out.append((f, 2))
                nl = max(6, int(16 * lod))
                for j in range(nl):
                    s = 0.08 + 0.9 * j / nl; c = C(s)
                    tan = (C(min(1, s + 0.03)) - C(s)).normalized()
                    for sgn in (-1, 1):
                        dd = (tan * 0.75 + side * sgn * 0.55 + V((0, 0, -0.28))).normalized()
                        ll = L * (0.2 - 0.1 * s) * R.uniform(0.8, 1.2)
                        for f in blade(bm, c, dd, V((0, 0, 1)).cross(dd).normalized(), ll, 0.011 * h, 0.25, segs=2): out.append((f, (j + t) % 2))
        top = V((x, y, z + h))
        for q in range(10):
            a = q * 0.63; dd = V((math.cos(a) * 0.4, math.sin(a) * 0.4, 1)).normalized()
            for f in blade(bm, top - V((0, 0, 0.1 * h)), dd, V((-math.sin(a), math.cos(a), 0)), 0.13 * h, 0.014 * h, 0.1, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('pine_v4', build, [ND, ND2, TW])
    if snow:
        SN = m_snow('snow_v4')
        for (C, L) in branches_out:
            if R.random() < 0.35: continue
            s0 = R.uniform(0.35, 0.55); p = C(s0) + V((0, 0, 0.02 * h)); d = (C(s0 + 0.15) - C(s0 - 0.15))
            o = blob('snowpad', tuple(p), (L * 0.38, 0.05 * h, 0.014 * h), SN, sub=1, seg=12)
            o.rotation_euler = (0, -math.atan2(d.z, math.hypot(d.x, d.y)), math.atan2(d.y, d.x))
            T.wobble(o, 0.012 * h, 6.0, int(p.x * 50 + p.y * 30))
        blob('snowtip', (x, y, z + h * 1.0), (0.04 * h, 0.04 * h, 0.03 * h), SN, sub=1, seg=10)

# ------------------------------------------------------------------ kayak askısı + kayaklar + batonlar

def ski(loc, yaw, lean, c1, c2, L=1.5, name='ski'):
    """Kayak: ince uzun gövde (ön ucu yukarı kıvrık), ortada bağlama (topuk + burun parçası, tokalı), üstte renkli şerit."""
    W = 0.085; Tk = 0.022; n = 22
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    def prof(s):            # s: 0 arka → 1 ön; z kıvrımı ön uçta
        tip = smoothstep(0.82, 1.0, s); z = 0.16 * tip * tip
        w = W * (1 - 0.18 * math.sin(math.pi * s)) * (0.55 + 0.45 * (1 - smoothstep(0.93, 1.0, s)))
        return z, w
    rows = []
    for i in range(n + 1):
        s = i / n; z, w = prof(s); yy = (s - 0.5) * L
        rows.append([bm.verts.new((sx * w, yy, z + sz * Tk)) for (sx, sz) in ((-1, 0), (1, 0), (1, 1), (-1, 1))])
    for i in range(n):
        for k in range(4):
            k2 = (k + 1) % 4; f = bm.faces.new((rows[i][k], rows[i][k2], rows[i + 1][k2], rows[i + 1][k]))
            for lp, uv in zip(f.loops, ((k / 4, i / n), (k2 / 4, i / n), (k2 / 4, (i + 1) / n), (k / 4, (i + 1) / n))): lp[uvl].uv = uv
    bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1])
    def b(nt, bsdf):
        N = nt.nodes; Lk = nt.links; uv = kit.uv_node(nt); sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(uv.outputs[0], sep.inputs[0])
        st = N.new('ShaderNodeMath'); st.operation = 'PINGPONG'; st.inputs[1].default_value = 0.5; Lk.new(sep.outputs['X'], st.inputs[0])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.18; mr.inputs['From Max'].default_value = 0.2; Lk.new(st.outputs[0], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = srgb(c2); mx.inputs[7].default_value = srgb(c1)
        Lk.new(mr.outputs[0], mx.inputs['Factor']); Lk.new(mx.outputs[2], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.35; bsdf.inputs['Coat Weight'].default_value = 0.5
    o = link_mesh(name, bm, [nodes_mat('ski_' + c1, b)]); smooth(o, False)
    IR = m_metal('#3b3f48', name='binding')
    parts = [o,
             rbox('bind_toe', (0, 0.12, Tk + 0.03), (0.12, 0.1, 0.05), IR, bevel=0.012),
             rbox('bind_heel', (0, -0.16, Tk + 0.035), (0.11, 0.13, 0.06), IR, bevel=0.012),
             rbox('bind_lever', (0, -0.25, Tk + 0.06), (0.05, 0.08, 0.015), mat('lever', c1, 0.3, 0.4), bevel=0.006)]
    em = bpy.data.objects.new(name + '_root', None); bpy.context.scene.collection.objects.link(em)
    for p in parts: p.parent = em
    em.location = loc; em.rotation_euler = (math.radians(lean), 0, math.radians(yaw))
    return em

def pole(base, top, c, name='pole'):
    tube(name, [base, top], [0.014, 0.014], m_metal('#9aa2ad', name='polem'), res=2)
    d = V(top) - V(base)
    blob('grip', tuple(V(top) - d.normalized() * 0.06), (0.025, 0.025, 0.07), mat('grip', c, 0.4, 0.2), sub=1, seg=10)
    rr = blob('basket', tuple(V(base) + d.normalized() * 0.09), (0.06, 0.06, 0.012), mat('basket', '#2b2f36', 0.5, 0.1), sub=1, seg=12)

def ski_rack(cx, cy, z, yaw=0.0):
    """Kayak sehpası: iki A ayak (çapraz bağlı, ayak uçlarında kar birikintisi) + üst kiriş + alt dayama çıtası; 3 çift kayak
    kirişe yaslı, iki çift baton asılı. Ahşap yıpranmış (m_wood aşınmış boya)."""
    WD = m_wood('#9a6a40', 'rackwood', age=1.2); WD2 = m_wood('#b5814f', 'rackbar', paint='#d6463c', age=1.0)
    y0 = math.radians(yaw); fw = V((math.cos(y0), math.sin(y0), 0)); sd = V((-math.sin(y0), math.cos(y0), 0))
    P = lambda a, b, h: V((cx, cy, z)) + fw * a + sd * b + V((0, 0, h))
    for sx in (-1, 1):                       # A ayaklar
        post('legf', P(0.35, sx * 0.9, -0.05), P(0.0, sx * 0.9, 1.25), 0.04, WD, seed=sx)
        post('legb', P(-0.35, sx * 0.9, -0.05), P(0.0, sx * 0.9, 1.25), 0.04, WD, seed=sx + 3)
        post('brace', P(0.22, sx * 0.9, 0.45), P(-0.22, sx * 0.9, 0.45), 0.022, WD, seed=sx + 7)
        blob('snowfoot', tuple(P(0.35, sx * 0.9, 0.0)), (0.12, 0.1, 0.05), m_snow('snow_v4'), sub=1, seg=10)
        blob('snowfoot', tuple(P(-0.35, sx * 0.9, 0.0)), (0.12, 0.1, 0.05), m_snow('snow_v4'), sub=1, seg=10)
    tube('beam', [tuple(P(0.0, -1.05, 1.22)), tuple(P(0.0, 1.05, 1.22))], [0.045, 0.045], WD2, res=2)
    tube('rail', [tuple(P(0.42, -1.0, 0.18)), tuple(P(0.42, 1.0, 0.18))], [0.03, 0.03], WD, res=2)
    blob('beamsnow', tuple(P(0.0, 0.0, 1.27)), (0.06, 1.0, 0.03), m_snow('snow_v4'), sub=1, seg=12)
    cols = [('#e8463c', '#ffffff'), ('#2f8adf', '#ffd34a'), ('#3fbf6a', '#ffffff')]
    for k, (c1, c2) in enumerate(cols):
        for pair in (-0.06, 0.06):
            b = -0.6 + k * 0.6 + pair
            base = P(0.5, b, 0.12); top = P(0.04, b, 1.35)
            dvec = top - base
            yawd = math.degrees(math.atan2(dvec.y, dvec.x)) - 90
            lean = math.degrees(math.atan2(math.hypot(dvec.x, dvec.y), dvec.z))
            em = ski(tuple((base + top) / 2), 0, 0, c1, c2, L=dvec.length + 0.05, name=f'ski{k}{pair}')
            em.rotation_mode = 'XYZ'
            q = dvec.normalized().to_track_quat('Y', 'Z'); em.rotation_mode = 'QUATERNION'; em.rotation_quaternion = q
    for k, c in enumerate(('#ffd34a', '#e8463c')):
        for pair in (-0.03, 0.03):
            b = 0.95 - k * 0.12 + pair
            pole(tuple(P(-0.45, b, 0.05)), tuple(P(-0.02, b, 1.3)), c, name=f'pole{k}{pair}')

def snowman(loc, s=1.0):
    SN = m_snow('snow_v4'); x, y, z = loc
    blob('sm1', (x, y, z + 0.28 * s), (0.3 * s,) * 3, SN, sub=2, seg=16)
    blob('sm2', (x, y, z + 0.7 * s), (0.21 * s,) * 3, SN, sub=2, seg=16)
    blob('sm3', (x, y, z + 1.0 * s), (0.15 * s,) * 3, SN, sub=2, seg=16)
    blob('nose', (x - 0.16 * s, y, z + 1.0 * s), (0.08 * s, 0.025 * s, 0.025 * s), mat('carrot', '#f08a2a', 0.4, 0.1), sub=1, seg=10)
    for dy in (-0.05, 0.05): blob('eye', (x - 0.13 * s, y + dy * s, z + 1.06 * s), (0.02 * s,) * 3, mat('coal', '#222222', 0.6, 0), sub=0, seg=8)
    tube('scarf', [(x, y - 0.17 * s, z + 0.86 * s), (x - 0.12 * s, y, z + 0.87 * s), (x, y + 0.17 * s, z + 0.86 * s)], [0.04 * s] * 3, mat('scarf', '#e8463c', 0.6, 0), res=6)

def signpost(x, y, z, yaw, arrows, tr=None):
    """Tabela: yıpranmış direk + ok biçimli levhalar (beyaz boyalı yazı yerine simge: dağ, bayrak, ev)."""
    WD = m_wood('#8a5c36', 'signwood', age=1.3)
    post('signpost', (x, y, z - 0.1), (x, y, z + 1.5), 0.05, WD, seed=int(x * 7))
    for k, (ang, c) in enumerate(arrows):
        a = math.radians(yaw + ang); zz = z + 1.25 - k * 0.28
        pts = [(0, 0.09), (0.55, 0.09), (0.7, 0), (0.55, -0.09), (0, -0.09)]
        o = prism('arrow', pts, 0.04, m_wood('#c99a62', 'signboard', paint=c, age=1.4), loc=(x + math.cos(a) * 0.03, y + math.sin(a) * 0.03, zz), bevel=0.01)
        o.rotation_euler = (0, 0, a)
    blob('signmoss', (x, y, z + 0.02), (0.14, 0.14, 0.05), m_flat('#4f7f36', 0.2, 10, 'moss'), sub=1, seg=10)

def add_okti(loc, yaw, height=1.6):
    if not os.path.exists(OKTI): return
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=OKTI)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    if arm and arm.animation_data: arm.animation_data.action = None
    root = next((o for o in new if o.parent is None), new[0])
    bpy.context.view_layer.update()
    zs = [ (o.matrix_world @ V(c)).z for o in new if o.type == 'MESH' for c in o.bound_box]
    hh = max(zs) - min(zs) if zs else 1
    root.scale = [root.scale[i] * height / hh for i in range(3)]
    root.location = loc; root.rotation_euler = (root.rotation_euler[0], root.rotation_euler[1], math.radians(yaw))

def lift_new(tr, before):
    """Zemin z=0 varsayan yardımcıların (çalı rozeti, çiçek) ürettiği nesneleri arazi yüksekliğine oturtur."""
    new = [o for o in bpy.context.scene.objects if o not in before and o.type in ('MESH', 'CURVE')]
    if not new: return
    bpy.ops.object.select_all(action='DESELECT')
    for o in new: o.select_set(True)
    bpy.context.view_layer.objects.active = new[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in bpy.context.selected_objects:
        for v in o.data.vertices: v.co.z += tr.h(v.co.x, v.co.y)

def heather(x, y, z, seed):
    """Kar kenarı: seyrek kuru ot + funda (kahve-zeytin yapraklar, minik mor çiçek)."""
    R = random.Random(seed)
    DRY = m_leaf('#6b5a32', '#8f7c45', '#b8a464', '#c9b77a', 'dryg')
    def build(bm):
        out = []
        for j in range(R.randint(9, 14)):
            b_ = R.uniform(0, 6.28); up = R.uniform(0.55, 0.95)
            d = V((math.cos(b_) * (1 - up), math.sin(b_) * (1 - up), up)).normalized(); side = V((-math.sin(b_), math.cos(b_), 0))
            for f in blade(bm, V((x, y, z)), d, side, R.uniform(0.14, 0.26), 0.012, 0.5, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('heather', build, [DRY])
    PU = m_flat('#9a6fb0', 0.15, 10, 'heathf')
    for q in range(R.randint(2, 5)):
        blob('hf', (x + R.uniform(-0.08, 0.08), y + R.uniform(-0.08, 0.08), z + R.uniform(0.08, 0.16)), (0.025, 0.025, 0.04), PU, sub=0, seg=6)

def fern(x, y, z, seed, size=0.55):
    """Yamaç: eğrelti — kemerli yapraklar, iki yanda küçük yaprakçıklar (palmiye yaprağının küçüğü)."""
    R = random.Random(seed)
    FL = m_leaf('#2a6b34', '#3f8f40', '#78bf5a', '#9cd474', 'fern')
    def build(bm):
        out = []
        for q in range(R.randint(6, 9)):
            a = q * 6.28 / 7 + R.uniform(-0.3, 0.3); d = V((math.cos(a), math.sin(a), 0)); side = V((-d.y, d.x, 0)); L = size * R.uniform(0.8, 1.15)
            def C(s, d=d, L=L): return V((x, y, z)) + d * (L * s * 0.8) + V((0, 0, L * (0.9 * s - 0.95 * s * s)))
            for j in range(9):
                s_ = 0.12 + 0.86 * j / 9; c = C(s_); tan = (C(min(1, s_ + 0.04)) - c).normalized()
                for sgn in (-1, 1):
                    dd = (tan * 0.4 + side * sgn).normalized()
                    for f in blade(bm, c, dd, V((0, 0, 1)).cross(dd).normalized(), L * 0.2 * (1 - 0.6 * s_), 0.03 * size, 0.2, segs=2): out.append((f, 0))
        return out
    mesh_from_blades('fern', build, [FL])

def biome_scatter(tr, area, seed, step=0.9, avoid=None):
    """Bölgeye göre bitki grupları: kar kenarı (seyrek kuru ot/funda), soğuk çim (seyrek ot), yamaç (sık eğrelti + ot), düz çim (ot öbeği)."""
    R = random.Random(seed); n = 0
    x0, x1, y0, y1 = area
    yy = y0
    while yy < y1:
        xx = x0
        while xx < x1:
            x = xx + R.uniform(-0.4, 0.4) * step; y = yy + R.uniform(-0.4, 0.4) * step; xx += step
            if avoid and avoid(x, y): continue
            s, rock, cool = tr.zones(x, y); z = tr.h(x, y) - 0.01; slope = 1 - tr.normal(x, y).z
            r = R.random()
            if s > 0.55: continue
            if 0.12 < s <= 0.55:
                if r < 0.22: heather(x, y, z, seed + n); n += 1
            elif rock > 0.5:
                if r < 0.1: pebble((x, y, z + 0.04), R.uniform(0.08, 0.16), m_rock(), seed + n); n += 1
            elif slope > 0.08:
                if r < 0.28: fern(x, y, z, seed + n, R.uniform(0.4, 0.7)); n += 1
                elif r < 0.5: lush((x, y, z), 0.1, 1, seed + n, h=(0.16, 0.3)); n += 1
            else:
                if r < (0.18 if cool > 0.3 else 0.32): lush((x, y, z), 0.12, 1, seed + n, h=(0.16, 0.32)); n += 1
        yy += step
    return n

def snowflakes(area, z0, z1, count, seed):
    """Uçuşan küçük kar taneleri (yumuşak parlak noktalar)."""
    R = random.Random(seed); FL = mat('flake', '#ffffff', 0.4, 0.0, emit=0.6)
    bm = bmesh.new()
    for k in range(count):
        c = V((R.uniform(area[0], area[1]), R.uniform(area[2], area[3]), R.uniform(z0, z1))); r = R.uniform(0.018, 0.04)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r, matrix=__import__('mathutils').Matrix.Translation(c))
    link_mesh('flakes', bm, [FL])

def scatter_grass(tr, n, seed, area, avoid=None, snow_max=0.15):
    R = random.Random(seed); placed = 0; tries = 0
    while placed < n and tries < n * 20:
        tries += 1
        x = R.uniform(area[0], area[1]); y = R.uniform(area[2], area[3])
        if tr.snow_w(x, y) > snow_max or (avoid and avoid(x, y)): continue
        if tr.normal(x, y).z < 0.8: continue
        lush((x, y, tr.h(x, y) - 0.01), 0.12, 1, seed + placed, h=(0.18, 0.34)); placed += 1

def light(sc, sun_yaw=-35, exp=-0.45):
    sc.view_settings.exposure = exp
    for o in sc.objects:
        if o.type == 'LIGHT' and o.data.type == 'SUN': o.rotation_euler = (math.radians(50), 0, math.radians(sun_yaw)); o.data.energy = 3.4

# ------------------------------------------------------------------ sahneler

def scene_ski(out):
    sc = kit.reset(); sc.cycles.samples = 40; light(sc)
    # oyundaki karlı tepe (regions.json hills: x −23.8, z 28.8, h 6, r 5.2) yerel koordinatta (0, 4); kayak tepesi yamacına taşınır
    tr = Terrain([(0.0, 4.0, 6.0, 5.2, True), (9.5, -6.0, 1.2, 4.0, False)], 30, 0, 0, res=170)
    tr.build()
    SNW = m_snow('snow_v4')
    # pist: tepeden güneye kıvrılarak inen, ezilmiş kar şeridi (açık mavi kenar çizgili) — arazi rengini bozmaz, üstüne oturur
    def pist_m():
        def b(nt, bsdf):
            N = nt.nodes; L = nt.links; uv = kit.uv_node(nt); sep = N.new('ShaderNodeSeparateXYZ'); L.new(uv.outputs[0], sep.inputs[0])
            ed = N.new('ShaderNodeMath'); ed.operation = 'PINGPONG'; ed.inputs[1].default_value = 0.5; L.new(sep.outputs['X'], ed.inputs[0])
            mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.08; L.new(ed.outputs[0], mr.inputs['Value'])
            gr = N.new('ShaderNodeMath'); gr.operation = 'SINE'; mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 60
            L.new(sep.outputs['Y'], mm.inputs[0]); L.new(mm.outputs[0], gr.inputs[0])
            g2 = N.new('ShaderNodeMapRange'); g2.inputs['From Min'].default_value = -1; g2.inputs['To Min'].default_value = 0.94; g2.inputs['To Max'].default_value = 1.0; L.new(gr.outputs[0], g2.inputs['Value'])
            base = ramp(nt, [(0.0, '#9cc0ea'), (1.0, '#f4f8ff')]); L.new(mr.outputs[0], base.inputs['Fac'])
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            L.new(base.outputs[0], mx.inputs[6]); L.new(g2.outputs[0], mx.inputs[7]); L.new(mx.outputs[2], bsdf.inputs['Base Color'])
            bsdf.inputs['Roughness'].default_value = 0.55
        return nodes_mat('pist', b)
    pts = [(0.2 + 1.4 * math.sin(t * 2.6), 3.6 - 9.0 * t) for t in [i / 40 for i in range(41)]]
    drape(tr, pts, lambda s: 0.85 + 0.35 * s, pist_m(), lift=0.04, name='pist', uvlen=0.25)
    # kapı bayrakları pist kenarında
    DK = m_wood('#7a5232', 'skipole'); BL = m_flat('#2f8adf', 0.08, 8, 'blueflag'); RD = m_flat('#ff5a5a', 0.08, 8, 'redflag')
    for k in range(1, 9):
        x, y = pts[k * 4]; nx = 1.0 + 0.3 * k / 9
        for sx in (-1, 1):
            xx = x + sx * nx; z = tr.h(xx, y)
            tube('gate', [(xx, y, z - 0.05), (xx, y, z + 0.55)], [0.018, 0.018], DK, res=2)
            prism('pf', [(0, 0), (0.22 * sx, -0.06), (0, -0.14)], 0.01, BL if k % 2 else RD, loc=(xx, y, z + 0.53), bevel=0.003)
    # başlangıç: tepe yakınında ahşap kapı + kırmızı bayrak
    zt = tr.h(0.2, 3.9); WDG = m_wood('#b98a5a', 'gbarp', paint='#ff5a5a', age=1.3)
    for sx in (-1, 1): post('gp', (0.2 + sx * 0.75, 3.9, zt - 0.2), (0.2 + sx * 0.75, 3.9, zt + 1.15), 0.06, m_wood('#7a5232', 'gpost', age=1.3), seed=sx)
    plank('gbar', (0.2, 3.9, zt + 1.1), (1.75, 0.1, 0.22), WDG, seed=3)
    blob('gsnow', (0.2, 3.9, zt + 1.24), (0.9, 0.08, 0.05), SNW, sub=1, seg=12)
    tube('fpole', [(1.4, 4.6, tr.h(1.4, 4.6) - 0.1), (1.4, 4.6, tr.h(1.4, 4.6) + 1.6)], [0.03, 0.025], DK, res=2)
    prism('flag', [(0, 0), (0.6, -0.12), (0, -0.3)], 0.015, RD, loc=(1.42, 4.6, tr.h(1.4, 4.6) + 1.55), bevel=0.004)
    # alt: oyun girişi alanı — kayak sehpası, kızak, kardan adam, tabela (kar ile çim arasındaki kırağılı bant)
    ski_rack(3.2, -5.6, tr.h(3.2, -5.6), yaw=-20)
    snowman((-2.6, -4.4, tr.h(-2.6, -4.4)), 1.0)
    signpost(1.6, -7.3, tr.h(1.6, -7.3), 70, [(0, '#e8463c'), (150, '#2f8adf')])
    # çamlar: karda karlı, geçişte yarı karlı, çimde yeşil
    R = random.Random(5)
    spots = [(-3.4, 2.0, 2.4), (3.6, 1.6, 2.6), (-2.9, 6.8, 2.2), (3.0, 6.5, 2.0), (-4.6, -1.8, 2.6), (4.8, -2.2, 2.3),
             (-6.0, 3.2, 2.8), (6.4, 3.6, 2.5), (-6.8, -5.6, 3.0), (7.2, -4.6, 2.7), (-1.0, 9.0, 2.0), (5.8, 8.6, 2.2)]
    for (x, y, h) in spots:
        s = tr.snow_w(x, y)
        pine_v4((x, y, tr.h(x, y) - 0.05), h, int(x * 13 + y * 7), snow=s > 0.25)
    near_pist = lambda x, y: min(math.hypot(x - px, y - py) for (px, py) in pts[::2]) < 1.6
    print('biyom bitkileri', biome_scatter(tr, (-13, 13, -14, 9), 31, step=0.85, avoid=lambda x, y: near_pist(x, y) or math.hypot(x - 3.2, y + 5.6) < 1.6))
    snowflakes((-9, 9, -10, 10), 0.6, 8, 380, 3)
    for k in range(8):
        x, y = R.uniform(-10, 10), R.uniform(-13, -6)
        if tr.snow_w(x, y) < 0.1: pebble((x, y, tr.h(x, y) + 0.03), R.uniform(0.08, 0.16), m_rock(), 70 + k)
    add_okti((-0.6, -6.2, tr.h(-0.6, -6.2)), 200)
    print('tris', kit.tri_count([o for o in sc.objects if o.type == 'MESH']))
    kit.shoot(sc, os.path.join(out, 'after_ski.png'), (0.6, -1.0, 2.2), 27, -24, 34, lens=40, size=(1280, 800))

def scene_mountain(out):
    sc = kit.reset(); sc.cycles.samples = 40; light(sc, -30)
    # oyundaki dağ tepesi (x 5, z 37, h 8, r 6.3) yerel (0, 5); dağ oyunu girişi güney eteğinde, patika tepeye sarmal çıkar
    tr = Terrain([(0.0, 5.0, 8.0, 6.3, False), (-6.0, 9.0, 3.5, 3.5, False), (7.0, 8.0, 2.8, 3.2, False)], 34, 0, 1.5, res=180)
    tr.build()
    STN = m_rock(); HILL = m_rock(moss_th=(0.62, 0.85), grass=('#4f8a35', '#6aa645', '#9ccc5e'), warm=('#8f7f70', '#a8957f', '#c4ab8e'), name='crag')
    R = random.Random(9)
    # kaya çıkıntıları: arazinin içinden yarı gömülü (zemine "konmuş" değil); dik yamaçlarda
    for k in range(16):
        a = R.uniform(0, 6.28); r = R.uniform(1.2, 5.0); x, y = math.cos(a) * r, 5 + math.sin(a) * r * 0.9
        if tr.normal(x, y).z > 0.9 and r < 3.5: continue
        rr = R.uniform(0.4, 1.0); z = tr.h(x, y) - rr * 0.45
        rock((x, y, z), rr, HILL, 100 + k, sq=(1.2, 1.0, 0.7), sub=3, amt=0.18)
    # zirve: taş yığını (kerevit/kurgan) + bayrak
    zt = tr.h(0, 5)
    for k, (dx, dy, rr) in enumerate(((0, 0, 0.45), (0.25, 0.1, 0.32), (-0.1, -0.15, 0.3), (0.05, 0.02, 0.24))):
        rock((dx, 5 + dy, zt + 0.1 + k * 0.28), rr, STN, 200 + k, sq=(1.0, 1.0, 0.7), sub=2, amt=0.1)
    tube('pole', [(0.1, 5.1, zt + 0.6), (0.1, 5.1, zt + 2.3)], [0.035, 0.03], m_wood('#7a5232', 'mpole', age=1.2), res=2)
    prism('flag', [(0, 0), (0.8, -0.15), (0, -0.4)], 0.02, m_flat('#ff5a5a', 0.08, 8, 'redflag'), loc=(0.13, 5.1, zt + 2.25), bevel=0.005)
    # sarmal patika: etekten zirveye (toprak + kenar taşları + dik yerde ahşap basamak)
    DIRT = m_sand('mpath', '#c9a272')
    pts = []
    for i in range(90):
        t = i / 89; a = -math.pi / 2 + t * 2.4 * math.pi; r = 7.2 * (1 - t) + 0.9 * t
        pts.append((math.cos(a) * r, 5 + math.sin(a) * r * 0.92))
    pts = [(1.0, -4.5), (0.6, -3.2)] + pts
    drape(tr, pts, 0.42, DIRT, lift=0.03, name='trail', uvlen=0.5)
    WD = m_wood('#8a5c36', 'step', age=1.3)
    for k in range(2, len(pts) - 1, 3):
        x, y = pts[k]; x2, y2 = pts[k + 1]
        dz = tr.h(x2, y2) - tr.h(x, y); dist = math.hypot(x2 - x, y2 - y) or 1
        if abs(dz / dist) > 0.35:                              # dik: basamak
            tx, ty = (x2 - x) / dist, (y2 - y) / dist
            o = plank('step', (x, y, tr.h(x, y) + 0.06), (0.9, 0.12, 0.08), WD, rot=(0, 0, math.degrees(math.atan2(ty, tx)) + 90), seed=k)
        for sgn in (-1, 1):
            if R.random() < 0.55:
                tx, ty = (x2 - x) / dist, (y2 - y) / dist; sx, sy = -ty * sgn, tx * sgn
                px, py = x + sx * 0.55, y + sy * 0.55
                pebble((px, py, tr.h(px, py) + 0.02), R.uniform(0.07, 0.13), STN, 300 + k * 2 + (sgn > 0))
    # patika başı (dağ oyunu girişi): ahşap kemer + tabela + bank + çanta
    bx, by = 1.2, -5.6; zb = tr.h(bx, by)
    WA = m_wood('#7a5232', 'arch', age=1.3)
    for sx in (-1, 1): post('ap', (bx + sx * 0.95, by, zb - 0.2), (bx + sx * 0.95, by, zb + 2.0), 0.08, WA, seed=sx)
    plank('archbar', (bx, by, zb + 1.85), (2.3, 0.14, 0.38), m_wood('#c99a62', 'archsign', paint='#3f8f4a', age=1.4), seed=2)
    for k, c in enumerate(('#ffd34a', '#ffffff', '#ffd34a')):          # levhada üç dağ simgesi (yazısız)
        prism('peak', [(-0.18, 0), (0, 0.22), (0.18, 0)], 0.02, m_flat(c, 0.05, 8, 'peak' + c), loc=(bx - 0.55 + k * 0.55, by - 0.08, zb + 1.72), bevel=0.004)
    signpost(-1.4, -4.4, tr.h(-1.4, -4.4), 30, [(0, '#3f8f4a'), (200, '#e8a23c')])
    signpost(-5.2, 2.4, tr.h(-5.2, 2.4), 60, [(0, '#3f8f4a')])
    plank('bench', (3.4, -4.6, tr.h(3.4, -4.6) + 0.42), (1.3, 0.35, 0.07), WD, rot=(0, 0, 15), seed=5)
    for sx in (-1, 1):
        post('bleg', (3.4 + sx * 0.5, -4.6, tr.h(3.4, -4.6) - 0.05), (3.4 + sx * 0.5, -4.6, tr.h(3.4, -4.6) + 0.4), 0.04, WD, seed=sx + 9)
    # sık orman: alt yamaçlarda çam kümeleri (patikayı açık bırakır), çalı, çiçek, ot
    def near_trail(x, y): return min(math.hypot(x - px, y - py) for (px, py) in pts[::3]) < 1.0
    placed = 0
    for k in range(140):
        if placed >= 34: break
        a = R.uniform(0, 6.28); r = R.uniform(4.0, 12.5); x, y = math.cos(a) * r, 5 + math.sin(a) * r
        if near_trail(x, y) or (abs(x - bx) < 2.5 and abs(y - by) < 2.5) or tr.normal(x, y).z < 0.78: continue
        if y < -6 and abs(x) < 6: continue                       # ön kısım açık (kamera)
        pine_v4((x, y, tr.h(x, y) - 0.05), R.uniform(2.0, 3.2), 400 + k, lod=0.6); placed += 1
    BL = m_leaf('#2f7a3a', '#4fa64a', '#8fcf67', '#bfe38e', 'bush')
    bushes = []
    for k in range(40):
        a = R.uniform(0, 6.28); r = R.uniform(2.0, 10); x, y = math.cos(a) * r, 5 + math.sin(a) * r
        if near_trail(x, y) and R.random() < 0.7: continue
        bushes.append((x, y))
    before = set(bpy.context.scene.objects)
    mesh_from_blades('bushes', rosette(bushes, R, sizes=(0.3, 0.5), leaves=9), [BL])
    flower_heads([(x / 0.9, y / 0.9, R.uniform(0.15, 0.25)) for (x, y) in [(R.uniform(-8, 8), R.uniform(-6, 2)) for _ in range(14)] if not near_trail(x, y)], R)
    lift_new(tr, before)
    print('biyom bitkileri', biome_scatter(tr, (-13, 13, -9, 16), 77, step=0.8, avoid=lambda x, y: near_trail(x, y) or (abs(x - bx) < 1.6 and abs(y - by) < 1.2)))
    add_okti((0.6, -3.6, tr.h(0.6, -3.6)), 190)
    print('tris', kit.tri_count([o for o in sc.objects if o.type == 'MESH']))
    kit.shoot(sc, os.path.join(out, 'after_mountain.png'), (0.0, 1.8, 3.2), 31, -18, 33, lens=40, size=(1280, 800))

def scene_pine(out):
    sc = kit.reset(); sc.cycles.samples = 32; light(sc)
    tr = Terrain([(0, 0, 0.2, 3, True)], 8, 0, 0, res=60); tr.build()
    pine_v4((-1.2, 0, tr.h(-1.2, 0)), 2.6, 3, snow=False)
    pine_v4((1.2, 0.3, tr.h(1.2, 0.3)), 2.6, 4, snow=True)
    print('pine tris (yeşil+karlı)', kit.tri_count([o for o in sc.objects if o.type == 'MESH' and o.name != 'terrain']))
    kit.shoot(sc, os.path.join(out, 'closeup_pines.png'), (0, 0, 1.4), 6.8, -12, 10, lens=50, size=(1280, 800))

def scene_skis(out):
    sc = kit.reset(); sc.cycles.samples = 48; light(sc)
    tr = Terrain([(0, 0, 0.1, 3, True)], 8, 0, 0, res=50); tr.build()
    ski_rack(0, 0, tr.h(0, 0), yaw=-25)
    print('rack tris', kit.tri_count([o for o in sc.objects if o.type == 'MESH' and o.name != 'terrain']))
    kit.shoot(sc, os.path.join(out, 'closeup_skis.png'), (0, 0, 0.7), 4.6, -55, 18, lens=50, size=(1280, 800))

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    out = args[0]; os.makedirs(out, exist_ok=True)
    for s in (args[1:] or ['pine', 'skis', 'ski', 'mountain']):
        {'ski': scene_ski, 'mountain': scene_mountain, 'pine': scene_pine, 'skis': scene_skis}[s](out)
