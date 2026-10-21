# Bildirimler — çocuk açısından değerlendirme ve karar (22 Ekim 2026)

Klinik sınır geçerlidir: bu belge bir tanı ya da puanlama önermez. Amaç, haberin çocuğa yardım etmesi ve onu baskı altına almamasıdır.

## Soru

Ebeveyn yeni görev girince ya da bir görevi onaylayınca çocuk bunu oyunda görsün mü? Oyun kapalıyken telefona bildirim (push) gitsin mi?

## Yararları

- **Öngörülebilirlik:** Çocuk ondan ne beklendiğini bilir. Bu, 6–12 yaş için kaygıyı azaltır.
- **Hemen geri bildirim:** "Aferin, onaylandı" anı, ödülü davranışa bağlar. Gecikince bu bağ zayıflar.
- **Özerklik:** Görevi çocuk kendi zamanında ve kendi seçimiyle görür ("ne zaman yapacağıma ben karar veririm").

## Riskleri

- **Sürekli dürtme:** Sık bildirim "dışarıdan kontrol" hissi verir. Öz-belirleme kuramına göre bu iç motivasyonu düşürür; görev "yapılacak iş" olur, oyun "iş yeri" olur.
- **Ret ve olumsuz haber:** "Reddedildi" ya da "yapmadın" gibi sözler utanç ve kaçınma doğurur. Çocuk oyunu açmaktan kaçabilir.
- **Kaçırma korkusu ve geri sayım:** "Son 2 saat", seri bozulma uyarısı ve kırmızı sayaç gibi öğeler kaygı yaratır. Kaygıya yatkın çocuklarda bu daha belirgin olabilir.
- **Uyku ve okul:** Gece ya da derste gelen bildirim uykuyu ve dikkati böler.
- **Oyunun bölünmesi:** Mini oyun ortasında gelen haber akışı keser ve can sıkar.

## Karar

### 1. Oyun içi haber: AÇIK (sakin biçimde)

Kural kodda: `Assets/_Pofi/Scripts/Logic/App/Notices.cs`, testi `NoticeTests`.

- **Toplu gösterim:** Bir seferde en çok 3 haber çıkar. Fazlası "+N haber daha" olarak tek satırda özetlenir. Birden çok yeni görev tek cümle olur: "Ev Görevleri panosunda 2 yeni görev var".
- **Önce olumlu haber:** Sıra ödül, onay, yeni görev ve "bir daha deneyebilirsin" şeklindedir. Olumlu haberde pet sevinir ve yumuşak bir ses çalar. Olumsuz haber sessiz ve kısadır.
- **Ret dili yumuşak:** "{görev}: istersen bir daha deneyebilirsin". Ebeveynin notu yalnızca Ev Görevleri panosunda görünür, ekranda büyük harflerle çıkmaz.
- **Baskı dili yok:** "Son", "kaçırdın", "acele et" gibi sözler ve geri sayım kullanılmaz. Büyüyen kırmızı görev sayacı da yoktur.
- **Oyun bölünmez:** Mini oyun, kart oyunu ve etkinlik sırasında haberler kuyrukta bekler. Çocuk adaya, eve ya da bir panoya dönünce gösterilir.
- **Gerçek ödül:** Ödül verilince "Ödülün hazır!" çıkar. Ödül bekletilince "şimdilik bekleyecek · coinlerin sende" çıkar ve coin kaybı yoktur.

### 2. Cihaz bildirimi (push, oyun kapalıyken): KOD HAZIR, KAPALI

- `PushPolicy.Enabled = false` durumunda oyun cihaz anahtarını sunucuya kaydetmez (`register_push_token` çağrılmaz). Bu yüzden çocuğun telefonuna hiçbir bildirim gitmez.
- İleride açılırsa kurallar şunlardır:
  - **Ebeveyn açar:** ParentApp → çocuk ayarı. Varsayılan kapalıdır.
  - **Yalnız olumlu ya da nötr türler:** `task_assigned`, `task_approved`, `reward_given`. Ret, "yapamadı" ve hatırlatma hiçbir zaman push olmaz.
  - **Sessiz saatler:** 20:00–08:00 arası ve okul saatlerinde gönderilmez.
  - **Günlük sınır:** Günde en çok 1 push. Birden çok haber tek bildirimde toplanır.
- Açmadan önce bu kuralların sunucu tarafında da yazılması gerekir. Bu, `ortak` deposunda bir öneri olur: `push-apns` ve çocuk bildirimlerinde sessiz saat, günlük sınır ve ebeveyn izni. Telefon tarafı için Unity'ye Mobile Notifications paketi ve iOS push yetkisi eklenmelidir.

## Kimin ne yapması gerekir

- **Kullanıcı:** Push'u açmak isterse karar verir. Önerimiz, önce oyun içi haberlerin bir süre denenmesidir.
- **ParentApp penceresi (push açılırsa):** çocuk başına "telefona haber" ayarı.
