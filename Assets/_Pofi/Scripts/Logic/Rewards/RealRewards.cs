using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace Pofi.Logic.Rewards
{
    /// <summary>Ebeveynin tanımladığı gerçek ödül (Ö7; ortak/sozlesme/akislar.md 10).</summary>
    [Serializable]
    public sealed class RealReward
    {
        public string Id;
        public string Title;
        public string Icon;      // gift/park/movie/game/treat/book/toy/trip/star
        public int Price;
    }

    public static class RewardStatus
    {
        public const string Pending = "pending";
        public const string Given = "given";
        public const string Declined = "declined";
        public const string Cancelled = "cancelled";
    }

    [Serializable]
    public sealed class RewardRequest
    {
        public string Id;
        public string RewardId;
        public string Title;
        public string Icon;
        public int Price;
        public string Status;
        public string RequestedAt;
    }

    public sealed class RewardsSnapshot
    {
        public int Balance;
        public int Held;
        public int Available;
        public List<RealReward> Rewards = new List<RealReward>();
        public List<RewardRequest> Requests = new List<RewardRequest>();
    }

    /// <summary>Sunucu yanıtı. Error: null (tamam) / not_enough_coins / too_many_pending / unknown_reward / network / ...</summary>
    public sealed class RewardReply
    {
        public string Error;
        public bool Ok => Error == null;
        public const string Network = "network";
    }

    /// <summary>Gerçek ödüller sunucusu (child_rewards, child_request_reward, child_cancel_reward_request).
    /// Ağ yoksa GetAsync <see cref="OperationCanceledException"/> atar; istek/vazgeçme Error = "network" döner.</summary>
    public interface IRewardService
    {
        Task<RewardsSnapshot> GetAsync(CancellationToken ct = default);
        Task<RewardReply> RequestAsync(string rewardId, string txId, CancellationToken ct = default);
        Task<RewardReply> CancelAsync(string requestId, CancellationToken ct = default);
    }

    public enum RewardEventKind { Given, Declined }

    public sealed class RewardEvent
    {
        public RewardEventKind Kind;
        public RewardRequest Request;
    }

    /// <summary>
    /// Oyundaki son bilinen ödül durumu (çevrimdışı da gösterilir). Sunucu esastır: her senkronda tamamen yenilenir.
    /// Bekleyenden "verildi"/"bekleyecek"e geçenler olay olarak döner (sakin bir kutlama/not için).
    /// </summary>
    [Serializable]
    public sealed class RewardBook
    {
        public const int MaxPending = 3;   // sunucu: too_many_pending

        public List<RealReward> Rewards = new List<RealReward>();
        public List<RewardRequest> Requests = new List<RewardRequest>();
        public int Held;

        public IEnumerable<RewardRequest> Pending => Requests.Where(r => r.Status == RewardStatus.Pending);
        public bool CanRequestMore => Pending.Count() < MaxPending;
        public RewardRequest PendingFor(string rewardId) => Pending.FirstOrDefault(r => r.RewardId == rewardId);

        public List<RewardEvent> Apply(RewardsSnapshot snap)
        {
            var events = new List<RewardEvent>();
            if (snap == null) return events;
            var before = new HashSet<string>(Requests.Where(r => r.Status == RewardStatus.Pending).Select(r => r.Id));
            foreach (var r in snap.Requests ?? new List<RewardRequest>())
            {
                if (r == null || !before.Contains(r.Id)) continue;
                if (r.Status == RewardStatus.Given) events.Add(new RewardEvent { Kind = RewardEventKind.Given, Request = r });
                else if (r.Status == RewardStatus.Declined) events.Add(new RewardEvent { Kind = RewardEventKind.Declined, Request = r });
            }
            Rewards = (snap.Rewards ?? new List<RealReward>()).Where(x => x != null && !string.IsNullOrEmpty(x.Id)).ToList();
            Requests = (snap.Requests ?? new List<RewardRequest>()).Where(x => x != null && !string.IsNullOrEmpty(x.Id)).ToList();
            Held = Math.Max(0, snap.Held);
            return events;
        }
    }
}
