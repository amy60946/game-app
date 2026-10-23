using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Cosmetics;
using Pofi.Logic.Core;
using Pofi.Logic.Data;
using Pofi.Logic.Pet;

namespace Pofi.Tests.Logic
{
    public class BalanceLocalizationTests
    {
        [TestCase("Pofi", "Pofi'nin", "Pofi'yi")]
        [TestCase("Arlo", "Arlo'nun", "Arlo'yu")]
        [TestCase("Boncuk", "Boncuk'un", "Boncuk'u")]
        [TestCase("Pıtı", "Pıtı'nın", "Pıtı'yı")]
        [TestCase("Tosbi", "Tosbi'nin", "Tosbi'yi")]
        [TestCase("Şeker Kız", "Şeker Kız'ın", "Şeker Kız'ı")]
        [TestCase("Gümüş", "Gümüş'ün", "Gümüş'ü")]
        public void Name_suffixes(string name, string gen, string acc)
        {
            Assert.AreEqual(gen, TurkishSuffix.Genitive(name));
            Assert.AreEqual(acc, TurkishSuffix.Accusative(name));
        }

        [TestCase("Okti", "Okti'ye")] [TestCase("Pofi", "Pofi'ye")] [TestCase("Arlo", "Arlo'ya")] [TestCase("Boncuk", "Boncuk'a")]
        [TestCase("Gümüş", "Gümüş'e")] [TestCase("Şeker Kız", "Şeker Kız'a")]
        public void Name_dative(string name, string dat) => Assert.AreEqual(dat, TurkishSuffix.Dative(name));

        [TestCase(1, "1'de")] [TestCase(3, "3'te")] [TestCase(4, "4'te")] [TestCase(5, "5'te")] [TestCase(6, "6'da")]
        [TestCase(9, "9'da")] [TestCase(10, "10'da")] [TestCase(13, "13'te")] [TestCase(15, "15'te")] [TestCase(40, "40'ta")]
        public void Number_locative(int n, string expected) => Assert.AreEqual(expected, TurkishSuffix.Locative(n));

        /// <summary>
        /// FR-ECO-5: ebeveyn ödülü 1–50 coin. Varsayılan 5/10/20. Kural: günde 2 kolay görev (2×5) ile bir yiyecek + sabun
        /// her zaman karşılanır; ortalama gün (3 görev ≈ 30 coin) ile büyük ev eşyası birkaç (≤ 7) günde alınır.
        /// </summary>
        [Test]
        public void Prices_are_balanced_against_task_rewards()
        {
            var d = TestData.Load();
            var cheapestFood = d.Items.Where(i => i.Category == ItemCategory.Food && i.Level == 1).Min(i => i.Price);
            var soap = d.Item("clean_soap").Price;
            Assert.LessOrEqual(cheapestFood + soap, 2 * 5, "2 kolay görev = 1 yiyecek + sabun");

            // Tam bakım (günlük azalma sınırı 60 puan): tokluk + temizlik maliyeti
            var cfg = StatDecayConfig.Default;
            var apple = d.Item("food_apple");
            var dailyCare = Math.Ceiling(cfg.MaxDropPerDay / apple.Effects["fullness"]) * apple.Price +
                            Math.Ceiling(cfg.MaxDropPerDay / d.Item("clean_soap").Effects["cleanliness"]) * soap;
            TestContext.WriteLine($"tam bakım maliyeti: {dailyCare} coin/gün");
            Assert.LessOrEqual(dailyCare, 15, "ortalama günün yarısından azı bakıma gitmeli");

            var spare = 30 - dailyCare;
            foreach (var big in d.Items.Where(i => i.Category == ItemCategory.Home))
                Assert.LessOrEqual(big.Price / spare, 7.0, $"{big.Name} en fazla ~1 haftada alınmalı");
            foreach (var premium in d.Items.Where(i => i.Premium))
                Assert.LessOrEqual(premium.Price / spare, 14.0, $"{premium.Name} en fazla ~2 haftada alınmalı");
        }

        [Test]
        public void All_reason_keys_and_core_texts_exist_in_turkish()
        {
            var d = TestData.Load();
            string json = null;
            foreach (var r in new[] { Path.Combine(AppContext.BaseDirectory, "Data"), Path.Combine("Assets", "_Pofi", "Resources", "Data") })
                if (File.Exists(Path.Combine(r, "tr.json"))) json = File.ReadAllText(Path.Combine(r, "tr.json"));
            var loc = new Localization(json);
            var reasons = d.Pets.SelectMany(p => d.Items.Where(i => i.IsWearable).Select(i => CosmeticFit.Evaluate(p, i)))
                .Where(f => !f.Allowed).Select(f => f.ReasonKey).Distinct().ToList();
            reasons.Add("fit.reason.not_owned");
            foreach (var k in reasons) Assert.IsTrue(loc.Has(k), "eksik metin: " + k);
            Assert.AreEqual("Seviye 3'te açılır!", loc.Get("shop.locked", TurkishSuffix.Locative(3)));
            Assert.AreEqual("Arlo'nun kafasına bu şapka oturmuyor.", loc.Get("fit.reason.head_shape", TurkishSuffix.Genitive("Arlo")));
            Assert.AreEqual("[yok.boyle]", loc.Get("yok.boyle"));
        }
    }
}
