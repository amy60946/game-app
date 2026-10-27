"""Ebeveyn avatarlarını oyuna koyar: drafts/<kimlik>.png → Assets/_Pofi/Resources/UI/Avatars/<kimlik>.png
(yuvarlak kırpılmış, ince beyaz kenarlı, dışı şeffaf; 256 px). Kimlikler ortak sozlesme/durumlar.md §6a; okti = varsayılan yüz.

  python3 -I art/parent_avatars/to_game.py
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC = os.path.join(ROOT, 'art', 'parent_avatars', 'drafts')
OUT = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'UI', 'Avatars')
IDS = ['okti', 'okti_anne_1', 'okti_anne_2', 'okti_anne_3', 'okti_baba_1', 'okti_baba_2', 'okti_baba_3']
SIZE = 256
RING = 7          # beyaz kenar (px, 256'da)
SS = 4            # kenar yumuşaklığı için büyük çiz, küçült


def round_avatar(src, dst):
    big = SIZE * SS
    im = Image.open(src).convert('RGB').resize((big, big), Image.LANCZOS)
    mask = Image.new('L', (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    inner = Image.new('L', (big, big), 0)
    r = RING * SS
    ImageDraw.Draw(inner).ellipse((r, r, big - 1 - r, big - 1 - r), fill=255)
    out = Image.new('RGBA', (big, big), (255, 255, 255, 0))
    out.paste(Image.new('RGBA', (big, big), (255, 255, 255, 255)), (0, 0), mask)
    out.paste(im, (0, 0), inner)
    out.resize((SIZE, SIZE), Image.LANCZOS).save(dst, optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for k in IDS:
        round_avatar(os.path.join(SRC, k + '.png'), os.path.join(OUT, k + '.png'))
        print('oyuna', k)


if __name__ == '__main__':
    main()
