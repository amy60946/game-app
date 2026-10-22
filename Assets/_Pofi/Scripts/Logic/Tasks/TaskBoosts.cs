using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Services;

namespace Pofi.Logic.Tasks
{
    /// <summary>
    /// Zor görevde 2× XP teklifi (XP takibi Y2, kullanıcı onayı 22 Ekim 2026): "Yapamam" sonrası her seferinde değil —
    /// ilk "Yapamam"da bir kez, sonra yalnız çocuğun zorlandığı görevde (son 4 haftada tamamlama oranı %50'nin altı,
    /// en az 2 geçmiş örnek) ve haftada en çok 1 kez. Kabul ("Deneyeceğim") görevi yeniden açar; sonra onaylanırsa XP ×2.
    /// Geçmiş, senkronda görülen görev örneklerinin sonucundan yerelde tutulur (son 28 gün).
    /// </summary>
    [Serializable]
    public sealed class BoostState
    {
        public bool FirstShown;
        public int LastOfferDay = int.MinValue;
        public Dictionary<string, int> Outcomes = new Dictionary<string, int>();   // görev örneği → 1 yaptı (onay), 0 yapmadı; gün anahtarın içinde
    }

    public static class TaskBoosts
    {
        public const int WindowDays = 28, MinSamples = 2, CooldownDays = 7;
        public const double HardRate = 0.5;

        private static int Day(DateTime local) => Economy.XpSystem.DayNumber(local);

        private static int DayOf(string date) =>
            DateTime.TryParseExact(date, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var d)
                ? Economy.XpSystem.DayNumber(d) : int.MinValue;

        /// <summary>Geçmiş günlerin görev sonuçlarını kaydeder (senkrondan sonra); 28 günden eskisini siler.</summary>
        public static void RecordOutcomes(BoostState st, IEnumerable<ChildTask> tasks, DateTime local)
        {
            var today = Day(local);
            foreach (var t in tasks)
            {
                var d = DayOf(t.Date);
                if (d == int.MinValue || d >= today) continue;
                st.Outcomes[t.Key] = t.Status == ChildTaskStatus.Approved || t.Status == ChildTaskStatus.ChildDone ? 1 : 0;   // yaptı (onaylı ya da onay bekliyor)
            }
            foreach (var k in st.Outcomes.Keys.ToList())
            {
                var sep = k.IndexOf('|');
                if (sep < 0 || today - DayOf(k.Substring(sep + 1)) > WindowDays) st.Outcomes.Remove(k);
            }
        }

        /// <summary>Bu görevin son 4 haftadaki tamamlanma oranı (null: yeterli geçmiş yok).</summary>
        public static double? Rate(BoostState st, string taskId)
        {
            var prefix = taskId + "|";
            var mine = st.Outcomes.Where(kv => kv.Key.StartsWith(prefix, StringComparison.Ordinal)).Select(kv => kv.Value).ToList();
            if (mine.Count < MinSamples) return null;
            return mine.Average();
        }

        /// <summary>"Yapamam"dan hemen sonra teklif gösterilsin mi?</summary>
        public static bool ShouldOffer(BoostState st, ChildTask t, DateTime local)
        {
            if (t == null || t.IsFinal) return false;
            if (!st.FirstShown) return true;
            if (Day(local) - st.LastOfferDay < CooldownDays) return false;
            var r = Rate(st, t.TaskId);
            return r.HasValue && r.Value < HardRate;
        }

        public static void MarkOffered(BoostState st, DateTime local)
        {
            st.FirstShown = true;
            st.LastOfferDay = Day(local);
        }
    }

    /// <summary>Kişisel haftalık hedef (XP takibi Y6; sunucu: ortak proposed/20261022230000_weekly_goal).</summary>
    public sealed class WeeklyGoal
    {
        public string WeekStart;
        public int? Target;      // null: hedef yok (yalnız ölçüm ya da az görev)
        public int Done;
        public int Assigned;
        public bool Claimed;

        public bool Reached => Target.HasValue && Done >= Target.Value;
        public bool CanClaim => Reached && !Claimed;
        public int Left => Target.HasValue ? Math.Max(0, Target.Value - Done) : 0;

        /// <summary>Hedef ödülünün oyun içi XP'si: seviye ihtiyacının %10'u, en az 30.</summary>
        public static int XpFor(int levelNeed) => Math.Max(30, (int)Math.Round(levelNeed * 0.10));
    }

    public sealed class GoalClaim
    {
        public bool Ok;
        public string Error;     // no_goal / not_reached / already_claimed / offline
        public int Stones;
    }

    /// <summary>Görev ekleri (Y2 teklif kaydı, Y6 haftalık hedef). Sunucuda fonksiyon yoksa (öneri uygulanmadı) sessizce boş döner.</summary>
    public interface IGoalService
    {
        Task<ServiceError> RecordBoostAsync(string taskKey, bool accepted, CancellationToken ct = default);
        Task<WeeklyGoal> WeeklyGoalAsync(CancellationToken ct = default);
        Task<GoalClaim> ClaimWeeklyGoalAsync(CancellationToken ct = default);
    }
}
