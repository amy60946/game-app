# Giyilebilir eşya simgesi (256², şeffaf) oyundaki modelden: Resources/Items/<id>/<id>.fbx + _basecolor (+ varsa _spin parçası).
# Simge sayfasındaki eşyalarla aynı hava: parlak vinyl, yumuşak stüdyo ışığı, 3/4 açı, kareyi dolduran çerçeve.
# Kullanım: python -I wear_icon.py -- <id> [çıktı.png] [yaw=28] [pitch=14]   (çıktı yoksa Resources/Icons/<id>.png)
import sys, os, math, glob
import bpy
from mathutils import Vector as V
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, '../../Assets/_Pofi/Resources'))
a = sys.argv[sys.argv.index('--') + 1:]
iid = a[0]; out = a[1] if len(a) > 1 and a[1] else os.path.join(RES, 'Icons', iid + '.png')
yaw = float(a[2]) if len(a) > 2 else 28.0; pitch = float(a[3]) if len(a) > 3 else 14.0

bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
def load(part):
    d = os.path.join(RES, 'Items', iid)
    fbx = os.path.join(d, part + '.fbx')
    if not os.path.exists(fbx): return []
    before = set(bpy.data.objects.keys()); bpy.ops.import_scene.fbx(filepath=fbx)
    objs = [o for o in bpy.data.objects if o.name not in before]
    tex = next((p for p in glob.glob(os.path.join(d, part + '_basecolor.*'))), None)
    m = bpy.data.materials.new(part); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.38; b.inputs['Coat Weight'].default_value = 0.35; b.inputs['Coat Roughness'].default_value = 0.15
    if tex:
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(tex)
        m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    for o in objs:
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(m)
            for p in o.data.polygons: p.use_smooth = True
    return objs
objs = load(iid) + load(iid + '_spin')
glass = load(iid + '_glass')   # saydam parça (astronot kaskı camı; oyunda RealAssets.Item ile aynı)
for o in glass:
    for m in (o.data.materials if o.type == 'MESH' else []):
        b = m.node_tree.nodes['Principled BSDF']; tn = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
        if tn is not None: m.node_tree.links.new(tn.outputs['Alpha'], b.inputs['Alpha'])
        b.inputs['Roughness'].default_value = 0.05
        if hasattr(m, 'surface_render_method'): m.surface_render_method = 'BLENDED'
objs += glass
bpy.context.view_layer.update()
pts = [o.matrix_world @ V(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
mn = V([min(p[i] for p in pts) for i in range(3)]); mx = V([max(p[i] for p in pts) for i in range(3)])
c = (mn + mx) / 2; r = (mx - mn).length / 2

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 64; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.3
sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = 512
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.82, 0.86, 0.92, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.75
def area(name, energy, size, loc, col=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy * r * r; l.size = size * r; l.color = col
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = c + V(loc) * r * 3
    o.rotation_euler = (c - o.location).to_track_quat('-Z', 'Y').to_euler()
area('key', 260, 2.0, (-0.8, -1.0, 1.1), (1.0, 0.97, 0.92))
area('fill', 90, 3.0, (1.1, -0.7, 0.2), (0.85, 0.92, 1.0))
area('rim', 160, 1.5, (0.3, 1.2, 0.9))
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
y = math.radians(yaw); p = math.radians(pitch)
co.location = c + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * r * 6
co.rotation_euler = (c - co.location).to_track_quat('-Z', 'Y').to_euler()
# çerçeve: kameradan görünen genişlik/yükseklik → %92 doldur
bpy.context.view_layer.update()
inv = co.matrix_world.inverted()
cp = [inv @ q for o in objs if o.type == 'MESH' for q in (o.matrix_world @ v.co for v in o.data.vertices)]
wx = max(q.x for q in cp) - min(q.x for q in cp); wy = max(q.y for q in cp) - min(q.y for q in cp)
cd.ortho_scale = max(wx, wy) / 0.92
co.location += co.matrix_world.to_3x3() @ V(((max(q.x for q in cp) + min(q.x for q in cp)) / 2, (max(q.y for q in cp) + min(q.y for q in cp)) / 2, 0))
tmp = out + '.big.png'; sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
import subprocess
subprocess.run(['/usr/bin/python3', '-c', 'import sys\nfrom PIL import Image\nImage.open(sys.argv[1]).resize((256,256), Image.LANCZOS).save(sys.argv[2])', tmp, out], check=True)
os.remove(tmp); print('SIMGE', out)
