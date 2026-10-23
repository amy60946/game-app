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
        public LoginThrottle Throttle => _throttle;

        /// <summary>Erişim anahtarının bitiş zamanı (UTC). Bilinmiyorsa DateTime.MinValue.</summary>
        public DateTime AccessExpiresUtc { get; private set; }

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
            var expiresAt = (long?)s["expires_at"];
            var expiresIn = (long?)s["expires_in"];
            AccessExpiresUtc = expiresAt.HasValue ? DateTimeOffset.FromUnixTimeSeconds(expiresAt.Value).UtcDateTime
                : expiresIn.HasValue ? _clock().AddSeconds(expiresIn.Value) : _clock().AddMinutes(50);
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
            if (r.Status == 0 || r.Status >= 500) return Current;   // çevrimdışı ya da geçici sunucu hatası: yerel oturumla devam (FR-AUTH-2, çevrimdışı dayanıklılık)
            if (r.Status >= 400) { Current = null; return null; }
            TakeSession(JObject.Parse(r.Body));
            return Current;
        }

        /// <summary>
        /// Erişim anahtarı (1 saat geçerli) bitmek üzereyse ya da hiç yoksa (çevrimdışı açılış) yeniler.
        /// Senkrondan önce çağrılır. Ağ yoksa false; sunucu yenilemeyi reddederse false (oturum ValidateAsync ile denetlenir).
        /// </summary>
        public async Task<bool> EnsureFreshAsync(CancellationToken ct = default)
        {
            if (Current == null) return false;
            if (AccessToken != null && _clock() < AccessExpiresUtc - TimeSpan.FromMinutes(5)) return true;
            var refresh = _store.Get(RefreshKey);
            if (string.IsNullOrEmpty(refresh)) return false;
            var r = await _http.SendAsync("POST", _url + "/auth/v1/token?grant_type=refresh_token", Headers(false),
                JsonConvert.SerializeObject(new { refresh_token = refresh }), ct);
            if (r.Status < 200 || r.Status >= 300) return false;
            TakeSession(JObject.Parse(r.Body));
            return true;
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
            if (r.Status == 429) return AuthResult.Fail(AuthErrorKind.Throttled);   // sunucu deneme sınırı (15 dk'da 10 hata)
            if (r.Status >= 400)
            {
                _throttle.RecordFailure(now);
                string reason = null;
                try { if (!string.IsNullOrWhiteSpace(r.Body) && JToken.Parse(r.Body) is JObject eo) reason = (string)eo["reason"]; }
                catch (JsonException) { }
                return AuthResult.Fail(reason == "expired" ? AuthErrorKind.CodeExpired : reason == "used" ? AuthErrorKind.CodeUsed : AuthErrorKind.InvalidCode);
            }

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
            // 401 = erişim anahtarı geçersiz/eskimiş (yenilenince düzelir); bağlantı kaldırma değildir.
            if (r.Status >= 400) return AuthErrorKind.Unknown;
            return JArray.Parse(r.Body).Count == 0 ? AuthErrorKind.Revoked : AuthErrorKind.None;
        }

        public Task SignOutAsync(CancellationToken ct = default)
        {
            AccessToken = null; UserId = null; Current = null; AccessExpiresUtc = DateTime.MinValue;
            _store.Delete(RefreshKey);
            _store.Delete(ChildKey);
            return Task.CompletedTask; // oyun kaydı silinmez (FR-AUTH-4)
        }

        /// <summary>Sunucunun bugünkü yaş grubu (child_me) değiştiyse saklanan oturum da güncellenir: uygulama yeniden açılınca eski grupla başlamasın.</summary>
        public void RememberAgeBand(string band)
        {
            if (Current == null || string.IsNullOrEmpty(band)) return;
            StoredChild stored;
            try { stored = JsonConvert.DeserializeObject<StoredChild>(_store.Get(ChildKey) ?? ""); }
            catch (JsonException) { return; }
            if (stored == null || stored.ChildId != Current.ChildId || stored.AgeBand == band) return;
            stored.AgeBand = band;
            _store.Set(ChildKey, JsonConvert.SerializeObject(stored));
            Current = stored.ToSession();
        }

        private sealed class StoredChild
        {
            public string ChildId, Name, Avatar, AgeBand;
            public ChildSession ToSession() => new ChildSession(ChildId, Name, AgeBandProfile.Parse(AgeBand), Avatar);
        }
    }
}
