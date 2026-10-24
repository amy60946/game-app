using System;
using System.Linq;
using Pofi.Logic.Island;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.App
{
    /// <summary>İlk gün adımı (Ö5 "el ele").</summary>
    public enum FirstDayStep { Story, Pet, Walk, Feed, Board, Mark, Wait, Stone, Done }

    /// <summary>
    /// İlk gün akışı (Ö5; omurga analizi): kısa hikâye → pet seç → yürü → besle → Ev Görevleri panosu → "Yaptım" →
    /// onay beklenir → ilk Güneş Taşı ile ilk sis kalkar. Bu sürede diğer tanıtım ipuçları bekler (kendi yerlerinde açılır).
    /// Çocuk takılmaz: panoda görev yoksa ya da ilk açılıştan 24 saat geçtiyse akış biter. Eski oyuncular akışı görmez.
    /// </summary>
    public static class FirstDay
    {
        public const string DoneFlag = "first_day_done";   // GameState.SeenTips içinde
        public static readonly TimeSpan MaxLength = TimeSpan.FromHours(24);

        /// <summary>Oyun yüklenince çağrılır. İlk açılış zamanını yazar; pet'i olan (eski) oyuncu için akışı kapatır.</summary>
        public static void Start(GameState s, DateTime nowUtc)
        {
            if (s == null || s.FirstLaunchUtcTicks != 0) return;
            s.FirstLaunchUtcTicks = nowUtc.Ticks;
            if (s.HasPet) Finish(s);
        }

        public static void Finish(GameState s) { if (s != null) s.SeenTips.Add(DoneFlag); }

        public static bool IsActive(GameState s, DateTime local, DateTime nowUtc) => Current(s, local, nowUtc) != FirstDayStep.Done;

        public static FirstDayStep Current(GameState s, DateTime local, DateTime nowUtc)
        {
            if (s == null) return FirstDayStep.Story;
            if (s.SeenTips.Contains(DoneFlag)) return FirstDayStep.Done;
            if (s.FirstLaunchUtcTicks > 0 && nowUtc.Ticks - s.FirstLaunchUtcTicks > MaxLength.Ticks) return FirstDayStep.Done;
            if (Onboarding.Pending(s, Onboarding.Story)) return FirstDayStep.Story;
            if (!s.HasPet) return FirstDayStep.Pet;
            if (Onboarding.Pending(s, Onboarding.Walk)) return FirstDayStep.Walk;
            if (Onboarding.Pending(s, Onboarding.Feed)) return FirstDayStep.Feed;
            if (SunStoneBook.PlacedTotal(s.SunStones) > 0) return FirstDayStep.Done;
            if (SunStoneBook.Available(s.SunStones) > 0) return FirstDayStep.Stone;
            var tasks = s.Tasks.Tasks;
            if (tasks.Any(t => t.Status == ChildTaskStatus.ChildDone)) return FirstDayStep.Wait;
            if (Onboarding.Pending(s, Onboarding.Board)) return FirstDayStep.Board;
            if (tasks.Any(t => t.Status == ChildTaskStatus.Assigned && !t.IsMissed(local))) return FirstDayStep.Mark;
            return FirstDayStep.Done;   // görev yok: akış çocuğu bekletmez
        }

        /// <summary>İlk gün sürerken genel ipucu gösterilebilir mi? (ilk gün ipuçları ve kapı/oyun yerleri her zaman)</summary>
        public static bool AllowsTip(FirstDayStep step, string tipId)
        {
            if (step == FirstDayStep.Done) return true;
            switch (tipId)
            {
                case Onboarding.Walk: case Onboarding.Feed: case Onboarding.Wash: case Onboarding.Enter: case Onboarding.Play:
                case Onboarding.Story: case Onboarding.Board: case Onboarding.Mark: case Onboarding.Stone: case Onboarding.Shop:
                case Onboarding.TasksHome: case Onboarding.TasksDone: case Onboarding.TasksGame:   // Görevler penceresi tanıtımı (ilk gün en çok orada gerekir)
                case Onboarding.MapFar: case Onboarding.MapPin:   // haritada hedef imi (GB18-8): yeni başlayan en çok ilk gün kaybolur
                    return true;
                default:
                    return false;
            }
        }
    }
}
