# Unity lisansını GitHub'a tanıtma (bir kez yapılır)

Oyunu GitHub kendi bilgisayarlarında Unity ile derler. Bunun için ücretsiz **Unity Personal** lisansın gerekir.
Bu adımları **bilgisayarda** yap. Hiçbir bilgiyi sohbete yazma; yalnızca GitHub'daki gizli alanlara (Secrets) gireceksin.

## 1. Unity hesabı ve Unity Hub
1. https://unity.com/download adresine git, **Unity Hub**'ı indir ve kur.
2. Unity Hub'ı aç → **Sign in** → hesabın yoksa **Create account** ile e-posta ve şifreyle hesap aç.
   - Google/Apple ile giriş yaptıysan, Unity hesap ayarlarından bir **şifre belirle** (GitHub'a e-posta + şifre gerekiyor).
3. Unity Hub'da sol alttaki dişli (**Settings / Preferences**) → **Licenses** → **Add** → **Get a free personal license** → kabul et.
   (Unity Editor'ü kurmana gerek yok, yalnızca lisans yeter.)

## 2. Lisans dosyasını bul ve kopyala
Dosyanın adı `Unity_lic.ulf`:
- **Windows:** Dosya Gezgini'nin adres çubuğuna `C:\ProgramData\Unity` yaz, Enter.
- **Mac:** Finder → üst menüde **Git** → **Klasöre Git…** (⇧⌘G) → `/Library/Application Support/Unity` yaz, Enter.

`Unity_lic.ulf` dosyasına sağ tıkla → **Not Defteri / TextEdit ile aç** → tümünü seç (Ctrl+A / ⌘A) → kopyala.

## 3. GitHub'a gizli değer olarak ekle
1. https://github.com/amy60946/pofi-adasi → üstte **Settings** → solda **Secrets and variables** → **Actions**.
2. **New repository secret** ile şu üçünü tek tek ekle:

| Name | Secret (değer) |
|---|---|
| `UNITY_LICENSE` | Kopyaladığın dosya içeriğinin tamamı |
| `UNITY_EMAIL` | Unity hesabının e-postası |
| `UNITY_PASSWORD` | Unity hesabının şifresi |

3. Bitti. Claude'a "lisansı ekledim" demen yeterli.

> Unity hesabında iki adımlı doğrulama açıksa derleme başarısız olabilir; öyle olursa Claude seni yönlendirir.
