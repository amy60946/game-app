# Deniz feneri oyun modeli v2 (24 Ekim 2026; kullanıcı: "bütün yapılar ayrıntılı ve ada hayatına uygun eskitmeli olsun").
# Eski c_lighthouse (assets_town) düz bantlı bir koni, iki küçük cam damla ve renk + AO'dan ibaretti; 6 bin üçgene küresel
# sadeleşince pencere çerçevesi, korkuluk ve kubbe ayrıntısı eriyordu. Burada ayrıntılı taslak bld_kit hattıyla pişirilir:
#   - kule boyası: kırmızı-krem bantlar (fırça izli kenar), güneşte solmuş kırmızı, pul pul dökülen boya → altta krem sıva, büyük
#     dökülmelerde taş örgü (normal haritasında çukur); balkondan aşağı tuz ve pas akıntıları, pencere altlarında kir izi, dipte
#     toprak kiri + yosun;
#   - taş çerçeveli pencereler (eşik, lento, kanatlı solgun panjur, camda yansıma), kemerli taş söveli ahşap kapı (soluk turkuaz,
#     dökülen boya, demir menteşe kayışları, halka tokmak), önünde taş basamak ve basamak taşları;
#   - balkon: altında taş konsol dizisi, tahta döşeme, paslı demir korkuluk (iki kuşak), korkuluk dibinden pas izleri;
#   - fener odası: kırmızı kaide halkası, Fresnel mercek bantlı parlak cam (m_glow gibi sabit sıcak ışık), demir kayıtlar, kaburgalı
#     kırmızı kubbe, top + balıklı rüzgâr gülü;
#   - taş temel: likenli (sarı-yeşil benek) kaba taşlar, dipte ot/çiçek (eski yerleşim: sınırlar değişmesin), yaslanmış eski çapa.
# Ölçü ve yön eski FBX ile aynı (EnvFootprint 5,5 m): orijin zemin, kapı −Y, kule ekseni z.
# Kullanım: python -I bld/b_lighthouse.py -- <çıktı> [b_lighthouse] [--draft <png> [--yaw Y]]
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kiyi_kit as KK
from kiyi_kit import bpy, V, A, AT, kit, rbox, cyl, blob, tube, bk, lo, overlay, L_streaks, L_chain, srgb, ramp, nodes_mat

H = 3.6
NOG = (-9.0, -8.6)


def rad(z):
    t = (z - 0.5) / (H - 0.5)
    return 0.7 - 0.24 * t + 0.015 * math.sin(t * 9)


WINDOWS = ((1.85, 200.0), (2.75, 30.0), (2.3, 302.0))     # eski iki pencere + kapının sağ üstünde merdiven penceresi (ön görünüşte)


def m_tower():
    """Kule boyası: bantlar, solma, dökülme (sıva / taş örgü), tuz-pas akıntısı, pencere altı kir izi, dip kiri. Bump: dökülen yer çukur."""
    def b(nt, bsdf):
        G = A._G(nt); n = nt.nodes; l = nt.links
        o = G.obj(); z = G.z()
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
        nz = G.noise(o, 5.0, 6)
        zb = G.math('ADD', z, G.math('MULTIPLY', G.math('SUBTRACT', nz, 0.5), 0.06))
        ph = G.math('FRACT', G.math('DIVIDE', G.math('SUBTRACT', zb, 0.5), 0.9))
        red = G.math('MULTIPLY', G.rng(ph, 0.0, 0.02), G.rng(ph, 0.5, 0.48))
        cream = G.mix(G.rng(G.noise(o, 1.3, 4), 0.3, 0.75), '#efe2c8', '#f8efdc')
        redc = G.mix(G.rng(G.noise(o, 1.1, 4), 0.35, 0.8), '#cf4038', '#e2625a')          # güneşte solmuş lekeler
        col = G.mix(red, cream, redc)
        col = G.mix(0.12, col, G.noise(G.mapping(o, (3, 3, 40)), 2.0, 3, out='Color'), 'OVERLAY')   # yatay fırça izi
        # dökülme: gürültü (aşağıda ve tepeye yakın daha çok)
        bias = G.math('ADD', G.rng(z, 1.3, 0.55, 0, 0.08), G.rng(z, 3.0, 3.55, 0, 0.05))
        ch = G.math('ADD', G.noise(o, 3.2, 8, 0.62), bias)
        chip = G.rng(ch, 0.638, 0.658)                                                     # 1 = boya yok
        rim = G.math('MULTIPLY', G.rng(ch, 0.618, 0.638), G.rng(ch, 0.672, 0.655))
        plaster = G.mix(G.rng(G.noise(o, 8, 4), 0.3, 0.7), '#d6c8ad', '#e4d8c0')
        # büyük dökülmede taş örgü (yatay sıralı bloklar: bükülmüş voronoi)
        deep = G.rng(ch, 0.69, 0.71)
        blk = G.vor(G.mapping(o, (5.5, 5.5, 10.0)), 1.0, 'DISTANCE_TO_EDGE')
        mortar = G.rng(blk, 0.06, 0.02)
        stone = G.mix(G.rng(G.noise(o, 6, 4), 0.3, 0.7), '#9a9184', '#b3a998')
        stone = G.mix(mortar, stone, '#cfc6b3')
        under = G.mix(deep, plaster, stone)
        col = G.mix(chip, col, under)
        col = G.mix(G.math('MULTIPLY', rim, 0.45), col, '#6e5a48', 'MULTIPLY')
        # balkondan aşağı tuz (açık) ve pas (turuncu-kahve) akıntıları
        st1 = G.rng(G.noise(G.mapping(o, (16, 16, 1.1)), 1.0, 3), 0.56, 0.68)
        fall = G.math('MULTIPLY', G.rng(z, H - 1.1, H - 0.05), G.rng(z, H + 0.01, H - 0.04))
        col = G.mix(G.math('MULTIPLY', G.math('MULTIPLY', st1, fall), 0.62), col, '#f6f1e6')
        st2 = G.rng(G.noise(G.mapping(o, (30, 30, 1.6)), 4.0, 3), 0.6, 0.7)
        fall2 = G.math('MULTIPLY', G.rng(z, H - 0.75, H - 0.04), G.rng(z, H + 0.01, H - 0.04))
        col = G.mix(G.math('MULTIPLY', G.math('MULTIPLY', st2, fall2), 0.8), col, '#9c5a34')
        # pencere altı kir/tuz izi (pencere yönünde dar, aşağı akan)
        ln = n.new('ShaderNodeVectorMath'); ln.operation = 'NORMALIZE'
        cmb = n.new('ShaderNodeCombineXYZ'); l.new(sp.outputs['X'], cmb.inputs[0]); l.new(sp.outputs['Y'], cmb.inputs[1]); l.new(cmb.outputs[0], ln.inputs[0])
        for (zw, aw) in WINDOWS:
            dot = n.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
            l.new(ln.outputs[0], dot.inputs[0]); dot.inputs[1].default_value = (math.cos(math.radians(aw)), math.sin(math.radians(aw)), 0)
            m = G.math('MULTIPLY', G.rng(dot.outputs['Value'], 0.978, 0.992), G.rng(z, zw - 0.75, zw - 0.2))
            m = G.math('MULTIPLY', m, G.rng(z, zw - 0.12, zw - 0.18))
            m = G.math('MULTIPLY', m, G.rng(G.noise(G.mapping(o, (30, 30, 1.5)), 2.0, 3), 0.45, 0.6))
            col = G.mix(G.math('MULTIPLY', m, 0.55), col, '#7b6d5e', 'MULTIPLY')
        # dip kiri + yosun
        zn = G.math('ADD', z, G.math('MULTIPLY', G.noise(o, 5, 6), 0.25))
        col = G.mix(G.rng(zn, 1.05, 0.62, 0, 0.5), col, '#8a7656', 'MULTIPLY')
        moss = G.math('MULTIPLY', G.rng(zn, 0.82, 0.6, 0, 0.75), G.rng(G.noise(o, 9, 4), 0.48, 0.62))
        col = G.mix(moss, col, '#5e8a34')
        l.new(col, bsdf.inputs['Base Color'])
        # kabartma: dökülen boya ve taş derzi çukur
        h = G.math('SUBTRACT', 1.0, G.math('ADD', G.math('MULTIPLY', chip, 0.5), G.math('MULTIPLY', G.math('MULTIPLY', deep, mortar), 0.6)))
        bu = n.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = 0.8; bu.inputs['Distance'].default_value = 0.012
        l.new(h, bu.inputs['Height']); l.new(bu.outputs['Normal'], bsdf.inputs['Normal'])
    return nodes_mat('lhtower', b)


def m_lens():
    """Fener camı: sabit sıcak ışık; yatay Fresnel mercek bantları (açık/sarı), ortada parlak kuşak (pişirmede sabit renk)."""
    def b(nt, bsdf):
        G = A._G(nt); z = G.z()
        bands = G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', z, 2 * math.pi / 0.07)))
        col = G.mix(G.rng(bands, 0.2, 0.9), '#ffcf52', '#fff1b0')
        mid = G.math('MULTIPLY', G.rng(z, H + 0.25, H + 0.42), G.rng(z, H + 0.62, H + 0.46))
        col = G.mix(G.math('MULTIPLY', mid, 0.6), col, '#fffbe6')
        edge = G.math('ADD', G.rng(z, H + 0.27, H + 0.21, 0, 1), G.rng(z, H + 0.6, H + 0.67, 0, 1))
        col = G.mix(G.math('MULTIPLY', edge, 0.55), col, '#f2a240')
        nt.links.new(col, bsdf.inputs['Base Color'])
    return nodes_mat('lhlens', b)


def L_lichen(amt=0.6):
    """Taşta liken: sarı-yeşil ve gri-yeşil benek öbekleri (voronoi hücresi + seyrek gürültü kapısı)."""
    def fn(G, col):
        o = G.obj()
        cell = G.rng(G.vor(o, 11.0), 0.22, 0.1)
        gate = G.rng(G.noise(o, 2.4, 3), 0.5, 0.62)
        m = G.math('MULTIPLY', cell, gate)
        tone = G.mix(G.rng(G.noise(o, 4.0, 2), 0.4, 0.6), '#c9bf62', '#a7b47e')
        return G.mix(G.math('MULTIPLY', m, amt), col, tone)
    return fn


def on_tower(a_deg, z, out=0.0):
    """Kule yüzeyinde nokta ve dışa normal (a: derece, z)."""
    a = math.radians(a_deg); r = rad(z) + out
    return V((math.cos(a) * r, math.sin(a) * r, z)), V((math.cos(a), math.sin(a), 0))


def window(z, a_deg, STONE, GLASS, SH, I, seed):
    """Taş çerçeveli pencere: eşik (çıkıntılı), lento, iki söve, koyu cam + parlama, haç kayıt, iki solgun panjur (biri aralık)."""
    p, n = on_tower(a_deg, z); yaw = a_deg - 90.0
    t = V((-n.y, n.x, 0))
    W, Hh = 0.17, 0.25
    def P(dx, dz, dn): return tuple(p + t * dx + V((0, 0, dz)) + n * dn)
    rbox('wglass', P(0, 0, 0.012), (W, 0.03, Hh), GLASS, rot=(0, 0, yaw), bevel=0)
    rbox('wsill', P(0, -Hh / 2 - 0.035, 0.035), (W + 0.12, 0.09, 0.045), STONE, rot=(0, 0, yaw), bevel=0.01, seg=1)
    rbox('wlintel', P(0, Hh / 2 + 0.035, 0.028), (W + 0.1, 0.07, 0.06), STONE, rot=(0, 0, yaw), bevel=0.01, seg=1)
    for s in (-1, 1):
        rbox('wjamb', P(s * (W / 2 + 0.03), 0, 0.026), (0.055, 0.065, Hh + 0.02), STONE, rot=(0, 0, yaw), bevel=0.008, seg=1)
    rbox('wbar', P(0, 0, 0.03), (0.014, 0.01, Hh), I, rot=(0, 0, yaw), bevel=0)
    rbox('wbar', P(0, 0.02, 0.03), (W, 0.01, 0.014), I, rot=(0, 0, yaw), bevel=0)
    bk(rbox('wshine', P(-0.035, 0.03, 0.028), (0.03, 0.004, 0.12), A.m_flat('#9cc0de', 0.1, 6, 'wshine'), rot=(0, -28, yaw), bevel=0))
    # panjurlar: sol kapalıya yakın (duvara açık), sağ aralık
    for s, ang in ((-1, 70.0), (1, 25.0)):
        hinge = p + t * (s * (W / 2 + 0.06)) + n * 0.05
        dirv = (t * s) * math.cos(math.radians(ang)) + n * math.sin(math.radians(ang))
        c = hinge + dirv * 0.05
        yy = math.degrees(math.atan2(dirv.y, dirv.x))
        KK.plank2('shutter', tuple(c), (0.1, 0.018, Hh + 0.02), SH, rot=(0, 0, yy), seed=seed + s, amt=0.004, bevel=0.005)
        for dz in (-0.08, 0.08):
            bk(rbox('shinge', tuple(hinge + dirv * 0.045 + V((0, 0, dz))), (0.08, 0.022, 0.016), I, rot=(0, 0, yy), bevel=0.003))


def build():
    kit.reset(); random.seed(7)
    STN = overlay(A.m_rock(), L_lichen(0.65), 'lhrock')
    SOFT = overlay(A.m_rock(moss_th=(1.15, 1.4), warm=('#958a7c', '#aaa092', '#c2b8a6'), name='lhstone'), L_lichen(0.35), 'lhstone_k')
    STEP = overlay(A.m_rock(moss_th=(1.42, 1.7), warm=('#958a7c', '#aaa092', '#c2b8a6'), name='lhstep'), L_lichen(0.25), 'lhstep_k')
    I = AT.m_metal('#3e3b46', name='lhiron')
    # ---- taş temel (eski profil) + iki sıra kabarık taş
    prof_base = [(0.001, 0.0), (0.9, 0.0), (0.92, 0.18), (0.88, 0.42), (0.76, 0.5), (0.001, 0.5)]
    AT.lathe('base', prof_base, STN, segs=24, noise_amt=0.06)
    for row, z in enumerate((0.1, 0.3)):
        for k in range(12):
            a = k * 2 * math.pi / 12 + row * 0.26
            r = 0.9 if row == 0 else 0.84
            o = A.pebble((math.cos(a) * r, math.sin(a) * r, z), 0.16, STN, k + row * 20)
            o.scale = (1.0, 0.8, 0.85); o.rotation_euler = (0, 0, a); o.name = 'bstone'
    # ---- kule
    prof = [(rad(0.5 + i / 16 * (H - 0.5)), 0.5 + i / 16 * (H - 0.5)) for i in range(17)]
    AT.lathe('tower', [(0.001, 0.5)] + prof + [(0.001, H)], m_tower(), segs=32, noise_amt=0.01, seed=3)
    # ---- kapı: taş kemer + ahşap kanat (soluk turkuaz) + demir menteşe + halka
    DR = A.m_wood('#b98a5a', 'lhdoor', paint='#3d9a96', age=1.5, grime=NOG)
    yd = -rad(0.85)
    for k in range(4):
        KK.plank2('door', (-0.135 + k * 0.09, yd - 0.012, 0.86), (0.085, 0.05, 0.66), DR, seed=k + 3, amt=0.004, bevel=0.008)
    AT.prism('doortop', [(-0.18 + 0.36 * i / 10, 0.0) for i in range(11)][::-1] + [(0.18 * math.cos(t), 0.12 * math.sin(t)) for t in [j / 10 * math.pi for j in range(11)]],
             0.05, DR, loc=(0, yd - 0.012, 1.19), bevel=0.006)
    for zz in (0.68, 1.04):
        rbox('hinge', (-0.06, yd - 0.042, zz), (0.24, 0.012, 0.03), I, bevel=0.004, seg=1)
        for xx in (-0.15, -0.06, 0.03):
            KK.bolt((xx, yd - 0.05, zz), (0, -1, 0), I, r=0.01, drip=0.05)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.008, location=(0.1, yd - 0.055, 0.86), rotation=(math.radians(90), 0, 0), major_segments=14, minor_segments=5)
    bpy.context.object.name = 'knocker'; bpy.context.object.data.materials.append(I)
    blob('knockbase', (0.1, yd - 0.045, 0.9), (0.025, 0.01, 0.025), I, sub=0, seg=8)
    # taş söve: iki yanda üst üste bloklar + kemer taşları
    R = random.Random(4)
    for s in (-1, 1):
        for i, zz in enumerate((0.6, 0.78, 0.96, 1.13)):
            w = 0.09 if i % 2 == 0 else 0.07
            o = rbox('jamb', (s * (0.21 + w / 2 - 0.02), yd - 0.03, zz), (w, 0.1, 0.16), SOFT, bevel=0.015, seg=1)
            AT.wobble(o, 0.006, 6.0, R.random() * 9)
    for j in range(7):
        t = (j + 0.5) / 7 * math.pi
        c = (0.25 * math.cos(t), yd - 0.03, 1.2 + 0.17 * math.sin(t))
        o = rbox('arch', c, (0.075, 0.1, 0.11), SOFT, rot=(0, -math.degrees(t) + 90, 0), bevel=0.014, seg=1)
        AT.wobble(o, 0.005, 6.0, j * 3.3)
    # basamak + basamak taşları
    rbox('step', (0, -0.84, 0.47), (0.5, 0.26, 0.09), STEP, bevel=0.02, seg=1)
    rbox('step', (0, -0.98, 0.3), (0.56, 0.22, 0.1), STEP, rot=(0, 0, 2), bevel=0.02, seg=1)
    for k, (x, y) in enumerate(((0.05, -1.13), (-0.12, -1.13))):
        o = A.pebble((x, y, 0.02), 0.09, STEP, 70 + k); o.scale = (1.0, 0.85, 0.35); o.name = 'flagstone'
    # ---- pencereler
    GLASS = A.m_flat('#2e4762', 0.15, 6, 'darkglass')
    SH = A.m_wood('#b98a5a', 'lhshutter', paint='#4d9c8a', age=1.6, grime=NOG)
    for i, (z, a) in enumerate(WINDOWS):
        window(z, a, SOFT, GLASS, SH, I, 30 + i * 7)
    # ---- balkon: konsollar, döşeme, korkuluk
    for k in range(14):
        a = k * 2 * math.pi / 14 + 0.1
        r0 = rad(H - 0.1)
        c = V((math.cos(a) * (r0 + 0.05), math.sin(a) * (r0 + 0.05), H - 0.07))
        o = AT.prism('corbel', [(-0.075, 0.07), (0.075, 0.07), (0.075, 0.035), (0.0, -0.13), (-0.02, -0.13), (-0.075, -0.02)], 0.07, SOFT, bevel=0)
        o.location = c; o.rotation_euler = (0, 0, a - math.pi / 2)
        o.name = 'corbel'
    DK = overlay(A.m_wood('#9c6a40', 'lhdeck', age=1.3, grime=NOG), KK.L_sunbleach(0.25), 'lhdeck_k')
    cyl('balcony', (0, 0, H + 0.04), 0.6, 0.08, DK, verts=32, bevel=0.01)
    for k in range(12):
        a = k * 2 * math.pi / 12
        bk(rbox('deckline', (math.cos(a) * 0.4, math.sin(a) * 0.4, H + 0.081), (0.4, 0.008, 0.004), A.m_flat('#5e4028', 0.2, 8, 'deckgap'), rot=(0, 0, math.degrees(a)), bevel=0))
    RI = AT.m_metal('#3a3640', rust='#a65d34', name='lhrail', age=1.4)
    for k in range(18):
        a = k * 2 * math.pi / 18
        cyl('rail', (math.cos(a) * 0.565, math.sin(a) * 0.565, H + 0.235), 0.013, 0.31, RI, verts=6, bevel=0)
        if k % 3 == 0:
            KK.rust_drip(V((math.cos(a) * 0.605, math.sin(a) * 0.605, H)), V((math.cos(a), math.sin(a), 0)), 0.09, 0.012)
    for zz, rr in ((H + 0.39, 0.018), (H + 0.22, 0.011)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.565, minor_radius=rr, location=(0, 0, zz), major_segments=40, minor_segments=6)
        bpy.context.object.name = 'toprail'; bpy.context.object.data.materials.append(RI)
    # ---- fener odası
    BASE = AT.m_plaster('#d9483f', name='lhbase', dirt=0.0)
    AT.lathe('lroom', [(0.001, H + 0.08), (0.36, H + 0.08), (0.36, H + 0.2), (0.34, H + 0.22), (0.001, H + 0.22)], BASE, segs=24)
    cyl('lantern', (0, 0, H + 0.465), 0.31, 0.53, m_lens(), verts=8, bevel=0)      # üstü kubbe tabanına değer (kapalı)
    for k in range(8):
        a = (k + 0.5) * 2 * math.pi / 8
        rbox('mull', (math.cos(a) * 0.29, math.sin(a) * 0.29, H + 0.45), (0.035, 0.035, 0.52), I, rot=(0, 0, math.degrees(a)), bevel=0.006, seg=1)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.02, location=(0, 0, H + 0.7), major_segments=24, minor_segments=5)
    bpy.context.object.name = 'lring'; bpy.context.object.data.materials.append(I)
    ROOF = overlay(AT.m_plaster('#c94a40', name='lhroof', dirt=0.0), L_streaks('#8a3a30', 0.35, z_top=H + 1.06, length=0.4, scale=22), 'lhroof_k')
    AT.lathe('dome', [(0.001, H + 0.72), (0.42, H + 0.72), (0.4, H + 0.78), (0.3, H + 0.92), (0.15, H + 1.02), (0.001, H + 1.06)], ROOF, segs=32)
    for k in range(12):
        a = k * 2 * math.pi / 12
        pts = [(math.cos(a) * r_ * 1.01, math.sin(a) * r_ * 1.01, z_) for r_, z_ in ((0.41, H + 0.75), (0.32, H + 0.9), (0.17, H + 1.01), (0.05, H + 1.055))]
        o = tube('rib', pts, [0.014, 0.013, 0.011, 0.008], ROOF, res=2); o.data.bevel_resolution = 1
    blob('ball', (0, 0, H + 1.1), (0.06, 0.06, 0.06), I, sub=0, seg=14)
    tube('vane', [(0, 0, H + 1.1), (0, 0, H + 1.35)], [0.012, 0.01], I, res=2)
    blob('fish', (0.08, 0, H + 1.3), (0.12, 0.012, 0.045), I, sub=0, seg=14)
    AT.prism('fishtail', [(0.18, 1.3), (0.24, 1.34), (0.24, 1.26)], 0.012, I, loc=(0, 0, H), bevel=0.003)
    # ---- dip: eski kayalar ve ot/çiçek (aynı tohum: sınırlar korunur) + yaslanmış çapa
    for k, (x, y, r) in enumerate(((1.05, 0.3, 0.26), (-0.95, 0.6, 0.22), (0.7, -0.9, 0.18), (-1.0, -0.55, 0.2))):
        o = A.pebble((x, y, r * 0.45), r, STN, k + 50); o.scale = (1.0, 1.0, 1.4); o.name = 'rock'
    AT.dress(1.3, 15, n_tufts=12, flowers=4, pebbles=2, bushes=[(1.0, -0.45), (-0.95, 0.1), (0.35, 1.0), (-0.6, -0.85)], stone=STN,
             at=[(0.95, 0.0), (-0.7, 0.75), (0.5, -0.95)], exclude=lambda x, y: math.hypot(x, y) < 1.0 or (abs(x) < 0.3 and y < 0))
    anchor(V((0.52, -0.83, 0.0)), I)
    return 'deniz feneri'


def anchor(p, I):
    """Eski çapa: temele yaslı (gövde + kollar + halka), paslı; dibinde kısa halat kangalı."""
    AI = AT.m_metal('#4a4048', rust='#a8643a', name='anchor', age=1.6)
    lean = V((-0.12, 0.2, 1.0)).normalized()
    top = p + lean * 0.8
    tube('ashank', [tuple(p + lean * 0.06), tuple(top)], [0.036, 0.03], AI, res=2)
    side = V((0.85, 0.5, 0)).normalized()
    arm = [tuple(p + side * 0.24 + lean * 0.2), tuple(p + side * 0.12 + lean * 0.03), tuple(p + lean * 0.07), tuple(p - side * 0.12 + lean * 0.03), tuple(p - side * 0.24 + lean * 0.2)]
    tube('aarm', arm, [0.03, 0.033, 0.036, 0.033, 0.03], AI, res=3)
    for s in (1, -1):
        b = p + side * 0.24 * s + lean * 0.2
        blob('afluke', tuple(b + V((0, 0, 0.02))), (0.065, 0.026, 0.085), AI, rot=(0, 0, math.degrees(math.atan2(side.y, side.x))), sub=0, seg=10)
    tube('astock', [tuple(top - side * 0.22 - lean * 0.07), tuple(top + side * 0.22 - lean * 0.07)], [0.026, 0.026], AI, res=2)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.065, minor_radius=0.015, location=tuple(top + lean * 0.05), rotation=(0, math.radians(90), math.atan2(side.y, side.x)), major_segments=14, minor_segments=5)
    bpy.context.object.name = 'aring'; bpy.context.object.data.materials.append(AI)


DECIM = [(r'^lush$', 0.45), (r'^(bstone|rock|pebble|flagstone|Icosphere)$', 0.35), (r'^base$', 0.6),
         (r'^(toprail)$', 0.5), (r'^(knocker|aring)$', 0.6), (r'^(arch|jamb)$', 0.6), (r'^doortop$', 0.6),
         (r'^(pet|fc|stem)$', 0.35), (r'^(ashank|aarm|astock|vane|rib)$', 0.6)]
WEIGHTS = [(r'^tower$', 1.15), (r'^(door|doortop|hinge|knocker|knockbase)(_lo)?$', 1.7), (r'^(wglass|wsill|wlintel|wjamb|wbar|shutter)(_lo)?$', 1.6),
           (r'^(lantern|mull|lring)$', 1.5), (r'^(dome|rib)$', 1.2), (r'^(corbel|balcony)$', 1.0), (r'^(rail|toprail)$', 0.9),
           (r'^(base|bstone)$', 0.9), (r'^(arch|jamb|step)$', 1.4), (r'^(ashank|aarm|astock|afluke|aring)$', 1.2), (r'^ropecore', 0.8),
           (r'^(lush|rosette|tuft|pet|stem|fc)$', 0.5)]

if __name__ == '__main__':
    KK.main('b_lighthouse', build, DECIM, WEIGHTS, budget=12000, tex=1024, draft_dist=10.5, ds_low=True, floor=0.03)
