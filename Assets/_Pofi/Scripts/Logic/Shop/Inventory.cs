using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Cosmetics;
using Pofi.Logic.Data;

namespace Pofi.Logic.Shop
{
    /// <summary>
    /// Envanter (FR-SHOP-3): tüketilebilirler sayıyla, giyilebilir ve yerleştirilebilirler sahiplik olarak.
    /// Pet değişince (FR-PET-7) envanter korunur; uymayan giyilenler çıkarılır ama envanterde kalır.
    /// </summary>
    [Serializable]
    public sealed class Inventory
    {
        public Dictionary<string, int> Counts = new Dictionary<string, int>();     // yiyecek, sabun, tohum
        public List<string> Owned = new List<string>();                           // kıyafet, aksesuar, ev, dekor
        public Dictionary<string, string> Equipped = new Dictionary<string, string>(); // yuva → eşya kimliği

        public int CountOf(string itemId) => Counts.TryGetValue(itemId, out var c) ? c : 0;
        public bool Owns(string itemId) => Owned.Contains(itemId) || CountOf(itemId) > 0;

        public void Add(ItemDef item, int qty = 1)
        {
            if (item.IsConsumable) Counts[item.Id] = CountOf(item.Id) + qty;
            else if (!Owned.Contains(item.Id)) Owned.Add(item.Id);
        }

        /// <summary>Satın alma sunucuda reddedilirse geri alır.</summary>
        public void Remove(ItemDef item, int qty = 1)
        {
            if (item.IsConsumable)
            {
                var left = CountOf(item.Id) - qty;
                if (left > 0) Counts[item.Id] = left; else Counts.Remove(item.Id);
            }
            else
            {
                Owned.Remove(item.Id);
                foreach (var slot in Equipped.Where(kv => kv.Value == item.Id).Select(kv => kv.Key).ToList()) Equipped.Remove(slot);
            }
        }

        public bool TryConsume(string itemId)
        {
            var c = CountOf(itemId);
            if (c <= 0) return false;
            if (c == 1) Counts.Remove(itemId); else Counts[itemId] = c - 1;
            return true;
        }

        public FitResult TryEquip(PetSpeciesDef pet, ItemDef item)
        {
            if (!item.IsWearable || !Owned.Contains(item.Id)) return FitResult.No("fit.reason.not_owned");
            var fit = CosmeticFit.Evaluate(pet, item);
            if (fit.Allowed) Equipped[item.Slot] = item.Id;
            return fit;
        }

        public void Unequip(string slot) => Equipped.Remove(slot);

        /// <summary>Pet değişince: uymayan giyilenleri çıkarır (envanterde kalır). Çıkarılanları döndürür.</summary>
        public List<string> RefitFor(PetSpeciesDef pet, Func<string, ItemDef> lookup)
        {
            var removed = new List<string>();
            foreach (var kv in Equipped.ToList())
            {
                var item = lookup(kv.Value);
                if (item == null || !CosmeticFit.Evaluate(pet, item).Allowed)
                {
                    Equipped.Remove(kv.Key);
                    removed.Add(kv.Value);
                }
            }
            return removed;
        }
    }
}
