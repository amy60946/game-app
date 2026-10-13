namespace Pofi.Logic.Services
{
    /// <summary>
    /// Cihazda güvenli anahtar-değer saklama (iOS Keychain / Android Keystore). Mantık katmanı
    /// platformu bilmez; Unity tarafında gerçek uygulaması, testlerde bellek içi sürümü kullanılır.
    /// </summary>
    public interface ISecureStore
    {
        string Get(string key);
        void Set(string key, string value);
        void Delete(string key);
    }

    public sealed class MemorySecureStore : ISecureStore
    {
        private readonly System.Collections.Generic.Dictionary<string, string> _d =
            new System.Collections.Generic.Dictionary<string, string>();
        public string Get(string key) => _d.TryGetValue(key, out var v) ? v : null;
        public void Set(string key, string value) => _d[key] = value;
        public void Delete(string key) => _d.Remove(key);
    }
}
