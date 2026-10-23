"""
Sesli okuma örnekleri (V7, 23 Ekim 2026): aynı cümleler iki ücretsiz, ticari kullanıma açık Türkçe sesle.
  A) Chatterbox Multilingual (Resemble AI, MIT): doğal, duygulu; bulutta önceden kaydedilir, oyuna ses dosyası olarak girer.
  B) Piper tr_TR dfki (MIT motor): hafif, telefonda da çalışır; daha düz.
Kullanım: <venv>/bin/python -I gen_samples.py <çıkış_klasörü>
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


def chatterbox(prompt=None, tag="cb", exaggeration=0.5, cfg=0.5):
    import torch, torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.manual_seed(7)
    model = chatterbox.model if hasattr(chatterbox, "model") else ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    chatterbox.model = model
    res = []
    for name, text in LINES:
        t0 = time.time()
        wav = model.generate(text, language_id="tr", audio_prompt_path=prompt, exaggeration=exaggeration, cfg_weight=cfg)
        p = os.path.join(OUT, f"{tag}_{name}.wav")
        torchaudio.save(p, wav, model.sr)
        out = os.path.join(OUT, f"{tag}_{name}.mp3"); mp3(p, out)
        res.append({"id": name, "voice": tag, "text": text, "file": os.path.basename(out), "sec": duration(out), "gen": round(time.time() - t0, 1)})
        print(tag, name, res[-1]["sec"], "sn ses,", res[-1]["gen"], "sn üretim", flush=True)
    return res


if __name__ == "__main__":
    which = sys.argv[2] if len(sys.argv) > 2 else "all"
    done = json.load(open(os.path.join(OUT, "samples.json"))) if os.path.exists(os.path.join(OUT, "samples.json")) else []
    if which in ("all", "piper"):
        done = [x for x in done if x["voice"] != "piper"] + piper()
    if which in ("all", "cb"):
        done = [x for x in done if x["voice"] != "cb"] + chatterbox()
    if which in ("all", "cb_tr"):
        # Türkçe vurgulu ses: Piper'ın Türkçe kaydı Chatterbox'a ses örneği olarak verilir (dışarıdan kişi sesi kullanılmaz)
        ref = os.path.join(OUT, "_ref.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(OUT, "piper_anlatici_2.mp3"), ref], check=True)
        done = [x for x in done if x["voice"] != "cb_tr"] + chatterbox(prompt=ref, tag="cb_tr", exaggeration=0.6, cfg=0.4)
    json.dump(done, open(os.path.join(OUT, "samples.json"), "w"), ensure_ascii=False, indent=1)
    print("bitti", len(done))
