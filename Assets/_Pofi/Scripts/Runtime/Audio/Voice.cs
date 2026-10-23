using System.Collections.Generic;
using Pofi.Logic.Audio;
using UnityEngine;

namespace Pofi.Audio
{
    /// <summary>
    /// Sesli okuma (23 Ekim 2026, kullanıcı kararı): ekrana gelen hikâye, giriş filmi, ipucu ve adalı cümleleri önceden kaydedilmiş
    /// sesle okunur (anlatıcı B, Okti C, adalılar C'nin söyleyişi + F'nin ses tonu; art/voice/build_voice.py). Metin →
    /// <see cref="VoiceKey"/> → Resources/Voice/v_&lt;anahtar&gt; (IMA ADPCM, ham veriden AudioClip: tarayıcı çözücüsü gerekmez).
    /// Kaydı olmayan metin sessiz geçer. Herkeste açık (Settings.VoiceOn); konuşma balonunun köşesindeki hoparlör
    /// (<see cref="UI.VoiceButton"/>), avatar menüsü ya da Ayarlar'dan kapatılır. Okurken müzik kısılır.
    /// </summary>
    public static class Voice
    {
        public static bool Enabled = true;
        /// <summary>Aç/kapa kayda yazılsın (GameBootstrap verir).</summary>
        public static System.Action<bool> Persist;
        public static string CurrentKey { get; private set; }
        /// <summary>Test/ayıklama: çalınan kayıt sayısı ve son anahtar.</summary>
        public static int Played { get; private set; }
        public static string LastKey { get; private set; }

        private static HashSet<string> _index;
        private static AudioSource _src;
        private static readonly Dictionary<string, AudioClip> Cache = new Dictionary<string, AudioClip>();
        private static readonly List<string> Order = new List<string>();
        private const int CacheSize = 8;

        public static int Count { get { EnsureIndex(); return _index.Count; } }
        public static bool Speaking => _src != null && _src.isPlaying;

        public static bool Has(string text)
        {
            if (string.IsNullOrEmpty(text)) return false;
            EnsureIndex();
            return _index.Contains(VoiceKey.Of(text));
        }

        public static bool IsSpeaking(string text) => Speaking && CurrentKey != null && CurrentKey == VoiceKey.Of(text);

        /// <summary>
        /// Metnin kaydı varsa okur (açıksa). <paramref name="interrupt"/>: kayıt yoksa da öncekini sustur (hikâye ve film satırları:
        /// yeni satırın üstünde eski satır sürmesin). Balon ve ipuçları kaydı olmayan metinde öncekini kesmez.
        /// </summary>
        public static bool Say(string text, bool interrupt = false)
        {
            if (!Enabled) return false;
            if (!Has(text)) { if (interrupt) Stop(); return false; }
            return Play(VoiceKey.Of(text));
        }

        public static void Stop()
        {
            if (_src != null && _src.isPlaying) _src.Stop();
            if (CurrentKey == null) return;
            CurrentKey = null;
            Music.Duck(false);
        }

        /// <summary>Yalnız bu metin okunuyorsa sustur (kapanan balon sıradakinin sesini kesmesin).</summary>
        public static void StopIf(string text)
        {
            if (CurrentKey != null && CurrentKey == VoiceKey.Of(text)) Stop();
        }

        /// <summary>Aç/kapa. Açılınca <paramref name="replay"/> metni baştan okunur.</summary>
        public static void SetEnabled(bool on, string replay = null)
        {
            Enabled = on;
            Persist?.Invoke(on);
            if (!on) Stop();
            else if (replay != null) Say(replay, true);
        }

        /// <summary>Durum (ayıklama komutu "voice").</summary>
        public static string Describe()
        {
            EnsureIndex();
            return $"kayıt={_index.Count} açık={Enabled} okuyor={Speaking} anahtar={CurrentKey ?? "-"} çalınan={Played} son={LastKey ?? "-"}";
        }

        private static bool Play(string key)
        {
            var clip = Load(key);
            if (clip == null) return false;
            EnsureSource();
            _src.Stop();
            _src.clip = clip;
            _src.Play();
            CurrentKey = LastKey = key;
            Played++;
            Music.Duck(true);
            return true;
        }

        private static void EnsureIndex()
        {
            if (_index != null) return;
            _index = new HashSet<string>();
            var asset = Resources.Load<TextAsset>("Voice/index");
            if (asset == null) return;
            foreach (var line in asset.text.Split('\n'))
            {
                var tab = line.IndexOf('\t');
                var k = (tab > 0 ? line.Substring(0, tab) : line).Trim();
                if (k.Length == 16) _index.Add(k);
            }
            Resources.UnloadAsset(asset);
        }

        private static AudioClip Load(string key)
        {
            if (Cache.TryGetValue(key, out var hit) && hit != null) return hit;
            var asset = Resources.Load<TextAsset>("Voice/v_" + key);
            if (asset == null) return null;
            var pcm = ImaAdpcm.Decode(asset.bytes, out var rate);
            Resources.UnloadAsset(asset);
            if (pcm == null || pcm.Length == 0) return null;
            var clip = AudioClip.Create("voice_" + key, pcm.Length, 1, rate, false);
            clip.SetData(pcm, 0);
            Cache[key] = clip;
            Order.Remove(key);
            Order.Add(key);
            while (Order.Count > CacheSize)
            {
                var old = Order[0];
                Order.RemoveAt(0);
                if (old == CurrentKey) { Order.Add(old); continue; }
                if (Cache.TryGetValue(old, out var c) && c != null) Object.Destroy(c);
                Cache.Remove(old);
            }
            return clip;
        }

        private static void EnsureSource()
        {
            if (_src != null) return;
            var go = new GameObject("Voice");
            Object.DontDestroyOnLoad(go);
            _src = go.AddComponent<AudioSource>();
            _src.playOnAwake = false; _src.loop = false; _src.spatialBlend = 0f; _src.priority = 0; _src.volume = 1f;
            go.AddComponent<VoiceWatch>();
        }

        /// <summary>Kayıt kendiliğinden bitince müzik eski düzeyine döner (<see cref="VoiceWatch"/> her kare çağırır).</summary>
        internal static void Watch()
        {
            if (CurrentKey != null && _src != null && !_src.isPlaying && Application.isFocused) { CurrentKey = null; Music.Duck(false); }
        }
    }

    internal sealed class VoiceWatch : MonoBehaviour
    {
        private void Update() => Voice.Watch();
    }
}
