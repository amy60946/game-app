# Kulübe yükseltme taslağı v4 (kullanıcı isteği 20 Ekim 2026): inşa edilen kulübe, toplama + inşa adımlarıyla 3 seviyeye çıkar;
# her seviyede biraz uzar ve yeni ayrıntılar eklenir. Sv1 = bugünkü kulübe (assets_town.c_hut ile aynı plan), Sv2: daha uzun duvar,
# çatı katı penceresi, verandalı sundurma, fener, çiçek kutusu; Sv3: taş temel, daha uzun duvar, taş baca + duman, balkon, bayrak.
# Malzemeler assets_town/assets_v3 ile aynı (damarlı aşınmış ahşap, kesik kütük halkaları, halat, taş). Dış çizgi yok.
# Kullanım: /tmp/claude-0/bpyenv/bin/python -I hut_v4.py -- <çıktı_klasörü> [taslak|fbx]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import bpy
import assets_town as T
from assets_town import *
from kit import *
import kit
from mathutils import Vector as V

def _logs(Wd, Dp, n, r, z0, BK, door_rows):
    """Yatay kütük duvarlar (köşelerde taşan uçlar); ön duvarda kapı açıklığı (ilk door_rows sıra)."""
    for k in range(n):
        z = z0 + r + k * 2 * r
        for (axis, off) in (('x', -Dp / 2), ('x', Dp / 2), ('y', -Wd / 2), ('y', Wd / 2)):
            if axis == 'x' and off < 0 and k < door_rows:
                for (a0, a1) in ((-Wd / 2 - 0.15, -0.3), (0.3, Wd / 2 + 0.15)):
                    tube('log', [(a0, off, z), (a1, off, z)], [r * 0.98, r * 0.98], BK, res=2)
                continue
            if axis == 'x': tube('log', [(-Wd / 2 - 0.15, off, z), (Wd / 2 + 0.15, off, z)], [r * 0.98, r], BK, res=2)
            else: tube('log', [(off, -Dp / 2 - 0.15, z + r), (off, Dp / 2 + 0.15, z + r)], [r * 0.98, r], BK, res=2)

def hut(level):
    """level 1–3. Dönüş: yükseklik (çatı tepesi)."""
    R = random.Random(100 + level)
    BK = m_treebark('hutlog'); EG = m_endgrain('hutend')
    STN = m_rock(name='hutstone')
    Wd, Dp = 1.8, 1.5
    n = (7, 9, 11)[level - 1]; r = 1.15 / 7 / 2
    z0 = 0.0
    if level >= 3:
        # taş temel: kulübenin altında bir sıra yuvarlak taş (kütükler 0,18 yükselir)
        z0 = 0.18
        for side in range(4):
            L = Wd if side < 2 else Dp
            m_ = int(L / 0.2) + 2
            for i in range(m_):
                t = -L / 2 - 0.1 + i * (L + 0.2) / (m_ - 1)
                x, y = ((t, -Dp / 2) if side == 0 else (t, Dp / 2) if side == 1 else (-Wd / 2, t) if side == 2 else (Wd / 2, t))
                pebble((x, y, 0.09), R.uniform(0.1, 0.13), STN, level * 50 + side * 9 + i)
    H = z0 + n * 2 * r
    _logs(Wd, Dp, n, r, z0, BK, door_rows=5 + (level - 1))
    for (x, y) in ((-Wd / 2 - 0.15, -Dp / 2), (Wd / 2 + 0.15, -Dp / 2), (-Wd / 2 - 0.15, Dp / 2), (Wd / 2 + 0.15, Dp / 2)):
        for k in range(n):
            cyl('end', (x + (0.005 if x > 0 else -0.005), y, z0 + r + k * 2 * r), r * 0.9, 0.012, EG, rot=(0, 90, 0), verts=10)
    cyl('inner', (0, 0, H / 2), 0.1, 0.1, T.A.m_flat('#3a2818', 0.1, 6, 'hutin'), verts=6).scale = (Wd * 4.6, Dp * 4.6, H * 9.5)
    # kapı (seviye 2+: daha yüksek, üstünde kemer tahtası)
    DR = m_wood('#b98a5a', 'hutdoor', paint=('#2fa3a0', '#3b7fd1', '#c4553c')[level - 1], age=1.1)
    dh = 0.86 + 0.14 * (level - 1)
    for k in range(3): plank('door', (-0.17 + k * 0.17, -Dp / 2 - 0.02, z0 + dh / 2 + 0.02), (0.16, 0.05, dh), DR, seed=k)
    plank('brace', (0, -Dp / 2 - 0.055, z0 + dh * 0.28), (0.5, 0.025, 0.07), DR, seed=5)
    plank('brace', (0, -Dp / 2 - 0.055, z0 + dh * 0.78), (0.5, 0.025, 0.07), DR, seed=6)
    blob('knob', (0.15, -Dp / 2 - 0.08, z0 + dh * 0.55), (0.025, 0.02, 0.025), m_metal(name='knobm'), sub=0, seg=8)
    # yan pencere (+ panjur); seviye 3: iki pencere
    WIN = T.A.m_flat('#2f4a6a', 0.15, 6, 'darkglass'); SH = m_wood('#b98a5a', 'hutshut', paint='#e86f50', age=1.1)
    wins = [0.0] if level < 3 else [-0.36, 0.36]
    for wy in wins:
        rbox('win', (Wd / 2 + 0.11, wy, z0 + 0.7), (0.03, 0.3, 0.3), WIN, bevel=0.01)
        rbox('mull', (Wd / 2 + 0.13, wy, z0 + 0.7), (0.02, 0.025, 0.3), DR, bevel=0.005)
        for s_ in (-1, 1): plank('shutter', (Wd / 2 + 0.14, wy + s_ * 0.24, z0 + 0.7), (0.03, 0.15, 0.34), SH, seed=s_ + 10)
        if level >= 2:   # çiçek kutusu
            plank('fbox', (Wd / 2 + 0.2, wy, z0 + 0.5), (0.12, 0.34, 0.1), m_wood('#a8784c', 'fbox', paint='#f2c84b', age=1.2), seed=21)
            flower_heads([(Wd / 2 + 0.2, wy + d, z0 + 0.62 + R.uniform(0, 0.05)) for d in (-0.12, -0.04, 0.05, 0.13)], R, size=0.8)
    roof_lift = 0.9 + 0.12 * (level - 1)
    thatch(0, 0, H + 0.1, H + roof_lift, 1.25 + 0.05 * (level - 1), 0.16, 103 + level, layers=7)
    blob('knot', (0, 0, H + roof_lift + 0.05), (0.1, 0.1, 0.08), m_leaf('#b98a3e', '#d4a855', '#e8c674', '#f0d58e', 'straw'), sub=1, seg=12)
    top = H + roof_lift + 0.1
    if level >= 2:
        # çatı katı penceresi (ön): üçgen tahta alın + yuvarlak cam
        GW = m_wood('#c99a64', 'gable', age=1.2)
        for k in range(4):
            w = 0.7 - k * 0.15
            plank('gable', (0, -Dp / 2 - 0.06, H + 0.12 + k * 0.11), (w, 0.04, 0.1), GW, seed=30 + k)
        cyl('loft', (0, -Dp / 2 - 0.09, H + 0.28), 0.1, 0.02, WIN, rot=(90, 0, 0), verts=16)
        cyl('loftr', (0, -Dp / 2 - 0.08, H + 0.28), 0.12, 0.015, DR, rot=(90, 0, 0), verts=16)
        # sundurma: ön veranda tahtaları + 2 direk + tahta saçak + asılı fener
        DK = m_wood('#b0835a', 'deck', age=1.3)
        for k in range(6):
            plank('deck', (-0.75 + k * 0.3, -Dp / 2 - 0.4, z0 + 0.04), (0.28, 0.7, 0.05), DK, seed=40 + k)
        ph = z0 + dh + 0.25
        for x in (-0.82, 0.82):
            tube('post', [(x, -Dp / 2 - 0.72, z0), (x + R.uniform(-0.02, 0.02), -Dp / 2 - 0.72, ph)], [0.05, 0.045], BK, res=2)
        for k in range(5):
            plank('awn', (-0.8 + k * 0.4, -Dp / 2 - 0.42, ph + 0.06 - 0.0), (0.38, 0.78, 0.04), DK, rot=(-14, 0, 0), seed=50 + k)
        tube('hook', [(0.55, -Dp / 2 - 0.62, ph), (0.55, -Dp / 2 - 0.62, ph - 0.12)], [0.008, 0.008], m_metal(name='hookm'), res=2)
        rbox('lamp', (0.55, -Dp / 2 - 0.62, ph - 0.22), (0.1, 0.1, 0.14), m_glow(), bevel=0.02)
        rbox('lampcap', (0.55, -Dp / 2 - 0.62, ph - 0.13), (0.13, 0.13, 0.03), m_metal(name='lampm'), bevel=0.01)
    if level >= 3:
        # taş baca (sol arka) + duman bulutu
        # dış duvara yaslanan taş baca: yerden çatının üstüne kesintisiz taş sütun (iki taş yan yana)
        cx, cy = -Wd / 2 - 0.32, Dp / 2 - 0.35
        nst = int((H + 1.35) / 0.15)
        for k in range(nst):
            for j, dy in enumerate((-0.11, 0.11)):
                pebble((cx + R.uniform(-0.02, 0.02), cy + dy, 0.1 + k * 0.15), R.uniform(0.1, 0.13), STN, 300 + k * 2 + j)
        ctop = 0.1 + nst * 0.15
        for k in range(3):
            blob('smoke', (cx + 0.05 + k * 0.1, cy, ctop + 0.2 + k * 0.3), (0.13 + k * 0.05,) * 3, mat('smoke', '#f2f4f7', rough=0.9, coat=0), sub=2, seg=12)
        top = max(top, ctop + 1.0)
        # balkon (ön, çatı katı penceresinin altında): tahta zemin + halat korkuluk
        BL = m_wood('#b0835a', 'balc', age=1.3)
        plank('balc', (0, -Dp / 2 - 0.3, H - 0.05), (1.0, 0.5, 0.05), BL, seed=70)
        for x in (-0.48, -0.16, 0.16, 0.48):
            tube('bpost', [(x, -Dp / 2 - 0.52, H - 0.05), (x, -Dp / 2 - 0.52, H + 0.28)], [0.025, 0.022], BK, res=2)
        tube('brail', [(-0.5, -Dp / 2 - 0.52, H + 0.27), (0.5, -Dp / 2 - 0.52, H + 0.27)], [0.018, 0.018], T.m_rope(), res=2)
        tube('brail2', [(-0.5, -Dp / 2 - 0.52, H + 0.12), (0.5, -Dp / 2 - 0.52, H + 0.12)], [0.014, 0.014], T.m_rope(), res=2)
        # bayrak direği (çatı tepesi) + üçgen bayrak
        tube('pole', [(0, 0, top - 2.5), (0, 0, H + roof_lift + 0.75)], [0.02, 0.016], m_wood('#c48a57', 'pole'), res=2)
        blob('flag', (0.18, 0, H + roof_lift + 0.62), (0.18, 0.012, 0.1), T.m_cloth('#e85d4a', '#ffd447', 3.0, 'flag'), sub=1, seg=8)
    # odun yığını (her seviyede), seviye 2+: yanına el arabası yerine fıçı
    for k in range(6):
        row = 0 if k < 3 else 1
        x = 0.55 + (k % 3) * 0.17 + row * 0.08
        lg = lathe('wood', [(0.001, -0.25), (0.075, -0.25), (0.075, 0.25), (0.001, 0.25)], BK, segs=10)
        lg.rotation_euler = (math.radians(90), 0, 0); lg.location = (x + (0.5 if level >= 2 else 0), -Dp / 2 - 0.45 + (0.3 if level >= 2 else 0), 0.075 + row * 0.14)
    if level >= 2:
        lathe('barrel', [(0.001, 0), (0.16, 0), (0.19, 0.2), (0.16, 0.4), (0.001, 0.4)], m_wood('#9c6b42', 'barrel', age=1.3), segs=16).location = (-1.15, -Dp / 2 - 0.3, 0)
    for (x, y) in ((-Wd / 2, -Dp / 2), (Wd / 2, -Dp / 2), (-Wd / 2, Dp / 2), (Wd / 2, Dp / 2)):
        base_ring(x * 1.1, y * 1.2, 0.15, int(x * 7 + y * 5) + 110 + level, flowers=1 + level // 2)
    lush((0, 0, 0), 1.6 + 0.2 * level, 6 + 2 * level, 111 + level)
    return top

def build_at(level, ox):
    before = set(bpy.context.scene.objects)
    top = hut(level)
    for o in set(bpy.context.scene.objects) - before:
        if o.parent is None: o.location.x += ox
    return top

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    OUT = args[0]; os.makedirs(OUT, exist_ok=True)
    mode = args[1] if len(args) > 1 else 'taslak'
    def finish():
        to_mesh_all()
        for o in bpy.context.scene.objects:
            if o.type == 'MESH' and 'grain' not in o.data.uv_layers: grain_uv(o)
    if mode == 'fbx':
        for lv in (1, 2, 3):
            reset(); hut(lv); finish()
            objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
            print('b_hut%d' % lv, 'üçgen', export_baked_fbx(f'{OUT}/b_hut_lv{lv}', objs, size=1024), flush=True)
        sys.exit(0)
    only = [int(x) for x in os.environ.get('HUT_LV', '1,2,3').split(',') if x]
    # tek tek
    for lv in only:
        sc = reset(); sc.cycles.samples = 48
        g = ground(4.5, '#7fbf5a'); top = hut(lv); finish()
        objs = [o for o in sc.objects if o.type == 'MESH' and o.name != 'ground']
        print('seviye', lv, 'üçgen', tri_count(objs), 'yükseklik', round(top, 2), flush=True)
        shoot(sc, f'{OUT}/hut_lv{lv}.png', (0, -0.3, 1.25 + 0.35 * (lv - 1)), 7.2 + 1.1 * (lv - 1), 30, 22, lens=50, size=(900, 900))
    # yan yana
    sc = reset(); sc.cycles.samples = 48
    ground(9, '#7fbf5a')
    for lv, ox in ((1, -3.6), (2, 0.0), (3, 3.6)): build_at(lv, ox)
    finish()
    shoot(sc, f'{OUT}/hut_levels.png', (0.3, -0.4, 1.9), 16.5, 16, 15, lens=50, size=(1800, 900))
    print('ok')
