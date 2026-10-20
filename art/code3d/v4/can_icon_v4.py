# Sulama kabı simgesi (şeffaf arka plan; arayüz taslağı için): /tmp/claude-0/bpyenv/bin/python can_icon_v4.py -- <çıktı.png>
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_v4 as G
from kit import reset, shoot, to_mesh_all, grain_uv
import bpy
out = sys.argv[sys.argv.index('--') + 1]
sc = reset(); sc.cycles.samples = 48; sc.render.film_transparent = True
G.watering_can((0, 0, 0)); to_mesh_all()
for o in bpy.context.scene.objects:
    if o.type == 'MESH' and 'grain' not in o.data.uv_layers: grain_uv(o)
shoot(sc, out, (0.12, 0, 0.2), 1.3, 0, 12, 50, (512, 512))
