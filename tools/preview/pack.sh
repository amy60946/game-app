#!/usr/bin/env bash
# WebGL önizlemesini Artifact'a uygun pakete çevirir.
# Artifact yalnızca belirli uzantıları sunar ve .js dosyasında ikili veri kabul etmez; Unity'nin
# gzip'li .unityweb dosyaları bu yüzden .wasm uzantısıyla yayınlanır (loader içerikten tanır).
# Kullanım: bash tools/preview/pack.sh <çıktı-klasörü>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:?çıktı klasörü}"
git -C "$ROOT" fetch -q origin +webgl-preview:refs/remotes/origin/webgl-preview   # dal her derlemede yeniden yazılır
TMP="$(mktemp -d)"
git -C "$ROOT" archive origin/webgl-preview | tar -x -C "$TMP"
rm -rf "$OUT" && mkdir -p "$OUT/Build"
B="$TMP/PofiAdasi/Build"
cp "$B/PofiAdasi.loader.js" "$OUT/Build/"
cp "$B/PofiAdasi.framework.js.unityweb" "$OUT/Build/PofiAdasi.framework.wasm"
# Veri dosyası 14 MB'lık parçalara bölünür (önizleme sayfası tek dosyada 15 MB sınırı); sayfa parts.json'a göre birleştirir
split -b 14000000 -d -a 1 "$B/PofiAdasi.data.unityweb" "$OUT/Build/PofiAdasi.data.part"
n=0; for f in "$OUT"/Build/PofiAdasi.data.part[0-9]; do mv "$f" "$f.wasm"; n=$((n+1)); done
echo "{\"parts\": $n}" > "$OUT/Build/parts.json"
cp "$B/PofiAdasi.wasm.unityweb" "$OUT/Build/PofiAdasi.code.wasm"
cp "$ROOT/tools/preview/index.html" "$OUT/index.html"
cp "$ROOT/tools/preview/keyart.jpg" "$OUT/keyart.jpg"   # yükleme ekranı tam ekran görseli (art/scripts/keyart.py)
cat "$TMP/preview.json"; echo
ls -la "$OUT/Build"
