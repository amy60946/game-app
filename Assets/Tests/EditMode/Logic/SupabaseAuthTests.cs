using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using Pofi.Logic.Profile;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Supabase;

namespace Pofi.Tests.Logic
{
    public class SupabaseAuthTests
    {
        private sealed class FakeHttp : IHttp
        {
            public readonly List<(string method, string url, string body, IDictionary<string, string> headers)> Calls =
                new List<(string, string, string, IDictionary<string, string>)>();
            public Func<string, string, HttpReply> Handler = (m, u) => new HttpReply { Status = 404, Body = "{}" };

            public Task<HttpReply> SendAsync(string method, string url, IDictionary<string, string> headers, string body, CancellationToken ct)
            {
                Calls.Add((method, url, body, headers));
                return Task.FromResult(Handler(method, url));
            }
        }

        private const string Session = "{\"access_token\":\"AT\",\"refresh_token\":\"RT\",\"user\":{\"id\":\"u1\"}}";

        [Test]
        public void Code_login_creates_anonymous_session_redeems_and_stores_refresh_token()
        {
            var http = new FakeHttp
            {
                Handler = (m, u) => u.EndsWith("/auth/v1/signup") ? new HttpReply { Status = 200, Body = Session }
                    : u.EndsWith("/rpc/redeem_child_code") ? new HttpReply { Status = 200, Body = "{\"child_id\":\"c1\",\"family_id\":\"f\",\"name\":\"Nazlı\",\"avatar\":\"flamingo\",\"age_band\":\"B\"}" }
                    : new HttpReply { Status = 404 }
            };
            var store = new MemorySecureStore();
            var auth = new SupabaseAuthService("https://x.supabase.co/", "ANON", http, store);
            var r = auth.SignInWithCodeAsync(" ab12cd ").Result;
            Assert.IsTrue(r.Ok);
            Assert.AreEqual(AgeBand.B, r.Session.AgeBand);
            Assert.AreEqual("RT", store.Get(SupabaseAuthService.RefreshKey));
            Assert.AreEqual("{\"p_code\":\"AB12CD\"}", http.Calls[1].body);
            Assert.AreEqual("Bearer AT", http.Calls[1].headers["Authorization"]);
            Assert.AreEqual("ANON", http.Calls[0].headers["apikey"]);
        }

        [Test]
        public void Missing_age_band_defaults_to_safest_band()
        {
            var http = new FakeHttp
            {
                Handler = (m, u) => u.EndsWith("/signup") ? new HttpReply { Status = 200, Body = Session }
                    : new HttpReply { Status = 200, Body = "{\"child_id\":\"c1\",\"name\":\"N\",\"avatar\":\"kedi\"}" }
            };
            var r = new SupabaseAuthService("https://x", "K", http, new MemorySecureStore()).SignInWithCodeAsync("ABCDEF").Result;
            Assert.AreEqual(AgeBand.A, r.Session.AgeBand);
        }

        [Test]
        public void Invalid_code_and_network_errors_are_friendly()
        {
            var http = new FakeHttp { Handler = (m, u) => u.EndsWith("/signup") ? new HttpReply { Status = 200, Body = Session } : new HttpReply { Status = 400, Body = "{}" } };
            var auth = new SupabaseAuthService("https://x", "K", http, new MemorySecureStore());
            Assert.AreEqual(AuthErrorKind.InvalidCode, auth.SignInWithCodeAsync("ZZZZZZ").Result.Error);
            Assert.AreEqual(AuthErrorKind.InvalidCode, auth.SignInWithCodeAsync("ZZ").Result.Error, "biçim hatası sunucuya gitmez");
            var offline = new SupabaseAuthService("https://x", "K", new FakeHttp { Handler = (m, u) => new HttpReply { Status = 0 } }, new MemorySecureStore());
            Assert.AreEqual(AuthErrorKind.Network, offline.SignInWithCodeAsync("ABCDEF").Result.Error);
        }

        [Test]
        public void Restore_works_offline_and_detects_revocation_online()
        {
            var store = new MemorySecureStore();
            store.Set(SupabaseAuthService.RefreshKey, "RT");
            store.Set(SupabaseAuthService.ChildKey, "{\"ChildId\":\"c1\",\"Name\":\"N\",\"Avatar\":\"kedi\",\"AgeBand\":\"C\"}");
            var offline = new SupabaseAuthService("https://x", "K", new FakeHttp { Handler = (m, u) => new HttpReply { Status = 0 } }, store);
            Assert.AreEqual(AgeBand.C, offline.RestoreAsync().Result.AgeBand, "çevrimdışıyken de oyun açılır");

            var http = new FakeHttp
            {
                Handler = (m, u) => u.Contains("refresh_token") ? new HttpReply { Status = 200, Body = Session }
                    : u.Contains("/children") ? new HttpReply { Status = 200, Body = "[]" } : new HttpReply { Status = 404 }
            };
            var online = new SupabaseAuthService("https://x", "K", http, store);
            Assert.IsNotNull(online.RestoreAsync().Result);
            Assert.AreEqual(AuthErrorKind.Revoked, online.ValidateAsync().Result);
            online.SignOutAsync().Wait();
            Assert.IsNull(store.Get(SupabaseAuthService.RefreshKey));
        }
    }
}
