using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;

namespace Pofi.Logic.Pet
{
    public enum NameCheck { Ok, TooShort, TooLong, InvalidCharacters, NotAllowed }

    /// <summary>
    /// Pet ismi kuralları (FR-PET-2): 2–12 karakter, yalnızca harf (Türkçe dahil), kelimeler arasında tek boşluk,
    /// uygunsuz kelime filtresi. Hata mesajları yerelleştirme anahtarıyla gösterilir (pet.name.*).
    /// </summary>
    public sealed class PetNameRules
    {
        public const int Min = 2, Max = 12;

        private readonly HashSet<string> _words;
        private readonly List<string> _contains;

        private sealed class Blocklist
        {
            [JsonProperty("contains")] public List<string> Contains = new List<string>();
            [JsonProperty("words")] public List<string> Words = new List<string>();
        }

        public PetNameRules(string blocklistJson)
        {
            var b = JsonConvert.DeserializeObject<Blocklist>(blocklistJson);
            _contains = b.Contains.Select(Fold).ToList();
            _words = new HashSet<string>(b.Words.Select(Fold));
        }

        /// <summary>Boşlukları düzenler: baş/son boşluk atılır, çoklu boşluk teke iner.</summary>
        public static string Tidy(string raw) =>
            string.Join(" ", (raw ?? "").Split(new[] { ' ', '\t', '\n' }, StringSplitOptions.RemoveEmptyEntries));

        public NameCheck Check(string raw)
        {
            var name = Tidy(raw);
            if (name.Length < Min) return NameCheck.TooShort;
            if (name.Length > Max) return NameCheck.TooLong;
            foreach (var c in name)
                if (c != ' ' && !IsAllowedLetter(c)) return NameCheck.InvalidCharacters;

            var folded = Fold(name);
            var compact = folded.Replace(" ", "");
            if (_contains.Any(w => compact.Contains(w))) return NameCheck.NotAllowed;
            if (folded.Split(' ').Any(_words.Contains) || _words.Contains(compact)) return NameCheck.NotAllowed;
            return NameCheck.Ok;
        }

        private static bool IsAllowedLetter(char c) =>
            (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || "çğıöşüÇĞİÖŞÜâîûÂÎÛ".IndexOf(c) >= 0;

        /// <summary>Karşılaştırma için sadeleştirme (kültürden bağımsız, elle eşleme).</summary>
        public static string Fold(string s)
        {
            var sb = new StringBuilder(s.Length);
            char prev = '\0';
            foreach (var ch in s)
            {
                char c;
                switch (ch)
                {
                    case 'ç': case 'Ç': c = 'c'; break;
                    case 'ğ': case 'Ğ': c = 'g'; break;
                    case 'ı': case 'I': case 'İ': case 'î': case 'Î': c = 'i'; break;
                    case 'ö': case 'Ö': c = 'o'; break;
                    case 'ş': case 'Ş': c = 's'; break;
                    case 'ü': case 'Ü': case 'û': case 'Û': c = 'u'; break;
                    case 'â': case 'Â': c = 'a'; break;
                    case '0': c = 'o'; break;
                    case '1': c = 'i'; break;
                    case '3': c = 'e'; break;
                    case '4': c = 'a'; break;
                    case '5': c = 's'; break;
                    case '@': c = 'a'; break;
                    case '$': c = 's'; break;
                    default: c = ch >= 'A' && ch <= 'Z' ? (char)(ch + 32) : ch; break;
                }
                if (c == prev && c != ' ') continue; // "siiik" → "sik"
                sb.Append(c);
                prev = c;
            }
            return sb.ToString();
        }
    }
}
