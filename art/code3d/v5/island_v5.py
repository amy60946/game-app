# Ada v5 taslağı (20 Ekim 2026, kullanıcı: 49 referans görselin sanat yönüyle mevcut adayı güncelle, haritayı büyütebilirsin).
# Arazi oyunun kendi mantığından (IslandTerrain) ızgara olarak dökülür (C# aracı: /tmp/claude-0/terrdump), burada boyanır.
# Referans görseller yalnız kalite/hava hedefi; hiçbir şekil/doku kopyalanmaz, hepsi kodla özgün.
#   /tmp/claude-0/bpyenv/bin/python -I island_v5.py -- <dump.json> <çıktı_klasörü> <mod: before|after> <çekim,...> [örnek] [ölçek]
import sys, os, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', 'v4')): sys.path.insert(0, p)
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, noise as MN
import common as C
from assets_v3 import m_leaf, m_bark, blade, mesh_from_blades
import ski_mountain_v4 as SM
import scenes_v5 as S5

ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
PETS = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Pets')
LAYOUT = json.load(open(os.path.join(HERE, 'island_v5_layout.json'), encoding='utf-8'))
BIOMES = LAYOUT['terrain']['_biomes']

def ss(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))) if b != a else 0.0
    return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def mixc(a, b, t): return tuple(lerp(a[i], b[i], t) for i in range(3))
def hexc(h): return C.srgb(h)[:3]

# ------------------------------------------------------------------ arazi verisi

class Land:
    def __init__(self, path, after):
        d = json.load(open(path)); self.d = d
        self.nx, self.nz, self.step = d['nx'], d['nz'], d['step']
        self.x0, self.z0 = d['minx'], d['minz']
        self.h = np.array(d['height'], dtype=np.float32).reshape(self.nz, self.nx)
        self.c = np.array(d['coast'], dtype=np.float32).reshape(self.nz, self.nx)
        self.m = np.array(d['mix'], dtype=np.float32).reshape(self.nz, self.nx, 5)   # su, kum, patika, kaya, kar
        self.after = after
        df = d['def']; self.rx, self.rz, self.cz = df['rx'], df['rz'], df['cz']
        if after: self.cliffs()
        self.slope = self.calc_slope()

    def xz(self, i, j): return self.x0 + i * self.step, self.z0 + j * self.step

    def cliffs(self):
        """Kuzey-doğu kıyısı kayalık yar: kumsal yerine çim düzlüğü kıyıya kadar uzanır, sonra dik iner (oyunda Coast'a kesim)."""
        cf = BIOMES['cliff_coast']; a0, a1 = math.radians(cf['from_deg']), math.radians(cf['to_deg'])
        self.cliffw = np.zeros_like(self.h)
        for j in range(self.nz):
            for i in range(self.nx):
                x, z = self.xz(i, j); ang = math.atan2((z - self.cz) / self.rz, x / self.rx)
                w = ss(a0 - 0.25, a0 + 0.1, ang) * (1 - ss(a1 - 0.1, a1 + 0.25, ang))
                if w <= 0: continue
                c = float(self.c[j, i])
                top = 2.4 + 0.8 * MN.noise(V((x * 0.07, z * 0.07, 3.0)))
                hh = float(self.h[j, i])
                plateau = lerp(hh, max(hh, top), ss(0.82, 0.93, c))
                drop = lerp(plateau, -1.9, ss(0.975, 1.0 + 0.012 * MN.noise(V((x * 0.2, z * 0.2, 1))), c))
                self.h[j, i] = lerp(hh, drop, w)
                self.cliffw[j, i] = w * ss(0.95, 0.99, c)
                if c < 0.985: self.m[j, i, 1] *= (1 - w)   # kum yok
        self.m[:, :, 0] = np.clip((0.05 - self.h) / 0.25, 0, 1)

    def calc_slope(self):
        gz, gx = np.gradient(self.h, self.step)
        return np.sqrt(gx * gx + gz * gz)

    def height(self, x, z):
        fi = (x - self.x0) / self.step; fj = (z - self.z0) / self.step
        i = int(max(0, min(self.nx - 2, math.floor(fi)))); j = int(max(0, min(self.nz - 2, math.floor(fj))))
        tx, tz = fi - i, fj - j; h = self.h
        return float((h[j, i] * (1 - tx) + h[j, i + 1] * tx) * (1 - tz) + (h[j + 1, i] * (1 - tx) + h[j + 1, i + 1] * tx) * tz)

    def at(self, x, z):
        i = int(round((x - self.x0) / self.step)); j = int(round((z - self.z0) / self.step))
        i = max(0, min(self.nx - 1, i)); j = max(0, min(self.nz - 1, j)); return i, j

def biome_w(name, x, z, soft=0.35):
    b = BIOMES[name]; d = math.hypot(x - b['x'], z - b['z']); r = b['r']
    return ss(r, r * (1 - soft), d + MN.noise(V((x * 0.12, z * 0.12, 7))) * r * 0.25)

# ------------------------------------------------------------------ boyalı zemin rengi

def snow_f(x, z, sn, slope, hh):
    """Kar örtüsü 0..1: oyunun kar ağırlığı × yükseklikle kar çizgisi (gürültülü, eriyen kenar) − dik yamaçta kaya şeritleri."""
    n1 = MN.noise(V((x * 0.09, z * 0.09, 1.3))) * 0.5 + 0.5; n2 = MN.noise(V((x * 0.35, z * 0.35, 5))) * 0.5 + 0.5
    sf = ss(0.15, 0.6, sn + (n2 - 0.5) * 0.5) * ss(6.5, 9.5, hh + (n1 - 0.5) * 3.0)
    streak = ss(0.55, 0.72, MN.noise(V((x * 0.55, z * 0.13, 4))) * 0.5 + 0.5) * ss(0.6, 1.1, slope)
    sf *= 1 - streak * 0.85
    melt = ss(0.62, 0.72, MN.noise(V((x * 0.22, z * 0.22, 8))) * 0.5 + 0.5) * ss(0.03, 0.3, sn) * ss(2.0, 4.5, hh)
    return max(sf, melt * 0.92)                                                           # erimekte olan kar lekeleri kenarda

def ground_colors(L, x, z, i, j, hh):
    w, s, p, r, sn = (float(v) for v in L.m[j, i]); slope = float(L.slope[j, i])
    n1 = MN.noise(V((x * 0.09, z * 0.09, 1.3))) * 0.5 + 0.5; n2 = MN.noise(V((x * 0.35, z * 0.35, 5))) * 0.5 + 0.5
    if not L.after:   # bugünkü oyun (MapWorld.PaintGround)
        g = mixc((0.34, 0.52, 0.25), (0.45, 0.63, 0.31), n1)
        c = mixc(g, (0.97, 0.87, 0.63), s); c = mixc(c, (0.62, 0.57, 0.52), r); c = mixc(c, (0.97, 0.98, 1.0), sn)
        c = mixc(c, (0.83, 0.66, 0.45), p); c = mixc(c, (0.55, 0.78, 0.82), w)
        return tuple(v ** 2.2 for v in c)
    # v5: canlı ama dengeli çim; biyom tonları; kuru ot lekeleri; toprak açıklıkları
    g = mixc(hexc('#4f9a2e'), hexc('#86c84a'), n1)
    g = mixc(g, hexc('#b5d652'), ss(0.62, 0.85, n2) * 0.5)                              # açık sarı-yeşil lekeler
    dry = ss(0.55, 0.75, MN.noise(V((x * 0.04, z * 0.04, 9))) * 0.5 + 0.5)
    g = mixc(g, hexc('#b3a748'), dry * 0.55)                                              # sararmış çim
    g = mixc(g, hexc('#2d6a33'), biome_w('forest', x, z) * 0.6)                           # orman: koyu mavi-yeşil
    g = mixc(g, hexc('#58a03a'), biome_w('meadow_lake', x, z) * 0.4)
    cold = biome_w('snow', x, z, 0.5); g = mixc(g, hexc('#5f8a66'), cold * 0.6)           # kar yakını soğuk ton
    dirt = ss(0.7, 0.82, MN.noise(V((x * 0.16, z * 0.16, 2))) * 0.5 + 0.5) * (1 - s) * 0.7
    g = mixc(g, hexc('#8a6a3e'), dirt * (0.6 + 0.4 * biome_w('forest', x, z)))
    c = g
    c = mixc(c, mixc(hexc('#e9d39a'), hexc('#d9bd7f'), n2), s)                           # kum
    c = mixc(c, hexc('#b59a6e'), ss(0.35, 0.0, hh) * s * 0.6)                           # ıslak kum: su kıyısında koyu
    lk = BIOMES['meadow_lake']; dl = math.hypot(x - lk['x'], z - lk['z'])
    if dl < 9.0:                                                                          # göl kıyısı: ıslak toprak + kum halkası
        ring = ss(0.45, 0.05, abs(hh - 0.05)) * ss(9.0, 6.0, dl)
        c = mixc(c, mixc(hexc('#6f5a3c'), hexc('#c9b07e'), ss(-0.1, 0.3, hh)), ring * 0.85)
    rockc = mixc(hexc('#8d8a86'), hexc('#a9a199'), n2)
    rockc = mixc(rockc, hexc('#6c6878'), ss(0.4, 0.8, n1) * 0.4)                          # soğuk mor-gri
    rw = max(r, ss(0.8, 1.3, slope) * 0.9, getattr(L, 'cliffw', np.zeros((1, 1)))[j, i] if hasattr(L, 'cliffw') else 0)
    c = mixc(c, rockc, rw)
    snowc = mixc(hexc('#f4f7fb'), hexc('#c9d6ee'), ss(0.5, 1.4, slope) * 0.6)
    sf = snow_f(x, z, sn, slope, hh)
    c = mixc(c, rockc, sn * (1 - sf) * 0.4)
    c = mixc(c, hexc('#c4d2c8'), ss(0.0, 0.35, sn) * (1 - sf) * 0.45)                      # kırağı bandı (kar → kırağı → soğuk çim)                                              # kar altı: kaya + seyrek ot
    c = mixc(c, snowc, sf)                                                                # eriyen kar: gürültülü sınır
    pathc = mixc(hexc('#a07a4c'), hexc('#c19a66'), n2)
    c = mixc(c, pathc, p)
    c = mixc(c, hexc('#5a8f94'), w * 0.6)
    c = mixc(c, hexc('#0f4f86'), ss(-0.3, -1.4, hh) * 0.9)                                # deniz tabanı: açık denizle aynı ton
    return c

def build_terrain(L):
    nx, nz = L.nx, L.nz
    verts = []; cols = []
    for j in range(nz):
        for i in range(nx):
            x, z = L.xz(i, j); hh = float(L.h[j, i])
            verts.append((x, z, hh)); cols.append(ground_colors(L, x, z, i, j, hh))
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(nz - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new('ground'); me.from_pydata(verts, [], faces)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    flat = [v for c in cols for v in (c[0], c[1], c[2], 1.0)]; ca.data.foreach_set('color', flat)
    C.smooth_all(me)
    o = C.link('ground', me, C.vcol_mat('ground_m', rough=0.92, bump=0.18 if L.after else 0.0))
    if not L.after:
        b = o.data.materials[0].node_tree.nodes['Principled BSDF']
    return o

def weights(L, o):
    """Parçacık yoğunluk grupları: çim, çiçek, patika çakılı, orman zemini, kar kenarı."""
    groups = {k: o.vertex_groups.new(name=k) for k in ('grass', 'flowers', 'pebbles', 'litter', 'heath', 'dry')}
    nx = L.nx; buckets = {k: {} for k in groups}
    L.gw = np.zeros_like(L.h); L.sf = np.zeros_like(L.h)
    for j in range(L.nz):
        for i in range(nx):
            x, z = L.xz(i, j); w, s, p, r, sn = (float(v) for v in L.m[j, i]); sl = float(L.slope[j, i]); hh = float(L.h[j, i])
            if hh < 0.15: continue
            cliff = L.cliffw[j, i] if hasattr(L, 'cliffw') else 0
            sf = snow_f(x, z, sn, sl, hh); L.sf[j, i] = sf
            grass = max(0.0, 1 - max(s, p, r, ss(0.05, 0.5, sf), ss(0.8, 1.2, sl), cliff))
            n = MN.noise(V((x * 0.42, z * 0.42, 11))) * 0.5 + 0.5
            grass *= ss(0.22, 0.4, n)                                  # çimsiz açıklıklar (oyundaki GrassField ile aynı fikir)
            idx = j * nx + i; L.gw[j, i] = grass
            def put(k, v):
                if v > 0.02: buckets[k].setdefault(round(min(1.0, v), 2), []).append(idx)
            put('grass', grass)
            put('flowers', grass * (0.12 + 0.88 * biome_w('meadow_lake', x, z)) * ss(0.45, 0.75, MN.noise(V((x * 0.2, z * 0.2, 4))) * 0.5 + 0.5))
            put('pebbles', p * 0.8 + ss(0.3, 0.6, r) * 0.25 + s * 0.06)
            put('litter', biome_w('forest', x, z) * (1 - p) * 0.9)
            put('heath', biome_w('snow', x, z, 0.6) * ss(0.05, 0.4, sn) * (1 - ss(0.2, 0.6, sf)))
            put('dry', grass * ss(0.55, 0.75, MN.noise(V((x * 0.04, z * 0.04, 9))) * 0.5 + 0.5))
    for k, g in groups.items():
        for val, ids in buckets[k].items(): g.add(ids, val, 'REPLACE')

# ------------------------------------------------------------------ örnek (instance) kaynakları

SCN = None
def proto(name, fn):
    before = set(bpy.data.objects.keys()); fn()
    col = bpy.data.collections.new('P_' + name)
    for o in [o for o in bpy.data.objects if o.name not in before]:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    return col

def inst(col, loc, rot=0.0, s=1.0):
    e = bpy.data.objects.new('i_' + col.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = col
    e.location = V(loc); e.rotation_euler = (0, 0, rot); e.scale = (s, s, s); bpy.context.scene.collection.objects.link(e)
    return e

def tex_mat(name, png):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(png)
    b = nt.nodes['Principled BSDF']; nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.75
    return m

def fbx_proto(path_noext, name, tex_suffixes=('_basecolor.png', '_basecolor.jpg')):
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=path_noext + '.fbx')
    new = [o for o in bpy.data.objects if o.name not in before]
    png = next((path_noext + sfx for sfx in tex_suffixes if os.path.exists(path_noext + sfx)), None)
    m = tex_mat(name + '_m', png) if png else None
    for o in new:
        if o.type == 'MESH' and m: o.data.materials.clear(); o.data.materials.append(m)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ V(c) for o in new if o.type == 'MESH' for c in o.bound_box]
    mn = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    col = bpy.data.collections.new('F_' + name)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    return col, max(mx.x - mn.x, mx.y - mn.y), mn

ENV_CACHE = {}
def env(name, x, z, y, footprint, yaw_deg):
    """Oyundaki RealAssets.Footprint gibi: yatay en büyük boy = footprint, model orijinden zemine oturur. Unity açısı → Blender."""
    if name not in ENV_CACHE:
        p = os.path.join(ENV, name, name)
        if not os.path.exists(p + '.fbx'): ENV_CACHE[name] = None
        else: ENV_CACHE[name] = fbx_proto(p, name)
    if ENV_CACHE[name] is None: return None
    col, w, mn = ENV_CACHE[name]; s = footprint / max(0.01, w)
    return inst(col, (x, z, y - mn.z * s), -math.radians(yaw_deg), s)

# bitki örtüsü kaynakları

def tuft_obj(name, cols, n=34, h=(0.16, 0.34), r=0.16, seed=1):
    m = C.grass_mat(name + '_m', cols[0], cols[1], 0.4)
    R = random.Random(seed); pts = []
    for k in range(n):
        a = R.uniform(0, math.tau); rr = math.sqrt(R.random()) * r; pts.append((math.cos(a) * rr, math.sin(a) * rr, -0.01, R.uniform(0.7, 1.2)))
    o = C.blades(name, pts, m, h=h, w=(0.014, 0.028), segs=3, bend=0.4, seed=seed)
    return o

def flower_tuft(name, petal, heart, seed):
    def mk():
        R = random.Random(seed); pts = [(R.uniform(-0.12, 0.12), R.uniform(-0.12, 0.12), 0.0, R.uniform(0.8, 1.3)) for _ in range(5)]
        C.daisies(name, pts, seed=seed, petal=petal, heart=heart, r=(0.03, 0.05))
        tuft_obj(name + '_g', ('#2f6b1f', '#8fcc48'), n=10, h=(0.1, 0.2), r=0.12, seed=seed + 1)
    return proto(name, mk)

def pebble_obj(name, seed):
    m = C.rock_mat(name + '_m', base='#a59a8c', dark='#7a7068', moss='#6f8f43', moss_amt=0.15)
    o = C.rock(name, (0, 0, 0), 0.06, m, seed=seed, flat=0.55, sharp=0.6, sub=2)
    o.location = V((0, 0, 0.005)); return o

def scatter_all(L, ground, after):
    if not after:
        return
    vis = bpy.data.collections.new('stash'); bpy.context.scene.collection.children.link(vis)
    vis.hide_render = False
    def stash(o):
        for c in list(o.users_collection): c.objects.unlink(o)
        vis.objects.link(o); o.location = V((0, 0, -400)); return o
    gcol = bpy.data.collections.new('grassP')
    for k, (cs, h) in enumerate([(('#2c6b22', '#8fd04a'), (0.16, 0.32)), (('#356f24', '#b5dc58'), (0.14, 0.28)), (('#3a6a26', '#a7c94c'), (0.18, 0.38))]):
        o = tuft_obj('tuft%d' % k, cs, h=h, seed=20 + k); stash(o); gcol.objects.link(o)
    C.scatter(ground, None, 260000, 3, collection=gcol, vgroup='grass', rand_size=0.45, normal_align=0.15)
    dcol = bpy.data.collections.new('dryP'); o = tuft_obj('tuftdry', ('#6f6a2a', '#d9c766'), h=(0.18, 0.4), seed=31); stash(o); dcol.objects.link(o)
    C.scatter(ground, None, 50000, 5, collection=dcol, vgroup='dry', rand_size=0.4)
    fcol = bpy.data.collections.new('flowersP')
    for k, (pt, ht) in enumerate([('#ffffff', '#f2c230'), ('#7fb2ff', '#f6f0d0'), ('#ff9fc8', '#ffe28a'), ('#ffd23e', '#e08a20')]):
        c = flower_tuft('fl%d' % k, pt, ht, 40 + k)
        for ob in list(c.objects): stash(ob); fcol.objects.link(ob)
    C.scatter(ground, None, 26000, 7, collection=fcol, vgroup='flowers', rand_size=0.35)
    pcol = bpy.data.collections.new('pebP')
    for k in range(3): o = pebble_obj('peb%d' % k, 60 + k); stash(o); pcol.objects.link(o)
    C.scatter(ground, None, 22000, 9, collection=pcol, vgroup='pebbles', rand_size=0.8, normal_align=1.0)
    lcol = bpy.data.collections.new('litterP')
    for k in range(2):
        c = proto('litter%d' % k, lambda k=k: S5.leaf_litter((-0.3, 0.3, -0.3, 0.3), 14, 70 + k, lambda x, y: 0.0))
        for ob in list(c.objects): stash(ob); lcol.objects.link(ob)
    C.scatter(ground, None, 9000, 11, collection=lcol, vgroup='litter', rand_size=0.4, normal_align=1.0)
    hcol = bpy.data.collections.new('heathP')
    c = proto('heath', lambda: SM.heather(0, 0, 0, 5))
    for ob in list(c.objects): stash(ob); hcol.objects.link(ob)
    C.scatter(ground, None, 6000, 13, collection=hcol, vgroup='heath', rand_size=0.4)
    GRASS.update(g=gcol, d=dcol, f=fcol, p=pcol, l=lcol)

# ------------------------------------------------------------------ ağaç, kaya, bina yerleşimi

def place_world(L, after):
    d = L.d; R = random.Random(5)
    # yapılar (bölgeler)
    assets = {'region_home': 'b_home', 'region_shop': 'b_shop', 'region_task_board': 'b_task_board', 'region_swim_cove': 'b_swim',
              'region_surf_beach': 'b_surf', 'region_game_hut': 'b_game_hut', 'region_ski_hill': 'b_ski_hill', 'region_garden': 'b_garden',
              'region_pier': 'b_pier', 'region_cave': 'b_cave', 'region_festival': 'b_festival', 'region_mountain': 'b_mountain',
              'region_lighthouse': 'b_lighthouse'}
    for r in d['regions']:
        a = assets.get(r['Id'])
        if r['Id'] == 'region_coconut_grove':
            for k, (ox, oz, s) in enumerate([(-1.5, 0.6, 4.6), (1.4, -0.4, 4.0), (0.2, 1.8, 5.2)]):
                env('palm', r['x'] + ox, r['z'] + oz, L.height(r['x'] + ox, r['z'] + oz) - 0.1, s, k * 120)
            continue
        if after and a == 'b_ski_hill': continue   # v4 kayak tepesi: arazinin kendi karlı tepesi + pist (island_v5_near)
        if a: env(a, r['x'], r['z'], r['pad'] if not r['Water'] else 0.3, r['Size'], r['Yaw'])
    # süsler: oyundaki yerleşim (fener, çit, tabela, sandık) aynen; bitkiler v5'te biyomdan
    veg = {'palm', 'p_tree', 'p_bush', 'p_rock', 'p_flowers'}
    for p in d['props']:
        if after and p['Asset'] in veg and (p['Asset'] != 'palm' or not shot_clear(p['X'], p['Z'])): continue
        env(p['Asset'], p['X'], p['Z'], L.height(p['X'], p['Z']), p['Size'], p['Yaw'])
    if not after: return
    # ağaç kaynakları
    pines = [proto('pine%d' % k, lambda k=k: SM.pine_v4((0, 0, 0), 1.0, 90 + k, lod=0.7)) for k in range(2)]
    pine_snow = proto('pine_snow', lambda: SM.pine_v4((0, 0, 0), 1.0, 97, snow=True, lod=0.7))
    broad = [proto('broad%d' % k, lambda k=k: S5.broadleaf((0, 0, 0), 1.0, 50 + k, spread=1.1, name='broad%d' % k)) for k in range(2)]
    autumn = proto('autumn', lambda: S5.broadleaf((0, 0, 0), 1.0, 57, cols=('#8a3a1c', '#c4602a', '#e89a3a', '#f4c45a'), name='autumn'))
    willow = proto('willow', lambda: S5.willow((0, 0, 0), 1.0, 61))
    RK = C.rock_mat('rockA', base='#9a958e', dark='#6a6672', moss='#5c9a38', moss_amt=0.55)
    RK2 = C.rock_mat('rockB', base='#a8a094', dark='#75707a', moss='#6aa843', moss_amt=0.35)
    rocks = [proto('rock%d' % k, lambda k=k: C.rock('rk%d' % k, (0, 0, 0), 1.0, RK if k % 2 else RK2, seed=200 + k, flat=0.75, sharp=0.6, sub=3)) for k in range(4)]
    menhir = proto('menhir', lambda: C.rock('menhir', (0, 0, 0), 1.0, RK2, seed=300, flat=1.0, sharp=0.8, tall=2.6, thin=0.6, sub=3))
    cliffr = [proto('cliff%d' % k, lambda k=k: C.rock('cl%d' % k, (0, 0, 0), 1.0, RK, seed=400 + k, flat=1.0, sharp=0.9, tall=1.4, sub=3)) for k in range(3)]

    def free(x, z, rad=4.5):
        for r in d['regions']:
            if math.hypot(x - r['x'], z - r['z']) < r['Size'] * 0.7 + rad * 0.3: return False
        for (ax, az, bx, bz) in d['paths']:
            vx, vz = bx - ax, bz - az; ll = vx * vx + vz * vz
            t = 0 if ll == 0 else max(0, min(1, ((x - ax) * vx + (z - az) * vz) / ll))
            if math.hypot(x - (ax + vx * t), z - (az + vz * t)) < 1.6: return False
        return L.height(x, z) > 0.45 and shot_clear(x, z)

    def ring(bname, n, rmin=0.0):
        b = BIOMES[bname]; out = []
        for _ in range(n * 6):
            if len(out) >= n: break
            a = R.uniform(0, math.tau); rr = b['r'] * math.sqrt(R.uniform(rmin, 1.0)); x = b['x'] + math.cos(a) * rr; z = b['z'] + math.sin(a) * rr
            if free(x, z): out.append((x, z))
        return out
    # orman: çam ağırlıklı karışık
    for (x, z) in ring('forest', 46):
        k = R.random(); hgt = R.uniform(6.5, 10.5)
        col = pines[R.randrange(2)] if k < 0.65 else (broad[R.randrange(2)] if k < 0.88 else autumn)
        inst(col, (x, z, L.height(x, z) - 0.1), R.uniform(0, math.tau), hgt if col in pines else hgt * 0.7)
    # dağ yamaçları + kuzey: seyrek çam
    for _ in range(160):
        x = R.uniform(-60, 55); z = R.uniform(18, 62); i, j = L.at(x, z); hh = float(L.h[j, i])
        if hh < 1.5 or float(L.m[j, i, 4]) > 0.4 or not free(x, z): continue
        if float(L.slope[j, i]) > 1.1: continue
        inst(pines[R.randrange(2)], (x, z, hh - 0.1), R.uniform(0, 6.3), R.uniform(5, 8.5))
    # karlı çamlar
    for (x, z) in ring('snow', 22, 0.2):
        i, j = L.at(x, z)
        if float(L.slope[j, i]) > 1.2: continue
        inst(pine_snow, (x, z, L.height(x, z) - 0.1), R.uniform(0, 6.3), R.uniform(4.5, 7.5))
    # çayır + göl: iki büyük ağaç + söğüt
    b = BIOMES['meadow_lake']
    for (ox, oz, s, col) in ((-9.5, -3.0, 9.0, broad[0]), (8.5, -4.5, 8.0, broad[1]), (-5.5, 6.5, 6.5, willow)):
        x, z = b['x'] + ox, b['z'] + oz
        if L.height(x, z) > 0.3: inst(col, (x, z, L.height(x, z) - 0.15), R.uniform(0, 6.3), s)
    # adaya serpiştirilmiş geniş yapraklı + sonbahar ağaçları (biyom çeşitliliği)
    for _ in range(70):
        x = R.uniform(-55, 55); z = R.uniform(-45, 20)
        if not free(x, z) or float(L.m[L.at(x, z)[1], L.at(x, z)[0], 1]) > 0.3: continue
        if biome_w('forest', x, z) > 0.2: continue
        col = broad[R.randrange(2)] if R.random() < 0.8 else autumn
        inst(col, (x, z, L.height(x, z) - 0.1), R.uniform(0, 6.3), R.uniform(4.5, 7))
    # sahil: sık palmiye sırası (güney ve batı kumsalları)
    for _ in range(900):
        x = R.uniform(-62, 62); z = R.uniform(-50, 30); i, j = L.at(x, z)
        sand = float(L.m[j, i, 1]); hh = float(L.h[j, i])
        if not (0.5 < sand and 0.45 < hh < 1.3) or (hasattr(L, 'cliffw') and L.cliffw[j, i] > 0): continue
        if R.random() > 0.08: continue
        if not free(x, z, 2): continue
        env('palm', x, z, hh - 0.08, R.uniform(4.0, 5.6), R.uniform(0, 360))
    # kaya alanı: yosunlu kaya kümeleri + menhirler
    b = BIOMES['rock_field']
    for (x, z) in ring('rock_field', 40):
        inst(rocks[R.randrange(4)], (x, z, L.height(x, z) - 0.3), R.uniform(0, 6.3), R.uniform(0.9, 3.2))
    for (x, z) in ring('rock_field', 8, 0.05):
        inst(menhir, (x, z, L.height(x, z) - 0.3), R.uniform(0, 6.3), R.uniform(1.3, 2.0))
    # dik yamaç kayaları (dağlar) + yar kıyısı kayaları
    for _ in range(4000):
        i = R.randrange(L.nx); j = R.randrange(L.nz); x, z = L.xz(i, j)
        sl = float(L.slope[j, i]); hh = float(L.h[j, i]); cw = L.cliffw[j, i] if hasattr(L, 'cliffw') else 0
        if cw > 0.4 and R.random() < 0.5:
            inst(cliffr[R.randrange(3)], (x, z, hh - 1.2), R.uniform(0, 6.3), R.uniform(1.6, 3.2))
        elif sl > 1.0 and hh > 2.0 and R.random() < 0.18 and free(x, z, 2):
            inst(rocks[R.randrange(4)] if R.random() < 0.6 else cliffr[R.randrange(3)], (x, z, hh - 0.5), R.uniform(0, 6.3), R.uniform(1.2, 3.0))

def water(L, after):
    """Su: derinlikten renk (sığ turkuaz → derin mavi), sığda saydam; kıyıda köpük şeridi. Derinlik = arazi ızgarası."""
    nx, nz = L.nx, L.nz; pad = 700.0
    depth = np.maximum(np.clip(-L.h, 0, 4) / 4.0, np.clip((L.c - 1.0) / 0.3, 0, 1))   # kıyıdan uzaklaştıkça derin
    img = bpy.data.images.new('depth', nx, nz, float_buffer=True)
    px = np.zeros((nz, nx, 4), np.float32); px[..., 0] = depth; px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    foam = np.zeros((nz, nx), np.float32)
    rng = np.random.default_rng(3)
    edge = np.clip(1 - np.abs(L.h + 0.05) / 0.22, 0, 1)
    nzm = rng.random((nz, nx)).astype(np.float32)
    foam = np.clip(edge * (0.55 + 0.6 * nzm), 0, 1) * (L.h < 0.06)
    fimg = bpy.data.images.new('foam', nx, nz, float_buffer=True)
    fp = np.zeros((nz, nx, 4), np.float32); fp[..., 0] = foam; fp[..., 3] = 1.0; fimg.pixels.foreach_set(fp.ravel())
    x0, z0 = L.x0, L.z0; x1, z1 = x0 + (nx - 1) * L.step, z0 + (nz - 1) * L.step
    if after:   # ızgara dışında da derin deniz tabanı (saydam su altında gri gökyüzü görünmesin)
        bpy.ops.mesh.primitive_plane_add(size=1, location=((x0 + x1) / 2, (z0 + z1) / 2, -5.0))
        bed = bpy.context.object; bed.scale = (2000, 2000, 1); bm = bpy.data.materials.new('seabed'); bm.use_nodes = True
        bm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = C.srgb('#0f4f86'); bed.data.materials.append(bm)
    bpy.ops.mesh.primitive_plane_add(size=1, location=((x0 + x1) / 2, (z0 + z1) / 2, 0.0))
    w = bpy.context.object; w.name = 'water'; w.scale = (x1 - x0 + 2 * pad, z1 - z0 + 2 * pad, 1)
    m = bpy.data.materials.new('water_m'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.06 if after else 0.25
    if after: b.inputs['Coat Weight'].default_value = 0.6; b.inputs['Coat Roughness'].default_value = 0.02
    if not after:
        b.inputs['Base Color'].default_value = (0.04, 0.42, 0.85, 1); w.data.materials.append(m); return
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    # nesne koordinatı (-0.5..0.5) → ızgara uv
    sx = (x1 - x0 + 2 * pad) / (x1 - x0); sz = (z1 - z0 + 2 * pad) / (z1 - z0)
    mp.inputs['Scale'].default_value = (sx, sz, 1); mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    Lk.new(tc.outputs['Object'], mp.inputs[0])
    t = N.new('ShaderNodeTexImage'); t.image = img; t.extension = 'EXTEND'; t.interpolation = 'Cubic'; Lk.new(mp.outputs[0], t.inputs[0])
    t.image.colorspace_settings.name = 'Non-Color'
    sep = N.new('ShaderNodeSeparateColor'); Lk.new(t.outputs['Color'], sep.inputs[0])
    rp = S5.ramp(nt, [(0.0, '#7fe6d6'), (0.12, '#2fc0c4'), (0.4, '#1886ae'), (1.0, '#0f4f86')]); Lk.new(sep.outputs[0], rp.inputs['Fac'])
    ft = N.new('ShaderNodeTexImage'); ft.image = fimg; ft.extension = 'EXTEND'; ft.image.colorspace_settings.name = 'Non-Color'; Lk.new(mp.outputs[0], ft.inputs[0])
    fsep = N.new('ShaderNodeSeparateColor'); Lk.new(ft.outputs['Color'], fsep.inputs[0])
    nzt = N.new('ShaderNodeTexNoise'); nzt.inputs['Scale'].default_value = 140; nzt.inputs['Detail'].default_value = 3; Lk.new(mp.outputs[0], nzt.inputs['Vector'])
    fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; Lk.new(fsep.outputs[0], fm.inputs[0]); Lk.new(nzt.outputs['Fac'], fm.inputs[1])
    fr = N.new('ShaderNodeMapRange'); fr.inputs['From Min'].default_value = 0.28; fr.inputs['From Max'].default_value = 0.42; Lk.new(fm.outputs[0], fr.inputs['Value'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (0.95, 0.98, 1.0, 1)
    Lk.new(fr.outputs[0], mx.inputs['Factor']); Lk.new(rp.outputs[0], mx.inputs[6]); Lk.new(mx.outputs[2], b.inputs['Base Color'])
    # saydamlık: sığda sudan kum görünür
    al = N.new('ShaderNodeMapRange'); al.inputs['From Min'].default_value = 0.0; al.inputs['From Max'].default_value = 0.3
    al.inputs['To Min'].default_value = 0.45; al.inputs['To Max'].default_value = 0.97; Lk.new(sep.outputs[0], al.inputs['Value'])
    amx = N.new('ShaderNodeMath'); amx.operation = 'MAXIMUM'; Lk.new(al.outputs[0], amx.inputs[0]); Lk.new(fr.outputs[0], amx.inputs[1])
    Lk.new(amx.outputs[0], b.inputs['Alpha'])
    # hafif dalga tümseği
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.12; wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 60
    wv.inputs['Distortion'].default_value = 6; Lk.new(mp.outputs[0], wv.inputs['Vector']); Lk.new(wv.outputs['Fac'], bn.inputs['Height']); Lk.new(bn.outputs['Normal'], b.inputs['Normal'])
    w.data.materials.append(m)

OKTI = None
def okti(L, x, z, yaw_deg):
    global OKTI
    if OKTI is None:
        p = os.path.join(PETS, 'pet_13_genc', 'pet_13_genc'); OKTI = fbx_proto(p, 'okti', ('_basecolor.jpg',))
    col, w, mn = OKTI
    bpy.context.view_layer.update()
    # boy 1,75 m (PetModels.RealHeight)
    pts = [o.matrix_world @ V(c) for o in col.objects if o.type == 'MESH' for c in o.bound_box]
    hgt = max(p.z for p in pts) - min(p.z for p in pts)
    return inst(col, (x, z, L.height(x, z) - mn.z * (1.75 / hgt)), math.radians(yaw_deg), 1.75 / hgt)

# ------------------------------------------------------------------ çekimler

def look_cam(pos, look, fov=52, lens=None):
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(fov); cd.clip_end = 3000
    o = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(o)
    o.location = V(pos); o.rotation_euler = (V(look) - V(pos)).to_track_quat('-Z', 'Y').to_euler(); bpy.context.scene.camera = o
    return o

def game_shot(L, px, pz, heading_deg, dist=5.6, pitch=20, fov=52):
    """Oyundaki üçüncü şahıs kamera (MapScreen.TargetCamera): petin arkasından ~20°, pet alt üçte birde."""
    a = math.radians(heading_deg); fwd = V((math.sin(a), math.cos(a), 0))
    py = L.height(px, pz); hgt = 1.75
    pivot = V((px, pz, py + hgt * 0.9)); look = V((px, pz, py + hgt * 0.55)) + fwd * 1.5
    dirv = (-fwd * math.cos(math.radians(pitch))) + V((0, 0, math.sin(math.radians(pitch))))
    pos = pivot + dirv * dist; pos.z = max(pos.z, L.height(pos.x, pos.y) + 0.8)
    return pos, look

SHOTS = {   # x, z (oyun), bakış yönü (°, 0 = kuzey)
    'koy_merkezi': (0.0, -6.0, 0), 'kiyi': (50.0, 0.0, 20), 'cayir_gol': (-14.0, 22.5, 0),
    'orman': (-26.0, -14.0, 210), 'kayalik': (16.0, 15.0, 35), 'kar': (-30.0, 24.0, 345),
}

def shot_clear(x, z):
    """Çekim yerlerinde pet ile kamera arası boş kalsın (oyunda da kamera bitkiye girmez: yakın bitki saydamlaşır)."""
    for (px, pz, hd) in SHOTS.values():
        a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
        for t in (0.0, -2.5, -5.0):
            if math.hypot(x - (px + fx * t), z - (pz + fz * t)) < 5.5: return False
        if math.hypot(x - (px + fx * 4), z - (pz + fz * 4)) < 3.0: return False
        if hd == 210 and math.hypot(x - (px + fx * 9), z - (pz + fz * 9)) < 3.0: return False   # orman: içeri bakan koridor
    return True

NEAR = []
import island_v5_near as NEAR_
def set_far_grass(ground, on):
    """Oyun kamerası çekimlerinde genel çim/çiçek parçacıkları kapanır (yakında makro çim var; uzak zemin rengi yeterli)."""
    for md in ground.modifiers:
        if md.type == 'PARTICLE_SYSTEM' and md.particle_system.settings.instance_collection in (GRASS.get('g'), GRASS.get('d'), GRASS.get('f')):
            md.show_render = on

GRASS = {}
def local_grass(L, ground, cx, cz, rad=26.0):
    """Oyun kamerası çekimi: petin çevresinde sık çim/çiçek (uzakta genel dağılım yeterli)."""
    import bmesh
    o = ground.copy(); o.data = ground.data.copy(); o.name = 'grass_patch'
    for mdf in list(o.modifiers): o.modifiers.remove(mdf)
    bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if math.hypot(v.co.x - cx, v.co.y - cz) > rad], context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.location.z += 0.002
    o.hide_render = False; o.display_type = 'WIRE'
    C.scatter(o, None, 520000, 21, collection=GRASS['g'], vgroup='grass', rand_size=0.45, normal_align=0.15)
    C.scatter(o, None, 50000, 23, collection=GRASS['d'], vgroup='dry', rand_size=0.4)
    C.scatter(o, None, 30000, 25, collection=GRASS['f'], vgroup='flowers', rand_size=0.35)
    C.scatter(o, None, 5000, 27, collection=GRASS['p'], vgroup='pebbles', rand_size=0.8, normal_align=1.0)
    C.scatter(o, None, 5000, 29, collection=GRASS['l'], vgroup='litter', rand_size=0.4, normal_align=1.0)
    # yamanın kendisi görünmesin: yalnız parçacıklar
    o.show_instancer_for_render = False
    return o

def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    dump, out, mode = args[0], args[1], args[2]; shots = args[3].split(',')
    samples = int(args[4]) if len(args) > 4 else 48; k = float(args[5]) if len(args) > 5 else 1.0
    after = mode == 'after'; os.makedirs(out, exist_ok=True)
    sc = C.reset(samples=samples, size=(int(1600 * k), int(1000 * k)))
    sc.view_settings.exposure = -0.1
    sc.view_settings.look = 'AgX - Punchy' if after else 'None'
    if after:   # sıcak ana ışık + soğuk mavi/mor dolgu (gölgeler renkli, siyah değil) + açık gökyüzü
        C.sky(sc, strength=1.35, cloud_amt=0.6, top='#5a98e4', mid='#a8d3f6', hor='#eef6fc')
        C.sun(elev=36, azim=-38, energy=5.2, col='#ffe2b4', angle=1.5)
        fl = bpy.data.lights.new('fill', 'SUN'); fl.energy = 1.1; fl.color = (0.62, 0.66, 1.0); fl.angle = math.radians(30)
        fl.cycles.cast_shadow = False
        fo = bpy.data.objects.new('fill', fl); sc.collection.objects.link(fo); fo.rotation_euler = (math.radians(60), 0, math.radians(142))
    else:
        C.sky(sc, strength=0.9, cloud_amt=0.0)
        C.sun(elev=36, azim=-38, energy=3.6, col='#ffffff', angle=1.5)
    L = Land(dump, after)
    ground = build_terrain(L)
    if after: weights(L, ground)
    water(L, after)
    place_world(L, after)
    scatter_all(L, ground, after)
    d = L.d
    for s in shots:
        for o in [o for o in sc.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
        pet = [o for o in sc.objects if o.name.startswith('i_F_okti')]
        for o in pet: bpy.data.objects.remove(o)
        set_far_grass(ground, True)
        if s == 'kusbakisi':
            px, pz = d['plaza']; okti(L, px, pz - 2.0, 0)
            span = max(d['maxx'] - d['minx'], d['maxz'] - d['minz'])
            look = V((0, (d['minz'] + d['maxz']) / 2 + 2, 0)); pos = look + V((0, -span * 0.72, span * 0.62))
            look_cam(pos, look, fov=40); sc.view_settings.exposure = 0.3 if after else -0.1; sc.render.resolution_x, sc.render.resolution_y = int(1600 * k), int(1000 * k)
            name = 'ada_kusbakisi' if after else 'ada_once'
        else:
            x, z, hd = SHOTS[s]; okti(L, x, z, -hd + 180)
            for o in NEAR: bpy.data.objects.remove(o, do_unlink=True)
            NEAR[:] = NEAR_.build(L, sys.modules[__name__], s, x, z, hd) if after else []
            sc.view_settings.exposure = 0.45 if after else -0.1
            set_far_grass(ground, False)
            pos, look = game_shot(L, x, z, hd); look_cam(pos, look)
            sc.render.resolution_x, sc.render.resolution_y = int(1600 * k), int(900 * k); name = s
        if os.environ.get('PROBE'):   # hata ayıklama: görüntü noktasından ışın at, çarpan nesneyi yaz
            cam = sc.camera; dg = bpy.context.evaluated_depsgraph_get(); ru, rd, ld, lu = [cam.matrix_world @ p for p in cam.data.view_frame(scene=sc)]
            for uv in os.environ['PROBE'].split(';'):
                u, v = (float(t) for t in uv.split(',')); p = ld.lerp(rd, u).lerp(lu.lerp(ru, u), v); o = cam.matrix_world.translation
                hit = sc.ray_cast(dg, o, (p - o).normalized()); print('ISIN', u, v, hit[4].name if hit[4] else None, tuple(round(c, 1) for c in hit[1]))
            continue
        sc.render.filepath = os.path.join(out, name + '.png'); bpy.ops.render.render(write_still=True); print('ok', name)

if __name__ == '__main__':
    main()
