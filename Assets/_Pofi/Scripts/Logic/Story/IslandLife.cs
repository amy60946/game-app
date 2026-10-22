using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Meta;

namespace Pofi.Logic.Story
{
    public enum Season { Spring, Summer, Autumn, Winter }

    /// <summary>Gerçek takvimle mevsim (H6). Mevsim eşyası alınırsa kalır; kaçırılan ertesi yıl yine gelir.</summary>
    public static class Seasons
    {
        public static Season For(DateTime local)
        {
            var m = local.Month;
            if (m >= 3 && m <= 5) return Season.Spring;
            if (m >= 6 && m <= 8) return Season.Summer;
            if (m >= 9 && m <= 11) return Season.Autumn;
            return Season.Winter;
        }

        /// <summary>Yılbaşı ışıkları: 20 Aralık – 5 Ocak.</summary>
        public static bool HolidayLights(DateTime local) =>
            (local.Month == 12 && local.Day >= 20) || (local.Month == 1 && local.Day <= 5);

        /// <summary>Kışın tepelerde kar (kıyı ve kumsal hariç; görünümde yükseklikten).</summary>
        public static bool Snow(DateTime local) => For(local) == Season.Winter;

        public static string Key(Season s) => s.ToString().ToLowerInvariant();
    }

    /// <summary>
    /// Okti'nin günlüğü (H5): günün 2–3 anısı. Puan, not ya da karşılaştırma yok (klinik sınır).
    /// Satırlar tr.json "diary.*" anahtarlarıyla yazılır; sayaçlar günün etkinliğinden (Counters.Today) gelir.
    /// </summary>
    public static class Diary
    {
        public const int Keep = 60, MaxLines = 3;

        // öncelik sırası: gerçek görev en üstte, sonra yapılan şeyler; bakım (besle/yıka) en sonda
        private static readonly (string counter, string key)[] Order =
        {
            ("tasks_approved", "diary.task"), ("stone_placed", "diary.stone"), ("hut_built", "diary.hut"),
            ("gathered", "diary.gathered"), ("harvests", "diary.harvest"), ("item_bought", "diary.bought"),
            ("card_games_played", "diary.cards"), ("minigames_played", "diary.minigame"), ("home_tidied", "diary.tidy"),
            ("item_equipped", "diary.dressed"), ("pet_fed", "diary.fed"), ("pet_washed", "diary.washed"),
        };

        public static List<DiaryLine> Compose(Counters c)
        {
            var lines = new List<DiaryLine>();
            foreach (var (counter, key) in Order)
            {
                var n = c.TodayCount(counter);
                if (n <= 0) continue;
                lines.Add(new DiaryLine { Key = key, Args = new[] { n.ToString() } });
                if (lines.Count >= MaxLines) break;
            }
            return lines;
        }

        /// <summary>Bugünün sayfasını yazar ya da günceller (boş günde sayfa açılmaz). En yeni 60 gün tutulur.</summary>
        public static DiaryEntry Record(StoryState st, Counters c, DateTime local)
        {
            c.Roll(local);
            var day = Economy.XpSystem.DayNumber(local);
            var lines = Compose(c);
            var e = st.Diary.FirstOrDefault(x => x.Day == day);
            if (lines.Count == 0) return e;
            if (e == null) { e = new DiaryEntry { Day = day }; st.Diary.Add(e); }
            e.Lines = lines;
            st.Diary.Sort((a, b) => a.Day.CompareTo(b.Day));
            if (st.Diary.Count > Keep) st.Diary.RemoveRange(0, st.Diary.Count - Keep);
            return e;
        }
    }

    /// <summary>
    /// Adalıların istekleri (H4): günde en çok bir yeni istek, aynı anda en çok iki. Süre dolmaz, bekler.
    /// Ödül eşya + XP + dostluk; coin asla.
    /// </summary>
    public static class ResidentRequests
    {
        public const int MaxOpen = 2;

        public static void Refresh(StoryState st, IList<RequestDef> defs, int day, int level, string childId)
        {
            if (st.RequestDay == day) return;
            st.RequestDay = day;
            if (st.Requests.Count >= MaxOpen) return;
            var pool = defs.Where(d => d.MinLevel <= level && st.Requests.All(o => o.Id != d.Id)).ToList();
            if (pool.Count == 0) return;
            var pick = pool[(int)((uint)StableHash((childId ?? "") + ":" + day) % (uint)pool.Count)];
            st.Requests.Add(new OpenRequest { Id = pick.Id, Day = day });
        }

        public static bool CanFulfill(RequestDef d, Func<string, int> have) => d != null && have(d.Need) >= d.Count;

        /// <summary>İsteği yerine getirir: malzemeyi alır (take), dostluğu artırır, isteği kapatır. Olmazsa null.</summary>
        public static RequestDef Fulfill(StoryState st, IList<RequestDef> defs, string id, Func<string, int> have, Action<string, int> take)
        {
            var open = st.Requests.FirstOrDefault(o => o.Id == id);
            var d = defs.FirstOrDefault(x => x.Id == id);
            if (open == null || !CanFulfill(d, have)) return null;
            take(d.Need, d.Count);
            st.Requests.Remove(open);
            st.Friendship[d.Who] = (st.Friendship.TryGetValue(d.Who, out var f) ? f : 0) + 1;
            return d;
        }

        internal static int StableHash(string s)
        {
            unchecked
            {
                var h = 23;
                foreach (var ch in s) h = h * 31 + ch;
                return h;
            }
        }
    }

    /// <summary>Günün küçük sürprizleri (O3): her gün 2–3 tanesi adada belirir; kaçırılırsa bir şey kaybedilmez.</summary>
    public static class DailySurprises
    {
        public static List<SurpriseDef> ForDay(IList<SurpriseDef> defs, int day, string childId, int level, int count = 3)
        {
            var pool = defs.Where(d => d.MinLevel <= level).ToList();
            var rng = new Random(ResidentRequests.StableHash((childId ?? "") + "#" + day));
            return pool.OrderBy(_ => rng.Next()).Take(Math.Min(count, pool.Count)).ToList();
        }

        /// <summary>İlk dokunuşta true (ödül bir kez); gün değişince sıfırlanır.</summary>
        public static bool Take(StoryState st, int day, string id)
        {
            if (st.SurpriseDay != day) { st.SurpriseDay = day; st.SurprisesTaken.Clear(); }
            return st.SurprisesTaken.Add(id);
        }
    }

    /// <summary>Okti'ye dokununca tepki (A1): her dokunuşta sıradaki, art arda aynısı gelmez.</summary>
    public static class OktiReactions
    {
        public const string Jump = "jump", Wave = "wave", Tickle = "tickle", Clap = "clap", InkHeart = "ink_heart";
        public static readonly string[] All = { Jump, Wave, Tickle, Clap, InkHeart };

        public static string Next(StoryState st) => All[st.Reactions++ % All.Length];
    }

    /// <summary>Açılışta yükleme görseli: ulaşılmış bölümlerden, bir öncekinden farklı.</summary>
    public static class LoadingArts
    {
        public static LoadingArtDef Pick(StoryBook book, StoryState st, int chapter, int seed)
        {
            var pool = book.Arts.Where(a => a.Chapter <= chapter).ToList();
            if (pool.Count == 0) return null;
            if (pool.Count > 1) pool = pool.Where(a => a.Id != st.LastArt).ToList();
            var pick = pool[(int)((uint)seed % (uint)pool.Count)];
            st.LastArt = pick.Id;
            return pick;
        }
    }
}
