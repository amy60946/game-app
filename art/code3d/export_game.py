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
    # yapılar (bölge başına 1). bld/<ad>.py (24 Ekim 2026): taslağın tam ağından pişer (renk + AO + normal; bld/bld_kit.py),
    # eskitme katmanları bld/ada_eskitme.py; bütçe yalnız üst sınır raporu (küresel sadeleştirme yok)
    'b_home': ('house_cottage.py', 'c_house', 9000, 1024),
    'b_shop': ('assets_town.py', 'c_shop', 10000, 1024),
    'b_pier': ('bld/b_pier.py', 'b_pier', 13000, 1024),
    'b_lighthouse': ('bld/b_lighthouse.py', 'b_lighthouse', 12000, 1024),
    'b_task_board': ('assets_town.py', 'c_board', 4500, 1024),
    'b_garden': ('bld/b_garden.py', 'b_garden', 14000, 1024),
    'b_surf': ('bld/b_surf.py', 'b_surf', 12000, 1024),
    'b_swim': ('bld/b_swim.py', 'b_swim', 12000, 1024),   # v6 adada koy p_pool ile kurulur; bu yalnız eski ada
    'b_game_hut': ('bld/b_game_hut.py', 'b_game_hut', 15000, 1024),
    'b_festival': ('bld/b_festival.py', 'b_festival', 15000, 1024),
    'b_cave': ('assets_town.py', 'c_cave', 6000, 1024),
    'b_mountain': ('assets_town.py', 'c_mountain', 6000, 1024),
    'b_ski_hill': ('assets_town.py', 'c_ski', 7000, 1024),
    'b_hut': ('assets_town.py', 'c_hut', 6000, 1024),
    'p_site': ('assets_town.py', 'c_site', 3500, 512),
    'island_chunk': ('assets_town.py', 'c_chunk', 5000, 1024),
    # süsler (adada çok sayıda)
    # palmiye v2 (24 Ekim 2026): ayrıntılı taslaktan pişmiş renk + AO + normal haritası (palm_v2.py, v6/proxy_bake); eski c_palm yedek
    'palm': ('palm_v2.py', 'c_palm2', 3600, 1024),
    'p_tree': ('assets_town.py', 'c_tree', 3200, 512),
    'p_rock': ('assets_v3.py', 'c_rock', 1200, 512),
    'p_bush': ('assets_v3.py', 'c_bush', 1800, 512),
    'p_flowers': ('assets_v3.py', 'c_flowers', 1100, 512),
    'p_fence': ('assets_town.py', 'c_fence', 2500, 512),
    'p_lantern': ('assets_town.py', 'c_lantern', 3600, 512),   # 24 Ekim 2026: 1800'de cam önü çubukları, kelepçe ve kanca eriyordu
    'p_sign': ('assets_town.py', 'c_sign', 2000, 512),
    'p_crates': ('assets_town.py', 'c_crates', 4000, 512),
    'p_boat': ('assets_town.py', 'c_boat', 3500, 512),
    'p_log': ('assets_town.py', 'c_log', 1600, 512),
    'p_coconut': ('assets_town.py', 'c_coconut', 1200, 512),   # yerde hindistan cevizi (GB17, GatherKind.Coconut)
}
# ev eşyaları ve süsler (Resources/Items; kıyafetler ve petler Meshy'de kalır — iskelet/soket bağlı)
ITEMS = {
    'home_bed': ('assets_items.py', 'i_bed', 3500, 512), 'home_bookshelf': ('assets_items.py', 'i_bookshelf', 3500, 512),
    'home_lamp': ('assets_items.py', 'i_lamp', 2500, 512), 'home_rug': ('assets_items.py', 'i_rug', 3500, 512),
    'home_aquarium': ('assets_items.py', 'i_aquarium', 3500, 512), 'decor_lanterns': ('assets_items.py', 'i_lanterns', 3000, 512),
    'decor_palm': ('assets_items.py', 'i_palm', 1600, 512), 'decor_sandcastle': ('assets_items.py', 'i_sandcastle', 3500, 512),
    'decor_umbrella': ('assets_items.py', 'i_umbrella', 3000, 512),
}
# komik giyilebilir eşyalar (kullanıcı, 23 Ekim 2026: F1–F17; kodla yapılanlar). "<id>_spin" = aynı klasörde dönen parça
# (pervane, balıklar): ana parçayla aynı koordinatta dışa aktarılır, oyun kendi sınır merkezinden dikey eksende döndürür.
WEAR = {
    'hat_propeller': ('assets_wear_a.py', 'w_hat_propeller', 3000, 512), 'hat_propeller_spin': ('assets_wear_a.py', 'w_hat_propeller_spin', 800, 256),
    'hat_cake': ('assets_wear_a.py', 'w_hat_cake', 3500, 512), 'hat_watermelon': ('assets_wear_a.py', 'w_hat_watermelon', 2500, 512),
    'hat_crown_tilt': ('assets_wear_a.py', 'w_hat_crown_tilt', 2500, 512), 'hat_bucket': ('assets_wear_a.py', 'w_hat_bucket', 3000, 512),
    'hat_fishbowl': ('assets_wear_b.py', 'w_hat_fishbowl', 3500, 512), 'hat_fishbowl_spin': ('assets_wear_b.py', 'w_hat_fishbowl_spin', 1200, 256),
    'glasses_heart': ('assets_wear_b.py', 'w_glasses_heart', 2000, 512), 'glasses_nose': ('assets_wear_b.py', 'w_glasses_nose', 2500, 512),
    'glasses_snorkel': ('assets_wear_b.py', 'w_glasses_snorkel', 2500, 512), 'mask_hero': ('assets_wear_b.py', 'w_mask_hero', 1500, 512),
    'socks_arm': ('assets_wear_c.py', 'w_socks_arm', 1500, 512), 'pompom': ('assets_wear_c.py', 'w_pompom', 3000, 512),
    'outfit_hula': ('assets_wear_c.py', 'w_outfit_hula', 4000, 512),
}
WEAR['base_bottom'] = ('assets_base.py', 'w_base_bottom', 2500, 512)   # Okti'nin temel şortu (çıkarılamaz, CosmeticModels.Base)
ITEMS.update(WEAR)
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
    spin = item and name.endswith('_spin')
    dst = os.path.join(ITEMS_DIR if item else ENV, name[:-5] if spin else name)
    if os.path.isdir(dst) and not spin:
        for f in glob.glob(os.path.join(dst, '*')):
            if not os.path.basename(f).startswith(name + '_spin'): os.remove(f)   # dönen parça ayrı dışa aktarılır, silinmesin
    os.makedirs(dst, exist_ok=True)
    shutil.copy(os.path.join(out, builder + '.fbx'), os.path.join(dst, name + '.fbx'))
    shutil.copy(os.path.join(out, builder + '_basecolor.png'), os.path.join(dst, name + '_basecolor.png'))
    nrm = os.path.join(out, builder + '_normal.png')   # taslaktan pişirilen varlıklar (palm_v2) normal haritası da üretir
    if os.path.exists(nrm): shutil.copy(nrm, os.path.join(dst, name + '_normal.png'))
    print('OK', name, log[-1] if log else '', flush=True)
    return True

if __name__ == '__main__':
    names = sys.argv[1:] or list(ASSETS) + [n for n in ITEMS if n not in WEAR]   # giyilebilirler adla dışa aktarılır
    if not sys.argv[1:]:
        for n in REMOVE:
            d = os.path.join(ENV, n)
            if os.path.isdir(d): shutil.rmtree(d)
            if os.path.exists(d + '.meta'): os.remove(d + '.meta')
    ok = all([export(n) for n in names])
    sys.exit(0 if ok else 1)
