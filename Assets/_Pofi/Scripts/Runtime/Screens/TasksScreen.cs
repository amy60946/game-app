using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Görevler penceresi (C + D, kullanıcı kararı 24 Ekim 2026: "Ev Görevleri arkada kalmış gibi"). Sekme yok, iki bölüm:
    /// solda büyük, altın <b>Ev Görevleri</b> (ebeveynin gerçek görevleri; FR-TASK-2..5), sağda küçük, mavi <b>Oyun görevleri</b>
    /// (günlük görevler + günlük sandık, S2). Ev görevi kartı (D): "Ailenden" mührü, beceri ve zorluk, üç adımlı yol
    /// (yap → Mavi götürüyor → taş geldi), büyük Güneş Taşı ödülü. Çocuk "Yaptım" / "Yapamam" der, ebeveyn onaylar; coin ve taş
    /// yalnız onaydan sonra gelir. Değişiklik önce yerelde görünür, sonra senkronla gider (çevrimdışı kuyruk).
    /// İlk açılışta bilgilendirme eli sırayla bölümleri anlatır (<see cref="Onboarding.TasksIntro"/>).
    /// Adadaki Görev düğmesi, Evim'deki Görevler ve adadaki pano bu pencereyi açar (<see cref="ScreenBase.QuestPanel"/>).
    /// </summary>
    public sealed partial class TasksScreen : ScreenBase
    {
        // taslak pikseli × 1,5 (GoldKit.K) = tuval birimi
        private const float WinTop = 112f, WinBottom = 22f, WinRim = 9f, WinR = 45f, Pad = 24f, Gap = 24f;
        private const float SecR = 33f, SecRim = 4.5f, SecPad = 18f, EvHeadH = 96f, OyHeadH = 81f, WeekH = 84f, ListPadX = 10f;

        private static readonly Color InkBrown = Theme.Hex("#4A2600"), InkTan = Theme.Hex("#7A4A12"), InkBlue = Theme.Hex("#1F3A66"),
            InkBlueSoft = Theme.Hex("#6A7F9E"), InkGreen = Theme.Hex("#2E8A4A"), RibbonInk = Theme.Hex("#102E86");

        private RectTransform _listArea, _listView, _list, _empty, _week, _evRight, _evTitle, _oyTitle, _quests;
        private RectTransform _firstDone;   // ilk "Yaptım" (bilgilendirme eli)
        private RectTransform _goBtn;       // "Adaya götür" (taş ipucu)
        private Text _coins, _evSub, _gem;
        private float _evContentW, _oyContentW;
        private bool _filling;

        private int F(int n) => Mathf.RoundToInt(n * Mathf.Clamp(Th.Scale * Th.TextScale, 0.95f, 1.15f));

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            var veil = Ui.Fill(Root, "Veil").gameObject.AddComponent<Image>();
            veil.color = new Color(0f, 0.08f, 0.2f, 0.16f); veil.raycastTarget = false;
            BuildWindow();
            _coins = Header(T("home.daily"));   // "Görevler" kurdelesi pencerenin sol üst köşesine taşar; coin sağ üstte
            if (App.Backend != null)
            {
                // deneme ebeveyn paneli (yalnız sahte sunucu): pencerenin üstünde, ortada
                var demo = (RectTransform)CornerButton(T("demo.parent_button"), () => ParentGate(OpenDemoPanel), 380f).transform;
                demo.anchorMin = demo.anchorMax = new Vector2(0.5f, 1f);
                demo.pivot = new Vector2(0.5f, 1f);
                demo.anchoredPosition = new Vector2(0f, -14f);
            }
            NavBar(AppPage.Tasks);
            if (Onboarding.Pending(App.State, Onboarding.Board)) { Onboarding.Done(App.State, Onboarding.Board); App.Save(); }
            App.RecordActivity("board_opened");
            Activity.EnsureQuests(App.State, App.Data, App.Levels, App.LocalNow);
            App.Synced += OnSynced;
            Fill();
            QueueIntro();
            LoadGoal();
            _ = App.SyncNow();
        }

        private void OnSynced(SyncReport r)
        {
            if (this == null) return;
            Fill();
        }

        // ------------------------------------------------------------------ pencere iskeleti (bir kez)

        private void BuildWindow()
        {
            var side = Mathf.Max(36f, (Width - 2140f) * 0.5f);
            var winW = Width - side * 2f;
            var innerW = winW - WinRim * 2f;
            var oyW = Mathf.Clamp(winW * 0.27f, 480f, 560f);
            var evW = innerW - Pad * 2f - oyW - Gap;
            _evContentW = evW - SecRim * 2f - SecPad * 2f;
            _oyContentW = oyW - SecRim * 2f - SecPad * 2f;

            // E dili pencere: altın çerçeve, krem iç, ince açık iç kenar, gölge
            var win = Ui.Rect(Root, "Window", Vector2.zero, Vector2.zero);
            win.anchorMin = Vector2.zero; win.anchorMax = Vector2.one;
            win.offsetMin = new Vector2(side, WinBottom); win.offsetMax = new Vector2(-side, -WinTop);
            PanelKit.GoldRim(win, WinR);
            var sh = win.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.08f, 0.08f, 0.24f, 0.35f); sh.effectDistance = new Vector2(0f, -14f);
            var hi = Ui.Fill(win, "Hi");
            hi.offsetMin = new Vector2(WinRim, WinRim); hi.offsetMax = -hi.offsetMin;
            PanelKit.Flat(hi, new Color(1f, 1f, 1f, 0.5f), WinR - WinRim);
            var inner = Ui.Fill(win, "Inner");
            inner.offsetMin = new Vector2(WinRim + 4.5f, WinRim + 4.5f); inner.offsetMax = -inner.offsetMin;
            PanelKit.Grad(inner, Theme.Hex("#FFF8E4"), Theme.Hex("#F3DDA6"), WinR - WinRim - 4.5f);
            var grid = Ui.Fill(win, "Grid");
            grid.offsetMin = new Vector2(WinRim, WinRim); grid.offsetMax = -grid.offsetMin;

            // sol: Ev Görevleri (altın, büyük, hafif ışıma)
            var ev = Ui.Fill(grid, "Home");
            ev.offsetMin = new Vector2(Pad, Pad); ev.offsetMax = new Vector2(-(Pad + oyW + Gap), -Pad);
            var evBody = PanelKit.Section(ev, Theme.Hex("#FFF1C4"), Theme.Hex("#FBE3A0"), Theme.Hex("#F5C04A"), SecR, SecRim, new Color(1f, 0.78f, 0.31f, 0.55f), 39f);
            var evIn = Ui.Fill(evBody, "In");
            evIn.offsetMin = new Vector2(SecPad, SecPad); evIn.offsetMax = -evIn.offsetMin;
            BuildHomeHead(evIn);
            _listArea = Ui.Fill(evIn, "ListArea");
            _listArea.offsetMax = new Vector2(0f, -(EvHeadH + 12f));
            _list = Ui.ScrollList(_listArea, Vector2.zero, Vector2.one, 16f);
            _listView = (RectTransform)_list.parent;
            _empty = Ui.Fill(_listArea, "Empty");
            BuildEmpty(_empty);
            _empty.gameObject.SetActive(false);
            _week = Ui.Rect(evIn, "Week", Vector2.zero, Vector2.zero);
            _week.anchorMin = new Vector2(0f, 0f); _week.anchorMax = new Vector2(1f, 0f); _week.pivot = new Vector2(0.5f, 0f);
            _week.sizeDelta = new Vector2(0f, WeekH); _week.anchoredPosition = Vector2.zero;
            _week.gameObject.SetActive(false);

            // sağ: Oyun görevleri (mavi, küçük)
            var oy = Ui.Rect(grid, "Game", Vector2.zero, Vector2.zero);
            oy.anchorMin = new Vector2(1f, 0f); oy.anchorMax = new Vector2(1f, 1f); oy.pivot = new Vector2(1f, 0.5f);
            oy.offsetMin = new Vector2(-(Pad + oyW), Pad); oy.offsetMax = new Vector2(-Pad, -Pad);
            var oyBody = PanelKit.Section(oy, Theme.Hex("#EEF5FF"), Theme.Hex("#D8E8FF"), Theme.Hex("#A9CBFF"), SecR, SecRim);
            var oyIn = Ui.Fill(oyBody, "In");
            oyIn.offsetMin = new Vector2(SecPad, SecPad); oyIn.offsetMax = -oyIn.offsetMin;
            BuildGameHead(oyIn);
            _quests = Ui.Fill(oyIn, "Quests");
            _quests.offsetMax = new Vector2(0f, -(OyHeadH + 12f));
        }

        private void BuildHomeHead(RectTransform parent)
        {
            var head = TopBand(parent, "HomeHead", EvHeadH);
            var face = PanelKit.Lipped(head, Theme.Hex("#FFE27A"), Theme.Hex("#F5B52E"), Theme.Hex("#C98A1A"), 24f, 6f);
            Ui.IconImage(face, "ui_board", new Vector2(0f, 0.5f), 87f, new Vector2(9f + 43.5f, 0f));
            var title = Ui.Label(face, T("tasks.title"), 42, InkBrown, new Vector2(0f, 0.5f), new Vector2(400f, 52f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(110f, 13f));
            title.rectTransform.pivot = new Vector2(0f, 0.5f);
            title.rectTransform.sizeDelta = new Vector2(title.preferredWidth + 4f, 52f);
            _evTitle = title.rectTransform;
            _evSub = Ui.Label(face, "", 24, InkTan, new Vector2(0f, 0.5f), new Vector2(420f, 32f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(110f, -23f));
            _evSub.rectTransform.pivot = new Vector2(0f, 0.5f);
            _evRight = Ui.Fill(face, "Right");
        }

        private void BuildGameHead(RectTransform parent)
        {
            var head = TopBand(parent, "GameHead", OyHeadH);
            var face = PanelKit.Lipped(head, Theme.Hex("#86B8FF"), Theme.Hex("#2F64DB"), Theme.Hex("#1B47A8"), 24f, 6f);
            Ui.IconImage(face, "ui_star", new Vector2(0f, 0.5f), 63f, new Vector2(9f + 31.5f, 0f));
            var title = Ui.Label(face, T("quests.tab_game"), 35, Color.white, new Vector2(0f, 0.5f), new Vector2(360f, 46f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(82f, 2f));
            title.rectTransform.pivot = new Vector2(0f, 0.5f);
            title.rectTransform.sizeDelta = new Vector2(Mathf.Min(_oyContentW - 160f, title.preferredWidth + 4f), 46f);
            InkShadow(title, RibbonInk);
            _oyTitle = title.rectTransform;
            _gem = GoldKit.Gem(face, 51f);
            var g = (RectTransform)_gem.transform.parent;
            g.anchorMin = g.anchorMax = new Vector2(1f, 0.5f);
            g.anchoredPosition = new Vector2(-40f, 2f);
        }

        private static RectTransform TopBand(RectTransform parent, string name, float h)
        {
            var rt = Ui.Rect(parent, name, Vector2.zero, Vector2.zero);
            rt.anchorMin = new Vector2(0f, 1f); rt.anchorMax = new Vector2(1f, 1f); rt.pivot = new Vector2(0.5f, 1f);
            rt.sizeDelta = new Vector2(0f, h); rt.anchoredPosition = Vector2.zero;
            return rt;
        }

        /// <summary>Görev yokken bölüm boş kalmaz: Mavi (postacı) "ailen görev ekleyince haber getiririm" der.</summary>
        private void BuildEmpty(RectTransform parent)
        {
            var box = Ui.Fill(parent, "Box");
            box.offsetMin = new Vector2(ListPadX, 14f); box.offsetMax = new Vector2(-ListPadX, -14f);
            var face = PanelKit.Lipped(box, Theme.Hex("#FFFDF5"), Theme.Hex("#FFFDF5"), Theme.Hex("#E6CF98"), 30f, 4.5f);
            var mavi = Pic(face, Mavi, "Mavi", new Vector2(0f, 0.5f), new Vector2(190f, 266f), new Vector2(40f + 95f, 0f));
            if (mavi != null) Hover.On(mavi, 6f, 0.03f);
            var textW = _evContentW - ListPadX * 2f - 270f - 40f;
            var t = Ui.Label(face, T("tasks.empty_title"), F(39), Theme.Hex("#4A2C0A"), new Vector2(0f, 0.5f), new Vector2(textW, 60f), FontStyle.Bold, TextAnchor.LowerLeft, new Vector2(270f, 30f));
            t.rectTransform.pivot = new Vector2(0f, 0f);
            var s = Ui.Label(face, T("tasks.empty_sub"), F(28), Theme.Hex("#9A6B30"), new Vector2(0f, 0.5f), new Vector2(textW, 120f), FontStyle.Bold, TextAnchor.UpperLeft, new Vector2(270f, 18f));
            s.rectTransform.pivot = new Vector2(0f, 1f);
        }

        // ------------------------------------------------------------------ içerik (her senkronda)

        private void Fill()
        {
            if (_filling || this == null) return;
            _filling = true;
            try
            {
                _coins.text = App.State.Wallet.Available.ToString();
                FillHome();
                FillStones();
                FillWeek();
                FillGame();
                UpdateIntro();
            }
            finally { _filling = false; }
        }

        private void FillHome()
        {
            _firstDone = null;
            Ui.Clear(_list);
            var local = App.LocalNow;
            var today = DemoParent.Day(local);
            var tasks = App.State.Tasks.ForDisplay(local).Where(t => t.Date == today).ToList();
            _evSub.text = tasks.Count > 0 ? T("tasks.today", tasks.Count) : T("tasks.from_family");
            var empty = tasks.Count == 0;
            _listView.gameObject.SetActive(!empty);
            _empty.gameObject.SetActive(empty);
            if (empty) return;
            // ilk kart onay bekliyorsa üstünde uçan Mavi'ye yer
            var first = tasks[0];
            var top = first.Status == ChildTaskStatus.ChildDone && !first.IsMissed(local) ? 52 : 14;
            _list.GetComponent<VerticalLayoutGroup>().padding = new RectOffset((int)ListPadX, (int)ListPadX, top, 24);
            foreach (var task in tasks) Card(task, local);
        }

        // ---- Güneş Taşı (Ö1): Ev Görevleri başlığının sağında sıradaki onarım noktası + "Adaya götür" ----
        private void FillStones()
        {
            Ui.Clear(_evRight);
            _goBtn = null;
            var st = App.State.SunStones;
            var next = App.Data.SunBook.Next(st);
            var have = SunStoneBook.Available(st);
            // sol blok (başlık + alt yazı) ne kadar yer kaplıyor: sağdaki taş bilgisi onun üstüne binmesin
            var room = _evContentW - (110f + Mathf.Max(_evTitle.sizeDelta.x, _evSub.preferredWidth) + 24f);
            var x = -14f;   // sağ kenardan sola doğru dizilir

            if (next != null && have > 0)
            {
                // yerleştirme adada (kullanıcı, 20 Ekim 2026): çocuk taşı sisli yere (köprü, mağara yolu, fener…) götürür
                var go = SoftBtn(_evRight, T("stones.go"), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(0f, 64f), new Vector2(x, 2f),
                    () => App.Open(AppPage.Map), 27, "ui_sunstone");
                _goBtn = (RectTransform)go.transform;
                x -= _goBtn.sizeDelta.x + 14f;
            }

            // elindeki taş sayısı (simge + sayı) her zaman; en son, en solda
            var count = Ui.Label(_evRight, have.ToString(), 36, Theme.Hex("#8A3B00"), new Vector2(1f, 0.5f), new Vector2(80f, 50f), FontStyle.Bold, TextAnchor.MiddleRight);
            count.rectTransform.pivot = new Vector2(1f, 0.5f);
            var haveW = 60f + 6f + Mathf.Min(80f, count.preferredWidth);

            if (next == null)
            {
                var done = Ui.Label(_evRight, T("stones.all_done"), 25, Theme.Hex("#5A3000"), new Vector2(1f, 0.5f), new Vector2(320f, 40f), FontStyle.Bold, TextAnchor.MiddleRight, new Vector2(x, 2f));
                done.rectTransform.pivot = new Vector2(1f, 0.5f);
                x -= Mathf.Min(320f, done.preferredWidth) + 12f;
            }
            else
            {
                var placed = SunStoneBook.PlacedIn(st, next.Id);
                var soft = Mathf.Min(have, Mathf.Max(0, next.Cost - placed));   // elde olup henüz konmamış: açık altın
                var left = next.Cost - placed - have;
                var pipW = Mathf.Min(30f, (170f - (next.Cost - 1) * 5f) / next.Cost);
                var pips = PanelKit.Pips(_evRight, next.Cost, placed, soft, pipW, 18f, 5f, new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(x, 2f));
                x -= pips.sizeDelta.x + 14f;
                var name = Ui.Label(_evRight, next.Name, 27, Theme.Hex("#5A3000"), new Vector2(1f, 0.5f), new Vector2(240f, 36f), FontStyle.Bold, TextAnchor.MiddleRight, new Vector2(x, 13f));
                var more = Ui.Label(_evRight, left > 0 ? T("stones.more", left) : T("stones.enough"), 21, Theme.Hex("#8A5A22"), new Vector2(1f, 0.5f), new Vector2(240f, 30f), FontStyle.Bold, TextAnchor.MiddleRight, new Vector2(x, -17f));
                name.rectTransform.pivot = more.rectTransform.pivot = new Vector2(1f, 0.5f);
                var nameW = Mathf.Min(240f, Mathf.Max(name.preferredWidth, more.preferredWidth));
                if (-x + nameW + 14f + haveW > room) { name.gameObject.SetActive(false); more.gameObject.SetActive(false); }   // dar ekran: yer adı düşer
                else x -= nameW + 14f;
            }

            count.rectTransform.anchoredPosition = new Vector2(x, 2f);
            x -= haveW - 60f;
            Ui.IconImage(_evRight, "ui_sunstone", new Vector2(1f, 0.5f), 60f, new Vector2(x - 30f, 2f));
        }

        // ---- Kişisel haftalık hedef (Y6) ----
        private WeeklyGoal _goal;
        private bool _claiming;

        private async void LoadGoal()
        {
            var g = App.Goals != null ? await App.Goals.WeeklyGoalAsync() : null;
            if (this == null) return;
            _goal = g;
            FillWeek();
        }

        private void FillWeek()
        {
            if (_week == null) return;
            Ui.Clear(_week);
            var g = _goal;
            var show = g != null && g.Target.HasValue;   // sunucu önerisi yok ya da bu hafta hedef yok (yalnız ölçüm): satır yok
            _week.gameObject.SetActive(show);
            _listArea.offsetMin = new Vector2(0f, show ? WeekH + 12f : 0f);
            if (!show) return;
            var row = Ui.Fill(_week, "Row");
            PanelKit.Flat(row, new Color(1f, 1f, 1f, 0.55f), 24f);
            Ui.IconImage(row, "ui_gift", new Vector2(0f, 0.5f), 66f, new Vector2(12f + 33f, 0f));
            var x = -16f;
            if (g.CanClaim)
            {
                var b = GoBtn(row, T("goal.claim"), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(230f, 64f), new Vector2(x, 2f), ClaimGoal, 28);
                Hover.On(b, 4f, 0.05f);
                x -= 230f + 16f;
            }
            var total = Mathf.Clamp(g.Target.Value, 1, 10);
            var pips = PanelKit.Pips(row, total, Mathf.Min(g.Done, total), 0, 30f, 18f, 5f, new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(x, 0f));
            x -= pips.sizeDelta.x + 16f;
            var text = g.Claimed ? T("goal.claimed", g.Target.Value) : g.Reached ? T("goal.reached", g.Target.Value) : T("goal.short", g.Target.Value, g.Done);
            var w = _evContentW - 90f + x;
            var t = Ui.Label(row, text, F(26), InkTan, new Vector2(0f, 0.5f), new Vector2(w, WeekH - 8f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(90f, 0f));
            t.rectTransform.pivot = new Vector2(0f, 0.5f);
            Fit(t, F(26));
        }

        private async void ClaimGoal()
        {
            if (_claiming || App.Goals == null) return;
            _claiming = true;
            var r = await App.Goals.ClaimWeeklyGoalAsync();
            _claiming = false;
            if (this == null) return;
            if (r != null && r.Ok)
            {
                var level = App.Levels.Level(App.State.Xp);
                var xp = WeeklyGoal.XpFor(App.Levels.TotalXpFor(level + 1) - App.Levels.TotalXpFor(level));
                Audio.Sfx.Play(Audio.SfxKind.Success);
                StarSparkles.Around(App.Overlay.transform, new Vector2(0.5f, 0.6f), new Vector2(0.22f, 0.22f), 14, 61);
                Toast.Post(App.Overlay.transform, Th, T("goal.done_toast", r.Stones));
                App.GrantXp(xp, Logic.Economy.XpSource.Achievement);
                App.RecordActivity("weekly_goal");
            }
            await App.SyncNow();   // taşlar sunucudan gelir
            if (this == null) return;
            Fill();
            LoadGoal();
        }

        // ---- Oyun görevleri (sağ, mavi): günlük görevler + günlük sandık (S2) ----
        private void FillGame()
        {
            Ui.Clear(_quests);
            Activity.EnsureQuests(App.State, App.Data, App.Levels, App.LocalNow);
            var dq = App.State.DailyQuests;
            var y = 0f;
            var open = 0;
            foreach (var id in dq.Ids)
            {
                var q = App.Data.DailyQuests.FirstOrDefault(x => x.Id == id);
                if (q == null) continue;
                var done = dq.Claimed.Contains(id);
                if (!done) open++;
                y += QuestRow(_quests, y, q, done, Logic.Meta.DailyQuests.Progress(q, App.State.Counters)) + 12f;
            }
            _gem.transform.parent.gameObject.SetActive(open > 0);
            _gem.text = open.ToString();
            ChestRow(_quests, open);
        }

        private void OpenChest()
        {
            var level = App.Levels.Level(App.State.Xp);
            var prize = Logic.Meta.DailyChest.Open(App.State.DailyQuests, App.Data, App.State.Inventory, level, App.State.ChildId ?? "");
            App.Save();
            var item = prize != null ? App.Data.Item(prize.ItemId) : null;
            PlayChest(item != null ? Ui.Icon(item.Id) : null, () =>
            {
                Audio.Sfx.Play(Audio.SfxKind.Success);
                if (item != null) Toast.Post(App.Overlay.transform, Th, T(prize.Quantity > 1 ? "chest.got_n" : "chest.got", item.Name, prize.Quantity));
            });
            Fill();
        }

        // ---- Zor görevde 2× XP teklifi (Y2) ----
        private void BoostOffer(ChildTask task)
        {
            TaskBoosts.MarkOffered(App.State.Boosts, App.LocalNow);
            App.Save();
            RectTransform root = null;
            void Later() { if (root != null) Destroy(root.gameObject); _ = App.Goals?.RecordBoostAsync(task.Key, false); }
            root = Modal(620f, out var box, true, Later);
            var badge = Ui.Rect(box, "Badge", new Vector2(0.5f, 0.76f), new Vector2(220f, 160f));
            Ui.Panel(badge, Theme.Hex("#FFC93C"), 70f);
            Ui.Label(badge, "2×", Th.Font(96), Theme.Hex("#7A3B00"), new Vector2(0.5f, 0.5f), new Vector2(220f, 160f), FontStyle.Bold);
            Hover.On(badge, 5f, 0.1f);
            Ui.Label(box, T("boost.text"), Th.Font(40), Th.Text, new Vector2(0.5f, 0.48f), new Vector2(860f, 160f), FontStyle.Bold);
            Ui.Button(box, Th, T("boost.try"), new Vector2(0.3f, 0.17f), new Vector2(380f, 120f), () =>
            {
                Destroy(root.gameObject);
                var t = App.State.Tasks.Find(task.Key);
                if (t != null && App.State.Tasks.Mark(t.Key, ChildTaskStatus.Assigned, App.LocalNow, App.UtcNow) == ChangeResult.Ok) t.Boosted = true;
                _ = App.Goals?.RecordBoostAsync(task.Key, true);
                Audio.Sfx.Play(Audio.SfxKind.Sparkle);
                App.Save();
                Fill();
                _ = App.SyncNow();
            }, true, default, 44, true, Candy.Green);
            Ui.Button(box, Th, T("boost.later"), new Vector2(0.72f, 0.17f), new Vector2(340f, 120f), Later, false, default, 40);
        }

        private void Mark(ChildTask task, ChildTaskStatus to)
        {
            var r = App.State.Tasks.Mark(task.Key, to, App.LocalNow, App.UtcNow);
            if (r != ChangeResult.Ok) { Fill(); return; }
            if (to == ChildTaskStatus.ChildDone)
            {
                // "Yaptım" hem ilk gün ipucunu hem penceredeki "Yaptım" tanıtımını tamamlar
                if (Onboarding.Pending(App.State, Onboarding.Mark)) Onboarding.Done(App.State, Onboarding.Mark);
                if (Onboarding.Pending(App.State, Onboarding.TasksDone)) Onboarding.Done(App.State, Onboarding.TasksDone);
            }
            App.Save();
            Fill();
            if (to == ChildTaskStatus.ChildDone) AdvanceIfOn(Onboarding.TasksDone, Onboarding.Mark);
            _ = App.SyncNow();
            if (to == ChildTaskStatus.DeclinedByChild && TaskBoosts.ShouldOffer(App.State.Boosts, App.State.Tasks.Find(task.Key), App.LocalNow))
                BoostOffer(task);
        }

        // ------------------------------------------------------------------ bilgilendirme eli (ilk açılış)

        private sealed class IntroStep
        {
            public string Id, Caption;
            public Func<RectTransform> Target;
            public bool Keep;   // iş yapılınca biter (taş yerleştir, Yaptım'a bas); burada yalnız gösterilir
        }

        private readonly List<IntroStep> _intro = new List<IntroStep>();
        private int _introAt = -1;
        private float _introT;
        private Coach _coach;
        private Vector2 _aim;

        /// <summary>
        /// Pencere kalabalık görünmesin (kullanıcı, 24 Ekim 2026): ilk açılışta el sırayla gösterir. Bir adım dokununca ya da el iki tur
        /// gösterip cümle okunacak kadar bekleyince biter, sonraki gelir. Ardından yerleştirilecek taş varsa "Adaya götür".
        /// İlk gün "Yaptım" ipucu (Mark) penceredeki "Yaptım" adımıyla birleşir: aynı açılışta ikisi birden çıkmaz.
        /// </summary>
        private void QueueIntro()
        {
            _intro.Clear();
            var st = App.State;
            var day = FirstDay.Current(st, App.LocalNow, App.UtcNow);
            if (Onboarding.Pending(st, Onboarding.TasksHome)) AddStep(_intro.Count, Onboarding.TasksHome, T("tip.tasks_home"), () => _evTitle, false);
            if (_firstDone != null)
            {
                if (Onboarding.Pending(st, Onboarding.TasksDone)) AddStep(_intro.Count, Onboarding.TasksDone, T("tip.tasks_done"), () => _firstDone, false);
                else if (day == FirstDayStep.Mark && Onboarding.Pending(st, Onboarding.Mark)) AddStep(_intro.Count, Onboarding.Mark, T("tip.mark"), () => _firstDone, true);
            }
            if (Onboarding.Pending(st, Onboarding.TasksGame)) AddStep(_intro.Count, Onboarding.TasksGame, T("tip.tasks_game"), () => _oyTitle, false);
            var next = App.Data.SunBook.Next(st.SunStones);
            if (_goBtn != null && next != null && Onboarding.Pending(st, Onboarding.Stone))
                AddStep(_intro.Count, Onboarding.Stone, T("tip.stone_go", next.Name), () => _goBtn, true);
            _introAt = _intro.Count > 0 ? 0 : -1;
            _introT = -0.7f;   // pencere büyüyerek açılırken bekle
        }

        private void AddStep(int at, string id, string caption, Func<RectTransform> target, bool keep) =>
            _intro.Insert(at, new IntroStep { Id = id, Caption = caption, Target = target, Keep = keep });

        /// <summary>Görevler eşitlemeyle sonradan geldiyse "Yaptım" adımı sıradakine eklenir.</summary>
        private void UpdateIntro()
        {
            if (_introAt < 0 || _firstDone == null || !Onboarding.Pending(App.State, Onboarding.TasksDone)) return;
            if (_intro.Any(s => s.Id == Onboarding.TasksDone || s.Id == Onboarding.Mark)) return;
            AddStep(Mathf.Min(_introAt + 1, _intro.Count), Onboarding.TasksDone, T("tip.tasks_done"), () => _firstDone, false);
        }

        private void Update()
        {
            if (_introAt < 0 || _introAt >= _intro.Count || App == null) return;
            if (Root.Find("Modal") != null) return;   // ebeveyn sorusu, 2× teklifi açıkken bekle
            _introT += Time.unscaledDeltaTime;
            if (_introT < 0f) return;
            var s = _intro[_introAt];
            if (_coach == null)
            {
                var rt = s.Target();
                if (rt == null) { NextStep(); return; }
                _aim = Center(rt);
                var label = _intro.Count > 1 ? (_introAt + 1) + "/" + _intro.Count : null;
                _coach = Coach.Show(Root, s.Id, s.Caption, TipGesture.Tap, () => Aim(s), null, 2, label);
                _introT = 0f;
                return;
            }
            var tapped = _introT > 0.8f && (Input.GetMouseButtonDown(0) || (Input.touchCount > 0 && Input.GetTouch(0).phase == TouchPhase.Began));
            if (tapped || s.Target() == null || _introT > 5.4f) NextStep();
        }

        private Vector2 Aim(IntroStep s)
        {
            var rt = s.Target();
            if (rt != null) _aim = Center(rt);
            return _aim;
        }

        private static Vector2 Center(RectTransform rt) => RectTransformUtility.WorldToScreenPoint(null, rt.TransformPoint(rt.rect.center));

        private void NextStep()
        {
            if (_introAt < 0 || _introAt >= _intro.Count) { _introAt = -1; return; }
            var s = _intro[_introAt];
            if (!s.Keep && Onboarding.Pending(App.State, s.Id)) { Onboarding.Done(App.State, s.Id); App.Save(); }
            if (_coach != null) { _coach.Done(); _coach = null; }
            _introAt++;
            _introT = -0.3f;
            if (_introAt >= _intro.Count) { _introAt = -1; _intro.Clear(); }
        }

        private void AdvanceIfOn(params string[] ids)
        {
            if (_introAt >= 0 && _introAt < _intro.Count && Array.IndexOf(ids, _intro[_introAt].Id) >= 0) NextStep();
        }

        // ------------------------------------------------------------------ deneme ebeveyn paneli (yalnızca sahte sunucu)

        private void OpenDemoPanel()
        {
            var root = Modal(820f, out var box);
            ModalTitle(box, T("demo.title"));
            Ui.Label(box, T("demo.info"), Th.Font(32), Th.SubtleText, new Vector2(0.5f, 0.79f), new Vector2(860f, 110f));
            var pending = Ui.Label(box, T("demo.pending", DemoParent.Pending(App.Backend)), Th.Font(44), Th.Text, new Vector2(0.5f, 0.64f), new Vector2(860f, 70f), FontStyle.Bold);
            Ui.Button(box, Th, T("demo.approve_all"), new Vector2(0.5f, 0.5f), new Vector2(700f, 120f), async () =>
            {
                DemoParent.ApproveAll(App.Backend);
                Destroy(root.gameObject);
                await App.SyncNow();
            });
            Ui.Button(box, Th, T("demo.new_tasks"), new Vector2(0.5f, 0.355f), new Vector2(700f, 100f), async () =>
            {
                DemoParent.EnsureToday(App.Backend, App.LocalNow);
                Destroy(root.gameObject);
                await App.SyncNow();
            }, false, default, 40);
            Ui.Button(box, Th, T("demo.give_rewards"), new Vector2(0.5f, 0.225f), new Vector2(700f, 100f), async () =>
            {
                DemoParent.GiveRewards(App.Backend);
                Destroy(root.gameObject);
                await App.SyncNow();
            }, false, default, 40);
            Ui.Button(box, Th, T("demo.close"), new Vector2(0.5f, 0.09f), new Vector2(400f, 100f), () => Destroy(root.gameObject), false, default, 40);
            pending.name = "Pending";
        }

        private void OnDestroy()
        {
            if (App != null) App.Synced -= OnSynced;
        }
    }
}
