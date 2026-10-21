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
    public sealed class SupabaseGameService : IWalletService, ITaskService, ISaveService, Rewards.IRewardService
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

        public async Task<BalanceSnapshot> GetBalancesAsync(CancellationToken ct = default)
        {
            var r = await Rpc("child_me", null, ct);
            if (!Ok(r)) throw new OperationCanceledException(r.Status == 0 ? "çevrimdışı" : "sunucu: " + r.Status);
            var o = JObject.Parse(r.Body);
            return new BalanceSnapshot { Coins = (int?)o["balance"] ?? 0, SunStones = (int?)o["sun_stones"] };
        }

        public async Task<SpendResponse> SpendAsync(string txId, string itemId, int quantity, CancellationToken ct = default)
        {
            var r = await Rpc("spend_coins", new { p_tx = txId, p_item_id = itemId, p_quantity = quantity }, ct);
            if (r.Status == 0) return new SpendResponse { Error = ServiceError.Network };
            if (r.Status == 401 || r.Status == 403) return new SpendResponse { Error = ServiceError.Unauthorized };
            // geçici sunucu hatası (5xx, 408, 429): kuyrukta kalsın, tekrar denensin; diğer 4xx kalıcı ret (sonsuza dek takılmasın)
            if (r.Status >= 500 || r.Status == 408 || r.Status == 429) return new SpendResponse { Error = ServiceError.Network };
            if (!Ok(r)) return new SpendResponse { Error = ServiceError.Rejected, Balance = -1 };
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
                if (string.IsNullOrEmpty(date) || date.Length < 10 || string.IsNullOrEmpty((string)o["task_id"])) continue;   // bozuk satır atlanır
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
                    Skill = (string)o["skill"],
                    Difficulty = (string)o["difficulty"],
                });
            }
            return list;
        }

        public async Task<ServiceError> SetStatusAsync(string taskKey, ChildTaskStatus to, CancellationToken ct = default)
        {
            var status = StatusText(to);
            if (status == null) return ServiceError.Rejected;   // onay/ret yalnız ebeveynin: kalıcı ret, kuyruktan düşer
            var sep = taskKey.IndexOf('|');
            if (sep <= 0) return ServiceError.Rejected;
            var r = await Rpc("child_set_status", new { p_task_id = taskKey.Substring(0, sep), p_date = taskKey.Substring(sep + 1), p_status = status }, ct);
            if (r.Status == 0) return ServiceError.Network;
            if (r.Status == 401 || r.Status == 403) return ServiceError.Unauthorized;
            if (r.Status >= 500) return ServiceError.Network;
            return Ok(r) ? ServiceError.None : ServiceError.Rejected;   // ör. "Ebeveyn karar verdi": birleştirme sunucu durumunu alır
        }

        // ------------------------------------------------------------ gerçek ödüller (Ö7)

        public async Task<Rewards.RewardsSnapshot> GetAsync(CancellationToken ct = default)
        {
            var r = await Rpc("child_rewards", null, ct);
            if (r.Status == 404) return null;   // sunucuda Ö7 henüz yok: ödül bölümü gizli kalır
            if (!Ok(r)) throw new OperationCanceledException(r.Status == 0 ? "çevrimdışı" : "sunucu: " + r.Status);
            return ParseRewards(r.Body);
        }

        public static Rewards.RewardsSnapshot ParseRewards(string body)
        {
            var snap = new Rewards.RewardsSnapshot();
            if (string.IsNullOrWhiteSpace(body) || body.Trim() == "null") return snap;
            var o = JObject.Parse(body);
            snap.Balance = (int?)o["balance"] ?? 0;
            snap.Held = (int?)o["held"] ?? 0;
            snap.Available = (int?)o["available"] ?? 0;
            if (o["rewards"] is JArray rw)
                foreach (var x in rw.OfType<JObject>())
                    snap.Rewards.Add(new Rewards.RealReward { Id = (string)x["id"], Title = (string)x["title"], Icon = (string)x["icon"], Price = (int?)x["price"] ?? 0 });
            if (o["requests"] is JArray rq)
                foreach (var x in rq.OfType<JObject>())
                    snap.Requests.Add(new Rewards.RewardRequest
                    {
                        Id = (string)x["id"], RewardId = (string)x["reward_id"], Title = (string)x["title"], Icon = (string)x["icon"],
                        Price = (int?)x["price"] ?? 0, Status = (string)x["status"], RequestedAt = (string)x["requested_at"],
                    });
            return snap;
        }

        private static Rewards.RewardReply ParseReply(HttpReply r)
        {
            if (r.Status == 0 || r.Status >= 500 || r.Status == 401 || r.Status == 408 || r.Status == 429)
                return new Rewards.RewardReply { Error = Rewards.RewardReply.Network };
            if (!Ok(r)) return new Rewards.RewardReply { Error = "rejected" };
            try
            {
                var o = JObject.Parse(r.Body);
                return (bool?)o["ok"] == true ? new Rewards.RewardReply() : new Rewards.RewardReply { Error = (string)o["error"] ?? "rejected" };
            }
            catch (JsonException) { return new Rewards.RewardReply { Error = "rejected" }; }
        }

        public async Task<Rewards.RewardReply> RequestAsync(string rewardId, string txId, CancellationToken ct = default)
            => ParseReply(await Rpc("child_request_reward", new { p_reward = rewardId, p_tx = txId }, ct));

        public async Task<Rewards.RewardReply> CancelAsync(string requestId, CancellationToken ct = default)
        {
            var r = await Rpc("child_cancel_reward_request", new { p_id = requestId }, ct);
            if (!Ok(r)) return ParseReply(r);
            return r.Body != null && r.Body.Trim() == "true" ? new Rewards.RewardReply() : new Rewards.RewardReply { Error = "already_decided" };
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
