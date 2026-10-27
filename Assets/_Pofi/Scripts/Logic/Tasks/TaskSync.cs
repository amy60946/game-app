using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Tasks
{
    [Serializable]
    public sealed class OutboxChange
    {
        public string Key;
        public ChildTaskStatus To;
        public long ClientUtcTicks;
    }

    public enum TaskEventKind { NewTask, Approved, Rejected, Removed, Retry }

    /// <summary>Senkron sonrası olaylar: oyun içi rozet + pet'ten sesli bildirim + onay sahnesi (FR-TASK-4/5).</summary>
    public sealed class TaskEvent
    {
        public TaskEventKind Kind;
        public ChildTask Task;
    }

    /// <summary>
    /// Görevlerin yerel önbelleği ve çevrimdışı kuyruğu (FR-TASK-7). Çocuğun işaretlemesi hemen ekranda görünür,
    /// kuyrukta bekler ve ağ gelince gönderilir. Sunucu nihai karar verdiyse (onay/ret) kuyruktaki değişiklik düşer.
    /// </summary>
    [Serializable]
    public sealed class TaskBoard
    {
        public List<ChildTask> Tasks = new List<ChildTask>();
        public List<OutboxChange> Outbox = new List<OutboxChange>();

        public ChildTask Find(string key) => Tasks.FirstOrDefault(t => t.Key == key);

        /// <summary>Çocuk "Yaptım" / "Yapamam" / "Geri al" dedi.</summary>
        public ChangeResult Mark(string key, ChildTaskStatus to, DateTime local, DateTime nowUtc)
        {
            var t = Find(key);
            if (t == null) return ChangeResult.NotAllowed;
            var r = TaskRules.CanChange(t, to, local);
            if (r != ChangeResult.Ok) return r;
            t.Status = to;
            if (to == ChildTaskStatus.ChildDone) t.DoneLocalTicks = local.Ticks;
            else if (to == ChildTaskStatus.Assigned) t.DoneLocalTicks = 0;
            if (to != ChildTaskStatus.Assigned) t.Retry = false;   // yeniden "Yaptım"/"Yapamam": ebeveynin tekrar isteği karşılandı
            Outbox.RemoveAll(o => o.Key == key); // aynı görev için yalnızca son niyet gönderilir
            Outbox.Add(new OutboxChange { Key = key, To = to, ClientUtcTicks = nowUtc.Ticks });
            return ChangeResult.Ok;
        }

        /// <summary>Sunucu gönderilen değişikliği kabul etti.</summary>
        public void Acknowledge(string key) => Outbox.RemoveAll(o => o.Key == key);

        /// <summary>
        /// Sunucudan gelen listeyle birleştir. Kural: nihai durum (Approved/RejectedByParent) her zaman sunucudan gelir;
        /// nihai olmayan durumlarda kuyrukta bekleyen çocuk niyeti korunur.
        /// </summary>
        public List<TaskEvent> Merge(IEnumerable<ChildTask> server)
        {
            var events = new List<TaskEvent>();
            var incoming = server.ToList();
            var old = Tasks.ToDictionary(t => t.Key);
            var merged = new List<ChildTask>();
            foreach (var s in incoming)
            {
                old.TryGetValue(s.Key, out var local);
                if (local != null) { s.DoneLocalTicks = local.DoneLocalTicks; s.Boosted = local.Boosted; }   // yalnız cihazdaki alanlar
                var pending = Outbox.FirstOrDefault(o => o.Key == s.Key);
                if (s.IsFinal)
                {
                    if (pending != null) Outbox.Remove(pending);
                    if (local == null || local.Status != s.Status)
                        events.Add(new TaskEvent { Kind = s.Status == ChildTaskStatus.Approved ? TaskEventKind.Approved : TaskEventKind.Rejected, Task = s });
                }
                else if (pending != null)
                {
                    s.Status = pending.To;
                    s.Retry = local != null && local.Retry && pending.To == ChildTaskStatus.Assigned;   // çocuğun son niyeti geçerli
                }
                if (s.Retry && pending == null && (local == null || !local.Retry))
                    events.Add(new TaskEvent { Kind = TaskEventKind.Retry, Task = s });   // ebeveyn "Tekrar dene" dedi
                else if (local == null && !s.IsFinal) events.Add(new TaskEvent { Kind = TaskEventKind.NewTask, Task = s });
                merged.Add(s);
            }
            foreach (var gone in old.Values.Where(o => incoming.All(s => s.Key != o.Key)))
            {
                events.Add(new TaskEvent { Kind = TaskEventKind.Removed, Task = gone });
                Outbox.RemoveAll(o => o.Key == gone.Key);
            }
            Tasks = merged;
            return events;
        }

        /// <summary>Panoda gösterim sırası: yapılacaklar, bekleyenler, sonuçlananlar.</summary>
        public IEnumerable<ChildTask> ForDisplay(DateTime local) =>
            Tasks.OrderBy(t => t.IsMissed(local) ? 3 : t.Status == ChildTaskStatus.Assigned ? 0 : t.Status == ChildTaskStatus.ChildDone ? 1 : 2)
                 .ThenBy(t => t.DueLocalTicks);
    }
}
