using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.Pet;
using Pofi.Logic.State;

namespace Pofi.Logic.Home
{
    public enum PlaceResult { Ok, NotOwned, NotPlaceable, OutOfBounds, Occupied, AlreadyPlaced, NotPlaced }

    /// <summary>
    /// Ev yerleşimi (FR-ISL-3): sahip olunan ev/dekor eşyaları ızgaraya konur, taşınır, kaldırılır.
    /// Oda seviyeyle genişler ("home_expansion" açılışı). Eşyanın gösterge etkisi yalnızca ilk yerleştirmede uygulanır.
    /// Ortadaki hücreler petin yeridir (boş kalır).
    /// </summary>
    public static class HomeLayout
    {
        public static (int w, int h) Size(bool expanded) => expanded ? (6, 5) : (4, 4);

        public static bool IsPetCell(int x, int y, bool expanded)
        {
            var (w, h) = Size(expanded);
            return (x == w / 2 || x == w / 2 - 1) && (y == h / 2 || y == (h - 1) / 2);
        }

        public static Placement At(GameState s, int x, int y) => s.Home.FirstOrDefault(p => (int)p.X == x && (int)p.Y == y);

        public static PlaceResult Place(GameState s, ItemDef item, int x, int y, bool expanded)
        {
            if (item == null || !item.IsPlaceable) return PlaceResult.NotPlaceable;
            if (!s.Inventory.Owns(item.Id)) return PlaceResult.NotOwned;
            if (s.Home.Any(p => p.ItemId == item.Id)) return PlaceResult.AlreadyPlaced;
            var check = CheckCell(s, x, y, expanded, null);
            if (check != PlaceResult.Ok) return check;
            s.Home.Add(new Placement { ItemId = item.Id, X = x, Y = y });
            if (s.HomeEffectsApplied.Add(item.Id)) PetCare.ApplyPlacement(s.Stats, item);
            return PlaceResult.Ok;
        }

        public static PlaceResult Move(GameState s, string itemId, int x, int y, bool expanded)
        {
            var p = s.Home.FirstOrDefault(q => q.ItemId == itemId);
            if (p == null) return PlaceResult.NotPlaced;
            var check = CheckCell(s, x, y, expanded, itemId);
            if (check != PlaceResult.Ok) return check;
            p.X = x; p.Y = y;
            return PlaceResult.Ok;
        }

        public static PlaceResult Rotate(GameState s, string itemId)
        {
            var p = s.Home.FirstOrDefault(q => q.ItemId == itemId);
            if (p == null) return PlaceResult.NotPlaced;
            p.Rotation = (p.Rotation + 90) % 360;
            return PlaceResult.Ok;
        }

        public static PlaceResult Remove(GameState s, string itemId) =>
            s.Home.RemoveAll(q => q.ItemId == itemId) > 0 ? PlaceResult.Ok : PlaceResult.NotPlaced;

        /// <summary>Sahip olunan ama yerleştirilmemiş ev/dekor eşyaları.</summary>
        public static List<ItemDef> Unplaced(GameState s, GameData data) =>
            s.Inventory.Owned.Select(data.Item).Where(i => i != null && i.IsPlaceable && s.Home.All(p => p.ItemId != i.Id)).ToList();

        /// <summary>Oda küçülürse (olmaz ama güvenlik) dışarıda kalan eşyalar kaldırılır.</summary>
        public static void Clamp(GameState s, bool expanded)
        {
            var (w, h) = Size(expanded);
            s.Home.RemoveAll(p => p.X < 0 || p.Y < 0 || p.X >= w || p.Y >= h);
        }

        private static PlaceResult CheckCell(GameState s, int x, int y, bool expanded, string ignoreId)
        {
            var (w, h) = Size(expanded);
            if (x < 0 || y < 0 || x >= w || y >= h || IsPetCell(x, y, expanded)) return PlaceResult.OutOfBounds;
            var other = At(s, x, y);
            if (other != null && other.ItemId != ignoreId) return PlaceResult.Occupied;
            return PlaceResult.Ok;
        }
    }
}
