# Pofi Adası — Claude için çalışma notları

- Kullanıcı yazılımcı değil. Türkçe, sade dille, adım adım ve nereye tıklayacağını söyleyerek anlat. Şifre/anahtar/lisansı sohbete yapıştırmasını ASLA isteme; GitHub Secrets'a eklenir.
- Plan ve kararlar: `docs/PLAN.md` (onaylandı, 13 Ekim 2026). Kapsam dışına çıkma; öneriler not olarak yazılır ve sorulur. Belirsiz kararda tahmin etme, kısa soru sor.
- Ebeveyn uygulaması (ParentApp, Expo) ayrı depoda: `amy60946/parent-app` (`docs/DURUM.md`); uzman paneli ClinicApp: `amy60946/clinic-app`. Arka uç ortak Supabase projesi; sözleşme `amy60946/ortak`.
- Unity 6 LTS `6000.3.26f1`, URP. Unity Editor bu bulut ortamında çalışmaz (indirme engelli). Doğrulama:
  - `dotnet test tests-dotnet` → `Assets/_Pofi/Scripts/Logic` (Unity'siz saf C#, `noEngineReferences`) + `Assets/Tests/EditMode/Logic`. C# 9 ile sınırlı yaz (Unity ile aynı).
  - Unity derleme/test: GitHub Actions + GameCI (`.github/workflows/ci.yml`). WebGL çıktısı `webgl-preview` dalına yazılır; Claude bunu çekip Artifact olarak yayınlar (kullanıcı iPhone Safari'de açar).
- "Kod olarak proje": sahne, URP varlıkları ve oyuncu ayarları `Assets/_Pofi/Editor/ProjectSetup.cs` ile her derlemede kurulur. Elle düzenlenmiş Unity YAML'ına güvenme.
- Mantık (göstergeler, ekonomi, seviye, görev durumları, kıyafet uyumu …) mümkün olduğunca `Pofi.Logic` içinde ve birim testli olsun; Unity katmanı ince kalsın.
- 3D: Blender `bpy` (PyPI) betikleri `art/scripts/`. Nihai karakterler yapay zekâ 3D + temizlik ile gelecek. Referans görsellerdeki karakterleri kopyalama (telif).
- Konsept inceleme sayfası (Artifact): https://claude.ai/artifact/9DqKTtEM6TBj1G8uNtJPQo — kaynak `docs/art/`; aynı URL'ye yeniden yayınla.
- Bash'te `pkill -f`/`pgrep -f` desenini aynı komut satırında başka işle birleştirme: kendi kabuğunu da öldürür (çıkış kodu 144).
- **Oyun önizlemesi (iPhone):** https://claude.ai/artifact/QVTuwRzPRzMgAnhQxoh9ye — CI bitince `bash tools/preview/pack.sh <scratchpad>/onizleme` ve aynı dosya yolundan/URL'den yeniden yayınla (files: Build/*.wasm + loader.js). İlk WebGL derlemesi ~45 dk sürdü (önbellekle kısalır).
- Kullanıcı tercihi (13 Ekim 2026): her adımda önizleme yayınlama; fonksiyon geliştirmeye devam et. Önizleme yalnızca kullanıcı isteyince ya da büyük bir aşama bitince. 3D üretim aracı kararı kullanıcıyla birlikte verilecek.
- 3D üretim kararı (14 Ekim 2026): **Meshy** (kullanıcı üyelik alıyor). Erişim: ağ izni `api.meshy.ai` + `assets.meshy.ai`, anahtar ortam sırrı `MESHY_API_KEY` (sohbete asla). Önce pilot: Pofi + palmiye + küçük ada parçası oyunda → onay → tüm üretim. Kullanıcının kalite referansları ticari oyunlara ait olabilir: yalnızca hedef kalite/hava; yapay zekâ aracına yüklenmez, kopyalanmaz.
- Ekran yönü kararı (14 Ekim 2026): **YATAY** (telefon yan). Arayüz görselleri ve yerleşimler yataya göre. Pet konseptleri onaylandı (art/meshy/out/pet_XX/concept_*.png); Tosbi (pet_07) şimdilik bu haliyle, kredi kalırsa sırt kabuklu yeniden üretilecek.
- İletişim dili (14 Ekim 2026): kullanıcıyla **Türkçe** yaz.
- Ada gezme kararı (14 Ekim 2026): **dokun-yürü + kuşbakışı**. Pet adada yürür (yere dokun → oraya yürür, binaya dokun → kapısına gidip girer, kamera arkadan-yukarıdan takip eder); hızlı geçiş için kuşbakışı harita kalır. Ada köy gibi gezilecek kadar büyük, yapılar aralıklı; zemin gerçekçi (engebe, kumsal, tepe, patika) — prosedürel arazi + Meshy süsleri. P1 sanat onaylandı; P2 (kıyafet/ev eşyası) devam.
- Arayüz kararı (14 Ekim 2026, taslaklar onaylı): panel/alt menü yok; ana merkez ada. Sahne üstünde süzülen 3B "şeker" düğmeler.
  Sol üst pet rozeti + 4 gösterge halkası; sağ üst coin, Harita (kuşbakışı), Görev kısayolu; sol kenar Besle/Yıka (her yerde, yiyecek yoksa dükkâna koşar);
  sol alt yüzen joystick + dokun-yürü birlikte; sağ alt tek bağlamsal eylem tuşu (Zıpla/Gir/Topla/Oyna); eğilme yok.
  Topla, uyku, süsleme evde ("Evim" iç mekân). Giydirme: pete dokununca ve dükkânda. Oyun yerlerinin üstünde "▶ Oyna". Dükkân ürünleri tezgâhta süzülen baloncuklar.
  Hedef: 6-15 yaş için basit ama profesyonel; amaçsız tuş/özellik yok.
- Görsel gerçekçilik (14 Ekim 2026, onaylı sıra): önce KREDİSİZ deniz (dalga, parıltı, sığ turkuaz, kıyı köpüğü), kum (tepecik, rüzgâr çizgisi, ıslak kum), çim telleri, ışık; sonra kumsal objeleri için simge sayfası ön çalışması (~18 kredi) → onay → lite 3D (~260–320 kredi).
  **Işık uyarısı (kullanıcı):** ekran parlamasın, renkler uçuk/soluk olmasın; canlı ama dengeli, net gölge. Kullanıcının kumsal örnek görselleri yalnız hava/kalite hedefi (yapay zekâya yüklenmez, karakterler kopyalanmaz).
- Geri bildirim 3 kararları (14 Ekim 2026):
  - **Gece döngüsü kapalı** (`PetCare.NightCycle = false`): gökyüzü hep gündüz, "uyuyor" engeli yok; gece/gündüz koleksiyonları her zaman bulunur.
  - Kontrol: **sol yarı joystick, sağ yarı görünmez kamera döndürme** (iki başparmak aynı anda); otomatik kamera takibi yavaş, yalnız ileri giderken.
  - **Görev (sağ üst) = oyun içi seviye görevleri** (yıldız/XP). Ebeveynin gerçek görevleri adadaki panoda: **"Ev Görevleri"** (19 Ekim 2026, kullanıcı; eski geçici ad "Quests").
  - Önizlemede **Test erişimi**: Evim → Ayarlar → "Test: her şeyi aç" (en üst seviye, tüm eşyalar, 5000 coin; yalnız sahte arka uçta).
  - İpucu paneli üst şeritte, cümleler kısa.
- Geri bildirim 4 (15 Ekim 2026):
  - Meshy pet klipleri 10 sn, hareket yalnız başta (yürüme 2–27. kare): içe aktarıcı kırpar (`PofiArtImporter.ClipFrames`, ölçüm `art/scripts/anim_ranges.py`).
  - Tanıtım ipuçları sıralı (`MapScreen.Hud.TipSeq`, panelde adım/toplam); bağlamsal olanlar araya girer.
  - Kodla üretilen 3B arayüz görselleri: `art/scripts/ui_games.py` → `Resources/Games/`, `art/scripts/keyart.py` → festival arka planı (`Resources/Art/`) ve yükleme ekranı (`tools/preview/keyart.jpg`).
    ⚠️ HATIRLAT: yükleme ekranı görseli geçici; kullanıcı kontrol edecek.
  - Arka plan müziği kodla bestelendi (`art/scripts/music_island.py`, telifsiz); aç/kapa her ekranda sağ üst ♪.
  - M4 UYGULANDI (15 Ekim 2026): SQL Supabase'de (iş akışı "Supabase M4 uygula"), ParentApp eklemeleri parent-app dalına gönderildi ve Expo Go önizlemesine yayınlandı. Oyun gerçek sunucuya `SUPABASE_PUBLISHABLE_KEY` secret'ı ile bağlanır; deneme kodları sahte arka uçta kalır.
- Görsel stil kararı (15 Ekim 2026): hedef = boyalı/maket hissi veren ada (yumuşak toon ışık, dış çizgi yok, kıyı köpüğü, ışık hüzmesi, çiçekli çimen) + yumuşak "vinyl oyuncak" karakter/eşya. Referanslar (I Just Wanted to Fish ekranları, Behance vinyl) yalnız stil/teknik ilham; hiçbir şey kopyalanmaz, yapay zekâya yüklenmez.
  Üretim **bulutta betikle** (Blender bpy + Unity C#/CI); Blender MCP / Unity MCP kurulmaz (gereksiz + güvenlik açığı). Kamera şimdilik mevcut haliyle kalır.
  **Dış çizgi YOK** (kullanıcı, 15 Ekim): karakter/nesne çevresinde çizgi kullanılmaz (Pofi/Toon'un çizgi geçişi kapalı).
  Kodla 3D: `art/code3d/` (kit.py ortak araçlar; `export_palette_fbx` → tek mesh + palet dokusu, Unity'de `Resources/Env/g_*`; LOW = oyun çokgen bütçesi).
- Geri bildirim 5 (15 Ekim 2026) — hedef: yeni büyük özellik değil, tasarım + mevcut işlevleri iyileştirme:
  - Adım sesi yürüyüşe senkron (`PetWalker.Footsteps`, temas: yürüme 0.22/0.72, koşu 0.40/0.90); titreşim `Audio.Haptics` (jslib; iOS 18 switch hilesi).
  - Müzik ham PCM (`Resources/Audio/music_island_pcm.bytes`): WebGL ses çözücüsüne gerek yok; index.html `navigator.audioSession.type='playback'` (sessiz düğmesi).
  - Ada aksiyonları (`Logic/Island/Gathering`, `MapScreen.Gather`): kütük (balta, 3 vuruş) → odun, çalı (el) → dal, taş (kazma) → taş; "Kulübe yap" (6 odun, 4 dal, 3 taş).
    Nesne üstü alet baloncuğu + eylem düğmesi simgesi değişir; yeni aksiyonlar aynı yapıya eklenecek.
- Görsel yenileme ONAYLANDI ve uygulandı (15 Ekim 2026): tüm yapı/süs/ev eşyası modelleri kodla (art/code3d: assets_v3, assets_town, assets_items, house_cottage);
  oyuna `python3 art/code3d/export_game.py [ad]` ile (üçgen bütçesi + pişirilmiş doku, eski Meshy dosyaları silinir). Env modelleri orijinden zemine oturur (RealAssets.Footprint).
  Ortak eskime: `assets_v3.weather/_G`, ahşap/halat/demir/kumaş (assets_town). Kıyafetler ve petler Meshy'de kalır (iskelet/soket bağlı).
- iOS/TestFlight hattı: `.github/workflows/ios.yml` (commit mesajında `[ios]` ya da elle), `docs/TESTFLIGHT.md` (kullanıcının eklemesi gereken secret'lar).
- **Ortak kaynak (19 Ekim 2026): `amy60946/ortak`** — üç uygulamanın (Pofi Adası, ParentApp, ClinicApp) tek doğruluk kaynağı: Supabase göçleri, RPC'ler, durum adları, coin/XP/seviye kuralları, karar günlüğü (`DURUM.md`). Her işten önce `ortak/CLAUDE.md`, `ortak/DURUM.md` ve ilgili `ortak/sozlesme/*` okunur. Ortak bir şey değişecekse önce `ortak` (SQL `proposed/` + test + sözleşme + DURUM satırı), sonra bu uygulama. Bu depodaki `supabase/` klasörü eski kopyadır. Oturum sonunda `ortak/DURUM.md`'ye bir satır.
  Pencereler: "Oyun" (bu depo + ortak), "Ebeveyn" (parent-app + ortak), "Klinik" (clinic-app + ortak).
- iOS imzası (19 Ekim 2026, kullanıcı onaylı): macos-15 + Xcode 26 zorunlu; arşiv otomatik geliştirme imzası (`tools/ci/asc_device.py`), dışa aktarma elle App Store dağıtım imzası (`tools/ci/asc_sign.py`, geçici sertifika + profil, iş sonunda iptal). Xcode bulut imzası "Invalid Signature" verdi; kullanılmaz.
- İki ayrı uygulama (16 Ekim 2026): **Pofi Adası** (çocuk, `com.gameapp.ios`) ve **ParentApp** (yalnız ebeveyn, `com.parentapp.ios`; çocuk kod ekranı kaldırıldı). Sunucu/işlevler aynı. ParentApp TestFlight: `parent-app/.github/workflows/ios-testflight.yml` (macOS: expo prebuild + xcodebuild), `parent-app/docs/TESTFLIGHT.md`.
- Adlandırma (kullanıcı, 16 Ekim 2026): **"Fidan" adı hiçbir yerde kullanılmaz** (taslak addı). Ebeveyn uygulaması = **ParentApp**, oyun = **GameApp** (mağaza adı Pofi Adası). Bundle ID: GameApp `com.gameapp.ios`, ParentApp `com.parentapp.ios`; SKU `gameapp`, `parentapp`; ParentApp şeması `parentapp://`, Expo projesi `parentapp`.
- İş modeli kararı (19 Ekim 2026, "Joon iş modeli kanvası" dokümanı): gelir **hem aile aboneliği hem klinik/uzman kanalı**. Üç ürün canlıya alınacak: Pofi Adası (çocuk, ücretsiz "çekiş motoru"), ParentApp (aile aboneliği), klinik SaaS (web + ayrı uygulama, klinisyen başına ücret; ParentApp'in sade tasarım dilini izler). Üçü aynı Supabase'e bağlı. Raporlama iki okuyucuya (ebeveyn + uzman) yazılır; gizlilik onayı buna göre kapsanır.
  Referans dokümanlar (Claude Docs, kullanıcının projesinde, takip ediliyor): Joon iş modeli kanvası https://claude.ai/code/artifact/df7eafa7-1e1e-4014-8a5f-7d88cb985485 · Pofi Adası oyun omurgası analizi https://claude.ai/code/artifact/3c82704c-e120-4d73-ba9f-a7ffdc75eeac. Ürün geliştirme bu çıktılar ışığında; Joon yalnız iş modeli/rakip referansı (içerik, karakter, metin kopyalanmaz).
- Yaş bantları (19 Ekim 2026, kullanıcı): **A 6–8 / B 9–12 / C 13–15** (ortak/sozlesme/durumlar.md §4). Bant yalnız zorluk/arayüz; raporlar gerçek yaşı (ebeveynin girdiği doğum günü) kullanır. Mağaza: Kids Category dışı, 4+, çocuk kurallarına gönüllü uyum; yaş çocuktan sorulmaz.
- Omurga Ö1 + Ö2 + Ö5 onaylandı (19 Ekim 2026): **Güneş Taşı** (yalnız ebeveyn onayıyla; kolay 1 / orta 2 / zor 3; harcanmaz, `Resources/Data/sun_spots.json` onarım noktalarına sırayla yerleştirilir ve o bölge/oyun seviye yerine taşla açılır; `Logic/Island/SunStones.cs`), gerçek görev XP'si 20/35/50 + beceri yıldızı (`Logic/Tasks/RealTaskRewards.cs`, 6 beceri), ilk gün akışı (`Logic/App/FirstDay.cs`: hikâye → pet → yürü → besle → Ev Görevleri → Yaptım → onay → ilk sis; en geç 24 saat, eski oyuncu görmez). Sunucu tarafı ortak `migrations/20261019030000_sun_stones.sql` (uygulandı 19 Ekim 2026).
  Sıradaki (onay bekleyen): Ö3 bakım, Ö4 hikâye bölümleri, Ö6 posta kutusu, Ö7 gerçek ödül dükkânı, Ö8 ölçüm/rapor. Sis/onarım noktalarının 3B görseli henüz yok (kilitli bölge gri + "N Güneş Taşı" etiketi).
- Araştırma belgelerinin takibi bu pencerede (19 Ekim 2026): Joon iş modeli kanvası + oyun omurgası analizi; güncelleme ve Claude'a gönderilen yorumlar bu oturumu uyandırır.
- Görsel v3 ONAYLANDI ve uygulandı (19 Ekim 2026): simge ve arayüz parçaları Meshy (nano-banana-pro, 3x3 sayfa = 9 kredi) — `art/meshy/out/ui_v3_{a..e}`, kurulum `python3 art/meshy/install_ui_v3.py` (BALOO_VAR=Baloo2 değişken yazı tipi yolu verilirse yazı tipini de kurar).
  Resources/Icons (eski adlarla, kod değişmeden) + Resources/UI (çubuk, düğme renkleri, krem kart, yuvarlak düğme, şerit, tahta; `UI/Skin.cs` 9 dilimli, yoksa eski kodla çizim). Yazı tipi Baloo 2 ExtraBold (OFL, Resources/Fonts). Eşya simgeleri zaten aynı kalitede: yeniden üretilmedi (kredi korundu).
  Kalan Meshy kredisi: 889 (yeni simge gerekirse sayfa başına 9). Ada sahnesi/sis taslağı `art/mockups/` (oyuna henüz girmedi).

- Rehberli zincir + iyileştirmeler (19 Ekim 2026, kullanıcı onayı; omurga analizi §11): `Logic/App/Guide.cs` — Sv1–3 için 12 adım
  (besle, yıka, Evim'e gir, evi topla, aksesuar tak, Ev Görevleri panosu, malzeme topla, kulübe, hindistan cevizi oyunu, dükkândan al,
  Güneş Taşı yerleştir, kart oyunu). Adımlar `RecordActivity` sayaçlarıyla ilerler; ödül yalnız canlı yapılan adıma. Belgedeki bahçe/balık
  adımları Sv6/Sv7 içerik olduğu için ilk 3 seviyede hindistan cevizi/dükkân/kart oyunu ile değiştirildi.
  İpucu paneli artık ALT şeritte; "Kuşbakışı" düğmesi = "Harita"; bölge düğmesi (Gir/Oyna) yapının her kenarından açılır;
  Güneş Taşı bölgelerinde yer sisi (`Clouds.Spawn(..., fog:true)`); bahçe ekranı v3 görünüm; zemin/çim tonları sakin.
  ⚠️ HATIRLAT: kullanıcı "filtreleme sistemi" için ek geri bildirim verecek (19 Ekim 2026) — gelince sor/uygula.
  Seedance/Higgsfield kullanılmadı (bu ortamda erişim/anahtar yok); animasyonlar kodla. Meshy kredisi en az 100 kalmalı (kullanıcı kuralı).
- **Tek pet Okti** (20 Ekim 2026, kullanıcı): ahtapot `pet_13`, üç evre ayrı Meshy modeli (web sitesinden: çocuk → `Pets/pet_13_yavru`, ergen → `_genc`,
  yetişkin → `_yetiskin`; `RealAssets.StageModel`). Dönüştürme: `art/meshy/scripts/prepare_stages.py <glb> Assets/_Pofi/Resources/Pets <ad>`
  (7 klip: idle, walk, run, happy, wave, sleep, jump; kırpılmaz; ayak temasları `PetWalker.ModelContacts`). Diğer 12 pet `retired`
  (pets.json): seçimde yok, eski kayıt Okti'ye geçer (`Logic/App/PetRoster`), kart oyununda rakip olarak kalır.
  Meshy web dosyaları: kullanıcı indirme bağlantısını (assets.meshy.ai) sohbete yapıştırır, Claude indirir; GitHub tarayıcı yüklemesi 25 MB sınırına takıldı.
- Güneş Taşı adada yerleştirilir (20 Ekim 2026, kullanıcı): sisli bölgeye (köprü, mağara yolu, fener…) yaklaşınca eylem tuşu "Taşı koy";
  Ev Görevleri panosunda yalnız "Adaya götür". Ayarlar düğmesi müzik düğmesinin solunda, aynı boyda; yan düğmeler kenara yakın.
