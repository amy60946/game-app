using System;

namespace Pofi.Logic.Profile
{
    /// <summary>
    /// Yaş grubu (22 Ekim 2026, XP takibi S1: K 5 ve altı / A 6–8 / B 9–12 / C 13 ve üstü; sözleşme: ortak/sozlesme/durumlar.md §4):
    /// ebeveyn seçer ya da doğum gününden önerilir, giriş yanıtında gelir. Yalnız zorluk/arayüz/seviye hızı ayarıdır; raporlar gerçek yaşı kullanır.
    /// K sona eklendi (kayıtlardaki sayısal değerler değişmesin).
    /// </summary>
    public enum AgeBand { A, B, C, K }

    public static class AgeBands
    {
        /// <summary>En küçük iki grup (K, A): oyunlar ve kapılar A ayarlarını kullanır.</summary>
        public static bool Young(this AgeBand b) => b == AgeBand.A || b == AgeBand.K;
    }

    /// <summary>
    /// Yaş bandına göre arayüz ve oyun ayarları (FR-VOICE-2, FR-ECO-4, tema). Değerler veri dosyasıyla
    /// (ve uzaktan yapılandırmayla) ezilebilir; buradakiler güvenli varsayılanlardır.
    /// </summary>
    public sealed class AgeBandProfile
    {
        public AgeBand Band { get; }
        public string Theme { get; }               // "rounded_icons" | "balanced" | "compact"
        public bool VoiceAlwaysOn { get; }          // A: her metin sesli, kapatılamaz
        public bool VoiceDefaultOn { get; }
        public bool SubtitlesDefaultOn { get; }
        public float MiniGameDifficulty { get; }    // 0..1
        public int DailyXpCap { get; }
        public float ButtonScale { get; }

        private AgeBandProfile(AgeBand band, string theme, bool voiceAlways, bool voiceDefault, bool subs,
            float difficulty, int xpCap, float buttonScale)
        {
            Band = band; Theme = theme; VoiceAlwaysOn = voiceAlways; VoiceDefaultOn = voiceDefault;
            SubtitlesDefaultOn = subs; MiniGameDifficulty = difficulty; DailyXpCap = xpCap; ButtonScale = buttonScale;
        }

        public static AgeBandProfile For(AgeBand band)
        {
            switch (band)
            {
                case AgeBand.K: return new AgeBandProfile(band, "rounded_icons", true, true, true, 0.2f, 200, 1.3f);
                case AgeBand.A: return new AgeBandProfile(band, "rounded_icons", true, true, true, 0.3f, 250, 1.25f);
                case AgeBand.B: return new AgeBandProfile(band, "balanced", false, true, true, 0.6f, 300, 1.0f);
                case AgeBand.C: return new AgeBandProfile(band, "compact", false, false, true, 0.85f, 350, 0.9f);
                default: throw new ArgumentOutOfRangeException(nameof(band));
            }
        }

        /// <summary>Sunucudan gelen "K"/"A"/"B"/"C" metnini çözer; bilinmeyen değerde en güvenli bant (A).</summary>
        public static AgeBand Parse(string value)
        {
            switch ((value ?? "").Trim().ToUpperInvariant())
            {
                case "B": return AgeBand.B;
                case "C": return AgeBand.C;
                case "K": return AgeBand.K;
                default: return AgeBand.A;
            }
        }
    }
}
