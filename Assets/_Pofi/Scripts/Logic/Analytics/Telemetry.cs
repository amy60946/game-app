using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace Pofi.Logic.Analytics
{
    /// <summary>Tek kullanım olayı (ortak sozlesme/akislar.md §9: <c>track_events</c> dizisinin bir öğesi).</summary>
    public sealed class TelemetryEvent
    {
        public string Event;
        public Dictionary<string, object> Props;
        public string SessionId;
        public string At;          // ISO 8601 UTC
    }

    /// <summary>Gönderimin sonucu: gitti, sonra yeniden dene (ağ/sunucu), ya da at (istek reddedildi; sonsuz deneme olmasın).</summary>
    public enum TelemetrySend { Sent, Retry, Drop }

    /// <summary>Sunucu tarafı: <c>track_session('child', …)</c> ve <c>track_events('child', …)</c>.</summary>
    public interface ITelemetrySink
    {
        Task<TelemetrySend> SessionAsync(string platform, string version, CancellationToken ct = default);
        Task<TelemetrySend> SendAsync(IReadOnlyList<TelemetryEvent> events, string platform, string version, CancellationToken ct = default);
    }

    /// <summary>
    /// Oyunun birinci taraf kullanım ölçümü (canlıya alma §4, ortak akislar.md §9 "GameApp olayları").
    /// Üçüncü taraf SDK yok; kişisel veri ve serbest metin yok: olay adı <c>alan.eylem</c>, özellik değerleri yalnız
    /// sayı, doğru/yanlış ya da kısa kimlik biçiminde metin (ad, görev başlığı, mesaj gibi serbest metin düşer).
    /// Olaylar biriktirilir, aynısı tek satırda sayılır (<c>n</c>), en çok 50'lik toplu gönderilir; günlük üst sınır var.
    /// Uzun aradan (5 dk) sonra öne gelişte yeni oturum açılır ve sunucuya oturum bildirilir.
    /// </summary>
    public sealed class Telemetry : Services.IAnalyticsService
    {
        public const string App = "child";
        public const int BatchSize = 50;          // sunucu sınırı (track_events ≤ 50/çağrı)
        public const int MaxQueue = 300;          // çevrimdışı birikim üst sınırı (eskiler düşer)
        public const int DailyCap = 500;          // sunucunun 2000/gün sınırının çok altında
        public static readonly TimeSpan NewSessionAfter = TimeSpan.FromMinutes(5);

        private static readonly Regex NameRx = new Regex("^[a-z][a-z0-9_.]{1,59}$", RegexOptions.CultureInvariant);
        private static readonly Regex KeyRx = new Regex("^[a-z][a-z0-9_]{0,29}$", RegexOptions.CultureInvariant);
        private static readonly Regex ValueRx = new Regex("^[a-z0-9_.:-]{1,40}$", RegexOptions.CultureInvariant);

        private readonly Func<DateTime> _utcNow;
        private readonly List<TelemetryEvent> _queue = new List<TelemetryEvent>();
        private DateTime _day;
        private int _today;
        private DateTime? _pausedAt;
        private bool _sending;

        public string SessionId { get; private set; }
        /// <summary>Sunucuya bildirilmesi bekleyen oturum (açılış ya da uzun aradan sonra öne geliş).</summary>
        public bool SessionPending { get; private set; }
        public int Queued => _queue.Count;
        public IReadOnlyList<TelemetryEvent> Pending => _queue;

        public Telemetry(Func<DateTime> utcNow)
        {
            _utcNow = utcNow ?? (() => DateTime.UtcNow);
            NewSession();
        }

        public static bool ValidName(string name) => name != null && NameRx.IsMatch(name);

        /// <summary>Özellik süzgeci: yalnız sayı / bool / kısa kimlik metni (serbest metin, ad, not geçmez).</summary>
        public static Dictionary<string, object> Clean(IReadOnlyDictionary<string, object> props)
        {
            if (props == null || props.Count == 0) return null;
            var d = new Dictionary<string, object>();
            foreach (var kv in props)
            {
                if (kv.Key == null || !KeyRx.IsMatch(kv.Key) || d.Count >= 8) continue;
                var v = kv.Value;
                switch (v)
                {
                    case bool b: d[kv.Key] = b; break;
                    case int i: d[kv.Key] = i; break;
                    case long l: d[kv.Key] = l; break;
                    case float f when !float.IsNaN(f) && !float.IsInfinity(f): d[kv.Key] = Math.Round(f, 2); break;
                    case double x when !double.IsNaN(x) && !double.IsInfinity(x): d[kv.Key] = Math.Round(x, 2); break;
                    case string s when ValueRx.IsMatch(s): d[kv.Key] = s; break;
                    case Enum e:
                        var es = e.ToString().ToLowerInvariant();
                        if (ValueRx.IsMatch(es)) d[kv.Key] = es;
                        break;
                }
            }
            return d.Count == 0 ? null : d;
        }

        public void Track(string eventName, IReadOnlyDictionary<string, object> props = null)
        {
            if (!ValidName(eventName)) return;
            var now = _utcNow();
            if (now.Date != _day) { _day = now.Date; _today = 0; }
            if (_today >= DailyCap) return;
            var clean = Clean(props);
            // aynı oturumda aynı ad, özellik yok ya da yalnız sayı (n) → tek satır, n artar (sık eylemler, ör. besleme)
            var add = OnlyCount(clean) ? CountOf(clean) : 0;
            var same = add > 0 ? _queue.LastOrDefault(e => e.Event == eventName && e.SessionId == SessionId && OnlyCount(e.Props)) : null;
            if (same != null)
            {
                same.Props = same.Props ?? new Dictionary<string, object>();
                same.Props["n"] = CountOf(same.Props) + add;
                return;
            }
            _today++;
            _queue.Add(new TelemetryEvent
            {
                Event = eventName, Props = clean, SessionId = SessionId,
                At = now.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture),
            });
            if (_queue.Count > MaxQueue) _queue.RemoveRange(0, _queue.Count - MaxQueue);
        }

        private static bool OnlyCount(Dictionary<string, object> p) => p == null || (p.Count == 1 && p.ContainsKey("n"));
        private static int CountOf(Dictionary<string, object> p) => p != null && p.TryGetValue("n", out var v) && v is int k && k > 0 ? k : 1;

        /// <summary>Uygulama arka plana gitti.</summary>
        public void Pause() => _pausedAt = _utcNow();

        /// <summary>Öne geldi: uzun aradan sonraysa yeni oturum (true).</summary>
        public bool Resume()
        {
            var at = _pausedAt;
            _pausedAt = null;
            if (at == null || _utcNow() - at.Value < NewSessionAfter) return false;
            NewSession();
            return true;
        }

        /// <summary>Çıkışta: kuyruk boşalır, yeni oturum (önceki çocuğun olayları sonrakine yazılmasın).</summary>
        public void Restart()
        {
            _queue.Clear();
            _pausedAt = null;
            NewSession();
        }

        private void NewSession()
        {
            SessionId = Guid.NewGuid().ToString();
            SessionPending = true;
        }

        /// <summary>Bekleyen oturumu ve olayları gönderir (aynı anda tek gönderim). Ağ yoksa olaylar kuyrukta kalır.</summary>
        public async Task FlushAsync(ITelemetrySink sink, string platform, string version, CancellationToken ct = default)
        {
            if (sink == null || _sending) return;
            _sending = true;
            try
            {
                if (SessionPending)
                {
                    var s = await sink.SessionAsync(platform, version, ct);
                    if (s == TelemetrySend.Retry) return;
                    SessionPending = false;
                }
                for (var guard = 0; _queue.Count > 0 && guard < 10; guard++)
                {
                    var batch = _queue.Take(BatchSize).ToList();
                    var r = await sink.SendAsync(batch, platform, version, ct);
                    if (r == TelemetrySend.Retry) return;
                    foreach (var e in batch) _queue.Remove(e);   // gönderildi ya da reddedildi (yeniden denenmez)
                }
            }
            catch (OperationCanceledException) { }
            finally { _sending = false; }
        }
    }
}
