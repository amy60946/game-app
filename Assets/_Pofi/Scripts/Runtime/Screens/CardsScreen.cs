namespace Pofi.Screens
{
    /// <summary>Masa oyunları (M8): Renk Eşle, Domino, Kule. Unity katmanı sıradaki adım; şimdilik haritada "çok yakında".</summary>
    public sealed class CardsScreen : ScreenBase
    {
        public static bool Available => false;

        protected override void Build()
        {
            App.Open(Logic.App.AppPage.Map);
        }
    }
}
