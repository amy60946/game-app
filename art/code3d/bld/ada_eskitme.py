# Ada eskitmesi — Festival Alanı, Oyun Kulübesi ve Bahçe için ortak parçalar (24 Ekim 2026; kullanıcı: "haritadaki bütün yapılar
# ayrıntılı ve ada hayatına uygun eskitmeli olsun"). Oyun kamerası yapıya 8–14 m'den bakar ve yapı oyunda ~2,5 kat büyür: ayrıntı ancak
# geometride iri (taslakta ≥ 3–4 cm) ve renkte açık farkla okunur. Bu yüzden burada mikroskobik gürültü değil, okunur eskime parçaları var:
#   layer(m, fn)   var olan malzemenin taban rengine katman ekler (dünya konumundan: birleşik pişirme ağında da aynı yerde kalır)
#   salt / sunfade / base_moss   katmanlar: saçak/pervaz altı tuz izi, güneş solması, dipte (arka yüzde) yosun
#   m_canvas       çadır/tente kumaşı: şerit başına ton farkı (soluk değil canlı), dikiş çizgisi, çamur sıçraması, akıntı lekesi
#   m_patch        yama kumaşı + kesik dikiş; cloth_patch yüzeye oturan yama
#   m_moss / moss_clump, sand_mound / sand_ring, peg (çadır kazığı), bunting (flama ipi), rust_strap (paslı demir kayış)
#   clear_area     dress() süslerinden yeni bir parçanın altında kalanları siler (sınır kutusu bozulmasın diye dress aynı tohumla kurulur)
#   draft          taslağın (pişirmesiz) çizimi · bake: bld_kit.bake + iki yüz (ds) + üçgen sınırı denetimi
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import bld_kit as BK                     # code3d + v6 yollarını ekler
import bpy, bmesh
from mathutils import Vector as V, noise as mnoise
from mathutils.bvhtree import BVHTree
import kit
from kit import nodes_mat, ramp, uv_node, srgb, blob, rbox, tube
import assets_v3 as A
from assets_v3 import _shade, link_mesh, smooth, m_flat


# ------------------------------------------------------------------ malzeme katmanları

def wpos(G):
    g = G.n.new('ShaderNodeNewGeometry'); return g.outputs['Position']


def wxyz(G):
    sp = G.n.new('ShaderNodeSeparateXYZ'); G.l.new(wpos(G), sp.inputs[0]); return sp.outputs['X'], sp.outputs['Y'], sp.outputs['Z']


def layer(m, fn):
    """m'nin Base Color girişine bağlı rengi fn(G, renk) → yeni renk ile değiştirir (malzeme yerinde değişir)."""
    nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    inp = bsdf.inputs['Base Color']; G = A._G(nt)
    if inp.links: src = inp.links[0].from_socket
    else:
        rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = tuple(inp.default_value); src = rgb.outputs[0]
    nt.links.new(fn(G, src), inp)
    return m


def salt(z_top, z_len=0.45, amt=0.4, tint='#ece6d6', scale=16.0):
    """Saçak / pervaz altında aşağı akan soluk tuz-yağmur izleri: z_top'ta güçlü, z_len aşağıda biter (dünya z)."""
    def f(G, col):
        p = wpos(G); _, _, z = wxyz(G)
        st = G.rng(G.noise(G.mapping(p, (scale, scale, scale * 0.07)), 1.0, 3, 0.5), 0.52, 0.68)
        fade = G.rng(z, z_top - z_len, z_top - 0.03, 0, amt)
        cut = G.rng(z, z_top + 0.02, z_top - 0.01)
        return G.mix(G.math('MULTIPLY', G.math('MULTIPLY', st, fade), cut), col, tint)
    return f


def sunfade(amt=0.2, z0=None, z1=None, tint='#fff1d8', scale=1.3):
    """Güneş solması: geniş yumuşak lekeler (z0→z1 verilirse yukarı doğru artar). Beyaza değil sıcak açık tona, ölçülü."""
    def f(G, col):
        p = wpos(G)
        k = G.rng(G.noise(p, scale, 3, 0.5), 0.45, 0.72, 0, amt)
        if z0 is not None:
            _, _, z = wxyz(G); k = G.math('MULTIPLY', k, G.rng(z, z0, z1, 0.35, 1.0))
        return G.mix(k, col, tint)
    return f


def base_moss(z1=0.22, amt=0.75, back=(-0.4, 0.9), tint=('#4d7a2c', '#7aa23c')):
    """Dipte yosun: yerden z1'e doğru azalır, arka yüzde (+y, gölge) daha çok; yırtık sınır."""
    def f(G, col):
        p = wpos(G); _, y, z = wxyz(G)
        zn = G.math('ADD', z, G.math('MULTIPLY', G.noise(p, 7, 4), 0.12))
        k = G.math('MULTIPLY', G.rng(zn, z1, 0.02, 0, amt), G.rng(y, back[0], back[1], 0.25, 1.0))
        k = G.math('MULTIPLY', k, G.rng(G.noise(p, 11, 3), 0.42, 0.56))
        moss = G.mix(G.rng(G.noise(p, 30, 2), 0.4, 0.65), tint[0], tint[1])
        return G.mix(k, col, moss)
    return f


def grime(z1=0.18, amt=0.45, tint='#6b5236'):
    """Toprak sıçraması: yerden z1'e kadar koyu, lekeli (yağmurda sıçrayan kum/çamur)."""
    def f(G, col):
        p = wpos(G); _, _, z = wxyz(G)
        zn = G.math('ADD', z, G.math('MULTIPLY', G.noise(p, 9, 5), 0.08))
        k = G.math('MULTIPLY', G.rng(zn, z1, 0.0, 0, amt), G.rng(G.noise(p, 22, 3), 0.35, 0.6, 0.45, 1.0))
        return G.mix(k, col, tint)
    return f


def m_canvas(c1, c2, stripes=8.0, name='canvas', u0=0.0, mud=0.16, drip=None, fade=0.16, seam='#7d4b3a', var=0.07, bleach=None, stain=None):
    """Çadır kumaşı (grain uv: u çevre 0..1, v yukarı). Şeritler (iki renk), her şerit kendi tonunda (biri güneşte biraz açılmış),
    şerit arasında dikiş çizgisi, ince dokuma; dipte çamur sıçraması (dünya z < mud), drip=z verilirse oradan aşağı akıntı lekesi,
    bleach=(z0, z1, oran): c1 şeritleri yukarı doğru güneşte açılır; stain=(z0, z1): o bantta çay rengi su lekeleri (saçak boyu).
    Renk canlı kalır: solma beyaza değil, rengin açık tonuna."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        x = G.math('ADD', G.math('MULTIPLY', sep.outputs['X'], stripes * 2.0), u0 * stripes * 2.0)
        fr = G.math('FRACT', x); pid = G.math('FLOOR', x)
        odd = G.math('FRACT', G.math('MULTIPLY', pid, 0.5))                 # 0 → c1, 0.5 → c2
        is1 = G.math('LESS_THAN', odd, 0.25)
        wn = n.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '1D'; l.new(pid, wn.inputs['W'])
        r = wn.outputs['Value']
        c1v = G.mix(r, _shade(c1, 1.0 - var), _shade(c1, 1.0 + var))
        c1v = G.mix(G.rng(r, 0.6, 0.85, 0, fade), c1v, _shade(c1, 1.24))   # birkaç şerit güneşte açılmış
        if bleach:
            c1v = G.mix(G.rng(wxyz(G)[2], bleach[0], bleach[1], 0, bleach[2]), c1v, _shade(c1, 1.3))
        c2v = G.mix(r, _shade(c2, 1.0 - var * 0.5), _shade(c2, 1.0 + var * 0.3))
        col = G.mix(is1, c2v, c1v)
        # dikiş: şerit kenarında ince koyu çizgi + yanında açık iz
        edge = G.math('MINIMUM', fr, G.math('SUBTRACT', 1.0, fr))
        col = G.mix(G.rng(edge, 0.03, 0.012, 0, 0.55), col, seam, 'MULTIPLY')
        col = G.mix(G.rng(edge, 0.035, 0.05, 0.12, 0.0), col, '#fff6e6')
        o = G.obj()
        col = G.mix(0.12, col, G.noise(G.mapping(uv.outputs[0], (180, 60, 1)), 1.0, 2, out='Color'), 'OVERLAY')
        col = G.mix(G.rng(G.noise(o, 1.4, 3), 0.55, 0.75, 0, 0.12), col, _shade(c2, 1.03))      # geniş hafif solma
        if drip is not None:
            p = wpos(G); _, _, z = wxyz(G)
            st = G.rng(G.noise(G.mapping(p, (14, 14, 1.0)), 1.0, 3), 0.55, 0.7)
            k = G.math('MULTIPLY', st, G.rng(z, drip - 0.6, drip - 0.03, 0, 0.55))
            col = G.mix(G.math('MULTIPLY', k, G.rng(z, drip + 0.01, drip - 0.01)), col, '#b88f68', 'MULTIPLY')
        if stain:
            p = wpos(G); _, _, z = wxyz(G)
            bl = G.rng(G.noise(p, 4.5, 4, 0.6), 0.5, 0.64)
            band = G.math('MULTIPLY', G.rng(z, stain[0], stain[0] + 0.03), G.rng(z, stain[1], stain[1] - 0.12))
            col = G.mix(G.math('MULTIPLY', G.math('MULTIPLY', bl, band), 0.45), col, '#a98159', 'MULTIPLY')
        if mud:
            col = grime(mud, 0.7, '#7a5a3c')(G, col)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_patch(hexc, thread='#5a3826', name='patch', dots=None):
    """Yama: kendi rengi + dokuma + kenara yakın kesik dikiş (grain uv 0..1); dots verilirse puantiye."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        uv = uv_node(nt); sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
        u, v = sep.outputs['X'], sep.outputs['Y']
        du = G.math('MINIMUM', u, G.math('SUBTRACT', 1.0, u)); dv = G.math('MINIMUM', v, G.math('SUBTRACT', 1.0, v))
        d = G.math('MINIMUM', du, dv)
        band = G.math('MULTIPLY', G.rng(d, 0.06, 0.08), G.rng(d, 0.13, 0.11))
        w = G.math('LESS_THAN', du, dv)
        s = G.math('ADD', G.math('MULTIPLY', v, w), G.math('MULTIPLY', u, G.math('SUBTRACT', 1.0, w)))
        dash = G.rng(G.math('SINE', G.math('MULTIPLY', s, 2 * math.pi * 6)), -0.15, 0.15)
        col = G.mix(G.rng(G.noise(G.obj(), 3, 3), 0.3, 0.7), _shade(hexc, 0.93), _shade(hexc, 1.06))
        if dots:
            dd = G.vor(G.mapping(uv.outputs[0], (5, 5, 1)), 1.0)
            col = G.mix(G.rng(dd, 0.24, 0.2), col, dots)
        col = G.mix(0.14, col, G.noise(G.mapping(uv.outputs[0], (90, 90, 1)), 1.0, 2, out='Color'), 'OVERLAY')
        col = G.mix(G.rng(d, 0.03, 0.0, 0, 0.35), col, '#f6ead2')                    # yıpranmış kenar
        col = G.mix(G.math('MULTIPLY', band, dash), col, thread)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_moss(name='moss'):
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 14, 4), 0.35, 0.7), '#3f6e25', '#6f9d36')
        col = G.mix(G.rng(G.noise(o, 38, 2), 0.58, 0.72, 0, 0.6), col, '#a9c35a')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_sandy(name='sandy', hexc='#dcc08c'):
    """Kum / talaş yığını: sıcak kum, açık-koyu benek, dipte nemli koyu kenar."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 9, 4), 0.35, 0.68), _shade(hexc, 0.9), _shade(hexc, 1.07))
        col = G.mix(G.rng(G.noise(o, 60, 2), 0.62, 0.72, 0, 0.5), col, '#f1e2bd')
        col = G.mix(G.rng(G.noise(o, 45, 2), 0.66, 0.74, 0, 0.35), col, '#9d8058')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


# ------------------------------------------------------------------ parçalar

def set_ds(o):
    """İnce kumaş/bayrak: pişirmeden sonra arka yüz eklensin (proxy_bake ds_low)."""
    me = o.data
    a = me.attributes.get('ds') or me.attributes.new('ds', 'INT', 'FACE')
    a.data.foreach_set('value', [1] * len(me.polygons))
    return o


def mesh_obj(name, verts, faces, mats, uvs=None, mat_idx=None, smooth_=True, ds=False):
    """Köşe/yüz listesinden nesne; uvs: yüz başına (u, v) listesi ('grain'). mat_idx: yüz başına malzeme sırası."""
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    if uvs is not None:
        lay = me.uv_layers.new(name='grain')
        for poly, fu in zip(me.polygons, uvs):
            for li, uv in zip(poly.loop_indices, fu): lay.data[li].uv = uv
    if mat_idx is not None: me.polygons.foreach_set('material_index', mat_idx)
    me.polygons.foreach_set('use_smooth', [smooth_] * len(me.polygons))
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for m in mats: o.data.materials.append(m)
    if ds: set_ds(o)
    return o


def moss_clump(loc, r, seed=0, n=3, flat=0.42, m=None):
    """Yosun yastığı: 2–4 basık, yumrulu topak (köşe diplerine, tahta aralarına). r: yarıçap."""
    R = random.Random(seed); M = m or m_moss(); out = []
    for k in range(n):
        a = R.uniform(0, 6.28); d = r * 0.55 * (k > 0)
        rr = r * R.uniform(0.55, 0.9)
        o = blob('mossclump', (loc[0] + math.cos(a) * d, loc[1] + math.sin(a) * d, loc[2] + rr * flat * 0.3), (rr, rr * R.uniform(0.8, 1.0), rr * flat), M, sub=1, seg=10)
        A.smooth(o); bpy.context.view_layer.update()
        import assets_town as AT
        AT.wobble(o, rr * 0.22, 8.0, seed * 7 + k)
        out.append(o)
    return out


def sand_mound(cx, cy, rx, ry, h, seed=0, m=None, name='sandmound', n=20, rings=4):
    """Yere yayılmış alçak kum/toprak tümseği (kenarı yırtık, ortası tepecik)."""
    R = random.Random(seed); M = m or m_sandy()
    verts = [(cx, cy, h)]; faces = []
    for j in range(1, rings + 1):
        t = j / rings
        for i in range(n):
            a = i / n * 2 * math.pi
            k = 1 + 0.2 * mnoise.noise(V((math.cos(a) * 1.6, math.sin(a) * 1.6, seed + 0.3))) if j == rings else 1 + 0.08 * mnoise.noise(V((math.cos(a) * 2, math.sin(a) * 2, seed + j)))
            z = h * (1 - t * t) ** 1.4 + (0.004 if j == rings else 0.0)
            verts.append((cx + math.cos(a) * rx * t * k, cy + math.sin(a) * ry * t * k, z))
    for i in range(n): faces.append((0, 1 + i, 1 + (i + 1) % n))
    for j in range(rings - 1):
        b0 = 1 + j * n; b1 = 1 + (j + 1) * n
        for i in range(n):
            i2 = (i + 1) % n; faces.append((b0 + i, b1 + i, b1 + i2, b0 + i2))
    return mesh_obj(name, verts, faces, [M])


def sand_ring(cx, cy, radius_fn, width, h, seed=0, m=None, a0=0.0, a1=2 * math.pi, n=64, name='sanddrift'):
    """Duvar dibine yığılmış kum: iç kenar duvara yaslı (h yüksekliğinde), dışa doğru sıfıra iner; radius_fn(a) duvar yarıçapı.
    a0..a1 yay aralığı (kapı önü açık kalsın)."""
    M = m or m_sandy(); verts = []; faces = []
    rows = 4; cols = n + 1
    for i in range(cols):
        a = a0 + (a1 - a0) * i / n
        nn = mnoise.noise(V((math.cos(a) * 2.2, math.sin(a) * 2.2, seed)))
        hh = h * max(0.12, min(1.0, 0.55 + 0.9 * nn))
        ww = width * max(0.25, 0.85 + 0.9 * mnoise.noise(V((math.cos(a) * 3.1, math.sin(a) * 3.1, seed + 5))))
        if a1 - a0 < 2 * math.pi - 1e-3:
            e = min(i, n - i) / max(1, n * 0.08); hh *= min(1.0, e); ww *= 0.5 + 0.5 * min(1.0, e)
        r0 = radius_fn(a) - 0.015
        for j in range(rows):
            t = j / (rows - 1)
            verts.append((cx + math.cos(a) * (r0 + ww * t), cy + math.sin(a) * (r0 + ww * t), max(0.003, hh * (1 - t) ** 1.6) - 0.004 * t))
    for i in range(n):
        for j in range(rows - 1):
            a_, b_ = i * rows + j, (i + 1) * rows + j
            faces.append((a_, b_, b_ + 1, a_ + 1))
    return mesh_obj(name, verts, faces, [M])


def peg(x, y, away=(0.0, 1.0), h=0.2, w=0.04, m=None, seed=0, sink=0.42, mound=True):
    """Tahta çadır kazığı: kare gövde, geniş başlık, yükten (çadırdan) dışa eğik, yarısı kuma gömülü; dibinde küçük kum tümseği."""
    R = random.Random(seed); W = m or A.m_wood('#a27a4c', 'pegw')
    ax, ay = away; L = math.hypot(ax, ay) or 1.0; ax, ay = ax / L, ay / L
    tilt = R.uniform(14, 22)
    yaw = math.degrees(math.atan2(ay, ax))
    zc = h * (0.5 - sink)
    o = rbox('peg', (0, 0, 0), (w, w * 0.9, h), W, bevel=0.006)
    cap = rbox('peghead', (0, 0, 0), (w * 1.35, w * 1.25, w * 0.6), W, bevel=0.008)
    for p, dz in ((o, zc), (cap, zc + h / 2 + w * 0.2)):
        p.rotation_euler = (0, math.radians(tilt), math.radians(yaw))
        off = V((0, 0, dz)); off.rotate(p.rotation_euler)
        p.location = (x + off.x, y + off.y, off.z)
    out = [o, cap]
    if mound: out.append(sand_mound(x, y, w * 1.6, w * 1.4, 0.018, seed + 3, name='pegmound', n=12, rings=2))
    return out


def m_flag(hexc, faded=False, name=None):
    """Bayrak kumaşı: düz renk + dokuma; faded: güneşte açılmış (rengin açık tonu, beyaz değil)."""
    c = _shade(hexc, 1.16) if faded else hexc
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 6, 3), 0.3, 0.7), _shade(c, 0.94), _shade(c, 1.05))
        col = G.mix(G.rng(G.noise(o, 3, 3), 0.55, 0.75, 0, 0.25 if faded else 0.08), col, '#fff3dc')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name or ('flag' + c), b)


FLAG_COLORS = ('#f2bf45', '#36aab2', '#ee7a9c', '#86c25a', '#9a7ee0', '#f08a4b')


def bunting(p0, p1, sag, n, seed=0, size=0.1, colors=FLAG_COLORS, skip=(), torn=(), rope=None, thick=0.006, name='bunt'):
    """Flama ipi: sarkık ip + aşağı sarkan üçgen bayraklar (ortadan hafif katlı, ucu rastgele kıvrık, birkaçı solmuş;
    skip: eksik bayrak sırası, torn: ucu yırtık). Bayrak yüzleri iki yüzlü (ds)."""
    import assets_town as AT
    R = random.Random(seed); P0, P1 = V(p0), V(p1)
    def at(t): p = P0.lerp(P1, t); p.z -= sag * 4 * t * (1 - t); return p
    out = [tube(name + 'rope', [tuple(at(k / 6)) for k in range(7)], [thick] * 7, rope or AT.m_rope(), res=2)]
    out[-1].data.bevel_resolution = 1
    mats = {}
    verts = []; faces = []; mi = []; uvs = []; mlist = []
    for q in range(n):
        if q in skip: continue
        t0 = (q + 0.18) / n; t1 = (q + 0.82) / n
        a, b_ = at(t0), at(t1); mid = (a + b_) / 2
        d = (b_ - a).normalized(); side = d.cross(V((0, 0, 1))).normalized()
        L = size * R.uniform(1.05, 1.25)
        tip = mid + V((0, 0, -L)) + side * R.uniform(-0.25, 0.25) * L + d * R.uniform(-0.12, 0.12) * L
        fold = mid + side * R.uniform(0.04, 0.09) * L - V((0, 0, 0.004))
        c = colors[(q + seed) % len(colors)]; faded = R.random() < 0.35
        key = (c, faded)
        if key not in mats: mats[key] = len(mlist); mlist.append(m_flag(c, faded))
        base = len(verts)
        if q in torn:
            nt1 = mid + (tip - mid) * 0.7 + side * 0.02; nt2 = mid + (tip - mid) * 0.62 - d * 0.02
            verts += [a, fold, b_, nt1, nt2]
            faces += [(base, base + 1, base + 4), (base + 1, base + 2, base + 3), (base + 1, base + 3, base + 4)]
            uvs += [[(0, 1), (0.5, 1), (0.3, 0.3)], [(0.5, 1), (1, 1), (0.7, 0.3)], [(0.5, 1), (0.7, 0.3), (0.3, 0.3)]]
            mi += [mats[key]] * 3
        else:
            verts += [a, fold, b_, tip]
            faces += [(base, base + 1, base + 3), (base + 1, base + 2, base + 3)]
            uvs += [[(0, 1), (0.5, 1), (0.5, 0)], [(0.5, 1), (1, 1), (0.5, 0)]]
            mi += [mats[key]] * 2
    if faces:
        out.append(mesh_obj(name + 'flags', verts, faces, mlist, uvs=uvs, mat_idx=mi, smooth_=False, ds=True))
    return out


def rust_strap(p, nrm, length, w=0.03, axis=(1, 0, 0), m=None, rivets=2):
    """Paslı demir kayış (menteşe, kuşak): yüzeye yapışık ince yassı çubuk + perçinler; altında pas akıntısı (AT.nail)."""
    import assets_town as AT
    I = m or AT.m_metal('#4a4650', '#b0663a', 'strapm')
    n = V(nrm).normalized(); ax = V(axis).normalized()
    up = n.cross(ax).normalized()
    from mathutils import Matrix
    M = Matrix((ax, up, n)).transposed().to_4x4(); M.translation = V(p) + n * 0.006
    o = rbox('strap', (0, 0, 0), (length, w, 0.01), I, bevel=0.003)
    o.matrix_world = M
    out = [o]
    for k in range(rivets):
        t = (k + 0.5) / rivets - 0.5
        out.append(AT.nail(tuple(V(p) + ax * t * length * 0.85 + n * 0.008), tuple(n), I))
    return out


def clear_area(before, pred):
    """dress()'in eklediği (before kümesinde olmayan) nesnelerden merkezi pred(x, y) olanları siler."""
    gone = 0
    for o in [o for o in bpy.context.scene.objects if o.name not in before and o.type in ('MESH', 'CURVE')]:
        bb = [o.matrix_world @ V(c) for c in o.bound_box]
        cx = sum(c.x for c in bb) / 8; cy = sum(c.y for c in bb) / 8
        if pred(cx, cy): bpy.data.objects.remove(o); gone += 1
    return gone


# ------------------------------------------------------------------ çizim ve pişirme

def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = V((1e9,) * 3); hi = V((-1e9,) * 3)
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co; lo = V(map(min, lo, w)); hi = V(map(max, hi, w))
        e.to_mesh_clear()
    return lo, hi


def draft(png, yaw=35.0, pitch=24.0, size=(900, 700), samples=24):
    """Taslağın (pişirmesiz, tam ayrıntı) çizimi: render_low ile aynı çerçeve (sınır kutusu), kit.reset ışıkları."""
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    lo, hi = bounds(objs); ctr = (lo + hi) / 2; d = (hi - lo).length * 0.5 * 2.6
    sc = bpy.context.scene; sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = size
    cam = bpy.data.cameras.new('cam'); cam.lens = 50
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    yr, pr = math.radians(yaw), math.radians(pitch)
    co.location = ctr + V((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = png; bpy.ops.render.render(write_still=True)
    print('BOUNDS draft lo', tuple(round(x, 3) for x in lo), 'hi', tuple(round(x, 3) for x in hi), flush=True)


def bake(out, name, hi, decim, weights, cap, tex=1024, **kw):
    """bld_kit.bake + iki yüzlü ince parçalar (ds) + sınır: üçgen sayısı cap'i aşarsa uyarı (bütçe = cap × ds payı)."""
    cap = int(os.environ.get('POFI_TARGET', '0') or 0) or cap
    tris = BK.bake(out, name, hi, decim=decim, weights=weights, tex=tex, budget=kw.pop('budget', None), ds_low=True, **kw)
    print('SONUC', name, 'üçgen', tris, 'sınır', cap, 'AŞILDI' if tris > cap else 'tamam', flush=True)
    return tris


def args():
    """CLI: -- <çıktı> [ad] [--draft <png> [yaw]]   (export_game.py ikinci argüman olarak yapıcı adını verir; yok sayılır)"""
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = a[0] if a else '.'
    dr = None; yaw = 35.0
    if '--draft' in a:
        i = a.index('--draft'); dr = a[i + 1]
        if len(a) > i + 2: yaw = float(a[i + 2])
    return out, dr, yaw
