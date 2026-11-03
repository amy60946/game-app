using System;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// D3 ışık halkası (23 Ekim 2026, kullanıcı onayı): yeni bir düğme ilk kez gösterilirken ekran hafifçe kısılır, düğme aydınlık
    /// bir dairenin içinde kalır ve çevresinde yumuşak halka atar. Dokunmayı engellemez (çocuk düğmeye basabilir); ipucuyla birlikte kalkar.
    /// </summary>
    public sealed class Spotlight : MonoBehaviour
    {
        private RectTransform _hole, _ring, _root;
        private Func<Vector2> _target;
        private float _radius, _t;
        private CanvasGroup _group;
        private static Texture2D _holeTex, _ringTex;

        /// <summary><paramref name="parent"/> içinde (ör. ipucu kökü), en arkada; hedef ekran pikseli her karede okunur.</summary>
        public static Spotlight Show(RectTransform parent, Func<Vector2> target, float radius = 130f)
        {
            var root = Ui.Fill(parent, "Spotlight");
            root.SetAsFirstSibling();
            var s = root.gameObject.AddComponent<Spotlight>();
            s._root = root; s._target = target; s._radius = radius;
            s._group = root.gameObject.AddComponent<CanvasGroup>(); s._group.blocksRaycasts = false; s._group.interactable = false; s._group.alpha = 0f;
            // delikli karartma: büyük dokunun ortası saydam; dört kenar dolgusu ekranın geri kalanını kaplar
            s._hole = Ui.Rect(root, "Hole", new Vector2(0f, 0f), new Vector2(radius * 6f, radius * 6f));
            var hi = s._hole.gameObject.AddComponent<RawImage>(); hi.texture = HoleTex(); hi.raycastTarget = false; hi.color = new Color(0.02f, 0.08f, 0.2f, Dim);
            foreach (var side in new[] { "L", "R", "T", "B" })
            {
                var e = Ui.Rect(s._hole, "Fill" + side, new Vector2(0.5f, 0.5f), Vector2.zero);
                var ei = e.gameObject.AddComponent<Image>(); ei.color = hi.color; ei.raycastTarget = false;
                const float far = 8000f;
                switch (side)
                {
                    case "L": e.anchorMin = new Vector2(0f, 0.5f); e.anchorMax = new Vector2(0f, 0.5f); e.pivot = new Vector2(1f, 0.5f); e.sizeDelta = new Vector2(far, far * 2f); break;
                    case "R": e.anchorMin = new Vector2(1f, 0.5f); e.anchorMax = new Vector2(1f, 0.5f); e.pivot = new Vector2(0f, 0.5f); e.sizeDelta = new Vector2(far, far * 2f); break;
                    case "T": e.anchorMin = new Vector2(0f, 1f); e.anchorMax = new Vector2(1f, 1f); e.pivot = new Vector2(0.5f, 0f); e.sizeDelta = new Vector2(0f, far); break;
                    default: e.anchorMin = new Vector2(0f, 0f); e.anchorMax = new Vector2(1f, 0f); e.pivot = new Vector2(0.5f, 1f); e.sizeDelta = new Vector2(0f, far); break;
                }
                e.anchoredPosition = Vector2.zero;
            }
            s._ring = Ui.Rect(root, "Ring", new Vector2(0f, 0f), new Vector2(radius * 2.2f, radius * 2.2f));
            var ri = s._ring.gameObject.AddComponent<RawImage>(); ri.texture = RingTex(); ri.raycastTarget = false; ri.color = new Color(1f, 0.9f, 0.45f, 0.9f);
            s.Place();
            return s;
        }

        // ---- K5 B (kullanıcı, 3 Kasım 2026): ilk 3 kritik eylemde %50 karartma; birden çok aydınlık hedef (ör. elma → Okti) ----
        private Func<Vector2>[] _targets;
        private Texture2D _dyn;
        private Color32[] _px;
        private const int DynW = 96, DynH = 54;
        public const float Dim = 0.5f;

        /// <summary>
        /// Ekran 0,3 sn'de %50 kararır, her hedefin çevresi aydınlık kalır (sürüklemede kaynak + bırakılacak yer); halka son hedefte.
        /// Dokunmayı engellemez; ipucuyla birlikte (aynı kökte) kalkar.
        /// </summary>
        public static Spotlight ShowMany(RectTransform parent, Func<Vector2>[] targets, float radius = 150f)
        {
            var root = Ui.Fill(parent, "Spotlight");
            root.SetAsFirstSibling();
            var s = root.gameObject.AddComponent<Spotlight>();
            s._root = root; s._targets = targets; s._target = targets[targets.Length - 1]; s._radius = radius;
            s._group = root.gameObject.AddComponent<CanvasGroup>(); s._group.blocksRaycasts = false; s._group.interactable = false; s._group.alpha = 0f;
            s._dyn = new Texture2D(DynW, DynH, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "spot_dyn" };
            s._px = new Color32[DynW * DynH];
            var raw = Ui.Fill(root, "Dim").gameObject.AddComponent<RawImage>(); raw.texture = s._dyn; raw.raycastTarget = false;
            s._hole = Ui.Rect(root, "NoHole", Vector2.zero, Vector2.zero);
            s._ring = Ui.Rect(root, "Ring", new Vector2(0f, 0f), new Vector2(radius * 2.2f, radius * 2.2f));
            var ri = s._ring.gameObject.AddComponent<RawImage>(); ri.texture = RingTex(); ri.raycastTarget = false; ri.color = new Color(1f, 0.9f, 0.45f, 0.9f);
            s.Paint();
            s.Place();
            return s;
        }

        /// <summary>Düşük çözünürlüklü karartma dokusu: her hedefin çevresinde yumuşak delik (çift doğrusal büyütme kenarı yumuşatır).</summary>
        private void Paint()
        {
            if (_dyn == null || _targets == null) return;
            var sw = Mathf.Max(1f, UnityEngine.Screen.width); var sh = Mathf.Max(1f, UnityEngine.Screen.height);
            var rpx = _radius * sw / Mathf.Max(1f, _root.rect.width);
            var pts = new Vector2[_targets.Length];
            for (var i = 0; i < pts.Length; i++) pts[i] = _targets[i] != null ? _targets[i]() : new Vector2(-9999f, -9999f);
            var a0 = (byte)(Dim * 255f);
            for (var y = 0; y < DynH; y++)
                for (var x = 0; x < DynW; x++)
                {
                    var p = new Vector2((x + 0.5f) / DynW * sw, (y + 0.5f) / DynH * sh);
                    var d = float.MaxValue;
                    foreach (var q in pts) d = Mathf.Min(d, (p - q).magnitude / rpx);
                    var a = Mathf.Clamp01((d - 1f) / 0.45f);
                    _px[y * DynW + x] = new Color32(5, 20, 51, (byte)(a0 * a));
                }
            _dyn.SetPixels32(_px); _dyn.Apply(false);
        }

        private void OnDestroy() { if (_dyn != null) Destroy(_dyn); }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            _group.alpha = Mathf.MoveTowards(_group.alpha, 1f, Time.unscaledDeltaTime / 0.3f);
            Paint();
            Place();
            var p = Mathf.Repeat(_t / 1.2f, 1f);
            _ring.localScale = Vector3.one * Mathf.Lerp(0.85f, 1.25f, p);
            var c = _ring.GetComponent<RawImage>(); var col = c.color; col.a = 0.9f * (1f - p); c.color = col;
        }

        private void Place()
        {
            if (_target == null) return;
            var k = _root.rect.width / Mathf.Max(1f, UnityEngine.Screen.width);
            var sp = _target() * k;
            _hole.anchoredPosition = sp;
            _ring.anchoredPosition = sp;
        }

        /// <summary>Kare doku: ortada yarıçapın 1/6'sı saydam (yumuşak kenar), dışı dolu.</summary>
        private static Texture2D HoleTex()
        {
            if (_holeTex != null) return _holeTex;
            const int n = 192;
            _holeTex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "spot_hole" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x + 0.5f) / n * 2f - 1f; var v = (y + 0.5f) / n * 2f - 1f;
                    var d = Mathf.Sqrt(u * u + v * v) * 3f;   // 1 = yarıçap (doku 6 yarıçap genişliğinde)
                    var a = Mathf.Clamp01((d - 1f) / 0.35f);
                    px[y * n + x] = new Color(1f, 1f, 1f, a);
                }
            _holeTex.SetPixels32(px); _holeTex.Apply();
            return _holeTex;
        }

        private static Texture2D RingTex()
        {
            if (_ringTex != null) return _ringTex;
            const int n = 128;
            _ringTex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "spot_ring" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x + 0.5f) / n * 2f - 1f; var v = (y + 0.5f) / n * 2f - 1f;
                    var d = Mathf.Abs(Mathf.Sqrt(u * u + v * v) - 0.86f);
                    px[y * n + x] = new Color(1f, 1f, 1f, Mathf.Clamp01((0.07f - d) * 16f));
                }
            _ringTex.SetPixels32(px); _ringTex.Apply();
            return _ringTex;
        }
    }
}
