using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Profile;
using Pofi.Logic.Runner;

namespace Pofi.Tests.Logic
{
    public class RunnerTests
    {
        private static readonly AgeBand[] Bands = { AgeBand.K, AgeBand.A, AgeBand.B, AgeBand.C };
        private const float Dt = 1f / 60f;

        [Test]
        public void Yas_grubuna_gore_hiz_uzunluk_can()
        {
            var k = RunnerConfig.For(AgeBand.K);
            var a = RunnerConfig.For(AgeBand.A);
            var c = RunnerConfig.For(AgeBand.C);
            Assert.AreEqual(0, k.Hearts, "K: çarpınca yalnız yavaşlar");
            Assert.Greater(a.Hearts, c.Hearts);
            Assert.Less(k.MaxSpeed, c.MaxSpeed);
            Assert.Less(k.Goal, c.Goal);
            foreach (var b in Bands)
            {
                var cfg = RunnerConfig.For(b);
                // koşu sonsuz değil: ortalama hızla 50–80 sn
                var secs = cfg.Goal / ((cfg.StartSpeed + cfg.MaxSpeed) / 2f);
                Assert.That(secs, Is.InRange(50f, 80f), b.ToString());
            }
        }

        [Test]
        public void Parkur_her_zaman_gecilebilir()
        {
            foreach (var band in Bands)
                for (var seed = 0; seed < 60; seed++)
                {
                    var c = new RunnerCourse(band, seed);
                    var cfg = c.Config;
                    var rows = c.Obstacles.GroupBy(o => (int)Math.Round(o.Z * 10)).OrderBy(g => g.Key).ToList();
                    Assert.Greater(rows.Count, 8, $"{band}/{seed}: parkur boş");
                    float prev = -1f;
                    foreach (var row in rows)
                    {
                        var z = row.First().Z;
                        var full = row.Where(o => o.Lane == -1).ToList();
                        if (full.Count > 0) Assert.AreEqual(1, row.Count(), $"{band}/{seed}: zıpla/kay sırasında başka engel");
                        else Assert.Less(row.Select(o => o.Lane).Distinct().Count(), RunnerCourse.Lanes, $"{band}/{seed}: üç şerit kapalı");
                        Assert.GreaterOrEqual(z, RunnerCourse.StartClear - 0.01f);
                        Assert.LessOrEqual(z, cfg.Goal - RunnerCourse.EndClear + 0.01f);
                        if (prev >= 0f)
                        {
                            Assert.GreaterOrEqual(z - prev, cfg.MinGap - 0.01f, $"{band}/{seed}: sıralar çok yakın");
                            Assert.GreaterOrEqual(z - prev, cfg.SpeedAt(prev) * cfg.Reaction - 0.01f, $"{band}/{seed}: tepki mesafesi");
                        }
                        prev = z;
                    }
                    // K'de iki şeridi birden kapatan sıra yok
                    if (band == AgeBand.K) Assert.IsFalse(rows.Any(r => r.Count(o => o.Kind == Hazard.Block) > 1));
                    // tek papirüs; toplanacaklar Block'un içinde değil
                    Assert.AreEqual(1, c.Pickups.Count(p => p.Scroll));
                    Assert.AreEqual(c.Pickups.Count - 1, c.ScarabTotal);
                    foreach (var p in c.Pickups)
                        Assert.IsFalse(c.Obstacles.Any(o => o.Kind == Hazard.Block && o.Lane == p.Lane && Math.Abs(o.Z - p.Z) < 1.5f),
                            $"{band}/{seed}: skarabe engelin içinde ({p.Z})");
                }
        }

        [Test]
        public void Otomatik_kosucu_carpmadan_bitirir()
        {
            foreach (var band in Bands)
                for (var seed = 0; seed < 25; seed++)
                {
                    var run = new RunnerRun(new RunnerCourse(band, seed));
                    var events = new List<RunEvent>();
                    for (var i = 0; i < 60 * 200 && !run.Over; i++) run.Step(Dt, Bot(run), events);
                    Assert.IsTrue(run.Finished, $"{band}/{seed}: bitmedi");
                    Assert.AreEqual(0, run.Hits, $"{band}/{seed}: çarptı");
                    Assert.Greater(run.Scarabs, 0);
                    Assert.AreEqual(1, events.Count(e => e == RunEvent.Finish));
                    Assert.That(run.Elapsed, Is.InRange(45f, 95f), $"{band}/{seed}: süre");
                }
        }

        [Test]
        public void Hic_hareket_etmeyen_carpar_K_ise_yine_bitirir()
        {
            var k = new RunnerRun(new RunnerCourse(AgeBand.K, 7));
            for (var i = 0; i < 60 * 200 && !k.Over; i++) k.Step(Dt, RunAction.None);
            Assert.IsTrue(k.Finished, "K'de can bitmez");
            Assert.Greater(k.Hits, 0);

            var c = new RunnerRun(new RunnerCourse(AgeBand.C, 7));
            var ev = new List<RunEvent>();
            for (var i = 0; i < 60 * 200 && !c.Over; i++) c.Step(Dt, RunAction.None, ev);
            Assert.IsTrue(c.Out, "C: 3 çarpmada koşu biter");
            Assert.AreEqual(0, c.Hearts);
            Assert.AreEqual(3, ev.Count(e => e == RunEvent.Hit));
            Assert.Less(c.Z, c.Course.Config.Goal);
        }

        [Test]
        public void Carpinca_yavaslar_ve_dokunulmaz_olur()
        {
            var course = new RunnerCourse(AgeBand.A, 3);
            var run = new RunnerRun(course);
            var ev = new List<RunEvent>();
            while (!run.Over && !ev.Contains(RunEvent.Hit)) run.Step(Dt, RunAction.None, ev);
            Assert.IsTrue(run.Invuln);
            run.Step(Dt, RunAction.None);   // yavaşlama sonraki adımdan itibaren
            Assert.Less(run.Speed, course.Config.SpeedAt(run.Z) * 0.7f);
            Assert.AreEqual(course.Config.Hearts - 1, run.Hearts);
        }

        [Test]
        public void Zipla_ve_kay_suresi()
        {
            var run = new RunnerRun(new RunnerCourse(AgeBand.B, 1));
            run.Step(Dt, RunAction.Jump);
            Assert.IsTrue(run.Jumping);
            for (var i = 0; i < 22; i++) run.Step(Dt, RunAction.None);
            Assert.That(run.Height, Is.InRange(1.1f, RunnerRun.JumpPeak + 0.01f), "tepe ~0,37 sn");
            for (var i = 0; i < 40; i++) run.Step(Dt, RunAction.None);
            Assert.IsFalse(run.Jumping); Assert.AreEqual(0f, run.Height);
            run.Step(Dt, RunAction.Slide);
            Assert.IsTrue(run.Sliding);
            run.Step(Dt, RunAction.Left); run.Step(Dt, RunAction.Left);
            Assert.AreEqual(0, run.TargetLane, "en sol şeritte kalır");
            for (var i = 0; i < 20; i++) run.Step(Dt, RunAction.None);
            Assert.AreEqual(0f, run.LaneX, 0.001f);
        }

        [Test]
        public void Puan_ve_xp_siniri()
        {
            var run = new RunnerRun(new RunnerCourse(AgeBand.C, 11));
            for (var i = 0; i < 60 * 200 && !run.Over; i++) run.Step(Dt, Bot(run));
            var r = run.Result();
            Assert.AreEqual(RunnerTheme.GameId, r.GameId);
            Assert.AreEqual(run.Scarabs + 10 + (run.ScrollFound ? 3 : 0), r.Score);
            Assert.LessOrEqual(r.SuggestedXp, 40, "mini oyun kuralı: oyun başına en çok 40");
            var idle = new RunnerRun(new RunnerCourse(AgeBand.C, 11)).Result();
            Assert.AreEqual(5, idle.SuggestedXp, "katılım XP'si");
        }

        [Test]
        public void Bilgi_karti_sirayla_doner()
        {
            var seen = Enumerable.Range(0, RunnerTheme.EgyptFacts).Select(i => RunnerTheme.FactIndex(i, RunnerTheme.EgyptFacts)).ToList();
            CollectionAssert.AreEquivalent(Enumerable.Range(1, RunnerTheme.EgyptFacts), seen);
            Assert.AreEqual(1, RunnerTheme.FactIndex(RunnerTheme.EgyptFacts, RunnerTheme.EgyptFacts));
        }

        [Test]
        public void Ayni_tohum_ayni_parkur()
        {
            var a = new RunnerCourse(AgeBand.B, 42); var b = new RunnerCourse(AgeBand.B, 42);
            Assert.AreEqual(a.Obstacles.Count, b.Obstacles.Count);
            Assert.IsTrue(a.Obstacles.Zip(b.Obstacles, (x, y) => x.Z == y.Z && x.Lane == y.Lane && x.Kind == y.Kind).All(v => v));
        }

        /// <summary>Basit otomatik oyuncu: sıradaki engel sırasına göre şerit seçer, zamanında zıplar/kayar (parkurun geçilebilirliğinin kanıtı).</summary>
        private static RunAction Bot(RunnerRun r)
        {
            var obs = r.Course.Obstacles;
            var next = obs.Where(o => o.Z + RunnerRun.Depth > r.Z).OrderBy(o => o.Z).FirstOrDefault();
            if (next.Z <= 0f && obs.All(o => o.Z + RunnerRun.Depth <= r.Z)) return RunAction.None;
            var row = obs.Where(o => Math.Abs(o.Z - next.Z) < 0.1f).ToList();
            var d = next.Z - r.Z;
            if (next.Lane == -1)
            {
                if (next.Kind == Hazard.Low && !r.Jumping && d < r.Speed * 0.25f + 0.6f) return RunAction.Jump;
                if (next.Kind == Hazard.High && !r.Sliding && d < r.Speed * 0.35f + 0.6f) return RunAction.Slide;
                return RunAction.None;
            }
            var blocked = new HashSet<int>(row.Select(o => o.Lane));
            if (!blocked.Contains(r.TargetLane)) return RunAction.None;
            var best = Enumerable.Range(0, RunnerCourse.Lanes).Where(l => !blocked.Contains(l)).OrderBy(l => Math.Abs(l - r.TargetLane)).First();
            return best < r.TargetLane ? RunAction.Left : RunAction.Right;
        }
    }
}
