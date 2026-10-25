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
    /// Gezegen Koşusu (Oyun Kulübesi, 25 Ekim 2026; kullanıcı: "piramit değil gezegen konseptiyle başla"): Okti Ay'daki yolda kaçan
    /// kuyrukluyıldızın peşinden koşar, kristal toplar, gezegen kartı bulur, istasyon kapısına ulaşır. Kurallar ve parkur
    /// <c>Pofi.Logic.Runner</c>'da (deterministik, testli); burada 3B yol, kamera, dokunma ve arayüz.
    /// Dünya kendi kökünde (<see cref="Origin"/>), Stage kamerası kullanılır; yol 10 m'lik parçalar hâlinde önde kurulur, arkada
    /// havuza döner. Modeller art/code3d/runner (uzay Env/rs_*, Mısır rn_*; tema <see cref="RunnerTheme.Current"/>); yoksa basit kutularla.
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
        private Text _gemText, _bigText;
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
            foreach (var p in _pops) if (p.T != null) { p.T.localScale = Vector3.one; Put(p.T.name, p.T); }
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
                case RunEvent.Gem:
                    Audio.Sfx.Play(Audio.SfxKind.Coin);
                    Bump.Play(_gemText.transform.parent, 0.18f);
                    break;
                case RunEvent.Card:
                    Audio.Sfx.Play(Audio.SfxKind.Chime);
                    _bubble.Say(T("runner.card"), 2.2f);
                    break;
                case RunEvent.Hit:
                    Audio.Sfx.Play(Audio.SfxKind.Pop);
                    Audio.Haptics.Light();
                    _shake = 0.35f;
                    _bubble.Say(T("runner.oops"), 1.4f);
                    break;
            }
            // toplanan nesne: büyüyüp söner
            if (e == RunEvent.Gem || e == RunEvent.Card)
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
            foreach (var r in _petRenderers) if (r != null) r.enabled = true;   // son çarpmada yanıp sönerken kalmasın
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
            var theme = RunnerTheme.Current;
            var factN = RunnerTheme.FactIndex(Played, RunnerTheme.FactCount(theme));
            var xp = App.GrantXp(res.SuggestedXp, XpSource.MiniGame);
            App.RecordActivity("runner_played");
            if (_run.Finished) App.RecordActivity("runner_finished");
            App.RecordActivity("minigames_played");   // Okti'nin günlüğü (H5)
            App.State.Counters.SetMax("runner_best_m", Mathf.RoundToInt(_run.Z));
            App.Save();

            var root = Modal(900f, out var box, closeOutside: false);
            ModalTitle(box, T(_run.Finished ? "runner.finish_title" : "runner.out_title"));
            // toplanan + puan + XP
            var row = Ui.Rect(box, "Row", new Vector2(0.5f, 0.8f), new Vector2(860f, 110f));
            Ui.IconImage(row, _kit.GemIcon, new Vector2(0.12f, 0.5f), 96f);
            Ui.Label(row, "× " + _run.Gems, Th.Font(56), Th.Text, new Vector2(0.27f, 0.5f), new Vector2(200f, 100f), FontStyle.Bold);
            Ui.Label(row, T("mg.score", res.Score), Th.Font(48), Th.Text, new Vector2(0.55f, 0.5f), new Vector2(300f, 100f), FontStyle.Bold);
            Ui.Label(row, T("xp.gain", xp.Grant.Granted), Th.Font(56), Th.Primary, new Vector2(0.85f, 0.5f), new Vector2(260f, 100f), FontStyle.Bold);
            if (xp.Grant.CapReached || xp.Grant.Granted < xp.Grant.Requested)
                Ui.Label(box, T("mg.cap"), Th.Font(32), Th.SubtleText, new Vector2(0.5f, 0.69f), new Vector2(860f, 60f));
            else if (!_run.Finished)
                Ui.Label(box, T("runner.out_text"), Th.Font(34), Th.SubtleText, new Vector2(0.5f, 0.69f), new Vector2(860f, 60f));
            // bilgi kartı (kart bulunduysa "Kartta yazan")
            var card = Ui.Rect(box, "Fact", new Vector2(0.5f, 0.47f), new Vector2(840f, 240f));
            var ci = card.gameObject.AddComponent<Image>(); ci.sprite = GoldKit.Capsule(GoldKit.CreamTop, GoldKit.CreamBot); ci.type = Image.Type.Sliced; ci.raycastTarget = false;
            ci.pixelsPerUnitMultiplier = 96f / 120f;
            if (_run.CardFound) Ui.IconImage(card, _kit.CardIcon, new Vector2(0.09f, 0.5f), 120f);
            var fx = _run.CardFound ? 0.56f : 0.5f;
            var fw = _run.CardFound ? 660f : 780f;
            Ui.Label(card, T(_run.CardFound ? "runner.fact_card" : "runner.fact_title"), Th.Font(34), GoldKit.CreamInk, new Vector2(fx, 0.8f), new Vector2(fw, 50f), FontStyle.Bold);
            Ui.Label(card, T("runner." + theme + ".fact" + factN), Th.Font(36), GoldKit.CreamInk, new Vector2(fx, 0.4f), new Vector2(fw, 150f));
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
            // sol üst: toplanan sayısı + canlar
            _gemText = GoldKit.CurrencyPill(_hud, _kit.GemIcon, new Vector2(0f, 1f), new Vector2(150f * GoldKit.K * 0.5f + 40f, -70f));
            _gemText.text = "0";
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
            if (_gemText != null) _gemText.text = _run.Gems.ToString();
            for (var i = 0; i < _hearts.Count; i++)
                if (_hearts[i] != null) _hearts[i].color = i < _run.Hearts ? Color.white : new Color(0.35f, 0.35f, 0.4f, 0.55f);
        }

        // ------------------------------------------------------------ dünya

        /// <summary>
        /// Dünya kiti (RunnerTheme.Current): Env/ model adları + simgeler. Uzay (kullanıcı kararı 25 Ekim 2026, önce bu): Ay'da yürüyüş
        /// yolu, kaçan kuyrukluyıldız, kristal, gezegen kartı, istasyon kapısı (art/code3d/runner, rs_*). Mısır: rn_* (sonraki dünya).
        /// Model yoksa aynı ölçüde basit kutularla çizilir.
        /// </summary>
        private sealed class Kit
        {
            public string Floor, Wall, Block, Block2, Low, High, Gem, Card, Lead, Gate, GemIcon, CardIcon;
            public bool Space;
        }

        private static readonly Kit SpaceKit = new Kit
        {
            Floor = "rs_floor", Wall = "rs_wall", Block = "rs_block", Block2 = "rs_block2", Low = "rs_low", High = "rs_high",
            Gem = "rs_crystal", Card = "rs_card", Lead = "rs_comet", Gate = "rs_gate", GemIcon = "ui_crystal", CardIcon = "ui_card", Space = true,
        };

        private static readonly Kit EgyptKit = new Kit
        {
            Floor = "rn_floor", Wall = "rn_wall", Block = "rn_block", Block2 = "rn_block2", Low = "rn_low", High = "rn_high",
            Gem = "rn_scarab", Card = "rn_scroll", Lead = "rn_scarab", Gate = "rn_gate", GemIcon = "ui_scarab", CardIcon = "ui_scroll",
        };

        private static Kit _kit => RunnerTheme.Current == RunnerTheme.Egypt ? EgyptKit : SpaceKit;
        private string WallLeft => _kit.Wall + "_l";

        private Transform _sky;   // gök cisimleri + yıldızlar: kamerayla birlikte ilerler (hiç yaklaşmaz)
        private Color _ambSky, _ambEq, _ambGround;

        private void BuildWorld()
        {
            _world = new GameObject("RunnerWorld").transform;
            _world.position = Origin;
            // zemin: oyuncuyla ilerleyen geniş düzlem (yolun altında); uzayda leylak-gri Ay tozu, Mısır'da kum
            _ground = GameObject.CreatePrimitive(PrimitiveType.Plane).transform;
            _ground.name = "Ground";
            _ground.SetParent(_world, false);
            _ground.localScale = new Vector3(70f, 1f, 70f);
            Destroy(_ground.GetComponent<Collider>());
            var gr = _ground.GetComponent<Renderer>();
            gr.sharedMaterial = Mat(Theme.Hex(_kit.Space ? "#B9B2C8" : "#E9C887"), 0.08f);
            gr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            _far = new GameObject("Far").transform;     // uzak tepeler: çok yavaş yaklaşır
            _far.SetParent(_world, false);
            _sky = new GameObject("Sky").transform;     // gezegenler, yıldızlar
            _sky.SetParent(_world, false);
            if (_kit.Space) BuildSpaceSky(); else BuildDesertFar();
            // kaçan rehber (kuyrukluyıldız / altın skarabe)
            _lead = MakeLead();
            _lead.SetParent(_world, false);
        }

        private void FarProp(Transform parent, string name, Vector3 pos, float yaw, Func<Transform> fallback)
        {
            var t = RealAssets.EnvScaled(name, parent, 1f, yaw) ?? fallback();
            t.SetParent(parent, false);
            t.localPosition = pos;
            foreach (var r in t.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        /// <summary>Uzay göğü: lacivert → leylak geçiş, bulut yok; ışık serin; yıldızlar; halkalı gezegen ve Dünya; uzakta Ay tepeleri.</summary>
        private void BuildSpaceSky()
        {
            _ambSky = RenderSettings.ambientSkyColor; _ambEq = RenderSettings.ambientEquatorColor; _ambGround = RenderSettings.ambientGroundColor;
            App.Stage.SetSkyTones(Theme.Hex("#0E1442"), Theme.Hex("#2C2F7C"), Theme.Hex("#8C72CF"), Theme.Hex("#3B3474"), 0f, 0f);
            RenderSettings.ambientSkyColor = Theme.Hex("#9AA2E6");
            RenderSettings.ambientEquatorColor = Theme.Hex("#C2B4E2");
            RenderSettings.ambientGroundColor = Theme.Hex("#7A7298");
            // yıldızlar: önde, ufkun üstünde kubbe (kameraya dönük ışık lekeleri)
            var rng = new System.Random(7);
            for (var i = 0; i < 110; i++)
            {
                var az = ((float)rng.NextDouble() * 2f - 1f) * 85f * Mathf.Deg2Rad;
                var el = Mathf.Lerp(7f, 62f, Mathf.Pow((float)rng.NextDouble(), 0.8f)) * Mathf.Deg2Rad;
                var dir = new Vector3(Mathf.Sin(az) * Mathf.Cos(el), Mathf.Sin(el), Mathf.Cos(az) * Mathf.Cos(el));
                var warm = rng.NextDouble() < 0.25;
                var star = GainFx.Glow(_sky, warm ? new Color(1f, 0.92f, 0.7f) : new Color(0.85f, 0.92f, 1f), 0.9f, false);
                star.localPosition = dir * 420f + Vector3.up * 2f;
                star.localScale = Vector3.one * Mathf.Lerp(2.5f, 7.5f, (float)rng.NextDouble() * (float)rng.NextDouble());
            }
            FarProp(_sky, "rs_planet", new Vector3(-170f, 120f, 520f), 25f, () => Planet(32f, "#F2B36B", "#E88A5A", true));
            FarProp(_sky, "rs_earth", new Vector3(150f, 85f, 470f), -20f, () => Planet(18f, "#3E8EE0", "#5BC27A", false));
            FarProp(_far, "rs_hills", new Vector3(-75f, -0.4f, 170f), 10f, () => Hill(40f, 7f));
            FarProp(_far, "rs_hills", new Vector3(85f, -0.4f, 210f), 160f, () => Hill(46f, 9f));
            FarProp(_far, "rs_hills", new Vector3(-10f, -0.6f, 300f), 80f, () => Hill(60f, 12f));
        }

        private void BuildDesertFar()
        {
            FarProp(_far, "rn_pyramid", new Vector3(-95f, -0.2f, 230f), 20f, () => Pyramid(60f, 40f));
            FarProp(_far, "rn_pyramid", new Vector3(140f, -0.2f, 330f), -15f, () => Pyramid(70f, 46f));
            FarProp(_far, "rn_pyramid", new Vector3(-230f, -0.2f, 420f), 40f, () => Pyramid(50f, 32f));
            FarProp(_far, "rn_dune", new Vector3(60f, -0.3f, 160f), 0f, () => Hill(30f, 4f));
            FarProp(_far, "rn_dune", new Vector3(-70f, -0.3f, 190f), 70f, () => Hill(30f, 4f));
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
            _holder.localRotation = Quaternion.Euler(_run.Sliding ? -14f : 0f, 180f + lean, lean * 0.4f);   // geçtiği yöne döner ve yatar
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
            if (_sky != null) _sky.localPosition = new Vector3(0f, 0f, _run.Z);
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

        /// <summary>Kaçan rehber (kuyrukluyıldız): Okti'nin ~11 m önünde, hafif salınarak uçar; varışta kapıdan geçip gider.</summary>
        private void Lead(float dt)
        {
            var t = Time.time;
            var z = _run.Z + 11f;
            if (_run.Finished) z = Mathf.Max(_lead.localPosition.z + dt * 14f, z);
            _lead.localPosition = new Vector3(Mathf.Sin(t * 1.3f) * 1.4f, 2.1f + Mathf.Sin(t * 3.1f) * 0.25f, z);
            // kuyruk geriye (oyuncuya) bakar: model önü +Y/Blender → koşu yönü; hafif yalpalar
            _lead.localRotation = Quaternion.Euler(-6f, Mathf.Cos(t * 1.3f) * 14f, Mathf.Sin(t * 2.2f) * 8f);
        }

        /// <summary>Önde eksik olanları kur, arkada kalanları havuza döndür.</summary>
        private void Stream()
        {
            var z = _run.Z;
            var k = _kit;
            // yol + yan korkuluklar (10 m'lik parçalar)
            while (_spawnTile * Tile < z + Ahead && _spawnTile * Tile < _course.Config.Goal + 60f)
            {
                var tz = _spawnTile * Tile + Tile / 2f;
                Live(k.Floor, () => Floor(), new Vector3(0f, 0f, tz), 0f, tz + Tile / 2f);
                Live(k.Wall, () => Wall(), new Vector3(0f, 0f, tz), 0f, tz + Tile / 2f);
                var left = Live(WallLeft, () => Wall(), new Vector3(0f, 0f, tz), 0f, tz + Tile / 2f);
                left.localScale = new Vector3(-Mathf.Abs(left.localScale.x), left.localScale.y, left.localScale.z);
                _spawnTile++;
            }
            // yol kenarı süsleri (korkuluğun dışında)
            while (_spawnDecor * Tile * 2f < z + Ahead && _spawnDecor * Tile * 2f < _course.Config.Goal + 60f)
            {
                var dz = _spawnDecor * Tile * 2f + (float)_decorRng.NextDouble() * 8f;
                for (var side = -1; side <= 1; side += 2)
                {
                    var r = _decorRng.NextDouble();
                    var x = side * (8f + (float)_decorRng.NextDouble() * 7f);
                    var face = side > 0 ? -90f : 90f;   // yola dönük
                    if (k.Space)
                    {
                        if (r < 0.22) Live("rs_dome", () => Dome(), new Vector3(side * 12.5f, 0f, dz), face, dz + 6f);
                        else if (r < 0.36) Live("rs_rocket", () => Rocket(), new Vector3(side * 13f, 0f, dz), (float)_decorRng.NextDouble() * 360f, dz + 4f);
                        else if (r < 0.56) Live("rs_dish", () => Dish(), new Vector3(side * 8.5f, 0f, dz), face + 30f * side, dz + 3f);
                        else if (r < 0.8) Live("rs_crater", () => Crater(), new Vector3(x, 0f, dz), (float)_decorRng.NextDouble() * 360f, dz + 10f);
                    }
                    else
                    {
                        if (r < 0.45) Live("rn_palm", () => Palm(), new Vector3(x, 0f, dz), (float)_decorRng.NextDouble() * 360f, dz + 4f);
                        else if (r < 0.65) Live("rn_obelisk", () => Obelisk(), new Vector3(side * 6.6f, 0f, dz), side * 90f, dz + 2f);
                        else if (r < 0.72) Live("rn_sphinx", () => Sphinx(), new Vector3(side * 10.5f, 0f, dz), face, dz + 4f);
                    }
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
                        Live(o.Variant == 0 ? k.Block : k.Block2, () => Block(o.Variant), new Vector3((o.Lane - 1) * LaneW, 0f, o.Z), 0f, o.Z + 2f);
                        break;
                    case Hazard.Low: Live(k.Low, () => Low(), new Vector3(0f, 0f, o.Z), 0f, o.Z + 2f); break;
                    default: Live(k.High, () => High(), new Vector3(0f, 0f, o.Z), 0f, o.Z + 2f); break;
                }
            }
            // toplanacaklar + bilgi kartı
            var picks = _course.Pickups;
            while (_spawnPick < picks.Count && picks[_spawnPick].Z < z + Ahead)
            {
                var i = _spawnPick++;
                if (_run.Taken.Contains(i)) continue;
                var p = picks[i];
                var t = p.Card ? Live(k.Card, () => CardModel(), Vector3.zero, 0f, p.Z + 1f) : Live(k.Gem, () => GemModel(), Vector3.zero, 0f, p.Z + 1f);
                t.localPosition = new Vector3((p.Lane - 1) * LaneW, p.Height, p.Z);
                if (t.GetComponent<SpinAxis>() == null) t.gameObject.AddComponent<SpinAxis>().Speed = 160f;
                _pickObjs[i] = t;
            }
            // varış kapısı
            if (!_gateSpawned && _course.Config.Goal < z + Ahead + 40f)
            {
                _gateSpawned = true;
                Live(k.Gate, () => Gate(), new Vector3(0f, 0f, _course.Config.Goal + 1.5f), 0f, _course.Config.Goal + 40f);
            }
            // geride kalanlar havuza
            for (var j = _live.Count - 1; j >= 0; j--)
            {
                if (_live[j].Z > z - Behind) continue;
                Put(_live[j].Key, _live[j].T);
                _live.RemoveAt(j);
            }
            foreach (var kv in _pickObjs.Where(kv => kv.Value == null || !kv.Value.gameObject.activeSelf).ToList()) _pickObjs.Remove(kv.Key);
        }

        private Transform Live(string key, Func<Transform> fallback, Vector3 pos, float yaw, float until)
        {
            Transform t = null;
            if (_pool.TryGetValue(key, out var st) && st.Count > 0) { t = st.Pop(); t.gameObject.SetActive(true); }
            else
            {
                var asset = key == WallLeft ? _kit.Wall : key;
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
            for (var j = _live.Count - 1; j >= 0; j--) if (_live[j].T == t) { _live.RemoveAt(j); return; }
        }

        private void Put(string key, Transform t)
        {
            if (t == null) return;
            t.gameObject.SetActive(false);
            t.localScale = key == WallLeft ? t.localScale : new Vector3(Mathf.Abs(t.localScale.x), t.localScale.y, t.localScale.z);
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

        // ------------------------------------------------------------ yedek modeller (Env/rs_* · rn_* yoksa; aynı ölçüler)

        private Material Mat(Color c, float smooth = 0.2f)
        {
            var m = PetModels.NewMaterial(c, smooth);
            _owned.Add(m);
            return m;
        }

        private readonly Dictionary<string, Material> _mats = new Dictionary<string, Material>();
        private Material M(string hex, float smooth = 0.25f)
        {
            if (_mats.TryGetValue(hex, out var m) && m != null) return m;
            return _mats[hex] = Mat(Theme.Hex(hex), smooth);
        }

        // tema renkleri: uzay (panel leylak-gri, koyu lacivert, camgöbeği şerit, mercan, sarı) · Mısır (kum taşı, lapis, altın)
        private Material Main => M(_kit.Space ? "#C9C3D9" : "#E2B978");
        private Material Dark => M(_kit.Space ? "#5D5A86" : "#C39257");
        private Material Accent => M(_kit.Space ? "#3CCBE0" : "#2F5FD0", 0.6f);
        private Material Gold => M("#FFC531", 0.85f);
        private Material Coral => M("#F07A5F", 0.4f);
        private Material Leaf => M("#4E9A3E");

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
            Box(t, Main, new Vector3(0f, -0.15f, 0f), new Vector3(7.4f, 0.3f, Tile));
            for (var l = 0; l < 2; l++) Box(t, Accent, new Vector3((l - 0.5f) * LaneW, 0.005f, 0f), new Vector3(0.1f, 0.01f, Tile * 0.92f));
            if (_kit.Space) for (var e = -1; e <= 1; e += 2) Box(t, Dark, new Vector3(e * 3.55f, 0.04f, 0f), new Vector3(0.3f, 0.08f, Tile));
            return t;
        }

        private Transform Wall()
        {
            var t = Root3("wall");
            if (_kit.Space)
            {
                Box(t, Dark, new Vector3(4.3f, 0.45f, 0f), new Vector3(0.25f, 0.9f, Tile));
                Box(t, Main, new Vector3(4.3f, 1.05f, 0f), new Vector3(0.18f, 0.12f, Tile));
                Box(t, Dark, new Vector3(4.3f, 0.7f, 0f), new Vector3(0.22f, 1.4f, 0.22f), PrimitiveType.Cylinder);
                Box(t, Gold, new Vector3(4.3f, 1.45f, 0f), new Vector3(0.3f, 0.3f, 0.3f), PrimitiveType.Sphere);
                return t;
            }
            Box(t, Dark, new Vector3(4.45f, 1.1f, 0f), new Vector3(1.5f, 2.2f, Tile));
            Box(t, Accent, new Vector3(3.68f, 1.75f, 0f), new Vector3(0.04f, 0.25f, Tile));
            return t;
        }

        private Transform Block(int variant)
        {
            var t = Root3("block");
            if (_kit.Space && variant == 0)
            {
                Box(t, Dark, new Vector3(0f, 0.8f, 0f), new Vector3(1.9f, 1.6f, 1.2f), PrimitiveType.Sphere);
                Box(t, M("#A77BFF", 0.8f), new Vector3(0.35f, 1.45f, -0.2f), new Vector3(0.35f, 0.7f, 0.35f)).localRotation = Quaternion.Euler(0f, 45f, 20f);
                Box(t, Accent, new Vector3(-0.4f, 1.3f, -0.35f), new Vector3(0.28f, 0.5f, 0.28f)).localRotation = Quaternion.Euler(0f, 45f, -25f);
                return t;
            }
            Box(t, Main, new Vector3(0f, 0.45f, 0f), new Vector3(1.9f, 0.9f, 1.2f));
            Box(t, _kit.Space ? Coral : Dark, new Vector3(0f, 1.25f, 0f), new Vector3(1.5f, 0.7f, 1f));
            Box(t, Accent, new Vector3(0f, 0.6f, -0.61f), new Vector3(1.2f, 0.2f, 0.02f));
            return t;
        }

        private Transform Low()
        {
            var t = Root3("low");
            var c = Box(t, _kit.Space ? Coral : Dark, new Vector3(0f, 0.3f, 0f), new Vector3(0.5f, 3.5f, 0.5f), PrimitiveType.Cylinder);
            c.localRotation = Quaternion.Euler(0f, 0f, 90f);
            for (var f = -2; f <= 2; f++) Box(t, Dark, new Vector3(f * 1.5f, 0.1f, 0f), new Vector3(0.25f, 0.2f, 0.6f));
            Box(t, Gold, new Vector3(0f, 0.3f, -0.27f), new Vector3(0.5f, 0.3f, 0.02f));
            return t;
        }

        private Transform High()
        {
            var t = Root3("high");
            for (var s = -1; s <= 1; s += 2) Box(t, Main, new Vector3(s * 3.5f, 0.88f, 0f), new Vector3(0.6f, 1.75f, 0.6f));
            Box(t, Dark, new Vector3(0f, 1.45f, 0f), new Vector3(7.8f, 0.6f, 0.6f));
            Box(t, _kit.Space ? Accent : Gold, new Vector3(0f, 1.45f, -0.31f), new Vector3(0.5f, 0.5f, 0.02f), PrimitiveType.Sphere);
            for (var s = -1; s <= 1; s += 2) Box(t, Gold, new Vector3(s * 2.5f, 1.82f, 0f), new Vector3(0.18f, 0.18f, 0.18f), PrimitiveType.Sphere);
            return t;
        }

        private Transform Gate()
        {
            var t = Root3("gate");
            if (_kit.Space)
            {
                for (var s = -1; s <= 1; s += 2) Box(t, Dark, new Vector3(s * 4.6f, 1.2f, 0f), new Vector3(0.8f, 2.4f, 1.2f));
                for (var i = 0; i < 20; i++)   // halka: 20 parça
                {
                    var a = i / 20f * Mathf.PI * 2f;
                    var seg = Box(t, i % 2 == 0 ? Coral : Accent, new Vector3(Mathf.Cos(a) * 4.4f, 4.6f + Mathf.Sin(a) * 4.4f, 0f), new Vector3(1.5f, 0.7f, 0.9f));
                    seg.localRotation = Quaternion.Euler(0f, 0f, a * Mathf.Rad2Deg + 90f);
                }
                GainFx.Glow(t, new Color(0.6f, 0.9f, 1f), 0.5f, false).localScale = Vector3.one * 7f;
                t.GetChild(t.childCount - 1).localPosition = new Vector3(0f, 4.6f, 0.4f);
                return t;
            }
            for (var s = -1; s <= 1; s += 2) Box(t, Main, new Vector3(s * 4.6f, 3.25f, 0f), new Vector3(2.4f, 6.5f, 1.6f));
            Box(t, Dark, new Vector3(0f, 5.8f, 0f), new Vector3(7f, 1.2f, 1.2f));
            Box(t, Gold, new Vector3(0f, 5.8f, -0.62f), new Vector3(1.4f, 1.4f, 0.05f), PrimitiveType.Sphere);
            return t;
        }

        private Transform GemModel()
        {
            var t = Root3("gem");
            var g = new GameObject("Gem").transform;
            g.SetParent(t, false);
            g.gameObject.AddComponent<MeshFilter>().sharedMesh = GainFx.GemMesh;
            var mr = g.gameObject.AddComponent<MeshRenderer>();
            var m = M(_kit.Space ? "#A77BFF" : "#FFC531", 0.9f); m.SetFloat("_Rim", 2.2f);
            mr.sharedMaterial = m; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            g.localPosition = Vector3.up * 0.25f;
            g.localScale = Vector3.one * 1.1f;
            return t;
        }

        private Transform CardModel()
        {
            var t = Root3("card");
            Box(t, Coral, new Vector3(0f, 0.32f, 0f), new Vector3(0.5f, 0.62f, 0.06f));
            Box(t, M("#2C2F7C"), new Vector3(0f, 0.32f, -0.035f), new Vector3(0.4f, 0.5f, 0.01f));
            Box(t, M("#F2B36B"), new Vector3(0f, 0.34f, -0.045f), new Vector3(0.2f, 0.2f, 0.02f), PrimitiveType.Sphere);
            GainFx.Glow(t, new Color(1f, 0.9f, 0.6f), 0.7f, false).localScale = Vector3.one * 1.4f;
            return t;
        }

        private Transform MakeLead()
        {
            var t = RealAssets.EnvScaled(_kit.Lead, _world, _kit.Space ? 1.6f : 2.2f);
            if (t == null)
            {
                t = Root3("lead");
                if (_kit.Space)
                {
                    Box(t, M("#FFE27A", 0.9f), Vector3.zero, Vector3.one * 0.7f, PrimitiveType.Sphere);
                    for (var i = 1; i <= 4; i++)   // kuyruk geriye (oyuncuya) doğru küçülür
                        Box(t, M(i % 2 == 0 ? "#FFF3C2" : "#FFD15A", 0.9f), new Vector3(0f, 0.04f * i, -0.42f * i), Vector3.one * (0.62f - i * 0.11f), PrimitiveType.Sphere);
                }
                else
                {
                    Box(t, Gold, new Vector3(0f, 0.18f, 0f), new Vector3(0.42f, 0.24f, 0.52f), PrimitiveType.Sphere);
                    t.localScale = Vector3.one * 2.2f;
                }
            }
            GainFx.Glow(t, _kit.Space ? new Color(1f, 0.92f, 0.55f) : new Color(1f, 0.85f, 0.3f), 0.85f, false).localScale = Vector3.one * (_kit.Space ? 1.8f : 1.1f);
            foreach (var r in t.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return t;
        }

        // uzay süsleri
        private Transform Dome()
        {
            var t = Root3("dome");
            Box(t, Main, Vector3.zero, new Vector3(8f, 6f, 8f), PrimitiveType.Sphere);
            Box(t, Accent, new Vector3(0f, 1.2f, -3.6f), new Vector3(1.6f, 2.2f, 1.2f));
            Box(t, Gold, new Vector3(0f, 3.4f, 0f), new Vector3(0.2f, 1.6f, 0.2f), PrimitiveType.Cylinder);
            return t;
        }

        private Transform Rocket()
        {
            var t = Root3("rocket");
            Box(t, Dark, new Vector3(0f, 0.3f, 0f), new Vector3(4f, 0.6f, 4f), PrimitiveType.Cylinder);
            Box(t, M("#F4F1FA"), new Vector3(0f, 4.2f, 0f), new Vector3(1.6f, 3.3f, 1.6f), PrimitiveType.Cylinder);
            Box(t, Coral, new Vector3(0f, 8f, 0f), new Vector3(1.6f, 2.2f, 1.6f), PrimitiveType.Sphere);
            for (var f = 0; f < 3; f++)
            {
                var a = f * 120f * Mathf.Deg2Rad;
                Box(t, Coral, new Vector3(Mathf.Cos(a) * 0.9f, 1.6f, Mathf.Sin(a) * 0.9f), new Vector3(0.15f, 1.6f, 0.9f)).localRotation = Quaternion.Euler(0f, -f * 120f, 0f);
            }
            Box(t, Accent, new Vector3(0f, 5.2f, -0.78f), new Vector3(0.6f, 0.6f, 0.1f), PrimitiveType.Sphere);
            return t;
        }

        private Transform Dish()
        {
            var t = Root3("dish");
            Box(t, Dark, new Vector3(0f, 1.2f, 0f), new Vector3(0.25f, 1.2f, 0.25f), PrimitiveType.Cylinder);
            var d = Box(t, Main, new Vector3(0f, 2.8f, 0f), new Vector3(3f, 0.5f, 3f), PrimitiveType.Sphere);
            d.localRotation = Quaternion.Euler(-35f, 0f, 0f);
            Box(t, Gold, new Vector3(0f, 3.3f, -0.6f), new Vector3(0.25f, 0.25f, 0.25f), PrimitiveType.Sphere);
            return t;
        }

        private Transform Crater()
        {
            var t = Root3("crater");
            Box(t, Dark, new Vector3(0f, -0.1f, 0f), new Vector3(9f, 0.6f, 9f), PrimitiveType.Sphere);
            Box(t, M("#A39DB8"), new Vector3(0f, 0.02f, 0f), new Vector3(6.5f, 0.1f, 6.5f), PrimitiveType.Cylinder);
            return t;
        }

        private Transform Planet(float r, string body, string band, bool ring)
        {
            var t = Root3("planet");
            Box(t, M(body, 0.3f), Vector3.zero, Vector3.one * r * 2f, PrimitiveType.Sphere);
            Box(t, M(band, 0.3f), new Vector3(0f, r * 0.15f, 0f), new Vector3(r * 2.02f, r * 0.35f, r * 2.02f), PrimitiveType.Sphere);
            if (ring)
            {
                var rg = Box(t, M("#E9D9B8", 0.3f), Vector3.zero, new Vector3(r * 4.2f, 0.4f, r * 4.2f), PrimitiveType.Cylinder);
                rg.localRotation = Quaternion.Euler(18f, 0f, 14f);
            }
            return t;
        }

        private Transform Hill(float w, float h)
        {
            var t = Root3("hill");
            Box(t, _kit.Space ? M("#A9A2BF") : Main, Vector3.zero, new Vector3(w, h, w * 0.6f), PrimitiveType.Sphere);
            return t;
        }

        // Mısır süsleri (sonraki dünya)
        private Transform Palm()
        {
            var t = RealAssets.EnvFootprint("palm", _world, 4f) ?? Root3("palm");
            if (t.childCount == 0)
            {
                Box(t, Dark, new Vector3(0f, 2.5f, 0f), new Vector3(0.35f, 2.5f, 0.35f), PrimitiveType.Cylinder);
                Box(t, Leaf, new Vector3(0f, 5.2f, 0f), new Vector3(3f, 0.8f, 3f), PrimitiveType.Sphere);
            }
            return t;
        }

        private Transform Obelisk()
        {
            var t = Root3("obelisk");
            Box(t, Main, new Vector3(0f, 3.2f, 0f), new Vector3(0.9f, 6.4f, 0.9f));
            Box(t, Gold, new Vector3(0f, 6.7f, 0f), new Vector3(0.7f, 0.6f, 0.7f));
            return t;
        }

        private Transform Sphinx()
        {
            var t = Root3("sphinx");
            Box(t, Main, new Vector3(0f, 0.9f, 0f), new Vector3(2f, 1.8f, 5f));
            Box(t, Main, new Vector3(0f, 2.4f, -2f), new Vector3(1.4f, 1.6f, 1.4f));
            Box(t, Accent, new Vector3(0f, 2.6f, -1.9f), new Vector3(1.7f, 1.2f, 1.2f));
            return t;
        }

        private Transform Pyramid(float bas, float height)
        {
            var t = Root3("pyramid");
            for (var i = 0; i < 6; i++)
            {
                var k = 1f - i / 6f;
                Box(t, i % 2 == 0 ? Main : Dark, new Vector3(0f, height * (i + 0.5f) / 6f, 0f), new Vector3(bas * k, height / 6f, bas * k));
            }
            Box(t, Gold, new Vector3(0f, height, 0f), new Vector3(bas * 0.1f, height * 0.08f, bas * 0.1f));
            return t;
        }

        // ------------------------------------------------------------ temizlik / ayıklama

        /// <summary>PofiDebug "run": start (tanıtımı atla) · auto 1|0 · left|right|jump|slide · skip M (ileri sar) · result (varışa) · state.</summary>
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
                case "result": _run.DebugAdvance(99999f); _run.Step(0.5f, RunAction.None); return "varışa";
                default:
                    if (arg.StartsWith("skip ") && float.TryParse(arg.Substring(5), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var meters))
                    { _run.DebugAdvance(meters); return "ileri " + meters; }
                    return $"z {_run.Z:0.0}/{_course.Config.Goal:0} hız {_run.Speed:0.0} şerit {_run.LaneX:0.00} can {_run.Hearts} toplanan {_run.Gems}/{_course.GemTotal} " +
                           $"kart {_run.CardFound} bitti {_run.Finished} çıktı {_run.Out} canlı {_live.Count} havuz {_pool.Sum(kv => kv.Value.Count)}";
            }
        }

        private void OnDestroy()
        {
            if (Current == this) Current = null;
            if (_world != null) Destroy(_world.gameObject);
            foreach (var m in _owned) if (m != null) Destroy(m);
            if (_kit.Space && App != null && App.Stage != null)
            {
                // uzay göğü ve serin ışık geri alınır (ada / ev gündüz)
                App.Stage.SetSky(App.Theme.Sky);
                RenderSettings.ambientSkyColor = _ambSky; RenderSettings.ambientEquatorColor = _ambEq; RenderSettings.ambientGroundColor = _ambGround;
            }
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
