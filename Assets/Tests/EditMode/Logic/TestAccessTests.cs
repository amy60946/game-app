using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Progression;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Shop;

namespace Pofi.Tests.Logic
{
    public class TestAccessTests
    {
        [Test]
        public void Test_erisimi_en_ust_seviye_ve_tum_esyalar()
        {
            var data = TestData.Load();
            var levels = new LevelTable(data.Levels);
            var xp = TestAccess.XpToMax(levels, 0);
            Assert.AreEqual(levels.MaxLevel, levels.LevelFor(xp));
            Assert.AreEqual(0, TestAccess.XpToMax(levels, xp));

            var inv = new Inventory();
            Assert.AreEqual(data.Items.Count, TestAccess.GiveAllItems(data, inv));
            Assert.IsTrue(data.Items.All(i => inv.Owns(i.Id)));
            Assert.AreEqual(0, TestAccess.GiveAllItems(data, inv), "ikinci kez bir şey eklemez");

            var backend = new MockBackend(data);
            backend.TestGrantCoins(TestAccess.Coins);
            Assert.AreEqual(TestAccess.Coins, backend.Coins);
        }
    }
}
