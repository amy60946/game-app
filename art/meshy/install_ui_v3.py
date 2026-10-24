#!/usr/bin/env python3
"""v3 simge ve arayüz parçalarını oyuna kurar (19 Ekim 2026, kullanıcı onayı).
Meshy sayfaları (out/ui_v3_*) → hücrelere bölünür, beyaz arka plan saydamlaştırılır →
  Resources/Icons/<ad>.png (256 kare, eski adlarla: kod değişmeden yenilenir)
  Resources/UI/<parça>.png (çubuk, düğme, kart, şerit, yuvarlak düğme, tahta, kapat; 9 dilimli kullanılır)
Kullanım: python3 install_ui_v3.py
"""
import os, sys, glob, subprocess, tempfile
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
ICONS = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Icons')
UI = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'UI')
CUT = os.path.join(ROOT, 'art', 'mockups', 'cut_sheet.py')
SHEETS = {
    'ui_v3_a': ['ui_star', 'ui_coin', 'ui_sunstone', '-', 'clean_soap_v3', 'tool_hand', 'tool_axe', 'act_jump', 'act_enter'],
    'ui_v3_b': ['act_play', 'ui_map', 'ui_board', 'ui_plus', 'ui_check', 'tool_pickaxe', 'tool_hammer', 'ui_music', 'ui_hand'],
    'ui_v3_c': ['bar_orange', 'bar_blue', 'btn_green', 'card', 'ribbon', 'round', 'plank', 'star_big', 'close'],
    'ui_v3_d': ['mat_wood', 'mat_branch', 'mat_stone', 'ui_heart', 'ui_hut', 'ui_gift', 'ui_shop', 'ui_lock', 'ui_search'],
    'ui_v3_e': ['ui_coconut', 'ui_coconut_gold', 'ui_settings', 'ui_home', 'ui_wardrobe', 'ui_album', 'ui_trophy', 'ui_fishing', 'ui_garden'],
}
UI_PARTS = {'bar_orange', 'bar_blue', 'btn_green', 'card', 'ribbon', 'round', 'plank', 'star_big', 'close'}
SKIP = {'clean_soap_v3',   # eşya simgesi (clean_soap) zaten aynı kalitede: değiştirilmez
        'ui_coconut', 'ui_coconut_gold'}   # 24 Ekim 2026'dan beri kodla 3B: art/scripts/coconut_scene.py

def square(im, size=256, pad=0.06):
    k = size * (1 - 2 * pad) / max(im.size)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    c = Image.new('RGBA', (size, size), (0, 0, 0, 0)); c.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2)); return c

os.makedirs(UI, exist_ok=True)
tmp = tempfile.mkdtemp()
for sheet, names in SHEETS.items():
    srcs = sorted(glob.glob(os.path.join(HERE, 'out', sheet, 'concept_*_0.png')))
    if not srcs: print('yok:', sheet); continue
    # gölgeli/ışıltılı sayfalarda (d, e) açık gri gölge de arka plan sayılsın
    env = dict(os.environ, CUT_THRESH='60' if sheet in ('ui_v3_d', 'ui_v3_e') else '28')
    subprocess.run([sys.executable, CUT, srcs[-1], tmp] + names, check=True, env=env)
for sheets in SHEETS.values():
    for n in sheets:
        if n == '-' or n in SKIP: continue
        p = os.path.join(tmp, n + '.png')
        if not os.path.exists(p): continue
        im = Image.open(p).convert('RGBA')
        if n in UI_PARTS:
            k = 512 / max(im.size)   # 9 dilim için yeterli çözünürlük
            im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).save(os.path.join(UI, n + '.png'))
        else:
            sq = square(im)
            sq.save(os.path.join(ICONS, n + '.png'))
            if n == 'ui_hand':   # parmak ucu: en üstteki opak pikselin ortası (Coach pivotu)
                a = sq.split()[3]; w, h = sq.size
                for y in range(h):
                    xs = [x for x in range(w) if a.getpixel((x, y)) > 128]
                    if xs: print(f'ui_hand parmak ucu pivot = ({sum(xs) / len(xs) / w:.2f}, {1 - y / h:.2f})'); break
print('kuruldu')

# ------------------------------------------------------------------ türetilen parçalar (kredi harcamadan)
import numpy as np, colorsys
def load(n): return np.array(Image.open(os.path.join(UI, n + '.png')).convert('RGBA')).astype(np.float32)
def save(a, n): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(UI, n + '.png'))
def hsv(a):
    rgb = a[..., :3] / 255.0; mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn + 1e-6
    h = np.where(mx == rgb[..., 0], ((rgb[..., 1] - rgb[..., 2]) / d) % 6, np.where(mx == rgb[..., 1], (rgb[..., 2] - rgb[..., 0]) / d + 2, (rgb[..., 0] - rgb[..., 1]) / d + 4)) / 6
    return h, (mx - mn) / (mx + 1e-6), mx
o = load('bar_orange'); h, s, v = hsv(o)
orange = (s > 0.45) & (v > 0.45) & (h > 0.02) & (h < 0.14) & (o[..., 3] > 200)
ys, xs = np.where(orange)
save(o[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * np.where(orange[ys.min():ys.max() + 1, xs.min():xs.max() + 1, None], 1, [1, 1, 1, 0]), 'fill_orange')
# koyu iz: turuncu çubuğun sağdaki boş (koyu) yarısı aynalanarak tam boş çubuk yapılır (turuncu iz kalmaz)
right = o[:, xs.max() + 16:]
t = np.concatenate([right[:, ::-1], right], axis=1)
save(t, 'track_dark')
b = load('bar_blue'); h, s, v = hsv(b)
blue = (s > 0.35) & (v > 0.5) & (h > 0.5) & (h < 0.62) & (b[..., 3] > 200)
ys, xs = np.where(blue)
cb = b[ys.min() + 2:ys.max() - 1, xs.min() + 2:xs.max() - 1].copy()   # parlama şeridi dahil iç kısım
from PIL import ImageDraw as _D
mk = Image.new('L', (cb.shape[1], cb.shape[0]), 0); _D.Draw(mk).rounded_rectangle((0, 0, cb.shape[1] - 1, cb.shape[0] - 1), cb.shape[0] // 2, fill=255)
cb[..., 3] = np.minimum(cb[..., 3], np.array(mk))
save(cb, 'fill_blue')
# düğme renk çeşitleri: yeşil düğmenin tonu kaydırılır (parlaklık ve gölge aynı kalır)
g = load('btn_green'); gh, gs, gv = hsv(g)
for name, hue in (('btn_blue', 0.56), ('btn_orange', 0.08), ('btn_pink', 0.95)):
    out = g.copy(); m = gs > 0.2
    nh = np.where(m, hue, gh)                       # tüm renkli pikseller tek tona: gövde ve alt kenar uyumlu
    for yy, xx in zip(*np.where(m)):
        r_, g_, b_ = colorsys.hsv_to_rgb(nh[yy, xx], gs[yy, xx], gv[yy, xx]); out[yy, xx, :3] = (r_ * 255, g_ * 255, b_ * 255)
    save(out, name)
print('türetildi: track_dark, fill_orange, fill_blue, btn_blue/orange/pink')

# ------------------------------------------------------------------ yazı tipi: Baloo 2 ExtraBold (OFL) sabit örneği
FONTS = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Fonts')
src_font = os.environ.get('BALOO_VAR')
if src_font and os.path.exists(src_font):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    os.makedirs(FONTS, exist_ok=True)
    f = instancer.instantiateVariableFont(TTFont(src_font), {'wght': 800})
    f.save(os.path.join(FONTS, 'Baloo2-ExtraBold.ttf'))
    print('yazı tipi kuruldu')
