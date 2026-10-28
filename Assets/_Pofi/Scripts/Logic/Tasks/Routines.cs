using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Tasks
{
    /// <summary>Bir günün rutini: aynı RoutineId'li görev örnekleri, RoutinePosition sırasıyla.</summary>
    public sealed class RoutineGroup
    {
        public string Id, Title, Icon;
        public List<ChildTask> Steps = new List<ChildTask>();
        /// <summary>Sıradaki adım (ilk açık adım); hepsi kapandıysa null.</summary>
        public ChildTask Next;
        /// <summary>Kapanan adım sayısı (yaptım, onaylı, yapamam, ret): ilerleme "Closed / Steps.Count".</summary>
        public int Closed;
        public bool Complete => Next == null;
        public int IndexOf(ChildTask t) => Steps.FindIndex(s => s.Key == t.Key);
    }

    /// <summary>Panodaki bir satır: ya tek görev ya da rutin kartı.</summary>
    public sealed class BoardEntry
    {
        public ChildTask Task;
        public RoutineGroup Routine;
    }

    /// <summary>
    /// Oyunda rutin kartı (kullanıcı onayı 28 Ekim 2026; ortak akislar.md 5.4 adım 8). Her adım yine ayrı görevdir: ayrı "Yaptım",
    /// onay, coin. Rutin yalnız bir gösterim grubudur: sıradaki adım vurgulu, ilerleme "2 / 4", tamamlanınca ek coin yok, kısa
    /// kutlama. Başarısızlık durumu yok: kaçırılan ya da reddedilen adım yalnız kapanmış sayılır, rutin ilerler.
    /// </summary>
    public static class Routines
    {
        /// <summary>Çocuğun şimdi yapabileceği adım: atanmış ve süresi geçmemiş.</summary>
        public static bool IsOpen(ChildTask t, DateTime local) => t.Status == ChildTaskStatus.Assigned && !t.IsMissed(local);

        /// <summary>Çocuğun yaptığı adım (onay bekliyor ya da onaylandı): kartta üstü çizili.</summary>
        public static bool IsDone(ChildTask t) => t.Status == ChildTaskStatus.ChildDone || t.Status == ChildTaskStatus.Approved;

        /// <summary>
        /// Panodaki sırayı korur; aynı rutinin en az iki adımı varsa ilk göründüğü yerde tek rutin kartına toplanır.
        /// Tek adımlı ya da rutinsiz görev olduğu gibi kalır.
        /// </summary>
        public static List<BoardEntry> Layout(IList<ChildTask> tasks, DateTime local)
        {
            var counts = tasks.Where(t => !string.IsNullOrEmpty(t.RoutineId)).GroupBy(t => t.RoutineId).ToDictionary(g => g.Key, g => g.Count());
            var list = new List<BoardEntry>();
            var seen = new HashSet<string>();
            foreach (var t in tasks)
            {
                if (string.IsNullOrEmpty(t.RoutineId) || counts[t.RoutineId] < 2) { list.Add(new BoardEntry { Task = t }); continue; }
                if (!seen.Add(t.RoutineId)) continue;
                list.Add(new BoardEntry { Routine = Group(tasks, t.RoutineId, local) });
            }
            return list;
        }

        public static RoutineGroup Group(IEnumerable<ChildTask> tasks, string routineId, DateTime local)
        {
            var steps = tasks.Where(t => t.RoutineId == routineId).Select((t, i) => (t, i))
                .OrderBy(p => p.t.RoutinePosition < 0 ? int.MaxValue : p.t.RoutinePosition).ThenBy(p => p.i).Select(p => p.t).ToList();
            var first = steps.FirstOrDefault(s => !string.IsNullOrWhiteSpace(s.RoutineTitle)) ?? steps.FirstOrDefault();
            return new RoutineGroup
            {
                Id = routineId, Title = first?.RoutineTitle?.Trim(), Icon = first?.RoutineIcon, Steps = steps,
                Next = steps.FirstOrDefault(s => IsOpen(s, local)),
                Closed = steps.Count(s => !IsOpen(s, local)),
            };
        }

        /// <summary>Bu adım "Yaptım" ile kapanınca rutin biter mi (kutlama için; çağıran işaretlemeden önce sorar).</summary>
        public static bool FinishesWith(IEnumerable<ChildTask> tasks, ChildTask step, DateTime local)
        {
            if (step == null || string.IsNullOrEmpty(step.RoutineId) || !IsOpen(step, local)) return false;
            var g = Group(tasks, step.RoutineId, local);
            return g.Steps.Count >= 2 && g.Steps.All(s => s.Key == step.Key || !IsOpen(s, local));
        }

        /// <summary>Rutin simgesi (ParentApp/ClinicApp simge adı, ör. "sunny-outline") → oyundaki simge; bilinmeyen: yıldız.</summary>
        public static string IconFor(string icon)
        {
            var k = (icon ?? "").Trim().ToLowerInvariant().Replace("-outline", "").Replace("-sharp", "");
            switch (k)
            {
                case "sunny": case "sun": case "partly-sunny": return "ui_sunstone";
                case "moon": case "bed": case "cloudy-night": return "home_bed";
                case "school": case "library": case "book": case "reader": case "document-text": return "home_bookshelf";
                case "home": return "ui_home";
                case "people": case "heart": case "chatbubbles": return "ui_heart";
                case "bicycle": case "football": case "fitness": case "trophy": return "ui_trophy";
                case "leaf": case "flower": return "ui_garden";
                default: return "ui_star";
            }
        }
    }
}
