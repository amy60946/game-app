# Çocuk avatarları (Okti kız / erkek)

ParentApp penceresinin isteği (28 Ekim 2026, kullanıcı: "Çocuğun avatar seçimi de aile üyeleri gibi Okti versiyonlarıyla olsun, 6 kız 6 erkek; çocuk gibi"). ParentApp'te ilk çocuk ve çocuk ekleme ekranında `children.avatar` için. Kimlikler ortak `sozlesme/durumlar.md`'ye ParentApp penceresince yazılır.

| Kimlik | Ad | Ayrım |
|---|---|---|
| `okti_kiz_1` | Kurdeleli | pembe kurdele, pembe tişört |
| `okti_kiz_2` | Çiçek tokalı | iki yanda sarı çiçek toka, lila tişört |
| `okti_kiz_3` | Taçlı | yan yatık taç (`hat_crown_tilt`), nane yeşili tişört |
| `okti_kiz_4` | Kalp gözlüklü | kalp gözlük (`glasses_heart`), mercan tişört |
| `okti_kiz_5` | Bereli | pembe örgü bere (`hat_beanie`), turkuaz tişört |
| `okti_kiz_6` | Kulaklıklı | pembe kulaklık (`headphones`), sarı tişört |
| `okti_erkek_1` | Kasketli | mavi kasket (`hat_cap`), çil, turuncu tişört |
| `okti_erkek_2` | Pervaneli | renkli pervaneli şapka (`hat_propeller`), yeşil tişört |
| `okti_erkek_3` | Pilot | pilot gözlüklü bant (`hat_pilot_goggles`), çil, sarı tişört |
| `okti_erkek_4` | Güneş gözlüklü | güneş gözlüğü (`glasses_sun`), kırmızı tişört |
| `okti_erkek_5` | Antenli | yıldızlı anten (`hat_star_antenna`), çil, lacivert tişört |
| `okti_erkek_6` | Köpek balığı şapkalı | köpek balığı şapkası (`hat_shark`), beyaz tişört |

Hepsinde oyundaki çocuk evresi Okti (`Pets/pet_13_yavru`) + iri parlak göz; kızlarda kirpik ve yanak pembesi.

- `drafts/<kimlik>.png`: 1024×1024, omuz/baş, kendi pastel zemini; yuvarlak kırpmada okunur (`drafts/sheet.png`).
- `drafts/seffaf/<kimlik>.png`: aynı kadraj, şeffaf zemin.
- Üretim (ebeveyn avatarlarıyla aynı betik, Meshy kredisi yok):
  `nice -n 10 <bpy 4.2 + Pillow python> -I art/parent_avatars/make_drafts.py --group cocuk [kimlik ...] [--samples 128] [--size 1024]`
- Oyun şu an `children.avatar`'ı göstermiyor (çocuğun oyundaki yüzü Okti); gösterilirse `to_game.py` gibi yuvarlak küçültme eklenir.
