using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Tasks
{
    /// <summary>
    /// Beceri sözlüğü (Ö2; sözleşme: ortak/sozlesme/ekonomi.md 5B). 23 Ekim 2026'dan beri her görev kategorisi tek bir
    /// beceriye bağlıdır (kategori = beceri). Sunucudaki `tasks.skill` beceri anahtarıdır; eski serbest etiketler, kategori
    /// anahtarları ve İngilizce adlar da buraya eşlenir. Eşleşmeyen (Özel, boş) beceri yıldızı vermez.
    /// </summary>
    public static class SkillCatalog
    {
        public const string Teamwork = "teamwork", Stamina = "stamina", Knowledge = "knowledge",
            Strength = "strength", Focus = "focus", Kindness = "kindness";

        public static readonly IReadOnlyList<string> All = new[] { Teamwork, Stamina, Knowledge, Strength, Focus, Kindness };

        private static readonly Dictionary<string, string> Labels = new Dictionary<string, string>
        {
            [Teamwork] = "Takım Çalışması", [Stamina] = "Dayanıklılık", [Knowledge] = "Bilgi",
            [Strength] = "Güç", [Focus] = "Odak", [Kindness] = "Nezaket",
        };

        /// <summary>Görev kategorisi (ortak/sozlesme/durumlar.md 9) → beceri.</summary>
        public static readonly IReadOnlyDictionary<string, string> ByCategory = new Dictionary<string, string>
        {
            ["home"] = Teamwork, ["mind"] = Stamina, ["learn"] = Knowledge,
            ["health"] = Strength, ["self"] = Strength, ["focus"] = Focus, ["relation"] = Kindness,
        };

        // etiket (küçük harf) → anahtar: bugünkü ve eski ParentApp şablon etiketleri, İngilizce adlar, eski oyun anahtarları
        private static readonly Dictionary<string, string> Aliases = new Dictionary<string, string>
        {
            ["takım çalışması"] = Teamwork, ["sorumluluk"] = Teamwork, ["bağımsızlık"] = Teamwork,
            ["responsibility"] = Teamwork, ["independence"] = Teamwork,
            ["dayanıklılık"] = Stamina, ["sakinlik"] = Stamina, ["sakinleşme"] = Stamina, ["duygu farkındalığı"] = Stamina, ["calm"] = Stamina,
            ["bilgi"] = Knowledge, ["okuma"] = Knowledge, ["dil"] = Knowledge, ["temel beceriler"] = Knowledge, ["öğrenme"] = Knowledge,
            ["güç"] = Strength, ["öz bakım"] = Strength, ["hareket"] = Strength, ["sağlıklı alışkanlık"] = Strength, ["self_care"] = Strength,
            ["odak"] = Focus, ["odaklanma"] = Focus, ["öz denetim"] = Focus, ["sabır"] = Focus, ["planlama"] = Focus,
            ["nezaket"] = Kindness, ["empati"] = Kindness, ["minnettarlık"] = Kindness, ["paylaşma"] = Kindness,
            ["iletişim"] = Kindness, ["arkadaşlık"] = Kindness,
        };

        public static string Label(string key) => key != null && Labels.TryGetValue(key, out var l) ? l : null;

        /// <summary>Sunucudaki beceri metni → anahtar (bilinmeyen: null). Anahtarın, kategorinin ve İngilizce adın kendisi de kabul edilir.</summary>
        public static string Map(string skill)
        {
            if (string.IsNullOrWhiteSpace(skill)) return null;
            var s = skill.Trim();
            if (Labels.ContainsKey(s)) return s;
            // Türkçe küçük harf (WebGL'de kültür verisi olmayabilir: elle)
            var k = s.Replace('I', 'ı').Replace('İ', 'i').ToLowerInvariant();
            if (Labels.ContainsKey(k)) return k;
            if (ByCategory.TryGetValue(k, out var byCat)) return byCat;
            // İngilizce ad büyük I ile gelirse ("Independence") 'ı'ya döner: ASCII hâliyle de dene
            var ascii = s.ToLowerInvariant();
            if (Labels.ContainsKey(ascii)) return ascii;
            if (Aliases.TryGetValue(ascii, out var a)) return a;
            return Aliases.TryGetValue(k, out var key) ? key : null;
        }
    }

    /// <summary>Beceri yıldızları ve ödüllendirilmiş görev örnekleri (oyun kaydında).</summary>
    [Serializable]
    public sealed class SkillState
    {
        public Dictionary<string, int> Stars = new Dictionary<string, int>();
        public List<string> RewardedKeys = new List<string>();   // her görev örneği bir kez (en yeni ~200 tutulur)

        public int StarsOf(string key) => key != null && Stars.TryGetValue(key, out var n) ? n : 0;

        /// <summary>Eski kayıt (23 Ekim 2026 öncesi beceri anahtarları) → yeni altı beceri; yıldızlar toplanır.</summary>
        public void Normalize()
        {
            if (Stars == null) { Stars = new Dictionary<string, int>(); return; }
            var old = new List<KeyValuePair<string, int>>();
            foreach (var kv in Stars) if (SkillCatalog.Label(kv.Key) == null) old.Add(kv);
            foreach (var kv in old)
            {
                Stars.Remove(kv.Key);
                var to = SkillCatalog.Map(kv.Key);
                if (to != null) Stars[to] = StarsOf(to) + kv.Value;
            }
        }
    }

    public sealed class RealTaskReward
    {
        public ChildTask Task;
        public int Xp;
        public string Skill;      // null: beceri yok
        public int Stars;         // ödülden sonra o becerinin yıldızı
        public int NewTier;       // kademe yükseldiyse 1 bronz / 2 gümüş / 3 altın; değilse 0
        public bool SelfStarted;  // hatırlatma saatinden önce "Yaptım" (Y5): +yarım görev XP'si
        public bool Boosted;      // 2× XP teklifi kabul edilmişti (Y2)
    }

    /// <summary>
    /// Onaylanan gerçek görevin oyun içi ödülü (Ö2; sözleşme ekonomi.md 5.2): zorluğa göre XP (günlük sınıra sayılmaz)
    /// ve becerisine bir yıldız. Coin ve Güneş Taşı sunucudan gelir; bu sınıf yalnız oyun içi kısmı hesaplar.
    /// </summary>
    public static class RealTaskRewards
    {
        public const int KeepKeys = 200;
        public static readonly int[] TierStars = { 5, 15, 30 };

        public static int Xp(string difficulty)
        {
            switch (difficulty)
            {
                // 22 Ekim 2026 (kullanıcı, XP takibi M7): gerçek görev "cüzî" XP verir; asıl ödülü coin, Güneş Taşı ve beceri
                // yıldızıdır. Oran korunur (kolay 1 : orta 1,7 : zor 2,3). Günlük görünmez pay: XpSystem.AddRealTask.
                case "hard": return 14;
                case "medium": return 10;
                default: return 6;
            }
        }

        /// <summary>Zorluk sırası: kolay 1, orta 2, zor 3 (bilinmeyen: kolay). Görev kartındaki nokta sayısı.</summary>
        public static int Rank(string difficulty) => difficulty == "hard" ? 3 : difficulty == "medium" ? 2 : 1;

        /// <summary>
        /// Onaylanınca gelecek Güneş Taşı (sözleşme ekonomi.md 5A, sunucu stones_for_difficulty): kolay 1, orta 2, zor 3.
        /// Taşı sunucu verir; oyun bunu yalnız kartta göstermek için hesaplar.
        /// </summary>
        public static int Stones(string difficulty) => Rank(difficulty);

        /// <summary>
        /// "Kendiliğinden yaptı" (Y5, 22 Ekim 2026): çocuk "Yaptım"ı görevin günü, hatırlatma saatinden önce bastı.
        /// Hatırlatması olmayan görevde yok (karşılaştıracak saat yok). Ebeveyne iş düşmez.
        /// </summary>
        public static bool SelfStarted(ChildTask t)
        {
            if (t == null || t.DoneLocalTicks <= 0 || string.IsNullOrEmpty(t.Reminder) || t.Reminder.Length < 5) return false;
            if (!int.TryParse(t.Reminder.Substring(0, 2), out var hh) || !int.TryParse(t.Reminder.Substring(3, 2), out var mm)) return false;
            var done = new DateTime(t.DoneLocalTicks);
            if (done.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture) != t.Date) return false;
            return done.TimeOfDay < new TimeSpan(hh, mm, 0);
        }

        /// <summary>0 = kademe yok, 1 bronz, 2 gümüş, 3 altın.</summary>
        public static int Tier(int stars)
        {
            var t = 0;
            while (t < TierStars.Length && stars >= TierStars[t]) t++;
            return t;
        }

        /// <summary>Görev daha önce ödüllendirilmediyse yıldızı ekler ve ödülü döndürür; ödüllendirildiyse null.
        /// XP'yi çağıran ekler (seviye atlama ile birlikte).</summary>
        public static RealTaskReward Apply(SkillState s, ChildTask t)
        {
            if (t == null || t.Status != ChildTaskStatus.Approved || s.RewardedKeys.Contains(t.Key)) return null;
            s.RewardedKeys.Add(t.Key);
            if (s.RewardedKeys.Count > KeepKeys) s.RewardedKeys.RemoveRange(0, s.RewardedKeys.Count - KeepKeys);
            var basis = Xp(t.Difficulty);
            var r = new RealTaskReward { Task = t, Xp = basis * (t.Boosted ? 2 : 1), Skill = SkillCatalog.Map(t.Skill), Boosted = t.Boosted };
            if (SelfStarted(t)) { r.SelfStarted = true; r.Xp += basis / 2; }
            if (r.Skill != null)
            {
                var before = s.StarsOf(r.Skill);
                r.Stars = before + 1;
                s.Stars[r.Skill] = r.Stars;
                var tier = Tier(r.Stars);
                if (tier > Tier(before)) r.NewTier = tier;
            }
            return r;
        }

        /// <summary>Pet kartı için: yıldızı olan beceriler, çoktan aza.</summary>
        public static IEnumerable<KeyValuePair<string, int>> Ranked(SkillState s) =>
            SkillCatalog.All.Select(k => new KeyValuePair<string, int>(k, s.StarsOf(k))).Where(kv => kv.Value > 0).OrderByDescending(kv => kv.Value);
    }
}
