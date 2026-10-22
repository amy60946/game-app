using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Profile;

namespace Pofi.Logic.MiniGames
{
    /// <summary>Mini oyun sonucu (FR-MINI-7): XP günlük sınıra tabidir (XpSystem); burada oyunun önerdiği XP hesaplanır.</summary>
    public sealed class MiniGameResult
    {
        public string GameId;
        public int Score;
        public int SuggestedXp;
        public List<string> Finds = new List<string>(); // yeni bulgular (koleksiyon vb.)
    }

    public static class MiniGameXp
    {
        /// <summary>Taban 5 XP (katılım), skora göre artar, oyun başına en fazla 40 XP.</summary>
        public static int For(int score, int perPoint, int max = 40) => Math.Min(max, 5 + Math.Max(0, score) * perPoint);
    }

    // ---------------------------------------------------------------- Hindistan cevizi toplama (Sv1)

    public struct FallingItem
    {
        public int AtMs;      // düşmeye başladığı an
        public float X;       // 0..1 ekran genişliği
        public bool Golden;   // altın ceviz: 3 puan
    }

    /// <summary>
    /// Düşen cevizleri sepetle yakala (FR-MINI-1). Süre 30–45 sn; hız ve yoğunluk banda ve zorluğa göre.
    /// Program deterministik üretilir (tekrar oynanabilir, test edilebilir); fizik/görsel Unity'de.
    /// </summary>
    public sealed class CoconutCatch
    {
        public int DurationMs { get; }
        public float FallSeconds { get; }       // ekranı geçme süresi
        public List<FallingItem> Schedule { get; } = new List<FallingItem>();

        public CoconutCatch(AgeBand band, float difficulty, int seed)
        {
            var rng = new Random(seed);
            var bandBase = band.Young() ? 0.0f : band == AgeBand.B ? 0.35f : 0.65f;
            var d = Math.Max(0f, Math.Min(1f, bandBase + difficulty * 0.35f));
            DurationMs = band.Young() ? 30000 : band == AgeBand.B ? 40000 : 45000;
            FallSeconds = 3.2f - 1.6f * d;
            var interval = (int)(1300 - 750 * d);
            var lastX = 0.5f;
            for (var t = 600; t < DurationMs - (int)(FallSeconds * 1000); t += interval + rng.Next(-120, 121))
            {
                // Arka arkaya iki ceviz arası yatay mesafe sınırlı: yakalanabilir olsun
                var maxJump = 0.35f + 0.4f * d;
                var x = Math.Max(0.08f, Math.Min(0.92f, lastX + (float)(rng.NextDouble() * 2 - 1) * maxJump));
                Schedule.Add(new FallingItem { AtMs = t, X = x, Golden = rng.NextDouble() < 0.08 });
                lastX = x;
            }
        }

        public static int Points(FallingItem f) => f.Golden ? 3 : 1;

        public MiniGameResult Finish(IEnumerable<int> caughtIndices)
        {
            var idx = new HashSet<int>(caughtIndices.Where(i => i >= 0 && i < Schedule.Count));
            var score = idx.Sum(i => Points(Schedule[i]));
            return new MiniGameResult { GameId = "minigame_coconut", Score = score, SuggestedXp = MiniGameXp.For(score, 1) };
        }
    }

    // ---------------------------------------------------------------- Pet'e yardım et (Sv1)

    public enum Warmth { Found, Hot, Warm, Cold }

    /// <summary>
    /// Bot pet'in kayıp eşyasını bul (FR-MINI-2): saklanma noktalarından birine dokun, pet "sıcak/ılık/soğuk" der.
    /// Band A'da az nokta ve cömert ipucu.
    /// </summary>
    public sealed class HelpPetSearch
    {
        public int Columns { get; }
        public int Rows { get; }
        public int Hidden { get; }
        public int Tries { get; private set; }

        public HelpPetSearch(AgeBand band, int seed)
        {
            Columns = band.Young() ? 3 : 4;
            Rows = band.Young() ? 2 : band == AgeBand.B ? 3 : 4;
            Hidden = new Random(seed).Next(Columns * Rows);
        }

        public Warmth Guess(int spot)
        {
            Tries++;
            if (spot == Hidden) return Warmth.Found;
            var d = Math.Abs(spot % Columns - Hidden % Columns) + Math.Abs(spot / Columns - Hidden / Columns);
            return d == 1 ? Warmth.Hot : d == 2 ? Warmth.Warm : Warmth.Cold;
        }

        public MiniGameResult Finish() =>
            new MiniGameResult { GameId = "minigame_help_pet", Score = Math.Max(1, Columns * Rows - Tries + 1), SuggestedXp = Math.Max(10, 25 - Tries * 2) };
    }

    // ---------------------------------------------------------------- Yüzme / sörf / kayak (Sv2/3/5)

    public enum RowItem { Empty, Obstacle, Shell }

    /// <summary>
    /// Şeritli refleks oyunu (FR-MINI-3): 3 şerit, tek parmakla sağa/sola. Her satırda en az bir boş şerit
    /// garanti; art arda satırlar arasında bir şerit kaymayla geçilebilir yol hep vardır.
    /// Tema (yüzme: kaya/denizanası, sörf: dalga, kayak: kardan adam) yalnızca görseldir.
    /// </summary>
    public sealed class LaneRunner
    {
        public const int Lanes = 3;
        public string GameId { get; }
        public float RowsPerSecond { get; }
        public List<RowItem[]> Rows { get; } = new List<RowItem[]>();
        public List<int> SafeLanes { get; } = new List<int>(); // garanti edilen geçilebilir yol

        public LaneRunner(string gameId, AgeBand band, float difficulty, int seed, int rowCount = 120)
        {
            GameId = gameId;
            var rng = new Random(seed);
            var bandBase = band.Young() ? 0.0f : band == AgeBand.B ? 0.35f : 0.65f;
            var d = Math.Max(0f, Math.Min(1f, bandBase + difficulty * 0.35f));
            RowsPerSecond = 1.6f + 2.2f * d;
            var obstacleChance = 0.25 + 0.35 * d;
            var safe = 1; // oyuncunun kesin geçebileceği şerit
            for (var r = 0; r < rowCount; r++)
            {
                var row = new RowItem[Lanes];
                if (r >= 3)
                {
                    // Güvenli şerit en fazla bir kayar
                    safe = Math.Max(0, Math.Min(Lanes - 1, safe + rng.Next(-1, 2)));
                    for (var l = 0; l < Lanes; l++)
                        if (l != safe && rng.NextDouble() < obstacleChance) row[l] = RowItem.Obstacle;
                    if (rng.NextDouble() < 0.3) row[safe] = RowItem.Shell;
                }
                Rows.Add(row);
                SafeLanes.Add(safe);
            }
        }

        /// <summary>Oyuncunun şerit dizisini oynatır: engele çarpınca tur biter (ceza yok, sonuç ekranı).</summary>
        public MiniGameResult Simulate(IReadOnlyList<int> laneEachRow)
        {
            int shells = 0, distance = 0;
            for (var r = 0; r < Rows.Count && r < laneEachRow.Count; r++)
            {
                var lane = laneEachRow[r];
                if (Rows[r][lane] == RowItem.Obstacle) break;
                if (Rows[r][lane] == RowItem.Shell) shells++;
                distance++;
            }
            var score = distance / 4 + shells * 2;
            return new MiniGameResult { GameId = GameId, Score = score, SuggestedXp = MiniGameXp.For(score, 1) };
        }

        /// <summary>Test/bot: garanti edilen yol (her satırda en fazla bir şerit kayma).</summary>
        public List<int> PerfectPath() => SafeLanes.ToList();
    }
}
