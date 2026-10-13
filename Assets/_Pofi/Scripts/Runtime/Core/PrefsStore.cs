using Pofi.Logic.Services;
using UnityEngine;

namespace Pofi.Core
{
    /// <summary>
    /// Cihazda kalıcı küçük depo (PlayerPrefs; WebGL'de tarayıcının IndexedDB'si).
    /// Önizleme ve Mock içindir. Gerçek oturum belirteci iOS'ta Keychain'e taşınacak (FR-AUTH-2, M4).
    /// </summary>
    public sealed class PrefsStore : ISecureStore
    {
        public string Get(string key) => PlayerPrefs.HasKey(key) ? PlayerPrefs.GetString(key) : null;

        public void Set(string key, string value)
        {
            PlayerPrefs.SetString(key, value);
            PlayerPrefs.Save();
        }

        public void Delete(string key)
        {
            PlayerPrefs.DeleteKey(key);
            PlayerPrefs.Save();
        }
    }
}
