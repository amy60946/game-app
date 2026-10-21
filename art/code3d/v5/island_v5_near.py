# Ada v5 taslağı · oyun kamerası çekimleri için yakın plan ayrıntı (21 Ekim 2026, düzeltme turu).
# Her çekimde petin çevresine (≈30 m) kurulur, çekimden sonra silinir. Uzakta ada genel dağılımı (island_v5.py) yeterli.
#   makro çim (g9: açık limon → sarı uç, renk lekeleri, biyom tonu), çiçek kümeleri (G8), göl kıyısı (ıslak toprak, saz, taş),
#   kıyı köpüğü + yosunlu kıyı taşları (g1), kayak tepesi (v4 after_ski: pist, kapılar, sehpa, kardan adam, kar taneleri),
#   kaya kümesi + menhir (g4), orman zemini (G2: dökülmüş yaprak, mantar, eğrelti, dal).
# Hepsi kodla özgün; referans görseller yalnız kalite/hava hedefi.
import math, random
import bpy
import numpy as np
from mathutils import Vector as V, noise as MN
import common as C
import scenes_v5 as S5
import ski_mountain_v4 as SM
from assets_v3 import m_leaf, m_rock, blade, mesh_from_blades, pebble, flower_heads

# ------------------------------------------------------------------ hızlı ilkeller
# Ada sahnesinde binlerce nesne var: bpy.ops ile eklenen her küre tüm görünüm katmanını yeniden günceller (dakikalar).
# kit.blob ve assets_v3.pebble aynı biçimi bmesh ile doğrudan kuran sürümle değiştirilir (sonuç aynı).
import bmesh, kit, assets_v3, assets_town
from mathutils import Matrix, Euler
_SPH = {}
def _sphere_mesh(seg):
    if seg not in _SPH:
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(3, seg // 2), radius=1.0)
        me = bpy.data.meshes.new('sph%d' % seg); bm.to_mesh(me); bm.free(); _SPH[seg] = me
    return _SPH[seg]
def fast_blob(name, loc, radii, m, rot=(0, 0, 0), sub=2, seg=24):
    kit.seg_hint_small[0] = seg <= 12
    o = bpy.data.objects.new(name, _sphere_mesh(seg).copy()); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.scale = radii; o.rotation_euler = [math.radians(a) for a in rot]
    return kit._finish(o, m, sub)
def fast_pebble(loc, r, m, seed):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
    for v in bm.verts:
        v.co = V((v.co.x * 1.2, v.co.y, v.co.z * 0.6)); v.co += v.co.normalized() * MN.noise(v.co * 6 + V((seed, 0, 0))) * r * 0.25
    me = bpy.data.meshes.new('peb'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('pebble', me); bpy.context.scene.collection.objects.link(o); o.location = loc
    o.data.materials.append(m); assets_v3.smooth(o); return o
for _mod in (kit, assets_v3, assets_town, S5, SM):
    if hasattr(_mod, 'blob'): _mod.blob = fast_blob
    if hasattr(_mod, 'pebble'): _mod.pebble = fast_pebble
pebble = fast_pebble

GRASS_MATS = None
def grass_mats():
    """Biyom tonları: 0 genel limon, 1 açık leke, 2 sararmış, 3 orman (mavi-yeşil), 4 kar yakını (soğuk), 5 çayır (parlak)."""
    global GRASS_MATS
    if GRASS_MATS is None:
        GRASS_MATS = [C.grass_mat('ng0', '#3f8a22', '#cfe85c', 0.45), C.grass_mat('ng1', '#5c9e2c', '#e6f27c', 0.45),
                      C.grass_mat('ng2', '#7f7d2e', '#ecd977', 0.4), C.grass_mat('ng3', '#2d6a34', '#94c95c', 0.35),
                      C.grass_mat('ng4', '#4d7c5c', '#b8d6a6', 0.35), C.grass_mat('ng5', '#469a26', '#dcf06a', 0.5)]
    return GRASS_MATS

def sample(arr, L, x, z):
    """İkili doğrusal örnek (en yakın hücre kare kare boşluk bırakıyordu)."""
    fi = (x - L.x0) / L.step; fj = (z - L.z0) / L.step
    i = int(max(0, min(L.nx - 2, math.floor(fi)))); j = int(max(0, min(L.nz - 2, math.floor(fj)))); tx, tz = fi - i, fj - j
    return float((arr[j, i] * (1 - tx) + arr[j, i + 1] * tx) * (1 - tz) + (arr[j + 1, i] * (1 - tx) + arr[j + 1, i + 1] * tx) * tz)

def macro_grass(L, ctx, px, pz, hd, rad=30.0, tries=1800000, avoid=None, seed=1):
    """Makro çim telleri: petin önünde/çevresinde sık, uzaklaştıkça seyrek ve iri (g9 yöntemi)."""
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    cx, cz = px + fx * 6, pz + fz * 6
    R = random.Random(seed); buckets = [[] for _ in range(6)]
    for _ in range(tries):
        x = cx + R.uniform(-rad, rad); z = cz + R.uniform(-rad, rad)
        dx, dz = x - px, z - pz; d = math.hypot(dx, dz)
        if d > rad or (d > 7 and (dx * fx + dz * fz) / d < -0.35): continue
        g = sample(L.gw, L, x, z)
        fall = 1.0 if d < 6 else (6.0 / d) ** 1.4
        if R.random() > g * fall: continue
        if avoid and avoid(x, z): continue
        fw = ctx.biome_w('forest', x, z); cw = ctx.biome_w('snow', x, z, 0.5); mw = ctx.biome_w('meadow_lake', x, z)
        n = MN.noise(V((x * 0.12, z * 0.12, 3))) * 0.5 + 0.5
        dry = MN.noise(V((x * 0.04, z * 0.04, 9))) * 0.5 + 0.5
        r = R.random()
        if r < fw * 0.9: k = 3
        elif r < cw * 0.8: k = 4
        elif dry > 0.6 and r < 0.55: k = 2
        elif mw > 0.4 and r < 0.6: k = 5
        elif n > 0.56: k = 1
        else: k = 0
        buckets[k].append((x, z, L.height(x, z) - 0.01, 1.0 + max(0.0, d - 6) / 9.0))
    ms = grass_mats()
    for k, pts in enumerate(buckets):
        if pts: C.blades('ngrass%d' % k, pts, ms[k], h=(0.12, 0.3), w=(0.012, 0.028), bend=0.5, segs=3, seed=10 + k)
    return sum(len(b) for b in buckets)

def flowers(L, ctx, px, pz, hd, clusters=26, rad=20.0, seed=3, meadow=False):
    """Çiçek kümeleri: mavi, pembe, sarı, beyaz (G8). Kümeler gerçek çiçek tarlası gibi öbek öbek."""
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    R = random.Random(seed); heads = []; dz_w = []; dz_y = []; blue = []
    n = 0
    while n < clusters * 6 and len(heads) + len(dz_w) < clusters * 40:
        n += 1
        t = R.uniform(2.5, rad); s = R.uniform(-0.75, 0.75) * t
        cx = px + fx * t + fz * s; cz = pz + fz * t - fx * s
        if sample(L.gw, L, cx, cz) < 0.4: continue
        if not meadow and R.random() > 0.35: continue
        kind = R.randrange(4); cnt = R.randint(8, 18) if meadow else R.randint(4, 9)
        for _ in range(cnt):
            x = cx + R.gauss(0, 0.45); z = cz + R.gauss(0, 0.45); y = L.height(x, z)
            if kind == 0: dz_w.append((x, z, y, 1.0))
            elif kind == 1: dz_y.append((x, z, y, 0.8))
            elif kind == 2: blue.append((x, z, y + R.uniform(0.12, 0.24)))
            else: heads.append((x, z, y + R.uniform(0.16, 0.3)))
    if dz_w: C.daisies('n_daisy', dz_w, seed=seed, petal='#ffffff', heart='#f2c230', r=(0.05, 0.08))
    if dz_y: C.daisies('n_yel', dz_y, seed=seed + 1, petal='#ffd23e', heart='#e08a20', r=(0.045, 0.065))
    if heads: flower_heads(heads, R, size=1.5)
    if blue:
        BL = S5.m_flat('#5a8fe8', 0.12, 9, 'n_bluef')
        for (x, z, y) in blue:
            S5.blob('n_bl', (x, z, y), (0.06, 0.06, 0.08), BL, sub=0, seg=6)

def rocks_ring(L, pts, mat_moss=0.55, seed=7):
    """Kıyı/göl taşları: yosun başlıklı, yarısı toprağa gömülü."""
    rm = C.rock_mat('n_rock%d' % seed, base='#9c968e', dark='#6a6676', moss='#5f9c3a', moss_amt=mat_moss)
    R = random.Random(seed); out = []
    for (x, z, s) in pts:
        out.append(C.rock('n_r', (x, z, L.height(x, z) + s * 0.1), s, rm, seed=R.randrange(999), flat=R.uniform(0.5, 0.8),
                          sharp=0.6, rot=R.uniform(0, 6.3), sub=3))
    return out

# ------------------------------------------------------------------ çekim ayrıntıları

def near_meadow_lake(L, ctx, px, pz, hd):
    b = ctx.BIOMES['meadow_lake']; R = random.Random(11)
    # kıyı halkası: ıslak toprak bandının üstüne saz ve taş (göl çanağı arazide negatif tepe, kıyı ≈ yükseklik 0)
    reeds = []; stones = []
    for k in range(2600):
        a = R.uniform(0, math.tau); rr = R.uniform(2.0, 9.0); x = b['x'] + math.cos(a) * rr; z = b['z'] + math.sin(a) * rr
        h = L.height(x, z)
        if -0.22 < h < 0.12 and R.random() < 0.55: reeds.append((x, z, h))
        elif 0.0 < h < 0.35 and R.random() < 0.02: stones.append((x, z, R.uniform(0.15, 0.45)))
    RD = [m_leaf('#3d5f24', '#5f8a30', '#a6b85a', '#c9cf86', 'reedA'), m_leaf('#55662a', '#7f8a3a', '#c4b46a', '#ddd08e', 'reedB')]
    def build(bm):
        out = []
        for q, (x, z, h) in enumerate(reeds):
            for _ in range(R.randint(3, 6)):
                bb = R.uniform(0, 6.28); up = R.uniform(0.86, 0.98)
                d = V((math.cos(bb) * (1 - up), math.sin(bb) * (1 - up), up)).normalized(); side = V((-math.sin(bb), math.cos(bb), 0))
                for f in blade(bm, V((x + R.uniform(-0.1, 0.1), z + R.uniform(-0.1, 0.1), h - 0.05)), d, side, R.uniform(0.55, 1.15), 0.016, 0.25, segs=3):
                    out.append((f, q % 2))
        return out
    mesh_from_blades('reeds', build, RD)
    # saz başları (kahverengi püskül)
    TB = S5.m_flat('#6a4426', 0.12, 9, 'n_cattail')
    for (x, z, h) in reeds[::9]: S5.blob('n_cat', (x, z, h + R.uniform(0.75, 1.05)), (0.02, 0.02, 0.07), TB, sub=0, seg=6)
    rocks_ring(L, stones, 0.45, 12)
    # nilüfer yaprakları
    LP = S5.m_flat('#3f8f3a', 0.15, 6, 'n_lily'); PK = S5.m_flat('#ff9fc8', 0.1, 9, 'n_lilyf')
    for k in range(22):
        a = R.uniform(0, math.tau); rr = R.uniform(0.6, 3.6); x = b['x'] + math.cos(a) * rr * 1.2; z = b['z'] + math.sin(a) * rr
        if L.height(x, z) < -0.5:
            S5.blob('n_lp', (x, z, 0.015), (0.32, 0.3, 0.012), LP, sub=1, seg=10)
            if k % 4 == 0: S5.blob('n_lf', (x + 0.05, z, 0.07), (0.07, 0.07, 0.05), PK, sub=1, seg=8)
    flowers(L, ctx, px, pz, hd, clusters=60, rad=24, seed=5, meadow=True)

def near_coast(L, ctx, px, pz, hd):
    """Kıyı: ıslak kum + köpük şeridi (yerel yüksek çözünürlüklü maske) + yosunlu kıyı taşları."""
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    cx, cz = px + fx * 14, pz + fz * 14; S = 60.0; n = 480
    xs = np.linspace(cx - S / 2, cx + S / 2, n); zs = np.linspace(cz - S / 2, cz + S / 2, n)
    H = np.array([[L.height(x, z) for x in xs] for z in zs], np.float32)
    rng = np.random.default_rng(4)
    X, Z = np.meshgrid(xs, zs)
    nz = np.array([[MN.noise(V((x * 0.35, z * 0.35, 2))) for x in xs[::4]] for z in zs[::4]], np.float32)
    nz = np.kron(nz, np.ones((4, 4), np.float32))[:n, :n]
    line = np.clip(1 - np.abs(H + 0.06 + 0.05 * nz) / 0.07, 0, 1)                       # kıyı çizgisindeki köpük
    band2 = np.clip(1 - np.abs(H + 0.32 + 0.08 * nz) / 0.05, 0, 1) * 0.75               # ikinci, kırık dalga çizgisi
    lace = (np.sin((H * 26.0) + nz * 4.0) > 0.55) * np.clip((H + 0.6) / 0.5, 0, 1) * (H < -0.05) * 0.55   # dantel köpük
    foam = np.clip(np.maximum(line, np.maximum(band2, lace)) * (0.6 + 0.5 * rng.random((n, n))), 0, 1).astype(np.float32)
    img = bpy.data.images.new('n_foam', n, n, float_buffer=True)
    px_ = np.zeros((n, n, 4), np.float32); px_[..., 0] = foam; px_[..., 3] = 1; img.pixels.foreach_set(px_.ravel())
    bpy.ops.mesh.primitive_plane_add(size=S, location=(cx, cz, 0.012)); o = bpy.context.object; o.name = 'n_foam'
    m = bpy.data.materials.new('n_foam_m'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links
    bs = N['Principled BSDF']; bs.inputs['Base Color'].default_value = (0.95, 0.98, 1.0, 1); bs.inputs['Roughness'].default_value = 0.4
    t = N.new('ShaderNodeTexImage'); t.image = img; img.colorspace_settings.name = 'Non-Color'; t.extension = 'CLIP'
    sep = N.new('ShaderNodeSeparateColor'); Lk.new(t.outputs['Color'], sep.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.35; mr.inputs['From Max'].default_value = 0.55
    Lk.new(sep.outputs[0], mr.inputs['Value']); Lk.new(mr.outputs[0], bs.inputs['Alpha'])
    o.data.materials.append(m)
    # kıyı taşları: su çizgisinde, bazıları yarı batık
    R = random.Random(21); pts = []
    for k in range(400):
        t_ = R.uniform(4, 34); s = R.uniform(-14, 14); x = px + fx * t_ + fz * s; z = pz + fz * t_ - fx * s
        h = L.height(x, z)
        if -0.5 < h < 0.35 and R.random() < 0.12: pts.append((x, z, R.uniform(0.3, 1.1)))
    rocks_ring(L, pts[:26], 0.5, 22)
    # kumda deniz kabuğu/çakıl
    PB = m_rock(name='n_peb')
    for k in range(120):
        t_ = R.uniform(1, 18); s = R.uniform(-8, 8); x = px + fx * t_ + fz * s; z = pz + fz * t_ - fx * s; h = L.height(x, z)
        if 0.05 < h < 0.6: pebble((x, z, h + 0.02), R.uniform(0.04, 0.1), PB, k)

class TR:
    """ski_mountain_v4.drape için arazi arayüzü (Blender x,y = oyun x,z)."""
    def __init__(self, L): self.L = L
    def h(self, x, y): return self.L.height(x, y)

def near_ski(L, ctx, px, pz, hd):
    """v4 after_ski: karlı tepenin yamacından inen ezilmiş kar pisti, kapı bayrakları, kayak sehpası, kardan adam, tabela, kar taneleri."""
    tr = TR(L); peak = [hh for hh in ctx.LAYOUT['terrain']['hills'] if hh.get('snow')][0]
    x0, z0 = peak['x'] + 1.0, peak['z'] - 3.0; x1, z1 = px + 1.5, pz + 6.0
    pts = []
    for i in range(81):
        t = i / 80; pts.append((x0 + (x1 - x0) * t + 1.0 * math.sin(t * 5.0), z0 + (z1 - z0) * t))
    # pist malzemesi: açık mavi kenar + ince sıkıştırılmış kar çizgileri
    def pist_m():
        def b(nt, bsdf):
            N = nt.nodes; Lk = nt.links; uv = SM.kit.uv_node(nt); sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(uv.outputs[0], sep.inputs[0])
            ed = N.new('ShaderNodeMath'); ed.operation = 'PINGPONG'; ed.inputs[1].default_value = 0.5; Lk.new(sep.outputs['X'], ed.inputs[0])
            mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.08; Lk.new(ed.outputs[0], mr.inputs['Value'])
            gr = N.new('ShaderNodeMath'); gr.operation = 'SINE'; mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 60
            Lk.new(sep.outputs['Y'], mm.inputs[0]); Lk.new(mm.outputs[0], gr.inputs[0])
            g2 = N.new('ShaderNodeMapRange'); g2.inputs['From Min'].default_value = -1; g2.inputs['To Min'].default_value = 0.94; g2.inputs['To Max'].default_value = 1.0; Lk.new(gr.outputs[0], g2.inputs['Value'])
            base = SM.ramp(nt, [(0.0, '#9cc0ea'), (1.0, '#f4f8ff')]); Lk.new(mr.outputs[0], base.inputs['Fac'])
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            Lk.new(base.outputs[0], mx.inputs[6]); Lk.new(g2.outputs[0], mx.inputs[7]); Lk.new(mx.outputs[2], bsdf.inputs['Base Color'])
            bsdf.inputs['Roughness'].default_value = 0.55
        return SM.nodes_mat('n_pist', b)
    SM.drape(tr, pts, lambda s: 1.1 + 0.5 * s, pist_m(), lift=0.1, name='n_pist', uvlen=0.25)
    DK = SM.m_wood('#7a5232', 'n_skipole'); BL = SM.m_flat('#2f8adf', 0.08, 8, 'n_blueflag'); RDm = SM.m_flat('#ff5a5a', 0.08, 8, 'n_redflag')
    for k in range(1, 10):
        x, y = pts[k * 8]; nx = 1.4 + 0.4 * k / 9
        for sx in (-1, 1):
            xx = x + sx * nx; z = tr.h(xx, y)
            SM.tube('n_gate', [(xx, y, z - 0.05), (xx, y, z + 0.75)], [0.025, 0.025], DK, res=2)
            SM.prism('n_pf', [(0, 0), (0.3 * sx, -0.08), (0, -0.19)], 0.012, BL if k % 2 else RDm, loc=(xx, y, z + 0.72), bevel=0.003)
    # alt: oyun girişi alanı (kar ile çim arasındaki kırağı bandı)
    sx_, sz_ = px - 3.0, pz + 3.5
    SM.ski_rack(sx_, sz_, tr.h(sx_, sz_), yaw=-30)
    SM.snowman((px + 3.2, pz + 4.5, tr.h(px + 3.2, pz + 4.5)), 1.2)
    SM.signpost(px + 1.8, pz + 1.5, tr.h(px + 1.8, pz + 1.5), 60, [(0, '#e8463c'), (150, '#2f8adf')])
    # kar kenarı: funda + kuru ot; uçuşan kar taneleri (kameranın önünde)
    R = random.Random(9)
    for k in range(260):
        x = px + R.uniform(-16, 16); z = pz + R.uniform(-2, 24); i, j = L.at(x, z)
        sf = float(L.sf[j, i])
        if 0.08 < sf < 0.55 and R.random() < 0.6: SM.heather(x, z, L.height(x, z) - 0.01, 300 + k)
    SM.snowflakes((px - 9, px + 9, pz - 4, pz + 16), L.height(px, pz) + 0.4, L.height(px, pz) + 7, 520, 3)

def near_rocks(L, ctx, px, pz, hd):
    """g4: çimenlikte yosunlu kaya kümesi + dikili taşlar; tabanında çakıl ve çimen geçişi."""
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    rm = C.rock_mat('n_g4rock', moss_amt=0.45); R = random.Random(7); made = []
    cx, cz = px + fx * 9, pz + fz * 9
    for i in range(26):
        aa = R.uniform(0, math.tau); r = R.uniform(0.6, 7.0); x = cx + math.cos(aa) * r * 1.2; z = cz + math.sin(aa) * r * 0.9
        if math.hypot(x - px, z - pz) < 2.8: continue
        s = R.uniform(0.35, 1.25) * (1.35 if r < 3 else 1.0)
        made.append(C.rock('n_g4r', (x, z, L.height(x, z) + s * 0.12), s, rm, seed=i, flat=R.uniform(0.55, 0.9), rot=R.uniform(0, 6.3), tall=R.uniform(0.6, 1.0)))
    for i, (ox, oz, s, t) in enumerate([(-6.5, 1.0, 0.62, 3.2), (-4.8, 4.6, 0.5, 2.6), (6.0, 3.2, 0.55, 3.4), (2.4, 8.2, 0.45, 2.5), (-2.2, 9.6, 0.42, 2.9), (4.6, -0.8, 0.36, 2.2)]):
        x = cx + ox * fz + oz * fx; z = cz - ox * fx + oz * fz
        made.append(C.rock('n_g4m', (x, z, L.height(x, z) + s * t * 0.5), s, rm, seed=100 + i, flat=1.0, sharp=0.9, rot=R.uniform(0, 6.3), tall=t, thin=0.42))
    PB = m_rock(name='n_peb2')
    for o in made:
        for q in range(5):
            aa = R.uniform(0, 6.28); rr = o.scale.x * R.uniform(0.95, 1.4); x = o.location.x + math.cos(aa) * rr; z = o.location.y + math.sin(aa) * rr
            pebble((x, z, L.height(x, z) + 0.02), R.uniform(0.05, 0.13), PB, q + int(o.location.x * 7))
    return [(o.location.x, o.location.y, o.scale.x * 0.85) for o in made]

def near_forest(L, ctx, px, pz, hd):
    """G2: orman zemini — kırmızı-kahve dökülmüş yapraklar, mantarlar, eğreltiler, dallar."""
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a); R = random.Random(13)
    cx, cz = px + fx * 7, pz + fz * 7
    hf = lambda x, y: L.height(x, y)
    S5.leaf_litter((cx - 11, cx + 11, cz - 11, cz + 11), 9000, 70, hf)
    S5.leaf_litter((px - 4, px + 4, pz - 4, pz + 4), 2500, 71, hf)
    for k in range(14):
        t = R.uniform(2.5, 14); s = R.uniform(-5, 5); x = px + fx * t + fz * s; z = pz + fz * t - fx * s
        cap = ('#c4462e', '#d9873a', '#b8643a')[k % 3]
        S5.mushroom((x, z, L.height(x, z) - 0.01), R.uniform(0.12, 0.26), 400 + k, cap=cap, spots=k % 3 == 0)
    for k in range(40):
        t = R.uniform(2.5, 18); s = R.uniform(-9, 9); x = px + fx * t + fz * s; z = pz + fz * t - fx * s
        if abs(s) < 1.6 and t < 10: continue
        SM.fern(x, z, L.height(x, z) - 0.02, 500 + k, size=R.uniform(0.5, 0.95))
    for k in range(18):
        t = R.uniform(1.5, 12); s = R.uniform(-5, 5); x = px + fx * t + fz * s; z = pz + fz * t - fx * s
        aa = R.uniform(0, 6.28); l = R.uniform(0.3, 0.7)
        S5.twig((x, z, L.height(x, z) + 0.01), (x + math.cos(aa) * l, z + math.sin(aa) * l, L.height(x + math.cos(aa) * l, z + math.sin(aa) * l) + 0.01), 600 + k)

def build(L, ctx, shot, px, pz, hd):
    """Çekime göre yakın ayrıntı; yaratılan nesneleri döndürür (çekimden sonra silinir)."""
    import time; t0 = time.time()
    # ağır sahnede her bpy.ops çağrısı tüm parçacıkları yeniden değerlendirir: kurulum süresince görünümde kapat
    mods = [m for o in bpy.context.scene.objects for m in o.modifiers if m.type == 'PARTICLE_SYSTEM' and m.show_viewport]
    for m in mods: m.show_viewport = False
    before = set(bpy.data.objects)
    try:
        _build(L, ctx, shot, px, pz, hd)
    finally:
        for m in mods: m.show_viewport = True
    made = [o for o in bpy.data.objects if o not in before]
    print('ayrıntı tamam', shot, len(made), 'nesne', round(time.time() - t0, 1), 's', flush=True)
    return made

def _build(L, ctx, shot, px, pz, hd):
    import time; t0 = time.time()
    avoid = None
    if shot == 'kayalik':
        rk = near_rocks(L, ctx, px, pz, hd)
        avoid = lambda x, z: any(math.hypot(x - a, z - b) < r for (a, b, r) in rk)
    if shot == 'cayir_gol': near_meadow_lake(L, ctx, px, pz, hd)
    if shot == 'kiyi': near_coast(L, ctx, px, pz, hd)
    if shot == 'kar': near_ski(L, ctx, px, pz, hd)
    if shot == 'orman': near_forest(L, ctx, px, pz, hd)
    print('ayrıntı', shot, round(time.time() - t0, 1), 's', flush=True)
    if shot in ('koy_merkezi', 'kayalik', 'kar', 'kiyi'): flowers(L, ctx, px, pz, hd, clusters=18, seed=hash(shot) % 97)
    n = macro_grass(L, ctx, px, pz, hd, avoid=avoid, seed=len(shot))
    print('yakın çim', shot, n, round(time.time() - t0, 1), 's', flush=True)
