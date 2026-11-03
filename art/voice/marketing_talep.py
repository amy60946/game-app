"""
Marketing'e oyun sesleri talebi (3 Kasım 2026, kullanıcı: "Sesleri Marketing'den talep et, daha önce konuştuğumuz yapıda
güncellesin. Akıcı, ses tonları aynı/benzer kalsın, duraksamalar, Türkçe aksan ve diğer Marketing içeriklerinin detaylarıyla.
Hepsini yapmadan önce oyundaki kalıpları birer örnekle dinlet").

Çıktı (art/voice/talep/): satirlar.json (oyunun BÜTÜN okunan satırları: anahtar, karakter, kalıp, ekrandaki metin, okunacak
metin, bugün kaydı var mı), kaliplar.json (kalıp başına açıklama + bir örnek satır), ref/*.wav (karakter başına onaylı oyun
seslerinden ton referansı, IMA ADPCM'den açılır) + karakter.json (F0 ortancaları), BENIOKU.md (iş sırası ve teslim biçimi).
Teslim biçimi import_voices.py ile aynı: teslim.json + ses/<anahtar>.wav.

    python3 -I art/voice/marketing_talep.py
"""
import json, os, struct, sys, wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "talep")
VOICE = os.path.join(ROOT, "Assets", "_Pofi", "Resources", "Voice")
sys.argv = [sys.argv[0], os.path.join(OUT, "_bos")]
sys.path.insert(0, HERE)
import build_voice as B   # noqa: E402

# karakter tonları (GB20 ölçümü, onaylı oyun sesleri): anlatıcı B, Okti C (B ×1,22), adalılar H; Mavi ×0,92 tempo build_voice'ta
KARAKTER = {"anlatici": {"ref": "anlatici.wav", "f0": 149.5, "ad": "Anlatıcı (B)"},
            "okti": {"ref": "okti.wav", "f0": 190.2, "ad": "Okti (C)"},
            "adali": {"ref": "adali.wav", "f0": 243.1, "ad": "Adalılar (H)"}}

# kalıp: (kimlik, açıklama, eşleşme işlevi, örnek seçimi için tercih edilen kaynak)
def _p(src, pre): return src.startswith(pre)
KALIPLAR = [
    ("film", "Giriş filmi anlatımı: uzun, betimleyici, masalsı (anlatıcı)", lambda l: _p(l["src"], "story:intro")),
    ("hikaye_anlatici", "Hikâye sahnesi, anlatıcı satırı (bölüm açılış/kapanış)", lambda l: _p(l["src"], "story:") and l["role"] == "anlatici"),
    ("hikaye_okti", "Hikâye sahnesi, Okti konuşuyor (çocuksu, neşeli)", lambda l: _p(l["src"], "story:") and l["role"] == "okti"),
    ("hikaye_adali", "Hikâye sahnesi, adalı konuşuyor (Kıskaç, Tosbi, Pıtır, Hışır, Nur, Pus)", lambda l: _p(l["src"], "story:") and l["role"] == "adali" and l["who"] != "mavi"),
    ("hikaye_mavi", "Hikâye sahnesi, postacı Mavi (oyunda %8 yavaş çalınır)", lambda l: _p(l["src"], "story:") and l["who"] == "mavi"),
    ("rehber", "Rehber adımı: kısa yönerge + neden (\"Okti'ye dokun, elmayı seç: karnı doysun!\")", lambda l: _p(l["src"], "tr:guide.")),
    ("ipucu", "Tanıtım ipucu: el ekranda gösterirken okunan kısa cümle", lambda l: _p(l["src"], "tr:tip.") or _p(l["src"], "tr:gather.tip_")),
    ("okti_bakim", "Okti'nin tek cümlelik tepkisi (bakım, soluklanma, sevilme)", lambda l: l["role"] == "okti" and _p(l["src"], "tr:")),
    ("mavi_haber", "Mavi'nin haberi (posta, görev, Yıldız Kapısı)", lambda l: _p(l["src"], "tr:mavi.")),
    ("adali_selam", "Adalı selamı ve isteği", lambda l: _p(l["src"], "tr:res.") or _p(l["src"], "request:") or _p(l["src"], "tr:resident.")),
    ("genel_es", "Değişen bilgili cümlenin genel eşi (ekranda görev/ad yazar, ses genel cümleyi okur)", lambda l: l["src"].endswith(".say")),
    ("haber", "Kısa haber / geri bildirim (sandık, görev, bildirim, çanta, hedef)", lambda l: any(_p(l["src"], "tr:" + x) for x in
        ("notice.", "chest.", "quest.", "levelup.", "badge.", "welcome", "care.", "wardrobe.", "bag.", "voice.", "tasks.", "stones.", "cards.", "xp.", "goal.", "lore.", "mail.", "routine.", "shop."))),
    ("tanitim_karti", "Çok cümleli tanıtım/bilgi kartı (hediye taş, gerçek ödüller, Boncuk nedir, çocuğa not)", lambda l: _p(l["src"], "tr:gift.") or _p(l["src"], "tr:rewards.") or _p(l["src"], "tr:coin.") or _p(l["src"], "tr:info.")),
    ("kosu_bilgi", "Gezegen Koşusu bilgi kartı (Ay, uzay, Mısır gerçekleri)", lambda l: _p(l["src"], "tr:runner.")),
    ("oyun_yonerge", "Mini oyun ve ada eylemi yönergesi (bahçe, ateş, harita, dekor)", lambda l: _p(l["src"], "tr:mg.") or _p(l["src"], "tr:map.") or _p(l["src"], "tr:garden.") or _p(l["src"], "tr:fire.") or _p(l["src"], "tr:decor.") or _p(l["src"], "tr:gather.") or _p(l["src"], "tr:event.")),
    ("nasil_oynanir", "Defter › Nasıl oynanır kartı (başlık + açıklama, tek kayıt)", lambda l: _p(l["src"], "tr:howto.") or _p(l["src"], "tr:coach.")),
]
# özellik örneği (kalıplara ek, satırlar birden çok kalıpta): soru ezgisi
SORU = ("soru", "Soru cümlesi: sonu yükselen ezgi (hikâye, haber, istek; \"geldin mi?\", \"Hazır mısın?\")", "story:ch1_open:0:text")
# kalıp başına örnek (bugün sessiz, değişmesi gereken satırlar öncelikli; yoksa orta uzunlukta)
ORNEK = {"film": "story:intro:0:text", "rehber": "tr:guide.quests", "okti_bakim": "tr:care.resting", "mavi_haber": "tr:mavi.stargate",
         "genel_es": "tr:quest.ready.say", "tanitim_karti": "tr:coin.info", "nasil_oynanir": "tr:howto.care", "haber": "tr:chest.ready", "kosu_bilgi": "tr:runner.space.fact1"}


def spoken(text):
    """build_voice.spoken'ın trnorm'suz hâli: yalnız PRONOUNCE düzeltmeleri (sayı/kısaltma okunuşu Marketing zincirindeki
    trnorm'da yapılır; bu ortamda trnorm yok)."""
    for a, b in B.PRONOUNCE.items():
        text = text.replace(a, b)
    return text


def adpcm_decode(path):
    raw = open(path, "rb").read()
    assert raw[:4] == b"IMA1", path
    rate, n = struct.unpack("<ii", raw[4:12])
    pred, idx, out = 0, 0, []
    for b in raw[12:]:
        for code in (b & 15, b >> 4):
            if len(out) >= n: break
            step = B.STEP[idx]
            delta = step >> 3
            if code & 4: delta += step
            if code & 2: delta += step >> 1
            if code & 1: delta += step >> 2
            pred = max(-32768, min(32767, pred - delta if code & 8 else pred + delta))
            idx = max(0, min(88, idx + B.INDEX[code]))
            out.append(pred)
    return rate, out


def ref_wav(keys, dst):
    rate, allp = 22050, []
    for k in keys:
        rate, s = adpcm_decode(os.path.join(VOICE, f"v_{k}.bytes"))
        allp += s + [0] * int(rate * 0.45)
    with wave.open(dst, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(allp)}h", *allp))
    return round(len(allp) / rate, 1)


def main():
    os.makedirs(os.path.join(OUT, "ref"), exist_ok=True)
    have = {r.split("\t")[0] for r in open(os.path.join(VOICE, "index.txt"), encoding="utf-8") if r.strip()}
    rows = []
    for l in B.catalog():
        kal = next((k for k, _, f in KALIPLAR if f(l)), "diger")
        rows.append({"key": l["key"], "role": l["role"], "who": l.get("who"), "kalip": kal, "src": l["src"],
                     "text": l["text"], "tts": spoken(l["text"]), "kaydi_var": l["key"] in have})
    # kalıp örnekleri
    kal_out = []
    for kid, desc, _ in KALIPLAR:
        ls = [r for r in rows if r["kalip"] == kid]
        if not ls: continue
        pick = next((r for r in ls if r["src"] == ORNEK.get(kid)), None)
        if pick is None and kid == "hikaye_adali":   # Kıskaç'ın düz bir cümlesi (tırnaklı alıntı ve soru değil)
            pick = next((r for r in ls if r["who"] == "kiskac" and '"' not in r["text"] and "?" not in r["text"] and 40 <= len(r["text"]) <= 90), None)
        if pick is None:
            pool = [r for r in ls if not r["kaydi_var"]] or ls
            pool = sorted(pool, key=lambda r: len(r["text"]))
            pick = pool[len(pool) // 2]
        kal_out.append({"kalip": kid, "aciklama": desc, "karakter": KARAKTER[pick["role"]]["ad"], "satir_sayisi": len(ls),
                        "sessiz": sum(not r["kaydi_var"] for r in ls), "ornek": {k: pick[k] for k in ("key", "role", "who", "src", "text", "tts")}})
    qs = [r for r in rows if "?" in r["text"]]
    q = next((r for r in qs if r["src"] == SORU[2]), qs[0] if qs else None)
    if q:
        kal_out.append({"kalip": SORU[0], "aciklama": SORU[1], "karakter": KARAKTER[q["role"]]["ad"], "satir_sayisi": len(qs),
                        "sessiz": sum(not r["kaydi_var"] for r in qs), "ornek": {k: q[k] for k in ("key", "role", "who", "src", "text", "tts")}})
    # ton referansları: karakter başına onaylı 3–4 satır (anlatıcı: giriş filmi; Okti ve adalı: hikâye)
    refs = {}
    for role, pre in (("anlatici", "story:intro"), ("okti", "story:"), ("adali", "story:ch1")):
        ks = [r["key"] for r in rows if r["role"] == role and r["kaydi_var"] and r["src"].startswith(pre)
              and (role != "adali" or r["who"] == "kiskac") and 25 <= len(r["text"]) <= 90][:4]
        refs[role] = {"satirlar": ks, "sure_sn": ref_wav(ks, os.path.join(OUT, "ref", KARAKTER[role]["ref"]))}
    kar = {r: {"ref": KARAKTER[r]["ref"], "f0": KARAKTER[r]["f0"], "ad": KARAKTER[r]["ad"], **refs[r]} for r in KARAKTER}
    json.dump(rows, open(os.path.join(OUT, "satirlar.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(kal_out, open(os.path.join(OUT, "kaliplar.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(kar, open(os.path.join(OUT, "ref", "karakter.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sessiz = sum(not r["kaydi_var"] for r in rows)
    print(f"{len(rows)} satır ({sessiz} sessiz), {len(kal_out)} kalıp, diğer: {sum(r['kalip'] == 'diger' for r in rows)}")
    for k in kal_out: print(f"  {k['kalip']:15s} {k['satir_sayisi']:3d} satır ({k['sessiz']} sessiz) · örnek: {k['ornek']['text'][:70]}")


if __name__ == "__main__":
    main()
