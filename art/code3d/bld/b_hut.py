# Kulübe (çocuğun 6 odun, 4 dal, 3 taşla kurduğu) — oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına
# uygun eskitmeli olsun"). Oyunda GatherSpot "Kulübe yap" bitince EnvFootprint("b_hut", …, 4.2) ile konur: dış ölçüler, orijin ve
# ön yön (−Y = kapı) eski assets_town.c_hut ile aynı tutuldu.
# Elle yapılmış, halatla bağlanmış bir çocuk kulübesi:
#   - kütük duvar: her kütük biraz farklı kalın ve eğri, kabuklu (yer yer soyulmuş açık tahta), aralarında çamur + yosun dolgusu,
#     köşelerde taşan uçlar halkalı kesik yüzlü;
#   - "4 dal": köşelerde çatıyı taşıyan dört dal direk, kütük uçlarına halatla bağlı; kapı çerçevesi de dal, lento bağlı;
#   - "3 taş": kapı önünde yassı eşik taşı + ön köşelerde iki iri taş (liken, yosun);
#   - saz çatı: dört kat taranmış saz (kat başına halat kuşak, düzensiz saçak ucu, tel tel oluk → normal haritası), kuzeyde yosun,
#     bir yanda sonradan serilmiş kuru palmiye yaprağı yaması, tepede halatla sarılmış topuz + küçük üçgen bayrak;
#   - kapı: turkuaz boyalı tahtalar (dökülmüş), halat menteşe, kıvrık dal tutamak, çocuk eliyle boyanmış güneş;
#   - yan pencere: dal haç + turuncu panjur; önde odun yığını, baltası saplı kesme kütüğü; dipte kum, çakıl, ot, çiçek.
# Kullanım: python -I bld/b_hut.py -- <çıktı> [b_hut] [--draft <png>] [--stats]
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import koy_eskitme as KE
from koy_eskitme import AT, A, V, MN, bpy, bmesh, rbox, blob, cyl, tube, m_flat, m_leaf

NAME = 'b_hut'
CAP = 12000
Wd, Dp, H = 1.8, 1.5, 1.15
NC = 7; RL = H / NC / 2
TIERS = ((1.62, 1.2, 0.86, 1.29), (1.82, 1.47, 0.58, 0.99), (1.97, 1.69, 0.3, 0.69), (2.05, 1.87, 0.05, 0.39))   # (z üst, z alt, r üst, r alt)


def roof_z(r):
    """Saz çatının r yarıçapındaki dış yüzey yüksekliği (o noktayı örten en yüksek kat; demet sırtı payı dahil)."""
    best = None
    for (zt, zb, rt, rb) in TIERS:
        if rt <= r <= rb:
            t = (r - rt) / (rb - rt); z = zt + (zb - zt) * t + 0.02 * (0.3 + 0.7 * t)
            best = z if best is None else max(best, z)
    return best if best is not None else TIERS[0][1]


def m_log(name='hutlog'):
    """Kütük kabuğu + aralarda çamur/yosun dolgusu (yatay kütüğün üst/alt eğik yüzü: |normal z| 0,5–0,9), yer yer soyulmuş açık tahta."""
    def b(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        groove = G.vor(G.mapping(o, (2.0, 2.0, 11)), 2.2, 'DISTANCE_TO_EDGE')      # kütükler yatay: oluk yatay uzar
        col = G.mix(G.rng(G.noise(o, 3, 4), 0.3, 0.7), '#6a4a2e', '#8f6842')
        col = G.mix(G.rng(groove, 0.07, 0.0, 0, 0.7), col, '#33200f')
        peel = G.math('MULTIPLY', G.rng(G.noise(o, 2.2, 4), 0.66, 0.69), G.rng(G.noise(o, 0.7, 2), 0.45, 0.55))
        col = G.mix(peel, col, G.mix(G.rng(G.noise(G.mapping(o, (2, 2, 30)), 3, 3), 0.3, 0.7), '#c39a68', '#ddb886'))
        col = G.mix(G.rng(G.noise(o, 1.5, 4), 0.58, 0.72, 0, 0.3), col, '#a49e8e')       # güneşte grileşme
        nz = G.math('ABSOLUTE', G.nz())
        chink = G.rng(G.math('ADD', nz, G.math('MULTIPLY', G.noise(o, 6, 3), 0.25)), 0.62, 0.8)
        mud = G.mix(G.rng(G.noise(o, 5, 4), 0.45, 0.6), '#6d5338', '#55673a')
        col = G.mix(chink, col, mud)
        col = KE._surface(G, col, 1.0, 0.0, 0.5, 0.32, 0.8)
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat(name, b)


def m_straw(name='straw2', fresh=False):
    """Taranmış saz: eğim boyunca ince lif çizgileri (açıya bağlı çizgi deseni), demet demet ton farkı; eski katlar grileşmiş,
    altta kesik saz uçları (açık altın, koyu benekli), oyukta kir + kuzeyde (arka) yosun. fresh: tepe topuzu (daha altın)."""
    def b(nt, bsdf):
        G = KE.G2(nt); p = G.pos()
        sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(p, sp.inputs[0])
        ang = G.math('ARCTAN2', sp.outputs['Y'], sp.outputs['X'])
        warp = G.math('MULTIPLY', G.noise(p, 3.0, 3), 0.35)
        lines = G.math('SINE', G.math('MULTIPLY', G.math('ADD', ang, G.math('MULTIPLY', warp, 0.08)), 210.0))
        bund = G.math('SINE', G.math('MULTIPLY', G.math('ADD', ang, G.math('MULTIPLY', warp, 0.3)), 20.0))
        base = ('#c99a4c', '#e6c071') if fresh else ('#b08447', '#d8b062')
        col = G.mix(G.rng(bund, -0.6, 0.9), base[0], base[1])
        col = G.mix(G.rng(lines, 0.2, 0.9, 0, 0.45), col, '#7e5a2c')                         # lif çizgileri
        col = G.mix(G.rng(G.noise(p, 2.0, 3), 0.4, 0.7, 0, 0.35), col, '#8f6a38')
        if not fresh:
            col = G.mix(G.rng(G.noise(p, 1.2, 4), 0.5, 0.7, 0, 0.38), col, '#a39a84')          # güneşte grileşmiş saz
        under = G.rng(G.nz(), -0.15, -0.5)                                                       # kesik uçlar (alt yüz)
        ends = G.mix(G.rng(G.vor(p, 55), 0.0, 0.25, 0.75, 0), '#e8c87e', '#5c4220')
        col = G.mix(under, col, ends)
        occl = G.ao(0.14)
        col = G.mix(G.rng(occl, 0.85, 0.4, 0, 0.6), col, '#4a3820')
        mm = G.math('MULTIPLY', G.rng(occl, 0.82, 0.45, 0, 0.8), G.rng(G.noise(p, 3.0, 4), 0.42, 0.58))
        mm = G.math('MULTIPLY', mm, G.rng(G.wy(), -0.4, 0.6))                                   # kuzey (arka) yüzde yosun
        col = G.mix(mm, col, '#5b7f2e')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat(name, b)


def thatch_tier(z_top, z_bot, r_top, r_bot, seed, M, segs=160, lip=0.085, name='thatch'):
    """Saz katı: düz koni, 40 demet sırtı (yuvarlak kabartı) + ince lif olukları (normal haritası), demet boyları biraz farklı (çocuk işi),
    alt ucu küt kesik ve kalın (dudak: aşağı-içe, sonra içte yukarı; kesik uçlar alt yüzde)."""
    R = random.Random(seed); verts = []; faces = []
    NB = 40; blen = [R.uniform(-1, 1) for _ in range(NB)]
    rows_out = 5
    rings = []
    for i in range(rows_out + 1):
        t = i / rows_out; ring = []
        for j in range(segs):
            a = j / segs * 2 * math.pi
            ph = a / (2 * math.pi) * NB; bi = int(ph) % NB; f = ph - int(ph)
            ridge = 0.028 * math.sin(math.pi * f) ** 0.8 + 0.006 * math.sin(a * segs / 2.0)
            rr = r_top + (r_bot - r_top) * t + ridge * (0.3 + 0.7 * t)
            z = z_top + (z_bot - z_top) * t
            if i == rows_out:
                z += 0.028 * blen[bi] - 0.012 * math.sin(math.pi * f)
            ring.append(len(verts)); verts.append((math.cos(a) * rr, math.sin(a) * rr, z))
        rings.append(ring)
    for (dr, dz) in ((-lip * 0.35, -0.035), (-lip, 0.0), (-lip * 1.2, (z_top - z_bot) * 0.6)):
        ring = []
        for j in range(segs):
            x, y, z = verts[rings[rows_out][j]]; a = j / segs * 2 * math.pi
            ring.append(len(verts)); verts.append((x + math.cos(a) * dr, y + math.sin(a) * dr, z + dz))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            faces.append((rings[i][j], rings[i + 1][j], rings[i + 1][j2], rings[i][j2]))
    return KE._mesh(name, verts, faces, M)


def frond(a, r0, r1, M, RIB, seed):
    """Kuru palmiye yaprağı (çatı yaması): a açısında r0'dan r1'e çatı yüzeyini izleyen orta damar + iki yanda yatık yaprakçıklar."""
    R = random.Random(seed)
    d = V((math.cos(a), math.sin(a), 0)); sidev = V((-math.sin(a), math.cos(a), 0))
    def C(s):
        r = r0 + (r1 - r0) * s; return V((d.x * r, d.y * r, roof_z(r) + 0.035))
    pts = [tuple(C(s)) for s in (0, 0.25, 0.5, 0.75, 1.0)]
    tube('frib', pts, [0.014, 0.013, 0.011, 0.008, 0.004], RIB, res=3)
    def build(bm):
        out = []
        for k in range(18):
            s = 0.06 + 0.9 * k / 18; c = C(s); tan = (C(min(1, s + 0.03)) - C(max(0, s - 0.03))).normalized()
            for sgn in (-1, 1):
                dd = (tan * 0.6 + sidev * sgn * 0.8).normalized()
                L = (r1 - r0) * 0.32 * (1 - 0.45 * s) + R.uniform(-0.02, 0.02)
                for f in A.blade(bm, c + V((0, 0, 0.008)), dd, sidev.cross(dd).normalized() * sgn, L, 0.032, 0.25, segs=2):
                    out.append((f, 0))
        return out
    A.mesh_from_blades('frond', build, [M])


def build():
    R = random.Random(101)
    LOG = m_log(); EG = KE.m_endgrain2('hutend'); BARK = KE.m_bark2('hutpole', '#6e4c30')
    # kütük duvarlar (eski yerleşim: ön duvarda kapı açıklığı), her kütük farklı kalın + hafif eğri
    def log(p0, p1, r, seed):
        p0 = V(p0); p1 = V(p1); m = (p0 + p1) / 2
        ax = (p1 - p0).normalized(); side = ax.cross(V((0, 0, 1))).normalized()
        bow = side * (0.012 * MN.noise(V((seed * 1.3, 0.5, 0.2)))) + V((0, 0, 0.006 * MN.noise(V((0.3, seed, 1)))))
        tube('log', [tuple(p0), tuple(m + bow), tuple(p1)], [r * 0.97, r * 1.02, r * 0.95], LOG, res=3)
    k_id = 0
    for k in range(NC):
        z = RL + k * 2 * RL
        for (axis, off) in (('x', -Dp / 2), ('x', Dp / 2), ('y', -Wd / 2), ('y', Wd / 2)):
            rr = RL * R.uniform(0.92, 1.04); k_id += 1
            if axis == 'x' and off < 0 and k <= 4:
                for (a0, a1) in ((-Wd / 2 - 0.15, -0.34), (0.34, Wd / 2 + 0.15)):
                    log((a0, off, z), (a1, off, z), rr, k_id); k_id += 1
                continue
            if axis == 'x': log((-Wd / 2 - 0.15, off, z), (Wd / 2 + 0.15, off, z), rr, k_id)
            else: log((off, -Dp / 2 - 0.15, z + RL), (off, Dp / 2 + 0.15, z + RL), rr, k_id)
    # köşelerde kesik uçlar (halkalı)
    for (x, y) in ((-Wd / 2 - 0.15, -Dp / 2), (Wd / 2 + 0.15, -Dp / 2), (-Wd / 2 - 0.15, Dp / 2), (Wd / 2 + 0.15, Dp / 2)):
        for k in range(NC):
            cyl('end', (x + (0.006 if x > 0 else -0.006), y, RL + k * 2 * RL), RL * 0.86, 0.014, EG, rot=(0, 90, 0), verts=12, bevel=0.004)
    for (x, y) in ((-Wd / 2, -Dp / 2 - 0.15), (Wd / 2, -Dp / 2 - 0.15), (-Wd / 2, Dp / 2 + 0.15), (Wd / 2, Dp / 2 + 0.15)):
        for k in range(NC):
            cyl('end', (x, y + (0.006 if y > 0 else -0.006), 2 * RL + k * 2 * RL), RL * 0.86, 0.014, EG, rot=(90, 0, 0), verts=12, bevel=0.004)
    INNER = m_flat('#2e2116', 0.1, 6, 'hutin')
    rbox('inner', (0, 0, H / 2 + 0.04), (Wd - 0.12, Dp - 0.12, H + 0.06), INNER, bevel=0)
    # 4 dal: köşe direkleri (çatı saçağını taşır), kütük uçlarına halatla bağlı
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        bx, by = sx * (Wd / 2 + 0.1), sy * (Dp / 2 + 0.1)
        AT.post('pole', (bx, by, -0.04), (bx * 1.02, by * 1.02, 1.32), 0.045, BARK, taper=0.8, seed=i + 3)
        for (z0, z1) in ((0.3, 0.38), (0.86, 0.94)):
            KE.lash((bx, by, 0), 0.054, z0, z1, 1.6, thick=0.012, seed=i * 2 + int(z0 * 10))
    # kapı çerçevesi: iki dal + bağlı lento
    for sx in (-1, 1):
        AT.post('dpost', (sx * 0.31, -Dp / 2 - 0.05, -0.02), (sx * 0.3, -Dp / 2 - 0.05, 0.98), 0.035, BARK, taper=0.85, seed=sx + 20)
    AT.post('dpost', (-0.42, -Dp / 2 - 0.07, 0.93), (0.42, -Dp / 2 - 0.07, 0.95), 0.035, BARK, taper=0.9, seed=23)
    for sx in (-1, 1):
        KE.lash((sx * 0.3, -Dp / 2 - 0.06, 0.94), 0.046, -0.035, 0.035, 1.6, thick=0.011, axis='x', seed=sx + 30, tail=False)
    # kapı: turkuaz tahtalar (dökülmüş), destekler, halat menteşe, dal tutamak, çocuk eliyle boyanmış güneş
    DR = KE.m_wood2('#b38655', 'hutdoor', paint='#2b9e9a', age=1.2, salt=0.4, ground=0.3, chips=1.2)
    for k in range(3): AT.plank('door', (-0.17 + k * 0.17, -Dp / 2 - 0.02, 0.45), (0.16, 0.05, 0.86), DR, seed=k)
    for zz, sd in ((0.22, 5), (0.7, 6)): AT.plank('brace', (0, -Dp / 2 - 0.055, zz), (0.5, 0.025, 0.07), DR, seed=sd)
    for zz in (0.22, 0.7):
        KE.lash((-0.27, -Dp / 2 - 0.04, zz), 0.036, -0.03, 0.03, 1.6, thick=0.01, axis='x', seed=int(zz * 100), tail=False)
    DRIFT = KE.m_wood2('#b7ab95', 'driftwood', ground=0.0, silver=0.5)
    tube('handle', [(0.16, -Dp / 2 - 0.06, 0.38), (0.19, -Dp / 2 - 0.12, 0.46), (0.165, -Dp / 2 - 0.06, 0.55)], [0.016, 0.019, 0.015], DRIFT, res=4)
    SUN = KE._cached('kidsun', lambda: _kid_paint('#f5b52e', 'kidsun'))
    cyl('sun', (0.0, -Dp / 2 - 0.047, 0.5), 0.07, 0.006, SUN, rot=(90, 0, 0), verts=16, bevel=0)
    for q in range(8):
        a = q * math.pi / 4 + 0.15 * math.sin(q * 3)
        rbox('sun', (math.cos(a) * 0.11, -Dp / 2 - 0.047, 0.5 + math.sin(a) * 0.11), (0.05 + 0.012 * (q % 2), 0.005, 0.016), SUN,
             rot=(0, -math.degrees(a), 0), bevel=0)
    # yan pencere: koyu cam, dal haç (bağlı), pervaz, turuncu panjur
    WIN = m_flat('#2a3f58', 0.15, 6, 'darkglass')
    SH = KE.m_wood2('#b38655', 'hutshut', paint='#e8743f', age=1.2, salt=0.4, ground=0.0)
    rbox('win', (Wd / 2 + 0.1, 0, 0.7), (0.03, 0.36, 0.32), WIN, bevel=0.01)
    AT.post('wstick', (Wd / 2 + 0.13, 0, 0.52), (Wd / 2 + 0.13, 0, 0.88), 0.016, BARK, taper=0.9, seed=31)
    AT.post('wstick', (Wd / 2 + 0.13, -0.2, 0.7), (Wd / 2 + 0.13, 0.2, 0.7), 0.016, BARK, taper=0.9, seed=32)
    KE.lash((Wd / 2 + 0.13, 0, 0.7), 0.025, -0.02, 0.02, 1.5, thick=0.008, axis='y', seed=33, tail=False)
    AT.plank('sill', (Wd / 2 + 0.15, 0, 0.51), (0.1, 0.5, 0.035), KE.m_wood2('#9a6a3c', 'sill', salt=0.8, ground=0.0), seed=34)
    for s_ in (-1, 1): AT.plank('shutter', (Wd / 2 + 0.14, s_ * 0.28, 0.7), (0.03, 0.17, 0.38), SH, rot=(0, 0, s_ * 8), seed=s_ + 10)
    # çatı: dört kat saz + halat kuşaklar + yosun + palmiye yaması + topuz ve bayrak
    ST = m_straw(); STF = m_straw('strawtop', fresh=True)
    for i, (zt, zb, rt, rb) in enumerate(TIERS):
        thatch_tier(zt, zb, rt, rb, 200 + i, ST if i < 3 else STF)
        if i < 3:
            zr = zt - 0.05; rr = rt + (rb - rt) * 0.12 + 0.03
            pts = [(math.cos(a) * rr, math.sin(a) * rr, zr) for a in [j / 48 * 2 * math.pi for j in range(48)]]
            KE.rope3(pts, 0.016, closed=True, seg=0.07, around=6)
    for k, (a, r, rr) in enumerate(((70, 1.1, 0.11), (118, 0.92, 0.09), (100, 0.62, 0.075), (-35, 1.15, 0.06), (160, 1.2, 0.07))):
        aa = math.radians(a); x, y = math.cos(aa) * r, math.sin(aa) * r
        KE.moss_clump((x, y, roof_z(r) - 0.01), rr, 5 + k, (math.cos(aa) * 0.65, math.sin(aa) * 0.65, 0.76))
    FR = m_leaf('#66702e', '#8a8f3c', '#b0a556', '#c9bb74', 'dryfrond'); RIB = m_flat('#a08750', 0.15, 6, 'fribm')
    frond(math.radians(-24), 0.36, 1.3, FR, RIB, 300); frond(math.radians(-6), 0.42, 1.28, FR, RIB, 301)
    tube('knot', [(0, 0, 1.98), (0, 0, 2.05), (0.01, 0, 2.1)], [0.12, 0.095, 0.045], STF, res=3)
    KE.lash((0, 0, 0), 0.105, 2.0, 2.05, 2.0, thick=0.014, seed=41, tail=False)
    tube('flagstick', [(0.01, 0, 2.02), (0.02, 0.005, 2.17)], [0.011, 0.009], KE.m_wood2('#9a7046', 'stick', ground=0.0), res=2)
    FL = KE._cached('flag', lambda: _kid_paint('#e84a3c', 'flag', stripe='#f6c43a'))
    AT.prism('flag', [(0.0, 0.0), (0.0, 0.075), (0.13, 0.04)], 0.008, FL, loc=(0.025, 0.005, 2.085), rot=(0, 0, -20), bevel=0.003)
    # 3 taş: eşik taşı + ön köşelerde iki iri taş
    STN = KE.m_stone2('hutstone')
    st = A.pebble((0.0, -1.0, 0.03), 0.3, STN, 51); st.scale = (1.15, 0.62, 0.32)
    A.pebble((-1.13, -0.62, 0.1), 0.17, STN, 52); A.pebble((1.14, -0.5, 0.09), 0.15, STN, 53)
    KE.moss_clump((-1.13, -0.56, 0.2), 0.06, 54, (0, 0.5, 0.86))
    # odun yığını (eski yer) + baltası saplı kesme kütüğü
    for k in range(6):
        row = 0 if k < 3 else 1
        x = 0.55 + (k % 3) * 0.17 + row * 0.08
        lg = AT.lathe('wood', [(0.001, -0.25), (0.075, -0.25), (0.075, 0.25), (0.001, 0.25)], LOG, segs=12)
        lg.rotation_euler = (math.radians(90), 0, math.radians(R.uniform(-4, 4))); lg.location = (x, -Dp / 2 - 0.45, 0.075 + row * 0.14)
        cyl('wend', (x, -Dp / 2 - 0.71, 0.075 + row * 0.14), 0.07, 0.012, EG, rot=(90, 0, 0), verts=12, bevel=0.003)
    sx, sy = -0.72, -1.12
    AT.lathe('stump', [(0.001, 0.0), (0.17, 0.0), (0.16, 0.12), (0.15, 0.28), (0.001, 0.28)], LOG, segs=14).location = (sx, sy, 0)
    cyl('stumptop', (sx, sy, 0.282), 0.148, 0.008, EG, verts=14, bevel=0.002)
    tube('axeh', [(sx + 0.02, sy + 0.01, 0.3), (sx + 0.14, sy - 0.03, 0.47), (sx + 0.22, sy - 0.05, 0.6)], [0.016, 0.016, 0.018], KE.m_wood2('#c48a57', 'axehandle', ground=0.0), res=3)
    rbox('axeb', (sx - 0.005, sy + 0.012, 0.3), (0.12, 0.022, 0.09), KE.IRON(), rot=(0, -35, -12), bevel=0.01)
    # dip: kum + toprak + eski yerleşimin ot/çiçek/çakılı (aynı tohumlar)
    AT.dirt_patch(0, -1.05, 0.62, 0.32, 112)
    KE.sand_drift(0.0, -0.92, 0.7, 0.22, 0.05, seed=5, lean=(0, 0.6))
    KE.sand_drift(-0.55, 0.85, 0.5, 0.16, 0.04, seed=6, lean=(0, -0.5))
    KE.shell((0.42, -1.05, 0.012), 0.05, yaw=30); KE.starfish((-0.38, -1.22, 0.01), 0.07, yaw=10, hexc='#e86a52')
    for (x, y) in ((-Wd / 2, -Dp / 2), (Wd / 2, -Dp / 2), (-Wd / 2, Dp / 2), (Wd / 2, Dp / 2)):
        AT.base_ring(x * 1.1, y * 1.2, 0.15, int(x * 7 + y * 5) + 110, flowers=1)
    AT.lush((0, 0, 0), 1.6, 6, 111)
    KE.moss_clump((0.4, Dp / 2 + 0.06, 0.06), 0.08, 60, (0, 0.6, 0.8)); KE.moss_clump((-0.6, Dp / 2 + 0.07, 0.05), 0.07, 61, (0, 0.6, 0.8))


def _kid_paint(hexc, name, stripe=None):
    """Çocuk eliyle sürülmüş boya: fırça izli, yer yer ince (altı görünür), kenarı biraz dağınık; bayrakta ikinci renk şerit."""
    def b(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(G.mapping(o, (3, 30, 3)), 2.0, 3), 0.3, 0.7, 0, 0.5), hexc, A._shade(hexc, 1.15))
        if stripe:
            sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(o, sp.inputs[0])
            col = G.mix(G.rng(sp.outputs['Z'], 0.03, 0.036), col, stripe)
        col = G.mix(G.rng(G.noise(o, 9, 4), 0.62, 0.72, 0, 0.35), col, '#c9a77a')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return KE.nodes_mat(name, b)


DECIM = [(r'^thatch$', 0.1), (r'^log$', 0.42), (r'^end$', 0.22), (r'^wend$', 0.35), (r'^rope$', 0.33), (r'^fray$', 0.4), (r'^(pole|dpost|wstick)$', 0.5),
         (r'^(door|brace|shutter|sill)$', 0.3), (r'^(lush|tufts|rosette|frond)$', 0.32), (r'^(pet|fc)$', 0.3), (r'^(Icosphere|moss)$', 0.25),
         (r'^(stem|frib)$', 0.4), (r'^(sand|wornground)$', 0.3), (r'^(starfish|shell)$', 0.3), (r'^(knot|flagstick|handle|axeh)$', 0.5),
         (r'^(wood|stump)$', 0.5), (r'^sun$', 0.5)]
WEIGHTS = [(r'^(door|sun|handle|brace)$', 1.7), (r'^(win|shutter|wstick|sill|flag)$', 1.4), (r'^(thatch|knot)$', 1.15), (r'^(log|end)$', 1.0),
           (r'^(dpost|pole)$', 1.2), (r'^(lush|tufts|rosette|stem|pet|fc|Icosphere|fray|sand|wornground)$', 0.5), (r'^inner$', 0.2)]

if __name__ == '__main__':
    KE.main(NAME, build, DECIM, WEIGHTS, CAP, ds_low=True, fix_normals=False)
