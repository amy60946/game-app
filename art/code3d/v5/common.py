# v5 ortak araçlar (20 Ekim 2026): "painterly" yarı-gerçekçi ada sahneleri için gökyüzü, ışık, arazi, kaya, çim.
# Tüm biçimler kodla ve özgün üretilir; kullanıcının referans görselleri yalnız kalite/hava hedefi (kopyalanmaz).
import bpy, bmesh, math, random, mathutils
V = mathutils.Vector


def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)


def reset(samples=56, size=(1600, 900)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'; sc.view_settings.exposure = -0.15
    return sc


def sky(sc, strength=1.0, cloud_amt=0.55, top='#3f7fd8', mid='#8fc0f0', hor='#e8eef4', seed=0.0):
    """Boyalı gökyüzü: yukarıdan ufka renk geçişi + gürültüyle yumuşak, yığma bulutlar (dünya gölgelendiricisi)."""
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new('ShaderNodeOutputWorld'); bg = N.new('ShaderNodeBackground'); bg.inputs[1].default_value = strength
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    # Generated (dünya) = görüş yönü; z yükseklik
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = 0.0; r.elements[0].color = srgb(hor)
    r.elements[1].position = 0.55; r.elements[1].color = srgb(top)
    e = r.elements.new(0.16); e.color = srgb(mid)
    L.new(sep.outputs['Z'], ramp.inputs[0])
    # bulutlar: yön vektöründen gürültü, yükseklikle kısılır
    vm = N.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY'; vm.inputs[1].default_value = (1.6, 1.6, 4.5)
    L.new(tc.outputs['Generated'], vm.inputs[0])
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 2.2; noise.inputs['Detail'].default_value = 6
    noise.noise_dimensions = '4D'; noise.inputs['Roughness'].default_value = 0.55; noise.inputs['W'].default_value = seed
    L.new(vm.outputs[0], noise.inputs['Vector'])
    cr = N.new('ShaderNodeMapRange'); cr.inputs[1].default_value = 0.78 - cloud_amt * 0.4; cr.inputs[2].default_value = 0.78 - cloud_amt * 0.4 + 0.1
    L.new(noise.outputs['Fac'], cr.inputs[0])
    band = N.new('ShaderNodeMapRange'); band.inputs[1].default_value = 0.02; band.inputs[2].default_value = 0.12
    L.new(sep.outputs['Z'], band.inputs[0])
    fade = N.new('ShaderNodeMath'); fade.operation = 'MULTIPLY'; L.new(cr.outputs[0], fade.inputs[0]); L.new(band.outputs[0], fade.inputs[1])
    # bulut gölgeli alt yüzü: gürültü detayından hafif mor-gri
    shade = N.new('ShaderNodeMix'); shade.data_type = 'RGBA'
    shade.inputs['A'].default_value = srgb('#b9b6d2'); shade.inputs['B'].default_value = srgb('#ffffff')
    sh2 = N.new('ShaderNodeMapRange'); sh2.inputs[1].default_value = 0.45; sh2.inputs[2].default_value = 0.7
    L.new(noise.outputs['Fac'], sh2.inputs[0]); L.new(sh2.outputs[0], shade.inputs['Factor'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L.new(fade.outputs[0], mix.inputs['Factor']); L.new(ramp.outputs['Color'], mix.inputs['A']); L.new(shade.outputs['Result'], mix.inputs['B'])
    L.new(mix.outputs['Result'], bg.inputs['Color']); L.new(bg.outputs[0], out.inputs[0])
    return w


def sun(elev=38, azim=-40, energy=4.2, col='#fff1d8', angle=1.2):
    """Yönlü sinematik güneş: sıcak ışık; gölgeleri soğuk mavi gök dolgusu boyar."""
    s = bpy.data.lights.new('sun', 'SUN'); s.energy = energy; s.color = srgb(col)[:3]; s.angle = math.radians(angle)
    o = bpy.data.objects.new('sun', s); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    return o


def camera(loc, look, lens=32):
    cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.clip_end = 2000
    o = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(o)
    o.location = V(loc); o.rotation_euler = (V(look) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    return o


def link(name, me, m=None):
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    if m: me.materials.append(m)
    return o


def smooth_all(me):
    for p in me.polygons: p.use_smooth = True


def grid_terrain(name, size, res, hfunc, m=None, colfunc=None):
    """Izgara arazi: hfunc(x, y) yükseklik; colfunc(x, y, z, n) → (r,g,b) köşe rengi ("Col")."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=res, size=size / 2)
    for v in bm.verts:
        v.co.z = hfunc(v.co.x, v.co.y)
    bm.normal_update()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    smooth_all(me)
    if colfunc:
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        for i, v in enumerate(me.vertices):
            c = colfunc(v.co.x, v.co.y, v.co.z, v.normal)
            ca.data[i].color = (c[0], c[1], c[2], 1.0)
    return link(name, me, m)


def vcol_mat(name, rough=0.85, bump=0.25, attr='Col'):
    """Köşe rengi + el boyaması hissi veren hafif gürültü tonlaması + yumuşak tümsek."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    ca = N.new('ShaderNodeVertexColor'); ca.layer_name = attr
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 4
    tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'OVERLAY'; tint.inputs['Factor'].default_value = 0.35
    L.new(ca.outputs['Color'], tint.inputs['A']); L.new(nz.outputs['Fac'], tint.inputs['B'])
    L.new(tint.outputs['Result'], b.inputs['Base Color'])
    if bump:
        bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump
        n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 18; n2.inputs['Detail'].default_value = 3
        L.new(n2.outputs['Fac'], bn.inputs['Height']); L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m


def rock_mat(name='rock', base='#9a9488', dark='#6f6a66', moss='#5f9a3a', moss_amt=0.55, warm='#b8a68e'):
    """Kaya: üst yüzlerde (dünya normali z) gürültülü yosun/çim örtüsü, yanlarda gri-sıcak katmanlar, girintilerde koyu."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.8
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 1.6; n1.inputs['Detail'].default_value = 5
    L.new(tc.outputs['Object'], n1.inputs['Vector'])
    # katman çizgileri (tabaka): z'ye göre dalga
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'; wv.inputs['Scale'].default_value = 1.4
    wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    stone = N.new('ShaderNodeMix'); stone.data_type = 'RGBA'
    stone.inputs['A'].default_value = srgb(dark); stone.inputs['B'].default_value = srgb(base)
    L.new(n1.outputs['Fac'], stone.inputs['Factor'])
    st2 = N.new('ShaderNodeMix'); st2.data_type = 'RGBA'; st2.inputs['Factor'].default_value = 0.0
    wvr = N.new('ShaderNodeMapRange'); wvr.inputs[1].default_value = 0.55; wvr.inputs[2].default_value = 0.9; wvr.inputs[4].default_value = 0.35
    L.new(wv.outputs['Fac'], wvr.inputs[0]); L.new(wvr.outputs[0], st2.inputs['Factor'])
    L.new(stone.outputs['Result'], st2.inputs['A']); st2.inputs['B'].default_value = srgb(warm)
    # yosun maskesi: normal z + gürültü
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'
    nzm = N.new('ShaderNodeMath'); nzm.operation = 'MULTIPLY'; nzm.inputs[1].default_value = 0.35
    L.new(n1.outputs['Fac'], nzm.inputs[0]); L.new(sep.outputs['Z'], add.inputs[0]); L.new(nzm.outputs[0], add.inputs[1])
    mr = N.new('ShaderNodeMapRange'); mr.inputs[1].default_value = 1.15 - moss_amt * 0.5; mr.inputs[2].default_value = 1.2 - moss_amt * 0.5
    L.new(add.outputs[0], mr.inputs[0])
    mosscol = N.new('ShaderNodeMix'); mosscol.data_type = 'RGBA'
    mosscol.inputs['A'].default_value = srgb('#4f8a2e'); mosscol.inputs['B'].default_value = srgb(moss)
    L.new(n1.outputs['Fac'], mosscol.inputs['Factor'])
    fin = N.new('ShaderNodeMix'); fin.data_type = 'RGBA'
    L.new(mr.outputs[0], fin.inputs['Factor']); L.new(st2.outputs['Result'], fin.inputs['A']); L.new(mosscol.outputs['Result'], fin.inputs['B'])
    # girintiler: pointiness ile koyulaştır
    pt = N.new('ShaderNodeMapRange'); pt.inputs[1].default_value = 0.42; pt.inputs[2].default_value = 0.55; pt.inputs[3].default_value = 0.65; pt.inputs[4].default_value = 1.08
    L.new(geo.outputs['Pointiness'], pt.inputs[0])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    L.new(fin.outputs['Result'], mul.inputs['A'])
    cmb = N.new('ShaderNodeCombineXYZ'); L.new(pt.outputs[0], cmb.inputs[0]); L.new(pt.outputs[0], cmb.inputs[1]); L.new(pt.outputs[0], cmb.inputs[2])
    L.new(cmb.outputs[0], mul.inputs['B'])
    L.new(mul.outputs['Result'], b.inputs['Base Color'])
    bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.35; L.new(n1.outputs['Fac'], bn.inputs['Height'])
    L.new(bn.outputs['Normal'], b.inputs['Normal'])
    return m


def rock(name, loc, size, m, seed=0, flat=1.0, sharp=0.7, rot=0.0, sub=3, tall=1.0, thin=1.0):
    """Düşük çokgen kaya: ikosfer + katmanlı gürültü + yassılaştırma, yumuşak gölgelendirme (smooth shading)."""
    rnd = random.Random(seed)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    off = V((rnd.random() * 50, rnd.random() * 50, rnd.random() * 50))
    for v in bm.verts:
        p = v.co.copy()
        n = mathutils.noise.noise(p * 1.1 + off) * 0.35 + mathutils.noise.noise(p * 2.7 + off) * 0.12
        # yontulmuş yüzeyler: düzlemsel kırpma
        p = p * (1.0 + n)
        p.z *= flat * tall; p.y *= thin
        if p.z < -0.15 * tall: p.z = -0.15 * tall + (p.z + 0.15 * tall) * 0.25
        v.co = p
    for _ in range(int(sharp * 20)):
        d = V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))).normalized()
        k = rnd.uniform(0.38, 0.72)
        for v in bm.verts:
            t = v.co.dot(d)
            if t > k: v.co -= d * (t - k) * 0.97
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    smooth_all(me)
    o = link(name, me, m)
    o.location = V(loc); o.scale = (size, size * rnd.uniform(0.8, 1.15), size); o.rotation_euler = (rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), rot)
    return o


def grass_mat(name='grass', base='#2f6b1f', tip='#a8d94a', translucent=0.35):
    """Çim teli: kökten uca renk + arkadan vuran güneşte parlayan yarı saydamlık (translucency)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.6
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['UV'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = srgb(base); r.elements[1].color = srgb(tip)
    L.new(sep.outputs['Y'], ramp.inputs[0])
    # tel başına ton çeşitliliği
    oi = N.new('ShaderNodeAttribute'); oi.attribute_name = 'rnd'; hv = N.new('ShaderNodeHueSaturation')
    rr = N.new('ShaderNodeMapRange'); rr.inputs[3].default_value = 0.47; rr.inputs[4].default_value = 0.53
    L.new(oi.outputs['Fac'], rr.inputs[0]); L.new(rr.outputs[0], hv.inputs['Hue'])
    vv = N.new('ShaderNodeMapRange'); vv.inputs[3].default_value = 0.8; vv.inputs[4].default_value = 1.15
    L.new(oi.outputs['Fac'], vv.inputs[0]); L.new(vv.outputs[0], hv.inputs['Value'])
    L.new(ramp.outputs['Color'], hv.inputs['Color'])
    L.new(hv.outputs['Color'], b.inputs['Base Color'])
    tr = N.new('ShaderNodeBsdfTranslucent'); L.new(hv.outputs['Color'], tr.inputs['Color'])
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = translucent
    out = N['Material Output']
    L.new(b.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
    return m


def blade_mesh(name='blade', h=1.0, w=0.06, segs=4, bend=0.25):
    """Tek çim teli (uca doğru incelen, kavisli şerit); UV.y kökten uca 0→1."""
    bm = bmesh.new(); uv_l = bm.loops.layers.uv.new('UVMap')
    rows = []
    for i in range(segs + 1):
        t = i / segs; ww = w * (1 - t) ** 0.9 + 0.002
        y = bend * t * t
        rows.append((bm.verts.new((-ww / 2, y, h * t)), bm.verts.new((ww / 2, y, h * t)), t))
    for i in range(segs):
        a, b2, t0 = rows[i]; c, d, t1 = rows[i + 1]
        f = bm.faces.new((a, b2, d, c))
        for lp, uv in zip(f.loops, ((0, t0), (1, t0), (1, t1), (0, t1))): lp[uv_l].uv = uv
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth_all(me)
    return me


def scatter(target, inst_obj, count, seed, length=0.18, rand_size=0.5, vgroup=None, normal_align=0.1, collection=None):
    """Hair parçacık sistemiyle yüzeye örnek dağıt (çim, çiçek, çakıl)."""
    ps = target.modifiers.new(inst_obj.name if inst_obj else 'ps', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings; st.type = 'HAIR'; st.count = count; st.hair_length = length; st.use_advanced_hair = True
    st.render_type = 'COLLECTION' if collection else 'OBJECT'
    if collection: st.instance_collection = collection; st.use_collection_pick_random = True
    else: st.instance_object = inst_obj
    st.particle_size = 1.0; st.size_random = rand_size
    st.use_rotations = True; st.rotation_mode = 'NOR'; st.phase_factor_random = 2.0; st.rotation_factor_random = normal_align
    ps.seed = seed
    if vgroup: ps.vertex_group_density = vgroup
    return ps


def stash(o):
    """Örnek kaynak nesneyi görüş dışına al (gizlenirse parçacık örnekleri de görünmez)."""
    o.location = V((0, 0, -500)); return o


def hide(o):
    o.hide_render = True; o.hide_viewport = True
    if o.name in bpy.context.scene.collection.objects: pass
    return o


def blades(name, pts, m, h=(0.12, 0.28), w=(0.012, 0.03), segs=3, bend=0.35, seed=1):
    """Çim telleri tek ağda: pts = [(x, y, z, ölçek)]. Her tel uca doğru incelen, rastgele yöne kavisli şerit;
    UV.y kökten uca, 'rnd' (köşe başına tel rengi çeşitliliği)."""
    rnd = random.Random(seed)
    verts = []; faces = []; uvs = []; rv = []
    for (x, y, z, k) in pts:
        hh = rnd.uniform(*h) * k; ww = rnd.uniform(*w) * (0.7 + 0.3 * k)
        a = rnd.uniform(0, math.tau); ca, sa = math.cos(a), math.sin(a)
        lean = rnd.uniform(0.1, 1.0) * bend; la = rnd.uniform(0, math.tau)
        lx, ly = math.cos(la) * lean, math.sin(la) * lean
        r = rnd.random(); base = len(verts)
        for i in range(segs + 1):
            t = i / segs; wd = ww * (1 - t) ** 0.85 + 0.0006
            ox, oy = lx * hh * t * t, ly * hh * t * t
            verts.append((x - ca * wd / 2 + ox, y - sa * wd / 2 + oy, z + hh * t * (1 - 0.25 * lean * t)))
            verts.append((x + ca * wd / 2 + ox, y + sa * wd / 2 + oy, z + hh * t * (1 - 0.25 * lean * t)))
            uvs += [(0, t), (1, t)]; rv += [r, r]
        for i in range(segs):
            j = base + i * 2; faces.append((j, j + 1, j + 3, j + 2))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    at = me.attributes.new('rnd', 'FLOAT', 'POINT'); at.data.foreach_set('value', rv)
    smooth_all(me)
    return link(name, me, m)


def daisies(name, pts, seed=3, petal='#ffffff', heart='#f2c230', r=(0.03, 0.05)):
    """Papatya/çiçek başları: kısa sap + düz taç yaprak halkası + göbek (tek ağ, iki malzeme)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    for (x, y, z, k) in pts:
        rr = rnd.uniform(*r) * k; hz = z + rnd.uniform(0.08, 0.2) * k
        c = bm.verts.new((x, y, hz + 0.004)); ring = []
        n = 8
        for i in range(n * 2):
            a = i / (n * 2) * math.tau; rad = rr if i % 2 == 0 else rr * 0.45
            ring.append(bm.verts.new((x + math.cos(a) * rad, y + math.sin(a) * rad, hz - (0.01 if i % 2 == 0 else 0))))
        for i in range(n * 2):
            f = bm.faces.new((c, ring[i], ring[(i + 1) % (n * 2)])); f.material_index = 0
        hc = [bm.verts.new((x + math.cos(i / 6 * math.tau) * rr * 0.3, y + math.sin(i / 6 * math.tau) * rr * 0.3, hz + 0.008)) for i in range(6)]
        f = bm.faces.new(hc); f.material_index = 1
        s0 = bm.verts.new((x, y, z)); s1 = bm.verts.new((x + 0.004, y, z)); s2 = bm.verts.new((x + 0.004, y, hz)); s3 = bm.verts.new((x, y, hz))
        f = bm.faces.new((s0, s1, s2, s3)); f.material_index = 2
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(name, me)
    for hexc in (petal, heart, '#3f7a24'):
        mm = bpy.data.materials.new(name + hexc); mm.use_nodes = True
        bb = mm.node_tree.nodes['Principled BSDF']; bb.inputs['Base Color'].default_value = srgb(hexc); bb.inputs['Roughness'].default_value = 0.6
        me.materials.append(mm)
    return o
