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
        private static readonly string[] Tabs = { ItemCategory.Food, ItemCategory.Cleaning, ItemCategory.Clothes, ItemCategory.Accessory, ItemCategory.Seed };
        private static string _tab = ItemCategory.Food;   // sayfalar arası hatırlanır

        private RectTransform _grid;
        private Text _coins;
        private Button[] _tabButtons;

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            _coins = Header(T("shop.title"));

            var tabs = Ui.Rect(Root, "Tabs", new Vector2(0.5f, 1f), new Vector2(1040f, 110f));
            tabs.pivot = new Vector2(0.5f, 1f);
            tabs.anchoredPosition = new Vector2(0f, -175f);
            _tabButtons = new Button[Tabs.Length];
            for (var i = 0; i < Tabs.Length; i++)
            {
                var cat = Tabs[i];
                _tabButtons[i] = Ui.Button(tabs, Th, T("shop.tab." + cat), new Vector2(0.1f + i * 0.2f, 0.5f), new Vector2(196f, 96f),
                    () => { _tab = cat; Fill(); }, cat == _tab, default, 32, false);
            }

            var area = Ui.Area(Root, "GridArea", Vector2.zero, Vector2.one);
            area.offsetMin = new Vector2(0f, NavHeight + 10f);
            area.offsetMax = new Vector2(0f, -300f);
            _grid = Ui.ScrollList(area, Vector2.zero, Vector2.one, 24f, 3, new Vector2(320f, 400f));

            NavBar(AppPage.Shop);
            App.Synced += OnSynced;
            Fill();
        }

        private void OnSynced(Logic.State.SyncReport r)
        {
            if (this == null) return;
            Fill();
        }

        private void Fill()
        {
            _coins.text = App.State.Wallet.Available.ToString();
            for (var i = 0; i < Tabs.Length; i++)
            {
                var on = Tabs[i] == _tab;
                _tabButtons[i].targetGraphic.color = on ? Th.Primary : Th.Secondary;
                _tabButtons[i].GetComponentInChildren<Text>().color = on ? Th.PrimaryText : Th.SecondaryText;
            }
            Ui.Clear(_grid);
            var pet = App.Data.Pet(App.State.PetId);
            var items = App.Data.Items.Where(i => i.Category == _tab && !i.Premium).OrderBy(i => i.Level).ThenBy(i => i.Price);
            foreach (var item in items)
                Card(ShopRules.View(item, App.Level, App.State.Wallet, App.State.Inventory, pet));
        }

        private void Card(ShopView v)
        {
            var item = v.Item;
            var go = new GameObject(item.Id, typeof(RectTransform));
            var card = (RectTransform)go.transform;
            card.SetParent(_grid, false);
            var locked = v.State == BuyCheck.LevelLocked;
            var noFit = v.State == BuyCheck.DoesNotFitPet;
            var bg = Ui.Panel(card, locked || noFit ? new Color(1f, 1f, 1f, 0.7f) : Th.Panel, Th.Radius);

            // yer tutucu simge: eşyanın rengiyle yuvarlak kare + baş harf
            var icon = Ui.Rect(card, "Icon", new Vector2(0.5f, 0.66f), new Vector2(190f, 190f));
            var col = item.IsWearable ? CosmeticModels.ColorOf(item.Id) : CategoryColor(item.Category);
            if (locked || noFit) col = Color.Lerp(col, Color.gray, 0.7f);
            Ui.Panel(icon, col, 40f).raycastTarget = false;
            Ui.Label(icon, item.Name.Substring(0, 1), Th.Font(96), Color.white, new Vector2(0.5f, 0.5f), new Vector2(190f, 190f), FontStyle.Bold);

            Ui.Label(card, item.Name, Th.Font(34), Th.Text, new Vector2(0.5f, 0.29f), new Vector2(300f, 90f), FontStyle.Bold);

            string bottom;
            var bottomColor = Theme.Hex("#5A3B00");
            switch (v.State)
            {
                case BuyCheck.LevelLocked: bottom = T("shop.locked", TurkishSuffix.Locative(v.LockedUntilLevel)); bottomColor = Th.SubtleText; break;
                case BuyCheck.AlreadyOwned: bottom = T("shop.owned"); bottomColor = Theme.Hex("#2E9E4F"); break;
                case BuyCheck.DoesNotFitPet: bottom = T("shop.not_fit"); bottomColor = Th.SubtleText; break;
                default: bottom = item.Price + " coin"; break;
            }
            Ui.Label(card, bottom, Th.Font(32), bottomColor, new Vector2(0.5f, 0.09f), new Vector2(300f, 60f), FontStyle.Bold);
            if (item.IsConsumable && App.State.Inventory.CountOf(item.Id) > 0)
            {
                var badge = Ui.Rect(card, "Count", new Vector2(0.86f, 0.9f), new Vector2(64f, 64f));
                Ui.Panel(badge, Th.Primary, 32f).raycastTarget = false;
                Ui.Label(badge, App.State.Inventory.CountOf(item.Id).ToString(), Th.Font(30), Color.white, new Vector2(0.5f, 0.5f), new Vector2(64f, 64f), FontStyle.Bold);
            }

            var btn = go.AddComponent<Button>();
            btn.targetGraphic = bg;
            btn.onClick.AddListener(() => OnTap(v));
            go.AddComponent<PressBounce>();
        }

        private static Color CategoryColor(string cat)
        {
            switch (cat)
            {
                case ItemCategory.Food: return Theme.Hex("#FF9F43");
                case ItemCategory.Cleaning: return Theme.Hex("#3DC9FF");
                case ItemCategory.Seed: return Theme.Hex("#8C5A3C");
                default: return Theme.Hex("#9B7BFF");
            }
        }

        private void OnTap(ShopView v)
        {
            var pet = App.Data.Pet(App.State.PetId);
            switch (v.State)
            {
                case BuyCheck.LevelLocked: Info(T("shop.locked", TurkishSuffix.Locative(v.LockedUntilLevel))); return;
                case BuyCheck.AlreadyOwned: Info(T("shop.already_owned")); return;
                case BuyCheck.DoesNotFitPet: Info(T(v.Fit.ReasonKey, TurkishSuffix.Genitive(App.State.PetName))); return;
                case BuyCheck.NotEnoughCoins: NotEnough(); return;
            }
            var root = Modal(560f, out var box);
            Ui.Label(box, T("shop.buy_confirm", v.Item.Name, v.Item.Price), Th.Font(52), Th.Text, new Vector2(0.5f, 0.72f), new Vector2(880f, 200f), FontStyle.Bold);
            Ui.Button(box, Th, T("shop.yes"), new Vector2(0.3f, 0.24f), new Vector2(360f, 130f), () =>
            {
                Destroy(root.gameObject);
                var r = ShopRules.Buy(v.Item, 1, App.Level, App.State.Wallet, App.State.Inventory, pet, Guid.NewGuid().ToString("N"), App.UtcNow, out _);
                if (r == BuyCheck.Ok)
                {
                    App.Save();
                    Info(T("shop.bought", v.Item.Name));
                    Fill();
                    _ = App.SyncNow();
                }
                else if (r == BuyCheck.NotEnoughCoins) NotEnough();
                else Fill();
            }, true, default, 52, false);
            Ui.Button(box, Th, T("shop.no"), new Vector2(0.7f, 0.24f), new Vector2(360f, 130f), () => Destroy(root.gameObject), false, default, 52, false);
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
        }
    }
}
