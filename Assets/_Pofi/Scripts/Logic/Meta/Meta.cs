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
        public bool ChestOpened;   // günün 3 görevi bitince açılan günlük sandık (S2) bugün açıldı mı
    }

    /// <summary>Günlük sandıktan çıkan tek ödül (S2; coin değil — coin yalnız gerçek görevden).</summary>
    public sealed class ChestPrize
    {
        public const string Food = "food", Seed = "seed", Surprise = "surprise";
        public string Kind;
        public string ItemId;
        public int Quantity;
    }

    /// <summary>
    /// Günlük sandık (S2, kullanıcı onayı 22 Ekim 2026): günün bütün oyun içi görevleri bitince bir kez açılır, içinden tek ödül çıkar.
    /// Şans oranları sabit ve sandıkta görünür (kumar algısı olmasın): yiyecek %60 (2 adet), tohum %25 (2 adet), sürpriz eşya %15
    /// (henüz sahip olunmayan, seviyesi açık, coin'li bir aksesuar/süs; yoksa yiyecek). Para yok, coin yok.
    /// Sonuç gün + çocuktan belirlenir (yeniden açınca değişmez).
    /// </summary>
    public static class DailyChest
    {
        public static readonly (string Kind, int Percent)[] Odds = { (ChestPrize.Food, 60), (ChestPrize.Seed, 25), (ChestPrize.Surprise, 15) };

        public static bool Ready(DailyQuestState st) => st.Ids.Count > 0 && !st.ChestOpened && st.Ids.All(st.Claimed.Contains);

        public static ChestPrize Roll(DailyQuestState st, GameData data, Shop.Inventory inv, int level, string childId)
        {
            var rng = new Random(st.Day * 17 + 5 + DailyQuests.StableHash(childId));
            var roll = rng.Next(100);
            var kind = roll < Odds[0].Percent ? ChestPrize.Food : roll < Odds[0].Percent + Odds[1].Percent ? ChestPrize.Seed : ChestPrize.Surprise;
            List<ItemDef> Pick(Func<ItemDef, bool> f) => data.Items.Where(i => f(i) && i.Level <= level).OrderBy(i => i.Id, StringComparer.Ordinal).ToList();
            if (kind == ChestPrize.Surprise)
            {
                var pool = Pick(i => (i.Category == ItemCategory.Accessory || i.Category == ItemCategory.Decor) && !i.Premium && i.Price > 0 && !inv.Owns(i.Id));
                if (pool.Count > 0) return new ChestPrize { Kind = kind, ItemId = pool[rng.Next(pool.Count)].Id, Quantity = 1 };
                kind = ChestPrize.Food;
            }
            var list = Pick(i => i.Category == (kind == ChestPrize.Seed ? ItemCategory.Seed : ItemCategory.Food));
            if (list.Count == 0) list = Pick(i => i.Category == ItemCategory.Food);
            if (list.Count == 0) return null;
            return new ChestPrize { Kind = kind, ItemId = list[rng.Next(list.Count)].Id, Quantity = 2 };
        }

        /// <summary>Sandığı açar: ödülü envantere ekler, bugün için kapatır. Hazır değilse null.</summary>
        public static ChestPrize Open(DailyQuestState st, GameData data, Shop.Inventory inv, int level, string childId)
        {
            if (!Ready(st)) return null;
            var p = Roll(st, data, inv, level, childId);
            st.ChestOpened = true;
            var item = p != null ? data.Item(p.ItemId) : null;
            if (item != null) inv.Add(item, p.Quantity);
            return p;
        }
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
            st.ChestOpened = false;
            st.Ids = pool.OrderBy(_ => rng.Next()).Take(data.DailyQuestsPerDay).Select(q => q.Id).ToList();
        }

        public static int Progress(DailyQuestDef q, Counters c) => Math.Min(q.Target, c.TodayCount(q.Counter));

        /// <summary>Görev başına seviye payı (S2): 3 görevin toplamı o seviyenin gereken XP'sinin ~%12'si.</summary>
        public const double ShareOfLevel = 0.04;

        /// <summary>
        /// Görevin bugünkü XP'si (S2, 22 Ekim 2026): sabit sayı üst seviyede önemini yitiriyordu (Sv14'te seviyenin %1'i).
        /// O seviyenin gereken XP'sinin %4'ü, görevin göreli ağırlığıyla (ortalama 15 = 1); hiçbir zaman verideki sayının altına inmez.
        /// </summary>
        public static int XpFor(DailyQuestDef q, int levelNeed) =>
            Math.Max(q.Xp, (int)Math.Round(levelNeed * ShareOfLevel * q.Xp / 15.0));

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

        internal static int StableHash(string s)
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
