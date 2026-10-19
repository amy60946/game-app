# Görsel taslak v2: işaret eden beyaz çizgi film eldiveni (tanıtım ipucu eli). Özgün, kodla.
#   python3.11 -I glove_mockup.py -- çıktı.png
import bpy, math, sys, os, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code3d'))
import kit
from kit import mat, blob, cyl, srgb
out = sys.argv[sys.argv.index('--') + 1]
sc = kit.reset(); sc.cycles.samples = 64; sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 512
bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = srgb('#d9d6d0'); bg.inputs['Strength'].default_value = 0.55
glove = mat('glove', '#f7f7f9', 0.5, 0.15); seam = mat('seam', '#c9ced8', 0.6, 0)
parts = []
def P(o): parts.append(o); return o
# avuç (ön-arka basık) + manşet
P(blob('palm', (0, 0, 0), (0.5, 0.34, 0.5), glove))
c = P(cyl('cuff', (0.0, 0, -0.6), 0.4, 0.28, glove, verts=48, bevel=0.12)); c.scale = (1.05, 0.82, 1)
c2 = P(cyl('cuffline', (0.0, 0, -0.47), 0.41, 0.035, seam, verts=48, bevel=0.012)); c2.scale = (1.06, 0.84, 1)
# işaret parmağı: tombul kapsül, yukarı
P(cyl('index', (0.12, -0.04, 0.68), 0.18, 0.62, glove, verts=40, bevel=0.0))
P(blob('itip', (0.12, -0.04, 0.99), (0.18, 0.18, 0.18), glove))
P(blob('ibase', (0.12, -0.04, 0.38), (0.19, 0.19, 0.16), glove))
# kıvrık üç parmak: avucun önünde topaklar
for i, (x, z) in enumerate(((-0.1, 0.34), (-0.3, 0.24), (-0.45, 0.06))):
    P(blob(f'k{i}', (x, -0.28, z), (0.17, 0.19, 0.17), glove))
# başparmak: öne-yana yatık kapsül
P(blob('thumb', (0.4, -0.3, 0.02), (0.15, 0.16, 0.26), glove, rot=(55, -20, 0)))
# sırt dikişleri
for x in (-0.18, 0.0, 0.18):
    P(blob('l', (x, 0.32, 0.0), (0.012, 0.02, 0.26), seam, sub=0, seg=8))
root = bpy.data.objects.new('root', None); sc.collection.objects.link(root)
for o in parts: o.parent = root
root.rotation_euler = (math.radians(-12), math.radians(-28), math.radians(-20))
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = 3.0
co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
co.location = (0.0, -6, 0.3); co.rotation_euler = (math.radians(90), 0, 0)
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('ok', out)
