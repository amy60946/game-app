using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Safety
{
    /// <summary>Ebeveyn kapısı sorusu: sayılar YAZIYLA sorulur (küçük çocuk okuyup çözemesin), 4 seçenekten biri doğru.</summary>
    public sealed class GateChallenge
    {
        public string Prompt;          // "yedi çarpı sekiz kaç eder?"
        public int Answer;
        public List<int> Options = new List<int>();
    }

    /// <summary>
    /// Ebeveyn kapısı (FR-SET-1, Apple Kids kuralı): ayarlar, dış işlemler, pet değiştirme vb. önünde.
    /// Zorluk yaş bandına göre artar: büyük çocuğun da kolayca geçmemesi için C'de iki basamaklı çarpma.
    /// </summary>
    public static class ParentGate
    {
        /// <summary>Soruyu ebeveyn çözer: güvenlik denetimi L2 (22 Ekim 2026) sonrası her bantta iki basamaklı çarpma.
        /// (Eskiden A bandında 6–9 × 6–9 idi; 8 yaşındaki çocuk bilir.) Bant parametresi uyumluluk için kalır.</summary>
        public static GateChallenge Create(AgeBand band, Random rng) => CreateFor(AgeBand.C, rng);

        private static GateChallenge CreateFor(AgeBand band, Random rng)
        {
            int a, b;
            switch (band)
            {
                case AgeBand.K:
                case AgeBand.A: a = rng.Next(6, 10); b = rng.Next(6, 10); break;     // 6–9 × 6–9
                case AgeBand.B: a = rng.Next(11, 20); b = rng.Next(3, 10); break;    // 11–19 × 3–9
                default: a = rng.Next(12, 30); b = rng.Next(12, 20); break;          // 12–29 × 12–19
            }
            var answer = a * b;
            var options = new HashSet<int> { answer };
            while (options.Count < 4)
            {
                var off = rng.Next(1, 4) * (rng.Next(2) == 0 ? -1 : 1) * (band.Young() ? 1 : b);
                if (answer + off > 0) options.Add(answer + off);
            }
            return new GateChallenge
            {
                Prompt = $"{TurkishNumber.ToWords(a)} çarpı {TurkishNumber.ToWords(b)} kaç eder?",
                Answer = answer,
                Options = options.OrderBy(_ => rng.Next()).ToList(),
            };
        }
    }

    /// <summary>İki yanlış cevaptan sonra 30 sn bekleme (rastgele dokunarak geçilmesin; L2).</summary>
    public sealed class GateLock
    {
        public const int MaxFails = 2;
        public static readonly TimeSpan Wait = TimeSpan.FromSeconds(30);
        private int _fails;
        private DateTime _until;

        public TimeSpan Remaining(DateTime nowUtc) => nowUtc < _until ? _until - nowUtc : TimeSpan.Zero;

        public void Fail(DateTime nowUtc)
        {
            if (++_fails >= MaxFails) { _until = nowUtc + Wait; _fails = 0; }
        }

        public void Pass() => _fails = 0;
    }

    public static class TurkishNumber
    {
        private static readonly string[] Ones = { "", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz" };
        private static readonly string[] Tens = { "", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan" };

        /// <summary>0–9999 arası sayıyı Türkçe yazıya çevirir ("yüz", "bin" başında "bir" almaz).</summary>
        public static string ToWords(int n)
        {
            if (n == 0) return "sıfır";
            if (n < 0 || n > 9999) throw new ArgumentOutOfRangeException(nameof(n));
            var parts = new List<string>();
            var th = n / 1000; n %= 1000;
            if (th > 0) parts.Add(th == 1 ? "bin" : Ones[th] + " bin");
            var h = n / 100; n %= 100;
            if (h > 0) parts.Add(h == 1 ? "yüz" : Ones[h] + " yüz");
            if (n / 10 > 0) parts.Add(Tens[n / 10]);
            if (n % 10 > 0) parts.Add(Ones[n % 10]);
            return string.Join(" ", parts);
        }
    }
}
