using System;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Data;
using Pofi.Logic.Shop;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Dükkan (FR-SHOP-1..3): kategori sekmeleri, eşya ızgarası. Kilitli eşya "Seviye N'de açılır!" (havuç etkisi),
    /// pete uymayan gri ve nedenli. Satın alma önce yerelde bekleyen harcama olur, senkronla sunucuya gider.
    /// </summary>
    public sealed class ShopScreen : ScreenBase
    {
        private static readonly string[] Tabs = { ItemCategory.Food, ItemCategory.Cleaning, ItemCategory.Clothes, ItemCategory.Accessory, ItemCategory.Seed, ItemCategory.Home };
        private static readonly string[] TabIcons = { "food_apple", "clean_soap", "shirt_stripes", "glasses_round", "seed_carrot", "home_lamp" };
        private const int PerPage = 5;

        /// <summary>"Ev" sekmesi ev eşyalarıyla birlikte dekorları da gösterir.</summary>
        private static bool InTab(string category, string tab) => category == tab || (tab == ItemCategory.Home && category == ItemCategory.Decor);
        private static string _tab = ItemCategory.Food;   // sayfalar arası hatırlanır

        private RectTransform _shelf;
        private Text _coins;
        private Button[] _tabButtons;
        private SpeechBubble _bubble;
        private int _page, _selected;

        protected override void Build()
        {
            // Sahne: pet dükkân tezgâhının önünde, ürünler tezgâhın üstünde süzülür (14 Ekim 2026 taslağı)
            var def = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = false;
            PetCamera(0.5f, 0.05f, 0.42f);
            App.Stage.ShowPet(def, App.Growth, App.State.Inventory.Equipped.Values);
            App.Stage.SetBackdrop("b_shop", 6f, 3.4f);

            Candy.Caption(Root, T("shop.title"), 64, new Vector2(0.5f, 1f), new Vector2(600f, 90f), new Vector2(0f, -66f));
            _coins = Candy.Badge(Root, "ui_coin", "", new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-30f, -24f), 84f, 250f);

            _tabButtons = new Button[Tabs.Length];
            for (var i = 0; i < Tabs.Length; i++)
            {
                var cat = Tabs[i];
                _tabButtons[i] = Candy.Round(Root, Candy.White, TabIcons[i], 108f, new Vector2(0f, 1f), new Vector2(96f, -96f - i * 132f),
                    () => { _tab = cat; _page = 0; _selected = 0; Fill(); });
            }
            _shelf = Ui.Fill(Root, "Shelf");
            _bubble = Bubble(new Vector2(0.5f, 0.9f));
            NavBar(AppPage.Shop);
            App.Synced += OnSynced;
            Fill();
        }

        private void OnSynced(Logic.State.SyncReport r)
        {
            if (this == null) return;
            Fill();
        }

        private System.Collections.Generic.List<ShopView> Views()
        {
            var pet = App.Data.Pet(App.State.PetId);
            return App.Data.Items.Where(i => InTab(i.Category, _tab) && !i.Premium).OrderBy(i => i.Level).ThenBy(i => i.Price)
                .Select(i => ShopRules.View(i, App.Level, App.State.Wallet, App.State.Inventory, pet)).ToList();
        }

        private void Fill()
        {
            _coins.text = App.State.Wallet.Available.ToString();
            for (var i = 0; i < Tabs.Length; i++)
                _tabButtons[i].targetGraphic.color = Tabs[i] == _tab ? Candy.Orange : Candy.White;
            Ui.Clear(_shelf);
            var views = Views();
            var pages = Mathf.Max(1, (views.Count + PerPage - 1) / PerPage);
            _page = Mathf.Clamp(_page, 0, pages - 1);
            var start = _page * PerPage;
            var count = Mathf.Min(PerPage, views.Count - start);
            if (count <= 0) { Preview(null); return; }
            _selected = Mathf.Clamp(_selected, 0, count - 1);

            // yay biçiminde süzülen ürün baloncukları
            for (var k = 0; k < count; k++)
            {
                var v = views[start + k];
                var sel = k == _selected;
                var off = k - (count - 1) / 2f;
                var pos = new Vector2(off * 270f, 250f - off * off * 34f);
                var size = sel ? 210f : 160f;
                var idx = k;
                var b = Candy.Round(_shelf, sel ? new Color(1f, 0.93f, 0.6f) : Candy.White, v.Item.Id, size, new Vector2(0.5f, 0.5f), pos, () => { _selected = idx; Fill(); });
                var dim = v.State == BuyCheck.LevelLocked || v.State == BuyCheck.DoesNotFitPet;
                if (dim) foreach (var img in b.GetComponentsInChildren<Image>()) img.color *= new Color(1f, 1f, 1f, 0.55f);
                // altında fiyat / durum
                var tag = v.State == BuyCheck.LevelLocked ? T("shop.level_short", v.LockedUntilLevel)
                    : v.State == BuyCheck.AlreadyOwned ? T("shop.owned") : v.Item.Price.ToString();
                Candy.Badge(b.transform, v.State == BuyCheck.AlreadyOwned || v.State == BuyCheck.LevelLocked ? "ui_star" : "ui_coin", tag,
                    new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, 6f), 56f, 170f);
                if (v.Item.IsConsumable && App.State.Inventory.CountOf(v.Item.Id) > 0)
                    Candy.Count(b.transform).text = App.State.Inventory.CountOf(v.Item.Id).ToString();
            }
            if (pages > 1)
            {
                Candy.Pill(_shelf, Candy.White, "<", new Vector2(0.5f, 0.5f), new Vector2(110f, 110f), new Vector2(-780f, 160f), () => { _page = (_page + pages - 1) % pages; _selected = 0; Fill(); }, null, 56);
                Candy.Pill(_shelf, Candy.White, ">", new Vector2(0.5f, 0.5f), new Vector2(110f, 110f), new Vector2(780f, 160f), () => { _page = (_page + 1) % pages; _selected = 0; Fill(); }, null, 56);
            }

            // seçilen ürün: adı + Al düğmesi
            var cur = views[start + _selected];
            Candy.Caption(_shelf, cur.Item.Name, 48, new Vector2(0.5f, 0.5f), new Vector2(900f, 70f), new Vector2(0f, 40f));
            var label = cur.State == BuyCheck.AlreadyOwned ? T("shop.owned") : T("shop.buy", cur.Item.Price);
            Candy.Pill(_shelf, cur.State == BuyCheck.Ok ? Candy.Green : Candy.White, label, new Vector2(0.5f, 0.5f), new Vector2(320f, 120f), new Vector2(0f, -60f), () => OnTap(cur), "ui_coin", 50);
            Preview(cur);
        }

        /// <summary>Giyilebilir eşya seçilince pette önizleme (henüz alınmadıysa da).</summary>
        private void Preview(ShopView v)
        {
            var eq = App.State.Inventory.Equipped;
            if (v == null || !v.Item.IsWearable || v.State == BuyCheck.DoesNotFitPet) { App.Stage.SetCosmetics(eq.Values); return; }
            var tryOn = eq.Where(kv => kv.Key != v.Item.Slot).Select(kv => kv.Value).Append(v.Item.Id).ToList();
            App.Stage.SetCosmetics(tryOn);
        }

        private void OnTap(ShopView v)
        {
            var pet = App.Data.Pet(App.State.PetId);
            switch (v.State)
            {
                case BuyCheck.LevelLocked: _bubble.Say(T("shop.locked", TurkishSuffix.Locative(v.LockedUntilLevel))); return;
                case BuyCheck.AlreadyOwned: _bubble.Say(v.Item.IsWearable ? T("shop.tap_pet_to_wear") : T("shop.already_owned")); return;
                case BuyCheck.DoesNotFitPet: _bubble.Say(T(v.Fit.ReasonKey, TurkishSuffix.Genitive(App.State.PetName))); return;
                case BuyCheck.NotEnoughCoins: NotEnough(); return;
            }
            var r = ShopRules.Buy(v.Item, 1, App.Level, App.State.Wallet, App.State.Inventory, pet, Guid.NewGuid().ToString("N"), App.UtcNow, out _);
            if (r == BuyCheck.Ok)
            {
                App.Save();
                App.Stage.Hop();
                Audio.Sfx.Play(Audio.SfxKind.Coin);
                _bubble.Say(v.Item.IsWearable ? T("shop.bought_wear", v.Item.Name) : T("shop.bought", v.Item.Name));
                if (v.Item.IsWearable) { App.State.Inventory.TryEquip(pet, v.Item); App.Save(); }
                Fill();
                _ = App.SyncNow();
            }
            else if (r == BuyCheck.NotEnoughCoins) NotEnough();
            else Fill();
        }

        private void NotEnough()
        {
            var root = Modal(560f, out var box);
            Ui.Label(box, T("shop.not_enough_coins"), Th.Font(48), Th.Text, new Vector2(0.5f, 0.72f), new Vector2(860f, 200f), FontStyle.Bold);
            Ui.Button(box, Th, T("shop.go_to_tasks"), new Vector2(0.5f, 0.3f), new Vector2(640f, 130f), () => App.Open(AppPage.Tasks));
            Ui.Button(box, Th, "X", new Vector2(0.92f, 0.9f), new Vector2(90f, 90f), () => Destroy(root.gameObject), false, default, 44);
        }

        private void Info(string text)
        {
            var root = Modal(420f, out var box);
            Ui.Label(box, text, Th.Font(46), Th.Text, new Vector2(0.5f, 0.64f), new Vector2(860f, 220f), FontStyle.Bold);
            Ui.Button(box, Th, T("common.ok"), new Vector2(0.5f, 0.2f), new Vector2(360f, 110f), () => Destroy(root.gameObject), false, default, 44);
        }

        private void OnDestroy()
        {
            if (App != null) App.Synced -= OnSynced;
            if (App != null && App.Stage != null) App.Stage.SetBackdrop(null);
        }
    }
}
