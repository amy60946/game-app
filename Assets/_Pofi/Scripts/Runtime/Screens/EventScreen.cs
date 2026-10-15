using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Island;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Ada etkinlikleri (M10): Festival (Sv12, fenerleri yak → günde bir ödül) ve Fener (Sv15, ada finali → bir kez kutlama).
    /// </summary>
    public sealed class EventScreen : ScreenBase
    {
        private SpeechBubble _bubble;
        private int Day => XpSystem.DayNumber(App.LocalNow);

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            _bubble = Bubble(new Vector2(0.5f, 0.8f));
            if (App.Page == AppPage.Festival) Festival(); else Lighthouse();
            NavBar(AppPage.Map);
        }

        private void Festival()
        {
            // 3B festival meydanı (art/scripts/keyart.py, kredisiz) tam ekran; yoksa gece mavisi
            var bg = Ui.Area(Root, "Festival", Vector2.zero, Vector2.one);
            var bgi = bg.gameObject.AddComponent<Image>(); bgi.raycastTarget = false;
            var art = Ui.Art("Art/festival_bg");
            if (art != null)
            {
                bgi.sprite = art;
                var fit = bg.gameObject.AddComponent<AspectRatioFitter>();
                fit.aspectMode = AspectRatioFitter.AspectMode.EnvelopeParent; fit.aspectRatio = art.rect.width / art.rect.height;
            }
            else bgi.color = Theme.Hex("#22306B");
            bg.SetAsFirstSibling();
            Header(T("event.festival.title"));
            var claimed = !IslandEvents.CanClaimFestival(App.State.Events, Day);
            _bubble.Say(claimed ? T("event.festival.done") : T("event.festival.howto"), 5f);
            var lit = 0;
            var colors = new[] { "#FF5A7A", "#FFC83D", "#3DC9FF", "#7BD66B", "#A77BFF", "#FF9F43" };
            var off = Ui.Art("Games/lantern_off"); var on = Ui.Art("Games/lantern_on");
            for (var i = 0; i < IslandEvents.FestivalLanterns; i++)
            {
                // ipten sarkan kâğıt fenerler: üstte hafif kavis, dokununca yanar
                var t = IslandEvents.FestivalLanterns > 1 ? i / (float)(IslandEvents.FestivalLanterns - 1) : 0.5f;
                var x = Mathf.Lerp(0.16f, 0.84f, t);
                var y = 0.6f - Mathf.Sin(t * Mathf.PI) * 0.06f;
                var col = Theme.Hex(colors[i % colors.Length]);
                var rt = Ui.Rect(Root, "Lantern" + i, new Vector2(x, y), new Vector2(200f, 250f));
                var cord = Ui.Rect(rt, "Cord", new Vector2(0.5f, 1f), new Vector2(5f, 420f), new Vector2(0f, 200f));
                cord.gameObject.AddComponent<Image>().color = new Color(0.25f, 0.2f, 0.18f, 0.9f);
                var glow = Ui.Rect(rt, "Glow", new Vector2(0.5f, 0.5f), new Vector2(360f, 360f));
                var gi = glow.gameObject.AddComponent<Image>(); gi.sprite = CareFx.Dot; gi.raycastTarget = false;
                gi.color = new Color(col.r, col.g, col.b, 0.35f);
                glow.gameObject.SetActive(claimed);
                var img = Ui.Fill(rt, "Lamp").gameObject.AddComponent<Image>();
                img.sprite = claimed ? on : off; img.preserveAspect = true;
                if (img.sprite == null) { img.sprite = Ui.Rounded; img.type = Image.Type.Sliced; }
                img.color = claimed ? col : Color.Lerp(col, Color.gray, 0.6f);
                rt.gameObject.AddComponent<Sway>().Phase = i * 0.9f;
                var b = rt.gameObject.AddComponent<Button>();
                b.targetGraphic = img;
                rt.gameObject.AddComponent<PressBounce>();
                if (claimed) { rt.gameObject.AddComponent<Pulse>(); continue; }
                b.onClick.AddListener(() =>
                {
                    if (!b.interactable) return;
                    b.interactable = false;
                    if (on != null) img.sprite = on;
                    img.color = col;
                    glow.gameObject.SetActive(true);
                    rt.gameObject.AddComponent<Pulse>();
                    Audio.Sfx.Play(Audio.SfxKind.Pop);
                    lit++;
                    if (lit < IslandEvents.FestivalLanterns) return;
                    if (IslandEvents.ClaimFestival(App.State.Events, Day))
                    {
                        CoinBurst.Play(App.Overlay.transform, Th, T("event.festival.reward", IslandEvents.FestivalXp));
                        App.GrantXp(IslandEvents.FestivalXp, XpSource.Achievement);
                        App.Save();
                    }
                });
            }
        }

        private void Lighthouse()
        {
            var sky = Ui.Area(Root, "Sky", Vector2.zero, Vector2.one);
            sky.gameObject.AddComponent<Image>().color = Theme.Hex("#FFB88A");
            sky.SetAsFirstSibling();
            var sea = Ui.Area(Root, "Sea", Vector2.zero, new Vector2(1f, 0.2f));
            sea.gameObject.AddComponent<Image>().color = Theme.Hex("#3D8FD6");
            sea.SetSiblingIndex(1);
            Header(T("event.lighthouse.title"));
            var done = App.State.Events.FinalCelebrated;
            var tower = Ui.Rect(Root, "Tower", new Vector2(0.5f, 0.42f), new Vector2(220f, 600f));
            Ui.Panel(tower, Color.white, 40f).raycastTarget = false;
            for (var i = 0; i < 4; i++)
            {
                var stripe = Ui.Rect(tower, "Stripe" + i, new Vector2(0.5f, 0.15f + i * 0.22f), new Vector2(220f, 60f));
                Ui.Panel(stripe, Theme.Hex("#E8453C"), 10f).raycastTarget = false;
            }
            var lamp = Ui.Rect(Root, "Lamp", new Vector2(0.5f, 0.75f), new Vector2(200f, 200f));
            var lampImg = Ui.Panel(lamp, done ? Theme.Hex("#FFE38A") : new Color(1f, 1f, 1f, 0.3f), 100f);
            lampImg.raycastTarget = false;
            if (done) { lamp.gameObject.AddComponent<Pulse>(); _bubble.Say(T("event.lighthouse.again"), 5f); return; }

            _bubble.Say(T("event.lighthouse.howto"), 5f);
            var walker = Ui.Rect(Root, "Pet", new Vector2(0.5f, 0.1f), new Vector2(110f, 110f));
            Ui.Panel(walker, Theme.Hex(App.Data.Pet(App.State.PetId).MainColor), 55f).raycastTarget = false;
            var step = 0;
            const int Steps = 8;
            Ui.Button(Root, Th, T("event.climb"), new Vector2(0.82f, 0.25f), new Vector2(260f, 160f), () =>
            {
                if (step >= Steps) return;
                step++;
                Audio.Sfx.Play(Audio.SfxKind.Tap);
                var y = Mathf.Lerp(0.1f, 0.72f, step / (float)Steps);
                walker.anchorMin = walker.anchorMax = new Vector2(0.5f, y);
                if (step < Steps) return;
                lampImg.color = Theme.Hex("#FFE38A");
                lamp.gameObject.AddComponent<Pulse>();
                if (IslandEvents.ClaimFinal(App.State.Events))
                {
                    App.Save();
                    CoinBurst.Play(App.Overlay.transform, Th, T("event.lighthouse.final", App.State.PetName));
                    App.GrantXp(IslandEvents.FinalXp, XpSource.Achievement);
                    App.RecordActivity("lighthouse_lit");
                }
            }, true, default, 56, false);
        }
    }

    /// <summary>Rüzgârda hafif sallanma (fenerler).</summary>
    public sealed class Sway : MonoBehaviour
    {
        public float Phase;
        private void Update() => transform.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(Time.time * 1.6f + Phase) * 4f);
    }
}
