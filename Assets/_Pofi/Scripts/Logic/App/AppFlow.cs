using Pofi.Logic.Services;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Oyunun ana ekranları (M1–M2 dikey dilim). Ad ekranı yok (24 Ekim 2026, kullanıcı: "Ad hep Okti kalsın"):
    /// pet seçilince ad <see cref="PetRoster.Name"/> olur.
    /// </summary>
    public enum AppScreen { Login, PetSelect, Home }

    /// <summary>Pet hazır olduktan sonra alt menüden açılan sayfalar.</summary>
    public enum AppPage { Home, Map, Tasks, Shop, Wardrobe, MiniGame, Cards, Garden, Album, Settings, Decorate, Festival, Lighthouse, Mail }

    /// <summary>
    /// Hangi ekranın gösterileceğine karar verir. Unity katmanı yalnızca sonucu çizer;
    /// kural burada ve birim testlidir.
    /// </summary>
    public static class AppFlow
    {
        public static AppScreen Decide(ChildSession session, GameState state)
        {
            if (session == null) return AppScreen.Login;
            // adı olmayan kayıt (yüklemede düzeltilmemişse) tanışma ekranına döner; orada ad Okti olur
            if (state == null || !state.HasPet) return AppScreen.PetSelect;
            return AppScreen.Home;
        }

        /// <summary>Kayıt başka bir çocuğa aitse (cihazda kod değişti) yeni kayıt açılır.</summary>
        public static bool BelongsTo(GameState state, ChildSession session) =>
            state != null && session != null && state.ChildId == session.ChildId;
    }
}
