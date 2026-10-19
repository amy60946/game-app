#!/usr/bin/env bash
# CI (macOS): Unity'nin ürettiği Xcode projesini arşivler, otomatik imzayla (App Store Connect API anahtarı) dışa aktarır
# ve TestFlight'a yükler. Gizli bilgiler yalnız ortam değişkeninden gelir, loga yazılmaz.
# Gerekli: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8 (p8 dosyasının metni), APPLE_TEAM_ID. Kullanım: ios-testflight.sh <xcode_proje_klasörü>
set -euo pipefail
BUNDLE_ID="${BUNDLE_ID:-${IOS_BUNDLE_ID:-com.gameapp.ios}}"
here="$(cd "$(dirname "$0")" && pwd)"
proj="$1"
# App Store yüklemesi iOS 26 SDK (Xcode 26+) ister: kurulu en yeni kararlı Xcode seçilir
ls -d /Applications/Xcode*.app
xc=$(ls -d /Applications/Xcode_*.app 2>/dev/null | grep -v -i beta | sort -V | tail -1 || true)
[ -n "$xc" ] && sudo xcode-select -s "$xc/Contents/Developer"
v=$(xcodebuild -version | head -1 | awk '{print $2}' | cut -d. -f1)
[ "${v:-0}" -ge 26 ] || { echo "::error::Xcode $v kurulu; App Store Xcode 26+ istiyor (macos-15 imajında Xcode_26 yok)"; exit 1; }
missing=""
for v in ASC_KEY_ID ASC_ISSUER_ID ASC_KEY_P8 APPLE_TEAM_ID; do [ -z "${!v:-}" ] && missing="$missing $v"; done
if [ -n "$missing" ]; then
  # secret'lar yokken de Xcode derlemesini imzasız doğrula (yerel eklenti, Unity çerçevesi derleniyor mu?)
  echo "::warning::Eksik secret:$missing — TestFlight yüklemesi atlandı (docs/TESTFLIGHT.md). İmzasız derleme denetimi yapılıyor."
  cd "$proj"
  xcodebuild -project Unity-iPhone.xcodeproj -scheme Unity-iPhone -configuration Release \
    -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO -quiet build
  echo "İmzasız iOS derlemesi başarılı."
  exit 0
fi
keydir="$RUNNER_TEMP/asc"; mkdir -p "$keydir"; chmod 700 "$keydir"
key="$keydir/AuthKey_${ASC_KEY_ID}.p8"
# p8 metni nasıl yapıştırılmış olursa olsun (BEGIN/END'li ya da yalnız gövde, \r, boşluk, tek satır, "\n" yazıları) geçerli PEM'e çevrilir
body=$(printf '%s' "$ASC_KEY_P8" | sed 's/\\n/\n/g' | tr -d '\r' | sed -E 's/-----(BEGIN|END) [A-Z ]*KEY-----//g' | tr -d ' \t\n')
[ -n "$body" ] || { echo "::error::ASC_KEY_P8 boş"; exit 1; }
{ echo "-----BEGIN PRIVATE KEY-----"; printf '%s' "$body" | fold -w 64; echo; echo "-----END PRIVATE KEY-----"; } > "$key"
chmod 600 "$key"
openssl pkey -in "$key" -noout 2>/dev/null || echo "::warning::ASC_KEY_P8 geçerli bir özel anahtar gibi görünmüyor (.p8 dosyasının tüm metnini yapıştır)."
auth=(-allowProvisioningUpdates -authenticationKeyPath "$key" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID")

# Arşiv otomatik geliştirme imzasıyla alınır (en az bir kayıtlı cihaz gerekir → asc_device.py); dışa aktarma App Store
# dağıtım imzasıyla elle yeniden imzalar (aşağıda).
# Apple ara sertifikaları (WWDR G3/G6): imza zincirinin tamamı gömülsün, yoksa App Store "Invalid Signature" der
for c in AppleWWDRCAG3 AppleWWDRCAG6; do
  curl -fsSL -o "$RUNNER_TEMP/$c.cer" "https://www.apple.com/certificateauthority/$c.cer" \
    && security import "$RUNNER_TEMP/$c.cer" -k ~/Library/Keychains/login.keychain-db -A >/dev/null 2>&1 || true
done
python3 -m pip install -q --disable-pip-version-check "pyjwt[crypto]" 2>/dev/null || python3 -m pip install -q --break-system-packages "pyjwt[crypto]"
python3 "$here/asc_device.py" "$key"
archive="$RUNNER_TEMP/Pofi.xcarchive"
cd "$proj"
xcodebuild -version
xcodebuild -project Unity-iPhone.xcodeproj -scheme Unity-iPhone -configuration Release \
  -destination 'generic/platform=iOS' -archivePath "$archive" \
  DEVELOPMENT_TEAM="$APPLE_TEAM_ID" CODE_SIGN_STYLE=Automatic \
  "${auth[@]}" -quiet archive
[ -d "$archive" ] || { echo "::error::Arşiv oluşmadı"; exit 1; }
codesign -dvv "$(ls -d "$archive"/Products/Applications/*.app | head -1)" 2>&1 | grep -E "Authority|TeamIdentifier" || true

# Dışa aktarma: elle App Store dağıtım imzası (asc_sign.py → geçici sertifika + profil, geçici yerel anahtar zinciri;
# iş bitince sertifika/profil iptal edilir, anahtar zinciri silinir). Kullanıcı onayı: 19 Ekim 2026.
sign="$RUNNER_TEMP/sign"; kc="$RUNNER_TEMP/ci.keychain-db"; kcpw=$(openssl rand -hex 16)
trap 'python3 "$here/asc_sign.py" cleanup "$key" "$sign/info.json" || true; security delete-keychain "$kc" 2>/dev/null || true; rm -rf "$key" "$sign"' EXIT
python3 "$here/asc_sign.py" create "$key" "$BUNDLE_ID" "$sign"
openssl x509 -inform DER -in "$sign/cert.der" -out "$sign/cert.pem"
p12pw=$(openssl rand -hex 12)
openssl pkcs12 -export -legacy -inkey "$sign/key.pem" -in "$sign/cert.pem" -out "$sign/dist.p12" -passout "pass:$p12pw" 2>/dev/null \
  || openssl pkcs12 -export -inkey "$sign/key.pem" -in "$sign/cert.pem" -out "$sign/dist.p12" -passout "pass:$p12pw"
security create-keychain -p "$kcpw" "$kc"
security set-keychain-settings -lut 21600 "$kc"
security unlock-keychain -p "$kcpw" "$kc"
security import "$sign/dist.p12" -k "$kc" -P "$p12pw" -T /usr/bin/codesign -T /usr/bin/security -T /usr/bin/xcodebuild
for c in AppleWWDRCAG3 AppleWWDRCAG6; do [ -f "$RUNNER_TEMP/$c.cer" ] && security import "$RUNNER_TEMP/$c.cer" -k "$kc" >/dev/null 2>&1 || true; done
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$kcpw" "$kc" >/dev/null
security list-keychains -d user -s "$kc" $(security list-keychains -d user | tr -d '"')
echo "Dağıtım kimliği sayısı: $(security find-identity -v -p codesigning "$kc" | grep -c 'Apple Distribution' || true)"
puuid=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["profile_uuid"])' "$sign/info.json")
pname=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["profile_name"])' "$sign/info.json")
for d in "$HOME/Library/MobileDevice/Provisioning Profiles" "$HOME/Library/Developer/Xcode/UserData/Provisioning Profiles"; do
  mkdir -p "$d"; cp "$sign/profile.mobileprovision" "$d/$puuid.mobileprovision"
done

cat > "$RUNNER_TEMP/ExportOptions.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>teamID</key><string>${APPLE_TEAM_ID}</string>
  <key>signingStyle</key><string>manual</string>
  <key>signingCertificate</key><string>Apple Distribution</string>
  <key>provisioningProfiles</key><dict><key>${BUNDLE_ID}</key><string>${pname}</string></dict>
  <key>uploadSymbols</key><false/>
  <key>manageAppVersionAndBuildNumber</key><false/>
</dict></plist>
PL
xcodebuild -exportArchive -archivePath "$archive" -exportOptionsPlist "$RUNNER_TEMP/ExportOptions.plist" \
  -exportPath "$RUNNER_TEMP/export" -authenticationKeyPath "$key" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID"
echo "TestFlight'a yüklendi. App Store Connect işledikten sonra (genelde 10-30 dk) TestFlight sekmesinde görünür."
