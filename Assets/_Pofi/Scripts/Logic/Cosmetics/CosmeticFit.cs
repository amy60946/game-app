using Pofi.Logic.Data;

namespace Pofi.Logic.Cosmetics
{
    public sealed class FitResult
    {
        public bool Allowed;
        public string Variant;     // kullanılacak model varyantı (ör. "ear_holes", "clip", "on_shell")
        public string ReasonKey;   // izin yoksa yerelleştirme anahtarı (fit.reason.*)

        public static FitResult Ok(string variant) => new FitResult { Allowed = true, Variant = variant };
        public static FitResult No(string reason) => new FitResult { Allowed = false, ReasonKey = reason };
    }

    /// <summary>
    /// CosmeticFitSystem kuralları (FR-SHOP-3a). Tür verisi (pets.json → fit) × eşya verisi (items.json) → uyum.
    /// Uyumsuz eşya dükkanda ve giydirme ekranında gri ve açıklamalı gösterilir; uygun varyant otomatik seçilir.
    /// </summary>
    public static class CosmeticFit
    {
        public static FitResult Evaluate(PetSpeciesDef pet, ItemDef item)
        {
            if (!item.IsWearable) return FitResult.Ok(null);
            var fit = pet.Fit;
            switch (item.Slot)
            {
                case Slot.Head:
                    return item.Variants != null && item.Variants.Contains(fit.Hat)
                        ? FitResult.Ok(fit.Hat)
                        : FitResult.No("fit.reason.head_shape");      // ör. kulaklık yeleli/kulaklı kafaya oturmuyor
                case Slot.Eyes:
                    return item.Variants != null && item.Variants.Contains(fit.Glasses)
                        ? FitResult.Ok(fit.Glasses)
                        : FitResult.No("fit.reason.no_nose_bridge");  // gaga/hortum: klipsli varyant yok
                case Slot.Body:
                    if (fit.Body == "apron_only" && item.Cut != "apron") return FitResult.No("fit.reason.body_apron_only");
                    return FitResult.Ok(item.Cut);
                case Slot.Back:
                    switch (fit.Back)
                    {
                        case "none": return FitResult.No("fit.reason.back_wings");          // Benli: kanat kapakları
                        case "flat_only": return item.Flat ? FitResult.Ok("flat") : FitResult.No("fit.reason.back_spikes_plates");
                        case "on_shell": return FitResult.Ok("on_shell");                    // Tosbi: kabuğun üstüne
                        case "tail_hole": return FitResult.Ok("tail_hole");
                        default: return FitResult.Ok("normal");
                    }
                case Slot.Hand:
                    if (item.Glove && fit.Hands == "flipper") return FitResult.No("fit.reason.flipper_glove");
                    return FitResult.Ok(fit.Hands);
                default:
                    return FitResult.No("fit.reason.unknown_slot");
            }
        }
    }
}
