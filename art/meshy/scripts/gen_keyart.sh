#!/bin/bash
# Yükleme görselleri ve giriş filmi kareleri (Meshy nano-banana-pro, 16:9). Kullanım: gen.sh <ad> <okti_ref|-> "<sahne>"
cd "$(dirname "$0")/.." || exit 1
STYLE="Vivid 3D game key art for a cozy kids island adventure game, landscape 16:9, painted miniature diorama look, soft toon lighting with clean crisp shadows, saturated but balanced colors (never washed out, never glaring, no heavy bloom), turquoise shallow sea with white shore foam, lush green grass with tiny flowers, soft cumulus clouds, rounded friendly shapes, characters are soft matte vinyl toys, no outlines, no text, no letters, no logo, no user interface. Keep the bottom fifth of the image calm and simple so a loading bar and a short tip can sit there."
OKTI="The main character is exactly the little octopus from the reference image: light blue jelly-like octopus head, coral-pink round snout, small black eyes, wearing the same outfit."

name=$1; ref=$2; scene=$3
if [ "$ref" = "-" ]; then
  python3 meshy.py image "$name" nano-banana-pro "$scene $STYLE" --aspect 16:9
else
  python3 meshy.py image "$name" nano-banana-pro "$scene $OKTI $STYLE" --ref "$ref" --aspect 16:9
fi
