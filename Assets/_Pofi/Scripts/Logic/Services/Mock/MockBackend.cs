using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Data;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.Services.Mock
{
    /// <summary>
    /// Sahte sunucu: cüzdan, görevler ve kayıt yedeği. Gerçek Supabase davranışını taklit eder:
    /// fiyat sunucuda (oyun verisinden) okunur, harcama idempotenttir, coin yalnızca ebeveyn onayıyla artar.
    /// Geliştirmede "ebeveyn" işlemleri (görev ata, onayla, reddet) bu sınıftan çağrılır.
    /// </summary>
    public sealed class MockBackend : IWalletService, ITaskService, ISaveService, Rewards.IRewardService
    {
        private readonly GameData _data;
        private readonly Dictionary<string, int> _processedTx = new Dictionary<string, int>(); // txId → tutar
        private readonly List<ChildTask> _tasks = new List<ChildTask>();
        private string _remoteSave;
        private string _localSave;

        public int Coins { get; private set; }
        public int SunStones { get; private set; }
        public bool Offline { get; set; }

        public MockBackend(GameData data, int startCoins = 0)
        {
            _data = data;
            Coins = startCoins;
        }

        public IReadOnlyCollection<string> ProcessedTxIds => _processedTx.Keys;

        // ---------- "ebeveyn" tarafı (geliştirme) ----------

        public ChildTask ParentAssign(string taskId, string date, string title, int coins, Recurrence rec = Recurrence.Once,
            string skill = null, string difficulty = "easy")
        {
            var d = DateTime.ParseExact(date, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            var t = new ChildTask
            {
                TaskId = taskId, Date = date, Title = title, RewardCoins = Math.Max(1, Math.Min(50, coins)), Recurrence = rec,
                DueLocalTicks = d.AddDays(1).AddTicks(-1).Ticks, Status = ChildTaskStatus.Assigned,
                Skill = skill, Difficulty = difficulty ?? "easy",
            };
            _tasks.Add(t);
            return t;
        }

        /// <summary>Yalnız önizleme test erişimi (TestAccess): sahte arka uçta bakiye ekler.</summary>
        public void TestGrantCoins(int coins) => Coins += Math.Max(0, coins);

        public void ParentApprove(string key, string note = null)
        {
            var t = _tasks.First(x => x.Key == key);
            if (t.Status != ChildTaskStatus.ChildDone) throw new InvalidOperationException("Yalnızca çocuğun yaptım dediği görev onaylanır");
            t.Status = ChildTaskStatus.Approved;
            t.ParentNote = note;
            Coins += t.RewardCoins; // coin YALNIZCA burada artar
            SunStones += StonesFor(t.Difficulty);   // Güneş Taşı da (sunucu: stones_for_difficulty)
        }

        public static int StonesFor(string difficulty) => difficulty == "hard" ? 3 : difficulty == "medium" ? 2 : 1;

        /// <summary>Yalnız önizleme test erişimi: sahte arka uçta Güneş Taşı ekler.</summary>
        public void TestGrantStones(int n) => SunStones += Math.Max(0, n);

        public void ParentReject(string key, string note)
        {
            var t = _tasks.First(x => x.Key == key);
            t.Status = ChildTaskStatus.RejectedByParent;
            t.ParentNote = note;
        }

        // ---------- IWalletService ----------

        public Task<int> GetBalanceAsync(CancellationToken ct = default)
        {
            if (Offline) throw new OperationCanceledException("çevrimdışı");
            return Task.FromResult(Coins);
        }

        public Task<BalanceSnapshot> GetBalancesAsync(CancellationToken ct = default)
        {
            if (Offline) throw new OperationCanceledException("çevrimdışı");
            return Task.FromResult(new BalanceSnapshot { Coins = Coins, SunStones = SunStones });
        }

        public Task<SpendResponse> SpendAsync(string txId, string itemId, int quantity, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new SpendResponse { Error = ServiceError.Network, Balance = Coins });
            if (_processedTx.ContainsKey(txId)) return Task.FromResult(new SpendResponse { Balance = Coins });
            var item = _data.Item(itemId);
            if (item == null || quantity <= 0 || quantity > 20) return Task.FromResult(new SpendResponse { Error = ServiceError.UnknownItem, Balance = Coins });
            var amount = item.Price * quantity;
            // ödüle ayrılan coin harcanmaz (sunucu spend_coins ile aynı)
            if (amount > Coins - Held) return Task.FromResult(new SpendResponse { Error = ServiceError.NotEnoughCoins, Balance = Coins });
            Coins -= amount;
            _processedTx[txId] = amount;
            return Task.FromResult(new SpendResponse { Balance = Coins });
        }

        // ---------- gerçek ödüller (Ö7; sunucu kuralları: en çok 3 bekleyen, coin ayrılır, verince düşer) ----------

        private readonly List<Rewards.RealReward> _rewards = new List<Rewards.RealReward>();
        private readonly List<Rewards.RewardRequest> _requests = new List<Rewards.RewardRequest>();
        private readonly Dictionary<string, string> _requestTx = new Dictionary<string, string>();   // tx → istek

        public IReadOnlyList<Rewards.RewardRequest> RewardRequests => _requests;

        public void ParentAddReward(string id, string title, string icon, int price)
        {
            _rewards.RemoveAll(r => r.Id == id);
            _rewards.Add(new Rewards.RealReward { Id = id, Title = title, Icon = icon, Price = Math.Max(1, Math.Min(500, price)) });
        }

        private int Held => _requests.Where(q => q.Status == Rewards.RewardStatus.Pending).Sum(q => q.Price);

        /// <summary>Ebeveyn kararı. Verince coin düşer; bakiye yetmezse istek bekler (false).</summary>
        public bool ParentDecideReward(string requestId, bool give)
        {
            var q = _requests.FirstOrDefault(x => x.Id == requestId && x.Status == Rewards.RewardStatus.Pending);
            if (q == null) return false;
            if (give)
            {
                if (Coins < q.Price) return false;
                Coins -= q.Price;
            }
            q.Status = give ? Rewards.RewardStatus.Given : Rewards.RewardStatus.Declined;
            return true;
        }

        public Task<Rewards.RewardsSnapshot> GetAsync(CancellationToken ct = default)
        {
            if (Offline) throw new OperationCanceledException("çevrimdışı");
            var held = Held;
            return Task.FromResult(new Rewards.RewardsSnapshot
            {
                Balance = Coins, Held = held, Available = Math.Max(0, Coins - held),
                Rewards = _rewards.Select(r => new Rewards.RealReward { Id = r.Id, Title = r.Title, Icon = r.Icon, Price = r.Price }).OrderBy(r => r.Price).ToList(),
                Requests = Enumerable.Reverse(_requests).Take(20).Select(CloneReq).ToList(),
            });
        }

        public Task<Rewards.RewardReply> RequestAsync(string rewardId, string txId, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new Rewards.RewardReply { Error = Rewards.RewardReply.Network });
            if (string.IsNullOrEmpty(txId) || txId.Length < 8 || txId.Length > 64) return Task.FromResult(new Rewards.RewardReply { Error = "rejected" });
            if (_requestTx.ContainsKey(txId)) return Task.FromResult(new Rewards.RewardReply());
            var r = _rewards.FirstOrDefault(x => x.Id == rewardId);
            if (r == null) return Task.FromResult(new Rewards.RewardReply { Error = "unknown_reward" });
            if (_requests.Count(q => q.Status == Rewards.RewardStatus.Pending) >= Rewards.RewardBook.MaxPending)
                return Task.FromResult(new Rewards.RewardReply { Error = "too_many_pending" });
            if (_requests.Any(q => q.RewardId == r.Id && q.Status == Rewards.RewardStatus.Pending))
                return Task.FromResult(new Rewards.RewardReply { Error = "already_requested" });
            if (_requests.Count >= 10 && _requests.Skip(_requests.Count - 10).All(q => DateTime.TryParse(q.RequestedAt, null, System.Globalization.DateTimeStyles.RoundtripKind, out var at) && at > DateTime.UtcNow.AddHours(-24)))
                return Task.FromResult(new Rewards.RewardReply { Error = "too_many_today" });
            if (Coins - Held < r.Price) return Task.FromResult(new Rewards.RewardReply { Error = "not_enough_coins" });
            var id = "rq_" + (_requests.Count + 1) + "_" + txId.Substring(0, 6);
            _requests.Add(new Rewards.RewardRequest { Id = id, RewardId = r.Id, Title = r.Title, Icon = r.Icon, Price = r.Price, Status = Rewards.RewardStatus.Pending,
                RequestedAt = DateTime.UtcNow.ToString("o") });
            _requestTx[txId] = id;
            return Task.FromResult(new Rewards.RewardReply());
        }

        public Task<Rewards.RewardReply> CancelAsync(string requestId, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new Rewards.RewardReply { Error = Rewards.RewardReply.Network });
            var q = _requests.FirstOrDefault(x => x.Id == requestId && x.Status == Rewards.RewardStatus.Pending);
            if (q == null) return Task.FromResult(new Rewards.RewardReply { Error = "already_decided" });
            q.Status = Rewards.RewardStatus.Cancelled;
            return Task.FromResult(new Rewards.RewardReply());
        }

        private static Rewards.RewardRequest CloneReq(Rewards.RewardRequest q) => new Rewards.RewardRequest
        {
            Id = q.Id, RewardId = q.RewardId, Title = q.Title, Icon = q.Icon, Price = q.Price, Status = q.Status, RequestedAt = q.RequestedAt,
        };

        // ---------- ITaskService ----------

        public Task<List<ChildTask>> FetchAsync(string fromDate, string toDate, CancellationToken ct = default)
        {
            if (Offline) throw new OperationCanceledException("çevrimdışı");
            var list = _tasks.Where(t => string.CompareOrdinal(t.Date, fromDate) >= 0 && string.CompareOrdinal(t.Date, toDate) <= 0)
                .Select(Clone).ToList();
            return Task.FromResult(list);
        }

        public Task<ServiceError> SetStatusAsync(string taskKey, ChildTaskStatus to, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(ServiceError.Network);
            var t = _tasks.FirstOrDefault(x => x.Key == taskKey);
            if (t == null) return Task.FromResult(ServiceError.Rejected);
            if (t.IsFinal) return Task.FromResult(ServiceError.Rejected);
            if (to == ChildTaskStatus.Approved || to == ChildTaskStatus.RejectedByParent) return Task.FromResult(ServiceError.Rejected);
            t.Status = to;
            return Task.FromResult(ServiceError.None);
        }

        // ---------- ISaveService ----------

        public Task<string> LoadLocalAsync(CancellationToken ct = default) => Task.FromResult(_localSave);
        public Task SaveLocalAsync(string json, CancellationToken ct = default) { _localSave = json; return Task.CompletedTask; }
        public Task<string> LoadRemoteAsync(CancellationToken ct = default) => Task.FromResult(Offline ? null : _remoteSave);
        public Task<ServiceError> SaveRemoteAsync(string json, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(ServiceError.Network);
            _remoteSave = json;
            return Task.FromResult(ServiceError.None);
        }

        // ---------- kalıcılık (önizleme: sahte sunucu sayfa yenilenince kaybolmasın) ----------

        private sealed class Snapshot
        {
            public int Coins;
            public int SunStones;
            public List<ChildTask> Tasks = new List<ChildTask>();
            public Dictionary<string, int> Tx = new Dictionary<string, int>();
            public string Remote;
            public List<Rewards.RealReward> Rewards = new List<Rewards.RealReward>();
            public List<Rewards.RewardRequest> Requests = new List<Rewards.RewardRequest>();
            public Dictionary<string, string> RequestTx = new Dictionary<string, string>();
        }

        public string Export() => Newtonsoft.Json.JsonConvert.SerializeObject(new Snapshot
        {
            Coins = Coins, SunStones = SunStones, Tasks = _tasks.Select(Clone).ToList(), Tx = new Dictionary<string, int>(_processedTx), Remote = _remoteSave,
            Rewards = _rewards.ToList(), Requests = _requests.Select(CloneReq).ToList(), RequestTx = new Dictionary<string, string>(_requestTx),
        });

        /// <summary>Önceki <see cref="Export"/> çıktısını yükler. Bozuk veri yok sayılır (boş sunucu).</summary>
        public void Import(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return;
            Snapshot snap;
            try { snap = Newtonsoft.Json.JsonConvert.DeserializeObject<Snapshot>(json); }
            catch (Newtonsoft.Json.JsonException) { return; }
            if (snap == null) return;
            Coins = snap.Coins;
            SunStones = snap.SunStones;
            _tasks.Clear();
            if (snap.Tasks != null) _tasks.AddRange(snap.Tasks);
            _processedTx.Clear();
            if (snap.Tx != null) foreach (var kv in snap.Tx) _processedTx[kv.Key] = kv.Value;
            _remoteSave = snap.Remote;
            _rewards.Clear();
            if (snap.Rewards != null) _rewards.AddRange(snap.Rewards.Where(r => r != null));
            _requests.Clear();
            if (snap.Requests != null) _requests.AddRange(snap.Requests.Where(r => r != null));
            _requestTx.Clear();
            if (snap.RequestTx != null) foreach (var kv in snap.RequestTx) _requestTx[kv.Key] = kv.Value;
        }

        /// <summary>Sunucudaki görevlerin (ebeveyn gözünden) listesi: deneme ebeveyn paneli için.</summary>
        public IReadOnlyList<ChildTask> AllTasks => _tasks;

        private static ChildTask Clone(ChildTask t) => new ChildTask
        {
            TaskId = t.TaskId, Date = t.Date, Title = t.Title, Description = t.Description, RewardCoins = t.RewardCoins,
            Recurrence = t.Recurrence, DueLocalTicks = t.DueLocalTicks, Status = t.Status, ParentNote = t.ParentNote,
            Skill = t.Skill, Difficulty = t.Difficulty,
        };
    }
}
