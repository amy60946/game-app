using System;
using NUnit.Framework;
using Pofi.Logic.Pet;

namespace Pofi.Tests.Logic
{
    /// <summary>K2 B: top oyunu ritmi (20 sn ara, azalan getiri) ve okşama.</summary>
    public class PlayRhythmTests
    {
        private static readonly DateTime T0 = new DateTime(2026, 11, 3, 10, 0, 0, DateTimeKind.Utc);

        [Test]
        public void Arka_arkaya_oyun_sayilmaz_getiri_azalir_ve_dinlenince_doner()
        {
            var r = new PlayRhythm();
            Assert.AreEqual(12f, r.Take(T0));
            Assert.IsFalse(r.Ready(T0.AddSeconds(5)), "20 sn dolmadan yeni oyun sayılmaz");
            Assert.AreEqual(15, r.SecondsLeft(T0.AddSeconds(5)));
            Assert.AreEqual(0f, r.Take(T0.AddSeconds(5)));
            Assert.AreEqual(8f, r.Take(T0.AddSeconds(20)));
            Assert.AreEqual(5f, r.Take(T0.AddSeconds(45)));
            Assert.AreEqual(5f, r.Take(T0.AddSeconds(70)), "en düşük 5");
            Assert.AreEqual(12f, r.NextGain(T0.AddMinutes(12)), "10 dk ara: yeniden 12");
            Assert.AreEqual(12f, r.Take(T0.AddMinutes(12)));
        }

        [Test]
        public void Oyun_mutluluk_verir_sayilmayan_oyun_soluklanir()
        {
            var stats = new PetStats();
            var before = stats[StatKind.Happiness];
            Assert.AreEqual(CareResult.Resting, PetCare.Play(stats, T0, 0f));
            Assert.AreEqual(before, stats[StatKind.Happiness]);
            Assert.AreEqual(CareResult.Ok, PetCare.Play(stats, T0, 8f));
            Assert.Greater(stats[StatKind.Happiness], before);
        }

        [Test]
        public void Oksama_kucuk_getiri_en_sik_6_saniyede_bir()
        {
            var r = new PlayRhythm();
            Assert.AreEqual(PlayRhythm.PetHappiness, r.Pet(T0));
            Assert.AreEqual(0f, r.Pet(T0.AddSeconds(3)));
            Assert.AreEqual(PlayRhythm.PetHappiness, r.Pet(T0.AddSeconds(6)));
        }
    }
}
