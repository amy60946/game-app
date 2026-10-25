# Uygulama simgesi: S'ye O'nun çene yapısı (kullanıcı, 25 Ekim 2026: "birinin çene yapısını diğerine koy, kodla tekrar dene,
# geri kalan bütün detaylar aynı kalsın"). Yapay zekâyla yeniden üretim yok: S (şu anki simge) piksel piksel korunur; yalnız
# kafanın altına O'nun dalgalı jöle kıvrımı (kafa altındaki kalın, parlak etek) görüntü işlemeyle yerleştirilir:
#   1. O'da mavi jöle maskesi → kafa altı bandı (kol kesilir, sağ kenar yumuşatılır);
#   2. bant S'deki kafa genişliğine ölçeklenir, S'nin kafa ortasına hizalanır, rengi S'nin mavisine eşlenir (kanal ortalama/sapma);
#   3. S'nin kafasının bulunmadığı yerde (yanlar, alt) kıvrım tam görünür; S'nin kafasının içinde yalnız alt kenara yakın bölgede
#      görünür ve yukarı doğru S'ye karışır — ağız, yanak, göz hiç değişmez (ayrıca korunur);
#   4. kıvrımın tişörte düşen yumuşak gölgesi eklenir.
# Kullanım: <python + numpy/scipy/PIL> art/scripts/app_icon_chin.py <çıktı_klasörü> [ad:y_bağlantı:ölçek_çarpanı ...]
#   girdiler art/icon_chin/src_S.png (= Assets/_Pofi/Art/AppIcon.png, 24 Ekim), src_O.png (O seçeneği, Meshy son taslak).
import os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'icon_chin')


def load(name):
    return np.asarray(Image.open(os.path.join(SRC, name)).convert('RGB')).astype(np.float32)


def blue(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (b > r + 25) & (b >= g) & (a.max(-1) > 90)


def head_mask(a, seed):
    """Mavi jöle bölgesi (parlama ve yanaklar dahil, delikler dolu); seed noktasını içeren parça."""
    m = nd.binary_fill_holes(nd.binary_closing(blue(a), iterations=3))
    lab, _ = nd.label(m)
    return lab == lab[seed[1], seed[0]]


def rows(m, y):
    xs = np.where(m[y])[0]
    return (int(xs[0]), int(xs[-1])) if len(xs) else None


def o_band(O, y0=620, y1=822, cut_x=700):
    """O'nun kafa altı bandı: y0..y1 satırları, x <= cut_x (sağda kolla birleşen bölge alınmaz; eğme sağ yarıyı
    sol yarının aynası genişliğe açar — S önden bakıyor, O hafif yandan)."""
    m = head_mask(O, (450, 500))
    band = m[y0:y1].copy()
    band[:, cut_x + 1:] = False
    lab, _ = nd.label(band)
    sizes = nd.sum(band, lab, range(1, lab.max() + 1))
    band = lab == (np.argmax(sizes) + 1)
    band = nd.binary_opening(band, iterations=2)
    return O[y0:y1], band


def match_color(src, smask, ref, rmask):
    out = src.copy()
    for c in range(3):
        s = src[..., c][smask]; r = ref[..., c][rmask]
        out[..., c] = (src[..., c] - s.mean()) / (s.std() + 1e-6) * r.std() + r.mean()
    return np.clip(out, 0, 255)


def compose(S, O, attach_y=612, k_scale=1.0, fade=30, shadow=0.32, blend_rows=70, mirror=False, cut_x=760):
    Sm = head_mask(S, (500, 440))
    # S'nin yüz ayrıntıları (ağız, yanak, göz, kaş): kafanın içinde kırmızı ağırlıklı ya da koyu pikseller + çevresi — kesinlikle korunur
    face = Sm & ((S[..., 0] > S[..., 2]) | (S.max(-1) < 80))
    face = nd.binary_dilation(face, structure=np.ones((3, 3)), iterations=8)
    l, r = rows(Sm, attach_y)
    sw, sc = r - l, (l + r) / 2.0
    oy0 = 620
    ob, om = o_band(O, oy0, cut_x=cut_x)
    xs = np.where(head_mask(O, (450, 500))[oy0])[0]   # O'nun bu satırdaki kafa genişliği (ilk parça; sağdaki kol değil)
    run = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)[0]
    ol, orr = int(run[0]), int(run[-1])
    ow = orr - ol
    k = sw / ow * k_scale
    nh, nw = int(round(ob.shape[0] * k)), int(round(ob.shape[1] * k))
    img = np.asarray(Image.fromarray(ob.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float32)
    msk = np.asarray(Image.fromarray((om * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255
    # O'nun arka plan saçağı girmesin: maske 1 px içe, sonra yumuşak kenar
    msk = nd.grey_erosion(msk, size=(5, 5)); msk = nd.gaussian_filter(msk, 0.9)
    ox = int(round(sc - (ow * k) / 2.0 - ol * k)); oy = attach_y   # O'nun sol kenarı S'nin ortasına göre yerleşir
    H, W = S.shape[:2]
    big_img = np.zeros_like(S); big_m = np.zeros(S.shape[:2], np.float32)
    # satır satır eğme: kıvrımın üstü S'nin yuvarlak kafasının kenarını izler (köşe/basamak olmaz), aşağı indikçe O'nun kendi
    # genişliğine açılır; sağ kenar sol kenarın S ortasına göre aynası (simetrik etek)
    # satırın dış kenarları (en geniş satırdan aşağısı, dilimlerin arası açılsa da sabit: dilimlerin alt kıvrımı bozulmaz)
    A = np.full(nh, np.nan); B = np.full(nh, np.nan)
    for i in range(nh):
        xs = np.where(msk[i] > 0.5)[0]
        if len(xs) >= 4: A[i], B[i] = xs[0], xs[-1]
    ok = ~np.isnan(A)
    i_full = int(np.nanargmin(np.where(ok, A, np.nan)))
    A[i_full:] = A[i_full]; B[i_full:] = B[i_full]
    # kenar satırdan satıra titremesin (tüylü görünüyordu): dikeyde yumuşat
    A[ok | (np.arange(nh) > i_full)] = nd.gaussian_filter1d(A[ok | (np.arange(nh) > i_full)], 4, mode='nearest')
    B[ok | (np.arange(nh) > i_full)] = nd.gaussian_filter1d(B[ok | (np.arange(nh) > i_full)], 4, mode='nearest')
    TL = np.zeros(nh); TR = np.zeros(nh)
    for i in range(nh):
        y = oy + i
        if not ok[min(i, i_full)] and i <= i_full: continue
        tl_n = ox + A[i]; tr_n = (2 * sc - tl_n) if mirror else (ox + B[i])
        br = rows(Sm, y) if 0 <= y < H else None
        w = np.clip(i / float(blend_rows), 0, 1); w = w * w * (3 - 2 * w)
        if i > i_full:
            TL[i], TR[i] = TL[i_full], TR[i_full]
        elif br is not None:
            TL[i] = br[0] + (tl_n - br[0]) * w; TR[i] = br[1] + (tr_n - br[1]) * w
        else:
            TL[i], TR[i] = tl_n, tr_n
    for i in range(nh):
        y = oy + i
        if y < 0 or y >= H or np.isnan(A[i]) or TR[i] - TL[i] < 8: continue
        tl, tr, hl, hr = TL[i], TR[i], A[i], B[i]
        xa, xb = max(0, int(np.floor(tl)) - 2), min(W, int(np.ceil(tr)) + 3)
        xx = np.arange(xa, xb, dtype=np.float32)
        u = (xx - tl) / (tr - tl)
        sx = hl + u * (hr - hl)
        sy = np.full_like(sx, i)
        for c in range(3):
            big_img[y, xa:xb, c] = nd.map_coordinates(img[..., c], [sy, sx], order=1, mode='nearest')
        mv = nd.map_coordinates(msk, [sy, sx], order=1, mode='constant')
        if i <= i_full: mv[(u < -0.004) | (u > 1.004)] = 0
        big_m[y, xa:xb] = mv
    # renk: kıvrım S'nin alt kafa mavisine eşlenir (yalnız mavi pikseller ölçülür)
    ref = Sm & blue(S) & ~face; ref[:attach_y - 140] = False; ref[attach_y + 40:] = False
    big_img = match_color(big_img, (big_m > 0.5) & blue(big_img), S, ref)
    # karışım: bağlantı çizgisinden aşağı 'fade' px içinde S'den O'ya geçer, altı tamamen O (S'nin eski yuvarlak çenesi ve
    # tişörte düşen koyu gölgesi altta kalır); S'nin kafasının dışında (yanlarda açılan etek) kıvrım her yerde tam görünür
    yy = np.arange(H, dtype=np.float32)[:, None]
    t = np.clip((yy - attach_y) / float(fade), 0, 1); t = t * t * (3 - 2 * t)
    inside = nd.gaussian_filter(Sm.astype(np.float32), 2)
    a = big_m * (inside * t + (1 - inside))
    a = a * (1 - nd.gaussian_filter(face.astype(np.float32), 2))   # yüz ayrıntısı kesin korunur
    # gölge: kıvrımın altına, kıvrımın dışında kalan yere (tişört, kol, arka plan)
    sh = nd.shift(nd.gaussian_filter(big_m, 9), (14, 4), order=1) * (1 - big_m)
    sh[:attach_y] = 0
    out = S * (1 - shadow * sh[..., None])
    out = out * (1 - a[..., None]) + big_img * a[..., None]
    return np.clip(out, 0, 255).astype(np.uint8), dict(k=round(k, 3), attach=attach_y, width=sw)


if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    # ad:bağlantı_y:ölçek[:m] (m = sağ yarı sol yarının aynası, kol tarafı x<=700)
    specs = sys.argv[2:] or ['A:612:1.0', 'B:600:1.0', 'C:612:1.08']
    S, O = load('src_S.png'), load('src_O.png')
    for sp in specs:
        f = sp.split(':'); name, ay, ks = f[0], f[1], f[2]; mir = len(f) > 3 and f[3] == 'm'
        im, info = compose(S, O, int(ay), float(ks), mirror=mir, cut_x=700 if mir else 760)
        Image.fromarray(im).save(os.path.join(out, f'chin_{name}.png'))
        print(name, info, flush=True)
