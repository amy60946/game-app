using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Island;
using Pofi.Logic.Pet;
using Pofi.Logic.Core;
using Pofi.UI;
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
        private RectTransform _feedBtn;
        private float _questT;
        private Image _xpFill;

        private void BuildHud()
        {
            var hud = Ui.Fill(Root, "Hud");
            // sol üst
            // pet kartı: madalyon + isim plakası + seviye yıldızı + XP kapsülü (Candy.PetPlate)
            var pet = App.Data.Pet(App.State.PetId);
            _levelBadge = Candy.PetPlate(hud, App.State.PetId, Theme.Hex(pet.MainColor), new Vector2(24f, -16f), out _levelText, out _levelNum, out _xpFill);
            Color[] cols = { new Color(1f, 0.62f, 0.26f), new Color(0.24f, 0.79f, 1f), new Color(1f, 0.44f, 0.68f), new Color(0.48f, 0.84f, 0.42f) };
            for (var i = 0; i < 4; i++)
                _gauges[i] = Candy.Gauge(hud, cols[i], HudIcons[i], 128f, new Vector2(0f, 1f), new Vector2(30f + 64f + i * 144f, -262f));

            // sağ üst
            _coinText = Candy.CoinPlate(hud, new Vector2(-30f, -22f));
            _stoneText = Candy.ResourcePlate(hud, "ui_sunstone", new Vector2(-340f, -22f), 240f);   // Güneş Taşı (yerleştirilebilir)
            var map = Candy.Pill(hud, Candy.Blue, T("map.overview"), new Vector2(1f, 1f), new Vector2(300f, 116f), new Vector2(-180f, -206f), ToggleMode, null, 48);
            _modeText = map.transform.Find("Label").GetComponent<Text>();
            _mapBtn = (RectTransform)map.transform;
            var tasks = Candy.Round(hud, Candy.Orange, "ui_star", 132f, new Vector2(1f, 1f), new Vector2(-430f, -206f), GoTasks, T("hud.tasks"));
            _tasksBtn = (RectTransform)tasks.transform;
            _questCount = Candy.Count(tasks.transform);   // bugün açık oyun içi görev sayısı
            var next = App.Map.NextToUnlock(App.Level, App.State.VisitedRegions, App.Data.SunBook, App.State.SunStones);
            if (next != null)
                Candy.Caption(hud, T("map.next", next.Region.Name, next.UnlockLevel), 32, new Vector2(0.5f, 0f), new Vector2(900f, 56f), new Vector2(0f, 46f));

            // sol kenar: Besle, Yıka
            _leftBar = Ui.Rect(hud, "Care", new Vector2(0f, 0.5f), new Vector2(190f, 430f), new Vector2(130f, -70f));
            var feed = Candy.Round(_leftBar, Candy.Orange, "food_apple", 160f, new Vector2(0.5f, 0.78f), Vector2.zero, OnFeed, T("hud.feed"));
            _feedBtn = (RectTransform)feed.transform;
            _feedCount = Candy.Count(feed.transform);
            var wash = Candy.Round(_leftBar, Candy.Blue, "clean_soap", 160f, new Vector2(0.5f, 0.2f), Vector2.zero, OnWash, T("hud.wash"));
            _washCount = Candy.Count(wash.transform);

            // sağ alt: bağlamsal eylem
            // simgesi o anki eyleme göre değişir (balta, el, kazma, çekiç, zıpla, kapı, oyna); altında kısa yazı
            var act = Candy.Round(hud, Candy.White, "act_jump", 230f, new Vector2(1f, 0f), new Vector2(-190f, 230f), () => _actionDo?.Invoke(), T("hud.jump"));
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
            RefreshHud();
        }

        private void HudDestroy()
        {
            if (App != null) App.XpGained -= OnXp;
        }

        /// <summary>XP kazanınca rozetin yanında "+N ★" süzülür; ilk seferde XP ipucu.</summary>
        private void OnXp(int n)
        {
            if (this == null || _levelBadge == null) return;
            var f = Ui.Rect(_levelBadge.parent, "XpGain", new Vector2(0f, 1f), new Vector2(240f, 90f), new Vector2(620f, -70f));
            Ui.IconImage(f, "ui_star", new Vector2(0f, 0.5f), 80f, new Vector2(40f, 0f));
            Candy.Caption(f, T("xp.star", n), 56, new Vector2(0.5f, 0.5f), new Vector2(160f, 90f), new Vector2(40f, 0f));
            f.gameObject.AddComponent<FloatUp>();
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
            for (var i = 0; i < 4; i++) _gauges[i].fillAmount = st.Stats[HudKinds[i]] / 100f;
            _levelText.text = st.PetName;
            _levelNum.text = App.Level.ToString();
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
            // ilk gün (Ö5): yürü → besle → Ev Görevleri panosu (görev işaretle / taşı yerleştir orada)
            var day = FirstDayNow;
            if (day == FirstDayStep.Board) { Tip(Onboarding.Board, TipGesture.Tap, () => RegionScreen("region_task_board")); return; }
            if (day == FirstDayStep.Mark) { Tip(Onboarding.Mark, TipGesture.Tap, () => RegionScreen("region_task_board"), null, null, null, "tip.board"); return; }
            if (day == FirstDayStep.Stone) { Tip(Onboarding.Stone, TipGesture.Tap, () => RegionScreen("region_task_board")); return; }
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
                if (Vector2.Distance(sp, p) < 2.6f)
                {
                    var go = kv.Value.gameObject;
                    key = "hud.collect"; icon = "tool_hand"; act = () => Collect(go, go.name);
                    break;
                }
            }
            if (key == "hud.jump")
            {
                // kapı önünde → Gir / Oyna
                RegionView best = null; var bd = 3.4f;
                foreach (var v in _views)
                {
                    if (!v.Unlocked) continue;
                    var (dx, dz) = _terrain.Door(v.Region);
                    var d = Vector2.Distance(p, new Vector2(dx, dz));
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
