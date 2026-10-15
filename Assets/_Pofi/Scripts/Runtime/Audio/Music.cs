using UnityEngine;

namespace Pofi.Audio
{
    /// <summary>
    /// Arka plan müziği (kullanıcı isteği, 15 Ekim 2026): kodla bestelenmiş telifsiz tropik döngü
    /// (Resources/Audio/music_island.ogg, art/scripts/music_island.py). Sahneler arası kesintisiz çalar;
    /// aç/kapa her ekranda sağ üstteki ♪ düğmesinden (UI.MusicButton), tercih kayıtta (Settings.MusicVolume).
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
                var clip = Resources.Load<AudioClip>("Audio/music_island");
                if (clip == null) return;
                var go = new GameObject("Music");
                Object.DontDestroyOnLoad(go);
                _src = go.AddComponent<AudioSource>();
                _src.clip = clip; _src.loop = true; _src.playOnAwake = false; _src.spatialBlend = 0f; _src.priority = 0;
            }
            _src.volume = Mathf.Clamp01(volume);
            if (!_src.isPlaying) _src.Play();   // WebGL: tarayıcı ilk dokunuşta sesi açar
        }

        public static void SetVolume(float volume)
        {
            if (_src == null) { Init(volume); return; }
            _src.volume = Mathf.Clamp01(volume);
            if (_src.volume > 0f && !_src.isPlaying) _src.Play();
        }
    }
}
