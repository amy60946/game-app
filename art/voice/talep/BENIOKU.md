# Oyun sesleri — Marketing'e talep (3 Kasım 2026)

Kullanıcı (GameApp penceresinde, aynen): "Sesleri Marketing'den talep et, daha önce konuştuğumuz structure'da güncellesin.
Akıcı, ses tonları aynı/benzer kalsın, duraksamalar, Türkçe aksan ve diğer marketing içeriklerinin sahip olduğu detaylar ile
sesler üretilsin. Hepsini yapmadan önce, game'deki kalıpları birer örnekle dinlet bana."

## Kapsam
- **Oyunun bütün okunan satırları: 440** (`satirlar.json`). 274'ünün bugün kaydı var (eski zincir), 166'sı sessiz
  (GB20 + K1–K5 + Nasıl oynanır). Hepsi yeni zincirle yeniden üretilir (kullanıcı: "güncellesin"); eski kayıtlar oyunda,
  yenisi onaylanıp teslim edilene kadar kalır.
- Karakterler ve tonlar **bugünkü gibi kalır** (kullanıcı 28 Ekim: "mevcutlar daha iyi"): anlatıcı **B**, Okti **C** (B ×1,22),
  adalılar **H** (Kıskaç, Tosbi, Pıtır, Hışır, Nur, Pus, Mavi). Mavi oyunda ×0,92 yavaş çalınır (oyun tarafı uygular, sen uygulama).
  Ton referansı `ref/anlatici.wav`, `ref/okti.wav`, `ref/adali.wav` (onaylı oyun seslerinden, 22 kHz) + `ref/karakter.json`
  (F0 ortancaları 149,5 / 190,2 / 243,1 Hz). Spiker B sesi kullanılmaz.
- İstenen nitelik: Marketing içeriklerindeki detaylar — akıcılık (sözcük içi kopukluk yok), doğal duraklar (cümle sonu ~0,38 sn,
  virgül ~0,18 sn, uzun es en çok 0,40 sn), Türkçe aksan (yabancı vurgu yok), soru cümlesinde yükselen ezgi, çocuğa sıcak ve sakin üslup.
  GameApp'teki uyarlama `art/voice/akis_oyun.py` (v4 zinciri + karakter tonu + perde düzeltmesi) yol gösterir; kendi
  zincirinin son hâli daha iyiyse onu kullan, tonlar referansa yakın kalsın.

## Sıra (kullanıcı kararı)
1. **Önce örnek:** `kaliplar.json`'daki 17 kalıbın her birinden **bir** örnek (alan `ornek`). Dinleme sayfası (Artifact):
   kalıp adı + açıklaması, karakter, ekrandaki metin, ses; yanında aynı satırın **bugünkü oyun sesi** varsa karşılaştırma
   (bugünkü ses yoksa yalnız yeni). Bağlantıyı kullanıcıya ver, **onay bekle**.
2. Onaydan sonra 440 satırın tamamı.
3. **Teslim** (GameApp `import_voices.py` biçimi): `teslim.json` = `[{"key","file","role","who","cer","asr"}]` + `ses/<key>.wav`
   (44,1 kHz ya da 22 kHz mono WAV; ses düzeyi eşitlemesi ve Mavi temposu yapma, oyun tarafı yapar). Anahtar (`key`) değişmez:
   ekrandaki metnin karması (`satirlar.json`). Okunacak metin `tts` (yalnız telaffuz düzeltmeleri uygulanmış; sayıların yazıyla
   okunuşu trnorm'da). Paket Artifact olarak yayınlanır; bağlantı GameApp penceresine (tek mesaj) ve kullanıcıya.
4. GameApp penceresi alır: `import_voices.py` → `build_voice.py --write-only` → derleme + önizleme.

## Notlar
- `{0}` gibi değişen bilgi taşıyan cümlelerin sesi `.say` genel eşidir (kalıp `genel_es`); ekranda tam metin durur.
- "Nasıl oynanır" kartlarında başlık + metin tek kayıt ("Besle, yıka, oyna. Okti'ye dokun: …").
- Satır listesi yeniden üretmek için (GameApp deposunda): `python3 -I art/voice/marketing_talep.py`.

## Ek talep: Macera adı (5 Kasım 2026)

Kullanıcı kararı (ortak `sozlesme/durumlar.md` 5B): ebeveynin verdiği görevler oyunda **macera** (pano "Maceralar"; ekran adı, düğme,
sayaç, kart), açıklama cümlelerinde **sorumluluk**. Sağ üstteki oyun içi "Görev" aynen kalır. Bu yüzden 34 satırın metni değişti ve sesi
yok: `ek_macera_5kasim.json` (alanlar `satirlar.json` ile aynı). Aynı zincir, aynı ton referansları (`ref/`, değişmedi), aynı teslim
biçimi (`teslim.json` + `ses/<key>.wav`; yalnız bu 34 satır yeterli). Diğer 406 satır yerinde kalır.
