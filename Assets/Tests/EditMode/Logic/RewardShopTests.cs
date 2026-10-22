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

        private static (MockBackend server, SyncCoordinator sync, GameState s) Setup(int stones)
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            server.TestGrantStones(stones);
            DemoParent.EnsureRewards(server);
            var sync = new SyncCoordinator(server, server, server, data, server);
            var s = GameState.NewFor("child_a", Utc);
            s.PetId = "pet_13"; s.PetName = "Okti";
            return (server, sync, s);
        }

        [Test]
        public async Task Istek_onaylaninca_harcanabilir_tas_duser_ada_tasi_kalir()
        {
            var (server, sync, s) = Setup(6);
            await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(DemoParent.SampleRewards.Length, s.Rewards.Rewards.Count);
            Assert.AreEqual(6, s.Rewards.Spendable);

            var r = await server.RequestAsync("demo_park", 1);
            Assert.IsTrue(r.Ok);
            Assert.AreEqual(r.RequestId, (await server.RequestAsync("demo_park", 1)).RequestId, "aynı ödül için bekleyen istek geri döner");
            await sync.SyncAsync(s, Local, Utc);
            Assert.IsNotNull(s.Rewards.Pending);
            Assert.IsFalse(s.Rewards.CanRequestMore, "arayüz aynı anda tek bekleyen istek");

            Assert.AreEqual(1, DemoParent.GiveRewards(server));
            var rep = await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(RewardEventKind.Given, rep.RewardEvents.Single().Kind);
            Assert.AreEqual(3, s.Rewards.Spendable, "6 − 3");
            Assert.AreEqual(6, server.SunStones, "adadaki kazanılan taş azalmaz");
            Assert.AreEqual(0, (await sync.SyncAsync(s, Local, Utc)).RewardEvents.Count, "olay bir kez");
        }

        [Test]
        public async Task Degis_tokus_adetli_ve_sinirlar()
        {
            var (server, sync, s) = Setup(5);
            Assert.AreEqual("not_enough_stones", (await server.RequestAsync("demo_tablet", 6)).Error);
            Assert.AreEqual("rejected", (await server.RequestAsync("demo_park", 2)).Error, "eşya ödülü tek adet");
            Assert.AreEqual("rejected", (await server.RequestAsync("demo_tablet", 21)).Error, "en çok 20 kez");
            Assert.AreEqual("not_found", (await server.RequestAsync("yok", 1)).Error);
            Assert.IsTrue((await server.RequestAsync("demo_tablet", 3)).Ok);
            await sync.SyncAsync(s, Local, Utc);
            var q = s.Rewards.Pending;
            Assert.AreEqual(3, q.Cost); Assert.AreEqual(30, q.Amount);
            Assert.AreEqual("Tablet süresi · 30 dakika", RewardText.Label(q));
            Assert.AreEqual("1 taş = 10 dk", RewardText.Rate(s.Rewards.Find("demo_tablet")));

            Assert.IsTrue(server.ParentDecideReward(q.Id, false, "Bugün değil"));
            var rep = await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(RewardEventKind.Declined, rep.RewardEvents.Single().Kind);
            Assert.AreEqual(5, s.Rewards.Spendable, "şimdi olmaz: taş düşmez");

            Assert.IsTrue((await server.RequestAsync("demo_park", 1)).Ok);
            await sync.SyncAsync(s, Local, Utc);
            Assert.IsTrue((await server.CancelAsync(s.Rewards.Pending.Id)).Ok);
            Assert.AreEqual("not_found", (await server.CancelAsync(s.Rewards.Pending.Id)).Error);
        }

        [Test]
        public async Task Ebeveynin_dogrudan_odulu_ve_tas_dusurmesi_haber_olur_ilk_senkronda_gecmis_sayilmaz()
        {
            var (server, sync, s) = Setup(10);
            server.ParentGiveReward("demo_movie");
            await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(0, (await sync.SyncAsync(s, Local, Utc)).RewardEvents.Count, "ilk senkronda geçmiş olay yok");
            server.ParentGiveReward("demo_park");
            server.ParentDeductStones(1, "Oyuncakları toplamadık");
            var rep = await sync.SyncAsync(s, Local, Utc);
            Assert.AreEqual(1, rep.RewardEvents.Count(e => e.Kind == RewardEventKind.Given));
            var d = rep.RewardEvents.Single(e => e.Kind == RewardEventKind.Deducted).Deduction;
            Assert.AreEqual(1, d.Amount); Assert.AreEqual("Oyuncakları toplamadık", d.Note);
            Assert.AreEqual(1, s.Rewards.Spendable, "10 − 5 − 3 − 1");
            var notes = Pofi.Logic.App.NoticeDigest.Build(null, rep.RewardEvents);
            Assert.IsTrue(notes.Any(n => n.Key == "notice.stones_deducted_note"));
        }

        [Test]
        public void Hedef_kalan_tas()
        {
            var book = new RewardBook { Spendable = 2 };
            var r = new RealReward { Id = "a", Cost = 5 };
            book.Rewards.Add(r); book.GoalId = "a";
            Assert.AreEqual(3, book.StonesLeft(book.Goal));
            book.Apply(new RewardsSnapshot { Spendable = 2 });
            Assert.IsNull(book.GoalId, "ödül kalkınca hedef düşer");
        }

        [Test]
        public void Sunucu_yaniti_okunur()
        {
            var snap = SupabaseGameService.ParseRewards(
                @"[{""id"":""r1"",""title"":""Tablet"",""kind"":""exchange"",""cost"":1,""unit"":""minute"",""unit_amount"":10,""icon"":""tablet""}]",
                @"[{""id"":""q1"",""reward_id"":""r1"",""title"":""Tablet"",""quantity"":3,""cost"":3,""unit"":""minute"",""amount"":30,""source"":""child"",""status"":""pending"",""note"":null,""created_at"":""2026-10-22T10:00:00Z""}]",
                @"[{""id"":17,""amount"":-2,""note"":""söz"",""created_at"":""2026-10-22T10:00:00Z""}]");
            Assert.IsTrue(snap.Rewards.Single().IsExchange);
            Assert.AreEqual(30, snap.Requests.Single().Amount);
            Assert.AreEqual("17", snap.Deductions.Single().Id);
            Assert.AreEqual(2, snap.Deductions.Single().Amount);
            Assert.AreEqual(0, SupabaseGameService.ParseRewards("null", "", "{bozuk").Rewards.Count);
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
