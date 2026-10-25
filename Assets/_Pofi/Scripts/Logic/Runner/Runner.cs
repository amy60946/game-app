using System;
using System.Collections.Generic;
using Pofi.Logic.MiniGames;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Runner
{
    // Oyun Kulübesi koşu oyunu (25 Ekim 2026, kullanıcı: "kart oyunlarının yerine çocukların bugün sevdiği tarzda bir koşu oyunu
    // koy, nabız yoklayalım"; araştırma + alternatifler https://claude.ai/artifact/DHw1MjM35Zi9cSbZkdXT1m, öneri A "Piramit Koşusu").
    // Üç şerit, sağa/sola kaydır = şerit, yukarı = zıpla, aşağı = kay. Kovalayan canavar yok: Okti kaçan altın skarabenin peşinden koşar.
    // Koşu sonsuz değil: her parkurun bir varış kapısı var (~55–75 sn), sonra adaya dönüş. Coin yok; XP mevcut mini oyun kuralıyla
    // (MiniGameXp, oyun başına ≤ 40, günlük sınıra sayılır). Parkur tohumla deterministik üretilir (testli); çizim Runtime/Screens/RunnerScreen.

    /// <summary>Engel türü: Block şeridi kapatır (şerit değiştir), Low yerde (zıpla), High başın hizasında (kay).</summary>
    public enum Hazard { Block, Low, High }

    public enum RunAction { None, Left, Right, Jump, Slide }

    public struct Obstacle
    {
        public float Z;        // parkurdaki yeri (m)
        public int Lane;       // 0..2; −1 = bütün yol (Low / High)
        public Hazard Kind;
        public int Variant;    // görünüm çeşidi (Block: 0/1)
    }

    public struct Pickup
    {
        public float Z;
        public int Lane;
        public float Height;   // yerden yükseklik (zıplama yayında havada)
        public bool Scroll;    // papirüs (koşu başına bir tane, bilgi kartı)
    }

    /// <summary>Koşu olayları (ses, efekt, sayaç için ekrana bildirilir).</summary>
    public enum RunEvent { Hit, Scarab, Scroll, Finish, Out }

    /// <summary>Yaş grubuna göre koşu ayarı (ortak/sozlesme/durumlar.md §4: K 5 ve altı / A 6–8 / B 9–12 / C 13+).</summary>
    public sealed class RunnerConfig
    {
        public float StartSpeed, MaxSpeed;   // m/sn; parkur boyunca doğrusal hızlanır
        public float Goal;                   // varış kapısı (m)
        public int Hearts;                   // 0 = sınırsız (K: çarpınca yalnız yavaşlar)
        public float MinGap;                 // iki engel sırası arası en az (m)
        public float Reaction;               // tepki süresi (sn): sıra aralığı en az hız × bu
        public float DoubleChance;           // iki şeridi birden kapatan sıra olasılığı
        public float FullWidthChance;        // zıpla/kay sırası olasılığı

        public static RunnerConfig For(AgeBand band)
        {
            switch (band)
            {
                case AgeBand.K: return new RunnerConfig { StartSpeed = 7f, MaxSpeed = 9f, Goal = 420f, Hearts = 0, MinGap = 24f, Reaction = 1.6f, DoubleChance = 0f, FullWidthChance = 0.2f };
                case AgeBand.A: return new RunnerConfig { StartSpeed = 8f, MaxSpeed = 11f, Goal = 560f, Hearts = 5, MinGap = 21f, Reaction = 1.35f, DoubleChance = 0.2f, FullWidthChance = 0.28f };
                case AgeBand.B: return new RunnerConfig { StartSpeed = 9f, MaxSpeed = 13f, Goal = 720f, Hearts = 3, MinGap = 18f, Reaction = 1.15f, DoubleChance = 0.35f, FullWidthChance = 0.32f };
                default: return new RunnerConfig { StartSpeed = 10f, MaxSpeed = 15f, Goal = 860f, Hearts = 3, MinGap = 16f, Reaction = 1.0f, DoubleChance = 0.45f, FullWidthChance = 0.35f };
            }
        }

        public float SpeedAt(float z) => StartSpeed + (MaxSpeed - StartSpeed) * Math.Max(0f, Math.Min(1f, z / Math.Max(1f, Goal)));
    }

    /// <summary>
    /// Parkur: engel sıraları + skarabe dizileri + bir papirüs. Kurallar (testli): hiçbir sırada üç şerit birden kapalı değil;
    /// yol boyu Low/High tek başına (yanında Block yok); sıralar arası en az <see cref="RunnerConfig.MinGap"/> ve o hızda tepki mesafesi;
    /// başlangıçta 30 m, varıştan önce 25 m boş; toplanacaklar engelin içinde değil.
    /// </summary>
    public sealed class RunnerCourse
    {
        public const int Lanes = 3;
        public const float StartClear = 30f, EndClear = 25f;
        public const float ScarabStep = 2.6f;

        public RunnerConfig Config { get; }
        public List<Obstacle> Obstacles { get; } = new List<Obstacle>();
        public List<Pickup> Pickups { get; } = new List<Pickup>();
        public int ScarabTotal { get; private set; }

        public RunnerCourse(AgeBand band, int seed) : this(RunnerConfig.For(band), seed) { }

        public RunnerCourse(RunnerConfig cfg, int seed)
        {
            Config = cfg;
            var rng = new Random(seed);
            var z = StartClear;
            var free = 1;   // önceki sıranın açık şeridi (skarabe dizisi oradan akar)
            var rows = new List<(float z, bool full)>();
            while (z < cfg.Goal - EndClear)
            {
                var r = rng.NextDouble();
                if (r < cfg.FullWidthChance)
                {
                    var kind = rng.NextDouble() < 0.5 ? Hazard.Low : Hazard.High;
                    Obstacles.Add(new Obstacle { Z = z, Lane = -1, Kind = kind });
                    rows.Add((z, true));
                    // Low'un üstünden yay çizen skarabeler (zıplayana ödül)
                    if (kind == Hazard.Low) Arc(z, free);
                }
                else
                {
                    var two = rng.NextDouble() < cfg.DoubleChance;
                    // açık şerit en çok bir kayar: yeni açık şerit eskisine komşu ya da aynı
                    var open = Math.Max(0, Math.Min(Lanes - 1, free + rng.Next(-1, 2)));
                    var single = Other(open, rng);
                    for (var l = 0; l < Lanes; l++)
                    {
                        if (l == open) continue;
                        if (!two && l != single) continue;
                        Obstacles.Add(new Obstacle { Z = z, Lane = l, Kind = Hazard.Block, Variant = rng.Next(2) });
                    }
                    rows.Add((z, false));
                    free = open;
                }
                var gap = Math.Max(cfg.MinGap, cfg.SpeedAt(z) * cfg.Reaction) + (float)rng.NextDouble() * 6f;
                // skarabe dizisi: bu sıradan sonraki aralığın ortasında, açık şeritte
                var next = z + gap;
                if (rng.NextDouble() < 0.8) Trail(z + 4f, Math.Min(next - 4f, cfg.Goal - EndClear), free);
                z = next;
            }
            // papirüs: parkurun ~%55'inde, iki sıra arasında, açık şeritte
            var target = cfg.Goal * 0.55f;
            var best = StartClear; var bestLane = 1;
            for (var i = 0; i + 1 < rows.Count; i++)
            {
                var mid = (rows[i].z + rows[i + 1].z) / 2f;
                if (Math.Abs(mid - target) < Math.Abs(best - target) && rows[i + 1].z - rows[i].z >= 12f) { best = mid; bestLane = LaneFreeAt(rows[i].z); }
            }
            Pickups.RemoveAll(p => Math.Abs(p.Z - best) < 2f && p.Lane == bestLane);
            Pickups.Add(new Pickup { Z = best, Lane = bestLane, Height = 0.4f, Scroll = true });
            Pickups.Sort((a, b) => a.Z.CompareTo(b.Z));
            ScarabTotal = Pickups.Count - 1;
        }

        private static int Other(int open, Random rng)
        {
            // tek Block: açık şerit dışındaki iki şeritten biri
            var a = (open + 1) % Lanes; var b = (open + 2) % Lanes;
            return rng.NextDouble() < 0.5 ? a : b;
        }

        private int LaneFreeAt(float z)
        {
            for (var l = 0; l < Lanes; l++)
            {
                var blocked = false;
                foreach (var o in Obstacles) if (Math.Abs(o.Z - z) < 0.1f && (o.Lane == l || o.Lane == -1)) blocked = true;
                if (!blocked) return l;
            }
            return 1;
        }

        private void Trail(float from, float to, int lane)
        {
            var n = Math.Min(6, (int)((to - from) / ScarabStep));
            if (n < 3) return;
            var start = (from + to) / 2f - (n - 1) * ScarabStep / 2f;
            for (var i = 0; i < n; i++) Pickups.Add(new Pickup { Z = start + i * ScarabStep, Lane = lane, Height = 0.35f });
        }

        private void Arc(float z, int lane)
        {
            // zıplama yayı: tepe 1,3 m; skarabeler engelin önünde-üstünde-arkasında
            for (var i = -2; i <= 2; i++)
            {
                var t = 0.5f + i * 0.2f;
                Pickups.Add(new Pickup { Z = z + i * 1.6f, Lane = lane, Height = 0.35f + 4f * 1.1f * t * (1f - t) });
            }
        }

        /// <summary>Bu Z'de, bu şeritte, bu türde engel var mı (testler ve yardım için).</summary>
        public bool Blocked(float z, int lane)
        {
            foreach (var o in Obstacles)
                if (Math.Abs(o.Z - z) < 0.1f && (o.Lane == lane || o.Lane == -1) && o.Kind == Hazard.Block) return true;
            return false;
        }
    }

    /// <summary>
    /// Koşunun kendisi (deterministik adım): şerit geçişi ~0,18 sn, zıplama 0,75 sn (tepe 1,3 m), kayma 0,75 sn.
    /// Çarpınca can azalır (K'de azalmaz), hız ×0,6'ya düşüp 2 sn'de toparlanır, 1,2 sn dokunulmazlık.
    /// </summary>
    public sealed class RunnerRun
    {
        public const float JumpTime = 0.75f, JumpPeak = 1.3f, SlideTime = 0.75f, LaneTime = 0.18f;
        public const float Invulnerable = 1.2f, HitSlow = 0.6f, Recover = 2f;
        public const float LowTop = 0.55f, HighBottom = 1.15f;   // engel ölçüleri (rn_low üstü, rn_high kiriş altı)
        public const float Depth = 0.6f;                         // çarpışma için engelin yarım derinliği + petin yarıçapı

        public RunnerCourse Course { get; }
        public float Z { get; private set; }
        public float Speed { get; private set; }
        public float LaneX { get; private set; } = 1f;            // 0..2 (kesirli: geçiş sırasında)
        public int TargetLane { get; private set; } = 1;
        public float Height { get; private set; }                 // zıplama yüksekliği
        public bool Sliding => _slide > 0f;
        public bool Jumping => _jump > 0f;
        public float SlideT => _slide <= 0f ? 0f : 1f - _slide / SlideTime;
        public float JumpT => _jump <= 0f ? 0f : 1f - _jump / JumpTime;
        public int Hearts { get; private set; }
        public int Hits { get; private set; }
        public bool Invuln => _inv > 0f;
        public int Scarabs { get; private set; }
        public bool ScrollFound { get; private set; }
        public bool Finished { get; private set; }
        public bool Out { get; private set; }
        public bool Over => Finished || Out;
        public float Progress => Math.Min(1f, Z / Math.Max(1f, Course.Config.Goal));
        public float Elapsed { get; private set; }
        public readonly HashSet<int> Taken = new HashSet<int>();  // toplanan Pickups sırası

        private float _jump, _slide, _inv, _slow;
        private int _nextObs, _nextPick;
        private readonly HashSet<int> _hitRows = new HashSet<int>();

        public RunnerRun(RunnerCourse course)
        {
            Course = course;
            Hearts = course.Config.Hearts;
            Speed = course.Config.StartSpeed;
        }

        /// <summary>Bir adım (dt sn) + bu karedeki hareket. Olaylar <paramref name="events"/>'e eklenir.</summary>
        public void Step(float dt, RunAction action, List<RunEvent> events = null)
        {
            if (Over || dt <= 0f) return;
            switch (action)
            {
                case RunAction.Left: TargetLane = Math.Max(0, TargetLane - 1); break;
                case RunAction.Right: TargetLane = Math.Min(RunnerCourse.Lanes - 1, TargetLane + 1); break;
                case RunAction.Jump: if (_jump <= 0f) { _jump = JumpTime; _slide = 0f; } break;
                case RunAction.Slide:
                    if (_jump > 0f) _jump = Math.Min(_jump, 0.12f);   // havadayken aşağı: hızla in (sonra kay)
                    _slide = SlideTime;
                    break;
            }
            Elapsed += dt;
            var cfg = Course.Config;
            if (_slow > 0f) _slow = Math.Max(0f, _slow - dt);
            var mul = 1f - (1f - HitSlow) * (_slow / Recover);
            Speed = cfg.SpeedAt(Z) * mul;
            var z0 = Z;
            Z += Speed * dt;
            // şerit geçişi
            var step = dt / LaneTime;
            if (Math.Abs(LaneX - TargetLane) <= step) LaneX = TargetLane; else LaneX += Math.Sign(TargetLane - LaneX) * step;
            // zıplama / kayma
            if (_jump > 0f) { _jump = Math.Max(0f, _jump - dt); var t = 1f - _jump / JumpTime; Height = _jump > 0f ? 4f * JumpPeak * t * (1f - t) : 0f; }
            else Height = 0f;
            if (_slide > 0f && _jump <= 0f) _slide = Math.Max(0f, _slide - dt);
            if (_inv > 0f) _inv = Math.Max(0f, _inv - dt);

            // engeller: geçilen aralıktaki (z0 − Depth, Z + Depth) sıralar
            var obs = Course.Obstacles;
            while (_nextObs < obs.Count && obs[_nextObs].Z < z0 - Depth - 2f) _nextObs++;
            for (var i = _nextObs; i < obs.Count && obs[i].Z <= Z + Depth; i++)
            {
                var o = obs[i];
                if (o.Z < z0 - Depth) continue;
                if (_hitRows.Contains(i) || _inv > 0f) continue;
                if (Collides(o))
                {
                    _hitRows.Add(i);
                    Hits++;
                    _inv = Invulnerable; _slow = Recover;
                    if (cfg.Hearts > 0) Hearts = Math.Max(0, Hearts - 1);
                    events?.Add(RunEvent.Hit);
                    if (cfg.Hearts > 0 && Hearts == 0) { Out = true; events?.Add(RunEvent.Out); return; }
                }
            }
            // toplananlar
            var picks = Course.Pickups;
            while (_nextPick < picks.Count && picks[_nextPick].Z < z0 - 1.5f) _nextPick++;
            for (var i = _nextPick; i < picks.Count && picks[i].Z <= Z + 0.8f; i++)
            {
                if (Taken.Contains(i)) continue;
                var p = picks[i];
                if (p.Z < z0 - 0.8f) continue;
                if (Math.Abs(LaneX - p.Lane) > 0.55f) continue;
                var bodyTop = Sliding ? 0.8f : 1.5f;
                if (p.Height > Height + bodyTop || p.Height + 0.5f < Height) continue;
                Taken.Add(i);
                if (p.Scroll) { ScrollFound = true; events?.Add(RunEvent.Scroll); }
                else { Scarabs++; events?.Add(RunEvent.Scarab); }
            }
            if (Z >= cfg.Goal) { Z = cfg.Goal; Finished = true; events?.Add(RunEvent.Finish); }
        }

        private bool Collides(Obstacle o)
        {
            switch (o.Kind)
            {
                case Hazard.Block: return Math.Abs(LaneX - o.Lane) < 0.6f;
                case Hazard.Low: return Height < LowTop;
                default: return !Sliding;   // High: ayakta (zıplarken de) çarpar
            }
        }

        /// <summary>Puan: skarabe + bitirme 10 + papirüs 3. XP mini oyun kuralı (5 + puan, ≤ 40).</summary>
        public MiniGameResult Result()
        {
            var score = Scarabs + (Finished ? 10 : 0) + (ScrollFound ? 3 : 0);
            return new MiniGameResult { GameId = RunnerTheme.GameId, Score = score, SuggestedXp = MiniGameXp.For(score, 1) };
        }
    }

    /// <summary>
    /// Konu yolu (araştırma sayfası: önce Mısır, ilgi tutarsa Uzay, sonra Dinozor). Motor aynı; tema yalnız görünüş + bilgi kartları.
    /// Bilgiler tr.json "runner.&lt;tema&gt;.fact&lt;n&gt;" (çocuğa uygun, korkutucu imge yok); her koşuda sıradaki.
    /// </summary>
    public static class RunnerTheme
    {
        public const string GameId = "minigame_runner";
        public const string Id = "runner";
        public const string Egypt = "egypt";
        public const int EgyptFacts = 12;

        public static int FactIndex(int runsPlayed, int count) => count <= 0 ? 0 : 1 + ((Math.Max(0, runsPlayed) % count + count) % count);
    }
}
