using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Petin ayağında yumuşak temas gölgesi (kumsal görseli önünde: gerçek gölgeyi alacak zemin yok, pet havada durmasın).
    /// Yere yatık, ışıksız saydam yüzey (Pofi/Sprite); boyunu Stage petin ölçeğine ve zıplamasına göre ayarlar.
    /// </summary>
    public static class ContactShadow
    {
        private static Texture2D _tex;

        public static Transform Create(Transform parent)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Object.Destroy(q.GetComponent<Collider>());
            q.name = "ContactShadow";
            q.transform.SetParent(parent, false);
            q.transform.localPosition = new Vector3(0f, 0.004f, 0f);
            q.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);   // yüzü yukarı
            var r = q.GetComponent<MeshRenderer>();
            var m = InkHeart.SpriteMat(Tex());
            m.renderQueue = 3001;   // uzak kumsal görselinden (3000) sonra çizilsin
            r.sharedMaterial = m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return q.transform;
        }

        /// <summary>Ortası koyu, kenarı tamamen sönen sıcak kahve elips (kumun gölge tonu).</summary>
        private static Texture2D Tex()
        {
            if (_tex != null) return _tex;
            const int n = 64;
            _tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "contact_shadow" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
            for (var x = 0; x < n; x++)
            {
                var u = (x + 0.5f) / n * 2f - 1f; var v = (y + 0.5f) / n * 2f - 1f;
                var d = Mathf.Clamp01(u * u + v * v);
                var a = Mathf.Pow(1f - d, 1.8f) * 0.5f;
                px[y * n + x] = new Color(0.36f, 0.24f, 0.12f, a);
            }
            _tex.SetPixels32(px); _tex.Apply();
            return _tex;
        }
    }

    /// <summary>
    /// Kumsal görselinin denizinde kısa kısa parlayan yıldız parıltıları (24 Ekim 2026: "deniz parıltısı"). Görselin çocukları:
    /// konum görselin (u, v) oranında, ekran oranı değişse de denizde kalır. Parçacık modülü yok: birkaç dörtgen, kodla.
    /// </summary>
    public sealed class BeachGlints : MonoBehaviour
    {
        private static Texture2D _tex;
        private readonly List<Transform> _items = new List<Transform>();
        private readonly List<Vector3> _base = new List<Vector3>();
        private readonly List<float> _phase = new List<float>(), _speed = new List<float>();
        private Material _mat;
        private float _t;

        /// <summary><paramref name="aspect"/>: görselin en/boy oranı (parıltı kare kalsın); spots: (u, v), v alttan.</summary>
        public static BeachGlints Add(Transform picture, float aspect, IList<Vector2> spots)
        {
            var g = picture.gameObject.AddComponent<BeachGlints>();
            g._mat = InkHeart.SpriteMat(Tex());
            g._mat.SetColor("_Color", new Color(1f, 0.98f, 0.9f, 1f));
            g._mat.renderQueue = 3001;   // görselin (3000) üstünde
            var rnd = new System.Random(11);
            for (var i = 0; i < spots.Count; i++)
            {
                var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
                Destroy(q.GetComponent<Collider>());
                q.name = "Glint";
                q.transform.SetParent(picture, false);
                q.transform.localPosition = new Vector3(spots[i].x - 0.5f, spots[i].y - 0.5f, -0.002f);
                var size = 0.026f + (float)rnd.NextDouble() * 0.018f;   // görsel yüksekliğine oran
                var s = new Vector3(size / Mathf.Max(0.1f, aspect), size, 1f);
                q.transform.localScale = Vector3.zero;
                var r = q.GetComponent<MeshRenderer>();
                r.sharedMaterial = g._mat;
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
                g._items.Add(q.transform); g._base.Add(s);
                g._phase.Add((float)rnd.NextDouble() * 20f);
                g._speed.Add(0.7f + (float)rnd.NextDouble() * 0.9f);
            }
            return g;
        }

        private void Update()
        {
            _t += Time.deltaTime;
            var calm = UI.Theme.ReduceMotion;
            for (var i = 0; i < _items.Count; i++)
            {
                // çoğu zaman sönük, arada bir kısa parlama (sinüsün tepesi keskinleştirilir)
                var w = Mathf.Sin(_t * _speed[i] + _phase[i]);
                var k = calm ? 0.5f : Mathf.Pow(Mathf.Max(0f, w), 8f);
                _items[i].localScale = _base[i] * k;
                _items[i].localRotation = Quaternion.Euler(0f, 0f, calm ? 0f : _t * 25f + _phase[i] * 10f);
            }
        }

        private void OnDestroy()
        {
            if (_mat != null) Destroy(_mat);
        }

        /// <summary>Dört kollu yıldız + yumuşak hale (beyaz; renk malzemeden).</summary>
        private static Texture2D Tex()
        {
            if (_tex != null) return _tex;
            const int n = 64;
            _tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "beach_glint" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
            for (var x = 0; x < n; x++)
            {
                var u = Mathf.Abs((x + 0.5f) / n * 2f - 1f); var v = Mathf.Abs((y + 0.5f) / n * 2f - 1f);
                var arms = Mathf.Exp(-u * u / 0.5f - v * v / 0.0025f) + Mathf.Exp(-v * v / 0.5f - u * u / 0.0025f);
                var halo = Mathf.Exp(-(u * u + v * v) / 0.02f) * 0.9f + Mathf.Exp(-(u * u + v * v) / 0.12f) * 0.25f;
                var a = Mathf.Clamp01(arms + halo) * Mathf.Clamp01((1f - Mathf.Max(u, v)) * 4f);
                px[y * n + x] = new Color(1f, 1f, 1f, a);
            }
            _tex.SetPixels32(px); _tex.Apply();
            return _tex;
        }
    }
}
