using System;
using System.Collections.Generic;

namespace Pofi.Logic.Island
{
    [Serializable]
    public sealed class EventState
    {
        public int FestivalDay = -1;         // son festival ödülünün günü
        public bool FinalCelebrated;         // fener (Sv15) final kutlaması yapıldı mı
    }

    /// <summary>
    /// Festival (Sv12): her gün fenerleri yakınca bir kez ödül (XP). Fener (Sv15): ada finali — bir kez kutlanır.
    /// </summary>
    public static class IslandEvents
    {
        public const int FestivalLanterns = 6;
        public const int FestivalXp = 25;
        public const int FinalXp = 100;

        public static bool CanClaimFestival(EventState s, int day) => s.FestivalDay != day;

        public static bool ClaimFestival(EventState s, int day)
        {
            if (!CanClaimFestival(s, day)) return false;
            s.FestivalDay = day;
            return true;
        }

        public static bool ClaimFinal(EventState s)
        {
            if (s.FinalCelebrated) return false;
            s.FinalCelebrated = true;
            return true;
        }
    }
}
