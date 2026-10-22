using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Pofi.Logic.Profile;

namespace Pofi.Logic.Story
{
    // Hikâye (kullanıcı onayı 23 Ekim 2026; metin: "Pofi Adası Hikâyesi" belgesi). Veri Resources/Data/story.json'da;
    // metin değişikliği kod değiştirmez. Sahneler adanın üstünde oynar (portre + balon); her sahne bir kez, sonra Defter'de.

    /// <summary>Bir konuşma satırı. <see cref="Text"/> varsayılan (B grubu); A ve K için kısa, C için esprili sürüm olabilir.</summary>
    public sealed class StoryLine
    {
        [JsonProperty("who")] public string Who;      // narrator, okti, kiskac, pitir, hisir, mavi, tosbi, nur, pus
        [JsonProperty("text")] public string Text;
        [JsonProperty("a")] public string Short;      // A (6–8) ve K (≤5)
        [JsonProperty("c")] public string Teen;       // C (13–15)
        [JsonProperty("mood")] public string Mood;    // happy, surprised, sad, think (portre ifadesi)
    }

    public sealed class StoryScene
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("chapter")] public int Chapter;
        [JsonProperty("trigger")] public string Trigger;   // intro | level | spot | event
        [JsonProperty("arg")] public string Arg;           // seviye no, onarım noktası kimliği ya da sayaç adı
        [JsonProperty("summary")] public string Summary;   // hikâye kapalıyken tek satırlık balon
        [JsonProperty("art")] public string Art;           // sahne/yükleme görseli (Resources/Art/Story/<art>)
        [JsonProperty("lines")] public List<StoryLine> Lines = new List<StoryLine>();
    }

    public sealed class StoryChapterDef
    {
        [JsonProperty("n")] public int Number;
        [JsonProperty("title")] public string Title;
        [JsonProperty("level")] public int Level;          // bölümün başladığı seviye
    }

    /// <summary>Fener bekçisinin günlük sayfası (H3).</summary>
    public sealed class LorePageDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("n")] public int Number;
        [JsonProperty("text")] public string Text;
        [JsonProperty("where")] public string Where;       // tosbi | sparkle | region:<id> | lighthouse
        [JsonProperty("chapter")] public int Chapter;      // bu bölümden itibaren bulunabilir
    }

    /// <summary>Adalı isteği (H4). Ödül eşya/XP; coin asla (coin yalnız onaylı gerçek görevden).</summary>
    public sealed class RequestDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("who")] public string Who;
        [JsonProperty("text")] public string Text;
        [JsonProperty("need")] public string Need;         // malzeme ya da eşya kimliği
        [JsonProperty("count")] public int Count = 1;
        [JsonProperty("reward")] public string RewardItem; // eşya kimliği (boş olabilir)
        [JsonProperty("xp")] public int Xp;
        [JsonProperty("minLevel")] public int MinLevel = 1;
    }

    /// <summary>Günün küçük sürprizi (O3): kaçırılırsa ceza yok.</summary>
    public sealed class SurpriseDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("kind")] public string Kind;          // bottle, crabs, butterfly, shells, starfish, gull
        [JsonProperty("minLevel")] public int MinLevel = 1;
        [JsonProperty("xp")] public int Xp = 3;
        [JsonProperty("say")] public string Say;
    }

    /// <summary>Yükleme görseli (hikâyeyle eşleşen; yalnız ulaşılmış bölümünkiler).</summary>
    public sealed class LoadingArtDef
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("chapter")] public int Chapter;
        [JsonProperty("tip")] public string Tip;
    }

    public sealed class StoryBook
    {
        [JsonProperty("chapters")] public List<StoryChapterDef> Chapters = new List<StoryChapterDef>();
        [JsonProperty("scenes")] public List<StoryScene> Scenes = new List<StoryScene>();
        [JsonProperty("pages")] public List<LorePageDef> Pages = new List<LorePageDef>();
        [JsonProperty("requests")] public List<RequestDef> Requests = new List<RequestDef>();
        [JsonProperty("surprises")] public List<SurpriseDef> Surprises = new List<SurpriseDef>();
        [JsonProperty("arts")] public List<LoadingArtDef> Arts = new List<LoadingArtDef>();
        [JsonProperty("names")] public Dictionary<string, string> Names = new Dictionary<string, string>();

        public static StoryBook Parse(string json) =>
            string.IsNullOrWhiteSpace(json) ? new StoryBook() : JsonConvert.DeserializeObject<StoryBook>(json) ?? new StoryBook();

        public StoryScene Scene(string id) => Scenes.FirstOrDefault(s => s.Id == id);
        public string NameOf(string who) => who != null && Names.TryGetValue(who, out var n) ? n : who;

        /// <summary>Bu seviyede açık olan en yüksek bölüm (0 = giriş).</summary>
        public int ChapterFor(int level) => Chapters.Where(c => c.Level <= level).Select(c => c.Number).DefaultIfEmpty(0).Max();

        public List<string> Validate(ISet<string> spots)
        {
            var e = new List<string>();
            foreach (var g in Scenes.GroupBy(s => s.Id).Where(g => g.Count() > 1)) e.Add("sahne tekrar: " + g.Key);
            foreach (var s in Scenes)
            {
                if (s.Lines.Count == 0) e.Add(s.Id + ": satır yok");
                if (s.Lines.Count > 6) e.Add(s.Id + ": en çok 6 satır");
                foreach (var l in s.Lines)
                {
                    if (string.IsNullOrWhiteSpace(l.Text)) e.Add(s.Id + ": boş satır");
                    else if (l.Text.Split(' ').Length > 14) e.Add(s.Id + ": satır uzun: " + l.Text);
                    if (l.Who != "narrator" && !Names.ContainsKey(l.Who ?? "")) e.Add(s.Id + ": bilinmeyen konuşan " + l.Who);
                }
                if (s.Trigger == StoryDirector.Level && !int.TryParse(s.Arg, out _)) e.Add(s.Id + ": seviye sayı olmalı");
                if (s.Trigger == StoryDirector.Spot && spots != null && !spots.Contains(s.Arg)) e.Add(s.Id + ": bilinmeyen onarım noktası " + s.Arg);
                if (string.IsNullOrWhiteSpace(s.Summary)) e.Add(s.Id + ": özet yok");
            }
            foreach (var r in Requests) if (r.Count < 1) e.Add(r.Id + ": adet en az 1");
            return e;
        }
    }

    [Serializable]
    public sealed class OpenRequest
    {
        public string Id;
        public int Day;      // geldiği gün (süre dolmaz; yalnız sıralama için)
    }

    [Serializable]
    public sealed class DiaryLine
    {
        public string Key;          // tr.json anahtarı (diary.*)
        public string[] Args = new string[0];
    }

    [Serializable]
    public sealed class DiaryEntry
    {
        public int Day;
        public List<DiaryLine> Lines = new List<DiaryLine>();
    }

    /// <summary>Hikâye ve günlük ada hayatı kaydı (oyun kaydında).</summary>
    [Serializable]
    public sealed class StoryState
    {
        public bool Initialized;
        public bool IntroSeen;
        public HashSet<string> Seen = new HashSet<string>();
        public HashSet<string> Pages = new HashSet<string>();
        public List<OpenRequest> Requests = new List<OpenRequest>();
        public int RequestDay;
        public Dictionary<string, int> Friendship = new Dictionary<string, int>();
        public List<DiaryEntry> Diary = new List<DiaryEntry>();
        public string LastArt;
        public int Reactions;
        public int SurpriseDay;
        public HashSet<string> SurprisesTaken = new HashSet<string>();
    }

    /// <summary>Hangi sahne ne zaman oynar (H1). Tetikler: ilk giriş, seviye, Güneş Taşı onarımı, olay sayacı.</summary>
    public static class StoryDirector
    {
        public const string Intro = "intro", Level = "level", Spot = "spot", Event = "event";

        /// <summary>Sahnenin koşulu sağlandı mı (izlenmiş olsun olmasın).</summary>
        public static bool Due(StoryScene s, int level, ICollection<string> repairedSpots, Func<string, bool> eventHappened)
        {
            switch (s.Trigger)
            {
                case Intro: return true;
                case Level: return int.TryParse(s.Arg, out var lv) && level >= lv;
                case Spot: return repairedSpots != null && repairedSpots.Contains(s.Arg);
                case Event: return eventHappened != null && eventHappened(s.Arg);
                default: return false;
            }
        }

        /// <summary>
        /// İlk kurulum: yeni oyuncu filmden başlar. Hikâyeden önce başlamış oyuncuya geçmiş sahneler yığılmaz: olmuş olanlar
        /// izlenmiş sayılır (Defter'de durur), yalnız en son olanı oynar.
        /// </summary>
        public static void Init(StoryState st, StoryBook book, bool existingPlayer, int level, ICollection<string> spots, Func<string, bool> ev)
        {
            if (st.Initialized) return;
            st.Initialized = true;
            if (!existingPlayer) return;
            st.IntroSeen = true;
            var due = book.Scenes.Where(s => s.Trigger != Intro && Due(s, level, spots, ev)).ToList();
            foreach (var s in due.Take(Math.Max(0, due.Count - 1))) st.Seen.Add(s.Id);
            foreach (var s in book.Scenes.Where(s => s.Trigger == Intro)) st.Seen.Add(s.Id);
        }

        /// <summary>Şimdi oynaması gereken sahne (yoksa null). Sıra: giriş, sonra dosyadaki sıra.</summary>
        public static StoryScene Next(StoryBook book, StoryState st, int level, ICollection<string> spots, Func<string, bool> ev)
        {
            foreach (var s in book.Scenes)
            {
                if (st.Seen.Contains(s.Id)) continue;
                if (s.Trigger == Intro && st.IntroSeen) continue;
                if (Due(s, level, spots, ev)) return s;
            }
            return null;
        }

        public static void MarkSeen(StoryState st, StoryScene s)
        {
            if (s == null) return;
            st.Seen.Add(s.Id);
            if (s.Trigger == Intro) st.IntroSeen = true;
        }

        /// <summary>Yaş grubuna göre metin: A ve K kısa sürümü, C esprili sürümü (yoksa varsayılan).</summary>
        public static string Text(StoryLine l, AgeBand band)
        {
            if ((band == AgeBand.A || band == AgeBand.K) && !string.IsNullOrWhiteSpace(l.Short)) return l.Short;
            if (band == AgeBand.C && !string.IsNullOrWhiteSpace(l.Teen)) return l.Teen;
            return l.Text;
        }

        /// <summary>K (≤5) için kendiliğinden ilerleme süresi (saniye); diğerleri dokunuşla ilerler.</summary>
        public static float AutoAdvance(AgeBand band) => band == AgeBand.K ? 4f : 0f;

        /// <summary>Defter → Hikâye: izlenmiş sahneler, sırayla.</summary>
        public static List<StoryScene> Replayable(StoryBook book, StoryState st) => book.Scenes.Where(s => st.Seen.Contains(s.Id)).ToList();
    }
}
