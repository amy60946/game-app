using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Profile;
using Pofi.Logic.Runner;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Piramit Koşusu (Oyun Kulübesi, 25 Ekim 2026): Okti altın skarabenin peşinden taş yolda koşar. Kurallar ve parkur
    /// <c>Pofi.Logic.Runner</c>'da (deterministik, testli); burada 3B yol, kamera, dokunma ve arayüz.
    /// Dünya kendi kökünde (<see cref="Origin"/>), Stage kamerası kullanılır; yol 10 m'lik parçalar hâlinde önde kurulur, arkada
    /// havuza döner. Modeller art/code3d/runner (Env/rn_*); yoksa basit kutularla çizilir.
    /// Kaydır: sağ/sol şerit, yukarı zıpla, aşağı kay; dokun = zıpla. Klavye: oklar / WASD / boşluk.
    /// İlk iki koşuda her engel türünün ilk örneğinde zaman yavaşlar ve el hareketi gösterir.
    /// </summary>
    public sealed class RunnerScreen : ScreenBase
    {
        public static readonly Vector3 Origin = new Vector3(-600f, 0f, 0f);
        public const float LaneW = 2.2f, Tile = 10f, Ahead = 130f, Behind = 16f;
        /// <summary>Çekim/deneme: otomatik koşucu (PofiDebug "run auto").</summary>
        public static bool DebugAuto;
        public static RunnerScreen Current { get; private set; }

        private RunnerCourse _course;
        private RunnerRun _run;
        private Transform _world, _holder, _pet, _lead, _ground, _far;
        private Renderer[] _petRenderers = new Renderer[0];
        private readonly List<RunEvent> _events = new List<RunEvent>();
        private float _petScale = 1f, _camX, _shake, _lastHeight;
        private bool _playing, _wasJumping, _ending;
        private float _countdown, _endTimer;
        private int _seed, _spawnObs, _spawnPick, _spawnTile, _spawnDecor;
        private bool _gateSpawned;
        private readonly Dictionary<int, Transform> _pickObjs = new Dictionary<int, Transform>();
        private readonly List<(string Key, Transform T, float Z)> _live = new List<(string, Transform, float)>();
        private readonly Dictionary<string, Stack<Transform>> _pool = new Dictionary<string, Stack<Transform>>();
        private readonly List<(Transform T, float Age)> _pops = new List<(Transform, float)>();
        private readonly List<Material> _owned = new List<Material>();
        private System.Random _decorRng;

        // arayüz
        private Image _bar;
        private Text _scarabText, _bigText;
        private readonly List<Image> _hearts = new List<Image>();
        private SpeechBubble _bubble;
        private RectTransform _hand, _hud;
        private Hazard? _teach;           // şu an öğretilen engel türü (zaman yavaş)
        private bool _teachBlock;         // şerit değiştirme öğretiliyor
        private readonly HashSet<string> _taught = new HashSet<string>();
        private bool _tutorial;
        private bool _musicLow;
        private float _slowmo = 1f;

        // dokunma
        private readonly Dictionary<int, Vector2> _press = new Dictionary<int, Vector2>();
        private readonly HashSet<int> _swiped = new HashSet<int>();
        private float _lastTouch = -10f;
        private Vector2 _mousePress; private bool _mouseDown, _mouseSwiped;

        private int Played => App.State.Counters.Total("runner_played");

        protected override void Build()
        {
            Current = this;
            App.Stage.SetPetVisible(false);
            App.Stage.AllowDrag = false;
            Audio.Music.Scene(true); _musicLow = true;
            BuildWorld();
            BuildPet();
            Reset(Environment.TickCount);
            Intro();
        }

        // ------------------------------------------------------------ akış

        private string Title => T("mg.runner.title");

        private void Intro()
        {
            Ui.Clear(Root);
            var root = Modal(780f, out var box, closeOutside: false);
            ModalTitle(box, Title);
            Ui.Label(box, T("mg.runner.howto", App.State.PetName), Th.Font(40), Th.SubtleText, new Vector2(0.5f, 0.6f), new Vector2(840f, 330f));
            Ui.Button(box, Th, T("mg.start"), new Vector2(0.5f, 0.24f), new Vector2(560f, 140f), () => { Destroy(root.gameObject); Play(); },
                true, default, 52, true, GoldKit.RibbonGreenBot);
            Ui.Button(box, Th, T("mg.exit"), new Vector2(0.5f, 0.07f), new Vector2(400f, 90f), () => App.Open(AppPage.Map), false, default, 36);
        }

        private void Play()
        {
            Ui.Clear(Root);
            BuildHud();
            _tutorial = Played < 2;
            _taught.Clear();
            _countdown = 3.2f;
            _playing = true; _ending = false;
            RealAssets.Play(_pet, "idle", false);
        }

        /// <summary>Yeni parkur: dünya ve sayaçlar baştan.</summary>
        private void Reset(int seed)
        {
            _seed = seed;
            _course = new RunnerCourse(App.Session.AgeBand, seed);
            _run = new RunnerRun(_course);
            foreach (var l in _live) Put(l.Key, l.T);
            _live.Clear(); _pickObjs.Clear();
            foreach (var p in _pops) if (p.T != null) Put("rn_scarab", p.T);
            _pops.Clear();
            _spawnObs = 0; _spawnPick = 0; _spawnTile = -2; _spawnDecor = -2; _gateSpawned = false;
            _decorRng = new System.Random(seed ^ 0x5f3759);
            _camX = 0f; _wasJumping = false; _teach = null; _teachBlock = false;
            Stream();
            PlacePet(0f);
            Cam(0f, true);
        }

        private void Update()
        {
            if (_run == null) return;
            var dt = Mathf.Min(Time.deltaTime, 0.05f);
            UpdatePops(dt);
            if (_lead != null) Lead(dt);
            if (!_playing) { Cam(dt, false); return; }

            if (_countdown > 0f)
            {
                var before = Mathf.CeilToInt(_countdown - 0.2f);
                _countdown -= dt;
                var now = Mathf.CeilToInt(_countdown - 0.2f);
                if (_bigText != null)
                {
                    _bigText.text = now >= 1 ? now.ToString() : T("runner.go");
                    if (now != before) { Bump.Play(_bigText.transform, 0.35f); Audio.Sfx.Play(now >= 1 ? Audio.SfxKind.Tap : Audio.SfxKind.Whoosh); }
                }
                if (_countdown <= 0f)
                {
                    if (_bigText != null) _bigText.text = "";
                    RealAssets.Play(_pet, "run", false);
                    if (Played == 0) _bubble.Say(T("runner.first"), 3f);
                }
                Cam(dt, false);
                return;
            }

            if (_ending)
            {
                _endTimer -= dt;
                // varışta Okti kapıdan geçip yavaşlar; çıkışta yerinde durur
                if (_run.Finished) { _holder.localPosition += Vector3.forward * Mathf.Max(0f, _endTimer) * 3f * dt; }
                Cam(dt, false);
                if (_endTimer <= 0f) { _ending = false; _playing = false; Results(); }
                return;
            }

            var act = DebugAuto ? Bot() : ReadInput();
            var simDt = dt;
            Teach(ref act, ref simDt);
            _events.Clear();
            _run.Step(simDt, act, _events);
            foreach (var e in _events) OnEvent(e);
            Stream();
            PlacePet(dt);
            Cam(dt, false);
            UpdateHud();
            if (_run.Over && !_ending) EndRun();
        }

        private void OnEvent(RunEvent e)
        {
            switch (e)
            {
                case RunEvent.Scarab:
                    Audio.Sfx.Play(Audio.SfxKind.Coin);
                    Bump.Play(_scarabText.transform.parent, 0.18f);
                    break;
                case RunEvent.Scroll:
                    Audio.Sfx.Play(Audio.SfxKind.Chime);
                    _bubble.Say(T("runner.scroll"), 2.2f);
                    break;
                case RunEvent.Hit:
                    Audio.Sfx.Play(Audio.SfxKind.Pop);
                    Audio.Haptics.Light();
                    _shake = 0.35f;
                    _bubble.Say(T("runner.oops"), 1.4f);
                    break;
            }
            // toplanan nesne: büyüyüp söner
            if (e == RunEvent.Scarab || e == RunEvent.Scroll)
                foreach (var i in _run.Taken)
                    if (_pickObjs.TryGetValue(i, out var t) && t != null)
                    {
                        _pickObjs.Remove(i);
                        RemoveLive(t);
                        _pops.Add((t, 0f));
                    }
        }

        private void EndRun()
        {
            _ending = true;
            _endTimer = _run.Finished ? 1.8f : 1.2f;
            HideTeach();
            if (_run.Finished)
            {
                Audio.Sfx.Play(Audio.SfxKind.Success);
                RealAssets.Play(_pet, "happy", false);
                Confetti.Burst(App.Overlay.transform, 70, 2.4f);
            }
            else
            {
                RealAssets.Play(_pet, "idle", false);
                _bubble.Say(T("runner.out_bubble"), 2f);
            }
        }

        private void Results()
        {
            var res = _run.Result();
            var factN = RunnerTheme.FactIndex(Played, RunnerTheme.EgyptFacts);
            var xp = App.GrantXp(res.SuggestedXp, XpSource.MiniGame);
            App.RecordActivity("runner_played");
            if (_run.Finished) App.RecordActivity("runner_finished");
            App.RecordActivity("minigames_played");   // Okti'nin günlüğü (H5)
            App.State.Counters.SetMax("runner_best_m", Mathf.RoundToInt(_run.Z));
            App.Save();

            var root = Modal(900f, out var box, closeOutside: false);
            ModalTitle(box, T(_run.Finished ? "runner.finish_title" : "runner.out_title"));
            // skarabe + puan + XP
            var row = Ui.Rect(box, "Row", new Vector2(0.5f, 0.8f), new Vector2(860f, 110f));
            Ui.IconImage(row, "ui_scarab", new Vector2(0.12f, 0.5f), 96f);
            Ui.Label(row, "× " + _run.Scarabs, Th.Font(56), Th.Text, new Vector2(0.27f, 0.5f), new Vector2(200f, 100f), FontStyle.Bold);
            Ui.Label(row, T("mg.score", res.Score), Th.Font(48), Th.Text, new Vector2(0.55f, 0.5f), new Vector2(300f, 100f), FontStyle.Bold);
            Ui.Label(row, T("xp.gain", xp.Grant.Granted), Th.Font(56), Th.Primary, new Vector2(0.85f, 0.5f), new Vector2(260f, 100f), FontStyle.Bold);
            if (xp.Grant.CapReached || xp.Grant.Granted < xp.Grant.Requested)
                Ui.Label(box, T("mg.cap"), Th.Font(32), Th.SubtleText, new Vector2(0.5f, 0.69f), new Vector2(860f, 60f));
            else if (!_run.Finished)
                Ui.Label(box, T("runner.out_text"), Th.Font(34), Th.SubtleText, new Vector2(0.5f, 0.69f), new Vector2(860f, 60f));
            // bilgi kartı (papirüs bulunduysa "Papirüste yazan")
            var card = Ui.Rect(box, "Fact", new Vector2(0.5f, 0.47f), new Vector2(840f, 240f));
            var ci = card.gameObject.AddComponent<Image>(); ci.sprite = GoldKit.Capsule(GoldKit.CreamTop, GoldKit.CreamBot); ci.type = Image.Type.Sliced; ci.raycastTarget = false;
            ci.pixelsPerUnitMultiplier = 96f / 120f;
            if (_run.ScrollFound) Ui.IconImage(card, "ui_scroll", new Vector2(0.09f, 0.5f), 120f);
            var fx = _run.ScrollFound ? 0.56f : 0.5f;
            var fw = _run.ScrollFound ? 660f : 780f;
            Ui.Label(card, T(_run.ScrollFound ? "runner.fact_scroll" : "runner.fact_title"), Th.Font(34), GoldKit.CreamInk, new Vector2(fx, 0.8f), new Vector2(fw, 50f), FontStyle.Bold);
            Ui.Label(card, T("runner." + RunnerTheme.Egypt + ".fact" + factN), Th.Font(36), GoldKit.CreamInk, new Vector2(fx, 0.4f), new Vector2(fw, 150f));
            Ui.Button(box, Th, T("mg.again"), new Vector2(0.5f, 0.2f), new Vector2(560f, 130f), () =>
            {
                Destroy(root.gameObject);
                App.RecordActivity("runner_retry");
                Reset(Environment.TickCount);
                Play();
            }, true, default, 52, true, GoldKit.RibbonGreenBot);
            Ui.Button(box, Th, T("mg.exit"), new Vector2(0.5f, 0.06f), new Vector2(460f, 96f), () => App.Open(AppPage.Map), false, default, 40);
        }

        // ------------------------------------------------------------ dokunma

        private RunAction ReadInput()
        {
            if (Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.A)) return RunAction.Left;
            if (Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.D)) return RunAction.Right;
            if (Input.GetKeyDown(KeyCode.UpArrow) || Input.GetKeyDown(KeyCode.W) || Input.GetKeyDown(KeyCode.Space)) return RunAction.Jump;
            if (Input.GetKeyDown(KeyCode.DownArrow) || Input.GetKeyDown(KeyCode.S)) return RunAction.Slide;
            var thresh = Mathf.Max(24f, Screen.height * 0.045f);
            var act = RunAction.None;
            if (Input.touchCount > 0)
            {
                _lastTouch = Time.unscaledTime;
                for (var i = 0; i < Input.touchCount; i++)
                {
                    var t = Input.GetTouch(i);
                    switch (t.phase)
                    {
                        case TouchPhase.Began:
                            if (OverUi(t.fingerId)) break;
                            _press[t.fingerId] = t.position; _swiped.Remove(t.fingerId);
                            break;
                        case TouchPhase.Moved:
                        case TouchPhase.Stationary:
                            if (_press.TryGetValue(t.fingerId, out var p0) && !_swiped.Contains(t.fingerId) && (t.position - p0).magnitude > thresh)
                            { act = Dir(t.position - p0); _swiped.Add(t.fingerId); }
                            break;
                        default:
                            if (_press.TryGetValue(t.fingerId, out var p1) && !_swiped.Contains(t.fingerId))
                                act = (t.position - p1).magnitude > thresh ? Dir(t.position - p1) : RunAction.Jump;
                            _press.Remove(t.fingerId); _swiped.Remove(t.fingerId);
                            break;
                    }
                }
                return act;
            }
            if (Time.unscaledTime - _lastTouch < 0.6f) return RunAction.None;   // dokunmanın taklit fare olayları
            if (Input.GetMouseButtonDown(0) && !OverUi(-1)) { _mouseDown = true; _mouseSwiped = false; _mousePress = Input.mousePosition; }
            if (_mouseDown)
            {
                var d = (Vector2)Input.mousePosition - _mousePress;
                if (!_mouseSwiped && d.magnitude > thresh) { _mouseSwiped = true; act = Dir(d); }
                if (Input.GetMouseButtonUp(0)) { if (!_mouseSwiped) act = RunAction.Jump; _mouseDown = false; }
            }
            return act;
        }

        private static bool OverUi(int pointer) =>
            EventSystem.current != null && (pointer >= 0 ? EventSystem.current.IsPointerOverGameObject(pointer) : EventSystem.current.IsPointerOverGameObject());

        private static RunAction Dir(Vector2 d) =>
            Mathf.Abs(d.x) > Mathf.Abs(d.y) ? (d.x < 0f ? RunAction.Left : RunAction.Right) : (d.y > 0f ? RunAction.Jump : RunAction.Slide);

        /// <summary>Otomatik koşucu (çekimler): sıradaki engel sırasına göre şerit seçer, zamanında zıplar/kayar.</summary>
        private RunAction Bot()
        {
            var next = NextRow(out var row);
            if (row == null) return RunAction.None;
            var d = next - _run.Z;
            var full = row.FirstOrDefault(o => o.Lane == -1);
            if (row.Count == 1 && full.Lane == -1)
            {
                if (full.Kind == Hazard.Low && !_run.Jumping && d < _run.Speed * 0.25f + 0.6f) return RunAction.Jump;
                if (full.Kind == Hazard.High && !_run.Sliding && d < _run.Speed * 0.35f + 0.6f) return RunAction.Slide;
                return RunAction.None;
            }
            var blocked = new HashSet<int>(row.Select(o => o.Lane));
            if (!blocked.Contains(_run.TargetLane)) return RunAction.None;
            var best = Enumerable.Range(0, RunnerCourse.Lanes).Where(l => !blocked.Contains(l)).OrderBy(l => Math.Abs(l - _run.TargetLane)).First();
            return best < _run.TargetLane ? RunAction.Left : RunAction.Right;
        }

        private float NextRow(out List<Obstacle> row)
        {
            row = null;
            foreach (var o in _course.Obstacles)
                if (o.Z + RunnerRun.Depth > _run.Z)
                {
                    var z = o.Z;
                    row = _course.Obstacles.Where(x => Mathf.Abs(x.Z - z) < 0.1f).ToList();
                    return z;
                }
            return float.MaxValue;
        }

        // ------------------------------------------------------------ öğretici

        /// <summary>
        /// İlk iki koşu: her engel türünün ilk örneğine ~1 sn kala zaman yavaşlar, engelin önünde durur ve el doğru kaydırmayı
        /// gösterir; doğru hareket gelince zaman normale döner (durma mesafesi hareketin yetişeceği kadar: şerit 0,32 sn, zıplama 0,16 sn).
        /// </summary>
        private void Teach(ref RunAction act, ref float simDt)
        {
            _slowmo = 1f;
            if (!_tutorial || DebugAuto) return;
            var z = NextRow(out var row);
            if (row == null) { HideTeach(); return; }
            var d = z - _run.Z;
            var full = row.Count == 1 && row[0].Lane == -1;
            var key = full ? row[0].Kind.ToString() : "Block";
            bool Needed() => full ? (row[0].Kind == Hazard.Low ? !_run.Jumping : !_run.Sliding) : row.Any(o => o.Lane == _run.TargetLane);
            if (_teach == null && !_teachBlock)
            {
                if (_taught.Contains(key) || !Needed() || d > _run.Speed * 1.05f) return;
                _taught.Add(key);
                if (full) _teach = row[0].Kind; else _teachBlock = true;
                ShowTeach(full ? row[0].Kind : Hazard.Block, row);
            }
            // öğretirken hareket hemen işlenir (zaman donmuşken de şerit/zıplama/kayma başlasın)
            if (act != RunAction.None) { Apply(act); act = RunAction.None; }
            if (!Needed() || d < 0.4f) { HideTeach(); return; }
            var stop = RunnerRun.Depth + _run.Speed * (full ? 0.18f : 0.32f);
            _slowmo = d < stop ? 0f : 0.2f;
            simDt *= _slowmo;
        }

        /// <summary>Öğretici donmuşken hareketi hemen işle (Step dt = 0 iken de şerit/zıplama/kayma başlasın).</summary>
        private void Apply(RunAction act) => _run.Step(0.0001f, act);

        private void ShowTeach(Hazard kind, List<Obstacle> row)
        {
            string key; Vector2 dir;
            switch (kind)
            {
                case Hazard.Low: key = "runner.teach_jump"; dir = Vector2.up; break;
                case Hazard.High: key = "runner.teach_slide"; dir = Vector2.down; break;
                default:
                    key = "runner.teach_lane";
                    var free = Enumerable.Range(0, RunnerCourse.Lanes).Where(l => row.All(o => o.Lane != l)).OrderBy(l => Math.Abs(l - _run.TargetLane)).First();
                    dir = free < _run.TargetLane ? Vector2.left : Vector2.right;
                    break;
            }
            _bubble.Say(T(key), 4f);
            if (_hand != null) Destroy(_hand.gameObject);
            _hand = Ui.IconImage(_hud, "ui_hand", new Vector2(0.5f, 0.42f), 150f);
            if (_hand != null) { var sw = _hand.gameObject.AddComponent<SwipeHint>(); sw.Dir = dir; }
        }

        private void HideTeach()
        {
            _teach = null; _teachBlock = false;
            if (_hand != null) { Destroy(_hand.gameObject); _hand = null; }
        }

        // ------------------------------------------------------------ arayüz

        private void BuildHud()
        {
            _hud = Ui.Fill(Root, "Hud");
            // sol üst: skarabe sayısı + canlar
            _scarabText = GoldKit.CurrencyPill(_hud, "ui_scarab", new Vector2(0f, 1f), new Vector2(150f * GoldKit.K * 0.5f + 40f, -70f));
            _scarabText.text = "0";
            _hearts.Clear();
            for (var i = 0; i < _course.Config.Hearts; i++)
            {
                var h = Ui.IconImage(_hud, "ui_heart", new Vector2(0f, 1f), 62f, new Vector2(64f + i * 66f, -150f));
                if (h != null) _hearts.Add(h.GetComponent<Image>());
            }
            // üst orta: yol çubuğu → kapı
            var barRt = Ui.Rect(_hud, "Way", new Vector2(0.5f, 1f), new Vector2(Mathf.Min(760f, Width * 0.42f), 44f), new Vector2(0f, -64f));
            var inner = GoldKit.RimCapsule(barRt, Theme.Hex("#5B3A1A"), Theme.Hex("#3C250F"));
            _bar = Ui.Bar(inner, new Vector2(0.5f, 0.5f), Vector2.zero, new Color(0f, 0f, 0f, 0f), Theme.Hex("#FFC83D"), 18f);
            Ui.Stretch(_bar.transform.parent as RectTransform);
            Ui.IconImage(barRt, "ui_trophy", new Vector2(1f, 0.5f), 78f, new Vector2(18f, 4f));
            CloseButton(_hud, () => App.Open(AppPage.Map));
            MusicButton.Place(MusicButton.BesideClose);
            _bigText = Ui.Label(_hud, "", Th.Font(200), Color.white, new Vector2(0.5f, 0.58f), new Vector2(900f, 260f), FontStyle.Bold);
            var o = _bigText.gameObject.AddComponent<Outline>(); o.effectColor = GoldKit.RibbonBlueInk; o.effectDistance = new Vector2(5f, -5f);
            _bubble = Bubble(new Vector2(0.5f, 0.7f));
            UpdateHud();
        }

        private void UpdateHud()
        {
            if (_bar != null) Ui.SetBar(_bar, _run.Progress);
            if (_scarabText != null) _scarabText.text = _run.Scarabs.ToString();
            for (var i = 0; i < _hearts.Count; i++)
                if (_hearts[i] != null) _hearts[i].color = i < _run.Hearts ? Color.white : new Color(0.35f, 0.35f, 0.4f, 0.55f);
        }

        // ------------------------------------------------------------ dünya

        private void BuildWorld()
        {
            _world = new GameObject("RunnerWorld").transform;
            _world.position = Origin;
            // kum zemini: oyuncuyla ilerleyen geniş düzlem (yolun altında)
            _ground = GameObject.CreatePrimitive(PrimitiveType.Plane).transform;
            _ground.name = "Sand";
            _ground.SetParent(_world, false);
            _ground.localScale = new Vector3(70f, 1f, 70f);
            Destroy(_ground.GetComponent<Collider>());
            var sand = Mat(Theme.Hex("#E9C887"), 0.08f);
            var gr = _ground.GetComponent<Renderer>(); gr.sharedMaterial = sand; gr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            // uzakta piramitler ve kum tepeleri (oyuncuyla yavaşça yaklaşır)
            _far = new GameObject("Far").transform;
            _far.SetParent(_world, false);
            void FarProp(string name, Vector3 pos, float yaw, Func<Transform> fallback)
            {
                var t = RealAssets.EnvScaled(name, _far, 1f, yaw) ?? fallback();
                t.localPosition = pos;
                foreach (var r in t.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            FarProp("rn_pyramid", new Vector3(-95f, -0.2f, 230f), 20f, () => Pyramid(60f, 40f));
            FarProp("rn_pyramid", new Vector3(140f, -0.2f, 330f), -15f, () => Pyramid(70f, 46f));
            FarProp("rn_pyramid", new Vector3(-230f, -0.2f, 420f), 40f, () => Pyramid(50f, 32f));
            FarProp("rn_dune", new Vector3(60f, -0.3f, 160f), 0f, () => Dune());
            FarProp("rn_dune", new Vector3(-70f, -0.3f, 190f), 70f, () => Dune());
            // altın skarabe (kaçan rehber)
            _lead = MakeScarab(true);
            _lead.SetParent(_world, false);
        }

        private void BuildPet()
        {
            var def = App.Data.Pet(App.State.PetId);
            _holder = new GameObject("RunnerPet").transform;
            _holder.SetParent(_world, false);
            _petScale = PetModels.StageScale(App.Growth);
            if (def != null)
            {
                _pet = PetModels.Build(def, _holder, App.Growth);
                var items = App.State.Inventory.Equipped.Values.Select(App.Data.Item).Where(i => i != null).ToList();
                CosmeticModels.Apply(_pet, def, items, App.Growth);
            }
            _holder.localScale = Vector3.one * _petScale;
            _holder.localRotation = Quaternion.Euler(0f, 180f, 0f);   // model kameraya (−Z) bakar; koşu +Z
            _petRenderers = _holder.GetComponentsInChildren<Renderer>();
            if (_pet != null)
            {
                var anim = _pet.GetComponentInChildren<Animation>();
                if (anim != null && anim.GetClip("jump") != null) anim["jump"].wrapMode = WrapMode.ClampForever;
            }
        }

        private void PlacePet(float dt)
        {
            var x = (_run.LaneX - 1f) * LaneW;
            var lean = (_run.TargetLane - _run.LaneX) * 22f;
            _holder.localPosition = new Vector3(x, _run.Height, _run.Z);
            _holder.localRotation = Quaternion.Euler(_run.Sliding ? -14f : 0f, 180f - lean, lean * 0.4f);
            // kayma: yassılır (kirişin altından geçer); zıplama: havada hafif uzar
            var sq = _run.Sliding ? new Vector3(1.18f, 0.48f, 1.18f) : _run.Jumping ? new Vector3(0.94f, 1.08f, 0.94f) : Vector3.one;
            _holder.localScale = Vector3.Lerp(_holder.localScale, sq * _petScale, dt <= 0f ? 1f : Mathf.Min(1f, dt * 14f));
            // klip: zıplama başlayınca jump, bitince run; koşu hızına göre adım
            if (_run.Jumping && !_wasJumping) { if (!RealAssets.Play(_pet, "jump", false)) RealAssets.Play(_pet, "run", false); }
            if (!_run.Jumping && _wasJumping && !_run.Over) RealAssets.Play(_pet, "run", false);
            _wasJumping = _run.Jumping;
            var anim = _pet != null ? _pet.GetComponentInChildren<Animation>() : null;
            if (anim != null && anim.GetClip("run") != null) anim["run"].speed = Mathf.Clamp(_run.Speed / 9f, 0.75f, 1.5f) * Mathf.Max(0.15f, _slowmo);
            // çarpınca dokunulmazlık süresince yanıp söner
            var vis = !_run.Invuln || Mathf.Repeat(Time.time * 10f, 1f) > 0.35f;
            foreach (var r in _petRenderers) if (r != null) r.enabled = vis;
            if (_ground != null) _ground.localPosition = new Vector3(0f, -0.03f, _run.Z + 120f);
            if (_far != null) _far.localPosition = new Vector3(0f, 0f, _run.Z * 0.93f);
            _lastHeight = _run.Height;
        }

        private void Cam(float dt, bool snap)
        {
            var px = (_run.LaneX - 1f) * LaneW;
            _camX = snap ? px * 0.6f : Mathf.Lerp(_camX, px * 0.6f, Mathf.Min(1f, dt * 5f));
            var aspect = (float)Screen.width / Mathf.Max(1, Screen.height);
            var fov = aspect < 1.5f ? 60f : 52f;   // iPad (4:3): üç şerit sığsın
            var y = 3.3f + _lastHeight * 0.35f;
            var pos = Origin + new Vector3(_camX, y, _run.Z - 6.9f);
            var look = Origin + new Vector3(_camX * 0.75f, 1.15f + _lastHeight * 0.25f, _run.Z + 7.5f);
            if (_shake > 0f)
            {
                _shake = Mathf.Max(0f, _shake - dt);
                pos += new Vector3(Mathf.Sin(Time.time * 61f), Mathf.Sin(Time.time * 47f), 0f) * _shake * 0.25f;
            }
            var cam = App.Stage.Camera;
            cam.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(look - pos));
            cam.fieldOfView = fov;
        }

        /// <summary>Kaçan altın skarabe: Okti'nin ~11 m önünde, hafif salınarak uçar; varışta kapıdan geçip gider.</summary>
        private void Lead(float dt)
        {
            var t = Time.time;
            var z = _run.Z + 11f;
            if (_run.Finished) z = Mathf.Max(_lead.localPosition.z + dt * 14f, z);
            _lead.localPosition = new Vector3(Mathf.Sin(t * 1.3f) * 1.4f, 1.9f + Mathf.Sin(t * 3.1f) * 0.25f, z);
            _lead.localRotation = Quaternion.Euler(-12f, Mathf.Sin(t * 1.3f) * 25f, Mathf.Sin(t * 2.2f) * 10f);
        }

        /// <summary>Önde eksik olanları kur, arkada kalanları havuza döndür.</summary>
        private void Stream()
        {
            var z = _run.Z;
            // yol + yan duvarlar (10 m'lik parçalar)
            while (_spawnTile * Tile < z + Ahead && _spawnTile * Tile < _course.Config.Goal + 60f)
            {
                var tz = _spawnTile * Tile + Tile / 2f;
                Live("rn_floor", () => Floor(), new Vector3(0f, 0f, tz), 0f, tz + Tile / 2f);
                Live("rn_wall", () => Wall(), new Vector3(0f, 0f, tz), 0f, tz + Tile / 2f);
                var left = Live("rn_wall_l", () => { var w = Wall(); return w; }, new Vector3(0f, 0f, tz), 0f, tz + Tile / 2f);
                left.localScale = new Vector3(-Mathf.Abs(left.localScale.x), left.localScale.y, left.localScale.z);
                _spawnTile++;
            }
            // yol kenarı süsleri (duvarın dışında): palmiye, dikilitaş, ara sıra sfenks
            while (_spawnDecor * Tile * 2f < z + Ahead && _spawnDecor * Tile * 2f < _course.Config.Goal + 60f)
            {
                var dz = _spawnDecor * Tile * 2f + (float)_decorRng.NextDouble() * 8f;
                for (var side = -1; side <= 1; side += 2)
                {
                    var r = _decorRng.NextDouble();
                    var x = side * (7.5f + (float)_decorRng.NextDouble() * 6f);
                    if (r < 0.45) Live("rn_palm", () => Palm(), new Vector3(x, 0f, dz), (float)_decorRng.NextDouble() * 360f, dz + 4f);
                    else if (r < 0.65) Live("rn_obelisk", () => Obelisk(), new Vector3(side * 6.6f, 0f, dz), side * 90f, dz + 2f);
                    else if (r < 0.72) Live("rn_sphinx", () => Sphinx(), new Vector3(side * 10.5f, 0f, dz), side > 0 ? -90f : 90f, dz + 4f);
                }
                _spawnDecor++;
            }
            // engeller
            var obs = _course.Obstacles;
            while (_spawnObs < obs.Count && obs[_spawnObs].Z < z + Ahead)
            {
                var o = obs[_spawnObs++];
                switch (o.Kind)
                {
                    case Hazard.Block:
                        var name = o.Variant == 0 ? "rn_block" : "rn_block2";
                        Live(name, () => Block(), new Vector3((o.Lane - 1) * LaneW, 0f, o.Z), 0f, o.Z + 2f);
                        break;
                    case Hazard.Low: Live("rn_low", () => Low(), new Vector3(0f, 0f, o.Z), 0f, o.Z + 2f); break;
                    default: Live("rn_high", () => High(), new Vector3(0f, 0f, o.Z), 0f, o.Z + 2f); break;
                }
            }
            // skarabeler + papirüs
            var picks = _course.Pickups;
            while (_spawnPick < picks.Count && picks[_spawnPick].Z < z + Ahead)
            {
                var i = _spawnPick++;
                if (_run.Taken.Contains(i)) continue;
                var p = picks[i];
                var t = p.Scroll ? Live("rn_scroll", () => Scroll(), Vector3.zero, 0f, p.Z + 1f) : Live("rn_scarab", () => MakeScarab(false), Vector3.zero, 0f, p.Z + 1f);
                t.localPosition = new Vector3((p.Lane - 1) * LaneW, p.Height, p.Z);
                if (t.GetComponent<SpinAxis>() == null) t.gameObject.AddComponent<SpinAxis>().Speed = 160f;
                _pickObjs[i] = t;
            }
            // varış kapısı
            if (!_gateSpawned && _course.Config.Goal < z + Ahead + 40f)
            {
                _gateSpawned = true;
                Live("rn_gate", () => Gate(), new Vector3(0f, 0f, _course.Config.Goal + 1.5f), 0f, _course.Config.Goal + 40f);
            }
            // geride kalanlar havuza
            for (var k = _live.Count - 1; k >= 0; k--)
            {
                if (_live[k].Z > z - Behind) continue;
                Put(_live[k].Key, _live[k].T);
                _live.RemoveAt(k);
            }
            foreach (var kv in _pickObjs.Where(kv => kv.Value == null || !kv.Value.gameObject.activeSelf).ToList()) _pickObjs.Remove(kv.Key);
        }

        private Transform Live(string key, Func<Transform> fallback, Vector3 pos, float yaw, float until)
        {
            Transform t = null;
            if (_pool.TryGetValue(key, out var st) && st.Count > 0) { t = st.Pop(); t.gameObject.SetActive(true); }
            else
            {
                var asset = key == "rn_wall_l" ? "rn_wall" : key;
                t = RealAssets.EnvScaled(asset, _world, 1f) ?? fallback();
                t.name = key;
                t.SetParent(_world, false);
            }
            t.localPosition = pos;
            t.localRotation = Quaternion.Euler(0f, yaw, 0f);
            _live.Add((key, t, until));
            return t;
        }

        private void RemoveLive(Transform t)
        {
            for (var k = _live.Count - 1; k >= 0; k--) if (_live[k].T == t) { _live.RemoveAt(k); return; }
        }

        private void Put(string key, Transform t)
        {
            if (t == null) return;
            t.gameObject.SetActive(false);
            t.localScale = key == "rn_wall_l" ? t.localScale : new Vector3(Mathf.Abs(t.localScale.x), t.localScale.y, t.localScale.z);
            if (!_pool.TryGetValue(key, out var st)) _pool[key] = st = new Stack<Transform>();
            st.Push(t);
        }

        private void UpdatePops(float dt)
        {
            for (var i = _pops.Count - 1; i >= 0; i--)
            {
                var (t, age) = _pops[i];
                age += dt;
                if (t == null) { _pops.RemoveAt(i); continue; }
                if (age > 0.28f)
                {
                    t.localScale = Vector3.one;
                    Put(t.name, t);
                    _pops.RemoveAt(i);
                    continue;
                }
                t.localScale = Vector3.one * (1f + age * 4f);
                t.localPosition += Vector3.up * dt * 3f;
                _pops[i] = (t, age);
            }
        }

        // ------------------------------------------------------------ yedek modeller (rn_* yoksa)

        private Material Mat(Color c, float smooth = 0.2f)
        {
            var m = PetModels.NewMaterial(c, smooth);
            _owned.Add(m);
            return m;
        }

        private Material _stone, _stoneDark, _gold, _lapis, _leaf, _red;
        private Material Stone => _stone != null ? _stone : (_stone = Mat(Theme.Hex("#E2B978")));
        private Material StoneDark => _stoneDark != null ? _stoneDark : (_stoneDark = Mat(Theme.Hex("#C39257")));
        private Material Gold => _gold != null ? _gold : (_gold = Mat(Theme.Hex("#FFC531"), 0.85f));
        private Material Lapis => _lapis != null ? _lapis : (_lapis = Mat(Theme.Hex("#2F5FD0"), 0.6f));
        private Material Leaf => _leaf != null ? _leaf : (_leaf = Mat(Theme.Hex("#4E9A3E")));
        private Material Red => _red != null ? _red : (_red = Mat(Theme.Hex("#C8553D")));

        private Transform Root3(string name) { var t = new GameObject(name).transform; t.SetParent(_world, false); return t; }

        private static Transform Box(Transform parent, Material m, Vector3 pos, Vector3 size, PrimitiveType type = PrimitiveType.Cube)
        {
            var g = GameObject.CreatePrimitive(type);
            Destroy(g.GetComponent<Collider>());
            g.transform.SetParent(parent, false);
            g.transform.localPosition = pos;
            g.transform.localScale = size;
            g.GetComponent<Renderer>().sharedMaterial = m;
            return g.transform;
        }

        private Transform Floor()
        {
            var t = Root3("floor");
            Box(t, Stone, new Vector3(0f, -0.15f, 0f), new Vector3(7.4f, 0.3f, Tile));
            for (var l = 0; l < 2; l++) Box(t, StoneDark, new Vector3((l - 0.5f) * LaneW, 0.005f, 0f), new Vector3(0.08f, 0.01f, Tile * 0.9f));
            return t;
        }

        private Transform Wall()
        {
            var t = Root3("wall");
            Box(t, StoneDark, new Vector3(4.45f, 1.1f, 0f), new Vector3(1.5f, 2.2f, Tile));
            Box(t, Lapis, new Vector3(3.68f, 1.75f, 0f), new Vector3(0.04f, 0.25f, Tile));
            Box(t, Stone, new Vector3(4.45f, 1.6f, 0f), new Vector3(1.1f, 3.2f, 1.1f), PrimitiveType.Cylinder).localScale = new Vector3(1.1f, 1.6f, 1.1f);
            return t;
        }

        private Transform Block()
        {
            var t = Root3("block");
            Box(t, Stone, new Vector3(0f, 0.45f, 0f), new Vector3(1.9f, 0.9f, 1.2f));
            Box(t, StoneDark, new Vector3(0f, 1.25f, 0f), new Vector3(1.5f, 0.7f, 1f));
            Box(t, Lapis, new Vector3(0f, 0.6f, -0.61f), new Vector3(1.2f, 0.2f, 0.02f));
            return t;
        }

        private Transform Low()
        {
            var t = Root3("low");
            var c = Box(t, StoneDark, new Vector3(0f, 0.28f, 0f), new Vector3(0.56f, 3.5f, 0.56f), PrimitiveType.Cylinder);
            c.localRotation = Quaternion.Euler(0f, 0f, 90f);
            Box(t, Gold, new Vector3(0f, 0.28f, -0.29f), new Vector3(0.6f, 0.3f, 0.02f));
            return t;
        }

        private Transform High()
        {
            var t = Root3("high");
            for (var s = -1; s <= 1; s += 2) Box(t, Stone, new Vector3(s * 3.5f, 0.88f, 0f), new Vector3(0.7f, 1.75f, 0.7f));
            Box(t, StoneDark, new Vector3(0f, 1.45f, 0f), new Vector3(7.8f, 0.6f, 0.7f));
            Box(t, Gold, new Vector3(0f, 1.45f, -0.36f), new Vector3(0.5f, 0.5f, 0.02f), PrimitiveType.Sphere);
            return t;
        }

        private Transform Gate()
        {
            var t = Root3("gate");
            for (var s = -1; s <= 1; s += 2) Box(t, Stone, new Vector3(s * 4.6f, 3.25f, 0f), new Vector3(2.4f, 6.5f, 1.6f));
            Box(t, StoneDark, new Vector3(0f, 5.8f, 0f), new Vector3(7f, 1.2f, 1.2f));
            Box(t, Gold, new Vector3(0f, 5.8f, -0.62f), new Vector3(1.4f, 1.4f, 0.05f), PrimitiveType.Sphere);
            return t;
        }

        private Transform Palm()
        {
            var t = RealAssets.EnvFootprint("palm", _world, 4f) ?? Root3("palm");
            if (t.childCount == 0)
            {
                Box(t, StoneDark, new Vector3(0f, 2.5f, 0f), new Vector3(0.35f, 2.5f, 0.35f), PrimitiveType.Cylinder);
                Box(t, Leaf, new Vector3(0f, 5.2f, 0f), new Vector3(3f, 0.8f, 3f), PrimitiveType.Sphere);
            }
            return t;
        }

        private Transform Obelisk()
        {
            var t = Root3("obelisk");
            Box(t, Stone, new Vector3(0f, 3.2f, 0f), new Vector3(0.9f, 6.4f, 0.9f));
            Box(t, Gold, new Vector3(0f, 6.7f, 0f), new Vector3(0.7f, 0.6f, 0.7f));
            return t;
        }

        private Transform Sphinx()
        {
            var t = Root3("sphinx");
            Box(t, Stone, new Vector3(0f, 0.9f, 0f), new Vector3(2f, 1.8f, 5f));
            Box(t, Stone, new Vector3(0f, 2.4f, -2f), new Vector3(1.4f, 1.6f, 1.4f));
            Box(t, Lapis, new Vector3(0f, 2.6f, -1.9f), new Vector3(1.7f, 1.2f, 1.2f));
            return t;
        }

        private Transform Pyramid(float bas, float height)
        {
            var t = Root3("pyramid");
            for (var i = 0; i < 6; i++)
            {
                var k = 1f - i / 6f;
                Box(t, i % 2 == 0 ? Stone : StoneDark, new Vector3(0f, height * (i + 0.5f) / 6f, 0f), new Vector3(bas * k, height / 6f, bas * k));
            }
            Box(t, Gold, new Vector3(0f, height, 0f), new Vector3(bas * 0.1f, height * 0.08f, bas * 0.1f));
            return t;
        }

        private Transform Dune()
        {
            var t = Root3("dune");
            Box(t, Stone, Vector3.zero, new Vector3(30f, 4f, 20f), PrimitiveType.Sphere);
            return t;
        }

        private Transform Scroll()
        {
            var t = Root3("scroll");
            Box(t, Mat(Theme.Hex("#F3E2B5")), new Vector3(0f, 0.2f, 0f), new Vector3(0.36f, 0.35f, 0.36f), PrimitiveType.Cylinder).localRotation = Quaternion.Euler(0f, 0f, 90f);
            Box(t, Red, new Vector3(0f, 0.2f, 0f), new Vector3(0.39f, 0.06f, 0.39f), PrimitiveType.Cylinder).localRotation = Quaternion.Euler(0f, 0f, 90f);
            GainFx.Glow(t, new Color(1f, 0.9f, 0.5f), 0.7f, false).localScale = Vector3.one * 1.4f;
            return t;
        }

        private Transform MakeScarab(bool lead)
        {
            var t = RealAssets.EnvScaled("rn_scarab", _world, lead ? 2.2f : 1f);
            if (t == null)
            {
                t = Root3("scarab");
                Box(t, Gold, new Vector3(0f, 0.18f, 0f), new Vector3(0.42f, 0.24f, 0.52f), PrimitiveType.Sphere);
                Box(t, Lapis, new Vector3(0f, 0.25f, -0.2f), new Vector3(0.24f, 0.14f, 0.18f), PrimitiveType.Sphere);
                if (lead) t.localScale = Vector3.one * 2.2f;
            }
            if (lead) GainFx.Glow(t, new Color(1f, 0.85f, 0.3f), 0.8f, false).localScale = Vector3.one * 1.1f;
            foreach (var r in t.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return t;
        }

        // ------------------------------------------------------------ temizlik / ayıklama

        /// <summary>PofiDebug "run": start (tanıtımı atla) · auto 1|0 · left|right|jump|slide · state.</summary>
        public string Debug(string arg)
        {
            switch (arg)
            {
                case "start":
                    var m = Root.Find("Modal"); if (m != null) Destroy(m.gameObject);
                    Play(); _countdown = 0.01f; return "başladı";
                case "auto 1": DebugAuto = true; return "otomatik";
                case "auto 0": DebugAuto = false; return "elle";
                case "left": _run.Step(0.001f, RunAction.Left); return "sol";
                case "right": _run.Step(0.001f, RunAction.Right); return "sağ";
                case "jump": _run.Step(0.001f, RunAction.Jump); return "zıpla";
                case "slide": _run.Step(0.001f, RunAction.Slide); return "kay";
                default:
                    return $"z {_run.Z:0.0}/{_course.Config.Goal:0} hız {_run.Speed:0.0} şerit {_run.LaneX:0.00} can {_run.Hearts} skarabe {_run.Scarabs}/{_course.ScarabTotal} " +
                           $"papirüs {_run.ScrollFound} bitti {_run.Finished} çıktı {_run.Out} canlı {_live.Count} havuz {_pool.Sum(kv => kv.Value.Count)}";
            }
        }

        private void OnDestroy()
        {
            if (Current == this) Current = null;
            if (_world != null) Destroy(_world.gameObject);
            foreach (var m in _owned) if (m != null) Destroy(m);
            if (App != null && App.Stage != null) App.Stage.AllowDrag = true;
            if (_musicLow) { _musicLow = false; Audio.Music.Scene(false); }
        }
    }

    /// <summary>Öğretici el: verilen yöne kayar, başa döner (kaydırma hareketini gösterir).</summary>
    public sealed class SwipeHint : MonoBehaviour
    {
        public Vector2 Dir = Vector2.up;
        private Vector2 _start;
        private float _t;
        private void Start() => _start = ((RectTransform)transform).anchoredPosition;
        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            var k = Mathf.Repeat(_t, 1.1f) / 1.1f;
            var move = Mathf.SmoothStep(0f, 1f, Mathf.Min(1f, k * 1.4f));
            ((RectTransform)transform).anchoredPosition = _start + Dir * 220f * move;
            var g = GetComponent<Image>();
            if (g != null) g.color = new Color(1f, 1f, 1f, k < 0.85f ? 1f : (1f - k) / 0.15f);
        }
    }
}
