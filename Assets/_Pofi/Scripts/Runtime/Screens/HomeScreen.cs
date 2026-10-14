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
        private static readonly string[] GaugeIcons = { "food_apple", "clean_soap", "ui_heart", "home_bed" };
        private Text _coins, _title, _feedCount, _washCount;
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
            App.Stage.SetAmbient(true);

            // Sahne üstü (14 Ekim 2026 kararı): sol üst rozet + gösterge halkaları, sağ üst coin ve evin düğmeleri, sağ alt bakım
            _title = Candy.Badge(Root, "ui_star", "", new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(30f, -24f), 84f, 440f);
            for (var i = 0; i < 4; i++)
                _gaugeFills[i] = Candy.Gauge(Root, StatColors[i], GaugeIcons[i], 112f, new Vector2(0f, 1f), new Vector2(30f + 56f + i * 128f, -176f));
            _coins = Candy.Badge(Root, "ui_coin", "", new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-30f, -24f), 84f, 250f);

            var row = new List<(string key, System.Action act)> { ("home.daily", DailyPanel), ("album.button", () => App.Open(AppPage.Album)) };
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
                var b = Candy.Round(Root, colors[i], icons[i], 140f, new Vector2(1f, 0f), new Vector2(i % 2 == 0 ? -400f : -210f, i < 2 ? 400f : 200f), () => Care(a), T(labels[i]));
                if (a == CareAction.Feed) _feedCount = Candy.Count(b.transform);
                if (a == CareAction.Wash) _washCount = Candy.Count(b.transform);
            }
            NavBar(AppPage.Home);
            App.Synced += OnSynced;

            Refresh();
            _bubble.Say(T("pet.welcome", App.State.PetName), 4f);
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
            _title.text = $"{st.PetName} · {T("home.level", App.Level)}";
            _feedCount.text = Count(ItemCategory.Food).ToString();
            _washCount.text = Count(ItemCategory.Cleaning).ToString();
        }

        private int Count(string category) =>
            App.State.Inventory.Counts.Where(kv => App.Data.Item(kv.Key)?.Category == category).Sum(kv => kv.Value);

        private ItemDef First(string category) =>
            App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .FirstOrDefault(it => it != null && it.Category == category);

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
                default: r = PetCare.Tidy(st.Stats); break;
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

        private void DailyPanel()
        {
            Activity.EnsureQuests(App.State, App.Data, App.Levels, App.LocalNow);
            var root = Modal(760f, out var box);
            Ui.Label(box, T("home.daily"), Th.Font(60), Th.Text, new Vector2(0.5f, 0.88f), new Vector2(880f, 90f), FontStyle.Bold);
            var i = 0;
            foreach (var id in App.State.DailyQuests.Ids)
            {
                var q = App.Data.DailyQuests.FirstOrDefault(x => x.Id == id);
                if (q == null) continue;
                var y = 0.7f - i * 0.17f;
                var done = App.State.DailyQuests.Claimed.Contains(id);
                var prog = DailyQuests.Progress(q, App.State.Counters);
                Ui.Label(box, q.Text, Th.Font(40), done ? Theme.Hex("#2E9E4F") : Th.Text, new Vector2(0.42f, y), new Vector2(700f, 70f), FontStyle.Bold, TextAnchor.MiddleLeft);
                Ui.Label(box, done ? T("home.daily_done") : prog + "/" + q.Target, Th.Font(38), Th.SubtleText, new Vector2(0.86f, y), new Vector2(200f, 70f), FontStyle.Bold);
                var bar = Ui.Bar(box, new Vector2(0.5f, y - 0.055f), new Vector2(860f, 16f), new Color(0f, 0f, 0f, 0.08f), Th.Primary, 8f);
                Ui.SetBar(bar, (float)prog / q.Target);
                i++;
            }
            Ui.Button(box, Th, T("common.ok"), new Vector2(0.5f, 0.1f), new Vector2(360f, 110f), () => Destroy(root.gameObject), false, default, 44);
        }

        private void OnSynced(Logic.State.SyncReport r) => Refresh();

        private void OnDestroy()
        {
            if (App != null) App.Synced -= OnSynced;
        }
    }
}
