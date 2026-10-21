using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Rewards;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Services.Supabase;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    /// <summary>Ö7 gerçek ödül dükkânı: istek → coin ayrılır → ebeveyn verir/bekletir (ortak/sozlesme/akislar.md 10).</summary>
    public class RewardShopTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 22, 17, 0, 0);
        private static readonly DateTime Utc = new DateTime(2026, 10, 22, 14, 0, 0, DateTimeKind.Utc);

        private static (MockBackend server, SyncCoordinator sync, GameState s) Setup(int coins)
        {
            var data = TestData.Load();
            var server = new MockBackend(data, coins);
            DemoParent.EnsureRewards(server);
            var sync = new SyncCoordinator(server, server, server, data, server);
            var s = GameState.NewFor("child_a", Utc);
            s.PetId = "pet_13"; s.PetName = "Okti";
            return (server, sync, s);
        }

        [Test]
        public async Task Istek_coini_ayirir_verilince_duser_ve_olay_gelir()
        {
            var (server, sync, s) = Setup(50);
            await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(DemoParent.SampleRewards.Length, s.Rewards.Rewards.Count);
            Assert.AreEqual(50, s.Wallet.Available);

            Assert.IsTrue((await server.RequestAsync("demo_park", "tx-park-0001")).Ok);
            Assert.IsTrue((await server.RequestAsync("demo_park", "tx-park-0001")).Ok, "aynı işlem kimliği tekrar: aynı sonuç");
            await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(20, s.Wallet.Held);
            Assert.AreEqual(30, s.Wallet.Available, "ayrılan coin eşya dükkânında harcanamaz");
            Assert.AreEqual(1, s.Rewards.Pending.Count());
            Assert.IsNotNull(s.Rewards.PendingFor("demo_park"));

            Assert.AreEqual(1, DemoParent.GiveRewards(server));
            var r = await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(RewardEventKind.Given, r.RewardEvents.Single().Kind);
            Assert.AreEqual(30, s.Wallet.ServerCoins);
            Assert.AreEqual(0, s.Wallet.Held);
            Assert.AreEqual(0, r.CoinsEarned, "ödül düşüşü kazanç sayılmaz");
            Assert.AreEqual(0, (await sync.SyncAsync(s, Local, Utc)).RewardEvents.Count, "olay bir kez");
        }

        [Test]
        public async Task Bekletme_coini_birakir_ve_sinirlar()
        {
            var (server, sync, s) = Setup(200);
            Assert.IsTrue((await server.RequestAsync("demo_book", "tx-book-0001")).Ok);
            Assert.IsTrue((await server.RequestAsync("demo_park", "tx-a-000001")).Ok);
            Assert.IsTrue((await server.RequestAsync("demo_treat", "tx-b-000001")).Ok);
            Assert.AreEqual("too_many_pending", (await server.RequestAsync("demo_movie", "tx-c-000001")).Error, "en çok 3 bekleyen (kitap + park + dondurma)");
            Assert.AreEqual("unknown_reward", (await server.RequestAsync("yok", "tx-d-000001")).Error);
            Assert.AreEqual("rejected", (await server.RequestAsync("demo_park", "kisa")).Error);

            await sync.SyncAsync(s, Local, Utc);
            var park = s.Rewards.PendingFor("demo_park");
            Assert.IsTrue(server.ParentDecideReward(park.Id, false));
            var r = await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(RewardEventKind.Declined, r.RewardEvents.Single().Kind);
            Assert.AreEqual(200, s.Wallet.ServerCoins, "bekletilen ödülde coin kalır");

            var treat = s.Rewards.PendingFor("demo_treat");
            Assert.IsTrue((await server.CancelAsync(treat.Id)).Ok);
            Assert.AreEqual("already_decided", (await server.CancelAsync(treat.Id)).Error);
            await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(80, s.Wallet.Held, "yalnız kitap bekliyor");
        }

        [Test]
        public async Task Bakiye_yetmezse_ebeveyn_veremez_istek_bekler()
        {
            var (server, sync, s) = Setup(40);
            Assert.IsTrue((await server.RequestAsync("demo_movie", "tx-movie-001")).Ok);
            Assert.AreEqual("not_enough_coins", (await server.RequestAsync("demo_park", "tx-park-0002")).Error, "ayrılan coin yeni isteğe yetmez");
            await sync.SyncAsync(s, Local, Utc);
            // çocuk eski sürümden eşya almış gibi: sunucu bakiyesi düşer
            await server.SpendAsync("tx-spend-1", TestData.Load().Items.First(i => i.Price > 0 && i.Price <= 40).Id, 1);
            Assert.AreEqual(0, DemoParent.GiveRewards(server));
            Assert.AreEqual(RewardStatus.Pending, server.RewardRequests.Single().Status);
        }

        [Test]
        public void Ayrilan_coin_harcanabilir_bakiyeden_duser()
        {
            var w = new Wallet { ServerCoins = 50, Held = 30 };
            Assert.AreEqual(20, w.Available);
            Assert.AreEqual(SpendResult.NotEnoughCoins, w.TrySpend("food_apple", 1, 25, "tx1", Utc, out _));
            Assert.AreEqual(SpendResult.Ok, w.TrySpend("food_apple", 1, 20, "tx2", Utc, out _));
        }

        [Test]
        public void Sunucu_yaniti_okunur()
        {
            var snap = SupabaseGameService.ParseRewards(@"{""balance"":70,""held"":20,""available"":50,
              ""rewards"":[{""id"":""r1"",""title"":""Parka gitmek"",""icon"":""park"",""price"":20}],
              ""requests"":[{""id"":""q1"",""reward_id"":""r1"",""title"":""Parka gitmek"",""icon"":""park"",""price"":20,""status"":""pending"",""requested_at"":""2026-10-22T10:00:00Z"",""decided_at"":null}]}");
            Assert.AreEqual(20, snap.Held);
            Assert.AreEqual("r1", snap.Requests.Single().RewardId);
            var book = new RewardBook();
            Assert.AreEqual(0, book.Apply(snap).Count, "ilk görüşte olay yok");
            Assert.IsFalse(book.Apply(null) == null);
            Assert.AreEqual(0, SupabaseGameService.ParseRewards("null").Rewards.Count);
        }

        // ---------------------------------------------------------------- güvenlik denetimi M1/M2

        private sealed class AuthFailWallet : IWalletService
        {
            public ServiceError SpendError = ServiceError.Unauthorized;
            public Task<int> GetBalanceAsync(CancellationToken ct = default) => Task.FromResult(100);
            public Task<BalanceSnapshot> GetBalancesAsync(CancellationToken ct = default) => Task.FromResult(new BalanceSnapshot { Coins = 100 });
            public Task<SpendResponse> SpendAsync(string txId, string itemId, int quantity, CancellationToken ct = default) =>
                Task.FromResult(new SpendResponse { Error = SpendError, Balance = -1 });
        }

        [Test]
        public async Task Oturum_dolunca_satin_alma_silinmez()
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            var wallet = new AuthFailWallet();
            var sync = new SyncCoordinator(server, wallet, server, data);
            var s = GameState.NewFor("child_a", Utc);
            s.Wallet.ServerCoins = 100;
            var item = data.Items.First(i => i.Price > 0 && i.IsConsumable);
            s.Wallet.TrySpend(item.Id, 1, item.Price, "tx-auth-1", Utc, out _);
            s.Inventory.Add(item, 1);
            var r = await sync.SyncAsync(s, Local, Utc);
            Assert.IsTrue(r.Offline);
            Assert.AreEqual(1, s.Wallet.Pending.Count, "401: harcama kuyrukta kalır");
            Assert.AreEqual(1, s.Inventory.CountOf(item.Id), "eşya geri alınmaz");

            wallet.SpendError = ServiceError.Rejected;   // kalıcı ret (4xx): kuyruktan düşer, bakiye bilinmiyorsa korunur
            await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(0, s.Wallet.Pending.Count);
            Assert.AreEqual(100, s.Wallet.ServerCoins);
        }
    }
}
