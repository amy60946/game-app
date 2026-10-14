using System;
using System.Collections.Generic;
using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Fishing;
using Pofi.Logic.MiniGames;
using Pofi.Logic.Profile;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Mini oyunlar (M6, FR-MINI-1..3, 7): Ceviz Yakala, Pet'e Yardım, Yüzme/Sörf/Kayak (şeritli).
    /// Kurallar ve program <c>Pofi.Logic.MiniGames</c>'te (deterministik, testli); burada yalnızca çizim ve dokunma.
    /// Akış: tanıtım kartı → oyun → sonuç (puan, XP, günlük sınır notu) → tekrar / adaya dön.
    /// </summary>
    public sealed class MiniGameScreen : ScreenBase
    {
        public static bool Supports(string id) =>
            id == "coconut" || id == "help_pet" || id == "swim" || id == "surf" || id == "ski" || id == "fishing" || id == "cave" || id == "hike";

        private string _id;
        private RectTransform _area, _hud;
        private Text _score, _timer;
        private SpeechBubble _bubble;
        private Action<float> _tick;
        private bool _playing;

        protected override void Build()
        {
            _id = App.MiniGameId;
            App.Stage.SetPetVisible(false);
            App.Stage.AllowDrag = false;
            Intro();
        }

        private string Title => T("mg." + _id + ".title");
        private float Difficulty => AgeBandProfile.For(App.Session.AgeBand).MiniGameDifficulty;
        private Color PetColor => Theme.Hex(App.Data.Pet(App.State.PetId).MainColor);

        // ------------------------------------------------------------ akış

        private void Intro()
        {
            Ui.Clear(Root);
            var root = Modal(760f, out var box);
            Ui.Label(box, Title, Th.Font(80), Th.Text, new Vector2(0.5f, 0.84f), new Vector2(880f, 120f), FontStyle.Bold);
            var howKey = _id == "swim" || _id == "surf" || _id == "ski" ? "mg.lane.howto" : "mg." + _id + ".howto";
            Ui.Label(box, T(howKey, App.State.PetName), Th.Font(42), Th.SubtleText, new Vector2(0.5f, 0.56f), new Vector2(840f, 260f));
            Ui.Button(box, Th, T("mg.start"), new Vector2(0.5f, 0.24f), new Vector2(560f, 140f), () => { Destroy(root.gameObject); Play(); });
            Ui.Button(box, Th, T("mg.exit"), new Vector2(0.5f, 0.07f), new Vector2(400f, 90f), () => App.Open(AppPage.Map), false, default, 36);
        }

        private void Play()
        {
            Ui.Clear(Root);
            _area = Ui.Fill(Root, "Area");
            _hud = Ui.Rect(Root, "Hud", Vector2.zero, Vector2.zero);
            _hud.anchorMin = new Vector2(0f, 1f); _hud.anchorMax = new Vector2(1f, 1f);
            _hud.pivot = new Vector2(0.5f, 1f);
            _hud.sizeDelta = new Vector2(0f, 110f);
            _hud.gameObject.AddComponent<Image>().color = new Color(1f, 1f, 1f, 0.85f);
            Ui.Label(_hud, Title, Th.Font(48), Th.Text, new Vector2(0.22f, 0.5f), new Vector2(420f, 100f), FontStyle.Bold);
            _score = Ui.Label(_hud, T("mg.score", 0), Th.Font(48), Th.Text, new Vector2(0.62f, 0.5f), new Vector2(360f, 100f), FontStyle.Bold);
            _timer = Ui.Label(_hud, "", Th.Font(44), Th.SubtleText, new Vector2(0.88f, 0.5f), new Vector2(220f, 100f), FontStyle.Bold);
            _bubble = Bubble(new Vector2(0.5f, 0.72f));
            var seed = Environment.TickCount;
            switch (_id)
            {
                case "coconut": StartCoconut(seed); break;
                case "help_pet": StartHelpPet(seed); break;
                case "fishing": StartFishing(seed); break;
                case "cave": StartCave(seed); break;
                case "hike": StartHike(seed); break;
                default: StartLanes(seed); break;
            }
            _playing = true;
        }

        private void Update()
        {
            if (_playing && _tick != null) _tick(Time.deltaTime);
        }

        private void Finish(MiniGameResult res, string counter, int counterAmount)
        {
            if (!_playing) return;
            _playing = false;
            _tick = null;
            var xp = App.GrantXp(res.SuggestedXp, XpSource.MiniGame);
            if (counter != null) App.RecordActivity(counter, counterAmount);

            var root = Modal(820f, out var box);
            Ui.Label(box, T("mg.result_title"), Th.Font(84), Th.Text, new Vector2(0.5f, 0.85f), new Vector2(880f, 120f), FontStyle.Bold);
            Ui.Label(box, T("mg.score", res.Score), Th.Font(56), Th.Text, new Vector2(0.5f, 0.68f), new Vector2(880f, 90f), FontStyle.Bold);
            Ui.Label(box, T("xp.gain", xp.Grant.Granted), Th.Font(64), Th.Primary, new Vector2(0.5f, 0.55f), new Vector2(880f, 100f), FontStyle.Bold);
            if (xp.Grant.CapReached || xp.Grant.Granted < xp.Grant.Requested)
                Ui.Label(box, T("mg.cap"), Th.Font(36), Th.SubtleText, new Vector2(0.5f, 0.43f), new Vector2(860f, 90f));
            Ui.Button(box, Th, T("mg.again"), new Vector2(0.5f, 0.26f), new Vector2(560f, 130f), () => { Destroy(root.gameObject); Play(); });
            Ui.Button(box, Th, T("mg.exit"), new Vector2(0.5f, 0.09f), new Vector2(460f, 100f), () => App.Open(AppPage.Map), false, default, 40);
        }

        private RectTransform Dot(Transform parent, Vector2 anchor, float size, Color c)
        {
            var rt = Ui.Rect(parent, "o", anchor, new Vector2(size, size));
            Ui.Panel(rt, c, size / 2f).raycastTarget = false;
            return rt;
        }

        /// <summary>Basit sahne arka planı: gökyüzü + zemin şeridi (zeminin üst sınırı ekran yüksekliğinin oranı).</summary>
        private void Backdrop(Color sky, Color ground, float groundTop)
        {
            var bg = Ui.Fill(_area, "Sky");
            bg.gameObject.AddComponent<Image>().color = sky;
            bg.GetComponent<Image>().raycastTarget = false;
            var g = Ui.Area(_area, "Ground", Vector2.zero, new Vector2(1f, groundTop));
            g.gameObject.AddComponent<Image>().color = ground;
            g.GetComponent<Image>().raycastTarget = false;
            bg.SetAsFirstSibling();
            g.SetSiblingIndex(1);
        }

        private static float PointerX01() => Mathf.Clamp01(Input.mousePosition.x / Mathf.Max(1f, Screen.width));

        // ------------------------------------------------------------ Ceviz Yakala

        private void StartCoconut(int seed)
        {
            var game = new CoconutCatch(App.Session.AgeBand, Difficulty, seed);
            Backdrop(Theme.Hex("#8FDBFF"), Theme.Hex("#F6D79A"), 0.16f);
            var basketW = App.Session.AgeBand == AgeBand.A ? 0.28f : App.Session.AgeBand == AgeBand.B ? 0.24f : 0.2f;
            const float BasketY = 0.2f;
            var basket = Ui.Rect(_area, "Basket", new Vector2(0.5f, BasketY), new Vector2(Width * basketW * 0.6f, 100f));
            basketW *= 0.6f;   // yatay ekran geniş: sepet oransal olarak daralır
            Ui.Panel(basket, PetColor, 40f).raycastTarget = false;
            var basketX = 0.5f;
            var live = new Dictionary<int, RectTransform>();
            var caught = new List<int>();
            var next = 0;
            var t = 0f;
            var score = 0;
            _tick = dt =>
            {
                t += dt;
                var ms = (int)(t * 1000f);
                if (Input.GetMouseButton(0)) basketX = Mathf.Lerp(basketX, Mathf.Clamp(PointerX01(), basketW / 2f, 1f - basketW / 2f), 1f - Mathf.Exp(-25f * dt));
                basket.anchorMin = basket.anchorMax = new Vector2(basketX, BasketY);
                while (next < game.Schedule.Count && game.Schedule[next].AtMs <= ms)
                {
                    var f = game.Schedule[next];
                    live[next] = Dot(_area, new Vector2(f.X, 1.02f), f.Golden ? 100f : 90f, f.Golden ? Theme.Hex("#FFC400") : Theme.Hex("#7A4A26"));
                    next++;
                }
                foreach (var i in new List<int>(live.Keys))
                {
                    var f = game.Schedule[i];
                    var p = (ms - f.AtMs) / (game.FallSeconds * 1000f);
                    var y = Mathf.Lerp(1.02f, BasketY, p);
                    live[i].anchorMin = live[i].anchorMax = new Vector2(f.X, y);
                    if (p >= 1f && p < 1.08f && Mathf.Abs(f.X - basketX) < basketW / 2f + 0.03f)
                    {
                        caught.Add(i);
                        score += CoconutCatch.Points(f);
                        _score.text = T("mg.score", score);
                        Destroy(live[i].gameObject);
                        live.Remove(i);
                    }
                    else if (y < -0.05f)
                    {
                        Destroy(live[i].gameObject);
                        live.Remove(i);
                    }
                }
                _timer.text = T("mg.time", Mathf.Max(0, Mathf.CeilToInt((game.DurationMs - ms) / 1000f)));
                if (ms >= game.DurationMs) Finish(game.Finish(caught), "coconuts_caught", caught.Count);
            };
        }

        // ------------------------------------------------------------ Pet'e Yardım

        private void StartHelpPet(int seed)
        {
            var game = new HelpPetSearch(App.Session.AgeBand, seed);
            Backdrop(Theme.Hex("#8FDBFF"), Theme.Hex("#9BD77F"), 0.75f);
            _timer.text = "";
            var grid = Ui.Rect(_area, "Grid", new Vector2(0.5f, 0.44f), new Vector2(1300f, 720f));
            var cellW = 1300f / game.Columns;
            var cellH = 720f / game.Rows;
            var size = Mathf.Min(cellW, cellH) - 30f;
            var done = false;
            for (var i = 0; i < game.Columns * game.Rows; i++)
            {
                var spot = i;
                var c = i % game.Columns;
                var r = i / game.Columns;
                var pos = new Vector2(-650f + cellW * (c + 0.5f), 360f - cellH * (r + 0.5f));
                var bush = Ui.Rect(grid, "Bush" + i, new Vector2(0.5f, 0.5f), new Vector2(size, size), pos);
                var img = Ui.Panel(bush, Theme.Hex("#46B85A"), size / 2.2f);
                var btn = bush.gameObject.AddComponent<Button>();
                btn.targetGraphic = img;
                bush.gameObject.AddComponent<PressBounce>();
                btn.onClick.AddListener(() =>
                {
                    if (done) return;
                    var w = game.Guess(spot);
                    _score.text = T("mg.score", Math.Max(0, game.Columns * game.Rows - game.Tries + 1));
                    switch (w)
                    {
                        case Warmth.Found:
                            done = true;
                            img.color = Theme.Hex("#FFD23F");
                            Dot(bush, new Vector2(0.5f, 0.5f), size * 0.5f, PetColor);
                            _bubble.Say(T("mg.help_pet.found"));
                            Invoke(nameof(FinishHelp), 1.2f);
                            _pendingHelp = game;
                            break;
                        case Warmth.Hot: img.color = Theme.Hex("#FF6B4A"); _bubble.Say(T("mg.help_pet.hot")); break;
                        case Warmth.Warm: img.color = Theme.Hex("#FFB347"); _bubble.Say(T("mg.help_pet.warm")); break;
                        default: img.color = Theme.Hex("#6FA8FF"); _bubble.Say(T("mg.help_pet.cold")); break;
                    }
                });
            }
            _tick = _ => { };
        }

        private HelpPetSearch _pendingHelp;

        private void FinishHelp()
        {
            if (_pendingHelp != null) Finish(_pendingHelp.Finish(), "pets_helped", 1);
            _pendingHelp = null;
        }

        // ------------------------------------------------------------ Yüzme / Sörf / Kayak

        private void StartLanes(int seed)
        {
            var game = new LaneRunner("minigame_" + _id, App.Session.AgeBand, Difficulty, seed);
            var bg = _area.gameObject.AddComponent<Image>();
            bg.color = _id == "ski" ? Theme.Hex("#EAF4FF") : _id == "surf" ? Theme.Hex("#38B6E8") : Theme.Hex("#5CCBF5");
            bg.raycastTarget = false;
            float[] laneX = { 0.36f, 0.5f, 0.64f };
            const float PlayerY = 0.2f, RowGap = 0.13f;
            var obstacleColor = _id == "ski" ? Theme.Hex("#B8C7DA") : _id == "surf" ? Color.white : Theme.Hex("#7D8796");
            var player = Dot(_area, new Vector2(laneX[1], PlayerY), 130f, PetColor);
            var lane = 1;
            var lanes = new List<int>();
            var visuals = new Dictionary<int, List<RectTransform>>();
            var shells = 0;
            var t = 0f;
            const float Lead = 3f;    // ilk satıra kadar boş satır sayısı
            _timer.text = "";
            _tick = dt =>
            {
                t += dt;
                if (Input.GetMouseButtonDown(0))
                {
                    lane = Mathf.Clamp(lane + (PointerX01() < 0.5f ? -1 : 1), 0, 2);
                }
                var px = Mathf.Lerp(player.anchorMin.x, laneX[lane], 1f - Mathf.Exp(-18f * dt));
                player.anchorMin = player.anchorMax = new Vector2(px, PlayerY);

                var pos = t * game.RowsPerSecond - Lead;   // oyuncunun bulunduğu satır (kesirli)
                // satır geçişleri
                while (lanes.Count < game.Rows.Count && pos >= lanes.Count)
                {
                    var r = lanes.Count;
                    lanes.Add(lane);
                    var item = game.Rows[r][lane];
                    if (item == RowItem.Obstacle)
                    {
                        _bubble.Say(T("mg.lane.crash"));
                        Finish(game.Simulate(lanes), _id == "swim" ? "swim_runs" : null, 1);
                        return;
                    }
                    if (item == RowItem.Shell)
                    {
                        shells++;
                        if (visuals.TryGetValue(r, out var vs)) foreach (var v in vs) if (v != null && v.name == "shell" + lane) v.gameObject.SetActive(false);
                    }
                    _score.text = T("mg.score", r / 4 + shells * 2);
                }
                if (lanes.Count >= game.Rows.Count)
                {
                    Finish(game.Simulate(lanes), _id == "swim" ? "swim_runs" : null, 1);
                    return;
                }
                // görünür satırlar
                var first = Mathf.Max(0, Mathf.FloorToInt(pos) - 2);
                var last = Mathf.Min(game.Rows.Count - 1, Mathf.CeilToInt(pos + (1f - PlayerY) / RowGap) + 1);
                for (var r = first; r <= last; r++)
                {
                    if (!visuals.TryGetValue(r, out var vs))
                    {
                        vs = new List<RectTransform>();
                        for (var l = 0; l < 3; l++)
                        {
                            var it = game.Rows[r][l];
                            if (it == RowItem.Empty) continue;
                            var v = it == RowItem.Obstacle ? Dot(_area, Vector2.zero, 140f, obstacleColor) : Dot(_area, Vector2.zero, 70f, Theme.Hex("#FFD23F"));
                            v.name = (it == RowItem.Obstacle ? "obs" : "shell") + l;
                            vs.Add(v);
                        }
                        visuals[r] = vs;
                    }
                    foreach (var v in vs)
                    {
                        var l = v.name[v.name.Length - 1] - '0';
                        var y = PlayerY + (r - pos) * RowGap;
                        v.anchorMin = v.anchorMax = new Vector2(laneX[l], y);
                    }
                }
                foreach (var r in new List<int>(visuals.Keys))
                    if (r < first)
                    {
                        foreach (var v in visuals[r]) if (v != null) Destroy(v.gameObject);
                        visuals.Remove(r);
                    }
                player.SetAsLastSibling();
                _hud.SetAsLastSibling();
            };
        }

        // ------------------------------------------------------------ Mağara keşfi

        private void StartCave(int seed)
        {
            var game = new CaveExplore(App.Session.AgeBand, seed);
            var bg = _area.gameObject.AddComponent<Image>();
            bg.color = Theme.Hex("#1B1830");
            bg.raycastTarget = false;
            var cell = Mathf.Min(1400f / game.Width, 760f / game.Height);
            var cells = new Image[game.Width * game.Height];
            _timer.text = T("mg.cave.lights", game.Lights);
            var finishing = false;
            for (var i = 0; i < cells.Length; i++)
            {
                var idx = i;
                var x = i % game.Width;
                var y = i / game.Width;
                var pos = new Vector2((x - (game.Width - 1) / 2f) * cell, ((game.Height - 1) / 2f - y) * cell - 40f);
                var rt = Ui.Rect(_area, "c" + i, new Vector2(0.5f, 0.5f), new Vector2(cell - 8f, cell - 8f), pos);
                cells[i] = Ui.Panel(rt, Theme.Hex("#2C2850"), 16f);
                var b = rt.gameObject.AddComponent<Button>();
                b.targetGraphic = cells[i];
                b.onClick.AddListener(() =>
                {
                    if (game.Done || finishing) return;
                    var found = game.Look(idx % game.Width, idx / game.Width);
                    foreach (var r in game.Revealed)
                        cells[r].color = game.Found.Contains(r) ? Theme.Hex("#3DE1FF") : Theme.Hex("#7A6A9A");
                    _bubble.Say(found > 0 ? T("mg.cave.found") : T("mg.cave.nothing"), 1.5f);
                    if (found > 0) Audio.Sfx.Play(Audio.SfxKind.Coin);
                    _score.text = T("mg.score", game.Found.Count * 3);
                    _timer.text = T("mg.cave.lights", game.Lights);
                    if (game.Done) { finishing = true; Invoke(nameof(FinishCave), 1.2f); _pendingCave = game; }
                });
            }
            _tick = _ => { };
        }

        private CaveExplore _pendingCave;

        private void FinishCave()
        {
            if (_pendingCave != null) Finish(_pendingCave.Finish(), null, 0);
            _pendingCave = null;
        }

        // ------------------------------------------------------------ Dağ yürüyüşü

        private void StartHike(int seed)
        {
            var game = new HikeRoute(App.Session.AgeBand, seed);
            var bg = _area.gameObject.AddComponent<Image>();
            bg.color = Theme.Hex("#A8D8A0");
            bg.raycastTarget = false;
            var layerH = 780f / game.Layers;
            var buttons = new Button[game.Layers, HikeRoute.Columns];
            RectTransform walker = null;
            Vector2 Pos(int l, int c) => new Vector2((c - 1) * 320f, -400f + l * layerH);
            void Refresh()
            {
                for (var l = 0; l < game.Layers; l++)
                for (var c = 0; c < HikeRoute.Columns; c++)
                {
                    var b = buttons[l, c];
                    if (b == null) continue;
                    var can = l == game.Layer + 1 && game.CanStep(c);
                    b.interactable = can;
                    var visited = l <= game.Layer && game.Path.Count > l && game.Path[l] == c;
                    b.targetGraphic.color = visited ? Th.Primary : can ? Color.white : new Color(1f, 1f, 1f, 0.45f);
                }
                walker.anchoredPosition = Pos(game.Layer, game.Column) + new Vector2(0f, 70f);
                walker.SetAsLastSibling();
                _score.text = T("mg.score", game.Collected);
            }
            for (var l = 0; l < game.Layers; l++)
            for (var c = 0; c < HikeRoute.Columns; c++)
            {
                if (l == 0 && c != 1) continue;
                var lc = l; var cc = c;
                var rt = Ui.Rect(_area, $"n{l}_{c}", new Vector2(0.5f, 0.5f), new Vector2(200f, Mathf.Min(110f, layerH - 12f)), Pos(l, c));
                var img = Ui.Panel(rt, Color.white, 40f);
                var v = game.Value[l, c];
                if (l == game.Layers - 1) Ui.Label(rt, "^", Th.Font(60), Th.Text, new Vector2(0.5f, 0.5f), rt.sizeDelta, FontStyle.Bold);
                for (var k = 0; k < v; k++)
                {
                    var berry = Ui.Rect(rt, "b" + k, new Vector2(0.5f, 0.5f), new Vector2(34f, 34f), new Vector2((k - (v - 1) / 2f) * 40f, 0f));
                    Ui.Panel(berry, k % 2 == 0 ? Theme.Hex("#E8453C") : Theme.Hex("#FF8AD8"), 17f).raycastTarget = false;
                }
                var b = rt.gameObject.AddComponent<Button>();
                b.targetGraphic = img;
                buttons[l, c] = b;
                b.onClick.AddListener(() =>
                {
                    if (lc != game.Layer + 1 || !game.Step(cc)) return;
                    if (game.Value[lc, cc] > 0) Audio.Sfx.Play(Audio.SfxKind.Coin);
                    Refresh();
                    if (game.AtSummit)
                    {
                        _bubble.Say(T("mg.hike.summit"));
                        _pendingHike = game;
                        Invoke(nameof(FinishHike), 1.2f);
                    }
                });
            }
            walker = Dot(_area, new Vector2(0.5f, 0.5f), 90f, PetColor);
            walker.anchorMin = walker.anchorMax = new Vector2(0.5f, 0.5f);
            _timer.text = "";
            Refresh();
            _tick = _ => { };
        }

        private HikeRoute _pendingHike;

        private void FinishHike()
        {
            if (_pendingHike != null) Finish(_pendingHike.Finish(), null, 0);
            _pendingHike = null;
        }

        // ------------------------------------------------------------ Balık tutma

        private void StartFishing(int seed)
        {
            const int Rounds = 3;
            var rng = new System.Random(seed);
            var bg = _area.gameObject.AddComponent<Image>();
            bg.color = Theme.Hex("#2E9BD6");
            bg.raycastTarget = false;
            var bobber = Dot(_area, new Vector2(0.5f, 0.55f), 90f, Theme.Hex("#E8453C"));
            var top = Dot(bobber, new Vector2(0.5f, 0.75f), 50f, Color.white);
            top.name = "Top";
            var round = 0;
            var caught = 0;
            var xp = 0;
            var score = 0;
            FishingRound fr = null;
            var t = 0f;
            Button action = null;
            void NextRound()
            {
                if (round >= Rounds)
                {
                    var res = new MiniGameResult { GameId = "minigame_fishing", Score = score, SuggestedXp = Math.Max(5, xp) };
                    Finish(res, "fish_caught", caught);
                    return;
                }
                round++;
                fr = null;
                _timer.text = T("mg.fishing.round", round, Rounds);
                Ui.SetText(action, T("mg.fishing.cast"));
            }
            action = Ui.Button(_area, Th, T("mg.fishing.cast"), new Vector2(0.5f, 0.16f), new Vector2(640f, 170f), () =>
            {
                if (fr == null)
                {
                    fr = new FishingRound(rng, App.Session.AgeBand, App.Level, Logic.Pet.PetCare.IsNight(App.LocalNow), App.Data.Collection);
                    t = 0f;
                    Ui.SetText(action, T("mg.fishing.pull"));
                    _bubble.Say(T("mg.fishing.wait"), 1.2f);
                    return;
                }
                var r = fr.Resolve((int)(t * 1000f));
                if (r == CatchResult.Caught && fr.Fish != null)
                {
                    caught++;
                    var isNew = Logic.Meta.CollectionBook.Discover(App.State.Collection, fr.Fish, App.State.Counters);
                    xp += FishingRound.Xp(fr.Fish, isNew);
                    score += fr.Fish.Rarity;
                    _score.text = T("mg.score", score);
                    _bubble.Say(isNew ? T("map.sparkle_new", fr.Fish.Name) : T("mg.fishing.caught", fr.Fish.Name), 2.5f);
                    App.Save();
                }
                else _bubble.Say(r == CatchResult.TooEarly ? T("mg.fishing.early") : T("mg.fishing.late"), 2f);
                NextRound();
            }, true, default, 60);
            NextRound();
            _tick = dt =>
            {
                if (fr == null) { bobber.anchoredPosition = new Vector2(0f, Mathf.Sin(Time.time * 2f) * 8f); return; }
                t += dt;
                var ms = (int)(t * 1000f);
                var biting = ms >= fr.BiteAtMs && ms <= fr.BiteAtMs + fr.WindowMs;
                bobber.anchoredPosition = biting ? new Vector2(Mathf.Sin(Time.time * 40f) * 10f, -50f) : new Vector2(0f, Mathf.Sin(Time.time * 3f) * 10f);
                if (ms > fr.BiteAtMs + fr.WindowMs + 600)
                {
                    _bubble.Say(T("mg.fishing.late"), 2f);
                    NextRound();
                }
            };
        }

        private void OnDestroy()
        {
            if (App != null && App.Stage != null) App.Stage.AllowDrag = true;
        }
    }
}
