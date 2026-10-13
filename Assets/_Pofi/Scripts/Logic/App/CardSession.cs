using Pofi.Logic.Cards;
using Pofi.Logic.Profile;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Masa oyunu oturumu (M8, FR-CARD-2/3): bot zorluğu yaş bandından başlar ve oyun başına uyarlanıp kayıtta saklanır.
    /// Oyun kimlikleri levels.json açılış kimlikleriyle aynı: card_color_match, card_domino, card_tower.
    /// </summary>
    public static class CardSession
    {
        public static readonly string[] Games = { "card_color_match", "card_domino", "card_tower" };

        public static DifficultyAdapter Difficulty(GameState s, string gameId, AgeBand band)
        {
            if (!s.CardDifficulty.TryGetValue(gameId, out var d) || d == null)
            {
                d = new DifficultyAdapter(AgeBandProfile.For(band).MiniGameDifficulty);
                s.CardDifficulty[gameId] = d;
            }
            return d;
        }

        /// <summary>Oyun sonu: zorluğu uyarlar, verilecek XP'yi döndürür (kazanınca tam, kaybedince cesaret ödülü).</summary>
        public static int Finish(GameState s, string gameId, AgeBand band, bool childWon)
        {
            var d = Difficulty(s, gameId, band);
            var xp = CardRewards.Xp(childWon, d.Level);
            d.Record(childWon);
            return xp;
        }
    }
}
