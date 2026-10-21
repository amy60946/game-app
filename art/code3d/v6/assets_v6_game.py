# Ada v6 süsleri → oyun modelleri (22 Ekim 2026; onaylı taslağın aynı kodu, oyun bütçesiyle).
# Her model taslaktaki örnek ölçüsünde (ör. çam 1 m boyunda kurulur, yerleşim ölçeği 5–12) → bake_game.py'deki "s" doğrudan ölçektir.
# Dışa aktarma: kit.export_baked_fbx (üçgen bütçesi POFI_TARGET + pişirilmiş renk/AO) → Resources/Env/<ad>/<ad>.fbx + _basecolor.png
#   /tmp/claude-0/bpyenv/bin/python -I assets_v6_game.py -- [ad ...]
import sys, os, math, random, shutil, glob, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
PY = os.environ.get('POFI_BPY', '/tmp/claude-0/bpyenv/bin/python')
STAGE = os.environ.get('POFI_STAGE', '/tmp/pofi_v6_export')

# oyun adı: (yapıcı, üçgen bütçesi, doku boyu)
ASSETS = {
    't_round0': ('round:0', 1400, 512), 't_round1': ('round:1', 1400, 512), 't_round2': ('round:2', 1400, 512), 't_round3': ('round:3', 1400, 512),
    't_cypress': ('cypress', 800, 512), 't_birch': ('birch', 1200, 512),
    't_pine0': ('pine:0', 1100, 512), 't_pine1': ('pine:1', 1100, 512), 't_pine2': ('pine:2', 1100, 512), 't_pine_snow': ('pine_snow', 1100, 512),
    't_palm_tall0': ('palm2:0', 1500, 512), 't_palm_tall1': ('palm2:1', 1500, 512), 't_palm_tall2': ('palm2:2', 1500, 512),
    't_bush': ('bush', 380, 256),
    'r_boulder': ('boulder', 350, 256), 'r_boulder_b': ('boulderB', 350, 256), 'r_pebble': ('pebW', 250, 256),
    'p_campfire': ('campfire', 2600, 512), 'p_log_v6': ('log', 700, 256), 'p_stump_v6': ('stump', 600, 256),
    'p_driftwood': ('driftwood', 1400, 512), 'p_starfish': ('starfish', 300, 128), 'p_crab': ('crab', 700, 256),
    'p_pool': ('pool', 7000, 1024), 'b_temple': ('temple', 32000, 2048),
    'p_trail_pole': ('pole', 120, 128), 'p_snow_lump': ('snowlump', 160, 128),
}

def build(spec):
    import bpy
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
    import kit_v6 as K, kit2_v6 as K2, kit3_v6 as K3
    col = bpy.context.scene.collection
    kind, _, k = spec.partition(':'); k = int(k or 0)
    # oyun tacı: yaprak kartları az ve iri, iç kabuk dolu (bütçeye inince taç dağılmasın; boyalı topak görünümü korunur)
    if kind in ('round', 'birch', 'bush') and not getattr(K, '_game_crown', False):
        orig = K.crown
        def game_crown(*a, **kw):
            kw['density'] = kw.get('density', 320) * 0.05; kw['leaf'] = kw.get('leaf', 0.35) * 2.4; kw['shell'] = 0.98
            return orig(*a, **kw)
        K.crown = game_crown; K._game_crown = True
    bark = K.bark_mat()
    if kind == 'round':
        pals = [K.PAL_BROAD, K.PAL_BROAD2, K.PAL_BROAD3, K.PAL_BROAD4]
        K.round_tree('rt', 1.0, 10 + k, col=col, palette=pals[k], spread=0.85 + 0.12 * k, fol=K.foliage_mat('fol_broad'), bark=bark, clumps=8 + k)
    elif kind == 'cypress': K.cypress('cy', 1.0, 30, col=col, fol=K.foliage_mat('fol_cyp', translucent=0.15), bark=bark)
    elif kind == 'birch': K.birch('bi', 1.0, 40, col=col, fol=K.foliage_mat('fol_broad'))
    elif kind == 'pine': K.pine('pi', 1.0, 50 + k, col=col, fol=K.foliage_mat('fol_pine', translucent=0.18), bark=bark, palette=(K.PAL_PINE, K.PAL_PINE2, K.PAL_PINE3)[k])
    elif kind == 'pine_snow': K.pine('ps', 1.0, 55, col=col, fol=K.foliage_mat('fol_pine', translucent=0.18), bark=bark, palette=K.PAL_PINE_SNOW)
    elif kind == 'palm2': K2.palm('pm', (9.5, 13.0, 16.0)[k], 300 + k, col=col, thick=(1.0, 0.85, 0.8)[k])
    elif kind == 'bush': K.bush('bu', 1.0, 60, col=col, fol=K.foliage_mat('fol_broad'), leaf=0.09)
    elif kind == 'boulder': K.boulder('bd', (1.0, 0.9, 0.8), 70, mat=K.rock_mat('rockA', base='#b3a8a8', dark='#7f7386', light='#d4c9c0', moss_amt=0.18), col=col)
    elif kind == 'boulderB': K.boulder('bb', (1.0, 0.85, 0.85), 80, mat=K.rock_mat('rockB', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.28), col=col)
    elif kind == 'pebW': K.boulder('bw', (1.0, 0.85, 0.7), 90, cuts=4, mat=K.rock_mat('rockW', base='#d6d0cc', dark='#a49ca0', light='#ece8e2', moss_amt=0.0, cracks=0.2), col=col, bevel=0.25, top_flat=0.0)
    elif kind == 'campfire':
        K2.campfire_v2('cf', col=col, seed=4, scale=1.0)
        # alevler oyunda canlı (Runtime/World/Campfire): pişirilen modelde yalnız odun + taş + kor
        for o in list(col.objects):
            if any(m and m.name.endswith('_fire') for m in getattr(o.data, 'materials', [])) or o.type == 'LIGHT':
                bpy.data.objects.remove(o)
    elif kind == 'log': K2.log_v2('lg', 3.0, 0.34, 20, col=col)
    elif kind == 'stump': K2.stump_v2('st', 0.42, 0.55, 30, col=col)
    elif kind == 'driftwood': K2.driftwood('dw', 5.8, 0.62, 5, col=col)
    elif kind == 'starfish': K2.starfish('sf', 0.15, 51, col=col)
    elif kind == 'crab': K2.crab('cr', 0.22, 60, col=col)
    elif kind == 'pool':
        rmA = K.rock_mat('rockA', base='#b3a8a8', dark='#7f7386', light='#d4c9c0', moss_amt=0.18)
        rmB = K.rock_mat('rockB', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.28)
        K2.swim_pool('pool', col=col, seed=3, mats=(rmA, rmB))
    elif kind == 'temple':
        K3.temple(col)
        for o in list(bpy.context.scene.objects):
            if o.type == 'LIGHT': bpy.data.objects.remove(o)
    elif kind == 'pole':
        v, f = K.tube_data([(0, 0, 0), (0, 0, 1.35)], [0.045, 0.04], 6, 0); K.mesh_obj('pole', v, f, K.bark_mat('pole_bark', base='#7a5536', dark='#4a3222', light='#a67c55'), col=col)
        cap = bpy.data.materials.new('pole_cap'); cap.use_nodes = True; cap.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#f07a1a') + (1,)
        v, f = K.tube_data([(0, 0, 1.35), (0, 0, 1.6)], [0.06, 0.06], 6, 0); K.mesh_obj('cap', v, f, cap, col=col)
    elif kind == 'snowlump': K2.snow_lump('sl', 1.0, 70, col=col, mat=K2.snow_mat())
    else: raise SystemExit('bilinmeyen ' + spec)

def child(name, out):
    """bpy alt süreci: tek model kur + pişir + dışa aktar."""
    import bpy
    sys.path.insert(0, os.path.join(HERE, '..'))
    import kit as KT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build(ASSETS[name][0])
    # örnek koleksiyonları (ağaç içindeki tekrar eden parçalar) gerçek ağa çevrilir
    bpy.ops.object.select_all(action='SELECT')
    try: bpy.ops.object.duplicates_make_real()
    except Exception: pass
    for o in list(bpy.context.scene.objects):
        if o.type == 'CURVE':
            bpy.context.view_layer.objects.active = o; o.select_set(True)
            try: bpy.ops.object.convert(target='MESH')
            except Exception: pass
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    tris = KT.export_baked_fbx(os.path.join(out, name), objs, size=ASSETS[name][2])
    print('üçgen', tris, flush=True)

def export(name):
    out = os.path.join(STAGE, name); os.makedirs(out, exist_ok=True)
    _, target, tex = ASSETS[name]
    env = dict(os.environ, POFI_TARGET=str(target), POFI_TEX=str(tex))
    r = subprocess.run([PY, '-I', os.path.abspath(__file__), '--child', name, out], env=env, capture_output=True, text=True, cwd=HERE)
    fbx = os.path.join(out, name + '.fbx')
    if r.returncode != 0 or not os.path.exists(fbx):
        print('HATA', name, r.stdout[-1200:], r.stderr[-1500:], flush=True); return False
    dst = os.path.join(ENV, name)
    if os.path.isdir(dst):
        for f in glob.glob(os.path.join(dst, '*')): os.remove(f)
    os.makedirs(dst, exist_ok=True)
    shutil.copy(fbx, os.path.join(dst, name + '.fbx'))
    shutil.copy(os.path.join(out, name + '_basecolor.png'), os.path.join(dst, name + '_basecolor.png'))
    print('OK', name, [l for l in r.stdout.splitlines() if 'üçgen' in l][-1:], flush=True)
    return True

if __name__ == '__main__':
    if '--child' in sys.argv:
        i = sys.argv.index('--child'); child(sys.argv[i + 1], sys.argv[i + 2])
    else:
        args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        names = args or list(ASSETS)
        bad = [n for n in names if not export(n)]
        print('bitti', len(names) - len(bad), 'hatalı:', bad)
