using System;
using Pofi.Logic.Data;
using Pofi.Logic.Progression;
using Pofi.Logic.Shop;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Önizleme test erişimi (kullanıcı isteği, 14 Ekim 2026): XP biriktirmeden tüm fonksiyonları denemek için en üst seviye,
    /// tüm eşyalar ve bol coin. Yalnızca sahte arka uçla (önizleme) gösterilir; gerçek çocuk hesabında yoktur.
    /// </summary>
    public static class TestAccess
    {
        public const int Coins = 5000, Consumables = 20, SunStones = 30;

        /// <summary>En üst seviyeye ulaşmak için gereken XP (zaten oradaysa 0).</summary>
        public static int XpToMax(LevelTable levels, int totalXp) => Math.Max(0, levels.TotalXpFor(levels.MaxLevel) - totalXp);

        /// <summary>Her eşyadan verir: tüketilenlerden <see cref="Consumables"/> adet, diğerlerinden bir tane. Eklenen çeşit sayısı.</summary>
        public static int GiveAllItems(GameData data, Inventory inv)
        {
            var n = 0;
            foreach (var item in data.Items)
            {
                if (item.IsConsumable) { if (inv.CountOf(item.Id) < Consumables) { inv.Add(item, Consumables - inv.CountOf(item.Id)); n++; } }
                else if (!inv.Owns(item.Id)) { inv.Add(item); n++; }
            }
            return n;
        }
    }
}
