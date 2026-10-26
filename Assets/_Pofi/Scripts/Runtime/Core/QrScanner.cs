using System;
using System.Runtime.InteropServices;
using Pofi.Logic.Auth;
using UnityEngine;

namespace Pofi.Core
{
    /// <summary>
    /// QR ile oyuna bağlanma (26 Ekim 2026, kullanıcı: "QR ile ilerleriz; kodla da giriş yapılabildiği için PC'de o kullanılır";
    /// ortak akislar.md §2.0). Yalnız iOS uygulamasında: yerel kamera okuyucu (Plugins/iOS/PofiNative.mm, AVFoundation) tam ekran açılır,
    /// ilk QR'ı okuyunca kapanır. Tarayıcı / bilgisayar / düzenleyicide <see cref="Available"/> false: giriş ekranı kod kutusuyla kalır.
    /// Görüntü kaydedilmez, gönderilmez; yalnız okunan metin döner.
    /// </summary>
    public sealed class QrScanner : MonoBehaviour
    {
        private const string Receiver = "PofiQr";
        private static QrScanner _inst;
        private Action<string, string> _done;   // (okunan metin, iptal nedeni: "cancel" | "denied" | "nocamera")

#if UNITY_IOS && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern int PofiQrAvailable();
        [DllImport("__Internal")] private static extern void PofiQrScan(string receiver, string title, string cancel);
        public static bool Available { get { try { return PofiQrAvailable() == 1; } catch { return false; } } }
#else
        public static bool Available => false;
#endif

        /// <summary>Kamerayı açar; sonuç ana iş parçacığında: done(metin, null) ya da done(null, neden).</summary>
        public static void Scan(string title, string cancel, Action<string, string> done)
        {
            if (!Available) { done?.Invoke(null, "nocamera"); return; }
            if (_inst == null)
            {
                var go = new GameObject(Receiver);
                DontDestroyOnLoad(go);
                _inst = go.AddComponent<QrScanner>();
            }
            _inst._done = done;
#if UNITY_IOS && !UNITY_EDITOR
            PofiQrScan(Receiver, title, cancel);
#endif
        }

        // yerel taraftan (UnitySendMessage)
        public void OnQrScanned(string text) { var d = _done; _done = null; d?.Invoke(text, null); }
        public void OnQrCancel(string reason) { var d = _done; _done = null; d?.Invoke(null, string.IsNullOrEmpty(reason) ? "cancel" : reason); }
    }

    /// <summary>
    /// <c>pofiadasi://baglan?kod=…</c> bağlantısı (telefonun kendi kamerasıyla QR okutulunca oyun açılır). Güvenlik: kod yalnız giriş
    /// kutusuna YAZILIR, giriş kendiliğinden başlamaz (başka bir sitenin bağlantısı cihazı habersizce başka hesaba bağlayamasın);
    /// oturum açıksa yok sayılır (LoginScreen yalnız oturum yokken açılır).
    /// </summary>
    public static class DeepLink
    {
        public static string PendingCode { get; private set; }
        public static event Action Arrived;
        private static bool _init;

        public static void Init()
        {
            if (_init) return;
            _init = true;
            Application.deepLinkActivated += Handle;
            if (!string.IsNullOrEmpty(Application.absoluteURL)) Handle(Application.absoluteURL);
        }

        private static void Handle(string url)
        {
            if (string.IsNullOrEmpty(url) || !url.StartsWith(ChildCode.Scheme, StringComparison.OrdinalIgnoreCase)) return;
            var code = ChildCode.FromScan(url);
            if (code == null) return;
            PendingCode = code;
            Arrived?.Invoke();
        }

        /// <summary>Bekleyen kodu bir kez verir.</summary>
        public static string Take() { var c = PendingCode; PendingCode = null; return c; }
    }
}
