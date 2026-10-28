using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    public class RoutineTests
    {
        private static readonly DateTime Now = new DateTime(2026, 10, 28, 8, 0, 0);

        private static ChildTask T(string id, string routine, int pos, ChildTaskStatus st = ChildTaskStatus.Assigned) => new ChildTask
        {
            TaskId = id, Date = "2026-10-28", Title = id, Status = st, DueLocalTicks = Now.Date.AddDays(1).AddTicks(-1).Ticks,
            RoutineId = routine, RoutineTitle = routine == null ? null : "Güne hazır sabah", RoutineIcon = routine == null ? null : "sun",
            RoutinePosition = routine == null ? -1 : pos,
        };

        [Test]
        public void Rutin_adimlari_tek_kartta_sirayla_toplanir()
        {
            var tasks = new List<ChildTask> { T("kitap", null, -1), T("yatak", "r1", 1), T("dis", "r1", 0), T("kahvalti", "r1", 2) };
            var board = Routines.Layout(tasks, Now);
            Assert.AreEqual(2, board.Count, "rutinsiz görev + tek rutin kartı");
            Assert.AreEqual("kitap", board[0].Task.TaskId);
            var r = board[1].Routine;
            Assert.AreEqual(new[] { "dis", "yatak", "kahvalti" }, r.Steps.Select(s => s.TaskId).ToArray(), "routine_position sırası");
            Assert.AreEqual("Güne hazır sabah", r.Title);
            Assert.AreEqual("dis", r.Next.TaskId);
            Assert.AreEqual(0, r.Closed);
        }

        [Test]
        public void Tek_adimli_rutin_sıradan_kart()
        {
            var board = Routines.Layout(new List<ChildTask> { T("dis", "r1", 0), T("kitap", null, -1) }, Now);
            Assert.IsTrue(board.All(b => b.Task != null));
        }

        [Test]
        public void Sıradaki_adım_ilk_açık_adım_basarisizlik_yok()
        {
            var tasks = new List<ChildTask>
            {
                T("dis", "r1", 0, ChildTaskStatus.Approved), T("yatak", "r1", 1, ChildTaskStatus.RejectedByParent),
                T("kahvalti", "r1", 2), T("canta", "r1", 3),
            };
            var r = Routines.Group(tasks, "r1", Now);
            Assert.AreEqual("kahvalti", r.Next.TaskId, "reddedilen adım rutini durdurmaz");
            Assert.AreEqual(2, r.Closed);
            Assert.IsFalse(r.Complete);
        }

        [Test]
        public void Son_acik_adim_rutini_bitirir_kutlama_bir_kez()
        {
            var tasks = new List<ChildTask> { T("dis", "r1", 0, ChildTaskStatus.ChildDone), T("yatak", "r1", 1) };
            Assert.IsTrue(Routines.FinishesWith(tasks, tasks[1], Now));
            Assert.IsFalse(Routines.FinishesWith(tasks, tasks[0], Now), "zaten yapılmış adım yeniden bitirmez");
            tasks[1].Status = ChildTaskStatus.ChildDone;
            Assert.IsTrue(Routines.Group(tasks, "r1", Now).Complete);
            Assert.IsFalse(Routines.FinishesWith(tasks, tasks[1], Now), "bitmiş rutinde kutlama tekrarlanmaz");
        }

        [Test]
        public void Yapamam_denen_adim_rutini_durdurmaz()
        {
            var tasks = new List<ChildTask> { T("dis", "r1", 0, ChildTaskStatus.DeclinedByChild), T("yatak", "r1", 1) };
            Assert.AreEqual("yatak", Routines.Group(tasks, "r1", Now).Next.TaskId);
            Assert.IsTrue(Routines.FinishesWith(tasks, tasks[1], Now), "son açık adım yapılınca rutin biter");
        }

        [Test]
        public void Rutin_simgesi_oyun_simgesine_eslenir()
        {
            Assert.AreEqual("ui_sunstone", Routines.IconFor("sunny-outline"));
            Assert.AreEqual("home_bed", Routines.IconFor("moon-outline"));
            Assert.AreEqual("home_bookshelf", Routines.IconFor("school-outline"));
            Assert.AreEqual("ui_star", Routines.IconFor(null));
            Assert.AreEqual("ui_star", Routines.IconFor("bilinmeyen"));
        }
    }
}
