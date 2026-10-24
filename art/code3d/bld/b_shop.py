# Dükkân (pazar tezgâhı) — oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Temel: assets_town.c_shop (onaylı yerleşim: direkler, turkuaz tahta ön, şeritli tente, meyve sepetleri, kavanoz rafı, fenerler, tabela,
# önde meyve kasaları, arkada palmiye). Aynı yapıcı çağrılır → dış ölçüler/orijin/ön yön birebir (oyun EnvFootprint 8 m; dükkân
# penceresinde arka plan). Üstüne:
#   - malzemeler ada eskitmeli: turkuaz boya güneşte solmuş ve iri pullar halinde dökülmüş, tahtada tuz/su izi, dipte toprak + yosun,
#     oyuklarda kir; bir ön tahta sonradan değiştirilmiş (boyasız, açık ton, fazladan çivi); tente şeritleri canlı ama solgun lekeli;
#     palmiye yaprağı neon değil derin yeşil;
#   - direk tepelerinde halat bağ, tente köşelerinden direğe halat; tabelada deniz yıldızı;
#   - sağ yan panelde kurumaya asılmış balık ağı + iki şamandıra + deniz yıldızı; önde tebeşirli fiyat tahtası (elma = coin resmi);
#   - tezgâh altında (arkadan görünür) çuval ve küçük fıçı; ön dipte rüzgârın biriktirdiği kum, deniz kabukları, arka direk diplerinde yosun.
# Kullanım: python -I bld/b_shop.py -- <çıktı> [b_shop] [--draft <png>] [--stats]
import os, sys, math, random, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import koy_eskitme as KE
from koy_eskitme import AT, A, V, MN, bpy, bmesh, rbox, blob, cyl, tube, m_flat, m_leaf

NAME = 'b_shop'
CAP = 18000
Wd, Dp = 2.2, 1.1


def _swap(mapping):
    """Yapıcının malzemelerini adına göre (sondaki .001 atılır) yenileriyle değiştir."""
    for o in bpy.context.scene.objects:
        if o.type not in ('MESH', 'CURVE'): continue
        for i, m in enumerate(o.data.materials):
            if m is None: continue
            k = re.sub(r'\.\d+$', '', m.name)
            if k in mapping: o.data.materials[i] = mapping[k]


def net_drape(x, y0, y1, z_top, z_bot, M, seed=0):
    """Yan panele asılı, kurumaya bırakılmış balık ağı: panel üst kenarından dışa sarkan kalın, kıvrımlı örtü (alt kenarı dalgalı),
    üst kenarda içe kıvrılır. Ağ ilmekleri malzemede (m_net)."""
    R = random.Random(seed); NY, NZ = 16, 8; verts = []; faces = []; grid = []
    for i in range(NZ + 1):
        t = i / NZ; row = []
        for j in range(NY + 1):
            u = j / NY; y = y0 + (y1 - y0) * u
            fold = 0.025 * math.sin(u * math.pi * 5 + seed) * t + 0.012 * MN.noise(V((y * 6, t * 3, seed)))
            hang = (0.06 * math.sin(u * math.pi * 3 + 1.0) + 0.05 * MN.noise(V((y * 4, seed, 0)))) * t
            z = z_top - (z_top - z_bot) * t - hang
            xx = x + 0.022 + fold + 0.02 * t
            if i == 0: xx = x - 0.03                                     # üstte panelin arkasına kıvrılır
            row.append(len(verts)); verts.append((xx, y, z + (0.025 if i == 0 else 0)))
        grid.append(row)
    for i in range(NZ):
        for j in range(NY):
            faces.append((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    o = KE._mesh('net', verts, faces, M)
    sol = o.modifiers.new('th', 'SOLIDIFY'); sol.thickness = 0.018; sol.offset = 1.0
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    if sum(f.normal.x for f in bm.faces) < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o


def chalkboard(cx, cy, yaw):
    """Tebeşirli fiyat tahtası (A sehpa): koyu yeşil-gri levha + tahta çerçeve; tebeşirle elma, eşittir, coin resmi; tozlu silinti izleri."""
    a = math.radians(yaw)
    def P(dx, dy, dz): return (cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a), dz)
    FW = KE.m_wood2('#9a6a3c', 'chalkfr', salt=0.6, ground=0.2)
    def slate(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 3, 4), 0.3, 0.7), '#2f3d38', '#3b4a44')
        col = G.mix(G.rng(G.noise(G.mapping(o, (2, 2, 9)), 2, 3), 0.45, 0.7, 0, 0.35), col, '#7d8a84')   # silinti izi
        nt.links.new(col, bsdf.inputs['Base Color'])
    SL = KE.nodes_mat('slate', slate); CH = m_flat('#f4f1e6', 0.08, 12, 'chalk'); CY = m_flat('#f3c94a', 0.08, 12, 'chalky')
    tilt = 14
    for sgn in (-1, 1):   # arka ve ön ayaklar (A biçimi)
        for dx in (-0.2, 0.2):
            AT.plank('chalkleg', P(dx, sgn * 0.09, 0.27), (0.035, 0.03, 0.56), FW, rot=(sgn * tilt, 0, yaw), seed=int(dx * 10 + sgn * 3), amt=0.003)
    rbox('chalk', P(0, -0.105, 0.3), (0.42, 0.02, 0.36), SL, rot=(-tilt, 0, yaw), bevel=0.006)
    for (dx, dz, sx, sz) in ((0, 0.18, 0.46, 0.035), (0, -0.18, 0.46, 0.035), (-0.215, 0, 0.035, 0.36), (0.215, 0, 0.035, 0.36)):
        AT.plank('chalkfr', P(dx, -0.11 + dz * math.sin(math.radians(tilt)), 0.3 + dz * math.cos(math.radians(tilt))), (sx, 0.026, sz), FW,
                 rot=(-tilt, 0, yaw), seed=int(dz * 100 + dx * 10), amt=0.002)
    def onb(dx, dz, d=0.0):
        t = math.radians(tilt)
        return P(dx, -0.117 - d + dz * math.sin(t), 0.3 + dz * math.cos(t))
    # elma (tebeşir halka + sap + yaprak), "=", coin (sarı dolu daire + iç halka)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.007, location=onb(-0.11, 0.0), rotation=(math.radians(90 - tilt), 0, a), major_segments=20, minor_segments=4)
    bpy.context.object.name = 'chalkd'; bpy.context.object.data.materials.append(CH)
    rbox('chalkd', onb(-0.11, 0.07), (0.008, 0.006, 0.03), CH, rot=(-tilt, 0, yaw), bevel=0)
    rbox('chalkd', onb(-0.09, 0.075), (0.03, 0.006, 0.012), CH, rot=(-tilt, -30, yaw), bevel=0)
    for dz in (0.012, -0.012): rbox('chalkd', onb(0.0, dz), (0.05, 0.006, 0.009), CH, rot=(-tilt, 0, yaw), bevel=0)
    c = cyl('chalkd', onb(0.11, 0.0), 0.052, 0.006, CY, rot=(90 - tilt, 0, yaw), verts=16, bevel=0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.005, location=onb(0.11, 0.0, 0.004), rotation=(math.radians(90 - tilt), 0, a), major_segments=16, minor_segments=4)
    bpy.context.object.name = 'chalkd'; bpy.context.object.data.materials.append(m_flat('#c99a2a', 0.08, 12, 'chalky2'))


def build():
    AT.c_shop()
    # --- malzemeler: ada eskitmesi
    W = KE.m_wood2('#8d5f38', 'shopw', salt=0.7, ground=0.45)
    W2 = KE.m_wood2('#ad7a4a', 'shopw2', salt=0.6, ground=0.35)
    TOPW = KE.m_wood2('#bb8a58', 'shoptop', salt=0.5, ground=0.0)
    PAINT = KE.m_wood2('#a87a4c', 'shoppaint', paint='#25a09c', age=1.25, salt=1.0, ground=0.35, chips=1.25)
    SIGN = KE.m_wood2('#a87a4c', 'shopsign', paint='#f3e3c0', age=1.2, salt=0.8, ground=0.0, chips=1.2)
    CL = AT.m_cloth('#e9504c', '#fff1dc', stripes=7.0, name='awning2', age=1.15)
    PALM = m_leaf('#2c7430', '#479a3c', '#86c055', '#acd677', 'palmleaf2'); RIB = m_flat('#7aa84c', 0.15, 6, 'ribm2')
    _swap({'shopw': W, 'shopw2': W2, 'shoptop': TOPW, 'shoppaint': PAINT, 'shopsign': SIGN, 'awning': CL, 'palmleaf': PALM, 'ribm': RIB})
    # bir ön tahta sonradan değiştirilmiş: boyasız, açık ton, fazladan çivi
    NEW = KE.m_wood2('#c8975f', 'newplank', salt=0.2, ground=0.3, silver=0.04)
    fronts = sorted([o for o in bpy.context.scene.objects if re.sub(r'\.\d+$', '', o.name) == 'front'], key=lambda o: o.matrix_world.translation.x)
    if len(fronts) > 7:
        pk = fronts[7]; pk.data.materials.clear(); pk.data.materials.append(NEW)
        x = pk.matrix_world.translation.x
        for z in (0.33, 0.62): AT.nail((x, -Dp / 2 + 0.015, z), (0, -1, 0), streak=True)
    # --- halat bağlar: direk tepeleri + tente köşesinden direğe
    for sx in (-1, 1):
        for sy in (-1, 1):
            top = 2.0 if sy > 0 else 1.75
            cx, cy = KE.post_center((sx * Wd / 2, sy * Dp / 2, -0.03), (sx * Wd / 2, sy * Dp / 2, top), sx * 3 + sy, top - 0.165)
            KE.lash((cx, cy, 0), 0.064, top - 0.2, top - 0.13, 1.6, thick=0.012, seed=sx * 3 + sy)
        KE.rope3([(sx * Wd / 2, -Dp / 2, 1.66), (sx * (Wd / 2 + 0.08), -Dp / 2 - 0.2, 1.63), (sx * (Wd / 2 + 0.15), -Dp / 2 - 0.38, 1.62)], 0.011, seg=0.04, around=6)
    # tabelada deniz yıldızı
    KE.starfish((0.36, -0.229, 2.16), 0.06, yaw=20, nrm=(0, -0.98, -0.2), hexc='#f0844a')
    # --- sağ yan panel: kurumaya asılmış balık ağı + şamandıralar + deniz yıldızı
    NET = KE.m_net('net2')
    net_drape(Wd / 2 - 0.01, -0.12, 0.46, 0.9, 0.42, NET, seed=3)
    KE.buoy((Wd / 2 + 0.1, 0.05, 0.4), 0.06, '#f0663a'); KE.buoy((Wd / 2 + 0.1, 0.33, 0.45), 0.055, '#f2b632')
    KE.rope3([(Wd / 2 + 0.06, 0.05, 0.47), (Wd / 2 + 0.09, 0.05, 0.43)], 0.008, seg=0.02, around=6)
    KE.rope3([(Wd / 2 + 0.06, 0.33, 0.52), (Wd / 2 + 0.09, 0.33, 0.48)], 0.008, seg=0.02, around=6)
    KE.starfish((Wd / 2 + 0.06, 0.2, 0.72), 0.07, yaw=-10, nrm=(1, 0, 0.1), hexc='#e9704f')
    # --- önde tebeşirli fiyat tahtası
    chalkboard(-1.05, -0.98, 18)
    # --- tezgâh altında (arkadan görünür) çuval + küçük fıçı
    def burlap(nt, bsdf):
        G = KE.G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(G.mapping(o, (60, 60, 60)), 1.0, 2), 0.3, 0.7), '#a58a5c', '#c4a978')
        col = G.mix(G.rng(G.noise(o, 3, 4), 0.55, 0.7, 0, 0.35), col, '#7a6040')
        nt.links.new(col, bsdf.inputs['Base Color'])
    SACK = KE.nodes_mat('burlap', burlap)
    sk = blob('sack', (-0.62, 0.22, 0.24), (0.2, 0.17, 0.25), SACK, sub=1, seg=14); AT.wobble(sk, 0.025, 4.0, 7)
    tube('sack', [(-0.62, 0.22, 0.46), (-0.61, 0.22, 0.53), (-0.6, 0.23, 0.56)], [0.06, 0.035, 0.05], SACK, res=3)
    KE.lash((-0.62, 0.22, 0), 0.05, 0.47, 0.5, 1.5, thick=0.009, tail=False)
    AT.barrel((0.66, 0.24, 0.21), r=0.16, h=0.42, wood=KE.m_wood2('#9c6638', 'barrel2', salt=0.4, ground=0.3), iron=KE.IRON())
    # --- dip: rüzgârın biriktirdiği kum, kabuklar, arka direk diplerinde yosun
    KE.sand_drift(0.0, -Dp / 2 - 0.1, 1.05, 0.2, 0.055, seed=8, lean=(0, 0.7))
    KE.sand_drift(-1.25, 0.55, 0.4, 0.3, 0.05, seed=9)
    KE.shell((0.05, -1.05, 0.012), 0.05, yaw=-30); KE.shell((-0.25, -1.2, 0.012), 0.045, yaw=60, hexc='#f3dcd0', band='#d98f7a')
    KE.starfish((0.95, -1.0, 0.01), 0.07, yaw=40, hexc='#ef7a4c')
    for sx in (-1, 1):
        KE.moss_clump((sx * Wd / 2, Dp / 2 + 0.06, 0.05), 0.075, 20 + sx, (0, 0.6, 0.8))
    KE.moss_clump((-Wd / 2 + 0.05, -Dp / 2 + 0.02, 0.92 + 0.035), 0.04, 23, (0, 0, 1))


DECIM = [(r'^(orange|apple|tomato)$', 0.07), (r'^melon$', 0.15), (r'^(front|side|shelf|top|trim|slat|lid|brace|patch|sign|chalkleg|chalkfr)$', 0.12),
         (r'^(jar)$', 0.12), (r'^(lush|tufts|rosette|backbush|basebush|potplant|ctops|fleaf|fray|fibers)$', 0.25),
         (r'^(pet|fc)$', 0.2), (r'^(Icosphere|moss)$', 0.22), (r'^(stem|stemb)$', 0.2), (r'^(nail|streak)$', 0.25), (r'^(rope)$', 0.2),
         (r'^(starfish|shell)$', 0.2), (r'^(rib|root)$', 0.25), (r'^trunk$', 0.35), (r'^(leaflets)$', 0.45), (r'^(nut|crown)$', 0.3),
         (r'^(banana|btip|bstem|carrot)$', 0.25), (r'^(lamp|lcap)$', 0.25), (r'^(basket|pot|cup)$', 0.4), (r'^(edge|core)$', 0.25),
         (r'^(net)$', 0.4), (r'^(buoy)$', 0.15), (r'^(barrel|sack)$', 0.2), (r'^(Torus)$', 0.3), (r'^(chalkd)$', 0.5),
         (r'^(post)$', 0.5), (r'^(wornground)$', 0.5), (r'^(awning)$', 0.7), (r'^(signpost|bag)$', 0.4)]
WEIGHTS = [(r'^(sign|bag|chalk|chalkd|chalkfr)$', 1.8), (r'^(front|side|trim)$', 1.35), (r'^(awning)$', 1.3), (r'^(orange|apple|tomato|melon|banana|carrot|jar|basket)$', 1.2),
           (r'^(net|buoy|starfish)$', 1.3), (r'^(top|shelf|post)$', 1.1),
           (r'^(lush|tufts|rosette|backbush|basebush|stem|pet|fc|Icosphere|fray|sand|wornground|fibers)$', 0.5), (r'^(leaflets|rib|trunk|nut|crown|root)$', 0.6),
           (r'^(core|cratein)$', 0.3)]

if __name__ == '__main__':
    KE.main(NAME, build, DECIM, WEIGHTS, CAP, ds_low=True, cage=0.025, ray=0.1)
