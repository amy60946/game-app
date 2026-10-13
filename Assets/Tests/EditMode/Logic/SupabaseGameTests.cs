using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Supabase;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    public class SupabaseGameTests
    {
        private sealed class FakeHttp : IHttp
        {
            public Func<string, JObject, HttpReply> Handler;
            public readonly List<(string url, string body, string auth)> Calls = new List<(string, string, string)>();
            public Task<HttpReply> SendAsync(string method, string url, IDictionary<string, string> headers, string body, CancellationToken ct)
            {
                headers.TryGetValue("Authorization", out var auth);
                Calls.Add((url, body, auth));
                var fn = url.Substring(url.LastIndexOf('/') + 1);
                return Task.FromResult(Handler(fn, string.IsNullOrEmpty(body) ? new JObject() : JObject.Parse(body)));
            }
        }

        private static HttpReply R(int status, string body) => new HttpReply { Status = status, Body = body };

        private static SupabaseGameService Svc(FakeHttp http) =>
            new SupabaseGameService("https://p.supabase.co/", "ANON", http, () => "TOKEN", new MemorySecureStore());

        [Test]
        public async Task Gorevler_sunucu_bicimiinden_okunur_ve_durum_eslenir()
        {
            var http = new FakeHttp
            {
                Handler = (fn, args) => fn == "child_tasks"
                    ? R(200, @"[{""task_id"":""t1"",""date"":""2026-10-14"",""title"":""Odanı topla"",""description"":"""",""coins"":10,""recurring"":true,""repeat_kind"":""weekly"",""status"":""rejected"",""parent_note"":""Dağınık""},
                                {""task_id"":""t2"",""date"":""2026-10-14"",""title"":""Dişler"",""description"":null,""coins"":5,""recurring"":false,""repeat_kind"":""daily"",""status"":""assigned"",""parent_note"":null}]")
                    : R(200, "null"),
            };
            var list = await Svc(http).FetchAsync("2026-10-13", "2026-10-20");
            Assert.AreEqual(2, list.Count);
            Assert.AreEqual("t1|2026-10-14", list[0].Key);
            Assert.AreEqual(ChildTaskStatus.RejectedByParent, list[0].Status);
            Assert.AreEqual("Dağınık", list[0].ParentNote);
            Assert.AreEqual(Recurrence.Weekly, list[0].Recurrence);
            Assert.AreEqual(Recurrence.Once, list[1].Recurrence);
            Assert.AreEqual(new DateTime(2026, 10, 14, 23, 59, 59).Ticks, new DateTime(list[1].DueLocalTicks).AddTicks(-(list[1].DueLocalTicks % TimeSpan.TicksPerSecond)).Ticks);
            Assert.AreEqual("Bearer TOKEN", http.Calls[0].auth);
            Assert.AreEqual("https://p.supabase.co/rest/v1/rpc/child_tasks", http.Calls[0].url);
            StringAssert.Contains("\"p_from\":\"2026-10-13\"", http.Calls[0].body);
        }

        [Test]
        public async Task Durum_gonderimi_ve_hata_eslemesi()
        {
            var http = new FakeHttp { Handler = (fn, a) => (string)a["p_status"] == "pending" ? R(200, "\"pending\"") : R(400, "{\"message\":\"Ebeveyn karar verdi\"}") };
            var svc = Svc(http);
            Assert.AreEqual(ServiceError.None, await svc.SetStatusAsync("t1|2026-10-14", ChildTaskStatus.ChildDone));
            StringAssert.Contains("\"p_task_id\":\"t1\"", http.Calls[0].body);
            StringAssert.Contains("\"p_date\":\"2026-10-14\"", http.Calls[0].body);
            Assert.AreEqual(ServiceError.Rejected, await svc.SetStatusAsync("t1|2026-10-14", ChildTaskStatus.Assigned));
            Assert.AreEqual(ServiceError.Unauthorized, await svc.SetStatusAsync("t1|2026-10-14", ChildTaskStatus.Approved));
            Assert.AreEqual(1 + 1, http.Calls.Count);   // onay isteği sunucuya hiç gitmez
            var offline = Svc(new FakeHttp { Handler = (f, a) => R(0, null) });
            Assert.AreEqual(ServiceError.Network, await offline.SetStatusAsync("t1|2026-10-14", ChildTaskStatus.ChildDone));
        }

        [Test]
        public async Task Harcama_yanitlari()
        {
            var http = new FakeHttp
            {
                Handler = (fn, a) => (string)a["p_item_id"] == "glasses_round"
                    ? R(200, "{\"ok\":true,\"error\":null,\"balance\":5}")
                    : R(200, "{\"ok\":false,\"error\":\"not_enough_coins\",\"balance\":5}"),
            };
            var svc = Svc(http);
            var ok = await svc.SpendAsync("tx12345678", "glasses_round", 1);
            Assert.AreEqual(ServiceError.None, ok.Error);
            Assert.AreEqual(5, ok.Balance);
            Assert.AreEqual(ServiceError.NotEnoughCoins, (await svc.SpendAsync("tx12345679", "home_bed", 1)).Error);
            Assert.AreEqual(ServiceError.Network, (await Svc(new FakeHttp { Handler = (f, a) => R(503, "") }).SpendAsync("tx1234567a", "x", 1)).Error);
        }

        [Test]
        public async Task Senkron_koordinatoru_gercek_istemciyle_calisir()
        {
            var data = TestData.Load();
            var server = new Dictionary<string, string> { ["t1|2026-10-14"] = "assigned" };
            var balance = 0;
            var http = new FakeHttp
            {
                Handler = (fn, a) =>
                {
                    switch (fn)
                    {
                        case "child_set_status":
                            server[(string)a["p_task_id"] + "|" + (string)a["p_date"]] = (string)a["p_status"];
                            return R(200, "\"ok\"");
                        case "child_tasks":
                            return R(200, "[" + string.Join(",", server.Select(kv =>
                                $"{{\"task_id\":\"{kv.Key.Split('|')[0]}\",\"date\":\"{kv.Key.Split('|')[1]}\",\"title\":\"T\",\"coins\":10,\"recurring\":false,\"status\":\"{kv.Value}\"}}")) + "]");
                        case "child_me": return R(200, "{\"balance\":" + balance + "}");
                        default: return R(204, "");
                    }
                },
            };
            var svc = Svc(http);
            var sync = new SyncCoordinator(svc, svc, svc, data);
            var local = new DateTime(2026, 10, 14, 10, 0, 0);
            var s = GameState.NewFor("c", DateTime.UtcNow);
            await sync.SyncAsync(s, local, DateTime.UtcNow);
            Assert.AreEqual(1, s.Tasks.Tasks.Count);
            s.Tasks.Mark("t1|2026-10-14", ChildTaskStatus.ChildDone, local, DateTime.UtcNow);
            await sync.SyncAsync(s, local, DateTime.UtcNow);
            Assert.AreEqual("pending", server["t1|2026-10-14"]);
            server["t1|2026-10-14"] = "approved";   // ebeveyn onayladı
            balance = 10;
            var rep = await sync.SyncAsync(s, local, DateTime.UtcNow);
            Assert.AreEqual(10, rep.CoinsEarned);
            Assert.AreEqual(ChildTaskStatus.Approved, s.Tasks.Tasks[0].Status);
            Assert.IsTrue(http.Calls.Any(c => c.url.EndsWith("game_save_put")));

            var offline = new SupabaseGameService("https://p", "A", new FakeHttp { Handler = (f, a) => R(0, null) }, () => "T", new MemorySecureStore());
            var rep2 = await new SyncCoordinator(offline, offline, offline, data).SyncAsync(s, local, DateTime.UtcNow);
            Assert.IsTrue(rep2.Offline);
        }
    }
}
