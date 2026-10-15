using UnityEngine;
#if UNITY_WEBGL && !UNITY_EDITOR
using System.Runtime.InteropServices;
#endif

namespace Pofi.Audio
{
    /// <summary>
    /// Aksiyonlarda telefonun kısa, hafif titreşimi (kullanıcı isteği 15 Ekim 2026). WebGL: Plugins/WebGL/PofiHaptics.jslib
    /// (Android: vibrate; iPhone: iOS 18+ sistem dokunsal hissi). Çok sık tetiklenmez (60 ms aralık).
    /// Yerel (TestFlight) derlemede iOS hafif darbe API'si ile değiştirilecek; şimdilik yalnız WebGL.
    /// </summary>
    public static class Haptics
    {
        public static bool Enabled = true;
        /// <summary>Test için: kaç titreşim istendi.</summary>
        public static int Count { get; private set; }
        private static float _last = -1f;

#if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern void PofiHaptic(int ms);
#endif

        public static void Light() => Pulse(10);
        public static void Medium() => Pulse(22);

        private static void Pulse(int ms)
        {
            if (!Enabled || Time.unscaledTime - _last < 0.06f) return;
            _last = Time.unscaledTime;
            Count++;
#if UNITY_WEBGL && !UNITY_EDITOR
            PofiHaptic(ms);
#endif
        }
    }
}
