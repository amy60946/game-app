using System;

namespace Pofi.Logic.Auth
{
    /// <summary>
    /// Hatalı kod denemelerinde kısa bekleme (FR-AUTH-3, FR-SAFE-5). Sunucu da ayrıca sınırlar;
    /// bu sınıf istemcide çocuğa nazik geri sayım göstermek içindir. Saat dışarıdan verilir (test edilebilir).
    /// </summary>
    public sealed class LoginThrottle
    {
        private readonly int _freeAttempts;
        private readonly TimeSpan _baseDelay;
        private readonly TimeSpan _maxDelay;
        private int _failures;
        private DateTime _lockedUntilUtc = DateTime.MinValue;

        public LoginThrottle(int freeAttempts = 3, int baseDelaySeconds = 15, int maxDelaySeconds = 300)
        {
            _freeAttempts = freeAttempts;
            _baseDelay = TimeSpan.FromSeconds(baseDelaySeconds);
            _maxDelay = TimeSpan.FromSeconds(maxDelaySeconds);
        }

        public int Failures => _failures;

        public TimeSpan Remaining(DateTime nowUtc) =>
            nowUtc >= _lockedUntilUtc ? TimeSpan.Zero : _lockedUntilUtc - nowUtc;

        public bool CanTry(DateTime nowUtc) => Remaining(nowUtc) == TimeSpan.Zero;

        /// <summary>Başarısız denemeyi kaydeder; ilk birkaç hata serbest, sonra bekleme her seferinde ikiye katlanır.</summary>
        public void RecordFailure(DateTime nowUtc)
        {
            _failures++;
            var over = _failures - _freeAttempts;
            if (over <= 0) return;
            var seconds = Math.Min(_maxDelay.TotalSeconds, _baseDelay.TotalSeconds * Math.Pow(2, over - 1));
            _lockedUntilUtc = nowUtc + TimeSpan.FromSeconds(seconds);
        }

        public void RecordSuccess()
        {
            _failures = 0;
            _lockedUntilUtc = DateTime.MinValue;
        }
    }

    /// <summary>Giriş kodu biçimi: 6 karakter, harf/rakam (sunucudaki random_code ile aynı).</summary>
    public static class ChildCode
    {
        public const int Length = 6;

        /// <summary>Kullanıcı girişini temizler: harf/rakam dışını atar, ASCII küçük harfi büyütür (Türkçe i/ı tuzağına düşmeden).</summary>
        public static string Normalize(string input)
        {
            if (input == null) return "";
            var chars = new System.Text.StringBuilder(Length);
            foreach (var c in input)
            {
                // Yalnızca ASCII: platformların Unicode büyük harf kuralları farklı olabilir (ör. ı → I).
                if (c >= 'a' && c <= 'z') chars.Append((char)(c - 32));
                else if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')) chars.Append(c);
            }
            return chars.ToString();
        }

        public static bool IsWellFormed(string normalized) => normalized != null && normalized.Length == Length;
    }
}
