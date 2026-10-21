using System.Runtime.InteropServices;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Supabase;

namespace Pofi.Core
{
    /// <summary>
    /// Oturum belirteci deposu (güvenlik denetimi M4, FR-AUTH-2): iOS'ta yenileme belirteci Keychain'de (yalnız bu cihaz),
    /// diğer anahtarlar ve diğer platformlar <see cref="PrefsStore"/>. Eski sürümden PlayerPrefs'te kalan belirteç ilk okumada
    /// Keychain'e taşınır ve PlayerPrefs'ten silinir. Keychain yazılamazsa PlayerPrefs'e düşer (oturum kaybolmasın).
    /// </summary>
    public sealed class SecureStore : ISecureStore
    {
        private readonly PrefsStore _prefs = new PrefsStore();

        private static bool Secret(string key) => key == SupabaseAuthService.RefreshKey;

#if UNITY_IOS && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern int PofiKeychainSet(string key, string value);
        [DllImport("__Internal")] private static extern string PofiKeychainGet(string key);
        [DllImport("__Internal")] private static extern void PofiKeychainDelete(string key);

        public string Get(string key)
        {
            if (!Secret(key)) return _prefs.Get(key);
            var v = PofiKeychainGet(key);
            if (!string.IsNullOrEmpty(v)) return v;
            var old = _prefs.Get(key);                       // eski sürüm: taşı
            if (!string.IsNullOrEmpty(old) && PofiKeychainSet(key, old) == 1) _prefs.Delete(key);
            return old;
        }

        public void Set(string key, string value)
        {
            if (!Secret(key)) { _prefs.Set(key, value); return; }
            if (PofiKeychainSet(key, value ?? "") == 1) _prefs.Delete(key);
            else _prefs.Set(key, value);
        }

        public void Delete(string key)
        {
            if (Secret(key)) PofiKeychainDelete(key);
            _prefs.Delete(key);
        }
#else
        public string Get(string key) => _prefs.Get(key);
        public void Set(string key, string value) => _prefs.Set(key, value);
        public void Delete(string key) => _prefs.Delete(key);
#endif
    }
}
