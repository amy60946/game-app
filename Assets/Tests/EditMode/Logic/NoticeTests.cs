using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Rewards;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    public class NoticeTests
    {
        private static TaskEvent Ev(TaskEventKind k, string id, string date = "2026-10-22") =>
            new TaskEvent { Kind = k, Task = new ChildTask { TaskId = id, Date = date, Title = "Görev " + id } };

        [Test]
        public void Yeni_gorevler_tek_haberde_tekrarlar_sayilmaz()
        {
            var n = NoticeDigest.Build(new[] { Ev(TaskEventKind.NewTask, "a"), Ev(TaskEventKind.NewTask, "a", "2026-10-23"), Ev(TaskEventKind.NewTask, "b") }, null);
            Assert.AreEqual("notice.new_task_many", n.Single().Key);
            Assert.AreEqual(2, n.Single().Args[0]);
            Assert.AreEqual("notice.new_task_one", NoticeDigest.Build(new[] { Ev(TaskEventKind.NewTask, "a") }, null).Single().Key);
        }

        [Test]
        public void Olumlu_once_ret_yumusak_ve_en_cok_uc_haber()
        {
            var rewards = new[]
            {
                new RewardEvent { Kind = RewardEventKind.Given, Request = new RewardRequest { Title = "Park" } },
                new RewardEvent { Kind = RewardEventKind.Declined, Request = new RewardRequest { Title = "Film" } },
            };
            var n = NoticeDigest.Build(new[] { Ev(TaskEventKind.Approved, "a"), Ev(TaskEventKind.Rejected, "b"), Ev(TaskEventKind.NewTask, "c") }, rewards);
            Assert.AreEqual(NoticeDigest.MaxPerSync, n.Count);
            Assert.AreEqual("notice.reward_given", n[0].Key);
            Assert.IsTrue(n[0].Happy);
            Assert.AreEqual("notice.more", n.Last().Key);
            Assert.AreEqual(3, n.Last().Args[0]);

            var r = NoticeDigest.Build(new[] { Ev(TaskEventKind.Rejected, "b") }, null).Single();
            Assert.AreEqual("notice.try_again_one", r.Key);
            Assert.IsFalse(r.Happy);
            Assert.AreEqual(0, NoticeDigest.Build(null, null).Count);
        }

        [Test]
        public void Kuyruk_sakin_ana_kadar_bekler_ve_birikince_ozetlenir()
        {
            var box = new NoticeInbox();
            box.Add(NoticeDigest.Build(new[] { Ev(TaskEventKind.NewTask, "a") }, null));
            box.Add(NoticeDigest.Build(new[] { Ev(TaskEventKind.Approved, "a") }, null));
            box.Add(NoticeDigest.Build(new[] { Ev(TaskEventKind.Approved, "b"), Ev(TaskEventKind.Approved, "c") }, null));
            box.Add(NoticeDigest.Build(new[] { Ev(TaskEventKind.Rejected, "d") }, null));
            Assert.AreEqual(0, box.Drain(calmMoment: false).Count, "mini oyunda gösterilmez");
            var shown = box.Drain(calmMoment: true);
            Assert.AreEqual(3, shown.Count);
            Assert.AreEqual("notice.more", shown.Last().Key);
            Assert.AreEqual(0, box.Count);
        }

        [Test]
        public void Push_kapali_ve_kurallari()
        {
            var noon = new DateTime(2026, 10, 22, 16, 0, 0);
            Assert.IsFalse(PushPolicy.MaySend("task_assigned", noon, 0, true, false), "kod hazır ama kapalı");
            Assert.IsFalse(Array.Exists(PushPolicy.AllowedKinds, k => k == "task_rejected" || k == "task_declined"), "olumsuz haber cihaz bildirimi olmaz");
        }
    }
}
