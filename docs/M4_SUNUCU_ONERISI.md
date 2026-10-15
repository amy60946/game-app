# M4 – Oyun ile Fidan'ı bağlama (sunucu önerisi)

**Durum: onaylandı (15 Ekim 2026), henüz uygulanmadı.** Uygulama adımları: `docs/M4_UYGULAMA.md` (GitHub Actions "Supabase M4 uygula": önce deneme, sonra gerçek).

## Ne sağlar?
1. **Yaş bandı:** Çocuğun doğum gününden otomatik önerilir (6–9 → A, 10–12 → B, 13–15 → C). Ebeveyn değiştirebilir.
2. **Görev durumları:** Çocuk oyunda "Yaptım" ya da "Yapamam" der. Ebeveyn Fidan'da **onaylar** ya da **not yazarak reddeder** ("Yatak dağınık kalmış").
3. **Coin defteri:** Coin **yalnızca ebeveyn onaylayınca** eklenir; çocuk ya da oyun kendisi coin ekleyemez. Onay geri alınırsa coin de geri düşer.
4. **Dükkan fiyatları sunucuda:** Oyun "bu eşyayı al" der; fiyatı sunucu belirler. Aynı alışveriş iki kez düşülmez, bakiye eksiye inmez.
5. **Oyun kaydı yedeği:** Telefon değişse de ilerleme kaybolmaz.
6. **Cihaz bağlantısını kaldırma:** Ebeveyn Fidan'dan çocuğun cihaz bağlantısını kapatabilir; oyun "Bağlantın kapatıldı, yeni kod iste" der.

## Nasıl denendi?
- `supabase/test/run.sh`: Bu makinede gerçek PostgreSQL 16 üzerinde Fidan'ın mevcut şeması + bu öneri + 41 kontrol (giriş kodu, haftalık/aylık görevler, yetkisiz erişim denemeleri, coin hilesi denemesi, çift harcama, başka ailenin erişimi…). Hepsi geçti. Dosya iki kez çalıştırılınca da sorun çıkmıyor.
- Oyun tarafı istemcisi: `Assets/_Pofi/Scripts/Logic/Services/Supabase/SupabaseGameService.cs` (+4 test).

## Onaylarsan yapılacaklar (sırayla)
1. `supabase/proposed/20261015000000_pofi_game.sql` dosyasını Supabase panelinde SQL Editor'da bir kez çalıştırmak (sana adım adım anlatırım).
2. Fidan'a küçük eklemeler: çocuk eklerken yaş bandı, incelemede "reddet + not", çocuğun coin bakiyesi, "cihaz bağlantısını kaldır" düğmesi.
3. Oyunda sahte arka uç yerine gerçek bağlantıyı açmak (ayar dosyasında Supabase adresi + yayınlanabilir anahtar; gizli anahtar asla).

## Senin vermen gereken kararlar
- Bu öneriyi uygulayalım mı? (Evet ise 1. adımı birlikte yaparız.)
- Fidan'daki eski "çocuk girişi" masal ekranı kalsın mı (açık soru S6)?
