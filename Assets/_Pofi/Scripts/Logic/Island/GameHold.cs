using System.Collections.Generic;

namespace Pofi.Logic.Island
{
    /// <summary>
    /// Beklemedeki oyunlar (kullanıcı, 24 Ekim 2026: "mini oyunlarda hindistan cevizi toplamayı tutalım, diğerleri şimdilik
    /// beklemede kalsın"). Bekleyen oyunun yeri adada durur ama açılmaz ("Yakında"), "sıradaki yer" şeridinde, rehberde ve
    /// günlük görevlerde çıkmaz. Bir oyunu yeniden açmak için adını <see cref="ActiveMiniGames"/>'e eklemek yeter.
    /// </summary>
    public static class GameHold
    {
        /// <summary>Açık mini oyunlar: Ceviz Yakala + Oyun Kulübesi'nde Gezegen Koşusu (25 Ekim 2026, kart oyunlarının yerine).</summary>
        public static readonly HashSet<string> ActiveMiniGames = new HashSet<string> { "coconut", "runner" };
        /// <summary>Masa/kart oyunları (Oyun Kulübesi) da beklemede.</summary>
        public static bool CardsOnHold = true;

        public static bool MiniGameOnHold(string id) => !string.IsNullOrEmpty(id) && !ActiveMiniGames.Contains(id);

        public static bool RegionOnHold(RegionDef r)
        {
            if (r == null) return false;
            var kind = IslandMap.KindOf(r.Target, out var arg);
            return kind == RegionTargetKind.MiniGame ? MiniGameOnHold(arg) : kind == RegionTargetKind.Cards && CardsOnHold;
        }

        /// <summary>Özellik anahtarı (levels.json / daily_quests.json "unlock": minigame_swim, card_color_match …) beklemede mi?</summary>
        public static bool FeatureOnHold(string feature)
        {
            if (string.IsNullOrEmpty(feature)) return false;
            if (feature.StartsWith("minigame_")) return MiniGameOnHold(feature.Substring("minigame_".Length));
            return CardsOnHold && feature.StartsWith("card_");
        }

        /// <summary>Seviye kutlamasında beklemedeki oyunlar ve yerleri "açıldı" diye listelenmez.</summary>
        public static void FilterLevelUp(Progression.LevelUp up, IslandMap map)
        {
            if (up == null) return;
            up.Unlocked.RemoveAll(id => FeatureOnHold(id) || (map != null && RegionOnHold(map.Find(id))));
        }
    }
}
