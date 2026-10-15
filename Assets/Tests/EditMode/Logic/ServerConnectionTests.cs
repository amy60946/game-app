using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using Pofi.Logic.Profile;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.Services.Supabase;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    /// <summary>M4: sunucu ayarı, deneme/gerçek kod yönlendirmesi, anahtar yenileme ve kayıt yedeğinden geri yükleme.</summary>
    public class ServerConnectionTests
    {
        private sealed class FakeHttp : IHttp
        {
            public readonly List<string> Urls = new List<string>();
            public Func<string, HttpReply> Handler = u => new HttpReply { Status = 404, Body = "{}" };
            public Task<HttpReply> SendAsync(string method, string url, IDictionary<string, string> headers, string body, CancellationToken ct)
            {
                Urls.Add(url);
                return Task.FromResult(Handler(url));
            }
        }

        private static string Jwt(string role)
        {
            string B64(string s) => Convert.ToBase64String(Encoding.UTF8.GetBytes(s)).TrimEnd('=').Replace('+', '-').Replace('/', '_');
            return B64("{\"alg\":\"HS256\"}") + "." + B64("{\"iss\":\"supabase\",\"role\":\"" + role + "\"}") + ".imza";
        }

        private DateTime _now = new DateTime(2026, 10, 15, 12, 0, 0, DateTimeKind.Utc);

        private const string Session = "{\"access_token\":\"AT\",\"refresh_token\":\"RT\",\"expires_in\":3600,\"user\":{\"id\":\"u1\"}}";
        private const string Redeemed = "{\"child_id\":\"c-real\",\"family_id\":\"f\",\"name\":\"Efe\",\"avatar\":\"kedi\",\"age_band\":\"B\"}";

        private static FakeHttp ServerOk() => new FakeHttp
        {
            Handler = u => u.EndsWith("/signup") || u.Contains("refresh_token") ? new HttpReply { Status = 200, Body = Session }
                : u.EndsWith("/rpc/redeem_child_code") ? new HttpReply { Status = 200, Body = Redeemed }
                : new HttpReply { Status = 404, Body = "{}" }
        };

        // ------------------------------------------------------------ ayar

        [Test]
        public void Empty_or_broken_config_means_mock()
        {
            Assert.IsFalse(ServerConfig.Parse(null).IsConfigured);
            Assert.IsFalse(ServerConfig.Parse("{ bozuk").IsConfigured);
            Assert.IsFalse(ServerConfig.Parse("{\"url\":\"https://p.supabase.co\",\"publishableKey\":\"\"}").IsConfigured);
            Assert.IsFalse(ServerConfig.Parse("{\"url\":\"http://p.supabase.co\",\"publishableKey\":\"sb_publishable_x\"}").IsConfigured, "https şart");
            var ok = ServerConfig.Parse("{\"url\":\" https://p.supabase.co \",\"publishableKey\":\"sb_publishable_abc\"}");
            Assert.IsTrue(ok.IsConfigured);
            Assert.AreEqual("https://p.supabase.co", ok.Url);
            Assert.IsTrue(ok.DemoCodes, "deneme kodları varsayılan açık");
        }

        [Test]
        public void Secret_keys_are_never_accepted()
        {
            Assert.IsTrue(ServerConfig.LooksSecret("sb_secret_abc"));
            Assert.IsTrue(ServerConfig.LooksSecret(Jwt("service_role")));
            Assert.IsFalse(ServerConfig.LooksSecret(Jwt("anon")));
            Assert.IsFalse(ServerConfig.LooksSecret("sb_publishable_abc"));
            Assert.IsFalse(ServerConfig.Parse("{\"url\":\"https://p.supabase.co\",\"publishableKey\":\"" + Jwt("service_role") + "\"}").IsConfigured);
            Assert.IsTrue(ServerConfig.Parse("{\"url\":\"https://p.supabase.co\",\"publishableKey\":\"" + Jwt("anon") + "\"}").IsConfigured);
        }

        // ------------------------------------------------------------ yönlendirme

        [Test]
        public async Task Demo_codes_go_to_mock_real_codes_go_to_server()
        {
            var store = new MemorySecureStore();
            var http = ServerOk();
            var router = new RoutedAuthService(new MockAuthService(store, () => _now),
                new SupabaseAuthService("https://p.supabase.co", "K", http, store, () => _now), store);

            var demo = await router.SignInWithCodeAsync("a1a1a1");
            Assert.IsTrue(demo.Ok);
            Assert.IsTrue(router.IsMock);
            Assert.AreEqual(0, http.Urls.Count, "deneme kodu sunucuya gitmez");

            var real = await router.SignInWithCodeAsync("XK7P2Q");
            Assert.IsTrue(real.Ok);
            Assert.IsTrue(router.IsServer);
            Assert.AreEqual("c-real", real.Session.ChildId);
            Assert.IsNull(store.Get(MockAuthService.SessionKey), "eski deneme oturumu kapandı");

            // Uygulama yeniden açılır: kod tekrar sorulmaz, gerçek oturum geri gelir.
            var again = new RoutedAuthService(new MockAuthService(store, () => _now),
                new SupabaseAuthService("https://p.supabase.co", "K", ServerOk(), store, () => _now), store);
            var restored = await again.RestoreAsync();
            Assert.AreEqual("c-real", restored.ChildId);
            Assert.AreEqual(AgeBand.B, restored.AgeBand);
            Assert.IsTrue(again.IsServer);
        }

        [Test]
        public async Task Without_server_everything_is_mock_and_old_sessions_restore()
        {
            var store = new MemorySecureStore();
            var mock = new MockAuthService(store, () => _now);
            await mock.SignInWithCodeAsync("B2B2B2");     // M4 öncesi kurulum: yalnız sahte oturum kayıtlı

            var router = new RoutedAuthService(new MockAuthService(store, () => _now), null, store);
            Assert.AreEqual("child_b", (await router.RestoreAsync()).ChildId);
            Assert.IsTrue(router.IsMock);
            Assert.IsTrue(router.DemoCodesEnabled);
            Assert.AreEqual(AuthErrorKind.InvalidCode, (await router.SignInWithCodeAsync("XK7P2Q")).Error);
        }

        [Test]
        public async Task Demo_codes_can_be_disabled_for_real_builds()
        {
            var store = new MemorySecureStore();
            var http = new FakeHttp { Handler = u => u.EndsWith("/signup") ? new HttpReply { Status = 200, Body = Session } : new HttpReply { Status = 400, Body = "{}" } };
            var router = new RoutedAuthService(new MockAuthService(store, () => _now),
                new SupabaseAuthService("https://p.supabase.co", "K", http, store, () => _now), store, demoCodes: false);
            Assert.IsFalse(router.DemoCodesEnabled);
            Assert.AreEqual(AuthErrorKind.InvalidCode, (await router.SignInWithCodeAsync("A1A1A1")).Error);
            Assert.IsTrue(http.Urls.Any(u => u.EndsWith("/rpc/redeem_child_code")), "kod sunucuya gitti");
        }

        [Test]
        public async Task Sign_out_forgets_side_but_keeps_nothing_dangling()
        {
            var store = new MemorySecureStore();
            var router = new RoutedAuthService(new MockAuthService(store, () => _now),
                new SupabaseAuthService("https://p.supabase.co", "K", ServerOk(), store, () => _now), store);
            await router.SignInWithCodeAsync("XK7P2Q");
            await router.SignOutAsync();
            Assert.IsNull(store.Get(RoutedAuthService.ModeKey));
            Assert.IsNull(store.Get(SupabaseAuthService.RefreshKey));
            Assert.IsNull(await router.RestoreAsync());
        }

        // ------------------------------------------------------------ anahtar yenileme / bağlantı kaldırma

        [Test]
        public async Task Access_token_is_refreshed_only_when_about_to_expire()
        {
            var store = new MemorySecureStore();
            var http = ServerOk();
            var auth = new SupabaseAuthService("https://p.supabase.co", "K", http, store, () => _now);
            await auth.SignInWithCodeAsync("XK7P2Q");
            var calls = http.Urls.Count;

            Assert.IsTrue(await auth.EnsureFreshAsync());
            Assert.AreEqual(calls, http.Urls.Count, "taze anahtar: istek yok");

            _now = _now.AddMinutes(58);
            Assert.IsTrue(await auth.EnsureFreshAsync());
            Assert.IsTrue(http.Urls.Last().Contains("grant_type=refresh_token"));
            Assert.AreEqual(_now.AddSeconds(3600), auth.AccessExpiresUtc);
        }

        [Test]
        public async Task Expired_token_is_not_mistaken_for_revocation()
        {
            var store = new MemorySecureStore();
            var http = ServerOk();
            var auth = new SupabaseAuthService("https://p.supabase.co", "K", http, store, () => _now);
            await auth.SignInWithCodeAsync("XK7P2Q");
            http.Handler = u => new HttpReply { Status = 401, Body = "{}" };
            Assert.AreNotEqual(AuthErrorKind.Revoked, await auth.ValidateAsync());
        }

        [Test]
        public async Task Server_hiccup_on_restore_keeps_session()
        {
            var store = new MemorySecureStore();
            await new SupabaseAuthService("https://p", "K", ServerOk(), store, () => _now).SignInWithCodeAsync("XK7P2Q");
            var flaky = new SupabaseAuthService("https://p", "K", new FakeHttp { Handler = u => new HttpReply { Status = 503 } }, store, () => _now);
            Assert.IsNotNull(await flaky.RestoreAsync(), "geçici sunucu hatasında kod yeniden sorulmaz");
        }

        // ------------------------------------------------------------ kayıt yedeği

        private static GameState Pet(string child, long ticks) =>
            new GameState { ChildId = child, PetId = "pet_03", PetName = "Pofi", LastSavedUtcTicks = ticks };

        [Test]
        public void Remote_backup_wins_on_new_device_or_when_newer()
        {
            Assert.IsTrue(SaveRestore.PreferRemote(Pet("c1", 10), "c1", localHasPet: false, localSavedUtcTicks: 0), "yeni telefon");
            Assert.IsTrue(SaveRestore.PreferRemote(Pet("c1", 20), "c1", true, 10), "başka cihazda daha yeni");
            Assert.IsFalse(SaveRestore.PreferRemote(Pet("c1", 10), "c1", true, 20), "yerel daha yeni");
            Assert.IsFalse(SaveRestore.PreferRemote(Pet("c2", 99), "c1", false, 0), "başka çocuğun kaydı");
            Assert.IsFalse(SaveRestore.PreferRemote(new GameState { ChildId = "c1", LastSavedUtcTicks = 99 }, "c1", false, 0), "petsiz yedek işe yaramaz");
            Assert.IsFalse(SaveRestore.PreferRemote(null, "c1", false, 0));
        }

        [Test]
        public async Task Unreachable_backup_is_not_treated_as_missing()
        {
            var offline = new SupabaseGameService("https://p", "K", new FakeHttp { Handler = u => new HttpReply { Status = 0 } }, () => "T", new MemorySecureStore());
            var r = await SaveRestore.CheckAsync(offline, "c1", false, 0);
            Assert.IsFalse(r.Reached, "ulaşılamadı: senkron yerel kaydı sunucuya yazmasın");

            var empty = new SupabaseGameService("https://p", "K", new FakeHttp { Handler = u => new HttpReply { Status = 200, Body = "null" } }, () => "T", new MemorySecureStore());
            r = await SaveRestore.CheckAsync(empty, "c1", false, 0);
            Assert.IsTrue(r.Reached);
            Assert.IsNull(r.Adopt);

            var json = SaveCodec.Serialize(Pet("c1", 0), new DateTime(2026, 10, 14, 0, 0, 0, DateTimeKind.Utc));
            var backup = new SupabaseGameService("https://p", "K", new FakeHttp { Handler = u => new HttpReply { Status = 200, Body = json } }, () => "T", new MemorySecureStore());
            r = await SaveRestore.CheckAsync(backup, "c1", false, 0);
            Assert.AreEqual("pet_03", r.Adopt.PetId);
        }
    }
}
