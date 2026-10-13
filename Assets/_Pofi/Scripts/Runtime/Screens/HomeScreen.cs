using System;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Pet;
using Pofi.Logic.Progression;
using Pofi.Logic.Safety;
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
        private SpeechBubble _bubble;
        private float _tick, _idle;
        private RectTransform _gate;
        private bool _night;

        protected override void Build()
        {
            var def = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = true;
            App.Stage.SetCamera(new Vector3(0f, 1.14f, -6.23f), 0f);
            App.Stage.ShowPet(def, App.Growth);

            // Üst bilgi kartı: isim, seviye/evre, coin ve göstergeler
            var top = Ui.Rect(Root, "Top", new Vector2(0.5f, 0.835f), new Vector2(1010f, 420f));
            Ui.Panel(top, Th.Panel, Th.Radius);
            _title = Ui.Label(top, "", Th.Font(54), Th.Text, new Vector2(0.4f, 0.85f), new Vector2(740f, 80f), FontStyle.Bold, TextAnchor.MiddleLeft);
            var coin = Ui.Rect(top, "Coins", new Vector2(0.84f, 0.85f), new Vector2(230f, 84f));
            Ui.Panel(coin, Theme.Hex("#FFD23F"), 42f);
            var coinDot = Ui.Rect(coin, "Icon", new Vector2(0.2f, 0.5f), new Vector2(54f, 54f));
            Ui.Panel(coinDot, Theme.Hex("#F5A300"), 27f);
            _coins = Ui.Label(coin, "0", Th.Font(46), Theme.Hex("#5A3B00"), new Vector2(0.62f, 0.5f), new Vector2(150f, 80f), FontStyle.Bold);

            for (var i = 0; i < 4; i++)
            {
                var col = i % 2;
                var row = i / 2;
                var anchor = new Vector2(col == 0 ? 0.27f : 0.73f, row == 0 ? 0.56f : 0.24f);
                Ui.Label(top, T(StatKeys[i]), Th.Font(34), Th.SubtleText, anchor, new Vector2(440f, 50f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(0f, 34f));
                _bars[i] = Ui.Bar(top, anchor, new Vector2(440f, 40f), new Color(0f, 0f, 0f, 0.08f), StatColors[i], 20f, new Vector2(0f, -14f));
            }

            // Ayarlar / çıkış (ebeveyn kapısı)
            Ui.Button(Root, Th, T("settings.sign_out"), new Vector2(0.87f, 0.972f), new Vector2(210f, 76f), OpenGate, false, default, 34);

            _bubble = Bubble(new Vector2(0.5f, 0.675f));

            // Bakım düğmeleri
            var bar = Ui.Rect(Root, "Actions", new Vector2(0.5f, 0.095f), new Vector2(1010f, 230f));
            Ui.Panel(bar, Th.Panel, Th.Radius);
            var labels = new[] { "home.feed", "home.wash", "home.play", "home.tidy" };
            var actions = new[] { CareAction.Feed, CareAction.Wash, CareAction.Play, CareAction.Tidy };
            for (var i = 0; i < 4; i++)
            {
                var a = actions[i];
                var b = Ui.Button(bar, Th, T(labels[i]), new Vector2(0.125f + i * 0.25f, 0.5f), new Vector2(220f, 170f), () => Care(a), i == 2, default, 42);
                var badge = Ui.Rect(b.transform, "Count", new Vector2(0.88f, 0.9f), new Vector2(64f, 64f));
                if (a == CareAction.Feed || a == CareAction.Wash)
                {
                    Ui.Panel(badge, Th.Danger, 32f).raycastTarget = false;
                    var t = Ui.Label(badge, "0", Th.Font(32), Color.white, new Vector2(0.5f, 0.5f), new Vector2(64f, 64f), FontStyle.Bold);
                    if (a == CareAction.Feed) _feedCount = t; else _washCount = t;
                }
                else Destroy(badge.gameObject);
            }
            Footer();

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
        }

        private void Refresh()
        {
            var st = App.State;
            for (var i = 0; i < 4; i++) Ui.SetBar(_bars[i], st.Stats[Kinds[i]] / 100f);
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
            if (r == CareResult.Ok) { App.Stage.Hop(); App.Save(); }
            _idle = 0f;
            _bubble.Say(CareFeedback.Message(App.Loc, a, r, st.PetName));
            Refresh();
        }

        // ---- ebeveyn kapısı ----
        private void OpenGate()
        {
            if (_gate != null) return;
            App.Stage.AllowDrag = false;
            var ch = ParentGate.Create(App.Session.AgeBand, new System.Random());
            _gate = Ui.Fill(Root, "Gate");
            _gate.gameObject.AddComponent<Image>().color = new Color(0f, 0.08f, 0.2f, 0.55f);
            var box = Ui.Rect(_gate, "Box", new Vector2(0.5f, 0.5f), new Vector2(960f, 900f));
            Ui.Panel(box, Color.white, Th.Radius);
            Ui.Label(box, T("gate.title"), Th.Font(56), Th.Text, new Vector2(0.5f, 0.9f), new Vector2(880f, 80f), FontStyle.Bold);
            Ui.Label(box, T("gate.hint"), Th.Font(34), Th.SubtleText, new Vector2(0.5f, 0.82f), new Vector2(880f, 60f));
            Ui.Label(box, ch.Prompt, Th.Font(48), Th.Text, new Vector2(0.5f, 0.69f), new Vector2(880f, 140f), FontStyle.Bold);
            for (var i = 0; i < ch.Options.Count; i++)
            {
                var v = ch.Options[i];
                var anchor = new Vector2(i % 2 == 0 ? 0.28f : 0.72f, i < 2 ? 0.47f : 0.29f);
                Ui.Button(box, Th, v.ToString(), anchor, new Vector2(360f, 130f), () =>
                {
                    CloseGate();
                    if (v == ch.Answer) App.SignOut();
                    else _bubble.Say(T("gate.wrong"));
                }, false, default, 56);
            }
            Ui.Button(box, Th, "X", new Vector2(0.5f, 0.09f), new Vector2(160f, 100f), CloseGate, false, default, 48);
        }

        private void CloseGate()
        {
            if (_gate != null) Destroy(_gate.gameObject);
            _gate = null;
            App.Stage.AllowDrag = true;
        }
    }
}
