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

        public static bool On => _src != null && _src.volume > 0.001f;

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
            }
            _src.volume = Mathf.Clamp01(volume);
            if (!_src.isPlaying) _src.Play();   // WebGL: tarayıcı ilk dokunuşta sesi açar
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

        public static void SetVolume(float volume)
        {
            if (_src == null) { Init(volume); return; }
            _src.volume = Mathf.Clamp01(volume);
            if (_src.volume > 0f && !_src.isPlaying) _src.Play();
        }
    }
}
