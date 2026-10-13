using Pofi.Logic.Services;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>Oyunun ana ekranları (M1–M2 dikey dilim).</summary>
    public enum AppScreen { Login, PetSelect, PetName, Home }

    /// <summary>
    /// Hangi ekranın gösterileceğine karar verir. Unity katmanı yalnızca sonucu çizer;
    /// kural burada ve birim testlidir.
    /// </summary>
    public static class AppFlow
    {
        public static AppScreen Decide(ChildSession session, GameState state)
        {
            if (session == null) return AppScreen.Login;
            if (state == null || string.IsNullOrEmpty(state.PetId)) return AppScreen.PetSelect;
            if (string.IsNullOrEmpty(state.PetName)) return AppScreen.PetName;
            return AppScreen.Home;
        }

        /// <summary>Kayıt başka bir çocuğa aitse (cihazda kod değişti) yeni kayıt açılır.</summary>
        public static bool BelongsTo(GameState state, ChildSession session) =>
            state != null && session != null && state.ChildId == session.ChildId;
    }
}
