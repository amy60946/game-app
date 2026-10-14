# Meshy kredi planı (Premium, 3.100 kredi/ay)

Ölçülen gerçek maliyetler (pilot, 14 Ekim 2026 – `art/meshy/ledger.csv`):

| İşlem | Kredi |
|---|---|
| Konsept görsel (nano-banana-pro, 1 görsel) | 9 |
| Görselden 3D, dokulu + PBR (latest) | 30 |
| Görselden 3D, dokulu (meshy-6-lite) – küçük eşyalar için | 15 |
| İskelet (yürüme + koşu animasyonu dahil) | 5 |
| Ek animasyon (her biri) | 3 |

Pilot harcaması: Pofi 56 + palmiye 39 + ada parçası 39 + şapka denemesi 24 = **158**. Kalan: **2.942**.

## Tahmin (kalan iş)

| Öncelik | İş | Adet | Birim | Toplam |
|---|---|---|---|---|
| P1 | Petler (konsept ~1,5 deneme, 3D ~1,2 deneme, iskelet, 6 animasyon) | 11 | ~73 | ~800 |
| P1 | Ada/harita binaları (ev, dükkan, pano, kulübe, çadır, fener, iskele, mağara girişi…) | 12 | ~39 | ~470 |
| P1 | Ada zemin parçaları (çeşitlilik) | 3 | ~39 | ~120 |
| P1 | Çevre süsleri (kaya, çalı, çiçek, çit, kayık, fener direği…) – lite | 10 | ~24 | ~240 |
| P1 | Simgeler (yiyecek, tohum, balık, böcek, kabuk…) – bir görselde 9'lu sayfa | 36 | 9/9 | ~45 |
| P1 | Arayüz görselleri (düğme, panel, çerçeve, arka plan) | 10 | 9 | ~90 |
| P2 | Kıyafet/aksesuar – lite | 27 | ~24 | ~650 |
| P2 | Ev eşyası + dekor – lite | 9 | ~24 | ~215 |
| | **Toplam tahmin** | | | **~2.630** |
| | Yedek (yeniden denemeler) | | | ~310 |

Sonuç: Premium'un bu ayki kredisi projeyi **sığdırıyor** ama yedek dar. Kural:
1. Önce P1 (oyunun görünümü), sonra P2.
2. Küçük eşyalarda lite model, büyüklerde (pet, bina) tam model.
3. Her pet için önce konsept görsel onayı, sonra 3D (3D en pahalı adım; boşa harcanmasın).
4. Kredi 300'ün altına inerse dururum ve sana sorarım (ek kredi paketi ya da öncelik kesme).

Riskler:
- Meshy iskeleti iki ayaklı karakterler için. Top gövdeli Pıtı, kaplumbağa Tosbi ve uğur böceği Benli'de iskelet zorlanabilir. Gerekirse bu üçünde animasyonu basit hareketlerle (zıplama, sallanma) kodla yaparım.
- Kıyafetler 12 farklı vücuda tek modelle oturmayacak: soket + ölçek + pet başına küçük ayar tablosu gerekir.
