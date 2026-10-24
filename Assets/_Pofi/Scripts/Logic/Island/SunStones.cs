using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Pofi.Logic.Progression;

namespace Pofi.Logic.Island
{
    /// <summary>Adada Güneş Taşı yerleştirilen onarım noktası (sis, köprü, yol, fener). Veri: Resources/Data/sun_spots.json.</summary>
    public sealed class SunSpotDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("cost")] public int Cost = 1;
        [JsonProperty("region")] public string Region;                       // yerleştirme yeri (haritada)
        [JsonProperty("opens")] public List<string> Opens = new List<string>(); // açtığı içerik (levels.json kimlikleri)
        [JsonProperty("say")] public string Say;                              // onarılınca pet'in cümlesi
    }

    /// <summary>Kaydedilen taş durumu. Kazanılan toplam sunucudan gelir; yerleştirme yalnız oyundadır.</summary>
    [Serializable]
    public sealed class SunStoneState
    {
        public int Earned;                                                    // sunucudaki toplam (child_me.sun_stones)
        public int Peak;                                                      // bugüne kadarki en yüksek toplam (geri alınıp yeniden gelen taş "yeni" sayılmaz)
        public int Gift;                                                      // hediye taş (GB19, yalnız ada): ilk oyunda Mavi'den 1; sunucuya gitmez, harcanmaz
        public Dictionary<string, int> Placed = new Dictionary<string, int>(); // nokta → yerleştirilen taş
    }

    public enum PlaceResult { Ok, Repaired, NoStones, AlreadyRepaired, NotNext, Unknown }

    /// <summary>
    /// Güneş Taşı (Ö1; sözleşme: ortak/sozlesme/ekonomi.md 5A). Taş yalnız ebeveyn onayıyla gelir, harcanmaz,
    /// adadaki onarım noktalarına sırayla yerleştirilir. Bir nokta dolunca açtığı bölge/oyun açılır: bu içerikte
    /// seviye yerine taş belirleyicidir. Onay geri alınıp toplam düşerse yerleştirilmiş taş geri alınmaz (ceza yok).
    /// </summary>
    public sealed class SunStoneBook
    {
        private sealed class File { [JsonProperty("spots")] public List<SunSpotDef> Spots = new List<SunSpotDef>(); }

        public IReadOnlyList<SunSpotDef> Spots { get; }
        private readonly Dictionary<string, SunSpotDef> _gate = new Dictionary<string, SunSpotDef>();

        public SunStoneBook(IReadOnlyList<SunSpotDef> spots)
        {
            Spots = spots ?? new List<SunSpotDef>();
            foreach (var s in Spots) if (s?.Opens != null) foreach (var id in s.Opens) _gate[id] = s;
        }

        public static SunStoneBook Parse(string json) =>
            new SunStoneBook(string.IsNullOrWhiteSpace(json) ? new List<SunSpotDef>() : JsonConvert.DeserializeObject<File>(json)?.Spots);

        public SunSpotDef Find(string id) => Spots.FirstOrDefault(s => s.Id == id);

        public static int PlacedIn(SunStoneState st, string spotId) => st.Placed.TryGetValue(spotId, out var n) ? n : 0;
        public static int PlacedTotal(SunStoneState st) => st.Placed.Values.Sum();
        public static int Available(SunStoneState st) => Math.Max(0, st.Earned + st.Gift - PlacedTotal(st));

        /// <summary>
        /// Kulübe yerindeki sis (GB19, kullanıcı 24 Ekim 2026): ilk sıradaki nokta; hediye taşla açılır. İlk oyunda Mavi bir
        /// Güneş Taşı hediye eder (hoş geldin coin'i gibi), çocuk onunla sisi dağıtmayı öğrenir; sonraki taşlar gerçek görevden.
        /// </summary>
        public const string HutSpot = "spot_hut_fog";

        /// <summary>Hediye taşı verir (çocuk başına bir kez, yalnız ada). Verildiyse true.</summary>
        public static bool GiveGift(SunStoneState st)
        {
            if (st == null || st.Gift > 0) return false;
            st.Gift = 1;
            return true;
        }

        /// <summary>Gerçek görevden gelen taşlarla yapılmış yerleştirme sayısı (hediye hariç).</summary>
        public static int RealPlaced(SunStoneState st) => Math.Max(0, PlacedTotal(st) - st.Gift);

        /// <summary>
        /// Kulübe sisi sonradan eklendi: kulübesini yapmış, başka bir sisi açmış ya da rehberi kapalı eski oyuncuda hediye taş
        /// verilip kulübe yerine kendiliğinden konur (sis hiç görünmez; boştaki taş sayısı değişmez). Yapıldıysa true.
        /// </summary>
        public bool CatchUpHutFog(SunStoneState st, bool oldPlayer)
        {
            var s = Find(HutSpot);
            if (s == null || st == null || !oldPlayer || IsRepaired(st, HutSpot)) return false;
            st.Gift = Math.Max(st.Gift, 1);
            st.Placed[HutSpot] = Math.Max(PlacedIn(st, HutSpot), s.Cost);
            return true;
        }

        public bool IsRepaired(SunStoneState st, string spotId)
        {
            var s = Find(spotId);
            return s != null && PlacedIn(st, spotId) >= s.Cost;
        }

        /// <summary>Sıradaki onarılacak nokta (hepsi bittiyse null).</summary>
        public SunSpotDef Next(SunStoneState st) => Spots.FirstOrDefault(s => PlacedIn(st, s.Id) < s.Cost);

        /// <summary>Sıradaki noktaya bir taş yerleştirir.</summary>
        public PlaceResult PlaceOne(SunStoneState st, string spotId)
        {
            var s = Find(spotId);
            if (s == null) return PlaceResult.Unknown;
            if (PlacedIn(st, spotId) >= s.Cost) return PlaceResult.AlreadyRepaired;
            if (Next(st) != s) return PlaceResult.NotNext;
            if (Available(st) <= 0) return PlaceResult.NoStones;
            st.Placed[spotId] = PlacedIn(st, spotId) + 1;
            return PlacedIn(st, spotId) >= s.Cost ? PlaceResult.Repaired : PlaceResult.Ok;
        }

        /// <summary>Sunucudaki toplam alınır. Dönen değer: yeni kazanılan taş (kutlama için; düşüşte 0).</summary>
        public static int ApplyServerTotal(SunStoneState st, int? total)
        {
            if (total == null) return 0;            // sunucu henüz taş bilmiyor (eski sürüm): yerel değer korunur
            var gained = Math.Max(0, total.Value - Math.Max(st.Earned, st.Peak));
            st.Earned = Math.Max(0, total.Value);
            st.Peak = Math.Max(st.Peak, st.Earned);
            return gained;
        }

        /// <summary>İçerik taşla mı açılıyor? Öyleyse onarım noktası, değilse null.</summary>
        public SunSpotDef GateOf(string featureId) => featureId != null && _gate.TryGetValue(featureId, out var s) ? s : null;

        /// <summary>Tek açılış kapısı: taşla açılan içerik onarımla, diğerleri seviyeyle (levels.json).</summary>
        public bool IsOpen(string featureId, int level, LevelTable levels, SunStoneState st)
        {
            var g = GateOf(featureId);
            return g != null ? IsRepaired(st, g.Id) : levels.IsUnlocked(featureId, level);
        }

        /// <summary>Seviye kutlamasından taşla açılan içerik çıkarılır (o seviyede açılmıyor).</summary>
        public void FilterLevelUp(LevelUp up)
        {
            if (up != null) up.Unlocked.RemoveAll(id => GateOf(id) != null);
        }
    }
}
