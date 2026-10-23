using System.Text;
using System.Text.RegularExpressions;

namespace Pofi.Logic.Audio
{
    /// <summary>
    /// Sesli okuma eşleşmesi (23 Ekim 2026): ekrana yazılan metin → kayıt anahtarı. Etiketler (&lt;b&gt;…) atılır, boşluklar
    /// tekleşir, UTF-8 baytları üzerinde FNV-1a 64 bit, 16 hane küçük onaltılık. art/voice/build_voice.py ile birebir aynı:
    /// kayıt metinle üretilir, oyun yalnız aynı metni gösterince çalar (pet adı değişmişse eşleşmez, yanlış ad duyulmaz).
    /// </summary>
    public static class VoiceKey
    {
        private static readonly Regex Tags = new Regex("<[^>]*>");
        private static readonly Regex Spaces = new Regex(@"\s+");

        public static string Normalize(string text)
        {
            if (string.IsNullOrEmpty(text)) return "";
            return Spaces.Replace(Tags.Replace(text, ""), " ").Trim();
        }

        public static string Of(string text)
        {
            ulong h = 0xcbf29ce484222325UL;
            foreach (var b in Encoding.UTF8.GetBytes(Normalize(text)))
            {
                h ^= b;
                h *= 0x100000001b3UL;
            }
            return h.ToString("x16");
        }
    }
}
