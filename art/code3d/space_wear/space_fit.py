# Uzay kıyafetleri: evre başına yerleşim kuralları + kıyafet × hareket denemesi (25 Ekim 2026).
# 1) rules: her evrede kask/gözlük/taç başın, çanta/jetpack/pelerin sırtın ölçüsünden hesaplanır ve oyundaki
#    CosmeticModels.BuildReal formülüne (eşya sınır kutusu, boy × pet boyu, Head/Spine1 kemiği, baş eşyası alttan) çevrilir →
#    okti_fit_rules biçiminde "item:<id>" (çocuk), "genc:item:<id>", "yetiskin:item:<id>" {size, up, fwd} + C# OktiItem/OktiItemStage.
# 2) test: eşyalar aynı formülle yerleştirilip kemiğe bağlanır (pelerin SkinToBody gibi en yakın gövde köşelerinden deri),
#    deri tulumlar evrenin iskeletine bağlanır; kliplerde (idle, walk, run, jump, squat, tumble) ölçülür:
#      tulum: vücut köşelerinin tulumdan dışarı taşma oranı/derinliği (baş hariç), kenar uzama oranı (en büyük, %99)
#      sert eşya: eşya köşelerinin vücuda girme oranı/derinliği (dinlenmeye göre fark, anim_fit_test.py ile aynı ölçü)
# Kullanım: python -I space_fit.py -- rules <eşya_klasörü> <çıktı.json>
#           python -I space_fit.py -- test <eşya_klasörü> <tulum_klasörü> <kurallar.json> <rapor.json> [evre,…] [klip,…]
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import bpy, bmesh
import numpy as np
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree
import space_kit as K

# oyundaki evre kuralları (CosmeticModels.cs OktiRules / OktiGenc / OktiAdult): kemik, boy, yukarı, ileri, alttan
RULES = {
    'yavru': {'head': ('Head', 0.62, -0.14, 0.0, True), 'back': ('Spine1', 0.36, -0.04, -0.2, False)},
    'genc': {'head': ('Head', 0.465, -0.14, 0.0, True), 'back': ('Spine1', 0.25, -0.04, -0.11, False)},
    'yetiskin': {'head': ('Head', 0.42, -0.14, 0.0, True), 'back': ('Spine1', 0.24, -0.04, -0.11, False)},
}
SLOT = {'hat_astro_helmet': 'head', 'hat_pilot_goggles': 'head', 'hat_star_antenna': 'head',
        'back_astro_pack': 'back', 'back_pilot_jetpack': 'back', 'back_star_cape': 'back'}
EYE = {'yavru': 0.817, 'genc': 0.862, 'yetiskin': 0.889}          # CosmeticModels.OktiEyes (göz hizası, boya oran)
SKIN_BACK = {'back_star_cape'}                                    # oyunda SkinItems'e eklenmeli (sırt kemiklerine deri)
SUITS = ('outfit_astro', 'outfit_pilot', 'outfit_star')


def load_item(item_dir, iid, glass=True):
    objs = []
    for part in (iid, iid + '_glass') if glass else (iid,):
        p = os.path.join(item_dir, part + '.fbx')
        if not os.path.exists(p): continue
        new = K.import_fbx(p)
        tex = os.path.join(item_dir, part + '_basecolor.png'); nrm = os.path.join(item_dir, part + '_normal.png')
        m = item_material(part, tex, nrm if os.path.exists(nrm) else None, glass=part.endswith('_glass'))
        for o in new:
            if o.type == 'MESH':
                o.data.materials.clear(); o.data.materials.append(m); o['part'] = part
                for p_ in o.data.polygons: p_.use_smooth = True
        objs += [o for o in new if o.type == 'MESH']
    bpy.context.view_layer.update()
    return objs


def item_material(name, tex, nrm=None, glass=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(tex)
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.42; b.inputs['Coat Weight'].default_value = 0.25
    if nrm:
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(nrm); n.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8
        nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if glass:
        # önizleme camı: saydam + kenarda yansıma + dokudaki parıltı
        out = nt.nodes['Material Output']; tr = nt.nodes.new('ShaderNodeBsdfTransparent'); gl = nt.nodes.new('ShaderNodeBsdfGlossy')
        gl.inputs['Roughness'].default_value = 0.04; lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.12
        mx = nt.nodes.new('ShaderNodeMixShader'); add = nt.nodes.new('ShaderNodeMath'); add.operation = 'MAXIMUM'
        nt.links.new(lw.outputs['Fresnel'], add.inputs[0]); nt.links.new(t.outputs['Alpha'], add.inputs[1])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.75
        nt.links.new(add.outputs[0], mul.inputs[0])
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 0.6; nt.links.new(t.outputs['Color'], em.inputs['Color'])
        sh = nt.nodes.new('ShaderNodeAddShader'); nt.links.new(gl.outputs[0], sh.inputs[0]); nt.links.new(em.outputs[0], sh.inputs[1])
        nt.links.new(mul.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(sh.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
        m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m


def bounds(objs):
    pts = np.array([tuple(o.matrix_world @ v.co) for o in objs for v in o.data.vertices])
    return pts.min(0), pts.max(0)


# ------------------------------------------------------------------ evre ölçüleri

def head_pts(B):
    m = B.head_shell if B.head_shell.any() else (B.W[:, K.CI['head']] > 0.5)
    return B.P[m]


def head_center(B):
    hp = head_pts(B); return (hp[:, 0].min() + hp[:, 0].max()) / 2, (hp[:, 1].min() + hp[:, 1].max()) / 2


def back_y(B, z, gap):
    """Sırt ortasında (x ≈ omurga) z yüksekliğinde vücut yüzeyinin en arka noktası + gap."""
    g5 = K.group5(B.W); m = (g5[:, 0] > 0.5) & ~B.head_shell
    cx, cy = B.spine_xy(z)
    sel = m & (np.abs(B.P[:, 2] - z) < 0.015 * B.H) & (np.abs(B.P[:, 0] - cx) < 0.06 * B.H)
    if not sel.any(): sel = m & (np.abs(B.P[:, 2] - z) < 0.04 * B.H)
    return float(B.P[sel, 1].max()) + gap


def torso_width(B, z):
    g5 = K.group5(B.W); m = (g5[:, 0] > 0.5) & ~B.head_shell & (np.abs(B.P[:, 2] - z) < 0.015 * B.H)
    cx, _ = B.spine_xy(z)
    return 2 * float(np.abs(B.P[m, 0] - cx).max()) if m.any() else 0.3 * B.H


def rim_back(B):
    cx, cy = B.spine_xy(B.hips_z); return B.rim_at(cx, cy + 1.0)


# ------------------------------------------------------------------ istenen yerleşim (dünya) → oyun sayıları

def desired(B, iid, objs):
    """→ (s ölçek, istenen sınır kutusu merkezi x, y; baş için alt z, sırt için merkez z)."""
    import space_items as SI
    H = B.H
    mn, mx = bounds(objs); c = (mn + mx) / 2
    hp = head_pts(B); cx, cy = head_center(B); top = B.maxz
    if iid == 'hat_astro_helmet':
        rr = np.sqrt((hp[:, 0] - cx) ** 2 + (hp[:, 1] - cy) ** 2)
        s = (rr.max() + 0.006 * H) / (SI.HELM_R - 0.046)
        zr = float(np.mean(B.rim_bottom)) + 0.004 * H
        for _ in range(60):                      # fanus başı tümüyle içine alsın
            Rd = 0.985 * SI.HELM_R * s; Hd = SI.HELM_K * SI.HELM_R * s; z0 = zr + 0.03 * s
            up_ = hp[:, 2] > z0
            e = (rr[up_] / Rd) ** 2 + ((hp[up_, 2] - z0) / Hd) ** 2
            if e.max() <= 0.93: break
            s *= 1.015
        return s, cx, cy, zr + s * mn[2], None
    if iid == 'hat_pilot_goggles':
        ze = EYE[B.stage] * H; zg = ze + 0.5 * (top - ze)
        sl = hp[np.abs(hp[:, 2] - zg) < 0.012 * H]
        r = np.sqrt((sl[:, 0] - cx) ** 2 + (sl[:, 1] - cy) ** 2).max()
        s = (r + 0.004 * H) / SI.GOG_R
        return s, cx, cy + s * c[1], zg + s * mn[2], None
    if iid == 'hat_star_antenna':
        fr = hp[np.abs(hp[:, 1] - cy) < 0.05 * H]
        def xh(z):
            q = fr[np.abs(fr[:, 2] - z) < 0.01 * H]
            return float(np.abs(q[:, 0] - cx).max()) if len(q) else 0.0
        s = 1.0
        for _ in range(30):
            ze = top + 0.004 * H - s * SI.BAND_B
            s = (xh(ze) + 0.006 * H) / SI.BAND_A
        ze = top + 0.004 * H - s * SI.BAND_B
        return s, cx, cy + s * c[1], ze + s * mn[2], None
    # sırt eşyaları
    zt = rim_back(B) - 0.012 * H
    if iid == 'back_star_cape':
        zt = rim_back(B) - 0.006 * H
        wt = torso_width(B, zt - 0.05 * H)
        s = max(0.55 * (zt - B.minz) / 0.62, 0.42 * wt / 0.21)
        yb = back_y(B, zt - 0.02 * H, 0.012 * H)
        # tutturma bandının ortası (model y ≈ 0.035, z ≈ 0) sırta
        cz = zt - s * (0.0 - c[2]); cyw = yb + s * (c[1] - 0.026)
        return s, B.spine_xy(zt)[0], cyw, None, cz
    zm = (zt + B.hips_z) / 2
    wt = torso_width(B, zm)
    if iid == 'back_astro_pack':
        s = min(0.80 * wt / 0.30, 0.95 * (zt - (B.hips_z - 0.03 * H)) / (mx[2] - mn[2]))
    else:
        s = min(0.78 * wt / 0.22, 1.0 * (zt - (B.hips_z - 0.06 * H)) / (mx[2] - mn[2]))
    cz = zt - s * (mx[2] - c[2])
    yb = back_y(B, cz, 0.012 * H)
    cyw = yb + s * (c[1] - mn[1])
    return s, B.spine_xy(cz)[0], cyw, None, cz


def game_numbers(B, iid, objs):
    """İstenen yerleşimi oyunun kural sayılarına çevirir: boy (pet boyuna), yukarı, ileri (+ evre kuralına göre fark)."""
    H = B.H; slot = SLOT[iid]
    bone, rs, ru, rf, bottom = RULES[B.stage][slot]
    s, cxw, cyw, zbot, czw = desired(B, iid, objs)
    mn, mx = bounds(objs)
    w = max(mx[0] - mn[0], mx[1] - mn[1])
    size = s * w / H
    bp = B.bones[bone][0]
    fwd = (bp.y - cyw) / H                         # ön = −Y: hedef y = kemik y − fwd·h
    up = (zbot - B.maxz) / H if slot == 'head' else (czw - bp.z) / H
    side_err = (cxw - bp.x) / H
    return dict(size=round(size, 4), up=round(up, 4), fwd=round(fwd, 4), size_mult=round(size / rs, 4), up_add=round(up - ru, 4),
                fwd_add=round(fwd - rf, 4), scale=round(s, 4), side_err=round(side_err, 4))


def place(B, iid, objs, num):
    """Oyundaki BuildReal ile aynı yerleşim (dinlenme duruşu): ölçek = boy·h / max(gen x, y), baş eşyası alttan, kemiğe bağla."""
    H = B.H; slot = SLOT[iid]; bone = RULES[B.stage][slot][0]
    root = bpy.data.objects.new('it_' + iid, None); bpy.context.scene.collection.objects.link(root)
    for o in objs: o.parent = root
    bpy.context.view_layer.update()
    mn, mx = bounds(objs); w = max(mx[0] - mn[0], mx[1] - mn[1])
    root.scale = V((1, 1, 1)) * (num['size'] * H / w); bpy.context.view_layer.update()
    mn, mx = bounds(objs); c = (mn + mx) / 2
    bp = B.bones[bone][0]
    tgt = V((bp.x, bp.y - num['fwd'] * H, bp.z + num['up'] * H))
    if slot == 'head':
        tgt.z = B.maxz + num['up'] * H
        z = tgt.z - (mn[2] - root.location.z)
    else:
        z = tgt.z - (c[2] - root.location.z)
    root.location = V((tgt.x - (c[0] - root.location.x), tgt.y - (c[1] - root.location.y), z))
    bpy.context.view_layer.update()
    if iid in SKIN_BACK:
        for o in objs:
            mw = o.matrix_world.copy(); o.parent = None; o.data.transform(mw); o.matrix_world.identity()
            K.skin_like_nearest(o, B.body, k=4, torso_only=True)
            am = o.modifiers.new('arm', 'ARMATURE'); am.object = B.arm
            o.parent = B.arm; o.matrix_parent_inverse = B.arm.matrix_world.inverted()
        bpy.data.objects.remove(root)
        return objs
    mw = root.matrix_world.copy()
    root.parent = B.arm; root.parent_type = 'BONE'; root.parent_bone = B.bone_full[bone]
    bpy.context.view_layer.update(); root.matrix_world = mw; bpy.context.view_layer.update()
    return objs


def load_suit(B, suit_dir, oid):
    p = os.path.join(suit_dir, '%s_%s.fbx' % (oid, B.stage))
    new = K.import_fbx(p)
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:
        for m in o.modifiers:
            if m.type == 'ARMATURE': m.object = B.arm
        mw = o.matrix_world.copy(); o.parent = B.arm; o.matrix_world = mw
        base = os.path.join(suit_dir, '%s_%s' % (oid, B.stage))
        o.data.materials.clear(); o.data.materials.append(item_material(oid + B.stage, base + '_basecolor.png', base + '_normal.png'))
        for p_ in o.data.polygons: p_.use_smooth = True
    for o in new:
        if o.type == 'ARMATURE': bpy.data.objects.remove(o)
    return meshes


# ------------------------------------------------------------------ ölçüler

def evaluated(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    pts = np.array([tuple(o.matrix_world @ v.co) for v in me.vertices]); edges = np.array([tuple(ed.vertices) for ed in me.edges])
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(o.matrix_world); bm.normal_update(); t = BVHTree.FromBMesh(bm); bm.free()
    e.to_mesh_clear(); return pts, edges, t


def inside_frac(tree, pts, h):
    n = 0; deep = 0.0
    for p in pts:
        loc, nor, _, d = tree.find_nearest(V(p))
        if loc is None: continue
        if (V(p) - loc).dot(nor) < 0: n += 1; deep = max(deep, d)
    return n / max(1, len(pts)), deep / h


def poke(B, body_pts, suit_tree, mask):
    """Vücut köşelerinin tulumdan dışarı taşması (baş hariç): oran ve en derin (boya oran)."""
    n = 0; deep = 0.0; idx = np.nonzero(mask)[0]
    for i in idx:
        p = V(body_pts[i]); loc, nor, _, d = suit_tree.find_nearest(p)
        if loc is None: continue
        s = (p - loc).dot(nor)
        if s > 0.001 * B.H: n += 1; deep = max(deep, s)
    return n / max(1, len(idx)), deep / B.H


def set_clip(B, clip):
    p = os.path.join(B.dir, '%s@%s.fbx' % (B.name, clip))
    if not os.path.exists(p): return None
    objs = K.import_fbx(p); src = next((o for o in objs if o.type == 'ARMATURE'), None)
    act = src.animation_data.action if src and src.animation_data else None
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)
    if act is None: return None
    B.arm.animation_data_create(); B.arm.animation_data.action = act
    return act


FRAMES = {'run': None, 'walk': None, 'idle': [1, 20, 40, 60], 'jump': list(range(10, 32, 3)), 'squat': [1, 9, 15, 19, 21, 23, 29, 37, 45],
          'tumble': None, 'happy': None, 'wave': None}


def frames_for(clip, act):
    f0, f1 = [int(x) for x in act.frame_range]
    fr = FRAMES.get(clip)
    if fr: return [f for f in fr if f0 <= f <= f1]
    return sorted(set(int(round(f0 + (f1 - f0) * i / 7.0)) for i in range(8)))


def run_test(item_dir, suit_dir, rules, stages, clips):
    rep = {}
    for st in stages:
        K.reset_scene(); B = K.Body(st); H = B.H
        rep[st] = {}
        nonhead = ~B.head_shell & (B.W[:, K.CI['head']] < 0.5)
        # tulumlar (ayrı ayrı)
        for oid in SUITS:
            if not os.path.exists(os.path.join(suit_dir, '%s_%s.fbx' % (oid, st))): continue
            meshes = load_suit(B, suit_dir, oid)
            for pb in B.arm.pose.bones: pb.matrix_basis.identity()
            if B.arm.animation_data: B.arm.animation_data.action = None
            bpy.context.view_layer.update()
            rest_pts, edges, tree = evaluated(meshes[0])
            rest_len = np.linalg.norm(rest_pts[edges[:, 0]] - rest_pts[edges[:, 1]], axis=1) + 1e-9
            bp, _, _ = evaluated(B.body)
            base_poke = poke(B, bp, tree, nonhead)
            r = {'rest_poke': [round(base_poke[0], 4), round(base_poke[1], 4)], 'clips': {}}
            for clip in clips:
                act = set_clip(B, clip)
                if act is None: continue
                worst = [0, 0, 0, 0, 0]
                for f in frames_for(clip, act):
                    bpy.context.scene.frame_set(f)
                    pts, _, tree = evaluated(meshes[0]); bp, _, _ = evaluated(B.body)
                    pk = poke(B, bp, tree, nonhead)
                    ln = np.linalg.norm(pts[edges[:, 0]] - pts[edges[:, 1]], axis=1) / rest_len
                    if pk[1] > worst[1]: worst[0], worst[1], worst[2] = round(pk[0], 4), round(pk[1], 4), f
                    worst[3] = max(worst[3], round(float(ln.max()), 3)); worst[4] = max(worst[4], round(float(np.percentile(ln, 99)), 3))
                r['clips'][clip] = {'poke_frac': worst[0], 'poke_deep_h': worst[1], 'frame': worst[2], 'stretch_max': worst[3], 'stretch_p99': worst[4]}
            rep[st][oid] = r
            for o in meshes: bpy.data.objects.remove(o)
            if B.arm.animation_data: B.arm.animation_data.action = None
        # sert eşyalar (hepsi birlikte takılı; her biri ayrı ölçülür)
        for pb in B.arm.pose.bones: pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        placed = {}
        for iid in SLOT:
            objs = load_item(item_dir, iid, glass=False)
            if not objs: continue
            num = rules[st][iid]
            placed[iid] = place(B, iid, objs, num)
        bp_tree = B.body_bvh()
        base = {iid: inside_frac(bp_tree, np.concatenate([evaluated(o)[0] for o in objs]), H) for iid, objs in placed.items()}
        for iid in placed: rep[st][iid] = {'rest_inside': [round(base[iid][0], 4), round(base[iid][1], 4)], 'clips': {}}
        for clip in clips:
            act = set_clip(B, clip)
            if act is None: continue
            worst = {}
            for f in frames_for(clip, act):
                bpy.context.scene.frame_set(f)
                tree = B.body_bvh()
                for iid, objs in placed.items():
                    pts = np.concatenate([evaluated(o)[0] for o in objs])
                    fr, dp = inside_frac(tree, pts, H)
                    d = (round(fr - base[iid][0], 4), round(dp - base[iid][1], 4), f)
                    if iid not in worst or d[1] > worst[iid][1]: worst[iid] = d
            for iid, d in worst.items():
                rep[st][iid]['clips'][clip] = {'inside_frac_delta': d[0], 'deep_delta_h': d[1], 'frame': d[2]}
        print('TEST', st, flush=True)
    return rep


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:]
    if a[0] == 'rules':
        item_dir, out = a[1], a[2]
        res = {}
        for st in K.STAGES:
            K.reset_scene(); B = K.Body(st); res[st] = {}
            for iid in SLOT:
                objs = load_item(item_dir, iid, glass=False)
                res[st][iid] = game_numbers(B, iid, objs)
                for o in objs: bpy.data.objects.remove(o)
            print(st, json.dumps(res[st]), flush=True)
        json.dump(res, open(out, 'w'), indent=1)
    elif a[0] == 'test':
        item_dir, suit_dir, rules_p, out = a[1:5]
        stages = a[5].split(',') if len(a) > 5 else list(K.STAGES)
        clips = a[6].split(',') if len(a) > 6 else ['idle', 'walk', 'run', 'jump', 'squat', 'tumble']
        rep = run_test(item_dir, suit_dir, json.load(open(rules_p)), stages, clips)
        json.dump(rep, open(out, 'w'), indent=1, ensure_ascii=False)
        print('BITTI', out)
