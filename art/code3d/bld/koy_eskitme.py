# Köy yapıları (b_home, b_shop, b_hut, b_task_board) için ortak eskitme ve ada hayatı parçaları (24 Ekim 2026; kullanıcı:
# "haritadaki bütün yapılar en uygun, ayrıntılı ve ada hayatına uygun eskitmeli olsun"). bld_kit hattıyla pişirilir.
# İlke: oyun kamerası 8–14 m geriden, ~24° yukarıdan bakar → ayrıntı İRİ ve OKUNUR olmalı:
#   geometri  — yosun öbeği, yama tahta + çivi, paslı demir kuşak, halat bağ, kum birikintisi, deniz kabuğu, deniz yıldızı, şamandıra;
#   renk      — güneşte solmuş ve pul pul dökülmüş boya (altından tahta), saçak/pencere altında tuz ve su izi, oyuklarda kir,
#               dipte toprak + yosun, taşta liken; mikroskobik gürültü değil.
# Renkler canlı ama dengeli (soluk değil, neon değil); dış çizgi yok; tasarımlar özgün.
# Dünya konumu (Geometry → Position) kullanan etkiler pişirmede de doğrudur: proxy_bake kaynağı dünya koordinatında birleştirir.
# Oyuk kiri Ambient Occlusion düğümüyle (yalnız aynı nesne: pişirmede tüm yapı tek ağ, hedef ağ ışınlara karışmaz).
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', 'v6')):
    if p not in sys.path: sys.path.insert(0, p)
import bpy, bmesh
from mathutils import Vector as V, noise as MN
import kit
from kit import srgb, ramp, nodes_mat, uv_node, rbox, blob, cyl, tube
import assets_v3 as A
from assets_v3 import _shade, link_mesh, smooth, m_leaf, m_flat
import assets_town as AT
import bld_kit as BK


# ------------------------------------------------------------------ düğüm yardımcıları

class G2(A._G):
    def pos(self):
        g = self.n.new('ShaderNodeNewGeometry'); return g.outputs['Position']
    def wz(self):
        sp = self.n.new('ShaderNodeSeparateXYZ'); self.l.new(self.pos(), sp.inputs[0]); return sp.outputs['Z']
    def wy(self):
        sp = self.n.new('ShaderNodeSeparateXYZ'); self.l.new(self.pos(), sp.inputs[0]); return sp.outputs['Y']
    def ao(self, dist=0.18, samples=8):
        a = self.n.new('ShaderNodeAmbientOcclusion'); a.samples = samples; a.only_local = True
        a.inputs['Distance'].default_value = dist; return a.outputs['AO']


def _surface(G, col, age=1.0, salt=0.0, cavity=0.45, ground=0.35, moss=0.6, wet=True):
    """Ortak eskime katmanları (dünya konumuyla): oyuk kiri, tuz/su izi (dikey çizgiler, lekeli), dipte toprak + yosun."""
    p = G.pos()
    if cavity:
        occl = G.rng(G.ao(0.16), 0.75, 0.35, 0, cavity)                 # oyuk: koyu toprak kiri
        col = G.mix(occl, col, '#3e2c1c')
    if salt:
        st = G.noise(G.mapping(p, (16, 16, 1.1)), 1.0, 3)               # boyuna uzamış gürültü → aşağı akan izler
        gate = G.rng(G.noise(p, 1.3, 3), 0.42, 0.62)
        s_pale = G.math('MULTIPLY', G.rng(st, 0.56, 0.7), gate)
        col = G.mix(G.math('MULTIPLY', s_pale, 0.42 * salt), col, '#efe9da')    # tuz çiçeği: açık, kireçli
        if wet:
            s_dark = G.math('MULTIPLY', G.rng(st, 0.36, 0.26), gate)
            col = G.mix(G.math('MULTIPLY', s_dark, 0.3 * salt), col, '#4a3a2a')  # su izi: koyu, ince
    if ground:
        zn = G.math('ADD', G.wz(), G.math('MULTIPLY', G.noise(p, 4, 5), 0.18))
        grime = G.rng(zn, ground, 0.02, 0, 0.6 * age)
        col = G.mix(grime, col, '#5a4330')
        if moss:
            mm = G.math('MULTIPLY', G.rng(zn, ground * 0.6, 0.0, 0, moss), G.rng(G.noise(p, 7, 4), 0.48, 0.6))
            col = G.mix(mm, col, '#557a2c')
    return col


def m_wood2(hexc, name, paint=None, age=1.0, salt=0.0, cavity=0.45, ground=0.35, moss=0.6, chips=1.0, silver=0.12):
    """Ada ahşabı: tahta boyunca dalgalı halka bantları + lif + düğüm + boyuna çatlak (grain UV); hafif gümüşi güneş solması;
    paint: güneşte solmuş boya, İRİ pullar halinde dökülür (kenarda ve dipte daha çok), pul kenarı koyu, altından tahta;
    salt: tuz/su izi; ground: dipte toprak + yosun (dünya z)."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt)
        uv = uv_node(nt)
        wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
        wv.inputs['Scale'].default_value = 1.6; wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 3
        l.new(G.mapping(uv.outputs[0], (1.0, 7.0, 1.0)), wv.inputs['Vector'])
        rp = ramp(nt, [(0.0, _shade(hexc, 0.74)), (0.5, hexc), (1.0, _shade(hexc, 1.14))]); l.new(wv.outputs['Fac'], rp.inputs['Fac'])
        fibn = G.noise(G.mapping(uv.outputs[0], (2.0, 40.0, 1.0)), 3.0, 5, out='Color')
        wood = G.mix(0.3, rp.outputs[0], fibn, 'OVERLAY')
        knot = G.rng(G.vor(uv.outputs[0], 1.3), 0.06, 0.0, 0, 0.6)
        wood = G.mix(knot, wood, _shade(hexc, 0.55))
        ck = G.vor(G.mapping(uv.outputs[0], (0.5, 9.0, 1.0)), 2.0, 'DISTANCE_TO_EDGE')
        crack = G.math('MULTIPLY', G.rng(ck, 0.03, 0.0, 0, 1), G.rng(G.noise(uv.outputs[0], 2.2), 0.5, 0.6))
        o = G.obj()
        wood = G.mix(G.rng(G.noise(o, 1.3, 5, 0.6), 0.55, 0.75, 0, silver * age), wood, '#a49b8c')   # güneş solması
        out = wood
        if paint:
            pcol = G.mix(G.rng(G.noise(o, 1.1, 4), 0.3, 0.75, 0, 0.32 * age), paint, _shade(paint, 1.2))   # solma
            pcol = G.mix(0.14, pcol, fibn, 'OVERLAY')                                                   # fırça izi
            bare = _shade(hexc, 0.95)
            # dökülme: iri gürültü + kenar + dipte daha çok (dünya z)
            ch = G.math('ADD', G.noise(o, 2.6 / max(chips, 0.3), 6, 0.62), G.math('MULTIPLY', G.edges(0.54, 0.64), 0.16 * chips))
            ch = G.math('ADD', ch, G.math('MULTIPLY', G.rng(G.wz(), 0.45, 0.0), 0.07 * chips))
            th = 0.69 - 0.035 * age * chips
            keep = G.rng(ch, th, th - 0.025)
            rim = G.math('MULTIPLY', G.rng(ch, th - 0.05, th - 0.025), G.rng(ch, th + 0.03, th))
            out = G.mix(keep, G.mix(0.35, wood, bare), pcol)
            out = G.mix(G.math('MULTIPLY', rim, 0.45), out, _shade(paint, 0.55))
        out = G.mix(G.math('MULTIPLY', crack, 0.7), out, '#2e2015')
        out = G.mix(G.math('MULTIPLY', G.edges(0.56, 0.66), 0.14 * age), out, '#ead9b6')           # aşınmış kenar
        out = _surface(G, out, age, salt, cavity, ground, moss)
        l.new(out, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_bark2(name='bark2', hexc='#7a5536', moss=0.5):
    """Kabuklu kütük: boyuna derin oluklar, sıcak kahve, gri liken lekeleri; kuzey/alt yüzde yosun; kesişme yerlerinde kir."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); o = G.obj()
        groove = G.vor(G.mapping(o, (10, 10, 1.6)), 2.2, 'DISTANCE_TO_EDGE')
        col = G.mix(G.rng(G.noise(o, 3, 4), 0.3, 0.7), _shade(hexc, 0.82), _shade(hexc, 1.18))
        col = G.mix(G.rng(groove, 0.07, 0.0, 0, 0.72), col, '#35210f')
        col = G.mix(G.rng(G.noise(o, 1.6, 4), 0.58, 0.7, 0, 0.3), col, '#a39d8c')
        col = G.mix(G.math('MULTIPLY', G.rng(G.vor(o, 9), 0.0, 0.1, 0.5, 0), G.rng(G.noise(o, 2.5), 0.55, 0.65)), col, '#c9c79a')   # liken
        nz = G.nz()
        mm = G.math('MULTIPLY', G.rng(nz, 0.25, 0.75, 0, moss), G.rng(G.noise(o, 3.5, 4), 0.48, 0.62))
        col = G.mix(mm, col, '#5b7f2e')
        col = _surface(G, col, 1.0, 0.0, 0.5, 0.3, 0.7)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_endgrain2(name='endgrain2'):
    """Kesik kütük yüzü: yıllık halkalar (iri, okunur), koyu öz, kenarda kabuk halkası, radyal çatlak; güneşte grileşmiş."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); o = G.obj()
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(G.mapping(o, (1, 1, 1)), sp.inputs[0])
        rr = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', sp.outputs['X'], sp.outputs['X']), G.math('MULTIPLY', sp.outputs['Y'], sp.outputs['Y'])))
        rn = G.math('ADD', rr, G.math('MULTIPLY', G.noise(o, 3.0, 3), 0.025))
        ring = G.math('SINE', G.math('MULTIPLY', rn, 95.0))
        col = G.mix(G.rng(ring, 0.3, 1.0, 0, 0.5), '#e4b97f', '#b07a42')
        col = G.mix(G.rng(rn, 0.05, 0.0, 0, 0.55), col, '#8a5a2c')
        ang = G.math('ARCTAN2', sp.outputs['Y'], sp.outputs['X'])
        crack = G.math('MULTIPLY', G.rng(G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', ang, 2.0))), 0.05, 0.0, 0, 1), G.rng(rr, 0.02, 0.06))
        col = G.mix(G.math('MULTIPLY', crack, 0.8), col, '#3a2414')
        col = G.mix(G.rng(G.noise(o, 2.0, 4), 0.5, 0.7, 0, 0.25), col, '#a8a092')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_moss2(name='moss2'):
    """Yosun öbeği: koyu dip, açık sarımsı-yeşil uçlar (yukarı bakan yüz), iri benekli ton dalgası."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); p = G.pos()
        col = G.mix(G.rng(G.noise(p, 9, 5), 0.35, 0.68), '#3c6a24', '#6d9a33')
        col = G.mix(G.rng(G.nz(), 0.3, 0.95, 0, 0.55), _shade('#3c6a24', 0.75), col)
        col = G.mix(G.rng(G.noise(p, 34, 3), 0.6, 0.7, 0, 0.6), col, '#a8c457')
        col = G.mix(G.rng(G.ao(0.08), 0.8, 0.4, 0, 0.5), col, '#2c4a1a')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_stone2(name='stone2', base=('#8b8478', '#a39b8e', '#bdb4a4'), lichen=0.8, moss=0.6):
    """Taş: sıcak gri dalga, koyu benek + ince çatlak, açık sarı-yeşil ve turuncu liken lekeleri, üstte yosun, oyukta kir."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); o = G.obj()
        rp = ramp(nt, list(zip((0.3, 0.5, 0.72), base))); l.new(G.noise(o, 2.4, 6), rp.inputs['Fac'])
        col = G.mix(G.rng(G.vor(o, 14), 0.0, 0.1, 0.35, 0), rp.outputs[0], '#5d574f')
        cr = G.math('MULTIPLY', G.rng(G.vor(G.mapping(o, (1, 1, 1)), 2.6, 'DISTANCE_TO_EDGE'), 0.016, 0.0, 0, 0.6), G.rng(G.noise(o, 2.5), 0.45, 0.6))
        col = G.mix(cr, col, '#3f3a35')
        lich = G.math('MULTIPLY', G.rng(G.vor(o, 6.5), 0.0, 0.16, 1, 0), G.rng(G.noise(o, 3.0, 3), 0.5, 0.62, 0, lichen))
        col = G.mix(lich, col, '#d6d39a')
        lich2 = G.math('MULTIPLY', G.rng(G.vor(G.mapping(o, (1.7, 1.7, 1.7)), 5.0), 0.0, 0.09, 1, 0), G.rng(G.noise(o, 2.2, 3), 0.62, 0.7, 0, lichen * 0.8))
        col = G.mix(lich2, col, '#d99a4a')
        mm = G.math('MULTIPLY', G.rng(G.math('ADD', G.nz(), G.math('MULTIPLY', G.noise(o, 3.5, 4), 0.6)), 1.0, 1.25, 0, moss), 1.0)
        col = G.mix(mm, col, '#5f8a30')
        col = _surface(G, col, 1.0, 0.0, 0.5, 0.25, 0.6)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_tile2(hexc, name, age=1.0, moss=0.6):
    """Kiremit: ton dalgası, güneş yanığı açık lekeler, alt kenarda koyu nem, oyukta yosun + kir, yer yer tuz kabuğu."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); o = G.obj(); p = G.pos()
        rp = ramp(nt, [(0.3, _shade(hexc, 0.86)), (0.5, hexc), (0.72, _shade(hexc, 1.1))]); l.new(G.noise(o, 1.2, 4), rp.inputs['Fac'])
        col = G.mix(0.25, rp.outputs[0], G.noise(o, 22, 3, out='Color'), 'OVERLAY')
        col = G.mix(G.rng(G.noise(p, 1.6, 4), 0.58, 0.74, 0, 0.32 * age), col, _shade(hexc, 1.28))     # güneş yanığı
        col = G.mix(G.math('MULTIPLY', G.edges(0.55, 0.65), 0.25 * age), col, '#f2c6a8')             # kırık kenar
        occl = G.ao(0.12)
        col = G.mix(G.rng(occl, 0.8, 0.35, 0, 0.55), col, '#4b3022')
        mm = G.math('MULTIPLY', G.rng(occl, 0.85, 0.5, 0, moss), G.rng(G.noise(p, 3.5, 4), 0.45, 0.6))
        col = G.mix(mm, col, '#5f8a30')
        sl = G.math('MULTIPLY', G.rng(G.noise(p, 2.2, 4), 0.66, 0.74), 0.3 * age)
        col = G.mix(sl, col, '#ece4d2')                                                                    # tuz kabuğu (seyrek, iri)
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_sand2(name='sand2', hexc='#e2c08a'):
    """Kum birikintisi: rüzgâr dalgacıkları (bükülmüş şerit), açık tepe / koyu ıslak dip, kabuk kırıntısı benekleri."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); p = G.pos()
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(p, sp.inputs[0])
        rip = G.math('SINE', G.math('MULTIPLY', G.math('ADD', G.math('ADD', sp.outputs['X'], G.math('MULTIPLY', sp.outputs['Y'], 0.4)),
                                                         G.math('MULTIPLY', G.noise(p, 1.5, 3), 0.5)), 26.0))
        col = G.mix(G.rng(rip, -0.4, 1.0, 0, 0.35), _shade(hexc, 0.9), _shade(hexc, 1.08))
        col = G.mix(G.rng(G.noise(p, 5, 4), 0.35, 0.7, 0, 0.5), col, _shade(hexc, 0.85))
        col = G.mix(G.rng(G.wz(), 0.05, 0.0, 0, 0.35), col, '#b08a5a')
        col = G.mix(G.rng(G.vor(p, 60), 0.0, 0.06, 0.7, 0), col, '#fbf3e3')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


def m_net(name='net', hexc='#5d7d86', bg='#3a4d52'):
    """Toplu duran balık ağı: eşkenar dörtgen ilmek çizgileri (iki çapraz şerit), arası koyu (ağın içi), lifli ton."""
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links; G = G2(nt); o = G.obj()
        sp = n.new('ShaderNodeSeparateXYZ'); l.new(o, sp.inputs[0])
        def band(ax, ay):
            v = G.math('ADD', G.math('MULTIPLY', sp.outputs['X'], ax), G.math('MULTIPLY', sp.outputs['Z'], ay))
            v = G.math('ADD', v, G.math('MULTIPLY', sp.outputs['Y'], 0.6))
            return G.rng(G.math('ABSOLUTE', G.math('SINE', G.math('MULTIPLY', v, 38.0))), 0.25, 0.08)
        m = G.math('MAXIMUM', band(1, 1), band(1, -1))
        col = G.mix(m, bg, G.mix(G.rng(G.noise(o, 6), 0.3, 0.7), hexc, _shade(hexc, 1.3)))
        col = G.mix(G.rng(G.noise(o, 2.0, 3), 0.55, 0.7, 0, 0.3), col, '#c9b98e')
        l.new(col, bsdf.inputs['Base Color'])
    return nodes_mat(name, b)


# ------------------------------------------------------------------ parçalar

def _mesh(name, verts, faces, m, smooth_on=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    if m: o.data.materials.append(m)
    me.polygons.foreach_set('use_smooth', [smooth_on] * len(me.polygons))
    return o


def _orient(o, loc, nrm=(0, 0, 1), yaw=0.0):
    q = V(nrm).normalized().to_track_quat('Z', 'Y')
    o.rotation_mode = 'QUATERNION'
    from mathutils import Quaternion
    o.rotation_quaternion = q @ Quaternion((0, 0, 1), math.radians(yaw))
    o.location = loc
    return o


def moss_clump(loc, r, seed=0, nrm=(0, 0, 1), squash=0.42, lumps=3, m=None):
    """Yosun öbeği: üst üste binen 2–4 yumru (gürültüyle bozulmuş basık küre), yüzeye yaslanır. Adı 'moss' (decim tablosu)."""
    R = random.Random(seed); M = m or MOSS()
    bm = bmesh.new()
    for k in range(lumps):
        off = V((R.uniform(-0.6, 0.6) * r, R.uniform(-0.6, 0.6) * r, 0)) if k else V((0, 0, 0))
        rr = r * (1.0 if k == 0 else R.uniform(0.5, 0.8))
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for v in res['verts']:
            d = v.co.copy()
            if d.z < -0.15: d.z = -0.15 + (d.z + 0.15) * 0.2
            kk = 1.0 + 0.22 * MN.noise(d * 2.4 + V((seed * 3.1 + k, 0, 0))) + 0.08 * MN.noise(d * 7 + V((0, seed, k)))
            v.co = off + V((d.x * rr * kk, d.y * rr * kk, d.z * rr * squash * kk))
    o = link_mesh('moss', bm, [M]); smooth(o)
    return _orient(o, loc, nrm, R.uniform(0, 360))


def starfish(loc, r, yaw=0.0, nrm=(0, 0, 1), hexc='#f07a4a', name='starfish'):
    """Deniz yıldızı: beş kalın, uca doğru incelen kol (kubbeli sırt), sırtta açık benekler (malzeme)."""
    M = _star_mat(hexc)
    N = 50; rings = 4; verts = []; faces = []
    def rad(a): return r * (0.36 + 0.64 * abs(math.cos(2.5 * a)) ** 1.8)
    top = []
    for i in range(rings + 1):
        t = i / rings; row = []
        for j in range(N):
            a = j / N * 2 * math.pi; rr = rad(a) * t
            h = r * 0.2 * (1 - t ** 2) ** 0.6 * (0.55 + 0.45 * rad(a) / r)
            row.append(len(verts)); verts.append((math.cos(a) * rr, math.sin(a) * rr, h))
        top.append(row)
    bot = len(verts); verts.append((0, 0, 0.0))
    for i in range(rings):
        for j in range(N):
            j2 = (j + 1) % N
            if i == 0: faces.append((top[0][j], top[1][j], top[1][j2]))
            else: faces.append((top[i][j], top[i + 1][j], top[i + 1][j2], top[i][j2]))
    for j in range(N):
        j2 = (j + 1) % N; faces.append((bot, top[rings][j2], top[rings][j]))
    o = _mesh(name, verts, faces, M)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return _orient(o, loc, nrm, yaw)


_MATS = {}
def _star_mat(hexc):
    k = ('star', hexc)
    if k in _MATS: return _MATS[k]
    def b(nt, bsdf):
        G = G2(nt); o = G.obj()
        col = G.mix(G.rng(G.noise(o, 6, 3), 0.3, 0.7), _shade(hexc, 0.88), _shade(hexc, 1.1))
        col = G.mix(G.rng(G.vor(o, 70), 0.0, 0.2, 0.8, 0), col, '#ffe2b8')
        nt.links.new(col, bsdf.inputs['Base Color'])
    _MATS[k] = nodes_mat('starfish' + hexc, b); return _MATS[k]


def shell(loc, r, yaw=0.0, nrm=(0, 0, 1), hexc='#f6d9c4', band='#e59a8a', name='shell'):
    """Tarak kabuğu: yelpaze gövde (dalgalı kaburgalar), menteşe kulakçıkları, büyüme halkası bantları."""
    def b(nt, bsdf):
        G = G2(nt); o = G.obj(); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(o, sp.inputs[0])
        rr = G.math('SQRT', G.math('ADD', G.math('MULTIPLY', sp.outputs['X'], sp.outputs['X']), G.math('MULTIPLY', sp.outputs['Y'], sp.outputs['Y'])))
        bands = G.rng(G.math('SINE', G.math('MULTIPLY', rr, 9.0 / r)), 0.2, 0.8, 0, 0.6)
        col = G.mix(bands, hexc, band)
        col = G.mix(G.rng(G.noise(o, 18), 0.6, 0.7, 0, 0.3), col, '#fff8ee')
        nt.links.new(col, bsdf.inputs['Base Color'])
    M = _MATS.get(('shell', hexc, band)) or nodes_mat('shell' + hexc, b); _MATS[('shell', hexc, band)] = M
    NA, NR = 20, 5; verts = []; faces = []; rows = []
    for i in range(NR + 1):
        t = i / NR; row = []
        for j in range(NA + 1):
            a = math.radians(-62 + 124 * j / NA)
            rib = 0.06 * r * abs(math.sin(j * math.pi / 2.0)) * t
            h = r * 0.32 * (1 - t ** 2) ** 0.5 * (1 - 0.3 * (abs(a) / 1.1) ** 2) + rib
            row.append(len(verts)); verts.append((math.sin(a) * r * t, math.cos(a) * r * t - r * 0.35, h))
        rows.append(row)
    for i in range(NR):
        for j in range(NA):
            faces.append((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    c = len(verts); verts.append((0, 0.02 * r - r * 0.35, 0.0))
    ring = rows[NR]
    for j in range(NA): faces.append((c, ring[j + 1], ring[j]))
    o = _mesh(name, verts, faces, M)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    for sx in (-1, 1):   # kulakçık
        e = rbox('shell', (sx * r * 0.16, -r * 0.37, r * 0.03), (r * 0.26, r * 0.14, r * 0.05), M, bevel=r * 0.02)
        e.parent = o
    _orient(o, loc, nrm, yaw); bpy.context.view_layer.update()
    for ch in list(o.children):
        mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
    return o


def buoy(loc, r, c1='#f0663a', c2='#f6efe0', name='buoy'):
    """Şamandıra (ağ yüzdürücüsü): yumurta biçimi, ortada açık renk bant (solmuş, lekeli). Doku koordinatı nesnenin kendi birim
    küresinde (blob ölçeği nesnede)."""
    def b(nt, bsdf):
        G = G2(nt); o = G.obj()
        sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(o, sp.inputs[0])
        bnd = G.rng(G.math('ABSOLUTE', sp.outputs['Z']), 0.22, 0.3)
        col = G.mix(bnd, c2, c1)
        col = G.mix(G.rng(G.noise(o, 2.0, 4), 0.52, 0.72, 0, 0.35), col, '#fff1d8')
        col = G.mix(G.rng(G.noise(o, 6.0, 4), 0.62, 0.72, 0, 0.45), col, '#6a5844')
        nt.links.new(col, bsdf.inputs['Base Color'])
    M = nodes_mat(name + c1, b)
    return blob(name, loc, (r, r, r * 1.2), M, sub=1, seg=16)


def sand_drift(cx, cy, rx, ry, h, seed=0, lean=(0.0, 0.0), m=None, name='sand', z0=0.0):
    """Kum birikintisi: yere yapışık alçak tümsek (kenarı yırtık), lean yönünde yığılmış (duvar/basamak dibine rüzgârla dolmuş)."""
    M = m or SAND()
    NR, NA = 4, 22; verts = []; faces = []; rows = []
    for i in range(NR + 1):
        t = i / NR; row = []
        for j in range(NA):
            a = j / NA * 2 * math.pi
            k = 1 + 0.22 * MN.noise(V((math.cos(a) * 1.6, math.sin(a) * 1.6, seed))) + 0.08 * MN.noise(V((math.cos(a) * 5, math.sin(a) * 5, seed + 2)))
            x = math.cos(a) * rx * k * t; y = math.sin(a) * ry * k * t
            bias = 1 + lean[0] * (x / max(rx, 1e-3)) + lean[1] * (y / max(ry, 1e-3))
            z = h * max(0.0, (1 - t * t)) ** 1.4 * max(0.2, bias) + 0.004
            z += 0.012 * MN.noise(V((x * 4, y * 4, seed)))  * (1 - t)
            row.append(len(verts)); verts.append((cx + x, cy + y, z0 + max(0.004, z)))
        rows.append(row)
    c = len(verts); verts.append((cx, cy, z0 + h + 0.004))
    for j in range(NA): faces.append((c, rows[0][j], rows[0][(j + 1) % NA]))
    for i in range(NR):
        for j in range(NA):
            j2 = (j + 1) % NA; faces.append((rows[i][j], rows[i + 1][j], rows[i + 1][j2], rows[i][j2]))
    o = _mesh(name, verts, faces, M)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(o.data); bm.free()
    return o


def iron_strap(p, along, nrm, length, width=0.05, m=None, nails=2, name='strap'):
    """Paslı demir kuşak: yüzeye yatık ince levha + çivi (pas akıntılı)."""
    M = m or IRON()
    p = V(p); a = V(along).normalized(); n = V(nrm).normalized(); s = n.cross(a).normalized()
    o = rbox(name, (0, 0, 0), (length, width, 0.008), M, bevel=0.003)
    from mathutils import Matrix
    mat3 = Matrix((a, s, n)).transposed()
    o.matrix_world = Matrix.Translation(p + n * 0.004) @ mat3.to_4x4()
    for k in range(nails):
        t = (k + 0.5) / nails - 0.5
        AT.nail(tuple(p + a * (t * length * 0.8) + n * 0.008), tuple(n), M, streak=abs(n.z) < 0.5)
    return o


def rope3(pts, thick, m=None, closed=False, seg=None, around=9, twist=2.4, name='rope'):
    """Hafif halat: TEK tüp, kesiti üç loblu ve boy boyunca burgulu (üç kollu halat görünümü); strand_rope'un üç ayrı tüpünden
    ~4 kat ucuz. pts kaba çizgi (kendi içinde sıklaştırılır); closed → halka (çatı kuşağı). grain UV: u = boy (m), v = çevre (0..1)."""
    M = m or ROPE()
    P = [V(p) for p in pts]
    if closed: P = P + [P[0]]
    seg = seg or thick * 2.2
    dense = []
    for i in range(len(P) - 1):
        L = (P[i + 1] - P[i]).length; n = max(1, int(math.ceil(L / seg)))
        for k in range(n): dense.append(P[i].lerp(P[i + 1], k / n))
    if not closed: dense.append(P[-1])
    N = len(dense)
    acc = [0.0]
    for i in range(1, N): acc.append(acc[-1] + (dense[i] - dense[i - 1]).length)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('grain'); rings = []
    prev_n = None
    for i, c in enumerate(dense):
        a = dense[(i + 1) % N] if closed else dense[min(i + 1, N - 1)]
        b = dense[(i - 1) % N] if closed else dense[max(i - 1, 0)]
        t = (a - b).normalized()
        if prev_n is None:
            nx = t.cross(V((0, 0, 1)));
            if nx.length < 1e-3: nx = t.cross(V((1, 0, 0)))
            nx.normalize()
        else:
            nx = (prev_n - t * prev_n.dot(t)).normalized()          # paralel taşıma: kesit dönmesin
        prev_n = nx; ny = t.cross(nx).normalized()
        ph = acc[i] / thick * twist
        ring = []
        for j in range(around):
            th = j / around * 2 * math.pi
            rr = thick * (0.8 + 0.2 * math.cos(3 * th - ph))
            ring.append(bm.verts.new(c + (nx * math.cos(th) + ny * math.sin(th)) * rr))
        rings.append(ring)
    nr = len(rings); last = nr if closed else nr - 1
    for i in range(last):
        r0, r1 = rings[i], rings[(i + 1) % nr]
        u0, u1 = acc[i], acc[i] + (dense[(i + 1) % N] - dense[i]).length
        for j in range(around):
            j2 = (j + 1) % around
            f = bm.faces.new((r0[j], r0[j2], r1[j2], r1[j]))
            for lp, uv in zip(f.loops, ((u0, j / around), (u0, (j + 1) / around), (u1, (j + 1) / around), (u1, j / around))): lp[uvl].uv = uv
    if not closed:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            for lp in f.loops: lp[uvl].uv = (0.0, 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = link_mesh(name, bm, [M]); smooth(o)
    return o


def post_center(base, top, seed, z):
    """AT.post direğinin z yüksekliğindeki ekseni (x, y): taban–orta–tepe noktalarından ikinci derece yaklaşık (orta nokta gürültüyle
    kayık; halat bağ direği tam sarsın diye)."""
    b = V(base); t = V(top)
    m = (b + t) / 2 + V((MN.noise(V((seed, 1, 2))) * 0.04, MN.noise(V((2, seed, 1))) * 0.04, 0))
    u = (z - b.z) / (t.z - b.z)
    p = b * (1 - u) * (1 - 2 * u) + m * 4 * u * (1 - u) + t * u * (2 * u - 1)
    return p.x, p.y


def lash(center, r, z0, z1, turns, thick=0.012, axis='z', seed=0, m=None, tail=True):
    """Direğe/dala sarılmış halat bağ (rope_wrap gibi ama rope3 ile): sarmal + uçta kısa sarkan kuyruk."""
    pts = []; n = max(8, int(turns * 14))
    for i in range(n + 1):
        t = i / n; a = t * turns * 2 * math.pi + seed
        q = V((math.cos(a) * r, math.sin(a) * r, z0 + (z1 - z0) * t))
        if axis == 'x': q = V((z0 + (z1 - z0) * t, math.cos(a) * r, math.sin(a) * r))
        elif axis == 'y': q = V((math.cos(a) * r, z0 + (z1 - z0) * t, math.sin(a) * r))
        pts.append(V(center) + q)
    if tail:
        a = turns * 2 * math.pi + seed; e = pts[-1]
        out = V((math.cos(a), math.sin(a), 0)) if axis == 'z' else V((0, 0, 0))
        pts += [e + out * 0.03 + V((0, 0, -0.05)), e + out * 0.04 + V((0, 0, -0.12))]
    return rope3(pts, thick, m, seg=thick * 2.6, around=6)


def patch_plank(loc, size, rot, m, nail_nrm, seed=0):
    """Sonradan çakılmış yama tahta (farklı ton) + köşelerinde çivi."""
    o = AT.plank('patch', loc, size, m, rot=rot, seed=seed, amt=0.004)
    n = V(nail_nrm).normalized()
    L = max(size); ax = 0 if size[0] == L else (1 if size[1] == L else 2)
    d = V((1 if ax == 0 else 0, 1 if ax == 1 else 0, 1 if ax == 2 else 0))
    from mathutils import Euler
    d = Euler([math.radians(x) for x in rot]).to_matrix() @ d
    for sgn in (-1, 1):
        AT.nail(tuple(V(loc) + d * (sgn * L * 0.38) + n * (min(sz for sz in size) * 0.5)), tuple(n), streak=(sgn > 0))
    return o


# ortak malzeme önbelleği (her betik reset'ten sonra yeniden kurar)
_C = {}
def _cached(k, fn):
    m = _C.get(k)
    if m is None or m.name not in bpy.data.materials: m = fn(); _C[k] = m
    return m
def MOSS(): return _cached('moss', lambda: m_moss2())
def SAND(): return _cached('sand', lambda: m_sand2())
def IRON(): return _cached('iron', lambda: AT.m_metal('#4a4650', '#b0622e', name='iron2', age=1.3))
def ROPE(): return _cached('rope', lambda: AT.m_rope('#c9a46c', 'rope2', age=1.1))


def flowers_at(spots, R, size=1.0):
    """Küçük çiçekler (assets_v3.flower_heads gibi: sap + 5 taç yaprak + göbek) ama sap verilen yükseklikten başlar
    (çiçek kasası, saksı): spots = [(x, y, z_dip, boy)]."""
    ST = m_flat('#469c3a', 0.15, 6, 'stem'); CY = m_flat('#ffc93a', 0.15, 12, 'fcenter')
    PET = [m_flat('#ff7aa8', 0.12, 9, 'p_pink'), m_flat('#fff6ea', 0.08, 9, 'p_wht'), m_flat('#b78cff', 0.12, 9, 'p_pur'), m_flat('#ffd447', 0.1, 9, 'p_yel')]
    for k, (x, y, z0, h) in enumerate(spots):
        head = V((x, y, z0 + h)); base = V((x, y, z0))
        tube('stem', [tuple(base), tuple((base + head) / 2 + V((0.01, 0, 0))), tuple(head)], [0.012, 0.01, 0.009], ST, res=2)
        pm = PET[(k + R.randint(0, 3)) % len(PET)]; sz = R.uniform(0.9, 1.2) * size
        blob('fc', tuple(head + V((0, 0, 0.012 * size))), (0.032 * sz, 0.032 * sz, 0.022 * sz), CY, sub=0, seg=8)
        for j in range(5):
            b = j * 2 * math.pi / 5 + k
            blob('pet', tuple(head + V((math.cos(b) * 0.055 * sz, math.sin(b) * 0.055 * sz, -0.004))), (0.048 * sz, 0.03 * sz, 0.012 * sz), pm,
                 rot=(0, 0, math.degrees(b)), sub=0, seg=8)


def leaf_recolor(objs_prefix, mat):
    """Hazır yapıcıdan gelen yaprak nesnelerinin malzemesini değiştir (ör. palmiye yaprağı daha derin yeşil, neon değil)."""
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o.name.split('.')[0] in objs_prefix:
            o.data.materials.clear(); o.data.materials.append(mat)


# ------------------------------------------------------------------ önizleme + komut satırı

def scene_bounds(objs=None):
    lo = V((1e9,) * 3); hi = V((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs or bpy.context.scene.objects:
        if o.type != 'MESH': continue
        e = o.evaluated_get(dg); me = e.to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co; lo = V(map(min, lo, w)); hi = V(map(max, hi, w))
        e.to_mesh_clear()
    return lo, hi


def draft(png, yaw=35.0, pitch=24.0, size=(900, 700), samples=40, dist=None):
    """Yüksek ayrıntılı taslağın (pişirmesiz, prosedürel malzemelerle) Cycles çizimi: tasarım denemesi için hızlı bakış."""
    lo, hi = scene_bounds(); ctr = (lo + hi) / 2; r = (hi - lo).length * 0.5; d = dist or r * 2.6
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = size
    cam = bpy.data.cameras.get('dcam') or bpy.data.cameras.new('dcam'); cam.lens = 50
    co = bpy.data.objects.get('dcam')
    if co is None: co = bpy.data.objects.new('dcam', cam); sc.collection.objects.link(co)
    sc.camera = co
    yr, pr = math.radians(yaw), math.radians(pitch)
    co.location = ctr + V((math.sin(yr) * math.cos(pr) * d, -math.cos(yr) * math.cos(pr) * d, math.sin(pr) * d))
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)


def stats(high, decim, weights):
    """Hedef ağın (pişirmeden önce, gizli yüz silinmeden) nesne anahtarına göre üçgen dağılımı."""
    import collections, re
    low = BK.build_low(high, decim, weights); acc = collections.Counter()
    for o in low:
        acc[re.sub(r'\.\d+$', '', o.name[:-4])] += sum(len(p.vertices) - 2 for p in o.data.polygons)
    print('HEDEF toplam (gizli yüz silinmeden)', sum(acc.values()), flush=True)
    for k, n in acc.most_common(45): print('   ', k, n, flush=True)


def main(name, build, decim, weights, cap, **kw):
    """Komut satırı: <betik> -- <çıktı> [ad] [--draft <png>] [--stats]
    --draft: yüksek modelin önden ve arkadan çizimi (<png> ve <png>_b.png); --stats: hedef üçgen dağılımı; yoksa pişir + dışa aktar.
    export_game.py çağrısı: -- <çıktı> <ad> (POFI_TARGET üçgen üst sınırı, POFI_TEX doku boyu)."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = args[0] if args else os.path.join('/tmp', name)
    kit.reset(); _C.clear(); _MATS.clear()
    build()
    high = BK.prepare()
    if '--draft' in args:
        png = args[args.index('--draft') + 1]
        draft(png, 35, 24); draft(png[:-4] + '_b.png', 200, 24)
        lo, hi = scene_bounds(); print('TASLAK sınır', tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi), flush=True)
        return
    if '--stats' in args:
        stats(high, decim, weights); return
    budget = int(os.environ.get('POFI_TARGET', '0') or 0) or cap
    BK.bake(out, name, high, decim=decim, weights=weights, tex=1024, budget=budget, **kw)
