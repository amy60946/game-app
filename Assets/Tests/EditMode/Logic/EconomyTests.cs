using System;
using NUnit.Framework;
using Pofi.Logic.Economy;

namespace Pofi.Tests.Logic
{
    public class EconomyTests
    {
        private static readonly DateTime Now = new DateTime(2026, 10, 13, 10, 0, 0, DateTimeKind.Utc);

        [Test]
        public void Spend_reduces_available_until_server_confirms()
        {
            var w = new Wallet { ServerCoins = 20 };
            Assert.AreEqual(SpendResult.Ok, w.TrySpend("food_apple", 2, 3, "tx1", Now, out _));
            Assert.AreEqual(14, w.Available);
            Assert.AreEqual(20, w.ServerCoins, "sunucu onaylamadan kesinleşmez");
            w.Acknowledge("tx1", 14);
            Assert.AreEqual(14, w.Available);
            Assert.IsEmpty(w.Pending);
        }

        [Test]
        public void Cannot_overspend_including_pending()
        {
            var w = new Wallet { ServerCoins = 10 };
            Assert.AreEqual(SpendResult.Ok, w.TrySpend("food_fish", 1, 6, "a", Now, out _));
            Assert.AreEqual(SpendResult.NotEnoughCoins, w.TrySpend("food_fish", 1, 6, "b", Now, out _));
            Assert.AreEqual(SpendResult.InvalidAmount, w.TrySpend("x", 0, 6, "c", Now, out _));
        }

        [Test]
        public void Offline_spends_are_settled_by_server_snapshot_and_server_wins()
        {
            var w = new Wallet { ServerCoins = 30 };
            w.TrySpend("clean_soap", 1, 3, "s1", Now, out _);
            w.TrySpend("food_apple", 1, 3, "s2", Now, out _);
            // Sunucu s1'i işledi, s2 henüz ulaşmadı; bu arada ebeveyn 10 coinlik görevi onayladı.
            var earned = w.ApplyServerSnapshot(30 - 3 + 10, new[] { "s1" });
            Assert.AreEqual(10, earned);
            Assert.AreEqual(37, w.ServerCoins);
            Assert.AreEqual(34, w.Available, "s2 hâlâ bekliyor");
        }

        [Test]
        public void Rejected_spend_is_returned_for_inventory_rollback()
        {
            var w = new Wallet { ServerCoins = 5 };
            w.TrySpend("food_fish", 1, 5, "r1", Now, out _);
            var back = w.Reject("r1", 0);
            Assert.AreEqual("food_fish", back.ItemId);
            Assert.AreEqual(0, w.Available);
        }

        [Test]
        public void Xp_daily_cap_applies_to_play_but_not_to_task_streak()
        {
            var xp = new XpSystem();
            var day = new DateTime(2026, 10, 13, 18, 0, 0);
            var g1 = xp.Add(200, XpSource.MiniGame, day, 250);
            var g2 = xp.Add(100, XpSource.CardGame, day, 250);
            Assert.AreEqual(200, g1.Granted);
            Assert.AreEqual(50, g2.Granted);
            Assert.IsTrue(g2.CapReached);
            Assert.AreEqual(30, xp.Add(30, XpSource.TaskStreak, day, 250).Granted, "görev serisi sınıra takılmaz");
            Assert.AreEqual(0, xp.Add(10, XpSource.Fishing, day, 250).Granted);
            Assert.AreEqual(250, xp.RemainingToday(day.AddDays(1), 250), "ertesi gün sıfırlanır");
            Assert.AreEqual(280, xp.TotalXp);
        }

        [Test]
        public void Streak_grows_and_restarts_without_penalty()
        {
            var s = new TaskStreak();
            var d = new DateTime(2026, 10, 1, 9, 0, 0);
            Assert.AreEqual(10, s.Record(d));
            Assert.AreEqual(0, s.Record(d.AddHours(5)), "aynı gün ikinci kez bonus yok");
            Assert.AreEqual(15, s.Record(d.AddDays(1)));
            Assert.AreEqual(20, s.Record(d.AddDays(2)));
            Assert.IsTrue(s.IsAlive(d.AddDays(3)));
            Assert.AreEqual(10, s.Record(d.AddDays(5)), "kırılınca 1'den başlar, ceza yok");
            Assert.AreEqual(40, TaskStreak.Bonus(30));
        }
    }
}
