using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Progression;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    public class LevelGiftsTests
    {
        [Test]
        public void Her_hediye_veride_var_ve_coin_ya_da_tas_degil()
        {
            var data = TestData.Load();
            for (var lv = 1; lv <= 15; lv++)
            {
                var id = LevelGifts.For(lv);
                if (id == null) continue;
                var it = data.Item(id);
                Assert.IsNotNull(it, id);
                Assert.That(it.Category == "decor" || it.Category == "home", id);
            }
        }

        [Test]
        public void Atlanan_seviyelerin_hediyesi_bir_kez_verilir()
        {
            var data = TestData.Load();
            var s = new GameState();
            var got = LevelGifts.Claim(s, data, new LevelUp { From = 1, To = 3 });
            Assert.AreEqual(new[] { "decor_sandcastle", "decor_umbrella" }, got.Select(i => i.Id).ToArray());
            Assert.IsTrue(s.Inventory.Owns("decor_sandcastle"));
            var again = LevelGifts.Claim(s, data, new LevelUp { From = 2, To = 3 });
            Assert.IsEmpty(again);
        }

        [Test]
        public void Sahip_olunan_esya_yerine_baska_esya_gelir()
        {
            var data = TestData.Load();
            var s = new GameState();
            s.Inventory.Add(data.Item("home_rug"));
            var got = LevelGifts.Claim(s, data, new LevelUp { From = 3, To = 4 });
            Assert.AreEqual(1, got.Count);
            Assert.AreNotEqual("home_rug", got[0].Id);
            Assert.That(got[0].IsPlaceable && got[0].Level <= 4);
        }

        [Test]
        public void Hediyesiz_seviye_bos_doner_ama_isaretlenir()
        {
            var s = new GameState();
            var got = LevelGifts.Claim(s, TestData.Load(), new LevelUp { From = 8, To = 9 });
            Assert.IsEmpty(got);
            Assert.IsTrue(s.GiftedLevels.Contains(9));
        }
    }
}
