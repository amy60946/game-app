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

        /// <summary>QR / bağlantı şeması (ortak akislar.md §2.0): <c>pofiadasi://baglan?kod=AB12CD</c>.</summary>
        public const string Scheme = "pofiadasi://";

        /// <summary>
        /// Okunan QR ya da açılan bağlantıdan giriş kodu (26 Ekim 2026). Kabul: bizim şemamız (<c>pofiadasi://baglan?kod=…</c>, büyük/küçük
        /// harf fark etmez) ya da yalnız kodun kendisi (boşluk/tire olabilir). Başka bağlantılar (https://…, başka şema) ve 6 karakter
        /// tutmayan her şey null — kod denemesi sayılmaz.
        /// </summary>
        public static string FromScan(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return null;
            var t = text.Trim();
            if (t.IndexOf("://", System.StringComparison.Ordinal) >= 0)
            {
                if (!t.StartsWith(Scheme, System.StringComparison.OrdinalIgnoreCase)) return null;
                var rest = t.Substring(Scheme.Length);
                var q = rest.IndexOf('?');
                if (q < 0) return null;
                var path = rest.Substring(0, q).TrimEnd('/');
                if (!string.Equals(path, "baglan", System.StringComparison.OrdinalIgnoreCase)) return null;
                foreach (var part in rest.Substring(q + 1).Split('&'))
                {
                    var eq = part.IndexOf('=');
                    if (eq <= 0 || !string.Equals(part.Substring(0, eq), "kod", System.StringComparison.OrdinalIgnoreCase)) continue;
                    var code = Normalize(System.Uri.UnescapeDataString(part.Substring(eq + 1)));
                    return IsWellFormed(code) ? code : null;
                }
                return null;
            }
            // yalnız kod: harf, rakam, boşluk ve tire dışında karakter varsa (cümle, adres) bizim değil
            foreach (var c in t)
                if (!(char.IsLetterOrDigit(c) && c < 128) && c != ' ' && c != '-') return null;
            var raw = Normalize(t);
            return IsWellFormed(raw) ? raw : null;
        }
    }
}
