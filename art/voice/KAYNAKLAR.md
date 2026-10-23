# Sesli okuma: kaynaklar ve atıflar

Oyundaki sesli okuma kayıtları yapay zekâ ile üretilmiştir; gerçek bir kişinin sesi kopyalanmamıştır.
Oyun içinde kısa atıf: Ayarlar → en alttaki satır (`settings.voice_credits`).

| Ne | Kaynak | Lisans | Nasıl kullanıldı |
|---|---|---|---|
| Anlatıcı (B), Okti (C) | Chatterbox Multilingual, Resemble AI (https://huggingface.co/ResembleAI/chatterbox) | MIT | Türkçe metin, hazır ses, canlı üslup (exaggeration 0,8, cfg 0,3). Okti: perde ×1,22. |
| Adalı sesi (H) söyleyişi | Aynı model (C kaydı) | MIT | Ses dönüştürme (Chatterbox VC) ile ses rengi F'ye çevrildi. |
| Adalı ses rengi (F) | Ahenk (https://github.com/ozguradmin/ahenk-turkish-tts), Ahenk Cep ağırlıkları | CC BY 4.0 | Tasarlanmış yapay ses f022, neşeli üslup, perde ×1,18; 10 sn örnek `ref/adali_f.mp3` yalnız ses rengi hedefi olarak. |
| Ahenk'in eğitim verisi | Alania Turkish Synthetic Speech by PatientDesk AI (https://huggingface.co/datasets/cloud0day3/alania-synthetic-speech-tr) | CC BY 4.0 | Ahenk'in istediği atıf korunur. Includes Turkish web text from FineWeb-2 (https://huggingface.co/datasets/HuggingFaceFW/fineweb-2), used under ODC-By 1.0 and subject to Common Crawl's terms of use. |
| Ahenk'in eğitim metni | Alania Turkish Domain Text by PatientDesk AI (https://huggingface.co/datasets/cloud0day3/alania-domain-text-tr) | CC BY 4.0 | Ahenk'in istediği atıf korunur. |
| f022 sesinin tasarımı | VoxCPM2, OpenBMB (https://huggingface.co/openbmb/VoxCPM2) | Apache-2.0 | Metin tarifinden tasarlanmış ses; gerçek kişi değil. |
| Okunuş biçimi | trnorm (Ahenk deposu) | Apache-2.0 | Sayılar yazıyla ("3 taş" → "üç taş"). |
| Denetim | faster-whisper (Whisper medium, Systran) | MIT | Her kayıt yazıya dökülüp cümleyle karşılaştırılır. |

Kullanılmayan: Piper tr_TR dfki (ses verisi CC BY-NC-SA, ticari değil), Bark (yavaş ve hatalı), Ahenk büyük model ve
Trendyol-TTS (ekran kartı ister; Trendyol'un eğitim verisi özel, ticari hak belirsiz).

Üretim: `art/voice/build_voice.py` (satır listesi ve sonuçlar `manifest.json`), örnekler `art/voice/gen_samples.py`.
