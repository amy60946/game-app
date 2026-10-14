using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Island;
using Pofi.Logic.Pet;
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
        private Text _levelText, _coinText, _feedCount, _washCount, _actionText;
        private RectTransform _action, _stickBase, _stickKnob, _tray, _leftBar;
        private System.Action _actionDo;
        private string _actionKey;
        private float _hudTick, _statTick;
        private readonly Dictionary<int, Transform> _sparkleObjs = new Dictionary<int, Transform>();

        private void BuildHud()
        {
            var hud = Ui.Fill(Root, "Hud");
            // sol üst
            _levelText = Candy.Badge(hud, "ui_star", "", new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(30f, -24f), 84f, 440f);
            Color[] cols = { new Color(1f, 0.62f, 0.26f), new Color(0.24f, 0.79f, 1f), new Color(1f, 0.44f, 0.68f), new Color(0.48f, 0.84f, 0.42f) };
            for (var i = 0; i < 4; i++)
                _gauges[i] = Candy.Gauge(hud, cols[i], HudIcons[i], 112f, new Vector2(0f, 1f), new Vector2(30f + 56f + i * 128f, -176f));

            // sağ üst
            _coinText = Candy.Badge(hud, "ui_coin", "", new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-30f, -24f), 84f, 250f);
            var map = Candy.Pill(hud, Candy.Blue, T("map.overview"), new Vector2(1f, 1f), new Vector2(250f, 96f), new Vector2(-155f, -176f), ToggleMode, null, 40);
            _modeText = map.transform.Find("Label").GetComponent<Text>();
            var tasks = Candy.Round(hud, Candy.Orange, "hand_flag", 104f, new Vector2(1f, 1f), new Vector2(-370f, -176f), GoTasks, T("hud.tasks"));
            var count = Candy.Count(tasks.transform);
            count.transform.parent.gameObject.AddComponent<TaskBadgeView>().Init(App, count);
            var next = App.Map.NextToUnlock(App.Level, App.State.VisitedRegions);
            if (next != null)
                Candy.Caption(hud, T("map.next", next.Region.Name, next.UnlockLevel), 32, new Vector2(0.5f, 0f), new Vector2(900f, 56f), new Vector2(0f, 46f));

            // sol kenar: Besle, Yıka
            _leftBar = Ui.Rect(hud, "Care", new Vector2(0f, 0.5f), new Vector2(160f, 360f), new Vector2(110f, -40f));
            var feed = Candy.Round(_leftBar, Candy.Orange, "food_apple", 132f, new Vector2(0.5f, 0.78f), Vector2.zero, OnFeed, T("hud.feed"));
            _feedCount = Candy.Count(feed.transform);
            var wash = Candy.Round(_leftBar, Candy.Blue, "clean_soap", 132f, new Vector2(0.5f, 0.2f), Vector2.zero, OnWash, T("hud.wash"));
            _washCount = Candy.Count(wash.transform);

            // sağ alt: bağlamsal eylem
            var act = Candy.Pill(hud, Candy.Green, T("hud.jump"), new Vector2(1f, 0f), new Vector2(300f, 150f), new Vector2(-200f, 150f), () => _actionDo?.Invoke(), null, 54);
            _action = (RectTransform)act.transform;
            _actionText = act.transform.Find("Label").GetComponent<Text>();

            // sol alt: yüzen joystick (parmak değince belirir)
            _stickBase = Ui.Rect(hud, "Stick", Vector2.zero, new Vector2(250f, 250f));
            var sb = _stickBase.gameObject.AddComponent<Image>(); sb.sprite = Ui.Rounded; sb.type = Image.Type.Sliced; sb.pixelsPerUnitMultiplier = 0.48f; sb.color = new Color(1f, 1f, 1f, 0.25f); sb.raycastTarget = false;   // tam daire
            var so = _stickBase.gameObject.AddComponent<Outline>(); so.effectColor = new Color(1f, 1f, 1f, 0.7f); so.effectDistance = new Vector2(4f, -4f);
            _stickKnob = Ui.Rect(_stickBase, "Knob", new Vector2(0.5f, 0.5f), new Vector2(120f, 120f));
            var kb = _stickKnob.gameObject.AddComponent<Image>(); kb.sprite = Ui.Rounded; kb.type = Image.Type.Sliced; kb.color = new Color(1f, 1f, 1f, 0.9f); kb.raycastTarget = false;
            _stickKnob.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
            _stickBase.gameObject.SetActive(false);

            RefreshHud();
        }

        private void RefreshHud()
        {
            var st = App.State;
            for (var i = 0; i < 4; i++) _gauges[i].fillAmount = st.Stats[HudKinds[i]] / 100f;
            _levelText.text = $"{st.PetName} · {T("home.level", App.Level)}";
            _coinText.text = st.Wallet.Available.ToString();
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
        }

        // ------------------------------------------------------------------ bağlamsal eylem

        private void UpdateAction()
        {
            var p = _world.Walker.Position;
            string key = "hud.jump";
            System.Action act = () => _world.Walker.Jump();

            // yakında parıltı → Topla
            foreach (var kv in _sparkleObjs)
            {
                if (kv.Value == null) continue;
                var sp = _world.Local(kv.Value.position);
                if (Vector2.Distance(sp, p) < 2.6f)
                {
                    var go = kv.Value.gameObject;
                    key = "hud.collect"; act = () => Collect(go, go.name);
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
                    act = () => EnterRegion(v);
                }
            }
            _actionDo = act;
            if (_actionKey != key) { _actionKey = key; _actionText.text = T(key); }
        }

        /// <summary>Mini oyun ya da masa oyunu bölgesi mi (üstünde "Oyna!" çağrısı gösterilir)?</summary>
        private static bool IsPlayPlace(RegionDef r)
        {
            var kind = IslandMap.KindOf(r.Target, out _);
            return kind == RegionTargetKind.MiniGame || kind == RegionTargetKind.Cards;
        }

        // ------------------------------------------------------------------ bakım

        private void OnFeed()
        {
            if (_tray != null) { CloseTray(); return; }
            var foods = App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .Where(it => it != null && it.Category == ItemCategory.Food).ToList();
            if (foods.Count == 0) { RunToShop(T("hud.no_food")); return; }
            _tray = Ui.Rect(_leftBar.parent, "Tray", new Vector2(0f, 0.5f), new Vector2(foods.Count * 124f + 30f, 150f), new Vector2(0f, 60f));
            _tray.pivot = new Vector2(0f, 0.5f);
            _tray.anchoredPosition = new Vector2(210f, 40f);
            for (var i = 0; i < foods.Count; i++)
            {
                var it = foods[i];
                var b = Candy.Round(_tray, Candy.White, it.Id, 108f, new Vector2(0f, 0.5f), new Vector2(70f + i * 124f, 0f), () => Care(CareAction.Feed, it));
                Candy.Count(b.transform).text = App.State.Inventory.CountOf(it.Id).ToString();
            }
        }

        private void OnWash()
        {
            CloseTray();
            var soap = App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .FirstOrDefault(it => it != null && it.Category == ItemCategory.Cleaning);
            if (soap == null) { RunToShop(T("hud.no_soap")); return; }
            Care(CareAction.Wash, soap);
        }

        private void Care(CareAction a, ItemDef item)
        {
            CloseTray();
            var st = App.State;
            var local = App.LocalNow;
            var r = a == CareAction.Feed ? PetCare.Feed(st.Stats, st.Inventory, item, local) : PetCare.Wash(st.Stats, st.Inventory, item, local);
            if (r == CareResult.Ok)
            {
                _world.Walker?.Jump();
                App.Save();
                App.RecordActivity(a == CareAction.Feed ? "pet_fed" : "pet_washed");
            }
            _toast.Say(CareFeedback.Message(App.Loc, a, r, st.PetName));
            RefreshHud();
        }

        private void CloseTray()
        {
            if (_tray == null) return;
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

        private void GoTasks() => App.Open(AppPage.Tasks);   // görev ekranı doğrudan (yürümeye gerek yok)

        // ------------------------------------------------------------------ joystick

        private void HandleStick(Vector3 screen)
        {
            var radius = Screen.height * 0.11f;
            var delta = (Vector2)(screen - _press);
            if (!_moved && delta.magnitude > Screen.height * 0.025f)
            {
                _moved = true;
                CloseTray();
                _stickBase.gameObject.SetActive(true);
                var k = Root.rect.width / Mathf.Max(1f, Screen.width);
                _stickBase.anchoredPosition = new Vector2(_press.x * k, _press.y * k);
            }
            if (!_moved) return;
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
