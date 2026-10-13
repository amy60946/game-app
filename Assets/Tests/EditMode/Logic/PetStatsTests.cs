using System;
using NUnit.Framework;
using Pofi.Logic.Pet;

namespace Pofi.Tests.Logic
{
    public class PetStatsTests
    {
        private static readonly DateTime T0 = new DateTime(2026, 10, 13, 8, 0, 0, DateTimeKind.Utc);
        private readonly StatDecayConfig _cfg = StatDecayConfig.Default;

        [Test]
        public void Decays_slowly_over_time()
        {
            var s = PetStats.New(T0);
            s.Tick(T0.AddHours(2), _cfg);
            Assert.AreEqual(72f, s[StatKind.Fullness], 0.01f);
        }

        [Test]
        public void Never_goes_below_floor_even_after_weeks_closed()
        {
            var s = PetStats.New(T0);
            s.Tick(T0.AddDays(30), _cfg);
            foreach (StatKind k in Enum.GetValues(typeof(StatKind)))
                Assert.AreEqual(_cfg.Floor, s[k], 0.01f, "pet asla tamamen boş kalmaz");
        }

        [Test]
        public void Daily_drop_is_capped()
        {
            var s = PetStats.New(T0);
            s.Add(StatKind.Fullness, 100f);
            s.Tick(T0.AddHours(15), _cfg); // aynı gün içinde 15 saat → 60 puanla sınırlı
            Assert.AreEqual(100f - _cfg.MaxDropPerDay, s[StatKind.Fullness], 0.01f);
        }

        [Test]
        public void Cap_resets_on_new_day()
        {
            var s = PetStats.New(T0);
            s.Add(StatKind.Fullness, 100f);
            s.Tick(T0.AddHours(15), _cfg);     // 08:00 → 23:00 : 40
            s.Tick(T0.AddHours(18), _cfg);     // ertesi gün 02:00 : +2 saat yeni gün → 32
            Assert.AreEqual(32f, s[StatKind.Fullness], 0.01f);
        }

        [Test]
        public void Clock_going_backwards_does_nothing()
        {
            var s = PetStats.New(T0);
            s.Tick(T0.AddHours(-5), _cfg);
            Assert.AreEqual(80f, s[StatKind.Happiness], 0.01f);
        }

        [Test]
        public void Actions_clamp_to_0_100_and_sadness_threshold()
        {
            var s = PetStats.New(T0);
            s.Add(StatKind.Cleanliness, 500f);
            Assert.AreEqual(100f, s[StatKind.Cleanliness]);
            s.Add(StatKind.Home, -60f);
            Assert.IsTrue(s.IsSad(StatKind.Home, _cfg));
            Assert.AreEqual(StatKind.Home, s.Lowest());
        }
    }
}
