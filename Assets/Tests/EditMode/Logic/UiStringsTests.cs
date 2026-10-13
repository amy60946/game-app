using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using NUnit.Framework;
using Pofi.Logic.Core;

namespace Pofi.Tests.Logic
{
    /// <summary>Unity ekranlarında kullanılan her metin anahtarı tr.json'da olmalı (yoksa ekranda "[anahtar]" görünür).</summary>
    public class UiStringsTests
    {
        private static string FindRuntimeDir()
        {
            foreach (var start in new[] { AppContext.BaseDirectory, Directory.GetCurrentDirectory() })
            {
                var d = new DirectoryInfo(start);
                while (d != null)
                {
                    var p = Path.Combine(d.FullName, "Assets", "_Pofi", "Scripts", "Runtime");
                    if (Directory.Exists(p)) return p;
                    d = d.Parent;
                }
            }
            return null;
        }

        [Test]
        public void Ekranlardaki_metin_anahtarlari_tabloda_var()
        {
            var dir = FindRuntimeDir();
            if (dir == null) Assert.Ignore("Runtime klasörü bulunamadı");
            var loc = new Localization(TestData.ReadText("tr.json"));
            var rx = new Regex(@"(?:\bT|Loc\.Get|app\.Loc\.Get)\(\s*""([a-z_]+\.[a-zA-Z0-9_.]+)""");
            var missing = Directory.GetFiles(dir, "*.cs", SearchOption.AllDirectories)
                .SelectMany(f => rx.Matches(File.ReadAllText(f)).Cast<Match>().Select(m => m.Groups[1].Value + "  (" + Path.GetFileName(f) + ")"))
                .Where(k => !k.Split(' ')[0].EndsWith(".") && !loc.Has(k.Split(' ')[0]))
                .Distinct().ToList();
            Assert.IsEmpty(missing, string.Join("\n", missing));
        }

        [Test]
        public void Birlesik_anahtarlar_tabloda_var()
        {
            var loc = new Localization(TestData.ReadText("tr.json"));
            var keys = new[] { "food", "cleaning", "clothes", "accessory", "seed", "home" }.Select(c => "shop.tab." + c)
                .Concat(Pofi.Logic.Data.Slot.All.Select(x => "wardrobe.slot." + x))
                .Concat(new[] { "bug", "shell", "resident", "fish" }.Select(c => "album.cat." + c))
                .Concat(Pofi.Logic.App.CardSession.Games.SelectMany(g => new[] { "cards.game." + g, "cards.desc." + g }))
                .Concat(new[] { "Red", "Yellow", "Green", "Blue" }.Select(c => "cards.color." + c))
                .Concat(new[] { "Skip", "Reverse", "DrawTwo", "Wild", "WildDrawFour" }.Select(k => "cards.kind." + k))
                .Concat(new[] { "coconut", "help_pet", "swim", "surf", "ski", "fishing" }.Select(g => "mg." + g + ".title"));
            foreach (var k in keys) Assert.IsTrue(loc.Has(k), k);
        }
    }
}
