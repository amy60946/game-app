# İlerleme

Son güncelleme: 13 Ekim 2026. M0 tamam (Unity derlemesi + iPhone önizlemesi). M1–M2 dikey dilim yazıldı, CI'da derleniyor.
Doğrulama: `dotnet test tests-dotnet` → 118 test; `tools/compile-check/run.sh` → Unity katmanının hızlı derleme denetimi (Unity'siz); kesin doğrulama GitHub Actions + GameCI.

## Unity katmanı (`Assets/_Pofi/Scripts/Runtime`) – M1–M2 dikey dilim

| Ekran / parça | Dosya | Durum |
|---|---|---|
| Uygulama kökü, ekran akışı (`Logic/App/AppFlow`), kayıt (PlayerPrefs) | `Core/GameBootstrap.cs`, `Core/PrefsStore.cs` | yazıldı |
| Kodla giriş (Mock; deneme kodları ekranda) | `Screens/LoginScreen.cs` | yazıldı |
| Yaş bandı teması (A iri/yuvarlak, B dengeli, C sade) | `UI/Theme.cs`, `UI/Ui.cs` | yazıldı |
| 12 yer tutucu pet + soketler, 360° çevirme, zıplama | `World/PetModels.cs`, `World/Stage.cs` | yazıldı |
| Pet karuseli + son onay | `Screens/PetSelectScreen.cs` | yazıldı |
| İsim verme + filtre, hoş geldin hediyesi (öneri) | `Screens/PetNameScreen.cs`, `Data/start.json` | yazıldı |
| Ev: 4 gösterge, besle/yıka/oyna/topla, gece, ebeveyn kapısıyla çıkış | `Screens/HomeScreen.cs` | yazıldı |

## Yazılan oyun mantığı (`Assets/_Pofi/Scripts/Logic`)

| Alan | Gereksinim | Dosya | Durum |
|---|---|---|---|
| Kodla giriş, hatalı deneme beklemesi, iptal algılama | FR-AUTH-1..4, FR-SAFE-5 | `Auth/`, `Services/Mock/MockAuthService.cs`, `Services/Supabase/SupabaseAuthService.cs` | ✅ (Supabase'e karşı canlı test, Unity derlemesinden sonra) |
| Yaş bandı profilleri | §2, FR-VOICE-2, FR-ECO-4 | `Profile/AgeBand.cs` | ✅ |
| Oyun verisi (12 pet, 49 eşya, seviyeler, koleksiyon, rozetler, günlük görevler) | veri odaklı | `Resources/Data/*.json`, `Data/` | ✅ + doğrulama testi |
| Pet göstergeleri, azalma, taban, günlük sınır | FR-PET-3 | `Pet/PetStats.cs` | ✅ |
| Bakım eylemleri, gece uykusu | FR-PET-4, FR-ISL-2 | `Pet/PetCare.cs` | ✅ |
| Pet ismi + uygunsuz kelime filtresi | FR-PET-2, FR-SAFE-5 | `Pet/PetName.cs`, `Data/name_blocklist.json` | ✅ |
| Seviye 1–15, açılış tablosu, büyüme evreleri | FR-PROG-1..3, FR-PET-5 | `Progression/` | ✅ |
| Cüzdan (sunucu esaslı), çevrimdışı harcama kuyruğu | FR-ECO-1, FR-ECO-3 | `Economy/Wallet.cs` | ✅ |
| XP + günlük sınır, görev serisi | FR-ECO-2, FR-ECO-4, FR-TASK-6 | `Economy/XpSystem.cs` | ✅ |
| Fiyat dengesi | FR-ECO-5 | test: `BalanceLocalizationTests` | ✅ (akvaryum fiyatı düzeltildi) |
| Dükkan, envanter, kıyafet uyumu | FR-SHOP-1..3a, FR-PET-7 | `Shop/`, `Cosmetics/` | ✅ (her eşya × her pet testi) |
| Gerçek görevler, durum geçişleri, senkron | FR-TASK-2,3,5,7 | `Tasks/` | ✅ |
| Kayıt + şema göçü, senkron koordinatörü | kabul 6 | `State/` | ✅ (uçtan uca test) |
| Masa oyunları altyapısı + Renk Eşle, Domino, Kule + botlar | FR-CARD-1..4 | `Cards/` | ✅ (yüzlerce bot-bot oyunu) |
| Mini oyunlar: ceviz, Pet'e yardım, yüzme/sörf/kayak | FR-MINI-1..3 | `MiniGames/` | ✅ |
| Bahçe, balık tutma, koleksiyon, rozetler, günlük görevler | FR-MINI-4,5, FR-META-1..3 | `Garden/`, `Fishing/`, `Meta/` | ✅ |
| Ebeveyn kapısı | FR-SET-1 | `Safety/ParentGate.cs` | ✅ |
| Karaoke altyazı, viseme zamanlaması | FR-VOICE-1, FR-VOICE-4 | `Audio/Subtitles.cs` | ✅ (ses dosyası yokken tahmini) |
| Türkçe metin tablosu + ek uyumu | §2 | `Resources/Data/tr.json`, `Core/TurkishSuffix.cs` | ✅ |

## Henüz yok
- **Unity katmanı (görünen her şey):** ekranlar, 3D sahne, animasyon, ses, dokunma. Lisans gelince başlar.
- **Mağara ve dağ mini oyunları, festival, fener (Sv 11–15 içeriği):** M10.
- **Sunucu tarafı (Supabase):** yaş bandı sütunu, yeni görev durumları, coin defteri, `spend_coins` / `child_tasks` / oyun kaydı fonksiyonları. Ebeveyn uygulamasına dokunduğu için kullanıcı onayıyla M4'te.
- **Gerçek modeller ve ses:** yapay zekâ 3D + stüdyo.

## Kullanıcıya sorulacaklar
- UNO ve Jenga tescilli markalar: oyunda "Renk Eşle" ve "Kule" adları kullanılıyor (onaylandı, 13 Ekim 2026).
