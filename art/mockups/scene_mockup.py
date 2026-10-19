# Geri bildirim 7 (19 Ekim 2026) görsel taslak v2: canlı ada sahnesi (kuşbakışına yakın oyun kamerası).
#   python3.11 -I scene_mockup.py -- çıktı.png
# Hedef hava: sarı-yeşil, alacalı çim; yonca ve çiçek öbekleri; taş döşeme lekeleri; yosunlu taş duvar; iri yapraklı bitki;
# çalı; kumsal ve sığ su; kenarlarda yumuşak sis (Güneş Taşı ile kalkacak yerler). Tüm şekiller burada kodla, özgün.
import bpy, math, random, sys, os, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code3d'))
import kit
from kit import srgb, mat, blob, rbox, cyl
V = mathutils.Vector
out = sys.argv[sys.argv.index('--') + 1]
rnd = random.Random(19)
sc = kit.reset(); sc.cycles.samples = 40
sc.view_settings.exposure = -0.55
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

def nz(x, y, s=1.0):
    return (math.sin(x * 1.7 * s + 1.3) * math.cos(y * 1.3 * s - 0.7) + math.sin((x + y) * 0.9 * s + 2.1)) * 0.5

# ------------------------------------------------------------------ zemin: alacalı sarı-yeşil çim + kumsal + su
W, D = 22.0, 14.0
bpy.ops.mesh.primitive_grid_add(x_subdivisions=180, y_subdivisions=120, size=1, location=(0, 0, 0))
g = bpy.context.object; g.scale = (W, D, 1); bpy.ops.object.transform_apply(scale=True)
def shore(x, y): return y < -4.2 + 0.9 * math.sin(x * 0.35) and x > 1.5     # sağ alt kumsal
def beach_h(x, y): return -4.2 + 0.9 * math.sin(x * 0.35) - y
for v in g.data.vertices:
    x, y = v.co.x, v.co.y
    h = 0.05 * nz(x, y, 0.7)
    if x > 1.5:
        b = beach_h(x, y)
        if b > 0: h -= min(0.5, b * 0.35)          # kumsaldan suya iner
    v.co.z = h
gm = bpy.data.materials.new('ground'); gm.use_nodes = True; nt = gm.node_tree; N = nt.nodes; L = nt.links
bsdf = N['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.9
tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 0.35; n1.inputs['Detail'].default_value = 5; L.new(tc.outputs['Object'], n1.inputs['Vector'])
grass = N.new('ShaderNodeValToRGB'); r = grass.color_ramp
r.elements[0].position = 0.35; r.elements[0].color = srgb('#5e9a1c')
r.elements[1].position = 0.68; r.elements[1].color = srgb('#93c22a')
L.new(n1.outputs['Fac'], grass.inputs['Fac'])
n2 = N.new('ShaderNodeTexVoronoi'); n2.inputs['Scale'].default_value = 1.4; L.new(tc.outputs['Object'], n2.inputs['Vector'])
mott = N.new('ShaderNodeMixRGB'); mott.blend_type = 'MULTIPLY'; mott.inputs['Fac'].default_value = 0.18
L.new(grass.outputs['Color'], mott.inputs[1]); L.new(n2.outputs['Distance'], mott.inputs[2])
# kum / su: z yüksekliğine göre
zr = N.new('ShaderNodeMapRange'); zr.inputs['From Min'].default_value = -0.02; zr.inputs['From Max'].default_value = -0.12
L.new(sep.outputs['Z'], zr.inputs['Value'])
sand = N.new('ShaderNodeRGB'); sand.outputs[0].default_value = srgb('#f1dfa8')
mix = N.new('ShaderNodeMixRGB'); L.new(zr.outputs['Result'], mix.inputs['Fac']); L.new(mott.outputs[0], mix.inputs[1]); L.new(sand.outputs[0], mix.inputs[2])
L.new(mix.outputs[0], bsdf.inputs['Base Color'])
g.data.materials.append(gm)
# kısa ince çim telleri (yalnız çimen)
vg = g.vertex_groups.new(name='d')
for v in g.data.vertices:
    vg.add([v.index], 0.0 if v.co.z < -0.03 else 1.0, 'REPLACE')
g.modifiers.new('hair', 'PARTICLE_SYSTEM'); ps = g.particle_systems[0]; st = ps.settings
st.type = 'HAIR'; st.count = 160000; st.hair_length = 0.12; st.length_random = 0.5
st.child_type = 'NONE'; st.root_radius = 0.5; st.tip_radius = 0.0; st.radius_scale = 0.014; st.roughness_1 = 0.03
ps.vertex_group_density = 'd'
hm = mat('hair', '#7fb52a', 0.6, 0); g.data.materials.append(hm); st.material = len(g.data.materials)
# su
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.16))
wm = bpy.data.materials.new('water'); wm.use_nodes = True; wb = wm.node_tree.nodes['Principled BSDF']
wb.inputs['Base Color'].default_value = srgb('#29c2c9'); wb.inputs['Roughness'].default_value = 0.08
wb.inputs['Transmission Weight'].default_value = 0.35; bpy.context.object.data.materials.append(wm)

def gz(x, y):
    h = 0.05 * nz(x, y, 0.7)
    if x > 1.5 and beach_h(x, y) > 0: h -= min(0.5, beach_h(x, y) * 0.35)
    return h

# ------------------------------------------------------------------ taş döşeme lekeleri (zemine gömülü, açık gri)
tile = mat('tile', '#a9ada3', 0.85, 0); tile2 = mat('tile2', '#959a90', 0.85, 0)
def tiles(cx, cy, n, spread):
    for _ in range(n):
        x, y = cx + rnd.uniform(-spread, spread), cy + rnd.uniform(-spread * 0.6, spread * 0.6)
        k = rnd.randint(7, 10)
        bpy.ops.mesh.primitive_cylinder_add(vertices=k, radius=rnd.uniform(0.18, 0.32), depth=0.06, location=(x, y, gz(x, y) + 0.005))
        o = bpy.context.object; o.rotation_euler.z = rnd.uniform(0, math.tau)
        for v in o.data.vertices: v.co.x *= rnd.uniform(0.85, 1.15); v.co.y *= rnd.uniform(0.85, 1.15)
        bv = o.modifiers.new('b', 'BEVEL'); bv.width = 0.02; bv.segments = 2
        o.data.materials.append(rnd.choice([tile, tile2]))
for (cx, cy) in ((-5.5, 3.2), (-1.5, 4.6), (2.8, 2.5), (-3.8, -2.2), (5.2, -0.6), (-7.5, -0.5)):
    tiles(cx, cy, rnd.randint(5, 9), 1.1)

# ------------------------------------------------------------------ yosunlu taş duvar
stone = [mat('st1', '#d8ccb2', 0.8, 0), mat('st2', '#c4b79c', 0.8, 0), mat('st3', '#e3d9c2', 0.8, 0)]
moss = mat('moss', '#6fb52e', 0.8, 0)
def wall(p0, p1, rows=2):
    p0, p1 = V(p0), V(p1); d = p1 - p0; n = int(d.length / 0.5)
    for i in range(n):
        for rr in range(rows):
            t = (i + (0.5 if rr % 2 else 0)) / n
            if t > 1: continue
            p = p0 + d * t
            s = (rnd.uniform(0.38, 0.5), rnd.uniform(0.32, 0.42), rnd.uniform(0.22, 0.3))
            o = rbox('w', (p.x, p.y, gz(p.x, p.y) + 0.12 + rr * 0.26), s, rnd.choice(stone),
                     rot=(rnd.uniform(-4, 4), rnd.uniform(-4, 4), math.degrees(math.atan2(d.y, d.x)) + rnd.uniform(-8, 8)), bevel=0.06, seg=3)
            if rr == rows - 1 and rnd.random() < 0.45:
                blob('m', (p.x, p.y, gz(p.x, p.y) + 0.12 + rr * 0.26 + 0.14), (0.2, 0.16, 0.05), moss, sub=1, seg=12)
wall((-10, 1.5), (-4.5, 6.5)); wall((3.5, 6.8), (9.5, 4.0)); wall((-9.5, -3.5), (-6.0, -6.5), rows=1)

# ------------------------------------------------------------------ kayalar
rock = [mat('r1', '#9aa0a3', 0.75, 0), mat('r2', '#7f8689', 0.75, 0), mat('rr', '#c46a4a', 0.75, 0)]
def rocks(cx, cy, n, red=False):
    for _ in range(n):
        x, y = cx + rnd.uniform(-0.6, 0.6), cy + rnd.uniform(-0.4, 0.4); s = rnd.uniform(0.18, 0.45)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, gz(x, y) + s * 0.3))
        o = bpy.context.object; o.scale = (s * rnd.uniform(1, 1.4), s, s * rnd.uniform(0.7, 1.1))
        for v in o.data.vertices: v.co *= rnd.uniform(0.85, 1.1)
        sd = o.modifiers.new('s', 'SUBSURF'); sd.levels = sd.render_levels = 2
        for pl in o.data.polygons: pl.use_smooth = True
        o.data.materials.append(rock[2] if red and rnd.random() < 0.6 else rnd.choice(rock[:2]))
rocks(-2.8, 1.0, 6); rocks(4.5, 3.6, 5, red=True); rocks(-6.5, 5.8, 4, red=True); rocks(1.0, -5.6, 7)

# ------------------------------------------------------------------ bitkiler: çalı, iri yapraklı bitki, çiçek, yonca
leaf_dark = mat('ld', '#2f8a3a', 0.6, 0.1); leaf_mid = mat('lm', '#4fae3d', 0.6, 0.1); leaf_lt = mat('ll', '#86cc3e', 0.6, 0.1)
def bush(x, y, r=0.7, berries=None):
    for _ in range(14):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, r * 0.6)
        px, py = x + math.cos(a) * d, y + math.sin(a) * d; s = rnd.uniform(0.28, 0.42) * r
        blob('b', (px, py, gz(x, y) + r * 0.45 + rnd.uniform(-0.1, 0.25) * r), (s, s, s * 0.9), rnd.choice([leaf_dark, leaf_mid]), sub=1, seg=14)
    if berries:
        bm = mat('berry' + berries, berries, 0.3, 0.3)
        for _ in range(10):
            a = rnd.uniform(0, math.tau)
            blob('be', (x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55, gz(x, y) + r * rnd.uniform(0.4, 0.9)), (0.06, 0.06, 0.06), bm, sub=0, seg=10)
def fern(x, y, s=1.0, m=None):
    m = m or leaf_mid
    for i in range(8):
        a = i / 8 * math.tau + rnd.uniform(-0.2, 0.2); tilt = rnd.uniform(35, 60)
        o = blob('lf', (x + math.cos(a) * 0.35 * s, y + math.sin(a) * 0.35 * s, gz(x, y) + 0.22 * s), (0.42 * s, 0.13 * s, 0.025 * s), m, sub=1, seg=14)
        o.rotation_euler = (0, -math.radians(tilt), a)
def flower_patch(x, y, col, n=7):
    pm = mat('p' + col, col, 0.45, 0.1); cm = mat('fc', '#ffd23a', 0.4, 0)
    for _ in range(n):
        px, py = x + rnd.uniform(-0.45, 0.45), y + rnd.uniform(-0.3, 0.3); z = gz(px, py) + rnd.uniform(0.12, 0.26)
        for k in range(5):
            a = k / 5 * math.tau
            o = blob('pt', (px + math.cos(a) * 0.055, py + math.sin(a) * 0.055, z), (0.055, 0.035, 0.015), pm, sub=0, seg=10)
            o.rotation_euler.z = a
        blob('c', (px, py, z + 0.01), (0.03, 0.03, 0.02), cm, sub=0, seg=8)
        blob('lf', (px + 0.05, py, z - 0.1), (0.09, 0.04, 0.01), leaf_mid, sub=0, seg=8)
def clover(x, y, n=12):
    cm = mat('clv', '#58b33a', 0.6, 0)
    for _ in range(n):
        px, py = x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.4, 0.4); z = gz(px, py) + 0.04
        for k in range(3):
            a = k / 3 * math.tau + rnd.uniform(0, 1)
            blob('cl', (px + math.cos(a) * 0.05, py + math.sin(a) * 0.05, z), (0.05, 0.05, 0.012), cm, sub=0, seg=10)
def tree(x, y):
    bark = mat('bark', '#8a5a34', 0.7, 0)
    kit.tube('trunk', [(x, y, gz(x, y)), (x + 0.1, y, gz(x, y) + 0.9), (x - 0.05, y + 0.05, gz(x, y) + 1.7)], [0.12, 0.09, 0.07], bark)
    for _ in range(18):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 0.8)
        blob('c', (x + math.cos(a) * d, y + math.sin(a) * d, gz(x, y) + 1.9 + rnd.uniform(-0.3, 0.45)), (0.42, 0.42, 0.34),
             rnd.choice([leaf_mid, leaf_lt, leaf_dark]), sub=1, seg=14)

for (x, y, b) in ((-8.2, 3.0, None), (-1.0, 6.2, '#5b3fb5'), (6.8, 2.2, None), (-4.5, -4.8, None), (8.5, -1.8, '#e63b3b')): bush(x, y, rnd.uniform(0.6, 0.9), b)
for (x, y) in ((-6.0, 1.0), (0.5, 3.8), (4.0, 5.6), (-2.2, -3.6), (7.4, 0.2), (-9.0, -1.8)): fern(x, y, rnd.uniform(0.9, 1.3), rnd.choice([leaf_mid, leaf_lt]))
for (x, y, c) in ((-3.2, 3.5, '#ff6a3d'), (1.8, 1.2, '#ffcf3a'), (-7.0, -2.8, '#ff7fb0'), (3.2, -2.4, '#ffcf3a'), (6.2, 4.4, '#ff4a4a'),
                  (-0.5, -2.2, '#ffffff'), (-5.2, 6.0, '#ff9f3a'), (5.8, -3.0, '#ff7fb0'), (-2.0, 0.2, '#6fb8ff')): flower_patch(x, y, c)
for (x, y) in ((-4.2, 0.2), (2.2, 4.0), (-1.2, -1.0), (4.6, 1.2), (-7.8, 4.6), (0.4, -3.8)): clover(x, y)
tree(-3.6, 5.0); tree(8.0, 5.6); tree(-8.6, -4.6); tree(6.4, -4.4)
def free(x, y): return abs(x - 0.0) > 1.6 or y > 6.5
for _ in range(34):
    x, y = rnd.uniform(-10.5, 10.5), rnd.uniform(-6.5, 6.8)
    if not free(x, y) or (x > 1.5 and beach_h(x, y) > -0.3): continue
    k = rnd.random()
    if k < 0.3: bush(x, y, rnd.uniform(0.5, 0.95), rnd.choice([None, None, '#e63b3b', '#5b3fb5', '#ff9f3a']))
    elif k < 0.6: fern(x, y, rnd.uniform(0.8, 1.4), rnd.choice([leaf_mid, leaf_lt, leaf_dark]))
    else: flower_patch(x, y, rnd.choice(['#ff6a3d', '#ffcf3a', '#ff7fb0', '#ff4a4a', '#ffffff', '#ff9f3a', '#b98cff']), rnd.randint(5, 10))
for _ in range(16):
    x, y = rnd.uniform(-10.5, 10.5), rnd.uniform(-6.5, 6.8)
    if free(x, y) and not (x > 1.5 and beach_h(x, y) > -0.3): clover(x, y, 14)

# ------------------------------------------------------------------ yürüyüş patikası: açık toprak, kenarı düzensiz (orta)
dirt = mat('dirt', '#e2c48a', 0.95, 0)
for i in range(40):
    t = i / 40; x = -0.6 + 1.2 * math.sin(t * 3); y = -5 + t * 9
    bpy.ops.mesh.primitive_circle_add(vertices=14, radius=rnd.uniform(0.38, 0.52), fill_type='NGON', location=(x, y, gz(x, y) + 0.004))
    o = bpy.context.object; o.scale = (1.0, rnd.uniform(0.7, 1.0), 1); o.data.materials.append(dirt)

# ------------------------------------------------------------------ pet
pet_dir = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Pets', 'pet_01')
try:
    bpy.ops.import_scene.fbx(filepath=os.path.join(pet_dir, 'pet_01.fbx'))
    objs = list(bpy.context.selected_objects)
    pm = bpy.data.materials.new('pet'); pm.use_nodes = True
    tex = pm.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(os.path.join(pet_dir, 'pet_01_basecolor.jpg'))
    pm.node_tree.links.new(tex.outputs['Color'], pm.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    meshes = [o for o in objs if o.type == 'MESH']
    for o in meshes: o.data.materials.clear(); o.data.materials.append(pm)
    bpy.context.view_layer.update()
    mn = V((1e9,) * 3); mx = V((-1e9,) * 3)
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ V(c); mn = V(map(min, mn, w)); mx = V(map(max, mx, w))
    s = 1.0 / max(mx.z - mn.z, 1e-3)
    for o in [o for o in objs if o.parent is None]:
        o.scale = o.scale * s; o.rotation_euler.z += math.radians(-20)
        o.location = (0.2 - (mn.x + mx.x) / 2 * s, -0.6 - (mn.y + mx.y) / 2 * s, gz(0.2, -0.6) - mn.z * s)
except Exception as e:
    print('pet yok', e)

# ------------------------------------------------------------------ sis: yumuşak beyaz bulut kümeleri (kenarlar)
fog = bpy.data.materials.new('fog'); fog.use_nodes = True; fn = fog.node_tree.nodes; fl = fog.node_tree.links
for x_ in list(fn): fn.remove(x_)
o_ = fn.new('ShaderNodeOutputMaterial'); mx_ = fn.new('ShaderNodeMixShader'); tr = fn.new('ShaderNodeBsdfTransparent')
em = fn.new('ShaderNodeBsdfPrincipled'); em.inputs['Base Color'].default_value = (0.97, 0.98, 1.0, 1); em.inputs['Roughness'].default_value = 1.0
em.inputs['Emission Color'].default_value = (0.9, 0.93, 0.97, 1); em.inputs['Emission Strength'].default_value = 0.2
lw = fn.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.55
pw = fn.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.6
fl.new(lw.outputs['Facing'], pw.inputs[0]); fl.new(pw.outputs[0], mx_.inputs['Fac'])
fl.new(em.outputs[0], mx_.inputs[1]); fl.new(tr.outputs[0], mx_.inputs[2]); fl.new(mx_.outputs[0], o_.inputs['Surface'])
fog.blend_method = 'BLEND'
def fogbank(cx, cy, n, spread):
    for _ in range(n):
        x, y = cx + rnd.uniform(-spread, spread), cy + rnd.uniform(-spread * 0.5, spread * 0.5); s = rnd.uniform(0.6, 1.2)
        blob('fog', (x, y, 0.4 + rnd.uniform(0, 0.6)), (s * 1.3, s, s * 0.6), fog, sub=1, seg=16)
fogbank(9.8, 5.2, 50, 3.0); fogbank(10.8, -0.5, 30, 1.8); fogbank(-10.8, 6.2, 34, 2.6); fogbank(0, 8.4, 40, 7)

# ------------------------------------------------------------------ kamera: kuşbakışına yakın (oyun haritası açısı)
cd = bpy.data.cameras.new('cam'); cd.lens = 26
co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
co.location = (0.0, -8.6, 11.0)
tgt = V((0.0, 0.6, 0.0)); co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.resolution_x, sc.render.resolution_y = 1600, 740
for o in sc.collection.objects:
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        o.data.energy = 3.2; o.rotation_euler = (math.radians(42), 0, math.radians(-30))
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('ok', out)
