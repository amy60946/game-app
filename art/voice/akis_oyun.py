"""
Oyun sesleri — Marketing'in v4 akış zinciriyle, karakter tonları korunarak (GB20, 2 Kasım 2026).

Kullanıcı (Marketing penceresinde, aynen): "GameApp'e son ulaştığımız/ulaşacağımız detaylı en iyi ses detayları bilgisini ve nasıl
yapılacağını aktar, o kendi penceresinde yapsın, yani geri devralsın". Zincir Marketing'in ses paketi v4'üdür (Ahenk Cep → Praat
ezgi → Chatterbox VC → akış seçimi); bu betik onu oyun karakterlerine uyarlar:
  - VC hedefi her karakterin ONAYLI oyun seslerinden kurulan ton referansı (anlatıcı / Okti / adalı); spiker B sesi kullanılmaz.
  - Perde hedefi (Z.B_F0) o karakterin onaylı satırlarının F0 ortancası; aday seçimi ona göre (Marketing uyarısı: B'ye kırpılmasın).
    Çıktı ortancası hedefe 0,8 yarım tondan uzaksa küçük perde düzeltmesi.
  - 30 Ekim sonrası iyileştirmeler: sözcük içi kopukluk cezası (hece_kopuk, akış puanında −6), çok cümleli satırda cümle sonu
    es 0,38 / virgül 0,18 sn (yalnız uzatır), 0,45 sn'yi aşan es 0,40'a kısalır.
  - Ses düzeyi eşitleme ve Mavi temposu (×0,92) burada uygulanmaz: build_voice.py oyun biçimine yazarken uygular.
Çıktı: <çıktı>/ses/<anahtar>.wav + teslim.json → import_voices.py → build_voice.py --write-only (bkz. import_voices.py).

Kullanım (ses ortamı tts_venv; SES_PAKET = Marketing ses paketi klasörü, ör. <scratchpad>/devir/spiker_ses):
  SES_PAKET=… <tts_venv>/bin/python -I art/voice/akis_oyun.py <ref_klasörü> <çıktı> [--ornek] [--only anahtar,…]
  ref_klasörü: anlatici.wav, okti.wav, adali.wav + karakter.json (onaylı satırlardan; F0 ortancaları)
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PAKET = os.environ.get("SES_PAKET")
if not PAKET or not os.path.isdir(PAKET):
    sys.exit("SES_PAKET (Marketing ses paketi klasörü) verilmeli")
sys.path.insert(0, PAKET)
import numpy as np, soundfile as sf   # noqa: E402
from ses import zincir as Z           # noqa: E402
from ses import akis as A             # noqa: E402

# ---------------------------------------------------------------- Whisper sonucu aynı dosya için bir kez (akış ölçüsü + hece kopukluğu)
_wo, _wc = Z.words_of, {}


def _words_of(path):
    k = (path, os.path.getmtime(path))
    if k not in _wc:
        if len(_wc) > 64:
            _wc.clear()
        _wc[k] = _wo(path)
    return _wc[k]


Z.words_of = _words_of

# ---------------------------------------------------------------- (a) sözcük içi kopukluk cezası (Marketing, 2 Kasım 2026)
_olcu = A.akis_olcu


def akis_olcu(path, shown, high_f0=False):
    m = _olcu(path, shown, high_f0)
    y, sr = sf.read(path); y = np.asarray(y, dtype="float64")
    if y.ndim > 1:
        y = y.mean(axis=1)
    db, hop = A._db(y, sr)
    ref = float(np.median(db[db > db.max() - 35]))
    words, _ = Z.words_of(path)
    kopuk = 0
    for w in words:
        if w.end - w.start < 0.30:
            continue
        run = best = 0
        for v in db[int((w.start + 0.05) / hop):int((w.end - 0.05) / hop)]:
            run = run + 1 if v < ref - 30 else 0
            best = max(best, run)
        kopuk += best * hop >= 0.10
    m["hece_kopuk"] = int(kopuk)
    return m


def akis_puani(m):
    return m["cukur_db"] - 0.25 * m["bosluk_ms"] - 3.0 * max(0.0, m["perde_sicr"] - 1.2) - 6.0 * m.get("hece_kopuk", 0)


A.akis_olcu, A.akis_puani = akis_olcu, akis_puani

# ---------------------------------------------------------------- (b) duraklar: uzun esi kısalt, cümle/virgül esini doğal boya uzat
CUMLE_ES, VIRGUL_ES, PAUSE_MAX, PAUSE_TO = 0.38, 0.18, 0.45, 0.40


def frames_db(y, hop):
    n = len(y) // hop
    fr = np.sqrt(np.mean(y[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(fr + 1e-9)


def _runs(db, thr, min_s):
    sp = np.where(db >= thr)[0]
    runs, run = [], None
    if len(sp) == 0:
        return runs
    for k in range(sp[0], sp[-1] + 1):
        if db[k] < thr:
            run = (run[0], k) if run else (k, k)
        else:
            if run and (run[1] - run[0] + 1) * 0.01 >= min_s:
                runs.append(run)
            run = None
    return runs


def kisalt(path):
    y, sr = sf.read(path); y = np.asarray(y, dtype="float64"); hop = int(0.01 * sr)
    db = frames_db(y, hop)
    runs = [r for r in _runs(db, db.max() - 38, PAUSE_MAX) if (r[1] - r[0] + 1) * 0.01 > PAUSE_MAX]
    if not runs:
        return 0
    out, last, xf = [], 0, int(0.005 * sr)
    for a, b in runs:
        dur = (b - a + 1) * 0.01
        cut = int((dur - PAUSE_TO) * sr)
        mid = (a + b + 1) // 2 * hop
        s0, s1 = mid - cut // 2, mid + (cut - cut // 2)
        out.append(y[last:s0]); last = s1
    out.append(y[last:])
    sf.write(path, np.concatenate(out), sr, subtype="PCM_16")
    return len(runs)


def uzat(path, metin):
    n_c = len(re.findall(r"[.!?…](?=[”\"’]?\s)", metin.strip()))
    n_v = len(re.findall(r"[,;:]", metin))
    if n_c + n_v == 0:
        return 0
    y, sr = sf.read(path); y = np.asarray(y, dtype="float64"); hop = int(0.01 * sr)
    db = frames_db(y, hop)
    runs = _runs(db, db.max() - 38, 0.06)
    runs.sort(key=lambda r: -(r[1] - r[0]))
    hedef = {r: (CUMLE_ES if i < n_c else VIRGUL_ES) for i, r in enumerate(runs[:n_c + n_v])}
    ekle = []
    for (a, b), h in hedef.items():
        dur = (b - a + 1) * 0.01
        if dur < h - 0.02:
            ekle.append(((a + b + 1) // 2 * hop, int((h - dur) * sr), a * hop, (b + 1) * hop))
    if not ekle:
        return 0
    ekle.sort(); out, last, xf = [], 0, int(0.005 * sr)
    for pos, n, s0, s1 in ekle:
        out.append(y[last:pos])
        tohum = y[s0:s1] if s1 - s0 > 2 * xf else np.zeros(2 * xf)
        dolgu = np.resize(np.concatenate([tohum, tohum[::-1]]), n)
        w = np.linspace(0, 1, xf)
        if n > 2 * xf:
            dolgu[:xf] *= w; dolgu[-xf:] *= w[::-1]
        out.append(dolgu); last = pos
    out.append(y[last:])
    sf.write(path, np.concatenate(out), sr, subtype="PCM_16")
    return len(ekle)


# ---------------------------------------------------------------- perde: karakterin onaylı ortancasına
def f0_median(path, fmax):
    Z.F0_MAX = fmax
    _, _, _, f0, _, _ = Z.f0_track(path)
    v = f0[~np.isnan(f0)]
    return float(np.median(v)) if len(v) else float("nan")


def perde_duzelt(path, hedef, fmax):
    """Karakter perdesinden 0,8 yarım tondan uzaksa yalnız AŞAN kısmı geri çeker (en çok 1,5 yt): ünlem/soru satırının doğal
    yüksekliği korunur, büyük kaydırma formantı bozmaz. 1,2 sn'den kısa satırda ölçü güvenilmez → dokunmaz.
    Dönüş: (ölçülen fark, uygulanan kaydırma) yarım ton."""
    med = f0_median(path, fmax)
    if np.isnan(med):
        return 0.0, 0.0
    st = 12 * np.log2(med / hedef)
    if abs(st) <= 0.8 or Z.duration(path) < 1.2:
        return round(st, 2), 0.0
    kay = float(np.sign(st)) * min(1.5, abs(st) - 0.8)
    k = 2 ** (-kay / 12)
    tmp = path + ".p.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-af", f"asetrate={Z.SR}*{k:.5f},aresample={Z.SR},atempo={1 / k:.5f}",
                    "-ac", "1", "-c:a", "pcm_s16le", tmp], check=True)
    os.replace(tmp, path)
    return round(st, 2), round(-kay, 2)


def soru_bul(metin):
    m = re.search(r"(\w+)\s+m[ıiuü]\s*,?\s*yoksa\b.*?(\w+)\s+m[ıiuü]\s*\?", metin)
    return (m.group(1), m.group(2)) if m else None


ORNEK = {"anlatici": 4, "okti": 3, "adali": 3}


def main():
    refdir, OD = sys.argv[1], sys.argv[2]
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    sys.argv = [sys.argv[0], OD] + [a for a in sys.argv[3:] if a in ("--ornek",)]
    import build_voice as B
    kar = json.load(open(os.path.join(refdir, "karakter.json"), encoding="utf-8"))
    idx = os.path.join(B.DST, "index.txt")
    have = {r.split("\t")[0] for r in open(idx, encoding="utf-8") if r.strip()}
    lines = [l for l in B.catalog() if l["key"] not in have]
    if only:
        lines = [l for l in lines if l["key"] in only]
    if "--ornek" in sys.argv:   # karakter başına birkaç satır (dinleme sayfası): kısa-orta-uzun karışık
        pick = []
        for role, n in ORNEK.items():
            ls = sorted([l for l in lines if l["role"] == role], key=lambda l: len(l["text"]))
            if ls:
                pick += [ls[int(i * (len(ls) - 1) / max(1, n - 1))] for i in range(min(n, len(ls)))]
        lines = pick
    lines.sort(key=lambda l: ("anlatici", "okti", "adali").index(l["role"]))   # VC hedefi az değişsin
    os.makedirs(os.path.join(OD, "ses"), exist_ok=True)
    WD = os.path.join(OD, "_is"); os.makedirs(WD, exist_ok=True)
    tj = os.path.join(OD, "teslim.json")
    teslim = {t["key"]: t for t in json.load(open(tj, encoding="utf-8"))} if os.path.exists(tj) else {}
    t0 = time.time()
    for i, l in enumerate(lines):
        if l["key"] in teslim and os.path.exists(os.path.join(OD, teslim[l["key"]]["file"])):
            continue
        c = kar[l["role"]]
        Z.REF_DARK = c["ref"] if os.path.isabs(c["ref"]) else os.path.join(refdir, c["ref"])
        Z.B_F0 = c["f0"]
        fmax = 500 if c["f0"] > 170 else 350
        Z.F0_MAX = fmax   # aday seçimindeki perde ölçüsü de karakterin aralığında
        said = B.spoken(l["text"])
        row = A.bolum_uret(WD, OD, l["key"], l["text"], said, [], soru_bul(l["text"]), {"speed": 1.0})
        src = os.path.join(OD, l["key"] + ".wav")
        dst = os.path.join(OD, "ses", l["key"] + ".wav")
        os.replace(src, dst)
        ham = os.path.join(OD, "ses", "_ham"); os.makedirs(ham, exist_ok=True)
        subprocess.run(["cp", dst, os.path.join(ham, l["key"] + ".wav")], check=True)   # son işlemler yeniden ayarlanabilsin
        n_k = kisalt(dst)
        n_u = uzat(dst, l["text"]) if len(re.findall(r"[.!?…]", l["text"])) >= 2 or "," in l["text"] else 0
        st, kay = perde_duzelt(dst, c["f0"], fmax)
        teslim[l["key"]] = {"key": l["key"], "file": f"ses/{l['key']}.wav", "role": l["role"], "who": l.get("who"), "text": l["text"],
                            "cer": 0.0 if row["exact"] else 0.05, "asr": row["whisper"], "utmos": row["utmos"],
                            "akis": row["akis"], "f0_once_st": st, "perde_kaydir_st": kay, "es_kisalan": n_k, "es_uzayan": n_u, "dur": round(Z.duration(dst), 2)}
        json.dump(list(teslim.values()), open(tj, "w"), ensure_ascii=False, indent=1)
        print(f"[{i + 1}/{len(lines)}] {l['role']:8s} UTMOS {row['utmos']} birebir {row['exact']} akış {row['akis'].get('puan')} "
              f"kopuk {row['akis'].get('hece_kopuk')} perde {st:+} st (kaydır {kay:+}) | {l['text']}  ←  {row['whisper']}  ({(time.time() - t0) / 60:.0f} dk)", flush=True)
    print("bitti", len(teslim), "satır", flush=True)


if __name__ == "__main__":
    main()
