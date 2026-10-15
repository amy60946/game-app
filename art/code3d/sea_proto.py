# Deniz prototipi (EEVEE, gerçek zamanlı): kıyıya vuran dalgalar, dalga ucunda köpük, sığ turkuaz → derin mavi, ıslak kum,
# güneş parıltısı; gölgeye düşen yerde parıltı/köpük azalır (palmiye + kaya gölgesi). Onaydan sonra oyunun Pofi/Water
# gölgelendiricisine taşınacak (aynı formüller: derinlik → renk, kıyı mesafesi → köpük bandı, zamanla kıyıya ilerleyen dalga).
# Kullanım: EGL_PLATFORM=surfaceless python -I sea_proto.py -- <çıktı_klasörü> <varlık_klasörü> [kare_sayısı]
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, mathutils
from kit import srgb
args = sys.argv[sys.argv.index('--') + 1:]
OUT, ASSETS = args[0], args[1]; FRAMES = int(args[2]) if len(args) > 2 else 1
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
try: sc.eevee.taa_render_samples = 16
except Exception: pass
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 12

# gökyüzü (yalnız kamerada) + hafif ortam ışığı
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
n = w.node_tree.nodes; l = w.node_tree.links
bg = n['Background']; tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); rp = n.new('ShaderNodeValToRGB')
rp.color_ramp.elements[0].position = 0.5; rp.color_ramp.elements[0].color = srgb('#d6f1ff'); rp.color_ramp.elements[1].position = 0.75; rp.color_ramp.elements[1].color = srgb('#5cb8f5')
l.new(tc.outputs['Generated'], sep.inputs[0]); l.new(sep.outputs['Z'], rp.inputs['Fac']); l.new(rp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.7
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(1.5); sun.color = (1.0, 0.96, 0.88)
so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(-200))    # sağ-önden: parıltı yolu denizde, nesneler yandan aydınlık

SLOPE, SHORE = 0.07, 4.0     # kum yüksekliği: z = SLOPE*(SHORE - y)  → y > SHORE deniz
def frame_driver(sock, expr='frame/12.0'):
    d = sock.driver_add('default_value').driver; d.type = 'SCRIPTED'; d.expression = expr

def sand_mat():
    m = bpy.data.materials.new('sand'); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']; b.inputs['Roughness'].default_value = 0.95
    tco = n.new('ShaderNodeTexCoord'); sxyz = n.new('ShaderNodeSeparateXYZ'); l.new(tco.outputs['Object'], sxyz.inputs[0])
    # ıslak kum: kıyı çizgisine yakın koyu (dalga çekilince parlak ıslak iz)
    wet = n.new('ShaderNodeMapRange'); wet.interpolation_type = 'SMOOTHSTEP'
    wet.inputs['From Min'].default_value = SHORE - 1.6; wet.inputs['From Max'].default_value = SHORE - 0.2; l.new(sxyz.outputs['Y'], wet.inputs['Value'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 6; l.new(tco.outputs['Object'], nz.inputs['Vector'])
    dry = n.new('ShaderNodeValToRGB'); dry.color_ramp.elements[0].color = srgb('#efd39a'); dry.color_ramp.elements[1].color = srgb('#fbe6b6')
    l.new(nz.outputs['Fac'], dry.inputs['Fac'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb('#cfa86e')
    l.new(wet.outputs[0], mx.inputs['Factor']); l.new(dry.outputs[0], mx.inputs[6])
    l.new(mx.outputs[2], b.inputs['Base Color'])
    rg = n.new('ShaderNodeMapRange'); rg.inputs['To Min'].default_value = 0.95; rg.inputs['To Max'].default_value = 0.35
    l.new(wet.outputs[0], rg.inputs['Value']); l.new(rg.outputs[0], b.inputs['Roughness'])
    # rüzgâr çizgileri (hafif kabartı)
    wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 2.5; wv.inputs['Distortion'].default_value = 4; l.new(tco.outputs['Object'], wv.inputs['Vector'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.15; l.new(wv.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs[0], b.inputs['Normal'])
    return m

def water_mat():
    """derinlik d = SLOPE*(y - SHORE) (kum eğiminden, analitik). Renk: d küçük → kum tonlu sığ turkuaz → turkuaz → derin mavi.
    Köpük: (a) kıyı teması, (b) zamanla kıyıya ilerleyen dalga bantları (sin(d·k − t)), gürültüyle parçalı; derinde söner.
    Parıltı: düşük pürüzlülük + hareketli gürültü kabartısı (güneş yolunda pırıltı); gölgede doğal olarak azalır."""
    m = bpy.data.materials.new('water'); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']; b.inputs['Roughness'].default_value = 0.08; b.inputs['Specular IOR Level'].default_value = 0.35
    tco = n.new('ShaderNodeNewGeometry'); sxyz = n.new('ShaderNodeSeparateXYZ'); l.new(tco.outputs['Position'], sxyz.inputs[0])   # dünya konumu
    dep = n.new('ShaderNodeMath'); dep.operation = 'MULTIPLY_ADD'; dep.inputs[1].default_value = SLOPE; dep.inputs[2].default_value = -SLOPE * SHORE
    l.new(sxyz.outputs['Y'], dep.inputs[0])
    col = n.new('ShaderNodeMapRange'); col.inputs['From Min'].default_value = 0.0; col.inputs['From Max'].default_value = 0.6; l.new(dep.outputs[0], col.inputs['Value'])
    cr = n.new('ShaderNodeValToRGB'); el = cr.color_ramp.elements
    el[0].position = 0.0; el[0].color = srgb('#c9f0d8'); el[1].position = 1.0; el[1].color = srgb('#1569b5')
    e = el.new(0.12); e.color = srgb('#6fe3d4'); e = el.new(0.35); e.color = srgb('#2ec0cf'); e = el.new(0.65); e.color = srgb('#1e8fd0')
    l.new(col.outputs[0], cr.inputs['Fac'])
    # zaman
    tval = n.new('ShaderNodeValue'); frame_driver(tval.outputs[0])
    # dalga bantları: sin(d*45 - t*3)
    k1 = n.new('ShaderNodeMath'); k1.operation = 'MULTIPLY'; k1.inputs[1].default_value = 70.0; l.new(dep.outputs[0], k1.inputs[0])
    k2 = n.new('ShaderNodeMath'); k2.operation = 'MULTIPLY'; k2.inputs[1].default_value = 3.0; l.new(tval.outputs[0], k2.inputs[0])
    ph = n.new('ShaderNodeMath'); ph.operation = 'SUBTRACT'; l.new(k1.outputs[0], ph.inputs[0]); l.new(k2.outputs[0], ph.inputs[1])
    # yan yöne hafif kıvrım
    nzw = n.new('ShaderNodeTexNoise'); nzw.inputs['Scale'].default_value = 0.35; l.new(tco.outputs['Position'], nzw.inputs['Vector'])
    ph2 = n.new('ShaderNodeMath'); ph2.operation = 'MULTIPLY_ADD'; ph2.inputs[1].default_value = 4.0
    l.new(nzw.outputs['Fac'], ph2.inputs[0]); l.new(ph.outputs[0], ph2.inputs[2])
    sn = n.new('ShaderNodeMath'); sn.operation = 'SINE'; l.new(ph2.outputs[0], sn.inputs[0])
    band = n.new('ShaderNodeMapRange'); band.interpolation_type = 'SMOOTHSTEP'; band.inputs['From Min'].default_value = 0.8; band.inputs['From Max'].default_value = 0.97
    l.new(sn.outputs[0], band.inputs['Value'])
    fade = n.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = 0.03; fade.inputs['From Max'].default_value = 0.14
    fade.inputs['To Min'].default_value = 1; fade.inputs['To Max'].default_value = 0; l.new(dep.outputs[0], fade.inputs['Value'])
    fb = n.new('ShaderNodeMath'); fb.operation = 'MULTIPLY'; l.new(band.outputs[0], fb.inputs[0]); l.new(fade.outputs[0], fb.inputs[1])
    # kıyı teması
    edge = n.new('ShaderNodeMapRange'); edge.interpolation_type = 'SMOOTHSTEP'; edge.inputs['From Min'].default_value = 0.0; edge.inputs['From Max'].default_value = 0.02
    edge.inputs['To Min'].default_value = 1; edge.inputs['To Max'].default_value = 0; l.new(dep.outputs[0], edge.inputs['Value'])
    fsum = n.new('ShaderNodeMath'); fsum.operation = 'MAXIMUM'; l.new(fb.outputs[0], fsum.inputs[0]); l.new(edge.outputs[0], fsum.inputs[1])
    # parçalı köpük (hareketli gürültü)
    mp = n.new('ShaderNodeMapping'); l.new(tco.outputs['Position'], mp.inputs['Vector'])
    loc = mp.inputs['Location']; d = loc.driver_add('default_value', 1).driver; d.type = 'SCRIPTED'; d.expression = '-frame/12.0*0.18'
    fn = n.new('ShaderNodeTexNoise'); fn.inputs['Scale'].default_value = 7; fn.inputs['Detail'].default_value = 4; l.new(mp.outputs[0], fn.inputs['Vector'])
    br = n.new('ShaderNodeMapRange'); br.inputs['From Min'].default_value = 0.38; br.inputs['From Max'].default_value = 0.62; l.new(fn.outputs['Fac'], br.inputs['Value'])
    fm = n.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; l.new(fsum.outputs[0], fm.inputs[0]); l.new(br.outputs[0], fm.inputs[1])
    fmc = n.new('ShaderNodeMath'); fmc.operation = 'MULTIPLY'; fmc.use_clamp = True; fmc.inputs[1].default_value = 1.6; l.new(fm.outputs[0], fmc.inputs[0])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = srgb('#ffffff')
    l.new(fmc.outputs[0], mx.inputs['Factor']); l.new(cr.outputs[0], mx.inputs[6])
    l.new(mx.outputs[2], b.inputs['Base Color'])
    rg = n.new('ShaderNodeMapRange'); rg.inputs['To Min'].default_value = 0.06; rg.inputs['To Max'].default_value = 0.7
    l.new(fmc.outputs[0], rg.inputs['Value']); l.new(rg.outputs[0], b.inputs['Roughness'])
    # pırıltı: hareketli kabartı
    mp2 = n.new('ShaderNodeMapping'); l.new(tco.outputs['Position'], mp2.inputs['Vector'])
    d2 = mp2.inputs['Location'].driver_add('default_value', 0).driver; d2.type = 'SCRIPTED'; d2.expression = 'frame/12.0*0.25'
    bn = n.new('ShaderNodeTexNoise'); bn.inputs['Scale'].default_value = 5; bn.inputs['Detail'].default_value = 8; l.new(mp2.outputs[0], bn.inputs['Vector'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.15; bump.inputs['Distance'].default_value = 0.04
    l.new(bn.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs[0], b.inputs['Normal'])
    return m

# kum: hafif engebeli eğim
bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=120, size=1, location=(0, 0, 0))
sand = bpy.context.object; sand.scale = (30, 30, 1); bpy.ops.object.transform_apply(scale=True)
from mathutils import noise
for v in sand.data.vertices:
    v.co.z = SLOPE * (SHORE - v.co.y) + 0.04 * noise.noise(mathutils.Vector((v.co.x * 0.4, v.co.y * 0.4, 0)))
sand.data.materials.append(sand_mat())
for p in sand.data.polygons: p.use_smooth = True
# deniz: hafif dalgalı yüzey (yer değiştirme, zamanla kıyıya)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=160, size=1, location=(0, 0, 0))
sea = bpy.context.object; sea.scale = (90, 60, 1); bpy.ops.object.transform_apply(scale=True)
sea.location.y = 33.0
sea.data.materials.append(water_mat())
for p in sea.data.polygons: p.use_smooth = True
# palmiye + kaya (gölge düşürsün)
def load(name, loc, yaw, scale=1.0):
    before = set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=f'{ASSETS}/{name}.fbx')
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    img = bpy.data.images.load(f'{ASSETS}/{name}_basecolor.png')
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img
    m.node_tree.links.new(t.outputs[0], m.node_tree.nodes['Principled BSDF'].inputs['Base Color']); m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(m)
        o.location = loc; o.rotation_euler[2] = math.radians(yaw); o.scale = (scale,) * 3
    return objs
load('c_palm', (2.6, 2.6, SLOPE * (SHORE - 2.6)), 200, 1.0)
load('c_rock', (-2.4, 3.2, SLOPE * (SHORE - 3.2) - 0.05), 30, 1.3)
cam = bpy.data.cameras.new('c'); cam.sensor_fit = 'VERTICAL'; cam.angle = math.radians(46)
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0.0, -3.2, 3.2); co.rotation_euler = (mathutils.Vector((0.2, 7.5, 0.0)) - co.location).to_track_quat('-Z', 'Y').to_euler()
for f in range(FRAMES):
    sc.frame_set(f * 2 + 1)
    sc.render.filepath = f'{OUT}/sea_{f:02d}.png'; bpy.ops.render.render(write_still=True)
    print('kare', f, flush=True)
