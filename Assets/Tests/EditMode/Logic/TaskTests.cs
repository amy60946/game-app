using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    public class TaskTests
    {
        private static readonly DateTime Morning = new DateTime(2026, 10, 13, 9, 0, 0);
        private static readonly DateTime Utc = new DateTime(2026, 10, 13, 6, 0, 0, DateTimeKind.Utc);

        private static ChildTask T(string id, ChildTaskStatus s = ChildTaskStatus.Assigned, int coins = 10) => new ChildTask
        {
            TaskId = id, Date = "2026-10-13", Title = id, RewardCoins = coins, Status = s,
            DueLocalTicks = new DateTime(2026, 10, 13, 23, 59, 59).Ticks,
        };

        [Test]
        public void Child_transitions()
        {
            var t = T("a");
            Assert.AreEqual(ChangeResult.Ok, TaskRules.CanChange(t, ChildTaskStatus.ChildDone, Morning));
            Assert.AreEqual(ChangeResult.Ok, TaskRules.CanChange(t, ChildTaskStatus.DeclinedByChild, Morning));
            Assert.AreEqual(ChangeResult.NotAllowed, TaskRules.CanChange(t, ChildTaskStatus.Approved, Morning), "çocuk onaylayamaz");
            t.Status = ChildTaskStatus.ChildDone;
            Assert.AreEqual(ChangeResult.Ok, TaskRules.CanChange(t, ChildTaskStatus.Assigned, Morning), "onaydan önce geri alınabilir");
            t.Status = ChildTaskStatus.Approved;
            Assert.AreEqual(ChangeResult.AlreadyFinal, TaskRules.CanChange(t, ChildTaskStatus.Assigned, Morning));
        }

        [Test]
        public void Missed_task_cannot_be_marked_and_shows_last()
        {
            var t = T("a");
            var late = new DateTime(2026, 10, 14, 8, 0, 0);
            Assert.IsTrue(t.IsMissed(late));
            Assert.AreEqual(ChangeResult.Missed, TaskRules.CanChange(t, ChildTaskStatus.ChildDone, late));
            var board = new TaskBoard { Tasks = { t, T("b") } };
            board.Tasks[1].DueLocalTicks = new DateTime(2026, 10, 15).Ticks;
            Assert.AreEqual("b", board.ForDisplay(late).First().TaskId);
        }

        [Test]
        public void Offline_mark_survives_merge_until_server_decides()
        {
            var board = new TaskBoard();
            board.Merge(new[] { T("a"), T("b") });
            Assert.AreEqual(ChangeResult.Ok, board.Mark("a|2026-10-13", ChildTaskStatus.ChildDone, Morning, Utc));
            // Ağ yok; sunucu hâlâ eski durumu döndürüyor → yerel niyet korunur
            board.Merge(new[] { T("a"), T("b") });
            Assert.AreEqual(ChildTaskStatus.ChildDone, board.Find("a|2026-10-13").Status);
            Assert.AreEqual(1, board.Outbox.Count);
            // Ebeveyn onayladı → sunucu kazanır, kuyruk temizlenir, onay olayı
            var ev = board.Merge(new[] { T("a", ChildTaskStatus.Approved), T("b") });
            Assert.AreEqual(TaskEventKind.Approved, ev.Single().Kind);
            Assert.AreEqual(10, ev.Single().Task.RewardCoins);
            Assert.IsEmpty(board.Outbox);
        }

        [Test]
        public void Undo_replaces_previous_intent_in_outbox()
        {
            var board = new TaskBoard();
            board.Merge(new[] { T("a") });
            board.Mark("a|2026-10-13", ChildTaskStatus.ChildDone, Morning, Utc);
            board.Mark("a|2026-10-13", ChildTaskStatus.Assigned, Morning, Utc);
            Assert.AreEqual(1, board.Outbox.Count);
            Assert.AreEqual(ChildTaskStatus.Assigned, board.Outbox[0].To);
        }

        [Test]
        public void New_rejected_and_removed_events()
        {
            var board = new TaskBoard();
            var ev1 = board.Merge(new[] { T("a"), T("b") });
            Assert.AreEqual(2, ev1.Count(e => e.Kind == TaskEventKind.NewTask));
            var rejected = T("a", ChildTaskStatus.RejectedByParent);
            rejected.ParentNote = "Odanı birlikte toplayalım";
            var ev2 = board.Merge(new[] { rejected });
            Assert.IsTrue(ev2.Any(e => e.Kind == TaskEventKind.Rejected && e.Task.ParentNote.Contains("birlikte")));
            Assert.IsTrue(ev2.Any(e => e.Kind == TaskEventKind.Removed && e.Task.TaskId == "b"));
        }

        [Test]
        public void Ebeveyn_tekrar_dene_gorevi_yeniden_acar_ve_bir_kez_haber_verir()
        {
            // ortak 20261027130000: ebeveyn "Tekrar dene" → sunucu 'retry' (oyunda Atandı + Retry), not çocuğa görünür
            var board = new TaskBoard { Tasks = { T("a", ChildTaskStatus.ChildDone) } };
            var srv = T("a"); srv.Retry = true; srv.ParentNote = "Yatağı da topla";
            var ev = board.Merge(new[] { srv });
            Assert.AreEqual(1, ev.Count(e => e.Kind == TaskEventKind.Retry), "tekrar dene haberi");
            Assert.AreEqual(0, ev.Count(e => e.Kind == TaskEventKind.NewTask), "yeni görev sayılmaz");
            var t = board.Find("a|2026-10-13");
            Assert.IsTrue(t.Retry);
            Assert.AreEqual(ChangeResult.Ok, TaskRules.CanChange(t, ChildTaskStatus.ChildDone, Morning), "Yaptım yeniden açık");

            var again = T("a"); again.Retry = true;
            Assert.AreEqual(0, board.Merge(new[] { again }).Count(e => e.Kind == TaskEventKind.Retry), "aynı istek ikinci kez haber olmaz");

            // çocuk yeniden "Yaptım" dedi: bayrak kalkar; sunucu henüz eski haldeyken kuyruktaki niyet geçerli
            Assert.AreEqual(ChangeResult.Ok, board.Mark("a|2026-10-13", ChildTaskStatus.ChildDone, Morning, Utc));
            Assert.IsFalse(board.Find("a|2026-10-13").Retry);
            var stale = T("a"); stale.Retry = true;
            var ev2 = board.Merge(new[] { stale });
            Assert.AreEqual(ChildTaskStatus.ChildDone, board.Find("a|2026-10-13").Status);
            Assert.IsFalse(board.Find("a|2026-10-13").Retry);
            Assert.AreEqual(0, ev2.Count(e => e.Kind == TaskEventKind.Retry));
        }

        [Test]
        public void Tekrar_dene_ve_onay_notu_haberlerde()
        {
            var a = T("Odanı topla", ChildTaskStatus.Approved); a.ParentNote = "Harika toplamışsın";
            var r = T("Dişler"); r.Retry = true; r.ParentNote = "Arkadakiler de";
            var list = Pofi.Logic.App.NoticeDigest.Build(new[]
            {
                new TaskEvent { Kind = TaskEventKind.Approved, Task = a },
                new TaskEvent { Kind = TaskEventKind.Retry, Task = r },
            }, null);
            Assert.IsTrue(list.Any(n => n.Key == "notice.approved_one_note" && (string)n.Args[1] == "Harika toplamışsın"));
            Assert.IsTrue(list.Any(n => n.Key == "notice.retry_one_note" && (string)n.Args[0] == "Dişler"));
            var plain = T("Dişler"); plain.Retry = true;
            Assert.AreEqual("notice.retry_one", Pofi.Logic.App.NoticeDigest.Build(new[] { new TaskEvent { Kind = TaskEventKind.Retry, Task = plain } }, null)[0].Key);
        }

        [Test]
        public void Kart_zorlugu_ve_gunes_tasi_sozlesmeyle_ayni()
        {
            // ekonomi.md 5A: kolay 1 / orta 2 / zor 3 taş; kartta aynı sayıda nokta; deneme sunucusu da aynı kuralı kullanır
            Assert.AreEqual(1, RealTaskRewards.Stones("easy"));
            Assert.AreEqual(2, RealTaskRewards.Stones("medium"));
            Assert.AreEqual(3, RealTaskRewards.Stones("hard"));
            Assert.AreEqual(1, RealTaskRewards.Stones(null), "bilinmeyen zorluk kolay sayılır");
            Assert.AreEqual(2, RealTaskRewards.Rank("medium"));
            foreach (var d in new[] { "easy", "medium", "hard", null })
                Assert.AreEqual(RealTaskRewards.Stones(d), Pofi.Logic.Services.Mock.MockBackend.StonesFor(d));
        }
    }
}
