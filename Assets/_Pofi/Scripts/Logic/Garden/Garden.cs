using System;
using System.Collections.Generic;
using Pofi.Logic.Data;
using Pofi.Logic.Shop;

namespace Pofi.Logic.Garden
{
    public enum PlotState { Empty, NeedsWater, Growing, Ready }

    [Serializable]
    public sealed class Plot
    {
        public string SeedId;
        public long PlantedUtcTicks;
        public long WateredUtcTicks;   // büyüme sulandığı andan itibaren sayılır
        public PlotState StateAt(DateTime nowUtc, ItemDef seed)
        {
            if (string.IsNullOrEmpty(SeedId)) return PlotState.Empty;
            if (WateredUtcTicks == 0) return PlotState.NeedsWater;
            var ready = new DateTime(WateredUtcTicks, DateTimeKind.Utc).AddMinutes(seed.GrowMinutes);
            return nowUtc >= ready ? PlotState.Ready : PlotState.Growing;
        }
    }

    public enum GardenResult { Ok, Locked, NoSeed, Busy, NotReady, NothingToWater }

    /// <summary>
    /// Bahçe (FR-MINI-4): tohum ek → sula → gerçek zamanda büyür → hasat (yiyecek; coin değil).
    /// Tarla sayısı seviyeyle artar: Sv6'da 3, her iki seviyede +1, en fazla 6.
    /// </summary>
    [Serializable]
    public sealed class GardenState
    {
        public const int HarvestYield = 2;
        public List<Plot> Plots = new List<Plot>();

        public static int PlotCountFor(int level) => level < 6 ? 0 : Math.Min(6, 3 + (level - 6) / 2);

        public void EnsurePlots(int level)
        {
            while (Plots.Count < PlotCountFor(level)) Plots.Add(new Plot());
        }

        public GardenResult Plant(int index, ItemDef seed, Inventory inv)
        {
            if (index < 0 || index >= Plots.Count) return GardenResult.Locked;
            if (!string.IsNullOrEmpty(Plots[index].SeedId)) return GardenResult.Busy;
            if (seed.Category != ItemCategory.Seed || !inv.TryConsume(seed.Id)) return GardenResult.NoSeed;
            Plots[index] = new Plot { SeedId = seed.Id };
            return GardenResult.Ok;
        }

        public GardenResult Water(int index, DateTime nowUtc)
        {
            if (index < 0 || index >= Plots.Count) return GardenResult.Locked;
            var p = Plots[index];
            if (string.IsNullOrEmpty(p.SeedId) || p.WateredUtcTicks != 0) return GardenResult.NothingToWater;
            p.WateredUtcTicks = nowUtc.Ticks;
            return GardenResult.Ok;
        }

        public GardenResult Harvest(int index, DateTime nowUtc, Func<string, ItemDef> lookup, Inventory inv, out ItemDef produce)
        {
            produce = null;
            if (index < 0 || index >= Plots.Count) return GardenResult.Locked;
            var p = Plots[index];
            if (string.IsNullOrEmpty(p.SeedId)) return GardenResult.NotReady;
            var seed = lookup(p.SeedId);
            if (p.StateAt(nowUtc, seed) != PlotState.Ready) return GardenResult.NotReady;
            produce = lookup(seed.Grows);
            inv.Add(produce, HarvestYield);
            Plots[index] = new Plot();
            return GardenResult.Ok;
        }
    }
}
