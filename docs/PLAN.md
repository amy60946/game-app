# Pofi Adası — Mimari plan, proje yapısı, riskler ve açık sorular

Durum: **TASLAK — kullanıcı onayı bekleniyor.** Onaydan önce kod/varlık üretimi yapılmaz.

### Kullanıcı kararları (13 Ekim 2026)
- **S1 Depo:** Yeni ayrı depo (`pofi-adasi`, Git LFS).
- **S3 Test cihazı:** Yalnızca iPhone → Apple onayına kadar WebGL önizleme (iPhone Safari'de açılır); Apple gelince TestFlight. Android APK üretilir ama kullanıcı denemez.
- **S4 Nihai 3D:** Yapay zekâ ile 3D üretim (Meshy/Tripo vb.) + temizlik. 0A/0B ve yer tutucuları Claude Blender betikleriyle yapar. Araç seçimi ve ticari lisans planı (ücretli plan gerekebilir) 0B sonunda kullanıcıya sunulacak.
- **S5 Ses:** Şimdilik sessiz, sonra stüdyo. `VoiceSubtitleSystem` + `VoiceLineSO` + altyazı/karaoke altyapısı ses dosyası olmadan çalışır (zamanlama yoksa düz altyazı). Not/öneri: ara çözüm olarak cihazın yerleşik Türkçe sesi (iOS AVSpeechSynthesizer, kelime aralığı geri çağrısıyla vurgulama) ücretsiz kullanılabilir — onay beklemekte.
Tarih: 13 Ekim 2026. Kaynak: kullanıcının oyun brief'i + 3D varlık brief'i + `ornek-gorsellerim.docx` (57 stil referansı).

---

## 0. Kısa özet

- Çocuk oyunu, **ayrı bir Unity uygulaması** olarak yapılır (Unity 6 LTS, URP, C#, iOS + Android). Ebeveyn uygulaması (ParentApp, Expo) olduğu gibi kalır.
- Arka uç olarak **mevcut Supabase projesi** kullanılır. Brief'teki REST sözleşmesi (§6), Supabase RPC fonksiyonlarına çevrilir. Oyun kodu bunu bilmez; her şey `I*Service` arayüzlerinin arkasındadır. Önce `Mock*` servislerle çalışılır.
- Brief'teki M1–M10'un önüne bir **M0 (boru hattı)** ekliyorum. M0, boş bir Unity yapısının otomatik derlenip senin telefonunda açıldığını kanıtlar. Bu adım olmadan hiçbir şeyi gerçekten test edemeyiz (bkz. §1).
- 3D: Önce **Aşama 0A (ortak şablon)** ve **0B (konsept)** yapılır. Blender'ı betikle bu ortamda çalıştırıp önizleme render'ı alabilirim. Nihai kahraman modeller için dürüst kalite değerlendirmesi §6.4'te.

---

## 1. Çalışma ortamı gerçekleri (önemli)

| Konu | Durum | Sonuç |
|---|---|---|
| Unity Editor bu bulut ortamında | Unity indirme sunucuları ağ politikasında kapalı. Docker Hub erişilebilir, Unity lisansı yok. | Unity'yi burada doğrudan çalıştıramıyorum. C# kodunu yazarım; derleme, test ve build **GitHub Actions + GameCI** (Docker'da Unity) ile otomatik yapılır. Alternatif: `unityci/editor` imajını bu ortamda Docker ile denemek (lisans gerekir). |
| Unity lisansı | Unity Personal ücretsizdir (yıllık gelir/fon < 200 bin $). | Bir Unity hesabı açman gerekir. E-posta/şifre/lisans **GitHub repo Secrets**'a eklenir, sohbete asla yazılmaz. |
| Telefonda deneme | Expo Go Unity oyunu açamaz. | **Android**: CI'ın ürettiği APK doğrudan kurulur. **iOS**: Apple Developer hesabı + TestFlight gerekir (Apple onayı bekleniyor). Ara çözüm: her milestone'da **WebGL önizleme** (tarayıcıda, telefondan açılır). |
| Blender | `bpy` (Blender'ın Python modülü) PyPI'dan kurulabiliyor. 4 CPU, GPU yok. | Betikle modelleme ve Cycles CPU render yapılabilir (yavaş ama yeterli). Önizleme PNG'leri üretebilirim. |
| Depo | Şu an yalnızca `amy60946/parent-app` erişimim var. | Önerim: Git LFS'li yeni bir depo, `amy60946/pofi-adasi` (§2.1, açık soru S1). |
| GitHub Actions maliyeti | Özel depoda Linux dakikaları kotalı, macOS dakikaları 10 kat sayılır. | iOS build'ini yalnızca milestone sonlarında alırız. Günlük kontroller Linux'ta yapılır. |

---

## 2. Mimari

### 2.1 Depo ve araçlar
- **Yeni depo** `pofi-adasi` (öneri): Unity projesi + `art/` (Blender kaynakları) + `.github/workflows`. Büyük ikili dosyalar için Git LFS (`*.fbx, *.png, *.wav, *.blend`).
  - Alternatif: `parent-app/game/` klasörü. Daha basit, ama LFS kotası ve CI tek depoda karışır.
- Unity **6 LTS** (6000.x; M0'da güncel LTS yaması sabitlenir), **URP**, **Input System**, **Addressables**, **Localization** (tr tablosu), **TextMeshPro**, **Mobile Notifications**, **Test Framework**.
- Harici kütüphane en aza indirilir. Animasyon/tween için küçük bir iç yardımcı yazılır (lisans riski yok). Her harici varlık/font için `docs/LICENSES.md` tutulur.
- Font: Türkçe karakterli, açık lisanslı (OFL), yuvarlak bir yazı tipi (ör. Nunito / Baloo 2; M0'da seçilir).

### 2.2 Klasör yapısı
```
Assets/_Pofi/
  Scripts/
    Core/        GameBootstrap, EventBus, GameState, Clock (sunucu saatiyle düzeltilmiş), FeatureFlags, Remote config
    Services/    IAuthService, ITaskService, IWalletService, ISaveService, IAnalyticsService, IConfigService
                 Mock/  (yerel JSON sahte arka uç)   Supabase/  (gerçek uygulama, UnityWebRequest + RPC)
    Pet/         PetStatsSystem, PetGrowthSystem, PetController, SocketRig, VisemeDriver
    Economy/     EconomySystem (coin bakiyesi = sunucu; bekleyen harcama kuyruğu), XpSystem (günlük sınır)
    Progression/ ProgressionSystem, UnlockGate
    Tasks/       TaskSyncSystem, TaskBoard
    Shop/  Inventory/  Garden/  Fishing/  Cards/ (CardGameFramework, IGameRules, ColorMatch "Renk Eşle", Domino, Tower "Kule")
    MiniGames/   Coconut, HelpPet, Swim, Surf, Ski, Cave, Hike
    Social/      AmbientResidents, FriendVisit (Faz B, bayrak kapalı)
    Audio/       VoiceSubtitleSystem, SubtitleSyncController, PetVoice
    UI/          Tema (AgeBandProfile → A/B/C), ekranlar, ParentGate
    Data/        ScriptableObject tanımları (PetSpeciesSO, ItemSO, LevelTableSO, VoiceLineSO, RegionSO, FitRuleSO …)
  Prefabs/  ScriptableObjects/  Art/  Audio/  Localization/tr/  Scenes/
Assets/Tests/  EditMode/ (mantık birim testleri)  PlayMode/ (akış testleri)
art/         Blender kaynakları: pets/{pet}/, pets/_shared/, props/, environment/, ui_renders/, scripts/ (bpy)
tools/       Ses içe aktarma ve zamanlama aracı, kıyafet uyum ekran görüntüsü betiği
```

### 2.3 Sistemler ve olay akışı
- Sistemler birbirini doğrudan çağırmaz; tipli bir **EventBus** üzerinden konuşur (ör. `TaskApproved → EconomySystem → CoinsChanged → UI + PetStatsSystem(mutluluk)`).
- `GameState`: tek doğruluk kaynağı (pet, envanter, XP, seviye, ev yerleşimi, koleksiyon). Serileştirilebilir, sürüm numaralı (göç/migration desteği).
- **Zaman:** Göstergelerin azalması `lastTickUtc` farkıyla hesaplanır. Alt sınır ve günlük maksimum düşüş vardır. Cihaz saatiyle hile/karışıklığa karşı sunucu saati referans alınır.
- **Veri odaklı:** Pet türleri, eşyalar, fiyatlar, seviye eşikleri, açılış tablosu, ses satırları ve uyum kuralları ScriptableObject'tir. Uzaktan yapılandırma için Supabase'deki `game_config` tablosu (JSON) bu değerlerin üstüne yazar (fiyat, günlük XP sınırı, etkinlik).
- **Özellik bayrakları:** `FeatureFlags` (yerel varsayılan + remote config). Faz B (arkadaş ziyareti) kapalı gelir.

### 2.4 Addressables ve bellek
- Gruplar: `pet_01` … `pet_12` (model + texture + tür animasyonları), `shared_rig_anims`, `cosmetics`, `island`, `props`, `audio_voice_tr`, `ui_portraits`.
- Seçim karuseli: 12 kart **önceden render edilmiş portre** (ui_portraits, 512px). Yalnızca odaktaki karakter canlı 3D yüklenir (LOD1), kart değişince öncekinin bellekten çıkarılması garanti edilir.
- Oyunda yalnızca seçili pet'in tam kalite grubu bellekte durur. Bot pet'ler: aynı türün LOD2'si + renk varyasyonu (malzeme parametresiyle, ek texture yok).
- Bütçeler (brief §4) CI'da otomatik raporlanır: Addressables build raporu → pet başına boyut tablosu.

---

## 3. Arka uç entegrasyonu (Supabase'e eşleme)

Brief'teki sözleşme → mevcut sistemle uyumlu hâli:

| Brief | Supabase karşılığı | Not |
|---|---|---|
| `POST /child/auth {code}` | `auth.signInAnonymously()` + `rpc('redeem_child_code')` | **Zaten var.** Yanıta `age_band` eklenecek. `token` = Supabase oturumu. Refresh token iOS Keychain / Android Keystore'da saklanır (FR-AUTH-2). |
| Hatalı kod sınırı (FR-AUTH-3, SAFE-5) | `redeem_child_code` içinde deneme sayacı + bekleme | Yeni. |
| Kod iptali (FR-AUTH-4) | Ebeveyn "cihaz bağlantısını kaldır" → `children.user_id = null` → oyun `child_me()` ile fark eder | Ebeveyn uygulamasına küçük ekleme gerekir. |
| `GET /child/tasks` | `rpc('child_tasks', from, to)` | Tekrar kuralları (günlük/haftalık/aylık günler) **sunucuda** açılır; C#'ta ikinci bir kopyası olmaz. |
| Görev durumları | `completions.status`: `child_done`, `approved`, `declined_by_child`, `rejected_by_parent` + `parent_note` | Şu an `pending/approved` var. Göç: `pending → child_done`. `assigned` = kayıt yok; `missed` = süre geçti ve kayıt yok (hesaplanır). |
| `GET /child/wallet` | `coin_ledger` tablosu; bakiye = toplam | Coin **yalnızca** sunucudaki tetikleyiciyle eklenir (görev `approved` olunca). İstemci yazamaz (FR-ECO-1). |
| `POST /child/wallet/spend` | `rpc('spend_coins', item_id, qty, client_tx_id)` | Fiyat sunucudaki `shop_prices` tablosundan okunur (istemcinin fiyatına güvenilmez). `client_tx_id` ile çevrimdışı kuyruk tekrar gönderilse de bir kez işlenir. |
| `POST /child/sync` | `child_game_state` (jsonb, sürüm) + `rpc('sync_game_state')` | Çakışmada coin = sunucu. Diğer alanlar: sürüm/zaman damgası ile birleştirme; kurallar M4'te testlerle tanımlanır. |
| Remote config | `game_config` tablosu (yalnızca okuma) | |
| Bildirim (FR-TASK-4) | Oyun içi: Realtime/periyodik çekme. Uzak push: altyapı hazır, kapalı. | |

**Ebeveyn uygulamasına (ParentApp) gereken küçük eklemeler** (park edilmiş tarafa dokunur, sırası gelince sorarım):
1. Çocuk eklerken **yaş bandı** (A/B/C). Doğum gününden önerilir, ebeveyn değiştirebilir.
2. İnceleme ekranında **reddet + not** (`rejected_by_parent`, `parent_note`).
3. Çocuğun coin bakiyesini görme.
4. Cihaz bağlantısını kaldırma (kod iptali).

---

## 4. Milestone planı (öneri)

Her milestone sonunda: çalışan build (Android APK + WebGL önizleme; Apple hazırsa TestFlight), kısa özet, test raporu.

| # | İçerik | Senin göreceğin |
|---|---|---|
| **M0** (yeni) | Depo, Git LFS, Unity projesi, GameCI ile otomatik test + Android/WebGL build, sürüm adlandırma | Telefonda açılan boş "Pofi Adası" ekranı. Boru hattının çalıştığının kanıtı. |
| M1 | İskelet, EventBus, GameState, Kayıt/Yükleme, Mock servisler, kodla giriş (Mock + Supabase), yaş bandı teması, Addressables altyapısı, Localization tablosu, ParentGate | Kod girip giriş, yaş bandına göre farklı arayüz |
| M2 | `PetSpeciesSO`, 12 yer tutucu pet (renkli primitif + soket hiyerarşisi), karusel (portre + odakta canlı 3D, 360° döndürme), son onay, isim (filtre), 4 gösterge + azalma, ev, büyüme evreleri | Pet seçip isim verme, göstergeler |
| M3 | Ekonomi, dükkan, envanter, giydirme, `CosmeticFitSystem` + otomatik uyum ekran görüntüsü betiği | Coin ile alışveriş, giydirme |
| M4 | Görev panosu, durum geçişleri, senkron + çevrimdışı kuyruk, coin kazanma sahnesi, Supabase göçleri (§3), ebeveyn uygulaması eklemeleri | ParentApp'te onaylanan görev oyunda coin olur |
| M5 | Ada haritası, bölge geçişi, gün/gece, seviye/açılış tablosu, havuç etkisi, seviye kutlaması | Adayı gezme, kilitli bölgeler |
| M6 | Hindistan cevizi, Pet'e yardım, Yüzme, Sörf, Kayak | 5 mini oyun |
| M7 | Bahçe, Balık tutma, Koleksiyon, Rozetler, Günlük görevler, Seri | |
| M8 | `CardGameFramework`, Renk Eşle, Domino, Kule, bot yapay zekâ | 3 masa oyunu |
| M9 | Ses+altyazı senkronu (karaoke), viseme, pet sesleri, erişilebilirlik | |
| M10 | Mağara, Dağ, Festival, Fener, cila, performans/bellek, mağaza hazırlığı | |

Gerçek 3D modeller, sanat hattında (§6) **paralel** ilerler ve hazır oldukça yer tutucu prefab'ların yerine geçer.

**Önerim (not, karar senin):** M0 → M1 → M2'nin ilk yarısı bir "dikey dilim" olarak hızlıca bitirilsin. Böylece telefonda gerçek bir şey görür ve yönü erkenden doğrularız.

---

## 5. Veri ve denge taslakları (M1–M3'te kesinleşir)

- Seviye XP eşikleri (taslak): Sv2 = 100, sonra her seviye ×1.35 → Sv15 ≈ 4.900. Toplamda, günlük XP sınırıyla (Band A 250 / B 300 / C 350) yaklaşık 8–10 haftada Sv15.
- Fiyat taslağı (görev ödülü varsayılanı 5/10/20 coin): yiyecek 3–6, sabun 3, gözlük/şapka 15–30, kıyafet 25–60, ev eşyası 40–120, tohum 2, premium set 150–250. "Günde 2–4 görev = yiyecek + sabun karşılanır, büyük eşya birkaç günde" kuralı bir simülasyon testiyle doğrulanır.
- Göstergeler: saatte ~4 puan düşüş, alt sınır 10, günlük en fazla 60 puan düşüş (veriyle ayarlanır).

---

## 6. 3D sanat hattı (Aşama 0A / 0B planı)

### 6.1 0A — Ortak şablon
- Oran kılavuzu: chibi, toplam boy 0.75 m (Yavru 0.6 / Genç 0.75 / Yetişkin 0.9), kafa ≈ boyun %48'i. Gövde "kıyafet şablonu" sabit oranlı.
- Ortak iskelet (Unity Humanoid'e uygun isimler) + tür katmanı kemikleri (kuyruk, kulak, hortum, yele, anten, kanat kapağı, kabuk).
- Soketler: `socket_head`, `socket_eyes`, `socket_body`, `socket_back`, `socket_hand_L`, `socket_hand_R` + tür başına çakışma kuralları (Tosbi kabuk, Piko diken, Benli kanat kapağı, Arlo yele) → `FitRuleSO`.
- Şapka varyantları: `normal`, `ear_holes`, `antenna_holes`, `mane_fit`.
- "Yumuşak vinil" shader: URP Shader Graph (soft lit, rim, sahte subsurface, renkli gölge tonu). Yedek: URP Lit. Ortak ışık sahnesi ve portre kamera ayarları.

### 6.2 0B — Konsept
- 12 pet için ön/yan/arka turnaround (Blender blockout render'ı), renk paleti, yüz kılavuzu.
- **Silüet sayfası** (12 siyah silüet) ve **renk ayrışma tablosu** (ΔE ve renk körlüğü simülasyonu ile).
- Erken fark ettiğim ayrışma riskleri:
  - **Mavi (#2F8CFF) ve Fifi (#5AD1FF)**: aynı ton ailesi. Öneri: Fifi'yi daha açık/pastel ve hafif turkuaza kaydırmak. Ama **Tosbi (#00C2B8)** ile çakışmamalı → tabloyla karar verilecek.
  - **Pıtı (#FFD21F), Arlo (#FFB000) ve Pofi (#FF9A2E)**: sarı-turuncu yığılması. Silüet farkı (püskül / yele / iri kulak) zaten güçlü, yine de ton aralığı açılacak.
  - **Mimi (pembe) ve Benli (kırmızı)**: Deuteranopi simülasyonunda yakınlaşabilir → desen farkı (Benli'nin benekleri) zorunlu.

### 6.3 Telif kontrolü — erken uyarılar
Referanslarda turuncu, tulumlu bir tilki/kırmızı panda karakteri var. **Pofi (turuncu tilki-tavşan)** buna yakın düşebilir. Öneri:
- Uzun, ucu yuvarlak **tavşan kulakları**,
- Krem yüz maskesi yerine farklı bir desen,
- **Tulum yok**.

Pembe ayı/kedi ve mor yaratık referansları da var; Mimi ve Boncuk'un silüeti bunlardan ayrıştırılacak. 0B'de her pet referansla yan yana kontrol edilir; şüphede durup sana sorarım.

### 6.4 Kalite konusunda dürüst değerlendirme
- Betikle Blender'da (bpy) yapabileceklerim: temiz, şişkin, yuvarlak "oyuncak" formları, blockout'lar, soket/iskelet şablonları, yer tutucular, ikon/portre render hattı, otomatik uyum render'ları. Bunlar **0A/0B ve yer tutucu** için yeterli.
- Referanstaki seviye (heykel detayı, kumaş kıvrımları, ince yüz ifadeleri, yüksek kaliteli rig ve animasyon) betikle elde edilemez. 12 pet × 3 evre × 20+ animasyon gerçekçi olarak şunlardan birini gerektirir:
  1. **İnsan 3D sanatçı** (önerim; brief hazır, aynen verilebilir), ya da
  2. **Yapay zekâ ile 3D üretim** (Meshy, Tripo, Rodin vb.) + sanatçı temizliği (topoloji, UV, rig). Lisans, tutarlılık ve topoloji sorunları belgelenir.
- Her aşamada poligon/texture/bellek raporu ve "insan cilası gereken yerler" listesi veririm.

---

## 7. Ses (FR-VOICE)

- Band A'da her metin seslendirilir; yüzlerce satır demektir.
- Öneri: Yer tutucu ve belki nihai ses için **Azure Neural TTS (tr-TR)**. Kelime zamanlarını (karaoke için `wordTimings`) ve **viseme kimliklerini** doğrudan verdiği için FR-VOICE-1 ve FR-VOICE-4'e birebir uyuyor. API anahtarı ortam sırrı olarak eklenir; ticari ve çocuk içeriği lisans şartları kontrol edilir.
- Stüdyo kaydı gelirse aynı araç zamanlamayı ses dosyasından hizalar (forced alignment).
- Pet sesleri: tür başına ton/perde profili + CC0/ticari lisanslı ses kütüphanesi ya da sentez. Lisanslar `LICENSES.md`'de tutulur.

---

## 8. Riskler

| Risk | Etki | Önlem |
|---|---|---|
| Unity'yi bu ortamda çalıştıramamak | Her değişikliği CI ile doğrulamak gerekir, döngü yavaşlar | M0'da GameCI; mantık kodu Unity'den bağımsız saf C# + EditMode testleri |
| iOS testinin Apple hesabına bağlı olması | iPhone'da deneme gecikir | Android APK + WebGL önizleme; Apple gelince TestFlight hattı hazır |
| Kapsam çok büyük (v1.0 = birkaç kişilik ekipte aylar sürecek iş) | Süre uzar | Dikey dilim önce; milestone'lar küçük, gösterilebilir parçalar |
| Sanat kalitesi ve tutarlılığı | Ürün hissi zayıflar | 0A/0B ile stil kilidi; nihai modeller için sanatçı/yapay zekâ kararı (S4) |
| Telif benzerliği | Hukuki risk | §6.3 kontrolleri, referansla yan yana karşılaştırma, lisans kaydı |
| 12 pet × kıyafet uyumu | Görsel hatalar | `CosmeticFitSystem` kuralları + otomatik uyum render raporu (kabul ölçütü 8) |
| Uygulama boyutu (≤ 70 MB pet) | Mağaza/indirme sorunu | Addressables + bütçe raporu CI'da; gerekirse sonradan indirme (remote catalog) |
| Çocuk verisi mevzuatı | Yayın engeli | §9 kontrol listesi, ebeveyn onay akışı ParentApp'te |
| Supabase anonim oturumu cihaz silinince kaybolur | Çocuk girişi kopar | Kod yeniden girilince ilerleme sunucudan (`child_game_state`) geri gelir |
| Sürüm uyumsuzlukları (Unity, URP, paketler) | Build kırılır | Sürümler sabitlenir; güncellemeler ayrı commit ve CI ile yapılır |

---

## 9. Mağaza ve uyum kontrol listesi (TASLAK — karar senin)

> Mağaza kuralları sık değişir. Yayından önce Apple, Google, KVKK ve FTC'nin güncel metinleriyle yeniden doğrulanacak.

**Temel sorun:** Apple'ın **Kids Category** yaş bantları "5 ve altı / 6–8 / 9–11"dir. 6–15 aralığını tek bir bant kapsamaz.

- **Seçenek A (önerim):** Kids Category **dışında** yayınlamak, ama Kids kurallarına gönüllü uymak (üçüncü taraf reklam/analitik yok, dış bağlantı ve satın alma yok, ebeveyn kapısı). Yaş derecelendirmesi en düşük seviyede (4+). Pazarlama ve mağaza metinleri aile odaklı olur.
- **Seçenek B:** Kids Category "9–11" bandı. 6–8 ve 12–15 yaşları kapsam dışında kalır, uygulamayı yanlış konumlandırır.

**Google Play:** Hedef kitlede 13 yaş altı olduğu için **Families politikası** zorunlu. Data safety formu, reklam yok, yalnızca Families uyumlu SDK. "Teacher Approved" isteğe bağlı.

**COPPA (ABD, 13 yaş altı):** Doğrulanabilir ebeveyn onayı ebeveyn uygulamasında alınır (çocuk kodu ebeveyn hesabından üretildiği için uygun zemin var). Gizlilik bildirimi, veri saklama süresi ve silme hakkı gerekir. 2025 COPPA değişikliklerine göre güncellenir.

**GDPR-K (AB):** Ülkeye göre 13–16 yaş altı için ebeveyn onayı, veri minimizasyonu.

**KVKK (Türkiye):** Çocuğun verisi için velinin **açık rızası** ve aydınlatma metni gerekir. Veri yurt dışında (Supabase bölgesi) tutuluyorsa yurt dışı aktarım şartlarına uyulur.

**Ortak maddeler:**
- Uygulama içi satın alma yok, reklam yok, dış bağlantı yok, serbest sohbet yok.
- Analitik kapalı ya da yalnızca birinci taraf, anonim ve ebeveyn onaylı.
- Çökme raporları kişisel veri içermez.
- Hesap/veri silme ebeveyn uygulamasında (zaten var).
- Herkese açık gizlilik politikası URL'si.
- App Review için demo ebeveyn hesabı ve demo çocuk kodu.

---

## 10. Açık sorular

- ~~S1 Depo~~ → yeni depo.
- **S2 Unity hesabı + CI:** Ücretsiz Unity Personal hesabı açıp bilgileri GitHub Secrets'a ekleyebilir misin? (Adım adım anlatırım.)
- ~~S3~~ → yalnızca iPhone.
- ~~S4~~ → yapay zekâ ile 3D üretim + temizlik.
- ~~S5~~ → şimdilik sessiz, sonra stüdyo.
- **S6 ParentApp'teki çocuk giriş ekranı:** Çocuklar artık Pofi Adası'na girecek. ParentApp'teki masalsı kod ekranı kaldırılsın mı (ParentApp yalnızca ebeveyn uygulaması olur)?
- **S7 Yaş bandı:** Doğum gününden otomatik önerilip ebeveyn mi değiştirsin, yoksa her zaman elle mi seçilsin?
- **S8 Mağaza stratejisi:** §9 Seçenek A mı, B mi?
- **S9 Pofi tasarımı:** §6.3'teki telif önlemleri (tavşan kulakları, tulum yok) uygun mu?

## 11. Öneriler (uygulanmadı, onay bekler)

- M0 + dikey dilim önce (§4).
- Görev tekrarlarının sunucuda açılması (§3): iki uygulamada ayrı mantık tutmamak için.
- Coin harcamasında fiyatın sunucudan okunması (§3): hileye karşı.
- Oyunun adı ile ebeveyn uygulamasının adı (ParentApp) arasındaki marka ilişkisinin netleştirilmesi (mağazada "ParentApp" + "Pofi Adası" gibi).
