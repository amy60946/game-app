using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Pofi.Logic.Progression;

namespace Pofi.Logic.Island
{
    public sealed class RegionDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("pos")] public float[] Pos = { 0f, 0f };
        [JsonProperty("target")] public string Target;
        [JsonProperty("color")] public string Color;
        [JsonProperty("shape")] public string Shape;

        public float X => Pos != null && Pos.Length > 0 ? Pos[0] : 0f;
        public float Z => Pos != null && Pos.Length > 1 ? Pos[1] : 0f;
    }

    public enum RegionTargetKind { Page, MiniGame, Cards, Soon }

    public sealed class RegionView
    {
        public RegionDef Region;
        public bool Unlocked;
        public int UnlockLevel;
        public bool IsNew;           // açıldı ama henüz ziyaret edilmedi (havuç etkisi / parıltı)
    }

    /// <summary>
    /// Ada haritası (M5, FR-ISL-1, FR-PROG-2): bölgeler, kilit durumu ve "yeni" işareti. Açılış seviyesi
    /// levels.json'dan gelir; harita yalnızca konum/hedefi bilir.
    /// </summary>
    public sealed class IslandMap
    {
        private sealed class File { [JsonProperty("regions")] public List<RegionDef> Regions = new List<RegionDef>(); }

        public IReadOnlyList<RegionDef> Regions { get; }
        private readonly LevelTable _levels;

        public IslandMap(string json, LevelTable levels)
        {
            Regions = JsonConvert.DeserializeObject<File>(json).Regions;
            _levels = levels;
        }

        public RegionDef Find(string id) => Regions.FirstOrDefault(r => r.Id == id);

        public List<RegionView> View(int level, ICollection<string> visited)
        {
            return Regions.Select(r =>
            {
                var at = _levels.UnlockLevel(r.Id);
                var open = level >= at;
                return new RegionView { Region = r, Unlocked = open, UnlockLevel = at, IsNew = open && at > 1 && !visited.Contains(r.Id) };
            }).ToList();
        }

        /// <summary>Kilitli bölgeler arasında en yakın açılacak olan (havuç: "Seviye N'de açılır").</summary>
        public RegionView NextToUnlock(int level, ICollection<string> visited) =>
            View(level, visited).Where(v => !v.Unlocked).OrderBy(v => v.UnlockLevel).FirstOrDefault();

        public static RegionTargetKind KindOf(string target, out string arg)
        {
            arg = null;
            if (string.IsNullOrEmpty(target) || target == "soon") return RegionTargetKind.Soon;
            if (target == "cards") return RegionTargetKind.Cards;
            var i = target.IndexOf(':');
            if (i > 0) arg = target.Substring(i + 1);
            if (target.StartsWith("page:")) return RegionTargetKind.Page;
            if (target.StartsWith("minigame:")) return RegionTargetKind.MiniGame;
            return RegionTargetKind.Soon;
        }
    }
}
