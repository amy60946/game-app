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
            return args == null || args.Length == 0 ? v : string.Format(v, args);
        }
    }
}
