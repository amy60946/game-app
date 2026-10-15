# M4 – Sunucuyu açma rehberi (adım adım)

Bu rehber, oyun ile Fidan'ı aynı sunucuya bağlayan eklemeyi (`supabase/proposed/20261015000000_pofi_game.sql`) Supabase'e uygulamak içindir. Yaklaşık 10 dakika sürer.

> **Önemli:** Şifreyi, bağlantı adresini ya da anahtarları **sohbete asla yapıştırma.** Hepsi yalnızca GitHub'daki "Secrets" bölümüne yazılır. Orada kimse (Claude dahil) değerini göremez.

---

## 1. Bağlantı adresini Supabase'den al

1. https://supabase.com/dashboard adresine gir ve Fidan projesini aç (`uhelhxqgpcjemadhsifx`).
2. Sayfanın üstündeki **Connect** düğmesine tıkla.
3. Açılan pencerede **Connection String** sekmesini seç, tür olarak **URI**'yi bırak.
4. **Session pooler** başlıklı kutudaki adresi kopyala. (Direct connection olanı değil: GitHub o adrese ulaşamıyor.)
   Adres şuna benzer: `postgresql://postgres.uhelhxqgpcjemadhsifx:[YOUR-PASSWORD]@aws-0-....pooler.supabase.com:5432/postgres`
5. Adresi telefondaki/bilgisayardaki bir not uygulamasına yapıştır ve `[YOUR-PASSWORD]` kısmını (köşeli parantezler dahil) veritabanı şifrenle değiştir.
   - Şifreyi hatırlamıyorsan: sol menüde **Project Settings → Database → Reset database password** → **Generate a password** → kopyala → **Reset password**. Bu işlem Fidan'ı bozmaz (Fidan bu şifreyi kullanmıyor).
   - Şifrede `@ # / ? %` gibi işaretler varsa adres bozulabilir. En kolayı: yukarıdaki gibi yeni bir şifre üretmek (yalnız harf ve rakam olur).

## 2. Adresi GitHub'a gizli olarak ekle

1. https://github.com/amy60946/pofi-adasi adresine git.
2. Üstte **Settings** → solda **Secrets and variables** → **Actions**.
3. Yeşil **New repository secret** düğmesi.
4. **Name** kutusuna tam olarak `SUPABASE_DB_URL` yaz.
5. **Secret** kutusuna 1. adımda hazırladığın adresi (şifreli haliyle) yapıştır → **Add secret**.
6. Not uygulamasındaki adresi sil.

## 3. Önce deneme olarak çalıştır (hiçbir şey değişmez)

1. Depoda üstteki **Actions** sekmesine tıkla.
2. Soldaki listeden **Supabase M4 uygula**'yı seç.
3. Sağdaki **Run workflow** düğmesine tıkla. Açılan küçük pencerede:
   - **Branch**: `claude/zen-noether-nlt3wm` kalsın.
   - **Deneme (değişiklikleri geri al)** kutusu **işaretli** kalsın.
4. Yeşil **Run workflow** düğmesine bas. Birkaç saniye sonra listede yeni bir satır belirir; ona tıkla.
5. 1 dakika içinde bitince:
   - **Yeşil tik**: her şey yolunda. "SQL'i uygula" adımını açarsan en altta `DENEME: tüm değişiklikler geri alınıyor` yazar.
   - **Kırmızı çarpı**: Claude'a "M4 denemesi kırmızı" yaz. Hata mesajını kopyalayabilirsin (şifre içermez, GitHub gizler).

## 4. Gerçek uygulama

1. 3. adımı tekrarla ama bu sefer **Deneme** kutusundaki **işareti kaldır**.
2. **Run workflow** → yeşil tik gelince "SQL'i uygula" adımının sonunda `UYGULANDI (commit).` yazar. Bitti.
3. Yanlışlıkla iki kez çalıştırırsan sorun olmaz (dosya tekrar çalıştırılmaya uygun).

## 5. İki küçük ayar daha

1. **Anonim giriş açık mı?** (oyun, çocuk kodu girişi için gerekli) Supabase → **Authentication → Sign In / Providers** → **Allow anonymous sign-ins** açık olmalı. Kapalıysa aç → **Save**.
2. **Oyunun gerçek sunucuya bağlanması** için oyunun da yayınlanabilir anahtarı bilmesi gerekir:
   - Supabase → **Project Settings → API Keys** → **Publishable key** (`sb_publishable_...` ile başlar) yanındaki kopyala simgesi. (Yalnız bu! **Secret key** ya da **service_role** olanı ASLA kullanma.)
   - GitHub → pofi-adasi → **Settings → Secrets and variables → Actions → New repository secret** → Name: `SUPABASE_PUBLISHABLE_KEY` → Secret: yapıştır → **Add secret**.
   - Bundan sonraki her oyun derlemesi gerçek kodları sunucuya gönderir. Deneme kodları (A1A1A1, B2B2B2, C3C3C3) ve "Test: her şeyi aç" önizlemede eskisi gibi çalışır.

Bunlar bitince Claude'a "M4 uygulandı" yaz; Fidan'ın yeni sürümünü (yaş grubu, notla ret, coin bakiyesi, cihaz bağlantısını kaldır) Claude yayınlar.

---

## Alternatif: SQL Editor ile elle uygulama

GitHub adımlarıyla uğraşmak istemezsen:

1. https://github.com/amy60946/pofi-adasi/blob/claude/zen-noether-nlt3wm/supabase/proposed/20261015000000_pofi_game.sql adresini aç.
2. Dosyanın sağ üstündeki **kopyala** simgesine (Copy raw file) tıkla.
3. Supabase → solda **SQL Editor** → **New query**.
4. Boş alana yapıştır → sağ altta **Run**.
5. `Success. No rows returned` yazarsa tamam. Kırmızı hata çıkarsa mesajı Claude'a ilet (dosya düzeltilip tekrar çalıştırılabilir).

Bu yolda deneme modu yoktur; ama dosya yerelde Fidan'ın güncel şemasıyla 41 kontrolden geçti ve tekrar çalıştırılması zarar vermez.
