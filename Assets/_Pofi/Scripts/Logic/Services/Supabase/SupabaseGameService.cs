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
    public sealed class SupabaseGameService : IWalletService, IWelcomeService, ITaskService, ISaveService, Rewards.IRewardService, IGoalService, Mail.IMailService
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
            return new BalanceSnapshot { Coins = (int?)o["balance"] ?? 0, SunStones = (int?)o["sun_stones"], AgeBand = (string)o["age_band"] };
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

        /// <summary>
        /// Hoş geldin coin'i (ortak claim_welcome_coins). Sunucuda işlev henüz yoksa (404) ya da geçici hata: Error dolu, çağıran
        /// sonra yeniden dener; "already_claimed" ise AlreadyClaimed (bir daha istenmez).
        /// </summary>
        public async Task<WelcomeResponse> ClaimWelcomeAsync(CancellationToken ct = default)
        {
            var r = await Rpc("claim_welcome_coins", null, ct);
            if (r.Status == 0 || r.Status >= 500 || r.Status == 408 || r.Status == 429) return new WelcomeResponse { Error = ServiceError.Network };
            if (r.Status == 401 || r.Status == 403) return new WelcomeResponse { Error = ServiceError.Unauthorized };
            if (!Ok(r)) return new WelcomeResponse { Error = ServiceError.Rejected };
            var o = JObject.Parse(r.Body);
            var ok = (bool?)o["ok"] == true;
            return new WelcomeResponse
            {
                Ok = ok, Coins = ok ? (int?)o["coins"] ?? 0 : 0, Balance = (int?)o["balance"] ?? -1,
                AlreadyClaimed = (string)o["error"] == "already_claimed", Error = ok ? ServiceError.None : ServiceError.Rejected,
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
                    Reminder = (string)o["reminder"],   // sunucu önerisi uygulanmadıysa alan yok: null
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

        // ------------------------------------------------------------ görev ekleri (ortak proposed/20261022210000, 20261022230000)

        public async Task<ServiceError> RecordBoostAsync(string taskKey, bool accepted, CancellationToken ct = default)
        {
            var sep = taskKey.IndexOf('|');
            if (sep <= 0) return ServiceError.Rejected;
            var r = await Rpc("child_record_boost", new { p_task_id = taskKey.Substring(0, sep), p_date = taskKey.Substring(sep + 1), p_choice = accepted ? "accepted" : "skipped" }, ct);
            if (r.Status == 0 || r.Status >= 500) return ServiceError.Network;
            return Ok(r) ? ServiceError.None : ServiceError.Rejected;   // 404: fonksiyon henüz yok — teklif oyunda yine çalışır
        }

        public async Task<WeeklyGoal> WeeklyGoalAsync(CancellationToken ct = default)
        {
            var r = await Rpc("child_weekly_goal", null, ct);
            if (!Ok(r)) return null;   // fonksiyon yok ya da ağ yok: pano gizli
            return ParseGoal(r.Body);
        }

        public static WeeklyGoal ParseGoal(string body)
        {
            try
            {
                var o = JObject.Parse(body);
                return new WeeklyGoal
                {
                    WeekStart = (string)o["week_start"], Target = (int?)o["target"], Done = (int?)o["done"] ?? 0,
                    Assigned = (int?)o["assigned"] ?? 0, Claimed = (bool?)o["claimed"] ?? false,
                };
            }
            catch (Newtonsoft.Json.JsonException) { return null; }
        }

        public async Task<GoalClaim> ClaimWeeklyGoalAsync(CancellationToken ct = default)
        {
            var r = await Rpc("claim_weekly_goal", null, ct);
            if (!Ok(r)) return new GoalClaim { Ok = false, Error = r.Status == 0 ? "offline" : "server" };
            try
            {
                var o = JObject.Parse(r.Body);
                return new GoalClaim { Ok = (bool?)o["ok"] ?? false, Error = (string)o["error"], Stones = (int?)o["stones"] ?? 0 };
            }
            catch (Newtonsoft.Json.JsonException) { return new GoalClaim { Ok = false, Error = "server" }; }
        }

        // ------------------------------------------------------------ gerçek ödüller (Güneş Taşı; ortak migrations/20261022130000_sun_stones_rewards)

        private Task<HttpReply> Get(string pathAndQuery, CancellationToken ct)
        {
            var h = new Dictionary<string, string> { ["apikey"] = _anonKey, ["Accept"] = "application/json" };
            var t = _token();
            if (!string.IsNullOrEmpty(t)) h["Authorization"] = "Bearer " + t;
            return _http.SendAsync("GET", _url + "/rest/v1/" + pathAndQuery, h, null, ct);
        }

        private static void Need(HttpReply r)
        {
            if (!Ok(r)) throw new OperationCanceledException(r.Status == 0 ? "çevrimdışı" : "sunucu: " + r.Status);
        }

        public async Task<Rewards.RewardsSnapshot> GetAsync(CancellationToken ct = default)
        {
            // satır güvenliği: çocuk yalnız ailesinin etkin ve kendine açık ödüllerini, kendi isteklerini ve kendi defterini görür
            var rw = await Get("rewards?select=id,title,kind,cost,unit,unit_amount,icon&order=cost.asc", ct);
            if (rw.Status == 404) return null;   // sunucuda ödüller yok: bölüm gizli kalır
            Need(rw);
            var rq = await Get("reward_requests?select=id,reward_id,title,quantity,cost,unit,amount,source,status,note,created_at&order=created_at.desc&limit=30", ct);
            Need(rq);
            var pen = await Get("sun_stone_ledger?select=id,amount,note,created_at&reason=eq.penalty&order=created_at.desc&limit=10", ct);
            Need(pen);
            var me = await Rpc("child_me", null, ct);
            Need(me);
            var snap = ParseRewards(rw.Body, rq.Body, pen.Body);
            snap.Spendable = (int?)JObject.Parse(me.Body)["sun_stones_spendable"] ?? 0;
            return snap;
        }

        public static Rewards.RewardsSnapshot ParseRewards(string rewards, string requests, string deductions)
        {
            var snap = new Rewards.RewardsSnapshot();
            foreach (var x in Rows(rewards))
                snap.Rewards.Add(new Rewards.RealReward
                {
                    Id = (string)x["id"], Title = (string)x["title"], Kind = (string)x["kind"] ?? Rewards.RewardKind.Item,
                    Cost = (int?)x["cost"] ?? 0, Unit = (string)x["unit"], UnitAmount = (int?)x["unit_amount"] ?? 0, Icon = (string)x["icon"],
                });
            foreach (var x in Rows(requests))
                snap.Requests.Add(new Rewards.RewardRequest
                {
                    Id = (string)x["id"], RewardId = (string)x["reward_id"], Title = (string)x["title"], Quantity = (int?)x["quantity"] ?? 1,
                    Cost = (int?)x["cost"] ?? 0, Unit = (string)x["unit"], Amount = (int?)x["amount"] ?? 0, Source = (string)x["source"],
                    Status = (string)x["status"], Note = (string)x["note"], CreatedAt = (string)x["created_at"],
                });
            foreach (var x in Rows(deductions))
                snap.Deductions.Add(new Rewards.StoneDeduction
                {
                    Id = (string)x["id"], Amount = Math.Abs((int?)x["amount"] ?? 0), Note = (string)x["note"], CreatedAt = (string)x["created_at"],
                });
            return snap;
        }

        private static IEnumerable<JObject> Rows(string body)
        {
            if (string.IsNullOrWhiteSpace(body)) return Enumerable.Empty<JObject>();
            try { return JToken.Parse(body) is JArray a ? a.OfType<JObject>().ToList() : Enumerable.Empty<JObject>(); }
            catch (JsonException) { return Enumerable.Empty<JObject>(); }
        }

        /// <summary>RPC hatası (raise exception): PostgREST gövdesi {code, message, hint}; hint sözleşmedeki anahtar.</summary>
        private static Rewards.RewardReply ParseReply(HttpReply r)
        {
            if (r.Status == 0 || r.Status >= 500 || r.Status == 401 || r.Status == 408 || r.Status == 429)
                return new Rewards.RewardReply { Error = Rewards.RewardReply.Network };
            if (Ok(r))
            {
                string id = null; var first = false;
                try { if (!string.IsNullOrWhiteSpace(r.Body) && JToken.Parse(r.Body) is JObject o) { id = (string)o["request_id"]; first = (bool?)o["first"] == true; } }
                catch (JsonException) { }
                return new Rewards.RewardReply { RequestId = id, First = first };
            }
            try
            {
                var o = JObject.Parse(r.Body);
                var hint = (string)o["hint"];
                var msg = (string)o["message"] ?? "";
                if (!string.IsNullOrEmpty(hint)) return new Rewards.RewardReply { Error = hint };
                if (msg.Contains("bulunamadı")) return new Rewards.RewardReply { Error = "not_found" };
            }
            catch (JsonException) { }
            return new Rewards.RewardReply { Error = "rejected" };
        }

        public async Task<Rewards.RewardReply> RequestAsync(string rewardId, int quantity, CancellationToken ct = default)
            => ParseReply(await Rpc("request_reward", new { p_reward_id = rewardId, p_quantity = Math.Max(1, quantity) }, ct));

        public async Task<Rewards.RewardReply> CancelAsync(string requestId, CancellationToken ct = default)
            => ParseReply(await Rpc("cancel_reward_request", new { p_request_id = requestId }, ct));

        // ------------------------------------------------------------ posta kutusu (H2; ortak migrations/20261022120000_messages)

        public async Task<List<Mail.MailMessage>> MessagesAsync(int limit = 100, CancellationToken ct = default)
        {
            var r = await Rpc("child_messages", new { p_limit = Math.Max(1, Math.Min(200, limit)) }, ct);
            return Ok(r) ? Mail.MailBox.Parse(r.Body) : null;   // null: ağ yok / fonksiyon yok
        }

        public async Task<int> MarkReadAsync(CancellationToken ct = default)
        {
            var r = await Rpc("mark_messages_read", null, ct);
            return Ok(r) && int.TryParse((r.Body ?? "").Trim(), out var n) ? n : 0;
        }

        public async Task<Mail.MailSend> SendAsync(string kind, string body, CancellationToken ct = default)
        {
            var r = await Rpc("child_send_message", new { p_kind = kind, p_body = body }, ct);
            if (r.Status == 0 || r.Status >= 500) return new Mail.MailSend { Error = "offline" };
            if (!Ok(r)) return new Mail.MailSend { Error = "server" };
            try { return new Mail.MailSend { Ok = true, Id = (string)JObject.Parse(r.Body)["id"] }; }
            catch (Newtonsoft.Json.JsonException) { return new Mail.MailSend { Ok = true }; }
        }

        private static readonly System.Text.RegularExpressions.Regex MediaPathRx =
            new System.Text.RegularExpressions.Regex(@"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(/[A-Za-z0-9_.\-]{1,120}){1,4}$");

        /// <summary>Posta kutusu medya yolu (sunucudan gelir; ebeveyn yazar): "aile-kimliği/…/dosya.uzantı" biçiminde mi? (güvenlik denetimi 24 Ekim 2026)</summary>
        public static bool SafeMediaPath(string p) => !string.IsNullOrEmpty(p) && p.Length <= 400 && !p.Contains("..") && MediaPathRx.IsMatch(p);

        public async Task<string> MediaUrlAsync(string mediaPath, CancellationToken ct = default)
        {
            if (!SafeMediaPath(mediaPath)) return null;   // adrese eklenmeden önce: aile klasörü + düz dosya adı, ".." ve sorgu karakteri yok
            var h = new Dictionary<string, string> { ["apikey"] = _anonKey, ["Content-Type"] = "application/json" };
            var t = _token();
            if (!string.IsNullOrEmpty(t)) h["Authorization"] = "Bearer " + t;
            var r = await _http.SendAsync("POST", _url + "/storage/v1/object/sign/mail/" + mediaPath, h, JsonConvert.SerializeObject(new { expiresIn = 600 }), ct);
            if (!Ok(r)) return null;
            try
            {
                var u = (string)JObject.Parse(r.Body)["signedURL"];
                return string.IsNullOrEmpty(u) ? null : _url + "/storage/v1" + (u.StartsWith("/") ? u : "/" + u);
            }
            catch (Newtonsoft.Json.JsonException) { return null; }
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
