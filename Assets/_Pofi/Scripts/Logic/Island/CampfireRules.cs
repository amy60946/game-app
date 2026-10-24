using System;

namespace Pofi.Logic.Island
{
    /// <summary>Kamp ateşinin kayıttaki durumu.</summary>
    [Serializable]
    public sealed class CampfireState
    {
        public int Day;            // bugünkü harlamaların günü (XpSystem.DayNumber)
        public int Today;          // bugün kaç kez harlandı
        public int Total;
        public long LastUtcTicks;  // en son harlama (alev boyu buna göre söner)
    }

    /// <summary>
    /// Kamp ateşini harla (kullanıcı GB18, 24 Ekim 2026: "odun toplama işini kamp ateşini harlamak için de kullanabiliriz,
    /// yeni bir XP kazanma seçeneği"): 2 odun ateşe atılır → XP. Günde en çok 3 kez (oyun içi XP, coin değil). Alev bir süre
    /// büyük yanar, saatler içinde yavaşça söner; sönükken ateş yine yanar (ada hiç karanlıkta kalmaz).
    /// </summary>
    public static class CampfireRules
    {
        public const int WoodPerStoke = 2, Xp = 8, MaxPerDay = 3;
        public static readonly TimeSpan GlowTime = TimeSpan.FromHours(3);

        public static int TodayCount(CampfireState s, int day) => s == null || s.Day != day ? 0 : s.Today;

        public enum Check { Ok, NeedWood, DoneToday }

        public static Check CanStoke(CampfireState s, GatherState g, int day)
        {
            if (TodayCount(s, day) >= MaxPerDay) return Check.DoneToday;
            return Gathering.Count(g, Gathering.Wood) >= WoodPerStoke ? Check.Ok : Check.NeedWood;
        }

        /// <summary>Harla: odun düşer, sayaç artar. Olmazsa false.</summary>
        public static bool Stoke(CampfireState s, GatherState g, int day, DateTime nowUtc)
        {
            if (CanStoke(s, g, day) != Check.Ok) return false;
            g.Materials[Gathering.Wood] = Gathering.Count(g, Gathering.Wood) - WoodPerStoke;
            if (s.Day != day) { s.Day = day; s.Today = 0; }
            s.Today++; s.Total++;
            s.LastUtcTicks = nowUtc.Ticks;
            return true;
        }

        /// <summary>Alevin harlama coşkusu 0..1 (harlandıktan sonra <see cref="GlowTime"/> içinde söner).</summary>
        public static float Heat(CampfireState s, DateTime nowUtc)
        {
            if (s == null || s.LastUtcTicks <= 0) return 0f;
            var age = (nowUtc.Ticks - s.LastUtcTicks) / (double)GlowTime.Ticks;
            return age >= 1 || age < 0 ? 0f : (float)(1 - age);
        }
    }
}
