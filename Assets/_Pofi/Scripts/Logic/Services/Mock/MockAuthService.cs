using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Auth;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Services.Mock
{
    /// <summary>
    /// Sahte arka uç: geliştirme ve testler için. Tanımlı kodlar tek kullanımlık değildir (deneme kolaylığı).
    /// Varsayılan kodlar: A1A1A1 (6–9), B2B2B2 (10–12), C3C3C3 (13–15).
    /// </summary>
    public sealed class MockAuthService : IAuthService
    {
        public const string SessionKey = "pofi.session";

        private readonly ISecureStore _store;
        private readonly Dictionary<string, ChildSession> _codes;
        private readonly HashSet<string> _revokedChildIds = new HashSet<string>();
        private readonly Func<DateTime> _clock;
        private readonly LoginThrottle _throttle = new LoginThrottle();
        private ChildSession _current;

        public MockAuthService(ISecureStore store, Func<DateTime> utcClock = null)
        {
            _store = store;
            _clock = utcClock ?? (() => DateTime.UtcNow);
            _codes = new Dictionary<string, ChildSession>
            {
                ["A1A1A1"] = new ChildSession("child_a", "Nazlı", AgeBand.A, "flamingo"),
                ["B2B2B2"] = new ChildSession("child_b", "Arven", AgeBand.B, "keçi"),
                ["C3C3C3"] = new ChildSession("child_c", "Deniz", AgeBand.C, "kurt"),
            };
        }

        public LoginThrottle Throttle => _throttle;

        /// <summary>Bu (normalize edilmiş) kod deneme kodlarından biri mi?</summary>
        public bool IsDemoCode(string normalized) => normalized != null && _codes.ContainsKey(normalized);

        /// <summary>Test/geliştirme: ebeveynin kodu iptal etmesini taklit eder (FR-AUTH-4).</summary>
        public void Revoke(string childId) => _revokedChildIds.Add(childId);

        public Task<ChildSession> RestoreAsync(CancellationToken ct = default)
        {
            var saved = _store.Get(SessionKey);
            if (string.IsNullOrEmpty(saved)) return Task.FromResult<ChildSession>(null);
            foreach (var s in _codes.Values)
                if (s.ChildId == saved) { _current = s; return Task.FromResult(s); }
            return Task.FromResult<ChildSession>(null);
        }

        public Task<AuthResult> SignInWithCodeAsync(string code, CancellationToken ct = default)
        {
            var now = _clock();
            if (!_throttle.CanTry(now)) return Task.FromResult(AuthResult.Fail(AuthErrorKind.Throttled));
            var normalized = ChildCode.Normalize(code);
            if (!ChildCode.IsWellFormed(normalized) || !_codes.TryGetValue(normalized, out var session)
                || _revokedChildIds.Contains(session.ChildId))
            {
                _throttle.RecordFailure(now);
                return Task.FromResult(AuthResult.Fail(AuthErrorKind.InvalidCode));
            }
            _throttle.RecordSuccess();
            _current = session;
            _store.Set(SessionKey, session.ChildId);
            return Task.FromResult(AuthResult.Success(session));
        }

        public Task<AuthErrorKind> ValidateAsync(CancellationToken ct = default)
        {
            if (_current == null) return Task.FromResult(AuthErrorKind.InvalidCode);
            return Task.FromResult(_revokedChildIds.Contains(_current.ChildId) ? AuthErrorKind.Revoked : AuthErrorKind.None);
        }

        public Task SignOutAsync(CancellationToken ct = default)
        {
            _current = null;
            _store.Delete(SessionKey);
            return Task.CompletedTask;
        }
    }
}
