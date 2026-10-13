using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Data;
using Pofi.Logic.Economy;
using Pofi.Logic.Services;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.State
{
    public sealed class SyncReport
    {
        public bool Offline;
        public List<TaskEvent> TaskEvents = new List<TaskEvent>();
        public int CoinsEarned;
        public int StreakBonusXp;
        public List<PendingSpend> RejectedSpends = new List<PendingSpend>();
    }

    /// <summary>
    /// Senkron (FR-TASK-7, kabul ölçütü 6): açılışta, ön plana gelince ve aralıkla çağrılır.
    /// Sıra: (1) görev niyetlerini gönder, (2) bekleyen harcamaları gönder, (3) görevleri çek ve birleştir,
    /// (4) bakiyeyi sunucudan al (sunucu esastır), (5) kaydı sunucuya yedekle. Ağ yoksa yerel durum bozulmaz.
    /// </summary>
    public sealed class SyncCoordinator
    {
        private readonly ITaskService _tasks;
        private readonly IWalletService _wallet;
        private readonly ISaveService _save;
        private readonly GameData _data;

        public SyncCoordinator(ITaskService tasks, IWalletService wallet, ISaveService save, GameData data)
        {
            _tasks = tasks; _wallet = wallet; _save = save; _data = data;
        }

        public async Task<SyncReport> SyncAsync(GameState s, DateTime local, DateTime nowUtc, CancellationToken ct = default)
        {
            var report = new SyncReport();
            try
            {
                // 1) Görev niyetleri
                foreach (var change in s.Tasks.Outbox.ToList())
                {
                    var err = await _tasks.SetStatusAsync(change.Key, change.To, ct);
                    if (err == ServiceError.Network) { report.Offline = true; return report; }
                    s.Tasks.Acknowledge(change.Key); // kabul ya da kalıcı ret: tekrar gönderme; birleştirme düzeltir
                }

                // 2) Bekleyen harcamalar
                foreach (var p in s.Wallet.Pending.ToList())
                {
                    var r = await _wallet.SpendAsync(p.TxId, p.ItemId, p.Quantity, ct);
                    if (r.Error == ServiceError.Network) { report.Offline = true; return report; }
                    if (r.Error == ServiceError.None) s.Wallet.Acknowledge(p.TxId, r.Balance);
                    else
                    {
                        var back = s.Wallet.Reject(p.TxId, r.Balance);
                        var item = _data.Item(back.ItemId);
                        if (item != null) s.Inventory.Remove(item, back.Quantity);
                        report.RejectedSpends.Add(back);
                    }
                }

                // 3) Görevler: dünden bir hafta sonrasına
                var from = local.Date.AddDays(-1).ToString("yyyy-MM-dd");
                var to = local.Date.AddDays(7).ToString("yyyy-MM-dd");
                var server = await _tasks.FetchAsync(from, to, ct);
                report.TaskEvents = s.Tasks.Merge(server);
                foreach (var ev in report.TaskEvents.Where(e => e.Kind == TaskEventKind.Approved))
                {
                    var bonus = s.Streak.Record(local);
                    if (bonus > 0) report.StreakBonusXp += s.Xp.Add(bonus, XpSource.TaskStreak, local, int.MaxValue).Granted;
                }

                // 4) Bakiye (sunucu esastır)
                var balance = await _wallet.GetBalanceAsync(ct);
                report.CoinsEarned = s.Wallet.ApplyServerSnapshot(balance, Array.Empty<string>());

                // 5) Yedek
                s.LastSyncUtcTicks = nowUtc.Ticks;
                await _save.SaveRemoteAsync(SaveCodec.Serialize(s, nowUtc), ct);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                report.Offline = true;
            }
            return report;
        }
    }
}
