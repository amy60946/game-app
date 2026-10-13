using System;
using System.Collections.Generic;

namespace Pofi.Logic.Cards
{
    /// <summary>
    /// Masa oyunları ortak altyapısı (FR-CARD-4). Her oyun kurallarını bu arayüzle tanımlar; sıra tabanlı akış,
    /// bot hamlesi ve sonuç (XP) ortak koddan yürür. Yeni oyun eklemek = yeni IGameRules.
    /// </summary>
    public interface IGameRules<TState, TMove>
    {
        int PlayerCount(TState s);
        int CurrentPlayer(TState s);
        IReadOnlyList<TMove> LegalMoves(TState s);
        void Apply(TState s, TMove move);
        bool IsOver(TState s);
        int Winner(TState s);            // -1: henüz yok / berabere
    }

    public interface IBot<TState, TMove>
    {
        TMove Choose(TState s, IReadOnlyList<TMove> legal, Random rng);
    }

    /// <summary>
    /// Zorluk uyarlama (FR-CARD-2): yaş bandı başlangıç zorluğunu verir; çocuk üst üste kaybederse bot yumuşar,
    /// üst üste kazanırsa biraz zorlaşır. Değer 0 (çok kolay) – 1 (zor).
    /// </summary>
    [Serializable]
    public sealed class DifficultyAdapter
    {
        public float Level;
        public int Streak; // + kazanma serisi, − kaybetme serisi

        public DifficultyAdapter(float start) { Level = Clamp(start); }

        public void Record(bool childWon)
        {
            Streak = childWon ? Math.Max(1, Streak + 1) : Math.Min(-1, Streak - 1);
            if (Streak >= 2) Level = Clamp(Level + 0.1f);
            if (Streak <= -2) Level = Clamp(Level - 0.15f); // kaybederken daha hızlı yumuşa: çocuğu bunaltma
        }

        private static float Clamp(float v) => Math.Max(0f, Math.Min(1f, v));
    }

    /// <summary>Masa oyunu XP'si (FR-CARD-3): kazanınca tam, kaybedince az (cesaret ödülü).</summary>
    public static class CardRewards
    {
        public static int Xp(bool won, float difficulty) => won ? (int)Math.Round(20 + 20 * difficulty) : 8;
    }
}
