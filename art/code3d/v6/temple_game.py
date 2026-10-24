# Tapınak oyun modeli (24 Ekim 2026; kullanıcı: "eskitme ve premium ayrıntılar görünmüyor, çim ve taşlar zemin gibi ayrıntılı olsun,
# fenerlerin ayrıntısı görünmüyor"). assets_v6_game.py 'temple' bunu kullanır; taslak (kit3_v6.temple) kaynak, burası hedef.
#
# Neden kayboluyordu (karşılaştırma: scratchpad temple_v2/before): eski yol tüm avluyu tek ağa birleştirip smart_project ile
# açıyordu → binlerce küçük ada (püskül, kafes çıtası, konsol) dokunun ~%75'ini boşlukta bıraktı; çatı ~120 px'e, fener ~20 px'e
# düştü; üstelik oyun içe aktarıcısı yapı dokusunu 1024'e indiriyordu. Ot telleri bütçe yüzünden çıkarılmıştı, teras üstü düz boyaydı.
# Şimdi:
#   - hedef = taslağın aynı ağı (alt bölmesiz); yalnız çatılar ve fener gövdeleri kendi içinde sadeleşir (küresel sadeleştirme yok);
#   - teras üstleri 0,75 m ızgaraya bölünür, hiçbir yönden görünmeyen yüzler (üst terasın altı, bina içi) silinir;
#   - UV adaları önem katsayısıyla büyütülüp sıkı paketlenir (fener ×3,2, basamak/plaka ×1,6, saçak altı ×0,45 …);
#   - pişirmeden sonra teras üstlerine 3B çim öbekleri ve çiçek demetleri (adadaki GrassField tonunda) eklenir; renkleri dokunun
#     üst şeridindeki renk örneklerinden (UV'de ayrılmış şerit).
import math, random, re
import bpy, bmesh
import numpy as np
from mathutils import Vector as V

TEX = 2048
RESERVE = 72 / TEX          # UV üst şeridi: 3B çim/çiçek renk örnekleri (64 px boyanır, 8 px tampon)
STRIP = 64 / TEX
CELL = 64                   # renk örneği hücresi (px)

# nesne adı → UV yoğunluk katsayısı (doğrusal); ilk eşleşen
WEIGHTS = [
    (r'_lan(_[sp])?_body', 3.2), (r'_lan(_[sp])?_(cap|rim|top|knot)', 2.0), (r'_lan(_[sp])?_(tas|cord)', 0.8),
    (r'_roof\d*_(hip|ridge|curl|orn)', 1.0), (r'_roof\d*$', 1.25),
    (r'_(door|lat|frame|sill|win|wfr|wlat)$', 1.5), (r'_brk$', 1.4), (r'_cb$', 1.5), (r'_col$', 1.3), (r'_w$', 1.15),
    (r'_t\d_top', 1.0), (r'_t\d_face', 1.25), (r'_s\d_\d+$', 1.6), (r'_(slab|joint)$', 1.6), (r'_st\d+$', 1.8),
    (r'_wall_cap$', 1.0), (r'_wall$', 0.85), (r'_finial$', 2.0),
]
# nesne adı → kendi içinde sadeleştirme oranı (yumuşak eğriler; kutular olduğu gibi kalır)
DECIM = [(r'_roof\d*$', 0.42), (r'_lan(_[sp])?_body', 0.3), (r'_roof\d*_(hip|ridge)', 0.6)]   # dikili taşlar sadeleşmez (ışın kaçıp kara benek)

def _key(name):
    return re.sub(r'\.\d+$', '', name)

def _lookup(table, name, default):
    k = _key(name)
    for pat, v in table:
        if re.search(pat, k): return v
    return default

def _grid_top(me, cell=0.75):
    """Teras üstü (yelpaze + kenar dudağı) → merkez yelpazesi silinir, dış halka tek çokgen olur, x/y düzlemleriyle ızgaraya bölünür
    (dudak da aynı düzlemlerle kesilir: T birleşimi yok)."""
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    n = (len(bm.verts) - 1) // 2
    ring = [bm.verts[k] for k in range(n)]; centre = bm.verts[2 * n]
    bmesh.ops.delete(bm, geom=[centre], context='VERTS')
    bm.faces.new(ring)
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
    for axis, lo, hi in ((0, min(xs), max(xs)), (1, min(ys), max(ys))):
        k = math.floor(lo / cell) * cell + cell
        while k < hi:
            co = [0.0, 0.0, 0.0]; co[axis] = k; no = [0.0, 0.0, 0.0]; no[axis] = 1.0
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
            k += cell
    bm.to_mesh(me); bm.free()

def build_low(high, col=None):
    """Taslak nesnelerinden oyun hedefi: aynı ağ (alt bölmesiz), seçili parçalar kendi içinde sadeleşir, teras üstü ızgara;
    her yüze UV katsayısı ('uvw'; aşağı bakan yüz ×0,45); hepsi üçgen."""
    dg = bpy.context.evaluated_depsgraph_get(); out = []
    col = col or bpy.context.scene.collection
    for o in high:
        if o.type != 'MESH': continue
        ratio = _lookup(DECIM, o.name, 1.0)
        if ratio < 1.0:
            d = o.modifiers.new('dec_low', 'DECIMATE'); d.ratio = ratio; d.use_collapse_triangulate = True
            dg.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        if ratio < 1.0:
            o.modifiers.remove(o.modifiers['dec_low']); dg.update()
        if re.search(r'_t\d_top$', _key(o.name)): _grid_top(me)
        c = bpy.data.objects.new(o.name + '_low', me); c.matrix_world = o.matrix_world.copy(); col.objects.link(c)
        w = _lookup(WEIGHTS, o.name, 1.0)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        lay = bm.faces.layers.float.new('uvw'); bm.normal_update()
        mw3 = c.matrix_world.to_3x3()
        for f in bm.faces:
            nz = (mw3 @ f.normal).normalized().z if f.normal.length > 0 else 0.0
            f[lay] = w * (0.45 if nz < -0.5 else 1.0)
        bm.to_mesh(me); bm.free()
        out.append(c)
    return out

# ------------------------------------------------------------------ 3B çim öbekleri ve çiçekler (pişirmeden sonra eklenir)

def _srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return np.array([(x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c])

# hücre: (kök, orta, uç) — adadaki GrassField tonları (Pofi/Grass _Root/_Tip) ve taslağın çiçek renkleri
SWATCH = [
    ('#2f5420', '#567f33', '#8aab4f'),      # 0 çim (ada teli)
    ('#2a5222', '#4c8530', '#86b84e'),      # 1 gür çim
    ('#55662a', '#869442', '#c6c475'),      # 2 kuru uçlu çim
    ('#2d5a22', '#3d7a2e', '#5a9a3a'),      # 3 çiçek sapı
    ('#3a43b8', '#4b55c8', '#5a62d8'),      # 4 çan çiçeği (koyu mavi-mor, adadaki gibi)
    ('#4b4fc8', '#5e5fe0', '#7067e6'),      # 5
    ('#6258d8', '#7a72f0', '#8c84f2'),      # 6
    ('#3e3aa8', '#4a45c0', '#5650cc'),      # 7
    ('#e0742c', '#f08a3a', '#f39a48'),      # 8 turuncu
    ('#ea9638', '#f6a648', '#f8b458'),      # 9
    ('#e8b440', '#f4c454', '#f6cf64'),      # 10
    ('#de6a44', '#ee7a52', '#f28a60'),      # 11
    ('#e6e2d8', '#f6f3ea', '#ffffff'),      # 12 beyaz
    ('#e0589a', '#f06aa8', '#f47cb4'),      # 13 pembe
    ('#e8c030', '#f4cf3a', '#f7da5a'),      # 14 sarı
    ('#c8901c', '#e0a828', '#eab43a'),      # 15 çiçek göbeği
    ('#b88ad8', '#c79ae8', '#d4aaee'),      # 16 leylak
]

def paint_swatches(lin, nrm):
    """Doku dizilerine (alttan yukarı satır sırası, doğrusal renk) üst şeridin renk örneklerini boyar; normal şeridi düz."""
    H, W = lin.shape[:2]; r0 = int(round(H * (1 - STRIP))); cw = max(1, W * CELL // TEX)
    t = np.linspace(0, 1, H - r0)[:, None]
    for k, (a, m, b) in enumerate(SWATCH):
        a, m, b = _srgb(a), _srgb(m), _srgb(b)
        g = np.where(t < 0.5, a + (m - a) * (t / 0.5), m + (b - m) * ((t - 0.5) / 0.5))
        lin[r0:, k * cw:(k + 1) * cw, :] = g[:, None, :]
    lin[r0:, len(SWATCH) * cw:, :] = _srgb('#567f33')
    nrm[int(round(nrm.shape[0] * (1 - STRIP))):, :, :] = (0.0, 0.0, 1.0)

def _uv(cell, t, du=0.0):
    """Renk örneği hücresinde UV: t = 0 kök … 1 uç; du hücre içinde yatay kayma (−0,5…0,5)."""
    u = (cell + 0.5 + du * 0.6) * CELL / TEX
    v = 1 - STRIP + (4 + t * (CELL - 8)) / TEX
    return (u, v)

class _Mesh:
    def __init__(self): self.V, self.F, self.UV, self.N = [], [], [], []
    def tri(self, a, b, c, ua, ub, uc, n, both=True):
        """Üçgen (+ ters yüzü; aynı yukarı-bakan normal: zemin gibi yumuşak gölgelenir, tel tel parlamaz). Ters yüz 0,6 mm arkada:
        çakışık iki yüz ışın izlemede birbirini gölgeliyordu (önizlemede teller kara görünüyordu)."""
        i = len(self.V); self.V += [a, b, c]; self.UV += [ua, ub, uc]; self.N += [n, n, n]; self.F.append((i, i + 1, i + 2))
        if both:
            g = (b - a).cross(c - a)
            g = g.normalized() * 0.0006 if g.length > 1e-12 else V((0, 0, 0))
            i = len(self.V); self.V += [b - g, a - g, c - g]; self.UV += [ub, ua, uc]; self.N += [n, n, n]; self.F.append((i, i + 1, i + 2))
    def obj(self, name, col):
        me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in self.V], [], self.F); me.update()
        uvl = me.uv_layers.new(name='UVMap'); uvs = np.array([self.UV[i] for f in self.F for i in f], np.float32)
        uvl.data.foreach_set('uv', uvs.ravel())
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.normals_split_custom_set_from_vertices([tuple(n) for n in self.N])
        o = bpy.data.objects.new(name, me); col.objects.link(o); return o

def _tuft(M, p, R, s=1.0, cell=0):
    """Çim öbeği: 8 kıl gibi tel (adadaki GrassField öbeği gibi), rastgele yön/boy/eğim."""
    for _ in range(8):
        a = R.uniform(0, math.tau); r = math.sqrt(R.random()) * 0.11 * s
        root = p + V((math.cos(a) * r, math.sin(a) * r, -0.01))
        face = R.uniform(0, math.pi); side = V((math.cos(face), math.sin(face), 0)) * (0.011 * s)
        h = R.uniform(0.09, 0.2) * s
        lean = V((R.uniform(-0.5, 0.5), R.uniform(-0.5, 0.5), 0)) * 0.14 * h / 0.15
        n = (V((0, 0, 1)) + V((-math.sin(face), math.cos(face), 0)) * 0.2).normalized()
        du = R.uniform(-0.5, 0.5)
        M.tri(root - side, root + side, root + lean + V((0, 0, h)), _uv(cell, 0.0, du - 0.3), _uv(cell, 0.0, du + 0.3), _uv(cell, 1.0, du), n)

_OCT = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
_OCT_F = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]

def _flower(M, p, R, kind):
    h = R.uniform(0.2, 0.32) if kind == 'bell' else R.uniform(0.14, 0.26)
    lean = V((R.uniform(-0.04, 0.04), R.uniform(-0.04, 0.04), 0)); top = p + lean + V((0, 0, h))
    face = R.uniform(0, math.pi); side = V((math.cos(face), math.sin(face), 0)) * 0.006
    up = V((0, 0, 1))
    M.tri(p - side, p + side, top, _uv(3, 0.0, -0.3), _uv(3, 0.0, 0.3), _uv(3, 1.0), up)
    if kind == 'bell':
        cell = R.choice((4, 5, 6, 7))
        for b in range(3):
            t = 0.55 + 0.17 * b; c = p + (top - p) * t + V((R.uniform(-0.02, 0.02), R.uniform(-0.02, 0.02), 0)); r = 0.03 * (1.15 - 0.2 * b)
            q = [c + V((x * r, y * r, z * r * 1.25)) for (x, y, z) in _OCT]
            for (i, j, k) in _OCT_F:
                nn = ((q[j] - q[i]).cross(q[k] - q[i])).normalized()
                tv = 0.75 if q[k].z > c.z else 0.35
                M.tri(q[i], q[j], q[k], _uv(cell, tv, -0.2), _uv(cell, tv, 0.2), _uv(cell, tv), (nn + up).normalized(), both=False)
    else:
        cell = {'daisy': R.choice((12, 12, 13)), 'orange': R.choice((8, 9, 10, 11)), 'yellow': R.choice((14, 16))}[kind]
        r = R.uniform(0.04, 0.058) * (0.75 if kind == 'yellow' else 1.0); k = 7; c0 = top + V((0, 0, 0.014))
        rim = [top + V((math.cos(a) * r, math.sin(a) * r, R.uniform(-0.006, 0.006))) for a in [i / k * math.tau + face for i in range(k)]]
        for i in range(k):
            M.tri(c0, rim[i], rim[(i + 1) % k], _uv(15 if kind != 'orange' else cell, 0.9), _uv(cell, 0.6, -0.3), _uv(cell, 0.6, 0.3), up, both=False)
            M.tri(top - V((0, 0, 0.004)), rim[(i + 1) % k], rim[i], _uv(cell, 0.3), _uv(cell, 0.3, 0.3), _uv(cell, 0.3, -0.3), up, both=False)

def meadow(L, H, seed=7):
    """Pişirmeden sonra: teras üstlerinde 3B çim öbekleri (kenarlarda, duvar/sütun diplerinde sık; içeride öbek öbek) ve çiçek
    demetleri. Yer ışınla bulunur (yalnız çimen yüzeyi: taş, plaka, basamak, taban üstüne konmaz)."""
    import kit3_v6 as K3
    from mathutils.bvhtree import BVHTree
    from mathutils import noise as MN
    dg = bpy.context.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(H, dg)
    R = random.Random(seed)
    t1 = K3.rounded_rect(0, 1.0, 30, 22, 2.0, seed=1); t2 = K3.rounded_rect(0, 4.5, 21, 13, 1.5, seed=2); t0 = K3.rounded_rect(-9, -8.5, 7, 3.5, 1.0, seed=3)
    tops = ((t2, 2.1), (t1, 1.0), (t0, 0.45))
    blocks = [(-10.5, 6.0, 3.3, 3.3), (0, 6.5, 5.9, 3.7), (11.5, 4.5, 3.4, 2.9), (0, -7.0, 1.75, 3.4), (0, -2.9, 2.25, 1.2), (-12.5, -9.0, 1.8, 2.0)]
    def ground(x, y):
        for poly, z in tops:
            if K3._in_poly(x, y, poly): return z
        return None
    def edge_d(x, y, poly):
        return min(math.hypot(x - px, y - py) for (px, py) in poly)
    M = _Mesh(); F = _Mesh(); n_t = n_f = 0
    step = 0.34
    for gx in np.arange(-15.5, 15.5, step):
        for gy in np.arange(-10.5, 12.5, step):
            x = gx + R.uniform(-0.45, 0.45) * step; y = gy + R.uniform(-0.45, 0.45) * step
            z = ground(x, y)
            if z is None: continue
            if any(abs(x - bx) < hw and abs(y - by) < hd for (bx, by, hw, hd) in blocks): continue
            hit = bvh.ray_cast(V((x, y, z + 0.6)), V((0, 0, -1)), 1.0)
            if hit[0] is None or abs(hit[0].z - (z + 0.02)) > 0.03 or hit[1].z < 0.9: continue
            p = hit[0]
            near = 99.0
            for a in range(6):
                d = V((math.cos(a * math.pi / 3), math.sin(a * math.pi / 3), 0))
                h2 = bvh.ray_cast(p + V((0, 0, 0.06)), d, 0.7)
                if h2[0] is not None: near = min(near, h2[3])
            if near < 0.13: continue                      # duvar/taban/taşın içine girmesin
            poly = [pp for pp, zz in tops if zz == z][0]
            rim = edge_d(x, y, poly)
            patch = MN.noise(V((x * 0.35, y * 0.35, 7.0)))   # −1..1: çimen öbekleri
            pr = 0.36 + 0.4 * max(0.0, patch) + (0.45 if rim < 0.7 else 0.0) + (0.4 if near < 0.6 else 0.0)
            if R.random() > pr: continue
            s = R.uniform(0.85, 1.25) * (1.15 if (rim < 0.7 or near < 0.6) else 1.0)
            cell = 2 if R.random() < 0.18 else (1 if R.random() < 0.45 else 0)
            _tuft(M, p, R, s, cell); n_t += 1
    # çiçek demetleri: taslaktaki gibi mavi çan çiçeği salonun önünde ve teras kenarlarında, beyaz/pembe/turuncu/sarı karışık öbekler
    kinds = ['bell'] * 4 + ['daisy'] * 3 + ['orange'] * 3 + ['yellow'] * 2
    tries = 0
    while n_f < 170 and tries < 7000:
        tries += 1
        poly, z = (t2, 2.1) if R.random() < 0.4 else ((t0, 0.45) if R.random() < 0.06 else (t1, 1.0))
        cx, cy = R.uniform(-14.5, 14.5), R.uniform(-10, 12)
        if ground(cx, cy) != z or any(abs(cx - bx) < hw + 0.2 and abs(cy - by) < hd + 0.2 for (bx, by, hw, hd) in blocks): continue
        kind = R.choice(kinds); placed = 0
        for j in range(R.randint(5, 9)):
            x, y = cx + R.gauss(0, 0.25), cy + R.gauss(0, 0.25)
            if ground(x, y) != z: continue
            hit = bvh.ray_cast(V((x, y, z + 0.6)), V((0, 0, -1)), 1.0)
            if hit[0] is None or abs(hit[0].z - (z + 0.02)) > 0.03: continue
            if any(bvh.ray_cast(hit[0] + V((0, 0, 0.08)), V((math.cos(a), math.sin(a), 0)), 0.12)[0] is not None for a in (0, 1.57, 3.14, 4.71)): continue
            _flower(F, hit[0], R, kind); placed += 1
        if placed: n_f += 1
    col = bpy.context.scene.collection
    print('3B çim öbeği', n_t, 'çiçek demeti', n_f, 'üçgen', len(M.F) + len(F.F), flush=True)
    return [M.obj('meadow_grass', col), F.obj('meadow_flowers', col)]
