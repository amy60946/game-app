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
            Assert.IsFalse(T.IsUnlocked("card_uno", 2));
            Assert.IsTrue(T.IsUnlocked("card_uno", 3));
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
            CollectionAssert.Contains(up.Unlocked, "card_jenga");   // Sv5
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
    }
}
