using System;
using System.Linq;
using Pofi.Logic.Safety;

namespace Pofi.Logic.Core
{
    /// <summary>
    /// Türkçe ek uyumu: pet adları çocuk tarafından seçildiği için ekler koddan üretilir.
    /// Kesme işaretiyle özel ad + ek: "Pofi'nin", "Arlo'yu", "Boncuk'un"; sayılar: "3'te", "6'da".
    /// </summary>
    public static class TurkishSuffix
    {
        private const string Vowels = "aeıioöuüAEIİOÖUÜ";
        private const string Hard = "fstkçşhpFSTKÇŞHP"; // fıstıkçı şahap

        private static char LastVowel(string word)
        {
            for (var i = word.Length - 1; i >= 0; i--)
                if (Vowels.IndexOf(word[i]) >= 0) return Lower(word[i]);
            return 'e';
        }

        private static char Lower(char c)
        {
            switch (c)
            {
                case 'I': return 'ı';
                case 'İ': return 'i';
                case 'Ö': return 'ö';
                case 'Ü': return 'ü';
                default: return char.ToLowerInvariant(c);
            }
        }

        private static bool EndsWithVowel(string w) => w.Length > 0 && Vowels.IndexOf(w[w.Length - 1]) >= 0;

        /// <summary>Dört yönlü ünlü: ı, i, u, ü.</summary>
        private static char High(char lastVowel)
        {
            switch (lastVowel)
            {
                case 'a': case 'ı': return 'ı';
                case 'e': case 'i': return 'i';
                case 'o': case 'u': return 'u';
                default: return 'ü';
            }
        }

        /// <summary>İki yönlü ünlü: a, e.</summary>
        private static char Low(char lastVowel) => "aıou".IndexOf(lastVowel) >= 0 ? 'a' : 'e';

        /// <summary>İlgi hâli: Pofi'nin, Boncuk'un, Pıtı'nın, Arlo'nun.</summary>
        public static string Genitive(string name)
        {
            var w = name.Trim();
            var v = High(LastVowel(w));
            return w + "'" + (EndsWithVowel(w) ? "n" : "") + v + "n";
        }

        /// <summary>Belirtme hâli: Pofi'yi, Boncuk'u, Arlo'yu, Pıtı'yı.</summary>
        public static string Accusative(string name)
        {
            var w = name.Trim();
            var v = High(LastVowel(w));
            return w + "'" + (EndsWithVowel(w) ? "y" : "") + v;
        }

        /// <summary>Yönelme hâli: Pofi'ye, Boncuk'a, Arlo'ya, Okti'ye.</summary>
        public static string Dative(string name)
        {
            var w = name.Trim();
            var v = Low(LastVowel(w));
            return w + "'" + (EndsWithVowel(w) ? "y" : "") + v;
        }

        /// <summary>Bulunma hâli sayıyla: 1'de, 3'te, 6'da, 10'da, 40'ta.</summary>
        public static string Locative(int n)
        {
            var spoken = TurkishNumber.ToWords(n).Split(' ').Last();
            var v = Low(LastVowel(spoken));
            var hard = Hard.IndexOf(spoken[spoken.Length - 1]) >= 0;
            return n + "'" + (hard ? "t" : "d") + v;
        }
    }
}
