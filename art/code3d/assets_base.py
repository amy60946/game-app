# Okti'nin çıkarılamayan temel giysisi (kullanıcı, 23 Ekim 2026: "karakter çıplak kalamıyor olsun"): şort — kodla, özgün tasarım.
# Temel üst = shirt_stripes kalıbı düz sarı (Items/base_top, art/code3d/base_top.py değil: doku export_game dışında, CosmeticModels.Base).
# Ölçü serbest (oyun sınır kutusundan ölçekler); ön = −Y, yukarı = +Z. Kullanım: export_game.py base_bottom
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets_town import *
from assets_items import m_fabric

def w_base_bottom():
    """Şort: yumuşak pamuklu mercan kumaş, iki kısa paça (hafif bol, uçları kıvrık), koyu bel lastiği + krem bağcık, yanlarda krem şerit,
    arkada küçük cep. Gövde ve paçalar voksel ile tek parça yumuşak yüzey."""
    FAB = m_fabric('#ef6f5e', name='shorts'); BAND = m_fabric('#c94f45', name='band'); TRIM = m_fabric('#fff1d6', name='trim')
    parts = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.0, depth=0.42, location=(0, 0, -0.16))
    hip = bpy.context.object; hip.scale = (0.52, 0.38, 1.0); parts.append(hip)
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.0, depth=0.36, location=(sx * 0.255, 0, -0.42))
        leg = bpy.context.object; leg.scale = (0.255, 0.31, 1.0); leg.rotation_euler = (0, math.radians(-sx * 6), 0); parts.append(leg)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = hip; bpy.ops.object.join()
    body = bpy.context.object; body.name = 'shorts'
    rm = body.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.018
    sm = body.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 12
    body.data.materials.clear(); body.data.materials.append(FAB)
    for p in body.data.polygons: p.use_smooth = True
    # bel lastiği (üstte, gövdenin hemen dışında)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.075, location=(0, 0, 0.04), major_segments=48, minor_segments=10)
    t = bpy.context.object; t.scale = (0.53, 0.39, 0.9); t.data.materials.append(BAND); smooth(t)
    # paça kıvrımları
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.05, location=(sx * 0.27, 0, -0.6), major_segments=32, minor_segments=8)
        c = bpy.context.object; c.scale = (0.26, 0.315, 1.0); c.rotation_euler = (0, math.radians(-sx * 6), 0); c.data.materials.append(FAB); smooth(c)
    # yan şeritler (krem), önde bağcık
    for sx in (-1, 1):
        rbox('stripe', (sx * 0.515, 0, -0.27), (0.03, 0.07, 0.62), TRIM, rot=(0, sx * 4, 0), bevel=0.012)
    tube('lace1', [(-0.03, -0.395, 0.03), (-0.07, -0.41, -0.06), (-0.09, -0.405, -0.14)], [0.014, 0.013, 0.012], TRIM, res=6)
    tube('lace2', [(0.03, -0.395, 0.03), (0.06, -0.41, -0.07), (0.05, -0.405, -0.15)], [0.014, 0.013, 0.012], TRIM, res=6)
    for sx in (-1, 1): blob('aglet', (sx * 0.07 if sx > 0 else -0.09, -0.405, -0.15 if sx > 0 else -0.14), (0.018, 0.018, 0.026), BAND, sub=1, seg=10)
    # arka cep
    rbox('pocket', (0.2, 0.385, -0.24), (0.16, 0.02, 0.15), BAND, rot=(8, 0, 0), bevel=0.02)
    return 'şort'

BUILDERS = {'w_base_bottom': (w_base_bottom, 512, None)}

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    OUT = args[0]; only = args[1:] or list(BUILDERS)
    os.makedirs(OUT, exist_ok=True)
    for name in only:
        fn, size, dec = BUILDERS[name]
        reset(); fn(); to_mesh_all()
        for o in bpy.context.scene.objects:
            if o.type == 'MESH' and 'grain' not in o.data.uv_layers: grain_uv(o)
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        tris = export_baked_fbx(f'{OUT}/{name}', objs, size=size, decimate=dec, ao_strength=float(os.environ.get('POFI_AO', '0.55')))
        print(name, 'üçgen', tris, flush=True)
