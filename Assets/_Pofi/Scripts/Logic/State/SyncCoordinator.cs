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
        public List<RealTaskReward> RealTaskRewards = new List<RealTaskReward>();   // onaylı gerçek görevin XP'si + beceri yıldızı (Ö2)
        public int RealTaskXp;
        public bool RealTaskGoalReached;
        public int SelfStarted;            // hatırlatmadan önce yapılıp onaylanan görev sayısı (Y5)   // görünmez günlük pay doldu: "bugünkü yıldız hedefine ulaştın" (M7)
        public int SunStonesEarned;      // bu senkronda yeni gelen Güneş Taşı (Ö1)
        public Progression.LevelUp LevelUp;   // görev XP'siyle seviye atlandıysa (kutlama)
        public List<Rewards.RewardEvent> RewardEvents = new List<Rewards.RewardEvent>();   // verilen / bekleyecek gerçek ödüller (Ö7)
    }

    /// <summary>
    /// Senkron (FR-TASK-7, kabul ölçütü 6): açılışta, ön plana gelince ve aralıkla çağrılır.
    /// Sıra: (1) görev niyetlerini gönder, (2) bekleyen harcamaları gönder, (3) görevleri çek ve birleştir,
    /// (4) bakiyeyi sunucudan al (sunucu esastır), (4b) gerçek ödülleri al, (5) kaydı sunucuya yedekle. Ağ yoksa yerel durum bozulmaz.
    /// </summary>
    public sealed class SyncCoordinator
    {
        private readonly ITaskService _tasks;
        private readonly IWalletService _wallet;
        private readonly ISaveService _save;
        private readonly GameData _data;
        private Progression.LevelTable _levels;
        /// <summary>Seviye tablosu (yaş grubuna göre; oyun girişte kendi tablosunu verir).</summary>
        public Progression.LevelTable Levels { get => _levels; set { if (value != null) _levels = value; } }
        private readonly Rewards.IRewardService _rewards;

        public SyncCoordinator(ITaskService tasks, IWalletService wallet, ISaveService save, GameData data, Rewards.IRewardService rewards = null)
        {
            _tasks = tasks; _wallet = wallet; _save = save; _data = data; _rewards = rewards;
            _levels = new Progression.LevelTable(data.Levels);
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
                    // Oturum süresi dolmuşsa (401) niyet silinmez: ağ yokmuş gibi bekler, oturum yenilenince gider
                    if (err == ServiceError.Network || err == ServiceError.Unauthorized) { report.Offline = true; return report; }
                    s.Tasks.Acknowledge(change.Key); // kabul ya da kalıcı ret: tekrar gönderme; birleştirme düzeltir
                }

                // 2) Bekleyen harcamalar. Sunucu seviye kilidini kayıttaki XP'den denetler: önce kayıt yedeklenir
                //    (yeni seviyede açılan eşya, eski yedek yüzünden reddedilmesin).
                if (s.Wallet.Pending.Count > 0)
                {
                    var pre = await _save.SaveRemoteAsync(SaveCodec.Serialize(s, nowUtc), ct);
                    if (pre == ServiceError.Network) { report.Offline = true; return report; }
                }
                foreach (var p in s.Wallet.Pending.ToList())
                {
                    var r = await _wallet.SpendAsync(p.TxId, p.ItemId, p.Quantity, ct);
                    // 401: satın alma geri alınmaz (eşya kaybolmasın); oturum yenilenince tekrar denenir
                    if (r.Error == ServiceError.Network || r.Error == ServiceError.Unauthorized) { report.Offline = true; return report; }
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
                var xpBefore = s.Xp.TotalXp;
                foreach (var ev in report.TaskEvents.Where(e => e.Kind == TaskEventKind.Approved))
                {
                    var bonus = s.Streak.Record(local);
                    if (bonus > 0) report.StreakBonusXp += s.Xp.Add(bonus, XpSource.TaskStreak, local, int.MaxValue).Granted;
                    var reward = RealTaskRewards.Apply(s.Skills, ev.Task);
                    if (reward == null) continue;
                    var g = s.Xp.AddRealTask(reward.Xp, local);
                    report.RealTaskXp += g.Granted;
                    if (g.CapReached) report.RealTaskGoalReached = true;
                    if (reward.SelfStarted) report.SelfStarted++;
                    report.RealTaskRewards.Add(reward);
                }
                report.LevelUp = _levels.Check(xpBefore, s.Xp.TotalXp);
                TaskBoosts.RecordOutcomes(s.Boosts ?? (s.Boosts = new BoostState()), s.Tasks.Tasks, local);

                // 4) Bakiye ve Güneş Taşı (sunucu esastır)
                var balances = await _wallet.GetBalancesAsync(ct);
                report.CoinsEarned = s.Wallet.ApplyServerSnapshot(balances.Coins, Array.Empty<string>());
                report.SunStonesEarned = Island.SunStoneBook.ApplyServerTotal(s.SunStones, balances.SunStones);

                // 4b) Gerçek ödüller (Güneş Taşı): liste, istekler, harcanabilir taş, taş düşürmeler
                // Ödül listesi alınamazsa (sunucu hatası, bozuk yanıt) senkronun geri kalanı ve yedek etkilenmez.
                if (_rewards != null)
                {
                    try
                    {
                        var snap = await _rewards.GetAsync(ct);
                        if (snap != null)
                        {
                            s.Rewards = s.Rewards ?? new Rewards.RewardBook();
                            report.RewardEvents = s.Rewards.Apply(snap);
                        }
                    }
                    catch (OperationCanceledException) when (!ct.IsCancellationRequested) { }
                    catch (Newtonsoft.Json.JsonException) { }
                }

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
