using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Services.Supabase;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    /// <summary>XP takibi Y2 (2× XP teklifi), Y5 (hatırlatmadan önce), Y6 (haftalık hedef) — 22 Ekim 2026.</summary>
    public class XpTrackingTests
    {
        private static readonly DateTime Utc = new DateTime(2026, 10, 22, 6, 0, 0, DateTimeKind.Utc);
        private static readonly DateTime Morning = new DateTime(2026, 10, 22, 8, 0, 0);   // Perşembe
        private const string Day = "2026-10-22";

        private static (MockBackend server, SyncCoordinator sync, GameState s) Setup()
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            var sync = new SyncCoordinator(server, server, server, data);
            var s = GameState.NewFor("c", Utc);
            s.PetId = "pet_01"; s.PetName = "Pofi";
            return (server, sync, s);
        }

        [Test]
        public void Hatirlatmadan_once_yapilan_gorev_yarim_gorev_XPsi_ekler()
        {
            var (server, sync, s) = Setup();
            server.ParentAssign("t_teeth", Day, "Dişlerini fırçala", 5, Recurrence.Once, null, "medium", "09:00");
            server.ParentAssign("t_late", Day, "Odanı topla", 5, Recurrence.Once, null, "medium", "07:30");
            server.ParentAssign("t_none", Day, "Kitap oku", 5, Recurrence.Once, null, "medium");
            sync.SyncAsync(s, Morning, Utc).Wait();
            Assert.AreEqual("09:00", s.Tasks.Find("t_teeth|" + Day).Reminder);
            foreach (var k in new[] { "t_teeth", "t_late", "t_none" }) s.Tasks.Mark(k + "|" + Day, ChildTaskStatus.ChildDone, Morning, Utc);
            Assert.AreEqual(Morning.Ticks, s.Tasks.Find("t_teeth|" + Day).DoneLocalTicks);
            sync.SyncAsync(s, Morning, Utc).Wait();
            Assert.AreEqual(Morning.Ticks, s.Tasks.Find("t_teeth|" + Day).DoneLocalTicks, "birleştirmede yerel alan korunur");
            Assert.IsTrue(RealTaskRewards.SelfStarted(s.Tasks.Find("t_teeth|" + Day)));
            Assert.IsFalse(RealTaskRewards.SelfStarted(s.Tasks.Find("t_late|" + Day)), "hatırlatmadan sonra bonus yok");
            Assert.IsFalse(RealTaskRewards.SelfStarted(s.Tasks.Find("t_none|" + Day)), "hatırlatmasız görevde bonus yok");
            // günlük pay oyun içi XP'ye bağlı: önce biraz oyun içi XP
            s.Xp.Add(40, Pofi.Logic.Economy.XpSource.DailyQuest, Morning, 300);
            server.ParentApprove("t_teeth|" + Day);
            var r = sync.SyncAsync(s, Morning, Utc).Result;
            Assert.AreEqual(1, r.SelfStarted);
            Assert.AreEqual(10 + 5, r.RealTaskXp, "orta 10 + yarısı 5");
        }

        [Test]
        public void Iki_kat_teklifi_ilk_kez_sonra_yalniz_zorlanilan_gorevde_haftada_bir()
        {
            var st = new BoostState();
            var t = new ChildTask { TaskId = "hw", Date = Day, Status = ChildTaskStatus.DeclinedByChild };
            Assert.IsTrue(TaskBoosts.ShouldOffer(st, t, Morning), "ilk Yapamam'da bir kez");
            TaskBoosts.MarkOffered(st, Morning);
            Assert.IsFalse(TaskBoosts.ShouldOffer(st, t, Morning.AddDays(3)), "haftada en çok 1");
            Assert.IsFalse(TaskBoosts.ShouldOffer(st, t, Morning.AddDays(8)), "geçmiş yoksa (oran bilinmiyor) teklif yok");
            // geçmiş: 4 örnekten 1'i yapılmış (%25) → zor görev
            var past = Enumerable.Range(1, 4).Select(i => new ChildTask
            {
                TaskId = "hw", Date = Morning.AddDays(8 - i).ToString("yyyy-MM-dd"),
                Status = i == 1 ? ChildTaskStatus.Approved : ChildTaskStatus.DeclinedByChild,
            }).ToList();
            past.Add(new ChildTask { TaskId = "easy", Date = Morning.AddDays(6).ToString("yyyy-MM-dd"), Status = ChildTaskStatus.Approved });
            past.Add(new ChildTask { TaskId = "easy", Date = Morning.AddDays(5).ToString("yyyy-MM-dd"), Status = ChildTaskStatus.ChildDone });
            TaskBoosts.RecordOutcomes(st, past, Morning.AddDays(8));
            Assert.AreEqual(0.25, TaskBoosts.Rate(st, "hw").Value, 1e-9);
            Assert.IsTrue(TaskBoosts.ShouldOffer(st, t, Morning.AddDays(8)), "zorlandığı görevde, 7 gün sonra");
            Assert.IsFalse(TaskBoosts.ShouldOffer(st, new ChildTask { TaskId = "easy", Date = Day }, Morning.AddDays(8)), "kolay bulduğu görevde yok");
            TaskBoosts.RecordOutcomes(st, new List<ChildTask>(), Morning.AddDays(40));
            Assert.IsNull(TaskBoosts.Rate(st, "hw"), "28 günden eski sonuçlar silinir");
        }

        [Test]
        public void Kabul_edilen_teklif_onayda_iki_kat_XP_verir()
        {
            var (server, sync, s) = Setup();
            server.ParentAssign("t_hw", Day, "Ödev", 10, Recurrence.Once, null, "hard");
            sync.SyncAsync(s, Morning, Utc).Wait();
            var key = "t_hw|" + Day;
            s.Tasks.Mark(key, ChildTaskStatus.DeclinedByChild, Morning, Utc);
            Assert.AreEqual(Pofi.Logic.Services.ServiceError.None, server.RecordBoostAsync(key, true).Result);
            Assert.IsTrue(server.Boosts[key]);
            s.Tasks.Mark(key, ChildTaskStatus.Assigned, Morning, Utc);
            s.Tasks.Find(key).Boosted = true;
            s.Tasks.Mark(key, ChildTaskStatus.ChildDone, Morning, Utc);
            sync.SyncAsync(s, Morning, Utc).Wait();
            Assert.IsTrue(s.Tasks.Find(key).Boosted, "kabul birleştirmede korunur");
            s.Xp.Add(100, Pofi.Logic.Economy.XpSource.DailyQuest, Morning, 300);
            server.ParentApprove(key);
            var r = sync.SyncAsync(s, Morning, Utc).Result;
            Assert.AreEqual(28, r.RealTaskXp, "zor 14 × 2");
            Assert.IsTrue(r.RealTaskRewards.Single().Boosted);
        }

        [Test]
        public void Haftalik_hedef_gecmisin_yuzde_yirmi_fazlasi_tavanli_ve_bir_kez_odullu()
        {
            var data = TestData.Load();
            var server = new MockBackend(data) { Today = Morning };
            var monday = new DateTime(2026, 10, 19);
            string D(DateTime d) => d.ToString("yyyy-MM-dd");
            // bu hafta 7 günlük görev
            for (var i = 0; i < 7; i++) server.ParentAssign("daily", D(monday.AddDays(i)), "Diş", 5);
            Assert.IsNull(server.GoalFor(Morning).Target, "geçmiş yok: yalnız ölçüm");
            // 2 hafta önce 5, geçen hafta 3 onaylı
            void Past(int offset)
            {
                var t = server.ParentAssign("p" + offset, D(monday.AddDays(offset)), "Eski", 5);
                server.SetStatusAsync(t.Key, ChildTaskStatus.ChildDone).Wait();
                server.ParentApprove(t.Key);
            }
            foreach (var o in new[] { -14, -13, -12, -11, -10, -7, -6, -5 }) Past(o);
            var g = server.GoalFor(Morning);
            Assert.AreEqual(5, g.Target, "(5 + 3) / 2 × 1,2 = 4,8 → 5");
            Assert.AreEqual(7, g.Assigned);
            Assert.AreEqual("not_reached", server.ClaimWeeklyGoalAsync().Result.Error);
            server.WeeklyCap = 4;
            Assert.AreEqual(4, server.GoalFor(Morning).Target, "ebeveyn düşürür");
            for (var i = 0; i < 4; i++)
            {
                var k = "daily|" + D(monday.AddDays(i));
                server.SetStatusAsync(k, ChildTaskStatus.ChildDone).Wait();
                server.ParentApprove(k);
            }
            var stones = server.SunStones;
            var c = server.ClaimWeeklyGoalAsync().Result;
            Assert.IsTrue(c.Ok);
            Assert.AreEqual(stones + 2, server.SunStones, "+2 Güneş Taşı");
            Assert.AreEqual("already_claimed", server.ClaimWeeklyGoalAsync().Result.Error);
            Assert.Greater(WeeklyGoal.XpFor(200), 29);
            Assert.AreEqual(495, WeeklyGoal.XpFor(4946), "seviye ihtiyacının %10'u");
        }

        [Test]
        public void Sunucu_hedef_yaniti_cozulur()
        {
            var g = SupabaseGameService.ParseGoal("{\"week_start\":\"2026-10-19\",\"target\":6,\"auto\":6,\"cap\":null,\"done\":2,\"assigned\":7,\"claimed\":false}");
            Assert.AreEqual(6, g.Target);
            Assert.AreEqual(4, g.Left);
            Assert.IsFalse(g.CanClaim);
            Assert.IsNull(SupabaseGameService.ParseGoal("{\"week_start\":\"2026-10-19\",\"target\":null,\"done\":0,\"assigned\":2,\"claimed\":false}").Target);
            Assert.IsNull(SupabaseGameService.ParseGoal("bozuk"));
        }
    }
}
