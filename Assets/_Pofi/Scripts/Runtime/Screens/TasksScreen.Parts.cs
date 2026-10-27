using System;
using Pofi.Logic.Data;
using Pofi.Logic.Tasks;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>Görevler penceresinin parçaları: ev görevi kartı (D), oyun görevi satırı, sandık satırı, düğmeler.</summary>
    public sealed partial class TasksScreen
    {
        // kart sütunları (taslak D: 76 | 1fr | 112 | 200 px, ×1,5; sağdaki eylem sütunu dar pencereye göre biraz kısa)
        private const float CardPadL = 18f, SealD = 114f, ColGap = 20f, CardPadR = 22f, CardMinH = 186f, CardR = 33f;
        // dar pencerede (iPad 4:3) ödül ve eylem sütunu daralır: başlık sütunu 116 birime düşüp kelimeler ortasından bölünüyordu
        // ("Dişlerin / i fırçala", tasarım turu 24 Ekim 2026)
        private float RewardW => _narrow ? 112f : 140f;
        private float ActW => _narrow ? 214f : 250f;
        private const float ChipH = 45f, StepD = 42f, StepLine = 24f;

        /// <summary>Postacı Mavi (v4 tam boy; yoksa portre, yoksa martı simgesi).</summary>
        private static Sprite Mavi => Ui.Icon("res_mavi_post") ?? Ui.Art("Portraits/res_mavi") ?? Ui.Icon("res_seagull");

        private float CardW => _evContentW - ListPadX * 2f;
        private float MainW => CardW - CardPadL - SealD - ColGap - ColGap - RewardW - ColGap - ActW - CardPadR;

        // ------------------------------------------------------------------ ev görevi kartı (D)

        private void Card(ChildTask task, DateTime local)
        {
            var missed = task.IsMissed(local);
            var s = task.Status;
            var waiting = !missed && s == ChildTaskStatus.ChildDone;
            var ok = s == ChildTaskStatus.Approved;
            var faded = missed || s == ChildTaskStatus.RejectedByParent || s == ChildTaskStatus.DeclinedByChild;
            var step = ok ? 2 : waiting ? 1 : 0;   // yol: yap → Mavi götürüyor → taş geldi

            var row = Ui.Row(_list, task.Key, CardMinH);
            var face = ok ? Theme.Hex("#F1FAE8") : waiting ? Theme.Hex("#F1F6FF") : Theme.Hex("#FFFDF5");
            var lip = ok ? Theme.Hex("#BFE3A4") : waiting ? Theme.Hex("#BCD3F2") : Theme.Hex("#E6CF98");
            var bg = Ui.Fill(row, "Bg");
            PanelKit.Flat(bg, lip, CardR);
            var sh = bg.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.47f, 0.27f, 0.04f, 0.12f); sh.effectDistance = new Vector2(0f, -9f);
            var body = Ui.Fill(row, "Body");
            body.offsetMin = new Vector2(0f, 4.5f);
            PanelKit.Flat(body, face, CardR);
            if (faded) row.gameObject.AddComponent<CanvasGroup>().alpha = 0.72f;

            // orta: başlık + çipler (beceri, zorluk) + yol
            var mainW = MainW;
            var main = Ui.Rect(row, "Main", Vector2.zero, Vector2.zero);
            main.anchorMin = new Vector2(0f, 0.5f); main.anchorMax = new Vector2(1f, 0.5f); main.pivot = new Vector2(0f, 0.5f);
            main.offsetMin = new Vector2(CardPadL + SealD + ColGap, 0f);
            main.offsetMax = new Vector2(-(CardPadR + ActW + ColGap + RewardW + ColGap), 0f);
            var title = Ui.Label(main, task.Title, F(34), Theme.Hex("#4A2C0A"), new Vector2(0.5f, 1f), new Vector2(0f, 40f), FontStyle.Bold, TextAnchor.UpperLeft);
            title.lineSpacing = 0.9f;
            var line = PrefH(title, mainW, "Ag");
            var titleH = Mathf.Min(PrefH(title, mainW, task.Title), line * 3.05f);
            if (PrefH(title, mainW, task.Title) > titleH + 1f) Fit(title, F(34));   // çok uzun başlık: üç satıra sığacak kadar küçülür
            var word = 0f;
            foreach (var wd in task.Title.Split(' ')) word = Mathf.Max(word, PrefW(title, wd));
            if (word > mainW) title.fontSize = Mathf.Max(Mathf.RoundToInt(F(34) * 0.6f), Mathf.FloorToInt(title.fontSize * mainW / word));   // en uzun kelime bölünmesin
            var trt = title.rectTransform;
            trt.anchorMin = new Vector2(0f, 1f); trt.anchorMax = new Vector2(1f, 1f); trt.pivot = new Vector2(0.5f, 1f);
            trt.sizeDelta = new Vector2(0f, titleH); trt.anchoredPosition = Vector2.zero;

            var chips = Ui.Rect(main, "Chips", Vector2.zero, Vector2.zero);
            chips.anchorMin = new Vector2(0f, 1f); chips.anchorMax = new Vector2(1f, 1f); chips.pivot = new Vector2(0.5f, 1f);
            chips.sizeDelta = new Vector2(0f, ChipH); chips.anchoredPosition = new Vector2(0f, -(titleH + 10f));
            var x = 0f;
            var skill = SkillCatalog.Label(SkillCatalog.Map(task.Skill));
            if (skill != null) x += Chip(chips, x, "ui_star", skill, Theme.Hex("#E7F0FF"), Theme.Hex("#24508F"), 0) + 10f;
            var rank = RealTaskRewards.Rank(task.Difficulty);
            x += Chip(chips, x, null, T("tasks.diff." + (rank == 3 ? "hard" : rank == 2 ? "medium" : "easy")), Theme.Hex("#F5E8C8"), Theme.Hex("#8A5A22"), rank) + 12f;
            var stepsW = StepD * 3f + StepLine * 2f;
            var blockH = titleH + 10f + ChipH;
            if (x + stepsW <= mainW) Steps(chips, x, step);
            else
            {
                // dar kart: yol ikinci satırda
                var path = Ui.Rect(main, "Path", Vector2.zero, Vector2.zero);
                path.anchorMin = new Vector2(0f, 1f); path.anchorMax = new Vector2(1f, 1f); path.pivot = new Vector2(0.5f, 1f);
                path.sizeDelta = new Vector2(0f, ChipH); path.anchoredPosition = new Vector2(0f, -(blockH + 8f));
                Steps(path, 0f, step);
                blockH += 8f + ChipH;
            }
            // ebeveynin notu: "Tekrar dene" (görev yeniden açık) ya da onayla gelen söz (ParentApp İnceleme; ortak 20261027130000)
            var note = NoteLine(task, missed);
            if (note != null)
            {
                var nl = Ui.Label(main, note, F(24), task.Retry ? Theme.Hex("#B4472A") : Theme.Hex("#3E7A2A"), new Vector2(0.5f, 1f), new Vector2(0f, 40f),
                    FontStyle.Bold, TextAnchor.UpperLeft);
                nl.lineSpacing = 0.92f;
                var nh = Mathf.Min(PrefH(nl, mainW, note), PrefH(nl, mainW, "Ag") * 3.05f);   // en çok üç satır
                if (PrefH(nl, mainW, note) > nh + 1f) Fit(nl, F(24));
                var nrt = nl.rectTransform;
                nrt.anchorMin = new Vector2(0f, 1f); nrt.anchorMax = new Vector2(1f, 1f); nrt.pivot = new Vector2(0.5f, 1f);
                nrt.sizeDelta = new Vector2(0f, nh); nrt.anchoredPosition = new Vector2(0f, -(blockH + 8f));
                blockH += 8f + nh;
            }
            main.sizeDelta = new Vector2(main.sizeDelta.x, blockH);
            main.anchoredPosition = new Vector2(main.anchoredPosition.x, 2f);
            var h = Mathf.Max(CardMinH, blockH + 40f);
            var le = row.GetComponent<LayoutElement>(); le.preferredHeight = le.minHeight = h;
            row.sizeDelta = new Vector2(0f, h);

            // sol: "Ailenden" mührü (hoş geldin görevinde Mavi: "Mavi'den")
            var welcome = task.TaskId == WelcomeId;
            var seal = Ui.Rect(row, "Seal", new Vector2(0f, 0.5f), new Vector2(SealD, SealD), new Vector2(CardPadL + SealD * 0.5f, 8f));
            GoldKit.RimDisc(seal, welcome ? Theme.Hex("#E7F0FF") : Theme.Hex("#FFF7DE"), welcome ? Theme.Hex("#BCD3F2") : Theme.Hex("#F6DFA4"), 6f);
            if (welcome && Mavi != null) Pic(seal, Mavi, "Mavi", new Vector2(0.5f, 0.5f), new Vector2(72f, 100f), new Vector2(0f, 12f));
            else Ui.IconImage(seal, "ui_home", new Vector2(0.5f, 0.5f), 78f, new Vector2(0f, 10f));
            GoldKit.Ribbon(seal, T(welcome ? "welcome_task.from" : "tasks.from_family"), welcome ? GoldKit.Tone.Blue : GoldKit.Tone.Red, 36f, 21, new Vector2(0.5f, 0f), new Vector2(0f, 3f));

            // sağda ödül: büyük Güneş Taşı × zorluk (kolay 1 / orta 2 / zor 3), altında küçük coin
            Reward(row, welcome ? 1 : RealTaskRewards.Stones(task.Difficulty), task.RewardCoins);

            // en sağda eylemler
            var act = Ui.Rect(row, "Act", new Vector2(1f, 0.5f), new Vector2(ActW, 141f), new Vector2(-(CardPadR + ActW * 0.5f), 2f));
            if (welcome)
            {
                var wd = GoBtn(act, T("task.done"), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(ActW, 78f), Vector2.zero, WelcomeDone, 34);
                _welcomeBtn = (RectTransform)wd.transform;   // "Yaptım" tanıtımı gerçek görevlere kalır; buradaki eli rehber gösterir
            }
            else if (missed) Note(act, T("tasks.missed_short"), 0f, 141f);
            else
            {
                switch (s)
                {
                    case ChildTaskStatus.Assigned:
                        var done = GoBtn(act, T("task.done"), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(ActW, 78f), Vector2.zero, () => Mark(task, ChildTaskStatus.ChildDone), 34);
                        if (_firstDone == null) _firstDone = (RectTransform)done.transform;
                        SoftBtn(act, T("task.decline"), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(180f, 54f), Vector2.zero, () => Mark(task, ChildTaskStatus.DeclinedByChild), 24);
                        break;
                    case ChildTaskStatus.ChildDone:
                        WaitChip(act);
                        SoftBtn(act, T("task.undo"), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(180f, 54f), Vector2.zero, () => Mark(task, ChildTaskStatus.Assigned), 24);
                        // B'nin sevimliliği: Mavi mektubu ailene götürüyor (kartın üstünde kanat çırpar)
                        var fly = Pic(row, Mavi, "MaviFly", new Vector2(1f, 1f), new Vector2(72f, 100f), new Vector2(-(CardPadR + ActW + 32f), -44f));
                        if (fly != null) { fly.rectTransform.pivot = new Vector2(0.5f, 0f); fly.gameObject.AddComponent<FlapFloat>(); }
                        break;
                    case ChildTaskStatus.DeclinedByChild:
                        Note(act, T("tasks.declined_soft"), 0f, 80f);
                        SoftBtn(act, T("task.undo"), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(180f, 54f), Vector2.zero, () => Mark(task, ChildTaskStatus.Assigned), 24);
                        break;
                    case ChildTaskStatus.Approved:
                        OkMessage(act);
                        break;
                    case ChildTaskStatus.RejectedByParent:
                        Note(act, T("task.rejected", task.ParentNote ?? "").Trim(), 0f, 141f);
                        break;
                }
            }
        }

        /// <summary>Kartın not satırı: ebeveyn "Tekrar dene" dediyse (not varsa aynen), onaylı görevde ebeveynin sözü; yoksa null.</summary>
        private string NoteLine(ChildTask task, bool missed)
        {
            var note = task.ParentNote?.Trim();
            if (task.Retry && task.Status == ChildTaskStatus.Assigned && !missed)
                return string.IsNullOrEmpty(note) ? T("task.retry") : T("task.retry_note", note);
            if (task.Status == ChildTaskStatus.Approved && !string.IsNullOrEmpty(note)) return T("task.approved_note", note);
            return null;
        }

        /// <summary>Kart çipi (beceri / zorluk). Zorlukta <paramref name="dots"/> kadar dolu nokta (●●○ yazı tipinde yok: çizilir).</summary>
        private float Chip(RectTransform row, float x, string icon, string text, Color bg, Color ink, int dots)
        {
            var chip = Ui.Rect(row, "Chip", new Vector2(0f, 0.5f), new Vector2(100f, ChipH));
            chip.pivot = new Vector2(0f, 0.5f);
            chip.anchoredPosition = new Vector2(x, 0f);
            PanelKit.Flat(chip, bg, ChipH * 0.5f);
            var t = Ui.Label(chip, text, F(22), ink, new Vector2(0f, 0.5f), new Vector2(300f, ChipH), FontStyle.Bold, TextAnchor.MiddleLeft);
            var tw = Mathf.Min(300f, t.preferredWidth);
            var left = icon != null ? 7f + 33f + 5f : 16f;
            var right = dots > 0 ? 10f + 3f * 12f + 2f * 5f + 16f : 16f;
            var w = left + tw + right;
            chip.sizeDelta = new Vector2(w, ChipH);
            if (icon != null) Ui.IconImage(chip, icon, new Vector2(0f, 0.5f), 33f, new Vector2(7f + 16.5f, 0f));
            t.rectTransform.pivot = new Vector2(0f, 0.5f);
            t.rectTransform.sizeDelta = new Vector2(tw + 4f, ChipH);
            t.rectTransform.anchoredPosition = new Vector2(left, 1f);
            if (dots > 0)
                for (var i = 0; i < 3; i++)
                {
                    var d = Ui.Rect(chip, "Dot" + i, new Vector2(0f, 0.5f), new Vector2(12f, 12f), new Vector2(left + tw + 10f + 6f + i * 17f, 0f));
                    PanelKit.Flat(d, i < dots ? ink : new Color(ink.r, ink.g, ink.b, 0.25f), 6f);
                }
            return w;
        }

        /// <summary>Üç adımlı yol: el (yap) → Mavi (ailene götürüyor) → Güneş Taşı (geldi). Şu anki adım parlar ve nabız atar.</summary>
        private void Steps(RectTransform row, float x, int current)
        {
            var icons = new[] { Ui.Icon("ui_hand"), Mavi, Ui.Icon("ui_sunstone") };
            for (var i = 1; i < 3; i++)   // önce çizgiler (dairelerin altında kalsın)
            {
                var lx = x + i * (StepD + StepLine) - StepLine * 0.5f;
                var ln = Ui.Rect(row, "Line" + i, new Vector2(0f, 0.5f), new Vector2(StepLine + 8f, 6f), new Vector2(lx, 0f));
                PanelKit.Flat(ln, i <= current ? Theme.Hex("#F2A81C") : Theme.Hex("#E3CB92"), 3f);
            }
            for (var i = 0; i < 3; i++)
            {
                var cx = x + StepD * 0.5f + i * (StepD + StepLine);
                var holder = Ui.Rect(row, "Step" + i, new Vector2(0f, 0.5f), new Vector2(StepD, StepD), new Vector2(cx, 0f));
                if (i == current)
                {
                    var glow = Ui.Rect(holder, "Glow", new Vector2(0.5f, 0.5f), new Vector2(StepD + 30f, StepD + 30f));
                    var gi = glow.gameObject.AddComponent<Image>(); gi.sprite = PanelKit.Glow; gi.color = new Color(0.95f, 0.66f, 0.11f, 0.8f); gi.raycastTarget = false;
                    PanelKit.Flat(Ui.Rect(holder, "Ring", new Vector2(0.5f, 0.5f), new Vector2(StepD + 9f, StepD + 9f)), Color.white, (StepD + 9f) * 0.5f);
                    PanelKit.Grad(Ui.Rect(holder, "Dot", new Vector2(0.5f, 0.5f), new Vector2(StepD, StepD)), Theme.Hex("#FFF0A0"), Theme.Hex("#F2A81C"), StepD * 0.5f);
                    holder.gameObject.AddComponent<SoftPulse>();
                }
                else PanelKit.Flat(Ui.Rect(holder, "Dot", new Vector2(0.5f, 0.5f), new Vector2(StepD, StepD)), i < current ? Theme.Hex("#F7D27A") : Theme.Hex("#EADBB5"), StepD * 0.5f);
                var pic = Pic(holder, icons[i], "Icon", new Vector2(0.5f, 0.5f), new Vector2(31f, i == 1 ? 38f : 31f), Vector2.zero);
                if (pic != null && i > current) pic.color = new Color(1f, 1f, 1f, 0.4f);
            }
        }

        private void Reward(RectTransform row, int stones, int coins)
        {
            var rew = Ui.Rect(row, "Reward", new Vector2(1f, 0.5f), new Vector2(RewardW, 152f), new Vector2(-(CardPadR + ActW + ColGap + RewardW * 0.5f), 4f));
            var glow = Ui.Rect(rew, "Glow", new Vector2(0.5f, 1f), new Vector2(136f, 136f), new Vector2(0f, -52f));
            var gi = glow.gameObject.AddComponent<Image>(); gi.sprite = PanelKit.Glow; gi.color = new Color(1f, 0.75f, 0.24f, 0.5f); gi.raycastTarget = false;
            Ui.IconImage(rew, "ui_sunstone", new Vector2(0.5f, 1f), 105f, new Vector2(0f, -52f));
            var n = Ui.Label(rew, "×" + stones, 39, Theme.Hex("#8A3B00"), new Vector2(0.5f, 1f), new Vector2(90f, 50f), FontStyle.Bold, TextAnchor.LowerRight, new Vector2(74f, -111f));
            n.rectTransform.pivot = new Vector2(1f, 0f);
            var o = n.gameObject.AddComponent<Outline>(); o.effectColor = Color.white; o.effectDistance = new Vector2(3f, -3f);
            if (coins <= 0) return;   // Mavi'nin hoş geldin görevi yalnız taş verir
            var c = Ui.Label(rew, T("tasks.coin", coins), 25, Theme.Hex("#8A5A22"), new Vector2(0.5f, 0f), new Vector2(120f, 40f), FontStyle.Bold, TextAnchor.MiddleLeft);
            var cw = 39f + 4f + Mathf.Min(100f, c.preferredWidth);
            c.rectTransform.pivot = new Vector2(0f, 0.5f);
            c.rectTransform.anchoredPosition = new Vector2(-cw * 0.5f + 43f, 20f);
            Ui.IconImage(rew, "ui_coin", new Vector2(0.5f, 0f), 39f, new Vector2(-cw * 0.5f + 19.5f, 20f));
        }

        /// <summary>Onay bekliyor (B'nin dili): mavi çip, solda postacı Mavi, "Ailen bakıyor".</summary>
        private void WaitChip(RectTransform act)
        {
            var chip = Ui.Rect(act, "Wait", new Vector2(0.5f, 1f), new Vector2(ActW, 69f));
            chip.pivot = new Vector2(0.5f, 1f);
            PanelKit.Lipped(chip, Theme.Hex("#5E9BFF"), Theme.Hex("#2B62D9"), Theme.Hex("#1B47A8"), 34f, 4.5f);
            Pic(chip, Mavi, "Mavi", new Vector2(0f, 0.5f), new Vector2(54f, 64f), new Vector2(8f + 27f, 4f));
            var t = Ui.Label(chip, T("tasks.waiting_mavi"), F(25), Color.white, new Vector2(0f, 0.5f), new Vector2(ActW - 82f, 56f), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(70f, 3f));
            t.rectTransform.pivot = new Vector2(0f, 0.5f);
            InkShadow(t, RibbonInk);
            Fit(t, F(25));
        }

        private void OkMessage(RectTransform act)
        {
            var t = Ui.Label(act, T("tasks.stone_came"), F(33), InkGreen, new Vector2(0.5f, 0.5f), new Vector2(ActW - 60f, 60f), FontStyle.Bold, TextAnchor.MiddleLeft);
            var tw = Mathf.Min(ActW - 60f, t.preferredWidth);
            var total = 54f + 6f + tw;
            t.rectTransform.pivot = new Vector2(0f, 0.5f);
            t.rectTransform.anchoredPosition = new Vector2(-total * 0.5f + 60f, 0f);
            Fit(t, F(33));
            Ui.IconImage(act, "ui_check", new Vector2(0.5f, 0.5f), 54f, new Vector2(-total * 0.5f + 27f, 0f));
        }

        /// <summary>Yumuşak bilgi yazısı (yapamam, kaçırıldı, ebeveyn notu): eylem sütununun üstünden <paramref name="top"/> aşağı.</summary>
        private void Note(RectTransform act, string text, float top, float height)
        {
            var t = Ui.Label(act, text, F(24), Theme.Hex("#8A5A22"), new Vector2(0.5f, 1f), new Vector2(ActW, height > 0f ? height : 141f), FontStyle.Bold, TextAnchor.MiddleCenter);
            t.rectTransform.pivot = new Vector2(0.5f, 1f);
            t.rectTransform.anchoredPosition = new Vector2(0f, -top);
            t.lineSpacing = 0.9f;
            Fit(t, F(24));
        }

        // ------------------------------------------------------------------ oyun görevleri (sağ)

        /// <summary>Kompakt oyun görevi satırı: yıldız, yazı, +XP; altında ilerleme çubuğu ve n/hedef. Yüksekliği döner.</summary>
        private float QuestRow(RectTransform parent, float y, DailyQuestDef q, bool done, int prog)
        {
            var w = _oyContentW;
            const float textX = 18f + 57f + 14f, rightW = 84f;
            var textW = w - textX - 16f - rightW - 6f;
            var rt = Ui.Rect(parent, "Quest " + q.Id, Vector2.zero, Vector2.zero);
            rt.anchorMin = new Vector2(0f, 1f); rt.anchorMax = new Vector2(1f, 1f); rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = new Vector2(0f, -y);
            var ink = done ? InkGreen : InkBlue;
            var txt = Ui.Label(rt, q.Text, F(27), ink, new Vector2(0f, 1f), new Vector2(textW, 40f), FontStyle.Bold, TextAnchor.UpperLeft);
            txt.lineSpacing = 0.9f;
            var line = PrefH(txt, textW, "Ag");
            var th = Mathf.Min(PrefH(txt, textW, q.Text), line * 2.05f);
            if (PrefH(txt, textW, q.Text) > th + 1f) Fit(txt, F(27));
            var h = Mathf.Max(92f, 14f + th + 10f + 16f + 16f);
            rt.sizeDelta = new Vector2(0f, h);

            var bg = Ui.Fill(rt, "Bg"); PanelKit.Flat(bg, Theme.Hex("#BCD3F2"), 24f);
            var face = Ui.Fill(rt, "Face"); face.offsetMin = new Vector2(0f, 4.5f); PanelKit.Flat(face, Color.white, 24f);
            bg.SetAsFirstSibling(); face.SetSiblingIndex(1);
            Ui.IconImage(rt, "ui_star", new Vector2(0f, 0.5f), 57f, new Vector2(18f + 28.5f, 2f));
            var trt = txt.rectTransform;
            trt.pivot = new Vector2(0f, 1f); trt.sizeDelta = new Vector2(textW, th); trt.anchoredPosition = new Vector2(textX, -14f);

            var xp = Ui.Label(rt, T("xp.star", Logic.App.Activity.QuestXp(App.State, App.Levels, q)), F(27), Theme.Hex("#B8751A"), new Vector2(1f, 1f), new Vector2(rightW, 38f), FontStyle.Bold, TextAnchor.MiddleRight, new Vector2(-16f, -12f));
            xp.rectTransform.pivot = new Vector2(1f, 1f);
            var bar = Ui.Bar(rt, new Vector2(0f, 0f), new Vector2(textW, 16f), Theme.Hex("#D9E5F5"), Color.white, 8f);
            var brt = (RectTransform)bar.transform.parent;
            brt.pivot = new Vector2(0f, 0f); brt.anchoredPosition = new Vector2(textX, 18f);
            var grad = bar.gameObject.AddComponent<VGradient>();
            grad.Top = done ? Theme.Hex("#A6EB8E") : Theme.Hex("#8CC2FF");
            grad.Bottom = done ? Theme.Hex("#3BB55B") : Theme.Hex("#2F7BE8");
            Ui.SetBar(bar, (float)prog / Mathf.Max(1, q.Target));
            var p = Ui.Label(rt, done ? T("home.daily_done") : prog + "/" + q.Target, F(22), done ? InkGreen : InkBlueSoft, new Vector2(1f, 0f), new Vector2(rightW + 6f, 34f), FontStyle.Bold, TextAnchor.MiddleRight, new Vector2(-16f, 9f));
            p.rectTransform.pivot = new Vector2(1f, 0f);
            return h;
        }

        /// <summary>Günlük sandık (S2): üç görev bitince bir kez açılır; şans oranları her zaman görünür.</summary>
        private void ChestRow(RectTransform parent, int open)
        {
            var dq = App.State.DailyQuests;
            var ready = Logic.Meta.DailyChest.Ready(dq);
            var w = _oyContentW;
            const float textX = 12f + 78f + 10f;
            var btnW = ready ? 120f : 0f;
            var textW = w - textX - 14f - (ready ? btnW + 12f : 0f);
            var rt = Ui.Rect(parent, "Chest", Vector2.zero, Vector2.zero);
            rt.anchorMin = new Vector2(0f, 0f); rt.anchorMax = new Vector2(1f, 0f); rt.pivot = new Vector2(0.5f, 0f);
            rt.anchoredPosition = Vector2.zero;
            var bg = Ui.Fill(rt, "Bg"); PanelKit.Flat(bg, new Color(1f, 1f, 1f, 0.75f), 24f);
            var title = Ui.Label(rt, T(dq.ChestOpened ? "chest.opened" : ready ? "chest.open_hint" : open > 0 ? "chest.left" : "chest.locked", open), F(26), InkBlue, new Vector2(0f, 1f), new Vector2(textW, 40f), FontStyle.Bold, TextAnchor.UpperLeft);
            var odds = Ui.Label(rt, T("chest.odds"), F(20), InkBlueSoft, new Vector2(0f, 1f), new Vector2(textW, 30f), FontStyle.Bold, TextAnchor.UpperLeft);
            title.lineSpacing = odds.lineSpacing = 0.9f;
            var th = PrefH(title, textW, title.text);
            var oh = PrefH(odds, textW, odds.text);
            var h = Mathf.Max(100f, 14f + th + 4f + oh + 14f);
            rt.sizeDelta = new Vector2(0f, h);
            title.rectTransform.pivot = odds.rectTransform.pivot = new Vector2(0f, 1f);
            title.rectTransform.sizeDelta = new Vector2(textW, th); title.rectTransform.anchoredPosition = new Vector2(textX, -14f);
            odds.rectTransform.sizeDelta = new Vector2(textW, oh); odds.rectTransform.anchoredPosition = new Vector2(textX, -14f - th - 4f);
            var gift = Ui.IconImage(rt, "ui_gift", new Vector2(0f, 0.5f), 78f, new Vector2(12f + 39f, 0f));
            if (gift != null && ready) Hover.On(gift, 5f, 0.06f);
            if (!ready) return;
            var b = GoBtn(rt, T("chest.open"), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(btnW, 66f), new Vector2(-12f, 0f), OpenChest, 30);
            Hover.On(b, 5f, 0.06f);
        }

        // ------------------------------------------------------------------ düğmeler ve yardımcılar

        /// <summary>E dili tek yeşil ana düğme ("Yaptım", "Aç", "Ödülü al").</summary>
        private Button GoBtn(Transform parent, string text, Vector2 anchor, Vector2 pivot, Vector2 size, Vector2 pos, Action onClick, int font)
        {
            var rt = Ui.Rect(parent, "Go " + text, anchor, size, pos);
            rt.pivot = pivot;
            var body = Candy.Shell(rt, Candy.Green);
            var t = Candy.Caption(rt, text, F(font), new Vector2(0.5f, 0.5f), new Vector2(size.x - 16f, size.y), new Vector2(0f, 2f), GoldKit.RibbonGreenInk);
            t.name = "Label";
            Fit(t, F(font));
            return Clickable(rt, body, onClick);
        }

        /// <summary>Krem ikincil düğme ("Yapamam", "Geri al", "Adaya götür"). Genişlik 0 ise yazıya göre.</summary>
        private Button SoftBtn(Transform parent, string text, Vector2 anchor, Vector2 pivot, Vector2 size, Vector2 pos, Action onClick, int font, string icon = null)
        {
            var rt = Ui.Rect(parent, "Soft " + text, anchor, size, pos);
            rt.pivot = pivot;
            var t = Ui.Label(rt, text, F(font), InkTan, new Vector2(0.5f, 0.5f), new Vector2(Mathf.Max(40f, size.x - 20f), size.y), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(0f, 2f));
            var iconW = icon != null ? size.y * 0.72f + 6f : 0f;
            if (size.x <= 0f)
            {
                size.x = 22f + iconW + t.preferredWidth + 24f;
                rt.sizeDelta = size;
                t.rectTransform.sizeDelta = new Vector2(t.preferredWidth + 6f, size.y);
            }
            t.rectTransform.anchoredPosition = new Vector2(iconW * 0.5f, 2f);
            var body = Candy.Shell(rt, Candy.White);
            t.transform.SetAsLastSibling();
            if (icon != null)
            {
                var ic = Ui.IconImage(rt, icon, new Vector2(0.5f, 0.5f), size.y * 0.72f, new Vector2(-(t.preferredWidth + 6f) * 0.5f - 1f, 2f));
                if (ic != null) ic.SetAsLastSibling();
            }
            Fit(t, F(font));
            return Clickable(rt, body, onClick);
        }

        private static Button Clickable(RectTransform rt, Image body, Action onClick)
        {
            var b = rt.gameObject.AddComponent<Button>();
            b.targetGraphic = body;
            var cols = b.colors; cols.pressedColor = new Color(0.85f, 0.85f, 0.85f); b.colors = cols;
            b.onClick.AddListener(() => Audio.Sfx.Play(Audio.SfxKind.Tap));
            if (onClick != null) b.onClick.AddListener(() => onClick());
            rt.gameObject.AddComponent<PressBounce>();
            return b;
        }

        private static Image Pic(Transform parent, Sprite sp, string name, Vector2 anchor, Vector2 size, Vector2 pos)
        {
            if (sp == null) return null;
            var rt = Ui.Rect(parent, name, anchor, size, pos);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sp; img.preserveAspect = true; img.raycastTarget = false;
            return img;
        }

        /// <summary>Kutuya sığmayan yazı küçülür (en çok %60'a); sığıyorsa olduğu gibi kalır.</summary>
        private static void Fit(Text t, int size)
        {
            t.resizeTextForBestFit = true;
            t.resizeTextMaxSize = size;
            t.resizeTextMinSize = Mathf.Max(10, Mathf.RoundToInt(size * 0.6f));
            t.verticalOverflow = VerticalWrapMode.Truncate;
        }

        private static void InkShadow(Text t, Color ink)
        {
            var s = t.gameObject.AddComponent<Shadow>();
            s.effectColor = ink; s.effectDistance = new Vector2(0f, -3f);
        }

        /// <summary>Verilen genişlikte yazının yüksekliği (yerleşim kurulmadan önce, ölçü için).</summary>
        private static float PrefW(Text t, string text)
        {
            var settings = t.GetGenerationSettings(Vector2.zero);
            return t.cachedTextGeneratorForLayout.GetPreferredWidth(text, settings) / Mathf.Max(0.01f, t.pixelsPerUnit);
        }

        private static float PrefH(Text t, float width, string text)
        {
            var settings = t.GetGenerationSettings(new Vector2(Mathf.Max(1f, width), 0f));
            return t.cachedTextGeneratorForLayout.GetPreferredHeight(text, settings) / Mathf.Max(0.01f, t.pixelsPerUnit);
        }
    }
}
