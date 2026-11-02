"""
Marketing teslimini oyuna alır (GB20, 2 Kasım 2026, kullanıcı: "yeni seslendirmeleri ses tonlarını tutarak Marketing yapsın").
Teslim klasörü: teslim.json = [{"key","file","role","who","cer","asr"}] + ses/<key>.wav (Marketing penceresinin Artifact'ından
indirilir). Her dosya çalışma klasörüne usta olarak (m_<key>.mp3) yazılır ve önbelleğe işlenir; sonra build_voice.py --write-only
yalnız oyun dosyalarını (Resources/Voice) yazar, hiçbir satırı yeniden üretmez. Onaylı eski sesler aynı kalır.

Kullanım (ses ortamı: trnorm için tts_venv):
  <tts_venv>/bin/python -I art/voice/import_voices.py <teslim_klasörü> <çalışma_klasörü>
  <tts_venv>/bin/python -I art/voice/build_voice.py <çalışma_klasörü> --write-only
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    src, work = sys.argv[1], sys.argv[2]
    sys.argv = [sys.argv[0], work]
    import build_voice as B
    lines = {l["key"]: l for l in B.catalog()}
    got = json.load(open(os.path.join(src, "teslim.json"), encoding="utf-8"))
    cache_p = os.path.join(work, "cache.json")
    cache = json.load(open(cache_p, encoding="utf-8")) if os.path.exists(cache_p) else {}
    ok = skip = 0
    for g in got:
        l = lines.get(g["key"])
        f = os.path.join(src, g["file"])
        if l is None or not os.path.exists(f):
            print("atlandı (katalogda yok ya da dosya yok):", g["key"], g.get("file")); skip += 1
            continue
        if g.get("role") and g["role"] != l["role"]:
            print("UYARI rol farklı:", g["key"], g["role"], "≠", l["role"])
        master = os.path.join(work, f"m_{g['key']}.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-ac", "1", "-ar", "44100", "-b:a", "128k", master], check=True)
        tts = B.spoken(l["text"])
        cache[g["key"]] = {"sig": f"{B.VERSION}|{l['role']}|{tts}", "seed": "marketing", "cer": float(g.get("cer") or 0.0), "asr": g.get("asr", "")}
        ok += 1
    json.dump(cache, open(cache_p, "w"), ensure_ascii=False, indent=1)
    print(f"alındı {ok}, atlandı {skip}; sıradaki: build_voice.py {work} --write-only")


if __name__ == "__main__":
    main()
