using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.State;

namespace Pofi.Logic.Progression
{
    /// <summary>
    /// L1 seviye hediyesi (23 Ekim 2026, kullanıcı onayı: "seviye ödülü açılan yer + bir eşya; coin ya da Güneş Taşı değil").
    /// Her seviyede tek eşya; Evim'e gider. Bir seviyenin hediyesi bir kez verilir (<see cref="GameState.GiftedLevels"/>);
    /// eşya o seviyede dükkânda açılmış olsa bile hediye olarak gelir (Evim'de yerleştirilir).
    /// </summary>
    public static class LevelGifts
    {
        private static readonly Dictionary<int, string> Table = new Dictionary<int, string>
        {
            { 2, "decor_sandcastle" }, { 3, "decor_umbrella" }, { 4, "home_rug" }, { 5, "decor_palm" }, { 6, "home_lamp" },
            { 7, "home_bookshelf" }, { 8, "home_aquarium" }, { 10, "decor_sandcastle" }, { 12, "decor_lanterns" }, { 14, "decor_palm" },
        };

        /// <summary>Seviyenin hediye eşyası (yoksa null).</summary>
        public static string For(int level) => Table.TryGetValue(level, out var id) ? id : null;

        /// <summary>
        /// Atlanan seviyelerin hediyelerini envantere koyar (birden çok seviye birden atlanırsa hepsi); verilenleri döndürür.
        /// Daha önce verilmiş seviye ya da veride olmayan eşya atlanır.
        /// </summary>
        public static List<ItemDef> Claim(GameState s, GameData data, LevelUp up)
        {
            var got = new List<ItemDef>();
            if (up == null) return got;
            for (var lv = up.From + 1; lv <= up.To; lv++)
            {
                if (s.GiftedLevels.Contains(lv)) continue;
                var id = For(lv);
                s.GiftedLevels.Add(lv);
                if (id == null) continue;
                var item = data.Item(id);
                // ev ve süs eşyası sahiplikle tutulur: zaten varsa o seviyeye kadar açılmış, sahip olunmayan başka bir eşya
                if (item == null || s.Inventory.Owns(item.Id))
                    item = data.Items.Where(i => i.IsPlaceable && i.Level <= lv && !s.Inventory.Owns(i.Id) && got.All(g => g.Id != i.Id))
                        .OrderBy(i => i.Price).FirstOrDefault();
                if (item == null) continue;
                s.Inventory.Add(item);
                got.Add(item);
            }
            return got;
        }
    }
}
