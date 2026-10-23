using System;

namespace Pofi.Logic.Economy
{
    public enum XpSource { MiniGame, CardGame, Fishing, Garden, DailyQuest, TaskStreak, Achievement, RealTask }

    public struct XpGrant
    {
        public int Requested;
        public int Granted;
        public bool CapReached;   // true ise "dinlenme zamanı" hatırlatması gösterilir (FR-ECO-4)
    }

    /// <summary>
    /// XP (FR-ECO-2, FR-ECO-4). Oyun içi etkinlikler günlük sınıra tabidir; gerçek görev serisi ve rozetler değildir
    /// (oyunu uzun oynamayı değil, sorumluluğu ödüllendirir). Gün, cihazın YEREL tarihine göre döner.
    /// </summary>
    [Serializable]
    public sealed class XpSystem
    {
        public int TotalXp;
        /// <summary>
        /// Ulaşılan en yüksek seviye (23 Ekim 2026, ortak 20261023040000): yaş grubu büyüyünce aynı XP daha küçük seviyeye denk
        /// gelebilir; seviye düşmez, açılan yerler ve eşyalar geri alınmaz. Sunucu seviye kilidi de bunu okur (Xp.BestLevel).
        /// </summary>
        public int BestLevel;
        public int Day;          // yerel tarih gün numarası
        public int XpToday;      // bugün sınıra sayılan XP
        public int InGameToday;  // bugün oyun içinden gelen XP (gerçek görev ve seri hariç; sınıra sayılmayan rozet/parıltı dahil)
        public int RealToday;    // bugün gerçek görevden gelen XP

        /// <summary>Gerçek görev XP'sinin görünmez günlük payı en az bu kadar (oyun oynamadan görev yapan çocuk da XP görür).</summary>
        public const int RealTaskFloor = 20;

        public static int DayNumber(DateTime local) => (int)(local.Date.Ticks / TimeSpan.TicksPerDay);

        // Günlük oyun içi görevler (günde 3) kendiliğinden sınırlıdır; seviyeye oranlı XP'leri (S2) sınıra takılmasın diye sayılmaz.
        public static bool CountsTowardCap(XpSource s) => s != XpSource.TaskStreak && s != XpSource.Achievement && s != XpSource.RealTask && s != XpSource.DailyQuest;

        public int RemainingToday(DateTime local, int dailyCap)
        {
            Roll(local);
            return Math.Max(0, dailyCap - XpToday);
        }

        public XpGrant Add(int amount, XpSource source, DateTime local, int dailyCap)
        {
            Roll(local);
            var g = new XpGrant { Requested = Math.Max(0, amount) };
            if (g.Requested == 0) return g;
            if (CountsTowardCap(source))
            {
                g.Granted = Math.Min(g.Requested, Math.Max(0, dailyCap - XpToday));
                XpToday += g.Granted;
                g.CapReached = XpToday >= dailyCap;
            }
            else
            {
                g.Granted = g.Requested;
            }
            if (source != XpSource.RealTask && source != XpSource.TaskStreak) InGameToday += g.Granted;
            else if (source == XpSource.RealTask) RealToday += g.Granted;
            TotalXp += g.Granted;
            return g;
        }

        /// <summary>
        /// Onaylı gerçek görevin XP'si (M7, 22 Ekim 2026): bir günde gerçek görevden gelen XP o günkü oyun içi XP'yi geçmez
        /// (en az <see cref="RealTaskFloor"/>). Çocuk sınırı görmez; dolunca <see cref="XpGrant.CapReached"/> = true ve arayüz
        /// "bugünkü yıldız hedefine ulaştın" der. Coin, Güneş Taşı ve beceri yıldızı bundan etkilenmez.
        /// </summary>
        public XpGrant AddRealTask(int amount, DateTime local)
        {
            Roll(local);
            var room = Math.Max(0, Math.Max(RealTaskFloor, InGameToday) - RealToday);
            var g = new XpGrant { Requested = Math.Max(0, amount) };
            g.Granted = Math.Min(g.Requested, room);
            g.CapReached = g.Requested > 0 && g.Granted < g.Requested;
            RealToday += g.Granted;
            TotalXp += g.Granted;
            return g;
        }

        private void Roll(DateTime local)
        {
            var d = DayNumber(local);
            if (d != Day) { Day = d; XpToday = 0; InGameToday = 0; RealToday = 0; }
        }
    }

    /// <summary>
    /// Görev serisi (FR-TASK-6): art arda günlerde en az bir onaylı görev → bonus XP (coin değil).
    /// Seri kırılırsa ceza yok; sayaç 1'den yeniden başlar.
    /// </summary>
    [Serializable]
    public sealed class TaskStreak
    {
        public int LastDay = int.MinValue;
        public int Count;

        /// <returns>Bu kayıt yeni bir gün ise verilecek bonus XP, aynı günse 0.</returns>
        public int Record(DateTime local)
        {
            var d = XpSystem.DayNumber(local);
            if (d == LastDay) return 0;
            Count = d == LastDay + 1 ? Count + 1 : 1;
            LastDay = d;
            return Bonus(Count);
        }

        /// <summary>1. gün 10, her gün +5, 7. günden sonra 40'ta sabit.</summary>
        public static int Bonus(int count) => 10 + 5 * (Math.Min(Math.Max(count, 1), 7) - 1);

        /// <summary>Arayüz için: seri hâlâ sürüyor mu (bugün ya da dün kayıt var mı)?</summary>
        public bool IsAlive(DateTime local) => XpSystem.DayNumber(local) - LastDay <= 1;
    }
}
