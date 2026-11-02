using System.Collections.Generic;
using Newtonsoft.Json;

namespace Pofi.Logic.Core
{
    /// <summary>Basit metin tablosu. Eksik anahtar "[anahtar]" olarak görünür (eksikler testte yakalanır).</summary>
    public sealed class Localization
    {
        private readonly Dictionary<string, string> _s;

        private sealed class File { [JsonProperty("strings")] public Dictionary<string, string> Strings = new Dictionary<string, string>(); }

        public Localization(string json) { _s = JsonConvert.DeserializeObject<File>(json).Strings; }

        public bool Has(string key) => _s.ContainsKey(key);

        public string Get(string key, params object[] args)
        {
            if (!_s.TryGetValue(key, out var v)) return "[" + key + "]";
            var r = args == null || args.Length == 0 ? v : string.Format(v, args);
            if (_s.TryGetValue(key + ".say", out var say)) Remember(r, args == null || args.Length == 0 ? say : string.Format(say, args));
            return r;
        }

        // ------------------------------------------------------------------ sesli okuma eşleri (GB20, 2 Kasım 2026)
        // Görev adı, ebeveyn adı gibi değişen bilgi taşıyan cümle önceden kaydedilemez: ekranda tam metin durur, ses "<anahtar>.say"daki
        // genel cümleyi okur ("Ailenden bir not getirdim! Bir görevini bir daha dener misin?"). Get bu eşi hatırlar; Voice sorar.
        private readonly Dictionary<string, string> _spoken = new Dictionary<string, string>();

        private void Remember(string shown, string said)
        {
            if (_spoken.Count > 256) _spoken.Clear();
            _spoken[shown] = said;
        }

        /// <summary>Ekrandaki metnin okunacak genel eşi (yoksa null).</summary>
        public string SpokenFor(string shown) => shown != null && _spoken.TryGetValue(shown, out var s) ? s : null;
    }
}
