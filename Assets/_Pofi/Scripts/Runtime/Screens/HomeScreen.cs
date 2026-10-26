using System.Collections.Generic;
using System;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Meta;
using Pofi.Logic.Pet;
using Pofi.Logic.Progression;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Ev: pet, 4 gösterge (zamanla yavaşça azalır), bakım düğmeleri, coin ve seviye.
    /// Çıkış ebeveyn sorusunun arkasında (FR-SET-1).
    /// </summary>
    public sealed class HomeScreen : ScreenBase
    {
        private static readonly StatKind[] Kinds = { StatKind.Fullness, StatKind.Cleanliness, StatKind.Happiness, StatKind.Home };
        private static readonly string[] StatKeys = { "stat.fullness", "stat.cleanliness", "stat.happiness", "stat.home" };
        private RectTransform _tidyBtn;
        private readonly RectTransform[] _careBtns = new RectTransform[4];   // Besle, Yıka, Oyna, Topla (gösterge sırasıyla aynı)
        private Coach _coach;
        private static readonly string[] GaugeIcons = { "food_apple", "clean_soap", "ui_heart", "home_bed" };
        private Text _coins, _feedCount, _washCount;
        private GoldProfile _prof;
        private Image _xpBar;
        private SpeechBubble _bubble;
        private float _tick, _idle;
        private bool _night;

        protected override void Build()
        {
            var def = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = true;
            PetCamera(0.5f, 0.18f, 0.86f, World.PetModels.RealHeight * World.PetModels.StageScale(Logic.Progression.GrowthStage.Yetiskin));   // yatay: pet ortada; çerçeve yetişkine göre, yavru daha küçük görünür
            App.Stage.ShowPet(def, App.Growth, App.State.Inventory.Equipped.Values);
            App.Stage.SetHomeItems(App.State.Home, App.Levels.IsUnlocked("home_expansion", App.Level));
            App.RecordActivity("home_entered");
            App.Stage.SetAmbient(true);

            // Sahne üstü (14 Ekim 2026 kararı): sol üst rozet + gösterge halkaları, sağ üst coin ve evin düğmeleri, sağ alt bakım
            // adayla aynı 3B pet kartı ve coin göstergesi
            // Altın Atölye (adayla aynı, kullanıcı 24 Ekim 2026): sol üst profil, sağ üst coin hapı, çerçevesiz 3B simge düğmeler
            _prof = GoldProfile.Build(Root, App.State.PetId, GaugeIcons, null);
            _coins = GoldKit.CurrencyPill(Root, "ui_coin", new Vector2(1f, 1f), new Vector2(CoinRight - 120f * GoldKit.K, -(24f + 24f) * GoldKit.K));

            var row = new List<(string key, string icon, string ex, System.Action act)>
                { ("home.daily", "ui_star", "#C26A08", () => QuestPanel()), ("album.button", "ui_album", "#7A4A12", () => App.Open(AppPage.Album)) };
            if (App.Levels.IsUnlocked("home_decor", App.Level)) row.Add(("decor.button", "home_lamp", "#7A4A12", () => App.Open(AppPage.Decorate)));
            row.Add(("settings.title", "ui_settings", "#4E5868", () => ParentGate(() => App.Open(AppPage.Settings), msg => _bubble.Say(msg))));
            for (var i = 0; i < row.Count; i++)
            {
                var r = row[i];
                // sol kenar dizisi (taslaktaki .x-left: 84 px, 34 px ara, mavi kurdele etiket)
                GoldKit.Icon3D(Root, r.icon, 84f * GoldKit.K, new Vector2(0f, 1f), new Vector2((34f + 42f) * GoldKit.K, -(158f + 42f + i * 118f) * GoldKit.K),
                    Theme.Hex(r.ex), r.act, T(r.key), GoldKit.Tone.Blue, i * 0.4f);
            }

            _bubble = Bubble(new Vector2(0.5f, 0.86f));

            // Sağ alt: bakım (Besle, Yıka, Oyna, Topla) — panel yok, yüzen şeker düğmeler
            var icons = new[] { "food_apple", "clean_soap", "ui_heart", "home_bookshelf" };
            var extrude = new[] { "#8E1020", "#A04A78", "#9E1B3C", "#5A3412" };
            var labels = new[] { "home.feed", "home.wash", "home.play", "home.tidy" };
            var actions = new[] { CareAction.Feed, CareAction.Wash, CareAction.Play, CareAction.Tidy };
            for (var i = 0; i < 4; i++)
            {
                var a = actions[i];
                System.Action act = a == CareAction.Feed ? () => OpenTray(ItemCategory.Food, CareAction.Feed)
                    : a == CareAction.Wash ? () => OpenTray(ItemCategory.Cleaning, CareAction.Wash) : (System.Action)(() => Care(a));
                var (b, _, _) = GoldKit.Icon3D(Root, icons[i], 104f * GoldKit.K, new Vector2(1f, 0f), new Vector2(i % 2 == 0 ? -470f : -250f, i < 2 ? 450f : 230f),
                    Theme.Hex(extrude[i]), act, T(labels[i]), GoldKit.Tone.Green, i * 0.35f);
                if (a == CareAction.Tidy) _tidyBtn = (RectTransform)b.transform;
                _careBtns[i] = (RectTransform)b.transform;
                if (a == CareAction.Feed) _feedCount = GoldKit.Gem(b.transform);
                if (a == CareAction.Wash) _washCount = GoldKit.Gem(b.transform);
            }
            NavBar(AppPage.Home);
            // Altın Atölye coin hapı pencere rozetinden geniş (simgesi soldan taşar): müzik düğmesi onun soluna (tasarım turu 24 Ekim 2026: üst üste biniyordu)
            MusicButton.Place(MusicButton.BesideClose - 56f);
            App.Synced += OnSynced;

            Refresh();
            if (Onboarding.Pending(App.State, Onboarding.Home))
                _coach = Coach.Show(Root, Onboarding.Home, T("tip.home"), TipGesture.Tap, () => RectTransformUtility.WorldToScreenPoint(null, _tidyBtn.position));
            else if (!GuideCoach()) _bubble.Say(T("pet.welcome", App.State.PetName), 4f);
            ApplyNight(true);
        }

        /// <summary>
        /// Rehberin evdeki adımları (kullanıcı GB17-2): "Topla'ya dokun" bitince aynı şekilde "Oyna'ya dokun" gelir; el ilgili düğmeye
        /// dokunur. Adım bitince panel kapanır. Gösterildiyse true.
        /// </summary>
        private bool GuideCoach()
        {
            if (_coach != null)
            {
                if (!_coach.Id.StartsWith("guide_")) return false;                       // başka ipucu (Evim tanıtımı, sürükleme)
                if (_coach.Id == "guide_close") { if (!LevelUpCelebration.Showing) return true; _coach.Done(); _coach = null; return false; }
                if (Guide.Is(App.State, App.Level, _coach.Id.Substring(6))) return true;   // adım sürüyor
                _coach.Done(); _coach = null;
            }
            if (LevelUpCelebration.Showing) return _coach != null;   // önce "Harika!" (el orada), sonra kapat
            var g = Guide.Current(App.State, App.Level);
            var btn = g == null ? null : g.Id == "tidy" ? _careBtns[3] : g.Id == "play" ? _careBtns[2] : null;
            if (btn == null) return GuideToClose(ref _coach, id => id == "home" || id == "tidy" || id == "play");   // sıradaki iş adada: çarpı
            _coach = Coach.Show(Root, "guide_" + g.Id, T(g.TextKey, App.State.PetName) + "  " + T("guide.reward", g.Xp), TipGesture.Tap,
                () => RectTransformUtility.WorldToScreenPoint(null, btn.position), null, 3, Guide.Label(App.State),
                null, T(g.TextKey, App.State.PetName));
            return true;
        }

        private void Update()
        {
            _tick += Time.deltaTime;
            if (_tick >= 1f)
            {
                _tick = 0f;
                GuideCoach();
                App.State.Stats.Tick(App.UtcNow, App.Decay);
                Refresh();
                ApplyNight(false);
            }
            _idle += Time.deltaTime;
            if (_idle > 18f)
            {
                _idle = 0f;
                _bubble.Say(CareFeedback.Idle(App.Loc, App.State.Stats, App.Decay));
            }
        }

        private void ApplyNight(bool force)
        {
            var night = PetCare.IsNight(App.LocalNow);
            if (!force && night == _night) return;
            _night = night;
            App.Stage.SetSky(night ? Theme.Hex("#22306B") : Th.Sky);
            App.Stage.SetSleeping(night);
        }

        private void Refresh()
        {
            var st = App.State;
            for (var i = 0; i < 4; i++) _prof.SetNeed(i, st.Stats[Kinds[i]]);
            _coins.text = st.Wallet.Available.ToString();
            _prof.SetName(st.PetName, st.Badges.Count);
            _prof.SetXp(App.Levels, st.Xp.TotalXp, App.Level, T("hud.xp_max"));
            _feedCount.text = Count(ItemCategory.Food).ToString();
            _washCount.text = Count(ItemCategory.Cleaning).ToString();
        }

        private int Count(string category) =>
            App.State.Inventory.Counts.Where(kv => App.Data.Item(kv.Key)?.Category == category).Sum(kv => kv.Value);

        private ItemDef First(string category) =>
            App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .FirstOrDefault(it => it != null && it.Category == category);

        private RectTransform _tray;

        /// <summary>Evde de yiyecek/sabun pete sürüklenir (adayla aynı el becerisi).</summary>
        private void OpenTray(string category, CareAction action)
        {
            if (_tray != null) { Destroy(_tray.gameObject); _tray = null; return; }
            var items = App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .Where(it => it != null && it.Category == category).ToList();
            if (items.Count == 0) { Care(action); return; }   // yoksa: "dükkândan al" mesajı
            _tray = Ui.Rect(Root, "Tray", new Vector2(1f, 0f), new Vector2(items.Count * 150f + 30f, 170f), new Vector2(0f, 0f));
            _tray.pivot = new Vector2(1f, 0f);
            _tray.anchoredPosition = new Vector2(-560f, action == CareAction.Feed ? 400f : 200f);
            RectTransform first = null; string firstId = null;
            for (var i = 0; i < items.Count; i++)
            {
                var it = items[i];
                var b = Candy.Round(_tray, Candy.White, it.Id, 130f, new Vector2(0f, 0.5f), new Vector2(80f + i * 150f, 0f), null);
                Candy.Count(b.transform).text = App.State.Inventory.CountOf(it.Id).ToString();
                var d = b.gameObject.AddComponent<DragItem>();
                d.IconId = it.Id; d.Layer = Root;
                d.Dropped = pos =>
                {
                    if (Vector2.Distance(pos, PetScreen()) > Screen.height * 0.22f) return false;
                    if (_tray != null) { Destroy(_tray.gameObject); _tray = null; }
                    CareWith(action, it);
                    return true;
                };
                d.Tapped = () => _bubble.Say(T(action == CareAction.Feed ? "tip.feed" : "tip.wash", Logic.Core.TurkishSuffix.Genitive(App.State.PetName)));
                if (first == null) { first = (RectTransform)b.transform; firstId = it.Id; }
            }
            var tip = action == CareAction.Feed ? Onboarding.Feed : Onboarding.Wash;
            if (_coach == null && Onboarding.Pending(App.State, tip))   // el eşyayı Okti'ye taşır, yapılana kadar gidip gelir
                _coach = Coach.Show(Root, tip, T("tip." + tip, Logic.Core.TurkishSuffix.Genitive(App.State.PetName)), TipGesture.Drag,
                    () => RectTransformUtility.WorldToScreenPoint(null, first.position), PetScreen, 99, null, null, null, Ui.Icon(firstId));
        }

        private Vector2 PetScreen() => App.Stage.Camera.WorldToScreenPoint(App.Stage.Pet != null ? App.Stage.Pet.position + Vector3.up * 1.0f : Vector3.zero);

        private void CareWith(CareAction a, ItemDef item)
        {
            var st = App.State;
            var r = a == CareAction.Feed ? PetCare.Feed(st.Stats, st.Inventory, item, App.LocalNow) : PetCare.Wash(st.Stats, st.Inventory, item, App.LocalNow);
            if (r == CareResult.Ok)
            {
                var tip = a == CareAction.Feed ? Onboarding.Feed : Onboarding.Wash;
                if (Onboarding.Pending(st, tip)) Onboarding.Done(st, tip);
                if (_coach != null) { _coach.Done(); _coach = null; }
                App.Stage.Hop();
                if (a == CareAction.Feed) CareFx.Food(Root, Ui.Icon(item.Id), PetScreen);
                else CareFx.Bubbles(Root, PetScreen);
                var gi = a == CareAction.Feed ? 0 : 1;
                GoldProfile.FlyCare(App.Overlay.transform, gi, GaugeIcons[gi], PetScreen());
                App.Save();
                App.RecordActivity(a == CareAction.Feed ? "pet_fed" : "pet_washed");
            }
            _idle = 0f;
            _bubble.Say(CareFeedback.Message(App.Loc, a, r, st.PetName));
            Refresh();
        }

        private void Care(CareAction a)
        {
            var st = App.State;
            var local = App.LocalNow;
            CareResult r;
            switch (a)
            {
                case CareAction.Feed:
                    var food = First(ItemCategory.Food);
                    r = food == null ? (PetCare.IsNight(local) ? CareResult.Sleeping : CareResult.NoItem) : PetCare.Feed(st.Stats, st.Inventory, food, local);
                    break;
                case CareAction.Wash:
                    var soap = First(ItemCategory.Cleaning);
                    r = soap == null ? (PetCare.IsNight(local) ? CareResult.Sleeping : CareResult.NoItem) : PetCare.Wash(st.Stats, st.Inventory, soap, local);
                    break;
                case CareAction.Play: r = PetCare.Play(st.Stats, local); break;
                default:
                    r = PetCare.Tidy(st.Stats);
                    if (Onboarding.Pending(st, Onboarding.Home)) { Onboarding.Done(st, Onboarding.Home); if (_coach != null) { _coach.Done(); _coach = null; } }
                    break;
            }
            if (r == CareResult.Ok)
            {
                App.Stage.Hop();
                var gi = a == CareAction.Feed ? 0 : a == CareAction.Wash ? 1 : a == CareAction.Play ? 2 : 3;
                GoldProfile.FlyCare(App.Overlay.transform, gi, GaugeIcons[gi], RectTransformUtility.WorldToScreenPoint(null, _careBtns[gi].position));
                App.Save();
                App.RecordActivity(a == CareAction.Feed ? "pet_fed" : a == CareAction.Wash ? "pet_washed" : a == CareAction.Play ? "pet_played" : "home_tidied");
            }
            _idle = 0f;
            _bubble.Say(CareFeedback.Message(App.Loc, a, r, st.PetName));
            Refresh();
        }

        private void OnSynced(Logic.State.SyncReport r) => Refresh();

        private void OnDestroy()
        {
            if (App != null) App.Synced -= OnSynced;
        }
    }
}
