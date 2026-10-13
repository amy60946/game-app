using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Ada haritası (M5): parmakla kaydırılır, bölgeye dokununca oraya gidilir. Kilitli bölge gri ve
    /// "Seviye N'de açılır!" der (havuç etkisi); yeni açılan bölgede "Yeni!" etiketi.
    /// </summary>
    public sealed class MapScreen : ScreenBase
    {
        private MapWorld _world;
        private List<RegionView> _views;
        private readonly Dictionary<string, RectTransform> _labels = new Dictionary<string, RectTransform>();
        private Vector2 _pan;                       // kamera kaydırması (x, z)
        private Vector3 _press, _last;
        private bool _down, _moved;
        private SpeechBubble _toast;
        private RectTransform _labelLayer;
        private List<Sparkle> _sparkles = new List<Sparkle>();
        private int Day => Logic.Economy.XpSystem.DayNumber(App.LocalNow);

        private static readonly Vector2 PanMin = new Vector2(-2.6f, -1.2f), PanMax = new Vector2(2.6f, 3.0f);

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            App.Stage.AllowDrag = false;
            _views = App.Map.View(App.Level, App.State.VisitedRegions);
            _world = MapWorld.Create(_views);
            _pan = new Vector2(0f, 0.4f);
            PlaceCamera();

            if (App.Map != null && App.Levels.IsUnlocked(Sparkles.UnlockId, App.Level))
            {
                _sparkles = Sparkles.Open(App.State.Sparkles, Day, Sparkles.ForDay(Day, App.State.ChildId, App.Level,
                    Logic.Pet.PetCare.IsNight(App.LocalNow), App.Data.Collection, App.Map.Regions));
                foreach (var sp in _sparkles) _world.AddSparkle(sp.Index, sp.X, sp.Z);
            }

            _labelLayer = Ui.Fill(Root, "Labels");
            foreach (var v in _views) _labels[v.Region.Id] = Label(v);

            var header = Header(T("map.title"));
            header.text = App.State.Wallet.Available.ToString();
            var next = App.Map.NextToUnlock(App.Level, App.State.VisitedRegions);
            if (next != null)
            {
                var hint = Ui.Rect(Root, "Next", new Vector2(0.5f, 0f), new Vector2(900f, 90f));
                hint.pivot = new Vector2(0.5f, 0f);
                hint.anchoredPosition = new Vector2(0f, NavHeight + 20f);
                Ui.Panel(hint, new Color(1f, 1f, 1f, 0.9f), 45f).raycastTarget = false;
                Ui.Label(hint, T("map.next", next.Region.Name, next.UnlockLevel), Th.Font(36), Th.Text, new Vector2(0.5f, 0.5f), new Vector2(880f, 80f), FontStyle.Bold);
            }
            _toast = Bubble(new Vector2(0.5f, 0.8f));
            NavBar(AppPage.Map);
        }

        private RectTransform Label(RegionView v)
        {
            var rt = Ui.Rect(_labelLayer, v.Region.Id, new Vector2(0f, 0f), new Vector2(300f, 70f));
            rt.pivot = new Vector2(0.5f, 0f);
            var bg = Ui.Panel(rt, v.Unlocked ? new Color(1f, 1f, 1f, 0.92f) : new Color(0.25f, 0.28f, 0.38f, 0.8f), 35f);
            bg.raycastTarget = false;
            var text = v.Unlocked ? v.Region.Name : v.Region.Name + " · Sv " + v.UnlockLevel;
            Ui.Label(rt, text, Th.Font(28), v.Unlocked ? Th.Text : Color.white, new Vector2(0.5f, 0.5f), new Vector2(290f, 66f), FontStyle.Bold);
            if (v.IsNew)
            {
                var badge = Ui.Rect(rt, "New", new Vector2(0.5f, 1f), new Vector2(120f, 50f), new Vector2(0f, 26f));
                Ui.Panel(badge, Th.Danger, 25f).raycastTarget = false;
                Ui.Label(badge, T("map.new"), Th.Font(26), Color.white, new Vector2(0.5f, 0.5f), new Vector2(120f, 50f), FontStyle.Bold);
                badge.gameObject.AddComponent<Pulse>();
            }
            return rt;
        }

        private void PlaceCamera()
        {
            var target = MapWorld.Origin + new Vector3(_pan.x, 0f, _pan.y);
            var pos = target + new Vector3(0f, 7.6f, -6.4f);
            App.Stage.SetCamera(pos, 50f, 50f);
        }

        private void Update()
        {
            HandleInput();
            PlaceCamera();
            var cam = App.Stage.Camera;
            var scale = Root.rect.width / Mathf.Max(1f, Screen.width);
            foreach (var kv in _labels)
            {
                var t = _world.Regions[kv.Key];
                var sp = cam.WorldToScreenPoint(t.position + Vector3.up * 1.15f);
                kv.Value.gameObject.SetActive(sp.z > 0f);
                kv.Value.anchoredPosition = new Vector2(sp.x * scale, sp.y * scale);
            }
        }

        private void HandleInput()
        {
            if (Input.GetMouseButtonDown(0) && !OverUi())
            {
                _down = true; _moved = false;
                _press = _last = Input.mousePosition;
            }
            if (_down && Input.GetMouseButton(0))
            {
                var d = Input.mousePosition - _last;
                if ((Input.mousePosition - _press).magnitude > Screen.width * 0.02f) _moved = true;
                var k = 9f / Mathf.Max(1f, Screen.width);
                _pan -= new Vector2(d.x, d.y) * k;
                _pan = Vector2.Max(PanMin, Vector2.Min(PanMax, _pan));
                _last = Input.mousePosition;
            }
            if (_down && Input.GetMouseButtonUp(0))
            {
                _down = false;
                if (!_moved) Tap(Input.mousePosition);
            }
        }

        private static bool OverUi()
        {
            var es = UnityEngine.EventSystems.EventSystem.current;
            if (es == null) return false;
            if (Input.touchCount > 0) return es.IsPointerOverGameObject(Input.GetTouch(0).fingerId);
            return es.IsPointerOverGameObject();
        }

        private void Tap(Vector3 screen)
        {
            var ray = App.Stage.Camera.ScreenPointToRay(screen);
            if (!Physics.Raycast(ray, out var hit, 100f)) return;
            var id = hit.collider.gameObject.name;
            if (id.StartsWith("sparkle_"))
            {
                Collect(hit.collider.gameObject, id);
                return;
            }
            var v = _views.FirstOrDefault(x => x.Region.Id == id);
            if (v == null) return;
            if (!v.Unlocked)
            {
                _toast.Say(T("map.locked", v.Region.Name, v.UnlockLevel));
                return;
            }
            App.State.VisitedRegions.Add(id);
            App.Save();
            App.Enter(v.Region, msg => _toast.Say(msg));
        }

        private void Collect(GameObject go, string id)
        {
            var idx = int.Parse(id.Substring("sparkle_".Length));
            var sp = _sparkles.FirstOrDefault(s => s.Index == idx);
            if (sp == null) return;
            Sparkles.Take(App.State.Sparkles, Day, sp);
            Destroy(go);
            var entry = App.Data.Collection.FirstOrDefault(e => e.Id == sp.EntryId);
            if (entry == null) return;
            var isNew = Logic.Meta.CollectionBook.Discover(App.State.Collection, entry, App.State.Counters);
            _toast.Say(isNew ? T("map.sparkle_new", entry.Name) : T("map.sparkle_again", entry.Name));
            App.Save();
            App.GrantXp(isNew ? 10 : 3, Logic.Economy.XpSource.Achievement);
        }

        private void OnDestroy()
        {
            if (_world != null) Destroy(_world.gameObject);
            if (App != null && App.Stage != null) App.Stage.AllowDrag = true;
        }
    }

    /// <summary>Hafif büyüyüp küçülen dikkat çekici (ör. "Yeni!" etiketi).</summary>
    public sealed class Pulse : MonoBehaviour
    {
        private void Update()
        {
            var s = 1f + Mathf.Sin(Time.unscaledTime * 5f) * 0.08f;
            transform.localScale = new Vector3(s, s, 1f);
        }
    }
}
