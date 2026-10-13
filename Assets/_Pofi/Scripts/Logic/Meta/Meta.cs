using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;

namespace Pofi.Logic.Meta
{
    /// <summary>
    /// Oyun sayaçları (beslendi, balık tutuldu …). Rozetler ve günlük görevler bunları izler; sistemler yalnızca sayaç artırır.
    /// </summary>
    [Serializable]
    public sealed class Counters
    {
        public Dictionary<string, int> Totals = new Dictionary<string, int>();
        public Dictionary<string, int> Today = new Dictionary<string, int>();
        public int Day;

        public int Total(string key) => Totals.TryGetValue(key, out var v) ? v : 0;
        public int TodayCount(string key) => Today.TryGetValue(key, out var v) ? v : 0;

        public void Add(string key, int n, DateTime local)
        {
            Roll(local);
            Totals[key] = Total(key) + n;
            Today[key] = TodayCount(key) + n;
        }

        /// <summary>"En iyi seri", "seviye", "balık türü sayısı" gibi maksimum değerler.</summary>
        public void SetMax(string key, int value)
        {
            if (value > Total(key)) Totals[key] = value;
        }

        public void Roll(DateTime local)
        {
            var d = Economy.XpSystem.DayNumber(local);
            if (d != Day) { Day = d; Today.Clear(); }
        }
    }

    public static class Badges
    {
        /// <summary>Yeni kazanılan rozetler (owned kümesine eklenir).</summary>
        public static List<BadgeDef> Evaluate(IEnumerable<BadgeDef> defs, Counters c, ISet<string> owned)
        {
            var earned = new List<BadgeDef>();
            foreach (var b in defs)
            {
                if (owned.Contains(b.Id) || c.Total(b.Counter) < b.Target) continue;
                owned.Add(b.Id);
                earned.Add(b);
            }
            return earned;
        }
    }

    [Serializable]
    public sealed class DailyQuestState
    {
        public int Day;
        public List<string> Ids = new List<string>();
        public List<string> Claimed = new List<string>();
    }

    /// <summary>
    /// Günlük 3 görev (FR-META-3). Gün ve çocuk kimliğinden deterministik seçilir (yeniden açınca değişmez),
    /// yalnızca açılmış içerikten seçilir. İlerleme o günün sayaçlarıyla ölçülür.
    /// </summary>
    public static class DailyQuests
    {
        public static void EnsureForToday(DailyQuestState st, GameData data, Func<string, bool> isUnlocked, string childId, DateTime local)
        {
            var day = Economy.XpSystem.DayNumber(local);
            if (st.Day == day && st.Ids.Count > 0) return;
            var pool = data.DailyQuests.Where(q => isUnlocked(q.Unlock)).OrderBy(q => q.Id, StringComparer.Ordinal).ToList();
            var rng = new Random(day * 31 + StableHash(childId));
            st.Day = day;
            st.Claimed.Clear();
            st.Ids = pool.OrderBy(_ => rng.Next()).Take(data.DailyQuestsPerDay).Select(q => q.Id).ToList();
        }

        public static int Progress(DailyQuestDef q, Counters c) => Math.Min(q.Target, c.TodayCount(q.Counter));

        /// <summary>Tamamlanmış ve henüz alınmamış görevlerin XP'si (alındı olarak işaretlenir).</summary>
        public static List<DailyQuestDef> Claim(DailyQuestState st, GameData data, Counters c)
        {
            var done = new List<DailyQuestDef>();
            foreach (var id in st.Ids)
            {
                var q = data.DailyQuests.First(x => x.Id == id);
                if (st.Claimed.Contains(id) || Progress(q, c) < q.Target) continue;
                st.Claimed.Add(id);
                done.Add(q);
            }
            return done;
        }

        private static int StableHash(string s)
        {
            unchecked
            {
                var h = 23;
                foreach (var ch in s ?? "") h = h * 31 + ch;
                return h & 0x7FFFFFFF;
            }
        }
    }

    public static class CollectionBook
    {
        /// <summary>Keşif: yeni ise true (defter "Yeni!" gösterir) ve tür sayaçları güncellenir.</summary>
        public static bool Discover(ISet<string> owned, CollectionEntryDef e, Counters c)
        {
            if (!owned.Add(e.Id)) return false;
            c.SetMax(e.Category + "_species", c.Total(e.Category + "_species") + 1);
            return true;
        }

        public static (int found, int total) Completion(IEnumerable<CollectionEntryDef> all, ISet<string> owned, string category)
        {
            var list = all.Where(e => e.Category == category).ToList();
            return (list.Count(e => owned.Contains(e.Id)), list.Count);
        }
    }
}
