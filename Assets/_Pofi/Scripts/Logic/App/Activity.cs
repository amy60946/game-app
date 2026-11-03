using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.Meta;
using Pofi.Logic.Progression;
using Pofi.Logic.State;
using Pofi.Logic.Island;

namespace Pofi.Logic.App
{
    public sealed class ActivityResult
    {
        public List<BadgeDef> NewBadges = new List<BadgeDef>();
        public List<DailyQuestDef> QuestsDone = new List<DailyQuestDef>();
        /// <summary>Bu eylemle biten (ödülü "Al"ı bekleyen) görevler (K1 A).</summary>
        public List<DailyQuestDef> QuestsReady = new List<DailyQuestDef>();
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
            s.Counters.Roll(local);
            EnsureQuests(s, data, levels, local);
            var before = DailyQuests.Ready(s.DailyQuests, data, s.Counters).Select(q => q.Id).ToList();
            if (n > 0) s.Counters.Add(counter, n, local);
            s.Counters.SetMax("level", level);
            s.Counters.SetMax("best_streak", s.Streak.Count);
            EnsureQuests(s, data, levels, local);

            var r = new ActivityResult();
            r.NewBadges.AddRange(Badges.Evaluate(data.Badges, s.Counters, s.Badges));
            foreach (var b in r.NewBadges) r.BadgeXp += b.Xp;
            // K1 A: biten görev ödülünü kendiliğinden vermez; çocuk Görevler penceresinde "Al"a dokunur (ClaimQuest)
            r.QuestsReady.AddRange(DailyQuests.Ready(s.DailyQuests, data, s.Counters).Where(q => !before.Contains(q.Id)));
            return r;
        }

        /// <summary>
        /// Görev ödülünü al (K1 A): hazır görev alındı olarak işaretlenir, XP'si döner (çağıran verir); günün son görevi alındıysa
        /// günlük sandık hazır. Hazır değilse boş sonuç.
        /// </summary>
        public static ActivityResult ClaimQuest(GameState s, GameData data, LevelTable levels, string questId)
        {
            var r = new ActivityResult();
            var q = DailyQuests.ClaimOne(s.DailyQuests, data, s.Counters, questId);
            if (q == null) return r;
            var level = levels.Level(s.Xp);
            var x = DailyQuests.XpFor(q, levels.TotalXpFor(level + 1) - levels.TotalXpFor(level));
            r.QuestsDone.Add(q); r.QuestXpEach.Add(x); r.QuestXp = x;
            r.ChestReady = DailyChest.Ready(s.DailyQuests);
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
            DailyQuests.EnsureForToday(s.DailyQuests, data, id => string.IsNullOrEmpty(id) || (!GameHold.FeatureOnHold(id) && data.SunBook.IsOpen(id, level, levels, s.SunStones)), s.ChildId ?? "", local);
        }
    }
}
