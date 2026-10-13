using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;

namespace Pofi.Logic.Data
{
    /// <summary>
    /// Tüm oyun verisi (pet türleri, eşyalar, seviye tablosu). Dosya okuma dışarıdan verilir:
    /// Unity'de Resources/TextAsset, testlerde disk. Validate() veri hatalarını erken yakalar.
    /// </summary>
    public sealed class GameData
    {
        public IReadOnlyList<PetSpeciesDef> Pets { get; }
        public IReadOnlyList<ItemDef> Items { get; }
        public LevelTableDef Levels { get; }

        private readonly Dictionary<string, PetSpeciesDef> _pets;
        private readonly Dictionary<string, ItemDef> _items;

        public GameData(IReadOnlyList<PetSpeciesDef> pets, IReadOnlyList<ItemDef> items, LevelTableDef levels)
        {
            Pets = pets; Items = items; Levels = levels;
            _pets = pets.GroupBy(p => p.Id).ToDictionary(g => g.Key, g => g.First());
            _items = items.GroupBy(i => i.Id).ToDictionary(g => g.Key, g => g.First());
        }

        /// <param name="readText">dosya adı ("pets.json") → içerik</param>
        public static GameData Load(Func<string, string> readText)
        {
            var pets = JsonConvert.DeserializeObject<PetsFile>(readText("pets.json")).Pets;
            var items = JsonConvert.DeserializeObject<ItemsFile>(readText("items.json")).Items;
            var levels = JsonConvert.DeserializeObject<LevelTableDef>(readText("levels.json"));
            return new GameData(pets, items, levels);
        }

        public PetSpeciesDef Pet(string id) => _pets.TryGetValue(id, out var p) ? p : null;
        public ItemDef Item(string id) => _items.TryGetValue(id, out var i) ? i : null;

        /// <summary>Veri tutarlılığı. Boş liste = hatasız.</summary>
        public List<string> Validate()
        {
            var errors = new List<string>();
            void Dup<T>(IEnumerable<T> list, Func<T, string> id, string kind)
            {
                foreach (var g in list.GroupBy(id).Where(g => g.Count() > 1)) errors.Add($"{kind} kimliği tekrar ediyor: {g.Key}");
            }
            Dup(Pets, p => p.Id, "pet");
            Dup(Items, i => i.Id, "eşya");
            if (Pets.Count != 12) errors.Add($"12 pet bekleniyordu, {Pets.Count} var");

            string[] hats = { "normal", "ear_holes", "center_hole", "antenna_holes", "mane_fit", "raised" };
            string[] backs = { "normal", "tail_hole", "on_shell", "flat_only", "none" };
            foreach (var p in Pets)
            {
                if (!hats.Contains(p.Fit.Hat)) errors.Add($"{p.Id}: bilinmeyen şapka uyumu {p.Fit.Hat}");
                if (!backs.Contains(p.Fit.Back)) errors.Add($"{p.Id}: bilinmeyen sırt uyumu {p.Fit.Back}");
                if (p.Fit.Body != "full" && p.Fit.Body != "apron_only") errors.Add($"{p.Id}: bilinmeyen gövde uyumu {p.Fit.Body}");
                if (p.Fit.Glasses != "normal" && p.Fit.Glasses != "clip") errors.Add($"{p.Id}: bilinmeyen gözlük uyumu {p.Fit.Glasses}");
                if (p.Fit.Hands != "paw" && p.Fit.Hands != "flipper") errors.Add($"{p.Id}: bilinmeyen el tipi {p.Fit.Hands}");
            }

            foreach (var i in Items)
            {
                if (!ItemCategory.All.Contains(i.Category)) errors.Add($"{i.Id}: bilinmeyen kategori {i.Category}");
                if (i.Price <= 0) errors.Add($"{i.Id}: fiyat pozitif olmalı");
                if (i.Level < 1 || i.Level > Levels.MaxLevel) errors.Add($"{i.Id}: seviye 1–{Levels.MaxLevel} dışında");
                if (i.IsWearable && !Slot.All.Contains(i.Slot)) errors.Add($"{i.Id}: bilinmeyen yuva {i.Slot}");
                if ((i.Slot == Slot.Head || i.Slot == Slot.Eyes) && (i.Variants == null || i.Variants.Count == 0))
                    errors.Add($"{i.Id}: şapka/gözlük varyant listesi boş");
                if (i.Slot == Slot.Body && i.Cut != "full" && i.Cut != "apron") errors.Add($"{i.Id}: gövde kesimi full|apron olmalı");
                if (i.Category == ItemCategory.Seed && (Item(i.Grows) == null || i.GrowMinutes <= 0))
                    errors.Add($"{i.Id}: tohumun ürünü ya da süresi geçersiz");
                if ((i.Category == ItemCategory.Food || i.Category == ItemCategory.Cleaning) && i.Effects.Count == 0)
                    errors.Add($"{i.Id}: tüketilebilir eşyanın etkisi yok");
            }

            if (Levels.XpToNext.Count != Levels.MaxLevel - 1) errors.Add("xpToNext uzunluğu maxLevel-1 olmalı");
            for (var k = 1; k < Levels.XpToNext.Count; k++)
                if (Levels.XpToNext[k] <= Levels.XpToNext[k - 1]) errors.Add($"XP eşikleri artmalı (Sv{k + 1})");
            foreach (var key in Levels.Unlocks.Keys)
                if (!int.TryParse(key, out var lv) || lv < 1 || lv > Levels.MaxLevel) errors.Add($"açılış tablosunda geçersiz seviye {key}");
            return errors;
        }
    }
}
