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
    /// Gezilebilir ada (M5, 14 Ekim 2026 kararı: dokun-yürü + kuşbakışı).
    /// Yürü: yere dokun → pet oraya yürür; binaya dokun → kapısına yürür ve girer; parıltıya dokun → gidip toplar.
    /// Parmakla yana sürüklemek kamerayı petin çevresinde döndürür. Kuşbakışı: tüm ada, kaydırılır; dokunulan yere
    /// pet hemen gider (hızlı geçiş). Kilitli bölge gri ve "Seviye N'de açılır!" der; yeni açılanda "Yeni!".
    /// </summary>
    public sealed partial class MapScreen : ScreenBase
    {
        private static IslandTerrain _terrain;   // oturum boyunca bir kez kurulur

        private MapWorld _world;
        private List<RegionView> _views;
        private readonly Dictionary<string, RectTransform> _labels = new Dictionary<string, RectTransform>();
        private bool _overview;
        private Vector2 _pan;                       // kuşbakışı kaydırma (x, z)
        private float _camYaw;                      // yürüme kamerasının pet çevresindeki açısı
        private Vector3 _camPos, _camLook;
        private Vector3 _press, _last;
        private bool _down, _moved, _stick;
        private SpeechBubble _toast;
        private RectTransform _labelLayer;
        private Text _modeText;
        private List<Sparkle> _sparkles = new List<Sparkle>();
        private int Day => Logic.Economy.XpSystem.DayNumber(App.LocalNow);

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            App.Stage.AllowDrag = false;
            if (_terrain == null) _terrain = new IslandTerrain(App.Map.Regions, App.Map.Terrain);
            _views = App.Map.View(App.Level, App.State.VisitedRegions);
            _world = MapWorld.Create(_views, _terrain);

            // Pet: en son girilen bölgenin kapısında (yoksa evin önünde) belirir
            var start = _terrain.Regions.FirstOrDefault(r => r.Id == App.State.LastRegion) ?? _terrain.Regions.FirstOrDefault(r => r.Id == "region_home");
            var (sx, sz) = start != null ? _terrain.Door(start) : (_terrain.PlazaX, _terrain.PlazaZ);
            var def = App.Data.Pet(App.State.PetId);
            var items = App.State.Inventory.Equipped.Values.Select(App.Data.Item).Where(i => i != null).ToList();
            if (def != null) { _world.PlacePet(def, PetModels.StageScale(App.Growth), items, sx, sz); _world.Walker.Teleport(sx, sz, 0f); _camYaw = 0f; }

            if (App.Levels.IsUnlocked(Sparkles.UnlockId, App.Level))
            {
                _sparkles = Sparkles.Open(App.State.Sparkles, Day, Sparkles.ForDay(Day, App.State.ChildId, App.Level,
                    Logic.Pet.PetCare.IsNight(App.LocalNow), App.Data.Collection, _terrain));
                foreach (var sp in _sparkles) _sparkleObjs[sp.Index] = _world.AddSparkle(sp.Index, sp.X, sp.Z);
            }

            _labelLayer = Ui.Fill(Root, "Labels");
            foreach (var v in _views) _labels[v.Region.Id] = Label(v);

            BuildHud();
            _toast = Bubble(new Vector2(0.5f, 0.78f));

            SnapCamera();
            _toast.Say(T("map.hint_walk"));
        }

        private void ToggleMode()
        {
            _overview = !_overview;
            if (_overview) TipDone(Onboarding.Overview); else TipDone(null);
            if (_modeText != null) _modeText.text = T(_overview ? "map.walk" : "map.overview");
            if (_world.Walker != null) _world.Walker.Steer(Vector2.zero);
            if (_overview) _pan = new Vector2(0f, _terrain.Def.Cz - 6f);   // kuşbakışı: adanın ortası
            _toast.Say(T(_overview ? "map.hint_overview" : "map.hint_walk"));
        }

        private RectTransform Label(RegionView v)
        {
            var rt = Ui.Rect(_labelLayer, v.Region.Id, new Vector2(0f, 0f), new Vector2(300f, 70f));
            rt.pivot = new Vector2(0.5f, 0f);
            var bg = Ui.Panel(rt, v.Unlocked ? new Color(1f, 1f, 1f, 0.92f) : new Color(0.25f, 0.28f, 0.38f, 0.8f), 35f);
            bg.raycastTarget = false;
            var text = v.Unlocked ? v.Region.Name : v.Region.Name + " · Sv " + v.UnlockLevel;
            Ui.Label(rt, text, Th.Font(28), v.Unlocked ? Th.Text : Color.white, new Vector2(0.5f, 0.5f), new Vector2(290f, 66f), FontStyle.Bold);
            if (v.Unlocked && IsPlayPlace(v.Region))
            {
                // oyun yerinin üstünde "Oyna!" çağrısı
                var play = Ui.Rect(rt, "Play", new Vector2(0.5f, 1f), new Vector2(220f, 84f), new Vector2(0f, 56f));
                var img = play.gameObject.AddComponent<Image>();
                img.sprite = Ui.Rounded; img.type = Image.Type.Sliced; img.color = Candy.Green; img.raycastTarget = false;
                var o = play.gameObject.AddComponent<Outline>(); o.effectColor = Color.white; o.effectDistance = new Vector2(4f, -4f);
                Candy.Caption(play, T("hud.play"), 44, new Vector2(0.5f, 0.5f), new Vector2(220f, 84f));
                play.gameObject.AddComponent<Pulse>();
            }
            if (v.IsNew)
            {
                var badge = Ui.Rect(rt, "New", new Vector2(0.5f, 1f), new Vector2(120f, 50f), new Vector2(0f, 26f));
                Ui.Panel(badge, Th.Danger, 25f).raycastTarget = false;
                Ui.Label(badge, T("map.new"), Th.Font(26), Color.white, new Vector2(0.5f, 0.5f), new Vector2(120f, 50f), FontStyle.Bold);
                badge.gameObject.AddComponent<Pulse>();
            }
            return rt;
        }

        // ------------------------------------------------------------------ kamera

        private void TargetCamera(out Vector3 pos, out Vector3 look, out float fov)
        {
            if (_overview || _world.Walker == null)
            {
                var c = _overview ? _pan : new Vector2(_terrain.PlazaX, _terrain.PlazaZ + 6f);
                look = MapWorld.Origin + new Vector3(c.x, 0f, c.y + 4f);
                pos = look + new Vector3(0f, 44f, -34f);
                fov = 40f;
                return;
            }
            // Üçüncü şahıs (14 Ekim 2026 geri bildirimi): petin arkasından, başının biraz üstünden, yakın; pet döndükçe kamera yavaşça arkasına geçer
            var w = _world.Walker;
            var p = w.transform.position;
            var hgt = PetModels.RealHeight * w.transform.lossyScale.y;
            if (w.Moving || w.Steering) _camYaw = Mathf.MoveTowardsAngle(_camYaw, w.Heading, 110f * Time.deltaTime);
            var fwd = Quaternion.Euler(0f, _camYaw, 0f) * Vector3.forward;
            look = p + Vector3.up * (hgt * 0.85f) + fwd * 1.6f;
            pos = p + Vector3.up * (hgt + 1.55f) - fwd * 4.9f;
            fov = 52f;
        }

        private void SnapCamera()
        {
            TargetCamera(out _camPos, out _camLook, out var fov);
            App.Stage.Camera.fieldOfView = fov;
            ApplyCamera(fov);
        }

        private void ApplyCamera(float fov)
        {
            var cam = App.Stage.Camera;
            cam.transform.SetPositionAndRotation(_camPos, Quaternion.LookRotation(_camLook - _camPos));
            cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, fov, 0.15f);
        }

        private void Update()
        {
            HandleInput();
            UpdateHud();
            TargetCamera(out var pos, out var look, out var fov);
            var k = 1f - Mathf.Exp(-6f * Time.deltaTime);
            _camPos = Vector3.Lerp(_camPos, pos, k);
            _camLook = Vector3.Lerp(_camLook, look, k);
            ApplyCamera(fov);

            var cam = App.Stage.Camera;
            var scale = Root.rect.width / Mathf.Max(1f, Screen.width);
            var petPos = _world.Walker != null ? _world.Walker.transform.position : _camLook;
            foreach (var kv in _labels)
            {
                var t = _world.Regions[kv.Key];
                var near = _overview || Vector3.Distance(t.position, petPos) < 26f;
                var lh = _world.LabelHeights.TryGetValue(kv.Key, out var hh) ? hh : 1.5f;
                if (!_overview) lh = Mathf.Min(lh, 3.4f);   // yakın kamerada etiket kadrajda kalsın (kapı üstü)
                var sp = cam.WorldToScreenPoint(t.position + Vector3.up * lh);
                kv.Value.gameObject.SetActive(near && sp.z > 0f);
                kv.Value.anchoredPosition = new Vector2(sp.x * scale, sp.y * scale);
            }
        }

        // ------------------------------------------------------------------ dokunma

        private void HandleInput()
        {
            if (Input.GetMouseButtonDown(0) && !OverUi())
            {
                _down = true; _moved = false;
                _press = _last = Input.mousePosition;
                _stick = !_overview && _world.Walker != null;   // joystick ekranın her yerinde (kamera sürükleme kaldırıldı)
            }
            if (_stick)
            {
                if (_down && Input.GetMouseButton(0)) { HandleStick(Input.mousePosition); return; }
                if (Input.GetMouseButtonUp(0))
                {
                    _down = false; _stick = false;
                    var moved = _moved;
                    EndStick();
                    if (!moved) Tap(Input.mousePosition);
                }
                return;
            }
            if (_down && Input.GetMouseButton(0))
            {
                var d = Input.mousePosition - _last;
                if ((Input.mousePosition - _press).magnitude > Screen.width * 0.02f) _moved = true;
                if (_moved)
                {
                    if (_overview)
                    {
                        var k = 60f / Mathf.Max(1f, Screen.width);
                        _pan -= new Vector2(d.x, d.y) * k;
                        _pan = Vector2.Max(new Vector2(_terrain.MinX + 8f, _terrain.MinZ + 6f), Vector2.Min(new Vector2(_terrain.MaxX - 8f, _terrain.MaxZ - 16f), _pan));
                    }

                }
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
            if (!Physics.Raycast(ray, out var hit, 400f)) return;
            var go = hit.collider.gameObject;
            if (go.name == "pet" && !_overview)
            {
                TipDone(Onboarding.Wardrobe);
                App.Stage.SetPetVisible(true);
                App.Open(AppPage.Wardrobe);   // giydirme: pete dokununca
                return;
            }
            if (go.name.StartsWith("sparkle_"))
            {
                var spot = _world.Local(go.transform.position);
                GoTo(spot.x, spot.y, () => { if (go != null) Collect(go, go.name); });
                return;
            }
            var v = _views.FirstOrDefault(x => x.Region.Id == go.name);
            if (v != null)
            {
                if (!v.Unlocked) _toast.Say(T("map.locked", v.Region.Name, v.UnlockLevel));
                var (dx, dz) = _terrain.Door(v.Region);
                GoTo(dx, dz, v.Unlocked ? () => EnterRegion(v) : (System.Action)null);
                return;
            }
            if (go.name == "ground")
            {
                TipDone(Onboarding.Walk);
                var p = _world.Local(hit.point);
                GoTo(p.x, p.y, null);
            }
        }

        /// <summary>Yürü modunda yürür; kuşbakışında hemen oraya geçer (hızlı geçiş) ve yürü moduna döner.</summary>
        private void GoTo(float x, float z, System.Action arrived)
        {
            var walker = _world.Walker;
            if (walker == null) { arrived?.Invoke(); return; }
            if (_overview)
            {
                var w = _terrain.NearestWalkable(x, z);
                if (float.IsNaN(w.x)) return;
                walker.Teleport(w.x, w.z, _camYaw);
                ToggleMode();
                SnapCamera();
                arrived?.Invoke();
                return;
            }
            if (!walker.WalkTo(x, z, arrived)) arrived?.Invoke();
        }

        /// <summary>Bölgeye gir (ör. hata ayıklama: "region region_shop").</summary>
        public void EnterById(string id)
        {
            var v = _views.FirstOrDefault(x => x.Region.Id == id);
            if (v != null && v.Unlocked) EnterRegion(v);
        }

        private void EnterRegion(RegionView v)
        {
            App.State.VisitedRegions.Add(v.Region.Id);
            App.State.LastRegion = v.Region.Id;
            App.Save();
            App.Enter(v.Region, msg => _toast.Say(msg));
        }

        private void Collect(GameObject go, string id)
        {
            var idx = int.Parse(id.Substring("sparkle_".Length));
            var sp = _sparkles.FirstOrDefault(s => s.Index == idx);
            if (sp == null) return;
            Sparkles.Take(App.State.Sparkles, Day, sp);
            TipDone(Onboarding.Sparkle);
            Destroy(go);
            var entry = App.Data.Collection.FirstOrDefault(e => e.Id == sp.EntryId);
            if (entry == null) return;
            var isNew = Logic.Meta.CollectionBook.Discover(App.State.Collection, entry, App.State.Counters);
            _toast.Say(isNew ? T("map.sparkle_new", entry.Name) : T("map.sparkle_again", entry.Name));
            App.Save();
            App.GrantXp(isNew ? 10 : 3, Logic.Economy.XpSource.Achievement);
        }

        /// <summary>Hata ayıklama/test: kamera modunu değiştir, ada üzerinde bir noktaya yürü.</summary>
        public void DebugToggle() => ToggleMode();
        public void DebugWalk(float x, float z) => GoTo(x, z, null);

        private void OnDestroy()
        {
            HudDestroy();
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
