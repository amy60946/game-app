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
            if (_terrain == null) _terrain = new IslandTerrain(App.Map.Regions, App.Map.Terrain, App.Island);
            _views = App.Map.View(App.Level, App.State.VisitedRegions, App.Data.SunBook, App.State.SunStones);
            World.PropCuller.Radius = 95f;
            _world = MapWorld.Create(_views, _terrain);
            SeasonLook.Apply(_world, App.LocalNow);   // H6: gerçek takvimle mevsim

            // Pet: bir pencereden dönülüyorsa kaldığı yerde; yoksa en son girilen bölgenin kapısında (yoksa evin önünde) belirir
            var start = _terrain.Regions.FirstOrDefault(r => r.Id == App.State.LastRegion) ?? _terrain.Regions.FirstOrDefault(r => r.Id == "region_home");
            var (sx, sz) = start != null ? _terrain.Door(start) : (_terrain.PlazaX, _terrain.PlazaZ);
            float heading = 0f, camYaw = 0f;
            if (App.MapSpot is Core.MapSpot spot && !float.IsNaN(spot.X) && !float.IsNaN(spot.Z))
            {
                sx = spot.X; sz = spot.Z; heading = spot.Heading; camYaw = spot.CamYaw;
            }
            var def = App.Data.Pet(App.State.PetId);
            var items = App.State.Inventory.Equipped.Values.Select(App.Data.Item).Where(i => i != null).ToList();
            if (def != null) { _world.PlacePet(def, App.Growth, items, sx, sz); _world.Walker.Teleport(sx, sz, heading); _camYaw = camYaw; }

            if (App.Levels.IsUnlocked(Sparkles.UnlockId, App.Level))
            {
                _sparkles = Sparkles.Open(App.State.Sparkles, Day, Sparkles.ForDay(Day, App.State.ChildId, App.Level,
                    Logic.Pet.PetCare.CollectTime(App.LocalNow), App.Data.Collection, _terrain));
                foreach (var sp in _sparkles) _sparkleObjs[sp.Index] = _world.AddSparkle(sp.Index, sp.X, sp.Z, !App.State.Collection.Contains(sp.EntryId));
            }

            // O3 günün küçük sürprizleri: bugün alınmamış olanlar adada belirir
            var todays = Logic.Story.DailySurprises.ForDay(App.Data.Story.Surprises, Day, App.State.ChildId, App.Level);
            _surprises = Logic.Story.SurprisePlaces.Place(todays, Day, App.State.ChildId, _terrain);
            var taken = App.State.Story.SurpriseDay == Day ? App.State.Story.SurprisesTaken : null;
            for (var i = 0; i < _surprises.Count; i++)
            {
                var sp = _surprises[i];
                if (taken != null && taken.Contains(sp.Def.Id)) continue;
                SurpriseView.Create(_world.transform, i, sp.Def.Kind, new Vector3(sp.X, _terrain.Height(sp.X, sp.Z), sp.Z));
            }

            // H2 posta kutusu: Evim'in kapısının yanında; okunmamış mesajda bayrak kalkık
            var home = _terrain.Regions.FirstOrDefault(r => r.Id == "region_home");
            if (home != null)
            {
                var (hx, hz) = _terrain.Door(home);
                var d = new Vector2(hx - home.X, hz - home.Z); d = d.sqrMagnitude > 0.01f ? d.normalized : Vector2.up;
                var side = new Vector2(-d.y, d.x) * 2.6f;
                var mx = hx + side.x; var mz = hz + side.y;
                _mailbox = Mailbox.Create(_world.transform, new Vector3(mx, _terrain.Height(mx, mz), mz), Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg);
                _mailbox.Unread = App.MailUnread > 0;
                RefreshMailFlag();
            }

            _labelLayer = Ui.Fill(Root, "Labels");
            foreach (var v in _views) _labels[v.Region.Id] = Label(v);
            BuildPlaceLabels();
            BuildGather();   // kütük/çalı/taş + kulübe yeri, nesne üstü baloncuklar

            BuildHud();
            _toast = Bubble(new Vector2(0.5f, 0.66f));   // petin başının üstünde

            SnapCamera();
            _toast.Say(T("map.hint_walk"));
            StartCoroutine(StoryCheck());   // Ö4: sırası gelen hikâye sahnesi
        }

        private void ToggleMode()
        {
            _overview = !_overview;
            World.PropCuller.Radius = _overview ? 400f : 95f;   // kuşbakışında bütün ada
            if (_overview) TipDone(Onboarding.Overview); else TipDone(null);
            if (_modeText != null) _modeText.text = T(_overview ? "map.walk" : "map.overview");
            RefreshTracker();
            if (_world.Walker != null) _world.Walker.Steer(Vector2.zero);
            if (_overview) _pan = _terrain.Baked != null ? new Vector2(0f, -18f) : new Vector2(0f, _terrain.Def.Cz - 6f);   // kuşbakışı: adanın ortası
            _toast.Say(T(_overview ? "map.hint_overview" : "map.hint_walk"));
        }

        // onaylı v6 haritasındaki alt yer adları (bölge değil, yalnız kuşbakışında; koyu yeşil hap): spots anahtarı ya da sabit nokta
        private static readonly (string Key, float X, float Z)[] Places =
        {
            ("temple", 0f, -6f), ("spire", 0f, 0f), ("canyon", 0f, 0f), ("lake", 0f, 0f), ("bluebell", 0f, 0f),
            ("forest", 0f, 0f), ("camp", 0f, 0f), ("@ski_piste", -46f, 47f), ("@sea_stack", 76f, -52f),
        };
        private readonly List<(RectTransform Rt, Vector3 At)> _places = new List<(RectTransform, Vector3)>();

        private void BuildPlaceLabels()
        {
            var lay = _terrain.Baked?.Layout;
            if (lay == null) return;
            foreach (var (key, x, z) in Places)
            {
                float px, pz;
                if (key[0] == '@') { px = x; pz = z; }
                else if (lay.Spots.TryGetValue(key, out var s) && s.Length >= 2) { px = s[0] + x; pz = s[1] + z; }
                else continue;
                var id = key.TrimStart('@');
                var rt = Ui.Rect(_labelLayer, "place_" + id, Vector2.zero, new Vector2(260f, 52f));
                rt.pivot = new Vector2(0.5f, 0f);
                Candy.Tag(rt, T("place." + id), new Color(0.13f, 0.27f, 0.24f, 0.86f), 24, 52f);
                _places.Add((rt, _world.World(px, pz) + Vector3.up * 3f));
            }
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
            var hasPlay = v.Unlocked && IsPlayPlace(v.Region);
            if (hasPlay)
            {
                // oyun yerinin üstünde "Oyna!" çağrısı
                var play = Ui.Rect(rt, "Play", new Vector2(0.5f, 1f), new Vector2(220f, 84f), new Vector2(0f, 56f));
                var img = play.gameObject.AddComponent<Image>();
                img.sprite = Ui.Rounded; img.type = Image.Type.Sliced; img.color = Candy.Green; img.raycastTarget = false;
                var o = play.gameObject.AddComponent<Outline>(); o.effectColor = Color.white; o.effectDistance = new Vector2(4f, -4f);
                Candy.Caption(play, T("hud.play"), 44, new Vector2(0.5f, 0.5f), new Vector2(220f, 84f));
                Hover.On(play, 7f, 0.07f);
            }
            if (v.IsNew)
            {
                // "Oyna!" baloncuğu varsa onun üstünde (üst üste binip ikisi de okunmuyordu)
                var badge = Ui.Rect(rt, "New", new Vector2(0.5f, 1f), new Vector2(120f, 50f), new Vector2(0f, hasPlay ? 128f : 26f));
                Ui.Panel(badge, Th.Danger, 25f).raycastTarget = false;
                Ui.Label(badge, T("map.new"), Th.Font(26), Color.white, new Vector2(0.5f, 0.5f), new Vector2(120f, 50f), FontStyle.Bold);
                Hover.On(badge, 5f, 0.08f);
            }
            return rt;
        }

        // ------------------------------------------------------------------ kamera

        private void TargetCamera(out Vector3 pos, out Vector3 look, out float fov)
        {
            if (_cine)
            {
                pos = _cinePos; look = _cineLook; fov = 48f;
                return;
            }
            if (_overview || _world.Walker == null)
            {
                var c = _overview ? _pan : new Vector2(_terrain.PlazaX, _terrain.PlazaZ + 6f);
                look = MapWorld.Origin + new Vector3(c.x, 0f, c.y + 4f);
                var big = _terrain.Baked != null ? 2.1f : 1f;   // v6 ada 2,5 kat büyük: kuşbakışı daha yüksekten
                pos = look + new Vector3(0f, 44f, -34f) * big;
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
            cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, fov - World.HitStop.Zoom, 0.15f);
        }

        private void Update()
        {
            if (!_cine) HandleInput();
            // dokunma başka ekran açtıysa (ör. pete dokun → Dolap) bu karede kamerayı geri çekme: dolapta pet görünmüyordu
            if (!gameObject.activeInHierarchy) return;
            UpdateGather();
            UpdateDressBubble();
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
            foreach (var (rt, at) in _places)
            {
                var sp = cam.WorldToScreenPoint(at);
                rt.gameObject.SetActive(_overview && sp.z > 0f);
                rt.anchoredPosition = new Vector2(sp.x * scale, sp.y * scale);
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
                    var kp = (_terrain.Baked != null ? 130f : 60f) / Mathf.Max(1f, Screen.width);
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
            if (hits.Length == 0) { if (!_overview) TapWater(ray); return; }
            System.Array.Sort(hits, (x, y) => x.distance.CompareTo(y.distance));
            var hit = hits[0];
            foreach (var h in hits) if (h.collider.gameObject.name == "pet") { hit = h; break; }
            if (hit.collider.gameObject.name != "pet")
                foreach (var h in hits) if (h.collider.gameObject.name.StartsWith("sparkle_")) { hit = h; break; }
            if (hit.collider.gameObject.name != "pet" && !hit.collider.gameObject.name.StartsWith("sparkle_"))
                foreach (var h in hits) if (h.collider.gameObject.name.StartsWith("surprise_")) { hit = h; break; }
            var go = hit.collider.gameObject;
            if (go.name == "pet" && !_overview)
            {
                // A1: her dokunuşta sıradaki küçük tepki; giydirme pete dokununca açılan baloncuktan (3,5 sn kalır)
                _world.Walker.React(Logic.Story.OktiReactions.Next(App.State.Story));
                ShowDressBubble();
                return;
            }
            if (go.name == "gather_site") { TapSite(); return; }
            if (go.name.StartsWith("gather_") && int.TryParse(go.name.Substring("gather_".Length), out var gi)) { TapNode(gi); return; }
            if (go.name == "mailbox")
            {
                var spot = _world.Local(go.transform.position);
                GoTo(spot.x, spot.y, () => { Audio.Sfx.Play(Audio.SfxKind.Pop); App.Open(AppPage.Mail); });
                return;
            }
            if (go.name.StartsWith("surprise_"))
            {
                var spot = _world.Local(go.transform.position);
                GoTo(spot.x, spot.y, () => { if (go != null) CollectSurprise(go); });
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
                if (!v.Unlocked) _toast.Say(v.Spot != null ? T("map.locked_stones", v.Region.Name, v.StonesLeft) : T("map.locked", v.Region.Name, v.UnlockLevel));
                var (dx, dz) = _terrain.Door(v.Region);
                GoTo(dx, dz, v.Unlocked ? () => EnterRegion(v) : (System.Action)null);
                return;
            }
            if (go.name == "ground")
            {
                var p = _world.Local(hit.point);
                if (!_overview && _terrain.Height(p.x, p.y) < -0.05f) { TapWater(ray); return; }   // denizin dibi: suya dokunuldu
                if (!_overview) PokeNear(ray, hit.distance, p);
                TipDone(Onboarding.Walk);
                GoTo(p.x, p.y, null);
            }
        }

        // ------------------------------------------------------------------ Ö4 hikâye sahneleri (23 Ekim 2026)

        /// <summary>
        /// Sırası gelen sahneyi oynatır (seviye, onarım noktası, olay). Bölüm açılışı sinema (S1), diğerleri ada üstü (S2) sunuşla;
        /// hikâye kapalıysa yalnız tek satırlık özet. Başka bir kutlama ekrandayken bekler. Ardışık en çok iki sahne.
        /// </summary>
        private System.Collections.IEnumerator StoryCheck()
        {
            yield return new WaitForSeconds(1.2f);
            var book = App.Data.Story; var st = App.State.Story;
            if (book == null || st == null || book.Scenes.Count == 0) yield break;
            var spots = new HashSet<string>(App.Data.SunBook.Spots.Where(s => App.Data.SunBook.IsRepaired(App.State.SunStones, s.Id)).Select(s => s.Id));
            System.Func<string, bool> ev = e => App.State.Counters.Total(e) > 0;
            var existing = App.Level > 1 || App.State.Xp.TotalXp > 0;
            Logic.Story.StoryDirector.Init(st, book, existing, App.Level, spots, ev);
            for (var n = 0; n < 2; n++)
            {
                while (_cine || StoryPlayer.Playing || App.Overlay.transform.Find("LevelUp") != null) yield return new WaitForSeconds(0.5f);
                var scene = Logic.Story.StoryDirector.Next(book, st, App.Level, spots, ev);
                if (scene == null) yield break;
                Logic.Story.StoryDirector.MarkSeen(st, scene);
                App.Save();
                if (!App.State.Settings.StoryOn) { _toast.Say(scene.Summary); yield break; }
                var done = false;
                if (_world.Walker != null) _world.Walker.Steer(Vector2.zero);
                var mode = scene.Trigger == Logic.Story.StoryDirector.Level || scene.Trigger == Logic.Story.StoryDirector.Intro ? StoryPlayer.Mode.Cinema : StoryPlayer.Mode.Island;
                StoryPlayer.Play(App.Overlay.transform, Th, book, scene, mode, Th.Band, App.State.PetName, App.State.PetId, T("story.go"), T("story.skip"), () => done = true);
                while (!done) yield return null;
                yield return new WaitForSeconds(0.6f);
            }
        }

        // ------------------------------------------------------------------ H1 sis kalkış sahnesi (23 Ekim 2026)
        private bool _cine;
        private Vector3 _cinePos, _cineLook;
        private CanvasGroup _hudGroup;

        /// <summary>
        /// Güneş Taşı bölgeyi açınca: arayüz çekilir, sinema bantları iner, kamera bölgeye döner; sis dağılıp yükselir, ışık patlar,
        /// gri bölge renklenir, Okti sevinir. Sonra <paramref name="done"/> (bölge açılır). Toplam ≈4 sn; girdi kapalı.
        /// </summary>
        private System.Collections.IEnumerator FogLift(RegionView v, System.Action done)
        {
            if (v == null || _world.Walker == null) { done?.Invoke(); yield break; }
            _cine = true;
            if (_hudGroup != null) _hudGroup.blocksRaycasts = false;   // görünmez düğmeler basılmasın
            _world.Walker.Steer(Vector2.zero); _world.Walker.Stop();
            var bars = new[] { Bar(true), Bar(false) };
            var c = _world.World(v.Region.X, v.Region.Z);
            var pet = _world.Walker.transform.position;
            var dir = c - pet; dir.y = 0f; dir = dir.sqrMagnitude > 0.01f ? dir.normalized : Vector3.forward;
            _cinePos = pet - dir * 7f + Vector3.up * 5.5f + Vector3.Cross(Vector3.up, dir) * 2.5f;
            _cineLook = c + Vector3.up * 1.6f;
            _world.Walker.Face(v.Region.X, v.Region.Z);
            for (var t = 0f; t < 1f; t += Time.deltaTime / 0.45f)
            {
                if (_hudGroup != null) _hudGroup.alpha = 1f - t;
                foreach (var b in bars) b.sizeDelta = new Vector2(0f, Mathf.Lerp(0f, 96f, t));
                yield return null;
            }
            if (_hudGroup != null) _hudGroup.alpha = 0f;
            yield return new WaitForSeconds(0.8f);
            // ışık patlaması + sis dağılır
            Audio.Sfx.Play(Audio.SfxKind.Chime);
            Audio.Haptics.Medium();
            var glow = GainFx.Glow(_world.transform, GainFx.StoneColor, 1.2f, false);
            glow.position = c + Vector3.up * 1.2f;
            var sp = App.Stage.Camera.WorldToScreenPoint(c + Vector3.up * 1.5f);
            StarSparkles.Around(Root, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.2f, 0.26f), 14, 23);
            _world.Fog.TryGetValue(v.Region.Id, out var fog);
            var clouds = new List<(Transform T, Vector3 P, Vector3 S)>();
            if (fog != null) foreach (Transform cl in fog) clouds.Add((cl, cl.localPosition, cl.localScale));
            var region = _world.Regions.TryGetValue(v.Region.Id, out var rt) ? rt : null;
            var mpb = new MaterialPropertyBlock();
            var rends = region != null ? region.GetComponentsInChildren<Renderer>(true) : new Renderer[0];
            for (var t = 0f; t < 1f; t += Time.deltaTime / 1.6f)
            {
                var e = t * t * (3f - 2f * t);
                glow.localScale = Vector3.one * Mathf.Lerp(0.5f, v.Region.Size * 1.6f, e);
                foreach (var (cl, p0, s0) in clouds)
                {
                    if (cl == null) continue;
                    var outw = p0 - fog.InverseTransformPoint(c); outw.y = 0f;
                    cl.localPosition = p0 + outw.normalized * e * v.Region.Size * 0.8f + Vector3.up * e * 4f;
                    cl.localScale = s0 * Mathf.Lerp(1f, 0.05f, e);
                }
                // gri bölge renklenir
                mpb.SetColor("_BaseColor", Color.Lerp(new Color(0.62f, 0.64f, 0.72f), Color.white, e));
                foreach (var r in rends) if (r != null) r.SetPropertyBlock(mpb);
                if (t > 0.35f && t - Time.deltaTime / 1.6f <= 0.35f) { _world.Walker.Cheer(); Audio.Sfx.Play(Audio.SfxKind.Success); }
                yield return null;
            }
            if (fog != null) Destroy(fog.gameObject);
            for (var t = 0f; t < 1f; t += Time.deltaTime / 0.5f) { glow.localScale *= 0.92f; yield return null; }
            Destroy(glow.gameObject);
            yield return new WaitForSeconds(0.5f);
            for (var t = 0f; t < 1f; t += Time.deltaTime / 0.4f)
            {
                foreach (var b in bars) b.sizeDelta = new Vector2(0f, Mathf.Lerp(96f, 0f, t));
                yield return null;
            }
            foreach (var b in bars) Destroy(b.gameObject);
            if (_hudGroup != null) { _hudGroup.alpha = 1f; _hudGroup.blocksRaycasts = true; }
            _cine = false;
            done?.Invoke();
        }

        private RectTransform Bar(bool top)
        {
            var b = Ui.Rect(Root, top ? "BarTop" : "BarBottom", new Vector2(0.5f, top ? 1f : 0f), Vector2.zero);
            b.anchorMin = new Vector2(0f, top ? 1f : 0f); b.anchorMax = new Vector2(1f, top ? 1f : 0f);
            b.pivot = new Vector2(0.5f, top ? 1f : 0f); b.anchoredPosition = Vector2.zero; b.sizeDelta = Vector2.zero;
            var img = b.gameObject.AddComponent<Image>(); img.color = Color.black; img.raycastTarget = true;
            return b;
        }

        // ------------------------------------------------------------------ dokunuş tepkileri (A1, O4; 23 Ekim 2026)
        private Button _dressBubble;
        private float _dressFor;

        private void ShowDressBubble()
        {
            if (_dressBubble == null)
            {
                _dressBubble = Candy.Round(_gLayer, Candy.White, "hoodie_soft", 118f, Vector2.zero, Vector2.zero, () =>
                {
                    TipDone(Onboarding.Wardrobe);
                    App.Stage.SetPetVisible(true);
                    App.Open(AppPage.Wardrobe);
                });
                Hover.On(_dressBubble, 6f);
            }
            _dressFor = 3.5f;
            _dressBubble.gameObject.SetActive(true);
            Bump.Play(_dressBubble.transform, 0.3f);
            UpdateDressBubble();
        }

        private void UpdateDressBubble()
        {
            if (_dressBubble == null || !_dressBubble.gameObject.activeSelf) return;
            if ((_dressFor -= Time.deltaTime) <= 0f || _overview || _world.Walker == null) { _dressBubble.gameObject.SetActive(false); return; }
            var sp = App.Stage.Camera.WorldToScreenPoint(_world.Walker.transform.position + Vector3.up * 2.6f * _world.Walker.transform.localScale.y);
            if (sp.z <= 0f) return;
            var k = Root.rect.width / Mathf.Max(1f, Screen.width);
            ((RectTransform)_dressBubble.transform).anchoredPosition = new Vector2(sp.x * k + 90f, sp.y * k);
        }

        /// <summary>Dokunma ışınına en yakın süs (ağaç, palmiye, çalı, deniz yıldızı) dürtülür; yakındaki yengeçler kaçar.</summary>
        private void PokeNear(Ray ray, float groundDist, Vector2 at)
        {
            Wobble best = null; var bestT = float.MaxValue;
            foreach (var (pos, rad, w) in _world.Reactive)
            {
                if (w == null || !w.gameObject.activeInHierarchy) continue;
                var c = _world.World(pos.x, pos.y) + Vector3.up * rad;   // gövde ortası kabaca
                var t = Vector3.Dot(c - ray.origin, ray.direction);
                if (t <= 0f || t > groundDist + rad * 2f) continue;
                var d = Vector3.Distance(ray.origin + ray.direction * t, c);
                if (d < rad * 1.1f && t < bestT) { bestT = t; best = w; }
            }
            if (best != null) best.Poke(ray.origin);
            foreach (var (pos, crab) in _world.Crabs)
                if (crab != null && Vector2.Distance(pos, at) < 2.2f) crab.Scare(at);
        }

        /// <summary>Suya dokununca halka (yürünmez).</summary>
        private void TapWater(Ray ray)
        {
            var plane = new Plane(Vector3.up, _world.transform.position);   // deniz yüzeyi: yerel y = 0
            if (!plane.Raycast(ray, out var d) || d > 220f) return;
            Ripple.Spawn(ray.GetPoint(d));
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
            // H3: bölgede bekçinin günlük sayfası (bölümü açıldıysa) — Defter'de birleşir
            var page = Logic.Story.LorePages.OnRegion(App.Data.Story, App.State.Story, App.Data.Story.ChapterFor(App.Level), v.Region.Id);
            if (page != null) Toast.Post(App.Overlay.transform, Th, T("lore.found", page.Number));
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
            // açılma (M5): kristal dönüp patlar, pet zafer hareketi yapar, pırıltı sesi; XP parçaları kristalden pete akar
            _sparkleObjs.Remove(idx);
            go.name = "sparkle_open";
            _xpFrom = go.transform.position;
            var fl = go.GetComponent<SparkleFloat>();
            if (fl != null) fl.Open(); else Destroy(go);
            if (_world.Walker != null) { _world.Walker.Face(go.transform.position.x - _world.transform.position.x, go.transform.position.z - _world.transform.position.z); _world.Walker.Cheer(); }
            Audio.Sfx.Play(Audio.SfxKind.Sparkle);
            var entry = App.Data.Collection.FirstOrDefault(e => e.Id == sp.EntryId);
            if (entry == null) return;
            var isNew = Logic.Meta.CollectionBook.Discover(App.State.Collection, entry, App.State.Counters);
            var page = Logic.Story.LorePages.OnSparkle(App.Data.Story, App.State.Story, App.Data.Story.ChapterFor(App.Level), Day);
            if (page != null) Toast.Post(App.Overlay.transform, Th, T("lore.found", page.Number));
            _toast.Say(isNew ? T("map.sparkle_new", entry.Name) : T("map.sparkle_again", entry.Name));
            App.Save();
            App.GrantXp(isNew ? 10 : 3, Logic.Economy.XpSource.Achievement);
        }

        private List<Logic.Story.SurpriseSpot> _surprises = new List<Logic.Story.SurpriseSpot>();
        private Mailbox _mailbox;
        private static bool _mailToldThisSession;

        private async void RefreshMailFlag()
        {
            await App.RefreshMail();
            if (this == null || _mailbox == null) return;
            _mailbox.Unread = App.MailUnread > 0;
            if (App.MailUnread > 0 && !_mailToldThisSession) { _mailToldThisSession = true; _toast.Say(T("mail.new", App.MailUnread)); }
        }

        /// <summary>Sürpriz bulundu (O3): ödül günde bir kez (küçük XP), kısa söz; puan ya da seri yok.</summary>
        private void CollectSurprise(GameObject go)
        {
            if (!int.TryParse(go.name.Substring("surprise_".Length), out var idx) || idx < 0 || idx >= _surprises.Count) return;
            var def = _surprises[idx].Def;
            var view = go.GetComponent<SurpriseView>();
            if (view != null) view.React();
            if (_world.Walker != null) { _world.Walker.Face(go.transform.position.x - _world.transform.position.x, go.transform.position.z - _world.transform.position.z); _world.Walker.Cheer(); }
            if (!Logic.Story.DailySurprises.Take(App.State.Story, Day, def.Id)) return;
            _toast.Say(def.Say);
            _xpFrom = go.transform.position + Vector3.up * 0.6f;
            App.RecordActivity("surprise_found");
            App.Save();
            App.GrantXp(def.Xp, Logic.Economy.XpSource.Achievement);
        }

        /// <summary>Test: i. sürprizin yanına ışınlan (kamera ona baksın); liste döner.</summary>
        public string DebugSurprise(int i)
        {
            if (i >= 0 && i < _surprises.Count && _world.Walker != null)
            {
                var s = _surprises[i];
                var w = _terrain.NearestWalkable(s.X - 3f, s.Z - 3f);
                if (!float.IsNaN(w.x)) { _world.Walker.Teleport(w.x, w.z, 45f); _camYaw = Mathf.Atan2(s.X - w.x, s.Z - w.z) * Mathf.Rad2Deg; }
            }
            return string.Join(", ", _surprises.Select((s, k) => k + ":" + s.Def.Kind + "@" + s.X.ToString("0") + "," + s.Z.ToString("0")));
        }

        /// <summary>Test: pete dokunmuş gibi (A1 tepki + giydir baloncuğu).</summary>
        public string DebugPetTap()
        {
            if (_world.Walker == null) return "pet yok";
            var r = Logic.Story.OktiReactions.Next(App.State.Story);
            _world.Walker.React(r);
            ShowDressBubble();
            return r;
        }

        /// <summary>Test: posta kutusunun önüne ışınlan.</summary>
        public void DebugMailbox()
        {
            if (_mailbox == null || _world.Walker == null) return;
            var p = _world.Local(_mailbox.transform.position);
            var w = _terrain.NearestWalkable(p.x + 2.5f, p.y + 2.5f);
            if (float.IsNaN(w.x)) return;
            _world.Walker.Teleport(w.x, w.z, 0f);
            _camYaw = Mathf.Atan2(p.x - w.x, p.y - w.z) * Mathf.Rad2Deg;
        }

        /// <summary>Hata ayıklama/test: kamera modunu değiştir, ada üzerinde bir noktaya yürü.</summary>
        public void DebugToggle() => ToggleMode();
        public void DebugWalk(float x, float z) => GoTo(x, z, null);
        /// <summary>Test görüntüsü: peti (x, z) noktasına koy, kamerayı <paramref name="yaw"/> yönüne çevir.</summary>
        public void DebugTeleport(float x, float z, float yaw)
        {
            if (_world.Walker == null) return;
            _world.Walker.Teleport(x, z, yaw);
            _camYaw = yaw;
        }
        public string DebugPetScreen()
        {
            if (_world.Walker == null) return "yok";
            var sp = App.Stage.Camera.WorldToScreenPoint(_world.Walker.transform.position + Vector3.up * 0.7f);
            return $"{sp.x:0} {sp.y:0} {Screen.width} {Screen.height}";
        }

        /// <summary>Ekrandan çıkarken (pencere açıldı, bölgeye girildi) petin yerini hatırla.</summary>
        private void OnDisable()
        {
            if (App == null || _world == null || _world.Walker == null) return;
            var p = _world.Walker.Position;
            App.MapSpot = new Core.MapSpot(p.x, p.y, _world.Walker.Heading, _camYaw);
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
