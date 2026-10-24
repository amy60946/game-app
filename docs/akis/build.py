"""Akış haritası sayfasını kurar: python3 docs/akis/build.py <çıktı.html> (şablon + data.json + degerlendirme.json + map.b64 → tek dosya).
Yayın: https://claude.ai/artifact/Tt5TCHuSBnQNUHuJM1Jrbg (aynı dosya yolundan yeniden yayınla)."""
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(D, 'template.html'), encoding='utf-8').read()
t = t.replace('__MAP__', open(os.path.join(D, 'map.b64')).read()).replace('__DATA__', open(os.path.join(D, 'data.json'), encoding='utf-8').read())
t = t.replace('__EVAL__', open(os.path.join(D, 'degerlendirme.json'), encoding='utf-8').read())
open(sys.argv[1], 'w', encoding='utf-8').write(t)
