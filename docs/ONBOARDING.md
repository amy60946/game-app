# Tanıtım (onboarding) ipuçları

Kullanıcı isteği (14 Ekim 2026, geri bildirim madde 7 ve 11): çocuk her işlevi ilk karşılaştığında ekranda **hareketli bir dokunma izi**
(parmak ucu) hareketi 3 kez gösterir, üstte **iri altyazı** açıklar. Sonra bu altyazılar **seslendirilecek** (ses kimliği tabloda).

İlkeler
- Aynı anda tek ipucu. Her ipucu bir kez tamamlanır (`GameState.SeenTips`); çocuk hareketi yapınca kaybolur.
- İpucu girdiyi engellemez: çocuk ipucu sürerken hareketi yapabilir.
- Hareket türleri: **Dokunma** (hedefte iki kez basar), **Sürükleme** (başlangıçtan hedefe gider), **Kaydırma** (ekranda kayar).
- Altyazılar 6–15 yaş için kısa, emir kipinde, pet adıyla kişisel. Ekran parlamaz; balon beyaz, turuncu kenarlı.
- Kod: `Logic/App/Onboarding.cs` (liste, kural, testli), `UI/Coach.cs` (gösterim), ekranlar (tetikleyici ve tamamlanma).

| # | Kimlik | Ekran | Hareket | Ne zaman | Tamamlanır | Altyazı (tr.json) | Ses kaydı |
|---|---|---|---|---|---|---|---|
| 1 | `walk` | Ada | Kaydırma: parmak ekranın ortasından yukarı kayar (3 kez) | Adaya ilk giriş | Pet joystick ya da dokunmayla yürüdü | Ekrana dokun ve parmağını kaydır: {0} o yöne yürür! | `vo_tip_walk` |
| 2 | `jump` | Ada | Dokunma: sağ alttaki yeşil eylem tuşu | Yürüme öğrenildikten 6 sn sonra, tuş "Zıpla" iken | Zıpla tuşuna basıldı | Yeşil tuşa bas, {0} zıplasın! | `vo_tip_jump` |
| 3 | `enter` | Ada | Dokunma: yeşil eylem tuşu ("Gir") | İlk kez bir kapının önünde | Gir tuşuna basıldı | Kapının önündesin! Yeşil tuşa bas, içeri gir. | `vo_tip_enter` |
| 4 | `play` | Ada | Dokunma: yeşil eylem tuşu ("Oyna!") | İlk kez bir oyun yerinin kapısında | Oyna tuşuna basıldı | Burada oyun var! Yeşil 'Oyna' tuşuna bas. | `vo_tip_play` |
| 5 | `feed` | Ada (Besle tepsisi) | Sürükleme: tepsideki ilk yiyecekten petin üstüne (3 kez) | Besle tepsisi ilk açılış; ayrıca yiyeceğe yalnız dokunulursa yeniden | Yiyecek pete sürüklenip bırakıldı | Yiyeceği basılı tut ve {0} üstüne sürükle! | `vo_tip_feed` |
| 6 | `wash` | Ada (Yıka tepsisi) | Sürükleme: sabundan petin üstüne (3 kez) | Yıka tepsisi ilk açılış; sabuna yalnız dokunulursa yeniden | Sabun pete sürüklenip bırakıldı | Sabunu basılı tut ve {0} üstüne sürükle, köpürt! | `vo_tip_wash` |
| 7 | `tasks` | Ada | Dokunma: sağ üstteki bayrak (Görev) | Adada 20 sn geçince | Görev düğmesine basıldı | Gerçek görevlerini yap, coin kazan! Bayrağa dokun. | `vo_tip_tasks` |
| 8 | `xp` | Ada | Dokunma: sol üstteki yıldız rozeti ve XP çubuğu | İlk XP kazancında ("+N ★" süzülür) | 6 sn gösterildi | Yıldız topla, büyü! Oyun oyna, görev yap, parıltı bul: her biri yıldız verir. Çubuk dolunca seviye atlarsın. | `vo_tip_xp` |
| 9 | `wardrobe` | Ada | Dokunma: petin üstü | Giyilebilir bir eşya sahibi olunca | Pete dokunuldu (giydirme açıldı) | {0} üstünü değiştirmek için ona dokun! | `vo_tip_wardrobe` |
| 10 | `sparkle` | Ada | Dokunma: parıltının üstü | 14 m yakında parıltı varken | Parıltı toplandı | Parıltıyı gördün mü? Yanına git ve topla! | `vo_tip_sparkle` |
| 11 | `overview` | Ada | Dokunma: Kuşbakışı düğmesi | Görev ipucundan sonra, adada 45 sn | Kuşbakışı açıldı | Haritayı aç: dokunduğun yere hemen gidersin. | `vo_tip_overview` |
| 12 | `shop` | Dükkân | Dokunma: tezgâhtaki ürünler | Dükkân ilk açılış | Bir ürün seçildi | Bir ürüne dokun, sonra 'Al'a bas. | `vo_tip_shop` |
| 13 | `wardrobe_spots` | Giydirme | Dokunma: petin kafasındaki nokta | Giydirme ilk açılış | Bir yuva noktası seçildi | Noktalara dokun: şapka, gözlük, tişört, çanta! | `vo_tip_wardrobe_spots` |
| 14 | `home` | Evim | Dokunma: Topla düğmesi | Evim ilk açılış | Topla'ya basıldı | Evini toplamak için Topla'ya bas! | `vo_tip_home` |

`{0}` yerine petin adı gelir (gerekirse ek ile: "Pofi'nin").

## İlk gün akışı (Ö5, 19 Ekim 2026)

`Logic/App/FirstDay.cs`. Yeni oyuncu ilk gün yalnız şu sırayı görür; diğer ipuçları (bak, zıpla, giydir, Görev, kuşbakışı, parıltı) akış bitince kendi yerlerinde açılır.

1. **Hikâye kartı** (pet seçiminden önce): ada sisle kaplı, görevler Güneş Taşı kazandırır.
2. Pet seç ve isim ver.
3. **Yürü** → **Besle**.
4. **Ev Görevleri panosuna git** (pano üstünde parmak).
5. Panoda **Yaptım** (ilk yapılacak görevde parmak).
6. Beklerken: "Posta güvercini yolda… Beklerken Hindistan Cevizi oyna!".
7. Onay gelince taş gelir → panodaki **Yerleştir** → ilk sis kalkar, Yüzme Koyu açılır.

Akış biter: ilk taş yerleşince, panoda görev yoksa ya da ilk açılıştan 24 saat geçince. Pet'i olan eski oyuncular akışı görmez.
ParentApp tarafı (öneri, ParentApp penceresi): kurulumda yaşa göre "ilk gün paketi" (3 görev) ve ilk "Yaptım"da ebeveyne anında bildirim.

## Görevler penceresi tanıtımı (C + D, 24 Ekim 2026)

Görevler penceresi tek pencere, iki bölüm (solda altın Ev Görevleri, sağda mavi Oyun görevleri). Kalabalık görünmesin diye ilk
açılışta bilgilendirme eli sırayla anlatır (`Screens/TasksScreen.cs` → `QueueIntro`; sıra `Onboarding.TasksIntro`). Her adım
dokununca ya da el iki tur gösterip ~5 sn geçince biter; altyazıda "1/3" sıra rozeti.

| Kimlik | Hedef | Altyazı (tr.json) | Tamamlanır |
|---|---|---|---|
| `tasks_home` | altın "Ev Görevleri" başlığı | Ailenden gelen görevler burada. Yapınca Güneş Taşı kazanırsın! | gösterildi / dokunuldu |
| `tasks_done` | ilk "Yaptım" (yapılacak görev varsa) | Yaptın mı? Yaptım'a bas, Mavi ailene götürsün. | gösterildi / dokunuldu / Yaptım'a basıldı |
| `tasks_game` | mavi "Oyun görevleri" başlığı | Oyun görevleri yıldız verir. Hepsini bitir, sandığı aç! | gösterildi / dokunuldu |
| `stone` (var olan) | "Adaya götür" (yerleştirilecek taş varsa) | Taşı adaya götür: {0}! | ilk taş adada yerleşince |

İlk gün `mark` ipucu bu pencerede `tasks_done` ile birleşir: `tasks_done` görüldükten sonraki açılışlarda, ilk gün "Yaptım"
adımındaysa eski `mark` ipucu (sesli) yine ilk "Yaptım"ı gösterir. Yeni cümlelerin ses kaydı henüz yok (`build_voice.py` ile eklenir).

## XP (yıldız) nasıl anlatılıyor (madde 11)
- Sol üstte seviye rozetinin altında **XP çubuğu**: dolunca seviye atlanır.
- XP kazanılınca rozetin yanında **"+N ★"** yukarı süzülür.
- İlk XP'de `xp` ipucu: "Yıldız topla, büyü! Oyun oyna, görev yap, parıltı bul: her biri yıldız verir. Çubuk dolunca seviye atlarsın."
- XP kaynakları: mini oyunlar, masa oyunları, balık tutma, bahçe, günün görevleri, görev serisi, rozetler, keşif parıltıları.

## Sonraki adımlar (öneri)
- Seslendirme: tablodaki `vo_tip_*` satırları kayıt listesidir; ses gelince altyazıyla eşzamanlı çalınır (karaoke altyazı altyapısı hazır).
- El görseli: şimdilik parmak ucu (beyaz yuvarlak + halka). İstenirse bir sonraki simge sayfasında 3B "işaret eden el" üretilebilir (~2 kredi payı).
- Diğer ekranlar (bahçe, balık, mini oyunlar, masa oyunları) için de aynı kalıpla ipucu eklenecek.
