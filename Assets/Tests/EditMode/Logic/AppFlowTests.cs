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
        public void Ekran_sirasi_giris_secim_ev_ad_ekrani_yok()
        {
            Assert.AreEqual(AppScreen.Login, AppFlow.Decide(null, null));
            var st = GameState.NewFor("child_a", Now);
            Assert.AreEqual(AppScreen.PetSelect, AppFlow.Decide(Child, null));
            Assert.AreEqual(AppScreen.PetSelect, AppFlow.Decide(Child, st));
            st.PetId = "pet_13";
            Assert.AreEqual(AppScreen.PetSelect, AppFlow.Decide(Child, st), "adsız kayıt tanışma ekranına döner");
            PetChange.Choose(st, "pet_13", TestData.Load());
            Assert.AreEqual(AppScreen.Home, AppFlow.Decide(Child, st), "seçince doğrudan ada");
            Assert.AreEqual("Okti", st.PetName);
        }

        [Test]
        public void Secimde_ad_Okti_ve_hos_geldin_hediyesi_bir_kez()
        {
            var data = TestData.Load();
            var kit = new StarterKit(TestData.ReadText("start.json"));
            var st = GameState.NewFor("child_a", Now);
            PetChange.Choose(st, "pet_13", data, kit);
            Assert.AreEqual(PetRoster.Name, st.PetName);
            Assert.IsTrue(st.StarterGiven);
            var apples = st.Inventory.CountOf("food_apple");
            Assert.Greater(apples, 0);
            // Ayarlar → "Pet değiştir": seçim ekranı; yeniden seçince ad yine Okti, hediye ikinci kez verilmez
            PetChange.Begin(st);
            Assert.AreEqual(AppScreen.PetSelect, AppFlow.Decide(Child, st));
            PetChange.Choose(st, "pet_13", data, kit);
            Assert.AreEqual("Okti", st.PetName);
            Assert.AreEqual(apples, st.Inventory.CountOf("food_apple"));
            Assert.AreEqual(AppScreen.Home, AppFlow.Decide(Child, st));
        }

        [Test]
        public void Eski_kayitta_baska_ad_yuklemede_Okti_olur()
        {
            var data = TestData.Load();
            var kit = new StarterKit(TestData.ReadText("start.json"));
            var old = GameState.NewFor("child_a", Now);
            old.PetId = "pet_13"; old.PetName = "Ayşe";   // çocuk kendi adını yazmış olabilir
            old.StarterGiven = true;
            var back = SaveCodec.Deserialize(SaveCodec.Serialize(old, Now));
            Assert.AreEqual("Ayşe", back.PetName);
            Assert.IsTrue(PetRoster.FixName(back, kit, data));
            Assert.AreEqual("Okti", back.PetName);
            Assert.IsFalse(PetRoster.FixName(back, kit, data), "ikinci kez değişmez");
            Assert.AreEqual(AppScreen.Home, AppFlow.Decide(Child, back));

            // emekli petli eski kayıt: önce Okti'ye geçer, sonra adı sabitlenir
            var retired = GameState.NewFor("child_a", Now);
            retired.PetId = "pet_04"; retired.PetName = "Mimi"; retired.StarterGiven = true;
            Assert.IsTrue(PetRoster.Migrate(retired, data));
            Assert.IsTrue(PetRoster.FixName(retired, kit, data));
            Assert.AreEqual("pet_13", retired.PetId);
            Assert.AreEqual("Okti", retired.PetName);
        }

        [Test]
        public void Ad_ekraninda_kalmis_kayit_adi_ve_hediyeyi_alir()
        {
            var data = TestData.Load();
            var kit = new StarterKit(TestData.ReadText("start.json"));
            var st = GameState.NewFor("child_a", Now);
            st.PetId = "pet_13";   // eski akış: seçti, ad vermeden çıktı
            Assert.IsTrue(PetRoster.FixName(st, kit, data));
            Assert.AreEqual("Okti", st.PetName);
            Assert.IsTrue(st.StarterGiven);
            Assert.Greater(st.Inventory.CountOf("food_apple"), 0);

            var none = GameState.NewFor("child_a", Now);
            Assert.IsFalse(PetRoster.FixName(none, kit, data), "pet seçilmemiş kayda ad konmaz");
            Assert.IsNull(none.PetName);
            Assert.IsFalse(none.StarterGiven);
            Assert.IsFalse(PetRoster.FixName(null, kit, data));
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
            var ids = TestData.Load().Pets.Select(p => p.Id).Take(12).ToList();   // karusel mekaniği (12 öğe)
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
                "pet.meet_title", "pet.meet_hint", "pet.meet_button", "pet.welcome",
                "stat.fullness", "stat.cleanliness", "stat.happiness", "stat.home",
                "home.feed", "home.wash", "home.play", "home.tidy", "home.level", "settings.sign_out",
                "gate.title", "gate.wrong",
            };
            foreach (var k in keys) Assert.IsTrue(loc.Has(k), k);
        }
    }
}
