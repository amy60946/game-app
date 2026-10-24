using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// "Altın Atölye" gösterge takımı (E + G, kullanıcı onayı 22 Ekim 2026; 3B işleniş 1 "kalın simge", 24 Ekim 2026).
    /// Kaynak: Pofi Gösterge Seçenekleri sayfasının en üstündeki taslak (1280×720; burada ×1,5 = tuval birimi).
    /// Hepsi kodla çizilir (görsel dosyası yok): altın kenarlı kapsül/disk, uçları çentikli kurdele, yıldız rozet, kırmızı elmas sayı,
    /// çeyrek halka ve çerçevesiz 3B simge düğme (simgenin altında kendi renginde kalınlık + yerde gölge, hafif süzülme).
    /// </summary>
    public static class GoldKit
    {
        public const float K = 1.5f;   // taslak pikseli → tuval birimi

        private static readonly (float T, Color C)[] GoldStops =
        {
            (0f, Theme.Hex("#FFF6C2")), (0.38f, Theme.Hex("#F5BC3A")), (0.64f, Theme.Hex("#B8751A")), (0.88f, Theme.Hex("#FFE48C")), (1f, Theme.Hex("#FFE48C")),
        };

        public static readonly Color RibbonBlueTop = Theme.Hex("#4A86FF"), RibbonBlueBot = Theme.Hex("#1C49CC"), RibbonBlueInk = Theme.Hex("#102E86");
        public static readonly Color RibbonRedTop = Theme.Hex("#FF7373"), RibbonRedBot = Theme.Hex("#D72E46"), RibbonRedInk = Theme.Hex("#8E1426");
        public static readonly Color RibbonGreenTop = Theme.Hex("#7EDD6A"), RibbonGreenBot = Theme.Hex("#2A9E44"), RibbonGreenInk = Theme.Hex("#17652A");
        public static readonly Color CreamTop = Theme.Hex("#FFF7E0"), CreamBot = Theme.Hex("#F2D79A"), CreamInk = Theme.Hex("#6B3F0E");

        public enum Tone { Blue, Red, Green, Cream }

        private static readonly Dictionary<string, Sprite> Cache = new Dictionary<string, Sprite>();

        // ------------------------------------------------------------------ çizim yardımcıları

        private static Color Grad((float T, Color C)[] stops, float t)
        {
            t = Mathf.Clamp01(t);
            for (var i = 1; i < stops.Length; i++)
                if (t <= stops[i].T) return Color.Lerp(stops[i - 1].C, stops[i].C, Mathf.InverseLerp(stops[i - 1].T, stops[i].T, t));
            return stops[stops.Length - 1].C;
        }

        /// <summary>Doku üretir: inside(x, y) 0..1 kaplama (4×4 örnek), color(x, y) renk; y yukarı doğru (0 alt).</summary>
        private static Sprite Make(string key, int w, int h, Func<float, float, bool> inside, Func<float, float, Color> color, Vector4 border)
        {
            if (Cache.TryGetValue(key, out var s) && s != null) return s;
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "gold_" + key };
            var px = new Color[w * h];
            for (var y = 0; y < h; y++)
            for (var x = 0; x < w; x++)
            {
                var n = 0;
                for (var sy = 0; sy < 4; sy++)
                for (var sx = 0; sx < 4; sx++)
                    if (inside(x + (sx + 0.5f) / 4f, y + (sy + 0.5f) / 4f)) n++;
                var c = n > 0 ? color(x + 0.5f, y + 0.5f) : Color.clear;
                c.a *= n / 16f;
                px[y * w + x] = c;
            }
            tex.SetPixels(px);
            tex.Apply(false, true);
            s = Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, border);
            Cache[key] = s;
            return s;
        }

        private static bool InCapsule(float x, float y, float w, float h)
        {
            var r = h * 0.5f;
            var cx = Mathf.Clamp(x, r, w - r);
            var dx = x - cx; var dy = y - r;
            return dx * dx + dy * dy <= r * r;
        }

        /// <summary>Yatay kapsül (uçlar yarım daire), dikey geçiş üstten alta. 9 dilimli: yalnız yatay uzar.</summary>
        public static Sprite Capsule(Color top, Color bottom) =>
            Make("cap" + ColorUtility.ToHtmlStringRGBA(top) + ColorUtility.ToHtmlStringRGBA(bottom), 192, 96,
                (x, y) => InCapsule(x, y, 192f, 96f), (x, y) => Color.Lerp(bottom, top, y / 96f), new Vector4(47, 0, 47, 0));

        /// <summary>Altın kenar kapsülü (160° altın geçiş: açık → koyu → açık).</summary>
        public static Sprite GoldCapsule => Make("goldcap", 192, 96, (x, y) => InCapsule(x, y, 192f, 96f),
            (x, y) => Grad(GoldStops, 1f - y / 96f + (x / 192f - 0.5f) * 0.25f), new Vector4(47, 0, 47, 0));

        public static Sprite Disc(Color top, Color bottom) =>
            Make("disc" + ColorUtility.ToHtmlStringRGBA(top) + ColorUtility.ToHtmlStringRGBA(bottom), 128, 128,
                (x, y) => (x - 64f) * (x - 64f) + (y - 64f) * (y - 64f) <= 64f * 64f, (x, y) => Color.Lerp(bottom, top, y / 128f), Vector4.zero);

        public static Sprite GoldDisc => Make("golddisc", 128, 128, (x, y) => (x - 64f) * (x - 64f) + (y - 64f) * (y - 64f) <= 64f * 64f,
            (x, y) => Grad(GoldStops, 1f - y / 128f + (x / 128f - 0.5f) * 0.3f), Vector4.zero);

        /// <summary>Uçları içe çentikli kurdele (taslaktaki clip-path: %5 çentik). 9 dilimli: orta bant uzar.</summary>
        public static Sprite RibbonSprite(Color top, Color bottom) =>
            Make("rib" + ColorUtility.ToHtmlStringRGBA(top) + ColorUtility.ToHtmlStringRGBA(bottom), 256, 64,
                (x, y) =>
                {
                    var notch = 15f * (1f - Mathf.Abs(y - 32f) / 32f);
                    return x >= notch && x <= 256f - notch;
                },
                (x, y) => Color.Lerp(bottom, top, y / 64f), new Vector4(26, 0, 26, 0));

        /// <summary>Halka (çeyrek ihtiyaç yayları için Filled/Radial360); iç yarıçap 49/58 (taslak).</summary>
        public static Sprite Annulus => Make("ring", 256, 256, (x, y) =>
        {
            var d = Mathf.Sqrt((x - 128f) * (x - 128f) + (y - 128f) * (y - 128f));
            return d <= 127f && d >= 127f * 49f / 58f;
        }, (x, y) => Color.white, Vector4.zero);

        /// <summary>Beş köşeli yıldız (seviye rozeti), sarıdan turuncuya.</summary>
        public static Sprite Star => Make("star", 128, 128, (x, y) => InPoly(x / 128f, 1f - y / 128f, StarPts),
            (x, y) => Color.Lerp(Theme.Hex("#F2A81C"), Theme.Hex("#FFF3A8"), y / 128f), Vector4.zero);

        private static readonly Vector2[] StarPts =
        {
            new Vector2(.5f, 0f), new Vector2(.63f, .33f), new Vector2(.98f, .35f), new Vector2(.71f, .57f), new Vector2(.8f, .92f),
            new Vector2(.5f, .73f), new Vector2(.2f, .92f), new Vector2(.29f, .57f), new Vector2(.02f, .35f), new Vector2(.37f, .33f),
        };

        /// <summary>Parıltı (dört köşeli yıldız), krem.</summary>
        public static Sprite Twinkle => Make("twinkle", 64, 64, (x, y) => InPoly(x / 64f, 1f - y / 64f, TwinklePts), (x, y) => Theme.Hex("#FFF7C8"), Vector4.zero);

        private static readonly Vector2[] TwinklePts =
        {
            new Vector2(.5f, 0f), new Vector2(.6f, .4f), new Vector2(1f, .5f), new Vector2(.6f, .6f),
            new Vector2(.5f, 1f), new Vector2(.4f, .6f), new Vector2(0f, .5f), new Vector2(.4f, .4f),
        };

        private static bool InPoly(float x, float y, Vector2[] p)
        {
            var c = false;
            for (int i = 0, j = p.Length - 1; i < p.Length; j = i++)
                if ((p[i].y > y) != (p[j].y > y) && x < (p[j].x - p[i].x) * (y - p[i].y) / (p[j].y - p[i].y) + p[i].x) c = !c;
            return c;
        }

        /// <summary>Kırmızı elmas sayı rozeti: 45° dönük yuvarlak kare, krem kenar.</summary>
        public static Sprite GemSprite => Make("gem", 96, 96, (x, y) => InRoundSquare(Rot(x, y), 30f, 9f),
            (x, y) =>
            {
                var q = Rot(x, y);
                var inner = InRoundSquare(q, 25.5f, 6f);
                return inner ? Color.Lerp(Theme.Hex("#D0123B"), Theme.Hex("#FF6D8A"), y / 96f) : Theme.Hex("#FFF3C4");
            }, Vector4.zero);

        private static Vector2 Rot(float x, float y)
        {
            var dx = x - 48f; var dy = y - 48f;
            const float c = 0.70710678f;
            return new Vector2(dx * c + dy * c, -dx * c + dy * c);
        }

        private static bool InRoundSquare(Vector2 p, float half, float r)
        {
            var qx = Mathf.Abs(p.x) - (half - r); var qy = Mathf.Abs(p.y) - (half - r);
            var ox = Mathf.Max(qx, 0f); var oy = Mathf.Max(qy, 0f);
            return Mathf.Sqrt(ox * ox + oy * oy) + Mathf.Min(Mathf.Max(qx, qy), 0f) <= r;
        }

        /// <summary>Yerdeki yumuşak gölge (elips, ortası koyu).</summary>
        public static Sprite GroundShadow => Make("shade", 128, 32, (x, y) =>
        {
            var dx = (x - 64f) / 64f; var dy = (y - 16f) / 16f;
            return dx * dx + dy * dy <= 1f;
        }, (x, y) =>
        {
            var dx = (x - 64f) / 64f; var dy = (y - 16f) / 16f;
            var d = Mathf.Sqrt(dx * dx + dy * dy);
            return new Color(0.04f, 0.08f, 0.16f, 0.42f * Mathf.Clamp01(1f - d / 0.7f + 0.15f) * Mathf.Clamp01((1f - d) * 3f));
        }, Vector4.zero);

        // ------------------------------------------------------------------ yapı taşları

        private static Image Img(Transform parent, string name, Sprite sp, bool sliced, float height = 0f)
        {
            var rt = Ui.Fill(parent, name);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sp; img.raycastTarget = false;
            if (sliced)
            {
                img.type = Image.Type.Sliced;
                if (height > 0f) img.pixelsPerUnitMultiplier = sp.rect.height / height;   // uçlar yüksekliğe göre (elips olmasın)
            }
            return img;
        }

        /// <summary>Altın kenarlı kapsül: dışta altın, içte verilen geçiş (kenar = 4 taslak pikseli). İç dikdörtgeni döndürür.</summary>
        public static RectTransform RimCapsule(RectTransform rt, Color top, Color bottom, float rim = 4f * K)
        {
            var h = rt.sizeDelta.y;
            Img(rt, "Gold", GoldCapsule, true, h);
            var inner = Ui.Fill(rt, "In");
            inner.offsetMin = new Vector2(rim, rim); inner.offsetMax = new Vector2(-rim, -rim);
            var ii = inner.gameObject.AddComponent<Image>(); ii.raycastTarget = false;
            ii.sprite = Capsule(top, bottom); ii.type = Image.Type.Sliced; ii.pixelsPerUnitMultiplier = 96f / Mathf.Max(1f, h - rim * 2f);
            var sh = rt.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.05f, 0.11f, 0.31f, 0.3f); sh.effectDistance = new Vector2(0f, -6f * K);
            return inner;
        }

        /// <summary>Altın kenarlı disk (madalyon yüzü): iç geçiş açık mavi → mavi. İç dikdörtgeni döndürür.</summary>
        public static RectTransform RimDisc(RectTransform rt, Color top, Color bottom, float rim = 3f * K)
        {
            Img(rt, "Gold", GoldDisc, false);
            var inner = Ui.Fill(rt, "In");
            inner.offsetMin = new Vector2(rim, rim); inner.offsetMax = new Vector2(-rim, -rim);
            var ii = inner.gameObject.AddComponent<Image>(); ii.sprite = Disc(top, bottom); ii.raycastTarget = false;
            var sh = rt.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.05f, 0.11f, 0.31f, 0.35f); sh.effectDistance = new Vector2(0f, -6f * K);
            return inner;
        }

        private static (Color Top, Color Bot, Color Ink) ToneColors(Tone t)
        {
            switch (t)
            {
                case Tone.Red: return (RibbonRedTop, RibbonRedBot, RibbonRedInk);
                case Tone.Green: return (RibbonGreenTop, RibbonGreenBot, RibbonGreenInk);
                case Tone.Cream: return (CreamTop, CreamBot, CreamInk);
                default: return (RibbonBlueTop, RibbonBlueBot, RibbonBlueInk);
            }
        }

        /// <summary>
        /// Kurdele etiket: uçları çentikli bant, ortada beyaz (kremde kahverengi) yazı + koyu alt gölge. Genişlik yazıya göre.
        /// <paramref name="anchor"/> ebeveyn içindeki çapa; yazıyı döndürür.
        /// </summary>
        public static Text Ribbon(Transform parent, string text, Tone tone, float height, int fontSize, Vector2 anchor, Vector2 offset, float pad = 0f)
        {
            var (top, bot, ink) = ToneColors(tone);
            var rt = Ui.Rect(parent, "Ribbon", anchor, new Vector2(200f, height), offset);
            var img = rt.gameObject.AddComponent<Image>();
            var sp = RibbonSprite(top, bot);
            img.sprite = sp; img.type = Image.Type.Sliced; img.pixelsPerUnitMultiplier = sp.rect.height / height; img.raycastTarget = false;
            var t = Ui.Label(rt, text, fontSize, tone == Tone.Cream ? ink : Color.white, new Vector2(0.5f, 0.5f), new Vector2(1600f, height), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(0f, height * 0.04f));
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.raycastTarget = false;
            if (tone != Tone.Cream) { var s = t.gameObject.AddComponent<Shadow>(); s.effectColor = ink; s.effectDistance = new Vector2(0f, -2f * K); }
            if (pad <= 0f) pad = height * 0.62f;
            FitRibbon(t, pad);
            return t;
        }

        /// <summary>Kurdele genişliğini yazıya uydurur (yazı değişince çağır).</summary>
        public static void FitRibbon(Text t, float pad = -1f)
        {
            var rt = (RectTransform)t.transform.parent;
            if (pad < 0f) pad = rt.sizeDelta.y * 0.62f;
            rt.sizeDelta = new Vector2(Mathf.Max(rt.sizeDelta.y * 1.6f, t.preferredWidth + pad * 2f), rt.sizeDelta.y);
        }

        /// <summary>Kırmızı elmas sayı (düğmenin sağ üstü). Yazıyı döndürür; rozeti gizlemek için ebeveynini kapat.</summary>
        public static Text Gem(Transform parent, float size = 34f * K)
        {
            var rt = Ui.Rect(parent, "Gem", new Vector2(1f, 1f), new Vector2(size, size), new Vector2(-size * 0.18f, -size * 0.2f));
            var img = rt.gameObject.AddComponent<Image>(); img.sprite = GemSprite; img.raycastTarget = false;
            var sh = rt.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0f, 0f, 0f, 0.3f); sh.effectDistance = new Vector2(0f, -2f * K);
            var t = Ui.Label(rt, "", Mathf.RoundToInt(size * 0.56f), Color.white, new Vector2(0.5f, 0.5f), new Vector2(size, size), FontStyle.Bold);
            var ts = t.gameObject.AddComponent<Shadow>(); ts.effectColor = Theme.Hex("#7A0A20"); ts.effectDistance = new Vector2(0f, -1.5f * K);
            t.raycastTarget = false;
            return t;
        }

        /// <summary>Çerçevesiz 3B simge düğme (taslaktaki .b3, işleniş 1). Dönen değerler: düğme, simge resmi, etiket yazısı (yoksa null).</summary>
        public static (Button Btn, Image Icon, Text Label) Icon3D(Transform parent, string icon, float size, Vector2 anchor, Vector2 offset,
            Color extrude, Action onClick, string label = null, Tone labelTone = Tone.Blue, float delay = 0f)
        {
            var rt = Ui.Rect(parent, "B3 " + (label ?? icon), anchor, new Vector2(size, size), offset);
            var hit = rt.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            // yerde gölge (simgenin altında, süzülünce küçülür)
            var shade = Ui.Rect(rt, "Shade", new Vector2(0.5f, 0f), new Vector2(size * 0.68f, size * 0.17f), new Vector2(0f, -size * 0.06f));
            var si = shade.gameObject.AddComponent<Image>(); si.sprite = GroundShadow; si.raycastTarget = false;
            var ir = Ui.Fill(rt, "Icon");
            var img = ir.gameObject.AddComponent<Image>(); img.preserveAspect = true; img.raycastTarget = false;
            var sp = Ui.Icon(icon);
            if (sp != null) img.sprite = sp; else img.color = new Color(1f, 1f, 1f, 0f);
            var ex = ir.gameObject.AddComponent<Extrude>(); ex.Color = extrude; ex.Depth = Mathf.Max(6f, size * 0.07f);
            var fl = ir.gameObject.AddComponent<Hover3D>(); fl.Shade = shade; fl.Delay = delay; fl.Amp = Mathf.Max(4f, size * 0.045f);
            Text lab = null;
            if (!string.IsNullOrEmpty(label))
            {
                var h = Mathf.Clamp(size * 0.3f, 34f, 48f);
                lab = Ribbon(rt, label, labelTone, h, Mathf.RoundToInt(h * 0.6f), new Vector2(0.5f, 0f), new Vector2(0f, -h * 0.12f));
                lab.transform.parent.SetAsLastSibling();
            }
            var btn = rt.gameObject.AddComponent<Button>();
            btn.targetGraphic = img; btn.transition = Selectable.Transition.None;
            btn.onClick.AddListener(() => Audio.Sfx.Play(Audio.SfxKind.Tap));
            if (onClick != null) btn.onClick.AddListener(() => onClick());
            rt.gameObject.AddComponent<PressBounce>();
            return (btn, img, lab);
        }

        /// <summary>Simgeyi değiştir (eylem düğmesi): kalınlık aynı kalır.</summary>
        public static void SetIcon(Image img, string icon)
        {
            var sp = Ui.Icon(icon);
            if (sp == null || img == null) return;
            img.sprite = sp; img.color = Color.white;
        }

        /// <summary>Küçük parıltı (para hapı üstünde, taslaktaki .tw): belirip dönerek söner, döngüde.</summary>
        public static void Sparkle(Transform parent, Vector2 anchor, Vector2 offset, float size, float delay)
        {
            var rt = Ui.Rect(parent, "Twinkle", anchor, new Vector2(size, size), offset);
            var img = rt.gameObject.AddComponent<Image>(); img.sprite = Twinkle; img.raycastTarget = false;
            var tw = rt.gameObject.AddComponent<TwinkleFx>(); tw.Delay = delay;
        }
    }

    /// <summary>Simgenin altında kendi renginde kalınlık (taslak: drop-shadow 0 6px 0 renk) + üstte ince açık kenar.</summary>
    [RequireComponent(typeof(Graphic))]
    public sealed class Extrude : BaseMeshEffect
    {
        public Color Color = new Color(0.48f, 0.29f, 0.07f, 1f);
        public float Depth = 9f;
        private static readonly List<UIVertex> Src = new List<UIVertex>();
        private static readonly List<UIVertex> Out = new List<UIVertex>();

        public override void ModifyMesh(VertexHelper vh)
        {
            if (!IsActive()) return;
            Src.Clear(); vh.GetUIVertexStream(Src);
            Out.Clear();
            // üst açık kenar (beyaz %70, 1,5 birim yukarı)
            Copy(new Vector2(0f, 1.5f), new Color(1f, 1f, 1f, 0.55f), true);
            // kalınlık: 1,5 birim aralıklı kopyalar, en alttaki biraz daha koyu
            var steps = Mathf.Max(2, Mathf.RoundToInt(Depth / 1.5f));
            for (var k = steps; k >= 1; k--)
            {
                var c = Color.Lerp(Color, Color * 0.82f, k / (float)steps); c.a = 1f;
                Copy(new Vector2(0f, -Depth * k / steps), c, false);
            }
            Out.AddRange(Src);
            vh.Clear(); vh.AddUIVertexTriangleStream(Out);
        }

        private void Copy(Vector2 d, Color tint, bool whiten)
        {
            foreach (var v0 in Src)
            {
                var v = v0;
                v.position += (Vector3)d;
                var a = v.color.a / 255f * tint.a;
                // dokunun rengi yerine düz renk: aynı doku, renk çarpanı; açık kenar için beyaza yakın
                v.color = whiten ? new Color32(255, 255, 255, (byte)(a * 255f)) : (Color32)new Color(tint.r, tint.g, tint.b, a);
                Out.Add(v);
            }
        }
    }

    /// <summary>Süzülme (taslak: 3,4 sn, ±5 px) ve altındaki gölgenin nefes alması.</summary>
    public sealed class Hover3D : MonoBehaviour
    {
        public RectTransform Shade;
        public float Delay, Amp = 7f;
        private Vector2 _base;
        private bool _init;

        private void Update()
        {
            var rt = (RectTransform)transform;
            if (!_init) { _base = rt.anchoredPosition; _init = true; }
            if (Theme.ReduceMotion) { rt.anchoredPosition = _base; return; }
            var s = Mathf.Sin((Time.unscaledTime + Delay) * Mathf.PI * 2f / 3.4f);
            var up = (s * 0.5f + 0.5f);
            rt.anchoredPosition = _base + new Vector2(0f, up * Amp);
            if (Shade != null) { var k = 1f - 0.18f * up; Shade.localScale = new Vector3(k, k, 1f); }
        }
    }

    /// <summary>Parlama süpürmesi (taslak .shine): 3,2 sn'de bir soldan sağa geçen açık şerit; ebeveynin genişliğinde.</summary>
    public sealed class ShineSweep : MonoBehaviour
    {
        private void Update()
        {
            var rt = (RectTransform)transform;
            var parent = rt.parent as RectTransform;
            if (parent == null) return;
            var w = parent.rect.width;
            var t = Theme.ReduceMotion ? 2f : Mathf.Repeat(Time.unscaledTime, 3.2f) / 3.2f;
            var k = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(t / 0.6f));
            rt.anchoredPosition = new Vector2(Mathf.Lerp(-rt.sizeDelta.x, w + rt.sizeDelta.x, k), 0f);
            rt.gameObject.GetComponent<Image>().enabled = t < 0.6f;
        }
    }

    /// <summary>Parıltı döngüsü: 2,2 sn'de bir büyüyüp dönerek söner.</summary>
    public sealed class TwinkleFx : MonoBehaviour
    {
        public float Delay;

        private void Update()
        {
            var t = Mathf.Repeat(Time.unscaledTime + Delay, 2.2f) / 2.2f;
            var k = Theme.ReduceMotion ? 0.6f : Mathf.Sin(t * Mathf.PI);
            transform.localScale = new Vector3(k, k, 1f);
            transform.localRotation = Quaternion.Euler(0f, 0f, -45f * t);
        }
    }
}
