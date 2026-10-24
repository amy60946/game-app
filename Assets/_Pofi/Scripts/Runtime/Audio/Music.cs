using UnityEngine;

namespace Pofi.Audio
{
    /// <summary>
    /// Arka plan müziği (kullanıcı isteği, 15 Ekim 2026): kodla bestelenmiş telifsiz tropik döngü
    /// (art/scripts/music_island.py). Sahneler arası kesintisiz çalar;
    /// aç/kapa her ekranda sağ üstteki ♪ düğmesinden (UI.MusicButton), tercih kayıtta (Settings.MusicVolume).
    /// Dosya ham PCM (Resources/Audio/music_island_pcm.bytes: 22050 Hz, mono, 16 bit): WebGL'de sıkıştırılmış ses
    /// tarayıcının çözücüsüne kalıyordu ("Loading FSB failed", iPhone'da müzik yoktu); ham veriden AudioClip kurulunca çözücü gerekmez.
    /// </summary>
    public static class Music
    {
        private static AudioSource _src;
        public const float DefaultVolume = 0.55f;
        private static float _vol;
        private static bool _duck;
        private static int _scene;

        /// <summary>Sesli okuma sürerken müzik bu orana kısılır (<see cref="Voice"/>). 0,35 anlatıcıyı bastırıyordu (kullanıcı, 24 Ekim 2026).</summary>
        public const float DuckLevel = 0.18f;
        /// <summary>Giriş filmi ve hikâye sahnesi boyunca (cümleler arasında da) müzik arka fonda bu düzeyde kalır.</summary>
        public const float SceneLevel = 0.3f;
        /// <summary>Düzey değişimi ani değil: saniyede bu kadar (tam ses oranı) kayar.</summary>
        private const float FadeRate = 1.6f;

        public static bool On => _src != null && _vol > 0.001f;

        public static void Init(float volume)
        {
            if (_src == null)
            {
                var clip = LoadPcm("Audio/music_island_pcm", 22050);
                if (clip == null) return;
                var go = new GameObject("Music");
                Object.DontDestroyOnLoad(go);
                _src = go.AddComponent<AudioSource>();
                _src.clip = clip; _src.loop = true; _src.playOnAwake = false; _src.spatialBlend = 0f; _src.priority = 0;
                go.AddComponent<Fader>();
            }
            _vol = Mathf.Clamp01(volume);
            Apply();
            if (!_src.isPlaying) _src.Play();   // WebGL: tarayıcı ilk dokunuşta sesi açar
        }

        /// <summary>Sesli okuma başlarken/bitince: müzik kısılır, sonra eski düzeyine döner.</summary>
        public static void Duck(bool on)
        {
            _duck = on;
        }

        /// <summary>Film/hikâye sahnesi açılınca true, kapanınca false (iç içe sayılır): müzik arka fona çekilir.</summary>
        public static void Scene(bool on)
        {
            _scene = Mathf.Max(0, _scene + (on ? 1 : -1));
        }

        private static float Target => _vol * (_duck ? DuckLevel : _scene > 0 ? SceneLevel : 1f);

        private static void Apply()
        {
            if (_src != null) _src.volume = Target;
        }

        /// <summary>Kısma/açma yumuşak geçsin (anlatıcı başlarken müzik birden düşüp sıçramasın).</summary>
        private sealed class Fader : MonoBehaviour
        {
            private void Update()
            {
                if (_src == null) return;
                _src.volume = Mathf.MoveTowards(_src.volume, Target, FadeRate * Mathf.Max(_vol, 0.05f) * Time.unscaledDeltaTime);
            }
        }

        /// <summary>Durum (test/hata ayıklama): çalıyor mu, süre ve konum.</summary>
        public static string Describe() => _src == null ? "müzik yok" :
            $"çalıyor={_src.isPlaying} ses={_src.volume:0.00} konum={_src.time:0.0}/{(_src.clip != null ? _src.clip.length : 0f):0.0} sn";

        private static AudioClip LoadPcm(string path, int rate)
        {
            var asset = Resources.Load<TextAsset>(path);
            if (asset == null) return null;
            var bytes = asset.bytes;
            var n = bytes.Length / 2;
            var data = new float[n];
            for (var i = 0; i < n; i++) data[i] = (short)(bytes[2 * i] | (bytes[2 * i + 1] << 8)) / 32768f;
            var clip = AudioClip.Create("music_island", n, 1, rate, false);
            clip.SetData(data, 0);
            Resources.UnloadAsset(asset);
            return clip;
        }

        /// <summary>Ses oturumu yeniden kurulunca (iOS) ya da uygulamaya dönünce: açıksa çalmaya devam et.</summary>
        public static void Resume()
        {
            if (_src == null || _vol <= 0.001f || _src.isPlaying) return;
            _src.Play();
        }

        public static void SetVolume(float volume)
        {
            if (_src == null) { Init(volume); return; }
            _vol = Mathf.Clamp01(volume);
            Apply();
            if (_vol > 0f && !_src.isPlaying) _src.Play();
        }
    }
}
