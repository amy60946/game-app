using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Büyük pencere ve bölüm parçaları (Görevler penceresi C + D, 24 Ekim 2026; taslak: Ev Görevleri seçenekleri sayfası).
    /// Altın Atölye diliyle aynı renkler: altın çerçeveli krem pencere, dikey geçişli yuvarlak panel, yumuşak altın ışıma.
    /// Hepsi kodla çizilir; ölçüler tuval birimi (taslak pikseli × <see cref="GoldKit.K"/>).
    /// </summary>
    public static class PanelKit
    {
        private static readonly (float T, Color C)[] GoldStops =
        {
            (0f, Theme.Hex("#FFF6C2")), (0.38f, Theme.Hex("#F5BC3A")), (0.64f, Theme.Hex("#B8751A")), (0.88f, Theme.Hex("#FFE48C")), (1f, Theme.Hex("#FFE48C")),
        };

        private const int FrameR = 48;   // altın çerçeve dokusunun köşe yarıçapı (px)
        private const int GlowR = 44;    // ışıma dokusunun yayılma payı (px)
        private static Sprite _frame, _glow;

        private static Color Grad(float t)
        {
            t = Mathf.Clamp01(t);
            for (var i = 1; i < GoldStops.Length; i++)
                if (t <= GoldStops[i].T) return Color.Lerp(GoldStops[i - 1].C, GoldStops[i].C, Mathf.InverseLerp(GoldStops[i - 1].T, GoldStops[i].T, t));
            return GoldStops[GoldStops.Length - 1].C;
        }

        /// <summary>Altın geçişli yuvarlak köşeli dikdörtgen (9 dilimli): üst açık, yanlar koyulaşan altın, alt yine açık.</summary>
        public static Sprite GoldFrame
        {
            get
            {
                if (_frame != null) return _frame;
                const int n = 128;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "panel_gold" };
                var px = new Color[n * n];
                for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var cx = Mathf.Clamp(x + 0.5f, FrameR, n - FrameR);
                    var cy = Mathf.Clamp(y + 0.5f, FrameR, n - FrameR);
                    var d = Mathf.Sqrt((x + 0.5f - cx) * (x + 0.5f - cx) + (y + 0.5f - cy) * (y + 0.5f - cy));
                    var c = Grad(1f - (y + 0.5f) / n + ((x + 0.5f) / n - 0.5f) * 0.25f);
                    c.a = Mathf.Clamp01(FrameR - d + 0.5f);
                    px[y * n + x] = c;
                }
                tex.SetPixels(px);
                tex.Apply(false, true);
                _frame = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, new Vector4(FrameR, FrameR, FrameR, FrameR));
                return _frame;
            }
        }

        /// <summary>Yumuşak ışıma (beyaz; renk Image.color ile): ortası dolu, kenarlara doğru söner. 9 dilimli.</summary>
        public static Sprite Glow
        {
            get
            {
                if (_glow != null) return _glow;
                const int n = GlowR * 2 + 8;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "panel_glow" };
                var px = new Color[n * n];
                for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var dx = Mathf.Max(0f, Mathf.Max(GlowR - (x + 0.5f), x + 0.5f - (n - GlowR)));
                    var dy = Mathf.Max(0f, Mathf.Max(GlowR - (y + 0.5f), y + 0.5f - (n - GlowR)));
                    var k = Mathf.Clamp01(1f - Mathf.Sqrt(dx * dx + dy * dy) / GlowR);
                    px[y * n + x] = new Color(1f, 1f, 1f, k * k * (3f - 2f * k));
                }
                tex.SetPixels(px);
                tex.Apply(false, true);
                _glow = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, new Vector4(GlowR, GlowR, GlowR, GlowR));
                return _glow;
            }
        }

        /// <summary>Altın çerçeve resmi (köşe yarıçapı <paramref name="radius"/> tuval birimi).</summary>
        public static Image GoldRim(RectTransform rt, float radius)
        {
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = GoldFrame; img.type = Image.Type.Sliced; img.raycastTarget = false;
            img.pixelsPerUnitMultiplier = FrameR / Mathf.Max(4f, radius);
            return img;
        }

        /// <summary>Yuvarlak köşeli panel, üstten alta renk geçişi (taslaktaki linear-gradient).</summary>
        public static Image Grad(RectTransform rt, Color top, Color bottom, float radius)
        {
            var img = Ui.Panel(rt, Color.white, radius);
            img.raycastTarget = false;
            var g = rt.gameObject.AddComponent<VGradient>();
            g.Top = top; g.Bottom = bottom;
            return img;
        }

        /// <summary>Düz renk panel (dokunma almaz).</summary>
        public static Image Flat(RectTransform rt, Color c, float radius)
        {
            var img = Ui.Panel(rt, c, radius);
            img.raycastTarget = false;
            return img;
        }

        /// <summary>
        /// "Dudaklı" kabarık parça (taslak: inset 0 -4px 0 koyu ton): altta koyu şerit, üstünde geçişli yüz. Yüzü döndürür.
        /// </summary>
        public static RectTransform Lipped(RectTransform rt, Color top, Color bottom, Color lip, float radius, float lipH)
        {
            Flat(rt, lip, radius);
            var face = Ui.Fill(rt, "Face");
            face.offsetMin = new Vector2(0f, lipH);
            Grad(face, top, bottom, radius);
            return face;
        }

        /// <summary>
        /// Çerçeveli bölüm: dışta <paramref name="rim"/> renginde ince kenar, içte geçiş. İsteğe bağlı dış ışıma (<paramref name="glow"/>).
        /// İç dikdörtgeni döndürür.
        /// </summary>
        public static RectTransform Section(RectTransform rt, Color top, Color bottom, Color rim, float radius, float rimW, Color? glow = null, float glowW = 0f)
        {
            if (glow.HasValue && glowW > 0f)
            {
                var g = Ui.Fill(rt, "Glow");
                g.offsetMin = new Vector2(-glowW, -glowW); g.offsetMax = new Vector2(glowW, glowW);
                var gi = g.gameObject.AddComponent<Image>();
                gi.sprite = Glow; gi.type = Image.Type.Sliced; gi.color = glow.Value; gi.raycastTarget = false;
                gi.pixelsPerUnitMultiplier = GlowR / glowW;
            }
            var edge = Ui.Fill(rt, "Rim");
            Flat(edge, rim, radius);
            var body = Ui.Fill(rt, "Body");
            body.offsetMin = new Vector2(rimW, rimW); body.offsetMax = new Vector2(-rimW, -rimW);
            Grad(body, top, bottom, Mathf.Max(4f, radius - rimW));
            return body;
        }

        /// <summary>Sırası değişmeyen yatay "hap" dizisi (ilerleme noktaları). Dolu olanlar altın, yarı dolu açık altın, boşlar tan.</summary>
        public static RectTransform Pips(Transform parent, int total, int full, int soft, float pipW, float pipH, float gap, Vector2 anchor, Vector2 pivot, Vector2 offset)
        {
            total = Mathf.Max(1, total);
            var w = total * pipW + (total - 1) * gap;
            var rt = Ui.Rect(parent, "Pips", anchor, new Vector2(w, pipH), offset);
            rt.pivot = pivot;
            for (var i = 0; i < total; i++)
            {
                var p = Ui.Rect(rt, "Pip" + i, new Vector2(0f, 0.5f), new Vector2(pipW, pipH), new Vector2(pipW * 0.5f + i * (pipW + gap), 0f));
                var r = Mathf.Min(pipH, pipW) * 0.42f;
                if (i < full) Grad(p, Theme.Hex("#FFF0A0"), Theme.Hex("#F2A81C"), r);
                else if (i < full + soft) Grad(p, Theme.Hex("#FFF8D2"), Theme.Hex("#FFD45C"), r);
                else Flat(p, Theme.Hex("#E3CB92"), r);
            }
            return rt;
        }
    }

    /// <summary>Dikey renk geçişi: köşe renkleri yükseklik oranına göre (çarpılarak) boyanır. 9 dilimli panelde doğrusal kalır.</summary>
    [RequireComponent(typeof(Graphic))]
    public sealed class VGradient : BaseMeshEffect
    {
        public Color Top = Color.white, Bottom = Color.white;

        public override void ModifyMesh(VertexHelper vh)
        {
            if (!IsActive() || vh.currentVertCount == 0) return;
            var r = graphic.rectTransform.rect;
            var v = new UIVertex();
            for (var i = 0; i < vh.currentVertCount; i++)
            {
                vh.PopulateUIVertex(ref v, i);
                var t = Mathf.InverseLerp(r.yMin, r.yMax, v.position.y);
                var c = Color.Lerp(Bottom, Top, t) * (Color)v.color;
                v.color = c;
                vh.SetUIVertex(v, i);
            }
        }
    }

    /// <summary>Hafif nabız (görev kartında şu anki adım): 1,6 sn'de bir %8 büyüyüp küçülür.</summary>
    public sealed class SoftPulse : MonoBehaviour
    {
        public float Amount = 0.08f;
        private float _phase;
        private void Awake() => _phase = Random.value * 1.6f;
        private void Update()
        {
            var k = Theme.ReduceMotion ? 1f : 1f + Amount * (0.5f + 0.5f * Mathf.Sin((Time.unscaledTime + _phase) * Mathf.PI * 2f / 1.6f));
            transform.localScale = new Vector3(k, k, 1f);
        }
    }

    /// <summary>Kanat çırpar gibi süzülme (taslak .fly: 1,6 sn, sağa-yukarı kayıp ±6° döner). Mavi mektubu götürürken.</summary>
    public sealed class FlapFloat : MonoBehaviour
    {
        public Vector2 Swing = new Vector2(21f, 12f);
        public float Tilt = 6f;
        private Vector2 _base;
        private bool _init;

        private void Update()
        {
            var rt = (RectTransform)transform;
            if (!_init) { _base = rt.anchoredPosition; _init = true; }
            if (Theme.ReduceMotion) { rt.anchoredPosition = _base; rt.localRotation = Quaternion.identity; return; }
            var s = 0.5f - 0.5f * Mathf.Cos(Time.unscaledTime * Mathf.PI * 2f / 1.6f);   // 0 → 1 → 0
            rt.anchoredPosition = _base + new Vector2(Swing.x * s, Swing.y * s);
            rt.localRotation = Quaternion.Euler(0f, 0f, Mathf.Lerp(Tilt, -Tilt, s));      // uGUI: + saat yönünün tersi
        }
    }
}
