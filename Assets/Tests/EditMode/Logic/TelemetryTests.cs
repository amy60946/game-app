using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using Pofi.Logic.Analytics;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Supabase;

namespace Pofi.Tests.Logic
{
    public class TelemetryTests
    {
        private sealed class Sink : ITelemetrySink
        {
            public TelemetrySend Next = TelemetrySend.Sent;
            public int Sessions;
            public readonly List<List<TelemetryEvent>> Batches = new List<List<TelemetryEvent>>();
            public Task<TelemetrySend> SessionAsync(string platform, string version, CancellationToken ct = default)
            {
                if (Next == TelemetrySend.Sent) Sessions++;
                return Task.FromResult(Next);
            }
            public Task<TelemetrySend> SendAsync(IReadOnlyList<TelemetryEvent> events, string platform, string version, CancellationToken ct = default)
            {
                Batches.Add(events.ToList());
                return Task.FromResult(Next);
            }
        }

        private DateTime _now = new DateTime(2026, 11, 2, 10, 0, 0, DateTimeKind.Utc);
        private Telemetry New() => new Telemetry(() => _now);

        [Test]
        public void Olay_adi_bicime_uymazsa_dusurulur()
        {
            var t = New();
            t.Track("screen.map");
            t.Track("Screen.Map");
            t.Track("ekran açıldı");
            t.Track("x");
            t.Track(null);
            Assert.AreEqual(1, t.Queued);
        }

        [Test]
        public void Serbest_metin_ve_kisisel_veri_ozelliklerde_gecmez()
        {
            var p = Telemetry.Clean(new Dictionary<string, object>
            {
                ["step"] = "feed", ["level"] = 4, ["ok"] = true, ["ms"] = 1234.567,
                ["title"] = "Odanı topla", ["name"] = "Ayşe Yılmaz", ["Upper"] = "x", ["note"] = "çok güzel yaptın!",
                ["obj"] = new object(),
            });
            CollectionAssert.AreEquivalent(new[] { "step", "level", "ok", "ms" }, p.Keys);
            Assert.AreEqual(1234.57, (double)p["ms"], 1e-9);
        }

        [Test]
        public void Ayni_olay_ust_uste_tek_satirda_sayilir()
        {
            var t = New();
            t.Track("act.pet_fed");
            t.Track("act.pet_fed");
            t.Track("act.pet_fed", new Dictionary<string, object> { ["n"] = 2 });
            t.Track("guide.step", new Dictionary<string, object> { ["step"] = "feed" });
            t.Track("guide.step", new Dictionary<string, object> { ["step"] = "feed" });
            Assert.AreEqual(3, t.Queued);
            Assert.AreEqual(4, t.Pending[0].Props["n"]);
        }

        [Test]
        public async Task Oturum_ve_olaylar_50likler_halinde_gider()
        {
            var t = New();
            for (var i = 0; i < 120; i++) t.Track("level.up", new Dictionary<string, object> { ["level"] = i });
            var s = new Sink();
            await t.FlushAsync(s, "ios", "1.0 (32)");
            Assert.AreEqual(1, s.Sessions);
            Assert.AreEqual(new[] { 50, 50, 20 }, s.Batches.Select(b => b.Count).ToArray());
            Assert.AreEqual(0, t.Queued);
            Assert.IsFalse(t.SessionPending);
            Assert.IsTrue(s.Batches.SelectMany(b => b).All(e => e.SessionId == t.SessionId && e.At.EndsWith("Z")));
        }

        [Test]
        public async Task Ag_yoksa_kuyrukta_kalir_reddedilen_atilir()
        {
            var t = New();
            t.Track("screen.map");
            var s = new Sink { Next = TelemetrySend.Retry };
            await t.FlushAsync(s, "ios", "1");
            Assert.AreEqual(1, t.Queued);
            Assert.IsTrue(t.SessionPending);
            s.Next = TelemetrySend.Drop;
            await t.FlushAsync(s, "ios", "1");
            Assert.AreEqual(0, t.Queued);
        }

        [Test]
        public void Gunluk_sinir_ve_kuyruk_siniri()
        {
            var t = New();
            for (var i = 0; i < Telemetry.DailyCap + 50; i++) t.Track("level.up", new Dictionary<string, object> { ["level"] = i });
            Assert.AreEqual(Telemetry.MaxQueue, t.Queued);
            _now = _now.AddDays(1);
            t.Track("screen.map");
            Assert.AreEqual("screen.map", t.Pending.Last().Event);
        }

        [Test]
        public void Uzun_aradan_sonra_yeni_oturum()
        {
            var t = New();
            var first = t.SessionId;
            t.Pause();
            _now = _now.AddMinutes(2);
            Assert.IsFalse(t.Resume());
            Assert.AreEqual(first, t.SessionId);
            t.Pause();
            _now = _now.AddMinutes(10);
            Assert.IsTrue(t.Resume());
            Assert.AreNotEqual(first, t.SessionId);
            Assert.IsTrue(t.SessionPending);
        }

        // ------------------------------------------------------------ sunucu çağrısı biçimi

        private sealed class FakeHttp : IHttp
        {
            public int Status = 200;
            public readonly List<(string url, string body)> Calls = new List<(string, string)>();
            public Task<HttpReply> SendAsync(string method, string url, IDictionary<string, string> headers, string body, CancellationToken ct)
            {
                Calls.Add((url, body));
                return Task.FromResult(new HttpReply { Status = Status, Body = "1" });
            }
        }

        [Test]
        public async Task Sunucuya_child_uygulamasi_olarak_track_events_gider()
        {
            var http = new FakeHttp();
            var svc = new SupabaseGameService("https://p.supabase.co", "ANON", http, () => "TOKEN", new MemorySecureStore());
            var t = New();
            t.Track("app.open", new Dictionary<string, object> { ["first_screen_ms"] = 2400, ["signed_in"] = true });
            await t.FlushAsync(svc, "ios", "1.0 (32)");
            Assert.AreEqual("https://p.supabase.co/rest/v1/rpc/track_session", http.Calls[0].url);
            var s = JObject.Parse(http.Calls[0].body);
            Assert.AreEqual("child", (string)s["p_app"]);
            Assert.AreEqual("ios", (string)s["p_platform"]);
            Assert.AreEqual("https://p.supabase.co/rest/v1/rpc/track_events", http.Calls[1].url);
            var b = JObject.Parse(http.Calls[1].body);
            Assert.AreEqual("child", (string)b["p_app"]);
            var e = b["p_events"][0];
            Assert.AreEqual("app.open", (string)e["event"]);
            Assert.AreEqual(2400, (int)e["props"]["first_screen_ms"]);
            Assert.AreEqual(t.SessionId, (string)e["session_id"]);
            Assert.AreEqual(0, t.Queued);
        }

        [Test]
        public async Task Sunucu_hatasinda_yeniden_denenir_gecersiz_istekte_atilir()
        {
            var http = new FakeHttp { Status = 503 };
            var svc = new SupabaseGameService("https://p.supabase.co", "ANON", http, () => "TOKEN", new MemorySecureStore());
            var t = New();
            t.Track("screen.map");
            await t.FlushAsync(svc, "ios", "1");
            Assert.AreEqual(1, t.Queued);
            http.Status = 200;
            await t.FlushAsync(svc, "ios", "1");
            Assert.AreEqual(0, t.Queued);
            t.Track("screen.shop");
            http.Status = 400;
            await t.FlushAsync(svc, "ios", "1");
            Assert.AreEqual(0, t.Queued);
        }
    }
}
