using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Services
{
    /// <summary>Çocuk oturumu (FR-AUTH). Kişisel veri yok: yalnızca takma ad ve yaş bandı.</summary>
    public sealed class ChildSession
    {
        public string ChildId { get; }
        public string DisplayName { get; }
        public AgeBand AgeBand { get; }
        public string Avatar { get; }

        public ChildSession(string childId, string displayName, AgeBand ageBand, string avatar)
        {
            ChildId = childId; DisplayName = displayName; AgeBand = ageBand; Avatar = avatar;
        }
    }

    public enum AuthErrorKind { None, InvalidCode, Revoked, Network, Throttled, Unknown, CodeExpired, CodeUsed }   // süresi doldu / kullanıldı: sunucu reason (ortak codes_15min)

    public sealed class AuthResult
    {
        public ChildSession Session { get; }
        public AuthErrorKind Error { get; }
        public bool Ok => Session != null;

        private AuthResult(ChildSession s, AuthErrorKind e) { Session = s; Error = e; }
        public static AuthResult Success(ChildSession s) => new AuthResult(s, AuthErrorKind.None);
        public static AuthResult Fail(AuthErrorKind e) => new AuthResult(null, e);
    }

    /// <summary>
    /// Oyun kodu yalnızca bu arayüzü bilir. Uygulamalar: MockAuthService (yerel), SupabaseAuthService (gerçek).
    /// </summary>
    public interface IAuthService
    {
        /// <summary>Kayıtlı oturum varsa sessizce geri yükler (FR-AUTH-2). Yoksa null.</summary>
        Task<ChildSession> RestoreAsync(CancellationToken ct = default);

        /// <summary>Ebeveynin ürettiği kodla giriş (FR-AUTH-1).</summary>
        Task<AuthResult> SignInWithCodeAsync(string code, CancellationToken ct = default);

        /// <summary>Oturum hâlâ geçerli mi? Kod iptal edildiyse Revoked döner (FR-AUTH-4).</summary>
        Task<AuthErrorKind> ValidateAsync(CancellationToken ct = default);

        /// <summary>Cihazdaki oturumu kapatır; yerel oyun verisi silinmez.</summary>
        Task SignOutAsync(CancellationToken ct = default);
    }
}
