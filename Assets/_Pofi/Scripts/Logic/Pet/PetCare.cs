using System;
using Pofi.Logic.Data;
using Pofi.Logic.Shop;

namespace Pofi.Logic.Pet
{
    public enum CareResult { Ok, NoItem, WrongItem, Sleeping, AlreadyFull }

    /// <summary>
    /// Bakım eylemleri (FR-PET-4): besle, yıkan, oyna, ev düzenle; gece pet uyur (FR-ISL-2).
    /// Her eylem bir göstergeyi artırır; ceza yoktur. Sonuç, tepki animasyonu/sesi seçmek için kullanılır.
    /// </summary>
    public static class PetCare
    {
        public const float FullThreshold = 95f;
        public const float PlayHappiness = 12f;
        public const float TidyHome = 10f;

        /// <summary>Gece: 21:00–07:00 (yerel saat). Pet uyurken beslenmez, oynamaz; sabah kendiliğinden uyanır.</summary>
        public static bool IsNight(DateTime local) => local.Hour >= 21 || local.Hour < 7;

        public static CareResult Feed(PetStats stats, Inventory inv, ItemDef food, DateTime local)
        {
            if (food == null || food.Category != ItemCategory.Food) return CareResult.WrongItem;
            if (IsNight(local)) return CareResult.Sleeping;
            if (stats[StatKind.Fullness] >= FullThreshold) return CareResult.AlreadyFull;
            if (!inv.TryConsume(food.Id)) return CareResult.NoItem;
            Apply(stats, food);
            return CareResult.Ok;
        }

        public static CareResult Wash(PetStats stats, Inventory inv, ItemDef soap, DateTime local)
        {
            if (soap == null || soap.Category != ItemCategory.Cleaning) return CareResult.WrongItem;
            if (IsNight(local)) return CareResult.Sleeping;
            if (!inv.TryConsume(soap.Id)) return CareResult.NoItem;
            Apply(stats, soap);
            return CareResult.Ok;
        }

        public static CareResult Play(PetStats stats, DateTime local)
        {
            if (IsNight(local)) return CareResult.Sleeping;
            stats.Add(StatKind.Happiness, PlayHappiness);
            return CareResult.Ok;
        }

        public static CareResult Tidy(PetStats stats)
        {
            stats.Add(StatKind.Home, TidyHome);
            return CareResult.Ok;
        }

        /// <summary>Eve yerleştirilen eşyanın etkisi (bir kez, ilk yerleştirmede).</summary>
        public static void ApplyPlacement(PetStats stats, ItemDef homeItem) => Apply(stats, homeItem);

        private static void Apply(PetStats stats, ItemDef item)
        {
            foreach (var kv in item.Effects)
            {
                switch (kv.Key)
                {
                    case "fullness": stats.Add(StatKind.Fullness, kv.Value); break;
                    case "cleanliness": stats.Add(StatKind.Cleanliness, kv.Value); break;
                    case "happiness": stats.Add(StatKind.Happiness, kv.Value); break;
                    case "home": stats.Add(StatKind.Home, kv.Value); break;
                }
            }
        }
    }
}
