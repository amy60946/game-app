using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Seçilebilir pet listesi (20 Ekim 2026, kullanıcı: tek pet Okti, çocuk / ergen / yetişkin evreleriyle). Emekli pete sahip
    /// eski kayıt ilk seçilebilir pete geçer; çocuğun verdiği ad, eşyaları ve ilerlemesi korunur.
    /// </summary>
    public static class PetRoster
    {
        /// <summary>Kaydı geçirir; değiştiyse true (çağıran kaydeder).</summary>
        public static bool Migrate(GameState s, GameData data)
        {
            if (s == null || data == null || string.IsNullOrEmpty(s.PetId)) return false;
            var cur = data.Pet(s.PetId);
            if (cur != null && !cur.Retired) return false;
            var next = data.ActivePets.FirstOrDefault();
            if (next == null || next.Id == s.PetId) return false;
            s.PetId = next.Id;
            return true;
        }
    }
}
