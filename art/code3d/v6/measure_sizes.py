# v6 oyun modellerinin gerçek boyları (m) → Resources/Data/env_v6_sizes.json. Oyun (RealAssets.EnvScaled) FBX birim ölçeğinden
# bağımsız olsun diye model yüksekliğini buna eşitler.   /tmp/claude-0/bpyenv/bin/python -I measure_sizes.py -- ad1 ad2 ...
import sys, os, json
import bpy
from mathutils import Vector as V
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
OUT = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Data', 'env_v6_sizes.json')
names = sys.argv[sys.argv.index('--') + 1:]
data = json.load(open(OUT)) if os.path.exists(OUT) else {}
for n in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ENV, n, n + '.fbx'))
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ V(c) for o in bpy.context.scene.objects if o.type == 'MESH' for c in o.bound_box]
    data[n] = round(max(p.z for p in pts) - min(p.z for p in pts), 4)
json.dump(dict(_doc='v6 modellerinin gerçek boyu (m, ölçek 1); art/code3d/v6/measure_sizes.py', **{k: v for k, v in sorted(data.items()) if k != '_doc'}), open(OUT, 'w'), indent=1, ensure_ascii=False)
print(data)
