using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Cards
{
    // "Kule": blok çekme ve üste koyma oyunu (Jenga benzeri, özgün adla). Fizik Unity'de; bu sınıf kuralları,
    // sırayı ve "devrilme riskini" verir. Dokunma hassasiyeti (0–1) mini oyun girdisinden gelir.

    public readonly struct TowerMove
    {
        public readonly int Layer;   // 0 = en alt
        public readonly int Slot;    // 0 sol, 1 orta, 2 sağ
        public TowerMove(int layer, int slot) { Layer = layer; Slot = slot; }
        public override string ToString() => $"kat {Layer}, blok {Slot}";
    }

    public sealed class TowerState
    {
        public List<bool[]> Layers = new List<bool[]>();  // true = blok yerinde
        public int TopCount;          // en üstteki eksik katta kaç blok var (0–3; 3 ise yeni kat açılır)
        public int Current;
        public int Players = 2;
        public int LoserIndex = -1;   // kuleyi deviren kaybeder
        public Random Rng;
    }

    public sealed class TowerRules : IGameRules<TowerState, TowerMove>
    {
        public float Precision = 1f;  // çocuğun hamle hassasiyeti; bot için zorluğa göre ayarlanır

        public static TowerState NewGame(int layers, int players, int seed)
        {
            var s = new TowerState { Players = players, Rng = new Random(seed), TopCount = 3 };
            for (var i = 0; i < layers; i++) s.Layers.Add(new[] { true, true, true });
            return s;
        }

        public int PlayerCount(TowerState s) => s.Players;
        public int CurrentPlayer(TowerState s) => s.Current;
        public bool IsOver(TowerState s) => s.LoserIndex >= 0;
        public int Winner(TowerState s) => s.Players == 2 && s.LoserIndex >= 0 ? 1 - s.LoserIndex : -1;

        /// <summary>Tamamlanmış en üst kat ve onun altındaki kat hariç, yerinde olan her blok çekilebilir (klasik kural).</summary>
        public IReadOnlyList<TowerMove> LegalMoves(TowerState s)
        {
            var moves = new List<TowerMove>();
            var lastSafe = s.Layers.Count - (s.TopCount == 3 ? 1 : 2); // en üst tam kat yasak; eksik üst kat da yasak
            for (var l = 0; l < lastSafe; l++)
                for (var k = 0; k < 3; k++)
                    if (s.Layers[l][k] && WouldStand(s.Layers[l], k)) moves.Add(new TowerMove(l, k));
            return moves;
        }

        /// <summary>Kalan bloklar katı taşıyabilir mi: yalnızca bir kenar blok kalırsa kat çöker (fizikle de tutarlı).</summary>
        public static bool WouldStand(bool[] layer, int remove)
        {
            var after = (bool[])layer.Clone();
            after[remove] = false;
            var count = after.Count(b => b);
            if (count >= 2) return true;
            return count == 1 && after[1]; // tek blok ancak ortadaysa ayakta kalır
        }

        /// <summary>Devrilme olasılığı: yükseklik, katın zayıflığı ve hassasiyet. Kolay hamlelerde ~%2, riskli hamlelerde artar.</summary>
        public static float Risk(TowerState s, TowerMove m, float precision)
        {
            var layer = s.Layers[m.Layer];
            var left = layer.Count(b => b) - 1;
            var weakness = left == 1 ? 0.25f : 0f;                        // tek orta blokla kalan kat
            var edge = m.Slot != 1 && layer[1] ? 0.03f : 0.06f;           // orta varken kenar çekmek kolay
            var height = (s.Layers.Count - m.Layer) / (float)s.Layers.Count * 0.04f;
            var clumsy = (1f - Clamp01(precision)) * 0.25f;
            return Clamp01(0.01f + weakness + edge + height + clumsy);
        }

        public void Apply(TowerState s, TowerMove m)
        {
            if (IsOver(s)) throw new InvalidOperationException("Oyun bitti");
            if (!LegalMoves(s).Contains(m)) throw new InvalidOperationException("Bu blok çekilemez: " + m);
            if (s.Rng.NextDouble() < Risk(s, m, Precision)) { s.LoserIndex = s.Current; return; }
            s.Layers[m.Layer][m.Slot] = false;
            // Bloğu üste koy
            if (s.TopCount == 3) { s.Layers.Add(new[] { true, false, false }); s.TopCount = 1; }
            else { s.Layers[s.Layers.Count - 1][s.TopCount] = true; s.TopCount++; }
            s.Current = (s.Current + 1) % s.Players;
        }

        private static float Clamp01(float v) => v < 0 ? 0 : v > 1 ? 1 : v;
    }

    /// <summary>Bot en düşük riskli bloğu seçer; zorluk düştükçe daha sık "rastgele" dener.</summary>
    public sealed class TowerBot : IBot<TowerState, TowerMove>
    {
        private readonly float _difficulty;
        public TowerBot(float difficulty) { _difficulty = difficulty; }
        public float Precision => 0.6f + 0.4f * _difficulty;

        public TowerMove Choose(TowerState s, IReadOnlyList<TowerMove> legal, Random rng)
        {
            if (rng.NextDouble() > 0.4 + 0.6 * _difficulty) return legal[rng.Next(legal.Count)];
            return legal.OrderBy(m => TowerRules.Risk(s, m, Precision)).First();
        }
    }
}
