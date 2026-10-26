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
    /// Rehberli görev zinciri (ilk sürüm 19 Ekim 2026; sıra kullanıcı GB17/GB19, 24 Ekim 2026): oyun çocuğu baştan sona adım adım
    /// gezdirir, her adım tek şey öğretir ve küçük XP verir. Rota adada tek yönde akar (batı → doğu; geri dönüş yok): besle → yıka →
    /// Evim → topla → oyna → dükkândan ilk aksesuar (hoş geldin coin'iyle) → tak → Kıskaç'a git → 2 hindistan cevizi → Kıskaç'a
    /// teslim → Mavi gelir → Mavi'nin hediye Güneş Taşı + bilgi kartı (GB19) → kulübe yerindeki sisi taşla aç (meydanın doğusu) →
    /// kulübe malzemesi (yerin çevresinde) → kulübe → Ev Görevleri panosu (yanında; yeni taşlar buradan) → kamp ateşini harla
    /// (GB18, doğudaki kamp) → koydaki sis (gerçek görevle kazanılan taşla). Hazır olmayan adım (ör. coin ya da taş yok) atlanır ve hazır olunca geri gelir.
    /// Ödül yalnız adım o an, canlı yapılınca verilir; önceden yapılmış adım ödülsüz geçilir. Rehber bir kez başladıysa seviye
    /// sınırı yoktur (zincir Sv3'ü aşabilir); Sv3'ü geçmiş ve hiç başlamamış oyuncuda kapalıdır. Durum GameState.SeenTips içinde.
    /// </summary>
    public static class Guide
    {
        public const int MaxLevel = 3;
        public const string DoneFlag = "guide_done", Prefix = "guide:", DidPrefix = "did:";
        public const string CoconutRequest = "req_kiskac_coconut";
        public const int CoconutsNeeded = 2;
        /// <summary>Hoş geldin coin'i alındı işareti (GameState.SeenTips; GameBootstrap.ClaimWelcome yazar).</summary>
        public const string WelcomeFlag = "welcome_coins";
        /// <summary>Rehberin pano adımında açılan Ev Görevleri (hikâye ch1_board da bununla oynar).</summary>
        public const string BoardCounter = "board_guided";
        /// <summary>Rehberden önceki temel ipuçları (yürü, etrafa bak): sayaç bunlarla başlar ("1/20").</summary>
        public const int BasicsCount = 2;
        /// <summary>Oyundaki tek adım numarası (temel ipuçları + rehber): "3/20". Akış haritası belgesi de bu numarayı yazar.</summary>
        public static string Label(int index) => (index + 1) + "/" + (Steps.Count + BasicsCount);
        /// <summary>Şu anki rehber adımının numarası (temel ipuçlarından sonra).</summary>
        public static string Label(GameState s) => Label(BasicsCount + DoneCount(s));

        /// <summary>Giyilebilir eşya mı (katalogdan; <see cref="Configure"/>)? Varsayılan: hiçbiri.</summary>
        public static Func<string, bool> IsWearable = id => false;
        /// <summary>Sv1'de alınabilen en ucuz giyilebilir eşyanın fiyatı (hoş geldin coin'i bunu karşılar).</summary>
        public static int FirstWearPrice = 15;

        private static SunStoneBook _book;

        /// <summary>Katalogla kurulum (oyun açılışında ve testlerde).</summary>
        public static void Configure(Data.GameData data)
        {
            if (data == null) return;
            _book = data.SunBook;
            IsWearable = id => data.Item(id)?.IsWearable == true;
            var first = FirstWear(data, int.MaxValue);
            FirstWearPrice = first != null ? first.Price : 15;
        }

        /// <summary>
        /// Rehberin önerdiği ilk aksesuar: Sv1'de alınabilen, bütçeye (coin) sığan en ucuz giyilebilir eşya; komik eşyalar sonra
        /// (sunucu kataloğunda henüz yoklar, ortak E9). Yoksa null.
        /// </summary>
        public static Data.ItemDef FirstWear(Data.GameData data, int coins) =>
            data?.Items.Where(i => i.IsWearable && !i.Premium && i.Level <= 1 && i.Price > 0 && i.Price <= coins)
                .OrderBy(i => i.Fancy).ThenBy(i => i.Price).FirstOrDefault();

        private static bool OwnsWearable(GameState s) => s.Inventory.Owned.Any(id => IsWearable(id));

        public static readonly IReadOnlyList<GuideStep> Steps = new List<GuideStep>
        {
            new GuideStep { Id = "feed", Counter = "pet_fed", Xp = 10 },
            new GuideStep { Id = "wash", Counter = "pet_washed", Xp = 10 },
            new GuideStep { Id = "home", Counter = "home_entered", Xp = 10 },
            new GuideStep { Id = "tidy", Counter = "home_tidied", Xp = 15 },
            new GuideStep { Id = "play", Counter = "pet_played", Xp = 10 },
            // Hoş geldin coin'i henüz gelmediyse (ilk beslemede istenir) dükkân adımı yine sırada bekler: Kıskaç ancak dükkân ve giydirme
            // bitince gelir (akış haritası yorumu, 25 Ekim 2026: "her aksiyon sırasıyla"). Coin gelmiş ama yetmiyorsa ya da oyuncu Kıskaç'la
            // zaten tanışmışsa (eski kayıt) adım atlanır.
            new GuideStep { Id = "shop", Counter = "wear_bought", Xp = 20,
                Ready = s => s.Wallet.Available >= FirstWearPrice || (!s.SeenTips.Contains(WelcomeFlag) && !s.SeenTips.Contains(DidPrefix + "kiskac_met")),
                AlreadyDone = OwnsWearable },
            new GuideStep { Id = "wear", Counter = "item_equipped", Xp = 15, Ready = OwnsWearable },
            new GuideStep { Id = "kiskac", Counter = "kiskac_met", Xp = 10 },
            new GuideStep { Id = "coconut", Counter = "coconuts_ready", Xp = 20,
                AlreadyDone = s => s.Inventory.CountOf(Island.Gathering.CoconutItem) >= CoconutsNeeded },
            new GuideStep { Id = "deliver", Counter = "coconut_delivered", Xp = 15 },
            new GuideStep { Id = "mavi", Counter = "mavi_arrived", Xp = 10, AlreadyDone = s => s.Story.Seen.Contains("ch2_open") },
            new GuideStep { Id = "gift", Counter = "gift_stone", Xp = 10, AlreadyDone = s => s.SunStones.Gift > 0 },   // Mavi'nin hediye taşı (GB19)
            new GuideStep { Id = "clear", Counter = "hut_fog_cleared", Xp = 15,
                AlreadyDone = s => SunStoneBook.PlacedIn(s.SunStones, SunStoneBook.HutSpot) > 0 },                           // kulübe yerindeki sis
            new GuideStep { Id = "gather", Counter = "hut_ready", Xp = 20,
                AlreadyDone = s => s.Gather != null && (s.Gather.HutBuilt || Gathering.CanBuild(s.Gather)) },
            new GuideStep { Id = "hut", Counter = "hut_built", Xp = 10, AlreadyDone = s => s.Gather != null && s.Gather.HutBuilt },   // kulübe zaten 40 XP verir (Gathering.HutXp)
            // kulübenin yanında: yeni taşlar gerçek görevden. Sayaç yalnız bu adımdayken açılan pano (board_guided): Görev penceresi
            // daha önce açılmış olsa da adım ve Kıskaç'ın pano sahnesi kulübeden sonra gelir (akış haritası yorumu, 25 Ekim 2026)
            new GuideStep { Id = "board", Counter = BoardCounter, Xp = 15 },
            new GuideStep { Id = "fire", Counter = "fire_stoked", Xp = 10, AlreadyDone = s => s.Campfire != null && s.Campfire.Total > 0 },   // kamp ateşini harla (GB18)
            new GuideStep { Id = "stone", Counter = "stone_placed", Xp = 30,   // koydaki sis: hediye değil, görevle kazanılan taş
                Ready = s => SunStoneBook.Available(s.SunStones) > 0, AlreadyDone = s => SunStoneBook.RealPlaced(s.SunStones) > 0 },
        };

        public static GuideStep Get(string id) => Steps.FirstOrDefault(x => x.Id == id);

        public static bool IsDone(GameState s, GuideStep st) => s.SeenTips.Contains(Prefix + st.Id);

        /// <summary>Rehber açık mı (pet var, bitmedi; Sv3'ü geçmiş oyuncu ancak zinciri başlatmışsa)?</summary>
        public static bool Active(GameState s, int level) =>
            s != null && s.HasPet && !s.SeenTips.Contains(DoneFlag) && (level <= MaxLevel || DoneCount(s) > 0);

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

        /// <summary>Tamamlanan adım sayısı ve toplam (panelde "3/15").</summary>
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

        /// <summary>Oyun yüklenince: Sv3'ü geçmiş ve zinciri hiç başlatmamış oyuncuda rehberi kapatır; önceden yapılmış adımları ödülsüz geçer.</summary>
        public static void Start(GameState s, int level)
        {
            if (s == null) return;
            CatchUpHutFog(s, level);
            if (level > MaxLevel && DoneCount(s) == 0) { s.SeenTips.Add(DoneFlag); return; }
            OnActivity(s, level, null);
        }

        /// <summary>
        /// Kulübe sisi sonradan geldi (GB19): kulübesini yapmış, başka sisi açmış ya da rehberi kapalı/ilerisinde olan eski oyuncu
        /// sisi hiç görmez (hediye taş kendiliğinden konur, sahnesi izlenmiş sayılır). Rehberin ortasındaki yeni oyuncu adımları yapar.
        /// </summary>
        public static void CatchUpHutFog(GameState s, int level)
        {
            if (_book == null || s == null || !s.HasPet) return;
            var old = (s.Gather != null && s.Gather.HutBuilt) || SunStoneBook.PlacedTotal(s.SunStones) > 0
                || s.SeenTips.Contains(DoneFlag) || (level > MaxLevel && DoneCount(s) == 0);
            if (_book.CatchUpHutFog(s.SunStones, old)) s.Story.Seen.Add(HutFogScene);
        }

        /// <summary>Kulübe sisi kalkınca oynayan kısa sahne (story.json).</summary>
        public const string HutFogScene = "ch2_fog";

        /// <summary>Şu anki adım bu mu (çalışma zamanı kısayolu)?</summary>
        public static bool Is(GameState s, int level, string id) => Current(s, level)?.Id == id;
    }
}
