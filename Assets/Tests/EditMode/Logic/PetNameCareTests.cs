using System;
using System.IO;
using NUnit.Framework;
using Pofi.Logic.Pet;
using Pofi.Logic.Shop;

namespace Pofi.Tests.Logic
{
    public class PetNameCareTests
    {
        private static PetNameRules Rules()
        {
            string[] roots = { Path.Combine(AppContext.BaseDirectory, "Data"), Path.Combine("Assets", "_Pofi", "Resources", "Data") };
            foreach (var r in roots)
            {
                var p = Path.Combine(r, "name_blocklist.json");
                if (File.Exists(p)) return new PetNameRules(File.ReadAllText(p));
            }
            throw new FileNotFoundException("name_blocklist.json");
        }

        [TestCase("Pofi", NameCheck.Ok)]
        [TestCase("  Şeker   Kız ", NameCheck.Ok)]
        [TestCase("Çıtır", NameCheck.Ok)]
        [TestCase("Sıkı", NameCheck.Ok)]       // kısa kök 'sik' tam kelime değil → masum isim engellenmez
        [TestCase("Malika", NameCheck.Ok)]
        [TestCase("A", NameCheck.TooShort)]
        [TestCase("Çokuzunbirisim", NameCheck.TooLong)]
        [TestCase("Pofi!", NameCheck.InvalidCharacters)]
        [TestCase("Pofi2", NameCheck.InvalidCharacters)]
        [TestCase("Salak", NameCheck.NotAllowed)]
        [TestCase("Süper Mal", NameCheck.NotAllowed)]
        [TestCase("Orospuu", NameCheck.NotAllowed)]
        [TestCase("Siktirr", NameCheck.NotAllowed)]
        public void Names(string name, NameCheck expected) => Assert.AreEqual(expected, Rules().Check(name));

        [Test]
        public void Tidy_collapses_spaces() => Assert.AreEqual("Şeker Kız", PetNameRules.Tidy("  Şeker   Kız "));

        [Test]
        public void Feeding_uses_inventory_and_respects_night_and_fullness()
        {
            var d = TestData.Load();
            var stats = PetStats.New(DateTime.UtcNow);
            var inv = new Inventory();
            var day = new DateTime(2026, 10, 13, 12, 0, 0);
            var apple = d.Item("food_apple");
            Assert.AreEqual(CareResult.NoItem, PetCare.Feed(stats, inv, apple, day));
            inv.Add(apple, 3);
            Assert.AreEqual(CareResult.Ok, PetCare.Feed(stats, inv, apple, day));
            Assert.AreEqual(100f, stats[StatKind.Fullness], 0.01f);
            Assert.AreEqual(CareResult.AlreadyFull, PetCare.Feed(stats, inv, apple, day));
            Assert.AreEqual(CareResult.Sleeping, PetCare.Play(stats, new DateTime(2026, 10, 13, 22, 30, 0)));
            Assert.AreEqual(CareResult.WrongItem, PetCare.Wash(stats, inv, apple, day));
            inv.Add(d.Item("clean_soap"));
            stats.Add(StatKind.Cleanliness, -50f);
            Assert.AreEqual(CareResult.Ok, PetCare.Wash(stats, inv, d.Item("clean_soap"), day));
            Assert.AreEqual(70f, stats[StatKind.Cleanliness], 0.01f);
            Assert.AreEqual(2, inv.CountOf("food_apple"));
        }
    }
}
