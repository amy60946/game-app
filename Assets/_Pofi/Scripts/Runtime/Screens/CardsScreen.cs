using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Cards;
using Pofi.Logic.Core;
using Pofi.Logic.Data;
using Pofi.Logic.Economy;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Oyun Kulübesi (M8, FR-CARD-1..4): Renk Eşle, Domino, Kule — bir bot pete karşı.
    /// Kurallar/botlar <c>Pofi.Logic.Cards</c>'ta; zorluk oyun başına uyarlanır (<see cref="CardSession"/>).
    /// </summary>
    public sealed class CardsScreen : ScreenBase
    {
        public static bool Available => true;

        private string _game;
        private PetSpeciesDef _rival;
        private RectTransform _board;
        private Text _status;
        private float _botDelay = -1f;
        private Action _botMove;
        private float _difficulty;
        private System.Random _rng;

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            App.Stage.AllowDrag = false;
            Picker();
        }

        private void Update()
        {
            if (_botDelay < 0f) return;
            _botDelay -= Time.deltaTime;
            if (_botDelay < 0f) { var m = _botMove; _botMove = null; m?.Invoke(); }
        }

        private void BotAfter(float seconds, Action move)
        {
            _botMove = move;
            _botDelay = seconds;
        }

        // ------------------------------------------------------------ oyun seçimi

        private void Picker()
        {
            Ui.Clear(Root);
            _botDelay = -1f;
            Header(T("cards.title"));
            Candy.Caption(Root, T("cards.pick"), 52, new Vector2(0.5f, 0.86f), new Vector2(1200f, 80f));
            for (var i = 0; i < CardSession.Games.Length; i++)
            {
                var id = CardSession.Games[i];
                var need = App.Levels.UnlockLevel(id);
                var open = App.Level >= need;
                // büyük şeker kart: üstte oyunu anlatan 3B görsel (art/scripts/ui_games.py), altta ad ve kısa açıklama
                var card = Ui.Rect(Root, id, new Vector2(0.5f, 0.45f), new Vector2(580f, 700f), new Vector2((i - 1) * 620f, 0f));
                var img = Candy.Shell(card, open ? Candy.White : new Color(0.82f, 0.84f, 0.9f));
                var thumb = Ui.ArtImage(card, "Games/" + Thumb(id), new Vector2(0.5f, 0.64f), new Vector2(540f, 420f));
                if (thumb != null && !open) thumb.color = new Color(1f, 1f, 1f, 0.45f);
                Candy.Caption(card, T("cards.game." + id), 60, new Vector2(0.5f, 0.25f), new Vector2(540f, 90f));
                Ui.Label(card, open ? T("cards.desc." + id) : T("shop.locked", TurkishSuffix.Locative(need)), Th.Font(32), Th.SubtleText,
                    new Vector2(0.5f, 0.1f), new Vector2(520f, 100f));
                var b = card.gameObject.AddComponent<Button>();
                b.targetGraphic = img;
                b.interactable = open;
                card.gameObject.AddComponent<PressBounce>();
                b.onClick.AddListener(() => Begin(id));
            }
            NavBar(AppPage.Map);
        }

        private static string Thumb(string id) => id == "card_color_match" ? "thumb_cards" : id == "card_domino" ? "thumb_domino" : "thumb_tower";

        private void Begin(string id)
        {
            _game = id;
            _rng = new System.Random(Environment.TickCount);
            _difficulty = CardSession.Difficulty(App.State, id, App.Session.AgeBand).Level;
            var others = App.Data.Pets.Where(p => p.Id != App.State.PetId).ToList();
            _rival = others[_rng.Next(others.Count)];
            Ui.Clear(Root);
            var top = Ui.Rect(Root, "Top", Vector2.zero, Vector2.zero);
            top.anchorMin = new Vector2(0f, 1f); top.anchorMax = new Vector2(1f, 1f);
            top.pivot = new Vector2(0.5f, 1f);
            top.sizeDelta = new Vector2(0f, 110f);
            top.gameObject.AddComponent<Image>().color = new Color(1f, 1f, 1f, 0.88f);
            Ui.Label(top, T("cards.game." + id), Th.Font(50), Th.Text, new Vector2(0.15f, 0.5f), new Vector2(500f, 100f), FontStyle.Bold);
            Ui.PortraitIcon(top, _rival.Id, Color.Lerp(Theme.Hex(_rival.MainColor), Color.white, 0.6f), new Vector2(0.5f, 0.5f), 100f, new Vector2(-180f, 0f));
            Ui.Label(top, T("cards.vs", _rival.Name), Th.Font(38), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(320f, 100f), FontStyle.Normal, TextAnchor.MiddleLeft, new Vector2(60f, 0f));
            Ui.Button(top, Th, "X", new Vector2(0.96f, 0.5f), new Vector2(96f, 96f), Picker, false, default, 44, false);
            _status = Ui.Label(Root, "", Th.Font(44), Color.white, new Vector2(0.5f, 0.84f), new Vector2(1000f, 70f), FontStyle.Bold);
            _status.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -4f);
            _board = Ui.Area(Root, "Board", new Vector2(0f, 0f), new Vector2(1f, 0.8f));
            switch (id)
            {
                case "card_color_match": StartColorMatch(); break;
                case "card_domino": StartDomino(); break;
                default: StartTower(); break;
            }
        }

        private void GameOver(int winner)
        {
            _botDelay = -1f;
            var won = winner == 0;
            var xpAmount = CardSession.Finish(App.State, _game, App.Session.AgeBand, won);
            var xp = App.GrantXp(xpAmount, XpSource.CardGame);
            App.RecordActivity("card_games_played");
            var root = Modal(640f, out var box, closeOutside: false);
            var title = winner < 0 ? T("cards.draw_game") : won ? T("cards.won", xp.Grant.Granted) : T("cards.lost", xp.Grant.Granted);
            Ui.Label(box, title, Th.Font(56), Th.Text, new Vector2(0.5f, 0.7f), new Vector2(880f, 240f), FontStyle.Bold);
            if (won) App.Stage.Hop();
            Ui.Button(box, Th, T("mg.again"), new Vector2(0.5f, 0.32f), new Vector2(560f, 130f), () => { Destroy(root.gameObject); Begin(_game); });
            Ui.Button(box, Th, T("common.ok"), new Vector2(0.5f, 0.1f), new Vector2(400f, 100f), Picker, false, default, 40);
        }

        // ------------------------------------------------------------ Renk Eşle

        private ColorMatchRules _cm;
        private ColorMatchState _cms;
        private ColorMatchBot _cmBot;

        private void StartColorMatch()
        {
            _cm = new ColorMatchRules();
            var opts = Logic.Profile.AgeBands.Young(App.Session.AgeBand) ? ColorMatchOptions.ForBandA : new ColorMatchOptions();
            _cms = ColorMatchRules.NewGame(opts, _rng.Next());
            _cmBot = new ColorMatchBot(_difficulty);
            DrawColorMatch();
        }

        private static Color CardCol(CardColor c)
        {
            switch (c)
            {
                case CardColor.Red: return Theme.Hex("#E8453C");
                case CardColor.Yellow: return Theme.Hex("#FFC400");
                case CardColor.Green: return Theme.Hex("#2FB55A");
                case CardColor.Blue: return Theme.Hex("#2F80ED");
                default: return Theme.Hex("#30304A");
            }
        }

        private string CardText(Card c) => c.Kind == CardKind.Number ? c.Number.ToString() : T("cards.kind." + c.Kind);

        private RectTransform CardView(Transform parent, Card c, Vector2 anchor, Vector2 size, Vector2 offset = default)
        {
            // katmanlar: beyaz kenarlı gövde → renkli iç → beyaz eğik oval → sayı (3B görünüm, art/scripts/ui_games.py)
            var rt = Ui.Rect(parent, c.ToString(), anchor, size, offset);
            var body = rt.gameObject.AddComponent<Image>();
            body.sprite = Ui.Art("Games/card_body");
            if (body.sprite == null) { body.sprite = Ui.Rounded; body.type = Image.Type.Sliced; }
            var inner = Ui.Fill(rt, "Inner").gameObject.AddComponent<Image>();
            inner.sprite = Ui.Art("Games/card_inner") ?? Ui.Rounded; inner.color = CardCol(c.Color); inner.raycastTarget = false;
            var oval = Ui.Fill(rt, "Oval").gameObject.AddComponent<Image>();
            oval.sprite = Ui.Art("Games/card_oval") ?? Ui.Rounded; oval.raycastTarget = false;
            var num = c.Kind == CardKind.Number;
            var t = Ui.Label(rt, CardText(c), Mathf.RoundToInt(size.y * (num ? 0.42f : 0.17f)), num ? CardCol(c.Color) : Theme.Hex("#30304A"),
                new Vector2(0.5f, 0.5f), size, FontStyle.Bold);
            t.raycastTarget = false;
            t.gameObject.AddComponent<Outline>().effectColor = new Color(0f, 0f, 0f, 0.55f);
            t.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -4f);
            return rt;
        }

        private void DrawColorMatch()
        {
            Ui.Clear(_board);
            var s = _cms;
            // rakibin eli
            var n = s.Hands[1].Count;
            for (var i = 0; i < n; i++)
            {
                var bx = (i - (n - 1) / 2f) * Mathf.Min(80f, 1200f / Mathf.Max(1, n));
                if (Ui.ArtImage(_board, "Games/card_back", new Vector2(0.5f, 0.9f), new Vector2(110f, 155f), new Vector2(bx, 0f), false) == null)
                    Ui.Panel(Ui.Rect(_board, "Back", new Vector2(0.5f, 0.9f), new Vector2(110f, 155f), new Vector2(bx, 0f)), Theme.Hex(_rival.MainColor), 20f).raycastTarget = false;
            }
            Ui.Label(_board, T("cards.cards_left", n), Th.Font(32), Color.white, new Vector2(0.5f, 0.78f), new Vector2(400f, 50f), FontStyle.Bold);

            // masa: açık kart + aktif renk + deste
            CardView(_board, s.Top, new Vector2(0.44f, 0.54f), new Vector2(230f, 325f)).GetComponent<Image>().raycastTarget = false;
            var active = Ui.Rect(_board, "Active", new Vector2(0.44f, 0.3f), new Vector2(240f, 60f));
            Ui.Panel(active, CardCol(s.ActiveColor), 30f).raycastTarget = false;
            Ui.Label(active, T("cards.color." + s.ActiveColor), Th.Font(32), Color.white, new Vector2(0.5f, 0.5f), new Vector2(220f, 60f), FontStyle.Bold);
            var mine = s.Current == 0 && !_cm.IsOver(s);
            var drawLabel = s.DrewThisTurn ? T("cards.pass") : T("cards.draw");
            // deste: kart arkası yığını, üstünde "Çek"/"Geç"
            var deck = Ui.Rect(_board, "Deck", new Vector2(0.6f, 0.54f), new Vector2(230f, 325f));
            for (var d = 2; d >= 0; d--)
                Ui.ArtImage(deck, "Games/card_back", new Vector2(0.5f, 0.5f), new Vector2(230f, 325f), new Vector2(d * 7f, d * 7f), false);
            var deckImg = deck.gameObject.AddComponent<Image>(); deckImg.color = new Color(1f, 1f, 1f, 0f);
            Candy.Pill(deck, Candy.Orange, drawLabel, new Vector2(0.5f, 0f), new Vector2(200f, 84f), new Vector2(0f, -20f), null, null, 38).GetComponent<Button>().interactable = false;
            var draw = deck.gameObject.AddComponent<Button>();
            draw.targetGraphic = deckImg;
            draw.onClick.AddListener(() =>
            {
                if (_cms.Current != 0) return;
                _cm.Apply(_cms, ColorMatchMove.DrawCard());
                AfterColorMatchMove();
            });
            draw.interactable = mine;
            if (mine) deck.gameObject.AddComponent<Pulse>();

            // benim elim (iki sıra)
            var hand = s.Hands[0];
            var perRow = Mathf.Max(8, hand.Count);   // yatay: tek sıra
            var w = Mathf.Min(200f, 1760f / perRow);
            for (var i = 0; i < hand.Count; i++)
            {
                var row = i / perRow;
                var col = i % perRow;
                var count = Mathf.Min(perRow, hand.Count - row * perRow);
                var x = (col - (count - 1) / 2f) * w;
                var c = hand[i];
                var playable = mine && ColorMatchRules.CanPlay(s, c);
                var ch = Mathf.Min(280f, (w - 10f) * 1.42f);
                var cv = CardView(_board, c, new Vector2(0.5f, 0.17f), new Vector2(ch / 1.42f, ch), new Vector2(x, playable ? 34f : 0f));
                if (!playable) cv.gameObject.AddComponent<CanvasGroup>().alpha = 0.55f;
                var b = cv.gameObject.AddComponent<Button>();
                b.interactable = playable;
                var idx = i;
                b.onClick.AddListener(() => PlayCard(idx));
            }
            _status.text = _cm.IsOver(s) ? "" : mine ? T("cards.your_turn") : T("cards.bot_turn", _rival.Name);
        }

        private void PlayCard(int idx)
        {
            var c = _cms.Hands[0][idx];
            if (!c.IsWild)
            {
                _cm.Apply(_cms, ColorMatchMove.Play(idx));
                AfterColorMatchMove();
                return;
            }
            var root = Modal(560f, out var box, closeOutside: false);
            Ui.Label(box, T("cards.pick_color"), Th.Font(56), Th.Text, new Vector2(0.5f, 0.82f), new Vector2(880f, 90f), FontStyle.Bold);
            var colors = new[] { CardColor.Red, CardColor.Yellow, CardColor.Green, CardColor.Blue };
            for (var i = 0; i < 4; i++)
            {
                var col = colors[i];
                var sw = Ui.Rect(box, col.ToString(), new Vector2(0.17f + i * 0.22f, 0.4f), new Vector2(180f, 180f));
                var img = Ui.Panel(sw, CardCol(col), 40f);
                var b = sw.gameObject.AddComponent<Button>();
                b.targetGraphic = img;
                sw.gameObject.AddComponent<PressBounce>();
                b.onClick.AddListener(() =>
                {
                    Destroy(root.gameObject);
                    _cm.Apply(_cms, ColorMatchMove.Play(idx, col));
                    AfterColorMatchMove();
                });
            }
        }

        private void AfterColorMatchMove()
        {
            DrawColorMatch();
            if (_cm.IsOver(_cms)) { GameOver(_cm.Winner(_cms)); return; }
            if (_cms.Current != 0) BotAfter(0.9f, BotColorMatch);
        }

        private void BotColorMatch()
        {
            if (_cm.IsOver(_cms) || _cms.Current == 0) return;
            var legal = _cm.LegalMoves(_cms);
            _cm.Apply(_cms, _cmBot.Choose(_cms, legal, _rng));
            AfterColorMatchMove();
        }

        // ------------------------------------------------------------ Domino

        private DominoRules _dm;
        private DominoState _dms;
        private DominoBot _dmBot;

        private void StartDomino()
        {
            _dm = new DominoRules();
            _dms = DominoRules.NewGame(2, _rng.Next(), Logic.Profile.AgeBands.Young(App.Session.AgeBand) ? 5 : 7);
            _dmBot = new DominoBot(_difficulty);
            DrawDomino();
            if (_dms.Current != 0) BotAfter(0.9f, BotDomino);
        }

        private RectTransform TileView(Transform parent, Tile t, Vector2 anchor, Vector2 offset, float scale, bool highlight)
        {
            var size = new Vector2(110f, 200f) * scale;
            var rt = Ui.Rect(parent, t.ToString(), anchor, size, offset);
            var hit = rt.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            // fildişi taş (yatay çizilmiş görsel 90° döndürülür), ortada çizgi; sayılar gerçek domino noktaları
            var tileSp = Ui.Art("Games/domino_tile");
            var tile = Ui.Rect(rt, "Tile", new Vector2(0.5f, 0.5f), new Vector2(size.y, size.x));
            tile.localRotation = Quaternion.Euler(0f, 0f, 90f);
            var ti = tile.gameObject.AddComponent<Image>(); ti.raycastTarget = false;
            if (tileSp != null) ti.sprite = tileSp; else { ti.sprite = Ui.Rounded; ti.type = Image.Type.Sliced; }
            ti.color = highlight ? Theme.Hex("#FFF1B8") : Color.white;
            Pips(rt, t.A, new Vector2(0.5f, 0.75f), size);
            Pips(rt, t.B, new Vector2(0.5f, 0.25f), size);
            return rt;
        }

        private static readonly Vector2[][] PipLayout =
        {
            new Vector2[0],
            new[] { Vector2.zero },
            new[] { new Vector2(-1f, 1f), new Vector2(1f, -1f) },
            new[] { new Vector2(-1f, 1f), Vector2.zero, new Vector2(1f, -1f) },
            new[] { new Vector2(-1f, 1f), new Vector2(1f, 1f), new Vector2(-1f, -1f), new Vector2(1f, -1f) },
            new[] { new Vector2(-1f, 1f), new Vector2(1f, 1f), Vector2.zero, new Vector2(-1f, -1f), new Vector2(1f, -1f) },
            new[] { new Vector2(-1f, 1f), new Vector2(1f, 1f), new Vector2(-1f, 0f), new Vector2(1f, 0f), new Vector2(-1f, -1f), new Vector2(1f, -1f) },
        };

        private static void Pips(RectTransform tile, int value, Vector2 anchor, Vector2 size)
        {
            if (value < 0 || value >= PipLayout.Length) return;
            var pip = Ui.Art("Games/domino_pip");
            var d = size.x * 0.2f;
            foreach (var p in PipLayout[value])
            {
                var rt = Ui.Rect(tile, "pip", anchor, new Vector2(d, d), new Vector2(p.x * size.x * 0.24f, p.y * size.y * 0.13f));
                var img = rt.gameObject.AddComponent<Image>(); img.raycastTarget = false;
                if (pip != null) img.sprite = pip; else { img.sprite = Ui.Rounded; img.color = new Color(0.1f, 0.1f, 0.12f); }
            }
        }

        private void DrawDomino()
        {
            Ui.Clear(_board);
            var s = _dms;
            Ui.Label(_board, T("cards.tiles_left", s.Hands[1].Count), Th.Font(38), Color.white, new Vector2(0.5f, 0.92f), new Vector2(500f, 70f), FontStyle.Bold);

            // dizi: en fazla 7 taş görünür (uçlar önemli)
            var line = s.Line.ToList();
            var show = line.Count <= 7 ? line : line.Take(3).Concat(line.Skip(line.Count - 3)).ToList();
            for (var i = 0; i < show.Count; i++)
            {
                var x = (i - (show.Count - 1) / 2f) * 160f;
                TileView(_board, show[i], new Vector2(0.5f, 0.58f), new Vector2(x, 0f), 1.15f, false).GetComponent<Image>().raycastTarget = false;
            }
            if (s.Line.Count > 0)
            {
                Candy.Caption(_board, "< " + s.LeftEnd, 56, new Vector2(0.12f, 0.58f), new Vector2(220f, 80f));
                Candy.Caption(_board, s.RightEnd + " >", 56, new Vector2(0.88f, 0.58f), new Vector2(220f, 80f));
            }

            var mine = s.Current == 0 && !_dm.IsOver(s);
            var legal = mine ? _dm.LegalMoves(s) : (IReadOnlyList<DominoMove>)new List<DominoMove>();
            var hand = s.Hands[0];
            var w = Mathf.Min(170f, 1600f / Mathf.Max(1, hand.Count));
            for (var i = 0; i < hand.Count; i++)
            {
                var idx = i;
                var moves = legal.Where(m => !m.Draw && m.HandIndex == idx).ToList();
                var tv = TileView(_board, hand[i], new Vector2(0.5f, 0.15f), new Vector2((i - (hand.Count - 1) / 2f) * w, moves.Count > 0 ? 24f : 0f), Mathf.Min(1.3f, w / 130f), moves.Count > 0);
                var b = tv.gameObject.AddComponent<Button>();
                b.interactable = moves.Count > 0;
                b.onClick.AddListener(() =>
                {
                    if (moves.Count == 1) { _dm.Apply(_dms, moves[0]); AfterDominoMove(); return; }
                    var root = Modal(420f, out var box);
                    Ui.Button(box, Th, T("cards.left"), new Vector2(0.28f, 0.5f), new Vector2(360f, 140f), () =>
                    { Destroy(root.gameObject); _dm.Apply(_dms, moves.First(m => m.End == End.Left)); AfterDominoMove(); }, true, default, 52, false);
                    Ui.Button(box, Th, T("cards.right"), new Vector2(0.72f, 0.5f), new Vector2(360f, 140f), () =>
                    { Destroy(root.gameObject); _dm.Apply(_dms, moves.First(m => m.End == End.Right)); AfterDominoMove(); }, true, default, 52, false);
                });
            }
            if (mine && legal.Count == 1 && legal[0].Draw)
            {
                var label = s.Boneyard.Count > 0 ? T("cards.draw_tile") : T("cards.pass");
                Ui.Button(_board, Th, label, new Vector2(0.85f, 0.15f), new Vector2(340f, 110f), () => { _dm.Apply(_dms, DominoMove.DrawOrPass()); AfterDominoMove(); });
            }
            _status.text = _dm.IsOver(s) ? "" : mine ? T("cards.your_turn") : T("cards.bot_turn", _rival.Name);
        }

        private void AfterDominoMove()
        {
            DrawDomino();
            if (_dm.IsOver(_dms)) { GameOver(_dm.Winner(_dms)); return; }
            if (_dms.Current != 0) BotAfter(0.9f, BotDomino);
        }

        private void BotDomino()
        {
            if (_dm.IsOver(_dms) || _dms.Current == 0) return;
            _dm.Apply(_dms, _dmBot.Choose(_dms, _dm.LegalMoves(_dms), _rng));
            AfterDominoMove();
        }

        // ------------------------------------------------------------ Kule

        private TowerRules _tw;
        private TowerState _tws;
        private TowerBot _twBot;

        private float ChildPrecision => Logic.Profile.AgeBands.Young(App.Session.AgeBand) ? 0.95f : App.Session.AgeBand == Logic.Profile.AgeBand.B ? 0.9f : 0.85f;

        private void StartTower()
        {
            _tw = new TowerRules();
            _tws = TowerRules.NewGame(12, 2, _rng.Next());
            _twBot = new TowerBot(_difficulty);
            DrawTower(-1);
            Toast.Post(App.Overlay.transform, Th, T("cards.tower_hint"));
        }

        private void DrawTower(int fallen)
        {
            Ui.Clear(_board);
            var s = _tws;
            var mine = s.Current == 0 && !_tw.IsOver(s);
            var legal = mine ? _tw.LegalMoves(s) : (IReadOnlyList<TowerMove>)new List<TowerMove>();
            var layers = s.Layers.Count;
            var h = Mathf.Min(64f, 760f / layers);
            var baseY = -400f;
            for (var l = 0; l < layers; l++)
            {
                for (var k = 0; k < 3; k++)
                {
                    if (!s.Layers[l][k]) continue;
                    var wobble = fallen >= 0 ? new Vector2(UnityEngine.Random.Range(-260f, 260f), UnityEngine.Random.Range(-200f, 0f)) * (l / (float)layers) : Vector2.zero;
                    var pos = new Vector2((k - 1) * 250f, baseY + l * h) + wobble;
                    var blk = Ui.Rect(_board, $"b{l}_{k}", new Vector2(0.5f, 0.5f), new Vector2(244f, h - 4f), pos);
                    if (fallen >= 0) blk.localRotation = Quaternion.Euler(0f, 0f, UnityEngine.Random.Range(-40f, 40f) * (l / (float)layers));
                    var move = new TowerMove(l, k);
                    var can = legal.Contains(move);
                    // tahta blok (3B görünüm, ui_games.py); çekilebilenler parlak, diğerleri gölgede
                    var img = blk.gameObject.AddComponent<Image>();
                    img.sprite = Ui.Art("Games/block_wood");
                    if (img.sprite == null) { img.sprite = Ui.Rounded; img.type = Image.Type.Sliced; }
                    img.color = can ? Color.white : new Color(0.72f, 0.66f, 0.6f);
                    if (can)
                    {
                        blk.gameObject.AddComponent<Outline>().effectColor = new Color(1f, 1f, 1f, 0.9f);
                        var b = blk.gameObject.AddComponent<Button>();
                        b.targetGraphic = img;
                        b.onClick.AddListener(() => { _tw.Precision = ChildPrecision; _tw.Apply(_tws, move); AfterTowerMove(); });
                    }
                }
            }
            _status.text = fallen >= 0 ? T("cards.tower_fell") : mine ? T("cards.your_turn") : T("cards.bot_turn", _rival.Name);
        }

        private void AfterTowerMove()
        {
            if (_tw.IsOver(_tws))
            {
                DrawTower(_tws.LoserIndex);
                BotAfter(1.2f, () => GameOver(_tw.Winner(_tws)));
                return;
            }
            DrawTower(-1);
            if (_tws.Current != 0) BotAfter(1.0f, BotTower);
        }

        private void BotTower()
        {
            if (_tw.IsOver(_tws) || _tws.Current == 0) return;
            _tw.Precision = _twBot.Precision;
            _tw.Apply(_tws, _twBot.Choose(_tws, _tw.LegalMoves(_tws), _rng));
            AfterTowerMove();
        }

        private void OnDestroy()
        {
            if (App != null && App.Stage != null) App.Stage.AllowDrag = true;
        }
    }
}
