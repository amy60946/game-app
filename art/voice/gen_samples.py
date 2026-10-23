"""
Sesli okuma örnekleri (V7, 23 Ekim 2026): aynı cümleler ücretsiz Türkçe seslerle.
  cb / cb_canli) Chatterbox Multilingual (Resemble AI, MIT; model ağırlıkları da MIT): doğal, duygulu; bulutta önceden
     kaydedilir, oyuna ses dosyası olarak girer. cb sakin anlatıcı, cb_canli daha coşkulu (çocuklara).
  karakter) cb_canli'nin perdesi yükseltilmiş hali (Kıskaç gibi adalılar için; aynı tempo).
  piper) Piper tr_TR dfki: YALNIZ KARŞILAŞTIRMA. Motor MIT ama ses verisi CC BY-NC-SA 4.0 (ticari kullanım yok);
     oyuna girmez, başka sese örnek olarak da verilmez.
  Kalite: her kayıt Whisper'a dinletilir (cümle ↔ yazıya döküm, harf hata oranı); hatalı kayıt başka tohumla yeniden
     üretilir, en iyisi kalır (Chatterbox her seferinde biraz farklı okur; kısa cümlelerde arada kelime bozulur).
Kullanım: <venv>/bin/python -I gen_samples.py <çıkış_klasörü> [all|piper|cb|cb_canli|karakter|denetle|duzelt|kirp]
Çıktı: <ad>.mp3 + samples.json (cümle, ses, süre).
"""
import json, os, subprocess, sys, time, urllib.request

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

LINES = [
    ("anlatici_1", "Bir zamanlar mavi denizin ortasında Işık Adası vardı."),
    ("anlatici_2", "Sakinleri birbirine yardım eder, fener her gece yolları aydınlatırdı."),
    ("anlatici_6", "Evde yaptığın her iyilik bir Güneş Taşı olur. Haydi, adayı birlikte uyandıralım!"),
    ("kiskac_1", "Hey küçük! Sen de fırtınayla mı geldin?"),
    ("ipucu_1", "Elmayı Okti'ye sürükle!"),
]

PIPER_VOICE = "tr_TR-dfki-medium"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/"


def mp3(wav, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "24000", "-b:a", "64k", out], check=True)
    os.remove(wav)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return round(float(r.stdout.strip() or 0), 2)


def piper():
    d = os.path.join(OUT, "_piper"); os.makedirs(d, exist_ok=True)
    onnx = os.path.join(d, PIPER_VOICE + ".onnx")
    for f in (PIPER_VOICE + ".onnx", PIPER_VOICE + ".onnx.json"):
        p = os.path.join(d, f)
        if not os.path.exists(p):
            urllib.request.urlretrieve(PIPER_BASE + f, p)
    from piper import PiperVoice
    import wave
    voice = PiperVoice.load(onnx)
    res = []
    for name, text in LINES:
        wav = os.path.join(OUT, f"piper_{name}.wav")
        with wave.open(wav, "wb") as w:
            voice.synthesize_wav(text, w)
        out = os.path.join(OUT, f"piper_{name}.mp3"); mp3(wav, out)
        res.append({"id": name, "voice": "piper", "text": text, "file": os.path.basename(out), "sec": duration(out)})
    return res


STYLES = {"cb": (0.5, 0.5), "cb_canli": (0.8, 0.3)}   # (exaggeration, cfg_weight)


def cb_model():
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    if not hasattr(cb_model, "m"):
        cb_model.m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    return cb_model.m


def cb_take(tag, name, text, seed):
    import torch, torchaudio
    model = cb_model()
    ex, cfg = STYLES[tag]
    torch.manual_seed(seed)
    t0 = time.time()
    wav = model.generate(text, language_id="tr", exaggeration=ex, cfg_weight=cfg)
    p = os.path.join(OUT, f"{tag}_{name}.wav")
    torchaudio.save(p, wav, model.sr)
    out = os.path.join(OUT, f"{tag}_{name}.mp3"); mp3(p, out)
    return {"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out), "gen": round(time.time() - t0, 1), "seed": seed}


def chatterbox(tag="cb"):
    res = []
    for name, text in LINES:
        res.append(cb_take(tag, name, text, 7))
        print(tag, name, res[-1]["sec"], "sn ses,", res[-1]["gen"], "sn üretim", flush=True)
    return res


def _norm(t):
    import re
    t = t.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(re.sub(r"[^\wçğıöşü ]", "", t).split())


def _cer(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
    return d[-1] / max(1, len(a))


def check(x):
    """Whisper (medium, Türkçe) yazıya döküm + harf hata oranı (0 = kusursuz)."""
    from faster_whisper import WhisperModel
    if not hasattr(check, "m"):
        check.m = WhisperModel("medium", device="cpu", compute_type="int8")
    segs, _ = check.m.transcribe(os.path.join(OUT, x["file"]), language="tr", beam_size=5)
    x["asr"] = " ".join(s.text.strip() for s in segs)
    x["cer"] = round(_cer(_norm(x["text"]), _norm(x["asr"])), 3)
    return x


def trim(x, limit=0.03, gap=0.6):
    """Baştaki sessizliği ve uzun bir duraktan sonra gelen kuyruğu (nefes, uydurma ses) keser; kesik hali hâlâ tam cümleyse tutar."""
    import re
    src = os.path.join(OUT, x["file"])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "silencedetect=n=-40dB:d=0.25", "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    pairs = [(float(e), float(d)) for e, d in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", r.stderr)]
    head = pairs[0][0] - 0.12 if starts and starts[0] < 0.05 and pairs else 0.0
    cut = next((st + 0.18 for st, (en, d) in zip(starts, pairs) if d >= gap and st > 0.3 and en < x["sec"] - 0.05), None)
    if head <= 0.0 and cut is None:
        return x
    head = max(0.0, head)
    tmp = os.path.join(OUT, "_trim.mp3")
    args = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{head:.2f}", "-i", src]
    af = "anull"
    if cut is not None:
        n = cut - head
        args += ["-t", f"{n:.2f}"]
        af = f"afade=t=out:st={max(0.0, n - 0.05):.2f}:d=0.05"
    subprocess.run(args + ["-af", af, "-ac", "1", "-b:a", "64k", tmp], check=True)
    y = check(dict(x, file="_trim.mp3"))
    if y["cer"] <= max(limit, x["cer"]):
        os.replace(tmp, src)
        x = dict(y, file=x["file"], sec=duration(src))
        print(x["voice"], x["id"], "kırpıldı →", x["sec"], "sn", flush=True)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return x


def fix(done, limit=0.03, tries=5):
    """Hatalı Chatterbox kaydını başka tohumlarla yeniden üretir, en düşük hatalıyı tutar."""
    out = []
    for x in done:
        if x["voice"] in STYLES and x.get("cer", 1) > limit:
            best, keep = x, os.path.join(OUT, "_best.mp3")
            os.replace(os.path.join(OUT, x["file"]), keep)
            for k in range(tries):
                y = check(cb_take(x["voice"], x["id"], x["text"], 100 + k))
                print(x["voice"], x["id"], "deneme", k + 1, "hata", y["cer"], "|", y["asr"], flush=True)
                if y["cer"] < best["cer"]:
                    best = y; os.replace(os.path.join(OUT, y["file"]), keep)
                if best["cer"] <= 0.0:
                    break
            os.replace(keep, os.path.join(OUT, x["file"]))
            x = best
        out.append(x)
    return out


def character(src, tag, pitch):
    """Perde yükseltme (tempo aynı): adalı sesleri için."""
    res = []
    for name, text in LINES:
        a = os.path.join(OUT, f"{src}_{name}.mp3")
        if not os.path.exists(a):
            continue
        out = os.path.join(OUT, f"{tag}_{name}.mp3")
        f = f"asetrate=24000*{pitch},aresample=24000,atempo={1 / pitch:.4f}"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a, "-af", f, "-ac", "1", "-b:a", "64k", out], check=True)
        res.append({"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out)})
    return res


if __name__ == "__main__":
    which = sys.argv[2] if len(sys.argv) > 2 else "all"
    done = json.load(open(os.path.join(OUT, "samples.json"))) if os.path.exists(os.path.join(OUT, "samples.json")) else []
    if which in ("all", "piper"):
        done = [x for x in done if x["voice"] != "piper"] + piper()
    if which in ("all", "cb"):
        done = [x for x in done if x["voice"] != "cb"] + chatterbox()
    if which in ("all", "cb_canli"):
        done = [x for x in done if x["voice"] != "cb_canli"] + chatterbox(tag="cb_canli")
    if which in ("all", "denetle", "duzelt"):
        done = [check(x) if "cer" not in x or which == "denetle" else x for x in done]
    if which in ("all", "duzelt"):
        done = fix(done)
    if which in ("all", "duzelt", "kirp"):
        done = [trim(x) if x["voice"] in STYLES else x for x in done]
    if which in ("all", "karakter", "duzelt", "kirp"):
        done = [x for x in done if x["voice"] != "karakter"] + [check(x) for x in character("cb_canli", "karakter", 1.22)]
    json.dump(done, open(os.path.join(OUT, "samples.json"), "w"), ensure_ascii=False, indent=1)
    print("bitti", len(done))
