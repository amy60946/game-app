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
    public sealed class MockBackend : IWalletService, ITaskService, ISaveService
    {
        private readonly GameData _data;
        private readonly Dictionary<string, int> _processedTx = new Dictionary<string, int>(); // txId → tutar
        private readonly List<ChildTask> _tasks = new List<ChildTask>();
        private string _remoteSave;
        private string _localSave;

        public int Coins { get; private set; }
        public bool Offline { get; set; }

        public MockBackend(GameData data, int startCoins = 0)
        {
            _data = data;
            Coins = startCoins;
        }

        public IReadOnlyCollection<string> ProcessedTxIds => _processedTx.Keys;

        // ---------- "ebeveyn" tarafı (geliştirme) ----------

        public ChildTask ParentAssign(string taskId, string date, string title, int coins, Recurrence rec = Recurrence.Once)
        {
            var d = DateTime.ParseExact(date, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            var t = new ChildTask
            {
                TaskId = taskId, Date = date, Title = title, RewardCoins = Math.Max(1, Math.Min(50, coins)), Recurrence = rec,
                DueLocalTicks = d.AddDays(1).AddTicks(-1).Ticks, Status = ChildTaskStatus.Assigned,
            };
            _tasks.Add(t);
            return t;
        }

        public void ParentApprove(string key, string note = null)
        {
            var t = _tasks.First(x => x.Key == key);
            if (t.Status != ChildTaskStatus.ChildDone) throw new InvalidOperationException("Yalnızca çocuğun yaptım dediği görev onaylanır");
            t.Status = ChildTaskStatus.Approved;
            t.ParentNote = note;
            Coins += t.RewardCoins; // coin YALNIZCA burada artar
        }

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

        public Task<SpendResponse> SpendAsync(string txId, string itemId, int quantity, CancellationToken ct = default)
        {
            if (Offline) return Task.FromResult(new SpendResponse { Error = ServiceError.Network, Balance = Coins });
            if (_processedTx.ContainsKey(txId)) return Task.FromResult(new SpendResponse { Balance = Coins });
            var item = _data.Item(itemId);
            if (item == null || quantity <= 0) return Task.FromResult(new SpendResponse { Error = ServiceError.UnknownItem, Balance = Coins });
            var amount = item.Price * quantity;
            if (amount > Coins) return Task.FromResult(new SpendResponse { Error = ServiceError.NotEnoughCoins, Balance = Coins });
            Coins -= amount;
            _processedTx[txId] = amount;
            return Task.FromResult(new SpendResponse { Balance = Coins });
        }

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
            if (to == ChildTaskStatus.Approved || to == ChildTaskStatus.RejectedByParent) return Task.FromResult(ServiceError.Unauthorized);
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

        private static ChildTask Clone(ChildTask t) => new ChildTask
        {
            TaskId = t.TaskId, Date = t.Date, Title = t.Title, Description = t.Description, RewardCoins = t.RewardCoins,
            Recurrence = t.Recurrence, DueLocalTicks = t.DueLocalTicks, Status = t.Status, ParentNote = t.ParentNote,
        };
    }
}
