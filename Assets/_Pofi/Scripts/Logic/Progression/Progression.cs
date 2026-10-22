using System;
using System.Collections.Generic;
using Pofi.Logic.Data;

namespace Pofi.Logic.Progression
{
    public enum GrowthStage { Yavru, Genc, Yetiskin }

    /// <summary>Seviye atlayınca yayınlanan olay: kutlama ekranı yeni açılanları listeler (FR-PROG-3).</summary>
    public sealed class LevelUp
    {
        public int From;
        public int To;
        public List<string> Unlocked = new List<string>();
        public GrowthStage? NewStage;
    }

    /// <summary>
    /// XP → seviye (1–15), açılış kapısı (UnlockGate) ve büyüme evresi. XP yalnızca oyun içi etkinliklerden gelir;
    /// coin ile alınamaz (FR-ECO-2) — bu sınıf XP'nin kaynağını bilmez, yalnızca toplamla çalışır.
    /// </summary>
    public sealed class LevelTable
    {
        private readonly LevelTableDef _def;
        private readonly int[] _cumulative; // _cumulative[L-1] = L seviyesine ulaşmak için toplam XP

        public LevelTable(LevelTableDef def)
        {
            _def = def;
            _cumulative = new int[def.MaxLevel];
            UseBand(null);
        }

        public LevelTable(LevelTableDef def, Profile.AgeBand band) : this(def) => UseBand(band);

        /// <summary>
        /// Seviye eşiklerini yaş grubuna göre seçer (S1, 22 Ekim 2026): küçük yaşta seviye daha az XP ister.
        /// Grup tablosu yoksa ya da null verilirse genel tablo (= B). Açılış seviyeleri gruptan bağımsızdır.
        /// </summary>
        public void UseBand(Profile.AgeBand? band)
        {
            var steps = _def.XpToNext;
            if (band.HasValue && _def.XpToNextByBand != null && _def.XpToNextByBand.TryGetValue(band.Value.ToString(), out var b)
                && b != null && b.Count >= _def.MaxLevel - 1) steps = b;
            Band = band;
            for (var i = 1; i < _def.MaxLevel; i++) _cumulative[i] = _cumulative[i - 1] + steps[i - 1];
        }

        public Profile.AgeBand? Band { get; private set; }

        public int MaxLevel => _def.MaxLevel;
        public int TotalXpFor(int level) => _cumulative[Math.Max(1, Math.Min(level, MaxLevel)) - 1];

        public int LevelFor(int totalXp)
        {
            var level = 1;
            while (level < MaxLevel && totalXp >= _cumulative[level]) level++;
            return level;
        }

        /// <summary>Mevcut seviyede ilerleme (0–1). Son seviyede 1.</summary>
        public float ProgressInLevel(int totalXp)
        {
            var lv = LevelFor(totalXp);
            if (lv >= MaxLevel) return 1f;
            var start = _cumulative[lv - 1];
            return (totalXp - start) / (float)(_cumulative[lv] - start);
        }

        public int UnlockLevel(string featureId)
        {
            foreach (var kv in _def.Unlocks)
                if (kv.Value.Contains(featureId)) return int.Parse(kv.Key);
            return -1; // tabloda yoksa kilitsiz değil: bilinmeyen içerik
        }

        /// <summary>FR-PROG-2 kapısı. Tabloda olmayan kimlik kilitli sayılır (yanlış yazım içeriği açmasın).</summary>
        public bool IsUnlocked(string featureId, int level)
        {
            var need = UnlockLevel(featureId);
            return need > 0 && level >= need;
        }

        public IReadOnlyList<string> UnlocksAt(int level) =>
            _def.Unlocks.TryGetValue(level.ToString(), out var list) ? list : (IReadOnlyList<string>)Array.Empty<string>();

        public GrowthStage StageFor(int level)
        {
            if (level >= _def.Growth["yetiskin"]) return GrowthStage.Yetiskin;
            if (level >= _def.Growth["genc"]) return GrowthStage.Genc;
            return GrowthStage.Yavru;
        }

        /// <summary>XP değişince seviye atlama bilgisi (birden fazla seviye birden atlanabilir). Atlama yoksa null.</summary>
        public LevelUp Check(int oldXp, int newXp)
        {
            int from = LevelFor(oldXp), to = LevelFor(newXp);
            if (to <= from) return null;
            var up = new LevelUp { From = from, To = to };
            for (var l = from + 1; l <= to; l++) up.Unlocked.AddRange(UnlocksAt(l));
            if (StageFor(to) != StageFor(from)) up.NewStage = StageFor(to);
            return up;
        }
    }
}
