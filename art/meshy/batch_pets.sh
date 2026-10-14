#!/usr/bin/env bash
# Onaylı pet konseptlerini paralel olarak 3D'ye çevirir, sonra iskelet + 4 animasyon (idle, happy, wave, sleep).
# Kullanım: bash batch_pets.sh pet_02 pet_03 ...   (çıktı: out/<pet>/, günlük: out/<pet>/batch.log)
cd "$(dirname "$0")"
one() {
  p=$1; log=out/$p/batch.log
  img=$(ls out/$p/concept_*.png | head -1)
  python3 meshy.py to3d $p "$img" --polys 12000 --model latest --pose a-pose >>$log 2>&1 || { echo "$p 3D BAŞARISIZ" >>$log; return; }
  task=$(python3 -c "import json,glob;print(json.load(open(sorted(glob.glob('out/$p/to3d_*.json'))[-1]))['id'])")
  python3 meshy.py rig $p $task --height 0.7 >>$log 2>&1 || { echo "$p İSKELET BAŞARISIZ" >>$log; return; }
  rig=$(python3 -c "import json,glob;print(json.load(open(sorted(glob.glob('out/$p/rig_*.json'))[-1]))['id'])")
  for a in 0 44 28 269; do python3 meshy.py anim $p $rig $a >>$log 2>&1; done
  python3 - "$p" <<'PY'
import json,glob,sys,urllib.request
p=sys.argv[1]
t=json.load(open(sorted(glob.glob(f'out/{p}/rig_*.json'))[-1]))
ba=t['result'].get('basic_animations') or {}
for k,u in ba.items():
    if isinstance(u,str) and u.startswith('http') and k.endswith('_glb_url') and 'armature' not in k:
        open(f'out/{p}/basic_{k.replace("_glb_url","")}.glb','wb').write(urllib.request.urlopen(u).read())
PY
  echo "$p TAMAM" >>$log
}
for p in "$@"; do mkdir -p out/$p; one $p & done
wait
