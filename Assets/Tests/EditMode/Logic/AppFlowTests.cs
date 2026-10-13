using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Pet;
using Pofi.Logic.Profile;
using Pofi.Logic.Services;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    public class AppFlowTests
    {
        private static readonly DateTime Now = new DateTime(2026, 10, 13, 12, 0, 0, DateTimeKind.Utc);
        private static readonly ChildSession Child = new ChildSession("child_a", "Nazlı", AgeBand.A, "flamingo");

        [Test]
        public void Ekran_sirasi_giris_secim_isim_ev()
        {
            Assert.AreEqual(AppScreen.Login, AppFlow.Decide(null, null));
            var st = GameState.NewFor("child_a", Now);
            Assert.AreEqual(AppScreen.PetSelect, AppFlow.Decide(Child, null));
            Assert.AreEqual(AppScreen.PetSelect, AppFlow.Decide(Child, st));
            st.PetId = "pet_05";
            Assert.AreEqual(AppScreen.PetName, AppFlow.Decide(Child, st));
            st.PetName = "Limon";
            Assert.AreEqual(AppScreen.Home, AppFlow.Decide(Child, st));
        }

        [Test]
        public void Baska_cocugun_kaydi_kullanilmaz()
        {
            Assert.IsTrue(AppFlow.BelongsTo(GameState.NewFor("child_a", Now), Child));
            Assert.IsFalse(AppFlow.BelongsTo(GameState.NewFor("child_b", Now), Child));
            Assert.IsFalse(AppFlow.BelongsTo(null, Child));
        }

        [Test]
        public void Karusel_iki_yonde_doner()
        {
            var ids = TestData.Load().Pets.Select(p => p.Id).ToList();
            var picker = new PetPicker(ids);
            Assert.AreEqual("pet_01", picker.Current);
            Assert.AreEqual("pet_12", picker.Prev());
            Assert.AreEqual("pet_01", picker.Next());
            for (var i = 0; i < 12; i++) picker.Next();
            Assert.AreEqual("pet_01", picker.Current);
            Assert.AreEqual("pet_02", picker.Swipe(-200f, 80f));
            Assert.AreEqual("pet_02", picker.Swipe(30f, 80f));   // kısa hareket yok sayılır
            Assert.AreEqual("pet_01", picker.Swipe(120f, 80f));
            picker.JumpTo("pet_09");
            Assert.AreEqual(8, picker.Index);
        }

        [Test]
        public void Hos_geldin_hediyesi_bir_kez_verilir_ve_kayitta_kalir()
        {
            var data = TestData.Load();
            var kit = new StarterKit(TestData.ReadText("start.json"));
            foreach (var id in kit.Items.Keys) Assert.IsNotNull(data.Item(id), id);
            var st = GameState.NewFor("child_a", Now);
            Assert.IsTrue(kit.GiveOnce(st, data));
            var apples = st.Inventory.CountOf("food_apple");
            Assert.Greater(apples, 0);
            Assert.IsFalse(kit.GiveOnce(st, data));
            Assert.AreEqual(apples, st.Inventory.CountOf("food_apple"));
            Assert.AreEqual(0, st.Wallet.Available);   // hediye coin içermez

            var back = SaveCodec.Deserialize(SaveCodec.Serialize(st, Now));
            Assert.IsTrue(back.StarterGiven);
            Assert.AreEqual(apples, back.Inventory.CountOf("food_apple"));
        }

        [Test]
        public void Bakim_mesajlari_tabloda_var()
        {
            var loc = new Localization(TestData.ReadText("tr.json"));
            foreach (CareAction a in Enum.GetValues(typeof(CareAction)))
                StringAssert.DoesNotStartWith("[", CareFeedback.Message(loc, a, CareResult.Ok, "Pofi"));
            StringAssert.Contains("Pofi", CareFeedback.Message(loc, CareAction.Play, CareResult.Sleeping, "Pofi"));

            var stats = PetStats.New(Now);
            Assert.AreEqual("", CareFeedback.Idle(loc, stats, StatDecayConfig.Default));
            stats.Values[(int)StatKind.Cleanliness] = 15f;
            Assert.AreEqual(loc.Get("care.sad.cleanliness"), CareFeedback.Idle(loc, stats, StatDecayConfig.Default));
        }

        [Test]
        public void Arayuz_metinleri_tabloda_var()
        {
            var loc = new Localization(TestData.ReadText("tr.json"));
            string[] keys =
            {
                "auth.title", "auth.code_prompt", "auth.button", "auth.invalid", "auth.throttled", "auth.demo_hint", "auth.hello",
                "pet.pick_title", "pet.pick_hint", "pet.pick_button", "pet.pick_confirm", "pet.pick_yes", "pet.pick_no",
                "pet.name_title", "pet.name_placeholder", "pet.name_button", "pet.welcome",
                "stat.fullness", "stat.cleanliness", "stat.happiness", "stat.home",
                "home.feed", "home.wash", "home.play", "home.tidy", "home.level", "settings.sign_out",
                "gate.title", "gate.wrong",
            };
            foreach (var k in keys) Assert.IsTrue(loc.Has(k), k);
        }
    }
}
