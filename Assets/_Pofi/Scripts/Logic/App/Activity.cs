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
        public List<int> QuestXpEach = new List<int>();   // QuestsDone ile aynı sırada, seviyeye oranlı XP
        public bool ChestReady;   // bu eylemle günün son görevi bitti: günlük sandık açılabilir (S2)
    }

    /// <summary>
    /// Oyuncu eylemlerinin tek kaydı (besle, ceviz yakala, oyun oyna…): sayaç + rozet + günlük görev (FR-META-2/3).
    /// XP'yi burada vermez; çağıran <see cref="Progress.Grant"/> ile verir (rozet: Achievement, görev: DailyQuest kaynağı).
    /// </summary>
    public static class Activity
    {
        public static ActivityResult Record(GameState s, GameData data, LevelTable levels, string counter, int n, DateTime local)
        {
            var level = levels.Level(s.Xp);
            if (n > 0) s.Counters.Add(counter, n, local);
            s.Counters.SetMax("level", level);
            s.Counters.SetMax("best_streak", s.Streak.Count);
            EnsureQuests(s, data, levels, local);

            var r = new ActivityResult();
            r.NewBadges.AddRange(Badges.Evaluate(data.Badges, s.Counters, s.Badges));
            foreach (var b in r.NewBadges) r.BadgeXp += b.Xp;
            r.QuestsDone.AddRange(DailyQuests.Claim(s.DailyQuests, data, s.Counters));
            var need = levels.TotalXpFor(level + 1) - levels.TotalXpFor(level);
            foreach (var q in r.QuestsDone) { var x = DailyQuests.XpFor(q, need); r.QuestXpEach.Add(x); r.QuestXp += x; }
            r.ChestReady = r.QuestsDone.Count > 0 && DailyChest.Ready(s.DailyQuests);
            return r;
        }

        /// <summary>Bu seviyede görevin vereceği XP (panel gösterimi için; S2).</summary>
        public static int QuestXp(GameState s, LevelTable levels, DailyQuestDef q)
        {
            var level = levels.Level(s.Xp);
            return DailyQuests.XpFor(q, levels.TotalXpFor(level + 1) - levels.TotalXpFor(level));
        }

        public static void EnsureQuests(GameState s, GameData data, LevelTable levels, DateTime local)
        {
            var level = levels.Level(s.Xp);
            DailyQuests.EnsureForToday(s.DailyQuests, data, id => string.IsNullOrEmpty(id) || data.SunBook.IsOpen(id, level, levels, s.SunStones), s.ChildId ?? "", local);
        }
    }
}
