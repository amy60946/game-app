# Görsel taslak v4 (20 Ekim 2026): deniz + kumsal. Oyundaki kıyı kesiti, ÖNCE (bugünkü profil) / SONRA (önerilen).
#   /tmp/claude-0/bpyenv/bin/python shore_v4.py -- <çıktı_klasörü> [before|after|both]
# Önce: IslandTerrain.BaseHeight bugünkü formülü — kumsal +0,2 m'de düz durur, su çizgisinde ~%60 eğimle (~31°) düşer:
#       oyunda "küçük uçurum" gibi okunur; su opak, sığdaki kum görünmez.
# Sonra: kumsal 0,9 → 1,04 kıyı ölçüsü boyunca yumuşak rampa (en çok %21 ≈ 12°), sığ raf; su sığda kumu gösterir (derinlikle
#       renk), kıyıda köpük şeridi; deniz kabukları, yan yana palmiyeler, ağaç altında hindistan cevizleri. Tüm şekiller özgün, kodla.
import bpy, bmesh, math, random, sys, os, mathutils
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import kit
from kit import srgb, mat, blob
import assets_v3
V = mathutils.Vector

args = sys.argv[sys.argv.index('--') + 1:]
OUT = args[0]; WHICH = args[1] if len(args) > 1 else 'both'
os.makedirs(OUT, exist_ok=True)

R = 36.5   # ada yarıçapı (rx 39 / rz 34 ortalaması): kıyı ölçüsü c'deki 0,01 ≈ 0,37 m

def ss(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t

def h_old(c): return lerp(-1.6, 0.2, ss(1.07, 0.95, c)) + ss(0.93, 0.78, c) * 0.7
def h_new(c): return lerp(0.30, -0.32, ss(0.88, 1.04, c)) + lerp(0.0, -1.28, ss(1.02, 1.14, c)) + ss(0.93, 0.78, c) * 0.7

def coast(x, y):
    # y > 0 kara, y < 0 deniz; kıyı çizgisi hafif dalgalı (oyundaki gürültüye benzer)
    return 0.975 - y / R + 0.012 * math.sin(x * 0.22 + 1.0) + 0.006 * math.sin(x * 0.61)

def build(variant):
    sc = kit.reset(); sc.cycles.samples = 48
    sc.view_settings.exposure = -0.45
    sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = srgb('#a9d8f2')
    H = h_new if variant == 'after' else h_old
    rnd = random.Random(7)
    # ---------------------------------------------------------------- zemin (köşe renkli)
    W, D, step = 34.0, 26.0, 0.14
    nx, ny = int(W / step), int(D / step)
    bm = bmesh.new()
    col = bm.loops.layers.color.new('col')
    grid = []
    sand, wet, under = V(srgb('#f2e0ab')[:3]), V(srgb('#d9bf86')[:3]), V(srgb('#c9b07a')[:3])
    g1, g2 = V(srgb('#4f8a2c')[:3]), V(srgb('#7aa83e')[:3])
    def ground_col(x, y, h, c):
        n = 0.5 + 0.5 * math.sin(x * 0.7 + math.cos(y * 0.9) * 1.7) * math.cos(y * 0.5 - x * 0.2)
        grass = g1.lerp(g2, n)
        sand_w = max(ss(0.6, 0.3, h), ss(0.88, 0.93, c))
        k = grass.lerp(sand, sand_w)
        if variant == 'after':
            k = k.lerp(wet, ss(0.12, -0.02, h))           # ıslak kum şeridi (dalga ıslatır)
            k = k.lerp(under, ss(-0.02, -0.25, h))        # su altı kum (biraz koyu)
            # ince kum benekleri
            k *= 0.96 + 0.06 * (0.5 + 0.5 * math.sin(x * 9.1) * math.sin(y * 8.3))
        else:
            k = k.lerp(V(srgb('#bba371')[:3]), ss(0.0, -0.3, h))
        return k
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -W / 2 + i * step; y = -D / 2 + 4 + j * step
            c = coast(x, y); h = H(c)
            h += 0.03 * math.sin(x * 1.3 + y * 0.4) * ss(0.95, 0.88, c)   # kumsalda hafif dalgalanma
            row.append(bm.verts.new((x, y, h)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l in f.loops:
                p = l.vert.co; k = ground_col(p.x, p.y, p.z, coast(p.x, p.y)); l[col] = (k.x, k.y, k.z, 1.0)
    me = bpy.data.meshes.new('ground'); bm.to_mesh(me); bm.free()
    g = bpy.data.objects.new('ground', me); sc.collection.objects.link(g)
    for p in me.polygons: p.use_smooth = True
    gm = bpy.data.materials.new('ground'); gm.use_nodes = True; nt = gm.node_tree
    a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'col'
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.92
    nt.links.new(a.outputs['Color'], b.inputs['Base Color'])
    me.materials.append(gm)

    # ---------------------------------------------------------------- su
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -30, -0.02))
    w = bpy.context.object; w.scale = (140, 74, 1); bpy.ops.object.transform_apply(scale=True)
    s = w.modifiers.new('sub', 'SUBSURF'); s.subdivision_type = 'SIMPLE'; s.levels = s.render_levels = 8
    tx = bpy.data.textures.new('wave', 'CLOUDS'); tx.noise_scale = 1.6
    dsp = w.modifiers.new('wave', 'DISPLACE'); dsp.texture = tx; dsp.strength = 0.08; dsp.mid_level = 0.5
    wm = bpy.data.materials.new('water'); wm.use_nodes = True; wt = wm.node_tree; wb = wt.nodes['Principled BSDF']
    if variant == 'after':
        # sığda kum görünür: cam gibi geçirgen yüzey + derinlikle koyulaşan hacim (oyunda: arazi yüksekliğinden renk, aşağıya bak)
        wb.inputs['Base Color'].default_value = srgb('#bfeef0')
        wb.inputs['Transmission Weight'].default_value = 1.0
        wb.inputs['Roughness'].default_value = 0.06; wb.inputs['IOR'].default_value = 1.33
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -30, -1.0))
        vol = bpy.context.object; vol.scale = (140, 74, 1.96); bpy.ops.object.transform_apply(scale=True)
        vm = bpy.data.materials.new('vol'); vm.use_nodes = True; vt = vm.node_tree
        vt.nodes.remove(vt.nodes['Principled BSDF'])
        va = vt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = srgb('#1f9fb8'); va.inputs['Density'].default_value = 0.32
        vs = vt.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Color'].default_value = srgb('#7fe0e6'); vs.inputs['Density'].default_value = 0.035
        ad = vt.nodes.new('ShaderNodeAddShader')
        vt.links.new(va.outputs[0], ad.inputs[0]); vt.links.new(vs.outputs[0], ad.inputs[1])
        vt.links.new(ad.outputs[0], vt.nodes['Material Output'].inputs['Volume'])
        vol.data.materials.append(vm); vol.visible_camera = True
    else:
        wb.inputs['Base Color'].default_value = srgb('#2aa6c4'); wb.inputs['Roughness'].default_value = 0.12
    w.data.materials.append(wm)
    # deniz tabanı (ızgaranın ötesi): koyu kum, derin suda lacivertleşir
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -40, -1.62))
    sb = bpy.context.object; sb.scale = (160, 64, 1); bpy.ops.object.transform_apply(scale=True)
    sb.data.materials.append(mat('seabed', '#b49a6c', 0.9, 0))

    # ---------------------------------------------------------------- kıyı köpüğü: su çizgisini izleyen yırtık beyaz şerit
    def waterline(x):
        lo, hi = -6.0, 8.0
        for _ in range(40):
            m = (lo + hi) / 2
            if H(coast(x, m)) > -0.02: hi = m
            else: lo = m
        return (lo + hi) / 2
    if variant == 'after':
        for band, (off_in, off_out, alpha_k, sd) in enumerate(((0.05, 0.55, 1.0, 3), (0.9, 1.35, 0.55, 9))):
            bm = bmesh.new(); uv = bm.loops.layers.uv.new('uv'); rows = []
            xs = [-W / 2 + k * 0.25 for k in range(int(W / 0.25) + 1)]
            for x in xs:
                y0 = waterline(x) - 0.25 * math.sin(x * 0.3 + band)      # ikinci şerit biraz dalgalı, açıkta
                rows.append((bm.verts.new((x, y0 + off_in * (1 if band == 0 else -1) * (0.2 if band == 0 else 1), 0.0)),
                             bm.verts.new((x, y0 - off_out, 0.0))))
            for k in range(len(rows) - 1):
                f = bm.faces.new((rows[k][0], rows[k + 1][0], rows[k + 1][1], rows[k][1]))
                for l, (u, v) in zip(f.loops, ((k, 0), (k + 1, 0), (k + 1, 1), (k, 1))):
                    l[uv].uv = (u * 0.1, v)
            fm = bpy.data.meshes.new('foam%d' % band); bm.to_mesh(fm); bm.free()
            fo = bpy.data.objects.new('foam%d' % band, fm); sc.collection.objects.link(fo)
            fo.location.z = 0.035
            m = bpy.data.materials.new('foam%d' % band); m.use_nodes = True; t = m.node_tree; N = t.nodes; Lk = t.links
            pb = N['Principled BSDF']; pb.inputs['Base Color'].default_value = srgb('#fbfdff'); pb.inputs['Roughness'].default_value = 0.6
            tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 7.0; nz.inputs['Detail'].default_value = 6
            Lk.new(tc.outputs['Object'], nz.inputs['Vector'])
            grad = N.new('ShaderNodeSeparateXYZ'); Lk.new(tc.outputs['UV'], grad.inputs[0])
            fall = N.new('ShaderNodeMapRange'); fall.inputs['From Min'].default_value = 0.0; fall.inputs['From Max'].default_value = 1.0
            fall.inputs['To Min'].default_value = 0.95; fall.inputs['To Max'].default_value = -0.3
            Lk.new(grad.outputs['Y'], fall.inputs['Value'])
            ramp = N.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.42; ramp.inputs['From Max'].default_value = 0.6
            Lk.new(nz.outputs['Fac'], ramp.inputs['Value'])
            mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; Lk.new(ramp.outputs['Result'], mul.inputs[0]); Lk.new(fall.outputs['Result'], mul.inputs[1])
            mul2 = N.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; mul2.use_clamp = True; mul2.inputs[1].default_value = alpha_k
            Lk.new(mul.outputs[0], mul2.inputs[0])
            Lk.new(mul2.outputs[0], pb.inputs['Alpha'])
            fm.materials.append(m)
    else:
        # bugünkü oyun: dar, düz köpük çizgisi
        bpy.ops.mesh.primitive_plane_add(size=1); fo = bpy.context.object
        fo.scale = (W, 0.18, 1); bpy.ops.object.transform_apply(scale=True)
        fo.location = (0, waterline(0) - 0.1, 0.03)
        fo.data.materials.append(mat('foamold', '#eef8fb', 0.6, 0))

    # ---------------------------------------------------------------- palmiyeler (oyundaki c_palm), hindistan cevizleri, kabuklar
    before_objs = set(bpy.context.scene.objects)
    assets_v3.c_palm()
    kit.to_mesh_all()
    palm_parts = [o for o in bpy.context.scene.objects if o not in before_objs and o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in palm_parts: o.select_set(True)
    bpy.context.view_layer.objects.active = palm_parts[0]
    bpy.ops.object.join(); palm = bpy.context.object; palm.name = 'palm0'
    beach_y = lambda x: waterline(x) + (5.2 if variant == 'after' else 3.6)
    if variant == 'after':
        spots = [(-14.5, 0.3), (-11.8, -0.6), (-9.6, 0.5), (-7.0, -0.2), (-4.6, 0.8), (-1.6, -0.5), (1.2, 0.4), (3.6, -0.4),
                 (6.3, 0.6), (8.8, -0.3), (11.4, 0.5), (14.0, -0.2)]
    else:
        spots = [(-9.0, 0.0), (2.0, 0.6), (11.0, 0.0)]
    coco = mat('coco', '#6d4a2b', 0.75, 0.05); husk = mat('husk', '#8a6a3a', 0.8, 0.0)
    for k, (x, dy) in enumerate(spots):
        y = beach_y(x) + dy
        o = palm if k == 0 else palm.copy()
        if k: sc.collection.objects.link(o)
        o.location = (x, y, H(coast(x, y)) - 0.05)
        o.rotation_euler = (0, 0, math.radians(200 + rnd.uniform(-40, 40)))
        sc_k = rnd.uniform(0.8, 1.1); o.scale = (sc_k,) * 3
        if variant == 'after':
            for c in range(rnd.randint(2, 3)):     # ağaç altında 2–3 hindistan cevizi
                a = rnd.uniform(0, 6.28); r = rnd.uniform(0.35, 0.9)
                cx, cy = x + math.cos(a) * r, y + math.sin(a) * r
                cz = H(coast(cx, cy))
                blob('coco', (cx, cy, cz + 0.08), (0.12, 0.1, 0.1), coco if c else husk, rot=(rnd.uniform(0, 60), 0, rnd.uniform(0, 180)), sub=1, seg=16)
    if variant == 'after':
        shell_cols = ['#f6d6c8', '#f3e6cf', '#e9b8a6', '#fff4e2', '#d9a88a']
        for k in range(46):
            x = rnd.uniform(-W / 2 + 1, W / 2 - 1); y = waterline(x) + rnd.uniform(0.2, 3.6)
            z = H(coast(x, y)); m = mat('shell%d' % (k % 5), shell_cols[k % 5], 0.4, 0.3)
            if k % 3 == 0:
                # salyangoz kabuğu: kıvrık koni
                bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=0.07, depth=0.16, location=(x, y, z + 0.04))
                o = bpy.context.object; o.rotation_euler = (math.radians(80), 0, rnd.uniform(0, 6.28))
                tw = o.modifiers.new('tw', 'SIMPLE_DEFORM'); tw.deform_method = 'TWIST'; tw.angle = math.radians(220)
                o.data.materials.append(m)
                for p in o.data.polygons: p.use_smooth = True
            else:
                # tarak kabuğu: yelpaze, ince kaburgalar
                bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=8, radius=0.08, location=(x, y, z + 0.015))
                o = bpy.context.object; o.scale = (1.0, 0.85, 0.28); o.rotation_euler = (0, 0, rnd.uniform(0, 6.28))
                for v in o.data.vertices:
                    ang = math.atan2(v.co.y, v.co.x); v.co.z *= 1.0 + 0.35 * abs(math.sin(ang * 6))
                o.data.materials.append(m)
                for p in o.data.polygons: p.use_smooth = True
        # küçük çakıl ve deniz yosunu çizgisi (su bırakmış)
        for k in range(40):
            x = rnd.uniform(-W / 2, W / 2); y = waterline(x) + rnd.uniform(0.35, 0.9)
            blob('pb', (x, y, H(coast(x, y)) + 0.01), (0.04, 0.03, 0.015), mat('pebble', '#b9ad98', 0.7, 0.1), sub=0, seg=8)
    # kamera: oyundaki gibi yukarıdan; pet kıyıda yürürken: sudan kumsala ve palmiyelere çapraz bakış
    kit.shoot(sc, os.path.join(OUT, 'shore_%s.png' % variant), (0, waterline(0) + 2.2, 0.3), 15.5, 24, 30, lens=30, size=(1280, 800))

for v in (['before', 'after'] if WHICH == 'both' else [WHICH]):
    build(v)
    print('ok', v, flush=True)
