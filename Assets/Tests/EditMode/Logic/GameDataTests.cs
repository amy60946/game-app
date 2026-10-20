using System.Linq;
using NUnit.Framework;

namespace Pofi.Tests.Logic
{
    public class GameDataTests
    {
        [Test]
        public void Data_is_valid()
        {
            var errors = TestData.Load().Validate();
            Assert.IsEmpty(errors, string.Join("\n", errors));
        }

        [Test]
        public void Okti_tek_secilebilir_pet_eski_on_iki_emekli()
        {
            var d = TestData.Load();
            CollectionAssert.AreEqual(Enumerable.Range(1, 13).Select(i => $"pet_{i:00}").ToArray(), d.Pets.Select(p => p.Id).ToArray());
            Assert.AreEqual(new[] { "pet_13" }, d.ActivePets.Select(p => p.Id).ToArray());
            Assert.AreEqual("Okti", d.ActivePets[0].Name);
        }

        [Test]
        public void Emekli_petli_kayit_Oktiye_gecer_ad_korunur()
        {
            var d = TestData.Load();
            var s = new Pofi.Logic.State.GameState { PetId = "pet_04", PetName = "Mimi" };
            Assert.IsTrue(Pofi.Logic.App.PetRoster.Migrate(s, d));
            Assert.AreEqual("pet_13", s.PetId);
            Assert.AreEqual("Mimi", s.PetName);
            Assert.IsFalse(Pofi.Logic.App.PetRoster.Migrate(s, d), "ikinci kez değişmez");
            Assert.IsFalse(Pofi.Logic.App.PetRoster.Migrate(new Pofi.Logic.State.GameState(), d), "pet seçilmemiş kayıt");
        }
    }
}
