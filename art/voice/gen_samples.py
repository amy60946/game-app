"""
Sesli okuma örnekleri (V7, 23 Ekim 2026): aynı cümleler ücretsiz Türkçe seslerle.
  cb / cb_canli) Chatterbox Multilingual (Resemble AI, MIT; model ağırlıkları da MIT): doğal, duygulu; bulutta önceden
     kaydedilir, oyuna ses dosyası olarak girer. cb sakin anlatıcı, cb_canli daha coşkulu (çocuklara).
  ahenk_adali) ahenk_neseli'nin perdesi ×1,18 (adalılar için).
  vc_c / vc_b) adalı sesi (kullanıcı kararı): C (ya da B) kaydı Chatterbox VC ile F tonuna dönüştürülür; söyleyiş aynı kalır.
     Hedef örnek art/voice/ref/adali_f.mp3 (Ahenk'ten türetildi, CC BY 4.0 atıf).
  karakter) cb_canli'nin perdesi yükseltilmiş hali (Kıskaç gibi adalılar için; aynı tempo).
  bark_s<n>) Bark (Suno, MIT): nefesli, daha insan gibi tonlama; kendi Türkçe hazır sesleri; kararsız, denetimle seçilir.
  ema) EMA Lightning (Apache-2.0 kod + ağırlık): yerli Türkçe küçük model, tek ses, işlemcide gerçek zamandan hızlı.
  ahenk_neseli / ahenk_sakin / ahenk_duz) Ahenk Cep (CC BY 4.0, atıf: "Ahenk (https://github.com/ozguradmin/ahenk-turkish-tts), CC BY 4.0"):
     tasarlanmış yapay kadın sesi f022, üslup (neşeli/sakin/düz). Üretilen sesin yapay olduğu belirtilir.
  piper) Piper tr_TR dfki: YALNIZ KARŞILAŞTIRMA. Motor MIT ama ses verisi CC BY-NC-SA 4.0 (ticari kullanım yok);
     oyuna girmez, başka sese örnek olarak da verilmez.
  Kalite: her kayıt Whisper'a dinletilir (cümle ↔ yazıya döküm, harf hata oranı); hatalı kayıt başka tohumla yeniden
     üretilir, en iyisi kalır (Chatterbox her seferinde biraz farklı okur; kısa cümlelerde arada kelime bozulur).
Kullanım: <venv>/bin/python -I gen_samples.py <çıkış_klasörü> [all|piper|cb|cb_canli|karakter|denetle|duzelt|kirp|bark_tara|bark_s<n>|ema|ahenk_neseli,ahenk_sakin,...|adali_vc]
Çıktı: <ad>.mp3 + samples.json (cümle, ses, süre).
"""
import json, os, subprocess, sys, time, urllib.request

OUT = sys.argv[1] if __name__ == "__main__" else None   # build_voice.py içe aktarınca set_out ile verir
if OUT:
    os.makedirs(OUT, exist_ok=True)


def set_out(d):
    global OUT
    OUT = d
    os.makedirs(d, exist_ok=True)

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


STYLES = {"cb": (0.5, 0.5), "cb_canli": (0.8, 0.3), "_adali_b": (0.8, 0.3)}   # (exaggeration, cfg_weight)
ADALI_PITCH = 1.22   # C: B'nin perdesi


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


def bark_model():
    from transformers import AutoProcessor, BarkModel
    if not hasattr(bark_model, "m"):
        bark_model.p = AutoProcessor.from_pretrained("suno/bark")
        bark_model.m = BarkModel.from_pretrained("suno/bark")
        bark_model.m.eval()
    return bark_model.p, bark_model.m


def bark_take(tag, name, text, seed):
    """Bark (Suno, MIT): kendi Türkçe hazır sesleri v2/tr_speaker_0..9 (gerçek kişi kopyası değil). tag = bark_s<n>."""
    import torch, numpy as np, wave
    proc, model = bark_model()
    torch.manual_seed(seed)
    t0 = time.time()
    inputs = proc(text, voice_preset=f"v2/tr_speaker_{tag.split('_s')[1]}")
    with torch.inference_mode():
        audio = model.generate(**inputs, do_sample=True).cpu().numpy().squeeze()
    sr = model.generation_config.sample_rate
    p = os.path.join(OUT, f"{tag}_{name}.wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    out = os.path.join(OUT, f"{tag}_{name}.mp3"); mp3(p, out)
    return {"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out), "gen": round(time.time() - t0, 1), "seed": seed}


def _wav(name, tag, audio, sr):
    import numpy as np, wave
    p = os.path.join(OUT, f"{tag}_{name}.wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(np.asarray(audio, dtype="float32").squeeze(), -1, 1) * 32767).astype(np.int16).tobytes())
    out = os.path.join(OUT, f"{tag}_{name}.mp3"); mp3(p, out)
    return out


def ema_take(tag, name, text, seed):
    """EMA Lightning (Apache-2.0, kod + ağırlık): küçük Türkçe model, tek ses, işlemcide hızlı."""
    from ema_lightning import EMA
    if not hasattr(ema_take, "m"):
        ema_take.m = EMA(device="cpu")
    t0 = time.time()
    sp = ema_take.m.say(text, seed=seed, sample_rate=24000)
    out = _wav(name, tag, sp.audio if hasattr(sp, "audio") else sp.samples, 24000)
    return {"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out), "gen": round(time.time() - t0, 1), "seed": seed}


AHENK_STYLE = {"ahenk_neseli": "cheerful", "ahenk_sakin": "calm", "ahenk_duz": "neutral"}


def ahenk_take(tag, name, text, seed):
    """Ahenk Cep (ağırlıklar CC BY 4.0, atıf zorunlu): tasarlanmış yapay kadın sesi f022 (gerçek kişi değil), üslup seçilir."""
    if not hasattr(ahenk_take, "m"):
        from huggingface_hub import snapshot_download
        d = snapshot_download("ozgurguler/ahenk-cep-tr", allow_patterns=["*.pt", "ahenk_cep.py"])
        sys.path.insert(0, d)
        from ahenk_cep import AhenkCep
        ahenk_take.m = AhenkCep(f"{d}/student.pt", f"{d}/decoder.pt")
    t0 = time.time()
    audio, sr = ahenk_take.m.say(text, style=AHENK_STYLE[tag], seed=seed)
    out = _wav(name, tag, audio, sr)
    return {"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out), "gen": round(time.time() - t0, 1), "seed": seed}


def take(tag, name, text, seed):
    if tag == "adali": return adali_take(tag, name, text, seed)
    if tag.startswith("bark_"): return bark_take(tag, name, text, seed)
    if tag.startswith("ema"): return ema_take(tag, name, text, seed)
    if tag.startswith("ahenk_"): return ahenk_take(tag, name, text, seed)
    return cb_take(tag, name, text, seed)


def regen(tag):
    """Bir sesin bütün cümleleri (tohum 7) + denetim."""
    res = []
    for name, text in LINES:
        res.append(check(take(tag, name, text, 7)))
        print(tag, name, res[-1]["sec"], "sn,", res[-1]["gen"], "sn üretim, hata", res[-1]["cer"], "|", res[-1]["asr"], flush=True)
    return res


def f_ref(out=None):
    """Adalı hedef sesi (F tonu): ahenk_adali kayıtlarından ~10 sn tek örnek. Repoda art/voice/ref/adali_f.mp3 olarak durur."""
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref", "adali_f.mp3")
    if os.path.exists(repo):
        return repo
    os.makedirs(os.path.dirname(repo), exist_ok=True)
    parts = [os.path.join(OUT, f"ahenk_adali_{n}.mp3") for n in ("anlatici_2", "anlatici_6", "anlatici_1")]
    inp, flt = [], ""
    for i, q in enumerate(parts):
        inp += ["-i", q]
        flt += f"[{i}:a]apad=pad_dur=0.25[a{i}];"
    flt += "".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1,atrim=0:10.5[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", flt, "-map", "[o]", "-ac", "1", "-ar", "24000", "-b:a", "96k", repo], check=True)
    return repo


def vc_take(tag, name, text, src_tag):
    """Ses dönüştürme (Chatterbox VC, MIT): src_tag kaydının söyleyişi aynen kalır, ses rengi F'ye döner."""
    import torchaudio
    from chatterbox.vc import ChatterboxVC
    if not hasattr(vc_take, "m"):
        vc_take.m = ChatterboxVC.from_pretrained("cpu")
    t0 = time.time()
    wav = vc_take.m.generate(audio=os.path.join(OUT, f"{src_tag}_{name}.mp3"), target_voice_path=f_ref())
    p = os.path.join(OUT, f"{tag}_{name}.wav")
    torchaudio.save(p, wav, vc_take.m.sr)
    out = os.path.join(OUT, f"{tag}_{name}.mp3"); mp3(p, out)
    return {"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out), "gen": round(time.time() - t0, 1), "src": src_tag}


def pitch_file(src, out, pitch):
    f = f"asetrate=24000*{pitch},aresample=24000,atempo={1 / pitch:.4f}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", f, "-ac", "1", "-b:a", "64k", out], check=True)


def adali_take(tag, name, text, seed):
    """Adalı cümlesi: B üslubuyla oku → perdeyi yükselt (C) → F tonuna dönüştür (VC). Söyleyiş C, ses rengi F."""
    t0 = time.time()
    cb_take("_adali_b", name, text, seed)
    pitch_file(os.path.join(OUT, f"_adali_b_{name}.mp3"), os.path.join(OUT, f"_adali_c_{name}.mp3"), ADALI_PITCH)
    x = vc_take(tag, name, text, "_adali_c")
    x.update(seed=seed, gen=round(time.time() - t0, 1))
    return x


def similarity(files, ref):
    """Ses rengi benzerliği (Chatterbox VoiceEncoder, kosinüs; 1 = aynı ses)."""
    import librosa, numpy as np, torch
    from huggingface_hub import hf_hub_download
    from chatterbox.models.voice_encoder import VoiceEncoder
    if not hasattr(similarity, "ve"):
        ve = VoiceEncoder()
        ve.load_state_dict(torch.load(hf_hub_download("ResembleAI/chatterbox", "ve.pt"), map_location="cpu", weights_only=True))
        similarity.ve = ve.eval()
    load = lambda f: librosa.load(f, sr=16000)[0]
    e = similarity.ve.embeds_from_wavs([load(ref)] + [load(f) for f in files], sample_rate=16000)
    e = e / np.linalg.norm(e, axis=1, keepdims=True)
    return [round(float(e[0] @ v), 3) for v in e[1:]]


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


def fix(done, limit=0.03, tries=5, only=None):
    """Hatalı kaydı başka tohumlarla yeniden üretir, en düşük hatalıyı tutar."""
    out = []
    for x in done:
        ok = x["voice"] in only if only else (x["voice"] in STYLES or x["voice"] == "adali" or x["voice"].startswith(("bark_", "ema", "ahenk_")))
        if ok and x.get("cer", 1) > limit:
            best, keep = x, os.path.join(OUT, "_best.mp3")
            os.replace(os.path.join(OUT, x["file"]), keep)
            for k in range(tries):
                y = check(take(x["voice"], x["id"], x["text"], 100 + k))
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
    if which == "bark_tara":
        # 10 Türkçe Bark sesi, ilk cümle: hangisi doğal ve anlaşılır? (samples.json'a girmez)
        for n in range(10):
            y = check(bark_take(f"bark_s{n}", "tara", LINES[0][1], 7))
            print(f"bark_s{n}", y["sec"], "sn,", y["gen"], "sn üretim, hata", y["cer"], "|", y["asr"], flush=True)
    if which.startswith(("bark_s", "ema", "ahenk_")):
        for tag in which.split(","):
            done = [x for x in done if x["voice"] != tag] + regen(tag)
    if which == "adali_vc":
        # C'nin söyleyişi + F'nin ses tonu (kullanıcı, 23 Ekim): kaynak C (karakter) ve B (cb_canli) denenir
        for src, tag in (("karakter", "vc_c"), ("cb_canli", "vc_b")):
            made = [check(vc_take(tag, n, t, src)) for n, t in LINES]
            done = [x for x in done if x["voice"] != tag] + made
        ref = f_ref()
        for tag in ("ahenk_adali", "karakter", "vc_c", "vc_b"):
            xs = [x for x in done if x["voice"] == tag]
            sims = similarity([os.path.join(OUT, x["file"]) for x in xs], ref)
            for x, v in zip(xs, sims): x["sim_f"] = v
            print(f"{tag:12s} F'ye benzerlik ort. {sum(sims)/len(sims):.3f} | hata ort. %{100*sum(x.get('cer',0) for x in xs)/len(xs):.1f}", flush=True)
    if which == "adali":
        # ilk deneme: adali_vc'nin vc_c kayıtları (tohum 7); hatalılar baştan (B → C → F) yeniden üretilir, sonra kuyruk kırpılır
        base = [dict(x, voice="adali", file="adali_" + x["file"][len("vc_c_"):]) for x in done if x["voice"] == "vc_c"]
        for x in base:
            subprocess.run(["cp", os.path.join(OUT, "vc_c_" + x["id"] + ".mp3"), os.path.join(OUT, x["file"])], check=True)
        done = [x for x in done if x["voice"] != "adali"] + fix(base, only={"adali"})
        done = [trim(x) if x["voice"] == "adali" else x for x in done]
        xs = [x for x in done if x["voice"] == "adali"]
        for x, v in zip(xs, similarity([os.path.join(OUT, x["file"]) for x in xs], f_ref())): x["sim_f"] = v
    if which in ("all", "denetle", "duzelt"):
        done = [check(x) if "cer" not in x or which == "denetle" else x for x in done]
    if which in ("all", "duzelt"):
        done = fix(done)
    if which in ("all", "duzelt", "kirp"):
        done = [trim(x) if x["voice"] in STYLES or x["voice"].startswith(("bark_", "ema", "ahenk_")) else x for x in done]
    if which in ("all", "karakter", "duzelt", "kirp"):
        for src, tag, pitch in (("cb_canli", "karakter", 1.22), ("ahenk_neseli", "ahenk_adali", 1.18)):
            made = [check(x) for x in character(src, tag, pitch)]
            if made:
                done = [x for x in done if x["voice"] != tag] + made
    json.dump(done, open(os.path.join(OUT, "samples.json"), "w"), ensure_ascii=False, indent=1)
    print("bitti", len(done))
