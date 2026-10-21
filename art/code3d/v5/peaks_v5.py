# Ön tasarım v5 (20 Ekim 2026): G5 vadi + katmanlı dağlar, G6 karlı zirve, G7 eriyen kar zemini.
#   /tmp/claude-0/bpyenv/bin/python -I peaks_v5.py -- <çıktı_klasörü> [g5 g6 g7]
# Resimsi, yarı gerçekçi stilize: düşük çokgen yükseklik alanları + yumuşak gölgeleme, köşe rengiyle boyanmış biyom
# (dik yamaç = kaya, düz basamak = çim/kar), kameraya uzaklıkla maviye kayan hava perspektifi (Unity'de mesafe sisi).
# Kullanıcının referans görselleri yalnız hava/kalite hedefi; her şey kodla, özgün.
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import bpy, bmesh
from mathutils import Vector as V, noise as N
import kit
from kit import srgb, mat
from assets_town import lush, rock
from assets_v3 import smooth, link_mesh

def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

def lerp3(a, b, t): return a.lerp(b, max(0.0, min(1.0, t)))
def C(h): return V(srgb(h)[:3])

# ------------------------------------------------------------------ gökyüzü (stilize: dikey geçiş + gürültü bulutlar)

def sky(sc, top, mid, horizon, cloud, cloud_shadow, sun_dir, sun_col, strength=1.0, clouds=0.55):
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    n.clear()
    out = n.new('ShaderNodeOutputWorld'); bg = n.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs[0])
    rp = n.new('ShaderNodeValToRGB'); cr = rp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = srgb(horizon)
    cr.elements[1].position = 0.55; cr.elements[1].color = srgb(top)
    e = cr.elements.new(0.12); e.color = srgb(mid)
    l.new(sep.outputs['Z'], rp.inputs['Fac'])
    # bulutlar: yatay uzatılmış gürültü eşiği, altı gölgeli
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.2, 1.2, 3.5)
    l.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.6; nz.inputs['Detail'].default_value = 5; nz.inputs['Roughness'].default_value = 0.55
    l.new(mp.outputs[0], nz.inputs['Vector'])
    cm = n.new('ShaderNodeValToRGB'); c2 = cm.color_ramp
    c2.elements[0].position = clouds; c2.elements[0].color = (0, 0, 0, 1); c2.elements[1].position = clouds + 0.12; c2.elements[1].color = (1, 1, 1, 1)
    l.new(nz.outputs['Fac'], cm.inputs['Fac'])
    hm = n.new('ShaderNodeMath'); hm.operation = 'MULTIPLY'
    hz = n.new('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = 0.02; hz.inputs['From Max'].default_value = 0.16
    l.new(sep.outputs['Z'], hz.inputs['Value']); l.new(cm.outputs['Color'], hm.inputs[0]); l.new(hz.outputs['Result'], hm.inputs[1])
    shade = n.new('ShaderNodeMix'); shade.data_type = 'RGBA'
    shade.inputs[6].default_value = srgb(cloud_shadow); shade.inputs[7].default_value = srgb(cloud)
    l.new(nz.outputs['Fac'], shade.inputs['Factor'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    l.new(hm.outputs[0], mx.inputs['Factor']); l.new(rp.outputs['Color'], mx.inputs[6]); l.new(shade.outputs[2], mx.inputs[7])
    l.new(mx.outputs[2], bg.inputs['Color']); l.new(bg.outputs[0], out.inputs['Surface'])
    for o in list(sc.objects):
        if o.type == 'LIGHT': bpy.data.objects.remove(o)
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.6; sun.angle = math.radians(3); sun.color = sun_col
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = sun_dir

# ------------------------------------------------------------------ yükseklik alanı + boyalı köşe rengi + mesafe sisi

def field(name, x0, x1, y0, y1, res, hfun, colfun, fog=None, rough=0.9, overlay=0.16):
    nx = res; ny = max(4, int(res * (y1 - y0) / (x1 - x0)))
    bm = bmesh.new(); col = bm.loops.layers.color.new('Col')
    vs = [[bm.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, 0)) for i in range(nx + 1)] for j in range(ny + 1)]
    for row in vs:
        for v in row: v.co.z = hfun(v.co.x, v.co.y)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bm.normal_update()
    cache = {}
    for f in bm.faces:
        for lp in f.loops:
            v = lp.vert
            if v not in cache:
                c = colfun(v.co.x, v.co.y, v.co.z, v.normal); cache[v] = (c.x, c.y, c.z, 1.0)
            lp[col] = cache[v]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    vc = n.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    tx = n.new('ShaderNodeTexNoise'); tx.inputs['Scale'].default_value = 14; tx.inputs['Detail'].default_value = 7   # el boyaması fırça dokusu
    ov = n.new('ShaderNodeMix'); ov.data_type = 'RGBA'; ov.blend_type = 'OVERLAY'; ov.inputs['Factor'].default_value = overlay
    l.new(vc.outputs['Color'], ov.inputs[6]); l.new(tx.outputs['Color'], ov.inputs[7]); l.new(ov.outputs[2], b.inputs['Base Color'])
    surf = b.outputs[0]
    if fog:
        # hava perspektifi: kameraya uzaklıkla sis rengine karışır (Unity: RenderSettings.fog / mesafe sisi)
        fcol, f0, f1, fmax = fog
        cd = n.new('ShaderNodeCameraData'); mr = n.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = f0; mr.inputs['From Max'].default_value = f1; mr.inputs['To Max'].default_value = fmax
        l.new(cd.outputs['View Z Depth'], mr.inputs['Value'])
        em = n.new('ShaderNodeEmission'); em.inputs['Color'].default_value = srgb(fcol); em.inputs['Strength'].default_value = 1.0
        ms = n.new('ShaderNodeMixShader'); l.new(mr.outputs['Result'], ms.inputs['Fac']); l.new(surf, ms.inputs[1]); l.new(em.outputs[0], ms.inputs[2])
        surf = ms.outputs[0]
    l.new(surf, n['Material Output'].inputs['Surface'])
    o.data.materials.append(m); smooth(o)
    return o

def ridge(x, y, s, seed, oct=6):
    return N.ridged_multi_fractal(V((x * s + seed, y * s, seed * 0.7)), 1.0, 2.0, oct, 1.0, 2.0)

def terrace(h, step, k=0.55):
    """Katmanlı kaya basamakları: yüksekliği basamaklara çeker (k: basamak sertliği)."""
    f = h / step; i = math.floor(f); t = f - i
    t = sstep(0.0, 1.0, t) if k < 1 else (0 if t < 0.5 else 1)
    return (i + (1 - k) * (f - i) + k * t) * step

def peak(x, y, cx, cy, height, radius, seed, step=None, rough=0.35, s=0.06):
    d = math.hypot(x - cx, y - cy) / radius
    base = math.exp(-d * d * 1.6)
    r = ridge(x, y, s, seed) * 0.5
    h = height * base * (0.7 + rough * r) + height * 0.08 * N.noise(V((x * 0.05, y * 0.05, seed)))
    if step: h = terrace(h, step)
    return h

def jitter(x, y, s, seed): return N.noise(V((x * s, y * s, seed)))

# ------------------------------------------------------------------ G5: geniş vadi + katmanlı dağlar

def g5(out):
    sc = kit.reset(); sc.cycles.samples = 56; sc.view_settings.exposure = -0.25
    sky(sc, '#2f7fd6', '#6fb3ec', '#cfe6f6', '#ffffff', '#b8c9e3', (math.radians(52), 0, math.radians(-30)), (1.0, 0.95, 0.86), 1.05, 0.54)
    GR1, GR2, GR3, DRY = C('#3f9a2b'), C('#69bf38'), C('#97d850'), C('#c79a4a')
    RK1, RK2, RK3 = C('#6f7276'), C('#9a9b98'), C('#c4c2bb')
    def mcol(x, y, z, nrm):
        k = 0.5 + 0.5 * jitter(x, y, 0.08, 3)
        rockc = lerp3(RK1, RK2, sstep(0.0, 18, z)).lerp(RK3, 0.35 * k)
        rockc = rockc.lerp(C('#8a7f74'), max(0.0, jitter(x, y, 0.03, 8)) * 0.35)              # kahvemsi damar
        grass = lerp3(GR1, GR2, k).lerp(GR3, sstep(0.9, 1.0, nrm.z) * 0.3)
        flat = sstep(0.78, 0.9, nrm.z + 0.06 * jitter(x, y, 0.25, 5))                         # düz basamak = çim örtüsü
        return rockc.lerp(grass, flat)
    def fog(d0, d1, m): return ('#a9c9e6', d0, d1, m)
    # uzak katman (en mavi), orta katman, yakın büyük zirve
    field('far', -260, 260, 230, 330, 150, lambda x, y: sum(peak(x, y, cx, 280, h, r, s, None, 0.5, 0.03) for cx, h, r, s in
          [(-200, 42, 60, 1), (-110, 58, 55, 2), (-20, 48, 60, 3), (70, 66, 52, 4), (170, 50, 60, 5)]) - 2, mcol, fog(120, 330, 0.72))
    field('mid', -170, 170, 120, 220, 170, lambda x, y: sum(peak(x, y, cx, cy, h, r, s, 4.0, 0.45, 0.05) for cx, cy, h, r, s in
          [(-120, 170, 34, 40, 11), (-55, 160, 26, 34, 12), (40, 175, 30, 38, 13), (120, 165, 38, 42, 14)]) - 1, mcol, fog(90, 260, 0.5))
    field('hero', -90, 110, 70, 170, 220, lambda x, y: peak(x, y, 25, 120, 44, 40, 21, 4.5, 0.22, 0.05) +
          peak(x, y, -45, 104, 20, 26, 22, 3.2, 0.3, 0.06) + peak(x, y, 80, 100, 18, 24, 23, 3.2, 0.3, 0.06), mcol, fog(70, 260, 0.34))
    # vadi: yemyeşil çayır, yer yer kurumuş tutam lekeleri, hafif dalga; uzakta küçük göl
    def vh(x, y): return 0.6 * jitter(x, y, 0.04, 31) + 0.25 * jitter(x, y, 0.12, 32) + max(0.0, (y - 30) * 0.02)
    def vcol(x, y, z, nrm):
        k = 0.5 + 0.5 * jitter(x, y, 0.09, 33)
        c = lerp3(GR1, GR2, k).lerp(GR3, max(0.0, jitter(x, y, 0.2, 34)) * 0.6)
        return c.lerp(DRY, sstep(0.25, 0.6, jitter(x, y, 0.07, 35)) * 0.55)
    field('valley', -160, 160, -12, 200, 260, vh, vcol, fog(50, 200, 0.25), overlay=0.22)
    lake = mat('lake', '#3e88b6', 0.08, 0.3); bpy.ops.mesh.primitive_circle_add(vertices=48, radius=1, fill_type='NGON', location=(-10, 62, 0.95))
    lk = bpy.context.object; lk.scale = (22, 5, 1); lk.data.materials.append(lake)
    # ön plan: canlı ot öbekleri ve birkaç çiçek
    R = random.Random(5)
    for k in range(70):
        x = R.uniform(-16, 16); y = R.uniform(-6, 9)
        lush((x, y, vh(x, y) - 0.02), 0.5, 3, 500 + k, h=(0.35, 0.7))
    kit.shoot(sc, os.path.join(out, 'g5_vadi_daglar.png'), (8, 90, 12), 96, 3, 5, lens=24, size=(1600, 900))

# ------------------------------------------------------------------ G6: karlı zirve, gün batımı

def g6(out):
    sc = kit.reset(); sc.cycles.samples = 56; sc.view_settings.exposure = -0.3
    sky(sc, '#3a3f86', '#8a6fb5', '#f2b9b0', '#fde3d6', '#7b6a9e', (math.radians(74), 0, math.radians(-62)), (1.0, 0.78, 0.66), 1.0, 0.5)
    RK1, RK2 = C('#5d6578'), C('#9298a8')
    SN1, SN2 = C('#f6f3fb'), C('#c3c4e4')
    def scol(x, y, z, nrm):
        k = 0.5 + 0.5 * jitter(x, y, 0.15, 41)
        rockc = lerp3(RK1, RK2, k).lerp(C('#6a5e70'), max(0.0, jitter(x, y, 0.05, 44)) * 0.4)
        # ince kar tabakası: yatay yüzeylerde, gürültüyle kırık; aşağı/gölgeye bakan kar mavi-mor
        s = sstep(0.55, 0.72, nrm.z + 0.2 * jitter(x, y, 0.35, 42) + 0.004 * z)
        snow = lerp3(SN2, SN1, sstep(0.75, 1.0, nrm.z))
        return rockc.lerp(snow, s)
    h_peak = lambda x, y: (peak(x, y, 0, 70, 40, 26, 51, 3.0, 0.4, 0.08) + peak(x, y, -24, 48, 20, 18, 52, 2.4, 0.6, 0.11)
                           + peak(x, y, 26, 50, 24, 20, 53, 2.6, 0.6, 0.11))
    field('peak', -60, 60, 20, 100, 260, h_peak, scol, ('#b39ac7', 50, 160, 0.3), rough=0.7)
    field('far', -200, 200, 130, 220, 120, lambda x, y: sum(peak(x, y, cx, 170, h, r, s, None, 0.5, 0.04) for cx, h, r, s in
          [(-140, 30, 40, 61), (-60, 22, 36, 62), (70, 26, 40, 63), (150, 34, 42, 64)]), scol, ('#c5a9cf', 80, 230, 0.6))
    # ön plan: karlı patika (sıkışmış iz) ve kayalar
    def gh(x, y): return 0.5 * jitter(x, y, 0.06, 71) + max(0.0, (y - 12) * 0.12)
    def gcol(x, y, z, nrm):
        path = math.exp(-((x - 2.5 * math.sin(y * 0.12)) / 1.6) ** 2) * sstep(-8, 4, y) * (1 - sstep(18, 24, y))
        c = lerp3(SN2, SN1, 0.6 + 0.4 * jitter(x, y, 0.3, 72))
        return c.lerp(C('#a49cb8'), path * 0.6).lerp(C('#6c6676'), path * sstep(0.2, 0.6, jitter(x, y, 0.8, 73)) * 0.5)
    field('ground', -40, 40, -10, 30, 160, gh, gcol, ('#b39ac7', 40, 140, 0.2))
    RM = mat('rk6', '#5d6475', 0.75, 0.05); SM = mat('sn6', '#eef0fa', 0.5, 0.2)
    R = random.Random(9)
    for k in range(9):
        x = R.choice([-1, 1]) * R.uniform(4, 13); y = R.uniform(-2, 14); r = R.uniform(0.5, 1.6)
        rock((x, y, gh(x, y) + r * 0.2), r, RM, 900 + k, (1.0, 0.9, 0.75), 3, 0.28)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r * 0.75, location=(x, y, gh(x, y) + r * 0.62))
        cap = bpy.context.object; cap.scale = (1.0, 0.95, 0.28); cap.data.materials.append(SM); smooth(cap)
    import v4.ski_mountain_v4 as SMV
    SMV.snowflakes((-14, 14, -2, 22), 0.5, 7, 260, 77)
    kit.shoot(sc, os.path.join(out, 'g6_karli_zirve.png'), (0, 58, 20), 92, 6, 7, lens=28, size=(1600, 900))

# ------------------------------------------------------------------ G7: eriyen kar zemini (yakın plan)

def g7(out):
    sc = kit.reset(); sc.cycles.samples = 56; sc.view_settings.exposure = -0.35
    sky(sc, '#6d7fc0', '#c3a9d6', '#f3d4dd', '#fbeff3', '#a596bf', (math.radians(64), 0, math.radians(-50)), (1.0, 0.86, 0.8), 0.95, 0.6)
    SN1, SN2 = C('#f6f4fb'), C('#c7c9e6')
    DIRT, DRYG, MOSS = C('#6e5a4a'), C('#9b8a5c'), C('#6f7f45')
    def snow_w(x, y):
        n = jitter(x, y, 0.32, 81) * 0.6 + jitter(x, y, 1.1, 82) * 0.28 + jitter(x, y, 3.0, 83) * 0.1
        return sstep(-0.1, 0.1, n + 0.02 - 0.02 * max(0.0, 6 - y))       # kar lekeleri; ön planda biraz daha toprak
    def gh(x, y): return 0.18 * jitter(x, y, 0.2, 84) + 0.05 * jitter(x, y, 1.4, 85) + 0.06 * snow_w(x, y) + max(0.0, (y - 16) * 0.05)
    def gcol(x, y, z, nrm):
        s = snow_w(x, y); k = 0.5 + 0.5 * jitter(x, y, 1.5, 86)
        under = DIRT.lerp(DRYG, k).lerp(MOSS, max(0.0, jitter(x, y, 0.6, 87)) * 0.7)
        rim = math.exp(-((s - 0.5) / 0.18) ** 2)                          # erime kenarı: ıslak, koyu
        under = under.lerp(C('#4c3f3a'), rim * 0.35)
        snow = lerp3(SN2, SN1, 0.55 + 0.45 * jitter(x, y, 2.2, 88))
        return under.lerp(snow, s)
    field('snowfloor', -24, 24, -6, 30, 300, gh, gcol, ('#cdb9d9', 18, 60, 0.35), overlay=0.25)
    # karsız yamalarda kuru ot tutamları ve küçük taşlar
    R = random.Random(12); RM = mat('rk7', '#6a6f7e', 0.75, 0.05)
    placed = 0
    while placed < 120:
        x = R.uniform(-10, 10); y = R.uniform(-2, 12)
        if snow_w(x, y) > 0.35: continue
        lush((x, y, gh(x, y) - 0.02), 0.25, 2, 1200 + placed, h=(0.12, 0.28), bright=False); placed += 1
    for k in range(26):
        x = R.uniform(-9, 9); y = R.uniform(-1, 14); r = R.uniform(0.06, 0.32)
        rock((x, y, gh(x, y) + r * 0.25), r, RM, 1500 + k, (1.0, 0.85, 0.6), 2, 0.25)
    # arkada karlı kayalık sırt
    RK1, RK2 = C('#545b6d'), C('#878c9c')
    def rcol(x, y, z, nrm):
        s = sstep(0.55, 0.75, nrm.z + 0.2 * jitter(x, y, 0.4, 91))
        return lerp3(RK1, RK2, 0.5 + 0.5 * jitter(x, y, 0.2, 92)).lerp(lerp3(SN2, SN1, nrm.z), s)
    field('ridge', -70, 70, 30, 70, 200, lambda x, y: sum(peak(x, y, cx, 48, h, r, s, 1.6, 0.6, 0.12) for cx, h, r, s in
          [(-40, 9, 14, 93), (-12, 13, 15, 94), (18, 10, 13, 95), (46, 12, 15, 96)]), rcol, ('#cdb9d9', 30, 90, 0.4), rough=0.7)
    import v4.ski_mountain_v4 as SMV
    SMV.snowflakes((-8, 8, 0, 16), 0.2, 4.5, 220, 97)
    kit.shoot(sc, os.path.join(out, 'g7_eriyen_kar.png'), (0, 10, 0.8), 12, 0, 10, lens=24, size=(1600, 900))

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = args[0] if args else '.'
    os.makedirs(out, exist_ok=True)
    which = args[1:] or ['g5', 'g6', 'g7']
    for w in which: {'g5': g5, 'g6': g6, 'g7': g7}[w](out)
    print('ok', which)
