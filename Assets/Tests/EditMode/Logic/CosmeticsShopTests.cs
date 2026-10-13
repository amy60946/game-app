using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Cosmetics;
using Pofi.Logic.Data;
using Pofi.Logic.Economy;
using Pofi.Logic.Shop;

namespace Pofi.Tests.Logic
{
    public class CosmeticsShopTests
    {
        private static GameData D => TestData.Load();
        private static readonly DateTime Now = new DateTime(2026, 10, 13, 10, 0, 0, DateTimeKind.Utc);

        /// <summary>Kabul ölçütü 8: her giyilebilir × her pet ya varyantla uyar ya da açıklamalı reddedilir.</summary>
        [Test]
        public void Every_wearable_on_every_pet_has_a_variant_or_a_reason()
        {
            var report = new List<string>();
            foreach (var pet in D.Pets)
                foreach (var item in D.Items.Where(i => i.IsWearable))
                {
                    var r = CosmeticFit.Evaluate(pet, item);
                    Assert.IsTrue(r.Allowed ? !string.IsNullOrEmpty(r.Variant) : r.ReasonKey.StartsWith("fit.reason."),
                        $"{pet.Name} × {item.Name}");
                    if (!r.Allowed) report.Add($"{pet.Name} × {item.Name}: {r.ReasonKey}");
                }
            TestContext.WriteLine(string.Join("\n", report));
        }

        [Test]
        public void Each_pet_can_wear_at_least_one_item_in_every_slot_except_benli_back()
        {
            foreach (var pet in D.Pets)
                foreach (var slot in Slot.All)
                {
                    var any = D.Items.Where(i => i.Slot == slot).Any(i => CosmeticFit.Evaluate(pet, i).Allowed);
                    if (pet.Name == "Benli" && slot == Slot.Back) Assert.IsFalse(any);
                    else Assert.IsTrue(any, $"{pet.Name} için '{slot}' yuvasında hiç uygun eşya yok");
                }
        }

        [Test]
        public void Specific_rules_from_art_template()
        {
            FitResult F(string pet, string item) => CosmeticFit.Evaluate(D.Pets.First(p => p.Name == pet), D.Item(item));
            Assert.AreEqual("ear_holes", F("Pofi", "hat_cap").Variant);
            Assert.AreEqual("mane_fit", F("Arlo", "hat_straw").Variant);
            Assert.IsFalse(F("Benli", "backpack_small").Allowed);
            Assert.IsFalse(F("Piko", "cape_hero").Allowed);
            Assert.IsTrue(F("Piko", "badge_patch").Allowed);
            Assert.AreEqual("on_shell", F("Tosbi", "backpack_small").Variant);
            Assert.IsFalse(F("Pıtı", "shirt_stripes").Allowed);
            Assert.IsTrue(F("Pıtı", "apron_sailor").Allowed);
            Assert.IsFalse(F("Mavi", "glove_mitten").Allowed);
            Assert.IsFalse(F("Fifi", "glasses_star").Allowed, "hortumlu fil: klips varyantı olmayan gözlük takamaz");
            Assert.IsFalse(F("Pofi", "headphones").Allowed);
        }

        [Test]
        public void Buy_flow_checks_level_coins_fit_and_ownership()
        {
            var pofi = D.Pet("pet_01");
            var w = new Wallet { ServerCoins = 30 };
            var inv = new Inventory();
            Assert.AreEqual(BuyCheck.LevelLocked, ShopRules.View(D.Item("hat_cap"), 2, w, inv, pofi).State);
            Assert.AreEqual(3, ShopRules.View(D.Item("hat_cap"), 2, w, inv, pofi).LockedUntilLevel);
            Assert.AreEqual(BuyCheck.DoesNotFitPet, ShopRules.View(D.Item("headphones"), 5, w, inv, pofi).State);
            Assert.AreEqual(BuyCheck.Ok, ShopRules.Buy(D.Item("hat_cap"), 1, 3, w, inv, pofi, "t1", Now, out _));
            Assert.AreEqual(BuyCheck.AlreadyOwned, ShopRules.View(D.Item("hat_cap"), 3, w, inv, pofi).State);
            Assert.AreEqual(BuyCheck.NotEnoughCoins, ShopRules.View(D.Item("shirt_hawaii"), 3, w, inv, pofi).State);
            Assert.AreEqual(BuyCheck.Ok, ShopRules.Buy(D.Item("food_apple"), 2, 3, w, inv, pofi, "t2", Now, out _));
            Assert.AreEqual(2, inv.CountOf("food_apple"));
            Assert.AreEqual(4, w.Available);
        }

        [Test]
        public void Changing_pet_keeps_inventory_and_unequips_only_what_does_not_fit()
        {
            var inv = new Inventory();
            foreach (var id in new[] { "backpack_small", "hat_cap", "glasses_round" }) inv.Add(D.Item(id));
            var pofi = D.Pet("pet_01");
            Assert.IsTrue(inv.TryEquip(pofi, D.Item("backpack_small")).Allowed);
            Assert.IsTrue(inv.TryEquip(pofi, D.Item("hat_cap")).Allowed);
            var removed = inv.RefitFor(D.Pet("pet_12"), D.Item); // Benli: sırt yok
            CollectionAssert.AreEqual(new[] { "backpack_small" }, removed);
            Assert.IsTrue(inv.Owns("backpack_small"), "eşya envanterde kalır");
            Assert.AreEqual("hat_cap", inv.Equipped[Slot.Head]);
        }

        [Test]
        public void Consume_and_rollback()
        {
            var inv = new Inventory();
            inv.Add(D.Item("food_apple"), 2);
            Assert.IsTrue(inv.TryConsume("food_apple"));
            Assert.IsTrue(inv.TryConsume("food_apple"));
            Assert.IsFalse(inv.TryConsume("food_apple"));
            inv.Add(D.Item("cape_hero"));
            inv.Remove(D.Item("cape_hero"));
            Assert.IsFalse(inv.Owns("cape_hero"));
        }
    }
}
