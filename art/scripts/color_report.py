"""Renk ayrışma raporu: docs/art/renk_ayrisma.md + palet görseli üretir."""
import itertools, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from colors import hex2rgb, lab, de2000, sim, CVD
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
V0 = {'Pofi': '#FF9A2E', 'Mavi': '#2F8CFF', 'Kurbi': '#3ED16A', 'Mimi': '#FF5FA8', 'Pıtı': '#FFD21F', 'Boncuk': '#9B5CFF',
      'Tosbi': '#00C2B8', 'Piko': '#C77D2E', 'Fifi': '#5AD1FF', 'Arlo': '#FFB000', 'Lolo': '#FFF1D6', 'Benli': '#FF2E3B'}
# pets.py ile aynı (tek kaynak orada; burada rapor için)
import importlib.util
V1 = {'Pofi': '#FF7A2A', 'Mavi': '#1F6FE8', 'Kurbi': '#46D063', 'Mimi': '#FF86C2', 'Pıtı': '#FFEA5C', 'Boncuk': '#A77BFF',
      'Tosbi': '#00A693', 'Piko': '#8C5A3C', 'Fifi': '#8EDCFF', 'Arlo': '#FFAE1A', 'Lolo': '#FFF1D6', 'Benli': '#E8202E'}
SHAPE = {
    frozenset(('Piko', 'Benli')): 'Piko: sırt dikenleri + krem yüz; Benli: siyah benekli kanat kapakları + antenler',
    frozenset(('Kurbi', 'Arlo')): 'Kurbi: sırt plakaları + kalın kuyruk; Arlo: yele halkası',
    frozenset(('Pofi', 'Arlo')): 'Pofi: uzun tavşan kulakları; Arlo: yele',
    frozenset(('Pıtı', 'Arlo')): 'Pıtı: tepe püskülü + gaga; Arlo: yele',
    frozenset(('Mimi', 'Tosbi')): 'Mimi: üçgen kulaklar + bıyık; Tosbi: sırt kabuğu',
    frozenset(('Mavi', 'Boncuk')): 'Mavi: beyaz yüz maskesi + gaga; Boncuk: yuvarlak kulaklar',
    frozenset(('Kurbi', 'Tosbi')): 'Kurbi: plakalar + kuyruk; Tosbi: kabuk + yüzgeçler',
    frozenset(('Pofi', 'Kurbi')): 'Pofi: uzun tavşan kulakları + kabarık kuyruk; Kurbi: sırt plakaları + kalın kuyruk',
    frozenset(('Pıtı', 'Lolo')): 'Pıtı: gaga + püskül; Lolo: uzun kulaklar + boyun püskülleri',
}
def rows(p):
    out = []
    for a, b in itertools.combinations(p, 2):
        ra, rb = hex2rgb(p[a]), hex2rgb(p[b])
        d = {'normal': de2000(lab(ra), lab(rb))}
        for k in CVD: d[k] = de2000(lab(sim(ra, k)), lab(sim(rb, k)))
        out.append((a, b, d))
    return out
def worst(p, k): return min(rows(p), key=lambda r: r[2][k])
L = []
L.append('# Renk ayrışma tablosu (Aşama 0B)\n')
L.append('Ölçüt: CIEDE2000 renk farkı (ΔE). Kabaca ΔE < 10 "karışabilir", 10–20 "yakın", > 20 "net ayrışır".')
L.append('Renk körlüğü simülasyonu: Machado 2009 (deutan/protan/tritan, tam şiddet). Renkle ayrışmayan çiftler **şekil/desen** farkıyla ayrışmak zorundadır.\n')
L.append('## Revize edilen ana renkler\n')
L.append('| # | Pet | Brief önerisi | Revize | Neden |')
L.append('|---|---|---|---|---|')
why = {'Pofi': 'Arlo ile çok yakındı (ΔE 10) → daha kırmızımsı turuncu', 'Mavi': 'Boncuk ile deutan 1.9 → daha koyu kobalt',
       'Mimi': 'Tosbi ile deutan → daha açık pembe', 'Pıtı': 'Arlo ile yakın → daha açık limon sarısı',
       'Boncuk': 'Mavi ile deutan → daha açık lavanta-mor', 'Tosbi': 'Mimi/Kurbi ile → biraz daha koyu turkuaz',
       'Piko': 'Benli ile deutan 0.3 (!) → daha koyu kakao-kahve', 'Fifi': 'Mavi/Tosbi ile → daha açık gök mavisi',
       'Arlo': 'Pofi/Pıtı arasında sıkışmıştı → kehribar altın', 'Benli': 'Piko ile → daha koyu kırmızı', 'Kurbi': 'hafif ayar'}
for i, n in enumerate(V0, 1):
    L.append(f'| {i} | {n} | `{V0[n]}` | `{V1[n]}` | {why.get(n, "değişmedi")} |')
L.append('\n## Önce / sonra: en kötü çiftler\n')
L.append('| Görme | Brief paleti (en kötü çift) | Revize palet (en kötü çift) |')
L.append('|---|---|---|')
for k in ('normal', 'deutan', 'protan', 'tritan'):
    a = worst(V0, k); b = worst(V1, k)
    L.append(f'| {k} | {a[0]}–{a[1]}: ΔE {a[2][k]:.1f} | {b[0]}–{b[1]}: ΔE {b[2][k]:.1f} |')
L.append('\n## Revize palette yakın kalan çiftler ve şekil/desen ayrımı\n')
L.append('| Çift | normal | deutan | protan | tritan | Şekil/desen farkı |')
L.append('|---|---|---|---|---|---|')
for a, b, d in sorted(rows(V1), key=lambda r: min(r[2]['normal'] / 2, r[2]['deutan'], r[2]['protan'])):
    if min(d['normal'] / 2, d['deutan'], d['protan']) >= 10: continue
    L.append(f"| {a}–{b} | {d['normal']:.1f} | {d['deutan']:.1f} | {d['protan']:.1f} | {d['tritan']:.1f} | {SHAPE.get(frozenset((a, b)), '—')} |")
L.append('\nTüm çiftler normal görmede ΔE ≥ 19. Renk körlüğünde yakınlaşan çiftlerin hepsinde güçlü silüet farkı var (bkz. silüet sayfası).')
os.makedirs(os.path.join(ROOT, 'docs', 'art'), exist_ok=True)
open(os.path.join(ROOT, 'docs', 'art', 'renk_ayrisma.md'), 'w').write('\n'.join(L) + '\n')
# palet görseli
from PIL import Image, ImageDraw, ImageFont
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
img = Image.new('RGB', (12 * 130, 2 * 130 + 60), 'white'); d = ImageDraw.Draw(img)
for i, n in enumerate(V0):
    d.rounded_rectangle((i * 130 + 8, 8, i * 130 + 122, 122), 18, fill=V0[n])
    d.rounded_rectangle((i * 130 + 8, 138, i * 130 + 122, 252), 18, fill=V1[n])
    d.text((i * 130 + 65, 262), n, fill=(50, 50, 60), font=f, anchor='mt')
img.save(os.path.join(ROOT, 'docs', 'art', 'palet_once_sonra.png'))
print('\n'.join(L))
