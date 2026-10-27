using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.App
{
    /// <summary>Oyun içi kısa haber (yerelleştirme anahtarı + değerler).</summary>
    public sealed class Notice
    {
        public string Key;
        public object[] Args = Array.Empty<object>();
        public bool Happy;   // olumlu haber (pet sevinir); olumsuzlar sessiz ve kısa
    }

    /// <summary>
    /// Çocuğa giden oyun içi haberler (22 Ekim 2026; psikolojik değerlendirme: docs/BILDIRIMLER.md).
    /// Kurallar: toplu (bir senkronda en çok <see cref="MaxPerSync"/> haber, fazlası tek cümlede özetlenir),
    /// süre/baskı dili yok ("son", "kaçırdın", "acele" yok), ret özel ve yumuşak ("bir daha deneyebilirsin"),
    /// görev sayısı rozetle büyütülmez; oyun yarıda kesilmez (mini oyunda kuyrukta bekler, adaya dönünce gösterilir).
    /// </summary>
    public static class NoticeDigest
    {
        public const int MaxPerSync = 3;

        public static List<Notice> Build(IEnumerable<TaskEvent> tasks, IEnumerable<Rewards.RewardEvent> rewards)
        {
            var list = new List<Notice>();
            var evs = (tasks ?? Enumerable.Empty<TaskEvent>()).Where(e => e?.Task != null).ToList();

            // Olumlu haberler önce
            var rw = (rewards ?? Enumerable.Empty<Rewards.RewardEvent>()).Where(r => r != null).ToList();
            foreach (var r in rw.Where(r => r.Request != null))
                list.Add(r.Kind == Rewards.RewardEventKind.Given
                    ? new Notice { Key = "notice.reward_given", Args = new object[] { Rewards.RewardText.Label(r.Request) }, Happy = true }
                    : new Notice { Key = "notice.reward_waits", Args = new object[] { Rewards.RewardText.Label(r.Request) } });

            var approved = evs.Where(e => e.Kind == TaskEventKind.Approved).ToList();
            if (approved.Count == 1)
            {
                // ebeveynin onayla yazdığı söz ("Harika toplamışsın") aynen gösterilir (ortak 20261027130000)
                var note = approved[0].Task.ParentNote?.Trim();
                list.Add(string.IsNullOrEmpty(note)
                    ? new Notice { Key = "notice.approved_one", Args = new object[] { approved[0].Task.Title }, Happy = true }
                    : new Notice { Key = "notice.approved_one_note", Args = new object[] { approved[0].Task.Title, note }, Happy = true });
            }
            else if (approved.Count > 1) list.Add(new Notice { Key = "notice.approved_many", Args = new object[] { approved.Count }, Happy = true });

            // ebeveyn "Tekrar dene" dedi: suçlamasız, notu varsa aynen
            var retry = evs.Where(e => e.Kind == TaskEventKind.Retry).ToList();
            if (retry.Count == 1)
            {
                var note = retry[0].Task.ParentNote?.Trim();
                list.Add(string.IsNullOrEmpty(note)
                    ? new Notice { Key = "notice.retry_one", Args = new object[] { retry[0].Task.Title } }
                    : new Notice { Key = "notice.retry_one_note", Args = new object[] { retry[0].Task.Title, note } });
            }
            else if (retry.Count > 1) list.Add(new Notice { Key = "notice.retry_many", Args = new object[] { retry.Count } });

            // Yeni görevler: tek, sakin bir haber (gelecek günlerin tekrarları sayılmaz)
            var fresh = evs.Where(e => e.Kind == TaskEventKind.NewTask).Select(e => e.Task.TaskId).Distinct().Count();
            if (fresh == 1) list.Add(new Notice { Key = "notice.new_task_one" });
            else if (fresh > 1) list.Add(new Notice { Key = "notice.new_task_many", Args = new object[] { fresh } });

            var rejected = evs.Where(e => e.Kind == TaskEventKind.Rejected).ToList();
            if (rejected.Count == 1) list.Add(new Notice { Key = "notice.try_again_one", Args = new object[] { rejected[0].Task.Title } });
            else if (rejected.Count > 1) list.Add(new Notice { Key = "notice.try_again_many" });

            // ebeveynin taş düşürmesi: en sona, suçlamasız ("ailen … dedi"), not varsa aynen
            foreach (var d in rw.Where(r => r.Kind == Rewards.RewardEventKind.Deducted && r.Deduction != null).Select(r => r.Deduction).Take(1))
                list.Add(string.IsNullOrWhiteSpace(d.Note)
                    ? new Notice { Key = "notice.stones_deducted", Args = new object[] { d.Amount } }
                    : new Notice { Key = "notice.stones_deducted_note", Args = new object[] { d.Amount, d.Note.Trim() } });

            if (list.Count > MaxPerSync)
            {
                var rest = list.Count - (MaxPerSync - 1);
                list = list.Take(MaxPerSync - 1).ToList();
                list.Add(new Notice { Key = "notice.more", Args = new object[] { rest } });
            }
            return list;
        }
    }

    /// <summary>Haber kuyruğu: yalnız sakin anda (ada/ev/görev panosu) gösterilir; aynı anda birikenler en çok 3'e iner.</summary>
    public sealed class NoticeInbox
    {
        private readonly List<Notice> _queue = new List<Notice>();
        public int Count => _queue.Count;

        public void Add(IEnumerable<Notice> notices)
        {
            _queue.AddRange(notices ?? Enumerable.Empty<Notice>());
            // Uzun bir mini oyundan dönünce ekran haberle dolmasın
            if (_queue.Count > NoticeDigest.MaxPerSync)
            {
                var rest = _queue.Count - (NoticeDigest.MaxPerSync - 1);
                var keep = _queue.Take(NoticeDigest.MaxPerSync - 1).ToList();
                _queue.Clear();
                _queue.AddRange(keep);
                _queue.Add(new Notice { Key = "notice.more", Args = new object[] { rest } });
            }
        }

        /// <summary>Sakin anda çağrılır: kuyruk boşalır.</summary>
        public List<Notice> Drain(bool calmMoment)
        {
            if (!calmMoment || _queue.Count == 0) return new List<Notice>();
            var all = _queue.ToList();
            _queue.Clear();
            return all;
        }
    }

    /// <summary>
    /// Cihaz bildirimi (push, oyun kapalıyken) kuralları. Kod hazır ama KAPALI: <see cref="Enabled"/> = false, oyun cihaz
    /// anahtarını sunucuya kaydetmez (register_push_token çağrılmaz). Açılacaksa: ebeveyn ParentApp'ten açar, sessiz saatler
    /// ve günlük sınır sunucuda da uygulanır (ortak öneri gerekir). Ayrıntı: docs/BILDIRIMLER.md.
    /// </summary>
    public static class PushPolicy
    {
        public static readonly bool Enabled = false;
        public const int QuietFromHour = 20;   // 20:00–08:00 arası gönderilmez (uyku)
        public const int QuietToHour = 8;
        public const int MaxPerDay = 1;

        /// <summary>Çocuğa push gidebilecek türler: yalnız olumlu/nötr. Ret, "yapamadın", hatırlatma ve geri sayım asla.</summary>
        public static readonly string[] AllowedKinds = { "task_assigned", "task_approved", "reward_given" };

        public static bool MaySend(string kind, DateTime local, int sentToday, bool parentOptIn, bool schoolTime)
        {
            if (!Enabled || !parentOptIn || schoolTime) return false;
            if (Array.IndexOf(AllowedKinds, kind) < 0) return false;
            if (local.Hour >= QuietFromHour || local.Hour < QuietToHour) return false;
            return sentToday < MaxPerDay;
        }
    }
}
