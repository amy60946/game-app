using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Economy;
using Pofi.Logic.Island;
using Pofi.Logic.Profile;
using Pofi.Logic.Progression;
using Pofi.Logic.State;
using Pofi.Logic.Data;

namespace Pofi.Tests.Logic
{
    public class IslandTests
    {
        private static LevelTable Levels => new LevelTable(TestData.Load().Levels);
        private static IslandMap Map => new IslandMap(TestData.ReadText("regions.json"), Levels);

        [Test]
        public void Her_bolge_seviye_tablosunda_ve_tablodaki_her_bolge_haritada()
        {
            var map = Map;
            foreach (var r in map.Regions) Assert.Greater(Levels.UnlockLevel(r.Id), 0, r.Id);
            var inTable = Enumerable.Range(1, 15).SelectMany(l => Levels.UnlocksAt(l)).Where(id => id.StartsWith("region_"));
            foreach (var id in inTable) Assert.IsNotNull(map.Find(id), id);
            Assert.AreEqual(map.Regions.Count, map.Regions.Select(r => r.Id).Distinct().Count());
        }

        [Test]
        public void Bolgeler_birbirine_cok_yakin_degil()
        {
            var rs = Map.Regions;
            for (var i = 0; i < rs.Count; i++)
            for (var j = i + 1; j < rs.Count; j++)
            {
                var d = Math.Sqrt(Math.Pow(rs[i].X - rs[j].X, 2) + Math.Pow(rs[i].Z - rs[j].Z, 2));
                Assert.Greater(d, (rs[i].Size + rs[j].Size) / 2f + 2.5f, rs[i].Id + " – " + rs[j].Id);   // aralarından yürünebilsin
            }
        }

        [Test]
        public void Kilit_yeni_isareti_ve_siradaki()
        {
            var map = Map;
            var visited = new HashSet<string>();
            var v1 = map.View(1, visited);
            Assert.IsTrue(v1.First(v => v.Region.Id == "region_home").Unlocked);
            Assert.IsFalse(v1.First(v => v.Region.Id == "region_home").IsNew);   // başlangıç bölgeleri "yeni" sayılmaz
            Assert.IsFalse(v1.First(v => v.Region.Id == "region_swim_cove").Unlocked);
            Assert.IsTrue(map.View(2, visited).First(v => v.Region.Id == "region_swim_cove").OnHold, "mini oyun beklemede (kullanıcı, 24 Ekim 2026)");
            Assert.IsFalse(map.View(2, visited).First(v => v.Region.Id == "region_swim_cove").Unlocked);
            // beklemedeki bölgeler (Sv2 koy, Sv3 sörf) sıradaki hedef olmaz; Oyun Kulübesi (Sv3) Piramit Koşusu'yla açık (25 Ekim 2026)
            Assert.AreEqual("region_game_hut", map.NextToUnlock(1, visited).Region.Id, "beklemedeki bölgeler sıradaki hedef olmaz");
            var v6 = map.View(6, visited);
            Assert.IsTrue(v6.First(v => v.Region.Id == "region_garden").IsNew);
            visited.Add("region_garden");
            Assert.IsFalse(map.View(6, visited).First(v => v.Region.Id == "region_garden").IsNew);
        }

        [Test]
        public void Beklemedeki_oyunlar_seviye_kutlamasinda_listelenmez()
        {
            var up = new Pofi.Logic.Progression.LevelUp { From = 2, To = 3 };
            up.Unlocked.AddRange(new[] { "region_surf_beach", "minigame_surf", "region_game_hut", "minigame_runner", "card_color_match", "shop_hats", "minigame_coconut" });
            GameHold.FilterLevelUp(up, Map);
            // Oyun Kulübesi artık Piramit Koşusu'nu açar (25 Ekim 2026); kart oyunları beklemede
            CollectionAssert.AreEquivalent(new[] { "shop_hats", "minigame_coconut", "region_game_hut", "minigame_runner" }, up.Unlocked);
        }

        [Test]
        public void Hedef_turleri()
        {
            Assert.AreEqual(RegionTargetKind.Page, IslandMap.KindOf("page:shop", out var a)); Assert.AreEqual("shop", a);
            Assert.AreEqual(RegionTargetKind.MiniGame, IslandMap.KindOf("minigame:surf", out a)); Assert.AreEqual("surf", a);
            Assert.AreEqual(RegionTargetKind.Cards, IslandMap.KindOf("cards", out _));
            Assert.AreEqual(RegionTargetKind.Soon, IslandMap.KindOf("soon", out _));
            Assert.AreEqual(RegionTargetKind.Soon, IslandMap.KindOf(null, out _));
        }

        [Test]
        public void Xp_seviye_atlatir_gunluk_sinir_banda_gore()
        {
            var local = new DateTime(2026, 10, 14, 10, 0, 0);
            var s = GameState.NewFor("c", DateTime.UtcNow);
            var r = Progress.Grant(s, Levels, AgeBand.A, 120, XpSource.MiniGame, local);
            Assert.AreEqual(120, r.Grant.Granted);
            Assert.IsNotNull(r.LevelUp);
            Assert.AreEqual(2, r.LevelUp.To);
            CollectionAssert.Contains(r.LevelUp.Unlocked, "region_swim_cove");
            var big = Progress.Grant(s, Levels, AgeBand.A, 1000, XpSource.MiniGame, local);
            Assert.AreEqual(250 - 120, big.Grant.Granted);   // A bandı günlük 250
            Assert.IsTrue(big.Grant.CapReached);
            Progress.MarkCelebrated(s, r.LevelUp);
            Assert.IsTrue(s.SeenUnlocks.Contains("region_swim_cove"));
        }

        [Test]
        public void Her_acilisin_turkce_adi_var()
        {
            var loc = new Localization(TestData.ReadText("tr.json"));
            foreach (var id in Enumerable.Range(1, 15).SelectMany(l => Levels.UnlocksAt(l)))
                Assert.IsTrue(loc.Has("unlock." + id), id);
        }
    }
}

namespace Pofi.Tests.Logic
{
    public class ActivityTests
    {
        [Test]
        public void Besleme_sayaci_gunluk_gorev_ve_rozet()
        {
            var data = TestData.Load();
            var levels = new LevelTable(data.Levels);
            var local = new DateTime(2026, 10, 14, 10, 0, 0);
            var s = GameState.NewFor("child_a", DateTime.UtcNow);
            Activity.EnsureQuests(s, data, levels, local);
            Assert.AreEqual(data.DailyQuestsPerDay, s.DailyQuests.Ids.Count);
            foreach (var id in s.DailyQuests.Ids)
                Assert.IsTrue(levels.IsUnlocked(data.DailyQuests.First(q => q.Id == id).Unlock, 1), id);

            var gotQuest = false;
            var gotBadge = false;
            foreach (var counter in new[] { "pet_fed", "pet_washed", "pet_played", "home_tidied", "coconuts_caught", "pets_helped" })
                for (var i = 0; i < 30; i++)
                {
                    var r = Activity.Record(s, data, levels, counter, 1, local);
                    gotQuest |= r.QuestsDone.Count > 0 && r.QuestXp > 0;
                    gotBadge |= r.NewBadges.Count > 0;
                }
            Assert.IsTrue(gotQuest, "en az bir günlük görev tamamlanmalı");
            Assert.IsTrue(gotBadge, "en az bir rozet kazanılmalı");
            var again = Activity.Record(s, data, levels, "pet_fed", 1, local);
            Assert.AreEqual(0, again.QuestXp);   // aynı görev iki kez ödül vermez
        }
    }
}

namespace Pofi.Tests.Logic
{
    public class CardSessionTests
    {
        [Test]
        public void Zorluk_bantan_baslar_uyarlanir_ve_kayitta_kalir()
        {
            var s = GameState.NewFor("c", DateTime.UtcNow);
            var d = CardSession.Difficulty(s, "card_domino", AgeBand.A);
            Assert.AreEqual(AgeBandProfile.For(AgeBand.A).MiniGameDifficulty, d.Level, 1e-4);
            Assert.AreEqual(8, CardSession.Finish(s, "card_domino", AgeBand.A, false));
            CardSession.Finish(s, "card_domino", AgeBand.A, false);
            Assert.Less(CardSession.Difficulty(s, "card_domino", AgeBand.A).Level, d.Level + 1e-4f);
            Assert.Greater(CardSession.Finish(s, "card_domino", AgeBand.A, true), 8);

            var back = SaveCodec.Deserialize(SaveCodec.Serialize(s, DateTime.UtcNow));
            Assert.AreEqual(s.CardDifficulty["card_domino"].Level, back.CardDifficulty["card_domino"].Level, 1e-4);
            var levels = new LevelTable(TestData.Load().Levels);
            foreach (var g in CardSession.Games) Assert.Greater(levels.UnlockLevel(g), 0, g);
        }
    }
}

namespace Pofi.Tests.Logic
{
    public class SparkleTests
    {
        [Test]
        public void Gunluk_parilti_deterministik_uygun_ve_alininca_kaybolur()
        {
            var data = TestData.Load();
            var terrain = TestData.Terrain();
            var a = Sparkles.ForDay(20000, "child_a", 8, false, data.Collection, terrain);
            var b = Sparkles.ForDay(20000, "child_a", 8, false, data.Collection, terrain);
            Assert.AreEqual(Sparkles.PerDay, a.Count);
            foreach (var s in a) Assert.IsTrue(terrain.Walkable(s.X, s.Z), "parıltıya yürünebilmeli");
            CollectionAssert.AreEqual(a.Select(s => s.EntryId), b.Select(s => s.EntryId));
            foreach (var s in a)
            {
                var e = data.Collection.First(x => x.Id == s.EntryId);
                Assert.AreNotEqual("fish", e.Category);
                Assert.AreNotEqual("night", e.Time);
                Assert.LessOrEqual(e.Level, 8);
            }
            var st = new SparkleState();
            Assert.AreEqual(3, Sparkles.Open(st, 20000, a).Count);
            Sparkles.Take(st, 20000, a[1]);
            Assert.AreEqual(2, Sparkles.Open(st, 20000, a).Count);
            Assert.AreEqual(3, Sparkles.Open(st, 20001, a).Count);   // ertesi gün yenilenir
        }
    }
}

namespace Pofi.Tests.Logic
{
    public class PetChangeTests
    {
        [Test]
        public void Pet_degisince_envanter_kalir_uymayan_cikarilir()
        {
            var data = TestData.Load();
            var s = GameState.NewFor("c", DateTime.UtcNow);
            PetChange.Choose(s, "pet_01", data);
            var cape = data.Item("cape_hero");
            s.Inventory.Add(cape);
            Assert.IsTrue(s.Inventory.TryEquip(data.Pet("pet_01"), cape).Allowed);
            s.Wallet.ServerCoins = 40;

            PetChange.Begin(s);
            Assert.AreEqual(Pofi.Logic.App.AppScreen.PetSelect, AppFlow.Decide(new Pofi.Logic.Services.ChildSession("c", "x", AgeBand.B, null), s));
            var removed = PetChange.Choose(s, "pet_12", data);    // Benli: sırta eşya takılmaz
            CollectionAssert.Contains(removed, "cape_hero");
            Assert.IsTrue(s.Inventory.Owns("cape_hero"));
            Assert.AreEqual(40, s.Wallet.Available);
            Assert.AreEqual("Okti", s.PetName);   // ad sorulmaz (24 Ekim 2026)
        }
    }
}

namespace Pofi.Tests.Logic
{
    public class HomeLayoutTests
    {
        [Test]
        public void Yerlestir_tasi_kaldir_etki_bir_kez()
        {
            var data = TestData.Load();
            var s = GameState.NewFor("c", DateTime.UtcNow);
            var rug = data.Item("home_rug");
            var lamp = data.Item("home_lamp");
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.NotOwned, Pofi.Logic.Home.HomeLayout.Place(s, rug, 0, 0, false));
            s.Inventory.Add(rug); s.Inventory.Add(lamp);
            s.Stats.Values[(int)Pofi.Logic.Pet.StatKind.Home] = 50f;
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.Ok, Pofi.Logic.Home.HomeLayout.Place(s, rug, 0, 0, false));
            var after = s.Stats[Pofi.Logic.Pet.StatKind.Home];
            Assert.GreaterOrEqual(after, 50f);
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.AlreadyPlaced, Pofi.Logic.Home.HomeLayout.Place(s, rug, 3, 3, false));
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.Occupied, Pofi.Logic.Home.HomeLayout.Place(s, lamp, 0, 0, false));
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.OutOfBounds, Pofi.Logic.Home.HomeLayout.Place(s, lamp, 4, 0, false));
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.OutOfBounds, Pofi.Logic.Home.HomeLayout.Place(s, lamp, 1, 1, false)); // pet yeri
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.Ok, Pofi.Logic.Home.HomeLayout.Place(s, lamp, 4, 0, true));       // genişleyince sığar
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.Ok, Pofi.Logic.Home.HomeLayout.Move(s, "home_rug", 3, 3, false));
            Assert.AreEqual(Pofi.Logic.Home.PlaceResult.Ok, Pofi.Logic.Home.HomeLayout.Remove(s, "home_rug"));
            CollectionAssert.Contains(Pofi.Logic.Home.HomeLayout.Unplaced(s, data).Select(i => i.Id).ToList(), "home_rug");
            s.Stats.Values[(int)Pofi.Logic.Pet.StatKind.Home] = 50f;
            Pofi.Logic.Home.HomeLayout.Place(s, rug, 0, 0, false);
            Assert.AreEqual(50f, s.Stats[Pofi.Logic.Pet.StatKind.Home], 1e-3);   // etki ikinci kez yok

            var back = SaveCodec.Deserialize(SaveCodec.Serialize(s, DateTime.UtcNow));
            Assert.AreEqual(2, back.Home.Count);
            Assert.IsTrue(back.HomeEffectsApplied.Contains("home_rug"));
        }
    }
}
