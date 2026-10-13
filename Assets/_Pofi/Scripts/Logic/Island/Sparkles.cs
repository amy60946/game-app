using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;

namespace Pofi.Logic.Island
{
    public sealed class Sparkle
    {
        public int Index;
        public string EntryId;
        public float X, Z;      // haritada konum (bölgelerden uzak)
    }

    [Serializable]
    public sealed class SparkleState
    {
        public int Day;
        public List<int> Taken = new List<int>();
    }

    /// <summary>
    /// Haritada günlük "parıltılar" (FR-META-2): böcek, deniz kabuğu ve ada sakinleri keşfedilir. Günde en fazla 3;
    /// gün ve çocuk kimliğinden deterministik (yeniden açınca aynı yerde). Seviye ve gündüz/gece uygunluğu aranır.
    /// Balıklar burada çıkmaz (iskelede tutulur).
    /// </summary>
    public static class Sparkles
    {
        public const int PerDay = 3;
        public const string UnlockId = "collection_book";

        public static List<Sparkle> ForDay(int day, string childId, int level, bool night,
            IEnumerable<CollectionEntryDef> all, IReadOnlyList<RegionDef> regions)
        {
            var pool = all.Where(e => e.Category != "fish" && e.Level <= level && (e.Time == "any" || (e.Time == "night") == night))
                .OrderBy(e => e.Id, StringComparer.Ordinal).ToList();
            var list = new List<Sparkle>();
            if (pool.Count == 0) return list;
            var rng = new Random(day * 7919 + Hash(childId));
            var tries = 0;
            while (list.Count < PerDay && tries++ < 200)
            {
                var x = (float)(rng.NextDouble() * 8.0 - 4.0);
                var z = (float)(rng.NextDouble() * 5.6 - 1.8);
                if (regions.Any(r => Dist(r.X, r.Z, x, z) < 1.0f) || list.Any(s => Dist(s.X, s.Z, x, z) < 1.0f)) continue;
                if ((x * x) / 20f + ((z - 1f) * (z - 1f)) / 13f > 1f) continue;   // ada içinde kal
                list.Add(new Sparkle { Index = list.Count, EntryId = pool[rng.Next(pool.Count)].Id, X = x, Z = z });
            }
            return list;
        }

        /// <summary>Bugün alınmamış parıltılar.</summary>
        public static List<Sparkle> Open(SparkleState st, int day, List<Sparkle> all)
        {
            if (st.Day != day) { st.Day = day; st.Taken.Clear(); }
            return all.Where(s => !st.Taken.Contains(s.Index)).ToList();
        }

        public static void Take(SparkleState st, int day, Sparkle s)
        {
            if (st.Day != day) { st.Day = day; st.Taken.Clear(); }
            if (!st.Taken.Contains(s.Index)) st.Taken.Add(s.Index);
        }

        private static float Dist(float ax, float az, float bx, float bz) => (float)Math.Sqrt((ax - bx) * (ax - bx) + (az - bz) * (az - bz));

        private static int Hash(string s)
        {
            unchecked
            {
                var h = 17;
                foreach (var ch in s ?? "") h = h * 31 + ch;
                return h & 0x7FFFFFFF;
            }
        }
    }
}
