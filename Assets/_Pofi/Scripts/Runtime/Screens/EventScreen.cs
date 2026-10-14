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
            Header(T("event.festival.title"));
            var bg = Ui.Area(Root, "Night", Vector2.zero, Vector2.one);
            bg.gameObject.AddComponent<Image>().color = Theme.Hex("#22306B");
            bg.SetAsFirstSibling();
            var claimed = !IslandEvents.CanClaimFestival(App.State.Events, Day);
            _bubble.Say(claimed ? T("event.festival.done") : T("event.festival.howto"), 5f);
            var lit = 0;
            for (var i = 0; i < IslandEvents.FestivalLanterns; i++)
            {
                var col = i % 3;
                var row = i / 3;
                var rt = Ui.Rect(Root, "Lantern" + i, new Vector2(0.22f + col * 0.28f, 0.55f - row * 0.2f), new Vector2(180f, 220f));
                var img = Ui.Panel(rt, claimed ? Theme.Hex("#FFC83D") : new Color(1f, 1f, 1f, 0.25f), 90f);
                var b = rt.gameObject.AddComponent<Button>();
                b.targetGraphic = img;
                if (claimed) { rt.gameObject.AddComponent<Pulse>(); continue; }
                var colors = new[] { "#FF5A7A", "#FFC83D", "#3DC9FF", "#7BD66B", "#A77BFF", "#FF9F43" };
                var c = colors[i];
                b.onClick.AddListener(() =>
                {
                    if (!b.interactable) return;
                    b.interactable = false;
                    img.color = Theme.Hex(c);
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
}
