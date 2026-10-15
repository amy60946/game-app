# iPhone (TestFlight) hattı

Oyun GitHub Actions'ta iki adımda TestFlight'a gider (`.github/workflows/ios.yml`):

1. **Xcode projesi (Linux, GameCI):** Unity iOS derlemesi. Mevcut `UNITY_LICENSE` / `UNITY_EMAIL` / `UNITY_PASSWORD` secret'ları kullanılır.
2. **TestFlight (macOS):** `tools/ci/ios-testflight.sh` → `xcodebuild archive` (otomatik imza, App Store Connect API anahtarıyla
   sertifika/profil bulutta yönetilir) → `-exportArchive` (`destination: upload`) ile App Store Connect'e yükleme.

Çalıştırma: GitHub → **Actions** → **iOS (TestFlight)** → **Run workflow**. Ya da commit mesajında `[ios]` geçerse kendiliğinden.

## Bir kez yapılacaklar (kullanıcı)

Şifre/anahtar sohbete **yazılmaz**; hepsi GitHub → Settings → Secrets and variables → Actions → **New repository secret**.

1. Apple Developer Program üyeliği etkin olmalı.
2. developer.apple.com → Certificates, IDs & Profiles → **Identifiers** → **+** → App IDs → App →
   Bundle ID (Explicit): `com.fidan.pofi` (doluysa başka bir ad, örn. `com.fidan.pofiadasi` → `IOS_BUNDLE_ID` secret'ına yaz).
3. appstoreconnect.apple.com → **Apps** → **+** → **New App**: iOS, ad "Pofi Adası", dil Türkçe, 2. adımdaki Bundle ID, SKU `pofi-adasi`.
4. App Store Connect → **Users and Access** → **Integrations** → **App Store Connect API** → **Team Keys** → **+**:
   ad `GitHub`, erişim **Admin** (bulut imzası için gerekli). Key ID, Issuer ID ve `.p8` dosyası (yalnız bir kez inebilir).
5. Secret'lar:

| Secret | Değer |
|---|---|
| `ASC_KEY_ID` | Key ID |
| `ASC_ISSUER_ID` | Issuer ID |
| `ASC_KEY_P8` | `.p8` dosyasının tüm metni (BEGIN/END satırları dahil) |
| `APPLE_TEAM_ID` | developer.apple.com → Account → Membership details → Team ID |
| `IOS_BUNDLE_ID` | (isteğe bağlı) `com.fidan.pofi` dışında bir kimlik kaydedildiyse |

Secret'lar yoksa Xcode projesi yine üretilir (Actions → Artifacts → `pofi-ios-xcode`), yalnız yükleme adımı uyarıyla atlanır.

## Yükledikten sonra

- App Store Connect → uygulama → **TestFlight**: derleme 10–30 dk "Processing" görünür, sonra hazır olur.
- **Internal Testing** → **+** grup → kendini (Apple ID e-postan) ekle → iPhone'a **TestFlight** uygulamasını kur → davetten yükle.
- Şifreleme sorusu çıkmaz (`ITSAppUsesNonExemptEncryption = false`, `Editor/IosPostBuild.cs`).

## Ayarlar (kod olarak)

- Sürüm `ProjectSetup.AppVersion` (0.9.0), derleme numarası = Actions çalışma numarası (her yükleme benzersiz).
- Yatay, tam ekran, durum çubuğu gizli; simge `Assets/_Pofi/Art/AppIcon.png` (`art/scripts/app_icon.py`).
- iOS yerel: titreşim (UIImpactFeedbackGenerator) ve ses oturumu "playback" — `Plugins/iOS/PofiNative.mm`.
- Çentik/ev çubuğu: `UI/SafeArea.cs` (ekran kökleri ve köşe düğmeleri güvenli alanda).
- Not: Apple **Kids Category** için yaş bandı ve gizlilik metinleri mağaza yayınından önce (TestFlight için gerekmez) — `docs/PLAN.md`.
