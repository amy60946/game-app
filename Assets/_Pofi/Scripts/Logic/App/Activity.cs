using System;
using System.Collections.Generic;
using Pofi.Logic.Data;
using Pofi.Logic.Meta;
using Pofi.Logic.Progression;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    public sealed class ActivityResult
    {
        public List<BadgeDef> NewBadges = new List<BadgeDef>();
        public List<DailyQuestDef> QuestsDone = new List<DailyQuestDef>();
        public int BadgeXp, QuestXp;
    }

    /// <summary>
    /// Oyuncu eylemlerinin tek kaydı (besle, ceviz yakala, oyun oyna…): sayaç + rozet + günlük görev (FR-META-2/3).
    /// XP'yi burada vermez; çağıran <see cref="Progress.Grant"/> ile verir (rozet: Achievement, görev: DailyQuest kaynağı).
    /// </summary>
    public static class Activity
    {
        public static ActivityResult Record(GameState s, GameData data, LevelTable levels, string counter, int n, DateTime local)
        {
            var level = levels.LevelFor(s.Xp.TotalXp);
            if (n > 0) s.Counters.Add(counter, n, local);
            s.Counters.SetMax("level", level);
            s.Counters.SetMax("best_streak", s.Streak.Count);
            EnsureQuests(s, data, levels, local);

            var r = new ActivityResult();
            r.NewBadges.AddRange(Badges.Evaluate(data.Badges, s.Counters, s.Badges));
            foreach (var b in r.NewBadges) r.BadgeXp += b.Xp;
            r.QuestsDone.AddRange(DailyQuests.Claim(s.DailyQuests, data, s.Counters));
            foreach (var q in r.QuestsDone) r.QuestXp += q.Xp;
            return r;
        }

        public static void EnsureQuests(GameState s, GameData data, LevelTable levels, DateTime local)
        {
            var level = levels.LevelFor(s.Xp.TotalXp);
            DailyQuests.EnsureForToday(s.DailyQuests, data, id => string.IsNullOrEmpty(id) || levels.IsUnlocked(id, level), s.ChildId ?? "", local);
        }
    }
}
