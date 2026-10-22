using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Fishing;
using Pofi.Logic.Garden;
using Pofi.Logic.Meta;
using Pofi.Logic.Profile;
using Pofi.Logic.Progression;
using Pofi.Logic.Shop;

namespace Pofi.Tests.Logic
{
    public class MetaTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 13, 16, 0, 0);
        private static readonly DateTime Utc = new DateTime(2026, 10, 13, 13, 0, 0, DateTimeKind.Utc);

        [Test]
        public void Badges_are_earned_once_when_counter_reaches_target()
        {
            var d = TestData.Load();
            var c = new Counters();
            var owned = new HashSet<string>();
            c.Add("tasks_approved", 1, Local);
            var first = Badges.Evaluate(d.Badges, c, owned);
            Assert.AreEqual("badge_first_task", first.Single().Id);
            Assert.IsEmpty(Badges.Evaluate(d.Badges, c, owned));
        }

        [Test]
        public void Daily_quests_are_stable_for_the_day_and_only_unlocked()
        {
            var d = TestData.Load();
            var levels = new LevelTable(d.Levels);
            var st = new DailyQuestState();
            DailyQuests.EnsureForToday(st, d, id => levels.IsUnlocked(id, 1), "child_a", Local);
            var ids = st.Ids.ToList();
            Assert.AreEqual(3, ids.Count);
            Assert.IsTrue(ids.All(id => levels.IsUnlocked(d.DailyQuests.First(q => q.Id == id).Unlock, 1)));
            DailyQuests.EnsureForToday(st, d, id => levels.IsUnlocked(id, 1), "child_a", Local.AddHours(3));
            CollectionAssert.AreEqual(ids, st.Ids, "aynı gün değişmez");

            var c = new Counters();
            var q0 = d.DailyQuests.First(q => q.Id == ids[0]);
            c.Add(q0.Counter, q0.Target, Local);
            Assert.AreEqual(q0.Id, DailyQuests.Claim(st, d, c).Single(q => q.Id == q0.Id).Id);
            Assert.IsFalse(DailyQuests.Claim(st, d, c).Any(q => q.Id == q0.Id), "ödül bir kez alınır");
        }

        [Test]
        public void Gunluk_gorev_XPsi_seviyeye_oranli_ve_sinira_sayilmaz()
        {
            var d = TestData.Load();
            var levels = new LevelTable(d.Levels);
            var q = d.DailyQuests.First(x => x.Id == "dq_feed_2");   // 15 XP
            int Need(int lv) => levels.TotalXpFor(lv + 1) - levels.TotalXpFor(lv);
            Assert.AreEqual(15, DailyQuests.XpFor(q, Need(1)), "alt seviyede verideki sayının altına inmez");
            var high = DailyQuests.XpFor(q, Need(14));
            Assert.AreEqual((int)Math.Round(Need(14) * 0.04), high, "Sv14: seviyenin %4'ü");
            Assert.Greater(high, 100);
            var xp = new Pofi.Logic.Economy.XpSystem();
            xp.Add(300, Pofi.Logic.Economy.XpSource.MiniGame, Local, 300);
            Assert.AreEqual(high, xp.Add(high, Pofi.Logic.Economy.XpSource.DailyQuest, Local, 300).Granted, "günlük görev sınıra takılmaz");
            Assert.IsTrue(d.DailyQuests.Any(x => x.Id == "dq_harvest_2" && x.Counter == "harvests" && x.Unlock == "region_garden"), "bahçe görevi (M3)");
        }

        [Test]
        public void Gunluk_sandik_uc_gorev_bitince_bir_kez_acilir_coin_vermez()
        {
            var d = TestData.Load();
            var inv = new Inventory();
            var st = new DailyQuestState { Day = 20000, Ids = new List<string> { "dq_feed_2", "dq_wash_1", "dq_play_3" } };
            Assert.IsFalse(DailyChest.Ready(st));
            st.Claimed.AddRange(new[] { "dq_feed_2", "dq_wash_1" });
            Assert.IsNull(DailyChest.Open(st, d, inv, 5, "c"), "üç görev bitmeden açılmaz");
            st.Claimed.Add("dq_play_3");
            Assert.IsTrue(DailyChest.Ready(st));
            var a = DailyChest.Roll(st, d, inv, 5, "c");
            Assert.AreEqual(a.ItemId, DailyChest.Roll(st, d, inv, 5, "c").ItemId, "aynı gün aynı sonuç");
            var p = DailyChest.Open(st, d, inv, 5, "c");
            Assert.IsNotNull(p);
            Assert.IsTrue(inv.Owns(p.ItemId), "ödül envantere girer");
            Assert.IsTrue(new[] { ChestPrize.Food, ChestPrize.Seed, ChestPrize.Surprise }.Contains(p.Kind));
            Assert.IsNull(DailyChest.Open(st, d, inv, 5, "c"), "günde bir kez");
            Assert.AreEqual(100, DailyChest.Odds.Sum(o => o.Percent), "görünür oranlar %100");
            // dağılım: çok günde üç tür de çıkar, sürpriz eşya seviyesi açık ve sahip olunmayan
            var kinds = new HashSet<string>();
            for (var day = 0; day < 400; day++)
            {
                var s2 = new DailyQuestState { Day = 20000 + day, Ids = new List<string> { "x" }, Claimed = new List<string> { "x" } };
                var r = DailyChest.Roll(s2, d, inv, 3, "c");
                kinds.Add(r.Kind);
                if (r.Kind == ChestPrize.Surprise) Assert.LessOrEqual(d.Item(r.ItemId).Level, 3);
            }
            Assert.AreEqual(3, kinds.Count);
        }

        [Test]
        public void Garden_plant_water_grow_harvest()
        {
            var d = TestData.Load();
            var g = new GardenState();
            g.EnsurePlots(5);
            Assert.AreEqual(0, g.Plots.Count, "bahçe Sv6'da açılır");
            g.EnsurePlots(6);
            Assert.AreEqual(3, g.Plots.Count);
            var inv = new Inventory();
            var seed = d.Item("seed_carrot");
            Assert.AreEqual(GardenResult.NoSeed, g.Plant(0, seed, inv));
            inv.Add(seed);
            Assert.AreEqual(GardenResult.Ok, g.Plant(0, seed, inv));
            Assert.AreEqual(PlotState.NeedsWater, g.Plots[0].StateAt(Utc, seed));
            Assert.AreEqual(GardenResult.NotReady, g.Harvest(0, Utc.AddHours(5), d.Item, inv, out _), "sulanmadan büyümez");
            g.Water(0, Utc);
            Assert.AreEqual(GardenResult.NotReady, g.Harvest(0, Utc.AddMinutes(10), d.Item, inv, out _));
            Assert.AreEqual(GardenResult.Ok, g.Harvest(0, Utc.AddMinutes(31), d.Item, inv, out var produce));
            Assert.AreEqual("food_carrot", produce.Id);
            Assert.AreEqual(2, inv.CountOf("food_carrot"));
            Assert.AreEqual(6, GardenState.PlotCountFor(15));
        }

        [Test]
        public void Fishing_timing_window_by_band_and_species_by_level_and_time()
        {
            var d = TestData.Load();
            var rng = new Random(5);
            var a = new FishingRound(rng, AgeBand.A, 7, false, d.Collection);
            var c = new FishingRound(rng, AgeBand.C, 7, false, d.Collection);
            Assert.Greater(a.WindowMs, c.WindowMs, "küçükler için daha geniş pencere");
            Assert.AreEqual(CatchResult.TooEarly, a.Resolve(a.BiteAtMs - 1));
            Assert.AreEqual(CatchResult.Caught, a.Resolve(a.BiteAtMs + a.WindowMs));
            Assert.AreEqual(CatchResult.TooLate, a.Resolve(a.BiteAtMs + a.WindowMs + 1));
            for (var i = 0; i < 300; i++)
            {
                var f = FishingRound.Pick(rng, 7, false, d.Collection);
                Assert.LessOrEqual(f.Level, 7);
                Assert.AreNotEqual("night", f.Time);
            }
        }

        [Test]
        public void Collection_counts_species_once()
        {
            var d = TestData.Load();
            var owned = new HashSet<string>();
            var c = new Counters();
            var fish = d.Collection.First(e => e.Category == "fish");
            Assert.IsTrue(CollectionBook.Discover(owned, fish, c));
            Assert.IsFalse(CollectionBook.Discover(owned, fish, c));
            Assert.AreEqual(1, c.Total("fish_species"));
            Assert.AreEqual((1, 8), CollectionBook.Completion(d.Collection, owned, "fish"));
        }
    }
}
