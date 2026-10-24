# Kıyı yapılarının ortak araçları (24 Ekim 2026; kullanıcı: "haritadaki bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# İskele (b_pier), fener (b_lighthouse), yüzme koyu (b_swim) ve sörf kulübesi (b_surf) bu dosyayı kullanır; ortak hat bld_kit.py'dir.
# Burada yalnız kıyıya özgü eskitme katmanları ve küçük parçalar var:
#   - malzeme katmanı (overlay): var olan malzemenin rengine su çizgisi (ıslak koyu bant, yosun şeridi, midye beneği), güneş solması
#     (yukarı bakan yüz gümüşi), tuz/pas akıntısı eklenir — asıl malzeme değişmez, kopyası döner;
#   - "yalnız pişir" parçaları (adı _bk ile biter): midye kümeleri, çivi başı + pas halesi, cıvata, pas izi, kütük kesiti, lif uçları…
#     Taslakta (yüksek ayrıntı) durur, renk ve normal haritasına işlenir; oyun ağına girmez (üçgen bütçesi kabuk/tahta/halata kalır);
#   - komut satırı: python -I bld/<ad>.py -- <çıktı> [ad] [--draft <png>]  (export_game.py ikinci argüman olarak yapıcı adını verir).
import os, sys, re, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
for p in (os.path.join(ROOT, 'v6'), ROOT, HERE):
    if p not in sys.path: sys.path.insert(0, p)
import bpy, bmesh
from mathutils import Vector as V, noise as MN
import kit
from kit import rbox, cyl, blob, tube, srgb, ramp, nodes_mat, uv_node
import assets_v3 as A
import assets_town as AT
import bld_kit as BK
import proxy_bake as PB

BAKE_ONLY = r'_bk$'          # yalnız taslakta (dokuya işlenir, oyun ağına girmez)
LOW_ONLY = r'_lo$'           # yalnız oyun ağında (taslakta yok: halat çekirdeği gibi sade hedef parçalar)


def _key(name):
    return re.sub(r'\.\d+$', '', name)


def bk(o):
    """Nesneyi (ya da listeyi) 'yalnız pişir' yap: adı _bk ile biter → oyun ağına girmez, taslaktan dokuya işlenir."""
    if isinstance(o, (list, tuple)):
        for x in o: bk(x)
        return o
    if o is not None and not _key(o.name).endswith('_bk'): o.name = _key(o.name) + '_bk'
    return o


def lo(o):
    """Nesneyi 'yalnız oyun ağı' yap (adı _lo ile biter): taslakta yok, pişirmede hedef olur."""
    if o is not None and not _key(o.name).endswith('_lo'): o.name = _key(o.name) + '_lo'
    return o


def _resample(pts, step):
    P = [V(p) for p in pts]; out = [P[0]]; acc = 0.0
    for i in range(1, len(P)):
        seg = (P[i] - P[i - 1]).length; acc += seg
        if acc >= step or i == len(P) - 1:
            out.append(P[i]); acc = 0.0
    return out


def rope(pts, thick, m, sides=8, name='rope'):
    """Halat: taslakta üç kollu burgulu halat + lif uçları (yalnız pişir), oyunda aynı çizgide sade yuvarlak çekirdek (yalnız oyun):
    burgu, kol arası gölge ve lif açıklığı normal/renk haritasına işlenir (sadeleştirilmiş kollar tırtıklı görünüyordu)."""
    strands = AT.strand_rope(pts, thick, m, name=name)
    bk(strands)
    # çekirdek: strand_rope ile aynı sıklaştırma + yumuşatma, sonra seyrek örnek
    P = [V(p) for p in pts]; dense = []
    for i in range(len(P) - 1):
        Ls = (P[i + 1] - P[i]).length; nseg = max(2, int(Ls / (thick * 1.8)))
        for k in range(nseg): dense.append(P[i].lerp(P[i + 1], k / nseg))
    dense.append(P[-1])
    for _ in range(2):
        dense = [dense[0]] + [(dense[i - 1] + dense[i] * 2 + dense[i + 1]) / 4 for i in range(1, len(dense) - 1)] + [dense[-1]]
    core = _resample(dense, max(0.05, thick * 4.0))
    o = tube(name + 'core', [tuple(p) for p in core], [thick * 0.98] * len(core), m, res=1)
    o.data.bevel_resolution = max(0, (sides - 4) // 2)
    for sp in o.data.splines:
        for bp in sp.bezier_points: bp.handle_left_type = bp.handle_right_type = 'VECTOR'
    lo(o)
    return strands


def plank2(name, loc, size, m, rot=(0, 0, 0), seed=None, amt=0.01, bevel=0.012):
    """Tahta: taslakta assets_town.plank (ezik, yamukluk, köşe kırığı; yalnız pişir), oyunda aynı yerde tek kademe pahlı kutu
    (yalnız oyun). Alt bölmeli taslak tahta sadeleştirilince kenarları tırtıklanıyordu; kutu + normal haritası daha temiz."""
    bk(AT.plank(name, loc, size, m, rot=rot, seed=seed, amt=amt))
    b = rbox(name, loc, size, m, rot=rot, bevel=min(bevel, min(size) * 0.3), seg=1)
    return lo(b)


def rope_wrap(center, r, z0, z1, turns, m, thick=0.016, seed=0, sides=6):
    """assets_town.rope_wrap ile aynı sarım (sarmal + sarkan kuyruk), halat() ile."""
    pts = []; n = int(turns * 12)
    for i in range(n + 1):
        t = i / n; a = t * turns * 2 * math.pi + seed
        pts.append(tuple(V(center) + V((math.cos(a) * r, math.sin(a) * r, z0 + (z1 - z0) * t))))
    end = V(pts[-1]); a = turns * 2 * math.pi + seed
    tail = [tuple(end + V((math.cos(a) * 0.04, math.sin(a) * 0.04, -0.05))), tuple(end + V((math.cos(a) * 0.05, math.sin(a) * 0.05, -0.13)))]
    return rope(pts + tail, thick, m, sides=sides)


def rope_sag(a, b, sag, m, thick=0.02, n=8, sides=8):
    pts = []
    for i in range(n + 1):
        t = i / n; p = V(a).lerp(V(b), t); p.z -= sag * 4 * t * (1 - t); pts.append(tuple(p))
    return rope(pts, thick, m, sides=sides)


def frays_bake_only():
    """strand_rope'un lif uçları (ince iki yüzlü şerit) oyunda yalnız dokuda: ağda kıl gibi titrer ve bütçe yer."""
    for o in bpy.context.scene.objects:
        if _key(o.name) == 'fray': bk(o)


# ------------------------------------------------------------------ malzeme katmanları

def overlay(m, fn, name=None):
    """m'nin kopyası: Base Color'a giden renge fn(G, renk) → yeni renk katmanı eklenir."""
    m2 = m.copy(); m2.name = name or (m.name + '_k')
    nt = m2.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    inp = b.inputs['Base Color']; G = A._G(nt)
    if inp.links: src = inp.links[0].from_socket
    else:
        rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = inp.default_value; src = rgb.outputs[0]
    nt.links.new(fn(G, src), inp)
    return m2


def bumpify(m, strength=0.3, dist=0.006):
    """Renkten kabartma: taban renginin parlaklığı yükseklik olur (koyu çatlak, damar, düğüm, boya pulu kenarı çukur) → Cycles normal
    pişirmesi bunu da normal haritasına yazar; oyunda toon ışıkta tahta damarı ve dökülen boya kabarık okunur. Malzemeyi yerinde değiştirir."""
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    inp = b.inputs['Base Color']
    if not inp.links or b.inputs['Normal'].links: return m
    bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(inp.links[0].from_socket, bw.inputs[0])
    bu = nt.nodes.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = strength; bu.inputs['Distance'].default_value = dist
    nt.links.new(bw.outputs[0], bu.inputs['Height']); nt.links.new(bu.outputs['Normal'], b.inputs['Normal'])
    return m


def L_waterline(zw=0.0, wet=0.13, band=(-0.05, 0.05), amt=1.0, specks=True):
    """Su çizgisi (nesne Z = dünya Z olan parçalar: eğriden dönen kazık, dikme): su altı koyu-yeşilimsi, üstünde gürültülü ıslak bant,
    çizgide parlak yosun şeridi (üst kenarı tırtıklı), şeridin içinde açık midye benekleri."""
    def fn(G, col):
        o = G.obj(); z = G.z()
        zn = G.math('ADD', z, G.math('MULTIPLY', G.math('SUBTRACT', G.noise(o, 6.0, 4), 0.5), 0.06))
        below = G.rng(zn, zw + 0.02, zw - 0.1, 0, 0.7 * amt)                        # su altı
        col = G.mix(below, col, '#3f5233')
        wetm = G.rng(zn, zw + wet, zw + wet - 0.06, 0, 0.75 * amt)                  # ıslak koyu bant (çarpım)
        col = G.mix(wetm, col, '#8e8470', 'MULTIPLY')
        alg = G.math('MULTIPLY', G.rng(zn, band[0], band[0] + 0.03), G.rng(zn, band[1], band[1] - 0.025))
        alg = G.math('MULTIPLY', alg, G.rng(G.noise(o, 9.0, 3), 0.3, 0.55, 0.45, 1.0))
        col = G.mix(G.math('MULTIPLY', alg, 0.85 * amt), col, G.mix(G.rng(G.noise(o, 22, 3), 0.35, 0.7), '#4c7a2a', '#7fa83c'))
        salt = G.math('MULTIPLY', G.rng(zn, zw + wet - 0.01, zw + wet + 0.02), G.rng(zn, zw + wet + 0.07, zw + wet + 0.03))
        col = G.mix(G.math('MULTIPLY', salt, G.rng(G.noise(o, 14.0, 3), 0.45, 0.6, 0, 0.55 * amt)), col, '#ebe5d6')   # tuz çizgisi
        if specks:
            sp = G.math('MULTIPLY', G.rng(G.vor(o, 38.0), 0.12, 0.05), G.rng(zn, band[0] - 0.07, band[0] - 0.03))
            sp = G.math('MULTIPLY', sp, G.rng(zn, band[1] + 0.03, band[1] - 0.01))
            sp = G.math('MULTIPLY', sp, G.rng(G.noise(o, 3.0, 2), 0.42, 0.6))
            col = G.mix(G.math('MULTIPLY', sp, 0.8 * amt), col, '#e2dccd')
        return col
    return fn


def L_sunbleach(amt=0.32, tone='#b8ae9c'):
    """Güneş solması: yukarı bakan yüzler yer yer gümüşi gri-bej (yan yüzler sıcak kalır → tahta üstü ile kenarı ayrışır)."""
    def fn(G, col):
        up = G.rng(G.nz(), 0.35, 0.9, 0, amt)
        patch = G.rng(G.noise(G.obj(), 1.6, 4), 0.32, 0.7, 0.5, 1.0)
        return G.mix(G.math('MULTIPLY', up, patch), col, tone)
    return fn


def L_streaks(hexc='#f3efe4', amt=0.35, z_top=99.0, length=0.5, scale=14.0, thresh=(0.58, 0.7), seed=0.0):
    """Aşağı akan izler (tuz çiçeği açık, pas turuncu, kir koyu): dikeyde uzatılmış gürültü, z_top'un altında 'length' boyunca söner."""
    def fn(G, col):
        o = G.obj(); z = G.z()
        st = G.rng(G.noise(G.mapping(o, (scale, scale, 1.2)), 1.0 + seed, 3), thresh[0], thresh[1], 0, 1)
        fall = G.math('MULTIPLY', G.rng(z, z_top - length, z_top - 0.02), G.rng(z, z_top + 0.01, z_top - 0.02)) if z_top < 90 else 1.0
        m = G.math('MULTIPLY', st, fall) if not isinstance(fall, float) else st
        return G.mix(G.math('MULTIPLY', m, amt), col, hexc)
    return fn


def L_chain(*fns):
    def fn(G, col):
        for f in fns: col = f(G, col)
        return col
    return fn


# ------------------------------------------------------------------ küçük parçalar

def m_shell(name='barnacle'):
    return A.m_flat('#c8c0ae', 0.3, 40, name)


def cones(name, items, m_out, m_in, segs=8):
    """Midye/kabuk konileri tek ağda: items = [(konum, normal, taban yarıçapı, boy)]. Her biri kraterli küçük volkan (içi koyu)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    prof = [(1.0, 0.0), (0.82, 0.55), (0.5, 1.0), (0.32, 0.86), (0.05, 0.62)]
    for (p, n, rb, h) in items:
        n = V(n).normalized(); q = n.to_track_quat('Z', 'Y')
        rows = []
        for k, (rr, zz) in enumerate(prof):
            row = []
            for j in range(segs):
                a = j / segs * 2 * math.pi + k * 0.2
                w = 1.0 + 0.12 * math.sin(a * 3 + p[0] * 40)
                row.append(bm.verts.new(V(p) + q @ V((math.cos(a) * rr * rb * w, math.sin(a) * rr * rb * w, zz * h - h * 0.15))))
            rows.append(row)
        for i in range(len(rows) - 1):
            for j in range(segs):
                j2 = (j + 1) % segs
                f = bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))
                f.material_index = 1 if i >= 2 else 0
                for lp in f.loops: lp[uvl].uv = (lp.vert.co.x * 3, lp.vert.co.z * 3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = A.link_mesh(name, bm, [m_out, m_in]); A.smooth(o)
    return bk(o)


def barnacles_on_post(cx, cy, r, z0, z1, n, seed, a0=0.0, a1=2 * math.pi, size=(0.012, 0.024)):
    """Kazık çevresinde su çizgisi midye kümesi (yalnız pişir): öbek öbek, çizgiye yakın yoğun."""
    R = random.Random(seed); items = []
    nclu = max(2, n // 9)
    cl = [(R.uniform(a0, a1), R.uniform(z0, z1)) for _ in range(nclu)]
    for k in range(n):
        ca, cz = cl[k % nclu]
        a = ca + R.gauss(0, 0.22); z = min(z1, max(z0, cz + R.gauss(0, 0.028)))
        nrm = V((math.cos(a), math.sin(a), R.uniform(-0.1, 0.25)))
        p = V((cx + math.cos(a) * r, cy + math.sin(a) * r, z))
        rb = R.uniform(*size); items.append((p, nrm, rb, rb * R.uniform(0.9, 1.3)))
    return cones('barnacle', items, m_shell(), A.m_flat('#6f6a5c', 0.2, 30, 'barnhole'))


def bolt(p, nrm, m=None, r=0.018, drip=0.06, square=False):
    """Cıvata başı (altıgen ya da kare pul) + altında pas akıntısı — ikisi de yalnız pişir."""
    I = m or AT.m_metal('#4d4852', name='boltm')
    n = V(nrm).normalized(); q = n.to_track_quat('Z', 'Y').to_euler()
    o = cyl('bolt', tuple(V(p) + n * 0.006), r, 0.014, I, verts=4 if square else 6, bevel=0.003); o.rotation_euler = q
    out = [o]
    if drip and abs(n.z) < 0.6:
        out.append(rust_drip(V(p) - V((0, 0, r * 0.6)), n, drip, r * 0.8))
    return bk(out)


_RUST = {}
def rust_drip(p, nrm, length=0.08, width=0.012):
    """Pas akıntısı izi: yüzeye yapışık, aşağı doğru incelen turuncu-kahve damla (yalnız pişir)."""
    if 'm' not in _RUST: _RUST['m'] = A.m_flat('#8f4a26', 0.35, 30, 'rustdrip')
    n = V(nrm).normalized()
    s = blob('drip', tuple(V(p) + n * 0.002 - V((0, 0, length * 0.5))), (width, 0.0025, length * 0.5), _RUST['m'], sub=0, seg=8)
    s.rotation_euler = (0, 0, math.atan2(n.y, n.x) + math.pi / 2)
    return bk(s)


def rust_halo(p, r=0.03):
    """Çivi çevresinde yere sinmiş pas halesi (tahta üstü, yalnız pişir)."""
    if 'h' not in _RUST: _RUST['h'] = A.m_flat('#80583a', 0.4, 50, 'rusthalo')
    o = blob('halo', (p[0], p[1], p[2] + 0.0015), (r, r * 0.8, 0.002), _RUST['h'], rot=(0, 0, random.uniform(0, 180)), sub=0, seg=10)
    return bk(o)


def nail_top(p, r=0.012):
    """Tahta üstünde çivi başı + ince pas halesi (yalnız pişir)."""
    I = AT.m_metal('#5a5560', name='nailm')
    o = blob('nailh', (p[0], p[1], p[2] + 0.004), (r, r, 0.006), I, sub=0, seg=8)
    return bk([o, rust_halo(p, r * 1.7)])


def endgrain_cap(x, y, z, r, seed=0, lichen=True):
    """Kazık tepesinde kesik yüz (yıllık halka, çatlak) + yer yer liken (yalnız pişir)."""
    o = cyl('cap', (x, y, z + 0.004), r * 0.93, 0.008, AT.m_endgrain(), verts=16, bevel=0)
    out = [o]
    if lichen:
        R = random.Random(seed)
        L = A.m_flat('#a9b77a', 0.3, 30, 'lichen')
        for k in range(3):
            a = R.uniform(0, 6.28); rr = R.uniform(0.2, 0.6) * r
            out.append(blob('lich', (x + math.cos(a) * rr, y + math.sin(a) * rr, z + 0.009), (r * 0.22, r * 0.17, 0.003), L, sub=0, seg=8))
    return bk(out)


def coil(cx, cy, z, r0, turns, thick, m, seed=0, tail=None):
    """Güverteye serili halat kangalı (düz sarmal, her tur bir öncekinin yanında) + isteğe bağlı kuyruk (tail: noktalar)."""
    pts = []; n = int(turns * 18)
    for i in range(n + 1):
        t = i / n; a = t * turns * 2 * math.pi + seed
        rr = r0 + thick * 2.05 * turns * t
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, z + thick + 0.004 * math.sin(a * 3)))
    if tail: pts += list(tail)
    return rope(pts, thick, m, sides=6)


def m_net(name='net'):
    """Balık ağı yığını: koyu deniz yeşili ip, açık düğüm ızgarası (nesne koordinatında iki yönlü sinüs), yer yer solmuş/tuzlu."""
    def b(nt, bsdf):
        G = A._G(nt); o = G.obj(); n = nt.nodes; l = nt.links
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
        k = 2 * math.pi / 0.045
        gx = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', G.math('ADD', sp.outputs['X'], sp.outputs['Z']), k)))
        gy = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', G.math('SUBTRACT', sp.outputs['Y'], sp.outputs['Z']), k)))
        line = G.math('MAXIMUM', G.rng(gx, 0.25, 0.0), G.rng(gy, 0.25, 0.0))
        base = G.mix(G.rng(G.noise(o, 4, 3), 0.3, 0.7), '#22463f', '#2f5e52')
        col = G.mix(G.math('MULTIPLY', line, 0.85), base, '#8fb7a2')
        col = G.mix(G.rng(G.noise(o, 2.2, 4), 0.55, 0.75, 0, 0.35), col, '#c9d6c4')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def lumpy(name, loc, radii, m, seed=0, folds=0.25, sub=3):
    """Yumuşak yığın (ağ, havlu, çuval): basık ikosfer + kıvrım gürültüsü; tabanı düz."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1.0, location=(0, 0, 0))
    o = bpy.context.object; o.name = name
    for v in o.data.vertices:
        c = v.co.copy()
        f = 1.0 + folds * MN.noise(c * 2.6 + V((seed, 0, 0))) + folds * 0.5 * math.sin(c.x * 9 + c.y * 4 + seed)
        c = V((c.x * radii[0] * f, c.y * radii[1] * f, max(c.z, -0.25) * radii[2] * (0.8 + 0.3 * f)))
        v.co = c
    zmin = min(v.co.z for v in o.data.vertices)
    for v in o.data.vertices: v.co.z -= zmin
    o.location = loc; o.data.materials.append(m); A.smooth(o)
    return o


# ------------------------------------------------------------------ pişirme ve komut satırı

def drop_floor(objs, zcut):
    """Zemine (ya da deniz tabanına) yapışık, aşağı bakan yüzleri siler: oyunda hiç görünmez (arazi/su örter) ama hiçbir yönden
    'kapalı' sayılmadığı için gizli yüz ayıklamasından kaçıp dokuda büyük daire yer tutuyordu (fener temeli altı ~%2,5)."""
    n = 0
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update(); mw = o.matrix_world; m3 = mw.to_3x3()
        kill = [f for f in bm.faces if (m3 @ f.normal).normalized().z < -0.9 and max((mw @ v.co).z for v in f.verts) < zcut]
        n += len(kill)
        bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(o.data); bm.free()
    print('taban yüzü silindi', n, flush=True)


def bake(out_dir, name, high, decim=(), weights=(), tex=1024, budget=None, ao_dist=0.5, ao_strength=0.6, cage=0.03, ray=0.12, floor=None, **kw):
    """bld_kit.bake ile aynı; farklar: adı _bk ile biten taslak parçaları hedefe (oyun ağına) girmez, yalnız dokuya işlenir; _lo
    parçaları yalnız hedefte; floor verilirse o yüksekliğin altındaki aşağı bakan yüzler hedeften silinir."""
    os.makedirs(out_dir, exist_ok=True)
    tex = int(os.environ.get('POFI_TEX', '0') or 0) or tex
    hi = [o for o in high if not re.search(LOW_ONLY, _key(o.name))]
    low = BK.build_low([o for o in high if not re.search(BAKE_ONLY, _key(o.name))], decim, weights)
    if floor is not None: drop_floor(low, floor)
    for o in high:
        if re.search(LOW_ONLY, _key(o.name)): bpy.data.objects.remove(o)
    tris = PB.export_proxy(os.path.join(out_dir, name), hi, low, target=budget, size=tex, nsize=tex, cage=cage, ray=ray,
                           cull_hidden=True, uv_weight='uvw', dilate=16, ao_dist=ao_dist, ao_strength=ao_strength, **kw)
    print(name, 'üçgen', tris, flush=True)
    return tris


def groups(objs):
    """Ad grubuna göre üçgen sayısı (decim tablosunu ayarlamak için)."""
    dg = bpy.context.evaluated_depsgraph_get(); g = {}
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).to_mesh(); n = sum(len(p.vertices) - 2 for p in me.polygons); o.evaluated_get(dg).to_mesh_clear()
        k = _key(o.name); g[k] = g.get(k, 0) + n
    return dict(sorted(g.items(), key=lambda kv: -kv[1]))


def draft_render(png, yaw=35.0, pitch=24.0, dist=None, size=(900, 700), lens=50, samples=48):
    """Taslağın (yüksek ayrıntı, kendi malzemeleriyle) çizimi: render_low ile aynı ışık ve kamera."""
    from mathutils import Vector as V3
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    lo = V3((1e9,) * 3); hi = V3((-1e9,) * 3)
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ V3(c); lo = V3(map(min, lo, w)); hi = V3(map(max, hi, w))
    ctr = (lo + hi) / 2; r = (hi - lo).length * 0.5; d = dist or r * 2.6
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = size
    for o in [o for o in sc.objects if o.type in ('LIGHT', 'CAMERA')]: bpy.data.objects.remove(o)
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.0
    sc.world.use_nodes = True; bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.62, 0.78, 0.95, 1); bg.inputs['Strength'].default_value = 0.9
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(4)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(yaw + 40))
    cam = bpy.data.cameras.new('cam'); cam.lens = lens
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    yr, pr = math.radians(yaw), math.radians(pitch)
    co.location = ctr + V3((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)


def bounds(objs):
    lo = V((1e9,) * 3); hi = V((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH': continue
        e = o.evaluated_get(dg); me = e.to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co; lo = V(map(min, lo, w)); hi = V(map(max, hi, w))
        e.to_mesh_clear()
    return lo, hi


def main(default_name, build, decim, weights, budget, tex=1024, draft_dist=None, **bake_kw):
    """Komut satırı: -- <çıktı> [ad] [--draft <png> [--yaw Y]]. build() taslağı kurar (kit.reset dahil)."""
    args = sys.argv[sys.argv.index('--') + 1:]
    out = args[0]; os.makedirs(out, exist_ok=True)
    name = ([a for a in args[1:] if not a.startswith('-') and not a.endswith('.png') and not _isnum(a)] or [default_name])[0]
    build()
    frays_bake_only()
    high = BK.prepare()
    game = [o for o in high if not re.search(BAKE_ONLY, _key(o.name))]
    draft = [o for o in high if not re.search(LOW_ONLY, _key(o.name))]
    b0, b1 = bounds(game)
    print('oyun sınırı', tuple(round(x, 3) for x in b0), tuple(round(x, 3) for x in b1), 'boy', tuple(round(x, 3) for x in b1 - b0), flush=True)
    print('taslak üçgen', BK.tri_count(draft), 'oyun adayı (sadeleşmeden)', BK.tri_count(game), flush=True)
    if '--groups' in args:
        g = groups(game)
        dec = sum(int(n * BK._lookup(decim, k, 1.0)) for k, n in g.items())
        print('sadeleşme sonrası tahmini', dec, flush=True)
        print('gruplar', list(g.items())[:40], flush=True)
    if '--draft' in args:
        png = args[args.index('--draft') + 1]
        yaw = float(args[args.index('--yaw') + 1]) if '--yaw' in args else 35.0
        for o in high:
            if re.search(LOW_ONLY, _key(o.name)): o.hide_render = True
        draft_render(png, yaw=yaw, dist=draft_dist)
        return
    budget = int(os.environ.get('POFI_TARGET', '0') or 0) or budget
    bake(out, name, high, decim=decim, weights=weights, tex=tex, budget=budget, **bake_kw)


def _isnum(s):
    try: float(s); return True
    except ValueError: return False
