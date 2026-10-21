# v6 ortak araçlar (21 Ekim 2026): resimsi ada için kodla özgün ağaç, kaya, bulut, çiçek, kamp eşyaları.
# Yöntem: yaprak kartları + taç biçiminden aktarılmış yumuşak normaller (yumuşak, hacimli "boyalı" taç gölgesi),
# düzlemle yontulmuş + pahlı iri kayalar, metatoplardan pamuk bulutlar. Referans görseller yalnız hava/kalite hedefi.
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector as V, noise as MN

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)

def ramp3(t, cols):
    """t (n,) → renk (n,3); cols = [(konum, '#hex'), ...] doğrusal (doğrusal renk uzayında)."""
    pos = np.array([p for p, _ in cols]); cc = np.array([srgb(c) for _, c in cols])
    return np.stack([np.interp(t, pos, cc[:, k]) for k in range(3)], -1)

def link(o, col=None):
    (col or bpy.context.scene.collection).objects.link(o); return o

def mesh_obj(name, verts, faces, mat=None, colors=None, normals=None, smooth=True, col=None, attr='Col'):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    if smooth: me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if colors is not None:
        ca = me.color_attributes.new(attr, 'FLOAT_COLOR', 'POINT')
        c4 = np.ones((len(verts), 4), np.float32); c4[:, :3] = colors; ca.data.foreach_set('color', c4.ravel())
    if normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    if mat: me.materials.append(mat)
    o = bpy.data.objects.new(name, me); link(o, col); return o

# ------------------------------------------------------------------ malzemeler

def _mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']

def foliage_mat(name, translucent=0.28, rough=0.6, hue_var=0.03):
    """Taç: köşe rengi (koyu iç → açık tepe) + yaprak başına hafif ton oynaması + arkadan gelen ışıkta yarı saydamlık."""
    m, N, L, b = _mat(name)
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; nz.inputs['Detail'].default_value = 2
    tc = N.new('ShaderNodeTexCoord'); L.new(tc.outputs['Object'], nz.inputs['Vector'])
    hs = N.new('ShaderNodeHueSaturation'); L.new(vc.outputs['Color'], hs.inputs['Color'])
    # ağaç başına renk çeşitliliği (her örnek farklı): ton, doygunluk, parlaklık; + yaprak kümesi başına küçük oynama
    oi = N.new('ShaderNodeObjectInfo')
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.3; L.new(nz.outputs['Fac'], ad.inputs[0]); L.new(oi.outputs['Random'], ad.inputs[2])
    mr = N.new('ShaderNodeMapRange'); mr.inputs[1].default_value = 0.0; mr.inputs[2].default_value = 1.3; mr.inputs[3].default_value = 0.5 - hue_var * 1.6; mr.inputs[4].default_value = 0.5 + hue_var * 1.6
    L.new(ad.outputs[0], mr.inputs[0]); L.new(mr.outputs[0], hs.inputs['Hue'])
    sv = N.new('ShaderNodeMapRange'); sv.inputs[3].default_value = 0.82; sv.inputs[4].default_value = 1.18; L.new(oi.outputs['Random'], sv.inputs[0]); L.new(sv.outputs[0], hs.inputs['Value'])
    sa = N.new('ShaderNodeMapRange'); sa.inputs[3].default_value = 0.85; sa.inputs[4].default_value = 1.15; L.new(nz.outputs['Fac'], sa.inputs[0]); L.new(sa.outputs[0], hs.inputs['Saturation'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = 0.3
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    tr = N.new('ShaderNodeBsdfTranslucent'); L.new(hs.outputs['Color'], tr.inputs['Color'])
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = translucent
    L.new(b.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], N['Material Output'].inputs['Surface'])
    return m

def vcol_mat(name, rough=0.85, bump=0.0, bump_scale=20.0):
    m, N, L, b = _mat(name)
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; L.new(vc.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if bump:
        bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump
        n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = bump_scale; n2.inputs['Detail'].default_value = 4
        L.new(n2.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m

def bark_mat(name='bark_v6', base='#6e4b33', dark='#3f2a1e', light='#9a7352', white=False):
    """Gövde: dikey uzamış gürültüyle kabuk şeritleri; huş için beyaz + koyu yatay lekeler."""
    m, N, L, b = _mat(name)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6, 6, 0.8) if not white else (3, 3, 9)
    L.new(tc.outputs['Object'], mp.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4; nz.inputs['Detail'].default_value = 6; L.new(mp.outputs[0], nz.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); r = cr.color_ramp
    if white:
        r.elements[0].position = 0.58; r.elements[0].color = srgb('#efe9df') + (1,)
        r.elements[1].position = 0.64; r.elements[1].color = srgb('#2b2622') + (1,)
        mx = N.new('ShaderNodeMath'); mx.operation = 'SUBTRACT'; mx.inputs[0].default_value = 1.0
        L.new(nz.outputs['Fac'], mx.inputs[1]); L.new(mx.outputs[0], cr.inputs[0])
    else:
        r.elements[0].position = 0.3; r.elements[0].color = srgb(dark) + (1,)
        r.elements[1].position = 0.75; r.elements[1].color = srgb(light) + (1,)
        e = r.elements.new(0.5); e.color = srgb(base) + (1,)
        L.new(nz.outputs['Fac'], cr.inputs[0])
    L.new(cr.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.85
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.4 if not white else 0.1; L.new(nz.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m

def rock_mat(name, base='#b0a5a6', dark='#7d7184', light='#cfc4bc', moss='#6aa33e', moss_amt=0.2, cracks=0.5):
    """İri kaya: açık sıcak gri-leylak düzlemler, koyu soğuk çatlaklar (voronoi kenarı), üst yüzlerde yosun tozu."""
    m, N, L, b = _mat(name)
    geo = N.new('ShaderNodeNewGeometry'); tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 1.2; n1.inputs['Detail'].default_value = 4; L.new(tc.outputs['Object'], n1.inputs['Vector'])
    c1 = N.new('ShaderNodeValToRGB'); r = c1.color_ramp
    r.elements[0].position = 0.3; r.elements[0].color = srgb(dark) + (1,); r.elements[1].position = 0.72; r.elements[1].color = srgb(light) + (1,)
    e = r.elements.new(0.5); e.color = srgb(base) + (1,); L.new(n1.outputs['Fac'], c1.inputs[0])
    vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 0.7; vo.inputs['Randomness'].default_value = 1.0; L.new(tc.outputs['Object'], vo.inputs['Vector'])
    crk = N.new('ShaderNodeMapRange'); crk.inputs[1].default_value = 0.0; crk.inputs[2].default_value = 0.018; crk.inputs[3].default_value = 1.0 - cracks * 0.4; crk.inputs[4].default_value = 1.0
    L.new(vo.outputs['Distance'], crk.inputs[0])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    L.new(c1.outputs['Color'], mul.inputs[6]); cmb = N.new('ShaderNodeCombineXYZ')
    for k in range(3): L.new(crk.outputs[0], cmb.inputs[k])
    L.new(cmb.outputs[0], mul.inputs[7])
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 7; n2.inputs['Detail'].default_value = 3; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.6
    L.new(n2.outputs['Fac'], ad.inputs[0]); L.new(sep.outputs['Z'], ad.inputs[2])
    mm = N.new('ShaderNodeMapRange'); mm.inputs[1].default_value = 1.32 - moss_amt * 0.5; mm.inputs[2].default_value = 1.38 - moss_amt * 0.5
    L.new(ad.outputs[0], mm.inputs[0])
    fin = N.new('ShaderNodeMix'); fin.data_type = 'RGBA'; fin.inputs[7].default_value = srgb(moss) + (1,)
    L.new(mm.outputs[0], fin.inputs['Factor']); L.new(mul.outputs[2], fin.inputs[6])
    # el boyaması: yüz kenarlarında açık parıltı (eğimli normal farkı), çatlak dudağında parıltı, oyuklarda koyu (AO)
    bv = N.new('ShaderNodeBevel'); bv.samples = 6; bv.inputs['Radius'].default_value = 0.06
    dt = N.new('ShaderNodeVectorMath'); dt.operation = 'DOT_PRODUCT'; L.new(bv.outputs[0], dt.inputs[0]); L.new(geo.outputs['Normal'], dt.inputs[1])
    edg = N.new('ShaderNodeMapRange'); edg.inputs[1].default_value = 0.995; edg.inputs[2].default_value = 0.93; L.new(dt.outputs['Value'], edg.inputs[0])
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 6; ao.only_local = True; ao.inputs['Distance'].default_value = 0.35
    cav = N.new('ShaderNodeMapRange'); cav.inputs[1].default_value = 0.4; cav.inputs[2].default_value = 0.9; cav.inputs[3].default_value = 1.0; cav.inputs[4].default_value = 0.0
    L.new(ao.outputs['AO'], cav.inputs[0])
    cr2 = N.new('ShaderNodeMapRange'); cr2.inputs[1].default_value = 0.02; cr2.inputs[2].default_value = 0.035; L.new(vo.outputs['Distance'], cr2.inputs[0])
    cr3 = N.new('ShaderNodeMapRange'); cr3.inputs[1].default_value = 0.075; cr3.inputs[2].default_value = 0.045; L.new(vo.outputs['Distance'], cr3.inputs[0])
    clip_ = N.new('ShaderNodeMath'); clip_.operation = 'MINIMUM'; L.new(cr2.outputs[0], clip_.inputs[0]); L.new(cr3.outputs[0], clip_.inputs[1])
    rimsum = N.new('ShaderNodeMath'); rimsum.operation = 'ADD'; rimsum.use_clamp = True; L.new(edg.outputs[0], rimsum.inputs[0]); L.new(clip_.outputs[0], rimsum.inputs[1])
    rimf = N.new('ShaderNodeMath'); rimf.operation = 'MULTIPLY'; rimf.inputs[1].default_value = 0.7; L.new(rimsum.outputs[0], rimf.inputs[0])
    lit = N.new('ShaderNodeMix'); lit.data_type = 'RGBA'; lit.inputs[7].default_value = srgb('#f1ebe4') + (1,)
    L.new(rimf.outputs[0], lit.inputs['Factor']); L.new(fin.outputs[2], lit.inputs[6])
    cavf = N.new('ShaderNodeMath'); cavf.operation = 'MULTIPLY'; cavf.inputs[1].default_value = 0.65; L.new(cav.outputs[0], cavf.inputs[0])
    shd = N.new('ShaderNodeMix'); shd.data_type = 'RGBA'; shd.inputs[7].default_value = srgb('#3f3848') + (1,)
    L.new(cavf.outputs[0], shd.inputs['Factor']); L.new(lit.outputs[2], shd.inputs[6])
    L.new(shd.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.82
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.25
    hb = N.new('ShaderNodeMath'); hb.operation = 'ADD'; L.new(n2.outputs['Fac'], hb.inputs[0]); L.new(crk.outputs[0], hb.inputs[1])
    L.new(hb.outputs[0], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    # gerçek kabartma: çatlaklar içe oyuk (nesne birimi; kaya 1 m'lik örnekten ölçeklenir), hafif yüzey dalgası
    dcr = N.new('ShaderNodeMapRange'); dcr.inputs[1].default_value = 0.0; dcr.inputs[2].default_value = 0.05; dcr.inputs[3].default_value = -0.07 * (0.4 + cracks); dcr.inputs[4].default_value = 0.0
    L.new(vo.outputs['Distance'], dcr.inputs[0])
    dn2 = N.new('ShaderNodeMapRange'); dn2.inputs[1].default_value = 0.3; dn2.inputs[2].default_value = 0.7; dn2.inputs[3].default_value = -0.025; dn2.inputs[4].default_value = 0.025
    L.new(n1.outputs['Fac'], dn2.inputs[0])
    ad2 = N.new('ShaderNodeMath'); ad2.operation = 'ADD'; L.new(dcr.outputs[0], ad2.inputs[0]); L.new(dn2.outputs[0], ad2.inputs[1])
    dsp = N.new('ShaderNodeDisplacement'); dsp.space = 'OBJECT'; dsp.inputs['Midlevel'].default_value = 0.0; dsp.inputs['Scale'].default_value = 1.0
    L.new(ad2.outputs[0], dsp.inputs['Height']); L.new(dsp.outputs['Displacement'], N['Material Output'].inputs['Displacement'])
    try: m.displacement_method = 'BOTH'
    except Exception: m.cycles.displacement_method = 'BOTH'
    return m

# ------------------------------------------------------------------ gövde

def tube_data(pts, radii, res=8, v0=0):
    verts, faces = [], []
    pts = [V(p) for p in pts]
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = V((1, 0, 0)) if abs(t.z) > 0.9 else V((0, 0, 1)); u = t.cross(a).normalized(); w = t.cross(u)
        for k in range(res):
            th = k / res * math.tau; verts.append(p + (u * math.cos(th) + w * math.sin(th)) * radii[i])
    for i in range(len(pts) - 1):
        for k in range(res):
            a = v0 + i * res + k; b = v0 + i * res + (k + 1) % res
            faces.append((a, b, b + res, a + res))
    return verts, faces

def trunk_obj(name, branches, mat, col=None, res=8):
    vs, fs = [], []
    for pts, radii in branches:
        v, f = tube_data(pts, radii, res, len(vs)); vs += v; fs += f
    return mesh_obj(name, vs, fs, mat, col=col)

# ------------------------------------------------------------------ taç (yaprak kartı + yumuşak normal)

def crown(name, clusters, center, radii, palette, leaf=0.35, density=320, seed=0, col=None, mat=None, droop=0.35, shell=0.86, flat_top=0.0, cw=0.45):
    """clusters: [(merkez V, yarıçaplar V)], center/radii: tüm taç (normal kaynağı). palette: occ 0..1 → renk."""
    R = np.random.default_rng(seed)
    cen = np.array(center, np.float32); crad = np.array(radii, np.float32)
    V_, F_, C_, N_ = [], [], [], []
    nv = 0
    for (cc, rr) in clusters:
        cc = np.array(cc, np.float32); rr = np.array(rr, np.float32)
        area = 4 * math.pi * ((rr[0] * rr[1]) ** 1.6 + (rr[0] * rr[2]) ** 1.6 + (rr[1] * rr[2]) ** 1.6) ** (1 / 1.6) / 3
        n = int(density * area / (leaf * leaf) * 0.05) + 20
        d = R.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        d[:, 2] = np.where(d[:, 2] < -0.55, -0.55 + (d[:, 2] + 0.55) * 0.3, d[:, 2])     # alt yüz biraz düz
        p = cc + d * rr * R.uniform(0.86, 1.04, (n, 1))
        if flat_top: p[:, 2] = np.minimum(p[:, 2], cc[2] + rr[2] * (1 - flat_top) + (p[:, 2] - cc[2] - rr[2] * (1 - flat_top)) * 0.25)
        nc = (p - cc) / (rr * rr); nc /= np.linalg.norm(nc, axis=1, keepdims=True)
        ncr = (p - cen) / (crad * crad); ncr /= np.linalg.norm(ncr, axis=1, keepdims=True)
        nrm = nc * cw + ncr * (1 - cw) + R.normal(scale=0.08, size=(n, 3)); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        # yaprak yönü: yüzeye teğet, aşağı-dışa eğik
        up = np.array([0, 0, 1.0]); tang = np.cross(nc, up); tl = np.linalg.norm(tang, axis=1, keepdims=True); tang = np.where(tl > 1e-3, tang / np.maximum(tl, 1e-6), np.array([1.0, 0, 0]))
        rot = R.uniform(0, math.tau, (n, 1)); bit = np.cross(nc, tang)
        ldir = tang * np.cos(rot) + bit * np.sin(rot); ldir = ldir + nc * 0.35 - up * droop * 0.5; ldir /= np.linalg.norm(ldir, axis=1, keepdims=True)
        side = np.cross(nc, ldir); side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-6)
        s = leaf * R.uniform(0.75, 1.25, (n, 1))
        base = p - ldir * s * 0.35
        tip = base + ldir * s; mid = base + ldir * s * 0.45
        lv = mid + side * s * 0.3 + nc * s * 0.06; rv = mid - side * s * 0.3 + nc * s * 0.06
        quad = np.stack([base, lv, tip, rv], 1).reshape(-1, 3)
        V_.append(quad)
        idx = nv + np.arange(n)[:, None] * 4
        F_.append(np.concatenate([idx + np.array([0, 2, 1]), idx + np.array([0, 3, 2])], 0))
        occ = np.clip(0.42 + 0.3 * ncr[:, 2] + 0.22 * nc[:, 2] + 0.3 * (np.linalg.norm((p - cen) / crad, axis=1) - 0.75) + R.normal(scale=0.07, size=n), 0, 1)
        C_.append(np.repeat(occ, 4)); N_.append(np.repeat(nrm, 4, axis=0)); nv += n * 4
        # iç kabuk: boşluklardan gökyüzü görünmesin
        if shell:
            sh = _ico(2)
            sp = cc + sh * rr * shell
            sn = (sp - cen) / (crad * crad); sn /= np.linalg.norm(sn, axis=1, keepdims=True)
            V_.append(sp); F_.append(_ICO_F[2] + nv)
            C_.append(np.clip(0.18 + 0.35 * (sn[:, 2] * 0.5 + 0.5), 0, 1)); N_.append(sn); nv += len(sp)
    verts = np.concatenate(V_); occ = np.concatenate(C_); nrm = np.concatenate(N_)
    faces = np.concatenate([f if f.ndim == 2 else f for f in F_])
    colors = ramp3(occ, palette)
    return mesh_obj(name, verts, faces, mat, colors=colors, normals=nrm, col=col)

_ICO_V, _ICO_F = {}, {}
def _ico(sub):
    if sub not in _ICO_V:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        _ICO_V[sub] = np.array([v.co[:] for v in bm.verts], np.float32)
        _ICO_F[sub] = np.array([[v.index for v in f.verts] for f in bm.faces], np.int64); bm.free()
    return _ICO_V[sub]

PAL_BROAD = [(0.0, '#1d4a26'), (0.35, '#2f7a33'), (0.65, '#5aa83c'), (0.88, '#93cf55'), (1.0, '#c1e57a')]
PAL_BROAD2 = [(0.0, '#21502c'), (0.35, '#357f3c'), (0.65, '#62ad45'), (0.9, '#a2d460'), (1.0, '#c9e98a')]
PAL_CYPRESS = [(0.0, '#123222'), (0.4, '#1f4f31'), (0.75, '#2f6d3c'), (1.0, '#4f8f4c')]
PAL_BIRCH = [(0.0, '#2c5a26'), (0.4, '#4d8e35'), (0.75, '#86c24c'), (1.0, '#b9df73')]
PAL_PINE = [(0.0, '#173a26'), (0.4, '#24603a'), (0.75, '#3e8a45'), (1.0, '#6fb055')]
PAL_PINE_SNOW = [(0.0, '#173a26'), (0.45, '#24603a'), (0.7, '#9fbcc4'), (0.85, '#e8f0f6'), (1.0, '#ffffff')]
PAL_BROAD3 = [(0.0, '#2b4a1c'), (0.35, '#4f7a26'), (0.65, '#8aa83a'), (0.9, '#c4cf5a'), (1.0, '#e0dc82')]   # sarımsı
PAL_BROAD4 = [(0.0, '#173f2c'), (0.35, '#266b45'), (0.65, '#3f9a5a'), (0.9, '#7cc27a'), (1.0, '#a8dca0')]   # mavimsi
PAL_PINE2 = [(0.0, '#1d4226'), (0.4, '#2e7040'), (0.75, '#4f9a4c'), (1.0, '#8cc265')]
PAL_PINE3 = [(0.0, '#123327'), (0.4, '#1d5440'), (0.75, '#2f7a5a'), (1.0, '#5c9e80')]
PAL_BUSH = [(0.0, '#1f4c25'), (0.4, '#3b8434'), (0.8, '#76bb48'), (1.0, '#a9d867')]

def round_tree(name, h=8.0, seed=0, col=None, palette=PAL_BROAD, spread=1.0, fol=None, bark=None, clumps=11):
    """Yuvarlak yayvan ağaç (resimsi): eğik kalın gövde, 3-5 kol; taç = kubbe üstüne dağılmış 9-13 yumru küme
    (her küme kendi gölgesini alır → boyalı, topak topak taç)."""
    R = random.Random(seed)
    fol = fol or foliage_mat('fol_' + name); bark = bark or bark_mat()
    lean = V((R.uniform(-0.1, 0.1), R.uniform(-0.1, 0.1), 0)) * h
    k1 = V((0, 0, h * 0.34)) + lean * 0.5; top = V((0, 0, h * 0.55)) + lean
    br = [([(0, 0, -0.3), (0, 0, h * 0.12), tuple(k1), tuple(top)], [h * 0.07, h * 0.055, h * 0.045, h * 0.032])]
    cr = h * 0.34 * spread; cc = top + V((0, 0, h * 0.16)); crz = h * 0.27
    clusters = []
    for i in range(clumps):
        # kubbe yüzeyine yarı-düzenli dağılım (altın açı), alt sıra dışa taşar
        t = (i + 0.5) / clumps; zf = 1 - t * 1.25; ang = i * 2.39996 + R.uniform(-0.3, 0.3)
        rr = math.sqrt(max(0.0, 1 - min(1, zf) ** 2)) if zf > -0.2 else 0.95
        p = cc + V((math.cos(ang) * rr * cr * 0.72, math.sin(ang) * rr * cr * 0.72, max(-0.35, zf) * crz * 0.75))
        s = cr * R.uniform(0.36, 0.5) * (0.85 + 0.25 * (1 - t))
        clusters.append((p, V((s, s, s * 0.82))))
        if zf < 0.55 and R.random() < 0.8:
            base = k1 + (top - k1) * R.uniform(0.2, 1.0)
            br.append(([tuple(base), tuple((base + p) / 2 + V((0, 0, h * 0.03))), tuple(p)], [h * 0.03, h * 0.02, h * 0.01]))
    trunk_obj(name + '_trunk', br, bark, col=col)
    return crown(name + '_crown', clusters, cc, V((cr * 1.1, cr * 1.1, crz * 1.05)), palette, leaf=h * 0.038, density=520, seed=seed, col=col, mat=fol, cw=0.62)

def cypress(name, h=9.0, seed=0, col=None, fol=None, bark=None):
    R = random.Random(seed); fol = fol or foliage_mat('fol_' + name, translucent=0.15); bark = bark or bark_mat()
    trunk_obj(name + '_trunk', [([(0, 0, -0.2), (0, 0, h * 0.5)], [h * 0.03, h * 0.02])], bark, col=col)
    w = h * 0.12 * R.uniform(0.85, 1.15); clusters = []
    n = 11
    for i in range(n):
        t = i / (n - 1); z = h * (0.12 + 0.84 * t)
        rad = w * (math.sin(math.pi * (0.12 + 0.88 * t) ** 0.8) * 0.9 + 0.15) * (1.0 - 0.75 * t ** 3)
        off = V((R.uniform(-0.25, 0.25) * w, R.uniform(-0.25, 0.25) * w, 0))
        clusters.append((V((0, 0, z)) + off, V((rad * 1.0, rad * 1.0, h * 0.085))))
    return crown(name + '_crown', clusters, V((0, 0, h * 0.5)), V((w * 1.1, w * 1.1, h * 0.5)), PAL_CYPRESS, leaf=h * 0.022, density=420, seed=seed, col=col, mat=fol, droop=0.1, shell=0.8)

def birch(name, h=9.0, seed=0, col=None, fol=None, bark=None):
    R = random.Random(seed); fol = fol or foliage_mat('fol_' + name); bark = bark or bark_mat('birch_bark', white=True)
    lean = V((R.uniform(-0.08, 0.08), R.uniform(-0.08, 0.08), 0)) * h
    top = V((0, 0, h * 0.92)) + lean
    br = [([(0, 0, -0.2), tuple(V((0, 0, h * 0.4)) + lean * 0.4), tuple(top)], [h * 0.022, h * 0.017, h * 0.008])]
    clusters = []
    for i in range(R.randint(7, 10)):
        z = h * R.uniform(0.5, 0.97); ang = R.uniform(0, math.tau); rr = h * R.uniform(0.06, 0.16)
        p = V((0, 0, z)) + lean * (z / h) + V((math.cos(ang) * rr, math.sin(ang) * rr, 0))
        br.append(([tuple(V((0, 0, z * 0.9)) + lean * (z / h)), tuple(p)], [h * 0.008, h * 0.004]))
        s = h * R.uniform(0.08, 0.12); clusters.append((p + V((0, 0, s * 0.3)), V((s * 1.2, s * 1.2, s * 0.65))))
    trunk_obj(name + '_trunk', br, bark, col=col, res=7)
    return crown(name + '_crown', clusters, V((0, 0, h * 0.78)) + lean * 0.8, V((h * 0.22, h * 0.22, h * 0.22)), PAL_BIRCH, leaf=h * 0.03, density=230, seed=seed, col=col, mat=fol, shell=0.7)

def bush(name, r=1.0, seed=0, col=None, fol=None, palette=PAL_BUSH, leaf=0.16):
    R = random.Random(seed); fol = fol or foliage_mat('fol_' + name)
    clusters = [(V((R.uniform(-0.5, 0.5) * r, R.uniform(-0.5, 0.5) * r, r * R.uniform(0.35, 0.6))), V((r * R.uniform(0.5, 0.7),) * 2 + (r * 0.5,))) for _ in range(R.randint(3, 5))]
    return crown(name, clusters, V((0, 0, r * 0.4)), V((r * 1.1, r * 1.1, r * 0.75)), palette, leaf=r * leaf, density=300, seed=seed, col=col, mat=fol, droop=0.2)

def pine(name, h=10.0, seed=0, col=None, fol=None, bark=None, palette=None):
    """Katmanlı çam: koni etekler (her kat sarkan kart halkası), yumuşak koni normalleri; tepe sivri."""
    R = random.Random(seed); fol = fol or foliage_mat('fol_' + name, translucent=0.18); bark = bark or bark_mat()
    trunk_obj(name + '_trunk', [([(0, 0, -0.2), (0, 0, h * 0.55), (0, 0, h * 0.98)], [h * 0.035, h * 0.022, h * 0.006])], bark, col=col)
    Rn = np.random.default_rng(seed); tiers = 7
    V_, F_, C_, N_ = [], [], [], []; nv = 0
    for t in range(tiers):
        k = t / (tiers - 1); z0 = h * (0.16 + 0.74 * k); L = h * (0.33 - 0.27 * k) * R.uniform(0.9, 1.1)
        n = int(560 * (1.15 - k * 0.7))
        az = Rn.uniform(0, math.tau, n); s = np.sqrt(Rn.uniform(0.05, 1.0, n))
        r = L * s; drop = h * 0.12 * (s ** 1.6) * (1 - 0.4 * k) + h * 0.03 * Rn.uniform(0, 1, n)
        lump = 1 + 0.18 * np.sin(az * R.randint(5, 8) + t)
        p = np.stack([np.cos(az) * r * lump, np.sin(az) * r * lump, z0 - drop], -1)
        nr = np.stack([np.cos(az) * 0.8, np.sin(az) * 0.8, np.full(n, 0.75)], -1); nr /= np.linalg.norm(nr, axis=1, keepdims=True)
        out = np.stack([np.cos(az), np.sin(az), np.zeros(n)], -1)
        side = np.stack([-np.sin(az), np.cos(az), np.zeros(n)], -1)
        ldir = out * 0.8 + np.array([0, 0, -0.5]) + side * Rn.uniform(-0.6, 0.6, (n, 1)); ldir /= np.linalg.norm(ldir, axis=1, keepdims=True)
        sd = np.cross(nr, ldir); sd /= np.maximum(np.linalg.norm(sd, axis=1, keepdims=True), 1e-6)
        sz = h * 0.04 * Rn.uniform(0.7, 1.2, (n, 1))
        base = p - ldir * sz * 0.3; tip = base + ldir * sz; mid = base + ldir * sz * 0.5
        quad = np.stack([base, mid + sd * sz * 0.22, tip, mid - sd * sz * 0.22], 1).reshape(-1, 3)
        V_.append(quad); idx = nv + np.arange(n)[:, None] * 4
        F_.append(np.concatenate([idx + np.array([0, 2, 1]), idx + np.array([0, 3, 2])], 0))
        occ = np.clip(0.25 + 0.6 * s + 0.15 * k + Rn.normal(scale=0.07, size=n), 0, 1)
        C_.append(np.repeat(occ, 4)); N_.append(np.repeat(nr, 4, axis=0)); nv += n * 4
        # etek kabuğu (koyu iç koni)
        seg = 14; ring = []
        for q in range(seg):
            a = q / seg * math.tau; ring.append((math.cos(a) * L * 0.85, math.sin(a) * L * 0.85, z0 - h * 0.11))
        cv = np.array([(0, 0, z0 + h * 0.03)] + ring, np.float32)
        V_.append(cv); F_.append(np.array([[nv, nv + 1 + q, nv + 1 + (q + 1) % seg] for q in range(seg)]))
        C_.append(np.full(len(cv), 0.15)); N_.append(np.tile(np.array([0, 0, 1.0]), (len(cv), 1))); nv += len(cv)
    verts = np.concatenate(V_); faces = np.concatenate(F_); colors = ramp3(np.concatenate(C_), palette or PAL_PINE)
    return mesh_obj(name + '_crown', verts, faces, fol, colors=colors, normals=np.concatenate(N_), col=col)

# ------------------------------------------------------------------ iri kaya (düzlemle yontulmuş, pahlı)

def boulder(name, size=(2.0, 1.6, 1.2), seed=0, cuts=13, mat=None, col=None, bevel=0.07, top_flat=0.12):
    R = random.Random(seed)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        n = MN.noise(v.co * 1.3 + V((seed * 3.1, seed * 1.7, 0))) * 0.18
        v.co = V((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) * (1 + n)
    for c in range(cuts):
        if c == 0 and top_flat:
            nrm = V((R.uniform(-0.2, 0.2), R.uniform(-0.2, 0.2), 1)).normalized(); off = size[2] * (1 - top_flat)
        else:
            nrm = V((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(-0.4, 0.9))).normalized()
            ext = abs(nrm.x) * size[0] + abs(nrm.y) * size[1] + abs(nrm.z) * size[2]
            off = ext * R.uniform(0.5, 0.78) / (abs(nrm.x) + abs(nrm.y) + abs(nrm.z)) * 1.3
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=nrm * off, plane_no=nrm, clear_outer=True)
        edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges: bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(6), verts=bm.verts, edges=bm.edges)
    sharp = [e for e in bm.edges if e.calc_face_angle(0) > math.radians(28)]
    if bevel and sharp:
        try: bmesh.ops.bevel(bm, geom=sharp, offset=bevel * min(size), segments=3, profile=0.5, affect='EDGES', clamp_overlap=True)
        except Exception: pass
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    # büyük düz yüzler düz gölge, pah yüzleri yumuşak → yontulmuş ama yumuşak kenarlı
    areas = np.zeros(len(me.polygons)); me.polygons.foreach_get('area', areas)
    thr = np.percentile(areas, 55)
    me.polygons.foreach_set('use_smooth', (areas < thr).tolist())
    for v in me.vertices: v.co.z += 0.0
    if mat: me.materials.append(mat)
    o = bpy.data.objects.new(name, me); link(o, col)
    md = o.modifiers.new('sub', 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = 0; md.render_levels = 3
    return o

# ------------------------------------------------------------------ bulut (metatop yığını → ağ)

def cloud_mat(name='cloud_v6'):
    m, N, L, b = _mat(name)
    b.inputs['Base Color'].default_value = (1, 1, 1, 1); b.inputs['Roughness'].default_value = 1.0
    b.inputs['Subsurface Weight'].default_value = 0.0
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
    # alt yüz hafif leylak-gri, üst parlak beyaz; gölge siyah olmasın: yayma
    mr = N.new('ShaderNodeMapRange'); mr.inputs[1].default_value = -0.6; mr.inputs[2].default_value = 0.5; L.new(sep.outputs['Z'], mr.inputs[0])
    cr = N.new('ShaderNodeMix'); cr.data_type = 'RGBA'; cr.inputs[6].default_value = srgb('#c9cbe4') + (1,); cr.inputs[7].default_value = (1, 1, 1, 1)
    L.new(mr.outputs[0], cr.inputs['Factor']); L.new(cr.outputs[2], b.inputs['Base Color'])
    b.inputs['Emission Color'].default_value = srgb('#e8effc') + (1,); b.inputs['Emission Strength'].default_value = 0.3
    return m

def cumulus(name, size=60.0, seed=0, mat=None, col=None, res=None, tall=1.0):
    """Yığma bulut: düz taban + 2-3 kule gövde; yüzeyde üç kademe kabarcık (iri → küçük) → karnabahar, yumuşak kenar."""
    R = random.Random(seed)
    mb = bpy.data.metaballs.new(name + '_mb'); r0 = res or size * 0.016; mb.resolution = r0; mb.render_resolution = r0; mb.threshold = 0.6
    o = bpy.data.objects.new(name + '_mbo', mb); bpy.context.scene.collection.objects.link(o)
    def add(c, r, typ='BALL', sz=1.0):
        e = mb.elements.new(); e.co = c; e.radius = r; e.stiffness = 1.25; e.type = typ
        if typ == 'ELLIPSOID': e.size_z = sz
    body = []
    for t in range(R.randint(2, 3)):
        x0 = R.uniform(-0.28, 0.28) * size; ht = size * R.uniform(0.25, 0.45) * tall
        for k in range(4):
            c = V((x0 + R.gauss(0, size * 0.05), R.gauss(0, size * 0.05), ht * (0.25 + 0.22 * k))); r = size * (0.2 - 0.03 * k) * R.uniform(0.85, 1.1)
            body.append((c, r)); add(c, r)
    for lvl, (n, f) in enumerate(((28, (0.38, 0.58)), (55, (0.22, 0.34)), (50, (0.13, 0.2)))):
        for i in range(n):
            c, r = R.choice(body); d = V((R.gauss(0, 1), R.gauss(0, 0.7), abs(R.gauss(0.4, 0.9)))).normalized()
            add(c + d * r * R.uniform(0.85, 1.05), r * R.uniform(*f))
    for i in range(7):
        add(V((R.gauss(0, size * 0.25), R.gauss(0, size * 0.07), size * 0.03)), size * 0.17, 'ELLIPSOID', 0.3)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o); bpy.data.metaballs.remove(mb)
    for v in me.vertices:
        if v.co.z < 0: v.co.z = v.co.z * 0.15
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if mat: me.materials.append(mat)
    c = bpy.data.objects.new(name, me); link(c, col)
    c.visible_shadow = False
    return c

# ------------------------------------------------------------------ çiçek, kütük, kamp

def flower_patch_mesh(name, kind='bell', n=1, seed=0, col=None):
    """Tek çiçek demeti (sapı + başlar), parçacıkla serpilir. bell: mavi-mor çan dizisi; daisy: turuncu/sarı yıldız."""
    R = random.Random(seed); V_, F_, C_ = [], [], []
    stem = srgb('#3d7a2e')
    def add(verts, faces, c):
        o = len(V_); V_.extend(verts); F_.extend([tuple(i + o for i in f) for f in faces]); C_.extend([c] * len(verts))
    for s in range(n):
        bx, by = R.uniform(-0.12, 0.12), R.uniform(-0.12, 0.12); hh = R.uniform(0.22, 0.38)
        lean = V((R.uniform(-0.05, 0.05), R.uniform(-0.05, 0.05), 0))
        add([(bx - 0.006, by, 0), (bx + 0.006, by, 0), (bx + lean.x + 0.004, by + lean.y, hh), (bx + lean.x - 0.004, by + lean.y, hh)], [(0, 1, 2, 3)], stem)
        if kind == 'bell':
            cs = [srgb('#5a5fe0'), srgb('#7a72f0'), srgb('#9a8cf5'), srgb('#4b55c8')]
            for b in range(R.randint(5, 8)):
                t = 0.45 + 0.55 * b / 8; p = V((bx, by, 0)) + (V((lean.x, lean.y, hh))) * t + V((R.uniform(-0.025, 0.025), R.uniform(-0.025, 0.025), 0))
                r = 0.018 * (1.2 - t * 0.4)
                ico = _ico(1); add([tuple(p + V((q[0] * r, q[1] * r, q[2] * r * 1.2))) for q in ico], [tuple(f) for f in _ICO_F[1]], R.choice(cs))
        else:
            c = R.choice([srgb('#f4cf3a'), srgb('#f7dc5a'), srgb('#c79ae8')]) if kind == 'yellow' else R.choice([srgb('#f08a3a'), srgb('#f6a648'), srgb('#f4c454'), srgb('#ee7a52')])
            p = V((bx + lean.x, by + lean.y, hh * (0.6 if kind == 'yellow' else 1.0))); r = R.uniform(0.03, 0.045) * (0.7 if kind == 'yellow' else 1.0); k = 6
            ring = [tuple(p + V((math.cos(a) * r, math.sin(a) * r, R.uniform(-0.005, 0.01)))) for a in [i / k * math.tau for i in range(k)]]
            add([tuple(p + V((0, 0, 0.01)))] + ring, [(0, 1 + i, 1 + (i + 1) % k) for i in range(k)], c)
    return mesh_obj(name, V_, F_, vcol_mat(name + '_m', rough=0.6), colors=np.array(C_), col=col)

def rings_mat(name='wood_rings'):
    m, N, L, b = _mat(name)
    tc = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.rings_direction = 'Z'
    wv.inputs['Scale'].default_value = 2.5; wv.inputs['Distortion'].default_value = 3; L.new(tc.outputs['Object'], wv.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); r = cr.color_ramp; r.elements[0].color = srgb('#c9a273') + (1,); r.elements[1].color = srgb('#e8cfa2') + (1,)
    L.new(wv.outputs['Fac'], cr.inputs[0]); L.new(cr.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.85
    return m

def stump(name, r=0.6, h=0.7, seed=0, col=None, bark=None):
    """Kesik kütük: dibi kökler gibi genişleyen gövde, üstü testere dişli kırık kenar, kesitte yıllık halkalar."""
    R = random.Random(seed); bark = bark or bark_mat(); seg = 18; rows = 6
    verts, faces = [], []
    for i in range(rows):
        t = i / (rows - 1); z = h * t
        for k in range(seg):
            a = k / seg * math.tau
            rr = r * (1 + 0.45 * (1 - t) ** 3 * (0.6 + 0.4 * math.sin(a * 5 + seed))) * (1 + MN.noise(V((math.cos(a) * 2, math.sin(a) * 2, t * 2 + seed))) * 0.1)
            zz = z
            if i == rows - 1: zz = h + (R.uniform(0.0, 0.35) * h if k % 3 == 0 else R.uniform(-0.05, 0.08) * h)
            verts.append((math.cos(a) * rr, math.sin(a) * rr, zz - (0.15 if i == 0 else 0)))
    for i in range(rows - 1):
        for k in range(seg): faces.append((i * seg + k, i * seg + (k + 1) % seg, (i + 1) * seg + (k + 1) % seg, (i + 1) * seg + k))
    o = mesh_obj(name, verts, faces, bark, col=col)
    top = [(math.cos(k / seg * math.tau) * r * 0.93, math.sin(k / seg * math.tau) * r * 0.93, h * 0.98) for k in range(seg)]
    mesh_obj(name + '_top', [(0, 0, h * 1.0)] + top, [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)], rings_mat(), col=col)
    return o

def log(name, length=3.0, r=0.3, seed=0, col=None, bark=None):
    bark = bark or bark_mat(); R = random.Random(seed)
    pts = [(-length / 2 + length * t, R.uniform(-0.05, 0.05) * length * t * (1 - t), r) for t in np.linspace(0, 1, 6)]
    o = trunk_obj(name, [(pts, [r * 1.05, r, r * 0.98, r * 0.97, r * 0.95, r * 0.9])], bark, col=col, res=12)
    for sgn, (x, y, z), rr in ((-1, pts[0], r * 1.05), (1, pts[-1], r * 0.9)):
        cap = [(x, y + math.cos(a) * rr, z + math.sin(a) * rr) for a in np.linspace(0, math.tau, 13)[:-1]]
        mesh_obj(name + '_cap', [(x, y, z)] + cap, [(0, 1 + k, 1 + (k + 1) % 12) for k in range(12)], rings_mat(), col=col)
    return o

def campfire(name, col=None, seed=0, stone_mat=None):
    R = random.Random(seed); objs = []
    sm = stone_mat or rock_mat('fire_stone', base='#6f6a6e', dark='#3f3a40', light='#8d878a', moss_amt=0.0)
    for k in range(10):
        a = k / 10 * math.tau; o = boulder(name + '_s%d' % k, (0.16, 0.13, 0.1), seed=seed + k, cuts=5, mat=sm, col=col, bevel=0.1, top_flat=0.0)
        o.location = (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.03)
    bark = bark_mat()
    for k in range(4):
        a = k / 4 * math.tau + 0.3
        trunk_obj(name + '_w%d' % k, [([(math.cos(a) * 0.45, math.sin(a) * 0.45, 0.05), (0, 0, 0.45)], [0.06, 0.04])], bark, col=col)
    fm, N, L, b = _mat(name + '_flame')
    b.inputs['Base Color'].default_value = srgb('#ffb347') + (1,); b.inputs['Emission Color'].default_value = srgb('#ff9a2e') + (1,); b.inputs['Emission Strength'].default_value = 9.0
    for k in range(5):
        a = k / 5 * math.tau; rr = 0.12; hh = R.uniform(0.5, 0.8)
        v = [(math.cos(a) * rr + math.cos(t) * 0.09, math.sin(a) * rr + math.sin(t) * 0.09, 0.1) for t in np.linspace(0, math.tau, 7)[:-1]] + [(math.cos(a) * 0.05, math.sin(a) * 0.05, 0.1 + hh)]
        mesh_obj(name + '_f%d' % k, v, [(i, (i + 1) % 6, 6) for i in range(6)], fm, col=col)
    ld = bpy.data.lights.new(name + '_l', 'POINT'); ld.energy = 140; ld.color = srgb('#ffa04a'); ld.shadow_soft_size = 0.3
    lo = bpy.data.objects.new(name + '_l', ld); lo.location = (0, 0, 0.6); link(lo, col)

def beehive(name, col=None):
    m, N, L, b = _mat(name + '_m')
    tc = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.bands_direction = 'Z'; wv.inputs['Scale'].default_value = 4
    L.new(tc.outputs['Object'], wv.inputs['Vector']); cr = N.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = srgb('#6b4524') + (1,); cr.color_ramp.elements[1].color = srgb('#b07a3e') + (1,)
    L.new(wv.outputs['Fac'], cr.inputs[0]); L.new(cr.outputs['Color'], b.inputs['Base Color'])
    ico = _ico(2); v = [(q[0] * 0.28, q[1] * 0.28, q[2] * 0.36 * (1 + 0.15 * q[2])) for q in ico]
    return mesh_obj(name, v, _ICO_F[2], m, col=col)

# ------------------------------------------------------------------ yakın plan: çim telleri (numpy), yaprak demeti

def grass_blade_mat(name, base='#2f7a1f', mid='#6cb83a', tip='#d2ea62', translucent=0.42):
    """Çim teli: kök koyu → uç açık limon, tel başına ton oynaması, arkadan güneşte parlayan yarı saydamlık."""
    m, N, L, b = _mat(name)
    uv = N.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'; sep = N.new('ShaderNodeSeparateXYZ'); L.new(uv.outputs['UV'], sep.inputs[0])
    r = N.new('ShaderNodeValToRGB'); cr = r.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = srgb(base) + (1,); cr.elements[1].position = 1.0; cr.elements[1].color = srgb(tip) + (1,)
    e = cr.elements.new(0.45); e.color = srgb(mid) + (1,); L.new(sep.outputs['Y'], r.inputs[0])
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'rnd'
    hs = N.new('ShaderNodeHueSaturation'); L.new(r.outputs['Color'], hs.inputs['Color'])
    m1 = N.new('ShaderNodeMapRange'); m1.inputs[3].default_value = 0.47; m1.inputs[4].default_value = 0.53; L.new(at.outputs['Fac'], m1.inputs[0]); L.new(m1.outputs[0], hs.inputs['Hue'])
    m2 = N.new('ShaderNodeMapRange'); m2.inputs[3].default_value = 0.78; m2.inputs[4].default_value = 1.12; L.new(at.outputs['Fac'], m2.inputs[0]); L.new(m2.outputs[0], hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.55; b.inputs['Specular IOR Level'].default_value = 0.35
    tr = N.new('ShaderNodeBsdfTranslucent'); L.new(hs.outputs['Color'], tr.inputs['Color'])
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = translucent
    L.new(b.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], N['Material Output'].inputs['Surface'])
    return m

def fast_blades(name, P, mat, h=(0.12, 0.27), w=(0.008, 0.017), bend=0.5, segs=3, seed=1, col=None, normal_up=True):
    """P: (n,4) x,y,z,ölçek → tek ağda n çim teli (numpy ile; milyonlarca tel saniyeler içinde)."""
    R = np.random.default_rng(seed); n = len(P)
    if n == 0: return None
    hh = R.uniform(*h, n) * P[:, 3]; ww = R.uniform(*w, n) * (0.75 + 0.25 * P[:, 3])
    a = R.uniform(0, math.tau, n); ca, sa = np.cos(a), np.sin(a)
    lean = R.uniform(0.1, 1.0, n) * bend; la = R.uniform(0, math.tau, n); lx, ly = np.cos(la) * lean, np.sin(la) * lean
    rv = R.uniform(0, 1, n)
    rows = segs + 1; V_ = np.zeros((n, rows, 2, 3), np.float32); UV = np.zeros((n, rows, 2, 2), np.float32)
    for i in range(rows):
        t = i / segs; wd = ww * (1 - t) ** 0.85 + 0.0006
        ox, oy = lx * hh * t * t, ly * hh * t * t; z = P[:, 2] + hh * t * (1 - 0.25 * lean * t)
        V_[:, i, 0] = np.stack([P[:, 0] - ca * wd / 2 + ox, P[:, 1] - sa * wd / 2 + oy, z], -1)
        V_[:, i, 1] = np.stack([P[:, 0] + ca * wd / 2 + ox, P[:, 1] + sa * wd / 2 + oy, z], -1)
        UV[:, i, 0] = (0, t); UV[:, i, 1] = (1, t)
    verts = V_.reshape(-1, 3); base = (np.arange(n) * rows * 2)[:, None]
    q = []
    for i in range(segs):
        j = i * 2; q.append(np.stack([j, j + 1, j + 3, j + 2], -1))
    quads = (np.array(q)[None, :, :] + base[:, :, None]).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
    me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', (np.arange(len(quads)) * 4).astype(np.int32)); me.polygons.foreach_set('loop_total', np.full(len(quads), 4, np.int32))
    me.update()
    me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    uvl = me.uv_layers.new(name='UVMap'); uvv = UV.reshape(-1, 2)[quads.ravel()]; uvl.data.foreach_set('uv', uvv.ravel())
    at = me.attributes.new('rnd', 'FLOAT', 'POINT'); at.data.foreach_set('value', np.repeat(rv, rows * 2).astype(np.float32))
    if normal_up:   # çim teli yukarı bakan normalle gölgelenir: zemin gibi yumuşak, tel tel parıldamaz
        nn = np.zeros((len(verts), 3), np.float32); nn[:, 2] = 1.0
        nn[:, 0] = np.repeat(ca * 0.25, rows * 2); nn[:, 1] = np.repeat(sa * 0.25, rows * 2)
        nn /= np.linalg.norm(nn, axis=1, keepdims=True); me.normals_split_custom_set_from_vertices(nn)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); link(o, col); return o

def rosette(name, n=10, length=0.9, width=0.12, seed=0, col=None, cols=('#2f6e22', '#5aa335', '#b6db5c'), mat=None):
    """Geniş yapraklı demet (eğrelti benzeri): kökten kavisli, uca doğru sivri uzun yapraklar."""
    R = random.Random(seed); vs, fs, cs = [], [], []
    for i in range(n):
        a = i / n * math.tau + R.uniform(-0.2, 0.2); L = length * R.uniform(0.7, 1.15); up = R.uniform(0.9, 1.5); segs = 6
        d = V((math.cos(a), math.sin(a), 0)); side = V((-d.y, d.x, 0))
        o = len(vs)
        for k in range(segs + 1):
            t = k / segs; p = d * (L * t * 0.75) + V((0, 0, L * (up * t - (up + 0.6) * t * t * 0.9)))
            wd = width * math.sin(math.pi * min(1, 0.1 + t * 0.95)) * (1.0 if k < segs else 0.0)
            fold = V((0, 0, -wd * 0.4))
            vs += [tuple(p + side * wd + fold), tuple(p + V((0, 0, 0.005))), tuple(p - side * wd + fold)]; cs += [t] * 3
        for k in range(segs):
            b = o + k * 3; fs += [(b, b + 3, b + 4, b + 1), (b + 1, b + 4, b + 5, b + 2)]
    colors = ramp3(np.array(cs), [(0.0, cols[0]), (0.5, cols[1]), (1.0, cols[2])])
    return mesh_obj(name, vs, fs, mat or foliage_mat(name + '_m', translucent=0.35), colors=colors, col=col)

def mushroom(name, h=0.12, seed=0, col=None, cap='#e8743a'):
    R = random.Random(seed); m1 = vcol_mat(name + '_m', rough=0.5)
    ico = _ico(2); r = h * 0.7
    cv = [(q[0] * r, q[1] * r, h + max(-0.15, q[2]) * r * 0.55) for q in ico]
    sv = [(q[0] * h * 0.16, q[1] * h * 0.16, (q[2] * 0.5 + 0.5) * h) for q in ico]
    cc = ramp3(np.array([(q[2] * 0.5 + 0.5) for q in ico]), [(0.0, '#f2e6cf'), (0.45, '#f2e6cf'), (0.5, cap), (1.0, cap)])
    sc = np.tile(np.array(srgb('#efe6d4')), (len(ico), 1))
    return mesh_obj(name, cv + sv, np.concatenate([_ICO_F[2], _ICO_F[2] + len(ico)]), m1, colors=np.concatenate([cc, sc]), col=col)
