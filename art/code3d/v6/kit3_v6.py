# v6 Tapınak (22 Ekim 2026, kullanıcı madde 8 + örnek görsel): uzak doğu tarzı tapınak avlusu — çimenli taş teraslar ve basamaklar,
# ucu kalkık kiremit çatılı ana salon, 4 katlı pagoda, yan yapı, dalgalı kiremit başlıklı avlu duvarı, dikili taş bahçesi,
# pembe çiçekli ağaç, kırmızı fenerler. Hepsi kodla özgün (örnek yalnız hava/yerleşim hedefi).
import bpy, math, random
import numpy as np
from mathutils import Vector as V, noise as MN
import kit_v6 as K
import kit2_v6 as K2
from kit_v6 import srgb, mesh_obj, _mat

def c3(h): return np.array(srgb(h))

def vmat(name, rough=0.7, bump=0.15, bscale=25):
    return K2.vc_mat(name, rough=rough, bump=bump, bscale=bscale)

# ------------------------------------------------------------------ kutu (köşe rengi fonksiyonlu)

def box(name, x0, x1, y0, y1, z0, z1, colf, mat, col=None, seg=(1, 1, 1)):
    """Eksene hizalı kutu; colf(p, n) → renk. seg: x,y,z bölme (renk bandı için)."""
    V_, F_, C_ = [], [], []
    def quad_grid(o, du, dv, nu, nv, nrm):
        b = len(V_)
        for j in range(nv + 1):
            for i in range(nu + 1):
                p = o + du * (i / nu) + dv * (j / nv); V_.append(tuple(p)); C_.append(colf(p, nrm))
        for j in range(nv):
            for i in range(nu):
                a = b + j * (nu + 1) + i; F_.append((a, a + 1, a + nu + 2, a + nu + 1))
    sx, sy, sz = seg
    quad_grid(V((x0, y0, z0)), V((x1 - x0, 0, 0)), V((0, 0, z1 - z0)), sx, sz, V((0, -1, 0)))
    quad_grid(V((x1, y1, z0)), V((x0 - x1, 0, 0)), V((0, 0, z1 - z0)), sx, sz, V((0, 1, 0)))
    quad_grid(V((x1, y0, z0)), V((0, y1 - y0, 0)), V((0, 0, z1 - z0)), sy, sz, V((1, 0, 0)))
    quad_grid(V((x0, y1, z0)), V((0, y0 - y1, 0)), V((0, 0, z1 - z0)), sy, sz, V((-1, 0, 0)))
    quad_grid(V((x0, y0, z1)), V((x1 - x0, 0, 0)), V((0, y1 - y0, 0)), sx, sy, V((0, 0, 1)))
    o = mesh_obj(name, V_, F_, mat, colors=np.array(C_), col=col, smooth=False)
    return o

# ------------------------------------------------------------------ ucu kalkık kiremit çatı

def roof(name, cx, cy, z, w, d, h, over=0.9, curl=0.6, ridge=0.45, tile='terra', col=None, mat=None, res=56):
    """Kalçalı-beşik çatı: içbükey yamaçlar, saçak köşeleri kalkık; yamaç boyunca kiremit sıraları (köşe rengi oluk çizgileri),
    altta kalınlık + koyu saçak altı; mahya ve kalça sırtlarında yuvarlak kiremit başlıklar, uçlarında kıvrık süs."""
    W, D = w / 2 + over, d / 2 + over; rr = ridge
    pal = {'terra': ('#b9553d', '#7d3125', '#d27552'), 'grey': ('#75717a', '#4a4750', '#918d96')}[tile]
    base, groove, lite = c3(pal[0]), c3(pal[1]), c3(pal[2])
    V_, F_, C_ = [], [], []
    def surf(u, v):
        ax, ay = abs(u), abs(v)
        t = max(ay, (ax - rr) / (1 - rr) if ax > rr else 0.0)            # mahyadan saçağa 0..1
        zz = h * (1 - t) ** 1.7                                          # içbükey yamaç
        zz += curl * (max(0, ax - 0.75) / 0.25) ** 2.2 * (max(0, ay - 0.75) / 0.25) ** 2.2 * 1.0   # köşe kalkışı
        zz += curl * 0.35 * (max(ax, ay) ** 8)                              # saçak boyunca hafif kalkış
        return V((cx + u * W, cy + v * D, z + zz)), t, ax, ay
    n = res
    for j in range(n + 1):
        for i in range(n + 1):
            u = -1 + 2 * i / n; v = -1 + 2 * j / n; p, t, ax, ay = surf(u, v); V_.append(tuple(p))
            side = ay >= (ax - rr) / (1 - rr)                               # ön/arka yamaç mı
            coord = u * W if side else v * D
            g = 0.5 + 0.5 * math.cos(coord / 0.32 * math.tau)
            c = base * (0.92 + 0.12 * MN.noise(V((u * 9, v * 9, 3))))
            c = c + (groove - c) * (g ** 6) * 0.9 + (lite - c) * max(0, 1 - g * 3) * 0.0
            c = c + (lite - c) * 0.25 * (1 - t)
            C_.append(c)
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i; F_.append((a, a + 1, a + n + 2, a + n + 1))
    # kalınlık: saçak kenarından aşağı şerit + alt yüz (koyu ahşap)
    b0 = len(V_); edge = []
    for k in range(4 * n):
        s = k / n
        if s < 1: u, v = -1 + 2 * s, -1
        elif s < 2: u, v = 1, -1 + 2 * (s - 1)
        elif s < 3: u, v = 1 - 2 * (s - 2), 1
        else: u, v = -1, 1 - 2 * (s - 3)
        p, _, _, _ = surf(u, v); edge.append(p)
    for p in edge: V_.append(tuple(p)); C_.append(c3('#5a2a1e'))
    for p in edge: V_.append(tuple(p - V((0, 0, 0.28)))); C_.append(c3('#3a1c14'))
    m4 = 4 * n
    for k in range(m4):
        a = b0 + k; b = b0 + (k + 1) % m4; F_.append((a, b, b + m4, a + m4))
    ctr = len(V_); V_.append((cx, cy, z - 0.1)); C_.append(c3('#2e1812'))
    for k in range(m4): F_.append((b0 + m4 + (k + 1) % m4, b0 + m4 + k, ctr))
    o = mesh_obj(name, V_, F_, mat or roof_mat(name + '_m'), colors=np.array(C_), col=col)
    # sırtlar
    rm = vmat(name + '_r', 0.5, 0.1)
    rpts = [surf(u, 0)[0] + V((0, 0, 0.12)) for u in np.linspace(-rr, rr, 8)]
    K2.lathe(name + '_ridge', rpts, lambda t, a: 0.18, res=10, mat=rm, col=col, colfun=lambda t, a, q: groove * 1.1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            hp = [surf(sx * (rr + (1 - rr) * s), sy * s)[0] + V((0, 0, 0.1)) for s in np.linspace(0, 1, 12)]
            K2.lathe(name + '_hip', hp, lambda t, a: 0.13, res=8, mat=rm, col=col, colfun=lambda t, a, q: groove * 1.1)
            tip = hp[-1]; K2.lathe(name + '_curl', [tip, tip + V((sx * 0.25, sy * 0.25, 0.35)), tip + V((sx * 0.18, sy * 0.18, 0.6))], lambda t, a: 0.11 * (1 - 0.6 * t), res=8, mat=rm, col=col, colfun=lambda t, a, q: groove)
    for sx in (-1, 1):   # mahya uç süsleri
        p = surf(sx * rr, 0)[0] + V((0, 0, 0.1)); K2.lathe(name + '_orn', [p, p + V((sx * 0.1, 0, 0.5)), p + V((-sx * 0.15, 0, 0.85))], lambda t, a: 0.12 * (1 - 0.5 * t), res=8, mat=rm, col=col, colfun=lambda t, a, q: groove)
    return o


# ------------------------------------------------------------------ eskitilmiş malzemeler (kullanıcı notu: derinlik, gölge, damar, yıpranma, iz)

def _nodes(m):
    nt = m.node_tree; return nt.nodes, nt.links
def _mr(N, L, sock, a, b, c=0.0, d=1.0):
    n = N.new('ShaderNodeMapRange'); n.inputs[1].default_value = a; n.inputs[2].default_value = b; n.inputs[3].default_value = c; n.inputs[4].default_value = d; L.new(sock, n.inputs[0]); return n.outputs[0]
def _mix(N, L, fac, a, b, blend='MIX'):
    n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = blend
    for slot, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, (int, float)): n.inputs[slot].default_value = v
        elif isinstance(v, tuple): n.inputs[slot].default_value = v
        else: L.new(v, n.inputs[slot])
    return n.outputs[2]
def _math(N, L, op, a, b=None):
    n = N.new('ShaderNodeMath'); n.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: L.new(v, n.inputs[i])
    return n.outputs[0]
def _ao_edge(N, L, ao_dist=0.6, edge_r=0.03):
    """Oyuk koyuluğu (yerel AO) ve kenar parıltısı maskesi (bevel normali ile asıl normal farkı)."""
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.only_local = True; ao.inputs['Distance'].default_value = ao_dist
    geo = N.new('ShaderNodeNewGeometry'); bv = N.new('ShaderNodeBevel'); bv.samples = 6; bv.inputs['Radius'].default_value = edge_r
    dt = N.new('ShaderNodeVectorMath'); dt.operation = 'DOT_PRODUCT'; L.new(bv.outputs[0], dt.inputs[0]); L.new(geo.outputs['Normal'], dt.inputs[1])
    return ao.outputs['AO'], _mr(N, L, dt.outputs['Value'], 0.995, 0.9)

def plaster_mat(name, z0, hgt):
    """Sıva: köşe rengi + yukarıdan inen yağmur izleri (z'de uzamış gürültü), dipte toprak/kir sıçraması, yer yer dökülmüş sıva
    altından tuğla tonu, oyuklarda AO koyuluğu; ince sıva tümseği."""
    m, b = None, None
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _nodes(m); b = N['Principled BSDF']
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (2.2, 2.2, 0.25); L.new(tc.outputs['Object'], mp.inputs[0])
    st = N.new('ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 2.5; st.inputs['Detail'].default_value = 4; L.new(mp.outputs[0], st.inputs['Vector'])
    rel = _mr(N, L, sep.outputs['Z'], z0 + hgt, z0 + hgt * 0.35)              # tepeden aşağı izler incelir
    streak = _math(N, L, 'MULTIPLY', _mr(N, L, st.outputs['Fac'], 0.52, 0.68), rel)
    c = _mix(N, L, _math(N, L, 'MULTIPLY', streak, 0.45), vc.outputs['Color'], srgb('#6e6152') + (1,))
    dirt = _mr(N, L, sep.outputs['Z'], z0 + 0.9, z0 + 0.05)
    dn = N.new('ShaderNodeTexNoise'); dn.inputs['Scale'].default_value = 9; dn.inputs['Detail'].default_value = 5; L.new(tc.outputs['Object'], dn.inputs['Vector'])
    c = _mix(N, L, _math(N, L, 'MULTIPLY', dirt, _mr(N, L, dn.outputs['Fac'], 0.3, 0.7, 0.35, 0.8)), c, srgb('#5a4b3a') + (1,))
    pn = N.new('ShaderNodeTexNoise'); pn.inputs['Scale'].default_value = 1.6; pn.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], pn.inputs['Vector'])
    chip = _math(N, L, 'MULTIPLY', _mr(N, L, pn.outputs['Fac'], 0.71, 0.73), 0.85)
    br = N.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 3.0; br.inputs['Color1'].default_value = srgb('#a4573f') + (1,); br.inputs['Color2'].default_value = srgb('#8a4632') + (1,); br.inputs['Mortar'].default_value = srgb('#b8a48a') + (1,)
    br.inputs['Mortar Size'].default_value = 0.02; L.new(tc.outputs['Object'], br.inputs['Vector'])
    c = _mix(N, L, chip, c, br.outputs['Color'])
    ao, edge = _ao_edge(N, L, 0.8)
    c = _mix(N, L, _mr(N, L, ao, 0.2, 1.0, 0.55, 0.0), c, srgb('#3a2e28') + (1,))
    L.new(c, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.9
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35; bump.inputs['Distance'].default_value = 0.02
    L.new(_math(N, L, 'ADD', dn.outputs['Fac'], _math(N, L, 'MULTIPLY', chip, -1.5)), bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def wood_mat(name, paint=None, grain_axis='Z', scale=3.0, age=0.5):
    """Ahşap: boyuna damar (dalga + gürültü), budak; kenarlarda aşınmış açık ton, çizik; paint verilirse kırmızı/koyu boya,
    aşınmış yerlerden ahşap görünür. Oyuklarda AO koyuluğu, damar tümseği."""
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _nodes(m); b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = {'Z': (6.0, 6.0, 0.35), 'X': (0.35, 6.0, 6.0), 'Y': (6.0, 0.35, 6.0)}[grain_axis]
    L.new(tc.outputs['Object'], mp.inputs[0])
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 9; wv.inputs['Detail'].default_value = 4
    wv.inputs['Detail Scale'].default_value = 2.0; L.new(mp.outputs[0], wv.inputs['Vector'])
    gr = N.new('ShaderNodeValToRGB'); cr = gr.color_ramp; cr.elements[0].position = 0.2; cr.elements[0].color = srgb('#4f3220') + (1,); cr.elements[1].position = 0.85; cr.elements[1].color = srgb('#a27350') + (1,)
    e = cr.elements.new(0.55); e.color = srgb('#7a5236') + (1,); L.new(wv.outputs['Fac'], gr.inputs[0])
    wood = gr.outputs['Color']
    ao, edge = _ao_edge(N, L, 0.5, 0.025)
    sc = N.new('ShaderNodeTexNoise'); sc.inputs['Scale'].default_value = 14; sc.inputs['Detail'].default_value = 8; sc.inputs['Roughness'].default_value = 0.7; L.new(tc.outputs['Object'], sc.inputs['Vector'])
    wear = _math(N, L, 'MAXIMUM', _math(N, L, 'MULTIPLY', edge, 0.9), _mr(N, L, sc.outputs['Fac'], 0.68 - 0.1 * age, 0.72 - 0.1 * age))
    if paint:
        pc = _mix(N, L, _mr(N, L, sc.outputs['Fac'], 0.3, 0.7), srgb(paint) + (1,), tuple(x * 0.82 for x in srgb(paint)) + (1,))
        c = _mix(N, L, wear, pc, wood)                                                     # boya dökülmüş yer: ahşap
    else:
        c = _mix(N, L, _math(N, L, 'MULTIPLY', wear, 0.6), wood, srgb('#c9a47c') + (1,))     # aşınmış kenar açık
    c = _mix(N, L, _mr(N, L, ao, 0.2, 1.0, 0.6, 0.0), c, srgb('#24160f') + (1,))
    L.new(c, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.65 if paint else 0.8
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.4; bump.inputs['Distance'].default_value = 0.01
    L.new(_math(N, L, 'ADD', wv.outputs['Fac'], _math(N, L, 'MULTIPLY', wear, -0.6)), bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def roof_mat(name):
    """Kiremit: köşe rengi (oluk çizgileri) × akıntı lekeleri (z'de uzamış), alçak kısımlarda yosun lekeleri, likenler,
    kırık kiremit tonları; AO; kiremit sıra tümseği."""
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _nodes(m); b = N['Principled BSDF']
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3.0, 3.0, 0.4); L.new(tc.outputs['Object'], mp.inputs[0])
    st = N.new('ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 2.0; st.inputs['Detail'].default_value = 4; L.new(mp.outputs[0], st.inputs['Vector'])
    c = _mix(N, L, _math(N, L, 'MULTIPLY', _mr(N, L, st.outputs['Fac'], 0.5, 0.7), 0.5), vc.outputs['Color'], srgb('#3e3430') + (1,))
    mn = N.new('ShaderNodeTexNoise'); mn.inputs['Scale'].default_value = 3.5; mn.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], mn.inputs['Vector'])
    c = _mix(N, L, _math(N, L, 'MULTIPLY', _mr(N, L, mn.outputs['Fac'], 0.62, 0.7), 0.75), c, srgb('#5f7a3a') + (1,))     # yosun
    vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 25; L.new(tc.outputs['Object'], vo.inputs['Vector'])
    c = _mix(N, L, _math(N, L, 'MULTIPLY', _mr(N, L, vo.outputs['Distance'], 0.12, 0.05), 0.5), c, srgb('#b8b49a') + (1,))   # liken benekleri
    ao, edge = _ao_edge(N, L, 0.6)
    c = _mix(N, L, _math(N, L, 'MULTIPLY', edge, 0.35), c, srgb('#e2c9b0') + (1,))
    c = _mix(N, L, _mr(N, L, ao, 0.2, 1.0, 0.6, 0.0), c, srgb('#1e1614') + (1,))
    L.new(c, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.6
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.4; bump.inputs['Distance'].default_value = 0.03
    L.new(mn.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def brackets(name, cx, cy, z, w, d, n_side, col=None, mat=None):
    """Saçak altı ahşap konsollar (kademeli bloklar): sütun hizalarında, gölge ve derinlik verir."""
    mat = mat or wood_mat(name + '_m', paint='#8c2a20', grain_axis='X', age=0.6)
    for side in (-1, 1):
        y = cy + side * (d / 2 + 0.3)
        for i in range(n_side):
            x = cx - w / 2 - 0.25 + (w + 0.5) * i / (n_side - 1)
            for k, (dx, dy, dz, hh) in enumerate(((0.22, 0.22, 0.0, 0.18), (0.32, 0.42, 0.18, 0.16), (0.42, 0.62, 0.34, 0.16))):
                box(name, x - dx, x + dx, y - (dy if side < 0 else 0.1), y + (dy if side > 0 else 0.1), z + dz, z + dz + hh, lambda p, n: c3('#8c2a20'), mat, col)

# ------------------------------------------------------------------ duvarlı yapı katı (sütun, sıva, ahşap kafes pencere)

def hall_body(name, cx, cy, z, w, d, hgt, col=None, doors=3, windows=True):
    wall_m = plaster_mat(name + '_wm', z, hgt)
    def wc(p, n):
        zz = p.z - z
        if zz < 0.55: return c3('#9b4436') * (0.9 + 0.1 * MN.noise(V((p.x * 3, p.y * 3, 1))))     # alt kırmızı taban
        if zz > hgt - 0.5: return c3('#a83a2c')                                                   # üst kırmızı kuşak
        return c3('#efe5d3') * (0.93 + 0.07 * MN.noise(V((p.x * 1.5, p.y * 1.5, zz))))          # beyaz sıva
    box(name + '_w', cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, z, z + hgt, wc, wall_m, col, seg=(int(w * 2), int(d * 2), 8))
    col_m = wood_mat(name + '_cm', paint='#b3342a', grain_axis='Z', age=0.55)
    nx = max(2, int(w / 2.2)) + 1
    for i in range(nx):
        x = cx - w / 2 - 0.25 + (w + 0.5) * i / (nx - 1)
        for y in (cy - d / 2 - 0.3, cy + d / 2 + 0.3):
            K2.lathe(name + '_col', [V((x, y, z)), V((x, y, z + hgt + 0.1))], lambda t, a: 0.2, res=10, mat=col_m, col=col, colfun=lambda t, a, q: c3('#b3342a'))
            box(name + '_cb', x - 0.3, x + 0.3, y - 0.3, y + 0.3, z - 0.05, z + 0.25, lambda p, n: c3('#b5aa98'), wall_m, col)
    # kapılar / kafes pencereler (ön yüz)
    dm = wood_mat(name + '_dm', grain_axis='Z', scale=4.0, age=0.4)
    for i in range(doors):
        x = cx + (i - (doors - 1) / 2) * (w / max(1, doors))
        lat = lambda p, n, x=x: c3('#5c2a1f') if (int((p.x - x) * 8) % 2 == 0 or int((p.z - z) * 8) % 2 == 0) else c3('#2a120c')
        box(name + '_door', x - 0.7, x + 0.7, cy - d / 2 - 0.02, cy - d / 2 + 0.02, z + 0.55, z + hgt - 0.7, lat, dm, col, seg=(12, 1, 16))
        for q in range(7):                                                                   # kafes çıtaları (öne çıkık)
            xx = x - 0.6 + q * 0.2; box(name + '_lat', xx - 0.025, xx + 0.025, cy - d / 2 - 0.1, cy - d / 2 - 0.02, z + 0.6, z + hgt - 0.75, lambda p, n: c3('#5c2a1f'), dm, col)
        for q in range(9):
            zz = z + 0.65 + q * (hgt - 1.4) / 8; box(name + '_lat', x - 0.66, x + 0.66, cy - d / 2 - 0.09, cy - d / 2 - 0.03, zz - 0.025, zz + 0.025, lambda p, n: c3('#5c2a1f'), dm, col)
        box(name + '_frame', x - 0.82, x + 0.82, cy - d / 2 - 0.14, cy - d / 2 + 0.02, z + hgt - 0.78, z + hgt - 0.62, lambda p, n: c3('#5c2a1f'), dm, col)
        box(name + '_sill', x - 0.82, x + 0.82, cy - d / 2 - 0.16, cy - d / 2 + 0.02, z + 0.45, z + 0.6, lambda p, n: c3('#5c2a1f'), dm, col)
    if windows:
        for sx in (-1, 1):
            x = cx + sx * (w / 2 - 0.9)
            lat = lambda p, n, x=x: c3('#5c2a1f') if (int((p.x - x + 5) * 10) % 2 == 0 or int((p.z + 5) * 10) % 2 == 0) else c3('#1e0e08')
            box(name + '_win', x - 0.5, x + 0.5, cy - d / 2 - 0.06, cy - d / 2 + 0.02, z + 1.6, z + 2.5, lat, dm, col, seg=(10, 1, 10))

def lantern_mat(name):
    """Fener kâğıdı (gölgelendiricide, keskin): 12 koyu kaburga, uçlarda ince altın + mürekkep bantları, ortada altın çerçeveli
    desen kuşağı içinde iç içe bulut kıvrımları (6 tekrar). Kırmızı kâğıt arkadan aydınlanır (yarı saydamlık + hafif ışıma)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _nodes(m); b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    gx = _math(N, L, 'SUBTRACT', sep.outputs['X'], 0.5); gy = _math(N, L, 'SUBTRACT', sep.outputs['Y'], 0.5); gz = sep.outputs['Z']
    ang = _math(N, L, 'ARCTAN2', gy, gx)
    rib = _math(N, L, 'POWER', _math(N, L, 'ABSOLUTE', _math(N, L, 'COSINE', _math(N, L, 'MULTIPLY', ang, 6.0))), 40.0)
    bt = _math(N, L, 'ABSOLUTE', _math(N, L, 'SUBTRACT', gz, 0.5))
    def band(x, a0, a1):   # a0..a1 arası 1 (yumuşak kenar)
        return _math(N, L, 'MULTIPLY', _mr(N, L, x, a0 - 0.006, a0 + 0.006), _mr(N, L, x, a1 + 0.006, a1 - 0.006))
    gold = _math(N, L, 'MAXIMUM', band(bt, 0.40, 0.47), _math(N, L, 'MAXIMUM', band(bt, 0.135, 0.15), band(bt, 0.33, 0.345)))
    ink = band(bt, 0.36, 0.385)
    u = _math(N, L, 'FRACT', _math(N, L, 'MULTIPLY', _math(N, L, 'ADD', _math(N, L, 'DIVIDE', ang, 6.2832), 0.5), 6.0))
    v = _math(N, L, 'DIVIDE', _math(N, L, 'SUBTRACT', gz, 0.365), 0.27)
    du = _math(N, L, 'MULTIPLY', _math(N, L, 'SUBTRACT', u, 0.5), 2.0); dv = _math(N, L, 'MULTIPLY', _math(N, L, 'SUBTRACT', v, 0.5), 2.0)
    dist = _math(N, L, 'SQRT', _math(N, L, 'ADD', _math(N, L, 'MULTIPLY', du, du), _math(N, L, 'MULTIPLY', dv, dv)))
    inband = _mr(N, L, bt, 0.135, 0.125)
    swirl = _math(N, L, 'MAXIMUM', band(dist, 0.55, 0.66), band(dist, 0.22, 0.32))
    hook = _math(N, L, 'MULTIPLY', band(dv, -0.06, 0.06), _mr(N, L, du, 0.25, 0.3))         # kıvrımın kuyruğu
    motif = _math(N, L, 'MULTIPLY', _math(N, L, 'MAXIMUM', swirl, hook), inband)
    goldall = _math(N, L, 'MAXIMUM', gold, motif)
    c = _mix(N, L, _math(N, L, 'MULTIPLY', rib, 0.8), srgb('#d42d1a') + (1,), srgb('#7a140a') + (1,))
    c = _mix(N, L, ink, c, srgb('#1e0804') + (1,))
    c = _mix(N, L, goldall, c, srgb('#f0c048') + (1,))
    L.new(c, b.inputs['Base Color']); L.new(c, b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 0.45
    b.inputs['Roughness'].default_value = 0.55; b.inputs['Subsurface Weight'].default_value = 0.3
    mt = N.new('ShaderNodeMath'); mt.operation = 'MULTIPLY'; mt.inputs[1].default_value = 0.8; L.new(goldall, mt.inputs[0]); L.new(mt.outputs[0], b.inputs['Metallic'])
    return m

def lanterns(name, pts, col=None, light=True):
    """Geleneksel kâğıt fener: fıçı gövde (desen gölgelendiricide), siyah kapaklar, ip, altın düğüm, kırmızı püskül; içte sıcak ışık."""
    m = lantern_mat(name + '_lm'); dark = vmat(name + '_dk', 0.5, 0.1); tm = vmat(name + '_tas', 0.9, 0.6, 120)
    gold = c3('#e7b23e')
    for (x, y, z, s) in pts:
        R = random.Random(int(x * 7 + y * 3))
        path = [V((0, 0, s * (-0.34 + 0.68 * t))) for t in np.linspace(0, 1, 24)]
        o = K2.lathe(name + '_body', path, lambda t, a: s * 0.27 * (0.55 + 0.45 * math.sin(math.pi * t) ** 0.6), res=48, mat=m, col=col)
        o.location = (x, y, z)
        for zz, rr in ((0.36, 0.17), (-0.36, 0.15)):
            K2.lathe(name + '_cap', [V((x, y, z + s * zz - 0.03 * s)), V((x, y, z + s * zz + 0.04 * s))], lambda t, a, rr=rr: s * rr, res=16, mat=dark, col=col, colfun=lambda t, a, q: c3('#1c1410'))
        K2.lathe(name + '_cord', [V((x, y, z + s * 0.4)), V((x, y, z + s * 0.75))], lambda t, a: s * 0.012, res=6, mat=dark, col=col, colfun=lambda t, a, q: c3('#3a2418'))
        K2.lathe(name + '_knot', [V((x, y, z - s * 0.4)), V((x, y, z - s * 0.5))], lambda t, a: s * 0.04 * (1 - 0.3 * t), res=10, mat=tm, col=col, colfun=lambda t, a, q: gold)
        for k_ in range(14):
            a_ = k_ / 14 * math.tau; dx, dy = math.cos(a_) * 0.03 * s, math.sin(a_) * 0.03 * s
            K2.lathe(name + '_tas', [V((x + dx * 0.5, y + dy * 0.5, z - s * 0.5)), V((x + dx, y + dy, z - s * 0.85 - R.uniform(0, 0.05) * s))], lambda t, a: s * 0.008, res=4, mat=tm, col=col, colfun=lambda t, a, q: c3('#c8261a'))
        if light:
            ld = bpy.data.lights.new(name + '_l', 'POINT'); ld.energy = 6.0 * s; ld.color = srgb('#ffb066'); ld.shadow_soft_size = 0.2 * s
            lo = bpy.data.objects.new(name + '_l', ld); lo.location = (x, y, z); K.link(lo, col)

# ------------------------------------------------------------------ taş teras (çimenli üst, yontulmuş kaya yüz)

def terrace(name, outline, z0, z1, col=None, rock=None, seed=0):
    """outline: [(x,y)] kapalı, saat yönü tersine. Yüz: hafif içe eğik, düzensiz kaya bloklar (köşe rengi + kabartma);
    üst: çim (kenarda hafif kıvrık dudak)."""
    R = random.Random(seed); rock = rock or K.rock_mat(name + '_rk', base='#cbbda3', dark='#8c7f6c', light='#e6dcc8', moss_amt=0.15, cracks=0.6)
    pts = [V((x, y, 0)) for (x, y) in outline]; n = len(pts); rows = 6
    V_, F_ = [], []
    cen = sum(pts, V()) / n
    for r in range(rows + 1):
        t = r / rows; zz = z0 + (z1 - z0) * t
        for k, p in enumerate(pts):
            out = (p - cen); out.z = 0; out.normalize()
            jag = 0.12 * MN.noise(V((p.x * 0.8, p.y * 0.8, zz * 1.5 + seed))) + 0.06 * (r % 2)
            q = p + out * (jag - 0.18 * t); V_.append((q.x, q.y, zz))
    for r in range(rows):
        for k in range(n):
            a = r * n + k; b = r * n + (k + 1) % n; F_.append((a, b, b + n, a + n))
    wall = mesh_obj(name + '_face', V_, F_, rock, col=col)
    md = wall.modifiers.new('sub', 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = 0; md.render_levels = 2
    # üst çim (yelpaze)
    gm, N, L, b = _mat(name + '_g'); vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.0; nz.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    fz = N.new('ShaderNodeTexNoise'); fz.inputs['Scale'].default_value = 90.0; fz.inputs['Detail'].default_value = 2; L.new(tc.outputs['Object'], fz.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = srgb('#3f7f26') + (1,); mx.inputs[7].default_value = srgb('#9acd4e') + (1,)
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.6; L.new(fz.outputs['Fac'], ad.inputs[0]); L.new(nz.outputs['Fac'], ad.inputs[2])
    sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = 0.35; L.new(ad.outputs[0], sub.inputs[0]); L.new(sub.outputs[0], mx.inputs['Factor'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 0.6; L.new(mx.outputs[2], mul.inputs[6]); L.new(vc.outputs['Color'], mul.inputs[7])
    L.new(mx.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.9
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.6; bn.inputs['Distance'].default_value = 0.02; L.new(fz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    top = [(V_[rows * n + k][0], V_[rows * n + k][1], z1 + 0.02) for k in range(n)]
    lip = []
    for k, p in enumerate(pts):
        out = (p - cen); out.z = 0; out.normalize(); q = V(top[k]) + out * 0.12 + V((0, 0, -0.08)); lip.append(tuple(q))
    tv = top + lip + [(cen.x, cen.y, z1 + 0.02)]
    tf = [(k, (k + 1) % n, 2 * n) for k in range(n)] + [((k + 1) % n, k, n + k, n + (k + 1) % n) for k in range(n)]
    gc = [c3('#5fa13a') * (0.9 + 0.2 * R.random()) for _ in range(n)] + [c3('#3f7a2a')] * n + [c3('#6cae40')]
    mesh_obj(name + '_top', tv, tf, gm, colors=np.array(gc), col=col)

def steps(name, x, y, z0, z1, width, depth=0.45, col=None, rock=None):
    """Yontulmuş taş basamaklar: her basamak hafif düzensiz kutu (köşe rengi taş tonu), üst kenarı açık, arası koyu derz."""
    n = max(2, int(round((z1 - z0) / 0.28))); dz = (z1 - z0) / n; R = random.Random(int(x * 10 + y))
    m = vmat(name + '_m', 0.85, 0.5, 14)
    for i in range(n):
        yy0 = y - depth * (n - i); w2 = width / 2 * R.uniform(0.96, 1.04)
        def cf(p, nrm, zt=z0 + dz * (i + 1)):
            c = c3('#c8bba3') * (0.85 + 0.2 * MN.noise(V((p.x * 1.3, p.y * 1.3, p.z * 2))))
            if nrm.z > 0.5: c = c * 1.12
            if abs(p.z - zt) < 0.03 and nrm.z < 0.5: c = c * 1.2
            return c
        box(name + '_%d' % i, x - w2, x + w2, yy0, y + 0.2, z0 + dz * i - 0.05, z0 + dz * (i + 1), cf, m, col, seg=(int(width * 2), 2, 1))

def rounded_rect(cx, cy, w, d, r=1.2, n=10, noise=0.25, seed=0):
    pts = []
    for (qx, qy, a0) in ((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)):
        ccx, ccy = cx + qx * (w / 2 - r), cy + qy * (d / 2 - r)
        for k in range(n):
            a = math.radians(a0 + 90 * k / (n - 1)); rr = r + noise * MN.noise(V((math.cos(a) * 3 + qx, math.sin(a) * 3 + qy, seed)))
            pts.append((ccx + math.cos(a) * rr, ccy + math.sin(a) * rr))
    return pts

# ------------------------------------------------------------------ duvar (dalgalı kiremit başlıklı)

def court_wall(name, path, hgt=2.4, col=None):
    wm = vmat(name + '_m', 0.85, 0.3, 30)
    for (a, b) in zip(path[:-1], path[1:]):
        a, b = V(a + (0,)), V(b + (0,)); L = (b - a).length; dvec = (b - a).normalized(); sd = V((-dvec.y, dvec.x, 0)) * 0.3
        nseg = max(2, int(L * 3)); V_, F_, C_ = [], [], []
        for i in range(nseg + 1):
            p = a + dvec * (L * i / nseg)
            top = hgt + 0.18 * math.sin(L * i / nseg / 2.2 * math.tau)          # dalgalı başlık
            for (s, zz) in ((-1, 0), (-1, top), (1, top), (1, 0)):
                q = p + sd * s; V_.append((q.x, q.y, zz))
                C_.append(c3('#a8473a') if zz > hgt - 0.6 else (c3('#c9b48e') * (0.88 + 0.12 * MN.noise(V((q.x * 2, q.y * 2, zz * 4))))))
        for i in range(nseg):
            for k in range(3):
                a_ = i * 4 + k; F_.append((a_, a_ + 1, a_ + 5, a_ + 4))
        mesh_obj(name, V_, F_, wm, colors=np.array(C_), col=col)
        # kiremit başlık (koyu, iki yana taşan)
        cv, cf, cc = [], [], []
        for i in range(nseg + 1):
            p = a + dvec * (L * i / nseg); top = hgt + 0.18 * math.sin(L * i / nseg / 2.2 * math.tau)
            for (s, zz) in ((-1.9, -0.12), (0, 0.22), (1.9, -0.12)):
                q = p + sd * s; cv.append((q.x, q.y, top + zz)); cc.append(c3('#7d3125'))
        for i in range(nseg):
            for k in range(2):
                a_ = i * 3 + k; cf.append((a_, a_ + 1, a_ + 4, a_ + 3))
        mesh_obj(name + '_cap', cv, cf, wm, colors=np.array(cc), col=col)

# ------------------------------------------------------------------ tapınak avlusu

PAL_BLOSSOM = [(0.0, '#7a1f4f'), (0.35, '#b52f7a'), (0.65, '#dc4d9c'), (0.9, '#f07ec0'), (1.0, '#ffb3dc')]

def temple(col=None, seed=0):
    """Yerel koordinat: ön = −y (güney). Taban z = 0 (plato). Teraslar: alt 0→1.0, üst 1.0→2.1."""
    R = random.Random(seed)
    rock = K.rock_mat('tmp_rock', base='#cdbfa5', dark='#8b7e6b', light='#e8decb', moss_amt=0.12, cracks=0.6)
    terrace('tmp_t1', rounded_rect(0, 1.0, 30, 22, 2.0, seed=1), -0.3, 1.0, col, rock, 1)
    terrace('tmp_t2', rounded_rect(0, 4.5, 21, 13, 1.5, seed=2), 1.0, 2.1, col, rock, 2)
    terrace('tmp_t0', rounded_rect(-9, -8.5, 7, 3.5, 1.0, seed=3), -0.3, 0.45, col, rock, 3)          # önde küçük basamak sekisi
    steps('tmp_s1', 0, -10.0, -0.25, 1.0, 5.0, col=col, rock=rock)
    steps('tmp_s2', 0, -2.0, 1.0, 2.1, 4.0, col=col, rock=rock)
    steps('tmp_s3', -12.5, -10.0, -0.25, 1.0, 3.0, col=col, rock=rock)
    # ana salon (üst terasta)
    hall_body('tmp_hall', 0, 6.5, 2.1, 11, 6.5, 4.2, col, doors=3)
    roof('tmp_hall_roof', 0, 6.5, 2.1 + 4.2, 11, 6.5, 2.8, over=1.4, curl=0.9, ridge=0.5, tile='grey', col=col)
    lanterns('tmp_lan', [(x, 6.5 - 3.25 - 1.0, 2.1 + 3.5, 1.15) for x in (-4.5, -1.5, 1.5, 4.5)], col)
    brackets('tmp_brk', 0, 6.5, 2.1 + 4.2 - 0.5, 11, 6.5, 6, col)
    lanterns('tmp_lan_s', [(9.5, 1.3, 3.6, 0.9), (13.5, 1.3, 3.6, 0.9)], col)
    # pagoda (sol arka, alt terasta)
    px, py = -10.5, 6.0; z = 1.0; s = 6.0
    for i in range(4):
        hh = 3.3 if i == 0 else 2.3
        hall_body('tmp_pg%d' % i, px, py, z, s, s, hh, col, doors=1 if i == 0 else 0, windows=(i == 0))
        roof('tmp_pg_roof%d' % i, px, py, z + hh, s, s, 1.2 + 0.2 * (i == 3), over=1.15 - 0.1 * i, curl=0.7, ridge=0.02, tile='terra', col=col)
        z += hh + 0.6; s *= 0.8
    lanterns('tmp_lan_p', [(px - 3.1, py - 3.1, 3.4, 0.85), (px + 3.1, py - 3.1, 3.4, 0.85)], col)
    gm, N, L, b = _mat('tmp_gold'); b.inputs['Base Color'].default_value = srgb('#e0b23a') + (1,); b.inputs['Metallic'].default_value = 0.7; b.inputs['Roughness'].default_value = 0.35
    K2.lathe('tmp_finial', [V((px, py, z + 0.2)), V((px, py, z + 2.4))], lambda t, a: 0.12 * (1 - 0.8 * t) + 0.08 * (math.sin(t * 18) > 0.6), res=10, mat=gm, col=col)
    # yan yapı (sağ, alt terasta) + küçük köşk
    hall_body('tmp_side', 11.5, 4.5, 1.0, 6.0, 5.0, 3.4, col, doors=1)
    roof('tmp_side_roof', 11.5, 4.5, 4.4, 6.0, 5.0, 1.9, over=1.0, curl=0.6, ridge=0.35, tile='terra', col=col)
    # avlu duvarı (arka ve yanlar)
    court_wall('tmp_wall', [(-14.5, -6), (-14.5, 11.5), (14.5, 11.5), (14.5, -6)], 2.6, col)
    # dikili taş bahçesi (sol önde) + iri taşlar
    rk2 = K.rock_mat('tmp_rock2', base='#c9c3b6', dark='#8a8478', light='#e4ded2', moss_amt=0.3, cracks=0.5)
    for k, (x, y, sx, sy, sz) in enumerate(((-6.5, -3.0, 0.9, 0.8, 1.9), (-5.4, -3.6, 0.6, 0.5, 1.2), (-7.4, -4.0, 0.5, 0.5, 0.8), (6.5, -4.5, 0.8, 0.7, 1.0), (3.5, 9.6, 0.9, 0.8, 1.7))):
        o = K.boulder('tmp_st%d' % k, (sx, sy, sz), 600 + k, cuts=12, mat=rk2, col=col, top_flat=0.1); o.location = (x, y, (1.0 if y > -5 else 0.0) + sz * 0.85)
    # ağaçlar: arkada pembe çiçekli, önde yeşil yuvarlaklar + çalı
    fol = K.foliage_mat('tmp_fol'); bark = K.bark_mat('tmp_bark')
    pinkc = bpy.data.collections.new('C_tmp_pink'); K.round_tree('tmp_pink', 9.0, 77, col=pinkc, palette=PAL_BLOSSOM, spread=1.2, fol=K.foliage_mat('tmp_fol_p', translucent=0.35), bark=bark, clumps=13)
    greens = []
    for k in range(3):
        c = bpy.data.collections.new('C_tmp_g%d' % k); K.round_tree('tmp_g%d' % k, 7.0 + k, 80 + k, col=c, palette=(K.PAL_BROAD, K.PAL_BROAD3, K.PAL_BROAD2)[k], spread=1.1, fol=fol, bark=bark); greens.append(c)
    bushc = bpy.data.collections.new('C_tmp_bush'); K.bush('tmp_bush', 1.3, 90, col=bushc, fol=fol, leaf=0.09)
    trees = [(pinkc, -5.0, 12.8, 1.0, 1.25), (greens[0], -16.5, 2.0, 0.0, 1.0), (greens[1], 16.5, -1.0, 0.0, 0.9), (greens[2], 8.0, 13.0, 1.0, 1.0),
             (greens[0], -7.0, 13.5, 1.0, 0.85), (bushc, -3.5, -8.0, 0.0, 1.0), (bushc, 4.5, -8.5, 0.0, 0.8)]
    # taş döşeli yol: alt basamaktan üst basamağa (düzensiz plakalar, aralarında yosunlu derz)
    pvm = vmat('tmp_pave_m', 0.85, 0.5, 18)
    Rp = random.Random(9); y = -9.8
    while y < -3.6:
        x = -1.4; ln = Rp.uniform(0.45, 0.8)
        while x < 1.4:
            w = min(Rp.uniform(0.45, 0.9), 1.4 - x); tone = c3('#c4b8a2') * Rp.uniform(0.82, 1.08)
            box('tmp_slab', x + 0.03, x + w - 0.03, y + 0.03, y + ln - 0.03, 0.98, 1.06 + Rp.uniform(0, 0.03),
                lambda p, n, tone=tone: tone * (1.1 if n.z > 0.5 else 0.8), pvm, col)
            x += w
        y += ln
    box('tmp_joint', -1.45, 1.45, -9.85, -3.55, 0.97, 1.02, lambda p, n: c3('#4f6a2e'), pvm, col)
    terrace_plants(col, seed)
    return trees

def _in_poly(x, y, poly):
    inside = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1: inside = not inside
    return inside

def terrace_plants(col, seed=0):
    """Teras üstleri (adanın genel çimiyle aynı tel tel çim) + yoğun renkli çiçek öbekleri; yapı tabanları, basamaklar, yol boş."""
    R = np.random.default_rng(seed + 5); Rr = random.Random(seed + 6)
    t1 = rounded_rect(0, 1.0, 30, 22, 2.0, seed=1); t2 = rounded_rect(0, 4.5, 21, 13, 1.5, seed=2)
    blocks = [(-10.5, 6.0, 4.0, 4.0), (0, 6.5, 6.6, 4.4), (11.5, 4.5, 3.8, 3.3), (0, -8.0, 1.55, 2.6), (0, -6.0, 1.55, 2.6), (0, -2.8, 2.1, 1.0), (-12.5, -8.0, 2.0, 3.0)]
    def free(x, y):
        for (bx, by, hw, hd) in blocks:
            if abs(x - bx) < hw and abs(y - by) < hd: return False
        return True
    pts = []
    for poly, z, n in ((t1, 1.0, 230000), (t2, 2.1, 90000)):
        xs = R.uniform(-15.5, 15.5, n); ys = R.uniform(-10.5, 12.5, n)
        for x, y in zip(xs, ys):
            if not _in_poly(x, y, poly): continue
            if z < 2 and _in_poly(x, y, t2): continue
            if not free(x, y): continue
            pts.append((x, y, z + 0.02, 1.0 + 0.4 * R.random()))
    P = np.array(pts, np.float32)
    gmats = [K.grass_blade_mat('tmp_gr%d' % k, *cs) for k, cs in enumerate((('#2f7a1f', '#66b53a', '#cfe85e'), ('#348a22', '#79c43c', '#ddf06a', 0.5), ('#5f7a26', '#a7a845', '#e6d778')))]
    sel = R.integers(0, 3, len(P), endpoint=False); sel = np.where(R.random(len(P)) < 0.15, 2, np.where(R.random(len(P)) < 0.5, 1, 0))
    for k in range(3):
        K.fast_blades('tmp_grass%d' % k, P[sel == k], gmats[k], h=(0.1, 0.24), seed=20 + k, col=col)
    # çiçek öbekleri: mavi çan, turuncu/sarı yıldız, pembe, beyaz papatya
    kinds = [K.flower_patch_mesh('tmp_fb%d' % k, 'bell', 7, 300 + k) for k in range(2)] + [K.flower_patch_mesh('tmp_fd%d' % k, 'daisy', 6, 310 + k) for k in range(2)] + \
            [K.flower_patch_mesh('tmp_fy%d' % k, 'yellow', 5, 320 + k) for k in range(2)]
    for o in kinds:
        for c in list(o.users_collection): c.objects.unlink(o)
    pinks = []
    for k in range(2):
        o = K.flower_patch_mesh('tmp_fp%d' % k, 'daisy', 6, 330 + k); pinks.append(o)
        for c in list(o.users_collection): c.objects.unlink(o)
        ca = o.data.color_attributes['Col']; arr = np.zeros(len(o.data.vertices) * 4, np.float32); ca.data.foreach_get('color', arr); arr = arr.reshape(-1, 4)
        hot = arr[:, 0] > 0.3; arr[hot, :3] = np.array(srgb(Rr.choice(['#f06aa8', '#ffffff'])))[None, :]; ca.data.foreach_set('color', arr.ravel())
    pool = kinds + pinks
    for i in range(300):
        poly, z = (t1, 1.0) if Rr.random() < 0.7 else (t2, 2.1)
        for _ in range(20):
            cx, cy = Rr.uniform(-14, 14), Rr.uniform(-9.5, 11.5)
            if _in_poly(cx, cy, poly) and free(cx, cy) and (z > 2 or not _in_poly(cx, cy, t2)): break
        kind = Rr.choice(pool)
        for j in range(Rr.randint(5, 12)):
            x, y = cx + Rr.gauss(0, 0.5), cy + Rr.gauss(0, 0.5)
            if not (_in_poly(x, y, poly) and free(x, y)): continue
            e = bpy.data.objects.new('tmp_flw', kind.data); e.location = (x, y, z); e.rotation_euler = (0, 0, Rr.uniform(0, 6.3))
            sc_ = Rr.uniform(0.9, 1.4); e.scale = (sc_, sc_, sc_); col.objects.link(e)

def place_temple(L, inst_fn, cx, cz, yaw=0.0):
    col = bpy.data.collections.new('C_temple'); trees = temple(col)
    y0 = L.height(cx, cz)
    inst_fn(col, cx, cz, y0, yaw, 1.0)
    for (c, x, y, z, s) in trees:
        ca, sa = math.cos(yaw), math.sin(yaw); wx, wz = cx + x * ca - y * sa, cz + x * sa + y * ca
        inst_fn(c, wx, wz, y0 + z - 0.1, random.uniform(0, 6.3), s)
