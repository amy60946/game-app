using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    /// <summary>K6 A: ipuçlarını kapatma / yeniden açma ve "Nasıl oynanır" kartları.</summary>
    public class HintsTests
    {
        private static GameState New() => GameState.NewFor("c1", new DateTime(2026, 11, 2, 10, 0, 0, DateTimeKind.Utc));

        [Test]
        public void Ipuclari_varsayilan_acik_eski_kayitta_da()
        {
            Assert.IsTrue(Hints.On(New()));
            var old = SaveCodec.Deserialize(SaveCodec.Serialize(New(), DateTime.UtcNow).Replace("\"HintsOn\":true,", "").Replace(",\"HintsOn\":true", ""));
            Assert.IsTrue(Hints.On(old));
            Assert.IsTrue(Hints.On(null));
        }

        [Test]
        public void Kapatmak_rehberi_bitirmez_eylemle_ilerler()
        {
            var s = New();
            s.PetId = "pet_13"; s.PetName = "Okti";
            Hints.TurnOff(s);
            Assert.IsFalse(Hints.On(s));
            var before = Guide.DoneCount(s);
            Guide.OnActivity(s, 1, "pet_fed");
            Assert.AreEqual(before + 1, Guide.DoneCount(s));
            Assert.IsFalse(s.SeenTips.Contains(Guide.DoneFlag));
        }

        [Test]
        public void Yeniden_acinca_temel_ipuclari_bastan_rehber_ve_ilk_gun_korunur()
        {
            var s = New();
            s.SeenTips.Add(Onboarding.Walk);
            s.SeenTips.Add(Onboarding.Shop);
            s.SeenTips.Add(Onboarding.Mark);            // ilk gün akışı: yeniden gösterilmez
            s.SeenTips.Add(Guide.Prefix + "feed");       // rehber ilerlemesi korunur
            Hints.TurnOff(s);
            var n = Hints.Replay(s);
            Assert.AreEqual(2, n);
            Assert.IsTrue(Hints.On(s));
            Assert.IsTrue(Onboarding.Pending(s, Onboarding.Walk));
            Assert.IsTrue(Onboarding.Pending(s, Onboarding.Shop));
            Assert.IsFalse(Onboarding.Pending(s, Onboarding.Mark));
            Assert.IsTrue(s.SeenTips.Contains(Guide.Prefix + "feed"));
        }

        [Test]
        public void Nasil_oynanir_kartlari_ve_dugmeler_metin_tablosunda()
        {
            var loc = new Localization(TestData.ReadText("tr.json"));
            var keys = Hints.TextKeys().Concat(new[]
            {
                "album.tab.howto", "coach.skip", "coach.skip_ask", "coach.skip_yes", "coach.skip_no", "coach.skip_done",
                "howto.hints_on", "howto.hints_off", "howto.turn_off", "howto.turn_on", "howto.replayed",
            }).ToList();
            foreach (var k in keys) Assert.IsTrue(loc.Has(k), k);
            Assert.AreEqual(Hints.Cards.Count, Hints.Cards.Select(c => c.Id).Distinct().Count());
        }
    }
}
