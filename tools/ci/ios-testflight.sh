#!/usr/bin/env bash
# CI (macOS): Unity'nin ürettiği Xcode projesini arşivler, otomatik imzayla (App Store Connect API anahtarı) dışa aktarır
# ve TestFlight'a yükler. Gizli bilgiler yalnız ortam değişkeninden gelir, loga yazılmaz.
# Gerekli: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8 (p8 dosyasının metni), APPLE_TEAM_ID. Kullanım: ios-testflight.sh <xcode_proje_klasörü>
set -euo pipefail
proj="$1"
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
# dağıtım imzasıyla yeniden imzalar (sertifika Apple bulutunda, API anahtarı Admin).
python3 -m pip install -q --disable-pip-version-check "pyjwt[crypto]" 2>/dev/null || python3 -m pip install -q --break-system-packages "pyjwt[crypto]"
python3 "$(dirname "$0")/asc_device.py" "$key"
archive="$RUNNER_TEMP/Pofi.xcarchive"
cd "$proj"
xcodebuild -version
xcodebuild -project Unity-iPhone.xcodeproj -scheme Unity-iPhone -configuration Release \
  -destination 'generic/platform=iOS' -archivePath "$archive" \
  DEVELOPMENT_TEAM="$APPLE_TEAM_ID" CODE_SIGN_STYLE=Automatic \
  "${auth[@]}" -quiet archive
[ -d "$archive" ] || { echo "::error::Arşiv oluşmadı"; exit 1; }

cat > "$RUNNER_TEMP/ExportOptions.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>teamID</key><string>${APPLE_TEAM_ID}</string>
  <key>signingStyle</key><string>automatic</string>
  <key>uploadSymbols</key><true/>
  <key>manageAppVersionAndBuildNumber</key><false/>
</dict></plist>
PL
xcodebuild -exportArchive -archivePath "$archive" -exportOptionsPlist "$RUNNER_TEMP/ExportOptions.plist" \
  -exportPath "$RUNNER_TEMP/export" "${auth[@]}"
echo "TestFlight'a yüklendi. App Store Connect işledikten sonra (genelde 10-30 dk) TestFlight sekmesinde görünür."
rm -f "$key"
