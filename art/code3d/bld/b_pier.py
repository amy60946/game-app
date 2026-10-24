# İskele oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Eski c_pier (assets_town) tüm yapıyı 7 bin üçgene küresel sadeleştirip yalnız renk + AO pişiriyordu: tahta damarı, çivi, halat
# burgusu eriyor; su çizgisi kazığa geçirilmiş yeşil bir manşon gibi duruyordu. Burada ayrıntılı taslak kurulur, bld_kit hattıyla
# (aynı ağ, yalnız eğri parçalar sadeleşir; renk × AO + normal haritası) pişirilir. Taslak:
#   - güneşte gümüşileşmiş gri-kahve güverte tahtaları (üstü solgun, yanları sıcak), aralıklar belirgin; iki yeni değiştirilmiş açık
#     tahta, bir kalkık, bir kırık kısa tahta (alttaki kiriş görünür); kirişlere çakılı çivi başları + pas haleleri;
#   - taşıyıcı düzen: kazık başı kirişleri + boyuna üç kiriş + yan çapraz destekler (cıvata, pas akıntısı), kazık başında demir çember;
#   - kazıkların su çizgisi: su altı koyu-yeşil, ıslak koyu bant, tırtıklı yosun şeridi, midye kümeleri (kabarık), tuz çizgisi;
#     kazık tepesinde yıllık halkalı kesik + liken; deniz yıldızı;
#   - kıyı yanında halat korkuluk (dikmelere sarılı), deniz ucunda merdiven, demir baba + boyun halkası + suya inen palamar,
#     güvertede halat kangalı, turuncu usturmaça, can simidi (tutamak halatlı), balık ağı yığını + mantarlar, sandık (balık
#     işaretli), kova (içinde su), fener direğinde gemi feneri + yaslanmış olta.
# Ölçü ve yön eski FBX ile aynı (bölge 'pier', EnvFootprint 8,6 m yatay): orijin su seviyesinde (z = 0), boy x, güverte üstü 0,465;
# su çizgisi oyunda ~z 0 (deniz y −0,02, dalga ±0,09 m; ölçek ~2,3).
# Kullanım: python -I bld/b_pier.py -- <çıktı> [b_pier] [--draft <png> [--yaw Y]]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kiyi_kit as KK
from kiyi_kit import bpy, V, A, AT, kit, rbox, cyl, blob, tube, bk, overlay, L_waterline, L_sunbleach, L_streaks, L_chain

L, WD = 3.2, 1.3
DECK = 0.44                 # güverte tahtası merkezi (kalınlık 0,05 → üst 0,465)
TOP = DECK + 0.025
PX = (-L / 2 + 0.15, 0.0, L / 2 - 0.15)
PY = (-WD / 2 - 0.05, WD / 2 + 0.05)
PR = 0.13


def pile_top(x, y):
    if x == PX[2]: return 0.75                     # deniz ucu (fener direği / palamar kazığı)
    if y > 0: return 0.86                          # kıyı yanı: halat korkuluk dikmesi
    return 0.52


def build():
    kit.reset(); random.seed(11)
    R = random.Random(5)
    wl = L_waterline(0.0, wet=0.14)
    NOG = (-9.0, -8.6)            # weather() dip kiri kapalı: parçaların nesne Z'si yerel (tahtada her yer 'dip' sayılıyordu)
    PL = overlay(A.m_wood('#73553a', 'pile', age=1.3, grime=NOG), wl, 'pile_k')
    PL2 = overlay(A.m_wood('#7d5c3e', 'beam', age=1.2, grime=NOG), L_sunbleach(0.25), 'beam_k')
    tones = ('#b88e64', '#a98a6a', '#c39a6c', '#9e7a58')
    DKS = [overlay(A.m_wood(c, f'pdeck{i}', age=1.25, grime=NOG), L_sunbleach(0.24), f'pdeck{i}_k') for i, c in enumerate(tones)]
    FRESH = overlay(A.m_wood('#d29c5e', 'pdeckfresh', age=0.45, grime=NOG), L_sunbleach(0.1), 'pdeckfresh_k')
    RP = AT.m_rope(); RPW = overlay(AT.m_rope('#c9a974', 'ropewet'), wl, 'ropewet_k')
    for m in [PL, PL2, FRESH] + DKS: KK.bumpify(m, 0.1, 0.003)      # hafif: güçlüsü damarı oluklu karton gibi gösteriyordu
    I = AT.m_metal('#45414b', name='iron')

    # ---- kazıklar: su altı parçası ayrı (az doku), üstü su çizgisiyle
    for x in PX:
        for y in PY:
            top = pile_top(x, y); sd = int(x * 7 + y * 3) + 20
            tube('pile_sub', [(x, y, -0.6), (x, y, -0.13)], [PR * 1.01, PR * 1.01], PL, res=2)
            mid = (x + 0.012 * math.sin(sd), y + 0.01 * math.cos(sd), (top - 0.15) / 2)
            o = tube('pile', [(x, y, -0.15), mid, (x + 0.01, y, top)], [PR, PR * 0.96, PR * 0.92], PL, res=4)
            o.data.bevel_resolution = 2
            KK.endgrain_cap(x + 0.01, y, top, PR * 0.92, seed=sd)
            KK.barnacles_on_post(x, y, PR * 1.0, -0.1, 0.05, 34, seed=sd, size=(0.01, 0.02))
            # demir çember (kazık başı) + iki cıvata
            cyl('band', (x + 0.006, y, 0.17), PR * 1.06, 0.045, I, verts=16, bevel=0.006)
            for a in (0.6, 3.6):
                n = V((math.cos(a), math.sin(a), 0)); KK.bolt(V((x, y, 0.17)) + n * PR * 1.08, n, I, r=0.014, drip=0.07)
    # deniz yıldızı (kıyı yanı orta kazık, su çizgisinin hemen üstü)
    ST = A.m_flat('#f4844e', 0.18, 12, 'starfish')
    pts = [(math.cos(math.pi / 2 + k * math.pi / 5) * (0.062 if k % 2 == 0 else 0.027), math.sin(math.pi / 2 + k * math.pi / 5) * (0.062 if k % 2 == 0 else 0.027)) for k in range(10)]
    o = AT.prism('star', pts, 0.022, ST, loc=(0.02, PY[0] - PR + 0.0, 0.085), rot=(0, 12, 0), bevel=0.008)    # dolgun beş kollu yıldız (ince kollar örümceğe benziyordu)
    for k in range(5):
        a = math.pi / 2 + k * 2 * math.pi / 5
        bk(blob('stardot', (0.02 + math.cos(a) * 0.03, PY[0] - PR - 0.013, 0.085 + math.sin(a) * 0.03), (0.007, 0.004, 0.007), A.m_flat('#ffd2a8', 0.1, 6, 'stardot'), sub=0, seg=8))

    # ---- taşıyıcılar: kazık başı kirişleri (enine) + boyuna kirişler + yan çapraz destekler
    for x in PX:
        KK.plank2('beam', (x, 0, 0.255), (0.12, WD + 0.3, 0.1), PL2, seed=int(x * 10) + 50)
        for y in (-0.42, 0.42):
            KK.bolt((x - 0.061, y, 0.255), (-1, 0, 0), I, r=0.016, drip=0.05)
    for y in (-0.45, 0.0, 0.45):
        KK.plank2('stringer', (0, y, 0.36), (L + 0.08, 0.09, 0.105), PL2, seed=int(y * 10) + 70)
    for y in PY:
        for (xa, xb) in ((PX[0], PX[1]), (PX[1], PX[2])):
            a = V((xa + 0.08, y, 0.06)); b = V((xb - 0.08, y, 0.205)); d = b - a
            ang = math.degrees(math.atan2(d.z, d.x)); c = (a + b) / 2
            KK.plank2('xbrace', tuple(c), (d.length + 0.16, 0.05, 0.085), PL2, rot=(0, -ang, 0), seed=int(xa * 9 + y * 5) + 90)
            s = 1 if y > 0 else -1
            for p in (a + d.normalized() * 0.02, b - d.normalized() * 0.02):
                KK.bolt((p.x, y + s * 0.027, p.z), (0, s, 0), I, r=0.017, drip=0.06, square=True)

    # ---- güverte tahtaları
    widths = (0.17, 0.155, 0.18, 0.165)
    k = 0; x = -L / 2
    while x < L / 2 - 0.05:
        w = min(widths[k % 4], L / 2 - x)
        if w < 0.06: break
        m = FRESH if k in (5, 13) else DKS[(k * 3 + 1) % 4]
        cx = x + w / 2; ln = WD + AT.R_j(k + 1) * 0.04; cy = AT.R_j(k) * 0.03; z = DECK; rot = (0, 0, AT.R_j(k) * 1.2)
        if k == 9: rot = (0, 2.2, AT.R_j(k) * 1.2); z = DECK + 0.009                  # kalkık tahta
        if k == 16: ln = WD * 0.6; cy = WD / 2 - ln / 2 + 0.02                         # kırık kısa tahta (altta kiriş görünür)
        KK.plank2('deck', (cx, cy, z), (w - 0.02, ln, 0.05), m, rot=rot, seed=k + 60)
        for yy in ((-0.45, 0.0, 0.45) if k % 3 == 0 else (-0.45, 0.45)):
            if abs(yy - cy) > ln / 2 - 0.04: continue
            for dx in (-w * 0.26, w * 0.26):
                KK.nail_top((cx + dx, yy + R.uniform(-0.015, 0.015), TOP + (0.009 if k == 9 else 0.0)))
        x += w; k += 1

    # ---- kıyı yanı halat korkuluk (dikmelere sarılı)
    yR = PY[1]
    for xa, xb, za, zb in ((PX[0], PX[1], 0.8, 0.8), (PX[1], PX[2], 0.8, 0.7)):
        KK.rope_sag((xa + 0.12, yR, za), (xb - 0.12, yR, zb), 0.1, RP, thick=0.02)
    for x in PX[:2]:
        KK.rope_wrap((x, yR, 0), 0.14, 0.74, 0.83, 1.6, RP, thick=0.016, seed=x)
    for x in (PX[2],):
        for y in PY:
            KK.rope_wrap((x, y, 0), 0.14, 0.55, 0.66, 1.8, RP, thick=0.016, seed=y)

    # ---- deniz ucu: merdiven (suya iner; alt basamaklar yosunlu)
    LX = L / 2 + 0.07
    for y in (0.13, 0.41):
        tube('ladder', [(LX, y, -0.42), (LX + 0.005, y, 0.1), (LX, y, 0.53)], [0.03, 0.03, 0.028], PL, res=2)
    for z in (0.31, 0.11, -0.09, -0.29):
        tube('rung', [(LX, 0.13, z), (LX, 0.41, z)], [0.019, 0.019], PL, res=2)
    KK.barnacles_on_post(LX, 0.13, 0.03, -0.08, 0.06, 7, seed=91, size=(0.008, 0.014))
    KK.barnacles_on_post(LX, 0.41, 0.03, -0.08, 0.06, 7, seed=92, size=(0.008, 0.014))

    # ---- demir baba + boyun halkası + palamar (güverte köşesinden suya iner)
    BX, BY = L / 2 - 0.45, -0.3
    bb = AT.lathe('bollard', [(0.001, TOP), (0.11, TOP), (0.1, TOP + 0.03), (0.08, 0.6), (0.075, 0.68), (0.112, 0.72), (0.095, 0.765), (0.001, 0.775)], I, segs=16)
    bb.location = (BX, BY, 0)
    for a in range(4):
        n = V((math.cos(a * 1.57 + 0.4), math.sin(a * 1.57 + 0.4), 0))
        KK.bolt(V((BX, BY, TOP + 0.012)) + n * 0.085 + V((0, 0, 0.004)), (0, 0, 1), I, r=0.014, drip=0)
    bk(blob('rustpool', (BX + 0.05, BY - 0.09, TOP + 0.0015), (0.13, 0.07, 0.002), A.m_flat('#8a4f2c', 0.4, 40, 'rustpool'), rot=(0, 0, -25), sub=0, seg=12))   # babanın dibinde pas lekesi
    loop = [(BX + math.cos(t / 12 * 2 * math.pi) * 0.092, BY + math.sin(t / 12 * 2 * math.pi) * 0.092, 0.655 + 0.012 * math.sin(t / 12 * 4 * math.pi)) for t in range(13)]
    KK.rope(loop, 0.018, RP, sides=6)
    KK.rope([(BX + 0.09, BY - 0.02, 0.655), (BX + 0.3, BY - 0.15, 0.56), (1.55, -0.56, TOP + 0.03), (1.64, -0.665, TOP + 0.005),
                    (1.72, -0.73, 0.36), (1.87, -0.85, 0.13), (2.095, -1.0, -0.13)], 0.02, RPW, sides=8)
    # halat kangalı (palamarın artığı), kuyruğu babaya
    KK.coil(0.68, -0.3, TOP, 0.035, 3.2, 0.018, RP, seed=1.0, tail=[(0.86, -0.36, TOP + 0.02), (1.0, -0.33, TOP + 0.022)])

    # ---- usturmaça (deniz yanı, turuncu) ipiyle
    FX = 0.28
    FN = overlay(A.m_flat('#ee7a3c', 0.14, 9, 'fender'), L_streaks('#6d5a45', 0.4, z_top=0.32, length=0.3, scale=10), 'fender_k')
    KK.rope([(FX, -0.5, TOP + 0.02), (FX, -0.64, TOP + 0.03), (FX, -0.70, 0.43), (FX, -0.75, 0.33)], 0.012, RP, sides=6)
    blob('fender', (FX, -0.775, 0.21), (0.068, 0.068, 0.125), FN, sub=1, seg=16)
    cyl('fendercap', (FX, -0.775, 0.335), 0.03, 0.03, A.m_flat('#d8622e', 0.1, 9, 'fendercap'), verts=12)

    # ---- can simidi: kazıktaki çiviye asılı, dört tutamak bağı + çevre halatı
    LB = AT.m_cloth('#fff3e2', '#e2524c', stripes=4.0, name='lifering', age=1.1)
    lx, ly, lz = PX[0], PY[0] - 0.2, 0.42
    tube('peg', [(lx, PY[0] - PR + 0.02, 0.575), (lx, ly - 0.03, 0.585)], [0.016, 0.014], PL2, res=2)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.165, minor_radius=0.054, location=(lx, ly, lz), rotation=(math.radians(90), 0, 0), major_segments=40, minor_segments=14)
    t = bpy.context.object; t.name = 'lifering'; t.data.materials.append(LB)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi) + 0.0625) % 1.0, 0)
    for poly in me.polygons: poly.use_smooth = True
    ties = [i * math.pi / 2 + math.pi / 4 for i in range(4)]
    for a in ties:
        c = V((lx + math.cos(a) * 0.165, ly, lz + math.sin(a) * 0.165))
        pts = []
        for j in range(9):
            b = j / 8 * 2 * math.pi
            rad = V((math.cos(a), 0, math.sin(a)))
            pts.append(tuple(c + rad * math.cos(b) * 0.062 + V((0, 1, 0)) * math.sin(b) * 0.062 + V((-math.sin(a), 0, math.cos(a))) * (j - 4) * 0.004))
        KK.rope(pts, 0.009, RP, sides=4)
    for i in range(4):
        a0, a1 = ties[i], ties[(i + 1) % 4] + (2 * math.pi if i == 3 else 0)
        pts = []
        for j in range(7):
            a = a0 + (a1 - a0) * j / 6; rr = 0.222 - 0.012 * math.sin(j / 6 * math.pi)
            pts.append((lx + math.cos(a) * rr, ly, lz + math.sin(a) * rr))
        KK.rope(pts, 0.009, RP, sides=4)

    # ---- kıyı ucu: sandık (balık işaretli), ağ yığını + mantarlar, kova
    AT.crate((-0.9, 0.25, TOP), 0.4, DKS[1], PL2, yaw=12, seed=6)
    a = math.radians(12)
    fish = [(math.cos(t) * 0.075, math.sin(t) * 0.04) for t in [i / 10 * 2 * math.pi for i in range(10)]] + []
    body = AT.prism('fishpaint', [(x_ - 0.02, z_) for x_, z_ in fish], 0.004, A.m_flat('#2f86a6', 0.2, 20, 'fishpaint'), bevel=0)
    tail = AT.prism('fishpaint', [(0.045, 0.0), (0.105, 0.045), (0.105, -0.045)], 0.004, A.m_flat('#2f86a6', 0.2, 20, 'fishpaint'), bevel=0)
    for o in (body, tail):
        o.location = (-0.9 + math.sin(a) * 0.226, 0.25 - math.cos(a) * 0.226, TOP + 0.2); o.rotation_euler = (0, 0, a); bk(o)
    NET = KK.m_net()
    KK.lumpy('net', (-1.27, -0.06, TOP - 0.004), (0.2, 0.16, 0.1), NET, seed=3, folds=0.22)
    KK.lumpy('net', (-1.12, 0.12, TOP - 0.004), (0.13, 0.1, 0.06), NET, seed=8, folds=0.25)
    FL = [A.m_flat('#e8703a', 0.15, 10, 'floatO'), A.m_flat('#f1e2bc', 0.12, 10, 'floatC')]
    for i, (fx, fy, fz, rz) in enumerate(((-1.36, -0.12, 0.555, 20), (-1.2, -0.02, 0.56, 70), (-1.3, 0.04, 0.545, -30), (-1.08, 0.15, 0.525, 10), (-1.17, -0.17, 0.5, 45))):
        cyl('float', (fx, fy, fz), 0.032, 0.05, FL[i % 2], rot=(90, 0, rz), verts=12, bevel=0.008)
    BKT = A.m_wood('#a8693d', 'bucket', age=1.1)
    bu = AT.lathe('bucket', [(0.001, TOP), (0.11, TOP), (0.14, 0.7), (0.145, 0.72), (0.132, 0.722), (0.127, 0.7), (0.1, 0.5), (0.001, 0.5)], BKT, segs=18)
    bu.location = (-0.45, 0.4, 0)
    for zz, rr in ((0.53, 0.118), (0.67, 0.137)):
        bpy.ops.mesh.primitive_torus_add(major_radius=rr + 0.006, minor_radius=0.008, location=(-0.45, 0.4, zz), major_segments=20, minor_segments=5)
        bpy.context.object.name = 'hoop'; bpy.context.object.data.materials.append(I)
    cyl('bwater', (-0.45, 0.4, 0.66), 0.124, 0.006, A.m_flat('#2a7f8c', 0.25, 6, 'bwater'), verts=18, bevel=0)
    tube('handle', [(-0.45 - 0.14, 0.4, 0.70), (-0.45 - 0.1, 0.36, 0.82), (-0.45 + 0.1, 0.36, 0.82), (-0.45 + 0.14, 0.4, 0.70)], [0.007] * 4, I, res=3)

    # ---- fener direği + gemi feneri + yaslanmış olta
    fx, fy = PX[2], PY[1]
    AT.post('lamppost', (fx, fy, 0.75), (fx, fy, 1.45), 0.045, PL, seed=9)
    tube('arm', [(fx, fy, 1.4), (fx, fy - 0.2, 1.45), (fx, fy - 0.3, 1.38)], [0.014] * 3, I, res=4)
    lx2, ly2 = fx, fy - 0.3
    bpy.ops.mesh.primitive_torus_add(major_radius=0.022, minor_radius=0.006, location=(lx2, ly2, 1.36), rotation=(math.radians(90), 0, 0), major_segments=10, minor_segments=4)
    bpy.context.object.name = 'lhook'; bpy.context.object.data.materials.append(I)
    GL = AT.m_glow('#ffcf5a', 'pierglow', lamp=(0, 0, 0, 0.08))
    cyl('glass', (lx2, ly2, 1.255), 0.05, 0.11, GL, verts=12, bevel=0)
    for k2 in range(4):
        aa = k2 * math.pi / 2 + math.pi / 4
        cyl('lbar', (lx2 + math.cos(aa) * 0.055, ly2 + math.sin(aa) * 0.055, 1.255), 0.007, 0.12, I, verts=6, bevel=0)
    AT.lathe('lcap', [(0.001, 1.31), (0.072, 1.31), (0.068, 1.322), (0.035, 1.35), (0.001, 1.355)], I, segs=12).location = (lx2, ly2, 0)
    AT.lathe('lbase', [(0.001, 1.19), (0.066, 1.19), (0.07, 1.2), (0.06, 1.214), (0.001, 1.214)], I, segs=12).location = (lx2, ly2, 0)
    ROD = A.m_flat('#3b2c26', 0.15, 8, 'rod'); CORK = A.m_flat('#c8a272', 0.25, 30, 'cork')
    a0, a1 = V((1.04, 0.42, TOP + 0.01)), V((1.56, 0.74, 1.24)); dd = (a1 - a0)
    tube('rodgrip', [tuple(a0), tuple(a0 + dd * 0.17)], [0.02, 0.018], CORK, res=2)
    tube('rod', [tuple(a0 + dd * 0.16), tuple(a0 + dd * 0.55), tuple(a1)], [0.012, 0.008, 0.005], ROD, res=3)
    cyl('reel', (1.1, 0.45, 0.6), 0.03, 0.022, I, rot=(90, 0, 58), verts=12, bevel=0.004)
    blob('bobber', (1.15, 0.43, 0.58), (0.022, 0.022, 0.028), A.m_flat('#e8463c', 0.1, 6, 'bobber'), sub=1, seg=10)
    blob('bobber', (1.15, 0.43, 0.6), (0.02, 0.02, 0.016), A.m_flat('#fff6ea', 0.05, 6, 'bobberw'), sub=1, seg=10)
    return 'iskele'


# nesne adı → kendi içinde sadeleştirme (eğri/yoğun parçalar; tahta kutular olduğu gibi)
DECIM = [(r'^(pile|ladder|rung)$', 0.55), (r'^lifering$', 0.45), (r'^net$', 0.35),
         (r'^(slat|brace|lid|edge)$', 0.4), (r'^(fender|float|bucket|hoop|bollard)$', 0.6),
         (r'^(rod|rodgrip|handle|arm|lamppost|peg|star|bobber)$', 0.5), (r'^band$', 0.6)]
# nesne adı → UV yoğunluğu (yakın/önemli parçalar çok, su altı ve kiriş altı az)
WEIGHTS = [(r'^deck(_lo)?$', 1.55), (r'^lifering$', 1.7), (r'^(glass|lbar|lcap|lbase|lhook)$', 1.6), (r'^(fender|fendercap)$', 1.4),
           (r'^(slat|brace|lid|edge|core)$', 1.2), (r'^(net|float)$', 1.25), (r'^pile$', 1.05), (r'^pile_sub$', 0.3),
           (r'^(stringer|beam)(_lo)?$', 0.55), (r'^xbrace(_lo)?$', 0.8), (r'^ropecore', 0.8), (r'^(ladder|rung)$', 0.85), (r'^(bucket|bwater|hoop|handle)$', 1.15),
           (r'^bollard$', 1.2), (r'^band$', 0.9)]

if __name__ == '__main__':
    KK.main('b_pier', build, DECIM, WEIGHTS, budget=13000, tex=1024, floor=-0.5)
