# Geri bildirim 6 (19 Ekim 2026) görsel taslak: zemin. Kullanım:
#   python3.11 -I ground_mockup.py -- <now|new> çıktı.png
# now: bugünkü çim (0,5 m ızgarada 7 telli geniş öbek, 24–42 cm) + düz patika.
# new: kıl gibi ince, kısa (6–14 cm), sık çim; arada seyrek/kel lekeler; patikada çakıl, kum birikintisi, toprak topağı;
#      pet arkasında yaşlandıkça silinen ayak izleri. Referans (Family Island / Hay Day) yalnız kalite/hava hedefi; kopya yok.
import bpy, bmesh, math, random, sys, os, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code3d'))
import kit
from kit import srgb, mat
V = mathutils.Vector
mode, out = sys.argv[sys.argv.index('--') + 1:][:2]
rnd = random.Random(7)
sc = kit.reset()
sc.cycles.samples = 48
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

# ------------------------------------------------------------------ patika ekseni (hafif kıvrımlı, kameradan uzaklaşan)
def path_x(y): return 0.55 * math.sin(y * 0.35) - 0.2
HALF = 0.85          # patika yarı genişliği (m)
def path_d(x, y): return abs(x - path_x(y))

def noise2(x, y, s=1.0):
    return (math.sin(x * 1.7 * s + 1.3) * math.cos(y * 1.3 * s - 0.7) + math.sin((x + y) * 0.9 * s + 2.1)) * 0.5

# ------------------------------------------------------------------ zemin ağı
size, n = 24.0, 220
bpy.ops.mesh.primitive_grid_add(x_subdivisions=n, y_subdivisions=n, size=size, location=(0, 0, 0))
g = bpy.context.object; g.name = 'ground'
for v in g.data.vertices:
    x, y = v.co.x + 0, v.co.y + 0
    v.co.y += 2; y += 2
    v.co.z = 0.04 * noise2(x, y, 0.8) - (0.025 if path_d(x, y) < HALF else 0.0)   # patika hafif çökük

def ground_material():
    m = bpy.data.materials.new('groundmat'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.95
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    # patika maskesi: |x - path_x(y)| < HALF (+ kenar gürültüsü)
    sin = N.new('ShaderNodeMath'); sin.operation = 'SINE'
    yk = N.new('ShaderNodeMath'); yk.operation = 'MULTIPLY'; yk.inputs[1].default_value = 0.35
    ya = N.new('ShaderNodeMath'); ya.operation = 'ADD'; ya.inputs[1].default_value = 0.0
    L.new(sep.outputs['Y'], yk.inputs[0]); L.new(yk.outputs[0], ya.inputs[0]); L.new(ya.outputs[0], sin.inputs[0])
    px = N.new('ShaderNodeMath'); px.operation = 'MULTIPLY_ADD'; px.inputs[1].default_value = 0.55; px.inputs[2].default_value = -0.2
    L.new(sin.outputs[0], px.inputs[0])
    dx = N.new('ShaderNodeMath'); dx.operation = 'SUBTRACT'; L.new(sep.outputs['X'], dx.inputs[0]); L.new(px.outputs[0], dx.inputs[1])
    ad = N.new('ShaderNodeMath'); ad.operation = 'ABSOLUTE'; L.new(dx.outputs[0], ad.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    jit = N.new('ShaderNodeMath'); jit.operation = 'MULTIPLY_ADD'; jit.inputs[1].default_value = 0.35; jit.inputs[2].default_value = -0.17
    L.new(nz.outputs['Fac'], jit.inputs[0])
    ad2 = N.new('ShaderNodeMath'); ad2.operation = 'ADD'; L.new(ad.outputs[0], ad2.inputs[0]); L.new(jit.outputs[0], ad2.inputs[1])
    edge = N.new('ShaderNodeMapRange'); edge.inputs['From Min'].default_value = HALF - 0.12; edge.inputs['From Max'].default_value = HALF + 0.12
    L.new(ad2.outputs[0], edge.inputs['Value'])     # 0 = patika, 1 = çimen
    # patika rengi: toprak + açık kum birikintisi (gürültü)
    sand = N.new('ShaderNodeTexNoise'); sand.inputs['Scale'].default_value = 1.6; sand.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], sand.inputs['Vector'])
    pr = N.new('ShaderNodeValToRGB'); r = pr.color_ramp
    r.elements[0].position = 0.38; r.elements[0].color = srgb('#b98a5a' if mode == 'new' else '#d8b685')
    r.elements[1].position = 0.62; r.elements[1].color = srgb('#e2c493' if mode == 'new' else '#d8b685')
    L.new(sand.outputs['Fac'], pr.inputs['Fac'])
    fine = N.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 60; fine.inputs['Detail'].default_value = 2
    L.new(tc.outputs['Object'], fine.inputs['Vector'])
    grit = N.new('ShaderNodeMixRGB'); grit.blend_type = 'MULTIPLY'; grit.inputs['Fac'].default_value = 0.25 if mode == 'new' else 0.0
    L.new(pr.outputs['Color'], grit.inputs[1]); L.new(fine.outputs['Color'], grit.inputs[2])
    # çimen altı: toprak-yeşil karışık (kel lekelerde toprak görünür)
    under = N.new('ShaderNodeValToRGB'); u = under.color_ramp
    u.elements[0].position = 0.45; u.elements[0].color = srgb('#5c7a2e' if mode == 'new' else '#86c25c')
    u.elements[1].position = 0.62; u.elements[1].color = srgb('#8b6b43' if mode == 'new' else '#86c25c')
    bald = N.new('ShaderNodeTexNoise'); bald.inputs['Scale'].default_value = 1.6; bald.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], bald.inputs['Vector']); L.new(bald.outputs['Fac'], under.inputs['Fac'])
    mix = N.new('ShaderNodeMixRGB'); L.new(edge.outputs['Result'], mix.inputs['Fac'])
    L.new(grit.outputs[0], mix.inputs[1]); L.new(under.outputs['Color'], mix.inputs[2])
    L.new(mix.outputs[0], b.inputs['Base Color'])
    return m
g.data.materials.append(ground_material())

bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 74, -0.05))
bg_ = bpy.context.object; bg_.data.materials.append(mat('far', '#6fa544' if mode == 'new' else '#86c25c', 0.95, 0))
# ------------------------------------------------------------------ çim
def bald_w(x, y):
    """new: kel/seyrek lekeler (0–1 yoğunluk)."""
    v = noise2(x * 2.2 + 4, y * 2.0 - 2, 1.0) + 0.35 * noise2(x * 5.1, y * 4.7, 1.0)
    return max(0.0, min(1.0, (v + 0.7) * 2.6))

if mode == 'new':
    vg = g.vertex_groups.new(name='dens'); vl = g.vertex_groups.new(name='len')
    for v in g.data.vertices:
        x, y = v.co.x, v.co.y
        d = path_d(x, y)
        edge = max(0.0, min(1.0, (d - HALF + 0.05 + 0.12 * noise2(x * 3, y * 3)) / 0.35))
        vg.add([v.index], edge * bald_w(x, y), 'REPLACE')
        vl.add([v.index], 0.55 + 0.45 * (0.5 + 0.5 * noise2(x * 2.3, y * 2.1)), 'REPLACE')
    mod = g.modifiers.new('grass', 'PARTICLE_SYSTEM'); ps = g.particle_systems[0]; st = ps.settings
    st.type = 'HAIR'; st.count = 120000; st.hair_length = 0.13
    st.emit_from = 'FACE'; st.use_emit_random = True; st.distribution = 'RAND'
    st.child_type = 'INTERPOLATED'; st.child_percent = 3; st.rendered_child_count = 6; st.length_random = 0.5; st.child_radius = 0.12
    st.child_length = 0.75; st.child_length_threshold = 0.3
    st.clump_factor = 0.15; st.roughness_1 = 0.025; st.roughness_endpoint = 0.04; st.roughness_2 = 0.02
    st.root_radius = 0.35; st.tip_radius = 0.0; st.radius_scale = 0.012   # ~4 mm kökte, ucu sıfır: kıl gibi
    st.use_close_tip = True
    ps.vertex_group_density = 'dens'; ps.vertex_group_length = 'len'
    gm = bpy.data.materials.new('grass'); gm.use_nodes = True
    nt = gm.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.55
    hi = N.new('ShaderNodeHairInfo')
    rr = N.new('ShaderNodeValToRGB'); r = rr.color_ramp
    r.elements[0].position = 0.0; r.elements[0].color = srgb('#3f7a2c')
    r.elements[1].position = 1.0; r.elements[1].color = srgb('#a7d65a')
    mid = r.elements.new(0.55); mid.color = srgb('#6fae3e')
    var = N.new('ShaderNodeMath'); var.operation = 'MULTIPLY_ADD'; var.inputs[1].default_value = 0.25
    L.new(hi.outputs['Random'], var.inputs[0]); L.new(hi.outputs['Intercept'], var.inputs[2])
    L.new(var.outputs[0], rr.inputs['Fac']); L.new(rr.outputs['Color'], b.inputs['Base Color'])
    tr = N['Principled BSDF'].inputs.get('Subsurface Weight')
    g.data.materials.append(gm); st.material = len(g.data.materials)
else:
    # bugünkü öbek: 7 incelen geniş üçgen (0,24–0,42 m), 0,5 m hücrede bir öbek (GrassField.Clump)
    gm = mat('grass_now', '#79b84f', rough=0.7, coat=0)
    bm = bmesh.new()
    cr = random.Random(11)
    blades = []
    for _ in range(7):
        a = cr.random() * math.tau; rr_ = cr.random() * 0.22
        root = V((math.cos(a) * rr_, math.sin(a) * rr_, 0)); face = cr.random() * math.pi
        side = V((math.cos(face), math.sin(face), 0)) * 0.03; h = 0.24 + cr.random() * 0.18
        lean = V((cr.random() - 0.5, cr.random() - 0.5, 0)) * 0.08
        blades.append((root - side, root + side, root + lean + V((0, 0, h))))
    y = -8.0
    while y < 14:
        x = -12.0
        while x < 12:
            jx, jy = x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.2, 0.2)
            if path_d(jx, jy) > HALF + 0.05:
                rot = rnd.uniform(0, math.tau); c, s_ = math.cos(rot), math.sin(rot)
                for p0, p1, p2 in blades:
                    vs = [bm.verts.new((jx + p.x * c - p.y * s_, jy + p.x * s_ + p.y * c, p.z)) for p in (p0, p1, p2)]
                    bm.faces.new(vs)
            x += 0.5
        y += 0.5
    me = bpy.data.meshes.new('grassnow'); bm.to_mesh(me); o = bpy.data.objects.new('grassnow', me)
    sc.collection.objects.link(o); o.data.materials.append(gm)

# ------------------------------------------------------------------ patika detayları (yalnız new)
if mode == 'new':
    stone_m = [mat('st1', '#9a9184', 0.8, 0), mat('st2', '#b3a68e', 0.8, 0), mat('st3', '#7d7468', 0.85, 0), mat('st4', '#8c7f6c', 0.85, 0)]
    clod_m = mat('clod', '#7a5534', 0.95, 0)
    for i in range(150):
        y = rnd.uniform(-3.5, 9.5)
        side = rnd.choice([-1, 1]) if rnd.random() < 0.35 else rnd.uniform(-1, 1)
        x = path_x(y) + side * HALF * rnd.uniform(0.2, 1.15)
        s = rnd.uniform(0.012, 0.045) * (1.6 if rnd.random() < 0.07 else 1)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, 0.04 * noise2(x, y, 0.8) - 0.025 + s * 0.3))
        o = bpy.context.object; o.scale = (s * rnd.uniform(0.9, 1.5), s * rnd.uniform(0.8, 1.3), s * rnd.uniform(0.45, 0.8))
        o.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, math.tau))
        for v in o.data.vertices: v.co *= rnd.uniform(0.88, 1.08)
        o.data.materials.append(rnd.choice(stone_m)); bpy.ops.object.shade_smooth()
    for i in range(60):   # toprak topakları / kir
        y = rnd.uniform(-3.5, 9.5); x = path_x(y) + rnd.uniform(-1, 1) * HALF * 0.9
        s = rnd.uniform(0.02, 0.05)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=(x, y, -0.02 + s * 0.2))
        o = bpy.context.object; o.scale = (s * 1.3, s, s * 0.5); o.data.materials.append(clod_m)
    # ayak izleri: petin arkasında, eskisi soluk (oyunda: son ~8 iz, yaşlandıkça silinir)
    for k in range(9):
        y = -0.6 - k * 0.42
        for sidei, off in ((0, -0.13), (1, 0.13)):
            yy = y - sidei * 0.21; x = path_x(yy) + off
            age = k / 8.0
            fm = bpy.data.materials.new(f'fp{k}{sidei}'); fm.use_nodes = True
            bb = fm.node_tree.nodes['Principled BSDF']
            bb.inputs['Base Color'].default_value = srgb('#8a6440'); bb.inputs['Roughness'].default_value = 0.98
            bb.inputs['Alpha'].default_value = 0.85 * (1 - age) ** 1.3 + 0.03
            fm.blend_method = 'BLEND'
            for (dx, dy, rx, ry) in ((0, 0, 0.055, 0.045), (-0.045, 0.06, 0.018, 0.022), (-0.015, 0.075, 0.018, 0.022),
                                     (0.015, 0.075, 0.018, 0.022), (0.045, 0.06, 0.018, 0.022)):
                gz = 0.04 * noise2(x + dx, yy + dy, 0.8) - 0.025 + 0.003
                bpy.ops.mesh.primitive_circle_add(vertices=20, radius=1, fill_type='NGON', location=(x + dx, yy + dy, gz))
                o = bpy.context.object; o.scale = (rx, ry, 1); o.data.materials.append(fm)

# ------------------------------------------------------------------ pet (ölçek için): pet_01, oyundaki boy ~1,75 m'nin yavrusu ~0,9 m
pet_dir = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Pets', 'pet_01')
try:
    bpy.ops.import_scene.fbx(filepath=os.path.join(pet_dir, 'pet_01.fbx'))
    objs = [o for o in bpy.context.selected_objects]
    pm = bpy.data.materials.new('pet'); pm.use_nodes = True
    tex = pm.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(os.path.join(pet_dir, 'pet_01_basecolor.jpg'))
    pm.node_tree.links.new(tex.outputs['Color'], pm.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    pm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6
    meshes = [o for o in objs if o.type == 'MESH']
    for o in meshes:
        o.data.materials.clear(); o.data.materials.append(pm)
    bpy.context.view_layer.update()
    mn = V((1e9, 1e9, 1e9)); mx = V((-1e9, -1e9, -1e9))
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ V(c); mn = V(map(min, mn, w)); mx = V(map(max, mx, w))
    h = mx.z - mn.z; s = 1.05 / max(h, 1e-3)
    root = [o for o in objs if o.parent is None]
    for o in root:
        o.scale = o.scale * s; o.rotation_euler.z += math.radians(180)
        o.location = (path_x(0) - (mn.x + mx.x) / 2 * s, -(mn.y + mx.y) / 2 * s, -mn.z * s - 0.02)
except Exception as e:
    print('pet yüklenemedi:', e)

# ------------------------------------------------------------------ kamera: oyundaki gibi arkadan-yukarıdan
cd = bpy.data.cameras.new('cam'); cd.lens = 32
co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
co.location = (path_x(-5.2), -5.2, 3.3)
tgt = V((path_x(1.2), 1.2, 0.35)); d = tgt - co.location
co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('ok', out)
