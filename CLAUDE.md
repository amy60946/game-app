# Pofi Adası — Claude için çalışma notları

- Kullanıcı yazılımcı değil. Türkçe, sade dille, adım adım ve nereye tıklayacağını söyleyerek anlat. Şifre/anahtar/lisansı sohbete yapıştırmasını ASLA isteme; GitHub Secrets'a eklenir.
- Plan ve kararlar: `docs/PLAN.md` (onaylandı, 13 Ekim 2026). Kapsam dışına çıkma; öneriler not olarak yazılır ve sorulur. Belirsiz kararda tahmin etme, kısa soru sor.
- Ebeveyn uygulaması (Fidan, Expo) ayrı depoda: `amy60946/parent-app` (`docs/DURUM.md`). Arka uç ortak Supabase projesi.
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
