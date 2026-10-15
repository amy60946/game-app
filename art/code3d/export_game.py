# Oyun sürümü dışa aktarma (kullanıcı onayı 15 Ekim 2026: kodla yenilenen tüm modeller oyundakilerin yerine geçer).
# Her varlık: aynı kod → üçgen bütçesine indirgenmiş tek mesh (POFI_TARGET) → pişirilmiş renk+AO dokusu (POFI_TEX) →
# Assets/_Pofi/Resources/Env/<oyun_adı>/<oyun_adı>.fbx + _basecolor.png (eski Meshy dosyaları, normal haritaları dahil, silinir).
# Kullanım: python3 export_game.py [ad ...]     (bpy ortamı: /tmp/claude-0/bpyenv/bin/python)
import os, sys, subprocess, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.normpath(os.path.join(HERE, '../../Assets/_Pofi/Resources/Env'))
PY = os.environ.get('POFI_BPY', '/tmp/claude-0/bpyenv/bin/python')
STAGE = os.environ.get('POFI_STAGE', '/tmp/pofi_game_export')

# oyun adı: (betik, yapıcı, üçgen bütçesi, doku boyu). Bütçe: iPhone'da tüm ada ~0.5 M üçgen altında kalsın.
ASSETS = {
    # yapılar (bölge başına 1)
    'b_home': ('house_cottage.py', 'c_house', 9000, 1024),
    'b_shop': ('assets_town.py', 'c_shop', 10000, 1024),
    'b_pier': ('assets_town.py', 'c_pier', 7000, 1024),
    'b_lighthouse': ('assets_town.py', 'c_lighthouse', 6000, 1024),
    'b_task_board': ('assets_town.py', 'c_board', 4500, 1024),
    'b_garden': ('assets_town.py', 'c_garden', 8000, 1024),
    'b_surf': ('assets_town.py', 'c_surf', 7000, 1024),
    'b_swim': ('assets_town.py', 'c_swim', 6500, 1024),
    'b_game_hut': ('assets_town.py', 'c_game_hut', 8000, 1024),
    'b_festival': ('assets_town.py', 'c_festival', 6500, 1024),
    'b_cave': ('assets_town.py', 'c_cave', 6000, 1024),
    'b_mountain': ('assets_town.py', 'c_mountain', 6000, 1024),
    'b_ski_hill': ('assets_town.py', 'c_ski', 7000, 1024),
    'b_hut': ('assets_town.py', 'c_hut', 6000, 1024),
    'p_site': ('assets_town.py', 'c_site', 3500, 512),
    'island_chunk': ('assets_town.py', 'c_chunk', 5000, 1024),
    # süsler (adada çok sayıda)
    'palm': ('assets_v3.py', 'c_palm', 2600, 512),
    'p_tree': ('assets_town.py', 'c_tree', 3200, 512),
    'p_rock': ('assets_v3.py', 'c_rock', 1200, 512),
    'p_bush': ('assets_v3.py', 'c_bush', 1800, 512),
    'p_flowers': ('assets_v3.py', 'c_flowers', 1100, 512),
    'p_fence': ('assets_town.py', 'c_fence', 2500, 512),
    'p_lantern': ('assets_town.py', 'c_lantern', 1800, 512),
    'p_sign': ('assets_town.py', 'c_sign', 2000, 512),
    'p_crates': ('assets_town.py', 'c_crates', 4000, 512),
    'p_boat': ('assets_town.py', 'c_boat', 3500, 512),
    'p_log': ('assets_town.py', 'c_log', 1600, 512),
}
# ev eşyaları ve süsler (Resources/Items; kıyafetler ve petler Meshy'de kalır — iskelet/soket bağlı)
ITEMS = {
    'home_bed': ('assets_items.py', 'i_bed', 3500, 512), 'home_bookshelf': ('assets_items.py', 'i_bookshelf', 3500, 512),
    'home_lamp': ('assets_items.py', 'i_lamp', 2500, 512), 'home_rug': ('assets_items.py', 'i_rug', 3500, 512),
    'home_aquarium': ('assets_items.py', 'i_aquarium', 3500, 512), 'decor_lanterns': ('assets_items.py', 'i_lanterns', 3000, 512),
    'decor_palm': ('assets_items.py', 'i_palm', 1600, 512), 'decor_sandcastle': ('assets_items.py', 'i_sandcastle', 3500, 512),
    'decor_umbrella': ('assets_items.py', 'i_umbrella', 3000, 512),
}
ITEMS_DIR = os.path.normpath(os.path.join(HERE, '../../Assets/_Pofi/Resources/Items'))
REMOVE = ['t_beach', 't_cliff', 't_grass', 'g_log', 'g_site', 'g_hut']   # artık kullanılmayan eski varlıklar

def export(name):
    item = name in ITEMS
    script, builder, target, tex = ITEMS[name] if item else ASSETS[name]
    out = os.path.join(STAGE, name); os.makedirs(out, exist_ok=True)
    env = dict(os.environ, POFI_TARGET=str(target), POFI_TEX=str(tex))
    args = [PY, '-I', os.path.join(HERE, script), '--', out] + (['v3'] if script == 'house_cottage.py' else [builder])
    r = subprocess.run(args, env=env, capture_output=True, text=True, cwd=HERE)
    log = [l for l in r.stdout.splitlines() if 'üçgen' in l]
    if r.returncode != 0 or not os.path.exists(os.path.join(out, builder + '.fbx')):
        print('HATA', name, r.stdout[-1500:], r.stderr[-1500:], flush=True); return False
    dst = os.path.join(ITEMS_DIR if item else ENV, name)
    if os.path.isdir(dst):
        for f in glob.glob(os.path.join(dst, '*')): os.remove(f)
    os.makedirs(dst, exist_ok=True)
    shutil.copy(os.path.join(out, builder + '.fbx'), os.path.join(dst, name + '.fbx'))
    shutil.copy(os.path.join(out, builder + '_basecolor.png'), os.path.join(dst, name + '_basecolor.png'))
    print('OK', name, log[-1] if log else '', flush=True)
    return True

if __name__ == '__main__':
    names = sys.argv[1:] or list(ASSETS) + list(ITEMS)
    if not sys.argv[1:]:
        for n in REMOVE:
            d = os.path.join(ENV, n)
            if os.path.isdir(d): shutil.rmtree(d)
            if os.path.exists(d + '.meta'): os.remove(d + '.meta')
    ok = all([export(n) for n in names])
    sys.exit(0 if ok else 1)
