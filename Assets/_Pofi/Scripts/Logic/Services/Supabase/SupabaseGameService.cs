using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.Services.Supabase
{
    /// <summary>
    /// Gerçek sunucu (M4): cüzdan, görevler ve kayıt yedeği; supabase/proposed/20261015000000_pofi_game.sql
    /// fonksiyonlarını çağırır (child_me, child_tasks, child_set_status, spend_coins, game_save_get/put).
    /// Ağ yoksa <see cref="OperationCanceledException"/> (SyncCoordinator bunu "çevrimdışı" sayar) ya da ServiceError.Network.
    /// </summary>
    public sealed class SupabaseGameService : IWalletService, ITaskService, ISaveService
    {
        public const string LocalSaveKey = "pofi.save.local";

        private readonly string _url;
        private readonly string _anonKey;
        private readonly IHttp _http;
        private readonly Func<string> _token;
        private readonly ISecureStore _store;

        public SupabaseGameService(string url, string anonKey, IHttp http, Func<string> accessToken, ISecureStore store)
        {
            _url = url.TrimEnd('/');
            _anonKey = anonKey;
            _http = http;
            _token = accessToken;
            _store = store;
        }

        private Task<HttpReply> Rpc(string fn, object args, CancellationToken ct)
        {
            var h = new Dictionary<string, string> { ["apikey"] = _anonKey, ["Content-Type"] = "application/json" };
            var t = _token();
            if (!string.IsNullOrEmpty(t)) h["Authorization"] = "Bearer " + t;
            return _http.SendAsync("POST", _url + "/rest/v1/rpc/" + fn, h, JsonConvert.SerializeObject(args ?? new { }), ct);
        }

        private static bool Ok(HttpReply r) => r.Status >= 200 && r.Status < 300;

        // ------------------------------------------------------------ cüzdan

        public async Task<int> GetBalanceAsync(CancellationToken ct = default)
        {
            var r = await Rpc("child_me", null, ct);
            if (!Ok(r)) throw new OperationCanceledException(r.Status == 0 ? "çevrimdışı" : "sunucu: " + r.Status);
            return (int?)JObject.Parse(r.Body)["balance"] ?? 0;
        }

        public async Task<SpendResponse> SpendAsync(string txId, string itemId, int quantity, CancellationToken ct = default)
        {
            var r = await Rpc("spend_coins", new { p_tx = txId, p_item_id = itemId, p_quantity = quantity }, ct);
            if (r.Status == 0) return new SpendResponse { Error = ServiceError.Network };
            if (r.Status == 401 || r.Status == 403) return new SpendResponse { Error = ServiceError.Unauthorized };
            if (!Ok(r)) return new SpendResponse { Error = ServiceError.Network };   // geçici sunucu hatası: kuyrukta kalsın, tekrar denensin
            var o = JObject.Parse(r.Body);
            var balance = (int?)o["balance"] ?? 0;
            if ((bool?)o["ok"] == true) return new SpendResponse { Balance = balance };
            var err = (string)o["error"];
            return new SpendResponse
            {
                Balance = balance,
                Error = err == "not_enough_coins" ? ServiceError.NotEnoughCoins : err == "unknown_item" ? ServiceError.UnknownItem : ServiceError.Rejected,
            };
        }

        // ------------------------------------------------------------ görevler

        public static ChildTaskStatus ParseStatus(string s)
        {
            switch (s)
            {
                case "pending": return ChildTaskStatus.ChildDone;
                case "approved": return ChildTaskStatus.Approved;
                case "declined": return ChildTaskStatus.DeclinedByChild;
                case "rejected": return ChildTaskStatus.RejectedByParent;
                default: return ChildTaskStatus.Assigned;
            }
        }

        public static string StatusText(ChildTaskStatus s)
        {
            switch (s)
            {
                case ChildTaskStatus.ChildDone: return "pending";
                case ChildTaskStatus.DeclinedByChild: return "declined";
                case ChildTaskStatus.Assigned: return "assigned";
                default: return null;   // onay/ret yalnızca ebeveynin
            }
        }

        private static Recurrence ParseRecurrence(bool recurring, string kind)
        {
            if (!recurring) return Recurrence.Once;
            return kind == "weekly" ? Recurrence.Weekly : kind == "monthly" ? Recurrence.Monthly : Recurrence.Daily;
        }

        public async Task<List<ChildTask>> FetchAsync(string fromDate, string toDate, CancellationToken ct = default)
        {
            var r = await Rpc("child_tasks", new { p_from = fromDate, p_to = toDate }, ct);
            if (!Ok(r)) throw new OperationCanceledException(r.Status == 0 ? "çevrimdışı" : "sunucu: " + r.Status);
            var list = new List<ChildTask>();
            foreach (var o in JArray.Parse(r.Body).OfType<JObject>())
            {
                var date = (string)o["date"];
                var d = DateTime.ParseExact(date.Substring(0, 10), "yyyy-MM-dd", CultureInfo.InvariantCulture);
                list.Add(new ChildTask
                {
                    TaskId = (string)o["task_id"],
                    Date = date.Substring(0, 10),
                    Title = (string)o["title"],
                    Description = (string)o["description"],
                    RewardCoins = (int?)o["coins"] ?? 0,
                    Recurrence = ParseRecurrence((bool?)o["recurring"] ?? false, (string)o["repeat_kind"]),
                    DueLocalTicks = d.AddDays(1).AddTicks(-1).Ticks,
                    Status = ParseStatus((string)o["status"]),
                    ParentNote = (string)o["parent_note"],
                });
            }
            return list;
        }

        public async Task<ServiceError> SetStatusAsync(string taskKey, ChildTaskStatus to, CancellationToken ct = default)
        {
            var status = StatusText(to);
            if (status == null) return ServiceError.Unauthorized;
            var sep = taskKey.IndexOf('|');
            if (sep <= 0) return ServiceError.Rejected;
            var r = await Rpc("child_set_status", new { p_task_id = taskKey.Substring(0, sep), p_date = taskKey.Substring(sep + 1), p_status = status }, ct);
            if (r.Status == 0) return ServiceError.Network;
            if (r.Status == 401 || r.Status == 403) return ServiceError.Unauthorized;
            if (r.Status >= 500) return ServiceError.Network;
            return Ok(r) ? ServiceError.None : ServiceError.Rejected;   // ör. "Ebeveyn karar verdi": birleştirme sunucu durumunu alır
        }

        // ------------------------------------------------------------ kayıt

        public Task<string> LoadLocalAsync(CancellationToken ct = default) => Task.FromResult(_store.Get(LocalSaveKey));

        public Task SaveLocalAsync(string json, CancellationToken ct = default)
        {
            _store.Set(LocalSaveKey, json);
            return Task.CompletedTask;
        }

        /// <summary>Sunucudaki yedek; yedek yoksa null. Ağ/sunucu hatasında <see cref="OperationCanceledException"/>
        /// (çağıran "yedek yok" ile "ulaşılamadı"yı ayırır: ulaşılamazsa yerel kayıt sunucudakinin üstüne yazılmaz).</summary>
        public async Task<string> LoadRemoteAsync(CancellationToken ct = default)
        {
            var r = await Rpc("game_save_get", null, ct);
            if (!Ok(r)) throw new OperationCanceledException(r.Status == 0 ? "çevrimdışı" : "sunucu: " + r.Status);
            if (string.IsNullOrWhiteSpace(r.Body) || r.Body.Trim() == "null") return null;
            return r.Body;
        }

        public async Task<ServiceError> SaveRemoteAsync(string json, CancellationToken ct = default)
        {
            JToken data;
            try { data = JToken.Parse(json); }
            catch (JsonException) { return ServiceError.Rejected; }
            var r = await Rpc("game_save_put", new { p_data = data }, ct);
            if (r.Status == 0 || r.Status >= 500) return ServiceError.Network;
            return Ok(r) ? ServiceError.None : ServiceError.Rejected;
        }
    }
}
