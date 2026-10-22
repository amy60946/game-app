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
    public sealed class MockBackend : IWalletService, ITaskService, ISaveService, Rewards.IRewardService, IGoalService
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
            string skill = null, string difficulty = "easy", string reminder = null)
        {
            var d = DateTime.ParseExact(date, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            var t = new ChildTask
            {
                TaskId = taskId, Date = date, Title = title, RewardCoins = Math.Max(1, Math.Min(50, coins)), Recurrence = rec,
                DueLocalTicks = d.AddDays(1).AddTicks(-1).Ticks, Status = ChildTaskStatus.Assigned,
                Skill = skill, Difficulty = difficulty ?? "easy", Reminder = reminder,
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
            if (amount > Coins) return Task.FromResult(new SpendResponse { Error = ServiceError.NotEnoughCoins, Balance = Coins });
            Coins -= amount;
            _processedTx[txId] = amount;
            return Task.FromResult(new SpendResponse { Balance = Coins });
        }

        // ---------- gerçek ödüller (Güneş Taşı; sunucu sun_stones_rewards ile aynı kurallar) ----------
        // Kazanılan taş (SunStones, ada) azalmaz; harcanabilir = kazanılan − verilen ödüller − düşürmeler.

        private readonly List<Rewards.RealReward> _rewards = new List<Rewards.RealReward>();
        private readonly List<Rewards.RewardRequest> _requests = new List<Rewards.RewardRequest>();
        private readonly List<Rewards.StoneDeduction> _deductions = new List<Rewards.StoneDeduction>();
        private int _stonesSpent;

        public IReadOnlyList<Rewards.RewardRequest> RewardRequests => _requests;
        public int SpendableStones => Math.Max(0, SunStones - _stonesSpent);

        public void ParentAddReward(string id, string title, string icon, int cost, string unit = null, int unitAmount = 0)
        {
            _rewards.RemoveAll(r => r.Id == id);
            _rewards.Add(new Rewards.RealReward
            {
                Id = id, Title = title, Icon = icon, Cost = Math.Max(1, Math.Min(500, cost)),
                Kind = unit == null ? Rewards.RewardKind.Item : Rewards.RewardKind.Exchange, Unit = unit, UnitAmount = unit == null ? 0 : unitAmount,
            });
        }

        /// <summary>Ebeveyn kararı (decide_reward_request). Onayda taş düşer; bakiye yetmezse false (istek bekler).</summary>
        public bool ParentDecideReward(string requestId, bool approve, string note = null)
        {
            var q = _requests.FirstOrDefault(x => x.Id == requestId && x.Status == Rewards.RewardStatus.Pending);
            if (q == null) return false;
            if (approve)
            {
                if (SpendableStones < q.Cost) return false;
                _stonesSpent += q.Cost;
            }
            q.Status = approve ? Rewards.RewardStatus.Approved : Rewards.RewardStatus.Rejected;
            q.Note = note;
            return true;
        }

        /// <summary>Ebeveyn doğrudan ödül verir (give_reward).</summary>
        public bool ParentGiveReward(string rewardId, int quantity = 1)
        {
            var r = _rewards.FirstOrDefault(x => x.Id == rewardId);
            if (r == null || SpendableStones < r.Cost * quantity) return false;
            _stonesSpent += r.Cost * quantity;
            _requests.Add(new Rewards.RewardRequest
            {
                Id = "rq_" + (_requests.Count + 1), RewardId = r.Id, Title = r.Title, Quantity = quantity, Cost = r.Cost * quantity, Unit = r.Unit,
                Amount = r.UnitAmount * quantity, Source = "parent", Status = Rewards.RewardStatus.Approved, CreatedAt = DateTime.UtcNow.ToString("o"),
            });
            return true;
        }

        /// <summary>Ebeveyn taş düşürür (deduct_sun_stones); harcanabilir bakiye eksiye inmez.</summary>
        public void ParentDeductStones(int amount, string note)
        {
            var n = Math.Min(Math.Max(0, amount), SpendableStones);
            if (n == 0) return;
            _stonesSpent += n;
            _deductions.Add(new Rewards.StoneDeduction { Id = "pen_" + (_deductions.Count + 1), Amount = n, Note = note, CreatedAt = DateTime.UtcNow.ToString("o") });
        }

        public Task<Rewards.RewardsSnapshot> GetAsync(CancellationToken ct = default)
        {
            if (Offline) throw new OperationCanceledException("çevrimdışı");
            return Task.FromResult(new Rewards.RewardsSnapshot
            {
                Spendable = SpendableStones,
                Rewards = _rewards.Select(CloneReward).OrderBy(r => r.Cost).ToList(),
                Requests = Enumerable.Reverse(_requests).Take(30).Select(CloneReq).ToList(),
                Deductions = Enumerable.Reverse(_deductions).Take(10).Select(d => new Rewards.StoneDeduction { Id = d.Id, Amount = d.Amount, Note = d.Note, CreatedAt = d.CreatedAt }).ToList(),
            });
        }

        public Task<Rewards.RewardReply> RequestAsync(string rewardId, int quantity, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new Rewards.RewardReply { Error = Rewards.RewardReply.Network });
            var r = _rewards.FirstOrDefault(x => x.Id == rewardId);
            if (r == null) return Task.FromResult(new Rewards.RewardReply { Error = "not_found" });
            if (quantity < 1 || quantity > r.MaxQuantity) return Task.FromResult(new Rewards.RewardReply { Error = "rejected" });
            var same = _requests.FirstOrDefault(q => q.RewardId == r.Id && q.Status == Rewards.RewardStatus.Pending);
            if (same != null) return Task.FromResult(new Rewards.RewardReply { RequestId = same.Id });
            if (_requests.Count(q => q.Status == Rewards.RewardStatus.Pending) >= 5) return Task.FromResult(new Rewards.RewardReply { Error = "too_many_requests" });
            if (SpendableStones < r.Cost * quantity) return Task.FromResult(new Rewards.RewardReply { Error = "not_enough_stones" });
            var id = "rq_" + (_requests.Count + 1);
            _requests.Add(new Rewards.RewardRequest
            {
                Id = id, RewardId = r.Id, Title = r.Title, Quantity = quantity, Cost = r.Cost * quantity, Unit = r.Unit, Amount = r.UnitAmount * quantity,
                Source = "child", Status = Rewards.RewardStatus.Pending, CreatedAt = DateTime.UtcNow.ToString("o"),
            });
            return Task.FromResult(new Rewards.RewardReply { RequestId = id });
        }

        public Task<Rewards.RewardReply> CancelAsync(string requestId, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new Rewards.RewardReply { Error = Rewards.RewardReply.Network });
            var q = _requests.FirstOrDefault(x => x.Id == requestId && x.Status == Rewards.RewardStatus.Pending);
            if (q == null) return Task.FromResult(new Rewards.RewardReply { Error = "not_found" });
            q.Status = Rewards.RewardStatus.Canceled;
            return Task.FromResult(new Rewards.RewardReply());
        }

        private static Rewards.RealReward CloneReward(Rewards.RealReward r) => new Rewards.RealReward
        {
            Id = r.Id, Title = r.Title, Kind = r.Kind, Cost = r.Cost, Unit = r.Unit, UnitAmount = r.UnitAmount, Icon = r.Icon,
        };

        private static Rewards.RewardRequest CloneReq(Rewards.RewardRequest q) => new Rewards.RewardRequest
        {
            Id = q.Id, RewardId = q.RewardId, Title = q.Title, Quantity = q.Quantity, Cost = q.Cost, Unit = q.Unit, Amount = q.Amount,
            Source = q.Source, Status = q.Status, Note = q.Note, CreatedAt = q.CreatedAt,
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

        // ---------- IGoalService (Y2 teklif kaydı, Y6 haftalık hedef; sunucu kuralının kopyası) ----------

        public readonly Dictionary<string, bool> Boosts = new Dictionary<string, bool>();
        public int? WeeklyCap;
        private readonly HashSet<string> _goalClaims = new HashSet<string>();
        /// <summary>Test için "bugün"; null ise cihaz saati.</summary>
        public DateTime? Today;

        public Task<ServiceError> RecordBoostAsync(string taskKey, bool accepted, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(ServiceError.Network);
            if (_tasks.All(t => t.Key != taskKey)) return Task.FromResult(ServiceError.Rejected);
            Boosts[taskKey] = accepted;
            return Task.FromResult(ServiceError.None);
        }

        private static DateTime WeekStart(DateTime d) => d.Date.AddDays(-(((int)d.DayOfWeek + 6) % 7));

        public WeeklyGoal GoalFor(DateTime today)
        {
            var w = WeekStart(today);
            string S(DateTime d) => d.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            int Approved(DateTime a, DateTime b) => _tasks.Count(t => t.Status == ChildTaskStatus.Approved
                && string.CompareOrdinal(t.Date, S(a)) >= 0 && string.CompareOrdinal(t.Date, S(b)) <= 0);
            var assigned = _tasks.Count(t => string.CompareOrdinal(t.Date, S(w)) >= 0 && string.CompareOrdinal(t.Date, S(w.AddDays(6))) <= 0);
            var done = Approved(w, w.AddDays(6));
            var prev1 = Approved(w.AddDays(-7), w.AddDays(-1));
            var prev2 = Approved(w.AddDays(-14), w.AddDays(-8));
            var history = _tasks.Any(t => string.CompareOrdinal(t.Date, S(w)) < 0 && t.Status != ChildTaskStatus.Assigned);
            int? target = null;
            if (history && assigned >= 3)
            {
                var auto = (int)Math.Ceiling((prev1 + prev2) / 2.0 * 1.2);
                var t = Math.Min(Math.Max(3, auto), (int)Math.Floor(assigned * 0.9));
                if (t >= 3) target = WeeklyCap.HasValue ? Math.Min(t, WeeklyCap.Value) : t;
            }
            return new WeeklyGoal { WeekStart = S(w), Target = target, Done = done, Assigned = assigned, Claimed = _goalClaims.Contains(S(w)) };
        }

        public Task<WeeklyGoal> WeeklyGoalAsync(CancellationToken ct = default) =>
            Task.FromResult(Offline ? null : GoalFor(Today ?? DateTime.Now));

        public Task<GoalClaim> ClaimWeeklyGoalAsync(CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new GoalClaim { Error = "offline" });
            var g = GoalFor(Today ?? DateTime.Now);
            if (!g.Target.HasValue) return Task.FromResult(new GoalClaim { Error = "no_goal" });
            if (g.Claimed) return Task.FromResult(new GoalClaim { Error = "already_claimed" });
            if (!g.Reached) return Task.FromResult(new GoalClaim { Error = "not_reached" });
            _goalClaims.Add(g.WeekStart);
            SunStones += 2;
            return Task.FromResult(new GoalClaim { Ok = true, Stones = 2 });
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
            public List<Rewards.StoneDeduction> Deductions = new List<Rewards.StoneDeduction>();
            public int StonesSpent;
        }

        public string Export() => Newtonsoft.Json.JsonConvert.SerializeObject(new Snapshot
        {
            Coins = Coins, SunStones = SunStones, Tasks = _tasks.Select(Clone).ToList(), Tx = new Dictionary<string, int>(_processedTx), Remote = _remoteSave,
            Rewards = _rewards.ToList(), Requests = _requests.Select(CloneReq).ToList(), Deductions = _deductions.ToList(), StonesSpent = _stonesSpent,
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
            _deductions.Clear();
            if (snap.Deductions != null) _deductions.AddRange(snap.Deductions.Where(d => d != null));
            _stonesSpent = Math.Max(0, snap.StonesSpent);
        }

        /// <summary>Sunucudaki görevlerin (ebeveyn gözünden) listesi: deneme ebeveyn paneli için.</summary>
        public IReadOnlyList<ChildTask> AllTasks => _tasks;

        private static ChildTask Clone(ChildTask t) => new ChildTask
        {
            TaskId = t.TaskId, Date = t.Date, Title = t.Title, Description = t.Description, RewardCoins = t.RewardCoins,
            Recurrence = t.Recurrence, DueLocalTicks = t.DueLocalTicks, Status = t.Status, ParentNote = t.ParentNote,
            Skill = t.Skill, Difficulty = t.Difficulty, Reminder = t.Reminder,
        };
    }
}
