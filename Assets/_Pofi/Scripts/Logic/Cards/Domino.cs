using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Cards
{
    public readonly struct Tile : IEquatable<Tile>
    {
        public readonly int A, B;
        public Tile(int a, int b) { A = Math.Min(a, b); B = Math.Max(a, b); }
        public int Pips => A + B;
        public bool IsDouble => A == B;
        public bool Has(int n) => A == n || B == n;
        public int Other(int n) => A == n ? B : A;
        public bool Equals(Tile o) => A == o.A && B == o.B;
        public override bool Equals(object obj) => obj is Tile t && Equals(t);
        public override int GetHashCode() => A * 7 + B;
        public override string ToString() => $"[{A}|{B}]";
    }

    public enum End { Left, Right }

    public readonly struct DominoMove
    {
        public readonly bool Draw;    // çek (oynanabilir taş yoksa); yığın boşsa pas
        public readonly int HandIndex;
        public readonly End End;
        private DominoMove(bool draw, int i, End e) { Draw = draw; HandIndex = i; End = e; }
        public static DominoMove DrawOrPass() => new DominoMove(true, -1, End.Left);
        public static DominoMove Play(int i, End e) => new DominoMove(false, i, e);
    }

    public sealed class DominoState
    {
        public List<List<Tile>> Hands = new List<List<Tile>>();
        public List<Tile> Boneyard = new List<Tile>();
        public LinkedList<Tile> Line = new LinkedList<Tile>();
        public int LeftEnd = -1, RightEnd = -1;
        public int Current;
        public int ConsecutivePasses;
        public int WinnerIndex = -1;
        public bool Blocked;
    }

    /// <summary>Domino (çift-altı, 28 taş, çekmeli). Kimse oynayamazsa oyun kilitlenir; en az puanlı el kazanır.</summary>
    public sealed class DominoRules : IGameRules<DominoState, DominoMove>
    {
        public static DominoState NewGame(int players, int seed, int handSize = 7)
        {
            var rng = new Random(seed);
            var all = new List<Tile>();
            for (var a = 0; a <= 6; a++) for (var b = a; b <= 6; b++) all.Add(new Tile(a, b));
            for (var i = all.Count - 1; i > 0; i--) { var j = rng.Next(i + 1); (all[i], all[j]) = (all[j], all[i]); }
            var s = new DominoState();
            for (var p = 0; p < players; p++) { s.Hands.Add(all.Take(handSize).ToList()); all.RemoveRange(0, handSize); }
            s.Boneyard = all;
            // En büyük çifti olan başlar (yoksa 0. oyuncu)
            var best = -1;
            for (var p = 0; p < players; p++)
                foreach (var t in s.Hands[p].Where(t => t.IsDouble))
                    if (best < 0 || t.A > s.Hands[best].Where(x => x.IsDouble).Max(x => x.A)) best = p;
            s.Current = Math.Max(0, best);
            return s;
        }

        public int PlayerCount(DominoState s) => s.Hands.Count;
        public int CurrentPlayer(DominoState s) => s.Current;
        public bool IsOver(DominoState s) => s.WinnerIndex >= 0 || s.Blocked;
        public int Winner(DominoState s) => s.WinnerIndex;

        public static bool Fits(DominoState s, Tile t, End e) =>
            s.Line.Count == 0 || t.Has(e == End.Left ? s.LeftEnd : s.RightEnd);

        public IReadOnlyList<DominoMove> LegalMoves(DominoState s)
        {
            var moves = new List<DominoMove>();
            var hand = s.Hands[s.Current];
            for (var i = 0; i < hand.Count; i++)
            {
                if (Fits(s, hand[i], End.Left)) moves.Add(DominoMove.Play(i, End.Left));
                if (s.Line.Count > 0 && Fits(s, hand[i], End.Right) && !(s.LeftEnd == s.RightEnd && Fits(s, hand[i], End.Left)))
                    moves.Add(DominoMove.Play(i, End.Right));
            }
            if (moves.Count == 0) moves.Add(DominoMove.DrawOrPass());
            return moves;
        }

        public void Apply(DominoState s, DominoMove m)
        {
            var hand = s.Hands[s.Current];
            if (m.Draw)
            {
                if (s.Boneyard.Count > 0) { hand.Add(s.Boneyard[0]); s.Boneyard.RemoveAt(0); return; } // aynı oyuncu tekrar dener
                s.ConsecutivePasses++;
                if (s.ConsecutivePasses >= s.Hands.Count) { Block(s); return; }
                Advance(s);
                return;
            }
            var t = hand[m.HandIndex];
            if (!Fits(s, t, m.End)) throw new InvalidOperationException("Taş bu uca uymuyor: " + t);
            hand.RemoveAt(m.HandIndex);
            if (s.Line.Count == 0) { s.Line.AddFirst(t); s.LeftEnd = t.A; s.RightEnd = t.B; }
            else if (m.End == End.Left) { s.Line.AddFirst(t); s.LeftEnd = t.Other(s.LeftEnd); }
            else { s.Line.AddLast(t); s.RightEnd = t.Other(s.RightEnd); }
            s.ConsecutivePasses = 0;
            if (hand.Count == 0) { s.WinnerIndex = s.Current; return; }
            Advance(s);
        }

        private static void Advance(DominoState s) => s.Current = (s.Current + 1) % s.Hands.Count;

        private static void Block(DominoState s)
        {
            s.Blocked = true;
            var sums = s.Hands.Select(h => h.Sum(t => t.Pips)).ToList();
            var min = sums.Min();
            s.WinnerIndex = sums.Count(x => x == min) == 1 ? sums.IndexOf(min) : -1; // eşitlik: berabere
        }
    }

    /// <summary>Kolay: rastgele; zor: büyük taşı erken ver, elde çeşitlilik bırak, çiftleri oyna.</summary>
    public sealed class DominoBot : IBot<DominoState, DominoMove>
    {
        private readonly float _difficulty;
        public DominoBot(float difficulty) { _difficulty = difficulty; }

        public DominoMove Choose(DominoState s, IReadOnlyList<DominoMove> legal, Random rng)
        {
            if (legal.Count == 1 || rng.NextDouble() > 0.35 + 0.65 * _difficulty) return legal[rng.Next(legal.Count)];
            var hand = s.Hands[s.Current];
            double Score(DominoMove m)
            {
                if (m.Draw) return -100;
                var t = hand[m.HandIndex];
                var open = t.Other(m.End == End.Left ? s.LeftEnd : s.RightEnd);
                if (s.Line.Count == 0) open = t.B;
                var keepsOptions = hand.Count(x => !x.Equals(t) && x.Has(open));
                return t.Pips * 0.5 + (t.IsDouble ? 2 : 0) + keepsOptions * 1.5;
            }
            return legal.OrderByDescending(Score).First();
        }
    }
}
