using System;
using System.IO;
using Pofi.Logic.Data;

namespace Pofi.Tests.Logic
{
    /// <summary>Gerçek oyun verisini (JSON) testlerde yükler: .NET testinde çıktı klasöründen, Unity'de proje kökünden.</summary>
    public static class TestData
    {
        private static GameData _cached;

        public static GameData Load() => _cached ??= GameData.Load(ReadText);

        /// <summary>Pişmiş v6 adası (Resources/Data/island_v6.bytes + island_v6_layout.json).</summary>
        public static Pofi.Logic.Island.BakedIsland Island() => _island ??= Pofi.Logic.Island.BakedIsland.Load(File.ReadAllBytes(PathOf("island_v6.bytes")), ReadText("island_v6_layout.json"));
        private static Pofi.Logic.Island.BakedIsland _island;

        /// <summary>Oyundaki gibi kurulan ada arazisi (pişmiş v6).</summary>
        public static Pofi.Logic.Island.IslandTerrain Terrain()
        {
            if (_terrain != null) return _terrain;
            var map = new Pofi.Logic.Island.IslandMap(ReadText("regions.json"), new Pofi.Logic.Progression.LevelTable(Load().Levels));
            return _terrain = new Pofi.Logic.Island.IslandTerrain(map.Regions, map.Terrain, Island());
        }
        private static Pofi.Logic.Island.IslandTerrain _terrain;

        /// <summary>Data klasörünün yolu (Resources/Data; .NET testinde çıktı kopyası değil, depodaki asıl klasör tercih edilir).</summary>
        public static string PathOfData()
        {
            var repo = Path.Combine(Directory.GetCurrentDirectory(), "Assets", "_Pofi", "Resources", "Data");
            if (Directory.Exists(repo)) return repo;
            for (var d = new DirectoryInfo(AppContext.BaseDirectory); d != null; d = d.Parent)
            {
                var p = Path.Combine(d.FullName, "Assets", "_Pofi", "Resources", "Data");
                if (Directory.Exists(p)) return p;
            }
            return Path.GetDirectoryName(PathOf("pets.json"));
        }

        private static string PathOf(string name)
        {
            string[] roots =
            {
                Path.Combine(AppContext.BaseDirectory, "Data"),
                Path.Combine(Directory.GetCurrentDirectory(), "Assets", "_Pofi", "Resources", "Data"),
            };
            foreach (var r in roots)
                if (File.Exists(Path.Combine(r, "pets.json"))) return Path.Combine(r, name);
            throw new FileNotFoundException("Oyun verisi bulunamadı");
        }

        /// <summary>Data klasöründen bir dosyanın metni (ör. "tr.json").</summary>
        public static string ReadText(string name)
        {
            string[] roots =
            {
                Path.Combine(AppContext.BaseDirectory, "Data"),
                Path.Combine(Directory.GetCurrentDirectory(), "Assets", "_Pofi", "Resources", "Data"),
            };
            foreach (var r in roots)
                if (File.Exists(Path.Combine(r, "pets.json")))
                    return File.ReadAllText(Path.Combine(r, name));
            throw new FileNotFoundException("Oyun verisi bulunamadı");
        }
    }
}
