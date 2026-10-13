using System;
using NUnit.Framework;
using Pofi.Logic.Auth;
using Pofi.Logic.Profile;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Mock;

namespace Pofi.Tests.Logic
{
    public class AuthTests
    {
        private DateTime _now = new DateTime(2026, 10, 13, 12, 0, 0, DateTimeKind.Utc);

        [Test]
        public void Code_is_normalized_and_validated()
        {
            Assert.AreEqual("AB12CD", ChildCode.Normalize(" ab 12-cd "));
            Assert.IsTrue(ChildCode.IsWellFormed("AB12CD"));
            Assert.IsFalse(ChildCode.IsWellFormed("AB12C"));
            Assert.AreEqual("", ChildCode.Normalize(null));
        }

        [Test]
        public void Turkish_dotless_i_is_not_turned_into_valid_char_silently()
        {
            // "ı" ve "İ" kodda geçemez (sunucu yalnızca A-Z0-9 üretir) → atılır, kod kısa kalır.
            Assert.AreEqual("A1A1A", ChildCode.Normalize("a1a1aı"));
        }

        [Test]
        public void Valid_code_signs_in_and_is_restored_on_next_launch()
        {
            var store = new MemorySecureStore();
            var auth = new MockAuthService(store, () => _now);
            var r = auth.SignInWithCodeAsync("b2b2b2").Result;
            Assert.IsTrue(r.Ok);
            Assert.AreEqual(AgeBand.B, r.Session.AgeBand);

            var again = new MockAuthService(store, () => _now);
            var restored = again.RestoreAsync().Result;
            Assert.IsNotNull(restored);
            Assert.AreEqual("child_b", restored.ChildId);
        }

        [Test]
        public void Too_many_wrong_codes_throttle_then_release()
        {
            var auth = new MockAuthService(new MemorySecureStore(), () => _now);
            for (var i = 0; i < 4; i++)
                Assert.AreEqual(AuthErrorKind.InvalidCode, auth.SignInWithCodeAsync("ZZZZZZ").Result.Error);
            Assert.AreEqual(AuthErrorKind.Throttled, auth.SignInWithCodeAsync("A1A1A1").Result.Error);
            _now = _now.AddSeconds(16);
            Assert.IsTrue(auth.SignInWithCodeAsync("A1A1A1").Result.Ok);
        }

        [Test]
        public void Throttle_backs_off_exponentially_with_cap()
        {
            var t = new LoginThrottle(freeAttempts: 3, baseDelaySeconds: 15, maxDelaySeconds: 60);
            for (var i = 0; i < 3; i++) t.RecordFailure(_now);
            Assert.IsTrue(t.CanTry(_now));
            t.RecordFailure(_now);
            Assert.AreEqual(15, t.Remaining(_now).TotalSeconds, 0.01);
            t.RecordFailure(_now);
            Assert.AreEqual(30, t.Remaining(_now).TotalSeconds, 0.01);
            t.RecordFailure(_now); t.RecordFailure(_now);
            Assert.AreEqual(60, t.Remaining(_now).TotalSeconds, 0.01);
        }

        [Test]
        public void Revoked_code_is_detected_and_local_progress_is_not_touched()
        {
            var store = new MemorySecureStore();
            store.Set("pofi.save", "{\"xp\":120}");
            var auth = new MockAuthService(store, () => _now);
            Assert.IsTrue(auth.SignInWithCodeAsync("A1A1A1").Result.Ok);
            auth.Revoke("child_a");
            Assert.AreEqual(AuthErrorKind.Revoked, auth.ValidateAsync().Result);
            auth.SignOutAsync().Wait();
            Assert.AreEqual("{\"xp\":120}", store.Get("pofi.save"));
        }

        [Test]
        public void Age_band_profiles_follow_spec()
        {
            Assert.IsTrue(AgeBandProfile.For(AgeBand.A).VoiceAlwaysOn);
            Assert.IsFalse(AgeBandProfile.For(AgeBand.B).VoiceAlwaysOn);
            Assert.IsTrue(AgeBandProfile.For(AgeBand.C).SubtitlesDefaultOn);
            Assert.IsFalse(AgeBandProfile.For(AgeBand.C).VoiceDefaultOn);
            Assert.AreEqual(AgeBand.A, AgeBandProfile.Parse("x"));
            Assert.AreEqual(AgeBand.C, AgeBandProfile.Parse(" c "));
        }
    }
}
