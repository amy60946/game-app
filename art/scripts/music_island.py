# Pofi Adası arka plan müziği — tamamen kodla bestelenmiş, telifsiz, döngüye uygun (kullanıcı isteği 15 Ekim 2026).
# Tarz: huzurlu tropik oyun müziği (sıcak ukulele tıngırtısı, marimba melodisi, yumuşak bas, hafif shaker/tık);
# 104 BPM, Do majör, "tresillo" (3+3+2) ritmi. Hiçbir mevcut eserden alıntı yoktur; melodi sabit tohumla bu betikte üretilir.
# Kullanım: python3 music_island.py çıktı.wav   (ffmpeg varsa .ogg da yazılır)
import sys, math, subprocess, numpy as np

SR = 32000
BPM = 104
BEAT = 60.0 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(7)

def note_hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def env(n, a=0.005, d=0.5):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / d)
    return e

def marimba(m, dur, vel=0.5):
    n = int(SR * min(dur + 0.6, 1.4)); t = np.arange(n) / SR; f = note_hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.06) + 0.08 * np.sin(2 * np.pi * f * 10 * t) * np.exp(-t / 0.02)
    return vel * s * env(n, 0.002, 0.42)

def flute(m, dur, vel=0.25):
    n = int(SR * (dur + 0.15)); t = np.arange(n) / SR; f = note_hz(m)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.25)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    s = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.04 * np.sin(3 * ph)
    a = np.minimum(1, t / 0.06) * np.clip((dur + 0.15 - t) / 0.15, 0, 1)
    breath = rng.normal(0, 1, n) * 0.02 * a
    return vel * (s * a + breath)

def pluck(m, dur, vel=0.3, bright=0.5):
    """Karplus–Strong telli (ukulele)."""
    f = note_hz(m); N = int(SR / f); n = int(SR * (dur + 0.8))
    buf = rng.uniform(-1, 1, N + 6)
    buf = np.convolve(buf, np.ones(6) / 6, 'valid')[:N]          # yumuşak (sıcak) tel vuruşu
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * vel
    out = np.zeros(n); idx = 0
    damp = 0.996 - (1 - bright) * 0.004
    b = buf.copy()
    for i in range(n):
        out[i] = b[idx]
        nxt = (idx + 1) % N
        b[idx] = damp * 0.5 * (b[idx] + b[nxt])
        idx = nxt
    return out * np.exp(-np.arange(n) / SR / 1.2)

def bass(m, dur, vel=0.45):
    n = int(SR * (dur + 0.2)); t = np.arange(n) / SR; f = note_hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return vel * s * env(n, 0.01, 0.55) * np.clip((dur + 0.2 - t) / 0.2, 0, 1)

def shaker(vel=0.08):
    n = int(SR * 0.09); x = rng.normal(0, 1, n)
    x = np.diff(np.concatenate([[0], x]))                 # tiz (yüksek geçiren)
    return vel * x * env(n, 0.004, 0.03)

def kick(vel=0.35):
    n = int(SR * 0.25); t = np.arange(n) / SR
    f = 110 * np.exp(-t / 0.05) + 45
    return vel * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.12)

def tick(vel=0.12):
    n = int(SR * 0.05); t = np.arange(n) / SR
    return vel * np.sin(2 * np.pi * 1800 * t) * env(n, 0.0005, 0.012)

# akorlar (MIDI kökleri ve akor tonları) — A: C Am F G, B: F G Em Am, son: F G C C
C, Am, F, G, Em, Dm = [60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 55, 59], [50, 53, 57]
A = [C, Am, F, G]; Bp = [F, G, Em, Am]; END = [Dm, G, C, C]
song = A + A + Bp + END + A + [F, G, C, C] + Bp + END     # 32 ölçü
total_bars = len(song)
length = int(SR * (total_bars * BAR + 2.0))
mix = {k: np.zeros(length) for k in ('uke', 'mel', 'bass', 'perc')}

def put(track, start_s, sig):
    i = int(start_s * SR); j = min(length, i + len(sig))
    mix[track][i:j] += sig[: j - i]

PENT = [0, 2, 4, 7, 9]                                       # majör pentatonik
def melody_bar(chord, motif_seed, section):
    r = np.random.default_rng(motif_seed)
    # 8'lik ızgara: motif ritmi (1 = nota)
    rhythms = [[1, 0, 1, 1, 0, 1, 1, 0], [1, 1, 0, 1, 0, 1, 0, 0], [1, 0, 0, 1, 1, 0, 1, 1], [1, 0, 1, 0, 1, 1, 0, 0]]
    rh = rhythms[r.integers(len(rhythms))]
    root = chord[0] + 12
    notes = []
    prev = root + 4
    for k, on in enumerate(rh):
        if not on: continue
        # güçlü zamanlarda akor tonu, zayıflarda pentatonik komşu
        if k in (0, 4): cand = [c + 12 for c in chord] + [c + 24 for c in chord]
        else: cand = [60 + 12 + p for p in PENT] + [60 + p + 12 - 12 for p in PENT]
        cand = sorted(cand, key=lambda x: abs(x - prev) + r.uniform(0, 3))
        n = cand[0]; prev = n
        notes.append((k * BEAT / 2, n))
    return notes

for b, chord in enumerate(song):
    t0 = b * BAR
    section = 'B' if 8 <= b < 16 or 24 <= b < 28 else 'A'
    # ukulele: tresillo tıngırtı (0, 0.75, 1.5 vuruş) + 3. ve 4. vuruşta kısa vuruşlar
    for k, at in enumerate([0, 1.5, 3.0, 3.5]):
        for s_i, m in enumerate(sorted(chord)):
            put('uke', t0 + at * BEAT + s_i * 0.012, pluck(m, 0.4, vel=0.16 if k else 0.2, bright=0.6))
    # bas: kök 1. vuruş, beşli 3. vuruş, bazen geçiş
    put('bass', t0, bass(chord[0] - 12, BEAT * 1.4))
    put('bass', t0 + 2 * BEAT, bass(chord[0] - 12 + (7 if chord[0] % 12 != 4 else 3) - 12 + 12, BEAT * 1.2, 0.35))
    # vurmalı: kick 1 ve 3, tık 2 ve 4, shaker sekizlikler
    put('perc', t0, kick()); put('perc', t0 + 2 * BEAT, kick(0.25))
    put('perc', t0 + BEAT, tick()); put('perc', t0 + 3 * BEAT, tick())
    for e in range(8): put('perc', t0 + e * BEAT / 2, shaker(0.035 if e % 2 else 0.05))
    # melodi: A bölümünde marimba, B'de flüt; motif 2 ölçüde bir tekrar eder (akılda kalıcı)
    seed = 100 + (b % 2) + (0 if section == 'A' else 50) + (b // 8) % 2 * 7
    for (dt, m) in melody_bar(chord, seed, section):
        if section == 'A': put('mel', t0 + dt, marimba(m, BEAT / 2, 0.32))
        else: put('mel', t0 + dt, flute(m, BEAT * 0.45, 0.2))

out = mix['uke'] * 0.6 + mix['mel'] * 1.1 + mix['bass'] * 0.9 + mix['perc'] * 0.55
# basit oda yankısı (birkaç gecikme)
rev = np.zeros_like(out)
for d, g in ((0.031, 0.22), (0.047, 0.17), (0.071, 0.12), (0.113, 0.08)):
    k = int(d * SR); rev[k:] += out[:-k] * g
out = out + rev
# döngü: kuyruğu başa kat, tam ölçü sınırında kes
L = int(SR * total_bars * BAR)
tail = out[L:]; out = out[:L].copy(); out[: len(tail)] += tail
out /= np.max(np.abs(out)) + 1e-9
out *= 0.8
pcm = (out * 32767).astype('<i2')
path = sys.argv[1]
import wave
with wave.open(path, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(path, round(L / SR, 1), 's')
