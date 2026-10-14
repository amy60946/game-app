using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Fishing
{
    public enum CatchResult { TooEarly, Caught, TooLate }

    /// <summary>
    /// Balık tutma (FR-MINI-5): olta atılır, rastgele bir anda balık vurur; çocuk "çek" zamanlamasını tutturursa yakalar.
    /// Pencere yaş bandına göre geniştir (A en cömert). Tür; seviye, gündüz/gece ve nadirliğe göre seçilir.
    /// </summary>
    public sealed class FishingRound
    {
        public int BiteAtMs { get; }
        public int WindowMs { get; }
        public CollectionEntryDef Fish { get; }

        public FishingRound(Random rng, AgeBand band, int level, bool? night, IEnumerable<CollectionEntryDef> collection)
        {
            BiteAtMs = 1500 + rng.Next(3500);
            WindowMs = band == AgeBand.A ? 1400 : band == AgeBand.B ? 1000 : 700;
            Fish = Pick(rng, level, night, collection);
        }

        public CatchResult Resolve(int tapAtMs)
        {
            if (tapAtMs < BiteAtMs) return CatchResult.TooEarly;
            return tapAtMs <= BiteAtMs + WindowMs ? CatchResult.Caught : CatchResult.TooLate;
        }

        public static CollectionEntryDef Pick(Random rng, int level, bool? night, IEnumerable<CollectionEntryDef> collection)
        {
            var pool = collection.Where(e => e.Category == "fish" && e.Level <= level &&
                                             (night == null || e.Time == "any" || (e.Time == "night") == night)).ToList();
            if (pool.Count == 0) return null;
            // Nadirlik ağırlığı: yaygın 6, orta 3, nadir 1
            var weights = pool.Select(e => e.Rarity == 1 ? 6 : e.Rarity == 2 ? 3 : 1).ToList();
            var roll = rng.Next(weights.Sum());
            for (var i = 0; i < pool.Count; i++) { roll -= weights[i]; if (roll < 0) return pool[i]; }
            return pool[pool.Count - 1];
        }

        public static int Xp(CollectionEntryDef fish, bool isNew) => 5 * fish.Rarity + (isNew ? 10 : 0);
    }
}
