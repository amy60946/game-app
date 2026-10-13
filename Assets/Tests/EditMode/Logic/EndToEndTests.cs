using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Economy;
using Pofi.Logic.Pet;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Shop;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    /// <summary>Kabul ölçütleri 2 ve 6: görev → onay → coin → yiyecek → gösterge; çevrimdışı işlemler senkronlanır; kayıt korunur.</summary>
    public class EndToEndTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 13, 17, 0, 0);
        private static readonly DateTime Utc = new DateTime(2026, 10, 13, 14, 0, 0, DateTimeKind.Utc);

        [Test]
        public void Real_task_to_coins_to_food_to_happy_pet_with_offline_period()
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            var sync = new SyncCoordinator(server, server, server, data);
            var s = GameState.NewFor("child_a", Utc);
            s.PetId = "pet_01"; s.PetName = "Turunç";

            // Ebeveyn görev atar; çocuk oyunu açar
            server.ParentAssign("t_bed", "2026-10-13", "Yatağını topla", 10);
            var r1 = sync.SyncAsync(s, Local, Utc).Result;
            Assert.AreEqual(TaskEventKind.NewTask, r1.TaskEvents.Single().Kind);
            Assert.AreEqual(0, s.Wallet.Available, "oyun içi hiçbir eylem coin vermez");

            // Çevrimdışıyken "Yaptım"
            server.Offline = true;
            Assert.AreEqual(ChangeResult.Ok, s.Tasks.Mark("t_bed|2026-10-13", ChildTaskStatus.ChildDone, Local, Utc));
            Assert.IsTrue(sync.SyncAsync(s, Local, Utc).Result.Offline);
            Assert.AreEqual(1, s.Tasks.Outbox.Count, "niyet kuyrukta bekler");

            // Uygulama kapanıp açılır (kayıt korunur)
            s = SaveCodec.Deserialize(SaveCodec.Serialize(s, Utc));
            Assert.AreEqual(ChildTaskStatus.ChildDone, s.Tasks.Find("t_bed|2026-10-13").Status);

            // Ağ geldi → niyet gönderildi; ebeveyn onayladı → sonraki senkronda coin
            server.Offline = false;
            sync.SyncAsync(s, Local, Utc).Wait();
            server.ParentApprove("t_bed|2026-10-13", "Aferin!");
            var r2 = sync.SyncAsync(s, Local, Utc).Result;
            Assert.AreEqual(TaskEventKind.Approved, r2.TaskEvents.Single().Kind);
            Assert.AreEqual(10, r2.CoinsEarned);
            Assert.AreEqual(10, r2.StreakBonusXp, "seri bonusu XP'dir, coin değil");
            Assert.AreEqual(10, s.Wallet.Available);

            // Coin ile yiyecek al (çevrimdışı), pet'i besle
            server.Offline = true;
            var pet = data.Pet(s.PetId);
            Assert.AreEqual(BuyCheck.Ok, ShopRules.Buy(data.Item("food_apple"), 2, 1, s.Wallet, s.Inventory, pet, "tx-1", Utc, out _));
            s.Stats.Add(StatKind.Fullness, -50f);
            var before = s.Stats[StatKind.Fullness];
            Assert.AreEqual(CareResult.Ok, PetCare.Feed(s.Stats, s.Inventory, data.Item("food_apple"), Local));
            Assert.Greater(s.Stats[StatKind.Fullness], before);
            Assert.AreEqual(4, s.Wallet.Available, "bekleyen harcama gösterilir");

            // Ağ geldi → harcama sunucuda kesinleşir
            server.Offline = false;
            sync.SyncAsync(s, Local, Utc).Wait();
            Assert.AreEqual(4, server.Coins);
            Assert.AreEqual(4, s.Wallet.ServerCoins);
            Assert.IsEmpty(s.Wallet.Pending);
        }

        [Test]
        public void Server_rejects_spend_and_inventory_is_rolled_back()
        {
            var data = TestData.Load();
            var server = new MockBackend(data, startCoins: 5);
            var sync = new SyncCoordinator(server, server, server, data);
            var s = GameState.NewFor("c", Utc);
            s.PetId = "pet_01"; s.PetName = "Pofi";
            sync.SyncAsync(s, Local, Utc).Wait();
            server.Offline = true;
            ShopRules.Buy(data.Item("food_watermelon"), 1, 3, s.Wallet, s.Inventory, data.Pet("pet_01"), "tx-a", Utc, out _);
            // Başka bir cihazdan harcama yapıldı; sunucuda bakiye düştü (simülasyon)
            server.Offline = false;
            server.SpendAsync("other-device", "food_apple", 1).Wait();
            var r = sync.SyncAsync(s, Local, Utc).Result;
            Assert.AreEqual("food_watermelon", r.RejectedSpends.Single().ItemId);
            Assert.AreEqual(0, s.Inventory.CountOf("food_watermelon"));
            Assert.AreEqual(2, s.Wallet.Available);
        }

        [Test]
        public void Corrupt_or_future_save_returns_null_instead_of_crashing()
        {
            Assert.IsNull(SaveCodec.Deserialize("{bozuk"));
            Assert.IsNull(SaveCodec.Deserialize("{\"Schema\":99}"));
            Assert.IsNull(SaveCodec.Deserialize(""));
        }
    }
}
