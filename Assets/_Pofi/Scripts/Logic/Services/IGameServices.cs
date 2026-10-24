using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.Services
{
    public enum ServiceError { None, Network, Unauthorized, NotEnoughCoins, UnknownItem, Rejected }

    public sealed class SpendResponse
    {
        public ServiceError Error;
        public int Balance;            // sunucunun güncel bakiyesi (hata olsa da)
    }

    /// <summary>Sunucudaki bakiyeler: coin ve Güneş Taşı toplamı (sunucu taşı bilmiyorsa null).</summary>
    public sealed class BalanceSnapshot
    {
        public int Coins;
        public int? SunStones;
        public string AgeBand;   // child_me.age_band: K/A/B/C (ebeveyn seçimi ya da doğum gününden)
    }

    /// <summary>Hoş geldin coin'i yanıtı (ortak claim_welcome_coins): ilk çağrıda Ok + Coins; sonrakilerde AlreadyClaimed.</summary>
    public sealed class WelcomeResponse
    {
        public bool Ok;
        public bool AlreadyClaimed;
        public int Coins;
        public int Balance = -1;       // sunucunun güncel bakiyesi (bilinmiyorsa −1)
        public ServiceError Error;
    }

    /// <summary>
    /// Hoş geldin coin'i (kullanıcı GB17, 24 Ekim 2026; ortak proposed/20261024100000): çocuk başına bir kez 20 coin, ilk aksesuarı
    /// alabilsin diye. Coin yine sunucuda yazılır; istemci yalnızca ister. Tekrar çağrı güvenli (sunucu bir kez verir).
    /// </summary>
    public interface IWelcomeService
    {
        Task<WelcomeResponse> ClaimWelcomeAsync(CancellationToken ct = default);
    }

    /// <summary>Coin cüzdanı (sunucu). İstemci coin ekleyemez; yalnızca harcar.</summary>
    public interface IWalletService
    {
        Task<int> GetBalanceAsync(CancellationToken ct = default);

        /// <summary>Coin + Güneş Taşı tek istekte (child_me).</summary>
        Task<BalanceSnapshot> GetBalancesAsync(CancellationToken ct = default);

        /// <summary>txId tekrar gönderilirse sunucu yeniden düşmez (idempotent). Fiyatı sunucu belirler.</summary>
        Task<SpendResponse> SpendAsync(string txId, string itemId, int quantity, CancellationToken ct = default);
    }

    public interface ITaskService
    {
        /// <summary>Verilen tarih aralığındaki görev örnekleri (tekrarlar sunucuda açılır).</summary>
        Task<List<ChildTask>> FetchAsync(string fromDate, string toDate, CancellationToken ct = default);

        Task<ServiceError> SetStatusAsync(string taskKey, ChildTaskStatus to, CancellationToken ct = default);
    }

    /// <summary>Yerel kayıt (cihaz) + sunucu yedeği.</summary>
    public interface ISaveService
    {
        Task<string> LoadLocalAsync(CancellationToken ct = default);
        Task SaveLocalAsync(string json, CancellationToken ct = default);
        Task<string> LoadRemoteAsync(CancellationToken ct = default);
        Task<ServiceError> SaveRemoteAsync(string json, CancellationToken ct = default);
    }

    /// <summary>Anonim, ebeveyn onaylı, en az veri (FR-SAFE-3). Varsayılan uygulama hiçbir şey göndermez.</summary>
    public interface IAnalyticsService
    {
        void Track(string eventName, IReadOnlyDictionary<string, object> props = null);
    }

    public sealed class NoAnalytics : IAnalyticsService
    {
        public void Track(string eventName, IReadOnlyDictionary<string, object> props = null) { }
    }
}
