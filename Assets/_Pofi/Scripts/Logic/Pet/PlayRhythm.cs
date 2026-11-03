using System;

namespace Pofi.Logic.Pet
{
    /// <summary>
    /// Okti ile oyun ritmi (K2 B, kullanıcı 3 Kasım 2026; benchmark Pokémon-Amie/Refresh, Nintendogs: okşama her yerde, aynı pet
    /// tekrar tekrar oynandıkça getiri azalır). Top oyunu (adada Okti menüsündeki "Oyna", evde kalp) bitince sayılır:
    /// iki sayılan oyun arası en az <see cref="GapSeconds"/> sn (arka arkaya basmak "3 kez oyna"yı bitirmez), mutluluk getirisi
    /// 12 → 8 → 5 (10 dk oynanmazsa yeniden 12). Okşama (parmak Okti'nin üstünde 1 sn gezinir) küçük mutluluk verir, en sık 6 sn'de bir.
    /// Ceza, sayaç, "yoruldu" uyarısı yok; durum yalnız oturumda tutulur (kayda girmez).
    /// </summary>
    public sealed class PlayRhythm
    {
        public const double GapSeconds = 20, ResetSeconds = 600, PetGapSeconds = 6;
        public const float PetHappiness = 3f;
        public static readonly float[] Gains = { 12f, 8f, 5f };

        private DateTime? _last, _lastPet;
        private int _streak;

        /// <summary>Yeni bir top oyunu sayılabilir mi?</summary>
        public bool Ready(DateTime utc) => _last == null || (utc - _last.Value).TotalSeconds >= GapSeconds;

        /// <summary>Sıradaki oyuna kalan saniye (hazırsa 0).</summary>
        public int SecondsLeft(DateTime utc) =>
            _last == null ? 0 : Math.Max(0, (int)Math.Ceiling(GapSeconds - (utc - _last.Value).TotalSeconds));

        /// <summary>Sıradaki oyunun mutluluk getirisi (oynamadan bakmak için).</summary>
        public float NextGain(DateTime utc) => Gains[Math.Min(StreakAt(utc), Gains.Length - 1)];

        /// <summary>Oyun bitti: getiriyi döner ve ritmi ilerletir. Hazır değilse 0 (sayılmaz).</summary>
        public float Take(DateTime utc)
        {
            if (!Ready(utc)) return 0f;
            var streak = StreakAt(utc);
            _streak = streak + 1;
            _last = utc;
            return Gains[Math.Min(streak, Gains.Length - 1)];
        }

        /// <summary>Okşama: getirisi (sık okşamada 0; kalpler ve ses yine çıkar).</summary>
        public float Pet(DateTime utc)
        {
            if (_lastPet != null && (utc - _lastPet.Value).TotalSeconds < PetGapSeconds) return 0f;
            _lastPet = utc;
            return PetHappiness;
        }

        private int StreakAt(DateTime utc) => _last == null || (utc - _last.Value).TotalSeconds >= ResetSeconds ? 0 : _streak;
    }
}
