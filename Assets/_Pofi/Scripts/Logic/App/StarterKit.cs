using System.Collections.Generic;
using Newtonsoft.Json;
using Pofi.Logic.Data;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Pet ilk kez isimlendirilince verilen hoş geldin hediyesi (Data/start.json). Bir kez verilir;
    /// kayıtta <see cref="GameState.StarterGiven"/> işaretlenir. Coin vermez: coin yalnızca gerçek görevden gelir.
    /// </summary>
    public sealed class StarterKit
    {
        private sealed class File
        {
            [JsonProperty("items")] public Dictionary<string, int> Items = new Dictionary<string, int>();
        }

        public IReadOnlyDictionary<string, int> Items { get; }

        public StarterKit(string json)
        {
            Items = string.IsNullOrWhiteSpace(json)
                ? new Dictionary<string, int>()
                : (JsonConvert.DeserializeObject<File>(json)?.Items ?? new Dictionary<string, int>());
        }

        /// <summary>Hediyeyi bir kez verir. Bilinmeyen eşya kimlikleri atlanır. Verildiyse true.</summary>
        public bool GiveOnce(GameState state, GameData data)
        {
            if (state.StarterGiven) return false;
            foreach (var kv in Items)
            {
                var item = data.Item(kv.Key);
                if (item != null && kv.Value > 0) state.Inventory.Add(item, kv.Value);
            }
            state.StarterGiven = true;
            return true;
        }
    }
}
