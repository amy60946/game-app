# Ada v6 · oyun kamerası çekimleri için yakın plan ayrıntı (21 Ekim 2026).
# Her çekimde petin önündeki ~40 m'ye kurulur, çekimden sonra silinir; uzakta ada genel dağılımı (island_v6.py) yeterli.
# Makro çim (numpy telleri), çan çiçeği / turuncu çiçek halıları (kuşbakışı lekelerle aynı maske), çakıl, eğrelti, mantar,
# kanyonda kum dalgası + çakıl, ormanda kovan + devrik kütük, karda bayraklı pist + kardan adam. Hepsi kodla özgün.
import math, random
import numpy as np
import bpy
from mathutils import Vector as V
import kit_v6 as K
import terrain_v6 as TV

MATS = {}
def mats():
    if not MATS:
        MATS['g'] = K.grass_blade_mat('ng_g', '#2f7a1f', '#66b53a', '#cfe85e')        # genel limon
        MATS['m'] = K.grass_blade_mat('ng_m', '#348a22', '#79c43c', '#ddf06a', 0.5)  # çayır: parlak
        MATS['d'] = K.grass_blade_mat('ng_d', '#5f7a26', '#a7a845', '#e6d778')       # kuru sarı
        MATS['f'] = K.grass_blade_mat('ng_f', '#21552a', '#3f8a38', '#93c75a', 0.3)  # orman: mavi-yeşil koyu
        MATS['s'] = K.grass_blade_mat('ng_s', '#4a7556', '#7fa880', '#c8dcc0', 0.3)  # kar yakını soğuk
    return MATS

def bil(arr, x, z):
    fi = (x - TV.X0) / TV.STEP; fj = (z - TV.Z0) / TV.STEP
    i = np.clip(np.floor(fi).astype(int), 0, arr.shape[1] - 2); j = np.clip(np.floor(fj).astype(int), 0, arr.shape[0] - 2)
    tx = fi - i; tz = fj - j
    return (arr[j, i] * (1 - tx) + arr[j, i + 1] * tx) * (1 - tz) + (arr[j + 1, i] * (1 - tx) + arr[j + 1, i + 1] * tx) * tz

def sector_pts(px, pz, hd, n, rad, R, back=6.0):
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    x = px + R.uniform(-rad, rad, n); z = pz + R.uniform(-rad, rad, n)
    dx, dz = x - px, z - pz; d = np.hypot(dx, dz); fwd = (dx * fx + dz * fz)
    ok = (d < rad) & ((fwd > -back) | (d < back))
    return x[ok], z[ok], d[ok]

def macro_grass(L, B, px, pz, hd, n=9_000_000, rad=40.0, seed=1, out=None, dens=1.0, avoid=None):
    R = np.random.default_rng(seed)
    x, z, d = sector_pts(px, pz, hd, n, rad, R, back=6.5)
    g = bil(L.gw, x, z)
    fall = np.where(d < 7, 1.0, (7.0 / np.maximum(d, 1e-3)) ** 1.5)
    keep = R.uniform(0, 1, len(x)) < g * fall * dens
    if avoid is not None: keep &= ~avoid(x, z)
    x, z, d = x[keep], z[keep], d[keep]
    y = bil(L.h, x, z) - 0.01; sc = 1.0 + np.maximum(0, d - 7) / 10.0
    fw = bil(B['forest'], x, z); mw = bil(B['meadow'], x, z); sn = bil(L.d['snow'], x, z)
    dry = bil(L.dry, x, z); rr = R.uniform(0, 1, len(x))
    kind = np.full(len(x), 'g', dtype='<U1')
    kind[(dry > 0.5) & (rr < 0.55)] = 'd'
    kind[(mw > 0.35) & (rr < 0.7)] = 'm'
    kind[rr < fw * 0.95] = 'f'
    kind[(sn > 0.05) | (bil(B['snowpeak'], x, z) * (rr < 0.7) > 0.3)] = 's'
    M = mats(); objs = []
    for k in 'gmdfs':
        sel = kind == k
        if sel.sum() == 0: continue
        P = np.stack([x[sel], z[sel], y[sel], sc[sel]], -1).astype(np.float32)
        objs.append(K.fast_blades('ngrass_' + k, P, M[k], seed=seed + ord(k)))
    if out is not None: out += objs
    print('çim teli', len(x))
    return int(len(x))

FLOWER = {}
def flower_protos():
    if not FLOWER:
        FLOWER['bell'] = [K.flower_patch_mesh('pb%d' % k, 'bell', 7, 100 + k, col=bpy.data.collections.new('C_pb%d' % k)) for k in range(4)]
        FLOWER['daisy'] = [K.flower_patch_mesh('pd%d' % k, 'daisy', 6, 120 + k, col=bpy.data.collections.new('C_pd%d' % k)) for k in range(3)]
        FLOWER['yellow'] = [K.flower_patch_mesh('py%d' % k, 'yellow', 3, 140 + k, col=bpy.data.collections.new('C_py%d' % k)) for k in range(3)]
    return FLOWER

def obj_inst(o, x, z, y, rot, s, out):
    e = bpy.data.objects.new('n_' + o.name, o.data); e.location = (x, z, y); e.rotation_euler = (0, 0, rot); e.scale = (s, s, s)
    bpy.context.scene.collection.objects.link(e); out.append(e); return e

def flowers(L, px, pz, hd, out, rad=34.0, seed=5, n=900000, boost=1.0):
    """Çiçek halıları: kuşbakışında görünen mavi/turuncu lekelerle aynı yerlerde, kümeler hâlinde."""
    R = np.random.default_rng(seed); F = flower_protos()
    x, z, d = sector_pts(px, pz, hd, n, rad, R, back=3.0)
    fall = np.where(d < 6, 1.0, (6.0 / np.maximum(d, 1e-3)) ** 1.2)
    for key, mask, dens in (('bell', L.fb, 0.06), ('daisy', L.fo, 0.035), ('yellow', np.ones_like(L.fb) * 0.35, 0.006)):
        p = np.clip(bil(mask, x, z) * 1.6, 0, 1) * bil(L.gw, x, z) * fall * dens * boost
        keep = R.uniform(0, 1, len(x)) < p
        for xi, zi, di in zip(x[keep], z[keep], d[keep]):
            s = 1.0 + max(0, di - 6) / 14.0
            obj_inst(random.choice(F[key]), float(xi), float(zi), float(bil(L.h, xi, zi)) - 0.01, R.uniform(0, 6.28), s, out)

def props_near(L, P, px, pz, hd, out, seed=9, rosettes=40, pebbles=60, region=None):
    R = random.Random(seed); Rn = np.random.default_rng(seed)
    x, z, d = sector_pts(px, pz, hd, 40000, 30.0, Rn, back=2.0)
    g = bil(L.gw, x, z); keep = (Rn.uniform(0, 1, len(x)) < g) & (d > 3.0)
    if region is not None: keep &= region(x, z)
    idx = np.where(keep)[0]; Rn.shuffle(idx)
    ros = [K.rosette('ros%d' % k, 9 + k, 0.8 + 0.2 * k, 0.11, 200 + k, col=bpy.data.collections.new('C_ros%d' % k)) for k in range(3)]
    for i in idx[:rosettes]:
        obj_inst(R.choice(ros), float(x[i]), float(z[i]), float(bil(L.h, x[i], z[i])) - 0.05, R.uniform(0, 6.28), R.uniform(0.6, 1.4), out)
    for i in idx[rosettes:rosettes + pebbles]:
        s = R.uniform(0.12, 0.45); col = R.choice(P['boulderB'])
        e = bpy.data.objects.new('n_peb', None); e.instance_type = 'COLLECTION'; e.instance_collection = col
        e.location = (float(x[i]), float(z[i]), float(bil(L.h, x[i], z[i])) - s * 0.3); e.scale = (s, s, s); e.rotation_euler = (0, 0, R.uniform(0, 6.28))
        bpy.context.scene.collection.objects.link(e); out.append(e)

def sand_ripples(L, px, pz, hd, out, rad=26.0, seed=11, mask=None, color='#e9d2a2'):
    """Kum dalgacıkları + çakıl: yakında küçük taneler (kanyon, koy)."""
    Rn = np.random.default_rng(seed)
    x, z, d = sector_pts(px, pz, hd, 300000, rad, Rn, back=3.0)
    m = bil(L.d['sand'], x, z) if mask is None else mask(x, z)
    keep = Rn.uniform(0, 1, len(x)) < m * np.where(d < 8, 0.0025, 0.0025 * (8 / np.maximum(d, 1)) ** 2)
    x, z = x[keep], z[keep]
    pm = K.rock_mat('n_grav', base='#9e9294', dark='#6f6670', light='#c4bab4', moss_amt=0.0, cracks=0.2)
    proto_ = K.boulder('n_gravel', (1.0, 0.8, 0.55), 5, cuts=5, mat=pm, bevel=0.3, top_flat=0.0, col=bpy.data.collections.new('C_grav'))
    for xi, zi in zip(x, z):
        obj_inst(proto_, float(xi), float(zi), float(bil(L.h, xi, zi)) - 0.01, Rn.uniform(0, 6.28), Rn.uniform(0.025, 0.07) * (1 + 2.5 * Rn.uniform() ** 6), out)

def beehives(L, px, pz, hd, out, n=4, seed=13):
    """Ormanda dallara asılı kovanlar (çekim önündeki çamlara)."""
    R = random.Random(seed); hv = K.beehive('n_hive', col=bpy.data.collections.new('C_hive'))
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    for k in range(n):
        t = R.uniform(7, 16); s = R.uniform(-6, 6); x = px + fx * t + fz * s; z = pz + fz * t - fx * s
        obj_inst(hv, x, z, float(bil(L.h, x, z)) + R.uniform(2.6, 3.6), 0, R.uniform(1.0, 1.4), out)

def ski(L, px, pz, hd, out):
    """Kayak pisti: kırmızı/mavi kapı bayrakları, kardan adam, kızak."""
    a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
    red = K.vcol_mat('n_red'); red.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#e8423a') + (1,)
    red.node_tree.links.remove(red.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0])
    blu = K.vcol_mat('n_blu'); blu.node_tree.links.remove(blu.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0])
    blu.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#2f7be8') + (1,)
    wh = K.vcol_mat('n_wh'); wh.node_tree.links.remove(wh.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0])
    wh.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#f4f7fb') + (1,)
    for k in range(6):
        t = 8 + k * 5.0; s = (-3.5 if k % 2 else 3.5) + math.sin(k) * 0.8
        x = px + fx * t + fz * s; z = pz + fz * t - fx * s; y = float(bil(L.h, x, z))
        m = red if k % 2 else blu
        out.append(K.mesh_obj('n_pole', [(x - 0.03, z, y), (x + 0.03, z, y), (x + 0.03, z, y + 1.5), (x - 0.03, z, y + 1.5)], [(0, 1, 2, 3)], m))
        out.append(K.mesh_obj('n_flag', [(x, z, y + 1.5), (x + 0.6 * fz, z - 0.6 * fx, y + 1.3), (x, z, y + 1.05)], [(0, 1, 2)], m))
    x = px + fx * 6 - fz * 3; z = pz + fz * 6 + fx * 3; y = float(bil(L.h, x, z))
    for (r, hgt) in ((0.45, 0.4), (0.33, 1.0), (0.24, 1.45)):
        ico = K._ico(2); out.append(K.mesh_obj('n_sm', [(x + q[0] * r, z + q[1] * r, y + hgt + q[2] * r) for q in ico], K._ICO_F[2], wh))
    nose = K.vcol_mat('n_nose'); nose.node_tree.links.remove(nose.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0])
    nose.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#f07a1a') + (1,)
    out.append(K.mesh_obj('n_nose', [(x - fx * 0.24 - 0.03, z - fz * 0.24, y + 1.45), (x - fx * 0.24 + 0.03, z - fz * 0.24, y + 1.45), (x - fx * 0.5, z - fz * 0.5, y + 1.47)], [(0, 1, 2)], nose))

def build(L, B, P, shot, px, pz, hd):
    out = []
    if shot == 'cayir':
        macro_grass(L, B, px, pz, hd, out=out); flowers(L, px, pz, hd, out, boost=1.5); props_near(L, P, px, pz, hd, out, rosettes=10, pebbles=40)
    elif shot == 'kanyon':
        macro_grass(L, B, px, pz, hd, out=out, dens=0.8); sand_ripples(L, px, pz, hd, out, mask=lambda x, z: np.clip(bil(L.d['canyon'], x, z), 0, 1) * 0.9)
        props_near(L, P, px, pz, hd, out, rosettes=14, pebbles=30)
    elif shot == 'kamp':
        macro_grass(L, B, px, pz, hd, out=out); flowers(L, px, pz, hd, out, boost=0.8); props_near(L, P, px, pz, hd, out, rosettes=8, pebbles=40)
    elif shot == 'orman':
        macro_grass(L, B, px, pz, hd, out=out, dens=0.9); beehives(L, px, pz, hd, out); props_near(L, P, px, pz, hd, out, rosettes=36, pebbles=30)
        mus = [K.mushroom('n_mu%d' % k, 0.1 + 0.03 * k, k, col=bpy.data.collections.new('C_mu%d' % k), cap=c) for k, c in enumerate(('#e8743a', '#c4462e', '#e8a03a'))]
        R = random.Random(3); a = math.radians(hd); fx, fz = math.sin(a), math.cos(a)
        for k in range(40):
            t = R.uniform(2.5, 14); s = R.uniform(-5, 5); x = px + fx * t + fz * s; z = pz + fz * t - fx * s
            obj_inst(R.choice(mus), x, z, float(bil(L.h, x, z)) - 0.01, R.uniform(0, 6.28), R.uniform(0.8, 1.6), out)
        lg = K.log('n_log', 3.4, 0.32, 7, col=bpy.data.collections.new('C_log'))
        x, z = px + fx * 8 + fz * 2.5, pz + fz * 8 - fx * 2.5
        for o in list(bpy.data.collections['C_log'].objects):
            e = bpy.data.objects.new('n_lg', o.data); e.location = (x, z, float(bil(L.h, x, z)) - 0.05); e.rotation_euler = (0, 0, a + 0.9); bpy.context.scene.collection.objects.link(e); out.append(e)
    elif shot in ('sahil', 'kopuk'):
        macro_grass(L, B, px, pz, hd, out=out, dens=0.9); sand_ripples(L, px, pz, hd, out); props_near(L, P, px, pz, hd, out, rosettes=4, pebbles=10)
    elif shot in ('magara',):
        macro_grass(L, B, px, pz, hd, out=out); flowers(L, px, pz, hd, out, boost=1.2); props_near(L, P, px, pz, hd, out, rosettes=8, pebbles=40)
    elif shot == 'kamp_yakin':
        macro_grass(L, B, px, pz, hd, out=out); flowers(L, px, pz, hd, out, boost=0.6)
    elif shot == 'yamac':
        macro_grass(L, B, px, pz, hd, out=out); flowers(L, px, pz, hd, out, boost=1.0); props_near(L, P, px, pz, hd, out, rosettes=6, pebbles=70)
    elif shot == 'koy':
        macro_grass(L, B, px, pz, hd, out=out); flowers(L, px, pz, hd, out, boost=1.0); props_near(L, P, px, pz, hd, out, rosettes=6, pebbles=20)
    elif shot == 'koy_kiyi':
        macro_grass(L, B, px, pz, hd, out=out, dens=0.9); sand_ripples(L, px, pz, hd, out); props_near(L, P, px, pz, hd, out, rosettes=6, pebbles=20)
    elif shot in ('kar', 'kar_patika'):
        macro_grass(L, B, px, pz, hd, out=out, dens=0.7); ski(L, px, pz, hd, out)
    return out
