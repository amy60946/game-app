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
            root.gameObject.AddComponent<Image>().color = new Color(0.05f, 0.1f, 0.3f, 0.6f);
            // Yatay: solda yıldız + seviye, sağda açılanlar listesi
            var box = Ui.Rect(root, "Box", new Vector2(0.5f, 0.5f), new Vector2(1500f, 860f));
            Ui.Panel(box, Color.white, th.Radius);
            var star = Ui.Rect(box, "Star", new Vector2(0.25f, 0.7f), new Vector2(200f, 200f));
            Ui.Panel(star, Theme.Hex("#FFD23F"), 30f).raycastTarget = false;
            star.localRotation = Quaternion.Euler(0f, 0f, 45f);
            star.gameObject.AddComponent<Pulse>();
            Ui.Label(box, app.Loc.Get("levelup.title", up.To), th.Font(96), th.Text, new Vector2(0.25f, 0.4f), new Vector2(700f, 140f), FontStyle.Bold);

            var all = up.Unlocked.Where(id => !id.StartsWith("growth_") && app.Loc.Has("unlock." + id))
                .Select(id => "- " + app.Loc.Get("unlock." + id)).ToList();
            var lines = all.Take(4).ToList();
            if (all.Count > 4) lines.Add(app.Loc.Get("levelup.more", all.Count - 4));
            var y = 0.86f;
            if (up.NewStage != null)
                Ui.Label(box, app.Loc.Get("levelup.grew", app.State.PetName), th.Font(46), th.Primary, new Vector2(0.25f, 0.22f), new Vector2(700f, 80f), FontStyle.Bold);
            if (lines.Count > 0)
            {
                Ui.Label(box, app.Loc.Get("levelup.unlocked"), th.Font(40), th.SubtleText, new Vector2(0.72f, y), new Vector2(760f, 60f), FontStyle.Bold);
                Ui.Label(box, string.Join("\n", lines), th.Font(40), th.Text, new Vector2(0.72f, y - 0.07f), new Vector2(700f, 420f), FontStyle.Normal, TextAnchor.UpperLeft)
                    .rectTransform.pivot = new Vector2(0.5f, 1f);
            }
            Ui.Button(box, th, app.Loc.Get("levelup.ok"), new Vector2(0.72f, 0.12f), new Vector2(520f, 130f), () =>
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
