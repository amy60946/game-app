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
        private Text _coinText, _stoneText, _actionText;
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
        private RectTransform _trophy;

        private const float G = GoldKit.K;   // Altın Atölye taslağı (1280×720) → tuval birimi
        private Text _nextTip;
        private RectTransform _detail, _xpBar, _curRow;
        private CanvasGroup _detailG, _nextG;
        private readonly List<CanvasGroup> _hudLabels = new List<CanvasGroup>();
        private readonly List<RectTransform> _hudShrink = new List<RectTransform>();
        private RectTransform _homeBadge;
        private Text _homeNum;

        /// <summary>Bugün yapılmayı bekleyen ev görevi (ebeveynin verdiği, "Yaptım" denmemiş).</summary>
        private int HomeTasksOpen()
        {
            var local = App.LocalNow; var today = DemoParent.Day(local);
            return App.State.Tasks.ForDisplay(local).Count(t => t.Date == today && t.Status == Logic.Tasks.ChildTaskStatus.Assigned && !t.IsMissed(local));
        }

        private void BuildHud()
        {
            var hud = Ui.Fill(Root, "Hud");
            _hudGroup = hud.gameObject.AddComponent<CanvasGroup>();   // sinematik anlarda (H1) arayüz çekilir
            _hudLabels.Clear(); _hudShrink.Clear();
            // Altın Atölye + çerçevesiz 3B simgeler + yürürken gizlen (E + G, kullanıcı onayı 22 Ekim; işleniş 1 "kalın simge", 24 Ekim 2026).
            // Sol üst: yüz madalyonu, çevresinde 4 ihtiyaç yayı, köşede yıldız seviye; yanında kırmızı kurdele ad + kupa, altın XP çubuğu,
            // ihtiyaç değerleri. Madalyona dokununca menü (Defter, Ayarlar, Müzik, Sesli okuma).
            BuildProfile(hud);

            // üst orta: Güneş Taşı ve coin (altın kenarlı mavi hap, soldan taşan 3B simge; coin'de parıltı)
            _curRow = Ui.Rect(hud, "Currencies", new Vector2(0.5f, 1f), new Vector2(340f * G, 48f * G), new Vector2(0f, -(24f + 24f) * G));
            _stoneText = CurrencyPill(_curRow, "ui_sunstone", -91f * G);   // Güneş Taşı (yerleştirilebilir)
            _coinText = CurrencyPill(_curRow, "ui_coin", 91f * G);
            GoldKit.Sparkle(_coinText.transform.parent, new Vector2(0f, 1f), new Vector2(-10f * G, -2f * G), 16f * G, 0f);
            GoldKit.Sparkle(_coinText.transform.parent, new Vector2(0f, 0f), new Vector2(38f * G, 6f * G), 11f * G, 0.8f);
            RewardFlight.Register("coin", (RectTransform)_coinText.transform.parent);    // O1: kazanılan coin buraya uçar
            RewardFlight.Register("sunstone", (RectTransform)_stoneText.transform.parent);
            LongPressInfo.Add(_stoneText.transform.parent.gameObject, T("info.stones"));   // E4
            LongPressInfo.Add(_coinText.transform.parent.gameObject, T("info.coins"));

            // sağ üst: Harita (kuşbakışı / yürü) ve solunda Görev; çerçeve yok, simgenin kendisi düğme (kullanıcı, 24 Ekim 2026)
            // G (23 Ekim 2026): Ayarlar ve müzik avatar menüsünde; Ev Görevleri adadaki panodan ve Görev penceresinin sekmesinden açılır.
            MusicButton.SetVisible(false);
            var map = Shrinkable(hud, new Vector2(1f, 1f), new Vector2(-(22f + 50f) * G, -(8f + 50f) * G), 100f * G);
            var (mapBtn, _, mapLab) = GoldKit.Icon3D(map, "ui_map", 100f * G, new Vector2(0.5f, 0.5f), Vector2.zero, Theme.Hex("#7A4A12"), ToggleMode, T("map.overview"), GoldKit.Tone.Red, 0.9f);
            _modeText = mapLab;
            _mapBtn = (RectTransform)mapBtn.transform;
            Label(mapLab);
            LongPressInfo.Add(mapBtn.gameObject, T("info.map"));
            var tasksW = Shrinkable(hud, new Vector2(1f, 1f), new Vector2(-(22f + 100f + 22f + 42f) * G, -(8f + 46f) * G), 84f * G);
            var (tasks, _, tasksLab) = GoldKit.Icon3D(tasksW, "ui_star", 84f * G, new Vector2(0.5f, 0.5f), Vector2.zero, Theme.Hex("#C26A08"), GoTasks, T("hud.tasks"), GoldKit.Tone.Blue, 0.3f);
            _tasksBtn = (RectTransform)tasks.transform;
            Label(tasksLab);
            _questCount = GoldKit.Gem(tasks.transform);   // bugün açık oyun içi görev sayısı
            // ailenden görev varken kırmızı sayı yerine altın pano rozeti + ev görevi sayısı (Ev Görevleri C+D, 24 Ekim 2026)
            _homeBadge = Ui.Rect(tasks.transform, "HomeBadge", new Vector2(1f, 1f), new Vector2(76f * G * 0.82f, 40f * G * 0.82f), new Vector2(4f * G, -2f * G));
            GoldKit.RimCapsule(_homeBadge, Theme.Hex("#FFE27A"), Theme.Hex("#F5A81C"), 3f * G);
            Ui.IconImage(_homeBadge, "ui_board", new Vector2(0f, 0.5f), 32f * G * 0.82f, new Vector2(18f * G * 0.82f, 0f));
            _homeNum = Ui.Label(_homeBadge, "", Mathf.RoundToInt(21f * G * 0.82f), Theme.Hex("#5A3000"), new Vector2(1f, 0.5f), new Vector2(34f * G * 0.82f, 40f * G * 0.82f), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(-20f * G * 0.82f, 1f));
            _homeNum.raycastTarget = false;
            _homeBadge.gameObject.SetActive(false);
            LongPressInfo.Add(tasks.gameObject, T("info.tasks"));
            var next = App.Map.NextToUnlock(App.Level, App.State.VisitedRegions, App.Data.SunBook, App.State.SunStones);
            if (next != null)
            {
                // krem kurdele (taslak .e-tip): sıradaki yer; yürürken aşağı kayıp söner
                _nextTip = GoldKit.Ribbon(hud, T("map.next", next.Region.Name, next.UnlockLevel), GoldKit.Tone.Cream, 44f * G, Mathf.RoundToInt(20f * G), new Vector2(0.5f, 0f), new Vector2(0f, 46f));
                _nextG = _nextTip.transform.parent.gameObject.AddComponent<CanvasGroup>(); _nextG.blocksRaycasts = false;
            }

            // Besle/Yıka düğmeleri yok (G1 + G2, 23 Ekim 2026): bakım Okti'ye dokununca açılan baloncuklardan ve ihtiyaç baloncuğundan.
            // Tepsi bu katmanda açılır.
            _leftBar = Ui.Rect(hud, "Care", Vector2.zero, new Vector2(420f, 260f), new Vector2(196f, 172f));

            // sağ alt: bağlamsal eylem (çerçevesiz 3B simge + yeşil kurdele)
            // simgesi o anki eyleme göre değişir (balta, el, kazma, çekiç, zıpla, kapı, oyna); altında kısa yazı
            var (act, actIcon, actLab) = GoldKit.Icon3D(hud, "act_jump", 132f * G, new Vector2(1f, 0f), new Vector2(-(44f + 66f) * G, (44f + 66f) * G),
                Theme.Hex("#4E2E14"), () => _actionDo?.Invoke(), T("hud.jump"), GoldKit.Tone.Green, 0.2f);
            _action = (RectTransform)act.transform;
            _actionText = actLab;
            _actionIcon = actIcon;
            BuildBag(hud);    // Ç: sağdaki malzeme paneli yerine sol kenarda çanta
            BuildHutChip(hud);
            BuildNeed(hud);   // İ1 + İ4

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
            CollectSmartHide(hud);
        }

        // ------------------------------------------------------------------ Altın Atölye parçaları

        /// <summary>Sol üst profil (UI/GoldProfile; Evim de aynısını kullanır).</summary>
        private void BuildProfile(RectTransform hud)
        {
            _prof = GoldProfile.Build(hud, App.State.PetId, HudIcons, ToggleAvatarMenu);
            _levelBadge = _prof.Ring;
            for (var i = 0; i < 4; i++) { _gauges[i] = _prof.Arcs[i]; _gaugeGlow[i] = _prof.Glows[i]; }
            _detail = _prof.Detail; _detailG = _prof.DetailGroup; _xpBar = _prof.XpBar;
            _trophy = _prof.Trophy;
            RewardFlight.Register("xp", _xpBar);   // XP küreleri buraya uçar (kullanıcı, 24 Ekim 2026)
        }

        private GoldProfile _prof;

        private static Text CurrencyPill(RectTransform row, string icon, float x) => GoldKit.CurrencyPill(row, icon, new Vector2(0.5f, 0.5f), new Vector2(x, 0f));

        /// <summary>Yürürken küçülecek düğmenin taşıyıcısı (düğmenin kendi ölçeğini basma tepkisi yönetir).</summary>
        private RectTransform Shrinkable(RectTransform hud, Vector2 anchor, Vector2 offset, float size)
        {
            var w = Ui.Rect(hud, "Wrap", anchor, new Vector2(size, size), offset);
            _hudShrink.Add(w);
            return w;
        }

        // Kulübe çipi (taslak .x-chip): kulübe yapılana kadar sağ üstte küçük krem hap; yay dolar, "Kulübe 3/13". Dokununca Okti
        // şantiyeye yürür. Şantiyenin yanındaki gereksinim kartı (E3) açıkken gizlenir.
        private RectTransform _hutChip;
        private Image _hutRing;
        private Text _hutText;

        private void BuildHutChip(RectTransform hud)
        {
            if (_site == null || App.State.Gather.HutBuilt) return;
            _hutChip = Ui.Rect(hud, "HutChip", new Vector2(1f, 1f), new Vector2(200f * G, 48f * G));
            _hutChip.pivot = new Vector2(1f, 1f); _hutChip.anchoredPosition = new Vector2(-22f * G, -146f * G);
            GoldKit.RimCapsule(_hutChip, Theme.Hex("#FFF7E0"), Theme.Hex("#F4DEA8"), 3f * G);
            var ring = Ui.Rect(_hutChip, "Ring", new Vector2(0f, 0.5f), new Vector2(28f * G, 28f * G), new Vector2((8f + 14f) * G, 0f));
            var track = ring.gameObject.AddComponent<Image>(); track.sprite = GoldKit.Annulus; track.color = Theme.Hex("#E3CB92"); track.raycastTarget = false;
            var fr = Ui.Fill(ring, "Fill");
            _hutRing = fr.gameObject.AddComponent<Image>(); _hutRing.sprite = GoldKit.Annulus; _hutRing.color = Theme.Hex("#F2A81C"); _hutRing.raycastTarget = false;
            _hutRing.type = Image.Type.Filled; _hutRing.fillMethod = Image.FillMethod.Radial360; _hutRing.fillOrigin = (int)Image.Origin360.Top;
            Ui.IconImage(_hutChip, "tool_hammer", new Vector2(0f, 0.5f), 32f * G, new Vector2((8f + 28f + 8f + 16f) * G, 0f));
            _hutText = Ui.Label(_hutChip, "", Mathf.RoundToInt(18f * G), Theme.Hex("#6B3F0E"), new Vector2(1f, 0.5f), new Vector2(110f * G, 44f * G), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(-(16f + 55f) * G, 0f));
            _hutText.raycastTarget = false;
            var hit = _hutChip.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            var b = _hutChip.gameObject.AddComponent<Button>(); b.targetGraphic = hit; b.transition = Selectable.Transition.None;
            b.onClick.AddListener(() => { Audio.Sfx.Play(Audio.SfxKind.Tap); if (_world.Walker != null) _world.Walker.WalkTo(_sitePos.x, _sitePos.z); });
            _hutChip.gameObject.AddComponent<PressBounce>();
            LongPressInfo.Add(_hutChip.gameObject, T("gather.hut_short"));
            RefreshTracker();
        }

        /// <summary>Düğme kurdelesi yürürken söner.</summary>
        private void Label(Text t)
        {
            if (t == null) return;
            var g = t.transform.parent.gameObject.AddComponent<CanvasGroup>(); g.blocksRaycasts = false;
            _hudLabels.Add(g);
        }

        // ------------------------------------------------------------------ G akıllı gizlenme (onaylı, 22–23 Ekim 2026)
        // Yürürken (taslak "Yürürken"): ad/XP ayrıntısı, kurdeleler ve sıradaki yer söner; Görev, Harita, Çanta küçülür, paralar biraz küçülür.
        // Madalyon, yaylar, eylem tuşu ve joystick hep kalır. Durunca geri gelir.
        private float _hideT, _moveFor, _stillFor;
        private Vector2 _lastPetPos;

        private void CollectSmartHide(RectTransform hud) { }

        private void UpdateSmartHide(float dt)
        {
            if (_world.Walker == null) return;
            var p = _world.Walker.Position;
            var speed = (p - _lastPetPos).magnitude / Mathf.Max(0.0001f, dt);
            _lastPetPos = p;
            var moving = !_overview && !_cine && speed > 0.6f;
            if (moving) { _moveFor += dt; _stillFor = 0f; } else { _stillFor += dt; _moveFor = 0f; }
            var hide = _moveFor > 0.35f || (_hideT > 0f && _stillFor < 0.6f);   // kısa duraklamada geri zıplamasın
            _hideT = Mathf.MoveTowards(_hideT, hide ? 1f : 0f, dt / (hide ? 0.3f : 0.4f));
            var e = _hideT * _hideT * (3f - 2f * _hideT);
            if (_detailG != null) { _detailG.alpha = 1f - e; _detail.localScale = new Vector3(1f - 0.1f * e, 1f - 0.1f * e, 1f); }
            foreach (var g in _hudLabels) if (g != null) g.alpha = 1f - e;
            foreach (var w in _hudShrink) if (w != null) { var k = 1f - 0.22f * e; w.localScale = new Vector3(k, k, 1f); }
            if (_curRow != null) { var k = 1f - 0.14f * e; _curRow.localScale = new Vector3(k, k, 1f); }
            if (_nextG != null) { _nextG.alpha = 1f - e; ((RectTransform)_nextG.transform).anchoredPosition = new Vector2(0f, 46f - 18f * G * e); }
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

        /// <summary>Günlük sandık (S2): adada petin önünde 3B sandık açılır, ödül pete akar.</summary>
        protected override void PlayChest(Sprite prize, System.Action done)
        {
            var w = _world != null ? _world.Walker : null;
            if (w == null || _overview) { base.PlayChest(prize, done); return; }
            ChestFx.Play(w.transform, PetHeight, prize, () =>
            {
                if (this == null) return;
                if (_world != null && _world.Walker != null) _world.Walker.Cheer();
                done?.Invoke();
            });
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
            var f = Ui.Rect(_levelBadge.parent, "XpGain", new Vector2(0f, 1f), new Vector2(240f, 90f), new Vector2((148f + 250f + 70f) * G, -(12f + 58f) * G));
            Ui.IconImage(f, "ui_star", new Vector2(0f, 0.5f), 80f, new Vector2(40f, 0f));
            Candy.Caption(f, T("xp.star", n), 56, new Vector2(0.5f, 0.5f), new Vector2(160f, 90f), new Vector2(40f, 0f));
            f.gameObject.AddComponent<FloatUp>();
            // XP küreleri (kullanıcı, 24 Ekim 2026; Hay Day / Township tarzı): kazanıldığı yerden saçılıp XP çubuğuna uçar,
            // çubuk geldikçe dolar. Kaynak yoksa Okti'nin üstünden çıkar.
            var from = _xpFrom; _xpFrom = null;
            Vector2 sp;
            var w = _world != null ? _world.Walker : null;
            if (from.HasValue) sp = App.Stage.Camera.WorldToScreenPoint(from.Value);
            else if (w != null && !_overview) sp = App.Stage.Camera.WorldToScreenPoint(w.transform.position + Vector3.up * PetHeight * 0.9f);
            else sp = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
            RewardFlight.Fly(App.Overlay.transform, "xp", "ui_star", n, sp);
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
                _prof.SetNeed(i, st.Stats[HudKinds[i]]);   // besleyince/yıkayınca yay zıplar
            }
            // uçuştaki ödül sayaçtan düşülür: parçalar geldikçe sayı tek tek artar (O1)
            var coins = st.Wallet.Available - RewardFlight.Pending("coin"); var stones = Logic.Island.SunStoneBook.Available(st.SunStones) - RewardFlight.Pending("sunstone");
            if (_lastCoins >= 0 && coins != _lastCoins) Bump.Play(_coinText.transform.parent);
            if (_lastStones >= 0 && stones != _lastStones) Bump.Play(_stoneText.transform.parent, 0.3f);
            _lastCoins = coins; _lastStones = stones;
            _prof.SetName(st.PetName, st.Badges.Count);
            _coinText.text = coins.ToString();
            _stoneText.text = stones.ToString();
            // XP: uçuştaki küreler henüz sayılmaz (geldikçe çubuk dolar)
            _prof.SetXp(App.Levels, Mathf.Max(0, st.Xp.TotalXp - RewardFlight.Pending("xp")), App.Level, T("hud.xp_max"));
            RefreshBag();
            if ((_questT -= Time.deltaTime) <= 0f)
            {
                _questT = 1f;
                var home = HomeTasksOpen();
                _homeBadge.gameObject.SetActive(home > 0);
                _homeNum.text = home.ToString();
                if (home > 0) _questCount.transform.parent.gameObject.SetActive(false);
                else SetCount(_questCount, OpenQuests());
                _boardCount = home;
            }
        }

        private static void SetCount(Text t, int n)
        {
            t.text = n.ToString();
            t.transform.parent.gameObject.SetActive(n > 0);
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
            UpdateSmartHide(Time.deltaTime);
            UpdatePathGuide(Time.deltaTime);
            UpdateNeed(Time.deltaTime);
            UpdateHomeBtn(Time.deltaTime);
            _action.gameObject.SetActive(walking);
            if (!walking) { CloseTray(); return; }
            UpdateAction();
            _islandTime += Time.deltaTime;
            UpdateTips();
        }

        // ------------------------------------------------------------------ tanıtım ipuçları (docs/ONBOARDING.md)

        private string PetGen => Logic.Core.TurkishSuffix.Genitive(App.State.PetName);
        private string PetDat => Logic.Core.TurkishSuffix.Dative(App.State.PetName);

        // Tanıtım sırası (kullanıcı isteği, 15 Ekim 2026): hepsi arka arkaya değil, biri tamamlanınca kısa ara, sonra sıradaki;
        // panelde "adım/toplam" görünür. Bağlamsal olanlar (kapı, oyun yeri, parıltı) uygun anda araya girer.
        private static readonly string[] TipSeq =
            { Onboarding.Walk, Onboarding.Look, Onboarding.Jump, Onboarding.Wardrobe, Onboarding.Feed, Onboarding.Tasks, Onboarding.Overview };
        private float _tipGap = 1.5f;

        private static Sprite[] CareProps => new[] { Ui.Icon("food_apple"), Ui.Icon("clean_soap"), Ui.Icon("hoodie_soft") };

        private void Tip(string id, TipGesture g, System.Func<Vector2> from, System.Func<Vector2> to = null, string arg = null, Sprite prop = null, string key = null, Sprite[] props = null)
        {
            if (_coach != null || !Onboarding.Pending(App.State, id)) return;
            if (!FirstDay.AllowsTip(FirstDayNow, id)) return;   // ilk gün: yalnız ilk gün ipuçları (Ö5)
            var i = System.Array.IndexOf(TipSeq, id);
            var step = i >= 0 ? (i + 1) + "/" + TipSeq.Length : null;
            _coach = Coach.Show(Root, id, T(key ?? Onboarding.Get(id).CaptionKey, arg ?? App.State.PetName), g, from, to, props != null ? 6 : 3, step, prop, null, null, props);
            // D3 ışık halkası: yeni düğme ilk kez gösterilirken (Görev, Harita) ekran kısılır, düğme aydınlık kalır
            if (id == Onboarding.Tasks || id == Onboarding.Overview) Spotlight.Show((RectTransform)_coach.transform, from, 120f);
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

        private static bool _rewardsToldThisSession;

        private void UpdateTips()
        {
            if (_xpTipT > 0f) { _xpTipT -= Time.deltaTime; if (_xpTipT <= 0f) TipDone(Onboarding.Xp); }
            var guide = Guide.Current(App.State, App.Level);
            if (_coach != null && _coach.Id.StartsWith("guide_") && (guide == null || _coach.Id != "guide_" + guide.Id)) { _coach.Done(); _coach = null; _tipGap = 1f; }   // adım bitti
            if (_coach != null || _tray != null) return;
            if (StoryPlayer.Playing || _cine) { _tipGap = 0f; return; }   // hikâye konuşması sürerken yeni ipucu açılmaz (üst üste binmesin)
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
            // rehberli zincir: sıradaki adım, işaret eli hedefini gösterir; ilk gün pano/taş ipuçlarının yerine geçer
            if (basicsDone && guide != null && !_overview) { GuideTip(guide); return; }
            // Gerçek ödüller yeni açıldı (Sv4, GB17-13): oturumda bir kez el dükkânı gösterir; dükkân sekmesi tanıtımla açılır
            if (basicsDone && guide == null && !_overview && !_rewardsToldThisSession && App.Levels.IsUnlocked(ShopScreen.RewardsUnlock, App.Level)
                && !App.State.SeenTips.Contains(ShopScreen.RewardsIntroFlag))
            {
                _rewardsToldThisSession = true;
                _coach = Coach.Show(Root, "rewards_new", T("rewards.new_map"), TipGesture.Tap, () => RegionScreen("region_shop"), null, 3, null, null, T("rewards.new_map"));
                return;
            }
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
                case Onboarding.Wardrobe:  // Okti'ye dokun → menü (kullanıcı, 24 Ekim 2026): el dokunur, Besle/Yıka/Giydir baloncukları açılır
                    Tip(next, TipGesture.Tap, PetScreen, null, PetDat, null, "tip.pet_menu", CareProps);
                    break;
                case Onboarding.Feed:      // önce Okti'ye dokun (G2), elmaya dokun; tepsi açılınca sürükleme ipucu gelir
                    Tip(next, TipGesture.Tap, PetScreen, null, PetDat, null, "tip.feed_open", new[] { Ui.Icon("food_apple") });
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
            // "Okti'ye dokun" (G2), "Okti'nin üstüne dokun" (giydir)
            var arg = g.Id == "feed" || g.Id == "wash" ? PetDat : g.Id == "wear" ? PetGen : App.State.PetName;
            if (g.Id == "mavi") { _coach = Coach.Show(Root, "guide_" + g.Id, T(g.TextKey), TipGesture.Tap, MaviSky, null, 1, step, null, T(g.TextKey)); _tipGap = -4f; return; }
            var say = T(g.TextKey, arg);
            _coach = Coach.Show(Root, "guide_" + g.Id, say + "  " + T("guide.reward", g.Xp), TipGesture.Tap, GuideTarget(g), null, 3, step, null, say);
            _tipGap = -4f;   // panel kapanınca birkaç saniye nefes
        }

        /// <summary>Mavi'nin geleceği gökyüzü (ekranın sağ üstü): el oraya bir kez dokunur.</summary>
        private Vector2 MaviSky() => _mavi != null ? (Vector2)App.Stage.Camera.WorldToScreenPoint(_mavi.transform.position + Vector3.up)
            : new Vector2(Screen.width * 0.72f, Screen.height * 0.72f);

        private System.Func<Vector2> GuideTarget(GuideStep g)
        {
            switch (g.Id)
            {
                case "feed": case "wash": return PetScreen;   // Okti'ye dokun → Besle / Yıka baloncukları (G2)
                case "home": case "tidy": case "play": return () => RegionScreen("region_home");
                case "wear": return PetScreen;
                case "board": return () => RegionScreen("region_task_board");
                case "stone": return () => RegionScreen(App.Data.SunBook.Next(App.State.SunStones)?.Region ?? "region_task_board");
                case "kiskac": case "deliver": return KiskacScreen;
                case "coconut": return () => GuideWorld(g) is Vector2 c ? (Vector2)App.Stage.Camera.WorldToScreenPoint(_world.World(c.x, c.y) + Vector3.up * 0.8f) : RegionScreen("region_coconut_grove");
                case "gather": return NearestGatherScreen;
                case "hut": return () => App.Stage.Camera.WorldToScreenPoint(_world.World(_sitePos.x, _sitePos.z) + Vector3.up * 1.5f);
                case "fire": return FireGuideScreen;
                case "shop": return () => RegionScreen("region_shop");
                default: return PetScreen;
            }
        }

        private Vector2 KiskacScreen() =>
            _kiskac != null ? (Vector2)App.Stage.Camera.WorldToScreenPoint(_kiskac.transform.position + Vector3.up * 1.6f) : RegionScreen("region_shop");

        /// <summary>
        /// Rehberin toplama hedefi (GB17): kulübe için hâlâ eksik malzemenin en yakın noktası; ceviz adımında en yakın yerdeki ceviz
        /// (60 m'den uzaksa bahçe). Toplanmış (beklemedeki) noktalar sayılmaz.
        /// </summary>
        private GatherNode NearestNode(System.Func<GatherNode, bool> want, float maxDist = float.MaxValue)
        {
            var p = _world.Walker.Position; GatherNode best = null; var bd = maxDist;
            foreach (var n in _gNodes)
            {
                if (!want(n) || !_gSpots.TryGetValue(n.Index, out var sp) || !sp.gameObject.activeSelf) continue;
                var d = Vector2.Distance(p, new Vector2(n.X, n.Z));
                if (d < bd) { bd = d; best = n; }
            }
            return best;
        }

        private bool NeededForHut(GatherNode n) =>
            n.Kind != GatherKind.Coconut && Gathering.Lacking(App.State.Gather, Gathering.Rule(n.Kind).Material);

        // ------------------------------------------------------------------ N1 + N3 yol gösterme (23 Ekim 2026, onaylı)
        private World.PathGuide _path;
        private float _idleFor;
        private string _pathStep;

        /// <summary>Rehber adımının adadaki hedefi (yürünecek yer); pete dokunulan adımlarda (besle, yıka, giydir) yok.</summary>
        private Vector2? GuideWorld(GuideStep g)
        {
            switch (g.Id)
            {
                case "home": case "tidy": case "play": return DoorOf("region_home");
                case "board": return DoorOf("region_task_board");
                case "stone": return DoorOf(App.Data.SunBook.Next(App.State.SunStones)?.Region ?? "region_task_board");
                case "gather":
                {
                    var best = NearestNode(NeededForHut) ?? NearestNode(n => n.Kind != GatherKind.Coconut);
                    return best != null ? new Vector2(best.X, best.Z) : (Vector2?)null;
                }
                case "coconut":
                {
                    var nut = NearestNode(n => n.Kind == GatherKind.Coconut, 60f);
                    return nut != null ? new Vector2(nut.X, nut.Z) : DoorOf("region_coconut_grove");
                }
                case "kiskac": case "deliver": return _kiskac != null ? KiskacPos : DoorOf("region_shop");
                case "hut": return new Vector2(_sitePos.x, _sitePos.z);
                case "fire": return FireGuideWorld();
                case "shop": return DoorOf("region_shop");
                default: return null;
            }
        }

        private Vector2? DoorOf(string regionId)
        {
            var r = _terrain.Regions.FirstOrDefault(x => x.Id == regionId);
            if (r == null) return null;
            var (x, z) = _terrain.Door(r);
            return new Vector2(x, z);
        }

        /// <summary>Rehberli adımda çocuk 8 sn hareketsiz kalınca oklar açılır; yürürken kalır, hedefe varınca ya da adım değişince söner.</summary>
        private void UpdatePathGuide(float dt)
        {
            if (_world.Walker == null) return;
            if (_path == null) _path = World.PathGuide.Create(_world);
            var touching = Input.touchCount > 0 || Input.GetMouseButton(0);
            var moving = _world.Walker.Moving || _moveFor > 0f;
            _idleFor = touching || moving ? 0f : _idleFor + dt;
            var basicsDone = !Onboarding.Pending(App.State, Onboarding.Walk) && !Onboarding.Pending(App.State, Onboarding.Look);
            var guide = basicsDone && !_overview && !_cine ? Guide.Current(App.State, App.Level) : null;
            var target = guide != null ? GuideWorld(guide) : null;
            var stepId = guide?.Id;
            if (stepId != _pathStep) { _pathStep = stepId; _path.Hide(); }
            var pos = _world.Walker.Position;
            var arrived = target != null && Vector2.Distance(pos, target.Value) < 4f;
            if (target == null) _path.Hide();
            else if (arrived) _path.Hide();                                    // vardı
            else if (_path.Active) _path.Show(target.Value);                   // hedef kayabilir (en yakın kütük)
            else if (_idleFor > 8f) _path.Show(target.Value);
            _path.Tick(pos, App.Stage.Camera, dt);
            UpdateMaviGuide(_path.Active && target != null, target ?? Vector2.zero, arrived);   // N2: Mavi önden uçar
        }

        /// <summary>Kulübe için eksik malzemenin en yakın noktası (ekran); yoksa pet.</summary>
        private Vector2 NearestGatherScreen()
        {
            var best = NearestNode(NeededForHut) ?? NearestNode(n => n.Kind != GatherKind.Coconut);
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
            if (key == "hud.jump" && CampfireAction(p, out var fact)) { key = "hud.stoke"; icon = "mat_wood"; act = fact; }   // kamp ateşini harla (GB18)
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
                _actionKey = key; _actionText.text = T(key); GoldKit.FitRibbon(_actionText);
                GoldKit.SetIcon(_actionIcon, icon);
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
                if (v.Unlocked || v.Spot == null || v.StonesLeft <= 0) continue;   // onarılmış ama oyunu beklemede olan yer
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
                // H1: sis kalkış sahnesi (≈4 sn), sonra bölge açılır (ada yeniden kurulur)
                var view = _views.FirstOrDefault(x => x.Spot != null && x.Spot.Id == spot.Id);
                StartCoroutine(FogLift(view, () =>
                {
                    Toast.Post(App.Overlay.transform, Th, string.IsNullOrEmpty(spot.Say) ? T("stones.all_done") : spot.Say);
                    App.Route();
                }));
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
            string firstId = null;
            for (var i = 0; i < items.Count; i++)
            {
                var it = items[i];
                // beyaz daire yok (24 Ekim 2026): çerçevesiz simge + gösterge çerçevesi + elmas sayı
                var b = Ui.Rect(_tray, "Item " + it.Id, new Vector2(0f, 0.5f), new Vector2(130f, 130f), new Vector2(80f + i * 150f, 0f));
                var hit = b.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
                var pic = Ui.Rect(b, "Pic", new Vector2(0.5f, 0.5f), new Vector2(118f, 118f)).gameObject.AddComponent<Image>();
                pic.sprite = Ui.Icon(it.Id); pic.preserveAspect = true; pic.raycastTarget = false;
                GoldKit.Frame3D(pic);
                pic.gameObject.AddComponent<Hover3D>().Delay = i * 0.4f;
                GoldKit.Gem(b, 44f).text = App.State.Inventory.CountOf(it.Id).ToString();
                b.gameObject.AddComponent<PressBounce>();
                var d = b.gameObject.AddComponent<DragItem>();
                d.IconId = it.Id; d.Layer = Root;
                d.Dropped = pos => { if (!OverPet(pos)) return false; Care(action, it); return true; };
                d.Tapped = () => { _toast.Say(T("tip." + tip, PetGen)); TipDone(null); ShowDragTip(tip, (RectTransform)b.transform, true, it.Id); };
                LongPressInfo.Add(b.gameObject, it.Name);
                if (first == null) { first = (RectTransform)b.transform; firstId = it.Id; }
            }
            ShowDragTip(tip, first, false, firstId);
        }

        private void ShowDragTip(string tip, RectTransform from, bool force, string itemId)
        {
            if (from == null || (!force && !Onboarding.Pending(App.State, tip))) return;
            if (_coach != null) { _coach.Done(); _coach = null; }           // "Besle'ye dokun" adımı → sürükleme adımı
            var i = System.Array.IndexOf(TipSeq, tip);
            // el eşyayı (elma, sabun) tepsiden alıp Okti'nin üstüne götürür, bırakır; yapılana kadar gidip gelir (kullanıcı, 24 Ekim 2026)
            var icon = itemId != null ? Ui.Icon(itemId) : null;
            _coach = Coach.Show(Root, tip, T(Onboarding.Get(tip).CaptionKey, PetGen), TipGesture.Drag, () => UiScreen(from), PetScreen, 99,
                i >= 0 ? (i + 1) + "/" + TipSeq.Length : null, null, null, icon);
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
                var gi = a == CareAction.Feed ? 0 : 1;                                     // gösterge yayına küçük uçuş (GB17-2)
                GoldProfile.FlyCare(App.Overlay.transform, gi, HudIcons[gi], PetScreen());
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
