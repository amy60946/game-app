using NUnit.Framework;
using Pofi.Logic.Progression;

namespace Pofi.Tests.Logic
{
    public class ProgressionTests
    {
        private LevelTable T => new LevelTable(TestData.Load().Levels);

        [Test]
        public void Xp_thresholds_map_to_levels()
        {
            Assert.AreEqual(1, T.LevelFor(0));
            Assert.AreEqual(1, T.LevelFor(99));
            Assert.AreEqual(2, T.LevelFor(100));
            Assert.AreEqual(3, T.LevelFor(235));
            Assert.AreEqual(15, T.LevelFor(1_000_000));
            Assert.AreEqual(0.5f, T.ProgressInLevel(50), 0.001f);
        }

        [Test]
        public void Unlock_gate_follows_table()
        {
            Assert.IsTrue(T.IsUnlocked("region_shop", 1));
            Assert.IsFalse(T.IsUnlocked("card_color_match", 2));
            Assert.IsTrue(T.IsUnlocked("card_color_match", 3));
            Assert.IsFalse(T.IsUnlocked("region_lighthouse", 14));
            Assert.IsTrue(T.IsUnlocked("region_lighthouse", 15));
            Assert.IsFalse(T.IsUnlocked("bilinmeyen_icerik", 15), "tabloda olmayan kimlik kilitli kalmalı");
            Assert.AreEqual(7, T.UnlockLevel("minigame_fishing"));
        }

        [Test]
        public void Level_up_lists_all_new_unlocks_and_stage_change()
        {
            var up = T.Check(T.TotalXpFor(4) + 10, T.TotalXpFor(6));
            Assert.AreEqual(4, up.From);
            Assert.AreEqual(6, up.To);
            CollectionAssert.Contains(up.Unlocked, "card_tower");   // Sv5
            CollectionAssert.Contains(up.Unlocked, "region_garden"); // Sv6
            Assert.AreEqual(GrowthStage.Genc, up.NewStage);
            Assert.IsNull(T.Check(10, 20));
        }

        [Test]
        public void Growth_stages()
        {
            Assert.AreEqual(GrowthStage.Yavru, T.StageFor(4));
            Assert.AreEqual(GrowthStage.Genc, T.StageFor(5));
            Assert.AreEqual(GrowthStage.Yetiskin, T.StageFor(10));
        }

        [Test]
        public void Seviye_esikleri_yas_grubuna_gore()
        {
            var d = TestData.Load();
            var b = new LevelTable(d.Levels);
            Assert.AreEqual(100, b.TotalXpFor(2), "genel tablo = B");
            Assert.AreEqual(18791, b.TotalXpFor(15));
            var k = new LevelTable(d.Levels, Pofi.Logic.Profile.AgeBand.K);
            Assert.AreEqual(70, k.TotalXpFor(2));
            Assert.AreEqual(13140, k.TotalXpFor(15), "5 ve altı toplam");
            Assert.AreEqual(85, new LevelTable(d.Levels, Pofi.Logic.Profile.AgeBand.A).TotalXpFor(2));
            Assert.AreEqual(18791, new LevelTable(d.Levels, Pofi.Logic.Profile.AgeBand.B).TotalXpFor(15), "B bugünküyle aynı");
            var c = new LevelTable(d.Levels, Pofi.Logic.Profile.AgeBand.C);
            Assert.AreEqual(21610, c.TotalXpFor(15), "13 ve üstü toplam");
            Assert.AreEqual(1, c.LevelFor(114));
            Assert.AreEqual(2, k.LevelFor(114));
            k.UseBand(null);
            Assert.AreEqual(100, k.TotalXpFor(2), "grup kaldırılınca genel tablo");
            Assert.AreEqual(b.UnlockLevel("region_garden"), c.UnlockLevel("region_garden"), "açılış seviyeleri gruptan bağımsız");
            Assert.AreEqual(Pofi.Logic.Profile.AgeBand.K, Pofi.Logic.Profile.AgeBandProfile.Parse("K"));
            Assert.AreEqual(200, Pofi.Logic.Profile.AgeBandProfile.For(Pofi.Logic.Profile.AgeBand.K).DailyXpCap);
            Assert.IsTrue(Pofi.Logic.Profile.AgeBands.Young(Pofi.Logic.Profile.AgeBand.K));
            Assert.IsFalse(Pofi.Logic.Profile.AgeBands.Young(Pofi.Logic.Profile.AgeBand.C));
        }
    }
}
