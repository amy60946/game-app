using System;

namespace Pofi.Logic.Pet
{
    public enum StatKind { Fullness, Cleanliness, Happiness, Home }

    /// <summary>Gösterge azalma ayarları (veri dosyası / uzaktan yapılandırma ile ezilebilir).</summary>
    public sealed class StatDecayConfig
    {
        public float PerHour = 4f;          // saatte düşüş
        public float Floor = 10f;           // bunun altına inmez: pet asla "boş" kalmaz
        public float MaxDropPerDay = 60f;   // bir takvim gününde en fazla düşüş
        public float SadThreshold = 30f;    // altında üzgün animasyon + sesli ipucu

        public static StatDecayConfig Default => new StatDecayConfig();
    }

    /// <summary>
    /// Pet göstergeleri (0–100). Zaman, dışarıdan verilen UTC saatle ilerler; uygulama kapalıyken geçen süre
    /// de hesaplanır. Pet ASLA ölmez/hastalanmaz: yalnızca taban değere kadar iner (FR-PET-3).
    /// </summary>
    [Serializable]
    public sealed class PetStats
    {
        public const int Count = 4;
        public float[] Values = { 80f, 80f, 80f, 80f };
        public long LastTickUtcTicks;
        // Günlük düşüş sınırı için: hangi gün ve o gün ne kadar düştü
        public int DropDay;
        public float[] DroppedToday = new float[Count];

        public float this[StatKind k] => Values[(int)k];

        public static PetStats New(DateTime nowUtc)
        {
            return new PetStats { LastTickUtcTicks = nowUtc.Ticks, DropDay = DayIndex(nowUtc) };
        }

        private static int DayIndex(DateTime utc) => (int)(utc.Ticks / TimeSpan.TicksPerDay);

        /// <summary>Son güncellemeden bu yana geçen süreyi uygular. Saat geri giderse (cihaz saati değiştirildi) hiçbir şey yapmaz.</summary>
        public void Tick(DateTime nowUtc, StatDecayConfig cfg)
        {
            var last = new DateTime(LastTickUtcTicks, DateTimeKind.Utc);
            if (nowUtc <= last) return;

            // Gün gün ilerle ki günlük sınır her güne ayrı uygulansın.
            var cursor = last;
            while (cursor < nowUtc)
            {
                var day = DayIndex(cursor);
                if (day != DropDay)
                {
                    DropDay = day;
                    for (var i = 0; i < Count; i++) DroppedToday[i] = 0f;
                }
                var dayEnd = new DateTime((day + 1L) * TimeSpan.TicksPerDay, DateTimeKind.Utc);
                var segmentEnd = nowUtc < dayEnd ? nowUtc : dayEnd;
                var hours = (float)(segmentEnd - cursor).TotalHours;
                for (var i = 0; i < Count; i++)
                {
                    var allowed = Math.Max(0f, cfg.MaxDropPerDay - DroppedToday[i]);
                    var drop = Math.Min(hours * cfg.PerHour, allowed);
                    var before = Values[i];
                    Values[i] = Math.Max(cfg.Floor, Math.Min(before, before - drop));
                    DroppedToday[i] += before - Values[i];
                }
                cursor = segmentEnd;
            }
            LastTickUtcTicks = nowUtc.Ticks;
        }

        /// <summary>Eylem etkisi (besle, yıkan, oyna, ev düzenle). 0–100 arasında kalır.</summary>
        public void Add(StatKind k, float amount)
        {
            Values[(int)k] = Math.Max(0f, Math.Min(100f, Values[(int)k] + amount));
        }

        public bool IsSad(StatKind k, StatDecayConfig cfg) => Values[(int)k] < cfg.SadThreshold;

        /// <summary>En düşük gösterge: pet'in hangi ipucunu vereceğini seçmek için.</summary>
        public StatKind Lowest()
        {
            var min = 0;
            for (var i = 1; i < Count; i++) if (Values[i] < Values[min]) min = i;
            return (StatKind)min;
        }
    }
}
