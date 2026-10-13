"""Blockout ölçüleri: boy (m) ve üçgen sayısı (alt bölme seviye 1, viewport) — docs/art için tablo."""
import os, sys
import bpy
sys.path.insert(0, os.path.dirname(__file__))
import pets
from mathutils import Vector

def stats(pid, stage):
    bpy.ops.wm.read_factory_settings(use_empty=True); pets._mats.clear()
    b = pets.build(pid, stage)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tris, zmax, zhead = 0, 0.0, 0.0
    for ob in b.parts:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        for v in me.vertices:
            z = (ev.matrix_world @ v.co).z
            zmax = max(zmax, z)
            if ob.name.endswith('_head'):
                zhead = max(zhead, z)
        ev.to_mesh_clear()
    head = [o for o in b.parts if o.name.endswith('_head')][0]
    hb = head.evaluated_get(dg)
    zs = [(hb.matrix_world @ Vector(c)).z for c in hb.bound_box]
    return zmax, zhead, (max(zs) - min(zs)) / zhead, tris

print('| Pet | Evre | Toplam boy (kulak/anten dahil) | Kafa üstüne kadar boy | Kafa / boy | Üçgen (blockout) |')
print('|---|---|---|---|---|---|')
for pid, spec in pets.PETS.items():
    for st in pets.STAGES:
        if st != 'genc' and pid not in ('pet_01',):
            continue
        z, zh, ratio, tris = stats(pid, st)
        print(f"| {spec['name']} | {st} | {z:.2f} m | {zh:.2f} m | %{ratio * 100:.0f} | {tris:,} |")
