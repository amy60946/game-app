using System.Collections.Generic;
using UnityEngine;

namespace Pofi.Audio
{
    public enum SfxKind { Tap, Pop, Coin, Success, Fail, Whoosh, Chop, Rustle, Clink, Gain, Chime, Sparkle }

    /// <summary>
    /// Ses dosyası gelene kadar kodla üretilen kısa efektler (yumuşak "pop", coin şıngırtısı, başarı arpeji).
    /// Ses düzeyi oyuncu ayarından (<see cref="Volume"/>). WebGL'de ses ilk dokunuştan sonra başlar (tarayıcı kuralı).
    /// </summary>
    public static class Sfx
    {
        public static float Volume = 1f;
        private static AudioSource _src;
        private static readonly Dictionary<SfxKind, AudioClip> Clips = new Dictionary<SfxKind, AudioClip>();
        private const int Rate = 22050;

        public static void Play(SfxKind kind)
        {
            if (Volume <= 0.001f) { if (kind != SfxKind.Whoosh) Haptics.Light(); return; }
            EnsureSource();
            if (!Clips.TryGetValue(kind, out var clip)) Clips[kind] = clip = Make(kind);
            _src.PlayOneShot(clip, Volume * 0.6f);
            if (kind != SfxKind.Whoosh) Haptics.Light();   // her aksiyonda kısa hafif titreşim
        }

        private static void EnsureSource()
        {
            if (_src != null) return;
            var go = new GameObject("Sfx");
            Object.DontDestroyOnLoad(go);
            _src = go.AddComponent<AudioSource>();
            _src.playOnAwake = false;
        }

        private static AudioClip[] _steps;
        private static int _stepIdx;
        /// <summary>Test için: çalınan adım sesi sayısı.</summary>
        public static int Steps { get; private set; }

        /// <summary>
        /// Adım sesi (yürüyüşte ayağın yere değdiği anda, World.PetWalker çağırır): yumuşak "pıt" — süzülmüş kısa hışırtı +
        /// alçak tok vuruş; 4 çeşit sırayla (tekdüze olmasın). Titreşim yok (çok sık).
        /// </summary>
        public static void Step(bool run)
        {
            if (Volume <= 0.001f) return;
            EnsureSource();
            if (_steps == null)
            {
                _steps = new AudioClip[4];
                for (var v = 0; v < 4; v++) _steps[v] = StepClip(v);
            }
            Steps++;
            _stepIdx = (_stepIdx + 1) % _steps.Length;
            _src.PlayOneShot(_steps[_stepIdx], Volume * (run ? 0.42f : 0.32f));
        }

        private static AudioClip StepClip(int variant)
        {
            var n = (int)(Rate * 0.11f);
            var data = new float[n];
            var rng = new System.Random(31 + variant * 17);
            var lp = 0f;
            var thump = 105f + variant * 9f;
            var bright = 0.18f + variant * 0.03f;
            for (var i = 0; i < n; i++)
            {
                var t = i / (float)Rate;
                var noise = (float)(rng.NextDouble() * 2.0 - 1.0);
                lp += bright * (noise - lp);                                   // tek kutuplu alçak geçiren: yumuşak hışırtı
                var env = Mathf.Min(1f, i / (Rate * 0.002f)) * Mathf.Exp(-t * 48f);
                var low = Mathf.Sin(2f * Mathf.PI * thump * t) * Mathf.Exp(-t * 38f);
                data[i] = (lp * 1.6f + low * 0.55f) * env * 0.7f;
            }
            var clip = AudioClip.Create("step" + variant, n, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        private static AudioClip Make(SfxKind kind)
        {
            switch (kind)
            {
                case SfxKind.Tap: return Tone("tap", new[] { 880f }, 0.05f, 0.4f);
                case SfxKind.Pop: return Tone("pop", new[] { 520f, 780f }, 0.07f, 0.6f);
                case SfxKind.Coin: return Tone("coin", new[] { 1318.5f, 1760f }, 0.09f, 0.5f);
                case SfxKind.Success: return Tone("success", new[] { 523.25f, 659.25f, 783.99f, 1046.5f }, 0.09f, 0.55f);
                case SfxKind.Fail: return Tone("fail", new[] { 392f, 311f }, 0.14f, 0.5f);
                case SfxKind.Chop: return Hit("chop", 190f, 0.32f, 0.10f, 0.9f);     // tahta "tok"
                case SfxKind.Rustle: return Hit("rustle", 0f, 0.55f, 0.22f, 0.7f);  // yaprak hışırtısı
                case SfxKind.Clink: return Hit("clink", 1250f, 0.2f, 0.12f, 0.75f); // taş "çın"
                case SfxKind.Gain: return Tone("gain", new[] { 1046.5f, 1318.5f, 1568f, 2093f }, 0.055f, 0.45f);    // XP pete girdi: parlak yükselen pırıltı
                case SfxKind.Chime: return Tone("chime", new[] { 784f, 1174.7f, 1568f }, 0.11f, 0.5f);             // Güneş Taşı: daha tok, çan gibi
                case SfxKind.Sparkle: return Tone("sparkle", new[] { 1568f, 2093f, 2637f, 3136f, 2637f }, 0.04f, 0.35f);  // parıltı açıldı
                default: return Tone("whoosh", new[] { 300f, 600f }, 0.08f, 0.3f);
            }
        }

        /// <summary>Vuruş sesi: kısa süzülmüş gürültü (doku) + sönen ton (gövde; 0 Hz = yalnız gürültü).</summary>
        private static AudioClip Hit(string name, float hz, float noise, float seconds, float amp)
        {
            var n = (int)(Rate * seconds);
            var data = new float[n];
            var rng = new System.Random(name.Length * 31);
            var lp = 0f;
            for (var i = 0; i < n; i++)
            {
                var t = i / (float)Rate;
                lp += 0.35f * ((float)(rng.NextDouble() * 2.0 - 1.0) - lp);
                var env = Mathf.Min(1f, i / (Rate * 0.002f)) * Mathf.Exp(-t * (hz > 0f ? 30f : 14f));
                var tone = hz > 0f ? Mathf.Sin(2f * Mathf.PI * hz * t * (1f - t * 0.8f)) + 0.4f * Mathf.Sin(4.1f * Mathf.PI * hz * t) : 0f;
                data[i] = (tone * (1f - noise) + lp * noise * 2.2f) * env * amp * 0.7f;
            }
            var clip = AudioClip.Create(name, n, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        /// <summary>Notalar art arda; her biri yumuşak başlangıç ve üstel sönümle (tıkırtısız).</summary>
        private static AudioClip Tone(string name, float[] notes, float noteSeconds, float amp)
        {
            var per = (int)(Rate * noteSeconds);
            var tail = (int)(Rate * 0.12f);
            var data = new float[per * notes.Length + tail];
            for (var n = 0; n < notes.Length; n++)
            {
                var len = per + (n == notes.Length - 1 ? tail : per / 2);
                for (var i = 0; i < len && n * per + i < data.Length; i++)
                {
                    var t = i / (float)Rate;
                    var env = Mathf.Min(1f, i / (Rate * 0.004f)) * Mathf.Exp(-t * 18f);
                    var s = Mathf.Sin(2f * Mathf.PI * notes[n] * t) + 0.25f * Mathf.Sin(4f * Mathf.PI * notes[n] * t);
                    data[n * per + i] += s * env * amp * 0.8f;
                }
            }
            var clip = AudioClip.Create(name, data.Length, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }
    }
}
