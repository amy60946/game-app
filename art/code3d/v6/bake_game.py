# Ada v6 → oyun (22 Ekim 2026; kullanıcı: "tasarımların son versiyonlarını onayladığımı varsayarak oyuna göm").
# Onaylı taslağın (island_v6.py) aynı arazisi, aynı boyası ve aynı süs yerleşimi oyun verisine pişirilir (görünüm 1:1):
#   Resources/Data/island_v6.bytes   yükseklik + yüzey ızgarası (0,5 m): Logic/Island/BakedField
#   Resources/Data/island_v6_layout.json    bölgeler, meydan, patikalar, göl, süsler (tür, x, z, y, dönüş, ölçek)
#   Resources/Env/ground_v6/ground_v6.png   zemin dokusu: taslağın zemin malzemesi (tabaka, çatlak, boyalı kenar) üstten pişirilir; alfa = kum
# Kullanım: /tmp/claude-0/bpyenv/bin/python -I bake_game.py -- <terr.npz> [doku_boyu=2048]
import sys, os, json, math, random, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('ROCK_SUB', '0')            # pişirmede kabartma alt bölmesi gerekmez (doku üstten)
import numpy as np
import bpy
import island_v6 as IV
import terrain_v6 as TV

ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
DATA = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Data')
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
CELL = 0.5

def ss(a, b, x): return IV.ss(a, b, x)

def resample(a, L):
    """0,2 m ızgarayı 0,5 m ızgaraya (çift doğrusal)."""
    xs = np.arange(TV.X0, TV.X1 + 1e-6, CELL); zs = np.arange(TV.Z0, TV.Z1 + 1e-6, CELL)
    fi = (xs - TV.X0) / TV.STEP; fj = (zs - TV.Z0) / TV.STEP
    i0 = np.clip(np.floor(fi).astype(int), 0, L.nx - 2); j0 = np.clip(np.floor(fj).astype(int), 0, L.nz - 2)
    tx = (fi - i0)[None, :]; tz = (fj - j0)[:, None]
    J0, I0 = np.meshgrid(j0, i0, indexing='ij')
    a = a.astype(np.float32)
    return ((a[J0, I0] * (1 - tx) + a[J0, I0 + 1] * tx) * (1 - tz) + (a[J0 + 1, I0] * (1 - tx) + a[J0 + 1, I0 + 1] * tx) * tz), len(xs), len(zs)

def write_field(L, rw):
    d = L.d
    h, nx, nz = resample(L.h, L)
    lake = ((np.hypot(L.X - TV.LAKE['x'], L.Z - TV.LAKE['z']) < TV.LAKE['r'] + 5) & (L.h < TV.LAKE['level'])).astype(np.float32)
    layers = [d['sand'], np.maximum(d['path'], d['snowpath']), L.snw, rw, lake]
    m = [np.clip(resample(x, L)[0], 0, 1) for x in layers]
    with open(os.path.join(DATA, 'island_v6.bytes'), 'wb') as f:
        f.write(b'PV6\x01'); f.write(struct.pack('<iifff', nx, nz, TV.X0, TV.Z0, CELL))
        f.write(np.clip(np.round(h * 100), -32000, 32000).astype('<i2').tobytes())       # cm
        for x in m: f.write(np.round(x * 255).astype(np.uint8).tobytes())               # kum, patika, kar, kaya, göl
    IV.log('ızgara', nx, nz, 'h', float(h.min()), float(h.max()))

# ------------------------------------------------------------------ süs yerleşimi: taslağın kodu, örnek nesneler yerine kayıt

PROPS = []
def record(kind, x, z, y, rot=0.0, s=1.0, sxyz=None):
    PROPS.append(dict(a=kind, x=round(float(x), 2), z=round(float(z), 2), y=round(float(y), 2),
                      r=round(-math.degrees(float(rot)) % 360, 1), s=round(float(s), 3)))   # Blender z dönüşü (saat tersi) → Unity yaw

def stub_protos():
    """Taslaktaki örnek türleri → oyun varlık adları (Resources/Env). Çeşitler oyunda ayrı model olarak gelir."""
    return {
        'round': ['t_round%d' % k for k in range(4)] * 2, 'cypress': ['t_cypress'] * 3, 'birch': ['t_birch'] * 3,
        'pine': ['t_pine%d' % k for k in range(3)] * 2, 'pine_snow': ['t_pine_snow'] * 2, 'bush': ['t_bush'] * 4,
        'boulder': ['r_boulder'] * 5, 'boulderB': ['r_boulder_b'] * 4, 'pebW': ['r_pebble'] * 3, 'palm2': ['t_palm_tall%d' % k for k in range(3)] * 3,
        'palm': 'palm', 'rmA': None, 'rmB': None,
    }

def place_props(L, B):
    IV.inst = lambda col, x, z, y, rot=0.0, s=1.0, sxyz=None: record(col, x, z, y, rot, s if sxyz is None else max(sxyz))
    def env(name, x, z, y, footprint, yaw_deg): PROPS.append(dict(a=name, x=round(x, 2), z=round(z, 2), y=round(y, 2), r=round(yaw_deg % 360, 1), s=round(footprint, 3), fp=1))
    IV.env = env
    IV.cave = lambda *a, **k: None                  # mağara: bölge modeli + tünel oyunda b_cave
    IV.camp = lambda *a, **k: None                  # aşağıda elle
    IV.trail_poles = lambda *a, **k: None           # aşağıda elle
    P = stub_protos()
    IV.PALMS[:] = P['palm2']
    IV.place_world(L, B, P)
    # kamp: ateş + kütükler + kesik kütükler + kayalar (camp() ile aynı düzen)
    rr = random.Random(7); cx, cz = TV.SPOTS['camp']
    record('p_campfire', cx, cz, L.height(cx, cz), 0, 1.5)
    for k, (a, r_, ln) in enumerate(((0.3, 3.6, 3.4), (2.3, 3.8, 2.8), (4.0, 3.4, 3.0))):
        x, z = cx + math.cos(a) * r_, cz + math.sin(a) * r_; record('p_log_v6', x, z, L.height(x, z) - 0.06, a + math.pi / 2, ln / 3.0)
    for k, a in enumerate((1.2, 3.2, 5.2, 5.9)):
        x, z = cx + math.cos(a) * 4.6, cz + math.sin(a) * 4.6; record('p_stump_v6', x, z, L.height(x, z) - 0.05, rr.uniform(0, 6.3), (0.42, 0.32, 0.5, 0.36)[k] / 0.42)
    for k, a in enumerate((0.8, 1.8, 2.9, 4.6, 5.5)):
        x, z = cx + math.cos(a) * rr.uniform(5.6, 6.8), cz + math.sin(a) * rr.uniform(5.6, 6.8); s = rr.uniform(1.0, 1.9)
        record('r_boulder', x, z, L.height(x, z) - s * 0.25, rr.uniform(0, 6.3), s)
    # kıyı yaşamı (beach_life ile aynı yerler): oyuk kütük, deniz yıldızı, kaçan yengeç, havuz, açık ada
    sx_, sz_ = [r['pos'] for r in L.lay['regions'] if r['id'] == 'region_swim_cove'][0]
    record('p_pool', sx_, sz_, 0.05, 0.4, 1.35)
    for (x, z, yaw, ln) in IV.DRIFT: record('p_driftwood', x, z, L.height(x, z) - 0.42, math.radians(yaw), ln / 5.8)
    r2 = random.Random(11)
    for (x, z) in IV.STARS: record('p_starfish', x, z, L.height(x, z) + 0.005, r2.uniform(0, 6.3), r2.uniform(0.9, 1.3))
    for (x, z, yaw) in IV.CRABS: record('p_crab', x, z, L.height(x, z) + 0.06, math.radians(yaw), 1.0)
    ix, iz, ir = TV.ISLET
    for k in range(9):
        a = r2.uniform(0, math.tau); rad = ir * 0.55 * math.sqrt(r2.random()); x, z = ix + math.cos(a) * rad, iz + math.sin(a) * rad * 0.8
        if L.height(x, z) <= 0.6: continue
        if k % 2: env('palm', x, z, L.height(x, z) - 0.1, r2.uniform(4.0, 5.8), r2.uniform(0, 360))
        else: record('t_palm_tall%d' % (k % 3), x, z, L.height(x, z) - 0.15, r2.uniform(0, 6.3), r2.uniform(0.55, 1.0))
    for k in range(6):
        a = r2.uniform(0, math.tau); x, z = ix + math.cos(a) * ir * 0.95, iz + math.sin(a) * ir * 0.75
        s_ = r2.uniform(0.6, 1.6); record('r_boulder', x, z, L.height(x, z) - s_ * 0.3, r2.uniform(0, 6.3), s_)
    # tapınak (tek model) + avlusundaki ağaçlar
    tx, tz = TV.SPOTS['temple']; record('b_temple', tx, tz, L.height(tx, tz), 0.0, 1.0)
    # karlı patika: işaret direkleri (her ~3,5 m, iki yanda) + kar topakları setlerde
    pts = TV.SNOW_PATH; Rn = random.Random(17)
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        Ln = math.hypot(bx - ax, bz - az); dx, dz = (bx - ax) / Ln, (bz - az) / Ln; sx, sz = -dz, dx
        for i in range(max(1, int(Ln / 3.5))):
            for sg in (-1, 1):
                px = ax + dx * Ln * (i + 0.5) / max(1, int(Ln / 3.5)) + sx * sg * 2.25; pz = az + dz * Ln * (i + 0.5) / max(1, int(Ln / 3.5)) + sz * sg * 2.25
                if math.hypot(px + 38.0, pz - 40.0) < 6.5: continue       # kayak alanı yapısının içinde direk olmaz
                record('p_trail_pole', px, pz, L.height(px, pz) - 0.2, 0.0, 1.0)
        for i in range(int(Ln / 0.9)):
            for sg in (-1, 1):
                if Rn.random() < 0.4: continue
                off = Rn.uniform(1.6, 2.6); px = ax + dx * (i * 0.9 + Rn.uniform(0, 0.6)) + sx * sg * off; pz = az + dz * (i * 0.9) + sz * sg * off
                s_ = Rn.uniform(0.18, 0.5)
                if math.hypot(px + 38.0, pz - 40.0) < 6.5: continue
                record('p_snow_lump', px, pz, L.height(px, pz) - s_ * 0.3, Rn.uniform(0, 6.3), s_)

# ------------------------------------------------------------------ zemin dokusu: taslağın zemin malzemesi üstten pişirilir

def bake_ground(L, cols, rw, size):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    IV.terrain_mesh(L, cols, rw)
    objs = [o for o in sc.objects if o.type == 'MESH' and o.name.startswith('terrain')]
    W, H = size, int(round(size * (TV.Z1 - TV.Z0) / (TV.X1 - TV.X0)))
    for o in objs:
        for md in list(o.modifiers): o.modifiers.remove(md)
        me = o.data; uv = me.uv_layers.new(name='top')
        co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        vi = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
        u = (co[vi, 0] - TV.X0) / (TV.X1 - TV.X0); v = (co[vi, 1] - TV.Z0) / (TV.Z1 - TV.Z0)
        uv.data.foreach_set('uv', np.stack([u, v], -1).ravel())
        me.uv_layers.active = uv
    def bake(kind):
        img = bpy.data.images.new(kind, W, H, alpha=False, float_buffer=True)
        for o in objs:
            for m in o.data.materials:
                n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; n.name = 'bake_target'; m.node_tree.nodes.active = n
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if kind == 'col':
            sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.use_pass_color = True
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=4, use_clear=True)
        else:
            sc.world.light_settings.distance = 2.5
            bpy.ops.object.bake(type='AO', margin=4, use_clear=True)
        for o in objs:
            for m in o.data.materials:
                if 'bake_target' in m.node_tree.nodes: m.node_tree.nodes.remove(m.node_tree.nodes['bake_target'])
        return np.array(img.pixels[:], np.float32).reshape(H, W, 4)
    col = bake('col'); IV.log('renk pişti'); ao = bake('ao'); IV.log('AO pişti')
    a = 1.0 - 0.45 * (1.0 - ao[..., :1])                     # yumuşak oyuk gölgesi (tabaka araları, yar dipleri)
    lin = np.clip(col[..., :3] * a, 0, 1)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    # alfa: kum ağırlığı (oyun gölgelendiricisi: rüzgâr çizgisi + ıslak kum)
    sand = np.clip(L.d['sand'] * (1 - rw * 0.8) * (1 - L.d['path']), 0, 1)
    from PIL import Image
    sA = Image.fromarray((sand * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    rgba = np.concatenate([(srgb * 255).astype(np.uint8), np.array(sA)[..., None]], -1)[::-1]   # Blender alt satırdan başlar
    out = os.path.join(ENV, 'ground_v6'); os.makedirs(out, exist_ok=True)
    Image.fromarray(rgba, 'RGBA').save(os.path.join(out, 'ground_v6.png'), optimize=True)
    for o in objs: bpy.data.objects.remove(o)

def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    npz = args[0]; size = int(args[1]) if len(args) > 1 else 2048
    bpy.ops.wm.read_factory_settings(use_empty=True)
    L = IV.Land(npz); B = IV.biome_fields(L)
    cols, rw = IV.terrain_colors(L, B); IV.log('boya')
    write_field(L, rw)
    place_props(L, B)
    lay = TV.layout_json()
    lay['props'] = PROPS
    lay['islet'] = list(TV.ISLET); lay['snow_path'] = [list(p) for p in TV.SNOW_PATH]
    json.dump(lay, open(os.path.join(DATA, 'island_v6_layout.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    from collections import Counter
    IV.log('süsler', len(PROPS), dict(Counter(p['a'] for p in PROPS)))
    if os.environ.get('NO_TEX') != '1': bake_ground(L, cols, rw, size); IV.log('doku')

if __name__ == '__main__':
    main()
