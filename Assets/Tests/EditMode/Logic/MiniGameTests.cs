using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.MiniGames;
using Pofi.Logic.Profile;

namespace Pofi.Tests.Logic
{
    public class MiniGameTests
    {
        [Test]
        public void Coconut_band_changes_duration_speed_and_density()
        {
            var a = new CoconutCatch(AgeBand.A, 0f, 1);
            var c = new CoconutCatch(AgeBand.C, 0.5f, 1);
            Assert.AreEqual(30000, a.DurationMs);
            Assert.AreEqual(45000, c.DurationMs);
            Assert.Greater(a.FallSeconds, c.FallSeconds);
            Assert.Greater(c.Schedule.Count / (double)c.DurationMs, a.Schedule.Count / (double)a.DurationMs);
            Assert.IsTrue(a.Schedule.All(f => f.X >= 0.08f && f.X <= 0.92f));
        }

        [Test]
        public void Coconut_xp_is_capped_per_game()
        {
            var g = new CoconutCatch(AgeBand.B, 0.5f, 3);
            var all = g.Finish(Enumerable.Range(0, g.Schedule.Count));
            Assert.LessOrEqual(all.SuggestedXp, 40);
            Assert.AreEqual(5, g.Finish(new int[0]).SuggestedXp, "hiç yakalamasa da katılım XP'si");
        }

        [Test]
        public void Help_pet_hints_get_warmer()
        {
            var s = new HelpPetSearch(AgeBand.A, 4);
            Assert.AreEqual(Warmth.Found, s.Guess(s.Hidden));
            var t = new HelpPetSearch(AgeBand.C, 9);
            var neighbour = t.Hidden % t.Columns > 0 ? t.Hidden - 1 : t.Hidden + 1;
            Assert.AreEqual(Warmth.Hot, t.Guess(neighbour));
        }

        [Test]
        public void Runner_always_has_a_reachable_path()
        {
            foreach (AgeBand band in Enum.GetValues(typeof(AgeBand)))
                for (var seed = 0; seed < 50; seed++)
                {
                    var r = new LaneRunner("minigame_surf", band, 1f, seed);
                    Assert.IsTrue(r.Rows.All(row => row.Any(x => x != RowItem.Obstacle)), "her satırda boş şerit");
                    var path = r.PerfectPath();
                    for (var i = 1; i < path.Count; i++) Assert.LessOrEqual(Math.Abs(path[i] - path[i - 1]), 1, "tek hamlede geçilebilir");
                    var res = r.Simulate(path);
                    Assert.Greater(res.Score, 0);
                }
        }

        [Test]
        public void Runner_ends_on_obstacle_without_penalty()
        {
            var r = new LaneRunner("minigame_ski", AgeBand.B, 0.5f, 2);
            var crashRow = r.Rows.FindIndex(row => row[0] == RowItem.Obstacle);
            var res = r.Simulate(Enumerable.Repeat(0, r.Rows.Count).ToList());
            Assert.GreaterOrEqual(res.SuggestedXp, 5);
            Assert.Greater(crashRow, 0);
        }
    }
}
