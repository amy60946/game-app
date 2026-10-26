using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    /// <summary>Rehberli görev zinciri (App/Guide; sıra GB17, 24 Ekim 2026).</summary>
    public class GuideTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 19, 12, 0, 0);

        private static GameState NewPlayer()
        {
            Guide.Configure(TestData.Load());
            return new GameState { PetId = "pet_13", PetName = "Okti" };
        }

        private static System.Collections.Generic.List<GuideStep> Do(GameState s, string counter, int level = 1)
        {
            s.Counters.Add(counter, 1, Local);   // RecordActivity sırası: önce sayaç, sonra rehber
            return Guide.OnActivity(s, level, counter);
        }

        /// <summary>Hoş geldin coin'i (sunucu 20) + ilk aksesuar alınmış gibi.</summary>
        private static void BuyFirstWear(GameState s)
        {
            var item = Guide.FirstWear(TestData.Load(), 20);
            s.Inventory.Add(item);
            Do(s, "item_equipped");
            Do(s, "wear_bought");
        }

        [Test]
        public void Sira_kullanicinin_akisi_ve_sayaclar_essiz()
        {
            CollectionAssert.AreEqual(
                new[] { "feed", "wash", "home", "tidy", "play", "shop", "wear", "kiskac", "coconut", "deliver", "mavi", "gift", "clear", "gather", "hut", "fire", "stone" },
                Guide.Steps.Select(x => x.Id).ToArray());
            Assert.AreEqual(Guide.Steps.Count, Guide.Steps.Select(x => x.Counter).Distinct().Count());
            Assert.That(Guide.Steps.All(x => x.Xp > 0));
        }

        [Test]
        public void Hos_geldin_coini_ilk_aksesuari_karsilar_ve_komik_esya_onerilmez()
        {
            NewPlayer();
            var item = Guide.FirstWear(TestData.Load(), 20);
            Assert.IsNotNull(item, "20 coin'e Sv1'de giyilebilir bir eşya olmalı");
            Assert.IsFalse(item.Fancy, "komik eşyalar sunucu kataloğunda yok (ortak E9): önce sade eşya");
            Assert.LessOrEqual(Guide.FirstWearPrice, 20);
            Assert.IsNull(Guide.FirstWear(TestData.Load(), Guide.FirstWearPrice - 1));
        }

        [Test]
        public void Ilk_adim_besle_ve_sirayla_ilerler()
        {
            var s = NewPlayer();
            Assert.AreEqual("feed", Guide.Current(s, 1).Id);
            Assert.IsEmpty(Do(s, "pet_washed"), "sırası gelmeyen adım ödül vermez");
            var r = Do(s, "pet_fed");
            Assert.AreEqual("feed", r.Single().Id, "yıkama önceden yapıldı: ödülsüz geçilir");
            Assert.AreEqual("home", Guide.Current(s, 1).Id);
            Assert.AreEqual(2, Guide.DoneCount(s));
            Assert.AreEqual("5/19", Guide.Label(s), "temel ipuçları (yürü, etrafa bak) 1–2; rehber 3'ten başlar");
        }

        [Test]
        public void Coin_yoksa_dukkan_ve_giydir_atlanir_coin_gelince_doner()
        {
            var s = NewPlayer();
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "pet_played" }) Do(s, c);
            Assert.AreEqual("shop", Guide.Current(s, 1).Id, "hoş geldin coin'i beklenirken sıra dükkânda kalır (Kıskaç erken gelmez)");
            s.SeenTips.Add(Guide.WelcomeFlag);
            Assert.AreEqual("kiskac", Guide.Current(s, 1).Id, "coin geldi ama yetmiyor: rehber takılmaz, Kıskaç'a geçer");
            s.Wallet.ServerCoins = 20;
            Assert.AreEqual("shop", Guide.Current(s, 1).Id, "hoş geldin coin'i gelince dükkân adımı");
            BuyFirstWear(s);
            Assert.IsTrue(Guide.IsDone(s, Guide.Get("shop")));
            Assert.IsTrue(Guide.IsDone(s, Guide.Get("wear")), "dükkânda alınan aksesuar takılır: giydir de biter");
            Assert.AreEqual("kiskac", Guide.Current(s, 1).Id);
        }

        [Test]
        public void Kiskac_cevizi_teslim_Mavi_ve_kulube_sirayla()
        {
            var s = NewPlayer();
            s.Wallet.ServerCoins = 20;
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "pet_played" }) Do(s, c);
            BuyFirstWear(s);
            Assert.AreEqual("kiskac", Do(s, "kiskac_met").Single().Id);
            Assert.AreEqual("coconut", Guide.Current(s, 1).Id);
            s.Inventory.Add(TestData.Load().Item(Gathering.CoconutItem), Guide.CoconutsNeeded);
            Assert.IsEmpty(Do(s, "gathered"), "elde 2 ceviz (başka yoldan): adım ödülsüz geçilir");
            Assert.AreEqual("deliver", Guide.Current(s, 1).Id);
        }

        [Test]
        public void Ceviz_adimi_iki_ceviz_olunca_odullu_biter()
        {
            var s = NewPlayer();
            s.Wallet.ServerCoins = 20;
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "pet_played" }) Do(s, c);
            BuyFirstWear(s);
            Do(s, "kiskac_met");
            Assert.AreEqual("coconut", Do(s, "coconuts_ready").Single().Id);
            Assert.AreEqual("deliver", Guide.Current(s, 1).Id);
            Assert.AreEqual("deliver", Do(s, "coconut_delivered").Single().Id);
            Assert.AreEqual("mavi", Guide.Current(s, 1).Id);
            Assert.AreEqual("mavi", Do(s, "mavi_arrived").Single().Id);
            Assert.AreEqual("gift", Guide.Current(s, 1).Id, "Mavi'den sonra hediye taş (GB19)");
            GiftAndClear(s);
            Assert.AreEqual("gather", Guide.Current(s, 1).Id);
            s.Gather.Materials[Gathering.Wood] = 6; s.Gather.Materials[Gathering.Branch] = 4; s.Gather.Materials[Gathering.Stone] = 3;
            Assert.AreEqual("gather", Do(s, "hut_ready").Single().Id);
            Assert.AreEqual("hut", Guide.Current(s, 1).Id);
            Gathering.Build(s.Gather);
            Assert.AreEqual("hut", Do(s, "hut_built").Single().Id);
            Assert.AreEqual("fire", Guide.Current(s, 1).Id, "kulübeden sonra doğudaki kamp ateşi (pano hoş geldin göreviyle önce geldi)");
            Assert.AreEqual("fire", Do(s, "fire_stoked").Single().Id);
        }

        [Test]
        public void Tas_adimi_tas_yokken_atlanir_tas_gelince_doner()
        {
            var s = NewPlayer();
            s.Wallet.ServerCoins = 20;
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "pet_played" }) Do(s, c);
            BuyFirstWear(s);
            foreach (var c in new[] { "kiskac_met", "coconuts_ready", "coconut_delivered", "mavi_arrived" }) Do(s, c);
            GiftAndClear(s);
            foreach (var c in new[] { "hut_ready", "hut_built", "fire_stoked" }) Do(s, c);
            Assert.IsNull(Guide.Current(s, 1), "hediye taş kulübe sisine gitti, gerçek taş yok: gösterilecek adım yok");
            SunStoneBook.ApplyServerTotal(s.SunStones, 1);
            Assert.AreEqual("stone", Guide.Current(s, 1).Id);
            Assert.AreEqual("stone", Do(s, "stone_placed").Single().Id);
            Assert.IsFalse(Guide.Active(s, 1), "hepsi bitti");
        }

        [Test]
        public void Basladiysa_Sv3_sonrasi_surer_hic_baslamadiysa_kapanir()
        {
            var s = NewPlayer();
            Do(s, "pet_fed");
            Assert.IsTrue(Guide.Active(s, 5), "zincir başladı: seviye sınırı yok");
            Guide.Start(s, 5);
            Assert.IsTrue(Guide.Active(s, 5));
            Assert.AreEqual("wash", Guide.Current(s, 5).Id);

            var old = NewPlayer();
            Guide.Start(old, 4);
            Assert.IsFalse(Guide.Active(old, 3), "Sv3'ü geçmiş, hiç başlamamış oyuncu rehberi görmez");
        }

        [Test]
        public void Onceden_yapilmis_kulube_ve_Mavi_odulsuz_gecilir()
        {
            var s = NewPlayer();
            s.Gather.HutBuilt = true;
            s.Story.Seen.Add("ch2_open");
            Guide.Start(s, 1);   // kulübesi yapılmış eski oyuncu: kulübe sisi hiç görünmez (hediye taş kendiliğinden konur)
            s.Wallet.ServerCoins = 20;
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "pet_played" }) Do(s, c);
            BuyFirstWear(s);
            Do(s, "kiskac_met"); Do(s, "coconuts_ready");
            var r = Do(s, "coconut_delivered");
            Assert.AreEqual("deliver", r.Single().Id);
            Assert.AreEqual("fire", Guide.Current(s, 1).Id, "Mavi'yi görmüş, kulübesi yapılmış: hediye, sis ve kulübe adımları geçildi");
        }

        /// <summary>Mavi'nin hediye taşı + kulübe yerindeki sisi kaldırma (rehberin "gift" ve "clear" adımları).</summary>
        private static void GiftAndClear(GameState s)
        {
            Assert.IsTrue(SunStoneBook.GiveGift(s.SunStones));
            Assert.AreEqual("gift", Do(s, "gift_stone").Single().Id);
            Assert.AreEqual("clear", Guide.Current(s, 1).Id);
            Assert.AreEqual(PlaceResult.Repaired, TestData.Load().SunBook.PlaceOne(s.SunStones, SunStoneBook.HutSpot));
            Assert.AreEqual("clear", Do(s, "hut_fog_cleared").Single().Id);
        }

        [Test]
        public void Hediye_tas_kulube_sisini_acar_tas_adimini_ve_ilk_gunu_bitirmez()
        {
            var s = NewPlayer();
            Assert.IsTrue(SunStoneBook.GiveGift(s.SunStones));
            Assert.IsFalse(SunStoneBook.GiveGift(s.SunStones), "çocuk başına bir kez");
            Assert.AreEqual(1, SunStoneBook.Available(s.SunStones));
            SunStoneBook.ApplyServerTotal(s.SunStones, 0);
            Assert.AreEqual(1, SunStoneBook.Available(s.SunStones), "sunucu toplamı hediyeyi silmez (yalnız ada)");
            var book = TestData.Load().SunBook;
            Assert.AreEqual(SunStoneBook.HutSpot, book.Next(s.SunStones).Id, "ilk nokta kulübe yerindeki sis");
            Assert.AreEqual(PlaceResult.Repaired, book.PlaceOne(s.SunStones, SunStoneBook.HutSpot));
            Assert.AreEqual(0, SunStoneBook.RealPlaced(s.SunStones), "hediye taş gerçek taş sayılmaz");
            Assert.IsFalse(Guide.Get("stone").AlreadyDone(s), "koydaki sis adımı hâlâ gerçek taş bekler");
            Assert.AreNotEqual(FirstDayStep.Done, FirstDay.Current(s, Local, Local), "ilk gün akışı (Ev Görevleri) sürer");
            Assert.AreEqual("spot_fog_cove", book.Next(s.SunStones).Id, "sonra koy");
        }

        [Test]
        public void Rehberin_ortasindaki_oyuncu_hediye_adimina_doner_eski_oyuncu_sisi_gormez()
        {
            var book = TestData.Load().SunBook;
            var mid = NewPlayer();
            mid.Story.Seen.Add("ch2_open");
            mid.Gather.Materials[Gathering.Wood] = 3;
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "pet_played", "kiskac_met", "coconuts_ready", "coconut_delivered" }) Do(mid, c);
            Guide.Start(mid, 2);
            Assert.AreEqual("gift", Guide.Current(mid, 2).Id, "kulübesini yapmamış: hediye + sis adımları önce");
            Assert.IsFalse(book.IsRepaired(mid.SunStones, SunStoneBook.HutSpot));

            var old = NewPlayer();
            old.Gather.HutBuilt = true;
            SunStoneBook.ApplyServerTotal(old.SunStones, 2);
            book.PlaceOne(old.SunStones, SunStoneBook.HutSpot);   // eski sürümde ilk nokta yoktu: bunun yerine koya konmuş olurdu
            var fresh = NewPlayer();
            fresh.Gather.HutBuilt = true;
            SunStoneBook.ApplyServerTotal(fresh.SunStones, 2);
            var before = SunStoneBook.Available(fresh.SunStones);
            Guide.Start(fresh, 4);
            Assert.IsTrue(book.IsRepaired(fresh.SunStones, SunStoneBook.HutSpot), "kulübesi var: sis kendiliğinden kalkmış");
            Assert.AreEqual(before, SunStoneBook.Available(fresh.SunStones), "boştaki taş değişmez (hediye kendi yerine)");
            Assert.IsTrue(fresh.Story.Seen.Contains(Guide.HutFogScene), "sahnesi izlenmiş sayılır");
        }
    }
}
