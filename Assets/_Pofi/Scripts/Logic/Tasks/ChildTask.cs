using System;

namespace Pofi.Logic.Tasks
{
    /// <summary>Sunucudaki durumlar (FR-TASK-2). "Missed" sunucuda tutulmaz; süre geçince istemci hesaplar.</summary>
    public enum TaskStatus { Assigned, ChildDone, Approved, DeclinedByChild, RejectedByParent }

    public enum Recurrence { Once, Daily, Weekly, Monthly }

    /// <summary>
    /// Çocuğa görünen bir görev örneği. Tekrarlayan görevlerin her günü ayrı örnektir: Key = görevKimliği|tarih.
    /// </summary>
    [Serializable]
    public sealed class ChildTask
    {
        public string TaskId;
        public string Date;            // yyyy-MM-dd (yerel)
        public string Title;
        public string Description;
        public int RewardCoins;
        public Recurrence Recurrence;
        public long DueLocalTicks;     // bu saatten sonra "kaçırıldı" (varsayılan: günün sonu)
        public TaskStatus Status;
        public string ParentNote;      // ret/onay notu

        public string Key => TaskId + "|" + Date;

        public bool IsFinal => Status == TaskStatus.Approved || Status == TaskStatus.RejectedByParent;

        /// <summary>Atanmış ama süresi geçmiş: nazikçe "kaçırıldı" gösterilir, ceza yok (FR-TASK-3).</summary>
        public bool IsMissed(DateTime local) => Status == TaskStatus.Assigned && local.Ticks > DueLocalTicks;
    }

    public enum ChangeResult { Ok, NotAllowed, Missed, AlreadyFinal }

    /// <summary>Çocuğun yapabileceği durum geçişleri.</summary>
    public static class TaskRules
    {
        /// <summary>
        /// Assigned → ChildDone ("Yaptım") / DeclinedByChild ("Yapamam").
        /// ChildDone ya da DeclinedByChild → Assigned (geri al), ebeveyn karar vermeden önce.
        /// </summary>
        public static ChangeResult CanChange(ChildTask t, TaskStatus to, DateTime local)
        {
            if (t.IsFinal) return ChangeResult.AlreadyFinal;
            switch (t.Status)
            {
                case TaskStatus.Assigned:
                    if (to != TaskStatus.ChildDone && to != TaskStatus.DeclinedByChild) return ChangeResult.NotAllowed;
                    return t.IsMissed(local) ? ChangeResult.Missed : ChangeResult.Ok;
                case TaskStatus.ChildDone:
                case TaskStatus.DeclinedByChild:
                    return to == TaskStatus.Assigned ? ChangeResult.Ok : ChangeResult.NotAllowed;
                default:
                    return ChangeResult.NotAllowed;
            }
        }
    }
}
