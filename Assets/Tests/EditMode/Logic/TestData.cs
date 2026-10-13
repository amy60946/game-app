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
