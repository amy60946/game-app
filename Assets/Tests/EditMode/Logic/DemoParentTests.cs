using System;
using System.Linq;
using System.Threading.Tasks;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Shop;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    public class DemoParentTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 14, 10, 0, 0);
        private static readonly DateTime Utc = new DateTime(2026, 10, 14, 7, 0, 0, DateTimeKind.Utc);

        [Test]
        public async Task Gorev_onayi_coin_olur_ve_dukkanda_harcanir()
        {
            var data = TestData.Load();
            var backend = new MockBackend(data);
            var sync = new SyncCoordinator(backend, backend, backend, data);
            var st = GameState.NewFor("child_a", Utc);

            Assert.AreEqual(DemoParent.Samples.Length, DemoParent.EnsureToday(backend, Local));
            Assert.AreEqual(0, DemoParent.EnsureToday(backend, Local));   // ikinci kez atamaz
            await sync.SyncAsync(st, Local, Utc);
            Assert.AreEqual(DemoParent.Samples.Length, st.Tasks.Tasks.Count);

            foreach (var id in new[] { "demo_room", "demo_teeth" })
                Assert.AreEqual(ChangeResult.Ok, st.Tasks.Mark(st.Tasks.Tasks.First(t => t.TaskId == id).Key, ChildTaskStatus.ChildDone, Local, Utc));
            await sync.SyncAsync(st, Local, Utc);
            Assert.AreEqual(2, DemoParent.Pending(backend));
            Assert.AreEqual(0, st.Wallet.Available);              // onaysız coin yok

            Assert.AreEqual(2, DemoParent.ApproveAll(backend));
            var report = await sync.SyncAsync(st, Local, Utc);
            Assert.AreEqual(15, report.CoinsEarned);
            Assert.AreEqual(15, st.Wallet.Available);

            var hat = data.Item("glasses_round");   // Sv1 giyilebilir, 15 coin
            var pet = data.Pet("pet_01");
            var r = ShopRules.Buy(hat, 1, 1, st.Wallet, st.Inventory, pet, "tx1", Utc, out _);
            Assert.AreEqual(BuyCheck.Ok, r, hat.Id);
            await sync.SyncAsync(st, Local, Utc);
            Assert.AreEqual(15 - hat.Price, backend.Coins);
            Assert.AreEqual(15 - hat.Price, st.Wallet.Available);
            Assert.IsTrue(st.Inventory.TryEquip(pet, hat).Allowed);
        }

        [Test]
        public void Sahte_sunucu_disari_aktarilip_geri_yuklenir()
        {
            var data = TestData.Load();
            var a = new MockBackend(data);
            DemoParent.EnsureToday(a, Local);
            var b = new MockBackend(data);
            b.Import(a.Export());
            Assert.AreEqual(a.AllTasks.Count, b.AllTasks.Count);
            b.Import("bozuk{");                                   // bozuk veri: değişmez
            Assert.AreEqual(a.AllTasks.Count, b.AllTasks.Count);
        }
    }
}
