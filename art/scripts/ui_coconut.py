# Hindistan cevizi yakalama oyunu simgeleri (kredisiz, prosedürel): lifli kahverengi ceviz + altın ceviz.
# Kullanım: python -I ui_coconut.py -- çıktı_klasörü   → ui_coconut.png, ui_coconut_gold.png (256², şeffaf)
import bpy, math, sys
out = sys.argv[sys.argv.index('--') + 1]

def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 256; sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = 2.9
    co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (0, -6, 0.05); co.rotation_euler = (math.radians(90), 0, 0)
    sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3.0
    so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(55), math.radians(-20), math.radians(-35))
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.7, 0.78, 0.9, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
    return sc

def coconut(gold):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=48, radius=1.0)
    o = bpy.context.object; o.scale = (0.92, 0.92, 1.0); o.rotation_euler = (math.radians(38), 0, math.radians(12))   # üst (gözler) kameraya eğik
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new('m'); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    b = n['Principled BSDF']
    tc = n.new('ShaderNodeTexCoord')
    # lifler: dikey uzatılmış gürültü (renk ve kabartı)
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (14, 14, 2.5)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 8
    l.new(mp.outputs['Vector'], nz.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    if gold:
        ramp.color_ramp.elements[0].color = (0.85, 0.38, 0.0, 1); ramp.color_ramp.elements[1].color = (1.0, 0.75, 0.15, 1)
        b.inputs['Metallic'].default_value = 0.45; b.inputs['Roughness'].default_value = 0.38
    else:
        ramp.color_ramp.elements[0].color = (0.06, 0.028, 0.01, 1); ramp.color_ramp.elements[1].color = (0.3, 0.15, 0.055, 1)
        ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.7
        b.inputs['Roughness'].default_value = 0.85
    l.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    # üstte üç "göz"
    l.new(ramp.outputs['Color'], b.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.45 if not gold else 0.15
    l.new(nz.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    o.data.materials.append(m)
    for i in range(3):
        a = math.radians(90 + i * 120)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.11, location=(math.cos(a) * 0.2, math.sin(a) * 0.2 - 0.05, 0.97))
        e = bpy.context.object; e.scale = (1, 1, 0.45); bpy.ops.object.shade_smooth()
        em = bpy.data.materials.new('e'); em.use_nodes = True
        em.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.5, 0.25, 0.02, 1) if gold else (0.06, 0.03, 0.015, 1)
        em.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6
        e.data.materials.append(em); e.parent = o
    return o

for gold, name in ((False, 'ui_coconut'), (True, 'ui_coconut_gold')):
    sc = scene(); coconut(gold)
    sc.render.filepath = f"{out}/{name}_raw.png"; bpy.ops.render.render(write_still=True)
