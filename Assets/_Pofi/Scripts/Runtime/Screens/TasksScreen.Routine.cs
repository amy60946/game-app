using System;
using System.Linq;
using Pofi.Logic.Tasks;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Rutin kartı (kullanıcı onayı 28 Ekim 2026; ortak akislar.md 5.4 adım 8): aynı rutinin adımları başlık + ilerleme altında
    /// sırayla. Yapılanlar soluk ve üstü çizili, sıradaki adım tam görev kartı ("Yaptım" yalnız onda), sonrakiler soluk.
    /// K grubunda (≤ 5) liste yok: yalnız sıradaki adım + nokta göstergesi. Başarısızlık durumu yok; rutin bitince ek coin yok.
    /// </summary>
    public sealed partial class TasksScreen
    {
        private const float RoutineHeadH = 104f, StepRowH = 76f, StepIndent = 46f;

        private bool Young => App.Session != null && App.Session.AgeBand == Logic.Profile.AgeBand.K;

        private void RoutineCard(RoutineGroup g, DateTime local)
        {
            RoutineHead(g);
            if (g.Complete)
            {
                RoutineDoneRow(g);
                if (!Young) foreach (var s in g.Steps) StepRow(s, g, local);
                return;
            }
            foreach (var s in g.Steps)
            {
                if (s.Key == g.Next.Key) Card(s, local);
                else if (!Young) StepRow(s, g, local);
            }
        }

        /// <summary>Rutin başlığı: simge, ad, "2 / 4" ve adım noktaları (yapılan dolu, sıradaki parlak, sonrakiler boş).</summary>
        private void RoutineHead(RoutineGroup g)
        {
            var row = Ui.Row(_list, "Routine " + g.Id, RoutineHeadH);
            var bg = Ui.Fill(row, "Bg");
            PanelKit.Flat(bg, Theme.Hex("#BFE3DA"), CardR);
            var body = Ui.Fill(row, "Body");
            body.offsetMin = new Vector2(0f, 4.5f);
            PanelKit.Flat(body, Theme.Hex("#EAF7F3"), CardR);
            var disc = Ui.Rect(row, "Icon", new Vector2(0f, 0.5f), new Vector2(76f, 76f), new Vector2(CardPadL + 38f, 2f));
            GoldKit.RimDisc(disc, Theme.Hex("#FFFDF5"), Theme.Hex("#9ED3C4"), 5f);
            Ui.IconImage(disc, Routines.IconFor(g.Icon), new Vector2(0.5f, 0.5f), 54f);

            var dotsW = g.Steps.Count * 30f;
            var right = 22f + Mathf.Max(dotsW, 96f);
            var titleW = CardW - (CardPadL + 76f + 18f) - right - 18f;
            var title = Ui.Label(row, string.IsNullOrWhiteSpace(g.Title) ? T("routine.default") : g.Title, F(32), Theme.Hex("#1F4E45"),
                new Vector2(0f, 0.5f), new Vector2(titleW, 56f), FontStyle.Bold, TextAnchor.MiddleLeft);
            title.rectTransform.pivot = new Vector2(0f, 0.5f);
            title.rectTransform.anchoredPosition = new Vector2(CardPadL + 76f + 18f, Young ? 2f : 16f);
            Fit(title, F(32));
            if (!Young)
            {
                var sub = Ui.Label(row, g.Complete ? T("routine.all_done") : T("routine.next_hint"), F(22), Theme.Hex("#3E7A6A"),
                    new Vector2(0f, 0.5f), new Vector2(titleW, 34f), FontStyle.Normal, TextAnchor.MiddleLeft);
                sub.rectTransform.pivot = new Vector2(0f, 0.5f);
                sub.rectTransform.anchoredPosition = new Vector2(CardPadL + 76f + 18f, -22f);
                Fit(sub, F(22));
                var prog = Ui.Label(row, T("routine.progress", g.Closed, g.Steps.Count), F(30), Theme.Hex("#1F4E45"),
                    new Vector2(1f, 0.5f), new Vector2(right, 40f), FontStyle.Bold, TextAnchor.MiddleRight, new Vector2(-(22f + right * 0.5f) + 22f * 0.5f, 18f));
                prog.rectTransform.pivot = new Vector2(0.5f, 0.5f);
            }
            // adım noktaları
            var y = Young ? 0f : -20f;
            for (var i = 0; i < g.Steps.Count; i++)
            {
                var s = g.Steps[i];
                var x = -(22f + dotsW) + i * 30f + 15f;
                var next = g.Next != null && s.Key == g.Next.Key;
                var d = Ui.Rect(row, "Dot" + i, new Vector2(1f, 0.5f), new Vector2(next ? 24f : 18f, next ? 24f : 18f), new Vector2(x, y));
                if (next)
                {
                    PanelKit.Flat(d, Color.white, 12f);
                    PanelKit.Grad(Ui.Rect(d, "In", new Vector2(0.5f, 0.5f), new Vector2(18f, 18f)), Theme.Hex("#FFF0A0"), Theme.Hex("#F2A81C"), 9f);
                    d.gameObject.AddComponent<SoftPulse>();
                }
                else PanelKit.Flat(d, Routines.IsOpen(s, App.LocalNow) ? Theme.Hex("#CFE6DF") : Theme.Hex("#4FA88F"), 9f);
            }
        }

        /// <summary>Rutin bitti: sakin bir kutlama satırı (ek coin yok).</summary>
        private void RoutineDoneRow(RoutineGroup g)
        {
            var row = Ui.Row(_list, "RoutineDone " + g.Id, 86f);
            var box = Ui.Rect(row, "Box", new Vector2(0.5f, 0.5f), new Vector2(CardW - StepIndent, 76f), new Vector2(StepIndent * 0.5f, 0f));
            PanelKit.Flat(box, Theme.Hex("#E4F6D8"), 28f);
            Ui.IconImage(box, "ui_trophy", new Vector2(0f, 0.5f), 58f, new Vector2(18f + 29f, 2f));
            var t = Ui.Label(box, T("routine.complete", string.IsNullOrWhiteSpace(g.Title) ? T("routine.default") : g.Title), F(28), InkGreen,
                new Vector2(0f, 0.5f), new Vector2(CardW - StepIndent - 110f, 60f), FontStyle.Bold, TextAnchor.MiddleLeft);
            t.rectTransform.pivot = new Vector2(0f, 0.5f);
            t.rectTransform.anchoredPosition = new Vector2(18f + 58f + 14f, 0f);
            Fit(t, F(28));
        }

        /// <summary>Rutinin sıradaki olmayan adımı: kısa satır. Yapılan üstü çizili, sonraki soluk; kırmızı/çarpı/"kaçırdın" yok.</summary>
        private void StepRow(ChildTask s, RoutineGroup g, DateTime local)
        {
            var done = Routines.IsDone(s);
            var open = Routines.IsOpen(s, local);
            var row = Ui.Row(_list, "Step " + s.Key, StepRowH);
            var box = Ui.Rect(row, "Box", new Vector2(0.5f, 0.5f), new Vector2(CardW - StepIndent, StepRowH - 8f), new Vector2(StepIndent * 0.5f, 0f));
            PanelKit.Flat(box, done ? Theme.Hex("#F3FAEF") : Theme.Hex("#FFFBF0"), 26f);
            if (!done) box.gameObject.AddComponent<CanvasGroup>().alpha = open ? 0.62f : 0.75f;

            var n = Ui.Rect(box, "Num", new Vector2(0f, 0.5f), new Vector2(44f, 44f), new Vector2(16f + 22f, 0f));
            PanelKit.Flat(n, done ? Theme.Hex("#4FA88F") : Theme.Hex("#E9DDBB"), 22f);
            if (done) Ui.IconImage(n, "ui_check", new Vector2(0.5f, 0.5f), 30f);
            else Ui.Label(n, (g.IndexOf(s) + 1).ToString(), F(24), Theme.Hex("#7A5A22"), new Vector2(0.5f, 0.5f), new Vector2(44f, 44f), FontStyle.Bold);

            var actW = 230f;
            var titleW = CardW - StepIndent - (16f + 44f + 16f) - actW - 20f;
            var title = Ui.Label(box, s.Title, F(27), done ? Theme.Hex("#5E7A55") : Theme.Hex("#4A2C0A"), new Vector2(0f, 0.5f), new Vector2(titleW, 52f),
                FontStyle.Bold, TextAnchor.MiddleLeft);
            title.rectTransform.pivot = new Vector2(0f, 0.5f);
            title.rectTransform.anchoredPosition = new Vector2(16f + 44f + 16f, 0f);
            Fit(title, F(27));
            if (done)
            {
                // üstü çizili (yazı tipinde çizgi yok: ince bir şerit)
                var strike = Ui.Rect(box, "Strike", new Vector2(0f, 0.5f), new Vector2(Mathf.Min(titleW, title.preferredWidth) + 8f, 3f));
                strike.pivot = new Vector2(0f, 0.5f);
                strike.anchoredPosition = new Vector2(16f + 44f + 12f, 0f);
                PanelKit.Flat(strike, new Color(0.37f, 0.48f, 0.33f, 0.7f), 1.5f);
            }

            var act = Ui.Rect(box, "Act", new Vector2(1f, 0.5f), new Vector2(actW, StepRowH - 16f), new Vector2(-(14f + actW * 0.5f), 0f));
            switch (s.Status)
            {
                case ChildTaskStatus.ChildDone when !s.IsMissed(local):
                    var w = Ui.Label(act, T("tasks.waiting_mavi"), F(22), Theme.Hex("#2B62D9"), new Vector2(0f, 0.5f), new Vector2(110f, 50f), FontStyle.Bold, TextAnchor.MiddleLeft);
                    w.rectTransform.pivot = new Vector2(0f, 0.5f);
                    Fit(w, F(22));
                    SoftBtn(act, T("task.undo"), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(116f, 48f), Vector2.zero, () => Mark(s, ChildTaskStatus.Assigned), 22);
                    break;
                case ChildTaskStatus.DeclinedByChild:
                    SoftBtn(act, T("task.undo"), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(116f, 48f), Vector2.zero, () => Mark(s, ChildTaskStatus.Assigned), 22);
                    break;
                case ChildTaskStatus.Approved:
                    Ui.IconImage(act, "ui_sunstone", new Vector2(1f, 0.5f), 48f, new Vector2(-24f, 0f));
                    break;
                case ChildTaskStatus.Assigned when open:
                    var l = Ui.Label(act, T("routine.later"), F(22), Theme.Hex("#8A6A32"), new Vector2(1f, 0.5f), new Vector2(actW, 50f), FontStyle.Bold, TextAnchor.MiddleRight);
                    l.rectTransform.pivot = new Vector2(1f, 0.5f);
                    break;
            }
        }

        /// <summary>Bugünün panosundaki görevler (rutin tamamlanma denetimi için).</summary>
        private System.Collections.Generic.List<ChildTask> TodayTasks()
        {
            var local = App.LocalNow;
            var today = Logic.App.DemoParent.Day(local);
            return App.State.Tasks.ForDisplay(local).Where(t => t.Date == today).ToList();
        }
    }
}
