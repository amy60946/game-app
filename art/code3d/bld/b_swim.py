# Yüzme koyu oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Not: pişmiş v6 adasında koy havuzu süs olarak p_pool ile gelir (MapWorld.BuildRegion); b_swim pişmemiş (eski) ada ve yedek içindir.
# Eski c_swim (assets_town) 6,5 bin üçgene küresel sadeleşiyordu: kaya çatlakları, merdiven, iskele tahtası eriyordu. Taslak
# (eski yerleşim, sınırlar değişmesin; en yüksek nokta 0,58 → şemsiye/direk gibi yüksek parça yok):
#   - kenar kayaları: su çizgisinde ıslak koyu bant + yosun şeridi + midye beneği (dış halka kuru, yosunlu tepe);
#   - atlama iskelesi: solmuş turkuaz boyalı, dökülmüş tahta, paslı cıvatalar, ayakları su çizgili; çelik merdiven dipte paslı;
#   - suda: kırmızı-beyaz şamandıralı kulvar halatı (iki yanda kazık), simit, nilüfer + çiçek, simit ve merdiven çevresinde halka dalga;
#   - kıyıda: can simidi asılı kısa direk + yüzücü/dalga boyalı küçük tabela (dökülmüş boya), taşa serili çizgili havlu + terlik,
#     geniş yapraklı bitkiler, ot ve çiçek (eski tohumlar).
# Ölçü ve yön eski FBX ile aynı (bölge 'pool', EnvFootprint 8,6 m yatay): orijin zemin, su yüzü z 0,12.
# Kullanım: python -I bld/b_swim.py -- <çıktı> [b_swim] [--draft <png> [--yaw Y]]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kiyi_kit as KK
from kiyi_kit import bpy, bmesh, V, A, AT, kit, rbox, cyl, blob, tube, bk, lo, overlay, L_waterline, L_sunbleach, L_streaks, L_chain

NOG = (-9.0, -8.6)
WZ = 0.12


def to_world(o):
    """Konumu ağa işle (nesne koordinatı = dünya): su çizgisi katmanı dünya Z'sine göre çalışır."""
    from mathutils import Matrix
    o.data.transform(Matrix.Translation(o.location)); o.location = (0, 0, 0)
    return o


def rad(a): return 1.0 + 0.12 * math.sin(a * 3 + 1) + 0.07 * math.sin(a * 5)


def build():
    kit.reset(); random.seed(9)
    R = random.Random(9)
    base_rock = dict(moss_th=(0.95, 1.25), warm=('#a39586', '#bba996', '#d2c2a8'))
    STN_IN = overlay(A.m_rock(name='poolrock', **base_rock), L_waterline(WZ, wet=0.1, band=(WZ - 0.035, WZ + 0.035), amt=0.9), 'poolrock_wl')
    STN = A.m_rock(name='poolrock2', **base_rock)
    # su yüzeyi (eski düzensiz elips) + taban çanağı
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    N = 40; ctr = bm.verts.new((0, 0, WZ)); ring = []
    for i in range(N):
        a = i / N * 2 * math.pi; ring.append(bm.verts.new((math.cos(a) * rad(a) * 1.15, math.sin(a) * rad(a) * 0.85, WZ)))
    for i in range(N): bm.faces.new((ctr, ring[i], ring[(i + 1) % N]))
    water = A.link_mesh('water', bm, [AT.m_water()])
    sm = water.modifiers.new('sub', 'SUBSURF'); sm.levels = 2
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(0, 0, -0.26))
    bowl = bpy.context.object; bowl.name = 'bowl'; bowl.scale = (1.2, 0.9, 0.35); bowl.data.materials.append(AT.m_sand('poolbed', '#c9b58a'))
    # kenar kayaları (su çizgili) + dış halka (kuru)
    for i in range(22):
        a = i / 22 * 2 * math.pi + R.uniform(-0.05, 0.05)
        rr = rad(a); r = R.uniform(0.17, 0.27)
        o = AT.rock((math.cos(a) * rr * 1.25, math.sin(a) * rr * 0.95, 0.1), r, STN_IN, i, sq=(1.0, 1.0, 0.75)); o.name = 'rock'; to_world(o)
    for i in range(10):
        a = i / 10 * 2 * math.pi + 0.3; rr = rad(a) + 0.3
        o = AT.rock((math.cos(a) * rr * 1.25, math.sin(a) * rr * 0.98, 0.18), R.uniform(0.22, 0.32), STN, i + 40, sq=(1.0, 1.0, 0.9)); o.name = 'rockout'
    # atlama iskelesi: boyalı tahta (dökülmüş), ayaklar su çizgili, cıvatalar
    I = AT.m_metal('#4d4852', name='swimiron')
    DP = overlay(A.m_wood('#c9a77a', 'divepaint', paint='#2fa3a0', age=1.6, grime=NOG), L_sunbleach(0.2), 'divepaint_k')
    DW = overlay(A.m_wood('#8f5d36', 'divep', age=1.3, grime=NOG), L_waterline(WZ, wet=0.08, band=(WZ - 0.03, WZ + 0.03)), 'divep_k')
    KK.plank2('dive', (0.3, 0.65, 0.42), (0.36, 0.95, 0.06), DP, rot=(-4, 0, 0), seed=3, bevel=0.012)
    for y in (0.95, 1.12):
        for x in (0.18, 0.42):
            o = tube('dpost', [(x, y, -0.02), (x + 0.004, y, 0.2), (x, y, 0.42)], [0.04, 0.038, 0.036], DW, res=2); o.data.bevel_resolution = 2
    for y in (0.75, 1.03):
        for x in (0.2, 0.4):
            KK.bolt((x, y, 0.45 - 0.0698 * (y - 0.65)), (0, 0.07, 1), I, r=0.014, drip=0)
    tube('dbrace', [(0.18, 0.95, 0.12), (0.42, 1.12, 0.36)], [0.022, 0.022], DW, res=2)
    # çelik merdiven: dipte pas
    ST = overlay(AT.m_metal('#c9ccd6', '#9a6a4a', 'steel', age=0.8), L_streaks('#9c5a34', 0.6, z_top=0.36, length=0.3, scale=26), 'steel_k')
    for sx in (-0.12, 0.12):
        tube('lrail', [(-1.1 + sx, -0.3, 0.05), (-1.15 + sx, -0.3, 0.5), (-1.3 + sx, -0.3, 0.55), (-1.38 + sx, -0.3, 0.4)], [0.02] * 4, ST, res=4)
    for z in (0.15, 0.3):
        tube('rung', [(-1.24, -0.3, z), (-1.0, -0.3, z)], [0.015, 0.015], ST, res=2)
    # simit (eski yer) + çevresinde halka dalga
    RING = AT.m_cloth('#ff7aa8', '#fff1d6', stripes=4.0, name='floatie', age=1.1)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.2, minor_radius=0.075, location=(-0.4, 0.14, 0.15), major_segments=32, minor_segments=12)
    t = bpy.context.object; t.name = 'floatie'; t.data.materials.append(RING); t.rotation_euler = (math.radians(6), 0, 0)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, 0)
    RIP = A.m_flat('#bff2ee', 0.1, 6, 'ripple')
    for (cx, cy, r0) in ((-0.4, 0.14, 0.33), (-0.4, 0.14, 0.42), (-1.12, -0.3, 0.12), (-1.12, -0.3, 0.2), (0.3, 0.2, 0.14)):
        bpy.ops.mesh.primitive_torus_add(major_radius=r0, minor_radius=0.006, location=(cx, cy, WZ + 0.001), major_segments=40, minor_segments=4)
        o = bpy.context.object; o.scale = (1, 1, 0.25); o.data.materials.append(RIP); o.name = 'ripple'; bk(o)
    # kulvar halatı: iki kazık arası, kırmızı-beyaz şamandıralar
    RP = AT.m_rope('#d2b27a', 'swimrope')
    pa, pb = V((-1.12, -0.36, WZ + 0.03)), V((1.13, -0.46, WZ + 0.03))
    for p, sd in ((pa, 1), (pb, 2)):
        o = tube('lanepost', [(p.x, p.y, -0.05), (p.x, p.y, 0.34)], [0.035, 0.032], DW, res=2); o.data.bevel_resolution = 2
        KK.endgrain_cap(p.x, p.y, 0.34, 0.032, seed=sd, lichen=False)
    pts = [tuple(pa.lerp(pb, t / 12) + V((0, 0, -0.01 * math.sin(t / 12 * math.pi)))) for t in range(13)]
    KK.rope(pts, 0.008, RP, sides=4)
    FLT = [A.m_flat('#e8463c', 0.12, 8, 'laneR'), A.m_flat('#fff3e2', 0.08, 8, 'laneW')]
    n = 14
    for k in range(1, n):
        p = pa.lerp(pb, k / n)
        d = (pb - pa).normalized()
        o = cyl('lanefloat', (p.x, p.y, WZ + 0.02), 0.032, 0.07, FLT[k % 2], rot=(90, 0, math.degrees(math.atan2(d.y, d.x)) + 90), verts=10, bevel=0)
    # nilüfer + çiçek (eski), kenarda bitkiler
    LP = A.m_leaf('#3f9a3a', '#5fb446', '#8fd06a', '#b5e26a', 'lilypad')
    for k, (x, y) in enumerate(((0.66, -0.12), (0.84, 0.06), (-0.9, 0.4))):
        blob('lily', (x, y, 0.13), (0.13, 0.13, 0.01), LP, sub=0, seg=16)
    A.flower_heads([(0.66, -0.12, 0.16), (-0.9, 0.41, 0.16)], R, size=1.1)
    BL = A.m_leaf('#2f8a3a', '#4fb24a', '#9ad667', '#c2ea8e', 'baseleaf')
    A.mesh_from_blades('plants', A.rosette([(1.55, 0.35), (-1.5, 0.55), (1.2, -1.0), (-0.9, -1.15)], R, sizes=(0.35, 0.5), leaves=9), [BL])
    AT.dress(1.8, 22, n_tufts=8, flowers=5, pebbles=0, stone=STN, exclude=lambda x, y: (x / 1.55) ** 2 + (y / 1.2) ** 2 < 1.0)
    # kıyıda: can simidi direği + küçük tabela; havlu + terlik
    PX, PY = -1.62, -0.42
    SP = A.m_wood('#7a5232', 'swimpost', age=1.3, grime=NOG)
    o = tube('buoypost', [(PX, PY, -0.03), (PX, PY, 0.52)], [0.034, 0.03], SP, res=2); o.data.bevel_resolution = 2
    KK.endgrain_cap(PX, PY, 0.52, 0.03, seed=5, lichen=True)
    SG = overlay(A.m_wood('#c9a77a', 'swimsign', paint='#f4ead2', age=1.7, grime=NOG), L_sunbleach(0.15), 'swimsign_k')
    KK.plank2('sign', (PX + 0.035, PY - 0.0, 0.43), (0.025, 0.26, 0.16), SG, seed=17, bevel=0.006)
    WV = A.m_flat('#2f86c6', 0.08, 8, 'swimwave')
    pts = [(PX + 0.05, PY - 0.1 + i * 0.02, 0.4 + 0.022 * math.sin(i * 0.9)) for i in range(11)]
    bk(tube('swave', pts, [0.008] * len(pts), WV, res=1))
    bk(blob('swimmer', (PX + 0.05, PY + 0.02, 0.465), (0.006, 0.022, 0.022), A.m_flat('#e8463c', 0.08, 8, 'swimhead'), sub=0, seg=10))
    LB = AT.m_cloth('#fff3e2', '#e2524c', stripes=4.0, name='swimring', age=1.2)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.04, location=(PX - 0.045, PY, 0.24), rotation=(0, math.radians(90), 0), major_segments=28, minor_segments=10)
    t = bpy.context.object; t.name = 'buoy'; t.data.materials.append(LB)
    me = t.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = ((math.atan2(co.z, co.y) / (2 * math.pi) + 0.0625) % 1.0, 0)
    TW = AT.m_cloth('#36b5c9', '#fff3dc', stripes=6.0, name='swimtowel', age=1.1)
    towel_flat(1.42, -0.62, 0.0, 0.52, 0.3, -25, TW)
    FF = A.m_flat('#ffcf3a', 0.1, 8, 'flipflop'); STRP = A.m_flat('#2f86c6', 0.1, 8, 'flipstrap')
    for k, (x, y, yaw) in enumerate(((1.12, -0.86, 20), (1.2, -0.92, 35))):
        o = blob('flip', (x, y, 0.012), (0.045, 0.11, 0.012), FF, rot=(0, 0, yaw), sub=0, seg=12)
        bk(tube('strap', [(x - 0.03, y + 0.02, 0.022), (x, y + 0.06, 0.04), (x + 0.03, y + 0.02, 0.022)], [0.006] * 3, STRP, res=2))
    return 'havuz'


def towel_flat(cx, cy, z, Lx, Ly, yaw, m):
    """Yere serili havlu: hafif kırışık, kenarı kalkık, kalınlıklı (kapalı); grain u = enine (şerit yönü)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    a = math.radians(yaw); ca, sa = math.cos(a), math.sin(a)
    nx, ny = 10, 6; T = 0.01
    top = []; bot = []
    for i in range(nx + 1):
        rt = []; rb = []
        for j in range(ny + 1):
            u, v = i / nx, j / ny
            x = (u - 0.5) * Lx; y = (v - 0.5) * Ly
            h = 0.012 + 0.012 * math.sin(u * 7 + v * 2) * math.sin(v * 3.1) + 0.03 * max(0, u - 0.85) / 0.15
            X = cx + x * ca - y * sa; Y = cy + x * sa + y * ca
            rt.append(bm.verts.new((X, Y, z + h + T))); rb.append(bm.verts.new((X, Y, z + h)))
        top.append(rt); bot.append(rb)
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / nx, jj / ny)
            f = bm.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
            for lp, (ii, jj) in zip(f.loops, ((i, j + 1), (i + 1, j + 1), (i + 1, j), (i, j))): lp[uvl].uv = (ii / nx, jj / ny)
    for i in range(nx):
        for j in (0, ny):
            bm.faces.new((top[i][j], bot[i][j], bot[i + 1][j], top[i + 1][j]))
    for j in range(ny):
        for i in (0, nx):
            bm.faces.new((top[i][j], top[i][j + 1], bot[i][j + 1], bot[i][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = A.link_mesh('towel', bm, [m]); A.smooth(o)
    return o


DECIM = [(r'^(rock|rockout)$', 0.3), (r'^bowl$', 0.3), (r'^water$', 0.5), (r'^lush$', 0.5), (r'^(Icosphere|pebble)$', 0.35),
         (r'^(pet|fc|stem)$', 0.35), (r'^(lrail|rung|dpost|dbrace|lanepost|buoypost)$', 0.6), (r'^(floatie|buoy)$', 0.5),
         (r'^lanefloat$', 0.6), (r'^(flip|lily)$', 0.6)]
WEIGHTS = [(r'^water$', 1.0), (r'^bowl$', 0.2), (r'^rock$', 1.0), (r'^rockout$', 0.85), (r'^dive(_lo)?$', 1.6), (r'^(floatie|buoy)$', 1.6),
           (r'^sign(_lo)?$', 2.0), (r'^(lanefloat)$', 1.3), (r'^towel$', 1.4), (r'^(lrail|rung)$', 1.0), (r'^ropecore', 0.8),
           (r'^(lush|rosette|tuft|pet|stem|fc|plants)$', 0.5)]

if __name__ == '__main__':
    KK.main('b_swim', build, DECIM, WEIGHTS, budget=12000, tex=1024, ds_low=True, floor=-0.55)
