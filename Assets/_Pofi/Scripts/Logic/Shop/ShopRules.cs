using Pofi.Logic.Cosmetics;
using Pofi.Logic.Data;
using Pofi.Logic.Economy;

namespace Pofi.Logic.Shop
{
    public enum BuyCheck { Ok, LevelLocked, NotEnoughCoins, AlreadyOwned, DoesNotFitPet }

    public sealed class ShopView
    {
        public ItemDef Item;
        public BuyCheck State;
        public FitResult Fit;          // giyilebilirlerde: gri + açıklama için
        public int LockedUntilLevel;   // havuç etkisi: "Seviye N'de açılır!"
    }

    /// <summary>Dükkan kuralları (FR-SHOP-1/2). Fiyat burada yalnızca gösterim içindir; gerçek tutar sunucuda kontrol edilir.</summary>
    public static class ShopRules
    {
        public static ShopView View(ItemDef item, int level, Wallet wallet, Inventory inv, PetSpeciesDef pet, int qty = 1)
        {
            var v = new ShopView { Item = item, Fit = CosmeticFit.Evaluate(pet, item) };
            if (level < item.Level) { v.State = BuyCheck.LevelLocked; v.LockedUntilLevel = item.Level; return v; }
            if (!item.IsConsumable && inv.Owns(item.Id)) { v.State = BuyCheck.AlreadyOwned; return v; }
            if (!v.Fit.Allowed) { v.State = BuyCheck.DoesNotFitPet; return v; }
            if (wallet.Available < item.Price * qty) { v.State = BuyCheck.NotEnoughCoins; return v; }
            v.State = BuyCheck.Ok;
            return v;
        }

        /// <summary>Satın al: cüzdanda bekleyen harcama + envantere ekleme. Sunucu reddederse Wallet.Reject + Inventory.Remove.</summary>
        public static BuyCheck Buy(ItemDef item, int qty, int level, Wallet wallet, Inventory inv, PetSpeciesDef pet,
            string txId, System.DateTime nowUtc, out PendingSpend spend)
        {
            spend = null;
            var v = View(item, level, wallet, inv, pet, qty);
            if (v.State != BuyCheck.Ok) return v.State;
            if (wallet.TrySpend(item.Id, qty, item.Price, txId, nowUtc, out spend) != SpendResult.Ok) return BuyCheck.NotEnoughCoins;
            inv.Add(item, qty);
            return BuyCheck.Ok;
        }
    }
}
