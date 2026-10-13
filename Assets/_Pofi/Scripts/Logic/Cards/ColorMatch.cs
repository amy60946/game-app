using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Cards
{
    // "Renk Eşle": renk ya da sayı eşleştirmeli kart oyunu (UNO benzeri, özgün ad ve görsellerle).

    public enum CardColor { Red, Yellow, Green, Blue, Wild }
    public enum CardKind { Number, Skip, Reverse, DrawTwo, Wild, WildDrawFour }

    public readonly struct Card : IEquatable<Card>
    {
        public readonly CardColor Color;
        public readonly CardKind Kind;
        public readonly int Number; // yalnızca Number için 0–9

        public Card(CardColor c, CardKind k, int n = -1) { Color = c; Kind = k; Number = n; }
        public bool IsWild => Kind == CardKind.Wild || Kind == CardKind.WildDrawFour;
        public bool Equals(Card o) => Color == o.Color && Kind == o.Kind && Number == o.Number;
        public override bool Equals(object obj) => obj is Card c && Equals(c);
        public override int GetHashCode() => ((int)Color * 31 + (int)Kind) * 31 + Number;
        public override string ToString() => Kind == CardKind.Number ? $"{Color} {Number}" : $"{Color} {Kind}";
    }

    /// <summary>Yaş bandına göre kural seti: küçükler için yalnızca sayı + atla kartları.</summary>
    public sealed class ColorMatchOptions
    {
        public int Players = 2;
        public int HandSize = 7;
        public bool ActionCards = true;   // atla/yön değiştir/+2
        public bool WildCards = true;
        public static ColorMatchOptions ForBandA => new ColorMatchOptions { HandSize = 5, ActionCards = false, WildCards = true };
    }

    public readonly struct ColorMatchMove
    {
        public readonly bool Draw;           // kart çek (oynanabilir kart yoksa ya da tercihle)
        public readonly int HandIndex;
        public readonly CardColor ChosenColor; // joker için seçilen renk

        private ColorMatchMove(bool draw, int idx, CardColor chosen) { Draw = draw; HandIndex = idx; ChosenColor = chosen; }
        public static ColorMatchMove DrawCard() => new ColorMatchMove(true, -1, CardColor.Wild);
        public static ColorMatchMove Play(int idx, CardColor chosen = CardColor.Wild) => new ColorMatchMove(false, idx, chosen);
    }

    public sealed class ColorMatchState
    {
        public List<List<Card>> Hands = new List<List<Card>>();
        public List<Card> Deck = new List<Card>();
        public List<Card> Discard = new List<Card>();
        public CardColor ActiveColor;
        public int Current;
        public int Direction = 1;
        public bool DrewThisTurn;      // çektikten sonra oynayabilir ya da pas geçer
        public int WinnerIndex = -1;
        public Random Rng;

        public Card Top => Discard[Discard.Count - 1];
    }

    public sealed class ColorMatchRules : IGameRules<ColorMatchState, ColorMatchMove>
    {
        private static readonly CardColor[] Colors = { CardColor.Red, CardColor.Yellow, CardColor.Green, CardColor.Blue };

        public static List<Card> BuildDeck(ColorMatchOptions o)
        {
            var d = new List<Card>();
            foreach (var c in Colors)
            {
                d.Add(new Card(c, CardKind.Number, 0));
                for (var n = 1; n <= 9; n++) { d.Add(new Card(c, CardKind.Number, n)); d.Add(new Card(c, CardKind.Number, n)); }
                if (o.ActionCards)
                    for (var k = 0; k < 2; k++)
                    {
                        d.Add(new Card(c, CardKind.Skip)); d.Add(new Card(c, CardKind.Reverse)); d.Add(new Card(c, CardKind.DrawTwo));
                    }
            }
            if (o.WildCards)
                for (var k = 0; k < 4; k++)
                {
                    d.Add(new Card(CardColor.Wild, CardKind.Wild));
                    if (o.ActionCards) d.Add(new Card(CardColor.Wild, CardKind.WildDrawFour));
                }
            return d;
        }

        public static ColorMatchState NewGame(ColorMatchOptions o, int seed)
        {
            var s = new ColorMatchState { Rng = new Random(seed) };
            s.Deck = BuildDeck(o);
            Shuffle(s.Deck, s.Rng);
            for (var p = 0; p < o.Players; p++)
            {
                var hand = new List<Card>();
                for (var i = 0; i < o.HandSize; i++) hand.Add(Pop(s));
                s.Hands.Add(hand);
            }
            // İlk açık kart sayı kartı olsun (çocuk için sade başlangıç)
            Card first;
            do { first = Pop(s); if (first.Kind != CardKind.Number) s.Deck.Insert(0, first); } while (first.Kind != CardKind.Number);
            s.Discard.Add(first);
            s.ActiveColor = first.Color;
            return s;
        }

        public int PlayerCount(ColorMatchState s) => s.Hands.Count;
        public int CurrentPlayer(ColorMatchState s) => s.Current;
        public bool IsOver(ColorMatchState s) => s.WinnerIndex >= 0;
        public int Winner(ColorMatchState s) => s.WinnerIndex;

        public static bool CanPlay(ColorMatchState s, Card c) =>
            c.IsWild || c.Color == s.ActiveColor ||
            (c.Kind == CardKind.Number && s.Top.Kind == CardKind.Number && c.Number == s.Top.Number) ||
            (c.Kind != CardKind.Number && c.Kind == s.Top.Kind);

        public IReadOnlyList<ColorMatchMove> LegalMoves(ColorMatchState s)
        {
            var moves = new List<ColorMatchMove>();
            var hand = s.Hands[s.Current];
            for (var i = 0; i < hand.Count; i++)
            {
                if (!CanPlay(s, hand[i])) continue;
                if (hand[i].IsWild) foreach (var c in Colors) moves.Add(ColorMatchMove.Play(i, c));
                else moves.Add(ColorMatchMove.Play(i));
            }
            // Kart çekmek her zaman serbest değil: önce bir kez çekilir; çektikten sonra oynanamıyorsa "çek" = pas.
            moves.Add(ColorMatchMove.DrawCard());
            return moves;
        }

        public void Apply(ColorMatchState s, ColorMatchMove m)
        {
            if (IsOver(s)) throw new InvalidOperationException("Oyun bitti");
            var hand = s.Hands[s.Current];
            if (m.Draw)
            {
                if (s.DrewThisTurn) { EndTurn(s, 1); return; } // pas
                hand.Add(Pop(s));
                s.DrewThisTurn = true;
                if (!hand.Any(c => CanPlay(s, c))) EndTurn(s, 1);
                return;
            }
            var card = hand[m.HandIndex];
            if (!CanPlay(s, card)) throw new InvalidOperationException("Bu kart oynanamaz: " + card);
            hand.RemoveAt(m.HandIndex);
            s.Discard.Add(card);
            s.ActiveColor = card.IsWild ? (m.ChosenColor == CardColor.Wild ? CardColor.Red : m.ChosenColor) : card.Color;
            if (hand.Count == 0) { s.WinnerIndex = s.Current; return; }

            var next = Next(s, 1);
            switch (card.Kind)
            {
                case CardKind.Skip: EndTurn(s, 2); break;
                case CardKind.Reverse:
                    s.Direction = -s.Direction;
                    EndTurn(s, s.Hands.Count == 2 ? 2 : 1); // iki kişide yön değiştir = atla
                    break;
                case CardKind.DrawTwo: Give(s, next, 2); EndTurn(s, 2); break;
                case CardKind.WildDrawFour: Give(s, next, 4); EndTurn(s, 2); break;
                default: EndTurn(s, 1); break;
            }
        }

        private static void Give(ColorMatchState s, int player, int n)
        {
            for (var i = 0; i < n; i++) s.Hands[player].Add(Pop(s));
        }

        private static int Next(ColorMatchState s, int steps)
        {
            var n = s.Hands.Count;
            return ((s.Current + s.Direction * steps) % n + n) % n;
        }

        private static void EndTurn(ColorMatchState s, int steps)
        {
            s.Current = Next(s, steps);
            s.DrewThisTurn = false;
        }

        private static Card Pop(ColorMatchState s)
        {
            if (s.Deck.Count == 0)
            {
                // Atılanlar karıştırılıp yeni deste olur (açık kart kalır)
                var top = s.Discard[s.Discard.Count - 1];
                s.Deck = s.Discard.Take(s.Discard.Count - 1).ToList();
                s.Discard = new List<Card> { top };
                Shuffle(s.Deck, s.Rng);
                if (s.Deck.Count == 0) s.Deck = BuildDeck(new ColorMatchOptions());
            }
            var c = s.Deck[s.Deck.Count - 1];
            s.Deck.RemoveAt(s.Deck.Count - 1);
            return c;
        }

        private static void Shuffle<T>(IList<T> list, Random rng)
        {
            for (var i = list.Count - 1; i > 0; i--)
            {
                var j = rng.Next(i + 1);
                (list[i], list[j]) = (list[j], list[i]);
            }
        }
    }

    /// <summary>
    /// Bot: zorluk 0'da rastgele geçerli hamle; arttıkça elinde en çok olan rengi tutar, jokerleri saklar,
    /// rakibin kartı azalınca saldırı kartlarını kullanır. Kolay botlar bazen çekmeyi tercih eder (hata payı).
    /// </summary>
    public sealed class ColorMatchBot : IBot<ColorMatchState, ColorMatchMove>
    {
        private readonly float _difficulty;
        public ColorMatchBot(float difficulty) { _difficulty = difficulty; }

        public ColorMatchMove Choose(ColorMatchState s, IReadOnlyList<ColorMatchMove> legal, Random rng)
        {
            var plays = legal.Where(m => !m.Draw).ToList();
            if (plays.Count == 0) return ColorMatchMove.DrawCard();
            if (rng.NextDouble() > 0.35 + 0.65 * _difficulty) return plays[rng.Next(plays.Count)]; // kolay: rastgele

            var hand = s.Hands[s.Current];
            var colorCounts = hand.Where(c => !c.IsWild).GroupBy(c => c.Color).ToDictionary(g => g.Key, g => g.Count());
            var bestColor = colorCounts.Count == 0 ? CardColor.Red : colorCounts.OrderByDescending(kv => kv.Value).First().Key;
            var opponentCards = s.Hands.Where((h, i) => i != s.Current).Min(h => h.Count);

            double Score(ColorMatchMove m)
            {
                var c = hand[m.HandIndex];
                double score = 0;
                if (c.IsWild) score -= 5 - (opponentCards <= 2 ? 6 : 0);            // jokeri sakla, sona doğru kullan
                if (!c.IsWild && colorCounts.TryGetValue(c.Color, out var n)) score += n;
                if (c.Kind == CardKind.DrawTwo || c.Kind == CardKind.WildDrawFour || c.Kind == CardKind.Skip)
                    score += opponentCards <= 3 ? 4 : 0;
                if (c.Kind == CardKind.Number) score += c.Number * 0.05;          // yüksek sayıları önce ver
                if (c.IsWild && m.ChosenColor == bestColor) score += 1;
                return score;
            }
            return plays.OrderByDescending(Score).First();
        }
    }
}
