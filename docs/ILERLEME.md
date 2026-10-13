# İlerleme

Son güncelleme: 13 Ekim 2026. M0 tamam. M1–M10 oyun ekranları yazıldı (yer tutucu görsellerle); Unity derlemesi CI'da doğrulanıyor.
Doğrulama: `dotnet test tests-dotnet` → 140 test; `tools/compile-check/run.sh` → Unity katmanının hızlı derleme denetimi (Unity'siz); kesin doğrulama GitHub Actions + GameCI.

## Unity katmanı (`Assets/_Pofi/Scripts/Runtime`)

Tüm ekranlar koddan kurulur (sahne dosyası yok). Petler ve eşyalar şimdilik yer tutucu şekiller; gerçek modeller sanat hattından gelecek.

| Milestone | Ekran / parça | Dosya | Durum |
|---|---|---|---|
| M1 | Uygulama kökü, ekran akışı, kayıt (PlayerPrefs), kodla giriş (sahte arka uç), yaş bandı teması | `Core/`, `UI/`, `Screens/LoginScreen.cs` | ✅ Unity'de derlendi + test |
| M2 | 12 yer tutucu pet + soketler, karusel, isim, ev, 4 gösterge, gece | `World/PetModels.cs`, `Screens/PetSelect·PetName·HomeScreen.cs` | ✅ Unity'de derlendi |
| M3 | Dükkan (kilit, uyum, satın alma), dolap/giydirme, kıyafet yer tutucuları | `Screens/Shop·WardrobeScreen.cs`, `World/CosmeticModels.cs` | yazıldı |
| M4 (oyun tarafı) | Görev panosu (Yaptım/Yapamam/Geri al), senkron, coin kutlaması, **deneme ebeveyn paneli** | `Screens/TasksScreen.cs`, `UI/CoinBurst.cs` | yazıldı (Supabase bağlantısı M4 sunucu işinde) |
| M5 | 3B ada haritası (kaydır, dokun, kilit, "Yeni!"), seviye kutlaması | `World/MapWorld.cs`, `Screens/MapScreen.cs`, `Screens/LevelUpCelebration.cs` | yazıldı |
| M6 | Ceviz Yakala, Pet'e Yardım, Yüzme/Sörf/Kayak | `Screens/MiniGameScreen.cs` | yazıldı |
| M7 | Bahçe, balık tutma, koleksiyon defteri, rozetler, günlük görevler, haritada keşif parıltıları | `Screens/Garden·AlbumScreen.cs` | yazıldı |
| M8 | Oyun Kulübesi: Renk Eşle, Domino, Kule (bot pete karşı) | `Screens/CardsScreen.cs` | yazıldı |
| M9 (kısmi) | Ayarlar (ses, yazı boyutu, hareketi azalt, pet değiştir, çıkış), kodla üretilen ses efektleri | `Screens/SettingsScreen.cs`, `Audio/Sfx.cs` | yazıldı (seslendirme/altyazı: ses kaydı gelince) |
| M10 (içerik) | Mağara Keşfi, Dağ Yürüyüşü, Festival, Fener finali; ev süsleme (FR-ISL-3) | `Screens/EventScreen.cs`, `Screens/DecorateScreen.cs` | yazıldı |

Önizleme ve otomatik test: `GameBootstrap.PofiDebug` (yalnızca sahte arka uçla) tarayıcıdan `unityInstance.SendMessage("Bootstrap","PofiDebug","login A1A1A1")`.

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
- **Gerçek 3D modeller, animasyon, seslendirme:** sanat hattı (yapay zekâ 3D aracı kararı bekleniyor).
- **Cila, performans/bellek ölçümü, mağaza hazırlığı:** M10 sonu.
- **Sunucu tarafı (Supabase):** öneri hazır ve yerelde testli (`docs/M4_SUNUCU_ONERISI.md`, `supabase/proposed/`, `supabase/test/run.sh` → 38 kontrol). Ortak veritabanına uygulanması kullanıcı onayı bekliyor.
- **Gerçek modeller ve ses:** yapay zekâ 3D + stüdyo.

## Kullanıcıya sorulacaklar
- UNO ve Jenga tescilli markalar: oyunda "Renk Eşle" ve "Kule" adları kullanılıyor (onaylandı, 13 Ekim 2026).
