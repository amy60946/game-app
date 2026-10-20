using System.Collections.Generic;
using Newtonsoft.Json;

namespace Pofi.Logic.Data
{
    // Oyun verisinin C# karşılıkları. Kaynak: Assets/_Pofi/Resources/Data/*.json
    // Alan adları JSON ile birebir (camelCase).

    public sealed class PetFit
    {
        [JsonProperty("hat")] public string Hat = "normal";          // normal|ear_holes|center_hole|antenna_holes|mane_fit|raised
        [JsonProperty("glasses")] public string Glasses = "normal";  // normal|clip
        [JsonProperty("body")] public string Body = "full";          // full|apron_only
        [JsonProperty("back")] public string Back = "normal";        // normal|tail_hole|on_shell|flat_only|none
        [JsonProperty("hands")] public string Hands = "paw";         // paw|flipper
    }

    public sealed class PetSpeciesDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("species")] public string Species;
        [JsonProperty("mainColor")] public string MainColor;
        [JsonProperty("accentColor")] public string AccentColor;
        [JsonProperty("feature")] public string Feature;
        [JsonProperty("voiceId")] public string VoiceId;
        [JsonProperty("personalityAnims")] public List<string> PersonalityAnims = new List<string>();
        [JsonProperty("fit")] public PetFit Fit = new PetFit();
        /// <summary>Seçimden kaldırıldı (20 Ekim 2026: tek pet Okti); eski kayıtlar ilk seçilebilir pete geçer.</summary>
        [JsonProperty("retired")] public bool Retired;
    }

    public static class ItemCategory
    {
        public const string Food = "food", Cleaning = "cleaning", Clothes = "clothes", Accessory = "accessory",
            Home = "home", Seed = "seed", Decor = "decor";
        public static readonly string[] All = { Food, Cleaning, Clothes, Accessory, Home, Seed, Decor };
    }

    public static class Slot
    {
        public const string Head = "head", Eyes = "eyes", Body = "body", Back = "back", Hand = "hand";
        public static readonly string[] All = { Head, Eyes, Body, Back, Hand };
    }

    public sealed class ItemDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("category")] public string Category;
        [JsonProperty("price")] public int Price;
        [JsonProperty("level")] public int Level = 1;
        [JsonProperty("effects")] public Dictionary<string, float> Effects = new Dictionary<string, float>();
        [JsonProperty("slot")] public string Slot;                  // giyilebilirler
        [JsonProperty("variants")] public List<string> Variants;    // şapka / gözlük
        [JsonProperty("cut")] public string Cut;                    // gövde: full|apron
        [JsonProperty("flat")] public bool Flat;                    // sırt: düz mü
        [JsonProperty("glove")] public bool Glove;                  // el: eldiven mi
        [JsonProperty("grows")] public string Grows;                // tohum → yiyecek
        [JsonProperty("growMinutes")] public int GrowMinutes;
        [JsonProperty("premium")] public bool Premium;

        [JsonIgnore] public bool IsWearable => !string.IsNullOrEmpty(Slot);
        [JsonIgnore] public bool IsConsumable => Category == ItemCategory.Food || Category == ItemCategory.Cleaning || Category == ItemCategory.Seed;
        [JsonIgnore] public bool IsPlaceable => Category == ItemCategory.Home || Category == ItemCategory.Decor;
    }

    public sealed class LevelTableDef
    {
        [JsonProperty("maxLevel")] public int MaxLevel;
        [JsonProperty("xpToNext")] public List<int> XpToNext = new List<int>();
        [JsonProperty("growth")] public Dictionary<string, int> Growth = new Dictionary<string, int>();
        [JsonProperty("unlocks")] public Dictionary<string, List<string>> Unlocks = new Dictionary<string, List<string>>();
    }

    public sealed class CollectionEntryDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("category")] public string Category;   // fish|bug|shell|resident
        [JsonProperty("rarity")] public int Rarity = 1;
        [JsonProperty("level")] public int Level = 1;
        [JsonProperty("time")] public string Time = "any";   // day|night|any
    }

    public sealed class BadgeDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("counter")] public string Counter;
        [JsonProperty("target")] public int Target;
        [JsonProperty("xp")] public int Xp;
    }

    public sealed class DailyQuestDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("text")] public string Text;
        [JsonProperty("counter")] public string Counter;
        [JsonProperty("target")] public int Target;
        [JsonProperty("xp")] public int Xp;
        [JsonProperty("unlock")] public string Unlock;
    }

    internal sealed class CollectionFile { [JsonProperty("entries")] public List<CollectionEntryDef> Entries = new List<CollectionEntryDef>(); }
    internal sealed class BadgesFile { [JsonProperty("badges")] public List<BadgeDef> Badges = new List<BadgeDef>(); }
    internal sealed class DailyQuestsFile
    {
        [JsonProperty("perDay")] public int PerDay = 3;
        [JsonProperty("quests")] public List<DailyQuestDef> Quests = new List<DailyQuestDef>();
    }

    internal sealed class PetsFile { [JsonProperty("pets")] public List<PetSpeciesDef> Pets = new List<PetSpeciesDef>(); }
    internal sealed class ItemsFile { [JsonProperty("items")] public List<ItemDef> Items = new List<ItemDef>(); }
}
