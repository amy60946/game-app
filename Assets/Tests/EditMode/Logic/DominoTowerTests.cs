using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Cards;

namespace Pofi.Tests.Logic
{
    public class DominoTowerTests
    {
        [Test]
        public void Domino_tiles_and_matching()
        {
            var s = DominoRules.NewGame(2, 1);
            Assert.AreEqual(28, s.Hands.Sum(h => h.Count) + s.Boneyard.Count);
            var r = new DominoRules();
            s.Hands[s.Current] = new System.Collections.Generic.List<Tile> { new Tile(3, 5), new Tile(5, 6) };
            r.Apply(s, DominoMove.Play(0, End.Left));
            Assert.AreEqual(3, s.LeftEnd); Assert.AreEqual(5, s.RightEnd);
        }

        [Test]
        public void Domino_bot_games_finish_and_conserve_tiles()
        {
            var r = new DominoRules();
            var rng = new Random(7);
            for (var g = 0; g < 200; g++)
            {
                var s = DominoRules.NewGame(2, g);
                var bots = new[] { new DominoBot(0.2f), new DominoBot(0.9f) };
                var turns = 0;
                while (!r.IsOver(s) && turns++ < 500) r.Apply(s, bots[s.Current].Choose(s, r.LegalMoves(s), rng));
                Assert.IsTrue(r.IsOver(s), $"oyun {g} bitmedi");
                Assert.AreEqual(28, s.Hands.Sum(h => h.Count) + s.Boneyard.Count + s.Line.Count);
            }
        }

        [Test]
        public void Tower_rules_forbid_top_and_unstable_pulls()
        {
            var s = TowerRules.NewGame(6, 2, 1);
            var moves = new TowerRules().LegalMoves(s);
            Assert.IsFalse(moves.Any(m => m.Layer == 5), "en üst tam kattan çekilmez");
            Assert.AreEqual(15, moves.Count);
            Assert.IsFalse(TowerRules.WouldStand(new[] { true, false, true }, 0), "tek kenar blok kalırsa kat çöker");
            Assert.IsTrue(TowerRules.WouldStand(new[] { true, true, true }, 0));
            Assert.IsTrue(TowerRules.WouldStand(new[] { true, true, false }, 0), "tek orta blok ayakta kalır");
        }

        [Test]
        public void Tower_risk_grows_with_clumsiness_and_weak_layers()
        {
            var s = TowerRules.NewGame(10, 2, 1);
            var careful = TowerRules.Risk(s, new TowerMove(3, 0), 1f);
            var clumsy = TowerRules.Risk(s, new TowerMove(3, 0), 0.2f);
            Assert.Less(careful, 0.1f);
            Assert.Greater(clumsy, careful);
            s.Layers[3][0] = false;
            Assert.Greater(TowerRules.Risk(s, new TowerMove(3, 2), 1f), careful, "tek blokla kalacak kat riskli");
        }

        [Test]
        public void Tower_games_end_with_a_loser_and_tower_grows()
        {
            var r = new TowerRules { Precision = 0.8f };
            var rng = new Random(3);
            for (var g = 0; g < 100; g++)
            {
                var s = TowerRules.NewGame(12, 2, g);
                var bot = new TowerBot(0.7f);
                var turns = 0;
                while (!r.IsOver(s) && turns++ < 300)
                {
                    var legal = r.LegalMoves(s);
                    if (legal.Count == 0) { s.LoserIndex = s.Current; break; }
                    r.Apply(s, bot.Choose(s, legal, rng));
                }
                Assert.IsTrue(r.IsOver(s));
                Assert.GreaterOrEqual(s.Layers.Count, 12);
            }
        }
    }
}
