using System.Linq;
using Pofi.Core;
using Pofi.Logic.App;
using Pofi.Logic.Progression;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>Seviye atlama kutlaması (FR-PROG-3): yeni seviye, açılan içerikler, büyüme evresi. "Yaşasın!" ile kapanır.</summary>
    public static class LevelUpCelebration
    {
        public static void Show(GameBootstrap app, LevelUp up)
        {
            var th = app.Theme;
            Audio.Sfx.Play(Audio.SfxKind.Success);
            var root = Ui.Fill(app.Overlay.transform, "LevelUp");
            root.gameObject.AddComponent<Image>().color = new Color(0.04f, 0.08f, 0.12f, 0.62f);
            // v3 (19 Ekim 2026): kutu yok; sahne üstünde mavi şerit + iri yıldız ve içinde seviye, altında başlık ve açılanlar
            var box = Ui.Rect(root, "Box", new Vector2(0.5f, 0.5f), new Vector2(1500f, 900f));
            var ribbon = Skin.Ribbon;
            if (ribbon != null)
            {
                var rb = Ui.Rect(box, "Ribbon", new Vector2(0.5f, 0.82f), new Vector2(900f, 230f));
                var ri = rb.gameObject.AddComponent<Image>(); ri.sprite = ribbon; ri.preserveAspect = true; ri.raycastTarget = false;
            }
            var star = Ui.Rect(box, "Star", new Vector2(0.5f, 0.82f), new Vector2(300f, 300f), new Vector2(0f, 14f));
            var big = Skin.Plain("star_big") ?? Ui.Icon("ui_star");
            if (big != null) { var si = star.gameObject.AddComponent<Image>(); si.sprite = big; si.preserveAspect = true; si.raycastTarget = false; }
            else { Ui.Panel(star, Theme.Hex("#FFD23F"), 30f).raycastTarget = false; star.localRotation = Quaternion.Euler(0f, 0f, 45f); }
            star.gameObject.AddComponent<Pulse>();
            Candy.Caption(star, up.To.ToString(), 120, new Vector2(0.5f, 0.45f), new Vector2(300f, 200f), Vector2.zero, new Color(0.47f, 0.25f, 0f, 1f));
            Candy.Caption(box, app.Loc.Get("levelup.title", up.To), 84, new Vector2(0.5f, 0.6f), new Vector2(1200f, 120f));

            var all = up.Unlocked.Where(id => !id.StartsWith("growth_") && app.Loc.Has("unlock." + id))
                .Select(id => app.Loc.Get("unlock." + id)).ToList();
            var lines = all.Take(4).ToList();
            if (all.Count > 4) lines.Add(app.Loc.Get("levelup.more", all.Count - 4));
            if (up.NewStage != null)
                Candy.Caption(box, app.Loc.Get("levelup.grew", app.State.PetName), 50, new Vector2(0.5f, 0.5f), new Vector2(1200f, 80f), Vector2.zero, new Color(0.1f, 0.35f, 0.1f, 1f));
            if (lines.Count > 0)
            {
                Candy.Caption(box, app.Loc.Get("levelup.unlocked"), 42, new Vector2(0.5f, 0.41f), new Vector2(1200f, 64f));
                Candy.Caption(box, string.Join("  ·  ", lines), 40, new Vector2(0.5f, 0.33f), new Vector2(1400f, 64f), Vector2.zero, new Color(0.2f, 0.15f, 0.11f, 0.95f));
            }
            Ui.Button(box, th, app.Loc.Get("levelup.ok"), new Vector2(0.5f, 0.14f), new Vector2(520f, 130f), () =>
            {
                Progress.MarkCelebrated(app.State, up);
                app.Save();
                Object.Destroy(root.gameObject);
                if (up.NewStage != null && (app.Page == AppPage.Home || app.Page == AppPage.Map)) app.Route();   // büyüyen peti yeniden çiz
            });
            CoinBurst.Play(app.Overlay.transform, th, "");
        }
    }
}
