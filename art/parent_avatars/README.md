# Ebeveyn avatarları (Okti anne / baba) — TASLAK

ParentApp penceresinin isteği (27 Ekim 2026, kullanıcı: "Okti'nin kadın ve erkek versiyonları, profil foto şeklinde; taslakları ilet, beraber seçelim, onayladıktan sonra koyarsın").
Henüz **onaylanmadı**; seçim ParentApp'in karşılaştırma sayfasında yapılacak. Seçilenler ParentApp `assets/avatars` + oyuna aynı kimlikle girer, kimlikler ortak `sozlesme/durumlar.md`'ye yazılır.

| Kimlik | Ad | Ayrım |
|---|---|---|
| `okti_anne_1` | Çiçekli | kirpik, yanak pembesi, başta mercan çiçek, mercan tişört |
| `okti_anne_2` | Hasır şapkalı | kirpik, yanak pembesi, hasır şapka (oyundaki `hat_straw`), nane yeşili tişört |
| `okti_anne_3` | Fiyonklu gözlüklü | kirpik, yanak pembesi, pembe fiyonk, pembe yuvarlak gözlük (`glasses_round`), lila ton |
| `okti_baba_1` | Bıyıklı gözlüklü | bıyık, kahverengi yuvarlak gözlük, koyu mavi ton |
| `okti_baba_2` | Kaptan | kaş, kaptan şapkası (`set_captain_hat`), turkuaz ton, beyaz tişört |
| `okti_baba_3` | Kasketli | kaş, kırmızı kasket (`hat_cap`), turuncu tişört |

- `drafts/<kimlik>.png`: 1024×1024, omuz/baş, sade açık zemin; yuvarlak kırpmada okunur (`drafts/sheet.png` kare + yuvarlak yan yana).
- `drafts/seffaf/<kimlik>.png`: aynı kadraj, şeffaf zemin (oyun içi kullanım).
- Üretim: oyundaki yetişkin Okti modeli + oyundaki eşyalar + kodla süsler (kirpik, kaş, bıyık, çiçek, fiyonk); Meshy kredisi harcanmaz.
  `nice -n 10 <bpy 4.2 + Pillow python> -I art/parent_avatars/make_drafts.py [kimlik ...] [--samples 128] [--size 1024]`
