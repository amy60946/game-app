using System;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Sol üst profil (Altın Atölye, kullanıcı onayı 22 Ekim; işleniş 1, 24 Ekim 2026): altın çerçeveli yüz madalyonu, çevresinde
    /// 4 ihtiyaç yayı (üst açlık, sağ temizlik, alt mutluluk, sol ev), köşede yıldız seviye; yanında kırmızı kurdele ad + kupa,
    /// altın kenarlı XP çubuğu ("in / gereken", parlama) ve ihtiyaç değerleri. Ada ve Evim aynı parçayı kullanır.
    /// Ayrıntı bloğu (<see cref="Detail"/>) yürürken sönebilsin diye ayrı tutulur.
    /// </summary>
    public sealed class GoldProfile
    {
        private const float G = GoldKit.K;
        public const float ArcSpan = 76f / 360f;   // her ihtiyaç bir çeyrekte 76°lik yay (taslak: 7°–83°)
        public static readonly Color[] NeedCols = { Theme.Hex("#FF8A3D"), Theme.Hex("#3FA9F5"), Theme.Hex("#FF4F8B"), Theme.Hex("#7ED957") };

        public RectTransform Ring, Detail, XpBar, Trophy;
        public CanvasGroup DetailGroup;
        public readonly Image[] Arcs = new Image[4], Glows = new Image[4];
        public readonly Text[] Values = new Text[4];
        public Text Level, Name, TrophyCount, XpText;
        public Image XpFill;

        /// <param name="needIcons">4 ihtiyacın simgeleri (yaylarla aynı sıra).</param>
        public static GoldProfile Build(RectTransform parent, string petId, string[] needIcons, Action onTap)
        {
            var p = new GoldProfile();
            var ring = Ui.Rect(parent, "Profile", new Vector2(0f, 1f), new Vector2(116f * G, 116f * G), new Vector2((20f + 58f) * G, -(12f + 58f) * G));
            p.Ring = ring;
            for (var i = 0; i < 4; i++)
            {
                var q = Ui.Fill(ring, "Need" + i);
                q.localRotation = Quaternion.Euler(0f, 0f, -(i * 90f - 38f));
                var glow = Ui.Rect(q, "Glow", new Vector2(0.5f, 0.5f), new Vector2(116f * G * 1.2f, 116f * G * 1.2f));
                p.Glows[i] = Arc(glow, new Color(1f, 0.62f, 0.2f, 0f), ArcSpan + 0.02f);
                glow.localRotation = Quaternion.Euler(0f, 0f, 3.6f);
                var track = Arc(q, new Color(1f, 1f, 1f, 0.35f), ArcSpan);
                var sh = track.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.04f, 0.12f, 0.35f, 0.4f); sh.effectDistance = new Vector2(0f, -3f);
                p.Arcs[i] = Arc(Ui.Fill(q, "Fill"), NeedCols[i], 0f);
            }
            var face = Ui.Rect(ring, "Face", new Vector2(0.5f, 0.5f), new Vector2(94f * G, 94f * G));
            var inner = GoldKit.RimDisc(face, Theme.Hex("#9EE0FF"), Theme.Hex("#3E92F2"));
            var pic = Ui.Portrait(petId);
            if (pic != null)
            {
                inner.gameObject.AddComponent<Mask>().showMaskGraphic = true;
                var pr = Ui.Rect(inner, "Pic", new Vector2(0.5f, 0.5f), new Vector2(86f * G, 86f * G), new Vector2(0f, -2f * G));
                var pi = pr.gameObject.AddComponent<Image>(); pi.sprite = pic; pi.preserveAspect = true; pi.raycastTarget = false;
            }
            var star = Ui.Rect(ring, "Star", new Vector2(1f, 0f), new Vector2(52f * G, 52f * G), new Vector2(-20f * G, 22f * G));
            var si = star.gameObject.AddComponent<Image>(); si.sprite = GoldKit.Star; si.raycastTarget = false;
            var ss = star.gameObject.AddComponent<Shadow>(); ss.effectColor = Theme.Hex("#9A5A00"); ss.effectDistance = new Vector2(0f, -2f * G);
            p.Level = Ui.Label(star, "", Mathf.RoundToInt(22f * G), Theme.Hex("#7A3E00"), new Vector2(0.5f, 0.5f), new Vector2(52f * G, 52f * G), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(0f, -3f * G));
            p.Level.raycastTarget = false;
            if (onTap != null)
            {
                var hit = ring.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
                var btn = ring.gameObject.AddComponent<Button>(); btn.targetGraphic = hit; btn.transition = Selectable.Transition.None;
                btn.onClick.AddListener(() => onTap());
            }

            // ayrıntı: ad kurdelesi + kupa, XP çubuğu, ihtiyaç değerleri
            var det = Ui.Rect(parent, "ProfileDetail", new Vector2(0f, 1f), new Vector2(330f * G, 102f * G), Vector2.zero);
            det.pivot = new Vector2(0f, 0.5f);
            det.anchoredPosition = new Vector2((20f + 116f + 12f) * G, -(12f + 58f) * G);
            p.Detail = det;
            p.DetailGroup = det.gameObject.AddComponent<CanvasGroup>();
            p.Name = GoldKit.Ribbon(det, "", GoldKit.Tone.Red, 38f * G, Mathf.RoundToInt(23f * G), new Vector2(0f, 1f), Vector2.zero, 22f * G);
            var rib = (RectTransform)p.Name.transform.parent;
            rib.pivot = new Vector2(0f, 1f); rib.anchoredPosition = Vector2.zero;
            p.Trophy = Ui.Rect(rib, "Trophy", new Vector2(1f, 0.5f), new Vector2(56f * G, 30f * G), new Vector2(-(26f + 28f) * G * 0.5f - 8f, 0f));
            var ti = Ui.IconImage(p.Trophy, "ui_trophy", new Vector2(0f, 0.5f), 26f * G, new Vector2(13f * G, 0f));
            if (ti != null) ti.GetComponent<Image>().raycastTarget = false;
            p.TrophyCount = Ui.Label(p.Trophy, "", Mathf.RoundToInt(18f * G), Color.white, new Vector2(1f, 0.5f), new Vector2(28f * G, 30f * G), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(-12f * G, 0f));
            var tcs = p.TrophyCount.gameObject.AddComponent<Shadow>(); tcs.effectColor = GoldKit.RibbonRedInk; tcs.effectDistance = new Vector2(0f, -2f * G);
            p.TrophyCount.raycastTarget = false;

            p.XpBar = Ui.Rect(det, "Xp", new Vector2(0f, 1f), new Vector2(250f * G, 28f * G));
            p.XpBar.pivot = new Vector2(0f, 1f); p.XpBar.anchoredPosition = new Vector2(0f, -(38f + 6f) * G);
            var xin = GoldKit.RimCapsule(p.XpBar, Theme.Hex("#173A9A"), Theme.Hex("#10297A"));
            xin.gameObject.AddComponent<RectMask2D>();
            var fillRt = Ui.Fill(xin, "Fill");
            fillRt.offsetMin = new Vector2(2f * G, 2f * G); fillRt.offsetMax = new Vector2(-2f * G, -2f * G);
            var fill = Ui.Fill(fillRt, "Bar");
            fill.pivot = new Vector2(0f, 0.5f);
            p.XpFill = fill.gameObject.AddComponent<Image>(); p.XpFill.raycastTarget = false;
            p.XpFill.sprite = GoldKit.Capsule(Theme.Hex("#C4F77A"), Theme.Hex("#46C23C")); p.XpFill.type = Image.Type.Sliced;
            p.XpFill.pixelsPerUnitMultiplier = 96f / Mathf.Max(1f, 28f * G - 4f * G - 4f * G);
            var shine = Ui.Rect(xin, "Shine", new Vector2(0f, 0.5f), new Vector2(40f * G, 28f * G));   // parlama süpürmesi (taslak .shine)
            var shi = shine.gameObject.AddComponent<Image>(); shi.sprite = GoldKit.Capsule(new Color(1f, 1f, 1f, 0.5f), new Color(1f, 1f, 1f, 0.15f)); shi.raycastTarget = false;
            shine.gameObject.AddComponent<ShineSweep>();
            p.XpText = Ui.Label(p.XpBar, "", Mathf.RoundToInt(15f * G), Color.white, new Vector2(0.5f, 0.5f), new Vector2(250f * G, 28f * G), FontStyle.Bold);
            var xs = p.XpText.gameObject.AddComponent<Shadow>(); xs.effectColor = Theme.Hex("#18389A"); xs.effectDistance = new Vector2(0f, -2f * G);
            p.XpText.raycastTarget = false;

            for (var i = 0; i < 4; i++)
            {
                var cell = Ui.Rect(det, "Need" + i, new Vector2(0f, 1f), new Vector2(60f * G, 24f * G));
                cell.pivot = new Vector2(0f, 1f); cell.anchoredPosition = new Vector2(i * 62f * G, -(38f + 6f + 28f + 6f) * G);
                Ui.IconImage(cell, needIcons[i], new Vector2(0f, 0.5f), 24f * G, new Vector2(12f * G, 0f));
                p.Values[i] = Ui.Label(cell, "", Mathf.RoundToInt(15f * G), Color.white, new Vector2(0f, 0.5f), new Vector2(34f * G, 24f * G), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2((26f + 17f) * G, 0f));
                var ns = p.Values[i].gameObject.AddComponent<Outline>(); ns.effectColor = new Color(0.04f, 0.12f, 0.35f, 0.7f); ns.effectDistance = new Vector2(2f, -2f);
                p.Values[i].raycastTarget = false;
            }
            return p;
        }

        private static Image Arc(RectTransform rt, Color c, float fill)
        {
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = GoldKit.Annulus; img.color = c; img.raycastTarget = false;
            img.type = Image.Type.Filled; img.fillMethod = Image.FillMethod.Radial360; img.fillOrigin = (int)Image.Origin360.Top; img.fillClockwise = true;
            img.fillAmount = fill;
            return img;
        }

        /// <summary>İhtiyaç değeri (0–100): yay dolar, değer yazılır; artınca yay zıplar.</summary>
        public void SetNeed(int i, float value)
        {
            var f = Mathf.Clamp(value, 0f, 100f) / 100f * ArcSpan;
            if (f > Arcs[i].fillAmount + 0.02f * ArcSpan) Bump.Play(Arcs[i].transform.parent, 0.12f);
            Arcs[i].fillAmount = f;
            Values[i].text = Mathf.RoundToInt(value).ToString();
        }

        /// <summary>Ad kurdelesi: ad + (rozet varsa) kupa ve sayısı; değişince kurdele yazıya uyar.</summary>
        public void SetName(string name, int badges)
        {
            var nb = badges.ToString();
            if (Name.text == name && TrophyCount.text == nb) return;
            Name.text = name;
            TrophyCount.text = nb;
            Trophy.gameObject.SetActive(badges > 0);
            var rib = (RectTransform)Name.transform.parent;
            var pad = 22f * G;
            var extra = badges > 0 ? 62f * G : 0f;
            rib.sizeDelta = new Vector2(Name.preferredWidth + pad * 2f + extra, rib.sizeDelta.y);
            ((RectTransform)Name.transform).anchoredPosition = new Vector2(-extra * 0.5f, 0.04f * rib.sizeDelta.y);
        }

        /// <summary>XP çubuğu ve "in / gereken" (son seviyede <paramref name="maxText"/>).</summary>
        public void SetXp(Logic.Progression.LevelTable levels, int totalXp, int level, string maxText)
        {
            Level.text = level.ToString();
            var lv = levels.LevelFor(totalXp);
            Ui.SetBar(XpFill, levels.ProgressInLevel(totalXp));
            if (lv >= levels.MaxLevel) { XpText.text = maxText; return; }
            var start = levels.TotalXpFor(lv);
            XpText.text = (totalXp - start) + " / " + (levels.TotalXpFor(lv + 1) - start);
        }
    }
}
