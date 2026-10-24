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
        /// <summary>Gerçek ödüller sekmesi (Ö7): ebeveynin koyduğu ödüller coin'le istenir, ebeveyn verince coin düşer.</summary>
        private const string RealTab = "real";
        private static readonly string[] Tabs = { ItemCategory.Food, ItemCategory.Cleaning, ItemCategory.Clothes, ItemCategory.Accessory, ItemCategory.Seed, ItemCategory.Home, RealTab };
        private static readonly string[] TabIcons = { "food_apple", "clean_soap", "shirt_stripes", "glasses_round", "seed_carrot", "home_lamp", "ui_gift" };
        private const int PerPage = 10;   // E2a: 5 × 2 ızgara

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
            // E2a (23 Ekim 2026): Okti solda, tezgâh ortada görünür; ürünler tezgâhın altında çanta baloncuğunun ikizi küçük ızgarada
            PetCamera(0.2f, 0.05f, 0.5f);
            App.Stage.ShowPet(def, App.Growth, App.State.Inventory.Equipped.Values);
            App.Stage.SetBackdrop("b_shop", 6f, 3.4f);
            if (App.Stage.Backdrop != null)   // K: dükkâncı Kıskaç tezgâhın yanında
                World.Resident3D.Create(App.Stage.Backdrop, "kiskac", "res_kiskac", new Vector3(0.7f, 0.9f, 3.6f), 1.15f, 180f, null, null);   // tezgâhın arkasında, başı ve kabuğu tezgâhın üstünde

            Candy.Caption(Root, T("shop.title"), 64, new Vector2(0.5f, 1f), new Vector2(600f, 90f), new Vector2(0f, -66f));
            _coins = Candy.Badge(Root, "ui_coin", "", new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(CoinRight, -24f), 84f, 250f);

            _tabButtons = new Button[Tabs.Length];
            if (_tab == RealTab && !RewardsOpen) _tab = ItemCategory.Food;
            // özellik yeni açıldıysa dükkân doğrudan Gerçek ödüller sekmesiyle açılır (tanıtım kartı Fill'den sonra)
            if (RewardsOpen && !App.State.SeenTips.Contains(RewardsIntroFlag) && !Guide.Is(App.State, App.Level, "shop")) _tab = RealTab;
            for (var i = 0; i < Tabs.Length; i++)
            {
                var cat = Tabs[i];
                _tabButtons[i] = Candy.Round(Root, Candy.White, TabIcons[i], 108f, new Vector2(0f, 1f), new Vector2(96f, -96f - i * 118f),
                    () => OpenTab(cat));
            }
            // Gerçek ödüller birkaç seviye sonra açılır (kullanıcı GB17-13): kilitliyken sekme soluk, dokununca hangi seviyede açılacağı
            if (!RewardsOpen) foreach (var img in _tabButtons[Tabs.Length - 1].GetComponentsInChildren<Image>()) img.color *= new Color(1f, 1f, 1f, 0.45f);
            _shelf = Ui.Fill(Root, "Shelf");
            _bubble = Bubble(new Vector2(0.5f, 0.9f));
            NavBar(AppPage.Shop);
            App.Synced += OnSynced;
            Fill();
            if (_tab == RealTab) { _ = RefreshRewards(); if (!App.State.SeenTips.Contains(RewardsIntroFlag)) RewardsIntro(); }
            if (Guide.Is(App.State, App.Level, "shop")) GuideFirstWear();
            else if (Onboarding.Pending(App.State, Onboarding.Shop))
                _coach = Coach.Show(Root, Onboarding.Shop, T("tip.shop"), TipGesture.Tap, () => new Vector2(Screen.width * 0.42f, Screen.height * 0.26f));   // ızgaranın ilk ürünü
        }

        private RectTransform _buyBtn;

        public const string RewardsUnlock = "real_rewards", RewardsIntroFlag = "rewards_intro";
        private bool RewardsOpen => App.Levels.IsUnlocked(RewardsUnlock, App.Level);

        private void OpenTab(string cat)
        {
            if (cat == RealTab && !RewardsOpen) { _bubble.Say(T("rewards.locked", App.Levels.UnlockLevel(RewardsUnlock))); return; }
            _tab = cat; _page = 0; _selected = 0; Fill();
            if (cat != RealTab) return;
            _ = RefreshRewards();
            if (!App.State.SeenTips.Contains(RewardsIntroFlag)) RewardsIntro();
        }

        /// <summary>
        /// Gerçek ödüllerin ilk açılışı (kullanıcı GB17-13): üç adımlı kısa kart (görev → Güneş Taşı → ödül seç → İste), sonra el
        /// ilk ödüle ve İste'ye dokunur. İlk istek gidince "ilk isteğin ailene gitti" (ebeveyne de ilk istek olduğu bildirilir).
        /// </summary>
        private void RewardsIntro()
        {
            var root = Modal(640f, out var box);
            ModalTitle(box, T("rewards.intro_title"));
            var rows = new[] { ("ui_board", "rewards.intro_1"), ("ui_gift", "rewards.intro_2"), ("ui_sunstone", "rewards.intro_3") };
            for (var i = 0; i < rows.Length; i++)
            {
                var y = 0.72f - i * 0.19f;
                Ui.Label(box, (i + 1).ToString(), Th.Font(56), Theme.Hex("#C26A08"), new Vector2(0.1f, y), new Vector2(80f, 90f), FontStyle.Bold);
                Ui.IconImage(box, rows[i].Item1, new Vector2(0.21f, y), 96f);
                Ui.Label(box, T(rows[i].Item2), Th.Font(38), Th.Text, new Vector2(0.62f, y), new Vector2(700f, 110f), FontStyle.Bold, TextAnchor.MiddleLeft);
            }
            var say = string.Join(" ", rows.Select(r => T(r.Item2)));
            Audio.Voice.Say(say);
            Ui.Button(box, Th, T("rewards.intro_ok"), new Vector2(0.5f, 0.1f), new Vector2(420f, 120f), () =>
            {
                Audio.Voice.StopIf(say);
                Destroy(root.gameObject);
                App.State.SeenTips.Add(RewardsIntroFlag); App.Save();
                if (_coach == null && (App.State.Rewards?.Rewards.Count ?? 0) > 0)
                    _coach = Coach.Show(Root, "rewards_pick", T("rewards.pick"), TipGesture.Tap, () => new Vector2(Screen.width * 0.5f, Screen.height * 0.72f), null, 3, null, null, T("rewards.pick"));
            });
        }
        /// <summary>
        /// Rehberin dükkân adımı (kullanıcı GB17-4): hoş geldin coin'ine yeten ilk aksesuar seçili gelir, Okti'de denenir; el "Al"
        /// düğmesine dokunur. Alınca takılır (giydir adımı da biter) ve dükkânı kullanma alışkanlığı başlar.
        /// </summary>
        private void GuideFirstWear()
        {
            var item = Guide.FirstWear(App.Data, App.State.Wallet.Available);
            if (item == null) return;
            ShopTipDone();
            _tab = Tabs.Contains(item.Category) ? item.Category : ItemCategory.Accessory;
            var views = Views();
            var idx = views.FindIndex(v => v.Item.Id == item.Id);
            if (idx < 0) return;
            _page = idx / PerPage; _selected = idx % PerPage;
            Fill();
            var say = T("guide.shop_pick", item.Name);
            _coach = Coach.Show(Root, "guide_shop", say, TipGesture.Tap, () => _buyBtn != null ? RectTransformUtility.WorldToScreenPoint(null, _buyBtn.position) : new Vector2(Screen.width * 0.7f, Screen.height * 0.2f),
                null, 99, (Guide.DoneCount(App.State) + 1) + "/" + Guide.Steps.Count, null, say);
        }

        private Coach _coach;

        private void ShopTipDone()
        {
            if (!Onboarding.Pending(App.State, Onboarding.Shop)) return;
            Onboarding.Done(App.State, Onboarding.Shop); App.Save();
            if (_coach != null) { _coach.Done(); _coach = null; }
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
            if (_tab == RealTab) { FillRewards(); return; }
            var views = Views();
            var pages = Mathf.Max(1, (views.Count + PerPage - 1) / PerPage);
            _page = Mathf.Clamp(_page, 0, pages - 1);
            var start = _page * PerPage;
            var count = Mathf.Min(PerPage, views.Count - start);
            if (count <= 0) { Preview(null); return; }
            _selected = Mathf.Clamp(_selected, 0, count - 1);

            // E2a tezgâh baloncuğu: krem kart içinde 5 × 2 ızgara; her üründe küçük fiyat etiketi. Seç → tek yeşil "Al"
            const float tile = 136f, gap = 14f;
            var cols = Mathf.Min(5, count); var rows = Mathf.CeilToInt(count / (float)cols);
            var w = cols * tile + (cols - 1) * gap + 48f; var h = rows * tile + (rows - 1) * gap + 48f + 20f;
            // dar ekranda (iPad 4:3) kart ve "Al" birlikte küçülür: "Al" sağ kenardan taşıyordu, sola kaysa Okti'ye binerdi (tasarım turu 24 Ekim 2026)
            var sw = Width;
            var fit = Mathf.Clamp((sw - 64f - 0.58f * sw) / (w * 0.5f + 190f + 150f), 0.6f, 1f);   // 64: hap gölgesi + kenar payı (iPad'de kenara 4 px kalıyordu)
            var card = Ui.Rect(_shelf, "Counter", new Vector2(0.58f, 0f), new Vector2(w, h), new Vector2(0f, 60f + h * 0.5f * fit));
            card.localScale = new Vector3(fit, fit, 1f);
            var cimg = card.gameObject.AddComponent<Image>();
            if (Skin.Card != null) { Skin.Apply(cimg, Skin.Card, Mathf.Min(h, 360f)); cimg.color = Color.white; }
            else { cimg.sprite = Ui.Rounded; cimg.type = Image.Type.Sliced; cimg.color = new Color(1f, 0.96f, 0.86f); }
            card.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -8f);
            for (var k = 0; k < count; k++)
            {
                var v = views[start + k];
                var sel = k == _selected;
                var c = k % cols; var r = k / cols;
                var pos = new Vector2(-w * 0.5f + 24f + c * (tile + gap) + tile * 0.5f, h * 0.5f - 24f - r * (tile + gap) - tile * 0.5f);
                var idx = k;
                var cell = Ui.Rect(card, "Item " + v.Item.Id, new Vector2(0.5f, 0.5f), new Vector2(tile, tile), pos);
                var bg = cell.gameObject.AddComponent<Image>(); bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced;
                bg.color = sel ? new Color(1f, 0.9f, 0.55f) : new Color(1f, 1f, 1f, 0.85f);
                if (sel) { var o = cell.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.95f, 0.65f, 0.12f); o.effectDistance = new Vector2(4f, -4f); }
                Ui.IconImage(cell, v.Item.Id, new Vector2(0.5f, 0.6f), 96f);
                var dim = v.State == BuyCheck.LevelLocked || v.State == BuyCheck.DoesNotFitPet;
                if (dim) foreach (var img in cell.GetComponentsInChildren<Image>()) img.color *= new Color(1f, 1f, 1f, 0.5f);
                // küçük fiyat / durum etiketi
                var tag = v.State == BuyCheck.LevelLocked ? T("shop.level_short", v.LockedUntilLevel)
                    : v.State == BuyCheck.AlreadyOwned ? T("shop.owned") : v.Item.Price.ToString();
                Candy.Badge(cell, v.State == BuyCheck.AlreadyOwned || v.State == BuyCheck.LevelLocked ? "ui_star" : "ui_coin", tag,
                    new Vector2(0.5f, 0f), new Vector2(0.5f, 0.5f), new Vector2(0f, 4f), 44f, 118f);
                if (v.Item.IsConsumable && App.State.Inventory.CountOf(v.Item.Id) > 0)
                    Candy.Count(cell).text = App.State.Inventory.CountOf(v.Item.Id).ToString();
                var btn = cell.gameObject.AddComponent<Button>(); btn.targetGraphic = bg;
                btn.onClick.AddListener(() => { Audio.Sfx.Play(Audio.SfxKind.Tap); _selected = idx; ShopTipDone(); Fill(); });
                cell.gameObject.AddComponent<PressBounce>();
                LongPressInfo.Add(cell.gameObject, v.Item.Name);
            }
            if (pages > 1)
            {
                Candy.Pill(card, Candy.White, "<", new Vector2(0f, 0.5f), new Vector2(84f, 84f), new Vector2(-50f, 0f), () => { _page = (_page + pages - 1) % pages; _selected = 0; Fill(); }, null, 44);
                Candy.Pill(card, Candy.White, ">", new Vector2(1f, 0.5f), new Vector2(84f, 84f), new Vector2(50f, 0f), () => { _page = (_page + 1) % pages; _selected = 0; Fill(); }, null, 44);
            }

            // seçilen ürünün adı kartın üstünde; tek yeşil "Al" kartın sağında (alınamıyorsa soluk)
            var cur = views[start + _selected];
            Candy.Caption(card, cur.Item.Name, 44, new Vector2(0.5f, 1f), new Vector2(w, 64f), new Vector2(0f, 40f));
            var label = cur.State == BuyCheck.AlreadyOwned ? T("shop.owned") : T("shop.buy", cur.Item.Price);
            var buy = Candy.Pill(_shelf, Candy.Green, label, new Vector2(0.58f, 0f), new Vector2(300f, 116f), new Vector2((w * 0.5f + 190f) * fit, 60f + 58f * fit), () => OnTap(cur), "ui_coin", 46);
            _buyBtn = (RectTransform)buy.transform;
            _buyBtn.localScale = new Vector3(fit, fit, 1f);
            if (cur.State != BuyCheck.Ok) buy.targetGraphic.color = new Color(0.72f, 0.72f, 0.72f, 0.9f);
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
                if (v.Item.IsWearable)
                {
                    App.State.Inventory.TryEquip(pet, v.Item); App.Save();
                    App.RecordActivity("item_equipped");   // alınan aksesuar takılı gelir: rehberin giydir adımı da biter
                    App.RecordActivity("wear_bought");
                }
                if (_coach != null && _coach.Id == "guide_shop") { _coach.Done(); _coach = null; }
                App.RecordActivity("item_bought");
                Fill();
                _ = App.SyncNow();
            }
            else if (r == BuyCheck.NotEnoughCoins) NotEnough();
            else Fill();
        }

        // ------------------------------------------------------------ gerçek ödüller (Güneş Taşı; ParentApp ile ortak sözleşme)
        // Ebeveyn listeyi ve fiyatı belirler, çocuk taşı yetince ister, ebeveyn onaylar. Aynı anda tek bekleyen istek.
        // "Değiş tokuş" ödülünde (ör. 1 taş = 10 dk) kaç kez istendiği seçilir. Yetmeyen ödül "hedef" yapılır: "N taş kaldı".

        private bool _busy;
        private int _qty = 1;
        private string _qtyFor;

        private static string RewardIcon(string icon)
        {
            switch (icon)
            {
                case "park": case "outdoor": case "trip": return "decor_palm";
                case "movie": case "tv": case "tablet": case "screen": case "game": return "act_play";
                case "treat": case "icecream": case "food": return "food_icecream";
                case "book": case "read": return "home_bookshelf";
                case "toy": return "decor_sandcastle";
                case "money": case "coin": return "ui_coin";
                case "star": return "ui_star";
                default: return "ui_gift";
            }
        }

        private async System.Threading.Tasks.Task RefreshRewards()
        {
            if (App.Sync == null) return;
            await App.SyncNow();   // senkron ödülleri, istekleri ve taş bakiyesini getirir (OnSynced → Fill)
        }

        private void FillRewards()
        {
            Preview(null);
            var book = App.State.Rewards ?? new Logic.Rewards.RewardBook();
            Candy.Badge(_shelf, "ui_sunstone", T("rewards.stones", book.Spendable), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -150f), 70f, 330f);
            if (App.Rewards == null || book.Rewards.Count == 0)
            {
                Candy.Caption(_shelf, T("rewards.empty"), 44, new Vector2(0.5f, 0.5f), new Vector2(1100f, 200f), new Vector2(0f, 120f));
                return;
            }
            var list = book.Rewards;
            var pages = Mathf.Max(1, (list.Count + PerPage - 1) / PerPage);
            _page = Mathf.Clamp(_page, 0, pages - 1);
            var start = _page * PerPage;
            var count = Mathf.Min(PerPage, list.Count - start);
            _selected = Mathf.Clamp(_selected, 0, count - 1);
            var pending = book.Pending;
            for (var k = 0; k < count; k++)
            {
                var rw = list[start + k];
                var sel = k == _selected;
                var off = k - (count - 1) / 2f;
                var pos = new Vector2(off * 270f, 250f - off * off * 34f);
                var idx = k;
                var b = Candy.Round(_shelf, sel ? new Color(1f, 0.93f, 0.6f) : Candy.White, RewardIcon(rw.Icon), sel ? 210f : 160f, new Vector2(0.5f, 0.5f), pos,
                    () => { _selected = idx; Fill(); });
                var asked = pending != null && pending.RewardId == rw.Id;
                var tag = asked ? T("rewards.asked_short") : rw.IsExchange ? Logic.Rewards.RewardText.Rate(rw) : rw.Cost.ToString();
                Candy.Badge(b.transform, asked ? "ui_check" : "ui_sunstone", tag, new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, 6f), 56f, rw.IsExchange ? 260f : 170f);
                if (book.GoalId == rw.Id) Candy.Count(b.transform).text = "★";
            }
            if (pages > 1)
            {
                Candy.Pill(_shelf, Candy.White, "<", new Vector2(0.5f, 0.5f), new Vector2(110f, 110f), new Vector2(-780f, 160f), () => { _page = (_page + pages - 1) % pages; _selected = 0; Fill(); }, null, 56);
                Candy.Pill(_shelf, Candy.White, ">", new Vector2(0.5f, 0.5f), new Vector2(110f, 110f), new Vector2(780f, 160f), () => { _page = (_page + 1) % pages; _selected = 0; Fill(); }, null, 56);
            }
            var cur = list[start + _selected];
            if (_qtyFor != cur.Id) { _qtyFor = cur.Id; _qty = 1; }
            _qty = Mathf.Clamp(_qty, 1, cur.MaxQuantity);
            var total = cur.Cost * _qty;
            var title = cur.IsExchange ? Logic.Rewards.RewardText.Label(cur.Title, cur.Unit, cur.UnitAmount * _qty) : cur.Title;
            Candy.Caption(_shelf, title, 48, new Vector2(0.5f, 0.5f), new Vector2(1000f, 70f), new Vector2(0f, 40f));

            if (pending != null && pending.RewardId == cur.Id)
            {
                Candy.Pill(_shelf, Candy.White, T("rewards.cancel"), new Vector2(0.5f, 0.5f), new Vector2(420f, 110f), new Vector2(0f, -60f), () => _ = Cancel(pending), null, 44);
                Candy.Caption(_shelf, T("rewards.waiting"), 30, new Vector2(0.5f, 0.5f), new Vector2(1100f, 60f), new Vector2(0f, -150f));
                return;
            }
            if (cur.IsExchange)
            {
                // kaç kez: − adet +
                Candy.Pill(_shelf, Candy.White, "−", new Vector2(0.5f, 0.5f), new Vector2(100f, 100f), new Vector2(-330f, -60f), () => { _qty = Mathf.Max(1, _qty - 1); Fill(); }, null, 56);
                Candy.Pill(_shelf, Candy.White, "+", new Vector2(0.5f, 0.5f), new Vector2(100f, 100f), new Vector2(330f, -60f), () => { _qty = Mathf.Min(cur.MaxQuantity, _qty + 1); Fill(); }, null, 56);
            }
            var enough = book.Spendable >= total;
            if (enough)
                Candy.Pill(_shelf, pending == null ? Candy.Green : Candy.White, T("rewards.ask", total), new Vector2(0.5f, 0.5f), new Vector2(420f, 120f), new Vector2(0f, -60f),
                    () => _ = Ask(cur, _qty), "ui_sunstone", 50);
            else
                Candy.Pill(_shelf, book.GoalId == cur.Id ? new Color(1f, 0.93f, 0.6f) : Candy.White, T(book.GoalId == cur.Id ? "rewards.goal_set" : "rewards.make_goal"),
                    new Vector2(0.5f, 0.5f), new Vector2(420f, 120f), new Vector2(0f, -60f), () => ToggleGoal(cur), "ui_star", 44);
            var line = pending != null ? T("rewards.one_at_a_time", Logic.Rewards.RewardText.Label(pending))
                : enough ? T("rewards.how") : T("rewards.left", book.StonesLeft(cur, _qty));
            Candy.Caption(_shelf, line, 30, new Vector2(0.5f, 0.5f), new Vector2(1100f, 60f), new Vector2(0f, -150f));
            var goal = book.Goal;
            if (goal != null && goal.Id != cur.Id)
                Candy.Caption(_shelf, T("rewards.goal_line", goal.Title, book.StonesLeft(goal)), 28, new Vector2(0.5f, 0.5f), new Vector2(1100f, 50f), new Vector2(0f, -200f));
        }

        private void ToggleGoal(Logic.Rewards.RealReward rw)
        {
            var book = App.State.Rewards;
            book.GoalId = book.GoalId == rw.Id ? null : rw.Id;
            App.Save();
            _bubble.Say(book.GoalId == null ? T("rewards.goal_off") : T("rewards.goal_on", book.StonesLeft(rw)));
            Fill();
        }

        private async System.Threading.Tasks.Task Ask(Logic.Rewards.RealReward rw, int quantity)
        {
            if (_busy || App.Rewards == null) return;
            var book = App.State.Rewards;
            if (!book.CanRequestMore) { _bubble.Say(T("rewards.one_at_a_time", Logic.Rewards.RewardText.Label(book.Pending))); return; }
            if (book.Spendable < rw.Cost * quantity) { _bubble.Say(T("rewards.left", book.StonesLeft(rw, quantity))); return; }
            _busy = true;
            try
            {
                // sunucu aynı ödül için bekleyen isteği geri döndürür: yanıt kaybolup tekrar dokunulsa da ikinci istek açılmaz
                var r = await App.Rewards.RequestAsync(rw.Id, quantity);
                if (this == null) return;
                if (r.Ok)
                {
                    Audio.Sfx.Play(Audio.SfxKind.Coin);
                    App.Stage.Hop();
                    if (_coach != null && _coach.Id == "rewards_pick") { _coach.Done(); _coach = null; }
                    var first = r.First || !App.State.SeenTips.Contains("rewards_first_sent");
                    _bubble.Say(first ? T("rewards.first_sent") : T("rewards.asked", rw.Title));
                    if (first) { App.State.SeenTips.Add("rewards_first_sent"); StarSparkles.Around(Root, new Vector2(0.5f, 0.6f), new Vector2(0.2f, 0.15f), 12, 5); }
                    if (book.GoalId == rw.Id) book.GoalId = null;
                    App.RecordActivity("reward_requested");
                }
                else _bubble.Say(T(r.Error == "not_enough_stones" ? "rewards.not_enough_short"
                    : r.Error == "too_many_requests" ? "rewards.too_many"
                    : r.Error == "premium_required" ? "rewards.later"
                    : r.Error == Logic.Rewards.RewardReply.Network ? "rewards.offline" : "rewards.failed"));
                await App.SyncNow();   // _busy senkron bitene kadar açık: hızlı ikinci dokunuş ikinci istek açmaz
            }
            finally { _busy = false; }
        }

        private async System.Threading.Tasks.Task Cancel(Logic.Rewards.RewardRequest q)
        {
            if (_busy || App.Rewards == null) return;
            _busy = true;
            try
            {
                var r = await App.Rewards.CancelAsync(q.Id);
                if (this == null) return;
                _bubble.Say(T(r.Ok ? "rewards.cancelled" : r.Error == Logic.Rewards.RewardReply.Network ? "rewards.offline" : "rewards.failed"));
                await App.SyncNow();
            }
            finally { _busy = false; }
        }

        private void NotEnough()
        {
            var root = Modal(560f, out var box);
            Ui.Label(box, T("shop.not_enough_coins"), Th.Font(48), Th.Text, new Vector2(0.5f, 0.72f), new Vector2(860f, 200f), FontStyle.Bold);
            Ui.Button(box, Th, T("shop.go_to_tasks"), new Vector2(0.5f, 0.3f), new Vector2(640f, 130f), () => App.Open(AppPage.Tasks));
            ModalClose(box, () => Destroy(root.gameObject));
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
