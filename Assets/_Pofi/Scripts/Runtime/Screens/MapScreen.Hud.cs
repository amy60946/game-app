using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Island;
using Pofi.Logic.Pet;
using Pofi.Logic.Core;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Adanın sahne üstü arayüzü (14 Ekim 2026 kararı): sol üst pet rozeti + 4 gösterge halkası, sağ üst coin / kuşbakışı /
    /// görev kısayolu, sol kenar Besle–Yıka (her yerde; yiyecek yoksa dükkâna koşar), sol alt yüzen joystick,
    /// sağ alt bağlamsal eylem tuşu (Zıpla / Gir / Oyna / Topla). Panel ve alt menü yok.
    /// </summary>
    public sealed partial class MapScreen
    {
        private static readonly StatKind[] HudKinds = { StatKind.Fullness, StatKind.Cleanliness, StatKind.Happiness, StatKind.Home };
        private static readonly string[] HudIcons = { "food_apple", "clean_soap", "ui_heart", "home_bed" };

        private readonly Image[] _gauges = new Image[4];
        private Text _levelText, _levelNum, _coinText, _stoneText, _feedCount, _washCount, _actionText;
        private RectTransform _action, _stickBase, _stickKnob, _tray, _leftBar;
        private System.Action _actionDo;
        private Image _actionIcon;
        private string _actionKey;
        private float _hudTick, _statTick;
        private readonly Dictionary<int, Transform> _sparkleObjs = new Dictionary<int, Transform>();
        private Coach _coach;
        private float _islandTime;
        private RectTransform _levelBadge, _tasksBtn, _mapBtn;
        private Text _questCount;
        private RectTransform _feedBtn, _washBtn;
        private int _lastCoins = -1, _lastStones = -1;
        private float _questT;
        private Image _xpFill;
        private RectTransform _trophy;
        private Text _trophyCount;

        private void BuildHud()
        {
            var hud = Ui.Fill(Root, "Hud");
            // sol üst
            // pet kartı: madalyon + isim plakası + seviye yıldızı + XP kapsülü (Candy.PetPlate)
            var pet = App.Data.Pet(App.State.PetId);
            _levelBadge = Candy.PetPlate(hud, App.State.PetId, Theme.Hex(pet.MainColor), new Vector2(10f, -10f), out _levelText, out _levelNum, out _xpFill);
            // pet kartı dokunulur: Defter rozetler sekmesiyle açılır (XP takibi M4: "rozetleri oyunda göremedim").
            // XP kapsülünün sağında küçük kupa + kazanılan rozet sayısı.
            var plateHit = _levelBadge.gameObject.AddComponent<Image>(); plateHit.color = new Color(1f, 1f, 1f, 0f);
            var plateBtn = _levelBadge.gameObject.AddComponent<Button>(); plateBtn.targetGraphic = plateHit; plateBtn.transition = Selectable.Transition.None;
            plateBtn.onClick.AddListener(() => { Audio.Sfx.Play(Audio.SfxKind.Tap); AlbumScreen.ShowBadges(); App.Open(AppPage.Album); });
            _trophy = Ui.Rect(_levelBadge, "Trophy", new Vector2(0f, 1f), new Vector2(84f, 84f), new Vector2(506f, -116f));
            var ti = Ui.IconImage(_trophy, "ui_trophy", new Vector2(0.5f, 0.5f), 84f);
            if (ti != null) ti.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -4f);
            _trophyCount = Candy.Count(_trophy, 40f);
            // Yerleşim v3 taslağına göre (kullanıcı onayı, 19 Ekim 2026): halkalar küçük, rozetin altında; sol sütun Görev + Ev Görevleri;
            // üst orta Güneş Taşı + coin; sağ üst yuvarlak Harita ve Ayarlar; sol alt Besle/Yıka; sağ alt eylem.
            Color[] cols = { new Color(1f, 0.62f, 0.26f), new Color(0.24f, 0.79f, 1f), new Color(1f, 0.44f, 0.68f), new Color(0.48f, 0.84f, 0.42f) };
            for (var i = 0; i < 4; i++)
                _gauges[i] = Candy.Gauge(hud, cols[i], HudIcons[i], 96f, new Vector2(0f, 1f), new Vector2(16f + 48f + i * 110f, -244f));

            // üst orta: Güneş Taşı ve coin
            _stoneText = Candy.ResourcePlate(hud, "ui_sunstone", Vector2.zero, 300f);   // Güneş Taşı (yerleştirilebilir)
            TopCenter(_stoneText, -170f);
            _coinText = Candy.CoinPlate(hud, Vector2.zero, 300f);
            TopCenter(_coinText, 170f);

            // sağ üst: Harita (kuşbakışı / yürü) ve Ayarlar
            // kenarlara yakın (kullanıcı, 20 Ekim 2026)
            var map = Candy.Round(hud, Candy.White, "ui_map", 160f, new Vector2(1f, 1f), new Vector2(-92f, -100f), ToggleMode, T("map.overview"));
            _modeText = map.GetComponentInChildren<Text>();
            _mapBtn = (RectTransform)map.transform;
            // Ayarlar (kullanıcı, 19 Ekim 2026: "oyundan çıkamıyorum"): ses, pet değiştir, çıkış; Evim'e gitmeden. Ebeveyn sorusuyla açılır.
            // müzik düğmesinin (UI.MusicButton: sağ üst −386, −66, 92 birim) solunda, aynı boyda ve yazısız
            Candy.Round(hud, Candy.White, "ui_settings", 92f, new Vector2(1f, 1f), new Vector2(-496f, -66f),
                () => ParentGate(() => App.Open(AppPage.Settings), msg => _toast.Say(msg)));

            // sol sütun: oyun içi görevler ve ebeveynin Ev Görevleri
            var tasks = Candy.Round(hud, Candy.White, "ui_star", 150f, new Vector2(0f, 1f), new Vector2(98f, -400f), GoTasks, T("hud.tasks"));
            _tasksBtn = (RectTransform)tasks.transform;
            _questCount = Candy.Count(tasks.transform);   // bugün açık oyun içi görev sayısı
            Candy.Round(hud, Candy.White, "ui_board", 150f, new Vector2(0f, 1f), new Vector2(98f, -605f), () => App.Open(AppPage.Tasks), T("tasks.title"));
            var next = App.Map.NextToUnlock(App.Level, App.State.VisitedRegions, App.Data.SunBook, App.State.SunStones);
            if (next != null)
                Candy.Caption(hud, T("map.next", next.Region.Name, next.UnlockLevel), 32, new Vector2(0.5f, 0f), new Vector2(900f, 56f), new Vector2(0f, 46f));

            // sol kenar: Besle, Yıka
            _leftBar = Ui.Rect(hud, "Care", Vector2.zero, new Vector2(420f, 260f), new Vector2(196f, 172f));
            var feed = Candy.Round(_leftBar, Candy.White, "food_apple", 150f, new Vector2(0.3f, 0.6f), Vector2.zero, OnFeed, T("hud.feed"));
            _feedBtn = (RectTransform)feed.transform;
            _feedCount = Candy.Count(feed.transform);
            var wash = Candy.Round(_leftBar, Candy.White, "clean_soap", 124f, new Vector2(0.75f, 0.42f), Vector2.zero, OnWash, T("hud.wash"));
            _washBtn = (RectTransform)wash.transform;
            _washCount = Candy.Count(wash.transform);

            // sağ alt: bağlamsal eylem
            // simgesi o anki eyleme göre değişir (balta, el, kazma, çekiç, zıpla, kapı, oyna); altında kısa yazı
            var act = Candy.Round(hud, Candy.White, "act_jump", 230f, new Vector2(1f, 0f), new Vector2(-150f, 205f), () => _actionDo?.Invoke(), T("hud.jump"));
            _action = (RectTransform)act.transform;
            _actionText = act.GetComponentInChildren<Text>();
            var ai = act.transform.Find("Icon act_jump");
            _actionIcon = ai != null ? ai.GetComponent<Image>() : null;
            BuildTracker(hud);

            // sol alt: yüzen joystick (parmak değince belirir)
            _stickBase = Ui.Rect(hud, "Stick", Vector2.zero, new Vector2(250f, 250f));
            var sb = _stickBase.gameObject.AddComponent<Image>(); sb.sprite = Ui.Rounded; sb.type = Image.Type.Sliced; sb.pixelsPerUnitMultiplier = 0.48f; sb.color = new Color(1f, 1f, 1f, 0.25f); sb.raycastTarget = false;   // tam daire
            var so = _stickBase.gameObject.AddComponent<Outline>(); so.effectColor = new Color(1f, 1f, 1f, 0.7f); so.effectDistance = new Vector2(4f, -4f);
            _stickKnob = Ui.Rect(_stickBase, "Knob", new Vector2(0.5f, 0.5f), new Vector2(120f, 120f));
            var kb = _stickKnob.gameObject.AddComponent<Image>(); kb.sprite = Ui.Rounded; kb.type = Image.Type.Sliced; kb.color = new Color(1f, 1f, 1f, 0.9f); kb.raycastTarget = false;
            _stickKnob.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
            _stickBase.gameObject.SetActive(false);

            App.XpGained += OnXp;
            App.Synced += OnSyncedFx;
            App.BadgeEarned += OnBadge;
            RefreshHud();
        }

        /// <summary>Kaynak göstergesini (Candy.ResourcePlate) üst ortaya taşır: x merkeze göre.</summary>
        private static void TopCenter(Text plateText, float x)
        {
            var rt = (RectTransform)plateText.transform.parent;
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 1f);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = new Vector2(x, -30f);
        }

        private void HudDestroy()
        {
            if (App != null) { App.XpGained -= OnXp; App.Synced -= OnSyncedFx; App.BadgeEarned -= OnBadge; }
        }

        /// <summary>Rozet kazanınca (M4): pet sevinir, kupa yaylanır ve sayısı artar; rozetin XP'si ayrıca yıldız olarak akar.</summary>
        private void OnBadge(int n)
        {
            if (this == null) return;
            RefreshHud();
            if (_trophy != null) Bump.Play(_trophy, 0.4f);
            Audio.Sfx.Play(Audio.SfxKind.Chime);
            if (_world != null && _world.Walker != null && !_overview) _world.Walker.Cheer();
        }

        /// <summary>Bir sonraki XP kazanımının dünyada doğduğu yer (parıltı, kulübe…); yoksa parçalar petin üstünde doğar.</summary>
        private Vector3? _xpFrom;

        private float PetHeight => _world != null && _world.Walker != null ? PetModels.RealHeight * _world.Walker.transform.lossyScale.y : 1f;

        /// <summary>3B kazanım efekti (S4): parçalar pete akar; bitince gösterge yaylanır.</summary>
        private void GainFx3D(GainFx.Kind kind, int amount, Vector3? from)
        {
            var w = _world != null ? _world.Walker : null;
            if (w == null || _overview || amount <= 0) return;
            System.Action done = () =>
            {
                if (this == null) return;
                if (kind == GainFx.Kind.Xp && _levelBadge != null) Bump.Play(_levelBadge, 0.25f);
                if (kind == GainFx.Kind.Stone && _stoneText != null) Bump.Play(_stoneText.transform.parent, 0.3f);
            };
            if (from.HasValue) GainFx.Play(kind, amount, from.Value, w.transform, PetHeight, done);
            else GainFx.AroundPet(kind, amount, w.transform, PetHeight, done);
        }

        /// <summary>Senkronda gelen Güneş Taşı (ebeveyn onayı): altın kristaller gökten pete iner.</summary>
        private void OnSyncedFx(Logic.State.SyncReport r)
        {
            if (this == null || r == null) return;
            if (r.SunStonesEarned > 0) GainFx3D(GainFx.Kind.Stone, r.SunStonesEarned, null);
        }

        /// <summary>XP kazanınca rozetin yanında "+N ★" süzülür; ilk seferde XP ipucu.</summary>
        private void OnXp(int n)
        {
            if (this == null || _levelBadge == null) return;
            var f = Ui.Rect(_levelBadge.parent, "XpGain", new Vector2(0f, 1f), new Vector2(240f, 90f), new Vector2(620f, -70f));
            Ui.IconImage(f, "ui_star", new Vector2(0f, 0.5f), 80f, new Vector2(40f, 0f));
            Candy.Caption(f, T("xp.star", n), 56, new Vector2(0.5f, 0.5f), new Vector2(160f, 90f), new Vector2(40f, 0f));
            f.gameObject.AddComponent<FloatUp>();
            var from = _xpFrom; _xpFrom = null;
            GainFx3D(GainFx.Kind.Xp, n, from);
            RefreshHud();
            if (Onboarding.Pending(App.State, Onboarding.Xp))
            {
                TipDone(null);
                Tip(Onboarding.Xp, TipGesture.Tap, () => UiScreen(_levelBadge));
                _xpTipT = 6f;
            }
        }

        private float _xpTipT;

        private void RefreshHud()
        {
            var st = App.State;
            for (var i = 0; i < 4; i++)
            {
                var f = st.Stats[HudKinds[i]] / 100f;
                if (f > _gauges[i].fillAmount + 0.02f) Bump.Play(_gauges[i].transform.parent, 0.18f);   // besleyince/yıkayınca halka zıplar
                _gauges[i].fillAmount = f;
            }
            var coins = st.Wallet.Available; var stones = Logic.Island.SunStoneBook.Available(st.SunStones);
            if (_lastCoins >= 0 && coins != _lastCoins) Bump.Play(_coinText.transform.parent);
            if (_lastStones >= 0 && stones != _lastStones) Bump.Play(_stoneText.transform.parent, 0.3f);
            _lastCoins = coins; _lastStones = stones;
            _levelText.text = st.PetName;
            _levelNum.text = App.Level.ToString();
            if (_trophyCount != null)
            {
                var nb = st.Badges.Count;
                _trophyCount.text = nb.ToString();
                _trophyCount.transform.parent.gameObject.SetActive(nb > 0);
            }
            _coinText.text = st.Wallet.Available.ToString();
            _stoneText.text = Logic.Island.SunStoneBook.Available(st.SunStones).ToString();
            Ui.SetBar(_xpFill, App.Levels.ProgressInLevel(st.Xp.TotalXp));
            if ((_questT -= Time.deltaTime) <= 0f) { _questT = 1f; SetCount(_questCount, OpenQuests()); }
            SetCount(_feedCount, Count(ItemCategory.Food));
            SetCount(_washCount, Count(ItemCategory.Cleaning));
        }

        private static void SetCount(Text t, int n)
        {
            t.text = n.ToString();
            t.transform.parent.GetComponent<Image>().enabled = true;
        }

        private int Count(string category) =>
            App.State.Inventory.Counts.Where(kv => App.Data.Item(kv.Key)?.Category == category).Sum(kv => kv.Value);

        private void UpdateHud()
        {
            _statTick += Time.deltaTime;
            if (_statTick >= 1f) { _statTick = 0f; App.State.Stats.Tick(App.UtcNow, App.Decay); }
            _hudTick += Time.deltaTime;
            if (_hudTick >= 0.5f) { _hudTick = 0f; RefreshHud(); }

            var walking = !_overview && _world.Walker != null;
            _leftBar.gameObject.SetActive(walking);
            _action.gameObject.SetActive(walking);
            if (!walking) { CloseTray(); return; }
            UpdateAction();
            _islandTime += Time.deltaTime;
            UpdateTips();
        }

        // ------------------------------------------------------------------ tanıtım ipuçları (docs/ONBOARDING.md)

        private string PetGen => Logic.Core.TurkishSuffix.Genitive(App.State.PetName);

        // Tanıtım sırası (kullanıcı isteği, 15 Ekim 2026): hepsi arka arkaya değil, biri tamamlanınca kısa ara, sonra sıradaki;
        // panelde "adım/toplam" görünür. Bağlamsal olanlar (kapı, oyun yeri, parıltı) uygun anda araya girer.
        private static readonly string[] TipSeq =
            { Onboarding.Walk, Onboarding.Look, Onboarding.Jump, Onboarding.Wardrobe, Onboarding.Feed, Onboarding.Tasks, Onboarding.Overview };
        private float _tipGap = 1.5f;

        private void Tip(string id, TipGesture g, System.Func<Vector2> from, System.Func<Vector2> to = null, string arg = null, Sprite prop = null, string key = null)
        {
            if (_coach != null || !Onboarding.Pending(App.State, id)) return;
            if (!FirstDay.AllowsTip(FirstDayNow, id)) return;   // ilk gün: yalnız ilk gün ipuçları (Ö5)
            var i = System.Array.IndexOf(TipSeq, id);
            var step = i >= 0 ? (i + 1) + "/" + TipSeq.Length : null;
            _coach = Coach.Show(Root, id, T(key ?? Onboarding.Get(id).CaptionKey, arg ?? App.State.PetName), g, from, to, 3, step, prop);
        }

        /// <summary>İpucu tamamlandı (id null: yalnız ekrandakini kapat).</summary>
        private void TipDone(string id)
        {
            if (id != null && Onboarding.Pending(App.State, id)) { Onboarding.Done(App.State, id); App.Save(); }
            if (_coach != null && (id == null || _coach.Id == id)) { _coach.Done(); _coach = null; _tipGap = 0f; }
        }

        private FirstDayStep FirstDayNow => FirstDay.Current(App.State, App.LocalNow, App.UtcNow);

        /// <summary>Haritadaki bölgenin ekran noktası (yapının biraz üstü).</summary>
        private Vector2 RegionScreen(string id)
        {
            var r = App.Map.Find(id);
            if (r == null) return PetScreen();
            return App.Stage.Camera.WorldToScreenPoint(_world.World(r.X, r.Z) + Vector3.up * 3f);
        }

        private static Vector2 UiScreen(RectTransform rt) => RectTransformUtility.WorldToScreenPoint(null, rt.position);
        private Vector2 PetScreen() => App.Stage.Camera.WorldToScreenPoint(_world.Walker.transform.position + Vector3.up * 1.0f);

        private void UpdateTips()
        {
            if (_xpTipT > 0f) { _xpTipT -= Time.deltaTime; if (_xpTipT <= 0f) TipDone(Onboarding.Xp); }
            var guide = Guide.Current(App.State, App.Level);
            if (_coach != null && _coach.Id.StartsWith("guide_") && (guide == null || _coach.Id != "guide_" + guide.Id)) { _coach.Done(); _coach = null; _tipGap = 1f; }   // adım bitti
            if (_coach != null || _tray != null) return;
            _tipGap += Time.deltaTime;
            if (_tipGap < 2.5f) return;                                     // ipuçları arasında kısa nefes
            var st = App.State;
            var basicsDone = !Onboarding.Pending(st, Onboarding.Walk) && !Onboarding.Pending(st, Onboarding.Look);
            if (basicsDone)
            {
                if (_actionKey == "hud.enter") { Tip(Onboarding.Enter, TipGesture.Tap, () => UiScreen(_action)); if (_coach != null) return; }
                if (_actionKey == "hud.play") { Tip(Onboarding.Play, TipGesture.Tap, () => UiScreen(_action)); if (_coach != null) return; }
                foreach (var kv in _sparkleObjs)
                {
                    if (kv.Value == null || !Onboarding.Pending(st, Onboarding.Sparkle)) break;
                    if (Vector3.Distance(kv.Value.position, _world.Walker.transform.position) < 14f)
                    {
                        var tr = kv.Value;
                        Tip(Onboarding.Sparkle, TipGesture.Tap, () => tr != null ? (Vector2)App.Stage.Camera.WorldToScreenPoint(tr.position) : PetScreen());
                        return;
                    }
                }
            }
            // rehberli zincir (Sv1–3): sıradaki adım, işaret eli hedefini gösterir; ilk gün pano/taş ipuçlarının yerine geçer
            if (basicsDone && guide != null && !_overview) { GuideTip(guide); return; }
            // ilk gün (Ö5): yürü → besle → Ev Görevleri panosu (görev işaretle / taşı yerleştir orada)
            var day = FirstDayNow;
            if (day == FirstDayStep.Board) { Tip(Onboarding.Board, TipGesture.Tap, () => RegionScreen("region_task_board")); return; }
            if (day == FirstDayStep.Mark) { Tip(Onboarding.Mark, TipGesture.Tap, () => RegionScreen("region_task_board"), null, null, null, "tip.board"); return; }
            if (day == FirstDayStep.Stone) { Tip(Onboarding.Stone, TipGesture.Tap, () => RegionScreen(App.Data.SunBook.Next(App.State.SunStones)?.Region ?? "region_task_board"), null, null, null, "tip.stone_spot"); return; }
            var next = TipSeq.FirstOrDefault(id => Onboarding.Pending(st, id) && FirstDay.AllowsTip(day, id));
            switch (next)
            {
                case Onboarding.Walk:      // sol yarı: joystick
                    Tip(next, TipGesture.Slide, () => new Vector2(Screen.width * 0.25f, Screen.height * 0.3f), () => new Vector2(Screen.width * 0.25f, Screen.height * 0.55f));
                    break;
                case Onboarding.Look:      // sağ yarı: kamerayı döndür
                    Tip(next, TipGesture.Slide, () => new Vector2(Screen.width * 0.78f, Screen.height * 0.45f), () => new Vector2(Screen.width * 0.58f, Screen.height * 0.45f));
                    break;
                case Onboarding.Jump:
                    if (_actionKey == "hud.jump") Tip(next, TipGesture.Tap, () => UiScreen(_action));
                    break;
                case Onboarding.Wardrobe:  // pete dokun → giydirme; dokundukça başının üstünde şapka belirir
                    Tip(next, TipGesture.Tap, PetScreen, null, PetGen, Ui.Icon("hat_straw"));
                    break;
                case Onboarding.Feed:      // önce Besle'ye dokun; tepsi açılınca sürükleme ipucu gelir
                    Tip(next, TipGesture.Tap, () => UiScreen(_feedBtn), null, PetGen, null, "tip.feed_open");
                    break;
                case Onboarding.Tasks:
                    Tip(next, TipGesture.Tap, () => UiScreen(_tasksBtn));
                    break;
                case Onboarding.Overview:
                    Tip(next, TipGesture.Tap, () => UiScreen(_mapBtn));
                    break;
            }
        }

        /// <summary>Rehber adımı paneli (alt şerit): "3/12", kısa cümle ve ödül; el hedefe 3 kez dokunur, sonra kısa ara.</summary>
        private void GuideTip(GuideStep g)
        {
            var step = (Guide.DoneCount(App.State) + 1) + "/" + Guide.Steps.Count;
            _coach = Coach.Show(Root, "guide_" + g.Id, T(g.TextKey, App.State.PetName) + "  " + T("guide.reward", g.Xp), TipGesture.Tap, GuideTarget(g), null, 3, step);
            _tipGap = -4f;   // panel kapanınca birkaç saniye nefes
        }

        private System.Func<Vector2> GuideTarget(GuideStep g)
        {
            switch (g.Id)
            {
                case "feed": return () => UiScreen(_feedBtn);
                case "wash": return () => UiScreen(_washBtn);
                case "home": case "tidy": return () => RegionScreen("region_home");
                case "wear": return PetScreen;
                case "board": return () => RegionScreen("region_task_board");
                case "stone": return () => RegionScreen(App.Data.SunBook.Next(App.State.SunStones)?.Region ?? "region_task_board");
                case "gather": return NearestGatherScreen;
                case "hut": return () => App.Stage.Camera.WorldToScreenPoint(_world.World(_sitePos.x, _sitePos.z) + Vector3.up * 1.5f);
                case "coconut": return () => RegionScreen("region_coconut_grove");
                case "shop": return () => RegionScreen("region_shop");
                case "cards": return () => RegionScreen("region_game_hut");
                default: return PetScreen;
            }
        }

        /// <summary>En yakın toplanabilir kütük/çalı/taş (ekran noktası); yoksa pet.</summary>
        private Vector2 NearestGatherScreen()
        {
            var p = _world.Walker.Position;
            GatherNode best = null; var bd = float.MaxValue;
            foreach (var n in _gNodes)
            {
                var d = Vector2.Distance(p, new Vector2(n.X, n.Z));
                if (d < bd) { bd = d; best = n; }
            }
            if (best == null) return PetScreen();
            return App.Stage.Camera.WorldToScreenPoint(_world.World(best.X, best.Z) + Vector3.up * 1.2f);
        }

        // ------------------------------------------------------------------ bağlamsal eylem

        private void UpdateAction()
        {
            var p = _world.Walker.Position;
            string key = "hud.jump", icon = "act_jump";
            System.Action act = () => _world.Walker.Jump();
            if (GatherAction(out var gk, out var gicon, out var gact)) { key = gk; icon = gicon; act = gact; }

            // yakında parıltı → Topla (ada aksiyonu yoksa)
            foreach (var kv in _sparkleObjs)
            {
                if (key != "hud.jump") break;
                if (kv.Value == null) continue;
                var sp = _world.Local(kv.Value.position);
                var dist = Vector2.Distance(sp, p);
                var fl = kv.Value.GetComponent<SparkleFloat>();
                if (fl != null) fl.Near = 1f - (dist - 1.2f) / 3f;
                if (dist < 1.2f)
                {
                    // üstünden geçince kendiliğinden açılır (kullanıcı, 22 Ekim 2026)
                    var auto = kv.Value.gameObject;
                    Collect(auto, auto.name);
                    break;
                }
                if (dist < 2.6f)
                {
                    var go = kv.Value.gameObject;
                    key = "hud.collect"; icon = "tool_hand"; act = () => Collect(go, go.name);
                    break;
                }
            }
            if (key == "hud.jump" && SpotAction(p, out var sact)) { key = "hud.place"; icon = "ui_sunstone"; act = sact; }
            if (key == "hud.jump")
            {
                // kapı önünde ya da yapının herhangi bir kenarına yakın → Gir / Oyna (kullanıcı, 19 Ekim 2026: illa kapıya
                // gitmesin; bahçe, oyun kulübesi, dükkân, sörf plajı gibi yerlerin her yanından açılır)
                RegionView best = null; var bd = 3.4f;
                foreach (var v in _views)
                {
                    if (!v.Unlocked) continue;
                    var (dx, dz) = _terrain.Door(v.Region);
                    var d = Vector2.Distance(p, new Vector2(dx, dz));
                    var edge = Vector2.Distance(p, new Vector2(v.Region.X, v.Region.Z)) - v.Region.Size * 0.55f;   // tabana uzaklık
                    d = Mathf.Min(d, Mathf.Max(0f, edge) + 1.2f);   // kenarda ≈ 1,2 (kapı 3,4'ün içinde)
                    if (d < bd) { bd = d; best = v; }
                }
                if (best != null)
                {
                    var v = best;
                    key = IsPlayPlace(v.Region) ? "hud.play" : "hud.enter";
                    icon = key == "hud.play" ? "act_play" : "act_enter";
                    act = () => EnterRegion(v);
                }
            }
            var k2 = key;
            _actionDo = () => { TipDone(k2 == "hud.jump" ? Onboarding.Jump : k2 == "hud.play" ? Onboarding.Play : k2 == "hud.enter" ? Onboarding.Enter : null); act(); };
            if (_actionKey != key)
            {
                _actionKey = key; _actionText.text = T(key);
                if (_actionIcon != null) { var sp = Ui.Icon(icon); if (sp != null) _actionIcon.sprite = sp; }
                _action.localScale = Vector3.one * 1.12f;   // değişince küçük "pop"
            }
            _action.localScale = Vector3.Lerp(_action.localScale, Vector3.one, Time.deltaTime * 8f);
        }

        /// <summary>
        /// Güneş Taşı onarım noktası (sisli kilitli bölge) yakınında mı (kullanıcı, 20 Ekim 2026: taş panoda değil, adada ilgili yere
        /// götürülerek konur)? Eylem: taş varsa ve sıradaki noktaysa yerleştir; yoksa nedenini söyle.
        /// </summary>
        private bool SpotAction(Vector2 p, out System.Action act)
        {
            act = null;
            foreach (var v in _views)
            {
                if (v.Unlocked || v.Spot == null) continue;
                var edge = Vector2.Distance(p, new Vector2(v.Region.X, v.Region.Z)) - v.Region.Size * 0.55f;
                if (edge > 2.6f) continue;
                var spot = v.Spot;
                act = () => PlaceStone(spot);
                return true;
            }
            return false;
        }

        private void PlaceStone(SunSpotDef spot)
        {
            var st = App.State.SunStones;
            var r = App.Data.SunBook.PlaceOne(st, spot.Id);
            switch (r)
            {
                case PlaceResult.NoStones:
                    _toast.Say(T("map.locked_stones", App.Map.Find(spot.Region)?.Name ?? spot.Name, spot.Cost - SunStoneBook.PlacedIn(st, spot.Id)));
                    Audio.Sfx.Play(Audio.SfxKind.Fail);
                    return;
                case PlaceResult.NotNext:
                    _toast.Say(T("stones.not_next", App.Data.SunBook.Next(st)?.Name ?? ""));
                    Audio.Sfx.Play(Audio.SfxKind.Fail);
                    return;
                case PlaceResult.AlreadyRepaired:
                    return;
            }
            if (Onboarding.Pending(App.State, Onboarding.Stone)) Onboarding.Done(App.State, Onboarding.Stone);
            Audio.Sfx.Play(Audio.SfxKind.Success);
            Audio.Haptics.Medium();
            _world.Walker?.Jump();
            var sp = PetScreen();
            StarSparkles.Around(Root, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.14f, 0.2f), 10, 11);
            App.Save();
            App.RecordActivity("stone_placed");
            if (r == PlaceResult.Repaired)
            {
                Toast.Post(App.Overlay.transform, Th, string.IsNullOrEmpty(spot.Say) ? T("stones.all_done") : spot.Say);
                App.Route();   // sis kalkar, bölge açılır (ada yeniden kurulur)
            }
            else _toast.Say(T("stones.placed_more", spot.Cost - SunStoneBook.PlacedIn(st, spot.Id)));
        }

        /// <summary>Mini oyun ya da masa oyunu bölgesi mi (üstünde "Oyna!" çağrısı gösterilir)?</summary>
        private static bool IsPlayPlace(RegionDef r)
        {
            var kind = IslandMap.KindOf(r.Target, out _);
            return kind == RegionTargetKind.MiniGame || kind == RegionTargetKind.Cards;
        }

        // ------------------------------------------------------------------ bakım

        private void OnFeed() => OpenTray(ItemCategory.Food, CareAction.Feed, Onboarding.Feed, "hud.no_food");
        private void OnWash() => OpenTray(ItemCategory.Cleaning, CareAction.Wash, Onboarding.Wash, "hud.no_soap");

        /// <summary>Tepsi: eldeki yiyecek/sabunlar; basılı tutup pete sürükleyince kullanılır (el becerisi, madde 7).</summary>
        private void OpenTray(string category, CareAction action, string tip, string emptyKey)
        {
            if (_tray != null) { CloseTray(); return; }
            var items = App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .Where(it => it != null && it.Category == category).ToList();
            if (items.Count == 0) { RunToShop(T(emptyKey)); return; }
            _tray = Ui.Rect(_leftBar.parent, "Tray", new Vector2(0f, 0.5f), new Vector2(items.Count * 150f + 30f, 170f), Vector2.zero);
            _tray.pivot = new Vector2(0f, 0.5f);
            _tray.anchoredPosition = new Vector2(250f, action == CareAction.Feed ? 30f : -150f);
            RectTransform first = null;
            for (var i = 0; i < items.Count; i++)
            {
                var it = items[i];
                var b = Candy.Round(_tray, Candy.White, it.Id, 130f, new Vector2(0f, 0.5f), new Vector2(80f + i * 150f, 0f), null);
                Candy.Count(b.transform).text = App.State.Inventory.CountOf(it.Id).ToString();
                var d = b.gameObject.AddComponent<DragItem>();
                d.IconId = it.Id; d.Layer = Root;
                d.Dropped = pos => { if (!OverPet(pos)) return false; Care(action, it); return true; };
                d.Tapped = () => { _toast.Say(T("tip." + tip, PetGen)); TipDone(null); ShowDragTip(tip, (RectTransform)b.transform, true); };
                if (first == null) first = (RectTransform)b.transform;
            }
            ShowDragTip(tip, first, false);
        }

        private void ShowDragTip(string tip, RectTransform from, bool force)
        {
            if (from == null || (!force && !Onboarding.Pending(App.State, tip))) return;
            if (_coach != null) { _coach.Done(); _coach = null; }           // "Besle'ye dokun" adımı → sürükleme adımı
            var i = System.Array.IndexOf(TipSeq, tip);
            _coach = Coach.Show(Root, tip, T(Onboarding.Get(tip).CaptionKey, PetGen), TipGesture.Drag, () => UiScreen(from), PetScreen, 3,
                i >= 0 ? (i + 1) + "/" + TipSeq.Length : null);
        }

        /// <summary>Bırakılan nokta petin üstünde mi (ekranda petin çevresi ya da çarpışma kutusu)?</summary>
        private bool OverPet(Vector2 screen)
        {
            if (_world.Walker == null) return false;
            var cam = App.Stage.Camera;
            foreach (var h in Physics.RaycastAll(cam.ScreenPointToRay(screen), 200f)) if (h.collider.gameObject.name == "pet") return true;
            return Vector2.Distance(screen, PetScreen()) < Screen.height * 0.16f;
        }

        private void Care(CareAction a, ItemDef item)
        {
            CloseTray();
            var st = App.State;
            var local = App.LocalNow;
            var r = a == CareAction.Feed ? PetCare.Feed(st.Stats, st.Inventory, item, local) : PetCare.Wash(st.Stats, st.Inventory, item, local);
            if (r == CareResult.Ok)
            {
                TipDone(a == CareAction.Feed ? Onboarding.Feed : Onboarding.Wash);
                _world.Walker?.Jump();
                if (a == CareAction.Feed) CareFx.Food(Root, Ui.Icon(item.Id), PetScreen);   // 3 ısırıkta biter
                else CareFx.Bubbles(Root, PetScreen);                                      // sabun baloncukları
                App.Save();
                App.RecordActivity(a == CareAction.Feed ? "pet_fed" : "pet_washed");
            }
            _toast.Say(CareFeedback.Message(App.Loc, a, r, st.PetName));
            RefreshHud();
        }

        private void CloseTray()
        {
            if (_tray == null) return;
            if (_coach != null && (_coach.Id == Onboarding.Feed || _coach.Id == Onboarding.Wash)) { _coach.Done(); _coach = null; }
            Destroy(_tray.gameObject);
            _tray = null;
        }

        /// <summary>Malzeme bitti: pet dükkâna koşar ve dükkân açılır (kısa yol).</summary>
        private void RunToShop(string say)
        {
            _toast.Say(say);
            var shop = _views.FirstOrDefault(v => v.Region.Id == "region_shop");
            if (shop == null) return;
            var (dx, dz) = _terrain.Door(shop.Region);
            GoTo(dx, dz, () => EnterRegion(shop));
        }

        // Görev: oyun içi seviye görevleri (yıldız). Ebeveyn görevleri adadaki "Ev Görevleri" panosunda.
        private void GoTasks() { TipDone(Onboarding.Tasks); QuestPanel(); }

        // ------------------------------------------------------------------ joystick

        private void HandleStick(Vector2 screen)
        {
            var radius = Screen.height * 0.11f;
            var delta = screen - _press;
            if (!_moved && delta.magnitude > Screen.height * 0.025f)
            {
                _moved = true;
                CloseTray();
                _stickBase.gameObject.SetActive(true);
                var k = Root.rect.width / Mathf.Max(1f, Screen.width);
                _stickBase.anchoredPosition = new Vector2(_press.x * k, _press.y * k);
            }
            if (!_moved) return;
            TipDone(Onboarding.Walk);
            var dir = Vector2.ClampMagnitude(delta / radius, 1f);
            _stickKnob.anchoredPosition = dir * 70f;
            var w = Quaternion.Euler(0f, _camYaw, 0f) * new Vector3(dir.x, 0f, dir.y);
            _world.Walker.Steer(new Vector2(w.x, w.z));
        }

        private void EndStick()
        {
            if (_world.Walker != null) _world.Walker.Steer(Vector2.zero);
            _stickBase.gameObject.SetActive(false);
            _stickKnob.anchoredPosition = Vector2.zero;
        }
    }
}
