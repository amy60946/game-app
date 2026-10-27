using System;
using System.Linq;
using System.Threading.Tasks;
using NUnit.Framework;
using Pofi.Logic.Data;
using Pofi.Logic.Mail;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    /// <summary>Ebeveyn hediyesi (ParentApp, 27 Ekim 2026; ortak 20261027140000_parent_tasks_gifts).</summary>
    public class GiftTests
    {
        private static GameData Data() => TestData.Load();

        [Test]
        public void Sunucu_yaniti_okunur_bozuk_satir_atlanir()
        {
            var list = GiftBook.Parse(@"[{""id"":""a1"",""item_id"":""hat_cap"",""from_name"":""Annem"",""note"":"" Aferin "",""created_at"":""2026-10-27T10:00:00+00:00""},
                                         {""id"":null,""item_id"":""x""},{""id"":""a2"",""item_id"":""home_lamp"",""from_name"":null,""note"":null}]");
            Assert.AreEqual(2, list.Count);
            Assert.AreEqual("Aferin", list[0].Note);
            Assert.AreEqual(new DateTime(2026, 10, 27, 10, 0, 0, DateTimeKind.Utc), list[0].CreatedAt);
            Assert.AreEqual("", list[1].FromName);
            Assert.AreEqual(0, GiftBook.Parse("bozuk").Count);
        }

        [Test]
        public void Hediye_bir_kez_acilir_seviye_kilidi_yok_haber_bir_kez()
        {
            var data = Data();
            var st = GameState.NewFor("c1", DateTime.UtcNow);
            var crown = data.Items.First(i => i.IsWearable && i.Level >= 5);   // seviyesi yetmeyen eşya
            var lamp = data.Items.First(i => i.IsPlaceable);
            var g1 = new ParentGift { Id = "g1", ItemId = crown.Id, FromName = "Annem" };
            var g2 = new ParentGift { Id = "g2", ItemId = lamp.Id };
            var gone = new ParentGift { Id = "g3", ItemId = "bu_surumde_yok" };
            var pending = new[] { g1, g2, gone };

            var box = GiftBook.Unopened(st.Gifts, pending, id => data.Item(id) != null);
            Assert.AreEqual(2, box.Count, "tanınmayan eşya kutuda beklemez (sonraki sürümde gelir)");
            Assert.AreEqual(2, GiftBook.Tell(st.Gifts, box).Count);
            Assert.AreEqual(0, GiftBook.Tell(st.Gifts, box).Count, "haber bir kez");

            Assert.IsTrue(GiftBook.Open(st, data, g1));
            Assert.IsTrue(st.Inventory.Owns(crown.Id), "seviye gelmeden envanterde: dolapta giyilebilir");
            Assert.IsFalse(GiftBook.Open(st, data, g1), "iki kez girmez");
            Assert.IsFalse(GiftBook.HasPlaceable(st.Gifts, data));
            Assert.IsTrue(GiftBook.Open(st, data, g2));
            Assert.IsTrue(GiftBook.HasPlaceable(st.Gifts, data), "hediye ev eşyası: süsleme seviyesi gelmeden açılır");
            Assert.IsFalse(GiftBook.Open(st, data, gone));

            Assert.AreEqual(0, GiftBook.Unopened(st.Gifts, pending, id => data.Item(id) != null).Count);
            CollectionAssert.AreEquivalent(new[] { "g1", "g2" }, GiftBook.NeedsClaim(st.Gifts, pending).Select(g => g.Id));
        }

        [Test]
        public async Task Sahte_arka_uc_hediye_kapatir()
        {
            var b = new MockBackend(Data());
            var g = b.ParentGift("hat_cap");
            Assert.AreEqual(1, (await b.PendingGiftsAsync()).Count);
            Assert.AreEqual(true, await b.ClaimGiftAsync(g.Id));
            Assert.AreEqual(false, await b.ClaimGiftAsync(g.Id), "ikinci kapatma false");
            Assert.AreEqual(0, (await b.PendingGiftsAsync()).Count);
            b.Offline = true;
            Assert.IsNull(await b.PendingGiftsAsync());
            Assert.IsNull(await b.ClaimGiftAsync(g.Id));
        }
    }
}
