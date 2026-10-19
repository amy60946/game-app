using System;
using System.Linq;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Önizleme / geliştirme: gerçek ebeveyn uygulaması bağlanana kadar (M4) "ebeveyn" rolünü oynar.
    /// Bugün için örnek görevler atar ve çocuğun "yaptım" dediklerini onaylar. Yalnızca <see cref="MockBackend"/> ile çalışır.
    /// </summary>
    public static class DemoParent
    {
        public static readonly (string Id, string Title, int Coins, string Skill, string Difficulty)[] Samples =
        {
            ("demo_teeth", "Dişlerini fırçala", 5, "Öz Bakım", "easy"),
            ("demo_room", "Odanı topla", 10, "Sorumluluk", "medium"),
            ("demo_read", "15 dakika kitap oku", 10, "Odaklanma", "medium"),
            ("demo_table", "Sofrayı kurmaya yardım et", 5, "Takım Çalışması", "easy"),
            ("demo_homework", "Ödevini bitir", 20, "Sorumluluk", "hard"),
        };

        public static string Day(DateTime local) => local.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);

        /// <summary>Bugün için görev yoksa örnekleri atar. Atanan görev sayısını döndürür.</summary>
        public static int EnsureToday(MockBackend backend, DateTime local)
        {
            var day = Day(local);
            if (backend.AllTasks.Any(t => t.Date == day)) return 0;
            foreach (var s in Samples) backend.ParentAssign(s.Id, day, s.Title, s.Coins, Recurrence.Daily, s.Skill, s.Difficulty);
            return Samples.Length;
        }

        /// <summary>Çocuğun yaptım dediği tüm görevleri onaylar. Onaylanan sayısı.</summary>
        public static int ApproveAll(MockBackend backend)
        {
            var keys = backend.AllTasks.Where(t => t.Status == ChildTaskStatus.ChildDone).Select(t => t.Key).ToList();
            foreach (var k in keys) backend.ParentApprove(k, "Aferin!");
            return keys.Count;
        }

        public static int Pending(MockBackend backend) => backend.AllTasks.Count(t => t.Status == ChildTaskStatus.ChildDone);
    }
}
