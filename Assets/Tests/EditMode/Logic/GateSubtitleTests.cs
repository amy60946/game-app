using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Audio;
using Pofi.Logic.Profile;
using Pofi.Logic.Safety;

namespace Pofi.Tests.Logic
{
    public class GateSubtitleTests
    {
        [TestCase(7, "yedi")]
        [TestCase(10, "on")]
        [TestCase(56, "elli altı")]
        [TestCase(100, "yüz")]
        [TestCase(342, "üç yüz kırk iki")]
        [TestCase(1000, "bin")]
        [TestCase(2019, "iki bin on dokuz")]
        public void Turkish_number_words(int n, string words) => Assert.AreEqual(words, TurkishNumber.ToWords(n));

        [Test]
        public void Gate_has_one_correct_option_and_written_numbers()
        {
            var rng = new Random(1);
            foreach (AgeBand band in Enum.GetValues(typeof(AgeBand)))
                for (var i = 0; i < 50; i++)
                {
                    var g = ParentGate.Create(band, rng);
                    Assert.AreEqual(4, g.Options.Distinct().Count());
                    Assert.AreEqual(1, g.Options.Count(o => o == g.Answer));
                    Assert.IsFalse(g.Prompt.Any(char.IsDigit), "rakam yok, yazıyla soru");
                }
            Assert.Greater(ParentGate.Create(AgeBand.C, new Random(2)).Answer, 100);
            for (var i = 0; i < 50; i++) Assert.Greater(ParentGate.Create(AgeBand.A, new Random(i)).Answer, 100, "L2: küçük bantta da iki basamaklı");
            var lk = new GateLock(); var now = new DateTime(2026, 10, 22, 12, 0, 0, DateTimeKind.Utc);
            lk.Fail(now); Assert.AreEqual(TimeSpan.Zero, lk.Remaining(now));
            lk.Fail(now); Assert.AreEqual(GateLock.Wait, lk.Remaining(now), "iki yanlıştan sonra bekleme");
            Assert.AreEqual(TimeSpan.Zero, lk.Remaining(now.AddSeconds(31)));
        }

        [Test]
        public void Karaoke_highlights_words_in_order_and_estimates_without_audio()
        {
            var line = new VoiceLine { Id = "hello", Text = "Merhaba ben Pofi" };
            var words = SubtitleSync.TimingsFor(line, 12f);
            Assert.AreEqual(3, words.Count);
            Assert.AreEqual(-1, SubtitleSync.ActiveWord(words, -5));
            Assert.AreEqual(0, SubtitleSync.ActiveWord(words, 10));
            Assert.AreEqual(1, SubtitleSync.ActiveWord(words, words[1].StartMs + 1));
            Assert.AreEqual(2, SubtitleSync.ActiveWord(words, 999999));
            var slowA = SubtitleSync.DurationMs(SubtitleSync.EstimateTimings(line.Text, 8f));
            Assert.Greater(slowA, SubtitleSync.DurationMs(words), "küçükler için daha yavaş okuma");
        }

        [Test]
        public void Visemes_follow_words_and_close_at_end()
        {
            var words = SubtitleSync.EstimateTimings("Merhaba ben Pofi", 12f);
            var keys = SubtitleSync.EstimateVisemes("Merhaba ben Pofi", words);
            var dur = SubtitleSync.DurationMs(words);
            Assert.AreEqual("MBP", SubtitleSync.VisemeAt(keys, words[0].StartMs + 1, dur));
            Assert.AreEqual("kapalı", SubtitleSync.VisemeAt(keys, dur + 10, dur));
        }
    }
}
