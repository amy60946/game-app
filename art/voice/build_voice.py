"""
Oyunun sesli okuma kayıtları (23 Ekim 2026, kullanıcı kararı):
  anlatıcı = B (Chatterbox Multilingual, canlı üslup), adalılar = C'nin söyleyişi + F'nin ses tonu (ses dönüştürme, hedef
  ref/adali_f.mp3), Okti = C (B'nin perdesi ×1,22). Herkeste açık; çocuk balonun köşesindeki hoparlörden ya da avatar
  menüsünden kapatır (Settings.VoiceOn).
Okunanlar: giriş filmi + hikâye sahneleri (story.json; yaş grubu metinleri text/a/c ayrı kayıt), adalı istekleri ve selamları,
ipuçları ve rehber adımları (tr.json). Pet adı "Okti" ile kaydedilir: çocuk adı değiştirirse o satırlar sessiz kalır
(yanlış ad duyulmaz).

Eşleşme: oyunda ekrana yazılan metin → anahtar (Logic/Audio/VoiceKey: etiketler atılır, boşluklar tekleşir, FNV-1a 64 bit)
→ Resources/Voice/v_<anahtar>.bytes (IMA ADPCM 4 bit, 22050 Hz mono, Logic/Audio/ImaAdpcm) + Resources/Voice/index.txt.
Her kayıt Whisper ile denetlenir; hatalıysa başka tohumla yeniden üretilir (en çok 6 deneme), en iyisi kalır; uzun duraktan
sonraki kuyruk kesilir; ses düzeyi −18 LUFS'ye eşitlenir.

Kullanım: <venv>/bin/python -I art/voice/build_voice.py <çalışma_klasörü> [--list] [--missing] [--only anahtar,...] [--part i/n] [--retry]
  (--retry: oyunda henüz olmayan ve tam doğru çıkmamış satırlar 4 başka tohumla yeniden denenir, daha temizi kalır)
  (--missing: sesi eksik satırlar; düz python3 ile de çalışır, ses ortamı gerekmez)
  (--part: n paralel iş; hepsi bitince bir kez --part olmadan çalıştırılır: dosyalar ve index.txt yazılır)
Çalışma klasörü önbellektir: metni ve sesi değişmeyen satır yeniden üretilmez. Satır listesi ve sonuçlar art/voice/manifest.json.
"""
import json, os, re, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_samples as G   # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "Assets", "_Pofi", "Resources", "Data")
DST = os.path.join(ROOT, "Assets", "_Pofi", "Resources", "Voice")
MANIFEST = os.path.join(HERE, "manifest.json")
VERSION = 1            # ses ayarı değişirse artır: önbellek geçersizleşir
PET = "Okti"
RATE = 22050
LIMIT = 0.03           # kabul edilen harf hata oranı …
EDITS = 2              # … ya da en çok 2 harf farkı (Whisper adları biraz farklı yazar: "Kıskaç" → "kızkaç")
SEEDS = (7, 100, 101, 102)
RETRY_SEEDS = (103, 104, 105, 106)   # --retry: tam doğru çıkmayan yeni satıra ikinci tur
OKTI_PITCH = 1.22
TEMPO = {"mavi": 0.92}   # kullanıcı (23 Ekim): Mavi biraz yavaş konuşsun, daha kolay anlaşılsın (perde aynı)

TIP_SKIP = {"guide.reward", "guide.done", "tip.stone_go"}   # sayı ya da yer adı alan, önceden kaydedilemeyen metinler


# ---------------------------------------------------------------- anahtar (Logic/Audio/VoiceKey.cs ile aynı)

def normalize(text):
    t = re.sub(r"<[^>]*>", "", text)
    return " ".join(t.split())


def key(text):
    h = 0xcbf29ce484222325
    for b in normalize(text).encode("utf-8"):
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


# ---------------------------------------------------------------- satırlar

def role_of(who):
    return "anlatici" if who == "narrator" else "okti" if who == "okti" else "adali"


def fill_pet(s):
    """Tek {0} = pet adı (oyundaki Ui ile aynı ek): '{0} üstü…' → Okti'nin, '{0} dokun' → Okti'ye, diğerleri → Okti."""
    if "{" not in s:
        return s
    if s.count("{") != 1 or "{0}" not in s:
        return None
    after = s.split("{0}", 1)[1]
    form = PET + "'nin" if after.startswith(" üst") else PET + "'ye" if after.startswith(" dokun") else PET
    return s.replace("{0}", form)


# tip./guide. dışında okunan metinler: anahtar → {0} yerine konacak sabit (yoksa boş)
SPOKEN_EXTRA = {"welcome.coins": "20", "rewards.pick": "", "rewards.first_sent": "", "rewards.new_map": "", "gather.coconut_ready": "",
                "gather.coconut_got": ""}


def _first_wear_names(tr):
    """Giydirme rehberinin adını söylediği eşya: sahip olunan en ucuz komik olmayan giyilebilir (WardrobeScreen), rehber Sv1–2'de."""
    items = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))
    items = items["items"] if isinstance(items, dict) else items
    return [i["name"] for i in items if i.get("slot") and i.get("level", 1) <= 2 and not i.get("premium")
            and (not i.get("fancy") or i.get("level", 1) <= 1)]


# {0} pet adı olmayan rehber metinleri (26 Ekim 2026): oyundaki çağrıyla aynı değerler
VARIANTS = {
    # MapScreen.Hud GuideStageFor: T("guide.press", eylem tuşu yazısı, sondaki ! atılır); ActionServes'in tuşları
    "guide.press": lambda tr: [tr[k].rstrip("!") for k in ("hud.enter", "hud.play", "hud.collect", "hud.chop", "hud.mine",
                                                           "hud.build", "hud.place", "hud.stoke")],
    "guide.wear_item": _first_wear_names,   # WardrobeScreen: T("guide.wear_item", item.Name)
}


def catalog():
    story = json.load(open(os.path.join(DATA, "story.json"), encoding="utf-8"))
    tr = json.load(open(os.path.join(DATA, "tr.json"), encoding="utf-8"))["strings"]
    out, seen = [], set()

    def add(text, role, src, who):
        if not text or not re.search(r"[^\W\d_]", text):   # harfsiz satır ("...": susan adalı) okunmaz
            return
        k = key(text)
        if k in seen:
            return
        seen.add(k)
        out.append({"key": k, "text": normalize(text), "role": role, "src": src, "who": who})

    for sc in story["scenes"]:
        for i, l in enumerate(sc["lines"]):
            for f in ("text", "a", "c"):
                if f in l:
                    add(l[f].replace("{pet}", PET), role_of(l["who"]), f"story:{sc['id']}:{i}:{f}", l["who"])
    for r in story.get("requests", []):
        add(r["text"].replace("{pet}", PET), role_of(r["who"]), f"request:{r['id']}", r["who"])
    for k, v in tr.items():
        if k in TIP_SKIP:
            continue
        if k in VARIANTS:   # {0} pet adı değil: oyunun koyabileceği her değerle ayrı kayıt
            for arg in VARIANTS[k](tr):
                add(v.replace("{0}", arg), "anlatici", f"tr:{k}:{arg}", "narrator")
            continue
        if k.startswith(("tip.", "guide.", "gather.tip_")) or k == "gather.ready":
            add(fill_pet(v), "anlatici", "tr:" + k, "narrator")
        elif k.startswith("res.hi_"):
            add(fill_pet(v), "adali", "tr:" + k, k[len("res.hi_"):])
        elif k in SPOKEN_EXTRA:   # GB17: hoş geldin coin'i, gerçek ödüller tanıtımı, ceviz haberi (oyunda Voice.Say ile)
            add(v.replace("{0}", SPOKEN_EXTRA[k]) if "{0}" in v else v, "anlatici", "tr:" + k, "narrator")
    # 26 Ekim 2026: tanışma kartında Okti kendini tanıtır (Okti sesi), panodaki Mavi'nin hoş geldin görevi ipucu (anlatıcı)
    for k, role, who in (("pet.meet_intro", "okti", "okti"), ("welcome_task.tip", "anlatici", "narrator")):
        if k in tr: add(fill_pet(tr[k]), role, "tr:" + k, who)
    for a, b, c in [("rewards.intro_1", "rewards.intro_2", "rewards.intro_3"), ("gift.l1", "gift.l2", "gift.l3")]:   # tanıtım kartı üç satırı tek seferde okur
        add(" ".join(tr[x] for x in (a, b, c)), "anlatici", "tr:" + a.rsplit("_", 1)[0].rsplit(".", 1)[0] + ".intro" if a.startswith("rewards") else "tr:gift.card", "narrator")
    return out


# ---------------------------------------------------------------- üretim

# Modelin yanlış okuduğu yazımlar (yalnız seslendirilen metin; ekrandaki metin ve anahtar aynı kalır)
PRONOUNCE = {"Yaptım'a": "Yaptıma"}   # 26 Ekim 2026: kesme işaretiyle "yaptığıma" okunuyordu


def spoken(text):
    from trnorm import normalize as trn
    for a, b in PRONOUNCE.items():
        text = text.replace(a, b)
    return trn(text)   # sayılar yazıyla ("3 taş" → "üç taş"); başka değişiklik yapmaz


def take(line, seed):
    k, tts = line["key"], line["tts"]
    if line["role"] == "anlatici":
        return G.cb_take("cb_canli", k, tts, seed)
    if line["role"] == "okti":
        G.STYLES["_okti_b"] = G.STYLES["cb_canli"]
        G.cb_take("_okti_b", k, tts, seed)
        out = os.path.join(G.OUT, f"okti_{k}.mp3")
        G.pitch_file(os.path.join(G.OUT, f"_okti_b_{k}.mp3"), out, OKTI_PITCH)
        return {"id": k, "voice": "okti", "text": tts, "file": os.path.basename(out), "sec": G.duration(out), "seed": seed}
    return G.adali_take("adali", k, tts, seed)


def _fold(t):
    """Whisper'ın karıştırdığı sesler bir sayılır: s/z ("sise" ↔ "size", "sis" ↔ "siz"), ğ düşer."""
    return G._norm(t).replace("z", "s").replace("ğ", "")


def good(x):
    a, b = _fold(x["text"]), _fold(x.get("asr", ""))
    edits = G._cer(a, b) * len(a)
    return edits <= max(EDITS, LIMIT * len(a)) + 0.01


def make(line, seeds=SEEDS, floor=None):
    """En iyi kaydı m_<anahtar>.mp3 olarak bırakır. floor: eldeki kaydın hata oranı (--retry); yalnız ondan iyisi yerine geçer."""
    master = os.path.join(G.OUT, f"m_{line['key']}.mp3")
    best = None
    for seed in seeds:
        try:
            x = G.check(take(line, seed))
        except Exception as e:   # model bu tohumda çöktü (ör. hizalama): deneme başarısız sayılır
            print("  deneme hatası", seed, type(e).__name__, str(e)[:80], flush=True)
            continue
        if (best is None or x["cer"] < best["cer"]) and (floor is None or x["cer"] < floor):
            best = x
            os.replace(os.path.join(G.OUT, x["file"]), master)
        if best is not None and (best["cer"] == 0 if floor is not None else good(best)):
            break
    if best is None:
        return None
    best = dict(best, file=os.path.basename(master))
    best = G.trim(best, limit=max(LIMIT, best["cer"]))
    return best


# ---------------------------------------------------------------- oyun biçimi (Logic/Audio/ImaAdpcm.cs ile aynı)

STEP = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
        130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060,
        1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484,
        7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767]
INDEX = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]


def adpcm(samples, rate):
    """'IMA1' + örnek hızı + örnek sayısı (int32 LE) + 4 bitlik kodlar (her baytta önce alt yarım)."""
    pred, idx, codes = 0, 0, []
    for s in samples:
        step = STEP[idx]
        diff = s - pred
        code = 0
        if diff < 0:
            code, diff = 8, -diff
        delta = step >> 3
        if diff >= step:
            code |= 4; diff -= step; delta += step
        step >>= 1
        if diff >= step:
            code |= 2; diff -= step; delta += step
        step >>= 1
        if diff >= step:
            code |= 1; delta += step
        pred = max(-32768, min(32767, pred - delta if code & 8 else pred + delta))
        idx = max(0, min(88, idx + INDEX[code]))
        codes.append(code)
    if len(codes) % 2:
        codes.append(0)
    body = bytes(codes[i] | (codes[i + 1] << 4) for i in range(0, len(codes), 2))
    return b"IMA1" + struct.pack("<ii", rate, len(samples)) + body


def filters(who):
    t = TEMPO.get(who)
    return (f"atempo={t}," if t else "") + "loudnorm=I=-18:TP=-1.5:LRA=11"


def encode(master, dst, who=None):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", master, "-af", filters(who), "-ac", "1", "-ar", str(RATE),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    n = len(raw) // 2
    samples = struct.unpack(f"<{n}h", raw[: n * 2])
    with open(dst, "wb") as f:
        f.write(adpcm(samples, RATE))
    return n / RATE


def main():
    work = sys.argv[1]
    G.set_out(work)
    lines = catalog()
    if "--missing" in sys.argv:
        # sesi henüz üretilmemiş satırlar (ses ortamı gerekmez): yeni/değişen metinden sonra ve oturum sonunda bakılır
        idx = os.path.join(DST, "index.txt")
        have = {r.split("\t")[0] for r in open(idx, encoding="utf-8") if r.strip()} if os.path.exists(idx) else set()
        miss = [l for l in lines if l["key"] not in have]
        for l in miss:
            print(l["src"], "|", l["text"])
        print(len(miss), "eksik /", len(lines), "satır")
        return
    for l in lines:
        l["tts"] = spoken(l["text"])
    if "--list" in sys.argv:
        for l in lines:
            print(l["key"], l["role"], l["src"], "|", l["text"])
        print(len(lines), "satır")
        return
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    # --part i/n: n paralel işten i'ncisi (satır sırası % n == i); her iş kendi önbelleğine yazar, hepsi birlikte okunur
    part = tuple(int(v) for v in sys.argv[sys.argv.index("--part") + 1].split("/")) if "--part" in sys.argv else None
    if part:
        import torch
        torch.set_num_threads(max(1, (os.cpu_count() or 4) // part[1]))
    cache_p = os.path.join(work, f"cache_{part[0]}.json" if part else "cache.json")
    cache = {}
    for f in sorted(os.listdir(work)):
        if f.startswith("cache") and f.endswith(".json"):
            cache.update(json.load(open(os.path.join(work, f))))
    os.makedirs(DST, exist_ok=True)
    retry = "--retry" in sys.argv
    idx = os.path.join(DST, "index.txt")
    shipped = {r.split("\t")[0] for r in open(idx, encoding="utf-8") if r.strip()} if os.path.exists(idx) else set()
    t0 = time.time()
    for i, l in enumerate(lines):
        if part and i % part[1] != part[0]:
            continue
        sig = f"{VERSION}|{l['role']}|{l['tts']}"
        c = cache.get(l["key"])
        master = os.path.join(work, f"m_{l['key']}.mp3")
        fresh = c and c.get("sig") == sig and os.path.exists(master)
        if retry and fresh and l["key"] not in shipped and c["cer"] > 0 and (only is None or l["key"] in only):
            # --retry: oyunda henüz olmayan, tam doğru çıkmamış satır başka tohumlarla; yalnız daha temizi eskinin yerine geçer
            x = make(l, RETRY_SEEDS, floor=c["cer"])
            if x is None:
                print(f"[{i + 1}/{len(lines)}] aynı kaldı (hata %{100 * c['cer']:4.1f}) | {l['text']}", flush=True)
                continue
        elif (only is None or l["key"] in only) and not (fresh and only is None):
            x = make(l)
        else:
            continue
        if x is None:
            print(f"[{i + 1}/{len(lines)}] ATLANDI (model hatası) | {l['text']}", flush=True)
            continue
        c = cache[l["key"]] = {"sig": sig, "seed": x.get("seed"), "cer": x["cer"], "asr": x.get("asr", "")}
        mine = {k: v for k, v in cache.items() if not part or k in {q["key"] for j, q in enumerate(lines) if j % part[1] == part[0]}}
        json.dump(mine, open(cache_p, "w"), ensure_ascii=False, indent=1)
        print(f"[{i + 1}/{len(lines)}] {l['role']:8s} hata %{100 * x['cer']:4.1f} | {l['text']}  ←  {x.get('asr', '')}", flush=True)
    if part:
        print(f"parça {part[0]}/{part[1]} bitti", flush=True)
        return
    # oyun dosyaları yalnız sonda yazılır (üretim sürerken depo değişmesin)
    for l in lines:
        c = cache.get(l["key"])
        master = os.path.join(work, f"m_{l['key']}.mp3")
        if c and c.get("sig") == f"{VERSION}|{l['role']}|{l['tts']}" and os.path.exists(master):
            l["sec"] = round(encode(master, os.path.join(DST, f"v_{l['key']}.bytes"), l.get("who")), 2)
            l.update(seed=c.get("seed"), cer=c.get("cer"))
    keep = {f"v_{l['key']}.bytes" for l in lines if "sec" in l}
    for f in os.listdir(DST):
        if f.startswith("v_") and f.endswith(".bytes") and f not in keep:
            os.remove(os.path.join(DST, f))
    with open(os.path.join(DST, "index.txt"), "w", encoding="utf-8") as f:
        for l in lines:
            if "sec" in l:
                f.write(f"{l['key']}\t{l['role']}\t{l['text']}\n")
    json.dump({"version": VERSION, "rate": RATE, "pet": PET, "lines": lines}, open(MANIFEST, "w"), ensure_ascii=False, indent=1)
    total = sum(l.get("sec", 0) for l in lines)
    size = sum(os.path.getsize(os.path.join(DST, f)) for f in keep)
    print(f"bitti: {len(keep)}/{len(lines)} satır, {total / 60:.1f} dk ses, {size / 1e6:.1f} MB, {(time.time() - t0) / 60:.0f} dk", flush=True)


if __name__ == "__main__":
    main()
