using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Island;

namespace Pofi.Logic.Meta
{
    /// <summary>
    /// Günlük oyun görevinin "Git"i (GB20-5, kullanıcı 2 Kasım 2026: "oyun görevlerini yönlendirmeyle tamamlat"; benchmark:
    /// Hello Kitty Island Adventure "Show Guide" ışığı, Pokémon GO araştırma kartı): görev penceresinde satıra dokununca pencere
    /// kapanır, çocuk görevin yapıldığı yere yönlendirilir. Bakım görevleri Okti'nin kendisinde (el Okti'yi ve eşyayı gösterir),
    /// diğerleri bir bölgede (yerde oklar + Mavi önden uçar).
    /// </summary>
    public static class QuestGo
    {
        public enum Kind { None, Pet, Region }

        /// <summary>Sayaç → nereye: Pet ("food" / "soap") ya da Region (bölge kimliği). Bölge haritada yoksa None.</summary>
        public static (Kind Kind, string Arg) For(string counter, IEnumerable<RegionDef> regions)
        {
            switch (counter)
            {
                case "pet_fed": return (Kind.Pet, "food");
                case "pet_washed": return (Kind.Pet, "soap");
            }
            var list = regions as IList<RegionDef> ?? regions.ToList();
            string id = counter switch
            {
                "pet_played" => "region_home",
                "home_tidied" => "region_home",
                "harvests" => "region_garden",
                "plants_watered" => "region_garden",
                _ => null,
            };
            if (id == null)
            {
                var target = counter switch
                {
                    "coconuts_caught" => "minigame:coconut",
                    "runner_finished" => "minigame:runner",
                    "swim_runs" => "minigame:swim",
                    "fish_caught" => "minigame:fishing",
                    "pets_helped" => "minigame:help_pet",
                    "card_games_played" => "cards",
                    _ => null,
                };
                id = target == null ? null : list.FirstOrDefault(r => r.Target == target)?.Id;
            }
            return id != null && list.Any(r => r.Id == id) ? (Kind.Region, id) : (Kind.None, null);
        }
    }
}
