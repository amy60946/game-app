using System.Collections.Generic;
using UnityEngine;

namespace Pofi.Audio
{
    public enum SfxKind { Tap, Pop, Coin, Success, Fail, Whoosh }

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
            if (Volume <= 0.001f) return;
            if (_src == null)
            {
                var go = new GameObject("Sfx");
                Object.DontDestroyOnLoad(go);
                _src = go.AddComponent<AudioSource>();
                _src.playOnAwake = false;
            }
            if (!Clips.TryGetValue(kind, out var clip)) Clips[kind] = clip = Make(kind);
            _src.PlayOneShot(clip, Volume * 0.6f);
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
                default: return Tone("whoosh", new[] { 300f, 600f }, 0.08f, 0.3f);
            }
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
