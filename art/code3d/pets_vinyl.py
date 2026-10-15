# Vinyl oyuncak tarzı petler, tamamen kodla (deneme 15 Ekim 2026):
#  - pofi_vinyl: onaylı Pofi konseptinin (turuncu tilki-tavşan) vinyl yorumu
#  - foki: yeni, orijinal ada peti — tombul pastel mavi fok yavrusu, başında küçük deniz yıldızı
# Kullanım: python -I pets_vinyl.py -- <çıktı_klasörü> [pofi_vinyl|foki]
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from kit import _finish
args = sys.argv[sys.argv.index('--') + 1:]; OUT = args[0]; ONLY = set(args[1:])
os.makedirs(OUT, exist_ok=True)

def eye(side, x, y, z, s=1.0, look=(0, 0)):
    """Parlak siyah göz + iki ışık noktası (vinyl oyuncakların 'canlı' bakışı)."""
    black = mat('eye', '#1d1420', rough=0.08, coat=1.0)
    white = mat('glint', '#ffffff', rough=0.2, coat=0, emit=1.5)
    e = blob(f'eye{side}', (x, y, z), (0.062 * s, 0.035 * s, 0.078 * s), black, rot=(0, 0, -side * 14))
    g1 = blob(f'glint{side}a', (x + 0.02 * s + look[0], y - 0.03 * s, z + 0.03 * s + look[1]), (0.019 * s, 0.01 * s, 0.022 * s), white, sub=1, seg=12)
    g2 = blob(f'glint{side}b', (x - 0.022 * s + look[0], y - 0.03 * s, z - 0.03 * s + look[1]), (0.008 * s, 0.006 * s, 0.009 * s), white, sub=1, seg=10)
    return [e, g1, g2]

def pofi_vinyl():
    sc = reset()
    O = mat('orange', '#ff8a2a', rough=0.32, coat=0.35)
    C = mat('cream', '#fff1dc', rough=0.34, coat=0.3)
    PK = mat('blush', '#ff9c9c', rough=0.5, coat=0)
    BR = mat('nose', '#5a2f2a', rough=0.2, coat=0.6)
    parts = []
    for s in (-1, 1):
        parts.append(blob(f'foot{s}', (0.12 * s, -0.04, 0.045), (0.085, 0.11, 0.05), O))
        parts.append(blob(f'leg{s}', (0.11 * s, 0.0, 0.13), (0.07, 0.07, 0.09), O))
        parts.append(blob(f'arm{s}', (0.25 * s, -0.04, 0.42), (0.06, 0.06, 0.13), O, rot=(10, -s * 38, 0)))
        parts.append(blob(f'paw{s}', (0.31 * s, -0.07, 0.33), (0.055, 0.055, 0.055), C))
    parts.append(blob('body', (0, 0, 0.38), (0.24, 0.21, 0.27), O))
    parts.append(blob('belly', (0, -0.115, 0.36), (0.155, 0.11, 0.2), C))
    parts.append(blob('head', (0, -0.01, 0.9), (0.4, 0.34, 0.35), O))
    parts.append(blob('muzzle', (0, -0.245, 0.8), (0.21, 0.12, 0.14), C))
    parts.append(blob('nose', (0, -0.36, 0.86), (0.035, 0.025, 0.026), BR, sub=1))
    parts.append(tube('mouth', [(-0.045, -0.358, 0.8), (-0.022, -0.366, 0.785), (0, -0.362, 0.805), (0.022, -0.366, 0.785), (0.045, -0.358, 0.8)],
                      [0.006] * 5, BR))
    for s in (-1, 1):
        parts += eye(s, 0.165 * s, -0.27, 0.93)
        parts.append(blob(f'blush{s}', (0.27 * s, -0.235, 0.82), (0.055, 0.02, 0.035), PK, rot=(0, 0, s * 30), sub=1))
        # kulaklar: dış turuncu, iç krem; hafif dışa eğik
        ex, ez = 0.17 * s, 1.43
        parts.append(blob(f'ear{s}', (ex, 0.0, ez), (0.105, 0.065, 0.3), O, rot=(0, s * 12, 0)))
        parts.append(blob(f'earin{s}', (ex - 0.008 * s, -0.04, ez - 0.02), (0.06, 0.035, 0.22), C, rot=(0, s * 12, 0)))
    # kuyruk: arkada yukarı kıvrık, beyaz uç
    parts.append(tube('tail', [(0.1, 0.16, 0.22), (0.28, 0.3, 0.3), (0.42, 0.36, 0.5), (0.44, 0.32, 0.7)], [0.07, 0.15, 0.17, 0.145], O))
    parts.append(tube('tailtip', [(0.44, 0.32, 0.68), (0.425, 0.29, 0.83), (0.37, 0.25, 0.93)], [0.145, 0.12, 0.03], C))
    return sc, parts, (0, 0, 0.75), 3.4

def foki():
    sc = reset()
    B = mat('seal', '#9cc8f0', rough=0.3, coat=0.35)
    W = mat('white', '#f4f9ff', rough=0.32, coat=0.3)
    D = mat('dark', '#2b3550', rough=0.2, coat=0.6)
    PK = mat('blush', '#ff9fb2', rough=0.5, coat=0)
    ST = mat('star', '#ff8e6e', rough=0.35, coat=0.4)
    STD = mat('stardot', '#ffd2a8', rough=0.4, coat=0.2)
    parts = []
    # gövde + baş tek parça: elipsoitler birleştirilip voksel ile yeniden örülür, sonra yumuşatılır (boyun geçişi yumuşak)
    pieces = [blob('b0', (0, 0.02, 0.36), (0.36, 0.33, 0.38), B, sub=0, seg=48),
              blob('b1', (0, -0.02, 0.82), (0.36, 0.33, 0.32), B, sub=0, seg=48),
              blob('b2', (0, 0.1, 0.12), (0.3, 0.3, 0.14), B, sub=0, seg=48)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces: o.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join(); body = bpy.context.object; body.name = 'sealbody'
    rm = body.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.014
    bpy.ops.object.modifier_apply(modifier='rm')
    sm = body.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); sm.factor = 1.0; sm.iterations = 30; sm.smooth_type = 'LENGTH_WEIGHTED'; sm.use_only_smooth = True
    bpy.ops.object.modifier_apply(modifier='sm')
    dec = body.modifiers.new('dec', 'DECIMATE'); dec.ratio = 0.35
    for p in body.data.polygons: p.use_smooth = True
    parts.append(body)
    parts.append(blob('belly', (0, -0.2, 0.36), (0.25, 0.12, 0.27), W))
    parts.append(blob('muzzleL', (-0.075, -0.33, 0.73), (0.095, 0.07, 0.07), W))
    parts.append(blob('muzzleR', (0.075, -0.33, 0.73), (0.095, 0.07, 0.07), W))
    parts.append(blob('nose', (0, -0.39, 0.78), (0.045, 0.03, 0.032), D, sub=1))
    parts.append(tube('mouth', [(-0.03, -0.395, 0.69), (0, -0.4, 0.675), (0.03, -0.395, 0.69)], [0.006] * 3, D))
    for s in (-1, 1):
        for k in range(3):   # bıyık noktaları
            parts.append(blob(f'dot{s}{k}', (s * (0.08 + 0.03 * k), -0.395 + 0.012 * k, 0.74 + 0.025 * (k % 2)), (0.008, 0.005, 0.008), D, sub=0, seg=10))
        parts += eye(s, 0.15 * s, -0.31, 0.9, s=1.15)
        parts.append(blob(f'blush{s}', (0.255 * s, -0.27, 0.76), (0.06, 0.02, 0.038), PK, rot=(0, 0, s * 32), sub=1))
        # ön yüzgeçler: yanlarda, hafif öne
        parts.append(blob(f'flip{s}', (0.36 * s, -0.08, 0.3), (0.075, 0.13, 0.2), B, rot=(25, s * 35, s * 15)))
        # arka yüzgeçler: altta iki yana açık
        parts.append(blob(f'rear{s}', (0.16 * s, 0.32, 0.05), (0.13, 0.17, 0.045), B, rot=(0, 0, s * 35)))
    # başta deniz yıldızı (5 kollu, yumuşak)
    bm = bmesh.new()
    n = 5; outer, inner, th = 0.13, 0.06, 0.035
    ring = []
    for i in range(n * 2):
        a = math.pi / 2 + i * math.pi / n; r = outer if i % 2 == 0 else inner
        ring.append((r * math.cos(a), r * math.sin(a)))
    top = [bm.verts.new((x, y, th)) for x, y in ring]; bot = [bm.verts.new((x, y, 0)) for x, y in ring]
    bm.faces.new(top); bm.faces.new(list(reversed(bot)))
    for i in range(len(ring)):
        j = (i + 1) % len(ring); bm.faces.new((bot[i], bot[j], top[j], top[i]))
    me = bpy.data.meshes.new('star'); bm.to_mesh(me); bm.free()
    star = bpy.data.objects.new('star', me); sc.collection.objects.link(star)
    star.location = (0.13, -0.06, 1.12); star.rotation_euler = (math.radians(-18), math.radians(22), math.radians(10))
    _finish(star, ST, sub=3)
    parts.append(star)
    for i in range(5):
        a = math.pi / 2 + i * 2 * math.pi / 5
        p = star.matrix_world @ V((0.06 * math.cos(a), 0.06 * math.sin(a), th + 0.004))
        parts.append(blob(f'sd{i}', tuple(p), (0.014, 0.014, 0.01), STD, sub=1, seg=10))
    return sc, parts, (0, 0, 0.6), 3.2

for name, fn in (('pofi_vinyl', pofi_vinyl), ('foki', foki)):
    if ONLY and name not in ONLY: continue
    sc, parts, target, dist = fn()
    to_mesh_all()
    parts = [o for o in sc.objects if o.type == 'MESH']
    tris = tri_count(parts)
    export_glb(f'{OUT}/{name}.glb', parts)
    outline(parts, width=0.011)
    g = ground(4, '#a8dc84')
    for yaw, tag in ((-28, 'a'), (0, 'b'), (150, 'c')):
        shoot(sc, f'{OUT}/{name}_{tag}.png', target, dist, yaw, 14, lens=50, size=(900, 1000))
    print(name, 'üçgen', tris, flush=True)
