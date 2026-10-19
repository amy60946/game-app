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
        private static readonly Color[] StatColors =
        {
            Theme.Hex("#FF9F43"), Theme.Hex("#3DC9FF"), Theme.Hex("#FF6FAE"), Theme.Hex("#7BD66B"),
        };

        private readonly Image[] _gaugeFills = new Image[4];
        private RectTransform _tidyBtn;
        private Coach _coach;
        private static readonly string[] GaugeIcons = { "food_apple", "clean_soap", "ui_heart", "home_bed" };
        private Text _coins, _title, _levelNum, _feedCount, _washCount;
        private Image _xpFill;
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
            var pet = App.Data.Pet(App.State.PetId);
            Candy.PetPlate(Root, App.State.PetId, Theme.Hex(pet.MainColor), new Vector2(24f, -16f), out _title, out _levelNum, out _xpFill);
            for (var i = 0; i < 4; i++)
                _gaugeFills[i] = Candy.Gauge(Root, StatColors[i], GaugeIcons[i], 112f, new Vector2(0f, 1f), new Vector2(30f + 56f + i * 128f, -250f));
            _coins = Candy.CoinPlate(Root, new Vector2(-30f, -22f));

            var row = new List<(string key, System.Action act)> { ("home.daily", () => QuestPanel()), ("album.button", () => App.Open(AppPage.Album)) };
            if (App.Levels.IsUnlocked("home_decor", App.Level)) row.Add(("decor.button", () => App.Open(AppPage.Decorate)));
            row.Add(("settings.title", () => ParentGate(() => App.Open(AppPage.Settings), msg => _bubble.Say(msg))));
            for (var i = 0; i < row.Count; i++)
                Candy.Pill(Root, Candy.White, T(row[i].key), new Vector2(1f, 1f), new Vector2(330f, 88f), new Vector2(-195f, -160f - i * 112f), row[i].act, null, 34);

            _bubble = Bubble(new Vector2(0.5f, 0.86f));

            // Sağ alt: bakım (Besle, Yıka, Oyna, Topla) — panel yok, yüzen şeker düğmeler
            var icons = new[] { "food_apple", "clean_soap", "ui_heart", "home_bookshelf" };
            var colors = new[] { Candy.Orange, Candy.Blue, Candy.Pink, Candy.Green };
            var labels = new[] { "home.feed", "home.wash", "home.play", "home.tidy" };
            var actions = new[] { CareAction.Feed, CareAction.Wash, CareAction.Play, CareAction.Tidy };
            for (var i = 0; i < 4; i++)
            {
                var a = actions[i];
                System.Action act = a == CareAction.Feed ? () => OpenTray(ItemCategory.Food, CareAction.Feed)
                    : a == CareAction.Wash ? () => OpenTray(ItemCategory.Cleaning, CareAction.Wash) : (System.Action)(() => Care(a));
                var b = Candy.Round(Root, colors[i], icons[i], 160f, new Vector2(1f, 0f), new Vector2(i % 2 == 0 ? -440f : -230f, i < 2 ? 440f : 220f), act, T(labels[i]));
                if (a == CareAction.Tidy) _tidyBtn = (RectTransform)b.transform;
                if (a == CareAction.Feed) _feedCount = Candy.Count(b.transform);
                if (a == CareAction.Wash) _washCount = Candy.Count(b.transform);
            }
            NavBar(AppPage.Home);
            App.Synced += OnSynced;

            Refresh();
            if (Onboarding.Pending(App.State, Onboarding.Home))
                _coach = Coach.Show(Root, Onboarding.Home, T("tip.home"), TipGesture.Tap, () => RectTransformUtility.WorldToScreenPoint(null, _tidyBtn.position));
            else if (Guide.Current(App.State, App.Level)?.Id == "tidy")   // rehberli zincir: evi topla adımı
                _coach = Coach.Show(Root, "guide_tidy", T("guide.tidy") + "  " + T("guide.reward", Guide.Get("tidy").Xp), TipGesture.Tap,
                    () => RectTransformUtility.WorldToScreenPoint(null, _tidyBtn.position), null, 3, (Guide.DoneCount(App.State) + 1) + "/" + Guide.Steps.Count);
            else _bubble.Say(T("pet.welcome", App.State.PetName), 4f);
            ApplyNight(true);
        }

        private void Update()
        {
            _tick += Time.deltaTime;
            if (_tick >= 1f)
            {
                _tick = 0f;
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
            for (var i = 0; i < 4; i++) _gaugeFills[i].fillAmount = st.Stats[Kinds[i]] / 100f;
            _coins.text = st.Wallet.Available.ToString();
            _title.text = st.PetName;
            _levelNum.text = App.Level.ToString();
            Ui.SetBar(_xpFill, App.Levels.ProgressInLevel(st.Xp.TotalXp));
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
            RectTransform first = null;
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
                if (first == null) first = (RectTransform)b.transform;
            }
            var tip = action == CareAction.Feed ? Onboarding.Feed : Onboarding.Wash;
            if (_coach == null && Onboarding.Pending(App.State, tip))
                _coach = Coach.Show(Root, tip, T("tip." + tip, Logic.Core.TurkishSuffix.Genitive(App.State.PetName)), TipGesture.Drag,
                    () => RectTransformUtility.WorldToScreenPoint(null, first.position), PetScreen);
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
