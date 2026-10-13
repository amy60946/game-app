using System;
using Pofi.Logic.Economy;
using Pofi.Logic.Profile;
using Pofi.Logic.Progression;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    public sealed class XpResult
    {
        public XpGrant Grant;
        public LevelUp LevelUp;     // null: seviye atlanmadı
    }

    /// <summary>
    /// Tüm XP kazançlarının tek kapısı: günlük sınır yaş bandından (FR-ECO-4), seviye atlama ve açılışlar (FR-PROG-1..3).
    /// Seviye kutlaması gösterilince açılışlar <see cref="GameState.SeenUnlocks"/>'a yazılır.
    /// </summary>
    public static class Progress
    {
        public static XpResult Grant(GameState s, LevelTable levels, AgeBand band, int amount, XpSource source, DateTime local)
        {
            var before = s.Xp.TotalXp;
            var g = s.Xp.Add(amount, source, local, AgeBandProfile.For(band).DailyXpCap);
            return new XpResult { Grant = g, LevelUp = levels.Check(before, s.Xp.TotalXp) };
        }

        public static void MarkCelebrated(GameState s, LevelUp up)
        {
            if (up == null) return;
            foreach (var id in up.Unlocked) s.SeenUnlocks.Add(id);
        }
    }
}
