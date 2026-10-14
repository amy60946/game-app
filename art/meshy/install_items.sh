#!/usr/bin/env bash
# Meshy kıyafet/ev eşyası modellerini oyuna yerleştirir: Resources/Items/<id>/ (FBX + 512 px doku).
# Kullanım: bash art/meshy/install_items.sh [id …]   (id verilmezse items.json'daki giyilebilir + ev eşyaları)
set -e
root="$(cd "$(dirname "$0")/../.." && pwd)"
B=/tmp/claude-0/bpyenv/bin/python
M="$root/art/meshy"
ids="$*"
[ -z "$ids" ] && ids=$(python3 -c "import json;print(' '.join(i['id'] for i in json.load(open('$root/Assets/_Pofi/Resources/Data/items.json'))['items'] if i['category'] in ('clothes','accessory','home','decor')))")
for n in $ids; do
  [ -f "$M/out/$n/$n.glb" ] || { echo "$n: model yok"; continue; }
  R="$root/Assets/_Pofi/Resources/Items/$n"
  rm -rf "$R"; mkdir -p "$R"
  $B $M/scripts/prepare_asset.py model "$M/out/$n/$n.glb" "$R" "$n" 512 > "$M/out/$n/prepare.log" 2>&1 || { echo "$n: HATA"; continue; }
  rm -f "$R"/*_normal.jpg   # çevre/eşyada normal haritası yok (boyut)
  echo "$n: $(du -sh "$R" | cut -f1)"
done
