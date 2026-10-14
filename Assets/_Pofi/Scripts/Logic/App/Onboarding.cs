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
            Shop = "shop", WardrobeSpots = "wardrobe_spots", Home = "home";

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
        };

        public static TipDef Get(string id) => All.FirstOrDefault(t => t.Id == id);
        public static bool Pending(GameState s, string id) => s != null && !s.SeenTips.Contains(id);
        public static void Done(GameState s, string id) { if (s != null) s.SeenTips.Add(id); }
    }
}
