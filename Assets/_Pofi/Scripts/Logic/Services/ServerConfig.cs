using System;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Pofi.Logic.Services
{
    /// <summary>
    /// Sunucu ayarı (Resources/Data/server.json): Supabase adresi + yayınlanabilir (anon/publishable) anahtar.
    /// Boşsa oyun sahte arka uçla (Mock) çalışır. Gizli anahtar (service_role / sb_secret_) asla kabul edilmez:
    /// yanlışlıkla yazılırsa ayar "boş" sayılır.
    /// </summary>
    public sealed class ServerConfig
    {
        public string Url = "";
        public string PublishableKey = "";

        /// <summary>Deneme kodları (K4K4K4, A1A1A1, B2B2B2, C3C3C3) sahte arka uçla açılsın mı (önizleme ve "Test: her şeyi aç").</summary>
        public bool DemoCodes = true;

        public bool IsConfigured =>
            !string.IsNullOrWhiteSpace(Url) && Url.Trim().StartsWith("https://", StringComparison.OrdinalIgnoreCase)
            && !string.IsNullOrWhiteSpace(PublishableKey) && !LooksSecret(PublishableKey);

        public static ServerConfig Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return new ServerConfig();
            try
            {
                var c = JsonConvert.DeserializeObject<ServerConfig>(json) ?? new ServerConfig();
                c.Url = (c.Url ?? "").Trim();
                c.PublishableKey = (c.PublishableKey ?? "").Trim();
                return c;
            }
            catch (JsonException)
            {
                return new ServerConfig();
            }
        }

        /// <summary>Gizli anahtar mı? Yeni biçim "sb_secret_…", eski biçim rolü service_role olan JWT.</summary>
        public static bool LooksSecret(string key)
        {
            if (string.IsNullOrEmpty(key)) return false;
            key = key.Trim();
            if (key.StartsWith("sb_secret_", StringComparison.Ordinal)) return true;
            var parts = key.Split('.');
            if (parts.Length != 3) return false;
            try
            {
                var p = parts[1].Replace('-', '+').Replace('_', '/');
                p += new string('=', (4 - p.Length % 4) % 4);
                var payload = JObject.Parse(Encoding.UTF8.GetString(Convert.FromBase64String(p)));
                return (string)payload["role"] != "anon";
            }
            catch (Exception e) when (e is FormatException || e is JsonException || e is ArgumentException)
            {
                return true;   // çözülemeyen JWT benzeri anahtar: güvenli taraf
            }
        }
    }
}
