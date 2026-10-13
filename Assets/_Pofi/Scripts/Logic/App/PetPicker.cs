using System;
using System.Collections.Generic;

namespace Pofi.Logic.App
{
    /// <summary>Pet seçim karuseli: sonsuz döngü (12'den sonra 1), odaktaki pet ve son onay.</summary>
    public sealed class PetPicker
    {
        private readonly IReadOnlyList<string> _ids;

        public PetPicker(IReadOnlyList<string> petIds, int start = 0)
        {
            if (petIds == null || petIds.Count == 0) throw new ArgumentException("En az bir pet gerekli", nameof(petIds));
            _ids = petIds;
            Index = Wrap(start);
        }

        public int Index { get; private set; }
        public int Count => _ids.Count;
        public string Current => _ids[Index];

        public string Next() { Index = Wrap(Index + 1); return Current; }
        public string Prev() { Index = Wrap(Index - 1); return Current; }

        /// <summary>Kaydırma hareketi: sola kaydırınca sonraki, sağa kaydırınca önceki. Kısa hareket yok sayılır.</summary>
        public string Swipe(float deltaX, float threshold)
        {
            if (deltaX <= -threshold) return Next();
            if (deltaX >= threshold) return Prev();
            return Current;
        }

        public void JumpTo(string id)
        {
            for (var i = 0; i < _ids.Count; i++)
                if (_ids[i] == id) { Index = i; return; }
        }

        private int Wrap(int i) => ((i % _ids.Count) + _ids.Count) % _ids.Count;
    }
}
