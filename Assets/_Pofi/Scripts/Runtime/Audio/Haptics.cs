using UnityEngine;
#if (UNITY_WEBGL || UNITY_IOS) && !UNITY_EDITOR
using System.Runtime.InteropServices;
#endif

namespace Pofi.Audio
{
    /// <summary>
    /// Aksiyonlarda telefonun kısa, hafif titreşimi (kullanıcı isteği 15 Ekim 2026). WebGL: Plugins/WebGL/PofiHaptics.jslib
    /// (Android: vibrate; iPhone: iOS 18+ sistem dokunsal hissi). Çok sık tetiklenmez (60 ms aralık).
    /// iOS (TestFlight) derlemesi: Plugins/iOS/PofiNative.mm (UIImpactFeedbackGenerator).
    /// </summary>
    public static class Haptics
    {
        public static bool Enabled = true;
        /// <summary>Test için: kaç titreşim istendi.</summary>
        public static int Count { get; private set; }
        private static float _last = -1f;

#if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern void PofiHaptic(int ms);
#elif UNITY_IOS && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern void PofiHapticIOS(int strength);
        [DllImport("__Internal")] private static extern void PofiAudioPlayback();
        /// <summary>iOS: ses oturumunu "playback" yap (sessiz düğmesine rağmen ses duyulsun). Açılışta bir kez.</summary>
        public static void InitAudioSession() { try { PofiAudioPlayback(); } catch { } }
#endif
#if !(UNITY_IOS && !UNITY_EDITOR)
        public static void InitAudioSession() { }
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
#elif UNITY_IOS && !UNITY_EDITOR
            PofiHapticIOS(ms);
#endif
        }
    }
}
