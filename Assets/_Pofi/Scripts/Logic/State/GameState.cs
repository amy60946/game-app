using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Pofi.Logic.Economy;
using Pofi.Logic.Garden;
using Pofi.Logic.Meta;
using Pofi.Logic.Pet;
using Pofi.Logic.Shop;
using Pofi.Logic.Tasks;

namespace Pofi.Logic.State
{
    [Serializable]
    public sealed class Placement
    {
        public string ItemId;
        public float X, Y;       // ev ızgarası / serbest konum
        public int Rotation;
    }

    [Serializable]
    public sealed class PlayerSettings
    {
        public float MusicVolume = 0.7f;
        public float SfxVolume = 1f;
        public bool VoiceOn = true;
        public bool SubtitlesOn = true;
        public float TextScale = 1f;
        public bool HighContrast;
        public bool ReduceMotion;
        public bool NotificationsAllowed;
    }

    /// <summary>
    /// Oyunun kaydedilen tüm durumu (tek doğruluk kaynağı). Yerelde saklanır, sunucuyla senkronlanır.
    /// Coin bakiyesi Wallet içinde ama her zaman sunucudan düzeltilir.
    /// </summary>
    [Serializable]
    public sealed class GameState
    {
        public const int CurrentSchema = 1;

        public int Schema = CurrentSchema;
        public string ChildId;
        public string PetId;            // pet_01 … pet_12; null = henüz seçilmedi
        public string PetName;
        public PetStats Stats;
        public XpSystem Xp = new XpSystem();
        public TaskStreak Streak = new TaskStreak();
        public Wallet Wallet = new Wallet();
        public Inventory Inventory = new Inventory();
        public TaskBoard Tasks = new TaskBoard();
        public List<Placement> Home = new List<Placement>();
        public HashSet<string> Collection = new HashSet<string>();
        public HashSet<string> Badges = new HashSet<string>();
        public HashSet<string> SeenUnlocks = new HashSet<string>();   // kutlaması gösterilmiş açılışlar
        public HashSet<string> SeenTips = new HashSet<string>();      // tamamlanan tanıtım ipuçları (Onboarding)
        public HashSet<string> VisitedRegions = new HashSet<string>(); // haritada ziyaret edilen bölgeler ("yeni" işareti için)
        public string LastRegion;                                       // adada en son girilen bölge: pet dönüşte onun kapısında belirir
        public Counters Counters = new Counters();
        public DailyQuestState DailyQuests = new DailyQuestState();
        public GardenState Garden = new GardenState();
        public PlayerSettings Settings = new PlayerSettings();
        public long LastSavedUtcTicks;
        public long LastSyncUtcTicks;
        public Dictionary<string, Cards.DifficultyAdapter> CardDifficulty = new Dictionary<string, Cards.DifficultyAdapter>(); // oyun → uyarlanan bot zorluğu
        public Island.SparkleState Sparkles = new Island.SparkleState();
        public Island.EventState Events = new Island.EventState();
        public Island.GatherState Gather = new Island.GatherState();   // kütük/çalı/taş toplama + kulübe (Island/Gathering)
        public HashSet<string> HomeEffectsApplied = new HashSet<string>(); // ev eşyası etkisi bir kez (ilk yerleştirme)
        public bool StarterGiven;        // hoş geldin hediyesi verildi mi (App/StarterKit)

        public bool HasPet => !string.IsNullOrEmpty(PetId) && !string.IsNullOrEmpty(PetName);

        public static GameState NewFor(string childId, DateTime nowUtc) =>
            new GameState { ChildId = childId, Stats = PetStats.New(nowUtc) };
    }

    /// <summary>JSON kayıt/yükleme + şema göçü. Bozuk kayıt oyunu çökertmez: null döner, çağıran yedekten ya da sunucudan yükler.</summary>
    public static class SaveCodec
    {
        private static readonly JsonSerializerSettings Settings = new JsonSerializerSettings
        {
            Formatting = Formatting.None,
            NullValueHandling = NullValueHandling.Include,
            ObjectCreationHandling = ObjectCreationHandling.Replace,
        };

        public static string Serialize(GameState s, DateTime nowUtc)
        {
            s.LastSavedUtcTicks = nowUtc.Ticks;
            s.Schema = GameState.CurrentSchema;
            return JsonConvert.SerializeObject(s, Settings);
        }

        public static GameState Deserialize(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return null;
            try
            {
                var obj = JObject.Parse(json);
                var schema = obj.Value<int?>("Schema") ?? 0;
                if (schema > GameState.CurrentSchema) return null; // daha yeni sürümün kaydı: dokunma
                Migrate(obj, schema);
                return obj.ToObject<GameState>(JsonSerializer.Create(Settings));
            }
            catch (JsonException)
            {
                return null;
            }
        }

        /// <summary>Şema göçleri burada sırayla uygulanır (ör. 1→2 alan adı değişikliği).</summary>
        private static void Migrate(JObject obj, int from)
        {
            if (from < 1)
            {
                obj["Schema"] = 1;
            }
        }
    }
}
