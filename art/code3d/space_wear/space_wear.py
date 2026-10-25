# Uzay kıyafetleri — tek giriş (25 Ekim 2026). Bpy ortamı: /tmp/claude-0/bpyenv/bin/python -I space_wear.py -- <komut> …
#   suits   <çıktı> [kıyafet,…] [evre,…]   deri tulumlar (evre başına FBX + renk/normal dokusu) — space_kit.make_suit
#   items   <çıktı> [id,…]                 sert aksesuarlar (pişmiş renk × AO + normal) — space_items.py
#   rules   <çıktı>                        evre başına yerleşim sayıları (rules.json) — space_fit.py
#   test    <çıktı>                        kıyafet × hareket ölçüsü (fit_report.json) — space_fit.py
#   preview <çıktı> <önizleme_klasörü>      onay görselleri (yetişkin ön/arka/koşu/zıplama/çömelme + çocuk/genç paftası)
#   icons   <çıktı> <simge_klasörü>         256² şeffaf simgeler (wear_icon.py havası)
#   install <çıktı>                        oyun klasörlerine kopyala (Assets/_Pofi/Resources/Items/<id>/…)
#   notes   <çıktı>                        okti_fit_rules girdileri + CosmeticModels (OktiItem/OktiItemStage) satırları
# <çıktı> = ara klasör (ör. scratchpad/kiyafet/export): suits/, items/, rules.json burada.
import os, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
PY = os.environ.get('POFI_BPY', '/tmp/claude-0/bpyenv/bin/python')
OUTFITS = {'outfit_astro': ('hat_astro_helmet', 'back_astro_pack'), 'outfit_pilot': ('hat_pilot_goggles', 'back_pilot_jetpack'),
           'outfit_star': ('hat_star_antenna', 'back_star_cape')}
STAGES = ('yavru', 'genc', 'yetiskin')
RES = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'Assets', '_Pofi', 'Resources'))


def cmd_suits(out, outfits=None, stages=None):
    import importlib
    import space_kit as K
    info = {}
    for oid in outfits or OUTFITS:
        O = importlib.import_module(oid)
        for st in stages or STAGES:
            info['%s_%s' % (oid, st)] = K.make_suit(st, O, os.path.join(out, 'suits'), size=1024)
    p = os.path.join(out, 'suits', 'info.json')
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(info); json.dump(old, open(p, 'w'), indent=1)


def static_fallback(out):
    """Kemiksiz yetişkin tulumu (Items/<id>/<id>.fbx): RealAssets.HasItem + dükkân simgesi. Doku yetişkininkinin kopyası."""
    import space_kit as K, bpy
    for oid in OUTFITS:
        K.reset_scene()
        new = K.import_fbx(os.path.join(out, 'suits', '%s_yetiskin.fbx' % oid))
        ob = next(o for o in new if o.type == 'MESH')
        for m in list(ob.modifiers): ob.modifiers.remove(m)
        mw = ob.matrix_world.copy(); ob.parent = None; ob.matrix_world = mw
        K.export_static_fbx(os.path.join(out, 'suits', '%s.fbx' % oid), ob)


def install(out):
    done = []
    for oid, (hat, back) in OUTFITS.items():
        d = os.path.join(RES, 'Items', oid); os.makedirs(d, exist_ok=True)
        for st in STAGES:
            for suf in ('.fbx', '_basecolor.png', '_normal.png'):
                src = os.path.join(out, 'suits', '%s_%s%s' % (oid, st, suf))
                dst = os.path.join(d, 'skin_%s%s' % (st, suf)); shutil.copy(src, dst); done.append(dst)
        for src, dst in ((os.path.join(out, 'suits', oid + '.fbx'), os.path.join(d, oid + '.fbx')),
                         (os.path.join(out, 'suits', '%s_yetiskin_basecolor.png' % oid), os.path.join(d, oid + '_basecolor.png')),
                         (os.path.join(out, 'suits', '%s_yetiskin_normal.png' % oid), os.path.join(d, oid + '_normal.png'))):
            shutil.copy(src, dst); done.append(dst)
        for iid in (hat, back):
            d = os.path.join(RES, 'Items', iid); os.makedirs(d, exist_ok=True)
            for f in sorted(os.listdir(os.path.join(out, 'items'))):
                if f.startswith(iid + '.') or f.startswith(iid + '_'):
                    shutil.copy(os.path.join(out, 'items', f), os.path.join(d, f)); done.append(os.path.join(d, f))
    for p in done: print('KOPYA', os.path.relpath(p, os.path.join(RES, '..', '..', '..')))


def notes(out):
    """rules.json → okti_fit_rules.json girdileri (çocuk = "item:<id>", genç/yetişkin evreye özel) + C# OktiItem / OktiItemStage satırları."""
    r = json.load(open(os.path.join(out, 'rules.json')))
    fit = {}; cs_item = []; cs_stage = []
    for iid in r['yavru']:
        for st in STAGES:
            v = r[st][iid]
            key = ('item:' if st == 'yavru' else st + ':item:') + iid
            fit[key] = {'size': v['size_mult'], 'up': v['up_add'], 'fwd': v['fwd_add']}
            line = '["%s%s"] = new Vector3(%.4ff, %.4ff, %.4ff),' % ('' if st == 'yavru' else st + ':', iid, v['size_mult'], v['up_add'], v['fwd_add'])
            (cs_item if st == 'yavru' else cs_stage).append(line)
    json.dump(fit, open(os.path.join(out, 'okti_fit_rules_space.json'), 'w'), indent=1)
    open(os.path.join(out, 'cosmetic_models_space.txt'), 'w').write('// OktiItem\n' + '\n'.join(cs_item) + '\n// OktiItemStage\n' + '\n'.join(cs_stage) + '\n')
    print(json.dumps(fit, indent=1)); print('\n'.join(cs_item + cs_stage))


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    cmd, out = a[0], a[1]
    if cmd == 'suits':
        cmd_suits(out, a[2].split(',') if len(a) > 2 and a[2] else None, a[3].split(',') if len(a) > 3 else None)
        static_fallback(out)
    elif cmd == 'items':
        import space_items as SI
        for iid in (a[2].split(',') if len(a) > 2 else SI.BUILDERS): SI.export_item(iid, os.path.join(out, 'items'))
    elif cmd == 'rules':
        subprocess.run([PY, '-I', os.path.join(HERE, 'space_fit.py'), '--', 'rules', os.path.join(out, 'items'), os.path.join(out, 'rules.json')], check=True)
    elif cmd == 'test':
        subprocess.run([PY, '-I', os.path.join(HERE, 'space_fit.py'), '--', 'test', os.path.join(out, 'items'), os.path.join(out, 'suits'),
                        os.path.join(out, 'rules.json'), os.path.join(out, 'fit_report.json')] + a[2:], check=True)
    elif cmd == 'preview':
        subprocess.run([PY, '-I', os.path.join(HERE, 'space_preview.py'), '--', out, a[2]] + a[3:], check=True)
    elif cmd == 'icons':
        subprocess.run([PY, '-I', os.path.join(HERE, 'space_preview.py'), '--', out, a[2], 'icons'], check=True)
    elif cmd == 'install':
        install(out)
    elif cmd == 'notes':
        notes(out)
