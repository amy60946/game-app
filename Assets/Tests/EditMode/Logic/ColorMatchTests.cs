using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Cards;

namespace Pofi.Tests.Logic
{
    public class ColorMatchTests
    {
        private readonly ColorMatchRules _rules = new ColorMatchRules();

        [Test]
        public void Deck_composition()
        {
            Assert.AreEqual(108, ColorMatchRules.BuildDeck(new ColorMatchOptions()).Count);
            var bandA = ColorMatchRules.BuildDeck(ColorMatchOptions.ForBandA);
            Assert.IsFalse(bandA.Any(c => c.Kind == CardKind.DrawTwo || c.Kind == CardKind.WildDrawFour));
        }

        [Test]
        public void Matching_rules()
        {
            var s = ColorMatchRules.NewGame(new ColorMatchOptions(), 1);
            s.Discard.Add(new Card(CardColor.Red, CardKind.Number, 5));
            s.ActiveColor = CardColor.Red;
            Assert.IsTrue(ColorMatchRules.CanPlay(s, new Card(CardColor.Red, CardKind.Number, 2)));
            Assert.IsTrue(ColorMatchRules.CanPlay(s, new Card(CardColor.Blue, CardKind.Number, 5)));
            Assert.IsFalse(ColorMatchRules.CanPlay(s, new Card(CardColor.Blue, CardKind.Number, 3)));
            Assert.IsTrue(ColorMatchRules.CanPlay(s, new Card(CardColor.Wild, CardKind.Wild)));
        }

        [Test]
        public void Draw_two_gives_cards_and_skips()
        {
            var s = ColorMatchRules.NewGame(new ColorMatchOptions(), 2);
            s.Hands[0] = new List<Card> { new Card(CardColor.Green, CardKind.DrawTwo), new Card(CardColor.Green, CardKind.Number, 1) };
            s.Discard.Add(new Card(CardColor.Green, CardKind.Number, 4));
            s.ActiveColor = CardColor.Green;
            var before = s.Hands[1].Count;
            _rules.Apply(s, ColorMatchMove.Play(0));
            Assert.AreEqual(before + 2, s.Hands[1].Count);
            Assert.AreEqual(0, s.Current, "iki kişide +2 sırayı atlar");
        }

        [Test]
        public void Wild_sets_chosen_color_and_last_card_wins()
        {
            var s = ColorMatchRules.NewGame(new ColorMatchOptions(), 3);
            s.Hands[0] = new List<Card> { new Card(CardColor.Wild, CardKind.Wild), new Card(CardColor.Blue, CardKind.Number, 7) };
            _rules.Apply(s, ColorMatchMove.Play(0, CardColor.Blue));
            Assert.AreEqual(CardColor.Blue, s.ActiveColor);
            s.Current = 0;
            _rules.Apply(s, ColorMatchMove.Play(0));
            Assert.AreEqual(0, _rules.Winner(s));
        }

        [Test]
        public void Bots_always_finish_games_with_legal_moves()
        {
            var rng = new Random(42);
            var wins = new int[2];
            for (var g = 0; g < 200; g++)
            {
                var s = ColorMatchRules.NewGame(new ColorMatchOptions(), g);
                IBot<ColorMatchState, ColorMatchMove>[] bots = { new ColorMatchBot(0f), new ColorMatchBot(1f) };
                var turns = 0;
                while (!_rules.IsOver(s) && turns++ < 2000)
                {
                    var legal = _rules.LegalMoves(s);
                    _rules.Apply(s, bots[s.Current].Choose(s, legal, rng));
                }
                Assert.IsTrue(_rules.IsOver(s), $"oyun {g} bitmedi");
                wins[_rules.Winner(s)]++;
                var total = s.Hands.Sum(h => h.Count) + s.Deck.Count + s.Discard.Count;
                Assert.AreEqual(108, total, "kartlar kaybolmamalı");
            }
            Assert.Greater(wins[1], wins[0], "zor bot kolay bottan daha çok kazanmalı");
            TestContext.WriteLine($"kolay {wins[0]} – zor {wins[1]}");
        }

        [Test]
        public void Difficulty_softens_after_losses_and_rewards_losing_too()
        {
            var d = new DifficultyAdapter(0.6f);
            d.Record(false); d.Record(false);
            Assert.Less(d.Level, 0.6f);
            d.Record(true); d.Record(true);
            Assert.AreEqual(8, CardRewards.Xp(false, 1f), "kaybedince de az XP");
            Assert.Greater(CardRewards.Xp(true, 1f), CardRewards.Xp(true, 0f));
        }
    }
}
