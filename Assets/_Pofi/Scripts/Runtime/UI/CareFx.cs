using System;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Bakım efektleri (kullanıcı isteği, 15 Ekim 2026): beslerken yiyecek petin ağzının yanında 3 ısırıkta biter (her ısırıkta
    /// kenardan bir parça kopar, kırıntılar düşer); yıkarken petin çevresinde birkaç saniye süzülen sabun baloncukları.
    /// Ekran üstünde çizilir, pet konumunu her karede okur (pet zıplarken de üstünde kalır). Kodla, kredisiz.
    /// </summary>
    public static class CareFx
    {
        private static Sprite _bubble, _dot;
        private static readonly Sprite[] _bite = new Sprite[3];

        /// <summary>Yiyecek 3 ısırıkta biter.</summary>
        public static void Food(RectTransform root, Sprite icon, Func<Vector2> petScreen)
        {
            if (icon == null || root == null) return;
            var rt = Ui.Rect(root, "FoodBite", Vector2.zero, new Vector2(170f, 170f));
            rt.gameObject.AddComponent<FoodBite>().Init(root, icon, petScreen);
        }

        /// <summary>Petin çevresinde sabun baloncukları (~2,5 sn).</summary>
        public static void Bubbles(RectTransform root, Func<Vector2> petScreen)
        {
            if (root == null) return;
            var rt = Ui.Fill(root, "WashBubbles");
            var cg = rt.gameObject.AddComponent<CanvasGroup>(); cg.blocksRaycasts = false; cg.interactable = false;
            rt.gameObject.AddComponent<WashBubbles>().Init(root, petScreen);
        }

        internal static Vector2 ToCanvas(RectTransform root, Vector2 screen) => screen * (root.rect.width / Mathf.Max(1f, Screen.width));

        /// <summary>Isırık maskesi: k = 0 bütün, 1 bir ısırık, 2 iki ısırık (sağ üst kenardan yuvarlak parçalar eksik).</summary>
        internal static Sprite BiteMask(int k)
        {
            if (_bite[k] != null) return _bite[k];
            const int n = 128;
            var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[n * n];
            // ısırık merkezleri (0..1): sağ üst, sonra sağ
            var bites = new[] { new Vector2(0.86f, 0.82f), new Vector2(0.98f, 0.5f) };
            for (var y = 0; y < n; y++)
            for (var x = 0; x < n; x++)
            {
                var p = new Vector2((x + 0.5f) / n, (y + 0.5f) / n);
                var a = 1f;
                for (var b = 0; b < k; b++)
                {
                    // her ısırık iki üst üste daire (diş izi gibi dalgalı kenar)
                    var c = bites[b];
                    var d = Mathf.Min(Vector2.Distance(p, c), Vector2.Distance(p, c + new Vector2(-0.07f, -0.1f)) + 0.02f);
                    a = Mathf.Min(a, Mathf.Clamp01((d - 0.2f) * n * 0.5f));
                }
                px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            tex.SetPixels32(px); tex.Apply(false, true);
            return _bite[k] = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }

        /// <summary>Sabun baloncuğu: saydam iç, parlak ince kenar, sol üstte ışık lekesi.</summary>
        internal static Sprite Bubble
        {
            get
            {
                if (_bubble != null) return _bubble;
                const int n = 96;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
                var px = new Color[n * n];
                for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var dx = (x + 0.5f) / n - 0.5f; var dy = (y + 0.5f) / n - 0.5f;
                    var r = Mathf.Sqrt(dx * dx + dy * dy) * 2f;                       // 0 merkez, 1 kenar
                    var inside = Mathf.Clamp01((1f - r) * n * 0.5f);
                    var rim = Mathf.SmoothStep(0.72f, 0.97f, r) * 0.85f;
                    var hl = Mathf.Clamp01(1f - Vector2.Distance(new Vector2(dx, dy), new Vector2(-0.18f, 0.2f)) / 0.12f);
                    var a = inside * Mathf.Clamp01(0.1f + rim + hl * 0.9f);
                    px[y * n + x] = new Color(1f, 1f, 1f, a);
                }
                tex.SetPixels(px); tex.Apply(false, true);
                return _bubble = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
            }
        }

        /// <summary>Yuvarlak kırıntı / damla.</summary>
        internal static Sprite Dot
        {
            get
            {
                if (_dot != null) return _dot;
                const int n = 32;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
                var px = new Color[n * n];
                for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(n / 2f, n / 2f));
                    px[y * n + x] = new Color(1f, 1f, 1f, Mathf.Clamp01(n / 2f - 1f - d));
                }
                tex.SetPixels(px); tex.Apply(false, true);
                return _dot = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
            }
        }
    }

    /// <summary>Petin ağız hizasında yiyecek: belirir, 3 ısırıkta biter, kırıntılar düşer.</summary>
    public sealed class FoodBite : MonoBehaviour
    {
        private RectTransform _root, _rt, _mask;
        private Image _maskImg;
        private Func<Vector2> _pet;
        private float _t;
        private int _bites;
        private static readonly float[] BiteAt = { 0.55f, 1.05f, 1.55f };

        public void Init(RectTransform root, Sprite icon, Func<Vector2> pet)
        {
            _root = root; _rt = (RectTransform)transform; _pet = pet;
            _mask = Ui.Fill(_rt, "Mask");
            _maskImg = _mask.gameObject.AddComponent<Image>(); _maskImg.sprite = CareFx.BiteMask(0); _maskImg.raycastTarget = false;
            _mask.gameObject.AddComponent<Mask>().showMaskGraphic = false;
            var food = Ui.Fill(_mask, "Food").gameObject.AddComponent<Image>();
            food.sprite = icon; food.preserveAspect = true; food.raycastTarget = false;
            food.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
            _rt.localScale = Vector3.zero;
            Follow();
        }

        private void Follow() => _rt.anchoredPosition = CareFx.ToCanvas(_root, _pet()) + new Vector2(110f, 40f);   // ağzın yanında

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            Follow();
            var s = _t < 0.25f ? Mathf.SmoothStep(0f, 1f, _t / 0.25f) : 1f;
            // ısırık anında kısa "çatırt" vuruşu
            for (var i = 0; i < BiteAt.Length; i++)
            {
                var dt = _t - BiteAt[i];
                if (dt >= 0f && dt < 0.15f) s *= 1f - Mathf.Sin(dt / 0.15f * Mathf.PI) * 0.14f;
            }
            _rt.localScale = Vector3.one * s;
            _rt.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(_t * 9f) * 4f);
            while (_bites < BiteAt.Length && _t >= BiteAt[_bites])
            {
                _bites++;
                Crumbs();
                Audio.Sfx.Play(Audio.SfxKind.Pop);
                if (_bites < 3) _maskImg.sprite = CareFx.BiteMask(_bites);
                else _mask.gameObject.SetActive(false);                       // son ısırık: bitti
            }
            if (_t > 2.1f) Destroy(gameObject);
        }

        private void Crumbs()
        {
            for (var i = 0; i < 5; i++)
            {
                var c = Ui.Rect(_root, "Crumb", Vector2.zero, Vector2.one * UnityEngine.Random.Range(12f, 22f));
                var img = c.gameObject.AddComponent<Image>(); img.sprite = CareFx.Dot; img.raycastTarget = false;
                img.color = Color.Lerp(new Color(0.96f, 0.84f, 0.55f), new Color(0.85f, 0.35f, 0.25f), UnityEngine.Random.value * 0.5f);
                c.anchoredPosition = _rt.anchoredPosition + new Vector2(50f, 30f);
                c.gameObject.AddComponent<Crumb>().Init(new Vector2(UnityEngine.Random.Range(-160f, 160f), UnityEngine.Random.Range(120f, 280f)));
            }
        }
    }

    /// <summary>Düşen kırıntı (yerçekimi, solma).</summary>
    public sealed class Crumb : MonoBehaviour
    {
        private Vector2 _v;
        private float _t;
        private Image _img;
        public void Init(Vector2 v) { _v = v; _img = GetComponent<Image>(); }
        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _t += dt; _v.y -= 900f * dt;
            var rt = (RectTransform)transform;
            rt.anchoredPosition += _v * dt;
            var c = _img.color; c.a = Mathf.Clamp01(1f - _t / 0.7f); _img.color = c;
            if (_t > 0.7f) Destroy(gameObject);
        }
    }

    /// <summary>Petin çevresinde yükselen, sallanan ve patlayan sabun baloncukları.</summary>
    public sealed class WashBubbles : MonoBehaviour
    {
        private RectTransform _root;
        private Func<Vector2> _pet;
        private float _t, _next;
        private const float Spawn = 2.2f, Life = 1.5f;
        private readonly System.Collections.Generic.List<(RectTransform rt, Image img, Vector2 off, float born, float size, float phase)> _b =
            new System.Collections.Generic.List<(RectTransform, Image, Vector2, float, float, float)>();

        public void Init(RectTransform root, Func<Vector2> pet) { _root = root; _pet = pet; }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            var center = CareFx.ToCanvas(_root, _pet());
            while (_t < Spawn && _t >= _next)
            {
                _next += 0.12f;
                var size = UnityEngine.Random.Range(40f, 96f);
                var rt = Ui.Rect(transform, "Bubble", Vector2.zero, new Vector2(size, size));
                var img = rt.gameObject.AddComponent<Image>(); img.sprite = CareFx.Bubble; img.raycastTarget = false;
                // hafif yanardöner ton
                img.color = Color.HSVToRGB(UnityEngine.Random.value, 0.18f, 1f);
                _b.Add((rt, img, new Vector2(UnityEngine.Random.Range(-180f, 180f), UnityEngine.Random.Range(-120f, 60f)), _t, size, UnityEngine.Random.value * 6f));
            }
            for (var i = _b.Count - 1; i >= 0; i--)
            {
                var b = _b[i];
                var age = (_t - b.born) / Life;
                if (age >= 1f) { Destroy(b.rt.gameObject); _b.RemoveAt(i); continue; }
                var rise = age * 220f;
                var wob = Mathf.Sin(_t * 4f + b.phase) * 22f;
                b.rt.anchoredPosition = center + b.off + new Vector2(wob, rise);
                // büyüyerek belirir, sonda patlar (büyüyüp kaybolur)
                var s = age < 0.2f ? age / 0.2f : age > 0.88f ? 1f + (age - 0.88f) * 3f : 1f;
                b.rt.localScale = Vector3.one * s;
                var c = b.img.color; c.a = age > 0.88f ? Mathf.Clamp01(1f - (age - 0.88f) / 0.12f) : 1f; b.img.color = c;
            }
            if (_t > Spawn + Life) Destroy(gameObject);
        }
    }

    /// <summary>Parıldayan yıldız (pet seçimi/isim ekranında petin çevresinde): yavaşça büyüyüp söner, döner.</summary>
    public sealed class Twinkle : MonoBehaviour
    {
        public float Phase, Speed = 1.3f;
        private Image _img;
        private void Awake() => _img = GetComponent<Image>();
        private void Update()
        {
            var k = Mathf.Sin(Time.unscaledTime * Speed + Phase) * 0.5f + 0.5f;
            transform.localScale = Vector3.one * Mathf.Lerp(0.55f, 1.15f, k);
            transform.localRotation = Quaternion.Euler(0f, 0f, Time.unscaledTime * 25f + Phase * 40f);
            if (_img != null) { var c = _img.color; c.a = Mathf.Lerp(0.25f, 1f, k); _img.color = c; }
        }
    }

    public static class StarSparkles
    {
        /// <summary>Petin çevresine (ekran oranı merkez, yarıçap) birkaç parıldayan yıldız serper.</summary>
        public static void Around(Transform parent, Vector2 center01, Vector2 radius, int count, int seed)
        {
            var rnd = new System.Random(seed);
            for (var i = 0; i < count; i++)
            {
                var a = (i + (float)rnd.NextDouble() * 0.5f) / count * Mathf.PI * 2f;
                var p = center01 + new Vector2(Mathf.Cos(a) * radius.x, Mathf.Sin(a) * radius.y);
                var rt = Ui.IconImage(parent, "ui_star", p, 40f + (float)rnd.NextDouble() * 34f);
                if (rt == null) return;
                rt.GetComponent<Image>().raycastTarget = false;
                var tw = rt.gameObject.AddComponent<Twinkle>(); tw.Phase = (float)rnd.NextDouble() * 6f; tw.Speed = 1f + (float)rnd.NextDouble();
            }
        }
    }
}
