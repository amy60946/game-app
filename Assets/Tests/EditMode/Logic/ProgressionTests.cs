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
    
        [Test]
        public void Seviye_yas_grubu_buyuyunce_dusmez()
        {
            // 23 Ekim 2026 (ortak 20261023040000): K'de 170 XP Sv3; 6. doğum gününde grup A olur, aynı XP A tablosunda Sv2.
            var d = TestData.Load();
            var t = new LevelTable(d.Levels, Pofi.Logic.Profile.AgeBand.K);
            var xp = new Pofi.Logic.Economy.XpSystem { TotalXp = 170 };
            t.Remember(xp);
            Assert.AreEqual(3, t.Level(xp));
            t.UseBand(Pofi.Logic.Profile.AgeBand.A);
            Assert.AreEqual(2, t.LevelFor(170), "A tablosunda 170 XP Sv2");
            Assert.AreEqual(3, t.Level(xp), "ulaşılan seviye korunur");
            // A'da Sv3 eşiğine (200) ulaşınca ikinci kez kutlama yok; Sv4'te (A: 355) kutlama var
            var before = xp.TotalXp; xp.TotalXp = 210;
            Assert.IsNull(t.Check(xp, before), "Sv3 zaten kutlandı");
            before = xp.TotalXp; xp.TotalXp = 360;
            var up = t.Check(xp, before);
            Assert.IsNotNull(up); Assert.AreEqual(3, up.From); Assert.AreEqual(4, up.To);
            Assert.AreEqual(4, xp.BestLevel);
            // eski kayıt (en yüksek seviye yok) bugünkü seviyeyle başlar
            var old = new Pofi.Logic.Economy.XpSystem { TotalXp = 120 };
            Assert.AreEqual(t.LevelFor(120), t.Level(old));
        }
}
}
