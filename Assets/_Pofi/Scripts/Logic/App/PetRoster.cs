using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Seçilebilir pet listesi (20 Ekim 2026, kullanıcı: tek pet Okti, çocuk / ergen / yetişkin evreleriyle). Emekli pete sahip
    /// eski kayıt ilk seçilebilir pete geçer; eşyaları ve ilerlemesi korunur.
    /// Ad hep "Okti" (24 Ekim 2026, kullanıcı): çocuk ad yazmaz (gerçek adını yazmasın), sesli okuma kayıtları da bu adla.
    /// </summary>
    public static class PetRoster
    {
        /// <summary>Petin tek adı. Sesli okuma kayıtları (Resources/Voice) bu adla üretildi.</summary>
        public const string Name = "Okti";

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

        /// <summary>
        /// Yüklemede: pet seçilmiş kayıtta ad <see cref="Name"/> olur (eski kayıtta çocuğun verdiği ad da). Ad hiç konmamışsa
        /// (eski akışta ad ekranında kalmış) <paramref name="starter"/> hoş geldin hediyesi de verilir. Değiştiyse true (çağıran kaydeder).
        /// </summary>
        public static bool FixName(GameState s, StarterKit starter = null, GameData data = null)
        {
            if (s == null || string.IsNullOrEmpty(s.PetId) || s.PetName == Name) return false;
            var unnamed = string.IsNullOrEmpty(s.PetName);
            s.PetName = Name;
            if (unnamed && starter != null && data != null) starter.GiveOnce(s, data);
            return true;
        }
    }
}
