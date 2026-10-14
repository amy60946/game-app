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

        private readonly Image[] _bars = new Image[4];
        private Text _coins, _title, _feedCount, _washCount;
        private Image _xpBar;
        private SpeechBubble _bubble;
        private float _tick, _idle;
        private bool _night;

        protected override void Build()
        {
            var def = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = true;
            PetCamera(0.5f, 0.2f, 0.78f);   // yatay: pet ortada, göstergeler solda, bakım düğmeleri sağda
            App.Stage.ShowPet(def, App.Growth, App.State.Inventory.Equipped.Values);
            App.Stage.SetHomeItems(App.State.Home, App.Levels.IsUnlocked("home_expansion", App.Level));
            App.Stage.SetAmbient(true);

            // Üst bilgi kartı: isim, seviye/evre, coin ve göstergeler
            // Sol üst: isim, seviye, coin ve göstergeler
            var top = Ui.Rect(Root, "Top", new Vector2(0f, 1f), new Vector2(620f, 440f));
            top.pivot = new Vector2(0f, 1f);
            top.anchoredPosition = new Vector2(36f, -30f);
            Ui.Panel(top, Th.Panel, Th.Radius);
            _title = Ui.Label(top, "", Th.Font(46), Th.Text, new Vector2(0.36f, 0.89f), new Vector2(400f, 70f), FontStyle.Bold, TextAnchor.MiddleLeft);
            _coins = CoinPill(top, new Vector2(0.8f, 0.89f));
            _xpBar = Ui.Bar(top, new Vector2(0.5f, 0.77f), new Vector2(560f, 16f), new Color(0f, 0f, 0f, 0.08f), Theme.Hex("#FFC400"), 8f);

            for (var i = 0; i < 4; i++)
            {
                var y = 0.62f - i * 0.16f;
                var anchor = new Vector2(0.5f, y);
                Ui.Label(top, T(StatKeys[i]), Th.Font(30), Th.SubtleText, anchor, new Vector2(560f, 40f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(0f, 22f));
                _bars[i] = Ui.Bar(top, anchor, new Vector2(560f, 26f), new Color(0f, 0f, 0f, 0.08f), StatColors[i], 13f, new Vector2(0f, -14f));
            }

            // Sağ üst: günün görevleri, defter, süsle, ayarlar (ebeveyn kapısı)
            var row = new List<(string key, System.Action act)> { ("home.daily", DailyPanel), ("album.button", () => App.Open(AppPage.Album)) };
            if (App.Levels.IsUnlocked("home_decor", App.Level)) row.Add(("decor.button", () => App.Open(AppPage.Decorate)));
            row.Add(("settings.title", () => ParentGate(() => App.Open(AppPage.Settings), msg => _bubble.Say(msg))));
            for (var i = 0; i < row.Count; i++)
            {
                var b = Ui.Button(Root, Th, T(row[i].key), new Vector2(1f, 1f), new Vector2(250f, 78f), row[i].act, false, default, 32, false);
                var rt = (RectTransform)b.transform;
                rt.pivot = new Vector2(1f, 1f);
                rt.anchoredPosition = new Vector2(-36f, -30f - i * 92f);
            }

            _bubble = Bubble(new Vector2(0.5f, 0.86f));

            // Sağ alt: bakım düğmeleri (2×2)
            var bar = Ui.Rect(Root, "Actions", new Vector2(1f, 0f), new Vector2(500f, 380f));
            bar.pivot = new Vector2(1f, 0f);
            bar.anchoredPosition = new Vector2(-36f, NavHeight + 20f);
            Ui.Panel(bar, Th.Panel, Th.Radius);
            var labels = new[] { "home.feed", "home.wash", "home.play", "home.tidy" };
            var actions = new[] { CareAction.Feed, CareAction.Wash, CareAction.Play, CareAction.Tidy };
            for (var i = 0; i < 4; i++)
            {
                var a = actions[i];
                var b = Ui.Button(bar, Th, T(labels[i]), new Vector2(i % 2 == 0 ? 0.27f : 0.73f, i < 2 ? 0.73f : 0.27f), new Vector2(210f, 150f), () => Care(a), i == 2, default, 40, false);
                var badge = Ui.Rect(b.transform, "Count", new Vector2(0.88f, 0.9f), new Vector2(64f, 64f));
                if (a == CareAction.Feed || a == CareAction.Wash)
                {
                    Ui.Panel(badge, Th.Danger, 32f).raycastTarget = false;
                    var t = Ui.Label(badge, "0", Th.Font(32), Color.white, new Vector2(0.5f, 0.5f), new Vector2(64f, 64f), FontStyle.Bold);
                    if (a == CareAction.Feed) _feedCount = t; else _washCount = t;
                }
                else Destroy(badge.gameObject);
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
            for (var i = 0; i < 4; i++) Ui.SetBar(_bars[i], st.Stats[Kinds[i]] / 100f);
            _coins.text = st.Wallet.Available.ToString();
            _title.text = $"{st.PetName} · {T("home.level", App.Level)}";
            Ui.SetBar(_xpBar, App.Levels.ProgressInLevel(st.Xp.TotalXp));
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
