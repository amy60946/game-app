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
        private float _runBlend;                    // 0 yürüme/durma … 1 koşma (kamera uzaklığı, görüş açısı)
        private Vector3 _camVel, _lookVel;
        private Vector3 _camPos, _camLook;
        // dokunma: her parmak ayrı izlenir (sol yarı joystick, sağ yarı kamera; aynı anda iki başparmak)
        private enum Role { Stick, Look, Pan }
        private sealed class Finger { public Vector2 Press, Last; public bool Moved; public Role Role; }
        private readonly Dictionary<int, Finger> _fingers = new Dictionary<int, Finger>();
        private int _stickFinger = int.MinValue;
        private readonly HashSet<int> _alive = new HashSet<int>();
        private readonly List<int> _stale = new List<int>();
        private Vector2 _press;                    // joystick merkezi (ekran pikseli)
        private bool _moved;                       // joystick sürüklendi mi
        private float _lastTouch = -10f;           // dokunma sonrası taklit fare olaylarını yok saymak için
        private float _userPitch = 20f;            // sağ başparmakla ayarlanan bakış yüksekliği (derece)
        private float _lookHold;                   // elle döndürdükten sonra otomatik takibin beklediği süre
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
            _views = App.Map.View(App.Level, App.State.VisitedRegions, App.Data.SunBook, App.State.SunStones);
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
                    Logic.Pet.PetCare.CollectTime(App.LocalNow), App.Data.Collection, _terrain));
                foreach (var sp in _sparkles) _sparkleObjs[sp.Index] = _world.AddSparkle(sp.Index, sp.X, sp.Z);
            }

            _labelLayer = Ui.Fill(Root, "Labels");
            foreach (var v in _views) _labels[v.Region.Id] = Label(v);
            BuildGather();   // kütük/çalı/taş + kulübe yeri, nesne üstü baloncuklar

            BuildHud();
            _toast = Bubble(new Vector2(0.5f, 0.66f));   // petin başının üstünde

            SnapCamera();
            _toast.Say(T("map.hint_walk"));
        }

        private void ToggleMode()
        {
            _overview = !_overview;
            if (_overview) TipDone(Onboarding.Overview); else TipDone(null);
            if (_modeText != null) _modeText.text = T(_overview ? "map.walk" : "map.overview");
            RefreshTracker();
            if (_world.Walker != null) _world.Walker.Steer(Vector2.zero);
            if (_overview) _pan = new Vector2(0f, _terrain.Def.Cz - 6f);   // kuşbakışı: adanın ortası
            _toast.Say(T(_overview ? "map.hint_overview" : "map.hint_walk"));
        }

        private RectTransform Label(RegionView v)
        {
            var rt = Ui.Rect(_labelLayer, v.Region.Id, new Vector2(0f, 0f), new Vector2(300f, 64f));
            rt.pivot = new Vector2(0.5f, 0f);
            // yer adı: yarı saydam şeker etiket (açık: deniz mavisi, kilitli: gri), oyun yazı tarzı
            var text = v.Unlocked ? v.Region.Name
                : v.Spot != null ? v.Region.Name + " · " + T("map.stones_short", v.StonesLeft)   // Güneş Taşı ile açılır
                : v.Region.Name + " · Sv " + v.UnlockLevel;
            Candy.Tag(rt, text, v.Unlocked ? new Color(0.1f, 0.36f, 0.68f, 0.86f) : new Color(0.3f, 0.32f, 0.42f, 0.82f), 30, 64f);
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
            // Profesyonel üçüncü şahıs kamera (yay-kol): petin arkasından ~20° yükseklikte, pet kadrajın alt üçte birinde,
            // gidilen yöne biraz önden bakar; koşarken hafif uzaklaşır; yön ölü bölge ile yavaşça izlenir (çocukta baş dönmesi yok);
            // bina/zemin araya girerse kamera öne kayar.
            var w = _world.Walker;
            var p = w.transform.position;
            var scale = w.transform.lossyScale.y;
            var hgt = PetModels.RealHeight * scale;
            var running = w.Moving || w.Steering;
            _lookHold = Mathf.Max(0f, _lookHold - Time.deltaTime);
            if (running && _lookHold <= 0f)
            {
                // otomatik takip yalnız ileri giderken ve yavaş: yana itince kamera dönmez (dönme döngüsü/baş dönmesi yok);
                // geri gelirken (≥ 120°) hiç dönmez — pet kameraya doğru yürür, mobil oyunlardaki gibi
                var diff = Mathf.DeltaAngle(_camYaw, w.Heading);
                var forward = Mathf.Clamp01(Mathf.Cos(diff * Mathf.Deg2Rad));
                if (Mathf.Abs(diff) > 12f && Mathf.Abs(diff) < 120f)
                    _camYaw += diff * (1f - Mathf.Exp(-0.9f * forward * Time.deltaTime));
            }
            _runBlend = Mathf.MoveTowards(_runBlend, running ? 1f : 0f, Time.deltaTime * 1.5f);
            var fwd = Quaternion.Euler(0f, _camYaw, 0f) * Vector3.forward;
            var dist = Mathf.Lerp(4.3f, 4.6f, _runBlend) * Mathf.Max(0.85f, scale);   // pet kadrajda büyük (çocuğun odağı); durunca da geniş görüş
            var pivot = p + Vector3.up * (hgt * 0.9f);
            look = p + Vector3.up * (hgt * 0.55f) + fwd * Mathf.Lerp(1.3f, 1.5f, _runBlend);   // pet baştan ayağa ekranın alt-ortasında (yakın kamerada ayaklar kesilmesin), önü görünür
            // çarpışma (yay-kol + bıyık): arkada bina/tepe varsa kamera önce yana döner (±30°…±90°) ve açık görüş arar;
            // yoksa biraz yükselir (30°, 45°); hâlâ kapalıysa yaklaşır ama petin içine girmez. Dönüş ve yükselme yumuşak.
            float targetPitch = _userPitch, yawOff = 0f;
            var found = false;
            foreach (var p0 in BoomPitches)
            {
                var pitch = Mathf.Max(p0, _userPitch);
                foreach (var off in WhiskerYaws)
                {
                    if (p0 > 30f && off != 0f) continue;                      // yüksek açıda yan arama yok
                    var f = Quaternion.Euler(0f, _camYaw + off, 0f) * Vector3.forward;
                    if (CameraBlocked(pivot, Boom(pitch, f), dist, out _)) continue;
                    targetPitch = pitch; yawOff = off; found = true; break;
                }
                if (found) break;
            }
            if (found && yawOff != 0f && _lookHold <= 0f) _camYaw += yawOff * (1f - Mathf.Exp(-2.5f * Time.deltaTime));
            _camPitch = Mathf.Lerp(_camPitch, found ? targetPitch : Mathf.Max(32f, _userPitch), 1f - Mathf.Exp(-3f * Time.deltaTime));
            fwd = Quaternion.Euler(0f, _camYaw, 0f) * Vector3.forward;
            var dir = Boom(_camPitch, fwd);
            if (CameraBlocked(pivot, dir, dist, out var hitDist)) dist = Mathf.Max(2.8f, hitDist - 0.3f);   // dönerken geçici
            pos = pivot + dir * dist;
            var floor = _world.transform.TransformPoint(new Vector3(0f, _terrain.Height(pos.x - MapWorld.Origin.x, pos.z - MapWorld.Origin.z), 0f)).y + 0.8f;
            if (pos.y < floor) pos.y = floor;
            fov = Mathf.Lerp(52f, 54f, _runBlend);   // durunca görüş daralmasın (kullanıcı geri bildirimi)
        }

        private static readonly float[] BoomPitches = { 20f, 30f, 45f };
        private static readonly float[] WhiskerYaws = { 0f, 30f, -30f, 60f, -60f, 90f, -90f };
        private float _camPitch = 20f;

        private static Vector3 Boom(float pitchDeg, Vector3 fwd)
        {
            var e = pitchDeg * Mathf.Deg2Rad;
            return -fwd * Mathf.Cos(e) + Vector3.up * Mathf.Sin(e);
        }

        /// <summary>Pivot → kamera yönünde görüşü kapatan engel var mı (pet ve parıltılar sayılmaz).</summary>
        private static bool CameraBlocked(Vector3 pivot, Vector3 dir, float dist, out float hitDist)
        {
            hitDist = dist;
            var hits = Physics.SphereCastAll(pivot, 0.35f, dir, dist, ~0, QueryTriggerInteraction.Ignore);
            var blocked = false;
            foreach (var h in hits)
            {
                if (h.collider.gameObject.name == "pet" || h.collider is SphereCollider) continue;
                if (h.distance <= 0f) continue;                                   // pivot zaten içindeyse (kapı önü) sayma
                if (h.distance < hitDist) hitDist = h.distance;
                blocked = true;
            }
            return blocked;
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
            // dokunma başka ekran açtıysa (ör. pete dokun → Dolap) bu karede kamerayı geri çekme: dolapta pet görünmüyordu
            if (!gameObject.activeInHierarchy) return;
            UpdateGather();
            UpdateHud();
            TargetCamera(out var pos, out var look, out var fov);
            var lag = _overview ? 0.25f : 0.16f;
            _camPos = Vector3.SmoothDamp(_camPos, pos, ref _camVel, lag);
            _camLook = Vector3.SmoothDamp(_camLook, look, ref _lookVel, lag * 0.7f);
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
            _alive.Clear();
            if (Input.touchCount > 0)
            {
                _lastTouch = Time.unscaledTime;
                for (var i = 0; i < Input.touchCount; i++)
                {
                    var t = Input.GetTouch(i);
                    if (t.phase == TouchPhase.Began) FingerDown(t.fingerId, t.position, OverUi(t.fingerId));
                    else if (t.phase == TouchPhase.Moved || t.phase == TouchPhase.Stationary) FingerMove(t.fingerId, t.position);
                    else { FingerUp(t.fingerId, t.position, t.phase == TouchPhase.Canceled); continue; }
                    _alive.Add(t.fingerId);
                }
            }
            else if (Time.unscaledTime - _lastTouch >= 0.5f)       // dokunmatikte tarayıcının taklit fare olaylarını yok say
            {
                const int mouse = -1;
                if (Input.GetMouseButtonDown(0)) FingerDown(mouse, Input.mousePosition, OverUi(mouse));
                else if (Input.GetMouseButton(0)) FingerMove(mouse, Input.mousePosition);
                // çok hızlı tıklamada basma ve bırakma aynı karede gelebiliyor: bırakmayı da işle (yoksa dokunma kayboluyordu)
                if (Input.GetMouseButtonUp(0)) FingerUp(mouse, Input.mousePosition, false);
                if (Input.GetMouseButton(0)) _alive.Add(mouse);
            }
            // iPhone Safari parmak kalkınca "bitti" olayını bazen kaybediyor: ekranda olmayan parmakları bırak
            // (yoksa joystick takılı kalıp pet haritanın sonuna kadar yürüyordu)
            if (_fingers.Count > _alive.Count)
            {
                _stale.Clear();
                foreach (var id in _fingers.Keys) if (!_alive.Contains(id)) _stale.Add(id);
                foreach (var id in _stale) FingerUp(id, _fingers[id].Last, true);
            }
            if (_stickFinger == int.MinValue && _world.Walker != null && _world.Walker.Steering) EndStick();
        }

        private void FingerDown(int id, Vector2 pos, bool overUi)
        {
            if (overUi) return;
            var role = _overview ? Role.Pan
                : _world.Walker != null && pos.x < Screen.width * 0.5f && _stickFinger == int.MinValue ? Role.Stick : Role.Look;
            _fingers[id] = new Finger { Press = pos, Last = pos, Role = role };
            if (role == Role.Stick) { _stickFinger = id; _press = pos; _moved = false; }
        }

        private void FingerMove(int id, Vector2 pos)
        {
            if (!_fingers.TryGetValue(id, out var f)) return;
            var d = pos - f.Last;
            if (!f.Moved && (pos - f.Press).magnitude > Screen.height * 0.025f) f.Moved = true;
            switch (f.Role)
            {
                case Role.Stick:
                    HandleStick(pos);
                    break;
                case Role.Look:
                    if (!f.Moved) break;
                    // ekran genişliği kadar kaydırma ≈ 150° dönüş; dikeyde 10°–48° arası (yaygın mobil oyun hassasiyeti)
                    var k = 150f / Mathf.Max(1f, Screen.width);
                    _camYaw += d.x * k;
                    _userPitch = Mathf.Clamp(_userPitch - d.y * k * 0.6f, 10f, 48f);
                    _lookHold = 2.5f;
                    if (Mathf.Abs(d.x) + Mathf.Abs(d.y) > 0.5f) TipDone(Onboarding.Look);
                    break;
                case Role.Pan:
                    if (!f.Moved) break;
                    var kp = 60f / Mathf.Max(1f, Screen.width);
                    _pan -= d * kp;
                    _pan = Vector2.Max(new Vector2(_terrain.MinX + 8f, _terrain.MinZ + 6f), Vector2.Min(new Vector2(_terrain.MaxX - 8f, _terrain.MaxZ - 16f), _pan));
                    break;
            }
            f.Last = pos;
        }

        private void FingerUp(int id, Vector2 pos, bool canceled)
        {
            if (!_fingers.TryGetValue(id, out var f)) return;
            _fingers.Remove(id);
            var tapped = !f.Moved && !canceled;
            if (f.Role == Role.Stick)
            {
                _stickFinger = int.MinValue;
                tapped = !_moved && !canceled;
                EndStick();
            }
            if (tapped) Tap(pos);
        }

        private static bool OverUi(int fingerId)
        {
            var es = UnityEngine.EventSystems.EventSystem.current;
            if (es == null) return false;
            return fingerId >= 0 ? es.IsPointerOverGameObject(fingerId) : es.IsPointerOverGameObject();
        }

        private void Tap(Vector3 screen)
        {
            var ray = App.Stage.Camera.ScreenPointToRay(screen);
            // pet ve parıltı öncelikli: bina dokunma kutuları geniş, pet kapı önündeyken ışını önce onlar yakalıyordu
            var hits = Physics.RaycastAll(ray, 400f);
            if (hits.Length == 0) return;
            System.Array.Sort(hits, (x, y) => x.distance.CompareTo(y.distance));
            var hit = hits[0];
            foreach (var h in hits) if (h.collider.gameObject.name == "pet") { hit = h; break; }
            if (hit.collider.gameObject.name != "pet")
                foreach (var h in hits) if (h.collider.gameObject.name.StartsWith("sparkle_")) { hit = h; break; }
            var go = hit.collider.gameObject;
            if (go.name == "pet" && !_overview)
            {
                TipDone(Onboarding.Wardrobe);
                App.Stage.SetPetVisible(true);
                App.Open(AppPage.Wardrobe);   // giydirme: pete dokununca
                return;
            }
            if (go.name == "gather_site") { TapSite(); return; }
            if (go.name.StartsWith("gather_") && int.TryParse(go.name.Substring("gather_".Length), out var gi)) { TapNode(gi); return; }
            if (go.name.StartsWith("sparkle_"))
            {
                var spot = _world.Local(go.transform.position);
                GoTo(spot.x, spot.y, () => { if (go != null) Collect(go, go.name); });
                return;
            }
            var v = _views.FirstOrDefault(x => x.Region.Id == go.name);
            if (v != null)
            {
                if (!v.Unlocked) _toast.Say(v.Spot != null ? T("map.locked_stones", v.Region.Name, v.StonesLeft) : T("map.locked", v.Region.Name, v.UnlockLevel));
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
        public string DebugPetScreen()
        {
            if (_world.Walker == null) return "yok";
            var sp = App.Stage.Camera.WorldToScreenPoint(_world.Walker.transform.position + Vector3.up * 0.7f);
            return $"{sp.x:0} {sp.y:0} {Screen.width} {Screen.height}";
        }

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
