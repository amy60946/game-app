# Sörf kulübesi oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Eski c_surf (assets_town) 7 bin üçgene küresel sadeleşip yalnız renk + AO pişiyordu; sörf tahtaları düz şeritli, boya dökülmesi
# ve saz uçları eriyordu. Burada ayrıntılı taslak bld_kit hattıyla pişirilir. Taslak (eski yerleşim korunur, sınırlar değişmesin):
#   - kazıklar üstünde kulübe: güneşte solmuş turkuaz/krem boyalı yatay tahtalar (kenarlardan ve pul pul dökülen boya, tuz beneği),
#     kazık diplerinde kum yığıntısı ve ıslak koyu iz, kazık-döşeme bağlarında halat sargı;
#   - saz çatı: halka halka sarkan saz demetleri, saçakta tırtıklı kenar, çatıyı saran iki halat kuşak, tepe topuzu;
#   - sörf tahtaları (eski yer ve açı): solmuş taban rengi, ortada ahşap omurga çizgisi, her tahtada ayrı boyalı desen (çiçek /
#     şerit + güneş / zikzak dalga), mum lekesi, kenar vuruk izleri, altta yüzgeç; sol yanda tahtaların yaslandığı halat bağlı
#     sırık;
#   - önde dalga + güneş boyalı tabela (dökülmüş boya), saçaktan sarkan deniz kabuğu dizisi, tezgâhta hindistan cevizi kap ve
#     mum kalıbı, yan duvarda kurumaya asılmış çizgili havlu;
#   - kumda kabuklar, deniz yıldızı, karaya vurmuş gri dal parçası, palmiye filizi ve kumul otu (eski tohumlarla).
# Ölçü ve yön eski FBX ile aynı (bölge 'board', EnvFootprint 6,8 m yatay): orijin zemin, ön (tezgâh) −Y.
# Kullanım: python -I bld/b_surf.py -- <çıktı> [b_surf] [--draft <png> [--yaw Y]]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kiyi_kit as KK
from kiyi_kit import bpy, bmesh, V, A, AT, kit, rbox, cyl, blob, tube, bk, lo, overlay, L_streaks, L_sunbleach, L_chain, srgb, ramp, nodes_mat

NOG = (-9.0, -8.6)
SW, SD, SH, Z0 = 1.7, 1.3, 1.2, 0.25


def L_sanddust(amt=0.45):
    """Yukarı bakan yüzlerde kum tozu (açık bej lekeler; basamak, döşeme)."""
    def fn(G, col):
        up = G.rng(G.nz(), 0.5, 0.9)
        m = G.math('MULTIPLY', up, G.rng(G.noise(G.obj(), 7.0, 4), 0.5, 0.66, 0, amt))
        return G.mix(m, col, '#e8d3a2')
    return fn


def L_footwet(z_top=0.18, amt=0.6):
    """Kazık dibi: kumla temas eden ıslak koyu bant + kum lekesi (nesne Z = dünya Z: eğriden dönen kazık)."""
    def fn(G, col):
        o = G.obj(); z = G.z()
        zn = G.math('ADD', z, G.math('MULTIPLY', G.math('SUBTRACT', G.noise(o, 6.0, 4), 0.5), 0.08))
        col = G.mix(G.rng(zn, z_top, z_top - 0.08, 0, amt), col, '#8a7c66', 'MULTIPLY')
        col = G.mix(G.math('MULTIPLY', G.rng(zn, 0.06, 0.0), G.rng(G.noise(o, 12, 3), 0.4, 0.6)), col, '#dcc28e')
        return col
    return fn


def m_board(c1, c2, motif, name):
    """Sörf tahtası boyası (grain uv: u enine 0..1, v boyuna metre): solmuş taban, ahşap omurga çizgisi, desen, mum lekesi, vuruk.
    motif: 'flower' (burunda çiçek + kuyrukta bant), 'sun' (üç şerit + güneş), 'wave' (zikzak dalga + burun ucu)."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links
        uv = uv_node(nt); sp = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sp.inputs[0])
        u, v = sp.outputs['X'], sp.outputs['Y']; o = G.obj()
        du = G.math('SUBTRACT', u, 0.5)
        col = G.mix(G.rng(G.noise(o, 1.3, 3), 0.3, 0.75), c1, A._shade(c1, 1.12))
        if motif == 'flower':
            # burunda büyük beş yapraklı çiçek (v ≈ 0.45), kuyrukta krem bant
            cx, cy = 0.0, -0.1
            dvv = G.math('SUBTRACT', v, cy)
            r = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', G.math('MULTIPLY', du, 0.42), G.math('MULTIPLY', du, 0.42)), G.math('MULTIPLY', dvv, dvv)))
            ang = G.math('ARCTAN2', dvv, G.math('MULTIPLY', du, 0.42))
            petal = G.math('ADD', 0.075, G.math('MULTIPLY', G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', ang, 2.5))), 0.05))
            fl = G.rng(G.math('SUBTRACT', r, petal), 0.006, -0.004)
            col = G.mix(fl, col, c2)
            col = G.mix(G.rng(r, 0.035, 0.025), col, '#f6c445')
            band = G.math('MULTIPLY', G.rng(v, -0.5, -0.48), G.rng(v, -0.4, -0.42))
            col = G.mix(band, col, c2)
        elif motif == 'sun':
            for vc in (-0.38, -0.3, -0.22):
                band = G.math('MULTIPLY', G.rng(v, vc - 0.025, vc - 0.018), G.rng(v, vc + 0.025, vc + 0.018))
                col = G.mix(band, col, c2)
            dvv = G.math('SUBTRACT', v, 0.32)
            r = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', G.math('MULTIPLY', du, 0.4), G.math('MULTIPLY', du, 0.4)), G.math('MULTIPLY', dvv, dvv)))
            ang = G.math('ARCTAN2', dvv, G.math('MULTIPLY', du, 0.4))
            ray = G.math('MULTIPLY', G.rng(G.math('SINE', G.math('MULTIPLY', ang, 8.0)), 0.3, 0.6), G.rng(r, 0.1, 0.09))
            col = G.mix(G.math('MAXIMUM', G.rng(r, 0.062, 0.055), ray), col, '#ffd24a')
        else:
            zz = G.math('ADD', G.math('MULTIPLY', G.math('ABSOLUTE', G.math('SUBTRACT', G.math('FRACT', G.math('MULTIPLY', u, 3.0)), 0.5)), 0.12), -0.05)
            wave = G.math('MULTIPLY', G.rng(G.math('SUBTRACT', v, zz), -0.03, -0.022), G.rng(G.math('SUBTRACT', v, zz), 0.03, 0.022))
            col = G.mix(wave, col, c2)
            col = G.mix(G.rng(v, 0.6, 0.64), col, c2)
        # omurga çizgisi (ince koyu ahşap)
        col = G.mix(G.rng(G.math('ABSOLUTE', du), 0.012, 0.006), col, '#7a5432')
        # mum lekesi (orta bölgede soluk, pürüzlü) ve güneş solması
        wax = G.math('MULTIPLY', G.rng(G.math('ABSOLUTE', v), 0.42, 0.2), G.rng(G.noise(o, 9.0, 5), 0.5, 0.62, 0, 0.35))
        col = G.mix(wax, col, '#fbf3df')
        col = G.mix(G.rng(G.noise(o, 1.0, 3), 0.55, 0.75, 0, 0.25), col, '#fff6e6')
        # kenar vuruğu: kenarlarda seyrek koyu/açık benek
        ding = G.math('MULTIPLY', G.edges(0.52, 0.6), G.rng(G.noise(o, 18.0, 2), 0.62, 0.7))
        col = G.mix(G.math('MULTIPLY', ding, 0.6), col, '#c9b48e')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


from kit import uv_node


def surfboard(loc, Lb, wdt, c1, c2, rot, name, motif):
    """assets_town.surfboard biçimi (aynı yer/boy/açı) + yeni boya + kuyrukta yüzgeç."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=14, radius=1)
    o = bpy.context.object; o.name = 'board'; o.scale = (wdt / 2, Lb / 2, 0.035)
    bpy.ops.object.transform_apply(scale=True)
    for vv in o.data.vertices:
        t = vv.co.y / (Lb / 2)
        vv.co.x *= (1 - 0.35 * max(0, t)) * (1 - 0.15 * max(0, -t))
    o.data.materials.append(m_board(c1, c2, motif, name)); A.smooth(o)
    me = o.data; lay = me.uv_layers.new(name='grain')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = (co.x / wdt * 0.9 + 0.5, co.y / (Lb / 2) * 0.5 * (Lb / 1.6) * 1.0)
    fin = AT.prism('fin', [(-0.07, 0.0), (0.03, 0.0), (-0.02, -0.11), (-0.06, -0.1)], 0.012, A.m_flat('#2b3a4a', 0.15, 8, 'fin'), bevel=0.004)
    fin.rotation_euler = (0, 0, math.radians(90)); fin.location = (0, -Lb / 2 * 0.78, -0.028)
    fin.parent = o
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.update()
    mw = fin.matrix_world.copy(); fin.parent = None; fin.matrix_world = mw
    return o


def build():
    kit.reset(); random.seed(21)
    W = [overlay(A.m_wood(c, f'surfw{i}', paint=p, age=1.5, grime=NOG), L_streaks('#f4efe4', 0.25, scale=20), f'surfw{i}_k')
         for i, (c, p) in enumerate((('#b98a5a', '#6cc8d2'), ('#b98a5a', '#f4e2bc')))]
    DK = overlay(A.m_wood('#7a5232', 'surfdark', age=1.3, grime=NOG), L_footwet(0.2), 'surfdark_k')
    FL = overlay(A.m_wood('#c99a66', 'surffloor', age=1.3, grime=NOG), L_chain(L_sunbleach(0.25), L_sanddust(0.5)), 'surffloor_k')
    RP = AT.m_rope('#cdae78', 'surfrope')
    for x in (-SW / 2, SW / 2):
        for y in (-SD / 2, SD / 2):
            sd = int(x * 10 + y * 7)
            o = tube('stilt', [(x, y, -0.05), (x + 0.01 * math.sin(sd), y, (Z0 + SH) / 2), (x, y, Z0 + SH)], [0.07, 0.066, 0.06], DK, res=4)
            o.data.bevel_resolution = 2
            KK.rope_wrap((x, y, 0), 0.075, Z0 - 0.09, Z0 - 0.02, 1.4, RP, thick=0.012, seed=sd, sides=6)
            KK.endgrain_cap(x, y, Z0 + SH, 0.06, seed=sd, lichen=False)
            sand_mound(x, y, 0.2, sd)
    for k in range(8):
        KK.plank2('floor', (0, -SD / 2 - 0.2 + k * 0.2, Z0), (SW + 0.2, 0.18, 0.05), FL, seed=k + 3)
        for xx in (-SW / 2, 0, SW / 2):
            KK.nail_top((xx + 0.05, -SD / 2 - 0.2 + k * 0.2, Z0 + 0.025))
    rows = int(SH / 0.16) - 1                 # en üst sıra yok: köşeleri saz saçağın içinden dışarı taşıyordu (krem 'bayrak')
    for r in range(rows):
        z = Z0 + 0.1 + r * 0.16
        m = W[(r // 2) % 2]
        KK.plank2('back', (0, SD / 2, z), (SW, 0.05, 0.15), m, seed=r)
        for sx in (-1, 1): KK.plank2('side', (sx * SW / 2, 0, z), (0.05, SD, 0.15), m, seed=r + sx * 20)
        if z < Z0 + 0.55 or z > Z0 + 1.05:
            KK.plank2('front', (0, -SD / 2, z), (SW, 0.05, 0.15), m, seed=r + 40)
    KK.plank2('counter', (0, -SD / 2 - 0.08, Z0 + 0.55), (SW + 0.1, 0.24, 0.05), FL, seed=9)
    for xx in (-0.6, 0.6):
        AT.prism('bracket', [(0.0, 0.0), (0.16, 0.0), (0.0, -0.16)], 0.04, DK, loc=(xx, -SD / 2 - 0.035, Z0 + 0.525), rot=(0, 0, -90), bevel=0.006)
    # saz çatı + iki halat kuşak + tepe topuzu
    STRAW = overlay(A.m_leaf('#9a6e2e', '#c49a4c', '#e2bf78', '#ecd59a', 'straw'), L_thatchage(), 'straw_k')
    AT.thatch(0, 0, Z0 + SH + 0.02, Z0 + SH + 0.62, 1.2, 0.2, 5, layers=7, m=STRAW)
    for zz, rr in ((Z0 + SH + 0.32, 0.6), (Z0 + SH + 0.5, 0.36)):
        pts = [(math.cos(t / 20 * 2 * math.pi) * rr, math.sin(t / 20 * 2 * math.pi) * rr, zz + 0.015 * math.sin(t * 1.3)) for t in range(21)]
        KK.rope(pts, 0.016, RP, sides=6)
    blob('knot', (0, 0, Z0 + SH + 0.68), (0.12, 0.12, 0.1), STRAW, sub=0, seg=16)
    # sörf tahtaları (eski yer ve açılar) + sol yanda yaslandıkları sırık
    surfboard((-1.05, -0.95, 0.82), 1.6, 0.42, '#f27a5a', '#fff1d6', (16, 0, 18), 'sb1', 'flower')
    surfboard((-1.2, -0.3, 0.8), 1.6, 0.4, '#2fb2c0', '#fff1d6', (12, -10, 6), 'sb2', 'sun')
    surfboard((1.15, -0.85, 0.78), 1.55, 0.4, '#ffd04a', '#f2709e', (16, 6, -16), 'sb3', 'wave')
    tube('rackpole', [(-SW / 2 - 0.08, -SD / 2 - 0.02, 1.22), (-SW / 2 - 0.08, SD / 2 + 0.02, 1.22)], [0.03, 0.03], DK, res=2)
    for y in (-SD / 2, SD / 2):
        KK.rope_wrap((-SW / 2 - 0.04, y, 0), 0.08, 1.17, 1.27, 1.6, RP, thick=0.012, seed=y * 3, sides=6)
    # tabela: saçağın altında görünmüyordu → önde kumda dikili direkli tabela (dalga + güneş boyalı, dökülmüş boya, halat bağlı)
    SB = overlay(A.m_wood('#b98a5a', 'surfsign', paint='#2f8a8a', age=1.6, grime=NOG), L_sunbleach(0.15), 'surfsign_k')
    SX, SY, SZ = 0.3, -1.3, 0.6
    o = tube('signpost', [(SX - 0.27, SY + 0.03, -0.05), (SX - 0.27, SY + 0.03, SZ + 0.2)], [0.032, 0.028], DK, res=2); o.data.bevel_resolution = 1
    o = tube('signpost', [(SX + 0.27, SY + 0.03, -0.05), (SX + 0.27, SY + 0.03, SZ + 0.2)], [0.032, 0.028], DK, res=2); o.data.bevel_resolution = 1
    KK.plank2('sign', (SX, SY, SZ), (0.7, 0.035, 0.26), SB, seed=12, bevel=0.01)
    for xx in (SX - 0.27, SX + 0.27):
        KK.rope_wrap((xx, SY + 0.03, 0), 0.04, SZ + 0.05, SZ + 0.11, 1.5, RP, thick=0.01, seed=xx * 5, sides=4)
        sand_mound(xx, SY + 0.03, 0.09, int(xx * 30))
    WV = A.m_flat('#fff6e6', 0.05, 8, 'waveic')
    pts = [(-0.22 + i * 0.022, -0.045 + 0.055 * math.sin(i * 0.42) + (0.055 if i > 16 else 0) * math.sin((i - 16) * 0.8)) for i in range(21)]
    o = tube('wave', [(SX - 0.05 + x, SY - 0.024, SZ + z) for x, z in pts], [0.016] * len(pts), WV, res=1); o.data.bevel_resolution = 1
    blob('sunic', (SX + 0.22, SY - 0.022, SZ + 0.04), (0.05, 0.012, 0.05), A.m_flat('#ffc93a', 0.08, 8, 'sunic'), sub=0, seg=12)
    for k in range(8):
        a = k * math.pi / 4
        bk(rbox('sunray', (SX + 0.22 + math.cos(a) * 0.075, SY - 0.02, SZ + 0.04 + math.sin(a) * 0.075), (0.026, 0.006, 0.011), A.m_flat('#ffc93a', 0.08, 8, 'sunic'), rot=(0, -math.degrees(a), 0), bevel=0))
    SHL = [A.m_flat('#f7d9c4', 0.12, 10, 'shellA'), A.m_flat('#f4b9a6', 0.12, 10, 'shellB'), A.m_flat('#fff2e2', 0.1, 10, 'shellC')]
    for k, x in enumerate((SX - 0.27, SX + 0.27)):                       # direk başlarında birer kabuk
        shell((x, SY - 0.01, SZ + 0.24), 0.03, SHL[k], 40 + k)
    # tezgâhta hindistan cevizi kap + mum kalıbı; yan duvarda havlu
    blob('cup', (0.45, -SD / 2 - 0.1, Z0 + 0.62), (0.06, 0.06, 0.05), AT.m_fruit('coconut'), sub=0, seg=14)
    cyl('cupin', (0.45, -SD / 2 - 0.1, Z0 + 0.665), 0.045, 0.006, A.m_flat('#f3ead6', 0.1, 6, 'coconutin'), verts=12, bevel=0)
    tube('straw', [(0.46, -SD / 2 - 0.1, Z0 + 0.64), (0.5, -SD / 2 - 0.13, Z0 + 0.76)], [0.006, 0.006], A.m_flat('#f2709e', 0.05, 6, 'strawp'), res=1)
    rbox('wax', (-0.4, -SD / 2 - 0.12, Z0 + 0.6), (0.12, 0.07, 0.05), A.m_flat('#f4e9c8', 0.15, 14, 'waxb'), rot=(0, 0, 12), bevel=0.012, seg=1)
    TW = AT.m_cloth('#ff8c5a', '#fff3dc', stripes=7.0, name='towel', age=1.2)
    towel(SW / 2 + 0.03, -0.05, Z0 + 0.98, TW)
    # kum: kabuklar, deniz yıldızı, karaya vurmuş dal, palmiye filizi ve kumul otu (eski tohumlar)
    for k, (x, y) in enumerate(((0.6, -1.15), (-0.4, -1.2), (1.3, 0.6))):
        shell((x, y, 0.012), 0.05, SHL[k % 3], 10 + k, flat=True)
    ST = A.m_flat('#f4844e', 0.18, 12, 'starfish')
    for j in range(5):
        b_ = j * 2 * math.pi / 5
        blob('star', (-0.05 + math.cos(b_) * 0.05, -1.05 + math.sin(b_) * 0.05, 0.012), (0.06, 0.012, 0.016), ST, rot=(0, 0, math.degrees(b_)), sub=0, seg=8)
    blob('star', (-0.05, -1.05, 0.016), (0.035, 0.035, 0.016), ST, sub=0, seg=10)
    DW = A.m_wood('#a59d90', 'driftwood', age=1.4, grime=NOG)
    tube('drift', [(0.95, 0.85, 0.03), (1.15, 0.95, 0.05), (1.38, 1.0, 0.035)], [0.045, 0.04, 0.025], DW, res=3)
    tube('drift', [(1.1, 0.93, 0.05), (1.18, 1.08, 0.07)], [0.02, 0.012], DW, res=2)
    LEAF = A.m_leaf('#3f9a3a', '#6cc94c', '#b5e26a', '#d8f08a', 'palmling')
    def sprout(bm):
        out = []
        for k in range(7):
            a = k * 0.9; d = V((math.cos(a), math.sin(a), 0.7)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
            for f in A.blade(bm, V((1.35, 0.9, 0.05)), d, side, 0.5, 0.11, 0.9, segs=4, lift=0.2): out.append((f, 0))
        return out
    A.mesh_from_blades('sprout', sprout, [LEAF])
    G1 = A.m_leaf('#5f9a3d', '#86b85a', '#c7dd8a', '#dbe9a8', 'dunegrass')
    for k, (x, y) in enumerate(((-1.3, 0.85), (1.2, -1.0), (-0.9, -1.15))):
        A.mesh_from_blades('tuft', A.tufts((x, y, 0.0), 0.14, 2, 50 + k, h=(0.22, 0.38)), [G1])
    return 'sörf'


def L_thatchage(amt=0.3):
    """Saz yaşlanması: demet demet gri-kahve solmuş saz ve seyrek koyu nem izi (tek tip sarı saz yerine; geniş leke değil, ince)."""
    def fn(G, col):
        o = G.obj()
        col = G.mix(G.rng(G.noise(G.mapping(o, (6, 6, 2)), 3.0, 3), 0.52, 0.66, 0, amt), col, '#a08a62')
        col = G.mix(G.rng(G.noise(o, 12.0, 4), 0.62, 0.72, 0, 0.22), col, '#9a8a6e', 'MULTIPLY')
        return col
    return fn


def sand_mound(x, y, r, seed):
    """Kazık dibinde rüzgârın yığdığı kum (basık, kenarı yumuşak)."""
    o = KK.lumpy('sand', (x, y, -0.02), (r, r * 0.85, 0.07), AT.m_sand('surfsand', '#e6cc94'), seed=seed, folds=0.18, sub=2)
    return o


def shell(p, s, m, seed, flat=False):
    """Deniz tarağı kabuğu: yelpaze kaburgalı yarım disk (yalnız pişir değil: küçük ama renkli siluet)."""
    R = random.Random(seed)
    for j in range(5):
        b_ = math.radians(-50 + j * 25)
        if flat:
            blob('shell', (p[0] + math.sin(b_) * s * 0.8, p[1] + math.cos(b_) * s * 0.8, p[2]), (s * 0.36, s, s * 0.24), m, rot=(0, 0, -math.degrees(b_)), sub=0, seg=6)
        else:
            blob('shell', (p[0] + math.sin(b_) * s * 0.8, p[1], p[2] + math.cos(b_) * s * 0.8), (s * 0.36, s * 0.24, s), m, rot=(0, math.degrees(b_), 0), sub=0, seg=6)


def towel(x, y, z, m):
    """Yan duvarın üst tahtasına asılmış çizgili havlu: iki kat sarkan kumaş (kalınlıklı, kapalı)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    W_, Hh, T = 0.42, 0.5, 0.012
    rows = []
    for i in range(9):
        t = i / 8; zz = z - Hh * t
        row = []
        for j in range(7):
            s = j / 6; yy = y - W_ / 2 + W_ * s
            bulge = 0.02 * math.sin(s * math.pi) * t + 0.01 * math.sin(s * 9 + t * 4)
            row.append((V((x + bulge, yy, zz)), V((x + bulge + T, yy, zz)), (s, t)))
        rows.append(row)
    vin = [[bm.verts.new(a) for (a, b, _) in row] for row in rows]
    vout = [[bm.verts.new(b) for (a, b, _) in row] for row in rows]
    for i in range(8):
        for j in range(6):
            for vv, rev in ((vout, False), (vin, True)):
                q = [vv[i][j], vv[i][j + 1], vv[i + 1][j + 1], vv[i + 1][j]]
                f = bm.faces.new(q[::-1] if rev else q)
                for lp, (ii, jj) in zip(f.loops, ([(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)][::-1] if rev else [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)])):
                    lp[uvl].uv = (rows[ii][jj][2][0], rows[ii][jj][2][1])
    # kenar şeritleri (kapalı kabuk)
    for i in range(8):
        for j in (0, 6):
            f = bm.faces.new((vin[i][j], vout[i][j], vout[i + 1][j], vin[i + 1][j]))
    for j in range(6):
        for i in (0, 8):
            bm.faces.new((vin[i][j], vin[i][j + 1], vout[i][j + 1], vout[i][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = A.link_mesh('towel', bm, [m]); A.smooth(o)
    return o


DECIM = [(r'^thatch$', 0.75), (r'^ropecore', 1.0), (r'^(stilt)$', 0.6), (r'^sand$', 0.4), (r'^board$', 0.6), (r'^(knot|cup)$', 0.5),
         (r'^(shell|star)$', 0.5), (r'^(sprout|tuft)$', 1.0), (r'^(drift|wave|rackpole)$', 0.6)]
WEIGHTS = [(r'^board$', 1.7), (r'^fin$', 0.8), (r'^(sign_lo|wave|sunic|signpost)$', 1.8), (r'^(front|side|back)_lo$', 1.15), (r'^(counter|cup|cupin|wax|straw)', 1.3),
           (r'^towel$', 1.4), (r'^thatch$', 0.75), (r'^knot$', 0.8), (r'^floor', 0.9), (r'^stilt$', 0.9), (r'^sand$', 0.5),
           (r'^(shell|star)$', 1.2), (r'^ropecore', 0.8), (r'^(sprout|tuft)$', 0.8), (r'^drift$', 1.0)]

if __name__ == '__main__':
    KK.main('b_surf', build, DECIM, WEIGHTS, budget=12000, tex=1024, ds_low=True, floor=0.03)
