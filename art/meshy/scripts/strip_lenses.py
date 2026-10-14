"""Gözlük modelinden beyaz/opak cam yüzlerini siler (yalnız çerçeve kalır).
Kullanım: python strip_lenses.py girdi.glb çıktı.glb [eşik=0.8]
Her yüzün UV merkezindeki doku rengine bakılır; açık ve düşük doygunluklu yüzler silinir."""
import bpy, bmesh, sys
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
src, dst = a[0], a[1]
thr = float(a[2]) if len(a) > 2 else 0.8
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
removed = 0
for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
    mat = ob.active_material
    img = None
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image is not None:
                img = n.image; break
    if img is None: continue
    w, h = img.size; px = list(img.pixels)
    bm = bmesh.new(); bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.active
    kill = []
    for f in bm.faces:
        u = sum(l[uv].uv.x for l in f.loops) / len(f.loops); v = sum(l[uv].uv.y for l in f.loops) / len(f.loops)
        x = min(w - 1, max(0, int(u % 1 * w))); y = min(h - 1, max(0, int(v % 1 * h)))
        i = (y * w + x) * 4; r, g, b = px[i], px[i + 1], px[i + 2]
        mx, mn = max(r, g, b), min(r, g, b)
        if mx > thr and (mx - mn) < 0.12: kill.append(f)
    removed += len(kill)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(ob.data); bm.free()
print("silinen yüz", removed)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB")
