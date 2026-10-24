using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace Pofi.Logic.Rewards
{
    /// <summary>
    /// Ebeveynin tanımladığı gerçek ödül (ParentApp; sunucu ortak/migrations/20261022130000_sun_stones_rewards.sql).
    /// Bedeli harcanabilir Güneş Taşı. Tür: <c>item</c> (eşya/etkinlik, 1 adet) ya da <c>exchange</c> ("Değiş tokuş":
    /// her <see cref="Cost"/> taş = <see cref="UnitAmount"/> dakika ya da TL; 1–20 kez istenebilir).
    /// </summary>
    [Serializable]
    public sealed class RealReward
    {
        public string Id;
        public string Title;
        public string Kind = RewardKind.Item;
        public int Cost;               // taş (bir adet)
        public string Unit;            // minute / money (yalnız değiş tokuş)
        public int UnitAmount;
        public string Icon;

        public bool IsExchange => Kind == RewardKind.Exchange;
        public int MaxQuantity => IsExchange ? 20 : 1;
    }

    public static class RewardKind
    {
        public const string Item = "item";
        public const string Exchange = "exchange";
    }

    public static class RewardUnit
    {
        public const string Minute = "minute";
        public const string Money = "money";
    }

    /// <summary>reward_requests.status (ortak/sozlesme/durumlar.md P14).</summary>
    public static class RewardStatus
    {
        public const string Pending = "pending";
        public const string Approved = "approved";
        public const string Rejected = "rejected";
        public const string Canceled = "canceled";
    }

    [Serializable]
    public sealed class RewardRequest
    {
        public string Id;
        public string RewardId;
        public string Title;
        public int Quantity = 1;
        public int Cost;               // toplam taş
        public string Unit;
        public int Amount;             // toplam dakika / TL
        public string Source;          // child (oyunda istedi) / parent (ebeveyn doğrudan verdi)
        public string Status;
        public string Note;            // ebeveynin notu
        public string CreatedAt;
    }

    /// <summary>Ebeveynin taş düşürmesi (sun_stone_ledger reason = penalty): neden çocuğa sakin dille gösterilir.</summary>
    [Serializable]
    public sealed class StoneDeduction
    {
        public string Id;
        public int Amount;             // pozitif sayı (düşülen)
        public string Note;
        public string CreatedAt;
    }

    public sealed class RewardsSnapshot
    {
        public int Spendable;          // child_me.sun_stones_spendable
        public List<RealReward> Rewards = new List<RealReward>();
        public List<RewardRequest> Requests = new List<RewardRequest>();
        public List<StoneDeduction> Deductions = new List<StoneDeduction>();
    }

    /// <summary>Sunucu yanıtı. Error: null (tamam) / not_enough_stones / too_many_requests / premium_required / not_found / network / rejected.</summary>
    public sealed class RewardReply
    {
        public string Error;
        public string RequestId;
        /// <summary>Çocuğun ilk ödül talebi mi (sunucu request_reward "first", ortak 24 Ekim 2026): ebeveyne özel bildirim gider.</summary>
        public bool First;
        public bool Ok => Error == null;
        public const string Network = "network";
    }

    /// <summary>Gerçek ödüller sunucusu. Ağ yoksa GetAsync <see cref="OperationCanceledException"/>; istek/vazgeçme Error = "network".</summary>
    public interface IRewardService
    {
        Task<RewardsSnapshot> GetAsync(CancellationToken ct = default);
        /// <summary>request_reward: aynı ödül için bekleyen istek varsa o döner (tekrar dokunmak ikinci istek açmaz).</summary>
        Task<RewardReply> RequestAsync(string rewardId, int quantity, CancellationToken ct = default);
        Task<RewardReply> CancelAsync(string requestId, CancellationToken ct = default);
    }

    public enum RewardEventKind { Given, Declined, Deducted }

    public sealed class RewardEvent
    {
        public RewardEventKind Kind;
        public RewardRequest Request;
        public StoneDeduction Deduction;
    }

    /// <summary>
    /// Oyundaki son bilinen ödül durumu (çevrimdışı da gösterilir). Sunucu esastır: her senkronda yenilenir.
    /// Olaylar: bekleyen isteğe karar (verildi / şimdi olmaz), ebeveynin doğrudan verdiği yeni ödül, yeni taş düşürme.
    /// İlk senkronda geçmiş olay sayılmaz.
    /// </summary>
    [Serializable]
    public sealed class RewardBook
    {
        /// <summary>Arayüz aynı anda tek bekleyen istek gösterir (sunucu 5'e izin verir; ekonomi.md "Ödül kullanım ilkeleri").</summary>
        public const int MaxPending = 1;

        public List<RealReward> Rewards = new List<RealReward>();
        public List<RewardRequest> Requests = new List<RewardRequest>();
        public HashSet<string> Seen = new HashSet<string>();     // olayı gösterilmiş istek / düşürme kimlikleri
        public int Spendable;
        public bool Synced;
        public string GoalId;                                   // çocuğun hedef seçtiği ödül ("N taş kaldı")

        public RewardRequest Pending => Requests.FirstOrDefault(r => r.Status == RewardStatus.Pending);
        public bool CanRequestMore => Pending == null;
        public RealReward Find(string id) => Rewards.FirstOrDefault(r => r.Id == id);
        public RealReward Goal => GoalId == null ? null : Find(GoalId);

        /// <summary>Hedefe kalan taş (hedef yoksa ya da yettiyse 0).</summary>
        public int StonesLeft(RealReward r, int quantity = 1) => r == null ? 0 : Math.Max(0, r.Cost * Math.Max(1, quantity) - Spendable);

        public List<RewardEvent> Apply(RewardsSnapshot snap)
        {
            var events = new List<RewardEvent>();
            if (snap == null) return events;
            var before = Requests.ToDictionary(r => r.Id ?? "", r => r.Status);
            var requests = (snap.Requests ?? new List<RewardRequest>()).Where(x => x != null && !string.IsNullOrEmpty(x.Id)).ToList();
            var deductions = (snap.Deductions ?? new List<StoneDeduction>()).Where(x => x != null && !string.IsNullOrEmpty(x.Id)).ToList();
            if (Synced)
            {
                foreach (var r in requests)
                {
                    if (Seen.Contains(r.Id)) continue;
                    before.TryGetValue(r.Id, out var old);
                    if (r.Status == RewardStatus.Approved && (old == RewardStatus.Pending || (old == null && r.Source == "parent")))
                        events.Add(new RewardEvent { Kind = RewardEventKind.Given, Request = r });
                    else if (r.Status == RewardStatus.Rejected && old == RewardStatus.Pending)
                        events.Add(new RewardEvent { Kind = RewardEventKind.Declined, Request = r });
                    else continue;
                    Seen.Add(r.Id);
                }
                foreach (var d in deductions.Where(d => !Seen.Contains("d:" + d.Id)))
                {
                    events.Add(new RewardEvent { Kind = RewardEventKind.Deducted, Deduction = d });
                    Seen.Add("d:" + d.Id);
                }
            }
            else
            {
                foreach (var r in requests.Where(r => r.Status != RewardStatus.Pending)) Seen.Add(r.Id);
                foreach (var d in deductions) Seen.Add("d:" + d.Id);
            }
            Rewards = (snap.Rewards ?? new List<RealReward>()).Where(x => x != null && !string.IsNullOrEmpty(x.Id)).ToList();
            Requests = requests;
            Spendable = Math.Max(0, snap.Spendable);
            Synced = true;
            if (GoalId != null && Find(GoalId) == null) GoalId = null;   // ebeveyn kaldırdıysa hedef düşer
            if (Seen.Count > 400) Seen = new HashSet<string>(Seen.Skip(Seen.Count - 200));
            return events;
        }
    }

    /// <summary>Ödül metinleri (ParentApp reward_label ile aynı biçim): "Tablet · 30 dakika", "1 taş = 10 dk".</summary>
    public static class RewardText
    {
        public static string UnitShort(string unit) => unit == RewardUnit.Minute ? "dk" : unit == RewardUnit.Money ? "TL" : "";

        public static string Label(string title, string unit, int amount) =>
            unit == RewardUnit.Minute ? $"{title} · {amount} dakika" : unit == RewardUnit.Money ? $"{title} · {amount} TL" : title;

        /// <summary>Değiş tokuş oranı: "1 taş = 10 dk" (yalnız değiş tokuş; değilse null).</summary>
        public static string Rate(RealReward r) => r != null && r.IsExchange ? $"{r.Cost} taş = {r.UnitAmount} {UnitShort(r.Unit)}" : null;

        public static string Label(RewardRequest q) => q == null ? "" : Label(q.Title, q.Unit, q.Amount);
    }
}
