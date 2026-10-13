using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Pofi.Logic.Auth;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Services.Supabase
{
    public sealed class HttpReply
    {
        public int Status;
        public string Body;
    }

    /// <summary>HTTP soyutlaması: Unity'de UnityWebRequest, testlerde sahte. Ağ hatasında Status = 0.</summary>
    public interface IHttp
    {
        Task<HttpReply> SendAsync(string method, string url, IDictionary<string, string> headers, string body, CancellationToken ct);
    }

    /// <summary>
    /// Gerçek giriş (FR-AUTH): Supabase anonim oturum + ebeveyn uygulamasındaki redeem_child_code fonksiyonu.
    /// Yenileme anahtarı cihazda güvenli saklanır; açılışta sessizce yenilenir (FR-AUTH-2).
    /// Yayınlanabilir (anon) anahtar dışında hiçbir gizli bilgi istemcide yoktur.
    /// </summary>
    public sealed class SupabaseAuthService : IAuthService
    {
        public const string RefreshKey = "pofi.refresh_token";
        public const string ChildKey = "pofi.child";

        private readonly string _url;
        private readonly string _anonKey;
        private readonly IHttp _http;
        private readonly ISecureStore _store;
        private readonly LoginThrottle _throttle = new LoginThrottle();
        private readonly Func<DateTime> _clock;

        public string AccessToken { get; private set; }
        public string UserId { get; private set; }
        public ChildSession Current { get; private set; }

        public SupabaseAuthService(string url, string anonKey, IHttp http, ISecureStore store, Func<DateTime> utcClock = null)
        {
            _url = url.TrimEnd('/');
            _anonKey = anonKey;
            _http = http;
            _store = store;
            _clock = utcClock ?? (() => DateTime.UtcNow);
        }

        private Dictionary<string, string> Headers(bool authed = true)
        {
            var h = new Dictionary<string, string> { ["apikey"] = _anonKey, ["Content-Type"] = "application/json" };
            if (authed && AccessToken != null) h["Authorization"] = "Bearer " + AccessToken;
            return h;
        }

        private void TakeSession(JObject s)
        {
            AccessToken = (string)s["access_token"];
            UserId = (string)s["user"]?["id"];
            var refresh = (string)s["refresh_token"];
            if (!string.IsNullOrEmpty(refresh)) _store.Set(RefreshKey, refresh);
        }

        public async Task<ChildSession> RestoreAsync(CancellationToken ct = default)
        {
            var refresh = _store.Get(RefreshKey);
            var child = _store.Get(ChildKey);
            if (string.IsNullOrEmpty(refresh) || string.IsNullOrEmpty(child)) return null;
            var r = await _http.SendAsync("POST", _url + "/auth/v1/token?grant_type=refresh_token", Headers(false),
                JsonConvert.SerializeObject(new { refresh_token = refresh }), ct);
            Current = JsonConvert.DeserializeObject<StoredChild>(child)?.ToSession();
            if (r.Status == 0) return Current;            // çevrimdışı: yerel oturumla devam (FR-AUTH-2, çevrimdışı dayanıklılık)
            if (r.Status >= 400) { Current = null; return null; }
            TakeSession(JObject.Parse(r.Body));
            return Current;
        }

        public async Task<AuthResult> SignInWithCodeAsync(string code, CancellationToken ct = default)
        {
            var now = _clock();
            if (!_throttle.CanTry(now)) return AuthResult.Fail(AuthErrorKind.Throttled);
            var normalized = ChildCode.Normalize(code);
            if (!ChildCode.IsWellFormed(normalized)) { _throttle.RecordFailure(now); return AuthResult.Fail(AuthErrorKind.InvalidCode); }

            if (AccessToken == null)
            {
                var anon = await _http.SendAsync("POST", _url + "/auth/v1/signup", Headers(false), "{}", ct);
                if (anon.Status == 0) return AuthResult.Fail(AuthErrorKind.Network);
                if (anon.Status >= 400) return AuthResult.Fail(AuthErrorKind.Unknown);
                TakeSession(JObject.Parse(anon.Body));
            }

            var r = await _http.SendAsync("POST", _url + "/rest/v1/rpc/redeem_child_code", Headers(),
                JsonConvert.SerializeObject(new { p_code = normalized }), ct);
            if (r.Status == 0) return AuthResult.Fail(AuthErrorKind.Network);
            if (r.Status >= 400) { _throttle.RecordFailure(now); return AuthResult.Fail(AuthErrorKind.InvalidCode); }

            _throttle.RecordSuccess();
            var o = JObject.Parse(r.Body);
            var stored = new StoredChild
            {
                ChildId = (string)o["child_id"], Name = (string)o["name"], Avatar = (string)o["avatar"],
                AgeBand = (string)o["age_band"] ?? "A",   // sütun eklenene kadar en güvenli bant
            };
            _store.Set(ChildKey, JsonConvert.SerializeObject(stored));
            Current = stored.ToSession();
            return AuthResult.Success(Current);
        }

        public async Task<AuthErrorKind> ValidateAsync(CancellationToken ct = default)
        {
            if (Current == null || AccessToken == null) return AuthErrorKind.InvalidCode;
            // RLS: çocuk yalnızca user_id'si kendisine bağlı kaydı görür. Ebeveyn bağlantıyı kaldırınca boş liste döner.
            var r = await _http.SendAsync("GET", $"{_url}/rest/v1/children?select=id&user_id=eq.{UserId}", Headers(), null, ct);
            if (r.Status == 0) return AuthErrorKind.Network;
            if (r.Status == 401) return AuthErrorKind.Revoked;
            if (r.Status >= 400) return AuthErrorKind.Unknown;
            return JArray.Parse(r.Body).Count == 0 ? AuthErrorKind.Revoked : AuthErrorKind.None;
        }

        public Task SignOutAsync(CancellationToken ct = default)
        {
            AccessToken = null; UserId = null; Current = null;
            _store.Delete(RefreshKey);
            _store.Delete(ChildKey);
            return Task.CompletedTask; // oyun kaydı silinmez (FR-AUTH-4)
        }

        private sealed class StoredChild
        {
            public string ChildId, Name, Avatar, AgeBand;
            public ChildSession ToSession() => new ChildSession(ChildId, Name, AgeBandProfile.Parse(AgeBand), Avatar);
        }
    }
}
