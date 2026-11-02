using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.State;

namespace Pofi.Logic.App
{
    /// <summary>"Nasıl oynanır" kartı: simge + başlık + tek cümle (tr.json <c>howto.&lt;id&gt;.title</c> / <c>.text</c>).</summary>
    public sealed class HowToCard
    {
        public string Id;
        public string Icon;
        public HowToCard(string id, string icon) { Id = id; Icon = icon; }
    }

    /// <summary>
    /// K6 A (kullanıcı kararı, 2 Kasım 2026; benchmark: Apple HIG Onboarding, CHI 2012, NN/g): ipucu yazısı, rehber eli, yol okları
    /// ve öğretici ses herkes için "Geç" ile kapatılabilir; Defter › "Nasıl oynanır"dan yeniden açılır.
    /// Kapatmak rehberin kendisini bitirmez: adımlar eylemle ilerlemeye devam eder (hikâye sahneleri, hediye taş, ödüller kaybolmaz);
    /// yalnız gösterim susar. Çocuğun kendi istediği yön ("Git", haritadaki im) kapalıyken de çalışır.
    /// </summary>
    public static class Hints
    {
        public static bool On(GameState s) => s?.Settings == null || s.Settings.HintsOn;

        public static void TurnOff(GameState s)
        {
            if (s?.Settings != null) s.Settings.HintsOn = false;
        }

        /// <summary>
        /// İpuçlarını yeniden aç ve temel tanıtım ipuçlarını baştan göster. Rehber ilerlemesi, ilk gün akışı ve hikâye korunur.
        /// Dönen: yeniden gösterilecek ipucu sayısı.
        /// </summary>
        public static int Replay(GameState s)
        {
            if (s?.Settings == null) return 0;
            s.Settings.HintsOn = true;
            return s.SeenTips.RemoveWhere(id => Replayable.Contains(id));
        }

        /// <summary>Yeniden gösterilebilen tanıtım ipuçları (ilk gün akışı ve tek seferlik bilgiler hariç).</summary>
        public static readonly HashSet<string> Replayable = new HashSet<string>
        {
            Onboarding.Walk, Onboarding.Look, Onboarding.Jump, Onboarding.Enter, Onboarding.Play, Onboarding.Feed, Onboarding.Wash,
            Onboarding.Tasks, Onboarding.Wardrobe, Onboarding.Overview, Onboarding.Shop, Onboarding.WardrobeSpots, Onboarding.Home,
            Onboarding.Plant, Onboarding.Harvest, Onboarding.TasksHome, Onboarding.TasksDone, Onboarding.TasksGame,
            Onboarding.MapFar, Onboarding.MapPin,
        };

        /// <summary>Defter › Nasıl oynanır sırası (adada karşılaşılan sırayla).</summary>
        public static readonly IReadOnlyList<HowToCard> Cards = new List<HowToCard>
        {
            new HowToCard("walk", "act_walk"),
            new HowToCard("care", "food_apple"),
            new HowToCard("action", "act_enter"),
            new HowToCard("quests", "ui_star"),
            new HowToCard("home_tasks", "ui_board"),
            new HowToCard("stones", "ui_sunstone"),
            new HowToCard("map", "ui_map"),
            new HowToCard("shop", "ui_shop"),
            new HowToCard("mail", "ui_gift"),
        };

        public static IEnumerable<string> TextKeys() =>
            Cards.SelectMany(c => new[] { "howto." + c.Id + ".title", "howto." + c.Id + ".text" });
    }
}
