using System.Collections.Generic;
using Pofi.Logic.Data;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>
    /// Pet seçimi / değiştirme (FR-PET-1, FR-PET-7). Değiştirme ebeveyn kapısının arkasındadır.
    /// Envanter, coin, seviye korunur; yeni pete uymayan giyilenler çıkarılır (envanterde kalır).
    /// Ad sorulmaz: hep <see cref="PetRoster.Name"/> (24 Ekim 2026, kullanıcı).
    /// </summary>
    public static class PetChange
    {
        /// <summary>Ayarlardan "Pet'i değiştir": seçim ekranına dönülür (isim ve seçim temizlenir).</summary>
        public static void Begin(GameState s)
        {
            s.PetId = null;
            s.PetName = null;
        }

        /// <summary>
        /// Seçim onaylandı: ad <see cref="PetRoster.Name"/>; <paramref name="starter"/> verilirse hoş geldin hediyesi (bir kez).
        /// Çıkarılan (uymayan) eşya kimliklerini döndürür.
        /// </summary>
        public static List<string> Choose(GameState s, string petId, GameData data, StarterKit starter = null)
        {
            s.PetId = petId;
            s.PetName = PetRoster.Name;
            starter?.GiveOnce(s, data);
            var pet = data.Pet(petId);
            return pet == null ? new List<string>() : s.Inventory.RefitFor(pet, data.Item);
        }
    }
}
