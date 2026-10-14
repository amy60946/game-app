#!/usr/bin/env bash
# Meshy çıktısını oyuna yerleştirir: Resources/Pets/<pet>/ (model + idle/happy/wave/sleep/walk/run).
# Kullanım: bash art/meshy/install_pet.sh pet_02 [kaynak_klasör_adı]
set -e
p=$1; src=${2:-$1}
root="$(cd "$(dirname "$0")/../.." && pwd)"
B=/tmp/claude-0/bpyenv/bin/python
M="$root/art/meshy"; R="$root/Assets/_Pofi/Resources/Pets/$p"
rm -rf "$R"; mkdir -p "$R"
$B $M/scripts/prepare_asset.py model "$M/out/$src/rig_rigged_character_glb_url.glb" "$R" "$p" > /dev/null 2>&1
for a in 0:idle 44:happy 28:wave 269:sleep; do
  id=${a%%:*}; nm=${a##*:}
  f="$M/out/$src/anim${id}_animation_glb_url.glb"
  [ -f "$f" ] && $B $M/scripts/prepare_asset.py anim "$f" "$R" "$p@$nm" > /dev/null 2>&1
done
[ -f "$M/out/$src/basic_walking.glb" ] && $B $M/scripts/prepare_asset.py anim "$M/out/$src/basic_walking.glb" "$R" "$p@walk" > /dev/null 2>&1
[ -f "$M/out/$src/basic_running.glb" ] && $B $M/scripts/prepare_asset.py anim "$M/out/$src/basic_running.glb" "$R" "$p@run" > /dev/null 2>&1
echo "$p: $(ls "$R" | wc -l) dosya, $(du -sh "$R" | cut -f1)"
