using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Açılış yükleme ekranı (Y1–Y5, 23 Ekim 2026, kullanıcı onayı): her açılışta hikâyeyle eşleşen başka bir 3B görsel
    /// (ulaşılan bölümden, art arda aynısı gelmez), üstte ad, altta tek kısa ipucu. En az 1,2 sn görünür; oyun hazır olunca
    /// bulutlar kenarlardan gelip iki yana aralanır (sis temamız) ve ekran açılır. WebGL'de bu işi index.html yapar.
    /// </summary>
    public sealed class LoadingCover : MonoBehaviour
    {
        private const float MinShow = 1.2f, Gather = 0.45f, Part = 1f;
        private float _t, _closeAt = -1f;
        private RectTransform _left, _right;
        private CanvasGroup _group;
        private Image _fill;

        public static LoadingCover Show(Transform overlay, Theme th, Sprite art, string tip)
        {
            var root = Ui.Fill(overlay, "LoadingCover");
            root.SetAsLastSibling();
            var c = root.gameObject.AddComponent<LoadingCover>();
            c._group = root.gameObject.AddComponent<CanvasGroup>();
            var bg = root.gameObject.AddComponent<Image>(); bg.color = th.Sky;   // görsel yoksa gökyüzü
            if (art != null)
            {
                var pic = Ui.Fill(root, "Art");
                var img = pic.gameObject.AddComponent<Image>(); img.sprite = art; img.raycastTarget = false;
                var fit = pic.gameObject.AddComponent<AspectRatioFitter>();
                fit.aspectMode = AspectRatioFitter.AspectMode.EnvelopeParent; fit.aspectRatio = art.rect.width / art.rect.height;
            }
            Shade(root, true); Shade(root, false);
            Candy.Caption(root, "Pofi Adası", 96, new Vector2(0.5f, 0.9f), new Vector2(1200f, 130f), Vector2.zero, Candy.Deep(Candy.Orange));
            Candy.Caption(root, "Işık Adası'nın hikâyesi", 40, new Vector2(0.5f, 0.82f), new Vector2(1000f, 60f));
            // ince ilerleme çubuğu (açılış süresince dolar)
            var bar = Ui.Rect(root, "Bar", new Vector2(0.5f, 0.76f), new Vector2(560f, 22f));
            Ui.Panel(bar, new Color(1f, 1f, 1f, 0.55f), 11f).raycastTarget = false;
            var fill = Ui.Rect(bar, "Fill", new Vector2(0f, 0.5f), new Vector2(0f, 22f));
            fill.pivot = new Vector2(0f, 0.5f);
            c._fill = Ui.Panel(fill, Theme.Hex("#FFB21A"), 11f); c._fill.raycastTarget = false;
            if (!string.IsNullOrEmpty(tip))
            {
                var t = Candy.Banner(root, Candy.White, "ui_hand", new Vector2(0.5f, 0f), new Vector2(0f, 70f), 1100f, 36, false);
                t.SetText(tip);
            }
            c._left = Cloud(root, true); c._right = Cloud(root, false);
            return c;
        }

        /// <summary>Oyun hazır: en az 1,2 sn dolunca bulutlar aralanır ve kapak kalkar.</summary>
        public void Close() { if (_closeAt < 0f) _closeAt = Mathf.Max(_t, MinShow); }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            var fillTarget = _closeAt < 0f ? Mathf.Min(0.9f, _t / 2.5f) : 1f;
            var ft = (RectTransform)_fill.transform;
            var w = Mathf.MoveTowards(ft.sizeDelta.x / 560f, fillTarget, Time.unscaledDeltaTime * 1.5f);
            ft.sizeDelta = new Vector2(560f * w, 22f);
            if (_closeAt < 0f || _t < _closeAt) return;
            var k = _t - _closeAt;
            var W = ((RectTransform)transform).rect.width;
            if (k < Gather)
            {
                // bulutlar ortaya toplanır
                var e = Mathf.SmoothStep(0f, 1f, k / Gather);
                _left.anchoredPosition = new Vector2(Mathf.Lerp(0f, W * 0.56f, e), 0f);     // sağ kenarı ortaya gelir
                _right.anchoredPosition = new Vector2(Mathf.Lerp(0f, -W * 0.56f, e), 0f);
                return;
            }
            var p = Mathf.Clamp01((k - Gather) / Part);
            var q = 1f - Mathf.Pow(1f - p, 3f);
            _left.anchoredPosition = new Vector2(Mathf.Lerp(W * 0.56f, -W * 0.1f, q), 0f);   // iki yana aralanır
            _right.anchoredPosition = new Vector2(Mathf.Lerp(-W * 0.56f, W * 0.1f, q), 0f);
            _group.alpha = 1f - Mathf.Clamp01((k - Gather - 0.15f) / 0.5f);
            _group.blocksRaycasts = _group.alpha > 0.5f;
            if (p >= 1f) Destroy(gameObject);
        }

        private static void Shade(RectTransform root, bool top)
        {
            var s = Ui.Rect(root, top ? "ShadeTop" : "ShadeBottom", new Vector2(0.5f, top ? 1f : 0f), Vector2.zero);
            s.anchorMin = new Vector2(0f, top ? 0.62f : 0f); s.anchorMax = new Vector2(1f, top ? 1f : 0.3f); s.sizeDelta = Vector2.zero;
            var g = s.gameObject.AddComponent<RawImage>(); g.raycastTarget = false;
            g.texture = Gradient(top); g.color = new Color(0.04f, 0.16f, 0.31f, 0.5f);
        }

        private static readonly Dictionary<bool, Texture2D> Grads = new Dictionary<bool, Texture2D>();

        private static Texture2D Gradient(bool top)
        {
            if (Grads.TryGetValue(top, out var t) && t != null) return t;
            t = new Texture2D(1, 32, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            for (var y = 0; y < 32; y++) { var a = top ? y / 31f : 1f - y / 31f; t.SetPixel(0, y, new Color(1f, 1f, 1f, a * a)); }
            t.Apply();
            return Grads[top] = t;
        }

        /// <summary>Yumuşak bulut kümesi: üst üste binen beyaz daireler (ekranın yarısından geniş).</summary>
        private static RectTransform Cloud(RectTransform root, bool left)
        {
            // dış kenara yaslı, ekranın dışında başlar (anchoredPosition 0 = tam dışarıda)
            var c = Ui.Rect(root, left ? "CloudL" : "CloudR", new Vector2(left ? 0f : 1f, 0.5f), new Vector2(1500f, 1400f));
            c.pivot = new Vector2(left ? 1f : 0f, 0.5f);
            c.anchoredPosition = Vector2.zero;
            var puffs = new[] { (0.35f, 0.15f, 620f), (0.7f, 0.35f, 760f), (0.45f, 0.55f, 700f), (0.75f, 0.75f, 640f), (0.4f, 0.9f, 560f), (0.9f, 0.55f, 600f) };
            foreach (var (x, y, d) in puffs)
            {
                var p = Ui.Rect(c, "Puff", new Vector2(left ? x : 1f - x, y), new Vector2(d, d));
                var img = p.gameObject.AddComponent<Image>(); img.sprite = Ui.Rounded; img.type = Image.Type.Sliced;
                img.pixelsPerUnitMultiplier = 0.48f; img.color = new Color(1f, 1f, 1f, 0.97f); img.raycastTarget = false;
            }
            return c;
        }
    }
}
