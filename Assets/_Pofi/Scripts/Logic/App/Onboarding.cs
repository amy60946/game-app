using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>Tanıtım hareketi: ekrandaki parmak izi ne yapar.</summary>
    public enum TipGesture { Tap, Drag, Slide }

    public sealed class TipDef
    {
        public string Id;
        public TipGesture Gesture;
        public string Where;      // hangi ekranda (island, shop, wardrobe, home)
        public string Trigger;    // ne zaman gösterilir (belgede açıklama)
        public string DoneWhen;   // ne zaman tamamlanır
        public string CaptionKey => "tip." + Id;
        public string VoiceId => "vo_tip_" + Id;    // seslendirme kaydı adı (sonra)
    }

    /// <summary>
    /// İlk kez karşılaşılan işlevlerde gösterilen tanıtım ipuçları (14 Ekim 2026 geri bildirimi, madde 7 ve 11).
    /// Her ipucu bir kez tamamlanır (GameState.SeenTips); aynı anda yalnız bir ipucu görünür. Ayrıntılar: docs/ONBOARDING.md.
    /// </summary>
    public static class Onboarding
    {
        public const string Walk = "walk", Look = "look", Jump = "jump", Enter = "enter", Play = "play", Feed = "feed", Wash = "wash",
            Tasks = "tasks", Xp = "xp", Wardrobe = "wardrobe", Sparkle = "sparkle", Overview = "overview",
            Shop = "shop", WardrobeSpots = "wardrobe_spots", Home = "home",
            Story = "story", Board = "board", Mark = "mark", Stone = "stone",   // ilk gün akışı (App/FirstDay, Ö5)
            Plant = "plant", Harvest = "harvest",                              // bahçe sürükleme ipuçları (D2, 23 Ekim 2026)
            TasksHome = "tasks_home", TasksDone = "tasks_done", TasksGame = "tasks_game";   // Görevler penceresi tanıtımı (C + D, 24 Ekim 2026)

        /// <summary>
        /// Görevler penceresinin ilk açılışında sırayla gösterilen bilgilendirme eli (kullanıcı, 24 Ekim 2026: "pencere kalabalık
        /// görünmesin, bilgilendirme eli açıklasın"). Sıra: Ev Görevleri bölümü → ilk "Yaptım" → oyun görevleri; ardından taş varsa
        /// <see cref="Stone"/>. Her adım dokununca ya da el iki tur gösterince biter. "Yaptım" adımı ilk gün akışının
        /// <see cref="Mark"/> ipucunun yerini alır (ikisi aynı pencerede üst üste çıkmaz).
        /// </summary>
        public static readonly IReadOnlyList<string> TasksIntro = new[] { TasksHome, TasksDone, TasksGame };

        public static readonly IReadOnlyList<TipDef> All = new List<TipDef>
        {
            new TipDef { Id = Walk, Gesture = TipGesture.Slide, Where = "island", Trigger = "adaya ilk giriş", DoneWhen = "pet yürüdü (joystick ya da dokunma)" },
            new TipDef { Id = Look, Gesture = TipGesture.Slide, Where = "island", Trigger = "yürüme öğrenildi (sağ yarıda kamera)", DoneWhen = "sağ yarıda kaydırıldı" },
            new TipDef { Id = Jump, Gesture = TipGesture.Tap, Where = "island", Trigger = "yürüme öğrenildi, eylem tuşu 'Zıpla'", DoneWhen = "Zıpla'ya basıldı" },
            new TipDef { Id = Enter, Gesture = TipGesture.Tap, Where = "island", Trigger = "ilk kez bir kapının önünde", DoneWhen = "Gir'e basıldı" },
            new TipDef { Id = Play, Gesture = TipGesture.Tap, Where = "island", Trigger = "ilk kez 'Oyna!' yerinin önünde", DoneWhen = "Oyna'ya basıldı" },
            new TipDef { Id = Feed, Gesture = TipGesture.Drag, Where = "island", Trigger = "Besle tepsisi ilk açılış", DoneWhen = "yiyecek pete sürüklendi" },
            new TipDef { Id = Wash, Gesture = TipGesture.Drag, Where = "island", Trigger = "Yıka tepsisi ilk açılış", DoneWhen = "sabun pete sürüklendi" },
            new TipDef { Id = Tasks, Gesture = TipGesture.Tap, Where = "island", Trigger = "yürüme öğrenildi, açık görev var", DoneWhen = "Görev düğmesine basıldı" },
            new TipDef { Id = Xp, Gesture = TipGesture.Tap, Where = "island", Trigger = "ilk XP kazancı", DoneWhen = "6 sn gösterildi" },
            new TipDef { Id = Wardrobe, Gesture = TipGesture.Tap, Where = "island", Trigger = "giyilebilir eşya alındı", DoneWhen = "pete dokunuldu (giydirme açıldı)" },
            new TipDef { Id = Sparkle, Gesture = TipGesture.Tap, Where = "island", Trigger = "yakında parıltı var", DoneWhen = "parıltı toplandı" },
            new TipDef { Id = Overview, Gesture = TipGesture.Tap, Where = "island", Trigger = "görevler öğrenildi", DoneWhen = "Kuşbakışı açıldı" },
            new TipDef { Id = Shop, Gesture = TipGesture.Tap, Where = "shop", Trigger = "dükkân ilk açılış", DoneWhen = "bir ürün seçildi" },
            new TipDef { Id = WardrobeSpots, Gesture = TipGesture.Tap, Where = "wardrobe", Trigger = "giydirme ilk açılış", DoneWhen = "bir yuva noktası seçildi" },
            new TipDef { Id = Home, Gesture = TipGesture.Tap, Where = "home", Trigger = "Evim ilk açılış", DoneWhen = "Topla'ya basıldı" },
            new TipDef { Id = Story, Gesture = TipGesture.Tap, Where = "pet_select", Trigger = "ilk açılış, pet seçmeden önce", DoneWhen = "hikâye kartı kapatıldı" },
            new TipDef { Id = Board, Gesture = TipGesture.Tap, Where = "island", Trigger = "ilk gün: yürüme ve besleme bitti", DoneWhen = "Ev Görevleri panosu açıldı" },
            new TipDef { Id = Mark, Gesture = TipGesture.Tap, Where = "tasks", Trigger = "ilk gün: panoda yapılacak görev var", DoneWhen = "Yaptım'a basıldı" },
            new TipDef { Id = Stone, Gesture = TipGesture.Tap, Where = "tasks", Trigger = "yerleştirilecek Güneş Taşı var", DoneWhen = "ilk taş yerleştirildi" },
            new TipDef { Id = Plant, Gesture = TipGesture.Drag, Where = "garden", Trigger = "bahçede boş tarla ve tohum var", DoneWhen = "tohum sürüklenerek ekildi" },
            new TipDef { Id = Harvest, Gesture = TipGesture.Drag, Where = "garden", Trigger = "ilk kez hasada hazır ürün", DoneWhen = "orak sürüklenerek toplandı" },
            new TipDef { Id = TasksHome, Gesture = TipGesture.Tap, Where = "tasks", Trigger = "Görevler penceresi ilk açılış (altın Ev Görevleri başlığı)", DoneWhen = "dokunuldu ya da el iki tur gösterdi" },
            new TipDef { Id = TasksDone, Gesture = TipGesture.Tap, Where = "tasks", Trigger = "Görevler penceresinde yapılacak ev görevi var (ilk Yaptım)", DoneWhen = "dokunuldu, el iki tur gösterdi ya da Yaptım'a basıldı" },
            new TipDef { Id = TasksGame, Gesture = TipGesture.Tap, Where = "tasks", Trigger = "Görevler penceresi ilk açılış (mavi Oyun görevleri bölümü)", DoneWhen = "dokunuldu ya da el iki tur gösterdi" },
        };

        public static TipDef Get(string id) => All.FirstOrDefault(t => t.Id == id);
        public static bool Pending(GameState s, string id) => s != null && !s.SeenTips.Contains(id);
        public static void Done(GameState s, string id) { if (s != null) s.SeenTips.Add(id); }
    }
}
