#!/usr/bin/env bash
# Meshy çevre modellerini oyuna yerleştirir: Resources/Env/<ad>/ (FBX + 1024 JPG doku).
# Kullanım: bash art/meshy/install_env.sh b_home [p_rock …]   (ad verilmezse out/ altında .glb'si olan tüm b_/t_/p_)
set -e
root="$(cd "$(dirname "$0")/../.." && pwd)"
B=/tmp/claude-0/bpyenv/bin/python
M="$root/art/meshy"
names="$*"
[ -z "$names" ] && names=$(cd "$M/out" && for d in b_* t_* p_*; do [ -f "$d/$d.glb" ] && echo "$d"; done)
for n in $names; do
  R="$root/Assets/_Pofi/Resources/Env/$n"
  rm -rf "$R"; mkdir -p "$R"
  $B $M/scripts/prepare_asset.py model "$M/out/$n/$n.glb" "$R" "$n" > "$M/out/$n/prepare.log" 2>&1 || { echo "$n: HATA (out/$n/prepare.log)"; continue; }
  rm -f "$R"/*_normal.jpg   # çevre/eşyada normal haritası yok (boyut)
  echo "$n: $(ls "$R" | wc -l) dosya, $(du -sh "$R" | cut -f1)"
done
