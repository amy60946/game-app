# Komik giyilebilir eşyalar C (kullanıcı, 23 Ekim 2026): kol çorabı, ponpon, çiçek kolye + çim etek — kodla, özgün tasarım.
# Aynı dil (assets_items): dokulu kumaş/örgü, yaprak, halat; yumuşak AO; parlak "vinyl oyuncak" havası; dış çizgi yok.
# Ölçü: çocuk Okti biriminde (boy 1,70; gövde ekseni (0, 0.04)). Oyun eşyayı sınır kutusuyla ölçekler/yerleştirir
# (okti_fit_rules "item:<id>"), birim serbest. Ön = −Y, yukarı = +Z.
# Kullanım: python -I assets_wear_c.py -- <çıktı_klasörü> [w_socks_arm ...]   (oyuna: export_game.py socks_arm pompom outfit_hula)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets_town import *
import assets_town as T
import assets_v3 as A
from assets_v3 import _shade

TAU = 2 * math.pi

def _madd(G, a, b, c):
    """a * b + c (düğüm)."""
    m = G.n.new('ShaderNodeMath'); m.operation = 'MULTIPLY_ADD'
    for i, x in enumerate((a, b, c)):
        if isinstance(x, (int, float)): m.inputs[i].default_value = x
        else: G.l.new(x, m.inputs[i])
    return m.outputs[0]

def _frame(n, hint=(0, 0, 1)):
    """n'ye dik iki birim vektör (t1 hint'e yakın)."""
    n = V(n).normalized(); h = V(hint)
    if abs(n.dot(h)) > 0.95: h = V((1, 0, 0))
    t1 = (h - n * n.dot(h)).normalized(); t2 = n.cross(t1)
    return t1, t2

def _grow(k):
    """Sahnedeki her şeyi orijine göre k kat büyüt (dönüşümler köşelere işlenir). Oyun eşyayı sınır kutusuyla ölçekler; büyütme
    yalnız pişirmedeki AO mesafesini (0,35) eşyaya oranla küçültür (yoğun şerit/çiçek kararmasın). Nesne-koordinatlı gürültüler
    pişirmede dünya koordinatıyla okunur: malzemelerde ölçek buna göre (PSC)."""
    to_mesh_all()
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH': continue
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            try: bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception: pass
        o.data.transform(o.matrix_world); o.matrix_world = mathutils.Matrix.Identity(4)
        o.data.transform(mathutils.Matrix.Scale(k, 4))

# ------------------------------------------------------------------ malzemeler

def m_knit(stops, ztop, L, heel=None, name='knit', cols=40, rows=30):
    """Örgü çorap: boy boyunca (nesne Z) renk bantları (CONSTANT; kenarı örgü zikzağı), ilmek 'V' deseni (sütun × sıra),
    lastikli bilekte dikey fitiller, hafif tüylenme. stops: [(s, '#renk')], s = (ztop − z) / L (0 ağız, 1 burun).
    heel: (s0, s1, x_eşik, '#renk') −X yanında topuk yaması."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt); o = G.obj()
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
        ang = G.math('ARCTAN2', sp.outputs['Y'], sp.outputs['X'])
        col_i = G.math('MULTIPLY', ang, cols / TAU)
        tri = G.math('ABSOLUTE', G.math('SUBTRACT', G.math('FRACT', col_i), 0.5))          # 0 (sütun ortası) .. 0.5 (kenar)
        s = G.math('MULTIPLY', G.math('SUBTRACT', ztop, sp.outputs['Z']), 1.0 / L)
        sj = _madd(G, tri, 0.5 / rows, s)                                   # bant kenarı ilmek zikzağı
        rp = ramp(nt, stops, 'CONSTANT'); l.new(sj, rp.inputs['Fac'])
        col = rp.outputs[0]
        if heel:                                    # elips yama: s yönünde (s0..s1), çevrede −X'ten ± aw radyan
            s0, s1, aw, hc = heel
            sm = (s0 + s1) / 2; sh = (s1 - s0) / 2
            da = G.math('SUBTRACT', math.pi, G.math('ABSOLUTE', ang))
            e = G.math('ADD', G.math('POWER', G.math('MULTIPLY', G.math('SUBTRACT', sj, sm), 1.0 / sh), 2.0), G.math('POWER', G.math('MULTIPLY', da, 1.0 / aw), 2.0))
            col = G.mix(G.math('LESS_THAN', e, 1.0), col, hc)
        # ilmek V'leri: her sütunda aşağı bakan V sıraları; ilmek araları ve sütun araları koyu
        f = G.math('FRACT', _madd(G, s, rows, G.math('MULTIPLY', tri, 1.1)))
        st = G.math('MULTIPLY', G.rng(f, 0.0, 0.3), G.rng(f, 1.0, 0.72))
        st = G.math('MULTIPLY', st, G.rng(tri, 0.5, 0.34))
        col = G.mix(G.math('MULTIPLY', G.math('SUBTRACT', 1.0, st), 0.32), col, '#4a3a40', 'MULTIPLY')
        col = G.mix(G.math('MULTIPLY', st, 0.07), col, '#ffffff', 'SCREEN')
        # bilek lastiği: dikey fitil (s < 0.15)
        rib = G.rng(G.math('SINE', G.math('MULTIPLY', ang, 14.0)), -0.2, 0.9)
        cuffm = G.rng(s, 0.16, 0.13)
        col = G.mix(G.math('MULTIPLY', G.math('MULTIPLY', G.math('SUBTRACT', 1.0, rib), cuffm), 0.3), col, '#6a5a60', 'MULTIPLY')
        # tüylenme + hafif ton dalgası
        col = G.mix(0.1, col, G.noise(G.mapping(o, (160, 160, 160)), 1.0, 2, out='Color'), 'OVERLAY')
        col = G.mix(G.rng(G.noise(o, 6, 4), 0.35, 0.7, 0, 0.07), col, '#fff6ee', 'SCREEN')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_foil(base, light, dark, name):
    """Ponpon şeridi: dipten (u=0) uca koyu → ana → açık; boy boyunca kırışık parıltı bantları (folyo hissi), kenarlar koyu."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        uv = uv_node(nt); sp = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sp.inputs[0])
        rp = ramp(nt, [(0.0, _shade(base, 0.8)), (0.25, base), (1.0, _shade(base, 1.1))]); l.new(sp.outputs['X'], rp.inputs['Fac'])
        col = rp.outputs[0]
        o = G.obj()
        cr = G.noise(G.mapping(uv.outputs[0], (9.0, 0.6, 1.0)), 2.2, 3)
        col = G.mix(G.rng(cr, 0.58, 0.7, 0, 0.5), col, light)
        col = G.mix(G.rng(cr, 0.42, 0.32, 0, 0.35), col, dark, 'MULTIPLY')
        col = G.mix(G.rng(G.math('ABSOLUTE', sp.outputs['Y']), 0.7, 1.0, 0, 0.3), col, dark)
        col = G.mix(G.rng(G.noise(o, 2.4, 3), 0.58, 0.7, 0, 0.12), col, light, 'SCREEN')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

def m_petal(center, mid, edge, name, vein=None):
    """Taç yaprağı: göbekten (u=0) uca renk geçişi, ince boyuna damarlar, kenarda açık ton, hafif dalgalanma."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = A._G(nt)
        uv = uv_node(nt); sp = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sp.inputs[0])
        rp = ramp(nt, [(0.0, center), (0.38, mid), (0.8, mid), (1.0, edge)]); l.new(sp.outputs['X'], rp.inputs['Fac'])
        col = rp.outputs[0]
        vv = G.rng(G.math('SINE', G.math('MULTIPLY', sp.outputs['Y'], 11.0)), 0.6, 1.0, 0, 0.18)
        col = G.mix(G.math('MULTIPLY', vv, G.rng(sp.outputs['X'], 0.9, 0.2)), col, vein or _shade(center, 1.0), 'MULTIPLY')
        col = G.mix(0.15, col, G.noise(G.obj(), 14, 3, out='Color'), 'OVERLAY')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)

# ------------------------------------------------------------------ 1) kol çorabı

SOCK_TOP, SOCK_L = 0.22, 0.44
SOCK_STOPS = [(0.0, '#f2ebe0'), (0.15, '#d8392f'), (0.2617, '#ec7a22'), (0.3733, '#f0b92a'), (0.485, '#46a54a'),
              (0.5967, '#2f7fcf'), (0.7083, '#7a4cb8'), (0.84, '#f2ebe0')]

def _sock_radius(s, th):
    """s: 0 ağız .. 1 burun ucu; th: açı (0 = +X). Döner: (yarıçap, x_kayma)."""
    c, sn = math.cos(th), math.sin(th)
    def lerp(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))
    def sstep(a, b, x):
        t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
    if s <= 0.16:                                   # lastikli bilek (ağızda hafif genişler)
        rx, ry = 0.128 + 0.006 * sstep(0.05, 0.0, s), 0.152 + 0.006 * sstep(0.05, 0.0, s)
    elif s <= 0.4:                                  # bilek → topuk üstü hafif incelir
        t = sstep(0.16, 0.4, s); rx, ry = lerp(0.128, 0.116, t), lerp(0.152, 0.142, t)
    else:                                           # ayak: pençe üstünde genişler
        t = sstep(0.38, 0.62, s); rx, ry = lerp(0.116, 0.128, t), lerp(0.142, 0.198, t)
    r = 1.0 / math.sqrt((c / rx) ** 2 + (sn / ry) ** 2)         # elips
    if s <= 0.15: r += 0.0055 * math.cos(th * 12)                 # fitil
    if c < 0: r += 0.042 * math.exp(-((s - 0.45) / 0.1) ** 2) * (-c) ** 1.4     # topuk (−X: kolun üst/dış yanı)
    if s > 0.8: r *= math.sqrt(max(0.0, 1 - ((s - 0.8) / 0.2) ** 2)) ** 0.9       # yuvarlak burun
    return r, 0.024 * sstep(0.55, 1.0, s)          # burun hafifçe +X'e (topuğun tersine) kıvrılır

def w_socks_arm():
    """Renkli kol çorabı (tek; oyun iki kola koyar): tombul örgü çorap, ağzı/lastikli bileği üstte, yuvarlak burun altta,
    −X yanında hafif topuk kıvrımı; krem bilek + gökkuşağı çizgileri (kırmızı → mor) + krem topuk ve burun."""
    NA = 24
    S = [0.0, 0.02, 0.05, 0.09, 0.13, 0.16, 0.21, 0.27, 0.33, 0.39, 0.45, 0.51, 0.57, 0.63, 0.69, 0.75, 0.8, 0.85, 0.89,
         0.925, 0.955, 0.98, 0.995]
    bm = bmesh.new()
    def ring(z, rr, dx=0.0):
        return [bm.verts.new((math.cos(i / NA * TAU) * rr[i] + dx, math.sin(i / NA * TAU) * rr[i], z)) for i in range(NA)]
    rings = []
    # iç duvar (ağızdan içeri, koyu) → dudak → dış yüz
    for (s_in, k) in ((0.12, 0.86), (0.05, 0.87), (-0.004, 0.9)):
        rings.append(ring(SOCK_TOP - s_in * SOCK_L, [_sock_radius(0.0, i / NA * TAU)[0] * k for i in range(NA)]))
    rings.append(ring(SOCK_TOP + 0.006, [_sock_radius(0.0, i / NA * TAU)[0] * 0.96 for i in range(NA)]))
    for s in S:
        rr = [_sock_radius(s, i / NA * TAU)[0] for i in range(NA)]
        rings.append(ring(SOCK_TOP - s * SOCK_L, rr, _sock_radius(s, 0)[1]))
    for a, b2 in zip(rings[:-1], rings[1:]):
        for i in range(NA):
            j = (i + 1) % NA
            bm.faces.new((a[i], a[j], b2[j], b2[i]))
    tip = bm.verts.new((_sock_radius(1.0, 0)[1], 0, SOCK_TOP - SOCK_L))
    for i in range(NA): bm.faces.new((rings[-1][i], rings[-1][(i + 1) % NA], tip))
    bot = bm.verts.new((0, 0, SOCK_TOP - 0.13 * SOCK_L))
    for i in range(NA): bm.faces.new((rings[0][(i + 1) % NA], rings[0][i], bot))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    INSIDE = A.m_flat('#5a4a52', 0.1, 6, 'sockin')
    KN = m_knit(SOCK_STOPS, SOCK_TOP, SOCK_L, heel=(0.33, 0.57, 0.95, '#f2ebe0'), name='sockknit')
    o = link_mesh('sock', bm, [KN, INSIDE]); smooth(o)
    for p in o.data.polygons:                       # ağız içi koyu (içe bakan duvar + dip)
        if p.center.z > SOCK_TOP - 0.14 * SOCK_L and p.normal.dot(V((p.center.x, p.center.y, 0))) < 0: p.material_index = 1
    return 'kol çorabı'

# ------------------------------------------------------------------ 2) ponpon

def w_pompom():
    """Amigo ponponu (tek; oyun iki ele koyar): merkezden dışa 90 parlak ince yassı şerit (pembe + altın; düz kesik uçlu,
    burgulu, uca doğru kıvrık, kırışık folyo), içte pembe dolgu topu; ÜSTTE (+Z) elin tuttuğu kısa sap + halka.
    Top kol ucunun ötesinde durur (oturma: fwd)."""
    R = random.Random(7)
    PK = m_foil('#f0569c', '#ffc4de', '#b8396e', 'foilpink')
    GD = m_foil('#f4bc3a', '#ffeaa0', '#c48a26', 'foilgold')
    N = 90; RAD = 0.25
    def build(bm):
        out = []
        ga = math.pi * (3 - math.sqrt(5))
        for k in range(N):
            zz = 1 - 2 * (k + 0.5) / N; rr = math.sqrt(1 - zz * zz); a = k * ga
            d = V((math.cos(a) * rr, math.sin(a) * rr, zz))
            d = (d + V((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(-1, 1))) * 0.1).normalized()
            t1, t2 = _frame(d, (R.uniform(-1, 1), R.uniform(-1, 1), 1))
            ba = R.uniform(0, TAU); bend = t1 * math.cos(ba) + t2 * math.sin(ba)
            L = RAD * R.uniform(0.85, 1.05) * (0.78 if d.z > 0.8 else 1.0)          # sapın çevresi biraz kısa
            tw = R.uniform(-2.6, 2.6); cb = R.uniform(0.35, 0.9)
            mi = 0 if (k % 5) not in (1, 3) else 1                                   # 3/5 pembe, 2/5 altın
            segs = 5; rows = []
            for i in range(segs + 1):
                s = i / segs
                dd = (d + bend * cb * s * s).normalized()
                c = d * 0.05 + dd * (L * s) + V((0, 0, -0.035 * s * s))
                sd0 = t1 * math.cos(tw * s) + t2 * math.sin(tw * s)
                sd = (sd0 - dd * dd.dot(sd0)).normalized()
                w = 0.026 * (0.45 if i == 0 else 1.0)
                c = c + dd.cross(sd) * (0.006 * (1 if i % 2 else -1) * s)               # kırışık
                rows.append(((bm.verts.new(c + sd * w), (s, 1.0)), (bm.verts.new(c - sd * w), (s, -1.0))))
            for i in range(segs):
                (l0, r0), (l1, r1) = rows[i], rows[i + 1]
                out.append(([l0, l1, r1, r0], mi))
        return out
    mesh_from_blades('strips', build, [PK, GD])
    # dolgu: topaklı iç kütle (kısa şerit yığını gibi), pembe-altın benekli folyo
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.165, location=(0, 0, -0.005))
    co = bpy.context.object; co.name = 'core'
    for v in co.data.vertices: v.co += v.co.normalized() * (0.05 * mnoise.noise(v.co * 14 + V((3, 1, 7))) + 0.02 * mnoise.noise(v.co * 40))
    def core_b(nt, bsdf):
        G = A._G(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 3.0, 3), 0.5, 0.62), '#e2619c', '#ecb948')
        col = G.mix(G.rng(G.noise(G.mapping(o, (10, 10, 10)), 1.0, 2), 0.58, 0.7, 0, 0.35), col, '#ffc4de', 'SCREEN')
        nt.links.new(col, bsdf.inputs['Base Color'])
    co.data.materials.append(nodes_mat('pomcore', core_b)); smooth(co)
    HD = A.m_flat('#f7f0f4', 0.06, 8, 'pomhandle')
    tube('handle', [(0, 0, 0.12), (0, 0, 0.29)], [0.024, 0.022], HD, res=1)
    blob('cap', (0, 0, 0.295), (0.03, 0.03, 0.018), HD, sub=0, seg=8)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.034, minor_radius=0.009, location=(0, 0, 0.32), rotation=(math.radians(90), 0, 0),
                                     major_segments=12, minor_segments=4)
    bpy.context.object.data.materials.append(A.m_flat('#e9b43c', 0.1, 8, 'pomring'))
    _grow(3.0)
    return 'ponpon'

# ------------------------------------------------------------------ 3) çiçek kolye + çim etek

BODY_Y = 0.04                                       # çocuk Okti gövde ekseni (y)

def petal_flower(name, c, nrm, kind, size, R, mats, roll=0.0, P=8):
    """Tombul çiçek: 5 kubbeli taç yaprağı (her biri 10 köşeli yelpaze, üstü şişkin) + göbek; grain uv: u = göbekten uca.
    kind: 'hib' (geniş, çanak, uzun sarı başçık) | 'fra' (oval, çark gibi bindirmeli)."""
    n = V(nrm).normalized(); t1, t2 = _frame(n)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    M = 5
    for k in range(M):
        a = roll + k * TAU / M
        rad = t1 * math.cos(a) + t2 * math.sin(a); acr = n.cross(rad)
        if kind == 'hib': Lp, Wp, cup, tw = size * 1.0, size * 0.52, 0.34, 0.0
        else: Lp, Wp, cup, tw = size * 1.0, size * 0.36, 0.12, 0.42
        if kind == 'fra': rad, acr = (rad * math.cos(tw) + acr * math.sin(tw)), (acr * math.cos(tw) - rad * math.sin(tw))
        base = V(c) + n * (0.004 * k)               # bindirme: her yaprak bir öncekinin biraz üstünde
        top_c = base + rad * (Lp * 0.52) + n * (size * 0.22 + cup * Lp * 0.25)
        bot_c = base + rad * (Lp * 0.5) - n * (size * 0.08)
        ring_v = []
        for j in range(P):
            ph = j / P * TAU
            u = 0.5 - 0.5 * math.cos(ph); v = math.sin(ph)
            w = Wp * v * (math.sin(math.pi * min(1.0, 0.12 + u * 0.95)) ** 0.6)
            p = base + rad * (Lp * u) + acr * w + n * (cup * Lp * u * u)
            ring_v.append((bm.verts.new(p), (u, v)))
        tv = bm.verts.new(top_c); bv = bm.verts.new(bot_c)
        for j in range(P):
            (a0, ua), (a1, ub) = ring_v[j], ring_v[(j + 1) % P]
            for (verts, uvs) in (((a0, a1, tv), (ua, ub, (0.5, 0.0))), ((a1, a0, bv), (ub, ua, (0.5, 0.0)))):
                try: f = bm.faces.new(verts)
                except ValueError: continue
                f.material_index = 0
                for lp, uv in zip(f.loops, uvs): lp[uvl].uv = uv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = link_mesh(name, bm, [mats[0]]); smooth(o)
    # göbek
    blob(name + 'c', tuple(V(c) + n * (size * 0.16)), (size * 0.2, size * 0.2, size * 0.14), mats[1], sub=0, seg=6).rotation_euler = n.to_track_quat('Z', 'Y').to_euler()
    if kind == 'hib':                               # uzun başçık (hibiskus imzası)
        tip = V(c) + n * (size * 0.62) + t1 * (size * 0.18)
        tube(name + 's', [tuple(V(c) + n * (size * 0.15)), tuple(tip)], [size * 0.045, size * 0.03], mats[2], res=1)
        blob(name + 'st', tuple(tip), (size * 0.09, size * 0.09, size * 0.09), mats[3], sub=0, seg=6)
    return o

def w_outfit_hula():
    """Çiçek kolye ve çim etek: ÜSTTE başın jöle eteğinin hemen altında göğse sarkan tombul kolye (yeşil yapraklı kordon
    üstünde iri pembe hibiskus, beyaz ve sarı frangipani; arkası yüksek — baş eteğinin içinde —, önü U gibi sarkık), ALTTA
    kalçada halat bel bandı + iki kat, uca doğru açılan ve dalgalı savrulan çim/saman şerit etek, kalçada büyük pembe hibiskus.
    Arası boş: göbek görünür."""
    R = random.Random(23)
    HIB = [m_petal('#b8204e', '#ee5a8a', '#ff9dbc', 'hibpetal'), A.m_flat('#d83a6a', 0.1, 8, 'hibc'), A.m_flat('#f7d14a', 0.08, 8, 'hibst'), A.m_flat('#ffc42e', 0.1, 10, 'hibpol')]
    FRW = [m_petal('#f2b631', '#fff3d8', '#fffaf1', 'frawhite', vein='#e8dccb'), A.m_flat('#f2b631', 0.1, 8, 'fracw')]
    FRY = [m_petal('#ec8a1e', '#ffd04f', '#ffe7a0', 'frayel'), A.m_flat('#e87c1a', 0.1, 8, 'fracy')]
    LF = m_leaf('#2f7f35', '#4fa443', '#86c95a', '#b8e488', 'leileaf')
    # kolye yolu: arkada yüksek (baş eteğinin içinde), önde U gibi sarkar
    def lei(th):
        f = (1 - math.sin(th)) / 2
        z = 0.88 - 0.2 * f ** 1.6
        rr = 0.3 + 0.022 * f
        return V((math.cos(th) * rr, BODY_Y + math.sin(th) * rr, z))
    # yeşil kordon (yapraklı dolgu, çiçeklerin arası boş görünmesin)
    NM, NS, rc = 32, 4, 0.027
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain')
    ring = []
    for i in range(NM):
        th = i / NM * TAU; c = lei(th); tg = (lei(th + 0.01) - lei(th - 0.01)).normalized()
        n1 = (c - V((0, BODY_Y, c.z))).normalized(); n1 = (n1 - tg * tg.dot(n1)).normalized(); n2 = tg.cross(n1)
        ring.append([bm.verts.new(c + (n1 * math.cos(j / NS * TAU) + n2 * math.sin(j / NS * TAU)) * rc * (1 + 0.25 * math.sin(i * 2.3 + j))) for j in range(NS)])
    for i in range(NM):
        for j in range(NS):
            i2, j2 = (i + 1) % NM, (j + 1) % NS
            f = bm.faces.new((ring[i][j], ring[i2][j], ring[i2][j2], ring[i][j2]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = ((jj / NS) * 0.6 + 0.2, (ii % 2) * 2 - 1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    smooth(link_mesh('cord', bm, [A.m_flat('#3d8a3c', 0.3, 18, 'leicord')]))
    # çiçekler: önde iri ve sık (görünen kısım), arkada seyrek
    spots = [(0, 'hib', 0.118), (21, 'fra_w', 0.104), (42, 'fra_y', 0.102), (64, 'hib', 0.104), (90, 'fra_w', 0.092), (125, 'fra_y', 0.085), (160, 'hib', 0.085)]
    placed = []
    for d, kind, size in spots:
        for sg in ((1,) if d == 0 else (1, -1)):
            th = math.radians(-90 + sg * d); placed.append(th)
            p = lei(th); nrm = V((math.cos(th), math.sin(th), 0.5 + 0.3 * (1 - math.sin(th)) / 2))
            mats = HIB if kind == 'hib' else (FRW if kind == 'fra_w' else FRY)
            petal_flower('lei%d_%d' % (d, sg), p + nrm.normalized() * 0.012, nrm, 'hib' if kind == 'hib' else 'fra', size, R, mats, roll=R.uniform(0, TAU), P=8 if d < 100 else 6)
    # yapraklar: her çiçek arasında bir yaprak, yol boyunca dışa
    def leaves(bm):
        out = []
        ths = sorted(placed)
        for k, (a, b2) in enumerate(zip(ths, ths[1:] + [ths[0] + TAU])):
            th = (a + b2) / 2; p = lei(th)
            tg = (lei(th + 0.01) - lei(th - 0.01)).normalized(); nrm = V((math.cos(th), math.sin(th), 0.45)).normalized()
            sg = 1 if k % 2 else -1
            d = (tg * sg * 0.55 + nrm * 0.6 + V((0, 0, -0.35))).normalized()
            side = d.cross(nrm).normalized()
            for f in blade(bm, p, d, side, R.uniform(0.1, 0.12), 0.034, 0.2, segs=3): out.append((f, 0))
        return out
    mesh_from_blades('leaves', leaves, [LF])
    # bel bandı: halat (kendi grain uv'si: u = çevre, v = kesit)
    ZB, RB, rb = 0.485, 0.333, 0.028
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); NM, NS = 26, 4
    vs = [[bm.verts.new((math.cos(i / NM * TAU) * (RB + rb * math.cos(j / NS * TAU)), BODY_Y + math.sin(i / NM * TAU) * (RB + rb * math.cos(j / NS * TAU)) * 0.98,
                         ZB + rb * 1.15 * math.sin(j / NS * TAU))) for j in range(NS)] for i in range(NM)]
    for i in range(NM):
        for j in range(NS):
            i2, j2 = (i + 1) % NM, (j + 1) % NS
            f = bm.faces.new((vs[i][j], vs[i2][j], vs[i2][j2], vs[i][j2]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uvl].uv = (ii / NM * TAU * RB * 3, jj / NS * 0.3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    smooth(link_mesh('band', bm, [m_rope('#d4b06a', 'hulaband', age=0.35)]))
    # etek: iki kat şerit; uca doğru açılır, çevre boyunca dalgalı savrulma + şerit başına rastgele boy/açı
    GR = [m_leaf('#3f8a3a', '#5fae48', '#9ad064', '#c4e692', 'grassA'), m_leaf('#4f9440', '#76b84e', '#b2d870', '#d2eb9a', 'grassB'),
          m_leaf('#9a8440', '#c9ae62', '#e2cd88', '#efe2b0', 'straw')]
    def strands(bm):
        out = []
        for layer, (Nn, r0, r1, z0, z1, wt) in enumerate(((42, 0.318, 0.42, ZB + 0.005, 0.215, 0.058), (44, 0.34, 0.47, ZB - 0.012, 0.232, 0.06))):
            for k in range(Nn):
                th = (k + 0.5 * layer + R.uniform(-0.3, 0.3)) / Nn * TAU
                rad = V((math.cos(th), math.sin(th), 0)); tg = V((-math.sin(th), math.cos(th), 0))
                ze = z1 + R.uniform(-0.045, 0.03) + 0.022 * math.sin(th * 2 + 1.0)
                re = r1 + R.uniform(-0.03, 0.03) + 0.02 * math.sin(th * 3 + 0.4)
                ph = math.sin(th * 2.0 + 0.7) * 0.07 + R.uniform(-0.04, 0.04)          # savrulma: dalga + rastgele yatış
                wk = wt * R.uniform(0.8, 1.2); tws = R.uniform(-0.5, 0.5)
                mi = R.choices((0, 1, 2), (0.4, 0.3, 0.3))[0]
                rows = []
                for i in range(5):
                    s = (0.0, 0.3, 0.6, 0.85, 1.0)[i]
                    rr = r0 + (re - r0) * s ** 1.35
                    c = V((rad.x * rr, BODY_Y + rad.y * rr * 0.93, z0 + (ze - z0) * s)) + tg * (ph * s * s)
                    w = wk * (1 - 0.3 * s) * (0.3 if i == 4 else 1.0)
                    tgs = (tg + rad * (0.3 * math.sin(th * 7 + k) + tws * s)).normalized()
                    rows.append(((bm.verts.new(c + tgs * w * 0.5), (s, 1.0)), (bm.verts.new(c - tgs * w * 0.5), (s, -1.0))))
                for i in range(4):
                    (l0, r0_), (l1, r1_) = rows[i], rows[i + 1]
                    out.append(([l0, l1, r1_, r0_], mi))
        return out
    mesh_from_blades('skirt', strands, GR)
    # kalçada büyük hibiskus (petin sol önü)
    th = math.radians(-36)
    petal_flower('hip', V((math.cos(th) * (RB + 0.035), BODY_Y + math.sin(th) * (RB + 0.035), ZB + 0.005)), V((math.cos(th), math.sin(th), 0.25)), 'hib', 0.1, R, HIB, roll=0.4)
    _grow(1.5)
    return 'hula'

BUILDERS = {'w_socks_arm': (w_socks_arm, 512, None), 'w_pompom': (w_pompom, 512, None), 'w_outfit_hula': (w_outfit_hula, 512, None)}

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    OUT = args[0]; only = args[1:] or list(BUILDERS)
    os.makedirs(OUT, exist_ok=True)
    for name in only:
        fn, size, dec = BUILDERS[name]
        reset(); fn(); to_mesh_all()
        for o in bpy.context.scene.objects:
            if o.type == 'MESH' and 'grain' not in o.data.uv_layers: grain_uv(o)
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        tris = export_baked_fbx(f'{OUT}/{name}', objs, size=size, decimate=dec, ao_strength=float(os.environ.get('POFI_AO', '0.55')))
        print(name, 'üçgen', tris, flush=True)
