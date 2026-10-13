using System.Collections.Generic;
using Pofi.Logic.Data;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Pet seçimi / değiştirme (FR-PET-1, FR-PET-7). Değiştirme ebeveyn kapısının arkasındadır.
    /// Envanter, coin, seviye korunur; yeni pete uymayan giyilenler çıkarılır (envanterde kalır), isim yeniden sorulur.
    /// </summary>
    public static class PetChange
    {
        /// <summary>Ayarlardan "Pet'i değiştir": seçim ekranına dönülür (isim ve seçim temizlenir).</summary>
        public static void Begin(GameState s)
        {
            s.PetId = null;
            s.PetName = null;
        }

        /// <summary>Seçim onaylandı. Çıkarılan (uymayan) eşya kimliklerini döndürür.</summary>
        public static List<string> Choose(GameState s, string petId, GameData data)
        {
            s.PetId = petId;
            s.PetName = null;
            var pet = data.Pet(petId);
            return pet == null ? new List<string>() : s.Inventory.RefitFor(pet, data.Item);
        }
    }
}
