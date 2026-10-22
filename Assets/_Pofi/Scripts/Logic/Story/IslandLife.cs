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

    /// <summary>
    /// Adalıların yeri ve isteğin karşılanması (H4): malzeme (odun/dal/taş) toplanan malzemeden, eşya (hindistan cevizi, balık, havuç)
    /// envanterden düşülür; ödül eşyası envantere girer. Coin asla (yalnız onaylı gerçek görevden).
    /// </summary>
    public static class Residents
    {
        public static readonly Dictionary<string, string> Home = new Dictionary<string, string>
        {
            { "kiskac", "region_shop" }, { "mavi", "region_home" }, { "pitir", "region_coconut_grove" }, { "hisir", "region_coconut_grove" },
            { "tosbi", "region_pier" },
        };

        public static bool IsMaterial(string need) => need == Island.Gathering.Wood || need == Island.Gathering.Branch || need == Island.Gathering.Stone;

        public static int Have(State.GameState s, string need) =>
            IsMaterial(need) ? Island.Gathering.Count(s.Gather, need) : s.Inventory.CountOf(need);

        public static RequestDef Fulfill(State.GameState s, Data.GameData data, string requestId)
        {
            var d = ResidentRequests.Fulfill(s.Story, data.Story.Requests, requestId, k => Have(s, k), (k, n) =>
            {
                if (IsMaterial(k)) s.Gather.Materials[k] = Island.Gathering.Count(s.Gather, k) - n;
                else { var it = data.Item(k); if (it != null) s.Inventory.Remove(it, n); }
            });
            if (d != null && !string.IsNullOrEmpty(d.RewardItem))
            {
                var reward = data.Item(d.RewardItem);
                if (reward != null) s.Inventory.Add(reward);
            }
            return d;
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

    public sealed class SurpriseSpot
    {
        public SurpriseDef Def;
        public float X, Z;
    }

    public static class SurprisePlaces
    {
        /// <summary>Kıyıda durması gerekenler (kumsal: deniz seviyesine yakın yürünebilir yer).</summary>
        public static bool Shore(string kind) => kind == "bottle" || kind == "crabs" || kind == "shells" || kind == "starfish";

        public const float ShoreTop = 0.9f;

        /// <summary>
        /// Günün sürprizlerine belirlenimci yer: kıyı türleri kumsalda (yükseklik ≤ 0,9 m), diğerleri içeride; bölgelere ve
        /// birbirine yakın değil. Yer bulunamayan sürpriz o gün çıkmaz.
        /// </summary>
        public static List<SurpriseSpot> Place(IList<SurpriseDef> todays, int day, string childId, Island.IslandTerrain terrain)
        {
            var list = new List<SurpriseSpot>();
            var rng = new Random(ResidentRequests.StableHash((childId ?? "") + "@" + day));
            foreach (var d in todays)
            {
                var shore = Shore(d.Kind);
                for (var tries = 0; tries < 600; tries++)
                {
                    var x = (float)(terrain.MinX + rng.NextDouble() * (terrain.MaxX - terrain.MinX));
                    var z = (float)(terrain.MinZ + rng.NextDouble() * (terrain.MaxZ - terrain.MinZ));
                    if (!terrain.Walkable(x, z)) continue;
                    var h = terrain.Height(x, z);
                    if (shore ? h > ShoreTop || h < 0.05f : h < ShoreTop + 0.3f) continue;
                    if (terrain.Regions.Any(r => Dist(r.X, r.Z, x, z) < r.Size * 0.8f + 2f) || list.Any(s => Dist(s.X, s.Z, x, z) < 10f)) continue;
                    list.Add(new SurpriseSpot { Def = d, X = x, Z = z });
                    break;
                }
            }
            return list;
        }

        private static float Dist(float ax, float az, float bx, float bz) => (float)Math.Sqrt((ax - bx) * (ax - bx) + (az - bz) * (az - bz));
    }

    /// <summary>
    /// Fener bekçisinin günlük sayfaları (H3): sayfa bölümü açılınca bulunabilir hâle gelir; yerine göre bulunur
    /// (bölgeye girince, günün parıltısında günde bir, Tosbi Dede'den, fener yanınca). Bulunan sayfa Defter'de sırayla birleşir.
    /// </summary>
    public static class LorePages
    {
        public const string Sparkle = "sparkle", Tosbi = "tosbi", Lighthouse = "lighthouse";

        /// <summary>Bölgeye girince: o bölgenin sayfası (bölüm açıksa ve bulunmadıysa).</summary>
        public static LorePageDef OnRegion(StoryBook book, StoryState st, int chapter, string regionId) =>
            Find(book, st, chapter, p => p.Where == "region:" + regionId);

        /// <summary>Parıltı açılınca: bulunmamış en küçük numaralı parıltı sayfası, günde en çok bir.</summary>
        public static LorePageDef OnSparkle(StoryBook book, StoryState st, int chapter, int day)
        {
            if (st.PageDay == day) return null;
            var p = Find(book, st, chapter, x => x.Where == Sparkle);
            if (p != null) st.PageDay = day;
            return p;
        }

        /// <summary>Tosbi Dede ya da fener (olay): o yerin sayfası.</summary>
        public static LorePageDef OnPlace(StoryBook book, StoryState st, int chapter, string where) => Find(book, st, chapter, p => p.Where == where);

        private static LorePageDef Find(StoryBook book, StoryState st, int chapter, Func<LorePageDef, bool> where)
        {
            var p = book.Pages.Where(x => x.Chapter <= chapter && !st.Pages.Contains(x.Id) && where(x)).OrderBy(x => x.Number).FirstOrDefault();
            if (p != null) st.Pages.Add(p.Id);
            return p;
        }

        /// <summary>Defter: bulunan sayfalar numara sırasıyla.</summary>
        public static List<LorePageDef> Found(StoryBook book, StoryState st) => book.Pages.Where(p => st.Pages.Contains(p.Id)).OrderBy(p => p.Number).ToList();
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
