using System;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Auth;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Services.Supabase;

namespace Pofi.Logic.Services
{
    /// <summary>
    /// Giriş yönlendirici (M4): deneme kodları (A1A1A1, B2B2B2, C3C3C3) sahte arka uca, diğer kodlar gerçek sunucuya gider.
    /// Sunucu ayarı yoksa her şey sahte arka uçtadır. Hangi tarafla girildiği cihazda saklanır; açılışta o taraf
    /// sessizce geri yüklenir, böylece kod yalnızca bir kez sorulur (FR-AUTH-2).
    /// </summary>
    public sealed class RoutedAuthService : IAuthService
    {
        public const string ModeKey = "pofi.auth.mode";
        private const string ServerMode = "server";
        private const string MockMode = "mock";

        private readonly ISecureStore _store;
        private readonly bool _demoCodes;

        public MockAuthService Mock { get; }
        /// <summary>Sunucu ayarı yoksa null.</summary>
        public SupabaseAuthService Server { get; }
        /// <summary>Son giriş/geri yüklemenin tarafı (henüz yoksa null).</summary>
        public IAuthService Active { get; private set; }

        public bool IsServer => Active != null && Active == Server;
        public bool IsMock => Active != null && Active == Mock;
        /// <summary>Giriş ekranında deneme kodları gösterilsin mi.</summary>
        public bool DemoCodesEnabled => _demoCodes || Server == null;

        public RoutedAuthService(MockAuthService mock, SupabaseAuthService server, ISecureStore store, bool demoCodes = true)
        {
            Mock = mock ?? throw new ArgumentNullException(nameof(mock));
            Server = server;
            _store = store;
            _demoCodes = demoCodes;
        }

        /// <summary>Bu kod hangi tarafa gider?</summary>
        public IAuthService RouteFor(string code)
        {
            if (Server == null) return Mock;
            return _demoCodes && Mock.IsDemoCode(ChildCode.Normalize(code)) ? (IAuthService)Mock : Server;
        }

        public async Task<ChildSession> RestoreAsync(CancellationToken ct = default)
        {
            var side = _store.Get(ModeKey) == ServerMode && Server != null ? (IAuthService)Server : Mock;
            var s = await side.RestoreAsync(ct);
            Active = s != null ? side : null;
            return s;
        }

        public async Task<AuthResult> SignInWithCodeAsync(string code, CancellationToken ct = default)
        {
            var side = RouteFor(code);
            var r = await side.SignInWithCodeAsync(code, ct);
            if (!r.Ok) return r;
            // Gerçek sunucuya geçerken deneme oturumu kapanır. Deneme koduna geçerken gerçek oturum belirteci SİLİNMEZ
            // (güvenlik denetimi M3: çevrimdışı açılışta giriş ekranına düşen çocuk deneme kodu yazarsa aile bağlantısı kopmasın;
            // ebeveynin yeni kod üretmesi gerekmesin).
            if (side == Server) await Mock.SignOutAsync(ct);
            Active = side;
            _store.Set(ModeKey, side == Server ? ServerMode : MockMode);
            return r;
        }

        public Task<AuthErrorKind> ValidateAsync(CancellationToken ct = default) =>
            Active != null ? Active.ValidateAsync(ct) : Task.FromResult(AuthErrorKind.InvalidCode);

        public async Task SignOutAsync(CancellationToken ct = default)
        {
            if (Active != null) await Active.SignOutAsync(ct);
            Active = null;
            _store.Delete(ModeKey);
        }

        /// <summary>Çok hatalı denemeden sonra kalan bekleme (iki tarafın büyüğü).</summary>
        public TimeSpan ThrottleRemaining(DateTime nowUtc)
        {
            var a = Mock.Throttle.Remaining(nowUtc);
            var b = Server != null ? Server.Throttle.Remaining(nowUtc) : TimeSpan.Zero;
            return a > b ? a : b;
        }
    }
}
