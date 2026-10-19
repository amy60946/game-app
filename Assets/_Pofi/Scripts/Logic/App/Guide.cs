using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Island;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>Rehberli zincirin bir adımı: hangi sayaç tamamlar, ödül XP'si, en düşük seviye.</summary>
    public sealed class GuideStep
    {
        public string Id;
        /// <summary>Tamamlayan oyuncu eylemi (GameBootstrap.RecordActivity sayacı).</summary>
        public string Counter;
        public int Xp;
        public int MinLevel = 1;
        /// <summary>Hazır mı (ör. yerleştirilecek taş var mı); null = her zaman.</summary>
        public Func<GameState, bool> Ready;
        /// <summary>Sayaç dışında "zaten yapılmış" sayılma koşulu (eski kayıtlar için); null = yok.</summary>
        public Func<GameState, bool> AlreadyDone;
        public string TextKey => "guide." + Id;
    }

    /// <summary>
    /// Sv1–3 rehberli görev zinciri (kullanıcı onayı 19 Ekim 2026; omurga analizi §11): oyun çocuğu 12 adımda gezdirir,
    /// her adım tek şey öğretir ve küçük XP verir. Sıra sabit; hazır olmayan adım (ör. taş henüz onaylanmadı) atlanır ve
    /// hazır olunca geri gelir. Ödül yalnız adım o an, canlı yapılınca verilir; önceden yapılmış adım ödülsüz geçilir.
    /// Sv3'ü geçen ya da tüm adımları bitiren oyuncuda rehber kapanır. Durum GameState.SeenTips içinde ("guide:" önekli).
    /// </summary>
    public static class Guide
    {
        public const int MaxLevel = 3;
        public const string DoneFlag = "guide_done", Prefix = "guide:", DidPrefix = "did:";

        public static readonly IReadOnlyList<GuideStep> Steps = new List<GuideStep>
        {
            new GuideStep { Id = "feed", Counter = "pet_fed", Xp = 10 },
            new GuideStep { Id = "wash", Counter = "pet_washed", Xp = 10 },
            new GuideStep { Id = "home", Counter = "home_entered", Xp = 10 },
            new GuideStep { Id = "tidy", Counter = "home_tidied", Xp = 15 },
            new GuideStep { Id = "wear", Counter = "item_equipped", Xp = 15 },
            new GuideStep { Id = "board", Counter = "board_opened", Xp = 15 },
            new GuideStep { Id = "gather", Counter = "gathered", Xp = 20 },
            new GuideStep { Id = "hut", Counter = "hut_built", Xp = 10, AlreadyDone = s => s.Gather != null && s.Gather.HutBuilt },   // kulübe zaten 40 XP verir (Gathering.HutXp)
            new GuideStep { Id = "coconut", Counter = "coconuts_caught", Xp = 20 },
            new GuideStep { Id = "shop", Counter = "item_bought", Xp = 20 },
            new GuideStep { Id = "stone", Counter = "stone_placed", Xp = 30,
                Ready = s => SunStoneBook.Available(s.SunStones) > 0, AlreadyDone = s => SunStoneBook.PlacedTotal(s.SunStones) > 0 },
            new GuideStep { Id = "cards", Counter = "card_games_played", Xp = 30, MinLevel = 3 },
        };

        public static GuideStep Get(string id) => Steps.FirstOrDefault(x => x.Id == id);

        public static bool IsDone(GameState s, GuideStep st) => s.SeenTips.Contains(Prefix + st.Id);

        /// <summary>Rehber açık mı (pet var, Sv3'ü geçmedi, bitmedi)?</summary>
        public static bool Active(GameState s, int level) =>
            s != null && s.HasPet && level <= MaxLevel && !s.SeenTips.Contains(DoneFlag);

        /// <summary>Şu an gösterilecek adım; yoksa null (rehber kapalı ya da hazır adım yok).</summary>
        public static GuideStep Current(GameState s, int level)
        {
            if (!Active(s, level)) return null;
            foreach (var st in Steps)
            {
                if (IsDone(s, st)) continue;
                if (level < st.MinLevel) continue;
                if (st.Ready != null && !st.Ready(s) && !Did(s, st)) continue;
                return st;
            }
            return null;
        }

        /// <summary>Tamamlanan adım sayısı ve toplam (panelde "3/12").</summary>
        public static int DoneCount(GameState s) => s == null ? 0 : Steps.Count(st => IsDone(s, st));

        /// <summary>Adımın eylemi daha önce yapıldı mı (sayaç, rehber işareti ya da özel koşul)?</summary>
        public static bool Did(GameState s, GuideStep st) =>
            s.SeenTips.Contains(DidPrefix + st.Counter) || s.Counters.Total(st.Counter) > 0 || (st.AlreadyDone != null && st.AlreadyDone(s));

        /// <summary>
        /// Oyuncu eylemi (RecordActivity): eylemi işaretler ve rehberi ilerletir. Sırası gelmiş ve yapılmış adımlar tamamlanır;
        /// ödül yalnız bu eylemin tamamladığı adım(lar) için döner (çağıran XP verir).
        /// </summary>
        public static List<GuideStep> OnActivity(GameState s, int level, string counter)
        {
            var rewarded = new List<GuideStep>();
            if (s == null) return rewarded;
            if (!string.IsNullOrEmpty(counter)) s.SeenTips.Add(DidPrefix + counter);
            for (var guard = 0; guard < Steps.Count; guard++)
            {
                var cur = Current(s, level);
                if (cur == null || !Did(s, cur)) break;
                s.SeenTips.Add(Prefix + cur.Id);
                if (cur.Counter == counter) rewarded.Add(cur);
            }
            if (Steps.All(st => IsDone(s, st))) s.SeenTips.Add(DoneFlag);
            return rewarded;
        }

        /// <summary>Oyun yüklenince: Sv3'ü geçmiş oyuncuda rehberi kapatır; önceden yapılmış adımları ödülsüz geçer.</summary>
        public static void Start(GameState s, int level)
        {
            if (s == null) return;
            if (level > MaxLevel) { s.SeenTips.Add(DoneFlag); return; }
            OnActivity(s, level, null);
        }
    }
}
