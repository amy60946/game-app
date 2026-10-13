using Pofi.Logic.Core;
using Pofi.Logic.Pet;

namespace Pofi.Logic.App
{
    public enum CareAction { Feed, Wash, Play, Tidy }

    /// <summary>Bakım düğmesine basınca petin söylediği cümle (konuşma balonu + ileride ses).</summary>
    public static class CareFeedback
    {
        public static string Message(Localization loc, CareAction action, CareResult result, string petName)
        {
            switch (result)
            {
                case CareResult.Ok:
                    switch (action)
                    {
                        case CareAction.Feed: return loc.Get("care.ok.feed");
                        case CareAction.Wash: return loc.Get("care.ok.wash");
                        case CareAction.Play: return loc.Get("care.ok.play");
                        default: return loc.Get("care.ok.tidy");
                    }
                case CareResult.Sleeping: return loc.Get("care.sleeping", petName);
                case CareResult.AlreadyFull: return loc.Get("care.full");
                case CareResult.NoItem:
                case CareResult.WrongItem: return loc.Get("care.no_item");
                default: return "";
            }
        }

        /// <summary>Pet durduğunda en düşük göstergeye göre ipucu; hepsi iyiyse boş.</summary>
        public static string Idle(Localization loc, PetStats stats, StatDecayConfig cfg)
        {
            var low = stats.Lowest();
            if (!stats.IsSad(low, cfg)) return "";
            switch (low)
            {
                case StatKind.Fullness: return loc.Get("care.sad.fullness");
                case StatKind.Cleanliness: return loc.Get("care.sad.cleanliness");
                case StatKind.Happiness: return loc.Get("care.sad.happiness");
                default: return loc.Get("care.sad.home");
            }
        }
    }
}
