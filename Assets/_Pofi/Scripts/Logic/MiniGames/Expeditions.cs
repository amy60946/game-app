using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Profile;

namespace Pofi.Logic.MiniGames
{
    // ---------------------------------------------------------------- Mağara keşfi (Sv11)

    /// <summary>
    /// Mağara keşfi (FR-MINI-6): karanlık ızgarada fenerle bir kareye bakınca çevresindeki 3×3 alan aydınlanır;
    /// saklı mücevherleri sınırlı fener hakkıyla bul. Her yerleşim çözülebilir: mücevher sayısı ≤ fener hakkı.
    /// </summary>
    public sealed class CaveExplore
    {
        public int Width { get; }
        public int Height { get; }
        public int Lights { get; private set; }
        public HashSet<int> Gems { get; } = new HashSet<int>();
        public HashSet<int> Revealed { get; } = new HashSet<int>();
        public HashSet<int> Found { get; } = new HashSet<int>();
        public bool Done => Found.Count == Gems.Count || Lights == 0;

        public CaveExplore(AgeBand band, int seed)
        {
            var rng = new Random(seed);
            Width = band.Young() ? 5 : 6;
            Height = band.Young() ? 5 : band == AgeBand.B ? 7 : 8;
            var gems = band.Young() ? 3 : 4;
            Lights = gems + (band.Young() ? 4 : band == AgeBand.B ? 3 : 2);
            while (Gems.Count < gems) Gems.Add(rng.Next(Width * Height));
        }

        /// <summary>Fenerle bak: 3×3 alan aydınlanır. Yeni bulunan mücevher sayısını döndürür.</summary>
        public int Look(int x, int y)
        {
            if (Done || x < 0 || y < 0 || x >= Width || y >= Height) return 0;
            Lights--;
            var found = 0;
            for (var dy = -1; dy <= 1; dy++)
            for (var dx = -1; dx <= 1; dx++)
            {
                int cx = x + dx, cy = y + dy;
                if (cx < 0 || cy < 0 || cx >= Width || cy >= Height) continue;
                var i = cy * Width + cx;
                Revealed.Add(i);
                if (Gems.Contains(i) && Found.Add(i)) found++;
            }
            return found;
        }

        public MiniGameResult Finish()
        {
            var score = Found.Count * 3 + (Found.Count == Gems.Count ? Lights : 0);
            return new MiniGameResult { GameId = "minigame_cave", Score = score, SuggestedXp = MiniGameXp.For(score, 2) };
        }
    }

    // ---------------------------------------------------------------- Dağ yürüyüşü (Sv13)

    /// <summary>
    /// Dağ yürüyüşü (FR-MINI-6): katman katman zirveye çık; her adımda bir üst kattaki komşu (sol/düz/sağ) noktaya geç,
    /// oradaki çiçek/meyveyi topla. Rota seçimi = puan. En iyi rota dinamik programlamayla bilinir (XP ona göre ölçeklenir).
    /// </summary>
    public sealed class HikeRoute
    {
        public const int Columns = 3;
        public int Layers { get; }
        public int[,] Value { get; }      // [katman, sütun] toplanabilir değer (0–3)
        public int Layer { get; private set; }
        public int Column { get; private set; } = 1;
        public int Collected { get; private set; }
        public List<int> Path { get; } = new List<int> { 1 };
        public bool AtSummit => Layer == Layers - 1;

        public HikeRoute(AgeBand band, int seed)
        {
            var rng = new Random(seed);
            Layers = band.Young() ? 6 : band == AgeBand.B ? 8 : 10;
            Value = new int[Layers, Columns];
            for (var l = 1; l < Layers; l++)
            for (var c = 0; c < Columns; c++)
                Value[l, c] = rng.Next(4);
        }

        public bool CanStep(int column) => !AtSummit && column >= 0 && column < Columns && Math.Abs(column - Column) <= 1;

        public bool Step(int column)
        {
            if (!CanStep(column)) return false;
            Layer++;
            Column = column;
            Collected += Value[Layer, column];
            Path.Add(column);
            return true;
        }

        /// <summary>Başlangıçtan zirveye en çok toplanabilen değer.</summary>
        public int Best()
        {
            var best = new int[Columns];
            for (var c = 0; c < Columns; c++) best[c] = c == 1 ? 0 : int.MinValue / 2;
            for (var l = 1; l < Layers; l++)
            {
                var next = new int[Columns];
                for (var c = 0; c < Columns; c++)
                {
                    var from = int.MinValue / 2;
                    for (var d = -1; d <= 1; d++)
                        if (c + d >= 0 && c + d < Columns) from = Math.Max(from, best[c + d]);
                    next[c] = from + Value[l, c];
                }
                best = next;
            }
            return best.Max();
        }

        public MiniGameResult Finish()
        {
            var best = Math.Max(1, Best());
            var xp = 10 + (int)Math.Round(25.0 * Collected / best);
            return new MiniGameResult { GameId = "minigame_hike", Score = Collected, SuggestedXp = Math.Min(40, xp) };
        }
    }
}
